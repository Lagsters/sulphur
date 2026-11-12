"""Proves the console plays the songs as the tracker module says.

Builds tools/audio/preview.c, runs it headless with AUDIO_OUT and drives refengine.py through the
same schedule: the two must match (same samples, up to float rounding in vibrato and slides).
Then renders the first 30 s of every song with libopenmpt (openmpt123: OPENMPT123 or PATH) and
compares it with both: waveform, 50 ms loudness envelope and third-octave spectrum correlations
and the loudness difference. Reads the cycles sound_frame() took from the memory card.
Writes build/audio/verify.txt.

    python tools/audio/verify.py      (after make.py)
"""
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import dsp  # noqa: E402
import make  # noqa: E402
import metrics  # noqa: E402
import refengine  # noqa: E402
import xm2vircon  # noqa: E402
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
    for song in (1, 6):
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


def reference(d, sounds):
    spu = refengine.Spu(sounds)
    eng = refengine.Engine(spu, d)
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


# libopenmpt's command-line player (lib.openmpt.org, openmpt123.exe in the Windows binaries zip)
OPENMPT = os.environ.get("OPENMPT123") or shutil.which("openmpt123") or "openmpt123"


def openmpt(song, seconds, out):
    """libopenmpt's render of a subsong: 44.1 kHz, no interpolation and no volume ramping, as
    close to the console's mixer as it goes."""
    subprocess.run([OPENMPT, "--batch", "--quiet", "--force", "--subsong", str(song), "--end-time", str(seconds),
                    "--samplerate", "44100", "--filter", "1", "--ramping", "0", "--no-float", "--dither", "0",
                    "-o", str(out), str(ROOT / "assets/music/songs/sulphur.xm")], check=True, capture_output=True)
    x = dsp.read_wav(out)
    out.unlink()
    return x


def align(a, b, max_lag=44100):
    """Lag of b against a, -max_lag..max_lag (b[lag:] lines up with a; a negative lag means b
    is early), from the mid signals' cross-correlation over 10 s."""
    x = a.astype(np.float64).mean(axis=1)[:44100 * 10]
    y = b.astype(np.float64).mean(axis=1)[:44100 * 10 + max_lag]
    n = 1 << int(np.ceil(np.log2(len(x) + len(y) + max_lag)))
    c = np.fft.irfft(np.fft.rfft(y, n) * np.conj(np.fft.rfft(x, n)), n)
    lags = np.concatenate([np.arange(0, max_lag), np.arange(-max_lag, 0)])
    vals = np.concatenate([c[:max_lag], c[n - max_lag:]])
    return int(lags[np.argmax(vals)])


def shifted(x, lag, n):
    """x moved by lag samples (padded with silence), n long."""
    if lag >= 0:
        y = x[lag:lag + n]
    else:
        y = np.concatenate([np.zeros((-lag, 2), dtype=x.dtype), x[:n + lag]])
    return y


def compare(a, b):
    """Correlation of the waveforms, of their 50 ms loudness envelopes and of their spectra in
    third-octave bands, and the loudness difference b - a."""
    m = min(len(a), len(b))
    a, b = a[:m].astype(np.float64), b[:m].astype(np.float64)
    wave = float(np.corrcoef(a.ravel(), b.ravel())[0, 1])
    w = 2205

    def env(x):
        mm = x.mean(axis=1)[: (m // w) * w].reshape(-1, w)
        return np.sqrt((mm ** 2).mean(axis=1))

    envc = float(np.corrcoef(env(a), env(b))[0, 1])
    edges = 20 * 2 ** (np.arange(31) / 3)

    def bands(x):
        f, p = signal.welch(x.mean(axis=1), 44100, nperseg=8192)
        return np.array([p[(f >= lo) & (f < hi)].sum() for lo, hi in zip(edges, edges[1:])])

    spec = float(np.corrcoef(10 * np.log10(bands(a) + 1e-9), 10 * np.log10(bands(b) + 1e-9))[0, 1])
    return wave, envc, spec, metrics.lufs(b) - metrics.lufs(a)


def main():
    effects, _, levels, ducks = make.build_effects()
    t, music_sounds = xm2vircon.convert()
    d, sounds = make.engine_data(t, music_sounds, effects, levels, ducks)

    print("running the preview ROM...")
    console, card, log = run_console()
    print("rendering the reference...")
    ref = reference(d, sounds)
    lag = max(0, align(ref, console, len(console) - len(ref) + 1))
    con = console[lag:lag + len(ref)]
    m = min(len(con), len(ref))
    con, refc = con[:m], ref[:m]
    exact = float((con == refc).all(axis=1).mean())
    diff = np.abs(con.astype(np.int64) - refc.astype(np.int64))
    dsp.write_wav(ROOT / "build/audio/console_preview.wav", con.astype(np.float64) / 32767)

    lines = [f"console vs reference engine (preview ROM, {m / 44100:.1f} s from frame {lag / 735:.1f}):",
             f"  identical stereo samples {exact * 100:.3f}%, largest difference {int(diff.max())} LSB", ""]
    sched = schedule()
    pos = 0
    labels = make.SONG_NAMES + ["crossfade", "effects"]
    lines.append("part       console~reference: wave env  spectrum  dLUFS   identical  | sound_frame cycles max/mean")
    for part in range(SONG_COUNT + 2):
        frames = sum(1 for s in sched if s[2] == part)
        a, b = pos * 735, (pos + frames) * 735
        pos += frames
        wv, ev, sp, dl = compare(refc[a:b], con[a:b])
        same = (con[a:b] == refc[a:b]).all(axis=1).mean() * 100
        mx, total, cnt = card[16 + part * 4: 19 + part * 4]
        lines.append(f"  {labels[part].lower():9s} {wv:9.5f} {ev:7.4f} {sp:7.4f} {dl:+7.2f}  {same:8.3f}%  "
                     f"| {mx} / {total / max(cnt, 1):.0f}")
    lines += ["", "libopenmpt (the tracker) vs reference engine and console, first 30 s of each song:",
              "song       openmpt~reference: wave  env   spectrum dLUFS | openmpt~console: wave  env  spectrum dLUFS"]
    for k in range(SONG_COUNT):
        ompt = openmpt(k, 30, ROOT / "build/audio/openmpt.wav")
        a = refc[k * SONG_FRAMES * 735:(k + 1) * SONG_FRAMES * 735]
        c = con[k * SONG_FRAMES * 735:(k + 1) * SONG_FRAMES * 735]
        lg = align(a, ompt, 1470)   # libopenmpt is a frame early: the console hears a write a frame later
        o = shifted(ompt, lg, len(a))
        r1 = compare(a, o)
        r2 = compare(c, o)
        lines.append(f"  {make.SONG_NAMES[k].lower():9s} {r1[0]:8.4f} {r1[1]:6.4f} {r1[2]:6.4f} {r1[3]:+6.2f}"
                     f" | {r2[0]:8.4f} {r2[1]:6.4f} {r2[2]:6.4f} {r2[3]:+6.2f}   (lag {lg})")
    lines.append(f"memory card done flag: {card[0]}")
    text = "\n".join(lines) + "\n"
    _atomic_write(ROOT / "build/audio/verify.txt", text)
    print(text)
    if log.strip():
        print(log.strip()[-1500:])


if __name__ == "__main__":
    main()
