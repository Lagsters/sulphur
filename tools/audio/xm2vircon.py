"""Converts the songs module (assets/music/songs/sulphur.xm) for the console: its samples become
the music group's WAVs (assets/music/*.wav, rom.txt) and its patterns become per-voice command
lists for the sequencer in src/sound.h (appended to src/gen/music.h).

    python tools/audio/xm2vircon.py [module.xm]

The module holds all ten songs one after another in its order list, in SONG_* order: a song runs
from its first order to a position jump (Bxx) or pattern break (Dxx) back into itself, whose
target is the song's loop point; the next song starts at the order after the last one used.
At a song's first row, F01-F1F sets its speed (ticks per row), Fxx (32 and above) must be F96
(150 BPM: one tick per console frame) and Gxx sets the song's volume.

What the console plays (channels 1-12 are the voices; channels 13 and up only steer the song):
  notes, instruments (keymap to samples, relative note and finetune), key-off (==)
  volume column: set volume (0x10-0x50)
  instrument volume envelope with a sustain point (no envelope loop), fadeout
  effects: 1xx/2xx portamento up/down, 3xx tone portamento, 4xy vibrato (sine), Axy volume
  slide, Cxx set volume, ECx note cut, Bxx position jump, Dxx pattern break, Fxx speed/tempo,
  Gxx global volume (at the song's start); effect memory (00 params) for 1-4 and A
Anything else is reported and ignored: panning, arpeggio, volume-column effects, envelope loops,
auto-vibrato, E-subcommands other than ECx.
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import dsp  # noqa: E402
import xmfile  # noqa: E402
from assetlib import ROOT, _atomic_write, pack_group  # noqa: E402

SONG = ROOT / "assets/music/songs/sulphur.xm"
VOICES = 12
VOL_SCALE = "0.0078125"            # volume 64 -> channel gain 0.5, before the song's volume

T_NOTE, T_OFF, T_VOL, T_FX = 0, 1, 2, 3
FX_NONE, FX_VSLIDE, FX_VIBRATO, FX_TONE, FX_UP, FX_DOWN, FX_CUT = range(7)


def f32s(v):
    return f"{float(np.float32(v)):.9g}"


def sample_speed(s):
    """Channel speed of a sample at MIDI 60 (XM C-4): 8363 Hz shifted by its relative note and
    finetune, against the console's 44100 Hz."""
    return 8363.0 * 2 ** ((s.relative_note + s.finetune / 128) / 12) / 44100.0


def envelope_table(ins):
    """The volume envelope one value a tick (0..1), and the tick index it holds at until
    key-off. No envelope: full volume, cut at key-off."""
    pts = ins.envelope
    if not pts:
        return [1.0, 0.0], 0
    table = []
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        for t in range(t0, t1):
            table.append((v0 + (v1 - v0) * (t - t0) / (t1 - t0)) / 64.0)
    table.append(pts[-1][1] / 64.0)
    sus = pts[ins.sustain][0] if 0 <= ins.sustain < len(pts) else -1
    return table, sus


def split_songs(m):
    """[(first order, [(order, row range)...] played in sequence, loop index into it)]"""
    songs = []
    start = 0
    while start < len(m.orders):
        seq, seen = [], {}
        order, row = start, 0
        loop_at = None
        while True:
            pat = m.patterns[m.orders[order]]
            key = (order, row)
            if key in seen:
                loop_at = seen[key]
                break
            seen[key] = len(seq)
            jump = None
            r = row
            while r < len(pat):
                for cell in pat[r]:
                    fx, param = cell[3], cell[4]
                    if fx == 0x0B:
                        jump = (param, 0)
                    elif fx == 0x0D:
                        jump = (order + 1, (param >> 4) * 10 + (param & 15))
                if jump:
                    break
                r += 1
            seq.append((order, row, min(r + 1, len(pat))))
            if jump:
                order, row = jump
            else:
                order, row = order + 1, 0
            if order >= len(m.orders):
                break
        songs.append((start, seq, loop_at))
        start = max(o for o, _, _ in seq) + 1
    return songs


