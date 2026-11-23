- [ ] 🟢 **STEP 9 RE-OPENED WITH AN ANSWER: `LOAD` HAS CELLS OF ITS OWN, AND THE
      REFERENCE'S LOOP IS **PER SECTOR** — SO THE SLICE THAT WAS BUILT IS THE
      WRONG SHAPE.**
      🎚️ TIER 5 — on-par speed, on `LOAD`. ⏱ **RE-TAGGED 2026-10-10 FROM TIER 2:
      REASONABLE TIME ON `LOAD` IS MEASURED MET.** A 14 KB `LOAD"x",R`, timed
      OUTSIDE the guest (emulated time between two `CURLIN` writes,
      [`loadclock_probe.py`](scratchpad/loadclock_probe.py)): **8.3 s here
      against the CF-3300's 2.7 s, 3.0×** after D-LOADDI (6.9 s, 2.5× before it,
      [`loadclock_run.out`](scratchpad/loadclock_run.out) /
      [`loadclock_after.out`](scratchpad/loadclock_after.out)) — inside T2's 10×.
      What is left here is S10.C (OPEN's channels into disk.rom), ruled *"defer
      to later"* on 2026-10-09, and the speed.
      📏 **RE-MEASURED 2026-11-06** ([`loadclock_1106.out`](scratchpad/loadclock_1106.out)): 14 KB
      **8.94 s here against the CF-3300's 2.94 s** (1 KB: 0.75 against 1.36 -- the fixed cost
      is LOWER here; ~310 ms an extra sector against ~60). **WHERE IT GOES** -- every FDC
      command stamped in emulated time ([`fdccmd_probe.py`](scratchpad/fdccmd_probe.py) ->
      [`fdccmd_run.out`](scratchpad/fdccmd_run.out), a 14 KB program SAVEd then LOADed,
      [`loadspeed_prog.bas`](scratchpad/loadspeed_prog.bas); and 1 ms PC samples,
      [`loadspeed_pc.out`](scratchpad/loadspeed_pc.out): the time is in fdq_win /
      frdw_poll, WAITING for sectors): (1) **LOAD re-reads FAT sector 2 before every
      cluster** -- fat_next_cluster (basic/fat-prim-body.inc) reads the FAT sector into
      FAT_DBUF on EVERY call, there is no read cache; 47 reads for a 29-sector file, ~20 of
      them the same FAT sector, each a rotational wait. (2) **Adjacent data sectors land
      ~113 ms apart** (one passes every ~22 ms): the processing between them misses the
      next. (3) **SAVE rewrites BOTH FAT copies per cluster**, and a FAT sector written right
      after it was read costs a full revolution (~200 ms) -- D-RECSLOW's class (W3b).
      Every command is preceded by a seek-verify (1C), cheap (~1 ms) on the same track.
      ➡️ ~~NEXT: (1) a FAT READ cache in FAT_MBUF~~ -- FAT_MBUF is NOT a FAT-only buffer (the
      directory work goes through it too: 39 sites), and the reference's way is the whole
      FAT in RAM (1.5 KB for 720 KB). 🙋 **FOR JOOST: a FAT buffer in RAM is a RAM-layout
      choice (the TIER 4 rung's rule) -- may LOAD / file reads keep the FAT in a new
      1.5 KB RAM buffer (the disk build's free memory is ahead of the CF-3300's)?** Until
      then (1) waits; (3) and (2) do not need it.
      🏗️ **RULED (Joost, 2026-11-06): *"yes, go for the 1.5 KB FAT buffer, if reference does it,
      so should we"*.** The CF-3300's kernel keeps the whole FAT resident (`$E595`, loaded ONCE
      by a 3-sector DSKIO on the first search -- disk/docs/tier2-m20-spec.md §2.3); the disk
      build does the same: load on mount, chains from RAM, both copies written back on flush,
      dropped on a media change. (1) is unblocked.
      ⏸️ **RE-DONE, MEASURED, AND PARKED AGAIN (2026-11-07) -- THE GAIN IS GONE.** Built in
      D-DISKCARVE's room ([`fatres_wip2.patch`](scratchpad/fatres_wip2.patch): the gate's bit 7, one DSKIO per sector with
      interrupts open between, a write / FAT-entry write dropping bit 0; tests/test_fat_next_cluster.py
      green with the per-sector and forbidden-bit rows). **LOAD with it: 1 KB 0.63 s, 7 KB 2.59,
      14 KB 4.73** ([`loadclock_fatres2.out`](scratchpad/loadclock_fatres2.out)) -- **but today's HEAD WITHOUT it is already 0.62 / 2.59 /
      4.92** ([`loadclock_head1107.out`](scratchpad/loadclock_head1107.out)): the 11-06 HEAD's 8.94 s has halved through other work since
      (the 11-06 notes' (2) and (3) and the carves), and the resident FAT now buys -4 % on 14 KB and
      nothing on 7 KB or 1 KB. Not worth ~140 B of disk.rom and a RAM-ownership gate around
      MSX-DOS and every boot code; Joost's ruling ALLOWED the buffer, it did not require it.
      🔮 "~5.5 s": the number was right for the build, the premise (that FATRES is the lever)
      was stale -- measure HEAD before re-doing a parked speed slice. What is left of the gap to
      the CF-3300 (4.92 vs 2.94 s on 14 KB, 1.67x; 7 KB 2.59 vs 2.39) is per-sector CPU work and
      lost-data retries (the 11-06 FDC log), not FAT re-reads.
      📏 **TODAY'S SHAPE (2026-11-07, [`fdccmd_1107.out`](scratchpad/fdccmd_1107.out), the 14 KB LOAD's FDC commands in emulated
      time):** consecutive sector reads land either ~30 ms apart (the next sector caught) or
      ~230 ms apart (missed by a hair: one revolution, 200 ms at 300 rpm, lost), and one sector
      (S 04) took two lost-data retries -- ~0.63 s by itself. The work between two reads (the
      512-byte copy alone is ~3 ms) is longer than the inter-sector gap, so roughly every other
      sector costs a revolution; the CF-3300 averages ~100 ms a sector, ours ~170.
      📏 **HOW THE CF-3300 DOES IT (2026-11-07, Joost: "I guess we need to discover how the
      references do this?"; [`fdccmd_cf1107.out`](scratchpad/fdccmd_cf1107.out) -- fdccmd_probe.py's FDC_MACH: the same WD2793,
      "National" layout, slot 3-1, per openMSX's machine config; command register writes
      with BC / DE / HL, registers and I/O only):** the FAT sectors into its own buffer
      ($E795 / $E995); the FIRST data sector into a sector buffer ($ED95) -- it carries the
      $FF header byte, so its 511 B go to $8001..$81FF; then EVERY following full sector
      STRAIGHT TO ITS FINAL ADDRESS ($8200, $8400, ... -- HL steps $200 per read command,
      one command per sector, ~20 ms apart when the next is caught); the LAST partial sector
      into the buffer again. ~~It misses a revolution only ... 3-4 misses per 14 KB~~ 🔴
      ~~WRONG ... misses 12 of 26 gaps (and B counts down from $1B: ONE multi-sector
      DSKIO)~~ 🔴🔴 **CORRECTED 2026-11-08: THAT COUNT WAS ITS *SAVE*.** The probe program
      SAVEs then LOADs, and the `A2` / `AA` run with HL stepping $200 from $8200 (B counting
      down from $1B) is the WD2793's WRITE SECTOR -- SAVE writing the program straight from
      memory. The LOAD's READS (`82` / `8A`) also land in place, $8200 .. $B600, so the
      design above stands; but they miss **4 of 26** gaps (the second LOAD **2 of 26**), and
      their BC is the driver's register pointer ($7FBC), so whether the LOAD is one DSKIO
      is NOT visible.
      ➡️ **THE PLAN (no new RAM: the reference's own design):** zerobas's LOAD reads every
      sector into SECTOR_BUF and copies it. Read the full sectors of each contiguous run
      DIRECTLY into the program area -- the first sector (header) and the last partial one
      through the buffer, as the reference does; a run is consecutive sectors of one cluster,
      or of consecutive clusters. Witnesses: loadclock_probe (14 KB 4.92 s now, CF 2.94) and
      fdccmd_probe (the read commands' HL should step $200, as the CF-3300's do).
      ✅ **D-LOADDIRECT, DONE (2026-11-07).** disk/runtime.asm `hdl_direct` reads the file IN
      PLACE (the first sector's rest out of FAT_DBUF, every full sector through
      basic/fat-prim-body.inc's new `frs_to` entry -- one DSKIO a sector -- the last partial
      one through FAT_DBUF), then disk/kernel.asm `hdl_walk` applies the old stream's rules to
      the bytes in place; the stream (hdl_line / hdl_body / hdl_get_store, D-LOADRUN's
      hdl_run, D-LOADBASE's hdl_scan) is gone, and the swap is byte-neutral (disk.rom holes
      190 B after against 189 before). tests/test_loadrun.py is rewritten: a Python
      transcription of the stream's rules, checked against BOTH builds -- HEAD's disk.rom
      agrees on all 25 parse rows (cuts, corrupt links, a $C001 base, a failing sector), so
      the transcription is the old code's behaviour, not mine -- plus the in-place witness
      (24 data sectors at $8200..$B000 step $200). **ONE CHANGE, AT TXTMAX:** a file whose end
      lies past TXTMAX is now `out of memory` with nothing read (the stream read until TXTMAX
      and then said the same; both leave dpl_oom's empty program). The stream accepted a
      file up to 2 B longer (its $0000 end link was never stored); the direct read must not
      write past TXTMAX, the workspace floor, during the read. What the CF-3300 does with a
      file that does not fit is NOT measured (filed below).
      🎯 PREDICTED 14 KB 3.0-3.3 s: **3.28 s -- hit** ([`loadclock_direct.out`](scratchpad/loadclock_direct.out)): **1 KB 0.62 -> 0.57 s
      (CF 1.36), 7 KB 2.59 -> 2.26 (CF 2.39, now FASTER), 14 KB 4.92 -> 3.28 (CF 2.94: 1.67x ->
      1.11x).** FDC log ([`fdccmd_direct.out`](scratchpad/fdccmd_direct.out)): the in-place run is 29 reads in 3.02 s with 11
      revolutions missed, ~~the CF-3300's 27 in 2.99 s with 12 -- on par in the data phase~~
      🔴 **WRONG (corrected 2026-11-08): those 27 were the CF-3300's SAVE writes. Its LOAD
      reads miss 4 of 26 (1.32 s) -- it catches more sectors than we do; the totals are near
      par because other phases are faster here.**
      ➡️ **WHAT IS LEFT (filed, TIER 5): the lost-data retries.** The `80` reads from the retry
      site ($7AD9, B = 4) cost a revolution each: two on the LOAD's first FAT read, two in the
      data run. That is D-FDCDI's interrupt window landing at a data start (the ISR runs, the
      first DRQ is lost). The CF-3300's log shows none. 🔭 Measure first: how many retries per
      14 KB over several runs, and whether the window placement or the ISR length decides it.
      ➡️ **ALSO FILED (TIER 6): LOAD of a file too big for memory on the CF-3300** -- the
      message, whether the old program survives, whether it reads first.
      📏 **MEASURED (2026-11-07, fdccmd_probe.py FDC_DRQ=1: a D row at each command's first
      data-register read, a J row at each JIFFY write; [`fdcdrq_cf.out`](scratchpad/fdcdrq_cf.out) / [`fdcdrq_zb.out`](scratchpad/fdcdrq_zb.out)).** 🎯 Predicted
      "the CF-3300 waits masked": **hit -- 0 interrupts in 77 read waits** (its one ISR per
      sector runs in the gap between commands); ours took interrupts in 34 of 49 waits, one
      0.1 ms before the data start -- the lost-data source. **AND THE BIGGER LEVER:** our
      misses alternate exactly -- the next command leaves ~2.6 ms after a transfer ends
      (caught) inside a cluster, ~6.6 ms after (missed) at a cluster boundary (fat_advance's
      path); the CF-3300 issues the next 0.6-2.6 ms after every transfer, from ONE DSKIO
      (B = $1B) with no FAT work between sectors.
      ~~➡️ NEXT (D-LOADRUNS): ... ONE multi-sector DSKIO~~ **BUILT, MEASURED, REVERTED (2026-11-07).**
      🎯 Predicted 14 KB 1.5-2.2 s: **4.66 s -- a miss, the wrong way** ([`loadclock_runs.out`](scratchpad/loadclock_runs.out)). The driver's own
      loop gaps alternated 2.6 / 5.7 ms after a transfer ([`fdcdrq_runs.out`](scratchpad/fdcdrq_runs.out)), and the ISR sat at
      +0.2 ms in BOTH, so the FAT walk was never the cause. PC samples on OUR ROM
      ([`isrprof_probe.py`](scratchpad/isrprof_probe.py) -> [`isrprof_runs.out`](scratchpad/isrprof_runs.out)) put **~3 ms of a scan interrupt in C-BIOS's
      key_cmp bit walk** (all 88 bits, twice a scan -- the repeat path runs it again on an
      empty buffer; C-BIOS's own `TODO: Optimise scanning if no keys are pressed`).
      ✅ **D-KEYSKIP (cbios-repack patch #14, [`keyscan-skip.patch`](cbios-repack/keyscan-skip.patch)):** a row with no newly
      pressed key skips its walk; paid for by computing the F-key index instead of five
      compare arms (13 B over: island 1's pad grows by 13 B, which D-STOPKEY3 wanted).
      🔴 The full battery caught a first cut: the skip left B = 8 where the walk's djnz
      leaves 0, so KSCAN's exit BC read $08FF against the VG-8020's $00FF
      (biosregs-acceptance) -- "nothing else changes" was the claim, and a register
      was the exception. Fixed with `ld b,0` in the skip. dimedge-acceptance's two
      REFUSED rows went to NO READING: the faster interrupt let the ERR 7 handler loop
      scroll `RUN` off the screen ([`dimedge_keyskip_screen.out`](scratchpad/dimedge_keyskip_screen.out)) -- an instrument fault;
      its reader now takes the loop's own `[ 7` output as the refusal.
      🎯 Predicted runs + D-KEYSKIP 1.5-2.2 s: **3.45 s -- a miss** ([`loadclock_keyskip.out`](scratchpad/loadclock_keyskip.out); scan gaps now
      4.3 ms, plain 2.3-2.6, [`fdcdrq_keyskip.out`](scratchpad/fdcdrq_keyskip.out)). **A/B, D-KEYSKIP with ONE DSKIO A SECTOR:
      1 KB 0.57 s (CF 1.36), 7 KB 1.65 (CF 2.39), 14 KB 3.07 (CF 2.94: 1.04x)**
      ([`loadclock_ab_persec.out`](scratchpad/loadclock_ab_persec.out)) -- so the runs went back out; frs_head stays (6 B shorter).
      ➡️ **WHAT IS LEFT (TIER 5):** (a) lost-data retries under D-FDCDI's windows -- 3 in the
      14 KB run, a revolution each; the CF-3300 waits masked (0 ISRs in 77 waits). Idea, not
      measured: mask only the first few ms after a read command (a run's next sector arrives
      inside them; a missed one still gets windows for the long wait). (b) the per-sector
      seek-verify (`1C`, ~1 ms) on the same track, which the CF-3300 does not issue -- our
      next command leaves 2.3 ms after a transfer, the CF-3300's 1.1.
      📏 **(b) BUILT, MEASURED, REVERTED (2026-11-07, D-SEEKSKIP):** the read path skipped the seek
      when the track register already held the target (the `1C` vanished between same-track
      reads, [`fdccmd_seekskip.out`](scratchpad/fdccmd_seekskip.out)). 🎯 Predicted 14 KB 2.5-2.8 s: **3.070 s, unchanged to the
      millisecond** ([`loadclock_seekskip.out`](scratchpad/loadclock_seekskip.out); re-run with ZEROBAS_REFCACHE=0: the same) -- a miss. The
      millisecond is not what decides which sector is caught; nothing shipped.
      🟢 **LOAD IS ON PAR (2026-11-07):** 1 KB 0.57 s (CF 1.36), 7 KB 1.65 (CF 2.39), 14 KB 3.07
      (CF 2.94, 1.04x). What is left is (a) above, and two things seen on the way, FILED, not
      measured: **the motor goes OFF at the end of every DSKIO** (disk/driver.asm `mtoff`, from
      `dskio_ok`), so one call a sector toggles it every sector and `fdc_settle` (~0.9 ms of
      fixed delay) runs each time -- a disk ROM normally leaves it on and turns it off from a
      timer; and the National interface's FDC_CTRL ($7FBC) READS back IRQ / !DRQ, a way to
      see a sector's first DRQ coming without polling the status register under a window.
      ~~➡️ RE-DO PLAN (2026-11-07, D-DISKCARVE freed the room:~~ ~181 B of pads, the largest 104 B
      in front of $7F7C):** scratchpad/fatres_wip.patch no longer applies (its pads were filled);
      re-place by hand, smallest risk first --
      (a) the RAM gate FIRST: FATRES must not be trusted or written while foreign code can own
          $DE8D..$E48C -- 📏 READ 2026-11-07: that range also holds OUR page-3 bridges
          (INT_H_HIRAM $DDAE..$DF10, laid at every DOS entry), so the parked layout collided
          with us too. The two hand-offs to foreign code are boot_call0 (step 5) and
          lay_page0_env (steps 6-7, MSX-DOS); a BASENT restart re-enters disk init but SKIPS the
          power-on block (init.asm `basent_pending` -> boot_disk), where DOS_F346 := 0 lives.
          RULE: a "forbidden" bit set at boot_call0's entry and at lay_page0_env; cleared at
          power-on only (beside DOS_F346 := 0) and when boot_call0's code RETURNS (a data
          disk -- then also FATRES_OK := 0, so the next mount compares / reloads); a load and a
          trusted read both require it clear. Implement with (d) -- a flag alone gates nothing;
      (b) the staleness rule: every chain read must see a FAT_DEFER-held entry -- simplest is
          "a deferral drops FATRES_OK" (wrblkalt-acceptance is the witness);
      (c) the DI gap: load the FAT in per-sector DSKIOs with the D-FDCDI windows between them,
          not one 3-sector call (programs-acceptance --gaps is the witness);
      (d) then the code itself into today's pads (fres_read, fat_res_next + frn_tail,
          fres_same + fres_cmp, the mount hook), each pad padwatch-checked before filling;
      (e) LOAD timing (loadclock_probe.py) against the 11-06 numbers.
      ⏸️ **(1) BUILT AND PARKED 2026-11-06 (D-FATRES slice 1) -- THE FULL BATTERY WENT RED 236/245,
      NOT SHIPPED. The ROM work is saved as [`fatres_wip.patch`](scratchpad/fatres_wip.patch).** Three blockers, each
      a red gate: (i) **DI gaps** -- programs-acceptance: frame-interrupt gaps up to 0.34 s in five
      ladder programs; the reload is a multi-sector DSKIO with interrupts masked, and after any
      write it waits ~a revolution for sector 1 -- the load must take the D-FDCDI windows (or
      run in pieces); (ii) **a correctness red** -- wrblkalt-acceptance: two FCBs alternating
      block / random I/O no longer persist as written (most likely FATRES read stale while a
      FAT_DEFER write is still held -- the old path read FAT_MBUF / the disk; every chain read
      must see the deferred entry, or a deferral must drop FATRES_OK); (iii) **MSX-DOS** --
      dosmode, dosdate, strout, dosbasic, p1dta, p1vec, callsystem: FATRES ($DE8D..$E48C) is
      inside $C000-$DFFF, which MSX-DOS uses WHILE BOOTING, before DOS_F346 says so -- the
      gate needs a condition true from the first DOS load (BASENT_REQ's DOS_TRY / a boot-path
      flag), measured. What follows is the measured design and its numbers, kept for the re-do.
      Measured first where the CF-3300
      keeps it (RAM only): the whole 1536 B FAT resident in BOTH boot modes -- drive A at $E595
      ($E5AA on a CTRL boot), the phantom B: at $DF94 -- kept current after a SAVE
      ([`fatres_probe.py`](scratchpad/fatres_probe.py) -> [`fatres_probe.out`](scratchpad/fatres_probe.out), [`fatres_b_probe.out`](scratchpad/fatres_b_probe.out)): a normal boot's
      extra 1558 B is drive B's FAT space (Joost: CTRL boot drops a drive). Joost 2026-11-06:
      build it in that gap for a NORMAL boot; a CTRL boot keeps the sector path for now.
      FATRES $DE8D (1536 B, the gap), FATRES_OK $EDBA (disk-owned, every boot mode). A mount
      KEEPS the copy when the FAT sector 1 it reads anyway equals FATRES (bytes 0..10, 24..511
      -- fat_media overwrites 11..23; a disk differing only there, or only in a later FAT
      sector, is taken for the same: accepted); otherwise one multi-sector DSKIO reloads it.
      Any dskio_write clears it; DRVCNT != 2 (CTRL boot) or DOS_F346 != 0 (MSX-DOS) clears it
      and never reads it. fat_next_cluster follows the chain from RAM. disk.rom: the code is in
      seven pad fragments (disk free now 16 usable B + the FDC window). A first cut RELOADED on
      every mount: LOAD 14 KB 8.94 -> 6.34 s, but small operations doubled (re-reading sector 1
      waits a revolution); keeping it fixed that. 🔴 Two driver ideas tried on the way (skip the
      seek-verify on the same track; settle only after a seek) measured NOTHING and were
      reverted: the FDC log ([`fdccmd_sectmiss.out`](scratchpad/fdccmd_sectmiss.out)) shows the per-sector gap is LOAD's CPU work
      (~93 ms a sector, byte by byte) plus a lost-data retry every ~4th sector -- see below.
      **After ([`loadclock_keep.out`](scratchpad/loadclock_keep.out)): LOAD 1 KB 0.75 -> 0.56 s (CF 1.36), 7 KB 4.69 -> 3.28 (2.39),
      14 KB 8.94 -> 5.54 (2.94).** 🔮 ~6.5 s for the first cut: HIT; the keep version better.
      Small operations ([`fatres_ops.bas`](scratchpad/fatres_ops.bas), jiffies @50 Hz; [`fatres_ops_head.out`](scratchpad/fatres_ops_head.out) -> [`fatres_ops2.out`](scratchpad/fatres_ops2.out)):
      20 x OPEN/CLOSE 371 -> 396, 10 x FILES 123 -> 167 (+36 %, unexplained -- FILES does not
      write), 10 x OPEN/INPUT#/CLOSE 283 -> 298; the CF-3300 32 / 10 / 33 at 60 Hz.
      tests/test_fat_next_cluster.py 33 checks (keep / reload / gating / write-drop / sector
      fallback). The work was done by a subagent from a measured brief; reviewed and measured
      here.
      🔴 **(iv) DISK ROM SPACE (2026-11-06):** D-COPYALL took ~86 B of the 262 the patch was
      built against (176 left), so `fatres_wip.patch` no longer fits as it stands -- and the
      other two disk-side levers here (LOAD's per-byte body copy -> one `ldir` a sector run,
      ~70 B; PUT's write cache) need room too. ✅ **D-DISKJR (2026-11-06), the first carve:**
      52 `jp` -> `jr` in disk/kernel.asm, fat.asm, runtime.asm (`scratchpad/djr.py`: a label
      before every `jp`, assembled, kept when the target is in reach; driver.asm left alone --
      the FDC loops -- and four entry vectors plus the two jumps into the FDC data bodies kept
      3 B). The bytes collect before each region's pin: `$7F7C` 30 B, `$75A5` 25 B (hdl_body's
      region); disk free 176 -> 228 B.
      ✅ **D-LOADRUN (2026-11-06): LOAD's line body a SECTOR RUN at a time.** After one body
      byte goes the ordinary way (refill / EOF), `hdl_run` (disk/runtime.asm, called from
      hdl_body in disk/kernel.asm) copies min(body left, bytes left in the sector) with one
      `ldir`, when the run fits the file (FREAD_LEFT) and stays below TXTMAX; anything else
      returns untouched and the byte path meets the edge as before. 78 B: the $7F7C region
      took it after `innoe_body`, `wrseq_body` and `install_f365` moved into holes
      ($75A5 / $44F4 / $5552; wrseq's `jr` out became a `jp`). 📏 ([`loadrun_clock.out`](scratchpad/loadrun_clock.out)
      against [`loadclock_1106.out`](scratchpad/loadclock_1106.out)): LOAD 1 KB 0.75 -> 0.62 s,
      7 KB 4.69 -> 3.80, **14 KB 8.94 -> 6.76** (CF-3300 2.94). 🔮 Predicted ~5 s for 14 KB:
      MISSED -- the per-cluster FAT re-read (blocker (1), the resident FAT) is the rest.
      tests/test_loadrun.py: the as-built LOAD against the byte path (hdl_run trapped) on a
      whole file, 17 early ends around sector edges and 4 TXTMAX collisions -- same status,
      CLPTR and RAM -- plus a two-sided step-budget control (as built finishes, the byte path
      cannot).
      ✅ **D-LOADFAT (2026-11-06): LOAD's FAT sector, read once.** fat_next_cluster read the FAT
      sector into FAT_DBUF before EVERY cluster. While hk_dpload's tokenised read runs,
      FAT_DEFER's bit 7 (unused by the write bits 0-2) is set and the FAT sector goes into
      FAT_MBUF; a one-byte cell, FAT_FCACHE ($EDBA, in both maps + the disk.asm block
      assert), says which -- read and written ONLY under that bit. Every mount zeroes
      FAT_DEFER and hdl_answer clears bit 7 (keeping a write's bits), so no channel read, no
      directory work and no MSX-DOS code sees it on; and the mount LOAD starts with means no
      deferred write is holding FAT_MBUF. A straddling entry still reads the next sector into
      FAT_DBUF, as before. 🔴 The first cut made FAT_FCACHE itself the switch and cleared it
      in fat_mount: p1dta-acceptance went RED (BDOS SEQRD under MSX-DOS = $C9) -- but the
      bisection showed the cache was innocent: see `$4775` below. The room: `install_hook` /
      `df_entptr` moved to the $4392 / $4257 holes. 🔴 **AND `$4775` IS AN ENTRY POINT THAT
      WAS NEVER PINNED.** The first placement put install_hook in the $476A..$477C zero pad,
      and p1dta went red with the cache forced off too; moving install_hook alone did it, and
      to another hole it passed. Logging our ROM's PC inside that pad under MSX-DOS
      ([`hole477_probe.py`](scratchpad/hole477_probe.py) -> [`hole477_probe.out`](scratchpad/hole477_probe.out)): MSX-DOS calls
      `$4775` (return `$D88A`, its RAM kernel) and the $00 pad ran as NOPs into k_477D's `jp
      wrseq_body`. Pinned now (`k_4775: jp wrseq_body`, fat.asm -- the slide's own effect);
      after, one instruction at $4775 ([`hole477_after.out`](scratchpad/hole477_after.out)). The pad below and between
      the pins stays empty. ➡️ the class is filed as D-PADSLIDE below. 📏
      ([`loadfat_clock.out`](scratchpad/loadfat_clock.out)): LOAD 7 KB 3.80 -> **2.59 s**,
      14 KB 6.76 -> **4.92** (CF-3300 2.39 / 2.94); 🔮 ~4.5 for 14 KB: near, a miss by 0.4.
      tests/test_loadrun.py: a 13-cluster program from cluster 2 and from cluster 338 (its
      chain crosses the straddling entry 341 and FAT sector 2) loads to the exact bytes with
      the cache off after, in exactly mount + one-per-FAT-sector (+ the straddle) FAT reads
      ([`loadfat_reads.out`](scratchpad/loadfat_reads.out): each read with its caller) where
      it read 12. tests/test_fat_next_cluster.py (the cache off) unchanged and green.
      📏 **WHAT IS LEFT OF LOAD'S 1.7x, MEASURED 2026-11-06** ([`fdccmd_loadfat.out`](scratchpad/fdccmd_loadfat.out),
      [`fdccmd_loadseek_gaps.out`](scratchpad/fdccmd_loadseek_gaps.out)): sectors now chain ~30-33 ms apart -- but after EVERY
      track change two consecutive reads miss their sector by a whole revolution (~229 ms):
      9 misses in 32 reads, on S02/S03 or S03/S04, shifting by one per track (2-sector
      clusters on 9-sector tracks). NOT the seek's verify: issuing the read seek without it
      ($18, an experiment, reverted) changed nothing ([`loadseek_clock.out`](scratchpad/loadseek_clock.out)), and NOT a
      retry (no restore command in the log). ➡️ next: what the chain does differently there
      (a cluster boundary next to the track step?) -- disk.rom has no usable room left (82 B,
      all FDC window), so the fix needs a carve too.
      ➡️ NEXT: fix (i)-(iv) above, then re-apply; (a) FILES' +36 %; (b) slice 1b / 2 (the scans and the write path from FATRES --
      frees ROM); (c) **the small-operation gap itself: 14-15x the CF-3300** (it caches far
      more than the FAT across operations); (d) LOAD's per-sector CPU (~93 ms a 512 B sector,
      byte by byte) and the lost-data retries -- what remains of LOAD's 1.9x.
      ✅ **(3) SAVE'S FAT, FIXED 2026-11-06 (D-SAVEFAT):** a tokenised SAVE is one call, so it
      holds the FAT sector in FAT_MBUF across every cluster and writes it once before the
      close's directory work -- D-RECSLOW's W3b-within-one-call. FAT_DEFER bit 2 = the hold
      (set after sav_fits, whose free count resets the flag -- the first cut set it before
      and held nothing); fdh_rehold (disk/pageenv.asm, the $4217 hole) re-asserts bit 0
      before each mark / link; fwe_finish keeps bit 2 (1 / 3 -> 2 as before); sdw_end flushes
      before fat_io_close; ffds_undefer flushes a held sector (frl_xfail). An unwound SAVE
      now leaves no half-linked clusters (the CF-3300 commits its FAT at close). Host rig
      tests/test_save_fathold.py (sav_disk_write on empty720.dsk, its own FAT12 decode):
      plain 77 -> 38 sector commands, FAT writes 28 -> 2; the chain across FAT sectors 1 / 2;
      a full disk (status 3, copies equal). Knife (no flush before the close): the file
      comes back with a 1-cluster chain. Machine: the 14 KB SAVE 168 FDC commands / 13.0 s
      -> 85 / 7.8 s ([`fdccmd_after.out`](scratchpad/fdccmd_after.out)). Docs: concepts/disk.md.
      📏 **(2) MEASURED, NOT BUILT (2026-11-06): what the LOAD does between sectors.** The whole
      tokenised LOAD runs in hk_dpload's line loop (disk/kernel.asm), one fat_io_getbyte per
      program byte: the TXTMAX check, a call, a 32-bit FREAD_LEFT test and decrement, the
      store -- ~400-450 T a byte, ~230k T (~64 ms) a sector, so the next sector has long
      passed. An LDIR run-copy of what is left in the buffer (bounded by the body length,
      512 - FREAD_OFF, FREAD_LEFT and TXTMAX) would be ~3 ms a sector -- BUT (a) it needs ~60-70
      B of disk.rom and the largest usable hole is 23 B (a carve first), and (b) even at 3 ms the
      adjacent sector's gap (~1.7 ms) is missed: catching it needs multi-sector reads into a
      buffer, which is the 🙋 RAM question above. So LOAD waits on that ruling (or a disk.rom
      carve for the run-copy alone, worth measuring after).
      ~~🙋 **NEEDS-JOOST**~~ — a far better-posed question than before.
      MEASURED 2026-09-19 (D-HOOKCOUNT, `scratchpad/hookcount_probe.py`,
      §6.6r): two independent runs, every figure identical, three controls green.
      🔴 **THE METHOD WAS THE PROBLEM ALL ALONG.** Un-claiming a cell is a
      NEGATIVE probe whose witness (an error message) travels through the
      subsystem it breaks — and because `LOAD` destroys the program that would
      print the answer, it could only use `LOAD"<missing>"`, which dies in the
      directory search and never reaches the data phase. COUNTING breakpoint
      entries fixes both: the counter is outside the guest, so a SUCCESSFUL load
      is readable.
      🟢 **`LOAD` enters FIVE cells `OPEN` does not** — `$FE67`, `$FE76`,
      `$FED0`, `$FED5`, `$FEDA` — while `$FE5D` (H.NULO) is entered once by BOTH,
      exactly as §6.6p said. The question §6.6j called unanswerable was
      answerable; its instrument could not reach it.
      🔴 **AND `$FFCF`/`$FFD4` SCALE PER SECTOR: +8 for a 1055 B program, +34 for
      14369 B.** 3 data sectors vs 29 — a difference of 26, and the counts differ
      by 26. Not time-driven (`H.TIMI` is flat across cases). So the reference
      drives its sector loop from OUTSIDE the hook, one call per sector. **Step 9
      as designed puts the whole loop INSIDE `disk.rom`, entered once — the
      opposite shape.**
      🟢 **ROUNDS 2 AND 3 (§6.6s): THE PREDICTION HELD AND THE CELL IS NAMED.**
      Stated before the run — if `$FFCF` is per-sector, the MID image must read
      exactly **+20** (15 sectors + the 5-call mount overhead). It read +20.
      Three points, one line: 8 / 20 / 34 for 3 / 15 / 29 sectors.
      🟢 The public names are VALIDATED, not assumed: `SAVE` moves `$FE6C`
      (H.SAVE) and `FILES` moves `$FE7B` (H_FILE), two independent confirmations.
      🟢 `$FFCF` is the GENERIC sector service — a `SAVE` of the same program
      adds +27 on top of the identical load, so writes pay per sector too.
      🔴 **`$FE67` IS A SHARED VERB ENTRY: `LOAD` +1, `MERGE` +1, and nothing
      else touches it.** And during a `LOAD` it is entered BEFORE `$FE5D` (seq
      17129 vs 17131), which is the signature of an ENTRY versus something the
      entry calls. **So Joost's ruling — one cell, several verbs, a selector —
      was right, and I applied it to the wrong address.** `$FE67` is where that
      shape belongs.
      ⚠️ **RETRACTED FROM MY OWN §6.6r:** "its sector loop is driven from outside
      the hook" was an over-reading. 1 at the verb cell and 29 at the sector cell
      fits a loop INSIDE the handler just as well as one in main; counts cannot
      separate them. What IS determined is that a per-SECTOR boundary exists and
      a per-BYTE one does not — so a per-sector design is faithful, and where the
      loop above it sits is OURS to choose.
      🟢 **RESOLVED (D-BLOADARM):** the BSAVE payload is now `$A5` and the case
      READS IT BACK (165, behind a `CHR$` marker so the typed line cannot be
      mistaken for the result). The fixture is valid and `BLOAD` SUCCEEDED — so
      its zero at `$FE76` is REAL. `BLOAD` enters only the shared file-buffer-0
      set and has no dedicated cell among the four.
      🔑 **The published names are worth exactly this much, measured at four
      points:** `$FE6C` H.SAVE ✅ and `$FE7B` H_FILE ✅ are borne out; `$FE67`
      H.MERG is PARTLY (MERGE enters it — and so does LOAD); `$FE76` H.BINL is
      REFUTED (BLOAD does not enter it, LOAD does). A documented name identifies
      A verb that uses the cell, not the only one, and in one case not the verb
      at all. Generate hypotheses from the names; settle them with the counter.
      ⛔ **NOTHING MAY BE INSTALLED AT `$FE67` UNTIL IT EARNS THE CLEARANCE
      `$FE5D` FAILED.** Claiming `$FE5D` broke `stop-trap-acceptance` in a way no
      reasoning predicted and only a full battery caught (§6.6p).
      🟢 **ANSWERED 2026-09-19 (D-LOADPROTO, §6.6u) — AND IT IS NO LONGER A
      CHOICE.** The retraction above was right that counts cannot separate the two
      shapes. A RETURN ADDRESS can: at a breakpoint on a hook cell the word at
      `(SP)` is the return into whoever called it, and classifying it by page +
      selected slot names the caller's ROM. **Every per-sector entry's caller is
      in the DISK ROM** — 16 of 16 at 3 data sectors, 68 of 68 at 29 — each at a
      stack depth below the verb entry, and **no disk→main crossing occurs at
      either public inter-slot entry for the whole verb**. Main calls `$FE67`
      once and the disk ROM runs mount, directory search and the entire sector
      loop on its own side.
      ➡️ **So the slice to build is the WHOLE-LOOP move, not a per-sector service
      called from main.** That is the A-vs-B question off Joost's plate: the
      reference is B, measured rather than preferred.
      🔴 **AND THE CELL IS `$FE5D`, NOT `$FE67` — CORRECTED SAME DAY (D-CROSSABI,
      §6.6v).** Reading every published slot's five bytes shows **35 of 118 are
      CLAIMED** (`F7 <slot> <lo> <hi> C9`) and that **`$FE67`, `$FE6C` and both
      per-sector cells hold a bare `C9`** — BASIC calls them, they RET, nothing
      crosses. An entry COUNT cannot tell an offered extension point from a real
      handover, so every cell ranking built on D-HOOKCOUNT was blind to it. The
      claimed cells `LOAD` enters are `$FE5D` (pairs 1 in / 1 out in all six verb
      cases) and `$FE76` (one-way, binary-format program path only). 🔑 **Joost's
      §6.6m ruling — `$FE5D` + a selector — was right, and §6.6s's correction of it
      is retracted.**
      🔑 **THE CONTRACT IS MEASURED (D-SELECTOR, §6.6w).** `DE` carries an open
      MODE — `1` input (`LOAD`/`MERGE`/`BLOAD`/`OPEN…INPUT`), `2` output
      (`OPEN…OUTPUT`), `$80` for `SAVE` — and `HL` the file buffer. `AF` is
      invariant across every verb. 🔴 **There is NO verb selector: `LOAD`, `MERGE`
      and `BLOAD` are indistinguishable at the crossing.** So §6.6m's "one cell,
      several verbs, a selector" is right about the cell and wrong about the
      selector — the shared entry needs a MODE byte, not a verb dispatch, which
      is cheaper for step 9 rather than dearer.
      🔴 **AND A PERFECT-LOOKING CANDIDATE WAS REFUTED BY ASKING WHO READS IT.**
      `$F41F` holds the statement's BASIC token at the crossing (`$B5` LOAD,
      `$B6` MERGE, `$BA` SAVE, `$B0` OPEN — matching our own oracle-sourced
      equates at all four points). A read watchpoint shows 13 reads, ALL from
      MAIN, NONE inside the crossing. It is main's own bookkeeping. That is the
      mechanism check §6.6t's parked correlation never got, and it cost one run.
      🟢 **AND THE INPUT SURFACE IS ENUMERATED (D-DISKREAD, §6.6x).** A read
      watchpoint over `$F380..$FFFF`, armed for the crossing and filtered to
      readers in the disk ROM, gives **38 distinct cells for `LOAD`, 36 for
      `SAVE`, 36 of them SHARED** — `LOAD` adds two, `SAVE` adds none, and both
      make 480 disk-side reads. `$F864..$F870` is the FILE NAME, identified by
      its bytes (`..S       BAS` / `..T       BAS`), and §6.6w's `BC = $F871` is
      exactly one past it — two independent measurements meeting. ⚠️ Scope: the
      SHARED work area only; the disk ROM's private RAM below `$F380` is excluded
      by design.
      ➡️ **So step 9's RAM dependency is small and enumerable**, which is what a
      whole-loop move needs to know before it is priced.
      🟢 **AND THE RETURN DIRECTION IS MEASURED (D-DISKWRITE, §6.6y).** The disk
      ROM writes **22** work-area cells during a `LOAD` and **16** during a
      `SAVE`, each exactly once; what main SEES changed on return is **34** and
      **11** — different sets, and the difference is the finding. 🔑 It also
      resolves §6.6x's deliberately-unnamed block: `$F568..$F574` is an OUTPUT,
      filled by the disk side and reading `.S       BAS` / `.T       BAS` on
      return, so with `$F864..$F870` it forms an input/output PAIR.
      🔴 **PART OF THE PROTOCOL EXECUTES FROM RAM, AND IT IS NOW LOCATED
      (D-RAMCODE, §6.6z).** Five clusters, ALL BELOW `$F380` — which is why the
      `$F380..$FFFF` band of §6.6x/§6.6y could report a RAM writer but not say
      where it lived: `$F1D9..$F1E1` (9 B, 582 fetches), `$F1F4`,
      **`$F255..$F2A3` (79 B, the largest)**, `$F365..$F36B`, `$F38C..$F399`
      (the stub `scratchpad/cf_trace.py` found empirically and called CLPRIM).
      🔑 **The DISK ROM writes the 79-byte block at BOOT** — t≈3.80 against a
      crossing at t≈164.03, so installed once and NOT rebuilt per call. The
      timing is measured, not inferred: the probe logs the crossing's own
      timestamp.
      🔍 **AND THE GAP ANALYSIS IS DONE (D-HOOKCENSUS, §6.7).** A hook census
      taken the SAME WAY on both machines: the reference claims **35** of 118
      slots, we claim **18**, and **ours are a strict SUBSET** — not one cell we
      claim is left bare by the reference. The census also found what reading
      `hook_tab` could not: 17 rows but 18 installed, because `disk/init.asm`
      writes `$FFA7` (HPHYD) directly for the provider direction.
      🔑 **THE HEADLINE IS THAT THE ARCHITECTURES ARE INVERTED, BY AN EARLIER
      DECISION RATHER THAN BY OVERSIGHT.** The reference keeps mount, directory,
      FAT and the sector loop in its disk ROM. We keep the FAT12 engine and the
      loop in MAIN (`basic/fat.asm`, `basic/cload.asm`) and use the disk ROM as a
      pure sector transport over `CALSLT $4010` — the committed Depth-A plan of
      `expansion-protocol.md` §4b/§5, chosen so our loader can drive a FOREIGN
      disk ROM. Step 9 is the proposal to invert it back, and BOTH directions
      have to keep working.
      🟢 **Two things got CHEAPER:** no verb selector is needed (a mode byte
      suffices), and our claimed set already nests inside the reference's.
      🟢 **AND THE RULING CUTS THE RIGHT WAY FOR A COMBO JOOST AFFIRMED
      2026-09-20:** *"the VG8020 + for example the Philips NMS Disk extension is a
      valid machine combo. In the same way our non-disk ZeroBAS + that same disk
      extension should work."* With no disk implementation left in main+sub, a
      foreign cartridge's own Disk BASIC claims the hooks and runs — §0.0's point
      (3), reached for free rather than defended.
      ⚠️ **AND THAT COMBO IS UNTESTED.** `nodisk-acceptance` runs
      `C-BIOS_MSX1_EU_REPACK_NODISK`, whose slot 3-1 is EMPTY (verified in the
      machine XML). "No disk ROM at all" and "somebody else's disk ROM" are
      different machines and only the first is covered. The rig is that same
      machine with a foreign ROM in 3-1 — `nms8250_disk.rom`, `nms8245_disk.rom`,
      `cf-3300_disk.rom` and a dozen others are already present locally.
      🔴 **Two are BLOCKING and are ONE slice:** claim `$FE5D` (§6.6t's
      correlation is withdrawn by §6.6af; what remains is the STOP re-fire
      divergence, §6.6ag) and move the loop below it (the D-DPLMOVE slice that
      was backed out).
      🏗️ **RULED BY JOOST 2026-09-20: *"I think the answer to Two is obvious: we
      do as the reference does."*** The FAT12 engine and the loader's sector loop
      MOVE OUT OF MAIN INTO `disk.rom`. Rows 2, 5 and 6 of §6.7's table stop being
      questions and become the work. This SUPERSEDES the "clean middle path" of
      `spec-diskbasic-relocation.md`, whose rejected alternative (*"move all
      disk-BASIC incl. `fat.asm`, ~5 KB"*) is now the chosen one.
      ⚠️ The ruling is about WHO OWNS WHAT, not about copying every
      implementation detail: whether we need our own equivalent of the
      reference's ~96 B of RAM-resident code (§6.6ac) is a SEPARATE question it
      does not answer, and row 8 stays open.
      🟢 **✅ STEP 9 IS DONE, 2026-09-20 (§6.6am). `LOAD` RUNS IN `disk.rom`.**
      Main is `diskslot_test`, write `FOPEN_SEL` = `$4C`, `call chan_gate` on
      `H_FOPEN`, decode `DISKOP_STATUS` (0 loaded / 1 → `df_notfound` ERR 53 /
      2 → `ascii_load` / 3 → `disk_error` / 4 → `dpl_oom`). Mount, directory
      search, FAT walk and the byte loop are `hk_dpload`'s.
      💰 **120 B of main page 1 returned, measured 2026-09-20** — `dpl_line`/`dpl_body`/
      `dpl_get_store`/`dpl_eof`/`dpl_oom_pop`/`dpl_nf` went unreachable and
      `check_dead_code` named all six. Page 1 **43 B → 154 B free** (2026-09-20;
      re-run `make basic-reloc`, never quote it). `gates-full` 132/132 plus all
      eight excluded targets.
      🔴 `dpl_nf` had to go: it read `DISKOP_OP`, which now carries the SELECTOR,
      and its own header said that is safe only while the cell is provably fresh.
      ⚠️ **§6.6q's BUFFER HAZARD IS NOT RETIRED.** It did not bite, but no suite
      runs `PAINT` then `LOAD`; `LOAD` survives because everything in the window
      is per-statement scratch. That does NOT carry to steps 10-12, which run
      mid-program against live state. First thing step 10 must answer.
      🔴 **CORRECTED SAME DAY (§6.6an): "a selector value each" WAS MY OWN
      CLAIM AND IT IS WRONG.** §6.6n's generalisation is about the SELECTOR
      MECHANISM only; each of the three has a different blocker.
      🟢 **10 `OPEN` — APPROVED BY JOOST, 2026-09-22: *"yes, we need to do
      this"***. The RAM blocker below is real and stands as a COST, not as a
      refusal: it is what the slice has to solve, and the PAINT span-stack lever
      is the named candidate (`GFX_PSTK` is a FIXED 120 × 3 = 360 B array, where
      the reference grows its spans DOWN FROM `STKTOP` and costs nothing while
      `PAINT` is not running — `docs/spec-basic-graphics-g5.md` D3).
      ⚠️ **AND IT IS DOWNSTREAM OF THE SAME-ADDRESS RULING**, which Joost
      approved in the same breath: both are about where the two ROMs' buffers
      live, and §6.6q's hazard (`GFX_PSTK` sitting in disk's `SECTOR_BUF`
      window) is the same fact seen from the other side. Settle that first.
      🛑 **THE BLOCKER, FOR THE RECORD** — RAM. A channel holds its sector
      across statements and there is nowhere to put it: §6.6al measured the
      window 510/512 full, and main's FAT buffers already carry `disk.rom`'s own
      `R30_*`/`P1_BLIT`/`PG_SV_A8`/`RDBLK_*`. ⚠️ The map's "unattributed runs"
      are NOT free — the 102 B run at `$E15A` holds five undeclared `basic`
      cells.
      🛑 **11 `MERGE`** — SHAPE. It must TOKENISE each line (main's job, via the
      sub-ROM), so a disk-side loop needs per-line call-backs that `FOPEN_SEL`'s
      aliasing forbids. §8.9 already lists the reference's shape here as NOT
      MEASURED.
      🟡 **✅ THE *SHAPE* BLOCKER IS DISSOLVED 2026-09-21 (§6.6ap, D-MERGESHAPE,
      `scratchpad/mergeshape_probe.py`) — THE PREMISE WAS THE PROBLEM.** The
      reference's disk side **never owns `MERGE`'s line loop**, so the per-line
      call-back this blocker rules out is not needed. `$FE5D` is entered EXACTLY
      ONCE for a 2-line `MERGE` and once for a 100-line one; the transfer above
      it runs per BYTE through `$FE8A` (53 entries for 53 B, 1125 for 1125 B),
      and `$FE8A` is CLAIMED on BOTH reference vendors, so each is a real
      crossing. The cells that scale per LINE are in a band neither vendor
      claims — bare `ret`s, main's side, crossing nothing.
      🔑 **`MERGE` IS ASCII `LOAD`**: an identical 47-cell set, counts differing
      by at most 1 on nine of them at both sizes. And **tokenised `SAVE` is
      tokenised `LOAD` mirrored** — one crossing, `$FE6C`, `$FE71`, +27 per
      sector, zero per-byte. **The FORMAT selects the shape, not the verb.**
      ➡️ **SO THE PORT IS**: `ex_merge`/`ascii_load` reach the crossing for the
      OPEN only (another `FOPEN_SEL` value); the per-byte cursor becomes a
      `disk.rom` service main calls per byte; `ascii_read_lines` and the
      tokeniser **do not move**. Priced at 0.156 ms/byte against the reference's
      own 4.3 ms/byte (§6.2a), and the reference pays a claimed-cell crossing per
      byte on exactly these paths.
      ⚠️ Counts give the seam's GRANULARITY, not which side holds the loop
      counter — §6.6r's retraction is not re-imported.
      🔴 **AND "UNBLOCKED" WAS TOO BROAD — CORRECTED THE SAME DAY (§6.6aq,
      D-MERGEWIN, `scratchpad/mergewin_probe.py`).** The shape above needs
      `disk.rom`'s sector buffer to survive main running BETWEEN byte reads, and
      `disk.rom` borrows main's RAM for it (`SECTOR_BUF`/`FAT_DBUF` `$E2A0..
      $E49F`). Measured on our own machine with a `write_mem` watchpoint
      bracketed by `mrg_storeline` and the next `arl_getbyte`: **DIRTY at seven
      addresses in three runs** — `SH_OP`/`SH_LEN` `$E36D..$E36E`, `SH_PTR`
      `$E371..$E372`, `SH_ERR`/`TEMPTOP` `$E37E..$E380`, 287 writes over 40
      lines. `WBUF`'s window was clean.
      🔑 **THE SURFACE IS THE ROUTINE'S, NOT THE FIXTURE'S:** a `--rich` fixture
      (quoted strings, multi-statement bodies, `REM` tails, 2224 B against
      464 B, control firing 1898 times against 258) writes **the same seven
      addresses the same 287 times**.
      ➡️ **SO THE LEVER IS ~20 B OF RELOCATION, NOT 510** — move the `SH_*`
      argument block and `TEMPTOP` out of the window. §6.6al killed relocation
      for the WHOLE window; step 11 only needs the cells this ONE path writes.
      ⚠️ The map's "unattributed runs" are NOT free space — verify a target run
      before spending it (§6.6an nearly priced against one holding five
      undeclared `basic` cells).
      ⚠️ This does NOT retire §6.6q in general: `PAINT` then `LOAD` is still
      ungated and `GFX_PSTK` still sits in the same window.
      🟢 **✅ THE RELOCATION IS DONE 2026-09-21 (§6.6ar).** `SH_OP..SH_ERR`
      moved `$E36D..$E37E` -> **`$E20D..$E21E`** (the retired `TRAPSTK`'s
      source-declared FREE-RAM run, which the 18 B block fills to the byte,
      ending one below `TRAPPEND`); `TEMPTOP` moved `$E37F..$E380` ->
      **`$E238..$E239`** (6 B of that run left). `TEMPPOOL` is now anchored
      ABSOLUTELY so the 122 B chained below it does not move into the GFX block.
      🔬 **THE PROBE THAT FOUND IT IS THE ACCEPTANCE TEST THAT CLOSES IT:**
      287 writes / 7 addresses -> **0**, with the bracket arming the same 41
      times, the byte reads the same 467 (2227 rich) and the `TOKBUF` control
      the identical 258 and 1898. Only the subject moved.
      ➡️ **SO STEP 11's RAM BLOCKER IS CLEARED** and the port itself is next.
      🟢 **✅ STEP 11 IS DONE 2026-09-21 (§6.6at, D-MERGEPORT).** `MERGE` and
      ASCII `LOAD` open through `$FE5D` (`FOPEN_SEL_AOPEN $41`) and read every
      byte through it (`FOPEN_SEL_GETB $47`); the line loop and the tokeniser
      stay in main, which is what the reference does. ONE selector pair for both
      verbs, because on the reference they are one mechanism.
      💰 **IT COSTS MAIN BYTES AND DOES NOT SAVE THEM:** main page 1 was
      **140 B → 75 B free** and `disk.rom` **7888 B → 7842 B** (2026-09-21).
      `OPEN…FOR INPUT` still needs main's `fat_io_*`, so nothing could be
      deleted; the value is §0.0's point (3), as it was for `SAVE`.
      🔴 **TWO THINGS BIT, BOTH ALREADY-NAMED CLASSES:** `mrg_ioerr` used to
      `jp df_or_loaderr`, which picks ERR 53 vs a DSKIO code by reading
      `DISKOP_OP` — and `FOPEN_SEL` ALIASES it, so every missing file would have
      reported a disk error (*a shared tail is a label, not a decision*). And
      the selector must be re-asserted on EVERY crossing, because main runs the
      sub-ROM tokeniser between byte reads.
      🔬 `disk_probe_merge` 123, `disk_probe_load_ascii` 35,
      `disk_probe_save_ascii` 42 — all differential against the CF-3300 and
      identical; `mergewin_probe.py` CLEAN on both fixtures with its control
      firing 258 / 1898.
      🔁 **RE-MARKED 2026-09-27 — THE 🙋 AT THE TOP IS STALE.** Step 9 shipped
      2026-09-20, step 11 2026-09-21, and step 10 (`OPEN`) was APPROVED by Joost
      2026-09-22 (*"yes, we need to do this"*). Its blocker is RAM, and the lever it
      names — PAINT's span stack — was ruled RE-ARCHITECT on 2026-09-27.
      🤖 **AUTONOMOUS** — ruled above; price it from a clean tree, carve first.
      ⚠️ **THE TIER TAG IS STALE (2026-10-01):** `LOAD` is T2✓ on the sheet; what is
      left here, step 10, is the ownership move, not LOAD's speed.
      ✅ **RULED (Joost, 2026-10-09): "defer to later".** S10.C leaves the
      autonomous queue: it is done with the ownership work (S10.D/E), not at
      TIER 2 now. Do not re-ask; do not pick it up until that work starts.
      ~~🙋 **TIER QUESTION FOR JOOST (2026-10-08)**~~ -- and S10.C IS BIGGER THAN ITS
      PLAN SAID. Mapped before building: a disk channel's INPUT text rules (the
      Ctrl-Z end, the numeric item's PEEK, EOF) live in the sub-ROM SEQIO tenant
      (basic/input.asm `seq_call`, SUBROM_IDX_SEQIO). That tenant runs in PAGE 1,
      and `$FE8A` is a CALLF into disk.rom, ALSO page 1 -- a page-1 tenant cannot
      call it without switching itself out. So S10.C is not "point the byte
      source at a hook": the text rules would have to be rebuilt INSIDE disk.rom
      (as S10.B rebuilt the record writer), with D-INPQUOTE2's peek. No
      user-visible defect is measured on the input side; the tag's own reason is
      met. ➡️ Meanwhile the loop takes the next MEASURED, user-visible item (the
      TIER 4 FCB header fields). The question: keep S10.C at TIER 2, or re-tier it
      with the ownership work (S10.D/E)?
      ✅ **S10.0 ANSWERED 2026-10-01 (spec §6.6bc):** the CF-3300's channel is a
      record-size-1 MSX-DOS FCB moved by 256 B BLOCK I/O. The FCB changes only at
      record boundaries; header +6 is the byte position. The design that puts the
      buffer in the BASIC FCB's record, and needs no live sector between
      statements, holds. ~~➡️ Next: S10.1, PRINT# through `$FE85`.~~
      ➡️ **Corrected the same night (spec §6.6bc, "SLICE ORDER CORRECTED"):** the byte
      path cannot move before the per-channel state does, and `disk.rom`'s BDOS
      layer is single-file by design. ~~Next is **S10.A**: an FCB-stateful,
      multi-FCB BDOS engine~~ 🔴 HALF WRONG: only the BLOAD mini layer is
      single-file. The kernel's canonical WRBLK/RDRND/WRRND re-locate the file
      from the FCB every call, so they are multi-file already. S10.A is now a
      PROOF: a BDOSX case alternating two FCBs, byte-exact against stock, plus a
      check of which create/close/RDBLK entries exist at canonical depth. Then
      the OPEN/PRINT#/CLOSE vertical slice (S10.B).
      🔬 **STEP 10's INTERFACE MEASURED 2026-10-01 (D-CHANHOOK, spec §6.6bb):**
      - The CF-3300's channel verbs cross at EIGHT claimed cells: OPEN/CLOSE,
        each statement (`$FE4E`), each BYTE out (`$FE85`) and in (`$FE8A`), and
        EOF/LOF.
      - The sector loop stays on the disk side.
      - zerobas claims one of the eight (`$FE5D`).
      - So step 10 is the byte I/O behind `$FE85`/`$FE8A`, with the channel's
        sector state on the disk side, not only the OPEN arm.
      ([`chanhook_run.out`](scratchpad/chanhook_run.out),
      [`hookclaim_run.out`](scratchpad/hookclaim_run.out))
      ✅ **S10.B INCREMENT 1 SHIPPED (2026-10-06): A DISK FILE OPEN FOR OUTPUT IS
      DISK.ROM'S.** OUTPUT is mode 3 (`DOUT_MODE`; APPEND stays 2 on main's
      engine), its channel an MSX-DOS FCB in the channel's engine row: OPEN
      through `FOPEN_SEL_MAKE` (hk_fmake), PRINT# through `$FE85` a byte
      (hk_chout: the record = the block's +9, the position its +6), CLOSE
      through `$FE62` (hk_chclose: Ctrl-Z, the last record, the directory once).
      A full 256 B record is written AT ONCE by main's own engine as disk.rom
      assembles it (`fat_flush_data_sector`), with the write cursor -- first
      cluster, cluster, sector, directory position -- kept in the row's spare
      bytes. The sub-ROM's t_fch_save/t_fch_load leave a mode-3 row alone and
      re-cache its block address; LOF reads the FCB's size;
      hkk_open_check matches a mode-3 channel by its FCB name. D-CLEARCLOSE
      (9b8c0291) settled the one design risk first: no channel survives the
      `CLEAR` that would move its block.
      📏 ([`s10b_ship_measure.out`](scratchpad/s10b_ship_measure.out)) LOF/LOC
      read `0 0 0 0 256 256 512 512 601`, the CF-3300's (was 0 throughout); a
      full disk fails PRINT# at **I = 12**, the CF-3300's (diskfull's pin, 24,
      moved as it was written to); gate **`dout-acceptance`**
      ([`probes/disk/disk_probe_dout.py`](probes/disk/disk_probe_dout.py)) 8/8
      against the CF-3300 -- two OUTPUT channels alternating, OUTPUT beside
      APPEND and INPUT, OPEN/KILL/NAME of an open file (54/64/64), empty, exactly
      256 B, truncation. Knives ([`dout_knives.py`](scratchpad/dout_knives.py)):
      K-DO1 (no step-back after a first half) moves exactly twochan/append/input,
      K-DO2 (no directory stamp) all eight.
      ⏱ 4200 B of PRINT# + CLOSE: **14.2 emulated s against the CF-3300's 11.8
      (1.2×)**; main's engine took 7.9 (0.67×) -- a CALLF a byte, and a record
      in a sector's second half re-reads the first. T2 met; T5 tracks it.
      🔴 **THE FIRST BUILD WROTE RECORDS WITH `wrblk_body` AND WAS PARKED**
      ([`s10b_wip_measure.out`](scratchpad/s10b_wip_measure.out)): the canonical
      BDOS block write re-mounts, re-finds and rewrites the directory on EVERY
      record -- 17 DSKIO calls for a one-record OPEN/PRINT#/CLOSE against the
      old engine's 7 (the record writer: 12) -- and with the driver holding DI
      through each sector op, keys typed during that longer CLOSE were LOST
      (diskbasic-acceptance's PRINT# round-trip read `txt" for input…`). Two
      `ei` fixes (after each hook return -- C-BIOS's CALSLT returns DI, cbios
      `src/slot.asm` `calslt_restore` -- and at the handlers' entry) were
      MEASURED not to help; the record writer cured it. 🔴 **CORRECTED the same
      day: both `ei`s DID ship** (c6d03ec8's message and this line said they
      did not -- the squash carried them). They are kept, as interrupt hygiene
      and nothing more: a CALLF's return leaves interrupts off where every older
      path ran on through subrom_call's `ei`, and a long handler should not
      starve the keyboard between sector ops. No row witnesses either.
      🔴 **AND A STOPWATCH WAS WRONG TWICE ON THE WAY:** keyed on the cursor ROW
      settling, it read the parked build at "27.1 s vs 13.4" -- a silent loop
      never moves the row, and JIFFY/TIME stop while a sector op holds DI, so
      neither is a clock here. Re-timed marker to marker
      ([`s10b_stopwatch.py`](scratchpad/s10b_stopwatch.py)).
      🎯 Predictions: loflive parity -- hit; diskfull's pin to 12 -- hit; the
      two `ei` fixes -- MISSED twice; the record writer at ~10 DSKIO calls --
      12, near; it beating the CF-3300's time -- **MISSED** (1.2×); dout 7-8/8 --
      8/8 once its own three apparatus faults were fixed (a number wrapping at
      the row edge -- which was D-PRNUMWRAP, a real divergence -- an integer
      `MOD` overflow, and a trap MAXFILES had cleared).
      ✅ **INCREMENT 2 SHIPPED (2026-10-06): APPEND IS DISK.ROM'S TOO; mode 2 is no
      longer stored.** `FOPEN_SEL_APND` → `hk_fapp`: a missing file is refused
      (53, `File not found`, as before -- disk.rom now leaves the code itself);
      the FCB resumes at the last WHOLE record -- its random record (+33) the
      size rounded down, that record's bytes re-loaded into the block (a size
      that is a whole number of records re-loads the last record entire,
      DOUT_RFULL) -- and a trailing Ctrl-Z is stepped back onto. Records go to
      the random record now, not the size: LOF is the FCB's size and LOC its
      random record, and **they DIFFER on APPEND**
      ([`applof_run.out`](scratchpad/applof_run.out), the CF-3300): a 6 B file
      reads 6/0 after the OPEN, 6/0 after 10 B, 256/256 after 300; a 256 B one
      256/0, then 256/256 (the first byte overwrote its Ctrl-Z and completed
      the record), 512/512. Ours read LOF = LOC = the open size throughout --
      fixed with it: LOC on a mode-3 channel reads `FWR_BYTES`, which disk.rom
      keeps at the random record (`dout_mirror`; t_fch_load re-reads it).
      Main's `fat_io_append` is gone (page 1 113 → 202 B; its fatprim row 18
      keeps its numbered slot). dout-acceptance gains `app6`/`app256`, 10/10;
      knives ([`dout_knives2.py`](scratchpad/dout_knives2.py)) K-AP1 (no
      Ctrl-Z step-back) moves exactly app6/app256/append, K-AP2 (LOC = LOF) app6/app256.
      🔴 **A CALL-BACK RETURNS DI, AND IT MASKED THE WHOLE OPEN.** Increment 2's
      shared `dout_open` calls `fch_ctx_addr` back in main BEFORE the mount;
      C-BIOS's CALSLT returns DI, the driver keeps the CALLER's interrupt state
      (`fdc_di_save`), so every sector op of the OPEN ran masked and
      diskbasic-acceptance's PRINT# round-trip lost keys again (`opent.txt"…`).
      One `ei` after the call-back fixed it (2/2, 4200 B still 14.2 s).
      ⚠️ My first scoring of that `ei` was a MISS -- but the run carried a
      driver experiment too (D-FDCDI below) that made it worse; with the
      experiment out, the `ei` alone passes. Confounded, not refuted.
      ⏱ **THE BATTERY'S TWO TIMING CASUALTIES:** namspc's `f.appvarx` (OPEN..AS,
      CLOSE, OPEN..FOR APPEND, CLOSE) read UNREADABLE -- ours runs it in 2.28 s
      and the CF-3300 in 3.40 (marker to marker), but the probe gave ours a
      2.5 s window and the CF-3300 4.5; a disk row now gets at least the
      CF-3300's window on every side. And `badfnum-acceptance` went red ONCE in
      the parallel FULL battery and green on the serial retry (the runner calls
      it a flake). Then `kwsweep` did the same in the next FULL battery.
      🔴 **CORRECTED the same evening: BOTH LOGS WERE KEPT** -- under
      `/tmp/zerobas/gate_flakes/` (D-FLAKEKEEP, the sanctioned temp root), not
      `scratchpad/gate_flakes/`, where I looked and wrongly wrote "not kept".
      Read, neither is S10.B's: `kwsweep`'s first attempt died of
      `FileNotFoundError: /dev/cu.usbmodem101` -- the USB rig dropping off, the
      known intermittent; `badfnum`'s read ONE row, `fld_c16` (`FIELD #16,10 AS
      A$` -> 52), as no reading on ours -- a capture miss on a row with no disk
      write in it (3/3 green alone the same evening).
      ➡️ **Left for later increments:** ~~main's own write engine's deletion
      (SAVE ,A still uses it)~~ (✅ increment 3, D-ASAVEDOUT, 2026-10-08 --
      below), the input side through `$FE8A` (S10.C), the speed
      (keep a sector's first half instead of re-reading it), and ~~the `cp 2`
      mode tests main still carries for a mode nothing stores~~ (✅ D-MODE2DEAD,
      2026-10-07 -- below).
      ✅ **INCREMENT 3 SHIPPED (2026-10-08, D-ASAVEDOUT): `SAVE"name",A` TO DISK
      IS DISK.ROM'S, AND MAIN'S RESIDENT WRITE ENGINE IS GONE -- 113 B OF MAIN
      PAGE 1 (15 -> 128).** The create is OPEN FOR OUTPUT's own selector
      (`FOPEN_SEL_MAKE`) arriving with NO channel live -- the save parks the
      live one first (`fch_park`), and OPEN always claims its channel, so
      `FCH_ACTIVE` = 0 at `hk_fmake` means SAVE ,A and nothing else. Each byte
      is `H_CHOUT`, the end `H_CHCLOSE`, both again with no channel live, and
      disk.rom sends those to the sequential writer `hk_dpsave` already
      includes (`fat_io_create` / `fat_io_putbyte` / `fat_io_close`, buffering
      in the shared sector buffer exactly as main's copy did) -- NOT to
      `dout_open`'s 256 B record writer, which needs a channel row and a 265 B
      block: the reference's `#0` buffer would cost 267 B of `FRE(0)` here.
      Deleted from main: `fat_io_putbyte`, `fwr_bytes_inc`, pchar's
      `pch_main` arm and its mode tests (every disk byte is `H_CHOUT` now),
      the `sv-diskwr.inc` copy, and the `fat_flush_data_sector` /
      `fat_io_create` / `fat_io_close` stubs; the fatprim rows 11/23/24 they
      sent to answer `fp_stash_ok` (sub page 1 +27 B). disk.rom 4558 -> 4509 B.
      📏 ([`disk_probe_asavedev.py`](probes/disk/disk_probe_asavedev.py), gate
      `asavedev-acceptance`, the image read back against the CF-3300): a
      one-line program 15 B, ~2 KB over two clusters 2064 B, both byte for
      byte before AND after the move.
      🔴 **D-ASAVEDEV, FOUND BY ITS SEPARATING ROW AND FIXED WITH IT:** after
      `OPEN"CRT:"FOR OUTPUT AS#1 : PRINT#1,"X" : CLOSE#1`, `SAVE"Q.BAS",A`
      listed to the SCREEN and left Q.BAS **0 B** -- the CF-3300 writes its
      15 B ([`asavedev_before.out`](scratchpad/asavedev_before.out)). `PRDEV`
      is the PRINT# device selector and the save never set it; now one
      `ld (PRDEST),hl` sets both (`PRDEV` is the next byte, asserted at
      build time). `LLIST` and `LPRINT` set `PRDEV` = 1 and nothing resets
      it, so either one then `SAVE ,A` sent the listing to the PRINTER -- read
      from the code, NOT measured (the reference rig has no printer); the
      same store fixes it. 🔮 Predicted the divergence: HIT; predicted
      1 B (the Ctrl-Z): MISSED, the Ctrl-Z went to the screen too.
      🔴 **AND D-ASAVEFULLSTAMP'S RULE HAD TO MOVE WITH IT.** The first build
      turned diskfull-acceptance's `astamp` red: the CF-3300 stamps SA.BAS
      with the 1024 B that fit on a full disk, ours left 0/0. The rule was
      `ffds_full`, in the SUB-ROM's flush, which main's old path reached
      through its stub; disk.rom's flush does not carry it (it serves the
      BDOS too). It is in `hco_asav` now, for 66 only.
      📍 **NO SELECTOR OF ITS OWN BECAUSE THERE WAS NO BYTE FOR ONE:** a first
      cut added `FOPEN_SEL_ASAV` to `hk_dpload`'s chain and disk.rom assembled
      EMPTY -- that region (`$607B..$75A5`) had **0 B** free, the fill beside
      `hk_fmake` 752. The hook table enters through `hk_chout_e` /
      `hk_chclose_e` for the same reason.
      ⚠️ **AN APPARATUS MISS, MINE, ON THE WAY:** the `big` row read the
      CF-3300 at **0 B** twice. I blamed the typed line length and reshaped
      the row; it was the session ending before the reference's 2 KB write
      had committed -- two trailing lines and it reads 2064, ours' size.
      🔪 Knives ([`asavedout_knives.py`](scratchpad/asavedout_knives.py),
      [`asavedout_knives.out`](scratchpad/asavedout_knives.out)): K-AD1 (no
      `PRDEV` store) -> crt, K-AD2 (no partial stamp) -> astamp, K-AD3 (no
      `fat_io_close` at the end) -> plain/big/crt -- each moved EXACTLY those rows (3/3 predicted).
      ➡️ **Still left:** BSAVE to disk runs the SUB-ROM tenant's copy of the
      engine (no hook -- a foreign disk ROM would still get ours, the reason
      D-SAVEPORT moved tokenised SAVE), the input side (S10.C), the speed.
