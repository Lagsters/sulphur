"""Turns the runner's PPM frames into PNG, optionally as one contact sheet.

    python tools/frames.py <dir>                 every <dir>/f*.ppm -> .png next to it
    python tools/frames.py <dir> --sheet out.png [--cols 3] [--scale 0.5]
"""
import argparse
from pathlib import Path

from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--sheet")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--scale", type=float, default=0.5)
    a = ap.parse_args()
    frames = sorted(Path(a.dir).glob("f*.ppm"))
    images = []
    for f in frames:
        im = Image.open(f).convert("RGB")
        if not a.sheet:
            im.save(f.with_suffix(".png"))
        images.append(im)
    if a.sheet and images:
        w, h = int(images[0].width * a.scale), int(images[0].height * a.scale)
        rows = (len(images) + a.cols - 1) // a.cols
        sheet = Image.new("RGB", (w * a.cols, h * rows))
        for i, im in enumerate(images):
            sheet.paste(im.resize((w, h), Image.LANCZOS), ((i % a.cols) * w, (i // a.cols) * h))
        sheet.save(a.sheet)
    print(f"{len(images)} frames")


if __name__ == "__main__":
    main()
