"""A Python mirror of the sequencer in src/sound.h and of the Vircon32 SPU, for reference renders.

The engine half repeats the C code statement by statement in float32, so the console and this
renderer should produce the same samples; the SPU half follows ConsoleLogic/V32SPU.cpp: a sound
is read at the integer part of a double position advanced by the channel speed (no
interpolation), channels are summed into 16-bit samples in channel order, and the sum wraps
around instead of clipping. Keep both halves in step with the C code they mirror.
"""
import numpy as np

F = np.float32
SAMPLES_PER_FRAME = 735
NEVER = 0x7FFFFFFF


class Spu:
    def __init__(self, sounds):
        """sounds: list of dicts {pcm: int16 (n, 2), loop: bool, ls: int, le: int}."""
        self.sounds = sounds
        self.ch = [dict(state=0, sound=0, pos=0.0, speed=F(1.0), vol=F(0.5), loop=False) for _ in range(16)]

    # the ports the C code writes
    def stop(self, c):
        self.ch[c]["state"] = 0
        self.ch[c]["pos"] = 0.0

    def speed(self, c, s):
        self.ch[c]["speed"] = F(min(max(F(s), F(0)), F(128)))

    def volume(self, c, v):
        self.ch[c]["vol"] = F(min(max(F(v), F(0)), F(8)))

    def play(self, sound, c):
        ch = self.ch[c]
        if ch["state"] == 0:
            ch["sound"] = sound
        ch["loop"] = self.sounds[ch["sound"]]["loop"]
        ch["pos"] = 0.0
        ch["state"] = 2

    def playing(self, c):
        return self.ch[c]["state"] == 2

    def _positions(self, ch, n):
        """Integer read positions for up to n samples, advancing the channel."""
        snd = self.sounds[ch["sound"]]
        length = len(snd["pcm"])
        ls, le = snd["ls"], snd["le"]
        out = []
        sp = float(ch["speed"])
        pos = ch["pos"]
        done = 0
        while done < n:
            m = n - done
            seq = np.cumsum(np.concatenate([[pos], np.full(m, sp)]))   # sequential double adds
            read, after = seq[:-1], seq[1:]
            cut = m
            event = None
            if ch["loop"] and le > ls:
                cross = np.nonzero((read <= le) & (after > le))[0]
                if len(cross):
                    cut = cross[0] + 1
                    event = "loop"
            over = np.nonzero(after[:cut] > length - 1)[0]
            if event is None and len(over):
                cut = over[0] + 1
                event = "end"
            out.append(read[:cut].astype(np.int64))
            done += cut
            pos = after[cut - 1]
            if event == "loop":
                pos = ls + np.fmod(pos - ls, le - ls)
                if pos > length - 1:
                    event = "end"
            if event == "end":
                ch["state"] = 0
                ch["pos"] = 0.0
                return np.concatenate(out)
        ch["pos"] = pos
        return np.concatenate(out)

    def render(self):
        """One frame of output, int16 (735, 2), as SPU::UpdateOutputBuffer makes it."""
        acc = np.zeros((SAMPLES_PER_FRAME, 2), dtype=np.int32)
        for ch in self.ch:
            if ch["state"] != 2:
                continue
            idx = self._positions(ch, SAMPLES_PER_FRAME)
            k = len(idx)
            pcm = self.sounds[ch["sound"]]["pcm"][idx].astype(F)
            vol = F(F(1.0) * ch["vol"])
            mixed = acc[:k].astype(F) + (vol * pcm).astype(F)
            v = np.trunc(mixed).astype(np.int64)
            acc[:k] = ((v + 32768) & 0xFFFF) - 32768           # int16 wrap-around
        return acc.astype(np.int16)


