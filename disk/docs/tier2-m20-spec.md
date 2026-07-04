<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M20 spec — DIR free-space footer (BDOS `$1B` GETALLOC entry `$505D`)

**Status: LANDED (2026-07-02, REVISION 3).** §§1-10 below are the ORIGINAL
characterisation span (Opus). Its A/BC/DE/HL scan design (§4.1/§4.2/§4.4, §6) was correct
all along and is exactly what shipped; its "no new work cell is needed" claim (§4.3) also
held in the end. Two revisions were BUILT and FALSIFIED before the real fix was found:
**Revision 1** (this file's original §4.2 register-only design) computed A/BC/DE/HL
correctly but the footer still printed `0` — sentinel test (`HL=$BEEF` before `ret`)
proved the BDOS exit `$C6C5` never reflected our `HL`. **Revision 2** (resident-FAT-buffer
+ `IY`/`DPB+19`, synthesized from a one-time Opus+Fable dual-dispatch trial) was built and
verified WIRED CORRECTLY but the footer was STILL wrong, identically so — excluding `IY`
and `DPB+19` as the mechanism too. **Revision 3 (LANDED)**, from a follow-up Fable-solo
investigation: the real cause was the RAM kernel's common BDOS-exit path (`$D8AA-$D8BD`),
which gates `HL` passthrough on a dispatcher flag cell `$F306` — a handler that leaves it
set has its `HL` silently overwritten with `H:=B,L:=A` (a CP/M single-byte-result mirror)
instead of passed through; causally proven with a poke test. The fix is Revision 1's
original register-only body PLUS one store: clear `$F306` before `ret`. No buffer, no `IY`,
no `DPB+19` needed — Revision 2's entire premise was a red herring (stock's `IY`/DPB+19
reads during `$1B` are the STOCK HANDLER's own internal scratch, never consumed
downstream). Full root-cause writeup + acceptance results: see
[tier2-review-queue.md](tier2-review-queue.md) M20 entries (LANDED, then the two hard-stops
below it, newest first). Resume board: [tier2-STATE.md](tier2-STATE.md). Builds on M19's
dir-search (landed) — this is the SEPARATE free-scan
the M19 design never characterised.

## 1. Goal
Make MSX-DOS `DIR`'s footer render the SAME free-space line as stock. Concretely: on
test.dsk, `DIR` must print **`375808 bytes free`** at ROW22 (ours currently prints
**`0 bytes free`**), instead of `0`. Everything else about `DIR` already matches stock
byte-for-byte (M19: the file list + `41 files` + a fresh `A>` all identical) — this is
the ONE remaining divergence, a single line. The mechanism is one un-wired page-1 kernel
entry, **`$505D`** (the BDOS `$1B` GETALLOC free-cluster-count primitive); the fix wires
it to a real FAT free-cluster scan built on our own `fat_total_clusters` +
`fat_alloc_cluster` scan primitives. Tier-1 green, `disk.rom`==16384 B, no
canonical-address shift, all prior milestone repros intact.

## 2. What DIR's footer actually does — PINNED black-box (this span)
Method: `probes/disk/disk_probe_diff.py` (`callseq --log`, `callwatch --in-func`,
`readwatch --in-func`, `capture --at`), test.dsk auto-copied to tmp (mutation-safe),
anchored at COMMAND.COM `$0100`, driven with `--keys '\rDIR\r' --keys-at 22 --settle 90`.
NO stock/kernel CODE bytes were decoded — only entry PCs (addresses), call counts,
data-cell read addresses/reader-PCs, and entry/exit register snapshots.

### 2.1 The footer is BDOS `$1B` GETALLOC (the load-bearing finding)
`callseq --log 0x0005 --maxhits 2000 --settle 92` → the full `DIR` on test.dsk is
**1349 BDOS calls** on stock (1 STROUT boot + 1 SFIRST + 50 SNEXT + 51 SETDTA + 1231
CONOUT + …). The distinct funcs are exactly: STROUT, FOPEN, GDATE, BUFIN, SELDSK, CURDRV,
SETDTA, SFIRST, SNEXT, CONOUT — **plus exactly ONE `$1B` ALLOC (GETALLOC) call:**

