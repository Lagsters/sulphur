"""2D finishing of the story art in plain Python: sprite outlines, the copper sky of the title,
the logo glow, parchment maps and the map nodes."""
import numpy as np
from PIL import Image, ImageDraw

import assetlib


def _arr(im):
    return np.asarray(im.convert("RGBA")).astype(np.float32)


def _img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def outline(im, darkness=0.22):
    """A 1 px selective outline: each empty pixel touching the sprite takes a darkened copy of
    its neighbours' colour, so the edge reads on any floor without a flat black line."""
    a = _arr(im)
    solid = a[..., 3] > 0
    acc = np.zeros(a.shape[:2] + (3,), np.float32)
    cnt = np.zeros(a.shape[:2], np.float32)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        s = np.roll(solid, (dy, dx), (0, 1))
        c = np.roll(a[..., :3], (dy, dx), (0, 1))
        if dy == 1:
            s[0, :] = False
        if dy == -1:
            s[-1, :] = False
        if dx == 1:
            s[:, 0] = False
        if dx == -1:
            s[:, -1] = False
        acc += c * s[..., None]
        cnt += s
    edge = (~solid) & (cnt > 0)
    out = a.copy()
    out[edge, :3] = acc[edge] / cnt[edge, None] * darkness + np.array([4, 4, 10])
    out[edge, 3] = 255
    return _img(out)


def palette_of(im, colours=32):
    """The `colours` most useful colours of an image, snapped to the Amiga's 12-bit steps."""
    q = im.convert("RGB").quantize(colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette()[:colours * 3], np.float32).reshape(-1, 3)
    pal = np.round(pal / 17) * 17
    return [tuple(int(v) for v in c) for c in np.unique(pal, axis=0)]


def backdrop(im, colours=32, dither=1.0):
    """A finished full-screen picture: opaque, `colours` colours of 12 bits, ordered dither."""
    im = im.convert("RGBA")
    return assetlib.amiga(im, palette=palette_of(im, colours), dither=dither)


# ---------------------------------------------------------------------------
#   helpers for painted backdrops
# ---------------------------------------------------------------------------

def _rng(seed):
    return np.random.default_rng(seed)


def soft_noise(w, h, cell, seed, stretch=1.0):
    """Smooth noise in 0..1: random values on a coarse grid, enlarged bicubically."""
    gw, gh = max(2, int(w / (cell * stretch))), max(2, int(h / cell))
    small = Image.fromarray((_rng(seed).random((gh, gw)) * 255).astype(np.uint8), "L")
    return np.asarray(small.resize((w, h), Image.BICUBIC)).astype(np.float32) / 255


def fractal(w, h, cell, seed, octaves=4, stretch=1.0):
    total, amp, norm = np.zeros((h, w), np.float32), 1.0, 0.0
    for k in range(octaves):
        total += soft_noise(w, h, max(2, cell / 2 ** k), seed + k, stretch) * amp
        norm += amp
        amp *= 0.5
    return total / norm


def gradient_rows(h, stops):
    """Per-row colours interpolated through (position 0..1, (r, g, b)) stops."""
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.array([c for _, c in stops], np.float32)
    y = np.linspace(0, 1, h)
    return np.stack([np.interp(y, pos, cols[:, k]) for k in range(3)], -1)


# ---------------------------------------------------------------------------
#   the title screen
# ---------------------------------------------------------------------------

SKY = [(0.0, (14, 6, 32)), (0.18, (34, 10, 58)), (0.36, (78, 18, 72)), (0.5, (140, 34, 70)),
       (0.6, (200, 70, 52)), (0.67, (240, 130, 60)), (0.72, (255, 190, 100))]


