"""The four story scenes, shot by shot (docs/STORY.md) -> src/gen/scene_text.h for src/scenes.h.

    python tools/scenes/script.py

A scene is a list of shots. A shot has a backdrop (or black), a camera pan, actors, an optional
caption (top bar), lines (bottom bar: speaker and words, typed), labels (text placed on the
picture), the music mood and effects (shake, flash, chapter card frame). Positions are backdrop
pixels: x 0..680, y on screen (the backdrop's top is y 40, the actors' ground y 300); actors
flagged `screen` ignore the pan. Times are frames from the start of the shot (60 a second), or
from the start of line `on_line` for actors that wait for it.

Text goes through assetlib.c_string, so Polish letters get the font's codes; every line and
caption is checked against the font's advances to fit the screen.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from assetlib import ROOT, _atomic_write, char_code  # noqa: E402

META = json.loads((ROOT / "assets/scenes/meta.json").read_text(encoding="utf-8"))
STRIDE = META["stride"]
ANCHOR = META["anchors"]
GROUND = 300

# actor modes and flags, as in src/scenes.h
STILL, WALK, LOOP, ONCE, BUST = 0, 1, 2, 3, 4
FLIP, ADD, SCREEN, ORBIT = 1, 2, 4, 8
WHITE = 0xFFFFFFFF


def abgr(r, g, b, a=255):
    """The console's colour word: alpha, blue, green, red."""
    return (a << 24) | (b << 16) | (g << 8) | r


SPEAKERS = {   # name EN, PL, colour of the name
    "HERALD": ("HERALD", "HEROLD", abgr(240, 200, 80)),
    "DRATEWKA": ("DRATEWKA", "DRATEWKA", abgr(255, 120, 90)),
    "UTOPIEC": ("UTOPIEC", "UTOPIEC", abgr(110, 220, 160)),
    "WANDA": ("WANDA", "WANDA", abgr(130, 180, 255)),
    "JAGA": ("BABA JAGA", "BABA JAGA", abgr(170, 240, 90)),
    "KRAK": ("KRAK", "KRAK", abgr(250, 210, 90)),
}
SPEAKER_IDS = list(SPEAKERS)

SONG = {None: -1, "calm": "SONG_CALM", "tension": "SONG_TENSION", "joy": "SONG_JOY"}


def act(spr, x, y, x1=None, y1=None, t0=0, t1=0, arc=0, show=0, hide=-1, mode=STILL, f0=0, n=1, rate=0,
        idle=None, left=None, add=False, screen=False, attach=None, s0=100, s1=None, c0=WHITE, c1=None,
        talker=None, on_line=-1, orbit=None):
    x1 = x if x1 is None else x1
    y1 = y if y1 is None else y1
    if left is None:
        left = x1 < x
    flags = (FLIP if left else 0) | (ADD if add else 0) | (SCREEN if screen else 0)
    if orbit:   # (rx, ry, period, phase in degrees): circling (x, y)
        flags |= ORBIT
        x1, y1, t1, t0 = orbit
    return dict(spr=spr, x0=x, y0=y, x1=x1, y1=y1, t0=t0, t1=t1, arc=arc, show=show, hide=hide, mode=mode,
                f0=f0, n=n, rate=rate, idle=f0 if idle is None else idle, stride=STRIDE.get(spr, 64),
                flags=flags, attach=attach, s0=s0, s1=s0 if s1 is None else s1, c0=c0, c1=c0 if c1 is None else c1,
                talker=-1 if talker is None else SPEAKER_IDS.index(talker), on_line=on_line)


def walker(spr, x0, x1, t0=0, speed=1.6, y=GROUND, idle=8, **kw):
    """Walks from x0 to x1 at `speed` px a frame, then stands (frame `idle`)."""
    t1 = t0 + round(abs(x1 - x0) / speed)
    return act(spr, x0, y, x1, y, t0, t1, mode=WALK, f0=0, n=8, idle=idle, **kw)