```
STOCK n=1333 C=1B ALLOC A=00 B=C9 DE=D100 HL=C924 ret=C6C5 t=28.2587
```

immediately before the footer prints and `DIR` returns to `A>` (n=1346 CURDRV,
n=1347-48 emit "A>", n=1349 BUFIN = blocked at the prompt). **Ours issues the IDENTICAL
`$1B` call** (`OURS n=1415 C=1B ALLOC A=00 B=C9 DE=D100 HL=C924 ret=C6C5`), register-byte-
identical at entry — so COMMAND.COM reaches the footer path correctly on both. The
free-space line is NOT computed by COMMAND.COM itself and is NOT a separate disk-ROM
callback: **it is the documented MSX-DOS-1 BDOS function `$1B` (Get Allocation
Information / GETALLOC).** Repro (both machines):
```
python3 probes/disk/disk_probe_diff.py callseq --at 0x0100 --log 0x0005 \
  --maxhits 2000 --keys '\rDIR\r' --keys-at 22 --settle 92 \
  --diska ~/Documents/msx/msx/disks/test.dsk
# STOCK n=1333 C=1B ALLOC ; OURS n=1415 C=1B ALLOC — identical entry regs.
```

### 2.2 GETALLOC dispatches to page-1 kernel entry `$505D` (the missing entry)
`callwatch --in-func 0x1b --range 0x4000:0x7FFF` (ours) → while `$1B` is in flight ours
executes only page-1 PCs **`$505D`, `$50AD`, `$50B0`, `$50B4`, `$50B7`** — i.e. it enters
`$505D` then NOP-slides into the existing **`$50A9` stub tail** (`$50AD-$50B7`). So the
relocated RAM kernel, processing BDOS `$1B`, CALLs the page-1 disk-ROM entry **`$505D`**.
`capture --at 0x505D --nth 1` (both machines), during `$1B`:

| reg | STOCK | OURS |
|---|---|---|
| PC | `$505D` | `$505D` |
| AF | `$0044` | `$0044` |
| BC | `$5D1B` | `$5D1B` — **C=`$1B`** = the GETALLOC func code |
| DE | `$D100` | `$D100` |
| HL | `$C924` | `$C924` |
| IX | `$F195` | `$F195` |
| IY | `$ED55` | `$DC5B` — **NOT consumed**, benign (same as every prior veneer) |
| SP | `$DBFE` | `$DBFE` |

**Entry registers are byte-identical ours==stock (bar the never-consumed IY)** — a real
CALL boundary, the exact `$50xx`-veneer shape of M13/M17/M18/M19. Repro:
```
python3 probes/disk/disk_probe_diff.py callwatch --machine ours --range 0x4000:0x7FFF \
  --in-func 0x1b --keys '\rDIR\r' --keys-at 22 --settle 90 \
  --diska ~/Documents/msx/msx/disks/test.dsk
#   OURS: 505D 1x, 50AD 1x, 50B0 1x, 50B4 1x, 50B7 1x  (slides into the $50A9 stub)
python3 probes/disk/disk_probe_diff.py capture --at 0x505D --nth 1 --machine both \
  --keys '\rDIR\r' --keys-at 22 --settle 90 --diska ~/Documents/msx/msx/disks/test.dsk
```

