<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M24 — the FCB **write-tier** kernel entries `$461D`/`$477D`/`$456F` (BDOSX3 FCLOSE crash root cause; the `$456F` NOP-slide → BC=0 LDIR bomb) — CHARACTERISATION + fix-shape spec

**Status: SLICE A+B IMPLEMENTED (2026-07-03, signed off "good findings,
continue").** All three veneers (`$461D → bdos_create`, `$477D → wrseq_body`,
`$456F → bdos_close`) landed per §6; `ROM` stays 16384 B. Original
characterisation pass (below) is unchanged and still accurate for the
pre-fix state. **Result: the crash is GONE — BDOSX3's full 24-record/65-call
sequence now completes on ours (previously died at call n=48/record 10).**
27/27 boot callseq, DIR screen (45 s settle), Phase-1 BDOSX, BDOSX2, BDOSX0
all re-verified zero-diff/byte-identical; `make unit-test` 19/19; `make
probe` all green.

**New residual found post-fix (NOT yet root-caused, logged for a follow-up
slice):** starting at call n=51 (record 13, the FCLOSE after the
reopen+RDSEQ readback — a READ-mode close that should hit `bdos_close`'s
cheap `BDOS_WRMODE==0` fast path), ours diverges from stock in register
content (not call sequence — the full 65-call sequence still aligns
1:1): ours returns `A=$FF` where stock returns `A=$00`. `BDOS_WRMODE` is
reset to 0 unconditionally inside `bdos_close_write` regardless of the
record-10 close's own success/failure, so by n=51 it should read 0 and hit
the READ-close fast path — the A=$FF result implies either `BDOS_WRMODE` is
somehow nonzero here, or the write-close path's flush/`fat_dir_update` is
executing when it shouldn't. Similarly, record 21's FCLOSE (n=62) and
record 23's WRABS (n=65) and a few `SETDTA` calls (n=56/58/60) show smaller
register (HL/B) mismatches — an FCB content diff (`capture --mem
0x3b0:0x125`) confirms real content divergence, not just snapshot-buffer
noise, from offset `$0436` onward (inside the `regs` snapshot array — expected,
mirrors the known register diffs) and at `$03B1-$03D0` (inside the FCB
proper — NOT yet explained). Screen is byte-identical end-to-end (no crash,
clean final frame) so this is a correctness gap, not a stability one.
Recommend a fresh characterisation pass (same black-box method as this
doc) scoped to "why does a read-mode FCLOSE report A=$FF post-M24-slice-B" —
not yet dispatched, awaiting direction.

--

Below is the ORIGINAL characterisation pass (pre-implementation). Shape/rigor template:
[tier2-m22b-conout53a7-spec.md](tier2-m22b-conout53a7-spec.md); ground truth
[tier2-STATE.md](tier2-STATE.md); the exerciser design this executes:
[tier2-bdos-remaining-spec.md](tier2-bdos-remaining-spec.md) §5.3; fix-shape
precedents [tier2-m19-spec.md](tier2-m19-spec.md) (SFIRST/SNEXT bodies),
[tier2-m21-spec.md](tier2-m21-spec.md) (generic `k_47B2` trusts our own FCB state).

## 0. TL;DR

BDOSX3's 24-record mutation lifecycle dies at record 10 (FCLOSE, shared-prefix 47
calls): ours never issues call n=48 and the screen shows a genuine crash (corrupted
VDP state). Root cause, pinned black-box and confirmed mechanically:

- **The RAM kernel implements the FCB WRITE functions itself and CALLs a family of
  page-1 canonical worker entries — all un-wired on ours.** Our own Tier-1 write
  substrate (`bdos_create`/`bdos_seqwrite`/`bdos_close`, `fat_flush_data_sector`,
  `fat_alloc_cluster`, `fat_dir_create/update`) **never executes in DOS mode**: at
  FCLOSE time every `BDOS_WR*` cell is still virgin `$FF` and `callseq --log 0x4B34`
  shows 0 ours-side calls. The M24 briefing's suspect list (ffds cluster math, FAT
  linking, DIRSEC/DIROFF) is exonerated wholesale — that code never ran.
