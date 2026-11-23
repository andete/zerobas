- [ ] 🎯 **D-BIOSCONTRACT2 — THE 108 BIOS ROWS ARE WITNESSED; THEIR CONTRACTS ARE NOT ALL COMPARED (filed
      2026-11-14 under Joost's focus ruling: *"Any work done from now on till we broaden the scope again
      should be on MSX1 BIOS calls."*)**
      🎚️ TIER 1 — the BIOS entry surface (Joost 2026-11-08 / 11-13: entry points first, for C-BIOS upstream).
      🤖 **AUTONOMOUS** — black box: registers, work area, VRAM, PSG / VDP registers, ports, printer logger.
      📋 **THE QUEUE: [`bios_contract_inventory.md`](scratchpad/bios_contract_inventory.md)** -- per entry, what a caller can observe, which gate DIFFS
      it against a reference, and the gap (a read-only agent's reading of every gate source; tier-status's
      "exercised by" only says a gate NAMES an entry). Ranked gaps: (1) FORMAT -- nothing compared; (2)
      LPTOUT -- no direct comparing call; (3) STMOTR / CHGSND -- a port $AA bit, only registers diffed; (4)
      OUTDO's output and PRTFLG path; (5) the VDP REGISTERS after DISSCR / ENASCR / WRTVDP / CHGMOD /
      INI* / SET* / TOTEXT / CHGCLR (only RAM shadows diffed); (6) SETRD / SETWRT's address pointer; (7) flags
      BF misses (CNVCHR, ISFLIO, GSPSIZ, SETATR, the INLIN family's Cy on STOP, BREAKX held); (8) non-idle
      states (LPTSTT ready, LFTQ / GETVCP non-empty, PUTQ full, devices); (9) GICINI's queues, INITIO's exit
      registers; (10) SCREEN 3 variants of the cursor / MAPXYC / READC / SETC / NSETCX entries. Plus
      entry_table.py's own faults (biosl's rungs never credited; spurious CHKRAM / LEFTC / FORMAT witnesses;
      subrom-acceptance backs CALSLT with no reference).
      ✅ **(3) CLOSED 2026-11-14:** biosregs gained stmotr0b / stmotr1b / stmotrffb (port $AA bit 4) and chgsnd0b
      / chgsnd1b (bit 7): **5 / 5 SAME as the VG-8020** ([`BC_run1.out`](scratchpad/BC_run1.out)) -- no bug, an unmeasured contract
      now gated (each pair expects different bits, so an entry that ignored A fails one).
      ✅ **(5) CLOSED 2026-11-14:** new `make biosvdp-acceptance` (probes/basic/basic_probe_biosvdp.py; omsx_repl gained
      a `("vdpregs",)` capture -- R0..R7 through openMSX's `vdpreg`, the emulated chip, no ROM byte): DISSCR,
      ENASCR, WRTVDP (R7 := $5A, not its default), CHGMOD 0..3, INITXT / INIT32 / INIGRP / INIMLT, SETTXT /
      SETT32 / SETGRP / SETMLT, TOTEXT, CHGCLR -- each called through biosregs' USR stub, the program then
      looping so BASIC's prompt cannot reset the mode: **17 / 17 SAME as the VG-8020** ([`BV2_run1.out`](scratchpad/BV2_run1.out),
      [`BV2_run2.out`](scratchpad/BV2_run2.out) for WRTVDP's discriminating value). No bug; the chip now gated, not only the shadows.
      ✅ **(2) LPTOUT / (8) LPTSTT READY, 2026-11-14 -- AND A REAL DIFFERENCE (D-LPTSTTF).** The inventory's "LPTOUT:
      none directly" was wrong: outdlp-acceptance's lptout_noprn / lptout_intflg call `$00A5` from DATA bytes
      (decimal -- entry_table.py's name scan cannot see them); its ABORT path was compared. Added: `lptout_tab`
      (LPTOUT to the always-ready logger: `A\x09B\r\n`, the TAB NOT expanded, LPTPOS untouched) -- SAME; and
      `lptstt_rdy` (LPTSTT with the logger: A and F & $C1) -- **DIVERGED** ([`LP_run1.out`](scratchpad/LP_run1.out)): the VG-8020
      returns ready A = $FF **F = $BB**, not ready A = 0 **F = $42** ([`LP_flags.out`](scratchpad/LP_flags.out); the CF-3300's scrape was
      in the wrong VRAM plane, unread); C-BIOS gave $BC / $54 -- Cy always clear. Both readings are exactly `ccf /
      sbc a,a` after the busy bit is shifted into Cy (the flags read as a result, no ROM byte): **cbios-repack #24
      `lptstt-flags.patch`**, 4 B shorter, padded -- 7 bytes change, nothing moves (byte-diffed); REPACKED_SHA1
      5543843885.... After: outdlp 12 / 12 ([`LT_outdlp.out`](scratchpad/LT_outdlp.out)), biosflags green.
      ✅ **(6) CLOSED 2026-11-14:** biosvram-acceptance gained `setwrt` (HL $1006, then OUR OWN two OUT $98: $C3 $3C at
      $1006 / $1007 -- the pointer and its auto-increment) and `setrd` (HL $1009 over seeded $9A $9B, OUR OWN two
      IN $98 -> $9A $9B), DI around call and port I/O: **2 / 2 SAME as the VG-8020** ([`SW_run1.out`](scratchpad/SW_run1.out)). No bug.
      ✅ **(7) PART CLOSED 2026-11-14 -- AND TWO REAL DIFFERENCES (D-CNVCHRF, D-GRPHEDCLS).** biosflags gained
      isflio / gspsiz8 / gspsiz16 / setatr_ok / setatr_bad -- SAME ([`FL_run1.out`](scratchpad/FL_run1.out)) -- and cnv_plain /
      cnv_hdr / cnv_graph / cnv_nogfx, which **DIVERGED** ([`FL_run1.out`](scratchpad/FL_run1.out), [`FL_run2.out`](scratchpad/FL_run2.out)): C-BIOS's CNVCHR had
      the Z sense of the plain and converted answers swapped. **cbios-repack #25 `cnvchr-flags.patch`**, CHPUT's
      own test inverted with it (the first cut alone broke every typed line). cnv_hdr then read nothing on
      zerobas ([`CV_run3.out`](scratchpad/CV_run3.out)): GRPHED survived BASIC's CLS. Measured directly ([`CV_grphed2.out`](scratchpad/CV_grphed2.out)): the
      VG-8020 clears GRPHED in INITXT / INIT32 / CHGMOD 0, 1 / a text CLS, in nothing else; C-BIOS never.
      **cbios-repack #26 `grphed-cls.patch`** (cls_text clears it, 4 B from INIMLT's pad; the video block
      moves 4 B, GRPPRT's guard follows) + new `make grphed-acceptance`: 12 / 12 SAME ([`GH_gate.out`](scratchpad/GH_gate.out)),
      CNVCHR 4 / 4 ([`GH_cnv.out`](scratchpad/GH_cnv.out)); the screen / BIOS suites and unit tests green on the moved image
      ([`GH_biosflags-acceptance.out`](scratchpad/GH_biosflags-acceptance.out) and its GH_* siblings). Left of (7): the INLIN family's Cy on STOP, BREAKX held -- both
      closed below.
      ✅ **(4) CLOSED 2026-11-14 -- A REAL DIFFERENCE (D-OUTDOPRT).** outdlp-acceptance gained outdo_prn /
      outdo_prncol (OUTDO with PRTFLG ($F416) = 1) and outdo_scr (PRTFLG 0). The VG-8020 PRINTS with PRTFLG set,
      exactly OUTDLP's answer (TAB to spaces, LPTPOS 9 after `ABC TAB D`); zerobas's outdo went to pchar, the
      printer got nothing ([`OD_run1.out`](scratchpad/OD_run1.out): 13 / 15). outdo (basic/islands.asm) now jumps to `outdo_dest`
      (basic/main.asm, the low region's end: 15 B, 9 B left there): PRTFLG != 0 -> bios_outdlp, else pchar as
      before (zerobas's own LPRINT uses PRDEST / PRDEV and never sets PRTFLG). After: 15 / 15 ([`OD_run2.out`](scratchpad/OD_run2.out)).
      ⚠️ Not separated: which of PTRFIL (a file) and PRTFLG wins when both are set.
      ✅ **(7) CLOSED 2026-11-14 -- AND A SMALL DIFFERENCE (D-INLINSTOPF).** outdlp-acceptance gained pinlin_stop /
      inlin_stop / qinlin_stop: each entry waiting for a line, CTRL-STOP held. Both machines break the program
      (`Break in 20`), so the row ALSO reads the F / A the entry stored, from RAM after the run -- the break alone
      would agree without ever seeing Cy. Cy = 1 on both; the VG-8020's F = $45, A = 0 (`xor a / scf`'s flags),
      zerobas's F = $21, A = $0D ([`IN_run2.out`](scratchpad/IN_run2.out)). bios_inlin's STOP exit now `xor a / scf` (+4 B, the $3283
      pin pad 6 B left): 3 / 3 ([`IN_run3.out`](scratchpad/IN_run3.out)). BREAKX with STOP held was already compared (breakx_loop spins
      on its Cy).
      ✅ **(8) PART CLOSED 2026-11-14:** new `make biosq-acceptance` (probes/basic/basic_probe_biosq.py): after GICINI,
      LFTQ with 3 bytes queued (and queues 0 / 1 apart), PUTQ until it answers Z (127 bytes, LFTQ then 0), GETVCP
      voices 1 / 2, GETVC2 voice 2 offset 5: **6 / 6 SAME as the VG-8020** ([`BQ_run2.out`](scratchpad/BQ_run2.out)). No bug. The first run's one
      split was the APPARATUS: a result byte the code never wrote ([`BQ_run1.out`](scratchpad/BQ_run1.out)); the words are zeroed first now.
      ✅ Then GTSTCK stick 0 with RIGHT / UP+RIGHT / LEFT held (3 / 2 / 7) and GTTRIG trigger 0 with SPACE held (255),
      the key-matrix bits pressed by the harness, the code HALT-looping until the entry answers: **4 / 4 SAME**
      ([`BQ_run3.out`](scratchpad/BQ_run3.out)). 🔴 That commit then FILED ports 1 / 2 and GTPAD / GTPDL as undrivable -- WRONG (Joost: "don't
      we have the dongle"): input-devices-acceptance already plugs openMSX's paddle / touchpad / arkanoidpad, and
      the STRIG traps' PSG-latch injection (docs/spec-traps-t2-strig.md §7.3) presses ports 1 / 2. ✅ biosq now has
      both, DIRECT: latch rows (our code sets PSG R7 output, writes R14, calls GTSTCK / GTTRIG ports 1 / 2) and plug
      rows (GTPDL 1..6 with a paddle, GTPAD 0..7 with an arkanoidpad, ports A / B): **8 / 8 SAME** ([`BQ_run4.out`](scratchpad/BQ_run4.out)),
      every answer non-zero. All four entries L3. **Gap (8) CLOSED.**
      ✅ **(9) CLOSED 2026-11-14 -- A REAL DIFFERENCE (D-GICINIQ).** biosq's `gicini_state` dirties QUETAB / QUEBAK,
      QUEUEN..PLYCNT and the three voice blocks with $55, calls GICINI, reads them back: the VG-8020 rewrites each
      voice queue's descriptor whole (0 0 0 $7F + its buffer), MUSICF / PLYCNT 0, the voice blocks to their PLAY
      defaults; C-BIOS's GICINI wrote the PSG only -- a program stopping its music with GICINI heard zerobas's
      interrupt drain on ([`GI_run1.out`](scratchpad/GI_run1.out)). New `bios_gicini` (basic/main.asm, $0090 overlaid) does it, keeps every register
      as the VG-8020 does, then C-BIOS's body writes the PSG. Funded by PROMOTING ex_strig_stmt and ex_on_interval
      (trap statements, page 1 only) from the low region into the $6CF3 page-1 pin pad (879 -> 798 B, read
      2026-11-14); low free was 9, then 35 B on 2026-11-14. ex_strig_stmt alone left 4 B, and switch-build-check went
      RED: every switch-off build was 3 B over on 2026-11-14, so ex_on_interval went up too. cbios-repack #27:
      INITIO calls GICINI through the jump table and leaves F $54 / A $FF / E $0B as both references; initio-
      acceptance now diffs the exit registers: 3 / 3 ([`GI_initio.out`](scratchpad/GI_initio.out)), gicini_state SAME ([`GI_run3.out`](scratchpad/GI_run3.out)).
      🔭 FILED: the voice blocks' BYTES -- the VG-8020 leaves VOLUMX $88 / ENVLPX $FF / ENVPRX 0 / TEMPOX 120,
      zerobas's PLAY keeps its own encoding (volume 8, envelope 0, M 255, tempo 0 = "reseed"): a BASIC-side
      sysvar-fidelity item, out of the BIOS focus; the row shows them, does not compare them.
      🔭 FILED: tools/promote_scout.py lists bios_putq / bios_inlin / odl_put / bios_fnk as PROMOTABLE -- BIOS
      entry bodies a program may call with RAM in page 1, so they must stay in page 0. The scout has no BIOS-entry
      seeds; nothing was promoted from that list.
      📊 **LEVEL COLUMN (Joost 2026-11-14, "yes add the level column"):** docs/tier-status.md's BIOS table
      gains a contract level per entry -- L1 called, L2 happy path, L3 full contract, L4 errors / edges (L5 speed
      unscored under the focus) -- from `tools/bios_levels.py`; each claim names its proving gate, and a claim whose
      gate no longer witnesses the entry REFUSES the page (tests/test_entry_table.py (f)). Gaps (8)-(10) are the
      L2 rows.
      ✅ **(10) CLOSED 2026-11-14 -- A REAL DIFFERENCE (D-TDOWNCGE).** biosregs gained the SCREEN 3 rows of RIGHTC /
      LEFTC / UPC / DOWNC / TUPC / TDOWNC / MAPXYC / READC / SETC / NSETCX (CMASK a nibble): 18 / 19 SAME
      ([`S3_run1.out`](scratchpad/S3_run1.out)). TDOWNC diverged: the VG-8020 stops for CLOC high byte $17 in SCREEN 3 as well as 5 --
      two rules fit (5 or $17 / anything >= 5), so rows H = 8, $16 and SCREEN 2's $18 separated them: >= the
      bottom row, both modes ([`S3_run2.out`](scratchpad/S3_run2.out)..[`S3_run4.out`](scratchpad/S3_run4.out)). cbios-repack #28 `tdownc-ge.patch`: `jr z` -> `jr c` against the row
      less one, same size; 12 / 12 ([`S3_run5.out`](scratchpad/S3_run5.out)). Ten entries to L3. **ALL TEN RANKED GAPS ARE CLOSED.**
      ✅ **L2 -> L3: CHSNS (2026-11-16) -- A REAL DIFFERENCE (D-CHSNSA).** biosflags gained chsns_k / chsns_k3 /
      chsns_wrap (keys put in KEYBUF by the row's own code): Z agreed, A did not -- the VG-8020 answers PUTPNT - GETPNT,
      low bytes (1, 3, and $DB across the ring's end -- the wrap row separated it from a key count), C-BIOS $FF
      ([`CK_run1.out`](scratchpad/CK_run1.out), [`CK_run2.out`](scratchpad/CK_run2.out), [`CK_run3.out`](scratchpad/CK_run3.out)). cbios-repack #29 `chsns-a.patch`, 8 B shorter, padded; 4 / 4 ([`CK_run4.out`](scratchpad/CK_run4.out)).
      ✅ **L2 -> L4: PINLIN / INLIN / QINLIN (2026-11-16).** The "HL not diffed" note was WRONG -- the rows' cell
      already printed HL ($F55D) and A ($0D); the inventory's general `:END` remark had been copied onto them. Added:
      the Enter exit's Cy (0 on both) and QINLIN's `? ` prompt read from the name table (`? AB` on both): 4 / 4 SAME
      ([`IL_run1.out`](scratchpad/IL_run1.out)). With the STOP exit (outdlp, D-INLINSTOPF) the three are L4. No bug.
      ✅ **L2 -> L3: CALSLT / CALLF (2026-11-16).** "IX / IY / AF' on return" are the PUBLISHED destroyed
      registers, not outputs; what was uncompared was the register path. biosq calls DCOMPR (slot 0) through each:
      AF $FFBB, HL $1234, BC $5A5A, DE $1235 back -- 4 / 4 SAME ([`CSL_run1.out`](scratchpad/CSL_run1.out)). No bug.
      ✅ **L2 -> L3: INITXT / INIT32 / INIGRP / INIMLT and CLS (2026-11-16) -- THREE REAL DIFFERENCES (D-INITKEYS).**
      New `make biosclr-acceptance`: all 16 KB of VRAM filled with $55, the entry called, VRAM compared byte for byte
      (the font aside). The VG-8020's INITXT / INIT32 / text CLS draw the function-key line, C-BIOS's left spaces;
      INITXT cleared 80 * 24 for LINLEN 40 (`cp 40`), the VG-8020 960 bytes; SCREEN 3's clear wrote $600-$7FF too
      ([`CL_run1.out`](scratchpad/CL_run1.out), [`CL_run3.out`](scratchpad/CL_run3.out)). cbios-repack #30 `initkeys.patch` (FNKSB through the table in INITXT / INIT32,
      `cp 41`, `$600`; INIGRP's 6 B pad) + zerobas `bios_cls` ($00C3: C-BIOS's body, then FNKSB in SCREEN 0 / 1;
      the low region was 35 B free, then 22 B on 2026-11-16): 8 / 8 SAME ([`CL_run4.out`](scratchpad/CL_run4.out)). GRPPRT's glyph is the last
      L2 row.
      ✅ **L2 -> L3: GRPPRT (2026-11-16).** Its glyph comes from the FONT, which differs by design -- so both fonts
      were read back from VRAM after INITXT and only the 44 non-blank characters identical in both are used
      ([`GP_font.out`](scratchpad/GP_font.out)). biosclr's gp2_plus / gp2_edge (a block at 250,190) / gp2_c5 / gp3_plus: all 16 KB SAME ([`GP_run2.out`](scratchpad/GP_run2.out)). The first
      run's gp3 split was the APPARATUS -- no $55 fill before INIMLT, the machines' leftover VRAM showed through
      ([`GP_run1.out`](scratchpad/GP_run1.out)). No bug. **L2 IS EMPTY**: CHKRAM / FORMAT stay L1 (spurious witnesses; FORMAT's body is the
      disk ROM's).
      ✅ **entry_table.py's faults fixed (2026-11-16, D-ENTRYFAULTS).** The name was matched case-INSENSITIVELY:
      FORMAT matched every `str.format`, BEEP a BASIC string's `beep`; $0000 matched VRAM-address constants (CHKRAM),
      $00FF slotregs' byte mask (LEFTC). Now: names case-sensitive, $0000 / $00FF by name only, FORMAT by address
      only; DIR_RUNNERS credits biosl's rungs (biosl_run.py lists probes/bios/biosl) -- ~30 entries gain biosl-acceptance.
      Three genuine witnesses the old match found only by luck now NAME their entry in code (synchr's `SYNCHR`, biosq's
      `CALLF`, biosregs' `LEFTC`; the bytes unchanged). The page now says **2 NOT MEASURED: CHKRAM and FORMAT** -- the
      honest reading (no gate calls either); both were L1 on spurious witnesses. tests/test_entry_table.py (g).
      subrom-acceptance still backs CALSLT's "vs reference" mechanically; other witnesses are differential, no change.
      ✅ **THE BIOS QUEUE IS EMPTY (2026-11-16).** CHKRAM / FORMAT: Joost 2026-11-17 *"Rule both indirect"* -- entry_table's
      BIOS_RULED (a reset: every gate's boot; FORMAT: the disk ROM's body). Every main BIOS entry is L3+ or ruled.
