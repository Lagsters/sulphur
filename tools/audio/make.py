"""Regenerates all music and effects: instrument and effect samples (assets/music, assets/sfx),
their asset groups and C headers (src/gen/music.h, src/gen/sfx.h with the song data), reference
renders of every song through a Python mirror of the console (build/audio/*.wav), their metrics
(build/audio/metrics.txt) and MP3 previews (build/audio/preview/).

    python tools/audio/make.py            everything
    python tools/audio/make.py --no-render  samples and headers only

Needs numpy and scipy; ffmpeg for the MP3s.
"""
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import compose  # noqa: E402
import dsp  # noqa: E402
import instruments  # noqa: E402
import metrics  # noqa: E402
import refengine  # noqa: E402
import sfx  # noqa: E402
import songs  # noqa: E402
from assetlib import ROOT, _atomic_write, pack_group  # noqa: E402

OUT = ROOT / "build" / "audio"
SONG_NAMES = ["TITLE", "BATTLE", "WROCLAW", "SLEZA", "KRAKOW", "BOSS", "DRAGON", "CALM", "TENSION", "JOY"]
VEL_SCALE = "0.00393700787"        # velocity 127 -> channel gain 0.5 before the song's gain
SFX_GAIN = "0.45"                  # an effect at level 1 peaks at 0.4 of full scale
LOUDNESS_TARGET = -20.0            # approximate LUFS of every song
PEAK_CAP = 0.5                     # music peaks at most here: room for effects on top
EVENTS_TO_SFX = list(range(11))    # EV_BOMB..EV_ROAR -> the first 11 effects, in order
DUCKING = {"boom", "sheep_boom", "roar"}
TAIL_SECONDS = 12                  # renders run on past the loop point by this much


def f32s(v):
    """A float as C source text that parses back to the same float32."""
    return f"{float(np.float32(v)):.9g}"


def c_array(kind, name, values, per_line=8):
    if kind == "float":
        vals = [f32s(v) for v in values]
    else:
        vals = [str(int(v)) for v in values]
    rows = [", ".join(vals[i:i + per_line]) for i in range(0, len(vals), per_line)] or ["0"]
    return [f"{kind}[ {max(1, len(values))} ] {name} =", "{", "    " + ",\n    ".join(rows), "};"]


def pcm16(x):
    return np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16)


# ---------------------------------------------------------------------------
#   tables shared by the C header and the reference engine
# ---------------------------------------------------------------------------

