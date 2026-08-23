#!/usr/bin/env python3
"""D-TRAPSVC — does leaving a trap handler WITHOUT its `RETURN` kill that trap?

The candidate D-DEFERBLIND's scout filed and refused to fold in
(docs/deferblind-scout-2026-08-23.md §5). `TRAPSVC` is "count of live SERVICING
entries == depth of the service stack": `check_traps` INCREMENTS it on dispatch
(basic/traps.asm:369) and only `ex_return`'s `trap_return_check` DECREMENTS it
(basic/traps.asm:421) -- i.e. only on a normal `RETURN` out of the handler. The
same routine is the only writer of the entry's SERVICING -> ON auto-resume. So a
handler left by any other door (`RESUME <line>`, a plain `GOTO`) should leave the
entry SERVICING forever: `ct_find` fires only entries whose state is exactly ON,
so THAT TRAP IS SILENTLY DEAD, and the stale service record is never popped.

🔴 THIS IS A FAITHFULNESS QUESTION, NOT A BUG HUNT. Both references are EXPECTED
to leak the same way -- MSX BASIC's own contract is "a trap handler must end in
RETURN". The references define the want; a row where they disagree is not one.

INSTRUMENT: the shape D-DEFERBLIND calibrated -- whole programs, boot-per-case,
run on both references and zerobas, each printing ONE fenced value; a row that
printed nothing reads <NO OUTPUT> and is scored NOT MEASURED, never as
agreement. `--sides=zb` limits it. `scratchpad/trapsvc_calib.py` is the
calibration: it re-runs these same rows under a knife (K-TR1) that neuters the
SERVICING -> ON re-enable, and requires exactly the rows claimed to be pinned by
that re-enable to move.

ON INTERVAL is the instrument because it is the ONLY self-firing MSX1 trap --
KEY/STRIG/SPRITE/STOP need a human. All five share `check_traps` and
`trap_return_check` verbatim (the index is a parameter), which is the argument
for not paying for four more device-driven rows; §"NOT MEASURED" in the doc.

EVERY ROW PRINTS TWO NUMBERS, and the FIRST one is the guard: `B` = "the trap
fired at least once at all". A row whose subject reads 0 because the trap never
armed is a different fact from one that reads 0 because the trap DIED, and one
number cannot tell them apart.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}

JIF = 0xFC9E            # published work area: the frame counter (T5 probe's own)


def wait(line, n):
    """Let n FRAMES pass, machine-independently, with the T5 probe's high-byte
    re-read guard (a lo-then-hi read TEARS when the low byte wraps between the
    two PEEKs and composes 256 low)."""
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


CASES = {
    # --- the positive control: the handler RETURNs, nothing is abandoned ------
    'int.ctl':     twowindow("X=1", "RESUME50"),
    # --- the ONE-FIRE control, and it is what SEPARATES the two candidate
    #     knives. Period 60 in a 90-frame window fires EXACTLY ONCE, so the
    #     second window's fire depends on the SERVICING -> ON re-enable but not
    #     on the TRAPSVC count ever coming back down (1 is far from
    #     TRAPSTK_MAX=6). K-TR1 must move it; K-TR2 must not. ------------------
    'int.one':     twowindow("X=1", "RESUME50", period=60),
    # --- THE SUBJECT: an error inside the handler, trapped, left by RESUME <line>
    #     so line 710's RETURN is never reached ---------------------------------
    'int.resume':  twowindow("X=FNZ(0)", "RESUME50"),
    # --- the SEPARATING control: same program, same fault, but RESUME NEXT
    #     resumes AT line 710 -- the RETURN *is* reached. If this fires and
    #     int.resume does not, the missed RETURN is the mechanism and nothing
    #     else is (same fault, same handler, same trap, one keyword apart) -----
    'int.resnext': twowindow("X=FNZ(0)", "RESUMENEXT"),
    # --- the same abandonment with NO error anywhere: a plain GOTO out of the
    #     handler. Separates "leaving without RETURN" from "an error happened" -
    'int.goto':    twowindow("GOTO50", "RESUME50"),
    # --- how many such events does the machine survive? Each cycle re-enables
    #     the trap explicitly (`INTERVALON`), so the ENTRY comes back; the
    #     question is what the abandoned service records do. N = cycles that
    #     fired, E = the last ERR seen. zerobas has TWO candidate caps here
    #     (TRAPSTK_MAX=6 and GOSUB_DEPTH=8) -- gos.leak below measures the
    #     second one on its own so the number can say which. -------------------
    #     🔴 EACH CYCLE REPRINTS THE FENCE, and that is not cosmetic: zerobas
    #     ABORTS this program ("Out of memory in 800" -- an ERR 7 raised while
    #     the error handler is already active is untrapped), so a fence printed
    #     only at the END would leave the cap UNREADABLE. The first draft did,
    #     and its reading was the TYPED ECHO of that unreached line.
    'int.six':     ["10 ONERRORGOTO800",
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
    # --- the GOSUB-depth separator, with no trap in it at all. N = frames
    #     successfully nested, E = the ERR that stopped it (0 = never stopped).
    #     This is a SCOPE row: zerobas's GOSUB_DEPTH is 8 by own design
    #     (basic/sysvars.inc), so a divergence here is already filed and is
    #     what lets int.six's number be read. -----------------------------------
    'gos.leak':    ["10 ONERRORGOTO800",
                    "20 N=0:E=0",
                    "30 GOSUB100",
                    '90 CLS:PRINT"[";N;E;"]":END',
                    "100 N=N+1:IFN<12THEN30",
                    "110 RETURN",
                    "800 E=ERR:RESUME90"],
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")


def face(cap):
    """🔴 THE FENCE IS ALSO IN THE PROGRAM TEXT, so a run that never reaches its
    own `CLS:PRINT` leaves the TYPED ECHO of that line on screen -- and
    `PRINT"[";N;E;"]"` echoes as `[";N;E;"]`, which a bare bracket search reads
    as a value. It did, on `int.six`/zb, and `";N;E;"` looked enough like data to
    be tabulated. Every reading here is digits, spaces and minus signs, so a
    match containing anything else is the SOURCE, not the output: reject it and
    report <NO OUTPUT>, which is scored NOT MEASURED rather than as a value.
    [[apparatus-is-part-of-the-measurement]] -- an echo-anchored readout again."""
    if cap is None:
        return "<NO CAPTURE>"
    for m in BR.finditer("".join(cap)):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split()) or "<EMPTY>"
    return "<NO OUTPUT>"


def main():
    only, sides = None, ["vg8020", "cf3300", "zb"]
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
        else:
            only = a.split(",")
    labels = [l for l in CASES if not only or any(o in l for o in only)]
    faces = {}
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + CASES[l] + ["RUN"])],
                batch=False, boot=cfg["boot"], step=5.0, cap_gap=45.0,
                timeout=600.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l}", flush=True)
    print()
    W = max(len(l) for l in labels)
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only -- no reference column in this run)")
            continue
        if len(refs) != 1:
            note = "   ⚠️ THE REFERENCES DISAGREE — not a want"
        elif any("<NO" in v for v in vals.values()):
            note = "   .... NOT MEASURED (blank reading, not a divergence)"
        elif vals["zb"] not in refs:
            note = "   🔴 DIFF"
        else:
            note = ""
        print(line + note)
    print(f"\nROWS: {len(labels)} printed")


if __name__ == "__main__":
    main()
