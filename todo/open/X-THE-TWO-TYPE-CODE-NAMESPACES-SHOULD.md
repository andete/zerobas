- [ ] **THE TWO TYPE-CODE NAMESPACES SHOULD PROBABLY BECOME ONE.** Filed
      2026-08-01 by D-DEFSTR. The references use `3` for **both** the DEFtbl code
      and the variable-chain type byte, which makes `elsize == type` an identity
      and [`elsize_from_type`](sub/arrays.asm:943) — plus ~7 call sites —
      deletable. zerobas uses `1` in the chain with a `1 → 3` map.
      ⚠️ The chain's stored type byte is **RAM-observable**, so this needs its own
      oracle-lock on that byte before anything moves; D-REHOME measured only that
      the string scalar entry's SIZE agrees (+6 B, `ARYTAB $8003→$8009`), never
      its contents. ⚠️ Also note the entry field ORDER may differ from the
      reference's — unmeasured. A separate slice, not a ride-along.
      🎚️ OTHER — architecture
      🔁 **RULED (Joost, 2026-09-10): stays as classed** — not before TIERS 1–4 unless it
      blocks a keyword tier; still his call when it is picked.
      🤖 AUTONOMOUS — 🏗️ **RULED BY JOOST 2026-10-27**: *"Merge to reference codes"* (asked as the namespace item above; the scouting and pricing come first, then the merge).
