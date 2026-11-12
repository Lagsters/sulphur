"""The "done" gate: the exit code is the result.

    python tools/check.py           build the game and the test programs, run the logic tests,
                                    a short bot simulation and the performance checks
    python tools/check.py --sim     the long simulation instead (400 battle rounds, every
                                    stage of the story three times)
    python tools/check.py --clean   also wipe build/ first (CI starts clean anyway)

Test programs (tests/*.c) run on the real console code in the headless runner; they leave their
results on a memory card (tests/harness.h has the layout), which this script reads.
Failures listed in tests/KNOWN_FAILURES.md are reported apart and do not fail the gate; a known
failure that passes again is reported so the list can be trimmed.
"""
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toolchain import ROOT, tools  # noqa: E402

BUILD = ROOT / "build"
TESTS = ROOT / "tests"
CARD_WORDS = 262144                     # Constants::MemoryCardSize
CARD_RESULT, CARD_FAILS, CARD_STATS = 1024, 2048, 8192
RESULT_MAGIC = 1398096979
FRAME_CYCLES = 250000

# test programs: source in tests/, ROM name in build/ (prefixed, not to clash with other builds)
PROGRAMS = {"logic": "t_logic", "sim": "t_sim", "perf": "t_perf", "probe": "t_probe"}

problems = []          # what fails the gate
known_hits = []        # failures listed in tests/KNOWN_FAILURES.md
notes = []             # summary lines


def say(text):
    print(text, flush=True)


# ---------------------------------------------------------------------------
#   building and running
# ---------------------------------------------------------------------------

def build(program=None, name=None):
    cmd = [sys.executable, str(ROOT / "tools/build.py")] + ([program, name] if program else [])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f"FAIL: build of {program or 'the game'}\n{result.stdout}{result.stderr}")
    return BUILD / f"{name or 'sulphur'}.v32"


def write_card(path, inputs=()):
    words = [0] * CARD_WORDS
    for i, v in enumerate(inputs):
        words[i] = v
    path.write_bytes(b"V32-MEMC" + struct.pack(f"<{CARD_WORDS}i", *words))


def read_card(path):
    data = path.read_bytes()
    if data[:8] != b"V32-MEMC":
        raise ValueError(f"{path}: not a memory card")
    return struct.unpack(f"<{CARD_WORDS}i", data[8:8 + 4 * CARD_WORDS])


def card_string(words, at):
    out = []
    while words[at] != 0:
        out.append(chr(words[at]))
        at += 1
    return "".join(out), at + 1


def run_rom(rom, frames, card=None, skiplog=False, timeout=3600):
    """Runs a ROM headless; returns (runner summary dict, skipped frame numbers)."""
    t = tools()
    env = dict(os.environ)
    for key in ("INPUT_SCRIPT", "AUDIO_OUT", "FRAME_FROM", "FRAME_TO", "MEMCARD", "SKIPLOG", "GAMEPADS"):
        env.pop(key, None)
    if card:
        env["MEMCARD"] = str(card)
    if skiplog:
        env["SKIPLOG"] = "1"
    result = subprocess.run([str(t["runner"]), str(t["bios"]), str(rom), str(BUILD), str(frames), "0"],
                            capture_output=True, text=True, env=env, timeout=timeout)
    summary = {}
    for item in result.stdout.split():
        if "=" in item:
            k, v = item.split("=", 1)
            summary[k] = int(v)
    skips = [int(m) for m in re.findall(r"^skip (\d+)", result.stderr, re.M)]
    if "frames" not in summary:
        raise RuntimeError(f"runner failed on {rom.name}: {result.stderr[-2000:]}")
    return summary, skips


# ---------------------------------------------------------------------------
#   logic tests
# ---------------------------------------------------------------------------

