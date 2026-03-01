#!/usr/bin/env python3
"""
generate_glow.py
----------------
Generates the glow.png asset for the arch-installer Plymouth theme.
Run this once on the build machine before building the ISO.
The output goes into iso/airootfs/usr/share/plymouth/themes/arch-installer/

Requires: python-pillow
  sudo pacman -S python-pillow
"""

import sys
import os
import shutil

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    print("ERROR: Pillow not found. Install with:")
    print("  sudo pacman -S python-pillow")
    sys.exit(1)

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "iso", "airootfs", "usr", "share", "plymouth", "themes", "arch-installer"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Glow image ────────────────────────────────────────────────────────────────
# A soft radial cyan glow, 300x300, transparent background.
# Plymouth renders this behind the spinning logo.

SIZE   = 300
CENTER = SIZE // 2
MAX_R  = CENTER

glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(glow)

# Draw concentric circles from outside in, brighter toward center
for r in range(MAX_R, 0, -1):
    t = r / MAX_R
    alpha = int((1.0 - t ** 1.5) * 180)
    draw.ellipse(
        [CENTER - r, CENTER - r, CENTER + r, CENTER + r],
        fill=(92, 200, 240, alpha)
    )

# Blur to make it soft and glowy
glow = glow.filter(ImageFilter.GaussianBlur(radius=18))

out_path = os.path.join(OUTPUT_DIR, "glow.png")
glow.save(out_path, "PNG")
print(f"Generated: {out_path}  ({SIZE}x{SIZE})")

# ── Copy logo.png ─────────────────────────────────────────────────────────────
logo_src = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "installer", "assets", "installer.png"
)
logo_dst = os.path.join(OUTPUT_DIR, "logo.png")

if os.path.exists(logo_src):
    shutil.copy2(logo_src, logo_dst)
    print(f"Copied:    {logo_dst}")
else:
    print(f"WARNING: logo not found at {logo_src}")
    print("         Copy installer/assets/installer.png to the theme dir manually.")

print("\nDone! Theme assets ready in:")
print(f"  {OUTPUT_DIR}")