def bust(spr, x, talker, left=False, **kw):
    return act(spr, x, 320, mode=BUST, talker=talker, left=left, screen=True, **kw)


def once(spr, x, y, t, rate=4, **kw):
    n = {"boom": 6, "smoke": 6, "firework": 5}[spr]
    return act(spr, x, y, show=t, hide=t + n * rate, mode=ONCE, n=n, rate=rate, **kw)


def loop(spr, x, y, n, rate, **kw):
    return act(spr, x, y, mode=LOOP, n=n, rate=rate, **kw)


def grazing(x, y=GROUND, left=False, rate=24, **kw):
    return act("sheep", x, y, mode=LOOP, f0=8, n=2, rate=rate, left=left, **kw)


def shot(bd=None, length=240, pan=(0, 0), cap=None, song=None, lines=(), lines_at=30, actors=(), labels=(),
         card=False, shake=-1, flash=-1, dim=WHITE):
    return dict(bd=bd, len=length, pan=pan, cap=cap, song=song, lines=list(lines), lines_at=lines_at,
                actors=list(actors), labels=list(labels), card=card, shake=shake, flash=flash, dim=dim)


def label(en, pl, x, y, color=WHITE, big=False, t=0):
    return dict(en=en, pl=pl, x=x, y=y, color=color, big=big, t=t)


INK = abgr(70, 40, 24)


def card(roman, name_en, name_pl, emblem):
    """A chapter card on black: the gilded frame, CHAPTER n, the name typed big, its foe."""
    return shot(None, 210, card=True, labels=[
        label(f"CHAPTER {roman}", f"ROZDZIAŁ {roman}", 320, 92, abgr(230, 200, 120)),
        label(name_en, name_pl, 320, 120, WHITE, True, 20)], actors=[emblem])


def fireworks():
    out = []
    spots = [(190, 90), (420, 70), (300, 120), (520, 110), (120, 70), (360, 60), (470, 140), (230, 60),
             (560, 70), (300, 90), (160, 120), (420, 100)]
    tints = [abgr(255, 120, 120), abgr(140, 255, 140), abgr(255, 230, 120), abgr(140, 170, 255),
             abgr(255, 150, 240), abgr(255, 255, 255)]
    for k, (x, y) in enumerate(spots * 2):
        t = 20 + k * 19
        out.append(act("spark", x, 300, x + 4, y + 50, t - 26, t, show=t - 26, hide=t, mode=LOOP, n=4, rate=3,
                       add=True))
        out.append(once("firework", x + 4, y + 50, t, rate=7, add=True, c0=tints[k % len(tints)]))
    return out


# ---------------------------------------------------------------------------
#   the scenes
# ---------------------------------------------------------------------------

