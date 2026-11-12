"""The models of the game art, built from primitives (see blender_lib.py for units and camera).

Tiles span x, y in [-10, 10]; +y is north (up the screen). A block of height H that fills its
cell on screen reaches back to back_edge(H): its front face shows below, its top above.
Figures stand at the origin and face -y (toward the camera, "down").
"""
import math

import blender_lib as L
from blender_lib import box, cylinder, ellipsoid, lathe, mat, rock

FEET_UP = 4.0  # figures: the ground point is this many pixels above the bottom of the frame
DIR_ROT = {"down": 0.0, "up": math.pi, "left": -math.pi / 2, "right": math.pi / 2}


def back_edge(height):
    return (10 * L.SIN - height * L.COS) / L.SIN - 0.2


def ground(material, z=0.0):
    return box("ground", (0, 0, z - 0.5), (40, 40, 1), material)


# ---------------------------------------------------------------------------
#   town: Wroclaw market square (also the Battle arena)
# ---------------------------------------------------------------------------

def cobbles(seed, margin=0.0, skip=(), mats=None):
    r = L.rng(seed)
    mats = mats or [mat(f"cob{i}", c, rough=0.75, color2=c2, noise_scale=0.9, bump=0.35)
                    for i, (c, c2) in enumerate((("#4b4540", "#3a3531"), ("#423d3a", "#33302d"),
                                                 ("#504538", "#3c342b"), ("#45403b", "#2f2b28"),
                                                 ("#3d3936", "#2c2927"), ("#4f4944", "#3b3632")))]
    rows = 4
    rh = 20 / rows
    k = 0
    for i in range(rows):
        y0 = -10 + i * rh
        cuts = [-10.0]
        x = -10.0
        while True:
            x += r.uniform(4.6, 7.2)
            if x > 10 - 4.0:
                break
            cuts.append(x)
        cuts.append(10.0)
        for a, b in zip(cuts, cuts[1:]):
            k += 1
            if k in skip:
                continue
            cx, cy = (a + b) / 2, y0 + rh / 2
            rx, ry = (b - a) / 2 - 0.5, rh / 2 - 0.5
            rock(f"cob{k}", (cx + r.uniform(-0.2, 0.2), cy + r.uniform(-0.2, 0.2), 0.3),
                 (rx, ry, r.uniform(1.1, 1.6)), r.choice(mats), seed=seed * 50 + k, rough=0.12)


def floor_town(v):
    ground(mat("mortar", "#15120f", rough=0.95, color2="#0d0b09", noise_scale=0.7))
    if v == 0:
        cobbles(10)
    elif v == 1:
        cobbles(11)
    elif v == 2:
        cobbles(12, skip=(6,))
        for i, (x, y) in enumerate(((-1.5, 0.5), (0.8, -0.6), (2.0, 0.9))):
            rock(f"grit{i}", (x, y, 0.1), (0.9, 0.7, 0.5), mat("grit", "#3c352e"), seed=i + 3)
        moss = mat("moss", "#2c3a1c", rough=0.9, color2="#1e2814", noise_scale=1.5)
        for i in range(5):
            ellipsoid(f"moss{i}", (-6 + i * 3.1, -5.0 + (i % 2) * 0.4, 0.15), (0.9, 0.5, 0.5), moss)
    else:
        cobbles(13)
        water = mat("puddle", "#141c26", rough=0.05, spec=0.9)
        ellipsoid("puddle", (2.5, -2.5, 0.9), (5.5, 3.5, 0.25), water)


def brick_front(name, c1, c2, mortar, grime="#6a5a50"):
    return L.brick_mat(name, c1, c2, mortar, scale=1.0, brick_w=6.6, row_h=3.3, mortar_size=0.55,
                       bump=0.8, grime=grime, vertical=True)


