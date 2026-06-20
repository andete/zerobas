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
