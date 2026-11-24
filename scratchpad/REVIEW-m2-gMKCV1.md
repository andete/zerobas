# Goldfish review (test-writer role), 2026-11-24: MKI$.md, MKS$.md, MKD$.md, CVI.md, CVS.md, CVD.md

**Run-file records decoded (by hand, from the hex in `scratchpad/KMC_run1.out`, 37-byte records per `kmkcv.py`'s
layout):** DMK ref, all 105 records (e1 and S$ bytes; zb compared on the MKI$ truncation rows and the MKS$ rounding
rows); DFX ref, all 64 records (zb compared on e1 throughout); DCV ref, all 51 records (zb compared on 26 and 27);
FX ref/zb on e1 for records 0-6, 13, 18, 26, 31, 39-45, 60-63. **Not decoded record by record:** MK and CV (the
VG-8020 / NODISK groups), which I only spot-checked (e1 = 5, vt = 255 throughout, S$ length matching the source).
Evidence files read: `kmkcv.py`, `kmkcv_model.py`, `kmkcv_controls.py`, `mki_s_rules.py`, `cvs_rules.py` (the
other rules modules are the same template). I did not read `kconv_model.py`, `kmath_model.py`, `ramrec.py`,
`kmath.py`, or the `kwdoc_*.out` / `t6enum_b3.out` / `mkirange_*.out` files.

## 1. Rules not pinned by any measured case

1. **CVD.md, R-CVD-BYTES:** the parenthesis "(a zero exponent byte with digits, a non-BCD nibble: unchanged)" has
   no CVD case behind it. The only CV strings of 8 bytes or more are the double 1.2345678901234, the largest double
   and the 9-byte string, and all three are canonical. To pin it, measure `R=CVD(CHR$(0)+CHR$(&H10)+STRING$(6,0))`,
   `CHR$(&H80)+...`, and a double with a `&H1A` nibble. This is also the D-ZEROLET question for doubles, which no
   one has measured.
2. **MKI$.md, R-MKI-BYTES / Details / table:** a negative Overflow is never measured. Every Overflow case is
   positive (S:32768, S:1E10, D:1D20, D:9.999995D62, and FX `40000`), and `MKI$(-32769)` in the table comes from
   no KMC case. To pin it, add S:-32769, D:-32768.9999 (fits after truncation) and S:-1E10.
3. **CVS.md and CVD.md, R-CVS-EXPR / R-CVD-EXPR:** the sentence "CVx(MID$(S$,3)) starts at S$'s third byte" is
   measured only for CVI. The FX list has the MID$ case for CVI alone, and the rule selects 2 cases on each page:
   the 8-byte expression and the round trip. To pin it, add `S$="ABCDEFGHIJ":R=CVS(MID$(S$,3))` and the same for
   CVD.
4. **CVI.md and CVD.md, R-CVI-ASSIGN / R-CVD-ASSIGN:** the shared rule text claims how a single (and an exponent-0
   single) and a double are stored. On the CVI page every selected case is an integer, and on the CVD page none is
   a single. Those clauses are pinned only on other pages. Either cut the text to each page's own type, or the
   page asserts more than its cases show.
5. **CVI.md, CVS.md, CVD.md:** no rule covers an argument that fails to compute (the CV analogue of
   R-MKx-OWNERR). The FX list has no `1/0` case for CV, yet CVI.md Details asserts `CVI(0*(1/0)+1)` → 11 and
   `CVI(LEFT$("AB"))` → 2. The no-Disk-BASIC rule also says "whose argument computes" without any CV case of an
   argument that does not compute. To pin it, measure `R=CVI(CHR$(1/0))`-style cases on DFX and FX for all three
   functions.
6. **MKI$.md, MKS$.md, MKD$.md (and CV):** "The whole set of errors ... is {2, 6, 13}" (or {2, 13}, {2, 5, 13}) is
   a closure claim, and no case tries the remaining candidates. Two examples: error 14 (Out of string space) when
   string space is full before `S$=MKD$(x)`, and error 7 or 14 on string-heavy arguments. To pin it, add a
   `CLEAR <small>`-then-fill case.
7. **MKS$.md, R-MKS-BYTES:** the Overflow boundary is measured from one side only (9.999995D62 → 6). To pin the
   rounding threshold at the top exponent, add D:9.9999949999999D62, which should pack 7F 99 99 99.

## 2. Rules the measured cases could also explain with a different rule

