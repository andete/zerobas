# zerobas roadmap

What is still missing, split into the two delivery phases plus a deferred
transport track. See [`README.md`](README.md) for the current status and
[`PROVENANCE.md`](PROVENANCE.md) for the traceability rules every item below
must honour (allowed sources only; no disassembly).

## Status today

Working: byte-identical tokeniser (keywords, integer / `&H` constants,
`= + - * < >`), stored numbered-line programs (insert / replace / delete,
`NEW`, `RUN`), control flow (`GOTO`, `GOSUB`/`RETURN`, `FOR`/`NEXT`,
`IF`/`THEN`/`ELSE`, `END`/`STOP`), `DATA`/`READ`/`RESTORE`, comparisons,
`POKE`/`PEEK`, single-letter 16-bit integer variables, and cassette
`BLOAD"CAS:",R`.

Two reserved-but-unimplemented tokens to note: **`PRINT`**
([src/interp.asm](src/interp.asm), kwtable) and **`ON`**
([src/sysvars.inc](src/sysvars.inc)) both crunch but have no executor — they
die with `syntax error` at run time.

## Phase 1 — enough BASIC to boot loader stubs

The boot transport is already done: cassette `BLOAD"CAS:",R`, or a stored
program that pokes and jumps. What remains is the *language* a loader stub uses
around that `BLOAD` (typical shape: `CLEAR …,&Hxxxx : SCREEN n : BLOAD"…",R`
or `DEFUSR=&Hxxxx : BLOAD"…",R : A=USR(0)`).

Suggested order: `CLEAR` → `DEF USR`/`USR` → multi-char vars → `PRINT` →
`/` + `AND`/`OR` → `ON GOTO` → screen-setup verbs → `LIST`.

### Statements
- [ ] `CLEAR [strings][,himem]` — nearly every stub sets memory top before `BLOAD`
- [ ] `DEF USR[n]=addr` + `USR[n](x)` function — the non-`,R` jump into loaded code
- [ ] `PRINT` (+ `;` `,` separators, string literals, `TAB`) — wire up the existing token
- [ ] `ON expr GOTO/GOSUB` — token exists; needs a handler + a branch-target list in `branch_lineno`
- [ ] `SCREEN`, `COLOR`, `CLS`, `KEY OFF`, `WIDTH` — pre-handoff screen setup (thin BIOS/VDP wrappers)

### Expressions / variables
- [ ] Multi-character variable names — single-letter only is a hard wall
- [ ] `/`, `\`, `MOD`, and `AND`/`OR`/`NOT`/`XOR` — address / poke math
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
- [ ] **Editor / program management** — full `LIST`, `DELETE`, `RENUM`, `AUTO`,
      `TRON`/`TROFF`, `SWAP`, `WAIT`, `ERASE`, `FRE`, full `CLEAR` semantics

## Deferred track — disk transport

Not Phase 1 or 2: the device half is a disk-interface ROM (`PHYDIO` / the
`H.*` hooks), a whole separate project on the [cbios-tape](https://github.com/andete/cbios-tape)
model — kept a separate tree, combined only at runtime. The interpreter side is
small once that ROM exists: disk-filename parsing in `BLOAD`/`LOAD`, `RUN"file"`,
the BSAVE-header read, and the `,R` handoff — all mirroring
[src/bload.asm](src/bload.asm).