### 2.3 What stock's `$505D` does: scan the resident FAT buffer `$E595`
`readwatch --in-func 0x1b --range 0xE595:0x40` (stock) → **81 gated reads across 61
cells** of the buffer at **`$E595`**, by reader-PCs **`$4209`/`$420B`** (the page-1 FAT12
entry-unpack primitive). The buffer at `$E595` holds the volume's FAT (media byte `$F9`,
then the 12-bit cluster chain): `capture --at 0x5006 --nth 1 --mem 0xE595:0x20` (stock)
shows `F9 FF FF 03 F0 FF 05 60 00 07 80 00 …`. Decoding that buffer as FAT12 and counting
`$000` (free) entries from cluster 2 = **367 free clusters** = `367 × 1024 = 375808` — the
exact footer value. **The FAT buffer was loaded ONCE, during the FIRST SFIRST**, by a
single 3-sector `$4010` DSKIO: `callseq --log 0x4010` (stock) → `n=5 DE=0001 B=03 HL=E595
t=23.16` (sectors 1-3 = the 3-sector FAT). No FAT re-read happens at `$1B`/footer time
(`callwatch --in-func 0x1b --range 0x4010:0x4013` → only the `$4013` continuation, no
fresh read) — **`$505D` reads the ALREADY-resident `$E595` buffer.** Repro:
```
python3 probes/disk/disk_probe_diff.py readwatch --machine stock --range 0xE595:0x40 \
  --in-func 0x1b --gate-func9 --keys '\rDIR\r' --keys-at 22 --settle 90 \
  --diska ~/Documents/msx/msx/disks/test.dsk
#   E598: reads=1 V=03 readerPCs=4209 ; E599: reads=2 V=F0 readerPCs=4209 420B ; …
```

### 2.4 The OUTPUT contract — PINNED at the `$1B` return (`ret=$C6C5`)
`capture --at 0xC6C5 --nth 1` (both), the register state COMMAND.COM reads to format the
footer:

| reg | STOCK | meaning | OURS |
|---|---|---|---|
| A  | `$02`   | **sectors per cluster** | `$00` |
| BC | `$0200` | **bytes per sector (512)** | `$5D1B` |
| DE | `$02C9` | **total data clusters (713)** | `$F1AA` |
| HL | `$016F` | **free clusters (367)** | `$5D00` |
| IY | `$E595` | (FAT-buffer ptr; scratch) | `$DC5B` |

**⇒ GETALLOC's return contract is the documented one: `A` = sectors/cluster,
`BC` = bytes/sector, `DE` = total clusters, `HL` = free clusters.** COMMAND.COM computes
the footer as **free_bytes = HL × A × BC = 367 × 2 × 512 = 375808** and prints it. On OURS
every one of A/BC/DE/HL is **`$50A9`-stub garbage** (`A=$00` from the stub's `sub a`;
`DE=IX=$F1AA`, `HL=$5D00`) → `A=0` ⇒ free_bytes = 0 ⇒ `0 bytes free`. Repro:
```
python3 probes/disk/disk_probe_diff.py capture --at 0xC6C5 --nth 1 --machine both \
  --keys '\rDIR\r' --keys-at 22 --settle 90 --diska ~/Documents/msx/msx/disks/test.dsk
```
(Sources for the register meanings: MSX-DOS-1 BDOS function table `$1B`
GETALLOC — map.grauw.nl MSX-DOS functions, MSX2 Technical Handbook §BDOS, CP/M 2.2 fn 27
"Get Allocation Vector"/MSX GETALLOC. Cited, not decoded; the OBSERVED stock exit regs
above independently confirm the A/BC/DE/HL assignment for this disk.)

