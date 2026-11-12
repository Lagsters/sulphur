"""Figures for the game art: heroes, the dwarf, the bat and the sheep, each a puppet of primitives
on pivots, posed per frame by plain Python (no armatures, no keyframes).

A figure stands at the origin, faces -y, and is about 37 units tall (chibi proportions: a big head
reads at 24x32 pixels from a 55 degree camera).
"""
import math

import blender_lib as L
from blender_lib import box, cylinder, ellipsoid, empty, lathe, mat

SKIN = "#e0a882"
HEAD_TILT = -0.45  # the head looks up a little, or the 55 degree camera sees only the cap

LOOKS = {
    "dratewka": dict(cap="#6e4626", tunic="#d8c49c", legs="#4a3424", boots="#24180f", hair="#4a2c14", apron="#7a4a26"),
    "white": dict(cap="#f0eee8", tunic="#d8d6d0", legs="#4a4440", boots="#24180f", hair="#5a3a1c", belt="#3a2a1a"),
    "green": dict(cap="#3cc048", tunic="#26902e", legs="#3a3428", boots="#24180f", hair="#2a1a10", belt="#3a2a1a"),
    "blue": dict(cap="#4a6cf0", tunic="#2a44c0", legs="#3a3440", boots="#24180f", hair="#6a4420", belt="#3a2a1a"),
    "red": dict(cap="#f04030", tunic="#c02820", legs="#3a2a28", boots="#24180f", hair="#2a1a10", belt="#3a2a1a"),
}


class Rig:
    """Pivots of a two-legged puppet; walk(t) and die(f) pose it."""

    def __init__(self):
        self.root = empty("root")
        self.hips = empty("hips", (0, 0, 11.5), self.root)
        self.torso = empty("torso", (0, 0, 0), self.hips)
        self.legs = [empty(f"leg{s}", (s * 2.4, 0, 0), self.hips) for s in (-1, 1)]
        self.arms = [empty(f"arm{s}", (s * 5.3, 0, 9.8), self.torso) for s in (-1, 1)]
        self.head = empty("head", (0, 0, 12.0), self.torso)
        self.skirt = None
        self.stride, self.arm_swing, self.bob = 0.55, 0.55, 0.7
        self.hip_z = 11.5

    def walk(self, t):
        a = math.sin(2 * math.pi * t)
        self.root.location = (0, 0, 0)
        self.hips.location = (0, 0, self.hip_z - self.bob * abs(a))
        self.hips.rotation_euler = (0, 0, 0.12 * a)
        self.torso.rotation_euler = (0.06 * abs(a), 0, -0.1 * a)
        self.head.rotation_euler = (HEAD_TILT, 0, 0.06 * a)
        for s, leg in zip((1, -1), self.legs):
            leg.rotation_euler = (s * self.stride * a, 0, 0)
        for s, arm in zip((-1, 1), self.arms):
            arm.rotation_euler = (s * self.arm_swing * a, 0, s * -0.12)
        if self.skirt:
            self.skirt.rotation_euler = (0.05 * abs(a), 0.06 * a, 0)

    def die(self, f):
        """0 struck, 1 knees buckle, 2 sits, 3 lies (make.py turns it into sulphur smoke)."""
        self.walk(0)
        hip, lean, arm, leg, head = ((12.0, -0.25, 2.8, 0.0, -0.8),
                                     (8.0, 0.1, 1.8, -0.9, -0.2),
                                     (5.0, 0.35, 0.9, -1.4, 0.2),
                                     (2.5, 0.6, 0.4, -1.5, 0.5))[f]
        self.hips.location = (0, 0, hip)
        self.torso.rotation_euler = (lean, 0, 0)
        self.head.rotation_euler = (head, 0, 0)
        for s, a in zip((-1, 1), self.arms):
            a.rotation_euler = (-arm, 0, s * -0.5)
        for s, l in zip((-1, 1), self.legs):
            l.rotation_euler = (leg, 0, s * 0.15)

    def head_center(self):
        return (0, 0, self.hip_z + 12.0 + 5.5)