- Three dispatcher-class entries pinned this pass (all `ret=$D88A`, DE=IY=`$DA40`
  = kernel FCB work pointer): **`$461D`** (FMAKE worker, 1× per `$16`),
  **`$477D`** (sequential-write record worker, exactly 1× per `$15` — it does the
  buffering AND the flush I/O internally on stock), **`$456F`** (FCLOSE finaliser,
  1× per `$10` — ~2.6 s of flush+FAT+dir disk work for a dirty file, quick return
  for a read-close).
- On ours each CALL lands in unrelated own code/pad ("pad-slide luck" class,
  M22b §2.1): `$461D` = mid `rdb_byteloop` → exits via `rdb_eof` **A=$01** (this IS
  the n=37 register oddity — a real early symptom of the same root cause, not a red
  herring); `$477D` = the last pad byte of `ld hl,0` in `fat_mount` → 256×
  `add hl,de`/`djnz` spin + **clobbers FAT_FIRSTROOT/ROOTSECS/FIRSTDATA from stale
  SECTOR_BUF bytes**, returns Cy=0 (kernel satisfied; file data silently discarded —
  ours "runs" the 9 writes in 26 ms with zero disk I/O, stock takes ~1 s);
  **`$456F` = the `$00` pad byte before `bsr_have` → falls into the sequential-READ
  record copier with ambient `BDOS_BYTESLEFT=0` → n=0 → `ld c,a`/`ld b,0` → `LDIR`
  with BC=0 = a 65,536-byte copy** (captured live: `BC=0000 DE=0880 HL=E420` at
  `$45A0`) that sprays the entire RAM map — TPA, kernel, work area, stack, hooks —
  crashing inside the FCLOSE call. That is the observed divergence + VDP-garbage
  signature.
- Phase-1/BDOSX and every boot FCLOSE survived the **same** `$456F` fall-in only by
  luck: captured there, the LDIR ran with `BC=0080 DE=0500` (stale internal DTA) —
  a benign 128-byte copy. Two independent accidents (this and the `$477D` Cy=0
  return) kept the write tier looking green until the first FMAKE lifecycle.
- Fix shape (§6): wire the three entries as veneers onto bodies that reuse our
  proven Tier-1 write substrate (the M21b `k_47B2` pattern: trust our own state,
  reseed the DTA from `DOS_DTAPTR`), with `BDOS_WRMODE` gating the FCLOSE body so
  read-closes stay no-ops. Do NOT implement beyond FCLOSE-visible scope until the
  post-crash records (FREN/FDEL/RND/ABS) can run at all.

## 1. Reproduction (committed tree, `build/disk.rom` as-is)

```
python3 probes/disk/build_bdosx3_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
    --out /tmp/zerobas_bdosx3.dsk        # prints done=0x0333 etc.; bdosx3.com byte@$0102 = $03
python3 probes/disk/disk_probe_diff.py callseq --log 0x0005 --maxhits 70 \
    --diska /tmp/zerobas_bdosx3.dsk --keys '\rBDOSX3\r' --keys-at 20 --settle 60
```
→ FIRST DIVERGENCE at call n=48; shared identical prefix = 47 calls (n=47 = record-10
FCLOSE, entry `A=00 B=00 DE=03B0 HL=0000 ret=01D7`, both sides). `screen --machine
ours` (same keys) → corrupted frame (scrmod=78, garbled rows) = crash, not hang.
All probes below use the same disk/keys and arm on the loaded program
(`--arm-check-val 0x03`, fingerprint byte `$0102` — never the bare anchor, per the
false-positive-alignment trap).

## 2. Falsification pass

### 2.1 "FCLOSE returns; the crash is between records 10 and 11" — REFUTED
`capture --at 0x01D7 --nth 1 --arm-check-val 0x03` → stock reaches the post-FCLOSE
return at t=29.0573; **ours NEVER reaches it** (alignment guard: MISALIGNED). The
crash is entirely inside the BDOS `$10` call.

