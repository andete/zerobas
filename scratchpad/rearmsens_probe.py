#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-REARMSENS -- what actually MOVES `E_rearm_under_held_key_refires`?

`disk/docs/spec-diskcode-eviction.md` 6.6t parked a correlation with no mechanism:
installing an EIGHTEENTH hook in `hook_tab` reproducibly turns
`stop-trap-acceptance`'s `E_rearm_under_held_key_refires` red, at three different
cell addresses, including one no verb ever enters -- while an entry census shows
the machine doing byte-identical work.  That section's own closing advice is the
subject of this probe:

    "doubt `E_rearm_under_held_key_refires` before doubting the hardware: it
     scores 3 against a threshold of 2 where the reference scores 122, so it is
     a one-step-from-red metric, and what it counts is re-fires inside a fixed
     window.  Establish what makes IT move before attributing anything to hook
     installation."

So this probe NEVER changes the ROM.  Every arm runs the SHIPPED zerobas build.
If the flag moves anyway -- under repetition, under the loop length, or under a
sub-frame shift of the key-down instant -- then the 18th-hook correlation is a
property of the measurement and 6.6t's obstacle to step 9 dissolves.

WHY THE TWO MACHINES CANNOT SHARE A NUMBER HERE (from the gate's own header):
the reference latches Ctrl-STOP at interrupt time and re-latches it on every
scan while the key is down, so its count is "one per VBLANK for as long as the
FOR loop lasts" -- 122 is about 2.4 s of held key at 50 Hz, which is exactly how
long `FOR I=1TO6000:NEXT` takes there.  zerobas is EDGE-latched into PENDING
(the T2 STRIG model, adopted when STOPGRACE was removed).  An edge model under a
HELD key should fire ONCE.  It fires 3.  Those two extra fires are the whole
subject: nothing designed them, so nothing holds them at 3.

PREDICTIONS, STATED BEFORE THE RUN (scored in the summary, misses included):
  P1  the 25 s hold is equivalent to the row's 200 s hold -- the program has long
      since ended, so the extra 175 s of held key cannot add a fire.
  P2  the flag is NOT constant across identical repeated runs.
  P3  the flag does NOT scale with the FOR loop length (if it did, the fires
      would be periodic and zerobas would read in the hundreds, not 3).
  P4  the flag moves when the key-down instant is shifted by a few tens of ms.

CONTROLS:
  A0  NEGATIVE -- the same program with the trap disabled must read flag=0 while
      still gating ran=1/done=1.  Without it a probe that can only ever print a
      positive number would look like it was measuring something.
  A5  POSITIVE -- one reference run, to show the instrument does read a large
      number where a large number exists.

Clean-room: our own ROM is unrestricted, and the reference side here is a
behaviour count through the keyboard matrix -- no ROM byte is read.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))

import basic_probe_stop_trap as ST  # noqa: E402


# ---------------------------------------------------------------- pure helpers

def gate(rs):
    """The flags of `rs`, or None if the batch is not a datum.

    REFUSES on: an empty batch, a crashed trial (None), a trial whose arming
    statements did not all run (`ran` != 1), and a trial captured while the
    program was still spinning (`done` != 1).  A batch that refuses must print
    as a REFUSAL, never as a flag distribution -- 'silence is not evidence'."""
    if not rs:
        return None
    for r in rs:
        if r is None:
            return None
        if r.get("ran") != 1 or r.get("done") != 1:
            return None
    return [r.get("flag") for r in rs]


def spread(fl):
    """(min, max, sorted distinct values) of a gated flag list."""
    return (min(fl), max(fl), sorted(set(fl)))


def varies(fl):
    """True when the same measurement gave more than one answer."""
    return len(set(fl)) > 1


def scales(pairs, factor=2.0):
    """`pairs` is [(loop_length, [flags]), ...] sorted by loop length.  True when
    the largest group's median-ish max is at least `factor` x the smallest's --
    i.e. the count tracks how long the program ran."""
    if len(pairs) < 2:
        return None
    lo = max(pairs[0][1])
    hi = max(pairs[-1][1])
    if lo <= 0:
        return None
    return hi >= factor * lo


# ---------------------------------------------------------------- the programs

def rearm_prog(n=6000):
    """The gate's own `E_rearm_under_held_key_refires` program, verbatim except
    for the loop bound, which is the knob A3 turns."""
    return [ST.CLR, "10 ON STOP GOSUB 100", "20 STOP ON", ST.RANOK,
            f"30 FORI=1TO{n}:NEXT", "40 POKE&HD003,1:END",
            "100 POKE&HD000,PEEK(&HD000)+1",
            "102 STOP OFF:STOP ON",
            "106 RETURN"]


