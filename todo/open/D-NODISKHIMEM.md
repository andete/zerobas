- [ ] **BOOTED WITH NO DISK IN THE DRIVE, ZEROBAS GIVES BASIC 116 B LESS THAN THE CF-3300 (D-NODISKHIMEM, found 2026-11-26 by the
      cartridge survey).**
      🎚️ TIER 4 — RAM usage: FRE at the prompt of a disk machine started without a disk.
      🤖 **AUTONOMOUS** — measured; the guard gate covers the data-disk and DOS boots, not this one.
      MEASURED (scratchpad/cartsurvey.py, [AE_cartsurvey2.out](../../scratchpad/AE_cartsurvey2.out), sampled at 25 and 40 s): with NO disk the CF-3300 reads
      HIMEM $DF93, MEMSIZ $DD7B, STKTOP $DCB3 at the prompt; zerobas $DE77 / $DC5F / $DB97 -- the CF-3300 does not take
      the last piece ($DF93 -> $DE77, which it takes when Disk BASIC starts with a disk -- D-DISKROMHOST step 4) when
      the drive is empty; zerobas always does. With a data disk both read $DE77 (diskguard-acceptance's rows).
      NEXT: measure the rule -- what decides it on the CF-3300 (a disk at boot? at the first disk access? does the
      claim come later, at the first FILES / LOAD?) -- by sampling HIMEM after each step; then make zerobas follow.
