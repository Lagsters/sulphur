"""The backdrops of the scenes, painted in Blender: eight places, each a small 3D set seen from
a fixed camera. The actors walk on the line y = 0 nine metres from the camera, where one metre
is 64 final pixels, the scale of the cast.

    blender -b --factory-startup -P backdrops.py -- <outdir> [name ...]

Writes <outdir>/bd_<name>.png at twice the final 680 x 280 and <outdir>/bd_<name>.json with
anchors: named world points projected to final backdrop pixels (where the fire, the cave or the
notice board are), so the scene script puts actors on them.
"""
import json
import math
import os
import random
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from kit import ball, box, cyl, mat, mesh  # noqa: E402

W, H, SS = 680, 280, 2
OUT = "."


def setup():
    s = kit.reset()
    s.eevee.taa_render_samples = 48
    try:
        s.eevee.use_raytracing = True
    except AttributeError:
        pass
    # the actors' line y = 0 is 9 m away: 64 px a metre at 680 px over 36 mm and a 30 mm lens
    kit.camera((0, -9, 1.9), (0, 0, 1.9), lens=30)
    return s


def ground(color, color2=None, noise=0.5, scale=4.0, size=200, z=0.0, y=0.0, rough=0.9):
    return box((size, size, 1), (0, y + size / 2 - 20, z - 0.5),
               mat(color, rough, noise=noise, color2=color2, scale=scale))


def water(y0, y1, color="#1a2a48", z=0.02):
    return box((200, y1 - y0, 0.1), (0, (y0 + y1) / 2, z - 0.05), mat(color, 0.06, noise=0.15, scale=3))


def roof(x, y, w, d, h, z, material, along_x=True):
    """A gable roof prism over a w x d footprint at height z, ridge along x or y."""
    if along_x:
        v = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0), (-w / 2, 0, h), (w / 2, 0, h)]
        f = [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
    else:
        v = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0), (0, -d / 2, h), (0, d / 2, h)]
        f = [(0, 1, 4), (3, 5, 2), (0, 4, 5, 3), (1, 2, 5, 4), (0, 3, 2, 1)]
    return mesh(v, f, material, loc=(x, y, z), smooth=False)


def windows(x, y, w, h, z0, rows, cols, lit=0.0, color="#20180f", glow="#ffc060", size=(0.35, 0.55), rng=None):
    rng = rng or random.Random(1)
    for r in range(rows):
        for c in range(cols):
            wx = x - w / 2 + (c + 0.5) * w / cols
            wz = z0 + r * h / rows
            if rng.random() < lit:
                m = mat(glow, 0.5, emit=glow, strength=3.0)
            else:
                m = mat(color, 0.3)
            box((size[0], 0.08, size[1]), (wx, y, wz), m)


def house(x, y, w, h, d, wall, roofc, gable=True, lit=0.0, seed=0):
    """A town house facing the camera, its gable to the front."""
    rng = random.Random(seed)
    box((w, d, h), (x, y + d / 2, h / 2), mat(wall, 0.85, noise=0.3, scale=6))
    rm = mat(roofc, 0.7, noise=0.4, scale=10)
    if gable:
        roof(x, y + d / 2, w + 0.2, d + 0.2, w * 0.8, h, rm, along_x=False)
    else:
        roof(x, y + d / 2, w + 0.2, d + 0.2, 1.6, h, rm)
    floors = max(1, int(h / 2.6))
    windows(x, y - 0.03, w * 0.8, h - 1.2, 1.3, floors, max(1, int(w / 1.3)), lit=lit, rng=rng)


def tower(x, y, r, h, wall, roofc, roof_h, verts=8, z=0.0):
    cyl(r, r * 0.95, h, (x, y, z + h / 2), mat(wall, 0.85, noise=0.3, scale=5), verts=verts)
    cyl(r * 1.15, 0.0, roof_h, (x, y, z + h + roof_h / 2), mat(roofc, 0.6, noise=0.3, scale=8), verts=verts)


