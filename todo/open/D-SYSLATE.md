- [ ] 🔴 **DATA DISK AT POWER-ON, MSX-DOS DISK INSERTED LATER: `CALL SYSTEM` RESTARTS
      DISK BASIC ON THE CF-3300 (banner, 23430 bytes free) AND IS `Illegal function
      call` HERE (D-SYSLATE, found 2026-10-09 by D-CALLSYSTEM).**
      🎚️ TIER 6 — `CALL SYSTEM` after a disk swap
      🤖 **AUTONOMOUS** — the reference settles it.
      [`callsystem_swap.out`](scratchpad/callsystem_swap.out) `late` (CF-3300),
      [`callsystem_swap_zb.out`](scratchpad/callsystem_swap_zb.out) `late`
      (zerobas). The CF-3300's mark is not `&HF340`
      ([`callsystem_peek.out`](scratchpad/callsystem_peek.out)); find its rule
      (work-area cells after each boot) before changing ours.
      📏 **RE-MEASURED 2026-11-07** ([`syslate_cf.out`](scratchpad/syslate_cf.out); the 10-09 dump of this row had caught
      the CF-3300 mid-restart and decoded as garbage): after `CALL SYSTEM` the CF-3300 is at
      a COLD Disk BASIC -- `MSX BASIC version 1.0` banner, 23430 Bytes free, `Disk BASIC
      version 1.0`, SCREEN 1 -- and does NOT load MSX-DOS, though the disk in the drive now
      holds it. With D-F346's rows ($F346 = 0 after a data-disk boot; a data disk still in
      the drive is Illegal function call) the reference's rule reads: $F346 = 0 -> the disk
      in the drive is tried; not bootable -> 5, bootable -> a cold Disk BASIC restart (no
      DOS). zerobas answers 5 for both. ➡️ next: a "cold Disk BASIC restart, no DOS" path
      from hk_system (disk/kernel.asm) when $F346 = 0 and sector 0 is bootable -- find which
      of our boot entries (basent_body's 'B','D' restart? INIT with the DOS try off?) gives
      the banner without the hand-off, and gate it on callsystem-acceptance.
