"""The composer's toolkit: a song is a grid of 16th-note steps (a whole number of frames each)
on 12 voices, filled by helpers for drums, bass, guitars, arpeggios, pads and melodies.

The result is a list of note events per voice, exactly what the C sequencer (src/sound.h) plays:
start frame, duration in frames, sample, semitone offset, velocity, envelope, vibrato, bend.
"""
import re

import numpy as np

VOICES = 12
KICK, SNARE, HAT, BASS, GTR, LEAD, ECHO, ARP1, ARP2, PAD1, PAD2, X = range(12)

# envelope presets: (start level, k per frame toward sustain, sustain, release factor per frame)
ENVELOPES = [
    ("hit", 1.0, 0.0, 1.0, 0.5),       # one-shots: flat, quick release at the note's end
    ("pluck", 1.0, 0.0, 1.0, 0.62),
    ("gtr", 1.0, 0.985, 0.62, 0.5),    # power chords sag a little while held
    ("lead", 1.0, 0.99, 0.8, 0.72),
    ("pad", 0.0, 0.93, 1.0, 0.95),     # swells in over ~0.3 s, long release
    ("slowpad", 0.0, 0.975, 1.0, 0.965),
    ("bow", 0.35, 0.85, 1.0, 0.8),
    ("flute", 0.45, 0.8, 1.0, 0.75),
    ("drone", 0.0, 0.96, 1.0, 0.96),
    ("stac", 1.0, 0.0, 1.0, 0.3),
    ("ring", 1.0, 0.0, 1.0, 0.9),      # bells, cymbals: let them ring out
    ("bass", 1.0, 0.0, 1.0, 0.45),
    ("fall", 1.0, 0.95, 0.0, 0.5),     # fades while held: swells' ends, dying notes
    ("swell", 0.05, 0.96, 1.0, 0.6),
]
ENV = {e[0]: i for i, e in enumerate(ENVELOPES)}
VIBRATO_DEPTH = [0.0, 0.004, 0.008, 0.014]
BEND_START = [1.0, 2 ** (-1 / 12), 2 ** (-2 / 12), 2 ** (-0.5 / 12)]

