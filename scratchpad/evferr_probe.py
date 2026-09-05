#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EVFERR — the FIVE live `ev_f_err` jump sites, each with its SEPARATOR row.

TODO.md:3834 (T-BDB99C) filed this as "ev_f_err's OTHER SEVEN JUMP SITES", with two rows
LIVE and five rows AGREEING. This probe exists because an agreeing row has to
name its SECOND CAUSE OF GREEN before "agrees" is a reading about the SITE:

  * `A=VARPTR 5` / `A=VARPTR(5)` agree at 2 -- but ev_f_err leaves the cursor
    UNADVANCED, so `5` is a leftover token and `es_noentry` raises that 2. The
    expression layer said nothing. Separator: a form with NOTHING left over
    (`A=VARPTR`, `A=VARPTR(`).
  * `A=EOF(0)` / `A=LOF(0)` agree at 59 -- but `fch_check` sends channel 0 to
    `err_notopen_raise` BEFORE `fch_mode_class` runs, so :1101/:1122 are never
    reached. Separator: an OPEN device channel (`OPEN"CRT:"`).
  * `A=BASE 5` / `A=BASE(0` agree at 2 -- and the filed reason ("BASE is
    descoped and carries its own inline ERRMARK body") is STALE: G8_RESIDENT is
    1, the expr.asm stub holding :2032/:2037 IS NOT ASSEMBLED, and the resident
    `ev_f_base` (graphics.asm:1292) raises gfx_syntax. Separator: `A=BASE`.

Readout is `[ERR]`: 0 when the statement COMPLETED, else the MSX error code.
Predictions are pinned in scratchpad/evferr_predictions.md BEFORE this ran.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_signal                                               # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}


def case(stmt):
    # The mark goes before every END (probe_signal.mark_ends): the readout is an
    # ERROR CODE, never an address, so the ~8 bytes of extra program text cannot
    # move the answer (probe_signal rule 3).
    return probe_signal.mark_ends([
        "10 ONERRORGOTO900",
        f"20 {stmt}",
        '30 SCREEN0:CLS:PRINT"[";ERR;"]":END',
        '900 SCREEN0:CLS:PRINT"[";ERR;"]":END'])


CRT = 'OPEN"CRT:"FOROUTPUTAS#1'

CASES = {
    # --- site :813, ev_f_paren: a parenthesised expression not closed by ')' --
    'p.noclose':    case("A=(1+2"),
    'p.colon':      case("A=(1+2:B=3"),
    'p.nested':     case("A=((1+2)"),
    'p.print':      case("PRINT(1+2"),
    'p.ok':         case("A=(1+2)"),
    # --- sites :1886/:1890, VARPTR ------------------------------------------
    'v.nopar':      case("A=VARPTR 5"),
    'v.nopareol':   case("A=VARPTR"),          # SEPARATOR: nothing left over
    'v.badarg':     case("A=VARPTR(5)"),
    'v.badargeol':  case("A=VARPTR("),         # SEPARATOR: nothing left over
    'v.noclose':    case("A=VARPTR(B"),
    'v.nocloseset': case("B=1:A=VARPTR(B"),    # SEPARATOR: B is SET
    'v.ok':         case("B=1:A=VARPTR(B)"),
    # --- sites :1101/:1122, EOF/LOF on a length-less channel ------------------
    'e.eofdev':     case("A=EOF(0)"),
    'e.eofcrt':     case(f"{CRT}:A=EOF(1)"),   # SEPARATOR: an OPEN device chan
    'e.lofcrt':     case(f"{CRT}:A=LOF(1)"),   # SEPARATOR: an OPEN device chan
    'e.crtok':      case(f'{CRT}:PRINT#1,"X"'),
    # --- BLAST RADIUS of retargeting ev_f_err -> ev_f_empty at :813 ----------
    # missing.asm's els_tc_common CLEARS ERRMARK and uses the landmark as its
    # discriminator ("did the RHS parse as anything well-formed"), and its own
    # header records that "did eval consume any bytes" was tried first and
    # measured wrong. §6.1 named it as the one that can sink the design: a
    # DEFERRED FPERR changes which error wins there.
    's.strparen':   case('A$=(1+2'),
    's.strvp':      case('A$=VARPTR 5'),
    's.strok':      case('A$=(1+2)'),
    # two more consumers of the same ev_f_paren site, on non-LET grammar
    'p.if':         case("IF(1 THEN A=2"),
    'p.for':        case("FOR I=(1 TO 3:NEXT"),
    # the ARRAY arm of vptr_close, which shares the ')' check with the scalar one
    'v.aryunset':   case("A=VARPTR(Z(1)"),
    # --- IS "SYNTAX OUTRANKS DOMAIN" WIDER THAN vptr_unset? -------------------
    # `A=VARPTR(B` with B unset is the last DIFF: zb answers the DOMAIN error
    # (5) where both references answer the SYNTAX one (2). Before pricing a fix
    # sited at vptr_unset, ask whether the rule it implies has OTHER members --
    # a subscript that is out of range is the same shape one arm over, and an
    # unset STRING scalar is the same shape one type over.
    'd.arybadsub':  case("DIM Z(2):A=VARPTR(Z(9)"),
    'd.arybadsubok': case("DIM Z(2):A=VARPTR(Z(9))"),
    'd.strunset':   case("A=VARPTR(B$"),
    'd.strunsetok': case("A=VARPTR(B$)"),
    # --- the pair that is NOT ASSEMBLED: BASE is resident, not descoped -------
    'b.nopar':      case("A=BASE 5"),
    'b.nopareol':   case("A=BASE"),            # SEPARATOR: nothing left over
    'b.openeol':    case("A=BASE("),
    'b.ok':         case("A=BASE(0)"),
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")


def face(cap):
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
    tally = probe_signal.Tally()
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            out = {}
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + CASES[l] + ["RUN"])],
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0, **probe_signal.kwargs(out))
            tally.add(out, label=f"{s}/{l}")
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:<13s} -> {faces[s][l]!r}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = nmeas = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)")
            continue
        if len(refs) != 1:
            note = "   ⚠️ THE REFERENCES DISAGREE — not a want"
        elif any("<NO" in v for v in vals.values()):
            note = "   .... NOT MEASURED"
        elif vals["zb"] not in refs:
            note = "   🔴 DIFF"
            ndiff += 1
            nmeas += 1
        else:
            note = "   ✅"
            nmeas += 1
        print(line + note)
    print(f"\n  {nmeas} scored, {ndiff} DIFF, {len(labels) - nmeas} not measured")
    print(tally.line())
    return 1 if nmeas != len(labels) else 0


if __name__ == "__main__":
    sys.exit(main())
