"""Proves the console plays the music as the reference engine renders it.

Builds tools/audio/preview.c, runs it headless with AUDIO_OUT, drives refengine.py through the
same schedule, aligns the two recordings and compares them; reads the cycles sound_frame() took
from the memory card. Writes build/audio/verify.txt and build/audio/console_preview.wav.

    python tools/audio/verify.py      (after make.py)
"""
import os
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import dsp  # noqa: E402
import make  # noqa: E402
import refengine  # noqa: E402
from assetlib import ROOT, _atomic_write  # noqa: E402
from toolchain import tools  # noqa: E402

SONG_FRAMES, XFADE_FRAMES, EFFECT_FRAMES = 1800, 300, 150
EV_COUNT, SONG_COUNT, EV_BOOM = 11, 10, 1


def schedule():
    """(frame actions, events, part) per frame, as preview.c runs them: actions happen in the
    frame before its sound_frame()."""
    out = []
    for s in range(SONG_COUNT):
        for f in range(SONG_FRAMES):
            out.append(([("stop",), ("play", s)] if f == 0 else [], [0] * EV_COUNT, s))
    for k, song in enumerate((1, 6)):
        for f in range(XFADE_FRAMES):
            out.append(([("play", song)] if f == 0 else [], [0] * EV_COUNT, SONG_COUNT))
    for e in range(EV_COUNT + 1):
        for f in range(EFFECT_FRAMES):
            acts = [("stop",)] if (e == 0 and f == 0) else []
            ev = [0] * EV_COUNT
            if f == 0:
                ev[e if e < EV_COUNT else EV_BOOM] = 1 if e < EV_COUNT else 2
            out.append((acts, ev, SONG_COUNT + 1))
    for u in range(3):
        for f in range(40):
            out.append(([("ui", u)] if f == 0 else [], [0] * EV_COUNT, SONG_COUNT + 1))
    return out


def reference(t, sounds):
    spu = refengine.Spu(sounds)
    eng = refengine.Engine(spu, t)
    out = []
    for acts, ev, _ in schedule():
        out.append(spu.render())
        for a in acts:
            if a[0] == "stop":
                eng.music_stop()
            elif a[0] == "play":
                eng.music_play(a[1])
            else:
                eng.ui_sound(a[1])
        eng.sound_frame(ev)
    return np.concatenate(out)


def run_console():
    t = tools()
    rom = subprocess.run([sys.executable, str(ROOT / "tools/build.py"), "tools/audio/preview.c", "audio_preview"],
                         capture_output=True, text=True, cwd=ROOT)
    if rom.returncode != 0:
        sys.exit(rom.stdout + rom.stderr)
    work = ROOT / "build" / "audio" / "console"
    work.mkdir(parents=True, exist_ok=True)
    raw, card = work / "preview.raw", work / "preview.memc"
    for p in (raw, card):
        if p.exists():
            p.unlink()
    env = dict(os.environ, AUDIO_OUT=str(raw), MEMCARD=str(card))
    frames = 400 + len(schedule()) + 100
    run = subprocess.run([str(t["runner"]), str(t["bios"]), str(ROOT / "build/audio_preview.v32"), str(work), str(frames), "0"],
                         capture_output=True, text=True, env=env)
    audio = np.fromfile(raw, dtype="<i2").reshape(-1, 2)
    words = np.fromfile(card, dtype="<i4", offset=8)[:64]
    raw.unlink()
    return audio, words, run.stdout + run.stderr


def main():
    print("building the samples' reference tables...")
    import compose, instruments, sfx, songs  # noqa: E401
    inst = instruments.build()
    effects = sfx.build()
    names = [(s.name, f"assets/music/{s.name}.wav") for i in inst for s in i.samples]
    sample_pcm = [dsp.read_wav(ROOT / p) for _, p in names]
    effect_pcm = [dsp.read_wav(ROOT / f"assets/sfx/{n}.wav") for n, _, _ in effects]
    loops = [(s.loop[0], s.loop[1]) if s.loop else (0, 0) for i in inst for s in i.samples]
    bank = compose.Bank(inst)
    song_list = songs.build(bank)
    gains = [float(v) for v in (ROOT / "build/audio/gains.txt").read_text().split()]
    t = make.tables(inst, effects, song_list, gains)
    sounds = make.spu_sounds(sample_pcm, loops, effect_pcm)

    print("running the preview ROM...")
    console, card, log = run_console()
    print("rendering the reference...")
    ref = reference(t, sounds)

    # align: the cartridge starts after the BIOS; find the offset by cross-correlation
    c = console[:, 0].astype(np.float64)
    r = ref[:, 0].astype(np.float64)
    n = 1 << 22
    head = r[:44100 * 20]
    corr = np.fft.irfft(np.fft.rfft(c[:n], n * 2) * np.conj(np.fft.rfft(head, n * 2)), n * 2)
    lag = int(np.argmax(corr[:n]))
    con = console[lag:lag + len(ref)]
    m = min(len(con), len(ref))
    con, refc = con[:m], ref[:m]
    exact = float((con == refc).all(axis=1).mean())
    diff = np.abs(con.astype(np.int64) - refc.astype(np.int64))
    cc = float(np.corrcoef(con.astype(np.float64).ravel(), refc.astype(np.float64).ravel())[0, 1])
    err_db = 10 * np.log10((diff.astype(np.float64) ** 2).mean() / ((refc.astype(np.float64) ** 2).mean() + 1e-12) + 1e-20)
    dsp.write_wav(ROOT / "build/audio/console_preview.wav", con.astype(np.float64) / 32767)

    lines = [f"console audio: {len(console)} samples, cartridge audio starts at sample {lag} "
             f"(frame {lag / 735:.1f})",
             f"compared {m} samples ({m / 44100:.1f} s): identical stereo samples {exact * 100:.3f}%, "
             f"max difference {int(diff.max())} LSB, correlation {cc:.6f}, error {err_db:.1f} dB below the signal",
             "", "per part (console vs reference):"]
    sched = schedule()
    pos = 0
    labels = make.SONG_NAMES + ["crossfade", "effects"]
    for part in range(SONG_COUNT + 2):
        frames = sum(1 for s in sched if s[2] == part)
        a, b = pos * 735, (pos + frames) * 735
        pos += frames
        x, y = con[a:b].astype(np.float64), refc[a:b].astype(np.float64)
        pc = np.corrcoef(x.ravel(), y.ravel())[0, 1] if y.std() > 0 else float("nan")
        same = (con[a:b] == refc[a:b]).all(axis=1).mean() * 100
        mx, total, cnt = card[16 + part * 4: 19 + part * 4]
        lines.append(f"  {labels[part].lower():9s} correlation {pc:.6f}  identical {same:7.3f}%  "
                     f"sound_frame cycles: max {mx}, mean {total / max(cnt, 1):.0f} ({cnt} frames)")
    lines.append(f"memory card done flag: {card[0]}")
    text = "\n".join(lines) + "\n"
    _atomic_write(ROOT / "build/audio/verify.txt", text)
    print(text)
    if log.strip():
        print(log.strip()[-2000:])


if __name__ == "__main__":
    main()
