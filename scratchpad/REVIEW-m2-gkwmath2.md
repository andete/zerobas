# Goldfish review (test-writer role), 2026-11-23: docs/keywords/EXP.md, LOG.md, SIN.md, COS.md, TAN.md, ATN.md

**Run-file records decoded:** by hand, from `scratchpad/KTR_run1.out` (27-byte records, layout from kmath.py's
`decode`), ref and zb for each:
- TI: ID/EXP/LOG/SIN/COS/TAN/ATN of 0, EXP of -1000 and -32768.
- TS1: EXP -147.4.
- TS2: SIN/COS/TAN of 1E13, 5E13 and 7E13; COS/TAN of 4.71239; EXP of -65536 and -999999.
- FX: 16, 17, 112, 113, 114, 130, 133, 136, 137.

About 37 records in all. **Not decoded:** the remaining ~1,800 records. Every bound, worst-case figure and per-rule
case count in the tables is taken on trust from the generated text. The case predictions below (1.1E13, 1.3E13,
7.5, ...) are hand arithmetic with C = 0.15915494309190, not run.

## 1. Rules not pinned by any measured case

1. **All six pages: what a non-canonical zero result does next is never measured.** That means the 2-pi-digit zero
   (00 62 83 18 53 07 17 96), EXP's exponent-0 TINY results (decoded TS1 EXP -147.4: 00 96 60 36 12 55 89 73), and
   zerobas's leftover-digit zeros. The pages call these differences "invisible to PRINT", but no case PRINTs one,
   compares one with 0, or does arithmetic with one. To pin it, run `PRINT SIN(0)`, `IF SIN(0)=0`, `PRINT SIN(0)+1`,
   `PRINT EXP(-147.4)*1E10` and `IF ATN(-0)=0` on both machines.
2. **SIN / COS / TAN: the window where p has 13 integer digits (x about 6.3E12 to 6.3E13) has only two cases,
   1E13 and 5E13.** p has a fraction of .0 in both. Under the model, SIN(1.5E13) is the 2-pi zero (f = .5), and
   COS(1.3E13) is that zero too, with TAN(1.3E13) giving Overflow (p = 2069014260194.7, 1/4 - p rounds to a
   half turn). None of this is measured. To pin it, measure SIN, COS and TAN of 1.1E13, 1.3E13 and 1.5E13.
3. **EXP.md R-EXP-TINY: the entry edge (e^x = 1E-64, x = -147.3634) is bracketed only by -147.3 and -147.4.** The
   other band edges are bracketed to within 0.002. To pin it, measure -147.36 and -147.365 as doubles.
4. **SIN.md / TAN.md R-*-ZERO: "p below 1E-64 is 0" is witnessed only at x = ±1E-64.** At 1E-63 the result is
   already "near". The model puts the switch at about x = 6.28E-64. To pin it, measure SIN and TAN of 5E-64 and
   7E-64.
5. **All six pages: the result is only ever assigned to a double (R) or seen through USR.** Nothing pins what
   `A!=` or `A%=` stores, or what an expression around the call does, with an exponent-0 or 2-pi-digit result. To
   pin it, measure `A!=EXP(-147.4)`, `A%=SIN(0)` and `A!=TAN(1E13)`, and read the bytes.
6. **EXP.md: the HUGE threshold (somewhere in -65536 > x >= -99999) and the overflow edge (145.06286 to
   145.063) are unpinned.** Both are already in the open list.

## 2. Rules the cases could also explain with a different rule

1. **SIN.md R-SIN-ZERO's sentence and its check disagree.** The sentence says the result is zero "from 1E13 up,
   where p has no fraction digit left". The check says p's fraction is 0 or .5, which is stronger. At 1E13, p is
   1591549430919.0, which still has a fraction digit; it is 0 only because C ends in 0. The two rules separate on
   SIN(1.1E13): the model gives f = .9, so about -.5878; the sentence gives the zero.
2. **COS.md R-COS-ZERO and TAN.md R-TAN-POLE: "from 7E13 up" against the model, and half-up against half-even
   for r14(1/4 - p).** When p has 13 integer digits, every 1/4 - p is a rounding tie. Both measured ties (1E13, 5E13)
   have an odd digit before the 5, so half-up and half-even agree on them. They separate on COS(1.1E13): g = -.7
   with half-up, -.6 with half-even. On TAN(1.3E13), half-up gives Overflow, while both half-even and the sentence's
   "from 7E13" give a number.
3. **SIN / COS / TAN: rounding p = x*C half-up against half-even.** The measured tie at 10.5 (p =
   1.67112690246495) has an odd digit before the 5, so it does not separate them. SIN(7.5) does: p =
   1.19366207318925 rounds to ...893 or ...892, which is about 22 units apart in the result, far outside the 2.5
   bound. This comes from hand arithmetic; I did not check all 255 arguments for a tie with an even predecessor.