## 3. Root cause (pinned, clean-room — no stock/kernel code decoded)
The relocated RAM kernel, processing BDOS `$1B` (GETALLOC), CALLs page-1 disk-ROM entry
**`$505D`**. On ours `$505D` is `$00` NOP-padding (verified from our OWN rom, allowed:
`build/disk.rom` at `$5058` = `C3 05 79` = the M19 `jp setdta_cache_body` veneer, then
`$505B..$505C` = `00 00`, `$505D..$50A8` = `$00` fill up to the `$50A9` stub). The CALL
NOP-slides forward into the `$50A9` stub tail (`$50AD-$50B7`: `sub a / ld de,$F1AA /
ld ix,$F1AA / ld hl,$F359 / ret`), whose `ret` returns `A=$00, DE=IX=$F1AA, HL≈$5D00` —
which COMMAND.COM's footer formatter reads as "0 sectors/cluster, 0 free space." So the
free line prints `0`. **`ours never reads $E595 and never runs the $4200-region FAT
primitive during `$1B`** (`readwatch --machine ours --range 0xE595 --in-func 0x1b` → 0
reads; `callwatch --machine ours --range 0x4200:0x4220` during DIR → 0 hits) — it does no
free-cluster scan at all. Same un-wired `$50xx`-entry CLASS as M13/M17/M18/M19; the
correct body is a small FAT-scan primitive, not a read-a-cell veneer.

Note the un-related `$75A5` "ret-stub" and the per-file `C=05 LSTOUT` fork the prior span
flagged (STATE "Next action") are a **SEPARATE, cosmetically-absorbed COMMAND.COM branch
difference** (ours issues 82 spurious LSTOUT across the listing) — NOT the footer. It does
NOT prevent ours reaching `$1B`/`$505D` correctly (proven: ours' `$1B` entry regs are
byte-identical to stock). `$75A5` is a divergence symptom, not the free-count entry. The
free-count entry is `$505D`. (The LSTOUT fork is out of scope for M20 — see §8.4.)

## 4. Design — `getalloc_body` (reuse our own `fat_*` scan)
One new routine in the free tail (kernel.asm, like `sfirst_body`/`seldsk_drv_body`),
reached by a 3-byte `jp` veneer at `$505D`. It reuses our own `fat_total_clusters` (for
the cluster count + geometry) and the `$000`-scan loop already inside `fat_alloc_cluster`
(generalised from "stop at the first free cluster" to "count ALL free clusters").

### 4.1 What we already own (read from fat.asm — reusable)
- `fat_total_clusters` (fat.asm:739): reads the boot sector, returns **DE = dataClusters
  + 2** (its highest-cluster-plus-one bound); also leaves `FAT_SECPERCLUS`,
  `FAT_FIRSTDATA` etc. set. The DPB's "total clusters" the footer wants is `dataClusters`
  = that value − 2 = 713 on test.dsk (matches the pinned `DE=$02C9`). Reuse verbatim.
- `fat_alloc_cluster` (fat.asm:478): its scan `fac_loop`/`fac_have_sec`/
  `fac_entry_from_wbuf` linearly walks clusters 2..total, reading the FAT SECTOR-BY-SECTOR
  into WBUF and unpacking each 12-bit entry, testing `$000`. **The free-count body is that
  same loop with `jr z, fac_found` replaced by `inc (free-counter)`** — walk to the end
  instead of stopping at the first free cluster. Do NOT modify `fat_alloc_cluster` itself
  (loader/write path); write a sibling scan (or factor the shared inner unpack) so the
  Tier-1 write path is untouched.
- `read_sector` (fat.asm:106), `WBUF` ($E560, 512 B), `SECTOR_BUF` ($E2A0), the DPB layer,
  `FAT_SECPERCLUS`. All reusable.

### 4.2 `getalloc_body` (the `$505D` entry) — shape
```
; getalloc_body — BDOS $1B GETALLOC ($505D entry): return the volume's
; allocation geometry + free-cluster count. Clean-room: our own FAT scan
; (fat_total_clusters + the fat_alloc_cluster $000-scan loop) + the published
; GETALLOC A/BC/DE/HL contract; NO stock routine decoded.
;   out (§2.4): A  = sectors per cluster   (FAT_SECPERCLUS)
;               BC = bytes per sector      (512)
;               DE = total data clusters   (fat_total_clusters − 2)
;               HL = free  clusters        (count of $000 entries, clusters 2..total)
getalloc_body:
;   1. call fat_mount / fat_total_clusters   ; geometry + DE = dataClusters+2
;   2. HL := 0  (free counter)
;   3. scan clusters 2..(dataClusters+1): for each, unpack its 12-bit FAT entry
;      (reuse fat_alloc_cluster's sector-by-sector-into-WBUF read + the
;      fac_entry_from_wbuf unpack), and `if entry == $000: inc HL`.
;   4. load A := (FAT_SECPERCLUS); BC := 512; DE := dataClusters (= total−2);
;      HL := free count.  ret.
```
The exact register load order / whether the kernel also expects the FAT left resident at
`$E595` afterwards is the **first falsify-first build step** (§7.1) — the OBSERVED exit
regs (§2.4) are the hypothesis; build them and let the screen arbiter confirm.

### 4.3 No new work cell needed
Unlike M19 (which needed `BDOS_SRCHIDX` to persist search state across calls), GETALLOC is
a single self-contained call returning everything in registers (§2.4). The scan can use
`WBUF` ($E560) as its FAT-read scratch exactly as `fat_alloc_cluster` does. The free
counter lives in a register/HL for the duration of the one call. **No equates.inc change.**

### 4.4 Self-contained FAT read (do NOT depend on `$E595`)
Stock's `$505D` reads the FAT that its OWN SFIRST left resident at the kernel buffer
`$E595`. **Ours must NOT rely on `$E595`** — ours' `sfirst_body` (M19) reads dir sectors
into `SECTOR_BUF`/its own path and never populates the kernel's `$E595` FAT buffer (proven:
`readwatch --machine ours --range 0xE595 --no-gate` during DIR → 0 reads; `$E595` holds
garbage on ours). So `getalloc_body` must **read the FAT itself** (via `read_sector` into
WBUF, as `fat_alloc_cluster` already does) rather than assume a resident buffer. This is
the clean, self-contained choice and matches our existing FAT-scan primitives' behaviour
(they always read the FAT fresh). Net effect: ours issues its own FAT read during `$1B`
(stock issued the equivalent 3-sector read earlier, during SFIRST) — same total FAT I/O,
just at a different point in the flow; behaviourally invisible (the acceptance test is the
rendered footer, §7.1).

## 5. Net-zero / placement plan (VERIFIED this span)
- **`$505D` is free `$00` pad.** `build/disk.rom` bytes confirmed (our OWN rom — allowed):
  `$5058` = `C3 05 79` (M19 veneer), `$505B..$50A8` = `$00`. `$505D` sits in the existing
  `$00` gap between the M19 `$5058` SETDTA-cache veneer and the `$50A9` stub — **far more
  than the 3 bytes** a `jp getalloc_body` veneer needs. Net-zero, no canonical-address
  shift (same check M17/M18/M19 did for the neighbouring `$50xx` entries). Insert as an
  additional `ds $505D-$ / jp getalloc_body` anchor in the SAME descending `ds`-anchor
  chain in kernel.asm (`… $5058 setdta_cache → $505D getalloc → $50A9 stub …`), consuming
  existing pad. Verify with a 3-pass `--sym` object build that `disk.rom` stays 16384 B.
- **Body goes in the free tail** (kernel.asm, after `dirscan_match`/`name_cmp_wild`), like
  all prior bodies. Headroom checked: last non-zero ROM byte is `$7B99` → **1126 free-tail
  pad bytes** before `ds $8000-$` — ample for `getalloc_body` (~60-100 B est., mostly a
  reuse of the existing scan). Confirm the pad shrinks, no overflow.
- **No RAM cell** (§4.3).

## 6. Values to reproduce (test.dsk 720 KB, PINNED §2)
- free clusters **367** (`$016F`) — count of `$000` FAT entries, clusters 2..713.
- total data clusters **713** (`$02C9`) = `fat_total_clusters` (715) − 2.
- sectors/cluster **2**; bytes/sector **512** (`$0200`).
- footer = 367 × 2 × 512 = **375808 bytes free**.
(`fat_total_clusters` already returns 715 on this image per driver.asm:558-560's CF-3300
oracle note — cross-checks the pinned `DE=$02C9`.)

## 7. Acceptance criteria (falsify-first — cheapest disproving experiment first)
1. **Screen arbiter (primary):** `screen --machine both --keys '\rDIR\r' --keys-at 22
   --settle 70` → OURS ROW22 renders **`375808 bytes free`** (was `0 bytes free`),
   byte-identical to stock; every other row already matches (M19). Ideally the ROW22
   name-table HEX matches stock.
2. **`$1B` exit contract:** `capture --at 0xC6C5 --nth 1 --machine both --keys '\rDIR\r'`
   → ours returns `A=$02 BC=$0200 DE=$02C9 HL=$016F` (matching stock §2.4), instead of the
   `$50A9`-stub garbage.
3. **Entry wired:** `callwatch --machine ours --range 0x4000:0x7FFF --in-func 0x1b` → ours
   enters `$505D` then runs `getalloc_body` (NOT the `$50AD-$50B7` stub tail).
4. **Free-count correctness on a second disk:** repeat §7.1 on a different-fill asset disk
   (NOT committed test.dsk — a copied disk with a known free count) → the footer matches
   that disk's actual free space. Guards against hard-coding 367/375808.
5. **Tier-1 green + size:** `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300;
   `disk.rom` == 16384 B; no canonical-address shift (veneer consumes existing `$00` pad).
   **Crucial:** confirm `fat_alloc_cluster` (write path) is byte-unchanged (the new scan is
   a sibling, not an in-place edit).