def known_failures():
    """Names in backticks in the first column of the table in tests/KNOWN_FAILURES.md."""
    path = TESTS / "KNOWN_FAILURES.md"
    if not path.exists():
        return set()
    return set(re.findall(r"^\|\s*`([^`]+)`", path.read_text(encoding="utf-8"), re.M))


def fail(key, message):
    """A failure; keys listed in tests/KNOWN_FAILURES.md are known and do not fail the gate."""
    if key in known_failures():
        known_hits.append(message)
    else:
        problems.append(message)


def logic_tests(rom):
    card = BUILD / "t_logic.card"
    write_card(card)
    summary, _ = run_rom(rom, 400000, card)
    words = read_card(card)
    if words[CARD_RESULT] != RESULT_MAGIC:
        problems.append("logic tests: no results on the card (the program did not start)")
        return
    run, failed = words[CARD_RESULT + 2], words[CARD_RESULT + 3]
    fails, at = [], CARD_FAILS
    for _ in range(failed):
        name, at = card_string(words, at)
        note, at = card_string(words, at)
        fails.append((name, note))
    if words[CARD_RESULT + 1] != 1:
        current, _ = card_string(words, CARD_RESULT + 8)
        problems.append(f"logic tests stopped in '{current}' after {summary['frames']} frames "
                        f"(halted={summary.get('halted')})")
    known = known_failures()
    new = [(n, w) for n, w in fails if n not in known]
    old = [(n, w) for n, w in fails if n in known]
    fixed = sorted(k for k in known - {n for n, _ in fails} if not k.startswith(("sim:", "perf:")))
    say(f"logic tests: {run} run, {run - failed} passed, {len(new)} failed, {len(old)} known failures")
    for n, w in new:
        say(f"  FAIL {n}: {w}")
        fail(n, f"test failed: {n}")
    for n, w in old:
        say(f"  known failure {n}: {w}")
        known_hits.append(f"test: {n}")
    for n in fixed:
        say(f"  known failure passes now (remove it from tests/KNOWN_FAILURES.md): {n}")
    notes.append(f"logic: {run - failed}/{run} passed, {len(new)} new failures, {len(old)} known")


# ---------------------------------------------------------------------------
#   simulations
# ---------------------------------------------------------------------------

VIOLATIONS = {1: "player in a wall or crate", 2: "bomb on a wall or crate",
              3: "owner bomb counter differs from his bombs on the map",
              4: "counter out of range", 5: "two bombs on one cell", 6: "a list is full",
              7: "blast cover out of step with the blasts", 8: "the dragon lost hp without a sheep",
              9: "player's body in a crate or fixed wall"}
CAUSES = ("own blast", "other's blast", "zone", "boss fire", "monster", "boss touch", "sheep blast",
          "skeleton blast")


def chi2_sf_df3(x):
    """Upper tail of the chi-square distribution with 3 degrees of freedom."""
    return math.erfc(math.sqrt(x / 2)) + math.sqrt(2 * x / math.pi) * math.exp(-x / 2)


def run_parallel(jobs):
    workers = max(1, min(len(jobs), (os.cpu_count() or 2) - 1))
    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(lambda job: job(), jobs))


def sim_job(rom, index, inputs, frames):
    def job():
        card = BUILD / f"t_sim_{index}.card"
        try:
            write_card(card, inputs)
            run_rom(rom, frames, card)
            return read_card(card)
        finally:
            card.unlink(missing_ok=True)
    return job


def violations_of(words, base, label, found):
    count = words[CARD_STATS + base]
    for k in range(min(count, 40)):
        at = CARD_STATS + base + 1 + 4 * k
        rnd, frame, code, who = words[at:at + 4]
        found.append(f"{label} {rnd} frame {frame}: {VIOLATIONS.get(code, code)} (player {who})")
    return count


