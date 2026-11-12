"""The three bosses, modelled procedurally and posed per frame (runs inside Blender).

Coordinates: one arena cell is 1 unit, the origin is the ground point the sprite stands on
(its hotspot), +Y goes away from the camera, +Z up. Every boss faces the camera (-Y).
"""
import math
import os

from mathutils import Vector

import blib
from blib import Skeleton, material, emissive, tube, primitive, smooth

TAU = 2 * math.pi


def sin(t):
    return math.sin(TAU * t)


def cos(t):
    return math.cos(TAU * t)


# ---------------------------------------------------------------------------
#   utopiec: a hunched water demon, slimy green, hung with weed and reeds
# ---------------------------------------------------------------------------

def utopiec(t):
    """t in [0, 1): the walk cycle."""
    import random
    skin = material("utopiec_skin", (0.035, 0.13, 0.07), rough=0.42, sss=0.1, coat=0.45,
                    colour2=(0.24, 0.32, 0.07), mix_scale=2.6, bump=0.45, bump_scale=8)
    belly = material("utopiec_belly", (0.26, 0.33, 0.12), rough=0.4, coat=0.5,
                     colour2=(0.10, 0.20, 0.07), mix_scale=5, bump=0.3, bump_scale=12)
    weed = material("utopiec_weed", (0.06, 0.05, 0.015), rough=0.4, coat=0.7,
                    colour2=(0.22, 0.20, 0.04), mix_scale=12)
    weed2 = material("utopiec_weed2", (0.30, 0.36, 0.06), rough=0.4, coat=0.7)
    fin_mat = material("utopiec_fin", (0.20, 0.10, 0.08), rough=0.45, coat=0.4, sss=0.3,
                       colour2=(0.08, 0.14, 0.06), mix_scale=8)
    reed = material("utopiec_reed", (0.30, 0.28, 0.09), rough=0.6)
    cattail = material("utopiec_cattail", (0.18, 0.08, 0.03), rough=0.8)
    eye = emissive("utopiec_eye", (0.8, 1.0, 0.15), 8.0)
    socket = material("utopiec_socket", (0.01, 0.02, 0.01), rough=0.5)
    tooth = material("utopiec_tooth", (0.75, 0.72, 0.55), rough=0.35)

    bob = 0.06 * abs(sin(t)) - 0.03
    sway = 0.06 * sin(t)
    s = Skeleton()
    pelvis = s.add((sway, 0.05, 1.3 + bob), 0.42)
    belly_i = s.chain(pelvis, [((sway * 0.6, -0.02, 1.8 + bob), 0.56)], 2)
    chest = s.chain(belly_i, [((sway * 0.3, 0.18, 2.35 + bob), 0.56)], 2)
    hump = s.chain(chest, [((0, 0.2, 2.75 + bob), 0.54)], 2)
    s.chain(hump, [((0, -0.2, 2.85 + bob), 0.36)], 2)
    for side, phase in ((-1, 0.0), (1, 0.5)):
        a = sin(t + phase)
        lift = max(0.0, cos(t + phase)) * 0.25
        hip = s.add((side * 0.32 + sway, 0.05, 1.25 + bob), 0.30, pelvis)
        knee = s.chain(hip, [((side * 0.55, -0.15 + 0.25 * a, 0.72 + lift), 0.22)], 2)
        ankle = s.chain(knee, [((side * 0.5, 0.1 + 0.3 * a, 0.14 + lift * 0.8), 0.15)], 2)
        s.chain(ankle, [((side * 0.62, -0.22 + 0.3 * a, 0.06 + lift * 0.6), 0.13)], 1)
    hands = []
    for side, phase in ((-1, 0.5), (1, 0.0)):
        a = sin(t + phase)
        sh = s.add((side * 0.62, 0.1, 2.65 + bob), 0.25, hump)
        elbow = s.chain(sh, [((side * 0.98, 0.0 + 0.22 * a, 2.05 + bob), 0.18)], 2)
        wrist = s.chain(elbow, [((side * 1.02, -0.22 + 0.3 * a, 1.45 + bob), 0.14)], 2)
        hands.append((side, Vector(s.points[wrist])))
    s.build("utopiec_body", skin)
    b = primitive("uv_sphere", belly, radius=0.5, location=(sway * 0.6, -0.2, 1.8 + bob),
                  segments=24, ring_count=16)
    b.scale = (0.82, 0.55, 0.95)
    smooth(b)
    # head: wide and flat like a catfish, thrust forward low between the shoulders
    hx, hy, hz = 0.0, -0.42, 2.98 + bob
    head = primitive("uv_sphere", skin, radius=0.5, location=(hx, hy, hz), segments=32,
                     ring_count=16)
    head.scale = (1.15, 1.0, 0.68)
    smooth(head)
    jaw = primitive("uv_sphere", skin, radius=0.45, location=(hx, hy - 0.1, hz - 0.24),
                    segments=24, ring_count=12)
    jaw.scale = (1.15, 0.92, 0.5)
    smooth(jaw)
    m = primitive("uv_sphere", socket, radius=0.3, location=(hx, hy - 0.43, hz - 0.2),
                  segments=16, ring_count=8)
    m.scale = (1.55, 0.35, 0.22)
    m.rotation_euler = (0, 0, 0)
    for k in range(7):
        x = (k - 3) * 0.13
        up = k % 2 == 0
        z0 = hz - 0.13 if up else hz - 0.28
        primitive("cone", tooth, radius1=0.045, depth=0.13,
                  location=(hx + x, hy - 0.5 + abs(x) * 0.35, z0 - (0.05 if up else -0.05)),
                  rotation=(0 if up else math.pi, 0, 0), vertices=6)
    for side in (-1, 1):
        ex, ey, ez = hx + side * 0.27, hy - 0.38, hz + 0.12
        sk = primitive("uv_sphere", socket, radius=0.14, location=(ex, ey + 0.02, ez),
                       segments=16, ring_count=8)
        sk.scale = (1.3, 0.8, 0.7)
        e = primitive("uv_sphere", eye, radius=0.1, location=(ex, ey - 0.03, ez - 0.01),
                      segments=16, ring_count=8)
        e.scale = (1.25, 0.8, 0.62)
        # a heavy brow slanting down to the nose: an angry stare
        brow = primitive("uv_sphere", skin, radius=0.2, location=(ex + side * 0.03, ey + 0.02, ez + 0.13),
                         segments=16, ring_count=8)
        brow.scale = (1.4, 0.75, 0.42)
        brow.rotation_euler = (0, side * 0.45, 0)
        smooth(brow)
        # gill fins behind the jaw
        fin = [Vector((hx + side * 0.5, hy - 0.05, hz + 0.0)),
               Vector((hx + side * 0.95, hy + 0.2, hz + 0.5)),
               Vector((hx + side * 1.12, hy + 0.3, hz + 0.05)),
               Vector((hx + side * 0.98, hy + 0.25, hz - 0.35)),
               Vector((hx + side * 0.55, hy + 0.05, hz - 0.22))]
        blib.mesh_object("fin", fin, [(0, 1, 2, 3, 4)], fin_mat)
        for k in range(3):
            tube("fin_ray", [fin[0], fin[1 + k]], [0.05, 0.02], skin, sides=5)
        wrist = next(h[1] for h in hands if h[0] == side)
        for k in range(3):
            spread = (k - 1) * 0.12
            tube("claw", [wrist, wrist + Vector((side * 0.05 + spread, -0.12, -0.25)),
                          wrist + Vector((side * 0.08 + spread * 1.6, -0.22, -0.5))],
                 [0.07, 0.05, 0.015], skin, sides=6)
    # weed draped over the skull and shoulders, hanging down and swinging behind the walk
    rnd = random.Random(7)
    strands = []
    for k in range(12):
        x = rnd.uniform(-0.55, 0.55)
        strands.append(((hx + x, hy + rnd.uniform(0.0, 0.3), hz + 0.3), (x * 0.9, rnd.uniform(-0.25, 0.1)),
                        rnd.uniform(0.7, 1.3)))
    for side in (-1, 1, -1, 1, 1, -1, 1, -1, -1, 1):
        x = side * rnd.uniform(0.35, 0.8)
        strands.append(((x, rnd.uniform(-0.1, 0.25), 2.95 + bob), (side * 0.2, -0.45), rnd.uniform(1.0, 1.7)))
    for k, ((x, y, z), (dx, dy), length) in enumerate(strands):
        lag = 0.1 * sin(t - 0.15 + k * 0.07)
        pts, radii = [], []
        for i in range(7):
            u = i / 6
            drape = min(1.0, u * 3)          # first over the skull, then straight down
            pts.append((x + dx * drape * 0.6 + lag * u + 0.04 * math.sin(k * 1.7 + u * 7),
                        y + dy * drape, z + 0.05 * (1 - drape) - length * max(0.0, u - 0.25)))
            radii.append(0.085 * (1 - u * 0.7))
        tube("weed", pts, radii, weed if k % 3 else weed2, sides=5)
    # reeds and cattails stuck in the hump, at odd angles
    for k in range(6):
        x = (k - 2.5) * 0.2
        base = Vector((x, 0.45, 2.55 + bob))
        lean = rnd.uniform(-0.5, 0.5) + x * 0.8 + 0.05 * sin(t + k * 0.2)
        tip = base + Vector((lean, 0.3 + rnd.uniform(0, 0.3), rnd.uniform(0.8, 1.3)))
        tube("reed", [base, tip], [0.035, 0.01], reed, sides=5)
        if k in (1, 4):
            tube("cattail", [base.lerp(tip, 0.68), base.lerp(tip, 0.88)], [0.075, 0.065], cattail, sides=6)
    shift(0.0, 0.3, 0.0, scale=0.9)


def shift(dx, dy, dz, scale=1.0, col="actor"):
    """Moves and scales the whole posed creature about the origin (its feet)."""
    for ob in blib.collection(col).objects:
        ob.location = Vector(((ob.location.x) * scale + dx, ob.location.y * scale + dy,
                              ob.location.z * scale + dz))
        ob.scale = ob.scale * scale


# ---------------------------------------------------------------------------
#   rendering
# ---------------------------------------------------------------------------

SPRITES = {
    # name: (frames, w, h, builder(frame, frames))
    "utopiec_walk": (6, 56, 60, lambda f, n: utopiec(f / n)),
}


def render_all(out, scale):
    only = os.environ.get("STORY_ONLY", "")
    for name, (n, w, h, build) in SPRITES.items():
        if only and not name.startswith(only):
            continue
        blib.reset()
        blib.game_camera(w, h, scale)
        blib.sprite_lights()
        for f in range(n):
            blib.clear()
            build(f, n)
            blib.render(out / f"{name}_{f}.png")
