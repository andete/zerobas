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
- **Cassette statements (Joost, 2026-11-25: "I don't see a reason to treat them different").** `CLOAD`, `CSAVE`,
  `MOTOR` and the `CAS:` forms of region 13 are specified like every other keyword, and their differences follow the
  same rules as any other keyword's.

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
second unit (below); RND the third, on a sequence harness of its own (below).

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

### Goldfish pass 1 over the maths region (2026-11-24)

Two fresh test-writer reviewers (scratchpad/REVIEW-m2-gkwmath1.md, -gkwmath2.md; 46 findings), each acted on by an
isolated agent; the figures in the two unit sections above are the units' FIRST runs, these supersede them.
**kmath.py:** +103 cases (FY 93, FZ 10); each literal's type and each argument's bytes against its DATA text are checked
before any rule; measured order-of-checks rules on all five pages; two new items (D-ARGTYPEORDER: `F("A"` is 2 on the
reference, 13 here; D-ZEROMUL: `INT(.5!)*3` keeps digit bytes there). **ktrans.py:** +117 cases (TS3 46, TD3 18, FY 53).
Corrected: SIN's bound is 2 units (p rounded half UP to 14 digits; flushed to 0 below 6.28318E-64); COS rounds 1/4 - p
half DOWN in size (half up, half-even and truncation are each false), so its zero and TAN's Overflow begin at 7E12
(also 1.2E13, 1.7E13), on zerobas too; LOG's bound is 9; EXP's Overflow for huge negative arguments begins between
-75453 and -75460 (not -99999). D-TRANSZERO now includes one visible case (ATN of a POKEd signed-zero single prints
"-." here, 0 on the reference); D-SINDIGITS: 17 SIN and 3 TAN results outside the tightened bound.

### The maths region's third unit (2026-11-24): RND -- a sequence harness

One probe, one rules module, RND.md at DRAFT 1; with it all twelve maths keywords are at DRAFT 1.

- [probes/basic/spec/krnd.py](../../probes/basic/spec/krnd.py): 556 STEPS on each machine in eight groups (BOOT:
  direct mode from power-on, before any program line; RUNR / GOTO / GOTO2: the state at a program's first line after
  RUN, after GOTO, after a typed line; SQ1: positive and zero arguments of every type; SQ2: 46 reseeds; SQ3: 200
  steps; FX: 61 fixed statements). Run file [scratchpad/KRN_run1.out](../../scratchpad/KRN_run1.out). **A record is
  a step, not a case**: it holds the result (R's 8 bytes, or VALTYP and DAC through kmath's USR routine) AND the
  generator's state after the step -- RNDX, `$F857..$F85E`, the published work-area cell (named by C-BIOS's source;
  shown black-box to be the state: it steps on RND(1), stays on RND(0), is set by RND(-x) whatever came before).
  A group whose records are typed in DIRECT mode (BOOT) cannot zero its record area first: a long first line delays
  the typist and the next line is delivered mangled (the harness refused the first attempt); BOOT's records
  therefore write only the fields they own, and its ARG / DAC bytes are not read.
