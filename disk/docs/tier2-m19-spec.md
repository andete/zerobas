<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M19 spec — runtime directory search (BDOS SFIRST `$11` / SNEXT `$12`)

**Status: CHARACTERISED + DESIGNED (2026-07-01, Opus span). SPEC ONLY — no asm
touched, no fix implemented. STOP for sign-off.** Per [[spec-before-implementation]]
this is a **new-routine-class** milestone (like [tier2-oi3-spec.md](tier2-oi3-spec.md)),
NOT a self-approvable veneer-class fix (contrast [tier2-m17-spec.md](tier2-m17-spec.md)):
it is a substantial directory-search routine, so it gets its own explicit design
reasoning + sign-off. Resume board: [tier2-STATE.md](tier2-STATE.md). Characterisation
this builds on: [tier2-bdos-fcbread-spec.md](tier2-bdos-fcbread-spec.md) §3.

## 1. Goal
Make MSX-DOS `DIR` work on ours. Concretely: after `\rDIR\r` at `A>`, ours must render
the SAME directory listing as stock (test.dsk: the file list + `nn files` + `375808 bytes
free` + a fresh `A>`), instead of hanging in the current SETDTA/SNEXT search loop with a
blank screen. The mechanism is the two un-wired page-1 kernel dir-search entries
**`$4FB8` (SFIRST)** and **`$5006` (SNEXT)**; the fix wires them to a real root-directory
search built on our own `fat_mount`/`fat_find`/DPB layer. Tier-1 green, `disk.rom`==16384 B,
no canonical-address shift, all prior milestone repros intact.

## 2. Entry/exit register contracts — PINNED black-box (this span)
Method: `probes/disk/disk_probe_diff.py` (`callseq --log`, `capture --at`), test.dsk
auto-copied to tmp (mutation-safe), anchored at COMMAND.COM `$0100`, driven with
`--keys '\rDIR\r' --keys-at 22 --settle 60`. NO stock/kernel CODE bytes were decoded —
only entry PCs (addresses), call counts, and entry/exit register snapshots.

### 2.1 SFIRST `$4FB8` — entry contract (PINNED)
`callseq --log 0x4FB8`: **ours 1 call / stock 1 call**, register-identical.
`capture --at 0x4FB8 --nth 1` full regset (STOCK):

| reg | value | reg | value |
|---|---|---|---|
| PC | `$4FB8` | HL | `$5800` |
| SP | `$DBFE` | IX | `$F45C` (stock) / `$F1AA` (ours) — **NOT consumed**, diff is benign |
| AF | `$1000` | IY | `$DC5B` |
| BC | `$0000` | ret | `$D88A` (the shared kernel trampoline, as M17/M18) |
| DE | `$DA40` | | |

### 2.2 SNEXT `$5006` — entry contract (PINNED)
`callseq --log 0x5006`: **ours 6 calls / stock 6 calls**, register-identical **on every
call** (all 6 snapshots byte-identical: `AF=1000 BC=0000 DE=DA40 HL=5800 ret=D88A`).
`capture --at 0x5006 --nth 1` and `--nth 6` (STOCK) both show `AF=1000 BC=0000 DE=DA40
HL=5800 SP=DBFE`; only IX/IY differ ours-vs-stock and neither is consumed.

### 2.3 What the registers mean (the load-bearing finding)
**`DE=$DA40` and `HL=$5800` are CONSTANT across every SFIRST and SNEXT call** — they do
NOT vary per search the way a per-call FCB-pointer / DTA-pointer would. They are therefore
**fixed kernel-internal work-area pointers, not the search FCB / DTA passed in registers.**
This matches the M17/M18 shape exactly: like SELDSK (`$50D5`) and CURDRV (`$50C4`), the
page-1 dir-search entry is a **pure primitive whose real inputs live in the MSX-DOS work
area**, not in the entry registers. The kernel has already set up the search FCB (the 8.3
pattern + drive) and the DTA before it CALLs `$4FB8`/`$5006`; the disk-ROM entry's job is to
perform ONE directory-walk step against that already-established state and report found /
not-found via the return convention (§2.4). **⇒ our body reads the search pattern + DTA from
the established work-area/DTA state and writes the 32-byte found entry to the DTA — it does
NOT take an FCB pointer in DE.** (`HL=$5800` is in the DTA region the char doc already
observed — `disk_probe_diff.py callseq` at BDOS level shows the SETDTA/SNEXT loop churning
`HL=5800`; that is the DTA these calls target.)

