- [ ] 🔴 **`check_todo_citations.py` VERIFIES THAT AN ID MATCHES ITS LINE, NEVER
      THAT THE CITED BLOCK IS THE ONE THE PROSE IS ABOUT — AND ONE CITATION HAD
      BEEN POINTING AT AN UNRELATED ITEM FOR AN UNKNOWN LENGTH OF TIME.** Found
      2026-09-05 by D-EXPBAND, by accident.
      `docs/gapsweep-2026-08-21.md:124` reads **“`LOAD"CAS:"` accepts a tokenised
      tape (`../TODO.md:5345 (T-DB105B)`)”**, and `TODO.md:5345` was  NOT-A-CITATION
      `fp_exp`/`fp_log`'s `$8000` reachability item — a different subject
      entirely. The gate was GREEN on it, correctly by its own rule: the id
      really was the id of the block at that line. The real `LOAD"CAS:"` item is
      at `docs/TODO-done.md:31628 (T-A55F3D)`, now cited. **It surfaced only because closing
      the `$8000` item changed that headline, so the id stopped resolving** — had
      I not touched that line it would still be wrong and still be green.
      🎯 **THE HOLE IS STRUCTURAL, NOT A TYPO**: the id is derived from the
      headline, so a citation whose line and id agree is self-consistent no
      matter which block it names. `--fix` makes it worse in exactly this case —
      it rewrites the LINE from the ID, so a citation pointing at the wrong block
      gets its wrong target mechanically preserved across every future edit.
      🔴 **FOUR INSTANCES, NOT ONE — AND THE FOURTH WAS GREEN.** Having found the
      first by accident I walked the docs that cite items I had touched, and
      every one of the four citations I inspected named the wrong block:
      | doc | says | actually pointed at | state |
      |---|---|---|---|
      | `gapsweep-2026-08-21.md:124` | `LOAD"CAS:"` tokenised tape | the `$8000` reachability item | red (today) |
      | `spec-lean-retire-s3-gates.md:7` | RETIRE THE LEAN 16 KB CART | the DRAW scale-state item | red (today) |
      | `spec-lean-retire-s2-switch.md:7` | RETIRE THE LEAN 16 KB CART | `GFX_OP=1`'s marshalling | red (today) |
      | `spec-lean-retire-s1-explicit-machine.md:7` | RETIRE THE LEAN 16 KB CART | "a wall figure hardcoded inside a GATE" | 🔴 **GREEN** |
      All three lean-retire steps cite the same parent, and the real parent is
      block **T-9C566E** in `docs/TODO-done.md` — a file none of them named.
      (Cited by id, not `file:line`: the checker resolves a citation's path
      relative to the CITING file, so the `TODO-done.md:NNN` spelling that works
      from `docs/` cannot be written from `TODO.md` at the repo root at all.) **S1's was
      GREEN and verified-against-the-block-id at the moment I read it**, which is
      the proof this hole is not hypothetical: the gate's strongest category
      ("verified") contained a citation pointing at an unrelated subject. All
      four are repointed; the count is now 37 verified, 0 red.
      ⚠️ **This is 4 of the ~5 citations I actually inspected, NOT 4 of 37** — I
      looked only where an edit had already made one go red, plus the sibling
      docs beside it. The rate over the whole set is unmeasured, and the
      archive-move shape above (an item cited in `TODO.md` that later moved to
      `TODO-done.md`) predicts more. ~~A cheap first cut: flag any citation whose
      surrounding sentence shares no distinctive token (a backticked identifier,
      a quoted keyword) with the cited block's headline; expect false positives,
      so report ADVISORY rather than red.~~
      🔴 **THAT CHEAP FIRST CUT IS A MEASURED NEGATIVE, 2026-09-05 (D-CITESUBJ).**
      Built and run over the live corpus, after stripping the citation's own
      machinery (the id and the `TODO.md`/`TODO-done.md` spellings are artefacts
      of the citation, not evidence of its subject): comparing the citing
      sentence against the **headline** flags **30 of 46**; against the **whole
      cited block**, **21 of 46**. The four known-bad citations are already
      repointed, so **every one of those is a false positive** — the rule has no
      true positive left to find and a 46% advisory is one nobody reads
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]. Not
      shipped; recorded in the tool so it is not re-derived.
      ✅ **WHAT SHIPPED INSTEAD IS STRUCTURAL AND READS 0 FALSE POSITIVES:
      `subject_conflicts()` in
      [`tools/check_todo_citations.py`](tools/check_todo_citations.py).** THREE
      of the four were the SAME sentence in three sibling docs (`RETIRE THE LEAN
      16 KB CART`) resolving to THREE DIFFERENT blocks — a contradiction inside
      the tree, at most one of which can be right, detectable with no guess about
      meaning. Live reading: **34 distinct subject-bearing citing sentences, 0
      naming more than one block.** RED when it fires, and not mechanically
      fixable: the sentence has to be read.
      🔬 **AND ITS ONLY EVIDENCE THAT IT CAN FIRE IS ITS SELFTEST**, because the
      historical instances are fixed. Three arms reconstruct the shape (two docs
      → different blocks must give 1 conflict; → the same block must give 0), plus
      a distinctive-token arm so generic boilerplate cannot collide. Verified by
      falsification: widening the threshold to `> 99` turns the selftest RED.
      ➡️ **RESIDUAL: the LONE wrong citation is still undetectable.** This catches
      the sibling shape (3 of the 4); `gapsweep-2026-08-21.md:124`, a single
      citation naming a single wrong block, has no sibling to disagree with and
      would still be green. Nothing cheap is known for that one — the semantic
      route above is measured shut.
      🔴 **AND A FIFTH INSTANCE LANDED THE NEXT DAY, THE SAME WAY, IN THE SAME
      FILE (2026-09-06).** `docs/gapsweep-2026-08-21.md` §4 is headed *"A line
      store is bounded by the constant `TXTMAX`, not by HIMEM"* and cited the
      **`GFX_OP=1` marshalling** block. It was **GREEN** — the id really was the
      id of the block at that line — and surfaced only because D-GIRDOM2 closed
      that item, changing its headline so the id stopped resolving. **Exactly the
      lone-citation residual named above, found by exactly the accident that
      found the first four**, which is now five data points for a class no gate
      covers. Repointed to `T-E0B04B`, with the wrong citation quoted in place
      under the checker's own `NOT-A-CITATION` marker.
      ⚠️ ~~**CLOSING AN ITEM IS WHAT SURFACES THESE, and that is worth knowing when
      picking work**: the id is derived from the headline, so a `- [ ]` → `- [x]`
      edit re-keys every inbound citation. Five of five were found that way and
      none by looking.~~ **Five of SEVEN. Two were found by LOOKING the next
      morning, and that changes the conclusion above.**
      🔴 **INSTANCES SIX AND SEVEN, 2026-09-06 (D-CITEHEAD), BOTH IN
      `docs/gapsweep-2026-08-21.md`, BOTH GREEN SINCE 2026-08-21.**
      | § | heading | cited | should be |
      |---|---|---|---|
      | 3 | *SCREEN 3 draws on both references; zerobas raises ERR 5* | the *"rule witnessed only by a DEFERRED error"* item (`FN_FEND`, DEF FN knives) | **`T-6AC87B`** — whose headline is that heading VERBATIM, and which has since **moved to the archive** |
      | 5 | *A stored `DATA` literal charges the string pool 25 B* | the *"an item that states the wall inline goes stale"* item (prose wall figures) | **`T-B22650`** — again the heading verbatim |
      🎯 §3's real target moving to `TODO-done.md` is **the archive-move shape
      this entry predicted would produce more**, now observed rather than
      anticipated.
      🔬 **AND THE SEMANTIC ROUTE IS SHUT AS A *GATE*, NOT AS AN *AUDIT* — the
      sentence above overstated it.** Narrowed from "the citing sentence" to
      "the markdown HEADING above the citation", which in a survey document IS
      the item's name, and gated on the heading being claim-shaped (≥4
      distinctive tokens, so grouping headings like *"Also open, lower value"*
      and structural ones like *"S1 — Make the build…"* are out of scope):
      **41 md citations → 13 no heading, 10 heading too thin, 10 sharing a
      token, 10 FLAGGED of which 2 were REAL.** 20% precision — too noisy to
      collect into `make gates`, where a red that is wrong four times in five
      teaches people to ignore reds, and productive as a one-off sweep.
      [`scratchpad/citehead_audit.py`](scratchpad/citehead_audit.py) ships as an
      AUDIT with `rc 0` on purpose. Its eight remaining flags are all one shape:
      a document's own title or `§0` heading, which names the DOC and not the
      cited item. **Not tuned away — that would be fitting a rule to two data
      points.**
      🟢 **THE LONE-CITATION RESIDUAL IS NO LONGER UNCOVERED, 2026-09-06
      (D-CITENAME)** — [`scratchpad/citename_audit.py`](scratchpad/citename_audit.py).
      🎯 **AND THE SIGNAL WAS ALREADY IN THE RECORD, MIS-STATED.** Instances six
      and seven are written up above as headings that *disagree* with the cited
      block — a similarity, which is what made the semantic route look like the
      only one and it measured shut. Read them again and both carried something
      stronger and POSITIVE: the heading **IS** another block's headline,
      verbatim (`T-6AC87B`, `T-B22650`). That is an IDENTIFICATION, needs no
      threshold, and is precise exactly where token overlap is broad. Absence of
      a match says nothing, so the two rules are complements, not rivals.
      🔬 **FALSIFIED THREE WAYS, each restoring byte-identically.** A planted
      LONE mis-aim (§4 repointed at `T-B22650`) leaves
      `check_todo_citations.py` at **rc 0** and reads **rc 1** here — the
      residual class reproduced, and the existing gate demonstrated blind to it
      on the same bytes. A planted **see-also** (correct citation + one to
      another block) is ABSORBED, no flag: the unit is the HEADING, not the
      citation, and a group is clean as soon as any member names the identified
      block. Scored per citation that see-also would be a false positive with no
      defence. Plus `--selftest`, 8 arms.
      🔴 **AND IT READ A CLEAN 0 TWICE BEFORE IT READ ANYTHING** — once because
      `norm` kept sentence-final periods (`himem.` != `himem`), once because the
      section number sat at token 0 and defeated the prefix match. Same symptom,
      two causes, and **both were caught only because the readout also prints
      the POSITIVE bucket**: "0 flags" beside "0 headings name the block they
      cite" is not clean, it is blind
      [[readout-blind-to-its-own-subject]]. Live now: 41 citations → 21 name no
      block, 13 no heading in scope, 5 too thin, **2 positive controls**, 0 flags.
      ⚠️ **NOT COLLECTED INTO `make gates`, AND NOT FOR `citehead_audit`'s
      REASON.** That one is 20% precise; this reads 0 false positives with its
      only known FP shape designed out. The reason is the **DENOMINATOR — 2 of
      41 citations are in scope**, so as a gate it is 39/41 vacuous, and a green
      covering two rows is the shape this project keeps catching itself
      trusting. Recorded so the next reader does not re-derive the precision
      question when the real objection is coverage.
      💰 Zero ROM bytes; a tools-only change.
      🎚️ APPARATUS — citation tooling
      🤖 AUTONOMOUS — a gate settles it; finishable unattended (no his-decision signal found).