### 2.2 "The bug is in our new M24 write machinery (ffds cluster math, fat_alloc_cluster linking, fat_dir_create/fdc_useslot DIRSEC/DIROFF, fat_dir_update)" — REFUTED
That code is unreachable in DOS mode:
- `callseq --log 0x4B34` (`fat_flush_data_sector`): **ours 0 calls** over the whole
  run (stock's 3 hits at that numeric address are its own internal helper, callers
  `ret=$477B/$478E` — page-1-internal, not kernel ABI, and all post-FCLOSE).
- `capture --at 0x456F --mem 0xE4B0:0xB0` on ours at FCLOSE time:
  `BDOS_WRMODE/WRCLUS/WRFIRST/WRSECIDX/WRBUFLEN/WRBYTES` (`$E546-$E555`) are ALL
  virgin `$FF` — `bdos_create`/`bdos_seqwrite` never ran; FMAKE/WRSEQ were handled
  kernel-side. The hand-trace of `ffds_nopad_body` was correct but moot.

### 2.3 "The n=37 SETDTA A/HL oddity is unrelated leftover state" — REFUTED (real early symptom, same root cause)
n=37's entry `A/HL` are simply FMAKE's exit values (bdosx3 executes only
`ld ix/ld (ix+0)/call snap/ld de/ld c` in between — none touch A/HL). Ours' FMAKE
exit A=$01 is produced deterministically by the `$461D` fall-in: our
`rdb_byteloop` (which happens to sit at `$461D`) reads stale `RDBLK_CNT≠0`, sees
`BDOS_BYTESLEFT=0`, and exits via `rdb_eof` (`ld a,$01`); the kernel's `$F306`
mirror (M20 rule) then hands the program `HL:=H(B),L(A)=$0001`. Stock's real worker
exits A=$00 → `HL=$0000`. Same un-wired-entry family as the crash, one call
earlier — an early symptom, NOT the crash mechanism and NOT a red herring.
(Ours-side region walk during func `$16`: enters `$461D,4620,4624,4627,462B` then
`$4657`=`rdb_eof` — no stores on that path, so the fall-in is otherwise benign.)

### 2.4 "A `$456F`-class call would have crashed Phase-1/boot too, so `$456F` can't be it" — REFUTED (luck, twice measured)
`$456F` IS called in the green Phase-1 BDOSX run (1× each side, entry-identical bar
caller-scratch HL). Ours fell into the same `bsr_have` — but captured at the
`$45A0` LDIR there: `BC=0080 DE=0500 HL=E2A0` (BYTESLEFT was ≥128, stale internal
DTA `$0500`) → a harmless 128-byte copy. In the BDOSX3 run the ambient state is
different (`BYTESLEFT=0` after the .COM load streamed to EOF) → `BC=0000` → 64 KiB.
The severity is ambient-state-dependent; the entry was always broken.

### 2.5 "Ours' WRSEQ actually wrote the data via some other path" — REFUTED
Ours' records 0-10 all execute within t=22.835..22.861 (26 ms, no disk I/O; stock
spends ~1 s on the same records with visible flush gaps, e.g. 0.8 s inside record
5's `$477D` call). Ours' func-`$15` page-1 activity is ONLY the `$477D..$47A6`
fat_mount fall-through (with 489× `$477E` loop re-entries from `djnz` with B=0) —
no sector write path is ever entered. The 9 records' register-identity to stock is
an artifact of the fall-in returning Cy=0/A=$22 and the kernel not consuming more.

## 3. The pinned canonical entries (black-box, stock = oracle)

Method: `callwatch --in-func 0x16/0x15/0x10` (region entry sets, both machines) +
`callseq --log <entry>` (caller ret + entry regs + counts) + alignment-guarded
`capture --at 0xD88A` armed on the entry (exit regs). All runs armed on
`[$0102]==$03`.

