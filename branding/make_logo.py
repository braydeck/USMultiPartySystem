#!/usr/bin/env python3
"""Generate 256x256 Substack publication logo options from the nine-party palette."""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Wedge, Circle
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
ORDER = ["PRG", "LIB", "DSA", "SD", "STY", "CUP", "CON", "POP", "NAT"]
SEATS = {"CON": 202, "SD": 164, "STY": 130, "CUP": 103, "POP": 99, "LIB": 93, "NAT": 46, "DSA": 22, "PRG": 14}
COLORS = {"PRG": "#1e3a8a", "LIB": "#1d4ed8", "DSA": "#60a5fa", "SD": "#06b6d4", "STY": "#16a34a",
          "CUP": "#a16207", "CON": "#ea580c", "POP": "#dc2626", "NAT": "#7f1d1d"}
TOTAL = sum(SEATS.values())


def fig():
    f = plt.figure(figsize=(2.56, 2.56), dpi=100)
    ax = f.add_axes([0, 0, 1, 1]); ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_aspect("equal"); ax.axis("off")
    return f, ax


def parliament(bg, name):
    """Half-donut hemicycle: 9 wedges over the top semicircle, sized by seats."""
    f, ax = fig(); f.patch.set_facecolor(bg)
    ang = 180.0
    for code in ORDER:
        span = SEATS[code] / TOTAL * 180.0
        ax.add_patch(Wedge((0, -0.25), 1.05, ang - span, ang, width=0.62, facecolor=COLORS[code], edgecolor=bg, linewidth=2))
        ang -= span
    f.savefig(OUT / name, dpi=100, facecolor=bg)
    plt.close(f)


def ring(bg, name, monogram=None, mono_color="#0f172a", equal=True):
    """Full donut ring of 9 wedges (equal segments = visually balanced), optional monogram."""
    f, ax = fig(); f.patch.set_facecolor(bg)
    ang = 90.0
    for code in ORDER:
        span = 360.0 / len(ORDER) if equal else SEATS[code] / TOTAL * 360.0
        ax.add_patch(Wedge((0, 0), 0.92, ang - span, ang, width=0.21, facecolor=COLORS[code], edgecolor=bg, linewidth=2.5))
        ang -= span
    f.savefig(OUT / name, dpi=100, facecolor=bg)
    plt.close(f)
    if monogram:
        _stamp_monogram(OUT / name, monogram, mono_color)


def _stamp_monogram(path, glyph, color, fontsize=128):
    """Composite the glyph dead-center on the saved PNG, centered by its ACTUAL inked
    pixels (matplotlib/PIL text metrics include empty descender + side-bearing space,
    which pushes caps high and off-center). Render to a scratch layer, find the inked
    bbox via getbbox(), then paste so that box's center hits the image center."""
    base = Image.open(path).convert("RGBA")
    W, H = base.size
    fnt = ImageFont.truetype(fm.findfont("DejaVu Sans:bold"), fontsize)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((W // 2, H // 2), glyph, font=fnt, fill=color, anchor="mm")
    x0, y0, x1, y1 = layer.getbbox()  # actual inked extent
    dx = (W - (x0 + x1)) // 2
    dy = (H - (y0 + y1)) // 2
    base.alpha_composite(layer, (dx, dy))
    base.convert("RGB").save(path)


def pie(bg, name):
    """Full pie by seats — boldest fill."""
    f, ax = fig(); f.patch.set_facecolor(bg)
    ang = 90.0
    for code in ORDER:
        span = SEATS[code] / TOTAL * 360.0
        ax.add_patch(Wedge((0, 0), 0.92, ang - span, ang, facecolor=COLORS[code], edgecolor=bg, linewidth=2))
        ang -= span
    f.savefig(OUT / name, dpi=100, facecolor=bg)
    plt.close(f)


ring("#faf9f7", "logo.png")  # bare ring; monogram/wordmark added in Figma
print("wrote logo to", OUT / "logo.png")
