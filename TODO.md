# zerobas roadmap

zerobas is a **clean-room, game-loader-scoped MSX1 BASIC** plus its two storage
transports (cassette + disk), combined with an open BIOS (C-BIOS) only at runtime.
See [`README.md`](README.md) for the charter and the legal/provenance firewall,
[`PROVENANCE.md`](PROVENANCE.md) for the traceability rules every item below must
honour (allowed sources only; no disassembly), and
[`docs/dev-workflow.md`](docs/dev-workflow.md) for how to implement + validate one
item — do **one item per session** to keep context lean.

## Target — committed scope

The charter (README) is deliberate: *just enough MSX-BASIC to run the `.BAS` /
binary loader stubs that boot disk and tape games — **not** full-language
compatibility.* The committed target is therefore:

1. **Phase 1 — loader-stub BASIC** — ✅ done.
2. **Disk transport** (read + write) — ✅ done (`disk.rom`; see [`disk/TODO.md`](disk/TODO.md)).
3. **Tape transport** (read + write) — device signal layer ✅ done; **interpreter
   parity is the one remaining committed track** (below).

**Full MSX1 BASIC (Phase 2) is an aspirational appendix, NOT in the committed
target** — listed at the end of this file for reference only.

## Status today — three components, two axes

zerobas is three separately-built artifacts, combined only at runtime: `basic/` →
`basic.rom` (cartridge, slot 0 page 1); `tape/` → the zerobas-tape IPS patch
(C-BIOS page 0 cassette signal layer); `disk/` → `disk.rom` (slot 3-1).

| | Device / transport layer | Interpreter statements (basic.rom) |
|---|---|---|
| **Tape** | ✅ read **and** write signal layer (MSX1/2/2+) | ⚠️ `BLOAD"CAS:",R` works; `CLOAD`/`LOAD"CAS:"` oracle-validated but on-device load blocked by a zerobas-tape `$00`-run framing bug; **no tape SAVE** yet |
| **Disk** | ✅ DSKIO + FAT12 + BDOS, read **and** write (differential vs CF-3300 & MSX-DOS 1) | ✅ `BLOAD`/`LOAD`/`RUN`/`SAVE`/`BSAVE` for `"A:"` |

Language (Phase 1, done): byte-identical tokeniser (keywords, integer / `&H` /
`&O` constants, `= + - * / \ < >`, `MOD`/`AND`/`OR`/`XOR`/`NOT`), stored
numbered-line programs (`NEW`/`RUN`/edit), control flow (`GOTO`, `GOSUB`/`RETURN`,
`FOR`/`NEXT`, `IF`/`THEN`/`ELSE`, `ON … GOTO`/`GOSUB`, `END`/`STOP`, `CONT` +
Ctrl-STOP), `DATA`/`READ`/`RESTORE`, `POKE`/`PEEK`, `PRINT`, `CLEAR`,
`DEF USR`/`USR`, screen-setup verbs (`SCREEN`/`COLOR`/`CLS`/`WIDTH`/`KEY`),
`LIST`, the memory/I-O primitives (`VPOKE`/`VPEEK`, `OUT`/`INP`, `VARPTR`),
multi-character 16-bit integer vars, minimal string vars for `PRINT`, and the
storage statements above.

## Remaining — committed work to reach the target

### Tape — read + write parity with disk
- [ ] **`CLOAD` / `LOAD"CAS:"` on-device load** — the interpreter half is done and
      oracle-validated (the reference VG-8020 loads our synthetic `.cas` to the exact
      expected image), but on real hardware the device-half `TAPIN` hangs on the
      all-zero `$0000` end-link: a zerobas-tape **`$00`-run framing** limitation.
      Fix it in [`tape/`](tape/) (the cassette signal layer) so cassette
      program-load completes on-device. This is the last gap in tape *read*.