def pine(x, y, h, color="#1e3a2a", rng=None):
    rng = rng or random
    cyl(0.08 * h, 0.05 * h, 0.3 * h, (x, y, 0.15 * h), mat("#3a2818", 0.9))
    m = mat(color, 0.9, noise=0.4, scale=8)
    for k in range(3):
        cyl(0.3 * h * (1 - k * 0.22), 0, 0.5 * h, (x, y, 0.3 * h + k * 0.22 * h + 0.25 * h), m, verts=9,
            rot=(0, 0, rng.random() * 40))


def leafy(x, y, h, color="#3a5a28", rng=None):
    rng = rng or random
    cyl(0.07 * h, 0.05 * h, 0.5 * h, (x, y, 0.25 * h), mat("#4a3420", 0.9))
    b = ball(0.38 * h, (x, y, 0.72 * h), mat(color, 0.9, noise=0.5, scale=6), scale=(1.1, 1, 0.9), seg=16)
    kit.displace(b, 0.12 * h, 0.4)


def hill(x, y, r, z, color, color2, sx=1.0, sz=0.6, strength=1.5):
    b = ball(r, (x, y, z), mat(color, 0.9, noise=0.6, color2=color2, scale=2), scale=(sx, 1, sz), seg=48)
    kit.displace(b, strength, 0.6)
    return b


def crenels(x, y, w, z, m, step=0.6):
    n = int(w / step)
    for k in range(0, n, 2):
        box((step, 0.5, 0.45), (x - w / 2 + (k + 0.5) * step, y, z + 0.22), m)


def castle(x, y, z, scale=1.0, lit=0.3):
    """Wawel on its hill: walls, towers and the cathedral's gilded dome."""
    s = scale
    wall = "#c8b898"
    m = mat(wall, 0.85, noise=0.3, scale=5)
    box((9 * s, 2 * s, 2.5 * s), (x, y, z + 1.25 * s), m)
    crenels(x, y - 1 * s, 9 * s, z + 2.5 * s, m, 0.4 * s)
    box((5 * s, 3 * s, 4 * s), (x + 1.5 * s, y + 2 * s, z + 2 * s), mat("#d8c8a8", 0.85, noise=0.3, scale=5))
    roof(x + 1.5 * s, y + 2 * s, 5.2 * s, 3.2 * s, 1.4 * s, z + 4 * s, mat("#8a3a28", 0.7))
    windows(x + 1.5 * s, y + 0.45 * s, 4 * s, 2.4 * s, z + 2.4 * s, 2, 5, lit=lit, size=(0.25 * s, 0.4 * s))
    tower(x - 4.2 * s, y, 0.9 * s, 4.5 * s, wall, "#8a3a28", 2.2 * s, z=z)
    tower(x + 4.4 * s, y + 0.5 * s, 0.7 * s, 5.5 * s, wall, "#4a7a6a", 2.8 * s, z=z)
    tower(x - 1.6 * s, y + 3.5 * s, 0.6 * s, 6.5 * s, "#d0c0a0", "#4a7a6a", 3.0 * s, z=z)
    gold = mat("#e8b840", 0.25, 1.0)
    cyl(0.9 * s, 0.9 * s, 1.4 * s, (x - 0.3 * s, y + 1.5 * s, z + 3.2 * s), m)
    ball(0.95 * s, (x - 0.3 * s, y + 1.5 * s, z + 3.9 * s), gold, scale=(1, 1, 0.9))
    cyl(0.12 * s, 0, 0.9 * s, (x - 0.3 * s, y + 1.5 * s, z + 5.1 * s), gold)


def moon(x, y, z, r, color="#f4f0d8"):
    ball(r, (x, y, z), mat(color, 0.5, emit=color, strength=4.0))


def flame(x, y, z, h):
    """A bonfire: logs, layered flame cones and the light it throws."""
    wood = mat("#3a2414", 0.9)
    for a in (0, 60, 120):
        box((1.3 * h, 0.16, 0.16), (x, y, z + 0.1), wood, rot=(0, 10, a))
    for k, (c, r, hh) in enumerate((("#ff5010", 0.45, 1.3), ("#ff9020", 0.32, 1.0), ("#fff080", 0.18, 0.6))):
        cyl(r * h, 0, hh * h, (x, y - k * 0.05, z + hh * h / 2), mat(c, 0.5, emit=c, strength=6 + 4 * k), verts=10)
    kit.point((x, y - 0.6, z + 1.2 * h), 900 * h, "#ff8030", 0.4)


