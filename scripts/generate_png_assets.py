#!/usr/bin/env python3
"""Generate PNG icons from SVG sources for MasteryOS."""

import cairosvg
from pathlib import Path

PUBLIC = Path("/home/z/my-project/public")
BRAND = PUBLIC / "brand"

# Generate OG image (1200x630 PNG)
cairosvg.svg2png(
    url=str(BRAND / "og-image.svg"),
    write_to=str(BRAND / "og-image.png"),
    output_width=1200,
    output_height=630,
)
print("Generated: og-image.png (1200x630)")

# Generate icon 192x192
cairosvg.svg2png(
    url=str(BRAND / "logo-mark.svg"),
    write_to=str(PUBLIC / "icon-192.png"),
    output_width=192,
    output_height=192,
)
print("Generated: icon-192.png (192x192)")

# Generate icon 512x512
cairosvg.svg2png(
    url=str(BRAND / "logo-mark.svg"),
    write_to=str(PUBLIC / "icon-512.png"),
    output_width=512,
    output_height=512,
)
print("Generated: icon-512.png (512x512)")

# Generate apple-touch-icon (180x180)
cairosvg.svg2png(
    url=str(BRAND / "logo-mark.svg"),
    write_to=str(PUBLIC / "apple-touch-icon.png"),
    output_width=180,
    output_height=180,
)
print("Generated: apple-touch-icon.png (180x180)")

# Generate favicon.ico (32x32)
cairosvg.svg2png(
    url=str(PUBLIC / "favicon.svg"),
    write_to=str(PUBLIC / "favicon-32.png"),
    output_width=32,
    output_height=32,
)
print("Generated: favicon-32.png (32x32)")

print("\nAll PNG assets generated successfully!")
