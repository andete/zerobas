<!-- Copyright (c) 2026 Joost Yervante Damad; SPDX-License-Identifier: 0BSD -->
# M34 — WRSEQ disk-full onset parity (Tier-C case 2, P2)

Status: **SPEC — awaiting sign-off.** Investigation DONE (clean re-characterisation
+ mechanism pinned in our own source). Fix scope chosen by the user: **byte-identity**.

## 0. Summary

On a 100 %-full volume, sequential write (`$15` WRSEQ) of a freshly-created file
diverges from the National CF-3300 in two coupled ways. This spec makes ours
byte-identical to stock in every **observable** respect (BDOS return registers +
final on-disk artifact) via a single localised change to the write path; the
second divergence resolves automatically as a downstream consequence.

## 1. Clean characterisation (both machines, 2026-07-05)

Fixture: `build_bdosx4_disk.py` → 715-cluster 720 KB disk, **0 free clusters**,
1024-byte clusters. Exerciser `bdosx4.asm` (already carries the IX-preservation
fix, so the earlier "stock terminates the program" reading — an artifact of the
old IX-walk bug — is gone): FMAKE a fresh `BDOSXF.TMP`, SETDTA, WRSEQ ×12,
FCLOSE. Register buffer decoded (`tag,A,B,C,D,E,H,L` per 8-byte record):

| call        | stock A | ours A | note |
|-------------|:-------:|:------:|------|
| `$16` FMAKE |   00    |  00    | dir slot created (first cluster 0, size 0) |
| WRSEQ #1    | **01**  |  00    | stock disk-full at the FIRST record; ours "succeeds" |
| WRSEQ #2    |   01    |  00    | |
| WRSEQ #3    |   01    |  00    | |
| WRSEQ #4    |   01    | **01** | ours' first disk-full — at its 512-B sector-flush boundary |
| WRSEQ #5–12 |   01    |  01    | both stay full |
| `$10` FCLOSE| **00**  | **FF** | stock closes the 0-cluster file cleanly; ours errors |

Two divergences:

- **D1 — onset lag.** Stock returns disk-full (`A=01`) at WRSEQ **#1**; ours only
  at **#4**. Neither corrupts data (both refuse to overflow the disk).
- **D2 — FCLOSE return.** Closing the never-allocated file: stock `A=00`, ours `A=FF`.

