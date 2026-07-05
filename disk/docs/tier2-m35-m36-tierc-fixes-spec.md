<!-- Copyright (c) 2026 Joost Yervante Damad; SPDX-License-Identifier: 0BSD -->
# M35 + M36 — Tier-C case 5 (FREN collision) + case 4 (WRRND past-EOF) fixes

Status: **SPEC — M35 ready; M36 pending investigation.** User chose **fix to
byte-identity** for both (Tier-C cases 4 & 5). Case 3 (dir-full) already landed
byte-identical.

Both are adversarial-corner divergences the happy-path gate never reached, found by
the new Tier-C exercisers (bdosx6/bdosx7) and confirmed in OUR OWN source.

## M35 — FREN ($17) rename-collision (case 5)

### Characterisation (bdosx7 differential, both machines)
Fixture: two files `RENSRC.TMP` + `RENDST.TMP`. Exerciser: FREN RENSRC→RENDST
(RENDST already exists), then FOPEN RENSRC, then FOPEN RENDST.
- **Record 0 FREN:** stock **A=FF** (rejects the collision), ours **A=00** (renames
  anyway). L: stock FF (mirror of A), ours 0A.
- **Record 1 FOPEN RENSRC:** stock **A=00** (source survived — rename refused), ours
  **A=FF** (source gone — ours renamed it away).
- Record 2 FOPEN RENDST: both A=00; FCB first-cluster/dirloc differ (ours opened the
  renamed file, stock the original).

**Bug:** ours corrupts the namespace — it renames onto an existing name, producing a
duplicate directory entry; stock refuses.

### Root cause (OUR source)
`fren_body` ([fat.asm:1249](../fat.asm)) does `fat_mount` → `fat_find` on the OLD
name (FCB+1) → overwrites that dirent's name with the NEW name (FCB+17) →
`write_sector`. **No check that the new name already exists.**

### Fix
Insert a collision pre-check in `fren_body`, after `fat_mount` and BEFORE the
old-name `fat_find`: `fat_find` on the NEW name (FCB+17); if `Cy=0` (found) →
`jp fren_collision` where `fren_collision` shares `fren_miss`'s body
(`xor a; ld ($F306),a; scf; ld a,$FF; ret`). Exit A=$FF; the kernel's M20 mirror
sets L:=A=$FF → matches stock's A=FF/L=FF exactly. If the new name is NOT found,
fall through to the existing old-name find + rename (byte-unchanged).

- `fat_find` uses SECTOR_BUF + FAT_DIRSEC/FAT_NAMEPTR; calling it twice is safe (the
  second call for the old name re-establishes all state; the first is a pure
  existence test). Confirm `fat_find` preserves nothing the collision path needs.
- Placement: `fren_body` is in disk/fat.asm's relocatable tail; the added ~10 bytes
  grow it in place (net-zero canonical — only `jp fren_body`'s veneer target, an
  operand, may recompute; no `k_*` moves). Verify.

### Expected result
bdosx7 differential converges: record 0 FREN A=FF/L=FF; record 1 FOPEN RENSRC A=00
(source survives); record 2 FOPEN RENDST opens the original (first-cluster matches).
Any residual date/dirloc bytes are the documented allowlist classes. Fold BDOSX7
into `make bdos-acceptance`.

### Host test
Add `test_fren_collision` (mirror `test_fat_dir_create`): a FAT image with the new
name present → fren returns Cy=1/A=FF and leaves both dirents intact; new name
absent → rename succeeds. Wire into `make unit-test`.

## M36 — WRRND ($22) past-EOF file-size extension (case 4)

### Characterisation (bdosx6 differential, both machines)
Fixture: 256-byte `SHORT.DAT` (2 records, 1 allocated 1024-B cluster). Exerciser:
FOPEN → set FCB+14=128 → RDRND r0=5 → WRRND r0=5 → FCLOSE.
- **WRRND r0=5 (offset 640, past 256-B EOF but inside the allocated cluster):** both
  return **A=00**, but the FCB **file-size** field ends at stock **768** (=(5+1)*128),
  ours **256** (unchanged) — ours does not grow the file.
- RDRND r0=5: both **A=01** (EOF); delivered read buffer byte-identical; only the
  ancillary L differs (stock mirrors L:=A=01, ours L=00).
