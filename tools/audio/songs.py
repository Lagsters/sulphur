"""The ten songs, in the order of SONG_* in src/sound.h.

Every song is a grid of 16th-note steps of a whole number of frames (step 6 = 150 BPM, 7 = 128.6,
8 = 112.5, 9 = 100, 10 = 90, 12 = 75). A song loops from loop_bar to its end; the last bar leads
back into the loop bar (a fill, the dominant chord), and note tails and echoes run across the seam.
"""
from compose import (ARP1, ARP2, BASS, ECHO, GTR, HAT, KICK, LEAD, PAD1, PAD2, SNARE, X, Song,
                     midi)

ROCK = {"k": "x.......x.x.....", "s": "....S.......S...", "h": "x.x.x.x.x.x.x.x."}
ROCK2 = {"k": "x.......x.x...x.", "s": "....S.......S..g", "h": "x.x.x.x.x.x.x.xO"}
DRIVE = {"k": "x.x...x.x.x...x.", "s": "....S.......S...", "h": "x.o.x.o.x.o.x.o."}
HALF = {"k": "x.......x.....x.", "s": "........S.......", "h": "x.x.x.x.x.x.x.x."}
DOUBLE = {"k": "xxxxxxxxxxxxxxxx", "s": "....S.......S...", "h": "x...x...x...x..."}
POLKA = {"k": "x.......x.......", "s": "....s.......s...", "h": "..x...x...x...x."}
FILL = {"k": "x.......x.......", "s": "....S...ttmmll.S", "h": "x.x.x.x........."}
FILL16 = {"k": "x...............", "s": "SSSSttttmmmmllll", "h": "................"}
TOMS = {"s": "l.....l.....m.l."}


def title(bank):
    """Epic: a folk fiddle over a drone, then the band; D minor, 112.5 BPM."""
    s = Song(bank, "title", 8, 44, loop_bar=4)
    A = ["Dm", "Bb", "C", "Dm", "F", "Bb", "C", "A"]
    MEL = ("D5:4 E5:2 F5:2 G5:4 A5:4  Bb5:4 A5:2 G5:2 F5:8  G5:2 F5:2 E5:2 D5:2 E5:4 C5:4  D5:12 A4:4 "
           "A5:4 C6:2 Bb5:2 A5:4 F5:4  D6:4 C6:2 Bb5:2 F5:8  E5:2 F5:2 G5:2 E5:2 C5:4 G5:4  A5:4 C#6:4 E6:4 A5:4")
    # intro: drone, the theme on the fiddle, bells, a swell
    s.note(X, 0, 0, 64, "drone", midi("D3"), 70, env="drone")
    s.melody(LEAD, 0, MEL.split("A5:4 C6:2")[0], "fiddle", 96)
    s.note(PAD1, 0, 0, 16, "bell", midi("D5"), 70)
    s.note(PAD2, 2, 0, 16, "bell", midi("A4"), 60)
    s.pad(2, ["Dm", "A"], 60, picks=(0, 2))
    s.drums(3, 1, {"s": "........ttmmllll", "c": "................"})
    # A: the band with the fiddle
    s.drums(4, 7, ROCK)
    s.drums(11, 1, FILL)
    s.drums(4, 1, {"c": "x..............."})
    s.bass(4, A, "x.x.x.xox.x.x.xo", 104)
    s.power(4, A, "X-------M.M.X---", 92)
    s.melody(LEAD, 4, MEL, "fiddle", 104)
    s.pad(4, A, 58)
    # B: the lead guitar takes the theme an octave down, clean arpeggios underneath
    s.drums(12, 7, ROCK2)
    s.drums(19, 1, FILL)
    s.drums(12, 1, {"c": "x..............."})
    s.bass(12, A, "x.xxx.x.x.xxx.xo", 104)
    s.power(12, A, "X---M.M.X---M.M.", 84)
    s.melody(LEAD, 12, MEL, "lead", 100, transpose=-12)
    s.arp(12, A, "0.1.2.3.4.3.2.1.", 70, lo=50)
    s.pad(12, A, 54)
    # C: the bridge, half time, a flute over echoing arpeggios
    C = ["Bb", "F", "C", "Dm", "Gm", "Bb", "A", "A"]
    s.drums(20, 6, HALF, 0.85)
    s.drums(26, 2, {"k": "x...x...x...x...", "s": "....S.......S.SS", "h": "x.x.x.x.x.x.x.x."})
    s.bass(20, C, "x-------x-----5-", 100)
    s.arp(20, C, "0..2..3..4..3.2.", 74, lo=50)
    s.melody(LEAD, 20, "F5:6 D5:2 F5:4 G5:4  A5:8 C5:8  E5:6 G5:2 C6:4 Bb5:4  A5:12 -:4 "
             "G5:6 Bb5:2 D6:4 C6:4  Bb5:4 A5:4 F5:8  E5:4 C#5:4 E5:4 A5:4  G5:4 F5:4 E5:4 C#5:4", "flute", 100)
    s.pad(20, C, 66, env="slowpad")
    s.power(26, ["A", "A"], ["X---------------", "X-------X-X-X-X-"], 80)
    # A': fiddle and lead guitar together, an octave apart
    s.drums(28, 7, ROCK)
    s.drums(35, 1, FILL)
    s.drums(28, 1, {"c": "x..............."})
    s.bass(28, A, "x.x.x.xox.x.x.xo", 106)
    s.power(28, A, "X-------M.M.X---", 94)
    s.melody(LEAD, 28, MEL, "fiddle", 100)
    s.melody(ARP1, 28, MEL, "lead", 84, transpose=-12)
    s.pad(28, A, 60)
    # outro: a galloping riff and a solo, back to the loop
    O = ["Dm", "Dm", "Bb", "C", "Dm", "Dm", "Bb", "A"]
    s.drums(36, 7, {"k": "x.xx.xx.x.xx.xx.", "s": "....S.......S...", "h": "x.x.x.x.x.x.x.x."})
    s.drums(43, 1, FILL16)
    s.drums(36, 1, {"c": "x..............."})
    s.drums(40, 1, {"c": "x..............."})
    s.bass(36, O, "x.xx.xx.x.xx.xx.", 104)
    s.power(36, O, "X.MM.MM.X.MM.MM.", 92)
    s.improv(LEAD, 36, O, [2, 4, 5, 7, 9, 10, 0], seed=1, lo=62, hi=79)
    s.pad(36, O, 56)
    s.echo(LEAD, ECHO, 6, 0.4)
    return s