| fact | `$461D` | `$477D` | `$456F` |
|---|---|---|---|
| role (observed) | FMAKE `$16` create worker | WRSEQ `$15` per-record worker (buffer + flush I/O inside) | FCLOSE `$10` finaliser (flush dirty data + FAT + dir; fast path for read-close) |
| calls per func | 1× per FMAKE (both sides) | exactly 1× per WRSEQ record — 9/9 aligned, entry byte-identical | 1× per FCLOSE incl. read-closes (stock 3× = records 10/13/21; t=26.44/30.22/36.70) |
| caller | kernel dispatcher, `ret=$D88A` | same | same |
| entry regs | `A=21 B=00 C=00 DE=DA40 HL=039A` | `A=22 B=00 C=00 DE=DA40 HL=5800` (n=1; then `HL=0000`) | `A=21 B=00 C=00 DE=DA40 HL=varies` (caller scratch: 0000/0001/0050) |
| kernel FCB ptr | `DE=IY=$DA40` in every call — the write-tier family signature (A=$21 create/close class, A=$22 write class; B carries no `$xx`-low-byte fingerprint here, unlike the M22a eleven) | same | same |
| stock exit (at `$D88A`) | `AF=0044` (A=00), BC=FFFA DE=DA5F HL=ED4D IY=ED35 | `AF=0044` (A=00), BC=0001 DE=0000 HL=0002 IY=DA40 | `AF=0042` (A=00), BC=0301 DE=0007 HL=E595 IY=DA40; IX=F195 all three |
| stock work window | dir scan `$5622-$5692` (11× loop), `$5FBD-$608E`, `$6375`, `$784E-$7865` | `$41F4-$421E`, `$4555/4563`, `$487D-$48F2`, `$4CA3-$4D27`, `$4EF8-$4F63`, `$5496-$54CB` | `$440E-$4438`, `$5604-$5692` (8×/72× loops); record-10 call spans t=26.44→29.06 (~2.6 s of disk writes) |

Exit BC/DE/HL look like internal scratch (not established load-bearing); A=$00 + Z
flag is the result surface. The addresses in "stock work window" are UNCLASSIFIED
(kernel-ABI vs stock-internal) except the three entries above, which are proven
kernel-ABI by `ret=$D88A` callseq evidence. Repro one-liners:

```
python3 probes/disk/disk_probe_diff.py callseq --log 0x477D --maxhits 12 --arm-check-val 0x03 \
    --keys '\rBDOSX3\r' --keys-at 20 --settle 60 --diska /tmp/zerobas_bdosx3.dsk   # 9/9 aligned
python3 probes/disk/disk_probe_diff.py callwatch --in-func 0x10 --machine both --arm-check-val 0x03 \
    --maxhits 200 --keys '\rBDOSX3\r' --keys-at 20 --settle 60 --diska /tmp/zerobas_bdosx3.dsk
python3 probes/disk/disk_probe_diff.py capture --at 0xD88A --nth 1 --machine stock \
    --arm-addr 0x456F --arm-cond '[debug read memory 0x0102] == 0x03' \
    --keys '\rBDOSX3\r' --keys-at 20 --settle 60 --diska /tmp/zerobas_bdosx3.dsk
```

## 4. What ours does today (all byte checks: `build/disk.rom`, our own artifact)

- **`$456F`** — `$4558` holds the `jp k_4558` veneer (C3 30 78), `$455B-$456F` is
  `$00` pad, `bsr_have` starts at `$4570`. A CALL to `$456F` executes one NOP and
  falls into `bsr_have` (driver.asm `bsr_have`, the seq-READ record copier). With
  `BDOS_BYTESLEFT=0` (ambient after any completed `k_47B2` load): n:=0 →
  `ld c,a / ld b,0` → **`LDIR` with BC=0 = 65,536 iterations**. Captured live on
  ours at `$45A0`: `BC=0000 DE=0880 HL=E420 SP=DBFC` — source walks from
  SECTOR_BUF+3·128 through the whole address space, destination from `$0880`
  upward through the TPA, page-3 work area, the RAM kernel (`$C000+`), the stack
  and every hook. 190+ interrupt re-entries were observed mid-LDIR before the
  machine state disintegrates → crash inside FCLOSE; n=48 never issued; VDP left
  corrupted by subsequent wild execution. Also decrements BYTESLEFT and bumps
  RECIDX (moot).
