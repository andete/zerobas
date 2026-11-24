# Goldfish review (test-writer role), 2026-11-23: docs/keywords/STR$.md, VAL.md, HEX$.md, OCT$.md, BIN$.md

**Run-file records decoded.** I decoded the `SN` section of `scratchpad/KNM_run1.out` (ref and zb) by hand: all the integer
records and most of the single and double records, including the argument bytes of `KNM SN S 1E-65` on both sides. I did
**not** decode the `RX`, `VL` or `FX` sections. For those, every count and case index below comes from the probe lists
(`knum.py`), the model (`knum_model.py`) and the controls (`knum_controls.py`), not from the records. I did not read
`kwdoc_*.out` or `kwram_full.out`.

## 1. Rules not pinned by any measured case

1. **VAL.md, R-VAL-RANGE (overflow upper bound by digit count).** The rule keeps the exponent byte as 64 + E mod 256. So
   64–191 ones overflow, 192 ones give a zero that keeps its digits, and 193 give 1.1111111111111E-63. Only 63, 64, 65,
   128, 129, 200 and 255 ones were measured. Measure 130, 191, 192 and 193 ones to pin where the overflow region ends.
2. **STR$.md, R-STR-ZERO (the "exponent byte 0, digit bytes not" clause) has no zerobas witness.** On zerobas, `READ`
   stored `1E-65` as `00 00 00 00`; on the reference it stored `00 10 00 00` (decoded from the SN records). So zerobas's
   ✓ on that case tested an ordinary zero. To pin the clause on both machines, POKE `00 10 00 00` into `VARPTR(N!)` before
   `STR$(N!)`.
3. **VAL.md, R-VAL-SUFFIX `%` boundary.** Only `"40000%"` and `"1.5%"` were measured. To pin both the range test and
   truncation for a negative number, measure `"32767%"`, `"32768%"`, `"-32768%"`, `"-32769%"`, `"32767.9%"` and
   `"-32768.5%"`. `"-1.5%"` is already in Open.
4. **VAL.md, R-VAL-SUFFIX `!` rounding at the half.** `"1234567!"` separates truncation from rounding, but not half up
   from half to even. `"1234565!"` and `"1234575!"` would separate them.
5. **VAL.md, R-VAL-SPACE / R-VAL-PREFIX: TAB or LF before `&`, and `&` + gap + end.** The model skips TAB/LF before `&`
   (so `CHR$(9)+"&HFF"` would be 255) and gives error 2 for `"& "`. Neither was measured. zerobas already stops at TAB
   elsewhere, so the TAB case is a likely further divergence.
6. **STR$.md, HEX$.md, OCT$.md, BIN$.md: "the whole set of errors is {2, 13} / {2, 6, 13}".** No case ran with string
   space full, so `Out of string space` (14) is neither excluded nor measured. Fill string space and call each function,
   or narrow the claim to "with string space available".
7. **BIN$.md: three Details claims have no KNM case.** "`BIN` without `$` is an ordinary array name",
   `"<"+BIN$(5)+">"` is `<101>`, and `BIN$(2)` is `"10"`. The RX fixed statements have no concatenation, no bare `BIN`
   array, and 2 and 5 are not in `RX_*`.

## 2. Rules the cases could also explain with a different rule

1. **VAL.md, R-VAL-END.** Its check is the same full-outcome model as the class rules (`outcome(c, m_val)`). It therefore
   fails on any value divergence, and its 10 zerobas failures are cases from R-VAL-SPACE, R-VAL-PREFIX and R-VAL-RANGE.
   Rival readings: "VAL read past the end" and "TAB is not skipped" give the same ✗. To separate them, check that the
   result differs from `m_val(a$ + next byte)` wherever those two values differ.
2. **VAL.md, R-VAL-NUMBER rounding.**
   - Rule A: round once at the 15th digit, ignoring later digits. Rule B: keep a 16th guard digit and round twice. A and
     B agree on every measured string. `"1234567890123449"` separates them: …234 under A, …235 under B.
   - Rule C: round the magnitude half up. Rule D: round half toward +∞. C and D agree because no negative string has more
     than 14 digits. `"-123456789012345"` separates them.
3. **VAL.md, R-VAL-RANGE wrap for an `E` exponent.** Rule A: the `E` exponent is added mod 256. Rule B: any exponent
   outside 1..127 is an overflow, with no wrap. They agree on every `E` case measured (|E| ≤ 99); only the digit-count
   cases (148, 175) separate them. Under A, `"1E-194"` is 1E+62 and `"1E-200"` is 1E+57; under B both are error 6. Open's
   `"1E300"` is the right family, but name these separating values.
