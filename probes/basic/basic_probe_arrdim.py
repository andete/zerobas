#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARR-B -- WHERE THE REFERENCE BOUNDS A DIMENSION, characterised vs the VG-8020.

WHY THIS EXISTS
===============
`CLEAR 100 : DIM Q(20000)` answers **`Subscript out of range`** on the reference
and **`Out of memory`** here (docs/clearpool-vg8020-characterization.md §3). The
reference bounds a dimension BEFORE it tries to allocate; zerobas allocates until
it runs out (sub/arrays.asm `ary_alloc` -> `aal_oom`), so its error is right only
by accident of size. The divergence was found as a calibration row in the D-CLP
matrix aimed at something else entirely, and it lives on in that probe as
`oos-dim-huge` -- reported, never gated -- precisely so it would not be
"discovered" later by a red gate.

⚠️ THE ARRAYS ARC LISTED THIS AND NEVER ANSWERED IT. `docs/spec-basic-arrays.md`
§4 target **#9, "`Out of memory` onset -- the raise point when an array would
overflow the ceiling"**, has no row in the §4.1 results table. Nine other targets
were measured and pinned; this one was asked and dropped. The whole divergence
sits in the hole that left.

WHAT IS ACTUALLY UNKNOWN
========================
Only that the reference raises ERR 9 somewhere zerobas raises ERR 7. The RULE is
unmeasured, and the plausible rules disagree loudly:

  (a) a fixed subscript ceiling   -- `n > K` for some K, type-independent;
  (b) a 16-BIT BYTE-COUNT OVERFLOW -- `elsize*(n+1) > $FFFF`, i.e. the same
      product-overflow zerobas already computes in `ary_count_elems` /
      `ary_mul16_checked`, but reported as ERR 9 instead of being folded into
      the ceiling test;
  (c) an ELEMENT-count overflow    -- `Pi(bound+1) > $FFFF`, type-independent.

(a) is already half-falsified -- `DIM Q(20000)` says ERR 9, so K < 20000, yet a
plain `n > 32767` rule would have said ERR 7 -- but the discriminator that
matters is the **`typ` battery**: an unsuffixed array is DOUBLE (8 B/element), so
(b) predicts the break at `n+1 > 8192` for `#`, `> 16384` for `!` and `> 32768`
for `%`, while (a) and (c) predict the SAME break for all three. One battery,
three rules, one answer.

The `dim` battery separates PER-DIMENSION from PRODUCT: `DIM Q%(200,200)` has two
tiny bounds and 40401 elements. If the rule is per-dimension it allocates (and
dies of RAM); if it is the product it raises ERR 9 with no dimension anywhere
near a ceiling.

READING THIS FILE
=================
⚠️ EVERY ROW IS AN ERROR-CLASS ROW, NOT A NUMBER. The two machines have
different memory maps by construction (~28.8 KB free on the reference, ~15.7 KB
here), so the RAM-exhaustion threshold can never be made to agree and no row may
straddle it. Each `bnd`/`typ`/`dim` row is sized so that BOTH machines are out of
RAM for it: the only thing under measurement is WHICH ERROR the machine picks,
never whether the allocation would have fitted. The sizing is spelled out per row.

⚠️ EVERY LINE IS KEPT UNDER **37** CHARACTERS, NOT 40. Both readouts are
echo-anchored and an echo that WRAPS can never be matched again, because
`_echo_idx` compares whole rows -- the fault that made eleven rows of the first
D-CLP run read `<none>` on the REFERENCE, several of which then scored PASS
because zerobas answered `<none>` too.

