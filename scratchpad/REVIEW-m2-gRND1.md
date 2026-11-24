# Goldfish review (test-writer role), 2026-11-24: docs/keywords/RND.md

**Run-file records decoded** (by hand from the hex in `scratchpad/KRN_run1.out`, 34-byte records split by `fold`; arithmetic checked with `bc`; no repo code run): FX 0-60, ref and zb; SQ1 0-67, ref and zb; SQ2 0-29 and 117-184, ref and zb, plus the reseed rows 33, 37, ... 113 (every 4th), ref only; BOOT 0-16, RUNR/GOTO/GOTO2 0-4, ref and zb (E, R, VT, RNDX only). Also read `kwdoc_rnd.out` (the Example) in full.
**Not decoded:** SQ3 (all 210 records); SQ2 rows 30-116 except the reseed rows, and the zb side of those reseed rows; the DAC bytes of BOOT and RUNR/GOTO/GOTO2. Not read: `rndx_after.out`, `t6enum_b5.out` (cited only in the history section). The control counts in the page's Controls paragraph were not re-run; the ones I could re-derive from decoded rows are noted below.

## 1. Rules not pinned by any measured case

1. **RND.md, R-RND-NESTED, "(normalised, R-RND-VALUE)":** neither reseed-from-a-result case has a leading zero. FX 41's inner RND(1) is .34523184081661 (state 28699470846360 -> 34523184081661 -> reseed -> 75265701742880, checked with bc). FX 42's inner RND(0) is .75265701742880. So "the reseed takes the normalised double's digits" and "the reseed takes the raw state / RNDX digits" give the same result on every case. To pin it, measure `RND(-RND(0))` right after `RND(-1)` (state 04389820420821): normalised m = 43898204208210, raw m = 04389820420821.
2. **RND.md, Details + R-RND-START, "whenever a program line is typed or edited":** every line-entry case adds a NEW line number (BOOT `10 REM` into an empty program, `20 REM` after NEW, GOTO2 `99 REM` appended). Nothing measures replacing an existing line, deleting one by typing its number alone, or re-typing a line with the same text. To pin it, measure each of the three after a reseed (as GOTO2 does).
3. **RND.md, R-RND-START, RUN:** the only case that separates the RUN reset is RUNR 0. In BOOT, `20 REM` is typed just before `RUN`, so the line entry has already reset the state. `RUN <line>` is not measured; to pin it, run it after a reseed with no line typed in between.
4. **RND.md, R-RND-VALUE's example "S = 1 is 1E-14, 33 10 00 ...":** the only S = 1 case is SQ2 125, a `Q=USR(RND(N#))` step. R-RND-VALUE's own selection excludes USR rows, so this example is read only by R-RND-TYPE. The same holds for 10^13 (SQ2 141) and 12345 (SQ2 133). An R row with S = 1 would pin it under the rule that states it.

## 2. Rules the measured cases could also explain with a different rule

1. **RND.md, R-RND-CELL ("The state is ... held in RNDX"):** every case also fits "the state lives elsewhere, and RNDX is a write-only copy updated on every call". The probe only ever reads RNDX. The separating case is listed as open (POKE RNDX, then `RND(1)` / `RND(0)`), but the rule asserts the stronger reading anyway.
2. **RND.md, R-RND-REPEAT and Details, "RND(0) ... returns the last number again" / "repeats the last number":** read literally, "the last number RND returned" is false on BOOT 1. There, RND(0) at power-on returns .40649651372358, a number never returned before; the same happens after CLEAR, NEW and line entry. The check implements "returns S / 10^14 of the current state". The two rules separate exactly on BOOT 1 (measured), so the sentence should say "the current state's number".
3. **RND.md, R-RND-SEED, integer "decimal digits left-aligned":** "the integer is converted to a single (or double) first, and its digits are taken" gives the same m for every 16-bit integer (at most 5 digits, padded with zeros). No case can separate the two; the rule could say so instead of presenting left-alignment as a distinct mechanism. (Low priority: the two never differ.)

## 3. Citations that do not match the tables

1. **RND.md, Status block (2026-10-09):** it lists "entering a program line does not restart the sequence here" among three differences. Now R-RND-START is ✓ on zerobas, GOTO2 0 and BOOT 6 read S0 on zb, and "Differences" lists only two items. The same block's "every error ✓" contradicts R-RND-CHECKS ✗ (KRN FX 13-14: zb 0d, ref 02).
2. **RND.md, Differences, D-RNDZERO "KRN SQ2 121, FX 54-59":** FX 55 is not a difference. Both machines give R = 40 14 38 98 20 42 08 21, RNDX 00 14389820420821. The failing set in the tables is FX 54, 56, 57, 58, 59.
3. **RND.md, R-RND-REPEAT lists "-0!, -0#" (and the Evidence lists them as zero arguments) as cases distinct from 0!, 0#:** their recorded argument bytes are all zero (SQ1 35, 37, 40, 42: ARG 00 ...), and `check_args` requires that. The literal `-0` (FX 20) is the integer 0. No measured case has a sign-bit zero (80 00 ...), so naming "-0" implies coverage the table does not have.
4. **RND.md, R-RND-NEXT's text cites "a nested RND(1)":** its selection (`plain`, one call per statement) excludes the nested rows. FX 39 is read only by R-RND-NESTED.
5. **RND.md, R-RND-OTHER's text cites "an error":** its selection excludes `err` rows, which are read by R-RND-ERR / -CHECKS / -STRTARGET.
6. **RND.md, Evidence FX, "every error form (none may move the state)":** FX 3 (`R$=RND(1)`) is an error form that does move the state (RNDX 40649651372358 -> 59521943994623), as R-RND-STRTARGET says.
7. **krnd.py (cited probe source), lines 119-120:** it says each chosen pre-image is set so that "the step after the reseed lands on T exactly", and lists 12300000000000. The decoded rows show that 12300000000000 is reached one `RND(1)` later (SQ2 149 -> 02194897914141, SQ2 150 -> 12300000000000), and 01000000000000 two later (SQ2 159). The page's own wording is correct; the probe docstring is not.
8. **Controls I re-derived from decoded rows, all consistent:** A's last digit (360 of 362: the 2 true are SQ2 122 and FX 55, both stepping from state 0); RNDX holding the result (549 of 556: the 7 state-0 rows); result in the argument's type (20 of 94); program line / RUN / CLEAR / NEW (2 / 1 / 4 / 1 of 12); sign bit taken as zero (2 of 4). No mismatch found here.

## 4. Gaps in the open lists

1. **RND.md:** replacing an existing line, deleting a line (number alone) and re-typing an identical line are missing (see 1.2). The open list names DELETE / RENUM but not plain line edits, which the Details text asserts.
2. **RND.md:** a reseed from a returned number with leading zeros (the normalisation in R-RND-NESTED, 1.1) is not in the open list.
3. **RND.md:** `MAXFILES=` (which reinitialises the work area the way CLEAR does) and `RUN <line>` are not in the open list's reset-path enumeration.
4. **RND.md:** a sign-bit zero (`80 00 00 00`, `80 00 ...`) is listed as "`&H80` with zero digit bytes", but it is not tied to R-RND-REPEAT's "-0!, -0#" claim (3.3). Whether a negative zero repeats or reseeds from m = 0 (next state = C) is the open question that rule's wording hides.
