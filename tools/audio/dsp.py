"""DSP building blocks for the offline instrument and effect renderer (numpy + scipy).

Everything works on float64 arrays at RATE (44.1 kHz) unless a function takes `rate`.
Stereo signals are arrays of shape (n, 2).
"""
import wave
from pathlib import Path

import numpy as np
from scipy import signal

RATE = 44100


def seconds(n, rate=RATE):
    return np.arange(int(n * rate)) / rate


def rng(seed):
    return np.random.default_rng(seed)


# ---------------------------------------------------------------------------
#   filters (RBJ cookbook biquads as second-order sections)
# ---------------------------------------------------------------------------

def _biquad(kind, f, q=0.707, gain_db=0.0, rate=RATE):
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * min(f, rate * 0.49) / rate
    cw, sw = np.cos(w), np.sin(w)
    alpha = sw / (2 * q)
    if kind == "lp":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        aa = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "hp":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        aa = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "bp":
        b = [alpha, 0, -alpha]
        aa = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "peak":
        b = [1 + alpha * a, -2 * cw, 1 - alpha * a]
        aa = [1 + alpha / a, -2 * cw, 1 - alpha / a]
    elif kind == "lowshelf":
        sq = 2 * np.sqrt(a) * alpha
        b = [a * ((a + 1) - (a - 1) * cw + sq), 2 * a * ((a - 1) - (a + 1) * cw), a * ((a + 1) - (a - 1) * cw - sq)]
        aa = [(a + 1) + (a - 1) * cw + sq, -2 * ((a - 1) + (a + 1) * cw), (a + 1) + (a - 1) * cw - sq]
    elif kind == "highshelf":
        sq = 2 * np.sqrt(a) * alpha
        b = [a * ((a + 1) + (a - 1) * cw + sq), -2 * a * ((a - 1) + (a + 1) * cw), a * ((a + 1) + (a - 1) * cw - sq)]
        aa = [(a + 1) - (a - 1) * cw + sq, 2 * ((a - 1) - (a + 1) * cw), (a + 1) - (a - 1) * cw - sq]
    elif kind == "notch":
        b = [1, -2 * cw, 1]
        aa = [1 + alpha, -2 * cw, 1 - alpha]
    else:
        raise ValueError(kind)
    return np.array([b[0] / aa[0], b[1] / aa[0], b[2] / aa[0], 1.0, aa[1] / aa[0], aa[2] / aa[0]])


def eq(x, bands, rate=RATE):
    """bands: list of (kind, freq, q, gain_db). Works on mono or stereo."""
    sos = np.array([_biquad(k, f, q, g, rate) for (k, f, q, g) in bands])
    return signal.sosfilt(sos, x, axis=0)


def lp(x, f, order=2, rate=RATE):
    return signal.sosfilt(signal.butter(order, min(f, rate * 0.45), "low", fs=rate, output="sos"), x, axis=0)


def hp(x, f, order=2, rate=RATE):
    return signal.sosfilt(signal.butter(order, f, "high", fs=rate, output="sos"), x, axis=0)


def bp(x, f0, f1, order=2, rate=RATE):
    return signal.sosfilt(signal.butter(order, [f0, min(f1, rate * 0.45)], "band", fs=rate, output="sos"), x, axis=0)


def onepole_lp_var(x, cutoff, rate=RATE):
    """One-pole low-pass with a time-varying cutoff (array), mono; a Python loop."""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    alpha = 1 - np.exp(-2 * np.pi * cutoff / rate)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha[i] * (x[i] - acc)
        y[i] = acc
    return y


def resonator(x, f, decay, rate=RATE):
    """Two-pole resonator at f with an amplitude decay time `decay` seconds."""
    r = np.exp(-1.0 / (decay * rate))
    w = 2 * np.pi * f / rate
    return signal.lfilter([1 - r], [1, -2 * r * np.cos(w), r * r], x, axis=0)


# ---------------------------------------------------------------------------
#   strings: Karplus-Strong with a fractional delay, vectorised a period at a time
# ---------------------------------------------------------------------------

