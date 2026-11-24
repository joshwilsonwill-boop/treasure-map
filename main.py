#!/usr/bin/env python3
"""Charm the Cartographers: A One Day Treasure Map Sprint.

Draws one 1024x1024 treasure map of a fictional island, the Isle of
Misplaced Trousers, with seven labeled places, a compass rose, a sea
monster, a dotted route ending at a buried X, and small jokes in the
labels. Everything is drawn procedurally with Pillow: no network, no
outside images, no photographs.

The output is fully deterministic. All geometry is fixed, the only
randomness (parchment speckle) uses a fixed seed, and Pillow's PNG
encoder writes no timestamps, so two runs produce identical bytes.
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFont

W = H = 1024

PARCHMENT = (242, 227, 179)
ISLAND = (247, 234, 208)
SEA = (186, 210, 201)
SEA_DARK = (150, 185, 178)
INK = (59, 42, 26)
INK_SOFT = (96, 74, 48)
RED = (178, 52, 40)
BLUE = (70, 110, 140)
GREEN = (88, 118, 70)
GOLD = (180, 140, 50)

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
]


def load_font(names, size):
    """Try the given font files in the known dirs, then fall back."""
    for d in FONT_DIRS:
        for name in names:
            path = os.path.join(d, name)
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except OSError:
                    continue
    return ImageFont.load_default()


SERIF_BOLD = lambda s: load_font(["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"], s)
SERIF = lambda s: load_font(["DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"], s)
SANS_BOLD = lambda s: load_font(["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"], s)


def halo_text(draw, xy, text, font, fill=INK, halo=PARCHMENT, anchor="mm"):
    """Draw text with a light halo so it stays readable over the map."""
    x, y = xy
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=halo, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def dashed_line(draw, points, fill, width=2, dash=10, gap=7):
    """Draw a dashed polyline through the given points."""
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            continue
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        dist = 0.0
        while dist < length:
            end = min(dist + dash, length)
            draw.line(
                [(x1 + ux * dist, y1 + uy * dist), (x1 + ux * end, y1 + uy * end)],
                fill=fill,
                width=width,
            )
            dist = end + gap


def wavy_line(draw, x1, y1, x2, y2, fill, width=3, amp=8, waves=3):
    """Draw a wavy line between two points (for rivers)."""
    steps = 60
    pts = []
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length
    for i in range(steps + 1):
        t = i / steps
        off = amp * math.sin(t * waves * 2 * math.pi)
        pts.append((x1 + dx * t + nx * off, y1 + dy * t + ny * off))
    draw.line(pts, fill=fill, width=width, joint="curve")


def draw_compass(draw, cx, cy, r):
    """A compass rose: outer ring, eight-point star, N/E/S/W."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=3)
    draw.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], outline=INK_SOFT, width=1)
    for ang, length in [(0, r - 6), (45, r - 22), (90, r - 6), (135, r - 22),
                        (180, r - 6), (225, r - 22), (270, r - 6), (315, r - 22)]:
        rad = math.radians(ang - 90)
        tip = (cx + length * math.cos(rad), cy + length * math.sin(rad))
        base1 = (cx + 7 * math.cos(rad + math.pi / 2), cy + 7 * math.sin(rad + math.pi / 2))
        base2 = (cx - 7 * math.cos(rad + math.pi / 2), cy - 7 * math.sin(rad + math.pi / 2))
        fill = INK if ang % 90 == 0 else INK_SOFT
        draw.polygon([tip, base1, base2], fill=fill)
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=RED, outline=INK)
    f = SERIF_BOLD(22)
    halo_text(draw, (cx, cy - r - 16), "N", f)
    halo_text(draw, (cx + r + 16, cy), "E", f)
    halo_text(draw, (cx, cy + r + 18), "S", f)
    halo_text(draw, (cx - r - 16, cy), "W", f)


