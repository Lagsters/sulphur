"""Models and renders the game group's art in Blender; make.py runs it, not people:

    blender -b --factory-startup -P blender_scene.py -- <out dir> <ss> <job> [<job> ...]

Each job builds its models from primitives and writes <out dir>/<job>/<sprite>_<frame>.png at
<ss> times the sprite's size (tiles: 20*ss wide, 20*ss*sin(55 deg) tall; make.py stretches them).
"""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_lib as L  # noqa: E402
import blender_models as M  # noqa: E402

TILE = 20


def tile_frame(out, name, frame, ss):
    L.camera(TILE, TILE, ss, ground_square=True)
    L.render(os.path.join(out, f"{name}_{frame}.png"))


def job_tiles(theme, out, ss):
    floor = getattr(M, f"floor_{theme}")
    for v in range(4):
        L.clear_objects()
        floor(v)
        tile_frame(out, f"floor_{theme}", v, ss)
    for kind in ("pillar", "wall", "crate"):
        L.clear_objects()
        getattr(M, f"{kind}_{theme}")()
        tile_frame(out, f"{kind}_{theme}", 0, ss)


def job_misc(out, ss):
    L.clear_objects()
    M.zone()
    tile_frame(out, "zone", 0, ss)
    for f, glow in enumerate((False, True)):
        L.clear_objects()
        M.trapdoor(glow)
        tile_frame(out, "item_exit", f, ss)
    for f in range(4):
        L.clear_objects()
        M.bomb(f)
        L.camera(TILE, TILE, ss, offset=(0, -1.5))
        L.render(os.path.join(out, f"bomb_{f}.png"))
    for item in ("bomb", "range", "shield", "key"):
        L.clear_objects()
        getattr(M, f"item_{item}")()
        L.camera(TILE, TILE, ss, offset=(0, -1))
        L.render(os.path.join(out, f"item_{item}_0.png"))
    # HUD icons: the same objects, closer and more from the front
    for item, scale in (("bomb", 1.0), ("range", 0.95), ("shield", 0.95), ("key", 0.95)):
        L.clear_objects()
        getattr(M, f"icon_{item}")()
        L.camera(16 / scale, 16 / scale, ss * scale, offset=(0, 0), elev=math.radians(30))
        L.render(os.path.join(out, f"icon_{item}_0.png"))
    L.clear_objects()
    M.heart()
    L.camera(16, 16, ss, elev=math.radians(10))
    L.render(os.path.join(out, "icon_heart_0.png"))


def job_hero(look, out, ss):
    L.clear_objects()
    rig = M.hero(look)
    w, h = 24, 32
    for d, rot in M.DIR_ROT.items():
        rig.root.rotation_euler = (0, 0, rot)
        for f in range(8):
            rig.walk(f / 8)
            L.camera(w, h, ss, offset=(0, -h / 2 + M.FEET_UP))
            L.render(os.path.join(out, f"hero_{look}_{d}_{f}.png"))
    rig.root.rotation_euler = (0, 0, M.DIR_ROT["down"])
    for f in range(4):
        rig.die(f)
        L.camera(w, h, ss, offset=(0, -h / 2 + M.FEET_UP))
        L.render(os.path.join(out, f"hero_{look}_die_{f}.png"))
    rig.walk(0)
    rig.root.rotation_euler = (0, 0, M.DIR_ROT["down"])
    L.camera(16 / 1.25, 16 / 1.25, ss * 1.25, center=rig.head_center(), offset=(0, 0.4), elev=math.radians(20))
    L.render(os.path.join(out, f"icon_head_{look}_0.png"))


def job_dwarf(out, ss):
    L.clear_objects()
    rig = M.dwarf()
    w, h = 20, 24
    for d, rot in M.DIR_ROT.items():
        rig.root.rotation_euler = (0, 0, rot)
        for f in range(4):
            rig.walk(f / 4)
            L.camera(w, h, ss, offset=(0, -h / 2 + M.FEET_UP))
            L.render(os.path.join(out, f"dwarf_{d}_{f}.png"))


def job_bat(out, ss):
    L.clear_objects()
    rig = M.bat()
    for f in range(6):
        rig.flap(f / 6)
        L.camera(24, 20, ss, offset=(0, 0))
        L.render(os.path.join(out, f"bat_{f}.png"))


def job_sheep(out, ss):
    L.clear_objects()
    rig = M.sheep()
    w, h = 24, 22
    for d, rot in M.DIR_ROT.items():
        rig.root.rotation_euler = (0, 0, rot)
        for f in range(6):
            rig.run(f / 6)
            L.camera(w, h, ss, offset=(0, -h / 2 + M.FEET_UP))
            L.render(os.path.join(out, f"sheep_{d}_{f}.png"))
    rig.root.rotation_euler = (0, 0, M.DIR_ROT["left"] + math.radians(-25))
    for f in range(4):
        rig.graze(f)
        L.camera(w, h, ss, offset=(0, -h / 2 + M.FEET_UP))
        L.render(os.path.join(out, f"sheep_graze_{f}.png"))
    rig.run(0)
    rig.root.rotation_euler = (0, 0, math.radians(-30))
    L.camera(19, 19, ss * 16 / 19, center=(0, -2, 7), elev=math.radians(30))
    L.render(os.path.join(out, "icon_sheep_0.png"))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_root, ss, jobs = argv[0], float(argv[1]), argv[2:]
    L.reset_scene()
    L.lights()
    for job in jobs:
        out = os.path.join(out_root, job)
        os.makedirs(out, exist_ok=True)
        if job.startswith("tiles_"):
            job_tiles(job[6:], out, ss)
        elif job.startswith("hero_"):
            job_hero(job[5:], out, ss)
        else:
            globals()[f"job_{job}"](out, ss)
        print(f"JOB DONE {job}", flush=True)


main()
