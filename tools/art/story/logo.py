"""The SULPHUR logo: heavy gilded letters in Cinzel Black (SIL OFL 1.1, the variable font
instanced at weight 900), extruded and bevelled, lit like polished gold over dark stone (runs inside
Blender). Not Cinzel Decorative: its swash L reads as an I, so the word looked like "SUIPHUR"."""
import math
from pathlib import Path

import bpy

import blib
from blib import material

FONT = Path(__file__).resolve().parent / "Cinzel-Black.ttf"


def render_logo(out, scale):
    s = blib.reset(samples=64)
    w, h = 480 * scale, 120 * scale
    s.render.resolution_x, s.render.resolution_y = w, h
    curve = bpy.data.curves.new("logo", "FONT")
    curve.body = "SULPHUR"
    curve.font = bpy.data.fonts.load(str(FONT))
    curve.align_x, curve.align_y = "CENTER", "CENTER"
    curve.size = 1.0
    curve.space_character = 1.05
    curve.extrude = 0.16
    curve.bevel_depth = 0.035
    curve.bevel_resolution = 3
    ob = blib.link(bpy.data.objects.new("logo", curve))
    ob.rotation_euler = (math.radians(90), 0, 0)
    gold = material("logo_gold", (1.0, 0.72, 0.22), rough=0.22, metal=1.0, colour2=(0.85, 0.55, 0.12),
                    mix_scale=3, bump=0.25, bump_scale=14)
    curve.materials.append(gold)
    # a slight look up at the letters makes them monumental
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = 4.75
    cob = bpy.data.objects.new("cam", cam)
    s.collection.objects.link(cob)
    cob.location = (0, -20, -2.2)
    cob.rotation_euler = blib.look_rotation((0, 20, 2.2))
    s.camera = cob
    blib.sun((0.5, 0.6, -0.6), (1.0, 0.92, 0.75), 4.5, angle=4)
    blib.sun((-0.6, 0.3, 0.5), (1.0, 0.85, 0.2), 2.5, angle=8, shadow=False)
    blib.sun((0.0, -1.0, 0.2), (0.5, 0.4, 0.8), 1.0, shadow=False)
    # an environment of warm light above and dark below, for the gold to reflect
    world = s.world
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.05, 0.02, 0.02, 1)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (1.0, 0.8, 0.45, 1)
    mid = ramp.color_ramp.elements.new(0.52)
    mid.color = (0.5, 0.2, 0.08, 1)
    to01 = nt.nodes.new("ShaderNodeMapRange")
    to01.inputs["From Min"].default_value = -1
    nt.links.new(sep.outputs["Z"], to01.inputs["Value"])
    nt.links.new(to01.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.2
    blib.render(out / "logo.png")