def battle(bank):
    """Driving: palm-muted gallops in E minor, 150 BPM."""
    s = Song(bank, "battle", 6, 48)
    R = ["Em", "Em", "C", "D", "Em", "Em", "C", "B"]
    V = ["Em", "G", "D", "A", "Em", "G", "D", "B"]
    CH = ["C", "D", "Em", "Em", "C", "D", "B", "B"]
    riff = ["MMM.MMM.MMXM.M.M", "MMM.MMM.MMXM.X-.", "X-MMX-MMX-MMX-M.", "X-MMX-MMX-M.X-X-"]
    # riff
    s.drums(0, 7, DRIVE)
    s.drums(7, 1, FILL)
    s.drums(0, 1, {"c": "x..............."})
    s.bass(0, R, "x.xx.xx.x.xx.xx.", 106)
    s.power(0, R, riff, 96)
    # verse with lead
    s.drums(8, 7, ROCK2)
    s.drums(15, 1, FILL)
    s.bass(8, V, "x.x.x.x.x.x.x.xo", 104)
    s.power(8, V, "X---M.M.X---M.M.", 86)
    s.melody(LEAD, 8, "E5:6 G5:2 B5:4 A5:4  G5:4 F#5:4 D5:8  F#5:6 A5:2 D6:4 C#6:4  B5:4 A5:4 E5:8 "
             "E5:6 G5:2 B5:4 A5:4  B5:4 D6:4 G5:8  F#5:4 E5:4 D5:4 F#5:4  B5:16", "lead", 100, transpose=-12)
    s.pad(8, V, 52)
    # chorus: open chords, strings, the lead high
    s.drums(16, 7, {"k": "x.x...x.x.x...x.", "s": "....S.......S...", "h": "O.x.O.x.O.x.O.x."})
    s.drums(23, 1, FILL)
    s.drums(16, 1, {"c": "x..............."})
    s.drums(20, 1, {"c": "x..............."})
    s.bass(16, CH, "x.x.x.x.x.x.x.x.", 108)
    s.power(16, CH, "X-------X---X-X-", 96)
    s.melody(LEAD, 16, "G5:8 A5:4 B5:4  A5:8 F#5:4 D5:4  E5:12 B4:4  E5:4 G5:4 B5:8 "
             "C6:8 B5:4 A5:4  A5:8 B5:4 C6:4  B5:16  D#5:8 F#5:8", "lead", 104, transpose=-12)
    s.pad(16, CH, 62)
    s.arp(16, CH, "0.2.3.2.0.2.3.2.", 62, lo=52)
    # riff again, with a solo
    s.drums(24, 7, DRIVE)
    s.drums(31, 1, FILL)
    s.drums(24, 1, {"c": "x..............."})
    s.bass(24, R, "x.xx.xx.x.xx.xx.", 106)
    s.power(24, R, riff, 96)
    s.improv(LEAD, 24, R, [4, 6, 7, 9, 11, 0, 2], seed=2, lo=64, hi=81)
    # breakdown: half time, toms, the arpeggio alone
    B = ["Am", "Em", "C", "B", "Am", "Em", "C", "B"]
    s.drums(32, 6, {"k": "x.....x...x.....", "s": "........S.....tm", "h": "x...x...x...x..."})
    s.drums(38, 2, {"k": "x.x.x.x.x.x.x.x.", "s": "....S.......S.SS", "h": "x.x.x.x.x.x.x.x."})
    s.bass(32, B, "x-------x---x---", 100)
    s.arp(32, B, "0.1.2.3.4.3.2.1.", 74, lo=52)
    s.power(32, B, "X---------------", 76)
    s.pad(32, B, 64)
    # chorus out
    s.drums(40, 7, {"k": "x.x...x.x.x...x.", "s": "....S.......S...", "h": "O.x.O.x.O.x.O.x."})
    s.drums(47, 1, FILL16)
    s.drums(40, 1, {"c": "x..............."})
    s.bass(40, CH, "x.x.x.x.x.x.x.x.", 108)
    s.power(40, CH, "X-------X---X-X-", 96)
    s.melody(LEAD, 40, "G5:8 A5:4 B5:4  A5:8 F#5:4 D5:4  E5:12 B4:4  E5:4 G5:4 B5:8 "
             "C6:8 B5:4 A5:4  A5:8 B5:4 C6:4  B5:16  D#5:8 F#5:8", "lead", 104, transpose=-12)
    s.pad(40, CH, 62)
    s.echo(LEAD, ECHO, 3, 0.35)
    return s