class Engine:
    """music_* and sound_frame from src/sound.h."""

    def __init__(self, spu, data):
        self.spu, self.d = spu, data
        self.song = -1
        self.time = 0
        self.fade = F(1.0)
        self.duck = F(1.0)
        self.master = F(0.0)
        V = 12
        self.ptr = [0] * V
        self.end = [0] * V
        self.next = [NEVER] * V
        self.state = [0] * V
        self.left = [0] * V
        self.age = [0] * V
        self.vib = [0] * V
        self.old = [False] * V
        self.env = [F(0)] * V
        self.k = [F(0)] * V
        self.sus = [F(0)] * V
        self.rel = [F(0)] * V
        self.gain = [F(0)] * V
        self.base = [F(1)] * V
        self.bend = [F(1)] * V
        self.sfx_started = [-1000] * 3
        self.sfx_clock = 0
        self.sfx_seed = 12345

    def rewind(self, from_loop):
        d = self.d
        base = self.song * 12
        for v in range(12):
            first = d["first"][base + v]
            self.end[v] = first + d["count"][base + v]
            self.ptr[v] = first + (d["loop_ptr"][base + v] if from_loop else 0)
            self.next[v] = d["events"][self.ptr[v] * 2] & 0xFFFF if self.ptr[v] < self.end[v] else NEVER

    def release_all(self):
        for v in range(12):
            if self.state[v] != 0 and not self.old[v]:
                self.gain[v] = F(self.gain[v] * self.master)
                self.old[v] = True

    def music_play(self, song):
        if song == self.song:
            return
        was = self.song != -1
        self.release_all()
        self.song = song
        self.time = 0
        self.fade = F(0.0) if was else F(1.0)
        self.rewind(False)

    def music_stop(self):
        self.release_all()
        self.song = -1
        self.next = [NEVER] * 12

    def trigger(self, v, w0, w1):
        d, spu = self.d, self.spu
        smp = w1 & 255
        env = (w1 >> 22) & 15
        self.base[v] = F(d["semi"][(w1 >> 8) & 127] * d["sample_speed"][smp])
        self.bend[v] = d["bend_start"][(w1 >> 28) & 3]
        self.vib[v] = (w1 >> 26) & 3
        self.gain[v] = F(F((w1 >> 15) & 127) * d["vel_scale"])
        self.env[v] = d["env_start"][env]
        self.k[v] = d["env_k"][env]
        self.sus[v] = d["env_sus"][env]
        self.rel[v] = d["env_rel"][env]
        self.left[v] = (w0 >> 16) & 32767
        self.age[v] = 0
        self.state[v] = 1
        self.old[v] = False
        spu.stop(v)
        spu.speed(v, F(self.base[v] * self.bend[v]))
        spu.volume(v, F(F(self.env[v] * self.gain[v]) * self.master))
        spu.play(d["snd_base"] + smp, v)

    def music_update(self):
        d, spu = self.d, self.spu
        if self.fade < F(1.0):
            self.fade = F(self.fade + F(0.0333333))
            if self.fade > F(1.0):
                self.fade = F(1.0)
        if self.duck < F(1.0):
            self.duck = F(self.duck + F(0.0125))
            if self.duck > F(1.0):
                self.duck = F(1.0)
        if self.song != -1:
            self.master = F(F(d["song_gain"][self.song] * self.fade) * self.duck)
        ev = d["events"]
        for v in range(12):
            if self.time == self.next[v]:
                at = self.ptr[v] * 2
                self.trigger(v, ev[at], ev[at + 1])
                self.ptr[v] += 1
                self.next[v] = ev[at + 2] & 0xFFFF if self.ptr[v] < self.end[v] else NEVER
                continue
            st = self.state[v]
            if st == 0:
                continue
            if st == 1:
                self.env[v] = F(self.sus[v] + F(F(self.env[v] - self.sus[v]) * self.k[v]))
                self.left[v] -= 1
                if self.left[v] <= 0:
                    self.state[v] = 2
            else:
                self.env[v] = F(self.env[v] * self.rel[v])
                if self.env[v] < F(0.003):
                    spu.stop(v)
                    self.state[v] = 0
                    continue
            if self.old[v]:
                self.gain[v] = F(self.gain[v] * F(0.92))
                if self.gain[v] < F(0.0005):
                    spu.stop(v)
                    self.state[v] = 0
                    continue
                spu.volume(v, F(F(self.env[v] * self.gain[v]) * self.duck))
            else:
                spu.volume(v, F(F(self.env[v] * self.gain[v]) * self.master))
            self.age[v] += 1
            bent = False
            if self.bend[v] < F(1.0):
                self.bend[v] = F(F(1.0) - F(F(F(1.0) - self.bend[v]) * F(0.72)))
                if self.bend[v] > F(0.9995):
                    self.bend[v] = F(1.0)
                bent = True
            if self.vib[v] > 0 and self.age[v] > 10:
                depth = F(d["vib_depth"][self.vib[v]] * min(F(1.0), F(F(self.age[v] - 10) * F(0.0666667))))
                wobble = F(F(1.0) + F(depth * np.sin(F(F(self.age[v]) * F(0.576)))))
                spu.speed(v, F(F(self.base[v] * self.bend[v]) * wobble))
            elif bent:
                spu.speed(v, F(self.base[v] * self.bend[v]))
        if self.song != -1:
            self.time += 1
            if self.time >= d["length"][self.song]:
                self.time = d["loop"][self.song]
                self.rewind(True)

    # effects
    def sfx_channel(self):
        best, oldest = 12, NEVER
        for c in range(3):
            if not self.spu.playing(12 + c):
                return 12 + c
            if self.sfx_started[c] < oldest:
                oldest, best = self.sfx_started[c], 12 + c
        return best

    def sfx_play(self, effect, volume, speed, c):
        self.spu.stop(c)
        self.spu.speed(c, speed)
        self.spu.volume(c, volume)
        self.spu.play(self.d["sfx_base"] + effect, c)

    def sound_frame(self, events):
        d = self.d
        self.sfx_clock += 1
        for e, n in enumerate(events):
            if n <= 0:
                continue
            effect = d["sfx_of_event"][e]
            self.sfx_seed = (self.sfx_seed * 75 + 74) % 65537
            speed = F(F(0.97) + F(F(self.sfx_seed & 63) * F(0.001)))
            c = self.sfx_channel()
            self.sfx_started[c - 12] = self.sfx_clock
            self.sfx_play(effect, F(d["sfx_level"][effect] * d["sfx_gain"]), speed, c)
            if n > 1:
                c = self.sfx_channel()
                self.sfx_started[c - 12] = self.sfx_clock
                self.sfx_play(effect, F(F(d["sfx_level"][effect] * d["sfx_gain"]) * F(0.6)), F(speed * F(0.92)), c)
            if d["sfx_ducks"][effect]:
                self.duck = F(0.55)
        self.music_update()

    def ui_sound(self, which):
        d = self.d
        effect = d["sfx_ui_first"] + which
        self.sfx_play(effect, F(d["sfx_level"][effect] * d["sfx_gain"]), F(1.0), 15)