def draw_monster(draw, cx, cy):
    """A friendly sea monster: three humps, a head, an eye, a spout."""
    for i, dx in enumerate((-52, 0, 52)):
        h = 34 - abs(i - 1) * 8
        draw.arc([cx + dx - 30, cy - h, cx + dx + 30, cy + h], 180, 360, fill=INK, width=4)
    draw.ellipse([cx + 78, cy - 58, cx + 118, cy - 18], outline=INK, width=4, fill=SEA_DARK)
    draw.ellipse([cx + 100, cy - 50, cx + 108, cy - 42], fill=INK)
    draw.line([(cx + 98, cy - 62), (cx + 88, cy - 82)], fill=INK, width=3)
    draw.line([(cx + 104, cy - 62), (cx + 104, cy - 84)], fill=INK, width=3)
    draw.line([(cx + 110, cy - 62), (cx + 120, cy - 82)], fill=INK, width=3)


def draw_ship(draw, cx, cy):
    """A small galleon at anchor: hull, two masts, two sails, flag."""
    draw.polygon([(cx - 34, cy), (cx + 34, cy), (cx + 24, cy + 16), (cx - 24, cy + 16)], fill=(122, 82, 48), outline=INK)
    draw.line([(cx - 14, cy), (cx - 14, cy - 42)], fill=INK, width=3)
    draw.line([(cx + 14, cy), (cx + 14, cy - 34)], fill=INK, width=3)
    draw.polygon([(cx - 12, cy - 40), (cx - 12, cy - 4), (cx + 8, cy - 4)], fill=PARCHMENT, outline=INK)
    draw.polygon([(cx + 16, cy - 32), (cx + 16, cy - 4), (cx + 32, cy - 4)], fill=PARCHMENT, outline=INK)
    draw.polygon([(cx - 14, cy - 42), (cx - 14, cy - 52), (cx + 2, cy - 47)], fill=RED)


def draw_palm(draw, cx, cy, s=1.0):
    """A palm tree: leaning trunk and five fronds."""
    draw.line([(cx, cy), (cx + 6 * s, cy - 34 * s)], fill=INK, width=4)
    for ang in (-70, -35, 0, 35, 70):
        rad = math.radians(ang - 90)
        tip = (cx + 6 * s + 26 * s * math.cos(rad), cy - 34 * s + 26 * s * math.sin(rad))
        mid = (cx + 6 * s + 14 * s * math.cos(rad - 0.5), cy - 34 * s + 14 * s * math.sin(rad - 0.5))
        draw.line([(cx + 6 * s, cy - 34 * s), mid, tip], fill=GREEN, width=3, joint="curve")


def draw_lighthouse(draw, cx, cy):
    """A cursed lighthouse on a headland: striped tower, lamp, rays."""
    draw.polygon([(cx - 16, cy + 30), (cx + 16, cy + 30), (cx + 10, cy - 34), (cx - 10, cy - 34)],
                 fill=PARCHMENT, outline=INK)
    draw.line([(cx - 13, cy + 8), (cx + 13, cy + 8)], fill=RED, width=8)
    draw.line([(cx - 11, cy - 16), (cx + 11, cy - 16)], fill=RED, width=8)
    draw.rectangle([cx - 13, cy - 46, cx + 13, cy - 34], fill=INK)
    draw.ellipse([cx - 5, cy - 43, cx + 5, cy - 33], fill=GOLD)
    for ang in (-30, 0, 30):
        rad = math.radians(ang - 90)
        draw.line([(cx, cy - 38), (cx + 52 * math.cos(rad), cy - 38 + 52 * math.sin(rad))],
                  fill=GOLD, width=2)


def draw_parrot(draw, cx, cy, body):
    """A small parrot doodle: body, wing, beak, tail, eye."""
    draw.ellipse([cx - 8, cy - 12, cx + 8, cy + 10], fill=body, outline=INK)
    draw.ellipse([cx - 5, cy - 4, cx + 5, cy + 4], fill=GOLD)
    draw.polygon([(cx + 8, cy - 6), (cx + 16, cy - 2), (cx + 8, cy + 2)], fill=GOLD, outline=INK)
    draw.line([(cx - 4, cy + 10), (cx - 10, cy + 20)], fill=GREEN, width=3)
    draw.ellipse([cx + 1, cy - 9, cx + 5, cy - 5], fill=INK)


