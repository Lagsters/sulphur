"""The music's instruments, synthesized offline: every sample is a short recording of one note
(or a power chord) at one pitch, with its stereo picture and room baked in.

The console plays a sample at another pitch by changing the channel's speed, without
interpolation, so each instrument has a sample every few semitones and the composer picks the
nearest. Low, dark instruments (bass, strings) are stored at half the rate and played at half
speed: half the bytes for sounds that have nothing above 11 kHz anyway.
"""
from dataclasses import dataclass

import numpy as np

import dsp
from dsp import RATE


@dataclass
class Sample:
    name: str
    audio: np.ndarray          # (n, 2) float, at `rate`
    root: int                  # MIDI note it sounds at when played at its own rate
    rate: int = RATE           # stored at 44100 or 22050 (played at speed 0.5)
    loop: tuple = None         # (start, end) in samples, or None for a one-shot
    tune: float = 1.0          # speed correction measured from the rendered pitch


@dataclass
class Instrument:
    name: str
    samples: list
    level: float = 1.0         # how loud it is in the mix, relative to the others


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def cents_to_ratio(c):
    return 2 ** (c / 1200)


ROOM = dsp.reverb_ir(0.6, 0.45, 0.25, pre_ms=6, seed=11)
PLATE = dsp.reverb_ir(1.8, 1.6, 0.9, pre_ms=10, seed=12)
HALL = dsp.reverb_ir(3.0, 2.6, 1.4, pre_ms=22, seed=13)
HALL_HALF = dsp.reverb_ir(3.0, 2.6, 1.4, pre_ms=22, seed=14, rate=RATE // 2)


def make_loop(x, start_s, end_s, xfade_s, rate=RATE):
    ls, le = int(start_s * rate), int(end_s * rate)
    y = dsp.loop_crossfade(x, ls, le, int(xfade_s * rate))
    return y, (ls, le)


# ---------------------------------------------------------------------------
#   guitars
# ---------------------------------------------------------------------------

def _string(f, dur, seed, t60, bright, pick=0.12, softness=0.15, pickup=0.1):
    loss = 10 ** (-3 / (t60 * f))
    exc = dsp.pluck_excitation(f, seed, pick, softness)
    y = dsp.ks_string(f, dur, exc, loss, bright)
    return dsp.comb_pickup(y, f, pickup)


def _power_take(root, dur, muted, seed, detune_c, strum_ms):
    notes = [root, root + 7, root + 12]
    n = int(dur * RATE)
    x = np.zeros(n)
    for k, m in enumerate(notes):
        f = hz(m) * cents_to_ratio(detune_c + (k - 1) * 1.5)
        if muted:
            s = _string(f, dur, seed + k, 0.22, 0.25, softness=0.35)
        else:
            s = _string(f, dur, seed + k, 3.5, 0.62)
        at = int(k * strum_ms * RATE / 1000)
        x[at:] += s[:n - at] * (1.0 if k == 0 else 0.85)
    x /= np.abs(x).max()
    # the pedal before the amp: tight lows, a mid hump
    x = dsp.eq(x, [("hp", 75, 0.7, 0), ("peak", 720, 0.8, 4.0)])
    y = dsp.tube(x * 0.7, 28.0 if not muted else 22.0, bias=0.22)
    y = dsp.cabinet(y)
    if muted:
        t = np.arange(n) / RATE
        y *= np.exp(-t / 0.14) * 0.85 + 0.15 * np.exp(-t / 0.05)
    return y


def power_chord(root, muted, seed):
    dur = 0.36 if muted else 1.75
    a = _power_take(root, dur, muted, seed, +4, 7)
    b = _power_take(root, dur, muted, seed + 50, -4, 9)
    d = int(0.011 * RATE)
    b = np.concatenate([np.zeros(d), b[:-d]])
    # double-tracked: one take on each side, a little of each bleeding into the other
    st = np.stack([a + 0.12 * b, b + 0.12 * a], axis=1)
    st = dsp.reverb(st, ROOM, 0.10)[:len(st)]
    if muted:
        return dsp.fade_out(st, 0.05), None
    return make_loop(st, 0.95, 1.7, 0.3)


def lead_guitar(m, seed):
    dur = 1.35
    f = hz(m)
    x = _string(f, dur, seed, 9.0, 0.75, pick=0.2, softness=0.25, pickup=0.22)
    x /= np.abs(x).max()
    x = dsp.eq(x, [("hp", 160, 0.7, 0), ("peak", 900, 0.7, 6.0)])
    y = dsp.tube(x * 0.8, 70.0, bias=0.25, stages=2)
    y = dsp.cabinet(y)
    y = dsp.eq(y, [("peak", 800, 0.8, 3.0)])
    # a slight doubling for width, then a plate
    st = dsp.chorus(y, mix=0.22, depth_ms=1.2, rate_hz=0.6)
    st = dsp.reverb(st, PLATE, 0.18)[:len(y)]
    return make_loop(st, 0.6, 1.3, 0.3)


def clean_guitar(m, seed):
    dur = 1.3
    f = hz(m)
    t60 = 3.2 if m < 55 else 2.2
    x = _string(f, dur, seed, t60, 0.82, pick=0.16, softness=0.1, pickup=0.18)
    x /= np.abs(x).max()
    x = np.tanh(1.6 * x) / np.tanh(1.6)
    x = dsp.eq(x, [("hp", 80, 0.7, 0), ("peak", 140, 1.0, 2.5), ("peak", 2800, 1.0, 2.0),
                   ("highshelf", 7000, 0.7, -4.0)])
    st = dsp.chorus(x, mix=0.55, depth_ms=2.8, rate_hz=0.9)
    st = dsp.reverb(st, PLATE, 0.28)[:len(x)]
    return dsp.fade_out(st, 0.35), None


def bass_guitar(m, seed):
    """Fingered bass: a weak fundamental under strong 2nd-4th harmonics (the Jaguar XJ220
    reference), upper harmonics fading faster, a ~300 ms pluck over a longer tail."""
    rate = RATE // 2
    dur = 1.6
    r = dsp.rng(seed)
    t = np.arange(int(dur * rate)) / rate
    f = hz(m)
    amps = [0.45, 1.0, 0.85, 0.62, 0.36, 0.24, 0.15, 0.1, 0.07, 0.05, 0.035, 0.025]
    x = np.zeros_like(t)
    for k, a in enumerate(amps, start=1):
        fk = k * f * np.sqrt(1 + 0.00025 * k * k)
        if fk > 5000:
            break
        tau_fast = 0.30 / (1 + 0.25 * (k - 1))
        tau_slow = 1.3 / (1 + 0.45 * (k - 1))
        env = 0.62 * np.exp(-t / tau_fast) + 0.38 * np.exp(-t / tau_slow)
        x += a * env * np.sin(2 * np.pi * fk * t + r.uniform(0, 2 * np.pi))
    att = np.clip(t / 0.004, 0, 1)
    x *= att
    thump = dsp.lp(r.standard_normal(len(t)), 900, 2, rate=rate) * np.exp(-t / 0.012) * 0.6
    x += thump
    x /= np.abs(x).max()
    x = np.tanh(1.7 * x) / np.tanh(1.7)
    x = dsp.eq(x, [("hp", 45, 0.7, 0), ("peak", 700, 1.0, 2.0)], rate=rate)
    x = dsp.lp(x, 4200, 2, rate=rate)
    st = np.stack([x, x], axis=1)
    return dsp.fade_out(st, 0.25, rate=rate), None


# ---------------------------------------------------------------------------
#   drums
# ---------------------------------------------------------------------------

def kick(seed):
    r = dsp.rng(seed)
    t = dsp.seconds(0.55)
    f = 56 + 110 * np.exp(-t / 0.028)
    body = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t / 0.2)
    click = dsp.hp(r.standard_normal(len(t)), 2500, 2) * np.exp(-t / 0.004) * 0.45
    beater = np.sin(2 * np.pi * 3200 * t) * np.exp(-t / 0.006) * 0.2
    x = np.tanh(1.8 * (body + click + beater))
    x *= np.clip(t / 0.0008, 0, 1)
    st = dsp.reverb(x, ROOM, 0.07)[:len(x)]
    return dsp.fade_out(st, 0.08), None


