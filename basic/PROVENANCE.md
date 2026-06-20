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

### RAM additions (basic/sysvars.inc)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `LINEBUF` ($E100, 96), `TOKBUF` ($E160), `VARTAB` ($E1C0, 52 bytes) | — | own choice (free page-3 RAM in page $E1, clear of the $C000/$E000 demo regions) | sourced |

No quarantined items.
