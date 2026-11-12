"""Procedural effects in numpy: fire, sulphur smoke, sparks, sparkle, the figure shadow and the
closing-zone warning. Everything is drawn at 4x and reduced, then make.py gives it the Amiga look.
"""
import math

import numpy as np
from PIL import Image

UP = 4
LIGHT = np.array([-0.55, -0.6, 0.58])  # from the top left, as in Blender (screen x right, y down)
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def value_noise(w, h, cell, seed, octaves=3):
    """Smooth noise in [0, 1] of shape (h, w), feature size about `cell` pixels."""
    rnd = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        c = max(1.0, cell / (2 ** o))
        gw, gh = int(w / c) + 3, int(h / c) + 3
        grid = rnd.random((gh, gw)).astype(np.float32)
        img = Image.fromarray(grid, "F").resize((int(gw * c), int(gh * c)), Image.BICUBIC)
        a = np.asarray(img)[:h, :w]
        out += amp * a
        total += amp
        amp *= 0.5
    return np.clip(out / total, 0, 1)


def reduce(rgba, size):
    """Premultiplied area reduction of a float RGBA array (0..1) to an RGBA image."""
    a = rgba[..., 3:4]
    pm = np.concatenate([rgba[..., :3] * a, a], -1)
    chans = [np.asarray(Image.fromarray(pm[..., i].astype(np.float32), "F").resize(size, Image.BOX)) for i in range(4)]
    out = np.stack(chans, -1)
    alpha = out[..., 3:4]
    rgb = np.where(alpha > 1e-4, out[..., :3] / np.maximum(alpha, 1e-4), 0)
    res = np.concatenate([rgb, alpha], -1)
    return Image.fromarray((np.clip(res, 0, 1) * 255).astype(np.uint8), "RGBA")


def ramp(values, stops):
    """Map values in [0, 1] through [(position, '#rrggbb'), ...]."""
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.stack([hexrgb(c) for _, c in stops]) / 255.0
    out = np.empty(values.shape + (3,), np.float32)
    for k in range(3):
        out[..., k] = np.interp(values, pos, cols[:, k])
    return out


# ---------------------------------------------------------------------------
#   puffs: lit balls of smoke (a height field of spheres, shaded like the 3D art)
# ---------------------------------------------------------------------------

SMOKE = [(0.0, "#2a2618"), (0.35, "#5a5434"), (0.65, "#9a9050"), (0.9, "#d8cc78"), (1.0, "#f0e8a8")]
GREY_SMOKE = [(0.0, "#1c1a1a"), (0.4, "#3a3634"), (0.75, "#6a625a"), (1.0, "#a09888")]