def snare(seed):
    r = dsp.rng(seed)
    t = dsp.seconds(0.85)
    body = (np.sin(2 * np.pi * 185 * t) * 0.8 + np.sin(2 * np.pi * 332 * t) * 0.45) * np.exp(-t / 0.075)
    wires = dsp.bp(r.standard_normal(len(t)), 1400, 9500, 2) * (np.exp(-t / 0.16) * 0.9)
    crack = dsp.hp(r.standard_normal(len(t)), 3000, 2) * np.exp(-t / 0.008) * 0.6
    x = np.tanh(1.5 * (body + wires + crack))
    x *= np.clip(t / 0.0006, 0, 1)
    st = dsp.reverb(x, PLATE, 0.32)[:len(x)]
    st = dsp.width(st, 1.4)
    return dsp.fade_out(st, 0.2), None


def _metal(t, seed, base=1.0):
    freqs = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0]) * 1.7 * base
    r = dsp.rng(seed)
    x = sum(np.sign(np.sin(2 * np.pi * fq * t + r.uniform(0, 6.3))) for fq in freqs)
    return x / 6


def hat(seed, open_):
    r = dsp.rng(seed)
    dur = 0.65 if open_ else 0.16
    t = dsp.seconds(dur)
    tau = 0.22 if open_ else 0.03
    m = _metal(t, seed)
    x = dsp.bp(m, 6500, 14000, 2) * 0.7 + dsp.hp(r.standard_normal(len(t)), 8000, 2) * 0.35
    x *= np.exp(-t / tau) * np.clip(t / 0.0005, 0, 1)
    st = dsp.pan(x, 0.25)
    st = dsp.reverb(st, ROOM, 0.12)[:len(t)]
    return dsp.fade_out(st, 0.04), None