def _legs(rig, legs, boots, bone=False):
    lm = mat("legs", legs, rough=0.8, color2=None)
    bm = mat("boots", boots, rough=0.45, spec=0.6)
    for leg in rig.legs:
        if bone:
            cylinder("shin", 0.9, 0.8, 11.0, lm, parent=leg, loc=(0, 0, -11.2), seg=8)
            ellipsoid("knee", (0, 0, -5.5), (1.3, 1.3, 1.3), lm, parent=leg)
            ellipsoid("foot", (0, -1.0, -11.0), (1.4, 2.6, 0.8), lm, parent=leg)
        else:
            ellipsoid("leg", (0, 0, -5.0), (1.8, 1.9, 5.6), lm, parent=leg)
            ellipsoid("boot", (0, -0.9, -10.3), (2.1, 3.0, 1.9), bm, parent=leg)
            ellipsoid("bootcuff", (0, 0, -8.2), (2.2, 2.2, 1.1), bm, parent=leg)


def _arms(rig, sleeve, skin=SKIN, bone=False):
    sm = mat("sleeve", sleeve, rough=0.8)
    hm = mat("hand", skin, rough=0.6)
    for arm in rig.arms:
        if bone:
            cylinder("arm", 0.8, 0.7, 9.0, sm, parent=arm, loc=(0, 0, -9.0), seg=8)
            ellipsoid("hand", (0, -0.3, -9.6), (1.3, 1.3, 1.5), hm, parent=arm)
        else:
            ellipsoid("arm", (0, 0, -4.2), (1.7, 1.7, 4.6), sm, parent=arm)
            ellipsoid("hand", (0, -0.2, -9.0), (1.6, 1.6, 1.7), hm, parent=arm)


def _face(rig, skin=SKIN, eyes="#1a1210"):
    sk = mat("skin", skin, rough=0.55)
    em = mat("eyes", eyes, rough=0.3)
    ellipsoid("headball", (0, 0, 5.5), (6.2, 6.0, 6.0), sk, parent=rig.head)
    for s in (-1, 1):
        ellipsoid("eye", (s * 2.2, -5.5, 5.6), (1.0, 0.7, 1.4), em, parent=rig.head)
        ellipsoid("ear", (s * 6.0, 0.3, 5.0), (0.9, 1.4, 1.6), sk, parent=rig.head)
    ellipsoid("nose", (0, -6.1, 4.2), (1.0, 0.9, 1.0), mat("nose", "#d08868", rough=0.5), parent=rig.head)
    return sk


def shoemaker(look):
    p = LOOKS[look]
    rig = Rig()
    _legs(rig, p["legs"], p["boots"])
    tm = mat("tunic", p["tunic"], rough=0.85, color2=None)
    ellipsoid("body", (0, 0, 5.2), (5.2, 3.8, 6.4), tm, parent=rig.torso)
    ellipsoid("collar", (0, 0, 10.6), (3.6, 3.0, 1.3), tm, parent=rig.torso)
    if "apron" in p:
        leather = mat("apron", p["apron"], rough=0.5, color2="#5a3418", noise_scale=0.8, bump=0.3, spec=0.6)
        ellipsoid("apron", (0, -2.7, 3.2), (4.6, 1.6, 6.8), leather, parent=rig.torso)
        box("strap", (0, -3.2, 8.6), (6.0, 0.8, 0.9), leather, parent=rig.torso, bevel=0.3)
    belt = mat("belt", p.get("belt", "#3a2a1a"), rough=0.6)
    lathe("belt", [(5.3, 1.0), (5.5, 1.6), (5.3, 2.2)], belt, parent=rig.torso, cap=False)
    box("buckle", (0, -5.3, 1.6), (1.8, 0.8, 1.4), mat("buckle", "#d0a840", rough=0.3, metal=1.0), parent=rig.torso)
    _arms(rig, p["tunic"])
    _face(rig)
    hair = mat("hair", p["hair"], rough=0.8)
    ellipsoid("hair", (0, 1.4, 6.0), (6.5, 5.6, 5.8), hair, parent=rig.head)
    cap = mat("cap", p["cap"], rough=0.85, color2=None)
    ellipsoid("cap", (0, 1.2, 9.6), (6.6, 6.4, 3.2), cap, parent=rig.head)
    ellipsoid("brim", (0, -3.4, 9.0), (5.4, 3.0, 0.8), cap, parent=rig.head, rot=(0.15, 0, 0))
    ellipsoid("pom", (0, 2.4, 12.6), (1.5, 1.5, 1.5), cap, parent=rig.head)
    return rig


