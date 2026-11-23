- [ ] 🎚️ **WHAT PROVES A RUNG? T2, T4, T5 AND T6 HAVE NO PROVING ROW TYPE, SO
      `0 of 159` KEYWORDS PROVE ANY OF THEM (D-KWPROVEN, 2026-09-23).**
      🏗️ **RULED BY JOOST 2026-09-29 — DO NOT RE-ASK: T6✓ IMPLIES T3✓** (*"go with
      (a)"*). T6 proves every error the reference raises for every form, so the
      common errors T3 asks about are among them; `tools/tier_table.py`
      `proven_rungs` ticks T3 for a connected keyword with a `PROVES-T3:` row OR
      T6 (selftest S36za, S36zb NEGATIVE: not without connectedness). Effect,
      measured the same day: level 3 **32 → 121**, level 2 **113 → 24**. The 24 get
      REAL `PROVES-T3:` rows next (Joost: *"then real T3 rows for the 24"*).
      ✅ **AND 19 OF THE 24 HAVE THEM (D-KWT3 batches 6–7, same day)** — CONT, DATA,
      RESUME, RUN, TAN, WIDTH, PRINT, ERROR, CIRCLE, LOAD, OPEN, EOF, INPUT, CLOAD,
      BSAVE, SAVE, LPRINT, LFILES, AUTO: one `PROVES-T3:` row each, every one
      SUPPORTED against the reference AND checked to show the intended error on both
      sides, not blank-equals-blank ([`kwt3b6.out`](scratchpad/kwt3b6.out),
      [`kwt3b7.out`](scratchpad/kwt3b7.out), [`kwt3auto.out`](scratchpad/kwt3auto.out)).
      No divergence found. Level 3 **121 → 140**, level 2 **24 → 5**; kwsweep 933 → 952.
      🙋 **THE LAST FIVE HAVE NO NATURAL COMMON ERROR:** REM cannot raise one at all;
      END, STOP and CLS only error with junk after the word (and CLS/END's junk case
      is a known divergence, the TIER 6 item on `CLS` / `END` followed by an
      argument); LLIST's real-world error is a printer that is not ready, which the
      rig cannot produce. Asked of Joost 2026-09-29.
      🏗️ **RULED (Joost, same day): *"go with (A)"* — T3 DECLARED NOT APPLICABLE for
      those five,** each with its reason, in `tools/tier_table.py` `T3_NA`; the table
      renders the tick as `T3∅`, never `T3✓` (selftest S36zc, S36zd NEGATIVE). A
      keyword joins `T3_NA` only by ruling. **Level 2 is EMPTY: every keyword but
      VARPTR and the 13 N/A entries is at level 3 (145).**
      🎚️ TIER 1 — it is the bar every other item is measured against, and three
      quarters of it has never been measurable.
      🏗️ **RULED BY JOOST, 2026-09-24 — three of the four rungs now have a
      definition:**
      | rung | ruling |
      |---|---|
      | **T2** — reasonable time | a keyword's test program **finishes within a set time and never hangs** (accepted as proposed) |
      | **T4** — RAM usage | ***"The whole RAM map"*** — the comparison is the whole map, not per-keyword cells; per-keyword T4 is DERIVED from it. Consistent with his 2026-09-22 ruling (then numbered TIER 5), which the RAM-usage comparison item (TODO §"COMPARE RAM *USAGE*") already carries |
      | **T5** — on-par speed | ***"Track the ratio, set no bar yet"*** — a T5 row RECORDS zerobas ÷ reference and never passes or fails on it |
      | **T6** — the exhaustive error set | **not ruled** — split into its own 🙋 item directly below |
      🏗️ **T4's ROW TYPE, RULED BY JOOST 2026-09-30 — all three recommendations
      (*"agree with all three recommendations, build it"*):**
      | question | ruling |
      |---|---|
      | (b) strictness | **STRICT** — the same SET of documented work-area cells ($F380..) written, and each ENDS on the same value |
      | (c) economy | **SHOWN, never ticked** — cells written zerobas ÷ reference, like T5's ratio |
      | undocumented cells in the reference's own workspace | **REPORTED, not ticked** — (c) counts them; T4 does not require matching them |
      and on caching: *"reference is not going to change behavior all of a sudden, so
      once we know what memory reference uses, we don't need to measure that again,
      unless we do a different test"* — the reference side is replayed from the probe
      cache, keyed on the machine's bytes and the exact test.
      🔨 **BUILT 2026-09-30:** `make kwram` (`probes/basic/basic_probe_kwram.py`,
      D-RAMFOOT's instrument over kwtime's rows) writes `build/kwram.json`, and
      `tools/tier_table.py` `kwram_rungs` ticks T4 when EVERY authored form has a
      SUPPORTED row that is PASS on (a) FRE(0)/FRE("") delta AND (b). S36e was flipped
      DELIBERATELY for T4 (T5 stays barred); arms S36zf–zi, three NEGATIVE.
      📏 **FIRST READING 2026-09-30 — T4 0 of 159, economy measured for 123**
      ([`kwram_full.out`](scratchpad/kwram_full.out), 298 happy-path rows):
      - **(b) FAILS on all 246 rated rows** — predicted. Always the same cells:
        the reference writes `$F678–$F67A` / `$F698–$F69A` / `$F416` / `$F864–$F865`
        on every statement (and `$F7FE`, `$F7D4–$F7D5` on most); zerobas writes
        `$F7F8–$F7F9` and `$FCC8` (SLTTBL, its sub-ROM slot switching) on ~155.
        This is the D-ADDR29 arc's work list, ranked by reach.
      - **(a) PASSES on 219 of 237** (predicted ~85%). The 18 FAILs are real
        free-memory findings: DEF FN / FN (22 B there, 11 here), OPEN / FIELD
        (6 against 0), GET / PUT # (28 against 22), LSET / RSET (17 / 11), DATA
        strings and DEFSTR (the string pool charged 0 there, 1–3 here), PLAY
        strings (0 there, 52 / 12 here).
      - **(c)** median 1.26×; zerobas writes FEWER cells on 102 of 246 rows —
        the "very economical" hunch holds per statement, not everywhere.
      - **52 rows UNRATED** — predicted under 5%, MISS: rows whose control flow
        leaves before the closing line (END, NEW, LIST, GOSUB, ON GOTO, ERROR …).
        kwtime reaches them with a type-ahead end mark; kwram cannot yet.
      🔴 **THREE INSTRUMENT FAULTS ON THE WAY, EACH CAUGHT BY A CONTROL OR A
      REFUSAL, NONE BY LUCK:**
      - Every row was silently dropped for a >38-character typed line. The filter
        now NAMES what it drops and refuses an empty run.
      - A 660-case boot outran the 1800 s wall watchdog; the positive control
        refused the result. Each window is now flushed once, at close, and rows
        run in 40-row chunks.
      - Error rows (T6/T3) can never close a window: the first full run was 590 of
        836 UNRATED. Happy-path rows only now.
      One more was mine in the check, not the tool: a determinism "identical"
      whose second run had REPLAYED the first from the cache. Redone with
      `ZEROBAS_REFCACHE=0`: identical live against live, and across batch sizes
      once both machines' interrupt signatures are subtracted from both sides
      (zerobas's handler writes the keyboard rows only on SOME ticks).
      `--negative` (a documented cell planted on zerobas's side) FAILs (b) on
      every row ([`kwram_negative.out`](scratchpad/kwram_negative.out)).
      ➡️ `make kwram` is in the battery beside `kwtime`. 💰 **Its cost there: 1917 s
      (32 min) in the pool on 2026-09-30, the battery's longest unit.** The emulator
      tier runs with `ZEROBAS_REFCACHE=0` by design, so the reference side is
      measured live every battery. Whether the gate may replay the reference side
      (Joost: *"once we know what memory reference uses, we don't need to measure
      that again"*) is a policy change to the gate tier: 🔭 filed, not taken.
      🔢 **SWAPPED THE SAME DAY (D-TIERSWAP): RAM IS T4, SPEED IS T5** — this
      table is written in the new numbering.
      🪜 **AND THREE MORE RULINGS THE SAME MORNING (D-KWLADDER)**, asked when
      Joost checked *"what needs to be done still for a keyword without any
      open items"*:
      | question | ruling |
      |---|---|
      | ladder or independent ticks? | **LADDER, contiguous only** — a keyword's LEVEL is its highest unbroken run of proven rungs from T1; `T1✓ T2— T3✓` is level 1. `tools/tier_table.py` prints the level and a per-level count |
      | what does a T5 ratio show? | **the RATIO, no tick** (e.g. `T5 2.5×`) — measured, never passed or failed, until he sets a bar. So no keyword can pass level 4 today, and the sheet says why |
      | T2's "set time"? | **WITHIN 10× OF THE REFERENCE's time** for the same test program — first *"multiple of reference"*, then the number: ***"use 10x, it will be slow, but it finishes"*** |
      🎯 **SO T2 AND T5 ARE ONE MEASUREMENT** — zerobas ÷ reference for the
      same program, with a completion watchdog. T2 passes at ≤ 10×; T5
      displays it. One row type, built once, serves both rungs.
      ✅ **T2/T5's ROW TYPE IS BUILT (D-KWTIME, 2026-09-24):**
      [`probes/basic/basic_probe_kwtime.py`](probes/basic/basic_probe_kwtime.py),
      `make kwtime`, in the battery's static tier beside `kwsweep` (~30 s).
      Each plain kwsweep row that declares a FORM is re-typed with EXPLICIT line
      numbers (kwsweep's `RESPOND:` shape, so every `GOTO 40` still lands),
      bracketed by two program-written marks (`docs/spec-probe-mark.md`) —
      EMULATED time, so there is no "too short to time" rule: nothing is
      quantised, and two full runs were **bit-identical on all 225 rows**. A
      `CLS` precedes the start mark: without it a batched boot's accumulated
      screen made `PRINT` scroll and moved zerobas's deltas +1.7..3.4 ms.
      `tier_table` joins `build/kwtime.json` with kwsweep's pin: T2 = every
      authored form has a SUPPORTED row timed `OK` (≤ 10×); T5 = ~~the worst
      row's ratio~~ **the KEYWORD ALONE** (Joost's option (c), same day —
      D-KWT5ALONE below), SHOWN in the cell and never ticked. `S36e` was
      flipped DELIBERATELY (T4/T5/T6 still cannot tick) and five arms added,
      three of them negative (a 20× keyword, an UNTIMEABLE row, a pin from
      another ROM). The probe's own `--negative` run pads zerobas's side with a
      delay loop and reads every row SLOW (98–122×) before the real run.
      📏 **FIRST READING, 2026-09-24 — RECOUNT, NEVER QUOTE:** T2 proven for
      **81** of 159; the ladder moved from levels 0/1 only to 20 / 58 / 57 /
      24 at levels 0–3. Rows: OK 188, UNTIMEABLE 37, SLOW 0, HANG 0; two rows
      not typed (`space_b`, `ifkw_b` — a statement over 38 characters). Ratio
      median 1.15×, worst `SQR` **8.6×** (filed on the speed item).
      🔮 **PREDICTIONS, SCORED:** *"ratios in the 2.5–3.8× interpreter band"* —
      **MISS** (1.17–4.79× on the prototype; `PRINT`-bound rows sit near 1×).
      *"all under 10×"* — HIT. *"the padded negative reads SLOW, ~90×"* — HIT.
      *"no SLOW, no HANG, some UNTIMEABLE"* — HIT.
      🤖 **AUTONOMOUS — WHAT IS LEFT OF THIS ITEM:** (1) **the 37 UNTIMEABLE
      rows** — they `END`, `STOP`, `RETURN` or error before their last line, so
      the end mark is never reached (`GOSUB`, `END`, `RESUME`, `ON`, `ERROR`,
      `LIST`, `NEW`, `READ` …); they need a second shape (an end mark placed
      where the row actually finishes, or the prompt's return), and until then
      those keywords cannot reach T2; (2) **T4**, which is the RAM-map
      comparison it derives from (TIER 4 item).
      🔭 **SCOUTED FOR (1), NOT BUILT:** an end mark that needs NO program text
      is *"execution returned to direct mode"*. On the reference that is the
      documented CURLIN (`$F41C`) becoming `$FFFF` — a RAM watch, clean-room
      legal. ⚠️ **ZEROBAS DOES NOT MAINTAIN `$F41C`**: its `CURLINE` is at
      `$E038` and is a POINTER, direct mode being `CURLINE == dir_line` (a ROM
      constant; `basic/sysvars.inc`). So the shape would watch a DIFFERENT
      cell per machine — an asymmetric instrument whose bias must be measured
      on rows BOTH shapes can time before any ratio from it is believed.
      🧮 **AND THAT IS A RAM-RUNG FINDING IN ITS OWN RIGHT** (goal (b), *same
      addresses*): a program that PEEKs CURLIN reads the reference's current
      line and zerobas's nothing. ✅ **FIXED 2026-09-24 (D-CURLIN, Joost:
      "Yes, maintain CURLIN")** — zerobas publishes `$F41C` on every line
      entry (`derive_directf` → `curlin_pub`, low region) and `$FFFF` at the
      prompt; measured 10 / 300-after-GOTO / 65535-direct on BOTH machines, and
      gated by kwsweep's `peek_curlin`. Page 1 14 → 8 B, low 26 → 5 B. **So
      the UNTIMEABLE shape is SYMMETRIC now:** "CURLIN becomes `$FFFF`" is the
      end-of-program signal on both machines. ✅ **(1) DONE THE SAME DAY
      (D-KWUNTIME):** `omsx_repl` gained value-filtered extra watches
      (`watch_values`, keyword-only, armed at the RUN slot); kwtime watches
      `$F41D` for `$FF` and takes the first write AFTER the start mark (RUN is
      itself a direct line and writes `$FFFF` just before). 🔬 **THE SIGNAL IS
      NOT SYMMETRIC RAW:** from a program's end to `$FFFF` is 2.478 ms on the
      VG-8020 and 0.254 ms here (falling off the end), 2.877 / 0.553 ms on an
      `END` path — so each machine's END-path bias is CALIBRATED LIVE every
      run and subtracted. 🔴 **AND IT IS ONLY THE SAME EVENT ON AN `END` PATH:**
      the first cut accepted every row and read `stopkw` 0.26, `attrkw` 0.29,
      `onkw_b` 0.28 and `listkw` **239×** — Break/error-message paths and
      statements that return to direct mode themselves publish `$FFFF` at a
      different point per machine. CURLIN is now accepted only for a row with
      an `END` statement, none of `LIST LLIST NEW STOP CONT RUN`, and no
      "… in <line>" message on either screen (`sprite_stop` is excluded by the
      word STOP — conservative). **UNTIMEABLE 37 → 14, 23 rows timed via
      CURLIN, T2 82 → 92 keywords.** ⚠️ A twin that deletes `RESUME` changes
      the handler's control flow, so `RESUME`'s T5 (8.1×) is not its own speed. `docs/sysvar-msx1-coverage.md` already lists
      `CURLIN = $FFFF` among the cold-boot differences; the RAM-map comparison
      should carry it as a LIVE cell, not an init value. ⚠️ The whole-program-vs-keyword
      question below is Joost's and does not block either.
      💽 **D-KWTDISK (2026-09-24): THE DISK ROWS ARE TIMED TOO — T2 92 → 115
      KEYWORDS.** 51 keywords sat at level 1 with `T2—`, far more than the 14
      UNTIMEABLE rows could explain: `select_rows` skipped every RIGGED row, and
      48 of the FORM rows carry only the disk rig. They are now a second group,
      timed against the **CF-3300** — the VG-8020 has no drive, so a disk verb
      has no time there at all; it is the machine kwsweep already scores those
      rows against, and the rule Joost ruled for the RAM rung (*"prefer the
      vg8020"*, disk-only takes the CF-3300). ⚠️ That is an EXTENSION of the T2
      ruling's *"10× the VG-8020"* to where the VG-8020 cannot answer — stated
      here so it can be overruled, not assumed. Each measurement mounts a FRESH
      copy of the image, so a row that KILLs or NAMEs a file cannot change what
      its twin sees. A disk row with a SECOND rig (`lfiles`) stays out.
      🔪 **ITS OWN NEGATIVE ARM** in `--negative`: `lof` padded with 3000
      iterations reads **12.4× SLOW** (predicted ~13×). ⚠️ 6000 read HANG — it
      ran past the rig's 20 s capture window — caught, but not for the reason
      the arm asserts.
      📊 **RESULT: 275 rows, OK 254, UNTIMEABLE 21.** The 40 timed disk rows
      are **0.21–1.20×** — zerobas is FASTER than the CF-3300 on most disk
      verbs (`LOF` 0.21, `DSKI$` 0.22, `FILES` 0.27; slowest `KILL` 1.20).
      🔮 *"1–3×"* — **MISS**, low. The 7 untimeable disk rows are honest: three
      REFUSE on every machine (`SET`, `IPL`, `CMD` — no happy path to time) and
      four end the run themselves (`MERGE`, ASCII `SAVE`, `RUN"f"`, `LOAD"f",R`).
      ⏱ **D-KWTLONG (same day): the three rows kwtime could not TYPE are
      shortened, reading unchanged — T2 115 → 117.** `space_b`/`mki_c` moved
      `RIGHT$(A$,1)` into its own `B$=` statement, and `ifkw_b` spells PRINT
      `?` (the same token); each still reads `[ 32  32 ]` / `[ 2  1 ]` / `[1h]`
      on both sides. None of the three is a knife row (`space`, `mki`, `ifkw`
      are), so the knife pin is untouched. `SPACE$` → level 3, `IF` → level 2.
      🖨 **D-KWTRIG (same day): single-rig PRINTER and TAPE-WRITE rows are timed
      too — T2 117 → 120** (`LPRINT`/`LPOS` 1.12×, `CSAVE` 0.83×, against the
      VG-8020). kwtime reads RAM marks, never the artefact, so a rig only has
      to be PRESENT. ⚠️ `tape` (CLOAD) is left out on purpose: a CLOAD replaces
      the running program, so its end mark can never fire. 281 rows, OK 260.
      📋 **THE 22 KEYWORDS STILL `T2—`, BY REASON:** they end or replace the
      run (`CONT` `LIST` `NEW` `STOP` `RUN` `LOAD` `MERGE` `SAVE` `CLOAD`);
      editor/prompt rows the shape cannot type (`AUTO` `DELETE` `RENUM`
      `LLIST`); refuse on every machine (`CMD` `IPL` `SET`); `RESPOND:` rows
      (`INPUT`); hold/plug rigs (`KEY` `PDL`); two rigs at once (`LFILES`);
      and `CALL`/`USR`, whose rows are untimeable. The first group needs the
      prompt's return as its end (the CURLIN signal, which today is accepted
      only on an `END` path — measured asymmetric elsewhere).
      ~~🙋 **NEEDS-JOOST**~~ (answered above for T2/T4/T5) — a rung's definition is charter-level, not a coding
      choice. What does a row that PROVES "reasonable time" look like? A wall
      against the reference, per keyword? A ratio? Same question for RAM parity
      and for "the exhaustive error set", which has no obvious finite bound.
      🔴 **THIS ITEM EXISTS BECAUSE JOOST CAUGHT A REGRESSION I SHIPPED.** The
      D-KWSTATUS rework replaced a per-keyword tier with a STATUS, and in doing
      so deleted the LADDER: *"the old scoring system, while complicated, at
      least required building up tests and evidence to reach next tiers for a
      keyword"*, and *"lack of items at a tier for a command does not actually
      mean there are no defects"*. Both correct. **The status column measures
      the ABSENCE of filed items, and I had given that a green tick reading
      COVERED** — which rewards silence, exactly inverting what the old scheme
      demanded.
      📏 **MEASURED, and it is how big the loss was:** **32 keywords carry a
      scored `PROVES-T3:` row and the new sheet rendered that fact ZERO times.**
      The machinery (`kwsweep_t3`) was intact throughout; only the rendering
      dropped it.
      ✅ **FIXED THE SAME DAY:** `🟢 COVERED` is `🟢 NO KNOWN GAP` again (the
      phrase the old text emitter used, which I had deleted), and a **PROVEN**
      column carries the ladder: `T1✓ T2— T3✓ T4— T5— T6—`. A rung is ticked
      only by a DECLARED, SCORED row and never by silence — and T1 additionally
      requires knife-proven CONNECTEDNESS, so `LOF` reads `1/1 forms` and `T1—`.
      | rung | proving it |
      |---|---|
      | T1 — every authored form agrees, knife-proven | **139** of 159 |
      | T3 — a `PROVES-T3:` row scored vs the reference | **32** of 159 |
      | T2 / T4 / T5 / T6 — **no row type exists** | **0** of 159 |
      🎯 **SO THE FOUR ZEROES ARE THIS ITEM.** Nothing in this tree has shown
      that ANY keyword runs in reasonable time, at on-par speed, within the
      reference's RAM, or handles its exhaustive error set. That work was
      invisible while the sheet had one column; it is now a row of dashes 159
      wide. ~~⚠️ **T4 is additionally gated on the charter question** (*does
      faithful include speed?*), so T4's row type cannot even be specified until
      that is answered.~~ 🔴 **STALE WHEN WRITTEN:** that question had been
      answered on 2026-09-22 (*"yes but that is tier 4"*, TIER 4 item), and this
      sentence carried it as open for two days — a stale blocker outliving what
      made it true.
      🔬 **PINNED BY A NEGATIVE CONTROL** (`S36e`): ~~T2/T4/T5/T6~~ **T4/T5/T6**
      CANNOT be ticked (flipped 2026-09-24 when T2's row type landed — the
      deliberate act this sentence asked for). If that arm ever fires, a proving
      row type was added — which must be a deliberate act carrying its own
      definition of what the row proves, not a side effect of some other change.