### 2.4 Exit contract (found / exhausted) — convention pinned, exact code deferred to build
Per the published MSX-DOS-1 SFIRST/SNEXT contract (map.grauw.nl MSX-DOS function list;
MSX2 Technical Handbook §BDOS / §FCB; MSX Datapack): both functions return in **A** —
**A = `$00` a matching entry was found (its 32-byte directory image is in the DTA)**,
**A = `$FF` no (more) matching entry (search exhausted)**. The BDOS-level stream confirms
the *observable behavioural* contract this must reproduce: `callseq --log 0x0005 --maxhits
90 --keys '\rDIR\r'` shows **ours == stock byte-identical through n=33**, then STOCK's search
**terminates** (n=31 the search call returns exhausted, the kernel proceeds to CONOUT the
listing at n=34) while OURS re-enters an endless `$1A`/`$12` (SETDTA/SNEXT) alternation and
never prints — i.e. ours' SNEXT NEVER returns the "exhausted" signal, so the caller's loop
has no exit. The FIX must make SNEXT return "exhausted" once the root dir is walked out.

**Falsify-first exit-pin (do at build, exactly as M17 §4 deferred its return-F):** the
simplest hypothesis is **A=$00 found / A=$FF exhausted, flags irrelevant**. Build that; the
acceptance probe (§6.2/§6.3) proves it if the DIR listing renders and the BDOS stream
matches stock past n=33. If it stalls on a flag-dependent branch, re-pin the exact exit
register/flag via a black-box `capture` of the kernel's post-`$5006` branch input and add the
matching op (our own op chosen to REPRODUCE the observed value — never copied). Rationale for
deferring: pinning the exit reg precisely would require trapping stock's return path and
risks drifting toward decoding stock's routine, which the clean-room rule forbids; the
published contract + the behavioural stream give a testable hypothesis without that.

## 3. Root cause (pinned, clean-room — no stock/kernel code decoded)
The relocated RAM kernel, processing BDOS SFIRST (`$11`) / SNEXT (`$12`), CALLs page-1
disk-ROM entries at **`$4FB8`** and **`$5006`**. On ours both are `$00` NOP-padding
(verified: `build/disk.rom` at `$4FB8` = `00 00 00 …`, at `$5006` = `00 00 00 …`; the whole
`$4EE1..$50A9` region is our own `$00` fill from the `ds $50A9-$` in kernel.asm). The CALL
NOP-slides forward into the `$50A9` stub tail (`$50AD..$50B7`: `ld de,$F1AA / ld ix,$F1AA /
ld hl,$F359 / ret`), whose `ret` hands back the `$50A9` continuation contract — which the
SNEXT caller misreads as "another directory entry was found." So SNEXT never signals
exhausted and the search never terminates: `DIR` hangs, printing nothing. **Same un-wired
`$50xx`/`$4xxx`-entry CLASS as M13/M17/M18 — but the correct body is a full directory-search
routine, not a 3-byte read-a-cell veneer.** (Char doc §3.1 evidence: `callwatch --in-func
0x11/0x12` — stock executes 108/101 distinct page-1 PCs; ours executes only the entry + the
`$50AD-$50B7` stub tail, 80× for SNEXT.)

## 4. Design — the bodies (reuse our own `fat_*` layer)
Two new routines in the free tail (kernel.asm, like `seldsk_drv_body`/`conin_line_body`),
reached by 3-byte `jp` veneers at the two canonical entries. They reuse our own
`fat_mount` + the root-dir iteration already inside `fat_find` (`ff_secloop`/`ff_entloop`/
`name_cmp`/`toupper`), adding: (a) a search-position cursor persisted across calls, and
(b) the DTA copy of the 32-byte found entry.

### 4.1 What we already own (read from fat.asm/driver.asm — reusable as-is)
- `fat_mount` (fat.asm:114): parse BPB → `FAT_FIRSTROOT`, `FAT_ROOTSECS`, `FAT_FIRSTDATA`,
  `FAT_SECPERCLUS`, geometry; leaves boot sector in `SECTOR_BUF`. Reuse verbatim.