def scene_wroclaw():
    meadow = ANCHOR["wawel_night"]["meadow"][0]
    board_x, board_y = ANCHOR["rynek"]["board"][0], ANCHOR["rynek"]["board"][1] + 40
    # the dragon sweeps down over the pasture and takes a sheep on its way
    grab_x, dragon_t0, dragon_t1 = 360, 30, 300
    dragon = act("dragon_fly", -160, 70, 880, 60, dragon_t0, dragon_t1, arc=-150, mode=LOOP, n=4, rate=7)
    k = (grab_x + 160) / 1040
    grab_t = round(dragon_t0 + k * (dragon_t1 - dragon_t0))
    s1 = [
        dragon,
        grazing(meadow - 60),
        grazing(meadow + 40, left=True, rate=30),
        grazing(grab_x, hide=grab_t),
        # the carried sheep hangs under the dragon (attach: offset from actor 0 of the shot)
        act("sheep", 0, 52, show=grab_t, attach=0),
    ]
    shots = [
        shot("wawel_night", 330, (0, 40), ("KRAKOW, BY NIGHT", "KRAKÓW, NOCĄ"), "tension", actors=s1),
        shot("rynek", 300, (0, 30), ("WROCLAW, MORNING", "WROCŁAW, RANO"), "calm", lines_at=230,
             lines=[("HERALD", "Hear ye! The king seeks a dragon slayer!", "Słuchajcie! Król szuka pogromcy smoka!")],
             actors=[
                 walker("herald", -50, board_x - 42, 10, hide=180),
                 loop("herald", board_x - 42, GROUND, 2, 9, f0=8, show=180, hide=226),
                 act("herald", board_x - 42, GROUND, f0=9, show=226),
                 act("poster", board_x, board_y, show=196),
             ]),
        shot("rynek", 280, dim=abgr(96, 96, 96), actors=[act("poster_big", 320, 182, screen=True)], labels=[
            label("Dragon!", "Smok!", 320, 94, INK, True),
            label("REWARD:", "NAGRODA:", 320, 224, abgr(250, 220, 150)),
            label("HALF THE KINGDOM", "PÓŁ KRÓLESTWA", 320, 244, abgr(250, 220, 150))]),
        shot("rynek", 300, (30, 40), actors=[
            act("poster", board_x, board_y),
            walker("dratewka", 720, board_x + 66, 0, idle=8, left=True),
            loop("spark", board_x + 62, 168, 4, 4, show=250, add=True),
        ]),
        shot("rynek", 120, (40, 40), dim=abgr(150, 150, 150), lines_at=20,
             lines=[("DRATEWKA", "A dragon? I know just the thing: sulphur!", "Smok? Mam na niego sposób: siarka!")],
             actors=[bust("bust_dratewka", 300, "DRATEWKA"), loop("spark", 370, 170, 4, 4, add=True, screen=True)]),
        shot("workshop", 300, (0, 20), song="calm", shake=150, flash=150, actors=[
            act("dratewka", 300, GROUND, f0=11, hide=150),
            act("dratewka", 300, GROUND, f0=8, show=150, c0=abgr(90, 80, 80)),
            act("sack", 372, GROUND),
            act("sheep", 450, GROUND, left=True, hide=152),
            loop("spark", 474, 262, 4, 3, show=60, hide=150, add=True),
            once("boom", 450, 262, 150, rate=5),
            once("smoke", 430, 240, 170, rate=8),
            once("smoke", 470, 250, 182, rate=8),
        ]),
        shot("workshop", 120, (20, 20), dim=abgr(110, 100, 100), lines_at=40,
             lines=[("DRATEWKA", "...less sulphur next time.", "...następnym razem mniej siarki.")],
             actors=[bust("bust_dratewka_soot", 320, "DRATEWKA"), loop("soot", 330, 200, 3, 10, screen=True)]),
        shot("odra", 330, (40, 0), ("THE ODER", "ODRA"), "tension", shake=70, actors=[
            act("utopiec", 360, 450, 360, 334, 70, 170, f0=1, hide=170),
            act("utopiec", 360, 334, f0=0, show=170),
            once("smoke", 360, 300, 70, rate=6, c0=abgr(140, 200, 255)),
            once("smoke", 330, 306, 82, rate=6, c0=abgr(140, 200, 255)),
            once("smoke", 395, 304, 94, rate=6, c0=abgr(140, 200, 255)),
        ]),
        shot("odra", 120, (0, 0), dim=abgr(150, 150, 170), lines_at=20,
             lines=[("UTOPIEC", "No one crosses the Oder!", "Nikt nie przejdzie przez Odrę!")],
             actors=[bust("bust_utopiec", 330, "UTOPIEC", left=True)]),
        card("I", "Wroclaw", "Wrocław", act("utopiec", 320, 280, f0=0, screen=True, show=40, s0=80)),
    ]
    return shots


def witches(center, until=-1):
    cx, cy = center
    return [act("witch", cx, cy, orbit=(110, 16, 150, 0), mode=LOOP, n=2, rate=12, hide=until),
            act("witch", cx, cy, orbit=(110, 16, 150, 180), mode=LOOP, n=2, rate=12, hide=until)]