def pillar_town():
    h = 9
    yb = back_edge(h)
    bricks = brick_front("brick", "#8a3423", "#6e2a1e", "#2a201c")
    box("body", (0, (yb - 10) / 2, 4.5), (20, yb + 10, 9), bricks)
    roof = L.brick_mat("rooftown", "#8a3a26", "#6e2c1c", "#2a1a14", scale=1.0, brick_w=3.2, row_h=2.6,
                       mortar_size=0.4, bump=0.7)
    cy, dy = (yb - 10) / 2, yb + 10
    spire = cylinder("spire", 10 * math.sqrt(2), 0.0, 6.0, roof, loc=(0, cy, 9.0), rot=(0, 0, math.pi / 4), seg=4,
                     smooth=False)
    spire.scale = (1.0, dy / 20, 1.0)
    cap = mat("sandstone", "#c8ae84", rough=0.75, color2="#9a8060", noise_scale=0.6, bump=0.3)
    box("rim", (0, -9.4, 8.6), (20.2, 1.6, 1.2), cap, bevel=0.3)
    for sx in (-1, 1):
        box(f"quoin{sx}", (sx * 9.2, -9.5, 4.3), (1.8, 1.4, 8.4), cap, bevel=0.3)
    ellipsoid("finial", (0, cy, 15.2), (1.1, 1.1, 1.4), cap)


def wall_town():
    h = 10
    yb = back_edge(h)
    bricks = brick_front("brickw", "#5e2a20", "#4a2219", "#1a1412", grime="#403630")
    box("body", (0, (yb - 10) / 2, 4.5), (20, yb + 10, 9), bricks)
    top = L.brick_mat("bricktop", "#4c2a22", "#3e221c", "#18120f", scale=1.0, brick_w=6.6, row_h=3.3,
                      mortar_size=0.55, bump=0.6, grime="#403630")
    box("top", (0, (yb - 10) / 2 + 0.5, 9.5), (20, yb + 9, 1.2), top)
    coping = mat("coping", "#6c6458", rough=0.8, color2="#4a443c", noise_scale=0.6, bump=0.3)
    box("coping", (0, -9.0, 9.6), (20, 2.4, 1.6), coping, bevel=0.4)
    merlon = brick_front("merlon", "#6a2e22", "#56241a", "#1a1412", grime="#403630")
    for x in (-5.0, 5.0):
        box(f"merlon{x}", (x, -6.5, 11.6), (7.0, 6.0, 3.6), merlon, bevel=0.3)
        box(f"mcap{x}", (x, -6.5, 13.6), (7.6, 6.6, 0.8), coping, bevel=0.3)


def crate(material_set=None):
    """A wooden crate with planks and dark corner posts, warm and lit."""
    h = 9
    yb = back_edge(h) - 0.2
    y0, y1 = -9.4, yb
    cy, dy = (y0 + y1) / 2, y1 - y0
    wood = mat("wood", "#c07a38", rough=0.65, color2="#8a5224", noise_scale=0.5, bump=0.25)
    wood2 = mat("wood2", "#a8682e", rough=0.65, color2="#7a4820", noise_scale=0.5, bump=0.25)
    post = mat("post", "#5a3418", rough=0.7, color2="#3a2010", noise_scale=0.6)
    iron = mat("iron", "#4a4a50", rough=0.4, metal=0.8)
    box("core", (0, cy, h / 2 - 0.2), (15.4, dy - 0.6, h - 0.6), post)
    for i in range(3):
        x = -5.1 + i * 5.1
        box(f"top{i}", (x, cy, h - 0.5), (4.7, dy - 0.8, 1.0), wood if i % 2 == 0 else wood2, bevel=0.3)
    for i in range(2):
        z = 2.2 + i * 4.3
        box(f"front{i}", (0, y0 + 0.4, z), (14.0, 1.0, 4.0), wood2 if i == 0 else wood, bevel=0.3)
    for sx in (-1, 1):
        box(f"postf{sx}", (sx * 7.3, y0 + 0.5, h / 2), (1.8, 1.4, h), post, bevel=0.3)
        box(f"postb{sx}", (sx * 7.3, y1 - 0.7, h / 2), (1.8, 1.4, h), post, bevel=0.3)
        box(f"cap{sx}", (sx * 7.3, y0 + 0.5, h - 0.3), (2.0, 1.6, 1.0), iron, bevel=0.2)
    # a stencilled sulphur mark on the lid
    mark = mat("mark", "#d8b030", rough=0.6, emit="#d8b030", emit_strength=0.15)
    cylinder("mark", 1.6, 1.6, 0.2, mark, loc=(0, cy, h + 0.02), seg=12)


