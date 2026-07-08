<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Disk-BASIC & BDOS option-surface audit

**What this is.** A standing sweep of *every* Disk-BASIC verb and BDOS function against
its documented option/parameter surface, to answer one question the per-verb scoreboard
([diskbasic-verb-coverage.md](diskbasic-verb-coverage.md)) does **not**: *for each verb we
implement, do we handle every optional flag / parameter / mode the verb is documented to
accept, or did we implement the bare form and silently drop the variants?*

**Why it exists.** The ASCII program-save gap (`SAVE"…",A`, closed 2026-07-07,
[spec-ascii-saveload.md](../../basic/docs/spec-ascii-saveload.md)) was exactly this class
of miss: the *verb* was green on the scoreboard while an *option* of it was unimplemented.
A per-verb ✅ cannot catch a per-*option* gap. This doc is the option-level counterpart.

**Genre.** Scoreboard / notebook (the coverage matrix + gap tiers). The distilled
behavioural contract for the verbs themselves is [spec-diskbasic-verbs.md](spec-diskbasic-verbs.md);
the closure specs for the gaps found here are
[spec-diskbasic-option-closure.md](spec-diskbasic-option-closure.md).

**Clean-room basis.** The "documented options" column is the *published user-syntax* of MSX
BASIC (MSX Technical Handbook / MSX-BASIC reference) — user-facing grammar, not ROM code.
The "implemented" column is read from our own `basic/*.asm`. No reference/stock ROM was read
or disassembled ([no-reference-rom-disasm](../../README.md)).

---

## 0. Method & scope

- **Reference (the "should"):** the published optional-argument grammar of each verb.
- **Implemented (the "is"):** the argument parser in `basic/*.asm`, read statically
  (2026-07-08 sweep; two parallel readers over the loader verbs and the channel/file verbs).
- **In scope:** the disk-BASIC verb surface (the same set the scoreboard tracks) + the
  MSX-DOS-1 BDOS function surface. Cassette (`CAS:`) forms are noted where a *disk* verb
  shares the parser, but the tape stack owns them.
- **Not a bug list of general BASIC.** A few gaps below (keyboard `INPUT$(n)`, console
  `INPUT`, `CRT:`/`GRP:` device channels) straddle plain BASIC; they are recorded but
  flagged as cross-cutting, not disk-specific.

---

## 1. BDOS — the contract surface (function-complete; one real field-level gap)

BDOS functions have no *syntax* options, but "function present" ≠ "contract complete". The
real surface per function is **input registers → the ~37-byte in-memory FCB + the DTA
buffer → output registers, FCB write-backs, and DOS work-area cells (`$F100–$F3FF`)**. A
field-level pass over all of `$00`–`$30` (2026-07-08, two auditors: console/misc-register
+ work-area, and file/FCB-field) checked each contract element against our handlers and
against what the `bdos-acceptance` differential actually *exercises*.

**Result:** the `$00`–`$30` surface is function-complete and differential-verified on
driven paths — but the pass found **one genuine, undocumented, unexercised incompleteness**,
a cluster of documented/intentional simplifications, and several **stale scoreboard rows**
(the code is *more* complete than the doc claims). The differential is strong (it catches
register/FCB/work-area divergence on any path the exercisers drive — that is how FSIZE,
WRBLK, the RDRND wrong-record P1, and the LOGIN/`$F347` seed bug were all caught), but it
is only as wide as the exercisers, and the gap below sits on a path none of them drive.

### 1.1 Genuine gap (undocumented + unexercised)

- **`$15` WRSEQ — no CR/EX FCB position write-back.** M33 added `wrseq_writeback` (advance
  FCB `+32` CR / `+12` EX / cluster ptr per sequential record) but wired it to the **read**
  branch only ([kernel.asm:2694](../kernel.asm)); the **write** branch is a bare
  `jp bdos_seqwrite` with no advance ([kernel.asm:2699](../kernel.asm)). Stock advances the
  FCB on sequential *writes* too. Our own write sessions are byte-correct (the internal
  write-iterator tracks position), so the *file* is right — but the caller-visible FCB
  position is stale. **Observable path:** a program that does `WRSEQ` records then `$24`
  SETRND (which reads `+12`/`+32` to compute RR) gets a wrong random position. This is the
  exact class M33 closed for RDSEQ, left open for WRSEQ — a real asymmetry, not a design
  choice. The BDOS-side analogue of the BASIC VRAM find: a real thing hiding under a green
  function-level ✅. Closure specced in
  [spec-diskbasic-option-closure.md](spec-diskbasic-option-closure.md) Item 5.