def title(scene, dragon, size):
    """Scene render (transparent sky) + copper sky, clouds, stars, the dragon silhouette."""
    W, H = scene.size
    sky = np.zeros((H, W, 3), np.float32)
    rows = gradient_rows(H, SKY)
    # the copper list changes colour once per Amiga scanline: snap rows to 12-bit steps
    step = H // size[1]
    rows = np.round(rows / 17) * 17
    rows = np.repeat(rows[::step], step, axis=0)[:H]
    sky[:] = rows[:, None, :]
    # long dusk clouds: dark violet bodies with orange undersides
    yy = np.arange(H)[:, None] / H
    clouds = fractal(W, H, 90, 11, 5, stretch=6.0)
    band = np.exp(-((yy - 0.42) / 0.16) ** 2) + 0.6 * np.exp(-((yy - 0.16) / 0.07) ** 2)
    c = np.clip((clouds - 0.52) * 4.0, 0, 1) * band
    under = np.clip((clouds - np.roll(clouds, 6, axis=0)) * 12, 0, 1)
    body = np.array([40, 14, 48], np.float32)
    rim = np.array([255, 120, 60], np.float32)
    tone = body + (rim - body) * (under * np.clip(yy * 1.6, 0, 1))[..., None]
    sky = sky * (1 - c[..., None] * 0.85) + tone * (c[..., None] * 0.85)
    # stars in the high sky
    rng = _rng(4)
    for _ in range(140):
        x, y = rng.integers(0, W), int(rng.random() ** 2 * H * 0.3)
        b = rng.uniform(120, 255) * (1 - y / (H * 0.32))
        sky[y:y + 2, x:x + 2] = np.maximum(sky[y:y + 2, x:x + 2], b)
    canvas = Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # the setting sun's glow, centred on the brightest spot of the render
    a = _arr(scene)
    lum = a[..., :3].sum(-1) * (a[..., 3] > 0)
    lum[int(H * 0.62):] = 0
    ys, xs = np.nonzero(lum > lum.max() * 0.95)
    if len(xs):
        cx, cy = xs.mean(), ys.mean()
        d = np.hypot((np.arange(W)[None, :] - cx) / 1.6, np.arange(H)[:, None] - cy)
        glow = np.exp(-(d / (H * 0.18)) ** 2)[..., None] * np.array([255, 150, 60]) * 0.55
        g = _arr(canvas)
        g[..., :3] += glow
        canvas = _img(g)
    canvas.alpha_composite(scene)
    # the dragon over the town on the left, dark against the bright horizon
    box = dragon.getbbox()
    d = dragon.crop(box)
    target = int(W * 0.15)
    d = d.resize((target, int(d.height * target / d.width)), Image.LANCZOS).rotate(24, Image.BICUBIC, expand=True)
    da = _arr(d)
    da[..., :3] = da[..., :3] * 0.7 + np.array([10, 4, 16]) * 0.3
    canvas.alpha_composite(_img(da), (int(W * 0.06), int(H * 0.27)))
    # deepen the river (and tame the sun's streak on it) and the corners
    g = _arr(canvas)
    vy = np.clip((yy - 0.62) / 0.38, 0, 1)
    water = (yy > 0.62)[..., None]
    g[..., :3] = np.where(water, g[..., :3] / (1 + g[..., :3] / 255 * 0.4) * np.array([0.95, 0.85, 1.05]), g[..., :3])
    g[..., :3] *= (1 - 0.45 * vy)[..., None]
    xx = np.arange(W)[None, :] / W
    vig = 1 - 0.35 * np.clip((np.hypot(xx - 0.5, (yy - 0.5) * 0.9) - 0.35) / 0.4, 0, 1)
    g[..., :3] *= vig[..., None]
    g[..., 3] = 255
    out = _img(g).resize(size, Image.LANCZOS)
    return backdrop(out, 32)


# ---------------------------------------------------------------------------
#   the logo: the gilded letters with a dark rim and a banded sulphur glow
# ---------------------------------------------------------------------------

def _blur(mask, radius):
    im = Image.fromarray(np.clip(mask * 255, 0, 255).astype(np.uint8), "L")
    from PIL import ImageFilter
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255


