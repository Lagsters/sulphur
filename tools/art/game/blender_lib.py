"""Blender-side helpers for the game art: scene, lights, cameras, materials and primitives.

Imported by blender_scene.py inside Blender. One Blender unit is one final screen pixel; tiles are
20 units square. The camera is orthographic and looks north (+Y) and down at ELEV, so a height z
shows on screen as z * cos(ELEV) and a ground depth y as y * sin(ELEV).
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector, noise

ELEV = math.radians(55)
SIN, COS = math.sin(ELEV), math.cos(ELEV)


# ---------------------------------------------------------------------------
#   scene, lights, camera, render
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    scene.eevee.use_shadows = True
    scene.eevee.use_raytracing = True
    scene.eevee.use_fast_gi = True
    scene.eevee.fast_gi_distance = 6.0
    scene.eevee.shadow_resolution_scale = 1.0
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    scene.view_settings.look = "None"
    world = bpy.data.worlds.new("world")
    scene.world = world
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.030, 0.034, 0.050, 1.0)
    bg.inputs[1].default_value = 1.0
    return scene


def sun(name, direction, color, energy, angle=4.0):
    """A sun light shining along `direction` (from the light toward the scene)."""
    data = bpy.data.lights.new(name, "SUN")
    data.color = color
    data.energy = energy
    data.angle = math.radians(angle)
    data.use_shadow = True
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    ob.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()
    return ob


def point(name, loc, color, energy, radius=1.0):
    data = bpy.data.lights.new(name, "POINT")
    data.color = color
    data.energy = energy
    data.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    return ob


def lights(key=4.2, fill=0.9, rim=1.6):
    """The one light setup of the game: warm key from the top left, cool fill from the right,
    a cool rim from behind that separates figures from the dark floor."""
    sun("key", (1.0, 0.45, -1.35), (1.0, 0.86, 0.68), key, angle=6)
    sun("fill", (-1.0, 0.7, -0.5), (0.45, 0.58, 1.0), fill, angle=20)
    if rim:
        sun("rim", (-0.3, -1.0, -0.7), (0.70, 0.80, 1.0), rim, angle=10)


def camera(width, height, ss, center=(0.0, 0.0, 0.0), offset=(0.0, 0.0), elev=ELEV, ground_square=False):
    """Orthographic camera framing `width` x `height` screen units. `center` shows at `offset`
    from the middle of the frame. With ground_square the render covers width x height*SIN (the
    caller stretches it back), so ground cells come out square."""
    scene = bpy.context.scene
    data = bpy.data.cameras.new("cam")
    data.type = "ORTHO"
    rh = height * SIN if ground_square else height
    data.ortho_scale = max(width, rh)
    data.clip_start = 0.1
    data.clip_end = 1000
    ob = bpy.data.objects.new("cam", data)
    bpy.context.collection.objects.link(ob)
    look = Vector((0.0, math.cos(elev), -math.sin(elev)))
    up = Vector((0.0, math.sin(elev), math.cos(elev)))
    right = Vector((1.0, 0.0, 0.0))
    ox, oy = offset
    if ground_square:
        oy *= SIN
    ob.location = Vector(center) - look * 300 - right * ox - up * oy
    ob.rotation_euler = (math.pi / 2 - elev, 0.0, 0.0)
    scene.camera = ob
    scene.render.resolution_x = round(width * ss)
    scene.render.resolution_y = round(rh * ss)
    return ob


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def clear_objects(keep=("key", "fill", "rim")):
    for ob in list(bpy.data.objects):
        if ob.name not in keep:
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


# ---------------------------------------------------------------------------
#   materials
# ---------------------------------------------------------------------------

def lin(hexcolor):
    """'#rrggbb' (sRGB) -> linear RGB tuple."""
    h = hexcolor.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def _bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _new_material(name):
    m = bpy.data.materials.new(name)
    if not m.node_tree:
        m.use_nodes = True
    return m


def mat(name, color, rough=0.7, metal=0.0, color2=None, noise_scale=0.4, bump=0.0, emit=None,
        emit_strength=0.0, spec=0.4, detail=6.0, noise_contrast=(0.35, 0.65)):
    """Principled material; color2 adds a noise blend between the two colours (object space,
    noise_scale per unit), bump adds relief from the same noise."""
    m = _new_material(name)
    nt = m.node_tree
    b = _bsdf(m)
    b.inputs["Base Color"].default_value = (*lin(color), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if color2 or bump:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise_scale
        tex.inputs["Detail"].default_value = detail
        nt.links.new(tc.outputs["Object"], tex.inputs["Vector"])
        if color2:
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].position = noise_contrast[0]
            ramp.color_ramp.elements[1].position = noise_contrast[1]
            ramp.color_ramp.elements[0].color = (*lin(color2), 1)
            ramp.color_ramp.elements[1].color = (*lin(color), 1)
            nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
            nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        if bump:
            bn = nt.nodes.new("ShaderNodeBump")
            bn.inputs["Strength"].default_value = bump
            nt.links.new(tex.outputs["Fac"], bn.inputs["Height"])
            nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(emit), 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    return m


def brick_mat(name, c1, c2, mortar, scale, brick_w=0.5, row_h=0.25, mortar_size=0.02, bump=0.6,
              rough=0.85, offset=0.5, grime=None):
    """Blender's Brick Texture in object space, with mortar relief."""
    m = _new_material(name)
    nt = m.node_tree
    b = _bsdf(m)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.3
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (*lin(c1), 1)
    br.inputs["Color2"].default_value = (*lin(c2), 1)
    br.inputs["Mortar"].default_value = (*lin(mortar), 1)
    br.inputs["Scale"].default_value = scale
    br.inputs["Mortar Size"].default_value = mortar_size
    br.inputs["Brick Width"].default_value = brick_w
    br.inputs["Row Height"].default_value = row_h
    br.offset = offset
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    color_out = br.outputs["Color"]
    if grime:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 0.25
        tex.inputs["Detail"].default_value = 8
        nt.links.new(tc.outputs["Object"], tex.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*lin(grime), 1)
        ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        ramp.color_ramp.elements[0].position = 0.35
        ramp.color_ramp.elements[1].position = 0.7
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(color_out, mix.inputs[6])
        nt.links.new(ramp.outputs["Color"], mix.inputs[7])
        color_out = mix.outputs[2]
    nt.links.new(color_out, b.inputs["Base Color"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = bump
    bn.invert = True
    nt.links.new(br.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    return m


def crack_mat(name, color, color2, glow, glow_strength, scale=0.18, width=0.04):
    """Dark rock with glowing cracks along Voronoi cell edges."""
    m = mat(name, color, rough=0.8, color2=color2, noise_scale=0.5, bump=0.4)
    nt = m.node_tree
    b = _bsdf(m)
    tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].position = width
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    b.inputs["Emission Color"].default_value = (*lin(glow), 1)
    nt.links.new(ramp.outputs["Color"], b.inputs["Emission Strength"])
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    mult.inputs[1].default_value = glow_strength
    nt.links.new(ramp.outputs["Color"], mult.inputs[0])
    nt.links.new(mult.outputs[0], b.inputs["Emission Strength"])
    return m


def rings_mat(name, c1, c2, scale=1.2):
    """Wood end grain: concentric rings around the object's Y axis."""
    m = _new_material(name)
    nt = m.node_tree
    b = _bsdf(m)
    b.inputs["Roughness"].default_value = 0.8
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs[0], comb.inputs[0])
    nt.links.new(sep.outputs[2], comb.inputs[1])
    length = nt.nodes.new("ShaderNodeVectorMath")
    length.operation = "LENGTH"
    nt.links.new(comb.outputs[0], length.inputs[0])
    sine = nt.nodes.new("ShaderNodeMath")
    sine.operation = "SINE"
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = scale * 6.28
    nt.links.new(length.outputs["Value"], mul.inputs[0])
    nt.links.new(mul.outputs[0], sine.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.2
    ramp.color_ramp.elements[0].color = (*lin(c2), 1)
    ramp.color_ramp.elements[1].color = (*lin(c1), 1)
    nt.links.new(sine.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


# ---------------------------------------------------------------------------
#   primitives (built with bmesh; parent-local coordinates)
# ---------------------------------------------------------------------------

def empty(name, loc=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    return ob


def _finish(name, bm, material, parent, smooth=True, loc=(0, 0, 0), rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    if material:
        me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def ellipsoid(name, center, radii, material, parent=None, seg=20, rot=(0, 0, 0), jitter=0.0, seed=0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2 + 2), radius=1.0)
    if jitter:
        off = Vector((seed * 7.1, seed * 3.3, seed * 1.7))
        for v in bm.verts:
            v.co *= 1.0 + jitter * noise.noise(v.co * 1.3 + off)
    bmesh.ops.scale(bm, vec=radii, verts=bm.verts)
    return _finish(name, bm, material, parent, loc=center, rot=rot)


def box(name, center, size, material, parent=None, bevel=0.0, rot=(0, 0, 0), smooth=False, segments=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    ob = _finish(name, bm, material, parent, smooth=smooth, loc=center, rot=rot)
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "NONE"
        ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
        mod.harden_normals = False
    return ob


def lathe(name, profile, material, parent=None, seg=24, loc=(0, 0, 0), rot=(0, 0, 0), cap=True):
    """Surface of revolution around local Z from [(r, z), ...] (bottom to top)."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap:
        if profile[0][0] > 0:
            bm.faces.new(list(reversed(rings[0])))
        if profile[-1][0] > 0:
            bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(name, bm, material, parent, loc=loc, rot=rot)


def cylinder(name, r1, r2, depth, material, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), seg=20, smooth=True):
    """Cone/cylinder along local Z from z=0 to z=depth."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=depth)
    bmesh.ops.translate(bm, vec=(0, 0, depth / 2), verts=bm.verts)
    return _finish(name, bm, material, parent, smooth=smooth, loc=loc, rot=rot)


def rock(name, center, radii, material, parent=None, seed=0, rough=0.35, seg=24):
    """A lumpy stone: a sphere pushed in and out by noise."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    off = Vector((seed * 5.3, seed * 2.9, seed * 4.1))
    for v in bm.verts:
        n = noise.fractal(v.co * 1.1 + off, 0.5, 2.0, 3)
        v.co *= 1.0 + rough * n
    bmesh.ops.scale(bm, vec=radii, verts=bm.verts)
    return _finish(name, bm, material, parent, loc=center)


def poly(name, verts, faces, material, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), smooth=True, solidify=0.0):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        bm.faces.new([vs[i] for i in f])
    ob = _finish(name, bm, material, parent, smooth=smooth, loc=loc, rot=rot)
    if solidify:
        mod = ob.modifiers.new("solid", "SOLIDIFY")
        mod.thickness = solidify
    return ob


def rng(seed):
    return random.Random(seed)
