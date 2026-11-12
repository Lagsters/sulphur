"""Preview of the game art as the game draws it: one mock 640x360 arena per theme (tiles at 20 px,
figures with their feet hotspot at the bottom middle of their cell, shadows, items, bombs, fire)
and a contact sheet of every sprite at 3x.

    python tools/art/game/preview.py      (after make.py)  ->  build/art/preview_game.png
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import catalog  # noqa: E402

FRAMES = ROOT / "build" / "art" / "game" / "frames"
OUT = ROOT / "build" / "art" / "preview_game.png"
T = catalog.TILE
SPRITES = {name: (n, size, hot) for name, n, size, hot in catalog.game_sprites()}
SHADOW_UP = 3  # the shadow's centre sits this far above a figure's draw point (its ground contact)


def frame(name, f=0):
    return Image.open(FRAMES / f"{name}_{f}.png").convert("RGBA")


def put(screen, name, f, x, y):
    """Draws like draw_region_at(): the sprite's hotspot lands on (x, y)."""
    hx, hy = SPRITES[name][2]
    screen.alpha_composite(frame(name, f), (x - hx, y - hy))


def arena(theme, seed):
    rnd = random.Random(seed)
    W, H = 32, 18
    grid = [["floor"] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if r in (0, H - 1) or c in (0, W - 1):
                grid[r][c] = "wall"
            elif r % 2 == 0 and c % 2 == 0:
                grid[r][c] = "pillar"
            elif rnd.random() < 0.38 and not (c < 5 and r < 5) and not (c > 26 and r > 12):
                grid[r][c] = "crate"
    # the closing arena has taken the left column and part of the top row
    for r in range(1, H - 1):
        grid[r][1] = "zone"
    for c in range(1, 9):
        grid[1][c] = "zone"
    warn = [(r, 2) for r in range(2, 9)] + [(2, c) for c in range(3, 9)]
    for r, c in warn:
        grid[r][c] = "floor"
    open_cells = [(9, 6), (9, 7), (9, 8), (9, 9), (9, 10), (8, 9), (10, 9), (7, 9), (11, 9),
                  (5, 15), (5, 16), (5, 17), (6, 17), (13, 22), (13, 23), (13, 24), (12, 23), (14, 23),
                  (3, 3), (3, 4), (4, 3), (5, 3), (3, 5), (15, 27), (15, 28), (14, 28), (15, 29),
                  (7, 13), (7, 14), (7, 15), (11, 19), (11, 20), (11, 21), (3, 25), (3, 26), (3, 27), (4, 27),
                  (13, 12), (13, 13), (13, 14), (13, 15), (15, 5), (15, 6), (15, 7)]
    for r, c in open_cells:
        if grid[r][c] == "crate":
            grid[r][c] = "floor"
    return grid, warn


def scene(theme, seed, looks, monsters):
    screen = Image.new("RGBA", (640, 360), (0, 0, 0, 255))
    grid, warn = arena(theme, seed)
    rnd = random.Random(seed + 1)
    for r, row in enumerate(grid):
        for c, t in enumerate(row):
            x, y = c * T, r * T
            if t == "floor":
                put(screen, f"floor_{theme}", rnd.choice((0, 0, 0, 1, 1, 2, 3)), x, y)
            elif t == "zone":
                put(screen, "zone", 0, x, y)
            else:
                put(screen, f"{t}_{theme}", 0, x, y)
    for r, c in warn:
        put(screen, "zone_warn", 0, c * T, r * T)
    # items, the exit, a crate hiding the key
    for i, (r, c) in enumerate(((5, 16), (7, 14), (11, 20), (3, 26))):
        put(screen, ("item_bomb", "item_range", "item_shield", "item_key")[i], 0, c * T, r * T)
    put(screen, "item_exit", 1 if theme == "castle" else 0, 28 * T, 15 * T)
    crates = [(r, c) for r, row in enumerate(grid) for c, t in enumerate(row) if t == "crate"]
    sr, sc = crates[len(crates) // 2]
    # bombs (one with its fuse spark) and a blast cross
    for i, (r, c) in enumerate(((13, 23), (9, 4))):
        put(screen, "bomb", i * 2, c * T + T // 2, r * T + T // 2)
        put(screen, "spark", i, c * T + T // 2 + 3, r * T + T // 2 - 8)
    blast = [(9, 7), (9, 8), (9, 9), (9, 10), (8, 9), (10, 9), (7, 9), (11, 9)]
    for k, (r, c) in enumerate(blast):
        put(screen, "fire", min(7, 1 + k % 3), c * T + T // 2, r * T + T // 2)
    put(screen, "fire", 0, 9 * T + T // 2, 9 * T + T // 2)
    if theme == "castle":
        for k, (r, c) in enumerate(((13, 13), (13, 14), (13, 12))):
            put(screen, "fire_sheep", 2 + k, c * T + T // 2, r * T + T // 2)
    # figures, back to front
    figures = []
    spots = [(3, 4, "right", 3), (5, 17, "down", 0), (13, 22, "left", 5), (15, 6, "up", 2)]
    for (r, c, d, f), look in zip(spots, looks):
        figures.append((r, c * T + T // 2, f"hero_{look}_{d}", f))
    figures.append((11, 9 * T + T // 2, f"hero_{looks[-1]}_die", 3))
    for r, c, kind in monsters:
        if kind == "bat":
            figures.append((r, c * T + T // 2, "bat", r % 6))
        elif kind == "sheep_graze":
            figures.append((r, c * T + T // 2, "sheep_graze", 1))
        elif kind.startswith("sheep"):
            figures.append((r, c * T + T // 2, kind, 2))
        else:
            figures.append((r, c * T + T // 2, kind, 1))
    for r, x, name, f in sorted(figures, key=lambda t: t[0]):
        y = r * T + T - 1
        if name == "bat":
            put(screen, "shadow", 0, x, y - SHADOW_UP)
            put(screen, name, f, x, y - 14)
            continue
        if not name.endswith("_die"):
            put(screen, "shadow", 0, x, y - SHADOW_UP)
        put(screen, name, f, x, y)
    put(screen, "sparkle", 2, sc * T + T // 2, sr * T + T // 2)
    # HUD over the top wall row
    d = ImageDraw.Draw(screen)
    d.rectangle([0, 0, 639, 19], fill=(10, 8, 14, 255))
    x = 4
    for look in looks[:2]:
        put(screen, f"icon_head_{look}", 0, x, 2)
        x += 20
        for icon, num in (("icon_bomb", 3), ("icon_range", 2), ("icon_shield", 1), ("icon_heart", 3)):
            put(screen, icon, 0, x, 2)
            d.text((x + 17, 4), str(num), fill=(240, 230, 200, 255))
            x += 30
        x += 40
    put(screen, "icon_sheep", 0, 560, 2)
    put(screen, "icon_key", 0, 600, 2)
    return screen


def contact_sheet(scale=3, width=1920):
    pad, label = 6, 12
    rows, x, y, row_h = [], pad, pad, 0
    items = []
    for name, n, size, hot in catalog.game_sprites():
        w = n * (size[0] * scale + 2)
        h = size[1] * scale + label
        if x + w > width - pad:
            x, y = pad, y + row_h + pad
            row_h = 0
        items.append((name, n, size, x, y))
        x += w + pad * 2
        row_h = max(row_h, h)
    sheet = Image.new("RGBA", (width, y + row_h + pad), (52, 50, 62, 255))
    d = ImageDraw.Draw(sheet)
    for name, n, size, x, y in items:
        d.text((x, y), name, fill=(220, 220, 200, 255))
        for f in range(n):
            im = frame(name, f).resize((size[0] * scale, size[1] * scale), Image.NEAREST)
            sheet.alpha_composite(im, (x + f * (size[0] * scale + 2), y + label))
    return sheet


def main():
    themes = [
        ("town", 5, ("white", "green", "blue", "red"), [(7, 13, "dwarf_down"), (15, 13, "dwarf_left")]),
        ("forest", 6, ("dratewka", "wanda", "green", "skeleton"),
         [(3, 21, "bat"), (7, 25, "dwarf_right"), (11, 3, "dwarf_up"), (9, 27, "bat")]),
        ("castle", 7, ("dratewka", "wanda", "skeleton", "red"),
         [(5, 11, "sheep_left"), (7, 21, "sheep_graze"), (15, 17, "sheep_right"), (11, 27, "sheep_down"),
          (3, 15, "skeleton"), (9, 23, "bat")]),
    ]
    shots = []
    for theme, seed, looks, monsters in themes:
        monsters = [m for m in monsters if m[2] != "skeleton"]
        shots.append(scene(theme, seed, looks, monsters))
    sheet = contact_sheet()
    width = max(sheet.width, 640 * 3 + 16)
    out = Image.new("RGBA", (width, 360 + 16 + sheet.height), (20, 20, 24, 255))
    for i, s in enumerate(shots):
        out.alpha_composite(s, (i * (640 + 8), 0))
    out.alpha_composite(sheet, (0, 360 + 16))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    for i, s in enumerate(shots):
        s.save(OUT.with_name(f"preview_game_{themes[i][0]}.png"))
    sheet.save(OUT.with_name("preview_game_sheet.png"))
    print(OUT)


if __name__ == "__main__":
    main()
