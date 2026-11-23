- [ ] 💽 **D-DISKRUN — THE DISK COLLECTION ON BOTH MACHINES: 18 SYSTEM DISKS REACH
      MSX-DOS ON THE CF-3300 AND BASIC ON zerobas (run 2026-10-21, Joost: "Disk test run")**
      🎚️ TIER 1 — happy path: booting a disk is the first thing a disk machine does.
      🤖 **AUTONOMOUS** — the CF-3300 settles every row; triage is black box (screens,
      CURLIN, PC, our own ROM's breakpoints), the software is RUN, never decoded.
      📏 [`diskcorpus_run.py`](../../scratchpad/diskcorpus_run.py) boots every image of the `disks`
      collection (Joost 2026-10-20: never `my_disks`, which is private; the tool refuses
      it; the collection's location is passed in, never written here) on the National
      CF-3300 and on zerobas's disk machine from a /tmp copy, 45 s throttle-off, then types
      FILES. 143 images (130 .dsk, 10 .di1/.di2, 3 .xsa; one "*.dsk" entry is a directory):
      | class | n | meaning |
      |---|---|---|
      | BOTH-RUN | 92 | both machines run the disk's program (NOT compared further: a Japanese and a European machine draw different screens) |
      | ZB-NOBOOT | 27 | the CF-3300 runs something, zerobas sits at its prompt |
      | FILES-SAME | 8 | both at the prompt, the same FILES listing |
      | FILES-DIFF | 9 | mostly NOISE (the banners' version numbers, 32- vs 40-column wrapping); real candidates: no-waste.dsk (zerobas lists none), facdemo3.di2 (1 against 41), kq.dsk (two missing at the end) |
      | ZB-ONLY | 6 | zerobas runs a program where the CF-3300 sits in direct mode (BREAKER: zerobas at line 10) -- read each |
      | FILES-EMPTY | 1 | |
      📏 **RE-RUN 2026-11-04, CACHED** ([`diskcorpus_20261104.out`](../../scratchpad/diskcorpus_20261104.out); Joost: *"Cache
      it, then re-run"*): diskcorpus_run.py's launches now go through the reference store
      (`cached_run`, the disk keyed by its bytes) and its JSON lives in ~/.cache/zerobas, not /tmp
      (the 10-21 one was lost there). 143 images in 123 s: **BOTH-RUN 118 (was 92), ZB-NOBOOT 1
      (was 27)**, FILES-SAME 11, FILES-DIFF 8, ZB-ONLY 4, FILES-EMPTY 1. Every non-match is a filed
      one: ZB-NOBOOT is GAUNT (closed 10-27, written for RAM in slot 3-2); ZB-ONLY are BREAKER
      (MSX2), TestameB and calculus (the CF-3300 crashes, 10-23) and ss-final (flips run to run);
      FILES-DIFF are mostly one listing line apart. 🔮 "close to 10-21 minus the 18 D-BOOTDATE
      disks" -- MISSED: 26 of the 27 ZB-NOBOOT now boot.
      🔴 **CLASS A (18 of the 27 ZB-NOBOOT): the CF-3300 reaches MSX-DOS's `Enter date` and
      zerobas BASIC** -- including disks whose root directory holds NO system file at all
      (empty.dsk has no entries; almost_real.dsk's "directory" is art text). zerobas reads
      those directories CORRECTLY (FILES lists exactly what is there), and the BPBs are the
      test disk's (720 KB, F9) -- so it is not the FAT layer. Both machines enter the disk's
      boot code twice at $C01E (CF=0, then CF=1) identically (a breakpoint on our own call).
      ⚖️ The differential that places it: empty.dsk on the CF-3300 HARDWARE with zerobas's
      disk ROM fitted (`National_CF-3300_ZEROBASDISK`) ends in BASIC with `Type mismatch in
      0`; with the stock disk ROM, `Enter date`. So the divergence is in disk.rom's BOOT path
      (what the boot code is given, or calls, after step 7), not in C-BIOS or BASIC.
      📏 **PLACED (2026-10-21, black box, same CF-3300 hardware, stock disk ROM vs ours):**
      the boot code's BDOS $0F (open, FCB at $C0AB) fails identically (A=$FF; only HL
      differs, 00FF vs E46A -- and forcing HL=00FF on ours changes NOTHING, so not HL); no
      DSKIO beyond sector 0, no BDOS through $0005, nothing executed at $0100. Then the
      boot code jumps to **$4022** on both (page 0 already RAM) -- the published entry
      zerobas implements as BASENT ("start BASIC", D-DOSBASIC). 🔭 **A SECOND REFERENCE
      AGREES WITH THE FIRST** (Joost 2026-10-21: "Check another reference"): the VG-8020
      with a Philips NMS 1200 disk interface prints `Enter date (M-D-Y):` from empty.dsk
      too (🔮 "a CF-3300 quirk" MISSED). CHPUT is called, through an inter-slot call, with
      page 0 = the BIOS and page 1 = the disk interface (slots $F4): the DISK ROM prints
      it, in the BASIC environment. Answered with `1-1-90`, the NMS 1200 then starts Disk
      BASIC normally (banner, `Ok`, `PRINT 7*6` -> 42). **So: a stock disk ROM's $4022,
      entered by a boot loader that could not open MSXDOS.SYS, ASKS THE DATE (no clock on
      an MSX1) and then starts BASIC; zerobas's starts BASIC without asking.** The CF-3300
      prints the same prompt with Japanese text in the brackets.
      ➡️ D-BOOTDATE (filed above, measured) is the fix. After that: the other ZB-NOBOOT rows (DiscStation #32 A-D's own "Loading DS"
      loader, ROBOCOP, SirDan, xak2eng2, senigma), the FILES-DIFF candidates (facdemo3
      DONE: D-MEDIAID; facdemo1 DONE: D-COLOREQ; kq.dsk is the APPARATUS -- the CF-3300's
      FILES is slower and the T+6 capture caught it half done; given time it lists the same
      ([`kq_files_slow.out`](../../scratchpad/kq_files_slow.out))), and the six ZB-ONLY.
      📏 **RE-RUN 2026-10-21 after D-BOOTDATE / D-MEDIAID / D-COLOREQ / D-RAMAD / D-SIDES** (zerobas
      only, against the first run's reference rows: `diskcorpus_run.py --reuse-ref`;
      [`diskcorpus_rerun.out`](../../scratchpad/diskcorpus_rerun.out), the 43 non-BOTH-RUN rows): BOTH-RUN
      19 (the 18 date-question disks, now asking on both), ZB-NOBOOT 8, ZB-ONLY 7, FILES-DIFF 7,
      FILES-SAME 1 (facdemo3), FILES-EMPTY 1. 🔮 "class A -> BOTH-RUN" HIT. ⚠️ Two of the BOTH-RUN
      are the HEURISTIC, not agreement: ROBOCOP (zerobas at the date question, the CF-3300 in the
      game -> D-BDOSBASIC) and xak2eng2 (zerobas CURLIN $4003, junk). And most FILES-DIFF rows are
      the CLASSIFIER: files_listed() reads the banners' version numbers (`1.0`, `0.1`) as file
      names. BREAKER is an MSX2 game (`SET PAGE`, SCREEN 8 pictures): both fail, not ours.
      📏 **ROBOCOP after D-BDOSBASIC slice 1 (2026-10-21):** the loader now matches the CF-3300
      call for call; the game it loads resets ~4 s later on zerobas (the boot code runs again),
      where the CF-3300 shows `TECLE [CONTROL] !` first and resets ~15 s on. ➡️ What the loaded
      game calls (published BIOS entries, the slot state) on both, registers only.
      📏 **THE MEMMAN CLASS (no-waste, megadoom, modedit; 2026-10-21):** the references stop
      in MemMan's installer (`No free segment for MemMan`; megadoom `Illegal function call
      in 8`). D-RAMAD fixed two documented cells it found unset, and the three STILL part
      ways ([`ramad_zb_after.out`](../../scratchpad/ramad_zb_after.out)). ➡️ NEXT for this class:
      what memman.bin's BLOAD ,R reaches -- a breakpoint on the published BIOS / disk-ROM
      entries it calls (CALSLT, RDSLT, WRSLT, ENASLT, EXTBIO) on both machines, registers
      in and out; the software is never decoded.
      📏 **DONE (2026-10-22) -> D-MASTERS + D-BASENTRUN (fixed), D-HSTKE (filed).**
      [`slotcalls_probe.py`](../../scratchpad/slotcalls_probe.py)
      ([`slotcalls_nowaste.out`](../../scratchpad/slotcalls_nowaste.out)): no-waste's installer makes
      the SAME EXTBIO / ENASLT slot scan on both machines, then CALSLTs $4022 (BASENT) in the
      slot it reads from $F348 -- $87 on the CF-3300, C-BIOS's $C9 fill here (🔮 "the first
      difference is slot 3's expansion" MISSED: the scan agreed; the BC=$0300 / $0000 on the
      first EXTBIO did not matter). Filled ($F348 = this ROM's slot on every host), the call
      reached zerobas's BASENT, which re-ran disk INIT and AUTOEXEC.BAS: the same loop. Own
      disk ([`basent_autoexec.out`](../../scratchpad/basent_autoexec.out), an AUTOEXEC.BAS that
      counts its runs in RAM and calls $4022): CF-3300 1, zerobas 4. Planted hooks
      ([`basent_hooks.out`](../../scratchpad/basent_hooks.out)): the CF-3300 keeps all four across
      $4022, zerobas wiped them. Text at HL ([`basent_ref1.out`](../../scratchpad/basent_ref1.out),
      [`basent_ref2.out`](../../scratchpad/basent_ref2.out), four forms): never run -- 🔮 MISSED
      twice. 🔧 basent_body: a third mark, 'B','B' (neither DOS_SIG nor DOS_TRY = a running
      program): no date question, hooks kept (the trampoline's second entry), and hk_auto
      skips AUTOEXEC.BAS once and clears it. Hosts: tests/test_bootdate.py (5 rows; knives
      K1-K3 cut 2 / 2 / 3), tests/test_ramad.py ($F348 row; knife cuts 4 of 5 -- the $FF host
      builds the table anyway). no-waste on zerobas now lands at a prompt once
      ([`basentrun_nowaste.out`](../../scratchpad/basentrun_nowaste.out)); the CF-3300 also prints
      `No free segment for MemMan` -- through H.STKE ([`stke_memman.out`](../../scratchpad/stke_memman.out):
      memman points $FEDA at its own code just before the call), a hook zerobas never calls
      -> D-HSTKE.
      📏 **AFTER D-HSTKE (2026-10-22)**, the three disks
      ([`memman_class_after.out`](../../scratchpad/memman_class_after.out),
      [`stke_when_zb.out`](../../scratchpad/stke_when_zb.out)): no-waste and modedit print `No free
      segment for MemMan` and stop at the prompt, as on the CF-3300. megadoom still parts:
      the CF-3300 `Illegal function call in 8`, zerobas still RUNNING in line 7 at T45.
      ➡️ NEXT for megadoom: what its line 7 waits on (CURLIN stays 7) -- list lines 1-10 on
      zerobas (the screen only, never into the repo) and the slot calls it makes
      (slotcalls_probe.py), both machines.
      📏 **megadoom TRIAGED (2026-10-22) -> D-TXTTAB.** Listed on the CF-3300 (screen only):
      line 7 is the classic loader trick -- if PEEK(&HF677) is not &HD0, POKE it (and &HD000)
      and RUN its own loader file, so the program text moves to $D001. zerobas resets TXTTAB
      to $8001 at every NEW / LOAD, so the test never comes true and line 7 RUNs the loader
      for ever (CTRL+STOP cannot land; PC in READ / RESUME). The game itself is MSX2 (line 8
      `SCREEN7`): the CF-3300's `Illegal function call in 8` is the right end.
      📏 **UR-1 TRIAGED (2026-10-21): an MSX2 demo; both machines fail it, differently.**
      Its AUTOEXEC.BAS RUNs UR.BAS, whose line 30 is `BLOAD "...",R` of a machine-code
      loader; on the CF-3300 the machine then RESETS and boots again, round and round
      (the boot logo at T25, line 30 again at T40); on zerobas the loader comes back
      with `Missing operand in 30` and the program area is damaged (LIST hangs). The
      disk's files are MSX2-era (VDP / NPC / FM-PAC); not a BASIC divergence. 🎚️ TIER 6
      at most -- not pursued. (It did find the AUTOEXEC.BAS rule, D-BOOTDATE's addendum.)
      📏 **FULL RE-RUN 2026-10-22 after the day's disk fixes** (zerobas only, against 10-21's
      reference rows; [`diskcorpus_rerun2.out`](../../scratchpad/diskcorpus_rerun2.out)): BOTH-RUN 92 ->
      108, ZB-NOBOOT 27 -> 11, FILES-SAME 8 -> 10, ZB-ONLY 6 -> 5. Up: SirDan, megadoom, modedit.
      🔮 "nothing regresses" MISSED -- four rows BOTH-RUN -> ZB-NOBOOT, each read:
      **facdemo5** a REAL regression of D-BASENTRUN -- its boot code falls back to $4022 from the
      FIRST (Cy = 0) call, outside dos_handoff's DOS_TRY window, so $4022 took it for a running
      program and asked no date. Fixed: boot_call0 (disk/driver.asm) runs that call under DOS_TRY
      too; the date question is back. **f1sp3d-1** -> D-BDOSABS: its loader SETDTAs, then BDOS
      $2F RDABS 8 sectors; the CF-3300 reads them, the BASIC-side door answered $FF
      ([`f1sp3d_slotcalls.out`](../../scratchpad/f1sp3d_slotcalls.out)). Fixed: $2F / $30 in
      bdos_more2's table (rdabs_body / wrabs_body). It now HANGS inside that call instead ->
      D-F37DSLOT. 10-21's "BOTH-RUN" for it was a hang the classifier read as running.
      **elite** gets FURTHER than on 10-21 (then: stuck at the DOS banner at T45; now: the game
      starts, then jumps to $0000 at T17.4 with RAM in page 0 -- MSX-DOS's warm boot -- and
      zerobas has none there, so it slides into $4022 and BASIC); **starsh2** unchanged at the
      prompt. ➡️ elite's warm boot and starsh2 after D-F37DSLOT.
      Hosts: tests/test_bdosbasic.py ($2F / $30 dispatch rows; the "not answered" row now uses
      $31), tests/test_bootdate.py (boot_call0's mark); knives cut both
      ([`bdosabs_knife.out`](../../scratchpad/bdosabs_knife.out)).
      📊 **RE-SCORED 2026-10-23 after D-TPAP1 / D-TPAPTAIL / D-BOOTREGS** ([`diskcorpus_rerun4.out`](../../scratchpad/diskcorpus_rerun4.out)):
      BOTH-RUN **118**, ZB-NOBOOT **1**, ZB-ONLY 4, FILES-DIFF 8, FILES-SAME 10, FILES-EMPTY 2.
      elite, starsh2, f1sp3d-1, UR-1, senigma, facdemo5 and DiscStation #32 A-D now run (details
      in D-BOOTREGS). The one ZB-NOBOOT left is mania111_starquake.dsk, and the image is ALL
      ZEROS (no boot sector, FAT or directory -- the only image without $EB / $E9 at byte 0).
      The CF-3300 asks `Enter date ( - - ):` for it; zerobas starts BASIC. Not a program: filed
      here, not chased. ➡️ If it is ever taken up: does the VG-8020 + NMS 1200 ask too (the
      style split's authority), and what does the CF-3300 do with a blank but FORMATTED disk?
      📊 **RE-SCORED 2026-11-01, FULL (both machines; [`diskcorpus_full_1101.out`](../../scratchpad/diskcorpus_full_1101.out))**:
      BOTH-RUN 118, ZB-NOBOOT 1, ZB-ONLY 4, FILES-DIFF 8, FILES-SAME 11, FILES-EMPTY 1 -- every one of
      the 143 images in the class it had on 10-28 (🔮 HIT), across D-REREAD batches 7-11, D-G8OPCLOB,
      D-LPRTAB, D-BRKFRESH and D-USRSTRRES. 🔧 Apparatus: a `--reuse-ref` run wrote rows WITHOUT the
      reference fields, so every re-run leaned on the first full run's /tmp file; it was cleaned and
      the chain broke (`KeyError: 'ref_curlin'`). Re-run rows now carry ref_curlin / ref_pc /
      ref_mode / ref_files forward (scratchpad/diskcorpus_run.py), and this full run is the new base.
      📏 2026-10-23 (D-STEP7DATE's re-run, [`diskcorpus_rerun5.out`](../../scratchpad/diskcorpus_rerun5.out)):
      ss-final.dsk went FILES-EMPTY -> ZB-ONLY between re-run 4 and HEAD, independent of the ROM
      half (today's ROM does the same). The CF-3300 and re-run 4's zerobas stop at its own
      `FATAL ERROR  Not enough free memory found (at least 32kB)` under MSX-DOS; HEAD's zerobas
      passes that check and loads on. 📏 **BISECTED (2026-10-23, [`ssfinal_bisect.out`](../../scratchpad/ssfinal_bisect.out)):**
      0b417fb3 stops at the error, 1c884267 -- D-TPAPTAIL (b), P1_BLIT made atomic -- runs on.
      Both return from the copy with the caller's interrupt state; the only change is that no
      interrupt lands INSIDE the page-1 copy now. So the program's outcome hangs on interrupt
      timing inside a BDOS transfer. [`ssfinal_probe.py`](../../scratchpad/ssfinal_probe.py)
      ([`ssfinal_run.out`](../../scratchpad/ssfinal_run.out); RAM and work area only, page 0 read only
      while it is the RAM slot RAMAD0 names): under the program, the CF-3300's page-0 RAM holds
      `00 00 00` at $0005, zerobas's still `JP $DEB2` -- different code paths from 10 s on.
      The program misdetects the CF-3300 itself ("Turbo-R", "V9958"). 🎚️ TIER 6 latent, not
      chased: what it measures is inside third-party code, and the black-box route is a
      reference measurement of interrupts DURING a BDOS disk transfer into page 1 (our own
      test program on a DOS disk: count JIFFY across a long random-block read with EI).
      📏 **calculus and TestameB (2026-10-23): THE CF-3300 CRASHES ON BOTH -- not ours.**
      [`screen_timeline.py`](../../scratchpad/screen_timeline.py) ([`calculus_timeline.out`](../../scratchpad/calculus_timeline.out),
      [`testameb_timeline.out`](../../scratchpad/testameb_timeline.out)) and register samples
      ([`calculus_regs.out`](../../scratchpad/calculus_regs.out), [`testameb_cf_regs.out`](../../scratchpad/testameb_cf_regs.out)):
      ~1-2 s after its program starts, the CF-3300's SP runs down through all of RAM, JIFFY and
      SCRMOD read $FF (the work area wiped), interrupts off, PC sweeping -- its "picture" was
      the name table read during the wipe. zerobas fails differently (calculus: the program's
      own loop at $0D73 with interrupts on, JIFFY moving, hooks untouched; TestameB: a loop at
      $06BE), so there is no reference behaviour to match. Noted on the way: calculus loads
      MSX-DOS + the program by ~11 s on the CF-3300 and by ~20 s on zerobas -- disk read speed,
      TIER 5 (the LOAD speed item).
      Next by class: ZB-ONLY BREAKER (MSX2, both fail) / mb (🙋), FILES-DIFF (mostly noise, see
      the first table).
      📏 **mb.dsk is not ZB-ONLY, it is a BOOT LOOP** (read 2026-10-23, already so on 10-22 --
      diskcorpus_rerun2.out has the same row): zerobas sits on C-BIOS's start-up screen ("Init
      ROM in slot: 0") and our INIT runs again every 208 ms -- the boot code is entered at
      $C01E with Cy = 0 each time with the same SP / AF, the floppy controller polled in
      between, no step 7, no $4022, no RAM clear (so not a reset). Not D-BOOTREGS: a build of
      9f818938 loops too, and so does HEAD without the step-5 DE / HL. The disk holds a
      standard-looking boot sector, AUTOEXEC.BAS and MOONBLAS.* (no MSXDOS.SYS); the CF-3300
      ends at its prompt.
      📏 **READ FURTHER (2026-10-23, [`mb_stack.out`](../../scratchpad/mb_stack.out)):** the step-5 call
      NEVER comes back -- not to boot_call0, not to dos_handoff, not to C-BIOS's return
      address $F392 -- yet C-BIOS's ROM scan calls our INIT again for slot $87 page 1 (DE =
      $8704) with the SAME stack (SP $F2DC: $F392 / $F043 / $2467 / $8704 ...), every 208 ms.
      The boot code's only RAM write is one push (the instruction at $C04E). The stacks
      differ: the CF-3300 runs the boot code on SP = $C1FC with two returns into its ROM
      ($59FE, $5B35) and nothing above $C200; ours SP = $F2D6 with [boot_call0][the saved
      BASENT mark][boot_disk][C-BIOS's $F392]. 🔮 A build with the CF-3300's stack shape
      (SP := $C200, two returns into boot_call0, the mark in RAM) STILL LOOPED -- MISSED,
      reverted, not shipped. ➡️ Next: where the call at $C04E goes. A write-watch-armed
      `set_condition` fired 7 ms late, so log the PC at the call's own return address
      instead, or watch which of OUR entries (or C-BIOS's) runs between the push and the
      INIT re-entry.
      📏 **NARROWED (2026-10-23, [`mb_a8.out`](../../scratchpad/mb_a8.out)):** 230 µs after the boot
      code's entry, code at **$E47E** (RAM, inside our SECTOR_BUF) writes $A8 := $F0 (pages 0 /
      1 = slot 0) on a stack unwound to C-BIOS's scan frame (SP $F2EC, return $F392); then our
      main ROM's cold start (init, $4010) runs and C-BIOS re-scans every slot. None of our
      disk-ROM labels and no page-0 BIOS entry runs in between. REFUTED, one run each, all by
      overriding at the $C01E entry: DE / HL, the CF-3300's stack shape, DRVINF ($FB21 / $FB22
      := 02 / $87) and a reference-shaped $F349..$F356 (its words are BUFFER POINTERS on the
      CF-3300 -- $DF93, 0, $EF95, $ED95, $EB95, 0, $F195 -- not the trampolines our gated
      build_drvtbl writes; that reading is worth a note on build_drvtbl either way).
      ➡️ Next: who CALLS $E47E -- a write watch on page 1 / page 2 RAM for a fake "AB" header
      (a boot loader that lets the BIOS's own ROM scan start it), and what the CF-3300's scan
      does after this boot code's step 5.
      ✅ **ANSWERED (2026-10-23, [`mb_5e10.out`](../../scratchpad/mb_5e10.out), [`mb_nms1200.out`](../../scratchpad/mb_nms1200.out)):
      the boot code CALLs a FIXED DISK-ROM ADDRESS, $5E10** (breakpoints on every address
      $5DF8..$5E14, its return $C051 on the stack; DE = $7368, HL = $E646 on both machines). In
      our ROM $5E10 is the middle of basent_body, so it reaches bb_mark with L = 'F' (HL =
      $4246, not a mark), copies the restart trampoline to $E470 -- the "$E47E" above -- and
      restarts; INIT does not recognise the mark and boots again, for ever. And the REFERENCES
      DISAGREE about $5E10: on the CF-3300 it never returns either and the screen stays blank
      (SCREEN 1, a BIOS wait loop); on the VG-8020 + NMS 1200 BASIC starts and AUTOEXEC.BAS
      runs, ending `Illegal function call in 20`. The disk's boot sector is written for one
      disk ROM's internals; neither reference runs its program.
      🙋 **FOR JOOST:** zerobas's reboot loop is the worst of the three. Options: (a) pin a
      $5E10 entry that starts BASIC as the NMS 1200 does (AUTOEXEC.BAS runs), (b) as the
      CF-3300 does (a blank hang -- faithful to the disk reference, useless), (c) leave it and
      make only bb_mark robust (any entry there restarts BASIC once instead of looping). Not a
      style split, so not covered by the VG-8020 ruling.
      🏗️ **RULED BY JOOST 2026-10-27: (a), *"Start BASIC (NMS 1200)"*** -- pin a $5E10 entry
      in disk.rom that starts BASIC as the NMS 1200 does (AUTOEXEC.BAS runs). ➡️ Next:
      measure the NMS 1200's state at BASIC's start after that call (registers, the work
      area, which disk is current) black-box, then the pin -- price the $5E10 neighbourhood
      against check_disk_walls first.
      ✅ **SHIPPED 2026-10-27.** 📏 [`mbtime_probe.py`](../../scratchpad/mbtime_probe.py) -> [`mbtime_run.out`](../../scratchpad/mbtime_run.out): the NMS 1200 shows
      its banner at T6 and AUTOEXEC.BAS's `Illegal function call in 20` by T9 -- NO date
      question; the CF-3300 a blank screen; zerobas C-BIOS's start-up screen, looping. 🔮 HIT
      on all three. Nothing new was needed: under boot_call0's DOS_TRY mark basent_body is
      the boot-loader restart ('B','D'), which asks the date only with no AUTOEXEC.BAS. So
      $5E10 is pinned (disk/kernel.asm, `ds $5E10 - $` + `mb_5e10: jp basent_body`, 22 B
      of the free run before $5FE5; disk free 799 -> 796 B). After: zerobas ends where the
      NMS 1200 does ([`mbtime_after.out`](../../scratchpad/mbtime_after.out)). Gate: boot5e10-acceptance ([`disk_probe_5e10.py`](../../probes/disk/disk_probe_5e10.py):
      our own disk, boot code `CALL $5E10`, AUTOEXEC.BAS `10 PRINT "AX";5`; EU / ZB `AX 5`,
      [`boot5e10_gate.out`](../../scratchpad/boot5e10_gate.out)). 🔪 K-MB1 ([`mbpin_knife.py`](../../scratchpad/mbpin_knife.py)): kernel.asm back to HEAD -> ZB `no AX`,
      DIVERGES, all five restored ([`mbpin_knife.out`](../../scratchpad/mbpin_knife.out)). Docs: concepts/disk.md.

      📏 **UR-1.dsk, MEASURED 2026-11-07 -- IT DEPENDS ON WHAT THE REFERENCE'S H.READ HL POINTS AT**
      (sdsboot_probe.py SDS_IMG / SDS_TRANS / SDS_ENTRY / SDS_STACK: PC values, registers and
      stack words only -- no ROM byte, no game byte; [`ur1_trans_zb.out`](../../scratchpad/ur1_trans_zb.out), [`ur1_trans_cf90.out`](../../scratchpad/ur1_trans_cf90.out),
      [`ur1_8500_cf.out`](../../scratchpad/ur1_8500_cf.out), [`ur1_8507_cf.out`](../../scratchpad/ur1_8507_cf.out), [`ur1_8507_zb.out`](../../scratchpad/ur1_8507_zb.out), [`ur1_rst8_zb.out`](../../scratchpad/ur1_rst8_zb.out)). Its BLOAD,R code ($8500)
      installs a handler at $8507 on **H.READ ($FF07, the prompt hook)** and returns. The
      CF-3300 calls it at each prompt (~24 / 50 / 75 s) with HL = $7685 / $7683 / $7680 and DE =
      $6FB6 / $7612 / $7346 -- ADDRESSES IN ITS OWN BASIC ROM -- and the handler's `RST 08h`
      (SYNCHR) on HL succeeds. zerobas calls it with HL = DE = BC = $000B: SYNCHR fails, the
      error prints the prompt, H.READ calls the handler again, a stack word leaks per round,
      and the stack runs over the hooks at 33 s (H.TIMI -> $6132, H.ERRO -> $7801, mid-routine
      here) -- the reset the collection saw. (The "BOTH-RUN" before 2026-11-07 was the
      classifier, diskcorpus_rescore.out.)
      ✅ **AND IT IS AN MSX2 TITLE -- OUT OF SCOPE (Joost, 2026-11-07: "isn't UR-1 MSX2
      anyway?").** On the Philips NMS 8250 (MSX2) it runs in **SCREEN 8** -- an MSX2-only mode
      -- at line 30, stable at 45 and 90 s ([`ur1_nms8250_45.out`](../../scratchpad/ur1_nms8250_45.out), [`ur1_nms8250_90.out`](../../scratchpad/ur1_nms8250_90.out)). The CF-3300
      does NOT run it either: it jumps to $0000 at 24 s and comes back every ~25 s
      ([`ur1_trans_cf90.out`](../../scratchpad/ur1_trans_cf90.out), TRANS 0000 from FFB7) -- an MSX1 rebooting on an MSX2 program,
      which the collection's one-sample class read as "running". ~~🙋 the H.READ HL question~~
      withdrawn: there is no MSX1 behaviour to match. Same standing as BREAKER (MSX2, both
      fail). 🔴 Lesson: run a NOBOOT disk on an MSX2 too before tracing it.
      📏 **GAUNT.DSK, THE SAME DAY: THE CF-3300 DOES NOT RUN IT EITHER.** At 15, 20, 45 and 90 s
      the CF-3300 shows its BOOT LOGO ("MSX system version 1.0", SCREEN 1) with CURLIN = 0
      ([`gaunt_cf_45.out`](../../scratchpad/gaunt_cf_45.out), [`gaunt_cf_90.out`](../../scratchpad/gaunt_cf_90.out)) -- it never reaches the game; the collection's "ref
      RUNNING" was CURLIN = 0 during the logo (not $FFFF: a SECOND blind spot of the one-sample
      class, beside the hook-PC one fixed today). The NMS 8250 (MSX2) runs it: a BASIC loader in
      SCREEN 2 at 30 s, the game's own code by 60 s ([`gaunt_nms8250_30.out`](../../scratchpad/gaunt_nms8250_30.out)). zerobas resets after
      the boot code's `$4022`. With no MSX1 disk reference that runs it, GAUNT is not a
      divergence to chase here; same standing as UR-1 and BREAKER. 📏 So the collection's
      ZB-NOBOOT rows (2026-11-07) are both disks the CF-3300 cannot run.
      ✅ **THE LOGO HALF, DONE (2026-11-07):** diskcorpus_run.py's is_logo() -- every non-blank
      row one of the boot logo's -- makes a row "booting", not RUNNING, live and in the stored-row
      re-score. Re-scored ([`diskcorpus_rescore2.out`](../../scratchpad/diskcorpus_rescore2.out)): Seedofda, UZIX and quinpl BOTH-RUN ->
      ZB-ONLY (the CF-3300 on its logo at the sample). ➡️ NOT settled: a BLANK text screen
      with CURLIN 0 still reads RUNNING (zerobas's Seedofda / quinpl rows, the CF-3300's GAUNT
      row) -- CURLIN 0 is also the work area before BASIC sets it. Settle it with a later
      sample per row or a published "BASIC is up" cell, not a guess.
      ✅ **SETTLED AS A CLASS OF ITS OWN (2026-11-11): UNSETTLED** ([`diskcorpus_unsettled.out`](../../scratchpad/diskcorpus_unsettled.out)).
      diskcorpus_run.py's is_unsettled() -- a blank S0/S1 screen, CURLIN 0, the PC in ROM --
      is reported as itself, never RUNNING; a row that kept NO screen is never read as blank.
      🔴 **AND THE REFERENCE'S SCREEN HAD BEEN LOST FROM EVERY RE-RUN:** rerun_zb carried the
      reference's CURLIN / PC / mode / files but not ref_text, so is_logo / is_unsettled saw no
      reference screen at all in diskcorpus_f37.json; now carried, and `--rescore JSON
      [--rescore-ref FULL_JSON]` re-classifies stored rows offline. The latest run re-scored:
      **BOTH-RUN 117 -> 97, UNSETTLED 20** -- twenty "both run" rows rested on a blank screen.
      Re-run with a third sample at 120 s (predicted: most settle -- MISS): 18 still
      UNSETTLED, 2 ZB-ONLY (TestameB, quinpl). Most of the 18 sit with BOTH PCs in their disk
      ROMs for 120 s on a blank screen (the ic* set: $761B on the CF-3300, $7AAC here) --
      agreement on waiting, likely data disks of multi-disk sets, not a program running.
      ➡️ Next: per row, what a USER sees (a key, a disk swap) -- not another sample. The PC
      rule's own gap, filed here: under MSX-DOS page 0 is RAM, so a PC of $0005 (the BDOS
      jump) is a running DOS program, not ROM (the xak rows of the older full run).
      📏 **ZEROBAS-ONLY RE-RUN AFTER D-ROBOREG (2026-11-13, [`diskcorpus_20261113b.out`](../../scratchpad/diskcorpus_20261113b.out), against
      the same day's reference rows):** BOTH-RUN 92 -> 97, ZB-NOBOOT 3 -> 1 (UR-1 alone, 🔮 HIT),
      UNSETTLED 22 -> 19 (xak2eng3 / 4 / 5 now BOTH-RUN -- the page-1 bounce fix), and ONE row
      worse, facdemo3 FILES-SAME -> ZB-ONLY (🔮 "no row worse": MISS) -- filed under
      D-BD2FRAGILE, a layout-sensitive program, not a wrong value. 🔴 **WRONG -- IT WAS A WRONG
      VALUE (D-DRVCOUNT, fixed the same day):** DRVINF ($FB21) read 3 under Disk BASIC, the
      CF-3300 2. D-DRVINT (11-08) made our disk INIT write the drive count there, and main's
      slot scan then `inc`ed the same cell (it is also main's DISKSLOT_OK): 2 + 1. Main now
      turns 0 -> 1 and $FF -> 0 and keeps a count the disk ROM wrote (basic/islands.asm; every
      reader tests nonzero only). facdemo3 FILES-SAME again ([`facdemo3_run5.out`](../../scratchpad/facdemo3_run5.out), 🔮 HIT, and
      DRVINF 02 87, [`facusr_run9.out`](../../scratchpad/facusr_run9.out)). D-DRVINT was measured under MSX-DOS only; the new
      **`make drvinf-acceptance`** ([`disk_probe_drvinf.py`](../../probes/disk/disk_probe_drvinf.py)) reads it from Disk BASIC: unfixed 3 vs 2
      FAIL ([`drvinf_run1.out`](../../scratchpad/drvinf_run1.out)), fixed PASS ([`drvinf_run2.out`](../../scratchpad/drvinf_run2.out)).
      📏 **RE-RUN AFTER THE DAY'S FIXES (2026-11-13 evening, after D-IFFREAD; zerobas only against
      the morning's reference rows, [`diskcorpus_iffread.out`](../../scratchpad/diskcorpus_iffread.out)):** BOTH-RUN 98, **ZB-NOBOOT 0**,
      FILES-SAME 11, UNSETTLED 19, ZB-ONLY 5 -- two rows up, none down (🔮 "no row worse": HIT):
      **UR-1.dsk ZB-NOBOOT -> BOTH-RUN** (ZB-NOBOOT since 11-07; which of the day's fixes did it is
      not isolated -- D-ROBOREG's bounce / SAVSTK / USR, D-DRVCOUNT, D-TAPEBIOS, D-IFFREAD all
      landed before this run) and facdemo3 ZB-ONLY -> FILES-SAME (D-DRVCOUNT).
      - [ ] **diskcorpus_run.py's "last sample" sorts tags as STRINGS** -- 🎚️ APPARATUS — `sorted(t
            for t in caps)` puts `T120` before `T45`, so the 2026-11-11 third sample at 120 s was
            never the one read as last: that row set's UNSETTLED reading rests on the 45 s sample.
            Sort by the number.