- `fat_find`'s root-dir walk (fat.asm:171-244): iterates root-dir sectors via
  `FAT_DIRSEC`/`FAT_DIRREM`, 16 entries/sector, skips `$E5` (deleted) and end-mark `$00`,
  skips `attr & $18` (volume-label|directory), compares the 11-byte 8.3 name with
  `name_cmp` (case-insensitive via `toupper`). This is exactly the scan M19 needs; M19
  generalises it from "find the one open-file name, stop" to "find the next entry matching a
  (possibly wildcarded) pattern, remember where we stopped."
- `read_sector` (fat.asm:106), `SECTOR_BUF` ($E2A0, 512 B), the DPB layer.
- The DTA pointer: our `bdos_entry` path uses `BDOS_DTA` ($E4C0), but that is the PRIVATE
  loader BDOS surface (char doc §1), NOT the runtime kernel's DTA. The runtime DTA is the
  kernel-established DTA the `$4FB8`/`$5006` calls target (`HL=$5800` region, §2.3); the
  body copies the found entry there. **Open build item:** confirm at build whether the
  runtime DTA base is reachable from a work-area cell the entry can read, or whether the
  32-byte image is written relative to the established DTA the kernel set via its own SETDTA
  (the char doc shows runtime `$1A` SETDTA calls with `DE=D403`/`D3DB` — that DTA is what
  DIR's formatter reads). Pin the exact runtime-DTA source (`capture`/`readwatch` on our own
  memory after our own call) as the first build step, same as §2.4's exit-pin.

### 4.2 `sfirst_body` (the `$4FB8` entry)
```
; sfirst_body — BDOS SFIRST ($11): find the FIRST root-dir entry matching the
; kernel-established search pattern; copy its 32-byte dir image to the DTA;
; persist the scan position; return A=$00 found / A=$FF none.  (clean-room: our
; own dir walk + published SFIRST contract; NO stock routine decoded.)
sfirst_body:
;   1. call fat_mount            ; (re)parse BPB -> FAT_FIRSTROOT/FAT_ROOTSECS
;                                ;    ret c -> A=$FF (disk error = no entry)
;   2. init the scan cursor to entry 0:
;        FAT_DIRSEC := FAT_FIRSTROOT ; FAT_DIRREM := FAT_ROOTSECS
;        BDOS_SRCHIDX := 0        ; absolute directory-entry index (see §5)
;   3. jr dirscan_match           ; shared body: scan from BDOS_SRCHIDX for a match
```

### 4.3 `snext_body` (the `$5006` entry)
```
; snext_body — BDOS SNEXT ($12): resume from the saved scan position, find the
; NEXT matching root-dir entry; same DTA copy; return A=$00 / A=$FF exhausted.
snext_body:
;   1. call fat_mount            ; geometry back into scratch (idempotent, cheap)
;                                ;    ret c -> A=$FF
;   2. reconstruct the scan cursor FROM the persisted BDOS_SRCHIDX:
;        FAT_DIRSEC := FAT_FIRSTROOT + (BDOS_SRCHIDX >> 4)   ; 16 entries/sector
;        FAT_DIRREM := FAT_ROOTSECS - (BDOS_SRCHIDX >> 4)
;        (entry-within-sector offset = BDOS_SRCHIDX & 15, applied in the scan)
;   3. jr dirscan_match           ; continue from the entry AFTER the last match
```
(Reconstructing the cursor from a single absolute index `BDOS_SRCHIDX` is simpler and more
robust than caching `FAT_DIRSEC`/`FAT_DIRREM` across calls — those are also used by
`fat_find`/`fat_dir_create` on the LOADER path, so persisting THEM across runtime calls
risks cross-surface clobber. One own cell that we recompute the sector/offset from is clean.)

### 4.4 `dirscan_match` (shared body)
```
; dirscan_match — walk the root dir from the current cursor; on the first entry
; whose 8.3 name matches the search pattern (with ? wildcard, §4.5): copy the
; 32-byte entry to the DTA, set BDOS_SRCHIDX := that-index + 1, return A=$00.
; On end-of-directory ($00 mark) or all sectors scanned: return A=$FF.
;   - reuse the ff_secloop/ff_entloop structure (read sector, 16 entries),
;     but skip entries whose absolute index < BDOS_SRCHIDX (SNEXT resume),
;   - skip $E5 (deleted) and attr&$18 (vol-label|subdir) as fat_find does
;     [confirm DIR's attribute filter against the published SFIRST spec at
;      build — SFIRST may include volume label / subdir entries; DIR on a flat
;      MSX-DOS-1 720K disk has neither, so the fat_find filter is safe for the
;      acceptance test, but DOCUMENT the chosen filter],
;   - name match = name_cmp_wild (name_cmp + the ? rule, §4.5),
;   - on match: LDIR the 32 bytes at (dir entry) -> (runtime DTA); save index+1.
```

