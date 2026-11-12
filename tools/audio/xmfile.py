"""FastTracker 2 Extended Module (.xm) files: a small data model with a writer and a reader.

Samples are 16-bit; a stereo sample uses OpenMPT's XM extension (sample type bit 5: the left
channel's data, then the right one's, each delta-coded; lengths and loops in bytes of both).
OpenMPT and libopenmpt read it; MilkyTracker and FT2 itself would play only half of it.
"""
import struct
from dataclasses import dataclass, field

import numpy as np

NOTE_OFF = 97


@dataclass
class XMSample:
    name: str
    pcm: np.ndarray                # int16, (n,) mono or (n, 2) stereo
    loop_start: int = 0            # in sample frames
    loop_length: int = 0           # 0: no loop
    volume: int = 64
    finetune: int = 0              # -128..127, 1/128 semitone
    relative_note: int = 0         # semitones; XM note C-4 (index 48, MIDI 60) plays at 8363 Hz at 0/0
    panning: int = 128


@dataclass
class XMInstrument:
    name: str
    samples: list
    keymap: list                   # 96 sample indices, for XM notes 1..96 (MIDI 12..107)
    envelope: list                 # [(tick, value 0..64)], at most 12 points
    sustain: int = -1              # envelope point held until key-off, -1 for none
    fadeout: int = 0


@dataclass
class XMModule:
    name: str
    channels: int
    orders: list
    patterns: list                 # each: rows x channels of (note, ins, vol, fx, param), 0 = empty
    instruments: list
    speed: int = 6
    tempo: int = 125
    restart: int = 0
    tracker: str = "Sulphur xm composer"


def _pad(text, n):
    return text.encode("ascii", "replace")[:n].ljust(n, b"\0")


def _delta16(x):
    x = x.astype(np.int16)
    d = np.diff(x.astype(np.int32), prepend=0)
    return d.astype(np.int16).astype("<i2").tobytes()


def write(path, m: XMModule):
    out = bytearray()
    out += b"Extended Module: " + _pad(m.name, 20) + b"\x1a" + _pad(m.tracker, 20)
    out += struct.pack("<HI", 0x0104, 276)
    out += struct.pack("<HHHHHHHH", len(m.orders), m.restart, m.channels, len(m.patterns),
                       len(m.instruments), 1, m.speed, m.tempo)
    out += bytes(m.orders) + bytes(256 - len(m.orders))
    for pat in m.patterns:
        data = bytearray()
        for row in pat:
            for cell in row:
                note, ins, vol, fx, param = cell
                mask = (note > 0) | (ins > 0) << 1 | (vol > 0) << 2 | (fx > 0) << 3 | (param > 0) << 4
                if mask == 31:
                    data += bytes([note, ins, vol, fx, param])
                    continue
                data.append(0x80 | mask)
                for bit, val in enumerate((note, ins, vol, fx, param)):
                    if mask & (1 << bit):
                        data.append(val)
        assert len(data) < 65536
        out += struct.pack("<IBHH", 9, 0, len(pat), len(data)) + data
    for ins in m.instruments:
        head = bytearray()
        head += _pad(ins.name, 22) + b"\0" + struct.pack("<H", len(ins.samples))
        head += struct.pack("<I", 40) + bytes(ins.keymap)
        env = list(ins.envelope) + [(0, 0)] * (12 - len(ins.envelope))
        head += b"".join(struct.pack("<HH", t, v) for t, v in env)
        head += bytes(48)                                         # panning envelope
        flags = 1 | (2 if ins.sustain >= 0 else 0)
        head += bytes([len(ins.envelope), 0, max(0, ins.sustain), 0, 0, 0, 0, 0, flags, 0, 0, 0, 0, 0])
        head += struct.pack("<HH", ins.fadeout, 0)
        size = 4 + len(head)
        head += bytes(263 - size)
        out += struct.pack("<I", 263) + head
        datas = []
        for s in ins.samples:
            stereo = s.pcm.ndim == 2
            frames = len(s.pcm)
            bpf = 4 if stereo else 2
            kind = 0x10 | (0x20 if stereo else 0) | (1 if s.loop_length > 0 else 0)
            out += struct.pack("<IIIBbBBbB", frames * bpf, s.loop_start * bpf, s.loop_length * bpf,
                               s.volume, s.finetune, kind, s.panning, s.relative_note, 0)
            out += _pad(s.name, 22)
            datas.append(_delta16(s.pcm[:, 0]) + _delta16(s.pcm[:, 1]) if stereo else _delta16(s.pcm))
        for d in datas:
            out += d
    with open(path, "wb") as f:
        f.write(out)