def wroclaw(bank):
    """A lively town: fiddle and clean guitars, G major with the mixolydian F, 128.6 BPM."""
    s = Song(bank, "wroclaw", 7, 48)
    A = ["G", "C", "G", "D", "G", "C", "F", "D"]
    B = ["Em", "C", "G", "D", "Em", "C", "D", "D"]
    MA = ("G5:2 A5:2 B5:4 B5:2 A5:2 G5:4  E5:2 G5:2 C6:4 B5:2 A5:2 G5:4  B5:2 A5:2 G5:2 A5:2 B5:4 D6:4  A5:12 F#5:4 "
          "G5:2 A5:2 B5:4 B5:2 A5:2 G5:4  E5:2 G5:2 C6:4 E6:4 C6:4  A5:2 C6:2 F5:4 A5:4 C6:4  D6:8 A5:4 F#5:4")
    MB = ("E5:4 G5:4 B5:6 A5:2  G5:4 E5:4 C5:8  D5:2 G5:2 B5:4 A5:2 G5:2 D5:4  F#5:8 A5:8 "
          "B5:4 G5:4 E5:6 F#5:2  G5:4 A5:4 E5:8  F#5:4 A5:4 D6:4 C6:4  A5:16")
    for b0, sec in [(0, "intro"), (8, "a"), (16, "b"), (24, "a2"), (32, "bridge"), (40, "a3")]:
        if sec == "intro":
            s.drums(b0, 8, {"k": "x.......x.......", "h": "..x...x...x...x."}, 0.8)
            s.bass(b0, A, "x...5...x...5...", 96)
            s.arp(b0, A, "0.1.2.1.3.1.2.1.", 80, lo=50)
            s.note(X, b0, 0, 128, "drone", midi("G2") + 12, 46, env="drone")
            s.melody(LEAD, b0 + 4, MA.split("  ")[0] + " " + " ".join(MA.split("  ")[1:4]), "flute", 90)
        elif sec in ("a", "a2", "a3"):
            s.drums(b0, 7, {"k": "x.....x.x.......", "s": "....S.......S...", "h": "x.xox.xox.xox.xo"})
            s.drums(b0 + 7, 1, FILL)
            s.drums(b0, 1, {"c": "x..............."})
            s.bass(b0, A, "x..x5...x..x5.x.", 104)
            s.arp(b0, A, "0.2.3.2.1.2.3.2.", 72, lo=50)
            s.melody(LEAD, b0, MA, "fiddle", 104)
            if sec != "a":
                s.power(b0, A, "X.....X.X.......", 74)
            if sec == "a3":
                s.melody(PAD1, b0, MA, "flute", 76, transpose=-12 + 12)
            else:
                s.pad(b0, A, 50)
        elif sec == "b":
            s.drums(b0, 7, {"k": "x.......x.x.....", "s": "....S.......S...", "h": "O.x.x.x.O.x.x.x."})
            s.drums(b0 + 7, 1, FILL)
            s.drums(b0, 1, {"c": "x..............."})
            s.bass(b0, B, "x.x.x.x.x.x.x.xo", 104)
            s.power(b0, B, "X---M.M.X---M.M.", 82)
            s.melody(LEAD, b0, MB, "fiddle", 106)
            s.pad(b0, B, 56)
        elif sec == "bridge":
            Br = ["C", "D", "Bm", "Em", "C", "D", "G", "D"]
            s.drums(b0, 7, {"k": "x.......x.......", "s": "........S.......", "h": "x.x.x.x.x.x.x.x."}, 0.85)
            s.drums(b0 + 7, 1, FILL)
            s.bass(b0, Br, "x-------x-----5-", 100)
            s.note(X, b0, 0, 128, "drone", midi("D3"), 50, env="drone")
            s.arp(b0, Br, "0..2..3..4..3.2.", 72, lo=50)
            s.melody(LEAD, b0, "E5:6 G5:2 C6:8  D6:6 C6:2 A5:8  B5:6 A5:2 F#5:8  G5:12 -:4 "
                     "E5:6 G5:2 C6:8  D6:4 E6:4 F#6:8  G6:8 D6:8  A5:16", "flute", 98, transpose=-12)
            s.pad(b0, Br, 64, env="slowpad")
    s.echo(LEAD, ECHO, 3, 0.3)
    return s