def tables(inst, effects, song_list, gains):
    samples = [s for i in inst for s in i.samples]
    t = {
        "sample_speed": [np.float32((s.rate / dsp.RATE) * s.tune) for s in samples],
        "loop_start": [s.loop[0] if s.loop else 0 for s in samples],
        "loop_end": [s.loop[1] if s.loop else 0 for s in samples],
        "semi": [np.float32(2 ** ((i - 64) / 12)) for i in range(128)],
        "env_start": [np.float32(e[1]) for e in compose.ENVELOPES] + [np.float32(1)] * (16 - len(compose.ENVELOPES)),
        "env_k": [np.float32(e[2]) for e in compose.ENVELOPES] + [np.float32(0)] * (16 - len(compose.ENVELOPES)),
        "env_sus": [np.float32(e[3]) for e in compose.ENVELOPES] + [np.float32(1)] * (16 - len(compose.ENVELOPES)),
        "env_rel": [np.float32(e[4]) for e in compose.ENVELOPES] + [np.float32(0.5)] * (16 - len(compose.ENVELOPES)),
        "vib_depth": [np.float32(v) for v in compose.VIBRATO_DEPTH],
        "bend_start": [np.float32(v) for v in compose.BEND_START],
        "vel_scale": np.float32(float(VEL_SCALE)),
        "song_gain": [np.float32(float(f32s(g))) for g in gains],
        "length": [s.length for s in song_list],
        "loop": [s.loop_frame for s in song_list],
        "sfx_level": [np.float32(float(f32s(level))) for (_, _, level) in effects],
        "sfx_gain": np.float32(float(SFX_GAIN)),
        "sfx_of_event": EVENTS_TO_SFX,
        "sfx_ducks": [name in DUCKING for (name, _, _) in effects],
        "sfx_ui_first": 11,
        "snd_base": 0,
        "sfx_base": len(samples),
    }
    # round every float through its C text, so both sides use the same values
    for key in ("sample_speed", "semi", "env_start", "env_k", "env_sus", "env_rel", "vib_depth", "bend_start"):
        t[key] = [np.float32(float(f32s(v))) for v in t[key]]
    events, first, count, loop_ptr = [], [], [], []
    for s in song_list:
        for v in range(compose.VOICES):
            ev = s.events(v)
            first.append(len(events) // 2)
            count.append(len(ev))
            loop_ptr.append(next((i for i, e in enumerate(ev) if e[0] >= s.loop_frame), len(ev)))
            for e in ev:
                events.extend(compose.encode(e))
    t.update(events=events + [0, 0], first=first, count=count, loop_ptr=loop_ptr)
    return t


def music_header_tail(t, inst):
    names = [s.name for i in inst for s in i.samples]
    lines = ["", "// ---- the sequencer's data (tools/audio/make.py) ----", "",
             f"#define MUS_SAMPLES {len(names)}",
             f"#define MUS_SONGS {len(t['length'])}",
             f"#define MUS_VEL_SCALE {VEL_SCALE}", ""]
    lines += ["// playback speed of each sample at its root note: rate (half-rate samples play at 0.5)",
              "// times a tuning correction measured from the rendered pitch"]
    lines += c_array("float", "mus_sample_speed", t["sample_speed"])
    lines += ["// loop points in samples; 0, 0 for one-shots"]
    lines += c_array("int", "mus_loop_start", t["loop_start"])
    lines += c_array("int", "mus_loop_end", t["loop_end"])
    lines += ["// speed ratio of a semitone offset, index 64 = 0"]
    lines += c_array("float", "mus_semi", t["semi"])
    lines += ["// envelopes: start level, per-frame factor toward sustain, sustain, release factor",
              "// (" + ", ".join(e[0] for e in compose.ENVELOPES) + ")"]
    for key in ("env_start", "env_k", "env_sus", "env_rel"):
        lines += c_array("float", "mus_" + key, t[key])
    lines += c_array("float", "mus_vib_depth", t["vib_depth"])
    lines += c_array("float", "mus_bend_start", t["bend_start"])
    lines += ["// songs: length and loop point in frames, master gain"]
    lines += c_array("int", "mus_length", t["length"])
    lines += c_array("int", "mus_loop", t["loop"])
    lines += c_array("float", "mus_song_gain", t["song_gain"])
    lines += ["// per song and voice: first event, event count, the first event at the loop point"]
    lines += c_array("int", "mus_first", t["first"], 12)
    lines += c_array("int", "mus_count", t["count"], 12)
    lines += c_array("int", "mus_loop_ptr", t["loop_ptr"], 12)
    lines += ["// two words a note: start frame | duration << 16, then",
              "// sample | (semitones + 64) << 8 | velocity << 15 | envelope << 22 | vibrato << 26 | bend << 28"]
    hexes = [f"0x{w:08X}" for w in t["events"]]
    rows = [", ".join(hexes[i:i + 8]) for i in range(0, len(hexes), 8)]
    lines += [f"int[ {len(hexes)} ] mus_events =", "{", "    " + ",\n    ".join(rows), "};", ""]
    return lines


def sfx_header_tail(t, effects):
    lines = ["", "// ---- effect levels (tools/audio/make.py) ----", "",
             f"#define SFX_GAIN {SFX_GAIN}",
             "// channel volume of each effect, times SFX_GAIN"]
    lines += c_array("float", "sfx_level", t["sfx_level"])
    lines += ["// effects that duck the music while they play"]
    lines += c_array("int", "sfx_ducks", [int(d) for d in t["sfx_ducks"]])
    return lines + [""]


def append_to(path, lines):
    text = path.read_text(encoding="utf-8")
    end = text.rindex("#endif")
    _atomic_write(path, text[:end] + "\n".join(lines) + "\n#endif\n")


# ---------------------------------------------------------------------------
#   reference renders
# ---------------------------------------------------------------------------

def spu_sounds(sample_pcm, loops, effect_pcm):
    sounds = []
    for pcm, (ls, le) in zip(sample_pcm, loops):
        sounds.append(dict(pcm=pcm, loop=le > 0, ls=ls, le=le if le > 0 else len(pcm) - 1))
    for pcm in effect_pcm:
        sounds.append(dict(pcm=pcm, loop=False, ls=0, le=len(pcm) - 1))
    return sounds


def render_song(args):
    """One song from its start through its end and TAIL_SECONDS into the loop."""
    index, t, sounds, frames = args
    spu = refengine.Spu(sounds)
    eng = refengine.Engine(spu, t)
    eng.music_play(index)
    out = []
    for _ in range(frames):
        out.append(spu.render())
        eng.music_update()
    return np.concatenate(out)


def write_mp3(wav, mp3, fade_from=None):
    mp3.parent.mkdir(parents=True, exist_ok=True)
    af = ["-af", f"afade=t=out:st={fade_from}:d=4"] if fade_from else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), *af, "-codec:a", "libmp3lame",
                    "-b:a", "192k", str(mp3)], check=True)