def wanda():
    rig = Rig()
    rig.stride = 0.35
    red = mat("dress", "#c41c28", rough=0.7, color2="#8a1018", noise_scale=0.6, bump=0.15)
    _legs(rig, "#e0c0a0", "#6a2010")
    skirt = empty("skirtp", (0, 0, 0), rig.hips)
    rig.skirt = skirt
    lathe("skirt", [(7.0, -9.6), (6.4, -6.0), (5.2, -2.0), (4.4, 1.0), (0.0, 1.2)], red, parent=skirt, seg=28)
    gold = mat("gold", "#f0c040", rough=0.3, metal=1.0)
    lathe("hem", [(7.15, -9.7), (7.2, -8.9), (7.0, -8.4)], gold, parent=skirt, seg=28, cap=False)
    ellipsoid("body", (0, 0, 5.0), (4.4, 3.4, 6.0), red, parent=rig.torso)
    lathe("girdle", [(4.5, 0.6), (4.7, 1.3), (4.5, 1.9)], gold, parent=rig.torso, cap=False)
    _arms(rig, "#c41c28")
    _face(rig, eyes="#1a2a40")
    blond = mat("blond", "#e8c050", rough=0.6, color2="#b88a28", noise_scale=1.2, bump=0.3)
    ellipsoid("hair", (0, 1.0, 6.6), (6.6, 6.0, 5.8), blond, parent=rig.head)
    ellipsoid("fringe", (0, -3.0, 9.4), (5.6, 3.0, 2.2), blond, parent=rig.head)
    for i in range(6):
        ellipsoid(f"braid{i}", (0.3 * math.sin(i), 6.4 + 0.3 * i, 3.0 - 2.2 * i), (1.7 - 0.12 * i,) * 3, blond,
                  parent=rig.head)
    ellipsoid("ribbon", (0, 7.6, -10.2), (1.4, 0.8, 1.0), red, parent=rig.head)
    lathe("crown", [(3.6, 10.6), (3.8, 12.4)], gold, parent=rig.head, cap=False, seg=20)
    for i in range(5):
        a = 2 * math.pi * i / 5 - math.pi / 2
        cylinder(f"pt{i}", 0.9, 0.0, 2.4, gold, parent=rig.head, loc=(3.7 * math.cos(a), 3.7 * math.sin(a), 12.2), seg=6)
    ellipsoid("gem", (0, -3.9, 11.6), (0.8, 0.5, 0.8), mat("gem", "#40e0ff", rough=0.1, emit="#40c0ff",
                                                           emit_strength=1.5), parent=rig.head)
    return rig


