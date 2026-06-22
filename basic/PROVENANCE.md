# Provenance log — zerobas BASIC

Every constant, address, data table, and algorithm in the zerobas BASIC
interpreter must appear here with an independent **allowed** source, or be
explicitly **quarantined**. An unexplained magic value blocks release.

- **sourced** — traced to an allowed source (see [`../README.md`](../README.md) for the list).
- **quarantined** — no allowed source found; derived from spec or stubbed,
  **never copied** from a reference ROM or any MSX-BASIC / GW-BASIC disassembly.

The behavioural source `spec-bload-r.md` is this project's own black-box oracle
observation, captured in the `msx-preservation` repo
(`basic-spec/docs/spec-bload-r.md`).

## first light: `BLOAD"CAS:",R` (basic/main.asm, basic/bload.asm, basic/sysvars.inc)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Cartridge ROM header layout (`AB`, INIT, STATEMENT, DEVICE, TEXT, 6 reserved) | 16 bytes at $4000 | MSX2 Technical Handbook, cartridge ROM format | sourced |
| ROM page span | $4000–$7FFF (16 KB) | MSX2 Technical Handbook, memory map | sourced |
| TAPION entry point | $00E1 | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| TAPIN entry point | $00E4 | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| TAPIOF entry point | $00E7 | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| TAPION/TAPIN failure convention | CF set = fail | MSX Assembly Page BIOS call list | sourced |
| TAPIN trashes all registers | — | MSX Assembly Page BIOS call list ("Changes: all") | sourced |
| Binary-file id byte | $D0 | MSX2 Technical Handbook, BSAVE file format | sourced |
| File-header block size | 16 bytes (10× id + 6 filename) | spec-bload-r.md §1 (oracle) + MSX2 Tech Handbook | sourced |
| Data-header layout | start(LE), end(LE), exec(LE) | spec-bload-r.md §1 (oracle) + MSX2 Tech Handbook | sourced |
| Load is verbatim into start..end | — | spec-bload-r.md §2 (oracle) | sourced |
| `,R` handoff = jump to exec address | — | spec-bload-r.md §3 (oracle) | sourced |
| Two tape header tones (one per block ⇒ two TAPION calls) | — | spec-bload-r.md §1 (.cas block layout) + oracle-confirmed (probe PASS on VG-8020) | sourced |
| RAM scratch addresses ($E020–$E025), error marker ($E010) | — | own choice (free page-3 RAM, avoids demo regions) | sourced |

No quarantined items.

## tokeniser + executor (basic/interp.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `BLOAD` keyword token | $CF | spec-tokenise.md (oracle KBUF dump); cross-checks MSX Assembly Page token table | sourced |
| Keywords crunch to one token byte, case-folded | — | spec-tokenise.md §1–2 (oracle) | sourced |
| Non-keyword bytes (strings, punctuation, options) kept verbatim | — | spec-tokenise.md §3 (oracle) | sourced |
| Crunched-line terminator | $00 | spec-tokenise.md §4 (oracle) | sourced |
| Leading spaces skipped at execution | — | spec-tokenise.md §5 (oracle) | sourced |
| `'a'`..`'z'` → uppercase via `− $20` (upcase) | — | ASCII (public) | sourced |
| `RUNFLAG` ($E02F), `TOKBUF` ($E030) | — | own choice (free page-3 RAM) | sourced |

No quarantined items. Note: this documents the original BLOAD-only build, whose
keyword table held a single entry (`BLOAD`→$CF). The "non-keyword bytes kept
verbatim" row above is **superseded by Step A** for numbers and operators (they
now crunch to real tokens) — see the *Step A* section below; string literals and
the `REM`/`'` comment tail are still copied verbatim.

## startup header (basic/title.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| INITXT entry point | $006C | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| CHPUT entry point | $00A2 | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| Header text ("zerobas version 0.1 / clean-room MSX-BASIC program loader") | — | **own content** (project branding). Same *role* as MSX-BASIC's top-of-screen header before its prompt; **no** reference header text copied (that would be a clean-room violation and a false copyright claim) | sourced |
| CR/LF control codes ($0D/$0A) for CHPUT | — | ASCII / MSX2 Tech Handbook (console control codes) | sourced |

No quarantined items.

## REPL / keyboard line editor (basic/repl.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| CHGET entry point | $009F | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| `EI` before keyboard input | — | the keyboard ISR must run for CHGET; standard MSX practice (MSX2 Tech Handbook) | sourced |
| Backspace / Enter codes ($08 / $0D) | — | ASCII / MSX2 Tech Handbook (console codes) | sourced |
| Line editor + read/eval loop algorithm | — | **own code** (original); not derived from any disassembly | sourced |
| Prompt text "zb>" | — | **own content**, deliberately unlike MSX-BASIC's "Ok" | sourced |
| Error text "syntax error" / "load error" | — | own wording (plain English; not copied) | sourced |
| `LINEBUF`, `LINEMAX` | — | own choice (free page-3 RAM) | sourced |

No quarantined items.

## REM / POKE / PEEK statement slice

Behavioural source: `basic-spec/docs/spec-tokens-statements.md` (this project's
own black-box oracle observation) and the public MSX-BASIC *language* reference.

### Keyword tokens (basic/sysvars.inc, basic/interp.asm `kwtable`)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `POKE` token | `$98` | spec-tokens-statements.md (oracle KBUF dump); cross-checks MSX Assembly Page token table | sourced |
| `PEEK` token | `$FF $97` (two-byte function token) | spec-tokens-statements.md (oracle); MSX Assembly Page token table | sourced |
| `REM` token | `$8F` | spec-tokens-statements.md (oracle); MSX Assembly Page token table | sourced |
| `'` treated as REM (emit `$8F`, copy rest verbatim) | — | spec-tokens-statements.md (oracle: `'` → `$3A $8F $E6`); zerobas simplifies to the REM token (own design) | sourced |
| REM/`'` keep the rest of the line verbatim | — | spec-tokens-statements.md §2 (oracle) | sourced |
| Multi-byte token table entry layout `[klen][chars][tlen][tokens]` | — | own code (generalises the single-byte table for `PEEK`) | sourced |

### Statement loop, dispatch, assignment (basic/interp.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `:` statement separator (`$3A`); per-statement dispatch loop | — | own code; `:` is ASCII (public) and the documented MSX-BASIC separator (language reference) | sourced |
| `<letter> = <expr>` assignment | — | own code; assignment semantics from the public MSX-BASIC language reference | sourced |
| `is_letter` (`'A'`..`'Z'` test) | — | ASCII (public) | sourced |

### Expression evaluator (basic/expr.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| 16-bit integer grammar (`+ - *`, unary `-`, parens, `PEEK`, integer & `&H` constants, variables) | — | **own code** (precedence-climbing); not derived from any disassembly | sourced |
| Evaluator **decodes the crunched tokens** (constant tokens carry binary value; operator tokens drive precedence) — see Step A below | — | own code; the token bytes it decodes are oracle-sourced (spec-tokens-statements.md §3/§4) | sourced |
| `PEEK(addr)` reads one byte; `POKE addr,value` writes the low byte | — | public MSX-BASIC language reference | sourced |
| `mul16` shift-add | — | standard binary arithmetic (public) | sourced |

### Step A: byte-identical crunch + token-decoding (basic/interp.asm, basic/expr.asm, basic/sysvars.inc)

Earlier slices kept numbers/operators verbatim; that is **reversed** here so a
crunched line is byte-for-byte identical to a real ROM's. Behavioural source:
`basic-spec/docs/spec-tokens-statements.md §3/§4` (this project's own black-box
oracle observation — the fidelity sweep). Verified by `basic_probe_crunch.py`
(zerobas `TOKBUF` == reference `KBUF`, per line).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Digit constant tokens `0`–`9` | `$11 + n` | spec-tokens-statements.md §3 (oracle); MSX Assembly Page token table | sourced |
| One-byte int constant (`10`–`255`) | `$0F`, value | spec-tokens-statements.md §3 (oracle) | sourced |
| Two-byte int constant (`256`–`32767`) | `$1C`, value LE | spec-tokens-statements.md §3 (oracle) | sourced |
| `&H` hex constant | `$0C`, value16 LE | spec-tokens-statements.md §3 (oracle) | sourced |
| Operator tokens `= + - *` | `$EF $F1 $F2 $F3` | spec-tokens-statements.md §4 (oracle) | sourced |
| `'` crunch (now byte-exact) | `$3A $8F $E6` | spec-tokens-statements.md §3 (oracle) | sourced |
| Letters upcased outside string literals (vars + options) | — | spec-tokens-statements.md §4 (oracle: `a`→`A`, `,r`→`,R`; strings preserved) | sourced |
| `(` `)` `,` `:` and space kept verbatim | `$28 $29 $2C $3A $20` | spec-tokens-statements.md §4 (oracle) | sourced |
| Tokeniser constant/operator crunch + evaluator token-decode algorithm | — | **own code** (reproduces the observed output); not derived from any disassembly | sourced |
| Out of scope (not emitted): `&O`/`&B`, float (decimal `≥ 32768`), line-number-reference tokens | — | recorded in spec-tokens-statements.md as observed-but-deferred | sourced |

## Phase 1: CLEAR statement (basic/clear.asm, basic/sysvars.inc, basic/interp.asm)

