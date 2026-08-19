# M29 — WRBLK position cursor (kill the sequential-write O(n²))

Status: **✅ DONE — implemented + verified 2026-07-04** (was: DRAFT → signed off → landed)
Scope decisions taken: 2026-07-04 (two AskUserQuestion rounds — see §5).
Motivating trigger: user directive "The O(n²) should be investigated for improvement",
following the M28 round-trip where a 33-cluster WRBLK extend timed out the emulator
(recorded in [tier2-review-queue.md](tier2-review-queue.md) as "correct, just slow").

Clean-room: this is a performance refactor of OUR OWN routine
([kernel.asm](../kernel.asm) `wrblk_position_ext`). No stock code is read; the
on-disk artifact and the published WRBLK contract are unchanged (byte-identical
result guaranteed — see §4). Precedent: the same iterator shape as the M26/M28
parallel routines.

---

## 1. Characterisation (measured, not assumed)

Host harness `probes/disk/wrblk_perf.py --shape` (reuses `tests/test_wrblk_body_e2e.py`;
only `read_sector`/`write_sector` mocked, everything else real) counted sector I/O as a
function of workload. Two compounding O(n²) costs plus a constant-factor amplifier
were found; **this spec fixes only (P)** — the dominant one for the WRBLK workload.
(The K=1→32 allocation figures below were taken with an earlier variant of the same
harness; `--shape` reports the positioning column.)

| id | cost | measured | disposition |
|----|------|----------|-------------|
| **P** | `wrblk_position_ext` re-walks the chain from the head for **every** record | 1 record past a P-cluster file = ~4·P reads (linear in chain); N sequential records ⇒ O(N²) | **FIX (this spec)** |
| A | `fat_alloc_cluster` restarts the free-scan at cluster 2 every allocation | K-cluster extend: 19→2592 FAT reads for K=1→32 (quadratic) | deferred (needs next-free-hint + free-invalidation correctness surface) |
| C | `fat_next_cluster` never caches the FAT sector | 256-cluster walk = 1027 reads where ~3 suffice | dropped — `SECTOR_BUF` is clobbered by a data read **every hop** (kernel.asm:1044 then 1100-1101), so a `SECTOR_BUF`-keyed cache yields ~0; and P makes the remaining walk a once-per-call amortized cost |

Why P dominates and A/C do not, once P lands: after the cursor, each WRBLK call
performs exactly **one** from-head walk (its first positioning), which is the
§4-accepted "correct and simple, walk-from-start" non-goal shape shared with
`rrnd_position`. The per-record re-walks — the actual quadratic — are gone.

### 1.1 Actual before/after (M28 ROM vs M29 ROM, measured)

`probes/disk/wrblk_perf.py --before-after` runs the **identical** workload — ONE
`wrblk_body` call writing N sequential 128-byte records within an already-allocated
64-cluster file (within-EOF, so this isolates positioning; no allocation-A noise) —
on the pre-M29 (M28, commit `6535a59`) ROM and the M29 ROM, on the real-Z80 host
harness (baseline built from the git ref, so the comparison is reproducible). It counts **CPU
instructions executed** (`read_sector`/`write_sector` are trapped as zero-cost, so
this column is pure Z80 work) and **sector I/O** (disk work). On real MSX hardware
elapsed ≈ steps·t_cpu + io·t_sector with t_sector (floppy, ~ms) ≫ t_cpu (~µs), so
both columns dropping is the speed story.

| N records | M28 CPU steps | M28 I/O | M29 CPU steps | M29 I/O | CPU speedup | I/O speedup |
|--:|--:|--:|--:|--:|--:|--:|
| 16  | 7,863    | 84     | 4,917  | 27  | 1.6× | 3.1× |
| 32  | 21,783   | 292    | 8,883  | 51  | 2.5× | 5.7× |
| 64  | 70,839   | 1,092  | 16,815 | 99  | 4.2× | 11×  |
| 128 | 253,815  | 4,228  | 32,679 | 195 | 7.8× | 22×  |
| 256 | 959,226  | 16,644 | 64,410 | 387 | **14.9×** | **43×** |