- [ ] **Tape SAVE statements** — `CSAVE` / `SAVE"CAS:"` (tokenised program) and
      `BSAVE"CAS:",start,end[,exec]` (binary) to cassette, using the zerobas-tape
      **write** signal layer (`TAPOON`/`TAPOUT`/`TAPOOF`, already implemented) + the
      cassette file format (`$D3`/`$D0` header block + 6-char name + data). The
      existing disk `do_save`/`do_bsave` ([`basic/save.asm`](basic/save.asm))
      descope `"CAS:"` to `load_error` — extend them to route the tape device to the
      cassette write path. Oracle: a saved tape image reads back byte-identical on
      the reference, and round-trips through our own `CLOAD`/`BLOAD` once the framing
      fix above lands. This is tape *write* (mirrors what disk `SAVE`/`BSAVE` did).

### Phase 1 close-out — owed oracles (polish, non-blocking)
- [ ] `basic_probe_clear.py` — the `CLEAR` oracle is still owed.
- [ ] `USR` `DAC`/`VALTYP` calling-convention oracle follow-up (`USR` is own-design
      integer-only; the reference's DAC/VALTYP convention was never differenced).

Everything else for the committed target is done; the detailed done-record follows.

## Done — Phase 1 (loader-stub BASIC)

Complete and oracle-validated; kept below as the provenance / divergence record
(each item names where it lives and how it was validated). The typical loader
stub this supports: `CLEAR …,&Hxxxx : SCREEN n : BLOAD"…",R` or
`DEFUSR=&Hxxxx : BLOAD"…",R : A=USR(0)`.

### Statements
- [x] `CLEAR [strings][,himem]` — nearly every stub sets memory top before `BLOAD`
      (basic/clear.asm: full syntax parses; string-space accepted+ignored, himem
      recorded to HIMEM `$FC4A`. Oracle `basic_probe_clear.py` still owed.)
- [x] `DEF USR[n]=addr` + `USR[n](x)` function — the non-`,R` jump into loaded code
      (basic/usr.asm: vectors in USRTAB `$F39A`; crunch byte-identical. USR calling
      convention is own-design integer-only — DAC/VALTYP convention oracle follow-up owed.)
- [x] `CLOAD ["filename"]` — load a BASIC program from cassette; needed when a stub
      chain-loads a BASIC payload rather than a binary (complement to `BLOAD"CAS:"`)
      (basic/cload.asm: CLOAD=$9B / LOAD=$B5 crunch byte-identical; reads the $D3
      tokenised-BASIC tape image into the stored-program area at TXTBASE, relinks,
      makes it the current program. Optional filename parsed+ignored — own-design,
      no tape file catalogue. Functional load BLOCKED in-harness by a zerobas-tape
      `$00`-run framing limitation (every program ends in the all-zero $0000 end-link
      and the device-half TAPIN hangs on it); format+result oracle-validated — the
      reference VG-8020 loads our synthetic .cas to the exact expected image.)
- [x] `LOAD "CAS:filename"` — MSX-BASIC unified tape-load form; shares cassette I/O
      path with `CLOAD` but uses the `OPEN`-style filename syntax
      (same basic/cload.asm path as CLOAD; LOAD=$B5, "CAS:" device parsed, filename
      ignored. Same zerobas-tape `$00`-run device-half blocker as CLOAD.)
- [x] `PRINT` (+ `;` `,` separators, string literals, `TAB`) — wire up the existing token
      (basic/print.asm: numeric + string-literal items, `;`/`,` zones, `?` abbrev;
      crunch byte-identical, output verified in openMSX. `TAB(`/`SPC(` + string
      vars/`CHR$` still to do — need the Phase-2 string engine.)
- [x] `ON expr GOTO/GOSUB` — `branch_lineno` extended with comma-list loop; `ex_on`/`eon_seek_nth` handler added; all 7 functional probes (A=1..N, N=0 fallthrough, N>count fallthrough) pass
- [x] `SCREEN`, `COLOR`, `CLS`, `KEY OFF`, `WIDTH` — pre-handoff screen setup (thin BIOS/VDP wrappers)
      (basic/screen.asm: thin wrappers over CHGMOD/CHGCLR/CLS/ERAFNK/DSPFNK; new `OFF`
      token $EB added; crunch byte-identical incl. all 7 verbs; 9/9 functional probes
      pass `basic_probe_screen.py`. Divergences: SCREEN's extra args evaluated+ignored;
      COLOR doesn't repaint drawn text; KEY only does OFF/ON, `KEY n,"str"`/`KEY LIST`
      error — all Phase-2 scope.)

### Expressions / variables
- [x] Multi-character variable names — single-letter only is a hard wall
      (basic/vars.asm: 2 significant chars, key store; crunch byte-identical incl.
      digit-in-name; 2-char round-trip verified in openMSX)
- [x] `/`, `\`, `MOD`, and `AND`/`OR`/`NOT`/`XOR` — address / poke math
      (basic/expr.asm: full precedence ladder; crunch byte-identical, all ops verified
      in openMSX. `/` is integer + division is unsigned — documented divergences from
      MSX signed/float arithmetic; div-by-zero → 0. `^` still deferred to Phase 2.)
- [x] `&O` / `&B` literals — `&O` octal now emitted + evaluated; `&B` descoped
      (basic/interp.asm: `tk_hex` generalised to dispatch `&H`/`&O` on a radix
      (16/8) + token ($0C/$0B) pair; `&O` crunches byte-identical to the VG-8020
      as `$0B,<value16 LE>`, full `0..&HFFFF`; `ev_f` decodes `$0B` like `$0C`;
      `detok` already rendered `&O`. Oracle showed the reference has NO `&B`
      binary token — it copies `&B…` verbatim as ASCII — so `&B` is a documented
      own-design descope (kept verbatim, byte-identical to the reference; marked
      quarantined in basic/PROVENANCE.md), not a fabricated token. Validated:
      crunch + 4 control-flow/loops/data/statements regressions ALL PASS;
      functional `&o17`→15, `&o12`→10, `&o400`→256, `&o177777`→65535 in openMSX.)
- [x] `VARPTR`, `VPOKE`/`VPEEK`/`BASE`, `INP`/`OUT` — common in pokes
      (basic/vdpio.asm: VPOKE/OUT statement handlers; basic/expr.asm: VPEEK/INP/
      VARPTR/BASE function factors. Tokens oracle-confirmed byte-identical via
      basic_probe_crunch.py: VPOKE=$C6, OUT=$9C, VPEEK=$FF$98, INP=$FF$90,
      VARPTR=$E7, BASE=$C9 (cross-checks MSX2 TH Table 2.20). VPOKE/VPEEK use
      WRTVRM $004D / RDVRM $004A; OUT/INP do raw Z80 `out (c),a` / `in a,(c)`.
      detok renders all six (table-driven, no new render code). Functional
      `basic_probe_vdpio.py` 6/6 PASS. Divergences: VARPTR returns zerobas's OWN
      variable-table value-cell address (its table layout is its own design, not
      the reference's variable-area map) — valid+writable, sufficient for loader
      pokes; BASE is descoped — argument parsed+evaluated but BASE(n) returns 0
      and sets ERRMARK (reproducing the reference's per-mode VDP table-base map
      would need a forbidden source). Both quarantined in basic/PROVENANCE.md.)
- [x] String literals / variables *enough for `PRINT`* (full string engine is Phase 2)
      (basic/strvar.asm + basic/vars.asm: a `$`-suffixed name is a string variable
      with its own minimal inline store [name0][name1][len][bytes:STRMAX=32]; LET
      assigns a `"literal"` or copies another string var (A$=B$); PRINT emits a
      string var's value, incl. alongside literals (PRINT "X=";A$). Oracle-confirmed
      `$` is part of the name — NO special string token; crunch already byte-identical
      (`a$="hi"` → `41 24 EF 22 68 69 22`). Own-design VALTYP/STRPTR value-type notion.
      6/6 functional probes pass basic_probe_strvar.py. NOT built (Phase 2): concat `+`,
      string functions (LEN/MID$/CHR$/…), string arrays/DIM, string DATA — all descoped.)

### Usability
- [x] `LIST` — display the stored program, de-tokenised
      (basic/list.asm: `ex_list` walks the line-link chain; `detok` is the reverse
      of the tokeniser — keyword (`detok_kw`/`detok_kw2`), operator, int/`&H`/`&O`,
      line-ref, string/REM/DATA verbatim, `:`ELSE / `'` folds. No new token; reuses
      `div10`/CHPUT. 8/8 functional probes pass `basic_probe_list.py` (VRAM screen
      decode); crunch + all regression probes still pass. Divergence: only the
      no-arg whole-program form — `LIST n` / `LIST n-m` range args are Phase 2,
      a trailing argument is parsed-past + ignored.)