NOTE_RE = re.compile(r"^([A-G])([#b]?)(-?\d)$")
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    m = NOTE_RE.match(name)
    if not m:
        raise ValueError(name)
    n = PC[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return n + 12 * (int(m.group(3)) + 1)


CHORD_RE = re.compile(r"^([A-G][#b]?)(m7|maj7|m|7|dim|sus4|sus2|5|add9)?$")
CHORD_SHAPES = {None: [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10],
                "maj7": [0, 4, 7, 11], "dim": [0, 3, 6], "sus4": [0, 5, 7], "sus2": [0, 2, 7],
                "5": [0, 7], "add9": [0, 4, 7, 14]}


def chord(sym):
    """'Em' -> (root pitch class, intervals)."""
    m = CHORD_RE.match(sym)
    if not m:
        raise ValueError(sym)
    root = m.group(1)
    pc = (PC[root[0]] + {"#": 1, "b": -1}.get(root[1:], 0)) % 12
    return pc, CHORD_SHAPES[m.group(2)]


def in_range(pc, lo):
    """The MIDI note of pitch class pc at or above lo, within an octave."""
    return lo + (pc - lo) % 12


class Bank:
    """Maps (instrument, MIDI note) to (global sample index, semitone offset)."""

    def __init__(self, instruments):
        self.map = {}
        self.loudness = {}
        index = 0
        rms = {}
        for ins in instruments:
            self.map[ins.name] = [(index + k, s.root) for k, s in enumerate(ins.samples)]
            index += len(ins.samples)
            mid = ins.samples[len(ins.samples) // 2]
            head = mid.audio[:int(0.3 * mid.rate)]
            rms[ins.name] = float(np.sqrt((head ** 2).mean()))
        self.count = index
        # velocities mean loudness: a dense instrument (distorted guitar) gets its velocities
        # scaled down against a sparse one (a bell) so that 100 sounds alike on both
        ref = float(np.median(list(rms.values())))
        for name, r in rms.items():
            self.loudness[name] = float(np.clip(ref / r, 0.2, 1.6))

    def pick(self, name, note):
        options = self.map[name]
        if len(options) == 1 and options[0][1] == 0:
            return options[0][0], 0
        best = min(options, key=lambda o: (abs(note - o[1]), -o[1]))
        semi = note - best[1]
        assert -24 <= semi <= 24, (name, note)
        return best[0], semi


class Song:
    def __init__(self, bank, name, step, bars, loop_bar=0, steps_per_bar=16):
        self.bank, self.name, self.step = bank, name, step
        self.bars, self.loop_bar, self.spb = bars, loop_bar, steps_per_bar
        self.voices = [dict() for _ in range(VOICES)]      # start frame -> event

    @property
    def length(self):
        return self.bars * self.spb * self.step

    @property
    def loop_frame(self):
        return self.loop_bar * self.spb * self.step

    def frame(self, bar, s=0):
        return int(round((bar * self.spb + s) * self.step))

    @property
    def rows(self):
        return self.bars * self.spb

    def note(self, v, bar, s, dur, ins, note, vel=100, env=None, vib=0, bend=0):
        """A note on voice v at a bar and step, dur steps long (a step is a tracker row).
        The instrument's envelope shapes it (env names the envelope the composer meant; the
        tracker has one per instrument). vel 0..127 is scaled by the instrument's loudness."""
        row = bar * self.spb + s
        if row >= self.rows:
            row -= self.rows - self.loop_bar * self.spb
        vel = int(max(1, min(127, round(vel * self.bank.loudness[ins]))))
        self.voices[v][row] = (row, ins, note, vel, max(1, int(dur)), vib, bend)

    # ------------------------------------------------------------------ drums
    def drums(self, bar0, bars, pattern, vel=1.0, crash_voice=X):
        """pattern: dict with any of 'k' (kick: x, X accent, o soft), 's' (snare: s, S accent,
        g ghost, t/m/l toms), 'h' (hats: x, o soft, O open), 'c' (crash: x); a line of 16 steps
        a bar, several bars long patterns cycle."""
        for key, line in pattern.items():
            line = line.replace(" ", "")
            nb = max(1, len(line) // self.spb)
            for b in range(bars):
                seg = line[(b % nb) * self.spb:(b % nb + 1) * self.spb]
                for s, ch in enumerate(seg):
                    if ch in ".-":
                        continue
                    bb = bar0 + b
                    if key == "k":
                        self.note(KICK, bb, s, 40, "kick", 60, {"x": 116, "X": 127, "o": 88}[ch] * vel)
                    elif key == "s" and ch in "tml":
                        self.note(SNARE, bb, s, 50, "tom", {"t": 50, "m": 45, "l": 40}[ch], 112 * vel)
                    elif key == "s":
                        self.note(SNARE, bb, s, 50, "snare", 60, {"s": 106, "S": 125, "g": 46}[ch] * vel)
                    elif key == "h" and ch == "O":
                        self.note(HAT, bb, s, 30, "ohat", 60, 80 * vel, env="ring")
                    elif key == "h":
                        self.note(HAT, bb, s, 10, "hat", 60, {"x": 90, "o": 56}[ch] * vel)
                    elif key == "c":
                        self.note(crash_voice, bb, s, 110, "crash", 60, 102 * vel, env="ring")

    # ------------------------------------------------------------------ bass and guitars
    def _rhythm(self, bar0, chords, rhythm, fn):
        """Runs fn(bar, step, dur, chord) over a 16-char rhythm per bar, '-' holding the note
        and '.' resting; chords one per bar ('Em') or two ('Em C')."""
        for k, ch in enumerate(chords):
            parts = ch.split()
            line = rhythm[k % len(rhythm)] if isinstance(rhythm, list) else rhythm
            line = line.replace(" ", "")
            b = bar0 + k
            i = 0
            while i < len(line):
                c = line[i]
                if c in "-.":
                    i += 1
                    continue
                j = i + 1
                while j < len(line) and line[j] == "-":
                    j += 1
                part = parts[min(len(parts) - 1, i * len(parts) // len(line))]
                fn(b, i, j - i, part, c)
                i = j

    def bass(self, bar0, chords, rhythm, vel=104, lo=40):
        def fn(b, s, d, sym, c):
            pc, shape = chord(sym)
            root = in_range(pc, lo)
            n = {"x": root, "o": root + 12, "5": root + 7, "3": root + shape[1], "4": root + 5,
                 "7": root + 10, "b": root - 1, "w": root - 2, "X": root}[c]
            while n < 40:
                n += 12
            v = vel * (1.12 if c == "X" else 1.0)
            self.note(BASS, b, s, d, "bass", n, v, env="bass")
        self._rhythm(bar0, chords, rhythm, fn)

    def power(self, bar0, chords, rhythm, vel=100, lo=40):
        """'X' open power chord, 'M' palm-muted, 'x' open but softer."""
        def fn(b, s, d, sym, c):
            pc, _ = chord(sym)
            root = in_range(pc, lo)
            if c == "M":
                self.note(GTR, b, s, d, "mute", root, vel * 0.95, env="stac")
            else:
                self.note(GTR, b, s, d, "pwr", root, vel * (1.0 if c == "X" else 0.8), env="gtr")
        self._rhythm(bar0, chords, rhythm, fn)

    def arp(self, bar0, chords, pattern, vel=84, lo=52, ins="clean", voices=(ARP1, ARP2), env="pluck", ring=8):
        """Digits index the chord's notes stacked upward from lo (0 root, 1 third, 2 fifth,
        3 octave...); notes alternate between two voices so each one rings on."""
        state = {"k": 0}

        def tones(sym):
            pc, shape = chord(sym)
            root = in_range(pc, lo)
            out = []
            octave = 0
            while len(out) < 8:
                for iv in shape:
                    if iv >= 12:
                        continue
                    out.append(root + iv + octave)
                octave += 12
            return out

        for k, ch in enumerate(chords):
            parts = ch.split()
            line = (pattern[k % len(pattern)] if isinstance(pattern, list) else pattern).replace(" ", "")
            for i, c in enumerate(line):
                if not c.isdigit():
                    continue
                part = parts[min(len(parts) - 1, i * len(parts) // len(line))]
                n = tones(part)[int(c)]
                v = voices[state["k"] % len(voices)]
                state["k"] += 1
                self.note(v, bar0 + k, i, ring, ins, n, vel, env=env)

    def pad(self, bar0, chords, vel=70, lo=55, ins="strings", voices=(PAD1, PAD2), env="pad", picks=(1, 2)):
        """Holds chord tones on the pad voices; a chord repeated in the next bar keeps
        sounding instead of starting again."""
        k = 0
        while k < len(chords):
            sym = chords[k]
            j = k + 1
            while j < len(chords) and chords[j] == sym:
                j += 1
            pc, shape = chord(sym)
            root = in_range(pc, lo)
            notes = [root + shape[p % len(shape)] + 12 * (p // len(shape)) for p in picks]
            for v, n in zip(voices, notes):
                self.note(v, bar0 + k, 0, (j - k) * self.spb, ins, n, vel, env=env)
            k = j

    # ------------------------------------------------------------------ melodies
    def melody(self, v, bar0, text, ins, vel=100, env=None, vib=2, transpose=0, s0=0):
        """Tokens 'D5:4' (note and length in steps; the length carries over), '-:4' rest.
        Suffixes: 'v' vibrato, 'n' no vibrato, 'b' bend up a semitone, 'B' two, 's' scoop,
        '>' accent, '<' soft."""
        pos = bar0 * self.spb + s0
        dur = 4
        for tok in text.split():
            m = re.match(r"^([A-G][#b]?-?\d|-)(?::(\d+))?([vnbBs<>]*)$", tok)
            if not m:
                raise ValueError(f"{self.name}: bad token {tok}")
            if m.group(2):
                dur = int(m.group(2))
            if m.group(1) != "-":
                flags = m.group(3)
                bend = 1 if "b" in flags else 2 if "B" in flags else 3 if "s" in flags else 0
                vb = 0 if "n" in flags else (vib if dur >= 4 or "v" in flags else 0)
                vv = vel * (1.15 if ">" in flags else 0.75 if "<" in flags else 1.0)
                n = midi(m.group(1)) + transpose
                self.note(v, pos // self.spb, pos % self.spb, dur, ins, n, vv, env=env, vib=vb, bend=bend)
            pos += dur
        return pos

    def improv(self, v, bar0, chords, scale_pcs, seed, ins="lead", lo=62, hi=81, vel=100, rhythm=None):
        """A seeded improvised line: chord tones on strong steps, scale steps between, phrases
        of 2 bars with a held note at the end."""
        r = np.random.default_rng(seed)
        rhythms = rhythm or ["4 2 2 4 4", "2 2 2 2 4 4", "3 3 2 4 4", "4 4 2 2 4", "8 4 4"]
        cur = lo + (hi - lo) // 2
        for k, sym in enumerate(chords):
            pc, shape = chord(sym)
            ct = [(pc + i) % 12 for i in shape]
            rh = [int(x) for x in rhythms[r.integers(len(rhythms))].split()]
            if k % 2 == 1:
                rh = rh[:-2] + [rh[-2] + rh[-1]] if len(rh) > 2 else rh
            s = 0
            for i, d in enumerate(rh):
                pool = ct if (s % 4 == 0) else scale_pcs
                cands = [n for n in range(lo, hi + 1) if n % 12 in pool]
                cands.sort(key=lambda n: abs(n - cur) + r.uniform(0, 3.5))
                n = cands[0] if r.random() < 0.7 else cands[min(1, len(cands) - 1)]
                bend = 1 if (d >= 4 and r.random() < 0.3) else 0
                self.note(v, bar0 + k, s, d, ins, n, vel * (1.08 if s == 0 else 0.95), vib=2 if d >= 4 else 0, bend=bend)
                cur = n
                s += d

    # ------------------------------------------------------------------ echo and output
    def echo(self, src, dst, delay_steps, gain=0.45, repeats=1):
        """Delayed, quieter copies of the src voice's notes on the dst voice."""
        for r in range(1, repeats + 1):
            for row, e in sorted(self.voices[src].items()):
                t = row + delay_steps * r
                if t >= self.rows:
                    t -= self.rows - self.loop_bar * self.spb
                if t in self.voices[dst]:
                    continue
                self.voices[dst][t] = (t,) + e[1:3] + (max(1, int(e[3] * gain ** r)),) + e[4:]

    def events(self, v):
        return [self.voices[v][k] for k in sorted(self.voices[v])]


DEFAULT_ENV = {"kick": "hit", "snare": "hit", "hat": "hit", "ohat": "ring", "crash": "ring",
               "tom": "hit", "bass": "bass", "pwr": "gtr", "mute": "stac", "lead": "lead",
               "clean": "pluck", "strings": "pad", "fiddle": "bow", "flute": "flute",
               "drone": "drone", "bell": "ring", "trumpet": "bow"}