⚠️ **D-CLP's guard for that fault was too loose by three, and this probe inherited
it.** It tested against `omsx_repl.COLS` (40, the screen width), but the width
that actually wraps a line is **`LINLEN`, and the two machines do not boot at the
same one**: D-WID measured the reference at **37** and zerobas at 39
(docs/width-vg8020-characterization.md §, "the machines simply boot at different
text widths"). A 39-character row here duly came back `<no echo>` on BOTH
machines and scored **PASS** -- agreeing on nothing, which is the exact failure
mode the guard exists to prevent, sailing straight through the guard.
`ECHO_MAX = 37` below is the reference's boot `LINLEN`, i.e. the tighter of the
two, and it fires before an emulator boots.

⚠️ THE ERROR MESSAGE IS THE READOUT, not `ERR`. `Subscript out of range` and
`Out of memory` are different errors and telling them apart is the entire point;
the message is also what a user sees, and the tail shows an abort's trailing junk
as well. Message case is folded (the documented two-spelling split,
basic/arrays.asm:44).
"""
from __future__ import annotations
import argparse, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# The longest line whose echo is still matchable. NOT `omsx_repl.COLS` (40): a
# line wraps at `LINLEN`, and the reference boots at 37 where zerobas boots at 39
# (docs/width-vg8020-characterization.md). The tighter of the two is the one that
# has to hold, because a row unreadable on EITHER machine is a row that reports
# `<none>` on both and scores PASS. See the docstring.
ECHO_MAX = 37

# (label, battery, [lines]). The LAST line carries the readout and is always short
# enough not to wrap. A line containing '[' is read as a VALUE row (bracket span);
# anything else is read as an ERROR row (echo-anchored screen tail). Batteries:
#   ctl   -- the apparatus. READ FIRST; nothing else is readable if one fails.
#   repro -- the ORACLE's own recorded answers, checked against the REFERENCE
#            column alone. Not a statement about zerobas.
#   bnd   -- WHERE the bound sits, on the default (double) element type.
#   typ   -- does the bound MOVE WITH ELEMENT SIZE? the rule discriminator.
#   dim   -- per-DIMENSION or on the PRODUCT?
#   dom   -- the subscript argument's own domain (past int16, negative).
#   ord   -- which error WINS when two are available.
#   post  -- what survives a failed DIM.
CASES = [
    # --- controls: TWO-SIDED apparatus rows -----------------------------------
    # Rows BOTH machines are expected to pass TODAY. The tempting control -- a
    # huge DIM raising ERR 9 -- is exactly what zerobas must FAIL, so it is a
    # `repro` row instead and is asserted against the reference alone.
    ("ctl-value",    "ctl",  ['DIM Q(10)', 'PRINT "[";Q(10);"]"']),
    ("ctl-oob",      "ctl",  ['DIM Q(2)', 'Q(3)=1']),
    ("ctl-neg",      "ctl",  ['DIM Q(5)', 'Q(-1)=1']),
    ("ctl-redim",    "ctl",  ['DIM Q(3)', 'DIM Q(3)']),
    # the anti-<none> control: a MULTI-LINE case with a VALUE readout, so the
    # shape most rows use is itself proven to report something.
    ("ctl-multi",    "ctl",  ['DIM Q(4)', 'Q(2)=7', 'PRINT "[";Q(2);"]"']),
    # ...and its error-row counterpart: a multi-line case whose readout is a
    # MESSAGE, proving the tail anchors after a preceding statement has run.
    ("ctl-multierr", "ctl",  ['DIM Q(4)', 'Q(2)=7', 'Q(9)=1']),

    # --- reproduction: the ORACLE must still answer what it answered before ----
    # Both recorded 2026-07-29 in docs/clearpool-vg8020-characterization.md §3 /
    # the D-CLP probe's `oos-vs-oom` + `oos-dim-huge` rows. If the VG-8020 stops
    # answering these, nothing else in the run is readable. [[validate-oracle-artifacts]]
    ("repro-soor",   "repro", ['CLEAR 100', 'DIM Q(20000)']),
    ("repro-oom",    "repro", ['CLEAR 100', 'DIM Q(5000)']),

    # --- WHERE IS THE BOUND? default type = DOUBLE, 8 bytes per element -------
    # Sizing: 5001*8 = 40008 B and 8001*8 = 64008 B both exceed the free variable
    # space on BOTH machines, so a machine WITHOUT a dimension bound must answer
    # `Out of memory` for every row here and one WITH it flips at its own K.
    # Rule (b) predicts the flip between 8190 (65528 B, fits 16 bits) and
    # 8191 (65536 B, does not).
    ("bnd-5000",     "bnd", ['DIM Q(5000)']),
    ("bnd-8000",     "bnd", ['DIM Q(8000)']),
    ("bnd-8190",     "bnd", ['DIM Q(8190)']),
    ("bnd-8191",     "bnd", ['DIM Q(8191)']),
    ("bnd-8192",     "bnd", ['DIM Q(8192)']),
    ("bnd-10000",    "bnd", ['DIM Q(10000)']),
    ("bnd-16384",    "bnd", ['DIM Q(16384)']),
    ("bnd-20000",    "bnd", ['DIM Q(20000)']),
    ("bnd-32767",    "bnd", ['DIM Q(32767)']),

    # --- DOES THE BOUND MOVE WITH ELEMENT SIZE? the rule discriminator --------
    # `%` = 2 B, `!` = 4 B, `#` = 8 B (explicit, so this does not ride on the
    # unsuffixed default). Rule (b) puts each break at elsize*(n+1) > $FFFF:
    # `%` between 32766/32767, `!` between 16382/16383, `#` between 8190/8191.
    # Rules (a) and (c) put ALL THREE at the same n. Every row is far past both
    # machines' free RAM, so `Out of memory` is the no-bound answer throughout.
    ("typ-i-20000",  "typ", ['DIM Q%(20000)']),
    ("typ-i-32766",  "typ", ['DIM Q%(32766)']),
    ("typ-i-32767",  "typ", ['DIM Q%(32767)']),
    ("typ-s-16382",  "typ", ['DIM Q!(16382)']),
    ("typ-s-16383",  "typ", ['DIM Q!(16383)']),
    ("typ-d-8190",   "typ", ['DIM Q#(8190)']),
    ("typ-d-8191",   "typ", ['DIM Q#(8191)']),
    # a STRING array: its element is a descriptor, not a value, so its elsize is
    # a THIRD number and pins the rule a third time.
    ("typ-str-20000", "typ", ['DIM Q$(20000)']),
    ("typ-str-32767", "typ", ['DIM Q$(32767)']),
    # ...and the pair that PINS the string element width, which the two rows
    # above only bracket to {2,3}: at elsize 3 the break is 21845/21846 elements
    # (65535 B / 65538 B), at elsize 2 BOTH of these are far under $FFFF and both
    # answer `Out of memory`. 21845*3 = $FFFF EXACTLY, so this pair also settles
    # whether the test is `> $FFFF` or `>= $FFFF` -- the only element width in the
    # language that can land on the boundary, since 2/4/8 all skip straight from
    # 65534/65532/65528 to 65536.
    ("typ-str-21844", "typ", ['DIM Q$(21844)']),
    ("typ-str-21845", "typ", ['DIM Q$(21845)']),

    # --- PER-DIMENSION OR ON THE PRODUCT? -------------------------------------
    # Two tiny bounds, a huge product. If the rule is per-dimension these fall
    # through to the allocator and die of RAM; if it is the product they raise
    # the bound error with no single dimension anywhere near a ceiling.
    ("dim-200x200",  "dim", ['DIM Q%(200,200)']),      # 40401 el, 80802 B
    ("dim-150x150",  "dim", ['DIM Q%(150,150)']),      # 22801 el, 45602 B: the
                                                        # product FITS 16 bits and
                                                        # exceeds both machines'
                                                        # RAM -> the no-overflow
                                                        # control for this battery
    ("dim-huge1st",  "dim", ['DIM Q%(32767,0)']),      # dim 0 alone is at the
                                                        # single-dim break
    ("dim-huge2nd",  "dim", ['DIM Q%(0,32767)']),      # ...and the same bound in
                                                        # the SECOND position: a
                                                        # rule that only checks
                                                        # dim 0 differs here
    ("dim-3d",       "dim", ['DIM Q%(40,40,40)']),     # 68921 el, 137842 B
    # ⚠️ THE AUTO-DIM PATH IS A SECOND ALLOCATOR ENTRY and nothing above reaches
    # it. First touch of an undeclared array auto-dims EVERY dimension to 10
    # (§4.1), so four subscripts of a DOUBLE array ask for 11^4 * 8 = 117128 B --
    # over $FFFF without a single number in the source line being large. If the
    # bound is a property of DIM it answers `Out of memory` here; if it is a
    # property of the ALLOCATOR it answers the bound error.
    ("auto-4d",      "dim", ['Q(1,1,1,1)=1']),         # 14641 el, 117128 B
    # ...its control: the same shape at 2 B/element is 29282 B, under $FFFF and
    # over both machines' free RAM, so it must be `Out of memory` either way.
    ("auto-4d-int",  "dim", ['Q%(1,1,1,1)=1']),        # 14641 el, 29282 B
    # ⚠️ AND WHILE THE MATRIX IS HERE: zerobas caps subscripts at MAXDIM=4
    # (basic/sysvars.inc:1544, a slice-1 cap -- ">MAXDIM subscripts -> Subscript
    # out of range"). Whether the REFERENCE caps at 4 was never measured. Tiny
    # bounds, so nothing here is about size: a reference that allows five
    # dimensions simply succeeds and prints no error.
    ("dim-5dim",     "dim", ['DIM Q%(1,1,1,1,1)']),    # 32 el, 64 B
    # ...and how far it actually goes, so the finding is a MEASUREMENT and not
    # just "more than four". Both are tiny: 256 elements / 1 element.
    ("dim-8dim",     "dim", ['DIM Q%(1,1,1,1,1,1,1,1)']),
    # ⚠️ 12, not 16. The 16-dimension form is 39 characters, which read `<no echo>`
    # on BOTH machines and scored PASS -- see the ECHO_MAX note in the docstring.
    ("dim-12dim",    "dim", ['DIM Q%(0,0,0,0,0,0,0,0,0,0,0,0)']),

    # --- the subscript ARGUMENT's own domain ----------------------------------
    # Past int16 the argument cannot even be represented, so a THIRD error is
    # available and its precedence is part of the contract.
    ("dom-32768",    "dom", ['DIM Q(32768)']),
    ("dom-65535",    "dom", ['DIM Q(65535)']),
    ("dom-99999",    "dom", ['DIM Q(99999)']),
    ("dom-neg",      "dom", ['DIM Q(-1)']),
    ("dom-frac",     "dom", ['DIM Q(20000.7)']),
    ("dom-zero",     "dom", ['DIM Q(0)', 'PRINT "[";Q(0);"]"']),

    # --- WHICH ERROR WINS ------------------------------------------------------
    ("ord-redim",    "ord", ['DIM Q(3)', 'DIM Q(20000)']),
    ("ord-syntax",   "ord", ['DIM Q(20000),']),
    # a comma-separated list: does the FIRST array survive the SECOND's failure?
    # (`P` is legal and tiny; `Q` is the huge one.)
    # ⚠️ THE OBVIOUS READOUT AGREES FOR THE WRONG REASON. The first draft read
    # `PRINT P(0)`, which answered ` 0 ` on BOTH machines -- but an array that was
    # never created AUTO-DIMS to 10 on first touch and reads 0 too, so the row
    # passed whether P survived or not. Re-DIMing is the discriminator that a
    # value read can never be: `Redimensioned array` means P is there.
    ("ord-list",     "ord", ['DIM P(2),Q(20000)', 'DIM P(2)']),

    # --- WHAT SURVIVES A FAILED DIM -------------------------------------------
    # After the failure, is Q defined? Re-DIMing it is the clean discriminator:
    # `Redimensioned array` means the failed DIM left a descriptor behind,
    # an empty tail (the second DIM simply worked) means it did not.
    ("post-redim",   "post", ['DIM Q(20000)', 'DIM Q(3)']),
    # ...and the same claim from the other side, via a subscript the AUTO-DIM
    # bound excludes. `Q(11)` is out of range for an auto-dimmed 0..10 array and
    # in range for the 0..20000 one the failed DIM asked for, so this row reads
    # the rollback rather than the auto-dim. (`PRINT Q(10)` -- the first draft --
    # reads 0 either way and measures nothing, the same fault as `ord-list`.)
    ("post-auto",    "post", ['DIM Q(20000)', 'Q(11)=1']),
]


# The `repro` battery's expected REFERENCE answers. Checked against the oracle
# column ALONE: if the VG-8020 stops answering these, the oracle or the harness
# moved since docs/clearpool-vg8020-characterization.md §3, and no other row in
# the run means anything -- regardless of whether zerobas happens to agree.
REPRO_EXPECT = {
    "repro-soor": "Subscript out of range",
    "repro-oom":  "Out of memory",
}

# Rows kept as a RECORD rather than gated, with the reason.
#
# 🔴 D-ARR-C -- A SECOND, SEPARATE DIVERGENCE, found by this matrix's calibration
# while it was measuring something else. `MAXDIM = 4` (basic/sysvars.inc:1544) is
# a slice-1 implementation cap that was written down as a design decision and
# never measured against the reference: the reference accepts **at least twelve**
# dimensions and zerobas raises `Subscript out of range` at five. That is its own
# item -- raising the cap costs RAM in the `ARY_IDX` subscript block and widens
# every descriptor, and it has nothing to do with the byte-count rule this slice
# implements. Recorded here, exactly as D-CLP recorded `oos-dim-huge`, so it
# cannot be "discovered" later by a red gate. It turns from `----` into a
# gateable row the day the cap is raised.
NEVER_GATED = {
    "dim-5dim":  "D-ARR-C: MAXDIM=4 vs the reference's >=12",
    "dim-8dim":  "D-ARR-C: MAXDIM=4 vs the reference's >=12",
    "dim-12dim": "D-ARR-C: MAXDIM=4 vs the reference's >=12",
}


def norm(s):
    """Fold message case (the documented two-spelling divergence). Runs of spaces
    are COLLAPSED but never dropped, so whitespace-only junk still differs from no
    junk at all."""
    if s is None:
        return None
    return " ".join(s.casefold().replace("|", " | ").split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only")
    ap.add_argument("--batch", action="store_true",
                    help="share one boot across the matrix. NOT the default: a "
                         "case that SUCCEEDS in dimensioning leaves an array "
                         "behind, and a follower's own DIM then reports "
                         "`Redimensioned array` instead of what it measures.")
    ap.add_argument("--gate", action="store_true",
                    help="fail on any divergence; without it every row is "
                         "reported as a straight differential")
    args = ap.parse_args()

    sel = [c for c in CASES if not args.only or args.only in c[0]]
    if not sel:
        print("APPARATUS FAILURE: no rows selected")
        return 1
    # ⚠️ APPARATUS GUARD -- see the docstring. A row that cannot be read is a
    # silent hole, so this is an error, not a warning, and it fires before a
    # single emulator is booted.
    toolong = [(lbl, ln) for lbl, _b, lines in sel for ln in lines
               if len(ln) >= ECHO_MAX]
    if toolong:
        print(f"APPARATUS FAILURE: these lines are >= the reference's boot LINLEN "
              f"({ECHO_MAX}), so their echo wraps and the readout cannot anchor "
              f"on it:")
        for lbl, ln in toolong:
            print(f"     {lbl}: {len(ln)} chars {ln!r}")
        return 1

    specs = [("direct", ["CLS"] + lines) for _, _, lines in sel]

    def read(i, raw):
        """A value row reads the bracket span; an error row reads the
        echo-anchored tail. Both anchor on the case's LAST line. A value row that
        ABORTED has no ']' and reads <none>, distinguishable from a wrong value."""
        if raw is None:
            return None
        last = sel[i][2][-1]
        if "[" in last:
            v = omsx_repl.result_span_after_echo(raw, last)
            return v if v is not None else "<none>"
        t = omsx_repl.screen_tail(raw, last)
        return t if t is not None else "<no echo>"

    def compare(i, rr, zz):
        a, b = read(i, rr), read(i, zz)
        return a is not None and b is not None and norm(a) == norm(b)

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=args.batch, reset=("NEW", "CLS"))

    npass = 0
    for i, (label, battery, lines) in enumerate(sel):
        rt, zt = read(i, ref_raws[i]), read(i, zb_raws[i])
        ok = verdicts[i]
        gated = label not in NEVER_GATED
        npass += 1 if (ok and gated) else 0
        mark = "----" if not gated else ("PASS" if ok else "FAIL")
        print(f"{mark:5} {battery:5} {label:14} {':'.join(lines)[:40]:40}")
        print(f"        ref: {rt!r}")
        if not ok or not gated:
            print(f"        zb : {zt!r}")
        if not gated:
            print(f"        why ungated: {NEVER_GATED[label]}")
        sys.stdout.flush()

    ntot = sum(1 for c in sel if c[0] not in NEVER_GATED)
    nrep = len(sel) - ntot
    print(f"\n{npass}/{ntot} gated rows agree with the reference"
          + (f"  ({nrep} reported, never gated)" if nrep else ""))

    # --- the ORACLE check, before any verdict is read as a finding -------------
    bad_repro = []
    for i, (label, _b, _l) in enumerate(sel):
        want = REPRO_EXPECT.get(label)
        if want is None:
            continue
        got = read(i, ref_raws[i])
        if want.casefold() not in norm(got or ""):
            bad_repro.append(f"{label}: want {want!r}, oracle said {got!r}")
    if bad_repro:
        print("⚠️ THE ORACLE DID NOT REPRODUCE ITS OWN RECORDED ANSWERS:")
        for b in bad_repro:
            print(f"     {b}")
        print("   No row in this run is readable — the reference or the harness "
              "moved since docs/clearpool-vg8020-characterization.md §3.")
        return 1

    bad_ctl = [sel[i][0] for i in range(len(sel))
               if sel[i][1] == "ctl" and not verdicts[i]]
    if bad_ctl:
        print(f"⚠️ CONTROL ROWS DIVERGED ({', '.join(bad_ctl)}) — no other row in "
              f"this run is readable as a D-ARR-B finding")
        return 1
    if args.gate and npass != ntot:
        print("SOME FAILED")
        return 1
    print("ALL PASS" if npass == ntot else "REPORTED (not gated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
