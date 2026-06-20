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
keyword set). No oracle CLEAR probe exists yet — a `basic_probe_clear.py`
follow-up is owed in `msx-preservation` to confirm the crunch bytes and the
HIMEM write against the reference; nothing here invents expected oracle bytes.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `CLEAR` keyword token | `$92` | MSX2 Technical Handbook, Table 2.20 (cross-checks MSX Assembly Page token table; spec-controlflow.md §1) | sourced |
| `HIMEM` sysvar (CLEAR's memory-top ceiling) | `$FC4A` | C-BIOS system variables (BSD 2-clause); cross-checked against MSX2 Technical Handbook work-area appendix / MSX Assembly Page | sourced |
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
| USR calling convention: arg in HL, CALL the routine, HL = result; refuse a `0` (un-DEF'd) vector | — | **own design** (integer-only; no DAC/VALTYP float protocol). Oracle follow-up owed for the exact reference register/DAC convention — NOT taken from any disassembly | quarantined |
| DEF USR / USR parse + trampoline algorithm | — | **own code**; not derived from any disassembly | sourced |

The USR *calling convention* is the one **quarantined** item so far: zerobas's
integer-only convention is a deliberate own-design stand-in for MSX-BASIC's
DAC/VALTYP argument protocol, which has no allowed byte-level source here. It is
sufficient for loader stubs (arg/return usually ignored); a future oracle probe
should pin the real convention.

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

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `PRINT` token / `?` abbreviation | `$91` | MSX2 TH Table 2.20; `?`→`$91` oracle-confirmed (crunch) | sourced |
| PRINT items, `;`/`,` separators, trailing-sep newline suppression | — | public MSX-BASIC language reference | sourced |
| Integer number format: leading space (non-neg) / `-` (neg), no leading zeros, trailing space; signed 16-bit | — | public MSX-BASIC language reference (exact format also oracle-observable) | sourced |
| 14-column comma tab zones via CSRX | `$F3DD` | public language reference (zones) + C-BIOS sysvars (CSRX) | sourced |
| `CHPUT` for character output | `$00A2` | C-BIOS / MSX Assembly Page BIOS list | sourced |
| `div10`, number→ASCII, PRINT parse loop | — | **own code** (standard binary divide); not from any disassembly | sourced |
| `NUMBUF` decimal scratch | `$E0C0` | own choice (free page-3 RAM) | sourced |

No quarantined items. (String *variables*/functions for PRINT are deferred to the
Phase 2 string engine; only string literals + numeric expressions print today.)

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
(`basic_probe_cload.py`, FORMAT check PASS). But an end-to-end load *on zerobas*
is blocked by the **device half** under test — the zerobas-tape patch's `TAPIN`
cannot frame a run of consecutive `$00` bytes, and every tokenised BASIC program
ends in the all-zero `$0000` end-link. Confirmed by a raw verbatim TAPIN read,
which hangs inside `TAPIN` on the trailing `$00` run, while the reference's own
tape ROM (exercised by the FORMAT check) frames the same bytes fine. This is a
zerobas-tape (cassette device-half) limitation tracked in that component, NOT a
CLOAD/LOAD interpreter-half bug; the on-device functional load is gated on a
zerobas-tape `$00`-run framing fix. (BLOAD is unaffected — it reads a known byte
count and never a mid-stream `$0000`; `basic_probe_bload.py` still PASSes.)

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
| Read stops at the `$0000` end-link (never reads past it) | — | own code; required because the device half blocks on tape silence at end-of-data | sourced |
| Links recomputed by `relink` after load (loaded image = typed image) | — | program.asm `relink` (already sourced) | sourced |
| `CLOAD`/`LOAD` parse + `do_tape_prog` read algorithm; `CLPTR` ($E02B) scratch | — | **own code** (mirrors bload.asm's tape contract + program.asm's store/relink); not derived from any disassembly | sourced |
| Optional CLOAD filename / `"CAS:"` filename parsed and **ignored** (no tape file catalogue; TAPION opens the next file) | — | **own design** (loader-stub scope; documented in basic/cload.asm) | quarantined |
| On-zerobas end-to-end functional load blocked by zerobas-tape `$00`-run TAPIN framing (every program ends in `$0000`) | — | **device-half (zerobas-tape) limitation**, not this code — interpreter half is crunch-identical and the `.cas` format is reference-load oracle-validated; gated on a zerobas-tape fix | quarantined |

The filename-ignore and the on-device functional-load blocker are the two
**quarantined** items: the first is a deliberate own-design simplification
(loader-stub scope), the second is a cross-component device-half limitation
(zerobas-tape `$00`-run framing) — neither is a value lifted from any reference
ROM or disassembly. The CLOAD/LOAD interpreter half is complete, crunch
byte-identical, and oracle-validated against the reference's own CLOAD.

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
the combined `C-BIOS_MSX1_BASIC_DISK` machine, after boot the three locations the
disk ROM's INIT writes now carry its values: `SYSTEM` ($F37D) = `$416E`
(bdos_entry), `H.PHYD` ($FF3E) = `JP $416B` (phyd_handler), `H.DSKIO` ($FF4B) =
`JP $404E` (dskio). Differential control with the pre-scan ROM: all three read the
C-BIOS defaults ($C9 / $C9C9 — INIT did not run). Crunch byte-identical and the
four regression probes still pass (the scan runs harmlessly before the REPL).

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
MSX-DOS compatibility) — see disk/PROVENANCE.md §BDOS Set-DTA.

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
- **Streamed body store is not token-aware (shared with `do_tape_prog`).** Both
  `ctp_body` and `dpl_body` copy a line's token body until the FIRST `$00`, so a
  token operand byte that is itself `$00` (e.g. the high byte of an `&H` value
  `$0C $7B $00`) would be mistaken for the line terminator. The in-RAM store
  editor (`store_line`) uses the token-aware `skip_to_eol`, but a *streamed* load
  has no length up front. This is a pre-existing `do_tape_prog` limitation
  inherited verbatim, not introduced here; the realistic common case (operands
  with no embedded `$00`) loads correctly. The test fixture is built to avoid
  embedded `$00` (encodes `123` as the 1-byte `INT1` form `$0F $7B`, not the
  `&H` form), so it is a faithful exercise of the shared loop. A fully robust
  streamed loader (token-aware body copy) is deferred and would equally fix
  `do_tape_prog`.
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