def sleza(bank):
    """Night forest: a flute and echoing arpeggios over a drone, A minor (dorian), 75 BPM."""
    s = Song(bank, "sleza", 12, 30)
    A = ["Am", "G", "F", "Em", "Am", "G", "Dm", "Em"]
    s.note(X, 0, 0, 30 * 16, "drone", midi("A2") + 12, 50, env="drone")
    for b0 in (0, 8, 16):
        s.arp(b0, A, "0.2.4.3.1.3.2.4.", 70, lo=52)
        s.pad(b0, A, 56, env="slowpad", picks=(0, 2))
        s.bass(b0, A, "x---------------", 92)
        s.drums(b0, 8, {"s": "l.........l....."}, 0.7)
        s.drums(b0, 8, {"h": "........o......."}, 0.6)
    s.melody(LEAD, 2, "E5:4 A5:4 G5:4 E5:4  F5:6 E5:2 C5:8  B4:4 C5:2 D5:2 E5:8  -:16 "
             "A5:4 C6:4 B5:4 G5:4  A5:6 F5:2 D5:8  E5:4 F#5:4 G5:4 B5:4  A5:16", "flute", 100)
    s.melody(LEAD, 10, "C6:8 B5:4 A5:4  G5:6 F5:2 E5:8  F5:4 A5:4 D6:8  B5:16 "
             "A5:4 E5:4 A5:4 B5:4  C6:6 B5:2 A5:8  G5:4 F#5:4 E5:8  E5:16", "flute", 96)
    # the middle: a distant lead guitar, slow, deep in echo
    s.melody(LEAD, 18, "A4:8 C5:8  D5:12 B4:4  C5:8 A4:8  B4:16  E5:8 D5:8  F5:12 D5:4  E5:8 B4:8  A4:16",
             "lead", 82, vib=3)
    for b in (6, 14, 22):
        s.note(GTR, b, 8, 32, "bell", midi("E6"), 36)
    s.melody(KICK, 24, "E6:16 C6:16 D6:16 B5:16", "bell", 40)
    s.arp(24, ["Am", "G", "F", "Em", "Am", "Am"], "0.2.4.3.1.3.2.4.", 64, lo=52)
    s.pad(24, ["Am", "G", "F", "Em", "Am", "Am"], 54, env="slowpad", picks=(0, 2))
    s.bass(24, ["Am", "G", "F", "Em", "Am", "Am"], "x---------------", 90)
    s.drums(24, 6, {"s": "l.........l.....", "h": "........o......."}, 0.65)
    s.echo(LEAD, ECHO, 6, 0.42)
    return s


