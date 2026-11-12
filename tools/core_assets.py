"""The core group: a white square, the brush for every flat rectangle and fade."""
from PIL import Image

from assetlib import pack_group

if __name__ == "__main__":
    pack_group("core", [("white", [Image.new("RGBA", (16, 16), (255, 255, 255, 255))], (0, 0))])