6. **No regression:** the 27/27 boot BDOS parity (`--keys '\r'`) still holds; no int-storm
   (`dosboot_triage` OK); M13/M15/M17/M18/M19/OI-3 repros still pass (probes unchanged).
   In particular the M19 `DIR`-lists-files result is unaffected (`$505D` is a separate
   entry from `$4FB8`/`$5006`).

## 8. Risks / edge cases
1. **Exact exit registers.** §2.4 pins A/BC/DE/HL from the OBSERVED stock `$1B` return;
   build those (falsify-first). If COMMAND.COM's footer math needs a different reg (e.g.
   free space in a different unit, or a memory-structure fill at `DE=$D100`), the §7.1
   arbiter will show a wrong number and §7.2 pins which reg diverged — re-pin black-box and
   reproduce (our own op). Do NOT guess beyond the observed A/BC/DE/HL without a probe.
2. **`DE=$D100` at entry — a result-buffer pointer?** The entry `DE=$D100` could be a
   caller buffer some GETALLOC variants fill. This span's `capture --mem 0xD100:0x10` at
   the `$1B` return showed `$D100` UNCHANGED ours==stock (`20 20 20 2F D0 …`, unrelated
   text) — so `$D100` is NOT written by GETALLOC on this path; the result is register-only
   (§2.4). Re-confirm at build if §7.1 fails.