def anchors(points):
    s = bpy.context.scene
    out = {}
    for name, co in points.items():
        u = world_to_camera_view(s, s.camera, kit.Vector(co))
        out[name] = [round(u.x * W), round((1 - u.y) * H)]
    return out


def save(name, points=None):
    kit.render(os.path.join(OUT, f"bd_{name}.png"), W * SS, H * SS, transparent=False)
    with open(os.path.join(OUT, f"bd_{name}.json"), "w") as fh:
        json.dump({"anchors": anchors(points or {})}, fh)


# ---------------------------------------------------------------------------
#   the places
# ---------------------------------------------------------------------------

def wawel_night():
    setup()
    kit.sky([(0.25, "#2a3a70"), (0.55, "#141c48"), (1.0, "#05081a")], stars=0.035, light="#304070", light_strength=0.6)
    kit.sun((60, 0, 30), 1.6, "#9aa8e0", 3)
    moon(-30, 120, 48, 4.5)
    ground("#1e3a24", "#0e2014", 0.6, 3)
    water(5.0, 30, "#18284a")
    hill(12, 70, 18, -10, "#3a4a3a", "#1a2418", sx=1.6, sz=0.85, strength=2.5)
    castle(12, 66, 4.6, 1.5, lit=0.45)
    hill(-40, 80, 30, -20, "#1a2a2a", "#0a1414", sx=2.0, sz=0.9)
    rng = random.Random(3)
    for k in range(4):
        leafy(-9 + k * 1.2 + rng.random(), 6 + rng.random() * 2, 2.6 + rng.random(), "#1a3020", rng)
    for k in range(4):
        leafy(6.5 + k * 1.6, 7.0 + rng.random(), 2.4 + rng.random(), "#18301e", rng)
    save("wawel_night", {"meadow": (-2.5, 0, 0), "castle": (12, 66, 10), "sky": (0, 40, 14)})


def rynek():
    setup()
    kit.sky([(0.2, "#f4dcb0"), (0.5, "#a8c4e8"), (1.0, "#4a78c0")], light="#c0c8e0", light_strength=0.7)
    kit.sun((52, 0, -50), 4.0, "#fff0d0", 3)
    ground("#9a8a78", "#5a4e44", 0.6, 30)
    colours = ["#d86a4a", "#e8c070", "#7aa0c8", "#e89a70", "#a8c070", "#f0e0b0", "#c87a9a", "#e0b050"]
    rng = random.Random(7)
    x = -22.0
    k = 0
    while x < 24:
        w = 2.2 + rng.random() * 1.2
        if abs(x + w / 2 - 5.5) < 4.5:      # the town hall stands there
            x += 1.0
            continue
        house(x + w / 2, 24 + rng.random() * 0.4, w, 5.5 + rng.random() * 2.0, 4, colours[k % len(colours)],
              "#8a3a28", seed=k)
        x += w + 0.05
        k += 1
    # the town hall: brick, a stepped gable and its tower
    brick = mat("#a85a3a", 0.85, noise=0.4, scale=8)
    box((7, 5, 6), (5.5, 28.5, 3.0), brick)
    roof(5.5, 28.5, 7.2, 5.2, 3.5, 6, mat("#6a2a20", 0.7))
    for s in range(4):
        box((6.4 - s * 1.5, 0.4, 0.8), (5.5, 25.9, 6.1 + s * 0.8), brick)
    windows(5.5, 25.95, 6, 4, 1.4, 2, 5, size=(0.6, 1.2))
    tower(2.5, 29, 1.0, 9.5, "#b06040", "#3a6a5a", 3.5)
    ball(0.6, (2.5, 27.9, 7.5), mat("#f0e8d0", 0.4))                  # the clock face
    # the notice board where the herald nails the poster, and a well
    wood = mat("#6a4a2a", 0.8, noise=0.4, scale=12)
    for px in (-1.95, -0.65):
        box((0.14, 0.14, 2.6), (px, 0.8, 1.3), wood)
    box((1.6, 0.1, 1.2), (-1.3, 0.75, 1.75), mat("#8a6a42", 0.8, noise=0.4, scale=14))
    roof(-1.3, 0.8, 1.9, 0.5, 0.35, 2.6, wood)
    cyl(0.8, 0.8, 0.8, (5.5, 3.5, 0.4), mat("#8a8278", 0.9, noise=0.4, scale=10), verts=16)
    roof(5.5, 3.5, 2.0, 1.8, 1.0, 2.2, mat("#6a3a28", 0.7))
    for px in (4.7, 6.3):
        box((0.12, 0.12, 1.5), (px, 3.5, 1.5), wood)
    rng = random.Random(2)
    for k in range(4):
        leafy(-12 + k * 9.5 + rng.random(), 14 + rng.random(), 3.4, "#5a8a3a", rng)
    save("rynek", {"board": (-1.3, 0.7, 1.75), "ground": (0, 0, 0)})


