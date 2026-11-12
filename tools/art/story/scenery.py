"""The title backdrop (Wawel over the Vistula at dusk) and the three world maps (runs inside
Blender). Everything is built from primitives and noise; 2D finishing is in paint.py."""
import math
import random

import bpy
from mathutils import Vector

import blib
import bosses
from blib import material, emissive, primitive


# ---------------------------------------------------------------------------
#   shared pieces
# ---------------------------------------------------------------------------

def perspective_camera(location, target, lens, w, h):
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = w, h
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    cam.clip_start, cam.clip_end = 0.5, 2000
    ob = bpy.data.objects.new("cam", cam)
    s.collection.objects.link(ob)
    ob.location = location
    ob.rotation_euler = blib.look_rotation(Vector(target) - Vector(location))
    s.camera = ob
    return ob


def terrain(name, size, centre, res, height_fn, mat, col="actor"):
    """A grid of res x res quads over size (w, d) around centre with z = height_fn(x, y)."""
    w, d = size
    cx, cy = centre
    verts, faces = [], []
    for j in range(res + 1):
        for i in range(res + 1):
            x = cx - w / 2 + w * i / res
            y = cy - d / 2 + d * j / res
            verts.append((x, y, height_fn(x, y)))
    for j in range(res):
        for i in range(res):
            a = j * (res + 1) + i
            faces.append((a, a + 1, a + res + 2, a + res + 1))
    return blib.mesh_object(name, verts, faces, mat, col)


class Noise:
    """Smooth value noise with octaves (plain Python, deterministic)."""

    def __init__(self, seed):
        rnd = random.Random(seed)
        self.p = [rnd.random() for _ in range(256 * 256)]

    def _v(self, i, j):
        return self.p[(i & 255) * 256 + (j & 255)]

    def __call__(self, x, y, octaves=4):
        total, amp, norm = 0.0, 1.0, 0.0
        for _ in range(octaves):
            i, j = math.floor(x), math.floor(y)
            fx, fy = x - i, y - j
            fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
            a = self._v(i, j) + (self._v(i + 1, j) - self._v(i, j)) * fx
            b = self._v(i, j + 1) + (self._v(i + 1, j + 1) - self._v(i, j + 1)) * fx
            total += (a + (b - a) * fy) * amp
            norm += amp
            amp *= 0.5
            x, y = x * 2.03, y * 2.03
        return total / norm


def box(mat, loc, size, col="actor", rot=0.0):
    ob = primitive("cube", mat, col, size=1, location=loc)
    ob.scale = size
    ob.rotation_euler = (0, 0, rot)
    return ob


def roof(mat, loc, size, col="actor", rot=0.0, sides=4):
    """A pyramid roof (sides=4) or a cone spire on top of loc."""
    r = max(size[0], size[1]) * (0.72 if sides == 4 else 0.5)
    ob = primitive("cone", mat, col, vertices=sides, radius1=r, depth=size[2],
                   location=(loc[0], loc[1], loc[2] + size[2] / 2))
    ob.rotation_euler = (0, 0, rot + (math.pi / 4 if sides == 4 else 0))
    if sides == 4:
        ob.scale = (size[0] / max(size[0], size[1]), size[1] / max(size[0], size[1]), 1)
    return ob


def tower(wall, roof_mat, x, y, z, r, h, roof_h, col="actor", square=False):
    if square:
        box(wall, (x, y, z + h / 2), (r * 2, r * 2, h), col)
        roof(roof_mat, (x, y, z + h), (r * 2.3, r * 2.3, roof_h), col)
    else:
        primitive("cylinder", wall, col, vertices=16, radius=r, depth=h, location=(x, y, z + h / 2))
        primitive("cone", roof_mat, col, vertices=16, radius1=r * 1.25, depth=roof_h,
                  location=(x, y, z + h + roof_h / 2))