- [krnd_model.py](../../probes/basic/spec/krnd_model.py): the generator stated on the bytes -- S' = (A S + C) mod
  10^14 with July's black-box constants, a reseed from the argument's 14 mantissa digits, the result S / 10^14
  normalised -- and two prediction modes, so no rule replays the reference's output: one step from the state the
  previous record read, and whole groups from power-on / CLEAR and the arguments alone (R-RND-CHAIN).
  [krnd_controls.py](../../probes/basic/spec/krnd_controls.py) runs 20 rivals, each FALSE on some (each constant's
  last digit, RND(0) stepping, a positive argument reseeding, the reseed from the VALUE, right-aligned integer
  digits, right-to-left evaluation, an unnormalised result, RNDX holding the result, zerobas's three differences ...).
- Result: every rule holds on the VG-8020 and every recorded output is read by a rule; the July constants predict
  all 556 steps. zerobas agrees in every number and in RNDX, except: **D-RNDLINE** (TIER 1: typing a program line
  resets the state on the reference -- as CLEAR -- and not here; 5 cases), **D-RNDZERO** (TIER 6: state 0's result is 8
  zero bytes there, a zero with leftover digit bytes here; 6 cases), and `RND("A"` / `RND("A",2)` (13 here, 2
  there: D-ARGTYPEORDER, now noted for RND).
- Measured on both machines, now rules: `R$=RND(1)` steps the sequence before its Type mismatch; a single or double
  whose exponent byte is `&H80` reseeds from its digit bytes (the sign BIT decides), one with exponent byte 0 is a
  zero; `-1!/3` is a DOUBLE (so `RND(-1!/3)` is `RND(-1/3)`); two calls in one expression run left to right; CLS and
  GOTO keep the state.

### The conversion region's first unit (2026-11-24): CINT, CSNG, CDBL

One probe, [kconv.py](../../probes/basic/spec/kconv.py) -- kmath's frame, record and USR type readout, ktrans's
program builder -- over 13 integers, 49 singles and 44 doubles chosen where rival conversions disagree, and 80 fixed
statements; run file [scratchpad/KCV_run1.out](../../scratchpad/KCV_run1.out); model
[kconv_model.py](../../probes/basic/spec/kconv_model.py), controls
[kconv_controls.py](../../probes/basic/spec/kconv_controls.py) (11 rivals, each FALSE on some case). All three pages
at DRAFT 1; every rule holds on the VG-8020 and every recorded output is read. Measured: CINT truncates toward zero
and checks the range AFTER (32767.9 is 32767, 32768 Overflow); CSNG rounds a double half up on the 7th digit by
magnitude, a carry reaching the exponent -- so `CSNG(9.999995D62)` is Overflow (the page had said CSNG has no range
error: refuted); CDBL appends 8 zero digits to a single's 6. zerobas agrees on every value; its differences are
D-ARGTYPEORDER (all three), [D-CSNGOVERUSR](../../todo/open/D-CSNGOVERUSR.md) and
[D-CONVZERO](../../todo/open/D-CONVZERO.md) (both TIER 6). Next in the region: MKI$ / MKS$ / MKD$ and CVI / CVS /
CVD (string results: a STR_DIGEST record).

### The conversion region's second unit (2026-11-24): MKI$, MKS$, MKD$, CVI, CVS, CVD

One probe, [kmkcv.py](../../probes/basic/spec/kmkcv.py) -- a 37-byte record (the number's own bytes or the source
string's, R, S$'s length and bytes, the USR type readout) -- run on TWO pairs: the National CF-3300 (Disk BASIC, the
pages' reference) against zerobas DISK (groups DMK / DCV / DFX; [ramrec.py](../../probes/basic/spec/ramrec.py)'s
`measure(..., disk=True)` boots each with a copy of `disk/test720.dsk`, its records below $DE00), and the VG-8020
against zerobas NODISK (MK / CV / FX). Run file [scratchpad/KMC_run1.out](../../scratchpad/KMC_run1.out); model
[kmkcv_model.py](../../probes/basic/spec/kmkcv_model.py), controls
[kmkcv_controls.py](../../probes/basic/spec/kmkcv_controls.py) (17 rivals, each FALSE on some case). All six pages at
DRAFT 1. Measured: MKI$ / MKS$ / MKD$ ARE CINT / CSNG / CDBL followed by the result's own bytes (so `MKS$(9.999995D62)`
is Overflow -- the page had said MKS$ has no range error: refuted); CVI / CVS / CVD take the first 2 / 4 / 8 bytes of
a string at least that long, raw; without Disk BASIC every call whose argument computes is error 5. zerobas agrees on
every value; differences [D-MKNOPAREN](../../todo/open/D-MKNOPAREN.md) (`S$=MKI$` 24, not 2),
[D-DISKFNTYPE](../../todo/open/D-DISKFNTYPE.md) (diskless: a wrong-type argument 13, not 5), and D-ZEROLET for CVS.
**A probe pitfall, caught before any rule ran:** the empty source string's `FOR K=1 TO 0` loop ran its body ONCE (MSX
BASIC's FOR, noted above), reading a byte that belonged to the next case and shifting every later DATA read; both
machines shifted alike, so no difference showed it -- only the decoded lengths did (`[0]` with an S$ of 1 byte). The
loop is now behind `IF L>0`. spec-live re-types the D* groups on zerobas's DISK build.
The conversion region is complete at DRAFT 1.

### Goldfish pass 1 over the operators' first unit (2026-11-24)

One reviewer ([REVIEW-m2-gOPS1.md](../../scratchpad/REVIEW-m2-gOPS1.md)), 17 items: real 15, minor 2 (worked values
in the Details tables backed only by the example runs; the FX chains that do not separate, now said so). A new
group, KOP FY (41), measured what the rules asserted beyond their cases: precedence rows that SEPARATE (`1<2 AND 1`,
`1 EQV 2+3`, `1=1 IMP 1=0`, `6 OR 1 IMP 0` ...), MOD's own grouping and its place against `/` and `^`, Overflow
before Division by zero, right operands out of range for every operator, a twenty-NOT chain -- all as the pages
said. Two findings: the LEFT operand is made an integer as soon as the operator is met (`70000 AND "A"` is 6, not 13
-- predicted wrong, 55%); and D-MINUSNOT is wider than `-NOT 0`: NOT after ANY operator (`2*NOT 0`, `2+NOT 0=0`)
is a Syntax error on zerobas. NOT's summary, evidence and ERRORS text corrected (a one-operand operator); the open
lists name DAC's other bytes as non-evidence and the error set's closure (nesting, structure errors).

### The operators region's second unit (2026-11-24): LET, SWAP