def crash(seed):
    r = dsp.rng(seed)
    t = dsp.seconds(1.5)
    chans = []
    for ch in range(2):
        m = _metal(t, seed + ch, 0.8 + 0.07 * ch)
        n = r.standard_normal(len(t))
        x = dsp.hp(m * 0.5 + n * 0.8, 2800, 2)
        x = dsp.eq(x, [("peak", 5000, 0.8, 4.0)])
        x *= (np.exp(-t / 0.65) * 0.85 + np.exp(-t / 0.05) * 0.6) * np.clip(t / 0.001, 0, 1)
        chans.append(x)
    st = np.stack(chans, axis=1)
    st = dsp.reverb(st, PLATE, 0.2)[:len(t)]
    return dsp.fade_out(st, 0.4), None


def tom(seed):
    r = dsp.rng(seed)
    t = dsp.seconds(0.85)
    f0 = 98.0
    f = f0 * (1 + 0.28 * np.exp(-t / 0.05))
    x = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t / 0.32)
    x += np.sin(2 * np.pi * np.cumsum(f * 1.59) / RATE) * np.exp(-t / 0.09) * 0.35
    x += dsp.bp(r.standard_normal(len(t)), 800, 5000, 2) * np.exp(-t / 0.01) * 0.4
    x = np.tanh(1.6 * x)
    st = dsp.reverb(x, PLATE, 0.3)[:len(t)]
    return dsp.fade_out(st, 0.15), None


# ---------------------------------------------------------------------------
#   bowed, blown and struck: strings, fiddle, flute, hurdy-gurdy, bells, trumpet
# ---------------------------------------------------------------------------