def crate_town():
    floor_town(0)
    crate()


# ---------------------------------------------------------------------------
#   forest: Sleza mountain
# ---------------------------------------------------------------------------

def forest_ground():
    earth = mat("earth", "#2a2015", rough=0.95, color2="#1c2a12", noise_scale=0.22, bump=0.6,
                noise_contrast=(0.4, 0.6))
    ground(earth)


def floor_forest(v):
    forest_ground()
    r = L.rng(200 + v)
    pebble = mat("pebble", "#4a4a44", rough=0.8, color2="#323430", noise_scale=1.0, bump=0.3)
    grass = mat("grass", "#3d5222", rough=0.9, color2="#2a3a18", noise_scale=1.0)
    leaf = mat("leaf", "#6a4018", rough=0.9, color2="#4a2c12", noise_scale=1.0)
    moss = mat("mossf", "#2e4420", rough=0.95, color2="#1e3014", noise_scale=1.2, bump=0.5)
    n_peb, n_tuft, n_leaf = ((2, 2, 2), (1, 3, 1), (3, 1, 3), (0, 2, 4))[v]
    for i in range(n_peb):
        rock(f"peb{i}", (r.uniform(-7, 7), r.uniform(-7, 7), 0.2), (r.uniform(1.0, 1.8), r.uniform(0.8, 1.4), 0.9),
             pebble, seed=v * 10 + i)
    for i in range(n_tuft):
        x0, y0 = r.uniform(-6.5, 6.5), r.uniform(-6.5, 6.5)
        for j in range(5):
            a = r.uniform(-0.5, 0.5)
            cylinder(f"tuft{i}_{j}", 0.45, 0.0, r.uniform(2.5, 4.0), grass,
                     loc=(x0 + r.uniform(-1.2, 1.2), y0 + r.uniform(-0.8, 0.8), 0), rot=(a, r.uniform(-0.5, 0.5), 0),
                     seg=5, smooth=False)
    for i in range(n_leaf):
        ellipsoid(f"leaf{i}", (r.uniform(-8, 8), r.uniform(-8, 8), 0.15), (1.2, 0.6, 0.15), leaf,
                  rot=(0, 0, r.uniform(0, 3.14)))
    if v == 3:
        ellipsoid("mosspatch", (-2, 2, -0.2), (6.0, 4.0, 0.7), moss, jitter=0.25, seed=4)


