- [ ] 💰 **A 4 B DUP-SPAN THE D-ONLIST FIX CREATED, AND ITS OWN KNIFE FOUND
      IT.** Filed 2026-08-26. `esn_notlineno`'s discriminator
      (`dec de / ld a,d / or e / jr …`) is **byte-identical to `esn_p1`'s own
      countdown test** four instructions above it — the K-OL2 anchor guard
      reported *"anchor appears 2 times"* and that is what a duplicate span
      looks like from the outside.
      🔴 **RUN, NOT ASSUMED: `tools/dupspan_indep.py` DOES NOT SEE IT** —
      `scratchpad/onlist_dupspan.out`, zero mentions of `esn_p1` or
      `esn_notlineno` in a report that lists 169 nominal bytes. The reason is
      structural: the two spans end in DIFFERENT jumps (`jr z,esn_found` vs
      `jr nz,esn_nocf`), so the identical part is a 4-instruction **PREFIX**,
      and the tool's model is spans-with-terminators. That is a hole in the
      model, not a near miss —
      [[dupspan-slice]] already records that a span can be byte-identical
      without being ENTERED the same way; this is the mirror, byte-identical
      without EXITING the same way. **The tooling question is worth more than
      the 4 bytes.**
      ⚠️ Unpriced, and probably not worth taking alone: folding it needs a
      shared entry with the exit selected somehow, which is likely to cost more
      than it saves. Filed for the SWEEP, not for the carve.
      🟢 **THE SWEEP IS BUILT, 2026-09-09 (D-NGRAMCARVE,
      [](../../scratchpad/pair_carve_scout.py),
      [](../../scratchpad/ngram_carve.out)) — AND THIS ITEM WAS RIGHT THAT THE
      TOOLING QUESTION WAS WORTH MORE THAN THE FOUR BYTES.** The pair scout was
      2-instruction-only, so a THREE-instruction shared run was invisible to it
      exactly as it was to , for a different reason. Widened to
      runs of 2..5: **68 runs at 8+ sites**, top row

          net sites  B  k  run
           31     8  8  3  call ev_sp | cp ')' | jp nz,ev_f_empty
           29    12  6  2  ld hl,arga | call widen_rhs_operand
           20     9  6  3  inc ix | call ev_sp | cp '('

      **Verified, not taken on the tool's word**: the top run's 8 sites were
      re-counted by an independent grep (7 in , 1 in ).
      🎯 **AND THE PAIR SWEEP'S OWN OUTPUT WAS THE ARGUMENT FOR WIDENING.** Every
      row it printed said *"cannot win: a 3 B call is not cheaper"* — which is not
      a fact about the tree, it is a fact about the WINDOW. A 3 B call can never
      beat a 2 B pair; it beats an 8 B run easily.
      🔴 **A SECOND FAULT, AND IT WAS BURYING WINNERS: THE RANKING KEY.** The old
      sweep sorted by SITE COUNT and printed the top 20, so  — 12 sites, 6 B, **net +29** — sat below every 26-to-55
      site 2-byte pair that could not pay for itself, and was never shown. Ranked
      by NET now [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      ⚠️ **TWO ARMS THE PAIR VERSION NEVER HAD**, because a widened window widens
      the hazards: a run containing a / is REFUSED (the displacement
      moves, the identical hazard  decides as its question 2),
      and runs OVERLAP by construction — a 5-gram contains two 4-grams — so the
      savings are not additive and the tool says so: take the top row, re-run.
      💰 **AND IT FUNDS THE QUEUE.** 31 B from one run is more than the pending
       ASCII-digit arm needs; a carve is how that spend gets afforded rather
      than argued for.
      🎚️ BUDGET — 4 B dup-span
      🤖 AUTONOMOUS — the sweep is the deliverable and the 4 B this item filed
      stays not-worth-taking. The candidates it found are the follow-on.