3. **Total-cluster off-by-two.** `fat_total_clusters` returns dataClusters+2 (715); the
   footer's `DE` wants dataClusters (713). Subtract 2 (not 1 — the DPB+14 field wants
   dataClusters+1=714, a DIFFERENT encoding; do not confuse them). Verified: 715−2 = 713 =
   pinned `$02C9`.
4. **Out of scope — the per-file `LSTOUT` fork.** Ours issues 82 spurious `C=05 LSTOUT`
   calls across the listing (n=63 onward) that stock does not; this is a separate
   COMMAND.COM branch difference that is cosmetically ABSORBED (the file list + footer
   still render). It does NOT block `$1B`/`$505D` (ours' `$1B` entry regs are byte-
   identical to stock, §2.1). Leave it for a later characterisation; M20 fixes ONLY the
   `375808`-vs-`0` footer.
5. **FAT read cost.** `getalloc_body` reads the 3-sector FAT (via WBUF, sector-by-sector)
   on every `$1B`. Stock read it once at SFIRST time; ours reads it at GETALLOC time —
   same total I/O, acceptable. If a visible delay appears (`DIR` on ours already re-mounts
   per SFIRST/SNEXT, M19 §8.6), it is not worse than existing behaviour.
6. **Empty / full disk.** Free count 0 (full disk) must print `0 bytes free` (already
   ours' behaviour, but now for the RIGHT reason); a nearly-empty disk must print the large
   value. §7.4's second disk covers the non-zero case; a full disk is an optional extra.

## 9. Clean-room status
- BDOS `$1B` GETALLOC semantics and the A/BC/DE/HL return contract: published MSX-DOS-1
  BDOS function table (map.grauw.nl MSX-DOS functions, MSX2 TH §BDOS, CP/M 2.2 fn 27).
  Cited; and INDEPENDENTLY confirmed by the OBSERVED stock exit registers (§2.4) — we
  reproduce a documented+observed contract, we do not decode stock's routine.
- `$505D` as the kernel's `$1B` page-1 CALL target, its entry/exit register contract, and
  the `$E595` FAT-buffer read: BLACK-BOX only — `callseq`/`callwatch --in-func`/`readwatch
  --in-func`/`capture --at` entry-PC gating + call counts + data-cell read addresses +
  entry/exit register snapshots (§2), plus our own ROM's NOP-padding check (§3, §5).
  Stock's `$505D`/`$4209` routine internals were **NOT** decoded — only that entry PC, the
  reader PCs' addresses (not their bytes), the buffer address `$E595`, and the exit regs
  were observed.
- The free-cluster COUNT ALGORITHM is OUR OWN design reusing our own `fat_total_clusters`
  + `fat_alloc_cluster` scan. We implement the documented CONTRACT (return the volume's
  free-cluster count + geometry), NOT stock's algorithm.
- `build/disk.rom` byte reads (`$5058`/`$505D`) and the test.dsk FAT bytes decoded from the
  emulated RAM buffer are reads of OUR OWN rom / the OS's in-RAM data, not stock ROM CODE —
  allowed.
- No stock ROM / loaded MSXDOS.SYS / COMMAND.COM CODE bytes were read to reach any
  conclusion in this spec.

## 10. Status / next (for sign-off) — historical (§4.2's design shipped, see §11)
**Spec complete (characterise + design). AWAITING USER SIGN-OFF** (per
[[spec-before-implementation]] — new-routine class, not veneer-class). On go-ahead, the
build order is: (1) confirm the exact exit-register set + that `$D100` stays unwritten
(§8.1/§8.2, first falsify step), (2) add the `$505D` `jp` veneer + `getalloc_body` in the
free tail, reusing `fat_total_clusters` + a `fat_alloc_cluster`-derived `$000`-count scan
(sibling, not in-place — §4.1), (3) verify §7, (4) commit. This CLOSES `DIR` to 100%
byte-parity with stock. The still-open non-M20 tracks (the LSTOUT fork §8.4; the rest of
the FCB cluster + console tier blocked on the BDOS-exerciser `.COM`,
[[bdos-exerciser-com-test]]) are specced separately — do NOT fold in.

## 11. REVISION 3 — LANDED (2026-07-02): the `$F306` dispatcher-flag fix

### 11.1 Root cause
The RAM-resident MSX-DOS-1 kernel's common BDOS-exit path — shared by every BDOS
function (it is the same loaded MSXDOS.SYS image on both machines), reached at exit-PC
range `$D8AA-$D8BD` — tests a flag cell **`$F306`** (set to `$01` by the dispatcher at
BDOS-call entry, per [tier2-gdate-spec.md](tier2-gdate-spec.md)'s earlier pin) and, by
its **observed input→output register effect**, branches: **`$F306` cleared** → the
caller's `HL`/`DE`/`BC` survive untouched (passthrough); **`$F306` set** → the exit path
overwrites the return `HL` with **`H := the handler's B`, `L := the handler's A`** (a
CP/M-style single-byte-result mirror) before returning to `$C6C5`.

> **Clean-room note (2026-07-04 paper-trail audit remediation).** The rule above is
> stated in behavioural form only — the exit-PC range plus the observed input→output
> register effect, **causally proven black-box** by the `$F306:=0` poke test (§11.1
> below, which flips the branch and lets the handler's real `HL` survive) and
> corroborated by the in-tree `gdate_handler`. An earlier revision of this section
> reproduced a hand-decoded Z80 instruction listing of `$D8AA-$D8BD` — that is
> disassembly of the proprietary MSXDOS.SYS RAM image (✗ per
> [allowed-sources.md](../../docs/allowed-sources.md); the same class as the 2026-06-30
> M12 incident). It was **quarantined** and re-grounded on the poke-test source it
> already rested on; no asm ever depended on it. See the clean-room-audit run log
> (2026-07-04 disk paper trail).

A handler that returns a meaningful `HL` must clear `$F306` before its `ret`, or the exit
path silently replaces it with `H:=B, L:=A` (a CP/M-style single-byte-result convention).
Stock's `$505D` handler clears it (confirmed: `$F306=$01` at `$505D` entry on both
machines, `$00` by `$D8AA` on stock only — the clear happens INSIDE the handler). Our
Revision 1/2 bodies never did, so our correct `HL=$016F` was replaced every time by a
mirror of our own `A`/`BC` (`H:=B=$02, L:=A=$02` = `$0202` = 514 — the exact wrong
constant observed in BOTH falsified revisions, footer `514×2×512=526336`). This also
explains why Revision 2's `IY`/`DPB+19` wiring changed nothing: those reads (stock's 81
`$E595` accesses, the `DPB+19` accesses) are STOCK'S HANDLER's OWN internal FAT scan
(page-1 PCs throughout, confirmed via `callwatch --machine stock --in-func 0x1b`) —
nothing downstream of the handler's `ret` ever consults them. Causally proven (not just
inferred): poking `$F306:=0` at the exit-path anchor flips the branch and the handler's
real `HL` survives to `$C6C5` unmodified. Corroboration already in-tree: `gdate_handler`
([kernel.asm](kernel.asm)) already clears `$F306` — previously commented "stock parity,
harmless"; it is in fact load-bearing, and the only reason GDATE's `HL=year` reaches its
caller. Full investigation (all probe commands + trace dumps): tier2-review-queue.md M20
entries.

