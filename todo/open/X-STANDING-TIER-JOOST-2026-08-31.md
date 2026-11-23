- [ ] 🔁 **STANDING TIER (Joost, 2026-08-31): WHEN THE 🤖 QUEUE DRAINS, REVIEW
      EACH STATEMENT'S IMPLEMENTATION IN FULL, one verb at a time.** The
      calibration: PLAY was picked at RANDOM for review and yielded D-MUSICF (a
      stuck-voice bug both references separate,
      [`docs/spec-basic-musicf.md`](../../docs/spec-basic-musicf.md)) plus
      D-PLAYCORNER (four wrap divergences + `M0`,
      [`docs/spec-basic-playcorner.md`](../../docs/spec-basic-playcorner.md)) — two
      commits from one verb nobody suspected. Method that worked: read all
      layers of the implementation first, code-review for suspicious mechanism,
      THEN write the differential rows for what the review flags, fix against
      the rows. The review finds what row-first sweeps cannot: a wholesale
      store that is only wrong across TWO statements, a wrap that only shows
      at 65536+.
      📋 **WORKLIST DRAFTED (2026-08-31, while a battery ran):**
      [`docs/review-tier-worklist.md`](../../docs/review-tier-worklist.md) — 133
      handlers, 48 with a same-named spec, 85 without, grouped into likely-THIN
      (the `OUT`/`POKE`/`VPOKE` raw-I/O trio first: the coercion SURFACE is
      gated, the port/address MECHANISM never reviewed, and the D-PLAYCORNER
      wrap class lives exactly there; then DATA/RESTORE, DEFtype, TIME, CALL,
      MOTOR, AUTO/RENUM) vs arc-covered-under-another-name. ⚠️ A RANKED
      CANDIDATE ROTS — the file says so itself; re-verify per verb at pick-up.
      🔁 **PIPELINE RULE (Joost, same day): battery time is the NEXT verb's
      reading time.** Only emulator rows and tracked-file edits serialize
      behind a running battery; the read-and-review phase runs in parallel,
      with notes in /tmp until the battery lands.
      🎯 **AND JOOST SHARPENED THE ORDER (2026-09-11):** *"we still need to get rid
      of the 'no known gap' items in the table, so we have more known tier-ed
      work."* Said while ruling the D-SPMERGE jump loop, i.e. **this ranks directly
      AFTER that slice and ABOVE picking further TIER 4 speed work.** The reason is
      the queue itself: TIER 1 is down to the stack item, TIER 2 and TIER 3 are
      EMPTY, so the binding constraint stops being *"fix the next defect"* and
      becomes *"find out what is actually broken"*. A **"no known gap"** row is not
      a keyword that is fine — it is a keyword nobody has attributed evidence to,
      and converting one either yields a tiered defect or retires honestly.
      🔴 **CORRECTION 2026-09-12 (D-KWDRAIN batch 4): ONE OF THE TWO LEVERS BELOW
      DOES NOT EXIST.** The sentence "both levers exist" was filed without checking
      the first one. [`tools/tier_table.py`](../../tools/tier_table.py)'s own docstring calls
      the per-gate-row `subject:` tag *"the `subject:` tag per gate row that step (c)
      WILL add"*, and a sweep of `probes/` finds **zero** such tags — every hit for
      "subject:" is the English word in prose ([measured](../../scratchpad/kwdrain_levers.out)).
      So `kwsweep` rows are the ONLY working attribution path today
      [[a-justification-parenthesis-is-an-unrun-claim]].
      🎯 **AND THAT CEILING IS REAL, NOT COSMETIC.** `WIDTH` has an entire dedicated
      suite ([`probes/basic/basic_probe_width.py`](../../probes/basic/basic_probe_width.py))
      and still reads as "no known gap", because nothing connects a suite that SCORES
      a keyword to the keyword it scores. Same for the graphics verbs and the input
      devices, which have suites of their own.
      ⚠️ **DO NOT REACH FOR "IS IT TYPED SOMEWHERE" TO CLOSE THAT GAP** — re-measured
      2026-09-12 and it is ~100 %: **all 68** of the then-remaining "no known gap"
      words are typed by at least one probe (`ON` by 131 of them, `RUN` by 107,
      `SCREEN` by 81). The parked per-keyword-table block had already measured exactly
      this and concluded it means nothing; the re-measurement only confirms the
      denominator is worthless for attribution [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      ➡️ **SO THE DRAIN HAS A STRUCTURAL CEILING, and the remaining words are the ones
      above it:** display verbs (`CLS` `SCREEN` `COLOR` `WIDTH` `KEY`) cannot take a
      kwsweep row at all, because the sweep anchors on the echoed command and they
      destroy that anchor; `GOSUB`/`RETURN`/`ON`/`CONT` need MULTI-LINE programs the
      row format cannot express; `WAIT` needs a non-blocking port that does not exist
      safely (batch 3). Finishing those needs **step (c)** — a `subject:` tag that lets
      an existing suite claim its keyword — which is now the highest-value apparatus
      work this order implies, and it is apparatus that BLOCKS the order itself.
      ➡️ **THE LEVER THAT DOES EXIST is the runtime keyword-coverage capture**
      — ~~`subject:` tags on gate rows~~ (step (c), NOT BUILT, see the correction
      above), and the runtime keyword-coverage capture (`ZEROBAS_KWCOVER` in
      [`probes/lib/omsx_repl.py`](../../probes/lib/omsx_repl.py) +
      [`tools/kwcover.py`](../../tools/kwcover.py), `make kwcover`), which says which
      suites TYPE each keyword. 🔴 **EXERCISED IS NOT VERIFIED** — a keyword a suite
      merely types is not one any row SCORES, so the capture picks the suites and a
      mutation sweep per keyword is what actually converts the row. Never quote the
      remaining count from here: `make tiers ARGS=--keywords`.
      🟢 **BATCH 1 DRAINED 2026-09-12 (D-KWDRAIN): "no known gap" 114 -> 88**, with
      kwsweep evidence 33 -> 59 keyword(s)
      ([readings](../../scratchpad/kwdrain_batch1.out)). Twenty-six converted from
      unattributed to SCORED-against-the-reference — `ASC CINT CDBL CSNG FIX SGN SIN
      COS TAN ATN EXP LOG MOD NOT AND OR XOR OCT$ LEFT$ RIGHT$ STR$ STRING$ SPACE$
      LET REM CSRLIN` — as rows in
      [`probes/basic/basic_probe_kwsweep.py`](../../probes/basic/basic_probe_kwsweep.py),
      each printing a value the reference must match. 🔴 **THEY ARE DELIBERATELY NOT
      "control" ROWS**: a control that comes back unsupported means the APPARATUS is
      lying and voids the whole run, so a word under test has to read as a FINDING
      instead. Battery 128/128 after.
      🎯 **THE DRAIN RE-FOUND TWO ADJUDICATED CORNERS ON ITS FIRST RUN**, which is the
      apparatus working: raw `ATN(1)` and `EXP(1)` rows came back DIVERGENT, and both
      are already CLOSED by D-MATHACC
      ([`docs/spec-basic-mathacc.md`](../../docs/spec-basic-mathacc.md)) as last-digit ulp
      differences in which **zerobas is the MORE accurate side** (`EXP(1)` at −0.5 ulp
      against the reference's −2.5). Left raw they would have planted two permanently
      red rows in a summary people are meant to read, so both now score
      `INT(f(x)*1000)` — a stub still fails them, and a decided corner is not
      re-litigated every run.
      🔴 **AND ONE REAL ATTRIBUTION HOLE, WORTH MORE THAN THE COUNT: `CSRLIN` HAD A
      MEASURED DIVERGENCE THAT THE TABLE COUNTED AS NOTHING.** Its kwsweep row reads
      `DIVERGENT ref '[ 4 ]' vs zb '[ 3 ]'`, but the row is scored WEAK and
      [`tools/tier_table.py`](../../tools/tier_table.py)'s `kwsweep_evidence` EXCLUDES weak
      rows — so the keyword sat in "no known gap" with a divergence already on the
      record [[an-unnamed-outcome-reads-as-no-outcome]]. The divergence is an artifact
      of absolute cursor geometry against the echoed prompt, not a defect (the weak
      row's own note records CSRLIN measured CORRECT on 2026-09-07, D-WAITGAP), so the
      new row reads the DELTA across two PRINTs — what all three machines agree on,
      and what a stub still fails at 0.
      ⚠️ **SO "WEAK" IS A SECOND WAY A ROW CAN BE INVISIBLE**, alongside a blank
      reading: worth a sweep of every weak row for a hidden verdict. The other one
      today is `time`, SUPPORTED, nothing owed.
      🟢 **BATCH 2, 2026-09-12: 88 -> 76**, kwsweep evidence 59 -> 71, twelve more
      converted — `RND CVI USING THEN ELSE TO STEP OFF IF NEXT CLEAR DIM`
      ([readings](../../scratchpad/kwdrain_batch2.out)). Battery 128/128 after.
      🔴 **THE SYNTAX PARTICLES COULD NEVER HAVE BEEN ATTRIBUTED ON THE OBVIOUS
      SPELLING.** `tools/tier_table.py` credits a row to the FIRST keyword token in
      its CRUNCH body, and `THEN` `ELSE` `TO` `STEP` `OFF` `USING` can never be first
      in valid BASIC — so however well they work they would have sat in "no known
      gap" for ever, a hole in the ATTRIBUTION MECHANISM rather than in the ROM. The
      crunch body is crunched and NEVER EXECUTED (the probe's own header contract), so
      these rows put the particle first there — which is exactly what Layer 1 tests,
      that the word tokenises — while the exec line drives it in real syntax.
      🔴 **AND `CVI` WALKED STRAIGHT INTO THE PROBE'S OWN DOCUMENTED TRAP.** Written
      untagged it came back `EXTRA` — ref `Illegal function call` vs zb `[ 7 ]` —
      which is precisely the mis-attribution
      [`basic_probe_kwsweep.py`](../../probes/basic/basic_probe_kwsweep.py)'s header
      describes: a DISKLESS VG-8020 measured against zerobas's disk-equipped build,
      with the difference blamed on zerobas. The rest of the MK/CV family was already
      tagged `NEEDS-DISK:`; that row simply had not been. Tagged, it matches.
      🟢 **THAT ALSO FALSIFIED THE PROBE'S OWN STATUS NOTE, now corrected**: it said
      NEEDS-DISK rows report `NO-ORACLE` because the CF-3300 capture was unreadable
      (STATUS 2026-07-26). The oracle READS — `mki` `mks` `mkd` `cvs` `cvd` and the
      new `cvi` all return real verdicts [[a-fix-falsifies-the-justification-beside-it]].
      🟢 **BATCH 3, 2026-09-12: 76 -> 68**, evidence 71 -> 79, eight converted —
      `BEEP SOUND VPEEK VPOKE VDP INP OUT POKE`
      ([readings](../../scratchpad/kwdrain_batch3.out)). Battery 128/128 after. Every write
      aims at a harmless target (VRAM 0 is character 0's glyph, `OUT &HA0` selects a
      PSG register without writing one, `SOUND 7,255` is the mixer with all channels
      OFF, the POKE goes to $E000 inside zerobas's own RAM) and reads back what it
      wrote where it can, so a stub that silently ACCEPTS the statement still fails.
      🔴 **AND ONE ROW I WROTE WAS WRONG, NOT THE ROM — WORTH MORE THAN THE EIGHT.**
      `WAIT &HA9,0:PRINT"[9]"` came back DIVERGENT with zerobas printing nothing, and
      that was zerobas behaving CORRECTLY: `WAIT port,mask[,xor]` blocks until
      `((INP(port) XOR xor) AND mask) <> 0`, so a mask of 0 can NEVER be satisfied and
      the row blocks for ever BY DEFINITION. I had read mask 0 as "already true". The
      row is REMOVED and the reason filed where it would have gone.
      ⚠️ **SO `WAIT` STAYS UNATTRIBUTED ON PURPOSE**: the only obvious non-blocking
      port is the VDP status register, whose bit 7 sets every frame but which is
      READ-TO-CLEAR and would disturb the BIOS interrupt handler. "No known gap" is
      the honest state for it until a safe row exists — better than a row that passes
      for the wrong reason [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      ~~⚠️ `CLS` `SCREEN` `COLOR` `WIDTH` WERE HELD BACK DELIBERATELY: this sweep
      anchors its capture on the ECHOED COMMAND … They need their own handling~~
      🔴 **RETRACTED 2026-09-12 (step 4a) — THAT WAS THE ANCHOR'S LIMIT, NOT THE
      WORDS'.** Batch 3 filed it as "these words cannot take a kwsweep row at all",
      and batch 4 repeated it as a structural ceiling. Both were wrong: the `arrays`
      and `deffn` suites have ALWAYS run `CLS:PRINT"[";…` and read the bracketed
      marker straight off the screen. `marker_tail` in
      [`basic_probe_kwsweep.py`](../../probes/basic/basic_probe_kwsweep.py) now captures
      from a unique per-row marker (note prefix `NOECHO:<tag>`; a stale screen reads
      `?nomarker`, a REFUSAL rather than a pass), and **`CLS` `WIDTH` `COLOR` are
      attributed: 68 -> 65**, evidence 79 -> 82
      ([readings](../../scratchpad/kwdrain_step4a.out)). Battery 128/128.
      🔴 **TWO THINGS COST A ROW EACH TO GET RIGHT.** (1) FIRST-MATCH WAS WRONG: the
      exec line PRINTS the marker, so the marker text also sits in the ECHOED
      COMMAND — on the side whose echo survives (`WIDTH 37` reformats but does not
      clear on the reference) first-match captured command+answer while the other
      captured the answer alone, and the row read DIVERGENT with **both sides having
      printed `[W 37 ]`**. `marker_tail` takes the LAST matching row, because output
      always follows the echo. (2) MY FIRST `CLS` ROW SCORED THE PARSE, NOT THE
      BEHAVIOUR — a bare `[C1]` that a `CLS` doing nothing would print just as
      happily; it now reads `CSRLIN` back (the cursor is home after a real clear),
      and `COLOR` uses 7 rather than the DEFAULT 15 for exactly the same reason
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      ⚠️ **`SCREEN` AND `KEY` ARE DEFERRED WITH REASONS, not overlooked**: `SCREEN`'s
      only discriminating value is a MODE CHANGE, and `SCREEN 1` is 32 columns while
      this capture parses a 40-column screen — the row would break the reader it
      depends on. `KEY`'s natural readback is `FNKSTR`, which is **not in
      `basic/sysvars.inc`**; guessing the standard `$F87F` would be building on an
      unverified constant [[a-derived-constant-falsified-from-another-file]].
      🔴 **STEP 4b, AND ITS RESULT IS A ROW I DELETED.** A `keykw` row reading
      `CRTCNT` after `KEY OFF` came back **SUPPORTED / match on BOTH machines and was
      BLIND**: measured directly
      ([`scratchpad/kwdrain_keyblind.py`](../../scratchpad/kwdrain_keyblind.py),
      [readings](../../scratchpad/kwdrain_keyblind.out)), `CRTCNT` reads **24 with `KEY OFF`
      and 24 without**, on zerobas and the VG-8020 alike — so a `KEY` that parsed and
      did nothing would have passed it identically. **A GREEN VERDICT IS NOT EVIDENCE
      THAT THE READBACK MOVES.** The row is removed, the measurement filed in its
      place, and `KEY` stays unattributed until `FNKSTR` is settled.
      🎯 **SO THE CHECK BECAME THE STANDARD, AND IT IMMEDIATELY CAUGHT A SECOND ROW.**
      Every readback is now proved to move before the row is kept
      ([`scratchpad/kwdrain_discrim.py`](../../scratchpad/kwdrain_discrim.py)): `WIDTH`'s
      `LINLEN` 39 -> 37, `COLOR`'s `FORCLR` 15 -> 7, `CLS`'s `CSRLIN` 6 -> 0 — those
      three stand. But batch 3's `INP` row asked `INP(&HA8)>=0`, **which an ABSENT
      `INP` passes too**: the word parses as an undefined array, the call becomes
      element 0, and `0>=0` is TRUE. Measured
      ([`scratchpad/kwdrain_boolcheck.py`](../../scratchpad/kwdrain_boolcheck.py)):
      `INP(&HA8)` reads 240 and the stub shape reads **-1, identical to the real
      answer**. Changed to `>0`, which the stub fails at 0. `VDP` was checked the same
      way and is sound as written (240 against the stub's 0).
      ⚠️ **THE LESSON GENERALISES BEYOND THIS SWEEP:** a BOOLEAN row whose predicate
      is true of ZERO cannot see a missing keyword, because a missing keyword IS zero
      here [[a-case-that-agrees-can-agree-for-the-wrong-reason]] [[readout-blind-to-its-own-subject]].
      🟢 **STEP 4c: THE GRAPHICS VERBS ARE REACHABLE — 65 -> 61**, evidence 82 -> 86,
      `PSET PRESET POINT LINE` attributed. Two things had to combine: the echo-free
      capture (SCREEN 0/2 destroys the echo) and doing the READBACK BEFORE returning
      to text mode, because a SCREEN 2 screen cannot be read as 40-column text at
      all — so each row draws, reads `POINT` into a variable, returns to `SCREEN 0`
      and only then prints its marker.
      🎯 **READBACK MEASURED FIRST, as the standard now requires**
      ([`scratchpad/kwdrain_gfxcheck.py`](../../scratchpad/kwdrain_gfxcheck.py),
      [readings](../../scratchpad/kwdrain_gfxcheck.out), both machines agreeing): `POINT`
      reads **4** on a blank SCREEN 2, **15** after `PSET ,15`, and **4** again after
      `PRESET`; `LINE`'s row reads a pixel in the MIDDLE of the span and gets 15, so
      an endpoint-only LINE would fail it too. Each row moves when its own verb stops
      working rather than passing on a value that was already there.
      ⚠️ **`PSET` AND `POINT` ARE COUPLED and the rows say so**: `POINT` can only read
      what something drew, so `pointkw` moves if EITHER breaks. It still earns a row —
      a `POINT` that parses as an array reads 0, which neither 4 nor 15 can be.
      🟢 **STEP 4d: 61 -> 58**, evidence 86 -> 89 — `CIRCLE DRAW BASE SPRITE`
      ([readings](../../scratchpad/kwdrain_gfx2.out)). Measuring each readback BEFORE
      writing the row changed two of them, which is the whole point of the standard:
      🔴 **`BASE(0)` READS 0 — EXACTLY WHAT A STUB RETURNS**, so the obvious argument
      would have produced a blind row; the row uses `BASE(2)` (2048, and `BASE(10)`
      is 6144). And `CIRCLE`'s row reads the RIM at 15 while the CENTRE reads 4, so it
      sees a real circle rather than a filled blob.
      🟢 **`SPRITE`'s NO-OUTPUT WAS DIAGNOSED, NOT GUESSED AT**
      ([`scratchpad/kwdrain_spritechk.py`](../../scratchpad/kwdrain_spritechk.py)):
      `SPRITE$(0)=…` raises **Illegal function call in SCREEN 0** — sprites need a
      graphics screen — which is why the first form printed nothing on BOTH machines
      and looked like a broken probe. In SCREEN 2 the round-trip works (`ASC` 255,
      `LEN` 8), so the row writes the pattern to VRAM and reads it back and moves if
      either half breaks.
      🔴 **AND A THIRD SILENT-FAILURE MODE: A ROW CAN REPORT `SUPPORTED` AND CREDIT
      NOTHING.** The `SPRITE` row's crunch was `sprite$(0)="x"`, and
      [`tools/tier_table.py`](../../tools/tier_table.py)'s `WORD` regex KEEPS a trailing `$`
      (so `STR$`/`MID$` match) — which tokenises it to `SPRITE$`, while the kwtable
      keyword is `SPRITE`. The row went green, the keyword stayed in "no known gap",
      and **the only signal was the evidence count rising by three when four rows went
      in**. Crunch changed to `sprite on`; 58 -> 57, evidence 89 -> 90.
      🎯 **AUDITED RATHER THAN ASSUMED:** every one of the **94** rows now in the pin
      was checked through `stmt_keyword` — **0 credit no keyword**, so `SPRITE` was
      the only one. The check is three lines and belongs in the probe's own selftest
      if this happens again.
      🟢 **STEP 4e: 57 -> 52**, evidence 90 -> 95 — `GOSUB RETURN END READ RESTORE`.
      🔴 **AND THE "MULTI-LINE" BLOCKER WAS NEVER REAL EITHER**, which is the second
      ceiling this drain has talked itself into and then measured away.
      `omsx_repl.as_stored` SPLITS a `:`-joined exec into numbered lines 10/20/…,
      packing statements greedily into ≤34-char bodies — so a "one-line" row is
      already a multi-line program, and these words needed the line numbers worked
      out rather than a new mechanism. Verified by printing the packing BEFORE writing
      a row and then running it
      ([`scratchpad/kwdrain_multiline.py`](../../scratchpad/kwdrain_multiline.py),
      [readings](../../scratchpad/kwdrain_multiline.out), both machines):
      `A=0:GOSUB 20:…:END:A=7:RETURN` packs to `10 A=0:GOSUB 20:PRINT…:END` /
      `20 A=7:RETURN` and answers 7.
      🎯 **A CONTROL IS WHAT MAKES THE `RESTORE` ROW MEAN ANYTHING**: a single `READ Q`
      answers 3 and the row answers 6, so the second `READ` really did re-read the
      same `DATA` — which is only true if `RESTORE` reset the pointer. Without that
      control the row would pass on any two reads.
      ⚠️ **`ON` IS NOT THERE**: its two-target form packs badly — the greedy packer
      swallows both subroutines into line 20 — and padding statements to force a
      boundary would make the row about the PACKER instead of the keyword.
      🎯 **AUDIT RE-RUN: 99 pin rows, 0 crediting no keyword.**
      🟢 **STEP 4f: 52 -> 46**, evidence 95 -> 101 — `ON ERROR ERR ERL RESUME DEFINT`.
      Four of them come off ONE program: line 10 arms the handler and raises, line 20
      reports, and **`ERR` reads 7 while `ERL` reads 10**
      ([`scratchpad/kwdrain_errhand.py`](../../scratchpad/kwdrain_errhand.py),
      [readings](../../scratchpad/kwdrain_errhand.out), both machines) — so the row carries
      the CODE and the LINE, not merely "something was trapped".
      🎯 **`RESUME` NEEDED ITS OWN PROGRAM AND THE PACKER CHOSE ITS SHAPE**: the greedy
      split leaves the handler alone on line 30 as `RESUME NEXT`, which resumes at the
      statement after the one that raised — the PRINT on line 20. The row prints at
      all ONLY because RESUME returned control. `DEFINT`'s row asserts **1, not 1.7**,
      so it sees the COERCION rather than the parse.
      🔴 **AND THE AUDIT TOOL ITSELF WAS WRONG, which is worth more than the six.** The
      earlier "0 rows credit no keyword" was computed with an ad-hoc regex over
      `kwtable.inc` that admitted **`A`** as a keyword — so `a=err` looked like it
      credited `A`, and a genuinely uncreditable row was hidden behind the same false
      positive. Re-run through the table's OWN loader
      (`tier_table.kwtable_keywords()`): 105 rows, **exactly one** credits nothing —
      `swapctl`, stmt `a=1`, which is the pre-existing *"control (bare assign)"* row
      and is SUPPOSED to name no keyword. 101 distinct keywords credited.
      ⚠️ **THE RULE: AUDIT WITH THE CONSUMER'S OWN PARSER, NEVER A RE-IMPLEMENTATION**
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      🟢 **STEP 4g: 46 -> 44**, evidence 101 -> 103 — `MAX` and `STRIG`, **both of
      which separate through an ERROR**, which is still a differential
      ([`scratchpad/kwdrain_misc1.py`](../../scratchpad/kwdrain_misc1.py),
      [readings](../../scratchpad/kwdrain_misc1.out), both machines): bare `MAX` is a
      Syntax error on a real machine and prints `0` on a stub, so the row proves the
      word is TOKENISED rather than parsed as a name; `STRIG(5)` is out of the 0..4
      range and raises Illegal function call, while an undefined array `STRIG(5)`
      auto-dims and answers 0.
      ⚠️ **AND THREE THAT DO NOT SEPARATE, left unattributed rather than papered
      over:** `LPOS(0)` reads 0 and a stub reads 0; **`LPRINT` produced NO OUTPUT AT
      ALL on both machines** (no printer attached), so neither can be scored from
      here; and `LEN(INKEY$)` is 0 with no key pressed, which is exactly what a stub
      returns — `INKEY$` needs INJECTED KEYSTROKES, not a cleverer expression.
      🟢 **STEP 4h: `PAD` `ATTR$` `STOP` attributed, and `NEW` CONVERTED INTO A TIER 1
      DEFECT** — the first time this drain has produced a filed bug rather than a
      retirement, which is exactly what the order asked for. `ATTR$` settles an open
      question on the way: bare use raises **Illegal function call**, not a Syntax
      error, so it IS an MSX1 BASIC token here.
      ⚠️ **`PDL` IS STILL OUT and the reason is recorded**: `PDL(13)` raises Illegal
      function call, but the STUB shape errors there too (subscript out of range), so
      the two separate only by error PHRASE. `PDL(0)` should separate cleanly —
      measure before writing the row.
      🟢 **STEP 4i: 40 -> 39**, evidence 106 -> 107 — and the interesting part is WHY
      `NEW` needed a row AFTER its defect was fixed.
      🔴 **A FIX SILENTLY UN-ATTRIBUTES ITS OWN KEYWORD.** Attribution comes from
      **OPEN** items, so the moment D-NEWSTMT was closed, `NEW` fell straight back
      into "no known gap" — the table cannot tell *"investigated, fixed, and now
      correct"* from *"nobody ever looked"*. A kwsweep row is what HOLDS the ground a
      fix won, and `newkw` now carries the defect's own shape: `PRINT"[A]":NEW`, which
      before the fix would have read `Syntax error in 10` on the zb side.
      ⚠️ **THIS APPLIES TO EVERY DEFECT THIS DRAIN EVER CLOSES**, so closing an item
      without leaving a row behind quietly gives the keyword back to the unattributed
      pile [[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]].
      🎯 **AND THE PROGRAM-VERB SWEEP FOUND D-NEWSTMT WAS NOT A CLASS**
      ([readings](../../scratchpad/kwdrain_progverbs.out)): `LIST` in a program lists
      identically, `DELETE 99` raises `Illegal function call in 10` on both,
      `RENUM`/`AUTO` behave alike — every other program verb already had its
      `stmt_table` entry. `NEW` was the only one reachable solely from
      `dispatch_line`'s pre-tokenise match. The sweep did surface `CONT`'s missing
      line number, filed separately as TIER 5.
      🟢 **STEP 4j: 39 -> 37**, evidence 107 -> 109 — `LIST` and `DELETE`, written
      from shapes the D-NEWSTMT sweep had ALREADY measured on both machines rather
      than guessed.
      🔴 **AND A FIFTH FAILURE MODE, THE WORST SO FAR: A ROW THAT DAMAGES EVERY ROW
      AFTER IT.** An `AUTO` row scored the verb correctly — both machines print `[A]`
      then the `10*` line-entry prompt — but **`AUTO` leaves the machine IN
      line-entry mode**, so it swallowed the input of the cases that followed: the
      sweep went from 0 divergent to **DIVERGENT=22 + UNREADABLE=1**, twenty-one of
      them pure collateral. Removed, and the reason filed where the row was.
      **A row is not free of the session it runs in**
      [[apparatus-is-part-of-the-measurement]]. Attributing `AUTO` needs a form that
      EXITS line-entry mode, or a case of its own at the END of the sweep.
      ⚠️ **`LLIST` AND `RENUM` GET NO ROW EITHER, and agreeing with the reference is
      not the reason — being SEEN is:** `LLIST` prints only `[A]` on both (the printer
      output goes to the log, not the screen), so an LLIST that did nothing would pass
      too; and `RENUM` in a ONE-LINE program renumbers 10 to 10, which changes nothing
      observable — it needs a two-line program and a `LIST` read-back.
      🟢 **STEP 4k: `PDL` attributed** — and the row uses the VALUE, not the error:
      `PDL(0)` is out of range and raises Illegal function call while a stub answers
      0, which WOULD separate, but `PDL(1)` reads **255 on both machines** against a
      stub's 0, and a value differential says more than an error one
      ([`scratchpad/kwdrain_pdlchk.py`](../../scratchpad/kwdrain_pdlchk.py)).
      🔴 **AND `INKEY$` / `INPUT` / `GET` ARE NOT BLOCKED BY THE MACHINE — THEY ARE
      BLOCKED BY THE ROW FORMAT.** The harness HAS a race-immune key injector
      (`omsx_repl.key_proc()`, which writes at `GETPNT` and never moves it,
      documented against the D-LATCH delivery race and measured 100% -> 0%), and
      `basic_probe_key_trap.py` / `basic_probe_interval_trap.py` both drive it. But it
      arrives as a PROLOGUE plus an `after time` schedule, and a kwsweep row has no
      per-row prologue hook. So attributing them needs that hook, not a cleverer
      expression — a smaller and much better-defined job than step (c).
      ⚠️ **`RENUM` STAYS OUT for a reason measured this tick too**: it STOPS the
      program (both machines print `[A]` then `Ok`), so a trailing `LIST` in the same
      stored run never executes and the renumbering cannot be read back from inside
      one case.
      🎯 **WHERE THE DRAIN NOW STANDS, AND WHY IT SLOWS: 114 -> 36 (2026-09-12), and
      EVERY REMAINING WORD IS BLOCKED BY A NAMED PIECE OF APPARATUS, not by a missing
      idea.** The read-only disk verbs were measured this tick
      ([`scratchpad/kwdrain_diskchk.py`](../../scratchpad/kwdrain_diskchk.py),
      [readings](../../scratchpad/kwdrain_diskchk.out)) and none separate as written:
      **`DSKF(0)` reads 0 — exactly what a stub reads** (no disk is inserted, so the
      honest answer coincides with the blind one), `LOF`/`LOC`/`EOF` produce nothing
      without an open file, and `CLOSE` prints whether or not it does anything.
      | what is left | what unblocks it |
      |---|---|
      | `INKEY$` `INPUT` `GET` | ~~a per-row prologue hook~~ — **RE-ESTIMATED, see below** |
      | the tape/disk verbs | a rig with a MOUNTED disk of known contents that can absorb a write |
      | `LLIST` `LPOS` `LPRINT` | a reader for the PRINTER LOG (the output never reaches the screen) |
      | `AUTO` | a case slot that survives line-entry mode, or last position in the sweep |
      | `RENUM` | a read-back the stored-row format cannot express (RENUM stops the program) |
      | `USR` `CALL` | machine code to call |
      | `SCREEN` `KEY` `WAIT` | filed reasons above, each measured |
      | the suites that ALREADY score a keyword | **step (c)** |
      🔴 **CORRECTION 2026-09-12: "THE PER-ROW PROLOGUE HOOK IS THE SMALLEST BY A
      WIDE MARGIN" WAS WRONG, and I filed it before reading how injection is timed.**
      Two things kill that estimate. (1) `run_cases`'s `prologue` is documented as
      *"raw Tcl run ONCE, IMMEDIATELY, before the timeline is scheduled"* — it is the
      seam for `plug joyporta paddle`, NOT for timed input. (2)
      [`basic_probe_key_trap.py`](../../probes/basic/basic_probe_key_trap.py) does not use
      `run_cases` AT ALL: it builds its own complete Tcl schedule, enters the program
      by injection, and times events at `run_done + dt`. A key has to arrive AFTER the
      machine has consumed `RUN` and BEFORE the statement reads it, and that moment is
      computed inside `run_cases` from `boot` + per-line `step` — which a row cannot
      see. So this is a HARNESS change (expose or drive the per-case run time), not a
      row-format change, and the D-LATCH/D-LATCH2 races are exactly what it must not
      reopen.
      ⚠️ **SO THE CHEAP HALF OF JOOST'S ORDER IS DONE AND THE REST IS APPARATUS OF
      COMPARABLE SIZE.** None of the eight blockers is obviously smallest any more;
      they should be RANKED against TIER-4 speed work rather than picked by which one
      I happened to look at first.
      ➡️ **STEP (c) IS STILL NOT BUILT AND IS STILL THE CEILING** for words no
      kwsweep row can reach — but it is now a SMALLER set than batch 4 claimed, and
      its real cost is on the record: a `subject:` tag must mean *"a row whose verdict
      MOVES when this keyword breaks"*, and proving that per keyword is a mutation +
      rebuild + full battery, ~15 minutes each.
      ➡️ **NEXT BATCHES, cheapest context first:** the remaining pure/near-pure words
      (`RND` `MAX` `CVI` `LSET` `RSET` `POINT` `USING` `THEN` `ELSE` `TO` `STEP` `OFF`),
      then statement-shaped ones (`IF` `ON` `GOSUB` `RETURN` `NEXT` `READ` `RESTORE`
      `END` `STOP` `NEW` `RUN` `LIST` `DELETE` `RENUM` `AUTO` `CLEAR` `DIM` `LET`),
      then console/VDP (`CLS` `COLOR` `SCREEN` `WIDTH` `KEY` `BEEP` `SOUND` `VPEEK`
      `VPOKE` `VDP` `INP` `OUT` `WAIT` `POKE` `PSET` `PRESET` `LINE` `CIRCLE` `DRAW`
      `SPRITE` `BASE` `ATTR$` `PAD` `PDL` `STRIG` `SET`), and the tape/disk verbs LAST
      because they need a rig that can absorb a write.
      🔴 **SHARPENED AGAIN (Joost, 2026-09-12): "THE NO KNOWN GAP SHOULD BE ALL
      RESOLVED FIRST — HOW CAN WE PRIORITIZE PROPERLY WITHOUT THAT."** This
      OUTRANKS the TIER 4 speed items, and the reasoning is the queue's own: a
      keyword with no evidence can hide a TIER 1 defect, and one just DID —
      `NEW` came out of this list and was a happy-path failure. Ranking speed work
      above an unmeasured surface ranks against a number nobody can trust. So the
      drain runs to ZERO before TIER 4 is picked up again.
      🟢 **AND TWO OF THE NAMED BLOCKERS ARE ALREADY DEAD — MEASURED 2026-09-12,
      not argued.** (1) The `NO-ORACLE (5)` bullet in the TIER 1 keyword item says
      the CF-3300 gives no readable capture: `build/kwsweep-verdicts.json` now
      reports `mki` `mks` `mkd` `cvs` `cvd` — and the `cvi` row added this session —
      all **SUPPORTED** against that very machine. (2) **The disk fixture EXISTS and
      is wired**: `DISK_TEST_DSK := disk/test720.dsk`, generated by
      [`tools/make_test_dsk.py`](../../tools/make_test_dsk.py), mounted through
      `probe_sides.diska()` (which returns None for a driveless side rather than
      raising), already used by `ramfree-acceptance`, and guarded by
      `diskdep-check`. Its contents are purpose-built: `TEST.BIN` is exactly two
      clusters with a record hop and a cluster-chain EOF, plus `HI.TXT`,
      `PROG.BIN` (a real BSAVE binary) and `PROG.BAS`/`PROG2.BAS`.
      ➡️ **SO THE ~23 DISK AND TAPE WORDS ARE NOT BLOCKED ON BUILDING ANYTHING** —
      they are blocked on `basic_probe_kwsweep.py` NOT MOUNTING THE IMAGE (it names
      neither `diska` nor `DISK_TEST_DSK` today). That is the next slice, and it is
      threading an existing fixture into an existing probe, not new apparatus.
      🟢 **D-KWDISK, 2026-09-12: 36 -> 16, evidence 110 -> 130 — TWENTY WORDS, AND
      THE WHOLE SLICE WAS MOUNTING A FIXTURE THAT WAS ALREADY THERE.**
      `DSKF BLOAD BSAVE CLOSE CMD COPY DSKI$ DSKO$ EOF FILES IPL KILL LOC LOF LSET
      MERGE RSET RUN SAVE SET` ([readings](../../scratchpad/kwdisk_full.out), full sweep;
      [the new rows alone](../../scratchpad/kwdisk_only.out)).
      [`basic_probe_kwsweep.py`](../../probes/basic/basic_probe_kwsweep.py) now mounts a
      WRITABLE PRIVATE COPY of `disk/test720.dsk` on BOTH sides for the NEEDS-DISK
      group, and `make kwsweep` declares `$(DISK_TEST_DSK)` (`diskdep-check` green,
      74/74).
      🔴 **AND THE FIRST RUN PAID FOR ITSELF WITH TWO TIER 1 DEFECTS**, filed above:
      `MERGE` inside a program carries on here and returns to command level on the
      reference, and `FILES` ends its listing with a newline the reference does not
      emit. Both were invisible while the drive was empty — which is the whole
      argument for Joost's ruling.
      🔴 **`DSKF(0)` READING 0 WAS NEVER A STUB READING — IT WAS AN EMPTY DRIVE.**
      Batch 4 filed *"`DSKF(0)` reads 0 — exactly what a stub reads (no disk is
      inserted, so the honest answer coincides with the blind one)"* and drew the
      conclusion that the read-only disk verbs do not separate. With the image in,
      `DSKF(1)` reads **707**. The parenthesis named the cause and the conclusion
      still went the wrong way [[a-justification-parenthesis-is-an-unrun-claim]].
      🔴 **THE CAPTURE GAP IS PART OF THE MEASUREMENT, AND ITS FAILURE LOOKS LIKE A
      REFUSAL.** At the shared default (`cap_gap` 2.5) every WRITING row came back
      BLANK on the CF-3300 — no marker, no error, no prompt — which reads as *"the
      reference declines this verb"* and would have published five divergences that
      are pure apparatus. A real FAT write simply takes longer than the capture
      waited. Measured: 8 still blanks all five, 12/3.5 answers, 20/5 is what shipped,
      and the cost is EMULATED time, not wall time
      ([readings](../../scratchpad/kwdrain_diskslow.out)) [[apparatus-is-part-of-the-measurement]].
      🎯 **TWO CANDIDATE ROWS WERE THROWN AWAY FOR BEING BLIND, which is the standard
      working rather than a near miss.** A `CLOSE` row that reopened channel 1 passed
      WITHOUT the close (zerobas lets #1 be reopened, so the readback never moved); it
      became the FLUSH instead — 6 bytes are on the disk only because the channel was
      closed, and the same row without it measures 0. And a `FILES` row reading
      `CSRLIN` read 1 on zerobas and 0 on the CF-3300 *because the CF-3300 shows the
      function-key line and its screen is a row shorter* — the MACHINES, not the verb
      [[readout-blind-to-its-own-subject]]. (The row that replaced it found the real
      divergence, on the row BOUNDARY rather than the text.)
      🔴 **A DIRECT-MODE `BLOAD` EATS THE REST OF ITS LINE**, measured — the readback
      after it printed nothing at all, on both machines — so those rows are
      `mode="stored"` with the readback on a LATER numbered line, and `as_stored`'s
      packing was printed before each row was written rather than assumed.
      🎯 **`RUN` CAME OUT OF THE SAME BATCH AND NEEDS NO DISK AT ALL.** It sat in the
      list because RUN CLEARS VARIABLES, so no expression can carry a count across the
      restart: the flag has to live in RAM. `POKE`ing the cell next to the one
      `pokekw` already uses, `RUN <line>` re-enters and the second pass prints 2 where
      a RUN that did nothing prints 1.
      🎯 **AUDIT RE-RUN THROUGH THE CONSUMER'S OWN PARSER: 134 pin rows, exactly ONE
      credits no keyword** (`swapctl`, the intentional bare-assign control), **130
      distinct keywords credited.** And the WHOLE sweep summary was read, not just the
      new verdicts: `DIVERGENT=2 SUPPORTED=130`, no collateral — the `AUTO` lesson
      checked rather than remembered.
      ➡️ **WHAT IS LEFT IS 16 WORDS AND FIVE BLOCKERS**: `INKEY$` `INPUT` `GET` (the
      harness timing change), `LLIST` `LPOS` `LPRINT` `LFILES` (a printer-log reader),
      `CLOAD` `CSAVE` (a tape rig), `AUTO` `RENUM` (line-entry mode / a read-back the
      row format cannot express), `KEY` `SCREEN` `WAIT` `CALL` `USR` (each with a
      filed, measured reason above). None is blocked on an idea; each is blocked on a
      named piece of apparatus, and the disk one has just been shown to be the kind
      that is already built.
      🟢 **D-KWRIG, 2026-09-12: 16 -> 10, evidence 130 -> 136 — `USR` `SCREEN` `KEY`
      `WAIT` `LPOS` `LPRINT`, and every one of the six had a FILED blocker that was
      stale** ([readings](../../scratchpad/kwrig_full.out), full sweep;
      [the new rows](../../scratchpad/kwrig_only.out)).
      🔴 **`SCREEN`: *"its only discriminating value is a MODE CHANGE, and SCREEN 1 is
      32 columns while this capture parses a 40-column screen — the row would break
      the reader it depends on."* True, and beside the point: nothing makes the row
      STAY in the mode. `SCRMOD` **is** declared (`$FCAF`, basic/sysvars.inc), so the
      row switches, reads 2, comes back to SCREEN 0 and prints — the shape the
      graphics rows have used since step 4c.
      🔴 **`KEY`: the FNKSTR reasoning was right and incomplete.** Guessing `$F87F`
      would still be an unverified constant; `KEY LIST` puts the definitions ON THE
      SCREEN and needs no constant at all. The ten defaults are byte-identical on both
      machines, so the only difference the row can show is the `ZZQ` it assigns
      itself.
      🔴 **`USR`: "machine code to call" — one POKEd `$C9` IS machine code.** A bare
      RET leaves DAC alone, so `USR(7)` returns 7 on both machines against the stub
      shape's 0.
      🔴 **`WAIT` IS BACK, AND BATCH 3'S OWN BLOCKING ROW IS NOW ITS CONTROL.**
      `WAIT p,m` returns when `INP(p) AND m` is non-zero, so the mask comes from a
      MEASURED port — `INP(&HA8)` reads 240 on zerobas AND the VG-8020 — and the row
      was PROVED to return before it existed
      ([`scratchpad/kwdrain_waitchk.py`](../../scratchpad/kwdrain_waitchk.py),
      [readings](../../scratchpad/kwdrain_waitchk.out)). Batch 3's `mask 0` form is the
      control in that same run and still returns NOTHING, which is what says the
      machine really blocks.
      ⚠️ **AND WHAT THE `WAIT` ROW CANNOT SEE IS SAID IN THE ROW**: a WAIT that parsed
      and returned immediately passes it. WAIT has no observable but blocking, so the
      row scores ABSENCE (a missing WAIT makes the statement a Syntax error) and the
      blocking is scored by a control that can never be a sweep row because it does
      not come back [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      🟢 **`LPOS`/`LPRINT`: the printer log was never needed for THESE two.** The
      filed blocker — *"a reader for the PRINTER LOG (the output never reaches the
      screen)"* — is true of the printed TEXT and false of the head COLUMN, which
      `LPOS(0)` returns to the screen. Batch 4g measured bare `LPOS(0)` as 0 against a
      stub's 0 and stopped there; the readback simply had to be MOVED first, and
      `LPRINT"ABC";` moves it to 3 on both machines
      ([`scratchpad/kwdrain_lptchk.py`](../../scratchpad/kwdrain_lptchk.py),
      [readings](../../scratchpad/kwdrain_lptchk.out)).
      🔴 **THE PRINTER IS A RIG, AND ITS ABSENCE IS A HANG, NOT A BLANK** — measured in
      the same run with the plug removed: both rows produce NO OUTPUT AT ALL on both
      machines. So `NEEDS-PRINTER:` joins `NEEDS-DISK:` as a row tag, the two capture
      splitters collapsed into ONE function (the subject side needs the same rig as
      the reference — two near-copies is how the sweep came to compare a reference
      holding a disk against a zerobas holding none), and `_row_rig` names what each
      row needs.
      ⚠️ **`LLIST` AND `LFILES` ARE NOT IN THIS BATCH and the reason is specific**:
      their subject IS the printed text, so they need the `screen_printer` capture
      ([`probes/basic/basic_probe_lptverb.py`](../../probes/basic/basic_probe_lptverb.py)
      already has it) plus boot-per-case, because the log ACCUMULATES and a batched
      row reads its predecessors' output as its own. That is the slice that should
      generalise `_row_rig` to a row needing BOTH tags, which `lfiles` will be the
      first to do.
      ➡️ **TEN LEFT: `AUTO` `CALL` `CLOAD` `CSAVE` `GET` `INKEY$` `INPUT` `LFILES`
      `LLIST` `RENUM`.** Three clusters, each with named apparatus: the printer LOG
      (`LLIST` `LFILES`), the TAPE rig (`CLOAD` `CSAVE` — and it EXISTS:
      `cassetteplayer new` + [`probes/lib/cas_decode.py`](../../probes/lib/cas_decode.py),
      driven by nine `basic_probe_cas*` suites, so re-verify that blocker too), and
      the key INJECTOR timing (`INKEY$` `INPUT` `GET`). `AUTO` and `RENUM` are the
      two that need a row FORMAT rather than a rig, and `CALL` needs an extension
      that is safe to invoke.
      🔴 **D-KWTAPE, 2026-09-12: THE FIRST BLOCKERS THAT SURVIVED RE-VERIFICATION —
      and the tick still produced a TIER 1 defect, filed above (`LFILES` does not
      zero `LPTPOS`).** Eleven blockers have been re-checked this session; these are
      the first two that held, and both hold for a reason that is now MEASURED rather
      than asserted.
      🔴 ~~**`CSAVE`: THE TAPE RIG EXISTS AND RECORDS; NOTHING IN THIS TREE PLAYS.**~~
      **RETRACTED 2026-09-13 — see the correction below; it plays, and the encoder
      exists.** The paragraph is kept because its OTHER half (the `TIME` finding)
      stands.**
      `cassetteplayer new` + [`probes/lib/cas_decode.py`](../../probes/lib/cas_decode.py)
      is a RECORDER — a grep for `cassetteplayer insert` across `probes/` finds
      nothing — so `CSAVE` can write a tape kwsweep cannot read, and `CLOAD` has no
      tape to read at all. A playable fixture (the cassette equivalent of
      `disk/test720.dsk`) would need a bytes→WAV encoder this tree does not have;
      `cas_decode` only goes the other way.
      🔴 **AND THE CHEAP IDEA THAT WOULD HAVE HIDDEN IT: `TIME` DOES NOT ADVANCE
      DURING A CASSETTE SAVE.** A save takes seconds of tape, so the obvious
      screen-visible readback is the JIFFY delta — measured, the delta is **4** for a
      recording of 269 280 WAV bytes (~6 s), because the tape write runs with
      INTERRUPTS OFF ([`scratchpad/kwdrain_tapechk.py`](../../scratchpad/kwdrain_tapechk.py),
      [readings](../../scratchpad/kwdrain_tapechk.out)). The control — the same row with no
      `CSAVE` — reads the same 0, so the row would have AGREED on both machines while
      seeing nothing [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      🔴 **`LLIST`: THE PROGRAM STOPS, so the statement after it never runs** — on
      BOTH machines, which is why the first attempt read `NONE` and looked like a
      broken probe. In DIRECT mode there is no program to list, so the log is empty
      for the opposite reason. Its printed output IS byte-identical on both (54 B,
      the same bytes), so the verb is fine; what it has no path to is a SCREEN
      readback. `LLIST` needs the `screen_printer` capture, and that conclusion is
      now a measurement rather than a guess.
      ⚠️ **THE `LPOS`-AFTER-THE-VERB TRICK WAS TRIED AND IS BLIND FOR `LFILES`** —
      and being blind is what UNCOVERED the defect: the row reads 2 on zerobas
      (unchanged) where it reads 0 on the CF-3300, which is not a blind row at all
      but a divergent one. The readback that could not score the keyword scored the
      machine instead.
      ➡️ **SO THE HONEST SHAPE OF WHAT IS LEFT** is: one capture (`screen_printer`,
      already written in
      [`probes/basic/basic_probe_lptverb.py`](../../probes/basic/basic_probe_lptverb.py))
      unlocks `LLIST` and `LFILES`; one ENCODER (bytes→WAV) plus a fixture unlocks
      `CLOAD`, and `CSAVE` needs the WAV read back; the key injector's timing unlocks
      `INKEY$` `INPUT` `GET`; `AUTO` and `RENUM` need a row FORMAT; `CALL` needs an
      extension that is safe to invoke. None of these is hidden any more.
      🟢 **D-KWLOG, 2026-09-13: `LLIST` ATTRIBUTED — and the blocker was a CAPTURE,
      not the hazard it was filed under** ([readings](../../scratchpad/kwlog_full.out),
      full sweep; [the row alone](../../scratchpad/kwlog_only.out)).
      🔴 **THE FILED REASON WAS "printer-bound with the known unplugged-`LSTOUT`
      hang hazard", AND THAT HAZARD IS REAL AND WAS NEVER THE BLOCKER.** The plug
      answers it (D-KWRIG). What kept `LLIST` unscored is that its ONLY output is
      the printer: the program STOPS at it on BOTH machines so nothing reaches the
      screen, and in direct mode there is no program to list — an empty log, for
      the opposite reason. Its printed bytes were IDENTICAL on both all along
      ([`scratchpad/kwdrain_llistchk.py`](../../scratchpad/kwdrain_llistchk.py),
      [readings](../../scratchpad/kwdrain_llistchk.out)).
      🟢 **`NEEDS-LOG:` IS THE THIRD RIG, and it is a CAPTURE rather than a
      device**: it implies the printer plug and then READS the log. `_row_rigs`
      was already a tuple (D-DFEND) and `lfiles` already proved the two-tag path,
      so the slice added a reading, not a mechanism.
      🔴 **IT FORCES BOOT-PER-CASE, AND THAT IS NOT A PREFERENCE.** openMSX holds
      the log open and never truncates it, so batched, every case captures the
      WHOLE log and each row reads its predecessors' output as its own — D-BATCH2
      measured exactly that on
      [`basic_probe_lptverb.py`](../../probes/basic/basic_probe_lptverb.py) and **both
      modes still exited 0**, so no exit status can catch it.
      🔴 **THE CLASS COMES FROM THE SCREEN AND ONLY THE TEXT FROM THE LOG**, and a
      row that scored the screen half would compare two blank screens and call it
      agreement. A missing keyword answers `Syntax error` on the SCREEN and prints
      nothing at all, which is the differential
      [[an-unnamed-outcome-reads-as-no-outcome]].
      🔴 **AND THE FIRST CUT READ `?noecho` ON BOTH SIDES**, because BOTH halves of
      a `screen_printer` capture are HEX — the screen half does not come back
      decoded the way a plain `screen` capture does. That was UNREADABLE and
      therefore honest, but only because the echo guard exists: with the anchor
      gone there is nothing to compare, and two blank readings would otherwise
      have agreed. (`basic_probe_lptverb.py` never hits this — its screen
      batteries take the DEFAULT capture and only its printer battery takes this
      one; checked before anything was claimed about it.)
      🎯 **THE PROGRAM BEING LISTED IS THE ROW'S OWN**, which makes the expected
      text something CHOSEN rather than hoped for: the row is `LLIST:REM ZQ8` and
      the log reads `10 LLIST:REM ZQ8\r\n` byte for byte on both. The `:REM ZQ8` is
      there on purpose — a listing that printed only the line number, or mangled
      the token spacing, fails a row that asserted the verb's own name alone.
      🔴 **THE BLIND SHAPE WAS MEASURED FIRST**: the same program WITHOUT the
      `LLIST` leaves the log EMPTY on both machines, so the reading exists only
      because the verb ran.
      ➡️ **EIGHT LEFT, AND THE WHOLE PRINTER CLUSTER IS NOW CLOSED** — `LPRINT`
      and `LPOS` by D-KWRIG, `LFILES` by D-DFEND, `LLIST` here. What remains is
      the tape pair (nothing plays a tape), the key-injector three (harness
      timing), and `AUTO`/`RENUM`/`CALL`, which need a row FORMAT or a safe
      extension rather than a rig. Recount with `make tiers ARGS=--keywords`.
      🟢 **D-KWGET, 2026-09-13: `GET` and `CALL` attributed — 8 → 6, and neither
      needed apparatus** ([readings](../../scratchpad/kwget_full.out), full sweep).
      🔴 **`GET` IS NOT A KEYBOARD VERB, and the name is the whole reason it sat in
      this list.** MSX1's `GET` is the RANDOM-FILE record read (`GET #n[,record]`).
      `PUT` already ships and the disk rig has been mounted since D-KWDISK, so the
      round trip fits ONE row — and the blind shape is INSIDE the same reading
      rather than beside it: the FIELDed buffer is overwritten to `"Z"` between the
      `PUT` and the `GET`, and both values are printed. `90` then `66` is a real
      re-read; `90` then `90` is what a `GET` that parsed and did nothing gives,
      measured on both machines with the GET removed
      ([`scratchpad/kwdrain_getcall.py`](../../scratchpad/kwdrain_getcall.py),
      [readings](../../scratchpad/kwdrain_getcall.out)).
      ⚠️ **THREE OF THE SIX WORDS LEFT ARE IN THAT LIST FOR A NAME, NOT A GAP** —
      `INKEY$` and `INPUT` really are keyboard-blocked, but `GET` never was, and
      nothing in the filing said which kind it was. Worth a glance at the other
      five before assuming each needs what its neighbour needs.
      🔴 **`CALL` SCORES RESERVEDNESS AND NOTHING MORE, and that limit IS the
      finding.** The obvious form is BLIND: `CALL ZZQ`, bare `CALL` and the
      absent-keyword shape `ZZQQ ZZQ` all answer `Syntax error` on zerobas, the
      CF-3300 and the VG-8020 alike, so an unknown extension cannot separate a
      machine that HAS the verb from one that does not. What separates them is
      D-DONOTHING3's trick — a reserved word cannot be a variable: `CALL=1` is a
      Syntax error on all three while the stub shape `ZZQQ=1` assigns and prints
      ([`scratchpad/kwdrain_callres.py`](../../scratchpad/kwdrain_callres.py),
      [readings](../../scratchpad/kwdrain_callres.out)).
      ⚠️ **SO THE ROW CANNOT SEE WHETHER ANY EXTENSION WORKS**, and it says so in
      its own comment. The two that exist on this hardware are `CALL SYSTEM` and
      `CALL FORMAT` — one exits to DOS, one formats the disk — so neither is
      invokable from a sweep. A row that scores less than the whole verb, with the
      shortfall named, beats a row that passes for the wrong reason
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      🎯 **`CALL` IS RESERVED ON THE DISKLESS VG-8020 TOO**, which is what makes
      the VG-8020 its oracle rather than the CF-3300 — the same shape as `SET`,
      `IPL` and `CMD` in D-DONOTHING3.
      ➡️ **SIX LEFT: `AUTO CLOAD CSAVE INKEY$ INPUT RENUM`** — the tape pair
      (nothing plays a tape), the keyboard pair plus `AUTO` (the key injector's
      timing, and a case slot that survives line-entry mode), and `RENUM` (a
      read-back the row format cannot express: it STOPS the program, so no
      statement after it runs and an `LLIST` after it never executes either).
      🟢 **D-KWINP, 2026-09-13: `INPUT` and `RENUM` attributed — 6 → 4** — and
      `INPUT` is the SECOND word found to be in this list for its NAME rather than
      a gap ([readings](../../scratchpad/kwinp_full.out), full sweep).
      🔴 **`INPUT` SAT WITH `INKEY$` AS THOUGH IT SHARED THE KEYBOARD BLOCKER.**
      `INPUT #n, var` reads a FILE and needs no keystroke at all. The fixture's own
      `HI.TXT` holds `Hello from zerobas-disk!` + CRLF, so the length is **24** on
      both machines and the same row with the `INPUT#` removed reads **0**
      ([`scratchpad/kwdrain_inputauto2.py`](../../scratchpad/kwdrain_inputauto2.py),
      [readings](../../scratchpad/kwdrain_inputauto2.out)).
      ⚠️ **THE KEYBOARD FORM IS STILL UNSCORED and the row does not pretend
      otherwise** — `INPUT "prompt";A$` blocks, and that stays with `INKEY$` in the
      injector-timing group.
      🟢 **`RENUM`'S FILED REASON WAS TRUE AND NOT THE ONLY ROUTE.** "Needs a
      program to be visible" is right about a positive read-back — it stops the
      program, so nothing after it runs — but `RENUM 100` on a one-line program
      answers `Undefined line 100 in 10` on zerobas AND the CF-3300, byte for byte,
      while an ABSENT `RENUM` parses the line as a name followed by a number and
      answers `Syntax error`.
      ⚠️ **WHAT THAT ROW CANNOT SEE IS IN THE ROW**: it does not prove the
      renumbering, only that the verb parsed its argument and went LOOKING for a
      line — which a do-nothing `RENUM` would not do.
      🔴 **AND `AUTO`'S FILED BLOCKER IS WRONG — THE REAL ONE IS DIFFERENT AND
      MEASURED.** The filing says it is interactive and "swallows all following
      input", and that is solvable: put it LAST and there are no neighbours to
      poison. Proved by sacrificing two rows to it — the harness flagged BOTH as
      MIS-DELIVERED and then REFUSED on the CF-3300 rather than reporting garbage,
      which is the apparatus working ([readings](../../scratchpad/kwdrain_inputauto.out)).
      With nothing behind it the verb SCORES: both machines print the `100`
      line-entry prompt.
      ⚠️ **WHAT ACTUALLY BLOCKS IT IS THAT LINE-ENTRY MODE LEAVES NO PROMPT.**
      `screen_tail` runs to the closing prompt, and there isn't one — so on the
      CF-3300 the tail drags in twenty blank rows and the **function-key display**,
      which zerobas does not show. The row would read DIVERGENT for a
      machine-configuration reason, exactly like the `FILES`/`CSRLIN` row this
      drain already threw away [[readout-blind-to-its-own-subject]]. Attributing
      `AUTO` needs a way to EXIT line-entry mode (a Ctrl-C injection) or a tail
      rule that stops before the furniture — not a case slot.
      ➡️ **FOUR LEFT: `AUTO CLOAD CSAVE INKEY$`** — one screen-furniture problem,
      the tape pair (nothing plays a tape), and one genuine keyboard block.
      🟢 **D-KWAUTO, 2026-09-13: `AUTO` attributed — 4 → 3, and the row that taught
      "read the WHOLE sweep summary" is the one that proves the rule held**
      ([readings](../../scratchpad/kwauto_full.out), full sweep: **zero** DIVERGENT and
      **zero** apparatus warnings, where the first `AUTO` attempt produced
      DIVERGENT=22 + UNREADABLE=1).
      🔴 **THE FILED BLOCKER AND THE REAL ONE WERE DIFFERENT PROBLEMS.** The filing
      — *"INTERACTIVE: enters auto-line-number mode and swallows all following
      input"* — describes the POISONING, and position solves that: the row is now
      LAST in `SWEEP` and there is nothing behind it to eat. Proved before it was
      believed, by sacrificing two rows to it: the harness flagged both
      MIS-DELIVERED and then REFUSED on the CF-3300 rather than reporting garbage
      ([readings](../../scratchpad/kwdrain_inputauto.out)).
      🔴 **WHAT ACTUALLY STOOD IN THE WAY: LINE-ENTRY MODE PRINTS NO CLOSING
      PROMPT.** `screen_tail` runs to the prompt, so with none it runs to the
      bottom of the screen and collects the CF-3300's **function-key display**,
      which zerobas does not show — the row would have read DIVERGENT for a
      machine-configuration reason, exactly the `FILES`/`CSRLIN` row this drain
      already threw away [[readout-blind-to-its-own-subject]].
      🟢 **`NOFURN:` + `screen_tail_nofurn` IS THE FIX, AND IT IS KWSWEEP-LOCAL ON
      PURPOSE.** `omsx_repl.screen_tail` is a shared leaf; one row does not justify
      changing what every other probe reads. The echo anchor is still the harness's
      own `_echo_idx`, so the two differ in the ROW SET and in nothing else, and
      [`basic_probe_lptverb.py`](../../probes/basic/basic_probe_lptverb.py)'s
      `screen_rows` already does the same `[:-1]` with the same justification.
      ⚠️ **POSITION, NEVER CONTENT.** The obvious rule — drop a row reading
      `color auto goto list run` — is wrong in this very file: the `keykw` row
      REWRITES that line to `ZZQ auto goto list run`.
      🎯 **THE READING IS THE LINE-ENTRY PROMPT ITSELF**: `100` on both machines,
      the number `AUTO` was asked to start at. An absent `AUTO` parses `AUTO 100`
      as a name followed by a number and answers `Syntax error`; an `AUTO` that
      parsed and did nothing prints no prompt at all.
      ⚠️ **AND THE PLACEMENT IS LOAD-BEARING, SO IT IS WRITTEN AS A FENCE** — a
      banner comment above the row says it is placed, not sorted, and that anything
      appended after it inherits the poisoning.
      ➡️ **THREE LEFT: `CLOAD` `CSAVE` `INKEY$`** — the tape pair, which need a
      tape the emulator can PLAY (nothing in this tree does; `cas_decode` is
      WAV→bytes only, and a fixture would have to be RECORDED by driving one
      openMSX pass with `CSAVE`, the cassette twin of `tools/make_test_dsk.py`),
      and the one genuine keyboard block, which needs the injector's TIMING and
      must not reopen D-LATCH.
      🔴 **CORRECTION 2026-09-13 (D-KWAUTO tick): "NOTHING IN THIS TREE PLAYS A
      TAPE" IS FALSE, AND I FILED IT TWICE.** D-KWTAPE recorded it as a MEASURED
      blocker; the measurement was a grep for `cassetteplayer insert` under
      `probes/`, which is not how this tree mounts a tape. It mounts one as an
      openMSX COMMAND-LINE flag — `-cassetteplayer <file>` — in
      [`basic_probe_cas_options.py`](../../probes/basic/basic_probe_cas_options.py),
      [`basic_probe_cas_ascii.py`](../../probes/basic/basic_probe_cas_ascii.py) and
      [`basic_probe_cas_verbs.py`](../../probes/basic/basic_probe_cas_verbs.py), all of
      which LOAD programs off tape today.
      🔴 **AND THE ENCODER EXISTS TOO.** The same filing said *"`cas_decode` is
      WAV→bytes only, so a playable fixture would need an encoder this tree does
      not have"*. [`probes/lib/cas_encode.py`](../../probes/lib/cas_encode.py) is that
      encoder — `build_cas_basic(name, program)` synthesises a playable `.cas` from
      a tokenised program, clean-room, with every constant traced.
      ⚠️ **THIS IS THE ELEVENTH-OF-THIRTEEN PATTERN WITH MY OWN NAME ON IT.** Every
      stale blocker this session was inherited; this one I wrote, two ticks ago,
      from a grep that asked the wrong question. A blocker is only as good as the
      string it was measured with [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      ➡️ **SO THE TAPE PAIR IS BLOCKED ON A READBACK, NOT A RIG** — and that is a
      different and smaller claim. `CLOAD` replaces the program and returns to
      COMMAND LEVEL, so nothing in the same case can observe it; that is exactly
      `LOAD`'s shape, and `LOAD` is attributed by an OPEN ITEM rather than a row.
      `CSAVE`'s output is the recording, which needs the WAV decode
      (`basic_probe_cassave.py` already does it, out of kwsweep's reach).
      **Both are now questions about a CAPTURE, like `LLIST` was — and `NEEDS-LOG:`
      is the precedent for adding one.**
      🔴 **D-KWCLOAD, 2026-09-13: `CLOAD`'S BLOCKER HAS NOW MOVED THREE TIMES UNDER
      MEASUREMENT, and where it ended up is not where any of the filings put it.**
      Each step was cheap and each one killed the previous answer:
      | filed as | measured |
      |---|---|
      | "nothing in this tree PLAYS a tape" | FALSE — `-cassetteplayer` mounts one and three cas probes load off tape today; `cas_encode.build_cas_basic` synthesises the `.cas` |
      | "no READBACK — it returns to command level" | FALSE — **`Found:ZQ` reaches the SCREEN.** No new capture is needed at all |
      | *(new)* | 🔴 **THE VG-8020 DOES NOT READ THE FIXTURE.** zerobas prints `Found:ZQ`; the reference prints nothing and never returns to a prompt |
      🟢 **THE READBACK IS THE INTERESTING HALF AND IT IS FREE.** MSX BASIC prints
      `Found:<name>` while it searches a tape, so `CLOAD"ZQ"` against a mounted
      fixture is screen-visible on the subject side — the `NEEDS-LOG:`-style capture
      this was going to need is not needed
      ([`scratchpad/kwdrain_cloadchk.py`](../../scratchpad/kwdrain_cloadchk.py),
      [readings](../../scratchpad/kwdrain_cloadchk.out)).
      🔴 **AND THE TAPE POSITION IS STATE THAT SURVIVES A CASE** — the `AUTO` lesson
      in another costume. Batched, the second `CLOAD` answered `load error` because
      the first had already consumed the tape, and the first VG-8020 run was
      unusable with ALL THREE cases showing one stale screen **including the
      control**, which is the tell that the run and not the verb had failed. Boot
      per case, one fresh tape each
      ([readings](../../scratchpad/kwdrain_cloadchk2.out)).
      ⚠️ **THE REFERENCE SIDE IS NOT A TIMING PROBLEM AND NOT A MISSING PORT**, both
      checked because both are the cheap explanations: at `cap_gap` 60 **and** 150
      the VG-8020 screen is unchanged ([readings](../../scratchpad/kwdrain_cloadchk3.out)),
      and its openMSX config carries `<CassettePort/>` exactly as the repack machine
      does. ⚠️ Note that EVERY cassette probe in this tree runs on the repack
      machine only — its header says so — so whether the VG-8020 can read a tape
      here has never been asked before now.
      ➡️ **SO THE OPEN QUESTION IS AN ORACLE ONE**: either the fixture is built to
      zerobas's reading of the `.cas` format and a real BIOS wants something else
      (which would be a FINDING about the format, not about the verb), or the
      VG-8020's tape path needs an openMSX setting the repack machine does not.
      Separating those is the next measurement, and it is apparatus work.
      ➡️ **THE LAST THREE ARE AN APPARATUS DECISION, NOT A METHOD ONE** — filed as
      its own item below so it reaches the NEEDS-JOOST queue instead of hiding
      inside an autonomous block.
      🔴 **D-KWCASOR, 2026-09-13: NEITHER REFERENCE CAN READ A TAPE IN THIS RIG,
      AND ZEROBAS CAN.** The `CLOAD` question is now answered as far as measurement
      can take it, and the answer is an ORACLE fact, not a language one.
      | run | result |
      |---|---|
      | zb `CSAVE"ZQ"` → 124 486-byte WAV, then zb `CLOAD"ZQ"` | **`Found:ZQ`** ✅ the control: the tape is readable |
      | zb `LOAD"CAS:ZQ"` on the same tape | **`Found:ZQ`** ✅ |
      | VG-8020 `CLOAD"ZQ"` / `LOAD"CAS:ZQ"` on the SAME tape | nothing, no prompt — BOTH verbs |
      | CF-3300 `CLOAD"ZQ"` / `LOAD"CAS:ZQ"` on the SAME tape | nothing, no prompt — BOTH verbs |
      🟢 **THE FIXTURE AND THE ENCODER ARE EXONERATED THREE WAYS**: a `.cas` built
      clean-room by [`probes/lib/cas_encode.py`](../../probes/lib/cas_encode.py) from the
      published format fails on the reference, a WAV **zerobas itself recorded**
      fails there too, and zerobas reads both. A format that only zerobas accepts
      would not explain the spec-built one
      ([`scratchpad/kwdrain_casoracle.py`](../../scratchpad/kwdrain_casoracle.py),
      [readings](../../scratchpad/kwdrain_casoracle.out)).
      🟢 **AND IT IS NOT `CLOAD`-SPECIFIC**: `LOAD"CAS:"` fails identically on both
      references and works on zerobas
      ([readings](../../scratchpad/kwdrain_casoracle2.out)), so the verb is not the
      variable — the machine's tape READ path is.
      🎯 **THE CF-3300 WAS TRIED BECAUSE D-KWORACLE IS THE PRECEDENT** — that
      machine turned out to read a screen everyone had written off — and it carries
      `<CassettePort/>` exactly as the VG-8020 and the repack machine do. It reads
      nothing either ([readings](../../scratchpad/kwdrain_casoracle3.out)). Two
      references, two verbs, one tape: the same silence.
      ⚠️ **ONE UNTESTED DIFFERENCE, NAMED RATHER THAN CHASED**: every cassette probe
      in this tree passes `-cassetteplayer <file>` on the openMSX COMMAND LINE and
      runs on the repack machine only; these runs used the Tcl `cassetteplayer`
      PROLOGUE, which `omsx_repl.run_cases` supports. The prologue demonstrably
      works for zerobas. Testing the command-line form against a REFERENCE means
      going around `run_cases`, which is apparatus — and that is where this stops.
      ~~➡️ **SO `CLOAD` AND `CSAVE` HAVE NO ORACLE HERE**~~
      🔴 **RETRACTED THE SAME DAY (D-CASORACLE), AND THE REASON IS THE BEST PART:
      THE "FIXTURE" I WAS MEASURING WITH WAS THE DEFECT.** The VG-8020 reads a
      clean-room `.cas` perfectly (`Found:ZQ`), so the oracle was there all along.
      Every run that concluded "no oracle" had fed the reference a tape ZEROBAS
      RECORDED — which is precisely the artifact a real BIOS cannot read, filed
      above as a TIER 1 defect. **The broken subject was standing in for the
      instrument**, so the instrument was blamed
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      ⚠️ **THAT IS TWO WRONG BLOCKERS I FILED IN ONE NIGHT ON THIS ONE VERB** — "no
      tape player" (a grep for the wrong string) and "no oracle" (a fixture that was
      itself the bug). Both were re-verified away within the hour by someone
      re-running them, which is the whole argument for the re-verify rule.
      ⚠️ **AND ONE REAL CONSTRAINT SURVIVES**: on the reference the `.cas` reads in
      DIRECT mode and NOT in `stored` mode (`10 CLOAD"ZQ"` + `RUN` prints nothing
      there while zerobas prints `Found:ZQ`). A `CLOAD` row must be direct-mode —
      and whether that stored-mode difference is itself a divergence is unmeasured
      and NOT claimed here.
      ⚠️ **THE PATTERN WAS TEN FOR TEN AND IS NOW TEN OF TWELVE — the tape and
      the printer log HELD.** Every other blocker examined this session — the display verbs' "cannot take a row", the multi-line words'
      "cannot be expressed", the CF-3300 oracle, the disk fixture (which needed a
      `diska=` argument and a bigger capture gap), and then `SCREEN`'s mode, `KEY`'s
      missing constant, `USR`'s machine code, `WAIT`'s port, and the printer log
      `LPOS`/`LPRINT` never needed. Re-verify a blocker BEFORE believing it; that is
      cheaper than any of the work it was hiding, and it has not once been wrong.
      🎚️ STANDING — ruling
      🤖 AUTONOMOUS — kwsweep's keyword list is the denominator; work through
      it verb by verb, cheapest-context verbs first, and file what each review
      measures.