def _saw(phase, f_max_hz, f0, rate=RATE, tilt=1.0):
    """Band-limited sawtooth from its harmonics up to f_max_hz."""
    k_max = max(1, int(min(f_max_hz, rate * 0.45) / f0))
    x = np.zeros_like(phase)
    for k in range(1, k_max + 1):
        x += np.sin(k * phase) / k ** tilt
    return x


def strings(m, seed):
    rate = RATE // 2
    dur = 2.3
    r = dsp.rng(seed)
    t = np.arange(int(dur * rate)) / rate
    f = hz(m)
    left = np.zeros_like(t)
    right = np.zeros_like(t)
    for v in range(6):
        det = cents_to_ratio(r.uniform(-9, 9))
        vib = 1 + 0.003 * np.sin(2 * np.pi * r.uniform(4.6, 5.8) * t + r.uniform(0, 6.3))
        ph = 2 * np.pi * np.cumsum(f * det * vib) / rate + r.uniform(0, 6.3)
        s = _saw(ph, 7000, f, rate)
        p = (v / 5) * 2 - 1
        left += s * np.cos((p * 0.8 + 1) * np.pi / 4)
        right += s * np.sin((p * 0.8 + 1) * np.pi / 4)
    st = np.stack([left, right], axis=1)
    st = dsp.eq(st, [("peak", 300, 1.0, 3.0), ("peak", 1100, 1.2, 2.0), ("peak", 2600, 1.4, 1.5)], rate=rate)
    st = dsp.lp(st, 4200, 2, rate=rate)
    st *= np.clip(t / 0.28, 0, 1)[:, None] ** 1.5
    st = dsp.reverb(st, HALL_HALF, 0.32)[:len(t)]
    return make_loop(st, 1.0, 2.25, 0.45, rate=rate)


def fiddle(m, seed):
    dur = 1.15
    r = dsp.rng(seed)
    t = dsp.seconds(dur)
    f = hz(m)
    jitter = 1 + 0.0012 * dsp.lp(r.standard_normal(len(t)), 30, 1) * 8
    ph = 2 * np.pi * np.cumsum(f * jitter) / RATE
    x = _saw(ph, 9000, f, tilt=0.9)
    bow = dsp.bp(r.standard_normal(len(t)), 2000, 8000, 2) * (0.05 + 0.25 * np.exp(-t / 0.05))
    x = x + bow * np.abs(x).max()
    # the body: air and wood resonances, the bridge hill
    x = dsp.eq(x, [("hp", 180, 0.7, 0), ("peak", 280, 4.0, 6.0), ("peak", 460, 3.0, 4.0),
                   ("peak", 1500, 1.5, -4.0), ("peak", 2700, 1.2, 6.0), ("lp", 7500, 0.7, 0)])
    x *= np.clip(t / 0.06, 0, 1)
    st = dsp.reverb(x, ROOM, 0.22)[:len(t)]
    st = dsp.reverb(st, PLATE, 0.1)[:len(t)]
    return make_loop(st, 0.5, 1.1, 0.3)


def flute(m, seed):
    dur = 1.0
    r = dsp.rng(seed)
    t = dsp.seconds(dur)
    f = hz(m)
    ph = 2 * np.pi * f * t
    x = np.sin(ph) + 0.22 * np.sin(2 * ph + 0.4) + 0.07 * np.sin(3 * ph + 1.1) + 0.03 * np.sin(4 * ph)
    breath = r.standard_normal(len(t))
    tone_noise = dsp.resonator(breath, f, 0.02) * 0.6 + dsp.resonator(breath, 2 * f, 0.02) * 0.25
    air = dsp.hp(breath, 3000, 2) * 0.05
    chiff = dsp.bp(breath, 2.5 * f, min(8 * f, 15000), 2) * np.exp(-t / 0.03) * 0.5
    x = x + tone_noise * 0.25 / np.abs(tone_noise).max() * 2 + air + chiff
    x *= np.clip(t / 0.05, 0, 1)
    st = dsp.reverb(x, PLATE, 0.3)[:len(t)]
    return make_loop(st, 0.45, 0.95, 0.3)