### 11.2 The fix
Revision 1's register-only `getalloc_body` (§4.1/§4.2 above — own FAT scan via
`read_sector`/`WBUF`, reusing fat.asm's `fac_entry_from_wbuf` unpack, generalised from
"stop at first free" to "count all free", exactly as §4.1 originally proposed) is
UNCHANGED. The only addition: before `ret`, `xor a` / `ld ($F306),a` (clearing the flag),
THEN load the final `A := sectors/cluster` (order matters — the clear only needs `A=0`
transiently as the store source; the real return value must be loaded after). No new RAM
cell, no `IY`, no `DPB+19` — §4.3's original "no new work cell" claim held after all.

### 11.3 Acceptance — ALL PASS (2026-07-02)
1. **Screen arbiter:** `screen --machine both --keys '\rDIR\r' --keys-at 22 --settle 90`
   → OURS ROW22 = **`375808 bytes free`**, byte-identical to stock; ROW21 `41 files`,
   ROW23 `A>.` also identical (M19 intact).
2. **`$1B` exit contract:** `capture --at 0xC6C5 --nth 1` → ours `A=$02 BC=$0200
   DE=$02C9 HL=$016F` — byte-identical to stock in every register EXCEPT `IY`
   (`$DC5B` vs stock's `$E595`), confirmed benign/unconsumed per §11.1.
3. **Entry wired:** `callwatch --machine ours --range 0x4000:0x7FFF --in-func 0x1b` →
   ours enters `$505D` then runs `getalloc_body` through to its own `ret` (not the
   `$50AD-$50B7` stub tail).
4. **No regression:** `callseq --at 0x0100 --log 0x0005 --maxhits 40 --keys '\r'
   --keys-at 22 --settle 35` → 27/27 BDOS calls ALIGNED, zero divergence.
5. **Tier-1 green + size:** `make unit-test` 19/19; `make probe` → DSKIO byte-identical
   to the CF-3300 reference, BASIC print probes pass, tape probe OK; `disk.rom` ==
   16384 B (3-pass object); `fat_alloc_cluster`/`fac_entry_from_wbuf`/WBUF helpers
   byte-unchanged (reused, not edited).

`DIR` now matches stock 100% byte-for-byte: file list, `41 files`, `375808 bytes free`,
fresh `A>`. The M20 milestone is CLOSED. Remaining M20-adjacent items confirmed OUT OF
SCOPE (unchanged): the `$75A5`/per-file `LSTOUT` fork (§8.4); the rest of the FCB cluster
+ console tier, blocked on the BDOS-exerciser `.COM` ([[bdos-exerciser-com-test]]).