The **shape** is the proof, not the single ratio: M28 CPU steps ~4× per 2× N
(quadratic); M29 steps ~2× per 2× N (linear). The speedup therefore GROWS with N —
the O(N²)→O(N) signature. At N=256, 14.9× fewer instructions and 43× fewer sector
accesses; on 3.58 MHz hardware that write is roughly ~80 s → ~2 s (the t_sector
constant is approximate, so treat the wall-clock as order-of-magnitude; the ratios
are exact). This matches the M28 review-queue note that a large extend "needed
>46 s emulated".

---

## 2. Current behaviour (the defect)

`wrblk_position_ext` (kernel.asm:1016) on **every** call:
1. `fat_open` — resets the iterator to `FAT_FIRSTCLUS`, `FAT_CLUSSEC=0`.
2. Walks `target_sector_in_file + 1` steps via `wrblk_read_or_extend_sector`,
   each step following one FAT link **and reading that cluster's data sector into
   `SECTOR_BUF`**.

Because `WRBLK_REC` increments by 1 per loop iteration (kernel.asm:913), the caller
asks for a strictly non-decreasing sequence of records. Re-walking from the head each
time is therefore pure waste: 3 of every 4 records land in the **same** 512-byte
sector already positioned, and the 4th is exactly **one** step further on.

---

## 3. Design — incremental position cursor

Keep the iterator between calls instead of resetting it. WRBLK's record order is
strictly non-decreasing (invariant, kernel.asm:913), so the next target is always
`≥` the current one, and in practice a delta of **0** (same sector, ¾ of records)
or **1** (next sector).

### 3.1 New state (3 bytes, in the existing $E7F8–$E7FF free tail of the WRBLK block)
```
WRBLK_CURVALID  equ $E7F8   ; byte: 0 = iterator not yet positioned this call
WRBLK_CURSEC    equ $E7F9   ; word: sector-in-file the iterator currently sits on
                            ;       (meaningful only when CURVALID=1)
```
(Grep-confirmed free: the WRBLK block ends at `WRBLK_NEXTCLUS` $E7F6..$E7F7;
$E7F8–$E7FF is unused. `WRBLK_MULACC/OP/N` live in WBUF, not here.)

### 3.2 Initialisation
`wrblk_body` sets `WRBLK_CURVALID := 0` **once**, before `wrblk_loop`. The HL==0
`wrblk_zero_path` never calls `wrblk_position_ext`, so only the loop path is affected.

### 3.3 Revised `wrblk_position_ext`
```
wrblk_position_ext:
    ; WRBLK_RECSEC := WRBLK_REC & 3  (unchanged — within-sector record slot)
    ; target_sec (16-bit) := WRBLK_REC >> 2   (D:E:A >>2 as today; D always 0)
    ; BC := target_sec
    ld a,(WRBLK_CURVALID); or a; jr z, wpe_fresh
        ; DE := target_sec - WRBLK_CURSEC        (>=0 by the monotonic invariant)
        ; if DE==0 -> wpe_same : iterator already ON this sector AND SECTOR_BUF
        ;                        still holds its bytes -> return Cy=0, NO I/O
        ; else: WRBLK_CURSEC := target_sec; advance DE steps via
        ;       wrblk_read_or_extend_sector (ret c on disk-full); return Cy=0
wpe_fresh:
    call fat_open
    WRBLK_CURSEC := target_sec ; WRBLK_CURVALID := 1
    walk target_sec + 1 steps via wrblk_read_or_extend_sector  ; (today's loop)
    ret
```

### 3.4 Why `wpe_same` (delta==0, no read) is correct
Between finishing record R and positioning record R+1 in the SAME sector, the code
path (kernel.asm:899–897: `ldir` overlay → `write_sector` → DTA+=RS → REC+=1 →
CNT-=1 → `jp wrblk_loop`) never touches `SECTOR_BUF` except the overlay+write, which
leave the sector's current (and now persisted) bytes in the buffer. Overlaying the
next record's 128-byte slot and re-writing is exactly what the current code does after
its redundant re-read. `wrblk_position_ext`'s own preamble touches only `WRBLK_RECSEC`
and the target math. So the buffer genuinely still holds the target sector. ∎