def battle_sim(rom, rounds, cap=12000):
    per_job = 4
    # a game frame that overruns its cycles takes two console frames: room for that
    jobs = [sim_job(rom, j, [0, 1000 + j, per_job, cap], 3 * per_job * cap + 400)
            for j in range((rounds + per_job - 1) // per_job)]
    wins, draws, timeouts, frames, done, causes, viol = [0] * 4, 0, 0, 0, 0, [0] * 8, 0
    longest, found, console_frames, game_frames = 0, [], 0, 0
    for words in run_parallel(jobs):
        s = words[CARD_STATS:CARD_STATS + 40]
        done += s[0]
        for i in range(4):
            wins[i] += s[1 + i]
        draws += s[5]
        timeouts += s[6]
        frames += s[7]
        longest = max(longest, s[8])
        console_frames += s[20]
        game_frames += s[21]
        for i in range(8):
            causes[i] += s[10 + i]
        viol += violations_of(words, 100, "round", found)
    decided = sum(wins)
    chi2 = sum((w - decided / 4) ** 2 / (decided / 4) for w in wins) if decided else 0
    p = chi2_sf_df3(chi2) if decided else 1
    shares = "/".join(f"{100 * w / max(decided, 1):.0f}" for w in wins)
    say(f"battle simulation: {done} rounds, wins by corner TL/TR/BL/BR {wins[0]}/{wins[1]}/{wins[2]}/{wins[3]} "
        f"({shares}%), chi2={chi2:.2f} p={p:.3f}, draws {draws}, rounds at the {cap}-frame limit {timeouts}, "
        f"average {frames / max(done, 1):.0f} frames (longest {longest})")
    say("  deaths: " + ", ".join(f"{c} {n}" for c, n in zip(CAUSES, causes) if n))
    say(f"  game frames over the cycle budget (bots only, no drawing): {console_frames - game_frames} "
        f"of {game_frames}")
    say(f"  invariant violations: {viol}")
    for f in found[:10]:
        say(f"    {f}")
    if viol:
        fail("sim:battle invariants", f"battle simulation: {viol} invariant violations")
    if done < rounds:
        problems.append(f"battle simulation: only {done} of {rounds} rounds finished")
    if timeouts:
        fail("sim:battle rounds that never end", f"battle simulation: {timeouts} rounds hit the frame limit")
    notes.append(f"battle sim: {done} rounds, corner p={p:.3f}, draws {draws}, avg {frames / max(done, 1):.0f} frames")


def campaign_sim(rom, stages, tries, cap):
    jobs = [sim_job(rom, 100 + n, [1, 7, n, cap, n, tries], 3 * tries * cap + 400) for n in stages]
    say(f"story simulation: hero bots, {tries} tries per stage, {cap} frames each (the sim lets "
        "a hero bot carrying a sheep let it go at the dragon)")
    say("  stage  clears  dead  timeout  avg s  overruns  deaths")
    passable, viol, found = 0, 0, []
    for n, words in zip(stages, run_parallel(jobs)):
        s = words[CARD_STATS:CARD_STATS + 40]
        clears, dead, timeouts, clear_frames = s[1], s[2], s[3], s[4]
        why = ", ".join(f"{c} {k}" for c, k in zip(CAUSES, s[10:18]) if k)
        say(f"  {n:5d}  {clears}/{tries}     {dead:4d}  {timeouts:7d}  {clear_frames / max(clears, 1) / 60:5.1f}  "
            f"{s[20] - s[21]:8d}  {why}")
        if s[0] < tries:
            problems.append(f"story simulation: stage {n} finished only {s[0]} of {tries} tries")
        passable += clears > 0
        viol += violations_of(words, 100, f"stage {n} try", found)
    say(f"  stages cleared at least once: {passable}/{len(stages)}; invariant violations: {viol}")
    for f in found[:10]:
        say(f"    {f}")
    if viol:
        fail("sim:story invariants", f"story simulation: {viol} invariant violations")
    notes.append(f"story sim: {passable}/{len(stages)} stages cleared at least once, {viol} violations")


# ---------------------------------------------------------------------------
#   performance
# ---------------------------------------------------------------------------

def first_program_frame(probe):
    """The frame the cartridge's main() starts in: the probe halts at once."""
    summary, _ = run_rom(probe, 2000)
    return summary["frames"] - 1


def perf(game, perf_rom, probe, seconds):
    start = first_program_frame(probe)
    say(f"performance: a program starts in frame {start} (after the BIOS logo); every frame after it checked")
    # the title screen, then the battle demo it starts after TITLE_IDLE frames idle
    title_idle = 1800
    _, skips = run_rom(game, start + title_idle + 60 * seconds, skiplog=True)
    late = [f for f in skips if f >= start]
    say(f"  game ROM, {title_idle // 60} s of title then {seconds} s of the demo: {len(late)} skipped frames {late[:10]}")
    if late:
        fail("perf:game ROM", f"game ROM skips {len(late)} frames")
    for mode, label, key in ((0, "battle, four bots", "perf:battle"), (1, "dragon fight, hero bots", "perf:dragon")):
        card = BUILD / f"t_perf_{mode}.card"
        write_card(card, [mode, 60 * seconds])
        _, skips = run_rom(perf_rom, start + 3 * 60 * seconds, card, skiplog=True)
        words = read_card(card)
        card.unlink()
        s = words[CARD_STATS:CARD_STATS + 8]
        # skip numbers are runner frames, one less than the console's frame counter (s[5] is the
        # console's at measured frame 1). Frame 1 sets the scene up (its overrun lands on runner
        # frame s[5]) and is reported apart; the last measured frame is runner frame s[5] + s[0] - 2,
        # and the one after it halts.
        late = [f for f in skips if s[5] < f <= s[5] + s[0] - 2]
        say(f"  {label}: {len(late)} skipped frames {late[:8]}, worst frame {s[1]} cycles "
            f"({100 * s[1] / FRAME_CYCLES:.0f}% of {FRAME_CYCLES}) at frame {s[4]}, average {s[2]}, "
            f"frames over budget {s[3]} of {s[0]}; setting up took {s[6]} cycles")
        if late or s[3]:
            fail(key, f"{label}: {len(late)} skipped frames, {s[3]} frames over the cycle budget")
        notes.append(f"perf {label}: worst {s[1]} cycles, {s[3]} frames over budget")


def main():
    t0 = time.time()
    long_sim = "--sim" in sys.argv
    tools()
    if "--clean" in sys.argv:
        shutil.rmtree(BUILD, ignore_errors=True)
    for name in ["sulphur", *PROGRAMS.values()]:
        (BUILD / f"{name}.v32").unlink(missing_ok=True)
    say("== build")
    game = build()
    roms = {k: build(f"tests/{k}.c", v) for k, v in PROGRAMS.items()}
    say(f"built {game.name} ({game.stat().st_size // 1024} KB) and {', '.join(r.name for r in roms.values())}")
    say("== logic tests")
    logic_tests(roms["logic"])
    say("== simulation")
    if long_sim:
        battle_sim(roms["sim"], 400)
        campaign_sim(roms["sim"], list(range(1, 31)), 3, 7200)
    else:
        battle_sim(roms["sim"], 32)
        campaign_sim(roms["sim"], [1, 4, 5, 11, 20, 23, 30], 1, 7200)
    say("== performance")
    perf(game, roms["perf"], roms["probe"], 60 if long_sim else 30)
    say(f"== summary ({time.time() - t0:.0f} s)")
    for n in notes:
        say(f"  {n}")
    if known_hits:
        say(f"known failures ({len(known_hits)}, tests/KNOWN_FAILURES.md):")
        for k in known_hits:
            say(f"  {k}")
    if problems:
        say("FAIL")
        for p in problems:
            say(f"  {p}")
        sys.exit(1)
    say("OK")


if __name__ == "__main__":
    main()
