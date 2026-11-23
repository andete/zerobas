- [ ] **D-MSX1ON2 — THE MSX1 BIOS CALLS ON THE MSX2 / MSX2+ REFERENCES: SAME CASES, NOT ASSUMED THE SAME ANSWERS**
      🔁 THE RULE IS GENERAL (Joost 2026-11-23): every generation's calls are re-measured on EVERY later one --
      MSX1 on MSX2 / MSX2+ / turbo R, MSX2 on MSX2+ / turbo R, MSX2+ on turbo R. An MSX2 page's MSX2+ row is a
      separate reading (the FS-A1WSX), never inherited from the NMS 8250 / HB-F900 rows.
      🎚️ TIER 1 — Joost 2026-11-23: "we cannot assume that e.g. msx1 bios calls behave exactly the same on an msx2";
      part of D-MSX2SPEC.
      🤖 **AUTONOMOUS** — scratchpad/m1on2_run.py runs every MSX1 spec probe and biosl rung with biosl_run.py
      `--row msx2all` (NMS 8250 / HB-F900 / FS-A1WSX vs C-BIOS's MSX2 builds), one file per probe in
      scratchpad/AE_m1on2/. Then: set each MSX2 `CAP ref` against the VG-8020's committed one; where they differ, the
      MSX1 page grows a per-generation row (a rule that names its generation), and where C-BIOS MSX2 differs from its
      MSX2 reference, that is a C-BIOS finding. First reading (smoke): b2vdp's CAP E037 ref $FF / C-BIOS $00 on all
      three. The BDOS / disk-ROM probes (xb*, xd*, xchoice*) give no reading on C-BIOS's MSX2 builds
      -- expected: no C-BIOS build has a disk ROM yet (Joost 2026-11-23); for those only the reference-vs-VG-8020
      comparison applies.
      FIRST PASS DONE (2026-11-23): 137 probes run, triaged per byte into GEN / CONFIG / TIMING / APPARATUS /
      UNKNOWN -- scratchpad/m1on2-triage-{vdp,gfx,slots,disk}.md (their summaries are the index). NEXT, in order:
      (a) APPARATUS, so every probe gives a reading on all three: ✅ xlin / xlin2a-c DONE 2026-11-23 (`@type-ready`, a
          KEYREADY handshake; VG-8020 captures byte-identical, now gen=0 on all three MSX2s); ✅ xinit3 / xinit4 DONE 2026-11-23 (an H.KEYI guard,
          installed only where EXBRSA != 0; VG-8020 byte-identical bar xinit4's 4 known run-to-run cells) -- and a GEN
          FINDING: RG0SAV $1A hangs the NMS 8250 (IE1 reaches R#0, the line interrupt is never acknowledged; $4A does
          not), C-BIOS MSX2 the same; ✅ xvdpreg DONE 2026-11-23 (R#8-R#23 + copies put back per case, MSX2 only;
          all three references read; C-BIOS's MSX2 JP / MSX2+ builds overrun RAM there, the EU build does not);
          ✅ xsetw DONE 2026-11-23 (@caplen 19; gen=0 on all three); ✅ xcalslt DONE 2026-11-23 (the copy selects RAM's sub-slot,
          the preset is RAM's + 1; VG-8020 and CF-3300 byte-identical; every target now runs on all three, and the
          triage's "interrupts on in the target" (U1) was the copy bug, not the BIOS); xenaslt2 / xrdslt2
          stay CF-3300-only BY DESIGN (fixed IDs $83 / $87; reading 3-1's header is ruled for the CF-3300's ROM only --
          ENASLT / RDSLT on the MSX2s are covered by xenaslt / xrdslt, CONFIG only); ✅ xdsk3 DONE 2026-11-23 (@timeout
          60 emulated s ran out on the NMS 8250 / HB-F900 -- not a hang; 300 now, all three read); disk
          R-BS-SLOT's per-row IY constant. A probe edit changes the MSX1 runs too: re-measure the VG-8020 rows.
      (b) ✅ DONE 2026-11-23: every MSX1 page (docs/bios, docs/bdos, docs/disk) has "On later generations (MSX2,
          MSX2+)" (docs/spec-method.md §2 item 6, §4), its rules evaluated on the three machines' captures. LEFT: b3int's
          50 / 60 Hz blindness has no call page; CALSLT's Open [A] (a sub-slot other than 3-0) is partly measured now.
          WAS: a rule that names its generation, [M] on the three machines,
          MSX2 and MSX2+ separately (e.g. INIT* clear RG1SAV bit 7; SETTXT no longer computes RG3/5/6SAV; WRTPSG
          forces R7 bit 7; the BDOS / disk entries return with interrupts ON on all three MSX2s).
      (c) ✅ DONE 2026-11-23: sent to the C-BIOS session with the c0c0b31 rebase reply (inbox,
          2026-11-23-zerobas-rebased-on-c0c0b31.md). WAS: the C-BIOS MSX2 findings (where it keeps MSX1 behaviour the MSX2 changed, or matches neither) to the
          C-BIOS session -- after (a), so no finding rests on a probe that cannot run there.
      (d) the UNKNOWNs listed in each triage file. ✅ 2026-11-23: OUTDLP's $85 / $FF conversion is the JAPANESE
          machines' (the CF-3300, a Japanese MSX1, converts as the HB-F900), not the MSX2's; WRTPSG's R7 bit 7 is the
          MSX2s' PSG (bits 7 / 6 read 1 / 0 through the ports too -- probes/bios/spec/xpsgr7.asm), R-WP-REG holds.
