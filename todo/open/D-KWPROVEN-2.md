- [ ] 🎚️ **T6 — WHAT BOUNDS "THE EXHAUSTIVE ERROR SET"? THE ONE RUNG STILL
      WITHOUT A DEFINITION (split from D-KWPROVEN, 2026-09-24).**
      🎚️ TIER 1 — it is part of the bar every other item is measured against.
      🏗️ **RULED BY JOOST 2026-09-27: THE REFERENCE'S ERRORS, DOCUMENTED FORMS.** A keyword
      proves T6 when, for each documented syntax form, it has one row per
      distinct error the reference raises for that form (wrong type, out of
      range, missing argument, illegal direct, …), each matching the reference's
      error CODE and LINE. Finite per keyword, enumerable by probing the
      reference. 🤖 **AUTONOMOUS now**: build the T6 row type (same shape as
      D-KWPROVEN's T2/T5) and its per-keyword enumeration.
      🤖 **AUTONOMOUS** — ruled by Joost 2026-09-27 (above); a carve comes first.
      Was: 🙋 **NEEDS-JOOST** — rung definitions are charter-level. T2, T4 and T5
      were ruled on 2026-09-24; T6 was not addressed and stays open. The
      question: the set of errors a keyword can raise has no obvious finite
      bound, so what row set would count as having PROVED it — every error
      code the reference raises for that keyword's documented forms, or
      something wider?

      🟢 **D-KWT6 S1 SHIPPED (2026-09-27): THE ROW TYPE AND THE RUNG RULE — 0
      KEYWORDS MEASURED YET, ON PURPOSE.**
      * **The denominator** is [`tools/kwerrset.py`](tools/kwerrset.py): keyword
        → form → the error codes the REFERENCE raised, each entry written from a
        probe run with its provenance. EMPTY today; absence is UNRATED, never an
        empty set.
      * **The row** is a kwsweep `PROVES-T6:<code>` prefix tag on a `stored` row
        with a `FORM:` tag; the pin records `proves: "T6"` and `t6code`.
        `main` REFUSES before running anything a T6 row that is not `stored`, has
        no `FORM:`, has a malformed code, or carries the tag outside the prefix run
        (where the parser would silently drop it) — four planted rows, four
        refusals, `rc 2`.
      * **The rung** (`tools/tier_table.py` `t6_keywords`): CONNECTED, every
        authored form measured, a non-zero denominator, and every (form, code)
        covered by a SUPPORTED row. S36e flipped DELIBERATELY for T6; six arms
        S36t–S36y, five NEGATIVE; a mutation forcing T6 false turns S36t RED.
      ~~➡️ **NEXT, S2: the ENUMERATION probe** — per keyword form, apply a fixed
      fault battery on the REFERENCE (wrong type, each argument out of range,
      missing / extra argument, illegal direct where it applies), record the
      DISTINCT codes into `kwerrset.py`, then write the rows. Start with one
      keyword that is already T1–T3 so the first T6 tick is real evidence.~~
      🟢 **D-KWT6 S2 — BATCH 1 SHIPPED (2026-09-27): T6 PROVEN FOR 10 OF 159.**
      [`scratchpad/t6enum_probe.py`](scratchpad/t6enum_probe.py) traps each fault
      with `ON ERROR` and reads the reference's own `ERR`/`ERL` (no message table)
      → [`scratchpad/t6enum_run.out`](scratchpad/t6enum_run.out),
      [`scratchpad/t6enum_exp.out`](scratchpad/t6enum_exp.out). Ten one-form
      functions already at level 3; zerobas matched the VG-8020 on all 48 cases.
      | set | keywords |
      |---|---|
      | {2, 13} | ABS, SGN, INT, LEN |
      | {2, 5, 13} | SQR, LOG, ASC |
      | {2, 6, 13} | EXP, PEEK |
      | {2, 5, 6, 13} | CHR$ |
      27 `PROVES-T6:` rows (`t6<kw><code>`, `stored`, the probe's own lines), 27/27
      SUPPORTED with ` in 10` in the reading; kwsweep 382 → 409 SUPPORTED; the
      sheet reads **T6 10 of 159** and every level is unchanged at 3 (T4 has no
      row type, so the ladder stops there). The 27 read UNTIMEABLE in kwtime, as an
      error row should.
      🔮 Predicted every set right EXCEPT EXP: `EXP(99)` is ~1E43, inside MSX's
      ~1E63 range — my arithmetic — so the first battery never reached EXP's
      overflow and its set read {2, 13}. `EXP(150)` added: {2, 6, 13}.
      ⚠️ **THE BATTERY IS THE BOUND**, stated in the probe: type, missing, extra,
      and the named range edges. A code no case elicits is not in the set.
      ~~➡️ **NEXT: batch 2** — multi-argument and statement keywords (LEFT$,
      STRING$, INSTR, MID$, POKE, VPOKE, SOUND, …), where each ARGUMENT needs its
      own faults and statements add illegal-direct.~~
      🟢 **BATCH 2 SHIPPED (2026-09-27): 126 cases, 22 keywords, every argument
      faulted in turn** (`t6enum_probe.py --batch=2` →
      [`scratchpad/t6enum_b2.out`](scratchpad/t6enum_b2.out)). 60 more
      `PROVES-T6:` rows, 60/60 SUPPORTED; sets for 20 keywords in `kwerrset.py`.
      🔴 **THE BATTERY FOUND TWO REAL DIVERGENCES** — filed below as their own
      TIER 6 items: `STRING$(2,"")` (ref 5, zb 2) and `TAN(1E38)` (ref 6, zb OK).
      TAN's code 6 has no row, so TAN correctly does NOT reach T6.
      ⚠️ **MKI$ AND CVI ARE EXCLUDED — WRONG ORACLE.** They are Disk BASIC
      functions; on the diskless VG-8020 `MKI$("A")` and `CVI(5)` read 5, not
      13, and `MKI$(1,1)` 2 where zb says 13. They need the CF-3300 as the
      reference (the probe needs a `--ref` option for it).
      🔮 Misses: a BARE statement (`POKE`, `VPOKE`, `SOUND`) is **24** Missing
      operand on both, not 2; `TAN(1E38)` overflows on the reference; the MKI$/CVI
      type faults read 5 (the oracle problem above).
      ~~➡️ **NEXT:** MKI$/CVI (and the other disk functions) on the CF-3300; then
      the multi-FORM keywords (INSTR, MID$, VAL, …), whose rows must name each
      form.~~
      🟢 **BATCH 3 SHIPPED (2026-09-27): the Disk BASIC functions ON THE CF-3300**
      (`t6enum_probe.py --batch=3` → [`scratchpad/t6enum_b3.out`](scratchpad/t6enum_b3.out);
      zerobas's DISK build, the pairing kwsweep's `NEEDS-DISK:` rows use). 32 cases,
      7 sets, 18 `NEEDS-DISK: PROVES-T6:` rows, 18/18 SUPPORTED. CVI, CVS, CVD,
      MKS$ and MKD$ reach T6; MKI$ and DSKF do not — their missing code's only
      case DIVERGES.
      🔴 **THREE MORE REAL DIVERGENCES**, filed below: `MKI$(32768)` (ref 6
      Overflow, zb accepts it), `MK?$(1,1)` (ref 2, zb 13, all three MK$
      functions) and `DSKF(-1)`/`DSKF(256)` (ref 5, zb 62 Bad drive name).
      🔮 Every reference value predicted right; the three divergences were not
      predicted — they are zerobas's.
      ~~➡️ **NEXT:** the multi-FORM keywords (INSTR, MID$, VAL, …), whose rows must
      name each form; then statements with channel/line arguments.~~
      🟢 **BATCH 4 SHIPPED (2026-09-27): statements and multi-form keywords**
      (`t6enum_probe.py --batch=4` → [`scratchpad/t6enum_b4.out`](scratchpad/t6enum_b4.out)).
      Their errors are SCENARIOS, so each (keyword, form) has hand-written ONE-LINE
      cases (set-up on the same line); `RETURN`'s line form reaches its own 8 by
      recursing into its line (`IF X=0 THEN X=1:GOSUB 20 ELSE RETURN 99`). 80
      cases, 10 keywords / 17 forms, 43 rows — each the FIRST case that AGREED for
      its code — 43/43 SUPPORTED.
      🔴 **THREE MORE DIVERGENCES**, filed below: `MID$("AB",1,1,1)` and
      `MID$(5,1)="X"` (ref 2, zb 13 — the D-MKEXTRA shape) and `READ A:DATA 1E99`
      (ref 6 Overflow, zb 2). MID$'s substring-3arg code 2 and READ's code 6 have no
      agreeing case, so MID$ and READ stay T6-.
      ⚠️ VAL and FRE are NOT enumerable this way: their "forms" are argument
      CONTENT/type, which no syntax fault can tell apart — a question for the
      form list, not for this probe.
      🔮 Misses: `DIM A(10000)` is 9 Subscript out of range, not 7; `RESTORE,` is
      8 on both.
      🟢 **BATCH 5 SHIPPED (2026-09-27): 25 one-form operators, bare statements
      and readers** (`--batch=5` → [`scratchpad/t6enum_b5.out`](scratchpad/t6enum_b5.out)),
      87 cases, 46 rows 46/46 SUPPORTED. 🔴 **FIVE DIVERGENCES**, filed above the
      MID$ item: D-LETNUM (`LET 5=1` CORRUPTS the screen — TIER 3), D-ERRORARG,
      D-BAREEXTRA (`CLS 1` clears first, `END 1` ends silently), D-POSDUMMY.
      CLS, END and ERROR stay T6- (codes with no agreeing case). Five of the
      cases first read `<no reading>` on zerobas; the raw screens, not the
      reader, said why.
      🔮 Misses: an operator missing its right side is **24** Missing operand, not
      2; `POS("A")` is accepted on the reference.
      🟢 **BATCH 6 SHIPPED (2026-09-27): multi-form STATEMENTS** — FOR, IF, CLEAR,
      COLOR, SCREEN, LOCATE, TIME, DEFINT/SNG/DBL/STR (`--batch=6` →
      [`scratchpad/t6enum_b6.out`](scratchpad/t6enum_b6.out)), 107 cases, 56 rows,
      56/56 SUPPORTED. 🔴 **IT FOUND THE WORST BUG OF THE DAY — `CLEAR 30000`
      HUNG ZEROBAS** (D-CLEARFIT, FIXED above, funded by the D-CARVEFO carve),
      plus D-IFGOTOBARE and D-CLEAR3ARG (filed). T6 64 → **75** — predicted
      ~73 and MISSED by assuming D-CLEAR3ARG blocked CLEAR; `CLEAR,` covers its
      code 2. ⚠️ RESUME is NOT measurable by
      this probe — "RESUME without error" is untrappable on both machines, so it
      stays unrated; three valid `LOCATE` cases read nothing on the reference
      because the cursor move put the output above the reader's window.
      🔴 **AND MY S1 READER WAS WRONG, CAUGHT BY THE COUNT:** predicted T6 42, the
      sheet read **40** — NEXT and RETURN missing with every row SUPPORTED.
      `kwsweep_t6_cover` used `stmt_keyword` (the FIRST keyword), so
      `FOR I=1 TO 2:NEXT J` counted for FOR and `IF … ELSE RETURN 99` for IF. It
      now uses `stmt_subject` with the row's declared `SUBJECT:` (as the forms
      reader always did), the four scenario rows declare it, and arm S36z pins it
      (NEGATIVE half: undeclared, it is NEVER guessed as NEXT; a mutation back to
      `stmt_keyword` turns S36z RED). Re-read: **T6 42 of 159**.
      🟢 **BATCH 7 SHIPPED (2026-09-27): graphics statements, device functions,
      ON/KEY/FN, PLAY and SET** (`--batch=7` → [`scratchpad/t6enum_b7.out`](scratchpad/t6enum_b7.out)),
      226 cases over 22 keywords; 125 rows for the 20 whose every form read
      whole. **120 SUPPORTED, 5 EXTRA** (zerobas accepts what the reference
      refuses): D-DEFUSRRANGE, D-DEFFNPARAM and `STOP 1` (D-BAREEXTRA), filed
      below — they block DEF USR, DEF FN and STOP.
      ⛔ **CIRCLE and PAINT are left out on purpose:** `CIRCLE(99,99),-5` and
      both `PAINT(1,1),1,16` / `PAINT(1,1),1,1,1` gave the REFERENCE no reading,
      so those forms' sets are not known to be complete.
      🔴 **THE 46 GRAPHICS ROWS FOUND A TIER 1 BUG BEFORE THEY PROVED ANYTHING:**
      they read nothing on EITHER side, and the raw screens said why — an
      untrapped error in SCREEN 2 prints `Illegal function call in 10` on the
      VG-8020 and NOTHING on zerobas (D-GFXERRMSG, fixed, below). And the
      apparatus had to learn one thing: the return to the text screen clears
      the echoed RUN on both machines, so those rows read from the message's
      first word (`NOECHO:Illegal` …); `row_t6_code` steps over a leading
      `NOECHO:` itself (the shared prefix parser does not, on purpose).
      📊 **T6 75 → 90 of 159** (tier sheet, knife re-pinned on the final ROM).
      🟢 **7b (same night): CIRCLE and PAINT, once their three unread cases were
      read ALONE** ([`scratchpad/t6enum_b7_rerun.out`](scratchpad/t6enum_b7_rerun.out)):
      `PAINT(1,1),1,16` is a slow fill that completes and `CIRCLE(99,99),-5` a
      huge circle that completes after MINUTES — neither an error — while
      `PAINT(1,1),1,1,1` is 2, which the batch window had missed. 18 rows, 17
      SUPPORTED; **T6 90 → 91** (PAINT). CIRCLE stays T6- on a real divergence,
      D-CIRCANGLE, and zerobas's negative-radius refusal is D-CIRCNEGR.
      🟢 **BATCH 8 SHIPPED (2026-09-28): Disk BASIC statements, on the CF-3300**
      (`--batch=8` → [`scratchpad/t6enum_b8.out`](scratchpad/t6enum_b8.out); per
      case on both machines → [`scratchpad/t6enum_b8_zb.out`](scratchpad/t6enum_b8_zb.out)),
      126 cases over 27 keywords; RUN left out (its line form's errors are
      untrappable to the probe). **94 agree; the other 32 are D-DISKERRS**, whose
      pairs stay in the denominator, so those keywords stay T6-. **80 rows** for
      the agreeing pairs, **80/80 SUPPORTED. T6 91 → 102 of 159** (predicted ~102).
      🔴 **THE FIRST RUN PUT ALL 101 ROWS IN AND READ 47 EXTRAs, AND THEY WERE
      NOT DIVERGENCES:** a contiguous run, and cases like `LOAD 5` that agree
      when booted alone. It was D-RUNCLOSE (fixed, above): each stored row is a
      RUN, zerobas's RUN never closed the channels the previous row opened, and
      they leaked forward — four OLD rows broke beside them. Two apparatus
      lessons, both kept: a new disk batch is checked PER CASE on both machines
      before its rows join the batched sweep, and only agreeing pairs become
      rows (a wrong row poisons its neighbours in batch mode).
      🔴 **AND THE KNIFE PICKED AN ERROR ROW AGAIN:** INPUT$'s witness moved to
      `t8inputconsole13`. INPUT$ has no token, so its row is found by its
      `SUBJECT:` tag in a THIRD enumerator branch that the D-KWT6 skip had not
      reached; it skips T6 rows now, and the witness is `inputdol_b` again.
      🔮 Predicted +17 keywords, got +15: `ON GOTO` / `ON GOSUB` are composites
      the sheet scores in its composite table, and PAD and PLAY are held by
      their own open items.
      🔮 Predicted ~110 of 125 SUPPORTED with graphics divergences; it was 120
      with NONE in graphics — the misses were all argument checks elsewhere.
      And a first cut of the row NAMES collided (`colour-explicit` /
      `colour-default` cut to six letters); the duplicate-key guard refused it.
