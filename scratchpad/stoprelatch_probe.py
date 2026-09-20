#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-STOPRELATCH -- WHAT re-arms the reference's STOP trap under a held key?

D-REARMSENS (`disk/docs/spec-diskcode-eviction.md` 6.6af/6.6ag) established that
zerobas does NOT re-fire a re-arming handler under a held Ctrl-STOP: it answers
1, where the VG-8020 answers 122 at every phase.  That divergence is now the one
thing blocking step 9, so it has to be FIXED -- and the first step is to find out
what rule the reference is actually following, instead of inferring one from the
number 122.

`docs/spec-traps-t1-stop-reslice.md` records two reference facts that look like
they contradict each other:

    3 s hold during the handler   -> handler completes, +1 fire   EDGE, not level
    handler re-arms itself under  -> 122 fires
      a held key (STOP OFF:STOP ON)

Both cannot be explained by "the key level is sampled".  Something about the
re-arm makes the already-held key count as a fresh edge again.  THREE candidate
rules fit the two rows equally well, and no row anyone has run separates them:

  (a) the OFF is load-bearing -- leaving the ON state clears the edge shadow, so
      the following STOP ON sees a fresh edge;
  (b) the ON is load-bearing -- entering ON clears (or ignores) the shadow, and
      the OFF is incidental;
  (c) neither -- a held key re-fires whenever the trap is merely ARMED, and the
      "+1 fire" row above is about SERVICING specifically, not about arming.

This probe builds the cases that separate them.  Which one is true decides where
zerobas's fix goes: `es_clear` (a), `es_set` (b), or `rp_break` (c) -- three
different edits, and two of them would be wrong.

CADENCE IS THE SECOND QUESTION.  122 fires in a `FOR I=1TO6000:NEXT` that takes
~2.44 s on the reference is 50 Hz to within rounding, which SUGGESTS one fire per
VBLANK -- but 2.44 s is also a fixed number of interpreter statements, so the two
readings coincide on the only loop length ever run.  R4 sweeps the loop length:
a per-frame rule scales the count linearly with it, and so does a per-statement
rule -- but they disagree once the HANDLER's own cost changes, which is R5.

⚠️ EVERY ARM IS SAMPLED AT THREE KEY-DOWN PHASES, NOT ONE.  That is D-REARMSENS's
lesson applied to its own successor: a single schedule value produced the spike
this whole arc came from.  A one-number answer from this probe would be the same
mistake wearing a new label.

PREDICTIONS, STATED BEFORE THE RUN (scored below, misses included):
  P1  R3 (held key, handler does NOT re-arm) on the reference is SMALL (1-2).
  P2  R2 (`STOP ON` alone, no OFF) on the reference is SMALL -- i.e. rule (a),
      the OFF is what clears the shadow.
  P3  R1 scales linearly with the loop length on the reference (R4).
  P4  zerobas reads 1-3 on ALL of R1/R2/R3 -- no variant helps, because its
      shadow is only ever cleared by an OBSERVED RELEASE.

Clean-room: our own ROM is unrestricted; the reference side is a behaviour count
through the keyboard matrix.  No ROM byte is read.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))

import basic_probe_stop_trap as ST          # noqa: E402
from rearmsens_probe import gate, spread    # noqa: E402  (mutation-proved there)


PHASES = (0.300, 0.315, 0.330)
HOLD_UP = 25.0


def prog(rearm, n=6000, handler_delay=0):
    """The gate's re-arm program with two knobs.

    `rearm` is the body of line 102 (None omits the line entirely -- R3's
    no-re-arm case).  `handler_delay` adds a FOR delay INSIDE the handler, which
    is what separates a per-VBLANK cadence from a per-statement one."""
    h = ["100 POKE&HD000,PEEK(&HD000)+1"]
    if handler_delay:
        h.append(f"101 FORK=1TO{handler_delay}:NEXT")
    if rearm is not None:
        h.append(f"102 {rearm}")
    h.append("106 RETURN")
    return [ST.CLR, "10 ON STOP GOSUB 100", "20 STOP ON", ST.RANOK,
            f"30 FORI=1TO{n}:NEXT", "40 POKE&HD003,1:END", *h]


def disarmed_prog(n=6000):
    """The negative control: armed then disarmed, so no fire is possible."""
    return [ST.CLR, "10 ON STOP GOSUB 100", "20 STOP ON:STOP OFF", ST.RANOK,
            f"30 FORI=1TO{n}:NEXT", "40 POKE&HD003,1:END",
            "100 POKE&HD000,PEEK(&HD000)+1", "106 RETURN"]


def classify(r1, r2, r3, *, small=4):
    """Which of the three candidate rules do the reference's answers support?

    `r1`/`r2`/`r3` are gated flag lists for STOP OFF:STOP ON / STOP ON / no
    re-arm.  Returns a rule letter, or None when the readings do not separate
    them (which must print as 'INCONCLUSIVE', never as a rule)."""
    if not (r1 and r2 and r3):
        return None
    big = lambda fl: min(fl) > small
    if big(r3):
        return "c"                       # arming alone re-fires; the re-arm is noise
    if big(r1) and big(r2):
        return "b"                       # entering ON re-arms; the OFF is incidental
    if big(r1) and not big(r2):
        return "a"                       # leaving ON clears the shadow
    return None                          # r1 small too -> nothing reproduces 122


