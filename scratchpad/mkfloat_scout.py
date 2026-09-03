#!/usr/bin/env python3
r"""D-MKFLOAT scout — is zerobas's stored float BYTE-IDENTICAL to the reference's?

`MKS$` / `MKD$` / `CVS` / `CVD` are missing (filed 2026-09-03 by D-DEFERCHECK;
`MKS$` returns an EMPTY STRING, which is a silent wrong answer). `MKI$`/`CVI`
already ship and are a 2-byte copy out of the evaluated operand.

🎯 THE WHOLE SIZE OF THE SLICE TURNS ON ONE QUESTION THIS PROBE ASKS FIRST.
`basic/sysvars.inc` describes FAC as "value bytes as tokenised (8)" with a lead
byte (sign + excess-64 exponent) and a packed-BCD mantissa of 3 bytes (single) /
7 bytes (double) — i.e. the MSX2-TH number format. IF that is byte-identical to
what the reference stores, `MKS$` is `MKI$` with a different length and the slice
is small. If it is not, `MKS$` needs a FORMAT CONVERSION and the slice is a
different animal — and, worse, a string written to disk by one machine would not
read back on the other.

⚠️ THE QUESTION IS ASKED WITHOUT USING `MKS$`, DELIBERATELY. `MKS$` does not
exist here, so a probe built on it can only report its absence. `VARPTR` + `PEEK`
reads the STORED bytes of an ordinary variable on all three machines, so the
representation is compared directly and the answer does not depend on the verb
this slice is about.

🟢 CONTROLS. `i.*` reads a `%` INTEGER variable, whose 2-byte layout is already
known to agree (`CVI(MKI$(258))` = 258 on both). If an `i.*` row diverges the
instrument is wrong — VARPTR, PEEK, or the variable-store layout — and nothing
the `s.*`/`d.*` rows say can be believed.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

def bytes_of(var, n):
    """the n stored bytes of `var`, as one space-separated readout"""
    return ";".join(f"PEEK(VARPTR({var})+{i})" for i in range(n))

# --- 🟢 CONTROL: the integer pair, whose agreement is already established ----
add('i.258',  ['A%=258'],      bytes_of('A%', 2))
add('i.neg',  ['A%=-1'],       bytes_of('A%', 2))

# --- SINGLE precision: the 4 bytes MKS$ would have to emit -------------------
add('s.1p5',  ['A!=1.5'],      bytes_of('A!', 4))
add('s.one',  ['A!=1'],        bytes_of('A!', 4))
add('s.zero', ['A!=0'],        bytes_of('A!', 4))
add('s.neg',  ['A!=-1.5'],     bytes_of('A!', 4))
add('s.tenth',['A!=.1'],       bytes_of('A!', 4))
add('s.big',  ['A!=123456'],   bytes_of('A!', 4))
add('s.small',['A!=1E-9'],     bytes_of('A!', 4))

# --- 🔴 ZERO'S MANTISSA: zerobas leaves it $FF where both references store 0.
# Found by this scout while asking a different question. It is INVISIBLE today --
# lead byte 0 means "the value is zero" and the formatter never reads further --
# and it becomes USER-VISIBLE the moment `MKS$` ships, because `MKS$(0)` would
# emit CHR$(0)+CHR$(255)*3 and write that to disk. These rows separate the
# CRUNCH-time zero (a literal) from a RUNTIME zero (computed), which is the
# question that says where the fix goes.
add('z.lit',   ['A!=0'],        bytes_of('A!', 4))
add('z.dot',   ['A!=0.0'],      bytes_of('A!', 4))
add('z.calc',  ['A!=1-1'],      bytes_of('A!', 4))
add('z.mul',   ['A!=5*0'],      bytes_of('A!', 4))
add('z.under', ['A!=1E-99'],    bytes_of('A!', 4))
add('z.int',   ['A!=0%'],       bytes_of('A!', 4))
add('z.reassign', ['A!=1.5', 'A!=0'], bytes_of('A!', 4))
add('z.dcalc', ['A#=1-1'],      bytes_of('A#', 8))
add('z.dlit',  ['A#=0'],        bytes_of('A#', 8))
# 🟢 CONTROL: the same variable slot holding a NONZERO value must still read the
# reference's bytes, so a DIFF above is about zero and not about the slot.
add('z.ctl',   ['A!=0', 'A!=1.5'], bytes_of('A!', 4))

# --- IS `var_store_fac` THE ONLY DOOR? Arrays, FOR and READ have their own
# store paths, and a fix sited at the scalar store would leave them behind. The
# denominator matters more than the first site found.
add('z.arr',   ['DIM A!(2)', 'A!(1)=0'],  ";".join(f"PEEK(VARPTR(A!(1))+{i})" for i in range(4)))
add('z.arrctl',['DIM A!(2)', 'A!(1)=1.5'],";".join(f"PEEK(VARPTR(A!(1))+{i})" for i in range(4)))
add('z.read',  ['READ A!', 'DATA 0'],     bytes_of('A!', 4))
add('z.for',   ['FOR A!=0 TO 1', 'NEXT'], bytes_of('A!', 4))
add('z.defsng',['DEFSNG B', 'B=0'],       bytes_of('B', 4))

# 🎯 THE UNSET-VARIABLE READ HAS ITS OWN ZERO EXIT (`var_load_fac`, vars.asm)
# and NO ROW REACHED IT until this one. `B!` was never assigned, so reading it
# runs the "unset -> zero" path; assigning that to `A!` stores whatever FAC held.
# Added because the fix has three call sites and the row set only covered two --
# a third site with no row is a fix nothing can defend.
add('z.unset',  ['A!=B!'],       bytes_of('A!', 4))
add('z.dunset', ['A#=B#'],       bytes_of('A#', 8))

# --- DOUBLE precision: the 8 bytes MKD$ would have to emit -------------------
add('d.1p5',  ['A#=1.5'],      bytes_of('A#', 8))
add('d.one',  ['A#=1'],        bytes_of('A#', 8))
add('d.zero', ['A#=0'],        bytes_of('A#', 8))
add('d.neg',  ['A#=-1.5'],     bytes_of('A#', 8))
add('d.third',['A#=1/3'],      bytes_of('A#', 8))

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>34}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    same = len(set(vals)) == 1
    if not same: diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{v:>34}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF: {len(diff)}/{len(ORDER)}  " + " ".join(diff))
print("done")
