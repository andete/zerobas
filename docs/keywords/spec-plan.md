<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The keyword pages as a specification — the plan

← [Keyword pages](README.md) · [the index](spec-index.md) · [the method](../spec-method.md)

Developer documentation (D-KWSPEC, Joost 2026-11-23). The BIOS calls each have a page that is both the user
documentation and the specification: measured on the reference, its rules executable, reviewed until they stop
moving ([docs/spec-method.md](../spec-method.md), [docs/bios/index.md](../bios/index.md)). This plan applies the
same method to the BASIC keywords. BASIC is meant to graduate into C-BIOS one day; these pages are what such a port
is checked against, so "the page says it" has to mean "the reference was measured doing it".

The method itself is not restated here. This page says only what is DIFFERENT for a keyword: the regions, the
references, the harnesses, what a case and a rule are, and how a spec page differs from today's user page.

## 1. What a keyword spec is

- **A case** is BASIC typed on the machine: an expression or a statement inside a fixed program frame, with its
  inputs chosen by the probe. It is run on the reference and on zerobas, never compared with a value written by
  hand.
- **Its outputs** are what the keyword can be seen to do: the error it raises (ERR, and ERL where the line
  matters), the value it returns, the variables it should and should not change, the screen it leaves, the
  work-area cells, VRAM, the PSG. Each case records ALL of the outputs its region declares (spec-method §3a,
  "coverage is field-level").
- **A rule** is a sentence and a check over the cases, exactly as for the BIOS: a rules module
  `probes/basic/spec/<slug>_rules.py` (`<slug>`: the keyword in lower case, `$` as `_s`), checked by the unchanged
  [tools/spec_rules.py](../../tools/spec_rules.py). Its tables are generated onto the page between
  `<!-- RULES BEGIN -->` and `<!-- RULES END -->`; `make spec-rules-check` (in STATIC) runs these modules as well as
  the BIOS ones.
- **Clean room, unchanged:** the VG-8020's BASIC is a black box. Lines are typed; screen, RAM, VRAM, registers and
  ports are read. No reference ROM byte is read, no hook target followed, nothing single-stepped into ROM.

### The keyword-specific rules of a setup (in addition to spec-method §3a)

- **The readout must not use the keyword under test, nor its family.** The pilot reads a string result through
  `VARPTR` and `PEEK` (its descriptor, then its bytes), never through `LEN` / `MID$` / `ASC`.
- **Every case starts with its output holding a sentinel** (the pilot: `R$=CHR$(250)`), so an error, which assigns
  nothing, cannot read as a result; "nothing is assigned on an error" then becomes a rule with a check.
- **Inputs are distinct per position:** a source string whose byte at position p is `CHR$(p)` separates "the first
  n", "the last n", "n from p" and "n from p - 1" in every case.
- **Numbers at the values where rival rules disagree:** truncation vs rounding (`.9`, `1.5`, `255.9`), truncation vs
  `INT` (`-.9`), the overflow test before vs after truncation (`-32768.5`, `32767.9`), both ends of each range.
- **A capture is ended by the program**, not by a timer: a done flag the harness waits for (omsx_repl's
  sentinel capture) and an end byte after the last record. The decoder refuses a capture without both.
- **Every variable read through `VARPTR` is assigned first.** The third unit's first run read `S$` in a group that
  never assigned it: `VARPTR` returned bytes that were not a string descriptor, and the digest PEEKed 197 bytes at a
  page-0 address -- reference ROM -- on both machines. That run was discarded, not read, and the frame now assigns
  `S$=""` before its loop; a decoder cannot tell such a "length" from a real one, so the frame must prevent it.
- **The probe's own BASIC is apparatus.** The pilot found that a `FOR` whose start is past its limit runs its body
  once, on both machines (§6): a probe frame that relied on an empty loop would have built the wrong input.

## 2. The regions, in the loop's order

The keyword pages are already grouped by [docs/keywords/README.md](README.md); the regions follow those groups. The
order puts the cheapest, most self-contained regions first: pure functions, whose whole behaviour is a value and an
error code, before statements with machine state, and the devices last. Disk comes last, as it did for the BIOS
(Joost, 2026-11-19: the disk calls after every other call).