def selftest():
    ok = True

    def chk(label, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL':5} selftest {label}")
        ok = ok and cond

    chk("classify a: only the OFF variant is big",
        classify([122], [1], [1]) == "a")
    chk("classify b: both re-arm variants are big",
        classify([122], [120], [1]) == "b")
    chk("classify c: even the no-re-arm case is big",
        classify([122], [122], [99]) == "c")
    chk("classify NEGATIVE: nothing big at all is INCONCLUSIVE, not a rule",
        classify([1], [1], [1]) is None)
    chk("classify NEGATIVE: a refused arm refuses the verdict",
        classify(None, [1], [1]) is None)
    chk("classify NEGATIVE: an empty arm refuses the verdict",
        classify([], [1], [1]) is None)
    chk("classify uses the MINIMUM across phases, so one lucky phase is not a rule",
        classify([122, 1, 1], [1], [1]) is None)

    # The programs must actually differ in the line the arms are about.
    p1, p2, p3 = prog("STOP OFF:STOP ON"), prog("STOP ON"), prog(None)
    chk("R1 carries the OFF", "102 STOP OFF:STOP ON" in p1)
    chk("R2 carries the bare ON and no OFF",
        "102 STOP ON" in p2 and not any("STOP OFF" in l for l in p2))
    chk("R3 has no line 102 at all", not any(l.startswith("102") for l in p3))
    chk("the handler delay really lands in the handler",
        "101 FORK=1TO500:NEXT" in prog("STOP ON", handler_delay=500))
    chk("the negative control really disarms",
        "STOP ON:STOP OFF" in disarmed_prog()[2])
    print("\nSELFTEST OK" if ok else "\nSELFTEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--machine", default=ST.ZB_MACHINE)
    ap.add_argument("--ref-machine", default=ST.REF_MACHINE)
    ap.add_argument("--arms", default="R0,R1,R2,R3,R4,R5")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    want = set(a.strip() for a in args.arms.split(","))
    res = {}

    def batch(tag, machine, p, phases=PHASES):
        rs = []
        for dn in phases:
            r = ST.run(machine, p, [(dn, HOLD_UP)], deadline=300.0, timeout=240,
                       screen=True)
            b = None if r is None else {k: r.get(k) for k in ("flag", "ran", "done")}
            print(f"    {tag} phase {dn:.3f}: {b}")
            if r is None or r.get("ran") != 1 or r.get("done") != 1:
                print(f"    {tag} phase {dn:.3f}: UNGATED -- screen follows")
                ST.show_screen(r)
            rs.append(r)
        g = gate(rs)
        print(f"  {tag}: {'REFUSING (a phase was not a datum)' if g is None else g}")
        res[tag] = g
        return g

    MACHS = (("ref", args.ref_machine), ("zb ", args.machine))

    if "R0" in want:
        print("\n=== R0 NEGATIVE CONTROL: disarmed -> the counter must read 0 ===")
        for tag, m in MACHS:
            batch(f"R0.{tag}", m, disarmed_prog(), phases=PHASES[:1])

    for arm, rearm, what in (("R1", "STOP OFF:STOP ON", "the gate's own re-arm"),
                             ("R2", "STOP ON", "re-arm with NO disarm"),
                             ("R3", None, "no re-arm at all")):
        if arm not in want:
            continue
        print(f"\n=== {arm}: {what} ===")
        for tag, m in MACHS:
            batch(f"{arm}.{tag}", m, prog(rearm))

    if "R4" in want:
        print("\n=== R4 LOOP LENGTH: does the count track elapsed time? ===")
        for n in (1500, 3000, 12000):
            for tag, m in MACHS:
                batch(f"R4n{n}.{tag}", m, prog("STOP OFF:STOP ON", n=n),
                      phases=PHASES[:1])

    if "R5" in want:
        print("\n=== R5 HANDLER COST: per-VBLANK and per-statement disagree here ===")
        print("    a costlier handler spends more TIME per fire but the same number")
        print("    of statements, so a per-frame rule drops the count and a")
        print("    per-statement rule does not.")
        for d in (200, 800):
            for tag, m in MACHS:
                batch(f"R5d{d}.{tag}", m,
                      prog("STOP OFF:STOP ON", handler_delay=d), phases=PHASES[:1])

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for k, v in res.items():
        print(f"  {k:14} {'REFUSED' if v is None else f'{v}  spread={spread(v)}'}")

    print("\n--- PREDICTIONS SCORED ---")
    r1r, r2r, r3r = res.get("R1.ref"), res.get("R2.ref"), res.get("R3.ref")
    if r3r:
        print(f"  P1 reference no-re-arm is SMALL: {spread(r3r)} -> "
              f"{'HIT' if max(r3r) <= 4 else 'MISS'}")
    if r2r:
        print(f"  P2 reference bare-ON is SMALL (rule a): {spread(r2r)} -> "
              f"{'HIT' if max(r2r) <= 4 else 'MISS'}")
    rule = classify(r1r, r2r, r3r)
    print(f"  ➡️ RULE SUPPORTED BY THE REFERENCE: "
          f"{rule if rule else 'INCONCLUSIVE -- the arms do not separate them'}")
    pairs = [(n, res.get(f"R4n{n}.ref")) for n in (1500, 3000, 12000)]
    pairs = [(n, v) for n, v in pairs if v]
    if r1r:
        pairs.append((6000, r1r[:1]))
    pairs.sort()
    if len(pairs) >= 2:
        print(f"  P3 reference count vs loop length: "
              + "  ".join(f"{n}->{v[0]}" for n, v in pairs))
    zb = [res.get(f"R{i}.zb ") for i in (1, 2, 3)]
    if all(zb):
        allz = [f for v in zb for f in v]
        print(f"  P4 zerobas small on every variant: {spread(allz)} -> "
              f"{'HIT' if max(allz) <= 4 else 'MISS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
