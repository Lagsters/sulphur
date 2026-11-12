"""A look at the packed story art as the game would show it, read back from assets/story/ and
src/gen/story.h (so it checks the packing too).

    python tools/art/story/preview.py      -> build/art/preview_story.png (+ preview_story_*.png)

Title with the logo and a mock menu box, each map with a mock path of stage nodes, the bosses
at true size on a mock arena of 20 px tiles, and a 3x contact sheet of every boss frame.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "build" / "art"


def load_sprites():
    """name -> list of (frame image, hotspot) cut from the packed textures."""
    header = (ROOT / "src" / "gen" / "story.h").read_text()
    names = {}
    for m in re.finditer(r"#define STORY_([A-Z0-9_]+) (\d+)$", header, re.M):
        if not m.group(1).endswith(("_N", "_W", "_H")) and m.group(1) not in ("SPRITES", "SOUNDS"):
            names[int(m.group(2))] = m.group(1).lower()
    textures = [Image.open(ROOT / line.split()[1]).convert("RGBA")
                for line in (ROOT / "assets" / "story" / "rom.txt").read_text().splitlines()
                if line.startswith("texture")]
    sprites, current, tex = {}, None, 0
    for line in header.splitlines():
        m = re.search(r"story_tex\[ (\d+) \]", line)
        if m:
            current = names[int(m.group(1))]
            sprites[current] = []
        m = re.search(r"select_texture\( TEX_STORY_(\d+) \)", line)
        if m:
            tex = int(m.group(1))
        m = re.search(r"define_region\( (\d+), (\d+), (\d+), (\d+), (\d+), (\d+) \)", line)
        if m:
            x0, y0, x1, y1, hx, hy = map(int, m.groups())
            sprites[current].append((textures[tex].crop((x0, y0, x1 + 1, y1 + 1)), (hx - x0, hy - y0)))
    return sprites


def draw(canvas, sprite, x, y, frame=0):
    im, (hx, hy) = sprite[frame]
    canvas.alpha_composite(im, (x - hx, y - hy))


def title_screen(sp):
    c = sp["title_bg"][0][0].copy()
    draw(c, sp["logo"], 320, 78)
    d = ImageDraw.Draw(c)
    d.rectangle([230, 180, 410, 300], fill=(16, 10, 24), outline=(220, 180, 70), width=2)
    for k, text in enumerate(("STORY", "BATTLE", "OPTIONS", "QUIT")):
        d.text((290, 196 + k * 24), text, fill=(250, 230, 160) if k else (255, 255, 255))
    return c


def map_screen(sp, chapter):
    c = sp[f"map_{chapter}"][0][0].copy()
    d = ImageDraw.Draw(c)
    pts = [(70 + k * 55, 180 + int(28 * ((-1) ** k)) * (k % 3 != 0)) for k in range(10)]
    d.line(pts, fill=(60, 30, 14), width=3)
    for k, (x, y) in enumerate(pts):
        frame = 2 if k in (4, 9) else (1 if k < 3 else 0)
        draw(c, sp["map_node"], x, y, frame)
    return c


def arena(sp):
    c = Image.new("RGBA", (640, 360))
    d = ImageDraw.Draw(c)
    for r in range(18):
        for q in range(32):
            shade = 34 + 6 * ((q + r) % 2)
            d.rectangle([q * 20, r * 20, q * 20 + 19, r * 20 + 19], fill=(shade, shade - 4, shade - 8))
    # each boss stands on the bottom middle of its 2x2 cells (marked)
    spots = [("utopiec_walk", 0, 80, 140), ("utopiec_walk", 3, 180, 140), ("jaga", 0, 300, 140),
             ("jaga_cast", 2, 420, 140), ("dragon_idle", 0, 120, 320), ("dragon_roar", 2, 320, 320),
             ("dragon_hurt", 0, 520, 320)]
    for name, f, x, y in spots:
        d.rectangle([x - 20, y - 39, x + 19, y], outline=(90, 80, 60))
        draw(c, sp[name], x, y, f)
    return c


def contact(sp):
    names = ["utopiec_walk", "jaga", "jaga_cast", "dragon_idle", "dragon_roar", "dragon_hurt"]
    rows = [sp[n] for n in names]
    width = max(sum(f[0].width + 4 for f in r) for r in rows) + 4
    height = sum(r[0][0].height + 4 for r in rows) + 4
    c = Image.new("RGBA", (width, height), (36, 32, 30, 255))
    y = 4
    for r in rows:
        x = 4
        for im, _ in r:
            c.alpha_composite(im, (x, y))
            x += im.width + 4
        y += r[0][0].height + 4
    return c.resize((width * 3, height * 3), Image.NEAREST)


def main():
    sp = load_sprites()
    parts = {"title": title_screen(sp), "map_1": map_screen(sp, 1), "map_2": map_screen(sp, 2),
             "map_3": map_screen(sp, 3), "arena": arena(sp), "contact": contact(sp)}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, im in parts.items():
        im.save(OUT / f"preview_story_{name}.png")
    sheet_w = max(1290, parts["contact"].width)
    sheet = Image.new("RGBA", (sheet_w, 3 * 370 + parts["contact"].height + 10), (12, 12, 12, 255))
    for k, name in enumerate(("title", "map_1", "map_2", "map_3", "arena")):
        sheet.alpha_composite(parts[name], ((k % 2) * 650, (k // 2) * 370))
    sheet.alpha_composite(parts["contact"], (0, 3 * 370))
    sheet.save(OUT / "preview_story.png")
    print(OUT / "preview_story.png")


if __name__ == "__main__":
    main()