def scene_sleza():
    fire_x, fire_y = ANCHOR["sleza"]["fire"][0], ANCHOR["sleza"]["fire"][1] + 40
    flame = loop("flame", fire_x, fire_y + 2, 4, 6)
    wanda_x = fire_x + 90
    jaga_at = (fire_x - 70, 170)
    jaga_hover = act("jaga", jaga_at[0], jaga_at[1], orbit=(4, 8, 90, 0), mode=LOOP, n=2, rate=20, left=False)
    shots = [
        shot("sleza", 330, (0, 40), ("MOUNT SLEZA, KUPALA NIGHT", "ŚLĘŻA, NOC KUPAŁY"), "calm", actors=[
            flame, walker("dratewka", -40, 250, 20)]),
        shot("sleza", 240, (40, 40), song="tension", lines_at=110,
             lines=[("WANDA", "Let me go, you old hags!", "Puśćcie mnie, wiedźmy!")],
             actors=[flame, act("wanda", wanda_x, GROUND, f0=9, left=True), loop("magic", wanda_x, 240, 4, 6, add=True),
                     dict(jaga_hover, hide=-1), *witches((wanda_x, 220))]),
        shot("sleza", 260, (40, 40), shake=80, actors=[
            flame,
            act("dratewka", 300, GROUND, f0=9, hide=30),
            act("dratewka", 300, GROUND, f0=10, show=30),
            act("bomb", 330, 200, wanda_x - 70, 262, 30, 80, arc=90, hide=80),
            once("boom", wanda_x - 70, 250, 80, rate=5),
            act("wanda", wanda_x, GROUND, f0=9, left=True, hide=84),
            act("wanda", wanda_x, GROUND, f0=8, left=True, show=84),
            loop("magic", wanda_x, 240, 4, 6, add=True, hide=80),
            dict(jaga_hover, hide=96),
            *witches((wanda_x, 220), 84),
            act("witch", wanda_x - 100, 220, -140, 60, 84, 170, mode=LOOP, n=2, rate=6, show=84),
            act("witch", wanda_x + 100, 220, 860, 30, 84, 170, mode=LOOP, n=2, rate=6, show=84),
            act("jaga", jaga_at[0], jaga_at[1], 900, -40, 96, 230, mode=LOOP, n=2, rate=8, show=96),
            once("smoke", wanda_x - 80, 230, 100, rate=8),
        ]),
        shot("sleza", 100, (40, 40), dim=abgr(120, 140, 120), flash=0, lines_at=20,
             lines=[("JAGA", "The dragon will hear of you!", "Smok o was usłyszy!")],
             actors=[loop("magic", 430, 210, 4, 6, add=True, screen=True), bust("bust_jaga", 440, "JAGA", left=True)]),
        shot("sleza", 100, (40, 40), dim=abgr(150, 140, 130), lines_at=20,
             lines=[("WANDA", "I had them.", "Dałabym sobie radę.")],
             actors=[bust("bust_wanda", 360, "WANDA", left=True)]),
        shot("sleza", 270, (20, 40), song="calm", actors=[
            flame, walker("dratewka", 300, 780, 20), walker("wanda", wanda_x, 780, 70, speed=1.4)]),
        card("II", "Mount Sleza", "Ślęża", act("jaga", 320, 226, mode=LOOP, n=2, rate=20, screen=True, show=40, s0=80)),
    ]
    return shots