### 1.2 Under-tracked limitation (in-code note, but never widened or gated)

- **`$21`/`$22` RDRND/WRRND — 8-bit random record + fixed 128-byte record.**
  `rrnd_position` reads only `+33` (r0), ignoring `+34`/`+35` ([kernel.asm:3001](../kernel.asm)),
  and the transfer is a hardcoded 128 bytes, ignoring the `+14..15` record-size field.
  A file > 256 records (> 32 KB) or a non-128 record size random-accesses the wrong
  location. In-code acknowledged ("0..255; see scope note") but, unlike `$26`/`$27` which
  were widened to full 24-bit RR + real RS, this tier never was. Record size `+14..15` is
  likewise ignored across `$14`/`$15`/`$21`/`$22` (only `$23`/`$26`/`$27` honor it). Low
  practical impact (128-byte records are the norm) but a real field-level omission — closure
  specced as Item 5's sibling (widen or document-and-gate).

### 1.3 Documented / intentional simplifications (correct as-is)

| fn | simplification | why it's fine |
|---|---|---|
| `$24` SETRND | ours computes the *correct* CP/M position; **stock is a broken `RR:=1` stub** | intentional signed-off divergence (m32 char §4) — ours is right where stock is broken |
| `$26` WRBLK shrink | frees the tail + EOF-marks (FCLOSE-consistent) vs stock's FAT-corrupting bug | signed off; ours correct where stock breaks |
| `$27` RDBLK (boot path) | `bdos_rdblk` streams from record 0 | boot loaders always pass RR=0 → provable no-op (M31 Q2) |
| `$2D` STIME | ignores D/E (sec/hundredths) + no range-validate (`A` always 0) | clockless MSX1; documented residual |
| `$2E` VERIFY | flag stored, write-effect not coupled | **faithful** — black-box shows stock also no-ops |
| GTIME/GDATE | return constants; STIME/SDATE don't round-trip | clockless target |
| FOPEN/FMAKE/FCLOSE | dirent date not stamped (`+25` dirloc not written) | allowlisted cosmetic |
| `$05` LSTOUT | printer no-op on C-BIOS (delegates to `$00A5` LPTOUT stub) | two-interface delegation; real when C-BIOS grows LPTOUT |

### 1.4 Stale scoreboard/spec rows (code is MORE complete than the doc — corrected this pass)

- `$02` CONOUT — TAB-expansion + `$F237` column bookkeeping **is** implemented
  (`conout_tab`/`conout_emit_e`, M22b sl2); scoreboard said "deferred". → corrected.
- `$05` LSTOUT — dispatch `$5465` **is** wired to `lstout_body`; scoreboard + spec §6.6
  said "un-wired". → corrected.
- `$27` RDBLK (user path) — `k47b2_body` **reads FCB+33..35 and positions to record RR**
  (M31 faithful); scoreboard still showed "⚠ stream-from-0". → corrected.
- `$24` SETRND — scoreboard showed a plain ✅; it is the *intentional correct-divergence*
  above. → annotated.

The rest of this doc is the BASIC verb surface.

---

## 2. Option-coverage matrix (BASIC verbs)

Legend — **✅** fully handled · **◐** partial · **✗** absent · **⚠** absent *and fails
silently* (worse than a clean error — a user gets wrong/ignored behaviour, not a syntax
error). "Ref" = the documented option. Evidence is `file:line` in `basic/`.

### Program loaders