4. **HEX$.md, OCT$.md, BIN$.md, R-*-RANGE lower edge.** Three rules agree on every measured case (-32768.5 accepted,
   -32769 an error):
   - "truncate, then error below -32768";
   - "error at n ≤ -32769";
   - "round half toward zero, then test".

   `-32768.9` separates them. It is already in Open, so this is only a reminder that the item decides between rival rules.
5. **VAL.md, R-VAL-OWNERR.** `VAL(1/0)` has a numeric argument, so error 11 shows that evaluation comes before the type
   check. It does not show that an error inside a string-typed argument propagates. Rival: "VAL reports its own 2/13 for
   any bad argument". `VAL(MID$(S$,0))` (error 5 if propagated) separates them.

## 3. Citations that do not match the tables

1. **HEX$.md, OCT$.md, BIN$.md, the Controls line.** It says "FALSE on 5 … (32768.5, 65534.5, 65535.5, 65535.9 in two
   types)". Only 65535.9 is measured in two types (`RX_SGL` has no 32768.5, 65534.5 or 65535.5). The 5 cases are S
   65535.9 plus D 32768.5, 65534.5, 65535.5 and 65535.9; "in two types" would make 8.
2. **VAL.md, the Status line and the sentence under the error table.** Status says "every error ✓"; the sentence says
   "the errors were measured per form on both machines and are the same". The rule table contradicts both:
   - zerobas raises error 2 on KNM VL 84 and 164–168, where the reference returns a value;
   - zerobas raises error 6 on KNM VL 148 and 175, where the reference returns a value.

   The same sentence also leaves out the error 6 of `"40000%"`.
3. **VAL.md, the Controls line ("a clean zero for an exponent of 0 on 5") and its label in `knum_controls.py` ("zerobas's
   rule after an E").** The 5 cases include KNM VL 178 (a point and 64 zeros, with no `E`) and KNM VL 107 (`"1D-65"`, on
   which the Differences section says zerobas agrees). So "after an E" does not describe zerobas's rule.
4. **VAL.md, the Details table row "64 to 129 digits | error 6".** It reads as a boundary at 129, but the page's own rule
   predicts overflow through 191 digits (see 1.1).
5. **STR$.md, the Status line "found zerobas agreeing in every case".** The recorded argument bytes of KNM SN S 1E-65
   differ between the machines (ref `00 10 00 00`, zb `00 00 00 00`). The outputs agree only because the argument is not
   one of the counted outputs. The same `READ` difference is cited on VAL.md.
6. **Values in Details and tables that are not KNM cases.**
   - STR$.md: `STR$(1E9)` (Details and table) and `STR$(1#/3)` (Details; the measured case is the `READ` value
     .33333333333333, not 1#/3).
   - BIN$.md: `BIN$(5)` and `BIN$(2)`.
   - OCT$.md: `OCT$(511)`.

   These rest on the 2026-10-09 example run, or on nothing: `BIN$(2)` is not in the BIN$ example either.
7. **VAL.md, the R-VAL-END zerobas column (10 failures).** The Differences section names no read-past difference and
   does not say that these 10 are the SPACE, PREFIX and RANGE cases. Four of the ten are hidden behind "(+4)", so the
   reader cannot check that.

## 4. Gaps in the Open lists

1. **STR$.md.** Open names non-canonical bytes "in a double argument" only. Add:
   - a single with exponent byte 0x80 (negative zero) or other non-canonical bytes;
   - the zerobas side of the measured exponent-0 single (1.2).
2. **VAL.md.** Missing from Open:
   - digit counts 130–199 (1.1);
   - the `%` boundary at ±32768 (1.3);
   - `!` rounding at the half (1.4);
   - 16-digit guard rounding and a negative 15-digit number (2.2);
   - TAB/LF before `&`, and `"& "` (1.5);
   - an error inside a string-typed argument (2.5).
3. **STR$.md, HEX$.md, OCT$.md, BIN$.md.** Out of string space (14), and string formula too complex (16) if reachable,
   are in neither Open nor the error set (1.6).
4. **BIN$.md.** The array-name and concatenation claims (1.7) are neither measured nor listed as open.
5. **HEX$.md, OCT$.md, BIN$.md.** Single-precision arguments in the 32768–65535 range other than 65535.9 (for example
   `32768.5!`), and a negative hex literal argument (`&HFFFF` = -1, measured only for STR$), are neither measured nor
   listed.
