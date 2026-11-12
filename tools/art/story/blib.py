"""Blender-side helpers for the story art: scene setup, the game camera, lights, materials and
skin-modifier creatures. Imported by render.py inside `blender -b`; never run by plain Python.

World units: one arena cell is 1 unit and PX pixels at the final size.
"""
import math
import sys

import bpy
from mathutils import Vector

PX = 20
ELEVATION = 55.0          # the game's camera, degrees above the ground, orthographic


def script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def reset(samples=48):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.eevee.taa_render_samples = samples
    s.eevee.use_shadows = True
    s.eevee.shadow_resolution_scale = 1.0
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.render.film_transparent = True
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    s.render.resolution_percentage = 100
    world = bpy.data.worlds.new("world")
    s.world = world
    world.use_nodes = True
    world_colour((0.02, 0.02, 0.035), 1.0)
    return s


def world_colour(rgb, strength):
    bg = next(n for n in bpy.context.scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*rgb, 1)
    bg.inputs["Strength"].default_value = strength


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def clear(name="actor"):
    """Removes every object of a collection (the creature rebuilt for each frame)."""
    col = bpy.data.collections.get(name)
    if col is None:
        return
    for ob in list(col.objects):
        data = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)
        elif isinstance(data, bpy.types.Curve) and data.users == 0:
            bpy.data.curves.remove(data)


def link(ob, col="actor"):
    collection(col).objects.link(ob)
    return ob


def look_rotation(direction, up="Y"):
    return Vector(direction).normalized().to_track_quat("-Z", up).to_euler()


# ---------------------------------------------------------------------------
#   cameras and lights
# ---------------------------------------------------------------------------

def game_camera(w, h, scale, origin=(0, 0, 0)):
    """The arena camera for a w x h sprite rendered `scale` times larger: orthographic, ELEVATION
    degrees above the ground, the world origin landing on the bottom middle pixel (the feet)."""
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = w * scale, h * scale
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = max(w, h) / PX
    cam.clip_start, cam.clip_end = 0.1, 200
    ob = bpy.data.objects.new("cam", cam)
    s.collection.objects.link(ob)
    e = math.radians(ELEVATION)
    forward = Vector((0, math.cos(e), -math.sin(e)))
    up = Vector((0, math.sin(e), math.cos(e)))
    ob.location = Vector(origin) - forward * 60 + up * ((h / 2 - 0.5) / PX)
    ob.rotation_euler = look_rotation(forward)
    s.camera = ob
    return ob


def sun(direction, colour, strength, angle=4.0, shadow=True):
    lamp = bpy.data.lights.new("sun", "SUN")
    lamp.color = colour
    lamp.energy = strength
    lamp.angle = math.radians(angle)
    lamp.use_shadow = shadow
    ob = bpy.data.objects.new("sun", lamp)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = look_rotation(direction)
    return ob


def point(location, colour, power, radius=0.2, col=None):
    lamp = bpy.data.lights.new("point", "POINT")
    lamp.color = colour
    lamp.energy = power
    lamp.shadow_soft_size = radius
    ob = bpy.data.objects.new("point", lamp)
    if col:
        link(ob, col)
    else:
        bpy.context.scene.collection.objects.link(ob)
    ob.location = location
    return ob


def sprite_lights(key=4.2, rim=4.0, fill=0.5, ambient=0.15):
    """Key light top left (screen), a cool fill from the bottom right, a warm-white rim from
    behind that cuts the silhouette out of a dark arena."""
    sun((0.55, 0.45, -0.75), (1.0, 0.93, 0.80), key, angle=6)
    sun((-0.5, -0.3, -0.35), (0.45, 0.6, 1.0), fill, shadow=False)
    sun((-0.25, -1.0, -0.15), (1.0, 0.95, 0.85), rim, angle=2, shadow=False)
    world_colour((0.18, 0.2, 0.3), ambient)


# ---------------------------------------------------------------------------
#   materials
# ---------------------------------------------------------------------------

