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
    eye = emissive("utopiec_eye", (0.7, 1.0, 0.1), 0.9)
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
#   Baba Jaga: a crone flying in a wooden mortar, steering with the pestle
# ---------------------------------------------------------------------------

def jaga(t, cast=False):
    """t in [0, 1): the flight loop, or the spell when cast."""
    import random
    wood = material("jaga_wood", (0.20, 0.10, 0.04), rough=0.6, colour2=(0.42, 0.26, 0.11),
                    mix_scale=4, bump=0.5, bump_scale=6)
    pale_wood = material("jaga_pestle", (0.45, 0.32, 0.17), rough=0.55, colour2=(0.30, 0.18, 0.08),
                         mix_scale=9, bump=0.3, bump_scale=12)
    iron = material("jaga_iron", (0.08, 0.08, 0.09), rough=0.35, metal=0.9)
    cloak = material("jaga_cloak", (0.10, 0.06, 0.14), rough=0.7, colour2=(0.20, 0.12, 0.22),
                     mix_scale=5, bump=0.3, bump_scale=10)
    scarf = material("jaga_scarf", (0.50, 0.04, 0.03), rough=0.6, colour2=(0.30, 0.02, 0.04),
                     mix_scale=10, bump=0.3, bump_scale=14)
    flesh = material("jaga_flesh", (0.42, 0.40, 0.26), rough=0.5, sss=0.2,

                     colour2=(0.38, 0.40, 0.22), mix_scale=8, bump=0.4, bump_scale=18)
    hair = material("jaga_hair", (0.62, 0.62, 0.58), rough=0.5)
    eye = emissive("jaga_eye", (1.0, 0.75, 0.2), 1.4)
    magic = emissive("jaga_magic", (0.45, 1.0, 0.3), 1.0)
    dark = material("jaga_dark", (0.03, 0.02, 0.02), rough=0.9)
    rnd = random.Random(3)

    bob = 0.12 * sin(t) if not cast else 0.05 * sin(t)
    z0 = 0.55 + bob                     # the bottom of the mortar
    tilt = 0.06 * sin(t + 0.25)
    # mortar: a lathed log with iron hoops
    prof = [(0.0, 0.24), (0.07, 0.34), (0.17, 0.36), (0.3, 0.47), (0.65, 0.58), (0.92, 0.63), (1.0, 0.64)]
    tube("mortar", [(0, tilt * z, z0 + z) for z, r in prof], [r for z, r in prof], wood, sides=28)
    primitive("cylinder", dark, radius=0.56, depth=0.04, location=(0, tilt * 0.97, z0 + 0.97), vertices=28)
    for z, r in ((0.26, 0.47), (0.8, 0.63)):
        primitive("torus", iron, major_radius=r, minor_radius=0.035, location=(0, tilt * z, z0 + z),
                  major_segments=32, minor_segments=6)
    top = z0 + 1.0
    # body: hunched forward over the rim, the cloak spilling over it
    s = Skeleton()
    hip = s.add((0, 0.1, top - 0.3), 0.42)
    chest = s.chain(hip, [((0, -0.02, top + 0.42), 0.42)], 2)
    s.chain(chest, [((0, -0.15, top + 0.8), 0.3)], 2)
    s.build("jaga_body", cloak)
    for side in (-1, 1):
        drape = primitive("uv_sphere", cloak, radius=0.24, location=(side * 0.28, -0.22, top + 0.05),
                          segments=16, ring_count=8)
        drape.scale = (1.0, 0.7, 0.55)
        smooth(drape)
    hx, hy, hz = 0, -0.3, top + 1.15
    if cast:
        hy, hz = -0.2, top + 1.2
    # head: a red scarf over a long-nosed face
    sc = primitive("uv_sphere", scarf, radius=0.34, location=(hx, hy + 0.12, hz + 0.1), segments=24, ring_count=12)
    sc.scale = (1.0, 1.0, 1.0)
    smooth(sc)
    face = primitive("uv_sphere", flesh, radius=0.28, location=(hx, hy - 0.08, hz - 0.04), segments=24, ring_count=12)
    face.scale = (0.95, 0.85, 1.1)
    smooth(face)
    tube("nose", [(hx, hy - 0.3, hz + 0.02), (hx, hy - 0.56, hz - 0.04), (hx, hy - 0.64, hz - 0.2)],
         [0.09, 0.06, 0.02], flesh, sides=8)
    tube("chin", [(hx, hy - 0.25, hz - 0.22), (hx, hy - 0.4, hz - 0.36)], [0.09, 0.03], flesh, sides=8)
    for side in (-1, 1):
        primitive("uv_sphere", eye, radius=0.055, location=(hx + side * 0.12, hy - 0.31, hz + 0.08),
                  segments=8, ring_count=6)
    # grey hair and scarf tails streaming behind
    for k in range(9):
        x = rnd.uniform(-0.3, 0.3)
        flap = 0.12 * sin(t * 2 + k * 0.13)
        pts = [(hx + x, hy + 0.1, hz - 0.05)]
        for i in range(1, 6):
            u = i / 5
            pts.append((hx + x * (1 + u * 1.3), hy + 0.15 + u * 0.75, hz - 0.1 - u * 0.65 + flap * u + 0.05 * math.sin(k + u * 5)))
        tube("hair", pts, [0.05 * (1 - u * 0.6) for u in (0, .2, .4, .6, .8, 1)], hair, sides=5)
    for side in (-1, 1):
        flap = 0.15 * sin(t * 2 + (0.3 if side > 0 else 0))
        tube("scarf_tail", [(hx + side * 0.1, hy + 0.35, hz - 0.15), (hx + side * 0.2, hy + 0.6, hz - 0.45 + flap),
                            (hx + side * 0.28, hy + 0.85, hz - 0.65 - flap)], [0.09, 0.07, 0.03], scarf, sides=6)
    sh = [Vector((side * 0.38, -0.05, top + 0.7)) for side in (-1, 1)]

    if not cast:
        # right hand rows with the pestle; the left fist is shaken at the hero
        sweep = 0.45 * sin(t)
        grip = Vector((0.55, -0.45, top + 0.55))
        elbow = sh[1].lerp(grip, 0.5) + Vector((0.25, 0.1, -0.1))
        tube("arm_r", [sh[1], elbow, grip], [0.13, 0.11, 0.09], cloak, sides=8)
        primitive("uv_sphere", flesh, radius=0.1, location=grip, segments=12, ring_count=8)
        top_end = grip + Vector((-0.1 + sweep * 0.3, 0.25, 0.75))
        bottom = grip + Vector((0.35 + sweep * 0.5, 0.35 - sweep * 0.3, -1.45))
        tube("pestle", [top_end, grip, bottom], [0.07, 0.08, 0.17], pale_wood, sides=10)
        primitive("uv_sphere", pale_wood, radius=0.19, location=bottom, segments=12, ring_count=8)
        fist = Vector((-0.65, -0.55, top + 0.95 + 0.12 * sin(t * 2)))
        elbow = sh[0].lerp(fist, 0.5) + Vector((-0.2, 0.15, -0.15))
        tube("arm_l", [sh[0], elbow, fist], [0.13, 0.11, 0.09], cloak, sides=8)
        primitive("uv_sphere", flesh, radius=0.11, location=fist, segments=12, ring_count=8)
        for k in range(3):
            tube("finger", [fist, fist + Vector(((k - 1) * 0.06, -0.1, 0.17))], [0.035, 0.015], flesh, sides=5)
    else:
        # both arms up, a green spell swelling between the claws
        grow = 0.5 + 0.5 * math.sin(TAU * t - math.pi / 2)
        orb = Vector((0, -0.05, top + 2.1))
        for side, s0 in zip((-1, 1), sh):
            hand = orb + Vector((side * (0.32 + 0.12 * grow), 0.02, -0.15))
            elbow = s0.lerp(hand, 0.5) + Vector((side * 0.3, 0.1, -0.05))
            tube("arm", [s0, elbow, hand], [0.13, 0.11, 0.09], cloak, sides=8)
            primitive("uv_sphere", flesh, radius=0.1, location=hand, segments=12, ring_count=8)
            for k in range(3):
                tube("claw", [hand, hand + Vector((-side * 0.12, -0.05 + k * 0.05, 0.12 + k * 0.03))],
                     [0.035, 0.012], flesh, sides=5)
        r = 0.16 + 0.14 * grow
        primitive("uv_sphere", magic, radius=r, location=orb, segments=16, ring_count=10)
        halo = emissive("jaga_halo", (0.1, 0.6, 0.1), 1.0)
        for k in range(6):
            a = TAU * (k / 6 + t * 0.5)
            p0 = orb + Vector((math.cos(a) * (r + 0.1), 0, math.sin(a) * (r + 0.1)))
            p1 = orb + Vector((math.cos(a + 0.6) * (r + 0.35), -0.05, math.sin(a + 0.6) * (r + 0.35)))
            tube("wisp", [p0, p1], [0.04, 0.01], halo, sides=4)
        blib.point(orb + Vector((0, -0.3, 0.1)), (0.4, 1.0, 0.3), 60 + 120 * grow, radius=0.2, col="actor")
    # sparks and smoke trailing under the mortar
    ember = emissive("jaga_ember", (1.0, 0.55, 0.15), 1.5)
    smoke = material("jaga_smoke", (0.25, 0.24, 0.28), rough=0.9)
    for k in range(5):
        u = ((k / 5) + t) % 1.0
        p = Vector((0.15 * math.sin(k * 2.1), 0.3 + u * 1.2, z0 - 0.05 - u * 0.4))
        primitive("uv_sphere", smoke, radius=0.12 + 0.15 * u, location=p, segments=10, ring_count=6)
        if k % 2 == 0:
            primitive("uv_sphere", ember, radius=0.05, location=p + Vector((0.1, -0.15, 0.05)),
                      segments=6, ring_count=4)
    shift(0.0, 0.45, 0.0, scale=1.12)



