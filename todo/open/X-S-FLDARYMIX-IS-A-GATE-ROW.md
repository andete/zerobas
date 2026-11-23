- [ ] ⚠️ **`s.fldarymix` IS A GATE ROW NO KNIFE CAN REDDEN, and that is recorded
      rather than fixed** (D-FLDARY, spec §10.6). A scalar field and an
      array-element field coexisting in one `FIELD` is the row that makes §4.2's
      disjoint-key-space argument a measurement — but **no reachable program can
      collide the two spaces** (a scalar `k0` is an upcased letter `$41..$5A`; an
      element `k0` is `>= $80`), so K-FA1 moved `s.fldary2` and left this one
      green. Its falsifier is the assembly-time **assert** (K-FA7, which does
      refuse the build), not a cut. Anyone re-reading the knife table should not
      "fix" the row or the cut — the claim is structural
      ([[rule-gated-structurally-has-no-knife]]).
      ✅ **VERIFIED 2026-09-05 — the note is right, and every part of it was RUN
      rather than re-read.** A filed claim is worth nothing until someone
      executes it, and all three parts of this one execute cheaply:
      • **K-FA7 is not vacuous**: loosened from `> $7FFF` to `> $0100` the build
      is REFUSED (rc 2) and the log names
      `FLD_ELEMENT_KEY_BIT15_NOT_FREE__ARRAY_REGION_MAY_EXCEED_…`.
      `basic/field.asm` restored byte-identically after.
      • **The two key spaces are disjoint by construction**, read at the sites:
      `basic/field.asm:245` does `set 7,h` on the ARYTAB-relative offset, so an
      element `k0` is `>= $80`; a scalar's `k0` is the UPCASED FIRST CHARACTER of
      a name whose `is_letter` the caller has already checked, so `$41..$5A`.
      • **And the assert guards exactly the right thing**: `set 7,h` is only a
      valid tag while the raw offset cannot already carry bit 15, which is what
      `(TXTMAX - TXTBASE) > $7FFF` refuses. The looser `offset>>8 <= $3A < $41`
      argument in the comment is the FALLBACK (disjoint even without the tag),
      needing `< $4100` — a different and weaker bound, correctly described as
      the 1.1x margin the two bytes widen.
      🟢 It is also now inside a swept denominator: `make build-assert-check`
      (added 2026-09-05) classifies it as one of the 18 BUDGET asserts, so it can
      no longer be the kind of guard nobody has enumerated.
      ⚠️ **STAYS OPEN ONLY AS A NOTE-TO-READERS**, which is what it was filed as:
      do not "fix" `s.fldarymix` or K-FA1.
      🔁 STANDING — a NOTE TO READERS, not pickable work. Every part of it
      was RUN and verified on 2026-09-05; what keeps it open is the instruction
      *do not "fix" `s.fldarymix` or K-FA1*, which only helps while it is
      visible. It sat in the 🤖 queue with nothing in it to do.
      🎚️ APPARATUS — unknifeable row
