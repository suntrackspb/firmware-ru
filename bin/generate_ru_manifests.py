#!/usr/bin/env python3
"""
Generate RU-suffixed manifests and firmware-list-RU.json for the gh-pages branch.

Reads built artifacts (*.mt.json + *.bin) from --artifacts-dir,
renames them with a -RU version suffix, patches manifest JSON,
and updates firmware-list-RU.json in --output-dir.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description='Generate RU firmware manifests')
parser.add_argument('--version', required=True, help='Base firmware version (e.g. 2.7.21.fc6c89a)')
parser.add_argument('--channel', choices=['stable', 'alpha'], default='alpha')
parser.add_argument('--artifacts-dir', required=True, type=Path)
parser.add_argument('--output-dir', required=True, type=Path)
args = parser.parse_args()

base_version = args.version.lstrip('v')
ru_version   = f'{base_version}-RU'
channel_key  = f'ru_{args.channel}'
artifacts    = args.artifacts_dir
output       = args.output_dir

firmware_dir = output / f'firmware-{ru_version}'
firmware_dir.mkdir(parents=True, exist_ok=True)


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def rename_versioned(name: str) -> str:
    """firmware-board-2.7.21.fc6c89a.bin → firmware-board-2.7.21.fc6c89a-RU.bin"""
    return name.replace(base_version, ru_version)


targets = []

# ── Process each target manifest ──────────────────────────────────────────────
for mt_file in sorted(artifacts.glob('*.mt.json')):
    manifest = json.loads(mt_file.read_text())

    board    = manifest.get('platformioTarget', '')
    platform = manifest.get('mcu', '')

    if not board or not platform:
        print(f'WARNING: skipping {mt_file.name} — missing platformioTarget or mcu', file=sys.stderr)
        continue

    manifest['version'] = ru_version

    for entry in manifest.get('files', []):
        old_name = entry['name']
        new_name = rename_versioned(old_name) if base_version in old_name else old_name

        src = artifacts / old_name
        dst = firmware_dir / new_name

        if not src.exists():
            print(f'WARNING: artifact not found: {src}', file=sys.stderr)
            continue

        shutil.copy2(src, dst)
        entry['name']  = new_name
        entry['md5']   = md5(dst)
        entry['bytes'] = dst.stat().st_size

    # Copy any extra board-specific .bin not listed in manifest
    for extra in artifacts.glob(f'*{board}*{base_version}*.bin'):
        dest_name = rename_versioned(extra.name)
        dst = firmware_dir / dest_name
        if not dst.exists():
            shutil.copy2(extra, dst)

    # Copy OTA files (no version in name, shared per platform)
    for ota in list(artifacts.glob('mt-*.bin')) + list(artifacts.glob('bleota*.bin')):
        dst = firmware_dir / ota.name
        if not dst.exists():
            shutil.copy2(ota, dst)

    new_mt_name = rename_versioned(mt_file.name)
    (firmware_dir / new_mt_name).write_text(json.dumps(manifest, indent=2))

    targets.append({'board': board, 'platform': platform})
    print(f'  ✓ {board} ({platform})')

if not targets:
    print('ERROR: no targets found in artifacts — check artifact download step', file=sys.stderr)
    sys.exit(1)

# ── Write release manifest (firmware-VERSION-RU.json) ─────────────────────────
release_manifest = {'version': ru_version, 'targets': targets}
(firmware_dir / f'firmware-{ru_version}.json').write_text(json.dumps(release_manifest, indent=2))
print(f'\nRelease manifest written ({len(targets)} targets)')

# ── Update firmware-list-RU.json ───────────────────────────────────────────────
list_path = output / 'firmware-list-RU.json'
if list_path.exists():
    try:
        firmware_list = json.loads(list_path.read_text())
    except (json.JSONDecodeError, OSError):
        firmware_list = {}
else:
    firmware_list = {}

firmware_list.setdefault('releases', {})
firmware_list['releases'].setdefault('ru_stable', [])
firmware_list['releases'].setdefault('ru_alpha', [])

new_entry = {
    'id': f'v{ru_version}',
    'title': f'Meshtastic Firmware {base_version} (Кириллица / Cyrillic)',
    'release_notes': 'Поддержка кириллицы на экране устройства (-D OLED_RU=1). '
                     'Меню остаётся на английском, входящие сообщения отображаются на русском.',
    'targets': [t['board'] for t in targets],
}

channel_list = [e for e in firmware_list['releases'][channel_key] if e.get('id') != new_entry['id']]
channel_list.insert(0, new_entry)
firmware_list['releases'][channel_key] = channel_list

list_path.write_text(json.dumps(firmware_list, indent=2, ensure_ascii=False))
print(f'firmware-list-RU.json updated: {channel_key} → {len(channel_list)} entries')
print(f'\nDone. Output directory: {firmware_dir}')
