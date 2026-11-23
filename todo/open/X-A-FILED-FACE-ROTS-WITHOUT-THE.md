- [ ] 🔴 **A FILED *FACE* ROTS WITHOUT THE ROW CEASING TO DIVERGE, AND NOTHING
      DETECTS THAT.** Found three times on 2026-09-04, each by hand while picking
      the item up:
      • the NAME rows — entry and the corrected comment in `basic/files.asm` both
        said `zb ERR 24`; both read **ERR 2** (noted 2026-09-02, and the entry
        called it "THIRD STALE FILING");
      • `LEN=r` — entry says `zb -> Syntax error`; both sides raise **ERR 5**, so
        the CODE agrees and only the domain differs (D-RECLENDOM);
      • the concatenation entry — its whole subject had been FIXED by D-CATFIX
        three days earlier and the box was never struck (D-CATGATE).
      🎯 **`filed_row_sweep` CANNOT SEE THIS CLASS, AND ITS OWN DESIGN SAYS WHY.**
      It adjudicates each divergent row as *known* / *unfiled* / *no longer
      diverging*. A row that still diverges but now diverges **to a different
      face** is `known`, and reads green. The 2026-09-04 run was **0 UNFILED, 0
      NO-LONGER-DIVERGING** on all 15 probes — and two of the three above were
      live at that moment.
      ⚠️ **THIS IS NOT "add faces to the pin file" WITHOUT A DESIGN.**
      `tools/filed-row-known.txt` is row-labels-only and its loader refuses a
      degenerate parse (`< 5` probes) on purpose; a face column would have to
      survive that refusal, and several probes in the corpus print faces the
      sweep cannot even parse into row names (`playfn` reads *"6 marker(s) in 0
      parsed line(s)"* and works only by substring containment).
      💰 Not priced. The cheap half may be that a face belongs in the PROBE's own
      pin, not in the sweep's — the `basic_probe_nodisk.py` `PINNED` dict already
      does exactly this for 8 rows and goes RED on drift **in either direction**,
      which is the shape this wants.
      🎚️ APPARATUS — filed-face rot
      🤖 AUTONOMOUS — the corpus and the failure mode are both in hand; what is missing is a design, not a decision.
      🟢 **THE DEFERRAL HALF IS DONE (D-DEFERPIN, 2026-09-05), AND TWO MORE
      INSTANCES TURNED UP WHILE DOING IT** — so the class is at **five**, not
      three:
      • `basic_probe_namspc.py`'s three bare-verb deferrals read *"`Missing
        operand` on the CF-3300, `Syntax error` here"* while all three machines
        had come to print `Missing operand` (D-MISSOPMSG, same day). 🔴 **That
        note carried its OWN ⚠️ saying the reason must not go stale, written one
        round earlier. A warning is not a check.**
      • `basic_probe_fldwidth.py`'s `r.len100` said *"`Syntax error` here"*
        against a measured `Illegal function call`. 🔴 **This entry had already
        corrected that face on the `LEN=r` ENTRY a day earlier** — correcting the
        filing does not correct the probe, and nothing connected them.
      ➡️ **A DEFERRAL IS A PIN, NOT A NOTE.** `probe_report.Deferral(reason,
      side=face, ...)` records the faces that make the deferral true and goes RED
      on drift **in either direction**, including a side that stops being
      measured and a side measured but never pinned — the shape this entry itself
      named as the likely cheap half (`basic_probe_nodisk.py`'s `PINNED`).
      **All 10 live deferred rows in the battery are pinned**: `namspc` 2,
      `fldwidth` 2, `nxlist` 3, `screenerr` 3 (counted from the last green
      battery's logs, not from this line — recount before quoting).
      🟢 **AND IT HAS TEETH, MEASURED NOT ASSUMED**: K-DP1 mutated one pinned
      face (`m.blank`'s `zb`) and `namspc-acceptance` went **rc=2** naming exactly
      what moved, with the probe source restored byte-identically afterwards.
      🔒 **`make deferral-pin-check` (7 arms) stops the next deferral being
      added as a bare string again** — a static AST read, so it costs no emulator
      time and cannot be skipped by a row that did not run.
      🔴 **WHAT IS NOT DONE, EXPLICITLY**: the SCORED-row half. A row that still
      diverges but to a different face is still `known` to `filed_row_sweep`, and
      that is the design question this entry opened. Pinning 10 deferrals does
      not touch the 54 pinned divergent rows. **The item stays open for that.**
      💰 **PRICED AT LAST, 2026-09-10 (D-FACEPRICE) — the entry's own "Not
      priced" is now a number.** Counted from
      [`tools/filed-row-known.txt`](../../tools/filed-row-known.txt), excluding the
      declared NO-VERDICT probes:

          probes with SCORED pinned divergent rows        13   (60 rows)
            already carry an exact-value pin
              basic_probe_nodisk       PINNED               8 rows
              asciidigit               via its GATE TWIN
                                       basic_probe_asciidigit.PINNED   2 rows
              (2026-10-05: both gone -- the rows AGREE since D-ASCIINUM)
            NO face pin anywhere      11 probes            50 rows

      🎯 **SO THE REMAINING WORK IS 50 ROWS ACROSS 11 PROBES, AND THE TEMPLATE
      ALREADY EXISTS THREE TIMES** — `basic_probe_nodisk`'s `PINNED`,
      `basic_probe_asciidigit`'s, and D-DEFERPIN's `probe_report.Deferral` for the
      deferral half. It is per-probe mechanical work, not a missing design; the
      design question this entry opened has been answered by those three.
      ⚠️ **AND `asciidigit` IS THE SHAPE TO WATCH**: the pinned probe is the
      SCRATCHPAD one, while the pin that would catch drift lives in its GATE twin.
      Coverage exists, but not at the probe the sweep names — so a count taken off
      the pin file alone reads 2 rows worse than the tree is.
      🟢 **AND THE BACKLOG IS LATENT, NOT BURNING — SPOT-CHECKED 14 OF THE 50
      TODAY, ALL FACES INTACT** (`open2` 1, `deffn_alias` 2, `keystr` 5,
      `keylist` 6; [`.out`](../../scratchpad/open2_recheck.out),
      [`.out`](../../scratchpad/deffnalias_recheck.out),
      [`.out`](../../scratchpad/keystr_recheck.out),
      [`.out`](../../scratchpad/keylist_recheck.out)):
      • `e.same2` — `<File already open>` on the CF-3300, `OK` here: matches
        *"accepted here and refused on the CF-3300"*.
      • `o.alias` 505 vs 503, `o.aliasnest` 909 vs 903, **both controls agreeing**.
      • `keystr` all five: refs carry the default strings, zerobas all-zero —
        *"defaults absent on cold boot"*.
      • `keylist` all six: refs `0 5 0 5 5 0`, zerobas `2` throughout — *"ERR 2 to
        every form while the references accept 1..10 and raise ERR 5 outside"*.
      ⚠️ **THAT IS A 28% SAMPLE AND A NEGATIVE RESULT, NOT A CLEAN BILL.** The
      class is real — this entry records five instances — and 36 rows are still
      unchecked and unpinned. What the sample buys is URGENCY: no face in it has
      rotted, so this is worth doing properly rather than in a hurry.
      ✅ **AND THE FIRST 14 ARE NOW PINNED (D-FACEPIN, 2026-09-10) — the four
      probes whose faces were measured above, so nothing was pinned from memory.**
      `open2_probe` 1 · `deffn_alias_probe` 2 · `keystr_probe` 5 ·
      `keylist_probe` 6. Each carries a `PINNED` dict of exact values and exits
      **2** naming the row when one drifts, the shape `basic_probe_nodisk` and
      D-DEFERPIN already use.
      🎯 **KEYED BY SIDE NAME, NEVER BY COLUMN POSITION.** `sides` is an argv
      option in three of the four, so a positional pin would compare the wrong
      machine and say nothing about it.
      🟢 **AND IT ALSO FIXES THE EXIT-0 HALF FOR THOSE ROWS.** `open2_probe` had
      no exit path at all — it is one of the "prints divergences and exits 0"
      family the sweep flags. A drifted face now reaches an rc the sweep already
      prints.
      🔬 **KNIFE 4/4** ([`scratchpad/facepin_knife.py`](../../scratchpad/facepin_knife.py),
      [`.out`](../../scratchpad/facepin_knife.out)): one pinned face corrupted per
      probe → **rc=2 and the row named**, every time; and each probe RE-RUN after
      restore returns to rc=0, so the red is the pin biting and not the probe
      breaking. A pin that cannot redden reads exactly like a correct one on a
      green run.
      ✅ **BATCH 2 (same day): `dupopen` 6 + `dskibytes` 3 — 23 of 50 pinned.**
      Both RE-MEASURED at pin time rather than pinned from the readings taken
      earlier the same night: `dupopen`'s six all read `<File already open>` vs
      `OK`, `dskibytes`'s three read the zeros and 1s zerobas holds where the
      image has FAT12 bytes. Faces intact in both.
      🎯 **`dskibytes` PINS WHAT THE MACHINE HOLDS, NOT A VERDICT WORD** — zerobas
      has no `DSKI$`, so the window it never fills reads zeros, and `w.half2`'s 1s
      are pre-existing contents rather than a partial transfer. Pinning `has` is
      what would notice `DSKI$` starting to write something.
      🔬 **KNIFE NOW 6/6** ([`.out`](../../scratchpad/facepin_knife.out)), and two
      things in it were wrong first:
      • **It asserted `rc != 0`, which would have passed `dskibytes` for free** —
        that probe ALREADY exits 1 on its own DIFF verdict (3/3 rows differ by
        design), so "non-zero" is its resting state. The arm now requires
        **exactly 2**, and the restore control checks for the ABSENCE of a drift
        report rather than `rc == 0`.
      • **The mutant was derived by a substitution chain** (`'"0'→'"9'` etc.),
        which cannot address `dupopen` at all: it pins `"zb": "OK"` **six times**,
        so no bare literal is unique. Each arm now names its own find/replace.
      ✅ **BATCH 3 (same day): `putdomain` 8 — 31 of 50 pinned, knife 7/7.**
      Re-measured at pin time. The face pinned is **`E L` — the trapped ERR and
      LOF together** — because this probe exists precisely because ERR alone
      cannot separate "did it" from "declined quietly"; pinning only the ERR
      would pin the blind half.
      🎯 **`r.255`'s zb face is pinned as `0 -256`, and that is the FINDING, not
      a typo** — 65280 read back through a signed 16-bit `LOF`. Its knife arm
      mutates it to the plausible CORRECT value (`0 65280`), so the arm also
      demonstrates the pin firing **in the direction that matters: the day the
      defect is fixed**, which is when a stale filing would otherwise go quiet.
      🔴 **AND `reclen`'s FOUR ARE DELIBERATELY NOT PINNED — its face is an
      APPARATUS OUTCOME, not a measurement.** All four read
      `cf3300='OK'  zb='<NO OUTPUT>'`, and this file's own note explains why:
      *"D-PUT3SLOW: all four PASS with the CORRECT answer at a 5 s step; blank
      only at 2.5 s"*. The blank is the STEP, not the machine. Pinning it would
      manufacture a flaky red that goes off whenever the host is busy — worse
      than no pin, and exactly the confusion this entry exists to prevent.
      🎯 **SO THE 50 HAS A CEILING, AND IT IS NOT 50.** A row is face-pinnable
      only when its face is a MEASUREMENT; rows whose face is a timing or
      capture outcome must be excluded and SAID to be excluded, or the next
      person reads the gap as unfinished work
      [[apparatus-is-part-of-the-measurement]].
      ✅ **BATCH 4 (same day): `ngram14` 9 + `bareform` 1 — 41 of 50, knife 9/9.**
      🎯 **`ngram14`'S NINE ARE LAST-DIGIT FLOAT FACES, WHICH IS PRECISELY WHY
      THEY NEED PINNING**: `.78539816339745` against `…46` is ONE character, and
      any check coarser than the literal string calls the row green while the
      mathpack drifts under it. Its knife arm mutates exactly that digit.
      🟢 **AND `bareform`'s `CLOAD` IS HALF-PINNED — the first row where only ONE
      SIDE is a measurement.** Both references read `<none>` because `CLOAD`
      **waits for tape** and the capture window closes on a machine still
      blocked; the probe says so itself, two lines below its table (*"an absence,
      not agreement"*). Pinning `<none>` would assert the HARNESS goes on failing
      to read — a claim about the apparatus, not the machine. The `zb` side IS a
      measurement (`legal` where the references cannot be read at all), so that
      half is pinned and the reference halves are deliberately left out.
      🎯 **THE PER-SIDE PIN FORMAT IS WHAT MAKES THAT POSSIBLE**, and it turns out
      to matter: "is this row pinnable?" is the wrong question — **"which SIDES of
      it are measurements?"** is the right one, and the answer can be "some".
      ✅ **BATCH 5 CLOSES THE SCORED-ROW HALF: 44 PINNED + 6 DECLINED WITH
      REASONS = 50 ACCOUNTED FOR. Knife 10/10.**
      `playfn_fixture`'s five split on the `reclen` criterion, and the split is
      the tree's OWN caveat rather than my judgement:
      • **3 PINNED** — `one voice, no delay`, `voice 2, no delay`,
        `voice 3 only, no delay`. Their faces are `PLAY(n)` **STATE vectors**
        (−1/0 per voice), deterministic, and **byte-identical across the two
        independent runs taken earlier today** before anything was pinned.
      • **2 DECLINED** — the two `width: TIME` rows.
        [`tools/filed-row-known.txt`](../../tools/filed-row-known.txt) already records
        them as *"TIME readings (2 vs 6, 4 vs 14), not PLAY behaviour"* and warns
        that 4-vs-14 sits above the filed interpreter-speed band *"even allowing
        TIME's ±1 quantisation on small integers"*. A face pinned on a quantised
        timing reading fires whenever the quantum lands the other way.
      🎯 **THE CRITERION, STATED ONCE FOR WHOEVER PINS THE NEXT ONE: pin a face
      only where the face is a MEASUREMENT.** A timing reading, a capture
      outcome, or an absence is a property of the APPARATUS, and pinning it
      manufactures a flaky red that teaches people to ignore the gate. Six rows
      failed that test — `reclen`'s four (blank at 2.5 s, correct at 5 s) and
      these two — and every one is declined IN WRITING rather than left as a gap
      the next reader mistakes for unfinished work.
      📏 **FINAL TALLY**: 60 scored pinned rows → 10 already covered
      (`basic_probe_nodisk` 8, `asciidigit` via its gate twin 2) + **44 newly
      face-pinned across 9 probes** + **6 declined with a written reason**.
      🔬 **KNIFE 10/10** ([`scratchpad/facepin_knife.py`](../../scratchpad/facepin_knife.py),
      [`.out`](../../scratchpad/facepin_knife.out)) — one arm per probe, each requiring
      **exactly rc=2** and the row NAMED, each followed by a restore control that
      requires the drift report to be GONE. The design question this entry opened
      on 2026-09-04 is closed.
