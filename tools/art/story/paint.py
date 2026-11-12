"""2D finishing of the story art in plain Python: sprite outlines, the copper sky of the title,
the logo glow, parchment maps and the map nodes."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

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
