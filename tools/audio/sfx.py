"""Sound effects, synthesized: one stereo sample per game event (state.h EV_*) and per UI sound.

Order matters: it is the order of the sfx group in the ROM (SND_SFX_<NAME> in src/gen/sfx.h).
"""
import numpy as np

import dsp
from dsp import RATE

ROOM = dsp.reverb_ir(0.8, 0.6, 0.3, pre_ms=8, seed=21)
HALL = dsp.reverb_ir(2.2, 1.8, 0.9, pre_ms=18, seed=22)


def t_(sec):
    return dsp.seconds(sec)


def noise(n, seed):
    return dsp.rng(seed).standard_normal(n)


def env_exp(t, tau, attack=0.002):
    return np.exp(-t / tau) * np.clip(t / attack, 0, 1)


def crackles(t, seed, rate_hz, start, end, tau=0.004, level=1.0, hp_f=1500):
    """Random short clicks between start and end seconds: debris, fuse sparks, fire."""
    r = dsp.rng(seed)
    x = np.zeros(len(t))
    count = int(rate_hz * (end - start))
    for _ in range(count):
        at = int(r.uniform(start, end) * RATE)
        n = int(tau * 8 * RATE)
        seg = r.standard_normal(n) * np.exp(-np.arange(n) / (tau * RATE)) * r.uniform(0.2, 1.0)
        x[at:at + n] += seg[:max(0, len(x) - at)]
    return dsp.hp(x, hp_f, 2) * level


def bomb():
    """A match strike, then the sulphur fuse catching: a bright hiss with sparks."""
    t = t_(0.85)
    strike = dsp.bp(noise(len(t), 1), 1500, 9000, 2) * env_exp(t, 0.03) * 1.2
    flare = dsp.bp(noise(len(t), 2), 400, 3000, 2) * np.exp(-((t - 0.07) / 0.06) ** 2) * 0.9
    hiss_env = np.clip((t - 0.05) / 0.12, 0, 1) * (0.55 + 0.1 * np.sin(2 * np.pi * 13 * t))
    hiss = dsp.bp(noise(len(t), 3), 3500, 12000, 2) * hiss_env * 0.45
    sparks = crackles(t, 4, 40, 0.08, 0.8, 0.0015, 1.4, 4000)
    x = strike + flare + hiss + sparks
    st = dsp.pan(x, -0.1) + dsp.pan(sparks * 0.5, 0.5)
    st = dsp.reverb(st, ROOM, 0.15)[:len(t)]
    return dsp.fade_out(st, 0.15)


def _boom(seed, dur, depth_hz, size):
    t = t_(dur)
    # the thump: a pitch-falling sine, felt more than heard
    f = depth_hz + 90 * np.exp(-t / 0.05)
    sub = np.sin(2 * np.pi * np.cumsum(f) / RATE) * env_exp(t, 0.35 * size, 0.003)
    # the blast: broadband noise falling in brightness
    n = noise(len(t), seed)
    cut = 300 + 6000 * np.exp(-t / (0.06 * size))
    body = dsp.onepole_lp_var(n, cut) * env_exp(t, 0.25 * size, 0.001) * 2.2
    crack = dsp.hp(noise(len(t), seed + 1), 1200, 2) * env_exp(t, 0.012, 0.0005) * 1.0
    rumble = dsp.lp(noise(len(t), seed + 2), 160, 4) * env_exp(t, 0.6 * size, 0.05) * 6
    debris = crackles(t, seed + 3, 30 * size, 0.12, dur * 0.7, 0.003, 0.6, 1200)
    x = np.tanh(1.3 * (sub * 1.1 + body + crack)) + rumble + debris
    left = x + 0.4 * dsp.lp(noise(len(t), seed + 4), 400, 2) * env_exp(t, 0.3 * size)
    right = x + 0.4 * dsp.lp(noise(len(t), seed + 5), 400, 2) * env_exp(t, 0.3 * size)
    st = np.stack([left, right], axis=1)
    st = dsp.reverb(st, HALL, 0.25 * size)[:len(t)]
    return dsp.fade_out(st, dur * 0.3)


def boom():
    return _boom(10, 1.5, 42, 1.0)


