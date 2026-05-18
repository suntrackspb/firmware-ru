#!/usr/bin/env python3
"""
Apply RU-specific patches to firmware source files.

Run this after checking out an upstream firmware tag to add:
  - FREESANS_*PT_LANG aliases to AppletFont.h (selects WIN1251 when OLED_RU=1)
  - Switch nicheGraphics.h files to use LANG aliases instead of hardcoded WIN1252/WIN1253

Idempotent: safe to run multiple times, skips already-patched files.
"""

import glob
from pathlib import Path

ROOT = Path(__file__).parent.parent


def patch_applet_font():
    path = ROOT / "src/graphics/niche/InkHUD/AppletFont.h"
    if not path.exists():
        print(f"SKIP (not found): {path}")
        return

    content = path.read_text()
    if "FREESANS_12PT_LANG" in content:
        print(f"SKIP (already patched): {path.relative_to(ROOT)}")
        return

    lang_block = """
// Language-aware aliases — resolve to the correct encoding based on build flags.
// Use these in nicheGraphics.h instead of hardcoded WIN1252 variants.
#if defined(OLED_RU) || defined(OLED_UA)
#define FREESANS_12PT_LANG FREESANS_12PT_WIN1251
#define FREESANS_9PT_LANG  FREESANS_9PT_WIN1251
#define FREESANS_6PT_LANG  FREESANS_6PT_WIN1251
#elif defined(OLED_GR)
#define FREESANS_12PT_LANG FREESANS_12PT_WIN1253
#define FREESANS_9PT_LANG  FREESANS_9PT_WIN1253
#define FREESANS_6PT_LANG  FREESANS_6PT_WIN1253
#elif defined(OLED_PL) || defined(OLED_CS)
#define FREESANS_12PT_LANG FREESANS_12PT_WIN1250
#define FREESANS_9PT_LANG  FREESANS_9PT_WIN1250
#define FREESANS_6PT_LANG  FREESANS_6PT_WIN1250
#else
#define FREESANS_12PT_LANG FREESANS_12PT_WIN1252
#define FREESANS_9PT_LANG  FREESANS_9PT_WIN1252
#define FREESANS_6PT_LANG  FREESANS_6PT_WIN1252
#endif
"""
    last_endif = content.rfind("\n#endif")
    if last_endif == -1:
        print(f"ERROR: could not find #endif in {path}")
        return

    content = content[:last_endif] + "\n" + lang_block + "\n#endif\n"
    path.write_text(content)
    print(f"PATCHED: {path.relative_to(ROOT)}")


def patch_niche_graphics():
    for path in sorted(ROOT.glob("variants/**/nicheGraphics.h")):
        content = path.read_text()
        new_content = content

        rel = path.relative_to(ROOT)

        # t5s3_epaper: uses 24/18pt WIN1253 (no WIN1251 equivalent) — add #ifdef block
        if "t5s3_epaper" in str(path):
            old = (
                "    InkHUD::Applet::fontLarge = FREESANS_24PT_WIN1253;\n"
                "    InkHUD::Applet::fontMedium = FREESANS_18PT_WIN1253;\n"
                "    InkHUD::Applet::fontSmall = FREESANS_12PT_WIN1253;"
            )
            new = (
                "    // For Cyrillic/Ukrainian: no 24/18pt WIN1251 fonts exist, fall back to 12/9/6pt\n"
                "#if defined(OLED_RU) || defined(OLED_UA)\n"
                "    InkHUD::Applet::fontLarge = FREESANS_12PT_WIN1251;\n"
                "    InkHUD::Applet::fontMedium = FREESANS_9PT_WIN1251;\n"
                "    InkHUD::Applet::fontSmall = FREESANS_6PT_WIN1251;\n"
                "#else\n"
                "    InkHUD::Applet::fontLarge = FREESANS_24PT_WIN1253;\n"
                "    InkHUD::Applet::fontMedium = FREESANS_18PT_WIN1253;\n"
                "    InkHUD::Applet::fontSmall = FREESANS_12PT_WIN1253;\n"
                "#endif"
            )
            if old in new_content and "OLED_RU" not in new_content:
                new_content = new_content.replace(old, new)

        # heltec_mesh_pocket: uses 12/9/6pt WIN1253 → LANG
        elif "heltec_mesh_pocket" in str(path):
            new_content = new_content.replace("FREESANS_12PT_WIN1253", "FREESANS_12PT_LANG")
            new_content = new_content.replace("FREESANS_9PT_WIN1253", "FREESANS_9PT_LANG")
            new_content = new_content.replace("FREESANS_6PT_WIN1253", "FREESANS_6PT_LANG")

        # All other InkHUD boards: WIN1252 → LANG
        else:
            new_content = new_content.replace("FREESANS_12PT_WIN1252", "FREESANS_12PT_LANG")
            new_content = new_content.replace("FREESANS_9PT_WIN1252", "FREESANS_9PT_LANG")
            new_content = new_content.replace("FREESANS_6PT_WIN1252", "FREESANS_6PT_LANG")

        if new_content != content:
            path.write_text(new_content)
            print(f"PATCHED: {rel}")
        else:
            print(f"SKIP (no changes): {rel}")


if __name__ == "__main__":
    print("=== Applying RU InkHUD e-ink font patches ===\n")
    patch_applet_font()
    print()
    patch_niche_graphics()
    print("\n=== Done ===")
