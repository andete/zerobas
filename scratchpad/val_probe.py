#!/usr/bin/env python3
r"""D-VAL — VAL is a whole number parser, and it had ONE row.

`probes/basic/basic_probe_string.py` carries exactly one VAL case:
`VAL("34")+1` -> 35. That is a thin surface for a function whose job is to
re-implement the tokeniser's numeric scanner over arbitrary user text: bases,
exponents, signs, embedded spaces, partial parses and junk.

⚠️ VAL NEVER RAISES ON JUNK -- it returns 0 -- so a wrong answer here is SILENT,
which this project ranks worse than a refusal. That is the reason to sweep it:
there is no error code to notice, only a number that is quietly not the
reference's number.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr, extra=None):
    CASES[lab] = (setup, expr, list(extra or [])); ORDER.append(lab)

# --- the plain cases --------------------------------------------------------
add('p.int',     [], 'VAL("34")')
add('p.neg',     [], 'VAL("-34")')
add('p.plus',    [], 'VAL("+34")')
add('p.frac',    [], 'VAL("1.5")')
add('p.lead',    [], 'VAL(".5")')
add('p.trail',   [], 'VAL("5.")')

# --- junk and partial parses: VAL returns what it could read, never raises ---
add('j.empty',   [], 'VAL("")')
add('j.alpha',   [], 'VAL("ABC")')
add('j.tail',    [], 'VAL("12ABC")')
add('j.sign',    [], 'VAL("-")')
add('j.dot',     [], 'VAL(".")')
add('j.mid',     [], 'VAL("1.2.3")')
add('j.spacelead', [], 'VAL("  12")')
add('j.spacemid',  [], 'VAL("1 2")')
add('j.tabish',  [], 'VAL(" - 12")')
# --- HOW FAR CAN A NUMBER SPAN? This decides whether VAL can work on a BOUNDED
# copy of the body, or needs the whole 255 bytes terminated. `VAL("1 2")` = 12
# says spaces INSIDE a number are skipped, so the source span is not bounded by
# the digit count. Measure the pathological shapes before designing around them.
add('w.sp10',    [], 'VAL("1          2")')
add('w.sp40',    [], 'VAL("1' + ' ' * 40 + '2")')
add('w.spsign',  [], 'VAL("-          12")')
add('w.spdot',   [], 'VAL("1 . 5")')
add('w.spexp',   [], 'VAL("1 E 3")')
add('w.tail40',  [], 'VAL("12' + 'Z' * 40 + '")')

# --- bases: MSX VAL accepts the &H / &O / &B literal forms ------------------
add('b.hex',     [], 'VAL("&HFF")')
add('b.hexlow',  [], 'VAL("&hff")')
add('b.hexbare', [], 'VAL("&H")')
add('b.oct',     [], 'VAL("&O17")')
add('b.bin',     [], 'VAL("&B101")')
add('b.hextail', [], 'VAL("&HFFZZ")')
add('b.amp',     [], 'VAL("&")')
# --- base edge cases the first pass did not ask, needed BEFORE writing code ---
add('b.nopfx',   [], 'VAL("&17")')       # '&' + digits, no base letter
add('b.hsign',   [], 'VAL("-&H10")')     # a sign in front of a base literal
add('b.hspace',  [], 'VAL("&H 10")')     # a space between prefix and digits
add('b.hbad',    [], 'VAL("&HZZ")')      # prefix, then nothing valid
add('b.obad',    [], 'VAL("&O9")')       # 9 is not an octal digit
add('b.bbad',    [], 'VAL("&B2")')       # 2 is not a binary digit
add('b.hbig',    [], 'VAL("&HFFFF")')    # the 16-bit ceiling
add('b.hover',   [], 'VAL("&H1FFFF")')   # past it
add('b.lead',    [], 'VAL("  &HFF")')    # leading spaces then a base literal

# --- exponents --------------------------------------------------------------
add('e.e3',      [], 'VAL("1E3")')
add('e.eneg',    [], 'VAL("1E-3")')
add('e.d3',      [], 'VAL("1D3")')
add('e.ebare',   [], 'VAL("1E")')
add('e.big',     [], 'VAL("1E38")')
add('e.plus',    [], 'VAL("1E+3")')
add('e.fracexp', [], 'VAL("1.5E2")')

# --- 🔴 THE ROWS THAT DECIDE THE DESIGN, asked BEFORE the code is written.
# tk_float's own classification has three answers this parser has never had to
# give: a value past int16 (which becomes a FLOAT, not a wrapped integer), a
# TYPE SUFFIX (!/#/%), and the OVERFLOW reject -- whose VAL-mode answer is the
# one piece D-VALFLOAT's spec named as still open.
add('x.40000',   [], 'VAL("40000")')
add('x.n32768',  [], 'VAL("-32768")')
add('x.n40000',  [], 'VAL("-40000")')
add('x.ovf',     [], 'VAL("1E99")')
add('x.ovfd',    [], 'VAL("1D99")')
add('x.under',   [], 'VAL("1E-99")')
add('x.bang',    [], 'VAL("1.5!")')
add('x.hash',    [], 'VAL("1#")')
add('x.pct',     [], 'VAL("12%")')
add('x.pctfrac', [], 'VAL("1.7%")')
add('x.dbl',     [], 'VAL("1.234567890123")')
add('x.hexdot',  [], 'VAL("&HFF.5")')
add('x.pct9',    [], 'VAL("1.9%")')
add('x.pct25',   [], 'VAL("2.5%")')
add('x.pctbig',  [], 'VAL("40000.5%")')
add('x.pct007',  [], 'VAL("0.07%")')

# --- STR$, which the Phase-3 deferral note pairs with VAL ("floats in
# VAL/STR$"). If the note is stale for one it may be stale for both.
add('s.int',     [], 'STR$(34)')
add('s.neg',     [], 'STR$(-34)')
add('s.frac',    [], 'STR$(1.5)')
add('s.small',   [], 'STR$(.5)')
add('s.big',     [], 'STR$(1E9)')
add('s.roundtrip', [], 'VAL(STR$(1.5))')

# --- 🟢 the arithmetic context, which is what the one existing row tested ----
add('g.plus1',   [], 'VAL("34")+1')
add('g.var',     ['A$="7.5"'], 'VAL(A$)*2')
# --- 🔴 CONTROLS THAT SEPARATE THE LAYERS. If these are wrong too, the gap is
# FLOAT LITERALS and the arithmetic path, not VAL/STR$ -- a completely different
# (and much larger) finding. Naming the second possible cause before attributing
# the defect. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
add('c.lit',     [], '1.5')
add('c.litbig',  [], '1E9')
add('c.arith',   [], '3/2')
add('c.hexlit',  [], '&HFF')
# 🔴 THE SECOND CAUSE OF GREEN, and of red: every x.* row above has a LITERAL
# twin here. If VAL and the literal disagree on the same text, the answer is
# VAL's own; if they agree, the rule belongs to the crunch and a VAL fix must not
# invent a different one. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
add('c.pctlit',  [], '1.7%')
add('c.underlit',[], '1E-99')
add('c.ovflit',  [], '1E99')
add('c.40000lit',[], '40000')
add('c.banglit', [], '1.5!')
# 🔴 TRUNCATE OR ROUND? `1.7%` -> 1 cannot tell them apart on its own if the
# rule were "round toward zero"; `1.9%` and `2.5%` can. And the `%` range is
# +-32767, so a fractional literal whose INTEGER part is out of range asks
# whether the check runs before or after the truncation.
add('c.pct9lit', [], '1.9%')
add('c.pct25lit',[], '2.5%')
add('c.pct0lit', [], '0.7%')
add('c.pctdot',  [], '.5%')
add('c.pctbig',  [], '40000.5%')
add('c.pctzero', [], '0%')
# 🔴 THE ROW K-PT2 SAID WAS MISSING. `.5%` and `0.7%` do NOT exercise the
# negative-difference clamp: TKPOS counts DIGITS and the dot does not advance it,
# so `.5` has TKINTLEN=0 with TKNZPOS=0 and `0.7` has 1 and 1 -- a difference of
# zero, not a negative. TKNZPOS only passes TKINTLEN when the FRACTION has its
# own leading zeros. The arm reddened nothing until this row existed.
add('c.pct007lit',[], '0.07%')
add('c.pctd07lit',[], '.007%')
# the underflow boundary: the crunch's own rule is "dec_exp<=-64 reads as 0, no
# error", and 1E-99 refuses on both references, so the boundary is somewhere in
# between and this is where it gets named instead of assumed.
add('c.e64lit',  [], '1E-64')
add('c.e65lit',  [], '1E-65')
add('c.e70lit',  [], '1E-70')
add('c.e66lit',  [], '1E-66')
add('c.e67lit',  [], '1E-67')
add('c.e68lit',  [], '1E-68')
add('c.e69lit',  [], '1E-69')

# --- 🔴 WHAT ERL READS AFTER A TYPE-IN ERROR, and it needs its own instrument.
# The rows above read `ERR 6 AT 65535` on the references and `AT 0` here, but
# they read it through line 60 having been REJECTED, so they cannot say whether
# the 65535 is the line-entry error's doing or the missing line's. These three
# leave line 60 intact and read ERL as a VALUE, after a bad line typed behind it.
# ⚠️ TWO ARMS SHARE dl_ovf_report -- the crunch reject AND the out-of-range line
# number -- so both get a row before either gets a fix.
# [[a-shared-tail-is-not-a-decision]]
add('c.erlovf',  [], 'ERL', ['70 X=1E99'])
add('c.erlbadln',[], 'ERL', ['70000 X=1'])
add('c.erlnone', [], 'ERL')
add('ctl.num',   [], '1+1')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
diff, blind, no_oracle = [], [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if len(set(refs)) > 1:
        no_oracle.append(l)
    elif not same:
        diff.append(l)
    if any(any(m in str(res[s].get(l)) for m in ("<NO OUTPUT>", "<NO CAPTURE>", ';"'))
           for s in sides):
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'NO-ORACLE' if l in no_oracle else ('SAME' if same else 'DIFF')}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER) - len(no_oracle)} scorable"
      + ("  " + " ".join(diff) if diff else ""))
if no_oracle:
    print(f"⚠️  {len(no_oracle)} NO-ORACLE row(s): " + " ".join(no_oracle))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