def sheep_boom():
    """Bigger: deeper, longer, more debris, and a second blast."""
    a = _boom(20, 2.2, 34, 1.6)
    b = _boom(30, 2.2, 50, 1.0)
    d = int(0.16 * RATE)
    b = np.concatenate([np.zeros((d, 2)), b[:-d]])
    return a + 0.55 * b


def pickup():
    """A bright three-note bell chime rising (A5, C#6, E6), with sparkle."""
    t = t_(0.6)
    x = np.zeros(len(t))
    for k, m in enumerate([81, 85, 88]):
        at = int(k * 0.055 * RATE)
        tt = t[:len(t) - at]
        f = 440 * 2 ** ((m - 69) / 12)
        tone = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 2.76 * f * tt) * np.exp(-tt / 0.08)
                + 0.2 * np.sin(2 * np.pi * 5.4 * f * tt) * np.exp(-tt / 0.03))
        x[at:] += tone * env_exp(tt, 0.22, 0.001)
    st = np.stack([x, np.roll(x, 90)], axis=1)
    st = dsp.reverb(st, HALL, 0.22)[:len(t)]
    return dsp.fade_out(st, 0.15)


def death():
    """A falling groan over a low thud: a formant voice sliding down an octave."""
    t = t_(1.1)
    f0 = 180 * 2 ** (-1.2 * t) * (1 + 0.02 * np.sin(2 * np.pi * 7 * t))
    ph = 2 * np.pi * np.cumsum(f0) / RATE
    glottal = sum(np.sin(k * ph) / k ** 1.2 for k in range(1, 50))
    v = dsp.eq(glottal, [("peak", 650, 4, 14), ("peak", 1100, 5, 10), ("peak", 2500, 6, 6), ("lp", 4000, 0.7, 0)])
    v = v / np.abs(v).max() * env_exp(t, 0.45, 0.03)
    thud_f = 55 + 60 * np.exp(-t / 0.04)
    thud = np.sin(2 * np.pi * np.cumsum(thud_f) / RATE) * env_exp(t, 0.18, 0.002)
    x = 0.8 * v + 0.9 * thud
    st = dsp.reverb(x, ROOM, 0.3)[:len(t)]
    return dsp.fade_out(st, 0.25)


def shield():
    """A glass shell breaking: a crack, then many short high pings and falling shards."""
    t = t_(0.9)
    r = dsp.rng(41)
    x = dsp.hp(noise(len(t), 40), 2500, 2) * env_exp(t, 0.03, 0.0005) * 1.2
    for _ in range(26):
        at = r.uniform(0.0, 0.5)
        f = r.uniform(2500, 9000)
        tt = np.clip(t - at, 0, None)
        x += (t >= at) * np.sin(2 * np.pi * f * tt) * np.exp(-tt / r.uniform(0.02, 0.09)) * r.uniform(0.15, 0.5)
    hum = np.sin(2 * np.pi * 440 * t) * np.sin(2 * np.pi * 7 * t) * env_exp(t, 0.15) * 0.3
    x = x + hum
    st = np.stack([x, np.roll(x, 140)], axis=1)
    st = dsp.reverb(st, ROOM, 0.3)[:len(t)]
    return dsp.fade_out(st, 0.2)


def baa():
    """A sheep: a glottal pulse at ~330 Hz with the bleat's fast tremolo, through the formants of
    an open "ae" vowel, a short "b" onset and a falling end."""
    dur = 0.8
    t = t_(dur)
    r = dsp.rng(51)
    contour = 1 + 0.08 * np.clip(t / 0.08, 0, 1) - 0.18 * np.clip((t - 0.45) / 0.3, 0, 1)
    jitter = 1 + 0.01 * dsp.lp(r.standard_normal(len(t)), 40, 1) * 10
    f0 = 330 * contour * jitter
    ph = 2 * np.pi * np.cumsum(f0) / RATE
    # a glottal pulse: rich in harmonics, tilting -12 dB/oct
    src = sum(np.sin(k * ph) / k ** 1.5 for k in range(1, 40))
    src += 0.15 * r.standard_normal(len(t))       # breathiness
    trem = 0.55 + 0.45 * np.sin(2 * np.pi * 23 * t) ** 2
    x = np.zeros(len(t))
    for f, bw, g in [(800, 90, 1.0), (1750, 120, 0.6), (2650, 160, 0.35), (3600, 250, 0.15)]:
        x += dsp.resonator(src, f, 1 / (np.pi * bw)) * g
    x = x / np.abs(x).max()
    amp = np.clip((t - 0.02) / 0.04, 0, 1) * np.clip((dur - t) / 0.25, 0, 1)
    x *= amp * trem
    x += dsp.lp(r.standard_normal(len(t)), 400, 2) * np.exp(-((t - 0.02) / 0.01) ** 2) * 0.3   # the "b"
    st = dsp.reverb(x, ROOM, 0.18)[:len(t)]
    return dsp.fade_out(st, 0.1)


