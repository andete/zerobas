# Stock CF-3300 allocation-order characterisation (M30 open item D)

Status: **CHARACTERISED — no implementation proposed (per directive: characterise first)**
Date: 2026-07-05
Probe: [disk_probe_alloc_order.py](../../probes/disk/disk_probe_alloc_order.py)
Predecessor: the M30 round-trip `del_realloc` divergence
([disk_probe_wrblk_roundtrip.py](../../probes/disk/disk_probe_wrblk_roundtrip.py),
kind=`divergence`) and [tier2-m30-alloc-hint-spec.md](tier2-m30-alloc-hint-spec.md) §4.

## Question

M30 verification found: after `op1 = DELETE DELFILE.BIN` (freeing a low contiguous
hole) then `op2 = WRBLK extend WRTEST.BIN`, **ours** always picks the *lowest* freed
cluster (336), but the real **National CF-3300** oracle picks a *different* one (339).
Confirmed NOT caused by M30 (a pre-M30 ROM gives the same ours-chain). What ordering
does stock actually use when (re)allocating clusters?

## Method (clean-room, black-box)

Build a fresh `/tmp` copy of a real MSX-DOS-1 disk with a chosen free/used layout,
boot openMSX `National_CF-3300`, let a tiny WRBLK.COM exerciser
([wrblk_rt.asm](../../probes/disk/wrblk_rt.asm)) optionally DELETE a pre-seeded file
then extend `WRTEST.BIN` by K clusters, then pure-Python FAT12-parse the mutated
image and read the **resulting cluster chain**. The *sequence* of newly-allocated
clusters is the diagnostic. Stock ROM code is never read/disassembled; only its
OUTPUT DISK is read. Test disks are always `/tmp` copies.

The base disk (`~/Documents/msx/msx/disks/test.dsk`, 715 clusters, 1024 B/cluster)
has clusters **2–335 fully used**; free runs 336–501, 503–675, 687–714. After the
harness injects DELFILE.BIN (336–339), WRTEST.BIN (340), WRBLK.COM (341–343),
AUTOEXEC.BAT (344), first free is 345.

## Experiment matrix & stock results

| exp | layout (WRTEST tail L) | K | STOCK allocated (in order) | OURS |
|-----|------------------------|---|----------------------------|------|
| `order4`   | tail=340, freed hole 336–339 adjacent below | 4 | **339, 338, 337, 336** (down) | 336,337,338,339 |
| `descend1` | as order4 but DELFILE chain REVERSED (339→…→336) | 1 | **339** | 336 |
| `descend4` | reverse-chain hole, +4 | 4 | **339, 338, 337, 336** (down) | 336,337,338,339 |
| `over8`    | tail=340, hole 336–339 (only 4 free), +8 | 8 | 339, 338, 337, 336, **345, 346, 347, 348** (down, then up) | 336,337,338,339,345,346,347,348 |
| `nodel`    | tail=340, NO free hole below (339 used), +4 | 4 | **345, 346, 347, 348** (up) | 345,346,347,348 ✓= |
| `gap`      | tail=349, **L−1=348 used**, 347 free, lowest-free=340 | 1 | **350** (up-from-tail) | 340 |
| `extend` (round-trip) | tail=336, nothing free below, +1 | 1 | **341** (up) | 341 ✓= |

(OURS = global lowest-free-from-2; agrees with stock (✓=) exactly when nothing is free
just below the tail AND lowest-free == first-free-above-tail.)

### What each result rules out

- `order4` = `[339,338,337,336]` **descending** ⇒ NOT lowest-first (that's `[336,337,338,339]`);
  a downward scan, not upward.
- `descend4` = same `[339,338,337,336]` regardless of the delete's chain-walk order ⇒
  NOT "reuse in free-order / rover = last cluster released" (reverse delete still started at 339);
  the choice is by **cluster number relative to the file**, not by free-list history.
- `over8` continues `…336, 345,346,347,348` (UP after the hole dead-ends at used 335) ⇒
  NOT a global highest-free or a wrap-to-top-downward scan.
- `gap` = `350` (not 340, not 347) ⇒ phase-1 is the **single adjacent cluster L−1 only**
  (it did not scan down to the free 347), and phase-2 scans **upward from the tail**,
  NOT from cluster 2 (that would be 340).

## Inferred model (fits 100% of the data)

Stock extends a file's chain one cluster at a time. Given the current **tail cluster L**:

```
if (L-1) >= 2 and FAT[L-1] is free:      # phase 1: backward-contiguous
    allocate (L-1);   new tail = L-1
else:                                     # phase 2: forward scan
    allocate first free cluster scanning UPWARD from L;  new tail = that cluster
```

i.e. a **contiguity-preferring allocator**: it greedily keeps the file packed by
grabbing the cluster immediately *below* the tail; only when that exact cluster is
taken does it fall forward to the next free cluster above. The scan is **tail-relative**,
not disk-global.

Ours (`fat_alloc_cluster`, [fat.asm](../fat.asm)) has **no tail awareness at all**: it
returns the global lowest-free cluster (from cluster 2, M30-hinted). That is precisely
stock's *phase 2 minus the tail bias* — so ours and stock agree in every layout where
nothing is free just below the tail, and diverge exactly when a free cluster sits at
L−1 (the `del_realloc`/`order4` family) or when the lowest-free differs from the
first-free-above-the-tail (`gap`).

### Untested edge (noted, not needed for the divergence)

Phase-2 wrap-around: no experiment forced the upward scan off the top of the disk
(file near max cluster, free space only lower). Assumed to wrap to cluster 2 like a
normal FAT scan, but **unverified**. Also the first-cluster allocation of a *brand-new*
file (no tail L) is unexercised here — WRTEST's seed cluster came from the Python
injector, not stock.

## Why this is only cosmetic

Both chains are valid FAT12, hold **byte-identical file data**, report identical free
space, and are read identically by any DOS. The divergence is purely *which physical
clusters* hold the bytes and the chain's numeric order — a fragmentation/layout policy,
not a correctness or contract difference. No reader observes it.

## Options (for decision — not yet actioned)

1. **Document & accept (recommended).** Keep the round-trip `del_realloc` case as
   `kind="divergence"` (as the `shrink` case already is), citing this doc. Ours stays
   a clean lowest-free allocator. Zero risk, zero code change.
2. **Match stock byte-for-byte.** Requires teaching `fat_alloc_cluster` the file's
   current tail L (a contract/signature change threaded from the chain-extend loop),
   adding the phase-1 `L−1` probe, AND changing phase-2 from "lowest-free-from-2" to
   "upward-from-L". That is a broad change to the core allocation policy affecting
   **all** writes (WRSEQ/create/WRBLK), each needing fresh oracle validation — a large
   surface for a cosmetic gain. Not recommended unless byte-identical physical layout
   with stock becomes an explicit goal.