4. **EXP.md R-EXP-POS / R-EXP-NEG: a bound fits the data, but so might a structural rule.** The bounds are 500 and
   40,000 units against e^x. The alternative is a 14-digit reduction, like SIN's (for example p = r14(x * log10
   e)), with a small bound against the reduced target. The error growing with x, and the irregular 5 to 39,525
   units below -1, fit a reduction artefact. As written, an implementation 39,000 units off passes R-EXP-NEG. To
   separate the two, fit a reduced-target model and run it as a control.
5. **EXP.md R-EXP-HUGE: the rule "x <= -99999" also fits "x < -65536", or a 17-bit wrap of the argument.** Either
   would separate on -70000 or -80000. The open list has this.
6. **ATN.md R-ATN-ZERO: "keeps the argument's digit bytes" also fits "a non-canonical zero gives the constant
   00 10 00 00 ...".** The only non-zero digit pattern measured is 10 00 00. They separate on a single whose
   exponent byte is POKEd to 0 and whose digit bytes are 12 34 56.

## 3. Citations that do not match the tables

1. **TAN.md Details is contradicted by its own table and the run file.** It says "zerobas raises 2 and 13 in the
   same cases, but not yet 6". R-TAN-POLE has zerobas ✓ on all 17 cases, and in the decoded TS2 TAN 7E13 both
   machines give e1 = e2 = 06. The Status line on the same page also says "Overflow on both machines".
2. **SIN.md, COS.md, TAN.md Summary and Status overstate the agreement.** They say "only the last digit or two of
   a result can differ", and SIN.md adds that zerobas "reduces the angle exactly as the reference does". The tables
   disagree:
   - R-SIN-ZERO fails 36/36, R-COS-ZERO 17/17 and R-TAN-ZERO 19/19.
   - D-TRIGHALF moves the LEADING digits. In the decoded TAN(4.71239!), the reference gives -980761.90719410 and
     zerobas -980761.84675660, which differ from the 8th digit.
   - Decoded SIN(7E13): zerobas gives 00 11 14 08 46 01 64 33, which is p's digits, not 2 pi's.
3. **TAN.md "What we found" is falsified by R-TAN-OWN.** It says "`TAN(x)` is `SIN(x)/COS(x)` to the last digit".
   R-TAN-OWN says the quotient is "not always rounded correctly" (2.8 units), and the "correctly rounded" control
   is FALSE on 84 of 199.
4. **SIN.md R-SIN-ZERO's explanation "where p has no fraction digit left" is false at 1E13 and 5E13.** p is
   1591549430919.0 and 7957747154595.0. See item 2.1.
5. **SIN.md and LOG.md break the "Bounds, not digits" paragraph** ("B is the worst error MEASURED, rounded up ...
   a control shows that a tighter bound is false").
   - SIN: the worst is 1.9 and B is 2.5, shared with COS. The only tighter control is 1 unit, so "within 2" is not
     shown false.
   - LOG: the worst is 8.3 and B is 10, and the control is at 5.
6. **The ATN.md control "80 10 00 00 gives a negative zero C0 00 ..." claims "FALSE on 2 of the 2 cases (e.g. KTR
   FX 136)", but FX 136 is the single with exponent byte 0 (00 10 00 00).** The rival says nothing about that case.
   Only FX 137 separates it: decoded, the reference gives 00 10 00.. and zerobas C0 00...
7. **EXP.md misdescribes zerobas's zeros in two places.**
   - The controls "0 in the band" and "0 for the huge negatives -- zerobas's rule" test for 8 zero bytes. Decoded,
     zerobas gives TS2 EXP -999999 = 00 99 99 99 00 00 00 00 and TS2 EXP -65536 = 00 65 53 60 ..., the
     argument's own digits under exponent 0.
   - The Differences bullet on zero bytes names only the FLUSH region and the four ASSIGN/FORMS cases. It does not
     mention the BAND/HUGE cases, where zerobas's "0" also carries digit bytes.
   - The Status line says "Two recorded differences", but Differences has three bullets.
8. **EXP.md, LOG.md, COS.md and SIN.md each quote a figure for zerobas's own accuracy that no rule or control
   checks**: "within 1 unit ... on every argument measured", "within 1.7", "within 1.3 units ... away from the
   folds", "up to 6.1 units".

## 4. Gaps in the open lists

1. **All six pages: the open lists do not say that PRINT, comparison or arithmetic on non-canonical zero results
   is unmeasured** (item 1.1). The pages assert "invisible to PRINT" without a case behind it.
2. **SIN.md, COS.md, TAN.md: the "different rounding" item does not name the 13-integer-digit window or the tie
   cases where it would show**: 6.3E12 to 6.3E13 for 1/4 - p, and ties in p such as 7.5 (items 2.2 and 2.3). It
   also does not mention that the TAN Overflow set may extend below 7E13.
3. **EXP.md: the R-EXP-TINY entry edge (-147.3 / -147.4) is not listed.** Only the overflow edge and the
   huge-negative threshold are.
4. **SIN.md and TAN.md: the tiny-argument threshold where p flushes to 0 (between 1E-64 and 1E-63) is not
   listed.**
5. **All six pages: assignment to single or integer variables, and use inside a larger expression, are not
   listed as unmeasured** (item 1.5).