def boss_hit():
    """A heavy blow: a low thud, a metallic clang and a short growl of pain."""
    t = t_(0.75)
    thud_f = 60 + 80 * np.exp(-t / 0.03)
    thud = np.sin(2 * np.pi * np.cumsum(thud_f) / RATE) * env_exp(t, 0.15)
    clang = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, d in
                [(523, 0.25), (1311, 0.18), (2087, 0.12), (3290, 0.08)]) * 0.35
    f0 = 110 * (1 - 0.3 * t) * (1 + 0.04 * noise(len(t), 61).clip(-2, 2) * 0.3)
    ph = 2 * np.pi * np.cumsum(f0) / RATE
    growl = np.tanh(3 * sum(np.sin(k * ph) / k for k in range(1, 30)))
    growl = dsp.eq(growl, [("peak", 600, 3, 9), ("peak", 1200, 4, 6), ("lp", 3000, 0.7, 0)])
    growl = growl / np.abs(growl).max() * np.clip((t - 0.05) / 0.05, 0, 1) * np.exp(-t / 0.25) * 0.5
    crack = dsp.hp(noise(len(t), 62), 2000, 2) * env_exp(t, 0.008, 0.0003)
    x = np.tanh(1.2 * (thud + clang + crack)) + growl
    st = dsp.reverb(x, ROOM, 0.3)[:len(t)]
    st = dsp.width(st, 1.3)
    return dsp.fade_out(st, 0.15)


def fire():
    """Dragon fire: a roaring, swelling noise with a low rumble and crackling."""
    dur = 1.5
    t = t_(dur)
    n = noise(len(t), 71)
    swell = np.clip(t / 0.15, 0, 1) * np.clip((dur - t) / 0.5, 0, 1)
    flutter = 1 + 0.3 * dsp.lp(noise(len(t), 72), 12, 1) * 15
    roar = dsp.bp(n, 200, 2500, 2) * swell * flutter
    hiss = dsp.hp(noise(len(t), 73), 3000, 2) * swell * 0.25
    rumble = dsp.lp(noise(len(t), 74), 120, 4) * swell * 4
    cr = crackles(t, 75, 60, 0.1, dur - 0.1, 0.002, 1.0, 2500)
    x = roar + hiss + rumble + cr
    left = x + 0.3 * dsp.bp(noise(len(t), 76), 300, 2000, 2) * swell
    right = x + 0.3 * dsp.bp(noise(len(t), 77), 300, 2000, 2) * swell
    st = np.stack([left, right], axis=1)
    st = dsp.reverb(st, HALL, 0.15)[:len(t)]
    return dsp.fade_out(st, 0.2)


def wall():
    """The arena closing: stone grinding on stone, then a heavy thud and dust."""
    dur = 1.3
    t = t_(dur)
    r = dsp.rng(81)
    n = noise(len(t), 82)
    grain = np.abs(dsp.lp(r.standard_normal(len(t)), 35, 1)) * 25   # the rough, stuttering scrape
    grind = dsp.bp(n, 150, 1800, 2) * grain * np.clip(t / 0.05, 0, 1) * (t < 0.85)
    grind = dsp.eq(grind, [("peak", 400, 1.5, 6)])
    hit_t = np.clip(t - 0.85, 0, None)
    thud_f = 45 + 50 * np.exp(-hit_t / 0.04)
    thud = (t >= 0.85) * np.sin(2 * np.pi * np.cumsum(thud_f) / RATE) * np.exp(-hit_t / 0.18) * 1.6
    dust = (t >= 0.85) * dsp.bp(noise(len(t), 83), 800, 6000, 2) * np.exp(-hit_t / 0.12) * 0.6
    x = 0.6 * grind + thud + dust
    st = dsp.reverb(x, ROOM, 0.3)[:len(t)]
    st = dsp.width(st, 1.5)
    return dsp.fade_out(st, 0.1)