HEJNAL = "F4:4 A4:4 C5:8  C5:4 C5:4 D5:2 C5:2 Bb4:2 A4:2  Bb4:4 C5:4 A4:8  F4:4 A4:4 C5:6 -:2  " \
         "C5:2 D5:2 C5:2 Bb4:2 A4:2 G4:2 A4:4  F4:12 -:4"


def krakow(bank):
    """Traditional, with the Hejnal mariacki motif: a trumpet from the tower, then a
    krakowiak-like band; F major, 112.5 BPM."""
    s = Song(bank, "krakow", 8, 44, loop_bar=6)
    # the tower call alone, with bells and reverb, broken off as legend has it
    s.melody(LEAD, 0, HEJNAL.rsplit("F4:12", 1)[0] + "F4:3", "trumpet", 104, vib=1)
    s.note(X, 0, 0, 16, "bell", midi("F5"), 64)
    s.note(X, 2, 0, 16, "bell", midi("C5"), 56)
    s.note(X, 4, 0, 32, "bell", midi("F5"), 60)
    s.pad(0, ["F", "F", "F", "F", "Bb", "C"], 46, env="slowpad")
    s.drums(5, 1, {"s": "........ttmmllSS"})
    A = ["F", "C", "Dm", "Bb", "F", "C", "Bb", "C"]
    MA = ("C5:2 F5:2 F5:2 A5:2 G5:2 F5:2 E5:4  E5:2 G5:2 G5:2 Bb5:2 A5:2 G5:2 E5:4  D5:2 F5:2 A5:2 D6:2 C6:4 A5:4  "
          "Bb5:2 A5:2 G5:2 F5:2 D5:8  C5:2 F5:2 A5:2 C6:2 C6:2 A5:2 F5:4  G5:2 E5:2 C5:2 E5:2 G5:4 C6:4  "
          "Bb5:2 D6:2 F5:2 D6:2 C6:2 Bb5:2 A5:4  G5:4 A5:4 G5:4 E5:4")
    KRAK = {"k": "x...x...x...x...", "s": "..s.S...s.s.S...", "h": "x.x.x.x.x.x.x.x."}
    for b0 in (6, 22):
        s.drums(b0, 7, KRAK)
        s.drums(b0 + 7, 1, FILL)
        s.drums(b0, 1, {"c": "x..............."})
        s.bass(b0, A, "x.5.x.5.x.5.x.5.", 104)
        s.arp(b0, A, "..3.2.3...3.2.3.", 70, lo=52)
        s.melody(LEAD, b0, MA, "fiddle", 106)
        s.pad(b0, A, 54)
    # B: guitars and strings, the hejnal on the trumpet over the band
    B = ["Dm", "Bb", "F", "C", "Dm", "Bb", "C", "C"]
    for b0 in (14, 30):
        s.drums(b0, 7, ROCK)
        s.drums(b0 + 7, 1, FILL)
        s.drums(b0, 1, {"c": "x..............."})
        s.bass(b0, B, "x.x.x.xox.x.x.xo", 106)
        s.power(b0, B, "X-------M.M.X---", 90)
        s.melody(LEAD, b0 + 1, HEJNAL, "trumpet", 108, vib=1)
        s.pad(b0, B, 58)
    # coda back to the loop: fiddle and trumpet answer each other
    Cd = ["Bb", "C", "Am", "Dm", "Bb", "C", "F", "C"]
    s.drums(38, 5, KRAK)
    s.drums(43, 1, FILL16)
    s.bass(38, Cd[:6], "x.5.x.5.x.5.x.5.", 104)
    s.power(38, Cd[:6], "X-------X---X---", 86)
    s.melody(LEAD, 38, "D6:4 C6:4 Bb5:4 A5:4  G5:4 A5:4 C6:8  C6:4 A5:4 E5:4 C5:4  D5:12 -:4 "
             "F5:2 G5:2 A5:2 Bb5:2 C6:4 D6:4  E6:8 C6:8", "fiddle", 104)
    s.pad(38, Cd[:6], 58)
    s.echo(LEAD, ECHO, 4, 0.3)
    return s


