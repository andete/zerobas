# M30 — fat_alloc_cluster next-free hint (kill the multi-cluster-alloc O(n²))

Status: **✅ DONE — implemented + verified 2026-07-04** (was: DRAFT → signed off → landed)
Motivating trigger: the M29 follow-up. M29 fixed WRBLK *positioning* (P); the
*allocation* quadratic (A) was explicitly deferred. This is A. User directed
"continue with A" (2026-07-04).

Clean-room: performance refactor of OUR OWN `fat_alloc_cluster`
([fat.asm](../fat.asm)) + a one-line reset in OUR `fat_mount`. No contract change;
the allocated-cluster sequence is **provably identical** to today's (byte-identical
to the CF-3300 oracle — see §4). No stock code read.

---

## 1. The defect — and its true (CPU-only) shape

`fat_alloc_cluster` (fat.asm:391) restarts its free-cluster scan at **cluster 2 on
every call**. N allocations in one operation (a WRBLK past-EOF extend, a long WRSEQ)
each re-scan 2..(first-free), so the operation is O(N²) in **FAT-entry tests**.

**IMPORTANT (corrected during verification — honest scope):** the quadratic is
**CPU-only, not I/O.** `fat_alloc_cluster` already caches the FAT sector within a
call (`FAT_WRTMP2`), so a from-2 scan reads each FAT sector *at most once per call* —
its **sector I/O is already linear in N**. The re-scan cost is entirely the Z80
instructions spent testing FAT *entries in RAM* (up to first-free, growing each call).

Measured before/after (`wrblk_perf.py --alloc`, M29 ROM vs M30 ROM, ONE wrblk_body
call extending a file by K new clusters):

| K | CPU(M29) | I/O(M29) | CPU(M30) | I/O(M30) | CPU× | I/O× |
|--:|--:|--:|--:|--:|--:|--:|
| 1 | 14,001 | 142 | 14,007 | 142 | 1.0× | 1.0× |
| 8 | 57,775 | 219 | 22,849 | 219 | 2.5× | 1.0× |
| 32 | 235,207 | 483 | 53,161 | 483 | **4.4×** | **1.0×** |

(Free region 64 clusters in. On a large/full disk with first-free past a FAT-sector
boundary — >341 clusters — M30 also shaves the extra per-call boundary read, but I/O
stays ~1.0× because data + multi-FAT-copy writes dominate the count; at K=32 with
first-free 400 in, CPU× reaches **9.2×**.)

**Consequence for expectations:** unlike M29's positioning fix (which cut *actual
sector accesses*, a real wall-clock win on floppy-speed hardware), A is a **CPU
optimization**. It does NOT reduce disk I/O, so it will NOT dramatically change
wall-clock for I/O-bound cases like the `rr24` 33-cluster extend (whose cost is the
sector I/O of writing 33 clusters, unchanged). A is worthwhile — 4–9× fewer Z80
instructions on large multi-cluster allocations, zero correctness risk, byte-
identical — but its real-hardware benefit is smaller than P's. The earlier
"rr24 ~80 s" figure was P's positioning cost, not this.

## 2. The investigation result that de-risks A

A next-free hint's feared cost was **free-invalidation correctness**: a hint left
above a just-freed cluster would either report false disk-full or diverge from
stock's allocation order. **That surface does not exist here**, because of two facts
established by reading every FAT-mutation site:

**(i) The complete free-site map (only two, both simple chain-free loops):**
- `wrblk_shrink` freeloop — kernel.asm:1368 (`de=0`; `fat_write_fat_entry`).
- `$13` DELETE `fdel_body` loop — kernel.asm:2313 (`de=0`; `fat_write_fat_entry`).
- `$16` create "truncate-if-exists" **orphans** the old chain (fat.asm:791-792,
  documented divergence) — it frees **nothing**.

**(ii) No single BDOS operation both frees-a-low-cluster and then allocates:**
- `wrblk_body`: shrink (frees, `HL==0`) **XOR** extend (allocates, `HL>0`) — the two
  paths are mutually exclusive within one call.
- `$13` delete: frees only. `$16` create: orphans, then makes an *empty* file (first
  cluster 0 — no allocation). WRSEQ/write & WRBLK extend: allocate only.

