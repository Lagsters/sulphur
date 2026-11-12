"""Builds the scenes group: renders the cast and the backdrops in Blender, brings them down to
the final size with the Amiga look, paints the effects and packs it all.

    python tools/scenes/make.py              render what is missing, then pack
    python tools/scenes/make.py --render     render everything again (a few minutes)
    python tools/scenes/make.py --only cast|backdrops [name ...]   re-render some, then pack

Blender renders land in build/scenes/raw (twice the final size). Output: assets/scenes/tex*.png,
assets/scenes/rom.txt, src/gen/scenes.h, assets/scenes/meta.json (anchors and walk strides for
tools/scenes/script.py), then the script runs and writes src/gen/scene_text.h.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from assetlib import ROOT, amiga, pack_group  # noqa: E402

BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
RAW = ROOT / "build/scenes/raw"
BACKDROPS = ("wawel_night", "rynek", "workshop", "odra", "sleza", "krakow", "den", "hall")
CAST = ("dratewka", "wanda", "herald", "krak", "witch", "jaga", "utopiec", "dragon", "sheep", "props")
# sprites the cast jobs write, in the order they go into the group
CAST_SPRITES = ("dratewka", "wanda", "herald", "krak", "witch", "jaga", "utopiec", "dragon_fly", "dragon",
                "sheep", "sack", "cheese", "bomb", "bust_dratewka", "bust_dratewka_soot", "bust_wanda",
                "bust_krak", "bust_jaga", "bust_utopiec")
BUDGET = 12 * 1024 * 1024


def blender(script, args):
    cmd = [BLENDER, "-b", "--factory-startup", "-P", str(HERE / "blender" / script), "--", str(RAW), *args]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0 or "Traceback" in out.stdout + out.stderr:
        sys.exit(out.stdout[-3000:] + out.stderr[-3000:])


def render(force, only=None, names=()):
    RAW.mkdir(parents=True, exist_ok=True)
    if only in (None, "cast"):
        todo = list(names) if only else [c for c in CAST if force or not (RAW / f"{c if c != 'props' else 'bomb'}.json").exists()]
        if todo:
            print("blender: cast", " ".join(todo))
            blender("cast.py", todo)
    if only in (None, "backdrops"):
        todo = list(names) if only else [b for b in BACKDROPS if force or not (RAW / f"bd_{b}.json").exists()]
        if todo:
            print("blender: backdrops", " ".join(todo))
            blender("backdrops.py", todo)


# ---------------------------------------------------------------------------
#   from renders to sprites
# ---------------------------------------------------------------------------

def down(im, size):
    """Downscale with premultiplied alpha, so edges do not pick up the transparent black."""
    return im.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")


def crop_frames(frames, hot):
    """Crops all frames to the box their pixels share; returns frames and the moved hotspot."""
    boxes = [f.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox() for f in frames]
    boxes = [b for b in boxes if b]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    # keep the hotspot inside the frame and the frame even-sized around a centred hotspot
    x0, x1 = min(x0, hot[0]), max(x1, hot[0] + 1)
    y0, y1 = min(y0, hot[1]), max(y1, hot[1] + 1)
    return [f.crop((x0, y0, x1, y1)) for f in frames], (hot[0] - x0, hot[1] - y0)


def cast_sprite(name):
    meta = json.loads((RAW / f"{name}.json").read_text())
    w, h = meta["w"], meta["h"]
    frames = [amiga(down(Image.open(RAW / f"{name}_{k}.png"), (w, h))) for k in range(meta["frames"])]
    frames, hot = crop_frames(frames, tuple(meta["hot"]))
    return (name, frames, hot), meta


def backdrop(name):
    """680 x 280 with its own 32 colours (12-bit), as two sprites of 340 x 280 (left, right):
    three halves fill a row of a texture, nine a texture."""
    im = Image.open(RAW / f"bd_{name}.png").convert("RGB").resize((680, 280), Image.LANCZOS)
    q = im.quantize(32, method=Image.Quantize.MEDIANCUT)
    pal = np.array(q.getpalette()[:96]).reshape(-1, 3)
    pal = np.unique(np.round(pal / 17) * 17, axis=0)
    out = amiga(im.convert("RGBA"), palette=[tuple(p) for p in pal], dither=1.0)
    meta = json.loads((RAW / f"bd_{name}.json").read_text())
    return [(f"bd_{name}", [out.crop((0, 0, 340, 280))], (0, 0)),
            (f"bd_{name}_r", [out.crop((340, 0, 680, 280))], (0, 0))], meta


# ---------------------------------------------------------------------------
#   effects and the poster, painted here
# ---------------------------------------------------------------------------

RNG = np.random.default_rng(1234)


def noise(w, h, cell, seed):
    r = np.random.default_rng(seed).random((h // cell + 2, w // cell + 2)).astype(np.float32)
    img = Image.fromarray((r * 255).astype(np.uint8)).resize(((w // cell + 2) * cell, (h // cell + 2) * cell), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32)[:h, :w] / 255


def fbm(w, h, seed):
    return (noise(w, h, 16, seed) * 0.5 + noise(w, h, 8, seed + 1) * 0.3 + noise(w, h, 4, seed + 2) * 0.2)


def ramp(v, stops):
    """Colours along v in 0..1 from (position, (r, g, b)) stops."""
    pos = np.array([p for p, _ in stops])
    cols = np.array([c for _, c in stops], dtype=np.float32)
    out = np.zeros(v.shape + (3,), np.float32)
    for k in range(3):
        out[..., k] = np.interp(v, pos, cols[:, k])
    return out


def rgba(rgb, alpha):
    return amiga(Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(alpha, 0, 255)]).astype(np.uint8), "RGBA"))


def radial(w, h, cx=None, cy=None):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    return np.hypot(x - cx, y - cy), np.arctan2(y - cy, x - cx)


def boom():
    """A sulphur blast: a white flash, a yellow-orange fireball, rolling into dark smoke."""
    s, frames = 112, []
    d, _ = radial(s, s)
    for f in range(6):
        k = (f + 1) / 6
        n = fbm(s, s, 10 + f)
        r = 18 + 36 * k ** 0.6
        v = 1 - d / r + (n - 0.5) * 0.9
        heat = np.clip(v * 1.4 - k * 0.9 + 0.5, 0, 1)
        col = ramp(heat, [(0, (40, 30, 30)), (0.3, (120, 50, 20)), (0.55, (230, 110, 20)), (0.8, (255, 210, 60)), (1, (255, 255, 230))])
        frames.append(rgba(col, (v > 0.05) * 255))
    return ("boom", frames, (56, 56))


def smoke():
    s, frames = 64, []
    d, _ = radial(s, s)
    for f in range(6):
        k = (f + 1) / 6
        n = fbm(s, s, 40 + f)
        v = 1 - d / (12 + 18 * k) + (n - 0.5) * 0.8
        col = ramp(np.clip(v + 0.3 - 0.3 * k, 0, 1), [(0, (60, 56, 52)), (1, (170, 160, 150))])
        frames.append(rgba(col, (v > 0.1 + 0.25 * k * k) * 255))
    return ("smoke", frames, (32, 32))


def magic():
    """Green witch light: a spiral of motes around a glowing core, drawn added."""
    s, frames = 96, []
    d, a = radial(s, s)
    for f in range(4):
        ph = f / 4 * 2 * np.pi
        arms = np.cos(3 * a - d / 6 + ph)
        n = noise(s, s, 6, 60 + f)
        v = np.clip(arms * 0.6 + n * 0.6 - d / 48, 0, 1) * (d < 46)
        v = np.maximum(v, np.clip(1 - d / 14, 0, 1))
        col = ramp(v, [(0, (0, 40, 10)), (0.5, (40, 200, 60)), (1, (220, 255, 200))])
        frames.append(rgba(col, (v > 0.18) * 255))
    return ("magic", frames, (48, 48))


def firework():
    """One burst: sparks flying out along rays and falling, drawn added and tinted in C."""
    s, frames = 96, []
    rays = RNG.random(36) * 2 * np.pi
    speed = 0.7 + RNG.random(36) * 0.3
    for f in range(5):
        k = (f + 1) / 5
        img = np.zeros((s, s), np.float32)
        for a, sp in zip(rays, speed):
            for tail in range(6):
                kk = max(0.0, k - tail * 0.03)
                r = 42 * sp * (1 - (1 - kk) ** 2)
                x = int(s / 2 + np.cos(a) * r)
                y = int(s / 2 + np.sin(a) * r + 10 * kk * kk)
                if 1 <= x < s - 1 and 1 <= y < s - 1:
                    img[y - 1:y + 1, x - 1:x + 1] = max(img[y, x], 1 - tail * 0.15 - k * 0.3)
        col = ramp(img, [(0, (0, 0, 0)), (0.4, (180, 180, 180)), (1, (255, 255, 255))])
        frames.append(rgba(col, (img > 0.1) * 255))
    return ("firework", frames, (48, 48))


def spark():
    """A twinkling star: the lit fuse, an idea, the bugle's glint."""
    s, frames = 32, []
    d, a = radial(s, s)
    for f in range(4):
        arms = np.abs(np.cos(2 * a + f * 0.4)) ** 30 * np.clip(1 - d / (10 + 4 * (f % 2)), 0, 1)
        v = np.maximum(arms, np.clip(1 - d / (4 + f % 2), 0, 1))
        col = ramp(v, [(0, (255, 120, 0)), (0.5, (255, 220, 80)), (1, (255, 255, 255))])
        frames.append(rgba(col, (v > 0.15) * 255))
    return ("spark", frames, (16, 16))