| Verb | Documented option surface | Status | Evidence / note |
|---|---|:--:|---|
| `SAVE` | `"[dev:]name"[,A]` | ✅ | `,A` ASCII done ([save.asm:245](../../basic/save.asm:245)); `SAVE"CAS:",A` rejected (tape ASCII = follow-on) |
| `LOAD` | `"[dev:]name"[,R]` | ◐ | `,R` disk ✅; **`,R` ignored on the `CAS:` branch** ([cload.asm:98](../../basic/cload.asm:98)); ASCII/tokenised autodetect ✅ |
| `RUN"f"` | `"[dev:]name"[,R]` | ◐ | runs implicitly; no `CAS:`; trailing `,R` is a no-op |
| `MERGE` | `"[dev:]name"` (ASCII) | ◐ | disk ASCII ✅; **no `CAS:` merge**; tokenised-file merge unsupported |
| `BLOAD` | `"[dev:]name"[,R][,S][,offset]` | ⚠ | **`,S` VRAM ABSENT — silently ignored** ([bload.asm:374](../../basic/bload.asm:374)); **no `offset`**; `,R` ✅; `CAS:` ✅ |
| `BSAVE` | `"[dev:]name",start,end[,exec] \| ,start,end,S` | ⚠ | `start,end[,exec]` ✅; **`,S` VRAM ABSENT — literal `S` mis-eaten by `eval` as exec** ([save.asm:88](../../basic/save.asm:88)); `CAS:` ✅ |

### Sequential / channel I/O

| Verb | Documented option surface | Status | Evidence / note |
|---|---|:--:|---|
| `OPEN` | `"dev:name" [FOR INPUT\|OUTPUT\|APPEND] AS [#]n [LEN=r]` | ◐ | modes ✅ ([files.asm:225](../../basic/files.asm:225)); **device channels `CAS:`/`CRT:`/`LPT:`/`GRP:`/`COM:` ABSENT** (no dispatch; non-`A:/B:` colon → error [bload.asm:182](../../basic/bload.asm:182)); **`LEN=` ABSENT** (reclen fixed 256, [field.asm:31](../../basic/field.asm:31)) |
| `CLOSE` | `[[#]n[,[#]m]…]` | ◐ | bare (all) ✅, single ✅; **no comma list** ([files.asm:503](../../basic/files.asm:503)) |
| `PRINT#` | `#n[,\|;][USING …;]items` | ✅ | incl. `PRINT#n,USING` ([print.asm:59](../../basic/print.asm:59)); `TAB()`/`SPC()` not in item loop |
| `INPUT#` | `#n, var[,var…]` | ◐ | one **string** var only; **numeric ✗ (Phase-3)** ([files.asm:418](../../basic/files.asm:418)); no var list |
| `LINE INPUT#` | `#n, strvar$` | ✅ | single string var (matches doc); shares `input_common` |
| `INPUT$` | `(n[,[#]f])` | ◐ | file form ✅; **keyboard `INPUT$(n)` ✗** ([strvar.asm:159](../../basic/strvar.asm:159)) |

### Random-access record I/O

| Verb | Documented option surface | Status | Evidence / note |
|---|---|:--:|---|
| `FIELD` | `[#]n, w AS v$[,w AS v$…]` | ✅ | multi-field list ✅ ([field.asm:182](../../basic/field.asm:182)) |
| `GET#`/`PUT#` | `[#]n[,recno]` | ◐ | optional record-number ✅; **recno capped at 255** (high byte forced 0, [field.asm:642](../../basic/field.asm:642)) |
| `LSET`/`RSET`, `MK*$`/`CV*` | (no options) | ✅ | — |

### Directory / management / functions

| Verb | Documented option surface | Status | Evidence / note |
|---|---|:--:|---|
| `FILES` | `["filespec"]` | ◐ | **arg parsed-past & ignored; always lists whole root dir** ([files.asm:102](../../basic/files.asm:102)) |
| `KILL` | `"filespec"` (wildcard) | ◐ | single file only; **no wildcard** |
| `NAME` | `"old" AS "new"` | ◐ | works; **no "new exists" collision guard** ([files.asm:731](../../basic/files.asm:731)) — see §4 doc-fix |
| `MAXFILES` | `= n` (1..15) | ◐ | **capped at 2** ([files.asm:827](../../basic/files.asm:827)) |
| `CALL FORMAT` | `CALL FORMAT` (interactive) | ✅ | arg ignored; interactive menu (see §4 doc-fix) |
| `EOF`/`LOF`/`DSKF` | `(n)` / `(d)` | ✅ | `DSKF` drive arg required-but-ignored (single drive) |

### Tape verbs sharing a disk parser (tape stack owns these)