def _principled(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def material(name, colour, rough=0.5, metal=0.0, sss=0.0, coat=0.0, spec=0.5,
             colour2=None, mix_scale=6.0, bump=0.0, bump_scale=20.0, voronoi=False,
             emission=None, emit=0.0):
    """A Principled material; colour2 mottles the base with noise, bump adds noise (or voronoi
    scales) relief in object space."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    p = _principled(mat)
    p.inputs["Base Color"].default_value = (*colour, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Specular IOR Level"].default_value = spec
    if sss:
        p.inputs["Subsurface Weight"].default_value = sss
        p.inputs["Subsurface Radius"].default_value = (0.3, 0.2, 0.1)
        p.inputs["Subsurface Scale"].default_value = 0.1
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = 0.08
    if emission:
        p.inputs["Emission Color"].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = emit
    coord = None
    if colour2 is not None or bump:
        coord = nt.nodes.new("ShaderNodeTexCoord")
    if colour2 is not None:
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = mix_scale
        noise.inputs["Detail"].default_value = 6
        nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.35
        ramp.color_ramp.elements[0].color = (*colour, 1)
        ramp.color_ramp.elements[1].position = 0.7
        ramp.color_ramp.elements[1].color = (*colour2, 1)
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    if bump:
        if voronoi:
            tex = nt.nodes.new("ShaderNodeTexVoronoi")
            tex.feature = "F1"
            tex.distance = "EUCLIDEAN"
            tex.inputs["Scale"].default_value = bump_scale
            out = tex.outputs["Distance"]
        else:
            tex = nt.nodes.new("ShaderNodeTexNoise")
            tex.inputs["Scale"].default_value = bump_scale
            tex.inputs["Detail"].default_value = 8
            out = tex.outputs["Fac"]
        nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = 0.05
        nt.links.new(out, b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    return mat


def emissive(name, colour, strength):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type == "BSDF_PRINCIPLED":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*colour, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


# ---------------------------------------------------------------------------
#   geometry
# ---------------------------------------------------------------------------

class Skeleton:
    """Points with radii joined by edges, skinned (Skin modifier) and smoothed: a cheap way to
    model organic bodies, limbs and tails procedurally, posed per frame."""

    def __init__(self):
        self.points, self.radii, self.edges = [], [], []

    def add(self, pos, radius, parent=None):
        self.points.append(Vector(pos))
        self.radii.append(radius if isinstance(radius, tuple) else (radius, radius))
        i = len(self.points) - 1
        if parent is not None:
            self.edges.append((parent, i))
        return i

    def chain(self, parent, nodes, steps=2):
        """Adds (pos, radius) nodes after `parent`, with `steps` interpolated points between
        each pair; returns the index of the last."""
        prev = parent
        for pos, radius in nodes:
            r1 = radius if isinstance(radius, tuple) else (radius, radius)
            p0, r0 = self.points[prev], self.radii[prev]
            for k in range(1, steps + 1):
                t = k / steps
                prev = self.add(p0.lerp(Vector(pos), t),
                                (r0[0] + (r1[0] - r0[0]) * t, r0[1] + (r1[1] - r0[1]) * t), prev)
        return prev

    def build(self, name, mat, subdiv=2, col="actor"):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(p) for p in self.points], self.edges, [])
        ob = link(bpy.data.objects.new(name, me), col)
        skin = ob.modifiers.new("skin", "SKIN")
        skin.use_smooth_shade = True
        skin.branch_smoothing = 0.6
        layer = me.skin_vertices[0].data
        for i, r in enumerate(self.radii):
            layer[i].radius = r
            layer[i].use_root = (i == 0)
        sub = ob.modifiers.new("sub", "SUBSURF")
        sub.levels = sub.render_levels = subdiv
        assign(ob, mat)
        return ob


def mesh_object(name, verts, faces, mat, col="actor", smooth=True, subdiv=0):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    if smooth:
        for poly in me.polygons:
            poly.use_smooth = True
    ob = link(bpy.data.objects.new(name, me), col)
    if subdiv:
        sub = ob.modifiers.new("sub", "SUBSURF")
        sub.levels = sub.render_levels = subdiv
    assign(ob, mat)
    return ob


def primitive(kind, mat, col="actor", **kw):
    """bpy.ops primitive moved into `col`; kind is e.g. 'cylinder', 'cone', 'cube', 'uv_sphere'."""
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(**kw)
    ob = bpy.context.active_object
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    link(ob, col)
    assign(ob, mat)
    return ob


def smooth(ob, subdiv=0):
    for poly in ob.data.polygons:
        poly.use_smooth = True
    if subdiv:
        sub = ob.modifiers.new("sub", "SUBSURF")
        sub.levels = sub.render_levels = subdiv
    return ob


def tube(name, points, radii, mat, sides=8, col="actor", cap=True):
    """A tapered tube along points (horns, reeds, fingers, the pestle)."""
    verts, faces = [], []
    pts = [Vector(p) for p in points]
    n = len(pts)
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = d.orthogonal().normalized()
        b = d.cross(a).normalized()
        for k in range(sides):
            t = 2 * math.pi * k / sides
            verts.append(p + (a * math.cos(t) + b * math.sin(t)) * radii[i])
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, (i + 1) * sides + k2, (i + 1) * sides + k))
    if cap:
        verts.append(pts[0])
        verts.append(pts[-1])
        c0, c1 = len(verts) - 2, len(verts) - 1
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c0, k2, k))
            faces.append((c1, (n - 1) * sides + k, (n - 1) * sides + k2))
    return mesh_object(name, verts, faces, mat, col)


def render(path):
    s = bpy.context.scene
    s.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