def workshop():
    setup()
    kit.world_color("#2a2018", 0.5)
    plaster = mat("#b89a70", 0.95, noise=0.5, scale=3, color2="#6a5038")
    beam = mat("#3a2414", 0.85, noise=0.3, scale=10)
    box((30, 0.5, 9), (0, 6, 4.5), plaster)
    box((0.5, 20, 9), (-6.5, 0, 4.5), plaster)
    box((0.5, 20, 9), (6.8, 0, 4.5), plaster)
    box((30, 20, 0.4), (0, 0, 5.6), mat("#3a2818", 0.9))
    for x in range(-6, 8, 2):
        box((0.35, 20, 0.4), (x, 0, 5.2), beam)
    for x in (-4.5, 0.5, 5.0):
        box((0.35, 0.35, 6), (x, 5.6, 3), beam)
    ground("#5a4028", "#2a1c10", 0.5, 2.5)
    for k in range(-14, 14):                                          # floor boards
        box((0.04, 20, 0.02), (k * 0.6, 0, 0.0), mat("#2a1c10", 0.9))
    # the window, morning light falling through it
    box((2.4, 0.2, 1.8), (-2.0, 5.75, 3.2), mat("#f0e0b0", 0.5, emit="#f8e8c0", strength=3.0))
    box((0.12, 0.3, 1.9), (-2.0, 5.7, 3.2), beam)
    box((2.5, 0.3, 0.12), (-2.0, 5.7, 3.2), beam)
    kit.sun((50, 0, 200), 2.2, "#ffe8c0", 2)
    kit.point((-2.0, 4.5, 3.2), 300, "#ffe0b0", 1.0)
    # the hearth on the right
    stone = mat("#6a625a", 0.9, noise=0.5, scale=8)
    box((2.6, 1.2, 2.2), (4.8, 5.2, 1.1), stone)
    box((1.6, 0.4, 1.2), (4.8, 4.62, 0.7), mat("#100804", 0.9))
    for k, c in enumerate(("#ff5010", "#ffa030")):
        cyl(0.4 - k * 0.15, 0, 0.7 - k * 0.2, (4.8, 4.5, 0.45), mat(c, 0.5, emit=c, strength=8), verts=8)
    kit.point((4.8, 3.8, 0.9), 400, "#ff7020", 0.4)
    # the bench, lasts and boots on the shelves, hanging leather
    wood = mat("#7a5a38", 0.8, noise=0.4, scale=10)
    box((2.6, 0.9, 0.12), (-3.8, 2.0, 0.95), wood)
    for px in (-4.9, -2.7):
        box((0.12, 0.8, 0.95), (px, 2.0, 0.47), wood)
    leather = mat("#5a2e18", 0.6)
    for k in range(5):
        box((0.3, 0.12, 0.25), (-4.6 + k * 0.4, 1.9, 1.13), leather)
    for row in range(3):
        box((3.2, 0.5, 0.08), (1.5, 5.5, 1.6 + row * 0.9), wood)
        for k in range(5):
            box((0.22, 0.3, 0.45), (0.3 + k * 0.6, 5.4, 1.88 + row * 0.9), mat(["#3a1e10", "#6a3a1e", "#2a1a10"][k % 3], 0.5))
            box((0.35, 0.3, 0.12), (0.4 + k * 0.6, 5.4, 1.7 + row * 0.9), mat(["#3a1e10", "#6a3a1e", "#2a1a10"][k % 3], 0.5))
    for k in range(3):
        box((0.7, 0.05, 1.3), (-5.6 + k * 0.5, 5.4, 3.5), mat(["#8a5a30", "#6a4020", "#a07040"][k], 0.7), rot=(0, 0, 5 * k))
    save("workshop", {"ground": (0, 0, 0), "bench": (-3.8, 2.0, 1.0)})