def logo(render, size):
    W, H = size
    margin = 9
    letters = render.crop(render.getbbox())
    k = min((W - 2 * margin) / letters.width, (H - 2 * margin) / letters.height)
    letters = letters.convert("RGBa").resize((int(letters.width * k), int(letters.height * k)),
                                             Image.LANCZOS).convert("RGBA")
    from PIL import ImageFilter
    rgb = letters.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.2, percent=70, threshold=1))
    letters = Image.merge("RGBA", (*rgb.split(), letters.getchannel("A")))
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(letters, ((W - letters.width) // 2, (H - letters.height) // 2))
    a = _arr(canvas)
    solid = a[..., 3] / 255
    # glow: concentric hard-edged bands, the way an Amiga artist would paint it
    glow = _blur(solid, 5.0)
    near = _blur(solid, 1.6)
    out = np.zeros_like(a)
    bands = [(0.03, (90, 40, 6)), (0.12, (170, 110, 10)), (0.3, (240, 205, 40))]
    for threshold, colour in bands:
        m = glow > threshold
        out[m, :3] = colour
        out[m, 3] = 255
    rim = near > 0.08
    out[rim, :3] = (34, 14, 4)
    out[rim, 3] = 255
    letters_mask = solid > 0.5
    out[letters_mask] = a[letters_mask]
    out[letters_mask, 3] = 255
    return assetlib.amiga(_img(out), dither=0.6)


# ---------------------------------------------------------------------------
#   the world maps on parchment, and the stage nodes drawn over them
# ---------------------------------------------------------------------------

PAPER = np.array([226, 200, 150], np.float32)
INK = np.array([62, 36, 18], np.float32)


def world_map(render, size, chapter):
    W, H = render.size
    a = _arr(render)[..., :3]
    yy = np.arange(H)[:, None] / H
    xx = np.arange(W)[None, :] / W
    # the centre band, where the path of stages goes, is softened and lightened
    from PIL import ImageFilter
    soft = np.asarray(render.convert("RGB").filter(ImageFilter.GaussianBlur(3))).astype(np.float32)
    calm = np.exp(-((yy - 0.5) / 0.13) ** 4)[..., None]
    a = a * (1 - 0.55 * calm) + (soft * 0.75 + PAPER * 0.25) * (0.55 * calm)
    # parchment: a painted map, toned towards paper, with fibres and stains
    lum = a.mean(-1, keepdims=True)
    toned = a * 0.72 + (PAPER * (lum / 255) * 0.9 + INK * (1 - lum / 255) * 0.1) * 0.28
    fibres = fractal(W, H, 3, 100 + chapter, 3, stretch=4.0)
    stains = fractal(W, H, 160, 200 + chapter, 4)
    toned *= (0.92 + 0.12 * fibres[..., None]) * (0.9 + 0.18 * stains[..., None])
    # burnt, uneven edges: a vignette with a ragged border
    edge = np.minimum(np.minimum(xx, 1 - xx) * W / H, np.minimum(yy, 1 - yy))
    rag = fractal(W, H, 25, 300 + chapter, 4)
    e = edge + (rag - 0.5) * 0.06
    vign = np.clip((e - 0.0) / 0.16, 0, 1) ** 0.8
    burnt = np.clip((e - 0.012) / 0.02, 0, 1)
    toned = toned * (0.45 + 0.55 * vign[..., None])
    toned = toned * burnt[..., None] + np.array([28, 14, 8]) * (1 - burnt[..., None])
    # a thin double ink frame
    out = Image.fromarray(np.clip(toned, 0, 255).astype(np.uint8), "RGB").resize(size, Image.LANCZOS)
    d = ImageDraw.Draw(out)
    w, h = size
    for inset, width in ((10, 2), (15, 1)):
        d.rectangle([inset, inset, w - 1 - inset, h - 1 - inset], outline=(70, 40, 20), width=width)
    return backdrop(out.convert("RGBA"), 32)


def map_nodes(size):
    """Three medallions: stage ahead (dark bronze), cleared (gilded), boss (red)."""
    S = 4
    w, h = size
    looks = [((120, 92, 60), (52, 36, 24), (180, 150, 110)),
             ((255, 210, 70), (150, 92, 14), (255, 250, 200)),
             ((225, 40, 25), (100, 8, 8), (255, 170, 140))]
    frames = []
    for face, dark, shine in looks:
        big = np.zeros((h * S, w * S, 4), np.float32)
        yy, xx = np.mgrid[0:h * S, 0:w * S].astype(np.float32)
        cx, cy = (w * S - 1) / 2, (h * S - 1) / 2
        r = np.hypot(xx - cx, yy - cy) / (w * S / 2)
        # light from the top left: a sphere-like shading on the disc
        nx, ny = (xx - cx) / (w * S / 2), (yy - cy) / (h * S / 2)
        light = np.clip(0.55 - 0.45 * nx - 0.55 * ny, 0, 1)
        col = np.array(dark) + (np.array(face) - np.array(dark)) * light[..., None]
        spec = np.exp(-(((nx + 0.35) ** 2 + (ny + 0.4) ** 2) / 0.04))
        col = col + (np.array(shine) - col) * spec[..., None]
        ring = (r > 0.68) & (r <= 0.84)
        col[ring] = np.array(dark) * 0.9 + np.array(face) * 0.1 * light[ring, None]
        big[..., :3] = col
        big[..., 3] = np.where(r <= 0.84, 255, 0)
        edge = (r > 0.84) & (r <= 1.0)
        big[edge, :3] = (20, 10, 6)
        big[edge, 3] = 255
        im = _img(big).convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")
        frames.append(assetlib.amiga(im, dither=0.4))
    return frames