def mossy(name, stone, stone2, moss, threshold=0.55):
    """Stone with moss on the faces that look up."""
    m = mat(name, stone, rough=0.85, color2=stone2, noise_scale=0.35, bump=0.6)
    nt = m.node_tree
    b = L._bsdf(m)
    ramp_out = b.inputs["Base Color"].links[0].from_socket
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 0.5
    tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
    nt.links.new(tc.outputs["Object"], tex.inputs["Vector"])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(sep.outputs[2], add.inputs[0])
    nt.links.new(tex.outputs["Fac"], add.inputs[1])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = threshold + 0.45
    ramp.color_ramp.elements[1].position = threshold + 0.6
    nt.links.new(add.outputs[0], ramp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(ramp.outputs["Color"], mix.inputs["Factor"])
    nt.links.new(ramp_out, mix.inputs[6])
    mix.inputs[7].default_value = (*L.lin(moss), 1)
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m


def pillar_forest():
    forest_ground()
    stone = mossy("menhir", "#8a8a84", "#5e605c", "#4e6e2c", threshold=0.8)
    rock("stone", (0, -2.2, 5.0), (9.6, 7.0, 7.4), stone, seed=7, rough=0.22)
    rock("stone2", (-6.5, -7.5, 1.0), (3.2, 2.4, 2.2), stone, seed=8, rough=0.3)
    groove = mat("groove", "#2a2c2a", rough=1.0)
    for a in (0.7, -0.7):
        box(f"carve{a}", (0.3, -8.6, 6.0), (7.0, 0.8, 0.9), groove, rot=(0, a, 0))


def wall_forest():
    forest_ground()
    stone = mossy("wallstone", "#5a5a54", "#3a3b36", "#3a5422", threshold=0.9)
    h = 10
    yb = back_edge(h)
    box("core", (0, (yb - 10) / 2, 4.0), (20, yb + 9.5, 8), mat("dark", "#1e201c", rough=1.0))
    r = L.rng(31)
    k = 0
    for row, (z, yy) in enumerate(((2.8, -7.5), (2.8, -1.0), (7.0, -4.5), (7.0, 1.0))):
        x = -10.0 + (row % 2) * 3.5
        while x < 10:
            w = r.uniform(5.0, 7.0)
            k += 1
            rock(f"wr{k}", (x + w / 2 - 0.3, yy, z), (w / 2 + 0.2, 3.6, 3.0), stone, seed=k + 40, rough=0.18)
            x += w


def crate_forest():
    floor_forest(0)
    bark = mat("bark", "#6a4626", rough=0.9, color2="#3a2614", noise_scale=0.9, bump=0.9)
    ends = L.rings_mat("ends", "#d29a58", "#9a6430", scale=0.9)
    rr = 4.6
    top_z = rr + 2 * rr * 0.8 + rr
    yb = (10 * L.SIN - top_z * L.COS) / L.SIN - 0.3
    y0 = -9.4
    length = yb - y0
    for i, (x, z) in enumerate(((-4.9, rr), (4.9, rr), (0.0, rr + 2 * rr * 0.8))):
        log = cylinder(f"log{i}", rr, rr, length, bark, loc=(x, y0, z), rot=(-math.pi / 2, 0, 0), seg=18)
        log.data.materials.append(ends)
        for p in log.data.polygons:
            if abs(p.normal.z) > 0.9:
                p.material_index = 1


# ---------------------------------------------------------------------------
#   castle: Wawel
# ---------------------------------------------------------------------------

def floor_castle(v):
    ground(mat("grout", "#1b1a18", rough=0.95))
    stones = [mat(f"flag{i}", c, rough=0.75, color2=c2, noise_scale=0.35, bump=0.25)
              for i, (c, c2) in enumerate((("#48443e", "#3a3732"), ("#433f3a", "#36332f"),
                                           ("#4b463f", "#3c3833")))]
    layouts = (
        [(-5, -5, 9.4, 9.4), (5, -5, 9.4, 9.4), (-5, 5, 9.4, 9.4), (5, 5, 9.4, 9.4)],
        [(0, 0, 19.4, 19.4)],
        [(0, -5, 19.4, 9.4), (-5, 5, 9.4, 9.4), (5, 5, 9.4, 9.4)],
        [(-5, 0, 9.4, 19.4), (5, -5, 9.4, 9.4), (5, 5, 9.4, 9.4)],
    )
    for i, (x, y, w, d) in enumerate(layouts[v]):
        box(f"flag{i}", (x, y, 0.5), (w, d, 1.0), stones[(i + v) % 3], bevel=0.5)
    if v == 1:
        crack = mat("crack", "#141312", rough=1.0)
        for i, (x, y, a) in enumerate(((-3, 2, 0.6), (1, -1, -0.3), (4.5, -3.5, 0.8))):
            box(f"crack{i}", (x, y, 1.0), (4.5, 0.35, 0.2), crack, rot=(0, 0, a))


def ashlar(name, c1, c2, mortar):
    return L.brick_mat(name, c1, c2, mortar, scale=1.0, brick_w=9.0, row_h=4.6, mortar_size=0.5, bump=0.6,
                       grime="#8a8478", vertical=True)


def pillar_castle():
    h = 11
    yb = back_edge(h)
    cy, dy = (yb - 10) / 2, yb + 10
    box("body", (0, cy, 4.5), (20, dy, 9), ashlar("lime", "#e2dccd", "#cfc7b6", "#7a7264"))
    cap = mat("limecap", "#f0ebe0", rough=0.6, color2="#d0c8b8", noise_scale=0.5, bump=0.2)
    box("cap", (0, cy, 10), (20, dy, 2), cap, bevel=0.7)
    box("plinth", (0, cy, 11.4), (11, dy * 0.6, 1.4), cap, bevel=0.4)
    gold = mat("gold", "#e0b040", rough=0.3, metal=1.0)
    ellipsoid("ball", (0, cy, 14.2), (2.5, 2.5, 2.5), gold)


def wall_castle():
    h = 10
    yb = back_edge(h)
    cy, dy = (yb - 10) / 2, yb + 10
    box("body", (0, cy, 4.5), (20, dy, 9), ashlar("limew", "#8e877a", "#7a7468", "#3a3630"))
    roof = L.brick_mat("rooftile", "#7a3020", "#622618", "#2a120c", scale=1.0, brick_w=3.4, row_h=3.0,
                       mortar_size=0.45, bump=0.8)
    box("roof", (0, cy + 0.6, 9.4), (20, dy - 1.2, 1.2), roof)
    trim = mat("trim", "#a8a092", rough=0.7, color2="#7e786c", noise_scale=0.6)
    box("trim", (0, -9.4, 9.5), (20, 1.6, 1.6), trim, bevel=0.4)


def barrel():
    rr, h = 6.6, 10.0
    yb = back_edge(h)
    cy = yb - rr - 0.2
    staves = mat("staves", "#b0743a", rough=0.6, color2="#7c4c22", noise_scale=0.55, bump=0.3)
    prof = [(rr * (0.86 + 0.14 * math.sin(math.pi * z / h)), z) for z in [h * i / 10 for i in range(11)]]
    lathe("barrel", prof, staves, loc=(0, cy, 0), seg=28)
    lid = L.rings_mat("lid", "#c48a4a", "#8c5a2c", scale=0.6)
    cylinder("lid", rr * 0.86 - 0.3, rr * 0.86 - 0.3, 0.3, lid, loc=(0, cy, h - 0.25), seg=28)
    hoop = mat("hoop", "#3c3a38", rough=0.35, metal=0.9)
    for z in (1.6, h - 1.8):
        r0 = rr * (0.86 + 0.14 * math.sin(math.pi * z / h)) + 0.15
        lathe(f"hoop{z}", [(r0, z - 0.6), (r0, z + 0.6)], hoop, loc=(0, cy, 0), seg=28, cap=False)
    stave_line = mat("staveline", "#4a2a12", rough=0.9)
    for a in (-0.5, -0.15, 0.2, 0.55):
        x = math.sin(a) * rr * 1.0
        y = -math.cos(a) * rr * 1.0
        box(f"line{a}", (x, cy + y, h / 2), (0.25, 0.25, h * 0.98), stave_line, rot=(0, 0, a))


def crate_castle():
    floor_castle(0)
    barrel()


# ---------------------------------------------------------------------------
#   arena furniture: the closing zone, the trapdoor, bombs and items
# ---------------------------------------------------------------------------

def zone():
    h = 9
    yb = back_edge(h)
    rockm = L.crack_mat("basalt", "#2a2422", "#161210", glow="#ff8a10", glow_strength=2.0, scale=0.12,
                        width=0.025)
    box("block", (0, (yb - 10) / 2, h / 2), (20, yb + 10, h), rockm, bevel=0.8)


def trapdoor(glow):
    frame = mat("tframe", "#3a3631", rough=0.8, color2="#26231f", noise_scale=0.6, bump=0.3)
    box("tframe", (0, 0, 0.6), (19.6, 19.6, 1.2), frame, bevel=0.5)
    planks = [mat(f"tp{i}", c, rough=0.7, color2=c2, noise_scale=0.7, bump=0.3)
              for i, (c, c2) in enumerate((("#6a4422", "#4a2e16"), ("#5e3c1e", "#422a14")))]
    if glow:
        hole = mat("glowhole", "#ffcc40", emit="#ffc040", emit_strength=4.0)
        box("hole", (0, 0, 1.0), (15.5, 15.5, 0.6), hole)
    for i in range(4):
        z = 1.5 + (0.0 if not glow else 0.0)
        p = box(f"plank{i}", (-5.7 + i * 3.8, 0, z), (3.5 if not glow else 3.0, 15.0, 0.8), planks[i % 2], bevel=0.25)
        if glow:
            p.location.z += 1.5 + i * 0.5
            p.rotation_euler = (0.08, 0, 0)
    iron = mat("band", "#2c2c30", rough=0.4, metal=0.85)
    for y in (-4.5, 4.5):
        box(f"band{y}", (0, y, 2.1 + (2.2 if glow else 0)), (15.0, 1.4, 0.4), iron)
    ring = mat("ring", "#a08030", rough=0.35, metal=1.0)
    lathe("ring", [(1.6, -0.25), (1.6, 0.25)], ring, loc=(0, -1.5, 2.2 + (2.2 if glow else 0)), cap=False, seg=16)
    if glow:
        L.point("glow", (0, 0, 6), L.lin("#ffc040"), 400, radius=3)


def pot(scale=1.0, pulse=0.0, loc=(0, 0, 0)):
    """The sulphur bomb: a round clay pot crusted with yellow sulphur, a fuse on top."""
    clay = mat("clay", "#a05a32", rough=0.6, color2="#6a3420", noise_scale=0.9, bump=0.3)
    crust = mat("crust", "#e8c830", rough=0.9, color2="#a88a10", noise_scale=1.4, bump=1.0,
                emit="#ffd040", emit_strength=0.2 + 2.5 * pulse)
    s = scale
    x, y, z = loc
    ellipsoid("pot", (x, y, z + 5.0 * s), (5.6 * s, 5.6 * s, 5.0 * s), clay)
    ellipsoid("crust", (x, y, z + 7.0 * s), (4.9 * s, 4.9 * s, 3.4 * s), crust, jitter=0.3, seed=3)
    neck = mat("neck", "#6a3a20", rough=0.7)
    cylinder("neck", 2.0 * s, 1.6 * s, 2.0 * s, neck, loc=(x, y, z + 9.2 * s))
    fuse = mat("fuse", "#2a2018", rough=0.9)
    cylinder("fuse", 0.55 * s, 0.4 * s, 3.2 * s, fuse, loc=(x + 0.3 * s, y, z + 10.8 * s), rot=(0, 0.5, 0), seg=8)


def bomb(f):
    pulse = (0.0, 0.5, 1.0, 0.5)[f]
    pot(scale=0.95 + 0.07 * pulse, pulse=pulse, loc=(0, 0, -5.5))


def token():
    """Round dark stone plate every pickup lies on, so items read as items."""
    stone = mat("token", "#2a2622", rough=0.7, color2="#1a1714", noise_scale=0.8, bump=0.3)
    rim = mat("rim", "#c8a040", rough=0.35, metal=1.0)
    lathe("token", [(7.8, 0.0), (8.2, 0.6), (7.6, 1.4), (0.0, 1.4)], stone, seg=32)
    lathe("rim", [(7.9, 0.6), (8.3, 1.0), (7.9, 1.5)], rim, seg=32, cap=False)


def flame(loc, s=1.0):
    outer = mat("flame_o", "#ff6a10", emit="#ff5a00", emit_strength=3.0)
    inner = mat("flame_i", "#ffe070", emit="#ffe070", emit_strength=4.0)
    prof = [(0.0, 0.0), (2.8, 1.2), (3.4, 3.2), (2.6, 6.0), (1.2, 8.6), (0.0, 10.5)]
    lathe("flame", [(r * s, z * s) for r, z in prof], outer, loc=loc, seg=16)
    lathe("flame2", [(r * s * 0.55, z * s * 0.6) for r, z in prof], inner, loc=(loc[0], loc[1] - 2.4 * s, loc[2] + 0.4 * s), seg=16)


def shield(loc, s=1.0, rot=(0, 0, 0)):
    face = mat("shieldface", "#2a50a8", rough=0.4, metal=0.2)
    rim = mat("shieldrim", "#e0c050", rough=0.3, metal=1.0)
    cross = mat("shieldcross", "#e8e4dc", rough=0.5)
    import bmesh  # noqa: F401  (heater shield outline as a flat polygon, solidified)
    pts = [(-5, 6), (5, 6), (5, 1), (3.6, -3.4), (0, -6.6), (-3.6, -3.4), (-5, 1)]
    verts = [(x * s, 0, y * s) for x, y in pts]
    ob = L.poly("shield", verts, [list(range(len(pts)))], face, loc=loc, rot=rot, solidify=1.4 * s)
    ob.modifiers.new("bev", "BEVEL").width = 0.5 * s
    verts2 = [(x * s * 1.12, 0, y * s * 1.08 - 0.1 * s) for x, y in pts]
    ob2 = L.poly("shieldrim", verts2, [list(range(len(pts)))], rim, loc=(loc[0], loc[1] + 0.35 * s, loc[2]), rot=rot,
                 solidify=0.8 * s)
    ob2.modifiers.new("bev", "BEVEL").width = 0.3 * s
    box("cross_v", (0, -0.6 * s, 0), (1.6 * s, 0.6 * s, 9.0 * s), cross, parent=ob)
    box("cross_h", (0, -0.6 * s, 2.0 * s), (7.4 * s, 0.6 * s, 1.6 * s), cross, parent=ob)


def key(loc, s=1.0, rot=(0, 0, 0)):
    gold = mat("keygold", "#f0c040", rough=0.25, metal=1.0)
    root = L.empty("key", loc)
    root.rotation_euler = rot
    lathe("bow", [(2.6 * s, -0.6 * s), (2.6 * s, 0.6 * s)], gold, parent=root, loc=(-5 * s, 0, 0), rot=(0, 0, 0), cap=False,
          seg=18)
    lathe("bow_in", [(1.4 * s, -0.6 * s), (1.4 * s, 0.6 * s)], gold, parent=root, loc=(-5 * s, 0, 0), cap=False, seg=18)
    for i in range(18):
        a = 2 * math.pi * i / 18
        box(f"bowr{i}", (-5 * s + 2.0 * s * math.cos(a), 2.0 * s * math.sin(a), 0), (1.3 * s, 1.3 * s, 1.2 * s), gold,
            parent=root, rot=(0, 0, a))
    cylinder("shaft", 0.8 * s, 0.8 * s, 9.5 * s, gold, parent=root, loc=(-2.6 * s, 0, 0), rot=(0, math.pi / 2, 0), seg=12)
    box("bit1", (5.0 * s, -1.4 * s, 0), (1.2 * s, 2.8 * s, 1.2 * s), gold, parent=root)
    box("bit2", (3.0 * s, -1.2 * s, 0), (1.2 * s, 2.4 * s, 1.2 * s), gold, parent=root)
    return root


def item_bomb():
    token()
    pot(scale=0.62, loc=(0, 0, 1.2))


def item_range():
    token()
    flame((0, 0, 1.2), s=0.85)


def item_shield():
    token()
    shield((0, 0, 7.0), s=0.95, rot=(0.15, 0, 0))


def item_key():
    token()
    key((0.5, 0, 2.6), s=0.95, rot=(0.0, 0.0, 0.5))


def icon_bomb():
    pot(scale=0.95, pulse=0.3, loc=(0, 0, -6.2))


def icon_range():
    flame((0, 0, -6.5), s=1.25)


def icon_shield():
    shield((0, 0, 0.4), s=1.12)


def icon_key():
    key((0.5, 0, 0), s=1.0, rot=(math.radians(70), 0, math.radians(35)))


def heart():
    red = mat("heart", "#e02838", rough=0.25, color2="#a01020", noise_scale=0.3)
    pts = []
    for i in range(48):
        t = 2 * math.pi * i / 48
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * 0.42, 0, y * 0.42 + 0.8))
    ob = L.poly("heart", pts, [list(range(len(pts)))], red, solidify=3.0, loc=(0, 1.5, 0))
    bev = ob.modifiers.new("bev", "BEVEL")
    bev.width = 1.4
    bev.segments = 4
    ob.modifiers.new("sub", "SUBSURF").levels = 2


# figures live in blender_figures.py
from blender_figures import hero, dwarf, bat, sheep  # noqa: E402,F401