def scene_krakow():
    tx, ty = ANCHOR["krakow"]["tower_top"][0], ANCHOR["krakow"]["tower_top"][1] + 40
    cave_x = ANCHOR["den"]["cave"][0]
    meadow = ANCHOR["den"]["meadow"][0]
    dragon_x = cave_x - 10
    hit1, hit2 = 66, 176
    shots = [
        shot("krakow", 360, (0, 40), ("KRAKOW, AT DUSK", "KRAKÓW, O ZMIERZCHU"), "tension", shake=200, actors=[
            loop("spark", tx + 2, ty - 6, 4, 5, show=20, hide=150, add=True),
            act("dragon_fly", -150, 170, 860, 130, 130, 330, arc=30, mode=LOOP, n=4, rate=6),
        ]),
        shot("den", 300, (40, 40), actors=[
            act("dragon", dragon_x, GROUND, left=True, f0=0),
            act("dragon", dragon_x, GROUND, left=True, f0=1, show=hit1, hide=hit1 + 40),
            act("dragon", dragon_x, GROUND, left=True, f0=1, show=hit2, hide=hit2 + 40),
            act("wanda", 200, GROUND, f0=8, left=False),
            act("dratewka", 260, GROUND, f0=9, hide=24),
            act("dratewka", 260, GROUND, f0=10, show=24, hide=110),
            act("dratewka", 260, GROUND, f0=9, show=110, hide=134),
            act("dratewka", 260, GROUND, f0=10, show=134),
            act("bomb", 285, 200, dragon_x - 60, 210, 24, hit1, arc=60, hide=hit1),
            act("bomb", dragon_x - 60, 210, dragon_x - 150, 292, hit1, hit1 + 30, arc=40, show=hit1, hide=hit1 + 32),
            loop("spark", dragon_x - 60, 210, 4, 3, show=hit1, hide=hit1 + 12, add=True),
            once("smoke", dragon_x - 150, 285, hit1 + 30, rate=6),
            act("bomb", 285, 200, dragon_x - 40, 190, 134, hit2, arc=60, hide=hit2),
            act("bomb", dragon_x - 40, 190, dragon_x - 130, 292, hit2, hit2 + 30, arc=50, show=hit2, hide=hit2 + 32),
            loop("spark", dragon_x - 40, 190, 4, 3, show=hit2, hide=hit2 + 12, add=True),
            once("smoke", dragon_x - 130, 285, hit2 + 30, rate=6),
        ]),
        shot("den", 100, (40, 40), dim=abgr(140, 140, 140), lines_at=20,
             lines=[("WANDA", "Sulphur won't hurt it!", "Siarka go nie bierze!")],
             actors=[bust("bust_wanda", 300, "WANDA")]),
        shot("den", 280, (0, 0), song="calm", actors=[
            grazing(meadow - 70),
            grazing(meadow + 40, left=True, rate=30),
            act("sheep", meadow - 20, GROUND + 4, meadow + 110, GROUND + 4, 20, 160, mode=WALK, n=8, idle=8),
            walker("dratewka", 700, meadow + 220, 10, left=True),
        ]),
        shot("den", 120, (0, 0), dim=abgr(150, 150, 150), lines_at=20,
             cap=("CATCH A SHEEP, PRESS B TO SEND IT", "ZŁAP OWCĘ, B PUSZCZA JĄ DO SMOKA"),
             lines=[("DRATEWKA", "But a sheep full of it will.", "Ale owca z siarką - tak.")],
             actors=[grazing(130, rate=30), bust("bust_dratewka", 380, "DRATEWKA", left=True)]),
        card("III", "Krakow", "Kraków", act("dragon_fly", 320, 228, mode=LOOP, n=4, rate=8, screen=True, show=40, s0=90)),
    ]
    return shots