def ks_string(f0, dur, excitation, loss=0.996, bright=0.7, rate=RATE):
    """A plucked string: the loop holds a period of excitation and runs through a symmetric
    3-tap low-pass (brightness `bright`, 0..1) and a linear-interpolated fractional delay.
    `loss` is the gain per period. `excitation` is added at the start (any length)."""
    n = int(dur * rate)
    d = rate / f0 - 1.0                      # the 3-tap filter delays one sample
    N = int(np.floor(d))
    fr = d - N
    c1 = 0.5 + 0.5 * bright
    c0 = (1 - c1) / 2
    taps = np.convolve([c0, c1, c0], [1 - fr, fr]) * loss   # delays N, N+1, N+2, N+3
    off = N + 4                              # y[off + i] is output sample i
    exc = np.zeros(n)
    exc[:min(n, len(excitation))] = excitation[:n]
    y = np.zeros(off + n)
    i = 0
    while i < n:
        j = min(n, i + N)
        k = np.arange(i, j) + off
        y[k] = exc[i:j] + taps[0] * y[k - N] + taps[1] * y[k - N - 1] + taps[2] * y[k - N - 2] + taps[3] * y[k - N - 3]
        i = j
    return y[off:]


def pluck_excitation(f0, seed, pick_pos=0.13, softness=0.3, rate=RATE):
    """A period of noise shaped like a pick: low-passed by softness, comb-filtered at the pick
    position (the missing harmonics give the string its place)."""
    r = rng(seed)
    period = int(rate / f0)
    e = r.uniform(-1, 1, period)
    e = e - e.mean()
    if softness > 0:
        e = lp(e, 1200 + (1 - softness) * 9000, 1)
    p = max(1, int(pick_pos * period))
    e = e - np.concatenate([np.zeros(p), e[:-p]])
    return e


def comb_pickup(x, f0, pos=0.1, rate=RATE):
    """An electric pickup at `pos` of the string: a feed-forward comb."""
    d = max(1, int(pos * rate / f0))
    return x - 0.85 * np.concatenate([np.zeros(d), x[:-d]])


# ---------------------------------------------------------------------------
#   non-linear: tube-style waveshaping with oversampling
# ---------------------------------------------------------------------------

def tube(x, gain, bias=0.15, stages=2, oversample=4):
    """Asymmetric soft clipping in `stages` cascaded stages, run at `oversample` times the rate
    so the harmonics above Nyquist do not fold back as noise."""
    u = signal.resample_poly(x, oversample, 1, axis=0)
    for s in range(stages):
        g = gain if s == 0 else 2.5
        u = np.tanh(g * u + bias) - np.tanh(bias)
        # the coupling capacitor between stages blocks the offset of the bias
        u = signal.lfilter([1, -1], [1, -0.9995], u, axis=0)
    return signal.resample_poly(u, 1, oversample, axis=0)


def cabinet(x):
    """A closed 4x12 cabinet with a dynamic microphone: tight lows, a bump at 110 Hz, scooped
    low mids, presence at 2.5 kHz and a steep roll-off above 5 kHz."""
    y = hp(x, 70, 2)
    y = eq(y, [("peak", 120, 1.0, 6.0), ("peak", 450, 0.9, -4.5), ("peak", 2400, 1.2, 3.5),
               ("notch", 6800, 2.0, 0)])
    return lp(y, 5200, 6)


# ---------------------------------------------------------------------------
#   space: chorus, reverb, stereo
# ---------------------------------------------------------------------------

def delay_mod(x, base_ms, depth_ms, rate_hz, phase=0.0, rate=RATE):
    """Mono x through a delay of base +- depth ms modulated by a sine; linear interpolation."""
    n = len(x)
    t = np.arange(n)
    d = (base_ms + depth_ms * np.sin(2 * np.pi * rate_hz * t / rate + phase)) * rate / 1000
    return np.interp(t - d, t, x, left=0.0)