def odra():
    setup()
    kit.sky([(0.3, "#f8b060"), (0.55, "#c86a60"), (1.0, "#3a2a68")], light="#a07080", light_strength=0.7)
    kit.sun((80, 0, -60), 3.0, "#ffb070", 4)
    water(-20, 22, "#2a3a5a", z=0.0)
    ground("#2a3a24", "#14200e", 0.5, 3, y=22, z=0.25)
    # the far bank: the cathedral island's two spires, houses and trees
    brick = "#9a4a34"
    box((7, 5, 6), (2, 49, 3.0), mat(brick, 0.85, noise=0.4, scale=6))
    roof(2, 49, 7.2, 5.2, 3, 6, mat("#3a6a5a", 0.6))
    for tx in (-1.0, 5.0):
        tower(tx, 46, 1.2, 8.5, brick, "#3a7a68", 5.5, verts=8, z=0)
    rng = random.Random(5)
    for k in range(7):
        house(-26 + k * 3.4, 42 + rng.random() * 2, 3.0, 4 + rng.random() * 2, 3, ["#c8a080", "#a87a60", "#d8b890"][k % 3],
              "#6a3028", lit=0.3, seed=k)
    for k in range(12):
        leafy(-30 + k * 5.5 + rng.random() * 2, 30 + rng.random() * 3, 3 + rng.random() * 1.5, "#2a4a28", rng)
    # reeds in the near water at the sides
    reed = mat("#4a5a28", 0.9)
    for k in range(40):
        side = -1 if k < 20 else 1
        x = side * (5.0 + rng.random() * 3)
        cyl(0.03, 0.0, 1.0 + rng.random(), (x, -1 + rng.random() * 3, 0.5), reed, verts=5,
            rot=(rng.random() * 14 - 7, rng.random() * 14 - 7, 0))
    save("odra", {"river": (0, 0, 0), "far": (0, 25, 0)})


def sleza():
    setup()
    kit.sky([(0.2, "#3a3060"), (0.5, "#1a1a40"), (1.0, "#06061a")], stars=0.03, light="#304060", light_strength=0.6)
    kit.sun((60, 0, 40), 0.9, "#8090d0", 3)
    moon(28, 120, 40, 3.0, "#f0e8c8")
    ground("#1a2a1a", "#0a140a", 0.6, 3)
    hill(-14, 150, 60, -30, "#26324a", "#0e1420", sx=1.2, sz=1.0, strength=6.0)    # Ślęża
    rng = random.Random(11)
    for k in range(30):
        x = -30 + k * 2.0 + rng.random()
        pine(x, 22 + rng.random() * 8, 3 + rng.random() * 2.5, "#102018", rng)
    for x in (-6.2, -5.0, 7.6, 8.8):
        pine(x, 5 + rng.random() * 2, 4.5 + rng.random(), "#142a1e", rng)
    flame(2.6, 2.0, 0.0, 1.0)
    # standing stones of the old cult around the glade
    stone = mat("#5a5a60", 0.9, noise=0.5, scale=5)
    for x, y in ((-0.5, 5), (5.5, 5.5), (7.5, 3.0)):
        b = ball(0.5, (x, y, 0.7), stone, scale=(0.7, 0.6, 1.6), seg=12)
        kit.displace(b, 0.1, 0.3)
    save("sleza", {"fire": (2.6, 2.0, 0.0), "ground": (0, 0, 0), "path": (-4, 0, 0)})