def disabled_prog(n=6000):
    """A0's negative control: armed, then disarmed.  No fire is possible, the
    held key breaks the program, and the harness's injected POKE supplies
    `done`.  Must read flag=0 -- and must still be GATED, so a zero from a
    program that never ran cannot pass for one."""
    return [ST.CLR, "10 ON STOP GOSUB 100", "20 STOP ON:STOP OFF", ST.RANOK,
            f"30 FORI=1TO{n}:NEXT", "40 POKE&HD003,1:END",
            "100 POKE&HD000,PEEK(&HD000)+1",
            "102 STOP OFF:STOP ON",
            "106 RETURN"]


# ------------------------------------------------------------------- selftest

def selftest():
    ok = True

    def chk(label, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL':5} selftest {label}")
        ok = ok and cond

    good = [{"flag": 3, "ran": 1, "done": 1}, {"flag": 1, "ran": 1, "done": 1}]
    chk("gate POSITIVE: two clean trials yield their flags",
        gate(good) == [3, 1])
    chk("gate NEGATIVE: a crashed trial refuses",
        gate([{"flag": 3, "ran": 1, "done": 1}, None]) is None)
    chk("gate NEGATIVE: done=0 (still spinning) refuses",
        gate([{"flag": 3, "ran": 1, "done": 0}]) is None)
    chk("gate NEGATIVE: ran=0 (arming line never executed) refuses",
        gate([{"flag": 3, "ran": 0, "done": 1}]) is None)
    chk("gate NEGATIVE: an EMPTY batch refuses rather than reading as green",
        gate([]) is None)
    chk("gate NEGATIVE: ran=2 (fell past the poll loop) refuses",
        gate([{"flag": 0, "ran": 2, "done": 1}]) is None)

    chk("varies POSITIVE: two different answers", varies([3, 1]) is True)
    chk("varies NEGATIVE: one repeated answer", varies([3, 3, 3]) is False)
    chk("spread", spread([3, 1, 4]) == (1, 4, [1, 3, 4]))

    chk("scales POSITIVE: 8x the loop gives 8x the fires",
        scales([(1500, [3]), (12000, [24])]) is True)
    chk("scales NEGATIVE: a flat count does NOT scale",
        scales([(1500, [3]), (12000, [3])]) is False)
    chk("scales REFUSES on a single group", scales([(6000, [3])]) is None)
    chk("scales REFUSES when the small group read zero",
        scales([(1500, [0]), (12000, [3])]) is None)

    # The programs must actually differ in the line under test, or A0 is a copy
    # of A1 wearing a control's name.
    chk("the negative control really disarms",
        "STOP ON:STOP OFF" in disabled_prog()[2]
        and "STOP ON:STOP OFF" not in rearm_prog()[2])
    chk("the subject program is the gate's own row",
        rearm_prog()[6:] == ["100 POKE&HD000,PEEK(&HD000)+1",
                             "102 STOP OFF:STOP ON", "106 RETURN"])
    print("\nSELFTEST OK" if ok else "\nSELFTEST FAILED")
    return 0 if ok else 1


# ----------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--machine", default=ST.ZB_MACHINE)
    ap.add_argument("--ref-machine", default=ST.REF_MACHINE)
    ap.add_argument("--arms", default="A0,A1,A2,A3,A4,A5,A6,A7",
                    help="comma-separated arms to run")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    want = set(a.strip() for a in args.arms.split(","))
    results = {}

    def batch(tag, machine, prog, presses, trials):
        rs = []
        for i in range(trials):
            r = ST.run(machine, prog, presses, deadline=300.0, timeout=240,
                       screen=True)
            rs.append(r)
            brief = None if r is None else {k: r.get(k) for k in ("flag", "ran", "done")}
            print(f"    {tag} trial {i}: {brief}")
            if r is None or r.get("ran") != 1 or r.get("done") != 1:
                # A failed case contributes a row that LOOKS like data -- make the
                # failure visible instead of letting its flag into a distribution.
                print(f"    {tag} trial {i}: UNGATED -- screen follows")
                ST.show_screen(r)
        g = gate(rs)
        print(f"  {tag}: {'REFUSING (a trial was not a datum)' if g is None else g}")
        return g

    HOLD = [(0.3, 25.0)]
    LONG = [(0.3, 200.0)]

    if "A0" in want:
        print("\n=== A0 NEGATIVE CONTROL: trap disarmed -> the count must read 0 ===")
        results["A0"] = batch("A0", args.machine, disabled_prog(), HOLD, 2)

    if "A1" in want:
        print("\n=== A1 EQUIVALENCE: the row's 200 s hold vs a 25 s hold (P1) ===")
        results["A1long"] = batch("A1long", args.machine, rearm_prog(), LONG, 3)

    if "A2" in want:
        print("\n=== A2 REPEATABILITY: six identical runs, one unchanged ROM (P2) ===")
        results["A2"] = batch("A2", args.machine, rearm_prog(), HOLD, 6)

    if "A3" in want:
        print("\n=== A3 LOOP LENGTH: does the count track how long the program ran? (P3) ===")
        for n in (1500, 3000, 12000):
            results[f"A3n{n}"] = batch(f"A3n{n}", args.machine, rearm_prog(n), HOLD, 2)

    if "A4" in want:
        print("\n=== A4 PHASE: shift the key-down instant, ROM untouched (P4) ===")
        for dn in (0.34, 0.38, 0.42, 0.46):
            results[f"A4d{dn}"] = batch(f"A4d{dn}", args.machine, rearm_prog(),
                                        [(dn, 25.0)], 2)

    if "A6" in want:
        print("\n=== A6 FINE PHASE: 5 ms steps across one PAL frame, ROM untouched (P5) ===")
        for k in range(9):
            dn = round(0.300 + 0.005 * k, 3)
            results[f"A6d{dn}"] = batch(f"A6d{dn}", args.machine, rearm_prog(),
                                        [(dn, 25.0)], 1)

    if "A7" in want:
        print("\n=== A7 BOOT OFFSET: the SAME question asked the other way (P6) ===")
        print("    the press schedule is untouched; only the emulator's start phase")
        print("    relative to the whole injection schedule moves.")
        for k in range(9):
            bt = round(6.000 + 0.005 * k, 3)
            rs = []
            for i in range(1):
                r = ST.run(args.machine, rearm_prog(), HOLD, boot=bt,
                           deadline=300.0, timeout=240, screen=True)
                rs.append(r)
                brief = None if r is None else {x: r.get(x) for x in ("flag", "ran", "done")}
                print(f"    A7b{bt} trial {i}: {brief}")
                if r is None or r.get("ran") != 1 or r.get("done") != 1:
                    print(f"    A7b{bt} trial {i}: UNGATED -- screen follows")
                    ST.show_screen(r)
            g = gate(rs)
            print(f"  A7b{bt}: {'REFUSING (a trial was not a datum)' if g is None else g}")
            results[f"A7b{bt}"] = g

    if "A5" in want:
        print("\n=== A5 POSITIVE CONTROL: the reference, same program ===")
        results["A5ref"] = batch("A5ref", args.ref_machine, rearm_prog(), HOLD, 1)

    print("\n" + "=" * 70)
    print("SUMMARY -- every arm ran the SHIPPED ROM; nothing here changes hook_tab")
    print("=" * 70)
    for k, v in results.items():
        print(f"  {k:10} {'REFUSED' if v is None else f'{v}  spread={spread(v)}'}")

    print("\n--- PREDICTIONS SCORED ---")
    lng, sht = results.get("A1long"), results.get("A2")
    if lng and sht:
        same = set(lng) & set(sht) or set(lng) == set(sht)
        print(f"  P1 hold length irrelevant: long={sorted(set(lng))} "
              f"short={sorted(set(sht))} -> {'HIT' if same else 'MISS'}")
    else:
        print("  P1 unscored (an arm refused)")
    if sht:
        print(f"  P2 identical runs disagree: {spread(sht)} -> "
              f"{'HIT' if varies(sht) else 'MISS'}")
    else:
        print("  P2 unscored (A2 refused)")
    pairs = [(n, results[f"A3n{n}"]) for n in (1500, 3000, 12000)
             if results.get(f"A3n{n}")]
    if sht:
        pairs.append((6000, sht))
    pairs.sort()
    sc = scales(pairs) if len(pairs) >= 2 else None
    print(f"  P3 count does NOT scale with loop length: {[(n, f) for n, f in pairs]}"
          f" -> {'unscored' if sc is None else ('HIT' if sc is False else 'MISS')}")
    phase = {k: v for k, v in results.items() if k.startswith("A4")}
    if phase and sht:
        allf = list(sht) + [f for v in phase.values() if v for f in v]
        print(f"  P4 phase moves the count: {spread(allf)} -> "
              f"{'HIT' if varies(allf) else 'MISS'}")
    else:
        print("  P4 unscored")
    fine = [(float(k[4:]), v) for k, v in results.items() if k.startswith("A6d") and v]
    if fine:
        fine.sort()
        print(f"  P5 fine phase sweep (5 ms steps, one PAL frame is 20 ms):")
        print("     " + "  ".join(f"{d:.3f}->{v[0]}" for d, v in fine))
        vals = [v[0] for _, v in fine]
        print(f"     distinct answers across ONE frame: {sorted(set(vals))} -> "
              f"{'HIT' if len(set(vals)) > 1 else 'MISS'}")
    boot = [(float(k[4:]), v) for k, v in results.items() if k.startswith("A7b") and v]
    if boot:
        boot.sort()
        print(f"  P6 boot-offset sweep (the same question, other knob):")
        print("     " + "  ".join(f"{b:.3f}->{v[0]}" for b, v in boot))
        vals = [v[0] for _, v in boot]
        print(f"     distinct answers: {sorted(set(vals))} -> "
              f"{'HIT' if len(set(vals)) > 1 else 'MISS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
