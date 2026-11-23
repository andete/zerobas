- [ ] 🎚️ **~~TIER 5~~ TIER 4 (SWAPPED 2026-09-24) IS NOW "MATCHES THE REFERENCE'S
      RAM USAGE" — THE RUNG, AND WHAT CAN AND CANNOT BE IN IT (D-TIER5RAM,
      2026-09-22)**
      🎚️ TIER 4 — the rung's own definition; it is the bar every other item at
      this tier is measured against.
      🏗️ **SWAPPED WITH SPEED BY JOOST, 2026-09-24 (D-TIERSWAP): RAM USAGE IS
      TIER 4, ON-PAR SPEED IS TIER 5.** He asked whether the two should swap;
      the case put to him was (1) a RAM difference can stop a program RUNNING
      (a listing that fits on the reference is `Out of memory` here, or a
      `CLEAR`/`BLOAD`/`POKE` into a cell we use differently corrupts us) where a
      speed difference mostly makes it slower; (2) with T4 ruled *"track the
      ratio, set no bar yet"* the speed tier cannot CLOSE, and under
      "lowest tier first" an unclosable tier would hold the RAM tier back
      indefinitely. He chose the swap. **Prose below dated 2026-09-22/23 says
      "TIER 5" for this rung — that is the numbering of its date.**
      🏗️ **WHAT THE RUNG SECURES — RULED BY JOOST, 2026-09-24, ALL THREE:**
      asked which of three goals *"matches the reference's RAM usage"* means,
      since they can pull against each other, he chose every one:
      | goal | what it secures | measured by |
      |---|---|---|
      | **(a) same free memory** | `FRE(0)`/`FRE("")` and what `CLEAR` leaves match, so a program that fits on the reference fits here | the OBSERVABLE half |
      | **(b) same addresses** | work-area cells, undocumented ones included, live where the reference keeps them, so `PEEK`/`POKE`/`BLOAD` programs that touch them behave the same | the FOOTPRINT half |
      | **(c) same economy** | zerobas writes no more cells than the reference for the same operation — his *"very economical"* hunch, which stays a prediction to SCORE | the FOOTPRINT half |
      🎯 **AND THE TARGET WHEN THE REFERENCES DIVERGE IS THE VG-8020** — his
      words, *"if the references diverge, prefer the vg8020"*, the same rule
      as style splits [[oracle-split-prefer-vg8020]]. Cells that exist only
      with a disk ROM, which the VG-8020 does not have, take the CF-3300.
      This answers the *"no single referent"* objection below: "exactly" is
      still not the bar, but there IS now one machine to match.
      ⚠️ **WHERE (a) AND (b) CONFLICT** — matching an address can cost free
      memory, or the reverse — **that conflict comes back to Joost**, like
      every adjustment this rung proposes.
      🏗️ **RULED BY JOOST, 2026-09-22.** He proposed a tier *"matches the RAM
      usage of the reference exactly"*, then: ***"it would make more sense to
      make it tier 5 and bump current tier 5 to tier 6"***. Done — 13 `🎚️`
      markers moved, `tier_table.py` has six rungs, and **TIER 6 is now
      "handles every error situation correctly"**. He placed RAM fidelity ABOVE
      exhaustive error handling deliberately.
      ❌ **"EXACTLY" IS NOT THE BAR, AND HE AGREED — THE REFERENCES DISAGREE WITH
      EACH OTHER.** Measured in this tree: the CF-3300 and the Philips NMS 1200
      differ by **+2** in the file-buffer pointer (`expansion-protocol.md`
      §6.6ae), and the VG-8020 and CF-3300 have different stack tops (`$F09E`
      vs `$DB95`, the `VARPTR(#n)` item). *"The reference's RAM usage"* has no
      single referent to match, so a bar of *exact* equality is not well formed.
      ✅ **HIS ADDITION, AND IT WIDENS THE RUNG BEYOND WHAT I PROPOSED:** *"I do
      think we can also see what undocumented region gets used and should also
      try to match that."* So the rung is **not** limited to the documented work
      area — which cells the reference touches in its OWN workspace is in scope
      too, as a target to match where we reasonably can.
      🔴 **CLEAN ROOM, AND THIS IS THE LINE THAT MAKES THE WIDENING LEGAL.**
      Work-area RAM **addresses and CONTENTS are readable** (`expansion-protocol.md`
      §7), and that covers undocumented cells just as much as documented ones —
      *observing which addresses get written is not decoding anything*. What
      stays forbidden is §8.5: **the BYTES of the reference's RAM-RESIDENT CODE**.
      A written cell inside one of those five clusters is therefore reported as
      *belonging to a cluster*, never decoded. ROM bytes remain out entirely.
      ➡️ **THE BAR, IN TWO HALVES, BECAUSE THEY HAVE DIFFERENT EVIDENCE:**
      **(i) OBSERVABLE** — what a BASIC program can see: `FRE(0)`, `FRE("")`,
      `VARPTR` deltas, `PEEK` of documented cells, what `CLEAR n` leaves. These
      are behavioural and belong to the keyword that exposes them.
      **(ii) FOOTPRINT** — which cells get written for a given operation, in both
      workspaces. Measured by the watchpoint method, not by reading code.
      ⚠️ **AND A CAUTION ABOUT PLACEMENT THAT THE RENUMBER DOES NOT REMOVE:** an
      observable RAM divergence can break an ORDINARY program — `PEEK(VARPTR(A$))`
      is not exotic in MSX-land. When one does, it deserves the tier its IMPACT
      earns, which may be TIER 1, not this rung. The rung is where the SYSTEMATIC
      comparison lives, not a place to park breakage.
      🤖 **AUTONOMOUS** — the MEASUREMENT is permitted and needs no ruling. ⚠️ Any
      ADJUSTMENT it proposes comes back to Joost: moving a cell to match the
      reference changes an address this tree has already made decisions about
      (`docs/sysvar-rehoming-decisions.md`).