| Verb | Gap |
|---|---|
| `CSAVE` | no speed arg (`CSAVE"f",1\|2`) |
| `CLOAD` | name ignored; no `CLOAD?` verify |

---

## 3. Findings, tiered

**Tier 1 — real, in-genre, and previously undocumented (highest value).**

- **VRAM save/load (`BSAVE"…",…,S` + `BLOAD"…",S`)** — the classic screen-dump idiom
  (`BSAVE"S.SC2",BASE(…),…,S` / `BLOAD"S.SC2",S`). One coherent feature spanning both
  verbs. This is the option-level analogue of the ASCII-save miss. **Also a latent
  correctness trap:** `BSAVE"f",0,100,S` today evaluates `S` as an exec expression and
  saves RAM with a garbage exec — silently wrong, not an error.
- **Silent-parse hygiene** — `BLOAD`/`LOAD` accept and *ignore* any unrecognized comma-flag
  ([bload.asm:375](../../basic/bload.asm:375)); `BSAVE` mis-eats `S`. Violates
  "honest at the walls" — a typo or an unimplemented flag should be a clean `Syntax error`,
  not a silent no-op. Cheap; same parse sites as the VRAM work.

**Tier 2 — real but larger / partial-scope.**

- **OPEN device-name channels** (`CRT:`/`LPT:`/`GRP:`/`COM:`, and `CAS:` for OPEN) — no
  device-dispatch site exists at all. Overlaps general BASIC + the tape/printer stacks.
- **OPEN random `LEN=`** — record length hard-wired to 256; `LEN=128` won't parse.
- **BLOAD `offset`** — load address comes solely from the file header; no relocation param.

**Tier 3 — quality-of-life.**

- `FILES` / `KILL` wildcard filespec matching.
- `CLOSE` channel-list form.
- `INPUT#` / `LINE INPUT#` multi-variable lists.
- `MAXFILES` range (2 → up to 15); `GET`/`PUT` record numbers > 255.

**Cross-cutting (straddles general BASIC, not disk-specific):** numeric `INPUT#`
(already tracked Phase-3), keyboard `INPUT$(n)`, console `INPUT`.

**Already honestly out-of-scope (documented, not silent):** `LOC`, `DSKI$`, `DSKO$`
(direct-sector, Phase-3); the CLOSE / LINE INPUT# thin *verification* cells.

---

## 4. Doc-accuracy discrepancies this sweep caught

1. **`NAME` "shares the M35 refusal".** [spec-diskbasic-verbs.md](spec-diskbasic-verbs.md)
   §1 states the `NAME` verb rejects a rename collision. It does **not**: the handler
   overwrites the dir entry with no "new exists" check ([files.asm:731](../../basic/files.asm:731),
   its own comment: *"no 'new already exists' check (own design)"*). The M35 collision
   refusal + `test_fren_collision` are on the **BDOS `$17` FREN** path (MSX-DOS / `.COM`),
   which the BASIC verb does not route through. → spec corrected.
2. **`CALL FORMAT` "no prompts".** The [format.asm](../../basic/format.asm) header comment
   says the format path shows no prompts, but `do_format` reads an interactive
   `1=360k 2=720k?` menu ([format.asm:108](../../basic/format.asm:108)). → comment corrected.

---

## 5. Disposition

Per [spec-before-implementation](../../README.md): the gaps above are captured here (the
sweep) and specced for sign-off in
[spec-diskbasic-option-closure.md](spec-diskbasic-option-closure.md) **before** any code.
Closure order recommended: Tier 1 (VRAM `,S` + silent-parse hygiene, one work item on the
shared parse sites) → Tier 2 → Tier 3. Each closed option must land a gate cell in
`make diskbasic-acceptance` so an option can no longer silently regress — the same lesson
the ASCII-save arc and the scoreboard's F2 finding already taught.

## Provenance

Sweep performed 2026-07-08 by static read of `basic/*.asm` (parser acceptance) cross-checked
against published MSX-BASIC user-syntax. No reference ROM read. Companion documents:
[spec-diskbasic-verbs.md](spec-diskbasic-verbs.md) (verb behaviour),
[diskbasic-verb-coverage.md](diskbasic-verb-coverage.md) (per-verb scoreboard),
[tier2-bdos-coverage.md](tier2-bdos-coverage.md) (BDOS function scoreboard).
