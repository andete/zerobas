- [ ] 🔬 **COMPARE RAM *USAGE* AGAINST THE REFERENCE, CELL BY CELL — AND JOOST'S
      HUNCH IS THE HYPOTHESIS TO SCORE**
      🎚️ TIER 4 — RAM usage: this item is the measurement the RAM rung is
      derived from (re-tagged 2026-09-24, D-TIERSWAP; it had read TIER 2 —
      *"a cost comparison that feeds the eviction's remaining RAM blockers"* —
      which put the rung's own measurement at another tier's priority).
      🔭 **SCOPE WIDENED BY JOOST'S RULINGS:** *"the whole RAM map"*
      (2026-09-24), undocumented regions included (2026-09-22), against the
      VG-8020 (CF-3300 for disk-only cells), for all three goals — free memory,
      addresses, economy (D-TIER5RAM). The marker line below says DOCUMENTED
      work area; that is its 09-21 scope, and the measurement now covers
      both.
      🤖 **AUTONOMOUS** — measurement of the DOCUMENTED work area, which the
      clean-room line explicitly permits.
      🟢 **THE "NOT NOW" IS LIFTED, 2026-09-22.** Filed at his request on
      2026-09-21 as *"This is not something for now, but it may be valuable to
      compare variable usage between our implementation and reference and if we
      differ adjust if needed"* — and his TIER 5 ruling the next day asks for
      exactly this, widened to the UNDOCUMENTED regions. **This item is the
      measurement that populates the TIER 5 rung above** (TIER 4 since
      2026-09-24, D-TIERSWAP). 🏗️ **CONFIRMED
      2026-09-24 (D-KWPROVEN):** asked what proves T5, Joost answered ***"The
      whole RAM map"*** — so per-keyword T4 (T5 when he said it; swapped the same day) is DERIVED from this comparison,
      not measured separately. Then, the same day: *"I have a hunch reference is very economical
      with RAM."*
      🔮 **THE HUNCH IS A PREDICTION AND MUST BE SCORED AS ONE, INCLUDING A
      MISS.** State it before the run: *the reference writes FEWER distinct RAM
      cells than zerobas for the same BASIC operation.* ⚠️ Distrust it — it is
      the comfortable answer, and "economical" has at least three different
      meanings (fewer cells touched, fewer cells RESERVED, or state kept on the
      stack instead of in a named cell) which will not all point the same way.
      🟢 **ONE INSTANCE IS ALREADY CONFIRMED AND IT IS OURS:** the PAINT span
      stack is a FIXED `GFX_PSTK_CAP * GFX_PSTK_ENTSZ` = 120 × 3 = 360 B array,
      where the reference grows its spans DOWN FROM `STKTOP` and costs nothing
      while PAINT is not running (`docs/spec-basic-graphics-g5.md` D3). That is
      the lever step 10 is still waiting on, so this item and that one are the
      same question asked twice.
      🔬 **THE METHOD EXISTS — IT IS D-DISKWRITES's, POINTED SOMEWHERE ELSE.**
      `scratchpad/diskwrites_probe.py` already arms a `write_mem` watchpoint over
      a band, brackets it between two breakpoints and reports every address
      written, with a positive control that must fire. Point it at
      `$F380..$FFFF` (and at each machine's own workspace) on the CF-3300 and on
      zerobas, run the SAME typed BASIC on both, and diff the written sets.
      ⚠️ **AND `docs/ram-map.md` IS THE OTHER HALF OF THE DENOMINATOR**: it lists
      what WE declare. A cell the reference writes that we never named is the
      interesting direction, and so is a cell we reserve that it never touches.
      🔴 **CLEAN ROOM: THIS IS ON THE PERMITTED SIDE, BUT ONLY JUST.** Work-area
      RAM addresses and CONTENTS are readable (`expansion-protocol.md` §7). ROM
      bytes are not, and neither are the bytes of the reference's RAM-RESIDENT
      code (§8.5) — so a cell inside one of those five clusters is reported as
      belonging to a cluster, never decoded.
      ⚠️ **A DIFFERENCE IS NOT AUTOMATICALLY A DEFECT.** Some of our cells exist
      because we made a different, deliberate architectural choice (the channel
      context, the temp-descriptor pool). The output is a priced comparison for
      Joost, not a list of things to change.
      🔬 **D-RAMFOOT, THE FIRST MEASUREMENT (2026-09-24,
      `scratchpad/ramfoot_probe.py`, `scratchpad/ramfoot_run.out`).** 16
      one-line operations, VG-8020 vs zerobas, every address in `$E001..$FFFF`
      written inside a window the program opens and closes itself
      (`POKE&HE000,201/202`, keyed by a per-case TAG so a lost window cannot
      shift the rows). Stack pushes are classified by SP and excluded; an empty
      window gives the background; a positive `POKE&HE001,7` must record
      `$E001` on both or the run REFUSES. **Deterministic** — two runs diff
      identical.
      🔴 **THE INTERRUPT HAD TO BE MEASURED, NOT GUESSED, AND TWO CLASSIFIERS
      FAILED FIRST.** zerobas takes 8–14 ms from the TIME tick to its window,
      so nearly every zerobas window holds a 50 Hz interrupt (H.TIMI hits are
      counted per window). "Written only with interrupts off" caught
      interpreter cells (zerobas writes `ARYTAB`/`FRETOP`/`CTLLIM` under DI),
      and "near a tick" per op caught `FORCLR` on `COLOR`. What works is an
      `isr` control: a wait loop spans one tick, and a cell EVERY write of
      which sits within 0.3 ms before to 3 ms after an H.TIMI hit is the
      interrupt's. **Interrupt signature: VG-8020 31 cells, zerobas 24** —
      `STATFL`, `JIFFY`, the `NEWKEY` rows on both.
      🔮 **JOOST'S HUNCH, SCORED: HIT.** *"The reference writes FEWER distinct
      cells for the same operation"* — **on 12 of 16 ops; 527 cells vs 843
      in total (zerobas 1.6×)**. The four exceptions: `PRINT 1` (39 vs 8),
      `CLS` (69 vs 26), `LOCATE` (5 vs 4), `STR$` (47 vs 42). My own
      prediction (fewer `$F380+` cells here, more in total, not on every op)
      — HIT on all three parts.
      📍 **GOAL (b), SAME ADDRESSES — THE STRUCTURAL FINDING.** For
      arithmetic, variables and strings the reference writes the DOCUMENTED
      work area (`$F662`, `$F678..`, `$F698..`, `$F6A5..`, `$F6C4..$F6C7`,
      `$F7B4..`, `$F7F6..$F84F` recur), and zerobas writes almost none of it:
      its FAC/ARG/conversion/variable state lives in its OWN workspace
      (`FAC $F01C`, `ARGA $F06A`, `CVT $F0C8`, `ARYTAB $E1C0`, `VARTYPE
      $F14E` …). The reference writes NOTHING below `$F380` except its stack.
      ⚠️ So a program that PEEKs those documented cells reads the reference's
      state there and zerobas's stale bytes — an ADDRESS divergence per cell,
      to be named from the MSX2 TH work-area table and cross-checked against
      `make sysvarsweep` (which scores documented cells) before any is filed.
      ➕ **zerobas also writes `SLTTBL3` (`$FCC8`) and the secondary-slot
      register `$FFFF` on most ops** — its sub-ROM tenant calls; the reference
      writes neither for any of the 16.
      🏷 **NAMED (`scratchpad/ramfoot_names.py` → `scratchpad/ramfoot_names.out`,
      offline, names from C-BIOS's `systemvars.asm` — sysvarsweep's own
      generator):** **186 reference-only documented bytes in 29 published
      variables.** Three kinds, by what a program can SEE:
      | kind | variables | written by |
      |---|---|---|
      | **pointers a program PEEKs** | `STREND` `ARYTAB`† `TEMPPT` `TEMPST` `DSCTMP` `FRETOP`† `RNDX` | every variable op (STREND 12/16, ARYTAB 11/16); strings; `RND` |
      | **screen/device state** | `ATRBYT` `TTYPOS` `ESCCNT` `PRTFLG` `CNSDFG` `FNKSWI` `LINWRK` `GRPHED` | `COLOR`, `LOCATE`, `PRINT`, `CLS` |
      | **interpreter scratch** | `DIMFLG` `SUBFLG` `TEMP` `PRMFLG` `ARYTA2` `ENDFOR` `DAC` `ARG` `HOLD` `HOLD2` `HOLD8` `FBUFFR` `DECCNT` `PTRFIL` | arithmetic, `FOR`, `PRINT` |
      † already DECIDED once: D-REHOME (2026-08-01) rejected re-homing
      `FRETOP` and `ARYTAB` (REJECT-GROUP) — under the charter of that date,
      before goal (b) *same addresses* was ruled (2026-09-24).
      ⚠️ Maintaining a published cell costs ROM bytes on every path that
      changes it, and main has 13 B. A scratch cell no program reads buys goal
      (b) on paper and nothing a user can see.
      ~~🙋 **BACK TO JOOST (the rung's own rule):** which of the three kinds
      should zerobas maintain at the published address — and does goal (b)
      reopen D-REHOME's two rejections?~~
      🏗️ **RULED BY JOOST, 2026-09-24: *"All 29"*** — full address fidelity,
      scratch included, chosen over "pointers only" (the recommendation),
      "pointers + screen state" and "none for now". It REOPENS D-REHOME's
      `FRETOP`/`ARYTAB` rejections.
      🤖 **AUTONOMOUS — D-ADDR29, the arc it starts:** (1) a per-variable
      table — published name/address/width, zerobas's equivalent (name,
      address, width, FORMAT), any zerobas cell already AT the target, the
      D-REHOME verdict and its reason; (2) re-home by EQUATE where an
      equivalent exists with the same format (0 ROM bytes, and it frees our own
      workspace — goal (a) for free); (3) price the rest (a variable zerobas
      has no equivalent of must be WRITTEN, which costs ROM against the 13 B).
      ⚠️ A format mismatch (e.g. zerobas's FAC vs the BCD `DAC`) or a collision
      at the target is not decided here — those come back as priced choices.
      📋 **STEP (1) DONE — [`docs/spec-basic-addr29.md`](docs/spec-basic-addr29.md)**
      (2026-09-24): every variable classified E (equate, 0 B) / W (write) /
      N (new state) / ✋ (Joost's choice). **No target collides with a zerobas
      cell.** Tally: 1 plain E (`FBUFFR`), the pointer chain (moves TOGETHER —
      D-REHOME's group argument still holds, and `VARTAB` joins it), 5 ✋
      (`DAC` integer layout + the USR convention, `TEMPST` capacity 10 vs 32,
      `ARG`/`RNDX` formats, the N-set order), 4 W, 16 N. Slice order in its §5.
      🏗️ **THE ✋ CHOICES, RULED BY JOOST 2026-09-24 — all four as
      recommended** (spec §4.1): `DAC` FULL (ints at `DAC+2`, USR reads DAC —
      supersedes `usr.asm`'s HL convention); `TEMPST` pool SHRINKS to 10;
      `RNDX` now, `ARG` later; the N set OBSERVABLE-first.
      ~~🤖 **AUTONOMOUS — next slice: S1 `FBUFFR`** (spec §5), then the pointer
      chain.~~ ⚠️ Every ROM-growing slice needs a carve first (13 B).
      🟢 **S1 `FBUFFR` SHIPPED (2026-09-24), 0 ROM bytes — and the premise was
      measured first and was HALF wrong.** `scratchpad/fbuffr_probe.py`
      (`fbuffr_run.out` before, `fbuffr_after.out` after): the VG-8020 keeps
      `00` at `FBUFFR+0` and the text from `+1`, so the equate is `FOUTBUF =
      FBUFFR+1`, not `= FBUFFR`. After it, `PRINT 3.25` leaves the reference's
      exact text; the `SQRT_R`/`HORNER_*` aliases moved with it (the reference
      uses FBUFFR as SIN scratch too); `$F024..$F03B` is freed.
      📋 **STILL W (each a write, filed here, not done):** zerobas's `STR$`
      keeps PRINT's trailing space (` 123.5 ` vs ` 123.5`); INTEGERS are
      formatted in `NUMBUF`, not FBUFFR (`STR$(-7)`, `PRINT 42` leave stale
      text); `FBUFFR+0` is never written.
      ~~➡️ **NEXT: S2, the pointer chain** (spec §2/§5).~~
      🟢 **S2 THE POINTER CHAIN SHIPPED (2026-09-25) — main 3 B, sub 3 B, and
      the premise measured first** (`scratchpad/ptrchain_probe.py`, 9 states
      on the VG-8020 vs zerobas: `ptrchain_run.out` before, `ptrchain_after.out`
      after). zerobas already KEPT all three: `VARTAB` = `(PRGEND)+2`, `ARYTAB`
      byte-identical, `STREND` = `CTLLIM`−2 (its ARYEND) in EVERY state.
      So `ARYTAB` moved to `$F6C4` by EQUATE (`$E1C0` vacated), `STREND` is
      stored in `strheap_ctllim` (sub; every allocator success and the reset)
      and `VARTAB` beside `ARYTAB` in `vars_reset` (main low region).
      **After: DIFF 0/9.** D-REHOME's REJECT-GROUP condition is met — the whole
      chain moved together.
      🔮 Predicted 9/9 on the first cut — **MISS, 8/9**: `VARTAB` was stored in
      `sh_ctl_reset` (clear_vars), and a program EDIT never reaches clear_vars
      (`vars_reset` says so in as many words), so `program` read `$8003` against
      `$8013`. Moving the store to `vars_reset` fixed it.
      📏 sysvarsweep: `ARYTAB`/`VARTAB`/`STREND` HONOURED, `$E1C0` QUIET; its
      C-PRIV control was PINNED ON `$E1C0` "because it is a REJECT verdict"
      and is re-aimed at `CTLLIM` `$E056` (private by design — the reference
      has no control-pool floor). D-RAMFOOT re-run: reference-only documented
      bytes **186 in 29 variables → 182 in 27** (`scratchpad/s2_ramfoot_names.out`).
      📋 **SPLIT OUT, S2b `FRETOP`/`MEMSIZ`:** zerobas's heap reads a constant
      **12 B more "used"** than the reference in every state (`ptrchain_str.out`:
      4 vs 16 at boot, +5 for `A$="HELLO"` on both); the ceiling is exactly
      `$DB00`, so the 12 B is inside the heap (likely per-record overhead on the
      typed loop's temporaries) — measure what they are before any move.
      📏 **S2b's 12 B, EXPLAINED (2026-09-25, `scratchpad/strtemp_probe.py` →
      `scratchpad/strtemp_run.out`, a readout that builds no string): DIFF
      4/8, and every DIFF is zerobas holding MORE heap, never less.** Kept
      strings match (`A$="HELLO"` 5/5, `"AB"+"CD"` 4/4, a copy 6/6). Two
      policies differ: (a) a LITERAL argument of a string function is copied
      into the heap — `PRINT MID$("XYZ",2)` leaves 3 B on zerobas, 0 on the
      reference, and `A$=MID$("ABCDEF",2,3)` holds 6 against 3; (b) a
      released temporary is not handed back — `X=LEN(MID$(...)+"Q")` holds 10
      against 3. The reference evidently reclaims a temporary released while
      newest. `FRE("")` still matches because it collects first; the
      difference is FRETOP's value and how often zerobas collects.
      🔮 Predicted DIFF 3/8 (temporaries only) — **MISS: 4/8**, `mid_kept`
      too; the literal snapshot (a) was not in my hypothesis.
      ⚠️ **SO S2b IS NOT AN EQUATE MOVE.** Publishing zerobas's `FRETOP` at
      `$F69B` today would show a value that drifts from the reference after
      any temporary. Matching it means changing the string engine's
      temporary policy (reference-like reclaim of the newest released
      temporary; point at a literal instead of copying it) — goal (c)
      economy at the temporary level, a sub-ROM string-engine slice, priced
      when picked up.
      ~~➡️ **NEXT: S3 `CNSDFG`/`ATRBYT` writes** (spec §5); S2b is the temporary
      policy above.~~
      🟢 **S3 SHIPPED FOR `ATRBYT` (2026-09-25), 6 B page 1 — and the premise
      halved it** (`scratchpad/s3cells_probe.py`: `s3cells_run.out` before,
      `s3cells_after.out` after). RAMFOOT counts WRITES, so the question was
      what a PEEK reads: the reference's `COLOR` sets `ATRBYT` to the
      foreground (`COLOR 5` → 5, `COLOR 9` in SCREEN 2 → 9, `COLOR ,1` leaves
      15); zerobas never did. `clr_apply` now copies `FORCLR` into `ATRBYT`
      after the commit. **`ATRBYT` 9/9 after.**
      🔮 Predicted `CNSDFG` SAME everywhere (CLS only re-writes it) — **MISS**:
      zerobas BOOTS with `CNSDFG` = 0 against the reference's 255, and that is
      not a missing write — zerobas really boots with the function-key line
      HIDDEN (the VG-8020 shows `color auto goto list run`). `KEY ON`/`KEY OFF`
      already match. Filed as its own item, D-KEYBOOT, below; `CNSDFG` follows
      from it.
      ~~➡️ **NEXT: the N set, observable first** (spec §4.1: `TTYPOS` `PTRFIL`
      `ESCCNT` `GRPHED` `LINWRK` `FNKSWI`), or `DAC`/`TEMPST`/`RNDX` as ruled.~~
      🟢 **THE OBSERVABLE N SET, 2026-09-25 — 5 of 6 now read as the
      reference's, for 8 B main + one C-BIOS patch** (`scratchpad/nset_probe.py`:
      `nset_run.out` before, `nset_after.out` after; each cell captured into a
      variable on the operation's own line, so the readout cannot move it):
      | cell | before | what it was | now |
      |---|---|---|---|
      | `PTRFIL` `ESCCNT` `GRPHED` | 7/7 SAME | written transiently, read 0 after — **nothing to do** | SAME |
      | `TTYPOS` | 8/8 DIFF | C-BIOS's CHPUT mirrors the 1-BASED `CSRX` into it; the reference keeps BASIC's 0-BASED print column, and `LOCATE` moves it | merge patch at `$11CF` (`call ttypos_col`, `basic/islands.asm`; C-BIOS's own `ld (TTYPOS),a` stores `CSRX`−1) + `LOCATE` stores the column (3 B) — **7/7** |
      | `FNKSWI` | 7/8 DIFF | the reference's steady 1 (F1..F5 shown); one earlier 0 after `LOCATE` did not reproduce — its interrupt maintains the cell | boot stores 1 beside D-KEYBOOT's flags (5 B) — **7/7** |
      | `LINWRK` | 8/8 DIFF | the reference's key-line render SCRATCH (`$6F63` = "co" of "color" after CLS, `$FFFF` otherwise; timing-dependent) | **not mimicked** — no program reads a scratch line buffer |
      📏 `make sysvarsweep` agrees independently: its boot BASE-DIFF went
      **159 → 157 B** (BASIC-owned 80 → 78) — `TTYPOS` and `FNKSWI` left it.
      🔴 `check_dead_code.py` fix (14): a stub the merge patches INTO C-BIOS is
      entered by C-BIOS, so it is a declared root (`PATCH_ROOTS`), asserted to
      resolve like `init`.
      📋 **FILED, NOT FIXED:** (a) `PRINT CHR$(27);"Y";` then a `PRINT` — the
      reference takes the next two characters as the ESC Y coordinates and
      carries on; zerobas (C-BIOS CHPUT) leaves the rest of the line invisible
      (`esc_half`, both runs); 🎚️ TIER 6. ~~(b) The reference's key line shows
      F6..F10 while SHIFT is held (its interrupt flips `FNKSWI`); zerobas does
      not; 🎚️ TIER 3 — found by reasoning from the cell, NOT yet observed on
      screen: measure before building.~~ 📏 **(b) MEASURED 2026-09-26 —
      REFUTED where it can be measured** (`scratchpad/keyshift_probe.py` →
      `scratchpad/keyshift_run.out`): with SHIFT held while a program runs,
      the VG-8020's row 23 still reads `color auto goto list run` and `FNKSWI`
      stays 1 — the same as with CTRL held (the control). The prompt-idle case
      cannot be read here: the harness releases the key before the capture.
      The same probe found D-KEYCLS (below).
      📏 **THE IDLE PROMPT, MEASURED 2026-10-11: IT *DOES* SWITCH** -- SHIFT held at the
      prompt shows F6..F10 and FNKSWI 0 on the VG-8020; filed as D-KEYSHIFT.
      ~~➡️ **NEXT (ruled order):** `RNDX` (7 vs 8 B, spec §4), `TEMPST` → 10,
      `DAC` full; S2b's temporary policy.~~
      🟢 **`RNDX` SHIPPED (2026-09-25), 0 ROM bytes — the "7 vs 8 B" was one
      leading zero** (`scratchpad/rndx_probe.py`: `rndx_run.out` before,
      `rndx_after.out` after). In 7 states (boot, `RND(1)` once and twice,
      `RND(0)`, `RND(-1)`, `RND(-5)`, `RND(-5)` then `RND(1)`) zerobas's 7
      packed-BCD bytes equalled the VG-8020's `RNDX`+1..+7 EVERY time, and its
      `RNDX`+0 read `00` in all of them. So `RND_SEED` = `RNDX`+1 is an equate,
      `$F142..$F148` returns to the `SUB_INT_RAM` reservation, and zerobas's
      `RNDX`+0 is already 0 at boot. **After: all 8 bytes SAME, 7/7.**
      📏 `make sysvarsweep`: boot BASE-DIFF **157 → 150 B** (the seven seed
      bytes); the knife pin moved only its fingerprint.
      🔴 **AND THE MOVE WOULD HAVE DISARMED A GUARD:** `basic/subromcall.asm`'s
      build-time assert bounded the interrupt trampoline by `RND_SEED −
      SUB_INT_RAM`; with the seed at `$F858` that bound grows to ~1.8 KB and
      guards nothing. It is now bounded by `INT_MAIN_PRIM`, the next CLAIMED
      cell [[a-derived-constant-falsified-from-another-file]].
      ~~➡️ **NEXT (ruled order):** `TEMPST` → 10 (a behaviour change at depth —
      measure where the reference raises first), `DAC` full; S2b's temporary
      policy.~~
      📏 **`TEMPST` → 10: MEASURED, BUILT, AND REVERTED (2026-09-25) — the pool
      is not the limiting quantity** (`scratchpad/tempst_probe.py`:
      `tempst_run.out` at HEAD, `tempst_after.out` with the pool moved). Nested
      `MID$(A$,1)+( … )`: the VG-8020 takes depth **10** and raises `String
      formula too complex` at **11** — 10 descriptors, one per pending level.
      zerobas's 32 went past 14. With the pool moved to `$F67A` at 10 entries
      (equates only, plus `ISRCH_A` pinned — it chained off `TEMPBASE` and
      would have landed on `DSCTMP`/`FRETOP`), zerobas raised the error at
      depth **6**: it holds about TWO temporaries per level where the
      reference holds one — the same policy S2b found (argument snapshots and
      released temporaries are kept to the end of the statement). 🔮 Predicted
      11 on both — **MISS**; shipping it would break programs at depth 6..10,
      so it was reverted, nothing committed.
      🔴 **SO THE ORDER IS: the temporary policy FIRST, then `TEMPST` → 10**,
      which is then an equate move (and frees 96 B). Nested FUNCTION
      arguments (`LEFT$(MID$(…),99)`, 7/7 SAME up to depth 12) do not
      accumulate on either machine.
      ⏱️ **ALSO SEEN, NOT MEASURED:** at HEAD, depth 16 of the same shape takes
      longer than the harness's default step on zerobas (it answers `17`
      correctly with a 20 s step); the reference errors at 11, so there is no
      reference time at that depth. Measure depth 10 on both before calling it
      a speed item.
      ~~➡️ **NEXT:** the temporary policy (S2b) — release an argument snapshot
      and a consumed temporary when they are the newest; then `TEMPST` → 10;
      then `DAC` full.~~
      🟢 **D-TEMPPOL, PART 1 SHIPPED (2026-09-25): CONCATENATION NOW HOLDS ONE
      TEMPORARY PER PENDING LEVEL, AS THE REFERENCE DOES** — 0 B main, 20 B sub:
      (a) `str_concat_tail` takes operand 1 through `str_snapshot_arg` — a
      temp operand 1 IS the accumulator instead of being copied ("one extra
      harmless temp" was the second descriptor per level); (b) `sh_append`
      pops the appended operand when it is the NEWEST temp (`sap_release`) —
      its bytes are in R.
      📏 **WITH THE POOL AT 10 THEY MATCH EXACTLY:** `scratchpad/tempst_probe.py`
      → `scratchpad/tempst_after.out` (⚠️ taken on a build with `TEMPST` = 10 at
      `$F67A` plus both fixes): nested concat, nested arguments and a FLAT
      chain of 14 function operands, **DIFF 0/25**. At the shipped 32 they
      change nothing a program sees, and use less heap:
      `X=LEN(MID$(...)+"Q")` holds 7 B where it held 10 (reference 3;
      `scratchpad/strtemp_pol.out`).
      🔴 **WHY THE POOL IS STILL 32 — MORE CONSUMERS KEEP THEIR TEMPORARY TO
      THE END OF THE STATEMENT** (measured on the 10-pool build, both machines):
      | shape | reference | zerobas @ 10 |
      |---|---|---|
      | `X=LEN(MID$(A$,1))+…` 11 terms | 11 | `String formula too complex` |
      | `PRINT MID$(A$,1);…` 11 items | prints | `String formula too complex` |
      | `X=(MID$(A$,1)="X")+…` **8** terms | -8 | `String formula too complex` (two per compare) |
      A `PRINT` of 11 sliced items is an ordinary program; shipping the pool at
      10 before these release would break it.
      ~~➡️ **NEXT, D-TEMPPOL PART 2:** release the consumed temporary at the
      numeric consumers (`LEN`/`ASC`/`VAL`/`INSTR`…), at each `PRINT` item and
      in string comparison (both operands) — the reference's "free the temp you
      consumed if it is the newest" — then re-run `tempst_probe.py` plus these
      three shapes at 10 and ship `TEMPST` → 10 as the equate move above.~~
      🟢 **D-TEMPPOL PART 2 + `TEMPST` → 10 SHIPPED (2026-09-25) — the pool IS
      the published `TEMPST` (`$F67A`, 10 × 3 B) and matches the VG-8020 at
      every depth: `scratchpad/tempst_probe.py` → `tempst_after.out`, six
      shapes × depths 6..14 (nested concat, nested arguments, flat chain,
      `LEN` sums, `PRINT` items, comparisons), DIFF 0/51.** 96 B of zerobas
      workspace (`$E381..$E3E0`) freed; page 1 −35 B, sub page 0 −11 B.
      What released what (the reference frees a temporary its consumer used up,
      if it is the newest):
      * `LEN`/`ASC`/`VAL` — `ev_str_arg`'s exit jumps to `esa_release_int`
        (page 1): pop `STRPTR` if it is on top, then `flt_int_result`. All
        three read the descriptor before anything allocates; `VAL`'s parse is
        pure RAM. They are its only callers.
      * each `PRINT` item — `ems_print` calls `print_strval_rel` (print, then
        release); other `print_strval` callers are untouched.
      * string comparison — the sub-side `she_cmp_op` pops the right operand,
        then the left (`sh_pop_top`, shared with `sap_release`); and
        `ev_rel_str` KEEPS a left operand that is already a temp instead of
        copying it (`str_snapshot_arg`) — that copy was the last leak: the
        comparison shape still failed at depth 9 with only the pops in.
      ⚠️ Heap usage is UNCHANGED by part 2 (`scratchpad/strtemp_p2.out`,
      4/8 as before): releasing a DESCRIPTOR does not give its body back —
      the bytes wait for a collection, where the reference returns a body at
      the heap's edge at once. That is S2b's remaining half.
      📏 sysvarsweep boot BASE-DIFF 150 (unchanged — `TEMPST` is not a boot
      cell); kwsweep SUPPORTED=382; knife 0 flips.
      ~~➡️ **NEXT:** `DAC` full (spec §4.1), or S2b's heap half (return a
      released body at FRETOP), or `TEMPPT`'s value/direction.~~
      🟢 **`DAC`, THE USR HALF, SHIPPED (2026-09-25) — USR speaks the published
      convention, 67 B page 1.** Measured first: the ENTRY side by
      `probes/basic/basic_probe_usr.py` (the VG-8020 enters with the integer at
      `DAC+2..3`, `DAC+0..1` = 0, `VALTYP` = 2, HL = `$F7F6`, A = 2), the
      RETURN side by `scratchpad/usrdac_probe.py` (the result is DAC per
      `VALTYP`; HL means nothing; a float in DAC with `VALTYP` 4 returns 1.5;
      `USR(1.5)` passes and returns the float). zerobas's own HL convention
      differed on **4/6** stubs — including one I predicted would agree by
      coincidence (`inc`, which READS `DAC+2`: 1 against 6).
      `usr_call` now publishes the argument (a float as FAC's BCD bytes, an int
      at `DAC+2`), enters with HL = DAC and A = `VALTYP`, and reads the result
      back per `VALTYP` (a float through `flt_to_int16`, FAC/FACTYP standing).
      **After: 6/6 SAME** (`scratchpad/usrdac_after.out`), and
      `basic_probe_usr.py` asserts the published convention on BOTH machines
      now (its zerobas rows used to assert the opposite). `tests/test_usr.py`
      checks entry state and the returned argument.
      🟢 **`DAC`, THE FAC HALF, SHIPPED (2026-09-25): `FAC` IS `DAC`
      (`$F7F6`) — an equate, and it GAVE BACK 26 B of page 1.** Every `FAC`
      user is offset-internal (`FAC+0..+6`); `FACTYP` is addressed on its own
      (`push_lhs_frame`, `widen_fac_to`), so nothing depended on `FAC` sitting
      after `FACTYP`/`TKOVF`. USR's two 8-byte copies became copies of DAC onto
      itself and are gone. `$F01C..$F023` freed. `usrdac_probe.py` still 6/6
      (`scratchpad/usrdac_fac.out`).
      ⚠️ `scratchpad/g4_hang_probe.py` still names `0xF01C` — it is a FROZEN
      injector RECORD (`tools/injector-record-allow.txt`) describing its own
      date's layout; editing it turned `injector-check` red, so it stays.
      📏 **WHY THE INTEGER HALF WAITS:** a BASIC program cannot read DAC without
      moving it — `PEEK(&HF7F6)` evaluates its own address and result THROUGH
      the accumulator on the reference — so "ints at `DAC+2` on every integer
      path" has no observable except USR, which is done. It would cost bytes
      at every integer site for a value nothing can see; revisit only with a
      measurement that can.
      📏 **THE N SET'S EVALUATOR SCRATCH, MEASURED (2026-09-25,
      `scratchpad/nset2_probe.py` → `scratchpad/nset2_run.out`): 12 operations,
      16 bytes, each captured into an array on the operation's own line.**
      `DIMFLG` `SUBFLG` `PRMFLG` `PRTFLG` and `DECCNT`+0 already read the same
      after every operation. The other 11 bytes differ in EVERY case — the
      no-op `ctl` included — because what a program reads there is the
      reference's INTERNAL pointers: `ENDFOR` (`$F42E`+) and `TEMP`/`ARYTA2`
      point into its own direct-line buffer and array area, `DSCTMP` is the
      readout's own `MID$` descriptor, `ARG`/`DECCNT`+1 its math scratch.
      Matching them means reproducing the reference's internal layout (its
      line-buffer address, its FOR-frame bookkeeping), not adding stores.
      🔴 **THE FIRST RUN CALLED ALL 16 SAME ON ZERO READINGS:** the readout
      array needed `DIM` (16 > 10), every case raised `Subscript out of range`
      on BOTH machines, and the scorer skipped unread cases and printed SAME.
      The probe now REFUSES when any case has no reading
      [[an-unnamed-outcome-reads-as-no-outcome]].
      🏗️ **RULED BY JOOST, 2026-09-25: *"Stop here"*** — the N set ends with
      `TTYPOS` `FNKSWI` `PTRFIL` `ESCCNT` `GRPHED` `DIMFLG` `SUBFLG` `PRMFLG`
      `PRTFLG`; `ENDFOR` `TEMP` `ARYTA2` `DSCTMP` `ARG` `DECCNT` `HOLD*`
      `LINWRK` stay a STATED divergence (they hold the reference's internal
      pointers and scratch). The question as asked:
      ~~🙋 BACK TO JOOST (the ruling's own order: "observable first", then
      evaluator scratch): these cells ARE readable, but only as the
      reference's internal pointers; matching them is a re-layout of zerobas's
      evaluator, priced in the 100s of bytes and a redesign, for values a
      program can only read as addresses of the reference's own buffers. Stop
      the N set here (done: `TTYPOS` `FNKSWI` `PTRFIL` `ESCCNT` `GRPHED`
      `DIMFLG` `SUBFLG` `PRMFLG` `PRTFLG`), or pursue the scratch?~~
      🟢 **`TEMPPT` SHIPPED (2026-09-25): the temp pool's cursor IS the
      published `TEMPPT` and the pool grows UP from `TEMPST`, as the
      reference's.** At rest the VG-8020 reads `$F67A` (the empty pool's base)
      at `$F678`; zerobas read 0. Now it points at the next free slot:
      push = take the slot at `TEMPPT`, advance by 3, overflow past `TEMPBASE`;
      newest = `TEMPPT`−3 (`sh_pop_top`, `str_release_top`); the GC walks
      `[TEMPPOOL, TEMPPT)`; the statement-boundary resets load `TEMPPOOL`.
      `TEMPTOP` (`$E238`) is gone — renamed everywhere, so no stale use could
      survive with the old meaning; five unit tests re-seed an empty pool as
      `TEMPPT = TEMPPOOL`. `scratchpad/tempst_probe.py` gained a `temppt`
      shape: **DIFF 0/60** (`scratchpad/tempst_pt.out`), depth behaviour
      unchanged. It cost sub page 0 two bytes and page 1 nothing (clean
      build 2026-09-25). sysvarsweep boot BASE-DIFF
      **150 → 148 B** (the two `TEMPPT` bytes).
      ~~➡️ **NEXT (autonomous):** S2b's heap half (return a released body at
      FRETOP) — the last D-ADDR29 item not waiting on Joost.~~
      🟢 **D-S2BHEAP SHIPPED (2026-09-27, loop): THE HEAP'S EDGE IS GIVEN
      BACK — `strtemp_probe` DIFF 4/8 → 1/8** (`scratchpad/strtemp_s2b.out`).
      Two changes, both at the edge (FRETOP) only:
      * `str_release_top` (main page 1, the PRINT-item and `LEN`/`ASC`/`VAL`
        release) moves FRETOP past a popped temp whose body starts AT FRETOP —
        the classic "free the last temporary" rule. Safe because a temp's body
        is uniquely owned (`sh_src_is_temp`'s invariant); the GC's
        `OLD_FRETOP` root test is why that invariant is load-bearing.
      * `she_slice` keeps the kept bytes at the body's HIGH end (was: the
        front), so the trimmed PREFIX is the part at the edge, and a body at
        FRETOP returns it at once. `A$=MID$("ABCDEF",2,3)` now holds 3 B, as
        the reference, where the literal's 6-byte copy used to stay whole.
        That is part (a) of the 12 B, answered without touching the literal
        copy.
      | row | VG-8020 | before | after |
      |---|---|---|---|
      | `mid_kept` | 3 | 6 | **3** |
      | `temp_print` | 0 | 3 | **0** |
      | `temp_len` | 0 | 6 | **0** |
      | `temp_two` `LEN(MID$(..)+"Q")` | 3 | 7 | **0** |
      🔮 Predicted 0/8 — **MISS on `temp_two`**: zerobas now holds 3 B LESS
      than the reference (it held 4 B more). The concat accumulator EXTENDS
      the `MID$` temp in place (D-CONCATPEAK), so the release gives back the
      whole thing; the reference allocates a fresh body under the operand and
      leaves the operand stranded. Matching it would mean de-optimising
      D-CONCATPEAK, which exists to match the reference's PEAK — left as a
      stated divergence in the generous direction.
      ⚠️ The sub-side releases (`sh_pop_top`: a comparison's operands, a
      consumed concat operand) still only pop — sub page 0 has 16 B left after
      this slice (clean build 2026-09-27; main page 1 5 B). No probe row
      separates them yet.
      🔪 **FOUND ON THE WAY — D-KNIFENOREAD, FIXED:** `scratchpad/kwknife.py`
      scored a cut whose sweep printed NO verdict as LOAD-BEARING
      (`v != "SUPPORTED"`). The knife run of the D-BUFMERGE chain read
      NO-VERDICT on EVERY cut and pinned the whole set "knife-proven"; the next
      run read real verdicts and the four explained BLIND rows. Now NO-VERDICT
      is ⚠️ NO-READING, never `connected`, and the run exits 3 naming them. The
      one live case was `CSAVE`: its tape rig REFUSED whenever a side wrote no
      tape — including the knifed subject, which is the defect the row exists to
      see. It now refuses only a REFERENCE without a tape (a broken rig); a
      subject without one reads `<no tape written>`, which can never agree.
      `CSAVE` re-cut → MISSING, LOAD-BEARING.
      ~~➡️ **STILL TO MEASURE:** widen the op list (control flow, graphics, file
      I/O).~~ 📏 **CONTROL FLOW MEASURED 2026-09-26 (loop,
      `scratchpad/fremops_probe.py` → `scratchpad/fremops_run.out`)** — each row
      reads `FRE(0)` INSIDE one running program before and after entering the
      op, variables pre-created, so text and variables cancel:
      | op | VG-8020 | zerobas |
      |---|---|---|
      | one `FOR` frame (two nested: 50 vs 22) | **25 B** | **11 B** |
      | one `GOSUB` (two nested: 14 vs 16) | **7 B** | **8 B** |
      | inside a `DEF FN` call | **14 B** | **13 B** |
      | `ON ERROR` handler entered | 0 | 0 |
      | `DIM S$(10)` / `DIM D#(10)` | 41 / 96 | 41 / 96 |
      🔮 Predicted the arrays SAME and the frames DIFF — HIT; the size and sign
      of each frame gap were not predicted. **A real economy divergence:** a
      program near exhaustion reads different `FRE(0)` values and reaches `Out
      of memory` at a different nesting depth (zerobas ~2.3× deeper in `FOR`,
      slightly shallower in `GOSUB`).
      ~~🙋 **BACK TO JOOST (the rung's rule: adjustments are his):** make the
      frames CHARGE what the reference's do (25 / 7 / 14 — padding the FOR
      frame by 14 B wastes RAM to match), or accept the three as a stated
      divergence.~~ 🏗️ **RULED BY JOOST 2026-09-27: SHRINK OURS ONLY** — shrink only a frame
      where zerobas is BIGGER, so it is never worse than the reference. That is
      GOSUB alone (8 → 7 B). FOR (11 vs 25) and DEF FN (13 vs 14) are already
      smaller here and stay. ⚠️ The question as asked wrongly listed FN as
      bigger too; the ruling's rule ("never worse") decides it, and FN is
      already inside it. ~~🤖 **AUTONOMOUS now**: GOSUB's frame 8 → 7 B,
      re-measured with `scratchpad/fremops_probe.py`.~~
      🔴 **PRICED 2026-09-27 (loop): 8 → 7 IS A REDESIGN, NOT A SHRINK — BACK TO
      JOOST ON THE COST.** The frame is `[CURLINE:2][resume:2][prevGSP:2]
      [prevFSP:2]` (`basic/sysvars.inc` `GOSUB_FRAME`), and its own comment
      says *"Both are needed; neither is derivable from the other"*: `prevGSP`
      chains GOSUB frames because FOR frames interleave, `prevFSP` is D-FORRET's
      restore point. No field fits a byte (`prevFSP` is an arbitrary distance).
      The one 7-byte shape: drop `prevGSP` for a 1-byte TYPE and find the
      previous GOSUB by WALKING the pool, as the reference does — so every frame
      kind (FOR, GOSUB, trap, FN) must become self-describing (FOR 11 → 12 B,
      still under the reference's 25) and RETURN pays a walk (a T5 cost). That
      buys 1 byte per active GOSUB. The ruling was asked as a simple shrink; this
      is the price it did not show.
      🔬 **THE REFERENCE'S MECHANISM, MEASURED THE SAME DAY at Joost's request**
      ([`docs/reference-stack-frames.md`](docs/reference-stack-frames.md), RAM
      and registers only): frames live on the Z80 stack below `STKTOP`, each
      starting with a TYPE TOKEN and with NO chain words — GOSUB =
      `[8D][trap entry 2][caller line 2][resume ptr 2]` (7 B; the trap pointer
      is `$FC7F` for an `ON INTERVAL` GOSUB, `0000` otherwise), FOR =
      `[82][var ptr 2][step sign][kind][step 8][limit 8][line 2][text ptr 2]`
      (25 B for every variable type). RETURN/NEXT must therefore SCAN for the
      token — the walk priced above is exactly the reference's shape.
      ✅ **DONE 2026-10-17: THE GOSUB FRAME IS 7 B** -- not the priced redesign:
      [CURLINE:2][resume:2][prevFSP:2][gdelta:1], prevGSP = prevFSP + gdelta.
      FSP <= GSP always, and the only thing between them is ONE trap service
      record (a trap pushes it right under its own GOSUB frame and moves FSP to
      it), so gdelta is 0 or 3 -- "neither is derivable from the other" was true
      of the words, not of their distance. basic/program.asm gosub_push (+5 B) /
      ret_frame; fremops: GOSUB 7 / 14 on both (scratchpad/gosub7_fremops.out);
      recursion depth 3561 -> 4069 against the VG-8020's 4084, the rest is the
      frame margin (scratchpad/gosubedge_7b.out). 🔴 Knives K-GS1 / K-GS2 (gdelta
      stored 0 / ignored) were MISSED by the whole trap battery
      (scratchpad/gosub7_knife_run1.out); new trapsvc row `int.nest` (a GOSUB
      inside the handler, then the handler's RETURN) reads 1 1 on all three, and
      both knives redden it alone: 2/2 HIT (scratchpad/gosub7_knife.out).
      ✅ **RULED: match the reference, the 7 B frame** -- 2026-09-24 ("shrink ours
      only -> GOSUB 8 -> 7 B", LOOP-RESTART's 09-24 table) and re-confirmed
      2026-10-16 (*"we have to match reference"*; re-asked by mistake, this 🙋 had
      never been struck). ~~🙋 BACK TO JOOST: take the frame
      redesign for 1 B per GOSUB, or state~~
      GOSUB's 8 vs 7 as a divergence (the "never worse" rule then holds for FOR
      and FN only). ➡️ Graphics (PAINT's stack) and file I/O (`MAXFILES`, now
      D-FCBSHAPE) are still unmeasured here. ➡️ PAINT's stack is ALREADY FILED
      and characterised — "PAINT's SPAN STACK IS A FIXED ARRAY" (TIER 3, 🙋
      NEEDS-JOOST: a fixed 120-span cap against the reference's STKTOP-bound
      stack, both directions) — so it is not an open measurement here.
      📏 **GOAL (a), SAME FREE MEMORY — MEASURED 2026-09-25**
      (`scratchpad/fremem_probe.py` → `scratchpad/fremem_run.out`; VG-8020 vs
      zerobas's DISKLESS machine, a fresh boot per state):
      | state | VG-8020 `FRE(0)` | zerobas | gap | Δ from boot (both) |
      |---|---|---|---|---|
      | boot | 28815 | 22785 | −6030 | 0 |
      | `CLEAR 1000` | 28015 | 21985 | −6030 | −800 |
      | `CLEAR 0` | 29015 | 22985 | −6030 | +200 |
      | `DIM A(100)` | 27999 | 21969 | −6030 | −816 |
      | `DIM A%(100)` | 28605 | 22575 | −6030 | −210 |
      | 100-char string | 28809 | 22779 | −6030 | −6 |
      | 4 scalars | 28782 | 22752 | −6030 | −33 |
      | 10-line program | 28545 | 22515 | −6030 | −270 |
      `FRE("")` is IDENTICAL in every state (200 / 1000 / 0 / 100 / 199).
      🟢 **GOAL (c), ECONOMY, HOLDS EXACTLY** — every state costs the same
      bytes on both machines, to the byte (variables, arrays, strings, lines,
      CLEAR). 🔴 **GOAL (a) FAILS BY A CONSTANT 6030 B**: zerobas's free area
      ends near `$D900` (the control pool; then its own `$E000..$F37F`
      workspace), so a program of ~22.8–28.8 KB fits on the VG-8020 and not
      here. 🔮 Predicted "a fixed offset, deltas mostly matching" — HIT, and
      the deltas match EXACTLY.
      ~~🙋 **BACK TO JOOST (the rung's rule: adjustments are his):** close the
      6030 B — which means shrinking zerobas's reserved RAM (the pool, the
      workspace) toward the reference's layout — or accept it as a stated
      divergence?~~
      🏗️ **RULED BY JOOST, 2026-09-25: *"Scout where it goes"*** — account for
      the gap before choosing.
      📏 **SCOUTED 2026-09-25 (`scratchpad/ramlayout_probe.py` →
      `scratchpad/ramlayout_run.out`): the boot layout of all FOUR machines,
      read from their pointers.** The top of each free area is where the
      stack/control pool starts — the reference's `STKTOP`, zerobas's `CTLTOP`
      (the same expression, `strheap_varceil`):
      | machine | top of free | `FRE(0)` | above it, up to `$F380` |
      |---|---|---|---|
      | VG-8020 (diskless) | `$F0A0` | 28793 | 200 strings + 536 file buffers (`MEMSIZ` `$F168`..`HIMEM` `$F380`) = **736 B** |
      | CF-3300 (disk) | `$DB97` | 23408 | 200 strings + 536 file buffers + **5385 B disk work area** (`HIMEM` `$DE77`) = **6121 B** |
      | zerobas, either build | `$D906` | 22763 | 306 channel table + 200 strings + **1280 B `DETOKBUF`** (`$DB00`..`$DFFF`) + **4992 B workspace** (`$E000`..`$F37F`) = **6778 B** |
      🎯 **THE 6030 B IS MOSTLY A DISKLESS STORY.** zerobas's layout is the
      SAME with and without a disk (`TXTMAX` = `$DB00` in both), so against
      the DISK reference the gap is only **645 B** (23408 vs 22763), and
      against the diskless one it is 6030. Each checks to the byte against the
      table (6778 − 736 = 6042, 6778 − 6121 = 657; the 12 B left is the two
      machines' margins).
      📋 **WHERE zerobas's 6778 B GOES, LARGEST FIRST:**
      * **workspace `$E000..$F37F`, 4992 B** — of it `docs/ram-map.md`
        declares **2669 B `basic` + 942 B `disk`**, and ~1735 B lies in gaps
        between declared widths. ⚠️ A gap is a READING, not free space
        (cells addressed by offset have no row) — machine-verify before
        claiming any. The 942 B disk share is dead weight on the DISKLESS
        machine. Biggest `basic` tenants: `TOKBUF` 576, `FLD_DESC` 256,
        `CAL_BUF2` 256, `STRSCR` 256, `TEMPPOOL` 96 (→ 30 by the D-ADDR29
        ruling).
      * **`DETOKBUF`, 1280 B** — the LIST/ASCII-SAVE render buffer, sized for
        the worst case (254 × 5 + 1). It is the ONLY zerobas block between the
        free area and the workspace, so it is the one lever that moves
        `TXTMAX` directly — on BOTH builds. The reference layout shows no such
        buffer (its strings sit directly on `STKTOP`).
      * **channel table 306 B vs the reference's 536 B** — zerobas is 230 B
        AHEAD here.
      🔴 **AND ONE DEFECT THE SCOUT EXPOSED: zerobas's `HIMEM` (`$FC4A`) reads
      `$F380` on both builds, while zerobas itself occupies `$DB00..$F37F`.**
      On the CF-3300 `HIMEM` is `$DE77`, BELOW everything it uses, so a
      program may trust `PEEK(&HFC4A)` as the top of its own RAM (the usual
      way to site machine code). On zerobas the same program BLOADs over the
      interpreter's workspace. Filed as its own item below (D-HIMEMLIE).
      ~~🙋 **BACK TO JOOST (the rung's rule: adjustments are his)** — which
      lever, if any, to pull (each priced, none built; the item's own marker
      stays 🤖 for the D-ADDR29 arc below it):~~
      🏗️ **RULED BY JOOST, 2026-09-25: *"Drop DETOKBUF"*** (lever 1, as
      recommended) — render LIST/ASCII-SAVE a token at a time; +1280 B on both
      builds. **Spec: [`docs/spec-detokbuf-drop.md`](docs/spec-detokbuf-drop.md)**
      — the buffer has FIVE users (LIST, KEY LIST, two PRINT USING tenants, the
      GC's sort array), because a sub-ROM tenant cannot print directly.
      🟢 **S1 SHIPPED (2026-09-25): every renderer writes a 96 B WINDOW
      (`DB_WIN`, the `$E381` the temp pool left) instead of `DETOKBUF`.** The
      sub-side `pchar` discards `DB_SKIP` bytes, stores what fits, and sets
      `DB_MORE` past the window; the resident `detok_emit` re-runs a
      re-runnable renderer (LIST, KEY LIST) with the skip advanced until
      `DB_MORE` stays clear — an ordinary line renders ONCE. PRINT USING's
      tenants are not re-runnable and are asserted to fit one window.
      Page 1 −23 B, sub page 0 −24 B (clean build 2026-09-25). Smoke: 15/15
      `KEY`/`LIST`/`LLIST`/`SAVE`/`USING` rows SUPPORTED
      (`scratchpad/dt_smoke.out`).
      🔴 **AND THE SECOND CUT WAS TOO SLOW — the battery caught it:** re-running
      the whole line per window made `LIST` of a 250 × `?` line take **>8 s of
      emulated time against the VG-8020's <1 s** (`linemax` `list-max` read
      `<none>` — the harness step expired). A render now RESUMES AT A TOKEN:
      detok's main loop is stateless between tokens, so `dt_lp` marks each
      token start (`DT_TOK`) and `pchar` counts its output (`DT_TOKN`); on
      overflow in a LIST render it records the resume point and ABORTS the
      render (SP back to `DB_SP`), and `detok_emit` restarts at that token
      skipping only its drained bytes — linear. `KEY LIST` (~200 B) keeps the
      cheap skip-from-start. Verified byte-identical across window breaks in a
      keyword run, a 200-char string and a 230-char REM (unit harness), and
      `linemax` **60/60**; the 250 × `?` line now lists in 1.5–2.5 s emulated
      (<1 s on the reference) — inside the 10× bar. Page 1 105 B, sub page 0
      311 B free after (clean build 2026-09-25).
      🔴 **THE FIRST CUT RENDERED EVERY LIST LINE BLANK:** the new `db_begin`
      left HL = `DB_WIN`, and `dtk_tenant`'s HL is the TOKEN BODY — the
      helper-borrowed-the-caller's-register class
      [[a-scratch-register-that-was-the-callers-value]]; `test_list` caught it.
      🟢 **S2 SHIPPED (2026-09-26): the collector's sort array lives in the
      VARIABLE free area** — `[ARYEND+2, SP − CTL_STACK_MARGIN)`, idle during a
      collection since D-SPMERGE (the stack descends from the pool frontier
      toward the arrays); base from the LIVE array walk, not the stored
      `CTLLIM`. No room → `gc_slow` as before. The old N ≤ 256 cap was
      `DETOKBUF`'s 512 B, not the sort's (16-bit throughout), so it is gone:
      `scratchpad/gcspeed_probe.py` → `scratchpad/gcspeed_run.out`, a
      collection-heavy loop on both machines — 150 roots zerobas **1.48×** the
      VG-8020's ticks, 300 roots **0.42×** (it used to fall to O(n²) there),
      final strings identical. Sub page 0 292 B free after (clean build
      2026-09-26).
      🟢 **S3 SHIPPED (2026-09-26): `DETOKBUF` IS GONE, `TXTMAX` = `$E000` —
      +1280 B OF BASIC RAM ON BOTH BUILDS, MEASURED.**
      `scratchpad/fremem_probe.py` → `scratchpad/fremem_s3.out`: the gap to
      the VG-8020 is **−4750 in all eight states** (was −6030), and every
      economy delta still matches the reference to the byte. `HIMEM` follows
      through the boot store (now `$E000`).
      🔴 **TWO USERS THE SPEC'S FIVE-USER TABLE MISSED:** `PU_NUM` and `PU_DIG`
      were DERIVED equates (`DETOKBUF + 256`, `+ 512`), not code, so no grep of
      code found them — the ASSEMBLER did. They take declared FREE-RAM runs
      now (`PU_NUM` `$EA60`, `PU_DIG` `$E05A`; both claims shrunk).
      ⚠️ `TXTMAX` = `$E000` made a CONSTANT equal a workspace address, and the
      RAM map read it as a cell; `tools/ram_map.py` learned an explicit
      `NOT-A-CELL` marker on the equ's own line (selftest arms A-NAC, one
      negative), rather than growing the allow-list. The MSX-DOS cells in the
      old range (`$DD0E`, `$DDAE`, `$DF93`) are live only on the DOS-boot path
      (`lay_page0_env`). BASIC and MSX-DOS never RUN together (Joost,
      2026-09-01, D-RECLAIM: *"BASIC and DOS never co-exist"*), so BASIC REUSES
      those same bytes as ordinary program RAM -- by design, not by accident.
      The table below is kept as the priced record:
      | lever | gain | both builds? | what it takes |
      |---|---|---|---|
      | (1) **drop `DETOKBUF`** — render LIST/ASCII-SAVE a token at a time, as the reference's layout implies | **+1280 B** (disk build goes 635 B AHEAD of the CF-3300) | yes | sub-ROM detok rework (sub page 0 434 B / page 1 423 B free); a speed check on LIST |
      | (2) **a NODISK-only layout** — pack the 942 B disk share out of the diskless workspace and raise its `TXTMAX` | up to ~942 B + verified holes | diskless only | the workspace interleaves basic and disk cells; only the LOW end can be ceded (text grows up), so it is a re-layout, not a switch |
      | (3) **shrink `basic` tenants** — `TEMPPOOL` → 30 (ruled), the 256 B buffers, verified holes | tens to hundreds of B | yes | per tenant; each needs its ceiling proved |
      | (4) **accept** the diskless gap as a stated divergence | 0 | — | a doc line |
      🏗️ **RULED BY JOOST, 2026-10-12 — DO NOT RE-ASK:** *"We should not use more
      than the reference?"* -- asked which lever next, he restated the rung's own
      goal (a), ruled 2026-09-24: a program that fits on the reference must fit
      here. **So lever (4) is OUT: the diskless gap is CLOSED, not accepted.** The
      disk build already meets it (+635 B against the CF-3300); the NODISK build
      is −4750 B against the VG-8020 (`fremem_s3.out`, 2026-09-26). Levers (2)
      and (3) are the path, both likely needed. ➡️ **NEXT (TIER 4, ahead of the
      TIER 5 queue):** re-measure the gap on today's build, then lever (2) -- a
      NODISK-only layout that cedes the 942 B disk share -- then (3) per tenant,
      each with its ceiling proved.
      📏 **LEVER (3) MEASURED AGAINST THE REFERENCE, 2026-10-12 (Joost: *"our own
      buffers, test what buffers the reference uses, and see if we can meet the
      same"*).** [`refwork_probe.py`](scratchpad/refwork_probe.py) ->
      [`refwork_probe.out`](scratchpad/refwork_probe.out): a write watchpoint over
      the work area's DATA span ($F39A..$FD99 -- the RAM-resident code below and
      the hooks above are excluded, and only ADDRESSES are recorded), armed
      after boot, each case minus a control. Its first run armed at power-on and
      saw the BIOS clear all 2560 addresses in every case
      ([`refwork_probe_firstrun.out`](scratchpad/refwork_probe_firstrun.out)); it
      now refuses such a control.
      | job | VG-8020 (measured) | zerobas | its size |
      |---|---|---|---|
      | the typed line | **BUF** $F55E (258 B; BUFMIN $F55D for INPUT) | LINEBUF $EB00 | 256 B |
      | the crunched line | **KBUF** $F41F (318 B) | TOKBUF $EC00 | 576 B |
      | the trap table | **TRPTBL** $FC4C (78 B; RUN writes all of it) | ZTRAP $E1D1 | 55 B |
      | DEF FN parameters | **PARM1 / PARM2** (100 B each) | (its own scheme; no workspace buffer -- confirm) | -- |
      | number formatting | FBUFFR | FBUFFR (already shared) | -- |
      **zerobas writes NONE of KBUF / BUF / PARM1 / PARM2 / TRPTBL in any case**
      -- the reference's own buffers sit unused while zerobas pays for copies.
      Meeting the same: ~887 B of workspace (LINEBUF + TOKBUF are contiguous,
      $EB00..$EE3F, 832 B; ZTRAP 55), each then at the reference's ADDRESS too
      (goal b). Costs: (i) TOKBUF is 576, not 318, ON PURPOSE -- it absorbs one
      unbounded inner copy pass (tk_str_loop / tk_rem_rest / tk_data_rest) and
      adjudicates once at tk_end; KBUF's 318 means bounding those loops, in the
      tokenise tenant (sub page 0, 6 B on 2026-10-12 -- may have to move to sub2);
      (ii) LINEBUF is PAGE-ALIGNED on purpose (the single-low-byte idiom in
      read_line, ascii_read_lines and console INPUT); BUF crosses a page;
      (iii) a hole mid-workspace raises nothing: TXTMAX ($E000) climbs only when
      what sits below the hole moves up into it.
      ➡️ Next: confirm DEF FN's footprint; price (i)-(iii); then the moves, one
      buffer per commit, each with `fremem_probe.py` and ram-map-check.
      📏 **TRPTBL'S LAYOUT, MEASURED 2026-10-12** ([`trptbl_probe.py`](scratchpad/trptbl_probe.py)
      -> [`trptbl_probe.out`](scratchpad/trptbl_probe.out), VG-8020, the 78
      data bytes PEEKed): 3-byte entries **KEY 1-10, STOP, SPRITE, STRIG 0-4,
      INTERVAL** ($FC7F), 24 B reserved, all zeroed by RUN; byte 0 = `01` ON /
      `02` STOP / `00` OFF (OFF KEEPS the pointer); bytes 1-2 = the handler
      LINE's address (its link field). After `INTERVAL STOP` and a wait the
      entry still reads `02`: no latch bit is visible in it. 🔮 Order, shape and
      pointer HIT; the latch bit (predicted bit 2) MISS.
      🔴 **SO ZTRAP -> TRPTBL IS NOT THE CHEAP FIRST MOVE I took it for.**
      ZTRAP's ORDER IS ITS PRIORITY: `ct_find` (basic/traps.asm) fires the
      first pending entry scanning up, and the order is measured (INTERVAL,
      STOP, SPRITE, STRIG 0-4, KEY 10..1 -- keytrap.asm `key_entry_index`). The
      reference's table order is not its priority, so its layout means a
      custom priority walk in `ct_find`; ZTRAP's state byte also carries
      PENDING (bit 7) and the edge SHADOW (bit 6), which TRPTBL does not show.
      And its 54 B raise FRE(0) only after the workspace is packed (iii).
      ➡️ The move that pays is LINEBUF + TOKBUF (832 B, contiguous at $EB00)
      into BUF + KBUF, then the packing; price those first.
      📏 **THE GAP, RE-MEASURED 2026-10-12** ([`fremem_1012.out`](scratchpad/fremem_1012.out),
      NODISK vs the VG-8020): **−4978 B in all eight states** (28815 vs 23837
      at boot); every economy delta still matches to the byte. 🔮 Predicted
      the 09-26 figure, −4750: **MISS by 228 B -- zerobas's fixed RAM GREW
      since 09-26.** Not yet attributed. A suspect, unconfirmed: channel #0's
      267 B block (D-FCBSHAPE, 2026-10-10), ruled to be built because the
      reference has one too -- in which case the reference's FRE already pays
      for it and it should not widen the gap. ➡️ Attribute it first (`git log`
      of TXTMAX / the pool / HIMEM-side claims since 09-26, `ramlayout_probe.py`).
      ✅ **ATTRIBUTED THE SAME DAY** ([`ramlayout_1012.out`](scratchpad/ramlayout_1012.out)
      against 09-26's [`ramlayout_run.out`](scratchpad/ramlayout_run.out)): NODISK
      CTLTOP $D906 -> $DD22, FRE(0) 22763 -> 23815 (+1052, where DETOKBUF's drop
      gave +1280). The 228 B are the CHANNEL BLOCKS: on 09-26 zerobas's table
      was 306 B, 230 B SMALLER than the reference's 536; D-FCBSHAPE (09-30 /
      10-10) made them the reference's size. The reference pays the same, so it
      is an advantage given back, not a new cost. 🔮 My suspect (FCB0) was the
      right family, the wrong reading of it.
      🎯 **WHAT IS LEFT IS ALL THE WORKSPACE.** Above the free area the VG-8020
      keeps 736 B (200 strings + 536 channels) and zerobas 734 B -- the same
      structure. The difference is HIMEM: **$F380 there, $E000 here -- the 4992 B
      of zerobas's private workspace ($E000..$F37F)**, less 14 B of margins =
      the −4978. So closing the gap FULLY (goal a, ruled) means emptying that
      workspace: its tenants into the reference's own buffers where the job is
      the same (LINEBUF / TOKBUF -> BUF / KBUF, measured), into cells the
      reference leaves unused, into the sub ROMs' reach where a tenant can own
      it, or not at all (the 942 B disk share, on NODISK). Each B moved raises
      TXTMAX / HIMEM 1:1 only once the space below it is packed.
      💰 **TOKBUF -> KBUF PRICED, 2026-10-12, and the price was a bug: D-TOKOVF.**
      Pricing it found the crunch UNBOUNDED (tk_end its only test; a 253-
      character `0#` line wrote ~253 B past TOKBUF) -- fixed first, with the
      bound at tk_loop's head. With it the crunch writes at most 571 B (a body
      of 314 + one step + the terminator), and the reference's own buffers are
      CONTIGUOUS: KBUF $F41F (318) + BUFMIN $F55D (1) + BUF $F55E (258) = 577 B.
      So TOKBUF at KBUF needs NO second bound: past 318 the overshoot runs into
      BUF only, and only behind the source cursor once LINEBUF is BUF too
      (write minus read stays below 319: 317 at most at an inner loop's entry,
      and the 9 B main-loop step needs ~69 characters read to reach it).
      ➡️ **ORDER, one commit each, FRE measured each time:** (1) LINEBUF -> BUF
      (the `ld h,high LINEBUF` idiom in input.asm goes: BUF crosses $F600; the
      low-byte terminator compares survive: a 255-byte span has distinct low
      bytes -- but `ascii_read_lines`'s cap is `jr nc`, an ORDER test, and must
      become `jr z`);
      (2) TOKBUF -> KBUF -- $EB00..$EE3F (832 B) is then a hole; (3) shift the
      LOWEST 832 B of cells ($E000..$E33F) up into it as one block, TXTMAX ->
      $E340: the first FRE gain, +832. A tool rewrites each `equ` in the block by
      the same delta and `tools/ram_map.py` must show exactly that set moved.
      ✅ **(1) DONE 2026-10-12 (D-RAMBUF): LINEBUF = BUF $F55E.** files.asm's cap
      test `jr nc` -> `jr z`; console INPUT's cursor a 16-bit pointer
      (INP_CURSOR, 2 B of NUMBUF); main low region 47 -> 49 B (clean build).
      🔴 One DERIVED constant moved with it and the build's own assert caught it:
      DEF FN's parameter area ran "up to LINEBUF" (FN_AREA), so it would have
      grown into the freed page -- pinned to FN_PAREA_CEIL = $EB00, FN_MAXP stays
      9. Suites: input / linemax / inputdn / inputary / screditor / diskascii /
      cas-ascii all green. Knives ([`rambuf_knife.out`](scratchpad/rambuf_knife.out)):
      K-R1 (the cap back to `jr nc`) -> exactly diskascii + cas-ascii RED; K-R2
      (a cursor that never advances) -> exactly input RED; restored green. 🔮 Both
      HIT. No FRE change, by design: $EB00..$EBFF is a hole mid-workspace.
      ⚠️ For (2): corrupt-ovf's witness ($EF00) leaves the overrun's path once
      TOKBUF is KBUF -- re-site it (an unbounded overrun from KBUF would reach
      TXTTAB at $F676: LIST of a stored line is the witness).
      ✅ **(2) DONE 2026-10-12 (D-RAMKBUF): TOKBUF = KBUF $F41F.** No second bound
      (the proof above); two asserts beside TOKBUF pin its premises (LINEBUF is
      TOKBUF + 319; one pass ends inside BUF). Every main-loop step is <= 9 B --
      checked, not assumed: `bl_num` emits ONE reference per call and returns to
      tk_loop. $EB00..$EE3F is now one 832 B hole. corrupt-ovf re-sited to
      TXTTAB's high byte and the first line number (`128 10` on both).
      🔴 **TWO INSTRUMENT FINDINGS ON THE WAY:** (a) the re-sited row's first
      anchor was 55 characters, its echo wrapped, BOTH sides read `<none>` -- and
      SCORED PASS, knife included: the `corrupt` reader turned a missing span
      into the STRING "<none>", which agrees with itself. It is None now (refused
      by compare()); the whole linemax gate is still 62/62
      ([`ramkbuf_linemax.out`](scratchpad/ramkbuf_linemax.out)). (b) With a real
      readout the knife K-T1 (bound cut) STILL read green
      ([`ramkbuf_knife.out`](scratchpad/ramkbuf_knife.out)): in this layout the
      unbounded crunch overruns into BUF -- its own source -- AHEAD of the read
      cursor, and the `0#` literals' $00 bytes end the line early, so nothing
      past BUF is touched. The bound's absence is invisible on the machine for
      this input; its witness moved to the HOST: tests/test_tokenise.py crunches
      into TOKBUF from a source elsewhere over a sentinel and reads the reach --
      321 live, 831 with the bound cut ([`ramkbuf_hostknife.out`](scratchpad/ramkbuf_hostknife.out)).
      🔮 Predicted the rows `32769 10` (MISS: the wrapped anchor), the knife red
      (MISS twice), the host reach ~829 cut (HIT, 831).
      ✅ **(3) DONE 2026-10-13 (D-RAMSHIFT): THE FIRST FRE GAIN, +618 B ON BOTH
      BUILDS.** Not 832: STRSCR ($E26D, 256 B) straddles $E340, and the first
      cut at $E26D was REFUSED by the tool because STRSCR = RVDESC + 3 and
      RVDESC = FRETOP + 2 chain out of the block -- RVDESC is now pinned at
      its own address ($E26A; every FRETOP access is a 16-bit load/store by
      name, no adjacency assumed). Block $E000..$E269 -> $EB00..$ED69 (+$0B00,
      a whole number of pages: every low byte kept); TXTMAX $E000 -> $E26A.
      [`tools/ws_shift.py`](tools/ws_shift.py) rewrote 195 literal equates and
      VERIFIED from the resolved maps of both components (no .sym) that 229
      names moved exactly as claimed and nothing else did, the 70 disk mirrors
      through their basic originals ([`ramshift_apply.out`](scratchpad/ramshift_apply.out)).
      📏 [`fremem_shift.out`](scratchpad/fremem_shift.out): diskless **-4360 in
      all eight states** (was -4978), every economy delta still equal;
      [`ramshift_disk.out`](scratchpad/ramshift_disk.out): the disk build 23705
      against the CF-3300's 23430 -- **275 AHEAD** (was 343 short). 🔮 Both
      predicted exactly: HIT, HIT.
      ⚠️ $E000 IS PROGRAM RAM NOW: kwram / kwtime / castail / probe_signal POKE
      window marks there, which used to be dead workspace. On zerobas it is now
      the string space under the channel blocks (strings are allocated down
      from $E051); harmless while a measured program holds under ~80 B of
      strings -- the battery is the check. Golf (D-BASICROM) still cannot run:
      its USR data at $E05E..$E273 is now the channel blocks and RVDESC.
      ➡️ NEXT: the remaining hole ($ED6A..$EE3F, 214 B) cannot take STRSCR
      (256 B). Candidates, by size: the disk share on NODISK (942 B), STRSCR
      itself into a reference buffer, the FAT/CAL buffers on NODISK (1024 B).
      🔴 **ITS FIRST FULL BATTERY READ 200/202 -- HAND COPIES THE CHECKERS DO NOT
      SEE** (the battery log is not kept; the two reds were): `ramfree` (the `; FREE-RAM $A..$B` claims in sysvars.inc COMMENTS
      still named the old spans -- the shift tool rewrites `equ`s, not claims --
      and `CTLTOP_ADDR = 0xE052`, a copy under ANOTHER name) and `txtceil`
      (`TXTTAB, PRGEND, HIMEM, POOL = ..., 0xE026, ..., 0xE232`, a TUPLE
      assignment). wall-literal-check matches `NAME = value` with the cell's own
      name only, so all three passed it. ✅ The four claims shifted (each keeps
      its old span in a note); ramfree / txtceil / prgend_init read the moving
      cells from build/basic-reloc.sym. Green after:
      [`ramshift_ramfree.out`](scratchpad/ramshift_ramfree.out),
      [`ramshift_txtceil.out`](scratchpad/ramshift_txtceil.out).
      ➡️ FOR THE NEXT SHIFTS: ws_shift.py should rewrite the FREE-RAM claims
      too, and the checker's blind forms (tuples, renamed copies) want a sweep
      -- grep the probes for the shifted range's literals before the battery.
      (prgend_init is not wired into any gate; it passes when run by hand.)
      📐 **LEVER (2) PRICED, 2026-10-13 -- THE NEXT ~1.6 KB, DISKLESS ONLY.**
      Census of the remaining workspace ($E26A..$F37F, docs/ram-map.md): on the
      diskless build these are NEVER used -- the FAT data + metadata sector
      buffers (1024 B, $E5C0..$E9BF; but CAL_BUF / CAL_BUF2, the cassette
      ASCII-load buffers, 512 B, live INSIDE them), FLD_TAB + FLD_DESC (352 B;
      FIELD is refused without a disk since D-FLDGATE, basic_probe_nodisk
      `h.field`), and 91 disk-only cells (246 B declared). The main ROM is ONE
      binary for both builds, so they can only be ceded with a RUNTIME
      ceiling. Plan, one commit each:
      (a) TXTMAX -> a RAM cell set at boot from disk presence (TXTMAX_DISK /
          _NODISK, equal at first: no behaviour change, the gates prove the
          plumbing). ~6 main sites load it as a constant (str-engine, interp
          boot, cload x2, lineedit, strheap); ~+1 B each. The disk ROM's own
          uses keep the DISK constant -- it exists only on that build.
      (b) re-layout: the disk-only tenants packed at the workspace FLOOR, basic
          ones above; TXTMAX_NODISK = the basic block's bottom. Needs a packing
          tool (ws_shift moves one block; this reorders many) and every cell's
          width TRUSTED first (42 are pinned width-less in
          tools/ram-width-allow.txt). The packing also closes the unattributed
          runs (~600 B: $E41E 212, $F195 107, ...) for BOTH builds.
      (c) the cassette buffers: on the VG-8020 a tape ASCII load goes through
          channel 0's 267 B block -- measure whether CAL_BUF can be FCB 0's
          buffer, so the 512 B need not stay in the diskless workspace.
      After lever (2), the gap is ~2.7 KB of basic tenants proper -- STRSCR
      (256), DB_WIN (96), FN_PAREA (99, the reference has PARM1 for that
      job), FOR/GFX/PU scratch, the math cells: lever (3), per tenant.
      ✅ **(a) DONE 2026-10-13 (D-RAMCEIL): TXTCEIL ($ED6A, 2 B) is the ceiling
      boot chose.** interp.asm's HIMEM store now also stores TXTCEIL: TXTMAX
      (the disk build's) when a disk ROM lowered HIMEM, TXTMAX_NODISK otherwise
      -- equal for now. str-engine / strheap / cload load TXTCEIL; the disk ROM
      keeps the constant. 🔴 A BOOT-ORDER TRAP, caught by reading, not by a run:
      clear_vars -> heap_reset runs ~150 lines BEFORE the store, so it would
      have read power-on RAM (openMSX zero-fills: a heap ceiling of 0, and a
      suite that could pass for the wrong reason). TXTCEIL is seeded with TXTMAX
      before clear_vars, which is byte-for-byte what that reset always computed.
      Walls: page 1 111 -> 90 B, low 49 -> 48, sub page 0 71 -> 70 (clean build).
      Unchanged on all four machines, as predicted
      ([`ramceil_fremem.out`](scratchpad/ramceil_fremem.out),
      [`ramceil_disk.out`](scratchpad/ramceil_disk.out)). ⚠️ NO KNIFE YET: with
      the two ceilings equal, the boot DECISION cannot be witnessed -- step (b)
      owes the knife (cut the branch: the diskless FRE must fall back).
      ⚠️ For (b): a SHIFT boot leaves a disk ROM RECORDED (DISKSLOT_OK) but
      uninstalled, and HIMEM unlowered -> the diskless ceiling. Before the two
      differ, check that no disk verb can reach the disk-only buffers then.
      ✅ CHECKED 2026-10-13 (read, basic/islands.asm): the SHIFT path leaves
      DISKSLOT_OK = 0 (`inc` of the $FF the disk ROM leaves), and every disk
      verb gates through `diskslot_test` (program.asm, ~25 sites) -- "disk
      active" is ONE fact, and the HIMEM test boot uses agrees with it (the
      disk ROM lowers HIMEM exactly when it installs). (b) should ASSERT the
      two agree, or test DISKSLOT_OK directly.
      📏 **(b) MEASURED FIRST, 2026-10-13: WHAT DOES THE DISKLESS BUILD WRITE?**
      [`nodiskuse_probe.py`](scratchpad/nodiskuse_probe.py) -- a write watch over
      $E26A..$F37F on NODISK, armed after boot, 20 cases (line entry, INPUT,
      DEF FN, traps, USING, strings, arrays, FOR/GOSUB, ON ERROR, math, SCREEN 2
      graphics, PLAY, RENUM/DELETE, KEY, CLEAR/MAXFILES ...). 🔮 Predicted
      ~1.4 KB never written: MISS, 3528 B
      ([`nodiskuse_firstrun.out`](scratchpad/nodiskuse_firstrun.out)) -- "never
      written by these cases" is a LOWER BOUND ON USE, not free space: a
      buffer's tail stays unwritten unless a case fills it (STRSCR 13 of 256),
      and boot-only cells (the trampoline copy, the slot scan) are written
      before the watch arms and only read after. Its use is COUNTER-EVIDENCE
      ([`nodiskuse_probe.out`](scratchpad/nodiskuse_probe.out)): 6 statically
      disk-only cells the diskless build DID write. Four are cross-ROM overlays
      (a disk cell parked in a basic cell's bytes -- WA_SEG = FN_PAREA, the BDOS
      pair at $E542, RES_STUBS_END in the stack's reach): they move WITH their
      basic owner. 🔴 **The fifth is the finding: FLD_TAB, 16 of 96 B --
      `fld_init` (basic/field.asm) clears every slot's first byte on NEW / RUN,
      ungated, and `fld_clear_chan` on CLOSE.** On the diskless build the bytes
      just under the new ceiling are where the CHANNEL BLOCKS and the STRING
      SPACE live, so once a disk-only cell sits there, ANY ungated main-ROM
      write to it corrupts a running program. So (b) needs, BEFORE the move:
      (b1) a census of main-ROM writers to disk-only cells -- this probe saw
      only fld_init, but it cannot see the boot or anything no case drives --
      each gated on DISKSLOT_OK (diskslot_test, +4 B a site); (b2) the boot
      order checked (a write after init_filechan builds the channel blocks is
      as bad); (b3) a permanent stress row: strings and channel blocks pushed
      up to the diskless ceiling, against the VG-8020; then (b4) the move.
      📏 **(b1) THE WRITER CENSUS, 2026-10-13** ([`dowrite_probe.py`](scratchpad/dowrite_probe.py)
      -> [`dowrite_probe.out`](scratchpad/dowrite_probe.out)): the disk-only
      set (1085 B) watched on NODISK from POWER-ON, with the writer's PC, over
      the same 20 cases. Main / sub code: ONLY `fldi_lp` (fld_init) -- 🔮
      predicted fld_init + fld_clear_chan (CLOSE: no case closes a channel) +
      a boot initialiser or two: HIT on fld_init, the rest not seen. C-BIOS: a
      power-on page probe ($E700/$E900/$EF00), its MSX-DOS standard cells
      ($F33B..: fixed addresses near the TOP, never moved) and stack traffic at
      $F2B8. `vsf_wb_copy` writing $EAA2 was MY set's error (FN_PAREA has no
      declared width, so its bytes read as disk-only). The static complement
      (every main / sub reference to the FAT / FIELD buffers) is FAT, FORMAT,
      random-file and FIELD code behind the disk verbs' gate -- and one
      finding that is a READ: `strvar.asm` calls `fld_lookup` on EVERY string
      access and walks FLD_TAB (as does sub/arrays.asm). On the diskless build
      that table is always EMPTY, which is what keeps the answer "not FIELDed";
      in program RAM it would read a program's data. **So FLD_TAB (96 B) stays
      with the basic tenants; FLD_DESC (256 B), reached only through a FIELDed
      match, is truly disk-only.**
      ✅ **(b4), FIRST MOVE, 2026-10-13 (D-RAMFLD): +256 B DISKLESS.** STRSCR
      (with the disk ROM's five FDC cells overlaid in it) and FLD_DESC swap
      places; RVDESC goes to $ED6C; TXTMAX_NODISK = $E36A, TXTMAX (disk) stays
      $E26A. tools/ws_shift.py generalised to several moves at once (swaps),
      non-page deltas refused for page-idiom names, `--disk-only`, and a NO
      NEW OVERLAP invariant. 🔴 **ITS FIRST OVERLAP CHECK WAS BLIND:** the
      negative control (STRSCR moved onto FLD_DESC alone) VERIFIED -- ram_map
      drops the widths of cells that overlap (disputed / overrun), so two cells
      moved onto each other vanished from the check as they collided. Widths now
      come from the BEFORE map, applied at the after addresses; the control
      refuses with six NEW OVERLAPs ([`ramfld_apply.out`](scratchpad/ramfld_apply.out)
      is the real run: 9 names). And a boot-order sequel: clear_vars'
      heap_reset ran against the seed (the disk ceiling), leaving the heap's
      top 256 B below the diskless ceiling -- boot now re-runs heap_reset once
      the ceiling is chosen (the disk build had the mild form all along).
      📏 [`ramfld_fremem.out`](scratchpad/ramfld_fremem.out): diskless **-4104
      in all eight states** (was -4360), deltas equal;
      [`ramfld_disk.out`](scratchpad/ramfld_disk.out): disk build unchanged,
      23705. 🔮 Both exact: HIT.
      🔒 **New gate `make ceiling-acceptance`** ([`basic_probe_ceiling.py`](probes/basic/basic_probe_ceiling.py)):
      the boot's choice read back (TXTCEIL / HIMEM against the sym) -- the
      knife D-RAMCEIL owed: K-C1 (the diskless branch cut) -> exactly the
      nodisk row red, restored green ([`ramfld_knife.out`](scratchpad/ramfld_knife.out)).
      Its first two runs read INSTRUMENT FAULT on every row
      ([`ramfld_knife_firstrun.out`](scratchpad/ramfld_knife_firstrun.out)):
      the readout line wrapped -- at 41 characters, then at 37: the boot width
      is 37 (D-BOOTWIDTH), not 40.
      ⚠️ (b3) NOT ADDED, and why: FLD_DESC's new bytes are, on the diskless
      build, CHANNEL 0's block (it exists at every MAXFILES). A stress program
      can only drive ordinary channel use, which never reaches FIELD code -- a
      row that would agree for the wrong reason. The hazard is closed by the
      census and the read above (FLD_DESC is reached only through a FIELDed
      match, and FLD_TAB is empty without a disk).
      ➡️ NEXT in (b): the FAT buffers need the cassette pair out of them first
      (step c); the remaining disk-only cells are small and mostly overlays.
      📏 **THE WORKSPACE'S UNATTRIBUTED RUNS, CHECKED ON BOTH BUILDS, 2026-10-13**
      ([`holecheck_probe.py`](scratchpad/holecheck_probe.py) ->
      [`holecheck_probe.out`](scratchpad/holecheck_probe.out)): 14 runs of >= 16 B
      that neither map covers (747 B, the disk interrupt stack and $F200..$F37F
      excluded), watched from power-on with the writer's PC over the 20 cases.
      446 B never written, identical on both builds. 🔮 "most never written"
      HIT; "the disk build writes one more" MISS. 🔴 **THREE ARE LIVE TENANTS
      THE MAP DOES NOT KNOW**, written by our own code through offsets:
      $ECD4..$ED06 (trap_init / eos_store / eostr_idx / ss_write / rp_exec --
      the trap block is wider than its declarations), $E400..$E411 (sub
      gsxs_lp, graphics scratch past a cell's declared width), $F03D..$F049
      (sub tksd_dsat / trm_pad_lp, a digit / pad buffer beside TKDIG, which
      declares 1 B). ➡️ (1) give those three their real widths (the map
      becomes truthful); (2) the 446 B stay CANDIDATES -- dynamic absence is a
      lower bound -- so each needs a static offset check against its
      neighbours before any packing.
      ✅ **THE MAP CORRECTED, SAME DAY.** The three were WIDTHS the map had
      wrong, not unknown tenants: ZTRAP's comment still named its pre-D-RAMSHIFT
      span ($E1D1..$E207), and a range that does not start at its cell is
      ignored, so ZTRAP read 3 B -- SILENTLY (FOR_CUR's stale range had broken
      loudly; this one degraded to a smaller TRUSTED width). GFX_PSTK, the PAINT
      span stack, is 360 B ($E3F2..$E559), a union with DRAW's 256 B frame
      text and the sprite x-save -- its width was "disputed", so TWO of the
      "never written" holes ($E41E 130 B, $E4C2 48 B) were the deep end of
      the PAINT stack, which no case filled. TKDIG declared (1 B) for a 24 B
      array. All three now state their ranges; the GFX pin left
      tools/ram-width-allow.txt (the ratchet's good direction). A sweep for
      comment ranges stale by a shift delta found only ZTRAP (the rest are
      historical notes). ⚠️ tools/ws_shift.py rewrites equates, not comment
      ranges: the next shift must update them too (FOR_CUR and ZTRAP).
      📏 Re-run against the corrected map ([`holecheck_probe.out`](scratchpad/holecheck_probe.out);
      the first: [`holecheck_firstrun.out`](scratchpad/holecheck_firstrun.out)):
      9 candidates, 477 B, written by NOTHING of ours on either build (only
      C-BIOS's power-on page probe at $EE00). 🔮 Predicted ~477 B and only
      that writer: HIT.
      🏗️ **RULED BY JOOST, 2026-10-13 -- DO NOT RE-ASK:** *"so for every ram
      buffer or memory location we invented ourselves, we need to verify how
      reference does it and if we should not be using an existing "official"
      ram location instead"*. D-REHOME (2026-08, docs/sysvar-rehoming-decisions.md)
      did this for ten same-NAME cells; this extends it to EVERY private cell,
      with RAM as the reason (its REJECTs -- VALTYP, SAVTXT, SAVSTK, FRETOP --
      were judged on observability alone and get re-judged). Plan: (1) group
      every private cell by JOB; (2) per group, a write watch on the
      reference's published work area during that job (refwork_probe.py's
      method, addresses only); (3) per cell: (a) same job, an official cell
      exists -> move there, same address; (b) no reference equivalent ->
      keep, the reason in its own comment; (c) a zerobas mechanism (the
      sub-ROM bridge) -> keep, minimise; (4) one table, one TODO item per (a)
      group.
      📏 **(1) DONE, 2026-10-13** ([`officialram_inventory.py`](scratchpad/officialram_inventory.py)
      -> [`officialram_inventory.out`](scratchpad/officialram_inventory.out)):
      3283 B of declared cells in $E26A..$F37F -- files / channels / disk
      1857, cassette 542, graphics 472, string engine 300, sub-ROM bridge /
      boot 209, PRINT USING 154, traps 70, math 64, control pool 54,
      tokeniser / editor 49, DEF FN 18, arrays 13, PLAY 2, unclassified 72
      (grouped by name prefix: ROUGH -- step (2) corrects it by measurement).
      Already visible, private cells with an official cell for the SAME job:
      LPTPOS (official LPTPOS, $F415), TRACEFLAG (TRCFLG), MAXF (MAXFIL),
      DATAPTR (DATPTR), PRDEV (PRTFLG? -- check), ARGA / ARGB (DAC / ARG: a
      different number FORMAT, so priced, not assumed). Small in bytes; each
      also makes a PEEK of the official cell answer as on the reference.
      ✅ **(2), FIRST GROUP, 2026-10-13 (D-OFFICIAL): TRCFLG AND MAXFIL.**
      [`officialcell_probe.py`](scratchpad/officialcell_probe.py) ->
      [`officialcell_before.out`](scratchpad/officialcell_before.out): the
      VG-8020 keeps TRON in TRCFLG $F7C4 (175 under TRON in every context
      measured -- direct, program, TRON twice -- 0 under TROFF), MAXFILES in
      MAXFIL $F85F (1 at boot, 3 after MAXFILES=3), the READ position in
      DATPTR $F6C8 ($8000 at boot, $802B after one READ); zerobas read 0 in
      every row. 🔮 Predicted exactly that: HIT. TRACEFLAG and MAXF now ARE
      those cells (equates; TRON stores 175 -- same size as `ld a,1`; the
      trace test only asks nonzero), both rows SAME after
      ([`officialcell_probe.out`](scratchpad/officialcell_probe.out)). The
      CF-3300's own disk ROM READS MAXFIL during LOAD / SAVE
      (disk/docs/spec-diskcode-eviction.md) -- the official cell is where a
      disk ROM looks. 🔒 New gate `make officialcell-acceptance`
      ([`basic_probe_officialcell.py`](probes/basic/basic_probe_officialcell.py)):
      the four rows gated, DATPTR reported; knives K-O1 (TRACEFLAG back) ->
      exactly trcflg red, K-O2 (MAXF back) -> exactly maxfil + maxfil-ctl
      red, restored green ([`official_knife.out`](scratchpad/official_knife.out)).
      ➡️ NEXT: DATPTR -- zerobas's DATAPTR + DATASTATE (0 = unpositioned)
      against the reference's single pointer ($8000 = TXTTAB-1 when
      unpositioned): measure where the reference's pointer points after a
      READ, a RESTORE n and an exhausted DATA list first. Then LPTPOS /
      PRTFLG (LPRINT needs a printer plugged in the probe).
      📏 DATPTR MEASURED, 2026-10-13 ([`datptr_probe.py`](scratchpad/datptr_probe.py)
      -> [`datptr_probe.out`](scratchpad/datptr_probe.out)): ONE pointer on the
      VG-8020, no state byte -- TXTTAB-1 when unpositioned (RUN, RESTORE), the
      `,` after an item with more to come, the line's 0 after its last item,
      `RESTORE n` -> the byte before line n (the $0D convention), and after
      `Out of DATA` BACK TO THE RESTORE POINT. zerobas: four private cells
      (DATASTATE / DATAPTR / DATALINE / RESTORE_LINE, 7 B) -- converting is
      a rework of the READ tenant (sub page 0): its own item, priced first.
      🔴 **AND THE MEASUREMENT FOUND A BEHAVIOUR DIVERGENCE -- D-DATARESET,
      TIER 3, FIXED THE SAME DAY:** the rewind is observable. After `Out of
      DATA` + RESUME NEXT the VG-8020's next READ starts over (C = 5, the
      handler runs ONCE; after RESTORE 60 it rereads line 60's 7); zerobas
      stayed exhausted (C = 0, the handler ran twice)
      ([`datareset_probe.py`](scratchpad/datareset_probe.py), before values in
      its docstring; after: [`datareset_probe.out`](scratchpad/datareset_probe.out)).
      ✅ readdata-body.inc rov_none sets DATASTATE 0 ("unpositioned, from
      RESTORE_LINE") as it reports out-of-data -- the error is still raised
      on that READ; +3 B sub page 0 (70 -> 67). 🔒 Three rows in
      `make readerl-acceptance` (oodrewind / oodcount / oodrestore), 10/10;
      knife K-D1 (the store cut) -> exactly those three red, restored green
      ([`datareset_knife.out`](scratchpad/datareset_knife.out)). 🔮 HIT.
      🏗️ **ORDER CONFIRMED BY JOOST, 2026-10-13:** asked *"we should probably fix
      the bigest own invented ram regions first?"*, he confirmed the proposed
      order: *"go ahead with that order"*. BIGGEST FIRST, each step MEASURED
      on the reference before anything moves:
      (1) the FAT sector buffers (1024 B) TOGETHER with the cassette pair
          inside them (CAL_BUF / CAL_BUF2, 512 B) -- first: which buffer the
          VG-8020 uses for SAVE / LOAD "CAS:" and OPEN "CAS:" (the channel's
          own? then the cassette pair moves there and the FAT buffers become
          wholly disk-only, for the diskless floor);
      (2) the PAINT span stack GFX_PSTK (360 B, both builds) -- where the
          reference's PAINT keeps its spans;
      (3) STRSCR (256 B, both builds) -- the reference's string temporaries;
      (4) FLD_DESC (256 B), then PRINT USING's scratch -> FBUFFR.
      The small official-cell moves (DATPTR, LPTPOS / PRTFLG, the D-REHOME
      re-judgements) come after: they buy correctness more than bytes.
      📏 **(1) MEASURED, 2026-10-13.** [`casbuf_probe.py`](scratchpad/casbuf_probe.py)
      -> [`casbuf_probe.out`](scratchpad/casbuf_probe.out): the VG-8020 does
      ALL cassette I/O through the CHANNEL's own 256 B buffer (block + 9):
      SAVE / LOAD "CAS:" through #0's ($F177..$F276, VARPTR(#0) $F16E),
      OPEN ... AS #1 for output or input through #1's ($F280..$F37F) --
      no other buffer of size. zerobas wrote CAL_BUF ($E600..$E6FF) in every
      case, its own channel blocks ($E090 / $E199, the same 265 B shape)
      untouched. 🔮 HIT.
      [`casmotor_probe.py`](scratchpad/casmotor_probe.py) ->
      [`casmotor_probe.out`](scratchpad/casmotor_probe.out): an 8-block
      ASCII LOAD with the motor line (PPI port C bit 4) sampled -- the
      VG-8020 stops the motor between blocks (~0.1 s gaps), and so does
      zerobas (~0.2-0.3 s; D-CAS4BLK). 🔮 "zerobas keeps it running": MISS.
      So the read-ahead second buffer is REDUNDANT -- D-CAS4BLK's own note
      says the motor stop was the fix and the double buffer "only moved
      that one block later". ➡️ **(1) DESIGN:** cassette I/O through the
      channel's own buffer, ONE buffer, as on the reference (#0 for SAVE /
      LOAD, the opened channel for OPEN); CAL_BUF / CAL_BUF2 / CAS_WBUF
      retired; then the FAT sector buffers are wholly disk-only and move
      to the diskless floor (~1 KB). Cost: the page-aligned idioms
      (`ld h,CAL_CURHI`, `ld h,CAS_WBUF >> 8`) become 16-bit base + index,
      in the casmatch / casget tenant (sub page 1) and the SAVE / PRINT#
      path (main). Tape-timing code: the cassette suites are the gate.
      ✅ **(1a) DONE 2026-10-13 (D-CASFCB): tape I/O through the channel's own
      buffer.** CAS_BUFP ($ED6F) = channel block + FCH_HDRSZ, set by
      cas_bufp_set (basic/cload.asm): #0 in cas_open_match's stub (the search
      SKIPS files through it), SAVE "CAS:" and BLOAD's stub; #n in OPEN "CAS:"
      AS #n. One buffer, refilled when it drains (cal_serve); the EOF peek's
      LF-at-block-end case consumes the LF and reads the next block. CAL_BUF /
      CAL_BUF2 / CAS_WBUF / CAL_CURHI / CAL_XORHI retired. Walls: main page 1
      87 -> 44 B, sub page 1 61 -> 95 B (clean build). 🔴 The first cassette
      run read 13/14: casbin bty / bbare (PEEK 0) -- BLOAD's tenant calls the
      SUB-side cas_open_match, never main's stub, so its skip read through an
      unset pointer; BLOAD's resident stub sets it now (+4 B). All 14 green
      after. Knives ([`casfcb_knife.out`](scratchpad/casfcb_knife.out)): K-F1
      (BLOAD's set) -> exactly casbin bty + bbare red; K-F2 (the search stub's
      set) -> casbin lbin + cas-ascii red; restored green. 🔮 Both HIT.
      tools/ram_map.py's selftest arms A13 / A14 used the cassette buffers as
      their overlay examples; retargeted to main's FWBUF hosting the disk
      ROM's WRBLK cells (61/61). ➡️ (1b): the FAT sector buffers are now
      wholly disk-only -> the diskless floor (~1 KB).
      ✅ **(1b) DONE 2026-10-13 (D-FATFLOOR): the two 512 B FAT sector buffers
      moved to the diskless floor.** A rotation of $E36A..$E9BF by
      tools/ws_shift.py: FSECTOR_BUF / FWBUF (and disk.rom's SECTOR_BUF / WBUF,
      the same bytes) to $E36A / $E56A, everything that sat above them +$400;
      TXTMAX_NODISK $E36A -> $E76A, TXTMAX unchanged. 158 names moved, each
      verified ([`fatfloor_wsshift_apply.out`](scratchpad/fatfloor_wsshift_apply.out)).
      📏 [`fatfloor_fremem.out`](scratchpad/fatfloor_fremem.out): diskless boot
      FRE(0) 24711 -> **25735**, the gap to the VG-8020 -4104 -> **-3080**, every
      state's delta identical to the reference's; the disk build unchanged at
      23705, 275 ahead of the CF-3300 ([`fatfloor_disk.out`](scratchpad/fatfloor_disk.out)).
      🔮 Predicted 25735 / 23705: HIT, both. `CLEAR 25000` now fits on both
      machines; 26000 is the first size refused here and the VG-8020 still takes
      28000 ([`fatfloor_clear_probe.out`](scratchpad/fatfloor_clear_probe.out),
      🔮 HIT 6/6) -- the memory-map page's example was stale and is rewritten.
      🔴 **WHAT THE MOVE BROKE, AND WHAT THAT FIXED IN THE INSTRUMENTS:**
      (a) three asserts tested the literal `$E560` disk-cell wall -> they test
      DISKROM_CELLS_LO now, and disk.asm's `MBUF_PTR + 2 > SECTOR_BUF` (cells
      BELOW the buffers) became a disjointness test, the cells being above;
      (b) 49 `; $XXXX` comment copies on DERIVED names went stale (only
      wall-literal-check rule B saw them), plus COPY_STAMP's derived-line range
      (ram-map-check: width "disputed") and a hand copy of GFX_BAD in
      basic_probe_graphics_floor.py, which read a stale cell where a stray 0
      means "no mismatch" -- it reads the sym now. ws_shift rewrites both kinds
      of copy since; (c) ws_shift's overlap check said it took widths from the
      BEFORE map and built it from the AFTER files, where the generated ABI's
      mirrors sit at the last build's addresses: the reverse rotation was
      REFUSED on CALSLT_HL carrying FWBUF's 512 B. Fixed (built before the
      rewrite, without the ABI); negative control (STRSCR onto FLD_DESC) still
      REFUSED; a reverse-apply + forward-apply round trip reproduced the
      committed diff file for file ([`fatfloor_wsshift_reverse.out`](scratchpad/fatfloor_wsshift_reverse.out),
      [`fatfloor_wsshift_negctl.out`](scratchpad/fatfloor_wsshift_negctl.out));
      (d) ram_map selftest arms A4 / A6 and wall-literal's rule-B plant pinned
      addresses the move changed -> they read the declarations now.
      🆕 **A STANDING GATE FOR THE DISKLESS FLOOR.** Nothing checked, after a
      move, that [TXTMAX, TXTMAX_NODISK) -- program RAM on a diskless machine --
      holds only cells Disk BASIC alone uses: ws_shift did at move time from a
      hand-typed list, ceiling-acceptance reads its expectation from the same
      sym, and FRE(0) is never gated as an absolute. `make ram-map-check` now
      refuses any basic name there whose own comment does not open with
      `DISK-ONLY` (bare aliases of a tagged name pass); FLD_DESC, FSECTOR_BUF and
      FWBUF carry it, and ws_shift takes the tag as --disk-only. Selftest A17
      (real tree green, a planted untagged cell RED, the alias shape accepted).
      Knife K-FF1 ([`fatfloor_knife.out`](scratchpad/fatfloor_knife.out)):
      TXTMAX_NODISK +$100, into live cells -> ram-map-check RED naming 31 of
      them, ceiling-acceptance green; restored green. 🔮 HIT (run 1 NOT SCORED:
      its restore went red on a drifted docs/ram-map.md).
      The census ([`dowrite_probe.out`](scratchpad/dowrite_probe.out)) now leaves
      the floor out -- it is program RAM, where the string heap's writes are
      correct; the buffers are reached by symbol, so the pre-move census (written
      by nothing but C-BIOS's power-on RAM probe) still answers who writes them.
      Same five writers above the floor as before the move.
      📏 **(2) RE-PRICED AND MEASURED, 2026-10-13.** The order named "the PAINT
      span stack GFX_PSTK (360 B)" -- STALE: D-PAINTSP (2026-09-27) already put
      PAINT's spans below SP, as on the reference; GFX_PSTK survives only as the
      anchor of a 360 B union window ($E7F2..$E959), and PAINT's own cells there
      are 15 B. The binding tenant is DRAW: GFX_DBUF, a 256 B buffer each
      string is COPIED into (its header: the resident's eval between round trips
      can reuse the temp pool a DRAW argument lives in), the X-frame stack
      GFX_DFSTK (32 B) and ~60 B of parse state; sprites (GFX_VBUF, 32 B) and
      CIRCLE (8 B) are the smaller tenants.
      [`drawbuf_probe.py`](scratchpad/drawbuf_probe.py) ->
      [`drawbuf_probe.out`](scratchpad/drawbuf_probe.out), write watch, each
      case minus a control that assigns the same strings: the **VG-8020 has no
      DRAW buffer** -- a 3-level `X` nest writes 18 B and a 200-character string
      12 B, all just under STKTOP (the Z80 stack), plus documented work-area
      cells ($FCB3.., $F92A..); it reads the string IN PLACE. zerobas copies it:
      the 200-character string writes 168 B of GFX_DBUF beyond the control (its
      first 43 B are written by the control's SCREEN switch too), plus the parse
      state. 🔮 HIT. 🔴 Run 1 was VACUOUS on both machines -- the default 200 B
      string space refused line 40, so no DRAW ran and the two agreed; the probe
      now refuses a run that does not print its completion marker.
      ➡️ **(2) DESIGN, by D-PAINTSP's precedent (Joost's 2026-09-27 ruling for
      the same shape, "grow below SP"):** DRAW's frame text and X frames go to
      the free gap below SP (SP − margin down to ARYEND + 2, PAINT's region --
      one graphics statement is in flight at a time), the 256 B buffer and the
      32 B frame stack leave the fixed window, and the union shrinks to the
      parse state and the sprite block. A copy is kept (not the reference's
      in-place read) because the reason for it -- the temp pool reused across
      the co-routine's round trips -- is zerobas's own architecture; where the
      copy LIVES is what costs RAM. Price the sub page-0 tenant from a clean
      tree first; the freed span then rotates to the diskless floor as in (1b).
      🔁 **REVISED THE SAME DAY:** the substitution probes found that both
      machines resolve a VARIABLE REFERENCE after `=` / `X` (zerobas by the
      accident of evaluating untokenised text; D-DRAWSUBVAR, filed above), and
      found D-ARYCUR on the way. If a lookup allocates nothing, the copy's reason
      is gone and GFX_DBUF can go entirely instead of moving below SP: measure
      that first, then do D-DRAWSUBVAR and this together.
      ✅ **(2a) DONE 2026-10-13 (D-DRAWINPLACE): DRAW reads its strings IN PLACE.**
      📏 First the claim: [`drawalloc_probe.py`](scratchpad/drawalloc_probe.py) ->
      [`drawalloc_probe.out`](scratchpad/drawalloc_probe.out) -- a write watch
      bracketed by marks, `DRAW"XA$;R=A;XB$;"` against the same figure with no
      substitution, writers named by PC (our ROM): the substitution-only writers
      touch the ARY parameter block, str_eval's cursor and vlf_found -- NOTHING
      in the string space. A lookup allocates nothing, so no body moves during a
      DRAW. 🔮 HIT. Then `gdrw_pushframe` makes the frame the body itself (DPTR =
      DVAL, DEND = DVAL + len); the copy loop, GFX_DFREE's use and the buffer's
      own ERR 5 are gone; the nesting cap (8) stays. **Sub page 0 43 -> 76 B**
      (the copy was code too). 📏 The buffer's limit was a real divergence:
      two 132-character splices (272 B) drew on the VG-8020 and raised ERR 5 here
      ([`drawinplace_before.out`](scratchpad/drawinplace_before.out)), and now
      draw ([`drawinplace_after.out`](scratchpad/drawinplace_after.out)). 🔮 Both
      HIT. Row `draw_long_splice` in graphics-acceptance phase B; knife K-DI1
      ([`drawinplace_knife.out`](scratchpad/drawinplace_knife.out)): the copying
      tenant put back -> exactly that row fails; restored 13/13. HIT. The whole
      graphics-acceptance green (403 rows).
      ✅ **(2b) DONE 2026-10-13: the layout -- diskless FRE(0) +288.** 🔴 The plan
      ("shift basic cells into the freed span") was wrong: on the DISK build that
      span was disk.rom's own cell block ($E8A0..$E9AB), overlaid on purpose --
      and that overlay turned out to include the PERSISTENT DRAW cells
      (D-DSCALEDISK, filed below). So: (1) the union shrank to its real 44 B
      ($E7F2..$E81D) and DRAW's state follows it (GFX_DPTR = GFX_SFLAGS + 1;
      GFX_DFREE, GFX_DBUF, GFX_PSTK_CAP/_ENTSZ/_END retired; the persistent
      DSCALE/DANGLE follow TGT_ADDR); (2) a ws_shift ROTATION put disk.rom's cell
      block on the diskless floor, directly above the sector buffers, and every
      basic-core cell above it (144 names, VERIFIED; basic's own FAT_DEFER copy
      tagged DISK-ONLY -- the tool refused without it); (3) DB_WIN must sit in one
      page (the build said so) and no single shift allowed it, so a second
      rotation swapped it with the cells after it (64 names). TXTMAX_NODISK
      $E76A -> $E88A. The wall asserts that meant "basic below disk cells" now
      read BASIC_WS_CEIL ($E9C0, basic's FAT block); disk.asm asserts its block
      under main's TXTMAX_NODISK (exported by gen_resident_abi.py now). GFX_DANGLE
      declared its width mid-comment (the ARY_CUR trap) and was pinned as an
      "overruns"; declared, unpinned.
      📏 [`drawcompact_fremem.out`](scratchpad/drawcompact_fremem.out): diskless
      boot FRE(0) 25735 -> **26023**, gap to the VG-8020 **-2792**; disk build
      23705 unchanged ([`drawcompact_disk.out`](scratchpad/drawcompact_disk.out)).
      🔮 Both HIT. `CLEAR 26000` now fits here, 27000 is refused
      ([`drawcompact_clear_probe.out`](scratchpad/drawcompact_clear_probe.out);
      predicted 26000 refused: MISS).
      📏 **(3) MEASURED 2026-10-14 -- STRSCR IS MOSTLY ALREADY RETIRED.**
      [`strscr_probe.py`](scratchpad/strscr_probe.py) ->
      [`strscr_probe.out`](scratchpad/strscr_probe.out) (write watch, case minus
      a numeric control): concatenation, STR$, MID$ and STRING$ build their
      results straight in the string space on BOTH machines (the VG-8020 also
      writes FBUFFR for STR$) -- zerobas writes NOTHING in STRSCR for them.
      🔮 "zerobas stages them in STRSCR": MISS (arrays slice-4a moved the engine
      to the heap). [`strscr_census.py`](scratchpad/strscr_census.py) ->
      [`strscr_census.out`](scratchpad/strscr_census.out), writers by PC: only
      READ of string DATA (`rovs_put`), INPUT / LINE INPUT / INPUT$
      (`read_into_strscr`, `sidr_lp`), and KEY (`fname_expr`, the shared
      file-name evaluator, and `key_store`); string functions and PRINT USING
      write nothing there. Most of the 129 references are readers.
      ➡️ **(3) PLAN, one gated slice each, the reference's homes:** (3a) INPUT
      items straight from the typed line in BUF; (3b) READ straight from the
      program text; (3c) file names into the official FILNAM ($F866); (3d) KEY
      strings straight into the function-key table. Then STRSCR's 256 B go, on
      both builds. Re-run strscr_census.py after each: its writer list is the
      denominator.
      📐 Part (c), the cassette pair, PRICED: CAL_BUF / CAL_BUF2 / CAS_WBUF are
      live while a PROGRAM runs (INPUT# from "CAS:" reads through cal_getbyte,
      input.asm / strvar.asm; PRINT# to tape writes through cas_wbyte,
      print.asm), so they cannot sit in diskless program RAM. Freeing the FAT
      buffers needs two new page-aligned 256 B homes, or the reference's way
      (tape I/O through the channel's own FCB buffer) -- which retires the
      read-ahead double buffer that exists because the tokeniser could not
      keep up with the tape between blocks: a tape-timing risk to measure.
      ✅ **(3) DONE 2026-10-14 (D-STRSCRBUF): +256 B, BOTH BUILDS.** Not the
      four-slice plan above: one move. STRSCR is now an alias of `BUF`
      (`basic/sysvars.inc`), the reference's own line buffer -- every remaining
      writer (READ, file names, KEY) runs while BUF holds nothing live. The one
      reader that DID keep a line in BUF while staging, console INPUT, now
      parses its typed line one byte up (`inp_readline`, `basic/input.asm`),
      so an item staged at BUF+0.. never overwrites the text still to be read.
      Then the one-page shift `ws_shift.py --move E26A EF00 100` freed
      STRSCR's old page (TXTMAX $E36A, diskless ceiling $E98A).
      📏 [`strscrbuf_fremem.out`](scratchpad/strscrbuf_fremem.out): diskless
      boot FRE(0) 26279, VG-8020 28815, gap -2536 (was -2792); 🔮 -2536 HIT.
      [`strscrbuf_disk.out`](scratchpad/strscrbuf_disk.out): disk build 23961,
      CF-3300 23430 (531 ahead); 🔮 23961 HIT.
      🔪 K-SB1 ([`strscrbuf_knife.py`](scratchpad/strscrbuf_knife.py) ->
      [`strscrbuf_knife.out`](scratchpad/strscrbuf_knife.out)): the one-byte
      shift undone -> `input-acceptance` RED on the console INPUT rows only,
      restored green; 🔮 HIT. `tests/test_input.py` gained the same negative
      control (a line at LINEBUF+0 must misread).
      📏 **RE-MEASURED 2026-11-03 ([`fremem_20261103.out`](scratchpad/fremem_20261103.out)):
      the diskless gap is 0 in all eight states** -- boot 28815 on both, every delta and
      every `FRE("")` identical (D-WSZERO moved the diskless ceiling to `$F380`). Goal (a)
      holds on the diskless build; (b) / (c) moves stay Joost's, per the rung.
      ➡️ **NEXT: (4) FLD_DESC, and PRINT USING's scratch into FBUFFR.**
      📏 **(4) LOOKED AT 2026-10-14.** FLD_DESC is ALREADY on the diskless
      floor (DISK-ONLY, program RAM without a disk): moving it gains the
      VG-8020 comparison NOTHING; the disk build is already ahead of the
      CF-3300. The reference's way (a descriptor INTO the channel's buffer)
      needs a buffer that stays put, and zerobas's FSECTOR_BUF is a working
      copy swapped on every channel switch (`PRINT #2,F1$` would print channel
      2's bytes). Left as is, reasoned, not measured.
      PRINT USING's 32 B format copy: measuring it found D-PULONG (below) --
      the copy CUT formats longer than 32. Fixed by reading the format in
      place: 27 B of the block given up (`; FREE-RAM $EFDB..$EFF5`, a HOLE in
      the workspace until a layout move takes it; not program RAM yet).
