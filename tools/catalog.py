"""What the art must contain: every sprite the game draws, its frame count, size and hotspot.

The renderer (src/render.h and friends) uses these names through src/gen/<group>.h. The real art
(tools/art/*.py, rendered in Blender) and the placeholder art (tools/placeholder_art.py) both
produce exactly this list, so the game builds with either.

Hotspot conventions (the point draw_region_at() puts at the drawing point):
    tiles and icons    top left
    standing figures   between the feet (x = w/2, y = h-1): drawn at the bottom middle of the cell
    effects            the middle
"""

TILE = 20
THEMES = ("town", "forest", "castle")      # Wroclaw and Battle, Sleza, Krakow
DIRS = ("down", "up", "left", "right")
# 0 Dratewka, 1 Wanda, 2-5 Battle shoemakers in white, green, blue, red caps, 6 skeleton
LOOKS = ("dratewka", "wanda", "white", "green", "blue", "red", "skeleton")


def feet(w, h):
    return (w // 2, h - 1)


def mid(w, h):
    return (w // 2, h // 2)


def game_sprites():
    """(name, frames, (w, h), hotspot) of the game group: the arena, its people and the HUD."""
    s = []
    for t in THEMES:
        s.append((f"floor_{t}", 4, (TILE, TILE), (0, 0)))      # 4 variants, picked per cell
        s.append((f"pillar_{t}", 1, (TILE, TILE), (0, 0)))     # inner pillar, never breaks
        s.append((f"wall_{t}", 1, (TILE, TILE), (0, 0)))       # outer wall
        s.append((f"crate_{t}", 1, (TILE, TILE), (0, 0)))      # breaks in a blast
    s.append(("zone", 1, (TILE, TILE), (0, 0)))               # a cell the closing arena took
    s.append(("zone_warn", 1, (TILE, TILE), (0, 0)))          # a cell about to close (blinks)
    s.append(("bomb", 4, (TILE, TILE), mid(TILE, TILE)))      # sulphur bomb, pulsing
    s.append(("spark", 4, (8, 8), mid(8, 8)))                 # fuse sparks
    s.append(("fire", 8, (24, 24), mid(24, 24)))              # one burning cell, flash to smoke
    s.append(("fire_sheep", 8, (24, 24), mid(24, 24)))        # a sulphur sheep going off
    for item in ("item_bomb", "item_range", "item_shield", "item_key"):
        s.append((item, 1, (TILE, TILE), (0, 0)))
    s.append(("item_exit", 2, (TILE, TILE), (0, 0)))          # trapdoor: shut, glowing
    s.append(("sparkle", 4, (9, 9), mid(9, 9)))               # a crate hiding a quest item
    s.append(("shadow", 1, (18, 8), mid(18, 8)))              # under every figure
    for look in LOOKS:
        for d in DIRS:
            s.append((f"hero_{look}_{d}", 8, (24, 32), feet(24, 32)))   # frame 0 stands
        s.append((f"hero_{look}_die", 6, (24, 32), feet(24, 32)))
    for d in DIRS:
        s.append((f"dwarf_{d}", 4, (20, 24), feet(20, 24)))
    s.append(("bat", 6, (24, 20), mid(24, 20)))
    for d in DIRS:
        s.append((f"sheep_{d}", 6, (24, 22), feet(24, 22)))
    s.append(("sheep_graze", 4, (24, 22), feet(24, 22)))
    for icon in ("icon_bomb", "icon_range", "icon_shield", "icon_sheep", "icon_key", "icon_heart"):
        s.append((icon, 1, (16, 16), (0, 0)))
    for look in LOOKS:
        s.append((f"icon_head_{look}", 1, (16, 16), (0, 0)))
    return s


def story_sprites():
    """The story group: bosses, the title screen and the world map."""
    s = [
        ("utopiec_walk", 6, (56, 60), feet(56, 60)),   # drawn at the bottom middle of its 2x2 cells
        ("jaga", 6, (60, 64), feet(60, 64)),           # Baba Jaga flying in her mortar
        ("jaga_cast", 4, (60, 64), feet(60, 64)),
        ("dragon_idle", 6, (112, 88), feet(112, 88)),
        ("dragon_roar", 4, (112, 88), feet(112, 88)),
        ("dragon_hurt", 2, (112, 88), feet(112, 88)),
        ("title_bg", 1, (640, 360), (0, 0)),
        ("logo", 1, (480, 120), mid(480, 120)),
        ("map_node", 3, (14, 14), mid(14, 14)),        # stage ahead, stage cleared, boss stage
    ]
    for ch in (1, 2, 3):
        s.append((f"map_{ch}", 1, (640, 360), (0, 0)))
    return s
