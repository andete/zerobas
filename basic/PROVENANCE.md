# Provenance log — zerobas BASIC

Every constant, address, data table, and algorithm in the zerobas BASIC
interpreter must appear here with an independent **allowed** source, or be
explicitly **quarantined**. An unexplained magic value blocks release.

- **sourced** — traced to an allowed source (see [`../README.md`](../README.md) for the list).
- **quarantined** — no allowed source found; derived from spec or stubbed,
  **never copied** from a reference ROM or any MSX-BASIC / GW-BASIC disassembly.

The behavioural source `spec-bload-r.md` is this project's own black-box oracle
observation, captured in
[`basic/docs/spec-bload-r.md`](docs/spec-bload-r.md).

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
| Error message text (all of it) | — | **black-box measurement** of a running reference machine's screen — see the note below | sourced |
| `LINEBUF`, `LINEMAX` | — | own choice (free page-3 RAM) | sourced |

No quarantined items.

### ⚠️ The error-message row changed meaning on 2026-08-02, and the reason matters

It used to read *"own wording (plain English; not copied)"*, and that was true of
a tree whose messages were deliberately house-style lowercase. **D-MSGEXACT
withdrew that policy** and **D-MSGSUB** added fourteen more messages, so zerobas
now reproduces the reference's text **verbatim**, capitalisation included. The
old row would have been a false attestation, which is worse than no row.

**Why that is still clean-room, stated precisely** — the distinction is between
*observing a machine* and *copying its code*:

* Every string is a **reading of a screen**, taken with `ERROR n` in direct mode
  on two running reference machines and recorded in
  [`../docs/msgexact-msx1-characterization.md`](../docs/msgexact-msx1-characterization.md).
  That is the same black-box instrument every other characterization in this tree
  uses to fix behaviour, applied to output that happens to be text.
* **No reference ROM is disassembled, read, or diffed** to obtain them. The
  strings are not lifted from a ROM image; nothing locates them in one.
* They are **not transcribed from a published MSX-BASIC reference** either — and
  that is not a technicality: the published table gets ERR 17 wrong (`Can't
  continue`; the machines say `Can't CONTINUE`). Transcribing would have been
  both a worse source *and* a copy of someone's document.

⚠️ Short user-visible strings of this kind are facts about an interface, not
creative expression — the same status as an entry address or a work-area layout.
Reproducing them is what "faithful" means for a message; inventing them is what
made the old policy a divergence. Anything ORIGINAL to zerobas stays original and
is listed as such above (`zb>`, the startup banner).

## REM / POKE / PEEK statement slice

Behavioural source: `basic/docs/spec-tokens-statements.md` (this project's
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
`basic/docs/spec-tokens-statements.md §3/§4` (this project's own black-box
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
keyword set). Oracle: `basic_probe_clear.py` differences
zerobas against the Philips VG-8020 reference and confirms that after
`CLEAR 200,&HD000` both store `$D000` (LE) in HIMEM (`$FC4A`) — proving `$FC4A`
is CLEAR's memory-top home on the reference and that zerobas matches it.

> 🔴 **CORRECTION 2026-08-23 (D-CLRFIX, [`../docs/spec-basic-clrfix.md`](../docs/spec-basic-clrfix.md)):
> the sentence that stood here claimed "all **four** syntax forms (`CLEAR`,
> `CLEAR n`, `CLEAR ,himem`, `CLEAR n,himem`) parse without error and the line
> continues". There are **three**. `CLEAR ,himem` — string space omitted — is a
> `Syntax error` on the Philips VG-8020 **and** the National CF-3300, measured
> both in a trapped program and in direct mode. zerobas accepted it until the
> special case was deleted (−4 B). The other three forms are unaffected and
> still measured. ⚠️ `basic_probe_clear.py` is wired to no make target, so its
> group 2c asserted the acceptance unchecked for the life of the tree; that
> group is now pointed at the refusal.**

zerobas does not maintain the
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
| `<memory-top>` arg stored to HIMEM — **NOT record-only; see the correction below** | — | own design; HIMEM is the documented home of the value (language reference) | sourced |
| `CLEAR ,himem` (string space omitted) is a **`Syntax error`** on the VG-8020 and the CF-3300 | ERR 2 | `scratchpad/clrfix_probe.py` rows `q.comma` / `z.hd000` (both references, boot-per-case) | oracle-locked |
| `CLEAR <n>,<himem>` past int16 (`70000`) is **`Overflow`** on both references | ERR 6 | `scratchpad/clrfix_probe.py` row `q.ovf` | oracle-locked |
| `CLEAR <n>,-1` is **`Illegal function call`** on both references (zerobas diverges — open) | ERR 5 | `scratchpad/clrfix_probe.py` row `z.neg` | oracle-locked |
| CLEAR parse/dispatch algorithm | — | **own code** (mirrors the do_poke arg-parse pattern); not derived from any disassembly | sourced |

> 🔴 **CORRECTION 2026-08-23 (D-CLRFIX): "record-only" was false.** HIMEM is
> consulted, and by `CLEAR` itself: [`str-engine.asm`](str-engine.asm)
> `heap_reset` — called from `clear_vars`, which `CLEAR` calls — computes
> `FRETOP := min(HIMEM,TXTMAX)`, and the string pool's floor is derived sub-side
> from the same figure. Measured, not argued: `CLEAR ,200:A=1` answered
> `Out of memory` (row `q.commak`). The same phrase in
> [`clear.asm`](clear.asm)'s header is inverted in place. **Nothing about the
> provenance of the value or its address changes — only the claim that storing
> it is inert.**

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

### §variable area — arrays slice-4b: numeric scalar relocation (repack build only, docs/spec-basic-arrays-slice4b-scalar-reloc.md)

The fixed `VARTAB`/`VAREND` numeric pool above (Phase 1, unchanged in the
LEAN build) is **relocated in the repack build** out of the fixed $E1C0..$E240
span into the real-MSX contiguous chain (`TXTTAB→VARTAB→ARYTAB→…→FRETOP→
MEMSIZ`), joining arrays' own `[PRGEND+2, FRETOP)` region (arrays slice-1,
docs/spec-basic-arrays.md; string heap arrays slice-4a, docs/spec-basic-
arrays-slice4a-string-heap.md). Numeric scalars now share the SAME
insert-and-shift / `FRETOP` collision / GC-once-retry mechanism arrays
already use — creating a scalar opens a `stride`-byte hole at the current
`ARYTAB` by shifting the whole array region up (a bottom-up `LDDR`), the
mirror image of arrays' own top-down growth. The freed $E1C0..$E240 (128 B)
becomes ordinary RAM; the new `ARYTAB` live cell (2 B) is homed at its foot.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Contiguous chain order `program text → scalars → arrays → free → string heap → HIMEM` | — | documented MSX memory model (MSX2 Technical Handbook / MSX Assembly Page: `TXTTAB→VARTAB→ARYTAB→STREND→FRETOP→MEMSIZ`) | sourced |
| `ARYTAB` stored live cell = scalar-region end = array-region base | `$E1C0` (repack only; the just-freed foot of the dead `VARTAB` span) | own choice (free RAM) | sourced |
| Scalar entry format `[name0][name1][type][value:2/4/8]`, stride = type+3, key (name0,name1,type) | — | **own code / own choice** — carried over UNCHANGED from the pre-4b fixed-pool layout (F3 S3a, above); only the location + walk moved | sourced |
| Insert-and-shift mechanism (open a hole at `ARYTAB`, `LDDR` the array block up by `stride`, collision-checked BEFORE moving) + the `FRETOP` collision/GC-once-retry reuse | — | zerobas's own realisation of the documented memory model, reusing the arc's own arrays/heap machinery (sub/arrays.asm `ary_alloc`'s identical ceiling discipline) | sourced |
| Behaviour delta: a program EDIT now clears NUMERIC scalars + arrays (relink chains through the shared `vars_reset`); STRING scalars (fixed `STRTAB` pool) still survive an edit until slice 4c | — | More MSX-faithful (stock MSX-BASIC clears ALL variables on a direct-mode edit); pre-4b zerobas kept all scalars across an edit as an off-to-the-side-pool artifact. Interim divergence: numeric+arrays clear, string scalars persist to 4c (string-scalar unification) — documented, not yet fully faithful | sourced |
| Behaviour delta: scalar creation can now raise `Out of memory` (matches the array OOM disposition) instead of the pre-4b fixed-pool's silent drop | — | own design (the SAME `ARY_ERR`/`ary_errmap` codepath arrays' own OOM already uses) | sourced |

### §variable area — arrays slice-4c: string-scalar unification (repack build only, docs/spec-basic-arrays-slice4c-string-scalar-unification.md)

