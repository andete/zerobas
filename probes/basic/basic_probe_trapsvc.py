#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TRAPSVC -- does leaving a trap handler WITHOUT its `RETURN` kill that trap?

Promoted from `scratchpad/trapsvc_probe.py` on 2026-09-09, when the last two
divergent rows of the set CLOSED. `docs/spec-basic-trapsvc.md` is the detail;
this file is the gate that keeps the answer from rotting back.

WHAT THE ROWS ASK. `TRAPSVC` counts live SERVICING entries. `check_traps`
increments it on dispatch and only `ex_return`'s `trap_return_check` decrements
it -- i.e. only on a normal `RETURN` out of the handler, which is also the only
writer of the entry's SERVICING -> ON auto-resume. So a handler left by any
other door (`RESUME <line>`, a plain `GOTO`) leaves the entry SERVICING forever
and `ct_find`, which fires only entries in state ON, never fires it again.

🎯 AND THE ANSWER IS *YES, AND THAT IS FAITHFUL*. `RESUME <line>` and a plain
`GOTO` out of an `ON INTERVAL` handler kill that trap on the VG-8020, the
CF-3300 and zerobas alike; `RESUME NEXT`, one keyword apart, keeps it alive on
all three. This is a faithfulness question, not a bug hunt: MSX BASIC's own
contract is "a trap handler must end in RETURN", and the references define the
want.

✅ THE TWO ROWS THAT USED TO DIVERGE CLOSED WITH D-CTLPOOL, AS A SIDE EFFECT,
AND NOBODY NOTICED FOR FIVE DAYS. `int.six` read `6 18` against the references'
`9 18` and `gos.leak` read `8 7` against `12 0`, because zerobas had two fixed
arrays -- `TRAPSTK_MAX` = 6 and `GOSUB_DEPTH` = 8 -- where the references have
one HIMEM-bounded pool. D-CTLPOOL retired `TRAPSTK` outright and moved the GOSUB
depth to ~2800, so both caps went away and both rows converged. The spec's §6
had DECLINED a fix here, ranking three options that are every one of them about
`TRAPSTK`: the decline outlived the data structure it was about.
🔴 WHICH IS EXACTLY WHY THIS GATE EXISTS. Seven rows measured green by a fix
that was not aiming at them are seven rows nothing is holding.

INSTRUMENT. Whole programs, boot-per-case, run on both references and zerobas,
each printing ONE fenced value. A row that printed nothing reads `<NO OUTPUT>`
and is an INSTRUMENT FAULT, never agreement.
⚠️ EVERY TWO-WINDOW ROW PRINTS TWO NUMBERS AND THE FIRST IS THE GUARD: `B` = the
trap fired at least once at all. A row whose subject reads 0 because the trap
never armed is a different fact from one that reads 0 because the trap DIED, and
one number cannot tell them apart. The guard is checked here BEFORE any verdict.
⚠️ `int.six` REPRINTS ITS FENCE AT THE TOP OF EVERY CYCLE. Before the pool
landed zerobas ABORTED this program (an ERR 7 raised inside an already-active
`ON ERROR` handler is untrapped), and a fence printed only at the end would have
left the cap unreadable -- the first draft's reading was the TYPED ECHO of a
line it never reached. The reprint stays even though the abort is gone: it costs
nothing and it is what makes a future regression legible instead of blank.

ON INTERVAL is the instrument because it is the ONLY self-firing MSX1 trap --
KEY/STRIG/SPRITE/STOP need a human -- and all five share `check_traps` and
`trap_return_check` verbatim (the index is a parameter). `SPRITE` was measured
against the same 2x2 on 2026-08-26 (`scratchpad/clrtrapstk_sprite.py`), which is
what turned that code argument into a measurement.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
}

JIF = 0xFC9E            # published work area: the frame counter


