# Statement-review tier: draft worklist (analysed 2026-08-31 while the D-CLAMPPITCH battery ran)

Denominator: 133 ex_/ev_f_ handlers; 48 have a same-named spec, 85 do not.
The 85 are NOT 85 holes -- most are covered under ARC names. Grouping, with
the crude signal refined by which arc/gate actually exercises the file:

## Likely THIN (no arc obviously owns the mechanism) — review these first
- ✅ ex_out, ex_poke, ex_vpoke — **REVIEWED 2026-08-31, NO FINDING.** All three
  bodies + the read twins (PEEK/VPEEK/INP, `ev_f_ff`) read in full. The
  suspicion the ranking was built on — a 0..255 value domain the low-byte write
  ignores — is REFUTED by D-F2-2's own VG-8020 table
  ([`spec-basic-df2-2-intarg-coercion.md`](spec-basic-df2-2-intarg-coercion.md)
  §1.1): `OUT p,v` is Group-A ADDRESS domain on the reference (`arg=40000` =
  silent truncate, only >int16 is ERR 6), POKE/VPOKE use the same measured
  domains, VPOKE/VPEEK carry the VRAM 0..16383 leaf, and the missing-paren
  surface (`PRINT PEEK`) was pinned by the I1 differential. `intarg-acceptance`
  gates it per battery. 🎯 The tier's first no-finding: recorded WITH the
  refuting table so nobody re-walks this on the same suspicion.
- ✅ ex_data + ex_restore — **REVIEWED 2026-08-31, THREE REAL DEFECTS**
  (D-DATACOLON, [`spec-basic-datacolon.md`](spec-basic-datacolon.md)): the DATA
  body scan had no quote state at BOTH sites (crunch + runtime skip), bare
  RESTORE's `ret` ended the whole line (`RESTORE:C=9` skipped `C=9`), and junk
  after RESTORE was silence where the references raise ERR 8. 6 DIFF -> 0 on
  7 rows x 3 machines. The reverse of the trio's no-finding.
- ✅ ex_deftype — **REVIEWED 2026-08-31, ONE DEFECT, hidden by a
  wrong-reason SAME** (D-DEFCORNER,
  [`spec-basic-defcorner.md`](spec-basic-defcorner.md)): the item-end check
  accepted any non-comma byte, so `DEFINT AC=7` executed `C=7` as a statement
  (refs: ERR 2). `DEFINT AB` agreed on ERR 2 by coincidence — the separating
  row made the tail harmless and observable. 9 rows x 3 machines, 0 DIFF after.
- ✅ ex_time_assign + TIME — **FALSE THIN ENTRY** (found by reading,
  2026-08-31): `spec-basic-time.md` exists with a 45/45 characterization; the
  stem-match missed it because the handler is `ex_time_assign`. The body is
  exemplary — torn-store DI guard, site-local ERR 24, adjudicated domain.
- ✅ ex_call / ex_call_us — **SUSPICION MEASURED AND FIXED 2026-08-31/09-02
  (D-FMTTAIL, `425ae88`, [`spec-basic-fmttail.md`](spec-basic-fmttail.md)):
  4 DIFF → 0 FOR ZERO BYTES.** The entry below is kept as filed; this line is
  what happened to it. The reference rejects EVERY tail — `CALL FORMATX`,
  `CALL FORMATFOO`, `CALL FORMAT X` and `_FORMAT("A:")` are all `Syntax error`
  on the CF-3300, raised BEFORE the format prompt — so the name must END the
  statement. 🔴 **THE OLD BEHAVIOUR MEANT A TYPO SILENTLY FORMATTED THE DISK**:
  `CALL FORMATX` wiped it where the reference refuses. ⚠️ And the fix is
  end-of-STATEMENT, not end-of-line: `CALL FORMAT:PRINT 1` is accepted on both
  references, which is why the test is not a bare `or a`.
  📌 This line exists because the worklist still said "unmeasured" a day after
  the fix shipped — the same stale-record class as the five battery exclusions.