def krakow():
    setup()
    kit.sky([(0.15, "#ffc070"), (0.4, "#e07a6a"), (0.7, "#7a4a80"), (1.0, "#2a2050")], light="#a07090", light_strength=0.7)
    kit.sun((84, 0, -70), 3.0, "#ffa060", 3)
    ground("#7a6a60", "#3a302a", 0.6, 25)
    brick = "#a04a30"
    # St Mary's: the nave, the tall tower with its spire and crown, the lower one with a helmet
    box((5, 12, 8), (-3.5, 78, 4), mat(brick, 0.85, noise=0.4, scale=8))
    roof(-3.5, 78, 5.2, 12.2, 3.5, 8, mat("#5a2a20", 0.7), along_x=False)
    bm = mat(brick, 0.85, noise=0.4, scale=8)
    box((2.6, 2.6, 13), (-6.2, 71.5, 6.5), bm)
    cyl(1.3, 0.0, 6, (-6.2, 71.5, 16), mat("#3a6a5a", 0.6), verts=8)
    for dx, dy in ((-1.2, -1.2), (1.2, -1.2), (-1.2, 1.2), (1.2, 1.2)):
        cyl(0.35, 0.0, 2.0, (-6.2 + dx, 71.5 + dy, 14.0), mat("#3a6a5a", 0.6), verts=6)
    ball(0.45, (-6.2, 71.5, 18.0), mat("#e8b840", 0.25, 1.0))
    box((2.4, 2.4, 10.5), (-2.4, 71.5, 5.25), bm)
    ball(1.3, (-2.4, 71.5, 11.0), mat("#3a6a5a", 0.6), scale=(1, 1, 1.3))
    cyl(0.1, 0.0, 2.0, (-2.4, 71.5, 13.0), mat("#e8b840", 0.25, 1.0))
    windows(-6.2, 70.15, 2, 9, 3, 3, 1, size=(0.7, 2.0))
    # the Cloth Hall: a long hall, arcades below and a parapet of masks on top
    hall = mat("#e0c8a0", 0.85, noise=0.3, scale=8)
    box((26, 5, 5), (14, 40, 2.5), hall)
    roof(14, 40, 26.2, 5.2, 1.6, 5, mat("#8a3a28", 0.7))
    box((26.2, 0.4, 1.4), (14, 37.4, 5.7), hall)
    for k in range(20):
        box((0.3, 0.42, 0.7), (1.6 + k * 1.3, 37.4, 6.6), hall)
        box((0.8, 0.1, 2.6), (1.6 + k * 1.3, 37.45, 1.3), mat("#2a1e18", 0.8))
    rng = random.Random(9)
    for k in range(9):
        house(-37 + k * 3.0, 30 + rng.random() * 3, 2.9, 4.5 + rng.random() * 2, 3, ["#e0a070", "#c8b090", "#d08070"][k % 3],
              "#7a3428", lit=0.4, seed=k)
    hill(70, 160, 20, -8, "#3a3a4a", "#1a1a2a", sx=1.5, sz=0.7)
    castle(68, 156, 5.5, 1.6, lit=0.3)
    save("krakow", {"tower_top": (-6.2, 71.5, 14), "ground": (0, 0, 0), "sky": (0, 30, 16)})