def wait(line, n):
    """Let n FRAMES pass, machine-independently, with the high-byte re-read
    guard: a lo-then-hi read TEARS when the low byte wraps between the two PEEKs
    and composes 256 low."""
    return [f"{line} H=PEEK(&H{JIF+1:X}):W=PEEK(&H{JIF:X})+256*H"
            f":IFH<>PEEK(&H{JIF+1:X})THEN{line}",
            f"{line+1} H=PEEK(&H{JIF+1:X}):V=PEEK(&H{JIF:X})+256*H"
            f":IFH<>PEEK(&H{JIF+1:X})THEN{line+1}",
            f"{line+2} IFV-W<{n}THEN{line+1}"]


def twowindow(fault, resume, period=10):
    """Arm INTERVAL, let a 90-frame window pass (the handler fires ~9 times and
    on its FIRST fire takes `fault`), then clear C and let a SECOND 90-frame
    window pass. B = the trap ever fired; C = it fired in window TWO, i.e. after
    the handler was left by whatever door `fault`/`resume` opens."""
    return ["10 ONERRORGOTO800",
            f"20 ONINTERVAL={period}GOSUB700",
            "30 INTERVALON",
            *wait(40, 90),
            "50 C=0",
            *wait(51, 90),
            "60 INTERVALOFF",
            '70 CLS:PRINT"[";B;C;"]":END',
            "700 B=1:C=1:IFF=1THEN710",
            f"702 F=1:{fault}",
            "710 RETURN",
            f"800 {resume}"]


CASES = [
    ("int.ctl", twowindow("X=1", "RESUME50"),
     "CONTROL: the handler RETURNs, nothing is abandoned"),
    # The ONE-FIRE control, and what separates the two candidate knives: period
    # 60 in a 90-frame window fires EXACTLY ONCE, so window two depends on the
    # SERVICING -> ON re-enable but not on any count coming back down.
    ("int.one", twowindow("X=1", "RESUME50", period=60),
     "CONTROL: exactly ONE fire in window 1"),
    ("int.resume", twowindow("X=FNZ(0)", "RESUME50"),
     "THE SUBJECT: trapped error, left via RESUME <line>, RETURN never reached"),
    # 🎯 THE SEPARATOR, and it is what makes the answer a MECHANISM rather than a
    # correlation: the SAME program, same fault, same trap, one keyword apart --
    # RESUME NEXT lands *on* line 710's RETURN.
    ("int.resnext", twowindow("X=FNZ(0)", "RESUMENEXT"),
     "SEPARATOR: same fault, RESUME NEXT, which lands ON the RETURN"),
    ("int.goto", twowindow("GOTO50", "RESUME50"),
     "the same abandonment with NO error anywhere: a plain GOTO out"),
    # N = cycles that fired, E = the last ERR seen (18 = the undefined FNZ, which
    # is the fault, not the finding). Each cycle re-enables the trap explicitly,
    # so the ENTRY comes back; the question is what the abandoned service
    # records do. The loop caps itself at 9.
    ("int.six", ["10 ONERRORGOTO800",
                 "20 ONINTERVAL=10GOSUB700",
                 "30 N=0:E=0",
                 '40 CLS:PRINT"[";N;E;"]":INTERVALON:C=0',
                 *wait(41, 45),
                 "50 IFC=0THEN90",
                 "52 N=N+1:IFN<9THEN40",
                 '90 INTERVALOFF:CLS:PRINT"[";N;E;"]":END',
                 "700 C=1:X=FNZ(0)",
                 "710 RETURN",
                 "800 E=ERR:RESUME50"],
     "nine leak-and-re-arm cycles: N = cycles that fired, E = last ERR"),
    # 🎯 THE SCOPE ROW, with no trap in it at all. It is what lets int.six's
    # number be read: before the pool, zerobas had TWO candidate caps in that
    # program (TRAPSTK_MAX=6 and GOSUB_DEPTH=8) and "ERR 7 / Out of memory" was
    # the answer to both. This one measures the second on its own.
    ("gos.leak", ["10 ONERRORGOTO800",
                  "20 N=0:E=0",
                  "30 GOSUB100",
                  '90 CLS:PRINT"[";N;E;"]":END',
                  "100 N=N+1:IFN<12THEN30",
                  "110 RETURN",
                  "800 E=ERR:RESUME90"],
     "SCOPE: the GOSUB-depth separator, no trap in it at all"),
]

