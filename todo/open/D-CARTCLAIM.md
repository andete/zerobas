- [ ] 🐛 **A CARTRIDGE'S HIMEM CLAIM IS LOST AT BOOT: ZEROBAS BASIC PUTS HIMEM BACK TO $F380 (D-CARTCLAIM, found 2026-11-25
      by D-DISKROMHOST step 4(d)'s guard probe).**
      🎚️ TIER 1 — happy path: any cartridge with a work area of its own under HIMEM (one claim, a few bytes) has that RAM
      handed back to BASIC, and the string space sits directly under HIMEM.
      MEASURED (probes/disk/disk_probe_guard.py, scratchpad/AE_room_guard.out): a test cartridge (probes/disk/claimer.asm)
      whose INIT lowers HIMEM by 16, scanned before the disk ROM. The CF-3300 keeps the claim (its final HIMEM $DE57, 32 B
      under the plain $DE77). zerobas: the disk ROM's guard sees the lowered HIMEM and declines (as designed), and then
      the prompt reads HIMEM **$F380** -- the cartridge's 16 B given back.
      CAUSE (by reading): basic/interp.asm's boot keeps HIMEM only when its HIGH BYTE is under high TXTMAX (a disk ROM's
      claim, $DCxx..); any smaller claim is overwritten with the ceiling. Fix direction: keep any HIMEM below $F380
      (the C-BIOS value) and take the text ceiling as min(HIMEM, the chosen ceiling) -- check TXTCEIL's two-way choice
      and the diskless floor (D-RAMCEIL) before changing the test.
      NOT MEASURED: the VG-8020 with the claimer (no disk ROM in the way: expected $F370).
      🤖 **AUTONOMOUS** — the probe exists (diskguard-acceptance's claimer); but Joost's focus (2026-11-25) makes it a
      BASIC item: it waits behind the disk ROM's readiness for C-BIOS.