Behavioural source: the public MSX-BASIC *language* reference (CLEAR sets the
string-space size and the highest address BASIC may use). The token byte and the
HIMEM sysvar are documented-source-first (same provenance model as the Step B
keyword set). Oracle: `basic_probe_clear.py` (msx-preservation) differences
zerobas against the Philips VG-8020 reference and confirms that after
`CLEAR 200,&HD000` both store `$D000` (LE) in HIMEM (`$FC4A`) — proving `$FC4A`
is CLEAR's memory-top home on the reference and that zerobas matches it. All
four syntax forms (`CLEAR`, `CLEAR n`, `CLEAR ,himem`, `CLEAR n,himem`) parse
without error and the line continues. zerobas does not maintain the
string-heap sysvars (STKTOP/FRETOP/STREND) — it has no heap in Phase 1 — so
only the HIMEM observable is asserted; nothing here invents expected oracle
bytes. ALL PASS.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `CLEAR` keyword token | `$92` | MSX2 Technical Handbook, Table 2.20 (cross-checks MSX Assembly Page token table; spec-controlflow.md §1) | sourced |
| `HIMEM` sysvar (CLEAR's memory-top ceiling) | `$FC4A` | C-BIOS system variables (BSD 2-clause); cross-checked against MSX2 Technical Handbook work-area appendix / MSX Assembly Page | sourced |
| `CLEAR …,&HD000` writes `$D000` (LE) to HIMEM `$FC4A`, byte-identical to the Philips VG-8020 | `00 D0` @ `$FC4A` | `basic_probe_clear.py` differential oracle (Philips VG-8020 vs C-BIOS_MSX1 + cart) | oracle-locked |
| `CLEAR [<strings>][,<himem>]` syntax — both args optional, comma-separated, bare `CLEAR` valid | — | public MSX-BASIC language reference | sourced |
| `<string-space>` arg accepted + evaluated, then ignored (zerobas has no string heap to size) | — | own design (minimal memory model); documented in basic/clear.asm | sourced |
| `<memory-top>` arg stored to HIMEM, record-only (no allocator consults it yet under the fixed RAM layout) | — | own design; HIMEM is the documented home of the value (language reference) | sourced |
| CLEAR parse/dispatch algorithm | — | **own code** (mirrors the do_poke arg-parse pattern); not derived from any disassembly | sourced |

No quarantined items.

## Phase 1: DEF USR / USR + Phase-1 keyword tokens (basic/usr.asm, basic/sysvars.inc, basic/interp.asm)

Token bytes are from the **MSX2 Technical Handbook, Table 2.20** (Konamiman's
transcription — an allowed source; the same table spec-controlflow.md §1 quotes).
Cross-corroboration: the overlaps `DEF=$97`, `PRINT=$91`, `ON=$95`, `GOTO=$89`,
`GOSUB=$8D`, `LIST=$93` agree with values zerobas already oracle-confirmed, and
the new `DEF USR` / `USR` crunch was checked byte-identical against the live
VG-8020 reference via `basic_probe_crunch.py` (`defusr=&h9000`, `defusr0=&h9000`,
`a=usr(0)`, `a=usr1(5)` all PASS). No disassembly consulted.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `DEF` token | `$97` | MSX2 TH Table 2.20 (statement; distinct from PEEK's `$FF $97`) | sourced |
| `USR` token | `$DD` | MSX2 TH Table 2.20 (function / DEF USR target); crunch byte-identical (oracle) | sourced |
| `LIST`/`CLS`/`SCREEN`/`COLOR`/`WIDTH`/`KEY` tokens | `$93`/`$9F`/`$C5`/`$BD`/`$A0`/`$CC` | MSX2 TH Table 2.20 (handlers land in later Phase-1 tasks) | sourced |
| `USRTAB` (10 USR vectors, 2 bytes each) | `$F39A` | C-BIOS system variables (BSD 2-clause) | sourced |
| `DEFUSR[n]=<addr>` / `USR[n](<arg>)` syntax + USR-number 0..9 as a digit token | — | public MSX-BASIC language reference; crunch byte-identical (oracle) | sourced |
| USR calling convention: arg in HL, CALL the routine, HL = result; refuse a `0` (un-DEF'd) vector | — | **own design** (integer-only; no DAC/VALTYP float protocol). Reference convention now oracle-measured (`basic_probe_usr.py`): integer arg in `DAC+2..3` (LE, 8-byte DAC `$F7F6`), `VALTYP $F663 =$02`, `HL`→DAC base — observed black-box, NOT taken from any disassembly | quarantined |
| DEF USR / USR parse + trampoline algorithm | — | **own code**; not derived from any disassembly | sourced |

The USR *calling convention* is the one **quarantined** item so far: zerobas's
integer-only convention is a deliberate own-design stand-in for MSX-BASIC's
DAC/VALTYP argument protocol. The reference protocol is now **measured** (not
assumed) by `basic_probe_usr.py` — a black-box differential against the Philips
VG-8020: a tiny hand-authored stub, installed via `debug write_block` and called
through `DEFUSR0`, snapshots the entry state. With two distinct integer
arguments (`12345=$3039`, `258=$0102`) the reference consistently delivers the
value at `DAC+2..3` (LE word at offset 2 of the 8-byte DAC `$F7F6`), sets
`VALTYP` (`$F663`) `=$02` (integer), and enters with `HL`→DAC base; zerobas
delivers the value directly in `HL` and leaves DAC/VALTYP untouched. This
remains own-design (no byte-level reference source was read — only outputs were
observed) and is sufficient for loader stubs (arg/return usually ignored); the
full DAC/VALTYP protocol is Phase 2.

### Variable store (basic/vars.asm) — Phase 1: multi-character names

Grew from the single-letter A..Z store to multi-character names. Behavioural
source: the public MSX-BASIC *language* reference (numeric variable, 2 significant
characters, auto-init to 0). The digit-in-name and mid-name keyword crunch rules
were oracle-checked byte-identical against the VG-8020 (`a1`, `sc`, `ab9`, `x2`,
`x2=x2+1` PASS; `score` → `SC,OR,E` once `OR` is a known keyword), and a 2-char
round-trip (`AB`/`AC` distinct) was verified functionally in openMSX.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Variable name significant to 2 characters, value default 0 | — | public MSX-BASIC language reference | sourced |
| Table layout: 4-byte entries `[name0][name1][value:2]`, first-free allocation, 0 name0 = empty | — | **own code / own choice** (table layout is ours) | sourced |
| Tokeniser rule: a digit keeps its ASCII byte iff the previous char was part of a name (else it crunches to a number token); reserved words still match at every position (`SCORE`→`SC OR E`) | — | own code reproducing the **oracle**-observed crunch (`basic_probe_crunch.py`); not from any disassembly | sourced |
| `TKNAME` in-name flag | `$E028` | own choice (free page-3 RAM) | sourced |
| `VARTAB`/`VAREND` (32 slots × 4 bytes, $E1C0..$E23F) | — | own choice (free page-3 RAM) | sourced |

## Phase 1: PRINT statement (basic/print.asm, basic/interp.asm)

Behavioural source: the public MSX-BASIC *language* reference (PRINT items,
`;`/`,` separators, trailing-separator newline suppression, the signed-integer
number format with a leading sign-position space and a trailing space, and 14-
column comma zones). Output uses CHPUT; the comma zone reads CSRX. The `?`
abbreviation and every PRINT form crunch byte-identical to the VG-8020 reference
(`print"hi"`, `print a;b`, `print 1,2`, `?"x"`, `print a;`, `print` all PASS in
`basic_probe_crunch.py`); `print 12*12` → ` 144 ` and `?"HELLO";3-8` → `HELLO-5`
were verified on screen (VRAM dump) in openMSX.

**Multi-item PRINT — differential-confirmed on hardware.** `basic_probe_print.py`
(msx-preservation) types each line into BOTH the reference Philips VG-8020
built-in BASIC and zerobas (same VG-8020, `--cart`), reads each machine's SCREEN 0
name table, and compares the PRINT output rows byte-for-byte. ALL PASS,
ref==zerobas: `print 1;2`→`   1  2`, `print 1;2;3`→`   1  2  3`, `print 10;20`,
`print 7;"hi"`→`   7 hi`, `print 1;-2`→`   1 -2`, and the single comma tab zone
`print 1,2`→`   1             2`. This closes the gap that hid the earlier
"items after the first numeric one are dropped" bug (`print_number` clobbered HL,
`exp_num` lacked the push/pop guard `exp_strvar` has — fixed in basic/print.asm):
the old `basic_probe_statements` only exercised single-item PRINT.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `PRINT` token / `?` abbreviation | `$91` | MSX2 TH Table 2.20; `?`→`$91` oracle-confirmed (crunch) | sourced |
| PRINT items, `;`/`,` separators, trailing-sep newline suppression | — | public MSX-BASIC language reference | sourced |
| Integer number format: leading space (non-neg) / `-` (neg), no leading zeros, trailing space; signed 16-bit | — | public MSX-BASIC language reference (exact format also oracle-observable) | sourced |
| 14-column comma tab zones via CSRX | `$F3DD` | public language reference (zones) + C-BIOS sysvars (CSRX) | sourced |
| `CHPUT` for character output | `$00A2` | C-BIOS / MSX Assembly Page BIOS list | sourced |
| `div10`, number→ASCII, PRINT parse loop | — | **own code** (standard binary divide); not from any disassembly | sourced |
| `NUMBUF` decimal scratch | `$E0C0` | own choice (free page-3 RAM) | sourced |

**Quarantined divergence — comma tab-zone line-wrap.** Real MSX-BASIC moves a `,`
tab to a NEW LINE once the next 14-column zone would run past the screen width
(`basic_probe_print.py` observed the reference VG-8020 print `1,2,3` as `   1
2` / `   3` on two rows). zerobas's `print_comma_zone` tracks the 14-column zone
width but not the width-wrap, so it keeps tabbing on the same line
(`   1             2             3`). Out of loader-stub scope — a stub never
PRINTs enough comma items to wrap — so this is **observed and documented, not
chased** (same discipline as the disk-probe FCB-field divergences). Reported by
`basic_probe_print.py` without failing the in-scope cases.

(String *variables*/functions for PRINT are deferred to the Phase 2 string
engine; only string literals + numeric expressions print today.)

## Phase 1: division + logical/bitwise operators (basic/expr.asm, basic/interp.asm, basic/sysvars.inc)

Token bytes from **MSX2 Technical Handbook Table 2.20**. Precedence (NOT > AND >
OR > XOR below the relationals; `* /` > `\` > MOD > `+ -` above them) from the
public MSX-BASIC *language* reference. Crunch is byte-identical to the VG-8020
reference (full `basic_probe_crunch.py` ALL PASS — including `score`→`SC OR E`
now that `OR` is a known keyword); each operator was verified functionally via
POKE round-trips in openMSX (`100 mod 7`=2, `&hf0 or &h0f`=$ff, `&hff and &h0f`=
$0f, `&haa xor &hff`=$55, `7/2`=3, `&hf000\256`=$f0, `1000\7`=$8e, `(not
&h00ff)and 255`=$00).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `/` `\` `MOD` `AND` `OR` `XOR` `NOT` tokens | `$F4 $FC $FB $F6 $F7 $F8 $E0` | MSX2 TH Table 2.20 | sourced |
| Operator precedence ladder | — | public MSX-BASIC language reference | sourced |
| `AND`/`OR`/`XOR`/`NOT` as 16-bit bitwise (also logical on -1/0 relationals) | — | public MSX-BASIC language reference | sourced |
| `\`/`MOD` integer divide/remainder; `udiv16` restoring division | — | **own code** (standard algorithm); not from any disassembly | sourced |
| `/` computes the integer quotient (zerobas is integer-only) | — | **own design** — diverges from MSX's float `/`; floats are Phase 2 | quarantined |
| Division uses **unsigned** 16-bit operands (address math) | — | **own design** — diverges from MSX's signed integer divide; documented | quarantined |
| Division by zero → 0 + ERRMARK (no crash) | — | own design (MSX raises "Division by zero"); oracle follow-up owed | quarantined |

The integer-only `/`, the unsigned-division choice, and the divide-by-zero
behaviour are **quarantined**: they are deliberate own-design simplifications of
MSX's signed-integer/float arithmetic (Phase 2), chosen to serve loader address
math. A future oracle probe should pin the exact signed/float semantics.

## `ON expr GOTO/GOSUB` (basic/interp.asm, basic/program.asm)

Semantics from the **public MSX-BASIC language reference**: evaluate the 1-based
index expression; find the Nth comma-separated branch target; branch (GOTO) or
call (GOSUB) to it; fall through if N=0 or N > count.  Token `ON=$95` was already
oracle-confirmed (MSX2 TH Table 2.20).  Comma-separated `$0E,<lineno LE>` target
lists reuse the existing `branch_lineno` format — the tokeniser loop was extended
with a comma-list continuation so `branch_lineno` emits multiple `$0E,lo,hi`
entries separated by verbatim commas, matching the reference oracle.

Verified: all 7 functional probes pass on `Philips_VG_8020` in openMSX (ON GOTO
A=1,3,0-fallthrough,>count-fallthrough; ON GOSUB A=1,A=2,0-fallthrough with
RETURN resuming correctly at the statement after the ON…GOSUB).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `ON expr GOTO/GOSUB` semantics (1-based index, N=0 and N>count fall through) | — | public MSX-BASIC language reference | sourced |
| `ON_TOKEN` `$95` | — | MSX2 TH Table 2.20 (already sourced) | sourced |
| Comma-separated `$0E,lo,hi` target list in crunched stream | — | **own code** consistent with the existing `branch_lineno` format; oracle-compatible | sourced |
| `eon_seek_nth` scan algorithm; GOSUB frame layout and resume pointer | — | **own code** (standard linear scan + stack frame); not from any disassembly | sourced |

No quarantined items.

## Phase 1: screen-setup verbs SCREEN / COLOR / CLS / WIDTH / KEY (basic/screen.asm, basic/sysvars.inc, basic/interp.asm)

Thin wrappers over the documented C-BIOS screen entry points — the pre-handoff
screen setup a loader stub does before `BLOAD` (`SCREEN n : COLOR f,b,d : CLS`,
`KEY OFF`). zerobas owns no VDP programming of its own; each verb calls down
through the BIOS jump table the way the real BASIC does (see
`docs/msx1-basic-bios-coupling.md`). Statement *semantics* are from the public
MSX-BASIC *language* reference; the statement tokens are from MSX2 TH Table 2.20
(`CLS=$9F`, `WIDTH=$A0`, `COLOR=$BD`, `SCREEN=$C5`, `KEY=$CC`, already listed in
the DEF USR section), and `OFF=$EB`, the BIOS entry points and the work-area
addresses below are from the MSX Assembly Page / MSX2 TH / C-BIOS.

The new `OFF` keyword and every verb crunch byte-identical to the live VG-8020
reference via `basic_probe_crunch.py` (`screen 2`, `color 15,1,1`, `cls`,
`width 32`, `key off`, `key on`, `screen 1,1` all PASS). Functional behaviour was
verified on `Philips_VG_8020` in openMSX with `basic_probe_screen.py` (9/9 PASS:
SCREEN→SCRMOD, the ignored extra `SCREEN 1,1` arg, COLOR→FORCLR/BAKCLR/BDRCLR
incl. omitted-fg, WIDTH→LINLEN, CLS→cursor home, KEY OFF/ON continue the line).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `OFF` keyword token (`KEY OFF`) | `$EB` | MSX2 TH Table 2.20 / MSX Assembly Page token table; crunch byte-identical (oracle) | sourced |
| `CHGMOD` (SCREEN: switch mode, A = mode) | `$005F` | MSX Assembly Page BIOS list / MSX2 TH | sourced |
| `CHGCLR` (COLOR: apply colours, A = mode) | `$0062` | MSX Assembly Page BIOS list / MSX2 TH | sourced |
| `CLS` (clear screen; zero flag set on entry) | `$00C3` | MSX Assembly Page BIOS list / MSX2 TH | sourced |
| `ERAFNK` / `DSPFNK` (KEY OFF / KEY ON) | `$00CC` / `$00CF` | MSX Assembly Page BIOS list / MSX2 TH | sourced |
| `FORCLR` / `BAKCLR` / `BDRCLR` work vars | `$F3E9` / `$F3EA` / `$F3EB` | C-BIOS system variables (BSD 2-clause); cross-checked MSX2 TH work-area appendix | sourced |
| `LINL40` / `LINL32` / `LINLEN` (WIDTH) | `$F3AE` / `$F3AF` / `$F3B0` | C-BIOS system variables (BSD 2-clause); MSX2 TH work-area appendix | sourced |
| `SCRMOD` current screen mode | `$FCAF` | C-BIOS system variables (BSD 2-clause); MSX2 TH work-area appendix | sourced |
| `SCREEN [mode][,…]`, `COLOR [fg][,bg][,border]`, `CLS`, `WIDTH n`, `KEY OFF/ON` syntax | — | public MSX-BASIC language reference | sourced |
| SCREEN's extra args (sprite size, key click, …) evaluated and ignored — only the display mode is applied | — | own design (minimal; documented in basic/screen.asm) | sourced |
| COLOR applies colours via CHGCLR but does not repaint drawn text; omitted args keep the current colour | — | own design (matches the BIOS-call effect; full repaint is Phase 2) | sourced |
| KEY recognises only `OFF` / `ON`; `KEY <n>,"str"` (redefine) and `KEY LIST` raise syntax error | — | own design (loader-stub scope; full KEY is Phase 2) | sourced |
| WIDTH records the line length in LINLEN + the per-mode default, then re-runs CHGMOD to apply it | — | own code; mirrors the language-reference WIDTH effect | sourced |
| SCREEN/COLOR/CLS/WIDTH/KEY parse + dispatch algorithm | — | **own code** (mirrors the CLEAR/PRINT arg-parse pattern); not derived from any disassembly | sourced |

No quarantined items.

### RAM additions (basic/sysvars.inc)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `LINEBUF` ($E100, 96), `TOKBUF` ($E160), `VARTAB` ($E1C0, 52 bytes) | — | own choice (free page-3 RAM in page $E1, clear of the $C000/$E000 demo regions) | sourced |

No quarantined items.

## Phase 1: LIST statement (basic/list.asm, basic/interp.asm)

`LIST` displays the stored numbered-line program (the one NEW / RUN manage) as
source text. For each stored line it prints the line number, a space, the
**de-tokenised** body, then CR/LF. The handler lives in `basic/list.asm`
(`ex_list`), is dispatched on `LIST_TOKEN` (`$93`, already in `kwtable`) in
`exec_stmt`, and walks the line-link chain from `TXTBASE` exactly like RUN.

The detokeniser (`detok`) is the **inverse of the tokeniser** — it is **own
code**, written as the mirror image of `basic/interp.asm`'s `tokenise:` /
`kwtable` and constrained to the same token set that `tok_skip` steps. It renders
every token the tokeniser can emit:

- keyword tokens → their text by a reverse scan of `kwtable` (`detok_kw`,
  single-byte tokens; `detok_kw2`, the 2-byte forms PEEK `$FF $97` and ELSE
  `$3A $A1`) — the literal reverse of `match_kw`, reading the same table;
- integer / `&H` / `&O` constants (`$11+n` digit, `$0F`,b, `$1C`,w, `$0C` &H,w,
  `$0B` &O,w) → their decimal / `&H` / `&O` source text;
- operator tokens (`= $EF`, `+ $F1`, `- $F2`, `* $F3`, `/ $F4`, `\ $FC`,
  `> $EE`, `< $F0`) → their source character (`detok_op`, reverse of `tk_op_*`);
- line-number references `$0E,<lineno LE>` (and the post-RUN `$0D,<addr LE>`) →
  the decimal number;
- string literals `"…"`, REM / `'` comment tails, and DATA bodies → copied
  verbatim (the tokeniser stored them verbatim);
- the folded forms `:`+`$8F`+`$E6` → `'` and `:`+`$A1` → ` ELSE`.

No new constant or token byte is introduced: every value `detok` decodes is
already defined and cited in `basic/sysvars.inc` (Step A/B token table, MSX2 TH
Table 2.20 / Figure 2.12, oracle-confirmed). The number formatter reuses
`div10` (basic/print.asm); CHPUT (`$00A2`) is the only BIOS call.

LIST *semantics* (line number, one space, de-crunched body, newline) are from the
public MSX-BASIC *language* reference. No disassembly was read: the detokeniser is
derived purely as the reverse of this project's own oracle-sourced tokeniser.

**Divergence (Phase 2):** only the no-argument whole-program `LIST` is
implemented; `LIST <n>` and `LIST <n>-<m>` line-range arguments are deferred — a
trailing argument is currently parsed-past and ignored.

Validated: `make` builds a clean 16384-byte `basic.rom` with no warnings; the
crunch probe stays byte-identical and the controlflow / loops / data / statements
regression probes still pass (LIST adds no tokeniser change). Functional
round-trip verified on `C-BIOS_MSX1` in openMSX by `basic_probe_list.py`
(8/8 PASS): the new probe stores numbered lines, types `LIST`, dumps the SCREEN 0
name table from VRAM (`--mem VRAM:0x0000:960`), and checks each line round-trips
(PRINT + string + `:` + `&H`, FOR/TO/STEP, IF/THEN line-ref + ELSE + multi-char
vars + operator, POKE + REM tail, `;`/`,` separators, DATA body, `'` comment, and
an out-of-order multi-line insert that lists in number order).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `LIST` statement token (already in `kwtable`) | `$93` | MSX2 TH Table 2.20 / MSX Assembly Page token table (oracle-corroborated) | sourced |
| `LIST` semantics (number, space, de-crunched body, CR/LF) | — | public MSX-BASIC language reference | sourced |
| `detok` detokeniser (reverse of `tokenise:` / `kwtable`; `detok_kw`/`detok_kw2`/`detok_op` + constant/lineno/string/REM/DATA renderers) | — | **own code**, the reverse of this project's oracle-sourced tokeniser; not derived from any disassembly | sourced |
| `LIST <n>` / `LIST <n>-<m>` line-range arguments deferred (trailing arg parsed-past + ignored) | — | own design (Phase 2 scope; documented in basic/list.asm) | sourced |

No quarantined items.

## Phase 1: `&O` / `&B` integer literals (basic/interp.asm, basic/expr.asm, basic/sysvars.inc)

`&O<octal>` now crunches and evaluates; `&B<binary>` is a documented descope.

**Oracle (`basic_probe_crunch.py`, scratch test lines, restored to pristine
after).** The reference Philips VG-8020 crunches:

- `a=&o17` → `… 41 EF 0B 0F 00` — i.e. `$0B` (OCT_TOKEN) then `0F 00` = 15 LE
  (octal 17 = 15). `&o777` → `0B FF 01` (511), `&o177777` → `0B FF FF` (65535).
  So `&O` is `$0B,<value16 LE>`, full `0..&HFFFF`, the same shape as `&H`/`$1C`.
- `a=&b1010` → `… 41 EF 26 42 31 30 31 30 00` — `&`(`$26`) `B`(`$42`) then the
  ASCII digits verbatim. **The reference has NO `&B` binary token**: it copies
  `&B…` through as text. So `&B` is *not* tokenised specially, and inventing a
  token would diverge from the oracle.

**Implementation.** `tk_hex` (basic/interp.asm) is generalised from `&H`-only to
dispatch on the character after `&`: `H` → radix 16 / `HEX_TOKEN $0C`, `O` →
radix 8 / `OCT_TOKEN $0B` (radix + token held in new RAM scratch `TKRADIX`
`$E029` / `TKRTOK` `$E02A`); `&B` and a bare `&` fall through to copy the `&`
verbatim, exactly as the oracle does. The single accumulator loop multiplies by
the radix via shifts (`*8` for octal, `*16` for hex) and emits the stored token +
16-bit LE value. `ev_f` (basic/expr.asm) decodes `$0B` through the existing
`ev_f_word` path (identical 2-byte-LE decode to `$0C`/`$1C`). `detok`
(basic/list.asm) already rendered `$0B` → `&O…` (`dt_oct`), so no change there.

**`&B` descope (quarantined).** Because the oracle shows the reference emits no
`&B` token, zerobas keeps `&B…` verbatim (byte-identical to the reference). This
means `&B` is *not* an evaluable binary literal in zerobas — a deliberate
own-design descope, not a fabricated encoding. Should a future need arise it
would be an explicit own-design extension; for now it is quarantined as
"no allowed token to match."

No disassembly was read. `OCT_TOKEN $0B` is from MSX2 TH Table 2.20 and was
oracle-confirmed byte-for-byte by the crunch probe; the tokeniser/decoder
extension is **own code** (forward/reverse of this project's oracle-sourced
tokeniser).

Validated: `make` builds a clean 16384-byte `basic.rom`, no warnings. The crunch
probe is byte-identical incl. `&o17`/`&o777`/`&o0`/`&o177777` (all `$0B,…`) and
`&b0`/`&b1`/`&b1010`/`&b1111111111111111` (all verbatim, matching the reference).
The controlflow / loops / data / statements regression probes all stay ALL PASS.
Functional in openMSX (`Philips_VG_8020`, BLOAD-landmark freeze): `a=&o17`→15,
`a=&o12`→10, `a=&o400`→256, `a=&o177777`→65535.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `&O` octal constant token | `$0B` (`OCT_TOKEN`), `$0B,<value16 LE>` | MSX2 TH Table 2.20; oracle-confirmed byte-identical via `basic_probe_crunch.py` | sourced |
| `tk_hex` radix dispatch (`&H`/`&O`) + octal `*8` accumulator; `TKRADIX`/`TKRTOK` scratch | — | **own code**, forward of this project's oracle-sourced tokeniser; no disassembly | sourced |
| `ev_f` decode of `$0B` (reuses `ev_f_word`) | — | **own code**, mirrors the `$0C`/`$1C` decode | sourced |
| `&B` binary literal kept verbatim (no token) | — | own design: oracle shows the reference emits no `&B` token, so none is fabricated | quarantined |

## Phase 1: memory / I-O access — VPOKE / VPEEK / OUT / INP / VARPTR / BASE (basic/vdpio.asm, basic/expr.asm, basic/interp.asm, basic/sysvars.inc)

The pokes-and-ports primitives a loader stub uses around `BLOAD`: write/read
VDP video RAM (`VPOKE`/`VPEEK`), write/read a Z80 I/O port (`OUT`/`INP`), take a
variable's address (`VARPTR`), and query a VDP table base (`BASE`).

**Oracle (`basic_probe_crunch.py`, scratch test lines, restored to pristine
after).** The reference Philips VG-8020 crunches:

- `vpoke &h1800,65` → `… C6 20 0C 00 18 2C 41` — **VPOKE = `$C6`** (1-byte
  statement token), then the args.
- `out &h99,0` → `… 9C 20 0C 99 00` — **OUT = `$9C`** (1-byte statement token).
- `a=vpeek(&h1800)` → `… 41 EF FF 98 28 …` — **VPEEK = `$FF $98`** (function token,
  the same `$FF`-prefix two-byte form as PEEK `$FF $97`).
- `a=inp(&ha8)` → `… 41 EF FF 90 28 …` — **INP = `$FF $90`** (function token,
  `$FF`-prefix form).
- `a=varptr(b)` → `… 41 EF E7 28 42 29` — **VARPTR = `$E7`** (single-byte function
  token, NOT `$FF`-prefixed).
- `a=base(0)` → `… 41 EF C9 28 11 29` — **BASE = `$C9`** (single-byte function
  token, NOT `$FF`-prefixed).

All six cross-check against MSX2 Technical Handbook Table 2.20. They were then
verified byte-identical with zerobas's own crunch via `basic_probe_crunch.py`
(all 6 PASS) before the probe was restored to pristine.

**Implementation.** `VPOKE`/`OUT` are added to the `exec_stmt` dispatch
(`ex_vpoke`/`ex_out`) and handled in `basic/vdpio.asm`, mirroring `do_poke`'s
two-expression arg-parse: VPOKE writes the value's low byte to VRAM via
`WRTVRM ($004D)` (HL = VRAM address, A = byte); OUT issues a raw `out (c),a` with
BC = port. `VPEEK`/`INP`/`VARPTR`/`BASE` are function factors in `basic/expr.asm`'s
`ev_f`: the `$FF`-prefix factor was generalised from PEEK-only into `ev_f_ff`,
which parses `( <expr> )` once and dispatches on the selector byte — PEEK reads
RAM, VPEEK reads VRAM via `RDVRM ($004A)` (HL = VRAM address → A), INP reads a
port via `in a,(c)`. VARPTR (`$E7`) and BASE (`$C9`) are dispatched directly in
`ev_f` (they are single-byte, not `$FF`-prefixed). `detok` (basic/list.asm)
renders all six with no new code: it is table-driven, so VPOKE/OUT/VARPTR/BASE
fall out of the single-byte `detok_kw` scan and VPEEK/INP out of the 2-byte
`detok_kw2` scan once they are in `kwtable`. `tok_skip` needs no change — these
carry no in-stream operand bytes (the function arguments are ordinary
parenthesised expressions, already steppable).

**VARPTR own-address-map (quarantined).** VARPTR returns the address of the
variable's 2-byte value cell **in zerobas's own variable table (VARTAB)**, which
has zerobas's own layout — *not* the reference ROM's variable-area address map.
This is a deliberate, documented divergence: a loader stub that pokes through
VARPTR sees a valid, writable 16-bit cell, which is all the loader use needs, but
the numeric address differs from a real MSX. If the variable does not yet exist
it is allocated (value 0) so the returned address is always valid. Verified by
`basic_probe_vdpio.py` (`b=&h1234:a=varptr(b)` → PEEK(a),PEEK(a+1) = `34 12`).

**BASE descope (quarantined).** `BASE(n)` is parsed and its argument evaluated,
but it returns 0 and sets ERRMARK (`$DD` at `$E010`) rather than a VDP table base
address. zerobas drives the screen entirely through the C-BIOS CHGMOD path and
keeps no per-mode VDP table-base map of its own; reproducing the reference's exact
BASE() value table would require a forbidden source, so BASE is descoped (the line
still continues — only the BASE *value* is unavailable). Loader stubs needing real
VDP table bases are out of scope for now.

Validated: `make` builds a clean 16384-byte `basic.rom`, no warnings. The crunch
probe stays byte-identical (full ALL PASS, plus the 6 new keywords PASS in a
scratch run, probe restored). The controlflow / loops / data / statements
regression probes all stay ALL PASS. Functional `basic_probe_vdpio.py` 6/6 PASS
on `Philips_VG_8020` (VPOKE/VPEEK round-trip 65 and 200; INP read completes + line
runs; OUT completes + line runs; VARPTR cell = `34 12`; BASE returns 0 + ERRMARK
`$DD`, line continues). LIST round-trips the six keywords on screen.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `VPOKE` statement token | `$C6` | MSX2 TH Table 2.20; oracle-confirmed byte-identical via `basic_probe_crunch.py` | sourced |
| `OUT` statement token | `$9C` | MSX2 TH Table 2.20; oracle-confirmed byte-identical | sourced |
| `VPEEK` function token | `$FF $98` | MSX2 TH Table 2.20; oracle-confirmed byte-identical | sourced |
| `INP` function token | `$FF $90` | MSX2 TH Table 2.20; oracle-confirmed byte-identical | sourced |
| `VARPTR` function token | `$E7` (single-byte) | MSX2 TH Table 2.20; oracle-confirmed byte-identical | sourced |
| `BASE` function token | `$C9` (single-byte) | MSX2 TH Table 2.20; oracle-confirmed byte-identical | sourced |
| `WRTVRM` (VPOKE: write A to VRAM[HL]) | `$004D` | MSX Assembly Page BIOS list / MSX2 TH (VDP I/O) | sourced |
| `RDVRM` (VPEEK: read VRAM[HL] → A) | `$004A` | MSX Assembly Page BIOS list / MSX2 TH (VDP I/O) | sourced |
| `VPOKE`/`VPEEK`/`OUT`/`INP` semantics (write/read VRAM; write/read a Z80 port; low byte; 0..255 read) | — | public MSX-BASIC language reference + Z80 `out (c),a` / `in a,(c)` (hardware) | sourced |
| VPOKE/OUT handlers + `ev_f_ff` $FF-prefix dispatcher (PEEK/VPEEK/INP) + INP `in a,(c)` | — | **own code** (mirrors `do_poke` / `ev_f_peek`); not derived from any disassembly | sourced |
| `VARPTR(var)` returns the address of the value cell in **zerobas's own** VARTAB (not the reference's variable-area map); allocates the variable if new | — | **own design** — zerobas's table layout is its own; valid+writable cell, sufficient for loader pokes; numeric address diverges from a real MSX | quarantined |
| `BASE(n)` descoped: argument parsed+evaluated, returns 0 + sets ERRMARK (no fabricated VDP table-base map) | — | **own design** — reproducing the reference's per-mode VDP table-base values would need a forbidden source; descoped, not fabricated | quarantined |
| `VPOKE_TOKEN`/`OUT_TOKEN`/`VPEEK_TOKEN`/`INP_TOKEN`/`VARPTR_TOKEN`/`BASE_TOKEN` constants | — | own naming over the oracle-/Table-2.20-sourced token bytes | sourced |

The VARPTR own-address-map and the BASE descope are the two **quarantined**
items: both are deliberate own-design simplifications (loader-stub scope), not
values lifted from any reference ROM or disassembly. A future oracle probe could
pin BASE's real per-mode table-base values if a stub ever needs them.

## Phase 1: cassette program load — CLOAD / LOAD"CAS:" (basic/cload.asm, basic/interp.asm, basic/sysvars.inc)

The complement to `BLOAD"CAS:",R`: where BLOAD loads a BSAVE *binary image* into
raw RAM, `CLOAD` and `LOAD"CAS:"` load a *tokenised BASIC program* off cassette
into the stored-program area (the line-link area at TXTBASE that NEW / RUN / LIST
manage) and make it the current program — as if it had been typed. Both verbs
share one cassette I/O path (`do_tape_prog`); they differ only in argument syntax
(`CLOAD ["name"]` — implicit cassette; `LOAD "CAS:name"` — OPEN-style device).

**Oracle (token bytes, `basic_probe_crunch.py`, scratch test lines restored to
pristine after; cross-checks MSX2 TH Table 2.20).** The reference Philips VG-8020
crunches `cload` -> `… 9B 00`, `cload"name"` -> `… 9B 22 6E 61 6D 65 22`,
`load"cas:name"` -> `… B5 22 63 61 73 3A 6E 61 6D 65 22`, `load` -> `… B5`. So
**CLOAD = `$9B`** and **LOAD = `$B5`**, both single-byte statement tokens with the
quoted filename kept verbatim (exactly like BLOAD's `"CAS:"` argument). These were
verified byte-identical against zerobas's own crunch (committed `basic_probe_cload.py`,
all 5 forms PASS) before the crunch probe was restored to pristine.

**Cassette tokenised-BASIC file format.** Like a BSAVE binary, a tokenised BASIC
file is TWO tape blocks (so two TAPION calls, one per block tone): a header block
(10× file-id + 6-char name) and a data block. The file-id selects the kind —
`$D0` binary (BLOAD), **`$D3` tokenised BASIC (here)**, `$EA` ASCII (MSX2 TH,
cassette file format; `$D3` cross-checked against `tape/cassette-tool/cas_identify.py`
and a real VG-8020 CSAVE recording). The data block omits the binary's 6-byte
address header; it is the program-area image: a chain of
`[link:2 LE][lineno:2 LE][tokens…][00]` lines ending in a `$0000` link word — the
same line-link layout zerobas stores at TXTBASE (program.asm, already sourced /
oracle-confirmed). The saved absolute links are recomputed by `relink`
(program.asm) after the load, so the loaded program's bytes become byte-identical
to one typed in. The reader stops EXACTLY at the `$0000` end-link (the device half
blocks on tape silence once a block's data runs out — it does not signal a clean
end-of-data), so no byte past the program is read.

**Implementation.** `CLOAD`/`LOAD` are added to `kwtable` and the `exec_stmt`
dispatch (`ex_cload`/`ex_load` → `do_cload`/`do_load`). `do_cload` accepts an
optional quoted filename (parsed-past, ignored); `do_load` requires a `"CAS:…"`
device string (reusing bload.asm's `dev_cas` / `load_error`) and ignores any
trailing filename. Both fall into `do_tape_prog`, which mirrors bload.asm's tape
contract (TAPION per block; TAPIN trashes all registers so state lives in RAM):
verify the `$D3` id, skip the 16-byte header, re-TAPION the data block, then read
the line-link image into TXTBASE — `$0000` link ⇒ stop, otherwise store link +
lineno + body-to-`$00`, looping — set PRGEND, sync TXTTAB, and `relink`. No new
BIOS entry, RAM scratch is `CLPTR` ($E02B, own free page-3 RAM).

**Filename-ignore (own design).** zerobas keeps no tape file catalogue, so the
optional CLOAD filename / the `"CAS:…"` filename is parsed and discarded — TAPION
simply opens the next file on the tape. This is a documented own-design
simplification (loader-stub scope: a stub chain-loads the next tape file); it is
sufficient for the boot-loader use the project targets.

**Functional-load device-half blocker (quarantined — NOT a defect in this code).**
The interpreter half here is correct and crunch byte-identical, and the synthetic
`.cas` format is oracle-validated: the **reference VG-8020's own built-in CLOAD
loads our two-block `$D3` tape to the exact expected line-link image** at TXTBASE
(`basic_probe_cload.py`, FORMAT check PASS). An end-to-end load *on zerobas* now
also works (`basic_probe_cload_ondevice.py`, ALL PASS, on `C-BIOS_MSX1_EU_TAPE`
with `basic.rom` as a cart so the zerobas-tape reader services cassette). An
earlier in-harness hang was misattributed to the device half ("`TAPIN` cannot
frame a `$00` run"); oracle traces later **disproved** that — `TAPIN` frames the
`$00` run and the `$0000` end-link correctly at all bauds. The real cause was an
interpreter-half **register clobber** in `ctp_line`: `TAPIN` uses `C` as its
bit-counter and always returns `C=0`, but the old code stashed the link-low byte
in `C` across the second `TAPIN`, so the link word read as `$XX00` and the
body-length math hung the loader. Fixed by preserving link-low across the second
read (push/pop). The identical latent clobber in the disk `dpl_line`
(`disk_getbyte` also returns `C=0` on a record refill) was fixed at the same time.
`tape/` was correct throughout and is unchanged. (BLOAD was always unaffected — it
reads a known byte count and never a mid-stream `$0000`; `basic_probe_bload.py`
still PASSes.)

Validated: `make` builds a clean 16384-byte `basic.rom`, no warnings (no
jr-out-of-range). The crunch probe stays byte-identical (full ALL PASS, plus the
5 new CLOAD/LOAD forms PASS in `basic_probe_cload.py`). The controlflow / loops /
data / statements regression probes and `basic_probe_bload.py` all stay PASS.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `CLOAD` statement token | `$9B` | oracle-confirmed byte-identical via `basic_probe_crunch.py`; cross-checks MSX2 TH Table 2.20 | sourced |
| `LOAD` statement token | `$B5` | oracle-confirmed byte-identical via `basic_probe_crunch.py`; cross-checks MSX2 TH Table 2.20 | sourced |
| Quoted filename kept verbatim after the token (like BLOAD's `"CAS:"`) | — | oracle (`cload"name"`/`load"cas:name"` crunch) | sourced |
| Tokenised-BASIC cassette file id | `$D3` (×10) | MSX2 TH cassette file format; cross-checks `tape/cassette-tool/cas_identify.py` + a real VG-8020 CSAVE recording | sourced |
| Two-block layout (header block + data block ⇒ two TAPION) | — | MSX2 TH cassette file format; reference VG-8020 loads our two-block `.cas` correctly (oracle) | sourced |
| Data block = program-area line-link image, ends in `$0000` link | — | program.asm line-link layout (already sourced/oracle); reference-load oracle confirms the loaded image byte-for-byte | sourced |
| Read stops at the `$0000` end-link (never reads past it) | — | own code; the `$0000` link is the program terminator — reading past it would run into trailing carrier/silence and time out in `TAPIN` | sourced |
| Links recomputed by `relink` after load (loaded image = typed image) | — | program.asm `relink` (already sourced) | sourced |
| `CLOAD`/`LOAD` parse + `do_tape_prog` read algorithm; `CLPTR` ($E02B) scratch | — | **own code** (mirrors bload.asm's tape contract + program.asm's store/relink); not derived from any disassembly | sourced |
| Optional CLOAD filename / `"CAS:"` filename parsed and **ignored** (no tape file catalogue; TAPION opens the next file) | — | **own design** (loader-stub scope; documented in basic/cload.asm) | quarantined |
| On-zerobas end-to-end functional load (incl. the `$0000` end-link) | works | `basic_probe_cload_ondevice.py` ALL PASS (`C-BIOS_MSX1_EU_TAPE` + `basic.rom` cart, zerobas-tape reader). The earlier "blocked by device half" theory was disproved by oracle traces; the cause was the `ctp_line` register clobber, now fixed | sourced |

The filename-ignore is the one remaining **quarantined** item: a deliberate
own-design simplification (loader-stub scope), not a value lifted from any
reference ROM or disassembly. The earlier "on-device load blocked by zerobas-tape
`$00`-run framing" quarantine has been **resolved and removed**: oracle traces
disproved the device-half theory, the real cause was the `ctp_line` link-word
register clobber (fixed; see above), and on-device CLOAD/LOAD now load correctly.
The CLOAD/LOAD interpreter half is complete, crunch byte-identical, and
oracle-validated against both the reference's own CLOAD and an on-device load.

## Phase 1: minimal string variables for PRINT (basic/strvar.asm, basic/vars.asm, basic/print.asm, basic/interp.asm, basic/sysvars.inc)

"Enough for PRINT": a `$`-suffixed variable (e.g. `A$`) can hold a short string,
be assigned a `"literal"` or a copy of another string var (`A$=B$`), and be
PRINTed (including next to literals, `PRINT "X=";A$`). The full string engine —
heap + descriptor model, concat (`+`), `LEN`/`MID$`/`LEFT$`/`RIGHT$`/`CHR$`/… ,
string arrays + `DIM`, and string `DATA` — is **Phase 2 and explicitly NOT built
here**.

**Oracle (`basic_probe_crunch.py`, scratch test lines restored to pristine
after).** The reference Philips VG-8020 crunches `$`-variable lines exactly as
zerobas already does — **the crunch was byte-identical with no code change**,
because `$` is part of the variable name, not a special token:

- `a$="hi"`        → `… 41 24 EF 22 68 69 22` — `A`(`$41`) `$`(`$24`) `=`(`$EF`)
  then the literal `"hi"` verbatim. **The `$` is kept as the ASCII byte `$24` in
  the name; there is NO string-variable token.**
- `print a$`       → `… 91 20 41 24` — PRINT, space, `A$`.
- `b$=a$`          → `… 42 24 EF 41 24` — `B$` `=` `A$`.
- `print "x=";a$`  → `… 91 20 22 78 3D 22 3B 41 24` — PRINT `"x="` `;` `A$`.
- `let a$="z"`     → `… 88 20 41 24 EF 22 7A 22` — LET `A$` `=` `"z"`.

All six were confirmed byte-identical to zerobas's own `TOKBUF` via the crunch
probe (then the probe was restored to pristine — never committed). So this task
added **no tokeniser change**: the gap was purely runtime (store + print).

**String storage & value-type (own-design, quarantined).** zerobas does **not**
reproduce the reference ROM's string heap / string-descriptor layout (that would
need a forbidden source and is Phase 2). Instead it uses a minimal own-design
store:

- A string variable is a fixed-capacity inline record in a separate table
  `STRTAB` ($E240), keyed by the same 2-character `[name0][name1]` key as a
  numeric variable: `[name0:1][name1:1][len:1][bytes:STRMAX]`. `name0 = 0` marks
  a free slot. `STRMAX = 32`, `STRSLOTS = 8`. `A` and `A$` are independent (the
  `$` suffix selects this store vs the numeric one) — matching MSX-BASIC.
- A string VALUE is a `[len:1][bytes…]` descriptor; `STRPTR` points at it and
  `VALTYP = 1` flags "string". Only LET and PRINT consult VALTYP; arithmetic
  stays numeric-only. `STRSCR` ($E360) is scratch holding a literal lifted out of
  the token stream before LET copies it into the variable's slot.
- A value longer than `STRMAX` is **truncated** (no heap growth); an unset string
  variable reads as the empty string (a shared len-0 `STR_EMPTY` descriptor in
  ROM); the table-full case silently drops the assignment.

This store and the VALTYP/STRPTR notion are an original minimal design — chosen
for the "enough for PRINT" loader-stub scope — **not** lifted from any reference
ROM or disassembly.

**Implementation.** `var_str_type` (basic/vars.asm) reports whether a name
carries a `$` suffix (without advancing), so LET/PRINT/the factor layer can pick
the string path. `str_find`/`str_get_key`/`str_set_key` (basic/vars.asm) are the
string-store parallels of `var_find`/`var_get_key`/`var_set_key`. `str_eval`
(basic/strvar.asm) evaluates a string operand — a `"literal"` (copied into STRSCR)
or a `$`-variable (STRPTR → its stored descriptor) — and sets VALTYP/STRPTR.
`print_strval` emits a descriptor via CHPUT. `ex_let` (basic/interp.asm) branches
to `ex_let_str` for a `$`-name; `ex_print` (basic/print.asm) detects a `$`-var
item and prints its value (string literals already printed). `clear_vars` now
also empties STRTAB. `detok` (basic/list.asm) needs **no change**: the `$` is a
verbatim name byte and the literal is verbatim, so `10 A$="HI":PRINT A$` lists
back exactly (verified on screen in openMSX).

**Scope cut — explicitly NOT built (Phase 2 string engine):** concatenation
(`+` on strings), all string functions (`LEN MID$ LEFT$ RIGHT$ CHR$ ASC STR$ VAL
HEX$ …`), string arrays / `DIM`, string `DATA`/`READ`, `INPUT` of strings, and
the reference's real string heap/descriptor layout. The numeric expression
evaluator is unchanged and still integer-only.

Validated: `make` builds a clean 16384-byte `basic.rom`, no warnings / no
jr-out-of-range. The crunch probe stays byte-identical (full ALL PASS). The
controlflow / loops / data / statements / list regression probes all stay
ALL PASS. Functional `basic_probe_strvar.py` 6/6 PASS on `C-BIOS_MSX1` (VRAM
screen decode): `A$="HELLO":PRINT A$`→`HELLO`, `PRINT "X=";A$`→`X=HELLO`,
`B$=A$:PRINT B$`→the copy, the LET-keyword form, two independent string vars
(`PRINT A$;B$`→`ONETWO`), and reassignment (`SECOND`). A `$`-var lists correctly
(`10 A$="HI":PRINT A$`).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `$` is part of the variable name — NO special string-variable token | — | oracle (`basic_probe_crunch.py`: `a$="hi"` → `41 24 EF 22 68 69 22`); crunch byte-identical with no code change | sourced |
| `A$="literal"` / `A$=B$` / `PRINT A$` / `PRINT "X=";A$` crunch | (verbatim `$`/literal + `=`/`;`/`,`) | oracle (the five lines above, byte-identical) | sourced |
| String variable / PRINT-of-string *semantics* (assign, copy, print; `A` and `A$` independent; unset = "") | — | public MSX-BASIC language reference | sourced |
| String store layout `[name0][name1][len][bytes:STRMAX]` in STRTAB; STRMAX=32, STRSLOTS=8 | $E240 / 32 / 8 | **own design / own choice** (free page-$E RAM); NOT the reference's string heap/descriptor layout | quarantined |
| `VALTYP` / `STRPTR` value-type notion (0=numeric, 1=string + descriptor ptr) | $E0C8 / $E0C9 | **own design** (minimal stand-in; the reference's DAC/VALTYP model is not reproduced) | quarantined |
| `STRSCR` literal-lift scratch (`[len][bytes:STRMAX]`) | $E360 | own choice (free page-$E RAM) | sourced |
| Over-STRMAX truncation; unset string = shared len-0 `STR_EMPTY` (ROM); table-full drops the assignment | — | **own design** (no heap growth; loader-stub scope) | quarantined |
| `var_str_type` / `str_find` / `str_get_key` / `str_set_key` / `str_eval` / `print_strval` / `ex_let_str` parse + store + print algorithm | — | **own code** (parallels the numeric var store + the PRINT/LET arg-parse pattern); not derived from any disassembly | sourced |
| NOT built: concat `+`, string functions, string arrays/`DIM`, string `DATA` | — | Phase-2 string engine (explicitly descoped) | quarantined |

The string store layout, the VALTYP/STRPTR value-type notion, the truncation /
empty-/full-string behaviour, and the deliberate Phase-2 descope are the
**quarantined** items: all are original minimal own-design choices for the
"enough for PRINT" loader scope — none is a value lifted from any reference ROM
or disassembly. The oracle confirms `$` is part of the name (no fabricated
token), and the crunch stays byte-identical.

## Phase 1: CONT + Ctrl-STOP break handling (basic/interp.asm, basic/program.asm, basic/sysvars.inc)

Run-control: while a program is RUNning, Ctrl-STOP interrupts it at the current
line and returns to the REPL with a `break in <line>` indication; the `STOP`
statement does the same at its point in the line. `CONT` resumes a stopped /
broken program from where it stopped. If there is nothing to continue (never ran,
ran to completion, or the program was edited since the break), `CONT` reports
`can't continue`.

**Oracle (CONT token; `basic_probe_crunch.py`, scratch test lines `cont`, `stop`,
`cont:print 1`, restored to pristine after).** The reference Philips VG-8020
crunches `cont` to a single statement token **`$99`** (`… 52 3A 99 00`), and
`cont:print 1` to `… 99 3A 91 20 12 00` — i.e. CONT is one byte, no operands,
followed normally by `:PRINT 1`. `STOP` was already oracle-confirmed as `$90`.
CONT = `$99` cross-checks MSX2 TH Table 2.20. The byte was read from the reference
and is not fabricated; after the read the crunch probe was restored to pristine
(never committed).

**Ctrl-STOP polling — BIOS BREAKX `$00B7`.** The run loop polls Ctrl-STOP between
statements/lines with `BREAKX` (`$00B7`), which scans keyboard matrix row 6 with
no side effects and returns CF set when Ctrl-STOP is held, CF clear otherwise.
This is the documented MSX Assembly Page / MSX2 Technical Handbook contract, and
it is oracle-confirmed working **identically on C-BIOS_MSX1** (msx-preservation
`tools/omsx/bios_probe_breakx.py`; `docs/cbios-probe-results.md`: "$00B7 BREAKX —
pass … carry clear on both. IDENTICAL"). So the Ctrl-STOP functional check runs on
the default C-BIOS_MSX1 machine — no Philips fallback was needed (the Philips-only
rule applies only to tape `bload"cas:",r` landmark probes).

**CONT resume-state RAM layout (own-design, quarantined).** On a break, the run
loop records the minimal state needed to continue: `CONTLINE` (`$E0D0`, 2) = the
link-field address of the interrupted line (same meaning as the run loop's
`CURLINE`), `CONTPTR` (`$E0D2`, 2) = the exact token position to resume at, and
`CONTVALID` (`$E0D4`, 1) = 1 when a resume point is live. CONT restores these via
the existing mid-line resume path (`RESUMEFLAG`/`RESUMEPTR`, the same mechanism
RETURN/NEXT use) and re-enters the run loop **without** re-clearing variables or
the GOSUB/FOR/DATA state, so the suspended run continues with its full context.
The resume *point* differs by break source: a Ctrl-STOP saves the statement that
was about to run (so CONT re-runs from there); the `STOP` statement saves the
position right after the STOP token (so CONT runs the statement after STOP).
`CONTVALID` is cleared at RUN entry, on a program edit (`store_line`), and on
`NEW`, so CONT after a clean completion / a STOP-less run / an edit gives
`can't continue`. This three-word layout and the choice of resume points are
own-design (zerobas's run loop is its own design — not the reference's CONTXT /
OLDTXT / OLDLIN sysvar set, reproducing which would need a forbidden source);
sufficient for the loader-stub scope.

**Message text.** `break in <line>` and `can't continue` reproduce the *role* and
the documented observable wording of MSX-BASIC's `Break in <line>` and
`Can't CONTINUE` messages (MSX2 TH error/message list — an allowed source), but in
zerobas's existing **lowercase** style (matching `syntax error`, `out of memory`,
`undefined line`, …), so the wording is a documented own-design approximation, not
copied verbatim from any disassembly. The line number is printed via the existing
`ln_div_entry` bare-decimal formatter (already sourced); `can't continue` also
sets the error landmark `$C9` at `ERRMARK` (`$E010`), distinct from the other
landmark bytes.

Validated: `make` builds a clean 16384-byte `basic.rom`, no warnings (no
jr-out-of-range — the dispatch entries use `jp`). The crunch probe stays
byte-identical incl. the new `cont` → `$99` (full ALL PASS). The controlflow /
loops / data / statements regression probes all stay ALL PASS — confirming the
BREAKX poll in the run loop does not change normal completion and never
false-breaks (BREAKX reads CF clear / not-pressed during normal runs on
C-BIOS_MSX1; oracle-confirmed by `bios_probe_breakx.py` / `cbios-probe-results.md`
and re-confirmed by every program here running to completion). Functional
`basic_probe_cont.py` (msx-preservation) on `C-BIOS_MSX1`, 7/7 ALL PASS, via
fixed-emulated-time RAM capture (`debug read_block` of POKE sentinels at $D000/
$D001 and `ERRMARK` $E010 — robust where a bload-LANDMARK freeze was not): STOP
halts before the post-STOP statement (T=01); STOP→CONT resumes (T=02), incl.
across a line boundary (T=01,U=09); bare CONT / CONT after a STOP-less RUN / CONT
after a program edit all give `can't continue` ($C9); and a real Ctrl-STOP
keyboard-matrix press (openMSX `keymatrixdown` CTRL row6/bit1 + STOP row7/bit4)
breaks an *infinite* `goto` loop back to the REPL — proven by a direct POKE typed
after the press executing (U=09), where the same loop without the press never
yields (control: U stays cleared).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `CONT` statement token | `$99` | oracle-confirmed byte-identical via `basic_probe_crunch.py`; cross-checks MSX2 TH Table 2.20 | sourced |
| `STOP` statement token | `$90` | already oracle-confirmed (controlflow); re-confirmed here | sourced |
| `BREAKX` Ctrl-STOP poll entry | `$00B7` (CF set = pressed) | MSX Assembly Page BIOS call list / MSX2 TH; oracle-confirmed working on C-BIOS_MSX1 (`bios_probe_breakx.py`, `cbios-probe-results.md`) | sourced |
| Ctrl-STOP poll between statements/lines in the run loop | — | own code (poll point is ours); BREAKX contract is sourced | sourced |
| CONT resume-state layout: `CONTLINE` ($E0D0), `CONTPTR` ($E0D2), `CONTVALID` ($E0D4) | — | **own design** — minimal resume state in free page-$E0 RAM; NOT the reference's CONTXT/OLDLIN sysvar set | quarantined |
| Resume points: STOP → after the STOP token; Ctrl-STOP → the statement about to run | — | **own design**; reuses the existing RESUMEFLAG/RESUMEPTR mid-line resume path | quarantined |
| `CONTVALID` cleared on RUN / `store_line` (edit) / `NEW` → `can't continue` thereafter | — | own code reproducing the language-reference "Can't CONTINUE after edit / no run" behaviour | sourced |
| `break in <line>` / `can't continue` message wording | — | **own design** lowercase approximation of MSX-BASIC's `Break in <line>` / `Can't CONTINUE` (role + observable text from MSX2 TH message list); not copied from any disassembly | quarantined |
| `can't continue` error landmark | `$C9` at `ERRMARK` ($E010) | own choice (distinct landmark byte) | sourced |

The CONT resume-state layout, the choice of resume points, and the lowercase
message wording are the **quarantined** items: all are original own-design choices
(zerobas's run loop and message style are its own), not values lifted from any
reference ROM or disassembly. The CONT token byte and the BREAKX entry are both
oracle-confirmed / allowed-source-sourced.

## extension-ROM INIT scan (basic/initext.asm, basic/sysvars.inc)

On the combined machine (zerobas-BASIC in slot 0 page 1, zerobas-disk in slot
3-1), C-BIOS's cold-boot cartridge scan reaches zerobas-BASIC before slot 3-1;
zerobas's INIT enters the REPL and never returns, so C-BIOS never scans the
remaining slots and the disk ROM's INIT (which installs its DSKIO/PHYD hooks and
the SYSTEM/BDOS vector) never runs. `init_ext_roms`, called from `init` just
before `repl`, performs the rest of that boot scan itself: for every primary slot
*after* its own and every expanded subslot, it looks for the standard `"AB"`
header at $4000 and `CALSLT`s the INIT entry (the word at $4002) — exactly what
the BIOS boot scan does. A standard extension/disk INIT installs its hooks and
returns.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `RDSLT` (read a byte from any slot; A=slot, HL=addr → A) | $000C | MSX Assembly Page BIOS call list / MSX2 Technical Handbook | sourced |
| `RDSLT` clobbers AF/BC/DE, preserves HL/IX/IY | — | MSX Assembly Page BIOS call list | sourced |
| `CALSLT` (inter-slot call; IYh=slot, IX=addr) | $001C | MSX Assembly Page BIOS call list / MSX2 Technical Handbook | sourced |
| `EXPTBL` (expanded-slot flags, 1 byte/primary, bit 7 = expanded) | $FCC1 | MSX2 TH work area / C-BIOS system variables | sourced |
| Primary-slot-select I/O port (page-1 field = bits 3-2) | $A8 | MSX2 TH slot architecture | sourced |
| Slot-id byte format: bit7 = expanded, bits3-2 = secondary, bits1-0 = primary | — | MSX2 TH slot architecture | sourced |
| `"AB"` header + INIT entry word at $4002, scanned at $4000–$4003 | — | MSX2 TH cartridge ROM format (same header zerobas itself carries) | sourced |
| Scan policy: only primaries *after* our own page-1 primary (and their expanded subslots) | — | **own design** — matches the BIOS scan order so slots C-BIOS already initialised, and zerobas's own non-returning INIT, are never re-entered | quarantined |
| INIT scan scratch: `SCAN_PRIM` $E0D5, `SCAN_SLOT` $E0D6, `SCAN_INIT` $E0D7, `SCAN_IY` $E0D9 | — | own choice (free page-$E0 RAM in the $E0D5–$E0FF gap; used once at INIT, entirely under `di`, dead afterwards) | sourced |
| Scan runs under `di` (uninterrupted slot switching), `ei` on completion | — | own code; standard practice for RDSLT/CALSLT slot switching | sourced |
| disk-ROM slot capture: `DISKSLOT` $E0E7, `DISKSLOT_OK` $E0E8 | — | own choice (free page-$E0 RAM). The scan records the slot id (`SCAN_SLOT`) of each external `"AB"` ROM it inits, so BLOAD can later `CALSLT` the disk ROM's `bdos_entry` across slots (the entry *address* comes from the disk INIT's SYSTEM $F37D). Last-one-wins; the combined machine has exactly one external AB ROM (the disk), so it is unambiguous | sourced |

The only **quarantined** item is the scan *policy* (primaries after our own): an
original own-design choice. It is the cleanest correct behaviour for the standard
deployment (zerobas the slot-0 primary, scanned before the disk ROM in slot 3-1)
and avoids re-entering zerobas's own non-returning INIT. A consequence/limitation:
an extension ROM sharing zerobas's own (expanded) primary in a different subslot
is not reached — not the case for the slot-3-1 disk reference. Every BIOS entry,
sysvar, and the header/slot-id formats are allowed-source-sourced.

**Functional validation (openMSX, `disk_probe_init.py` in msx-preservation).** On
the combined `C-BIOS_MSX1_BASIC_DISK` machine, after boot the location the disk
ROM's INIT publishes now carries its value: `SYSTEM` ($F37D) = `bdos_entry`. (The
disk INIT formerly also installed `JP` hooks at `H.PHYD` $FF3E / `H.DSKIO` $FF4B;
those were removed from `disk/disk.asm` as oracle-contradicted dead code — see
disk/PROVENANCE.md §INIT — so the probe now asserts SYSTEM only.) Differential
control with the pre-scan ROM: `SYSTEM` reads the C-BIOS default ($31C3 — INIT did
not run). Crunch byte-identical and the four regression probes still pass (the scan
runs harmlessly before the REPL).

## disk DSKIO host engine (Phase 1.5) — standard-sector retarget (basic/fat.asm)

**What changed and why.** The disk loader verbs (`BLOAD`/`LOAD`/`RUN`/`SAVE`/
`BSAVE` for `"A:"`) formerly reached files through zerobas-disk's **private**
`bdos_entry` (the FCB BDOS layer, via the SYSTEM vector `$F37D`). Only the matched
zerobas-BASIC + zerobas-disk pair worked — a real/foreign standard disk ROM does
not implement that private FCB BDOS, so it could not service the loader. Phase 1.5
retargets the loader to the **standard `$4010` DSKIO physical-sector interface**
that *every* MSX1 disk ROM publishes, and moves the FAT12/directory logic
loader-side (`basic/fat.asm`, ported from our own `disk/disk.asm`). The loader is
now **disk-ROM-independent**: any standard disk ROM in the slot services it.

A black-box spike on the real National **CF-3300** Disk BASIC established (and the
[expansion-protocol.md](../disk/docs/expansion-protocol.md) pins) that the
drive-letter loader path is *pure DSKIO* — the disk ROM resolves `"A:"` internally
(BPB/FAT/dir) and moves bytes via DSKIO; there is no standard "open file by name"
entry to delegate to. So owning the FAT12 logic loader-side is the necessary price
of the universal sector interface, not avoidable duplication.

| Item | Value | Source class | Note |
|------|-------|--------------|------|
| `DSKIO_ENTRY` (disk-ROM interface table DSKIO offset) | $4010 | MSX2 TH §5 disk-ROM interface; black-box CF-3300 obs (expansion-protocol.md §3) | sourced — 16-byte header → table at base+$10; base $4000 → $4010 |
| DSKIO register convention: A=drive, B=#sectors, C=media, DE=first logical sector, HL=buffer, **CY=direction (clear=read/set=write)**; out CY=err, A=code, B=not-done | — | MSX2 TH §5; CF-3300 live trace (expansion-protocol.md §3) | sourced |
| cross-slot DSKIO via `CALSLT` $001C (slot=`DISKSLOT`, addr=$4010); CALSLT passes caller AF (direction CY) into the target and returns the target AF (error CY) | $001C | MSX Assembly Page / MSX2 TH; C-BIOS `clprim` restores AF around `jp (ix)` (observed, not transcribed) | sourced |
| FAT12 engine (BPB parse, cluster walk, 8.3 dir search, 12-bit nibble pack/unpack, free-cluster alloc, multi-FAT sync, dir create/update) | — | Microsoft FAT spec / ECMA-107 | **ported verbatim from disk/disk.asm** (our own clean-room code) |
| media descriptor passed to DSKIO | $F9 | MSX2 TH (720K) / CF-3300 obs; ignored by single-drive DSKIO | sourced |
| FAT engine scratch + 2× 512-byte sector buffers (`FSECTOR_BUF` $E5C0, `FWBUF` $E7C0, `FAT_*`/`FREAD_*`/`FWR_*` $E9C0..) | — | own choice (free page-3 RAM; survives DSKIO — own ROM uses only $E29A..$E29F, a foreign ROM keeps its sector work in the $F2xx-$F3xx sysvar area) | sourced placement |

**Oracle (host direction, BOTH disk ROMs).** `BLOAD"A:"` / `LOAD"A:"` / `RUN"A:"` /
`SAVE"A:"` / `BSAVE"A:"` all round-trip under zerobas-BASIC with (i) our own
`disk.rom` in slot 3-1 **and** (ii) the foreign National **CF-3300** disk ROM in
slot 3-1 — the machine rebuilt via `install-openmsx-machine.py --disk-rom <ROM>`.
The msx-preservation probes `disk_probe_bload_disk.py`, `disk_probe_save.py`,
`disk_probe_load_disk.py`, `disk_probe_run_disk.py`, `disk_probe_load_embedded_nul.py`
report **ALL PASS on both ROMs**. Before the retarget the foreign CF-3300 FAILED
every disk verb (the private `bdos_entry` path `CALSLT`ed `$F37D`, which CF-3300
sets to its own Disk-BASIC vector → garbage); after it, both ROMs drive the same
loader unchanged. That disk-ROM-independence is the whole point of the host side.
This is a black-box functional oracle (type a REPL line, observe RAM/PC); no ROM
is read or disassembled. The underlying DSKIO read is itself a passed differential
oracle vs the real CF-3300 (`disk_probe_dskio.py`, strand 1 below).

The `bdos_entry`/FCB BDOS path and its constants are **retired from the loader**
(no disk verb calls `bdos_entry` any more). zerobas-disk keeps `bdos_entry` as its
own internal implementation, and the differential-vs-MSX-DOS strand (below) still
describes that ROM-side layer — but the host loader no longer rides it.

## disk BLOAD / LOAD / RUN surface — consolidated index

The sections below cover the whole disk-aware loader surface. As of Phase 1.5 the
verbs reach files through the **standard `$4010` DSKIO** entry and the loader-side
FAT12 engine (`basic/fat.asm`, `§disk DSKIO host engine` above) — NOT the private
`bdos_entry`. They build on the `§extension-ROM INIT scan` above (which records
`DISKSLOT`/`DISKSLOT_OK`). This index is a map, not a substitute — the detail
tables stay in the per-feature sections. NOTE: the per-feature sections below
(`§disk BLOAD execute`, `§disk LOAD`, `§disk RUN`) were written for the original
`bdos_entry` FCB path and describe the on-disk FORMAT (markers, header layout,
streaming/relink) accurately; only their "reaches disk ROM via BDOS FCB calls"
plumbing is superseded by the DSKIO engine — read them for format, this section
for the transport.

| Surface | Verb | On-disk format / marker | Reaches disk ROM via | Detail section |
|---------|------|-------------------------|----------------------|----------------|
| Filename → 8.3 parse | `BLOAD"A:name"` (shared by all) | n/a (parses `"A:"`/`"B:"`/bare → `DISK_FCB_NAME`) | — (parse only) | §disk-BLOAD scratch FCB |
| Binary image load | `BLOAD"A:name"[,R]` | BSAVE binary, `$FE` header | standard DSKIO $4010 + loader FAT12 (`fat_io_open`/`fat_io_getbyte`) | §disk DSKIO host engine, §disk BLOAD execute |
| Tokenised program load | `LOAD"A:name"[,R]` | tokenised BASIC, `$FF` marker | same DSKIO/FAT12 read path; streams line-link image | §disk DSKIO host engine, §disk LOAD |
| Load-then-run | `RUN"A:name"` | tokenised BASIC, `$FF` marker | reuses `disk_prog_load` (§disk LOAD), always runs | §disk RUN |
| Binary / tokenised SAVE | `SAVE"A:name"` / `BSAVE"A:name",s,e[,x]` | `$FF` / `$FE` markers | standard DSKIO $4010 + loader FAT12 (`fat_io_create`/`fat_io_putbyte`/`fat_io_close`) | §disk DSKIO host engine |

**Constants the disk-extension path introduces (all `sourced`; see the named
section for the row):**

| Constant | Value | Source class | Section |
|----------|-------|--------------|---------|
| standard DSKIO entry offset + register convention (CY=direction) | $4010 | MSX2 TH §5 / CF-3300 obs | §disk DSKIO host engine |
| cross-slot DSKIO call: `CALSLT` $001C via `DISKSLOT`, addr $4010 | $001C / $4010 | MSX Assembly Page / MSX2 TH | §disk DSKIO host engine, §extension-ROM INIT scan |
| 8.3 name field +0..+10 (8 name + 3 ext, space-padded, upper-case) | — | Microsoft FAT spec §3.4; consumed by `fat_find`/`fat_dir_create` | §disk-BLOAD scratch FCB |
| disk BSAVE header `[$FE][start:2 LE][end:2 LE][exec:2 LE]` + raw data, start..end inclusive | $FE marker | MSX-BASIC file formats (MSX Wiki / MSX Resource Center) | §disk BLOAD execute |
| tokenised-BASIC disk marker | $FF | MSX-BASIC file formats (MSX Wiki / MSX Resource Center) | §disk LOAD |
| `DISK_FCB_NAME` / `DISKSLOT` / FAT engine scratch placement | $E0DC / $E0E7 / $E5C0+ | own choice (free page-$E0 / page-3 RAM, collision-checked) | §disk-BLOAD scratch FCB, §disk DSKIO host engine, §extension-ROM INIT scan |

### Oracle-confirmation status (read this before trusting "confirmed")

This surface has **four distinct validation strands**; the docs above deliberately
do not over-claim "byte-identical vs reference" where no reference exists.

1. **DSKIO sector-read — differential, byte-identical vs the real National
   CF-3300.** The **DSKIO sector-read path** underneath all of this
   (`disk_probe_dskio.py` in msx-preservation) is a *passed differential oracle*:
   the same `disk/test720.dsk` read on the CF-3300 reference and on our
   `*_BASIC_DISK` machine returns byte-identical data + carry/A. This is the read
   layer every BLOAD/LOAD/RUN ultimately rides on.

2. **FCB BDOS layer — NARROW differential, byte-identical vs real MSX-DOS 1.**
   `bdos_entry`'s FCB calls (Open `$0F` / Sequential Read `$14` / Close `$10` /
   Set-DTA `$1A`) *are* now differentially oracle-confirmed against genuine
   MSX-DOS 1.03 (`disk_probe_bdos.py` in msx-preservation). The same `ORACLE.BIN`
   (16 × 128-byte records) is read through Open → 17× SeqRead → Close on (a) real
   MSX-DOS — driven by a tiny `.COM` auto-run via `AUTOEXEC.BAT` from a DOS system
   disk on `National_CF-3300` — and (b) our `bdos_entry` reached across slots with
   CALSLT; the Open result, all 16 records, the EOF code, and the Close result come
   back **byte-identical**. The CF-3300's own ROM runs Disk BASIC (no CP/M FCB
   BDOS; see §INIT / disk/PROVENANCE.md), so MSX-DOS — not the CF-3300 disk ROM —
   is the reference for *this* layer; it is used strictly black-box (observe BDOS
   results + delivered bytes; MSXDOS.SYS / COMMAND.COM are never read or
   disassembled). **Scope: NARROW.** `ORACLE.BIN` is an exact cluster multiple, so
   EOF lands on a clean cluster boundary and the documented cluster-granular-EOF
   simplification is not exercised, and the FCB extent (+12) / current-record (+32)
   fields are not differenced. The **FULL** differential (those field mutations +
   sub-record EOF byte-bounding) needs `bdos_entry` tightened first and is a
   tracked follow-up (disk/TODO.md §interpreter extensions).

3. **BLOAD/LOAD/RUN/SAVE/BSAVE interpreter glue — functionally validated on
   openMSX, BOTH disk ROMs.** As of Phase 1.5 the verbs ride the standard `$4010`
   DSKIO entry + the loader-side FAT12 engine (`§disk DSKIO host engine`), NOT the
   `bdos_entry` FCB calls. The whole interpreter glue (token parse → 8.3 name parse
   → BSAVE/tokenised header parse → FAT12 read/write → store/exec/`,R`/relink) is
   validated *functionally* against our own FAT12 image, under **both** our own
   `disk.rom` and the foreign National **CF-3300** disk ROM, by
   `disk_probe_bload_disk.py` / `disk_probe_save.py` / `disk_probe_load_disk.py` /
   `disk_probe_run_disk.py` / `disk_probe_load_embedded_nul.py` (ALL PASS on both).
   Passing identically on a foreign standard ROM is itself the strong evidence:
   the host side speaks only the documented sector interface, so a ROM it has never
   seen services it unchanged. The DSKIO read underneath is a passed differential
   oracle vs the real CF-3300 (strand 1). **Do not read "validated end-to-end" in
   the sections below as "byte-identical vs a BASIC reference" for the interpreter
   glue itself — there is no reference MSX-BASIC *statement* path to differ
   against; the disk-ROM-independence + the differential DSKIO read are the
   guarantees.**

4. **Crunch (tokeniser) confirmed byte-identical vs the Philips VG-8020.** No new
   token byte was introduced for any of BLOAD/LOAD/RUN disk forms — disk
   filenames are verbatim ASCII in the crunch stream — and the crunch of e.g.
   `RUN"A:PROG.BAS"` is confirmed byte-identical vs the Philips VG-8020 reference
   (`basic_probe_crunch.py`, ALL PASS). This is a genuine differential oracle, on
   the tokeniser only.

**Embedded-`$00` streamed load — FIXED (length-driven body copy).** An earlier
`disk_prog_load` / `do_tape_prog` body streamer copied a line's token body until
the first `$00`, so a tokenised program with an embedded `$00` *operand* byte
(e.g. the high byte of an `&H` 16-bit literal `$0C $7B $00`, or `&HD100` →
`$0C $00 $D1`) was truncated mid-line — on **both** tape and disk LOAD/RUN. Both
readers now copy each body by the length DERIVED FROM THE SAVED LINK-WORD
DIFFERENCES, so embedded `$00`s round-trip. See *§disk LOAD — embedded-`$00`
length-driven body copy*.

## disk-BLOAD scratch FCB — filename parse (basic/bload.asm, basic/sysvars.inc)

PARSE-ONLY extension of `do_bload`'s device-string parser: it now recognises a
disk filename (`"A:name"` / `"B:name"` / bare `"name"`) in addition to the
existing `"CAS:"`, builds a CP/M-style scratch File Control Block in RAM, then
routes to the `do_disk_bload` placeholder (which, until the NEXT TODO item lands,
falls through cleanly to `load_error`). The `"CAS:"` tape path is byte-for-byte
unchanged. No new keyword/token: BLOAD arguments are kept verbatim ASCII in the
crunch stream (spec-tokenise.md), so the tokeniser is untouched and crunch stays
byte-identical (confirmed against the Philips VG-8020).

| Item | Value | Source | Status |
| --- | --- | --- | --- |
| Scratch FCB base `DISK_FCB` (12 bytes, $E0DB–$E0E6) | $E0DB | own choice (free page-$E0 RAM after the INIT-scan scratch, clear of the disk ROM's SECTOR_BUF/FAT scratch $E2A0–$E4BF; used only transiently during a BLOAD) | sourced |
| FCB layout: +0 drive code, +1..+11 = 11-byte 8.3 name field | — | CP/M / MSX-DOS FCB layout (MSX2 Technical Handbook, BDOS conventions); exactly what disk/disk.asm `bdos_open` (`fat_find`) consumes at FCB+1 | sourced |
| Drive-code convention: 0 = default, 1 = A, 2 = B | — | CP/M / MSX-DOS FCB convention (MSX2 TH / MSX-DOS BDOS). Current disk `bdos_open` ignores FCB+0, so this is forward-compat only | sourced |
| 8.3 name field: 8-char name + 3-char ext, space-padded $20, UPPER-CASE | — | FAT / MSX-DOS 8.3 directory-entry name format (Microsoft FAT spec); upper-cased via the existing `upcase` helper (ASCII) | sourced |
| Drive letter: `"A:"`/`"B:"` case-insensitive; bare name defaults to drive A | — | own design (a `<letter>:` prefix selects the drive; default = A) | sourced |

**8.3 conversion policy (own design).** The filename is split on the FIRST `.`;
up to 8 chars before the dot become the name field (space-padded to 8), up to 3
after become the ext (space-padded to 3); no dot → all-name, ext = 3 spaces. The
filename ends at the closing `"`. Rather than silently truncate (which hides
typos), the parser **rejects** (via `load_error`) anything that does not fit 8.3:
more than 8 name chars, more than 3 ext chars, a second `.`, or an empty name
(e.g. `""`, `".EXT"`, `"A:"`). This is a deliberate, documented simplification.

**`do_disk_bload` reads the disk** (since the "Disk BLOAD execute" item — see the
next section). It hands the FCB at `DISK_FCB` to the disk ROM's `bdos_entry`
(C=`BDOS_OPEN`, DE=`DISK_FCB`) across slots. The `,R` (RUNFLAG) parse is shared
between the tape and disk paths via `parse_close_run`, and the exec handoff via
`load_handoff`.

**Functional validation (openMSX, `disk_probe_bload_fcb.py` in msx-preservation).**
On `C-BIOS_MSX1_BASIC` (the parse path is pure interpreter code that never touches
the disk hardware, so the plain machine is a reliable, valid target — the combined
`_DISK` machine's longer INIT-scan boot makes keystroke timing flaky), typing each
line into the zerobas REPL and reading the scratch FCB at the `do_disk_bload`
landmark (reached once the FCB is fully built): `BLOAD"A:TEST.BIN"` →
drive 1, name `TEST    BIN`; bare `BLOAD"TEST.BIN"` → drive 1 (default A), same
name; `BLOAD"B:HI.TXT"` → drive 2, name `HI      TXT`. Strictly an observation of
zerobas's own scratch RAM; no ROM is read or disassembled. Crunch byte-identical
and the four regression probes still pass; `BLOAD"CAS:",R` end-to-end still loads
+ hands off (`basic_probe_bload.py`).

## disk BLOAD execute (basic/bload.asm, basic/sysvars.inc; disk/disk.asm BDOS $1A)

`do_disk_bload` now performs a real disk load: it opens the file named in
`DISK_FCB` through the disk ROM's BDOS FCB layer, reads + verifies the on-disk
BSAVE header, streams the data bytes into RAM, closes the file, and shares the
`,R` exec handoff with the cassette path (`load_handoff`). Three integration
problems from earlier validation are solved here.

**A — reaching `bdos_entry` across slots.** The disk ROM's `bdos_entry` lives in
slot 3-1, so it is reached with an inter-slot `CALSLT` ($001C), not a near call.
The slot id comes from `DISKSLOT` (recorded by the INIT scan, previous section);
the entry *address* is read at load time from the SYSTEM sysvar `$F37D`
(`SYSTEM_VEC`) the disk INIT filled. `bdos_call` builds the slot word in RAM
(reusing the dead post-INIT `SCAN_IY`) and CALSLTs `bdos_entry`. Limitation
(documented): last-recorded external AB ROM wins — unambiguous on the combined
machine (one disk ROM), would need per-ROM tracking for multi-ROM setups.

**B — DTA in page-0 ROM under Disk BASIC.** The disk ROM's SeqRead copies each
128-byte record to the DTA, default $0080. Under the combined Disk-BASIC machine
page 0 is BIOS ROM, so $0080 is not writable and a SeqRead there silently fails.
BLOAD therefore issues BDOS **$1A Set-DTA** (`BDOS_SETDTA`) first, pointing the
DTA at its own writable page-3 buffer `DISK_DTA` ($E4C2, 128 bytes, clear of the
disk ROM's SECTOR_BUF/FAT scratch $E2A0–$E4C1 and of all basic RAM). disk.asm
gained the `$1A` dispatch + a settable `BDOS_DTA` variable (default $0080 for
MSX-DOS compatibility) — see disk/PROVENANCE.md §BDOS interface (Set-DTA $1A rows).

**C — disk BSAVE header is NOT the cassette format.** The on-disk BSAVE
binary-file header is **7 bytes** `[$FE][start:2 LE][end:2 LE][exec:2 LE]`
immediately followed by the raw data — no 10×$D0 block and no filename in the
file body (the name is the directory entry). This differs from the cassette
header (10×$D0 + 6-char name + the three addresses), which the TODO text wrongly
called "same format as tape" — corrected in disk/TODO.md. BLOAD verifies the
`$FE` marker (else `load_error`), parses start/end/exec into the existing
`CURPTR`/`ENDPTR`/`EXECPTR`, and loads bytes start..end inclusive like the tape
`load_loop`. Source for the header layout: **MSX-BASIC file formats** (MSX Wiki /
MSX Resource Center) — an allowed public MSX-BASIC language reference.

| Item | Value | Source | Status |
| --- | --- | --- | --- |
| BDOS call `Open` | $0F | MSX2 Technical Handbook / MSX-DOS BDOS call table | sourced |
| BDOS call `Close` | $10 | MSX2 TH / MSX-DOS BDOS call table | sourced |
| BDOS call `Sequential Read` | $14 | MSX2 TH / MSX-DOS BDOS call table | sourced |
| BDOS call `Set DTA Address` (DE = new DTA) | $1A | MSX2 TH / MSX-DOS BDOS call table | sourced |
| BDOS calling convention: C = call #, DE = FCB/pointer, A = result | — | MSX2 TH / MSX-DOS BDOS conventions | sourced |
| disk BSAVE header: `[$FE][start:2 LE][end:2 LE][exec:2 LE]` + raw data, start..end inclusive | — | MSX-BASIC file formats (MSX Wiki / MSX Resource Center), public language reference | sourced |
| `BSAVE_DISK_ID` marker | $FE | as above | sourced |
| `SYSTEM_VEC` (disk ROM's `bdos_entry` address, set by disk INIT) | $F37D | MSX2 TH work area / C-BIOS system variables | sourced |
| `CALSLT` (IYh = slot, IX = addr) for the inter-slot BDOS call | $001C | MSX Assembly Page BIOS call list / MSX2 TH | sourced |
| `DISK_DTA` 128-byte SeqRead buffer | $E4C2 | own choice (free page-3 RAM past the disk ROM's scratch top $E4C1; clear of all basic RAM) | sourced |
| Streaming state: `DTA_OFF` $E0E9, `DTA_VALID` $E0EA, `BDOS_RES` $E0EB | — | own choice (free page-$E0 RAM; dead outside a BLOAD). 128-byte records are not header-aligned with the data, so bytes are pulled one at a time via `disk_getbyte`, refilling via SeqRead when the record is exhausted | sourced |

**Divergences / judgment calls.**
- The byte-at-a-time `disk_getbyte` over a 128-byte SeqRead record handles the
  non-record-aligned 7-byte header + data cleanly; EOF (SeqRead A≠0) mid-stream
  before reaching `end` takes `load_error`.
- On any error after Open (bad `$FE`, short read), `disk_load_err` closes the file
  before erroring — no leaked open file.
- `DISKSLOT_OK` = 0 (no disk ROM found by the INIT scan) makes `do_disk_bload`
  fall straight to `load_error`, so the parser-only `disk_probe_bload_fcb.py` on
  the plain (diskless) machine still reaches its FCB-read landmark and bails.

**Functional validation (openMSX, `disk_probe_bload_disk.py` in msx-preservation).**
On `C-BIOS_MSX1_BASIC_DISK` with `-diska disk/test720.dsk` (which now carries a
real BSAVE `PROG.BIN`: header `$FE` start=$C000 end=$C031 exec=$C000; the payload
writes $5A→$D000, self-loops at `JR $` $C010, then a 0..31 data tail):
`BLOAD"A:PROG.BIN",R` — the data bytes land byte-identical at $C000..$C031, PC
reaches the $C010 landmark (the `,R` handoff fired) and ($D000)=$5A (the loaded
code executed); `BLOAD"A:PROG.BIN"` (no `,R`) — the same bytes load but ($D000)
stays at its pre-poisoned sentinel $A5 (no exec). The read path is the same one
`disk_probe_dskio.py` confirms byte-identical to the CF-3300 reference. Crunch
byte-identical and the four regression probes still pass; `disk_probe_init.py`
and `disk_probe_bload_fcb.py` still pass; `BLOAD"CAS:",R` end-to-end still loads
+ hands off.

## disk LOAD — LOAD"filename"[,R] (basic/cload.asm, basic/bload.asm, basic/sysvars.inc)

The disk analogue of `LOAD"CAS:"`/`CLOAD`: where the cassette path loads a
tokenised BASIC *program* off tape (`do_tape_prog`), this loads the same kind of
program from a FAT12 disk file through the disk ROM's BDOS FCB layer. It is the
program-load counterpart to disk BLOAD (which loads a BSAVE *binary image* into
raw RAM); the two on-disk formats — and their marker bytes — are distinct.

**Device dispatch (do_load).** `do_load` now peeks the device string
NON-DESTRUCTIVELY, exactly like `do_bload`: a full `"CAS:"` prefix selects the
unchanged cassette path (`do_load_fn`/`do_tape_prog`), anything else falls
through to the disk path (a name like `"CASETTE"` is a disk name, not tape). The
cassette-only `do_cload` (`CLOAD`) is untouched. The disk path restores the
filename start from the stack (HL is mid-`"CAS:"` compare and not trustworthy),
parses the FCB via the shared `parse_disk_fcb`, then `parse_close_run` (so
`LOAD"A:PROG.BAS",R` sets `RUNFLAG`), calls `disk_prog_load`, and — iff `RUNFLAG`
— `jp run_prog` to RUN the freshly loaded program (LOAD",R" = load and run,
standard MSX behaviour). No new token: `LOAD` already exists as `LOAD_TOKEN`
($B5), and the disk filename is verbatim ASCII in the crunch stream — the
tokeniser is untouched and crunch stays byte-identical (Philips VG-8020).

**Shared FCB parse (`parse_disk_fcb`).** The drive-letter + 8.3-name parse that
was inline in `do_bload`'s `is_disk` is factored into `parse_disk_fcb`
(basic/bload.asm) and reused by BOTH BLOAD's and LOAD's disk paths, so the
`"A:"/"B:"`-prefix + `build_83_name` logic lives in one place.

**On-disk tokenised-BASIC format ($FF marker).** A BASIC program SAVEd to disk in
the default (tokenised, non-`,A`) form is a single leading marker byte **`$FF`**
(`BASIC_DISK_ID`) immediately followed by the in-memory program image — the SAME
line-link chain `do_tape_prog` reads: `[link:2 LE][lineno:2 LE][tokens…][00]` per
line, terminated by a `$0000` link word. This is DISTINCT from the BSAVE binary's
`$FE` disk marker (the two file kinds are told apart by their leading byte).
ASCII-saved BASIC (`SAVE…,A`) has no `$FF` and is plain text — out of scope; only
the `$FF` tokenised form is loaded. Source: **MSX-BASIC file formats** (MSX Wiki /
MSX Resource Center, an allowed public MSX-BASIC language reference — the same
class the `$FE` disk-BSAVE marker was sourced from). `disk_prog_load` verifies the
`$FF` marker on load (mismatch ⇒ `load_error`).

**`disk_prog_load`.** A reusable routine (callable by the future `RUN"filename"`):
checks `DISKSLOT_OK` (else `load_error`); Set-DTA→`DISK_DTA`; Open (require A=$00,
else `load_error`); reads the first byte and requires `BASIC_DISK_ID` ($FF); then
streams the line-link image into the program store at `TXTBASE` via `disk_getbyte`
— mirroring `do_tape_prog`'s `ctp_line`/`ctp_body`/`ctp_done` (store link word,
$0000 link ⇒ done, otherwise store link + lineno + token-body-to-`$00`; write the
`$0000` end marker; set `PRGEND`; `TXTTAB`=`TXTBASE`; `call relink`) — but sourcing
bytes from `disk_getbyte` and closing the file (BDOS Close) at the end. It leaves
a loaded, relinked program and returns; the `,R`/run decision stays in the caller.
The disk reader has BOTH a real EOF (`disk_getbyte` CF) and the `$0000` end-link:
the `$0000` link is the authoritative end (stop + close there); an EOF mid-line is
a truncated/corrupt file ⇒ `load_error` (`dpl_err`, after closing the file). A
store overflow past `TXTMAX` mirrors `ctp_oom` (`dpl_oom`: close, `new_prog`,
"out of memory", `$CC` landmark).

| Item | Value | Source | Status |
| --- | --- | --- | --- |
| `BASIC_DISK_ID` (on-disk tokenised-BASIC marker) | $FF | MSX-BASIC file formats (MSX Wiki / MSX Resource Center), public language reference | sourced |
| in-memory line-link image after the marker: `[link:2 LE][lineno:2 LE][tokens…][00]` per line, `$0000` end-link | — | same line-link layout as program.asm / do_tape_prog (allowed-source / oracle-confirmed) | sourced |
| `LOAD` statement token (reused, no new token) | $B5 | oracle-confirmed via `basic_probe_crunch.py` (already sourced, §Phase 1 cassette load) | sourced |

**Divergences / judgment calls.**
- **Streamed body store is LENGTH-DRIVEN (shared design with `do_tape_prog`).**
  A line's token body legitimately contains `$00` bytes — the two-byte int token
  `$1C lo hi`, the `&H`/`&O` constants `$0C/$0B lo hi`, and line-number refs all
  carry operand `$00`s (e.g. `&H7B` → `$0C $7B $00`, `&HD100` → `$0C $00 $D1`).
  An earlier version copied each body until the FIRST `$00`, mistaking such an
  operand byte for the line terminator and truncating the line; this was fixed
  (see *§disk LOAD — embedded-`$00` length-driven body copy* below). Both
  `dpl_body` and `do_tape_prog`'s `ctp_body` now derive each line's body length
  from the saved link-word differences and copy EXACTLY that many bytes, so
  embedded `$00`s round-trip. The fixture file `PROG2.BAS`
  (`10 POKE &HD100,&H7B`, two interior `$00`s) is the regression that pins this;
  `PROG.BAS` keeps the no-embedded-`$00` baseline (`123` as the 1-byte `INT1`
  form `$0F $7B`) so the two fixtures bracket the fix.
- LOAD",R" runs via `jp run_prog` (program.asm) after `disk_prog_load` returns;
  plain LOAD returns to the REPL. `disk_prog_load` is left cleanly callable by the
  next item's `RUN"filename"` (which adds only the run-after-load decision).
- On any error after Open (wrong marker, mid-line EOF), `dpl_err` closes the file
  before `load_error` — no leaked open file. `DISKSLOT_OK`=0 (no disk ROM) makes
  `disk_prog_load` fall straight to `load_error`.

**Functional validation (openMSX, `disk_probe_load_disk.py` in msx-preservation).**
On `C-BIOS_MSX1_BASIC_DISK` with `-diska disk/test720.dsk` (which now carries a
real tokenised `PROG.BAS`: `$FF` marker + the line-link image of `10 POKE
&HD002,123`, byte-identical to the typed-in crunch): `LOAD"A:PROG.BAS"` rebuilds
the relinked program at `$8001` byte-identical to the expected image and does NOT
auto-run (the `$D002` landmark stays its sentinel); `LOAD"A:PROG.BAS",R` rebuilds
the same store AND runs it (`($D002)`=$7B, the POKEd landmark). Crunch stays
byte-identical; the four regression probes, `basic_probe_cload.py`,
`basic_probe_bload.py`, `disk_probe_init.py`, `disk_probe_bload_fcb.py`,
`disk_probe_bload_disk.py`, and the `disk_probe_dskio.py` differential (vs the
CF-3300 reference) all still pass.

## disk RUN — RUN"filename" (basic/cload.asm, basic/interp.asm)

A thin wrapper: `RUN"A:name"` (and `"B:"`/bare) loads a tokenised BASIC program
from disk and then RUNs it — i.e. LOAD then RUN, with the run implicit (there is
no `,R` option; running is the whole point). It reuses the LOAD plumbing
verbatim (`parse_disk_fcb` + `disk_prog_load`) and adds nothing to the load
logic — only the always-run decision.

**Dispatch path.** `RUN` already has a token, `RUN_TOKEN` ($8A). A *bare* `RUN`
or `RUN <lineno>` typed in direct mode is handled earlier as raw ASCII in
`basic/program.asm`'s `dl_cmd` (`is_cmd` matches "RUN" only when followed by a
delimiter — end / space / colon) and runs the stored program from the start
without ever reaching the executor. But `RUN"file"` has a `"` right after RUN
(not a delimiter), so `dl_cmd` does NOT match it: it falls through to
tokenise+exec, crunching as `RUN_TOKEN` followed by the quoted filename kept
verbatim as ASCII (oracle-confirmed below). To handle that token at run time, a
`RUN_TOKEN` case was added to the executor's statement dispatch in
`basic/interp.asm` (next to `LOAD_TOKEN`→`ex_load`): `RUN_TOKEN`→`ex_run`→
`do_run`. This is purely additive and does not disturb the direct-mode bare-RUN
path (that path never produces a `RUN_TOKEN` reaching the executor).

**`do_run` (basic/cload.asm).** On entry HL points past `RUN_TOKEN`.
`skip_spaces`, then dispatch on the next char:
- `"` (a quoted filename) → `RUN"A:name"`: `inc hl` past the quote, `call
  parse_disk_fcb` (build `DISK_FCB`; on a malformed drive/name it routes to
  `load_error` itself), `call parse_close_run` (consume the closing quote — and
  tolerate a stray `,R` harmlessly; `CF`→`load_error`), `call disk_prog_load`
  (the SAME reusable load `LOAD"name"` uses), then `jp run_prog`. Net effect:
  load the tokenised program, then run it. This mirrors `do_load`'s disk path
  exactly, minus the `RUNFLAG` test — RUN always runs.
- anything else (a bare tokenised `RUN`, or `RUN<lineno>` which the tokeniser
  stored as `RUN_TOKEN` + a line-ref token) → `jp run_prog`: run the stored
  program from the start, matching the existing bare-RUN semantics (a line
  number is ignored, exactly as the `dl_cmd` path ignores it). A simple
  defensive branch; in practice bare RUN is consumed by `dl_cmd` and rarely
  reaches here.

No new keyword token (`RUN_TOKEN` already exists) and the disk filename is
verbatim ASCII in the crunch stream, so the tokeniser is untouched and crunch
stays byte-identical (Philips VG-8020).

| Item | Value | Source | Status |
| --- | --- | --- | --- |
| `RUN` statement token (reused, no new token) | $8A | oracle-confirmed via `basic_probe_crunch.py` | sourced |
| `RUN"A:PROG.BAS"` crunch = `8A 22 41 3A 50 52 4F 47 2E 42 41 53 22 00` (`RUN_TOKEN` + the quoted filename verbatim, no line-number conversion) | — | oracle-confirmed byte-identical vs Philips VG-8020 (`basic_probe_crunch.py`) | sourced |
| load logic (FCB parse, `$FF` marker, line-link stream) | — | reused unchanged from disk LOAD (§disk LOAD) — no duplication | sourced |

**Functional validation (openMSX, `disk_probe_run_disk.py` in msx-preservation).**
On `C-BIOS_MSX1_BASIC_DISK` with `-diska disk/test720.dsk` (carrying the real
tokenised `PROG.BAS`: `$FF` marker + the line-link image of `10 POKE &HD002,123`):
`RUN"A:PROG.BAS"` rebuilds the relinked program at `$8001` byte-identical to the
expected image (it LOADED) AND runs it — the POKEd landmark `($D002)`=$7B (it
RAN). Both assertions pass. Crunch stays byte-identical (the new
`RUN"A:PROG.BAS"` crunch case PASSes alongside all existing cases); the four
regression probes (controlflow/loops/data/statements), `disk_probe_init.py`,
`disk_probe_bload_fcb.py` (landmark refreshed for the shifted `do_disk_bload`
address), `disk_probe_bload_disk.py`, `disk_probe_load_disk.py`, and the
`disk_probe_dskio.py` differential (vs the CF-3300 reference) all still pass.

## disk LOAD — embedded-`$00` length-driven body copy (basic/cload.asm, basic/sysvars.inc)

A tokenised line's token body legitimately contains `$00` bytes: the two-byte
int token `$1C lo hi`, the `&H`/`&O` constant tokens `$0C`/`$0B lo hi`, and the
line-number reference tokens all carry operand `$00`s — e.g. `256` → `$1C 00 01`,
`&HD100` → `$0C 00 D1`, `&H7B` → `$0C 7B 00`. The original streamed program
readers (`do_tape_prog`'s `ctp_body` and `disk_prog_load`'s `dpl_body`) copied a
line's body until the FIRST `$00`, treating that byte as the line terminator —
so any saved program with an embedded `$00` operand was **truncated mid-line on
load**, corrupting it. This was a real bug on **both** tape LOAD/`CLOAD` and disk
LOAD/RUN, masked only because the test fixtures deliberately avoided embedded
`$00`.

**Fix: length-driven copy.** The line boundary is not the first `$00`; it is
defined by the link words. In the streamed line-link image
(`[link:2 LE][lineno:2 LE][tokens…][00]` per line) the saved link words are the
saving machine's consecutive absolute line addresses, so a line's full length is
`(this line's link) − (previous line's link)` and its body length is that minus
the 4-byte link+lineno header. Both `ctp_body` and `dpl_body` now:

1. read the 2-byte link word `L_n` (`$0000` ⇒ end of program, unchanged);
2. compute `body_len = L_n − A_n − 4`, where `A_n` is the previous line's link
   word, held in new RAM scratch `CLINK` and seeded with `TXTBASE` for the first
   line (`A_0` = the saving machine's text base, assumed `== TXTBASE` $8001, the
   MSX disk-BASIC base — true for every realistic saved file and the fixtures);
3. store the link word + 2-byte line number verbatim, then copy EXACTLY
   `body_len` body bytes — embedded `$00`s and all — landing precisely on the
   next link word.

`relink` (program.asm) then recomputes the links exactly as before; it already
walked lines with the token-aware `skip_to_eol` (which steps `$0C`/`$1C`/… and
their operand bytes), so relink never had this bug — only the streamed *copy*
did. The existing `TXTMAX` bounds checks, the `$0000` end-of-program detection,
and the disk reader's real-EOF handling (`dpl_err`, file close on error) are all
preserved; the per-line body length is guarded on the Z80 stack across the
register-trashing `TAPIN` / `disk_getbyte` reads (`ctp_err_pop`/`ctp_oom_pop`,
`dpl_err_pop`/`dpl_oom_pop` drop it before the shared error paths so the stack
stays balanced). The tape and disk loops stay parallel mirrors (different byte
source + error handling), matching the existing structure.

| Item | Value | Source | Status |
| --- | --- | --- | --- |
| Line boundary defined by saved link-word differences (`body_len = L_n − A_n − 4`), NOT the first `$00` | — | the line-link layout (program.asm, already sourced): each link is the saving machine's absolute address of the next line | sourced |
| First line's predecessor address `A_0` = saving machine's text base, assumed `== TXTBASE` ($8001) | — | **own design** — only the first line is base-dependent (all later lines use base-independent link differences); $8001 is the MSX disk-BASIC text base and what the fixtures/relink use. A saved file from a different text base would mis-size only its first line; documented assumption | quarantined |
| `CLINK` ($E02D) — previous link word / current line's saving-machine start address (2) | — | own choice (free page-3 RAM, the 2-byte gap after `CLPTR`) | sourced |
| Length-driven `ctp_body`/`dpl_body` copy algorithm; stack-guarded body counter | — | **own code**; not derived from any disassembly | sourced |

**Functional validation (openMSX).** Build is clean (`basic.rom` 16384 bytes, 0
warnings); the tokeniser is untouched so the crunch stays byte-identical. New
regression `disk_probe_load_embedded_nul.py` (in msx-preservation) loads
`PROG2.BAS` (`10 POKE &HD100,&H7B`, body `98 20 0C 00 D1 2C 0C 7B 00 00` with two
interior `$00`s) and asserts the store at `$8001` is byte-identical to the
relinked image for both `LOAD"A:PROG2.BAS"` (no auto-run) and `LOAD…,R` (RUN
fires the post-`$00` POKE, `($D100)`=$7B) — a pre-fix load truncated at the first
interior `$00` and could never reach that POKE. The existing
`disk_probe_load_disk.py`, `disk_probe_run_disk.py`, `disk_probe_bload_disk.py`
and the four controlflow/loops/data/statements regression probes all still pass.
The matching `do_tape_prog` fix is exercised by the same length-driven path;
on-device end-to-end tape load now also works — the earlier apparent block was a
`ctp_line` link-word register clobber (`TAPIN`/`disk_getbyte` return `C=0`), fixed
alongside the disk `dpl_line` clobber (§Phase 1 cassette load, updated).

## SAVE / BSAVE statement tokens — oracle-locked (tokens + IMPLEMENTED handlers)

> **Implemented** (see *§disk SAVE / BSAVE* below for the handler write side).
> The two crunch tokens `$D0` (BSAVE) / `$BA` (SAVE) are now `equ`'d in
> `basic/sysvars.inc`, added to `kwtable`, dispatched in `interp.asm`, and the
> `do_bsave` / `do_save` handlers live in `basic/save.asm`. The crunch is now
> **byte-identical** to the VG-8020 (the four `bsave…`/`save…` lines are PERMANENT
> cases in `basic_probe_crunch.py`'s `CRUNCH_ONLY`, ALL PASS). This section remains
> as the **token oracle-lock evidence**; the paragraphs below that say "no handler
> yet" describe the PRE-implementation state and are kept for the provenance trail.

This section **oracle-LOCKS the tokeniser bytes** for both verbs from the
reference VG-8020's crunch buffer. It documented the crunch bytes; the handler
write side is documented in *§disk SAVE / BSAVE*.

This is the same clean-room method that locked `BLOAD`/`CLOAD`/`LOAD`/`RUN`
(§first light, §Phase 1 cassette load, §disk RUN) and POKE/PEEK/VPOKE/VPEEK
(§REM/POKE/PEEK, §Phase 1 memory / I-O access): the token byte is **OBSERVED** from
the reference VG-8020's crunch buffer KBUF and cross-checked against the **MSX2
Technical Handbook Table 2.20** / MSX Assembly Page token table. No disassembly was
read; the reference ROM is a black box (identical line in, observed crunch out).

**Oracle (`basic_probe_crunch.py`, scratch CRUNCH_ONLY test lines — the
freeze-`bload"cas:",r` LEADS so the SAVE/BSAVE body is crunched but never executed,
and the probe was RESTORED to pristine after; never committed).** Each line below
is shown with its full crunch; the leading `CF 22 63 61 73 3A 22 2C 52 3A` is the
prepended `BLOAD"CAS:",R:` and the SAVE/BSAVE body follows it. The Philips VG-8020
reference crunches:

- `bsave"cas:name",&hc000,&hc031,&hc000`
  → `… 52 3A` **`D0`** `22 63 61 73 3A 6E 61 6D 65 22` `2C 0C …` —
  **BSAVE = `$D0`** (single-byte statement token), then the quoted filename
  `"cas:name"` verbatim, `,` (`$2C`), then the `&H` addresses.
- `bsave"a:prog.bin",&hc000,&hc031`
  → `… 52 3A` **`D0`** `22 61 3A 70 72 6F 67 2E 62 69 6E 22` `2C 0C …` —
  same `$D0`, disk filename `"a:prog.bin"` verbatim.
- `bsave"x",&hc0c1,&hc031,&hc0c2` (short name + non-zero-low-byte addresses so the
  48-byte dump / terminator scan captures the FULL tail)
  → `… 52 3A` **`D0`** `22 78 22` `2C` `0C C1 C0` `2C` `0C 31 C0` `2C` `0C C2 C0` `00`
  — `$D0` `"x"` then **three** comma-separated `&H` addresses, each
  `$0C,<value16 LE>` (HEX_TOKEN, the same encoding as elsewhere — see §Step A),
  commas verbatim `$2C`, `$00` terminator.
- `bsave"x",&hc0c1,&hc031`
  → `… 52 3A` **`D0`** `22 78 22` `2C` `0C C1 C0` `2C` `0C 31 C0` `00`
  — the two-address (no-exec) form: `$D0` `"x"` `,` start `,` end `$00`.
- `save"cas:name"`
  → `… 52 3A` **`BA`** `22 63 61 73 3A 6E 61 6D 65 22` `00` —
  **SAVE = `$BA`** (single-byte statement token), then `"cas:name"` verbatim, `$00`.
- `save"a:prog",a`
  → `… 52 3A` **`BA`** `22 61 3A 70 72 6F 67 22` `2C` **`41`** `00` —
  same `$BA`, `"a:prog"` verbatim, `,` (`$2C`), then the ASCII-save flag as the
  **upcased letter `A` = `$41` kept VERBATIM** (NOT a token), `$00`.

**Decoded result.**

| Verb | Statement token (observed) | Form | Argument crunch (observed) |
|------|----------------------------|------|----------------------------|
| `BSAVE` | **`$D0`** | single-byte statement token (NOT `$FF`-prefixed) | `"filename"` verbatim ASCII (like BLOAD); each `&H` address → `$0C,<value16 LE>` (HEX_TOKEN); commas verbatim `$2C`; optional 3rd (exec) address present or absent |
| `SAVE` | **`$BA`** | single-byte statement token (NOT `$FF`-prefixed) | `"filename"` verbatim ASCII; optional `,A` → comma `$2C` + the letter `A` (`$41`) as **upcased verbatim ASCII**, NOT a special token (exactly how zerobas already upcases option letters like BLOAD's `,R`) |

**Cross-check (MSX2 TH Table 2.20 / MSX Assembly Page token table).** `$BA` = SAVE
and `$D0` = BSAVE are the documented statement-token values; both observations
agree with the table. Both are **single-byte statement tokens** — the task's "could
BSAVE be a `$FF`-prefixed function-style token like PEEK/VPEEK?" question resolves
**NO**: BSAVE/SAVE crunch like the other *statements* (POKE `$98`, VPOKE `$C6`,
OUT `$9C`, CLOAD `$9B`, LOAD `$B5`, RUN `$8A`), not like the `$FF`-prefixed
*functions* (PEEK `$FF $97`, VPEEK `$FF $98`, INP `$FF $90`).

**Surprise / note — `$D0` is dual-use across two distinct namespaces.** The BSAVE
*crunch token* `$D0` is the SAME byte value as the **cassette binary-file id byte**
`BIN_ID $D0` (§first light: "Binary-file id byte | $D0", the 10× header byte of a
tape BSAVE image). These do NOT collide: one is a keyword token in the crunch line
buffer (KBUF/TOKBUF), the other is a data byte on tape — different namespaces,
different consumers. (Likewise the on-disk BSAVE marker is `$FE` and the on-disk
tokenised-BASIC marker is `$FF`, both already sourced in §disk BLOAD execute /
§disk LOAD — those are file-format markers, again unrelated to the `$D0`/`$BA`
*crunch* tokens locked here.) The interpreter agent should keep the keyword-token
constants (`$D0`/`$BA`) and the file-id/marker constants (`$D0`/`$FE`/`$FF`)
clearly named so the coincidence is not mistaken for a relationship.

**What zerobas does today (why the crunch is not yet byte-identical).** With no
`SAVE`/`BSAVE` in `kwtable`, zerobas's tokeniser keeps the keyword as verbatim
ASCII: it crunches `bsave"x",…` to `… 42 53 41 56 45 22 78 22 …` (`BSAVE` =
`42 53 41 56 45`) and `save"…"` to `… 53 41 56 45 22 …` (`SAVE` = `53 41 56 45`),
where the reference emits the single `$D0` / `$BA` token. So a scratch crunch run
shows these four lines as **FAIL** (zb verbatim-ASCII vs ref token) — that is the
EXPECTED pre-implementation state, NOT a regression: the existing committed test
set (`LINES` / `CRUNCH_ONLY`) is unchanged and still **ALL PASS**, and these
SAVE/BSAVE probe lines were scratch-only and removed (probe restored to pristine).
Once the interpreter agent adds `$D0`/`$BA` to `kwtable` + handlers, the crunch
will become byte-identical and these lines move into the committed probe set
(`basic_probe_crunch.py` and/or a dedicated `basic_probe_save.py`, mirroring how
`basic_probe_cload.py` locked CLOAD/LOAD).

**Implementation guidance for the later interpreter agent (NOT done here).** When
the WRITE statements are built, add to `basic/sysvars.inc` near the other load
tokens:

    SAVE_TOKEN      equ     $BA     ; SAVE "dev:name"[,A]  (oracle-confirmed; PROVENANCE §SAVE/BSAVE)
    BSAVE_TOKEN     equ     $D0     ; BSAVE "dev:name",start,end[,exec] (oracle-confirmed; PROVENANCE §SAVE/BSAVE)

(These equs are intentionally **NOT** added now: an unused equ would trip pasmo's
"never used" warning and `basic.rom` must stay 0-warnings / byte-identical — see
the matching commented pointer in `basic/sysvars.inc`.) The argument parse mirrors
the existing patterns: the filename parses like BLOAD's `"CAS:"`/`"A:"` device
string (`do_bload`/`parse_disk_fcb`), the `&H` addresses evaluate through the
ordinary expression evaluator (the `$0C` HEX_TOKEN decode in `ev_f`, §Step A), the
commas are statement-internal separators, and SAVE's `,A` is a one-letter
ASCII-save flag (the `$41` is just the upcased option letter, parsed like BLOAD's
`,R` RUNFLAG). The on-disk SAVE/BSAVE *file formats* the handler must write are
already sourced in §disk BLOAD execute (`$FE` BSAVE header
`[$FE][start:2 LE][end:2 LE][exec:2 LE]` + raw data) and §disk LOAD (`$FF`
tokenised-BASIC marker + line-link image); the cassette SAVE/BSAVE formats in
§first light (10× id byte + 6-char name + the three addresses). This section adds
ONLY the missing piece: the two crunch tokens.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `BSAVE` statement token | `$D0` (single-byte; NOT `$FF`-prefixed) | OBSERVED in VG-8020 KBUF via `basic_probe_crunch.py` (scratch, restored); cross-checks MSX2 TH Table 2.20 | sourced |
| `SAVE` statement token | `$BA` (single-byte; NOT `$FF`-prefixed) | OBSERVED in VG-8020 KBUF via `basic_probe_crunch.py` (scratch, restored); cross-checks MSX2 TH Table 2.20 | sourced |
| BSAVE filename kept verbatim ASCII after the token (like BLOAD's `"CAS:"`/`"A:"`) | — | oracle (`bsave"cas:name"…`/`bsave"a:prog.bin"…` crunch) | sourced |
| BSAVE address args: each `&H` address → `$0C,<value16 LE>` (HEX_TOKEN), commas verbatim `$2C`; 2-address (start,end) and 3-address (start,end,exec) forms both observed | — | oracle (`bsave"x",&hc0c1,&hc031[,&hc0c2]` crunch); the `$0C` HEX_TOKEN is already sourced (§Step A) | sourced |
| SAVE filename kept verbatim ASCII after the token | — | oracle (`save"cas:name"`/`save"a:prog"` crunch) | sourced |
| SAVE `,A` ASCII-save flag crunches as comma `$2C` + the letter `A` (`$41`) upcased VERBATIM — NOT a token | — | oracle (`save"a:prog",a` → `… BA … 2C 41 00`); same upcasing as BLOAD's `,R` option letter | sourced |
| `$D0` BSAVE crunch token vs `$D0` cassette binary-file id (§first light): same byte, DIFFERENT namespaces (keyword token vs tape data byte) — not a collision | — | observed (both already sourced); cross-namespace coincidence noted | sourced |
| `SAVE_TOKEN`/`BSAVE_TOKEN` equs in basic/sysvars.inc | **now added + USED** (`$BA`/`$D0`); kwtable + dispatch + handlers live (*§disk SAVE / BSAVE*) | implemented | sourced |

No quarantined items: both token bytes are oracle-OBSERVED and Table-2.20
cross-checked, exactly like every other load/store token in this log. The only
own-design choices are in the handler (file-format writing, already pre-sourced in
the disk read sections), documented in *§disk SAVE / BSAVE* below.

## disk SAVE / BSAVE — write side (basic/save.asm, basic/interp.asm, basic/sysvars.inc; disk/disk.asm BDOS $15/$16)

The WRITE complement of *§disk BLOAD execute* (BSAVE binary) and *§disk LOAD*
(tokenised BASIC). `do_bsave` / `do_save` (basic/save.asm) crunch from the
oracle-locked `$D0` / `$BA` tokens (*§SAVE / BSAVE statement tokens*), parse the
device string + arguments, and write a real FAT12 file through the disk ROM's BDOS
FCB write subset (Create $16 / Sequential Write $15 / Close $10), reusing the read
side's plumbing (`parse_disk_fcb`, `bdos_call`, `DISK_DTA`, `load_error`).

- **`BSAVE"A:F",start,end[,exec]`** writes the on-disk BSAVE binary
  `[$FE][start:2 LE][end:2 LE][exec:2 LE]` then `RAM[start..end]` inclusive. The
  `$FE` header layout is already sourced in *§disk BLOAD execute* (the exact format
  the read side consumes). `start`/`end`/`exec` are evaluated through the ordinary
  expression evaluator (`eval`, basic/expr.asm), so `&H` addresses decode via the
  `$0C` HEX_TOKEN like everywhere else. **Default exec = start** when the third arg
  is omitted (own-design default, matching the read side and MSX BASIC — a BSAVE
  with no entry point runs from its load address; *oracle-confirmed by the
  round-trip* in `disk_probe_save.py`: `BSAVE…,&HC000,&HC011` with no `,exec`, then
  `BLOAD…,R`, jumps to `$C000`).
- **`SAVE"A:F"`** writes the on-disk tokenised-BASIC file `[$FF]` then the
  in-memory line-link program image `TXTBASE..PRGEND+1` inclusive (`PRGEND` points
  at the `$0000` end-of-program marker, so the last image byte is `PRGEND+1` — the
  high byte of the end-link). The `$FF` marker + line-link format are already
  sourced in *§disk LOAD*. This is exactly the byte image `disk_prog_load` /
  `do_tape_prog` read back, so a SAVE→LOAD/RUN round-trips byte-identically (oracle
  `disk_probe_save.py`).

**Device dispatch — DISK or CAS:.** Both verbs now **device-dispatch** on the
prefix: a `"CAS:"` device routes to the cassette write path (*§tape SAVE / CSAVE*
below), and a bare name / `"A:"`/`"B:"` goes to the disk path above. The prefix is
peeked **non-destructively** (`dev_cas`, exactly like `do_bload`'s CAS: peek, so
`"CASE.BIN"` falls through to disk cleanly). This replaces the earlier
`reject_cas → load_error` descope (tape write is now implemented).

**SAVE `,A` ASCII form — out of scope (own-design descope).** `SAVE"name",A`
(detokenised ASCII save) takes `load_error`: any comma after the SAVE filename is
rejected (so `,A` and any other flag are unsupported). Reproducing the ASCII
detokeniser output byte-for-byte is a larger task; the default tokenised save is
the supported form. Documented limitation.

**Shared disk-write helper (own design, mirrors the read side).**
`disk_write_begin` (require `DISKSLOT_OK`; Set-DTA $1A → `DISK_DTA`; Create $16) /
`disk_putbyte` (fill the 128-byte `DISK_DTA` record, Sequential Write $15 when full,
reset the index) / `disk_write_end` (zero-pad + flush the partial final record,
Close $10) factor the Create+accumulate+Close cycle used by both handlers — the
write analogue of how the read side shares `disk_getbyte` / `bdos_call`. `DSV_OFF`
($E0EC) is the record fill index; `DSV_PTR` ($E0ED) / `DSV_END` ($E0EF) drive the
source walk; all in the free page-$E0 scratch gap, collision-checked clear of the
read-side `DTA_OFF`/`DTA_VALID`/`BDOS_RES` and the disk ROM's own scratch.

**Record-rounded file size (BDOS property, not a handler choice).** The disk ROM's
Sequential Write writes a FIXED 128-byte record from the DTA and Close stamps the
directory size as `records × 128` (disk/disk.asm `bdos_seqwrite` / `wrbytes_add_
recsize` — out of scope, byte-identical). So a saved file's length is rounded UP to
the next 128-byte boundary with trailing zero-fill. This is **benign for both
formats**: the BSAVE reader is bounded by the `end` address in the `$FE` header and
the tokenised reader stops at the `$0000` end-link — neither reads into the pad. A
real MSX-DOS cross-read sees the same record-rounded size (a property of this BDOS
implementation; documented in disk/PROVENANCE.md).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| BSAVE/SAVE statement dispatch (`$D0`→`do_bsave`, `$BA`→`do_save`) | — | oracle-locked tokens (*§SAVE / BSAVE statement tokens*) | sourced |
| on-disk BSAVE binary `[$FE][start][end][exec]` + `RAM[start..end]` | `$FE` | MSX-BASIC file formats (already sourced, §disk BLOAD execute) | sourced |
| on-disk tokenised-BASIC `[$FF]` + line-link image `TXTBASE..PRGEND+1` | `$FF` | MSX-BASIC file formats (already sourced, §disk LOAD) | sourced |
| BDOS Create / Sequential Write / Close call numbers | $16 / $15 / $10 | MSX2 TH / MSX-DOS BDOS call table | sourced |
| default exec address = start when `,exec` omitted | — | own design (matches read side / MSX BASIC); oracle round-trip `disk_probe_save.py` | sourced |
| `"CAS:"` device dispatches to the cassette write path (was `reject_cas`→`load_error`) | — | implemented (*§tape SAVE / CSAVE*); non-destructive `dev_cas` peek | sourced |
| SAVE `,A` ASCII-save form rejected (`load_error`) | — | own-design descope (ASCII detokeniser out of scope) | quarantined |
| `DSV_OFF`/`DSV_PTR`/`DSV_END` write-stream scratch | $E0EC/$E0ED/$E0EF | own choice (free page-$E0 RAM, collision-checked) | sourced |
| record-rounded file size (128-byte pad) | — | disk ROM BDOS property (disk/disk.asm, out of scope); benign for both readers | sourced |

Oracle confirmation: `disk_probe_save.py` (msx-preservation) — three round-trips on
`C-BIOS_MSX1_BASIC_DISK` against a /tmp writable copy of test720.dsk: BSAVE→BLOAD
(data byte-identical), BSAVE→BLOAD,R (default-exec handoff fires at the JR$
landmark, `$D000`=`$5A`), SAVE→NEW→RUN (relinked store byte-identical + program
ran). Crunch byte-identical via `basic_probe_crunch.py` (the four `bsave…`/`save…`
CRUNCH_ONLY cases). The MSX-DOS cross-read (the disk ROM's write side proven valid
to genuine MSX-DOS) is already established for the BDOS layer by
`disk_probe_fwrite.py` (disk/PROVENANCE.md §FAT12 write-back); these handlers only
drive that proven BDOS write subset.

## tape SAVE / CSAVE — cassette write side (basic/save.asm, basic/interp.asm, basic/sysvars.inc)

The WRITE complement of *§Phase 1 cassette load* (CLOAD/LOAD"CAS:"). `CSAVE"name"`,
`SAVE"CAS:name"` (both tokenised) and `BSAVE"CAS:name",start,end[,exec]` (binary)
write a real cassette file through the zerobas-tape **write** signal layer
(`TAPOON $00EA` / `TAPOUT $00ED` / `TAPOOF $00F0`, already implemented in
`tape/tape.asm`, reached via the cassette BIOS vectors). Same two-block cassette
file layout the read side consumes and that `cas_encode.py` (`build_cas` /
`build_cas_basic`) documents:

- **Header block** (`TAPOON` long): the file-type id ×10 — `$D3` for tokenised
  (CSAVE / SAVE"CAS:"), `$D0` for binary (BSAVE) — then the 6-char space-padded
  filename; `TAPOOF`.
- **Data block** (`TAPOON` short): for binary, `start`/`end`/`exec` (LE) then
  `RAM[start..end]`; for tokenised, the line-link program image `TXTBASE..PRGEND+1`
  (ending in the `$0000` end-link). `TAPOOF`. No `$FE`/`$FF` markers — those are
  disk-only; on tape the `$D0`/`$D3` header-block id is the type tag.

**Register hygiene (the load-side lesson applied).** The cassette BIOS calls
clobber every register (`TAPIN` famously returns `C=0`; `TAPOUT` is no safer), so
the tape-save loops keep ALL state in RAM across each `TAPOUT`: `TSV_PTR` ($E0F1) /
`TSV_END` ($E0F3) walk the source, `TSV_CNT` ($E0F5) counts, `TSV_NAME` ($E0F6, 6)
holds the parsed name — the same discipline `disk_putword` uses on the disk side.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `CSAVE` statement token | `$9A` | OBSERVED from the Philips VG-8020 crunch buffer (`basic_probe_crunch.py`, scratch line, restored to pristine); cross-checks MSX2 TH Table 2.20 (adjacent to `CLOAD $9B`) | sourced |
| `TAPOON`/`TAPOUT`/`TAPOOF` write entries | `$00EA`/`$00ED`/`$00F0` | MSX2 TH cassette BIOS entry table; our own `tape/tape.asm` contracts | sourced |
| Header block = file-type id ×10 + 6-char name; data block = payload | `$D3`/`$D0` | MSX2 TH cassette file format; cross-checks `cas_encode.py` + a real VG-8020 recording (oracle) | sourced |
| tokenised data block = `TXTBASE..PRGEND+1` line-link image (ends in `$0000`) | — | program.asm line-link layout (already sourced); identical to the disk/tape read image | sourced |
| binary data block = `start`/`end`/`exec` (LE) + `RAM[start..end]` | — | MSX-BASIC binary cassette format (already sourced, §disk BLOAD execute) | sourced |
| `SAVE"CAS:"` / `CSAVE` write the **tokenised** ($D3) format (no ASCII save) | — | own-design descope (matches zerobas's tokenised disk SAVE; ASCII detokeniser is Phase 2) | quarantined |
| 6-char filename truncation / space-pad; bare `CSAVE` → 6 spaces | — | MSX cassette format (6-char name); bare-name default is own design | sourced |
| `TSV_PTR`/`TSV_END`/`TSV_CNT`/`TSV_NAME` tape-write scratch | $E0F1/$E0F3/$E0F5/$E0F6 | own choice (free page-$E0 RAM, collision-checked clear of `DSV_*`/read-side scratch) | sourced |

Oracle confirmation: `basic_probe_tape_save.py` (msx-preservation), three independent
oracles on `C-BIOS_MSX1_EU_TAPE` (zerobas-tape write layer) with `basic.rom` as a
cart — (1) **format**: zerobas writes a tape, openMSX records the CAS-out, `cas_decode`
yields bytes byte-identical to `build_cas`/`build_cas_basic`; (2) **cross-read**: the
reference Philips VG-8020 `CLOAD`s zerobas's recorded `.cas` to the correct image; (3)
**self round-trip**: `CSAVE`→`CLOAD` and `BSAVE"CAS:"`→`BLOAD"CAS:"` byte-identical
(using the just-fixed read path). Crunch stays byte-identical and the five basic
regression probes ALL PASS.

## FILES — Disk BASIC directory listing (basic/files.asm, basic/interp.asm, basic/sysvars.inc)

Phase 2's first Disk BASIC file-channel verb, built by **EXTEND** over the existing
loader-side FAT12 engine (`§disk DSKIO host engine`): the file verbs move bytes
through the SAME standard `DSKIO ($4010)` + FAT12 substrate as the loader, so they
are layered on `basic/fat.asm`, not delegated to the in-slot Disk BASIC
(file-channel-protocol.md §0/§4/§5, the Step-0 spike result).

**Statement.** `FILES` lists the root directory. `do_files` (basic/files.asm)
mounts the volume (`fat_mount`), walks the root-directory sectors with
`read_sector` + the on-disk 32-byte directory-entry layout (Microsoft FAT spec,
same layout `fat_find` already matches): a `$00` first byte ends the scan, `$E5`
marks a deleted entry, attribute bit `$10` (sub-directory) / `$08` (volume label)
are skipped. Each surviving entry is rendered as the **8.3 name field** — 8 name
bytes (raw on-disk, already upper-case + space-padded) + `'.'` + 3 extension bytes
= a fixed 12-char field — printed via `CHPUT ($00A2)`.

**Token.** `FILES = $B7`, oracle-LOCKED byte-identical to the reference **Philips
VG-8020** (`basic_probe_crunch.py`, case `files` → `… 3A B7 00`) — the
disk-extension keyword is in the MAIN ROM's reserved-word table even on the
diskless reference — cross-checked against MSX2 TH Table 2.20. Added to `kwtable`
(tokenise) and rendered by the existing table-driven `detok_kw` (LIST round-trip
confirmed: `10 FILES` lists back as `10 FILES`).

**Wrap.** Entries are single-space separated and wrapped to as many 12-char fields
as fit the active text width, driven by the live cursor column (`CSRX $F3DD`)
against the active width (`LINLEN $F3B0`) — the faithful MSX algorithm. Validated
two ways against the real **National CF-3300** Disk BASIC v1.0
(`disk_probe_files.py`, /tmp copy of `test720.dsk` = TEST.BIN, HI.TXT, PROG.BIN,
PROG.BAS, PROG2.BAS): (1) at zerobas's native width the five 8.3 fields appear in
directory order in the exact field format; (2) at `WIDTH 29` (the CF-3300 width)
the listing is **byte-identical** to the CF-3300 reference's three logical lines
(`diskbasic_probe_files.py`):

```
TEST    .BIN HI      .TXT
PROG    .BIN PROG    .BAS
PROG2   .BAS
```

**Scratch.** Only `FILES_ENTIDX` ($E0FC, 1 byte, dead outside a FILES listing) is
needed beyond the fat.asm scratch — the dir-walk position lives in
`FAT_DIRSEC`/`FAT_DIRREM`, and the per-entry pointer is re-derived from
`FILES_ENTIDX` after each `CHPUT` (which clobbers every register). Placed in the
free `$E0FC..` gap below `LINEBUF ($E100)`, collision-checked.

**Divergences (own design, quarantined):**
- An optional `<filespec>` pattern argument is **parsed-past and IGNORED** — `FILES`
  always lists the whole directory. The argument-skip is not string-aware (a `:`
  inside a quoted pattern would terminate early); both are acceptable because the
  pattern is unimplemented. Pattern matching is a later Phase-2 item.
- On a missing disk slot / mount / I-O error `FILES` reuses the loader's
  `load_error` path ("load error"), not a Disk-BASIC-specific "Disk offline"
  message — own-design error wording, consistent with the other disk verbs.
- The disk-name header / "Ok" framing around the listing is the REPL's, not emitted
  by `do_files`.

Clean-room: original code; FILES *semantics* + the 8.3 field layout from the public
MSX-BASIC language reference and black-box CF-3300 observation; the directory walk
reuses fat.asm primitives. No disassembly. See file-channel-protocol.md.

## file channel — sequential read (OPEN/INPUT#/LINE INPUT#/CLOSE) (basic/files.asm, basic/interp.asm, basic/sysvars.inc)

Phase 2's sequential file-channel **read** path, EXTEND over the existing fat.asm
sequential reader (`fat_io_open` / `fat_io_getbyte`) per the Step-0 verdict
(file-channel-protocol.md §4/§5: the file verbs share the standard DSKIO+FAT12
substrate, so they layer on the loader's engine).

**Statements (basic/files.asm).**
- `OPEN "name" FOR INPUT AS #n` — `do_open` parses the quoted filename with the
  shared `parse_disk_fcb` (drive prefix + 8.3 into `DISK_FCB_NAME`), the `FOR`
  ($82) + `INPUT` ($85) tokens, the verbatim-ASCII `AS`, an optional `#`, and the
  channel number via `eval`; then `fat_io_open` mounts + finds the file + primes
  the byte stream. Records the single channel in `FCH_NUM`/`FCH_MODE`.
- `LINE INPUT #n, A$` — `ex_line` requires `INPUT` after `LINE` (graphics LINE is
  Phase 3) and reads to CR. `INPUT #n, A$` — `ex_input`, the file form, reads to
  `,`/CR. Both share `read_into_strscr`, which streams `fat_io_getbyte` into the
  STRSCR `[len][bytes]` descriptor (ignoring LF, stopping on CR / mode delimiter,
  truncating past STRMAX) and stores it into the string variable via the existing
  `var_name_key` + `str_set_key`.
- `CLOSE [#n]` — `ex_close` clears the channel state (INPUT has no dirty state to
  flush; the OUTPUT flush via `fat_io_close` lands with the write verbs).

**Tokens** oracle-LOCKED byte-identical to the Philips VG-8020 crunch
(`basic_probe_crunch.py`): OPEN=$B0, INPUT=$85, LINE=$AF, CLOSE=$B4 (cross-checked
MSX2 TH Table 2.20). `AS` and `#` are kept verbatim ASCII; the channel digit
crunches to the `$11+n` single-digit token (zerobas already emits this — `1`→$12).
Added to `kwtable`; rendered by the table-driven `detok_kw`.

**Validation** (`disk_probe_fileread.py`, /tmp copy of `test720.dsk` holding
`HI.TXT = "Hello from zerobas-disk!\r\n"`): `OPEN…FOR INPUT…:LINE INPUT#1,A$:CLOSE
#1:PRINT A$` and the `INPUT#1,A$` variant both print `Hello from zerobas-disk!`
(CR/LF stripped) — matching the ground-truth disk bytes — and the **real National
CF-3300 Disk BASIC prints the identical line** (differential). The full crunch
oracle + 16 host unit-test files still pass; FILES is unaffected.

**The HL-clobber rule (a fixed bug, recorded).** `fat_io_open` reaches disk via
`CALSLT`, which clobbers HL (the BASIC text cursor) along with every register. The
first `do_open` lost HL across the open and `jp exec_stmt` ran on a garbage cursor
→ a spurious "syntax error" *after* the channel had actually opened. Fix: guard HL
(and DE) on the stack across `fat_io_open`. Same discipline as the read loop, whose
counter (`IN_RDLEN`) and mode live in RAM because `fat_io_getbyte`'s DSKIO clobbers
the register file.

**Scratch.** `FCH_NUM`/`FCH_MODE` ($E0FD/$E0FE) persist across statements;
`FCH_RDMODE` ($E0FF) + `IN_RDLEN` (overlays the dead `FILES_ENTIDX` $E0FC) are
transient within one read statement. All in the free `$E0FC..$E0FF` gap below
`LINEBUF`, collision-checked.

**Divergences (own design, quarantined):**
- **ONE channel only** — the engine has a single global `FREAD_*` state; the file
  number is recorded but not checked against a `MAXFILES` table. Multi-channel is a
  later sub-item.
- INPUT#/LINE INPUT# fill **string variables only** (numeric INPUT# = Phase 3); a
  value longer than STRMAX (32) is truncated (the string layer's own limit).
- INPUT# is minimal: it stops at `,`/CR and ignores LF, but does **not** do leading-
  whitespace skipping or quoted-field parsing (Phase 3 refinements).
- console `INPUT` (no `#`), graphics `LINE`, and `OPEN … FOR OUTPUT` are not
  implemented here — they error (`stmt_error`); OUTPUT arrives with the write verbs.
- file/channel errors (no disk, not found, no open channel) reuse the loader's
  `load_error` ("load error") path, not a Disk-BASIC-specific message.

Clean-room: original code; verb semantics + the FCB-by-name / sequential read model
from the public MSX-BASIC language reference and the black-box CF-3300 DSKIO trace
(file-channel-protocol.md §2/§3); the byte stream reuses fat.asm. No disassembly.

## file channel — sequential write (OPEN FOR OUTPUT / PRINT# / CLOSE) (basic/files.asm, basic/print.asm, basic/interp.asm, basic/repl.asm, basic/strvar.asm, basic/sysvars.inc)

The WRITE complement of the read path above, EXTEND over the fat.asm write engine
(`fat_io_create` / `fat_io_putbyte` / `fat_io_close`, all Phase-1.5 oracle-confirmed).

**Statements.**
- `OPEN "name" FOR OUTPUT AS #n` — `do_open`'s OUTPUT arm. The mode keyword is the
  one subtlety: **`OUTPUT` crunches to two reserved words, `OUT` ($9C) + `PUT`
  ($B3)**, not a single keyword (oracle-observed; the `PUT` token was added to
  `kwtable` solely so `FOR OUTPUT` tokenises byte-identically — the PUT *statement*
  is sub-phase 2c and has no dispatch). After matching OUT+PUT, `fat_io_create`
  makes/truncates the file and primes the write iterator; `FCH_MODE = 2`.
- `PRINT #n, <items>` — `ex_print` (basic/print.asm) detects a leading `#`, checks
  the channel is open FOR OUTPUT, consumes the `#n` + separator, sets `PRDEST = 1`,
  and falls into the **same screen-PRINT item loop**. Every emit site (`exp_str_lp`,
  `print_strval`, `print_string`, `print_crlf`, `print_comma_zone`) now routes
  through **`pchar`**, which sends the byte to `CHPUT` (screen) when `PRDEST = 0` or
  to `fat_io_putbyte` (the channel) when `PRDEST = 1`. So number/string-var/literal
  formatting and the closing CRLF are reused verbatim — no duplicated PRINT logic.
- `CLOSE #n` (OUTPUT) — appends the **CP/M text-EOF marker `Ctrl-Z` ($1A)** then
  `fat_io_close` (flush the buffered sector + stamp size/first-cluster).

**The Ctrl-Z fidelity (found by the oracle).** The CF-3300 differential
(`disk_probe_filewrite.py`) showed the real CF-3300 writes `hello world\r\n\x1a`
for `PRINT#1,"hello world"` — MSX Disk BASIC stamps a `Ctrl-Z` on CLOSE of a
sequential OUTPUT file. zerobas now does the same, so the written file is
**byte-identical to the CF-3300's** (`hello world\r\n\x1a`), not just round-trip
readable.

**PRDEST discipline.** `PRDEST` ($E0CB) is 0 (screen) everywhere except inside
PRINT#'s own item loop. It is zeroed at cold start (`init_filechan`), and
re-cleared at every statement boundary (`exec_stmt` top), the REPL prompt, and
`stmt_error` — so a mid-PRINT# error, the next statement, and the prompt always
reach the screen, never the half-written file. `pchar` preserves every register
(fat_io_putbyte's DSKIO clobbers the file), making it a drop-in for `call CHPUT`.

**Validation** (`disk_probe_filewrite.py`, /tmp copy of `test720.dsk` — the
committed image is never mounted): `OPEN"OUT.TXT" FOR OUTPUT AS #1 :
PRINT#1,"hello world" : CLOSE#1` then the read-back `OPEN…FOR INPUT…:LINE
INPUT#1,A$:…:PRINT A$` prints `hello world` (self round-trip); the on-disk
`OUT.TXT` parses (our own FAT12 read of the image) to `b"hello world\r\n\x1a"`
(ground truth); and the **real CF-3300 writes a byte-identical `OUT.TXT`**
(differential). Tokens oracle-locked (`basic_probe_crunch.py`: OUTPUT→$9C $B3,
PRINT#→$91 …). Full crunch + 16 unit-test files + the FILES/read probes still pass.

**HL guard.** `fat_io_create`/`fat_io_putbyte`/`fat_io_close` all reach disk via
CALSLT (clobbers HL = the text cursor), so HL is stacked across each — the same
rule that fixed the read-path OPEN bug.

**Divergences (own design, quarantined):** single channel; `OPEN FOR APPEND` not
yet implemented; `PRINT# USING` is a later item; the comma-zone wrap divergence of
screen PRINT (PROVENANCE.md §PRINT) applies equally to PRINT#; write errors
(disk full / not-open) reuse `load_error`.

Clean-room: original code; semantics from the public MSX-BASIC reference + the
black-box CF-3300 trace; the write engine reuses fat.asm. No disassembly.

## KILL — delete a file (basic/files.asm, basic/fat.asm, basic/interp.asm, basic/sysvars.inc)

The first file-management verb after FILES. `KILL "name"` deletes a file by freeing
its FAT cluster chain and marking its directory entry deleted — EXTEND over fat.asm.

**Engine (`fat_delete`, basic/fat.asm).** Mounts, then `fat_find` locates the 8.3
name — `fat_find` now also records the entry's location (`FWR_DIRSEC` / `FWR_DIROFF`,
write-side scratch the read path ignores). It then walks the cluster chain from
`FAT_FIRSTCLUS`: for each data cluster (2 ≤ c < $FF8) it reads the *next* link
(`fat_next_cluster`) and frees the current entry to 0 in **every FAT copy**
(`fat_write_fat_entry`); at the end-of-chain it re-reads the directory sector,
writes `$E5` over the entry's first byte (the Microsoft FAT deleted-entry marker),
and writes the sector back.

**Statement (`do_kill`, basic/files.asm).** Parses the quoted filename with the
shared `parse_disk_fcb` (same `A:`/`B:` prefix + 8.3 handling as the loader verbs),
guards HL across the CALSLT-heavy `fat_delete`, and continues. Token `KILL = $D4`
oracle-LOCKED byte-identical to the Philips VG-8020 crunch (`basic_probe_crunch.py`;
MSX2 TH Table 2.20); added to `kwtable` + dispatch, detok table-driven.

**Validation** (`disk_probe_kill.py`, /tmp copy of `test720.dsk` — committed image
never mounted): `KILL "HI.TXT"` leaves the entry no longer found, its directory
byte = `$E5`, and its FAT cluster (4) freed to 0; and the resulting **disk image is
byte-identical to the real CF-3300 Disk BASIC** after the same KILL (KILL touches
only the dir entry's first byte + the FAT chain, so the images must match exactly —
they do). Full crunch + 16 unit-test files + the FILES/read/write probes still pass.

**Divergences (own design, quarantined):** single file only — no wildcard
`KILL "*.BAK"` (a later item); a missing file / I-O error reuses the loader's
`load_error` ("load error") path, not a Disk-BASIC "File not found" message.

Clean-room: original code; KILL semantics + the `$E5` deleted-marker / chain-free
rules from the public MSX-BASIC reference + Microsoft FAT spec, validated by the
byte-identical CF-3300 differential. No disassembly.

## NAME — rename a file (basic/files.asm, basic/interp.asm, basic/sysvars.inc)

`NAME "old" AS "new"` renames a file by overwriting its directory entry's 8.3 name
field — no FAT change (the clusters and size are untouched). EXTEND over fat.asm,
reusing `fat_find`'s recorded entry location (`FWR_DIRSEC`/`FWR_DIROFF`).

**Statement (`do_name`).** Parses the OLD name (`parse_disk_fcb` → `DISK_FCB_NAME`),
the verbatim-ASCII `AS`, and checks the NEW name's opening quote. It finds the OLD
file FIRST (recording the entry location) because building the NEW name reuses
`DISK_FCB_NAME`; then parses the NEW name, re-reads the directory sector, `LDIR`s
the new 11-byte 8.3 field over the entry, and writes the sector back. HL (the text
cursor) is guarded on the stack across every CALSLT (`fat_mount`/`fat_find`/
`read_sector`/`write_sector`). Token `NAME = $D3` oracle-LOCKED byte-identical to
the Philips VG-8020 crunch (`basic_probe_crunch.py`; MSX2 TH Table 2.20). Note the
token VALUE ($D3) equals `BASIC_ID` (the cassette tokenised-BASIC marker) but lives
in a different namespace — separately-named constants, like SAVE/BSAVE.

**Validation** (`disk_probe_name.py`, /tmp copy of `test720.dsk` — committed image
never mounted): `NAME "HI.TXT" AS "BYE.TXT"` leaves HI.TXT gone and BYE.TXT present
with the **same first cluster (4), size (26), and data** ("Hello from
zerobas-disk!\r\n"); and the resulting **disk image is byte-identical to the real
CF-3300** after the same NAME (rename rewrites only the one entry's 8.3 field).
Full crunch + 16 unit-test files + the FILES/read/write/KILL probes still pass.

**Divergences (own design, quarantined):** no "new name already exists" check (a
later refinement); the drive prefix on either name is accepted and ignored for the
stamp (single drive); errors (no disk / old not found / I-O) reuse `load_error`.

Clean-room: original code; NAME semantics + the 8.3 dir-field layout from the public
MSX-BASIC reference + Microsoft FAT spec, validated by the byte-identical CF-3300
differential. No disassembly.