# The REFERENCE face for every row, measured 2026-08-23 and reproduced
# 2026-09-09 (`scratchpad/trapsvc_pincheck.out`). Both references agree on all
# seven -- a row where they did NOT agree would not be a want -- so ONE pin
# serves both, and a side that leaves it is an oracle drift, not a finding.
PINNED = {
    "int.ctl":     "1 1",
    "int.one":     "1 1",
    "int.resume":  "1 0",
    "int.resnext": "1 1",
    "int.goto":    "1 0",
    "int.six":     "9 18",
    "gos.leak":    "12 0",
}
# The rows whose FIRST number is the "the trap fired at all" guard. `int.six`
# and `gos.leak` count something else in that column and are excluded by name,
# not by shape -- their pins carry their own arming evidence (N reaches its
# loop cap, which cannot happen without the trap).
GUARDED = ("int.ctl", "int.one", "int.resume", "int.resnext", "int.goto")

NUM = re.compile(r"^[-0-9 ]+$")


def face(raw):
    """The LAST bracketed all-numeric run. 🔴 The fence is also in the PROGRAM
    TEXT, so a run that never reaches its own `CLS:PRINT` leaves the typed echo
    of that line on screen; taking the last match and requiring it to be numeric
    is what keeps a typed line from being read as a value."""
    hit = None
    for m in re.finditer(r"\[([^\[\]]*)\]", "".join(raw or "")):
        if NUM.match(m.group(1)):
            hit = " ".join(m.group(1).split())
    return hit or "<NO OUTPUT>"


def run(machine, boot, reset, sel):
    return [face(c) for c in omsx_repl.run_cases(
        machine, [(lab, list(reset) + prog + ["RUN"]) for lab, prog, _w in sel],
        batch=False, reset=(), boot=boot, step=5.0, cap_gap=45.0, timeout=600.0)]


def num(v, i=0):
    try:
        return int(v.split()[i])
    except (ValueError, IndexError):
        return None


def selftest():
    """No emulator: the verdict logic against synthetic reads, including the two
    ways this gate can go blind. 🔴 A gate that reports PASS on a degenerate
    input has failed the way the thing it replaced failed."""
    ok = True

    def check(what, got, want):
        nonlocal ok
        if got != want:
            ok = False
            print(f"  🔴 {what}: {got!r}, want {want!r}")
        else:
            print(f"  ✅ {what}")

    check("face takes the LAST numeric fence, not the typed echo",
          face(['40 CLS:PRINT"[";N;E;"]":INTERVALON', "[ 9  18 ]"]), "9 18")
    check("face rejects a fence carrying quotes (the typed line)",
          face(['40 CLS:PRINT"[";N;E;"]"']), "<NO OUTPUT>")
    check("face reports a missing reading, never an empty agreement",
          face(["Ok"]), "<NO OUTPUT>")
    check("num reads the guard column", num("1 0"), 1)
    check("num refuses a blank", num("<NO OUTPUT>"), None)
    check("the guard rows are a subset of the pinned rows",
          set(GUARDED) <= set(PINNED), True)
    check("every case has a pin", {c[0] for c in CASES} == set(PINNED), True)
    # The arm: a zerobas row that AGREES with a guard reading 0 must still be
    # rejected, because the trap never armed. This is the 2026-08-23 fault.
    check("a blind row (B=0) is not agreement",
          verdict({"vg8020": {"int.resume": "0 0"},
                   "cf3300": {"int.resume": "0 0"},
                   "zb": {"int.resume": "0 0"}},
                  [c for c in CASES if c[0] == "int.resume"])[0], ["int.resume"])
    check("a genuine agreement is clean",
          verdict({s: {"int.resume": "1 0"} for s in ("vg8020", "cf3300", "zb")},
                  [c for c in CASES if c[0] == "int.resume"])[0], [])
    check("a zerobas divergence is caught",
          verdict({"vg8020": {"int.six": "9 18"}, "cf3300": {"int.six": "9 18"},
                   "zb": {"int.six": "6 18"}},
                  [c for c in CASES if c[0] == "int.six"])[0], ["int.six"])
    check("a REFERENCE drift is caught and named separately",
          verdict({"vg8020": {"int.six": "7 18"}, "cf3300": {"int.six": "9 18"},
                   "zb": {"int.six": "9 18"}},
                  [c for c in CASES if c[0] == "int.six"])[1], True)
    print("SELFTEST: PASS" if ok else "SELFTEST: RED")
    return 0 if ok else 1