- Ancillary FCB diffs: +14 (stock 00 / ours 80), +20/+21/+24/+25 (documented
  date/devid/dirloc classes).

**Gap:** ours' WRRND writes the record's data but never records the file-size
extension → FCLOSE/read-back sees the past-EOF write dropped. (M26 explicitly scoped
past-EOF FAT-growth out; this is the within-allocated-cluster size bump, which is
tractable.)

### Mechanism (investigation DONE, key finding changes scope)
- File-size field = **FCB+16..19** LE, in both the user FCB and the $DA40 kernel copy
  ([fat.asm:1180-1188](../fat.asm) seeds it from `FAT_FILESIZE` at FOPEN). The
  captured 768 vs 256 lives there (diverging byte +17).
- The kernel does a generic **copy-back $DA40 → user FCB** after the call (same path
  that already carries WRRND's CR side effect `ix+32:=ix+33`, [kernel.asm:3036](../kernel.asm)),
  so `wrrnd_body` updating **`ix+16..19`** propagates to the user FCB — no dispatcher
  change.
- **Data already persists** (traced: `write_sector` lands record 5's 128 bytes at
  offset 640 in the allocated cluster); the ONLY gap is the size not being recorded.
- **DECISIVE FINDING (read-only artifact oracle, 2026-07-05): stock persists the
  extended size to the on-disk DIRECTORY, not just the FCB.** Ran stock in-place on
  the fixture → `SHORT.DAT` dirent size went **256 → 768**. **⇒ an FCB-only bump
  would be a VACUOUS fix** (RAM differential passes, disk still wrong — the exact
  "RAM gate is blind to disk writes" trap). M36 MUST also update the dirent, and the
  verification MUST round-trip the disk.

### Fix (SCOPE ↑ from an FCB bump to FCB + directory persistence)
In `wrrnd_body`, on the success path after `write_sector` ([kernel.asm:3035](../kernel.asm)),
before the CR side effect:
1. `newsize = max(oldsize, (r0+1)*RECSIZE)` — oldsize from `ix+16..19`; compute
   `(r0+1)` as a 16-bit value BEFORE the ×128 shift (r0=255 safe); +18/+19 stay 0
   (max 32768). If `newsize <= oldsize` → skip everything (happy-path within-file
   WRRND, incl. BDOSX3 rec18-20, is byte-unchanged).
2. If extending: write `ix+16..19 = newsize` (FCB copy → user via copy-back).
3. **Persist to the dirent** the same way `fren_body` patches a name in place
   ([fat.asm:1249](../fat.asm)): `fat_find` the file (name at `ix+1`) → HL = &dirent
   in SECTOR_BUF, `FAT_DIRSEC` = its sector; write `newsize` to **dirent+28..31**
   (`DIRENT_FILESIZE`), leaving +26 first-cluster and the name intact (do NOT use
   `fat_dir_update` — it rewrites first-cluster from BDOS_WRFIRST, which WRRND must
   not touch); `write_sector (FAT_DIRSEC)`. On `fat_find`/write error → `wrrnd_ioerr`.
   - Ensure geometry is mounted before `fat_find` (rrnd_position's `fat_open` path;
     add `fat_mount` if needed, as `fren_body` does). fat_find/write_sector reload
     SECTOR_BUF — safe, the record sector is already persisted.
   - Only within-allocated-cluster extension is in scope (r0 within the existing
     chain). r0 beyond the allocated chain still returns the M26 out-of-scope
     `rrnd_pos_err` A=$02 (FAT growth for random write remains an M26 non-goal;
     the fixture's r0=5 stays inside cluster 0).

### +14 and RDRND-L (ancillary)
- **+14** (CP/M S2 / repurposed record-size field): stock writes its S2 derivation
  (0 for r0≤255) → 00; ours keeps the exerciser's poked 128. **Allowlist** (internal
  field, unrelated to the size bug) — matching it would clobber a documented WRBLK
  input field. Documented decision, not folded into the fix.
- **RDRND L-mirror** (stock L:=A on the EOF path, ours L=0): ancillary undefined
  register; **allowlist** (contract pins A). Optionally a 2-byte `ld h,0/ld l,a` at
  the EOF exits — tag-along, not required.

### Exerciser enhancement (non-vacuous verification)
Enhance `bdosx6.asm`: after FCLOSE, save the post-WRRND FCB size, then add **record 4
= re-FOPEN SHORT.DAT** (a fresh FOPEN reloads size from the dirent). Capture region
covers regs (all 5 return codes) + the reopened FCB size (proves the DIRENT holds
768) + the saved post-WRRND size (proves the in-memory FCB held 768). This makes the
gate differential see the disk persistence — not a RAM-only pass. Update
`build_bdosx6_disk.py`'s capture region accordingly.

### Host test
`test_wrrnd_extend` (mirror `test_wrblk_extend`): past-EOF (within-cluster) WRRND
grows FCB+16..19 to (r0+1)*128 and patches the dirent size; within-file WRRND leaves
size unchanged. Wire into `make unit-test`.

### Verification plan (both M35 + M36)
1. bdosx7 (M35) + bdosx6 (M36) differentials 0-byte-diff (bar allowlisted
   date/dirloc + M36's +14 / RDRND-L ancillary registers). **M36 non-vacuous:** the
   enhanced bdosx6 re-FOPEN record must show the reopened size = **768 on ours** (=
   stock), proving the DIRENT was persisted — not just the RAM FCB.
2. **Disk-artifact cross-check:** read the ours-run `SHORT.DAT` dirent size directly
   (read-only oracle, as the scope-finding check did for stock) → 768. This is the
   real anti-vacuity guard for M36.
3. Happy-path non-regression: `make bdos-acceptance` still green on
   BDOSX/2/3/0/4/5 (FREN happy-path = BDOSX3 rec14; RRND/WRRND happy-path =
   BDOSX3 rec18-20 — within-file WRRND, newsize==oldsize, skips the M36 branch). Fold
   BDOSX6 + BDOSX7 in.
4. WRBLK/RDBLK round-trips unchanged. `make unit-test` green (+ new host tests).
5. Tier-1: disk.rom 16384 B, 0 `k_*` moved; oracle md5 unchanged.

### Section 6 — Results — DONE, byte-identical (2026-07-05)

Implemented by Sonnet 5, independently verified by Opus.

**M35 (FREN collision):** ~12-byte in-place pre-check in `fren_body`
([fat.asm:1264](../fat.asm)) — `fat_find` on FCB+17, `jp nc, fren_miss` on hit.
bdosx7 differential: **record 0 FREN now A=FF** (refuses the collision, was A=00),
**record 1 FOPEN RENSRC A=00** (source survives, was A=FF), record 2 intact. Diff
dropped 8→3 bytes, all allowlisted classes (FCB+25 dirloc + FREN H/L undefined —
contract pins A, same class as BDOSX3 rec14).

**M36 (WRRND past-EOF):** new `wrrnd_extend` in the free corridor
([kernel.asm:1882](../kernel.asm)), called after the record `write_sector`
([kernel.asm:3128](../kernel.asm)). Grows `ix+16..19` = max(oldsize,(r0+1)*128) AND
patches the on-disk dirent+28..31 (the `fren_body` `fat_find`-in-place idiom; NOT
`fat_dir_update`, to leave first-cluster untouched). Sonnet caught + fixed a real bug
mid-implementation (the `wre_noext` early-outs originally leaked the size-compare's
`Cy=1` as a false I/O error on every within-file WRRND — the new host test caught it).
bdosx6 differential: **post-WRRND FCB size = 768 both** (`wrsize` cell 0-diff),
**re-FOPEN'd size = 768 both** (FCB+16..19 0-diff — proves the DIRENT was persisted).
**Anti-vacuity cross-check:** direct read of the ours-run `SHORT.DAT` dirent = **768**
(= stock). Diff dropped 7→4 bytes, all allowlisted (FCB+20/21 date, +25 dirloc,
RDRND L-mirror). RDRND EOF (A=01) + delivered read data already byte-identical.

**Gate:** `make bdos-acceptance` = **11/11 converged** (BDOSX6 both regions + BDOSX7
folded in with the documented-class allowlists; all happy-path exercisers still
pass — no regression). **Unit tests 34/34** (+ `test_fren_collision`,
`test_wrrnd_extend`). **Tier-1:** disk.rom 16384 B; 0 `k_*` canonical moved; FDC
window `$7F80-$7FBF` clean $00 (fat_find_body shifted to `$7F3E`, 66 B clear of the
guard, which never fired). Oracle `test.dsk` md5 unchanged.
