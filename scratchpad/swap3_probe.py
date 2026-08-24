#!/usr/bin/env python3
"""D-SWAP3 -- `SWAP A,B,C` (a THIRD operand) is ERR 2, not ERR 5, on both refs.

`TODO.md` §"Language / verb surface": zerobas raises `Illegal function call`
(ERR 5) for a third SWAP operand, and `docs/missing-vg8020-characterization.md`
§4.5 records that same `Illegal function call` -- BUT its fixture left `B`
undefined, so what it measured is the SECOND-operand rule (`A=1:SWAP A,B` ->
ERR 5, the operand must EXIST) firing before the parse ever reaches `,C`. The
claim to verify: when `B` is DEFINED, the reference gives `Syntax error` (ERR 2)
for the third operand -- i.e. §4.5 is a case that AGREES for the wrong reason.

🎯 THE SEPARATOR IS WHETHER B EXISTS. Four fixtures pin it:
  s.3none  SWAP A,B,C                (nothing defined)   -> exp ERR 5 both
  s.3bund  A=1:SWAP A,B,C            (A def, B undef)     -> exp ERR 5 both
  s.3cund  A=1:B=2:SWAP A,B,C        (A,B def, C undef)   -> claim ERR 2 refs
  s.3all   A=1:B=2:C=3:SWAP A,B,C    (all def)            -> claim ERR 2 refs

READOUT `[ERR R]` from ON ERROR GOTO 900. `UNTRAPPED <msg> in <line>` is a
TRAPPABILITY reading, not a missing one (an unnamed outcome reads as no
outcome -- clrtrap's lesson). `<A>` prints before the statement so "died AT the
SWAP" is distinguishable from "never ran". A control reads a swapped value back.
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


def tcase(stmt, setup=None, read="0"):
    p = ["10 ONERRORGOTO900", '20 PRINT"<A>";']
    if setup:
        p.append(f"25 {setup}")
    p += [f"30 {stmt}",
          f'40 R={read}:PRINT"[";ERR;R;"]":END',
          f'900 R={read}:PRINT"[";ERR;R;"]":END']
    return p


CASES = {
    # --- the four separating fixtures for the THIRD operand -----------------
    's.3none':  tcase("SWAP A,B,C"),
    's.3bund':  tcase("SWAP A,B,C", setup="A=1"),
    's.3cund':  tcase("SWAP A,B,C", setup="A=1:B=2"),
    's.3all':   tcase("SWAP A,B,C", setup="A=1:B=2:C=3"),
    # --- the trailing comma, both operand states (stmt_error today) ---------
    's.tc.def': tcase("SWAP A,B,", setup="A=1:B=2"),
    's.tc.bun': tcase("SWAP A,B,", setup="A=1"),
    's.tc.non': tcase("SWAP A,B,"),
    # --- does the trailing comma ALSO swap-first? (the deeper-fix witness) ---
    's.tc.va':  tcase("SWAP A,B,", setup="A=1:B=2", read="A"),   # refs A=2
    's.tc.vb':  tcase("SWAP A,B,", setup="A=1:B=2", read="B"),   # refs B=1
    # --- type mismatch AND an extra operand: which wins? (type check is
    #     before the exchange, so ERR 13 should precede the ERR-2 boundary) --
    's.mm3':    tcase("SWAP A%,B!,C", setup="A%=1:B!=2"),
    's.mm3v':   tcase("SWAP A%,B!,C", setup="A%=1:B!=2", read="A%"),  # not swapped
    # --- a FOURTH operand and beyond: does the class extend past three? ------
    's.4all':   tcase("SWAP A,B,C,D", setup="A=1:B=2:C=3:D=4"),
    # --- controls: the second-operand rule and the valid swap ---------------
    's.2none':  tcase("SWAP A,B"),                       # both undef -> ERR 5
    's.2bund':  tcase("SWAP A,B", setup="A=1"),          # B undef -> ERR 5
    's.ok':     tcase("SWAP A,B", setup="A=1:B=2", read="A"),   # -> 0, A=2
    's.ok3':    tcase("SWAP A,B,C", setup="A=1:B=2:C=3", read="A"),  # refs
    #                EXCHANGE A<->B then raise: refs A=2, zb A unchanged=1
    's.ok3b':   tcase("SWAP A,B,C", setup="A=1:B=2:C=3", read="B"),  # refs B=1
    # --- §4.5's own verbatim rows (B undefined, as the doc ran them) --------
    'z.45.3':   tcase("SWAP A,B,C"),                     # doc: Illegal function
    'z.45.tc':  tcase("SWAP A,B,"),                      # doc: Syntax error
    'z.45.one': tcase("SWAP A"),                         # doc: Syntax error
    'z.45.lit': tcase("SWAP A,1", setup="A=1"),          # doc: Syntax error
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")
ERRMSG = re.compile(r"(Missing operand|Syntax error|Illegal function call|"
                    r"Type mismatch|Overflow|Out of memory|Undefined line number|"
                    r"Division by zero|Redimensioned array|Subscript out of range|"
                    r"NEXT without FOR|RETURN without GOSUB|Out of DATA|"
                    r"String too long|Bad file mode|File not found)"
                    r"\s+in\s+(\d+)")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    txt = "".join(cap)
    for m in BR.finditer(txt):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split()) or "<EMPTY>"
    m = ERRMSG.search(txt)
    if m:
        return f"UNTRAPPED {m.group(1)} in {m.group(2)}"
    return "<NO OUTPUT>"


def main():
    only, sides, raw = None, ["vg8020", "cf3300", "zb"], False
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
        elif a == "--raw":
            raw = True
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
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:9s} {faces[s][l]!r}", flush=True)
            if raw and ("<NO" in faces[s][l] or "UNTRAP" in faces[s][l]):
                scr = "".join(caps[0] or [])
                keep = [ln.rstrip() for ln in scr.split("\n") if ln.strip()]
                print(f"      RAW: {keep[-8:]}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = nmeas = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)"); continue
        if len(refs) != 1:
            print(line + "   !! THE REFERENCES DISAGREE -- not a want"); continue
        if any("<NO" in v for v in vals.values()):
            print(line + "   .... NOT MEASURED"); continue
        nmeas += 1
        if vals["zb"] not in refs:
            ndiff += 1; print(line + "   *** DIFF")
        else:
            print(line)
    print(f"\nROWS: {len(labels)} printed, {nmeas} scored -- {ndiff} DIFF")


if __name__ == "__main__":
    main()