class Converter:
    def __init__(self, m):
        self.m = m
        self.warnings = Counter()
        self.samples = []                 # (instrument index, sample)
        self.first_sample = []
        for i, ins in enumerate(m.instruments):
            self.first_sample.append(len(self.samples))
            for s in ins.samples:
                self.samples.append((i, s))

    def song(self, start, seq, loop_at):
        m = self.m
        speed, gain = m.speed, 64
        commands = [[] for _ in range(VOICES)]
        state = [dict(ins=0, vol=64, fx=FX_NONE, vib=(0, 0), porta=0, slide=0, tone=0, target=0)
                 for _ in range(VOICES)]
        frame = 0
        loop_frame = 0
        first_row = True
        for k, (order, r0, r1) in enumerate(seq):
            if k == loop_at:
                loop_frame = frame
            pat = m.patterns[m.orders[order]]
            for r in range(r0, r1):
                row = pat[r]
                for ch, cell in enumerate(row):
                    fx, param = cell[3], cell[4]
                    if fx == 0x0F and param:
                        if param < 32:
                            speed = param
                        elif param != 150:
                            self.warnings["tempo other than 150 BPM (F96)"] += 1
                    elif fx == 0x10 and first_row:
                        gain = min(64, param)
                    if ch >= VOICES and (cell[0] or cell[1]):
                        self.warnings["notes on channels past 12"] += 1
                for v in range(min(VOICES, len(row))):
                    self.cell(commands[v], state[v], row[v], frame)
                first_row = False
                frame += speed
        loop_index = loop_at if loop_at is not None else 0
        if loop_at is None:
            loop_frame = 0
        return dict(commands=commands, length=frame, loop=loop_frame, gain=gain / 64.0, speed=speed)

    def cell(self, out, st, cell, frame):
        note, ins, vol, fx, param = cell
        if ins:
            st["ins"] = ins
        tone = fx == 0x03
        if 1 <= note <= 96 and not tone:
            if ins == 0 and st["ins"] == 0:
                self.warnings["note without an instrument"] += 1
                return
            xi = self.m.instruments[st["ins"] - 1]
            if not xi.samples:
                return
            smp_local = xi.keymap[note - 1]
            s = xi.samples[smp_local]
            if ins:
                st["vol"] = s.volume
            if 0x10 <= vol <= 0x50:
                st["vol"] = vol - 0x10
            smp = self.first_sample[st["ins"] - 1] + smp_local
            out.append((frame, T_NOTE, smp | ((note + 11) << 8) | (st["vol"] << 15) | ((st["ins"] - 1) << 22)))
            st["target"] = note + 11
        else:
            if note == xmfile.NOTE_OFF:
                out.append((frame, T_OFF, 0))
            if tone and 1 <= note <= 96:
                st["target"] = note + 11
            if 0x10 <= vol <= 0x50:
                st["vol"] = vol - 0x10
                out.append((frame, T_VOL, st["vol"]))
        if vol and not 0x10 <= vol <= 0x50:
            self.warnings["volume column effects"] += 1
        # the row's effect
        kind, p1, p2 = FX_NONE, 0, 0
        if fx == 0x0C:
            st["vol"] = min(64, param)
            out.append((frame, T_VOL, st["vol"]))
        elif fx == 0x0A:
            if param:
                st["slide"] = param
            kind, p1, p2 = FX_VSLIDE, st["slide"] >> 4, st["slide"] & 15
        elif fx == 0x04:
            sp, dp = param >> 4, param & 15
            vs, vd = st["vib"]
            st["vib"] = (sp or vs, dp or vd)
            kind, p1, p2 = FX_VIBRATO, st["vib"][0], st["vib"][1]
        elif fx == 0x03:
            if param:
                st["tone"] = param
            kind, p1, p2 = FX_TONE, st["tone"], st["target"]
        elif fx in (0x01, 0x02):
            if param:
                st["porta"] = param
            kind, p1 = (FX_UP if fx == 1 else FX_DOWN), st["porta"]
        elif fx == 0x0E and param >> 4 == 0x0C:
            kind, p1 = FX_CUT, param & 15
        elif fx in (0x0B, 0x0D, 0x0F, 0x10) or (fx == 0 and param == 0):
            pass
        else:
            self.warnings[f"effect {fx:X}{param:02X}"] += 1
        if kind != FX_NONE or st["fx"] != FX_NONE:
            out.append((frame, T_FX, kind | (p1 << 4) | (p2 << 12)))
        st["fx"] = kind


