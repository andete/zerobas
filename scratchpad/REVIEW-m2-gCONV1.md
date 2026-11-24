# Goldfish review (test-writer role), 2026-11-24: CINT.md, CSNG.md, CDBL.md

Read: the three pages; probes/basic/spec/kconv.py, kconv_model.py, kconv_controls.py, cint_rules.py, csng_rules.py,
cdbl_rules.py, kmath.py; scratchpad/KCV_run1.out. NOT read: ramrec.py, tools/spec_rules.py, kwdoc_*.out,
t6enum_b2.out, and kmath_model.py (not linked by any page, so `K.assigned`, `K.no_usr`, `K.result_is` are inferred
from their names and use).

Run-file records DECODED by hand (27-byte records, ref and zb): FX 0-24 (all of CINT's), FX 31-34, 48, 49 (CSNG),
FX 56-59, 73, 74 (CDBL), FX 75-79; CS rows for args 0, -0, 1, .5 (all four fns); CD rows for .49999999999999,
1.2345649999999, 32767.99999999, -32768.99999999, 9.9999949999999D62, 9.999995D62, -9.999995D62, 9.9999999999999D62;
CI rows 1 and -32768. NOT decoded: every other CI/CS/CD record. The controls' FALSE counts were re-derived by
reasoning over the argument lists (39, 26, 12 for CINT; 2 for half-to-even), not by decoding each record.

## 1. Rules not pinned by any measured case

1. **CINT** -- R-CINT-TRUNC says "a single **or double** whose exponent byte is 0 or &H80 is 0", but no double with
   such an exponent and nonzero digits was measured (READ "0"/"-0" store all-zero bytes; the only POKEd arguments
   are singles). The same unmeasured input drives kconv_model's `m_csng` (`b[:4]`) and `m_cdbl` (unchanged). Pin:
   FX rows with `N#` POKEd to exponent 0 and &H80, digits left in, through all three functions.
2. **CSNG** -- R-CSNG-OVER names "9.999995D62, 9.9999999999999D62 **and their negatives**", but -9.9999999999999D62
   is not in the CD list (only -9.999995D62 is). Pin: add `-9.9999999999999D62` to CD_ARGS.
3. **CSNG** -- Details: "the same rounding that happens when a double is stored into a single variable
   (`A!=1.2345678#`)" -- no case stores into a single. Pin: `T!=N#` for every CD argument, its bytes compared with
   `CSNG(N#)`, including whether `T!=9.999995D62` is error 6 too.
4. **CINT** (also CSNG, CDBL) -- only a DOUBLE target `R` is measured; CINT's "stores into `A%` unchanged:
   `A%=CINT(3.7)`" rests on the old example run only, and a result stored to `T%`/`T!` is unmeasured for all three
   (kmath's FY measured this for its own functions). Pin: `T%=F(N)` and `T!=F(N)` rows read back through `USR`.
5. **CINT** -- Details and table quote `CINT(40000.5)` (Overflow), `PRINT CINT` and `CINT(2`; none is a KCV case
   (the probe has `R=CINT`, `R=CINT(5`, and no 40000.5), and 40000.5 appears in no cited file. Pin: add them as FX
   rows, or quote the measured forms.
6. **CINT / CSNG / CDBL** -- whether an argument's own error comes before the missing `)` is unmeasured
   (`F(1/0`, `F(1/0,2)`), and so is overflow against a missing `)` (`CINT(32768`, `CSNG(9.999995D62`). Pin: FX rows
   for those four forms per function.
7. **CSNG / CDBL** -- `CSNG(1.2345678#)`, `CSNG(1E38)`, `CDBL(1E38)`, `CDBL(1)/3` and `-CDBL(-32768)` in Details
   are not KCV cases; they rest on kwdoc/t6enum runs (not decoded here) that predate the probe.

## 2. Rules the cases could also explain with a different rule

1. **CDBL** -- the case labelled "a single expression widened", `CDBL(1!/3)` (KCV FX 78), recorded a DOUBLE
   argument: R and DAC are `40 33 33 33 33 33 33 33`, VALTYP 8, and the model itself treats it as `THIRD_D`. So it
   pins "a double unchanged", not widening, and Details' "CDBL of a single 1/3 is .333333" is pinned by no KCV case.
   Rival: "a single result is widened by its 6 digits" vs "a single-typed expression is really evaluated as a
   double". Separating case: `Z!=1/3:R=CDBL(Z!)` plus a `USR(1!/3)` row.
2. **CINT / CSNG / CDBL** -- R-*-FORMS asserts literal types (2.5 single, 7 integer, -32768 single, &H8000
   integer...), but no case of these pages separates them: CINT gives the same integer whether 2.5 is single or
   double, CSNG the same single, CDBL the same 8 bytes (a single 2.5 widened = double 2.5; -32768 integer or single
   widens to the same double). The clause is kmath's LIT rows (KMA_run1.out, not cited). Separating case: `LIT`
   apparatus rows (`Q=USR(<literal>)`, no function) in this probe.
3. **CSNG** -- R-CSNG-USE: VALTYP 8 for `CSNG(1/3)*3` is explained by "single times integer is a double" or by
   "CSNG's result enters arithmetic as a double". Separating cases: `USR(CSNG(1/3))` (alone), `CSNG(1/3)*3!`,
   `CSNG(1/3)*CSNG(3)`.
4. **CINT** -- R-CINT-ODD (and TRUNC's exponent-0 clause): both POKEd singles are +-0.1E-64, which truncation toward
   zero sends to integer 0 anyway, so "exponent byte 0 means zero" and "a tiny number truncated" coincide on every
   CINT case. No CINT case can separate them; the clause is unfalsifiable here (say so, or drop it).
5. **CINT / CSNG / CDBL** -- R-*-ORDER: "`)` is required before the TYPE check" vs "syntax is checked before ANY
   evaluation error". Both give 2 on `F("A"` and `F("A",2)`. Separating case: `F(1/0` (11 under the first, 2 under
   the second).

## 3. Citations that do not match the tables

1. **CSNG** -- R-CSNG-ASSIGN (a rule about R's stored bytes) is ✗ on zerobas at KCV CD CSNG 9.999995D62,
   -9.999995D62, 9.9999999999999D62, yet R's bytes and E1 are identical on both machines (E1 6, R = sentinel
   `c5 12 34 50 00 00 00 00`), and Differences says "`R=CSNG(x)` is the same on both". The ✗ comes from the USR
   record (zb VALTYP 8, DAC zero), which the sentence does not mention; a test written from the sentence would pass
   zerobas.
2. **CSNG / CDBL** -- "What we found": "the bare `CSNG` and the unclosed `CSNG(2` are measured on sibling functions
   only" (same in CDBL.md) is now false: KCV FX 31/32 and 56/57 measured `R=CSNG(5`, `R=CSNG`, `R=CDBL(5`, `R=CDBL`
   (error 2 on both).
3. **CSNG** -- the 2026-09-27 bullet still reads "{2, 13} on both machines", and "Tests that cover it" still says
   kwsweep's "error rows for {2, 13}", against the page's own {2, 6, 13} (the spec-probe bullet says it was refuted,
   but these two lines were left as they were).
4. **CDBL** -- the evidence list counts `CDBL(1!/3)` among the cases (and the probe labels it "a single expression
   widened"); the run records it as a double argument (see 2.1). The label misdescribes the case the rule reads.

## 4. Gaps in the open lists

1. **CINT** (and CSNG/CDBL via USR) -- a recorded, undeclared difference: for an INTEGER result the reference leaves
   the argument's first two bytes in DAC+0/+1, zerobas zeroes them (KCV CS CINT 1: ref DAC `41 10 00 01`, zb
   `00 00 00 01`; KCV FX 10: ref `41 25 00 02`, zb `00 00 00 02`; KCV CD CINT .49999999999999: ref `40 49 00 00`,
   zb `00 00 00 00`). A USR routine sees it. The pages say "0 unread" because only "the result's own bytes" count;
   neither Differences nor Open names these bytes as non-evidence.
2. **CSNG** -- D-CSNGOVERUSR shows zerobas raising the Overflow LATE (after the enclosing USR ran). Other enclosing
   contexts are neither measured nor listed open: `PRINT CSNG(9.999995D62)`, `CSNG(...)+0`, `ABS(CSNG(...))`,
   `T!=CSNG(...)`.
3. **CSNG / CDBL** -- the POKEd exponent-0 results (kept on the reference, zeroed on zerobas) are never USED: `+1`,
   comparisons, `SGN`, `STR$` of `CSNG(N!)` / `CDBL(N!)` (kmath FY did this for FIX/INT). Not in the open lists.
4. **All three** -- not listed open: results stored to `%` / `!` variables (1.4), the order of an argument's own
   error and overflow against a missing `)` (1.6), nesting depth (kmath FZ), and the mixed-type arithmetic type
   R-CSNG-USE defers to "the operators' region".