def windows(mat, x0, x1, y, z, count, size=0.18, col="actor", rnd=None, facing_y=True):
    """Small lit windows on a wall facing the camera (-Y)."""
    rnd = rnd or random.Random(1)
    for k in range(count):
        if rnd.random() < 0.35:
            continue
        x = x0 + (x1 - x0) * (k + 0.5) / count
        box(mat, (x, y, z + rnd.uniform(-0.1, 0.1)), (size, 0.05, size * 1.6), col)


# ---------------------------------------------------------------------------
#   the title: Wawel hill and castle over the Vistula at dusk, a copper sky
# ---------------------------------------------------------------------------

COPPER = [  # (height of the sky 0 = horizon .. 1 = zenith, colour) for constant bands
    (0.00, (1.00, 0.62, 0.22)), (0.02, (1.00, 0.48, 0.16)), (0.045, (0.95, 0.36, 0.14)),
    (0.075, (0.85, 0.25, 0.16)), (0.11, (0.70, 0.17, 0.20)), (0.15, (0.52, 0.11, 0.24)),
    (0.20, (0.36, 0.07, 0.26)), (0.26, (0.24, 0.05, 0.25)), (0.33, (0.15, 0.04, 0.22)),
    (0.42, (0.09, 0.03, 0.18)), (0.55, (0.05, 0.02, 0.13)), (0.70, (0.03, 0.015, 0.09)),
]