One probe, [klet.py](../../probes/basic/spec/klet.py): each case its own line starting from `CLEAR`, the statement
under test last, the next line reading ERR and up to two variables (a number's bytes, a string's length and first 7
bytes); 57 cases; run file [scratchpad/KLT_run1.out](../../scratchpad/KLT_run1.out); model
[klet_model.py](../../probes/basic/spec/klet_model.py) (stores by CINT's / CSNG's rules), controls
[klet_controls.py](../../probes/basic/spec/klet_controls.py) (9 rivals, each FALSE on some case). Both pages at
DRAFT 1; every rule holds on the VG-8020. New on SWAP's page: an operator after the second variable (`SWAP A,B+0`)
exchanges FIRST and raises Syntax error after -- the page had it among the plain shape errors. One difference:
[D-SWAPNEW](../../todo/open/D-SWAPNEW.md) (a failed SWAP with a new second variable leaves it holding the first's
value here). **Two probe pitfalls, caught before any rule ran:** reading a plain name's TYPE from the byte before its
VARPTR assumes MS-BASIC's variable-table layout (zerobas's differs, an array element has none) -- the cases now name
each variable's type; and a variable created AFTER an array element's VARPTR was taken moves the arrays, so the
address went stale (`Q$(0)` read as "" on both machines) -- the probe's own variables now exist before each case.
The operators region is complete at DRAFT 1.

### Goldfish pass 1 over the conversion region (2026-11-24)

Two reviewers, one per unit ([REVIEW-m2-gCONV1.md](../../scratchpad/REVIEW-m2-gCONV1.md),
[REVIEW-m2-gMKCV1.md](../../scratchpad/REVIEW-m2-gMKCV1.md)): 20 + 23 items; scored real 34, known 4, wrong 0, minor
5. Two new fixed-statement groups measured what the rules asserted beyond their cases -- KCV FY (31) and KMC FY /
DFY (18 a pair) -- and the reference held every prediction: a POKEd double through CINT / CSNG / CDBL; `F(1/0` is 11
but `CINT(32768` and `CSNG(9.999995D62` with no `)` are 2 (the `)` before the conversion); a double stored in a
single rounds as CSNG, and past the top is error 6 leaving the variable as it was; CDBL of a single holding 1/3 is
.33333300000000 (the reviewer's "is it widening at all?" answered); MKS$'s exact ties round half up in both signs;
an error leaves `S$` as it was (not emptied); CVD returns non-canonical doubles raw. Found in passing, for the
operators region: `CSNG(1/3)*3!`, a single times a single, is a DOUBLE on both machines. Corrected: stale sentences
on CSNG / CDBL / MKS$ / MKD$ / CVI / CVS / CVD (sibling-only syntax, "{2, 13}", "a diskless zerobas does the same"),
MKI$'s order of errors, CVS's sign-bit zero, MKD$'s "converted, not padded" (integers only), the mislabelled FX 78
(it is a double), CSNG-ASSIGN now reads the statement's own error (R is the same on both machines), and each CV
page's ASSIGN text cut to its own type. No new zerobas difference: the new failures are D-CONVZERO (doubles too),
D-CSNGOVERUSR (the negative end) and D-DISKFNTYPE. Minor / kept: CINT's exponent-0 clause cannot be separated from
truncation (both give 0); the literal types are kmath's measured LIT rows; the error-set closure (Out of string
space) and DAC's bytes beyond the result are in the open lists.

### The operators region's first unit (2026-11-24): AND, OR, XOR, EQV, IMP, NOT, MOD