| # | region | keywords | reference | harness (§3) |
|---|---|---|---|---|
| 1 | **strings** | LEN LEFT$ RIGHT$ MID$ ASC CHR$ INSTR SPACE$ STRING$ STR$ VAL HEX$ OCT$ BIN$ | VG-8020 | RAM record |
| 2 | maths | ABS SGN INT FIX SQR EXP LOG SIN COS TAN ATN RND | VG-8020 | RAM record (the value's 8 BCD bytes) |
| 3 | conversion | CINT CSNG CDBL MKI$ MKS$ MKD$ CVI CVS CVD | VG-8020 | RAM record |
| 4 | operators | AND OR XOR EQV IMP NOT MOD LET SWAP | VG-8020 | RAM record |
| 5 | flow | GOTO GOSUB RETURN IF FOR NEXT END STOP CONT RUN | VG-8020 | RAM record + screen |
| 6 | errors | ERR ERL ERROR RESUME TRON TROFF REM DEFINT DEFSNG DEFDBL DEFSTR | VG-8020 | RAM record + screen |
| 7 | program | NEW LIST LLIST DELETE RENUM AUTO DATA READ RESTORE DIM ERASE CLEAR | VG-8020 | screen + program text |
| 8 | memory | PEEK POKE VARPTR FRE USR FN BASE INP OUT WAIT TIME | VG-8020 | RAM record + ports |
| 9 | composite | ON DEF GET PUT | per statement | per statement |
| 10 | text | PRINT LPRINT CLS LOCATE CSRLIN POS LPOS WIDTH SCREEN COLOR KEY | VG-8020 | screen + work area |
| 11 | graphics | PSET PRESET LINE CIRCLE PAINT DRAW POINT SPRITE VDP VPEEK VPOKE | VG-8020 | VRAM + VDP registers |
| 12 | sound-input | BEEP SOUND PLAY INKEY$ INPUT STICK STRIG PAD PDL MOTOR | VG-8020 | PSG registers, held keys, the rig |
| 13 | files | OPEN CLOSE EOF LOAD SAVE MERGE BLOAD BSAVE CLOAD CSAVE | VG-8020 (`CAS:`), CF-3300 (disk) | tape image / disk image + screen |
| 14 | disk | FILES LFILES KILL NAME COPY DSKF DSKI$ DSKO$ FIELD LSET RSET LOC LOF IPL CMD SET | CF-3300 | disk image + screen |

- **Composite words** (`ON`, `DEF`, `GET`, `PUT`) come after the regions their statements belong to: `ON ERROR` is
  the errors region's, `ON KEY GOSUB` the text region's, `DEF FN` the memory region's, `PUT SPRITE` graphics'.
- **Within a region**, the loop takes a family that shares a contract together (the pilot: `LEFT$` / `RIGHT$` /
  `MID$`), then the lowest 🎚️ tier of the open TODO items first, as for the BIOS.
- **The reference.** The Philips VG-8020 for BASIC; the National CF-3300 for Disk BASIC (the pages' `<!-- example:
  reference=... -->` line already says which). When the two differ on a non-disk keyword, the page records both; a
  purely presentational split ships the VG-8020's value (Joost, 2026-09-04).
- **Later generations** (spec-method §2.6): an MSX2's BASIC is a different ROM with more statements; each rule is
  re-measured there before a page may claim it. Until then the page's "On later generations" section is one `[A]`.
- **Question for Joost:** the BIOS loop's 2026-11-19 ruling kept BASIC's cassette STATEMENTS out of the fix pass.
  Are `CLOAD` / `CSAVE` / `MOTOR` and the `CAS:` forms of region 13 in D-KWSPEC's spec work, with their differences
  filed and not fixed?

## 3. The harnesses

All of them type BASIC through [probes/lib/omsx_repl.py](../../probes/lib/omsx_repl.py) (`run_cases`: KEYBUF
injection, delivery verified, one boot per probe group), so a case is exactly what a person could type.

| harness | reads | how | used by |
|---|---|---|---|
| **RAM record** | per case: ERR, the result, the source / bystander variables | the typed program evaluates every case of a matrix in a loop and POKEs a fixed-size record per case above `CLEAR`'s limit; values come from `VARPTR` + `PEEK` (a string's descriptor and bytes; a number's own 2 / 4 / 8 bytes); `capture=("mem_abs", ...)`, `sentinel_capture` on the done flag | strings, maths, conversion, operators, memory; flow and errors for their values |
| **screen** | the text screen's rows | the SCREEN 0 name table (omsx_repl's default capture), as [kwdoc_examples.py](../../scratchpad/kwdoc_examples.py) reads an example | what a keyword PRINTS: LIST, PRINT, error messages, `INPUT`'s prompt |
| **work area** | cursor and screen cells, the program text | `mem_abs` of the published cells (CSRX / CSRY, TXTTAB ...) | text, program |
| **VRAM / VDP** | the pattern, colour and sprite tables; R0-R7 | `vram_segs`, `vdpregs` | graphics |
| **PSG / devices** | PSG registers, held keys, the rig | `probes/lib/psgtrace.py`; `holds`, `@BREAK`; `rigfw.py` | sound-input |
| **media** | the tape and disk images after the statement | `cas_encode` / `cas_decode`; a private copy of `disk/test720.dsk` | files, disk |

The pilot's probe, [probes/basic/spec/kslice.py](../../probes/basic/spec/kslice.py), is the RAM-record harness's
first instance. It boots the VG-8020 and zerobas's diskless machine (`C-BIOS_MSX1_EU_REPACK_NODISK`); a disk
region's probe boots the CF-3300 and `C-BIOS_MSX1_EU_REPACK_DISK` instead, as the example check does.

## 4. The page: today's user page, plus the specification

Today's keyword page ([about.md](about.md)) has: status, summary, syntax, details, example, differences, "what we
found, and how", where it lives, tests. A spec page KEEPS the user content and ADDS the contract sections of
spec-method §2:

| section | user page | spec page |
|---|---|---|
| title | `` `NAME` — what it does`` | the same |
| **`> **Spec:** <state>`** | — | NEW, above the status line: `DRAFT n` / `REVIEWED n` / `FINAL`, the date, the reference and the probe. The index reads it |
| status line (the tier ladder) | yes | kept: it says which GATES pass; the Spec line says how far the page is measured |
| summary, syntax | yes | kept, plain prose |
| details (with the "you write / you get" table) | yes | kept as the READER's version of the rules. Each statement in it must be backed by a rule below or listed under Open; a detail no case backs is a finding |
| example | yes, run by `kwdoc_examples.py` | kept, still run |
| **the specification** | — | NEW: the reference, the evidence tags (`[KS ...]` for the pilot's cases), the generated rule tables |
| differences from the reference | yes | kept; each difference names the failing rule and its TODO item, which the index reads |
| **on later generations** | — | NEW (spec-method §2.6) |
| **open (not measured)** | — | NEW: every `[A]` |
| what we found, and how | yes | **question for Joost** (below) |
| where it lives, related, tests | yes | kept |

**"What we found, and how" is history**, and spec-method §2 rules a spec page describes behaviour, not history
(Joost, 2026-11-18). The proposal: keep the section while the page is a DRAFT (it names the past failures a reviewer
should probe), and delete it when the page goes FINAL; the history stays in git, `docs/TODO-done.md` and the
`docs/spec-basic-*.md` documents the section links to. [about.md](about.md) lists the section as required; it
changes with this ruling.

## 5. The index

[docs/keywords/spec-index.md](spec-index.md) is generated like [docs/bios/index.md](../bios/index.md):
[tools/kw_spec_index.py](../../tools/kw_spec_index.py) (`make kw-spec-index`; `make kw-spec-index-check` is in
STATIC; the pre-commit hook regenerates it when a keyword page is staged). It lists every keyword page in loop order
with its region, the region's harness, the reference, the page's spec state, its open count and its differences.
Every page must have a region and every region entry a page, so neither can be lost quietly. A page without a Spec
line is a "user page", not an error: the loop converts the pages region by region. The README stays the reader's
index; the spec index is the loop's queue.

## 6. The pilot (2026-11-23): the slice functions

The first unit is the strings region's slice family, `LEFT$`, `RIGHT$` and `MID$` (the function form; the statement
is open on MID$'s page). One probe, three rules modules, three pages at DRAFT 1:

- [probes/basic/spec/kslice.py](../../probes/basic/spec/kslice.py): 1,224 cases on each machine. LEFT$ / RIGHT$:
  5 source lengths x 28 counts; MID$: 4 lengths x 15 positions x 15 counts (one of them "no count"); 44 fixed
  expressions (types, missing and extra arguments, spaces, nesting, the order of the checks). Run file
  [scratchpad/KSL_run1.out](../../scratchpad/KSL_run1.out).
- [kslice_model.py](../../probes/basic/spec/kslice_model.py) holds the model the rules check against;
  `left_s_rules.py`, `right_s_rules.py`, `mid_s_rules.py` are the pages' modules.
- Result: every rule holds on the VG-8020, every recorded output is read by a rule, and **zerobas agrees in every
  case** (0 of 1,224 differ). Controls: the model with rounding in place of truncation makes 22 LEFT$ cases false;
  MID$ with position 0 allowed, 104; LEFT$'s data judged by RIGHT$'s rules, 15.
- Two user-page findings: MID$'s error table still said an extra argument is "2 on the reference, 13 here" after the
  difference was fixed (zerobas raises 2, case KS FX 30); corrected on the page.

**Found in passing (not a slice-function rule):** `FOR I=1 TO 0 ... NEXT` runs its body ONCE, on the VG-8020 and on
zerobas alike (`10 S$="":FOR I=1 TO 0:S$=S$+"X":NEXT` leaves `LEN(S$)` 1 and I 2; `FOR J=5 TO 1` prints J = 5, then
J is 6). [FOR.md](FOR.md) does not say so; it belongs on FOR's spec page when the flow region comes.

### The second unit (2026-11-24): LEN, ASC, CHR$, SPACE$, STRING$, INSTR

One probe, six rules modules, six pages at DRAFT 1:

- [probes/basic/spec/kstr.py](../../probes/basic/spec/kstr.py): 2,044 cases on each machine in ten groups (SRC:
  LEN / ASC over 41 sources; NUM: CHR$ / SPACE$ over the 28 numbers; STRN: STRING$ over 28 counts x 17 codes;
  STRS: STRING$ over 28 counts x 5 fill strings; INS1-INS4: INSTR over 5 haystacks x 13 (8) needles x 21 starts;
  OS: SPACE$ / STRING$ where `CLEAR 200`'s string space runs out; FX: 115 fixed statements). Run file
  [scratchpad/KST_run1.out](../../scratchpad/KST_run1.out). Its record holds BOTH result kinds -- `R$`'s digest and
  `R`'s own 8 bytes, each with its sentinel -- so a numeric function that wrote a string, or the reverse, is seen.
- [kstr_model.py](../../probes/basic/spec/kstr_model.py) holds the model and the rule builders; `len_rules.py`,
  `asc_rules.py`, `chr_s_rules.py`, `space_s_rules.py`, `string_s_rules.py`, `instr_rules.py` are the pages' modules.
  [kstr_controls.py](../../probes/basic/spec/kstr_controls.py) runs ten rival rules over the same reference cases;
  each is FALSE on some (rounding for CHR$ / SPACE$, INT for CHR$, a C-string LEN, ASC of the last character, the
  code before the count, an empty fill allowed at count 0, INSTR searching one past the start, start 0 allowed, and
  zerobas's own empty-needle rule).
- Result: every rule holds on the VG-8020 and every recorded output is read by a rule. zerobas differs in 39
  cases, two new items: **D-INSTREMPTY** (`INSTR(p,a$,"")` with p past the end is 0 on the reference,
  min(p, LEN(a$)+1) here; `INSTR("","")` 0 vs 1; 34 cases) and **D-CLOSESPACE** (a space between INSTR's or
  STRING$'s last STRING argument and `)` is a syntax error here; 5 cases). LEN, ASC, CHR$ and SPACE$ agree in every
  case.
- Found in passing, on both machines: `INSTR("A",S$,T$)` is a Syntax error (a string first means the two-string
  form, so the third argument is one too many); `STRING$(-1,"A"` (unclosed) is error 5 -- the count is checked
  before the rest of the call is even parsed.

### The third unit (2026-11-24): STR$, VAL, HEX$, OCT$, BIN$

One probe, five rules modules, five pages at DRAFT 1:

- [probes/basic/spec/knum.py](../../probes/basic/spec/knum.py): 571 cases on each machine in four groups (SN: STR$
  over 13 integers, 76 singles and 32 doubles; RX: HEX$ / OCT$ / BIN$ over 8 integers, 8 singles and 43 doubles;
  VL: VAL over 183 byte strings; FX: 90 fixed statements). Run file
  [scratchpad/KNM_run1.out](../../scratchpad/KNM_run1.out). A numeric argument is READ into a variable of the
  case's own type and that variable's bytes are recorded BEFORE the call, so the rules work from the exact value
  given (`ramrec.number`), not from the DATA text; a string result is recorded byte for byte (24 bytes, the length,
  the sum); VAL's result as R's 8 bytes. VAL's record also holds the byte that follows its string in memory (the
  build leaves the string's own prefix there), so reading past the end would be seen.
- [knum_model.py](../../probes/basic/spec/knum_model.py) holds the models -- PRINT's number format, the 16-bit
  pattern of the radix functions, VAL's scanner -- and the rule builders; `str_s_rules.py`, `val_rules.py`,
  `hex_s_rules.py`, `oct_s_rules.py`, `bin_s_rules.py` are the pages' modules.
  [knum_controls.py](../../probes/basic/spec/knum_controls.py) runs 17 rival rules over the reference's cases; every
  one is FALSE on some (PRINT's trailing space, no leading space, full form only to 6 digits or down to .001, `D`
  for doubles; truncation above 32767, rounding, the range test before truncation; zerobas's four VAL rules,
  half-even rounding, truncation, 6 digits after an `E`).
- Result: every rule holds on the VG-8020 and every recorded output is read by a rule. STR$, HEX$, OCT$ and BIN$
  agree in every case. VAL differs in 19 cases, two new items: **D-VALWS** (TAB and LF are skipped inside a number,
  and whitespace between `&` and its letter, on the reference; 13 cases) and **D-VALEXP** (the exponent byte wraps
  past 255 digits, and a value whose exponent lands on 0 keeps its digit bytes, on the reference; 6 cases).
- Measured on both machines, now rules (the user pages said otherwise or nothing): HEX$ / OCT$ / BIN$ truncate
  below 32768 but take n - 65536 BEFORE truncating from 32768 up, so 32768.5 is &H8001 and 65535.5 is "0", not an
  error; STR$ writes a number in full from .01 to below 10^14 for singles too (1E13! is 14 digits), with `E` for a
  double's exponent; VAL keeps 14 digits rounded half up, keeps 7+ digits through an `E` exponent, and `"1E-66"` is
  Overflow (the exponent wraps below 0).

### Goldfish pass 1 over the strings region (2026-11-24)

One fresh test-writer reviewer per probe family (scratchpad/REVIEW-m2-gkwslice.md, -gkwstr.md, -gkwnum.md; 74
findings), each acted on by an isolated agent; the counts above are the units' FIRST runs, these are the current ones.
**kslice.py:** +133 cases (MX: MID$'s position and count at the 16-bit edges, 88; FY: 45 statements with the source
rebuilt and checked by content); its rival rules now live in kslice_controls.py (21, each false somewhere); no new
divergence. **kstr.py:** a 30-byte record (the sources now checked by content), +30 cases, the STRN group split in
two so no group's records reach $F380 (asserted -- docs/clean-room-audit.md 2026-11-24 near miss); 16 controls; no
new divergence (a literal STRING$ fill shows D-CLOSESPACE too). **knum.py:** +60 cases, 631 on each machine; 31
controls. The VAL page corrected: only the DIGIT COUNT wraps (192 ones are a zero that keeps its digits), an `E`
exponent is added without wrapping ("1E-194" and "1E300" are Overflow). VAL's zerobas differences are now three items:
D-VALWS (whitespace, incl. before `&`), D-VALEXP (the digit-count edges) and D-VALPCT (`"-32768%"` is Overflow here,
-32768 on the reference).

### The maths region's first unit (2026-11-24): ABS, SGN, INT, FIX, SQR

One probe, five rules modules, five pages at DRAFT 1. The transcendentals (EXP, LOG, SIN, COS, TAN, ATN) were the
second unit (below); RND is left for a later one (a seed / sequence harness of its own).

- [probes/basic/spec/kmath.py](../../probes/basic/spec/kmath.py): 160 cases a keyword on each machine (19 integers,
  66 singles, 52 doubles, 23 fixed statements; 4 more fixed statements are LET evidence no page loads) in four groups
  (MI / MS / MD: one per argument type, so no group's records reach $F380, asserted; FX). Run file
  [scratchpad/KMA_run1.out](../../scratchpad/KMA_run1.out). **The result's TYPE is seen** (§7 item 3): every case
  runs twice, `R=F(N)` (R's 8 bytes) and `Q=USR(F(N))`, where USR is the probe's own 18-byte routine above `CLEAR`'s
  limit that copies `VALTYP` and `DAC` -- the result unconverted, by the MSX convention [USR.md](USR.md) documents --
  into the probe's memory. An apparatus row per argument (no function) must give back the argument's own type and
  bytes on both machines, or the loader refuses the run. Only the probe's own memory is PEEKed.
- [kmath_model.py](../../probes/basic/spec/kmath_model.py) holds the models and the rule builders; `abs_rules.py`,
  `sgn_rules.py`, `int_rules.py`, `fix_rules.py`, `sqr_rules.py` are the pages' modules.
  [kmath_controls.py](../../probes/basic/spec/kmath_controls.py) runs 18 rival rules over the reference's cases; each
  is FALSE on some (ABS(-32768%) a double or error 6; SGN in the argument's type; FIX rounding, flooring, or a clean
  zero below 1; INT in the argument's type, toward zero, always a double, an integer whenever it fits; SQR correctly
  rounded, truncated, within 1 unit, a single for a single; the sign of 80 10 00 00 ignored; zerobas's LET).
- Result: every rule holds on the VG-8020 and every recorded output is read by a rule. SGN agrees in every case. Four
  new items, all invisible to PRINT (the values agree): **D-ABSINTEDGE** (`ABS(-32768%)` a single there, a double
  here), **D-INTNEGTYPE** (INT of a negative number with a fraction: the integer -1 above -1, a double below, on the
  reference; the argument's type here), **D-ZEROLET** (a single whose exponent byte is 0 but whose digit bytes are
  not -- FIX(.5!)'s result -- is stored as zero bytes here, as its own bytes on the reference), **D-SQRZERO** (`SQR(0%)`'s
  result keeps leftover digit bytes here). SQR's last digit differs in 35 cases, the known difference ruled by Joost
  on 2026-07-13 -- now measured as within 3 units of the 14th digit on the reference, not "one unit low".
- Measured on both machines, now rules (the user pages said otherwise or nothing): SGN is always an integer; SQR is
  always a double; a literal `2.5` is a single, `7` an integer, `-32768` a single, `1/4` a double; FIX and INT of a
  number below 1 return a zero that keeps the argument's digit bytes (exponent byte 0, the sign dropped); SGN and
  SQR see `80 10 00 00` (sign bit, exponent 0) as negative.

### The maths region's second unit (2026-11-24): EXP, LOG, SIN, COS, TAN, ATN

One probe, six rules modules, six pages at DRAFT 1:

- [probes/basic/spec/ktrans.py](../../probes/basic/spec/ktrans.py): 1,762 cases on each machine (255 a keyword, plus 232 apparatus rows) in six
  groups (TI: 33 integers; TS1 / TS2: 56 + 53 singles; TD1 / TD2: 51 + 39 doubles; FX: 23 fixed statements a
  keyword), on kmath's frame unchanged -- the argument's own bytes, `R=F(N)`'s 8 bytes, and the result's TYPE and
  bytes through the probe's USR routine, checked per argument by the `ID` apparatus row. Run file
  [scratchpad/KTR_run1.out](../../scratchpad/KTR_run1.out). The arguments sit at the special points, at +-x for the
  symmetry rules, across the whole range of each type, at EXP's overflow and underflow edges, at LOG's domain edge,
  and at the angle reduction's landmarks (multiples of pi/4 in 14 digits, 1E10 ... 9.99999E62).
- [ktrans_model.py](../../probes/basic/spec/ktrans_model.py) holds the exact mathematics (Decimal, 60+ digits), the
  models and the rule builders; `exp_rules.py`, `log_rules.py`, `sin_rules.py`, `cos_rules.py`, `tan_rules.py`,
  `atn_rules.py` are the pages' modules. **A transcendental's rule is a BOUND**: a double within B units of the 14th
  significant digit of an exact target, B the reference's measured worst rounded up (EXP 3 / 500 / 40,000 by range,
  LOG 10, SIN / COS 2.5, TAN 6, ATN 3). [ktrans_controls.py](../../probes/basic/spec/ktrans_controls.py) runs 27
  rival rules over the reference's cases; each is FALSE on some (every bound tightened, the true sin / cos / tan in
  place of the reduced one, three rival reductions, zerobas's zeros and band, correct rounding everywhere, a single
  result for a single argument).
- **The trig reduction is now a rule** (inferred from the outside, as D-TANBIG did for large angles): p = x *
  0.15915494309190 in 14 digits; SIN is the sine of 2 pi frac(p), COS of 2 pi frac(r14(1/4 - p)); TAN errs (6) exactly
  where COS's reduced angle is a whole or half turn. It fits all 431 nonzero SIN / COS results within 2.1 units.
- Result: every rule holds on the VG-8020 and every recorded output is read by a rule. LOG agrees in every case
  (within its bound). Three new items: **D-TRIGHALF** (TIER 1: near a half or whole turn zerobas keeps more of the
  angle than the 14-digit reduction -- SIN(3.1415926535898#) -1.5707963267949E-13 here, -1.2566370614359E-13 there;
  16 cases over SIN / COS / TAN), **D-SINDIGITS** (zerobas's sine up to 6.1 units off the reduced target, the
  reference's worst 1.9; 8 cases over SIN / TAN), **D-TRANSZERO** (TIER 6: the zero results' digit bytes -- the reference's SIN /
  COS / TAN zero carries 2 pi's digits 00 62 83 18 53 07 17 96; EXP's tiny and flushed zeros; ATN of a signed zero;
  integer-zero leftovers in R as D-SQRZERO). EXP's Overflow band and huge negatives (17 cases) are the deliberate
  §12.9 difference, already standing.
- Measured on both machines, now rules (the pages said otherwise or nothing): all six always return a DOUBLE; EXP(0)
  and COS(0) are exactly 1, LOG(1) exactly 0; SIN, TAN and ATN are odd and COS even, byte for byte; LOG's reference
  error is up to 8.3 units (the page said 5); ATN's worst is 2.7 units on BOTH machines (the page's 2-unit target is
  neither's); below 1E-64 EXP returns a zero that keeps e^x's digits, then Overflow down to 1E-129, then 0 down to
  x = -65536, then Overflow again from -99999.

## 7. Tooling: what exists, what is missing

Exists and fits unchanged: `tools/spec_rules.py` (the checker is not BIOS-specific: a module, its cases, its rules,
field-level coverage); `omsx_repl.run_cases` with `mem_abs` capture and the sentinel; `kwdoc_examples.py` (the
example check); `tools/kwforms.py` and `tools/kwerrset.py` (the authored FORMS and the measured ERROR SET per
keyword form, which say how many forms and errors a page's matrix must reach).

Missing:
1. **A keyword page as a gate** (spec-method §8). `tools/spec_live.py` re-runs a BIOS page's probes on zerobas only,
   but it finds them through the `.asm` probe named in a run file's header and runs them with `biosl_run.py`. A
   keyword probe needs a zerobas-only mode (`kslice.py` measures both machines today) and a run-file header that
   names it; then spec_live can dispatch on the probe kind. Until then the pilot's pages are checked against their
   committed run only (`spec-rules-check`), and a later zerobas change is not caught by them.
2. ~~A shared RAM-record library~~ **built 2026-11-24:** [ramrec.py](../../probes/basic/spec/ramrec.py) -- the
   frame line, the error line, the string-digest subroutine, `measure` (both machines, sentinel capture), `frame`
   (refuses a capture without the done flag and the end byte), `digest`, the run file's sections. kslice uses it;
   its program text, run file and decoded cases are byte-identical through it.
3. **Number readouts:** built. `ramrec.number` decodes a numeric variable's own bytes exactly (integer, single,
   double BCD); kstr records `R`'s 8 bytes through it, and knum a typed ARGUMENT's own bytes as well. A result's
   TYPE is seen since kmath (2026-11-24): the probe's own USR routine copies `VALTYP` and `DAC` as USR receives
   them, checked on every argument by an apparatus row; a later numeric probe can reuse `kmath.ROUTINE` and the
   `ID` row.
4. **A tie to the existing denominators:** a rules module could assert that its fixed expressions reach every
   (form, error) pair `kwerrset.py` lists for the keyword, so a spec page cannot miss an error the T6 rung knows.
5. **The review loop** (spec-method §6) has not run on a keyword page yet; the pilot pages are DRAFT 1.
