<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M24 — the FCB **write-tier** kernel entries `$461D`/`$477D`/`$456F` (BDOSX3 FCLOSE crash root cause; the `$456F` NOP-slide → BC=0 LDIR bomb) — CHARACTERISATION + fix-shape spec

**Status: M24 crash fix + M25 RDSEQ fix both LANDED (2026-07-03).** M24
(slice A+B) fixed the FCLOSE crash; M25 (this doc's "UPDATE 2" section)
fixed the follow-on discovery that `$477D` is shared between WRSEQ and
RDSEQ, restoring general-purpose RDSEQ correctness under a real booted
kernel. See "M25 RESOLVED" below for the fix and full re-verification.
Two unrelated, pre-existing divergences were found and confirmed NOT caused
by either fix (FCB field mirror gaps, RDBLK content, and a FREN-onward
cascade in BDOSX3) — logged as an M26 candidate, not yet investigated.

**Status: SLICE A+B IMPLEMENTED (2026-07-03, signed off "good findings,
continue").** All three veneers (`$461D → bdos_create`, `$477D → wrseq_body`,
`$456F → bdos_close`) landed per §6; `ROM` stays 16384 B. Original
characterisation pass (below) is unchanged and still accurate for the
pre-fix state. **Result: the crash is GONE — BDOSX3's full 24-record/65-call
sequence now completes on ours (previously died at call n=48/record 10).**
27/27 boot callseq, DIR screen (45 s settle), Phase-1 BDOSX, BDOSX2, BDOSX0
all re-verified zero-diff/byte-identical; `make unit-test` 19/19; `make
probe` all green.

**UPDATE 2026-07-03 (follow-up investigation, corrects the residual note
above): the real bug is NOT record 13's FCLOSE — it's a universal RDSEQ
($14) regression introduced by slice B's `$477D → wrseq_body` wiring, and
the "Phase-1 BDOSX zero-diff" regression check that supposedly cleared this
commit was a FALSE PASS (anchor collision, see below). Status: CONFIRMED
ROOT CAUSE, fix NOT YET IMPLEMENTED — awaiting sign-off.**

**Misattribution correction.** The `callseq --log 0x0005` entry-register dump
used to diagnose the original residual logs registers *at BDOS-call entry*,
not at return. `A` is not an input to any of these calls, so it is leftover
from whichever call last touched it. Re-deriving from `regs` snapshot-buffer
memory (`build_bdosx3_disk.py`'s own `regs = fcb-relative` addressing, each
record 8 bytes: `regs + N*8`, byte +1 = A, byte +7 = L) shows the *actual*
per-call recorded results:

- record 12 RDSEQ (`regs+12*8+1` = `$0436`): **ours = `$FF`, stock = `$00`.**
- record 13 FCLOSE (`regs+13*8+1` = `$043E`): ours = stock = `$00` — **no
  divergence at all.** The earlier "FCLOSE A=$FF" claim was `callseq`'s
  logged entry-A for the FCLOSE call, which is really RDSEQ's leftover
  result (nothing between the two calls touches `A` — confirmed by reading
  `probes/disk/bdosx3.asm`'s `snap` routine, which doesn't clobber `A`, and
  the source between the RDSEQ and FCLOSE calls, which has no `ld a,...`).
- record 14 FREN (`regs+14*8+1` = `$0446`): ours = `$FC`, stock = `$00` —
  a second, likely-downstream divergence (not yet explained; may cascade
  from record 12's failure corrupting FCB state consumed by FREN's own
  directory search).

**Confirmed root cause: `$477D` is called by the real kernel during EVERY
RDSEQ ($14), not only WRSEQ ($15).** `callwatch --in-func 0x14 --machine
ours` on BDOSX3's record-12 RDSEQ shows PC visiting exactly
`$477D → wrseq_body ($7B11) → bdos_seqwrite ($46EE) → bsw_err ($472C)` —
the same write-path chain M24 slice B wired for WRSEQ. Since `BDOS_WRMODE`
is legitimately `0` during any read, `bdos_seqwrite`'s `ld a,(BDOS_WRMODE);
or a; jr z, bsw_err` guard fires and returns `A=$FF` — and this becomes the
RDSEQ call's own final, visible result. Register snapshots taken at `$477D`'s
entry (`BC=0000, DE=IY=$DA40, HL=5800, AF=2220`) are IDENTICAL in shape
between a genuine WRSEQ call (occurrence #1, record 1) and this RDSEQ call
(occurrence #10, record 12) — no register at entry distinguishes direction,
so `$477D`'s real contract is broader than "the WRSEQ worker": it looks like
a shared "prepare/verify current record" step the kernel calls for BOTH
sequential read and write, with direction determined some other way (not
yet identified — possibly the kernel expects the page-1 body itself to
consult FCB state, not a register).

**This is NOT scoped to BDOSX3's edge case — it is universal.** Re-running
the SAME `callwatch --in-func 0x14` + `capture --mem` check against
Phase-1's `BDOSX.COM` (`probes/disk/build_bdosx_disk.py`, a plain
FOPEN→RDSEQ×2 read of a pristine pre-seeded file, no write/reopen involved
at all) shows the identical chain firing **twice** (once per RDSEQ call),
and both calls' own recorded `A` results are `$FF` (ours) vs `$00` (stock)
— `regs+2*8+1` = `$0351` and `regs+3*8+1` = `$0359`, both diverge. Worse:
the ACTUAL DATA delivered to the DTA is also wrong — `capture --mem
0x400:0x20` shows ours reading all `$00` from `$040E` onward where stock
shows the real deterministic file-content pattern. This means
`bdos_seqread_body`'s own record-copy `LDIR` likely never executes at all
for these calls (matches the killed follow-up agent's own last observation
before it stalled: "zero writes during func $14 — the data landed in rdbuf
at some other time") — the kernel appears to abort the whole RDSEQ call as
soon as `$477D` returns non-zero, never reaching the real transfer step.

**Why the M24 slice A+B regression suite didn't catch this: an anchor
collision, the exact pitfall `disk_probe_diff.py`'s own docs warn about.**
The previously-run "Phase-1 BDOSX zero-diff" check used
`build_bdosx_disk.py`'s auto-printed `capture --at <done> --keys ...`
hint verbatim, with no `--arm-check-*`. `BDOSX.COM`'s `done` self-loop
address (`$01BC` in this build) happens to collide with something hit
*twice within the first 1.2s of boot*, long before keys are even typed
(`--keys-at 20`) — so occurrence #1 (and #2) fire on unrelated pre-boot
state that trivially matches on both machines, and the check reported
"zero-diff" without ever actually comparing post-execution state. Arming on
`--arm-check-addr 0x0102 --arm-check-val 0x01` (the loaded COM's own
fingerprint byte) fixes the alignment (both sides then hit the real `done`
loop around t≈25-27s) and immediately exposes the divergence above. BDOSX2
doesn't exercise RDSEQ at all (grepped, no `$14` in `bdosx2.asm`), so it
could never have caught this regardless.

**Proposed fix shape (NOT implemented — needs sign-off given the widened
blast radius):** `$477D`'s body must stop assuming "this call always means
write". Concretely: read `BDOS_WRMODE` as `wrseq_body`/`bdos_seqwrite`
already do, but when it reads `0` (a read-mode context), return success
(`A=$00`, no-op) instead of falling into `bsw_err`, so the kernel proceeds
to whatever it does next for the real record transfer (presumably the
already-wired `$4558 → bdos_seqread_body` veneer, unchanged since before
M24). When `BDOS_WRMODE` is `1`, keep today's behaviour (full
`bdos_seqwrite` call) unchanged — WRSEQ correctness (records 1-9, verified
zero-diff) must not regress. This is a small, targeted change (a new
`wrseq_body` that branches on `BDOS_WRMODE` before deciding whether to
forward into `bdos_seqwrite` or just return `A=0`), but it needs a falsify-
first pass — specifically confirming (a) that the real record data is
correctly delivered to the DTA once `$477D` stops short-circuiting the
kernel's read path, and (b) that WRSEQ's own `$477D` hits (which also see
`BDOS_WRMODE=1` correctly) are unaffected — before committing. **Recommend
a fresh, narrowly-scoped investigation/implementation pass focused on: (1)
confirm the no-op-on-read-mode fix restores correct RDSEQ data+status on
both BDOSX and BDOSX3, (2) re-run the FULL regression suite this time WITH
correct arm-check anchoring on every self-looping `done`-style probe
(BDOSX, BDOSX2, BDOSX0) to close the false-pass gap, (3) re-check record
14's FREN `A=$FC` divergence once RDSEQ is fixed, since it may simply
disappear as a downstream effect.**

**UPDATE 2 2026-07-03 (implementation attempted, REVERTED — this is bigger
than M24's scope, needs a dedicated follow-up milestone, not a slice fix).**
Tried the proposed no-op-on-read fix above; it did NOT restore correct
RDSEQ data, and a second attempt also failed. Both attempts were reverted
(`git checkout -- disk/kernel.asm`) — the tree is back to the exact
`a435292` committed state (crash-fix only, no RDSEQ change). `disk/kernel.asm`
was NOT re-committed with either attempt below; this section is a record of
what was tried and ruled out, for whoever picks this up next.

- **Attempt 1 (no-op success on `BDOS_WRMODE==0`, as proposed above):**
  confirmed via `callwatch --in-func 0x14` that this DOES stop `bdos_seqwrite`/
  `bsw_err` from running, and the RDSEQ call's own status register is now
  correctly `A=$00` (verified: `regs` buffer diff dropped to 0 bytes for the
  status fields). **But the actual DTA content is still all `$00`** where
  stock delivers the real file bytes — no better than before. Checked
  whether the kernel then calls the existing `$4558 → bdos_seqread_body`
  veneer to do the real transfer, as the fix shape assumed: it does NOT —
  `callwatch --in-func 0x14 --range 0x4550:0x4570` shows **zero hits** in
  that range during any RDSEQ call. `$4558` is the COMMAND.COM-load-specific
  entry (per its own header comment in `disk/driver.asm`), not a general
  per-record RDSEQ path arbitrary `.COM` programs take. So the fix's premise
  — "make $477D a clean no-op and let the kernel/veneer do the real read
  elsewhere" — is falsified: there is no "elsewhere" being called.

- **Attempt 2 (make `$477D`'s read branch actually call `bdos_seqread`,
  reseeding `BDOS_DTA` from `DOS_DTAPTR` first, symmetric with the write
  branch):** since `$477D` really does appear to be the ONLY page-1 entry
  the kernel touches per RDSEQ record, tried making it genuinely perform the
  read. Result: `bdos_seqread` now executes (confirmed via `callwatch`,
  distinct new PCs entered), but it immediately returns **EOF (`A=$01`)**
  instead of delivering data — `BDOS_BYTESLEFT` reads `0` at this point.
  Root cause: `BDOS_BYTESLEFT`/`BDOS_RECIDX` (the state `bdos_seqread`
  depends on) are seeded ONLY by `bdos_open` (`disk/driver.asm:458-483`,
  our OWN internal FOPEN, used when there is no real DOS kernel) and by
  `bdos_rdblk` (`disk/driver.asm:618-646`, the boot-loader's own local
  reseed for `$27` RDBLK). **Neither ever runs for a real kernel-driven
  `$0F` FOPEN in the DOS-boot scenario** — that path goes through
  `fopen_fill_body` (`disk/fat.asm:1166+`, wired to veneer `$4462`, M21a),
  which by its own documented scope ("owns ONLY +14(high)..+31" of the FCB)
  deliberately does NOT touch `BDOS_BYTESLEFT`/`BDOS_RECIDX` or call
  `fat_open` to re-prime the iterator. So `bdos_seqread` has no valid state
  to work from after a real kernel FOPEN — it was apparently designed
  assuming a caller (`bdos_open`) that never actually runs in this context.

**The real picture this exposes: general-purpose RDSEQ (`$14`) correctness
for an arbitrary `.COM` program, under a REAL booted MSX-DOS-1 kernel, may
never have been genuinely verified — going back further than M24.** The
"Phase-1 BDOSX zero-diff" claim (this milestone and earlier ones) rested on
an anchor-collision false pass (see UPDATE 1 above); once corrected, RDSEQ's
actual data delivery in this exact scenario (`FOPEN` via the real kernel →
`$14` RDSEQ) has NEVER shown correct output in any probe run this session,
under the original committed code OR either fix attempt. Whether RDSEQ ever
worked correctly for OTHER call patterns already exercised elsewhere (e.g.
the boot-time `$27` RDBLK path used to load `MSXDOS.SYS`/`COMMAND.COM`,
which DOES seed `BDOS_BYTESLEFT` itself and is unaffected by any of this) is
not in question — only the plain `$0F FOPEN` → `$14 RDSEQ` sequence an
ordinary user program uses.

**This needs a dedicated investigation milestone, not a same-session slice
fix.** Two open architectural questions block a real fix: (1) does the real
kernel expect `$477D`'s read branch to do a full `bdos_seqread`-equivalent
transfer (in which case `fopen_fill_body` needs to grow to also seed
`BDOS_BYTESLEFT`/`BDOS_RECIDX`/prime the FAT iterator, extending its scope
well past M21a's original "owns only +14..+31" boundary), or (2) does the
kernel do its own internal record delivery via low-level DSKIO and
`$477D`'s real per-record job is something else entirely unrelated to data
transfer (e.g. lazy cluster-boundary bookkeeping shared by both directions),
in which case the actual bug is elsewhere (maybe in DSKIO itself, or in
alloc-map fields `fopen_fill_body` populates) and `$477D`'s read branch
should genuinely stay a no-op. Recommend scoping this as its own milestone
(tentatively M25) with a proper characterisation pass before any more code
changes — the same falsify-first discipline as the original M24 pass above,
but starting from "what does the kernel actually need from page-1 for a
generic user-program RDSEQ" rather than assuming symmetry with WRSEQ.

**M25 RESOLVED 2026-07-03 — architectural question (1) confirmed correct,
fix landed.** The missing piece was `fopen_fill_body` (disk/fat.asm, M21a):
it already has `FAT_FIRSTCLUS` and `FAT_FILESIZE` in hand from its own
dir-fill work, but never primed the READ-side iterator
(`FAT_CURCLUS`/`FAT_CLUSSEC` via `fat_open`) or seeded `BDOS_RECIDX`/
`BDOS_BYTESLEFT` — the exact state `bdos_seqread` depends on, and which
only `bdos_open`/`bdos_rdblk` ever seeded (neither runs for a real
kernel-driven `$0F` FOPEN). Fix: `fopen_fill_body` now also calls
`fat_open` and mirrors `bdos_open`'s own `BDOS_RECIDX`/`BDOS_BYTESLEFT` seed
(disk/fat.asm), and `wrseq_body` ($477D's body, disk/kernel.asm) now
dispatches on `BDOS_WRMODE`: nonzero → `bdos_seqwrite` (unchanged), zero →
`bdos_seqread` (previously a no-op that never restored correct data —
architectural question (2), "the kernel does its own DSKIO read", is now
FALSIFIED; `$477D` really is the one shared entry and needed the full
`bdos_seqread` call, not a no-op).

**Verification (all re-run WITH `--arm-check-addr 0x0102`/`--arm-check-val`
anchoring this time, closing the UPDATE 1 false-pass gap):**
- BDOSX3 record 12 RDSEQ + record 13 FCLOSE (the originally reported bug):
  **zero-diff**, confirmed via `capture --mem 0x435:0x10` (both status and
  the FCB proper).
- Phase-1 BDOSX records 2-3 RDSEQ: status registers zero-diff; full 384-byte
  file content (`--mem 0x400:0x180`) zero-diff.
- Two divergences found but confirmed PRE-EXISTING (byte-identical between
  this fix and the `a435292` baseline, rebuilt and diffed directly) —
  unrelated to this fix, logged here rather than silently dropped: (a)
  `fopen_fill_body`'s own FCB mirror fields at FCB+16/17/20/21/24/28/29
  (`0x310-0x321` in the BDOSX probe) diverge from stock — likely a separate,
  never-before-correctly-anchor-tested gap in the +16..31 field population;
  (b) BDOSX's own `$27` RDBLK call shows a real content divergence from
  `0x500` onward (stock delivers `$00`, ours delivers real trailing file
  bytes) — RDBLK reseeds its own state independently and is unrelated to
  this fix. Both are pre-existing and out of scope here; worth their own
  characterisation pass later (tentatively M26).
- BDOSX3 records 14+ (FREN `A=$FC` and a wider cascade through record 23):
  ALSO confirmed pre-existing/byte-identical vs. the `a435292` baseline —
  unrelated to the RDSEQ fix, likely more un-wired canonical entries in the
  FREN/FDEL/RDRND/WRRND/RDABS/WRABS call family. Same M26 candidate as above.
- BDOSX2 (doesn't exercise RDSEQ): zero-diff, correctly re-anchored
  (`--arm-check-addr 0x0102 --arm-check-val 0xcd`).
- BDOSX0: `callseq --log 0x0005` 43/43 shared calls aligned, no divergence.
- Boot `callseq` (18 shared calls to the `A>` prompt): aligned, no divergence.
- DIR screen at 45 s settle: byte-identical (VRAM name-table + hex dump).
- `make unit-test`: 19/19. `make probe`: all green.

`ROM` stays exactly 16384 B, no 64KB-wrap warnings on rebuild. Changes:
disk/fat.asm (`fopen_fill_body` read-state seed) and disk/kernel.asm
(`wrseq_body` dispatch) only — no driver.asm changes needed this round.

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