# ---------------------------------------------------------------------------
#   the dragon of Wawel: huge, bronze-green, horned, wings half spread
# ---------------------------------------------------------------------------

def dragon(pose, t, silhouette=None):
    """pose: 'idle', 'roar' or 'hurt'; t in [0, 1) through its loop. silhouette replaces every
    material by one (the dragon in the title sky)."""

    def mat(name, *a, **k):
        return silhouette if silhouette is not None else material(name, *a, **k)

    def glow(name, colour, strength):
        return silhouette if silhouette is not None else emissive(name, colour, strength)

    scales = mat("dragon_scales", (0.07, 0.15, 0.06), rough=0.42, metal=0.3,
                 colour2=(0.40, 0.28, 0.08), mix_scale=2.2, bump=0.35, bump_scale=11, voronoi=True)
    plates = mat("dragon_plates", (0.62, 0.46, 0.16), rough=0.4, metal=0.3,
                 colour2=(0.40, 0.26, 0.08), mix_scale=6, bump=0.3, bump_scale=10)
    wing = mat("dragon_wing", (0.30, 0.07, 0.04), rough=0.55, sss=0.4,
               colour2=(0.40, 0.22, 0.06), mix_scale=3, bump=0.25, bump_scale=6)
    horn = mat("dragon_horn", (0.62, 0.55, 0.38), rough=0.35, colour2=(0.22, 0.15, 0.08), mix_scale=3)
    gums = mat("dragon_gums", (0.35, 0.04, 0.03), rough=0.4)
    mouth = glow("dragon_throat", (1.0, 0.35, 0.05), 1.6)
    eye = glow("dragon_eye", (1.0, 0.6, 0.05), 1.6)

    breathe = sin(t)
    jaw = 0.12 + 0.03 * breathe
    head_lift, head_back, head_turn, wing_up, wing_spread = 0.0, 0.0, 0.0, 0.08 * breathe, 0.0
    eyes_open = True
    if pose == "roar":
        k = [0.5, 1.0, 1.0, 0.7][int(t * 4) % 4]
        jaw = 0.25 + 0.5 * k
        head_lift, head_back, wing_up, wing_spread = 0.7 * k, 0.3 * k, 0.35 * k, 0.25 * k
    elif pose == "hurt":
        k = [1.0, 0.6][int(t * 2) % 2]
        jaw = 0.3 * k
        head_lift, head_back, head_turn, wing_up, wing_spread = 0.2 * k, 0.55 * k, 0.35 * k, -0.25 * k, -0.2 * k
        eyes_open = False
    elif pose == "fly":
        wing_up, wing_spread = 0.5, 0.4
    chest_r = 0.82 + 0.04 * breathe
    s = Skeleton()
    tail = s.add((-0.9, 3.9, 0.25), 0.04)
    s.chain(tail, [((-0.2, 3.5, 0.3), 0.12), ((0.5, 3.0, 0.35), 0.2), ((0.45, 2.3, 0.55), 0.32)], 3)
    pelvis = s.chain(len(s.points) - 1, [((0, 1.65, 0.95), 0.62)], 2)
    belly = s.chain(pelvis, [((0, 0.95, 1.15), chest_r)], 2)
    chest = s.chain(belly, [((0, 0.35, 1.4), chest_r * 0.95)], 2)
    nx, ny, nz = math.sin(head_turn) * 0.4, -0.55 + head_back, 2.25 + head_lift
    s.chain(chest, [((0, 0.05, 1.95), 0.52), ((nx * 0.6, ny + 0.3, 2.25 + head_lift * 0.6), 0.42),
                    ((nx, ny, nz), 0.36)], 2)
    feet = []
    for side in (-1, 1):
        hip = s.add((side * 0.6, 1.55, 0.95), 0.42, pelvis)
        knee = s.chain(hip, [((side * 1.0, 1.25, 0.55), 0.3)], 2)
        ankle = s.chain(knee, [((side * 0.95, 1.65, 0.18), 0.17)], 2)
        foot = s.chain(ankle, [((side * 1.0, 1.3, 0.06), 0.15)], 1)
        feet.append(Vector(s.points[foot]))
        sh = s.add((side * 0.6, 0.35, 1.25), 0.36, chest)
        elbow = s.chain(sh, [((side * 0.95, 0.35, 0.65), 0.24)], 2)
        wrist = s.chain(elbow, [((side * 0.85, -0.05, 0.15), 0.15)], 2)
        foot = s.chain(wrist, [((side * 0.85, -0.3, 0.06), 0.14)], 1)
        feet.append(Vector(s.points[foot]))
    s.build("dragon_body", scales)
    for f in feet:
        for k in range(3):
            tube("claw", [f, f + Vector(((k - 1) * 0.12, -0.25, -0.03))], [0.06, 0.01], horn, sides=5)
    # belly plates down the chest, under the head
    for k in range(5):
        u = k / 4
        p = Vector((0, -0.42 + 0.12 * u, 1.75 - 0.75 * u))
        pl = primitive("uv_sphere", plates, radius=0.42 - 0.08 * u, location=p, segments=16, ring_count=8)
        pl.scale = (1.0, 0.4, 0.36)
        pl.rotation_euler = (0.3, 0, 0)
        smooth(pl)
    # dorsal spikes from the neck down the tail
    spine = [Vector((nx, ny + 0.2, nz + 0.25)), Vector((0, 0.1, 2.25)), Vector((0, 0.5, 2.2)),
             Vector((0, 1.0, 2.0)), Vector((0, 1.6, 1.6)), Vector((0.3, 2.3, 0.95)), Vector((0.45, 3.0, 0.6)),
             Vector((-0.2, 3.5, 0.45))]
    for k in range(len(spine) - 1):
        for j in range(2):
            p = spine[k].lerp(spine[k + 1], j / 2)
            size = 0.32 * (1 - k / len(spine) * 0.7)
            tube("spike", [p - Vector((0, 0, 0.1)), p + Vector((0, size * 0.6, size))], [size * 0.35, 0.01],
                 horn, sides=5)
    # head: skull, snout, a hinged lower jaw, horns
    hb = Vector((nx, ny, nz))
    head_from = set(blib.collection("actor").objects)
    fwd = Vector((math.sin(head_turn), -math.cos(head_turn), -0.4 + head_lift * 1.2)).normalized()
    side_v = Vector((math.cos(head_turn), math.sin(head_turn), 0))
    up_v = side_v.cross(fwd).normalized()
    if up_v.z < 0:
        up_v = -up_v
    skull = primitive("uv_sphere", scales, radius=0.38, location=hb + up_v * 0.08, segments=24, ring_count=12)
    skull.scale = (1.05, 1.0, 0.85)
    smooth(skull)
    s = Skeleton()
    a = s.add(hb + up_v * 0.05, 0.32)
    s.chain(a, [(hb + fwd * 0.55 + up_v * 0.02, 0.24), (hb + fwd * 0.95 - up_v * 0.02, 0.19)], 2)
    s.build("snout", scales)
    hinge = hb - up_v * 0.15 + fwd * 0.05
    jfwd = (fwd * math.cos(jaw) - up_v * math.sin(jaw)).normalized()
    jup = up_v * math.cos(jaw) + fwd * math.sin(jaw)
    s = Skeleton()
    a = s.add(hinge, 0.22)
    s.chain(a, [(hinge + jfwd * 0.5, 0.17), (hinge + jfwd * 0.85, 0.12)], 2)
    s.build("jaw", scales)
    if jaw > 0.2:
        # the open mouth: a glowing throat and gums between the jaws
        mid = hinge + (fwd + jfwd).normalized() * 0.45 + (up_v + jup) * 0.06
        inside = primitive("uv_sphere", mouth, radius=0.22, location=mid, segments=16, ring_count=8)
        inside.scale = (0.9, 1.4, 0.4 + jaw * 0.5)
        inside.rotation_euler = (0.0, 0.0, head_turn)
        g = primitive("uv_sphere", gums, radius=0.25, location=mid - jup * 0.05, segments=12, ring_count=6)
        g.scale = (0.8, 1.2, 0.3)
        g.rotation_euler = (0.0, 0.0, head_turn)
    for k in range(5):
        u = 0.25 + k * 0.17
        for sgn in (-1, 1):
            p_up = hb + fwd * (u * 0.95) - up_v * 0.13 + side_v * sgn * (0.17 - u * 0.06)
            tube("tooth", [p_up, p_up - up_v * 0.1], [0.03, 0.005], horn, sides=4)
            p_lo = hinge + jfwd * (u * 0.85) + jup * 0.1 + side_v * sgn * (0.13 - u * 0.05)
            tube("tooth", [p_lo, p_lo + jup * 0.09], [0.03, 0.005], horn, sides=4)
    for sgn in (-1, 1):
        base = hb + side_v * sgn * 0.22 + up_v * 0.25 - fwd * 0.05
        tube("horn", [base, base - fwd * 0.3 + up_v * 0.12 + side_v * sgn * 0.2,
                      base - fwd * 0.65 + up_v * 0.1 + side_v * sgn * 0.38,
                      base - fwd * 0.85 - up_v * 0.05 + side_v * sgn * 0.42], [0.1, 0.07, 0.04, 0.01], horn, sides=8)

        tube("horn2", [base - fwd * 0.1 - up_v * 0.15 + side_v * sgn * 0.08,
                       base - fwd * 0.45 - up_v * 0.05 + side_v * sgn * 0.32], [0.06, 0.01], horn, sides=6)
        ep = hb + fwd * 0.38 + up_v * 0.17 + side_v * sgn * 0.2
        if eyes_open:
            e = primitive("uv_sphere", eye, radius=0.075, location=ep, segments=10, ring_count=6)
            e.scale = (1.3, 1.0, 0.6)
        brow = primitive("uv_sphere", scales, radius=0.11, location=ep + up_v * 0.06 - fwd * 0.02,
                         segments=10, ring_count=6)
        brow.scale = (1.5, 1.2, 0.55)
        brow.rotation_euler = (0, sgn * 0.35, head_turn)
        smooth(brow)
        tube("nose_horn", [hb + fwd * 0.85 + up_v * 0.12 + side_v * sgn * 0.08,
                           hb + fwd * 0.9 + up_v * 0.3 + side_v * sgn * 0.12], [0.04, 0.005], horn, sides=5)
    # the head is modelled small and scaled up about its base: a big readable face
    for ob in set(blib.collection("actor").objects) - head_from:
        ob.location = hb + (ob.location - hb) * 1.45
        ob.scale = ob.scale * 1.45
    # wings: arm, fingers and a scalloped membrane, half spread over the back
    for sgn in (-1, 1):
        lift = wing_up
        S = Vector((sgn * 0.45, 0.55, 1.95))
        W = Vector((sgn * (1.5 + wing_spread * 0.6), 0.9 - wing_spread * 0.3, 3.4 + lift * 1.2))
        tips = [Vector((sgn * (2.55 + wing_spread), 1.2, 3.35 + lift * 1.6)),
                Vector((sgn * (2.7 + wing_spread), 1.55, 2.2 + lift * 1.3)),

                Vector((sgn * (2.2 + wing_spread * 0.7), 1.85, 1.15 + lift * 0.8)),
                Vector((sgn * 1.45, 2.0, 0.75 + lift * 0.4))]
        B = Vector((sgn * 0.45, 1.6, 1.45))
        ring = []
        for i, tp in enumerate(tips):
            ring.append(tp)
            nxt = tips[i + 1] if i + 1 < len(tips) else B
            ring.append(tp.lerp(nxt, 0.5).lerp(W, 0.22))
        ring.append(B)
        faces = [(1, 2 + i, 3 + i) for i in range(len(ring) - 1)]
        faces += [(1, 2 + len(ring) - 1, 0), (0, 1, 2)]
        mem = blib.mesh_object("membrane", [S, W] + ring, faces, wing)
        mem.modifiers.new("solid", "SOLIDIFY").thickness = 0.03
        tube("wing_arm", [S, S.lerp(W, 0.5) + Vector((0, -0.1, 0.15)), W], [0.16, 0.12, 0.1], scales, sides=8)
        for tp in tips:
            tube("finger", [W, W.lerp(tp, 0.5) + Vector((0, -0.05, 0.05)), tp], [0.07, 0.05, 0.015], scales, sides=6)
        tube("thumb", [W, W + Vector((sgn * 0.05, -0.2, 0.25))], [0.06, 0.01], horn, sides=5)
    shift(0.0, 0.75, 0.0, scale=0.92)
    if silhouette is not None:
        return
    if pose == "hurt" and t < 0.5:
        blib.point((0, -2.0, 2.0), (1.0, 0.2, 0.1), 900, radius=0.5, col="actor")
    if pose == "roar":
        blib.point(hinge + fwd * 0.7, (1.0, 0.45, 0.1), 40 + 60 * jaw, radius=0.3, col="actor")


