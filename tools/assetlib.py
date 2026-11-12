"""Shared asset helpers: the Amiga look, texture atlases with their C regions, sounds, text.

Every asset group (core, font, game, story, scenes, music, sfx) is written the same way:

    assets/<group>/tex<k>.png      texture atlases (each at most 1024x1024)
    assets/<group>/rom.txt         "texture <path>" / "sound <path>" lines in ROM order
    src/gen/<group>.h              ids and regions for C

tools/build.py joins the groups in a fixed order and writes src/gen/rom.h with the first texture
and sound id of each group (TEX_BASE_<GROUP>, SND_BASE_<GROUP>); the group headers count from
there, so groups never renumber each other.
"""
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
GROUPS = ("core", "font", "game", "story", "scenes", "music", "sfx")
TEXTURE_SIZE = 1024

# ---------------------------------------------------------------------------
#   the Amiga look: 12-bit colour (4 bits a channel, 4096 colours) with ordered dithering
# ---------------------------------------------------------------------------

_BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32)


def amiga(image, levels=16, dither=1.0, palette=None):
    """RGBA image -> the same with colours snapped to 12-bit steps (or to `palette`, a list of
    (r,g,b)), with a 4x4 Bayer dither of `dither` steps. Alpha is snapped to 0 or 255, because
    the console blends, and soft edges look like no Amiga game did."""
    a = np.asarray(image.convert("RGBA")).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3]
    h, w = alpha.shape
    threshold = (_BAYER4[np.arange(h)[:, None] % 4, np.arange(w)[None, :] % 4] + 0.5) / 16 - 0.5
    if palette is None:
        step = 255.0 / (levels - 1)
        q = np.floor(rgb / step + 0.5 + threshold[..., None] * dither)
        rgb = np.clip(q, 0, levels - 1) * step
    else:
        pal = np.asarray(palette, dtype=np.float32)
        jitter = rgb + threshold[..., None] * dither * 24.0
        d = ((jitter[..., None, :] - pal[None, None, :, :]) ** 2).sum(-1)
        rgb = pal[d.argmin(-1)]
    out = np.dstack([rgb, np.where(alpha >= 128, 255, 0)]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


# ---------------------------------------------------------------------------
#   texture atlases and regions
# ---------------------------------------------------------------------------

def _c_name(name):
    return "".join(ch if ch.isalnum() else "_" for ch in name).upper()


def _atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
    os.replace(tmp, path)


def pack_group(group, sprites, sounds=()):
    """Writes the textures, rom.txt and src/gen/<group>.h of one group.

    sprites: list of (name, frames, hotspot) with frames a list of RGBA images of one size and
    hotspot (x, y) in a frame: the point draw_region_at() puts at the drawing point.
    sounds: list of (name, wav path relative to the repo root).

    In C, for a sprite NAME of group GROUP:
        GROUP_NAME             its index in group_tex[] / group_reg[]
        GROUP_NAME_N, _W, _H   frame count and frame size
        group_tex[GROUP_NAME]  texture id; group_reg[GROUP_NAME] + f is the region of frame f
    and SND_GROUP_NAME for each sound; define_group_regions() defines every region once.
    """
    assert group in GROUPS, group
    gdir = ROOT / "assets" / group
    gdir.mkdir(parents=True, exist_ok=True)
    for old in gdir.glob("tex*.png"):
        old.unlink()
    # shelf packing, tallest first; all frames of a sprite go into one texture
    order = sorted(range(len(sprites)), key=lambda i: -sprites[i][1][0].height)
    textures, placed = [], {}
    shelf = None  # (x, y, height) of the open shelf in the last texture

    def fit(state, w, h, count):
        """Spots for `count` frames from shelf state, or None when the texture is full."""
        x, y, sh = state
        spots = []
        for _ in range(count):
            if x + w > TEXTURE_SIZE:
                x, y, sh = 0, y + sh, 0
            if y + h > TEXTURE_SIZE:
                return None, state
            spots.append((x, y))
            x, sh = x + w + 1, max(sh, h + 1)
        return spots, (x, y, sh)

    for i in order:
        name, frames, hot = sprites[i]
        w, h = frames[0].size
        assert w <= TEXTURE_SIZE and h <= TEXTURE_SIZE, name
        assert all(f.size == (w, h) for f in frames), f"{name}: frames differ in size"
        spots = None
        if textures:
            spots, after = fit(shelf, w, h, len(frames))
        if spots is None:
            textures.append(Image.new("RGBA", (TEXTURE_SIZE, TEXTURE_SIZE), (0, 0, 0, 0)))
            spots, after = fit((0, 0, 0), w, h, len(frames))
            if spots is None:
                raise ValueError(f"{name}: its frames do not fit one texture; split the sprite")
        shelf = after
        t = len(textures) - 1
        for f, (x, y) in zip(frames, spots):
            textures[t].paste(f, (x, y))
        placed[i] = [(t, x, y) for (x, y) in spots]
    # crop each texture to what is used: the ROM stores textures at their own size
    paths = []
    for k, tex in enumerate(textures):
        box = tex.getbbox() or (0, 0, 1, 1)
        tex = tex.crop((0, 0, box[2], box[3]))
        path = gdir / f"tex{k}.png"
        tex.save(path)
        paths.append(path)
    up = _c_name(group)
    lines = [f"// generated by the asset tools for the {group} group: do not edit",
             f"#ifndef GEN_{up}_H", f"#define GEN_{up}_H", '#include "rom.h"', ""]
    for k in range(len(textures)):
        lines.append(f"#define TEX_{up}_{k} ( TEX_BASE_{up} + {k} )")
    lines.append(f"#define {up}_SPRITES {len(sprites)}")
    region_base = [0] * len(textures)
    regions = {}
    for i, (name, frames, hot) in enumerate(sprites):
        t = placed[i][0][0]
        regions[i] = (t, region_base[t])
        region_base[t] += len(frames)
        cn = _c_name(name)
        w, h = frames[0].size
        lines.append(f"#define {up}_{cn} {i}")
        lines.append(f"#define {up}_{cn}_N {len(frames)}")
        lines.append(f"#define {up}_{cn}_W {w}")
        lines.append(f"#define {up}_{cn}_H {h}")
    for i, (name, path) in enumerate(sounds):
        lines.append(f"#define SND_{up}_{_c_name(name)} ( SND_BASE_{up} + {i} )")
    lines.append(f"#define {up}_SOUNDS {len(sounds)}")
    lines += ["", f"int[ {max(1, len(sprites))} ] {group}_tex;",
              f"int[ {max(1, len(sprites))} ] {group}_reg;", "",
              f"void define_{group}_regions()", "{"]
    for i, (name, frames, hot) in enumerate(sprites):
        t, r0 = regions[i]
        w, h = frames[0].size
        lines.append(f"    {group}_tex[ {i} ] = TEX_{up}_{t}; {group}_reg[ {i} ] = {r0};")
        lines.append(f"    select_texture( TEX_{up}_{t} );")
        for f, (tt, x, y) in enumerate(placed[i]):
            lines.append(f"    select_region( {r0 + f} ); define_region( {x}, {y}, {x + w - 1}, {y + h - 1}, {x + hot[0]}, {y + hot[1]} );")
    lines += ["}", "", "#endif", ""]
    _atomic_write(ROOT / "src/gen" / f"{group}.h", "\n".join(lines))
    rom = [f"texture {p.relative_to(ROOT).as_posix()}" for p in paths]
    rom += [f"sound {Path(p).as_posix()}" for (_, p) in sounds]
    _atomic_write(gdir / "rom.txt", "\n".join(rom) + "\n")
    return paths


# ---------------------------------------------------------------------------
#   text: strings for C as arrays of character codes; Polish letters get codes 128..145,
#   the font group draws glyphs for 32..126 and these
# ---------------------------------------------------------------------------

POLISH = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"


def char_code(ch):
    if ch in POLISH:
        return 128 + POLISH.index(ch)
    code = ord(ch)
    if 32 <= code <= 126:
        return code
    raise ValueError(f"no glyph for {ch!r}")


def c_string(text):
    """A C initializer for an int array holding text, zero-terminated."""
    return "{ " + ", ".join(str(char_code(ch)) for ch in text) + (", 0 }" if text else "0 }")