### 3.5 Why the incremental advance is correct
The cursor path does **not** call `fat_open`, so `FAT_CURCLUS`/`FAT_CLUSSEC` persist
from the previous call's end — the true iterator position. Advancing `delta` steps of
`wrblk_read_or_extend_sector` reaches `target_sec`, allocating/linking through any gap
exactly as a from-head walk would (`WRBLK_PREVCLUS` is recomputed inside each step).
The destination sector is read fresh (delta≥1), matching today's "freshly allocated
sector reads back existing disk bytes" contract. ∎

---

## 4. Invariant preserved — byte-identical artifact

The on-disk result (dirent size + first cluster, FAT chain, every written record's
bytes) is **identical** to the pre-change routine for every input, because the cursor
only elides redundant `fat_open`+re-walk+re-read work that recomputes the same
position and the same `SECTOR_BUF` contents. No FAT entry, data byte, or dirent field
is written differently. This is asserted, not argued, by the regression tests (§6).

## 5. Scope decisions (signed off 2026-07-04)
- Q1 "How far": **C + P** initially, then **narrowed to P only** after the deeper read
  of the walk body showed C is inert here (SECTOR_BUF clobbered per hop; P makes the
  remaining walk a once-per-call amortized cost).
- **A** (allocator next-free hint) and **C** (FAT-sector cache) are deferred/dropped;
  their rationale + measurements live in this doc and the review queue so they can be
  reopened if a future workload needs them.

## 6. Verification plan (must pass before commit)
1. **Existing tests unchanged**: `make unit-test` (28) + `test_wrblk_body_e2e.py`,
   `test_wrblk_extend.py`, `test_wrblk_fsize.py` all still PASS — the artifact is
   byte-identical, so no expected-value edits are allowed. Any diff = a bug.
2. **New host test** `test_wrblk_cursor.py`: drive a multi-record, multi-cluster
   sequential WRBLK and assert (a) the artifact equals a from-head reference, and
   (b) sector I/O is now **O(N)** not O(N²) — re-run `charac_alloc2.py`'s shape and
   assert reads/record is bounded (no growth with prefill for the same-sector case;
   ~constant per new cluster). This locks the fix in.
3. **Tier-1**: `disk.rom` still exactly 16384 B; sym diff shows **0 `k_*` moved**
   (the +~40 bytes land in the free $60EC–$75A4 corridor).
4. **Round-trip** `disk_probe_wrblk_roundtrip.py`: still byte-identical to the CF-3300
   oracle (the ultimate artifact check). A NEW `multi` case (8 sequential records in
   ONE call, `checkrec=6`) directly exercises the cursor path against stock —
   `wpe_same` reuse of `SECTOR_BUF` across iterations + a `wpe_adv` step — which the
   pre-existing 0/1-record cases did not reach.
   NOTE (correction to an earlier draft claim): the `rr24` single-record 33-cluster
   extend is **allocation-bound** (deferred cost **A**, `fat_alloc_cluster` rescans
   from cluster 2), NOT positioning-bound. It has one `wrblk_position_ext` call, so the
   cursor gives it ~zero speedup; it still needs the larger emulator budget
   (`--end 150`) and is verified byte-identical there (no regression). M29's O(N) win
   is for MULTI-record sequential writes, proven by the host test + the §1
   characterisation re-run (K=32 single-call extend: 2592 → 131 FAT reads).

## 7. Implementation note
Signed-off-spec implementation → Sonnet 5 (model split), Opus verifies. The change is
~40 lines in one routine + 3 RAM equates + 1 init line + one new host test. `fat.asm`,
the shared kernel, and `fat_read_file_sector` are **untouched**.