def roar():
    """The dragon: a huge growling voice (a jittered pulse at ~70 Hz through "aw" formants,
    overdriven) rising then falling, with a breathy noise layer."""
    dur = 2.0
    t = t_(dur)
    r = dsp.rng(91)
    contour = 1 + 0.5 * np.sin(np.pi * np.clip(t / 1.6, 0, 1)) - 0.2 * np.clip((t - 1.3) / 0.7, 0, 1)
    jitter = 1 + 0.06 * dsp.lp(r.standard_normal(len(t)), 25, 1) * 12
    f0 = 68 * contour * jitter
    ph = 2 * np.pi * np.cumsum(f0) / RATE
    src = sum(np.sin(k * ph) / k ** 0.9 for k in range(1, 120))
    src = np.tanh(2.5 * src / np.abs(src).max())
    breath = r.standard_normal(len(t)) * 0.4
    x = np.zeros(len(t))
    for f, bw, g in [(450, 100, 1.0), (800, 120, 0.8), (1400, 200, 0.5), (2600, 300, 0.3)]:
        x += dsp.resonator(src + breath, f, 1 / (np.pi * bw)) * g
    x = x / np.abs(x).max()
    sub = np.sin(2 * np.pi * np.cumsum(f0 * 0.5) / RATE) * 0.5
    amp = np.clip(t / 0.12, 0, 1) * np.clip((dur - t) / 0.6, 0, 1)
    x = np.tanh(1.6 * (x + sub)) * amp
    st = dsp.reverb(x, HALL, 0.35)[:len(t)]
    st = dsp.width(st, 1.4)
    return dsp.fade_out(st, 0.15)


def ui_move():
    t = t_(0.07)
    x = np.sin(2 * np.pi * 1400 * t) * env_exp(t, 0.012, 0.0005) + dsp.bp(noise(len(t), 101), 2000, 6000, 2) * env_exp(t, 0.004, 0.0003) * 0.4
    return dsp.fade_out(np.stack([x, x], axis=1), 0.01)


def ui_confirm():
    t = t_(0.38)
    x = np.zeros(len(t))
    for k, m in enumerate([74, 81]):
        at = int(k * 0.07 * RATE)
        tt = t[:len(t) - at]
        f = 440 * 2 ** ((m - 69) / 12)
        x[at:] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 3 * f * tt) * np.exp(-tt / 0.04)) * env_exp(tt, 0.12, 0.001)
    st = np.stack([x, np.roll(x, 60)], axis=1)
    st = dsp.reverb(st, ROOM, 0.2)[:len(t)]
    return dsp.fade_out(st, 0.08)


def ui_type():
    t = t_(0.045)
    x = dsp.bp(noise(len(t), 111), 1500, 7000, 2) * env_exp(t, 0.005, 0.0003) + np.sin(2 * np.pi * 900 * t) * env_exp(t, 0.008) * 0.4
    return dsp.fade_out(np.stack([x, x], axis=1), 0.01)


# name, function, relative loudness (the channel volume the game plays it at)
EFFECTS = [
    ("bomb", bomb, 0.7),
    ("boom", boom, 1.0),
    ("pickup", pickup, 0.6),
    ("death", death, 0.85),
    ("shield", shield, 0.7),
    ("baa", baa, 0.8),
    ("sheep_boom", sheep_boom, 1.0),
    ("boss_hit", boss_hit, 0.85),
    ("fire", fire, 0.85),
    ("wall", wall, 0.8),
    ("roar", roar, 1.0),
    ("ui_move", ui_move, 0.45),
    ("ui_confirm", ui_confirm, 0.5),
    ("ui_type", ui_type, 0.3),
]


def build():
    out = []
    for name, fn, level in EFFECTS:
        x = fn()
        x = x / np.abs(x).max() * 0.89
        out.append((name, x, level))
    return out
