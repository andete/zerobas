- [ ] **THE DISK ROM ON C-BIOS'S OTHER HOSTS: MSX1 JP / BR / INTERNATIONAL, MSX2 AND MSX2+ -- UNMEASURED (D-DISKMSX2HOST,
      queued 2026-11-27).**
      🎚️ TIER 1 — the disk ROM for C-BIOS: Joost (2026-11-27) wants "a with and without variant of each existing
      cbios"; only C-BIOS MSX1 EU is gated (`make nobasic-acceptance`). Asked whether to measure the rest: "yes".
      🤖 **AUTONOMOUS** — zerobas-side only: machines built from the pinned C-BIOS ROM copies in the openMSX share
      (`tools/install_cbios_msx2.py`), never a C-BIOS build or change (memory no-cbios-work-only-the-inbox).
      WHAT: for each C-BIOS config family, a NOBASIC_DISK machine with build/disk.rom in its free subslot, then the
      no-BASIC MSX-DOS session (disk_probe_dossession) and the reach proof (disk_probe_nobasicreach) on it:
        - MSX1 JP / BR / international: slot 3 plain RAM -> expanded, disk in 3-1 (as EU). Locale differs (JP: INIT32
          at $7D2F, keyboard, date order).
        - MSX2 (x4): 3-0 sub ROM, 3-2 mapper -> disk in 3-1.
        - MSX2+ (x4): 3-0 sub, 3-1 music, 3-2 mapper -> disk in 3-3 (never gated).
      The pin (tools/cbios-nobasic.pin) then covers every ROM those machines use. Findings go to the C-BIOS inbox
      (diskport-02 lists the variants) and, when zerobas's, to items here.
      ACCEPTANCE: each variant boots MSX-DOS 1 to A> and the session reads as on the CF-3300 (or the difference is
      filed and pinned); the reach proof GREEN; the measured variants gated (battery, or daily sweeps if slow).
      📏 **MEASURED 2026-11-27** (scratchpad/msx2host_run.py, [AE_msx2host1.out](../../scratchpad/AE_msx2host1.out)): MSX1 international /
      EU / JP / BR: the session 21/21 and the reach proof GREEN on all four (🔮 "JP diverges": MISS). MSX2 (x4): the
      reach proof GREEN, the session 0/21; MSX2+ (x4): 0/21 and the reach proof an INSTRUMENT FAULT. Traced
      ([AE_msx2host_boottrace.out](../../scratchpad/AE_msx2host_boottrace.out), scratchpad/m2boot_trace.py): on MSX2 the boot path is the MSX1's up to MSX-DOS at
      $0100, then the BIOS's $0000 is reached ~2.4 s later and the machine restarts every ~8.5 s. The same C-BIOS
      MSX2 with the Sony HBD-F1 instead boots MSX-DOS 1.03 -- so the fault is OURS.
      🔴 **ROOT CAUSE (read from our code, confirmed by the fix): the subslot register written without its SLTTBL mirror.** page0_ram_in
      (disk/init.asm) puts page 3's RAM subslot in page 0 by writing $FFFF only. C-BIOS MSX2 then calls its sub ROM
      (3-0, page 0) and restores the subslot from the stale SLTTBL[3] -> page 0 = the sub ROM under MSX-DOS. On every
      MSX1 host the stale value is subslot 0 = the RAM: two rules that coincide on every row the gates had. Also
      hard-coded "RAM = subslot 0, disk ROM = subslot 1": p1_blit_tmpl (`and $F3`: page 1 -> subslot 0 for the
      DSKIO / RDBLK copy into page 1 -- the SUB ROM on MSX2) and wa_seg_*_tmpl (`ld a,$04` / `ld a,$00`; only on the
      $FF-gate CF-3300 host).
      ✅ **FIXED 2026-11-27 -- ONE ROM FOR ALL 12.** (1) sltt_set (disk/init.asm): page0_ram_in / page0_ram_out write
      $FFFF AND SLTTBL[page 3's primary]. (2) The page-1 switches take the HOST's subslots: wa_patch / p1_patch /
      ram_p1bits (disk/kernel.asm, in front of $75A5) patch the installed copies -- $F368 / $F36B's bits from
      HOOK_SLOT and from page 3's RAM subslot, P1_BLIT's flip = ours XOR the RAM's (`xor`, was `and $F3`); br_bdos
      puts back the caller's page-1 subslot exactly (was "RAM again iff the bits were 0"). Every RAM template keeps
      its size: no RAM address moves. MSX2_EU alone after (1): 21/21; after (2) all 12 variants: session 21/21 +
      the disk image SAME, reach proof GREEN ([AE_msx2host2.out](../../scratchpad/AE_msx2host2.out); 🔮 12/12: HIT). Gated: `make nobasic-acceptance`
      (battery: MSX1 EU, MSX2 EU, MSX2+ EU) and `make nobasic-all-acceptance` (daily sweeps: all 12),
      probes/disk/disk_probe_nobasichosts.py.
      Batch checks: knife re-pinned; RAM atlas re-measured (SLTTBL3 gains the disk ROM's write at the DOS boot,
      WA_SEG_SET a new label in the existing block, no cell moved); disk corpus ([AE_m2h_diskcorpus.out](../../scratchpad/AE_m2h_diskcorpus.out)) the same
      as the last batch but f1sp3d-2.dsk BOTH-RUN -> UNSETTLED -- 2 of 2 at the 45 s sample, and BOTH-RUN with the
      SLTTBL write cut ([AE_m2h_f1sp3d.out](../../scratchpad/AE_m2h_f1sp3d.out)); sampled at 10..90 s on both ROMs ([AE_m2h_f1sp3d_times.out](../../scratchpad/AE_m2h_f1sp3d_times.out)) it ALTERNATES on
      both (old: unsettled 10-20 s, runs 30-90; new: runs 10, unsettled 20-45, runs 60-90) -- the game's blank
      loading phases meeting the one sample, as D-DISKROMHOST found for the same disk; it runs on both. At the boot
      code's entry SLTTBL[3] = the live register = $04 on the CF-3300 and on ours ([AE_m2h_slttbl_new.out](../../scratchpad/AE_m2h_slttbl_new.out)).
      ➡️ LEFT: a DOS program that runs in page 1 of the TPA on MSX2 (br_bdos's old restore left the disk ROM there
      after every BDOS call -- the session's programs are small; no gate row reaches $4000-$7FFF of the TPA yet).
