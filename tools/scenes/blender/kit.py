"""Blender helpers shared by the scene renders: a clean scene, painted materials, primitives,
lights and the render settings. Runs inside Blender 5.2 (bpy)."""
import math
import os

import bpy
from mathutils import Vector

RAD = math.pi / 180


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()
    s = bpy.context.scene
    try:
        s.render.engine = "BLENDER_EEVEE"
    except TypeError:
        s.render.engine = "BLENDER_EEVEE_NEXT"
    s.eevee.taa_render_samples = 32
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    s.render.resolution_percentage = 100
    w = bpy.data.worlds.new("world")
    s.world = w
    return s


def hexcol(h, a=1.0):
    """'#rrggbb' (sRGB) -> linear RGBA for shader inputs."""
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, a)


_mats = {}


def mat(color, rough=0.6, metal=0.0, emit=None, strength=1.0, noise=0.0, color2=None, scale=8.0):
    """A material; noise > 0 mixes color with color2 (or a darker shade) by a noise texture,
    the brush texture of a painted surface."""
    key = (color, rough, metal, emit, strength, noise, color2, scale)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"m{len(_mats)}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    base = hexcol(color)
    if noise > 0:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = 6
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        c2 = hexcol(color2) if color2 else tuple(v * 0.45 for v in base[:3]) + (1,)
        ramp.color_ramp.elements[0].position = 0.5 - noise / 2
        ramp.color_ramp.elements[1].position = 0.5 + noise / 2
        ramp.color_ramp.elements[0].color = c2
        ramp.color_ramp.elements[1].color = base
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = base
    if emit:
        bsdf.inputs["Emission Color"].default_value = hexcol(emit)
        bsdf.inputs["Emission Strength"].default_value = strength
    _mats[key] = m
    return m


def _finish(obj, material, parent, smooth):
    if material is not None:
        obj.data.materials.append(material)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    if parent is not None:
        obj.parent = parent
    return obj


def box(size, loc, material=None, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=[r * RAD for r in rot])
    o = bpy.context.object
    o.scale = size
    return _finish(o, material, parent, False)


def ball(radius, loc, material=None, parent=None, scale=(1, 1, 1), seg=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=radius,
                                         location=loc, rotation=[r * RAD for r in rot])
    o = bpy.context.object
    o.scale = scale
    return _finish(o, material, parent, True)


def cyl(r1, r2, depth, loc, material=None, parent=None, rot=(0, 0, 0), verts=20, scale=(1, 1, 1)):
    """A cone frustum along local z, centred at loc."""
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth,
                                    location=loc, rotation=[r * RAD for r in rot])
    o = bpy.context.object
    o.scale = scale
    return _finish(o, material, parent, True)


def limb(r1, r2, length, material, parent):
    """A limb hanging from its parent's origin down along -z (a joint at the top)."""
    o = cyl(r1, r2, length, (0, 0, -length / 2), material, parent)
    ball(r1 * 1.02, (0, 0, 0), material, parent)
    return o


def empty(loc, parent=None, name="e"):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if parent is not None:
        o.parent = parent
    return o


def mesh(verts, faces, material=None, parent=None, loc=(0, 0, 0), smooth=True):
    me = bpy.data.meshes.new("mesh")
    me.from_pydata([Vector(v) for v in verts], [], faces)
    me.update()
    o = bpy.data.objects.new("mesh", me)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return _finish(o, material, parent, smooth)


def displace(obj, strength, scale, kind="CLOUDS", subdiv=0):
    if subdiv:
        m = obj.modifiers.new("sub", "SUBSURF")
        m.levels = m.render_levels = subdiv
        m.subdivision_type = "SIMPLE"
    t = bpy.data.textures.new("tex", kind)
    t.noise_scale = scale
    m = obj.modifiers.new("disp", "DISPLACE")
    m.texture = t
    m.strength = strength
    return obj


def sun(rot, energy=3.0, color="#ffffff", angle=4.0):
    d = bpy.data.lights.new("sun", "SUN")
    d.energy = energy
    d.color = hexcol(color)[:3]
    d.angle = angle * RAD
    o = bpy.data.objects.new("sun", d)
    bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = [r * RAD for r in rot]
    return o


def point(loc, energy=100.0, color="#ffffff", radius=0.1):
    d = bpy.data.lights.new("pt", "POINT")
    d.energy = energy
    d.color = hexcol(color)[:3]
    d.shadow_soft_size = radius
    o = bpy.data.objects.new("pt", d)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return o


def world_color(color, strength=1.0):
    w = bpy.context.scene.world
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = hexcol(color)
    bg.inputs["Strength"].default_value = strength


def sky(stops, stars=0.0, light=None, light_strength=0.3):
    """A painted sky behind everything: colour stops (height 0..1 of the view, '#rrggbb') over
    the window coordinates, stars scattered when stars > 0. The world lights the scene with
    `light` (a flat colour) so the gradient does not tint everything."""
    w = bpy.context.scene.world
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Window"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], hexcol(stops[0][1])
    els[1].position, els[1].color = stops[-1][0], hexcol(stops[-1][1])
    for pos, col in stops[1:-1]:
        e = els.new(pos)
        e.color = hexcol(col)
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    color = ramp.outputs["Color"]
    if stars > 0:
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 160
        nt.links.new(coord.outputs["Window"], vor.inputs["Vector"])
        cmp = nt.nodes.new("ShaderNodeMath")
        cmp.operation = "LESS_THAN"
        cmp.inputs[1].default_value = stars
        nt.links.new(vor.outputs["Distance"], cmp.inputs[0])
        add = nt.nodes.new("ShaderNodeMix")
        add.data_type = "RGBA"
        add.blend_type = "ADD"
        nt.links.new(cmp.outputs[0], add.inputs["Factor"])
        nt.links.new(color, add.inputs["A"])
        add.inputs["B"].default_value = (0.9, 0.9, 0.8, 1)
        color = add.outputs["Result"]
    cam_bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(color, cam_bg.inputs["Color"])
    lit = nt.nodes.new("ShaderNodeBackground")
    lit.inputs["Color"].default_value = hexcol(light or "#404050")
    lit.inputs["Strength"].default_value = light_strength
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(lit.outputs[0], mix.inputs[1])
    nt.links.new(cam_bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def camera(loc, look_at, ortho=None, lens=35):
    c = bpy.data.cameras.new("cam")
    if ortho:
        c.type = "ORTHO"
        c.ortho_scale = ortho
    else:
        c.lens = lens
    c.clip_end = 2000
    o = bpy.data.objects.new("cam", c)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    d = Vector(look_at) - Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = o
    return o


def outline(thickness=1.6, color="#100808"):
    """Freestyle contour lines: the drawn outline of a painted sprite."""
    s = bpy.context.scene
    s.render.use_freestyle = True
    s.render.line_thickness_mode = "ABSOLUTE"
    vl = s.view_layers[0]
    ls = vl.freestyle_settings.linesets[0] if vl.freestyle_settings.linesets else vl.freestyle_settings.linesets.new("l")
    ls.select_by_visibility = True
    ls.select_by_edge_types = True
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = False
    if ls.linestyle is None:
        ls.linestyle = bpy.data.linestyles.new("line")
    ls.linestyle.thickness = thickness
    ls.linestyle.color = hexcol(color)[:3]


def render(path, w, h, transparent=True):
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = w, h
    s.render.film_transparent = transparent
    s.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)
