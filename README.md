# Sulphur — the sulphur legend

An arena game for the [Vircon32](https://www.vircon32.com/) fantasy console, a fork of
[BlasTIC](https://github.com/Lagsters/blastic) for TIC-80.

- **Battle**: four players drop sulphur bombs, break crates and fight to be the last one standing
  while the arena closes in. Players without a gamepad are played by bots.
- **Story**: the Polish legend of Dratewka the shoemaker. Thirty stages across Wroclaw, Mount
  Sleza and Krakow, three bosses, and the dragon of Wawel, whom only a sheep stuffed with sulphur
  can hurt: catch one, then let it go at the dragon.

Graphics are modelled and rendered in Blender and brought down to the Amiga's 12-bit colour; the
music is synthesized and played by a tracker on the console's 16 channels. The songs live in one
FastTracker 2 module, `assets/music/songs/sulphur.xm` (ten subsongs, stereo samples in OpenMPT's
XM extension), which `tools/audio/make.py` converts for the console. English and Polish.

## Controls

| Gamepad | |
|---|---|
| D-pad | walk |
| A | lay a sulphur bomb / confirm |
| B | let a sheep go at the dragon / back |
| Start | pause / skip a scene |

## Build

Python 3 with NumPy and Pillow, and g++ (Windows: WinLibs) for the test runner.

```
python tools/build.py          # build/sulphur.v32
python tools/check.py          # build, tests, simulation and performance
```

`tools/toolchain.py` downloads the pinned Vircon32 dev tools and the console source, and builds
the headless runner used by the tests.

## Licence

MIT, see `LICENSE`. Third-party software and fonts: `THIRD_PARTY.md`.