def skeleton():
    rig = Rig()
    bone = "#e6dcc0"
    _legs(rig, bone, bone, bone=True)
    bm = mat("bone", bone, rough=0.6, color2="#b0a484", noise_scale=1.0, bump=0.2)
    dark = mat("void", "#120c10", rough=1.0)
    ellipsoid("pelvis", (0, 0, 0.6), (3.6, 2.2, 1.8), bm, parent=rig.hips)
    cylinder("spine", 0.9, 0.9, 6.0, bm, parent=rig.torso, loc=(0, 0.6, 0.5), seg=8)
    ellipsoid("ribcore", (0, 0, 7.0), (3.8, 2.8, 3.8), dark, parent=rig.torso)
    for i in range(4):
        z = 4.6 + i * 1.6
        r = 4.2 - abs(i - 1.6) * 0.5
        lathe(f"rib{i}", [(r, z - 0.45), (r + 0.3, z), (r, z + 0.45)], bm, parent=rig.torso, cap=False, seg=18)
    ellipsoid("shoulders", (0, 0, 10.0), (5.6, 2.0, 1.0), bm, parent=rig.torso)
    rag = mat("rag", "#2a2430", rough=0.95, color2="#1a141e", noise_scale=1.0)
    lathe("rag", [(4.4, -4.0), (4.0, -1.0), (3.6, 1.6)], rag, parent=rig.hips, cap=False, seg=10)
    _arms(rig, bone, skin=bone, bone=True)
    ellipsoid("skull", (0, 0, 6.0), (5.6, 5.6, 5.8), bm, parent=rig.head)
    ellipsoid("jaw", (0, -2.2, 1.6), (3.6, 3.0, 2.0), bm, parent=rig.head)
    glow = mat("glow", "#ffe040", emit="#ffd020", emit_strength=6.0)
    for s in (-1, 1):
        ellipsoid("socket", (s * 2.3, -4.6, 5.8), (1.9, 1.2, 2.0), dark, parent=rig.head)
        ellipsoid("pupil", (s * 2.3, -5.4, 5.6), (0.8, 0.5, 0.8), glow, parent=rig.head)
    ellipsoid("nosehole", (0, -5.4, 3.6), (0.6, 0.5, 0.7), dark, parent=rig.head)
    for i in range(4):
        box(f"tooth{i}", (-1.5 + i, -4.6, 1.5), (0.6, 0.4, 0.9), dark, parent=rig.head)
    return rig


def hero(look):
    if look == "wanda":
        return wanda()
    if look == "skeleton":
        return skeleton()
    return shoemaker(look)


# ---------------------------------------------------------------------------
#   monsters and the sheep
# ---------------------------------------------------------------------------

def dwarf():
    rig = Rig()
    rig.hip_z = 5.5
    rig.hips.location = (0, 0, 5.5)
    rig.legs = [empty(f"leg{s}", (s * 1.8, 0, 0), rig.hips) for s in (-1, 1)]
    rig.arms = [empty(f"arm{s}", (s * 4.0, 0, 6.6), rig.torso) for s in (-1, 1)]
    rig.head.location = (0, 0, 8.4)
    rig.stride, rig.arm_swing, rig.bob = 0.7, 0.7, 0.6
    trousers = mat("trousers", "#2a3a6a", rough=0.8)
    boots = mat("dboots", "#1e140c", rough=0.5)
    for leg in rig.legs:
        ellipsoid("leg", (0, 0, -2.4), (1.5, 1.5, 2.8), trousers, parent=leg)
        ellipsoid("boot", (0, -0.9, -4.9), (1.6, 2.4, 1.3), boots, parent=leg)
    coat = mat("coat", "#2c6a30", rough=0.8, color2="#1c4a20", noise_scale=0.8)
    ellipsoid("body", (0, 0, 3.6), (4.2, 3.4, 4.6), coat, parent=rig.torso)
    lathe("belt", [(4.2, 1.2), (4.4, 1.8), (4.2, 2.4)], mat("dbelt", "#3a2410", rough=0.6), parent=rig.torso, cap=False)
    for arm in rig.arms:
        ellipsoid("arm", (0, 0, -2.6), (1.4, 1.4, 3.0), coat, parent=arm)
        ellipsoid("hand", (0, -0.2, -5.6), (1.3, 1.3, 1.3), mat("dskin", SKIN, rough=0.6), parent=arm)
    sk = mat("dskin2", SKIN, rough=0.55)
    ellipsoid("headball", (0, 0, 4.4), (4.6, 4.4, 4.4), sk, parent=rig.head)
    for s in (-1, 1):
        ellipsoid("eye", (s * 1.6, -4.0, 4.8), (0.7, 0.5, 0.9), mat("deye", "#140c0a"), parent=rig.head)
    ellipsoid("nose", (0, -4.6, 3.8), (1.3, 1.1, 1.1), mat("dnose", "#e07060", rough=0.4), parent=rig.head)
    beard = mat("beard", "#f4f0e8", rough=0.9, color2="#c8c4bc", noise_scale=1.4, bump=0.4)
    ellipsoid("beard", (0, -3.0, 1.4), (3.8, 2.4, 3.6), beard, parent=rig.head, jitter=0.1, seed=2)
    cylinder("beardtip", 2.6, 0.2, 4.0, beard, parent=rig.head, loc=(0, -3.6, 0.8), rot=(math.pi - 0.3, 0, 0), seg=12)
    capm = mat("dcap", "#e02a20", rough=0.75, color2="#a01810", noise_scale=0.7)
    cylinder("cap", 4.9, 2.2, 5.0, capm, parent=rig.head, loc=(0, 0.4, 6.4), rot=(0.25, 0, 0), seg=20)
    cylinder("cap2", 2.3, 0.2, 5.0, capm, parent=rig.head, loc=(0, 1.6, 11.0), rot=(0.75, 0, 0), seg=16)
    ellipsoid("capbrim", (0, 0.3, 6.6), (5.0, 4.8, 1.0), capm, parent=rig.head)
    return rig


