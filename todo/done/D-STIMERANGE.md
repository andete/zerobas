- [x] **D-STIMERANGE — BDOS STIME TAKES ANY TIME: A = 0 WHERE THE CF-3300 ANSWERS $FF FOR AN OUT-OF-RANGE ONE**
      🎚️ TIER 6 — every error (a program passing hour 25 / minute 60 / second 60 / hundredths 100; filed 2026-11-17).
      🤖 **AUTONOMOUS** — BDOSXT in bdos-acceptance, its 4 STIME bytes pinned at ours (D-DISKCONTRACT gap 11:
      [`XT_stock.out`](../../scratchpad/XT_stock.out), [`XT_ours.out`](../../scratchpad/XT_ours.out)). stime_body ($4E7E) is `xor a / ld b,h / ld c,l / ret`; the fix checks H < 24,
      L < 60, D < 60, E < 100 -> else A = $FF (~+20 B; the clock itself keeps nothing on either machine). Bytes: the disk
      ROM's hole has 2 B -- after D-DOSDRVB's parts (TIER 3) in the next carve. When it lands, drop the 4 pins.
      ✅ **FIXED 2026-11-26.** Re-measured first ([AE_stime1.out](../../scratchpad/AE_stime1.out)): hour 25 / minute 60 / second 60 already answered $FF --
      D-F37DSETDATE (2026-11-22) had put those checks into stime_body; only hundredths 100 still answered 0. stime_body
      now refuses E > 99 too (+5 B); BDOSXT is a 0-byte diff with all four pins dropped ([AE_stime2.out](../../scratchpad/AE_stime2.out)).
