"""Blender entry point for the story art: renders one subject's frames as large PNGs.

    blender -b --factory-startup -P tools/art/story/render.py -- <subject> <out_dir> <scale>

subject: bosses, title, maps, logo. tools/art/story/make.py runs this and post-processes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blib  # noqa: E402


def main():
    subject, out, scale = blib.script_args()[:3]
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    scale = int(scale)
    if subject == "bosses":
        import bosses
        bosses.render_all(out, scale)
    elif subject == "title":
        import scenery
        scenery.render_title(out, scale)
    elif subject == "maps":
        import scenery
        scenery.render_maps(out, scale)
    elif subject == "logo":
        import logo
        logo.render_logo(out, scale)
    else:
        raise SystemExit(f"unknown subject {subject}")


main()
