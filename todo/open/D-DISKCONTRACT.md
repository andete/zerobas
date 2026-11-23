- [ ] 🎯 **D-DISKCONTRACT — THE DISK ROM'S BIOS-LEVEL ENTRIES AND THE BDOS: WHAT IS COMPARED, NOT ONLY CALLED (filed
      2026-11-17, Joost widening the focus: *"Widen to BDOS/disk BIOS"*)**
      🎚️ TIER 1 — the entry surface; the disk ROM's first user is C-BIOS WITHOUT BASIC (Joost 2026-11-14).
      🤖 **AUTONOMOUS** — black box: registers, RAM, the disk image, the FDC's port traffic; the CF-3300 the reference.
      ➡️ FIRST: a contract inventory as D-BIOSCONTRACT2's (scratchpad/bios_contract_inventory.md) -- per published disk-ROM
      entry (DSKIO, DSKCHG, GETDPB, CHOICE, DSKFMT, MTOFF, the pinned kernel entries) and per BDOS function: what a caller
      can observe, which gate DIFFS it against the CF-3300, the gap -- ranked; then the gaps in order. Out of scope:
      BASIC-facing work (Disk BASIC statements), tape. The BDOS speed items stay TIER 5.
      📋 **THE INVENTORY: [`disk_contract_inventory.md`](../../scratchpad/disk_contract_inventory.md)** (2026-11-17, a read-only agent; headline verified by hand).
      ✅ **(1) CLOSED 2026-11-17 -- the gates ran on the WRONG HOST.** bdos- / dskfmt- / fmtdos-acceptance compared our
      disk.rom under the CF-3300's OWN BIOS (omsx_session.py's OURS_MACHINE default National_CF-3300_ZEROBASDISK), never on
      the shipped C-BIOS machine. Measured there: bdos 25 / 25 converge ([`DKC_bdos_cbios.out`](../../scratchpad/DKC_bdos_cbios.out)), dskfmt 4 / 4, fmtdos 3 / 3
      ([`DKC_dskfmt_cbios.out`](../../scratchpad/DKC_dskfmt_cbios.out), [`DKC_fmtdos_cbios.out`](../../scratchpad/DKC_fmtdos_cbios.out)) -- no bug (prediction "a divergence" MISSED). The three now run with
      `ZEROBAS_OURS_MACHINE=$(REPACK_MACHINE)`; the CF-3300-host BDOS run stays as `bdos-cfhost-acceptance` (gate_wt's
      EXCLUDED5 list). 🔭 TIER 5: some exercisers run much slower on C-BIOS (WRZER 65.8 s vs 42.8, DOSL-D3 155.6 vs 93.0).
      ✅ **(2) / (3) DSKIO PART, 2026-11-17.** New `make phydioerr-acceptance` (probes/disk/disk_probe_phydioerr.py): PHYDIO
      ($0144 -> DSKIO) called directly on the shipped machine against the CF-3300 -- a WRITE (sector 13 then compared in
      both images), a write to a write-protected (read-only) image (Cy, A = 0, nothing written), no disk (A = 2), the
      last sector, sectors past the end, $FFFF: 6 SAME, 3 a REAL DIFFERENCE pinned ([`PE_run1.out`](../../scratchpad/PE_run1.out), [`PE_run2.out`](../../scratchpad/PE_run2.out), [`PE_run3.out`](../../scratchpad/PE_run3.out)):
      a cylinder past the last (sector 1440 / 1500 / 2000) -> the CF-3300 A = 2 (not ready), zerobas A = 8 (record not
      found); $FFFF wraps in range on both (so a CYLINDER rule, not a sector-count one) -- filed D-DSKIOCYL below.
      Left of (2): the BDOS-level error path (DISKVE / Abort-Retry-Ignore for a .COM program); CRC / seek codes.
      🔴 **(2) BDOS LEVEL, 2026-11-17 -- A REAL DIFFERENCE, FILED D-DISKVE (next).** New exerciser BDOSXE (probes/disk/bdosxe.asm,
      build_bdosxe_disk.py; NOT gated yet -- it would be RED): FMAKE and WRABS on a WRITE-PROTECTED disk with the program's own
      DISKVE handler. The CF-3300 calls it twice (A = 0, C = $01 -- write / write-protect, B = 1), then FMAKE A = 0 and WRABS
      A = $FF after Ignore; zerobas NEVER calls it -- FMAKE A = $FF, WRABS A = 0 (SUCCESS on a protected disk)
      ([`XE_stock.out`](../../scratchpad/XE_stock.out), [`XE_ours.out`](../../scratchpad/XE_ours.out), [`XE_run1.out`](../../scratchpad/XE_run1.out)).
      ✅ **(5) DIRIO WITH A KEY WAITING, 2026-11-17 -- SAME, no bug.** BDOSX2 stages a 4th key ('xyzw'); record 11 POLLS
      DIRIO input ($06, E = $FF) until it answers (A = $77 'w' on both), a new record 14 keeps the drained case (A = 0):
      0-byte-diff ([`DK_run4.out`](../../scratchpad/DK_run4.out), [`DK_ours2.out`](../../scratchpad/DK_ours2.out)). TWO APPARATUS TRAPS on the way: record 14 moved `done` to $0205, which
      the CF-3300's BOOT passes through -- a vacuous anchor at t = 14.8 s reading boot RAM ([`DK_stock.out`](../../scratchpad/DK_stock.out)); `done` is
      now pinned at $0330. And a single DIRIO call agreed on both machines with A = 0 -- 'w' was not yet typed -- so
      it never saw a key ([`DK_ours.out`](../../scratchpad/DK_ours.out)): a case agreeing for the wrong reason.
      ✅ **(4) THE $F37D DISPATCH, 2026-11-17 -- A REAL DIFFERENCE FIXED (D-SETRNDRS).** New `make bdosf37d-acceptance`
      (probes/disk/bdosf37d_acceptance.py): 25 rows through $F37D -- VERSION LOGIN CURDRV SELDSK GDATE GTIME ALLOC SFIRST
      SNEXT FOPEN FSIZE SETRND RDRND FCLOSE FREN FDEL FMAKE WRRND WRZER CONST DIRIO CONOUT -- every A, the published
      register outputs, 5 FCBs, the DTA, root entries 0..3: all SAME but FCB S's +36 ([`F7_run1.out`](../../scratchpad/F7_run1.out)). Tracked per row
      ([`F7_run2.out`](../../scratchpad/F7_run2.out), [`F7_run3.out`](../../scratchpad/F7_run3.out)): SETRND set RR's top byte from a 16-bit RS / 2. D-BDOSFCB's rule (11-10) was
      measured with RS = 128 and 1 only, where two rules COINCIDE; [`setrnd_rs_probe.py`](../../scratchpad/setrnd_rs_probe.py) (RS = $0080 $0181 $0200
      $0400 $1234 $FFFF, [`F7_rs2.out`](../../scratchpad/F7_rs2.out)) separates them: the CF-3300 sets r2 = RS's LOW byte / 2, r3 = 0. setrnd_body
      (disk/kernel.asm, both $0005 and $F37D) fixed, 4 B shorter: 6 / 6 ([`F7_rs3.out`](../../scratchpad/F7_rs3.out)), bdosf37d PASS ([`F7_run4.out`](../../scratchpad/F7_run4.out)).
      ✅ **(5) THE CONSOLE'S SCREEN OUTPUT, 2026-11-17.** New exerciser BDOSXC (in bdos-acceptance): CLS, TAB, BS, BEL,
      ESC Y and two STROUTs; the program reads its own name table back through the VDP ports (a CALSLT to LDIRMV
      copied NOTHING on either machine -- an all-zero buffer that AGREED: [`XC_stock.out`](../../scratchpad/XC_stock.out)) with LINLEN / CSRY / CSRX:
      0-byte-diff ([`XC4_run.out`](../../scratchpad/XC4_run.out)). One real difference, FILED D-CONCOL below: the BDOS's logical column ($F237, which TAB
      counts from) after a control code ([`XC2_stock.out`](../../scratchpad/XC2_stock.out), [`XC3_stock.out`](../../scratchpad/XC3_stock.out), [`XC3_ours.out`](../../scratchpad/XC3_ours.out)). The gated text places TABs only
      after CR LF / printable text. Left of (5): the echo of CONIN / BUFIN on screen; Ctrl-P / Ctrl-C / Ctrl-S.
      ✅ **(5) BUFIN'S ECHO, 2026-11-17 -- A REAL DIFFERENCE FIXED (D-BUFINECHO).** New exerciser BDOSXK (in
      bdos-acceptance): typed `x` (CONIN) then `Helz` BS `lo` Return (BUFIN), the screen read back. The buffer matched;
      the SCREEN did not: the CF-3300 erases the BackSpaced char (BS, space, BS -- `Helz` BS Return separated it from a
      bare BS) and echoes CR on Return (cursor at column 0); ours showed "Helzlo" / "Helz", cursor after
      ([`XK_stock.out`](../../scratchpad/XK_stock.out), [`XK_ours.out`](../../scratchpad/XK_ours.out), [`XK2_stock.out`](../../scratchpad/XK2_stock.out), [`XK2_ours.out`](../../scratchpad/XK2_ours.out)). conin_line_body (disk/runtime.asm): BS un-echoes through fmt_pr,
      Return echoes CR; +12 B net into the 13 B pad before $7F7C. After: 0 diffs on both key sets ([`XK3_1_ours.out`](../../scratchpad/XK3_1_ours.out),
      [`XK3_2_ours.out`](../../scratchpad/XK3_2_ours.out)). Left of (5): Ctrl-P / Ctrl-C / Ctrl-S at the console.
      ✅ **(9) THE DISK IMAGE AFTERWARDS, 2026-11-17.** bdosf37d now diffs the WHOLE image after its 25 $F37D calls
      (FMAKE / FDEL / FREN / WRRND / WRZER / FCLOSE among them): boot, both FAT copies, the root, the data area -- all SAME
      but one sector ([`IM_run1.out`](../../scratchpad/IM_run1.out)): the never-written records of NEWFILE.TMP's reused cluster -- the CF-3300 writes its
      STALE sector buffer around WRRND's record, ours reads-modifies-writes the old sector. Undefined content; excused
      by name and FILED D-SLACK below ([`IM_run2.out`](../../scratchpad/IM_run2.out): PASS).
      ✅ **(13) A SECOND GEOMETRY, 2026-11-17.** bdosf37d runs on a 360 KB single-sided image too (media $F8, 2-sector FATs,
      the regions from the image's own BPB; ZB_GEOMETRY=360, both in the gate): all 25 rows, the FCBs, the DTA and the
      whole image SAME (ALLOC 354 clusters on both: [`G3_360.out`](../../scratchpad/G3_360.out); 720 KB still PASS, [`G3_720.out`](../../scratchpad/G3_720.out)). No bug.
      ✅ **(7) A DISK SWAP, 2026-11-17 -- SAME.** The harness can swap drive A mid-run now (disk_probe_diff.py
      `--swap-image` / `--swap-at`, omsx_session.run_job's `swap_at` / `swap_image`: an `after time` `diska`). New exerciser
      BDOSXS (in bdos-acceptance): DSKCHG before the swap (B = 1), after it (B = 0 -- "unknown", NOT $FF, on BOTH), then
      an SFIRST finds SWAPPED.TXT, a file only the new disk holds: 81 B byte-identical ([`XS_stock.out`](../../scratchpad/XS_stock.out), [`XS_ours.out`](../../scratchpad/XS_ours.out)).
      🔴 **(8) DRIVE B UNDER MSX-DOS, 2026-11-17 -- A REAL DIFFERENCE, FILED D-DOSDRVB.** New exerciser BDOSXB (probes/disk/
      bdosxb.asm; NOT gated yet -- it would be RED): SELDSK 1, CURDRV, SFIRST *.* on the default drive, the screen read back.
      The CF-3300 selects B ($F247 = 1, CURDRV 1), and the SFIRST prompts "Insert diskette for drive B: / and strike a key
      when ready", waits for the key, and leaves the DTA's drive byte 2; zerobas stays on A ($F247 0, CURDRV 0, no prompt,
      DTA drive 1) ([`XB_stock.out`](../../scratchpad/XB_stock.out), [`XB_ours.out`](../../scratchpad/XB_ours.out), [`XB2_stock.out`](../../scratchpad/XB2_stock.out), [`XB2_ours.out`](../../scratchpad/XB2_ours.out)).
      🔴 **(11) SDATE / STIME INVALID INPUT, 2026-11-17 -- STIME's RANGE CHECK MISSING, FILED D-STIMERANGE.** New exerciser
      BDOSXT (probes/disk/bdosxt.asm, in bdos-acceptance): 13 cases, each followed by GDATE / GTIME. SDATE is the SAME on
      every row (valid 0; month 13, Feb 30, 1979, 2100, month 0 all $FF and the date kept; the leap day valid). STIME:
      the CF-3300 answers $FF for hour 25, minute 60, second 60, hundredths 100; ours 0 every time
      ([`XT_stock.out`](../../scratchpad/XT_stock.out), [`XT_ours.out`](../../scratchpad/XT_ours.out)). Those 4 bytes are pinned at ours in the gate. 🔮 "the CF-3300 keeps the time STIME set": MISS --
      its GTIME reads 00:00:00 throughout, as ours (no clock on an MSX1). Left: (12) VERIFY, (5) Ctrl-P / C / S, (6) > $30.
      💰 **D-DISKCARVE6 STEP 1 (2026-11-17): a 61 B hole at $7568, in front of the $75A5 pin.** A read-only agent's plan
      (checked against the source): the span [$607B, $75A5) has no pin inside, so any byte freed there lands in front of
      $75A5. Four call-only routines MOVED into exact-fit pads in front of other pins -- wrblk_mul_rr_rs (14 B -> $4FF8),
      wrblk_off24 (11 -> $420C), hl_x128 / hl_x32 (8 -> $445A), fmt_buf (8 -> $5016) -- plus 8 B of savings inside the
      span (the dead `jr dc_result`; jp -> jr to dskio_calslt x2, to sv_load_error x3, sav_fin's). `make basic-reloc`: disk
      free 0 -> 61 B, one run (🔮 61: HIT). All 12 disk suites, knives and unit tests green. Reserve (the same plan): fmt_key /
      fmt_echo (8 -> $5046), fname_ev (7 -> $4365) for 76 B; skip_sp, fmt_err for 89 B.
      💰 **STEP 2 (2026-11-17): 76 B at $7559.** fmt_key / fmt_echo moved in front of $504E, fname_ev in front of $436C
      (🔮 76: HIT). Left in reserve: skip_sp (7 -> $47AB), fmt_err (6 -> $5FDE) for 89 B.
      ➡️ NEXT: ~~D-DISKVE into the hole~~ ✅ LANDED 2026-11-17 (74 of the 76 B); then D-DOSDRVB, D-CONCOL,
      D-DSKIOCYL -- the plan's reserve (skip_sp, fmt_err) first.
      💰 **STEP 3 (2026-11-17): the reserve, 2 -> 15 B at $7596** (🔮 15: HIT). skip_sp moved into the 7 B pad in
      front of $47B2 (disk/fat.asm), fmt_err into the 7 B pad in front of $5FE5; the plan is spent. More exact-fit
      pads stand (zero runs of 7-10 B at $4006, $47B5, $4E93, $4FE4, $5051, $50A2, $50D8, $5532 -- read
      `build/disk.rom`, never this list) for the next call-only moves.
      💰 **STEP 4 (2026-11-17): 2 -> 72 B at $755D** (🔮 72: HIT), for D-DOSDRVB part 2's MSX-DOS prompt. A read-only
      agent's plan, each item checked against the source: fdc_wp_chkrdy -> $553C, fmt_off -> $50E0, fmt_bkey -> $77B8,
      fat_total_clusters -> $544E, fcf_zero -> $43A4, disk_putbyte -> $5058, hkcv_float -> $50A9 (its jr -> jp), and
      four duplicate tails folded (hkdf_done / hkdf_bad -> hk_claim_status, fat_dir_update -> fat_dir_create's write-back,
      fat_advance -> fat_open's). Left out: toupper (needs fat.asm's $47B9 anchor dropped -- unproven), fmt_t_q (its 3 B
      pad's pin line not found). 🔴 tools/check_dead_code.py: `conin` ($50E0) was live only by falling through its pad
      (fix 16's accident); fmt_off in that pad turned it and six callees "dead" -- now a declared DISK_PIN_ROOT.
      🔴 **D-DISKVE's KEY FAILS (measured 2026-11-17):** under BASIC the CF-3300's DISKVE ($F323) holds $72AE (its BASIC's
      handler cell), zerobas's holds $C9C9 -- NOT zero. "Call the handler when DISKVE is non-zero" would make zerobas BASIC
      jump through a garbage pointer on its first disk error. So D-DISKVE also needs: zerobas's disk init leaving a known
      DISKVE under BASIC (~6 B in init), a measurement of what MSX-DOS's boot leaves there, and RDABS / WRABS's A = $FF
      after Ignore (a flag, or their own call). The wrapper itself prices ~66 B (Retry by re-entry, Abort `jp 0`
      -- unmeasured, Ignore = NC): over the 61 B hole, so carve step 2 (the plan's reserve: fmt_key / fmt_echo, fname_ev
      -> 76 B) first.
