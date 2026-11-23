- [ ] **HOW MUCH OF THE 311-BYTE `NO-ORACLE` BUCKET IS A POINTER?** Filed
      2026-08-01 by D-REHOME. `FRETOP` sat in that bucket scored as *"no
      reading"* while all three sides agreed **perfectly** on the movement
      (−4/−20). The sweep now has a `SAME-DELTA` verdict, but it is only applied
      in the re-homing table — **the 3199-byte census still classifies every byte
      absolutely.** 🔴 `NO-ORACLE` is a verdict about the COMPARISON, not about
      the variable, and the bucket is an over-count by an unmeasured amount.
      ⚠️ A byte-wise delta pass needs a rule for what counts as a pointer PAIR;
      naive per-byte deltas on a 16-bit cell will agree by luck on the high byte.
      ✅ **MEASURED 2026-09-05 (D-NOORCNT) — the census now prints the breakdown
      every run, so it cannot rot back into "an unmeasured amount".**
      Of the **311 B**: **26 B in derived 2-byte cells (13 cells)**, 280 B in
      cells of another width, 2 B unnamed.
      🔴 **14 B (7 cells) AGREE ON THE DELTA — an oracle the absolute test threw
      away**: `MEMSIZ`, `STKTOP`, `FRETOP`, `SAVSTK`, `FILTAB`, `NULBUF`,
      `HIMEM`. Identical across all 13 movement states. So the over-count is
      **14 B, ~4.5% of the bucket** — not the whole 311, and now a number.
      12 B (6 cells) disagree on the delta too, so NO-ORACLE stands for those.
      🎯 **THE PAIRING RULE IS THE ENTRY'S OWN WARNING, HONOURED**: a pair is
      never guessed from adjacency — it is a PUBLISHED head whose DERIVED extent
      (distance to the next published symbol) is exactly 2 and BOTH of whose
      bytes are in the bucket. The 280 B in other-width cells are counted and
      LEFT ALONE: their width is unknown, and inventing one is the error the
      entry warned against.
      🔴 **AND THE FIRST RUN OVER-COUNTED, for exactly the reason this sweep
      already guards elsewhere**: it included the BASELINE state, where every
      delta is 0 and `0 == 0`, and reported **13** cells agreeing instead of 7.
      `classify` already refuses to dress up baseline agreement ("a machine that
      never touches a byte agrees with one that does"); the breakdown now skips
      the baseline for the same reason.
      🎚️ BUDGET — NO-ORACLE bucket
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