`fat_mount` runs **once at the start of every** BDOS file operation, before any
`fat_alloc_cluster`. So if the hint is **reset to 2 in `fat_mount`**, it only has to
persist across the allocations *within one operation* — and within one operation the
allocation sequence starts at 2 and never sees a free below where it has reached.
**⇒ zero free-site changes, no wrap-around, no free-invalidation surface.**

## 3. Design — per-operation next-free hint

### 3.1 New state (1 persistent-per-operation word)
```
FAT_ALLOCHINT   equ $E7FB   ; next cluster to try in fat_alloc_cluster's scan;
                            ; reset to 2 by fat_mount (per-operation lifetime).
```
(`$E7FB` is grep-clean, in the "clear of every other disk region" $E7E8-$E7FF gap,
just past the M28/M29 WRBLK cells $E7E8-$E7FA. Parked here as a FAT-allocator cell
with per-operation lifetime; documented as such. `fat_alloc_cluster` is reached from
several paths — WRBLK, WRSEQ, create-then-write — so it is a FAT cell, not a WRBLK
one, despite the neighbourhood.)

### 3.2 `fat_mount` — reset
Add, once, where `fat_mount` finishes parsing the BPB (before it returns success):
```
ld hl, 2 ; ld (FAT_ALLOCHINT), hl   ; per-operation: next free-scan starts at 2
```
This must be on the SUCCESS path and run before any allocation. (Implementer:
confirm `fat_mount` is called exactly once per operation and always precedes
`fat_alloc_cluster`; it is — no code path re-mounts mid-allocation.)

### 3.3 `fat_alloc_cluster` — scan from the hint, advance on success
Two edits to fat.asm:391:
- Replace the scan seed `ld hl, 2` (fat.asm:397) with `ld hl, (FAT_ALLOCHINT)`.
- At `fac_found` (fat.asm:419), after the cluster is claimed and before `ret`, set
  `FAT_ALLOCHINT := cluster + 1` (the claimed cluster is in HL there).

Nothing else changes: the FAT-sector cache (`FAT_WRTMP2`), straddle handling, EOC
write, and the `fac_full` total-clusters bound are all untouched. The bound still
declares full correctly (§4).

**Net-zero caution:** the seed swap `ld hl, 2` → `ld hl, (FAT_ALLOCHINT)` is
byte-size-neutral (both 3 bytes: `21 02 00` → `2A FB E7`) — no shift. But the
`fac_found` advance (`push hl; inc hl; ld (FAT_ALLOCHINT),hl; pop hl`, ~7 bytes,
HL must survive as the return value) GROWS inline code that sits just below the
`ds $498C/$49B4/$49C3` and above the `ds $4A39/$4A40` canonical anchors. If the
`$4A39` ds cannot absorb the growth, apply the established **3b-relocation**
(M28/M29 pattern): divert `fac_found`'s tail to a small body in the free
`$60EC-$75A4` corridor, keeping every `k_*` address net-zero. Implementer picks
whichever keeps `disk.rom` = 16384 B with 0 `k_*` moved (§6.5).

## 4. Invariant & byte-identity proof