- **`$477D`** — lands on the third byte (`$00`) of fat_mount's `ld hl,0` at
  `$477B`, i.e. `nop`; then `$477E add hl,de` / `$477F djnz $477E` runs 256× (entry
  B=0, DE=$DA40 — the observed `HL -= $25C0 (mod 64K)` walk and B=FF,FE,… ladder;
  the "calls" logged at `$477E` are these loop iterations with the kernel's
  `$D88A` return still on the stack, not real calls). Falls through fat_mount's
  tail: **overwrites `FAT_FIRSTROOT` (`$E4A3`), `FAT_ROOTSECS` (`$E4A5`),
  `FAT_FIRSTDATA` (`$E4A7`) from garbage HL + stale SECTOR_BUF BPB offsets**, then
  `or a / ret` → Cy=0, A=$22 preserved. Self-healing for later readers (every
  FOPEN/SFIRST path re-runs `fat_mount`), but the record data is silently
  discarded.
- **`$461D`** — our `rdb_byteloop` (driver.asm) happens to start exactly there;
  see §2.3. Exit A=$01 (vs stock $00) — the sole register-visible symptom before
  the crash.

## 5. Pinned contracts (what the fix must reproduce)

1. **`$456F` (FCLOSE finaliser):** entry per §3; must make a write-opened file
   durable (flush buffered partial sector, complete the cluster chain, rewrite the
   dir entry with true size + first cluster) and be a cheap no-op for read-closes
   (stock's record-13/21 calls return in milliseconds). Exit A=$00/Z on success.
2. **`$477D` (WRSEQ record worker):** entry per §3, one call per 128-byte record;
   consumes the record from the kernel DTA (**`DOS_DTAPTR` `$F23D`**, NOT our
   stale `BDOS_DTA` — the M21b lesson, verbatim); accumulates the true byte count;
   performs sector-granular writes as the buffer fills (stock's timing gaps show
   the flush happens inside this call, not at close). Exit A=$00.
3. **`$461D` (FMAKE worker):** entry per §3; creates/truncates the directory entry
   (stock's 11× `$5622-$5692` loop = root-dir slot scan) and primes the write
   state. Exit A=$00.
4. **`$F306` rule (M20, general):** none of the three stock exits carries a
   load-bearing HL as far as observed (BDOSX3's own records only consume A);
   default = leave `$F306` semantics exactly as the proven read-side bodies do,
   and pin per-entry only if a divergence shows in the acceptance diff.
5. Exit BC/DE/HL/F beyond A+Z: observed values recorded in §3 but NOT established
   as contract; the acceptance oracle is the full BDOSX3 differential (register
   snapshots + buffer + FCB memory diff), which will catch any consumer we can
   reach without asserting unobserved semantics.

## 6. Proposed fix shape (M24; for sign-off — do NOT build yet)

Class: M19/M21 — three byte-exact-position veneers in existing pad/collision-free
spots + bodies in free tail reusing OUR proven Tier-1 write substrate (no stock
algorithm; same clean-room posture as `k_47B2`). Net-zero; ROM stays 16384 B.

- **`$461D: jp fmake_body`** — `$461D` currently = `rdb_byteloop` REAL code, so
  this is a RELOCATION case (M21a-RC-1 convention): move the colliding
  `bdos_rdblk` interior (or just `rdb_byteloop..rdb_eof`) to a free tail with the
  established `jr→jp` treatment, then anchor the veneer. `fmake_body` ≈ our
  `bdos_create_body` semantics driven from the kernel context: `fat_mount` +
  `fat_dir_create(kernel-FCB name)` + prime `BDOS_WR*`, exit A=$00/$FF. The name
  source inside the `$DA40` kernel FCB must be pinned first (one `capture --mem
  0xDA40:0x30` at entry, both machines — data cells, allowed).
- **`$477D: jp wrseq_body`** — `$477D` is the tail byte of a `ld hl,0` inside
  `fat_mount`; splitting there needs the same relocation treatment for
  `fat_mount`'s tail (or move `fat_mount` wholesale to the free tail and leave a
  label veneer — position-free, reached only by `call fat_mount`). `wrseq_body` ≈
  `bdos_seqwrite` with `BDOS_DTA` reseeded from `DOS_DTAPTR` (`$F23D`) at entry
  (M21b rule) — buffers 128 B into SECTOR_BUF, flushes via the EXISTING
  `fat_flush_data_sector`/`fat_alloc_cluster`/`fat_write_fat_entry` chain when
  full. This is where the M24 briefing's never-exercised second-cluster
  allocation finally runs — on OUR substrate, whose hand-trace (ffds_nopad_body
  `cp (hl)` boundary math) already looks right and now becomes testable.
- **`$456F: jp fclose_body`** — pure pad today (`$455B-$456F` all `$00`);
  3-byte veneer, no relocation. `fclose_body` = our `bdos_close` gated on
  `BDOS_WRMODE` (read-close → `xor a; ret`, matching stock's fast path; dirty →
  flush partial sector + `fat_dir_update`). NOTE: `bdos_close` itself lives at
  `$469A` and is position-free — the veneer can `jp bdos_close` directly if the
  register/exit surface survives the acceptance diff.
- **State hygiene:** `fmake_body` must fully prime `BDOS_WR*` (they are `$FF`
  garbage in DOS mode until then) and the write path must not depend on any
  Tier-1-only initialisation. `BDOS_BYTESLEFT` stays a read-side cell; the fix
  must NOT repurpose it.
- **Explicit non-goals for the first slice:** FREN `$17` / FDEL `$13` /
  RDRND-WRRND `$21/$22` / RDABS-WRABS `$2F/$30` — unreachable today (the run dies
  at record 10). Expect additional un-wired entries behind them; land the three
  above, re-run BDOSX3, and characterise the NEXT first-divergent record with this
  same method before writing more bodies (the remaining-spec's "localise, then
  STOP" rule).

Build order falsify-first: slice A = `$456F` veneer alone (3 bytes in pad, zero
relocation risk). Prediction to verify: the LDIR bomb disappears and FCLOSE
returns, but the lifecycle then diverges at reopen/readback (records 11-12,
because FMAKE/WRSEQ still discard data) — that observed divergence pattern is
itself the confirmation that §4's model is right. Then slice B = `$461D` +
`$477D` (the two relocations + bodies) to make the whole 24-record run
diff-clean.

## 7. Acceptance criteria

1. **BDOSX3 full pass:** `capture --at 0x0333 --arm-check-val 0x03 --machine both
   --mem 0x03b0:0x125` (FCB+regs) and `--mem 0x04d5:0x380` (data buffers) →
   alignment guard passes on BOTH machines; byte-diff zero, or a localised
   post-record-10 divergence that becomes the next milestone's evidence.
2. **The three entries align:** `callseq --log 0x461D/0x477D/0x456F` → counts and
   entry regs ours==stock (1×, 9×, 3× in this scenario); exit A=$00 at `$D88A`.
3. **n=37 symptom gone:** the callseq n=37 SETDTA entry shows `A=00 HL=0000` on
   ours (FMAKE now exits A=$00).
4. **Durability proof (the real oracle):** records 11-12 (reopen + RDSEQ readback
   of `wrpat`) and 14-16 (rename/delete/negative-open) byte-identical — this is
   the second-cluster FAT-allocation evidence the milestone was designed to
   produce; plus `screen --machine both` → both sides end at an intact frame.
5. **No regression:** 27/27 boot callseq; Phase-1 BDOSX capture zero-diff; BDOSX2
   14-record zero-diff; BDOSX0; DIR screen byte-identical; `make unit-test`
   19/19; `make probe`; `disk.rom` == 16384 B (3-pass object).
6. **Docs:** [tier2-bdos-coverage.md](tier2-bdos-coverage.md) rows
   `$15/$16` (+`$10` write-close) updated with the new entries;
   [tier2-STATE.md](tier2-STATE.md) next-action overwrite; the `$4555/$4563`
   classification residual (§8) carried forward.

## 8. Residuals / open questions (none block sign-off)

1. **`$4555` / `$4563` (+`$4566/$4569`)** appear as region entries in stock's
   `$15`/`$16` windows. On ours `$4555` is mid-`jp` operand and `$4563` is pad
   sliding into `bsr_have` — if either is kernel-ABI (not stock-internal), it is a
   fourth/fifth un-wired entry. Ours' windows show no CALL arriving there in THIS
   scenario; classify with `callseq --log` the moment any future record diverges.
2. The FREN/FDEL/RND/ABS windows (records 14-23) are uncharacterised — blocked
   behind the crash; expect more entries (see §6 non-goals).
3. The kernel-FCB layout at `$DA40` (name offset for `fmake_body`) — pin by a
   data capture at implementation time, both machines.
4. Stock's `$4B34` helper (callers `$477B/$478E`, args C=$80 DE=file-offset
   HL=buf-ish) is page-1-internal on stock; our `fat_flush_data_sector`
   coincidentally sits at that address — no action needed, noted to prevent a
   future "canonical address?" wild-goose chase.
5. Whether the `$477D` geometry-cell clobber (§4) has any reachable consequence
   pre-fix (all known readers re-mount first) — moot once wired, listed for
   completeness.
6. Exit F for `$461D/$477D` is `$44`, `$456F` `$42` — recorded, not asserted
   load-bearing (same posture as M22b §5.1).

## 9. Clean-room status

- **No stock ROM / MSXDOS.SYS / COMMAND.COM code bytes read, dumped, or decoded.**
  Stock-side evidence in this pass: entry-PC sets and counts (`callwatch`
  opcode-fetch region entries), caller-ret + registers at published/observed call
  points (`callseq`, `capture`), timings, and screen renders — observation classes
  already established for M17-M22. The §3 "work window" columns are entered-PC
  sets, not decodes.
- Every byte-level decode in §4 is of OUR OWN `build/disk.rom` (verified
  byte-identical to a fresh assemble of our own source) — clean-room by
  construction.
- The three entries are de-facto page-1 kernel-ABI addresses (class of
  `$4010`/`$5454`/the M22a eleven; [spec-diskrom-kernel.md](spec-diskrom-kernel.md)
  §1.3), pinned purely by call-target observation.
- Proposed bodies reuse OUR substrate (fat.asm/driver.asm write-back layer, built
  from the Microsoft FAT spec + published BDOS contracts per disk/PROVENANCE.md);
  no stock algorithm is reproduced.
- Test-disk hygiene: every run used `/tmp` copies (the harness copies `--diska`
  per run; the builder copies test.dsk); `git status` clean throughout; committed
  images untouched.

## 10. Impact / recommendation (headline for sign-off)

The M24 exerciser did exactly what its spec predicted ("expect an M13→M21-class
big body behind an un-wired entry; localise, then STOP"): the entire DOS-mode FCB
**write tier** rests on three un-wired canonical entries, and the write machinery
we built for Tier-1 has never run under the kernel. The crash is the `$456F`
NOP-slide's BC=0 LDIR under ambient `BYTESLEFT=0`; the n=37 oddity is the same
family's benign face. Recommend implementing §6 as ONE milestone (slice A then
slice B, falsify-first), with the explicit expectation that records 14-23 will
surface a follow-up entry batch. STOP: awaiting sign-off; no asm has been touched.