def boss(bank):
    """Tense: E phrygian, half-step riffs and strings in minor seconds, 128.6 BPM."""
    s = Song(bank, "boss", 7, 40)
    R = ["Em", "F", "Em", "Bb", "Em", "F", "G", "F#"]
    riff = ["MM.MM.XM.MM.X-X-", "MM.MM.XM.MM.X---"]
    for b0 in (0, 24):
        s.drums(b0, 7, {"k": "x.xx..x.x.xx..x.", "s": "....S.......S...", "h": "x.x.x.x.x.x.x.x."})
        s.drums(b0 + 7, 1, FILL)
        s.drums(b0, 1, {"c": "x..............."})
        s.bass(b0, R, "x.xx..x.x.xx..x.", 106)
        s.power(b0, R, riff, 96)
        s.pad(b0, ["Em", "F", "Em", "Bb", "Em", "F", "G", "F#"], 54, picks=(0, 1))
    s.melody(LEAD, 0, "-:16 -:16 E5:4 F5:4 G5:4 Bb5:4  A5:12 -:4  -:16 -:16  B5:4 C6:4 B5:4 G5:4  F#5:16",
             "lead", 96, transpose=-12, vib=3)
    s.improv(LEAD, 24, R, [4, 5, 7, 8, 10, 11, 1], seed=6, lo=64, hi=82)
    M = ["Am", "Em", "F", "B", "Am", "Em", "F", "B"]
    s.drums(8, 8, {"k": "x...x...x...x...", "s": "..........S.....", "h": "xxxxxxxxxxxxxxxx"}, 0.8)
    s.bass(8, M, "x.x.x.x.x.x.x.x.", 100)
    s.power(8, M, "M.M.M.M.M.M.M.MM", 84)
    s.melody(LEAD, 8, "E5:6 F5:2 E5:4 C5:4  B4:8 G4:8  C5:6 B4:2 A4:4 F4:4  D#5:16 "
             "E5:6 F5:2 G5:4 A5:4  B5:8 G5:8  A5:6 G5:2 F5:4 E5:4  D#5:16", "fiddle", 104, vib=3)
    s.pad(8, M, 60, picks=(0, 2))
    S = ["F", "F", "Em", "Em", "Dm", "Dm", "B", "B"]
    s.drums(16, 6, {"s": "l...m...l...t...", "k": "x.......x......."})
    s.drums(22, 2, {"k": "xxxxxxxxxxxxxxxx", "s": "S...S...S...SSSS"})
    s.bass(16, S, "x---------------", 100)
    s.power(16, S, "X---------------", 86)
    s.pad(16, S, 66, env="slowpad", picks=(0, 1))
    s.note(X, 16, 0, 128, "bell", midi("B4"), 50)
    s.note(X, 20, 0, 64, "bell", midi("F5"), 50)
    s.drums(32, 7, {"k": "x.xx..x.x.xx..x.", "s": "....S.......S...", "h": "O.x.O.x.O.x.O.x."})
    s.drums(39, 1, FILL16)
    s.drums(32, 1, {"c": "x..............."})
    s.bass(32, M, "x.xx..x.x.xx..x.", 106)
    s.power(32, M, riff, 96)
    s.melody(LEAD, 32, "E5:6 F5:2 E5:4 C5:4  B4:8 G4:8  C5:6 B4:2 A4:4 F4:4  D#5:16 "
             "E5:6 F5:2 G5:4 A5:4  B5:8 G5:8  A5:6 G5:2 F5:4 E5:4  D#5:16", "lead", 100, vib=3)
    s.pad(32, M, 58)
    s.echo(LEAD, ECHO, 3, 0.35)
    return s