def hurdy_gurdy(m, seed):
    dur = 2.2
    r = dsp.rng(seed)
    t = dsp.seconds(dur)
    x = np.zeros_like(t)
    # the wheel turns at 4 Hz: 6 turns in the 1.5 s loop
    wheel = 1 + 0.12 * np.sin(2 * np.pi * 4 * t)
    for k, (dm, a) in enumerate([(0, 1.0), (7, 0.7), (12, 0.45), (-12, 0.5)]):
        f = hz(m + dm) * cents_to_ratio(r.uniform(-3, 3))
        ph = 2 * np.pi * f * t + r.uniform(0, 6.3)
        x += a * _saw(ph, 8000, f, tilt=0.8)
    rasp = dsp.bp(r.standard_normal(len(t)), 1500, 6000, 2) * 0.12
    x = x * wheel + rasp * np.abs(x).max() * wheel
    x = dsp.eq(x, [("hp", 70, 0.7, 0), ("peak", 1200, 2.0, 7.0), ("peak", 2600, 2.0, 5.0),
                   ("peak", 500, 1.0, -3.0), ("lp", 7000, 0.7, 0)])
    x *= np.clip(t / 0.15, 0, 1)
    st = dsp.chorus(x, mix=0.25, depth_ms=1.0, rate_hz=0.5)
    st = dsp.reverb(st, ROOM, 0.2)[:len(t)]
    return make_loop(st, 0.5, 2.0, 0.4)


def bell(m, seed):
    dur = 1.4
    r = dsp.rng(seed)
    t = dsp.seconds(dur)
    f = hz(m)
    ratios = [0.5, 1.0, 1.183, 1.506, 2.0, 2.514, 2.662, 3.011, 4.166, 5.433]
    amps = [0.55, 0.9, 0.65, 0.4, 0.75, 0.35, 0.28, 0.28, 0.18, 0.1]
    decays = [2.6, 1.9, 1.4, 1.2, 1.0, 0.7, 0.6, 0.5, 0.35, 0.25]
    chans = []
    for ch in range(2):
        x = np.zeros_like(t)
        for ra, a, d in zip(ratios, amps, decays):
            fq = f * ra + (ch - 0.5) * 0.6 * ra
            if fq > 16000:
                continue
            x += a * np.exp(-t / d) * np.sin(2 * np.pi * fq * t + r.uniform(0, 6.3))
        chans.append(x)
    st = np.stack(chans, axis=1)
    strike = dsp.hp(r.standard_normal(len(t)), 3000, 2) * np.exp(-t / 0.004) * 0.3
    st += strike[:, None]
    st *= np.clip(t / 0.001, 0, 1)[:, None]
    st = dsp.reverb(st, HALL, 0.25)[:len(t)]
    return dsp.fade_out(st, 0.5), None


def trumpet(m, seed):
    dur = 1.05
    r = dsp.rng(seed)
    t = dsp.seconds(dur)
    f = hz(m)
    fq = f * (1 - 0.03 * np.exp(-t / 0.025))
    ph = 2 * np.pi * np.cumsum(fq) / RATE
    bright = 0.35 + 0.65 * (1 - np.exp(-t / 0.045)) - 0.15 * (1 - np.exp(-t / 0.3))
    x = np.zeros_like(t)
    for k in range(1, 40):
        if k * f > 12000:
            break
        a = np.exp(-(k - 1) / (0.6 + 5.5 * bright))
        x += a * np.sin(k * ph)
    x += dsp.bp(r.standard_normal(len(t)), 1000, 5000, 2) * 0.02
    x = dsp.eq(x, [("hp", 200, 0.7, 0), ("peak", 1250, 1.2, 4.0), ("peak", 2800, 1.5, 2.0), ("lp", 8000, 0.7, 0)])
    x *= np.clip(t / 0.03, 0, 1)
    st = dsp.reverb(x, HALL, 0.3)[:len(t)]
    return make_loop(st, 0.45, 1.0, 0.3)