def copper_world(strength=1.0, bands=COPPER):
    """A sky of hard horizontal colour bands, the Amiga copper gradient, reflected by water."""
    world = bpy.context.scene.world
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    absz = nt.nodes.new("ShaderNodeMath")
    absz.operation = "ABSOLUTE"
    nt.links.new(sep.outputs["Z"], absz.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = bands[0][0], (*bands[0][1], 1)
    els[1].position, els[1].color = bands[1][0], (*bands[1][1], 1)
    for pos, c in bands[2:]:
        e = els.new(pos)
        e.color = (*c, 1)
    nt.links.new(absz.outputs["Value"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength


def render_title(out, scale):
    s = blib.reset(samples=64)
    # the sky stays transparent: paint.py lays straight copper bands behind it; the world
    # gradient here only feeds the reflections in the river
    s.eevee.use_raytracing = True
    w, h = 640 * scale, 360 * scale
    copper_world()
    perspective_camera((0, -60, 4.0), (0, 40, 9.5), 32, w, h)
    rnd = random.Random(5)
    noise = Noise(3)
    # the low dusk sun behind the castle and a warm rim on every silhouette
    blib.sun((0.35, -1.0, -0.1), (1.0, 0.45, 0.2), 2.2, angle=3)
    blib.sun((0.3, 0.6, -0.5), (0.35, 0.25, 0.6), 0.35, shadow=False)
    sun_disc = emissive("sun_disc", (1.0, 0.55, 0.25), 1.6)
    primitive("uv_sphere", sun_disc, radius=9, location=(-150, 420, 4), segments=32, ring_count=16)
    # the Vistula: dark, still, reflecting the sky
    water = material("water", (0.01, 0.01, 0.03), rough=0.12, spec=0.6, bump=0.12, bump_scale=0.35)
    primitive("plane", water, size=800, location=(0, 200, 0))
    # far hills: layered ridges fading into the dusk
    for k, (y, hgt, c) in enumerate([(380, 16, (0.30, 0.10, 0.22)), (260, 11, (0.18, 0.06, 0.16)),
                                     (170, 7, (0.10, 0.04, 0.10))]):
        m = material(f"ridge{k}", c, rough=0.9)
        terrain(f"ridge{k}", (900, 60), (0, y), 120,
                lambda x, yy, hgt=hgt, k=k: max(-1.0, hgt * (noise(x * 0.012 + k * 7, yy * 0.02, 5) - 0.35) * 2.2
                                               - abs(yy - y) * 0.3), m)
    # the near bank on the left: willows and the town under the dusk
    bank = material("bank", (0.02, 0.015, 0.02), rough=0.9)
    terrain("bank", (120, 40), (-75, 60), 60,
            lambda x, y: 2.5 * noise(x * 0.08, y * 0.08) + 1.5 - max(0, (x + 25) * 0.25) - max(0, (40 - y) * 0.1), bank)
    town = material("town", (0.05, 0.03, 0.06), rough=0.8)
    lit = emissive("lit", (1.0, 0.7, 0.3), 2.2)
    for k in range(26):
        x = -95 + k * 3.0 + rnd.uniform(-1, 1)
        y = 75 + rnd.uniform(0, 20)
        hh = rnd.uniform(2.0, 4.0)
        box(town, (x, y, 1 + hh / 2), (2.6, 2.6, hh))
        roof(town, (x, y, 1 + hh), (2.6, 2.6, 1.8))
        if rnd.random() < 0.6:
            box(lit, (x + rnd.uniform(-0.6, 0.6), y - 1.32, 1 + hh * 0.6), (0.4, 0.05, 0.6))
    # St Mary's two towers far on the left
    for x, hh in ((-60, 14), (-56, 11)):
        tower(town, town, x, 100, 1, 1.2, hh, 4 if hh > 12 else 2.5, square=True)
    # Wawel hill: limestone and dark trees, the castle on top
    rock = material("rock", (0.07, 0.045, 0.05), rough=0.85, colour2=(0.16, 0.09, 0.08), mix_scale=0.4,
                    bump=0.6, bump_scale=0.6)
    hx, hy = 30, 45

    def hill(x, y):
        r = math.hypot((x - hx) / 1.4, (y - hy))
        base = 11.0 * max(0.0, 1 - (r / 20) ** 2.2)
        return base + 1.2 * noise(x * 0.25, y * 0.25) * min(1.0, base) - 0.6
    terrain("hill", (80, 50), (hx, hy), 110, hill, rock)
    trees = material("trees", (0.015, 0.02, 0.02), rough=0.9, colour2=(0.05, 0.04, 0.03), mix_scale=1.2,
                     bump=0.8, bump_scale=3)
    for k in range(160):
        x = hx + rnd.uniform(-28, 28)
        y = hy - 19 + rnd.uniform(-3, 8)
        z = max(0.0, hill(x, y))
        if z < 0.2 or z > 7.5:
            continue
        t = primitive("uv_sphere", trees, radius=rnd.uniform(0.6, 1.2), location=(x, y, z + 0.6),
                      segments=10, ring_count=6)
        t.scale = (1, 1, 1.4)
    top = 10.0
    wall = material("castle_wall", (0.20, 0.14, 0.13), rough=0.75, colour2=(0.11, 0.08, 0.09),
                    mix_scale=0.5, bump=0.3, bump_scale=2)
    red_roof = material("castle_roof", (0.16, 0.04, 0.035), rough=0.6)
    green_roof = material("copper_roof", (0.07, 0.15, 0.13), rough=0.45, metal=0.4)
    gold = material("gold", (1.0, 0.72, 0.25), rough=0.2, metal=1.0)
    # curtain wall along the crest, battlements, the palace block and towers
    box(wall, (hx, hy, top), (34, 14, 4))
    for k in range(34):
        box(wall, (hx - 16.5 + k, hy - 6.9, top + 2.3), (0.55, 0.4, 0.7))
    box(wall, (hx + 6, hy + 2, top + 4), (14, 10, 5))
    roof(red_roof, (hx + 6, hy + 2, top + 6.5), (14, 10, 3.5))
    windows(lit, hx - 1, hx + 13, hy - 3.05, top + 5.2, 10, size=0.5, rnd=rnd)
    windows(lit, hx - 16, hx + 16, hy - 7.05, top + 0.5, 18, size=0.45, rnd=rnd)
    tower(wall, red_roof, hx - 16, hy - 6, top - 2, 2.2, 9, 5)          # Sandomierska
    tower(wall, red_roof, hx + 17, hy - 5, top - 2, 2.0, 8, 4.5)        # Senatorska
    tower(wall, red_roof, hx + 19, hy + 5, top - 1, 1.6, 7, 4)
    # the cathedral: nave, the tall clock tower with a copper helm and the golden chapel dome
    cx = hx - 7
    box(wall, (cx, hy - 1, top + 4), (10, 5, 6))
    roof(green_roof, (cx, hy - 1, top + 7), (10, 5, 3))
    tower(wall, green_roof, cx - 6, hy - 2, top, 1.6, 15, 6, square=True)
    primitive("uv_sphere", gold, radius=2.0, location=(cx + 1, hy - 4.5, top + 8.5), segments=24, ring_count=12)
    box(wall, (cx + 1, hy - 4.5, top + 6.5), (3.6, 3.6, 4))
    primitive("cone", gold, vertices=8, radius1=0.5, depth=2.2, location=(cx + 1, hy - 4.5, top + 11.2))
    tower(wall, gold, cx + 5, hy - 2, top + 2, 1.0, 9, 3)
    blib.render(out / "title.png")
    # the dragon in the sky, a dark silhouette lit only on its rim
    blib.reset(samples=32)
    w2, h2 = 220 * scale, 140 * scale
    blib.collection("actor")
    shadow = material("silhouette", (0.02, 0.01, 0.03), rough=0.5, spec=0.8)
    bosses.dragon("fly", 0.25, silhouette=shadow)
    perspective_camera((1.5, -3.5, -10), (0, 1.2, 1.6), 35, w2, h2)
    blib.sun((0.4, -1.0, 0.1), (1.0, 0.5, 0.2), 6.0, angle=2, shadow=False)
    blib.world_colour((0.05, 0.02, 0.06), 1.0)
    blib.render(out / "dragon.png")


# ---------------------------------------------------------------------------
#   the world maps: painted overviews of each chapter seen from high above
# ---------------------------------------------------------------------------

class Batch:
    """Many small shapes (houses, roofs, trees) gathered into one mesh per material."""

    def __init__(self):
        self.verts, self.faces = [], []

    def _add(self, verts, faces):
        o = len(self.verts)
        self.verts += verts
        self.faces += [tuple(i + o for i in f) for f in faces]

    def box(self, c, size, rot=0.0):
        x, y, z = c
        sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
        cr, sr = math.cos(rot), math.sin(rot)
        v = []
        for dz in (-sz, sz):
            for dx, dy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
                v.append((x + dx * cr - dy * sr, y + dx * sr + dy * cr, z + dz))
        self._add(v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    def gable(self, c, size, rot=0.0):
        """A ridge roof over a box of size (w, d) whose top is at c."""
        x, y, z = c
        sx, sy, h = size[0] / 2 * 1.1, size[1] / 2 * 1.1, size[2]
        cr, sr = math.cos(rot), math.sin(rot)

        def p(dx, dy, dz):
            return (x + dx * cr - dy * sr, y + dx * sr + dy * cr, z + dz)
        v = [p(-sx, -sy, 0), p(sx, -sy, 0), p(sx, sy, 0), p(-sx, sy, 0), p(-sx, 0, h), p(sx, 0, h)]
        self._add(v, [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)])

    def cone(self, c, r, h, sides=6):
        x, y, z = c
        v = [(x + r * math.cos(2 * math.pi * k / sides), y + r * math.sin(2 * math.pi * k / sides), z)
             for k in range(sides)] + [(x, y, z + h)]
        self._add(v, [(k, (k + 1) % sides, sides) for k in range(sides)] + [tuple(range(sides - 1, -1, -1))])

    def blob(self, c, r, h):
        """A low-poly round tree crown."""
        x, y, z = c
        v, f = [], []
        rings = [(0.0, 0.55), (0.35, 1.0), (0.75, 0.75), (1.0, 0.0)]
        for zz, rr in rings:
            for k in range(7):
                a = 2 * math.pi * k / 7
                v.append((x + r * rr * math.cos(a), y + r * rr * math.sin(a), z + h * zz))
        for i in range(len(rings) - 1):
            for k in range(7):
                k2 = (k + 1) % 7
                f.append((i * 7 + k, i * 7 + k2, (i + 1) * 7 + k2, (i + 1) * 7 + k))
        self._add(v, f)

    def build(self, name, mat):
        if self.verts:
            blib.mesh_object(name, self.verts, self.faces, mat, smooth=False)


def river_mesh(name, points, width, z, mat, steps=8):
    """A flat ribbon along a smoothed polyline (Catmull-Rom); returns the path points."""
    pts = [Vector((p[0], p[1], 0)) for p in points]
    path = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(steps):
            t = k / steps
            path.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                               + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    path.append(pts[-1])
    verts, faces = [], []
    for i, p in enumerate(path):
        d = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        n = Vector((-d.y, d.x, 0))
        wv = width * (1 + 0.15 * math.sin(i * 0.7))
        verts += [(p.x + n.x * wv / 2, p.y + n.y * wv / 2, z), (p.x - n.x * wv / 2, p.y - n.y * wv / 2, z)]
    for i in range(len(path) - 1):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    blib.mesh_object(name, verts, faces, mat, smooth=False)
    return path


def near_path(path, x, y, dist):
    return any((p.x - x) ** 2 + (p.y - y) ** 2 < dist * dist for p in path)


def map_setup(w, h):
    s = blib.reset(samples=48)
    s.render.film_transparent = False
    s.eevee.use_raytracing = True
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = 64
    ob = bpy.data.objects.new("cam", cam)
    s.collection.objects.link(ob)
    e = math.radians(62)
    fwd = Vector((0, math.cos(e), -math.sin(e)))
    ob.location = -fwd * 80
    ob.rotation_euler = blib.look_rotation(fwd)
    s.camera = ob
    s.render.resolution_x, s.render.resolution_y = w, h
    blib.sun((0.55, -0.45, -0.7), (1.0, 0.9, 0.72), 4.0, angle=3)
    blib.world_colour((0.35, 0.42, 0.6), 0.45)


def ground(height_fn, colours, seed):
    """The land: rolling ground coloured by a patchwork of fields."""
    m = bpy.data.materials.new(f"land{seed}")
    m.use_nodes = True
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Roughness"].default_value = 0.9
    coord = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 0.2
    nt.links.new(coord.outputs["Object"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    n = len(colours)
    els[0].position, els[0].color = 0.0, (*colours[0], 1)
    els[1].position, els[1].color = 1.0 / n, (*colours[1 % n], 1)
    for k in range(2, n):
        e = els.new(k / n)
        e.color = (*colours[k], 1)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vor.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[0], ramp.inputs["Fac"])
    # fine noise on top: furrows and grass
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 3.0
    tex.inputs["Detail"].default_value = 6
    nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    nt.links.new(tex.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.4
    nt.links.new(tex.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    terrain("land", (90, 70), (0, 2), 180, height_fn, m)


def forest(round_, pine, rnd, count, area, height_fn, keep, pine_share=0.5):
    x0, x1, y0, y1 = area
    for _ in range(count):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if not keep(x, y):
            continue
        z = height_fn(x, y)
        r = rnd.uniform(0.45, 0.8)
        if rnd.random() < pine_share:
            pine.cone((x, y, z), r * 0.8, r * 3.2, sides=6)
        else:
            round_.blob((x, y, z), r, r * 1.6)


def build_trees(round_, pine):
    round_.build("trees", material("leaves", (0.10, 0.20, 0.05), rough=0.9, colour2=(0.18, 0.26, 0.06),
                                   mix_scale=0.5))
    pine.build("pines", material("needles", (0.04, 0.12, 0.06), rough=0.9))


def town(rnd, area, height_fn, keep, count, walls=None):
    """Houses with red roofs packed in an area; optional city walls (x0, x1, y0, y1)."""
    houses, roofs = Batch(), Batch()
    x0, x1, y0, y1 = area
    for _ in range(count):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if not keep(x, y):
            continue
        z = height_fn(x, y)
        w, d, hh = rnd.uniform(0.8, 1.5), rnd.uniform(0.7, 1.2), rnd.uniform(0.6, 1.3)
        rot = rnd.choice((0.0, math.pi / 2)) + rnd.uniform(-0.1, 0.1)
        houses.box((x, y, z + hh / 2), (w, d, hh), rot)
        roofs.gable((x, y, z + hh), (w, d, 0.7), rot)
    if walls:
        wx0, wx1, wy0, wy1 = walls
        for k in range(int(wx1 - wx0)):
            for yy in (wy0, wy1):
                houses.box((wx0 + k + 0.5, yy, height_fn(wx0 + k, yy) + 0.7), (1.05, 0.5, 1.4))
        for k in range(int(wy1 - wy0)):
            for xx in (wx0, wx1):
                houses.box((xx, wy0 + k + 0.5, height_fn(xx, wy0 + k) + 0.7), (0.5, 1.05, 1.4))
        for xx in (wx0, wx1, (wx0 + wx1) / 2):
            for yy in (wy0, wy1):
                houses.box((xx, yy, height_fn(xx, yy) + 1.2), (1.4, 1.4, 2.4))
                roofs.cone((xx, yy, height_fn(xx, yy) + 2.4), 1.0, 1.4, sides=4)
    houses.build("houses", material("plaster", (0.62, 0.55, 0.42), rough=0.8))
    roofs.build("roofs", material("tiles", (0.48, 0.12, 0.06), rough=0.7, colour2=(0.35, 0.08, 0.05),
                                  mix_scale=2))


def church(x, y, z, towers=1, gold=False, scale=1.0):
    b, r = Batch(), Batch()
    b.box((x, y, z + 1.2 * scale), (4 * scale, 1.8 * scale, 2.4 * scale))
    r.gable((x, y, z + 2.4 * scale), (4 * scale, 1.8 * scale, 1.2 * scale))
    for k in range(towers):
        tx = x - 2.2 * scale + k * 1.1 * scale
        b.box((tx, y, z + 2.5 * scale), (1.0 * scale, 1.0 * scale, 5 * scale))
        r.cone((tx, y, z + 5 * scale), 0.75 * scale, 2.6 * scale, sides=8)
    b.build("church", material("stone", (0.55, 0.48, 0.40), rough=0.8))
    spire = material("gilt", (0.9, 0.62, 0.2), rough=0.25, metal=1.0) if gold else \
        material("verdigris", (0.12, 0.30, 0.22), rough=0.5, metal=0.3)
    r.build("spires", spire)


def river_water():
    return material("water", (0.04, 0.10, 0.16), rough=0.15, spec=0.7, bump=0.15, bump_scale=0.8)


def map_wroclaw(out, w, h):
    """Wroclaw on the Oder: the walled town, the cathedral island, forests to the south."""
    map_setup(w, h)
    noise = Noise(21)
    rnd = random.Random(21)

    def height(x, y):
        return 1.2 * noise(x * 0.05 + 3, y * 0.05) - 0.4
    ground(height, [(0.36, 0.42, 0.14), (0.52, 0.48, 0.18), (0.30, 0.36, 0.12), (0.60, 0.52, 0.26),
                    (0.42, 0.40, 0.16), (0.25, 0.32, 0.11)], 1)
    water = river_water()
    oder = river_mesh("oder", [(-40, 13), (-24, 16), (-10, 14), (2, 15.5), (14, 17), (26, 14), (40, 16)],
                      3.0, 0.35, water)
    branch = river_mesh("branch", [(2, 15.5), (8, 20.5), (14, 17)], 1.6, 0.36, water)
    river_mesh("moat", [(-16.5, 5.8), (-16.5, 12.0), (8.5, 12.0), (8.5, 5.8), (-16.5, 5.8)], 0.9, 0.34, water,
               steps=2)

    def free(x, y):
        return not near_path(oder + branch, x, y, 2.6)
    town(rnd, (-15.5, 7.5, 6.5, 11.2), height, free, 300, walls=(-15.2, 7.2, 6.6, 11.4))
    church(-4, 9, height(-4, 9) + 0.3, towers=2)
    church(8, 18.3, height(8, 18.3) + 0.3, towers=2)

    def woods(x, y):
        return free(x, y) and noise(x * 0.12 + 40, y * 0.12) > 0.45
    round_, pine = Batch(), Batch()
    forest(round_, pine, rnd, 1800, (-36, -4, -26, -7), height, woods, 0.3)
    forest(round_, pine, rnd, 1200, (10, 36, -26, -7), height, woods, 0.5)
    forest(round_, pine, rnd, 300, (-34, 34, 15, 26), height, lambda x, y: free(x, y) and not (-17 < x < 9), 0.2)
    forest(round_, pine, rnd, 120, (-34, 34, -7, 5), height, lambda x, y: rnd.random() < 0.25, 0.3)
    build_trees(round_, pine)
    town(rnd, (-6, 2, -18, -14), height, lambda x, y: True, 20)
    blib.render(out / "map_1.png")


def map_sleza(out, w, h):
    """Sleza: the bald granite top with the Kupala fire, deep forest all around, a lake."""
    map_setup(w, h)
    noise = Noise(37)
    rnd = random.Random(37)
    peaks = [(4, 7, 16.0, 16), (-22, 16, 5.0, 9)]

    def height(x, y):
        z = 1.0 * noise(x * 0.06, y * 0.06) - 0.3
        for px, py, ph, pr in peaks:
            d = math.hypot(x - px, (y - py) * 1.1) / pr
            z += ph * max(0.0, 1 - d) ** 1.6 * (0.85 + 0.3 * noise(x * 0.3, y * 0.3))
        return z
    ground(height, [(0.30, 0.38, 0.12), (0.40, 0.44, 0.16), (0.26, 0.32, 0.10), (0.48, 0.44, 0.20)], 2)
    rocks = material("granite", (0.40, 0.38, 0.36), rough=0.8, colour2=(0.25, 0.24, 0.24), mix_scale=1,
                     bump=0.8, bump_scale=2)
    for k in range(45):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0, 5.5)
        x, y = 4 + r * math.cos(a), 7 + r * math.sin(a)
        b = primitive("ico_sphere", rocks, subdivisions=1, radius=rnd.uniform(0.4, 0.9),
                      location=(x, y, height(x, y)))
        b.scale = (1, 1, 0.6)
    fire = emissive("fire", (1.0, 0.5, 0.1), 6.0)
    primitive("cone", fire, vertices=6, radius1=0.5, depth=1.2, location=(4, 7, height(4, 7) + 0.5))
    blib.point((4, 6, height(4, 7) + 2.5), (1.0, 0.5, 0.15), 3000, radius=0.4)
    water = river_water()
    lake = primitive("cylinder", water, vertices=32, radius=5, depth=0.2, location=(-22, -14, 0.0))
    lake.scale = (1.4, 0.8, 1)
    brook = river_mesh("brook", [(-40, -6), (-28, -10), (-22, -14), (-8, -19), (6, -22), (20, -26)],
                       1.0, 0.0, water)

    def keep(x, y):
        if math.hypot((x + 22) / 7.5, (y + 14) / 4.3) < 1 or near_path(brook, x, y, 1.3):
            return False
        if -7 < y < 5 and rnd.random() < 0.85:
            return False
        return height(x, y) < 9.5 and noise(x * 0.15, y * 0.15 + 9) > 0.3
    round_, pine = Batch(), Batch()
    forest(round_, pine, rnd, 5200, (-36, 36, -26, 30), height, keep, 0.65)
    build_trees(round_, pine)
    town(rnd, (-30, -24, 0, 4), height, lambda x, y: True, 14)
    town(rnd, (22, 30, -6, -2), height, lambda x, y: True, 12)
    blib.render(out / "map_2.png")


def map_krakow(out, w, h):
    """Krakow: the walled town with St Mary's, Wawel on its hill over the Vistula bend."""
    map_setup(w, h)
    noise = Noise(53)
    rnd = random.Random(53)

    def height(x, y):
        z = 1.0 * noise(x * 0.05, y * 0.05) - 0.3
        d = math.hypot((x - 9) / 4.5, (y + 8) / 3.2)
        return z + 3.5 * max(0.0, 1 - d * d)
    ground(height, [(0.42, 0.44, 0.16), (0.56, 0.50, 0.22), (0.34, 0.38, 0.13), (0.62, 0.54, 0.28),
                    (0.46, 0.42, 0.18)], 3)
    water = river_water()
    vistula = river_mesh("vistula", [(-40, -10), (-22, -12), (-6, -15.5), (4, -13.5), (10, -12.2), (18, -14),
                                     (28, -16.5), (40, -14)], 4.2, 0.3, water)
    # the castle on the hill: walls, towers, the palace, the cathedral's gold dome
    hz = height(9, -8)
    b, r = Batch(), Batch()
    b.box((9, -8, hz + 0.6), (7, 4.5, 1.2))
    for x, y in ((5.5, -10.2), (12.5, -10.2), (5.5, -5.8), (12.5, -5.8)):
        b.box((x, y, hz + 1.2), (1.2, 1.2, 2.4))
        r.cone((x, y, hz + 2.4), 0.9, 1.4, sides=8)
    b.box((10.5, -7.2, hz + 1.8), (3.0, 2.4, 1.4))
    r.gable((10.5, -7.2, hz + 2.5), (3.0, 2.4, 1.0))
    b.build("castle", material("stone", (0.62, 0.52, 0.42), rough=0.8))
    r.build("castle_roofs", material("tiles", (0.48, 0.12, 0.06), rough=0.7))
    church(7.5, -8.5, hz + 1.2, towers=1, gold=True, scale=0.6)
    gold = material("gilt", (0.9, 0.62, 0.2), rough=0.25, metal=1.0)
    primitive("uv_sphere", gold, radius=0.7, location=(8.2, -9.2, hz + 2.4), segments=16, ring_count=8)
    # the dragon's den: a dark cave mouth under the hill by the river
    cave = primitive("uv_sphere", material("cave", (0.01, 0.01, 0.01), rough=1.0), radius=1.0,
                     location=(9, -11.6, height(9, -11.6) + 0.2), segments=12, ring_count=6)
    cave.scale = (0.7, 0.3, 0.45)


    def free(x, y):
        return not near_path(vistula, x, y, 3.0) and math.hypot((x - 9) / 5, (y + 8) / 3.6) > 1
    town(rnd, (-9, 9, 8, 17), height, lambda x, y: free(x, y) and not (-2.5 < x < 2.5 and 11 < y < 14), 300,
         walls=(-9.2, 9.2, 7.6, 17.4))
    church(0.5, 15.5, height(0.5, 15.5), towers=2, scale=0.9)
    hall = Batch()
    hall.box((0, 12.5, height(0, 12.5) + 0.5), (3.6, 1.0, 1.0))
    hall.build("cloth_hall", material("plaster", (0.62, 0.55, 0.42), rough=0.8))
    town(rnd, (-4, 6, -4, 2), height, free, 60)
    round_, pine = Batch(), Batch()
    forest(round_, pine, rnd, 900, (-36, -14, -26, 26), height, free, 0.2)
    forest(round_, pine, rnd, 700, (16, 36, -26, 26), height, free, 0.3)
    forest(round_, pine, rnd, 160, (-14, 16, 17.5, 26), height, free, 0.2)
    build_trees(round_, pine)
    blib.render(out / "map_3.png")


def render_maps(out, scale):
    w, h = 640 * scale, 360 * scale
    map_wroclaw(out, w, h)
    map_sleza(out, w, h)
    map_krakow(out, w, h)
