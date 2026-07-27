#!/usr/bin/env bash
# Fetches custom board variant directories from the develop branch and places
# them into the working tree (which is checked out at an upstream tag).
# Usage: sync_custom_variants.sh <owner/repo>
set -euo pipefail

REPO="${1:-suntrackspb/firmware-ru}"
BRANCH="develop"
API_BASE="https://api.github.com/repos/${REPO}/contents"
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

# Authenticate API requests when a token is available (CI matrix runs ~130
# concurrent jobs; unauthenticated api.github.com rate limit is 60 req/hour
# per IP and gets exhausted, causing sporadic 403s).
AUTH_HEADER=()
if [[ -n "${GH_TOKEN:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${GH_TOKEN}")
fi

# List of custom variant paths to sync (relative to repo root).
# Add new entries here when a new custom board is added to develop.
CUSTOM_VARIANTS=(
  "variants/nrf52840/diy/nrf52_promicro_diy_tcxo_cn"
)

for variant_dir in "${CUSTOM_VARIANTS[@]}"; do
  echo "Syncing ${variant_dir} from develop..."
  mkdir -p "${variant_dir}"

  # Get list of files in the directory via GitHub API
  files=$(curl -fsSL "${AUTH_HEADER[@]}" "${API_BASE}/${variant_dir}?ref=${BRANCH}" \
    | python3 -c "import json,sys; [print(f['name']) for f in json.load(sys.stdin) if f['type']=='file']")

  for file in $files; do
    curl -fsSL "${RAW_BASE}/${variant_dir}/${file}" -o "${variant_dir}/${file}"
    echo "  ✓ ${variant_dir}/${file}"
  done
done

echo "Custom variants synced."
