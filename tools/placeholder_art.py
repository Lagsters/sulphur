"""Placeholder art for every sprite in tools/catalog.py: flat shapes with the right sizes and
hotspots, so the game builds and runs before the real art exists.

    python tools/placeholder_art.py game|story
"""
import sys

from PIL import Image, ImageDraw

import catalog
from assetlib import pack_group

COLOURS = {"floor": (40, 48, 40), "pillar": (110, 110, 120), "wall": (90, 90, 100), "crate": (160, 100, 40),
           "zone": (70, 60, 60), "bomb": (230, 200, 40), "fire": (255, 140, 30), "item": (230, 230, 80),
           "hero": (220, 200, 160), "dwarf": (200, 40, 40), "bat": (120, 40, 140), "sheep": (240, 240, 240),
           "icon": (200, 200, 200), "spark": (255, 255, 120), "sparkle": (255, 255, 255), "shadow": (0, 0, 0),
           "utopiec": (60, 140, 90), "jaga": (130, 90, 160), "dragon": (170, 40, 30), "title": (30, 30, 70),
           "logo": (220, 180, 60), "map": (50, 70, 50)}


def colour(name):
    for key, c in COLOURS.items():
        if name.startswith(key):
            return c
    return (255, 0, 255)


def frames(name, n, size):
    out = []
    for f in range(n):
        im = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = colour(name)
        w, h = size
        if name.startswith(("floor", "pillar", "wall", "crate", "zone", "title", "map")):
            d.rectangle([0, 0, w - 1, h - 1], fill=c + (255,))
            if name.startswith(("crate", "pillar", "zone")):
                d.rectangle([1, 1, w - 2, h - 2], outline=(0, 0, 0, 255))
        else:
            k = 0.6 + 0.4 * ((f % 2) == 0)
            d.ellipse([w * (1 - k) / 2, h * (1 - k) / 2, w - 1 - w * (1 - k) / 2, h - 1 - h * (1 - k) / 2], fill=c + (255,))
        out.append(im)
    return out


def main(group):
    sprites = catalog.game_sprites() if group == "game" else catalog.story_sprites()
    pack_group(group, [(name, frames(name, n, size), hot) for (name, n, size, hot) in sprites])


if __name__ == "__main__":
    main(sys.argv[1])