**Invariant (holds throughout any one operation's allocation sequence):**
`FAT_ALLOCHINT ≤ index of the lowest free cluster`.
- Base: `fat_mount` sets it to 2 ≤ any cluster index (≥2).
- Step: allocating claims the lowest free cluster `C ≥ hint` (the scan from `hint`
  returns the first `$000`, and by the invariant nothing free lies below `hint`, so
  `C` is the global lowest free). Setting `hint := C+1` re-establishes it: `C` is now
  used and `[2,C)` were already all used, so the new lowest free is `≥ C+1`.
  No frees occur in an allocating operation, so nothing lowers the true lowest-free.

**Byte-identity (to *today's* zerobas, which is the invariant M30 guarantees):**
under the invariant, scanning from `hint` returns the *same* cluster as scanning
from 2 (both return the global lowest free `$000`). Therefore the whole allocated-
cluster sequence is identical to **today's (pre-M30) zerobas**, for every input —
verified directly: `test_fat_alloc_hint.py` (a) equals a from-2 reference across
first-free-far and hole layouts, and a HEAD-ROM `del_realloc` round-trip produces the
identical ours chain to the M30 ROM. Cross-operation, the hint resets to 2, so a
delete-then-write in a *later* operation re-scans from 2 exactly as pre-M30 did. ∎

**NB — this is byte-identity to *today's zerobas*, NOT to the CF-3300 in every
scenario.** Our allocator is (and always was) lowest-free-first: after a delete it
reuses the freed low clusters. The CF-3300's allocator is NOT lowest-free-first — it
skips to a higher cluster (verified: `del_realloc` ours `[340,336]` vs stock
`[340,339]`, and a HEAD ROM shows the *same* ours chain). That ours≠stock allocation
**order** after a free is **PRE-EXISTING** (present before M30) and is tracked as a
separate characterisation item, not an M30 effect. For the no-free paths that the
M28/M29 round-trip already pins (within/extend/rr24/multi), ours stays byte-identical
to stock under M30 (re-verified).

**Full detection unchanged:** if the scan reaches `total_clusters` with no `$000`,
no free cluster `≥ hint` exists; since `[2,hint)` are all used, none exists at all ⇒
genuinely full. Same `fac_full` path as today. No wrap-around needed.

## 5. Scope
- **In:** per-operation hint (kills the intra-operation quadratic — the motivating
  cost). ~4 changed lines + 1 equate.
- **Deferred (noted, not done):** a *whole-mount* persistent hint would also speed a
  long series of SEPARATE small append operations (each currently re-scans from 2).
  That version DOES need the free-site hint-lowering (byte-identity across a
  free-then-alloc spanning two operations) — the correctness surface this design
  avoids. Not required for the motivating workload; revisit only if separate-append
  latency is shown to matter.

## 6. Verification — RESULTS (all passed unless noted)
1. **Existing tests + round-trip byte-identical, NO expected-value edits.** ✅
   `make unit-test` 30/30. The two edits to `test_fat_alloc_cluster.py` /
   `test_wrblk_extend.py` are FIXTURE seeding only (they call the allocator without
   `fat_mount`, so they now seed `FAT_ALLOCHINT=2` — what `fat_mount` does); no
   expected values changed. No-free round-trip cases within/multi still MATCH stock.
2. **`del_realloc` round-trip — REFRAMED (my §6 draft assumption was wrong).** ✅
   I assumed "both ours and stock reuse the freed low clusters." **Stock does not.**
   Verified: ours `[340,336]` (reuses freed 336), stock `[340,339]` (skips). A HEAD
   (pre-M30) ROM gives the **same** ours chain `[340,336]`, so this ours≠stock is
   PRE-EXISTING, not M30. The case is now `kind="divergence"` (documents it, asserts
   ours self-consistent + lowest-free-first — like the `shrink` case), and a separate
   follow-up tracks characterising the CF-3300's allocation order.
3. **Host test `test_fat_alloc_hint.py`.** ✅ (a) sequence == from-2 reference across
   first-free-far AND hole layouts; (b) `hint ≤ lowest-free` after every alloc;
   (c) `fat_mount` reset + cross-operation reuse of a freed cluster; (d) O(1)-ish
   reads/cluster; (e) disk-full still detected.
4. **Speed `wrblk_perf.py --alloc`.** ✅ Allocation-bound M29→M30: CPU 4.4× (K=32,
   free 64 in) up to 9.2× (free 400 in); **I/O 1.0×** — A is CPU-only (see §1; the
   `FAT_WRTMP2` intra-call cache already made allocation I/O linear).
5. **Tier-1.** ✅ `disk.rom` = 16384 B; **0 `k_*` moved**. `fac_found`'s ~7-byte
   growth was absorbed by the `$4A39` ds (no 3b-relocation needed); the byte churn
   (~1189 bytes) is internal-label shift within the two ds-absorbed regions +
   absolute-reference updates — canonical addresses net-zero, all tests green.

## 7. Implementation note
Signed-off-spec → Sonnet 5 (model split), Opus verifies. ~4 changed lines in
`fat.asm` + 1 line in `fat_mount` + 1 equate + 2 tests + 1 round-trip case. The
shared kernel, `fat_write_fat_entry`, and both free sites are **untouched**.
