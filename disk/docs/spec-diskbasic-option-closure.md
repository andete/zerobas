<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec (for sign-off): Disk-BASIC option-surface closure

> **STATUS: ALL ITEMS (1–5) IMPLEMENTED + GATED (2026-07-08). Closure spec COMPLETE.**
> Item 4 (FILES/KILL 8.3 `*`/`?` wildcards + CLOSE channel list) landed 2026-07-08,
> byte-identical to CF-3300; Item 3 `LEN=` (sector-tiling sizes only, a user-decided scope
> narrowing) and Items 1+2+5 earlier the same day. Device channels (Item 3's second half)
> were routed to the plain-BASIC axis, out of this disk-BASIC spec. See the Sign-off section.
> Q1.4 (BLOAD `,offset`) resolved: **deferred, but the parser now rejects a
> typed offset with a clean `load error`** (never a silent wrong-address load) and is
> structured so real offset support is a one-branch add. See the Sign-off section.
> ✅ **SUPERSEDED 2026-10-07 (D-BLOADOFS): the offset is implemented.** The "clean
> `load error`" was PRINTED and RETURNED -- no ON ERROR handler ever saw it -- and
> it was not one branch: the offset is an expression, so the parse moved into main
> (`pcr_bload`, basic/bload.asm), where `eval` is mapped.
> Per
> [spec-before-implementation](../../README.md) this captures the design + verification
> plan for the option gaps chosen from the sweep
> ([diskbasic-option-surface.md](diskbasic-option-surface.md)) so they can be **signed off
> before** any implementation. Each work item has its own sign-off line and open
> questions; they can be approved independently and in tiers.

The items, in recommended closure order:

1. **VRAM `,S`** on `BSAVE`/`BLOAD` + the silent-`S` correctness trap (Tier 1).
2. **Silent-parse hygiene** — reject unrecognized comma-flags (Tier 1, rides on #1's sites).
3. **OPEN device channels + `LEN=`** (Tier 2).
4. **`FILES`/`KILL` wildcard + `CLOSE` list** (Tier 3).
5. **BDOS `$15` WRSEQ FCB position write-back** (+ the RDRND/WRRND / record-size sibling) —
   the one genuine gap from the BDOS contract-completeness pass
   ([diskbasic-option-surface.md §1.1–1.2](diskbasic-option-surface.md)).

A shared rule for all four: **every option closed lands a cell in
`make diskbasic-acceptance`** so it cannot silently regress (the F2 lesson from
[diskbasic-verb-coverage.md](diskbasic-verb-coverage.md)).

---

## Item 1 — VRAM save/load (`BSAVE"…",…,S` + `BLOAD"…",S`)

**Reference grammar (published MSX-BASIC syntax).**

```
BSAVE "dev:name", start, end [, exec]          ; RAM save   (existing)
BSAVE "dev:name", start, end, S                ; VRAM save  (NEW) — start/end are VRAM addrs
BLOAD "dev:name" [, R]                          ; RAM load   (existing)
BLOAD "dev:name", S                             ; VRAM load  (NEW) — header addrs are VRAM
```

The `S` occupies the **4th positional slot** of `BSAVE` (where `exec` would go) and the
**first option slot** of `BLOAD`. With `,S` the start/end/exec stored in (BSAVE) or read
from (BLOAD) the `$FE` header are interpreted as **VRAM** addresses; the bytes stream
to/from VRAM instead of RAM. `exec` is meaningless for a VRAM save (no run target).

**Approach — minimal swap of the byte source/sink.** The existing data loops already
move `RAM[start..end]` one byte at a time:
- `BSAVE` RAM path: [save.asm:107](../../basic/save.asm:107) (`bsv_data`) reads
  `RAM[cur]` → file. VRAM variant: read `RDVRM(cur)` ([sysvars.inc:48](../../basic/sysvars.inc:48),
  `$004A`) instead.
- `BLOAD` RAM path: the header-directed store loop. VRAM variant: `WRTVRM(addr)`
  ([sysvars.inc:47](../../basic/sysvars.inc:47), `$004D`) instead of a RAM store.

A single `VRAM_FLAG` scratch byte selects the source/sink. Byte-by-byte `RDVRM`/`WRTVRM`
is the low-risk fit (mirrors the existing loop shape); a `LDIRMV`/`LDIRVM` block move is a
later perf option, not needed for correctness.

**Parse-site changes.**
- `BSAVE` ([save.asm:82-89](../../basic/save.asm:82)): the optional-4th-arg parse must
  peek the token *before* `eval`. If it is the literal `S` (not part of an expression),
  set `VRAM_FLAG`, leave `exec = start`, and do **not** feed `S` to `eval`. **This is the
  fix for the current silent trap** where `S` is mis-evaluated as an exec expression.
- `BLOAD` ([bload.asm:104-378](../../basic/bload.asm:104), `parse_close_run`): add an `S`
  branch alongside the existing `R` test; `S` sets `VRAM_FLAG`.

**Verification.** New gate cells `BSAVE(VRAM)` / `BLOAD(VRAM)`: BSAVE a known VRAM region
(write it first via `VPOKE`/screen), BLOAD it back, assert the VRAM range round-trips
byte-identical. Preferred harness = the keyboard-free `.bas`-on-disk / AUTOEXEC path
([diskbasic-bas-harness-spec.md](diskbasic-bas-harness-spec.md)), not `type`-injection.
Oracle: differential vs CF-3300 (`BSAVE"S.SC1",...,S` of a filled pattern) + an offline
FAT12 header/byte check of the `.SC*` file.

**Open questions for sign-off.**
- **Q1.1** Scope the header semantics: on VRAM save do we store the VRAM start/end/exec
  verbatim in the `$FE` header (stock behaviour), so a `,S` BLOAD reads them back as VRAM
  addresses? (Recommend: yes — match stock so `.SC1/.SC2` screen files interchange.)
- **Q1.2** Do we support combining `,S` with `,R` on BLOAD? (Recommend: **no** — a VRAM
  load has no exec target; `BLOAD"f",S,R` → `Syntax error`. Keep it simple.)
- **Q1.3** MSX1 VRAM is 16 KB (`$0000–$3FFF`). Clamp/validate addresses ≥ `$4000`, or pass
  through to `RDVRM`/`WRTVRM` (which mask to the VDP address width)? (Recommend: pass
  through; document the 14-bit wrap, don't add a range error stock doesn't have.)
- **Q1.4** `offset` param (`BLOAD"f",S,offset` / `BLOAD"f",R,offset`) — **out of this
  item's scope** (deferred to a follow-on); flagged here only so the parse grammar leaves
  room for it. Confirm deferral.

---

## Item 2 — Silent-parse hygiene ("honest at the walls")

**Problem.** After the closing quote, `BLOAD`/`LOAD` silently *ignore* any comma-flag that
is not `R` ([bload.asm:375](../../basic/bload.asm:375), `jr nz,pcr_ok`); `BSAVE`
mis-evaluates a stray 4th token. A typo (`BLOAD"f",X`) or an unimplemented flag produces a
silent no-op, not a diagnostic — the exact failure mode that hid the VRAM gap.

**Approach.** Convert the "unrecognized flag" fall-through into a clean `Syntax error`
(`load_error`), *after* Item 1 has taught the parsers the legitimate flags (`R`, `S`). So:
- `parse_close_run`: recognize `R` and `S`; **anything else → `load_error`**.
- `BSAVE` 4th slot: `S` → VRAM; a numeric expression → exec; **a bare identifier that is
  neither → `load_error`** rather than a wrong exec.

**Verification.** Negative gate cells: `BLOAD"f",X` and `BSAVE"f",0,9,Q` must each raise
`Syntax error` (assert the error, not a silent load). Fold into the Item-1 gate cells.

**Open questions.**
- **Q2.1** Any real MSX program that relies on the lenient ignore (unlikely)? This changes
  a silent no-op into an error — a behavioural change. Confirm we want strictness (Recommend:
  yes; it is the stated "honest at the walls" principle and matches stock, which errors).

---

## Item 3 — OPEN device channels + random `LEN=`

> **⚠ Scoping call needed first (Q3.0).** Device-name channels (`CRT:`/`LPT:`/`GRP:`/`COM:`)
> are **general-BASIC I/O**, not disk-specific — `OPEN"CAS:"` belongs to the tape stack,
> `LPT:` to the printer path (LPTOUT now lives in zerobas-tape,
> [cbios-lptout-followup](../../basic/docs/)), `COM:` needs RS-232 hardware absent on this
> MSX1 target. This item may belong to the **plain-BASIC axis**, not disk-BASIC. Decide the
> home before building. `LEN=` (below) *is* squarely disk-BASIC and can proceed regardless.

**Reference grammar.**

```
OPEN "dev:name" [FOR INPUT|OUTPUT|APPEND] AS [#]n [LEN=reclen]
  dev ∈ { A:|B: (disk, existing), CAS: (tape), CRT:|GRP: (screen), LPT: (printer), COM: (RS-232) }
```

**Approach.**
- **`LEN=` (in-scope, low-risk):** parse an optional `LEN` token + `= expr` after `AS #n`
  ([files.asm:290](../../basic/files.asm:290)); pass `reclen` (1..256, default 256) into
  `fat_rand_open` and the FIELD record size ([field.asm:31](../../basic/field.asm:31)),
  replacing the hard-wired 256.
- **Device channels (pending Q3.0):** add a device-name dispatch *ahead of*
  `parse_disk_fcb` in `ex_open` ([files.asm:216](../../basic/files.asm:216)) — a prefix
  peek (same shape as the `CAS:` peek the loaders use). Recommended MSX1 subset to
  implement: `CRT:` (→ screen, `CHPUT`), `LPT:` (→ printer, `LPTOUT`), and `CAS:`
  (→ tape sequential, delegating to the tape stack). Defer `GRP:` (graphics text) and
  `COM:` (no hardware) as explicit non-goals.

**Verification.** `LEN=`: a random round-trip with `LEN=128` records asserts record
positioning at 128-byte stride (host unit test `test_open_len` + a gate cell). Device
channels: `PRINT#` to a `CRT:` channel renders on screen; `LPT:` prints via the openMSX
printer logger ([openmsx-printer-pluggable](openmsx-probing-toolbox.md)).

**Open questions.**
- **Q3.0** Home this item in disk-BASIC or the plain-BASIC axis? (Recommend: split — do
  `LEN=` now under disk-BASIC; route device channels to the plain-BASIC track.)
- **Q3.1** Device subset: `CRT:`+`LPT:`+`CAS:` only, or also `GRP:`? (Recommend: the three;
  `GRP:` deferred.)
- **Q3.2** `LEN=` max — 256 (our buffer) or the MSX 256 ceiling anyway? (Recommend: 1..256,
  error outside.)

---

## Item 4 — FILES/KILL wildcard + CLOSE list

**Reference grammar.**

```
FILES ["filespec"]     ; filespec = [drive:]pattern, pattern uses 8.3 * and ?
KILL  "filespec"       ; wildcard delete
CLOSE [[#]n [,[#]m]…]   ; channel list
```

**Approach.**
- **`FILES` filespec:** today the arg is consumed-and-ignored
  ([files.asm:102](../../basic/files.asm:102)); instead parse it into an 8.3 pattern and
  match each dir entry (`*` = fill remainder, `?` = any one char) before listing. Bare
  `FILES` stays "list all".
- **`KILL` wildcard:** loop the dir scan, deleting every entry matching the 8.3 pattern
  (reuse the FILES matcher + the existing single-file `ex_kill` free-chain logic).
- **`CLOSE` list:** after closing one channel ([files.asm:503](../../basic/files.asm:503)),
  loop while the next token is `,` — parse `[#]expr`, close, repeat.

**Verification.** `FILES"*.BAS"` lists only `.BAS` entries (differential vs CF-3300);
`KILL"*.TMP"` deletes the matching set and leaves others (offline FAT12 dir check);
`CLOSE#1,#2` closes both (channel-table assert). One gate cell each.

**Open questions.**
- **Q4.1** `KILL` wildcard with zero matches — silent, or `File not found`? (Recommend:
  match stock — `File not found` if the pattern matches nothing.)
- **Q4.2** `FILES` filespec on a no-match — empty listing + free-space footer, or an error?
  (Recommend: empty listing, matches stock `FILES` semantics.)

---

## Item 5 — BDOS `$15` WRSEQ FCB position write-back (+ RDRND/WRRND siblings)

> **BDOS-layer item** (the others are BASIC-verb). Surfaced by the contract-completeness
> pass, not the syntax sweep. Verified against source, not yet fixed.

**The gap.** M33 added `wrseq_writeback` (advance FCB `+32` CR / `+12` EX / cluster ptr per
sequential record) but wired it to the **read** branch only
([kernel.asm:2788](../kernel.asm)); `wrseq_body_write` is a bare `jp bdos_seqwrite`
([kernel.asm:2699](../kernel.asm)) with no advance. Stock MSX-DOS-1 advances the FCB on
sequential *writes* too. Our written file is byte-correct (the internal write-iterator
tracks position); only the **caller-visible FCB position** goes stale. Observable via a
`WRSEQ`-then-`$24 SETRND` sequence (SETRND reads `+12`/`+32` to compute RR).

**Approach.** Mirror the read-branch fix: after `bdos_seqwrite` returns on a written
record, call `wrseq_writeback` (or a write-flavoured twin) to advance `+32`/`+12`/cluster
from the same write-iterator state. The routine already exists; the change is wiring it on
the write branch with the correct "record written" condition (no EOF skip — a write always
advances). Watch the `$F306` HL rule and that our own PRINT#/COMMAND.COM-copy write paths
still round-trip (they read internal state, not the FCB, so should be unaffected — assert
it).

**Sibling (decide together).** `$21`/`$22` RDRND/WRRND position on `+33` (r0) only and use a
fixed 128-byte record, ignoring `+34/+35` and `+14..15`
([diskbasic-option-surface.md §1.2](diskbasic-option-surface.md)). Two honest options:
(a) **widen** to full 24-bit RR + real record size (matches `$26`/`$27`, unblocks
> 32 KB random files); or (b) **document-and-gate** the 8-bit/128-byte limit as a signed-off
boundary. Same call applies to the `+14..15` record-size omission across `$14`/`$15`.

**Verification.** A differential that does `WRSEQ` of N records then reads the FCB position
bytes (`+12`/`+32`) and compares to stock — the write-back must match. Add a
`test_wrseq_position` host unit test alongside the existing `test_wrblk_*`. For the sibling,
a > 256-record random round-trip (option a) or a negative-bound assertion (option b). Land
the cell in `make bdos-acceptance` (this is a differential, so it stays out of the
emulator-free `unit-test` — except the host position twin).

**Open questions.**
- **Q5.1** WRSEQ write-back: fix now (recommended — it's a real asymmetry M33 left open,
  same low-risk shape as the RDSEQ fix)?
- **Q5.2** RDRND/WRRND sibling: **widen** to 24-bit RR + real RS, or **document-and-gate**
  the 8-bit/128 limit? (Recommend: document-and-gate first — 128-byte records are the norm
  and widening is unverified surface; widen later if a real > 32 KB random-file need appears.)

---

## Cross-item verification & provenance

- All new option behaviour is **black-box** vs the CF-3300 oracle and/or the read-only
  FAT12 artifact oracle ([oracle-artifacts.md](oracle-artifacts.md)); no reference ROM is
  read ([no-reference-rom-disasm](../../README.md)).
- Prefer the keyboard-free `.bas`-on-disk / AUTOEXEC harness over `type`-injection for
  every new cell (the SAVE/BSAVE flaky-probe lesson,
  [diskbasic-verb-coverage.md](diskbasic-verb-coverage.md) §0).
- On each item's landing: add its cell(s) to `make diskbasic-acceptance`, bump the gate
  count, and tick the option's row in
  [diskbasic-option-surface.md](diskbasic-option-surface.md) §2 from ✗/⚠/◐ to ✅.

## Sign-off

- [x] **Item 1** — VRAM `,S` — **DONE 2026-07-08.** `VRAM_FLAG` ($E0E9); `bsave_opt4`
  classifier + `bsv_data` RDVRM source ([save.asm](../../basic/save.asm)); `parse_close_run`
  `S` branch + `disk_load_loop` WRTVRM sink ([bload.asm](../../basic/bload.asm)). Header
  addrs stored/read verbatim (Q1.1); no `,S`+`,R` combine (Q1.2); pass-through 14-bit wrap
  (Q1.3); `,offset` deferred but cleanly rejected (Q1.4). Gate cell `BSAVE/BLOAD(VRAM)`
  (CF-3300 differential, byte-identical both save + load paths).
- [x] **Item 2** — silent-parse hygiene — **DONE 2026-07-08.** BLOAD via `parse_close_run`
  CF-return; BSAVE via `bsave_opt4` **CF-return** (Q2.1 strict). ⚠ Found + fixed a real bug:
  `bsave_opt4` first used `jp load_error` internally, but `load_error` ends in `ret` and
  resumes the *caller* (do_bsave) — so a rejected `,Q` still created the file. Fixed to the
  CF-return + top-level `jp c,load_error` pattern. Gate cell `OPTION(hygiene)` (ours-only
  behavioural: NEG `,X` / `,S,offset` / BSAVE `,Q` all reject; positive load still works).
- [x] **Item 3** — `LEN=` **DONE 2026-07-08.** Scope surprise surfaced + user-decided
  (the record engine assumed 256-byte sector-tiling records; a naive "replace 256" would
  silently corrupt on a straddling size): **sector-tiling sizes only** — `LEN=r` for r a
  power of two in 1..256 (512/r records tile the sector, no straddle); non-tiling / out-of-
  range → `Syntax error`. `oo_parse_reclen` ([files.asm](../../basic/files.asm)) parses the
  `$FF $92` LEN token + validates; per-channel `FCH_RECLENS` (default 256); `frnd_calc`
  generalized to `byteoffset=(N-1)*r → GP_SEC/GP_WITHIN` + `mul_reclen`/`load_reclen`
  ([field.asm](../../basic/field.asm)). Gates: host [test_open_len.py](../../tests/test_open_len.py)
  (geometry r=256/128/64/1 + parse/rejection; `make unit-test` 37/37) + CF-3300 differential
  [disk_probe_openlen.py](../../probes/disk/disk_probe_openlen.py) (`OPEN(LEN=)` cell in
  `make diskbasic-acceptance`, LEN=128 4-record round-trip byte-identical). Device channels
  routed to the plain-BASIC axis (Q3.0), out of scope here.
- [x] **Item 4** — FILES/KILL wildcard + CLOSE list — **DONE 2026-07-08.** Shared
  matcher: `name_cmp` ([fat.asm](../../basic/fat.asm)) now honours `?`, and `build_83_name`
  ([bload.asm](../../basic/bload.asm)) expands `*` to fill a field with `?`. FILES filters
  each dir entry through `name_cmp` (bare FILES lists all); KILL loops `fat_delete` over
  every match (Q4.1: File-not-found if none matched); CLOSE parses a `,`-separated channel
  list (`dc_listloop`, [files.asm](../../basic/files.asm)). **FILES + KILL wildcard are
  byte-identical to CF-3300** (Q4.2 empirically confirmed — CF-3300 wildcards the same:
  [disk_probe_files_wildcard.py](../../probes/disk/disk_probe_files_wildcard.py),
  [disk_probe_kill_wildcard.py](../../probes/disk/disk_probe_kill_wildcard.py), full-image
  diff). CLOSE-list is a keyboard-free functional gate
  ([disk_probe_closelist.py](../../probes/disk/disk_probe_closelist.py)). Host matcher test
  [test_wildcard.py](../../tests/test_wildcard.py) (`make unit-test` 38/38); cells
  `FILES(wild)`/`KILL(wild)`/`CLOSE(list)` in `make diskbasic-acceptance`.
- [x] **Item 5** — **DONE 2026-07-08.** (5a) BDOS `$15` WRSEQ FCB write-back: the
  register-transparent write-side twin `wrseq_wr_writeback` ([kernel.asm](../kernel.asm),
  commit 932f5e8) advances +12 EX / +16..19 size / +26,27 first cluster / +28,29 cluster /
  +30 rec-in-cluster / +32 CR from the write-iterator cells after every written record;
  wired on `wrseq_body_write` (advance only on A=$00), `BDOS_SEQREC` reset at write-open.
  Net-zero (`disk.rom` 16384 B). **Byte-identical to CF-3300** (differential BDOSX8;
  `make bdos-acceptance` 12/12, BDOSX3/BDOSX4 unchanged) + emulator-free twin
  [test_wrseq_position.py](../../tests/test_wrseq_position.py). (5b) RDRND/WRRND 8-bit/128
  limit **document-and-gated** (Q5.2): promoted to a signed-off boundary in
  [diskbasic-option-surface.md §1.3](diskbasic-option-surface.md), PINNED by the
  negative-bound gate [test_rrnd_8bit_limit.py](../../tests/test_rrnd_8bit_limit.py)
  (proves r1/r2 + `+14/15` fully ignored — silent-drift guard). `make unit-test` 36/36.
