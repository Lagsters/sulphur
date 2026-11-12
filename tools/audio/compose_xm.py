"""Writes the composer's songs (songs.py) and the synthesized instruments (instruments.py) as one
FastTracker 2 module, assets/music/songs/sulphur.xm: the songs' source of truth from then on,
to open and edit in OpenMPT. xm2vircon.py reads it back for the console.

Layout: 16 channels; 1-12 are the voices (compose.py: kick, snare/toms, hats, bass, rhythm
guitar, lead, lead echo, two arpeggio voices, two pad voices, extra), 13-16 steer: the first row
of a song sets its speed (13: F0x), tempo (14: F96, one tick a frame) and volume (15: Gxx); its
last row jumps back to its loop point (13: Bxx). One tracker row is a 16th note.
"""
import math

import numpy as np

import compose
import xmfile
from compose import DEFAULT_ENV, ENVELOPES, ENV

CHANNELS = 16
VIB_DEPTH = {1: 1, 2: 2, 3: 4}     # compose.py vibrato levels -> 4xy depth
VIB_SPEED = 6                      # 4xy speed: 6/64 of a cycle a tick, 5.6 Hz


def envelope_points(name):
    """An XM volume envelope from a compose.py envelope preset (start level, per-tick factor
    toward the sustain level, sustain level, release factor per tick after key-off)."""
    _, start, k, sus, rel = ENVELOPES[ENV[name]]
    pts = [(0, start)]
    if abs(start - sus) * 64 >= 0.5:
        if k == 0:
            pts.append((1, sus))
        else:
            for t in (1, 3, 6, 10, 16, 25, 40, 60, 90, 130):
                v = sus + (start - sus) * k ** t
                if abs(v - sus) * 64 < 0.5:
                    pts.append((t, sus))
                    break
                pts.append((t, v))
            else:
                pts.append((pts[-1][0] + 40, sus))
    sustain = len(pts) - 1
    t0 = pts[-1][0]
    for d in (1, 2, 4, 7, 12, 20, 32, 50, 80, 120, 180):
        if len(pts) >= 11:
            break
        v = sus * rel ** d
        if v * 64 < 0.5:
            break
        pts.append((t0 + d, v))
    pts.append((pts[-1][0] + (1 if rel < 0.7 else 8), 0.0))
    return [(t, int(round(v * 64))) for t, v in pts], sustain


def xm_sample(s):
    pcm = np.clip(np.round(s.audio * 32767), -32768, 32767).astype(np.int16)
    # play at the sample's own rate (times its tuning) at its root note
    x = 12 * math.log2(s.rate * s.tune / 8363.0) + 60 - s.root
    rel = int(round(x))
    ft = int(round((x - rel) * 128))
    loop_start, loop_len = (s.loop[0], s.loop[1] - s.loop[0] + 1) if s.loop else (0, 0)
    return xmfile.XMSample(s.name, pcm, loop_start, loop_len, 64, ft, rel)


def xm_instrument(ins):
    roots = [s.root for s in ins.samples]
    keymap = []
    for i in range(96):
        m = i + 12
        keymap.append(min(range(len(roots)), key=lambda k: (abs(m - roots[k]), -roots[k])))
    env, sus = envelope_points(DEFAULT_ENV.get(ins.name, "hit"))
    return xmfile.XMInstrument(ins.name, [xm_sample(s) for s in ins.samples], keymap, env, sus)


def song_rows(song, ins_index, volume):
    """The song as rows x CHANNELS cells (note, instrument, volume, effect, parameter)."""
    rows = song.rows
    grid = [[[0, 0, 0, 0, 0] for _ in range(CHANNELS)] for _ in range(rows)]
    vib_from = max(1, math.ceil(10 / song.step))
    for v in range(compose.VOICES):
        events = song.events(v)
        starts = [e[0] for e in events]
        for k, (r, ins, midi, vel, dur, vib, bend) in enumerate(events):
            nxt = starts[k + 1] if k + 1 < len(starts) else rows
            end = min(r + dur, nxt, rows)
            ino = ins_index[ins] + 1
            vol = 0x10 + max(1, min(64, round(vel * 64 / 127)))
            first = midi
            body = r + 1
            if bend and end - r >= 3:
                first = midi - (2 if bend == 2 else 1)
                body = r + 2
            grid[r][v] = [first - 11, ino, vol, 0, 0]
            if first != midi:
                grid[r + 1][v] = [midi - 11, 0, 0, 0x03, 0x04]
            if vib:
                for rr in range(max(body, r + vib_from), end):
                    grid[rr][v] = [0, 0, 0, 0x04, (VIB_SPEED << 4) | VIB_DEPTH[vib]]
            if r + dur < nxt and r + dur < rows:
                grid[r + dur][v][0] = xmfile.NOTE_OFF
    grid[0][12][3:] = [0x0F, song.step]
    grid[0][13][3:] = [0x0F, 150]
    grid[0][14][3:] = [0x10, volume]
    return grid


def build(inst, song_list, volumes):
    instruments = [xm_instrument(i) for i in inst]
    ins_index = {i.name: k for k, i in enumerate(inst)}
    patterns, orders = [], []
    for song, vol in zip(song_list, volumes):
        grid = song_rows(song, ins_index, vol)
        loop_row = song.loop_bar * song.spb
        cuts = sorted(set(list(range(0, song.rows, 64)) + [loop_row, song.rows]))
        first_order = len(orders)
        loop_order = None
        for a, b in zip(cuts, cuts[1:]):
            if a == loop_row:
                loop_order = len(orders)
            orders.append(len(patterns))
            patterns.append([[tuple(c) for c in row] for row in grid[a:b]])
        last = list(patterns[-1][-1])
        last[12] = tuple(last[12][:3]) + (0x0B, loop_order if loop_order is not None else first_order)
        patterns[-1][-1] = last
    assert len(patterns) <= 256 and len(orders) <= 256
    return xmfile.XMModule("Sulphur", CHANNELS, orders, patterns, instruments, speed=6, tempo=150)