def dragon(bank):
    """The heaviest: slow E phrygian riffs with double kick, tolling bells, 100 BPM."""
    s = Song(bank, "dragon", 9, 36, loop_bar=4)
    R = ["E5", "E5", "F5", "E5", "E5", "E5", "Bb5", "A5"]
    riff = ["X-----MMX---MM.M", "X---X---MMMMX---"]
    s.note(X, 0, 0, 32, "bell", midi("E4"), 70)
    s.note(X, 2, 0, 32, "bell", midi("Bb4"), 64)
    s.drums(0, 3, {"k": "x...............", "s": "l.......l......."})
    s.drums(3, 1, FILL16)
    s.power(0, ["E5", "E5", "F5", "E5"], "X---------------", 100)
    s.bass(0, ["E5", "E5", "F5", "E5"], "x---------------", 106)
    s.pad(0, ["Em", "Em", "F", "Em"], 60, env="slowpad", picks=(0, 1))
    for b0 in (4, 20):
        s.drums(b0, 7, {"k": "x.x...x.x.xx..x.", "s": "........S.......", "h": "x...x...x...x..."})
        s.drums(b0 + 7, 1, FILL)
        s.drums(b0, 1, {"c": "x..............."})
        s.drums(b0 + 4, 1, {"c": "x..............."})
        s.bass(b0, R, ["x-----xxx---xx.x", "x---x---xxxxx---"], 110)
        s.power(b0, R, riff, 100)
        s.pad(b0, ["Em", "Em", "F", "Em", "Em", "Em", "Bb", "A"], 56, picks=(0, 1))
    s.melody(LEAD, 6, "E5:4 F5:4 G5:8  Bb5:12 A5:4  G5:8 F5:8  E5:16  B5:4 C6:4 B5:4 Bb5:4  E5:16",
             "lead", 100, transpose=-12, vib=3)
    C = ["C5", "C5", "D5", "D5", "Bb5", "Bb5", "B5", "B5"]
    for b0 in (12, 28):
        s.drums(b0, 7, DOUBLE)
        s.drums(b0 + 7, 1, FILL16)
        for k in range(8):
            s.drums(b0 + k, 1, {"c": "x..............."})
        s.bass(b0, C, "x.x.x.x.x.x.x.x.", 110)
        s.power(b0, C, "X-------X-------", 100)
        s.pad(b0, ["C", "C", "D", "D", "Bb", "Bb", "B", "B"], 64, picks=(0, 1, 2))
        s.melody(LEAD, b0, "G5:8 A5:4 B5:4  C6:16  A5:8 B5:4 C6:4  D6:16  F6:8 E6:4 D6:4  D6:16  "
                 "D#6:8 E6:4 F#6:4  B5:16", "lead", 104, transpose=-12, vib=3)
    s.improv(LEAD, 20, R, [4, 5, 7, 9, 10, 11, 2], seed=7, lo=62, hi=80)
    s.echo(LEAD, ECHO, 6, 0.33)
    return s


def calm(bank):
    """A still moment: clean guitar arpeggios, strings and a flute, D major, 75 BPM."""
    s = Song(bank, "calm", 12, 22)
    A = ["D", "Bm", "G", "A", "D", "F#m", "G", "A"]
    s.arp(0, A, "0.2.3.4.5.4.3.2.", 76, lo=50)
    s.pad(0, A, 54, env="slowpad")
    s.bass(0, A, "x-------x-------", 86)
    s.melody(LEAD, 2, "F#5:6 E5:2 D5:8  G5:6 A5:2 B5:8  A5:6 F#5:2 D5:4 E5:4  F#5:8 E5:8", "flute", 96)
    B = ["G", "A", "F#m", "Bm", "Em", "G", "A", "A"]
    s.arp(8, B, "0.2.3.4.5.4.3.2.", 76, lo=50)
    s.pad(8, B, 58, env="slowpad")
    s.bass(8, B, "x-------x-------", 86)
    s.melody(LEAD, 8, "B5:6 A5:2 G5:8  C#6:6 B5:2 A5:8  A5:4 F#5:4 C#6:8  D6:16  "
             "B5:6 G5:2 E5:8  D5:4 E5:4 G5:8  A5:8 E5:8  C#5:16", "flute", 96)
    s.arp(16, A[:6], "0.2.3.4.5.4.3.2.", 70, lo=50)
    s.pad(16, A[:6], 52, env="slowpad")
    s.bass(16, A[:6], "x---------------", 84)
    s.melody(LEAD, 16, "D6:8 C#6:4 B5:4  A5:16  B5:8 D6:8  E6:16  D6:8 A5:8  E5:16", "fiddle", 84, transpose=-12)
    for b in (0, 8, 16):
        s.note(X, b, 0, 32, "bell", midi("A5"), 34)
    s.echo(ARP1, ECHO, 6, 0.3)
    return s


def tension(bank):
    """A threat: a low pulse on D against E flat, swelling strings, toms like a heartbeat;
    90 BPM."""
    s = Song(bank, "tension", 10, 24)
    P = ["Dm", "Dm", "Eb", "Dm", "Dm", "Dm", "Bb", "A"]
    for b0 in (0, 8, 16):
        s.bass(b0, P, "x.x.x.x.x.x.x.x.", 98)
        s.drums(b0, 8, {"s": "l..l........l..l", "k": "x..x............"}, 0.85)
        s.pad(b0, ["Dm", "Dm", "Eb", "Dm", "Dm", "Dm", "Bb", "A"], 62, picks=(0, 1))
    s.power(8, P, "M.M.M.M.M.M.M.M.", 78)
    s.power(16, P, ["X---------------", "M.M.M.M.X-------"], 82)
    s.drums(16, 8, {"h": "x.x.x.x.x.x.x.x."}, 0.7)
    s.melody(LEAD, 4, "A5:12 Bb5:4  A5:16  -:16 -:16", "fiddle", 86, vib=3)
    s.melody(LEAD, 12, "D5:8 Eb5:8  D5:8 C5:4 Bb4:4  A4:16  C#5:16", "fiddle", 92, vib=3)
    s.melody(LEAD, 20, "D5:8 Eb5:8  F5:8 Eb5:8  D5:16  C#5:16", "lead", 90, vib=3)
    for b in range(0, 24, 4):
        s.note(X, b, 0, 64, "bell", midi("Ab4") if b % 8 else midi("D5"), 46)
    s.echo(LEAD, ECHO, 5, 0.35)
    return s


