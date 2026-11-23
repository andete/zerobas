- [ ] 🔴 **SEVEN FILED PROBES PRINT DIVERGENCES AND EXIT 0.** Measured
      2026-08-31 by D-FILEDROT,
      [`docs/spec-filed-row-rot.md`](docs/spec-filed-row-rot.md), instrument
      `scratchpad/filed_row_sweep.py` — every open TODO item's cited row set,
      re-run serially with the refcache OFF. **THE DENOMINATOR: 18 probes — 14
      diverge, 7 of those INVISIBLE to any rc-only collector, 2 clean, 2 with no
      verdict channel at all.**
      The seven: `deffn_alias_probe`, `keystr_probe`, `ntwall_probe`,
      `onerrarm_probe`, `open2_probe`, `playfn_fixture_probe`, `trapsvc_probe`.
      Several are divergences we have DECIDED not to fix (`keystr` is the
      NOT-THIS-ONE `KEY n,"str"` item, ~160 B), so the fix is NOT "make them
      exit 1" — a deliberate non-fix must still be VISIBLE, and a probe cannot
      tell the two apart. What is owed is a convention that separates *measured
      and known* from *measured and unnoticed*.
      🔴 **AND THERE IS NO VERDICT CONTRACT TO BUILD ON**: the 18 probes use
      **eight** output shapes and two rc conventions. The sweep reads markers
      and rc as INDEPENDENT channels for exactly that reason, and refuses to
      call anything clean when they disagree.
      ✅ **CONVENTION LANDED 2026-08-31 (same day):**
      `tools/filed-row-known.txt` pins, per probe, the divergent rows a
      filed item OWNS — named by the owning entry's HEADING, because line
      numbers rot. The sweep adjudicates every marker line against it and the
      verdict now reads `[N known]`, `🔴 UNFILED — read them`, or `⚠️ NO LONGER
      DIVERGING — the CVI shape, re-run and re-file`. **Measured on all 18: 0
      unfiled, 0 stale — every divergence in the corpus is owned by an entry.**
      Falsified by planting BOTH directions on the same output (a dropped known
      row reads UNFILED; a ghost row reads NO-LONGER-DIVERGING; the unmodified
      control reads neither). The set is pinned; the judgement is not.
      📏 **RE-RUN IN FULL 2026-09-02 (13 probes, serial, refcache OFF).** The
      corpus shrank 18 → 13 because five items closed; **0 UNFILED, 0 NO-LONGER-
      DIVERGING** across all thirteen. The one stale pin the day produced —
      `onerrarm_probe`'s four rows, fixed by D-ONERRGO an hour earlier — was
      found and removed by hand before this run, which is the debt a fix leaves
      when it does not move the pin with it.
      ✅ **AND THE RUN CLOSED THE `reclen_probe` HOLE (D-RECLENV).** It reported
      `🔴 NOTHING PARSED`, and the sweep's own source says why: *"a two-column
      table, NO verdict word anywhere -- an EIGHTH shape that simply has no
      channel to read"*. That refusal is honest, but the consequence was that a
      probe documenting an **untrappable hang** (D-PUT3) was invisible to the one
      instrument built to notice unnoticed divergences. It now emits per-row
      `DIFF <label>` markers and a `DIFF: n/m` summary, and the sweep reads
      `DIVERGES 4/7 ... [4 known]`.
      🔴 **A NAIVE DIFF COUNT WOULD HAVE BEEN WRONG, AND THAT IS THE DESIGN.**
      Ten `k./x./ctl./s.` rows read blank on zb as a CONSEQUENCE of that same
      hang (their programs issue 3+ PUTs). Counting them would inflate ONE defect
      into fourteen and claim record-layout evidence the run does not have, so
      they are reported separately and **deliberately NOT pinned**. The split is
      derived from the CASES data, not a hand-kept list that would drift.
      🔴 **AND THE FIRST CUT OF THAT CHANNEL DID NOT WORK** — a `DIFF:` summary
      alone made the sweep say *"0 known, ⚠️ 4 known row(s) NO LONGER DIVERGING"*
      while listing those four AS DIVERGING: its `MARKER` wants `DIFF` followed
      by whitespace, and `DIFF:` has a colon. Caught by RUNNING the sweep against
      the file rather than assuming the channel worked.
      📌 **12 of 13 now have a readable verdict channel.** `budget_probe` is the
      last, and it is a TIMING TABLE with no verdict concept at all — an honest
      unparsed, not a hole.
      📏 **RE-RUN IN FULL 2026-09-05 — 20 PROBES, SERIAL, REFCACHE OFF — AND
      THE CORPUS GREW 13 → 20 AS TODAY'S SLICES CITED NEW PROBES.**
      🟢 **THE MAINTENANCE THIS ENTRY ASKS FOR WAS OWED BY TODAY'S OWN WORK**:
      `reclendom_probe` and `uplus_probe` entered the corpus diverging and
      unpinned, and would have read `🔴 UNFILED`. Both adjudicated into
      `tools/filed-row-known.txt` from the runs, named by their owning heading.
      🔴 **AND ONE OF THOSE PINS WAS UNVALIDATABLE — WORSE THAN NO PIN.**
      `reclendom_probe` read `🔴 NOTHING PARSED`: it prints `DIFF` in the MIDDLE
      of a table row, and the sweep's `MARKER` wants it at line START or END. So
      eight pinned rows could be neither confirmed nor go stale, while
      `--check-orphans` still called the pin live. **A NINTH output shape**, and
      the same remedy D-RECLENV applied to `reclen_probe`: per-row `DIFF <label>`
      lines.
      🔴 **AND THE FIX PRODUCED A PHANTOM ROW ON ITS FIRST TRY** — the summary
      `DIFF total 8/23` matched `^\s*DIFF\s` and was counted as a NINTH marker,
      reading as `1 UNFILED`. Re-worded to carry no marker token; now 8 markers,
      **8 known, 0 unfiled**. Caught by RUNNING the sweep against the file, which
      is the same way D-RECLENV caught its mirror-image `DIFF:` bug.
      🔴 **THREE PROBES CARRY GENUINELY UNADJUDICATED DIVERGENCES — 11 MARKER
      LINES, AND THEY ARE THE NEXT THING TO READ:**

          casfch_probe      6 markers   0 known, 6 UNFILED   (rc=1)
          trapdepth_probe   4 markers   0 known, 4 UNFILED   (exits 0)  🟢 READ
          ramfree_probe    10 markers   9 known, 1 UNFILED   (rc=1)

      🟢 **`trapdepth_probe` READ 2026-09-05 — ALL FOUR WERE FALSE, AND THE CAUSE
      IS WORTH THE ENTRY.** It scored the whole reading `[D E F]`, and **`D` is
      the recursion DEPTH before overflow — a CAPACITY figure set by how much RAM
      each machine has for GOSUB frames.** It reads 4071 / 3302 / 2858 and can
      never agree, so every row reported `REFS SPLIT · zb DIFF` while `E` (the
      ERR that stopped it) and `F` (actual handler entries) were **identical on
      all three, every row** — which is the subject. Now scored on `E F`; all
      four read `refs agree`.
      🎯 **AND THE ABSOLUTE COMPARISON WAS HIDING THE FIGURE `D` IS ACTUALLY
      FOR.** The question is a WITHIN-machine delta, and it is now printed:
      `d.depth0 → d.depth1` costs **−25 / −25 / −22** frames, `→ d.ctl20`
      **−31 / −31 / −27**. ⚠️ **Deliberately NOT scored**: a frame is 8 B here
      (`GOSUB_FRAME`) and this row does not measure the references' frame size,
      so 25-vs-22 in FRAMES is not yet a difference in BYTES
      [[a-mechanism-inferred-from-one-observation]].
      🔴 **AND REMOVING THE FALSE MARKERS EXPOSED A SECOND HOLE**: the sweep went
      from `4 UNFILED` straight to `🔴 NOTHING PARSED`, because this table ends no
      row in a verdict word and carries no `vg8020=` pair. Honest, and still
      blind — **a probe that is CLEAN has to be able to say so.** Each row now
      ends `SAME`/`DIFF`/`NO-ORACLE`; the sweep reads
      `clean: 4 parsed line(s), no divergence marker`.

      That is the sweep doing exactly what it exists for: a divergence nobody has
      adjudicated, made loud. **Not read yet — recorded so the next pass starts
      from a list rather than a re-run.**
      🟢 **THE ORPHAN SIDE IS NOW CLEAN, 2026-09-06 (D-PINPRUNE) — 17 pins → 14,
      and TWO OF THE THREE WERE DEBT THIS DAY'S OWN FIXES LEFT.**
      `--check-orphans` named three pins cited by no OPEN item, so the sweep
      never ran them and could not see them go stale. Re-run by hand with the
      refcache OFF, every pinned row now AGREES:
      | pin | rows | reading | closed by |
      |---|---|---|---|
      | `uplus_probe` | `x.str` `x.strlit` `x.prstr` | 0 of 9 diverge | D-UPSTR (today) |
      | `reclendom_probe` | 8 rows | 0 of 23 diverge | D-RECLENFIX (today) |
      | `ntwall_probe` | 6 rows | all `refs-agree zb=same` | D-NTFLOOD |
      All three removed; `--check-orphans` now reads *"no orphans — every pin
      names a probe this sweep still runs"*.
      🎯 **THIS IS THE `onerrarm_probe` SHAPE AGAIN, AND IT IS THE ENTRY'S OWN
      STANDING DEBT** — *"the debt a fix leaves when it does not move the pin
      with it"*. It recurred twice in one day, from my own commits, which says
      the rule is not carried by anything that runs: closing an item does not
      touch `tools/filed-row-known.txt`, and only `--check-orphans` notices, and
      only when someone runs it.
      🔴 **AND I ALMOST FILED A FALSE FINDING OFF A TRUNCATED VIEW.** The first
      look at `ntwall_probe` showed 4 rows, none of them the six pinned, and I
      was one step from *"the pin names rows the probe no longer emits"*. The
      file I was reading was **my own `tail -22`**, not the run: the probe's
      output had gone to `scratchpad/ntwall_rerun.out`, 115 lines, where all six
      are present and agreeing [[a-readout-blind-to-its-own-subject]].
      ✅ **THE 11 STANDING MARKERS ARE ALL RESOLVED — RE-VERIFIED 2026-09-09,
      AND SIX OF THEM WERE ALREADY STALE WHEN I READ THEM.**
      • `trapdepth_probe`'s 4 — read 2026-09-05, all four FALSE (recorded above).
      • `casfch_probe`'s 6 — pin REMOVED 2026-09-08: *"`i.inp` and `i.byte` no
        longer diverge"*. The probe has since left the corpus with its citing
        item, so a re-run would not have found them either.
      • `ramfree_probe`'s 1 — **measured today**
        ([`scratchpad/filedrow_ramfree.out`](scratchpad/filedrow_ramfree.out)):
        `clean: 14 parsed line(s), no divergence marker`. Gone.
      ⚠️ **The corpus has grown 20 → 53 probes since that list was written**, so
      "the next thing to read" had rotted the way a ranked candidate does
      [[a-ranked-candidate-rots-like-a-wall]]. Re-run before acting on any list
      in this block.
      🟢 **AND THE ENTRY'S OWN NAMED DEBT IS PAID — D-PINGATE, `make
      filed-pin-check`** ([`tools/check_filed_pins.py`](tools/check_filed_pins.py)).
      This block's verdict was *"the rule is not carried by anything that runs:
      closing an item does not touch `tools/filed-row-known.txt`, and only
      `--check-orphans` notices, and only when someone runs it."* There is now a
      caller in the battery. 🎯 **The CHECK is not new** — it is
      `filed_row_sweep.check_orphans()`, which found all three historical stalls;
      the gate IMPORTS the sweep rather than reimplementing it, so "the corpus"
      has one definition and not two free to drift.
      🔴 **AND PRINTING TWO COUNTS SIDE BY SIDE FOUND A BLIND SPOT INSIDE THE
      INSTRUMENT.** `check_orphans()` names pins with `([a-z0-9_]+_probe):` and
      `known_rows()` with `": " in line` — **24 vs 25**. The odd one is
      `basic_probe_nodisk`: it does not end in `_probe`, and `CITE` only matches
      `scratchpad/<x>_probe.py` while it lives in `probes/basic/`. So it is in
      **neither the corpus nor the orphan report** — a pin that could never be
      called stale, inside the instrument built to make exactly that loud.
      🎯 **It is harmless TODAY and that is not the point**: its rows are also
      pinned to exact values in `basic_probe_nodisk.PINNED` and gated by `make
      nodisk-acceptance`, which the file itself says. The hazard is that the
      exclusion was SILENT, so the next such pin gets the blind spot without the
      belt and braces. The gate now reconciles the two scans and reddens on any
      pin the orphan scan cannot NAME unless its line declares `NOT-IN-SWEEP`
      with what validates it instead
      [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
      🔬 Both arms are selftested by planting: a fabricated orphan and a
      fabricated unnameable pin each go red and name themselves, and the
      committed file is judged by the same code that judges the plants.
      ✅ **RUN IN FULL 2026-09-10 (D-FILEDSLICE) — ALL 53 PROBES, SERIAL,
      REFCACHE OFF, IN FOUR SLICES**
      ([1](scratchpad/filedrow_slice1.out), [2](scratchpad/filedrow_slice2.out),
      [3](scratchpad/filedrow_slice3.out), [4](scratchpad/filedrow_slice4.out)).
      ⏱️ **AND THE ESTIMATE ABOVE WAS WRONG BY AN ORDER OF MAGNITUDE — it is
      ~20 MINUTES, not hours.** The 900 s per-probe timeout is a ceiling nothing
      reaches; the slowest probe in the corpus is 94 s and the median is under
      10. That mattered: "this needs a window we do not have" is why the run had
      been deferred, and it was a guess about a cost nobody had measured.
      🟢 **THE HEADLINE IS THE ONE THING NO STATIC GATE CAN REACH — A PIN WHOSE
      ROWS STOPPED DIVERGING.** `playfn_fixture_probe`'s `empty string, no delay`
      now reads `-1 0 0 0` on BOTH sides. Removed from the set, per the file's own
      rule. ⚠️ **Confirmed TWICE before removal** — these are PLAY *timing* rows
      and pulling a pin on a flake is worse than leaving it; two independent runs
      give an identical divergence set
      ([`.out`](scratchpad/playfn_recheck.out), [2](scratchpad/playfn_recheck2.out)).
      🔴 **NO CAUSE IS CLAIMED**; the other three transient rows still differ, so
      the class is not closed, only this member
      [[a-mechanism-inferred-from-one-observation]].
      🔴 **FOUR PROBES READ UNFILED — AND THREE WERE DEBT FROM THIS SESSION'S OWN
      SLICES**, which is this entry's standing shape, *"the debt a new probe
      leaves"*, recurring inside a single night. All adjudicated from the RUN:
      `asciidigit_probe` (2), `putdomain_probe` (8), `dskibytes_probe` (3) and
      [`bareform_probe`](scratchpad/bareform_probe.py) (1, apparatus-bounded: both references read `<none>`
      because `CLOAD` waits for tape). Two more had no verdict channel and are
      now declared NO-VERDICT with their kind established from the probe rather
      than the family name: `deffn_nestdepth_probe`, `dskilow_probe`.
      🔴 **THE PHANTOM-SUMMARY BUG HAPPENED A THIRD TIME, IN MY OWN PROBE.**
      `asciidigit_probe` printed `  DIFF 2/5 ...`, which `MARKER`'s `^\s*DIFF\s`
      counts as one more divergent row than the run has — it reported 2 and swept
      as 3. Same remedy as `reclen_probe`'s `DIFF:` and `reclendom_probe`'s
      `DIFF total`: the summary now says `rows diverging`. ~~**Three instances
      says the wording is load-bearing and nothing enforces it.**~~
      ✅ **ENFORCED 2026-09-24 (D-MARKERWORD), AND IT CAUGHT THREE MORE THE
      MOMENT IT RAN** — see that item. Six instances, not three.
      🎯 **AND VERIFYING THE PINS IS WHAT CAUGHT THE LAST ONE.** Re-run after
      pinning, six of seven read `[N known]` — and `dskibytes_probe` read
      `[0 known, ⚠️ 3 known row(s) NO LONGER DIVERGING]` **while all three rows
      were still failing**. Its `DIFF: n/m` summary says how many diverge but not
      WHICH, so the pin could be neither confirmed nor go stale. Fixed with
      per-row `DIFF <label>` lines (D-RECLENV's remedy); now `[3 known]`.
      **A pin is not filed until the sweep has been re-run and agrees.**
      📏 **RE-RUN IN FULL 2026-09-24 — 73 PROBES, SERIAL, REFCACHE OFF, THE
      WHOLE CORPUS.** Result: **1 UNFILED · 0 NO-LONGER-DIVERGING · 35 of 73
      NOTHING PARSED.**
      💰 **AND THE COST LINE BELOW WAS OPTIMISTIC BUT NOT BY MUCH — MEASURED:**
      5 probes in 119 s, then 68 in 1895 s, so **~34 minutes for the full 73** at
      ~26 s each. ⚠️ A first reading of this called the estimate "stale by 3.6×";
      that was the PROBE COUNT (20 → 73), not the TIME. **A count is not a
      cost** — the corpus more than tripled while the wall time went from
      "20 minutes" to about half an hour, because most of the growth is in
      fast probes.
      📊 **THE CORPUS SPLITS EXACTLY FOUR WAYS (2026-09-24): 35 NOTHING PARSED
      · 9 DECLARED no-verdict · 21 clean · 8 DIVERGES = 73.** The 35 is the real
      hole; the 9 are measurement instruments doing their job.
      ✅ **AND THE TRIAGE IS NOT "GIVE ALL 35 A CHANNEL".** A probe that COMPARES
      two sides and cannot say so is a hole; a probe that only MEASURES has no
      verdict to give and should be DECLARED. **Three declared 2026-09-24**, each
      checked against its own header first:
      `aliasscope_probe` (a watchpoint BYTE COUNT — and D-ALIASBITE's own lesson
      is that a footprint does not predict an outcome) · `hookcount_probe` (a
      TALLY of breakpoint entries per hook cell) · `rigcap_probe` (asks openMSX
      which pluggables EXIST — it characterises the EMULATOR, not BASIC, so
      there is no oracle to diverge from). **Two more on 2026-09-24:**
      `fatbuf_probe` (reads which BYTES are resident in the CF-3300's RAM to
      count buffer REGIONS; its own closing lines say *"evidence about REGION
      COUNT, never about the engine"*) and `diskwrites_probe` (which cells the
      disk side WROTE against which CHANGED on return, reporting BLIND SPOTs
      rather than a verdict). **Four more on 2026-09-24, read in full before
      deciding:** `mdr_probe` (*"Feasibility scouting for MOTOR / DELETE / RENUM
      sweep rows"* — its own first line) · `ctrlstop_probe` (an APPARATUS
      control: *"this probe is that extension's CONTROL"*, testing the harness's
      two-row hold rather than BASIC) · `csrsw_probe` and `clicksw_probe` (both
      ask whether a work-area cell is READABLE AT ALL and report PER SIDE —
      `READABLE` / `does NOT distinguish the two settings` / `INSTRUMENT FAULT`
      — three machines, three independent readings, **no cross-side verdict**;
      the human compares them). **Four more the same night:** `beepobs_probe`
      (*"is BEEP's effect observable through the PSG?"* — it exists because
      BEEP's sweep row prints a CONSTANT MARKER and so scores that the word RAN
      and nothing about what it DID) · `clearhimem_probe` (FEASIBILITY: *"is
      `CLEAR n,himem` safe to make a sweep row"*, settling two hazards before a
      row is written) · `varptrn_probe` (asks whether a row is WRITABLE AT ALL
      and answers no for the obvious axis: *"A row can only be written on an
      axis where the sides CAN agree. The ADDRESS cannot"* — **a probe that
      concludes a comparison is impossible cannot itself be one**) ·
      `spritestate_probe` (*"This observes STATE and COUNT. The CAUSE is a
      question for the …"*). **Five more:** `drawleak_probe` (an APPARATUS
      diagnosis — DRAW's ANGLE and SCALE persist across PROGRAMS, so a BATCHED
      sweep carries them between cases and the middle one *"reads the
      BACKGROUND — it drew rotated"*) · `drawsubst_probe` (the `varptrn` shape
      again: *"BOTH MACHINES DREW NOTHING AND NEITHER RAISED. A row agreeing on
      an absence both sides produce says nothing about either"*) ·
      `nodiskgap_probe` (a markdown TABLE of rows × machines, no verdict
      column) · `fcbstride_probe` (*"265 or 267? Measure it before any stride is
      laid down"* — reconciling TWO OF OUR OWN NUMBERS that disagree by 2, not a
      reference comparison). **Four more:** `boolaxis_probe` (*"can the BOOLEAN
      rows carry a VALUE without diverging?"* — the absolutes are
      machine-dependent) · `deleterange_probe` (*"a breadth row needs to know
      whether execution CONTINUES after a successful DELETE: if it does not,
      nothing can be read afterwards and the row cannot carry a VALUE"*) ·
      `paintarg_probe` (does `PAINT(x,y),C,B` fault, *"or does the FLOOD outrun
      the capture?"* — and it records its own first cut failing its own control)
      · `datacolon2_probe`. **13 left.**
      🔴 **AND `datacolon2` IS A THIRD TRAP, AFTER THE TWO FAILED CLASSIFIERS.**
      Its header says the control *"must read 42 on both machines"* — pure
      comparison language — but it prints `=== <machine> ===` sections of raw
      readings with NO cross-machine verdict. **AN EXPECTATION STATED IN A
      HEADER FOR A HUMAN READER IS NOT A VERDICT THE PROBE COMPUTES**, exactly
      as MENTIONING a reference is not having an oracle. Reading the final
      prints is what separates them, every time.
      🧩 **AND FOUR OF THEM TURN OUT TO BE ONE CLUSTER:** `keyline`, `holdrow`,
      `joyplug` and `sticksample` all ask **whether the RIG works** — is the key
      line where we think, does the hold land, is a joystick pluggable, is the
      sampling window wrong. **They are the apparatus asking about itself**, and
      they are declared as a group with that said once. `keyline` is the
      canonical case of trap three: its header states *"it must find 'Z'
      somewhere … the same offsets must be blank"* and it prints NONE of it.
      **9 left.**
      📊 **A PATTERN IS EMERGING IN WHAT GETS DECLARED, AND IT IS WORTH NAMING:**
      most of these probes exist to decide **whether a row can be written at
      all** — is the effect observable, is there a cell, can the sides ever
      agree, is the sweep contaminating itself. **They are the step BEFORE a
      row, so of course they have no verdict.** That is not a hole in the
      corpus; it is the corpus containing its own groundwork.
      🔴 **AND THERE IS NO MECHANICAL TRIAGE — TWO SCANS WERE TRIED AND BOTH
      FAILED, WHICH IS THE USEFUL PART OF THIS SLICE.**
      **(a)** *"does it print verdict vocabulary?"* — `keyline_probe` carries
      explicit expectations in its own header (*"it must find 'Z' somewhere ...
      the same offsets must be blank"*) and scores ZERO: the expectations live
      in comparisons, not in printed words.
      **(b)** *"does it drive a reference machine?"* — nearly all of them do,
      and `fatbuf_probe` mentions one FIVE times while being pure
      characterisation. **MENTIONING A REFERENCE IS NOT HAVING AN ORACLE.**
      🎯 **SO THE QUESTION IS NOT ANSWERABLE FROM THE SOURCE'S SURFACE:** it is
      *does this probe ask "do we MATCH?" or "what does X DO?"*, and only
      reading the probe's purpose settles it. The remaining 30 are a read-each
      job, a few per session rather than one sweep. ⚠️ **Do not let a future
      tick "speed this up" with a classifier** — both of the above looked
      reasonable and were wrong in opposite directions.
      🔬 **DECLARING WAS VERIFIED EMULATOR-FREE, IN THREE DIRECTIONS**, by
      calling the sweep's own `score()` rather than re-running 34 minutes of
      probes: undeclared → `NOTHING PARSED`; declared → `BY DESIGN`; **declared
      BUT EMITTING A MARKER → still `DIVERGES`.** So a declaration cannot
      silence a real divergence.
      ⚠️ **THAT DOES NOT CANCEL THE SWEEP'S OWN WARNING**, which is about a
      different failure: *"Declaring one does NOT make its rows safe —
      interpspeed sat here for two days with `c.arith` reading `<NO OUTPUT>`,
      which set the filed speed band 0.7× too low"*. A declaration protects
      against a MISSING channel, never against rows that are quietly WRONG.
      🔴 **35 OF 73 — NEARLY HALF — HAD NO READABLE VERDICT CHANNEL**, against
      this entry's own *"12 of 13 now have a readable verdict channel"* from
      when the corpus was 13. **That line is badly stale and the ratio has gone
      the wrong way**: every slice since has cited probes without asking whether
      the sweep can read them. ⚠️ `NOTHING PARSED` is an honest refusal, not a
      false green — but a corpus half of which cannot be adjudicated is a
      denominator with a hole in it, and that is this entry's own subject.
      ➡️ **THE UNFILED ONE IS A ROW THAT CAME BACK — filed separately below
      (D-PLAYBACK), and DELIBERATELY NOT RE-PINNED.**
      ✅ **`playx_probe` HAS A VERDICT CHANNEL (2026-09-25) — 9 → 8 LEFT.** It
      asks *"do we MATCH?"*, so it gets a channel, not a declaration: one
      `DIFF <label>` per row where zerobas and the VG-8020 differ, then the
      sweep's own `DIFF: n/m` summary — printed BEFORE the CF-3300 column,
      whose boot-per-case delivery is a known apparatus failure that exits
      hard. `scratchpad/playx_after.out` reads **`DIFF: 0/13`** (D-PLAYX12
      shipped `X` the same night), and `filed_row_sweep.score()` reads it
      clean; a planted `DIFF` row reads DIVERGES, unfiled — both directions
      checked. **`playnote_probe` likewise** (`scratchpad/playnote_run.out`,
      `DIFF: 0/10`; `n00` unscored — its own header says a rest's register
      reading is not a pitch verdict). **`playmml_probe` and `playpsg_probe`
      ([`scratchpad/playmml_probe.py`](scratchpad/playmml_probe.py),
      [`scratchpad/playpsg_probe.py`](scratchpad/playpsg_probe.py)) are
      DECLARED NO-VERDICT** (`tools/filed-row-known.txt`): both are
      D-KWPLAY scouts whose questions are answered, and the verdicts they
      scouted for are kwsweep's TIME-synced `playkw_*` rows — `playpsg`'s own
      reads are unsynced (D-PSGLATCH's race), so a channel there would score a
      racy instrument. **Then four more DECLARED** (2026-09-25):
      [`scratchpad/cf3300_files_probe.py`](scratchpad/cf3300_files_probe.py)
      (a refresh tool for a frozen constant),
      [`scratchpad/loadrun_probe.py`](scratchpad/loadrun_probe.py) (a timing
      instrument),
      [`scratchpad/mergeshape_probe.py`](scratchpad/mergeshape_probe.py)
      (characterises the reference's MERGE), and
      [`scratchpad/mergewin_probe.py`](scratchpad/mergewin_probe.py) (its
      window question was retired by D-BUFMERGE). **1 left:**
      [`scratchpad/clrtrapstk_stop_probe.py`](scratchpad/clrtrapstk_stop_probe.py)
      already HAS a channel, but it refused its own run: its two-tap positive
      control read VG-8020 **2**, zerobas **11**, which it took for a tap that
      did not land. It was not the instrument — it was D-STOPTAP. **After
      D-STOPTAP's fix (2026-09-25) the control reads 2/2 and the probe reads
      `0 divergence(s)`, clean to the sweep. THE TRIAGE IS DONE: 0 left.**
      🎚️ APPARATUS — probes that exit 0 on a divergence
      🤖 AUTONOMOUS — re-run it in slices after any session that adds probes.
      **Measured 2026-09-24 at ~34 minutes for the full corpus**, and the debt
      lands the same night.

      📏 **RE-RUN IN FULL 2026-09-27 (loop) — 91 PROBES, SERIAL, REFCACHE OFF: 0
      UNFILED, 0 UNDECLARED NOTHING-PARSED, 0 NO-LONGER-DIVERGING.** The first
      pass read 5 UNFILED and 11 NOTHING PARSED, and every one was bookkeeping
      or a stale PROBE, not a new defect: `ptrchain_probe` reads the pre-move
      private cells unless given `--after` (now in the sweep's ARGS; it reads
      `DIFF: 0/9`); `strtemp_probe` hard-coded the old `$DB00` ceiling (every
      row read 64256; it now reads HIMEM, and its 4 real rows were S2b's heap
      half, pinned — D-S2BHEAP then closed 3 of them the same night; the pin
      now names `temp_two` alone, re-scored `DIVERGES 1/8 [1 known]`); `nset`/`nset2` are the cells Joost's 2026-09-25 "Stop here"
      names; `fremops` is today's frame economy; the 11 silent ones are
      characterisation/timing instruments, now DECLARED with their own reasons.
      🔌 The sweep also REFUSES any probe that drives the rig or opens a window
      (`rigfw_window_probe`: NOT SWEPT — ask Joost first). ✅ `rigcap_probe`'s
      600 s TIMEOUT (2026-09-27) was the probe's own launch: default renderer
      (a WINDOW) and no subprocess timeout. It is now headless and bounded and
      finishes in seconds; `cf3300_arch_probe` had the same launch and got the
      same fix (re-run: 35 claimed cells, as filed). The sweep now also
      refuses any probe that launches openMSX without `renderer none`.