class Bat:
    def __init__(self):
        self.root = empty("bat", (0, 0, 0))
        fur = mat("fur", "#3a2a34", rough=0.9, color2="#241820", noise_scale=1.2, bump=0.4)
        wingm = mat("wing", "#4a2a40", rough=0.6, color2="#2a1424", noise_scale=0.5, bump=0.3)
        ellipsoid("body", (0, 0.8, 0), (2.4, 3.2, 2.2), fur, parent=self.root)
        ellipsoid("headb", (0, -2.4, 0.8), (2.2, 2.0, 2.0), fur, parent=self.root)
        for s in (-1, 1):
            cylinder("earb", 0.9, 0.0, 2.6, fur, parent=self.root, loc=(s * 1.2, -2.4, 2.2), rot=(0, s * 0.35, 0), seg=6)
            ellipsoid("eyeb", (s * 0.9, -4.1, 1.2), (0.55, 0.4, 0.5),
                      mat("redeye", "#ff3020", emit="#ff2010", emit_strength=8.0), parent=self.root)
        ellipsoid("fang", (0, -4.2, 0.1), (0.8, 0.3, 0.5), mat("fang", "#f0f0e0"), parent=self.root)
        self.wings = []
        pts = [(0, 1.5), (3.0, 2.6), (6.5, 2.6), (10.0, 1.2), (8.6, -0.6), (7.2, 0.6), (5.6, -1.2), (4.0, 0.4),
               (2.2, -1.2), (0, -1.0)]
        for s in (-1, 1):
            piv = empty(f"wing{s}", (s * 1.6, 0.6, 0.6), self.root)
            verts = [(s * x, y, 0) for x, y in pts]
            faces = [[0, i, i + 1] for i in range(1, len(pts) - 1)]
            L.poly("membrane", verts, faces, wingm, parent=piv, solidify=0.3)
            for (x, y) in ((6.5, 2.6), (10.0, 1.2)):
                cylinder("finger", 0.35, 0.2, math.hypot(x, y), fur, parent=piv,
                         rot=(-math.pi / 2, 0, math.atan2(-s * x, y)), seg=6)
            self.wings.append((s, piv))
        self.root.rotation_euler = (0.25, 0, 0)

    def flap(self, t):
        a = math.cos(2 * math.pi * t)
        for s, piv in self.wings:
            piv.rotation_euler = (0, s * -(0.15 + 0.85 * a), 0)
        self.root.location = (0, 0, 1.2 * a)


