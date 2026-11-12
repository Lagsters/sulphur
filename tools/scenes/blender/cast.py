"""The cast of the scenes, rendered in Blender: side-view figures facing right (walk cycles and
poses), busts for close-ups (still, talking, blinking), the dragon, the sheep and the props.

    blender -b --factory-startup -P cast.py -- <outdir> [name ...]

Writes <outdir>/<name>_<frame>.png at twice the final size and <outdir>/<name>.json with the
hotspot and, for walkers, the ground covered by one walk cycle. Figures are 64 px a metre at the
final size; the C player mirrors them with a negative drawing scale when they face left.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from kit import RAD, ball, box, cyl, empty, limb, mat  # noqa: E402

PX_M = 64          # final pixels a metre
SS = 2             # rendered at twice the final size, downscaled by make.py
OUT = "."


def shade(h, k):
    h = h.lstrip("#")
    return "#" + "".join(f"{min(255, int(int(h[i:i + 2], 16) * k)):02x}" for i in (0, 2, 4))


def swing(o, deg):
    """Turns a joint about the depth axis; positive swings what hangs below it forward (+x)."""
    o.rotation_euler = (o.rotation_euler[0], -deg * RAD, o.rotation_euler[2])


# ---------------------------------------------------------------------------
#   people
# ---------------------------------------------------------------------------

def face(head, sp, r):
    """Eyes, brows, nose and mouth on a head of radius r facing +x; returns (mouth, lids)."""
    skin = mat(sp["skin"], 0.55)
    white = mat("#f4f0e8", 0.3)
    iris = mat(sp.get("eyes", "#3a2a1a"), 0.2)
    lids = []
    for y in (-0.42 * r, 0.42 * r):
        ball(0.2 * r, (0.8 * r, y, 0.2 * r), white, head, seg=12)
        ball(0.11 * r, (0.97 * r, y, 0.2 * r), iris, head, seg=10)
        lid = ball(0.235 * r, (0.8 * r, y, 0.2 * r), skin, head, seg=12)
        lid.hide_render = True
        lids.append(lid)
        box((0.06 * r, 0.32 * r, 0.06 * r), (0.9 * r, y, 0.45 * r), mat(sp.get("brows", sp.get("hair", "#402010"))), head)
    nose = sp.get("nose", 1.0)
    cyl(0.25 * r * nose, 0.05 * r, 0.55 * r * nose, (1.0 * r + 0.2 * r * nose, 0, -0.05 * r), skin, head,
        rot=(0, 90 + sp.get("nose_tilt", 15), 0), verts=12)
    mouth = ball(0.22 * r, (0.86 * r, 0, -0.5 * r), mat("#5a1a14", 0.4), head, scale=(0.5, 1.3, 0.3), seg=12)
    return mouth, lids


def hat(head, sp, r):
    kind = sp.get("hat")
    if kind == "cap":           # the shoemaker's soft cap, its tip flopping back
        c = mat(sp["cap"], 0.7, noise=0.3, scale=20)
        ball(r * 1.1, (-0.12 * r, 0, 0.55 * r), c, head, scale=(1.08, 1.02, 0.55))
        ball(r * 0.5, (-0.95 * r, 0, 0.35 * r), c, head)
        ball(r * 0.3, (-1.3 * r, 0, 0.05 * r), c, head)
    elif kind == "beret":       # the herald's beret and feather
        ball(r * 1.25, (0, 0, 0.75 * r), mat(sp["cap"], 0.6), head, scale=(1.1, 1.1, 0.35))
        ball(r * 0.9, (-0.9 * r, 0, 1.5 * r), mat("#f0f0f0", 0.6), head, scale=(1.4, 0.15, 0.3), rot=(0, -35, 0))
    elif kind == "crown":
        gold = mat("#e0b040", 0.25, 1.0)
        cyl(r * 0.95, r * 1.05, r * 0.6, (0, 0, 0.95 * r), gold, head)
        for k in range(6):
            a = k * 60 * RAD
            cyl(r * 0.18, 0, r * 0.45, (math.cos(a) * r, math.sin(a) * r, 1.45 * r), gold, head, verts=8)
        ball(r * 0.12, (r * 1.02, 0, 0.95 * r), mat("#c01818", 0.2), head)
    elif kind == "circlet":
        cyl(r * 1.03, r * 1.03, r * 0.18, (0, 0, 0.5 * r), mat("#e8c050", 0.25, 1.0), head, rot=(0, -12, 0))
    elif kind == "witch":
        black = mat("#1a1420", 0.7)
        cyl(r * 2.0, r * 2.0, r * 0.1, (0, 0, 0.75 * r), black, head, rot=(0, 8, 0))
        cyl(r * 0.95, 0.0, r * 2.6, (-0.4 * r, 0, 2.0 * r), black, head, rot=(0, -22, 0))
    elif kind == "scarf":       # Baba Jaga's headscarf, knotted under the chin
        c = mat(sp["cap"], 0.8, noise=0.35, scale=15)
        ball(r * 1.1, (-0.42 * r, 0, 0.2 * r), c, head, scale=(1.0, 1.08, 1.1))
        ball(r * 0.6, (0.1 * r, 0, 0.75 * r), c, head, scale=(1.4, 1.6, 0.6))
        ball(r * 0.25, (0.4 * r, 0, -1.05 * r), c, head)


def hair(head, sp, r):
    h = sp.get("hair")
    if not h:
        return
    m = mat(h, 0.75, noise=0.4, scale=25)
    ball(r * 1.0, (-0.32 * r, 0, 0.22 * r), m, head, scale=(0.95, 1.06, 1.0))
    if sp.get("braid"):
        for k in range(6):
            ball(r * (0.32 - k * 0.025), (-0.95 * r - k * 0.03, 0, -0.6 * r - k * 0.55 * r), m, head)
    if sp.get("long_hair"):     # Jaga's grey wisps, utopiec's weed
        for k in range(7):
            z = -0.2 * r - (k % 3) * 0.1
            cyl(0.1 * r, 0.03 * r, 1.4 * r, (-0.7 * r + k * 0.1 * r, (k - 3) * 0.28 * r, z - 0.6 * r), m, head,
                rot=(0, -8 + k * 3, 0), verts=6)
    if sp.get("beard"):
        b = mat(sp["beard"], 0.8, noise=0.3, scale=20)
        cyl(0.8 * r, 0.12 * r, 2.4 * r, (0.55 * r, 0, -1.5 * r), b, head, rot=(0, 12, 0))
        ball(0.5 * r, (0.95 * r, 0, -0.35 * r), b, head, scale=(0.6, 1.4, 0.4))


def person(sp):
    """A figure facing +x with its feet at the origin; returns its joints."""
    s = sp.get("height", 1.75) / 1.75
    r = 0.115 * s * sp.get("head", 1.0)
    skin = mat(sp["skin"], 0.55)
    near = lambda c: mat(c, 0.6, noise=0.25, scale=12)          # noqa: E731
    far = lambda c: mat(shade(c, 0.62), 0.6, noise=0.25, scale=12)  # noqa: E731
    root = empty((0, 0, 0), name="root")
    pelvis = empty((0, 0, 0.92 * s), root, "pelvis")
    tunic = sp["tunic"]
    b = sp.get("build", 1.0)
    ball(0.2 * s, (0, 0, 0.3 * s), near(tunic), pelvis, scale=(0.82 * b, 1.1 * b, 1.5))
    cyl(0.16 * s, 0.17 * s, 0.25 * s, (0, 0, 0.08 * s), near(tunic), pelvis, scale=(1, 1.15, 1))
    if sp.get("belly"):
        ball(0.2 * s, (0.05 * s, 0, 0.12 * s), near(tunic), pelvis, scale=(1, 0.8, 1))
    if sp.get("skirt", True) and not sp.get("dress"):
        cyl(0.24 * s, 0.17 * s, 0.3 * s, (0, 0, -0.07 * s), near(tunic), pelvis, scale=(1, 0.8, 1))
    if sp.get("belt"):
        cyl(0.175 * s, 0.175 * s, 0.05 * s, (0, 0, 0.03 * s), mat(sp["belt"], 0.35, 0.3), pelvis, scale=(1, 0.75, 1))
    if sp.get("apron"):
        cyl(0.26 * s, 0.18 * s, 0.5 * s, (0.03 * s, 0, -0.12 * s), near(sp["apron"]), pelvis, scale=(1, 0.95, 1))
    if sp.get("collar"):
        ball(0.2 * s, (0, 0, 0.52 * s), mat(sp["collar"], 0.9, noise=0.4, scale=40), pelvis, scale=(1.1, 1.1, 0.4))
    if sp.get("cape"):
        box((0.05 * s, 0.36 * s, 0.95 * s), (-0.19 * s, 0, 0.1 * s), far(sp["cape"]), pelvis, rot=(0, 8, 0))
    if sp.get("dress"):
        dress = cyl(0.36 * s, 0.17 * s, 0.9 * s, (0, 0, -0.43 * s), near(sp["dress"]), pelvis)
        dress.name = "dress"
    cyl(0.05 * s, 0.055 * s, 0.12 * s, (0.01, 0, 0.6 * s), skin, pelvis)
    head = empty((0.02 * s, 0, 0.71 * s), pelvis, "head")
    ball(r, (0, 0, 0), skin, head, scale=(1.0, 0.92, 1.12))
    ball(0.28 * r, (-0.05 * r, -0.95 * r, 0.05 * r), skin, head)     # the near ear
    mouth, lids = face(head, sp, r)
    hair(head, sp, r)
    hat(head, sp, r)
    rig = {"root": root, "pelvis": pelvis, "head": head, "mouth": mouth, "lids": lids, "s": s}
    sleeve = sp.get("sleeve", tunic)
    for side, y, m in (("n", -0.215, near), ("f", 0.215, far)):
        sh = empty((0, y * s, 0.5 * s), pelvis, "sh" + side)
        limb(0.056 * s, 0.047 * s, 0.3 * s, m(sleeve), sh)
        el = empty((0, 0, -0.3 * s), sh, "el" + side)
        limb(0.047 * s, 0.04 * s, 0.26 * s, m(sleeve), el)
        hand = ball(0.047 * s, (0, 0, -0.29 * s), mat(sp["skin"] if side == "n" else shade(sp["skin"], 0.7), 0.55), el)
        rig["sh" + side], rig["el" + side], rig["hand" + side] = sh, el, hand
        hip = empty((0, y * 0.42 * s, 0), pelvis, "hip" + side)
        limb(0.075 * s, 0.06 * s, 0.43 * s, m(sp["legs"]), hip)
        kn = empty((0, 0, -0.43 * s), hip, "kn" + side)
        limb(0.06 * s, 0.046 * s, 0.43 * s, m(sp["legs"]), kn)
        cyl(0.064 * s, 0.056 * s, 0.2 * s, (0, 0, -0.34 * s), m(sp["boots"]), kn)
        an = empty((0, 0, -0.44 * s), kn, "an" + side)
        box((0.2 * s, 0.085 * s, 0.07 * s), (0.05 * s, 0, 0.0), m(sp["boots"]), an)
        rig["hip" + side], rig["kn" + side], rig["an" + side] = hip, kn, an
    return rig


def pose(rig, legs=(0, 0), knees=(0, 0), arms=(0, 0), elbows=(15, 15), bob=0.0, lean=0.0, head=0.0):
    for side, k in (("n", 0), ("f", 1)):
        swing(rig["hip" + side], legs[k])
        swing(rig["kn" + side], -knees[k])
        swing(rig["an" + side], -(legs[k] - knees[k]))
        swing(rig["sh" + side], arms[k])
        swing(rig["el" + side], elbows[k])
    rig["pelvis"].location.z = 0.92 * rig["s"] + bob
    swing(rig["pelvis"], -lean)
    swing(rig["head"], -head)


def walk(rig, p, amp=25):
    a = 2 * math.pi * p

    def knee(ph):
        return 5 + 50 * max(0.0, math.cos(ph)) ** 1.5
    pose(rig, legs=(amp * math.sin(a), amp * math.sin(a + math.pi)),
         knees=(knee(a), knee(a + math.pi)),
         arms=(-0.8 * amp * math.sin(a), -0.8 * amp * math.sin(a + math.pi)),
         elbows=(15 + 10 * max(0, -math.sin(a)), 15 + 10 * max(0, math.sin(a))),
         bob=0.022 * math.cos(2 * a) - 0.01, lean=4)


def stride_px(amp, s):
    """Ground covered by one walk cycle (two steps) in final pixels."""
    return round(2 * 2 * 0.86 * s * math.sin(amp * RAD) * PX_M)


# ---------------------------------------------------------------------------
#   cameras, lights and rendering
# ---------------------------------------------------------------------------

def lights(rim=True):
    kit.world_color("#4a5060", 0.9)
    kit.sun((55, 0, -35), 3.6, "#fff0d8", 6)
    if rim:
        kit.sun((-60, 0, 140), 3.0, "#a8c0ff", 6)
    kit.sun((80, 0, 70), 0.8, "#ffd0a0", 20)


def side_camera(w, h, ground=4, cx=0.0):
    """Ortho side view, w x h final pixels, the ground `ground` px above the bottom edge."""
    zc = (h / 2 - ground) / PX_M
    kit.camera((cx, -20, zc), (cx, 0, zc), ortho=max(w, h) / PX_M)


def shoot(name, frames, w, h, hot, extra=None):
    """Renders frames (callables that pose the scene) as <name>_<k>.png."""
    for k, f in enumerate(frames):
        f()
        kit.render(os.path.join(OUT, f"{name}_{k}.png"), w * SS, h * SS)
    meta = {"frames": len(frames), "w": w, "h": h, "hot": hot}
    meta.update(extra or {})
    with open(os.path.join(OUT, f"{name}.json"), "w") as fh:
        json.dump(meta, fh)


def busts(name, rig, size=160, ortho=0.62, yaw=38, drop=0.1, mouth_open=3.2, after=None):
    """A close-up, the face three quarters to the right: still, talking, blinking."""
    for o in list(kit.bpy.data.objects):
        if o.type == "CAMERA":
            kit.bpy.data.objects.remove(o)
    pose(rig, elbows=(10, 10), arms=(5, -5))
    if after:
        after()
    hz = rig["head"].matrix_world.translation.z
    look = (0.05, 0, hz - drop)
    d = 6.0
    kit.camera((look[0] + d * math.sin(yaw * RAD), -d * math.cos(yaw * RAD), look[2] + 0.4), look, ortho=ortho)
    mouth, lids = rig["mouth"], rig["lids"]
    sc = tuple(mouth.scale)

    def still():
        mouth.scale = sc
        for lid in lids:
            lid.hide_render = True

    def talk():
        mouth.scale = (sc[0] * 1.3, sc[1], sc[2] * mouth_open)

    def blink():
        mouth.scale = sc
        for lid in lids:
            lid.hide_render = False
    shoot(name, [still, talk, blink], size, size, [size // 2, size - 1])


PEOPLE = {
    "dratewka": dict(skin="#e8b08a", tunic="#5f7a34", legs="#6a4428", boots="#3a2414", apron="#9a6a3a",
                     hat="cap", cap="#c02a1e", hair="#6a3a18", belt="#3a2414"),
    "wanda": dict(skin="#f2c4a0", tunic="#2a56b0", dress="#2a56b0", legs="#2a56b0", boots="#5a3020",
                  hair="#e8c050", braid=True, hat="circlet", belt="#e0b040", height=1.66, eyes="#2050a0",
                  brows="#a07020", sleeve="#e8e0d0"),
    "herald": dict(skin="#e0a888", tunic="#c02828", sleeve="#e0b020", legs="#e0b020", boots="#2a1a10",
                   hat="beret", cap="#20286a", hair="#2a1a10", belt="#2a1a10"),
    "krak": dict(skin="#e8b898", tunic="#902020", dress="#902020", legs="#902020", boots="#3a2010",
                 hat="crown", hair="#e8e8e8", beard="#f0f0f0", brows="#d0d0d0", collar="#f4f0ea",
                 cape="#6a1418", belly=True, build=1.15, nose=1.2),
    "witch": dict(skin="#8aa868", tunic="#3a2050", legs="#3a2050", boots="#1a1010", hat="witch",
                  hair="#202020", long_hair=True, cape="#2a1838", nose=1.7, nose_tilt=-10, eyes="#c0d020"),
    "jaga": dict(skin="#c8a080", tunic="#4a3a5a", legs="#4a3a5a", boots="#1a1010", hat="scarf",
                 cap="#a83030", hair="#b0b0a8", long_hair=True, nose=2.0, nose_tilt=-18, eyes="#80a020",
                 brows="#909088"),
    "utopiec": dict(skin="#4a8a70", tunic="#3a6a50", legs="#4a8a70", boots="#4a8a70", skirt=False,
                    hair="#2a5a30", long_hair=True, eyes="#e0d030", nose=0.6, head=1.25, belly=True,
                    sleeve="#4a8a70", brows="#2a4a30"),
}


def build_person(name, overrides=None):
    kit.reset()
    kit.outline(2.4)
    lights()
    sp = dict(PEOPLE[name])
    sp.update(overrides or {})
    return person(sp), sp


def walker(name, extra_poses=(), amp=25, bust=True, w=96, h=136, overrides=None, bust_name=None):
    rig, sp = build_person(name, overrides)
    if sp.get("dress"):
        amp = 18
    side_camera(w, h)
    frames = [lambda k=k: walk(rig, k / 8, amp) for k in range(8)]
    frames += [lambda p=p: pose(rig, **p) for p in extra_poses]
    shoot(name, frames, w, h, [w // 2, h - 5], {"stride": stride_px(amp, rig["s"])})
    if bust:
        busts(bust_name or "bust_" + name, rig)


def dratewka():
    walker("dratewka", extra_poses=[
        dict(),                                                     # 8 stands
        dict(arms=(-150, 10), elbows=(40, 15), lean=-6, legs=(-12, 10)),   # 9 winds up a throw
        dict(arms=(100, -20), elbows=(5, 15), lean=8, legs=(14, -14)),    # 10 throws
        dict(arms=(30, 25), elbows=(70, 70), head=-8),              # 11 works at the bench
    ])
    rig, sp = build_person("dratewka", dict(skin="#6a5448", cap="#3a2420", hair="#1a1410", tunic="#2a3020",
                                            apron="#3a2a20", brows="#101010"))
    busts("bust_dratewka_soot", rig)


def wanda():
    walker("wanda", extra_poses=[dict(), dict(arms=(-5, 5), elbows=(0, 0), head=12)])


def herald():
    rig, sp = build_person("herald")
    # the hammer in the near hand: handle along the forearm's hand, head at its end
    wood, iron = mat("#7a5030", 0.6), mat("#505860", 0.3, 0.8)
    hand = rig["handn"]
    cyl(0.018, 0.018, 0.32, (0.13, 0, -0.29), wood, rig["eln"], rot=(0, 90, 0), verts=8)
    box((0.06, 0.06, 0.14), (0.28, 0, -0.29), iron, rig["eln"])
    side_camera(96, 136)
    frames = [lambda k=k: walk(rig, k / 8, 25) for k in range(8)]
    frames += [lambda: pose(rig, arms=(170, 30), elbows=(40, 15)),   # 8 hammer up
               lambda: pose(rig, arms=(85, 30), elbows=(30, 15))]    # 9 hammer down
    shoot("herald", frames, 96, 136, [48, 131], {"stride": stride_px(25, rig["s"])})
    del hand


def krak():
    rig, sp = build_person("krak")
    gold = mat("#e0b040", 0.25, 1.0)
    cyl(0.02, 0.02, 1.3, (0.0, 0, -0.35), gold, rig["handf"], rot=(0, 0, 0), verts=8)   # the sceptre
    ball(0.05, (0.0, 0, 0.32), gold, rig["handf"])
    side_camera(96, 136)
    frames = [lambda: pose(rig, arms=(10, 45), elbows=(20, 50)),                  # 0 stands
              lambda: pose(rig, arms=(75, 45), elbows=(10, 50), head=-5)]        # 1 offers
    shoot("krak", frames, 96, 136, [48, 131])
    busts("bust_krak", rig, ortho=0.9, drop=0.2)


def witch():
    """Riding a broom: sitting, cape and hat; two frames of a bobbing ride."""
    rig, sp = build_person("witch")
    wood = mat("#6a4a2a", 0.7)
    straw = mat("#b09040", 0.9, noise=0.4, scale=30)
    broom = empty((0, 0, 0.82), rig["root"], "broom")
    cyl(0.025, 0.025, 1.7, (0.15, 0, 0), wood, broom, rot=(0, 90, 0), verts=8)
    cyl(0.03, 0.17, 0.5, (-0.85, 0, 0), straw, broom, rot=(0, -90, 0), verts=14)
    side_camera(140, 120, ground=-30, cx=-0.1)
    frames = []
    for k in range(2):
        def f(k=k):
            pose(rig, legs=(80, 75), knees=(85, 80), arms=(70, 60), elbows=(25, 25), lean=10, bob=-0.05,
                 head=4 * k)
            broom.rotation_euler = (0, (-6 + 8 * k) * RAD, 0)
        frames.append(f)
    shoot("witch", frames, 140, 120, [70, 60])


def jaga():
    """Baba Jaga in her mortar, rowing the air with the pestle; and her bust."""
    rig, sp = build_person("jaga")
    wood = mat("#7a5a3a", 0.7, noise=0.5, scale=6, color2="#3a2818")
    m = cyl(0.42, 0.3, 0.75, (0.0, 0, 0.55), wood, rig["root"])
    cyl(0.4, 0.4, 0.02, (0, 0, 0.93), mat("#1a1008", 0.9), rig["root"])
    pestle = empty((0, 0, 0), rig["handn"], "pestle")
    cyl(0.03, 0.05, 1.2, (0.0, 0, -0.1), mat("#8a6a4a", 0.6), pestle, rot=(0, 0, 0), verts=8)
    ball(0.08, (0, 0, -0.68), mat("#8a6a4a", 0.6), pestle)
    side_camera(128, 136, ground=-10)
    frames = []
    for k in range(2):
        def f(k=k):
            pose(rig, legs=(0, 0), arms=(60 + 50 * k, 30), elbows=(30, 40), lean=-5 + 10 * k, bob=0.1)
            pestle.rotation_euler = (0, (40 - 50 * k) * RAD, 0)
            m.rotation_euler = (0, (-4 + 8 * k) * RAD, 0)
        frames.append(f)
    shoot("jaga", frames, 128, 136, [64, 68])
    pestle.hide_render = True
    busts("bust_jaga", rig)


def utopiec():
    rig, sp = build_person("utopiec")
    weed = mat("#2a5a30", 0.8)
    for k in range(5):
        cyl(0.04, 0.01, 0.35, (0.0, (k - 2) * 0.07, -0.25), weed, rig["pelvis"], rot=(0, (k - 2) * 6, 0), verts=6)
    side_camera(112, 144)
    frames = [lambda: pose(rig, arms=(165, 150), elbows=(20, 25), head=-10, lean=-4),
              lambda: pose(rig, arms=(120, 100), elbows=(40, 45), head=0, lean=6)]
    shoot("utopiec", frames, 112, 144, [56, 139])
    busts("bust_utopiec", rig, ortho=0.9, drop=0.12)


# ---------------------------------------------------------------------------
#   the dragon and the sheep
# ---------------------------------------------------------------------------

def dragon_model():
    kit.reset()
    kit.outline(2.6)
    lights()
    green = mat("#3e7034", 0.5, noise=0.5, scale=10, color2="#1e3a1a")
    belly = mat("#c8a454", 0.6, noise=0.3, scale=14)
    horn = mat("#e8dcc0", 0.4)
    wingm = mat("#7a2e22", 0.7, noise=0.4, scale=6, color2="#4a1810")
    root = empty((0, 0, 0), name="root")
    body = empty((0, 0, 1.6), root, "body")
    ball(1.0, (0, 0, 0), green, body, scale=(1.7, 0.85, 0.85))
    ball(0.85, (-0.05, 0, -0.18), belly, body, scale=(1.75, 0.8, 0.75))
    ball(0.8, (1.1, 0, 0.15), green, body, scale=(1.0, 0.85, 0.95))
    for k in range(7):                                   # spikes along the back
        cyl(0.13, 0, 0.35, (1.2 - k * 0.45, 0, 0.9 - abs(k - 2) * 0.05), horn, body, rot=(0, -20, 0), verts=8)
    neck = []
    parent = body
    loc = (1.6, 0, 0.45)
    for k in range(4):
        j = empty(loc, parent, f"neck{k}")
        ball(0.5 - k * 0.06, (0.35, 0, 0), green, j, scale=(1.2, 0.9, 1))
        cyl(0.08, 0, 0.25, (0.3, 0, 0.45 - k * 0.05), horn, j, rot=(0, -25, 0), verts=8)
        neck.append(j)
        parent, loc = j, (0.55, 0, 0)
    headp = empty((0.6, 0, 0), parent, "head")
    ball(0.42, (0.15, 0, 0.05), green, headp, scale=(1.3, 0.85, 0.9))
    box((0.8, 0.42, 0.28), (0.65, 0, 0.0), green, headp, rot=(0, 8, 0))
    eye = mat("#f0d020", 0.2, emit="#f0b000", strength=2.0)
    ball(0.08, (0.4, -0.3, 0.22), eye, headp)
    ball(0.035, (0.46, -0.36, 0.22), mat("#100000"), headp)
    for y in (-0.18, 0.18):
        cyl(0.09, 0, 0.6, (-0.3, y, 0.45), horn, headp, rot=(0, -60, 0), verts=10)
    jaw = empty((0.05, 0, -0.12), headp, "jaw")
    box((0.75, 0.36, 0.12), (0.4, 0, -0.06), green, jaw)
    box((0.7, 0.3, 0.05), (0.4, 0, 0.02), mat("#a02020", 0.5), jaw)
    for k in range(5):
        cyl(0.03, 0, 0.09, (0.15 + k * 0.14, -0.15, 0.08), horn, jaw, verts=6)
        cyl(0.03, 0, 0.09, (0.25 + k * 0.14, -0.15, -0.1), horn, headp, rot=(180, 0, 0), verts=6)
    tail = []
    parent, loc = body, (-1.5, 0, 0.1)
    for k in range(8):
        j = empty(loc, parent, f"tail{k}")
        ball(0.42 - k * 0.045, (-0.3, 0, 0), green, j, scale=(1.3, 0.9, 1))
        tail.append(j)
        parent, loc = j, (-0.45, 0, 0)
    cyl(0.32, 0, 0.6, (-0.4, 0, 0), horn, parent, rot=(0, -90, 0), scale=(1, 0.2, 1), verts=4)
    legs = {}
    for name, x, y in (("fn", 0.9, -0.5), ("ff", 0.9, 0.5), ("bn", -0.9, -0.5), ("bf", -0.9, 0.5)):
        m = green if y < 0 else mat("#2a4e24", 0.5)
        hip = empty((x, y, -0.3), body, "leg" + name)
        limb(0.3, 0.22, 0.6, m, hip)
        kn = empty((0, 0, -0.6), hip, "kn" + name)
        limb(0.2, 0.16, 0.6, m, kn)
        for c in (-0.12, 0, 0.12):
            cyl(0.06, 0, 0.25, (0.2, c, -0.62), horn, kn, rot=(0, 110, 0), verts=6)
        legs[name] = (hip, kn)
    wings = {}
    tips = [(0.0, 0.0), (0.6, 1.4), (0.4, 3.1), (-0.2, 2.3), (-0.8, 2.9), (-1.0, 1.9), (-1.8, 2.5), (-1.7, 1.4),
            (-2.5, 1.5), (-1.6, 0.3)]
    for side, sgn, m in (("n", -1, wingm), ("f", 1, mat("#5a2018", 0.7))):
        piv = empty((0.6, 0.45 * sgn, 0.6), body, "wing" + side)
        verts = [(x, sgn * yy, 0) for (x, yy) in tips]
        faces = [(0, k, k + 1) for k in range(1, len(tips) - 1)]
        kit.mesh(verts, faces, m, piv, smooth=False)
        wings[side] = (piv, sgn)
    return dict(root=root, body=body, neck=neck, head=headp, jaw=jaw, tail=tail, legs=legs, wings=wings)


def dragon_pose(d, wing=60, neck=(25, 10, -10, -20), head=-10, jaw=0, legs=None, tail=(-10, 5, 8, 5, 0, -5, -8, -5)):
    for k, j in enumerate(d["neck"]):
        swing(j, 0)
        j.rotation_euler = (0, -neck[k] * RAD, 0)
    d["head"].rotation_euler = (0, -head * RAD, 0)
    d["jaw"].rotation_euler = (0, jaw * RAD, 0)
    for k, j in enumerate(d["tail"]):
        j.rotation_euler = (0, -tail[k] * RAD, 0)
    for side, (piv, sgn) in d["wings"].items():
        piv.rotation_euler = (sgn * wing * RAD, -15 * RAD, 0)
    legs = legs or {"fn": (0, 0), "ff": (0, 0), "bn": (0, 0), "bf": (0, 0)}
    for name, (a, b) in legs.items():
        hip, kn = d["legs"][name]
        swing(hip, a)
        swing(kn, b)


def dragon():
    d = dragon_model()
    tuck = {"fn": (-60, 80), "ff": (-50, 70), "bn": (-70, 60), "bf": (-60, 50)}
    # flying: four wingbeats; the body level, legs tucked, neck stretched forward
    kit.camera((0.6, -40, 1.9), (0.6, 0, 1.9), ortho=8.4)
    def fly(wing, lift):
        dragon_pose(d, wing=wing, neck=(-5, -8, -8, -5), head=5, legs=tuck, tail=(5, 3, -2, -5, -5, 0, 5, 8))
        d["body"].location.z = 1.6 + lift
    frames = [lambda w=w, l=l: fly(w, l) for (w, l) in ((85, -0.1), (40, 0.0), (-35, 0.12), (20, 0.05))]
    shoot("dragon_fly", frames, 224, 136, [112, 68])
    # on the ground facing right: idle, jaws open (roar, swallow), drinking with the head down
    for o in list(kit.bpy.data.objects):
        if o.type == "CAMERA":
            kit.bpy.data.objects.remove(o)
    kit.camera((0.9, -40, 2.25), (0.9, 0, 2.25), ortho=7.8)
    stand = {"fn": (8, -4), "ff": (-6, -2), "bn": (5, -6), "bf": (-8, 0)}
    frames = [lambda: dragon_pose(d, wing=70, neck=(30, 15, -5, -25), head=-15, legs=stand),
              lambda: dragon_pose(d, wing=80, neck=(40, 20, 0, -30), head=-35, jaw=40, legs=stand),
              lambda: dragon_pose(d, wing=60, neck=(-20, -30, -25, -15), head=-30, jaw=10, legs=stand)]
    shoot("dragon", frames, 224, 205, [112, 200])


def sheep():
    kit.reset()
    kit.outline(2.2)
    lights()
    wool = mat("#ece4cc", 0.95, noise=0.35, scale=18, color2="#b8ae98")
    dark = mat("#2a2420", 0.6)
    darkf = mat("#1a1612", 0.6)
    root = empty((0, 0, 0), name="root")
    body = empty((0, 0, 0.5), root, "body")
    b = ball(0.3, (0, 0, 0), wool, body, scale=(1.45, 0.95, 0.9), seg=32)
    kit.displace(b, 0.05, 0.08, subdiv=1)
    head = empty((0.42, 0, 0.12), body, "head")
    ball(0.12, (0.06, 0, 0), dark, head, scale=(1.45, 0.85, 1.0))
    ball(0.13, (-0.02, 0, 0.06), wool, head, scale=(0.8, 1.0, 0.8))
    ball(0.05, (0.0, -0.11, 0.05), dark, head, scale=(1.6, 0.6, 0.6), rot=(0, 0, 30))
    ball(0.02, (0.1, -0.08, 0.04), mat("#f0e0a0", 0.2), head)
    legs = []
    for name, x, y in (("fn", 0.27, -0.12), ("ff", 0.27, 0.12), ("bn", -0.27, -0.12), ("bf", -0.27, 0.12)):
        hip = empty((x, y, -0.12), body, "leg" + name)
        limb(0.04, 0.03, 0.36, dark if y < 0 else darkf, hip)
        legs.append(hip)
    side_camera(72, 56, ground=3)

    def gait(p):
        a = 2 * math.pi * p
        for k, hip in enumerate(legs):
            ph = a + (math.pi if k in (1, 2) else 0)
            swing(hip, 24 * math.sin(ph))
        body.location.z = 0.5 + 0.015 * math.cos(2 * a)
        head.rotation_euler = (0, 0, 0)
    frames = [lambda k=k: gait(k / 8) for k in range(8)]

    def graze(k):
        for hip in legs:
            swing(hip, 0)
        head.rotation_euler = (0, (55 + 6 * k) * RAD, 0)
        head.location = (0.4, 0, 0.0)
    frames += [lambda: graze(0), lambda: graze(1)]
    shoot("sheep", frames, 72, 56, [36, 52], {"stride": round(4 * 0.36 * math.sin(24 * RAD) * PX_M * 1.0)})


# ---------------------------------------------------------------------------
#   props
# ---------------------------------------------------------------------------

def props():
    kit.reset()
    kit.outline(2.0)
    lights()
    sackm = mat("#b0915a", 0.95, noise=0.45, scale=30, color2="#7a6038")
    s = ball(0.32, (0, 0, 0.32), sackm, scale=(0.9, 0.85, 1.05), seg=32)
    kit.displace(s, 0.04, 0.15, subdiv=1)
    cyl(0.12, 0.07, 0.15, (0, 0, 0.68), sackm)
    cyl(0.1, 0.1, 0.03, (0, 0, 0.62), mat("#4a3020", 0.8))
    ball(0.2, (0.25, 0, 0.0), mat("#e8d030", 0.9, noise=0.4, scale=40), scale=(1.6, 1.2, 0.25))
    side_camera(64, 64, ground=4)
    shoot("sack", [lambda: None], 64, 64, [32, 59])

    kit.reset()
    kit.outline(2.0)
    lights()
    rind = mat("#d89a28", 0.5)
    cheese = mat("#f2d060", 0.6, noise=0.3, scale=20)
    w = cyl(0.3, 0.3, 0.2, (0, 0, 0.1), rind, verts=32)
    cyl(0.29, 0.29, 0.21, (0, 0, 0.1), cheese, verts=32, scale=(1, 1, 0.98))
    for k in range(5):
        ball(0.03, (0.1 * math.cos(k * 1.3), -0.3, 0.06 + 0.02 * k), mat("#c09030"), scale=(1, 0.3, 1))
    kit.camera((0, -10, 2.5), (0, 0, 0.1), ortho=0.9)
    shoot("cheese", [lambda: None], 48, 40, [24, 20])
    del w

    kit.reset()
    kit.outline(2.0)
    lights()
    ball(0.17, (0, 0, 0.17), mat("#3a3430", 0.5, noise=0.3, scale=15))
    cyl(0.175, 0.175, 0.06, (0, 0, 0.2), mat("#e8d030", 0.6))
    cyl(0.012, 0.012, 0.15, (0.04, 0, 0.38), mat("#c0a070"), rot=(0, 20, 0), verts=6)
    side_camera(28, 28, ground=2)
    shoot("bomb", [lambda: None], 28, 28, [14, 14])


JOBS = {"dratewka": dratewka, "wanda": wanda, "herald": herald, "krak": krak, "witch": witch, "jaga": jaga,
        "utopiec": utopiec, "dragon": dragon, "sheep": sheep, "props": props}

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    OUT = args[0]
    os.makedirs(OUT, exist_ok=True)
    for job in args[1:] or list(JOBS):
        JOBS[job]()