### 4.5 Wildcard `?` semantics (published contract — cited, not invented)
MSX-DOS-1 FCB search matches an 8.3 name field where **`?` (byte `$3F`) in the search FCB's
name/ext matches ANY single character in that position** (the standard CP/M-derived FCB
wildcard; `*` is expanded by COMMAND.COM into `?`-fill BEFORE the FCB is built, so the FCB
the disk-ROM entry sees contains only literal chars and `?`, never `*`). Source: MSX2
Technical Handbook §FCB / MSX-DOS function table (map.grauw.nl), CP/M 2.2 FCB match rule.
So `name_cmp_wild` = `name_cmp` (case-insensitive, `toupper`) with **one added rule: a search
byte of `$3F` matches unconditionally.** `DIR` with no argument searches the FCB `???????????`
(all-`?`) → every non-deleted, non-vol-label entry matches (see §5.3 probe finding).

**Important:** COMMAND.COM builds the FCB and does the `*`→`?` expansion; we do NOT parse the
command line or expand `*`. We only honour `?` in the already-built FCB name field. Verify at
build (§5.3) whether DIR-no-arg issues `???????????` (all-wildcard) or a concrete pattern.

## 5. New work cell(s)
### 5.1 `BDOS_SRCHIDX` — the persistent search-position index (NEW)
- **Holds:** the absolute root-directory entry index (0-based, 0..rootEnts-1) of the NEXT
  entry to examine on the following SNEXT. SFIRST sets it to (first-match index + 1); each
  SNEXT resumes there and updates it to (its-match index + 1). A word (rootEnts ≤ 254, but a
  word is cleaner for the `>>4` sector math and cheap).
- **Why safe/necessary:** SNEXT MUST resume where SFIRST/the prior SNEXT stopped — the
  search state has to persist across separate BDOS calls, and the entry registers carry only
  fixed kernel pointers (§2.3), so the state has nowhere else to live. It is OUR OWN design
  cell (like `BDOS_RECIDX`/`BDOS_BYTESLEFT`), documented in PROVENANCE.md.