def soot():
    """Flakes of soot and wisps drifting off a scorched face."""
    w, h, frames = 96, 80, []
    pts = RNG.random((22, 2)) * [w, h]
    for f in range(3):
        img = np.zeros((h, w, 4), np.float32)
        for k, (x, y) in enumerate(pts):
            yy = int((y - f * 6 - k % 3 * 2) % h)
            xx = int(x + 3 * np.sin(f + k))
            sz = 2 + k % 3
            img[yy:yy + sz, xx:xx + sz] = (30, 26, 24, 255) if k % 4 else (90, 84, 80, 255)
        frames.append(amiga(Image.fromarray(img.astype(np.uint8), "RGBA")))
    return ("soot", frames, (48, 40))


def flame():
    """The Kupala bonfire's flames, flickering over the painted fire."""
    w, h, frames = 48, 64, []
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    for f in range(4):
        n = noise(w, h + 32, 6, 90 + f)[f * 8:f * 8 + h]
        width = (y / h) ** 0.8 * 20 + 2
        v = 1 - np.abs(x - w / 2 + (n - 0.5) * 10) / width - (1 - y / h) * 0.4 + (n - 0.5) * 0.5
        col = ramp(np.clip(v, 0, 1), [(0, (200, 40, 0)), (0.4, (255, 120, 20)), (0.8, (255, 220, 80)), (1, (255, 255, 200))])
        frames.append(rgba(col, (v > 0.05) * 255))
    return ("flame", frames, (24, 63))