def convert(path=SONG, write=True):
    m = xmfile.read(path)
    conv = Converter(m)
    songs = [conv.song(*s) for s in split_songs(m)]

    sounds = []
    for k, (i, s) in enumerate(conv.samples):
        name = s.name or f"ins{i + 1}_{k}"
        rel = Path("assets/music") / f"{name}.wav"
        if write:
            pcm = s.pcm if s.pcm.ndim == 2 else np.stack([s.pcm, s.pcm], axis=1)
            dsp.write_wav(ROOT / rel, pcm.astype(np.float64) / 32767)
        sounds.append((name, rel.as_posix()))

    env_values, env_first, env_len, env_sus = [], [], [], []
    for ins in m.instruments:
        table, sus = envelope_table(ins)
        env_first.append(len(env_values))
        env_len.append(len(table))
        env_sus.append(sus)
        env_values += table

    t = {
        "sample_speed": [np.float32(float(f32s(sample_speed(s)))) for _, s in conv.samples],
        "loop_start": [s.loop_start if s.loop_length else 0 for _, s in conv.samples],
        "loop_end": [s.loop_start + s.loop_length - 1 if s.loop_length else 0 for _, s in conv.samples],
        "semi": [np.float32(float(f32s(2 ** ((i - 60) / 12)))) for i in range(128)],
        "env": [np.float32(float(f32s(v))) for v in env_values],
        "env_first": env_first, "env_len": env_len, "env_sus": env_sus,
        "fadeout": [np.float32(float(f32s(ins.fadeout / 65536.0))) for ins in m.instruments],
        "sine": [np.float32(float(f32s(v))) for v in SINE],
        "vol_scale": np.float32(float(VOL_SCALE)),
        "song_gain": [np.float32(float(f32s(s["gain"]))) for s in songs],
        "length": [s["length"] for s in songs],
        "loop": [s["loop"] for s in songs],
        "speed": [s["speed"] for s in songs],
    }
    events, first, count, loop_ptr = [], [], [], []
    for s in songs:
        for v in range(VOICES):
            cmds = sorted(s["commands"][v], key=lambda c: c[0])      # stable: keeps row order
            first.append(len(events) // 2)
            count.append(len(cmds))
            loop_ptr.append(next((i for i, c in enumerate(cmds) if c[0] >= s["loop"]), len(cmds)))
            for f, typ, w1 in cmds:
                assert f < 65536
                events += [f | (typ << 16), w1]
    t.update(events=events + [0, 0], first=first, count=count, loop_ptr=loop_ptr)
    if write:
        keep = {ROOT / p for _, p in sounds}
        for old in (ROOT / "assets/music").glob("*.wav"):
            if old not in keep:
                old.unlink()
        pack_group("music", [], sounds)
        append_tables(t, len(m.instruments))
    for w, n in conv.warnings.items():
        print(f"xm2vircon: ignored {n}x {w}")
    return t, sounds


# the vibrato's sine (FT2/OpenMPT ModSinusTable), -1..1 over 64 steps
SINE = [v / 128.0 for v in (
    0, 12, 25, 37, 49, 60, 71, 81, 90, 98, 106, 112, 117, 122, 125, 126,
    127, 126, 125, 122, 117, 112, 106, 98, 90, 81, 71, 60, 49, 37, 25, 12,
    0, -12, -25, -37, -49, -60, -71, -81, -90, -98, -106, -112, -117, -122, -125, -126,
    -127, -126, -125, -122, -117, -112, -106, -98, -90, -81, -71, -60, -49, -37, -25, -12)]


def c_array(kind, name, values, per_line=8):
    vals = [f32s(v) for v in values] if kind == "float" else [str(int(v)) for v in values]
    rows = [", ".join(vals[i:i + per_line]) for i in range(0, len(vals), per_line)] or ["0"]
    return [f"{kind}[ {max(1, len(values))} ] {name} =", "{", "    " + ",\n    ".join(rows), "};"]


def append_tables(t, instruments):
    lines = ["", "// ---- the songs, converted from assets/music/songs/sulphur.xm by tools/audio/xm2vircon.py ----", "",
             f"#define MUS_SAMPLES {len(t['sample_speed'])}",
             f"#define MUS_INSTRUMENTS {instruments}",
             f"#define MUS_SONGS {len(t['length'])}",
             f"#define MUS_VOL_SCALE {VOL_SCALE}", ""]
    lines += ["// channel speed of each sample at MIDI note 60, and its loop (0, 0: none)"]
    lines += c_array("float", "mus_sample_speed", t["sample_speed"])
    lines += c_array("int", "mus_loop_start", t["loop_start"])
    lines += c_array("int", "mus_loop_end", t["loop_end"])
    lines += ["// speed ratio of a MIDI note against note 60"]
    lines += c_array("float", "mus_semi", t["semi"])
    lines += ["// instrument volume envelopes, one value a tick; the tick held until key-off (-1: none)"]
    lines += c_array("float", "mus_env", t["env"])
    lines += c_array("int", "mus_env_first", t["env_first"])
    lines += c_array("int", "mus_env_len", t["env_len"])
    lines += c_array("int", "mus_env_sus", t["env_sus"])
    lines += c_array("float", "mus_ins_fadeout", t["fadeout"])
    lines += c_array("float", "mus_sine", t["sine"])
    lines += ["// songs: length and loop point in frames, volume"]
    lines += c_array("int", "mus_length", t["length"])
    lines += c_array("int", "mus_loop", t["loop"])
    lines += c_array("float", "mus_song_gain", t["song_gain"])
    lines += ["// per song and voice: first command, command count, the first command at the loop point"]
    lines += c_array("int", "mus_first", t["first"], 12)
    lines += c_array("int", "mus_count", t["count"], 12)
    lines += c_array("int", "mus_loop_ptr", t["loop_ptr"], 12)
    lines += ["// two words a command: frame | type << 16 (0 note, 1 key-off, 2 volume, 3 effect), then",
              "// note: sample | MIDI note << 8 | volume << 15 | instrument << 22; volume: 0..64;",
              "// effect: kind | p1 << 4 | p2 << 12 (kinds: none, volume slide up/down, vibrato speed/depth,",
              "// tone portamento speed/target note, portamento up, down, note cut at tick)"]
    hexes = [f"0x{w:08X}" for w in t["events"]]
    rows = [", ".join(hexes[i:i + 8]) for i in range(0, len(hexes), 8)]
    lines += [f"int[ {len(hexes)} ] mus_events =", "{", "    " + ",\n    ".join(rows), "};", ""]
    path = ROOT / "src/gen/music.h"
    text = path.read_text(encoding="utf-8")
    end = text.rindex("#endif")
    _atomic_write(path, text[:end] + "\n".join(lines) + "\n#endif\n")


if __name__ == "__main__":
    t, sounds = convert(Path(sys.argv[1]) if len(sys.argv) > 1 else SONG)
    print(f"{len(sounds)} samples, {len(t['length'])} songs, {len(t['events']) // 2 - 1} commands")
