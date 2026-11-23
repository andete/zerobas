- [ ] 📊 **THE CORRECTNESS SCOREBOARD — WHAT "FULL CORRECTNESS" ACTUALLY
      REQUIRES, 2026-09-02.** Built the moment Joost's sequencing (below) made
      "reach full correctness" the goal, because the file had no map of it.
      🔴 **54 PINNED DIVERGENT ROWS IS NOT 54 DEFECTS**, and reading it that way
      would send the next slice at the wrong things. Classified from
      `tools/filed-row-known.txt`, every row owned by a filed item:

          ACCEPTED DEVIATION, signed off — not defects               9
            ngram14  9  the §12.9-adjudicated negative-EXP carve-out
          DECLINED, priced and refused                               5
            keystr   5  NOT-THIS-ONE `KEY n,"str"` (~160 B)
          APPARATUS, not BASIC behaviour                             9
            ramfree  9  echo-fence readout rows; the entry says so
          SPEED, not correctness (reclassified today)                4
            reclen   4  D-PUT3SLOW: all four PASS with the CORRECT
                        answer at a 5 s step; blank only at 2.5 s
          ---------------------------------------------------------------
          REAL OPEN CORRECTNESS DEBT                                16
          ✅ ALL SIX CLUSTERS RE-RUN 2026-09-02 — EVERY PIN ACCURATE.

          🤖 AUTONOMOUS, BUT BEHIND A DESIGN STEP                    6
            ntwall       6  PAINT: a borderless wall is eaten
                            19 rows / 6 DIFF. "No row yet separates the
                            candidate rules", and the fix touches
                            gfx_plot_cur, shared with PSET/LINE/CIRCLE/
                            DRAW — all agreeing today and required to.

          🙋 BLOCKED ON JOOST                                        7
            deffn_alias  2  two formals of one call alias. TWO PRICED
                            OPTIONS, and one is FREE: fix top-level only
                            for **−8 B** (closes 1 of 2), or grow the
                            shadow area **+99 B RAM** (closes both).
            trapsvc      2  trap handler w/o RETURN; six-event cap.
                            Priced and DECLINED — charter/scope.
            playfn       2  PLAY(n) start-up transient. Measured in full
                            2026-09-02 (D-PLAYWIN): the window closes
                            within ONE STATEMENT and BOTH machines have
                            one, of different shape. The measurement
                            argues for declining.
            open2        1  same file on two channels. **+165 B RAM.**

      🎯 **SO THE AUTONOMOUS CORRECTNESS QUEUE IS EMPTY.** Everything left is
      either waiting on a decision that is Joost's (7 rows) or behind a design
      question the owning item states it cannot yet answer (6 rows). Nothing here
      is blocked on effort.
      🔴 **AND `ngram13` LEFT THE BOARD ENTIRELY (16 → 13).** Its 3 rows are
      NO-ORACLE, not divergences: a truncated store's last line has no `$00`
      terminator, so relink's scan stops wherever RAM holds one, and the machines
      reach those rows over different RAM history. `10 POKE` vs `10` is **the same
      store rendered past its own end** — D-TRUNCLOAD proved that with a PEEK
      instrument and closed the item at 18/18. `ngram13_probe` is the OLDER probe
      and never got the classification, so it kept reporting history as
      divergence. Now marked; it reads 6 scored / 6 agree / 3 NO-ORACLE.
      **That is the third time today a NO-ORACLE classification decided whether a
      row was debt at all.** [[no-oracle-is-about-the-comparison]]

      🎯 **SO THE CORRECTNESS QUEUE IS 16 ROWS, NOT 54** — and one of those is
      already 🙋 on a spend. That is a finishable number, which is the point of
      writing it down.
      🔴 **THE FIRST VERSION OF THIS BOARD SAID 17, AND IT WAS WRONG WITHIN THE
      HOUR.** `reqcomma`'s pinned `g.field` reads **10 on both machines** (0/12
      DIFF) — its item shipped 2026-09-01 and the row that still diverges is
      `e.val`, a different, structural 🙋. `oomtail`'s two are stale the same way
      (0/3 DIFF). **A scoreboard built from pins inherits every stale pin**, so
      each line was re-run rather than trusted; `ngram13` survived that and
      `reqcomma`/`oomtail` did not.
      🎯 **AND THE CAUSE IS STRUCTURAL, WHICH IS WHY IT KEEPS HAPPENING.**
      `filed_row_sweep.py` validates the probes cited by OPEN items. When an item
      CLOSES its probe leaves that corpus and **its pin becomes unreachable by
      the one instrument that would notice it going stale.** Five stale pins in
      one day, and the last two were invisible by construction. New
      `--check-orphans` reports any pin whose probe no OPEN item cites; it found
      both within a minute of existing. **Run it whenever an item closes.**
      ⚠️ **THIS COUNTS ONLY WHAT IS PINNED.** It is the set of divergences some
      filed item OWNS; it is NOT a claim that the tree has no others. The
      denominators that would say so are `kwsweep` (keywords), `sysvarsweep`
      (sysvar cells) and the NO-ORACLE buckets — **and the last of those moved
      TWICE on 2026-09-02**, when a third reference dissolved `LSET`/`RSET` and
      `CVI` from unscorable to scored-and-agreeing. A row parked NO-ORACLE is
      unmeasured, not clean. [[no-oracle-is-about-the-comparison]]
      ✅ **EVERY LINE RE-RUN, NOT TRUSTED (2026-09-02).** `ntwall` 19 rows / 6
      DIFF — exactly the pinned six (`wall.row solid.row h2 h4 hp3 vp.solid`),
      pin ACCURATE. `ngram13` 3 of 9, pin ACCURATE. `reqcomma` 0/12 and `oomtail`
      0/3, pins REMOVED. Four probes re-run; two pins died.
      🔴 **A SIXTH STALE PIN, AND `--check-orphans` IS WHAT FOUND IT (2026-09-08).**
      Run on closing the do-nothing-keyword item — which is exactly when this
      section says to run it — it reported one orphan, `casfch_probe`. Re-measured
      by hand with `--input-only`
      ([`scratchpad/casfch_orphan_recheck.out`](../../scratchpad/casfch_orphan_recheck.out)):
      the whole CAS-input set reads **SAME**, `i.inp` 0/0 and `i.byte` 72/72, where
      the pin said `INPUT$` on a `CAS:` channel opened FOR INPUT *"reads on the
      reference and raises ERR 55 here"*. The divergence was fixed and **the pin
      outlived the fix**. Retired from `tools/filed-row-known.txt`; 27 pins → 26,
      and the orphan check now reads clean.
      🔴 **AND MY FIRST WORDING OF THIS NOTE WAS WRONG — *"two of the 16 rows were
      this probe's"*. THEY WERE NOT.** The 16 are enumerated right above:
      `ntwall` 6 + `deffn_alias` 2 + `trapsvc` 2 + `playfn` 2 + `open2` 1 +
      `ngram13` 3. `casfch` is in none of them, so retiring its pin leaves the
      correctness queue exactly where it was and moves only the 54-row pinned
      total. I wrote the sentence from "a pin died, the board counts pins" without
      reading the board's own enumeration four lines up — a relationship asserted,
      not checked [[a-justification-parenthesis-is-an-unrun-claim]].
      🎯 **THE POINT SURVIVES THE CORRECTION, WHICH IS WHY IT IS WORTH KEEPING.**
      A board built from pins inherits every stale pin, this block says so three
      times in its own text, and a sixth pin has now died since the last re-run —
      so **re-derive the number, do not decrement it**, in either direction
      [[a-ranked-candidate-rots-like-a-wall]].
      🔴 **A SEVENTH STALE PIN, 2026-09-09 — AND THIS ONE I ORPHANED MYSELF,
      THE SAME NIGHT I FILED IT.** `partial_probe`'s four rows (`col.fgok`
      `col.bgok` `col.tail` `col.type`) were pinned by `ce0adbcd`, a
      FILING-ONLY commit whose own subject line is *"the fix I built did not
      run"* and whose reason for filing was a PRICE: *"3 B over the page-1
      wall"*. The carve landed hours later and `ecf0c859` shipped the shadow
      (`clr_prep` / `clr_commit`) with *"4 DIFF -> 0"* in its subject — and
      nothing came back to the pin file. Re-measured from a clean tree
      ([`scratchpad/partial_pincheck.out`](../../scratchpad/partial_pincheck.out)):
      **12 rows, `0 divergence(s)`**, the four pinned ones and the `col.type`
      `BAKCLR = 0` reading the pin called unexplained. Retired; **26 pins → 25**,
      `--check-orphans` clean.
      🎯 **THE PIN'S JUSTIFICATION ROTTED BEFORE ITS VERDICT DID.** *"Blocked
      on a page-1 carve"* is a WALL READING wearing a row's clothes, and the wall
      it named moved five times that same night (2 B → 142 B). So the rule this
      block already carries for numbers extends to REASONS: a pin whose reason is
      a COST is re-priced whenever the budget moves, not when someone re-runs the
      row [[repricing-page1-slice]].
      ⚠️ **AND THE OBVIOUS DETECTOR DOES NOT WORK — TESTED BEFORE BUILDING IT.**
      A gate reading commit messages for *"<probe> ... DIFF -> 0"* would have
      caught this only if the shipping commit NAMED its probe; `ecf0c859` does not
      mention `partial_probe` anywhere in its message. It does add three
      `scratchpad/partial_*.out` artifacts, so a stem-match on touched paths would
      fire — noisily. Recorded as a MEASURED dead end, not built
      [[a-mechanism-inferred-from-one-observation]].
      🎚️ STANDING — correctness scoreboard (meta)
      🤖 AUTONOMOUS — the named rows are the queue; re-run before working one.