def puffs(w, h, blobs, stops=SMOKE, seed=0, rough=0.25, glow=None):
    """blobs: (cx, cy, r) in output pixels. Returns float RGBA at UP times the size."""
    W, H = w * UP, h * UP
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) + 0.5
    height = np.full((H, W), -1.0, np.float32)
    nz = value_noise(W, H, 6 * UP / 2, seed, 3)
    for cx, cy, r in blobs:
        cx, cy, r = cx * UP, cy * UP, r * UP
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        hgt = np.sqrt(np.maximum(r * r - d2, 0)) / UP
        hgt = np.where(d2 < r * r, hgt + rough * r / UP * (nz - 0.5) * 2, -1)
        height = np.maximum(height, hgt)
    mask = height > 0
    gy, gx = np.gradient(np.where(mask, height, 0))
    n = np.stack([-gx * UP, -gy * UP, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    lit = np.clip((n * LIGHT).sum(-1), 0, 1)
    shade = np.clip(0.15 + 0.85 * lit, 0, 1)
    rgb = ramp(shade, stops)
    if glow is not None:
        rgb = np.clip(rgb + glow[..., None] * hexrgb("#ff8020") / 255.0, 0, 1)
    return np.dstack([rgb, mask.astype(np.float32)])


def smoke_blobs(cx, cy, spread, count, rmin, rmax, seed, rise=0.0):
    rnd = np.random.default_rng(seed)
    out = []
    for i in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        d = spread * math.sqrt(rnd.uniform(0, 1))
        out.append((cx + d * math.cos(a), cy + d * math.sin(a) * 0.8 - rise * rnd.uniform(0.5, 1.0),
                    rnd.uniform(rmin, rmax)))
    return out


# ---------------------------------------------------------------------------
#   fire
# ---------------------------------------------------------------------------

FIRE = [(0.0, "#300800"), (0.25, "#8a1a04"), (0.45, "#d8400a"), (0.65, "#ff8a1a"), (0.82, "#ffd040"),
        (0.94, "#fff4b0"), (1.0, "#ffffff")]
SULPHUR_FIRE = [(0.0, "#203008"), (0.25, "#4a7010"), (0.45, "#9ac020"), (0.65, "#e0e040"), (0.82, "#fff070"),
                (0.94, "#ffffc0"), (1.0, "#ffffff")]


def flames(w, h, f, n, seed, stops):
    """One burning cell: a white flash, then turbulent flame licking upward, then smoke."""
    W, H = w * UP, h * UP
    t = f / (n - 1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) + 0.5
    cx, cy = W / 2, H / 2
    nz = value_noise(W, H + 40 * UP, 5 * UP, seed + 7, 4)
    shift = int(f * 3 * UP)
    nz = nz[shift:shift + H] if shift + H <= nz.shape[0] else nz[-H:]
    dx, dy = (xx - cx) / (W / 2), (yy - cy) / (H / 2)
    # a rounded square, so neighbouring cells merge into one sheet of fire
    r = (np.abs(dx) ** 3 + np.abs(dy) ** 3) ** (1 / 3)
    size = (1.05, 1.0, 0.98, 0.92, 0.80, 0.62, 0.0, 0.0)[min(f, 7)] if n == 8 else 1.0 - t
    heat = (1.0, 0.9, 0.82, 0.72, 0.55, 0.38, 0.0, 0.0)[min(f, 7)] if n == 8 else 1.0 - t
    upward = np.clip(-dy, -1, 1) * 0.12
    field = (1.0 - r / max(size, 1e-3)) + (nz - 0.5) * 0.9 + upward
    inten = np.clip(field * 1.25, 0, 1) * heat + (0.3 if f == 0 else 0.0) * (1 - r)
    inten = np.clip(inten, 0, 1)
    mask = field > 0.0
    rgb = ramp(inten, stops)
    fire = np.dstack([rgb, mask.astype(np.float32)])
    if f >= 4:
        k = f - 4
        blobs = smoke_blobs(w / 2, h / 2 + 1, (4, 6, 8, 9)[k], (5, 7, 8, 6)[k], (2.5, 3.0, 2.8, 2.0)[k],
                            (4.5, 5.0, 4.4, 3.2)[k], seed + f, rise=(1, 2, 3, 5)[k])
        sm = puffs(w, h, blobs, GREY_SMOKE if stops is FIRE else SMOKE, seed=seed + f)
        if k >= 2:
            holes = value_noise(W, H, 3 * UP, seed + 30 + f, 2) < (0.3 if k == 2 else 0.5)
            sm[..., 3] *= ~holes
        under = sm[..., 3] > 0
        fire = np.where(mask[..., None] & (inten[..., None] > 0.25), fire, np.where(under[..., None], sm, fire))
        if k >= 2:
            fire = sm
    return fire


def fire(f, seed=1):
    return reduce(flames(24, 24, f, 8, seed, FIRE), (24, 24))


def fire_sheep(f, seed=11):
    """A sulphur sheep going off: a greenish-yellow sulphur blast with tufts of wool flying out."""
    img = flames(24, 24, f, 8, seed, SULPHUR_FIRE)
    if 1 <= f <= 6:
        rnd = np.random.default_rng(5)
        blobs = []
        for i in range(7):
            a = rnd.uniform(0, 2 * math.pi) + i
            d = 3 + f * 1.6 * rnd.uniform(0.8, 1.2)
            blobs.append((12 + d * math.cos(a), 12 + d * math.sin(a) - f * 0.3, max(0.8, 1.9 - 0.15 * f)))
        wool = puffs(24, 24, blobs, [(0.0, "#8a8478"), (0.5, "#d0ccc0"), (1.0, "#ffffff")], seed=3, rough=0.4)
        on = wool[..., 3] > 0
        img = np.where(on[..., None], wool, img)
    return reduce(img, (24, 24))


# ---------------------------------------------------------------------------
#   sparks, sparkle, shadow, warning
# ---------------------------------------------------------------------------

def _star(w, h, f, rays, length, core, colours, rot=0.0, thin=0.6):
    W, H = w * UP, h * UP
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) + 0.5
    cx, cy = W / 2, H / 2
    dx, dy = (xx - cx) / UP, (yy - cy) / UP
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx) - rot
    ray = np.abs(np.sin(ang * rays / 2))
    width = thin / np.maximum(r, 0.3)
    star = (ray < width) & (r < length)
    v = np.clip(1.0 - r / max(length, 0.1), 0, 1)
    v = np.where(r < core, 1.0, v * 0.9)
    mask = star | (r < core)
    rgb = ramp(v, colours)
    return np.dstack([rgb, mask.astype(np.float32)])


