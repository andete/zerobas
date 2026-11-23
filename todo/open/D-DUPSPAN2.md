- [ ] ⚠️ **D-DUPSPAN2 shipped 28 aliases with NO per-site row set.** Filed
      2026-08-22, [`docs/spec-basic-dupspan2.md`](docs/spec-basic-dupspan2.md)
      §5.1. Eleven emulator batteries say the collapse broke nothing; none of
      them can say it was OBSERVABLE — a site nothing exercises stays green
      through any mistake made to it, which is why D-DUPSPAN built
      `scratchpad/dupspan_probe.py` and cut its canonical VALUES. The substitute
      here is `tools/dupspan_indep.py`'s machine-checked per-alias verdict, an
      argument about the MECHANISM rather than the observable. Owed: one row per
      aliased site, and a knife per canonical whose predicted set is that
      canonical's aliases and nothing else.
      📏 **THE PER-SITE DENOMINATOR EXISTS NOW, TAKEN FROM THE SOURCE**
      ([`scratchpad/dupspan2_roster.py`](scratchpad/dupspan2_roster.py)): **27
      aliases in 16 files, 21 distinct canonicals**, each named with its
      canonical and its file:line. A per-site row set needs a per-site list, and
      the list was a sentence in a spec.
      🔴 **AND IT IS 27, NOT 28 — THE SPEC'S §3 HEADING CONTRADICTED ITS OWN
      §6.** The 28th is `dr_stored equ dl_run`, which §6 records as **DECLINED**
      (its comment holds a deliberately unshipped `jp run_prog_top` that an
      `equ` would erase). The heading was written before that decision and never
      re-counted; the FILE count, 16, was right all along. **Corrected in
      place** [[two-sections-of-one-doc-disagreed]].
      🔴 **AN ALIAS IS SPELLED TWO WAYS AND A SCANNER THAT KNOWS ONE
      UNDERCOUNTS.** `ee_synerr_pop:` is a LABEL; `poke_err equ ex_let_err` is an
      EQU. My first cut looked only for `^name:` and resolved **22 of 27** — and
      the five it could not place were all EQUs, which are the *clearest* aliases
      in the tree [[a-hand-listed-denominator-is-a-scope-claim]].
      ➡️ ~~**THE OBSERVABILITY HALF IS STILL OWED, AND NOW IT IS PRICED.** The
      knives the item asks for are **21** … each needing its own battery to
      score — roughly 21 × 7 min.~~ 🔴 **THE PRICE ASSUMED THE BATTERY IS THE
      ONLY SCORER, AND IT IS NOT (D-DUPOBS, 2026-09-06).**
      ✅ **ALL 21 ARMS RUN, HOST-SIDE, IN ~13 MINUTES**
      ([`scratchpad/dupobs_knives.py`](scratchpad/dupobs_knives.py)): each
      canonical cut to a bare `ret` — one uniform mutation, so a green arm cannot
      be "my cut was too gentle here" — and scored with `make unit-test`, ~31 s
      per arm and no emulator anywhere.

          observed by the HOST tests alone   10 of 21
          not observed                       11  ctp_err_pop ctp_link_err
                                                 ed_done elas_err ers_undef
                                                 evmc_sqr_err gosub_stk_over
                                                 nm_fail pl_typeerr
                                                 sst_overflow tm_raise

      🎯 **So half the owed work is DONE and the remainder is bounded**: eleven
      canonicals the host tests do not reach, which may still be exercised by the
      emulator battery — that is the part still worth ~7 min each, and it is
      eleven, not twenty-one.
      ⚠️ **WHAT A CUT CAN AND CANNOT SAY, WHICH THE ENTRY'S OWN WORDING
      OVERSTATES.** An `equ` alias IS the canonical's address, so there is no
      separate code to cut and **no knife can distinguish "reached via the alias"
      from "reached via the canonical"** — that is a STATIC question about who
      names which symbol. What a cut answers is the half the entry actually calls
      owed: whether the shared body is exercised at all, or is *"a site nothing
      exercises [that] stays green through any mistake made to it"*.
      🔴 **AND MY SCANNER MADE THIS ITEM'S OWN DOCUMENTED MISTAKE.** It looked for
      `^canon:` and resolved **20 of 21** — `elas_err` is `equ ems_err_pop1`, a
      canonical that is itself an alias. This entry already says *"an alias is
      spelled two ways and a scanner that knows one undercounts"* and records the
      identical 22-of-27 miss. Reading a warning is not heeding it; the scanner
      follows `equ` chains now, and `elas_err` scores NOT OBSERVED rather than
      going uncounted.
      🔬 **AND `knife-rom-guard-check` CAUGHT THE RUNNER SHIPPING WITHOUT A
      ROM-HASH CHECK — correctly, and it matters more here than usual.** In most
      knives an inert cut produces a green arm that looks like "reddened
      nothing"; in THIS one a green arm **is the finding** (*"this site is
      unobserved"*), so an inert knife would manufacture the very result the run
      exists to report. The runner hashes the images around every build and
      reports `INERT (ROM unchanged)` as its own outcome now.
      ✅ **D-DUPOBS2 (2026-09-10): THE EMULATOR HALF IS STARTED, AND THE SCORER
      IS CHEAPER THAN THE ENTRY ASSUMED**
      ([`scratchpad/dupobs_emu.py`](scratchpad/dupobs_emu.py),
      [`.out`](scratchpad/dupobs_emu.out)).
      🎯 **A RED IS CONCLUSIVE AND A GREEN IS NOT — so the suites are tried
      CHEAPEST FIRST and the ladder STOPS at the first red.** The entry priced
      this at "~7 min each" assuming the whole battery is the scorer; measured
      costs from the last full battery make the ladder
      `error` 12 s → `missing` 45 s → `penderr` 54 s → `error-trap` 68 s, so an
      observed site can cost as little as **12 seconds** instead of a battery.
      📏 **FIRST SLICE, 4 of the 11: `ed_done` is OBSERVED (by
      `missing-acceptance`).** `ctp_err_pop`, `ctp_link_err` and `elas_err` are
      still green against the ladder.
      ⚠️ **AND THE ASYMMETRY IS IN THE VERDICT, NOT HIDDEN IN IT**: "still green"
      means **not observed by THESE FOUR SUITES**, not "unobserved by the
      battery" — that needs the whole battery, and reporting the second as the
      first is precisely the over-claim this entry has caught in its own earlier
      cuts twice.
      🔴 **THE INERT-CUT GUARD MATTERS MORE HERE THAN ANYWHERE**: a green arm IS
      the finding, so a cut that never reached the ROM manufactures the exact
      answer the run exists to report. Every arm hashes the images around its
      build and reports `INERT (ROM unchanged)` as its own outcome.
      📏 **ALL ELEVEN NOW RUN — 14 of 21 CANONICALS OBSERVED.** The generic
      ladder took `ed_done` (`missing`), `ers_undef` (`error-trap`) and
      `evmc_sqr_err` (`error` — 12 s, the cheapest rung).
      🎯 **A SECOND, SUBJECT-MATCHED PASS took one more**: the names say what each
      tail is about, so the cheapest suite that plausibly drives it goes first.
      `gosub_stk_over` fell to `stackpool-acceptance`. ⚠️ A matched ladder is a
      NARROWER claim, not a broader one — still-green after its own subject's
      suites is worth more than a generic green, and still is not "unobserved".
      🔴 **SEVEN REMAIN GREEN, AND THEY ARE NOT ALL THE SAME STRENGTH**:
      • **five have had their subject pass** — `pl_typeerr` (sound, tmfp),
        `tm_raise` (tmfp, intarg, logicops), `sst_overflow` (stackpool,
        stmtpend), `elas_err` (array, clearpool), `nm_fail` (namspc);
      • **two have not**, because their ladder is the expensive one:
        `ctp_err_pop` and `ctp_link_err` want `clearpool` 87 s + `ctllim` **391
        s**, so ~8 min each worst case.
      🔴 **AND THE RUNNER'S OWN FOOTNOTE WAS WRONG FOR ONE RUN.** It said "NOT
      OBSERVED BY THESE FOUR SUITES" unconditionally, while a subject ladder is
      one to three. A verdict line that miscounts its own denominator is the same
      fault this entry keeps finding in the things it measures
      [[a-readout-blind-to-its-own-subject]]. Fixed to name the ladder it
      actually ran.
      ✅ **CLOSED 2026-09-10 — ALL 21 SCORED TO THE CEILING THAT EXISTS:
      17 OBSERVED, 4 NOT** ([`scratchpad/dupobs_emu.py --battery`](scratchpad/dupobs_emu.py),
      [`.out`](scratchpad/dupobs_emu_battery.out)). The two `ctp_*` subject
      ladders ran first and both stayed green (`clearpool` 87 s + `ctllim` 391 s
      each), so all seven survivors went to the battery pass.

          observed by the EMULATOR TIER   elas_err     fldwidth-acceptance
                                          pl_typeerr   graphics + play
                                          tm_raise     time + play
          NOT OBSERVED by any behavioural unit the battery has
                                          ctp_err_pop  ctp_link_err
                                          nm_fail      sst_overflow

      🔴 **AND THE FILED NEXT STEP ABOVE NAMED THE WRONG SCORER — USING IT
      WOULD HAVE ANSWERED THIS ITEM WRONGLY, IN THE DIRECTION THAT CLOSES IT.**
      *"the full battery … is the only scorer that can turn 'still green' into
      'unobserved'"* is false: `patch-freshness-check` compares the committed
      `.ips`/`.bps` against the built ROM, so **any** cut reddens it by
      construction. Measured, not reasoned — with `ctp_err_pop` cut,
      `make patch-freshness-check` returns **rc=2**, and green again once
      restored. A `gates-full` pass would have marked all seven "observed" via a
      gate that reads ROM BYTES rather than behaviour. So the scorer is the
      **emulator tier only** (81 units; the 39 static ones excluded, and the list
      is taken from `run_gates.STATIC` itself rather than re-typed — one
      denominator). That is a ceiling, not a shortcut: "still green" here means
      no behavioural gate in the battery reaches the site.
      🔴 **THE FIRST BATTERY RUN COULD NOT NAME ITS OWN RED.** The verdict
      said `observed by the EMULATOR TIER` and stopped — the ladder pass can name
      its suite because it runs one at a time, and this pass runs 81 at once into
      a `probe_tmp` log that is deleted at exit. An unnamed outcome reads as no
      outcome [[an-unnamed-outcome-reads-as-no-outcome]]; the runner parses
      `run_gates`' own `RED:` line now, and **that fix is what produced the
      finding below** — without it the run would have reported three anonymous
      reds and hidden it.
      🎯 **THE SUBJECT-MATCHED LADDER WENT 1 FOR 4, AND THE THREE MISSES WERE
      NOT NEAR MISSES.** The heuristic is *the name says what the tail is about*:
      • `elas_err` → its ladder was `array`, `clearpool`; the unit that sees it is
        **`fldwidth-acceptance`**;
      • `pl_typeerr` → ladder `sound`, `tmfp`; seen by **`graphics` + `play`**;
      • `tm_raise` → ladder `tmfp`, `intarg`, `logicops`; seen by **`time` + `play`**.
      Only `gosub_stk_over` → `stackpool-acceptance` was predicted. A shared
      error tail is reached from wherever its callers are, and its NAME describes
      the error it raises, not the statement that raises it
      [[a-shared-tail-is-not-a-decision]]. **A subject ladder is a cost
      optimisation, never evidence** — a green one says less than it looks.
      ➡️ **WHAT THE 4 LEAVE OWED IS THE ITEM'S ORIGINAL POINT**, not a new
      question: `ctp_err_pop`, `ctp_link_err`, `nm_fail` and `sst_overflow` are
      exactly *"a site nothing exercises [that] stays green through any mistake
      made to it"*. Each needs a row that reaches it, or a written decline saying
      why it cannot be reached from BASIC. The per-site row set for the other 27
      aliases is still owed separately.
      🟢 **2 OF THE 4 SETTLED 2026-09-27 (D-SSTROW, loop):**
      • **`sst_overflow` — REACHED, KNIFE-PROVEN.** `basic_probe_string.py`
        (string-acceptance) gains `hex.depth9` / `hex.depth10`: a concat nest
        with `HEX$(1)` innermost, so HEX$'s result tail (`shx_finish` →
        `shxf_overflow`, an alias of this body) finds the 10-entry pool full at
        depth 10. Both expectations are the VG-8020's own answers (depth 9 →
        `LEN` 10, depth 10 → *String formula too complex*, zerobas the same).
        A knife on the body's error code FAILS `hex.depth10` and leaves
        `hex.depth9` passing. 🔴 **The obvious row was blind:** the same nest
        with `A$` innermost (tempst's `concat` shape) raises the same error
        on both machines, and the knife did NOT move it — that ERR 16 comes
        from the slice's own push, sub-side. A row that shows the right error
        at the right depth can still not reach the named site
        [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      • **`nm_fail` — NO LONGER EXISTS.** D-DKNAME removed the label (only
        comments in `basic/files.asm` and PROVENANCE name it).
      🔧 **FOUND ON THE WAY — D-PLANCHILD:** `make gates-plan` scoped this very
      edit to **0** emulator suites, because `tools/pick_gates.py`'s closure
      followed only `import`s and `string_acceptance.py` runs
      `basic_probe_string.py` as a SUBPROCESS, by path. The closure now also
      follows a quoted `<name>.py` literal that resolves to a local module;
      the plan then reads `string-acceptance`. Selftest arm P12b, with a
      NEGATIVE half, and a mutation removing the literal-following turns it
      RED in the module under test.
      ~~➡️ **STILL OWED: `ctp_err_pop`, `ctp_link_err`** (`basic/cload.asm`) —
      CLOAD's tape-read failures inside a program body; the row is a
      truncated `.cas` image, cut inside the link word and inside the body.~~
      🟢 **AND THE LAST 2 SETTLED THE SAME NIGHT (D-CASCUT):**
      `basic_probe_castail.py` (castail-acceptance) gains `cas-cut-link` and
      `cas-cut-body` — a tokenised tape that ENDS inside the program, CLOAD,
      then Ctrl-STOP. All three sides (VG-8020, CF-3300, zerobas) read
      `<load-failed>` and return to a working prompt (`:alive`). A knife per
      exit (redirect to `ctp_oom`) moves ONLY its own row. 🔴 **The first
      `cas-cut-link` reached the WRONG exit**: it kept both link bytes on the
      premise that the last byte before the silence is never framed; on
      zerobas that byte IS read, the knife on `ctp_link_err` moved nothing and
      the one on `ctp_err_pop` moved both rows. Cutting after link-LOW fixed
      it. Same answer on all three sides either way — only the knife could
      tell. **All four sites the audit named are now reached or gone.** The
      per-site row set for the other 27 aliases is still owed separately.
      🎚️ APPARATUS — per-site alias rows
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (roster + count fixed 2026-08-26; the 21 knives remain, now priced).