def den():
    setup()
    kit.sky([(0.2, "#f0d0a0"), (0.6, "#9ab8d8"), (1.0, "#5a80b8")], light="#b0b8d0", light_strength=0.7)
    kit.sun((55, 0, -40), 3.6, "#fff0d0", 3)
    ground("#4a7a34", "#2a4a1e", 0.6, 3)
    water(4, 30, "#3a5a80", z=0.03)
    box((30, 20, 1), (13, 14, -0.45), mat("#4a7a34", 0.9, noise=0.6, color2="#2a4a1e", scale=3))
    hill(-30, 70, 25, -10, "#5a7a8a", "#3a5060", sx=2.0, sz=0.5)
    # the limestone cliff of Wawel hill with the dragon's cave at its foot
    rock = mat("#c8bca0", 0.95, noise=0.6, scale=1.5, color2="#7a7060")
    cliff = box((16, 8, 6.5), (13, 13, 3.0), rock)
    kit.displace(cliff, 0.8, 1.5, subdiv=4)
    b = ball(2.0, (7.2, 8.9, 0.6), mat("#0a0606", 1.0), scale=(1.2, 0.15, 1.1), seg=32)
    ball(2.3, (7.2, 8.95, 0.6), mat("#3a342a", 1.0), scale=(1.2, 0.12, 1.1), seg=32)
    rng = random.Random(4)
    for k in range(5):
        leafy(-6 + k * 1.4 + rng.random(), 3.0 + rng.random(), 2.0 + rng.random(), "#3a6a2a", rng)
    reed = mat("#6a8a3a", 0.9)
    for k in range(25):
        cyl(0.03, 0.0, 0.6 + rng.random() * 0.6, (-6 + rng.random() * 8, 3.6 + rng.random() * 0.6, 0.3), reed, verts=5)
    del b
    save("den", {"cave": (7.2, 8.8, 0.0), "meadow": (-3, 0, 0), "river": (-2, 4.5, 0)})


def hall():
    setup()
    kit.world_color("#20140c", 0.5)
    stone = mat("#8a7a68", 0.9, noise=0.5, scale=3, color2="#4a4038")
    box((30, 0.5, 10), (0, 7, 5), stone)
    box((30, 20, 0.4), (0, 0, 7.5), mat("#2a1e14", 0.9))
    ground("#6a5a4a", "#3a3028", 0.6, 1.5)
    red = mat("#8a1a1a", 0.7, noise=0.3, scale=6)
    gold = mat("#e0b040", 0.3, 1.0)
    box((3.5, 12, 0.03), (0, 2.5, 0.01), red)                         # the carpet
    for x in (-5.5, -2.6, 2.6, 5.5):
        cyl(0.4, 0.4, 7.5, (x, 3.5, 3.75), mat("#a89880", 0.8, noise=0.4, scale=4), verts=16)
        box((1.0, 1.0, 0.4), (x, 3.5, 0.2), stone)
        box((1.0, 1.0, 0.4), (x, 3.5, 7.3), stone)
    for x in (-4.0, 4.0):                                             # the tall windows
        box((1.4, 0.2, 3.4), (x, 6.7, 4.2), mat("#a0c0f0", 0.4, emit="#c0d8ff", strength=2.5))
        box((1.6, 0.25, 0.1), (x, 6.65, 4.2), mat("#2a1e14"))
    for x in (-1.6, 1.6):                                             # the banners
        box((1.0, 0.05, 2.8), (x, 6.6, 4.8), red)
        ball(0.25, (x, 6.5, 5.0), gold)
    # the throne on its dais, under a canopy
    box((3, 2, 0.5), (0, 4.6, 0.25), stone)
    box((1.4, 0.9, 0.6), (0, 4.6, 0.8), red)
    box((1.5, 0.3, 2.6), (0, 5.1, 1.8), mat("#6a3a1a", 0.6))
    box((1.6, 0.35, 0.2), (0, 5.1, 3.1), gold)
    box((2.8, 1.6, 0.15), (0, 4.8, 4.6), red)
    for k, x in enumerate((-4.6, 4.6)):                               # torches
        box((0.12, 0.12, 0.6), (x, 6.6, 3.0), mat("#3a2414"))
        cyl(0.12, 0, 0.4, (x, 6.5, 3.5), mat("#ffa030", 0.5, emit="#ff9020", strength=8), verts=8)
        kit.point((x, 6.0, 3.5), 250, "#ff9040", 0.3)
    kit.point((0, -2, 5), 600, "#ffe0c0", 2.0)
    kit.sun((60, 0, 20), 1.0, "#c0d0ff", 5)
    save("hall", {"throne": (0, 4.0, 0.5), "ground": (0, 0, 0)})


JOBS = {f.__name__: f for f in (wawel_night, rynek, workshop, odra, sleza, krakow, den, hall)}

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    OUT = args[0]
    os.makedirs(OUT, exist_ok=True)
    for job in args[1:] or list(JOBS):
        JOBS[job]()
