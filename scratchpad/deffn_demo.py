#!/usr/bin/env python3
"""D-DEFFNLAND — the closing demo: real MSX BASIC on the SHIPPING ROM.

Two kinds of row, and they are asked different questions:

  fn.*    THE VERB. Before this slice every one of these was `Syntax error`
          on zerobas -- recorded, not assumed: `make kwsweep` at the previous
          run printed `deffn  ABSENT MISSING  ref '[ 3 ]' vs zb 'Syntax error
          in 10'`, and `make deffn-acceptance` scored 67 of 69 subject rows
          divergent. The BEFORE column below is that reading; the AFTER column
          is this run.
  car.*   THE CARVES that paid for it (the two clone collapses) and the two
          leaves PROMOTED from page 1 into the low region. Their claim is the
          opposite one -- that nothing observable moved -- so their BEFORE and
          AFTER are the same and the reference columns are the whole check.

🔴 THE READOUT SHAPE IS INHERITED FROM scratchpad/dupspan2_demo.py AND ITS TWO
BLIND DRAFTS. Every row puts its VALUE inside the brackets; the fall-through
line prints NOTHING, so a row that produced no value reads `<NO OUTPUT>` -- a
missing measurement, which is not a divergence and must not read as agreement.
Rows whose answer is an ERROR say so through the ON ERROR handler.
"""
from __future__ import annotations
import os, re, sys
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}

SYNERR = "ERR 2"        # what zerobas answered every fn.* row before the verb

# label, what it exercises, program lines, the RECORDED pre-slice zb reading
CASES = [
    ("fn.basic",  "the verb at all",
     ['DEF FNA(X)=X+1', 'PRINT"[";FNA(2);"]"'], SYNERR),
    ("fn.defint", "an INT result -- the value lives in DE across a CALSLT",
     ['DEFINT A-Z', 'DEF FNA(X)=X+1', 'PRINT"[";FNA(2);"]"'], SYNERR),
    ("fn.pct",    "the result is coerced to the FN's OWN type",
     ['DEF FNA%(X)=X/2', 'PRINT"[";FNA%(5);"]"'], SYNERR),
    ("fn.bang",   "...and its `!` twin is not (the same body, 2.5)",
     ['DEF FNA!(X)=X/2', 'PRINT"[";FNA!(5);"]"'], SYNERR),
    ("fn.str",    "a `$` function, and PRINT classifying the item",
     ['DEF FNA$(X$)=X$+"!"', 'PRINT"[";FNA$("hi");"]"'], SYNERR),
    ("fn.shadow", "the formal is a SHADOW: the program's X is untouched",
     ['X=5', 'DEF FNA(X)=X*10', 'PRINT"[";FNA(9);X;"]"'], SYNERR),
    ("fn.actual", "...but the ACTUAL is evaluated in the CALLER's scope",
     ['X=5', 'DEF FNA(X)=X*10', 'PRINT"[";FNA(X+1);"]"'], SYNERR),
    ("fn.nest",   "nesting: the outer frame comes BACK",
     ['DEF FNA(X)=X', 'DEF FNB(X)=FNA(X+1)+X', 'PRINT"[";FNB(3);"]"'], SYNERR),
    ("fn.arity",  "ERR 2 -- the two delimiter lists must AGREE",
     ['DEF FNA(X)=X', 'PRINT FNA(1,2)'], SYNERR),
    ("fn.ceil",   "ERR 5 at the TENTH formal -- a division, not a rule",
     ['DEF FNA(A,B,C,D,E,F,G,H,I,J)=A', 'PRINT FNA(1,2,3,4,5,6,7,8,9,10)'], SYNERR),
    ("fn.undef",  "ERR 18, which nothing in this ROM could reach before",
     ['PRINT FNZ(1)'], SYNERR),
    ("fn.clear",  "CLEAR erases a definition (it lives in the variable chain)",
     ['DEF FNA(X)=X', 'CLEAR', 'PRINT FNA(1)'], SYNERR),
    # --- the carves and the promotion: nothing observable may have moved ---
    ("car.savdsk", "sav_flag_a, disk entry: SAVE\"...\",B is refused",
     ['SAVE"A:ZZ.BAS",B'], "load error"),
    ("car.savcas", "sav_flag_a, cassette entry: the SECOND caller",
     ['SAVE"CAS:ZZ",B'], "load error"),
    ("car.dbl",    "arga_pack_fac -- the 7-mantissa-byte (double) entry",
     ['PRINT"[";1/3;"]"'], "same"),
    ("car.sng",    "arga_pack_single -- the 3-byte entry, same body now",
     ['A!=1/3', 'PRINT"[";A!;"]"'], "same"),
    ("car.poke",   "basic/poke.asm, PROMOTED into the low region",
     ['POKE &HE000,65', 'PRINT"[";PEEK(&HE000);"]"'], "same"),
    ("car.sound",  "basic/sound.asm, promoted -- and its measured ERR 5 boundary",
     ['SOUND 0,0', 'SOUND 14,0'], "same"),
    ("car.loc",    "loc_missing: the alias that had broken the G8 build gate",
     ['LOCATE ,'], "same"),
]
BR = re.compile(r"\[([^\]]*)\]")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = BR.search(cap)
    return (" ".join(m.group(1).split()) or "<empty>") if m else "<NO OUTPUT>"


def main() -> int:
    step = float(os.environ.get("DEFFN_DEMO_STEP", "4.0"))
    agree = same = 0
    for label, what, prog, before in CASES:
        body = ["10 ON ERROR GOTO 900", "15 SCREEN 0"]
        body += [f"{20+10*k} {ln}" for k, ln in enumerate(prog)]
        body += ['890 END', '900 SCREEN 0:PRINT"[ERR";ERR;"]":END']
        row = {}
        for sd, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=step, cap_gap=10.0,
                timeout=300.0)
            row[sd] = face(caps[0])
        ok_refs = row["vg8020"] == row["cf3300"]
        ok_zb = row["zb"] == row["vg8020"]
        agree += ok_refs
        same += ok_zb
        print(f"  {label:11s} {'refs-agree' if ok_refs else 'REFS DIFFER':12s} "
              f"{'zb=same' if ok_zb else 'zb=DIFF':8s} "
              f"before={before!r:16s} vg={row['vg8020']!r} cf={row['cf3300']!r} "
              f"zb={row['zb']!r}   [{what}]", flush=True)
    print(f"\n  {same} of {len(CASES)} zerobas readings match the VG-8020; "
          f"{agree} of {len(CASES)} references agree with each other", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