def read(path) -> XMModule:
    b = open(path, "rb").read()
    assert b[:17] == b"Extended Module: ", "not an XM file"
    name = b[17:37].rstrip(b"\0").decode("ascii", "replace")
    tracker = b[38:58].rstrip(b"\0").decode("ascii", "replace")
    hsize = struct.unpack_from("<I", b, 60)[0]
    length, restart, channels, npat, nins, flags, speed, tempo = struct.unpack_from("<HHHHHHHH", b, 64)
    assert flags & 1, "only linear frequency tables are supported"
    orders = list(b[80:80 + length])
    pos = 60 + hsize
    patterns = []
    for _ in range(npat):
        plen, _, rows, size = struct.unpack_from("<IBHH", b, pos)
        pos += plen
        data = b[pos:pos + size]
        pos += size
        pat, i = [], 0
        for _ in range(rows):
            row = []
            for _ in range(channels):
                if size == 0:
                    row.append((0, 0, 0, 0, 0))
                    continue
                c = data[i]
                if c & 0x80:
                    i += 1
                    vals = []
                    for bit in range(5):
                        if c & (1 << bit):
                            vals.append(data[i])
                            i += 1
                        else:
                            vals.append(0)
                    row.append(tuple(vals))
                else:
                    row.append(tuple(data[i:i + 5]))
                    i += 5
            pat.append(row)
        patterns.append(pat)
    instruments = []
    for _ in range(nins):
        isize = struct.unpack_from("<I", b, pos)[0]
        iname = b[pos + 4:pos + 26].rstrip(b"\0").decode("ascii", "replace")
        ns = struct.unpack_from("<H", b, pos + 27)[0]
        if ns == 0:
            pos += isize
            instruments.append(XMInstrument(iname, [], [0] * 96, [], -1))
            continue
        shsize = struct.unpack_from("<I", b, pos + 29)[0]
        keymap = list(b[pos + 33:pos + 129])
        pts = [struct.unpack_from("<HH", b, pos + 129 + 4 * k) for k in range(12)]
        npts, _, vsus = b[pos + 225], b[pos + 226], b[pos + 227]
        vtype = b[pos + 233]
        fadeout = struct.unpack_from("<H", b, pos + 239)[0]
        envelope = pts[:npts] if vtype & 1 else []
        sustain = vsus if (vtype & 2) else -1
        pos += isize
        heads = []
        for _ in range(ns):
            ln, ls, ll, vol, ft, kind, pan, rel, _ = struct.unpack_from("<IIIBbBBbB", b, pos)
            sname = b[pos + 18:pos + 40].rstrip(b"\0").decode("ascii", "replace")
            heads.append((ln, ls, ll, vol, ft, kind, pan, rel, sname))
            pos += shsize
        samples = []
        for ln, ls, ll, vol, ft, kind, pan, rel, sname in heads:
            raw = b[pos:pos + ln]
            pos += ln
            bits16, stereo = bool(kind & 0x10), bool(kind & 0x20)
            d = np.frombuffer(raw, dtype="<i2" if bits16 else np.int8).astype(np.int64)
            span = 65536 if bits16 else 256
            if stereo:
                half = len(d) // 2
                pcm = np.stack([np.cumsum(d[:half]), np.cumsum(d[half:])], axis=1)
            else:
                pcm = np.cumsum(d)
            pcm = (pcm + span // 2) % span - span // 2
            if not bits16:
                pcm = pcm * 256
            unit = (2 if bits16 else 1) * (2 if stereo else 1)
            loop = (kind & 3) != 0 and ll > 0
            samples.append(XMSample(sname, pcm.astype(np.int16), ls // unit if loop else 0,
                                    ll // unit if loop else 0, vol, ft, rel, pan))
        instruments.append(XMInstrument(iname, samples, keymap, envelope, sustain, fadeout))
    return XMModule(name, channels, orders, patterns, instruments, speed, tempo, restart, tracker)