def bat():
    return Bat()


class Sheep:
    def __init__(self):
        self.root = empty("sheep")
        self.body = empty("sbody", (0, 0, 8.0), self.root)
        wool = mat("wool", "#f2eee4", rough=0.95, color2="#c8c2b4", noise_scale=1.3, bump=1.2)
        black = mat("blackf", "#1c1a1c", rough=0.6, color2="#0c0a0c", noise_scale=1.0)
        ellipsoid("core", (0, 0, 0.4), (5.0, 7.0, 4.4), wool, parent=self.body, jitter=0.12, seed=1)
        r = L.rng(5)
        for i in range(26):
            u = r.uniform(0, 2 * math.pi)
            v = r.uniform(-0.6, 1.2)
            x = 4.6 * math.cos(u) * math.cos(v)
            y = 6.4 * math.sin(u) * math.cos(v)
            z = 0.4 + 4.0 * math.sin(v)
            rr = r.uniform(1.9, 2.7)
            ellipsoid(f"puff{i}", (x, y, z), (rr, rr, rr * 0.9), wool, parent=self.body, seg=12, jitter=0.15, seed=i)
        self.neck = empty("neck", (0, -6.6, 2.4), self.body)
        ellipsoid("headbk", (0, -3.6, 0.6), (2.9, 4.2, 3.0), black, parent=self.neck, rot=(0.35, 0, 0))
        ellipsoid("topknot", (0, -1.4, 3.0), (2.3, 1.8, 1.4), wool, parent=self.neck, seg=12, jitter=0.15, seed=9)
        for s in (-1, 1):
            ellipsoid("earb", (s * 3.6, -1.8, 1.6), (2.2, 1.0, 0.9), black, parent=self.neck, rot=(0, s * -0.3, s * 0.3))
            ellipsoid("eyes", (s * 1.8, -5.2, 1.9), (0.6, 0.5, 0.6), mat("seye", "#e8e0b0", rough=0.2), parent=self.neck)
        self.legs = []
        for i, (x, y) in enumerate(((-2.4, -4.4), (2.4, -4.4), (-2.4, 4.0), (2.4, 4.0))):
            piv = empty(f"sleg{i}", (x, y, -2.6), self.body)
            cylinder("legb", 0.9, 0.8, 5.6, black, parent=piv, loc=(0, 0, -5.6), seg=8)
            ellipsoid("hoof", (0, -0.2, -5.4), (1.0, 1.2, 0.6), black, parent=piv)
            self.legs.append((i, piv))
        ellipsoid("tail", (0, 7.4, 1.2), (1.6, 1.6, 1.6), wool, parent=self.body, seg=12)

    def run(self, t):
        a = math.sin(2 * math.pi * t)
        c = math.cos(2 * math.pi * t)
        self.body.location = (0, 0, 8.0 + 1.2 * max(0.0, c))
        self.body.rotation_euler = (-0.12 * a, 0, 0)
        self.neck.rotation_euler = (0.15 * a, 0, 0)
        for i, piv in self.legs:
            front = i < 2
            swing = 0.75 * (a if front else -a)
            piv.rotation_euler = (swing + (0.08 if i % 2 else -0.08) * c, 0, 0)

    def graze(self, f):
        self.run(0)
        self.body.location = (0, 0, 7.6)
        self.body.rotation_euler = (0.12, 0, 0)
        self.neck.rotation_euler = ((1.0, 1.15, 1.05, 0.9)[f], 0, (0.0, 0.05, -0.05, 0.0)[f])
        for i, piv in self.legs:
            piv.rotation_euler = ((-0.1 if i < 2 else 0.12), 0, 0)


def sheep():
    return Sheep()
