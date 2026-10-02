#!/usr/bin/env python3
"""
Brand Asset & Favicon Generation Pipeline for SerpApi Job & Market Radar.
Generates pixel-perfect SVG logos and rasterizes multi-resolution favicons
using resvg-py and Pillow.
"""

import os
import io
from PIL import Image
import resvg_py

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

# 1. Premium Vector Icon Mark (viewBox 0 0 100 100)
# Sleek geometric radar reticle with 45-degree beam and detected telemetry blips
ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <radialGradient id="radarBg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#05070a" />
    </radialGradient>
    <linearGradient id="cyanSweep" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.8" />
      <stop offset="50%" stop-color="#00f0ff" stop-opacity="0.2" />
      <stop offset="100%" stop-color="#00f0ff" stop-opacity="0.0" />
    </linearGradient>
    <linearGradient id="neonGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="100%" stop-color="#00f0ff" />
    </linearGradient>
  </defs>

  <!-- Base Rounded Container with subtle cyan border -->
  <rect width="100" height="100" rx="22" fill="url(#radarBg)" stroke="#1e293b" stroke-width="1.5"/>

  <!-- Radar Concentric Rings -->
  <circle cx="50" cy="50" r="38" fill="none" stroke="#1e293b" stroke-width="1.2"/>
  <circle cx="50" cy="50" r="26" fill="none" stroke="#00f0ff" stroke-width="1.4" stroke-opacity="0.4" stroke-dasharray="3 3"/>
  <circle cx="50" cy="50" r="14" fill="none" stroke="#00f0ff" stroke-width="1.2" stroke-opacity="0.6"/>

  <!-- Precision Crosshairs -->
  <line x1="50" y1="8" x2="50" y2="20" stroke="#00f0ff" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="50" y1="80" x2="50" y2="92" stroke="#00f0ff" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="8" y1="50" x2="20" y2="50" stroke="#00f0ff" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="80" y1="50" x2="92" y2="50" stroke="#00f0ff" stroke-width="1.8" stroke-linecap="round"/>

  <!-- Active 45-degree Radar Sweep Sector -->
  <path d="M 50 50 L 76.8 23.2 A 38 38 0 0 0 50 12 Z" fill="url(#cyanSweep)"/>
  <line x1="50" y1="50" x2="76.8" y2="23.2" stroke="#00f0ff" stroke-width="2.5" stroke-linecap="round"/>

  <!-- Telemetry Detection Nodes (Active Job Matches) -->
  <circle cx="68" cy="32" r="3.2" fill="#10b981"/>
  <circle cx="68" cy="32" r="6" fill="none" stroke="#10b981" stroke-width="0.8" stroke-opacity="0.5"/>

  <circle cx="34" cy="62" r="2.4" fill="#38bdf8"/>
  <circle cx="62" cy="70" r="2" fill="#00f0ff"/>

  <!-- Radar Core Emitter -->
  <circle cx="50" cy="50" r="4.5" fill="url(#neonGlow)"/>
  <circle cx="50" cy="50" r="2" fill="#ffffff"/>
</svg>"""

# 2. Responsive Vector Favicon (Works on Light & Dark browser tabs)
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <defs>
    <style>
      .bg { fill: #0a0b0e; }
      .ring { stroke: #00f0ff; stroke-width: 1.5; fill: none; }
      .core { fill: #00f0ff; }
      .blip { fill: #10b981; }
      @media (prefers-color-scheme: light) {
        .bg { fill: #0f172a; }
      }
    </style>
  </defs>
  <rect width="32" height="32" rx="7" class="bg"/>
  <circle cx="16" cy="16" r="11" class="ring" stroke-opacity="0.3" stroke-dasharray="2 1"/>
  <circle cx="16" cy="16" r="7" class="ring" stroke-opacity="0.7"/>
  <line x1="16" y1="16" x2="24" y2="8" stroke="#00f0ff" stroke-width="2" stroke-linecap="round"/>
  <circle cx="16" cy="16" r="2.2" class="core"/>
  <circle cx="21" cy="11" r="1.5" class="blip"/>
</svg>"""

