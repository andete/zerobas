# zerobas roadmap

What is still missing, split into the two delivery phases plus a deferred
transport track. See [`README.md`](README.md) for the current status,
[`PROVENANCE.md`](PROVENANCE.md) for the traceability rules every item below
must honour (allowed sources only; no disassembly), and
[`docs/dev-workflow.md`](docs/dev-workflow.md) for how to implement and validate
one item — do **one item per session** to keep context lean.

## Status today

Working: byte-identical tokeniser (keywords, integer / `&H` constants,
`= + - * < >`), stored numbered-line programs (insert / replace / delete,
`NEW`, `RUN`), control flow (`GOTO`, `GOSUB`/`RETURN`, `FOR`/`NEXT`,
`IF`/`THEN`/`ELSE`, `END`/`STOP`), `DATA`/`READ`/`RESTORE`, comparisons,
`POKE`/`PEEK`, single-letter 16-bit integer variables, and cassette
`BLOAD"CAS:",R`.

Two reserved-but-unimplemented tokens to note: **`PRINT`**
([basic/interp.asm](basic/interp.asm), kwtable) and **`ON`**
([basic/sysvars.inc](basic/sysvars.inc)) both crunch but have no executor — they
die with `syntax error` at run time.

## Phase 1 — enough BASIC to boot loader stubs

The boot transport is already done: cassette `BLOAD"CAS:",R`, or a stored
program that pokes and jumps. What remains is the *language* a loader stub uses
around that `BLOAD` (typical shape: `CLEAR …,&Hxxxx : SCREEN n : BLOAD"…",R`
or `DEFUSR=&Hxxxx : BLOAD"…",R : A=USR(0)`).

Suggested order: `CLEAR` → `DEF USR`/`USR` → multi-char vars → `PRINT` →
`/` + `AND`/`OR` → `ON GOTO` → screen-setup verbs → `LIST`.

### Statements
- [x] `CLEAR [strings][,himem]` — nearly every stub sets memory top before `BLOAD`
      (basic/clear.asm: full syntax parses; string-space accepted+ignored, himem
      recorded to HIMEM `$FC4A`. Oracle `basic_probe_clear.py` still owed.)
- [x] `DEF USR[n]=addr` + `USR[n](x)` function — the non-`,R` jump into loaded code
      (basic/usr.asm: vectors in USRTAB `$F39A`; crunch byte-identical. USR calling
      convention is own-design integer-only — DAC/VALTYP convention oracle follow-up owed.)
- [ ] `CLOAD ["filename"]` — load a BASIC program from cassette; needed when a stub
      chain-loads a BASIC payload rather than a binary (complement to `BLOAD"CAS:"`)
- [ ] `LOAD "CAS:filename"` — MSX-BASIC unified tape-load form; shares cassette I/O
      path with `CLOAD` but uses the `OPEN`-style filename syntax
- [x] `PRINT` (+ `;` `,` separators, string literals, `TAB`) — wire up the existing token
      (basic/print.asm: numeric + string-literal items, `;`/`,` zones, `?` abbrev;
      crunch byte-identical, output verified in openMSX. `TAB(`/`SPC(` + string
      vars/`CHR$` still to do — need the Phase-2 string engine.)
- [ ] `ON expr GOTO/GOSUB` — token exists; needs a handler + a branch-target list in `branch_lineno`
- [ ] `SCREEN`, `COLOR`, `CLS`, `KEY OFF`, `WIDTH` — pre-handoff screen setup (thin BIOS/VDP wrappers)

### Expressions / variables
- [x] Multi-character variable names — single-letter only is a hard wall
      (basic/vars.asm: 2 significant chars, key store; crunch byte-identical incl.
      digit-in-name; 2-char round-trip verified in openMSX)
- [x] `/`, `\`, `MOD`, and `AND`/`OR`/`NOT`/`XOR` — address / poke math
      (basic/expr.asm: full precedence ladder; crunch byte-identical, all ops verified
      in openMSX. `/` is integer + division is unsigned — documented divergences from
      MSX signed/float arithmetic; div-by-zero → 0. `^` still deferred to Phase 2.)
- [ ] `&O` / `&B` literals — tokens reserved, not yet emitted
- [ ] `VARPTR`, `VPOKE`/`VPEEK`/`BASE`, `INP`/`OUT` — common in pokes
- [ ] String literals / variables *enough for `PRINT`* (full string engine is Phase 2)

### Usability
- [ ] `LIST` — no way to view a stored program today
- [ ] `CONT`, Ctrl-STOP / break handling

## Phase 2 — complete MSX1 BASIC

- [ ] **Floating point** — the math pack, `!`/`#`/`%` type suffixes,
      `DEFINT`/`DEFSNG`/`DEFDBL`/`DEFSTR`, and the float crunch tokens
      (decimal ≥ 32768 etc.) currently out of scope
- [ ] **Full string engine** — string variables + heap, `+` concat,
      `LEN MID$ LEFT$ RIGHT$ INSTR STR$ VAL CHR$ ASC HEX$ OCT$ STRING$ SPACE$ INKEY$`
- [ ] **Arrays + `DIM`** (numeric and string, multi-dimensional)
- [ ] **`^`** and the math functions
      `ABS SGN INT SQR SIN COS TAN ATN LOG EXP RND FIX CINT CSNG CDBL`
- [ ] **I/O** — `INPUT`, `LINE INPUT`, `INPUT$`, `PRINT USING`; file I/O
      (`OPEN CLOSE PRINT# INPUT# GET PUT EOF LOF LOC`, `MAXFILES`); full tape
      verbs (`SAVE LOAD CSAVE CLOAD MERGE BSAVE`, `MOTOR`)
- [ ] **Graphics** (TMS9918) — `SCREEN 0–3`, `LINE`, `PSET`/`PRESET`,
      `CIRCLE`, `PAINT`, `DRAW`, sprites (`GET`/`PUT`, `SPRITE$`), `VDP`
- [ ] **Sound** (AY-3-8910) — `SOUND`, `PLAY` (MML), `BEEP`
- [ ] **Input devices** — `STICK STRIG PAD PDL`, `KEY(n)`, `STRIG(n) ON/OFF/STOP`
- [ ] **Error handling** — `ON ERROR GOTO`, `RESUME`, `ERR`/`ERL`, `ERROR n`,
      numbered error messages
- [ ] **Interrupt traps** — `ON INTERVAL/KEY/SPRITE/STOP GOSUB`
- [ ] **Screen-editor REPL** — real MSX BASIC does not use a sequential prompt
      loop; Enter reads the *current cursor line from VRAM* (not a dedicated
      input buffer), so the user can cursor-up to any visible output, edit it
      in place, and re-enter it. Needs cursor-key handling and VDP line-readback.
      Our `repl.asm` is a deliberate simplification; full replacement is Phase 2.
- [ ] **Editor / program management** — full `LIST`, `DELETE`, `RENUM`, `AUTO`,
      `TRON`/`TROFF`, `SWAP`, `WAIT`, `ERASE`, `FRE`, full `CLEAR` semantics

## Deferred track — disk transport

Not Phase 1 or 2. See [`disk/TODO.md`](disk/TODO.md) for the full plan and
status. The interpreter-side items (disk-filename parsing in `BLOAD`/`LOAD`,
`RUN"file"`, BSAVE-header read, `,R` handoff) are small once the
[`disk/`](disk/) ROM's BDOS API is stable — they mirror
[`basic/bload.asm`](basic/bload.asm).