SPARK = [(0.0, "#c03008"), (0.4, "#ff9020"), (0.75, "#ffe060"), (1.0, "#ffffff")]
TWINKLE = [(0.0, "#2080c0"), (0.45, "#80e0ff"), (0.8, "#e0ffff"), (1.0, "#ffffff")]


def spark(f):
    lengths = (3.4, 4.0, 2.8, 3.8)
    img = _star(8, 8, f, (6, 4, 6, 4)[f], lengths[f], (1.1, 1.4, 1.0, 1.3)[f], SPARK, rot=f * 0.7, thin=0.7)
    return reduce(img, (8, 8))


def sparkle(f):
    lengths = (1.6, 3.4, 4.5, 3.0)
    img = _star(9, 9, f, 4, lengths[f], (0.8, 0.9, 1.2, 0.9)[f], TWINKLE, rot=(0, 0, math.pi / 4, 0)[f] if f != 2 else 0,
                thin=0.55)
    if f == 2:
        img2 = _star(9, 9, f, 4, 2.6, 0.0, TWINKLE, rot=math.pi / 4, thin=0.5)
        img = np.where(img2[..., 3:4] > img[..., 3:4], img2, img)
    return reduce(img, (9, 9))


BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 + 1 / 32


def shadow():
    """A dithered dark ellipse: the console draws it opaque, the pattern lets the floor through."""
    w, h = 18, 8
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    density = np.clip(1.15 - r, 0, 1) * 0.95
    on = (BAYER4[np.arange(h)[:, None] % 4, np.arange(w)[None, :] % 4] < density) & (r < 1)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = (8, 6, 10)
    out[..., 3] = on * 255
    return Image.fromarray(out, "RGBA")


def zone_warn():
    """A cell about to close: a glowing hot rim with hatching inside (the game blinks it)."""
    w = 20
    yy, xx = np.mgrid[0:w, 0:w]
    edge = np.minimum(np.minimum(xx, yy), np.minimum(w - 1 - xx, w - 1 - yy))
    out = np.zeros((w, w, 4), np.uint8)
    hot, mid, low = hexrgb("#fff0a0"), hexrgb("#ffa020"), hexrgb("#c03010")
    rim0 = edge == 0
    rim1 = edge == 1
    hatch = (edge >= 2) & (((xx + yy) % 6) < 2) & (edge <= 4)
    corner = ((xx < 6) | (xx > 13)) & ((yy < 6) | (yy > 13)) & (edge <= 2)
    for m, c in ((hatch, low), (rim1, mid), (rim0, mid), (corner & (edge <= 1), hot)):
        out[m, :3] = c
        out[m, 3] = 255
    return Image.fromarray(out, "RGBA")


# ---------------------------------------------------------------------------
#   dying in sulphur smoke (frames over a rendered figure)
# ---------------------------------------------------------------------------

def die_frame(figure, f, seed=3):
    """figure: the rendered pose (RGBA image at the sprite size) or None for frames 4 and 5."""
    w, h = 24, 32
    cx, foot = w / 2, h - 1 - 4
    plans = {
        0: (0.0, []),
        1: (0.15, smoke_blobs(cx, foot - 6, 4, 4, 1.6, 2.6, seed + 1)),
        2: (0.45, smoke_blobs(cx, foot - 5, 6, 7, 2.2, 3.6, seed + 2, rise=1)),
        3: (0.8, smoke_blobs(cx, foot - 6, 7, 9, 2.8, 4.4, seed + 3, rise=2)),
        4: (1.0, smoke_blobs(cx, foot - 9, 7, 9, 2.8, 4.6, seed + 4, rise=4)),
        5: (1.0, smoke_blobs(cx, foot - 13, 7, 7, 1.8, 3.4, seed + 5, rise=6)),
    }
    gone, blobs = plans[f]
    out = np.zeros((h, w, 4), np.float32)
    if figure is not None:
        fig = np.asarray(figure.convert("RGBA")).astype(np.float32) / 255
        tint = (0.45, 0.3, 0.2, 0.1)[f]
        fig[..., :3] = fig[..., :3] * (1 - tint) + tint * hexrgb("#fff080") / 255
        dissolve = value_noise(w, h, 2.5, seed + f, 2) < gone
        fig[..., 3] *= ~dissolve
        out = fig
    if blobs:
        sm = reduce(puffs(w, h, blobs, SMOKE, seed=seed + f), (w, h))
        sm = np.asarray(sm).astype(np.float32) / 255
        if f == 5:
            holes = value_noise(w, h, 2.0, seed + 9, 2) < 0.35
            sm[..., 3] *= ~holes
        on = sm[..., 3] > 0.5
        out = np.where(on[..., None], sm, out)
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA")