- **Placement (no collision — checked against equates.inc + init.asm):** the scratch map is
  `$E4A0..$E55D` (FAT + BDOS + HOOK_SLOT), then `WBUF` at `$E560..$E75F`, then the
  interrupt/CONIN scratch at `$E760+`. There is a **2-byte free gap at `$E55E..$E55F`**
  (after `HOOK_SLOT` `$E55D`, before `WBUF` `$E560`) — the same kind of gap `HOOK_SLOT`
  itself was slotted into ("in the `$E55D` gap … before WBUF"). Propose
  **`BDOS_SRCHIDX equ $E55E` (word)**. Confirm at build it does not overlap WBUF's `$E560`
  and that nothing writes `$E55E..$E55F` (grep clean this span). If a second scratch cell is
  needed (e.g. a saved runtime-DTA base, per §4.1's open item), take it from the free
  `$E76x`/`$E7xx` region below `DRV_TRAMP` ($E800) that CONIN scratch already draws from.
- **Lifetime:** DOS-phase only; dead during BASIC/loader phases like the other BDOS scratch.
  No init-time build needed (SFIRST always sets it before any SNEXT reads it).

### 5.2 Cells NOT to reuse (collision guard)
- `FAT_DIRSEC`/`FAT_DIRREM` ($E4BB/$E4BD): used by `fat_find` (loader Open) AND
  `fat_dir_create` (write path). We recompute them from `BDOS_SRCHIDX` at each entry rather
  than persist them → no cross-surface aliasing.
- `BDOS_DTA` ($E4C0), `BDOS_RECIDX`, `BDOS_BYTESLEFT`, the write cells: the PRIVATE loader
  BDOS surface (char doc §1). The runtime dir-search uses the KERNEL's DTA, not `BDOS_DTA`.
- `FAT_NAMEPTR` ($E4B9): `fat_find`'s search-name pointer. If `dirscan_match` reuses
  `name_cmp` it may reuse `FAT_NAMEPTR` as the pattern pointer WITHIN a call (transient), but
  must not assume it survives across calls — the pattern is re-established each entry.

## 6. Net-zero / placement plan (VERIFIED this span)
- **Entries are free `$00` pad.** `build/disk.rom` bytes confirmed (our OWN rom — allowed):
  `$4FB8` = `00 00 00 00 00 00 00 00`, `$5006` = `00 00 00 00 00 00 00 00`. Both sit inside
  the large `$4EE1..$50A9` `$00` fill (the `ds $50A9-$` in kernel.asm). So each has **far
  more than the 3 free bytes** a `jp` veneer needs — net-zero, no canonical-address shift
  (same check M17/M18 did for `$50D5`/`$50C4`, which are in this very fill region). **Flag:**
  since `$4FB8`/`$5006` are BELOW the existing `$50A9`/`$50C4`/`$50D5`/`$50E0` veneers, the
  new `jp` veneers must be inserted as additional `ds $4FB8-$ / jp sfirst_body` and
  `ds $5006-$ / jp snext_body` anchors in the SAME descending-address `ds`-anchor chain in
  kernel.asm (currently `$4E4B`→`$4EDE`→`$50A9`→`$50C4`→`$50D5`→`$50E0`); `$4FB8` and `$5006`
  slot in in address order between `$4EDE` and `$50A9`. Each anchor consumes existing pad, so
  the downstream anchors are unaffected. Verify with a 3-pass `--sym` object build that
  `disk.rom` stays 16384 B.
- **Bodies go in the free tail** (kernel.asm, after `curdrv_body`), like all prior bodies.
  Headroom checked: current last non-zero ROM byte is `$7A8C` → **1395 free-tail pad bytes**
  before the `ds $8000-$` — ample for `sfirst_body`+`snext_body`+`dirscan_match`+
  `name_cmp_wild` (~150-250 B est.). Confirm the pad shrinks, no overflow.
- **`BDOS_SRCHIDX`** consumes the free `$E55E..$E55F` RAM gap — RAM, not ROM, so no size
  impact.

## 7. Acceptance criteria (falsify-first — cheapest disproving experiment first)
1. **Screen arbiter (primary):** `screen --machine both --keys '\rDIR\r' --keys-at 22
   --settle 60` → OURS renders the SAME directory listing as stock (the file list +
   `nn files` + `375808 bytes free` + a fresh `A>`), no hang, no blank screen. Ideally the
   name-table HEX rows match stock byte-for-byte.
2. **Call-sequence parity past n=33:** `callseq --at 0x0100 --log 0x0005 --maxhits 90
   --keys '\rDIR\r' --keys-at 22 --settle 60` → ours matches stock past n=33 (the search call
   returns exhausted, so the SETDTA/SNEXT loop terminates and CONOUT of the listing begins at
   n=34), aligned to the return to `A>`. (Current state: ours diverges into an endless
   `$1A`/`$12` loop at ~n=34 — see §2.4.)
3. **Entry-count + return contract:** `callseq --log 0x4FB8` → ours hits it the same count
   as stock (1); `callseq --log 0x5006` → ours matches stock's count (6 on this disk) and
   ours' final SNEXT returns the exhausted code (A=$FF) that terminates the loop.
4. **Wildcard correctness:** with a `DIR` that lists all files, every non-deleted file on
   test.dsk appears exactly once (no phantom repeats — the current bug — and no drops).
5. **Tier-1 green + size:** `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300; `disk.rom`
   == 16384 B; no canonical-address shift (entries consume existing `$00` pad, §6).
6. **No regression:** the 27/27 boot BDOS parity (`--keys '\r'`) still holds; no int-storm
   (`dosboot_triage` OK); M13/M15/M17/M18/OI-3 repros still pass (their probes unchanged).

## 8. Risks / edge cases
1. **Empty directory / no match.** SFIRST on a dir with no matching entry (or an all-`$00`
   root dir) must return A=$FF immediately (no DTA write). `dirscan_match` hits the `$00`
   end-mark on the first entry → A=$FF. COMMAND.COM's `DIR` then prints its "no files"
   path. Verify with a fresh EMPTY asset disk (NOT committed test.dsk).
2. **Exactly one entry.** SFIRST returns A=$00 (that entry copied, `BDOS_SRCHIDX`:=1); the
   next SNEXT resumes at index 1, finds the `$00` end-mark, returns A=$FF. The listing shows
   one file then terminates. Guard: the `>>4` sector recompute must handle `BDOS_SRCHIDX`
   landing exactly on a sector boundary and the case `FAT_DIRREM` reaching 0 mid-scan.
3. **Wildcard patterns from DIR — VERIFY, don't assume.** Whether COMMAND.COM's `DIR` (no
   arg) issues `???????????` (all-wildcard) or a concrete `*.*`-expanded FCB is a **build-time
   probe question**: gate a `readwatch`/`capture` on OUR OWN memory (or the established
   search FCB region) after our own SFIRST call, or observe the FCB the kernel set up, to pin
   the actual pattern before finalising `name_cmp_wild`. The `?` rule is the published
   contract; the specific pattern DIR uses is an empirical check. `DIR FILENAME.EXT` (a
   concrete name) and `DIR *.COM` (COMMAND.COM expands `*`→`?`) are secondary patterns — the
   body handles all three uniformly since it only sees literal-or-`?` FCB bytes.
4. **"Exhausted" code must match what stock returns.** §2.4 defers the EXACT exit code/flags
   to the falsify-first build (A=$FF is the published value + the behaviourally-required
   "terminate the loop" signal). If A=$FF alone doesn't terminate stock's loop identically,
   re-pin the exact exit register/flag black-box and reproduce it (our own op). Do NOT guess
   beyond the published A=$00/$FF without a concrete probe.
5. **Runtime DTA source (§4.1 open item).** The body must write the 32-byte image to the
   KERNEL's runtime DTA (the one DIR's formatter reads — char doc shows runtime `$1A` SETDTA
   `DE=D403`/`D3DB`), NOT our private `BDOS_DTA`. Pin the runtime-DTA source cell/pointer as
   the first build step (one-sided `capture`/`readwatch` on our own memory).
6. **`fat_mount` cost per call.** Calling `fat_mount` on every SFIRST/SNEXT re-reads the boot
   sector (an FDC op) 7× for a 6-file listing. Acceptable for correctness first; if the
   arbiter shows a visible delay, cache the mount (a "mounted" flag) — but that is an
   optimisation, not required for acceptance. `fat_find`/`bdos_open` already re-mount per
   Open, so this matches existing behaviour.
7. **Attribute filter (§4.4).** Confirm at build whether SFIRST should surface volume-label /
   subdirectory entries. test.dsk (flat MSX-DOS-1 720K) has neither, so `fat_find`'s
   `attr&$18` skip gives the correct acceptance result; DOCUMENT the chosen filter and its
   published-contract basis.

## 9. Clean-room status
- SFIRST/SNEXT semantics, the `?` wildcard rule, and the 32-byte directory-entry image
  format: published MSX-DOS-1 BDOS function table + FCB/directory spec (map.grauw.nl, MSX2 TH
  §BDOS/§FCB, MSX Datapack, CP/M 2.2 FCB match rule). Cited, not decoded.
- `$4FB8`/`$5006` as the kernel's SFIRST/SNEXT page-1 CALL targets, and their entry/exit
  register contract: BLACK-BOX only — `callseq --log`/`capture --at` entry-PC gating + call
  counts + entry-register snapshots (§2), plus our own ROM's NOP-padding check (§6). Stock's
  routine internals (the 108/101 page-1 PCs) were **NOT** decoded — only entry PCs
  (addresses, not bytes) and visit counts were observed.
- The directory-search ALGORITHM is OUR OWN design reusing our own `fat_mount`/`fat_find`/DPB
  layer + our own new `BDOS_SRCHIDX` cell. We are implementing the documented CONTRACT (given
  the FCB pattern, find matching dir entries), NOT reverse-engineering stock's algorithm.
- `build/disk.rom` byte reads (`$4FB8`/`$5006`) are reads of OUR OWN rom — allowed.
- No stock ROM / loaded MSXDOS.SYS / COMMAND.COM CODE bytes were read to reach any conclusion
  in this spec.

## 10. Status / next (for sign-off)
**Spec complete (characterise + design). STOP for sign-off** (per
[[spec-before-implementation]] — new-routine class, not veneer-class). On go-ahead, the build
order is: (1) pin the runtime-DTA source + the exact exit code (§2.4/§4.1/§5, first falsify
step), (2) add `BDOS_SRCHIDX` + the two `jp` veneers + the three tail bodies, (3) verify §7,
(4) commit. **NOTE the still-open non-M19 tracks from the char doc** (do NOT fold in): the
rest of the FCB cluster (`$10/$14/$23/$26/$27`) is blocked on the BDOS-exerciser `.COM`
([[bdos-exerciser-com-test]]), specced separately.