def main(render=True):
    print("instruments...")
    inst = instruments.build()
    print("effects...")
    effects = sfx.build()

    music_sounds = []
    for i in inst:
        for s in i.samples:
            path = Path("assets/music") / f"{s.name}.wav"
            dsp.write_wav(ROOT / path, s.audio)          # half-rate samples too: the header says 44.1 kHz
            music_sounds.append((s.name, path.as_posix()))
    sfx_sounds = []
    for name, x, _ in effects:
        path = Path("assets/sfx") / f"{name}.wav"
        dsp.write_wav(ROOT / path, x)
        sfx_sounds.append((name, path.as_posix()))
    pack_group("music", [], music_sounds)
    pack_group("sfx", [], sfx_sounds)
    sample_pcm = [dsp.read_wav(ROOT / p) for _, p in music_sounds]
    effect_pcm = [dsp.read_wav(ROOT / p) for _, p in sfx_sounds]
    loops = [(s.loop[0], s.loop[1]) if s.loop else (0, 0) for i in inst for s in i.samples]
    rom_bytes = sum(a.nbytes for a in sample_pcm) + sum(a.nbytes for a in effect_pcm)
    print(f"sound data: {len(sample_pcm)} instrument samples, {len(effect_pcm)} effects, {rom_bytes:,} bytes")

    bank = compose.Bank(inst)
    song_list = songs.build(bank)
    sounds = spu_sounds(sample_pcm, loops, effect_pcm)

    # calibrate each song's gain: a quiet render, then loudness and peak decide
    probe = 0.2
    t = tables(inst, effects, song_list, [probe] * len(song_list))
    gains = [probe] * len(song_list)
    if render:
        print("calibrating song levels...")
        jobs = [(k, t, sounds, s.length) for k, s in enumerate(song_list)]
        with ProcessPoolExecutor() as pool:
            probes = list(pool.map(render_song, jobs))
        for k, x in enumerate(probes):
            loud = metrics.lufs(x)
            peak = np.abs(x.astype(np.float64)).max() / 32768
            gains[k] = probe * min(10 ** ((LOUDNESS_TARGET - loud) / 20), PEAK_CAP / peak)
    else:
        old = ROOT / "build/audio/gains.txt"
        if old.exists():
            gains = [float(v) for v in old.read_text().split()]
    t = tables(inst, effects, song_list, gains)

    append_to(ROOT / "src/gen/music.h", music_header_tail(t, inst))
    append_to(ROOT / "src/gen/sfx.h", sfx_header_tail(t, effects))
    OUT.mkdir(parents=True, exist_ok=True)
    _atomic_write(OUT / "gains.txt", " ".join(f32s(g) for g in gains))
    events = len(t["events"]) // 2 - 1
    print(f"songs: {events} note events, {len(t['events']) * 4:,} bytes of RAM")
    if not render:
        return

    print("reference renders...")
    jobs = [(k, t, sounds, s.length + TAIL_SECONDS * 60) for k, s in enumerate(song_list)]
    with ProcessPoolExecutor() as pool:
        renders = list(pool.map(render_song, jobs))
    report = ["song      len(s) loop(s) BPM    LUFS  TP(dBFS) 60-250Hz  S/M   centroid Hz (mean/min/max)  seam dB (bar median/p90)  seam step/p99.9"]
    for k, (s, x) in enumerate(zip(song_list, renders)):
        name = SONG_NAMES[k].lower()
        wav = OUT / f"{name}.wav"
        dsp.write_wav(wav, x.astype(np.float64) / 32767)
        song_part = x[:s.length * refengine.SAMPLES_PER_FRAME]
        cen = metrics.centroid_track(song_part)
        bar = s.spb * s.step * refengine.SAMPLES_PER_FRAME
        sm = metrics.seam(x, s.length * refengine.SAMPLES_PER_FRAME, bar, s.loop_frame * refengine.SAMPLES_PER_FRAME)
        report.append(
            f"{name:9s} {s.length / 60:6.1f} {(s.length - s.loop_frame) / 60:6.1f} {900 / s.step:6.1f} "
            f"{metrics.lufs(song_part):6.1f} {metrics.true_peak_db(song_part):7.1f} "
            f"{metrics.band_share(song_part):8.2f} {metrics.width(song_part):6.2f} "
            f"{np.mean(cen):7.0f} {np.min(cen):6.0f} {np.max(cen):6.0f}        "
            f"{sm['seam_db']:5.1f} ({sm['bar_median_db']:.1f}/{sm['bar_p90_db']:.1f})            "
            f"{sm['seam_step']:.3f}/{sm['p999_step']:.3f}")
        write_mp3(wav, OUT / "preview" / f"{name}.mp3", fade_from=s.length / 60 + TAIL_SECONDS - 4)

    # an effects reel: every effect at the level the game plays it, with gaps
    reel = []
    gap = np.zeros((int(0.5 * dsp.RATE), 2))
    for (name, x, level), pcm in zip(effects, effect_pcm):
        reel += [pcm.astype(np.float64) / 32767 * level * float(SFX_GAIN), gap]
    reel = np.concatenate(reel)
    dsp.write_wav(OUT / "effects.wav", reel)
    write_mp3(OUT / "effects.wav", OUT / "preview" / "effects.mp3")
    report.append("")
    report.append("effect      len(s)  peak(dBFS at game level)  LUFS")
    for (name, x, level), pcm in zip(effects, effect_pcm):
        y = pcm.astype(np.float64) / 32767 * level * float(SFX_GAIN)
        report.append(f"{name:11s} {len(pcm) / dsp.RATE:6.2f}  {20 * np.log10(np.abs(y).max()):8.1f}  {metrics.lufs(y):8.1f}")
    report.append("")
    report.append(f"sound data in the ROM: {rom_bytes:,} bytes; song events: {events}")
    text = "\n".join(report) + "\n"
    _atomic_write(OUT / "metrics.txt", text)
    print(text)


if __name__ == "__main__":
    main(render="--no-render" not in sys.argv)
