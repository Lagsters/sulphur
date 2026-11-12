"""Regenerates the music and effects for the console.

    python tools/audio/make.py              effects (assets/sfx), the songs module converted
                                            (assets/music, src/gen/music.h, src/gen/sfx.h),
                                            reference renders, metrics and MP3 previews
    python tools/audio/make.py --no-render  only the assets and headers
    python tools/audio/make.py --compose    first rewrites the songs module from the Python
                                            composer (songs.py, instruments.py), levelling each
                                            song's volume (Gxx): this overwrites edits made in
                                            a tracker

The songs' source of truth is the module assets/music/songs/sulphur.xm (see xm2vircon.py for
what the console plays of it). Outputs: build/audio/<song>.wav (reference renders through a
Python mirror of the console, refengine.py), build/audio/metrics.txt, build/audio/preview/*.mp3.
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

import dsp  # noqa: E402
import metrics  # noqa: E402
import refengine  # noqa: E402
import sfx  # noqa: E402
import xm2vircon  # noqa: E402
from assetlib import ROOT, _atomic_write, pack_group  # noqa: E402

OUT = ROOT / "build" / "audio"
SONG_NAMES = ["TITLE", "BATTLE", "WROCLAW", "SLEZA", "KRAKOW", "BOSS", "DRAGON", "CALM", "TENSION", "JOY"]
SFX_GAIN = "0.5"                   # an effect at level 1 peaks at 0.45 of full scale
LOUDNESS_TARGET = -20.0            # approximate LUFS of every song
PEAK_CAP = 0.5                     # music peaks at most here: room for effects on top
EVENTS_TO_SFX = list(range(11))    # EV_BOMB..EV_ROAR -> the first 11 effects, in order
DUCKING = {"boom", "sheep_boom", "roar"}
TAIL_SECONDS = 12                  # renders run on past the loop point by this much


f32s = xm2vircon.f32s
c_array = xm2vircon.c_array


def build_effects():
    effects = sfx.build()
    sounds = []
    for name, x, _ in effects:
        path = Path("assets/sfx") / f"{name}.wav"
        dsp.write_wav(ROOT / path, x)
        sounds.append((name, path.as_posix()))
    pack_group("sfx", [], sounds)
    levels = [np.float32(float(f32s(level))) for (_, _, level) in effects]
    ducks = [int(name in DUCKING) for (name, _, _) in effects]
    lines = ["", "// ---- effect levels (tools/audio/make.py) ----", "",
             f"#define SFX_GAIN {SFX_GAIN}", "// channel volume of each effect, times SFX_GAIN"]
    lines += c_array("float", "sfx_level", levels)
    lines += ["// effects that duck the music while they play"]
    lines += c_array("int", "sfx_ducks", ducks)
    path = ROOT / "src/gen/sfx.h"
    text = path.read_text(encoding="utf-8")
    end = text.rindex("#endif")
    _atomic_write(path, text[:end] + "\n".join(lines) + "\n\n#endif\n")
    return effects, sounds, levels, ducks


def engine_data(t, music_sounds, effects, levels, ducks):
    """The tables of the C code plus the effects' and the SPU's sounds, for refengine."""
    d = dict(t)
    d.update(sfx_level=levels, sfx_gain=np.float32(float(SFX_GAIN)), sfx_of_event=EVENTS_TO_SFX,
             sfx_ducks=ducks, sfx_ui_first=11, snd_base=0, sfx_base=len(music_sounds))
    sounds = []
    for k, (_, p) in enumerate(music_sounds):
        pcm = dsp.read_wav(ROOT / p)
        ls, le = t["loop_start"][k], t["loop_end"][k]
        sounds.append(dict(pcm=pcm, loop=le > 0, ls=ls, le=le if le > 0 else len(pcm) - 1))
    for name, _, _ in effects:
        pcm = dsp.read_wav(ROOT / f"assets/sfx/{name}.wav")
        sounds.append(dict(pcm=pcm, loop=False, ls=0, le=len(pcm) - 1))
    return d, sounds


def render_song(args):
    """One song from its start through `frames` frames (past its end it loops)."""
    index, d, sounds, frames = args
    spu = refengine.Spu(sounds)
    eng = refengine.Engine(spu, d)
    eng.music_play(index)
    out = []
    for _ in range(frames):
        out.append(spu.render())
        eng.music_update()
    return np.concatenate(out)


def render_all(d, sounds, frames):
    jobs = [(k, d, sounds, f) for k, f in enumerate(frames)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        return list(pool.map(render_song, jobs))


def compose():
    """Writes the module from the Python composer, then levels the songs: a quiet render of
    each decides its Gxx from its loudness and peak."""
    import compose as composer
    import compose_xm
    import instruments
    import songs
    import xmfile
    print("instruments...")
    inst = instruments.build()
    song_list = songs.build(composer.Bank(inst))
    xm2vircon.SONG.parent.mkdir(parents=True, exist_ok=True)
    xmfile.write(xm2vircon.SONG, compose_xm.build(inst, song_list, [64] * len(song_list)))
    effects, _, levels, ducks = build_effects()
    t, music_sounds = xm2vircon.convert()
    probe = 0.1
    d, sounds = engine_data(t, music_sounds, effects, levels, ducks)
    d["song_gain"] = [np.float32(probe)] * len(song_list)
    print("levelling the songs...")
    probes = render_all(d, sounds, t["length"])
    volumes = []
    for x in probes:
        loud = metrics.lufs(x)
        peak = np.abs(x.astype(np.float64)).max() / 32768
        gain = probe * min(10 ** ((LOUDNESS_TARGET - loud) / 20), PEAK_CAP / peak)
        volumes.append(int(max(1, min(64, np.floor(gain * 64)))))
    print("song volumes (Gxx):", volumes)
    xmfile.write(xm2vircon.SONG, compose_xm.build(inst, song_list, volumes))


def write_mp3(wav, mp3, fade_from=None):
    mp3.parent.mkdir(parents=True, exist_ok=True)
    af = ["-af", f"afade=t=out:st={fade_from}:d=4"] if fade_from else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), *af, "-codec:a", "libmp3lame",
                    "-b:a", "192k", str(mp3)], check=True)


def main(render=True):
    effects, sfx_sounds, levels, ducks = build_effects()
    t, music_sounds = xm2vircon.convert()
    d, sounds = engine_data(t, music_sounds, effects, levels, ducks)
    rom_bytes = sum(s["pcm"].nbytes for s in sounds)
    events = len(t["events"]) // 2 - 1
    print(f"sound data: {len(music_sounds)} instrument samples, {len(effects)} effects, {rom_bytes:,} bytes; "
          f"{events} song commands ({len(t['events']) * 4:,} bytes of RAM)")
    if not render:
        return
    OUT.mkdir(parents=True, exist_ok=True)
    print("reference renders...")
    frames = [n + TAIL_SECONDS * 60 for n in t["length"]]
    renders = render_all(d, sounds, frames)
    report = ["song      len(s) loop(s) BPM    LUFS  TP(dBFS) 60-250Hz  S/M   centroid Hz (mean/min/max)  "
              "seam dB (bar median/p90)  seam step/p99.9"]
    spf = refengine.SAMPLES_PER_FRAME
    for k, x in enumerate(renders):
        name = SONG_NAMES[k].lower()
        length, loop, speed = t["length"][k], t["loop"][k], t["speed"][k]
        wav = OUT / f"{name}.wav"
        dsp.write_wav(wav, x.astype(np.float64) / 32767)
        part = x[:length * spf]
        cen = metrics.centroid_track(part)
        sm = metrics.seam(x, length * spf, 16 * speed * spf, loop * spf)
        report.append(
            f"{name:9s} {length / 60:6.1f} {(length - loop) / 60:6.1f} {900 / speed:6.1f} "
            f"{metrics.lufs(part):6.1f} {metrics.true_peak_db(part):7.1f} "
            f"{metrics.band_share(part):8.2f} {metrics.width(part):6.2f} "
            f"{np.mean(cen):7.0f} {np.min(cen):6.0f} {np.max(cen):6.0f}        "
            f"{sm['seam_db']:5.1f} ({sm['bar_median_db']:.1f}/{sm['bar_p90_db']:.1f})            "
            f"{sm['seam_step']:.3f}/{sm['p999_step']:.3f}")
        write_mp3(wav, OUT / "preview" / f"{name}.mp3", fade_from=length / 60 + TAIL_SECONDS - 4)

    reel = []
    gap = np.zeros((int(0.5 * dsp.RATE), 2))
    report += ["", "effect      len(s)  peak dBFS (as played)  LUFS"]
    for (name, _, level), s in zip(effects, sounds[len(music_sounds):]):
        y = s["pcm"].astype(np.float64) / 32767 * level * float(SFX_GAIN)
        reel += [y, gap]
        report.append(f"{name:11s} {len(y) / dsp.RATE:6.2f}  {20 * np.log10(np.abs(y).max()):8.1f}  {metrics.lufs(y):12.1f}")
    dsp.write_wav(OUT / "effects.wav", np.concatenate(reel))
    write_mp3(OUT / "effects.wav", OUT / "preview" / "effects.mp3")
    report += ["", f"sound data in the ROM: {rom_bytes:,} bytes; song commands: {events}"]
    text = "\n".join(report) + "\n"
    _atomic_write(OUT / "metrics.txt", text)
    print(text)


if __name__ == "__main__":
    if "--compose" in sys.argv:
        compose()
    main(render="--no-render" not in sys.argv)
