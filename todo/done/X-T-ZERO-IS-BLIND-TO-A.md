- [x] 🔴 **`t.zero` IS BLIND TO A CUT THAT ALSO DISABLES ITS SEED, AND THE PROBE
      ✅ **CLOSED 2026-09-05.** Re-verified after the fix: `make locarg-acceptance ONLY=t.zero` reads ` 0  0  0 ` on all three and the row is armed by K-LA5, the knife that found the blindness.
      CLAIMS OTHERWISE.** Filed 2026-08-09 by D-LOCARG
      ([`docs/spec-basic-locarg.md`](../../docs/spec-basic-locarg.md) §8.3), found by
      knife K-LA5. Every `t.*` program in `basic_probe_locarg.py` opens with
      `CLS:LOCATE 7,4` so that "the cursor did not move" reads ` 4  7 ` and is
      distinguishable from the CLS home position ` 0  0 ` — the probe's `SEED`
      comment says so. That holds for every row **except the one whose target IS
      home**: `t.zero` (`LOCATE 0,0`) reads ` 0  0  0 ` whether both `LOCATE`s
      applied or neither did. Harmless in the shipped tree (where the seed
      applies) and **not** a reason to change the row — `LOCATE 0` being a VALUE
      and not an omission is what it is for. Recorded because the comment
      currently over-claims, and because the same shape will recur in any probe
      that seeds a cell it also tests.
      ✅ **FIXED 2026-09-05 (D-ZEROSEED) — the exception is REMOVED, not
      narrowed, and the row keeps everything it had.**
      🎯 **THE ANSWER IS THE ENTRY'S OWN LAST SENTENCE**: a probe that SEEDS a
      cell with the mechanism it also TESTS has no reading for "the mechanism is
      gone". So `t.zero` is seeded by something else — `CLS:PRINT"       ";`
      leaves the cursor at column 7 by a route no `LOCATE` cut touches.
      | | reading |
      |---|---|
      | seed alone | ` 0  0  7 ` |
      | seed + `LOCATE 0,0` | ` 0  0  0 ` |
      Both measured on all three sides. **The row's subject and its PASS reading
      are unchanged** (` 0  0  0 `, as before), so nothing the entry wanted to
      protect is lost — `LOCATE 0` is still a VALUE and not an omission.
      🔬 **ARMED WITH K-LA5 ITSELF**, the knife that found the blindness:
      `loc_next`'s `scf` → `nop`, so every accept reads as OMITTED. `t.zero` now
      reads **` 0  0  7 ` on zerobas against ` 0  0  0 ` on both references — a
      DIFF**, where before the reseed it read ` 0  0  0 ` on all three and could
      not fail. `basic/missing.asm` restored byte-identically.
      🟢 The plant used `knife_guard.cut()` (D-CUTSCOPE, the same day), which
      refuses unless the anchor is unique — its first real use outside a
      retrofit.
      ⚠️ **Only `t.zero` is reseeded.** It is the sole row whose target IS the
      seed-free home position; changing `SEED` globally would shift every other
      row's recorded "did not move" reading from ` 4  7 ` to ` 0  7 ` for no
      gain. The probe's comment now records the technique rather than the
      exception.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