def scene_ending():
    cave_x = ANCHOR["den"]["cave"][0]
    river_x = ANCHOR["den"]["river"][0]
    dx = cave_x - 10
    red = abgr(255, 90, 60)
    eat, drink_at, drink_x, swell, bang = 150, 300, river_x + 120, 370, 440
    shots = [
        shot("den", 500, (40, 0), song="tension", shake=bang, flash=bang, actors=[
            act("dragon", dx, GROUND, left=True, f0=0, hide=eat - 10),
            act("dragon", dx, GROUND, left=True, f0=1, show=eat - 10, hide=eat + 30),
            act("dragon", dx, GROUND, dx, GROUND, eat + 30, drink_at - 70, left=True, f0=0, c1=red,
                show=eat + 30, hide=drink_at - 50),
            act("dragon", dx, GROUND, drink_x, GROUND, drink_at - 50, drink_at, left=True, f0=0, c0=red,
                show=drink_at - 50, hide=drink_at),
            act("dragon", drink_x, GROUND, left=True, f0=2, c0=red, show=drink_at, hide=swell),
            act("dragon", drink_x, GROUND, drink_x, GROUND, swell, bang, left=True, f0=0, c0=red,
                c1=abgr(255, 200, 200), s0=100, s1=160, show=swell, hide=bang),
            act("sheep", 40, GROUND, dx - 110, GROUND, 0, eat, mode=WALK, n=8, idle=0, hide=eat),
            loop("spark", 6, -40, 4, 3, attach=6, add=True, hide=eat),
            once("boom", drink_x - 30, 230, bang, rate=6),
            once("boom", drink_x + 40, 200, bang + 8, rate=6),
            once("boom", drink_x, 260, bang + 16, rate=6),
            once("smoke", drink_x, 220, bang + 30, rate=10),
        ]),
        shot("hall", 260, (0, 20), song="joy", actors=[
            act("krak", 340, 292, f0=0),
            walker("wanda", -40, 260, 10),
            walker("dratewka", 720, 430, 0, left=True),
        ]),
        shot("hall", 100, (20, 20), dim=abgr(140, 130, 120), lines_at=20,
             lines=[("KRAK", "Your reward!", "Twoja nagroda!"),
                    ("WANDA", "Half the kingdom, father.", "Pół królestwa, ojcze."),
                    ("KRAK", "Half the cheese?", "Pół sera?")],
             actors=[bust("bust_krak", 200, "KRAK"), bust("bust_wanda", 450, "WANDA", left=True)]),
        shot("hall", 200, (20, 20), actors=[
            act("krak", 340, 292, f0=1),
            act("wanda", 260, GROUND, f0=8),
            act("dratewka", 430, GROUND, f0=8, left=True),
            act("cheese", 385, 222, 410, 224, 30, 80, arc=50),
            loop("spark", 412, 214, 4, 5, show=80, hide=130, add=True),
        ]),
        shot("wawel_night", 520, (0, 20), labels=[label("The End", "Koniec", 320, 176, WHITE, True, 300)],
             actors=[*fireworks(),
                     act("wanda", 140, GROUND, f0=8), act("dratewka", 190, GROUND, f0=8),
                     grazing(240, rate=30)]),
    ]
    return shots


SCENES = [scene_wroclaw(), scene_sleza(), scene_krakow(), scene_ending()]

# ---------------------------------------------------------------------------
#   C tables
# ---------------------------------------------------------------------------


def font_widths():
    text = (ROOT / "src/gen/font_metrics.h").read_text(encoding="utf-8")
    adv = [int(v) for v in re.search(r"font_body_adv = \{([^}]*)\}", text).group(1).split(",")]
    big = [int(v) for v in re.search(r"font_title_adv = \{([^}]*)\}", text).group(1).split(",")]

    def width(s, table):
        w = 0
        for ch in s:
            c = char_code(ch)
            g = c - 32 if c <= 126 else c - 33
            w += table[g]
        return w
    return lambda s: width(s, adv), lambda s: width(s, big)