- ⚠️ (as filed) ex_call / ex_call_us — **REVIEWED 2026-08-31, ONE SUSPICION FILED (TODO,
  unmeasured)**: `exc_skip` swallows everything to ':'/EOL after matching
  "FORMAT", so `CALL FORMATFOO` and `CALL FORMAT anything` both format here —
  and the skip is quote-blind (the D-DATACOLON class). Rows need the
  interactive-format rig (the CF-3300's CALL FORMAT prompts), so they are
  sketched in the TODO item rather than run tonight.
- ✅ ex_key + ex_key_stmt — **REVIEWED 2026-09-01, NO NEW FINDING**: the
  surface is two measured forms plus one pinned decline. `KEY ON/OFF` is a
  BIOS pair (ERAFNK/DSPFNK, cursor guarded); `KEY(n) ON/OFF/STOP` is the
  T3-measured trap form (byte-coerced arg, reversed band, STOP==OFF per
  D-T3-6, trappable ERR 2 on junk); `KEY <n>,"str"` and `KEY LIST` are
  stmt_error — the NOT-THIS-ONE item, already scouted (D-KEYSTR: storage
  measured, cold-boot defaults absent) and pinned in filed-row-known.txt.
- ✅ ex_motor — **REVIEWED 2026-08-31, NO FINDING**: measured to its corners
  already (spec §3.5 — `MOTOR STOP` is ERR 2 with a do-not-harmonise warning,
  bare-MOTOR toggles only at a statement boundary).
- ✅ ex_locate — **REVIEWED 2026-08-31, NO FINDING**: the surface is already
  measured to an unusual depth — screen-dumped domain-error ORDERING (parse
  all three then apply, corrected against the spec's own first reading), the
  ERR-24 missing-operand family, the fourth-argument row, and the O-3
  cursor-argument deviation recorded as such.
- ✅ ex_auto + ex_renum — **REVIEWED 2026-09-01, NO FINDING — measured deeper
  than a review reaches**: D-EDITVERB's R-AU*/R-RN* row families already cover
  every corner a read flags (empty-entry-vs-bare-lineno-DELETE separated by
  `au-emptykill`, Ctrl-STOP discard, the screen-only `*` marker, the dangling
  reference report's OLD-number format, and R-RN17's measured CONT/vars
  survival with its own separating pair). AUTO's loop stores nothing itself —
  every dispatch_line rule applies for free.

**THE THIN SECTION IS FULLY WALKED (2026-09-01).** Score: 3 verb groups with
real defects (DATA/RESTORE x3, DEFtype x1, PLAY x3 slices earlier), 5
no-findings recorded with their refuting citations, 2 false-thin entries, 1
suspicion filed with its rig named (CALL FORMAT). What remains of the tier is
the arc-covered groups below — spot-verify each arc actually reads the
MECHANISM before trusting the name — and the filed suspicions.

## Covered by an arc under another name (verify the arc actually reads the
## mechanism before skipping)
- 🔴 **ex_if — REVIEWED 2026-09-02, ONE REAL DEFECT, AND THE ARC NAME WAS THE
  PROBLEM** (D-IFSEM, [`spec-basic-ifsem.md`](spec-basic-ifsem.md)). The first
  entry in this section to be checked, and it justifies the section's own
  warning. Claimed cover: "interp.asm core: lineerr + unit tests" — but
  `lineerr` is LINE ENTRY, `lnblank`'s four ELSE rows are about CRUNCHING, there
  is no `spec-basic-if.md`, and `IF` appears across dozens of probes as FIXTURE
  SCAFFOLDING with `direct_ctrl`'s single `if_then` row as the entire execution
  surface. **A statement the whole battery leans on, measured by almost
  nothing.** Found: a false outer `IF` was caught by a NESTED `IF`'s `ELSE`
  (`IF 0 THEN IF 1 THEN B=1 ELSE B=2` ran `B=2`; refs leave B alone). +27 B,
  4 DIFF → 0 of 16. ⚠️ Two rules fit the first rows and only `n.outerelse`
  separates them — "a false IF ends the line" would have been the wrong fix.
  🟢 One suspicion REFUTED and recorded: a string condition is `Type mismatch`
  on all three (eval rejects before truthiness), and `tok_skip` is already
  quote/REM/DATA/float-stride aware.
- ✅ **program.asm flow (gosub/return/next/on_*) — VERIFIED COVERED 2026-09-02,
  a FALSE THIN ENTRY.** A name search finds no `spec-basic-gosub.md` and no
  `gosub-acceptance`, which looks like a hole — it is not. `RETURN <line>` has
  `spec-basic-retln.md` + a 27-row characterization with both references
  agreeing; `ON <trap> GOSUB` has `spec-basic-reqgosub.md` (12 rows); FOR/NEXT
  has THREE suites (`forvar`, `nxary`, `nxlist`) and two specs; `ON GOTO/GOSUB`
  has `ondom` + `onlist`. The GOSUB DEPTH difference (refs 12, zb 8) is already
  filed under `trapsvc` (🙋). Same failure mode as the `ex_time_assign` entry
  above: **the stem-match misses coverage filed under a slice name.**
  ⚠️ NOT reviewed line-by-line — `ex_gosub`'s own body was read only far enough
  to confirm the depth question is the filed one. Recorded as covered, not as
  audited.
- ✅ **print/lprint/llist — REVIEWED 2026-09-02, NO FINDING**
  (`scratchpad/printzone_probe.py`, 25 rows x 3 machines).
  🎯 **THE GAP WAS REAL BUT THE SURFACE IS CORRECT.** There is no general PRINT
  spec and no `print-acceptance`: only `spec-basic-print-unparen-compare.md`
  (one corner), `spec-print-hash-using.md` (`PRINT#` USING) and
  `lptverb-acceptance` (the LPRINT/LLIST VERB). And every probe in the tree
  prints with SEMICOLONS, so COMMA ZONES, `TAB`, `SPC` and trailing separators
  were exercised by almost nothing — `IF`'s exact shape. Measured anyway:
  comma zones (14/28), empty and doubled commas, over-width comma, `TAB`
  forwards/backwards/0/1, `SPC` 0 and wide, and the numeric leading-space rule.
  **23 of 25 agree outright.**
  🔴 **THE OTHER TWO ARE A REFERENCES-DISAGREE, NOT A DEFECT**: `TAB(45)`/
  `SPC(45)` read vg8020 **8** vs cf3300 **6**, with zerobas on 6 — a column past
  the line WRAPS, so the answer is a function of each machine's BOOT WIDTH.
  Pinning it dissolves them: `WIDTH 39` → 6/6/6, `WIDTH 32` → 13/13/13, control
  `WIDTH 39:TAB(10)` → 10/10/10. [[no-oracle-is-about-the-comparison]]
  🔴 **AND ROUND 1's READOUT WAS STRUCTURALLY BLIND — ITS OWN CONTROL CAUGHT
  IT.** Reading `POS(0)` as the harness EXPRESSION returned **1 on all 21 rows**,
  because the fixture emits `60 CLS:PRINT"[";<expr>;"]"` and that CLS resets the
  cursor first. `p.ctl` (`PRINT"AB";`, expected 3) is the row that said so. The
  read now happens on the printing line.
  📌 **NOT GATED, deliberately**: a 25-row no-finding suite costs battery time
  forever and protects no fix. The rows are kept in scratchpad and named here, so
  anything that touches `basic/print.asm` has them to hand.
- ✅ **field.asm / files.asm (close/files/kill/merge/name) — VERIFIED COVERED
  2026-09-02, and the coverage READS THE MECHANISM.** `MERGE` looked like the
  risk: no `spec-basic-merge.md`, and every probe naming it (`castail`,
  `cas_match`, `lnblank`) is the CASSETTE path, while the token comment says
  "merge an ASCII program from DISK". But `disk_probe_fat_error_disposition.py`
  covers the disk path properly — and its `merge-alive` row tests the
  DISTINGUISHING property with its reasoning written down: it merges INTO an
  existing program and asserts BOTH that the file arrived (`MG`) and that the
  resident program survived (`ZQ`), noting *"a control asserting only MG would be
  green on a MERGE that behaved like LOAD"*. That is mechanism coverage, not name
  coverage.
  🔴 **BUT IT WAS EXCLUDED FROM THE BATTERY AS "NOT MEASURED", SO NOTHING RAN
  IT.** Run 2026-09-02: **20 rows printed, 11 scored, ALL PASS** over a live FAT
  layer, with merge/name/kill/append each verified AT THE DIRECTORY SECTOR rather
  than the screen. The exclusion is re-reasoned to SCOPE (Tier-2 disk-provider
  arc, needs the disk ROM + a live FAT fixture) — *"NOT MEASURED"* is a claim that
  rots the moment anyone runs it, and nobody had.
  ⚠️ **FOUR MORE EXCLUSIONS STILL SAY "NOT MEASURED"** (I first wrote two, and
  counted only the ones I had looked at): `bdos-acceptance`,
  `diskbasic-acceptance`, `input-devices-acceptance`, `lnblank-say-acceptance`.
  Same shape, same cheap remedy: run them, then re-reason the exclusion as SCOPE
  or drop it. ✅ **`lnblank-say-acceptance` DONE the same day: 208/208 gating rows
  agree** (2 allowlisted KNOWN_DIVERGE, pinned); re-reasoned to SCOPE — it is a
  `--say` variant of a suite that IS collected and green, so running both doubles
  ~134 s of battery for one subject. Three left: `bdos`, `diskbasic`,
  `input-devices`.
- ✅ **cload/csave/bload/bsave/save — VERIFIED COVERED 2026-09-02, four probes
  under three names.** `csave`/`bload`/`bsave` have no same-named spec, which is
  what put them on this list; all three are covered anyway. `BSAVE"CAS:"` →
  `basic_probe_tape_save`; `BSAVE"A:…"` → `disk_probe_option_hygiene`; `BLOAD` →
  the bload probes plus `fat-error`'s bload-alive/missing/nodisk; `CSAVE` →
  `cassave-acceptance` (collected); `CLOAD`/`SAVE` have specs.
  🟢 The two archived probes are allowlisted in `probe-reach-allow.txt` as
  **"ARCHIVED AND STILL RE-PROVABLE — RUN GREEN 2026-08-31"**, with no `make`
  target BY CHOICE and their findings written up. That is a coherent policy, not
  a hole — the fact can be re-proven when the code changes, which is the point.
  ⚠️ Coverage verified by READING what each probe exercises; the handlers
  themselves were not re-read line by line. Covered, not audited.
- ✅ **`diskbasic-acceptance` RUN 2026-09-02: 34/34 verbs CONVERGED** — the whole
  Disk-BASIC verb surface still matches the oracle. Third exclusion this day
  moved from *"NOT MEASURED"* to a measurement; re-reasoned to SCOPE. Two left:
  `bdos` and `input-devices`.
- ✅ **graphics.asm handlers — VERIFIED COVERED 2026-09-02, and this group's
  cover is the STRONGEST of the seven.** `graphics-acceptance` is a collected
  ~300 s tent-pole, but the load-bearing part is
  `scratchpad/gate_blindness_sweep.py`: a MUTATION sweep that asks *"which
  graphics-acceptance rows can anything redden?"*, mutating the graphics tenant
  one instruction at a time and recording which rows go red.
  🎯 **THAT IS THIS TIER'S OWN QUESTION, AUTOMATED.** "Does the arc read the
  MECHANISM" is exactly what a mutation sweep answers, and it has already found
  **three blind gate rows in one week** — G3's clip rows (D-SPOKELINE), G6's
  `clip_left` (D-DRAWCLAMP) and `box_bf` (D-BFBYTE), each green for months while
  blind to the very thing it was named for. No other group has an instrument that
  checks its own gate this way.
  ⚠️ The open `ntwall` rows (6, PAINT) are NOT closed by this — they are a real
  divergence behind a design step, tracked on the correctness scoreboard.

**THE ARC-COVERED SECTION IS FULLY WALKED (2026-09-02).** Seven groups. Score:
**2 real defects** (`IF` — a false outer IF caught by a nested IF's ELSE, +27 B,
now gated; `PRINT USING` — six float format specifiers missing behind a stale
"arrives with Phase-3 floats" comment), **1 real gap with no defect** (`PRINT`'s
comma/TAB/SPC surface, 25 rows measured, ungated by choice), **4 verified
covered** (program.asm flow, files.asm, save/cassette verbs, graphics).
🔴 **THE ARC NAME WAS WRONG IN 3 OF 7.** And the split is worth keeping: the
defects came from READING THE CODE; the covered verdicts came from reading what
the probes exercise. Those are worth less, and are marked *covered, not audited*.
📏 **FOUR BATTERY EXCLUSIONS CONVERTED** from *"NOT MEASURED"* to a measurement
along the way: `fat-error` 11/11, `lnblank-say` 208/208, `diskbasic` 34/34,
`input-devices` 50/50. One left: `bdos` (Tier-2 DOS-boot).
- program.asm flow (gosub/return/next/on_*): lineerr shards + trap
  acceptances + D-TRAPSVC/D-ONERRARM.
- field.asm (get/lset/rset): FIELD arc + D-FLDCLOSE; files.asm
  (close/files/kill/merge): disk acceptance + D-OPEN2 rows.
- interp.asm core (let/if/goto/rem/data-sep/end): lineerr + unit tests.
- print/lprint/llist: LPT arc (cbios-lptout-followup) + print specs.
- cload/csave/bload/bsave/save: the cassette + truncload + oomtail work.
- ex_print_using: spec-print-hash-using.

## Method (calibrated on PLAY, 3 commits from 1 verb)
1. Read EVERY layer of the verb first (resident stub, tenant, servicer,
   tables). 2. Code-review for mechanism smells: wholesale stores of shared
   state, 16-bit wrap, clamps nobody measured, "mirrors X" comments, guards
   whose only outcome is deferred. 3. Write differential rows for what the
   review flags -- accept/reject FIRST, then value/trace rows where a screen
   read is blind. 4. Fix against the rows; heavy gates for the touched arc.

⚠️ A RANKED CANDIDATE ROTS. Re-verify "thin" per verb at pick-up time -- this
file records the 2026-08-31 reading, not the truth.
