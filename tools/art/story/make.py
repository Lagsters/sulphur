"""Regenerates the story group (bosses, title screen, logo, world maps) from Blender renders.

    python tools/art/story/make.py [--force] [subject ...]

Blender renders each subject large into build/art/story/raw/<subject>/ and is rerun only when a
Blender-side source changed (or with --force); this script then downscales, applies the Amiga
look and packs everything with assetlib.pack_group("story", ...). BLENDER overrides the path to
blender.exe. Subjects: bosses, title, maps, logo.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

import assetlib  # noqa: E402
import catalog  # noqa: E402
import paint  # noqa: E402

BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
RAW = ROOT / "build" / "art" / "story" / "raw"
FONT = HERE / "Cinzel-Black.ttf"
# how many times larger than the final size Blender renders, per subject
SCALE = {"bosses": 4, "title": 2, "maps": 2, "logo": 3}
SOURCES = {"bosses": ["bosses.py"], "title": ["scenery.py", "bosses.py"], "maps": ["scenery.py"],
           "logo": ["logo.py", FONT.name]}


def _stamp(subject):
    h = hashlib.sha256(str(SCALE[subject]).encode())
    for name in ["blib.py", "render.py"] + SOURCES[subject]:
        h.update((HERE / name).read_bytes())
    return h.hexdigest()


def render(subject, force):
    out = RAW / subject
    stamp = out / "stamp.txt"
    want = _stamp(subject)
    if not force and stamp.exists() and stamp.read_text() == want:
        return
    out.mkdir(parents=True, exist_ok=True)
    print(f"rendering {subject} in Blender ...", flush=True)
    cmd = [BLENDER, "-b", "--factory-startup", "-P", str(HERE / "render.py"), "--",
           subject, str(out), str(SCALE[subject])]
    log = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if log.returncode != 0 or "Traceback" in log.stdout + log.stderr:
        sys.stdout.write(log.stdout[-4000:] + log.stderr[-4000:])
        raise SystemExit(f"Blender failed on {subject}")
    stamp.write_text(want)


def raw(subject, name):
    return Image.open(RAW / subject / f"{name}.png").convert("RGBA")


def sprite_frame(im, size):
    """A large render -> a sprite frame: downscaled, sharpened, outlined, 12-bit colour."""
    small = im.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")
    rgb = small.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.0, percent=60, threshold=1))
    small = Image.merge("RGBA", (*rgb.split(), small.getchannel("A")))
    return paint.outline(assetlib.amiga(small, dither=0.7))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    for subject in args or SCALE:
        render(subject, force)
    sprites = []
    for name, n, size, hot in catalog.story_sprites():
        if name.startswith(("utopiec", "jaga", "dragon")):
            frames = [sprite_frame(raw("bosses", f"{name}_{f}"), size) for f in range(n)]
        elif name == "title_bg":
            frames = [paint.title(raw("title", "title"), raw("title", "dragon"), size)]
        elif name == "logo":
            frames = [paint.logo(raw("logo", "logo"), size)]
        elif name == "map_node":
            frames = paint.map_nodes(size)
        elif name.startswith("map_"):
            frames = [paint.world_map(raw("maps", name), size, int(name[-1]))]
        else:
            raise SystemExit(f"no art for {name}")
        assert len(frames) == n and all(f.size == size for f in frames), name
        sprites.append((name, frames, hot))
    paths = assetlib.pack_group("story", sprites)
    pixels = sum(Image.open(p).size[0] * Image.open(p).size[1] for p in paths)
    for p in paths:
        print(p.relative_to(ROOT).as_posix(), Image.open(p).size)
    print(f"story: {len(sprites)} sprites, {pixels} texture pixels ({pixels * 4 / 2**20:.1f} MB RGBA)")


if __name__ == "__main__":
    main()