This corrects the old `tier2-tierC-spec.md` §2 numbers (which said stock onset at
#2 and "stock terminates") — those came from the contaminated exerciser.

## 2. Mechanism (pinned in OUR source — clean-room)

**D1 root cause.** `bdos_seqwrite_body` ([kernel.asm:2883](../kernel.asm)) copies
each 128-B record into `SECTOR_BUF` and only calls `fat_flush_data_sector` when
`BDOS_WRBUFLEN` reaches 512 (line 2620). Cluster allocation happens *inside* the
flush (`ffds_nopad_body` → `ffds_alloc` → `fat_alloc_cluster`). So records #1–3
(buflen 128/256/384 < 512) return `A=00` without ever touching allocation; record
#4 triggers the flush → `fat_alloc_cluster` → no free cluster → `A=01`. Stock
allocates the fresh file's first cluster **eagerly on record #1**, so it fails
immediately.

`ffds_nopad_body`'s allocation decision (kernel.asm:523) is exactly:

```
needs-a-new-cluster  ==  (BDOS_WRCLUS == 0)            ; no cluster yet (fresh file)
                      ||  (BDOS_WRSECIDX >= FAT_SECPERCLUS)  ; current cluster full
```

**D2 root cause — DOWNSTREAM of D1.** `bdos_close_write`
([driver.asm:697](../driver.asm)): if `BDOS_WRBUFLEN > 0` it flushes the partial
sector before the dir update. On the full disk ours buffered 384 B (records #1–3),
so FCLOSE's flush calls `fat_flush_data_sector` → allocation fails → `Cy=1` →
`bdos_close_err` → `A=FF`. Stock never buffered anything (fail-fast at #1), so its
FCLOSE has nothing to flush → clean `fat_dir_update` (first cluster 0, size 0) →
`A=00`. **If ours never buffers the unwritable records, `BDOS_WRBUFLEN` stays 0 at
FCLOSE, the flush is skipped, and FCLOSE returns `A=00` — D2 disappears with no
FCLOSE-specific change.** (Same shape as the "fix the derail, the downstream storm
resolves" lesson.)

## 3. The fix — eager free-cluster **availability** pre-check

### 3.1 Design

Add, at the **top** of `bdos_seqwrite_body` (after the `BDOS_WRMODE` gate, BEFORE
the `ldir` that buffers the record), a check that fires only at a **sector start**
that would need a **new cluster**, and, when it does, verifies a free cluster
exists — returning `A=01` (disk full) *before* buffering if none:

```
    ; --- M34: eager disk-full onset (byte-identical to stock #1 onset) ---
    ld   hl,(BDOS_WRBUFLEN)
    ld   a,h
    or   l
    jr   nz, .buffer            ; mid-sector: cluster already validated at its start
    ; sector start — does the pending flush need a NEW cluster?  (mirror ffds_nopad_body)
    ld   hl,(BDOS_WRCLUS)
    ld   a,h
    or   l
    jr   z, .needclus           ; no cluster yet (fresh file)
    ld   a,(BDOS_WRSECIDX)
    ld   hl,FAT_SECPERCLUS
    cp   (hl)
    jr   c, .buffer             ; room in current cluster -> no new cluster needed
.needclus:
    call fat_have_free_cluster  ; Cy=0 a $000 cluster exists; Cy=1 none
    jr   nc, .buffer
    ld   a,$01                  ; disk full — return BEFORE buffering / byte-count advance
    ret
.buffer:
    ; ... existing body (ldir into SECTOR_BUF, advance WRBUFLEN, wrbytes_add_recsize, flush-at-512) ...
```

Key property: on any disk that **has** a free cluster the check passes and control
falls into the *unchanged* existing body — so the happy path (BDOSX3 records 1–9
byte-identity, multi-cluster allocation) is provably untouched. The check only
changes behaviour when there is genuinely no free cluster, and then only to
surface `A=01` at the same record stock does. Because the check runs only at
sector starts that need a new cluster (once per cluster), it adds no per-record
cost on the happy path.

### 3.2 New helper — `fat_have_free_cluster` (scan-only)

A non-committing sibling of `fat_alloc_cluster`: scan FAT copy 0 from cluster 2 to
the last data cluster for any `$000` entry. Return `Cy=0` if one exists, `Cy=1` if
none. It does **not** mark, does **not** touch `FAT_ALLOCHINT`, and reuses the
existing 12-bit unpack `fac_entry_from_wbuf` (shared straddle-correct helper) plus
`fat_total_clusters`. Placed in the kernel free corridor (≥3.7 KB free at
`$66f6`). ~40 bytes. It scans from cluster 2 (not the M30 hint) so "none free" is
answered correctly even after deletions; the common non-full case finds a free
cluster quickly.

### 3.3 What does NOT change

- `fat_flush_data_sector`, `fat_alloc_cluster`, `ffds_nopad_body` — untouched (the
  real allocation still happens at flush; the M34 check only *gates* entry).
- `bdos_close` / `driver.asm` — untouched (D2 resolves via the `WRBUFLEN==0` path
  that already exists at driver.asm:704).
- `bdos_seqread` / RDSEQ, RRND, boot mini-BDOS — untouched (the check lives in the
  write body only, reached solely via `wrseq_body`'s write branch).
- No canonical address moves; the `$46EE → bdos_seqwrite` veneer and every pinned
  entry are net-zero. `bdos_seqwrite_body` is in the relocated-bodies free region,
  so it can grow in place.

## 4. Design note — availability-check vs. true-eager (why this design)

Stock actually *reserves* (marks EOC) the cluster in the FAT at record #1. The M34
availability-check instead only **confirms a free cluster exists** at record #1 and
leaves the real reservation at the flush (record #4), exactly as today.

- **Observationally byte-identical.** The differential compares BDOS return
  registers (now identical: onset #1, all-`01`, FCLOSE `00`) and the **final**
  on-disk artifact after FCLOSE (identical: on a full disk nothing is allocated on
  either machine; on a non-full disk both allocate the same clusters — already
  proven byte-identical by BDOSX3 + M30). The only difference is the FAT's
  *intermediate* reservation state between records #1 and #4 on a non-full disk,
  which is **unobservable** through any MSX-DOS-1 BDOS call (single-tasking; no
  concurrent FAT reader) and, on a crash mid-write, leaves ours *cleaner* (stock
  leaks an orphaned reserved cluster; ours reserves nothing).
- **Lower risk.** The happy path falls through into the byte-unchanged existing
  body, so BDOSX3's proven WRSEQ byte-identity cannot regress. True-eager would
  restructure `fat_flush_data_sector` (allocate-then-write split) — real regression
  risk on a milestone-closed (M24/M25) shared write path that also carries the
  just-landed M33 write-back.

**Recommendation: availability-check.** If the reviewer wants the FAT's
intermediate reservation state to also match stock (true-eager), say so at sign-off
and the spec grows a §3.4 for the flush restructure + its extra verification.

## 5. Verification plan (Opus, independent — never trust self-reports)

1. **D1+D2 differential (the oracle):** rebuild `bdosx4` fixture, run
   `disk_probe_diff.py capture --at <done> --arm-check-val <sig> --machine both
   --mem <regs>:0x80`. **Both machines must reach the anchor**, and the 16×8
   register buffer must be **0-byte-diff** — i.e. ours' WRSEQ #1 = `A=01`, #1–12 all
   `01`, FCLOSE `A=00`. (Ours is slow on the full-disk scan — allow ≥120 s settle,
   confirmed t≈71 s in characterisation.)
2. **Happy-path non-regression (critical):** `make bdos-acceptance` unchanged
   (BDOSX3 WRSEQ records 1–9 still 0-byte-diff; gate count unchanged). Plus the
   WRSEQ/WRBLK disk-artifact round-trips (`disk_probe_wrblk_roundtrip.py`, M31
   `disk_probe_rdblk_roundtrip.py`) still pass — the write path still allocates the
   same clusters and writes the same data on a non-full disk.
3. **Host unit test:** add `test_fat_have_free_cluster` (free-present → NC;
   all-full FAT → C) alongside the existing `test_fat_alloc_cluster`. `make
   unit-test` green.
4. **Tier-1:** `disk.rom` exactly 16384 B; baseline symbol diff shows **0 `k_*`
   canonical entries moved** (only `bdos_seqwrite_body` grows + one new corridor
   label); FDC window clean; `$46EE` veneer intact.
5. **Boot:** COMMAND.COM still boots (the write path is on the DOS boot surface).
6. Oracle `test.dsk` md5 unchanged `86e840b868810a11f15278ac3d6bb3ff`; git clean of
   any /tmp fixture write-back.

### 5.1 Honest prediction (to be confirmed/corrected in §6, per the M31/M32 discipline)
D2 (FCLOSE `A=00`) is **predicted** to green automatically from the D1 fix (§2
reasoning is airtight from source, but unverified until implemented). If it does
not, a targeted FCLOSE change is added and this section is corrected.

### 5.2 Gate wiring decision
`bdosx4` is currently OUT of `make bdos-acceptance`. Once the differential is
0-byte-diff, **fold BDOSX4 into the gate** (it becomes a real, non-vacuous
disk-full assertion with no allowlist needed — the whole point of the fix). Confirm
at sign-off.

## 6. Results — DONE, byte-identical (2026-07-05)

Implemented by Sonnet 5, independently verified by Opus (never self-reports).

**Implementation** (disk/kernel.asm only; no equates/fat.asm/Makefile change):
- The eager pre-check inserted at the top of `bdos_seqwrite_body` exactly per §3.1
  (labels `bsw_m34_needclus`/`bsw_m34_buffer`); the existing body is byte-for-byte
  unchanged below `bsw_m34_buffer`.
- `fat_have_free_cluster` placed in the free corridor at **$66F6** — a faithful
  mirror of `fac_loop_body`'s proven scan (same FAT_WRTMP/WRTMP2/BYTEIDX/PARITY/
  FATSTART math + `fac_entry_from_wbuf`), scanning from cluster 2, returning `Cy`
  instead of claiming; never calls `fat_write_fat_entry`, never touches
  `FAT_ALLOCHINT`/`FAT_CURCLUS`/`FAT_CLUSSEC`. One correctness detail beyond the
  spec: a `pop hl` on the read-error exit to balance the loop's `push hl`.

**The oracle — bdosx4 differential (both machines):** register buffer **0 of 128
bytes differ**. So ours now matches stock exactly:
- **D1 fixed:** disk-full (`A=01`) at WRSEQ **#1**, all of #1–12 `01`.
- **D2 fixed (prediction CONFIRMED):** FCLOSE `A=00` — resolved automatically by the
  D1 fix, with **no FCLOSE-specific change**, exactly as §2/§5.1 predicted (ours
  never buffers → `WRBUFLEN=0` → FCLOSE skips the failing flush → clean dir update).
- Bonus: ours now reaches the anchor faster (t≈30 s vs 71 s pre-fix — fail-fast, no
  slow buffered flush).
- Residual: the **live** `AF` at the `done` anchor differs (stock `0093`, ours
  `0044`) — but that decodes to `A=$00` on **both**; only the Z80 **F** flags byte
  differs. `F` is not part of any BDOS return contract (only `A` is), the exerciser
  records A/B/C/D/E/H/L but not F, and the gate classes a live-register-only delta
  as benign epilogue. Non-divergence.

**Happy-path non-regression:** `make bdos-acceptance` **7/7** converged (BDOSX3
WRSEQ records 1–9 + second-cluster allocation still 0-byte-diff; DTA region
0-byte-diff). WRBLK/RDBLK disk-artifact round-trips unchanged (within/extend/multi
MATCH; del_realloc/rr24/shrink are the pre-existing, documented, accepted
divergences — M34 provably cannot touch them: its code is reachable only via
`bdos_seqwrite_body`, the $15 WRSEQ / boot-mini-BDOS write worker; WRABS $30 and
WRBLK $26 are separate bodies). `make unit-test` **32/32** (new
`test_fat_have_free_cluster`: free-present→NC, all-full→C, hint-untouched,
no-write). 

**Gate wiring:** BDOSX4 folded into `make bdos-acceptance` (`EXERCISERS`), no
allowlist needed (0-byte-diff). `build_bdosx4_disk.py` printed settle bumped 60→90
(post-fix anchor at t≈30 s; margin for CI host-load). The disk-full corner is now a
standing regression guard.

**Tier-1:** `disk.rom` exactly **16384 B**; baseline symbol diff = **0 `k_*`
canonical entries moved** (the ~30 B `bdos_seqwrite_body` growth ripples through the
relocated bodies after it until the next `ds` anchor re-absorbs — veneer operands
recomputed by pasmo, all canonical addresses fixed; the $66F6 helper is absorbed by
the `ds $75A5` anchor with no downstream ripple). Oracle `test.dsk` md5
`86e840b868810a11f15278ac3d6bb3ff` unchanged; git clean of fixture write-back.
