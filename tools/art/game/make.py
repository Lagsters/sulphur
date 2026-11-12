"""Builds the game art group: renders the models in Blender, reduces the renders to sprite size,
outlines figures, adds the procedural effects, gives everything the Amiga look and packs it.

    python tools/art/game/make.py [--force] [--only job,job]

Renders are cached under build/art/game/renders/<job>/ with a stamp of the Blender sources they
came from, so a rerun only renders what changed. Final frames also go to build/art/game/frames/
for tools/art/game/preview.py.
"""
import argparse
import hashlib
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
import catalog  # noqa: E402
import fx  # noqa: E402
from assetlib import amiga, pack_group  # noqa: E402

BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
SS = 8
BUILD = ROOT / "build" / "art" / "game"
RENDERS = BUILD / "renders"
FRAMES = BUILD / "frames"

FIGURE_JOBS = ["hero_" + look for look in catalog.LOOKS] + ["dwarf", "bat", "sheep"]
JOBS = ["tiles_" + t for t in catalog.THEMES] + ["misc"] + FIGURE_JOBS
COMMON = ["blender_lib.py", "blender_scene.py"]


def job_stamp(job):
    files = COMMON + (["blender_figures.py", "blender_models.py"] if job in FIGURE_JOBS else ["blender_models.py"])
    h = hashlib.sha256(f"ss={SS}".encode())
    for f in files:
        h.update((HERE / f).read_bytes())
    return h.hexdigest()[:16]


def render(jobs, workers=1):
    """Runs Blender on the jobs in one process: parallel Blenders broke EEVEE shader compilation
    on the GPU driver here (garbled GLSL, a crash)."""
    if not jobs:
        return
    groups = [jobs[i::workers] for i in range(min(workers, len(jobs)))]

    def run(group):
        cmd = [BLENDER, "-b", "--factory-startup", "-P", str(HERE / "blender_scene.py"), "--",
               str(RENDERS), str(SS)] + group
        res = subprocess.run(cmd, capture_output=True, text=True)
        done = [line.split()[-1] for line in res.stdout.splitlines() if line.startswith("JOB DONE")]
        if res.returncode != 0 or set(done) != set(group):
            sys.stderr.write(res.stdout[-4000:] + res.stderr[-4000:])
            raise SystemExit(f"Blender failed on {group}")
        for job in group:
            (RENDERS / job / "stamp").write_text(job_stamp(job))
        print("rendered", " ".join(group), flush=True)

    with ThreadPoolExecutor(len(groups)) as pool:
        list(pool.map(run, groups))


def stale(jobs):
    out = []
    for job in jobs:
        stamp = RENDERS / job / "stamp"
        if not stamp.exists() or stamp.read_text() != job_stamp(job):
            out.append(job)
    return out


# ---------------------------------------------------------------------------
#   post-processing
# ---------------------------------------------------------------------------

def load(job, name):
    return Image.open(RENDERS / job / f"{name}.png").convert("RGBA")


def shrink(img, size):
    """Premultiplied Lanczos reduction (sharper than a box, which smears 20 px tiles)."""
    a = np.asarray(img).astype(np.float32) / 255
    pm = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1)
    ch = [np.asarray(Image.fromarray(pm[..., i], "F").resize(size, Image.LANCZOS, reducing_gap=3.0)) for i in range(4)]
    out = np.clip(np.stack(ch, -1), 0, 1)
    al = out[..., 3:4]
    rgb = np.where(al > 1e-3, out[..., :3] / np.maximum(al, 1e-3), 0)
    return np.concatenate([np.clip(rgb, 0, 1), al], -1)


def tone(rgba, gain=1.0, gamma=1.0, sat=1.0, contrast=1.0, tint=None):
    rgb = rgba[..., :3]
    rgb = np.clip(rgb * gain, 0, 1) ** gamma
    lum = (rgb * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
    rgb = lum + (rgb - lum) * sat
    mean = 0.35
    rgb = mean + (rgb - mean) * contrast
    if tint is not None:
        rgb = rgb * np.asarray(tint, np.float32)
    return np.concatenate([np.clip(rgb, 0, 1), rgba[..., 3:4]], -1)


def to_image(rgba, opaque=False):
    a = rgba.copy()
    if opaque:
        a[..., 3] = 1.0
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")


def sharpen(img, amount=60):
    rgb = img.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.8, percent=amount, threshold=1))
    out = rgb.convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


def outline(img, strength=0.28, corners=False):
    """A 1 px dark outline around the opaque shape, tinted by the colour it borders."""
    a = np.asarray(img).astype(np.int32)
    on = a[..., 3] > 0
    h, w = on.shape
    acc = np.zeros((h, w, 3), np.int32)
    cnt = np.zeros((h, w), np.int32)
    steps = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    if corners:
        steps += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    for dy, dx in steps:
        sh_on = np.zeros_like(on)
        sh_rgb = np.zeros_like(acc)
        ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
        xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
        sh_on[yd, xd] = on[ys, xs]
        sh_rgb[yd, xd] = a[ys, xs, :3]
        acc += sh_rgb * sh_on[..., None]
        cnt += sh_on
    edge = (~on) & (cnt > 0)
    col = acc / np.maximum(cnt, 1)[..., None] * strength + np.array([6, 4, 10]) * (1 - strength)
    out = a.copy()
    out[edge, :3] = np.clip(col[edge], 0, 255)
    out[edge, 3] = 255
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def tile(job, name, f, **tn):
    src = load(job, f"{name}_{f}")
    rgba = tone(shrink(src, (20, 20)), **tn)
    return amiga(sharpen(to_image(rgba, opaque=True), 50))


