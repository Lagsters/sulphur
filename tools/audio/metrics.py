"""Measurements of rendered audio (int16 or float stereo at 44.1 kHz), standing in for ears."""
import numpy as np
from scipy import signal

import dsp

RATE = 44100


def as_float(x):
    x = np.asarray(x)
    return x.astype(np.float64) / 32768.0 if x.dtype.kind == "i" else x.astype(np.float64)


def lufs(x):
    """Integrated loudness after ITU-R BS.1770 (K-weighting, 400 ms blocks, gates at -70 LUFS
    and -10 LU); the K filter is the RBJ approximation at 44.1 kHz, so 'approximate LUFS'."""
    x = as_float(x)
    k = dsp.eq(x, [("highshelf", 1681.97, 0.7072, 4.0), ("hp", 38.135, 0.5003, 0.0)])
    block, hop = int(0.4 * RATE), int(0.1 * RATE)
    if len(k) < block:
        return -99.0
    ms = np.array([(k[i:i + block] ** 2).mean(axis=0).sum() for i in range(0, len(k) - block + 1, hop)])
    lk = -0.691 + 10 * np.log10(ms + 1e-12)
    gated = ms[lk > -70]
    if len(gated) == 0:
        return -99.0
    rel = -0.691 + 10 * np.log10(gated.mean()) - 10
    gated = ms[(lk > -70) & (lk > rel)]
    return float(-0.691 + 10 * np.log10(gated.mean()))


def true_peak_db(x):
    x = as_float(x)
    up = signal.resample_poly(x, 4, 1, axis=0)
    return float(20 * np.log10(np.abs(up).max() + 1e-12))


def band_share(x, lo=60, hi=250):
    """Share of the mid signal's power between lo and hi Hz (of 20 Hz-20 kHz)."""
    m = as_float(x).mean(axis=1)
    f, p = signal.welch(m, RATE, nperseg=8192)
    band = p[(f >= lo) & (f < hi)].sum()
    total = p[(f >= 20) & (f < 20000)].sum()
    return float(band / (total + 1e-20))


def width(x):
    """Side-to-mid RMS ratio: 0 is mono."""
    x = as_float(x)
    m = (x[:, 0] + x[:, 1]) / 2
    s = (x[:, 0] - x[:, 1]) / 2
    return float(np.sqrt((s ** 2).mean()) / (np.sqrt((m ** 2).mean()) + 1e-12))


def centroid_track(x, win=1.0):
    """Spectral centroid (Hz) of each `win`-second window of the mid signal."""
    m = as_float(x).mean(axis=1)
    n = int(win * RATE)
    out = []
    freqs = np.fft.rfftfreq(n, 1 / RATE)
    for i in range(0, len(m) - n + 1, n):
        spec = np.abs(np.fft.rfft(m[i:i + n] * np.hanning(n)))
        if spec.sum() > 1e-9:
            out.append(float((freqs * spec).sum() / spec.sum()))
    return out


def short_rms_db(m, at, span):
    seg = m[max(0, at):at + span]
    return 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)


def seam(x, seam_sample, bar_samples, first_bar_sample=0):
    """Level change (dB, 200 ms before vs after) at the loop seam, against the median of the
    same change at every bar line of the song: a seam no worse than a bar line is seamless."""
    m = as_float(x).mean(axis=1)
    span = int(0.2 * RATE)

    def jump(at):
        return abs(short_rms_db(m, at, span) - short_rms_db(m, at - span, span))

    bars = [jump(int(b)) for b in np.arange(first_bar_sample + bar_samples, seam_sample - span, bar_samples)]
    # the largest sample-to-sample step near the seam against the whole render
    d = np.abs(np.diff(m))
    near = d[seam_sample - 64:seam_sample + 64].max()
    return dict(seam_db=float(jump(seam_sample)), bar_median_db=float(np.median(bars)),
                bar_p90_db=float(np.percentile(bars, 90)),
                seam_step=float(near), p999_step=float(np.percentile(d, 99.9)))