The fixed `STRTAB` string-scalar pool (`$E240..$E268`, 8 × 5-B `[name0][name1]
[len][ptr]` descriptors) is **dissolved in the repack build**: string scalars
join the SAME unified chain 4b relocated numeric scalars into, as ordinary
`[name0][name1][type=1][len:1][ptr:2]` entries (stride 6, keyed on
`(name0,name1,type)` exactly like a numeric entry — the `$` suffix resolves to
type 1 via the existing `var_str_type` unifier). This reaches the full real-MSX
`TXTTAB→VARTAB→ARYTAB→…→FRETOP→HIMEM` model: no fixed variable pool remains.
`str_get_key`/`str_set_key` (basic/vars.asm) become thin glue over the SAME
`ARY_OP` 4/5 (`SCALAR_FIND`/`SCALAR_ALLOC`) scalar ops 4b already added to the
ARY tenant (sub/arrays.asm) — no new op-code, no new param block — with the
stride substituted through the existing `elsize_from_type` map (already used by
`ary_stride`/`ary_alloc`) so a type=1 entry strides 6 (3 header + the 3-byte
heap descriptor) instead of the raw `type+3`. `sg_walk_scalars`
(sub/strheap.asm) replaces `sg_walk_strtab` as the GC root-enumeration pass
over the chain, visiting a type=1 entry's descriptor at `entry+3` (one byte
past the `STRTAB`-slot convention, since a chain entry carries an explicit type
byte a dedicated pool omitted).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| String-scalar entry format `[name0][name1][type=1][len:1][ptr:2]`, stride = `elsize_from_type(type)+3` | — | **own code / own choice** — the pre-4c `STRTAB` descriptor's `[len][ptr]` tail carried over unchanged, only the location/stride/walk changed | sourced |
| `sg_walk_scalars` (GC root enumeration over the unified chain, entry+3 offset) | — | own code, modelled on the sibling `sg_walk_arrays` (already `(ARYTAB)`-anchored, type-filtered, `elsize_from_type`-strided) | sourced |
| H1 fix: a `str_set_key` var-to-var copy snapshots the SOURCE descriptor onto the temp-descriptor stack (the same mechanism 4a's own concat operand-snapshot uses, `str_snapshot_to_temp`) before the target scalar alloc, so the source survives both the target's insert-shift and a possible collision GC | — | own design; the load-bearing fix this slice exists to isolate (§6 of the spec) — a string-array-element or RVDESC source would otherwise go stale mid-store | sourced |
| H3 fix: `vars_reset` (basic/arrays.asm) now also resets the string heap (`heap_reset`) on every scalar+array reset, not just via `clear_vars` — closes an orphaned-body leak on `relink` (program edit) / a standalone `new_prog` (LOAD), the two call sites that don't otherwise run `heap_reset` | — | own design (intrinsic to making string scalars chain-resident; §3d/Q4 of the spec) | sourced |
| Behaviour delta: a program EDIT now clears string scalars TOO (resolves the 4b §7.1 interim divergence — `A$` no longer survives an edit) | — | More MSX-faithful (stock MSX-BASIC clears ALL variables on a direct-mode edit); differential-confirmed against the VG-8020 reference (both clear `A$`+`A` on a stored-line edit) | sourced |
| Behaviour delta: `str_set_key`'s scalar-chain OOM (the table-full disposition, now dynamic/unbounded rather than the pre-4c fixed 8-slot cap) raises a surfaced `Out of memory` instead of a silent drop — required wiring an `(FPERR)` check into `ex_let_str` (basic/interp.asm) mirroring `ex_let`'s own numeric post-store check, since `str_set_key`'s pre-4c contract never needed one (a STRTAB-full store was ALWAYS a silent, deliberate drop) | — | own design (the SAME `ARY_ERR`/`ary_errmap` codepath arrays'/numeric-scalars' own OOM already uses) | sourced |
| KNOWN RESIDUAL: the same OOM-surfacing gap (FPERR set by `str_set_key` but never checked by the caller) is UNFIXED at the other three `str_set_key` call sites — `basic/input.asm`'s `inpc_vstr` (plain `INPUT` string variable) and `inpc_line` (`LINE INPUT`), and `basic/files.asm`'s `INPUT#` site — a scalar-chain OOM during any of those three still silently drops the assignment. Only `ex_let_str` (LET) was fixed + gated this slice; flagged for a follow-up, not fixed here (scope/risk judgment call — `inpc_vstr` in particular is a multi-variable loop with `?redo`/`?extra ignored` stack bookkeeping not touched to avoid destabilising the input-acceptance gate under time pressure) | — | own design gap | sourced |

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
types each line into BOTH the reference Philips VG-8020
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
| `SCREEN`'s **mode** is a checked byte argument (`eval_byte_checked`: deferred expression error → ERR 6 past int16 → ERR 5 outside 0..255) narrowed by `cp 4` to 0..3, **checked before `CHGMOD`**; an argument list that ends where a value was required is `Missing operand` (ERR 24) at all four such slots; every trailing arg is a checked byte and the FIRST (sprite size) has domain 0..3; an OMITTED arg still occupies its slot | — | oracle-pinned on the VG-8020 **and** the CF-3300, 61/61 (`docs/spec-basic-screenerr.md`, `make screenerr-acceptance`) | sourced |
| ⚠️ SUPERSEDED 2026-08-10 by the row above — *"SCREEN's extra args (sprite size, key click, …) evaluated and ignored — only the display mode is applied"*. It had been **half-stale since the G7 slice**, which made the first trailing argument the live sprite size, and fully stale from D-SCRERR, which range-checks the rest. Kept as a pointer because a retired claim that simply vanishes is invisible on the next grep (`bf0dab5`) | — | own design (was: minimal; documented in basic/screen.asm) | superseded |
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

**BASE descope — RETIRED 2026-07-22 (graphics slice G8).** For most of the
project's life `BASE(n)` was parsed and its argument evaluated, but returned 0 and
set ERRMARK (`$DD` at `$E010`) rather than a table base address: zerobas drives the
screen through the C-BIOS CHGMOD path, kept no per-mode VDP table-base map of its
own, and fabricating one was not allowed. The G8 characterization removed the
premise rather than the rule — the per-mode map is **not** ours to invent, it is the
published MSX work-area table at `$F3B3`, which our own C-BIOS runtime maintains
byte-identically to the reference in every mode (measured on both machines,
docs/spec-basic-graphics-g8.md §4.1). `BASE(n)` is therefore now a plain work-area
word fetch, and `BASE(n)=v` validates + stores + reprograms, with no reference value
table anywhere in the source. The LEAN cart, which has no graphics at all, keeps the
descoped stub (`IF !G8_RESIDENT`).

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
| `BASE(n)` real value: the work-area word at `$F3B3 + 2n` (G8, 2026-07-22; the descope above is retired — LEAN build still stubs it) | — | published MSX work-area table (`TXTNAM..` at `$F3B3`), maintained by the BIOS; black-box-confirmed identical on the reference and on our runtime | sourced |
| `VDP(n)` = the register mirrors at `$F3DF + n`, `VDP(8)` = `STATFL` `$F3E7`; `VDP(n)=` writes mirror + port | — | published MSX work-area + TMS9918A register-write contract; black-box-confirmed | sourced |
| `BASE(n)=` reprogram rule incl. the SCREEN-1/2 off-by-one (source group `[0,2,3,3][SCRMOD]`) | — | **own code from black-box measurement** (poison-tested, spec G8 §4.4) — behaviour observed, never disassembled | sourced |
| `VDP` function token | `$C8` (single-byte) | MSX2 TH Table 2.20; oracle-confirmed byte-identical via the crunch capture | sourced |
| `VPOKE_TOKEN`/`OUT_TOKEN`/`VPEEK_TOKEN`/`INP_TOKEN`/`VARPTR_TOKEN`/`BASE_TOKEN` constants | — | own naming over the oracle-/Table-2.20-sourced token bytes | sourced |

The VARPTR own-address-map is now the only **quarantined** item here: a deliberate
own-design simplification, not a value lifted from any reference ROM or
disassembly. (The BASE descope that used to sit beside it was retired in G8, as
described above — by reading the published work-area table, not by fabricating
one.)

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
trailing filename. **⚠️ "quoted" is stale for `do_load` since D-FNEXPR2
(2026-08-21):** its argument is any string EXPRESSION (`LOAD A$`,
`LOAD A$+".BAS"`), evaluated by `fname_expr` and staged in `STRSCR` before the
`"CAS:"` dispatch runs — measured on the CF-3300, row `f.loadvar`. `do_cload`
is genuinely untouched and its argument really is quoted-literal-only; that is
now a divergence of its own and not a shared description. Both fall into `do_tape_prog`, which mirrors bload.asm's tape
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

### 🔴 D-CASTAIL — what `RUN"CAS:x"` / `LOAD"CAS:x",R` do AFTER the load

Measured 2026-08-07 against **two** references — the Philips VG-8020 and the
National CF-3300, which agree row for row — by
`probes/basic/basic_probe_castail.py` (`make castail-acceptance`, 9/9 + 1 pinned
divergence at the time; the same gate reads **31/31 + 1 pin** since D-CASSEARCH
and D-CASOPEN extended it, below). Spec `docs/spec-basic-castail.md`, reading
`docs/castail-msx1-characterization.md`. This closes the residual
`docs/spec-basic-runtail.md` §9 filed, and it is the **tape twin of D-RUNTAIL**:
the same two defects, on the two `basic/cload.asm` sites that reach `run_prog`
from a statement context.

**(1) A failed tape load ran the resident program anyway.** `do_tape_prog`'s
failure exits `jp load_error`, `load_error` prints and **returns**, and both call
sites' next instruction was `jp run_prog`. Measured: after a Ctrl-STOP-aborted
`RUN"CAS:NOSUCH"` with `10 PRINT"ZQ1"` resident, both references print their
message and stop; zerobas printed the message and then **ran `ZQ1`**.
`do_tape_prog` now carries the same CF-out contract `disk_prog_load` has (CF set
= the load failed and has already reported), consumed by `ret c` at
`dl_cas_close` and `dr_is_cas`. Its producer is `dpl_err` — **shared with the
disk half**, so the producer cost **0 B** — and `load_error` itself is still not
touched, for the same ~50-call-site reason. `verify_error` **is** edited in
place, and that is safe because both of its callers are inside `do_tape_prog`.

**(2) `jp run_prog` from a statement entered the run loop NESTED.** Identical to
D-RUNTAIL's defect (2) above and with the identical symptom —
`Illegal function call in 3346` after **every** `RUN"CAS:x"` / `LOAD"CAS:x",R`,
hit and abort alike, on the **success path of a shipped verb**. Both sites now
`jp run_prog_top`. ⚠️ `basic_probe_cas_verbs.py`'s `RUN"CAS:"` tests could not
see this: they assert a **memory witness** (`$D0FF` → `$99`), and a witness byte
cannot see an extra screen row.

⚠️ **Two divergences of the tape SEARCH were recorded here and not fixed by
D-CASTAIL. The first is now CLOSED by D-CASSEARCH, below.** The second stands: a
missing tape file is not an error on an MSX1 at all — the reference searches past
the end of the tape and waits forever, which is why the only failure row here is
an operator Ctrl-STOP. Filed in `TODO.md`.

| item | value | how established | status |
|------|-------|------------------|--------|
| Nothing is printed after a successful `RUN"CAS:x"` / `LOAD"CAS:x",R` beyond the loaded program's own output | — | oracle, **two** references agreeing (`castail` `cas-run-hit` / `cas-run-hit-res` / `cas-loadr-hit`) | sourced |
| A failed tape load runs **nothing**, not the resident program | — | oracle, both references (`castail` `cas-run-brk-res` / `cas-loadr-brk-res`) | sourced |
| `LOAD"CAS:x"` without `,R` loads and does not run | — | oracle, both references (`castail` `cas-load-plain` + its listing) | sourced |
| `do_tape_prog` CF-out contract; `run_prog_top` at both tape sites | — | **own code** (mirrors `disk_prog_load`'s, D-RUNTAIL §3.2); not derived from any disassembly | sourced |
| No `Found:`/`Skip :` tape-search progress line | diverges | oracle, both references print it | ✅ **CLOSED by D-CASSEARCH** (below) — was quarantined (pinned + filed) |

### 🔴 D-CASSEARCH — what an MSX1 prints WHILE the tape search runs

**Closed 2026-08-07.** Gate `probes/basic/basic_probe_castail.py`
(`make castail-acceptance`, **17/17 + 3 pinned divergences** at the time; the
same gate reads **31/31 + 1 pin** since D-CASOPEN closed two of them, below), spec
`docs/spec-basic-cassearch.md`, reading
`docs/cassearch-msx1-characterization.md`. Closes the residual D-CASTAIL filed
above; measured on the **Philips VG-8020** and the **National CF-3300**, which
agree row for row.

**Both references print one progress row per decision of the tape search** —
`Found:NAME` when it takes a file, `Skip :NAME` when it steps over one, the name
being the **header just read**. zerobas printed neither, so a user watching a
tape load saw nothing until it finished. `basic/casmatch-body.inc` now emits the
row at `com_match` and `com_miss`, through `CHPUT`, for **57 B in sub page 1**.

🔴 **The site was decided by measurement, not by reading the code.** The residual
named `LOAD` / `RUN` / `CLOAD`, but `cas_open_match` has **three** callers —
`MERGE"CAS:"` and `OPEN"CAS:" FOR INPUT` (`basic/files.asm`) share the same
search engine, so a print sited there prints for them too. Measured: **all four
verbs print the identical rows** on both references. Had any one been silent,
this siting would have closed one divergence by opening two.

🔴 **`print_msg` is unreachable from the emit and that is structural.** The
match/skip loop is a sub-ROM **page-1 tenant** (`SUBROM_IDX_CASMATCH`);
`print_msg` is at `$7687`, main page 1, which `check_tenant_closure.py --page1`
forbids a page-1 tenant to call. `CHPUT` (`$00A2`, page-0 BIOS) is legal for one
— the same reason `sub/title.asm` is a page-1 tenant — so the two prefixes are
the tenant's own bytes and the sink is BIOS.

✅ **A SECOND divergence was found by these rows and is now CLOSED by D-CASOPEN,
below.** `OPEN"CAS:name" FOR INPUT` **name-matches on both references** — it steps
over a non-matching file and opens the named one. zerobas deliberately did not
(`basic/files.asm` `oo_dev_cas` wrote `CAS_WANT_ON = 0`, commented *"name-matching
is Item A's CLOAD/LOAD/RUN/MERGE scope, not OPEN"*), so it opened the **next**
file and delivered the **wrong file's bytes**. That scoping decision was measured
wrong; it was **pinned** per side by the gate and filed in `TODO.md` rather than
folded in, because it is the OPEN verb's name handling, in a different file, and
three reference readings it needed were unmeasured. D-CASOPEN took those three
readings and closed it for **7 B in main page 1**.

| item | value | how established | status |
|------|-------|------------------|--------|
| A tape search prints `Found:NAME` when it takes a file | — | oracle, both references (`castail` `cas2-bare`, `cas-load-plain:search`) | sourced |
| ...and `Skip :NAME` once per stepped-over file, naming the SKIPPED file | — | oracle, both references (`castail` `cas2-load`) | sourced |
| All four searching verbs print it — `LOAD"CAS:"`, `CLOAD`, `MERGE"CAS:"`, `OPEN"CAS:"` | — | oracle, both references (`castail` `cas2-*`) | sourced |
| The emit is sited in the shared search engine, through `CHPUT`, in the page-1 tenant | — | **own code**; not derived from any disassembly | sourced |
| Whether the reference pads the name to 6 on screen | **not decidable** | a trailing pad space is indistinguishable from unwritten screen, and a CR/LF follows | **non-claim** (recorded, not measured) |
| `OPEN"CAS:name"` ignores the name and opens the NEXT file | diverges | oracle, both references name-match (`castail` `cas2-open`, `cas2-open:echo`) | ✅ **CLOSED by D-CASOPEN** (below) — was quarantined (pinned + filed) |

### 🔴 D-CASOPEN — `OPEN"CAS:name" FOR INPUT` honours the name

**Closed 2026-08-07.** Gate `probes/basic/basic_probe_castail.py`
(`make castail-acceptance`, **31/31 + 1 pinned divergence**), spec
`docs/spec-basic-casopen.md`, reading
`docs/casopen-msx1-characterization.md`. Closes the residual D-CASSEARCH pinned
and filed above; measured on the **Philips VG-8020** and the **National CF-3300**,
which agree on all twelve new readings.

`oo_dev_cas`'s `FOR INPUT` arm wrote `CAS_WANT_ON = 0` before every search, so a
named cassette OPEN opened whatever file came next and the channel then delivered
the **wrong file's bytes**. It now captures the name with `cas_capture_name` — the
shared cassette-name parser `LOAD`/`RUN`/`CLOAD`/`MERGE` already use — for **7 B
in main page 1** (165 → 158 B free). The search engine is unchanged.

🎯 **The defect is NARROWER than it was filed, and only opening the file could say
so.** The name was already parsed on the OPEN path (`tape_parse_name` → `TSV_NAME`,
before the `FOR INPUT`/`FOR OUTPUT` dispatch) — which is why `FOR OUTPUT` had a
name to write into its `$EA` header, correctly, all along. What was missing was
the hand-off to the search on the INPUT arm. So the fix is a **re-routing of an
existing capture**, and its whole 7 B is the `CAS_WANT` → `TSV_NAME` copy that
gives the OUTPUT arm back what it expects; the INPUT half is byte-**negative**.

🔴 **A THIRD face of the divergence that the pinned row could not see.** The pin
asks a name that MATCHES, and a machine that never compares answers it the same as
one that compares case-insensitively. `OPEN"CAS:rt"` for a tape holding `RT`
separates them: both references compare, miss both files, run off the tape and
answer the Ctrl-STOP with a message; zerobas answered **nothing**, having opened
the first file. The reference compare is **byte-exact**, the same rule
`CAS_WANT` already implemented for `LOAD`/`CLOAD`.

🎯 **`FOR OUTPUT` is read off the TAPE THE MACHINE WROTE.** The screen cannot
answer what an OPEN records — it prints nothing whether it writes the name, six
spaces or garbage — so those rows run on a `cassetteplayer new` recording and
`probes/lib/cas_decode.py` decodes the WAV. Signal edges only, the same decoder on
all three sides, no reference ROM disassembled.

| item | value | how established | status |
|------|-------|------------------|--------|
| `OPEN"CAS:name" FOR INPUT` name-matches: it steps over non-matching files and opens the named one | — | oracle, both references (`castail` `cas2-open` + `:echo`) | sourced |
| Bare `OPEN"CAS:"` takes the NEXT file, exactly as bare `LOAD"CAS:"` does | — | oracle, both references (`castail` `cas2-openbare` + `:echo`) | sourced |
| The cassette name compare is **case-sensitive**: `OPEN"CAS:rt"` does not find `RT` | — | oracle, both references (`castail` `cas2-opencase` + `:alive`) | sourced |
| `OPEN"CAS:WX" FOR OUTPUT` writes `'WX    '`, space-padded to six, into the `$EA` header | — | oracle, both references, decoded off the recording (`castail` `cas-openout:tape`) | sourced |
| Bare `OPEN"CAS:" FOR OUTPUT` writes six spaces | — | oracle, both references, decoded off the recording (`castail` `cas-openoutbare:tape`) | sourced |
| `cas_capture_name` reused at `oo_dev_cas`; `CAS_WANT` → `TSV_NAME` copy on the OUTPUT arm | — | **own code** (`merge_cas` is the landed precedent for a `files.asm` caller); not derived from any disassembly | sourced |
| Whether a name longer than six characters is truncated or refused on `OPEN"CAS:"` | **not measured** | no row asks; the shared capture truncates on every verb | **non-claim** |

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
This is the documented MSX Assembly Page / MSX2 Technical Handbook contract — the
published interface is the provenance — and was separately observed behaving
**identically on C-BIOS_MSX1** ($00B7 BREAKX: carry clear when Ctrl-STOP is not
held, on both the reference and C-BIOS). So the Ctrl-STOP functional check runs on
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
`basic_probe_cont.py` on `C-BIOS_MSX1`, 7/7 ALL PASS, via
fixed-emulated-time RAM capture (`debug read_block` of POKE sentinels at $D000/
$D001 and `ERRMARK` $E010 — robust where a bload-LANDMARK freeze was not): STOP
halts before the post-STOP statement (T=01); STOP→CONT resumes (T=02), incl.
across a line boundary (T=01,U=09); bare CONT / CONT after a STOP-less RUN / CONT
after a program edit all give `can't continue` ($C9); and a real Ctrl-STOP
keyboard-matrix press (openMSX `keymatrixdown` CTRL row6/bit1 + STOP row7/bit4)
breaks an *infinite* `goto` loop back to the REPL — proven by a direct POKE typed
after the press executing (U=09), where the same loop without the press never
yields (control: U stays cleared).

⚠️ **CORRECTED AND RETIRED 2026-07-30 (D-CONTR,
[`docs/spec-basic-cont-record.md`](../docs/spec-basic-cont-record.md)).** Two
things above are no longer true. **(a)** The claim *"CONT after a STOP-less RUN
… gives `can't continue`"* records a **DIVERGENCE**, not agreement: the
reference records a resume point at *every* run stop, so a `CONT` there resumes
past the end of the program and returns to `Ok` **silently**. That is now fixed
and gated (`cont2_falloff`). **(b)** `basic_probe_cont.py` itself has been
DELETED. It was wired into no make target, and the lean-cart retirement (S1–S3)
removed the `cart` global its `run(cart, …)` calls referenced, so it had become
unrunnable. Its coverage lives on in rows that actually run: `cont*` and
`cont2_*` in `basic_probe_abort_depth.py` (`make abort-acceptance`) for every
`CONT`/`STOP` behaviour it asserted, and `make stop-trap-acceptance` for the
real Ctrl-STOP keyboard-matrix press. The historical result above is left as
written because it *was* the measurement of the day; only its interpretation was
wrong.

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

**Functional validation (openMSX, `disk_probe_init.py`).** On
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

**Cross-host BIOS-independence — validated on a real BIOS.** The flip side of the
same standardization is that the *host BIOS* should not matter either: zerobas-disk is
a standard slot disk ROM driven through `$4010`, so any real MSX BIOS can host the
stack. Proven directly: the `zerobas-disk` openMSX extension (generated by
`tools/install-openmsx-machine.py --disk-rom`) plugs zerobas-disk into a **real Philips
VG-8020** (a genuine MSX1 BIOS, not C-BIOS, not the Japanese CF-3300), loaded with the
zerobas-BASIC cartridge. `probes/disk/disk_probe_crossbios.py` runs the identical
program — `FILES` + an `OPEN`/`PRINT#`/`CLOSE` → reopen → `LINE INPUT#` round-trip — on
both the C-BIOS host and the VG-8020 host and gets byte-identical results (same
directory listing, same `<phil>` round-trip). Note zerobas-disk supplies only the
sector DRIVER, so the verbs come from the zerobas-BASIC cartridge on both hosts — this
validates the BASIC+disk *stack* is host-BIOS-independent, not that a bare host BASIC
gains disk support.

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
The probes `disk_probe_bload_disk.py`, `disk_probe_save.py`,
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
| Load-then-run | `RUN"A:name"` | tokenised BASIC, `$FF` marker | reuses `disk_prog_load` (§disk LOAD); runs iff the load SUCCEEDED (D-RUNTAIL — "always runs" was this table's own wrong claim, §disk RUN) | §disk RUN |
| Binary / tokenised SAVE | `SAVE"A:name"` / `BSAVE"A:name",s,e[,x]` | `$FF` / `$FE` markers | standard DSKIO $4010 + loader FAT12 (`fat_io_create`/`fat_io_putbyte`/`fat_io_close`) | §disk DSKIO host engine |

**Constants the disk-extension path introduces (all `sourced`; see the named
section for the row):**

| Constant | Value | Source class | Section |
|----------|-------|--------------|---------|
| standard DSKIO entry offset + register convention (CY=direction) | $4010 | MSX2 TH §5 / CF-3300 obs | §disk DSKIO host engine |
| cross-slot DSKIO call: `CALSLT` $001C via `DISKSLOT`, addr $4010 | $001C / $4010 | MSX Assembly Page / MSX2 TH | §disk DSKIO host engine, §extension-ROM INIT scan |
| 8.3 name field +0..+10 (8 name + 3 ext, space-padded, upper-case) | — | Microsoft FAT spec §3.4; consumed by `fat_find`/`fat_dir_create` | §disk-BLOAD scratch FCB |
| disk BSAVE header `[$FE][start:2 LE][end:2 LE][exec:2 LE]` + raw data, start..end inclusive | $FE marker | MSX-BASIC file formats (public language reference) | §disk BLOAD execute |
| tokenised-BASIC disk marker | $FF | MSX-BASIC file formats (public language reference) | §disk LOAD |
| `DISK_FCB_NAME` / `DISKSLOT` / FAT engine scratch placement | $E0DC / $E0E7 / $E5C0+ | own choice (free page-$E0 / page-3 RAM, collision-checked) | §disk-BLOAD scratch FCB, §disk DSKIO host engine, §extension-ROM INIT scan |

### Oracle-confirmation status (read this before trusting "confirmed")

This surface has **four distinct validation strands**; the docs above deliberately
do not over-claim "byte-identical vs reference" where no reference exists.

1. **DSKIO sector-read — differential, byte-identical vs the real National
   CF-3300.** The **DSKIO sector-read path** underneath all of this
   (`disk_probe_dskio.py`) is a *passed differential oracle*:
   the same `disk/test720.dsk` read on the CF-3300 reference and on our
   `*_BASIC_DISK` machine returns byte-identical data + carry/A. This is the read
   layer every BLOAD/LOAD/RUN ultimately rides on.

2. **FCB BDOS layer — NARROW differential, byte-identical vs real MSX-DOS 1.**
   `bdos_entry`'s FCB calls (Open `$0F` / Sequential Read `$14` / Close `$10` /
   Set-DTA `$1A`) *are* now differentially oracle-confirmed against genuine
   MSX-DOS 1.03 (`disk_probe_bdos.py`). The same `ORACLE.BIN`
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

**Functional validation (openMSX, `disk_probe_bload_fcb.py`).**
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
`load_loop`. Source for the header layout: **MSX-BASIC file formats** — an allowed public MSX-BASIC language reference.

| Item | Value | Source | Status |
| --- | --- | --- | --- |
| BDOS call `Open` | $0F | MSX2 Technical Handbook / MSX-DOS BDOS call table | sourced |
| BDOS call `Close` | $10 | MSX2 TH / MSX-DOS BDOS call table | sourced |
| BDOS call `Sequential Read` | $14 | MSX2 TH / MSX-DOS BDOS call table | sourced |
| BDOS call `Set DTA Address` (DE = new DTA) | $1A | MSX2 TH / MSX-DOS BDOS call table | sourced |
| BDOS calling convention: C = call #, DE = FCB/pointer, A = result | — | MSX2 TH / MSX-DOS BDOS conventions | sourced |
| disk BSAVE header: `[$FE][start:2 LE][end:2 LE][exec:2 LE]` + raw data, start..end inclusive | — | MSX-BASIC file formats, public language reference | sourced |
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

**Functional validation (openMSX, `disk_probe_bload_disk.py`).**
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
cassette-only `do_cload` (`CLOAD`) is untouched. The disk path parses the FCB
via the shared `parse_disk_fcb`, then the `,R` tail (so `LOAD"A:PROG.BAS",R`
sets `RUNFLAG`), calls `disk_prog_load`, and — iff `RUNFLAG` — `jp run_prog` to
RUN the freshly loaded program (LOAD",R" = load and run, standard MSX
behaviour).

**⚠️ D-FNEXPR2 (2026-08-21) falsified two sentences that stood here, and they
are inverted rather than deleted.** They read: *"The disk path restores the
filename start from the stack (HL is mid-`"CAS:"` compare and not
trustworthy)"*, and *"then `parse_close_run`"*. Both were true of the
hand-rolled `"CAS:"` compare loop and the literal-quote gate this verb used to
carry. Neither is now: the compare is `dev_cmp`, which restores HL itself on a
miss (so the `push`/`pop` pair the first sentence described no longer exists —
it was the THIRD hand-rolled copy of `dev_cmp` in the tree and D-FNFUND had
collapsed only the two in `save.asm`); and the argument is a string EXPRESSION
staged in `STRSCR`, so there is no closing quote in the program text to consume
and the tail is entered at `pcr_noquote` with the cursor reloaded from
`FN_RESUME`. The analysis is kept because the reason it was written down — HL
is not trustworthy across a device-prefix compare — is exactly why `dev_cmp`
has the contract it has. No new token: `LOAD` already exists as `LOAD_TOKEN`
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
the `$FF` tokenised form is loaded. Source: **MSX-BASIC file formats** (an allowed public MSX-BASIC language reference — the same
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
| `BASIC_DISK_ID` (on-disk tokenised-BASIC marker) | $FF | MSX-BASIC file formats, public language reference | sourced |
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

**Functional validation (openMSX, `disk_probe_load_disk.py`).**
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
  (the SAME reusable load `LOAD"name"` uses), then — **`ret c` and
  `jp run_prog_top`** (D-RUNTAIL, see below). Net effect: load the tokenised
  program, then run it. This mirrors `do_load`'s disk path exactly, minus the
  `RUNFLAG` test.
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

### 🔴 D-RUNTAIL — this section was wrong on BOTH halves, and both were measured

`docs/spec-basic-runtail.md`, measured in
`docs/runtail-msx1-characterization.md` on the National CF-3300 (2026-08-07).
Gate: `make runtail-acceptance` (9/9 readings agree across cf3300 + zb).

**(1) "RUN always runs" was false about the machine.** After a load that FAILED,
the CF-3300 prints its message and stops — it does **not** run whatever program
happens to be resident. zerobas did: `load_error` prints and **returns**, and
`do_run`'s next instruction was `jp run_prog`. `disk_prog_load` now carries a
CF-out contract (CF set = the load failed and has already reported) and both
callers `ret c`. The contract is stated on `disk_prog_load`'s own exits and
**not** inside `load_error`, which has ~50 sites across `files`/`save`/`print`/
`field`/`format`/`bload`/`cload`, several of which resume into their caller on
purpose.

**(2) `jp run_prog` from a statement entered the run loop NESTED.** `RUN"A:name"`
is not the REPL's `RUN` command (`is_cmd` needs a delimiter after "RUN" and this
one is `"`), so it reaches `do_run` as a crunched statement, inside the enclosing
line's own run loop. `run_prog` overwrites `CURLINE`; when the loaded program
ended, its `ret` landed back in `exec` and the **enclosing** loop resumed with
`CURLINE` pointing at the loaded program's end marker, walked off it into
`CURLINE := $0000`, found the page-0 ROM's own non-zero `DI / JP` there and
dispatched the byte at `$0004` as a BASIC statement — in RUN mode. Observable:
`Illegal function call in 3346` after **every** `RUN"file"` and `LOAD"file",R`,
hit and miss alike, `3346` being the word at `$0002` printed as `CURLINE+2`.
Both sites now `jp run_prog_top`, which restores `SAVSTK` — the prompt-clean
depth `dispatch_line` records before any statement runs — so `run_prog`'s `ret`
returns to the REPL exactly as the bare-`RUN` command path's always did.

✅ **The tape twins are CLOSED by D-CASTAIL** (`docs/spec-basic-castail.md`,
measured in `docs/castail-msx1-characterization.md`). `dl_cas_close` and
`dr_is_cas` had **both** defects, not only (2), and both are fixed the same way:
`jp run_prog_top`, and a CF-out contract on `do_tape_prog` consumed by `ret c`.
See §cassette program load below. This paragraph previously said they were
"deliberately unchanged"; that was true at `3e84afa` and is no longer.

**Functional validation (openMSX, `disk_probe_run_disk.py`).**
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
regression `disk_probe_load_embedded_nul.py` loads
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

Oracle confirmation: `disk_probe_save.py` — three round-trips on
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
`SAVE"CAS:name"` (✅ **ASCII since D-CASSAVE, `,A` or not** — see below) and
`BSAVE"CAS:name",start,end[,exec]` (binary)
write a real cassette file through the zerobas-tape **write** signal layer
(`TAPOON $00EA` / `TAPOUT $00ED` / `TAPOOF $00F0`, already implemented in
`tape/tape.asm`, reached via the cassette BIOS vectors). Same two-block cassette
file layout the read side consumes and that `cas_encode.py` (`build_cas` /
`build_cas_basic`) documents:

- **Header block** (`TAPOON` long): the file-type id ×10 — `$D3` for tokenised
  (CSAVE — **not** `SAVE"CAS:"`, D-CASSAVE), `$EA` for the ASCII listing
  (`SAVE"CAS:"`, `,A` or not), `$D0` for binary (BSAVE) — then the 6-char space-padded
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
| `SAVE"CAS:"` / `CSAVE` write the **tokenised** ($D3) format (no ASCII save) | diverged | own-design descope (matches zerobas's tokenised disk SAVE; ASCII detokeniser is Phase 2) | ✅ **WITHDRAWN by D-CASSAVE** — was quarantined |
| `SAVE"CAS:name"` writes the **ASCII** ($EA) format — the full listing, `,A` or not | — | oracle, **both** references, decoded off the recorded tape (`cassave` `sav-cas:id`/`:text`, `sav-cas-bare:*`) | sourced |
| `CSAVE"name"` writes the **tokenised** ($D3) format, and is NOT the same verb | — | oracle, both references, same decode (`cassave` `csave:id`/`:text`) | sourced |
| `SAVE"CAS:name"` and `SAVE"CAS:name",A` are ONE behaviour (same id, name field and payload text) | — | oracle, both references (`cassave` `sav-cas*` vs `sav-cas-a*`) — the reading that says routing them to one path is faithful and not a conflation | sourced |
| 6-char filename truncation / space-pad; bare `CSAVE` → 6 spaces | — | MSX cassette format (6-char name); bare-name default is own design | sourced |
| `TSV_PTR`/`TSV_END`/`TSV_CNT`/`TSV_NAME` tape-write scratch | $E0F1/$E0F3/$E0F5/$E0F6 | own choice (free page-$E0 RAM, collision-checked clear of `DSV_*`/read-side scratch) | sourced |

### 🔴 D-CASSAVE — `SAVE"CAS:name"` writes an ASCII tape

**Closed 2026-08-07.** Gate `probes/basic/basic_probe_cassave.py`
(`make cassave-acceptance`, **20/20 readings**), spec
`docs/spec-basic-cassave.md`, reading `docs/cassave-msx1-characterization.md`.
Closes the residual D-DOTGAPS filed (`docs/dotgaps-msx1-characterization.md`
§3.2) and pinned as `csv-tok`.

On an MSX1 `CSAVE` is the tokenised cassette write and `SAVE"CAS:"` is the ASCII
one, **`,A` or not**. zerobas wrote `$D3` there, and its own `basic/save.asm`
header table *documented that as intended* — so the row that first looked like a
cassette-specific `.` defect was the symptom of a **format** divergence. Fixed for
**0 B**: `sav_is_cas`'s no-flag arm now `jp cas_ascii_save` instead of
`jp tape_save_basic`, one absolute jump for another.

🔴 **A 0-BYTE FIX IS THE SHAPE THAT HIDES A CONFLATION, and this one was
nameable**: it makes `SAVE"CAS:x"` and `SAVE"CAS:x",A` literally one code path,
and a one-line diff cannot say whether that merged two things which should stay
apart. Measured instead — both forms, both references, decoded off the recorded
tape: same id, same name field, identical payload text. Refuted, not assumed.

🔴 **AND THE FILED READING WAS ONE MACHINE.** §3.2 decoded the VG-8020 only.
Re-specifying a **shipped** save format on one machine's word is what the
two-reference rule exists to stop; the CF-3300 agrees on all twenty readings.

🟢 **`CSAVE` is the control that keeps the claim narrow** — `$D3` on all three
sides, untouched — and `basic_probe_tape_save.py`'s `test_save_cas_format`
asserted the *tokenised* form for `SAVE"CAS:"`, i.e. the tree carried a GREEN
oracle for the defect. That expectation is inverted in the same commit.

Oracle confirmation: `basic_probe_tape_save.py`, three independent
oracles on `C-BIOS_MSX1_EU_TAPE` (zerobas-tape write layer) with `basic.rom` as a
cart — (1) **format**: zerobas writes a tape, openMSX records the CAS-out, `cas_decode`
yields bytes byte-identical to `build_cas`/`build_cas_basic` (CSAVE / BSAVE; the
`SAVE"CAS:"` oracle is the ASCII listing since D-CASSAVE); (2) **cross-read**: the
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

**`LFILES` — the printer twin (D-LFILES, 2026-08-06,
docs/spec-basic-lfiles.md).** Token `LFILES = $BB`, oracle-LOCKED from D-LNREF's
crunch walk. `ex_lfiles` and `ex_files` are the SAME head: they differ in one byte
of immediate data, the `DISKOP_SEL_*` op, which is simultaneously the tenant
selector, the **sink** selector and the **layout** selector.

🎯 `LFILES` is **not** `FILES` with the sink moved, and that is a MEASURED rule
(R-LF1, docs/lptverb-msx1-characterization.md §4, National CF-3300): the screen
form packs three 12-char fields per row, the printer form prints **one entry per
line**, each field followed by a trailing space (R-LF2) and CR/LF. The wrap
arithmetic reads `CSRX`/`LINLEN` — the *screen* cursor and the *screen* width — and
a printer moves neither, so on the printer it does not merely produce the wrong
layout: with `CSRX` frozen it collapses to no separator and no line break at all,
which is a layout that exists on neither device. Measured directly by knife K3.

A filespec filters with 8.3 `'*'`/`'?'` wildcards (R-LF3), and a filespec that
matches nothing prints nothing and raises **ERR 53 `File not found`** (R-LF4) — on
the SCREEN, since the message resolves through `raise_error` and the sub-hosted
`em_file_notfound`, not through the listing's sink. R-LF6 measured the same answer
for `FILES`, so the message lives in the shared walk.

**Home.** The directory walk and the entry emit are **not** main-resident: they are
`tnt_files` in the sub-ROM page-1 `dirverb_tenant` (`sub/dirverb.asm`,
`DISKOP_SEL_FILES`/`DISKOP_SEL_LFILES`), the eviction Phase 2 listed and dropped.
What stays in `basic/files.asm` is the head the head/body split forces: the
`DISKSLOT_OK` test, the eval-side `parse_disk_fcb`, one `subrom_call`, and the
statement tail. The move is behaviour-preserving for `FILES` because `print_crlf`
is `pchar(13)+pchar(10)` and `pchar` with `PRDEST=0` — which `exec_stmt` guarantees
at the top of every statement — *is* `call CHPUT`.

**Divergences (own design, quarantined):**
- On a missing disk slot / mount / I-O error `FILES`/`LFILES` reuse the loader's
  `load_error` path ("load error"), not a Disk-BASIC-specific "Disk offline"
  message — own-design error wording, consistent with the other disk verbs. Only
  the **no-match** disposition is reference-exact (`File not found`).
- ~~A bare `FILES`/`LFILES` over an **empty** directory prints nothing rather than
  `File not found`.~~ ✅ **CLOSED 2026-08-07 by D-DSKMSG.** The fixture now exists
  (`tools/make_test_dsk.py --empty`) and the reading is **R-LF7**
  ([`lptverb-msx1-characterization.md`](../docs/lptverb-msx1-characterization.md)
  §4.2): the reference raises `File not found` for a bare `FILES` *and* a bare
  `LFILES` over a mounted, writable, empty volume — the SAME disposition as a
  filespec that matched nothing, not a different one. `tnt_files` now seeds
  `DISKOP_STATUS` at "nothing matched" unconditionally (−4 B of sub page 1).
- The disk-name header / "Ok" framing around the listing is the REPL's, not emitted
  by `do_files`.
- ⚠️ The paragraph that used to stand here — *"an optional `<filespec>` pattern
  argument is parsed-past and IGNORED; pattern matching is a later Phase-2 item"* —
  was **stale**, and had been since the wildcard work landed (`build_83_name`'s
  `'*'` expansion + `name_cmp`'s `'?'`). `basic/files.asm`'s own header carried the
  same dead sentence directly above code that parses and applies the pattern.
  Corrected by D-LFILES, which had to read both to size the carve.

Clean-room: original code; FILES *semantics* + the 8.3 field layout from the public
MSX-BASIC language reference and black-box CF-3300 observation; the directory walk
reuses fat.asm primitives. No disassembly. See file-channel-protocol.md.

## file channel — sequential read (OPEN/INPUT#/LINE INPUT#/CLOSE) (basic/files.asm, basic/interp.asm, basic/sysvars.inc)

Phase 2's sequential file-channel **read** path, EXTEND over the existing fat.asm
sequential reader (`fat_io_open` / `fat_io_getbyte`) per the Step-0 verdict
(file-channel-protocol.md §4/§5: the file verbs share the standard DSKIO+FAT12
substrate, so they layer on the loader's engine).

**Statements (basic/files.asm).**
- `OPEN "name" FOR INPUT AS #n` — `do_open` parses the filename with the
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
yet implemented; the comma-zone wrap divergence of screen PRINT (PROVENANCE.md
§PRINT) applies equally to PRINT#; disk-full write errors reuse `load_error`.
⚠️ **"not-open" is NO LONGER on that list** — D-NOTOPEN (2026-07-31,
`docs/spec-basic-chan-notopen-err59.md`) measured the CF-3300 raising a trappable
ERR 59 `File not OPEN` for `PRINT #n` / `INPUT #n` / `LINE INPUT #n` on a channel
that was never opened, and zerobas now matches (`fch_mode_class`, basic/expr.asm).
`PRINT# USING` (the file form) IS supported (repack) and CF-3300-
validated byte-for-byte (`disk_probe_printusing_file.py`); ex_print dispatches a
USING after a #channel into printusing.asm with PRDEST=1. The format-copy fix that
made it correct (pu_deref_body must preserve A across the length→ldir-count window,
or the copy overruns the literal into the token stream) is in basic/str-engine.asm +
docs/spec-print-hash-using.md.

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

**Statement (`do_kill`, basic/files.asm).** Parses the filename with the
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

**Wildcard (2026-07-08, option-closure Item 4):** `KILL "*.BAK"` deletes EVERY
matching file — `do_kill` loops `fat_delete` (whose `fat_find`/`name_cmp` now honour
the `?` wildcard; `build_83_name` expands `*`→`?`) until no match remains, and raises
File-not-found only if nothing matched. Byte-identical to the real
CF-3300 after the same wildcard KILL (`disk_probe_kill_wildcard.py`), confirming
CF-3300 wildcards identically.

**No-match wording (2026-08-07, D-DSKMSG).** ✅ `KILL` at a filespec that matches
nothing raises **ERR 53 `File not found`** through `raise_error` — reference-exact,
measured as **R-DK1** on the CF-3300
([`dskmsg-msx1-characterization.md`](../docs/dskmsg-msx1-characterization.md)).
It used to reuse `load_error` ("load error") while the code's own comment said
`File not found`; the reading settled which was right, and
`make fat-error-acceptance`'s `kill-missing` pin moved in the same commit.
`ERR` now reads 53 and `ON ERROR` traps it, where neither happened before.

🔴 **That was NOT the 0 B jump-target swap it was filed as**
([`spec-basic-dskmsg.md`](../docs/spec-basic-dskmsg.md) §4.1). `fat_delete`
returns `Cy = 1` for *not found / mount / I-O error* alike, so `tnt_kill`'s
deleted-any flag was 0 for all three; re-pointing the head alone would have turned
a disk-offline `KILL` into a trappable ERR 53 on no evidence. The tenant now
mounts first and returns `DISKOP_STATUS = 2` for a mount failure, exactly as
`tnt_files` does. **Divergence (own design, quarantined, NARROWED):** a missing
disk / mount / I-O error still reuses `load_error`; only the **no-match**
disposition is reference-exact. An I-O error inside `fat_delete` after a
successful mount and before any deletion still reads as "nothing matched" — stated,
not measured.

⚠️ **`NAME` was measured at the same time and deliberately NOT changed** — for
**one slice**. R-DK2: the CF-3300 answers `File not found` to `NAME` at a missing
old file too, and `nm_fail` was a shared exit for the mount failure and the
not-found miss, so making it reference-exact was an arm split, not a target swap.
✅ **That split landed 2026-08-07 (D-DKNAME); see §NAME below.** The row is gated
and the printed not-gated line is gone with it.

Clean-room: original code; KILL semantics + the `$E5` deleted-marker / chain-free
rules from the public MSX-BASIC reference + Microsoft FAT spec, validated by the
byte-identical CF-3300 differential. No disassembly.

## NAME — rename a file (basic/files.asm, basic/interp.asm, basic/sysvars.inc)

`NAME "old" AS "new"` renames a file by overwriting its directory entry's 8.3 name
field — no FAT change (the clusters and size are untouched). EXTEND over fat.asm,
reusing `fat_find`'s recorded entry location (`FWR_DIRSEC`/`FWR_DIROFF`).

**Statement (`do_name`).** Parses the OLD name (`parse_disk_fcb` → `DISK_FCB_NAME`),
the verbatim-ASCII `AS`, then EVALUATES the NEW name. It finds the OLD
file FIRST (recording the entry location) because building the NEW name reuses
`DISK_FCB_NAME`; then parses the NEW name, re-reads the directory sector, `LDIR`s
the new 11-byte 8.3 field over the entry, and writes the sector back.

⚠️ **TWO CLAIMS THAT STOOD HERE UNTIL 2026-08-21 ARE NOW INVERTED, AND THE
ANALYSIS IS KEPT BECAUSE IT IS WHY THE NEW SHAPE IS SAFE.** This paragraph used
to read *"checks the NEW name's opening quote"* and *"HL (the text cursor) is
guarded on the stack across every CALSLT (`fat_mount`/`fat_find`/`read_sector`/
`write_sector`)"*. Both were true and both were falsified by D-FNEXPR
([`../docs/spec-basic-fnexpr.md`](../docs/spec-basic-fnexpr.md)):
* there is **no opening-quote check** any more — a filename argument is a string
  EXPRESSION, evaluated by `fname_expr`, of which a literal is one case;
* HL is **no longer guarded on the stack** across those CALSLTs, because the text
  cursor lives in `FN_RESUME` ($E227) instead. The guard's whole job was to carry
  a cursor across a call that clobbers the register file, and a RAM cell does that
  without a stack discipline three exits had to balance — `nm_fail`, `nm_fail2`
  and `nm_notfound` each shed the `pop hl` that existed only for it.
The HL-clobber rule the guard came from is UNCHANGED and still governs everything
else in this file; what changed is where `do_name` keeps the cursor, not whether
CALSLT clobbers it. Token `NAME = $D3` oracle-LOCKED byte-identical to
the Philips VG-8020 crunch (`basic_probe_crunch.py`; MSX2 TH Table 2.20). Note the
token VALUE ($D3) equals `BASIC_ID` (the cassette tokenised-BASIC marker) but lives
in a different namespace — separately-named constants, like SAVE/BSAVE.

**Validation** (`disk_probe_name.py`, /tmp copy of `test720.dsk` — committed image
never mounted): `NAME "HI.TXT" AS "BYE.TXT"` leaves HI.TXT gone and BYE.TXT present
with the **same first cluster (4), size (26), and data** ("Hello from
zerobas-disk!\r\n"); and the resulting **disk image is byte-identical to the real
CF-3300** after the same NAME (rename rewrites only the one entry's 8.3 field).
Full crunch + 16 unit-test files + the FILES/read/write/KILL probes still pass.

**Missing-old-file wording (2026-08-07, D-DKNAME).** ✅ `NAME` whose OLD file
does not exist raises **ERR 53 `File not found`** through `raise_error` —
reference-exact, measured as **R-DK2** on the CF-3300
([`dskmsg-msx1-characterization.md`](../docs/dskmsg-msx1-characterization.md) §2,
taken by D-DSKMSG one slice earlier). It used to reuse `load_error`, which this
section stated outright; the reading settled it and
`make fat-error-acceptance`'s `name-missing` pin moved in the same commit as the
code. `ERR` now reads 53 and `ON ERROR` traps it, where neither happened before.

🔴 **That was an ARM SPLIT, not the jump-target swap the residual filed**
([`spec-basic-dkname.md`](../docs/spec-basic-dkname.md) §2). `nm_fail` was a
SHARED exit for the `fat_mount` failure *and* the `fat_find` miss — both reached
it via `jr c,nm_fail` — so re-pointing it would have moved a disk-offline `NAME`
to a trappable ERR 53 on no reading at all, the same conflation D-DSKMSG found in
`do_kill`. The miss got its own exit (`nm_notfound`), the mount kept
`load_error`. **+4 B of main page 1, 0 B of sub-ROM** — `NAME`'s tenant is the
stamp only, so `sub.rom` is byte-identical across the change.

⚠️ **And the conflation went one level deeper than the residual said.**
`fat_find`'s own contract is `Cy = 1 not found / error` — it does `ret c` on a
`read_sector` failure mid-scan — so an I-O error during the root-directory walk
now reads as `File not found` too. Stated, not measured; `KILL` has the identical
residual one primitive over. Separating either needs a status out of the
primitive, which `tnt_files` has and `NAME` does not.

**Divergences (own design, quarantined):** no "new name already exists" check (a
later refinement); the drive prefix on either name is accepted and ignored for the
stamp (single drive); a missing disk / mount failure / stamp I-O error still
reuses `load_error`, and no row anywhere drives that arm (D-DKNAME's knife
K-NAME2 is the written-down predicted miss that proves it). Only the
**missing-old-file** disposition is reference-exact.

Clean-room: original code; NAME semantics + the 8.3 dir-field layout from the public
MSX-BASIC reference + Microsoft FAT spec, validated by the byte-identical CF-3300
differential. No disassembly.

## EOF / LOF — file-info functions (basic/expr.asm, basic/interp.asm, basic/sysvars.inc)

The first file-channel **functions** (the verbs so far were statements). Evaluated
as `$FF`-prefixed function factors in `ev_f_ff`, alongside PEEK/VPEEK/INP.

- **`EOF(#n)`** — returns -1 ($FFFF) once every byte of the open input file has
  been delivered (`FREAD_LEFT`, the read engine's 4-byte undelivered-count, == 0),
  else 0. The channel argument is parsed but ignored (single channel).
- **`LOF(#n)`** — returns the open file's length in bytes: `FAT_FILESIZE`, low 16
  bits. Argument parsed + ignored.
  **D-LOF (2026-07-31, `docs/spec-basic-lof-size-field.md`)**: `fat_find` sets that
  field only when a file is FOUND, so until this slice every CREATE path left it
  holding the previous tenant of the `FCH_STATE0` span — measured at 26 and at
  2048, and at `$FFFF` (= −1) after a cold boot, which is where the filed
  "`LOF` reads −1" came from. Nothing ever stored `$FFFF`. Now zeroed in
  `fat_io_create` and in `fat_rand_open`'s create arm, and grown by
  `frnd_update_size` on a RANDOM `PUT`. **Measured rule** (CF-3300,
  `docs/lof-cf3300-characterization.md`): the field is in RAM, **not** read from
  the directory — after `PUT #1,1` the reference reports `LOF` = 256 while the
  on-disk directory entry still holds 0 — seeded at OPEN (directory size for an
  existing file, 0 for a created one), unmoved by a sequential `PRINT #`, grown by
  a RANDOM `PUT`. The directory is stamped from `FWR_BYTES` at CLOSE, never from
  this field, so it cannot reach the disk.

**Tokens** `EOF = $FF $AB`, `LOF = $FF $AD` — oracle-LOCKED byte-identical to the
Philips VG-8020 crunch (`basic_probe_crunch.py`: `a=eof(1)`→`… FF AB 28 12 29`;
MSX2 TH Table 2.20). Added to `kwtable` as 2-byte `PEEK_PREFIX`-prefixed entries
(the same shape as VPEEK/INP); detok is the table-driven `detok_kw2`.

**Validation** (`disk_probe_eof.py`, /tmp copy of `test720.dsk`; HI.TXT is 26
bytes): `OPEN…INPUT…:PRINT LOF(1);EOF(1):CLOSE#1` prints `26  0` — and the real
CF-3300 prints the same two values (read-model-independent differential). After
exhausting the file (two LINE INPUT#), `PRINT EOF(1)` prints `-1`. Full crunch +
16 unit-test files + the FILES/read/write/KILL/NAME probes still pass.

**Divergences (own design, quarantined):** single channel — the argument selects
no distinct channel; `LOC` (sequential record position) and `DSKF` (free clusters)
are deferred (LOC's record semantics + DSKF's free-space scan are separate items);
LOF returns the low 16 bits (files ≥ 64 KB are out of the loader's scope).

Clean-room: original code; EOF/LOF semantics from the public MSX-BASIC reference,
validated by the CF-3300 differential. No disassembly.

## DSKF — free disk space (basic/expr.asm, basic/fat.asm, basic/interp.asm, basic/sysvars.inc)

`DSKF(d)` returns the number of free clusters on the drive (= free KB on the
1 KB/cluster 720 KB volume). A `$FF`-prefixed function (`DSKF = $FF $A6`,
oracle-locked to the VG-8020 crunch; MSX2 TH Table 2.20), evaluated in `ev_f_ff`.

**Engine (`fat_count_free`, basic/fat.asm).** Mounts, takes `fat_total_clusters`,
then walks every data cluster `[2, total)` and counts the FAT entries equal to 0.
A naïve one-`fat_next_cluster`-per-cluster scan is ~700 cross-slot DSKIO reads —
far too slow on a real FDC (observed: it did not finish in ~30 emulated seconds).
So `fat_count_free` **caches the current FAT sector** (in `FSECTOR_BUF`, keyed by
`FWR_FIRST`) and decodes the 12-bit even/odd-packed entry inline, re-reading only
when the cluster crosses a sector boundary (plus a one-byte straddle read at the
512-byte boundary) — collapsing it to a handful of reads. Loop state lives in RAM
(read_sector's CALSLT clobbers the register file): `FAT_WRTMP`/`FAT_WRTMP2`/
`FWR_CLUS`/`FWR_FIRST` (write-side scratch, dead during this read-only query) +
`FAT_B0`/`FAT_B1`. Sources: Microsoft FAT spec (a 0 entry is free; the nibble
packing).

**IX guard.** `ev_ff_dskf` pushes IX/IY across `fat_count_free`: CALSLT clobbers
IX, and IX is the evaluator's live token cursor. (The first cut omitted this and
the evaluator ran off into garbage after DSKF returned — a runaway that filled the
screen with `0`s; the fix is the same register-guard discipline as the statement
verbs, applied to the evaluator's cursor register.)

**Validation** (`disk_probe_dskf.py`, /tmp copy of `test720.dsk`): `PRINT DSKF(0)`
prints **707**, matching both a direct FAT12 free-cluster count of the image and
the real **CF-3300** (707). Full crunch + 16 unit-test files + the EOF/file probes
still pass.

**Divergence (own design):** single drive — the argument is parsed and ignored.

## LOC / LFILES — observed and DEFERRED (not implemented)

Two "small" verbs were **observed on the real CF-3300 and deliberately left out**,
with the observations recorded so the decision is grounded, not guessed:

* **`LOC(#n)` ($FF$AC).** On the CF-3300, `LOC(1)` returned **26 both immediately
  after OPEN and after a LINE INPUT#** of the 26-byte HI.TXT — i.e. it tracks
  neither bytes-read nor a record index in any way that matched the documented
  "records since OPEN". Its sequential-file semantics are quirky and unclear;
  reproducing the literal value without understanding it would be cargo-culting,
  which the clean-room rule forbids. Deferred until the semantics are pinned.
* **`LFILES` ($BB).** The line-printer counterpart of FILES — it directs the
  directory listing to the printer device (LPT), which zerobas has no driver for.
  Out of the loader/disk scope; deferred (would need a printer-output layer).

Both tokens are documented here so a future pass starts from the observation, not
from scratch.

## MAXFILES — multi-channel file table (basic/files.asm, basic/interp.asm, basic/print.asm, basic/expr.asm, basic/sysvars.inc)

`MAXFILES = n` sets how many sequential file channels may be open at once (and
bounds every `OPEN`/`INPUT#`/`PRINT#`/`CLOSE`/`EOF`/`LOF` channel number). This
**retires the single-channel limit** every Phase-2 file verb previously shared.

**Token (oracle-locked).** "MAXFILES" crunches to **TWO** reserved words —
`MAX` (`$CD`) + `FILES` (`$B7`) — exactly like `OUTPUT` = `OUT`+`PUT`. Proven
byte-identical on the diskless **Philips VG-8020** (`basic_probe_crunch.py`):
`max` → `$CD`, `files` → `$B7`, `maxfiles=2` → `$CD $B7 $EF $13`. So zerobas adds
a single `MAX` reserved word; the tokeniser then forms "MAXFILES" = MAX + FILES,
and the statement is dispatched on `$CD` (then requires `$B7`). MSX2 TH Table 2.20.
No disassembly — only the observed crunch bytes.

**Architecture — a write-back context cache over the unchanged `fat.asm`.** The
engine keeps ONE global set of streaming state (the 512-byte `FSECTOR_BUF` data
buffer + the `FREAD_*`/`FWR_*`/`FAT_CUR*` cursor span). Rather than refactor that
oracle-validated engine to be channel-indexed (deep, risky), each open channel
owns a **context block** `FCH_CTX[ch]` = `[state:FCH_STATESZ][buffer:512]` holding
a saved copy; the globals always hold the **active** channel's live state. The
channel manager (basic/files.asm) is the cache:
* `FCH_ACTIVE` names the channel whose state is live; `FCH_MODE`/`FCH_NUM` mirror
  it, so the existing read/write/PRINT# code (which reads those + the globals)
  works **unchanged**.
* `fch_select(ch)` makes `ch` live: if a different channel is active it **saves**
  the globals to that channel's ctx and **loads** `ch`'s — a write-back swap. Re-
  using the same channel back-to-back (the common case) copies nothing.
* `fch_claim(ch)` (used by OPEN) makes `ch` active without loading its about-to-be-
  overwritten ctx, saving any other active channel first.
The per-channel state span `FCH_STATE0..+FCH_STATESZ` (`$E9C9..$E9FA`, 50 bytes)
covers every value that must persist between statements for an open channel — the
read iterator, file meta (`FAT_FILESIZE` for LOF), the read stream, and the whole
write state. The mount geometry proper (`$E9C0..$E9C8`) stays **shared** below the
span — correct for a single drive (every `fat_mount` re-derives it identically).
`fat.asm` is byte-for-byte untouched; all its differential validation still holds.

**Dynamic allocation, ceiling 15 (D-FCH, repack build).** ⚠️ The paragraph this
replaces described a **562-byte static block and a RAM-bounded ceiling of 2**;
both are gone. `docs/spec-basic-filechan-alloc.md`:

* **§3.1 (S-FCH-1)** retired the 512-byte half — it was purely a *save copy* of
  the one global `FSECTOR_BUF`, which is now a real write-back cache
  (`fat_detach_channel` flushes the dirty partial sector in place,
  `fat_restage_channel` reads it back). A block is the 50-byte state span alone.
* **§3.2** made the table **dynamic**: it is carved out of the pool at
  `MAXFILES` time, immediately below the string-pool floor, at
  `min(HIMEM,TXTMAX) − POOLSIZE − MAXF×FCH_CTXSZ` — derived, never stored
  (`strheap_varceil`, `sub/strheap.asm`; `fch_ctx_addr` asks for a block through
  op 18). So `MAXFILES=n` costs **50 B per channel out of `FRE(0)`** and nothing
  is charged for channels a program never asks for, which is the mechanism the
  **reference** uses (measured: it charges 267 B/channel out of its own `FRE(0)`
  pool, `docs/chancost-cf3300-characterization.md`). `FRE("")` is untouched.
  `FCH_CEIL` is now **15**, the measured reference ceiling.
* `MAXFILES` also **CLEARs variables unconditionally**, even when the value does
  not change — measured on the CF-3300, and required for safety here anyway
  since the statement moves the variable region's ceiling.
* *(historical)* Until 2026-07-29 everything above was gated `IF ROM_BASE <
  $4000`, because the lean 16 KB cart kept the old static `[state][buffer]`
  table at `FCH_CTX = $EA00` with `FCH_CEIL = 2` and its byte-identity was a
  build gate. **That cart is retired** and there is now one build
  ([`docs/spec-lean-retire-s3-gates.md`](../docs/spec-lean-retire-s3-gates.md));
  the dynamic table above is simply what ships. Nothing here constrains new
  channel-table work.

The DEFAULT is
`MAXFILES = 1` (observed: `OPEN #1` works with no MAXFILES on the CF-3300). Like
the reference, `MAXFILES` reinitialises the file system — every open channel is
closed first (OUTPUT ones flushed + Ctrl-Z-stamped, via `fch_close_all`). Bare
`CLOSE` now closes **all** open channels (faithful), not just one.

**Register discipline.** Statement callers guard their `HL` text cursor across
`fch_select`; the `EOF`/`LOF` function callers, and `INPUT$`, rely on the
evaluator's `IX` token cursor surviving. ⚠️ **In the repack build the manager
now CONTAINS CALSLTs** (the D-FCH cache flush/re-stage, and the block-address
op), where it originally moved state with `LDIR` alone and needed no guard at
all. That contract is honoured by **one** `push ix` hoisted into `fch_select` —
the single door every `IX`-critical caller enters through; `fch_claim`'s only
caller (`do_open`) keeps its cursor in `HL` and already guards for CALSLT. Any
NEW caller of `fch_ctx_addr`/`fch_save_active`/`fch_load_ctx` must be checked
against this. The first cut of OPEN's success
path computed the `FCH_MODES[ch]` address into `HL`, clobbering the text cursor
before `jp exec_stmt` — so OPEN opened the file yet then executed from garbage
(a spurious "syntax error"); the fix guards `HL` across the table write.

**Validation.** `disk_probe_maxfiles.py` (/tmp copy of `test720.dsk`): two OUTPUT
files are opened **at once** and written **interleaved** (`PRINT #1` / `PRINT #2`
alternating, so each channel's buffered data must survive repeated context swaps),
then a bare `CLOSE` flushes both. On-disk `A.TXT` = `b"aaa\r\nccc\r\n\x1a"` and
`B.TXT` = `b"bbb\r\nddd\r\n\x1a"` — **byte-identical to the real National CF-3300**
given the identical program. The crunch suite (incl. `maxfiles=2`), the 16 host
unit-test files, and every single-channel file probe (read / write / EOF·LOF /
DSKF) still pass.

**Divergences (own design, quarantined):** the per-channel CHARGE is **50 B**
where the reference's is 267 — deliberate, and in the user's favour: a zerobas
block genuinely is 50 B of state (its sector staging is the shared cache), so it
charges what it uses rather than reserving 217 B/channel that nothing reads. The
*mechanism* and the *ceiling* now match. The resume-state RAM layout
(`FCH_MODES`/`FCH_ACTIVE` and the carved block itself) is zerobas's own, not the
reference's FCB/buffer map. ✅ **The `MAXFILES` ARGUMENT DOMAIN IS CLOSED
2026-07-31 by D-MFDOM** (`docs/spec-basic-maxfiles-domain.md`): the statement
takes its argument through `eval_byte_arg`, so the whole domain answers the
reference's class — outside int16 (the **range** −32768..32767, asymmetric)
raises ERR 6 `Overflow`; inside int16 but outside `0..FCH_CEIL` raises ERR 5
`Illegal function call`, negatives included; a fractional value **truncates** and
is then judged on the integer (`15.9` is accepted as 15, `2.5` becomes 2). All
measured on the CF-3300 across fourteen rows, not inferred from `CHR$`.
🔴 Before it, an argument **outside int16 was accepted SILENTLY as
`MAXFILES=0`** — every file channel disabled with no error — because `eval`'s
`flt_to_int16` zeroes `DE` for those and the hand-inlined high-byte test could
therefore never fire. The channel-NUMBER side was closed separately by
D-BADFNUM. ⚠️ **Partly closed 2026-07-31 by D-NOTOPEN**
(`docs/spec-basic-chan-notopen-err59.md`): a channel that is IN RANGE but NOT OPEN
now raises the reference's trappable ERR 59 from `PRINT#`/`INPUT#`/`LINE INPUT#`
as well as from `EOF`/`LOF`. ⚠️ **Closed further 2026-07-31 by D-NOTOPEN2**
(`docs/spec-basic-gpfi-notopen-err59.md`): `GET`/`PUT`/`FIELD`/`INPUT$(n,#f)` now
answer the reference on the WHOLE channel-mode grid, not just the not-open column.
Measured across every `FCH_MODES` value, both machines — the reference uses **five**
codes here and zerobas had two of them:

| channel | `GET`/`PUT` | `FIELD` | `INPUT$` |
|---|---|---|---|
| not open | **59** | **59** | **59** |
| open, disk, not RANDOM | **61** | **61** | **55** |
| open RANDOM | *(works)* | *(works)* | **61** |
| open `LPT:`/`CRT:` | **58** | **5** | **55** |

⚠️ Note `LPT:` answers **58** to `GET` and **5** to `FIELD` — the device rule is
per-verb, not one code. 🔴 And `FIELD` on a sequential channel used to be accepted
**SILENTLY** (nothing raised at all); that is the half of this that was a missing
check rather than a wrong code. ERR **55**/**58**/**61** are new to zerobas and are
served by `rerr_sparse2` (basic/missing.asm tail), a second sparse arm sited in
page 1 so the page-0 low region paid **zero** bytes for them.
⚠️ **`rerr_sparse2` NO LONGER EXISTS** — D-MSGMIGRATE (2026-08-02) moved all three
messages into the sub-ROM tenant (`sub/errmsg.asm`, keyed on ERRFLG), at which
point every arm of that routine read `ld hl,err_subhosted / jp raise_error_hl`,
which is what `rerr_unprintable` already was, and both sparse arms were deleted.
**The measurements in this table are unchanged and still binding** — they are what
the tenant's rows now have to honour, and `sparse-trap`
(`basic_probe_msgexact.py`) is what pins that these codes still TRAP rather than
print. Only the routing moved.

✅ The OUT-OF-RANGE class **LANDED 2026-07-31** as D-BADFNUM
(`docs/spec-basic-badfnum-channel-class.md`). It was filed as three rows and swept
as a grid of **12 channel-taking verbs × 5 channel classes**, 63 of whose 72 cells
diverged. The reference answers ONE rule — `D != 0` → ERR **5**, channel 0 → ERR
**59**, `> MAXF` → ERR **52** — with exactly two exceptions (`CLOSE #0` no-ops,
`OPEN … AS #0` is 52), so the nine `fch_valid` call sites that had invented **six**
dispositions between them now share one `fch_check`, and `fch_valid` is gone.
⚠️ It was NOT a single choke point in the way the filed item feared, but not for
the reason it gave: `PRINT #0` is ERR 59 and `PRINT #2` is ERR 52, yet BOTH are the
same routine's business — the exceptions are `CLOSE` and `OPEN`, not the codes.
⚠️ The two worst cells were not in the filed rows at all: `EOF`/`LOF` on a rejected
channel **raised nothing and returned a number** (`PRINT LOF(0)` printed ` 0`), and
`CLOSE #2` silently no-opped. ⚠️ The `CAS:` channel modes (7/8) are **NOT measured** —
zerobas sends them down the device arm by analogy with `LPT:`/`CRT:`, which is an
inference, and it is filed as such.

## OPEN … FOR APPEND — extend an existing sequential file (basic/files.asm, basic/fat.asm)

`OPEN "name" FOR APPEND AS #n` opens an existing sequential file and positions the
write cursor at end-of-file, so the following `PRINT#`/`CLOSE` extends it instead
of truncating it (which `FOR OUTPUT` does). A missing file is **REFUSED**, not
created — see the D-APPMISS correction below, which this summary line outlived by
one slice.

**Tokenisation (already byte-identical — no new token).** "APPEND" is **not** a
reserved word in the MSX main ROM, so the tokeniser crunches it as the name
**`APP`** (verbatim ASCII `$41 $50 $50`) followed by the **`END`** token (`$81`) —
"app"+"end". Proven on the diskless **Philips VG-8020** (`max…`-style token probe)
and **byte-identical on zerobas** (which also has no APPEND keyword):
`open"a.dat" for append as #1` → `B0 22…22 20 82 20 41 50 50 81 20 41 53 20 23 12`
on both. So OPEN's mode parser simply matches the literal `APP`+`$81` byte sequence
(alongside `INPUT`=`$85` and `OUTPUT`=`OUT $9C`+`PUT $B3`); nothing new to oracle-
lock in the crunch stream. `basic_probe_crunch.py` carries the case.

**Engine (`fat_io_append`, basic/fat.asm).** Mounts, `fat_find`s the file (which
records `FAT_FIRSTCLUS`/`FAT_FILESIZE` and the dir-entry location `FWR_DIRSEC`/
`FWR_DIROFF` reused at close), then **walks the cluster chain** reusing the read-
side `fat_open`/`fat_read_file_sector` (no new chain logic) — the last data sector
is left in `FSECTOR_BUF`. It then primes the write iterator to RESUME at EOF:
`FWR_CLUS` = the last cluster, `FWR_SECIDX` set so the next flush **rewrites** the
last partial sector (or starts a fresh one if the last sector was full), `FWR_BUFLEN`
= bytes already in that sector, `FWR_BYTES` = current size, `FWR_FIRST` = the
existing first cluster. An empty file resumes from offset 0 reusing its dir entry;
a **missing file is REFUSED** (`ret c` → `do_open`'s `oo_fail` → `load_error`).
fat.asm's READ/WRITE primitives are otherwise unchanged.

⚠️ **Corrected 2026-07-31 (D-APPMISS, `docs/spec-basic-append-missing-refuse.md`).**
This paragraph and `basic/fat.asm`'s comment both used to say a missing file
tail-calls `fat_io_create` — stated as settled CF-3300 parity, citing
`disk_probe_append.py`. It is not parity: measured two-sidedly (screen **and** the
machine's own disk image), the CF-3300 raises `File not found`, opens no channel —
the following `LOF(1)` reports ERR 59 — and writes **no directory entry at all**
(`lof-cf3300-characterization.md` §4). The cited probe creates its file with
OUTPUT first and only ever appends to an EXISTING one, so its parity claim is real
for the Ctrl-Z resume rule below and never reached the missing-file case. Now
gated two-sidedly by `diskbasic_probe_lof.py`'s `append_new` (LOF **and** the
directory column) and `append_new_wr` (a `PRINT #1` into the refused channel,
which reads the channel state without going through `LOF`), and on the class side
by `disk_probe_fat_error_disposition.py`'s `append-missing`, beside its
`open-missing` sibling.

**Ctrl-Z soft-EOF rule (CF-3300-observed).** `disk_probe_append.py --show-ref`: a
file written + closed as `"first\r\n\x1a"` (the OUTPUT close stamps a trailing
Ctrl-Z), then re-opened `FOR APPEND` and given `"second"`, becomes
**`"first\r\nsecond\r\n\x1a"`** on the real CF-3300 — the original `$1A` is **gone**.
So APPEND positions the cursor **on** a trailing Ctrl-Z and overwrites it (CP/M text
append), and the new CLOSE re-stamps a single Ctrl-Z. `fat_io_append` reads the
file's last data byte (`FSECTOR_BUF[rem-1]`, or `[511]` for a full last sector) and,
when it is `$1A`, backs the resume position up by one so the marker is overwritten.

**Validation** (`disk_probe_append.py`, /tmp copy of `test720.dsk`): the
create-then-append sequence yields on-disk `AP.TXT` = `b"first\r\nsecond\r\n\x1a"`,
**byte-identical to the real National CF-3300**. The APPEND crunch case, the 16
host unit-test files, and every other file probe (read / write / MAXFILES / EOF·LOF
/ DSKF) still pass.

**Divergences (own design):** APPEND is stored as the OUTPUT mode (2) after open —
the append-vs-truncate distinction only matters at open time, so every later
`PRINT#`/`CLOSE` treats the channel identically; the resume math uses the 16-bit
low word of the size (a >64 KB append is out of scope — loader text files are
small). **A missing file used to be created rather than erroring; corrected
2026-07-31 (D-APPMISS) — it now refuses, as the CF-3300 does.**

## INPUT$(n,#f) — read n raw bytes from a file as a string (basic/strvar.asm)

`INPUT$(n,#f)` reads EXACTLY n bytes from sequential file channel f and returns them
as a string — unlike `INPUT#`/`LINE INPUT#`, it does NO delimiter handling (commas,
CR/LF are taken literally), and the file cursor advances by n. This is zerobas's
first string-returning function.

**Tokenisation (no dedicated token).** "INPUT$" crunches to the `INPUT` token
(`$85`) + a literal `'$'` (`$24`) — not a function token. The args `( n , # f )`
stay literal ASCII (the digits crunch to `$11+d`). Oracle-locked byte-identical on
the VG-8020 and zerobas (`basic_probe_crunch.py`, case `a$=input$(2,#1)` ->
`41 24 EF 85 24 28 13 2C 23 12 29`). So the string evaluator recognises the operand
by the `$85`+`'$'` sequence; nothing new in the crunch table.

**Where it hooks in.** `str_eval` (the HL-based string-operand evaluator) gains an
`INPUT_TOKEN` branch: `$85` followed by `'$'` -> parse `( n , # f )`, else it is not
a string operand. The numeric args use `eval` (which saves/restores the numeric
evaluator's IX cursor); the channel is range-checked + selected with the same
`fch_valid`/`fch_select` as the statement verbs; the bytes come from `fat_io_getbyte`
on the now-live channel. The result fills the existing `STRSCR` `[len][bytes]`
descriptor (so `LET`/`PRINT` consume it unchanged via `STRPTR`/`VALTYP`). Only the
FILE form is supported; the keyboard form `INPUT$(n)` (no `'#'`) is Phase 3 and is
treated as "not a string operand" (the caller errors).

**Register guard (the bug that bit, then fixed).** The read loop's `fat_io_getbyte`
CALSLT clobbers everything, so the count state lives in RAM (`INDLR_N` target,
`IN_RDLEN` stored) and the eval cursor is stacked. The first cut then set
`STRPTR` with `ld hl,STRSCR` AFTER `pop hl` — clobbering the just-restored cursor, so
the read succeeded (a$ was correct) yet the assignment ran from garbage ("syntax
error"). Fix: set `STRPTR` while the cursor is still on the stack, then `pop hl`
(same HL-guard discipline as OPEN's success path).

**Validation** (`disk_probe_inputdollar.py`, /tmp copy of `test720.dsk` whose HI.TXT
begins "Hello from zerobas-disk!"): `A$=INPUT$(5,#1)` then `B$=INPUT$(6,#1)` print
`<Hello>` then `< from >` — the two reads in a row proving the cursor advances byte-
exactly — **identical to the real National CF-3300**. Crunch suite, 16 unit-test
files, and every file probe still pass.

**Divergences (own design):** the descriptor is clamped to `STRMAX` (=32) — a larger
n is still fully consumed (so the cursor stays correct) but only the first 32 bytes
are stored; reading past EOF stops at EOF (partial result) rather than raising the
reference's "Input past end of file"; the keyboard form is deferred to Phase 3.

## MKI$ / CVI — integer ↔ 2-byte-string conversion (basic/strvar.asm, basic/expr.asm)

The random-access conversion pair: `MKI$(n)` packs a 16-bit integer into a 2-byte
little-endian string; `CVI(s$)` is the inverse (the integer from s$'s first 2 bytes).
These are the integer members of the `MK*$`/`CV*` family; the float siblings
(`MKS$`/`MKD$`/`CVS`/`CVD`) need the Phase-3 float pack and are deferred. They fit
zerobas's integer + minimal-string model exactly and form the first piece of the
random-access sub-phase (2c).

**Tokens (oracle-locked, VG-8020).** `$FF`-prefixed function tokens: `MKI$ = $FF $AE`
(a STRING result — note the `'$'` is PART of the keyword, unlike `INPUT$` where INPUT
is its own token), `CVI = $FF $A8` (a NUMERIC result). `basic_probe_crunch.py` carries
`a$=mki$(258)` (→ `… FF AE 28 1C 02 01 29`) and `a=cvi(b$)` (→ `… FF A8 28 42 24 29`),
both byte-identical on the VG-8020 and zerobas. Added to the kwtable like EOF/LOF.

**Where they live.** `MKI$` returns a string, so it is evaluated in the HL-based
string evaluator (`str_eval`, basic/strvar.asm) — a `$FF`+`$AE` branch that parses
`( n )` (the numeric arg via `eval`) and writes the 2-byte `[2][lo][hi]` STRSCR
descriptor (binary-safe: len-prefixed, so a `$00` byte is fine). `CVI` returns a
number but takes a STRING argument, so it cannot use the numeric arg-parser
`ev_ff_arg`; `ev_ff_cvi` (basic/expr.asm) bridges the IX token cursor to `str_eval`
and back (IX is reloaded from str_eval's advanced HL, so an inner `eval` clobbering
IX is harmless), then reads 2 little-endian bytes from the descriptor. `CVI(MKI$(n))`
in one expression works (str_eval's MKI$ branch handles the nested call). The runtime
HANDLERS being disk-ROM features, the runtime oracle is the CF-3300, not the diskless
VG-8020.

**Register guard.** Same HL-cursor discipline as OPEN/INPUT$: MKI$ writes the STRSCR
descriptor with the eval cursor stacked, then restores it. Several `jr`s to
`str_eval_ok`/`str_eval_no` (strvar.asm) and the `ev_ff_cvi` dispatch (expr.asm) went
out of range as the handlers grew and were widened to `jp`.

**Validation** (`disk_probe_mkicvi.py`, /tmp copy of `test720.dsk`). One REPL line
(the CF-3300 garbles a second typed line) writes BOTH `A$=MKI$(258)` and
`C$=MKI$(CVI(A$))` to M.DAT, pinning the MKI$ byte order AND the CVI round trip on
disk (no fragile screen scrape): M.DAT = `b"\x02\x01\x02\x01\x1a"` (258 = 0x0102 LE,
reproduced by the round trip, + the OUTPUT-close Ctrl-Z) — **byte-identical to the
real National CF-3300**. Crunch suite, 16 unit-test files, strvar/statements probes,
and every file probe still pass.

**Divergences (own design):** integer-only — the float conversions are Phase 3;
`CVI` reads exactly 2 descriptor bytes (a shorter string yields a stale high byte
rather than the reference's "Illegal function call"); MKI$/CVI work in assignments
(`A$=MKI$…`, `A=CVI…`) but not yet directly inside `PRINT`/`PRINT#` (str_eval is not
reached on the PRINT numeric/letter fast-path) — use an intermediate variable.

## MERGE — merge an ASCII program from disk (basic/files.asm)

`MERGE "name"` reads a SAVE",A"-style ASCII (line-numbered text) program file and
stores each line into the CURRENT program (insert-or-replace by line number) — the
existing lines are KEPT, unlike `LOAD`/`RUN` which replace the whole program.

**Token (oracle-locked).** `MERGE = $B6`, a single-byte statement token in the MAIN
ROM table (the diskless VG-8020 tokenises it, like `FILES`); the filename is kept
verbatim ASCII. `basic_probe_crunch.py` carries `merge"prog.bas"` (byte-identical on
the VG-8020 and zerobas).

**Implementation — maximal reuse of the typed-line path.** `ex_merge` parses the
filename (`parse_disk_fcb`), opens the file (`fat_io_open`), and reads the byte
stream (`fat_io_getbyte`) accumulating each line into `LINEBUF` (lines end at CR
`$0D`; LF `$0A` is ignored; a Ctrl-Z `$1A` or EOF ends the file). Each completed line
is handed to **`dispatch_line`** — the exact same tokeniser + `store_line` path a
typed REPL line takes — so a numbered line is inserted/replaced and the existing
program is preserved. A non-blank, non-numbered line is a "Direct statement in file"
error (which also guards against a tokenised file being misread as garbage ASCII).
`dispatch_line`/`store_line` touch `LINEBUF`/`TOKBUF`/`SL_*` + the program text area
but NOT the fat_io read state (`FREAD_*`/`FSECTOR_BUF`), so the file stream survives
across each stored line. The byte stream uses the global fat_io state directly (like
`LOAD`/`BLOAD`), so MERGE while a user file channel is open is undefined.

**Validation** (`disk_probe_merge.py`, /tmp copy of `test720.dsk`). The probe builds
the ASCII merge source with the sequential write path itself — `PRINT#1,"10 a=1"` /
`PRINT#1,"30 a=a*10+3"` — types `20 a=a*10+2` and `40 print"<";a;">"` into the
current program, `MERGE`s the file, and `RUN`s. The merged 10/20/30/40 program
computes `a = ((1*10+2)*10+3) = 123` — a value that only comes out right if BOTH file
lines merged into the correct positions around the typed lines — **identical to the
real National CF-3300**. Crunch suite, 16 unit-test files, the LIST/control-flow
probes, and every file probe still pass.

**Divergences (own design):** ASCII (SAVE",A") source only — there is no tokenised-
MERGE (the reference also errors on a tokenised file; ours errors via the non-
numbered-line guard); the error wording reuses zerobas's `syntax error`/`load error`;
MERGE while a file channel is open is undefined (shares the global read state, like
the other loader verbs). A harness note (not a zerobas property): the real CF-3300
is slow enough after disk I/O that the test types one statement per line with wide
spacing, or it drops the next line's opening characters.

## FIELD / LSET / RSET — random-access record fields, slice 1 (basic/field.asm, basic/files.asm, basic/strvar.asm, basic/vars.asm, basic/interp.asm, basic/sysvars.inc)

**Sub-phase 2c, slice 1 of 2** (slice 2 = GET/PUT disk record I/O). A random-access
file partitions a fixed *record buffer* into named string *fields*; FIELD declares
the partitioning, LSET/RSET store a value into a field (left/right-justified, space-
padded), and reading a fielded variable yields its current slice of the buffer.

**Clean-room sourcing.** Verb *semantics* — FIELD partitions the buffer; LSET left-
justifies + right-pads with spaces, RSET right-justifies + left-pads; a value longer
than the field truncates from the right; a random file opens with `OPEN "name" AS #n`
(no `FOR` clause) — are from the public MSX-BASIC language reference. Token *values* were discovered by the VG-8020 crunch oracle (freeze
at TAPION mid-BLOAD, read KBUF), **not** from any disassembly:
`field#1,2 as a$` → `B1 23 12 2C 13 20 41 53 20 41 24` (FIELD=$B1, "AS" verbatim,
`#1`→`23 12`, the width `2`→`13` single-digit token); `lset a$="x"` → `B8 …`
(LSET=$B8); `rset b$="y"` → `B9 …` (RSET=$B9). All three confirmed byte-identical on
the zerobas side by `basic_probe_crunch.py`. GET=$B2 / PUT=$B3 were captured too but
belong to slice 2.

**Why a side table (own design, forced by zerobas's inline string store).** In MS-
BASIC a string variable holds a 3-byte *descriptor* `[len][ptr]`, and FIELD simply
points that descriptor into the record buffer. zerobas has no such descriptor: string
variables are stored INLINE in STRTAB (`[name0][name1][len][bytes:32]`). So a fielded
variable is recorded in a separate **field table** (`FLD_TAB`, `basic/sysvars.inc`):
each entry is `[chan][key0][key1][offset:2][width]`, mapping a 2-char var key to a
slice of a channel's record buffer. The record buffer is the channel's `FSECTOR_BUF`
(the 512-byte buffer the MAXFILES write-back cache already swaps per channel), so a
field's bytes live in the channel context and travel with it. Two hooks make a fielded
variable behave like one:
- **read** — `str_eval`'s variable path calls `fld_lookup` *before* `str_get_key`. If
  the key is fielded it `fch_select`s the field's channel, copies the slice from
  `FSECTOR_BUF` into `FLD_DESC` as a transient `[len][bytes]` descriptor, points STRPTR
  there, and returns CF set (so PRINT / CVI / comparison see the live bytes). A non-
  fielded key returns CF clear and the original STRTAB path runs unchanged — verified
  no-regression by the INPUT$ and MERGE probes.
- **write** — LSET/RSET (`basic/field.asm`) look the key up in the field table, select
  the channel, space-fill the field, then copy `min(srclen,width)` bytes left- or
  right-aligned.

**Scope / documented divergences.**
- `OPEN "name" AS #n` (RANDOM, mode 4 in FCH_MODES) opens-or-creates the file on disk
  and seeds the channel's record state; the buffer is space-filled. (Slice 1 stubbed
  this as an in-RAM buffer only; slice 2 — §GET/PUT below — made it real.)
- ~~LSET/RSET require a FIELDed target~~ — **closed 2026-08-08 (D-LRVAR,
  docs/spec-basic-lrvar.md).** A non-FIELDed target's CURRENT bytes are overwritten
  IN PLACE: the width is its own current length, that length NEVER changes, the
  value is space-padded and left- (LSET) or right-justified (RSET), a source longer
  than the target keeps its FIRST len(target) bytes **for both verbs**, and a target
  of length 0 — never assigned or assigned `""` — is a **no-op**, not an assignment
  and not an error. All 21 rows measured on the National **CF-3300** first
  (`make lrvar-acceptance`, 21/21); a diskless VG-8020 answers `Syntax error` to
  both words and cannot express the question, so every row rests on ONE reference.
  Array elements included — `LSET A$(2)="HI"` leaves `A$(1)` alone.
- `LSET`/`RSET` on a NUMERIC target is **Type mismatch** (ERR 13), not the ERR 2 it
  used to raise — measured on the CF-3300 (`A=1 : LSET A=2`), D-LRVAR.
- An `ERASE` that compacts the descriptor list **re-keys** the field table rather
  than dropping it: `aeng_erase` (sub/arrays.asm `aer_fldfix`) slides every
  ARYTAB-relative element key above the erased array down by its stride and frees
  any entry inside it, so a field on a surviving array keeps working. Measured: the
  CF-3300 KEEPS the field across `ERASE` of a sibling array (D-LRVAR §5.4 — this
  refuted the "drop every element entry" sweep D-FLDARY had priced for it).
- A fielded READ takes precedence over a plain STRTAB value; assigning a fielded name
  with a plain `LET` does not "disconnect" the field (real MSX-BASIC does).
- Field widths are 1..255; FIELD overflow past the record length is not checked. Up to
  FLD_SLOTS (=16) fields total; extra fields are dropped. The field table is cleared at
  cold start (init_filechan), on NEW/CLEAR/RUN (clear_vars), and when a channel closes
  (fch_do_close_ch), and replaced on re-FIELD of the same channel.

**Oracle.** `probes/disk/disk_probe_field.py`: `OPEN"R.DAT" AS #1 : FIELD #1,5 AS
A$,10 AS B$ : LSET A$="HI" : RSET B$="END" : PRINT"<";A$;"|";B$;">"` prints exactly
`<HI   |       END>` (5-wide left "HI", '|', 10-wide right "END") — the interior
spaces prove the justification + padding. zerobas and the real **National CF-3300**
print the byte-identical line (functional + differential PASS). The fat.asm engine is
untouched; the channel manager is reused unmodified (RANDOM is just a new FCH mode).

## GET / PUT — random-access record I/O, slice 2 (basic/field.asm, basic/files.asm, basic/sysvars.inc)

**Sub-phase 2c, slice 2 of 2** (slice 1 = FIELD/LSET/RSET). `PUT #f,N` writes the
record buffer to record N of the file; `GET #f,N` reads record N back into it. Built
by COMPOSING the fat.asm engine — fat.asm is **not modified**, so its oracle validation
holds.

**Record geometry (oracle-anchored).** The record length is **256 bytes** — confirmed
clean-room, not assumed: a CF-3300 `OPEN..AS #1 : FIELD..: LSET..: PUT #1,1 : CLOSE`
then reopen + `PRINT LOF(1)` prints `256`. Record N (1-based) occupies file bytes
`[(N-1)*256, (N-1)*256+256)`, i.e. file logical sector `(N-1)/2` at within-sector
offset `((N-1)&1)*256` — two records per 512-byte sector. Record numbers are 1..255
(file < 64 KB, the same 16-bit ceiling the loader text path documents).

**Buffer choreography (the load-bearing design point).** The live record stays in
`FSECTOR_BUF` throughout; `FWBUF` is reused *sequentially* for three roles that never
overlap in time: (1) FAT metadata while the cluster chain is walked/extended, (2) the
512-byte data sector for the read-modify-write, (3) the directory-entry stamp. Because
fat.asm's `fat_next_cluster` reads the FAT into `FSECTOR_BUF` (it would destroy the
record), the random walk uses a private `frnd_next` that reads the FAT into `FWBUF`
via the engine's own `fat_read_fat_sector`. Allocation (`fat_alloc_cluster`,
`fat_write_fat_entry`) and the dir stamp (`fat_dir_update`) already use `FWBUF` only.
CALSLT/DSKIO touch only the caller's HL buffer (the cross-component overlap invariant),
so `FSECTOR_BUF` is never clobbered by a disk op aimed at `FWBUF`.

**PUT.** `frnd_calc` splits the record number into file sector + within-offset.
`frnd_locate` walks the chain to that file sector, **extending** it when the record
lies beyond the current end (`fat_alloc_cluster` for a fresh cluster, marked EOC;
`fat_write_fat_entry` to link the previous cluster to it; the first cluster of a
previously-empty file is recorded in `FWR_FIRST`). If the target sector already exists
(`S < ceil(oldsize/512)`) it is read into `FWBUF` first so the *other* record sharing
that sector is preserved; otherwise `FWBUF` is space-filled. The 256-byte record is
overlaid at the within-offset, the sector is written, the file size grows to
`max(old, N*256)`, and `fat_dir_update` stamps the first cluster + size into the
directory entry — so the data survives CLOSE and is found on reopen.

**GET.** `frnd_locate` (read mode, no extend) resolves the physical sector, which is
read into `FWBUF`; the 256-byte record is copied into `FSECTOR_BUF[0..256)`, where the
FIELDed variables read it. A record beyond EOF returns spaces (lenient).

**RANDOM open made real.** `fat_rand_open` (replacing slice 1's in-RAM stub) mounts,
finds-or-creates the file (`fat_dir_create`), and seeds the per-channel state
(`FWR_FIRST` = first cluster, `FWR_BYTES` = current size, `FWR_DIRSEC`/`FWR_DIROFF` =
the directory entry) — all within the MAXFILES write-back-cache span, so they travel
with the channel. GET/PUT never re-mount (that would read the boot sector into
`FSECTOR_BUF`); the geometry from the open's mount persists in the shared `FAT_*` vars.

**Divergences.** Bare `GET`/`PUT` (no record number) default to record 1 — the
auto-incrementing "current record" is not tracked. Sparse/out-of-order PUT leaves
skipped records' bytes undefined; in-order writes are well-defined. `LEN=` (a custom
record length) is not parsed — the length is fixed at 256.

**Oracle.** `probes/disk/disk_probe_getput.py`: write `record 1 = "alpha"+"  bet"`
and `record 2 = "gamma"+"delta"` (records 1 and 2 share one sector, so PUT #1,2 must
read-modify-write to keep record 1), `CLOSE`, **reopen**, re-`FIELD`, and `GET` both
back — yielding `<alpha|  bet>` and `<gamma|delta>`. Reading the right bytes after a
close/reopen exercises chain allocation, the shared-sector read-modify-write, and the
directory stamp at once. zerobas and the real **National CF-3300** produce the byte-
identical pair (functional + differential PASS); `test720.dsk` is never mutated (the
probe runs on a /tmp copy).

## PRINT USING — formatted output (basic/printusing.asm, basic/print.asm, basic/interp.asm, basic/sysvars.inc)

`PRINT USING <format$>; <value>[; <value>]...` formats values through a template.
Reached from `ex_print` when the token after PRINT is USING.

**Clean-room sourcing.** The USING token ($E4) is oracle-locked to the VG-8020 crunch
(`print using"###";5` → `91 20 E4 22 23 23 23 22 3B 16`; `a$=using` → `... EF E4`);
the format string is kept verbatim ASCII inside its quotes. Field *semantics* are from
the public MSX-BASIC language reference. The integer formatter reuses print.asm's
`div10`; the emit path reuses `pchar`. No disassembly.

**Supported fields (the complete set for an integer-only numeric domain).**
- `#...#` — numeric field, width = the count of `#`. The (integer) value is right-
  justified; a negative value's `-` takes a position; a value too wide for the field
  is printed in full preceded by `%` (the MSX overflow marker).
- `\...\` — fixed-width string field, width = 2 + the chars between the backslashes;
  left-justified, space-padded, truncated if longer.
- `!` — the first character of the string value.
- `&` — the whole string value.
- any other character is a literal, emitted as-is.

**Format reuse + termination.** The format is walked once per value (`pu_to_field`
emits the literals before each field). When the format end is reached with values
still pending, it wraps to the start ONCE per call (so `"## "` over `1;2;3` yields
` 1  2  3 ` — each cycle re-emits the trailing/leading literals). When the values run
out, the remaining literals up to the next field are emitted (`pu_emit_tail`) and
output stops. A trailing `;` suppresses the closing newline, like PRINT.

**The load-bearing subtlety: the token cursor.** The format walker and the tail/has-
field scanners all use HL to index `PU_FMT`, but HL is also the live token cursor that
`eval`/`str_eval` consume for the VALUE list. Every call into a PU_FMT-walking helper
(`pu_has_field`, `pu_to_field`, `pu_emit_tail`) is therefore bracketed with
`push hl`/`pop hl` to preserve the cursor (the value formatters `pu_do_number`/
`pu_do_string` advance HL themselves and guard their own internal HL use; `pchar`
preserves all registers). The format string is copied out of the volatile STRSCR into
`PU_FMT` first, because evaluating a string VALUE with `str_eval` reuses STRSCR and
would otherwise clobber a literal format.

**Divergences (documented).** zerobas is integer-only, so the float-only format specs —
the decimal point `.`, exponential `^^^^`, and the `+`/`-`/`,`/`**`/`$$` embellishments
— are deferred to Phase-3 floats (not reachable in the current numeric domain). The
`_` literal-escape and the file form `PRINT# USING` are likewise deferred. The format
string truncates at PU_FMTMAX (32) chars.

**Oracle.** `probes/basic/basic_probe_printusing.py` RUNs a tagged program (zerobas
as a cartridge on a real Philips VG-8020 vs the same machine's built-in MSX-BASIC — a
same-hardware differential) covering all field kinds, sign, overflow, and format reuse:
e.g. `PRINT USING "###";5` → `  5`, `"##";1234` → `%1234`, `"\ \";"cat"` → `cat`,
`"!";"cat"` → `c`, `"## ";1;2;3` → ` 1  2  3 `. All seven cases are byte-identical
between zerobas and the VG-8020 (functional + differential PASS); crunch byte-identical
(basic_probe_crunch.py); the existing PRINT probe is unaffected.

## PRINT# USING — formatted output to a file channel (basic/print.asm)

The file form of PRINT USING. Reached when the token after `PRINT #n[,]` is USING:
`ex_print`'s channel path sets PRDEST=1 (output streams to the channel via `pchar`)
and, before the ordinary item loop, checks for the USING token and jumps into the
same `ex_print_using` formatter. The whole feature is therefore that one check — the
formatter already emits through `pchar`/`print_crlf`, which honour PRDEST, so the
formatted bytes and the line's CR/LF go to the file. PRDEST is reset to screen by
`exec_stmt` at the next statement boundary, as for an ordinary PRINT#. Oracle: the
comma after `#n` is optional (`print#1,using…` → `91 23 12 2C E4 …`; `print#1using…`
→ `91 23 12 E4 …`).

**Regional ROM divergence (an oracle finding, documented).** The two reference ROMs
disagree on PRINT USING *string* fields: the **Philips VG-8020** supports the full set
(`#`, `\..\`, `!`, `&`), but the **National CF-3300** (Japanese ROM) supports only `#`
and `!` — it emits a `\..\` or `&` template literally and then raises "Illegal function
call" (a value with no field). zerobas implements the full VG-8020 set (basic/
printusing.asm), matching the VG-8020 byte-for-byte (basic_probe_printusing.py, a
same-hardware screen differential). This is a genuine difference between real MSX ROMs,
not a zerobas choice.

**Oracle.** `probes/disk/disk_probe_printusing_file.py`: PRINT# USING writes three
formatted lines to U.DAT and CLOSEs; the FAT12 image is read back and must equal
`b"  5\r\n[c]\r\n 1  2  3 \r\n\x1a"` (numeric `#`, first-char `!`, format reuse, then the
Ctrl-Z soft-EOF). Because PRINT# writes to disk and only the CF-3300 is a disk oracle,
the differential uses the `#`/`!` subset both ROMs share; zerobas and the real National
CF-3300 produce the byte-identical file. test720.dsk is never mutated (/tmp copy).

## CALL FORMAT — initialise a blank FAT12 filesystem (basic/format.asm, basic/interp.asm, basic/sysvars.inc)

`CALL FORMAT` (or the `_FORMAT` abbreviation) writes a fresh empty FAT12 filesystem
onto drive A, in either of two geometries: 720 KB (media $F9) or 360 KB (media $FD). A
real MSX CALL FORMAT is interactive (a "Drive name? (A,B)" prompt, then the disk ROM's
CHOICE geometry menu — on the National CF-3300: `1 side` / `2 sides` / `±double track`,
then a confirm keystroke). zerobas keeps the choice that actually matters — the
geometry — and trims the drive prompt (one drive) and the confirm keystroke: it shows a
minimal `1=360k 2=720k?` menu, read via the REPL line editor, then formats. (zerobas-
disk's own CHOICE returns "no choices", so the menu is zerobas-BASIC's own.)
*History: the first cut supported only 720 KB, so there was nothing to choose and it
formatted with no prompt; the 360 KB geometry added the menu.*

**How (BASIC owns the filesystem).** zerobas-BASIC already drives the standard $4010
DSKIO read+write and owns FAT12, so `do_format` lays the structures down itself via
`write_sector` (basic/fat.asm) — no dependence on zerobas-disk's DSKFMT (a stub). It
clears the FAT + root-directory region, stamps each FAT copy's head (`[media][$FF][$FF]`),
and writes the boot sector (BPB) last. This is the Phase-1.5 "BASIC owns the
filesystem" model applied to formatting.

**Geometry is parameterised.** Each geometry is a descriptor (`GEOM_720K`, `GEOM_360K`:
firstFAT, numFATs, secPerFAT, lastSys, media, + a 32-byte boot template); the menu picks
one, stores its base in `FMT_DESC`, and `do_format` reads every field through that
pointer — no hardcoded constants, fully geometry-agnostic. A further geometry is just a
new descriptor + a menu entry. (zerobas already READS any
geometry by parsing the on-disk BPB at mount, so 360 KB disks already load; only
*formatting* one is the deferred part.)

**Tokeniser exception (oracle-driven).** The extended-statement NAME after `CALL`
(or the `_` abbreviation) is kept VERBATIM, not keyword-crunched: the VG-8020 crunches
`call format` to `CA 20 "FORMAT"` and `_format` to `5F "FORMAT"` — NOT `FOR`($82)+`MAT`.
Outside CALL the reference still crunches greedily inside names (`format=5` → `82 "MAT"
="5`, `total=5` → `D9 "TAL"…`), and zerobas matches both: `tokenise` gained a
CALL/`_`-scoped verbatim-name path (the same class of exception as REM/DATA bodies).
All four cases are byte-identical (basic_probe_crunch.py).

**Clean-room sourcing.** CALL token $CA is oracle-locked. Both BPB geometries are the
standard FAT12 layouts (Microsoft FAT spec / MSX2 TH), confirmed field-for-field
against black-box CF-3300 formats: 720 KB = media $F9 / 1440 sectors / 3 sec-per-FAT
("2 sides, double track"); 360 KB = media $FD / 720 sectors / 2 sec-per-FAT ("2 sides").
Both share 512 B/sec, 2 sec/clus, 1 reserved, 2 FATs, 112 root entries. The boot-CODE
region and OEM name ("ZEROBAS") are zerobas' OWN — the one documented divergence from a
byte-identical CF-3300 format (whose boot code is copyrighted ROM content; note the
CF-3300 also writes no $55AA signature). Note the CF-3300's confusing menu numbering:
its "2 - 2 sides" is the 360 KB (media $FD) format and "4 - 2 sides, double track" is
720 KB (media $F9). No disassembly.

**Oracle.** `probes/disk/disk_probe_format.py` formats a junk-filled (`0xE5`) image
in BOTH geometries (menu `2`→720 KB, `1`→360 KB) and checks two things per geometry:
STRUCTURAL — the BPB geometry (offsets 11..27) and FAT head are byte-identical to the
captured CF-3300 format for that geometry; FUNCTIONAL — a file written right after CALL
FORMAT round-trips (`T.DAT` = `hi\r\n\x1a`), proving the BPB, FAT and dir are all valid.
The boot-code/OEM divergence is intentional and not compared. test720.dsk is never
touched (the probe uses a throwaway image).

## Phase 3: string engine — concat (`+`) + LEN/ASC/VAL/CHR$/STR$/LEFT$/RIGHT$/MID$ (basic/str-engine.asm, basic/kwtable.inc, basic/strvar.asm, basic/expr.asm, basic/print.asm, basic/sysvars.inc)

The **first Phase-3 language feature**: the minimal string-VALUE layer (the
`$`-variable that only held a literal for PRINT — see the previous section) grown
into a real **string expression engine** — `+` concatenation and the eight core
string functions LEN / ASC / VAL (string→number) and CHR$ / STR$ / LEFT$ / RIGHT$ /
MID$ (→string). Spec: [`docs/spec-basic-string-engine.md`](../docs/spec-basic-string-engine.md)
(SIGNED OFF). Scope-deferred (documented there, not built): string comparison
(`=`/`<`/`>` on strings), INSTR/HEX$/OCT$/STRING$/SPACE$/INKEY$, the MID$ statement,
and floats in VAL/STR$.

**Repack-only, quarantined by construction.** The whole engine is assembled ONLY in
the repack build (`IF ROM_BASE < $4000`), into the page-0 low region `$2812-$3FFF`
freed by the C-BIOS repack (see the cbios-repack provenance + `docs/cbios-repack-provenance.md`).
The byte-full lean `basic.rom` (default `ROM_BASE=$4000`) is **unchanged** — it keeps
the minimal string-VALUE layer, and every page-1 hook below is a gated near-zero-byte
branch that folds back to the lean `str_eval` path, so the lean image stays
**byte-identical** (the pinned-sha256 regression guard). No new value in this section
touches the lean build.

**Clean-room stance.** Every value the engine emits or decodes is oracle-sourced (the
token bytes) or public-language-reference-sourced (the operator/function *semantics*);
everything structural — the fixed 3-slot temp-result ring, the STRMAX length clamp, the
inline `[len][bytes]` descriptor, the dup-then-slice substring strategy — is zerobas's
**own design**. The reference ROM's string heap + descriptor table + garbage collector
are deliberately **not** reproduced. No disassembly was read.

### Keyword tokens (basic/sysvars.inc, basic/kwtable.inc)

Captured black-box from the Philips VG-8020 crunch by `probes/basic/basic_probe_str_tokens.py`
(reference side only — reusing the crunch-probe harness, no disassembly; the probe
self-asserts) and cross-checked against the contiguous MSX2 TH Table 2.20 function
table. The eight entries were wired into the relocated `kwtable` (S3), so they crunch
**and** LIST-detokenise for free; the whole-corpus + string-keyword crunch is proven
byte-identical to the VG-8020 by `make string-acceptance` (the `basic_probe_crunch.py
--zb-machine` half) on the repack build.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `LEN` function token | `$FF $92` | basic_probe_str_tokens.py (oracle); MSX2 TH Table 2.20 | sourced |
| `LEFT$` function token | `$FF $81` | basic_probe_str_tokens.py (oracle); MSX2 TH Table 2.20 | sourced |
| `RIGHT$` function token | `$FF $82` | basic_probe_str_tokens.py (oracle); MSX2 TH Table 2.20 | sourced |
| `MID$` function token | `$FF $83` | basic_probe_str_tokens.py (oracle); MSX2 TH Table 2.20 | sourced |
| `STR$` function token | `$FF $93` | basic_probe_str_tokens.py (oracle); MSX2 TH Table 2.20 | sourced |
| `VAL` function token | `$FF $94` | basic_probe_str_tokens.py (oracle); MSX2 TH Table 2.20 | sourced |
| `ASC` function token | `$FF $95` | basic_probe_str_tokens.py (oracle); MSX2 TH Table 2.20 | sourced |
| `CHR$` function token | `$FF $96` | basic_probe_str_tokens.py (oracle); MSX2 TH Table 2.20 | sourced |

### `+` concatenation + the temp-result ring (basic/str-engine.asm, basic/strvar.asm)

The concat-aware `str_eval` wrapper (strvar.asm) folds a trailing `+ operand` chain
for every string context at once (LET, PRINT, PRINT#, the file-write path, …) with no
caller edits; `str_concat_tail` (str-engine.asm) copies operand 1 into a ring temp and
appends each further operand. 🔴 **IT USED TO SAY "clamped to STRMAX", AND THAT
WAS THE DIVERGENCE, NOT THE DESIGN** — corrected 2026-08-28 (D-STRLONG,
`docs/spec-basic-strlong.md`): a combined length over STRMAX raises
`String too long` (ERR 15), as both references do.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `+` concatenation semantics: left-to-right, result length = sum of operand lengths | — | public MSX-BASIC language reference | sourced |
| String-result **temp ring**: 3 slots (`STRNTMP=3`), round-robin `[len][bytes]` descriptors | `STRTMP`/`STRTMP_IDX`/`STRSCR` in free page-3 RAM (`$E240–$E55E`, below the `$E560` file/cassette buffers) | **own design** — the reference heap+GC is not reproduced; N=3 covers a binary op's ≤2 live operands + 1 result, a deeper nest reuses the oldest slot (documented depth-truncation) | quarantined |
| ~~**STRMAX** length clamp: strings longer than STRMAX are truncated~~ | ~~`64` (repack) / `32` (lean)~~ | ~~**own design** — the 255-faithful clamp overflows page-3 RAM by ~2 KB (spec §5a), so a smaller cap is chosen; extra bytes are dropped, no error~~ | **RETIRED** |
| **CONCATENATION over STRMAX raises ERR 15 `String too long`** | `STRMAX = 255` | public MSX-BASIC language reference, oracle-locked against BOTH references (`scratchpad/strlong_probe.py`) | **sourced** |

⚠️ **THE ROW ABOVE IS STRUCK, NOT DELETED, BECAUSE ITS REASONING WAS SOUND AND
ITS PREMISE EXPIRED.** The clamp was chosen when STRMAX was 64/32 and the
3-slot ring lived in page-3 RAM, where a 255-faithful cap really did overflow by
~2 KB. Arrays slice-4a retired that ring for the compacting heap and widened
STRMAX to 255 — at which point the clamp was no longer a RAM-budget concession
but a plain divergence, and it survived unexamined until 2026-08-28 because no
gate reads prose and the ONE unit-test case that touched it
(`tests/test_str_engine.py`) asserted the clamp. See `docs/spec-basic-strlong.md`.
| `str_alloc_temp` / `str_copy_desc` / `str_append_desc` / `str_concat_tail` ring allocator + append algorithm | — | **own code**; not derived from any disassembly | sourced |

### The eight verb handlers (basic/str-engine.asm, reached via gated hooks in basic/expr.asm, basic/strvar.asm, basic/print.asm)

Three near-zero-byte gated page-1 hooks route into the low-region handlers: `ev_f_ff`
(expr.asm) → `ev_ff_strnum` for LEN/ASC/VAL; `str_eval_maybe_mki` (strvar.asm) →
`str_func_ff` for CHR$/STR$/LEFT$/RIGHT$/MID$; PRINT's item loop (print.asm) tries
`str_eval` on a leading `$FF` token (so `PRINT CHR$(…)` prints, PEEK/… fall back to
numeric with HL restored). The substring verbs **dup the source into a fresh ring temp,
then slice in place** (LEFT$ = truncate; RIGHT$/MID$ = `LDIR` the slice to the front) so
only ONE temp address must survive the numeric-argument eval.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `LEN`/`ASC` semantics (byte length; ASCII code of char 1, `ASC("")` = error) | — | public MSX-BASIC language reference | sourced |
| `LEFT$`/`RIGHT$`/`MID$` semantics (1-based MID$ position, head/tail count clamped to available bytes, MID$ optional length → to end) | — | public MSX-BASIC language reference | sourced |
| `STR$(n)` decimal render, leading blank for `n ≥ 0` | — | public MSX-BASIC language reference; reuses `pu_fmt_int`/`div10` (basic/print.asm, already sourced) | sourced |
| `VAL(a$)` **integer-only** leading-number parse (spec D-E) | — | **own design** — MSX VAL parses floats; the leading-parse of an integer prefix is the loader-stub subset, floats deferred | quarantined |
| `CHR$(n)` = a 1-byte string of the **low 8 bits** of n (no range error on `n > 255`) | — | **own design** leniency — MSX errors on out-of-range; documented in-file | quarantined |
| `ev_ff_strnum`/`str_val_parse`/`str_func_ff` + the CHR$/STR$/LEFT$/RIGHT$/MID$ slice code; the `ev_str_arg` IX↔HL bridge and the three gated hooks | — | **own code** (mirrors the existing `ev_f_ff` / `str_eval` dispatch); not derived from any disassembly | sourced |

### PRINT leading-literal concat reroute (basic/print.asm)

A PRINT item *leading with a string literal* followed by `+` (`PRINT "a"+"b"`,
`PRINT "n="+STR$(x)`) is a string concatenation, but the fast char-by-char literal path
skipped the `+`-folding `str_eval`. `str_lit_concat_q` (repack-gated) look-aheads past
the literal — skipping the same intervening spaces `str_concat_tail` does — for a
trailing `PLUS_TOKEN`, and reroutes to `str_eval` when found; a plain literal keeps the
fast path (so a literal longer than STRMAX still prints in FULL, un-clamped). This was
**found by the `string-acceptance` gate**: without it `PRINT "a"+"b"` mis-parsed the
`+` as numeric and printed `AB 0 CD`.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| A string literal followed by `+` is a string concatenation (route to `str_eval`) | — | public MSX-BASIC language reference (string `+`) | sourced |
| `str_lit_concat_q` look-ahead + reroute; plain-literal fast path preserved | — | **own code**; not derived from any disassembly | sourced |

**Quarantined items (this section):** the fixed 3-slot temp ring (no heap/GC), the
STRMAX length clamp, integer-only VAL, and CHR$'s low-byte leniency — all deliberate
own-design simplifications of MSX-BASIC's heap-backed float-capable string model,
chosen to fit the repack window's RAM budget and the loader-first scope. None is a
value lifted from any reference ROM or disassembly; each is documented in
`basic/str-engine.asm` and the spec. A future RAM re-architecture could lift STRMAX
toward the MSX-faithful 255 (spec §5a) and a float pass could complete VAL/STR$.

**Gates.** `make string-acceptance` PASS (8 keywords crunch byte-identical to the
VG-8020 + carry the captured `$FF`-suffix; 14 execute cases print the right screen
output on the repack machine); lean `basic.rom` byte-identical; unit-test 40/40 (new
`tests/test_str_engine.py` + `tests/test_str_verbs.py`); `diskbasic-acceptance-repack`
34/34 (shared PRINT parse unregressed); `repack-boot` PASS; audit-citations clean.

## Phase 3: string comparison — relational operators on strings (basic/str-engine.asm, basic/expr.asm, basic/interp.asm, basic/print.asm, basic/sysvars.inc)

The follow-on to the string engine (the D-F item it deferred): the six relational
operators — `=` `<>` `<` `>` `<=` `>=` — on two string operands, so `IF A$="YES"` and
`IF LEFT$(N$,1)<"M"` work. Spec:
[`docs/spec-basic-string-compare.md`](../docs/spec-basic-string-compare.md) (SIGNED OFF).
**Repack-only**, like the whole string engine: the entire feature is assembled `IF
ROM_BASE < $4000`, and the byte-full lean `basic.rom` (default `ROM_BASE=$4000`) is
**unchanged** — every page-1 hook is a gated near-zero-byte branch, so the lean image
stays byte-identical (pinned-sha256 regression guard).

**Reuses the numeric relational spine — no new token.** `ev_rel` (basic/expr.asm)
already factors a comparison into a *requested-relation bit* (`relop_bit`: `<`→1, `=`→2,
`>`→4; the compound forms `<=`/`>=`/`<>` arrive as two relop tokens and merge to the OR),
AND'd against an *actual-relation bit* (1/2/4) from the operands, → non-zero ⇒ **-1** /
zero ⇒ **0**. String comparison substitutes exactly **one** thing: an unsigned-byte
comparator (`str_cmp_bits`) producing that same 1/2/4 encoding in place of the signed
`cmp16_bits`. So the six operators, the compound-form merge, the -1/0 convention, and the
boolean composition above `ev_rel` (`IF A$="Y" AND B=1`) are all inherited. The relop
tokens (`=`→`$EF`, `<`→`$F0`, `>`→`$EE`, already sourced from MSX2 TH Table 2.20 and
crunch byte-identical) are **unchanged** — `A$="YES"` already crunched correctly; only its
*evaluation* is added. No tokeniser / `kwtable` change.

### Comparison semantics + the hook (basic/str-engine.asm, basic/expr.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| String comparison: **unsigned** byte-by-byte, first differing byte's string is less; if one is a prefix of the other the SHORTER is less; equal iff same length + all bytes equal; case-sensitive; result -1/0 | — | standard MSX-BASIC string-ordering contract (public language reference), **oracle-locked black-box** on the Philips VG-8020 (`probes/basic/basic_probe_str_cmp.py`: reference-lock 6/6 for equal / prefix-shorter / case / first-diff-byte / empty × all six operators, then zerobas==reference 6/6) — measured, not assumed | sourced |
| `str_cmp_bits` unsigned-byte comparator → 1/2/4 (the same encoding `cmp16_bits` produces, so the caller's `and c` is unchanged) | — | **own code**; the relation-bit encoding is zerobas's own (matches expr.asm); not derived from any disassembly | sourced |
| `ev_rel` hook: probe the LHS (repack-gated) via the IX↔HL bridge + `str_eval`; a string LHS routes to `ev_rel_str` (snapshot LHS into a ring temp, read the relop(s), `str_eval` the RHS, compare), a non-string LHS leaves IX untouched and the unchanged numeric body runs | — | **own code** (mirrors the existing `ev_ff_cvi` IX↔HL bridge + the dup-then-operate discipline); not derived from any disassembly | sourced |

### Type mismatch — D-2, statement-level abort (basic/interp.asm, basic/print.asm, basic/sysvars.inc)

Comparing a string to a non-string (`A$ < 5`, `5 < A$`) is a real error that **aborts the
line**. zerobas has no mid-expression unwind (every evaluator error sets `ERRMARK` and
yields 0, continuing), and adding a saved-SP longjmp would touch the **shared lean run
driver** and threaten the byte-identical invariant — so the abort is raised at the
**statement boundary** (spec §3c): the comparator sets `ERRMARK` + a distinct `TMISMATCH`
marker and yields 0; the repack-gated condition-owning statement drivers (`ex_if`, the
numeric-assignment path, the PRINT-item path) check `TMISMATCH` right after their `eval`
and `jp` to `type_mismatch_error`. For `IF A$<5 THEN…` / `R=(A$<5)` the comparison is the
first thing evaluated, so the line aborts with the message before any clause runs —
observably identical to MSX.

⚠️ **THE PARAGRAPH ABOVE IS HISTORY AS OF D-PENDERR (2026-08-09, `34a6efe`,
[`docs/spec-basic-penderr.md`](../docs/spec-basic-penderr.md)).** The mechanism is
unchanged — deferred marker, statement-boundary abort, same message — but there is no
longer a *distinct* `TMISMATCH` marker. It was only ever a boolean shorthand for one
value of the pending-error **code** cell `FPERR` (`sfr_argok` already promoted it by hand,
and `fperr_to_err` entry 10 is the same ERR 13 `type_mismatch_error` raises), so the two
cells were merged into one, written **set-if-empty** so first-error-wins is a property of
the write. The comparator now records `FPERR := FPERR_TYPEMM (10)`; every former reader
of `TMISMATCH` reads the one cell. **No behaviour in this section changed**, which
`make tmfp-acceptance` (50/50) and `tests/test_str_compare.py` — now asserting
`FPERR == 10` where it asserted `TMISMATCH == 1` — are the standing evidence for.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| D-2 marker: the deferred type-mismatch **code** `FPERR_TYPEMM` = 10 in the pending-error cell `FPERR` (`$F069`), mapped to ERR 13 by `fperr_to_err`. ⚠️ **Was a dedicated 1-byte `TMISMATCH` cell until D-PENDERR (2026-08-09).** 🔴 **AND THIS ROW'S ADDRESS WAS ALREADY STALE BEFORE THAT**: it read `$E55F`, which arrays slice-4a had re-homed to `$E3E5` (`basic/sysvars.inc` says so in as many words — "unchanged in role from pre-4a, just re-homed after the heap layout above"). Recorded rather than silently corrected: a provenance row naming a *retired* cell is visible, one naming a *moved* one is not | `FPERR` `$F069`, code 10 | own choice (the code cell and its `fperr_to_err` entry both predate this; the merge adds no new RAM and frees a byte, `STRENG_SPARE $E3E5`, deliberately left unclaimed so `MIDS_DEST` does not move) | sourced |
| `type_mismatch_error` reports the reference-verbatim `"Type mismatch"` + aborts the line (mirrors `stmt_error`). ⚠️ **Was zerobas's own lowercase wording until D-MSGEXACT (2026-08-02)**; the statement-level abort remains own design | — | **black-box oracle measurement** on Philips_VG_8020 + National_CF-3300 (`probes/basic/basic_probe_msgexact.py`, `docs/msgexact-msx1-characterization.md`), corroborated by the published MSX-BASIC reference (allowed-sources, grade B, "the user-visible language contract ... errors"). NOT from any disassembly; statement-level abort is **own design** (§3c) | sourced |

### Documented divergences (own design)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| A bare string on a numeric RHS with no relop (`R=A$`) now raises `type mismatch` | — | **own design** — the unconditional LHS probe (spec §3a) makes this a natural consequence; MSX also errors here. Supersedes a pre-existing accidental gap where a `$`-var name-keyed *numeric shadow* cell was silently read (never a documented feature) | quarantined |
| ~~`PRINT A$<5` **unparenthesized** mis-routes~~ — **RESOLVED** by the PRINT-lead dispatch follow-on (below); the bare form now works and `PRINT A$<5` aborts with `type mismatch`, printing nothing | — | own code (the resolving reroute is own design; see the following subsection) | sourced |

The remaining **quarantined** item (bare string on a numeric RHS) is a deliberate
own-design outcome, not a value lifted from any reference ROM or disassembly; it is
documented in `basic/str-engine.asm` and the spec.

### Unparenthesized PRINT comparison — the PRINT-lead dispatch reroute (S2 follow-on, basic/print.asm, basic/str-engine.asm)

The one remaining surface gap the compare slice quarantined: a *bare* comparison as a
top-level `PRINT` item (`PRINT A$="YES"`, `PRINT A$<5`). The comparison engine already
produced the right value wherever a *numeric* expression ran — including the
**parenthesized** `PRINT (A$="YES")` — but `exp_loop` (PRINT's item loop) classified a
string-leading item as "a string to print" and emitted it *before* the relop was seen.
Spec: [`docs/spec-basic-print-unparen-compare.md`](../docs/spec-basic-print-unparen-compare.md)
(SIGNED OFF → SHIPPED). **Repack-only**; lean `basic.rom` byte-identical (the lean
`exp_strvar` body is preserved verbatim in the gated `ELSE` branch).

The fix is *only* in PRINT's dispatch — the comparison engine is untouched. It reuses
`str_eval` as the one string-subexpression parser (it already advances past the whole
operand + any `+`-concat chain) and then **peeks** the next token: a relop ⇒ the item is
the LHS of a comparison ⇒ restore the cursor to the operand start and re-drive via
`eval`→`ev_rel` (which yields -1/0, or records the deferred type-mismatch code so
`exp_num`'s existing check aborts `PRINT A$<5` with nothing printed — a distinct
`TMISMATCH` cell until D-PENDERR, the `FPERR_TYPEMM` code in the shared pending-error
cell since); no relop ⇒ print the descriptor `str_eval`
already produced, exactly as before (so plain `PRINT A$` pays no re-parse).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `relop_peek` — non-consuming test, ZF=1 iff the peeked token ∈ {`GT_TOKEN $EE`, `EQ_TOKEN $EF`, `LT_TOKEN $F0`}; a straight `sub GT_TOKEN` / `cp 3` range test over the established relop equates (testing the FIRST of a compound `<=`/`>=`/`<>` pair suffices — `ev_rel`'s own merge handles the second) | — | **own code**; no disassembly | sourced |
| `exp_strvar` / `exp_maybe_strfn` relop gate: `push` operand-start before `str_eval`, `relop_peek` after; on a relop `pop`+`jp exp_num` (re-parse via `eval`), else print as before. Stack balanced on all three branches (reparse / print / str_eval-fallback) | — | **own code** (reuses the existing `str_eval`→`print_strval` idiom); the `eval`→`ev_rel` path it re-drives is the same one `PRINT (…)` already used | sourced |
| `str_lit_concat_q` generalized from "does `+` follow this literal?" to "`+` **or** a relop follows" so a literal LHS (`PRINT "YES"=A$`) routes to the `str_eval` path; a plain literal keeps the fast un-clamped char path (the S5 STRMAX property is preserved) | — | **own code**; not derived from any disassembly | sourced |
| All three string leads covered: `$`-var, string literal, and the string-valued `$FF`/`INKEY$`/`STRING$` functions, plus `+`-concat chains (`PRINT A$+B$="HELLO"`) | — | own design (one shared `relop_peek` choke point) | sourced |

Oracle-locked black-box on the Philips VG-8020 (`probes/basic/basic_probe_str_cmp.py`
gained var/literal/function/concat PRINT-lead cases + the `A$<5` abort — reference-lock
then zerobas==reference), folded into `string-acceptance`'s **compare** half (no new
half). Host regression cover in `tests/test_str_compare.py` (all leads, the D-2 abort,
plain-print unchanged, and multi-item stack-balance `PRINT A$;B$<C$`).

**Gates.** `make string-acceptance` PASS (now three halves: crunch + execute + the new
**compare** — six relational operators, reference-lock + zerobas==reference on the repack
machine); lean `basic.rom` byte-identical (pinned sha256 unchanged); unit-test 41/41 (new
`tests/test_str_compare.py`); `diskbasic-acceptance-repack` 34/34 (shared `ev_rel`/`eval`
path unregressed); `repack-boot` PASS; audit-citations clean.

## Phase 3: string functions — INSTR / HEX$ / OCT$ / STRING$ / SPACE$ (basic/str-engine.asm, basic/kwtable.inc, basic/strvar.asm, basic/expr.asm, basic/print.asm, basic/sysvars.inc)

The next batch of deferred string-library verbs after the engine + comparison. Spec:
[`docs/spec-basic-string-functions.md`](../docs/spec-basic-string-functions.md) (SIGNED OFF).
**Repack-only**, like the whole string engine: assembled `IF ROM_BASE < $4000`; the
byte-full lean `basic.rom` is **unchanged** (every page-1 hook is a gated near-zero-byte
branch; pinned-sha256 regression guard). Reuses the S4 machinery (the temp-string ring,
the descriptor, the IX↔HL bridge) — no new RAM, no floats, no heap.

**Three integration shapes, dictated by the tokens (§4).** The reference token map is
**not** uniform, so the dispatch hook for each verb follows its captured width:

| Verb | Token | Width | Hook |
|------|-------|-------|------|
| `SPACE$` | `$FF $99` | 2-byte `$FF`-prefixed function | `str_func_ff` (Group A) |
| `OCT$` | `$FF $9A` | 2-byte `$FF`-prefixed function | `str_func_ff` (Group A) |
| `HEX$` | `$FF $9B` | 2-byte `$FF`-prefixed function | `str_func_ff` (Group A) |
| `STRING$` | `$E3` | 1-byte reserved word | a `str_eval` branch (Group B) |
| `INSTR` | `$E5` | 1-byte reserved word | an `ev_f` branch beside USR/VARPTR/BASE (Group C) |

### Tokens (basic/kwtable.inc, basic/sysvars.inc)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `SPACED_TOKEN` / `OCTD_TOKEN` / `HEXD_TOKEN` (`$FF`-suffixes) | `$99` / `$9A` / `$9B` | MSX2 TH Table 2.20 (the same contiguous function table as LEN/STR$/VAL) **AND black-box-captured** from the VG-8020 crunch 2026-07-10; the `$` is part of the keyword (like MKI$) | sourced |
| `STRING_TOKEN` / `INSTR_TOKEN` (bare single-byte reserved words) | `$E3` / `$E5` | MSX2 TH Table 2.20 **AND black-box-captured** from the VG-8020 crunch (`a$=string$(3,65)`→`…E3…`, `a=instr("ab","b")`→`…E5…`); collision-free vs existing token equates | sourced |
| Both directions (crunch + LIST detok) are data-driven off `kwtable`; adding the five entries wires each | — | own code (the table is scanned by `match_kw` / `detok_kw2`) | sourced |

Never a reference-ROM disassembly ([[no-reference-rom-disasm]]); the token bytes are the
sourced Table 2.20 values *confirmed by observation* (`probes/basic/basic_probe_str_fn.py`
+ the `basic_probe_crunch.py --zb-machine` corpus: `$FF`-suffix list + a `STR_KEYWORDS_1B`
bare-token list).

### Semantics + handlers (basic/str-engine.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `HEX$(n)` / `OCT$(n)`: text of `n` as an **unsigned 16-bit** value, uppercase, no leading zeros, ≥1 digit (`HEX$(-1)="FFFF"`, `OCT$(-1)="177777"`) | — | public MSX-BASIC ref, **oracle-locked black-box** (`basic_probe_str_fn.py` reference-lock then zerobas==reference); the digit loop **reimplements** `detok_hex16`/`detok_oct16` (list.asm) into a ring temp reusing only the leaf `hex_digit`/`oct_digit` — `list.asm` stays byte-identical (lean unaffected) | sourced |
| `SPACE$(n)`: `n` spaces | — | public MSX-BASIC ref, oracle-locked | sourced |
| `STRING$(n,c)` / `STRING$(n,x$)`: `n` copies of a numeric char code, or of `x$`'s first byte (empty `x$` = error) — 2nd-arg type resolved by probing for a string operand first (D-4) | — | public MSX-BASIC ref, oracle-locked; probe-based type detection is **own code** (reuses the `str_eval`-CF pattern) | sourced |
| `INSTR([p,]a$,b$)`: 1-based position of `b$` in `a$` from `p` (default 1), 0 if not found; empty `b$` → `p` clamped; optional leading `p` resolved by probing the first arg's type (D-5) | — | public MSX-BASIC ref, oracle-locked; both operands snapshotted into their own ring temp (the dup-then-operate discipline), `instr_search` is **own code** | sourced |

### Documented divergences (own design)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `HEX$`/`OCT$` view `n` as **unsigned 16-bit** (integer-only engine; no float rendering) | — | own design (D-2), consistent with the integer-only core; also the reference behaviour for the integer domain | quarantined |
| `SPACE$`/`STRING$` length clamps to **`STRMAX`=64** (reference ceiling is 255); a **negative** count is a function error | — | own design (D-3) — ⚠️ this cell used to read "identical to the concat/substring STRMAX-clamp philosophy", and the CONCAT half of that comparison no longer exists (D-STRLONG, 2026-08-28: concat RAISES). Whether `SPACE$`/`STRING$` should raise too is UNMEASURED and filed separately | quarantined |
| `INSTR` uses the **N=3 ring** for its two live snapshots (a deep `INSTR(a$+b$,c$+d$)` reuses the oldest slot) | — | own design (spec §3a ring bound) | quarantined |

### Two integration bugs the acceptance gate caught (both fixed before ship)

The S2 host unit tests call `str_eval` directly and read only descriptor-length bytes, so
they passed while two real defects survived; the S3 **execute + oracle** gate
(`basic_probe_str_fn.py`, live on the merged repack build) surfaced both:

1. **`PRINT STRING$(…)` raised a spurious `type mismatch`.** PRINT's item loop (`exp_loop`,
   basic/print.asm) special-cased `"`-literals, `$FF` functions, and `$`-vars but had **no
   `STRING_TOKEN` ($E3) case**, so a bare `STRING$` item fell through to `exp_num`→`ev_rel`,
   whose LHS string probe found a string with no relop → the D-2 bare-string abort. Fix: a
   repack-gated `cp STRING_TOKEN / jp z,exp_maybe_strfn` beside the `$FF` case (same class of
   fix as the S5 leading-literal-concat PRINT reroute).
2. **`SPACE$(n)` overran its ring slot.** The fill loop did `ld b,0 : djnz`, writing **256**
   bytes regardless of `count` — invisible to the descriptor-length assertions but it smeared
   `STRTMP_IDX`/`STRCAT_R`/`TMISMATCH` (`$E55C`–`$E55F`) and the file buffers, corrupting the
   `TMISMATCH` byte so a later statement spuriously aborted. Fix: loop on the count (`ld b,a`).
   A host regression (`tests/test_str_fn.py`, sentinel-past-fill) now guards it.

### Harness note

Adding a legitimate keyword cost one extra `match_kw` scan per tokenised word, which tipped
the disk acceptance suite's REPL driver — it typed lines via openMSX's timing-fragile `type`
(keyboard matrix) — into doubling a leading keystroke (a **false** `OPEN LEN=` failure, not a
ROM bug: the merged-ROM diff is all valid relocation). `probes/disk/disk_probe_getput.py` now
injects each line straight into the BIOS type-ahead buffer (KEYBUF `$FBF0` / GETPNT `$F3FA` /
PUTPNT `$F3F8`, published MSX2 TH contract — C-BIOS honours it, verified black-box; no
disassembly) so CHGET reads the bytes with no matrix scan.

**Gates.** `make string-acceptance` PASS (four halves: crunch + execute + compare +
**functions** — HEX$/OCT$/SPACE$/STRING$/INSTR reference-lock + zerobas==reference on the
repack machine); lean `basic.rom` byte-identical (pinned sha256 unchanged); unit-test 42/42
(new `tests/test_str_fn.py`, incl. the SPACE$ overrun regression); `diskbasic-acceptance-repack`
34/34; `repack-boot` PASS; audit-citations clean.

## Phase 3: INKEY$ — non-blocking keyboard read (basic/str-engine.asm, basic/kwtable.inc, basic/strvar.asm, basic/print.asm, basic/sysvars.inc)

The first **keyboard-reading** string verb, from the standing string deferral list. Spec:
[`docs/spec-basic-inkey.md`](../docs/spec-basic-inkey.md) (SIGNED OFF). **Repack-only**:
assembled `IF ROM_BASE < $4000`; the byte-full lean `basic.rom` is **unchanged** (pinned
sha256 `e21f61fe…4228005`). Tiny in code (no args, ≤1-byte result) but it crosses one new
seam the earlier string slices never touched — the BIOS **console input** path.

### Token (basic/kwtable.inc, basic/sysvars.inc)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `INKEY_TOKEN` (bare single-byte reserved word) | `$EC` | MSX2 TH Table 2.20 **AND black-box-captured** from the VG-8020 crunch (`a$=inkey$`→`41 24 EF EC`, `print inkey$`→`91 20 EC`) — the trailing `$24` is absent, so the `$` is **part of the keyword**; collision-free vs existing token equates | sourced |
| Crunch + LIST detok are data-driven off `kwtable`; the one entry wires both (`match_kw`/`detok_kw2`); no prefix shadow vs `INPUT`/`INSTR` (diverge at char 3) | — | own code | sourced |

### BIOS contract + handler (basic/str-engine.asm `str_fn_inkey`)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `CHSNS` = `$009C` (test keyboard buffer → Z=empty / NZ=key), `CHGET` = `$009F` (fetch a key) | — | published MSX BIOS console entries (MSX Assembly Page / MSX2 TH jump table — the same source the REPL's `CHGET`/`CHPUT` cite); never a reference-ROM disassembly ([[no-reference-rom-disasm]]) | sourced |
| `INKEY$` samples the keyboard **once, non-blocking**: empty string if no key, a 1-char string (the key) if one waits; the key is **consumed** | — | public MSX-BASIC ref, **oracle-locked black-box** (`basic_probe_inkey.py` reference-lock then zerobas==reference: empty `PRINT INKEY$`→`[]`, poll loop + injected key→the key) | sourced |
| Result is a 0-/1-byte temp-ring descriptor via `str_alloc_temp` (the same ring SPACE$/STRING$ use); dispatched from `str_eval_one` beside `STRING$` and from `exp_loop` via `exp_maybe_strfn` | — | own code (the established ring + dispatch pattern) | sourced |

### Documented divergence (own design)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Control keys pass through as their raw code (no special-casing, e.g. Ctrl-STOP → `$03` when untrapped) | — | own design (D-5), matching the reference "raw code" behaviour; no observed VG-8020 divergence on the tested keys | quarantined |

### Integration bug the live gate caught (fixed before ship)

The S2 host path (assignment `A$=INKEY$`) worked immediately, but the first live run found
`PRINT "[";INKEY$;"]"` raising a spurious **`type mismatch`** — the **same class** the
string-functions slice hit with `PRINT STRING$`: PRINT's `exp_loop` (basic/print.asm) had no
`INKEY_TOKEN` ($EC) case, so a bare `INKEY$` item fell through to `exp_num`→`ev_rel` (a
string with no relop → the D-2 abort). Fix: a repack-gated `cp INKEY_TOKEN / jp z,exp_maybe_strfn`
beside the `STRING$` case. The `INKEY$` acceptance half keeps a literal `PRINT INKEY$` test so
the gate keeps guarding that hook.

### Harness note

`INKEY$` is the first verb whose acceptance **drives the keyboard**: `basic_probe_inkey.py`
injects a keystroke (openMSX `type`) into a bounded poll loop (`10 A$=INKEY$:IF A$=""THEN10`),
which blocks until a key lands, so the injection instant need not be synchronised between the
two machines — the differential stays deterministic despite the real-time keyboard. The
real-speed reference needs ~3 s between a typed line and its Enter (a tighter gap fires Enter
mid-type and garbles the line).

**Gates.** `make string-acceptance` PASS (five halves: crunch + execute + compare + functions
+ **inkey** — empty-path + injected-key reference-lock + zerobas==reference on the repack
machine); lean `basic.rom` byte-identical (pinned sha256 unchanged); unit-test 42/42;
`diskbasic-acceptance-repack` 34/34.

## Phase 3: MID$ statement — in-place substring overwrite (basic/str-engine.asm, basic/interp.asm, basic/sysvars.inc)

The `MID$` **assignment statement** `MID$(A$,n[,m])=B$` — overwrite a substring of A$ in
place (the `MID$` **function** shipped with the string engine). Spec:
[`docs/spec-basic-mid-statement.md`](../docs/spec-basic-mid-statement.md) (SIGNED OFF).
**Repack-only**: assembled `IF ROM_BASE < $4000`; the byte-full lean `basic.rom` is
**unchanged** (pinned sha256 `e21f61fe…4228005`). Two firsts for zerobas: the first
**lvalue path into the string store**, and the first `$FF`-prefixed token to start a
**statement**.

### Token + dispatch (basic/interp.asm, basic/sysvars.inc)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| The `MID$` statement crunches with a leading **`$FF $83`** (`MIDD_TOKEN`), the SAME token as the `MID$` function | `$FF $83` | MSX2 TH Table 2.20 **AND black-box-captured** from the VG-8020 crunch (`bload"cas:",r:mid$(a$,1,2)="xy"` freeze → `FF 83 28 41 24 2C 12 2C 13 29 EF …`); the `=` is `EQ_TOKEN $EF` | sourced |
| `exec_stmt` (interp.asm) dispatches a leading `$FF` at statement start to `ex_mid_stmt`; only `$FF $83` is valid there (other `$FF` → `stmt_error`) | — | own code (a gated `cp PEEK_PREFIX` before the `is_letter` fallback) | sourced |

### Semantics + handler (basic/str-engine.asm `ex_mid_stmt`)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| In-place overwrite, **`LEN(A$)` invariant**; replaced count `k = min(m\|Lb, Lb, La-n+1)`; bytes outside `[n, n+k)` untouched; empty B$ / m=0 = no-op | — | public MSX-BASIC ref, **oracle-locked black-box** (`basic_probe_mid_stmt.py` reference-lock then zerobas==reference: `HELLO`→`HXYZO`/`HELWX`/`ABLLO`, truncate-to-fit) | sourced |
| Reuses `var_str_type`/`var_name_key` (LHS `$`-var), `str_get_key` (in-place STRTAB descriptor), `eval` (n/m), `str_eval` (RHS); the dest addr is stashed in `MIDS_DEST` (aliases NUMBUF, dead here) so the token cursor stays in HL through the arg parse | — | own code (established idioms) | sourced |

### Documented divergences (own design)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Range/type errors (`n<1`, `n>La`, `m<0`, non-string LHS/RHS) report via `syntax error` (`stmt_error`), **not** MSX's *Illegal function call* — zerobas has no such error | — | own design (D-3), the same own-wording convention as the string-compare `type mismatch`; the differential asserts both machines abort the line + leave A$ unchanged, only the wording differs | quarantined |
| Target = a plain `$`-suffixed string variable; `FIELD`ed / array lvalues deferred | — | own design (D-1); string arrays don't exist yet | quarantined |
| No `STRMAX` interaction — the statement never grows A$ (length invariant), unlike SPACE$/STRING$ | — | falls out of the in-place contract | — |

### Harness note

The overwrite math (compute `k`, copy) is BIOS-independent, so it carries an emulator-free
host unit-test (`tests/test_mid_stmt.py`, 9 cases): tokenise a full `MID$(…)="…"`, seed A$ in
STRTAB, call `ex_mid_stmt`, read A$ back — the success path ends in `jp exec_stmt` → `ret` at
end-of-line with no BIOS output. The error path (through `stmt_error`→`print_string`→CHPUT) is
covered by the live gate, not the unit test. The differential probe types the setup/op/print as
**three short direct-mode lines** (A$ persists across them): a single long line lets openMSX's
`type` Enter land mid-typing and silently drop the line (a real-speed keyboard-scan limit —
observed as a deterministic capture miss on one 44-char case; short lines fix it).

**Gates.** `make string-acceptance` PASS (six halves: crunch + execute + compare + functions +
inkey + **mid-stmt** — reference-lock + zerobas==reference on the repack machine + the range-
error divergence); lean `basic.rom` byte-identical (pinned sha256 unchanged); unit-test 43/43
(new `tests/test_mid_stmt.py`); `diskbasic-acceptance-repack` 34/34.

## Phase 3: console INPUT / LINE INPUT — keyboard line read (basic/input.asm, basic/files.asm, basic/main.asm, basic/sysvars.inc)

The **console** forms `INPUT ["prompt"{;|,}] var[,var…]` and `LINE INPUT ["prompt";] A$` — read a
typed line from the keyboard and parse it into variables. The **file** forms (`INPUT #n`,
`LINE INPUT #n`) already shipped (Phase-2 disk/tape); both stubbed the console form —
`input_common` did `jp nz,stmt_error ; console INPUT = Phase 3` (basic/files.asm). This slice
fills that stub. The biggest missing **interactivity** primitive: a program can compute and
`PRINT` but could not read a typed line (only `INKEY$`, one key). Spec:
[`docs/spec-basic-input.md`](../docs/spec-basic-input.md) (SIGNED OFF → SHIPPED). **Repack-only**:
the whole handler is assembled `IF ROM_BASE < $4000`; the byte-full lean `basic.rom` is
**unchanged** (pinned sha256 `e21f61fe…4228005`). Almost entirely **composition** of shipped
routines — the reason it is a slice, not a subsystem.

### Dispatch + reuse (basic/files.asm, basic/main.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `INPUT`→`$85` / `LINE`→`$AF` keyword crunch already tokenised (the file forms use them) — **no tokeniser / kwtable change** | — | pre-existing; the file forms shipped these | sourced |
| `input_common` branches `jp nz,input_console` (repack) / `jp nz,stmt_error` (lean) on the non-`#` (console) path; `FCH_RDMODE` (0=INPUT / 1=LINE INPUT), already set by `input_common`, selects the mode | — | own code (a gated one-line hook) | sourced |
| Reuses `read_line` (repl.asm; keyboard→LINEBUF), `read_into_strscr`+`ARL_GETBYTE`+`FCH_RDMODE` (files.asm; the file forms' field/line splitter, re-pointed at a console byte source), `var_name_key`/`var_set_key`/`var_str_type`/`str_set_key` (vars.asm; exactly as `ex_let`/`ex_let_str`) | — | own code (established idioms) — the shared splitter gives the console form the file forms' exact `,`/CR split, STRMAX clamp, and STRSCR descriptor | sourced |

### Semantics + handler (basic/input.asm `input_console`)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Prompt: a `"…"` literal is printed via CHPUT; then `;` → also print `"? "`, `,` → print nothing, bare `INPUT` → print `"? "`; `LINE INPUT` prints the literal but **never** `"? "` | — | public MSX-BASIC ref, **oracle-locked black-box** (`basic_probe_input.py` reference-lock then zerobas==reference: numeric/string/multi-var/LINE INPUT/prompt-`;`) | sourced |
| Comma-separated var list: each field split by `read_into_strscr` (mode 0) via `linebuf_getbyte`; numeric var → `input_num_field` → `var_set_key`; string var (`$`) → `str_set_key` (raw field bytes); numeric fields are **signed 16-bit integers** | — | public MSX-BASIC ref + oracle-locked; integer-only is the engine's stance (same as VAL, string-engine D-E) | sourced |
| `LINE INPUT` reads the **whole line** (mode 1 — commas and the leading space are data) into one `$`-var; a non-`$` var → `stmt_error` | — | public MSX-BASIC ref, oracle-locked (`" A,B C"` round-trips verbatim) | sourced |
| `linebuf_getbyte` — the one new `ARL_GETBYTE` source: next LINEBUF byte, advance `INP_CURSOR`; the 0 terminator reports EOF (CF set) **without** advancing — the same end contract `fat_io_getbyte`/`cas_in_getbyte` present, so the shared splitter drives the console line unchanged | — | own code (the tiny source vector) | sourced |
| `input_num_field` — strict signed-int16 validator accepting exactly `(spaces)(+\|-)?(digit+)(spaces)`; `str_val_parse` (VAL's parser) is too lenient — it accepts `"12x"` as `12`, which must `?redo` instead | — | own code (the documented integer INPUT-field contract; str_val_parse stays available for VAL) | sourced |

### Documented divergences (own design)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Re-prompt **wording** is the reference-verbatim `?Redo from start` / `?Extra ignored`. ⚠️ **Was zerobas's own lowercase (`?redo from start` / `?extra ignored`) until D-MSGEXACT (2026-08-02)** | — | **black-box oracle measurement** on Philips_VG_8020 + National_CF-3300 (`probes/basic/basic_probe_msgexact.py`, `docs/msgexact-msx1-characterization.md`), corroborated by the published MSX-BASIC reference (allowed-sources, grade B, "the user-visible language contract ... errors"). NOT from any disassembly | quarantined |
| Numeric fields are integer-only; a fractional / out-of-range field triggers the `?redo` re-prompt, not a float | — | own design (D-6); revisited when floats land | quarantined |
| `INPUT$(n)` (the no-echo n-key **function**) and numeric `INPUT#` (file form) are out of scope — separate later slices | — | own design (D-1); distinct mechanisms | — |

### Harness note

The parse core is BIOS-independent, so it carries an emulator-free host unit-test
(`tests/test_input.py`, 29 cases): `input_num_field` strict validation (rejects
empty/trailing-junk/embedded-space/fractional), `linebuf_getbyte` byte source + EOF, the
`read_into_strscr` field/line split driven through it, and `inpc_more_input`. The full statement
(prompt printing + `read_line` + assignment) needs the keyboard and screen — the openMSX oracle
probe's job. `basic_probe_input.py` **drives the keyboard** with a genuinely new wrinkle over the
INKEY$ probe: the program is typed and `RUN` first, and the INPUT **response** is a *separate*
keystroke burst delivered **after** the prompt appears (not batched with the program); `read_line`
blocks on Enter, so a response's arrival need only be ordered after `RUN`, and a `?redo` case
queues a second response after the first. A one-line harness fix landed in `omsx_run.py`: `type --`
ends option parsing so a response starting with `-` (a negative-number INPUT) is typed verbatim
instead of being swallowed as a command switch.

**Gates.** `make input-acceptance` PASS (8 cases: numeric / negative / string / multi-var / LINE
INPUT / prompt-`;` / `?redo` / `?extra` — reference-lock on the VG-8020 then zerobas==reference on
the repack machine; `?redo`/`?extra` differential the final value, wording differs per D-2); lean
`basic.rom` byte-identical (pinned sha256 unchanged); unit-test 44/44 (new `tests/test_input.py`);
`diskbasic-acceptance-repack` 34/34 (the file `INPUT#`/`LINE INPUT#` path shares `read_into_strscr`
— unregressed); `string-acceptance` PASS; `repack-boot` PASS; `audit-citations` clean.

## Phase 3: math float pack, F1 — float literals + PRINT (basic/float.asm, basic/interp.asm, basic/expr.asm, basic/print.asm, basic/program.asm, basic/sysvars.inc)

Slice F1 of the float-pack arc (docs/spec-basic-float-core.md, signed off
2026-07-11): decimal float literals crunch to the real `$1D`/`$1F` tokens and
PRINT renders them reference-identically. No float arithmetic yet (F2) and no
float variables (F3). Repack build only; the lean 16 KB `basic.rom` is
byte-identical (pinned sha256 unchanged).

### Representation + tokens

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Number format: lead byte = sign(bit7)+excess-64 exponent (byte 0 ⇒ value 0), then packed-BCD mantissa, 6 digits (single) / 14 (double), normalised 0.1 ≤ m < 1 | — | MSX2 Technical Handbook number-format chapter; **cross-checked byte-exact** black-box (`basic_probe_floatlit.py`, VG-8020 — the crunched value bytes ARE the stored form) | sourced |
| `SNG_TOKEN` / `DBL_TOKEN` literal tokens | `$1D`+4 B / `$1F`+8 B | MSX2 TH Table 2.20 + oracle capture | sourced |
| Classification (docs/spec-basic-float-core.md §9.2): `%`→int (consumed; >32767 = crunch error); `#`/`D`-exp→double; `!`→single; else D≤5 & ≤32767→int, D≤6→single, D≥7→double (D counts typed chars incl. trailing zeros) | — | oracle-locked black-box (`basic_probe_floatlit.py`, 60+ literal matrix incl. boundary/tie cases) | sourced |
| Rounding half-up at both precisions; carry-out-of-all-digits does NOT renormalise the exponent on the single path (`9999995!` → `1D 47 10 00 00` = 1000000) but DOES on the double path (16 nines → `1F 51 10 …` = 1E16) | — | oracle-locked (tie-breaker + carry captures, §9.2 rule 5) | sourced |
| Exponent walls: dec_exp ≤ 63 else crunch-time rejection; dec_exp < −63 → lead byte 0, mantissa retained (value 0) | — | oracle-locked (`1e62`/`1e63`/`1e-64`/`1e-65` captures; BLOAD-leads proves the rejection precedes execution) | sourced |
| Suffix-after-exponent is left unconsumed (`1e10#` leaves a raw `#`) | — | oracle-locked (extra S2 capture; `sub/tkfloat.asm` `tkf_try_exponent` header — the routine moved there in the sub-ROM wave-1 eviction, and D-EXPBAD measured that a DIGITLESS marker skips the suffix scan the same way) | sourced |
| All algorithms: digit scan, big-decimal round, BCD pack/unpack, `flt_out` layout | — | own-design (spec §9 distils the observed contract; no disassembly anywhere) | sourced |

### PRINT formatter (`flt_out`)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Display: sign space/`-` + digits + one trailing space; FIXED iff −1 ≤ dec_exp ≤ 14, else `E±nn` (2-digit, always signed; BOTH precisions use `E` — no `D` output form on this MSX1 reference); trailing zeros stripped; integer-valued → no point; <1 → leading `.`; value 0 → `0` | — | oracle-locked black-box (`basic_probe_float_fmt.py`, 60+ case matrix, VG-8020 ref-lock then zerobas==reference) | sourced |

### Documented divergences (own design)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| D-F1-1: crunch-time rejection message is the reference-verbatim `Overflow`. ⚠️ **Was zerobas's own lowercase until D-MSGEXACT (2026-08-02)** | — | **black-box oracle measurement** on Philips_VG_8020 + National_CF-3300 (`probes/basic/basic_probe_msgexact.py`, `docs/msgexact-msx1-characterization.md`), corroborated by the published MSX-BASIC reference (allowed-sources, grade B, "the user-visible language contract ... errors"). NOT from any disassembly | quarantined |
| D-F1-2: a float in an int context rounds half-up into the 16-bit ADDRESS domain (positives ≤65535 as the unsigned pattern — the published POKE/HEX$ −32768..65535 argument range; negatives ≥−32768); outside → 0 silently. Real Overflow semantics land in F2 | — | own design (interim; a strict-int16 cap would regress `POKE 40000,n` — caught in F1 review by `tests/test_str_fn.py` HEX$(65535)) | quarantined |
| D-F1-3: float operands under any operator (`+ - * / \ MOD AND OR XOR NOT` relationals) flag ERRMARK `$DD` and fall back to the rounded ints — no float arithmetic until F2 | — | own design (interim; `flt_guard` at every combine site) | quarantined |

### RAM + gates

New cells `$F01A–$F068` (FACTYP/TKOVF/FAC/FOUTBUF/TKDIG + scanner state) — own
choice, free RAM between basic's `CAS_VMIS $F019` and zerobas-disk's
`DRVA_DPB $F195` (the spec's suggested `$E0xx` cells were already occupied —
see sysvars.inc's comment). **Gates:** `basic_probe_floatlit.py --zb-machine`
ALL PASS; `basic_probe_float_fmt.py --zb-machine` ALL PASS;
`basic_probe_crunch.py` (lean + repack) ALL PASS; lean ROM byte-identical;
unit-test 45/45 (new `tests/test_float.py`); `diskbasic-acceptance-repack`
34/34; `string-acceptance` PASS; `input-acceptance` PASS; `audit-citations`
clean.

## Phase 3: math float pack, F2 — arithmetic + relationals + signed-int migration (basic/float-arith.asm, basic/float.asm, basic/expr.asm, basic/interp.asm, basic/print.asm, basic/poke.asm, basic/vdpio.asm, basic/str-engine.asm, basic/sysvars.inc)

Slice F2 of the float-pack arc (docs/spec-basic-float-core.md §10, oracle
round S2, 2026-07-11): `+ - * /` and the relationals now do real double BCD
arithmetic (single is storage-only, widens on use — supersedes §3b's
per-precision promotion sketch); `\`/`MOD` become signed and truncating;
two checked float→int16 domains (strict vs address) replace F1's interim
half-up rounding. New file `basic/float-arith.asm` (~2 KB); repack build
only, lean 16 KB `basic.rom` byte-identical (pinned).

### BCD arithmetic core (`basic/float-arith.asm`)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Working record: sign-magnitude, 14 significant BCD digits + 1 guard, unpacked one-digit-per-byte (`ARGA`/`ARGB`, own scratch — NOT `TKDIG`/`FOUTBUF`) | — | own design; digit width from the number-format spec (MSX2 TH), the unpacked layout and guard-digit rounding are an own-design implementation of the oracle-pinned rounding contract | sourced |
| `fp_add`/`fp_sub`: align by shifting the smaller-exponent operand (a digit shifted past the guard is dropped), same-sign add / diff-sign subtract-and-renormalise, round-half-up on the guard digit | — | own design implementing spec §10.2's pinned rounding + carry-renormalise cases (`1+5e-14`→tie-up, `1-1e-15`→carry through 14 nines, `99999999999999+1`→mantissa carry) | sourced |
| `fp_mul`: PRE-normalisation overflow/underflow check on the stored `dexp` sum (`e(a)+e(b)>63`→Overflow even when the normalised product fits); schoolbook 14×14→28-digit multiply; normalise; round | — | own design; the pre-check RULE (not the algorithm) is oracle-pinned (§10.2: `2e62*4`→Overflow though `8e62` is representable) | sourced |
| `fp_div`: divisor-zero → FPERR=2 (Division by zero); PRE-check on `e(a)-e(b)+1>63`; classic zero-pad/trial-subtract/append-digit long division, 15 quotient digits (14+guard) | — | own design; overflow-PRE-check rule oracle-pinned (§10.2: `2e62/.4`→Overflow though `5e62` fits) | sourced |
| Underflow (`e<-63` pre-check, either op) → silent 0, no FPERR | — | oracle-pinned (§10.2: `1e-40*1e-32`→`0`; boundary `1e-32*1e-32`→`1E-64` exact, `1e-33*1e-32`→`0`) | sourced |
| `fp_cmp`: same relation-bit convention as `cmp16_bits` (1/2/4 = lt/eq/gt) | — | own design, reusing the existing int-compare convention (expr.asm) so `combine_cmp`'s float and int paths are interchangeable to `ev_rel` | sourced |

### Domain converters + operator-site dispatch

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `fac_to_int_strict` (domain −32769<x<32768) and `fac_to_int_addr` (domain −32769<x<65536, wrap-then-truncate) — both TRUNCATE, not round | — | oracle-pinned (§10.3: `2.9\1`→`2`, `-2.9\1`→`-2`; address domain `40000.1`→`40001`, `65535.5`→wraps to `0`) | sourced |
| F1's `flt_to_int16` reworked to the same wrap-then-truncate shape but SILENT (no FPERR) — used eagerly on every float factor, per spec §1 | — | own design; supersedes F1's D-F1-2 half-up interim (§10.3 explicitly corrects it) | sourced |
| Operator-site protocol: a fixed-size LHS frame (FACTYP+FAC, 9 significant bytes) is pushed onto the Z80 stack at every `+ - * relational` site before the RHS is evaluated (FACTYP reset to 2 first); `combine_add`/`sub`/`mul`/`cmp`/`div_float` pop it back and dispatch int-fast-path-with-overflow-promotion vs BCD widen-and-combine | — | own design (spec §1 bullet 4's named mechanism); overflow-promotion RESULTS are oracle-pinned (§10.2: `32767+1`→`32768.0` double, `3125*625`→`1953125` exact) | sourced |
| int⊗int overflow detection via the Z80 P/V flag after `ADC`/`SBC HL,ss` (`+`/`-`) and a full 32-bit unsigned product (`mul16x16_32`, `*`) — not 16-bit wraparound | — | own design; Z80 P/V-on-signed-overflow is architecture, not a reference-BASIC behaviour | sourced |
| `/` is unconditionally the float path in the repack build (no int fast path) | — | oracle-pinned (§10.1: "`/` is always real division, always double") | sourced |
| Relationals never int-convert either side — both operands widen to double when either is float | — | oracle-pinned (§10.1: `40000=40000!`→`-1`, no Overflow) | sourced |

### Signed `\` / `MOD` (D-C migration)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `signed_div_de_bc`/`signed_mod_de_bc`: truncating signed division/remainder built around the existing unsigned `udiv16` magnitude divide; divisor 0 → FPERR=2 | — | own design; truncating-toward-zero + remainder-takes-dividend's-sign is oracle-pinned (§10.4: `7\2`→`3`, `-7\2`→`-3`, `7\-2`→`-3`, `-7 mod 2`→`-1`) | sourced |
| Quirk: `-32768\-1` → true magnitude 32768 does not fit int16 → silently promotes to a double `32768.0` (no Overflow) | — | oracle-pinned (§10.4, the one case where signed division's own result escapes int16) | sourced |

### Runtime error surface (D-F2-1)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| New `FPERR` cell (0 none / 1 overflow / 2 division-by-zero); statement drivers (`ex_if`/`ex_let`/`exp_num`) check it right after `eval()`/`ev_rel` and abort the WHOLE statement, mirroring D-2's `TMISMATCH`/`type_mismatch_error` pattern exactly. ⚠️ **D-PENDERR (2026-08-09) finished the sentence**: the codes now run 1..11, D-2's marker became one of them (`FPERR_TYPEMM` = 10), the separate cell is retired, and the write is **set-if-empty** (`penderr_set`, `basic/str-engine.asm`) so of two faults pending in one statement the FIRST is the one reported — measured on both references, `docs/penderr-msx1-characterization.md` §1 | — | own design, D-2's established abort shape reused verbatim for the new flag; the first-error-wins ORDER is **black-box oracle measurement** (`probes/basic/basic_probe_penderr.py`, `make penderr-acceptance`, 61 rows on VG-8020 + CF-3300) | sourced |
| Abort wording: `Overflow` REUSES `program.asm`'s crunch-time `err_overflow` string byte-for-byte (not duplicated); `Division by zero` is its own string. ⚠️ **Both were zerobas's own lowercase until D-MSGEXACT (2026-08-02)** | — | **black-box oracle measurement** on Philips_VG_8020 + National_CF-3300 (`probes/basic/basic_probe_msgexact.py`, `docs/msgexact-msx1-characterization.md`), corroborated by the published MSX-BASIC reference (allowed-sources, grade B, "the user-visible language contract ... errors"). NOT from any disassembly | sourced |
| `POKE`/`VPOKE` switch to `fac_to_int_addr` (checked, FPERR on overflow) instead of the silent eager conversion every other int-argument statement still uses (D-F2-2 residue, listed below) | — | own design; POKE/VPOKE are the two statements whose argument IS the address domain by definition (spec §10.3) | sourced |
| `HEX$`'s argument conversion also switches to `fac_to_int_addr`, so `PRINT HEX$(65536.)` aborts the whole PRINT line (checked live: `[` never prints) | — | oracle-pinned (§10.2: "in `print "[";1/0;"]"` the `[` prints, then the message, never the value or `]`") | sourced |

### Documented divergences / residue (own design)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| D-F2-1: runtime numeric errors abort the statement with the reference's verbatim wording. ⚠️ **Was zerobas's own lowercase until D-MSGEXACT (2026-08-02)** — the D-2 wording convention it followed is withdrawn tree-wide | — | **black-box oracle measurement** on Philips_VG_8020 + National_CF-3300 (`probes/basic/basic_probe_msgexact.py`, `docs/msgexact-msx1-characterization.md`), corroborated by the published MSX-BASIC reference (allowed-sources, grade B, "the user-visible language contract ... errors"). NOT from any disassembly | quarantined |
| D-F2-2: the SILENT eager `flt_to_int16` residue on int-argument sites not wired in F2 (POKE/VPOKE/HEX$/PRINT only) is being closed by the dedicated D-F2-2 arc (docs/spec-basic-df2-2-intarg-coercion.md, VG-8020-pinned). **Stage A1 LANDED 2026-07-19: `OUT` (`basic/vdpio.asm` `do_out`) port+value now use the checked ADDRESS domain `eval_addr` + `check_fperr_only` (Overflow ERR 6 outside 0..65535)** — mirrors POKE; self-funded by tightening `do_vpoke` to the same shared check. **Stage A2+VPEEK LANDED 2026-07-19 (`basic/expr.asm` `ev_ff_arg`, repack-only `IF ROM_BASE < $4000`, lean byte-identical): PEEK/INP re-coerce via `fac_to_int_addr`+`check_fperr_only` (address domain → ERR 6); VPEEK via `fac_to_int_strict`+`check_fperr_only` (int16 → ERR 6 >32767) then a VRAM `and $C0` range-check (0..16383 → ERR 5 outside). One inline check at the shared PEEK/VPEEK/INP parse point, selector-gated on `C` so EOF/LOF/DSKF/CVI skip it; fires even in non-`check_expr_errors` consumers (FOR bounds), which the statement-boundary path structurally could not. Funded by the disk/file cluster eviction Phase 1 (39 B).** **Stage B LANDED 2026-07-19 — CLOSES the arc (`basic/interp.asm` tail leaves `get_byte_arg`/`get_vram_arg` over `get_int16_checked` = HL-guarded `fac_to_int_strict`+`check_fperr_only`, all repack-only `IF ROM_BASE < $4000`, lean byte-identical): the byte-domain sites STRING$ count+char / SPACE$ count / `ON n` selector / `WIDTH n` (`str_fn_string`/`str_fn_space` str-engine.asm, `ex_on` program.asm, `ex_width` screen.asm) route through `get_byte_arg` (int16→ERR 6, then high-byte-set→ERR 5 for >255/negative); VPOKE addr (`do_vpoke` vdpio.asm) corrected OFF the too-wide F2 `fac_to_int_addr` (0..65535) ONTO `get_vram_arg` (int16→ERR 6, then `and $C0`→ERR 5 for 16384..32767/negative — the VRAM size 0..16383), and the landed VPEEK inline block deduped to `call get_vram_arg`. All Group-B callers main-resident (Q2), so one main leaf reaches all. Leaf sited at the file tail because a mid-file 31 B insert broke page 1's forward `jr`s to `goto_resolve`/`ex_if`.** | — | own design; A1+A2+B all landed + gated (`make intarg-acceptance`, 37/37 asserted incl. boundary/negative guards); domains VG-8020-black-box-pinned, error numbering per the published MSX-BASIC language reference (L110), no reference-ROM disassembly | sourced |

### Correctness fixes found in review (not oracle-pinned; internal control-flow)

Three architectural bugs were found and fixed during F2's own implementation
review, all instances of the same root cause — a shared "abort the whole
operation" tail (`raf_zero_ok` / `type_mismatch_error` / `fp_runtime_error`,
reached via a jump chain) reached through an intervening `call` boundary,
so the abort's own final `ret` resumed the WRONG frame instead of unwinding
past it. Fixed by having each such gate (`check_preexp_bounds` in
float-arith.asm; `push_lhs_frame`/`pop_lhs_and_probe`, also float-arith.asm;
`check_expr_errors`/`check_expr_errors_popbc` in interp.asm) explicitly
discard the dead intervening return address(es) before jumping into the
shared abort tail — own design, no oracle involvement (pure Z80 stack-frame
mechanics). Caught by `tests/test_float.py`'s F2 matrices and, for the
`interp.asm` instance, by `tests/test_str_compare.py`'s pre-existing D-2
regression cases (`unit-test`'s full run, not the float-specific gate
alone) — a reminder that a shared abort-tail refactor needs the FULL
`unit-test` suite, not just the touched feature's own gate.

### RAM + gates

New cells `$F069–$F104` (FPERR/ARGA/ARGB/MULPROD/DIVPAD/DIVREM/CVT +
combine-site scratch), all below zerobas-disk's `DRVA_DPB $F195` except the
tail (`FP_OPMODE`/`CVT_MODE`/`PLF_RA`/`PLF_RA2` at `$F0FF–$F104`, still
inside the free window — see sysvars.inc). **Gates:** `make` (lean) clean,
16384 B, byte-identical to the pre-F2 baseline; `make basic-reloc` +
`tools/check_reloc.py` clean (relocated image 22510 B, low region occupied,
lean unchanged); `make unit-test` 45/45 files (`tests/test_float.py`'s F2
matrices all pass: fp_add/sub/mul/div/cmp, both converters' domain/boundary
matrices, signed `\`/`MOD` incl. the `-32768\-1` quirk, int-overflow
promotion via `eval()`); `basic_probe_crunch.py` (lean, `--cart`) ALL PASS;
`basic_probe_controlflow.py`/`basic_probe_loops.py`/`basic_probe_data.py`/
`basic_probe_statements.py` (lean, `--cart`) ALL PASS; `audit-citations`
clean for `basic/`.

**Space blocker found this pass, RESOLVED same day (D5 revision):** F2 grew
the low region ($2812–$3FFF) past the zerobas-tape page-0 patch's reserved
splice window at `$3A72–$3C43` (D5), a constraint the implement brief's
~2.0 KB budget did not account for — `make repack-main` failed its
free-hole check, blocking the repack-machine differential gates. Resolved
by revising D5 (spec-cbios-repack-tooling.md §6): the tape body moved to
`FREE_ORG = $09EE`, the `0x00` fill free in ALL C-BIOS main variants,
freeing the whole `$2812–$3FFF` window for BASIC. The differential-oracle
gates were then run by the review pass (results recorded at the F2 S2
close-out entry below).

### F2 S2 close-out — review pass (Fable) + full gate record (2026-07-11)

The review pass found and fixed TWO further bugs, both invisible to the
implement pass's own matrices (the F1 lesson repeating: live/differential
checks catch what the unit matrices structurally cannot):

| What | Cited source | Status |
|---|---|---|
| IF truthiness over a float condition (`basic/interp.asm` ex_if): the condition was judged by the eagerly TRUNCATED DE, so `IF .5 THEN` took the FALSE branch. Fixed by a FACTYP dispatch (float -> DE:=0/1 from FAC's lead byte). Oracle-pinned by a companion capture (spec §10.4a: reference takes the TRUE branch on `IF .5 THEN`, FALSE on `IF 1.5-1.5 THEN`); pinned into the probe's RAW_LINES + re-verified live on the repack machine | spec §10.4a (basic_probe_float_arith.py companion capture, VG-8020) | sourced |
| Float relationals trashed ev_rel's REQUESTED relation bits (`basic/float-arith.asm` combine_cmp): the widen/fp_cmp core clobbers C, so `and c` intersected with a leftover constant that happened to hold the =/> bits — every float `=`/`>` compare passed BY LUCK, every float `<`/`<>`/`<=` answered wrong (`1.5<1.4` -> -1). Caught by the FULL differential gate, first run. Fixed by BC save/restore on the float path; six eval()-integration cases added to tests/test_float.py so the fast layer pins it | own design (fix); spec §10.1 (the pinned contract the bug broke) | sourced |

Probe hardening in the same pass (basic_probe_float_arith.py): machine-
agnostic screen tails (zerobas's `zb>`-prefixed echo + bare-`zb>` prompt
terminator), RAW lines compare their bracket SPAN (a >38-char echo wraps and
has no matchable row), and SPAN_ONLY error cases now REQUIRE a tail on both
sides (a dead machine can no longer pass vacuously on two absent spans).

Also observed, documented, NOT chased (pre-existing, out of F2 scope): the
expression-error surface is lenient — an unbalanced `(`-chain sets ERRMARK
but PRINT still prints a value (lean: the error-marked 0; repack + floats:
the FAC value, since exp_num dispatches on FACTYP). Same D-2-family
leniency genre as ev_f_err's 0-result convention; F2 changes its FLAVOR for
float expressions, nothing more.

**Full gate record (final bits, 2026-07-11):** `make float-acceptance` ALL
PASS — LITERALS + FORMAT halves (F1, unchanged) + the new ARITH half
(basic_probe_float_arith.py, **167/167** vs the VG-8020: expressions, error
surface incl. statement aborts, both conversion domains, signed \/MOD,
IF truthiness, multi-item PRINT); `make unit-test` **45/45** files (incl.
the new relational-bits cases); crunch probe byte-identical; the 4
regression probes ALL PASS; `make string-acceptance` PASS (6 halves);
`make input-acceptance` ALL PASS; `make diskbasic-acceptance-repack` 34/34;
`make audit-citations` clean; lean `basic.rom` byte-identical to the pre-F2
baseline (cmp). The space blocker was resolved by the D5 revision (tape
body -> `$09EE`, commit 781348f, its own tape-gate re-run recorded there).
Post-F2 space: page-0 content to `$3FFD` (2 B slack), page-1 tail 29 B —
the window is essentially FULL; see the spec's D-G addendum for the F3
space levers.

## FAT12 primitive/sector-layer eviction, Phase 1 (basic/fat.asm, basic/fat-prim-body.inc, basic/fat-delete-body.inc, sub/fatprim.asm, basic/sysvars.inc, sub/equates.inc, sub/sub.asm)

**What changed and why.** `docs/spec-evict-diskfile-cluster.md` §11 (SIGNED
OFF 2026-07-19). Phase 1 of the disk/file command cluster eviction: the
FAT12 **primitive/sector layer** of `basic/fat.asm` (`dskio_calslt`,
`read_sector`/`write_sector`, `fat_mount`, `fat_find`/`name_cmp`, the
cluster-chain walk, free-cluster allocation + FAT12 write-back, directory
create/update, and `fat_delete`) moves to a NEW sub-ROM PAGE-1 tenant
(`sub/fatprim.asm` `fatprim_tenant`, `SUBROM_IDX_FATPRIM=12`). The
byte-granular `fat_io_*` cursor (`fat_io_open`..`fat_io_close`) stays
main-ROM-resident in BOTH builds — it is reached via the `ARL_GETBYTE`
polymorphic RAM vector, valid only while the owning code is mapped in, so it
cannot move yet (spec §11's empirical rationale, measured 2026-07-19).

**Shape.** One selector-dispatched tenant entry (not 15 separate indices):
`fatprim_tenant` reads a `DISKOP_OP` byte (RAM) and jumps to the requested
primitive via a table indexed by `BC*3` (not `HL`/`DE` — those carry the
primitive's real inputs, passed through `subrom_call`/`CALSLT` untouched).
The shared bodies are `basic/fat-prim-body.inc` (`dskio_calslt`..
`fat_dir_update`) and `basic/fat-delete-body.inc` (`fat_delete` — kept in a
SEPARATE file only because it sits AFTER the resident `fat_io_*` cursor in
`basic/fat.asm`, so the lean cart's original byte ORDER — primitives, then
cursor, then `fat_delete` — could only be preserved by including it
separately at its original position). Lean 16 KB cart (`ROM_BASE >= $4000`):
both `.inc` files are included inline at their original positions,
BYTE-IDENTICAL to the pre-eviction build. Repack build (`ROM_BASE < $4000`):
`basic/fat.asm` emits resident SHIMS under the SAME 15 names instead, so
every existing call site across the codebase (`field.asm`/`files.asm`/
`cload.asm`/`expr.asm`, plus the resident `fat_io_*` cursor's OWN calls into
the primitive layer) is unchanged.

**Marshalling.** Cy cannot ride back through `subrom_call`/`CALSLT` (its own
`or a` always clears it — the `sub/format.asm` rule). Every primitive's exit
funnels through a uniform tenant-side stash of `{HL, A, a 0/nonzero STATUS
byte}` into a small `DISKOP` result block (`basic/sysvars.inc`); every
resident shim reloads HL+A and reconstructs Cy from STATUS identically. Two
primitives needed a non-uniform tail: `name_cmp` (Z, not Cy — STATUS doubles
as the Z surrogate) and `fat_count_free` (DE, not Cy/HL — mirrored into
`FAT_WRTMP2`, its own already-RAM-visible scratch, rather than a new RAM
cell, since the DISKOP block's 5-byte gap was already fully claimed by
OP/STATUS/A/HL). `fat_alloc_cluster`'s HL (the one real caller-read register
output besides the two above, `field.asm:576/599`) is covered by the
uniform reload — no bespoke handling needed.

**RAM.** The `DISKOP` block claims the LAST 5 free bytes below `FCH_CTX`
(`$E9FB`..`$E9FF`) — a genuine unclaimed gap, not a live-scratch alias:
unlike `FMT_GEOMSEL`/`FMT_RESULT` (safe to alias tape CSAVE/BSAVE scratch
because CALL FORMAT never nests inside a tape save), a FATPRIM shim is
reachable from INSIDE `do_save`'s `DSV_PTR`/`DSV_END` walk and `field.asm`'s
`GP_*` random-access loop state, so aliasing onto either would let a
primitive call clobber the caller's own live loop variables mid-walk.

**A same-assembly naming collision, found and fixed.** `sub/format.asm`
already defines its own private `write_sector` (FORMAT's sub-local CALSLT
write path, with its own `FMT_RESULT` stash) in the same `sub.rom` image —
pasmo has one flat global namespace, so `fat-prim-body.inc`'s copy could not
also be named `write_sector` once both tenants shared one assembly. Fixed by
naming the shared body's copy `fatprim_write_sector` and adding a zero-byte
`write_sector equ fatprim_write_sector` alias in `basic/fat.asm`'s lean
branch (right after the include) so every existing external call site
(`field.asm`/`files.asm`'s literal `call write_sector`) is unaffected; the
repack shim is independently named `write_sector` already (a different code
path, no collision).

**Gates (2026-07-19).** `make unit-test` 46/46 files. `make basic-reloc`:
lean `basic.rom` byte-identical (SHA256 matches `LEAN_SHA256` unchanged);
`check_kwtable_identity` OK; `check_resident_abi` OK; `check_tenant_closure`
(`--page1`, seeded from `sub_p1_table` incl. `fatprim_tenant`) OK — 168
routines closed, no main-page-1 escape (a pure RAM+BIOS(CALSLT) leaf, same
shape as `format_tenant`/`scan_stmt_end`, no resident-ABI import needed).
Page-1 free: **6 B before → 1185 B after** (`__MEAS_PAGE1_END`), i.e. **+1179
B freed** — funds D-F2-2 A2+VPEEK (33 B) + stage B with large headroom.
Machine-based disk-verb differential gates (`make diskbasic-acceptance`,
the adversarial VG-8020/CF-3300 pass) were NOT run in this session — they
need the installed oracle machines (a shared side effect out of scope here)
and are the parent's job per the implementation brief.

Clean-room: original code (the split mechanism, DISKOP marshalling, and
selector dispatch are own-design, the `CALL FORMAT` precedent + MSX2
Technical Handbook CALSLT/EXBRSA/sub-ROM-signature ABIs); the primitive
bodies are copied verbatim from our own `basic/fat.asm` (see that file's
header, and `§disk DSKIO host engine` above, for the full FAT12/DSKIO
provenance / oracle citations). No reference-ROM disassembly.

## Directory-verb I/O eviction, Phase 2 — KILL + NAME (basic/files.asm, sub/dirverb.asm, basic/sysvars.inc, sub/equates.inc, sub/sub.asm)

**What changed and why.** `docs/spec-evict-diskfile-cluster.md` §12. Phase 2
of the disk/file command cluster eviction: the disk **I/O bodies** of the two
directory-write verbs `KILL` and `NAME` move to a NEW sub-ROM PAGE-1 tenant
(`sub/dirverb.asm` `dirverb_tenant`, `SUBROM_IDX_DIRVERB=13`). Their `eval`/
parse HEADS stay main-resident (a page-1 tenant cannot reach `eval`/the
parser): `parse_disk_fcb`, the verbatim-ASCII `"AS"` scan, and the
`DISKSLOT_OK` check run resident and marshal their result into page-3 RAM
(`DISK_FCB_NAME`, plus `FWR_DIRSEC`/`FWR_DIROFF` set by the resident
`fat_mount`+`fat_find` shims for NAME) before a single `subrom_call` hands the
CALSLT-side sector work to the tenant.

**Why Phase 2 is small (measured).** Phase 1 already relocated the heavy
FAT12 primitive/sector engine to `fatprim_tenant`, so KILL/NAME were already
thin orchestration over sub-ROM shims. The tenant bodies call those Phase-1
primitives (`fat_delete` / `read_sector` / `fatprim_write_sector`) SUB-LOCALLY
(co-resident in the same page-1, no nested marshalling). Net page-1 relief was
therefore modest — **1117 B free before → 1134 B after (+17 B)** — and the
phase's real value is proving the selector-dispatched verb-body tenant pattern
that Phase 3 (LOAD/SAVE/BLOAD/BSAVE/MERGE/RUN) will scale up. `FILES` was left
resident by design (user decision): its listing loop interleaves `CHPUT` +
main-resident `print_crlf`, a head/body fork not worth Phase 2's risk.

**Shape.** ONE selector-dispatched tenant entry (like `fatprim_tenant`):
`dirverb_tenant` reads `DISKOP_OP` and branches — `DISKOP_SEL_KILL=0` →
`tnt_kill` (the `fat_delete` loop), `DISKOP_SEL_NAME_STAMP=1` →
`tnt_name_stamp` (read dir sector, overwrite the 11-byte 8.3 name in place,
write it back). These two values are a SEPARATE namespace on the same
`DISKOP_OP` cell as fatprim's `SEL_*` (only one `subrom_call` reaches one
tenant at a time, so 0/1 here do not alias fatprim's `READ_SECTOR`/
`WRITE_SECTOR`). Lean 16 KB cart (`ROM_BASE >= $4000`): the verb bodies stay
inline in `basic/files.asm`, BYTE-IDENTICAL to the pre-eviction build. Repack
(`ROM_BASE < $4000`): the `ELSE` branches of `do_kill`/`do_name` emit the
`subrom_call` head instead.

**NAME is a "stamp-only" split (no new RAM).** The resident head keeps
`fat_mount`+`fat_find` as the existing shims (OLD name in `DISK_FCB_NAME`),
then parses the NEW name into `DISK_FCB_NAME`; the tenant only does the
read+overwrite+write using `FWR_DIRSEC`/`FWR_DIROFF` + `DISK_FCB_NAME`. This
avoids a second 11-byte name buffer (the `$E0ED+` gap is fully claimed by
DSV/TSV/FILES/FCH scratch) and preserves the ORIGINAL statement ordering
(find-old-then-parse-new) exactly. A hypothetical full-op NAME (marshal both
names, fold mount+find into the tenant) would reorder new-name parsing before
the find, but since `parse_disk_fcb` errors and old-not-found BOTH route to
`load_error` ("load error"), even that reorder would be observationally
identical — recorded here as the reason the stamp-only choice costs no
behaviour.

**Marshalling.** Cy cannot ride back through `subrom_call`/`CALSLT`, so each
body returns disposition in `DISKOP_STATUS`. The two bodies use DIFFERENT
polarity, each read only by its OWN head: NAME_STAMP → 0 ok / 1 error
(standard); KILL → the deleted-any flag (0 = nothing matched → the head
raises "File not found" via `load_error`; nonzero = ok). KILL's flag mirrors
`basic/files.asm`'s ORIGINAL `do_kill` bug-for-bug: a real I/O error mid-loop
is treated as "no further match" (`fat_delete`'s Cy stops the loop), and
success is reported iff ≥1 entry was freed before the error.

**Gates (2026-07-20).** Lean `basic.rom` byte-identical; `check_tenant_
closure --page1` OK (14 page-1 tenants incl. `dirverb_tenant`, no main-page-1
escape); `check_resident_abi`/`subrom-abi-check` OK (sub.rom not stale);
`make unit-test` 46/46. `make diskbasic-acceptance` (lean **34/34**) +
`diskbasic-acceptance-repack` (**34/34**) — boot-per-probe differential vs the
real National CF-3300, incl. `disk_probe_kill.py` (real file delete → disk
byte-identical to CF-3300) and `disk_probe_name.py` (rename → byte-identical).
Adversarial boot-per-case edges the happy-path corpus skips: `KILL"NOSUCH.FIL"`
→ "load error" (confirms the STATUS=deleted-any=0 → `load_error` polarity),
`NAME"GHOST" AS ...` (old absent) → "load error". Test disks were /tmp copies;
no committed `.dsk` mutated.

Clean-room: original code (dispatch/marshalling glue own-design, the
`CALL FORMAT`/`fatprim` precedent + MSX2 Technical Handbook CALSLT ABIs); the
sector work reuses our own `basic/fat.asm` primitives sub-locally; KILL/NAME
*semantics* trace to `§KILL`/`§NAME` above (public MSX-BASIC language reference
+ black-box CF-3300). No reference-ROM disassembly.

## Phase 3: graphics G6 — `DRAW` (basic/graphics.asm, basic/usr.asm, basic/interp.asm, basic/kwtable.inc, basic/sysvars.inc, sub/graphics.asm, sub/deftype.asm, sub/sub.asm)

`DRAW <string>` — the MML-style macro language: `U D L R E F G H`, absolute and
relative `M`, the `B` (blank) and `N` (no-update) prefixes, `C` colour, `S`
scale, `A` angle, `X <expr$>;` substring execution and `=<expr>;` substitution.

**Language source.** `DRAW`'s *syntax and command repertoire* is the public
MSX-BASIC language reference. Every *numeric and behavioural* rule below is this
project's own black-box measurement of a reference machine profile — inputs in,
observed effects out — recorded in `scratchpad/g6_draw_notes.md` with the probes
that produced it (`scratchpad/g6_draw_char{1..7}.py`) and distilled into
[docs/spec-basic-graphics-g6.md](../docs/spec-basic-graphics-g6.md). No
reference-ROM disassembly; nothing here is derived from stock ROM bytes.

Measured contracts new to this slice (spec §3–§6):

- **the scale/count arithmetic**: `distance = signed16((n × S) mod 65536) / 4`,
  truncating **toward zero** — one rule that reproduces every large-count wrap
  observed (`U32767` → *down* 1, `U32768` → no move, `U33000` → up 232,
  `U40000` → up 7232, `U65535` → down 1) and the negative rounding
  (`S3U-10` → 7, not 8); falsified on seven fresh (n,S) pairs before coding;
- **`S` and `A` persist across `RUN`/`NEW`/`CLEAR`/`CLS`/`COLOR`/`SCREEN`** —
  only a power-on resets them (to 4 / 0), hence the cold-only init in `init`;
- **the angle rotates relative motion only** (never absolute `M`);
- **`DRAW`'s colour is the shared graphics attribute `ATRBYT` `$F3F2`** (the
  address is the published MSX work area): every graphics statement given an
  explicit colour stamps it, every colourless one stamps `FORCLR`, and `DRAW`
  reads it, writing only on `C n`. Introduced here and stamped from the tenant's
  dispatcher so `PSET`/`PRESET`/`LINE`/`CIRCLE`/`PAINT` all feed it;
- the error surface (§5), and that a `DRAW` `M`-segment is **byte-identical to
  the same `LINE`** — so G6 adds no rasteriser and reuses the landed G3 one.

**Own-design.** The parser, the co-routine split between the page-0 tenant and
the resident (the tenant cannot resolve `=var;` itself: a page-0 tenant has the
float pack switched out), the frame stack behind `X`, and the marshalling are
all zerobas's own. Two own-design caps have no measured counterpart and are
documented as such (spec D-G6-4): `X` nesting depth (8) and the total spliced
text (256 B), both raising `ERR 5`.

**Gate.** `make graphics-acceptance` Phases K/L/M — a differential against the
reference machine profile reading pattern **and** colour through `POINT`, the
25-case error surface, and the across-`RUN` persistence that no single-program
test can see. Plus `make unit-test` (`gdrw_scale`/`gdrw_rotate`, whose fixtures
are the measurements themselves).

## Space: `DEFtype` → page-0 sub tenant (basic/usr.asm, sub/deftype.asm, sub/sub.asm, basic/sysvars.inc)

`DEFINT`/`DEFSNG`/`DEFDBL`/`DEFSTR`'s body moved to the sub-ROM to fund G6's
resident half — see [docs/spec-eviction-g6-space.md](../docs/spec-eviction-g6-space.md).
Our own code, relocated verbatim bar the tenant ABI (cursor through `DEFT_PTR`,
`stmt_error`/`exec_stmt` tails become a status and a `ret`). The language is
unchanged, and the routine was already repack-only, so the lean cart is
byte-identical by construction. Clean-room: no disassembly — this is a move of
code we wrote.

> ⚠️ **"Relocated verbatim" describes THIS carve, not the file today.**
> D-DEFINTTOK (2026-08-18) and D-DEFTYPETOK (2026-08-19) gave all four verbs
> their own oracle-pinned single-byte tokens (`$AB`..`$AE`) and **deleted** the
> mnemonic-text parser this carve had moved, replacing it with a token peek and
> a 4-byte type-code table; the two resident handlers merged into one
> (`ex_deftype`). The language DID change there — the crunched byte shape did —
> and it changed toward the reference. Clean-room basis is unaffected: those
> tokens were read off a live VG-8020, not lifted
> ([docs/lnref-msx1-characterization.md](../docs/lnref-msx1-characterization.md)
> §4). The tenant ABI above (`DEFT_PTR`, `DEFT_STATUS`) is unchanged.

## 2026-08-19 — `VARPTR(<unset scalar>)` is `Illegal function call` (D-VPTRDOM) (basic/expr.asm)

`ev_f_varptr` created the variable when it did not exist — a signed-off arrays
slice-4b design choice (§3a), and measured wrong: `X=VARPTR(Q)` with `Q` unset is
`Illegal function call` on the VG-8020 **and** the CF-3300, against a `Q=1`
control silent on all three. **Two references.** The scalar path now calls
`var_find_typed` (find, never allocate) and defers FPERR=3 → ERR 5 through the
shared `ev_f_defer` tail. The ARRAY-element form is untouched: `VARPTR(A(1))`
still auto-dims on read, as the references do.

Consequence, recorded because it is a loss of coverage: `VARPTR` was the only
eval-time scalar allocator, so the arrays-§13a mid-statement `ARYTAB` shift is
now unreachable from BASIC on every side. The §13a guards stay (cheap, static
argument, needed again if an allocator returns); five `array-acceptance` rows
that forced the class through the old `VARPTR` are retired, 151 → 146.

Clean-room: our own code. The reference behaviour was established by black-box
probing (`PRINT VARPTR(ZZ)` on a never-referenced name), recorded in
`probes/basic/basic_probe_arrays.py` since 2026-07-17 and re-measured 2026-08-08
and 2026-08-19. No disassembly.

## 2026-08-19 — the `ev_sp` duplicate-load carve (D-EVSPDUP) (basic/expr.asm)

`ev_sp` skips spaces and returns with `A` holding the first non-space byte — its
only exit is `ret nz`, taken straight after `ld a,(ix+0)`. All 24 of its call
sites in `expr.asm` followed it with a second `ld a,(ix+0)`, reloading what it
had just returned: 3 B each, 72 B. Removed; main page-1 free 3 B → 69 B. No
behaviour change intended or measured, and the register contract is now written
down at `ev_sp` itself because no gate can check one. Knife K-VS1 (`ld a,(ix+1)`,
same length) turns `unit-test` and `float-acceptance` red, so the contract is
under test.

Clean-room: our own code, a redundancy removal. No disassembly.

## 2026-08-19 — `INPUT #n` takes a LIST of targets (D-INPLIST) (basic/files.asm)

`inp_readvar` parsed exactly ONE target and fell into `jp exec_stmt`, so the
leftover `,` of `INPUT#1,A$,B$` raised `Syntax error`. Oracle: the CF-3300 reads
`HILO` over a `HI,LO` file (row `f.mixctl`, carried DEFERRED in
`lvfix-acceptance` since D-LVFIX measured it 2026-08-08 and re-confirmed
2026-08-09). ONE reference only — `INPUT #n` is Disk BASIC and a diskless
VG-8020 cannot express it.

The loop is the routine itself: `inp_readvar` already required the separator on
entry (for the comma after the channel number), and the comma between two
targets is the same byte in the same place, so the tail tests for one and
re-enters at the top. 7 B, no second parser.

Funded in `do_open`, +8 B: the "APPEND" match was four unrolled
`cp`/`jp nz`/`inc hl`/`ld a,(hl)` groups for a sequence that is plainly DATA, and
is a 13 B loop over a 5-byte `oo_app_seq` now; six `jp cc,stmt_error` sites in
that parse share one local `oo_synerr` trampoline. Page-1 free 2 → 10 → 3 B; the
carve was built and gated ALONE first (`diskbasic-acceptance` 34/34) so that
"behaviour unchanged" is a reading rather than an argument.

Clean-room: our own code. The one oracle fact the APPEND sequence encodes — that
the main-ROM tokeniser crunches "APPEND" to `$41 $50 $50 $81` — was already
measured and is unchanged by moving it from instructions into a `db`.

## Phase 3: input devices, I1 — `STICK(n)` / `STRIG(n)` (basic/expr.asm, basic/kwtable.inc, basic/sysvars.inc)

The joystick/cursor direction reader and the trigger reader, as the first slice
of the input-devices arc
([docs/spec-basic-input-devices.md](../docs/spec-basic-input-devices.md)).

**Sourced — published contracts.** The two BIOS entry points and their
signatures come from the MSX Assembly Page BIOS call list / MSX Technical Data
Book (allowed sources): `GTSTCK` `$00D5` (A = device 0..2 in, A = direction 0..8
out) and `GTTRIG` `$00D8` (A = trigger 0..4 in, A = `$00`/`$FF` out). Both are
documented "Registers: All", which is why the token cursor `IX` is guarded
across the calls even though our C-BIOS target does not in fact touch it.

**Sourced — this project's own black-box oracle** (Philips VG-8020; raw record
[scratchpad/i1_input_notes.md](../scratchpad/i1_input_notes.md), scripts
`i1_input_char1.py` / `i1_input_char2.py`). No reference-ROM disassembly. The
measured facts the implementation reproduces:

- the crunch tokens `STICK` = `$FF $A2`, `STRIG` = `$FF $A3` — two-byte
  `$FF`-prefixed FUNCTION tokens, the `PEEK` shape, so no statement token;
- the domains (`STICK` 0..2, `STRIG` 0..4) and the errors outside them
  (`ERR 5`), including that an in-int16 but out-of-domain index such as
  `STICK(32767)` is `ERR 5` while `STICK(32768)` is `ERR 6`;
- the argument coercion: **truncate toward zero** on both signs, pinned with
  discriminators where rounding and truncating disagree (`STRIG(4.9)` → 0,
  `STICK(-0.6)` → 0);
- the grammar surface (`ERR 2` for a missing/unclosed/extra argument list, for
  statement position, and for a bare name; `ERR 13` for a string argument);
- the eight-way direction encoding and its cancellation rule, measured live
  against the key matrix: row 8 bit 4/5/6/7 → 7/1/5/3, an opposing pair → 0;
- that `STRIG` yields the BASIC truth values 0 / **−1**, not the BIOS byte.

**Runtime note (not a language fact).** C-BIOS's own `GTSTCK`/`GTTRIG` were read
from the C-BIOS **source** (BSD 2-clause; our runtime target, not the artifact
zerobas reimplements) only to confirm they are implemented rather than stubbed —
and that their keyboard direction table reproduces the measurement above. That
check is what makes the thin-wrapper implementation legitimate; the behaviour
asserted by the gate is the VG-8020's, never C-BIOS's.

**Own-design.** The dispatch-table `cpir` set test that replaced the per-token
compare chain, the domain check layered on the D-F2-2 `get_byte_arg`/`gb_illegal`
coercion already shipped, and the `A`-into-both-halves widening that turns
`GTTRIG`'s `$00`/`$FF` into 0/−1.

**Gate.** `make input-devices-acceptance` (31 cases): grammar/error surface,
idle values, and a live key-matrix phase that holds a matrix bit down across the
RUN — the only phase that can distinguish a real read from a constant 0, since
with nothing plugged the idle value *is* 0. Plus the crunch corpus (new
`STICK`/`STRIG` rows and `STEP`/`STOP`/`STR$` anti-collision rows).

## Space: `BEEP` → page-0 sub tenant (basic/sound.asm, sub/beep.asm, sub/sub.asm, sub/equates.inc, basic/sysvars.inc)

`BEEP`'s body moved to the sub-ROM to fund input-devices slice I1 — see
[docs/spec-basic-input-devices.md](../docs/spec-basic-input-devices.md) §7. Our
own code, relocated verbatim bar the tenant ABI (the leading cursor step and the
`exec_stmt` tail stay resident; the tenant just returns). The routine was already
repack-only, so the lean cart is byte-identical by construction. Clean-room: no
disassembly — this is a move of code we wrote. The `BEEP` language contract is
unchanged and still pinned by `make beep-acceptance` against the VG-8020.

## 2026-07-29 — the `IF ROM_BASE` gates and the lean 16 KB build are retired

Clean-room status: **unchanged, and nothing here is restated by this entry.**

Until this date the interpreter assembled two ways, selected by a `ROM_BASE`
symbol: `$2812` for the relocated slot-0 image that ships, and `$4000` for a
16 KB page-1-only "lean" cartridge that excluded seven source files. 284
`IF ROM_BASE` directives across `basic/` and `sub/` chose between them.

Step 3 of RETIRE THE LEAN 16 KB CART
([`docs/spec-lean-retire-s3-gates.md`](../docs/spec-lean-retire-s3-gates.md))
constant-folded every one of those gates at `ROM_BASE = $2812`, deleted the
symbol and the `basic/main-reloc.asm` wrapper, and renamed the surviving org
constant to `BASIC_ORG`. `basic/main.asm` is now the sole entry point.

**No byte moved.** `build/basic-reloc.rom`, `build/sub.rom`, `build/disk.rom` and
`build/zerobas-main-eu.rom` are byte-identical across the change; that identity
was the gate the edit was made under.

⚠️ **EARLIER ENTRIES IN THIS FILE ARE NOT REWRITTEN, DELIBERATELY.** Many of them
describe a routine's placement in terms of "lean cart: inline here / repack:
evicted there", or note that a change kept the lean image byte-frozen. Those
statements were true when written and are part of the record of how the code
reached its present shape — this file is a provenance log, not a description of
the current tree. Read any `ROM_BASE` / lean/repack framing in an entry dated
before today as historical. The source comments, by contrast, WERE swept, since
a comment describes the code it sits beside.

## 2026-07-31 — a blank inside a line number, and the ceiling behind it (D-LNBLANK)

Clean-room status: **unchanged.** Everything below is a black-box oracle
observation of two reference machines — identical inputs typed in, the stored
program's own bytes read back out of RAM. No disassembly, no reference-ROM
inspection. The token values used to read the captures (`$0E` line-number
reference, `$8F` REM, the branch keywords) were already pinned from the MSX2
Technical Handbook (Table 2.20 / Figure 2.12), an allowed source.

**Two oracles, not one.** Every row was asked of both `Philips_VG_8020` and
`National_CF-3300`. They agree on all 54 rows byte for byte, so the contract
below is recorded as **MSX-BASIC's**, not as one ROM's. The item had rested on a
single row from a single machine; the second oracle is what makes it safe to
implement rather than merely to copy.

Instrument: `("stored_line", TXTTAB)` — the exact bytes of the first stored line,
with the 2-byte link **never compared** (it is an absolute address, and the
CF-3300's Disk BASIC text base is not the VG-8020's $8001).

Contract established (measurement:
[`docs/lnblank-msx1-characterization.md`](../docs/lnblank-msx1-characterization.md),
spec [`docs/spec-basic-lnblank.md`](../docs/spec-basic-lnblank.md) §4):

* A blank inside a **decimal number** is transparent — in the leading line
  number, in a line-number reference after a branch keyword, and in an ordinary
  numeric literal. Any *run* is transparent, not just one blank.
* …but **not** inside a hex literal (`&H1 F` → `&H1`), a string literal, a REM
  tail, or a variable name.
* The leading line number consumes its digits plus exactly **one** blank —
  **none when its value is zero** (`00 REMX` eats none, `01 REMX` eats one).
* A line number past **65529** is refused: nothing stored, `Syntax error`
  printed, `PRINT ERR` reads **2**. 65529 is accepted and leaves ERR at 0.
* In a line-number reference, blanks *before* the number are copied verbatim and
  a blank *inside* it leaves no byte. A blank before an `ON…GOTO` comma does not
  end the list.
* `LIST` / `DELETE` / `AUTO` / `RENUM` / `ELSE` also take a `$0E` line-number
  reference (recorded; not implemented — see `TODO.md`).

Implemented in `parse_lineno` + `dl_store`
([`basic/program.asm`](program.asm)) and `bl_acc` + `bl_done`
([`basic/tokenise.inc`](tokenise.inc)) — **two copies of the same lookahead on
purpose**: the crunch body is evicted to the sub-ROM and `program.asm` stays in
the main ROM, so no call could be shared. 61 B, all page 1.

🔴 **A defect this fixed, recorded because the code's own comment had asserted the
opposite was harmless:** `parse_lineno`'s header used to say the accumulator
"wraps past 65535" and that line numbers above 65529 were "not guarded here".
Unguarded, `99999 REM` **silently stored a line numbered 34463** and reported
nothing. The bound is now checked, and — the part that matters — the overflow is
caught **during** accumulation rather than after it: a ceiling tested on the
finished value cannot see a number that already wrapped, and the first cut of the
fix duly let 99999 through.

## 2026-07-31 — a blank inside a decimal LITERAL, and the two things behind it (D-DECBLANK)

Clean-room status: **unchanged.** Everything below is a black-box oracle
observation of two reference machines — identical inputs typed in, the stored
program's own bytes read back out of RAM. No disassembly. The token values used
to read the captures (`$0F`/`$1C` integers, `$1D`/`$1F` single/double with a
bias-64 exponent and BCD mantissa, `$0B`/`$0C` octal/hex, `$84` DATA, `$8F` REM)
were already pinned from the MSX2 Technical Handbook, an allowed source.

**Two oracles, not one.** All 32 new rows were asked of both `Philips_VG_8020`
and `National_CF-3300`, `--repeat 2`, across four oracle-lock rounds, every
payload past the echo guard first. They agree on every row.

Instrument: `("stored_line", TXTTAB)`, link word never compared — as D-LNBLANK.

Contract established (measurement:
[`docs/decblank-msx1-characterization.md`](../docs/decblank-msx1-characterization.md),
spec [`docs/spec-basic-decblank.md`](../docs/spec-basic-decblank.md) §2):

* **The cursor a decimal-literal scan reports is one past the last character it
  actually CONSUMED.** Lookahead may cross any run of blanks; only consumption
  commits them.
* Consequently a blank run is transparent at every internal seam of the literal —
  between digits, before *and* after the decimal point, before the exponent
  marker, between the marker and its sign, between the sign and its digits,
  inside the exponent's own digit run (`1E 2 3` = 1E23), and before a `!`/`#`/`%`
  type suffix (`1 #` is a **double**).
* …and a run that merely **TRAILS** a number is left alone, **entirely**:
  `A=1 +2` keeps its blank and `A=1  +2` keeps both. ⚠️ This is where a decimal
  literal differs from the leading line number, which eats exactly one separator
  blank — so the two scanners do *not* share a rule, and only a row with a
  non-continuation past the blanks can tell them apart.
* The joined value flows through int/single/double classification normally
  (`3 2 7 6 7` is a two-byte integer; `3 2 7 6 8` is a single).
* It does not reach `&H`, `&O`, `&B` (which is not a radix on MSX1 at all —
  `A=&B1 1` is stored verbatim on both references), string literals, `REM` tails,
  `DATA` bodies or variable names.

Implemented as one blank-skipping fetch (`tkf_fetch`) used at five sites: the
mantissa digit runs, the decimal point, the exponent (marker/sign/digits) and the
type suffix in [`sub/tkfloat.asm`](../sub/tkfloat.asm), plus the `'.'`-led entry
in [`basic/tokenise.inc`](tokenise.inc). Each caller pushes the cursor first and
either discards it (accept) or restores it (reject) — the accept/reject split
*is* the contract above. **39 B, all sub-ROM page 0**; the main ROM came out
byte-identical.

⚠️ **The `'.'`-led entry is in a different file from the scanner, and a fix aimed
at `tk_float` cannot reach it.** `A=. 5` is 0.5 on both references; that decision
is taken in `tk_loop`'s dispatch before `tk_float` is entered.

🔴 **Two live defects were found by this slice's denominator and are NOT fixed
here**, both pinned in `make lnblank-acceptance`'s `KNOWN_DIVERGE` at their exact
current bytes so the gate reddens the day either is addressed:

* **D-EXPBAD** — a *malformed* exponent. Both references CONSUME a marker (and
  its sign) that turns out not to introduce an exponent and force the literal to
  **single** precision: `A=1EX` stores a single 1.0 then `X`, where zerobas
  stores the integer 1 then `EX`. Measured with **no blank anywhere**, which is
  what makes it a separate defect. zerobas' rollback is own-design and was never
  oracle-pinned.
* **`&B`** — zerobas crunches the digit run after an unrecognised `&B` to a
  token; both references keep the whole tail as ASCII.

A third cell is recorded as **not measurable** with the present instrument: a
trailing blank at end of line. The references drop it and zerobas keeps it, in a
verbatim `REM` tail as well as after a literal — which places the difference at
line ENTRY rather than in any scanner — but the echo guard `rstrip`s every screen
row and so is structurally blind to a trailing blank, and the row has not read
the same way on every pass. Reported, filed, never gated.

## 2026-07-31 — a MALFORMED exponent marker (D-EXPBAD)

Clean-room status: **unchanged.** Black-box oracle observation of two reference
machines — identical inputs typed in, the stored program's own bytes read back
out of RAM. No disassembly. Token values as in the D-DECBLANK entry above.

**Two oracles.** All 18 rows asked of both `Philips_VG_8020` and
`National_CF-3300`, `--repeat 2`, two oracle-lock rounds, every payload past the
echo guard first. They agree on every row, and every row was locked **before**
zerobas was run on it.

Contract established (measurement:
[`docs/expbad-msx1-characterization.md`](../docs/expbad-msx1-characterization.md),
spec [`docs/spec-basic-expbad.md`](../docs/spec-basic-expbad.md) §2):

* **The exponent's digits are OPTIONAL.** The grammar is `[EeDd] [+-]? digit*`,
  not `…digit+`: a marker at the exponent position is consumed with any
  immediately following sign, whether or not a digit follows, and there is **no
  rollback**. `1E` stores a single 1.0 with the marker gone; `1E+` eats the sign
  too.
* **The marker's PRECISION survives the failure**: `1D` is a **double**, `1E` a
  single (the digit count decides).
* **A consumed marker forces the literal off the INTEGER path**: `12345EX` is a
  single even though 12345 is int-eligible (D=5, ≤32767).
* **The type-suffix scan is skipped**, exactly as for a well-formed exponent
  (the `1e10#` quirk already recorded): `1E#` is a single followed by a raw `#`,
  `1E%` likewise — and `%` normally forces integer.
* The exponent **value is zero** when no digits follow, and a lowercase `e`/`d`
  counts as a marker.
* Consumption obeys D-DECBLANK's cursor rule unchanged: a blank run *before* a
  consumed character goes with it (`1E -X` loses its blank), one *behind* the
  last consumed character stays (`1E X`, `1E- X` keep theirs).
* It does **not** reach `branch_lineno`'s line-number scan (`GOTO 1EX` keeps
  `EX` on both references) or a `DATA` body.

Implemented by **deleting** the rollback in `tkf_try_exponent`
([`sub/tkfloat.asm`](../sub/tkfloat.asm)): `tke_fail` and the two digit-range
tests are gone and the commit is unconditional. The sign lookahead gained the
same push/accept/reject shape D-DECBLANK gave every other fetch, and the
exponent's digit fetch is left to `tke_dloop`, which already push/pops
correctly. **NET −8 B, all sub-ROM page 0**; the main ROM came out
byte-identical.

⚠️ **The blank seam is a cell the fix itself created.** While the marker was
never consumed, `1E X` could not distinguish "the marker was consumed and the
blank was not" from anything else. Committing where the code stood — after the
blank-skipping fetch — satisfies every row the defect was filed with and eats
that blank silently; two rows measured for this slice are the only objection.

🔴 **The defect was recorded here in its own header as own-design and never
oracle-pinned.** That is the class of claim worth re-asking: the routine had
implemented a "at least one digit" rule the language does not have, and the
correction removed code rather than adding it.

With this slice `make lnblank-acceptance`'s `KNOWN_DIVERGE` allowlist is
**EMPTY**: both cohorts filed in it (D-LNBLANK's five `lit-` rows, D-DECBLANK's
four `dec-expbad*` rows) were retired by the slice that fixed them, each closed
by the allowlist reporting the row as agreeing.

## 2026-08-01 — a blank does not break a variable NAME (D-NAMBLANK)

`basic/tokenise.inc` — **+12 B, all sub-ROM page 0** (free 4026 → 4014 B); both
main ROMs came out **byte-identical** to the pre-slice tree. Spec
`docs/spec-basic-nameblank.md`, measurement
`docs/nameblank-msx1-characterization.md`, gate `make lnblank-acceptance`
(**125/125 at `--repeat 2`**, three sides).

Filed as *"`&B` is not a radix on MSX1 — and zerobas half-crunches it anyway"*.

🔴 **The `&` was a red herring, and a row proves it positively rather than by
argument.** `20 A=&1` reads `A<EF>&<12>` on the VG-8020 and the CF-3300 both — a
digit directly behind the `&` is crunched *there* too, so `&` is inert on every
side. The filed row's content is the text `B1 1`, in which `B1` is an ordinary
variable name. Ten rows carrying no `&` at all diverge identically.

**R-N1: a blank is COPIED but changes no tokeniser state.** The in-a-name flag
survives a run of blanks, so a digit behind the blank continues the name: `B1 1`
is the identifier `B11`, and `20 B1 1=7` is readable back through `B11` (` 7 ` on
both references, ` 0 ` on zerobas before this slice). `tk_loop` reloaded `TKNAME`
into `B` and zeroed it every character; a blank reached `tk_copy`, which never set
it again. The fix intercepts the blank ahead of `match_kw` — where `B` is still
live — and puts the flag back.

⚠️ **`dec-oct` had been arguing for R-N1 since D-DECBLANK and nobody read it that
way.** `20 A=&O1 7` crunches its `7` on the references too, because an octal
*token* is not a name. Same shape as the filed row, opposite reading; the only
difference between them is whether a NAME preceded the blank. A row that AGREES
carried the answer to a row that diverged.

🔴 **The defect was bigger than one byte, and exactly one row shows it.**
`20 A=B 1 0`: the reference stores the identifier `B10` verbatim, zerobas stored
`B`, a blank and **the single literal 10** — having lost the name it handed the
run to the decimal scanner, which then correctly applied D-DECBLANK's own
blank-transparency and joined the digits. Two rules compounding. Every other
divergent row has a single digit behind the blank, where the two are
indistinguishable, so sampling `B1 1` alone would have got the slice's own size
wrong.

🔴 **A KNIFE FOUND A LIVE DEFECT IN THIS SLICE'S FIRST CUT, and the flawed build
was 29/31 GREEN.** `tk_copy` is the fallthrough target of the `is_letter` test, so
`tk_blank` parked immediately before it put **every punctuation character** through
a store of `B` — a register `match_kw` uses as its own compare counter and had
long since clobbered. The build read green on whatever value happened to be left
there: clean *by luck*. K2 (`ld a,b` → `ld a,1`) made it unmissable via
`20 A=B$1`, **a row with no blank in it at all**, and `tk_blank` moved past
`tk_copy_up`. That is this spec's §4.3 liveness claim violated by the code §4.3
describes — the knife aimed at the justification hit it.

⚠️ **The battery could not have caught it.** Every row written before the knife
reached `tk_copy` through a blank, an operator or a type suffix; none put ordinary
punctuation between a name and a digit. `nam-paren` / `nam-parenblk` were added
because of K2 and oracle-locked on both references before zerobas was run on them.

K4 was **predicted GREEN** and first reported `nam-parenblk` as `REFUSED (empty
program)`. Run alone at `--repeat 2` on the same build it agrees — a dropped
keystroke, which openMSX being deterministic would have reproduced on every re-run
of that batch. The justification survives: routing a blank back through the full
`match_kw`/operator chain changes no row.

**Filed, not fixed:** `.` is an identifier character on MSX1 (`20 A=B.5` diverges
with **no blank at all**), now two pinned `KNOWN_DIVERGE` entries — so that
allowlist is non-empty again, deliberately. Folding it in would have needed the
RUN-time variable-name scan too, not just the tokeniser.

> ✅ Landed the next day as **D-NAMDOT** (section below). 🔴 The last sentence is
> **wrong**: MSX1's executor does *not* accept `.`, the fix was tokeniser-only
> and sub-ROM only, and making `vars.asm` accept `.` was run as a knife and
> shipped a divergence. Left in place — the prediction is worth re-reading next
> to what refuted it.

## 2026-08-01 — the `CALL` device-name scan is a RANGE test (D-CNAME)

Spec [`docs/spec-basic-cname.md`](../docs/spec-basic-cname.md), measurement
[`docs/cname-msx1-characterization.md`](../docs/cname-msx1-characterization.md).
Filed by D-LNLIST from three rows that were all written to ask a *different*
question and had their digit eaten before they could ask it. 56 rows
oracle-locked on the **VG-8020 and the CF-3300**, which agree, `--repeat 2`, past
the echo guard, before zerobas was run on any of them.

Three rules, all landing in one loop of [`tokenise.inc`](tokenise.inc):

* **R-C1** — the scan ends at **end of line**, `:` (`$3A`) or `(` (`$28`), and at
  nothing else. The terminator is left for the ordinary crunch, which is why
  `20 CALL X(5)` stores the `(` and crunches its 5 to `<16>`, and why
  `20 CALL X:PRINT 5` has a second statement at all.
* **R-C2** — a character in **`$21`..`$2F`** is **discarded** and the scan
  continues past it. Fourteen characters (`(` is R-C1's), walked contiguously.
* **R-C3** — everything else is **stored**: `a`..`z` upcased, the rest verbatim,
  **including the blank**. No keyword crunch, no numeric crunch, no length bound.

🔴 **THE FILED FRAMING WAS RIGHT ABOUT THE DIRECTION AND WRONG ABOUT THE RULE,
IN BOTH DIRECTIONS.** *"The scan stops short — the reference reaches further"* is
true, and the rule it suggests — copy identifier characters and blanks, drop
everything else — is refuted: `; < = > ? @ [ \ ] ^ _ ` ~` are **kept** verbatim
and the scan runs on past them. The narrow reading, *only the `+` is swallowed*,
is refuted the other way: thirteen more characters are dropped.

🔴 **AND THE OPERATORS LAND ON BOTH SIDES.** `+ - * /` are dropped; `^ \ = < >`
are kept. Nine operators split down the middle, so neither operator-ness nor the
token byte separates them — the same interleaving shape D-LNLIST hit, where `\`
(`$FC`) kept the mode and `MOD` (`$FB`) cleared it. What separates them is the
**ASCII range**, and only a contiguous walk could show it. All fifteen characters
of `$21..$2F` and every deliverable printable character at or above `$3B` were
read, so **both classes are denominators, not samples**. The three rows that
filed this defect each agree with two different wrong rules.

🔴 **THE FIX DELETES A SUB-ROM ROUTINE, AND THE DEAD-CODE GATE FORCED IT.**
[`vars.asm`](vars.asm) is **not** included by `sub/sub.asm`, so `tcn_name`'s
`call is_ident_cont` was the only caller of the sub-local clone anywhere
sub-side. Replacing it with the range test orphaned 16 bytes and
`make basic-reloc`'s hard dead-code gate failed the build rather than shipping
them. Knife **K6** turns that argument into a measurement: it restores the clone
with no caller and the **build** goes red, naming `is_ident_cont` and `siic_no`
dead. `is_letter` survives the same edit (`tk_notkw` still calls it), and this
file's own `is_ident_cont` keeps all three of its callers and is untouched.

**NET −10 B** (+6 for the loop, −16 for the clone), **all sub-ROM page 0**
(3998 → 4008 B free); both main ROMs **byte-identical**, asserted by hash.
`lnblank-acceptance` **251/251** at `--repeat 2`, up from 195/195 — exactly the
56 new rows — and `KNOWN_DIVERGE` is now **EMPTY**, the fifth cohort to retire
from it and not one has rotted.

⚠️ **THE MACHINE DOES NOT SURVIVE A MISSING END-OF-LINE TEST.** `$00` is below
`'0'`, so without the leading `or a` it takes R-C2's discard path and the cursor
runs past the line terminator. Knife **K7** defeats exactly that test: batched,
*every* zerobas row came back `NOCAPTURE`, which is not a reading at all — a hung
machine and a broken harness are the same value. Run on isolated single rows it
separates, and that is the measurement: `20 CALL X(5)` still reads correctly
while `20 CALL X` is `NOCAPTURE`, so the corruption is **per payload**.

⚠️ **Three apparatus findings, each caught by a guard rather than by luck.**
`{` `|` `}` are not deliverable through this harness — and the `}` row returned a
stable, both-references-agreeing `<CA> X{5}` from a payload containing neither
brace, a perfect fake that only the echo guard killed. The echo guard's payload
ceiling is the display width, because it matches whole screen rows. And
`cnm-lower` mangles **intermittently in a batch**, which `--repeat` cannot catch:
openMSX is deterministic, so a harness race reproduces identically across boots.

## 2026-08-01 — `.` is an identifier character to the TOKENISER (D-NAMDOT)

Spec [`docs/spec-basic-namedot.md`](../docs/spec-basic-namedot.md), measurement
[`docs/namedot-msx1-characterization.md`](../docs/namedot-msx1-characterization.md).
Split out of D-NAMBLANK, which filed it from two rows. 23 rows oracle-locked on
the **VG-8020 and the CF-3300**, which agree, `--repeat 2`, past the echo guard.

Two rules, both landing in one five-line dispatch arm of
[`tokenise.inc`](tokenise.inc):

* **R-D1** — a `.` arriving with the in-a-name state LIVE **continues the
  identifier**: copied verbatim, state survives, exactly as a digit does. `B.5`
  is the identifier `B.5`; `B .5` is the same one across a blank (R-N1).
* **R-D2** — a `.` with the state DEAD begins a numeric constant **and the digit
  is OPTIONAL**. A bare `.` is the single-precision literal 0
  (`$1D,00,00,00,00`), including at end of line and straight into an exponent
  marker (`20 A=.`, `20 A=.E5`).

The one-character lookahead that used to stand there is **deleted** — R-D2 says
there was nothing to look ahead for, and R-D1 says the question was about the
name state. `tk_namedig` is reused rather than cloned. **NET −10 B, all sub-ROM
page 0** (4014 → 4024 B free); both main ROMs came out **byte-identical**,
asserted by hash.

🔴 **THE FILED PRESCRIPTION WAS REFUTED, AND THAT IS THE FINDING.** D-NAMBLANK,
`TODO.md` and this file all recorded that a crunch storing `B.5` as name bytes
*requires* the RUN-time scan ([`vars.asm`](vars.asm) `is_ident_cont`) to accept
`.` too. **MSX1 does the forbidden thing**: it stores name bytes it then refuses
to resolve. `B.5=7` and `A=B.5` are `Syntax error` (ERR=2) on both references,
against a `B5=7` control at ERR=0 — PRINT emits `B`'s value and chokes on the
leftover `.5`. The tokeniser's identifier charset and the executor's are
**different charsets**, and reproducing that is the charter. Knife **K4** made
the prescribed `vars.asm` change and drove those rows ERR 2 → 0: the filed fix
would have shipped a live divergence in the exact place the item pointed at, and
cost 4 B of a main page-1 wall with 8 B on it. `DEFINT`/`DEFSNG`/`DEFSTR`,
`VARPTR`, `FOR` variables, `DIM`/array names and `INPUT`/`READ` targets are all
untouched *because they reach that one unchanged scanner*.

🔴 **R-D2 WAS FOUND BY ROWS WRITTEN TO BE CONTROLS.** `20 A=.B` and `20 .A=1`
were filed as predicted-green two-sided cells and both refuted their own
prediction. Correcting them in place turned *"a `.`+digit leads a literal"* into
*"a `.` leads a literal"* — and made the fix a **deletion**, the D-EXPBAD shape.

🔴 **A `<none>` READING ON BOTH REFERENCES IS NOT AGREEMENT.** The first `dotd`
payloads printed no closing `]` **because the behaviour under test aborted the
statement**, so every side read `<none>` and compared EQUAL. Reading the SCREEN
found the `Syntax error`; the rows were re-asked through `ERR`, which prints its
brackets whether or not the statement aborts. Same class as the `--say`-without-
brackets item filed one slice earlier.

Five knives, all run and reverted. K1/K2 separate R-D1 from R-D2; **K3**
(`ld a,b` → `ld a,1`) separates R-D1 from *"a `.` is always an identifier
char"* — a distinction **neither filed row could make**, and the reason the
bounding rows `dot-sfx`/`dot-paren`/`dot-kw` exist; K4 above; K5
(`tk_namedig`'s `ld a,1` → `ld a,0`) shows the dot must **set** the state, with
`dot-two` (`B..5`) the row that says so.

⚠️ **K1 and K5 each reddened a row predicted GREEN, and both corrections stand.**
A cell that is a two-sided control between the two *candidate* rules can still
move under a knife, because **a knife is a third rule**: `20 A=B.` reads `B.`
under the old rule (a digitless dot is copied) *and* under R-D1 (it is a name
char), for opposite reasons — K1 is neither. And a K1 `REFUSED (empty program)`
on `dot-eol`, a row K1 does not touch, re-ran clean **alone at `--repeat 2`** on
the same build: a dropped keystroke, which a deterministic emulator reproduces
exactly.

`nam-dot`/`nam-dot0` **retired** from `KNOWN_DIVERGE` — the third cohort to leave
that allowlist by going red rather than by rotting.

**Filed, not fixed:** `20 GOTO 1.5` — the reference emits `$0E,0001`, copies the
`.` verbatim and then emits a **SECOND** `$0E`. That is `branch_lineno`'s list
continuation, **different code**, and the evidence it is independent is that this
fix did not move the row. One pinned `KNOWN_DIVERGE` entry, `dot-goto`.

## 2026-08-07 — a `READ` target is a VARIABLE REFERENCE, and a DATA item is not trimmed at the end (D-READVAR)

Spec [`docs/spec-basic-readvar.md`](../docs/spec-basic-readvar.md), measurement
[`docs/readvar-msx1-characterization.md`](../docs/readvar-msx1-characterization.md),
gate `make readvar-acceptance`. **24 rows on three sides — `Philips_VG_8020`,
`National_CF-3300` and the repack — and both references agree on all 24**, so
every row has an oracle and the reference column IS the specification. Clean-room:
observed screen output only; both reference ROMs are black boxes.

The residual this closes was filed as *"zerobas has no string `READ`"*. It is one
face of five: [`ex_read`](program.asm) consumed **one letter** and stored through
`var_get`/`var_set`, the single-letter int16 shim in [`vars.asm`](vars.asm), while
every other variable reference in the tree goes through `var_name_key`.

**Three row classes, newly sourced, each stated as the references answer it:**

* **A — the target grammar.** A `READ` target is *any* variable reference:
  1- or 2-character names, a letter+digit name, each of `%` `!` `#` `$`, and the
  DEFtbl default when there is no suffix — exactly what `LET` and `INPUT` accept.
  `DATA 7` / `READ AB` / `READ A%` / `READ A1` all read ` 7 `; `DATA HELLO` /
  `READ A$` reads `HELLO`; `DEFSTR Z` / `READ Z` reads `HELLO`. Sourced from both
  references, 10 rows. ⚠️ `READ A(1)` is **also** accepted on both references
  (` 7 `) and is **NOT implemented here** — deferred with its measurement, see
  below.
* **B — how a DATA item lexes into a string.** 🔴 **This surface was INVISIBLE to
  this tree until a string target existed at all** — an int16 parse cannot tell
  `DATA HELLO` from `DATA "HELLO"` from `DATA HI THERE` — so these 11 rows are
  characterization of something never before read here, not a regression check.
  The rule, stated from the rows: **skip leading spaces, then take bytes verbatim
  to the next comma or the end of the statement; a leading `"` delimits instead
  and the closing `"` ends it, so a comma inside quotes is content; NOTHING is
  trimmed from the end.** `DATA 42` into `A$` answers `42`, not ` 42 ` — the
  missing `PRINT` spaces are the tell that the value is a string. `DATA ,X` reads
  the empty string.
  🔴 **`DATA PAD  ,X` reads back `'PAD  '`, two trailing spaces intact.** The
  symmetric rule — trim both ends, since the leading spaces plainly are trimmed —
  is the obvious one, and it is **wrong on both references**. It was measured only
  because the denominator was re-examined for what it had not asked; no numeric row
  could ever have caught it, and knife K-RV4 builds the symmetric rule and reddens
  `b.trailsp` alone.
* **C — the reverse cross.** `DATA HELLO` / `READ A` is a **`Syntax error`** on
  both references. 🔴 **This is the one divergence that pointed the OTHER way:**
  every other row was zerobas refusing what the references accept, while here
  zerobas *accepted* what they refuse — `data_parse_int` parsed no digits, yielded
  0 and stored it silently. Sourced as an error, and implemented in the DATA
  engine (a third return status), not in the target parse.

**Own design, not sourced** — the shapes these rules are implemented *in*:

| | |
|---|---|
| `RDV_MODE` ($E554), the main→tenant item-mode cell, and `RDV_ST`'s third value | own choice — the READ/DATA engine is a page-0 sub-ROM tenant here (a zerobas-specific eviction), so its ABI is ours |
| the sub/main split — the tenant FILLS `STRSCR`, `ex_read` wraps it with `strscr_desc` and stores with `str_set_key` | **forced**, not chosen: `strscr_desc` ($2896) is in the main LOW region, switched OUT while the sub-ROM's page 0 is in. Same split `ex_input` already carries |
| the "trailing junk ⇒ not a number" test (`,` or end-of-line, nothing else) | own rule for a sourced *behaviour*. The reference's internal test is unobserved; what is measured is that `DATA HELLO` / `READ A` is ERR 2. A `:` arm is unnecessary rather than omitted — `tk_data_rest` ([`tokenise.inc`](tokenise.inc)) ends a `DATA` body **at** a `:`, so a stored body never contains one |

**Deferred with its evidence, not silently dropped:** `READ A(1)` / `READ A$(1)`
(`a.ary` / `a.arystr`) need `ex_let`'s array lvalue path (`ary_op0_resolve` /
`ary_store_write`, [`arrays.asm`](arrays.asm)) and are outside the `INPUT` twin
this slice was priced against — [`input.asm`](input.asm) has **no array handling
whatsoever**. Both rows stay measured and printed by the probe, marked `....` with
their reason, and are excluded from the gate's tally in **both** directions: a row
that can only ever be red is doc debt, not a gate. Re-filed in `TODO.md`.

## 2026-08-11 — a graphics statement gates the SCREEN mode AFTER its mandatory arguments (D-LINERR)

Spec [`docs/spec-basic-lineerr.md`](../docs/spec-basic-lineerr.md), measurement
[`docs/lineerr-msx1-characterization.md`](../docs/lineerr-msx1-characterization.md),
gate `make lineerr-acceptance`. **108 rows on three sides — `Philips_VG_8020`,
`National_CF-3300` and the repack — 106 scored and both references agreeing on
every one of them** (2 deferred, §SCREEN 3 below), so every scored row has an
oracle and the reference column IS the specification. Clean-room: observed screen
output and published MSX system-variable reads only; both reference ROMs are
black boxes.

**The rule, newly sourced:** *a graphics statement moves the WORK AREA to the
point its MANDATORY arguments resolve to, and refuses a wrong SCREEN mode
IMMEDIATELY AFTER THAT — after every fault the mandatory arguments can raise, and
BEFORE the first OPTIONAL argument is looked at.* Sourced from both references at
`PSET`, `PRESET`, `LINE`, `CIRCLE` and `PAINT`, each sited by a **pair** of rows
that bracket the gate from both directions (a mandatory argument's fault wins, an
optional one's does not), and independently by the work-area reading over a
`PSET(7,4)` seed. `DRAW` already agreed; `POINT` has no gate by construction and
is the control that says the class is about the PRECHECK and not about "graphics
in SCREEN 0" generally.

**Two corollaries, also sourced from both references:**

* a `LINE`/`PSET` colour is a **0..15 range check → ERR 5**, the rule `CIRCLE`
  and `PAINT` already carried — `PSET(20,21),16` is `Illegal function call` on
  both references. An out-of-int16 colour is ERR 6 from the coercion first.
* a `LINE` argument list that **ENDS where the COLOUR was required is `Missing
  operand` (ERR 24)**, at end-of-line and at a `:` alike — D-SCRERR's rule at a
  second verb. ⚠️ It does **not** extend one field along: at the box slot the
  identical two shapes are ERR 2. The `:` arm was therefore MEASURED here, not
  copied from `ex_screen`'s shape; a guard written by analogy would have made all
  four ERR 24 and been half wrong with no row to say so.

🔴 **THE FILED DIAGNOSIS WAS WRONG AND THE FILE REFUTED IT.** `TODO.md` and the
deferring probe both recorded *"LINE raises its own `Illegal function call`
eagerly from inside its coordinate parse"*. There is no ERR 5 anywhere in
`parse_coord`; the refusal was `ex_line_gfx`'s own opening `cp 2`, three
instructions in, and the row runs in the boot default SCREEN 0. Recorded because
the wrong diagnosis named the wrong SHAPE of fix — a per-driver patch — where the
answer is one shared leaf at five verbs.

🔴 **AND IT BECAME A FIVE-VERB RULE BECAUSE A NEGATIVE CONTROL DIVERGED.**
`n.pset0` was written as *"the wrong-mode rule at a DIFFERENT verb, which this
slice claims nothing about"* and diverged identically. A fix at LINE alone would
have shipped a partial rule under a green gate.

**Own design, not sourced** — the shapes these rules are implemented *in*:

| | |
|---|---|
| `gfx_point_gate` / `gfx_mode_gate` / `gfx_work_area`, three nesting entry points into 29 B beside `gfx_err5`, preserving `BC`/`DE`/`HL` and clobbering only `A` | own choice. The BEHAVIOUR is measured at five verbs; that the five share one leaf is ours. The register contract is forced by the callers: each still holds the token cursor in `HL`, and `gfx_plot_stmt` still needs the point in `BC`/`DE` for its own range test |
| `ex_circle` gates on **every** int request rather than only the radius | own rule for a sourced behaviour. Gating twice is the same as gating once — the second test can only pass — and it buys the measured ordering without a "which argument am I on" flag in the coroutine's resume state. `v.circ0.rt` is the row that forces the gate below the radius at all |
| the ERR-24 guard's `:` arm at the colour slot, and its ABSENCE at the box slot | both MEASURED (`a.trailcolon` → 24, `a.boxcolon` → 2), not chosen |
| `ex_line_gfx`'s p2 work-area write duplicating the tenant's own (`sub/graphics.asm` `gfx_line_op`) | deliberate, not dead. The CIRCLE spokes call that op internally and rely on its write; knife K-LE3's green `w.s2` is the row that shows a LINE which DRAWS takes its work area from the tenant |

⚠️ **SUPERSEDED BY THIS SLICE, kept as pointers rather than deleted** (`bf0dab5`:
a retired claim that simply vanishes is invisible on the next grep):
[`docs/spec-basic-graphics-g5.md`](../docs/spec-basic-graphics-g5.md) §6's
`ex_paint` order (**both** ends wrong — the gate was not first and the work-area
write was not last), and the word *"precheck"* in
[`docs/spec-basic-graphics-g2.md`](../docs/spec-basic-graphics-g2.md) §4's
SCREEN 0/1 bullet (the test is right, its position was not).

🔴 **AND ONE SUPERSEDED CLAIM TURNED OUT NEVER TO HAVE EXISTED.** The `and $0F`
colour mask shipped with the comment *"see G2 gate note"* — there is no such
note — and by its second reader that dangling pointer had been restated as
*"documented as a silent mask, **measured on the VG-8020**
(spec-basic-graphics-g2.md §11.9)"*. `spec-basic-graphics-g2.md` has no §11.9; it
has no §11 at all. Nothing mechanical could catch this: a dangling `§11.9` is not
a forbidden source, so `make audit-citations` is silent on it, and no gate ever
asked what `PSET(20,21),16` does. The domain is now stated where it belongs, with
its rows, as `spec-basic-graphics-g2.md` §3.5. **A citation that does not resolve
gets UPGRADED on the way to its second reader.**

**Deferred with its evidence, not silently dropped:** `m.s3` / `v.pset3` —
SCREEN 3 **draws** on both references where zerobas raises ERR 5. A whole-feature
gap (a second rasteriser and a second address/clash model), not an error-surface
defect: this slice moved *where* the refusal happens, and the refusal itself is
correct for every mode zerobas implements. Both rows stay measured, printed
`....`, and excluded from the gate's tally in **both** directions. Re-filed in
`TODO.md`, with PAINT's two unordered ERR 5s and DRAW.

## 2026-08-11 — `DRAW` gates the mode BEFORE its argument, and two whitespace defects (D-DRAWERR)

Spec [`docs/spec-basic-lineerr.md`](../docs/spec-basic-lineerr.md) §11,
measurement
[`docs/lineerr-msx1-characterization.md`](../docs/lineerr-msx1-characterization.md)
§10, gate `make lineerr-acceptance`. **189 rows on the same three sides, 187
scored and both references agreeing on every one** (4 deferred — SCREEN 3, and
the DRAW scale default below). Clean-room: observed screen output and published
MSX system-variable reads only; both reference ROMs are black boxes. The `DRAW`
*language* remains the public MSX-BASIC language reference, every behavioural
rule our own black-box measurement, no disassembly.

**The rule, newly sourced, and it is a NEGATIVE result:** *`DRAW` refuses a wrong
SCREEN mode BEFORE evaluating its string expression.* `DRAW 5` is **ERR 5** in
SCREEN 0/1 and **ERR 13** in SCREEN 2, on both references — the opposite order to
the five verbs D-LINERR sourced above, which is why the count there is five and
not six. Sourced from six rows carrying every fault the argument can raise (a
numeric literal, both type-mismatch sites, and deferred 11/6 through `STR$`),
against the SCREEN-2 control that says the ERR 13 exists at all.

🔴 **The row DRAW had been excluded on could not see the question.** `v.draw0`
is `DRAW"U10"` — a string LITERAL, whose evaluation raises nothing — so it reads
ERR 5 whichever side of `str_eval` the gate is on. It does pin one thing nobody
had stated: the gate sits above the tenant's walk, since a walk in SCREEN 0 would
have moved the work area.

**Routines touched, and neither had a provenance row before:**

* `ex_draw` (`basic/graphics.asm`) — gained `call skip_spaces` before
  `str_eval`. Without it `str_eval` was handed HL on the space after the token
  and returned "not a string operand", so **`DRAW A$` was `Type mismatch`** and
  `DRAW` accepted a string *literal* and nothing else. `ex_let_str` and
  `spr_assign` both already skipped, which is why the `SPRITE$(n)=` sibling row
  `n.sprdz` never diverged. **+3 B, page 1.**
* `gdrw_peek` (`sub/graphics.asm`) — now skips spaces and TABs itself, and
  `gdrw_skipws` is an `equ` onto it. The old arrangement called `gdrw_skipws`
  at four sites, all *between commands*, while the block header claimed
  whitespace was "ignorable anywhere". `DRAW"R1 0"` is `R10` on both references,
  so the rule is **skip before every character fetch**. `gdrw_peek_raw`
  deliberately still does not skip: `gdrw_sub_scan` walks `=var;` text with it
  and those spaces are DATA. **−3 B, sub page 0** (the 16-byte `gdrw_skipws`
  body is gone).

**Deferred with its evidence, not silently dropped:** `d.lit2` / `d.def32k` —
the boot-default DRAW **scale** state is not `S4`. Both references move the full
count from boot and wrap only after an explicit `S`; zerobas initialises
`GFX_DSCALE = 4` and wraps from boot. `scratchpad/g6_draw_notes.md` §3's model is
correct and its generalisation is not — all twelve points it was fitted and
falsified on set `S` first, and the multiply is the identity everywhere except
the wrap, so a large count is the only observable that separates the two states.
Out of this slice's reach (it changes what DRAW *draws*, and "never set" needs a
sentinel `S4` cannot collide with); both rows stay measured, printed `....`,
excluded from the tally in **both** directions, and filed in `TODO.md`.
[`docs/spec-basic-graphics-g6.md`](../docs/spec-basic-graphics-g6.md) §4's
*"resets them, to `S = 4`"* and §5's two error rows are corrected in place with
SUPERSEDED pointers rather than deleted.

## 2026-08-11 — `DRAW`'s scale state has THREE values, and `$8000` is positive (D-DSCALE)

Spec [`docs/spec-basic-lineerr.md`](../docs/spec-basic-lineerr.md) §12,
measurement
[`docs/lineerr-msx1-characterization.md`](../docs/lineerr-msx1-characterization.md)
§11, gate `make lineerr-acceptance`. **210 rows on the same three sides, 208
scored and both references agreeing on every one** (2 deferred — SCREEN 3 only;
the previous entry's two scale rows are **undeferred here and green**).
Clean-room: observed screen output and published MSX system-variable reads only;
both reference ROMs are black boxes. The `DRAW` *language* remains the public
MSX-BASIC language reference, every behavioural rule our own black-box
measurement, no disassembly.

**The rule, newly sourced:** *`DRAW`'s scale state has three values — never-set,
explicit `S4`, and explicit `Sn`.* From boot neither the multiply nor the divide
runs, so both references move the FULL count (`DRAW"BU40000"` → 40000); after
any explicit `S`, including `S4` and `S0`, the count wraps (`DRAW"S4BU40000"` →
7232). **Nothing else arms it:** `DRAW"A0BU32767"`, `DRAW"C1BU32767"` and
`DRAW"BU32767S4"` all still move the full count, and `DRAW"S4":DRAW"BU32767"`
wraps — so the arming is an already-executed `S`, it persists into the next
statement, and the cells are independent.

**`GFX_DANGLE` was asked the same question and needs no sentinel — measured, not
assumed.** The angle has no wrap of its own (domain a checked `0..3`,
rotate-by-zero the identity), so `d.a0.32k` borrows the scale's wrap as its
readout. Both branches of the design fork were written down and priced before
the run; the rows chose the cheap one.

**Routines touched:**

* `init`'s cold-boot G6 hook (`basic/interp.asm`) — `ld a,4` deleted, so
  `GFX_DSCALE` starts at the **never-set sentinel 0**. 0 is a usable sentinel
  only because `gdo_s` maps `S0` to 4 (measured against a pre-set `S8` *and*
  `S2`), so no explicit `S` can ever store it. **−2 B, page 1.**
* `gdrw_scale` (`sub/graphics.asm`) — the `jr z` arm marked *"S=0 cannot reach
  here"* becomes `ret z`, passing `GFX_DARG` through untouched. The old arm fell
  into the divide with `HL = 0`, which returns a distance of 0, not "no
  scaling". **−1 B.**
* `gdrw_sc_neg` (`sub/graphics.asm`) — after the magnitude negation, `bit 7,h`
  still set can only mean the product was `$8000`, which takes the positive
  shift path. **+4 B.**

**Net −2 B page 1, +3 B sub page 0.** Walls: low **14 B**, page 1 **73 B**, sub
p0 **3604 B**, sub p1 **1483 B**.

🔴 **A SECOND DEFECT, FOUND BY A ROW WRITTEN AS A CONTROL — the previous entry's
shape, again.** `d.s4.8k` (`DRAW"S4BU8192"`) was the green control saying the
divergence was about the *state* and not about large counts. It diverged: the
16-bit product `$8000` is **+32768** on both references and −32768 in
`gdrw_scale`, so the sign boundary is `$8001`. `$8000` is the one 16-bit value
that is its own two's-complement negation. Pinned at five `(n,S)` pairs reaching
the same product (`S2U16384`, `S8U4096`, `S1U32768`, `S4U24576`, `S4U-8192`)
with `$7FFC` and `$8004` as the neighbours that make it a boundary.

🔴 **And the row designed as the sharpest discriminator reads nothing.**
`d.def8k` (`DRAW"BU8192"`) was written as *"the smallest count that separates the
two scale states"*; at a **correct** `S4` the two states coincide there, because
the product is exactly `$8000`. The minimal discriminator is **8193**. Its three
predicted values were right and its stated justification was wrong.

🔴 **And `d.defneg` (`DRAW"BU-8192"`) is green on the UNFIXED tree, for the
wrong reason** — the two defects cancel exactly there. Only a knife reinstating
one of them makes it move, which K-DS1 does.

`scratchpad/g6_draw_notes.md` §2's *"a fresh boot measures S=4"* and §3's model,
and [`docs/spec-basic-graphics-g6.md`](../docs/spec-basic-graphics-g6.md) §3/§4,
are corrected in place with pointers rather than deleted: nineteen readings
fitted and falsified that model and not one of them was at `$8000` or at the
boot default.