- [x] `CONT`, Ctrl-STOP / break handling
      (basic/program.asm: the RUN loop polls BIOS `BREAKX` ($00B7) between
      statements/lines and on every FOR/NEXT iteration; a press branches to
      `do_break`, which saves the resume state and prints `break in <line>`. The
      `STOP` statement (`ex_stop`) records resume = the statement after STOP, then
      `do_break`; `CONT` (`ex_cont`) restores `CURLINE`/`RESUMEPTR` and re-enters
      the run loop via the existing `RESUMEFLAG` mid-line resume path. `CONTVALID`
      is cleared at RUN entry, on `store_line` (edit), and on `NEW`, so CONT after
      a clean/STOP-less completion or an edit gives `can't continue` (ERRMARK $C9).
      CONT token oracle-confirmed byte-identical via basic_probe_crunch.py
      (`cont`→$99, cross-checks MSX2 TH Table 2.20); BREAKX oracle-confirmed on
      C-BIOS_MSX1 (bios_probe_breakx.py — CF clear when not pressed, so no
      false-breaks). Functional `basic_probe_cont.py` 7/7 PASS on C-BIOS_MSX1:
      STOP halts, STOP→CONT resumes incl. across a line boundary, all three
      can't-continue cases, and a real Ctrl-STOP keyboard-matrix press breaking an
      infinite loop back to the REPL. Divergences: the resume-state RAM layout
      (CONTLINE/CONTPTR/CONTVALID) and lowercase `break in`/`can't continue`
      wording are own-design — zerobas's run loop is its own design, not the
      reference's CONTXT/OLDLIN sysvars — both quarantined in basic/PROVENANCE.md.)

## Aspirational appendix — full MSX1 BASIC (NOT in the committed target)

Beyond the README charter (loader-stub scope) — listed for reference and to mark
where the natural boundaries are, **not** planned/committed work. If the charter is
ever raised, this becomes the plan; until then these items are explicitly out of
scope. (Note: tape/disk file I/O — `SAVE`/`LOAD`/`CSAVE`/`CLOAD`/`BSAVE` — has been
pulled forward into the committed transport tracks above; the `OPEN`/`CLOSE`/
`PRINT#`/`INPUT#` random-access file layer stays here.)

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

## Done — storage transports

### Disk (`disk/` → `disk.rom`, slot 3-1) — complete, read **and** write
The full FDC + FAT12 + BDOS stack, both directions, each layer
differential-confirmed against real hardware/software (strictly black-box, no
disassembly): WD2793 physical sector read **and** write vs the **National
CF-3300**, and the FCB BDOS file read **and** write (Open/SeqRead/Close +
Create/SeqWrite/Close, on a FAT12 read+write-back layer) vs real **MSX-DOS 1**.
The interpreter side lives in `basic/`: `BLOAD`/`LOAD`/`RUN`/`SAVE`/`BSAVE` for
`"A:"`, the `init_ext_roms` slot-scan ([`basic/initext.asm`](basic/initext.asm))
that boots the disk ROM, and the cross-slot BDOS calls. See
[`disk/TODO.md`](disk/TODO.md) and [`disk/PROVENANCE.md`](disk/PROVENANCE.md) for
the per-item record and the documented divergences (FCB bookkeeping fields,
directory timestamps, the intentional GETDPB stub).

### Tape (`tape/` → zerobas-tape IPS patch) — device layer complete, read **and** write
The cassette signal layer C-BIOS lacks: `TAPION`/`TAPIN`/`TAPIOF` (read) and
`TAPOON`/`TAPOUT`/`TAPOOF` (write) — FSK leader detect + auto-baud + byte framing
and the write waveform, at 1200 and 2400 baud, round-trip validated on MSX1 /
MSX2 / MSX2+. See [`tape/DESIGN.md`](tape/DESIGN.md) and
[`tape/PROVENANCE.md`](tape/PROVENANCE.md). The **interpreter** side is not yet at
parity — `BLOAD"CAS:",R` works; the two remaining committed items (the `CLOAD`
on-device `$00`-run framing fix and tape `SAVE`) are in the **Remaining** section
near the top of this file.