def sprite(job, name, size, edge=True, sharp=70, corners=False, **tn):
    src = load(job, name)
    rgba = tone(shrink(src, size), **tn)
    img = to_image(rgba)
    img = sharpen(img, sharp)
    img = amiga(img)
    return outline(img, corners=corners) if edge else img


def opaque_cut(img, threshold=0.5):
    """Alpha to 0/1 at a threshold (amiga() does it at 128; this lets thin parts survive)."""
    a = np.asarray(img).copy()
    a[..., 3] = np.where(a[..., 3] >= threshold * 255, 255, 0)
    return Image.fromarray(a, "RGBA")


# per-sprite tone: floors dark and quiet, crates warm and bright, figures punchy
FLOOR = dict(gain=0.82, contrast=0.8, sat=0.9)
TILE_TONE = {
    "floor_town": dict(gain=0.85, contrast=0.85, sat=0.95),
    "floor_forest": dict(gain=0.9, contrast=0.85, sat=1.0),
    "floor_castle": dict(gain=0.8, contrast=0.8, sat=0.9),
    "crate": dict(gain=1.1, sat=1.15, contrast=1.1),
    "pillar_castle": dict(gain=0.88, sat=1.05, contrast=1.15),
    "pillar": dict(gain=1.05, sat=1.05, contrast=1.2),
    "wall": dict(gain=0.95, contrast=1.05),
    "zone": dict(gain=1.0, contrast=1.1),
}
FIGURE = dict(gain=1.08, sat=1.2, contrast=1.12)


def tone_for(name):
    for key, t in TILE_TONE.items():
        if name.startswith(key):
            return t
    return {}


def make_sprite(name, n, size):
    """The frames of one catalog sprite."""
    w, h = size
    if name.split("_")[0] in ("floor", "pillar", "wall", "crate"):
        theme = name.split("_")[1]
        return [tile(f"tiles_{theme}", name, f, **tone_for(name)) for f in range(n)]
    if name == "zone":
        return [tile("misc", name, 0, **tone_for(name))]
    if name == "item_exit":
        return [tile("misc", name, f) for f in range(n)]
    if name in ("bomb",) or name.startswith("item_"):
        return [sprite("misc", f"{name}_{f}", size, sat=1.15, contrast=1.1) for f in range(n)]
    if name in ("icon_bomb", "icon_range", "icon_shield", "icon_key", "icon_heart"):
        return [sprite("misc", f"{name}_0", size, sat=1.15, contrast=1.1)]
    if name == "icon_sheep":
        return [sprite("sheep", "icon_sheep_0", size, **FIGURE)]
    if name.startswith("icon_head_"):
        look = name[len("icon_head_"):]
        return [sprite(f"hero_{look}", f"{name}_0", size, **FIGURE)]
    if name.startswith("hero_") and name.endswith("_die"):
        look = name[5:-4]
        frames = []
        for f in range(n):
            base = None
            if f < 4:
                base = sprite(f"hero_{look}", f"{name}_{f}", size, **FIGURE)
            frames.append(outline(amiga(fx.die_frame(base, f)), strength=0.3) if f >= 1 else base)
        return frames
    if name.startswith("hero_"):
        look = name[5:].rsplit("_", 1)[0]
        return [sprite(f"hero_{look}", f"{name}_{f}", size, **FIGURE) for f in range(n)]
    if name.startswith(("dwarf_", "sheep_")):
        job = name.split("_")[0]
        return [sprite(job, f"{name}_{f}", size, **FIGURE) for f in range(n)]
    if name == "bat":
        return [sprite("bat", f"bat_{f}", size, **FIGURE) for f in range(n)]
    if name == "fire":
        return [amiga(fx.fire(f)) for f in range(n)]
    if name == "fire_sheep":
        return [amiga(fx.fire_sheep(f)) for f in range(n)]
    if name == "spark":
        return [amiga(fx.spark(f), dither=0.5) for f in range(n)]
    if name == "sparkle":
        return [amiga(fx.sparkle(f), dither=0.5) for f in range(n)]
    if name == "shadow":
        return [fx.shadow()]
    if name == "zone_warn":
        return [fx.zone_warn()]
    raise KeyError(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="render every job again")
    ap.add_argument("--only", help="render only these jobs (comma separated), then pack")
    ap.add_argument("--no-render", action="store_true", help="pack from the cached renders")
    args = ap.parse_args()
    RENDERS.mkdir(parents=True, exist_ok=True)
    if not args.no_render:
        jobs = args.only.split(",") if args.only else (JOBS if args.force else stale(JOBS))
        render(jobs)
    FRAMES.mkdir(parents=True, exist_ok=True)
    for old in FRAMES.glob("*.png"):
        old.unlink()
    packed = []
    pixels = 0
    for name, n, size, hot in catalog.game_sprites():
        frames = make_sprite(name, n, size)
        assert len(frames) == n, name
        for f, im in enumerate(frames):
            assert im.size == size, (name, im.size)
            im.save(FRAMES / f"{name}_{f}.png")
        packed.append((name, frames, hot))
    paths = pack_group("game", packed)
    for p in paths:
        with Image.open(p) as im:
            pixels += im.width * im.height
            print(f"{p.relative_to(ROOT).as_posix()}: {im.width}x{im.height}")
    print(f"game group: {len(packed)} sprites, {pixels * 4 / 1e6:.2f} MB of texture pixels")


if __name__ == "__main__":
    main()