def draw_tree(draw, cx, cy, s=1.0):
    """A round leafy tree."""
    draw.line([(cx, cy), (cx, cy - 22 * s)], fill=INK, width=4)
    draw.ellipse([cx - 18 * s, cy - 44 * s, cx + 18 * s, cy - 12 * s], fill=GREEN, outline=INK)


def draw_hill(draw, cx, cy, s=1.0):
    """A small hill with a snow-free top and a flag."""
    draw.polygon([(cx - 34 * s, cy), (cx + 34 * s, cy), (cx, cy - 40 * s)],
                 outline=INK, fill=(216, 196, 150))
    draw.line([(cx, cy - 40 * s), (cx, cy - 54 * s)], fill=INK, width=2)
    draw.polygon([(cx, cy - 54 * s), (cx, cy - 46 * s), (cx + 12 * s, cy - 50 * s)], fill=RED)


def draw_map():
    """Draw the whole map and return the image."""
    img = Image.new("RGB", (W, H), PARCHMENT)
    draw = ImageDraw.Draw(img)

    # Parchment speckle, fixed seed so the bytes never change.
    rng = random.Random(42)
    for _ in range(700):
        x, y = rng.randint(0, W - 1), rng.randint(0, H - 1)
        shade = rng.choice([(232, 214, 162), (236, 219, 170), (228, 208, 154)])
        draw.ellipse([x, y, x + 2, y + 2], fill=shade)
    # A few old stains.
    for (x, y, rx, ry) in [(820, 820, 90, 60), (180, 220, 70, 50), (880, 620, 60, 44)]:
        draw.ellipse([x - rx, y - ry, x + rx, y + ry], outline=(214, 190, 140), width=2)

    # Sea.
    draw.rectangle([36, 130, 988, 988], fill=SEA)
    # Wave marks in the sea.
    for (x, y) in [(140, 250), (250, 320), (880, 420), (920, 700), (150, 700), (700, 900), (350, 930)]:
        draw.arc([x - 26, y - 10, x + 26, y + 10], 200, 340, fill=SEA_DARK, width=2)
        draw.arc([x - 14, y - 4, x + 14, y + 4], 200, 340, fill=SEA_DARK, width=2)

    # The island.
    island = [(320, 215), (430, 185), (545, 195), (650, 225), (735, 275), (790, 350),
              (805, 450), (775, 545), (735, 640), (665, 730), (575, 800), (470, 845),
              (375, 835), (295, 785), (240, 700), (215, 600), (225, 505), (205, 430),
              (235, 340), (270, 260)]
    draw.polygon(island, fill=ISLAND, outline=INK)
    draw.line(island + [island[0]], fill=INK, width=4, joint="curve")
    # Inner shoreline echo.
    inner = [(x + (512 - x) * 0.03, y + (512 - y) * 0.03) for x, y in island]
    draw.line(inner + [inner[0]], fill=INK_SOFT, width=1, joint="curve")

    # Grog Lagoon, a bay of still water in the south west.
    draw.ellipse([262, 692, 398, 782], fill=SEA, outline=INK, width=3)
    draw.arc([282, 708, 378, 766], 200, 340, fill=SEA_DARK, width=2)

    # Mutiny Cove, a notch bitten out of the west coast.
    draw.ellipse([178, 428, 262, 512], fill=SEA, outline=INK, width=3)

    # Hills and the river that feeds the lagoon.
    draw_hill(draw, 430, 380, 1.0)
    draw_hill(draw, 560, 500, 0.8)
    wavy_line(draw, 470, 392, 348, 700, BLUE, width=3)

    # Parrot Parliament: three trees and two parrots.
    for (x, y, s) in [(590, 448, 1.0), (640, 458, 0.9), (615, 420, 0.8)]:
        draw_tree(draw, x, y, s)
    draw_parrot(draw, 596, 396, RED)
    draw_parrot(draw, 636, 404, BLUE)

    # Cursed Lighthouse on the north east headland.
    draw_lighthouse(draw, 735, 300)

    # Rum Runner's Rest: a hut and a palm in the south.
    draw.rectangle([548, 762, 592, 794], fill=(196, 158, 110), outline=INK)
    draw.polygon([(542, 764), (598, 764), (570, 742)], fill=RED, outline=INK)
    draw_palm(draw, 612, 800, 0.9)

    # Widow's Walk: a cliff edge on the west.
    draw.line([(232, 600), (232, 640), (262, 640)], fill=INK, width=3)
    draw.line([(232, 600), (252, 584)], fill=INK, width=3)

    # A palm at the landing beach.
    draw_palm(draw, 700, 756, 1.0)

    # The dotted route: ship, beach, and on to the X.
    draw_ship(draw, 868, 868)
    dashed_line(draw, [(838, 842), (760, 762), (640, 682), (540, 612), (498, 566)],
                RED, width=3, dash=9, gap=7)
    # Footpaths between the places.
    dashed_line(draw, [(490, 560), (590, 452)], INK_SOFT, width=2, dash=7, gap=6)
    dashed_line(draw, [(490, 560), (570, 762)], INK_SOFT, width=2, dash=7, gap=6)
    dashed_line(draw, [(490, 560), (330, 737)], INK_SOFT, width=2, dash=7, gap=6)

    # The buried X.
    draw.line([(466, 536), (514, 584)], fill=RED, width=6)
    draw.line([(514, 536), (466, 584)], fill=RED, width=6)
    draw.ellipse([452, 522, 528, 598], outline=RED, width=2)

    # Compass rose in the north east sea.
    draw_compass(draw, 884, 168, 56)

    # The sea monster in the south west sea, sunk low so its spout and
    # head stay clear of the Kraken label above it.
    draw_monster(draw, 110, 892)

    # Labels, each with a small ink dot on the place it names.
    f_big = SERIF_BOLD(24)
    f_med = SERIF_BOLD(21)
    f_small = SERIF(16)
    f_tiny = SERIF(14)

    def place(x, y, text, font=f_med, dot=None):
        if dot:
            draw.ellipse([dot[0] - 4, dot[1] - 4, dot[0] + 4, dot[1] + 4], fill=INK)
        halo_text(draw, (x, y), text, font)

    halo_text(draw, (512, 58), "THE ISLE OF MISPLACED TROUSERS", SERIF_BOLD(36))
    halo_text(draw, (512, 100), "surveyed by Capt. W. Obble, who lost his trousers here in 1719",
              SERIF(17))

    place(345, 812, "Grog Lagoon", f_med, dot=(330, 737))
    halo_text(draw, (345, 836), "2 doubloons a cup", f_tiny)
    place(128, 462, "Mutiny Cove", f_med, dot=(220, 470))
    halo_text(draw, (128, 486), "bring your own plank", f_tiny)
    place(618, 372, "Parrot Parliament", f_med, dot=(618, 420))
    halo_text(draw, (618, 500), "(they vote)", f_tiny)
    place(735, 208, "Cursed Lighthouse", f_med, dot=(735, 262))
    halo_text(draw, (735, 232), "the light lies", f_tiny)
    place(490, 626, "X Marks the Spot", f_big, dot=(490, 560))
    halo_text(draw, (490, 652), "dig here, mind the crabs", f_small)
    place(700, 835, "Rum Runner's Rest", f_med, dot=(570, 778))
    place(258, 658, "Widow's Walk", f_med, dot=(247, 620))
    halo_text(draw, (258, 682), "she is still waiting", f_tiny)
    place(120, 792, "Ye Kraken's Nap", f_med, dot=(110, 836))
    halo_text(draw, (120, 816), "here be mild inconvenience", f_tiny)

    # Scale bar and a last joke along the bottom.
    draw.line([(392, 962), (632, 962)], fill=INK, width=3)
    draw.line([(392, 954), (392, 970)], fill=INK, width=3)
    draw.line([(512, 954), (512, 970)], fill=INK, width=3)
    draw.line([(632, 954), (632, 970)], fill=INK, width=3)
    halo_text(draw, (512, 940), "1 league = 1 very long walk", f_small)

    # Double frame.
    draw.rectangle([24, 24, 1000, 1000], outline=INK, width=4)
    draw.rectangle([36, 36, 988, 988], outline=INK, width=1)

    return img


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    img = draw_map()
    img.save(os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