def report_bounds(name, w, h):
    """Prints how far the posed creature reaches in sprite pixels, so nothing gets clipped."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    xs, ys = [], []
    for ob in blib.collection("actor").objects:
        if ob.type != "MESH":
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        for v in list(me.vertices)[::3]:
            c = world_to_camera_view(sc, sc.camera, ev.matrix_world @ v.co)
            xs.append(c.x * w)
            ys.append((1 - c.y) * h)
        ev.to_mesh_clear()
    print(f"BOUNDS {name}: x {min(xs):.0f}..{max(xs):.0f} of {w}, y {min(ys):.0f}..{max(ys):.0f} of {h}")


# ---------------------------------------------------------------------------
#   rendering
# ---------------------------------------------------------------------------

SPRITES = {
    # name: (frames, w, h, builder(frame, frames))
    "utopiec_walk": (6, 56, 60, lambda f, n: utopiec(f / n)),
    "jaga": (6, 60, 64, lambda f, n: jaga(f / n)),
    "jaga_cast": (4, 60, 64, lambda f, n: jaga(f / n, cast=True)),
    "dragon_idle": (6, 112, 88, lambda f, n: dragon("idle", f / n)),
    "dragon_roar": (4, 112, 88, lambda f, n: dragon("roar", f / n)),
    "dragon_hurt": (2, 112, 88, lambda f, n: dragon("hurt", f / n)),
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
            report_bounds(f"{name}_{f}", w, h)
            blib.render(out / f"{name}_{f}.png")