# 3. Full Brand Logo (Horizontal layout for Header & Presentations)
LOGO_FULL_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 80" width="360" height="80">
  <defs>
    <linearGradient id="logoSweep" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#00f0ff" stop-opacity="0.0"/>
    </linearGradient>
    <linearGradient id="textCyan" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00f0ff"/>
      <stop offset="100%" stop-color="#38bdf8"/>
    </linearGradient>
  </defs>

  <!-- Icon Mark Container -->
  <g transform="translate(10, 10)">
    <rect width="60" height="60" rx="14" fill="#0f172a" stroke="#1e293b" stroke-width="1.2"/>
    <circle cx="30" cy="30" r="22" fill="none" stroke="#1e293b" stroke-width="1"/>
    <circle cx="30" cy="30" r="15" fill="none" stroke="#00f0ff" stroke-width="1.2" stroke-opacity="0.4" stroke-dasharray="2 2"/>
    <path d="M 30 30 L 45 15 A 22 22 0 0 0 30 8 Z" fill="url(#logoSweep)"/>
    <line x1="30" y1="30" x2="45" y2="15" stroke="#00f0ff" stroke-width="2" stroke-linecap="round"/>
    <circle cx="30" cy="30" r="3" fill="#00f0ff"/>
    <circle cx="41" cy="19" r="2.2" fill="#10b981"/>
  </g>

  <!-- Typography -->
  <g transform="translate(84, 46)">
    <text font-family="'Space Grotesk', -apple-system, sans-serif" font-weight="700" font-size="22" fill="#f8fafc" letter-spacing="1">SERPAPI</text>
    <text x="96" font-family="'Space Grotesk', -apple-system, sans-serif" font-weight="800" font-size="22" fill="url(#textCyan)" letter-spacing="2">RADAR</text>
    <text y="17" font-family="'JetBrains Mono', monospace" font-size="9" fill="#94a3b8" letter-spacing="1.5">REAL-TIME LABOR INTELLIGENCE</text>
  </g>
</svg>"""


def generate_assets():
    os.makedirs(STATIC_DIR, exist_ok=True)

    # 1. Write SVG vectors
    icon_svg_path = os.path.join(STATIC_DIR, "logo-icon.svg")
    with open(icon_svg_path, "w", encoding="utf-8") as f:
        f.write(ICON_SVG)
    print(f"[OK] Generated {icon_svg_path}")

    favicon_svg_path = os.path.join(STATIC_DIR, "favicon.svg")
    with open(favicon_svg_path, "w", encoding="utf-8") as f:
        f.write(FAVICON_SVG)
    print(f"[OK] Generated {favicon_svg_path}")

    logo_full_path = os.path.join(STATIC_DIR, "logo.svg")
    with open(logo_full_path, "w", encoding="utf-8") as f:
        f.write(LOGO_FULL_SVG)
    print(f"[OK] Generated {logo_full_path}")

    # 2. Render High-Resolution Raster Icons with resvg-py
    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }

    images_for_ico = []

    for filename, dim in sizes.items():
        # Render directly from SVG string at exact dimensions
        png_bytes = resvg_py.svg_to_bytes(
            svg_string=ICON_SVG,
            width=dim,
            height=dim,
            shape_rendering="geometric_precision"
        )
        out_path = os.path.join(STATIC_DIR, filename)
        with open(out_path, "wb") as f:
            f.write(png_bytes)
        print(f"[OK] Rendered {filename} ({dim}x{dim}) via resvg-py ({len(png_bytes)} bytes)")

        # Collect 16, 32, and 48 sizes for multi-resolution ICO
        if dim in [16, 32]:
            img = Image.open(io.BytesIO(png_bytes))
            images_for_ico.append(img)

    # Also render a 48x48 specifically for standard desktop ICO
    ico_48_bytes = resvg_py.svg_to_bytes(
        svg_string=ICON_SVG,
        width=48,
        height=48,
        shape_rendering="geometric_precision"
    )
    img_48 = Image.open(io.BytesIO(ico_48_bytes))
    images_for_ico.append(img_48)

    # 3. Build Multi-Resolution Windows ICO (16x16, 32x32, 48x48)
    ico_path = os.path.join(STATIC_DIR, "favicon.ico")
    # Base image is 32x32, appending 16x16 and 48x48
    base_img = [img for img in images_for_ico if img.size == (32, 32)][0]
    extra_imgs = [img for img in images_for_ico if img.size != (32, 32)]
    base_img.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=extra_imgs
    )
    print(f"[OK] Generated multi-resolution Windows ICO at {ico_path} ({os.path.getsize(ico_path)} bytes)")


if __name__ == "__main__":
    generate_assets()