def main():
    width, width_big = font_widths()
    strings, chars = [], []

    def string(en, pl):
        for s in (en, pl):
            strings.append(len(chars))
            chars.extend(char_code(ch) for ch in s)
            chars.append(0)
        return len(strings) // 2 - 1

    spk = [(string(en, pl), col) for (en, pl, col) in SPEAKERS.values()]
    shots, actors, lines, labels = [], [], [], []
    scene_first = []
    problems = []
    for scene in SCENES:
        scene_first.append(len(shots))
        for sh in scene:
            a0 = len(actors)
            for a in sh["actors"]:
                a = dict(a)
                if a["attach"] is not None:
                    a["attach"] += a0
                actors.append(a)
            l0 = len(lines)
            for who, en, pl in sh["lines"]:
                name_w = max(width(SPEAKERS[who][0]), width(SPEAKERS[who][1]))
                for s in (en, pl):
                    if 16 + name_w + 12 + width(s) > 628:
                        problems.append(f"line too wide: {s!r}")
                lines.append((SPEAKER_IDS.index(who), string(en, pl)))
            b0 = len(labels)
            for lb in sh["labels"]:
                w = width_big if lb["big"] else width
                if max(w(lb["en"]), w(lb["pl"])) > 600:
                    problems.append(f"label too wide: {lb['en']!r}")
                labels.append((string(lb["en"], lb["pl"]), lb))
            cap = -1
            if sh["cap"]:
                if max(width(sh["cap"][0]), width(sh["cap"][1])) > 620:
                    problems.append(f"caption too wide: {sh['cap'][0]!r}")
                cap = string(*sh["cap"])
            bd = f"SCENES_BD_{sh['bd'].upper()}" if sh["bd"] else "-1"
            shots.append(dict(bd=bd, pan0=sh["pan"][0], pan1=sh["pan"][1], len=sh["len"], cap=cap,
                              song=SONG[sh["song"]], line0=l0, lines=len(lines) - l0, lines_at=sh["lines_at"],
                              actor0=a0, actors=len(actors) - a0, label0=b0, labels=len(labels) - b0,
                              card=int(sh["card"]), shake=sh["shake"], flash=sh["flash"], dim=sh["dim"]))
    if problems:
        sys.exit("\n".join(problems))

    def arr(name, values):
        vals = [str(v) if not isinstance(v, int) or v < 0x80000000 else str(v - (1 << 32)) for v in values]
        body = ", ".join(vals) if vals else "0"
        return f"int[ {max(1, len(vals))} ] {name} = {{ {body} }};"

    def sprite(name):
        return f"SCENES_{name.upper()}"

    out = ["// generated by tools/scenes/script.py: do not edit", "#ifndef GEN_SCENE_TEXT_H",
           "#define GEN_SCENE_TEXT_H", '#include "scenes.h"', "",
           f"#define SCENE_COUNT {len(SCENES)}", f"#define SCENE_SHOTS {len(shots)}",
           f"#define SCENE_ACTORS {len(actors)}", "",
           "// texts: EN at 2 * id, PL at 2 * id + 1 in scene_str_at", arr("scene_chars", chars),
           arr("scene_str_at", strings), "",
           arr("speaker_name", [s for s, _ in spk]), arr("speaker_color", [c for _, c in spk]), "",
           arr("scene_first", scene_first + [len(shots)]), ""]
    for key in ("bd", "pan0", "pan1", "len", "cap", "song", "line0", "lines", "lines_at", "actor0", "actors",
                "label0", "labels", "card", "shake", "flash", "dim"):
        out.append(arr(f"shot_{key}", [s[key] for s in shots]))
    out.append("")
    out.append(arr("line_who", [w for w, _ in lines]))
    out.append(arr("line_text", [t for _, t in lines]))
    out.append(arr("label_text", [s for s, _ in labels]))
    for key in ("x", "y", "color", "big", "t"):
        out.append(arr(f"label_{key}", [int(lb[key]) for _, lb in labels]))
    out.append("")
    for key in ("spr", "x0", "y0", "x1", "y1", "t0", "t1", "arc", "show", "hide", "mode", "f0", "n", "rate", "idle",
                "stride", "flags", "attach", "s0", "s1", "c0", "c1", "talker", "on_line"):
        vals = []
        for a in actors:
            v = a[key]
            if key == "spr":
                v = sprite(v)
            elif key == "attach":
                v = -1 if v is None else v
            vals.append(v)
        out.append(arr(f"actor_{key}", vals))
    out += ["", "#endif", ""]
    _atomic_write(ROOT / "src/gen/scene_text.h", "\n".join(out))
    total = 0
    for k, scene in enumerate(SCENES):
        frames = sum(sh["len"] for sh in scene)
        total += frames
        print(f"scene {k}: {len(scene)} shots, at least {frames / 60:.1f} s")
    print(f"scene_text.h: {len(shots)} shots, {len(actors)} actors, {len(lines)} lines, {len(chars)} chars")


if __name__ == "__main__":
    main()