One probe, [kops.py](../../probes/basic/spec/kops.py) -- two operands READ into X / Y of each type, both recorded, a
35-byte record -- over 20 integer, 20 single and 14 double pairs and 87 fixed expressions (precedence: every ordered
pair of the two-operand logical operators, NOT against comparisons and arithmetic, MOD among `*` `+` `\`; literal
types; each operator's error forms); run file [scratchpad/KOP_run1.out](../../scratchpad/KOP_run1.out); model
[kops_model.py](../../probes/basic/spec/kops_model.py) (CINT's conversion, then 16-bit logic, and a small precedence
parser for the fixed expressions), controls [kops_controls.py](../../probes/basic/spec/kops_controls.py) (31 rivals,
each FALSE on some case). All seven pages at DRAFT 1; every rule holds on the VG-8020. Measured, and now stated:
NOT binds below the comparisons and arithmetic (`NOT 1<2` is 0, `NOT 1+2` -4) -- NOT's page had it unmeasured;
MOD sits between `\` and `+` -- MOD's page had it unmeasured. zerobas agrees in every case but one:
[D-MINUSNOT](../../todo/open/D-MINUSNOT.md), `-NOT 0` a Syntax error here (1 there). LET and SWAP are the region's
second unit.

### Goldfish pass 1 over RND (2026-11-24)

One reviewer ([REVIEW-m2-gRND1.md](../../scratchpad/REVIEW-m2-gRND1.md)), 19 items, scored: **real 15**, known 1,
wrong 0, minor 3. Four rules asserted more than their cases reached; a new direct-mode group, **EDIT** (17 steps),
measured them and the reference held every prediction (a line re-typed / replaced / deleted, `RUN 20` and
`MAXFILES=` reset; RNDX is the state; a reseed from a leading-zero number takes the normalised digits; a sign-bit
zero reseeds from 0). One new difference: zerobas takes that sign-bit zero for a zero,
[D-RNDNEGZERO](../../todo/open/D-RNDNEGZERO.md) (TIER 6). The citation items (a stale status block, FX 55 counted
as a difference, `-0` arguments that are stored as zero bytes, rule texts citing rows their selections exclude, the
probe's pre-image comment) are corrected. Kept as minor: an integer's "left-aligned digits" equal a conversion's
(no case can separate them); the S = 1 example read only through USR (open list); the known item is the
RNDX-copy rival, now a control. Two new controls: MAXFILES= keeping the state, RNDX a copy.

## 7. Tooling: what exists, what is missing

Exists and fits unchanged: `tools/spec_rules.py` (the checker is not BIOS-specific: a module, its cases, its rules,
field-level coverage); `omsx_repl.run_cases` with `mem_abs` capture and the sentinel; `kwdoc_examples.py` (the
example check); `tools/kwforms.py` and `tools/kwerrset.py` (the authored FORMS and the measured ERROR SET per
keyword form, which say how many forms and errors a page's matrix must reach).

Missing:
1. ~~A keyword page as a gate~~ **built 2026-11-24:** `tools/spec_live.py` re-types each group of a keyword run file
   on zerobas only (the probe whose `RUN = "..."` names the file; `ramrec.measure` with zerobas alone), replaces
   its `CAP zb  :` line, and evaluates the page's rules on that live copy; `make spec-live` runs the BIOS and the
   keyword pages together (`--keywords` for these alone; ~140 s of boots, 4 at a time). The first run
   ([AE_kwlive1.out](../../scratchpad/AE_kwlive1.out)): every group's capture as committed; 11 of 26 pages'
   Differences lists did not match their failing rules -- rules cited as context counted, failing rules not cited.
   **The convention since:** in "Differences from the reference" a rule zerobas FAILS is cited as `rule R-X-Y` /
   `rules R-X-Y, R-X-Z` (shortened after the first, `rules R-RND-VALUE, -SEED`), or anywhere inside a parenthesis
   that opens with "rule(s)"; a rule named as context ("its own result agrees (R-ABS-ODD)", "R-SQR-LET holds") has
   no "rule" before it. spec-live requires the cited set to equal the failing set, as for the BIOS pages' tables.
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

### The flow region's first unit (2026-11-25): FOR, NEXT

One probe, [kfor.py](../../probes/basic/spec/kfor.py): each case its own line from `CLEAR`, the body counting its runs
in WN%, the next line recording the FIRST error, the LAST error, the runs and the loop variable; 43 cases; run file
[scratchpad/KFR_run1.out](../../scratchpad/KFR_run1.out); model [kfor_model.py](../../probes/basic/spec/kfor_model.py),
controls [kfor_controls.py](../../probes/basic/spec/kfor_controls.py) (8 rivals, each FALSE on some case). Both pages at
DRAFT 1; every rule holds on the VG-8020 and every recorded output is read. Measured: the body runs AT LEAST ONCE (`FOR
I=3 TO 1` once, I 4 -- predicted 0 runs: a miss); an integer variable TRUNCATES start, limit and STEP (STEP .5 never
ends); a limit it cannot hold is Overflow at the FOR; STEP 0 never ends, also with the start past the limit; limit and
STEP are read once; a FOR that fails pushes NO frame. Four differences, filed: [D-FORFRAME](../../todo/open/D-FORFRAME.md)
(TIER 3: a failed FOR keeps its frame on zerobas -- with RESUME NEXT and STEP missing the program hangs),
[D-FORINTLIM](../../todo/open/D-FORINTLIM.md), [D-FORSTEP0](../../todo/open/D-FORSTEP0.md),
[D-NEXTCREATE](../../todo/open/D-NEXTCREATE.md). **Three probe faults, each caught by a run that read wrong on BOTH
machines:** recording only the LAST error (RESUME NEXT runs on along the line: a failed FOR's body and NEXT then raise
NEXT without FOR over the FOR's own error); a guard `IF WN%>20 THEN n` before NEXT (a false IF skips the rest of the
line, NEXT included: every loop read one run) -- now `ON -(WN%>20) GOTO n`; and a VARPTR of a variable that does not
exist, which is error 5 on both machines and stopped zerobas's run.

### The flow region's second unit (2026-11-25): GOTO, GOSUB, RETURN

One probe, [kgosub.py](../../probes/basic/spec/kgosub.py): each case a block of 30 lines -- line n the statement(s)
under test, n+5 .. n+20 its own target lines, n+25 the record -- so a case can jump, call and come back; the record
holds the first and last error, a counter and WP%, the bits of the lines reached (WHICH lines ran, not only how many);
30 cases; run file [scratchpad/KGS_run1.out](../../scratchpad/KGS_run1.out); model
[kgosub_model.py](../../probes/basic/spec/kgosub_model.py), controls
[kgosub_controls.py](../../probes/basic/spec/kgosub_controls.py) (6 rivals, each FALSE on some case). Three pages at
DRAFT 1; every rule holds on the VG-8020 and every recorded output is read. Measured: RETURN drops every FOR frame
opened since its GOSUB, and a NEXT inside a subroutine does not reach a FOR outside it (error 1 both); RETURN n
continues at n; a line past 65529, or a number followed by more text, is error 8 (Undefined line number), not 2.
Predictions scored: RETURN drops the subroutine's FOR (hit), RETURN n accepted (hit), a missing line is 8 (hit). One
difference: [D-GOTOSPACE](../../todo/open/D-GOTOSPACE.md) (TIER 1) -- `GO TO` with exactly one space is GOTO on the
reference (also after THEN), a Syntax error on zerobas; two spaces, `GO SUB` and `GO` alone are Syntax errors on both.

### The flow region's third unit (2026-11-25): IF

One probe, [kif.py](../../probes/basic/spec/kif.py), on kgosub.py's 30-line blocks, plus a line n+1 reached only by
FALLING THROUGH line n (a false IF skips the rest of its line, the GOTO to the record included -- without it a false IF
ran the case's target lines); 32 cases; run file [scratchpad/KIF_run1.out](../../scratchpad/KIF_run1.out); model
[kif_model.py](../../probes/basic/spec/kif_model.py), controls [kif_controls.py](../../probes/basic/spec/kif_controls.py)
(5 rivals, each FALSE on some case). IF.md at DRAFT 1; every rule holds on the VG-8020 and on zerobas (0 of 32 cases
differ). Measured: any non-zero number is true (.5, 1E-30); a false IF skips the WHOLE rest of the line, a NEXT
included; ELSE belongs to the nearest unmatched IF and runs its statements plus the rest of the line; THEN followed by
nothing or a colon is no error; a missing line after THEN is error 8 only when taken. Predictions scored: the false
IF's skip (hit), ELSE's nearest IF (hit), a string condition is 13 (hit). Left of the flow region: END, STOP, CONT,
RUN -- they stop or restart the program that records, so they need a screen-based harness.

### The flow region's last unit (2026-11-25): END, STOP, CONT, RUN -- the region complete

These stop or restart the program, so a program cannot record them: [kstop.py](../../probes/basic/spec/kstop.py) is
the first keyword probe that reads the SCREEN (omsx_repl's capture), normalised -- lines stripped, the prompt ("Ok" /
"ZB", a deliberate difference) one token, the key line dropped -- and a rule reads a case's RESPONSE: the screen
without the prompts and without the echo of what was typed, cut at the line width (37, not 40: the first model missed
the two wrapped echoes). 19 cases; run file [scratchpad/KSP_run1.out](../../scratchpad/KSP_run1.out) (JSON); model
[kstop_model.py](../../probes/basic/spec/kstop_model.py), controls
[kstop_controls.py](../../probes/basic/spec/kstop_controls.py) (7 rivals, each FALSE on some case). tools/spec_live.py
gained a hook for such probes: a probe module with `live_copy(run_file, td)` re-measures its own run file. Four pages at
DRAFT 1; zerobas agrees on all 19. Measured: END drops the rest of its line and a pending GOSUB, silently, and CONT
after END goes on after it; STOP prints `Break in n` (in direct mode `Break`), CONT goes on after it -- inside a GOSUB
the RETURN still works, inside a FOR the loop goes on, a variable changed while stopped is seen; CONT before anything
ran or after a program line changed prints `Can't CONTINUE`, a direct statement in between does not block it, and
after an ERROR it runs the failing statement again (predicted "Can't CONTINUE": a miss); RUN clears the variables, RUN
n starts at n, a missing n is `Undefined line number`. **The flow region (GOTO GOSUB RETURN IF FOR NEXT END STOP CONT
RUN) is complete at DRAFT 1.**

### Goldfish pass 1 over the flow region (2026-11-25): the models were tables

One fresh test-writer reviewer per probe family (scratchpad/REVIEW-m2-gkwfor.md, -gkwgosub.md, -gkwif.md,
-gkwstop.md; about 150 findings). **The finding that matters is shared by all four: each flow model (kfor_model,
kgosub_model, kif_model, kstop_model) is a per-case TABLE of whole records, and each control is a hand edit of one row.**
A wrong law with right table entries passes, so "every rule is executable" held in form only. The rework, unit by
unit: an interpreter model whose laws are the rules' sentences, rivals that change ONE law, the reviewers' separating
cases added, and the apparatus findings fixed (a frame that uses the keyword under test -- kif's handler uses IF,
kgosub's frame uses GOTO, kfor's readout uses FOR; spec-plan §1 forbids it). Page claims the reviewers found the
records contradict are corrected in the same pass. Until then the four units stay DRAFT 1 with this note.

**FOR / NEXT reworked (2026-11-25), the first of the four.** [kfor_model.py](../../probes/basic/spec/kfor_model.py) is
now an interpreter of the FOR / NEXT laws (FOR's order of work, frames stacked on top, NEXT's lazy list, STEP 0 never
ending); [kfor_controls.py](../../probes/basic/spec/kfor_controls.py) holds 21 one-law rivals, each FALSE on some case.
[kfor.py](../../probes/basic/spec/kfor.py) gained a group FY of 33 separating cases (a second typed program: with them
one program outgrew the RAM below HIMEM), an error-count byte, and a readout without FOR / NEXT. Predictions for FY:
30 of 33 held; the three misses changed two rules -- **STEP 0 never ends even at start = limit** (Microsoft's sign
compare predicted one run) and **a second FOR on the same variable stacks a new frame instead of replacing the first**
(FOR.md had claimed "replaces", unmeasured). Page claims corrected: "matches in every case", FOR's error set, "one step
past the limit". zerobas: 11 cases differ, all filed -- D-FORINTLIM widened (start / limit / step conversion),
D-FORSTEP0 pinned, and two new items, D-NEXTFRAME (a failed NEXT J drops the open frame) and D-FORCOMMA.

**GOTO / GOSUB / RETURN reworked (2026-11-25), the second.** [kgosub_model.py](../../probes/basic/spec/kgosub_model.py)
is an interpreter over the case's own lines (the line number read digit by digit across spaces and only within 65529,
`GO TO` as the tokenizer's synonym, ONE stack for GOSUB and FOR, RETURN's check for a GOSUB before anything else);
[kgosub_controls.py](../../probes/basic/spec/kgosub_controls.py) holds 13 one-law rivals, each FALSE on some case.
[kgosub.py](../../probes/basic/spec/kgosub.py) gained group FY, 21 separating cases (absolute lines 6553 / 7000 for the
split at 65529). All 21 predictions for FY held. The frame keeps its GOTO on purpose (a wrong frame jump is refused by
the record frame's own check, never a plausible record) -- stated on the pages. zerobas: one new difference,
D-GOSUBFRAME (a GOSUB to a missing line pushes a frame).

**IF reworked (2026-11-25), the third.** [kif_model.py](../../probes/basic/spec/kif_model.py) is an interpreter that
walks the line character by character (statements end at `:` or ELSE; a false IF counts IF / ELSE levels to find its
ELSE; a true IF's first reached ELSE ends the line); [kif_controls.py](../../probes/basic/spec/kif_controls.py) holds
12 one-law rivals. [kif.py](../../probes/basic/spec/kif.py) gained group FY (28 cases, among them lines that END at
THEN / ELSE, which the appended `:GOTO` had made unreachable) and an error handler without IF (FX re-measured
byte-identical). FY predictions: 26 of 28 held; the misses are two laws now stated -- RESUME NEXT after an error in the
condition goes on at the next `:` OR ELSE (so `IF 1/0 THEN a ELSE b:c` runs neither part), and `IF c GOTO` without a
number is THEN. zerobas agrees on all 60.

**END / STOP / CONT / RUN reworked (2026-11-25), the last -- goldfish pass 1 over the flow region is acted on in
full.** [kstop_model.py](../../probes/basic/spec/kstop_model.py) types each case into a small BASIC (program lines,
direct statements, the resume point, open files, an error handler) and predicts the WHOLE normalised screen -- every
prompt and echo included, so a hang can no longer pass as "does nothing" and every recorded line is read (the first
model dropped 105 of 143). [kstop_controls.py](../../probes/basic/spec/kstop_controls.py): 26 one-law rivals.
[kstop.py](../../probes/basic/spec/kstop.py) gained group FY, 34 cases; the JSON run file now holds one section per
group. FY predictions: 31 of 34 held; the miss that matters -- **END closes open files on the VG-8020** (END.md had
said "stay open", a CF-3300 measurement: whether the references split is left open in D-ENDCLOSE). One case could not
reach its subject (FY 28's file was closed by END, not RUN) and was joined by two STOP-based ones. zerobas: three new
differences, D-ENDCLOSE, D-DELNOLINE, D-RUNCONT (TIER 6).

### The errors region's first unit (2026-11-25): DEFINT, DEFSNG, DEFDBL, DEFSTR -- the first interpreter model

[kdeftype.py](../../probes/basic/spec/kdeftype.py), 58 cases on the RAM-record harness (run file
[scratchpad/KDT_run1.out](../../scratchpad/KDT_run1.out)); the record keeps the first and last error, the type byte
before each named variable (`PEEK(VARPTR(v)-3)`) and a number the case leaves in `WV#`. Every probe variable carries
a suffix, so a case's `DEFSTR A-Z` cannot retype the probe. **The model, [kdeftype_model.py](../../probes/basic/spec/kdeftype_model.py),
is an interpreter** -- the answer to the flow region's goldfish pass: it runs each case's statements (the DEF list's
parse, the type of a name at each use, LET's conversion) and holds no per-case answer; the 11 controls in
[kdeftype_controls.py](../../probes/basic/spec/kdeftype_controls.py) each flip one law (all-or-nothing lists, a
swapped reversed range, CLEAR keeping the table, a variable keeping its birth type, rounding / flooring integers,
LET making its variable after the check, single precision truncating, a single default, a DEFSTR name apart from the
`$` one), and each is FALSE on some case. Behaviour agrees on all 58 cases. **One difference: the variable entry's
layout** -- the byte before the name is the type on the VG-8020 and the name's first letter on zerobas, whose entry is
[name0][name1][type][value] (D-VARLAYOUT, TIER 6). A first-run apparatus miss: `A=1E63` is Overflow when the line is
TYPED, so that case's line was never stored and its record repeated the previous case's -- replaced by `9.99999E62`.

### The errors region's second unit (2026-11-25): ERROR, ERR, ERL, RESUME (and ON ERROR GOTO's handler)

[kerr.py](../../probes/basic/spec/kerr.py), 40 SCREEN cases (run file [scratchpad/KER_run1.out](../../scratchpad/KER_run1.out)):
a probe that records into RAM catches errors with ON ERROR / RESUME NEXT, the keywords under test, so this one reads
the screen. The model is kstop's small BASIC, extended into ONE interpreter for every screen-reading keyword probe --
ERR / ERL on every error, a handler entered from the prompt too, No RESUME, ON ERROR GOTO 0 re-raising, RESUME's forms;
kstop's 53 screens still predicted. [kerr_controls.py](../../probes/basic/spec/kerr_controls.py): 13 one-law rivals.
Predictions from the pages: 37 of 38 held; the miss -- `ON ERROR GOTO A` is GOTO 0 on the VG-8020, not the Syntax
error RESUME.md claimed (that was zerobas's behaviour). A modelling fork (KST FY 3: after a handler ENDed, a typed
RESUME is not trapped) was decided by two added cases: RESUME's own error is never trapped; END does not disarm.
zerobas: two differences -- D-RESUMEMISS (TIER 3: `RESUME 99` to a missing line HANGS) and D-ONERRVAR (TIER 6).

### The errors region's last unit (2026-11-25): TRON, TROFF, REM -- region 6 complete

[ktron.py](../../probes/basic/spec/ktron.py), 25 SCREEN cases (run file [scratchpad/KTN_run1.out](../../scratchpad/KTN_run1.out);
`KTR_run1.out` was taken). The shared small BASIC gained the trace (`[n]`, no new line of its own, when a line is
entered from its top), REM / the apostrophe as the rest of the line, IF ... ELSE and GOTO; kstop's 53 and kerr's 40
screens are still predicted. [ktron_controls.py](../../probes/basic/spec/ktron_controls.py): 11 one-law rivals.
Predictions, taken from the pages: 25 of 25 held; zerobas agrees on all 25. **Region 6 (errors) is complete at
DRAFT 1**: DEFINT / DEFSNG / DEFDBL / DEFSTR, ERROR / ERR / ERL / RESUME, TRON / TROFF / REM.

### Goldfish pass 1 over the errors region (2026-11-25), and a working rule it forced

Three reviewers (scratchpad/REVIEW-m2-gkwdeft.md, -gkwerr.md, -gkwtron.md; about 140 findings). The structural finding,
in all three: with an INTERPRETER model every rule's check is the whole model, so a rule's ✓ says only that the model
agrees on the cases the rule selects -- not that its own SENTENCE was tested. **Rule from here on (Joost RULED 2026-11-25; now in
docs/spec-method.md §3a): every rule must have at least one one-law control that is FALSE on its own selection**; that
control is what pins the sentence. kdeftype_controls.py enforces it (a rule with no control of its own fails the run);
the other units follow as they are reworked. Also from the pass: a model that crashes under a rival law reads FALSE,
never an exception (kdeftype_model, kstop_model).

**DEF types reworked.** [kdeftype.py](../../probes/basic/spec/kdeftype.py): group FY (33 cases: the integer range
edges and the cut before the range test, the value a variable holds after an error, long names and two significant
characters, suffixed = unsuffixed, partial lists, spaces, arrays under a new type, DEF FN, CLEAR, an exact half, a FOR
start); WV# starts at a sentinel (-77); each record carries the case's own index, set at the end of its line, so a line
refused at typing cannot pass for its predecessor; the typed program's size is asserted. All 33 predictions held;
zerobas agrees on every value. The model gained a real FOR loop and DEF FN; its rule sentences now state every law it
uses; 18 controls, every rule pinned.

**ERROR / ERR / ERL / RESUME reworked.** [kerr.py](../../probes/basic/spec/kerr.py) gained group FY (29 cases from the
review); 27 of the predictions held. The misses, now stated laws: ERROR's bound is 32767 (`ERROR 40000` is Overflow --
the rule had said 65535), and ON ERROR GOTO acts on its number FIRST and checks the rest after (`ON ERROR GOTO A`
outside a handler is error 2 with the trap already off). Further laws the model had to learn from the reference: an
untrapped stop finishes the handler (a typed RESUME is then 22); after a GOTO 0 re-raise CONT runs the failing
statement again; RESUME leaves the GOSUB / FOR stack alone. The shared small BASIC also lost a wrong law the TRON
review found -- "a string literal followed by anything but `;` is error 2" (PRINT "A","B" is legal) -- for a real item
parser; RESUME's own error is untrapped because it is a RESUME, not because its code is 22; a run that never returns
leaves no prompt. 20 controls, every rule pinned.

**TRON / TROFF / REM reworked -- goldfish pass 1 over region 6 is acted on in full.** [ktron.py](../../probes/basic/spec/ktron.py)
gained group FY (17 cases: a line jumping to itself, a loop inside one line, RETURN to a line start, the trace through
a handler, CONT, a typed GOTO, ON n GOTO / THEN n targets, a traced REM line, an error after the trace, TROFF inside a
program, REM inside DATA, an apostrophe in a string and after THEN, `GOTO 30 REM X`, a non-default ELSE sentinel,
PRINT with a comma). All 17 predictions held; zerobas agrees on all. The small BASIC learned ON n GOTO, THEN n, string
READ, and lost an empty-THEN bug its own new case exposed. 13 controls, every rule pinned; the kstop, kerr, ktron and
kdeftype controls all enforce "a control of its own" now. Each page has its own Open list (one paragraph had been
copied across all three).

### The program region's first unit (2026-11-25): DATA, READ, RESTORE

[kdata.py](../../probes/basic/spec/kdata.py), 29 SCREEN cases (run file [scratchpad/KDA_run1.out](../../scratchpad/KDA_run1.out)),
taken from the three pages' own claims: DATA's item cutting (spaces, quotes protecting `,` and `:`, an unterminated
quote, empty items), a bad item's Syntax error in the DATA line, Out of DATA mid-READ, the position across RUN / CLEAR /
an edit / a direct READ, RESTORE n to a line with and without DATA, `RESTORE X` and `RESTORE,` (8). Every page claim
held; zerobas agrees on all 29. The small BASIC gained real DATA cutting and one READ pointer
(kstop / kerr / ktron screens still predicted). 11 controls, every rule pinned by one of its own -- the first unit
built under the working rule from the start. Two stale page sentences corrected (READ's Overflow row, RESTORE's
"not yet measured").

### The program region's second unit (2026-11-25): DIM, ERASE, CLEAR

[kdim.py](../../probes/basic/spec/kdim.py), 42 SCREEN cases (run file [scratchpad/KDM_run1.out](../../scratchpad/KDM_run1.out)),
taken from the three pages' claims: bounds from 0, the default bound 10, two dimensions, the 65535-byte check before
free memory, DIM's errors and its one-by-one making, ERASE's suffix-as-name and one-by-one removal, CLEAR's resets,
CLEAR n / FRE of an empty string, a bare CLEAR keeping the size (CLEAR n,top sets n), CLEAR's errors, a refused CLEAR
changing nothing. The memory-limit cases sit far from the edge, so no expectation depends on a free-memory figure.
Every page claim held; zerobas agrees on all 42. The small BASIC gained arrays (dim / element), ERASE and CLEAR
n,top, and lost two bugs its new cases exposed (PRINT's item scanner split inside parentheses; ERASE left the old
elements). 10 controls, every rule pinned.

### The program region's third unit (2026-11-25): NEW, LIST, DELETE, RENUM

[klist.py](../../probes/basic/spec/klist.py), 39 SCREEN cases (run file [scratchpad/KNL_run1.out](../../scratchpad/KNL_run1.out)),
taken from the four pages' claims: NEW's erasing (the string space stays; inside a program it stops; `NEW 1` erases
nothing), LIST's ranges with no range errors, `.`, LIST ending its line without being an edit, numbers relisted in the
machine's spelling, DELETE's checks before deleting (the high end must exist, the low need not) and its being an edit,
RENUM's numbering, its rewriting of references but not of text, its report of a missing target, its refusals and its
keeping the CONT point. Every page claim held; zerobas agrees on all 39. The small BASIC gained LIST / DELETE / RENUM
and output that wraps at 37 (a listed line of 38 characters showed it -- the TRON reviewer had predicted the model
would miss exactly that). 17 controls, every rule pinned. AUTO (CTRL+STOP) and LLIST (a printer) need their own
harness; their pages' Open lists say so. Region 7 is complete at DRAFT 1 but for those two.

### Goldfish pass 1 over the program region (2026-11-25)

Three reviewers (scratchpad/REVIEW-m2-gkwdata.md, -gkwdim.md, -gkwlist.md; ~130 findings). **DIM / ERASE / CLEAR
reworked first** -- its rules stated two wrong things: R-CLEAR-ERRORS said Overflow "past 65535" (it is past 32767:
CLEAR 32768 is 6 -- kerr's ERROR-bound mistake made again) and R-CLEAR-SIZE said "moving the top keeps the size" (its
own FX 33 sets n). kdim.py gained group FY (27 cases: CLEAR's bound and argument order, a top that leaves no room, the
string space and arrays sharing memory, CLEAR in a GOSUB, two arrays that do not fit, A# = A, two significant
characters, the 65535-byte edge for 2-, 4- and 3-byte elements, DIM's bound edge, bound 10 in every dimension and
after ERASE, a negative subscript (5, not 9 -- the one law not predicted), the wrong subscript count, a fractional
bound). zerobas agrees on all 27. The small BASIC now keys arrays by two characters and the TYPE, and counts ONE
memory budget (the string space plus every array). 14 controls, every rule pinned.