def parchment(w, h, seed):
    n = fbm(w, h, seed)
    col = ramp(n, [(0, (170, 130, 80)), (0.5, (220, 190, 140)), (1, (240, 220, 175))])
    d = np.minimum.reduce([np.mgrid[0:h, 0:w][1], np.mgrid[0:h, 0:w][0],
                           w - 1 - np.mgrid[0:h, 0:w][1], h - 1 - np.mgrid[0:h, 0:w][0]]).astype(np.float32)
    edge = d + (n - 0.5) * 12
    col *= np.clip(edge / 10, 0.45, 1)[..., None]
    return col, (edge > 1) * 255.0


def posters(dragon_frame):
    """The king's poster: on the board (small) and in close-up, a dragon drawn in soot; the
    words go on in C, in the player's language."""
    w, h = 240, 190
    col, alpha = parchment(w, h, 7)
    dr = down(dragon_frame, (dragon_frame.width * 2 // 3, dragon_frame.height * 2 // 3))
    a = np.asarray(dr)[..., 3] > 100
    ox, oy = (w - dr.width) // 2, 56
    region = col[oy:oy + dr.height, ox:ox + dr.width]
    region[a[:region.shape[0], :region.shape[1]]] = (70, 40, 20)
    for cx, cy in ((10, 10), (w - 11, 10), (10, h - 11), (w - 11, h - 11)):
        col[cy - 3:cy + 3, cx - 3:cx + 3] = (60, 60, 70)
    big = rgba(col, alpha)
    small = amiga(down(Image.fromarray(np.dstack([col, alpha]).astype(np.uint8), "RGBA"), (34, 31)))
    return [("poster_big", [big], (w // 2, h // 2)), ("poster", [small], (17, 15))]


# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if "--only" in args:
        i = args.index("--only")
        render(False, args[i + 1], args[i + 2:])
    else:
        render("--render" in args)
    sprites, meta = [], {"stride": {}, "anchors": {}, "hot": {}}
    for b in BACKDROPS:
        sp, m = backdrop(b)
        sprites += sp
        meta["anchors"][b] = m["anchors"]
    dragon_frame = None
    for name in CAST_SPRITES:
        sp, m = cast_sprite(name)
        sprites.append(sp)
        if "stride" in m:
            meta["stride"][name] = m["stride"]
        if name == "dragon_fly":
            dragon_frame = sp[1][0]
    sprites += [boom(), smoke(), magic(), firework(), spark(), soot(), flame()]
    sprites += posters(dragon_frame)
    for name, frames, hot in sprites:
        meta["hot"][name] = [frames[0].width, frames[0].height, hot[0], hot[1]]
    paths = pack_group("scenes", sprites)
    (ROOT / "assets/scenes/meta.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    used = sum(Image.open(p).width * Image.open(p).height * 4 for p in paths)
    print(f"scenes: {len(sprites)} sprites in {len(paths)} textures, {used / 1048576:.2f} MB of {BUDGET / 1048576:.0f} MB")
    if used > BUDGET:
        sys.exit("scenes: over the texture budget")
    subprocess.run([sys.executable, str(HERE / "script.py")], check=True)


if __name__ == "__main__":
    main()