def chorus(x, mix=0.5, depth_ms=2.5, rate_hz=0.8, rate=RATE):
    """Mono -> stereo chorus: two modulated copies in opposite phase on each side."""
    a = delay_mod(x, 14, depth_ms, rate_hz, 0.0, rate)
    b = delay_mod(x, 19, depth_ms, rate_hz * 1.13, np.pi, rate)
    left = x + mix * (a - 0.4 * b)
    right = x + mix * (b - 0.4 * a)
    return np.stack([left, right], axis=1)


def reverb_ir(length, rt_low, rt_high, pre_ms=12, early=8, seed=3, rate=RATE):
    """Stereo impulse response: sparse early reflections, then decorrelated noise decaying
    faster in the highs (rt_high) than in the lows (rt_low)."""
    r = rng(seed)
    n = int(length * rate)
    t = np.arange(n) / rate
    ir = np.zeros((n, 2))
    for ch in range(2):
        noise = r.standard_normal(n)
        low = lp(noise, 900, 2)
        high = noise - low
        env_lo = 10 ** (-3 * t / rt_low)
        env_hi = 10 ** (-3 * t / rt_high)
        tail = low * env_lo + high * env_hi
        fade = np.clip(t / 0.03, 0, 1)        # the tail builds up after the early reflections
        ir[:, ch] = tail * fade * 0.6
        for k in range(early):
            at = int((pre_ms + r.uniform(0, 40)) * rate / 1000)
            if at < n:
                ir[at, ch] += r.uniform(0.3, 0.9) * (1 if r.random() > 0.3 else -1) * (1 - k / early)
    pre = int(pre_ms * rate / 1000)
    ir[:pre] *= 0
    return ir / np.sqrt((ir ** 2).sum(axis=0).mean())


def reverb(x, ir, wet, dry=1.0):
    """x mono or stereo; returns stereo, longer by the IR."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    n = len(x) + len(ir) - 1
    out = np.zeros((n, 2))
    for ch in range(2):
        out[:, ch] = signal.fftconvolve(x[:, ch], ir[:, ch])
    out *= wet
    out[:len(x)] += dry * x
    return out


def pan(x, p):
    """Mono x to stereo at p in -1..1 (constant power)."""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def width(x, amount):
    """Stereo: scale the side signal."""
    m = (x[:, 0] + x[:, 1]) / 2
    s = (x[:, 0] - x[:, 1]) / 2 * amount
    return np.stack([m + s, m - s], axis=1)


def fit(x, n):
    """Pads or cuts x (first axis) to n samples."""
    if len(x) >= n:
        return x[:n]
    pad = np.zeros((n - len(x),) + x.shape[1:])
    return np.concatenate([x, pad])


def fade_out(x, sec, rate=RATE):
    n = min(len(x), int(sec * rate))
    w = np.ones(len(x))
    w[len(x) - n:] = np.cos(np.linspace(0, np.pi / 2, n)) ** 2
    return x * (w[:, None] if x.ndim == 2 else w)


def fade_in(x, sec, rate=RATE):
    n = min(len(x), max(1, int(sec * rate)))
    w = np.ones(len(x))
    w[:n] = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
    return x * (w[:, None] if x.ndim == 2 else w)


def loop_crossfade(x, loop_start, loop_end, xfade):
    """Blends the samples before loop_end with those before loop_start (equal power), so playing
    on from loop_end back to loop_start is continuous. Returns x cut after loop_end."""
    x = x[:loop_end + 1].copy()
    xfade = min(xfade, loop_start, loop_end - loop_start)
    w = np.sin(np.linspace(0, np.pi / 2, xfade)) ** 2
    if x.ndim == 2:
        w = w[:, None]
    a = x[loop_end + 1 - xfade:loop_end + 1]
    b = x[loop_start - xfade:loop_start]
    # equal power for uncorrelated material, equal gain where the two are alike
    x[loop_end + 1 - xfade:loop_end + 1] = a * np.sqrt(1 - w) + b * np.sqrt(w)
    return x


# ---------------------------------------------------------------------------
#   output
# ---------------------------------------------------------------------------

def write_wav(path, x, rate=RATE):
    """Stereo (or mono, duplicated) float in -1..1 -> 16-bit stereo WAV."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype="<i2").reshape(-1, w.getnchannels())
    return data