def joy(bank):
    """The feast: a folk dance (polka) with fiddle, flute, hurdy-gurdy and guitars, G major,
    150 BPM."""
    s = Song(bank, "joy", 6, 44)
    A = ["G", "D", "D", "G", "G", "C", "D", "G"]
    MA = ("B5:2 D6:2 B5:2 G5:2 A5:2 B5:2 G5:4  A5:2 F#5:2 A5:2 D6:2 C6:2 A5:2 F#5:4  "
          "A5:2 C6:2 A5:2 F#5:2 D5:2 F#5:2 A5:4  B5:2 A5:2 G5:2 B5:2 D6:8  "
          "B5:2 D6:2 B5:2 G5:2 A5:2 B5:2 G5:4  C6:2 E6:2 C6:2 G5:2 E5:2 G5:2 C6:4  "
          "B5:2 A5:2 G5:2 F#5:2 A5:2 D6:2 C6:4  B5:4 G5:4 G5:8")
    B = ["C", "G", "D", "G", "C", "G", "A", "D"]
    MB = ("E6:4 D6:2 C6:2 G5:8  D6:4 C6:2 B5:2 G5:8  A5:2 B5:2 C6:2 A5:2 F#5:4 D5:4  G5:4 B5:4 D6:8  "
          "E6:4 D6:2 C6:2 G5:8  D6:4 C6:2 B5:2 G5:8  C#6:2 B5:2 A5:2 G5:2 E5:4 C#5:4  D5:4 F#5:4 A5:8")
    s.note(PAD2, 0, 0, 44 * 16, "drone", midi("G2") + 12, 48, env="drone")
    for b0, sec in [(0, "a"), (8, "a"), (16, "b"), (24, "a"), (32, "b"), (40, "end")]:
        if sec == "a":
            s.drums(b0, 7, POLKA)
            s.drums(b0 + 7, 1, {"k": "x.......x.......", "s": "....s...s.s.S.S.", "h": "..x...x........."})
            s.bass(b0, A, "x...5...x...5...", 104)
            s.arp(b0, A, "..321.....321...", 66, lo=55, env="stac", ring=2)
            s.melody(LEAD, b0, MA, "fiddle", 106, vib=1)
            if b0 >= 8:
                s.melody(PAD1, b0, MA, "flute", 80, transpose=-12 + 12, vib=0)
            if b0 == 24:
                s.power(b0, A, "X.......X.......", 80)
        elif sec == "b":
            s.drums(b0, 7, ROCK)
            s.drums(b0 + 7, 1, FILL)
            s.drums(b0, 1, {"c": "x..............."})
            s.bass(b0, B, "x.x.5.x.x.x.5.x.", 106)
            s.power(b0, B, "X---M.M.X---M.M.", 88)
            s.melody(LEAD, b0, MB, "fiddle", 106, vib=1)
            s.melody(PAD1, b0, MB, "lead", 84, transpose=-12)
        else:
            s.drums(b0, 3, POLKA)
            s.drums(b0 + 3, 1, FILL16)
            s.bass(b0, ["G", "C", "D", "D"], "x.5.x.5.x.5.x.5.", 104)
            s.power(b0, ["G", "C", "D", "D"], "X---X---X-X-X-X-", 88)
            s.melody(LEAD, b0, "G5:2 B5:2 D6:2 G6:2 D6:2 B5:2 G5:4  E5:2 G5:2 C6:2 E6:2 C6:2 G5:2 E5:4  "
                     "F#5:2 A5:2 D6:2 F#6:2 D6:2 A5:2 F#5:4  D6:2 C6:2 B5:2 A5:2 G5:2 F#5:2 E5:2 D5:2", "fiddle", 106, vib=1)
    s.echo(LEAD, ECHO, 3, 0.25)
    return s


SONGS = [title, battle, wroclaw, sleza, krakow, boss, dragon, calm, tension, joy]


def build(bank):
    return [f(bank) for f in SONGS]