def verdict(reads, sel):
    """-> (bad row labels, reference_drift). Kept separate from main() so the
    selftest can drive it without an emulator."""
    bad, drift = [], False
    for lab, _p, _w in sel:
        want = PINNED[lab]
        r1, r2, g = (reads[s][lab] for s in ("vg8020", "cf3300", "zb"))
        if r1 != want or r2 != want:
            drift = True
            bad.append(lab)
            continue
        if lab in GUARDED and num(g) != 1:
            bad.append(lab)
            continue
        if g != want:
            bad.append(lab)
    return bad, drift


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only", help="substring filter on the row label")
    ap.add_argument("--gate", action="store_true",
                    help="exit non-zero on a pin drift or a broken precondition")
    ap.add_argument("--selftest", action="store_true",
                    help="drive the verdict logic on synthetic reads, no emulator")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    sel = [c for c in CASES if not args.only or args.only in c[0]]
    if not sel:
        print("no rows selected")
        return 2

    reads = {}
    for side, kw in list(SIDES.items()) + [("zb", dict(machine=args.zb_machine,
                                                       boot=8.0, reset=("NEW",)))]:
        reads[side] = dict(zip([c[0] for c in sel],
                               run(kw["machine"], kw["boot"], kw["reset"], sel)))

    sides = ["vg8020", "cf3300", "zb"]
    blank = sorted({f"{s}/{lab}" for s in sides for lab, v in reads[s].items()
                    if v == "<NO OUTPUT>"})
    if blank:
        print(f"INSTRUMENT FAULT: no reading on {blank} -- NOT MEASURED, and not "
              f"agreement. Every row here prints its fence unconditionally, so a "
              f"blank is the program not finishing, never a value.")
        return 2

    w = max(len(l) for l, _, _ in CASES)
    print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>8}" for s in sides) + "   what it asks")
    for lab, _p, why in sel:
        print(f"{lab:<{w}}  " + "  ".join(f"{reads[s][lab]:>8}" for s in sides)
              + f"   {why}")

    bad, drift = verdict(reads, sel)
    print()
    for lab, _p, _w in sel:
        want = PINNED[lab]
        r1, r2, g = (reads[s][lab] for s in ("vg8020", "cf3300", "zb"))
        if r1 != want or r2 != want:
            print(f"{lab:<{w}}  🔴 THE REFERENCE MOVED: vg={r1!r} cf={r2!r}, "
                  f"pinned {want!r} -- an oracle drift, not a zerobas finding")
        elif lab in GUARDED and num(g) != 1:
            print(f"{lab:<{w}}  🔴 BLIND: zerobas's guard column is {g!r} -- the "
                  f"trap never fired at all, so the second number is not an answer")
        elif g != want:
            print(f"{lab:<{w}}  🔴 DIFF  refs {want!r} vs zb {g!r}")
        else:
            print(f"{lab:<{w}}  ok   all three {want!r}")

    print(f"\nrows {len(sel)}  pinned {len(PINNED)}  red {len(bad)}")
    if drift:
        print("  ⚠️ A REFERENCE FACE MOVED. Nothing in this run is readable as a "
              "zerobas verdict until the oracle or the harness is explained.")
    elif bad:
        print("  🔴 THESE ROWS CLOSED WITH D-CTLPOOL (spec-basic-trapsvc.md §17) "
              "AND HAVE COME BACK. The control-frame pool is the first place to "
              "look: TRAPSTK is retired, so a cap reappearing means a NEW one.")
    print("TRAPSVC: PASS" if not bad else f"TRAPSVC: RED ({len(bad)})")
    return 1 if (bad and args.gate) else 0


if __name__ == "__main__":
    sys.exit(main())