1. **All six pages, every "nothing is assigned" / "S$ left as it was" clause** (R-MKI-BYTES "S$ left as it was";
   R-*-NODISK "nothing is assigned"; R-*-TYPE for `S$=CVx(...)`): S$'s pre-case sentinel is `""`. Rule A is "an
   error leaves S$ untouched". Rule B is "an error (or the disk hook's refusal) assigns the empty string". Both
   give SL = 0. To separate them, set `S$="XY"` before `S$=MKI$(32768)`, before `S$=MKS$("A")` without Disk BASIC,
   and before `S$=CVI("AB")`.
2. **CVI.md, R-CVI-EXPR / R-CVI-ASSIGN on KMC DFX 60 (`R=CVI(MKI$(-12345))`):** the round-trip value is exactly
   R's sentinel -12345, so R's 8 bytes (C5 12 34 50 00…) read the same whether or not the assignment happened.
   Rule A is "the result is stored in R". Rule B is "R is not assigned". Only the USR result (C7 CF) separates
   them, and R-CVI-ASSIGN reads R. To separate them on R as well, use any other value, for example
   `CVI(MKI$(-12346))`.
3. **MKS$.md, R-MKS-BYTES "a double rounded half up on its 7th digit":** D:1.2345650000001 is above the half, so
   round-half-up, round-half-even and "round to nearest, ties toward +∞" all give 41 12 34 57. Every other rounded
   case is clearly not a tie. To separate them, add D:1.234565 (exact tie, even 6th digit: half-up gives 1.23457,
   half-even gives 1.23456) and D:-1.234565 (away from zero gives -1.23457, toward +∞ gives -1.23456).
4. **MKD$.md, R-MKD-BYTES "converted as CDBL":** the control only separates integers (7 cases). A single
   "widened" by appending four zero bytes and a single "converted" by CDBL give identical bytes in BCD on every
   case. The rule cannot be told apart from "a non-integer is padded", so it is not wrong, but the page's
   "converted, not padded" claim in *What we found* holds only for integers.
5. **CVI.md / CVS.md / CVD.md, R-CVx-NODISK on short strings:** for CV strings shorter than the width, error 5 is
   both "no disk ROM" and "too short". Only the long-string rows (and FX 39/46/53) separate the rule from "length
   checked in main, then 5 from the hook". This is noted for completeness: the separating rows exist, but only the
   long strings count as evidence.

## 3. Citations that do not match the tables

1. **MKI$.md, Details:** "On the VG-8020 … only a syntax fault such as `MKI$(1,1)` is reported first, as error 2"
   is contradicted by R-MKI-OWNERR. Without Disk BASIC, `S$=MKI$(1/0)` is error 11 on the VG-8020 (KMC FX 1, e1 =
   0x0B), so the argument's own error is reported first too.
2. **CVS.md, *What we found* (spec-probe bullet):** "zerobas agrees on every value; its differences are error
   codes" contradicts the page's own D-ZEROLET difference (R-CVS-ASSIGN ✗ on KMC DCV 26, 27: R's bytes differ).
   It also contradicts the Summary's "and in one stored zero".
3. **CVS.md, Differences (D-ZEROLET):** the text says "a single whose exponent byte is 0", but it cites KMC DCV 27.
   That case's exponent byte is &H80 (80 10 00 00). The reference stores R = 80 10 00 00 00 00 00 00 and zerobas
   stores eight zero bytes. The sign-bit case should be named.
4. **MKS$.md, MKD$.md, CVI.md, CVS.md, CVD.md, Details "A diskless zerobas does the same for the calls measured
   there (…)":** this is stale. The KMC run measured 43 / 22 / 21 no-Disk-BASIC cases per keyword, and zerobas does
   NOT do the same on one of them (FX 13 / 26 / 39 / 46 / 53, error 13 against 5). Only MKI$.md's Details mentions
   that exception.
5. **MKI$.md, table row "`MKI$(32768)`, `MKI$(-32769)` → error 6" and Details:** the -32769 half has no KMC case
   (see §1 item 2). It rests on an uncited older run.

## 4. Gaps in the open lists

1. **All six pages:** the open lists do not record that S$'s error sentinel is `""` and so cannot detect an
   assignment of the empty string (§2 item 1).
2. **CVD.md:** missing a non-canonical double (exponent byte 0 or &H80 with digits, a non-BCD nibble) and the
   D-ZEROLET question for `R=CVD(...)` (§1 item 1).
3. **MKI$.md:** missing negative Overflow (§1 item 2).
4. **MKS$.md:** missing the exact tie of rounding on the 7th digit (positive and negative) and the near side of the
   Overflow boundary (§1 item 7, §2 item 3).
5. **CVI.md, CVS.md, CVD.md:** missing the argument's own error, with and without Disk BASIC, and `MID$` for CVS
   and CVD (§1 items 3, 5).
6. **All six pages:** the error-set closure is not listed as open (Out of string space, §1 item 6). Nor is
   assignment of a CV result to an integer or single variable (`R%=CVS(...)`, `A!=CVD(...)`: conversion and
   Overflow on the store).
