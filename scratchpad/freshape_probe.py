#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FREPLUS14 (2026-10-17), the measure-first step: how much does FRE(0) read below a
plain `A=FRE(0)` in each expression and statement SHAPE, on each machine? Joost ruled
(2026-10-16) that FRE(0) must match the reference "in every expression shape": the
reference counts down to the LIVE stack, so every construct's stack use shows. This is
the table any implementation has to reproduce.

Every variable exists before the first reading (FRE.md's rule). Each `B=<shape>` row
uses a shape whose VALUE is FRE(0) itself and prints A-B; the P rows print FRE(0)
raw in a statement where it cannot be stored, and the difference is taken here.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl

SHAPES = [
    ("paren", "(FRE(0))"), ("paren2", "((FRE(0)))"), ("paren3", "(((FRE(0))))"),
    ("add_l", "0+FRE(0)"), ("add_r", "FRE(0)+0"), ("mul_l", "1*FRE(0)"), ("mul_r", "FRE(0)*1"),
    ("addmul", "0+1*FRE(0)"), ("addadd", "0+0+FRE(0)"), ("addpar3", "0+(0+(0+FRE(0)))"),
    ("neg2", "-(-FRE(0))"), ("sub2", "1-(1-FRE(0))"), ("or_l", "0 OR FRE(0)"),
    ("rel_l", "(0=0)*0+FRE(0)"), ("abs", "ABS(FRE(0))"), ("intabs", "INT(ABS(FRE(0)))"),
    ("valstr", "VAL(STR$(FRE(0)))"), ("muldiv", "2*FRE(0)/2"),
    # round 3: the LEFT operand's TYPE (the relational rows read 12 B with an integer
    # left operand and 18 with a double one -- does the pending operator keep it at
    # its own width?)
    ("add_i", "I%+FRE(0)-I%"), ("add_s", "S!+FRE(0)-S!"), ("add_d", "D#+FRE(0)-D#"),
    ("mul_d", "E#*FRE(0)"),
]
def prog1(rows):                               # <= ~18 rows: more scroll off the screen
    return (["NEW", "10 DIM R(1):A=0:B=0:I=0:B$=\"\":I%=0:S!=0:D#=0:E#=1", "20 A=FRE(0)"]
            + [f"{30 + 2 * i} B={sh}:PRINT\"[{n}\";A-B;\"]\"" for i, (n, sh) in enumerate(rows)]
            + ["RUN"])
# statements: the raw FRE(0) where it cannot be stored; B where it can
PROG2 = ["NEW", "10 DIM R(1):A=0:B=0:I=0:B$=\"\":DEF FNF(X)=FRE(0)+X", "20 A=FRE(0)",
         '30 PRINT"[base";A;"]"',
         '40 PRINT"[print";FRE(0);"]"',
         '50 PRINT"[print2";0;FRE(0);"]"',
         '60 R(0)=FRE(0):PRINT"[arytgt";A-R(0);"]"',
         '70 FOR I=FRE(0) TO 99999!:B=I:I=99999!:NEXT:PRINT"[forstart";A-B;"]"',
         '80 B=FNF(0):PRINT"[fn";A-B;"]"',
         '90 GOSUB 200:PRINT"[gosub";A-B;"]"',
         '100 B$=STR$(FRE(0)):B=VAL(B$):PRINT"[letstr";A-B;"]"',
         '105 B=VAL(""+STR$(FRE(0))):PRINT"[concat";A-B;"]"',
         '110 B=FRE(0):PRINT"[again";A-B;"]":END',
         "200 B=FRE(0):RETURN", "RUN"]
THRESH = [("rel_lt", "A-K<FRE(0)"), ("rel_eq", "(A-K<FRE(0))=(0=0)"),
          ("and_l", "-1 AND (A-K<FRE(0))"), ("xor_l", "0 XOR (A-K<FRE(0))"),
          ("mod_l", "(A-K<FRE(0)) MOD 2"), ("idiv_l", "(A-K<FRE(0))\\1"),
          ("pow_l", "(A-K<FRE(0))^1"), ("not", "NOT(A-K<FRE(0))"),
          # 2026-10-17, round 2: the operator PENDING on the RIGHT side, the threshold
          # test nested inside it (its own 6 + 18 are known; T = (A-K<FRE(0)))
          ("mod_r", "8 MOD ((A-K<FRE(0))-2)"), ("idiv_r", "8\\((A-K<FRE(0))-2)"),
          ("pow_r", "2^(A-K<FRE(0))"), ("div_r", "1/((A-K<FRE(0))-2)"),
          ("eqv_r", "0 EQV (A-K<FRE(0))"), ("imp_r", "-1 IMP (A-K<FRE(0))"),
          ("eq_r", "0=(A-K<FRE(0))"), ("ne_r", "0<>(A-K<FRE(0))"), ("ge_r", "-1>=(A-K<FRE(0))"),
          ("le_r", "0<=(A-K<FRE(0))"), ("gt_r", "0>(A-K<FRE(0))"),
          ("ary", "R((A-K<FRE(0))+1)"), ("rel_i", "A%-K%<FRE(0)"), ("mid2", "VAL(MID$(\"1234567\",2+(A-K<FRE(0)),1))")]
# the parts of each threshold row that are already known, so the report can show the
# construct's own cost: (row, known bytes)
KNOWN = {"mod_r": 12 + 18, "idiv_r": 12 + 18, "div_r": 12 + 18, "pow_r": 6 + 18,
         "eqv_r": 6 + 18, "imp_r": 6 + 18, "eq_r": 6 + 18, "ne_r": 6 + 18, "ge_r": 6 + 18,
         "le_r": 6 + 18, "gt_r": 6 + 18, "ary": 6 + 18, "mid2": 10 + 10 + 6 + 18}
# A row's value flips at the first K > 25 + depth (FRE(0) inside the FOR reads
# A - 25 - depth): depth = K* - 26. Three lines a row -- an IF ends its line, so the
# NEXT must not share one (a first cut put it after the IF and nothing printed).
def prog3(rows):
    # at most ~18 rows a program: more and the first readings SCROLL off the screen
    # (round 3's first run lost rel_lt that way)
    return (["NEW", "10 DIM R(1):R(0)=0:R(1)=1:A=0:B=0:K=0:C=0:Z=0:A%=0:K%=0", "20 A=FRE(0):A%=A"]
         + [ln for i, (n, e) in enumerate(rows) for ln in (
             f"{30 + 4 * i} C=0:FOR K=0 TO 80:K%=K:B={e}:IF K=0 THEN Z=B",
             f"{31 + 4 * i} IF B<>Z AND C=0 THEN C=K",
             f"{32 + 4 * i} NEXT:PRINT\"[{n}\";C-26;\"]\"")]
         + ["RUN"])
# IF's condition context: the same threshold, four lines (the IF ends its line)
PROG4 = ["NEW", "10 A=0:B=0:K=0:C=0:Z=0", "20 A=FRE(0)",
         "30 C=0:FOR K=0 TO 80:B=0:IF (A-K<FRE(0)) THEN B=1",
         "31 IF K=0 THEN Z=B", "32 IF B<>Z AND C=0 THEN C=K",
         '33 NEXT:PRINT"[ifcond";C-26;"]"', "RUN"]
KNOWN["ifcond"] = 6 + 18
MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")


def readings(scr):
    flat = " ".join(scr[i:i + 40] for i in range(0, len(scr or ""), 40))
    return dict(re.findall(r"\[([a-z0-9_]+)\s*(-?\d+)\s*\]", flat)) | \
        {f"_{k}": v for k, v in re.findall(r"\[([a-z0-9]+)\s+-?\d+\s+(-?\d+)\s*\]", flat)}


def main():
    got = {m: {} for m in MACHINES}
    for prog in (prog1(SHAPES[:12]), prog1(SHAPES[12:]), PROG2, prog3(THRESH[:12]),
                 prog3(THRESH[12:]), PROG4):
        for m in MACHINES:
            scr = omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=60.0)[0]
            got[m] |= readings(scr)
    vg, zb = (got[m] for m in MACHINES)
    for g in (vg, zb):                              # raw PRINT readings -> differences from A
        a = int(g.get("base", 0))
        if "print" in g:
            g["print"] = str(a - int(g["print"]))
        if "_print2" in g:
            g["print2"] = str(a - int(g["_print2"]))
    keys = ([n for n, _ in SHAPES] + [n for n, _ in THRESH] + ["ifcond"]
            + ["print", "print2", "arytgt", "forstart", "fn", "gosub", "letstr", "concat", "again"])
    print(f"{'shape':10} {'VG':>6} {'ZB':>6}        own (VG depth - the known parts)")
    for k in keys:
        v, z = vg.get(k, "-"), zb.get(k, "-")
        own = f"  own {int(v) - KNOWN[k]:>4}" if k in KNOWN and v != "-" else ""
        print(f"{k:10} {v:>6} {z:>6}  {'SAME' if v == z else 'DIFF'}{own}")


if __name__ == "__main__":
    main()