# ---------------------------------------------------------------------------
#   the set
# ---------------------------------------------------------------------------

def _measure_pitch(audio, rate, expect):
    """Fundamental near `expect` (Hz) from the spectrum of the sample's middle, or None."""
    x = audio.mean(axis=1) if audio.ndim == 2 else audio
    a = int(0.15 * len(x))
    seg = x[a:a + min(len(x) - a, int(0.5 * rate))]
    if len(seg) < rate // 10:
        return None
    n = 1 << 18
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    freqs = np.fft.rfftfreq(n, 1 / rate)
    lo, hi = np.searchsorted(freqs, [expect * 0.95, expect * 1.05])
    k = lo + int(np.argmax(spec[lo:hi]))
    if spec[k] < spec.max() * 0.02:
        return None
    y0, y1, y2 = np.log(spec[k - 1:k + 2] + 1e-12)
    d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    return (k + d) * rate / n


def build():
    """All instruments, in a fixed order (the order of their samples in the ROM)."""
    inst = []

    def add(name, level, specs, fn, measure=True):
        samples = []
        for i, spec in enumerate(specs):
            root, args, rate = spec
            audio, loop = fn(*args)
            s = Sample(f"{name}_{root}" if len(specs) > 1 else name, audio, root, rate, loop)
            if measure:
                got = _measure_pitch(audio, rate, hz(root))
                if got:
                    s.tune = hz(root) / got
            samples.append(s)
        # one gain for the whole instrument keeps its notes even across samples
        peak = max(np.abs(s.audio).max() for s in samples)
        for s in samples:
            s.audio = s.audio * (0.89 / peak)
        inst.append(Instrument(name, samples, level))

    # the distorted chords' fundamentals are too buried for the pitch measure; the string model
    # is in tune by construction (the lead guitar, the same model, measures within 3 cents)
    add("pwr", 1.0, [(r, (r, False, 100 + r), RATE) for r in (40, 44, 48, 52)], power_chord, measure=False)
    add("mute", 1.0, [(r, (r, True, 200 + r), RATE) for r in (40, 44, 48, 52)], power_chord, measure=False)
    add("lead", 1.0, [(r, (r, 300 + r), RATE) for r in (57, 61, 65, 69, 73, 77, 81)], lead_guitar)
    add("clean", 1.0, [(r, (r, 400 + r), RATE) for r in (45, 50, 55, 60, 65, 70)], clean_guitar)
    add("bass", 1.0, [(r, (r, 500 + r), RATE // 2) for r in (40, 44, 48, 52)], bass_guitar)
    add("kick", 1.0, [(60, (1,), RATE)], kick, measure=False)
    add("snare", 1.0, [(60, (2,), RATE)], snare, measure=False)
    add("hat", 1.0, [(60, (3, False), RATE)], hat, measure=False)
    add("ohat", 1.0, [(60, (4, True), RATE)], hat, measure=False)
    add("crash", 1.0, [(60, (5,), RATE)], crash, measure=False)
    add("tom", 1.0, [(43, (6,), RATE)], tom, measure=False)
    add("strings", 1.0, [(r, (r, 600 + r), RATE // 2) for r in (48, 54, 60, 66, 72)], strings)
    add("fiddle", 1.0, [(r, (r, 700 + r), RATE) for r in (55, 60, 65, 70, 75, 80, 85)], fiddle)
    add("flute", 1.0, [(r, (r, 800 + r), RATE) for r in (62, 67, 72, 77, 82)], flute)
    add("drone", 1.0, [(r, (r, 900 + r), RATE) for r in (45, 50)], hurdy_gurdy)
    add("bell", 1.0, [(r, (r, 1000 + r), RATE) for r in (60, 67, 74, 81)], bell, measure=False)
    add("trumpet", 1.0, [(r, (r, 1100 + r), RATE) for r in (60, 65, 70, 75)], trumpet)
    return inst
