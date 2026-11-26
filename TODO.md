# zerobas roadmap

zerobas is a **clean-room reimplementation of MSX1 system software** — three
components (BASIC interpreter + cassette + disk) combined with an open BIOS (C-BIOS)
only at runtime — with **two co-equal goals**: the clean-room implementations
themselves, and the clean-provenance **documentation** of how these systems work
that the same discipline yields (see [`MISSION.md`](MISSION.md)). Scope today
is MSX1; the BASIC half targets **faithful, full MSX1 BASIC** (Phase 1 shipped the
*game-loader-stub* subset — enough to boot disk/tape game loaders — and the charter
has since been raised to full-language faithfulness, pursued in Phase 3), while tape
and disk are device-complete (read **and** write).

See [`README.md`](README.md) for the charter and the legal/provenance firewall,
[`PROVENANCE.md`](PROVENANCE.md) for the traceability rules every item below must
honour (allowed sources only; no disassembly), and
[`docs/dev-workflow.md`](docs/dev-workflow.md) for how to implement + validate one
item — do **one item per session** to keep context lean.

## Phases at a glance

| Phase | Scope | State |
|---|---|---|
| **1 — loader-stub BASIC + transports + standardization** | just enough MSX-BASIC to run `.BAS`/binary loader stubs; tape + disk read/write; standard DSKIO/`HPHYD` interfaces | **✅ closed** |
| **2 — full disk (Disk BASIC integration)** | the full file-channel verb surface (sequential + random-access + dir mgmt + `CALL FORMAT`), all oracle-validated | **✅ verb surface complete** — only the Tier-2 provider oracle (a distinct DOS-boot sub-track) + a few Phase-3-gated verbs remain |
| **3+ — full MSX1 BASIC** | floating point, full string engine, arrays, graphics, sound, … | **active charter** (raised from loader-stub) — landed: string engine, float pack, math pack, **arrays/DIM arc CONCLUDED** (through slice-4c string-scalar unification — the faithful unified variable area; no fixed variable pool remains) |

## Open — standing residuals (INDEX; this is the pickup list)

- [ ] **D-REREAD — REREAD EACH ROUTINE AGAINST ITS CONTRACT: 82 B FROM THE FIRST TEN (2026-10-30).** -> [D-REREAD](todo/open/D-REREAD.md) <!-- item:open/D-REREAD -->

- [ ] **WHICH GATE SUITES EARN THEIR TIME? A CENSUS, THEN A MUTATION SWEEP (D-SUITESWEEP, Joost 2026-11-01: "I have...** -> [D-SUITESWEEP](todo/open/D-SUITESWEEP.md) <!-- item:open/D-SUITESWEEP -->
- [x] **D-GATESPEED — THE BATTERY'S WALL TIME, EVERY ITEM OF THE 2026-11-25 REVIEW (Joost: "fix all of these please...** -> [D-GATESPEED](todo/done/D-GATESPEED.md) <!-- item:done/D-GATESPEED -->

- [ ] **BOULDER DASH II IS FRAGILE TO LOW-REGION CHANGES THAT PRESERVE EVERY VALUE (D-BD2FRAGILE, 2026-10-31).** -> [D-BD2FRAGILE](todo/open/D-BD2FRAGILE.md) <!-- item:open/D-BD2FRAGILE -->

- [ ] **fp_mul WITH AN INVALID BCD DIGIT (> 9): THE NEW LOOP'S LEFTMOST CELL CAN DIFFER FROM THE OLD ONE (D-FPMULBC...** -> [D-FPMULBCD](todo/open/D-FPMULBCD.md) <!-- item:open/D-FPMULBCD -->

- [ ] **THE PROGRAM LADDER: WHOLE 1980s-STYLE BASIC PROGRAMS AS INTEGRATION TESTS (D-PROGLADDER, Joost's idea 2026-...** -> [D-PROGLADDER](todo/open/D-PROGLADDER.md) <!-- item:open/D-PROGLADDER -->

- [ ] **STUDY: DEFERRED ERRORS VS RAISING AT THE POINT OF DETECTION — HOW MUCH OF THE PER-COMMAND "WHICH ERROR WINS...** -> [D-DEFERRSTUDY](todo/open/D-DEFERRSTUDY.md) <!-- item:open/D-DEFERRSTUDY -->

- [ ] **A TYPE MISMATCH IS RAISED AT A DIFFERENT POINT OF THE EXPRESSION THAN ON THE VG-8020, IN BOTH DIRECTIONS (D...** -> [D-TMORDER](todo/open/D-TMORDER.md) <!-- item:open/D-TMORDER -->

- [ ] **JOOST RULED 2026-09-17: EVERY HOOK-IMPLEMENTABLE KEYWORD MUST USE ITS HOOK, AND EVERY DISK COMMAND'S IMPLEM...** -> [X-JOOST-RULED-2026-09-17-EVERY](todo/open/X-JOOST-RULED-2026-09-17-EVERY.md) <!-- item:open/X-JOOST-RULED-2026-09-17-EVERY -->

- [ ] **STEP 9 RE-OPENED WITH AN ANSWER: `LOAD` HAS CELLS OF ITS OWN, AND THE REFERENCE'S LOOP IS** -> [X-STEP-9-RE-OPENED-WITH-AN](todo/open/X-STEP-9-RE-OPENED-WITH-AN.md) <!-- item:open/X-STEP-9-RE-OPENED-WITH-AN -->

- [ ] **D-DEADSEED — `check_dead_code` STAYED GREEN WITH `fat_io_append` UNCALLED (found 2026-10-06 by S10.B increm...** -> [D-DEADSEED](todo/open/D-DEADSEED.md) <!-- item:open/D-DEADSEED -->

- [ ] **D-CLOADREAD — AFTER CLOAD zerobas CALLS H.READ; THE VG-8020 PRINTS `Ok` AND CALLS H.MAIN ALONE (measured 20...** -> [D-CLOADREAD](todo/open/D-CLOADREAD.md) <!-- item:open/D-CLOADREAD -->

- [ ] **D-S16PREEXIST -- THREE DIFFERENCES THE S16 ROWS FOUND, PRESENT ON HEAD'S ROM TOO (2026-10-16)** -> [D-S16PREEXIST](todo/open/D-S16PREEXIST.md) <!-- item:open/D-S16PREEXIST -->

- [x] **D-FLDDESC — FIELD AS THE REFERENCE DOES IT: NO TABLE, THE VARIABLE'S OWN DESCRIPTOR POINTS INTO THE CHANNEL...** -> [D-FLDDESC](todo/done/D-FLDDESC.md) <!-- item:done/D-FLDDESC -->

- [ ] **D-ROMSIZE — BRING THE ROM FOOTPRINT TOWARD THE REFERENCE: ~2.2x ITS BASIC TODAY (Joost, 2026-10-14)** -> [D-ROMSIZE](todo/open/D-ROMSIZE.md) <!-- item:open/D-ROMSIZE -->

- [ ] **D-DISKRUN — THE DISK COLLECTION ON BOTH MACHINES: 18 SYSTEM DISKS REACH MSX-DOS ON THE CF-3300 AND BASIC ON...** -> [D-DISKRUN](todo/open/D-DISKRUN.md) <!-- item:open/D-DISKRUN -->

- [ ] **D-P0CB — COLD STATEMENTS OUT OF MAIN INTO zerobas-sub2 PAGE 0, THROUGH A PAGE-0 CALL-BACK (Joost 2026-10-21...** -> [D-P0CB](todo/open/D-P0CB.md) <!-- item:open/D-P0CB -->

- [ ] **D-TWOVARIANT — "BEST WITH SUB ROM" AND "GOOD WITHOUT SUB ROM" (Joost 2026-10-21, an idea, NOT a plan)** -> [D-TWOVARIANT](todo/open/D-TWOVARIANT.md) <!-- item:open/D-TWOVARIANT -->

- [ ] **D-VG8020-20 — ALSO RUN THE DIFFERENTIALS AGAINST THE VG 8020/20 (filed 2026-10-13, Joost: "add testing aga...** -> [D-VG8020-20](todo/open/D-VG8020-20.md) <!-- item:open/D-VG8020-20 -->

- [ ] **AN ASCII BASIC TAPE (`RUN"CAS:"`) TAKES ~40% LONGER TO LOAD THAN ON THE VG-8020 (D-ASCTAPESPD, found 2026-1...** -> [D-ASCTAPESPD](todo/open/D-ASCTAPESPD.md) <!-- item:open/D-ASCTAPESPD -->

- [ ] **D-TAPELOAD — MANY `.cas` AND `.wav` TAPES DO NOT LOAD (Joost, 2026-10-11; TRIAGED 2026-10-14, see the end)** -> [D-TAPELOAD](todo/open/D-TAPELOAD.md) <!-- item:open/D-TAPELOAD -->

- [ ] **D-BRIDGEIX — THE HOST SUBROM BRIDGE KEEPS IX (AND A, F) THE WAY THE MACHINE DOES NOT (found 2026-10-22 by D...** -> [D-BRIDGEIX](todo/open/D-BRIDGEIX.md) <!-- item:open/D-BRIDGEIX -->

- [ ] **D-BASICPUB — THE PUBLISHED BASIC-ROM ENTRY POINTS (MATH-PACK + INTERPRETER INTERNALS) ARE NOT AT THEIR ADDR...** -> [D-BASICPUB](todo/open/D-BASICPUB.md) <!-- item:open/D-BASICPUB -->

- [ ] **D-TAPINBLK — $72D4 PAST A BLOCK'S END, AND $72E9 WITH NO TAPE (2026-10-16)** -> [D-TAPINBLK](todo/open/D-TAPINBLK.md) <!-- item:open/D-TAPINBLK -->

- [ ] **D-SPRBASE0 — IN SCREEN 0, ATRBAS / PATBAS READ 0 (2026-10-16)** -> [D-SPRBASE0](todo/open/D-SPRBASE0.md) <!-- item:open/D-SPRBASE0 -->

- [ ] **D-BIOSSCRATCH — UNDOCUMENTED REGISTERS AFTER SNSMAT / GTTRIG / GTSTCK / CLRSPR (2026-10-16)** -> [D-BIOSSCRATCH](todo/open/D-BIOSSCRATCH.md) <!-- item:open/D-BIOSSCRATCH -->

- [ ] **D-PAGE2ISLAND — TENANTS MAPPED INTO PAGE 2 ($8000-$BFFF), FOR AUDITED TENANTS ONLY (ruled open 2026-10-11)** -> [D-PAGE2ISLAND](todo/open/D-PAGE2ISLAND.md) <!-- item:open/D-PAGE2ISLAND -->

- [ ] **~~TIER 5~~ TIER 4 (SWAPPED 2026-09-24) IS NOW "MATCHES THE REFERENCE'S RAM USAGE" — THE RUNG, AND WHAT CAN...** -> [D-TIER5RAM](todo/open/D-TIER5RAM.md) <!-- item:open/D-TIER5RAM -->

- [ ] **COMPARE RAM USAGE AGAINST THE REFERENCE, CELL BY CELL — AND JOOST'S HUNCH IS THE HYPOTHESIS TO SCORE** -> [X-COMPARE-RAM-USAGE-AGAINST-THE-REFERENCE](todo/open/X-COMPARE-RAM-USAGE-AGAINST-THE-REFERENCE.md) <!-- item:open/X-COMPARE-RAM-USAGE-AGAINST-THE-REFERENCE -->

- [ ] **THERE IS NO SINGLE RAM MAP, AND THAT IS WHAT MAKES EVERY RAM QUESTION EXPENSIVE** -> [X-THERE-IS-NO-SINGLE-RAM-MAP](todo/open/X-THERE-IS-NO-SINGLE-RAM-MAP.md) <!-- item:open/X-THERE-IS-NO-SINGLE-RAM-MAP -->

- [x] **PAINT's SPAN STACK IS A FIXED ARRAY; THE REFERENCE'S GROWS DOWN FROM `STKTOP` — A DIVERGENCE NO ROW COVERS,...** -> [X-PAINT-S-SPAN-STACK-IS-A](todo/done/X-PAINT-S-SPAN-STACK-IS-A.md) <!-- item:done/X-PAINT-S-SPAN-STACK-IS-A -->

- [ ] **`refcache-check` GOES RED ON THE CALENDAR, AND THE RETRY ARM CALLS IT "REAL".** -> [X-REFCACHE-CHECK-GOES-RED-ON-THE](todo/open/X-REFCACHE-CHECK-GOES-RED-ON-THE.md) <!-- item:open/X-REFCACHE-CHECK-GOES-RED-ON-THE -->

- [ ] **TOKENISED `LOAD` IS 5.8× THE REFERENCE PER BYTE, AND THAT IS NOT THE INTERPRETATION GAP.** -> [X-TOKENISED-LOAD-IS-5-8-THE](todo/open/X-TOKENISED-LOAD-IS-5-8-THE.md) <!-- item:open/X-TOKENISED-LOAD-IS-5-8-THE -->

- [ ] **THE CARVE INVENTORY, RE-RUN 2026-09-17 (D-LONGRUN) — THE MECHANICAL FAMILY IS NOT SHUT, IT IS JUST SMALL: ~...** -> [D-LONGRUN](todo/open/D-LONGRUN.md) <!-- item:open/D-LONGRUN -->

🔬 **RE-SWEEP DONE 2026-08-26 (D-TODOSWEEP), 65 TRANCHES** —
[`docs/todo-sweep-2026-08-26.md`](docs/todo-sweep-2026-08-26.md), verdicts in
`scratchpad/sweep_verdicts.json`, denominator `tools/todo_inventory.py`.
**Rule: re-run everything, inherit no claim.** ✅ **COMPLETE 2026-08-26 —
178 of 178 subject blocks carry a verdict** (`tools/todo_inventory.py --audit
scratchpad/sweep_verdicts.json` reports `subject with NO verdict: 0`).
📏 **HOW THEY WERE SETTLED: 68 RAN** (emulator, probe or gate), **53 INSPECTED**
(source, tree, git), **57 READ** from the block's own text. **32 carry an
explicit `read-not-run` caveat** — a read is a verdict about the WRITING, not
about the machine, and this file says which is which rather than averaging them.
🔴 **THE SUBJECT SET GREW WHILE BEING SWEPT, 177 → 178**: the last tranche
measured `NAME "old" AS <non-string>`, found two divergences, and REOPENED the
item that had closed that question at six verbs. A sweep that files nothing has
not thereby been thorough.
⚠️ **THE VERDICTS ROT LIKE ANY OTHER FIGURE.** The 2026-08-09 staleness sweep
covered 17 items and nothing gated it; this one is 178 and nothing gates it
either. Re-derive from `scratchpad/sweep_verdicts.json` and the audit, never
from this paragraph.

📦 **AND THEN THE CLOSED WORK WAS SPLIT OUT — 2026-08-26.** 233 blocks and three
whole done-record sections moved to [`docs/TODO-done.md`](docs/TODO-done.md),
**12577 → 3722 lines**, leaving **111 open items and 4 closed blocks whose
verdict is LIVE**.
📦 **SECOND PASS 2026-08-30**: 54 more blocks and three whole done-record
sections moved, **6145 → 4676 lines**; the archive grew to ~10400. **Count the
markers, do not quote these** — `python3 tools/todo_inventory.py --count`.
🟢 **THE TWO DEFECTS THAT SECOND PASS FOUND ARE FIXED (D-SPLITFIX, 2026-08-30)**
— the archive is APPENDED to and refuses to shrink, and the citation repointer no
longer backtracks into a shorter line number. Seven arms, collected by
`make selftest-check`. 🔴 **THE SPLIT RULE IS THE VERDICT, NOT THE CHECKBOX** —
`- [x]` was not evidence of finished work until the sweep said so, which is the
whole reason this section exists. Regenerate with
[`tools/split_todo_archive.py`](tools/split_todo_archive.py) (it refuses unless
the two files reconstruct the original byte for byte).
🟢 **AND THE CITATIONS INTO THIS FILE NO LONGER ROT SILENTLY.** All 42 now carry
the block's content-derived id beside the line — the line is for a human's
click, the **id** is what [`make todo-citation-check`](Makefile) trusts, with
`--fix` to repair a drifted line and `--annotate` to attach a missing id.

🤖🙋 **EVERY OPEN ITEM CARRIES A PICK-UP MARKER, AND THE MARKER SAYS WHO HAS TO
BE IN THE ROOM** — not what the item touches. Derived 2026-08-26 by
[`scratchpad/classify_open.py`](scratchpad/classify_open.py), which prints the
signal that decided each one so it can be argued with.

⚠️ **THE `n` COLUMN ROTS — RECOUNT IT, DO NOT QUOTE IT:**
**`make todo-marker-check`** (D-MARKGATE, 2026-09-05; `scratchpad/classify_open.py --count` is now a
wrapper over the same rule, because it used to carry a DIFFERENT and wrong one).
It reads the markers actually in this file and FAILS if an open item carries none,
or carries two buckets, or if its block splitter and `todo_inventory.py` disagree. The figures below are **as
measured 2026-08-27** and stand as taken; on that day the previous set was wrong
by **12** in the 🤖 bucket, and three items were `- [ ]`, unmarked, and ended
"✅ DONE" — so the loop would have re-picked finished work. (`classify_open.py`'s
own headline re-DERIVES a classification from signals and may differ by an item
or two; the MARKERS in this file are what the loop reads, and `--count` counts
those.)

| marker | meaning | n (2026-08-27) |
|---|---|---|

🔴 **AND THE MARKER'S *REASON* IS LARGELY BOILERPLATE — MEASURED 2026-09-09,
WHEN JOOST ASKED FOR HIS OPEN QUESTIONS ONE BY ONE.** 45 open items carry a
🙋/🔃 marker, and **20 of them carry one of seven canned phrases**, all applied by
the same bulk commit `c93edf74` (*"mark every open item with who has to be
there"*) — the same commit whose `--annotate` pass laundered two citations onto
the wrong block:

    6  ...(charter / scope)          4  ...(page-1 budget)
    5  ...(retire / delete)          2  ...(refactor, no oracle)

🎯 **SO A MARKER'S CATEGORY IS A GUESS ABOUT THE ITEM, NOT A STATEMENT FROM IT.**
Three consequences seen the same hour: `int_h_body`, a clean-room paper-trail
JUDGEMENT, is filed under *"(retire / delete)"*; two blocks of **218 and 213
lines** carry the same trailing *"(retire / delete)"* that a 17-line block does,
so the phrase cannot be describing either; and the emulated-time-budget item
carries *"(user-visible product text)"*, which is not what it is about.
➡️ **HOW TO READ THE QUEUE.** Count the markers, but never quote the marker's
REASON without reading the block — and when summarising the queue for Joost,
group by the DECISION, not by the marker. The 45 markers were six actual
decisions.
⚠️ Not fixed here: re-deriving 20 reasons by hand is a bigger job than the
queue it serves, and a wrong reason is visible the moment anyone reads the
block. Recorded so the count is never presented as 45 open questions again.
| 🤖 **AUTONOMOUS** | the reference or a gate settles it; finishable unattended | **62** |
| 🔭 **SCOUT-THEN-ASK** | the decision is Joost's, the measuring and pricing in front of it are not | **6** |
| 🙋 **NEEDS-JOOST** | a call that is his: what to evict from a scarce page, a refactor with no oracle, a charter question, a retirement | **25** |
| ⛔ **BLOCKED** | neither can start it now — an idle host, a missing fixture, apparatus that must be built first | **9** |

🎚️ **PRIORITY TIERS (Joost, 2026-09-10) — WHAT TO PICK, PER KEYWORD, IN THIS
ORDER.** Set after a night whose three commits were all TIER 5 or apparatus:
*"to give this project any chance of ever reaching completion without requiring
100 % correct edge cases, some steering is needed."*

| tier | per keyword | test |
|---|---|---|
| **TIER 1** | works correctly in the happy path | a MISSING keyword is TIER 1, not "unimplemented" |
| **TIER 2** | works in reasonable time | usable; not yet on par |
| **TIER 3** | handles the most common error situations | *would a 1985 magazine listing plausibly hit this?* — Type mismatch, Syntax error, Illegal function call on a bad argument, File not found, Out of DATA, Subscript out of range, Division by zero, a forgotten disk |
| **TIER 4** | matches the reference's RAM usage | not "exactly" — the references disagree with each other (D-TIER5RAM); per keyword it is DERIVED from the whole-RAM-map comparison |
| **TIER 5** | faster than or on par with the reference | the baseline is NOT 1.0 (D-INTERPSPEED §4); T5 rows RECORD the ratio and set no bar yet (Joost, 2026-09-24) |
| **TIER 6** | handles every error situation correctly | nesting depth 11, `+$$###`, string-temp-stack overflow, which of two errors wins |

🔢 **THE NUMBERING HAS MOVED TWICE, SO PROSE USES THE NUMBERING OF ITS DATE.**
**2026-09-10:** five tiers, TIER 4 = speed, TIER 5 = every error.
**2026-09-22:** RAM usage inserted as TIER 5, every error bumped to TIER 6.
**2026-09-24 (D-TIERSWAP):** RAM and speed swapped — TIER 4 = RAM usage,
TIER 5 = speed. So a "TIER 5" dated before 09-22 means every error, one dated
09-22/23 means RAM, and one from 09-24 on means speed. ⚠️ **The `🎚️` tags
are the only live numbering; `tools/tier_table.py` reads those, never the
prose.** The 🔁 PARKED notes quoting *"every TIER 5 item waits until TIERS 1–4
are clean"* are 09-10 prose: that parking is of the EVERY-ERROR tier, now 6.

🎯 **RULED (Joost, 2026-09-13): "kwsweep SUPPORTED is not evidence for tier 1",
then "let's call no tier established tier 0 to make it clear" — and, shown the
BROAD reading, "yes, this is what I mean indeed". EVERY KEYWORD IS TIER 0.**
An open TIER n item says a defect is FILED at n, **not** that n−1 was reached;
a row that agrees is ONE AGREEMENT POINT. Neither is attainment, so the table
no longer prints a ladder: every row reads TIER 0 and the text beside it says
only what is KNOWN AGAINST the keyword.
🌱 **BREADTH BEGINS (D-KWBREADTH batch 1, 2026-09-13) — the OTHER half of what
establishing a tier needs, and the half no keyword has.**
| row | reading | the form it adds |
|---|---|---|
| `sgn_b` | `[-1 0 1]` | all THREE sign branches — a row taking only `SGN(5)` passes on an implementation that never returns −1 |
| `fix_b` | `[-2 2]` | truncation toward zero on BOTH signs, where `FIX` and `INT` differ |
| `cos_b` | `[ 1 ]` | the exact point of the cosine |
| `vpoke_b` | `[ 7 ]` | the **LAST** byte of a 16 KB VRAM, where the existing row uses address 0 — an off-by-one in the address path shows here and nowhere else |
| `vpoke_b2` | `[ 255 ]` | the maximum byte VALUE, where the existing row writes 9 |
🎯 **EVERY READING IS A VALUE, NOT AN ERROR** (mode 6, learned from `PAD` the
same day), and none is 0 on both sides, which would merely trade mode 6 for
mode 2. **`vpoke_b` is KNIFE-PROVEN CONNECTED** — breadth that would notice a
break, not another agreement point.
⚠️ **AND THE LIMIT, SO FIVE ROWS DO NOT READ AS FIVE EQUAL PIECES OF
EVIDENCE**: `SGN`, `FIX` and `COS` are among the **30 keywords the knife
REFUSES** — the math and string groups dispatch through a third shape it
cannot reach — so their connectedness is UNMEASURABLE until that cut exists.
Their rows are breadth; they are not yet breadth that is known to bite.
🔬 **AND A REUSABLE LESSON: THE 38-COLUMN GUARD MEASURES THE TYPED LINE, BUT
WHAT WRAPS IS THE LINE PLUS WHATEVER THE SCREEN ALREADY HOLDS.** `vpoke_b2`
cleared the guard at 37 characters, PASSED when run alone, and lost its echo
anchor entirely once other rows had run before it — `UNREADABLE`, with the
reference showing a wrap pipe (`|[ 255 ]`). **A row that passes in isolation
and fails in company is precisely why the whole sweep summary gets read**, and
why `ONLY=` is a debugging aid rather than a verdict. Both `VPOKE` rows are
stored-mode now and the reason is recorded ON THE ROW, where the next author
meets it.
🌱 **BREADTH BATCH 2 (D-KWBREADTH, 2026-09-13) — AND THIS TIME THE TARGETS
WERE MEASURED, NOT GUESSED.** Batch 1 was aimed by intuition and landed on the
WELL-covered end: `make kwcover` over a full **83-suite / 46 969-line** capture
(0 of 159 keywords UNEXERCISED) puts `STR$` at 18 suites, `MID$` 14, `STRING$`
13, `HEX$` 10, `OCT$` 7, `INSTR` 6, `RND` 5. The planned batch-2 list was every
one of those. 🎯 **THE THIN END IS EIGHT KEYWORDS TYPED BY `kwsweep` PLUS
EXACTLY ONE OTHER SUITE — `ATTR$ BSAVE CALL CMD CVD DELETE IPL SET` — AND THAT
ONE SUITE IS `lnblank-acceptance` FOR ALL EIGHT, WHICH TYPES THEM AS TOKENISER
SUBJECTS (`20 CALL X`, `20 CALLX5`, `20 CALL X+5`) AND NEVER EXECUTES ONE.** So
those eight have ONE scoring row each; the MK/CV family sits just above at 3-4
suites with the same shape, and its existing rows have a visible reach limit:
`CVI(MKI$(7))` uses a value whose high byte is 0 and whose sign bit is clear,
so neither a byte swap nor a sign error can show; `CVS(MKS$(1))` and
`CVD(MKD$(1))` use a value that survives almost any mantissa packing; and
`LEN(MKI$(1))=2`, `LEN(MKS$(1))=4`, `LEN(MKD$(1))=8` **are all passed by a stub
that returns the right number of ZERO bytes.**
| row | reading | the form it adds |
|---|---|---|
| `cvi_b` | `[-1  32767 ]` | the SIGN and the 16-bit EXTREME, neither reachable through 7 |
| `cvs_b` | `[ 1.5 ]` | a FRACTION, on the 4-byte single pack |
| `cvd_b` | `[ .1 ]` | a fraction with NO exact binary form, on the 8-byte double pack |
| `mki_b` | `[ 2 ]` | MKI$'s **CONTENT** where its own row scores only LENGTH; 258 is `$0102`, so both bytes are non-zero and the reading confirms the little-endian order `basic/sysvars.inc:252` documents |
🔪 **THREE OF THE FOUR ARE KNIFE-PROVEN LOAD-BEARING** (`CVI`, `CVS`, `CVD` all
went MISSING with the selector cut) — a real improvement on batch 1, where
`SGN`/`FIX`/`COS` were all unmeasurable. Sweep: `DIVERGENT=2 SUPPORTED=188`,
the two divergences still the expected `swap_t3`/`dskf_t3` pair.
🔬 **AND `MKI$`'s REFUSAL IS THE FIRST CONCRETE LEAD ON THE 30**: the knife
reports *0 `cp $AE` sites with an `ev_*` target, 0 occurrences in
`ev_ff_argtab`*, and `basic/sysvars.inc:250` says why in prose written long
before the knife existed — **MKI$ is evaluated in `basic/strvar.asm` because it
returns a STRING**. The third cut shape is not one mystery, it is the
STRING-RETURNING function path, and that is a searchable target rather than a
tally.
📏 **THE PER-KEYWORD COST, WHICH IS THE NUMBER THAT DECIDES WHETHER THIS SCALES
TO 159**: one full sweep and one knife invocation covered the WHOLE batch, so
machine time is per-BATCH, not per-keyword, and amortises away. The irreducible
cost is DESIGN — read the existing row, then find a form it cannot reach — and
that is minutes per keyword and does not parallelise onto the machine. **So
breadth scales, and the binding constraint is authorship, not wall time.**
🌾 **BREADTH BATCH 3 (D-KWBREADTH, 2026-09-14) — A NEGATIVE RESULT, AND IT CLOSES
THE THIN-EIGHT LINE WITH A MEASURED REASON.** 🔴 **THIN COVERAGE AND *BROADENABLE*
COVERAGE ARE NOT THE SAME THING.** `kwcover` ranks by EXERCISE, and a keyword can
be thin **because there is nothing to exercise** — so the screening step is
reading each candidate's EXISTING row, and it is the cheap step that saves the
expensive one.
| of the thin eight | why breadth cannot help |
|---|---|
| `SET` `IPL` `CMD` | refuse ON SIGHT — ERR 5 on **every** reference; no working behaviour exists to broaden |
| `CALL` | its row tests that the word is RESERVED, which exercises the TOKENISER, not a handler |
| `ATTR$` | its exec line is `None` (MSX-DOS2-era, measured for the record) |
| `BSAVE` | **already** breadth-quality: a round trip, POKE 99 → BSAVE → overwrite with 7 → BLOAD → read 99 back |
| `CVD` | done in batch 2 |
| `DELETE` | the one real candidate — and it was MEASURED, not assumed |
🔬 **`DELETE` OF AN EXISTING LINE SILENTLY TERMINATES THE PROGRAM** — no error, no
output — and **all three machines agree**, both references included
(`scratchpad/deleterange_probe.py`, VG-8020 · CF-3300 · zerobas). The no-delete
CONTROL prints `[C9]` on all three, so the harness and the program shape are sound
and the silence is `DELETE`'s own doing; `DELETE 30-40` over existing lines behaves
the same. 🎯 **So its success path CANNOT CARRY A VALUE READING: a row for it
would read NOTHING ON BOTH SIDES, which is mode 2** — trading one blind spot for
another, which is the trade `PAD` already taught. **The thin eight yield ZERO
broadenable rows, and that is now a measurement rather than an omission.**
✅ **AND ONE USEFUL BY-PRODUCT, because the `AUTO` hazard was the reason to check:
`DELETE` RETURNS CLEANLY TO THE `Ok` PROMPT** — the `color auto goto list run`
function-key line is intact in every capture — so unlike `AUTO` (which left the
machine in LINE-ENTRY MODE and swallowed the input of 21 following rows) it would
NOT have poisoned its neighbours. The hazard was real in kind, absent in this case.
🔴 **AND THE PROBE'S OWN FIRST RUN IS THE LESSON WORTH KEEPING: REUSE THE EXISTING
TABLE, DO NOT INVENT YOUR OWN.** It supplied its own boot/reset values instead of
`basic_probe_kwsweep`'s `MACH_BOOT`/`MACH_RESET_PRE`, so the CF-3300 booted into
SCREEN 1 and every capture was the **PATTERN GENERATOR TABLE read as text** —
byte-identical for all four cases, **which is exactly what a broken leg looks like
when you want a result**. `omsx_repl` REFUSED TO CACHE IT AND SAID WHY rather than
handing back a plausible string. `basic_probe_kwsweep.py:1872` already records that
these two tables disagreeing "is what let this sit"; this probe reproduced that
exact failure by not reusing the one that exists.
🌾 **BREADTH BATCH 4 (D-KWBREADTH, 2026-09-14) — AND THE SCREEN THAT FOUND IT IS
THE REUSABLE PART.** Two row shapes predict an untouched behaviour far better than
any coverage RANK: **(a) a row that scores an ERROR leaves the SUCCESS path
untouched; (b) a row that scores a LENGTH or an EXISTENCE leaves the CONTENT
untouched** — which is exactly what `MKI$` turned out to be in batch 2.
⚠️ **AND THE SCREEN ITSELF OVER-FLAGGED, THE SAME WAY THE KNIFE DID.** A regex
looking for `LEN(` named `inkey` a candidate; the row is
`PRINT"[";A$;LEN(A$);"]"` → `[A 1 ]` and prints the CONTENT as well. **Every
candidate was then confirmed by READING its row, not by trusting the filter** —
the third time in one night that my own instrument drew a line I nearly reported
as a property of the tree.
| row | reading | what the old row could not reach |
|---|---|---|
| `using_b` | `[3.15]` | `##` needs no fraction, no point placement and no rounding; `#.##` needs all three, and 3.146 must ROUND to 3.15, not truncate to 3.14 |
| `mks_b` | `[ 65 ]` | MKS$'s CONTENT — `LEN(MKS$(1))=4` is passed by a stub returning four ZERO bytes; 1.5 packs as `65 21 0 0`, measured on the CF-3300 |
| `mkd_b` | `[ 65 ]` | the same reading on the 8-byte DOUBLE pack |
| `input_b` | `[Hello]` | the BYTES, not the COUNT — `LEN(A$)=24` is passed by a read returning 24 BLANKS; `HI.TXT` is `"Hello from zerobas-disk!"` (`tools/make_test_dsk.py`) |
🔪 **THREE OF THE FOUR ARE KNIFE-PROVEN LOAD-BEARING** (`MKS$`, `MKD$`, `INPUT`).
⚠️ **`USING` IS UNMEASURABLE, AND FOR A STRUCTURAL REASON WORTH RECORDING: token
`$E4` IS NOT IN `stmt_table` AT ALL** — `USING` is a MODIFIER of `PRINT`, not a
dispatched statement, so the statement cut cannot reach it by construction, the
way `ELSE` and `TO` cannot. That is a THIRD unconnectable-by-construction shape
beside `CALL`/`MAX` (reservedness) and it is a property of the language, not a
gap in the knife.
📏 Sweep `DIVERGENT=2 SUPPORTED=192`, the two divergences still the expected
`swap_t3`/`dskf_t3` pair, no `UNREADABLE`.
🌾 **BREADTH BATCH 5 (D-KWBREADTH, 2026-09-14) — THE CONSTANT-MARKER SHAPE, AND A
THIRD DIVERGENCE THAT WAS NOT A DEFECT.** Screening every row (not just
single-row keywords) found **twenty that print only a CONSTANT MARKER**: they
score that the word RAN and nothing about what it DID. Some are legitimate — for
`IF`/`THEN`/`ELSE` the marker's IDENTITY is which branch was taken — but where the
effect is separately readable, the marker is the whole of the evidence.
| row | reading | the effect its marker could not see |
|---|---|---|
| `clear_b` | `[ 1 ]` | `CLEAR` really RESETS variables — `A=5:CLEAR:A=A+1` reads 1, where a CLEAR that did nothing leaves 6. `clearkw` prints `[5]` |
| `locate_b` | `[N 5 ]` | the **ROW** argument, read back through `CSRLIN`. `locate` sets only a COLUMN and scores the marker's INDENTATION |
🔪 Both **knife-proven LOAD-BEARING**. Sweep back to `DIVERGENT=2 SUPPORTED=194`.
🔴 **AND `locate_b` WALKED INTO A WARNING SITTING TWO ROWS AWAY FROM IT.** Written
plainly it came back **DIVERGENT — and the VALUES AGREED**: ref `|||[ 5 ]` vs zb
`||||[ 5 ]`, three wrap pipes against four. `LOCATE` MOVES THE CURSOR, so the blank
lines ahead of the output depend on ambient screen state and **the row was
measuring SCREEN GEOMETRY rather than the keyword.** The `csrlin` row below it
already carries both the diagnosis (*"the VALUE is ambient scroll state"*) and the
remedy (*"Anchored with CLS all three agree everywhere"*). 🎯 **A THIRD DIVERGENCE
IS A NEW FINDING — AND THE FINDING WAS ABOUT MY ROW, NOT THE INTERPRETER.
INVESTIGATE BEFORE FILING, ALWAYS: the values matching while the verdict says
DIVERGENT is the signature of an APPARATUS difference.**
⚠️ **AND THE `CLS` THEN COST THE ECHO — THE NEXT TRAP IN THE SAME CORNER.**
Anchored but untagged, the row read `UNREADABLE ?noecho` on BOTH sides, because
`CLS` erases the echoed command the capture keys on. `NOECHO:` exists for exactly
that; the row is now captured by its own marker `[N` (the free one — `C D G L O Q
R S T W Z` were taken). **Two fixes, each of which created the next problem, and
both were already documented in this file by somebody who had met them.**
🌾 **BREADTH BATCH 6 (D-KWBREADTH, 2026-09-14) — ONE READBACK PATH TURNED TWO
CONSTANT MARKERS INTO VALUES.** `sound` writes PSG register 7 and prints `[7]`;
`outkw` writes the PSG ADDRESS LATCH and prints `[8]`. Neither observes what
landed — and I had written the PSG off as having no readback. **It has one:
`OUT &HA0,<reg>` selects a register and `INP(&HA2)` reads it**, so both effects
are observable and one mechanism served both rows.
| row | reading | the effect its marker could not see |
|---|---|---|
| `sound_b` | `[ 123 ]` | the byte `SOUND` actually DELIVERED, read back out of the PSG |
| `out_b` | `[ 77 ]` | the whole `OUT` → `INP` round trip through the DATA port; `outkw` writes only the ADDRESS latch and never reads it back |
🔪 **Both knife-proven LOAD-BEARING.** Sweep `DIVERGENT=2 SUPPORTED=196`.
⚠️ Register 0 (channel A fine tune) is used rather than 7 because it is a plain
8-bit cell **and because the MIXER is left exactly as it was — nothing is made
audible, and nothing is left changed for the rows that follow** (the `AUTO`
lesson: a row that mutates machine state is a row that can poison its neighbours).
🌾 **BREADTH BATCH 7 (D-KWBREADTH, 2026-09-14) — `BEEP` IS OBSERVABLE TOO, AND
THE CONSTANT-MARKER SCREEN IS NOW COMPLETE.** `beep_b` reads `[ 184 ]`,
**knife-proven LOAD-BEARING**; sweep `DIVERGENT=2 SUPPORTED=197`.
| case (`scratchpad/beepobs_probe.py`, all three machines) | PSG reg 7 |
|---|---|
| at rest — no `SOUND`, no `BEEP` | **184** |
| `SOUND 7,255`, no `BEEP` | **191** (`$BF`, the write masked) |
| `SOUND 7,255` **then** `BEEP` | **184** — BEEP put the mixer back |
🔴 **AND THE FIRST RUN OF THAT PROBE COULD NOT SEE IT: ITS CONTROL READ REGISTER 8
WHILE THE CHANGE WAS IN REGISTER 7.** `184` would have been read as *"nothing
happened"*, and the only thing separating that from the truth was a no-BEEP
reading OF THE SAME CELL. **A CONTROL AIMED AT THE WRONG CELL EXCLUDES NOTHING** —
the `a-case-that-agrees-can-agree-for-the-wrong-reason` rule, applied to the
CONTROL rather than to the case.
📋 **THE CONSTANT-MARKER CLASSIFICATION, FINISHED — so the next author does not
re-derive it.** Four rows gained an EFFECT reading (`clearkw`→`clear_b`,
`locate`→`locate_b`, `sound`→`sound_b`, `outkw`→`out_b`, plus `beep`→`beep_b`);
the rest are blocked, **and every reason was already written in this file**:
| row | why the marker is the honest limit |
|---|---|
| `renum` | its own note: *"RENUM stops the program, so nothing after it runs in the same case"* |
| `waitkw` | its own note: the first attempt BLOCKED FOR EVER BY DEFINITION (mask 0 can never satisfy `((INP(port) XOR xor) AND mask) <> 0`), and zerobas's silence was CORRECT. The one satisfiable port (VDP status bit 7) is READ-TO-CLEAR and would disturb the BIOS interrupt handler |
| `newkw` `deletekw` | program mutators; `DELETE` was MEASURED to terminate the program silently |
| `listkw` | `LIST` prints the PROGRAM while the row's own typed source is already on screen — ambiguous BY CONSTRUCTION |
| `stopkw` `files` `merge` `csave` | the marker sits before a halt or an I/O side effect with no readback in this harness |
🎯 **THIRTEEN BREADTH ROWS ACROSS SEVEN BATCHES, AND THE SCREEN THAT FOUND THEM IS
THE DELIVERABLE**: a row scoring an **ERROR** leaves the SUCCESS path untouched; a
row scoring a **LENGTH or EXISTENCE** leaves the CONTENT untouched; a row scoring a
**CONSTANT MARKER** leaves the EFFECT untouched. ⚠️ **And every screen over-flags,
so each candidate is confirmed by READING its row** — a `LEN(` regex nominated
`inkey`, whose row prints `A$` as well.
🌾 **BREADTH BATCH 8 (D-KWBREADTH, 2026-09-14) — THE FOURTH SCREENING AXIS: A
BOOLEAN READING SCORES A HALF-PLANE, NEVER THE VALUE.** Six rows read `>0`,
`>1000`, `<1` or `>=`, and `VDP(1)>0` is `-1` for ANY non-zero register read — the
note beside it already said the number is **240**, so the value was known and
simply not scored.
| row | reading | what the half-plane hid |
|---|---|---|
| `vdp_b` | `[ 240 ]` | the register's VALUE; `>0` passes on any wrong non-zero read |
| `varptr_b` | `[ 8 ]` | the array element STRIDE (MSX defaults to DOUBLE) |
| `fre_b` | `[ 99 ]` | what `DIM Z(9)` COSTS |
| `rnd_b` | `[ 438 ]` | the PRNG **SEQUENCE** |
🎯 **AND `rnd_b` ANSWERS THE QUESTION THE `rnd` ROW EXPLICITLY DECLINES.** That
note says whether zerobas's PRNG sequence matches the reference's is *"a separate
question this row does not ask"*. **It is now measured: `RND(negative)` reseeds
deterministically, and `INT(RND(-1)*10000)` is 438 on the VG-8020, the CF-3300 AND
zerobas** — the generator itself agrees, not merely its range.
⚠️ `VARPTR`, `FRE` and `RND`'s ABSOLUTE values are machine-dependent (RAM layouts
differ; the CF-3300's disk ROM steals RAM the diskless VG-8020 keeps), so each row
reads a **DELTA** and all four were measured in `scratchpad/boolaxis_probe.py`
BEFORE any row was written. `VARPTR` and `FRE` are knife-proven LOAD-BEARING;
**`RND` is among the 18 the knife refuses**, so its connectedness is unmeasurable.
Sweep `DIVERGENT=2 SUPPORTED=201`.
🔴 **AND `varptr_b` SHIPPED A FALSE JUSTIFICATION FOR ONE SWEEP, CAUGHT ONLY BY
READING THE VALUE.** It read `[-3 ]`, not `[ 8 ]` — **and was scored SUPPORTED,
because both machines agreed on −3.** The cause was MY OWN line-length split: MSX
stores SIMPLE variables BEFORE arrays, so creating `B` after taking
`A=VARPTR(Z(1))` **MOVED THE ARRAY between the two reads.** The 34-char body limit
forced the split, and the split changed the thing being measured
[[apparatus-is-part-of-the-measurement]]. `A=0:B=0` up front pins the array.
**A row can agree across machines, pass its gate, and still contradict the note
that justifies it — which is why the standing rule is READ WHAT THE ROW SAW, NOT
THE VERDICT IT PRINTED.**
🌾 **BREADTH BATCH 9 (D-KWBREADTH, 2026-09-14) — THE FIFTH AXIS: A ROW THAT
EXERCISES ONE ARGUMENT COUNT OF A VERB THAT TAKES SEVERAL.**
| row | reading | the form the old row could not reach |
|---|---|---|
| `instr_b` | `[ 3 ]` | the 3-argument START form. `instr` uses TWO args, and the only 3-arg coverage is `instr_t3`, which passes an **INVALID** start of 0 — so a start that is parsed and then DISCARDED finds the first `A` and reads 1 |
| `linekw_b` | `[P 15 ]` | the `,B` **BOX** form. (9,1) is the rectangle's TOP-RIGHT CORNER and **not** a point on the diagonal a `,B`-ignoring `LINE` would draw between the same two endpoints, so a discarded `,B` reads 4 |
🔪 Both **knife-proven LOAD-BEARING**. Sweep `DIVERGENT=2 SUPPORTED=203`.
🎯 **NINETEEN BREADTH ROWS ACROSS NINE BATCHES, AND THE FIVE SCREENING AXES ARE
THE DURABLE PART** — each names a SHAPE of row whose reading cannot see a whole
class of defect: an **ERROR** reading leaves the SUCCESS path untouched; a
**LENGTH or EXISTENCE** reading leaves the CONTENT untouched; a **CONSTANT
MARKER** leaves the EFFECT untouched; a **BOOLEAN** leaves the VALUE untouched;
and **ONE ARGUMENT COUNT** leaves every other form untouched. ⚠️ Every one of them
over-flags, so a candidate is confirmed by READING its row, never by the filter.
🌾 **BREADTH BATCH 10 (D-KWBREADTH, 2026-09-14) — AXIS (e) ON THE GRAPHICS
VERBS.** Both **knife-proven LOAD-BEARING**; sweep `DIVERGENT=2 SUPPORTED=205`.
| row | reading | the form the old row could not reach |
|---|---|---|
| `drawkw_b` | `[E 15 ]` | a DIFFERENT direction command. `drawkw` drives only `R`, which a `DRAW` implementing just that one — or ignoring the letter and moving right — passes. `D` draws DOWN, so the pixel read is BELOW the start |
| `circlekw_b` | `[F 15  4 ]` | the START/END **ARC** arguments. `circlekw` draws a FULL circle |
🎯 **AND `circlekw_b` READS TWO PIXELS ON PURPOSE, WHICH IS WHAT MAKES IT
DISCRIMINATING.** A full circle gives `15 15`, a correct arc `15 4`, an absent
`CIRCLE` `4 4`. **Reading only the OFF-arc pixel would have been blank on both
sides — mode 2 — because a `CIRCLE` that drew nothing leaves it blank too.** The
on-arc pixel is what separates "the arc arguments were honoured" from "nothing was
drawn at all", and without it the row would have agreed for the wrong reason.
🌾 **BREADTH BATCH 11 (D-KWBREADTH, 2026-09-14) — `psetkw_b` reads `[H 7 ]`,
knife-proven LOAD-BEARING; sweep `DIVERGENT=2 SUPPORTED=206`.** The `psetkw` row
draws in colour **15, the default foreground**, which is also exactly what a `PSET`
that PARSED AND DISCARDED its colour argument would leave. 7 is neither the
foreground nor the blank 4, so the row reads the COLOUR ARGUMENT rather than
"something was drawn".
🔭 **AND A NAMED GAP FOR THE NEXT SLICE, WITH THE REASON IT IS NOT A QUICK ROW:
`ON` HAS THREE FORMS AND ONLY `ON ERROR GOTO` IS COVERED.** There is no
`ON n GOTO` and no `ON n GOSUB` row anywhere in the sweep — the INDEX-SELECTED
jump, which is the form a 1985 listing actually uses, is unexercised. Writing it
needs SEPARATE numbered lines as jump targets, and **`as_stored` packs statements
GREEDILY into ≤34-char bodies**, so the targets merge into one line unless the
statement lengths are chosen to prevent it. `runkw` is the precedent and its note
says so out loud — *"`RUN 20` NAMES A LINE `as_stored` CHOSE … the packing was
printed before the row was written"*. **A deliberate packing, not a quick row.**
✅ **BREADTH BATCH 12 (D-KWBREADTH, 2026-09-14) — THE `ON` GAP IS CLOSED.**
`ongoto` reads `[J99]`, **knife-proven LOAD-BEARING**; sweep
`DIVERGENT=2 SUPPORTED=207`. The packing was PRINTED BEFORE THE ROW WAS WRITTEN,
as `runkw`'s note prescribes:
```
10 ON 2 GOTO 20,30:PRINT"[J00]":END
20 REM ZQ:PRINT"[J77]":END
30 PRINT"[J99]":END
```
🎯 **THREE DISTINCT READINGS, WHICH IS WHAT MAKES IT DISCRIMINATING**: `[J99]` if
the INDEX is honoured, `[J77]` if the `ON` jumps to the FIRST target whatever the
index, `[J00]` if it never jumps at all. A two-way reading could not have
separated "wrong target" from "no jump".
⚠️ **The `REM ZQ` is LOAD-BEARING PACKING, not decoration** — without it the two
handlers merge into one body and line 30 does not exist. And the targets read
`20,30` rather than `30,40` **because that substitution preserves every statement
LENGTH, so the packing is unchanged**; a longer target number would have re-packed
the program underneath the row.
✅ **BREADTH BATCH 13 (D-KWBREADTH, 2026-09-14) — `ON n GOSUB`, AND A KNIFE
VERDICT THAT WAS ABOUT THE PAIRING.** `ongosub` reads `[K 99 ]`; the pin now holds
**108 knifed, 105 CONNECTED, 3 not** (`CALL`, `MAX`, `PAD`). Sweep
`DIVERGENT=2 SUPPORTED=208`. The packing was **SEARCHED FOR, not guessed** — the
greedy packer merges the handlers unless the padding before each fills its body to
the 34-char limit, and **no padding below 22 characters does it**:
```
10 ON 2 GOSUB 30,40:PRINT"[K";A;"]"
20 END:REM ZZZZZZZZZZZZZZZZZZZZZZ
30 A=77:RETURN:REM QQQQQQQQQQQQQQ
40 A=99:RETURN
```
🔴 **AND `GOSUB:ongosub` CAME BACK 🔴 BLIND — WHICH WAS TRUE OF THE PAIRING, NOT OF
THE ROW.** Cutting `ON` breaks it (LOAD-BEARING); cutting `GOSUB` changes nothing,
because **`ON n GOSUB` IS DISPATCHED ENTIRELY BY `ON`'s HANDLER, WHICH CONSUMES THE
`GOSUB` TOKEN INLINE** rather than going through `stmt_table`'s GOSUB entry. That
is a fact about the interpreter, and a lesson about the instrument: **A BLIND
VERDICT CAN MEAN "YOU CUT THE WRONG KEYWORD FOR THIS ROW".**
🔴 **AND THE WRONG PAIR SILENTLY OVERWROTE A GOOD READING.** The pin is merged BY
KEYWORD, so `GOSUB:ongosub` recorded GOSUB as `connected: False, row: 'ongosub'`,
replacing the full sweep's correct `gosubkw` result — **a keyword flipped from
connected to unconnected by a run that was never about it.** Repaired by re-knifing
each keyword with its OWN row, and `kwknife.py` now **WARNS when a CLI pair names a
row whose subject (`tier_table.stmt_keyword`) is a different keyword**, verified by
running it on the pairing that caused it.
🌾 **BREADTH BATCH 14 (D-KWBREADTH, 2026-09-14) — `presetkw_b` reads `[M 9 ]`,
knife-proven LOAD-BEARING; sweep `DIVERGENT=2 SUPPORTED=209`.** `presetkw` gives
`PRESET` NO colour, so it can only see that PRESET ERASES; `PRESET(x,y),9` draws in
9, which is neither the background 4 nor the foreground 15.
🔭 **AND AXIS (f) IS LIVE, WITH FOUR KEYWORDS INVISIBLE TO BOTH INSTRUMENTS AT
ONCE: `OPEN`, `PAINT`, `PUT` and `FIELD` HAVE NO ROW AS SUBJECT ANYWHERE IN THE
SWEEP.** They appear only inside OTHER rows' setup lines — `OPEN` carries
`inputkw`, `lof` and `save` — so:
* **`kwcover` counts them EXERCISED**, because a collected suite types them;
* **the tier table credits the row's SUBJECT**, which is the other keyword;
* **the knife cannot reach them at all** — it re-runs a keyword's OWN row, and they
  have none. Confirmed: none of the four is in `scratchpad/kwknife-connected.json`.
🎯 **So they are exercised, load-bearing in practice, and unattributed by every
instrument the tree has.** That is a denominator gap, not a coverage gap, and it is
the sharpest thing axis (f) has turned up.
⚠️ **`OPEN`'s own row is NOT a quick write**: the untested forms are `FOR OUTPUT`
and `FOR APPEND`, which CREATE OR EXTEND A FILE on the shared fixture — and this
file's own rule is that **every row which READS the fixture is placed ahead of
every row that CHANGES it, so both sides walk the identical sequence**
[[apparatus-is-part-of-the-measurement]]. A write row has to be PLACED, not just
written.
✅ **BREADTH BATCH 15 (D-KWBREADTH, 2026-09-14) — TWO OF THE FOUR UNATTRIBUTED
KEYWORDS NOW HAVE ROWS THEY ARE THE SUBJECT OF.** Both **knife-proven
LOAD-BEARING**, and both now appear in the pin where neither could before; sweep
`DIVERGENT=2 SUPPORTED=211`.
| row | reading | why it is the keyword's own |
|---|---|---|
| `paintkw` | `[U 15 ]` | a box drawn with `LINE ,B` bounds the flood and (15,15) is INTERIOR — a pixel **nothing but a FILL sets**, so 15 filled against 4 blank |
| `putsprite` | `[V 50 ]` | the SCREEN 2 sprite ATTRIBUTE table at `$1B00` (6912), whose first byte is the sprite's Y — read straight back out of VRAM. `spritekw` round-trips `SPRITE$`, which is the **PATTERN** table and a different store |
🎯 **Both readings match their notes exactly** — `[V 50 ]` confirms `$1B00` really
is the attribute base and its first byte really is Y, so neither row repeats
`varptr_b`'s false justification. `OPEN` and `FIELD` remain, and both need the disk
fixture and a PLACEMENT decision rather than just a row.
✅ **BREADTH BATCH 16 (D-KWBREADTH, 2026-09-14) — `OPEN` HAS A ROW OF ITS OWN AND
IS IN THE PIN.** `openkw` is **knife-proven LOAD-BEARING**; sweep
`DIVERGENT=2 SUPPORTED=212`. Every other use of `OPEN` in this file is `FOR INPUT`
apparatus, so the `FOR OUTPUT` form was untested: create, write, close, reopen and
read `LOF`.
🔴 **PLACEMENT WAS THE HARD PART, NOT THE ROW.** It CREATES a file, and `files`
and `lfiles` LIST the directory while `dskf` reads FREE SPACE — a new file moves
all three readings. So it sits after `loc`, the LAST disk row, rather than beside
the other writers, which is the D-KWDISK rule applied rather than rediscovered.
🔴 **AND IT READ 5 WHERE MY NOTE CLAIMED 4 — `varptr_b`'s failure shape, caught
this time before the commit.** `"AB"` plus CRLF is four bytes and the file measures
**five on both machines**. The note now states 5 as MEASURED and names the likely
fifth byte (the `$1A` EOF marker Disk BASIC appends on CLOSE) **as a cause that has
NOT been read back** — because a green verdict says nothing about whether the
justification beside it is true.
🔭 **`FIELD` remains**, and needs the fixture plus the same placement care.
✅ **BREADTH BATCH 17 (D-KWBREADTH, 2026-09-14) — `FIELD` CLOSES AXIS (f). ALL
FOUR UNATTRIBUTED KEYWORDS NOW HAVE ROWS THEY ARE THE SUBJECT OF, AND ALL FOUR ARE
IN THE PIN.** `fieldkw` reads `[WXYZ]`, **knife-proven LOAD-BEARING**; pin **112
knifed, 109 CONNECTED, 3 not** (`CALL`, `MAX`, `PAD`), no junk keys; sweep
`DIVERGENT=2 SUPPORTED=213`.
The row is the RANDOM-access round trip: `OPEN … AS#1` with **no `FOR` clause**,
`FIELD` binds a buffer slice, `LSET` fills it, `PUT` writes record 1 and `GET`
reads it back. **The four verbs are load-bearing TOGETHER** — the reading fails if
any one of them does — and it is placed after `loc` and `openkw` because it CREATES
a file and `files`/`lfiles`/`dskf` must read the fixture first.
🎯 **AND THE NOTE WAS WRITTEN FROM THE MEASUREMENT, NOT BEFORE IT.** The row
shipped its first sweep with *"reading pending measurement"* in place of a number,
and `[WXYZ]` was written in only once both machines had printed it. That is the
direct answer to `openkw` claiming 4 where the file measured 5, and to `varptr_b`
claiming a stride of 8 while reading −3: **a note that predicts is a note that can
be wrong while every gate stays green.**
🌾 **BREADTH BATCH 18 (D-KWBREADTH, 2026-09-14) — AXIS (g): A READING THAT SAMPLES
ONE POINT OF A RANGE.** Measured across the whole row set rather than guessed: the
graphics rows use SCREEN 0, 1 and 2 and **never SCREEN 3**, and **every one of the
17 file rows opens channel #1** — the channel NUMBER was a constant in all of them.
| row | reading | the range it widens |
|---|---|---|
| `psetkw_c` | `[X 15 ]` | the same verb in SCREEN **3**, multicolour with its own VRAM layout, so plot and read-back both take a different address calculation. Knife-proven LOAD-BEARING |
| `openkw_b` | `[He]` | channel **#2**, needing `MAXFILES` raised. `OPEN` was already proven connected by `openkw`, so this widens the ROW SET rather than the pin |
🔴 **AND `openkw_b` COST SIX SWEEPS, EVERY ONE OF THEM MY OWN DOING.** (1) Written
with HI.TXT on both channels it went DIVERGENT — **not a new finding**: that is
`e.same2`, an already-filed TIER 5 item (same file on two channels: refused on the
CF-3300, accepted here), so the first version earns its minute only as
CORROBORATION that the filed defect is live. (2) With TEST.BIN as the second file it
read `File not found`, because it sat after `dsko` — *"rewrites the first byte of
the root directory"* — and TEST.BIN is the FIRST entry. (3) Moved among the readers
it read `[ 0 ]`, zero on both sides, which is mode 2. **🎯 THE ORDERING RULE CUTS
BOTH WAYS: a writer must go last, and a READER MUST GO BEFORE THE WRITERS OR IT
READS A FIXTURE THAT HAS MOVED** — I had filed it with the writers by reflex, though
`MAXFILES` is MACHINE state and both opens are `FOR INPUT`, so it creates nothing.
(4) 🔴 **AND THE LAST IS THE BEST: THE `MAXFILES=1` RESTORE HAD TO MOVE AFTER THE
`PRINT`.** Assigning `MAXFILES` performs an implicit CLEAR, so restoring it before
the readout WIPED `A$` and the row read `[]` — **the tidy-up that keeps the machine
as it was found destroying the measurement it was there to protect.**
🔬 Two behaviours measured along the way, identical on both machines and therefore
faithful rather than defects: with a second channel open `LOF(1)` reads 0 where
`lof` reads 26 with one, and a read from #1 while #2 is open returns nothing.
🌾 **BREADTH BATCH 19 (D-KWBREADTH, 2026-09-14) — AXIS (g) CONTINUED, AND THE
RANGES WERE MEASURED, NOT GUESSED.** Counting across the whole file: **every
`SPRITE$` and `PUT SPRITE` uses SPRITE 0**, and **every `ERROR` raised is 7** — two
ranges sampled at exactly one point. `spritekw_b` reads `[Y 222 ]`, **knife-proven
LOAD-BEARING**; sweep `DIVERGENT=2 SUPPORTED=216`.
🎯 **THE WRITE ORDER IS THE DISCRIMINATOR, AND GETTING IT BACKWARDS WOULD HAVE MADE
THE ROW USELESS.** Sprite 3 is written FIRST and sprite 0 SECOND, then 3 is read
back: indexed correctly that returns 3's own byte (222); if the index were
discarded both writes would land in one place and the read would return 0's (111).
**Writing 0 first would have made both answers identical** — the row would have
agreed whether or not the pattern-table index worked at all.
🔭 **`ERROR` is the remaining one-point range**: six rows raise code 7 and nothing
raises any other, so every error code's own path is unexercised. Its rows use the
`ON ERROR GOTO` + line-number shape, so a second code needs the packing printed
first, as `ongoto` and `ongosub` did.
✅ **BREADTH BATCH 20 (D-KWBREADTH, 2026-09-14) — THE `ERROR` CODE RANGE IS OPEN.**
`errorkw_b` reads `[I 53  10 ]`, **knife-proven LOAD-BEARING**; sweep
`DIVERGENT=2 SUPPORTED=217`. All six existing rows raise code **7**, so an
implementation that IGNORED the operand and always raised 7 would pass every one of
them. `ERR` returns **53**, so the operand is honoured; `ERL` returns **10**, the
line that raised it.
🎯 **BOTH `ERR` AND `ERL` ARE READ ON PURPOSE**, so the row separates *"the right
error"* from *"an error at the right line"* — either alone would agree for the
wrong reason, the same design point as `circlekw_b`'s second pixel and
`spritekw_b`'s write order. The packing was PRINTED before the row was written and
matches the existing shape (line 10 raises, line 20 handles).
🎚️ **D-KWTIER1 (2026-09-14) — `PSET` IS THE FIRST KEYWORD TO REACH ANY TIER.**
Joost's rule, ruled the same day: **CONNECTED + N distinct FORMS + no open item,
with N depending on the complexity of each individual keyword.** `PSET` now reads
**TIER 1** in `make tiers` and in `docs/tier-status.md`: knife-proven CONNECTED,
4/4 authored forms, no open item — every clause derived from the tool's own data,
none asserted.
🔴 **THREE THINGS WERE MISSING AND ONLY ONE WAS THE NUMBER.**
* **`tier_table` could not COUNT.** `kwsweep_evidence` does `if kw not in out` — it
  keeps the FIRST row per keyword and discards every other one, so all 33 breadth
  rows were invisible to it beyond the first. `kwsweep_forms()` now counts distinct
  forms from SUPPORTED rows only; a DIVERGENT row exercises a form and FAILS it.
* **Rows could not SAY which form they exercise.** A new `FORM:<name>` tag, parsed
  over the WHOLE note and deliberately NOT through `_row_prefix_tags` — `NOECHO:`
  is matched with `startswith` and must be a note's first token, so widening the
  prefix run would have changed where `PROVES-T3:` is seen on every row that has
  both.
* **N had to be AUTHORED, not derived.** `tools/kwforms.py` holds it as data with
  its reason. Deriving N by counting our own handler's argument branches would be
  **CIRCULAR** — a keyword we implemented too simply would get a lower bar and pass
  more easily, grading the test against the thing under test. A keyword with no
  entry is **UNRATED, never satisfied**: absence of a bar is not a bar of zero.
🎯 **AND THE FORM TAG IMMEDIATELY EARNED ITSELF: `psetkw` AND `psetkw_b` ARE THE
SAME FORM.** Both drive `PSET(x,y),c` and differ only in WHICH colour, so counting
ROWS would have called PSET two-thirds done on one form. PSET's four are
`colour-explicit`, `colour-default` (`[A 11 ]` — the CURRENT foreground, so a
hard-coded 15 fails), `step-relative` (`[B 15 ]` — five right of the last point, so
an absolute reading leaves the pixel blank) and `mode-screen3`.
🔴 **TWO BUGS FOUND BY CROSS-CHECKING RATHER THAN BY THE GATES.** (1) `psetkw_c`'s
crunch body was `'screen 3'`, so **`stmt_keyword` credited the row to SCREEN** — a
row named `psetkw_c`, testing PSET, scored for a different keyword and vanished
when PSET's forms were counted. **The CRUNCH BODY decides the subject, not the row
key.** (2) The open-item clause: `keyword_tiers`' entry is a TUPLE
`(tier, lines, evidence)`, and `(None, [], 'SUPPORTED')` is **TRUTHY** — testing
`bool(entry)` marked every keyword as carrying an open item and reported PSET
blocked by one it does not have. Only comparing against `PAINT`, which really does
carry a TIER 4 item, exposed it. Both are now selftests (S26–S28).
🎚️ **AND `CLEAR` IS THE SECOND, AT 3/3 FORMS** — `bare`, `string-space`, `himem`.
Its N is **3 where PSET's is 4**, which is the rule working as ruled: `CLEAR` has no
coordinate or mode dimension, so its whole surface is
`CLEAR [<string space>[,<himem>]]`. Both new rows are knife-proven LOAD-BEARING;
sweep `DIVERGENT=2 SUPPORTED=220`.
🔬 **`clear_c` WAS MEASURED IN ISOLATION FIRST** (`scratchpad/clearhimem_probe.py`),
because it carries TWO hazards at once: it lowers a GLOBAL ceiling, so every later
row would run with less memory unless the original is restored (the `AUTO` hazard),
and **`CLEAR` WIPES VARIABLES, so the original cannot be held in one** (the
`MAXFILES` trap). The original is parked in RAM at `$E003/$E004` — **above the
lowered ceiling, where BASIC will not touch it** — and the restore runs AFTER the
readout.
🎯 **AND THE ROW READS THE *SET* CEILING, NOT THE RESTING ONE.** At rest `HIMEM` is
**62336** on the VG-8020 and here but **56951** on the CF-3300, whose disk ROM
steals RAM — so a row reading the resting value would have DIVERGED for a reason
that is not a defect. `53248` (`$D000`) is what all three read once it is SET.
⚠️ The restore is `CLEAR 100,B` and not the 39-character expression: **a single
statement over 34 chars fits NEITHER mode**, and the split form was MEASURED to
still see `B` — the argument is evaluated before the clear takes effect.
🎚️ **AND `PRESET` IS THE THIRD, AT 4/4** — `colour-default`, `colour-explicit`,
`step-relative`, `mode-screen3`. Its syntax mirrors PSET's, so its N mirrors it
too, which is the first evidence the rule TRANSFERS rather than having been fitted
to the keyword it was built on. Both new rows knife-proven LOAD-BEARING; sweep
`DIVERGENT=2 SUPPORTED=222`.
🎯 **BOTH READ TWO PIXELS, ONE THE VERB MUST CHANGE AND ONE IT MUST LEAVE** —
`[1 4  15 ]` and `[2 4  15 ]`. A lone `4` cannot tell *"PRESET erased it"* from
*"PSET never drew it"*, and the erase verbs are exactly where that confusion is
free to happen.
⚠️ **DIGIT MARKERS, BECAUSE EVERY SINGLE-LETTER `NOECHO` MARKER A–Z IS TAKEN** —
and a letter marker would be a PREFIX of any two-letter one, since `marker_tail`
matches by SUBSTRING: `[A` would happily find a row printing `[AA`. `[1` and `[2`
cannot collide with the `[T1]`/`[R1]`/`[C1]` style already in use, because those
put a letter after the bracket.
🎚️ **AND `COLOR` IS THE FOURTH, AT 3/3 — AND IT IS THE ONE THAT TESTS TRANSFER,
BECAUSE ITS SHAPE IS NOT PSET'S.** `COLOR [fg][,bg][,border]` is three POSITIONS,
so the form that matters is the **OMISSION**: a parser that shifted `COLOR ,5` left
would write the background value into the foreground. `colorkw_b` reads `[3 5  7 ]`
and `colorkw_c` `[4 3  7 ]` — the changed cell, **and FORCLR still 7**, so the
omitted position was SKIPPED and not shifted. Both knife-proven LOAD-BEARING;
sweep `DIVERGENT=2 SUPPORTED=224`.
📊 **FOUR KEYWORDS AT TIER 1, AND THE N VALUES ARE DOING REAL WORK IN BOTH
DIRECTIONS**: `PSET` and `PRESET` at 4 (an optional trailing argument, a STEP
coordinate and a screen mode), `CLEAR` and `COLOR` at 3 (no coordinate and no mode;
`COLOR`'s three are positional). A fixed N would have been wrong for two of the
four — which is the ruling itself, demonstrated rather than argued.
🔴 **RETRACTED THE SAME MORNING — `ON` WAS AWARDED TIER 1 AND THE AWARD WAS NOT
SUPPORTED (D-KWCOMPOSITE, Joost 2026-09-14: *"one could consider the ON + second
keyword one composite keyword requiring its own tests"*).** `ON ERROR GOTO`,
`ON n GOTO`, `ON n GOSUB`, `ON KEY GOSUB`, `ON STOP GOSUB`, `ON INTERVAL=n GOSUB`,
`ON SPRITE GOSUB` and `ON STRIG GOSUB` are **STATEMENTS IN THEIR OWN RIGHT**, not
forms of one keyword — the traps have their own handlers (`ex_on_key`,
`ex_on_interval`, `ex_on_strig`, `eos_common`, `basic/interp.asm:284`). **Three
rows spoke for three of EIGHT composites and the table called it 3/3.**
🎯 **THE ERROR NAMED: I COUNTED THE KEYWORD THAT *BEGINS* THE STATEMENT, NOT THE
STATEMENT.** `stmt_keyword` returns the FIRST keyword token, which is the wrong
granularity here — and it is not only `ON`: **`LINE INPUT` and `LINE (x,y)-(x,y)`
share a token and are entirely different statements, so a GRAPHICS row would have
vouched for CONSOLE INPUT.** Thirteen composites are implemented in this tree
(`LINE INPUT` 35 mentions in `basic/`, `DEF FN` 79, `PRINT USING` 75, `PUT #` 44,
`PRINT #` 40, `DEF USR` 19, `PUT SPRITE` 16, the five ON-traps 4–12 each), and the
old model collapsed them into six parents. ⚠️ **`ON` REACHING TIER 1 "FOR FREE" WAS
A SYMPTOM, NOT A BONUS — THE CHEAPNESS SHOULD HAVE BEEN THE TELL.**
✅ **WITHDRAWN AND SPLIT.** The `ON` entry is gone from `tools/kwforms.py`, so it is
UNRATED again; `stmt_subject()` matches an AUTHORED composite list MOST SPECIFIC
FIRST (`ON ERROR GOTO` wins over `ON GOTO`, which never matches an `ON ERROR GOTO`
body) over EVERY keyword in the body, since `ON 2 GOTO 20,30` has an expression
between its two keywords. ON's three rows now attribute to **three different
statements**, each holding ONE form and each correctly UNRATED. **Four keywords
remain at TIER 1: `CLEAR`, `COLOR`, `PRESET`, `PSET`** — none of them composite,
none affected.
🔭 **AND A LIMIT MEASURED RATHER THAN CLAIMED: A COMPOSITE CANNOT YET BE AWARDED AT
ALL.** `tier1_keywords()` iterates the 159-keyword table, and no composite is in
it, so an authored form list for `ON GOTO` would still award nothing. Widening that
set is the next slice and it touches the DENOMINATOR — including S20, *"the full
list names every keyword exactly once"*. ⚠️ **DO NOT WEAKEN A SELFTEST TO MAKE A
COUNT COME OUT.**
✅ **ANSWERED (Joost, 2026-09-14): *"yes, bare print and print # and print using
have a different function"* — A PARENT TIERS INDEPENDENTLY OF ITS COMPOSITES.**
Bare `PRINT`, `PRINT #` and `PRINT USING` are three subjects with three form lists
and three N values. Still open and NOT answered by this: `USING` is UNCONNECTABLE
BY CONSTRUCTION (token `$E4` is not in `stmt_table`), yet `PRINT USING` is a unit
in its own right — so the connectedness clause must be satisfied by the
COMPOSITE's own cut, not the second word's, and no such cut exists yet.
🔬 **D-KWSUBJECT — A ROW NOW DECLARES THE STATEMENT IT IS ABOUT, BECAUSE
DERIVATION IS WRONG ON REAL ROWS (2026-09-14).** Three shapes defeat it, all
measured, none hypothetical: `using`'s crunch body is `using "##"` and **NEVER
MENTIONS PRINT**, so it scored for `USING`, a token that is not in `stmt_table` and
can never be cut; `inputkw`'s subject is `INPUT #1` but **`#` is punctuation and
invisible to keyword matching**, so it is indistinguishable from bare `INPUT`; and
the exec line cannot stand in for the body because it is apparatus-dominated
(`inputkw`'s opens a file, reads it, closes it and prints a length).
✅ **THE TAG.** `SUBJECT:PRINT_USING` in a row's note (`_` becomes a space, since a
note token cannot hold one), parsed exactly like `FORM:` — whole note, never the
prefix run, no effect on rig or flag parsing. Stored in the pin; `stmt_subject()`
prefers it over the derived value. **Five rows carry one**: `using`/`using_b` →
`PRINT USING`, `inputkw`/`input_b` → `INPUT #`, `getkw` → `GET #`.
🔴 **AND A DECLARED SUBJECT IS VALIDATED, NOT TRUSTED.** `known_subject()` accepts
only a keyword in the table or an authored statement name; anything else is
REFUSED OUT LOUD and the derived subject used instead. A typo would otherwise move
a row off its keyword and into a bucket nothing ever counts — silently, which is
the `kwcover` lesson applied to a tag. Selftests **S29** (a declared subject wins)
and **S30** (an unscoreable one is refused, not adopted).
📉 **THE HONEST CONSEQUENCE: FIVE KEYWORDS LOST EVIDENCE THEY NEVER HAD.** With
`kwsweep_evidence` keyed by SUBJECT, `GET`, `INPUT`, `ON`, `PUT` and `USING` no
longer show a row of their own — the rows did not vanish, they moved to the
statement they actually drive. **The table now reads worse and that is the point.**
🎯 **AND SEPARATING THE FOUR FALSE HOLES FROM THE ONE REAL ONE IS WHAT THE
DISTINCTION IS FOR.** MSX1 has **no bare `ON`, `DEF`, `GET`, `PUT` or `USING`
statement** — each exists only inside a composite, so "no row of its own" is the
truth about the language (`kwforms.NO_BARE_FORM`, rendered as its own bucket).
🔭 **`INPUT` IS DELIBERATELY NOT IN THAT SET, AND IT IS THE FINDING: BARE CONSOLE
`INPUT "x";A$` IS A REAL STATEMENT THIS TREE IMPLEMENTS AND HAS NEVER HAD A KWSWEEP
ROW.** Both of its rows drive the FILE form. Without the bare/composite
distinction this hole reads identically to the four that are not holes, which is
exactly how it stayed invisible. ⚠️ `input-acceptance` does exercise console INPUT
— the claim is scoped to the kwsweep denominator, not to the battery.
🚧 **D-TIERDOC — `docs/tier-status.md` IS GENERATED AND NOTHING NOTICED WHEN IT
DRIFTED (Joost, 2026-09-14: *"maybe generate the updated tier markdown after each
iteration before you run the suite?"*).** 128 green gates said nothing while the
doc's own header advertised `make tiers ARGS=--markdown` — a command that prints to
stdout and therefore writes nothing at all. Same class as a fix that falsifies the
paragraph beside it: **no gate reads prose.**
✅ **`make tiers-md-check`** regenerates to `build/tier-status.check.md` and diffs.
🔴 **AND THE PLACEMENT WAS WRONG TWICE BEFORE IT WAS RIGHT — THE INSTRUMENT
CAUGHT ITS OWN AUTHOR.** The first version put the check in `run_gates.MUTATORS`,
reasoning that it READS `build/kwsweep-verdicts.json` while the pool's own
`kwsweep` REWRITES it, so it had to run before the pool — the D-SELFMUT race,
applied by analogy. **It went RED on every run**, and the diff blamed the doc:
139 keywords with no row, the four TIER 1 awards silently gone.
🎯 **THE PIN WAS NOT STALE, IT WAS ABSENT — `run_gates.main()` OPENS WITH
`rm -rf {OUT} build`.** There is no "before the pool" in which that pin exists at
all; the pool's own `kwsweep` is what creates it. ✅ **`POSTCHECKS`, a new serial
phase AFTER the pool**, which is the STRONGER invariant anyway: the committed doc
is compared against the pin THIS battery just measured, not against whatever was
on disk when it started.
🔬 **AND THE REAL DEFECT WAS NOT THE PLACEMENT — IT WAS THAT THE GENERATOR
ANSWERED FROM A MISSING INPUT.** `tier_table.py --markdown` read an absent pin,
every `kwsweep_*` reader swallowed the `OSError` and returned `{}`, and it emitted
a confident, complete, WRONG document. ✅ **`pin_rows()` + a REFUSAL**: `--markdown`
now exits 2 naming the path and what it found, unless `--allow-no-pin` is passed.
**The refusal is what named the cause** — the MUTATORS diff alone said only "the
doc differs", and I would have gone on suspecting `selftest-check`, which I had
already measured innocent twice. [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]
📉 **TWO MORE OF THE SAME SHAPE, IN THE GATE RUNNER, BOTH FOUND BY READING A
SUMMARY LINE THAT COULD NOT BE TRUE.** `GATES: 41/40 green` — a post-pool unit
counted in the numerator and missing from the denominator (`GATES` is what the
POOL runs; the denominator now adds `POSTCHECKS` separately). And
`wall 0s (7s build + -7s gates)` — my new phase reused the name `t0`, which holds
the battery's START. ⚠️ **BOTH PRINTED UNDER AN ALL-GREEN RUN.**
🔴 **`battery-membership-check` THEN CALLED THE NEW GATE A SUITE NOBODY RUNS** —
correctly, by its own rule: it parses the `STATIC`/`EMULATOR` triple-quoted blobs
and `POSTCHECKS` is a list literal. Widened to parse it, with `MUTATORS`
deliberately left out (every name in it is already in `STATIC`, so it is a
scheduling hint, not a membership list). Its six selftests GREEN.
🔴 **IT PROVES THE DOC MATCHES THE GENERATOR, NOT THAT THE PIN IS CURRENT.** A doc
built from a month-old pin passes. Making the pin current is the WORKFLOW step —
**`make kwsweep && make tiers-md` BEFORE staging, never after a battery** — and
that is deliberately not a gate, because a gate that ran `kwsweep` would spend 120 s
of every battery re-deriving what the battery already writes.
⚡ **D-KWBATCH1 — THE BATCHED FLOW, AND THREE MORE KEYWORDS AT TIER 1 FOR ONE
BATTERY INSTEAD OF THREE** (Joost, 2026-09-14: *"if possible switch to a more
efficient flow doing a few keywords together, avoiding too many lengthy test
runs"*). ⚠️ **WHY ONE-PER-KEYWORD WAS SO EXPENSIVE, AND WHY THE OBVIOUS SHORTCUT
IS WRONG:** `source_fingerprint()` hashes the WHOLE `probes/`+`tests/`+`tools/`
trees into ONE value, so any edit to `basic_probe_kwsweep.py` forbids D-GATESKIP
from skipping the emulator tier — 88 targets re-run for a change that can only
affect one. **That is deliberate (a proof, not a judgement about blast radius),
so the answer is BATCHING, never weakening the skip.**
📏 **MEASURED 2026-09-14:** full battery 920–952 s · `make kwsweep` ~120 s ·
`make gates-fast` ~63 s · `make kwsweep ONLY=a,b,c` for three rows, once. The loop
is now: several keywords in one edit pass → `ONLY=` for the new rows → one
`make kwsweep` → knife each row → citations `--fix` → `make kwsweep && make
tiers-md` → stage → **ONE** battery → **ONE** commit naming every keyword.
🟢 **`BEEP` AND `CLS` AT N=1, AND THAT IS THE HONEST BAR, NOT A LOW ONE.** Both
take NO arguments, so one form is the whole surface. What keeps the evidence from
being vacuous is not a second form but WHAT THE ROW READS: `beep_b` scores the PSG
mixer register BEEP restores (184 against 191 without it), and `clskw` reads
CSRLIN back — a bare marker would have been printed just as happily by a CLS that
parsed and did nothing.
🟢 **`WIDTH` AT N=2, WHERE THE SECOND FORM IS A DIFFERENT CELL, NOT A DIFFERENT
NUMBER.** MSX keeps the width PER MODE — `LINL40` ($F3AE) for SCREEN 0, `LINL32`
($F3AF) for SCREEN 1, both DECLARED — and `WIDTH` writes whichever belongs to the
current mode. `widthkw_b` reads `[0a 29  37 ]`: **the cell WIDTH must change AND
the one it must leave alone**, so a handler that always wrote LINL40 passes
`widthkw` and fails here. 🎯 **BOTH CELLS ARE SET BY THE ROW ITSELF**, because the
VG-8020 and this repack do not agree about which mode they boot into and a row
reading an untouched cell would be measuring the BOOT and reporting it as WIDTH.
🔭 ~~**`LOCATE` STOPS AT 3/4 AND THE MISSING FORM IS A RECORDED DEVIATION, NOT A
MISSING ROW.** `basic/missing.asm` O-3: the third argument is parsed,
domain-checked and then **IGNORED** — "nothing in this tree reads CSRSW ... storing
it would be a write nobody reads".~~
✅ **4/4 AND TIER 1 SINCE 2026-09-16 (D-LOCCSR); O-3 IS WITHDRAWN.** The struck
sentence is a claim about THIS TREE, and the question a form has to answer is what
the REFERENCE leaves readable. It writes **`CSRSW $FCA9`**. Measured on both
references against a POKEd sentinel of 99
([`scratchpad/csrsw_probe.py`](scratchpad/csrsw_probe.py)):
`LOCATE ,,0` → 0, `,,1` → 1, `,,2` → **1**; zerobas left the sentinel standing on
all three. "Nobody reads it" described a gap on OUR side — never a reason not to
write what the reference writes. **10 B**, STATEMENT 148 → 149.
🎯 **THE VALUE IS FOLDED, AND ITS NEIGHBOUR'S IS NOT.** `LOCATE ,,2` stores **1**
where `SCREEN ,,2` stores **2** (D-SCRCLICK). Two adjacent work-area switches, two
opposite rules — so `,,2` was asked BEFORE either was implemented, and an
implementation generalised from one would have passed every 0-and-1 row and been
wrong for the other.
📊 **Fourteen blockers re-verified on this project, fourteen stale.** The bar comes from the REFERENCE's syntax, so
`LOCATE [X][,Y][,switch]` is four forms whatever we chose to implement.
⚠️ **A FORM WE DECLINED LEAVES THE KEYWORD SHORT OF TIER 1, AND THAT IS THE
MEASUREMENT WORKING.** New row `locate_c` covers the third of the four: `[0b 7  9 ]`
— `LOCATE ,7` after `LOCATE 9,3` moves the ROW and LEAVES the COLUMN, which is the
`COLOR` shape again. Neither `locate` nor `locate_b` could see a left-shifting
parser, because each supplies its axis in the position the shift would read anyway.
🔭 ~~**`SCREEN` STOPS AT 2/3** — `mode` and `sprite-size` covered, `key-click` has no
cell any row here can read.~~
✅ **3/3 AND TIER 1 SINCE 2026-09-16 (D-SCRCLICK), AND THE STRUCK CLAIM IS WHY THE
RULE EXISTS.** "No cell any row here can read" was an INSTRUMENT assumption, not a
fact about the machine: **`CLIKSW $F3DB`** is a published MSX work-area cell and
BOTH references move it. Against a POKEd sentinel of 99 — which is what makes a
reading of 0 a WATCHED write rather than a cell that was always 0 —
`SCREEN ,,0` → 0, `SCREEN ,,1` → 1, `SCREEN ,,2` → **2**
([`scratchpad/clicksw_probe.py`](scratchpad/clicksw_probe.py)). zerobas left the
sentinel standing on every one: `spr_extra_arg` dispatched slot 1 and slot 3 and
let slot 2 fall through to `ret nz`. **9 B** fixes it.
🎯 **`,,2` WAS ASKED BEFORE ANY CODE WAS WRITTEN AND IT CHANGED THE CODE.** Both
references store the byte **RAW** — no fold to 0/1 — so an `and 1` would have
looked right on the first two values and been wrong on the first one anyone
varies. Row `screenkw_d` carries all three for that reason.
📊 **Thirteen blockers re-verified on this project, thirteen stale.** New row `screenkw_c` reads RG1SAV ($F3E0, DECLARED),
whose bits 1..0 ARE the sprite size: `[0c 227  224 ]`, differing by exactly 3 and
identical in every other bit. 🔴 **AND THE HISTORY SAYS WHY IT WAS WORTH A ROW:**
`SCREEN 1,,99` once applied **99 as the sprite size** (`basic/screen.asm:121`) and
NO row could see it — the old `and $03` turned it into size 3, and a wrong sprite
size does not show up in `SCRMOD`, the only cell `screenkw` reads.
🔪 **ALL THREE NEW ROWS KNIFE-PROVEN LOAD-BEARING** (`widthkw_b` → MISSING,
`locate_c` → UNREADABLE, `screenkw_c` → MISSING with the handler cut).
⚠️ **AND THE COST OF BATCHING, STATED BECAUSE IT IS THE REAL ONE:** reviewing
several keywords' rows at once is exactly where I have mis-read before (`varptr_b`
scored SUPPORTED on `[-3 ]` while its note claimed 8; `openkw_b` took six sweeps).
Each reading above was read ON ITS OWN, never off the batch's summary line.
🟢 **THE PROBE REFUSED ONCE, CORRECTLY, AND SAVED A SWEEP:** `locate_c` was written
`direct` at 61 chars and the sweep answered *"probe defect — direct-mode exec lines
exceed one screen row (38 cols)"* and measured NOTHING rather than scoring a
wrapped echo.
⚡ **D-KWBATCH2 — SIX MORE KEYWORDS FOR TWO NEW ROWS, WHICH IS WHAT THE BATCHED
FLOW IS FOR.** `POKE`, `VPOKE`, `OUT`, `SOUND`, `VDP` and `TIME` all reach TIER 1;
the first four needed only their form lists authored and their existing rows
tagged, because the evidence was already there and nothing had ever counted it.
🎚️ **FOUR OF THEM ARE N=1, AND THE DOCTRINE IS WHAT KEEPS THAT HONEST.** `POKE
a,v`, `VPOKE a,v`, `OUT p,v` and `SOUND r,v` each take two REQUIRED arguments with
no optional part, no mode and no coordinate — one behaviour, so one form. What
makes N=1 a bar rather than a formality is WHAT THE ROW READS: every one of them
reads the written byte back (PEEK, VPEEK, the PSG's own readback port), so a verb
that parsed and wrote nothing fails.
⚠️ **AND `vpoke_b` / `vpoke_b2` ARE TAGGED WITH THE *SAME* FORM NAME ON PURPOSE.**
The last byte of VRAM and the maximum byte value are SAMPLES of one behaviour.
Tagging them separately would have let three readings of one form satisfy an N of
three — which is exactly the mistake `FORM:` was introduced to stop, committed
against the very rows that motivated it.
🟢 **`VDP` AND `TIME` AT N=2, AND THE SECOND FORM IS A DIFFERENT HANDLER.**
`VDP(n)` is both an expression and an assignment TARGET (`ex_vdp_assign`,
`basic/interp.asm`), and `TIME` has a read selector (`$CB`) and a separate
`ex_time_assign` (`basic/time.asm`). **Every existing row read.** New rows
`vdp_c` → `[0d 5  4 ]` and `time_c` → `[0e 300  100 ]`, both writing TWO DIFFERENT
values so a handler that stored a constant, or ignored the assignment and left the
old value, is visible on the second reading. Both knife-proven LOAD-BEARING.
🔴 **WHAT `vdp_c` CANNOT PROVE, SAID IN THE ROW RATHER THAN LEFT TO BE ASSUMED
AWAY: MSX VDP REGISTERS ARE WRITE-ONLY AT THE CHIP.** Every reader sees the RGnSAV
mirror, so no row anywhere can witness what the VDP got. The bar is the two ACCESS
PATHS, and the row scores the assignment path — parse, evaluate, store the value
written.
🎯 **AND `timetick` IS A BOOLEAN BECAUSE IT HAS TO BE — THE SPEED ITEM REACHES
INTO THE TIER BAR.** `TIME>T` across a delay loop is all a read row can ask:
zerobas is 2.5–3.8× slower than the reference (the open TIER 4 item), so a delay
loop's TIME **value** would diverge on INTERPRETER SPEED and be reported as a TIME
defect. `time_c` is where TIME's value gets scored, because writing a known value
and reading it back has no speed dependence. ⚠️ `INT(TIME/100)` and not `TIME`:
the clock ticks between the write and the read, so the raw value is not
reproducible; divided by 100 both readings sit exactly on a multiple and are
stable for ~100 ticks.
📊 **THIRTEEN KEYWORDS AT TIER 1** — `BEEP CLEAR CLS COLOR OUT POKE PRESET PSET
SOUND TIME VDP VPOKE WIDTH`. Two batteries got the last nine of them; one battery
each would have cost seven more.
⚡ **D-KWBATCH3 — FIVE MORE, AND JOOST'S SUGGESTION CLOSES THE LIMIT `vdp_c`
STATED.** `INP`, `TRON`, `TROFF`, `CIRCLE` and a strengthened `VDP` — **seventeen
keywords at TIER 1**.
🔴 **JOOST, 2026-09-14: *"if you choose a clever write, you can see the effects in
the visual appearance of the screen"*.** He is right that the effect is reachable,
and `vdp_c`'s stated limit — *no reader can see the chip* — was too pessimistic.
⚠️ **IT IS NOT REACHABLE THROUGH THIS CAPTURE, THOUGH, AND THAT IS WORTH WRITING
DOWN: `omsx_repl` SCRAPES VRAM `$0000` DIRECTLY**, so it reads the NAME TABLE and
not the display. A blanked screen, a changed backdrop and even a moved name-table
base all look identical to it. So the witness has to be something a **PROGRAM** can
measure.
🟢 **VDP REGISTER 1 BIT 5 IS THE FRAME-INTERRUPT ENABLE.** Clear it and the
50/60 Hz interrupt stops, so JIFFY stops and **TIME FREEZES** — and nothing but the
real chip can produce that. `vdp_d` reads `[0l 0 ]` on both machines: **zerobas's
`VDP(n)=v` does reach the port**, not merely the RGnSAV mirror.
🔴 **AND THE FIRST CUT OF THAT ROW REPORTED INTERPRETER SPEED AS A VDP
DIVERGENCE.** It timed the loop TWICE — once with the interrupt off and once with
it restored — as a guard against a loop too short to tick. That doubled the run,
and zerobas is 2.5–3.8× slower (the open TIER 4 item), so the pair **outran the
capture window**: the reference answered `[0l 0 -1 ]` and zerobas printed NOTHING
AT ALL. 🎯 **THE APPARATUS WAS THE MEASUREMENT AGAIN.** Separated in
`scratchpad/vdpie_probe.py` with five cases, each its own boot: the CONTROL shape
answers on both, the MIRROR write lands on both (`[M 208 240 ]`), the machine
SURVIVES the write and restores the register on both (`[S 240 ]`), and the
SINGLE-loop shape reads `[1 0 ]` on both. ✅ **The guard now comes from another row
— `timetick` runs the SAME 400 iterations with the interrupt ON and requires
`TIME>T` — so "long enough to tick" is established there and not paid for here.**
🔬 **TWO OF MY OWN ROWS WERE WRONG IN WAYS `SUPPORTED` CONCEALED, AND ONLY READING
EACH READING ON ITS OWN CAUGHT THEM.**
⚠️ **`tron_b` READ `[0k]` WITH NO TRACE — the same reading a DEAD TRON gives.**
`as_stored` packed the whole exec onto ONE numbered line, and TRON switches the
trace on *during* line 10, whose number has already been passed; with no line 20
there was nothing left to trace. **The row could never have discriminated, and it
scored SUPPORTED on both machines.** Fixed with a `REM` that forces a second line:
`[20][30][0k]`. The REM is not padding for length, it is the line the trace has to
reach.
⚠️ **`troff_b`'s NOTE CLAIMED `[10][20][30][0g]` AND THE MEASUREMENT IS
`[20][30][0g]`** — same cause for the missing `[10]`. The row IS discriminating
(line 30 is traced because the number prints BEFORE the TROFF on it runs, and 40–50
are not), but the note has been corrected to what was measured.
🎚️ **`INP` HAD ONLY A BOOLEAN, THE FOURTH SCREENING AXIS.** `INP(&HA8)>0` passes on
any wrong non-zero read — the same defect `vdp_b` fixed for `VDP`. `inp_b` drives a
known byte out to PSG register 0 and reads it back: `[ 66 ]`. ⚠️ **Its CRUNCH BODY
is `a=inp(&ha2)` so the reading is scored for INP** — `out_b` drives the same path
but its subject is OUT.
🎚️ **`TRON`/`TROFF` BOTH PRINTED A CONSTANT `[ok]`, THE THIRD SCREENING AXIS.** The
effect is scrapeable: MSX TRON prints each line number in brackets as it executes,
the way `listkw` scores the listing itself.
🟢 **`CIRCLE` AT N=5** — `CIRCLE [STEP](x,y),r[,[c][,[start][,[end][,aspect]]]]`.
Three new rows, each reading a pixel it must draw **and** one it must not:
`circlekw_c` STEP `[0h 15  4 ]` (an ignored STEP centres on (20,20), which draws
through (30,20) and leaves (60,50) blank — **both** readings move), `circlekw_d`
aspect `[0i 15  4 ]` ((50,70) is exactly on the rim of the circle an ignored aspect
would draw), `circlekw_e` default colour `[0j 11  4 ]` (the rim takes FORCLR and not
a hardcoded 15, and the centre reading keeps a FILLED circle from passing).
🔪 **ALL SEVEN NEW ROWS KNIFE-PROVEN LOAD-BEARING** — and `INP` needed
`kwknife.py --fn`, because it is a FUNCTION: the statement-mode pair cut a
`stmt_table` entry INP does not have and reported 🔴 BLIND. ⚠️ **A BLIND VERDICT CAN
MEAN THE WRONG CUT SHAPE, NOT A BLIND ROW.**
⚡ **D-KWBATCH4 — `LINE` AT N=6, THE WIDEST BAR IN THE TABLE, PLUS FIVE CHEAP
ONES. TWENTY-THREE KEYWORDS AT TIER 1.**
🟢 **`LINE [[STEP](x1,y1)] - [STEP](x2,y2) [,[c][,B|BF]]`** (`basic/graphics.asm`)
— six behaviours, and the three suffix forms really are three: a segment, an
OUTLINED box and a FILLED box are different drawings between the same two points.
The first coordinate is OPTIONAL and continues from the last point (GRPAC), a form
no other graphics verb here has. **N=6 is the widest in the table and it should
be** — LINE has more distinct shapes than any other MSX1 graphics statement.
🎯 **EVERY NEW ROW READS A PIXEL IT MUST DRAW *AND* ONE WHERE THE WRONG READING
WOULD HAVE DRAWN** — not merely somewhere blank, which only proves the screen is
not all 15. `linekw_d` STEP `[0o 15  4 ]`: an ignored STEP draws `(0,0)-(5,0)`, so
(3,0) lights up and (13,10) goes dark — **both** readings move. `linekw_e`
omitted start `[0p 15  4 ]`: a start defaulting to (0,0) draws the diagonal
`(0,0)-(20,10)`, which passes through **(15,7)** and misses (15,10) — so the
second reading is that diagonal, not empty space. `linekw_f` default colour
`[0q 11  4 ]` from FORCLR.
⚠️ **AND `linekw_c` USES (7,3), NOT (5,5), BECAUSE THE FIRST CHOICE WOULD HAVE
SEPARATED `BF` FROM `,B` AND FROM NOTHING ELSE.** (5,5) is inside the rectangle but
it is also ON THE DIAGONAL, so a bare segment reads 15 there too. (7,3) is inside,
off the edges and off the diagonal: 15 for a fill, 4 for a `,B` outline **and** 4
for a bare segment, so one reading separates BF from both.
🎚️ **`POINT` NEEDED A SECOND READING TO EARN N=1.** `pointkw` reads back the pixel
it had just drawn, which a POINT returning a constant — or the last colour written
— passes. `pointkw_b` reads that pixel **and one nothing ever drew**:
`[0m 15  4 ]`.
🟢 **`VPEEK`, `CSRLIN`, `POS`, `LPOS` AT N=1 WITH NO NEW ROWS** — one argument (or
none), one behaviour, and in each case the existing row already reads a VALUE that
a stub cannot fake: VPEEK reads back a byte VPOKE just wrote; `csrlind` reads the
DELTA across a PRINT rather than the absolute row (the absolute value is ambient
scroll state, which once measured the boot banner instead of the keyword); POS
prints four spaces first so the answer is a known non-zero column and not the 0 an
auto-dimmed array gives; and **LPOS's row IS the `LPRINT`** — a bare `LPOS(0)`
reads 0, exactly what a stub reads, and that left the word unattributed once
already.
🔪 **ALL FIVE NEW ROWS KNIFE-PROVEN LOAD-BEARING**, and `POINT`/`CSRLIN` needed
`kwknife.py --fn` — both were showing `connected=False` for no better reason than
never having been cut in FUNCTION mode.
⚡ **D-KWBATCH5 — SEVENTEEN KEYWORDS FOR FOUR NEW ROWS, AND A TIER 1 AWARD THAT
TURNED OUT TO REST ON A RACE. FORTY KEYWORDS AT TIER 1.**
🟢 **FOURTEEN NEEDED NO NEW ROW AT ALL** — `CHR$ HEX$ OCT$ BIN$ STR$ LEFT$ RIGHT$
CVI CVS CVD LET REM STOP END`, each one argument (or none) and one behaviour, each
with an existing row that already reads a VALUE a stub cannot fake. `endkw` puts
statements AFTER the END that would change the answer if it did not stop; `stopkw`'s
discriminator is the `Break in 10` message and not the marker before it; `rem`'s is
that `REM z` raises NO error.
🎚️ **THREE MORE NEEDED A ROW BECAUSE THE EXISTING ONE COULD NOT SEE WHAT IT
CLAIMED** — all three of the same screening axes. `space` reads `LEN(SPACE$(3))`
and **a LENGTH cannot see CONTENT**; `space_b` reads the first byte and the last,
`[ 32  32 ]`. `mki` reads `LEN(MKI$(1))`, which any two bytes pass; `mki_c` reads
both bytes of 258 = `$0102`, so the VALUE **and the byte order** are seen — a
big-endian store reads `[ 1  2 ]`. `erase` prints a constant `[ok]`, and **a
CONSTANT MARKER cannot see the EFFECT**; `erase_b` reads `[ 0 ]`, the array erased,
re-dimmed and back cleared, where an ERASE that did nothing makes the second DIM a
`Redimensioned array` error.
🔴 **A DUPLICATE ROW KEY IS SILENT AND DESTRUCTIVE, AND NOTHING CHECKED FOR ONE.**
My `mki_b` landed beside an existing `mki_b` and **the sweep ran BOTH**: two rows
with one name, and the pin is a dict keyed by row, so whichever finished last would
have SILENTLY REPLACED the other's verdict. Same shape as `GOSUB:ongosub`
overwriting GOSUB's reading — merged by key with no witness. ✅ **A module-level
guard now refuses to import a SWEEP with a duplicate key**, and the older row
(crunch `a=asc(mki$(258))`, which derives to **ASC**) carries `SUBJECT:MKI$`, since
its own note always said it was about MKI$.
🔴 **AND `mki_c` CAUGHT THAT MKI$ IS DISK BASIC.** Written without a rig tag it ran
against the diskless VG-8020 and came back EXTRA — reference `Illegal function
call`, zerobas `[ 2  1 ]`. `NEEDS-DISK:` fixes it. A missing rig tag reads exactly
like a divergence.
🔴 **BEEP'S TIER 1 AWARD RESTED ON A ROW THAT READS A TRANSIENT — CAUGHT ONLY
BECAUSE THIS BATCH MOVED IT.** `beep_b` scores the PSG mixer BEEP restores, 184
sounding against 191 finished — **a race between the beep ending and the `OUT`/`INP`
two statements later.** ALONE both machines read 184; in the full sweep the
reference reads 191 and zerobas 184, **deterministically over two runs**, because
zerobas is 2.5–3.8× slower (the open TIER 4 item) and is still sounding when the
reference has stopped. **The row was SUPPORTED only for as long as batching happened
to put the same neighbours before it**, and adding three rows elsewhere in the file
changed that.
✅ **DEMOTED TO `WEAK:` AND REPLACED, NOT PAPERED OVER.** `beep_c` reads a register
BEEP does **not** put back — channel A's tone-period low byte, zeroed first, which
BEEP leaves at **85** — so there is no race: `[ 85 ]` on both machines, in company,
knife-proven LOAD-BEARING. BEEP keeps TIER 1 on evidence that does not depend on
who finishes first. ⚠️ **THE ORIGINAL NOTE'S CLAIM IS STILL TRUE; IT JUST IS NOT
SCOREABLE** — that is what `WEAK:` is for.
🎯 **THIRD TIME TODAY THAT INTERPRETER SPEED LEAKED INTO A READING** (after `vdp_d`'s
two loops and `timetick`'s forced boolean). **A row that measures a TRANSIENT is
measuring the speed difference, not the keyword.**
⚡ **D-KWBATCH6 — SEVEN MORE FOR SEVEN ROWS, AND `VARPTR` MEASURES SHORT FOR A
REASON THAT IS ON RECORD. FORTY-SEVEN KEYWORDS AT TIER 1.**
🟢 **`MID$` AT N=3, AND THE THIRD FORM IS A STATEMENT.** `MID$(A$,n,m)=s` has
its OWN handler (`ex_mid_stmt`, `basic/str-engine.asm`), which no read row reaches
— the same shape as `VDP(n)=` and `TIME=`. `mid_c` reads the WHOLE string,
`aXYZef`: the replaced span AND that the bytes either side are untouched, where a
handler that rebuilt the string would pass a substring-only check. `mid_b` covers
the TWO-argument read, which runs to the end of the string — a different length
computation, not a different input.
🔴 **AND `mid_c` COULD NOT BE KNIFE-PROVEN, WHICH IS A LIMIT OF THE INSTRUMENT
AND IS SAID SO HERE RATHER THAN LEFT AS A GAP.** `MID$` is a two-byte function
selector (`$FF $83`), so in STATEMENT position it is not in `stmt_table` and the
statement cut reports 🔴 BLIND — the wrong-cut-shape verdict again. MID$ IS
knife-connected, through `mid_b` in `--fn` mode; what is unproven is that
`mid_c` specifically goes red when the assignment handler dies.
🟢 **`DIM` AT N=2: THE MULTI-DIMENSIONAL FORM HAS TO COMBINE SUBSCRIPTS INTO ONE
OFFSET**, which a single-subscript row cannot exercise at all. `dimkw_b` reads
`[ 7  0 ]` — the written cell **and the cell with the subscripts SWAPPED**, which is
where a row-major/column-major mix-up lights up instead.
🟢 **`DEFINT`/`DEFSNG`/`DEFDBL`/`DEFSTR` AT N=2 EACH.** `ex_deftype`
(`basic/usr.asm`) parses `letter` **or** `letter-letter` RANGE items and rejects a
reversed one, so the range is a second behaviour; the comma LIST is repetition of
those two, not a third form.
⚠️ **TWO OF THE FOUR RANGE ROWS NEEDED A SETUP TO BE ABLE TO FAIL.**
`DEFSNG A-C` alone proves nothing — single precision is already the default — so
the row runs `DEFINT A-C` first and measures that DEFSNG undid it. And **`1/3` is
DEFDBL's discriminator while `1.5` is not**: 1.5 is exact in single precision too,
so only a value needing the extra digits shows the letter really became double
(measured `.33333333333333`, fourteen digits).
🟢 **`INSTR` AT N=2 WITH NO NEW ROW** — `instr_b` searches `ABA` for `A` from
position 2, so a start that is parsed and IGNORED finds the FIRST `A` and reads 1
instead of 3.
🔭 **`VARPTR` STANDS AT 1/2, AND THE MISSING FORM IS DEFERRED WORK, NOT A
MISSING ROW.** `VARPTR(#n)` is recorded as DEFERRED in `docs/TODO-done.md`. Same
shape as `LOCATE` at 3/4: **the bar comes from the reference's syntax, not from
what we chose to build.**
🔴 **AND AS OF 2026-09-16 THE DEFERRAL HAS A MEASURED REASON, WHERE `TODO-done.md`
GAVE NONE — 🙋 IT IS NOW A RULING QUESTION FOR JOOST, NOT A TODO ITEM.**
[`scratchpad/varptrn_probe.py`](scratchpad/varptrn_probe.py), three sides:
| | `VARPTR(#1)` | `VARPTR(#2)`, default MAXFILES | stride after `MAXFILES=2` |
|---|---|---|---|
| VG-8020 | -3465 | ERR 52 | **265** |
| CF-3300 | -8850 | ERR 52 | **265** |
| zerobas | **ERR 2** | **ERR 2** | — |
🎯 **THE FORM IS GENUINELY MISSING** — `Syntax error` where both references answer
an address — and implementing it is CHEAP: `fch_ctx_addr` (basic/files.asm)
already turns a channel number into its block address.
🔴 **BUT THE ONLY AXIS THAT CAN AGREE IS THE STRIDE, AND OURS CANNOT MATCH IT.**
The ADDRESS is machine-specific, so a row must read a DELTA — exactly what
`varptr_b` does for the variable form, where "the machine-dependent base
cancels". The references stride at **265**: the MSX-standard FCB, 256-byte record
plus 9 header bytes. Ours would be `FCH_CTXSZ` = `FCH_STATESZ` 50 + `FCH_RECMAX`
256 = **306**. So `VARPTR(#n)` EXPOSES THE INTERNAL LAYOUT OF THE CHANNEL TABLE,
and matching it means adopting MSX's FCB shape — a change to the channel
implementation, not to `VARPTR`.
⚠️ **THIS IS THE FIRST BLOCKER THIS SESSION THAT SURVIVED RE-VERIFICATION.**
Fifteen re-verified, fourteen stale, this one REAL — and it only became a reason
rather than a word once it had a number. 🙋 What Joost gets to decide: implement
it anyway (the address form stops being a Syntax error, and the stride row simply
records a documented divergence), or leave it deferred and score `VARPTR` at 1/2
by design. The same shape as the `STICK`/`STRIG` breadth question already waiting
on him.
🔬 **PRICED 2026-09-17 (D-FATPAGE1), because Joost proposed it as the carve that
would fund `PLAY`'s `X<var>;` — and THE PREMISE NEEDS CORRECTING FIRST.**
🔴 **THE FAT ENGINE IS ALREADY OUT OF MAIN PAGE 1.** It is `fatprim_tenant`
(`sub/fatprim.asm`, which includes `basic/fat-prim-body.inc`); main's `fat_mount`
is a FOUR-BYTE SHIM — `ld a,DISKOP_SEL_FAT_MOUNT` / `jr fatprim_bounce`. Of
`fat-prim-body.inc`'s **86** labels only **8** exist in the main image. (My own
answer of 2026-09-16 said "the FAT is still in main page 1": true of the shims,
misleading about the engine.)
📏 **WHAT IS ACTUALLY THERE IS 394 B**, `$6427`–`$65B0`, measured as the span from
`fat.asm`'s first label to `bload.asm`'s (so it covers everything `fat.asm`
includes). ⚠️ An earlier reading of *"4012 B"* was WRONG: `fat_rand_get` /
`fat_rand_put` at `$73CE` are defined in `files.asm`, not here.

| part | ~size | |
|---|---|---|
| the selector shims (`fat_mount`/`fat_find`/…) | ~52 B | 4 B each; the engine is sub-side |
| `fatprim_bounce` | ~13 B | the one marshaller they all share |
| `fatio-body.inc` + `fatiocreate` + `fat_io_append`/`fia_*` | ~240 B | the READ path |
| `fatiow-body.inc` | ~77 B | the WRITE path |

💰 **SO THE CARVE ON OFFER IS THE ~317 B OF BYTE-LEVEL I/O**, and 10 call sites
outside the FAT's own bodies would need marshalling (`files.asm` 3, `field.asm` 3,
`cload.asm` 2, `expr.asm` 1, `bload-body.inc` 1) at 7 B each — **net ~250 B**,
which would fund `X` eight times over.
🔴 **AND IT CANNOT BE TAKEN THE OBVIOUS WAY, WHICH IS WHY THAT CODE IS IN MAIN.**
`fat_io_getbyte` is a PER-BYTE routine reached through a VECTOR: `cload.asm`
swaps `ARL_GETBYTE` between `cal_getbyte` (cassette) and `fat_io_getbyte` (disk)
and the shared line reader calls it once per byte. An inter-slot call is
**0.156 ms** (D-XSLOTPRICE), so a 4 KB `LOAD` would gain **~640 ms** of pure
overhead on a machine already ~3× slower than the reference. That is a TIER 2
question — reasonable time — not a free 250 B.
🎯 **THE CARVE IS REAL BUT IT NEEDS THE *LOOP* TO MOVE, NOT THE BYTE ROUTINE** —
i.e. the sub side runs the whole read/write, and main bounces once per
OPERATION. That is a redesign of the channel I/O layer, which is **the same layer
Joost's MSX-FCB-shape ruling already touches**, so the two should be priced
together rather than separately.
⛔ **THEREFORE IT IS NOT THE FUNDING FOR `PLAY X`** — that needs ~30 B and this is
a slice with a speed risk attached.
🎯 **RULED (Joost, 2026-09-16): NEITHER — *"I think this means we need to change to
the MSX's FCB shape."***
🔬 **MEASURED 2026-09-17 (D-FCBSTRIDE,
[`scratchpad/fcbstride_probe.py`](scratchpad/fcbstride_probe.py)) — 265 AND 267
ARE BOTH RIGHT, AND THE LAYOUT I GUESSED IS WRONG.**
| | VG-8020 | zerobas |
|---|---|---|
| `VARPTR(#1)` at `MAXFILES` 1 / 2 / 3 | −3465, −3730, −3995 | ERR 2 |
| shift per added channel | **−265** | — |
| stride #1→#2, #1→#3 | **265**, **530** | — |
| `FRE(0)` charge per channel, three steps | **267, 267, 267** | **306, 306, 306** |
✅ **THE SUBSTANCE OF THE HYPOTHESIS HOLDS**: 265 is the FCB proper (9 + 256) and
there are **2 MORE BYTES A CHANNEL** charged to `FRE(0)` that are not part of it.
Both numbers were re-measured here rather than inherited, and the FRE charge is
linear over three steps on both machines.
🔴 **BUT THE DECIDING ROW CAME BACK THE OTHER WAY, AND THAT IS THE USEFUL PART.**
I predicted `VARPTR(#1)` would shift by **267** per channel if a `FILTAB` sat
ABOVE the FCBs. It shifts by **265**, and the three readings agree on one
implied constant: **the FCB area's TOP IS PINNED AT `$F380` AND THE ARRAY GROWS
DOWNWARD, with #1 LOWEST** (`VARPTR(#1) + 265n = −3200 = $F380` for n = 1, 2 and
3). So the extra 2 a channel lives **BELOW** the FCB array, not above it — a
guess that fitted the arithmetic and still had the geometry backwards.
🎯 **WHAT THAT PINS FOR THE REBUILD**: match the reference exactly and a channel
costs **265 of FCB + 2 elsewhere**, the array hangs downward off `$F380`, and
`VARPTR(#n) = $F380 − 265·(MAXFILES − n + 1)` falls out for free instead of being
made to agree.
📏 **AND OUR OVERCHARGE IS NOW EXACT**: we charge **306** a channel
(`[state:50][record:256]`) against the reference's 267 — **39 B a channel more
than the reference charges**, of which **41 B** is the per-channel engine state
that has to leave the block (306 − 265). At `MAXFILES=15` the difference is
**585 B** of pool.
⚠️ **ONE PROBE FAULT WORTH NAMING**: zerobas's `VARPTR` cells printed
`'<E";ERR;"'` — the fence matched the SOURCE of the error line rather than its
output, because the handler's own text contains the marker. The reading is still
unambiguously an error, but a fence that appears in the source it echoes is the
hazard this tree has hit before and the cell is ugly proof of it.
 So `VARPTR(#n)` is not the work; the CHANNEL BLOCK is, and
`VARPTR(#n)` then falls out of it agreeing rather than being made to agree.
⚠️ **NOTED, NOT STARTED** (*"just note it, you don't need to do anything now"*). ➡️ **FILED 2026-09-26 as the
TIER 4 item D-FCBSHAPE** (Joost: *"file it as a tier 4 item"*) — the open work
lives there now; this paragraph is its measurement record.
🔴 **AND SCOPING IT FOUND THAT OUR TWO NUMBERS FOR THE REFERENCE'S PER-CHANNEL
BLOCK DISAGREE BY 2, WITH NOTHING RECONCILING THEM**:
| measurement | value | source |
|---|---|---|
| what `MAXFILES=n` costs `FRE(0)` per channel | **267** | D-MAXFRE, `docs/chancost-cf3300-characterization.md` §2 — exactly linear, BOTH references, ceiling 15 |
| the `VARPTR(#n)` stride | **265** | D-VARPTRN, BOTH references (the table above) |
Build to 265 and `VARPTR` agrees while `FRE(0)` is off by 2 a channel; build to 267
and the reverse. 🔬 **THE HYPOTHESIS TO TEST FIRST — AND IT IS ONLY A HYPOTHESIS:**
they measure different things, 265 being the FCB proper (9 header + 256 record) and
the other 2 a per-channel POINTER ENTRY in a separate table, which is how MSX's
`FILTAB` is publicly documented to work. 265 + 2 = 267 fits exactly, **and an
arithmetic coincidence is not a measurement** — read it on the machines before any
stride is laid down. [[two-rules-that-coincide-on-every-row-you-have]]
💰 **THE STRIDE IS THE SMALL HALF. THE 41 BYTES ARE THE WORK.** Our block is
`[state:FCH_STATESZ 50][record:256]` = **306**; the MSX FCB header is **9**. So the
change is finding a home for 41 B of per-channel ENGINE state that MSX keeps
elsewhere — the cluster iterator (`FAT_CURCLUS`/`FAT_CLUSSEC`), the file meta
`LOF` reads (`FAT_FIRSTCLUS`/`FAT_FILESIZE`), the read stream
(`FREAD_OFF`/`FREAD_LEFT`) and the whole `FWR_*` write state
(`basic/sysvars.inc` FCH_STATE0). MSX keeps it in the DISK ROM's work area —
which, after the hook re-architecture, is a place this tree now has.
📐 Blast radius: `basic/files.asm` (the ctx save/restore memcpys), `basic/field.asm`
(D-FIELDFIX made the record travel with the channel — that half already matches),
the FAT primitives, and `sub/strheap.asm`'s pool arithmetic
(`strheap_varceil`, `-FCH_CTXSZ`). 🟢 It RETURNS pool: 306 -> 265 gives back 41 B a
channel, up to **615 B** at `MAXFILES=15`.
🎚️ TIER 1 — happy path: a form both references answer and this tree refuses.
🤖 AUTONOMOUS — ruled 2026-09-16; measure 265-vs-267 first, write the shape to the
spec before moving code, then build. ⚠️ Its variable form is scored by `varptr_b` and NOT by
`varptr`, which reads `VARPTR(B)>0` — a BOOLEAN, which cannot see the address.
⚡ **D-KWBATCH7 — FIVE MORE FOR FOUR ROWS, AND THE DUPLICATE-KEY GUARD CAUGHT ME
ONE BATCH AFTER I WROTE IT. FIFTY-TWO KEYWORDS AT TIER 1.**
🔴 **I WROTE `mks_b` AND `mkd_b` AND THE IMPORT REFUSED — BOTH ALREADY EXISTED.**
The guard added in D-KWBATCH5, for exactly this, fired on its author's next batch.
🎯 **AND THE ROWS THAT EXISTED WERE THE ONES I WAS ABOUT TO DUPLICATE**: content
readings of MKS$ and MKD$, mis-attributed to **ASC** because their crunch bodies
are `a=asc(mks$(1.5))`. They now carry `SUBJECT:MKS$` / `SUBJECT:MKD$`, so both
keywords reach TIER 1 **with no new row at all** — the third time the SUBJECT tag
has recovered evidence that was already measured and scored for nobody (after
`PRINT USING` and `MKI$`).
⚠️ **THE LESSON IS NOT "CHECK THE KEY IS FREE", IT IS "CHECK WHETHER THE READING
ALREADY EXISTS UNDER THE WRONG SUBJECT".** A duplicate key is the visible symptom;
the invisible one is a row measuring the right thing and being counted for the
wrong keyword.
🟢 **`NEXT` AT N=3, AND THE SPLIT IS IN THE SOURCE.** `ex_next` parks 0 for a
bare NEXT (take the TOP frame) and `nx_comma` parks 1 (`basic/program.asm`), so the
named and comma-list forms take a DIFFERENT path through the frame search — a bare
NEXT cannot exercise the matching at all. `nextkw_c` closes TWO frames with one
`NEXT J,I` and reads `[ 3  3 ]`, where a list that closed only the first leaves the
outer loop open and I at 1.
🟢 **`BASE` AT N=2 — `BASE(n)` IS AN ASSIGNMENT TARGET TOO** (`ex_base_assign`,
`basic/interp.asm`), exactly like `VDP(n)`, and every existing row read.
⚠️ **THE WRITE ROW USES INDEX 5, NOT 2.** `BASE(2)` is the SCREEN 0 name table,
and writing it **MOVES THE TEXT PLANE THE CAPTURE SCRAPES**; `BASE(5)` belongs to
SCREEN 1, which is not on screen here, so the write is observable and harmless.
The original value is put back either way. `[0r 6144 ]`.
🟢 **`PEEK` HAD ONLY `PEEK(0)>=0`, A BOOLEAN TRUE OF EVERY POSSIBLE BYTE.** The
byte PEEK reads back was already scored — by `pokekw`, whose SUBJECT is POKE.
`peek_b`'s crunch body is `a=peek(-8192)`, so the reading is PEEK's: `[ 66 ]`.
⚡ **D-KWBATCH8 — TEN KEYWORDS AND NOT ONE NEW ROW. SIXTY-TWO AT TIER 1.**
`LOF EOF LOC KILL COPY LSET RSET DSKO$ GOSUB READ` — every one already had a row
that reads a VALUE a stub cannot fake; nothing had ever authored the bar those
readings were meeting.
🎯 **AND THE ROWS EARN N=1 BECAUSE OF WHAT THEIR AUTHORS PUT IN FRONT OF THE
READING, WHICH IS THE PART WORTH RECORDING**: `eof` **reads the file to its end
first**, so the answer is -1 against the 0 a stub gives — asking EOF of a freshly
opened file would have been 0 either way. `loc` consumes a known number of bytes
first. `kill` reads DSKF **before and after** and scores the DIFFERENCE, so it sees
the space the file gave back. `copy` opens the DESTINATION and reads its length.
`readkw` reads, RESTOREs and reads again, scoring the SUM, so a READ that always
returned the first item is still visible.
🟢 **`LSET`/`RSET` ARE EACH OTHER'S CONTROL.** Both read the FIRST byte of the
fielded buffer: left-justified it is the data, right-justified it is a pad space.
The same program with the other verb answers the other value, so neither row is
scoring merely "not a stub".
🔍 **A SUBJECT AUDIT OVER THE WHOLE SWEEP CAME BACK CLEAN.** Eighteen rows name
more than one keyword in their crunch body and declare no `SUBJECT:`; every one is
a verb plus a MODIFIER (`STEP`, `TO`, `FOR`, `ON`) or a composite `stmt_subject`
already resolves, and the three genuine mis-attributions were all the
`wrapper(inner)` shape — `a=asc(mki$(...))` and friends — which are now tagged.
⚠️ **`STICK`, `STRIG` and `PDL` ARE DELIBERATELY NOT AWARDED** *(by THESE rows; the
joystick forms of STICK and STRIG have real-stick rows since D-RIGFW, 2026-09-26)*. Their rows read 0,
which is the correct answer with nothing plugged in **and also exactly what a stub
returns** — a reading that cannot fail. `input-devices-acceptance` exercises them
properly; the kwsweep denominator cannot, and a bar met by an unfailable row would
be worse than no bar.
      🔴 **CORRECTION 2026-09-17 (D-STICKSAMPLE) — D-HOLDROW'S FRAMING WAS WRONG
      AND THE TREE ALREADY HAD THE ANSWER.** It reported *"`STICK(0)` does not
      read what the injection drives"* as a localised blocker. It does read it:
      polled instead of sampled once, `STICK(0)` reads **1** with cursor-UP held
      and `STRIG(0)` reads **-1** with SPACE held, on BOTH machines, with silent
      negative controls ([`scratchpad/sticksample_probe.py`](scratchpad/sticksample_probe.py)).
      🎯 **AND THE SHIPPING ROWS HAVE DONE EXACTLY THAT SINCE D-KWPLUG**:
      `stick_hold` reads `[2d 1 ]` and `strig_hold` reads `[1w-1 ]`, both
      SUPPORTED, both `NEEDS-HOLD:` with a poll — and `stick_hold`'s own note says
      why (*"`stick` below reads the idle 0 a stub also returns. This one holds the
      CURSOR-UP key … and reads the direction CODE"*). My probes sampled ONCE,
      immediately after `RUN`, which misses a press the poll catches. **The
      instrument was never broken; my probe was written worse than the row that
      already existed**, and three ticks went into it
      [[a-justification-parenthesis-is-an-unrun-claim]].
      ✅ **SO THE `cursor-keys` AND `space-bar` FORMS ARE ALREADY COVERED**, and
      the gap is EXACTLY the two the tier table names: `STICK`'s
      **`joystick-port`** and `STRIG`'s **`joystick-trigger`** (plus `PAD`'s
      **`switch`**). Those need a joystick that can be DRIVEN, which is what
      D-JOYPLUG measured and is the only part of this item still open.
      ⛔ **DO NOT INVESTIGATE `STICK`'s SAMPLING SOURCE** — that was D-HOLDROW's
      filed next step and it is withdrawn: `ev_ff_stick` calls `GTSTCK` and works.
      The next step is driving a PLUGGED device, nothing else.
      ⚠️ *(superseded by the correction above — kept because its INKEY$ rows are
      still the proof that the hold reaches row 8:)*
      ✅ **LOCALISED 2026-09-17 (D-HOLDROW,
      [`scratchpad/holdrow_probe.py`](scratchpad/holdrow_probe.py)) — THE HOLD RIG
      WORKS AND ROW 8 IS REACHED. `STICK(0)` DOES NOT READ WHAT THE INJECTION
      DRIVES.** One change at a time from a known-good hold, both machines
      identical:
      | case | held | reading |
      |---|---|---|
      | `INKEY$` | row 8 bit `$20` (UP) | **30** — the up-arrow code |
      | `INKEY$` | row 8 bit `$01` (SPACE) | **32** — space |
      | `INKEY$` | nothing | none |
      | **`STICK(0)`** | row 8 bit `$20` | **0** |
      So the press lands, row 8 is the right row, bit 5 is the right bit, and the
      negative control is silent — but `STICK(0)`, which on a real MSX reads the
      cursor keys, sees none of it. **On the VG-8020 too**, so this is not a
      zerobas defect: it is the injection reaching the keyboard DECODER (which
      fills the buffer `INKEY$` reads) and not whatever `STICK` samples.
      🎯 **THAT IS THE WHOLE VALUE OF THIS TICK**: the blocker was "the rig reads
      flat" and is now "`STICK`'s SOURCE is not driven by `keymatrixdown`". The
      next person looks at what `STICK` samples, not at the hold — three cuts were
      spent on the hold and it was never the problem.
      ⚠️ **ONE CASE IS NOT A FAULT AND MUST NOT BE READ AS ONE**: the F1 hold
      (row 6 bit `$20`), included as the known-good control, came back
      `<no reading>` — F1's macro AUTO-REPEATS for as long as the key is held and
      floods the screen, which is exactly why the shipping `keykw_b` row disarms
      with `KEY 1,""` first. The three rows above make it redundant.
      🔬 **RE-VERIFIED 2026-09-17 (D-JOYPLUG,
      [`scratchpad/joyplug_probe.py`](scratchpad/joyplug_probe.py)) — THE BLOCKER
      IS REAL AND ITS STATED REASON IS STALE.** Three things measured:
      * ✅ **`plug joyporta msxjoystick1` SUCCEEDS.** The pluggable exists in
        openMSX 21.0 and the prologue does not error, so *"no joystick pluggable
        in this openMSX"* is false. The plumbing to ask for one exists here too:
        `basic_probe_kwsweep.py` already has a `NEEDS-PLUG:` rig (`_plug_of`).
      * ⚠️ **PLUGGED CHANGES NOTHING**: `STICK(1)` and `STRIG(1)` read 0 plugged
        and 0 unplugged, on both machines. That row awards nothing by design — 0
        is also what nothing-plugged and what a stub return — it is here to show
        the plug did not BREAK the reads.
      * 🔴 **AND THE KEY MATRIX DOES NOT DRIVE `STICK(0)` — ON EITHER MACHINE.**
        `STICK(0)` is the KEYBOARD direction pad and needs no joystick at all, so
        arrow-UP held (row 8, bit `$20`) should read 1. It reads **0 on the
        VG-8020 as well as here.** So the instrument cannot currently move ANY
        `STICK`, and Joost's *"if needed create a testing pluggable device"* is
        still the route: what is missing is not a device to plug but a way to
        DRIVE one.
      🎯 **WHAT THAT LAST ROW COST, AND WHY THE REFERENCE COLUMN WAS WORTH IT.**
      With zerobas alone the same 0 looked like OUR `STICK(0)` being a stub — a
      TIER 1 defect reachable with no device at all, which is what I went looking
      for. The reference reading 0 too is what refuted it: an agreement on a value
      the CONTROL was supposed to move is a broken instrument, not a finding
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      ⚠️ **THREE CUTS, THREE DIFFERENT FAULTS, EACH CAUGHT BY THE CONTROL**: the
      first passed `holds` on DIRECT-mode cases, and the press is scheduled at the
      RUN SLOT which a direct case does not have; the second fixed that and still
      read flat; the third added the reference and showed the flatness is the rig,
      not the tree. The `(row, mask)` SHAPE was right throughout — `_hold_of`
      builds exactly the same 2-tuple — so the remaining suspect is the TIMING or
      the matrix row, and neither is worth another blind cut.
      📌 **NEXT STEP IS NOT ANOTHER CUT AT THIS PROBE**: take a row that is KNOWN
      to work (the `onkey` rows hold row 6 bit `$20` and score SUPPORTED) and
      change ONE thing at a time towards a `STICK(0)` read. That separates timing
      from matrix row in one run instead of guessing at both.
🎯 **RULED (Joost, 2026-09-16): *"we should come up with a way to test, if needed
create a testing pluggable device."*** So the filed blocker — no joystick pluggable
in this openMSX, injection being the MSX key matrix only, `joystickports` refusing a
write — is NOT the end of the question. ⚠️ **NOTED, NOT STARTED.**
🔬 **AND THE BLOCKER'S PREMISE IS ALREADY DOUBTFUL.** openMSX **21.0** here names
`msxjoystick1` / `msxjoystick2` and the connectors `joyporta` / `joyportb`, plus
`arkanoidpad`, `touchpad`, `trackball`, `mouse`, `joytap`, `ninjatap` and
`magickey` (read out of the shipped binary, 2026-09-16). **That is the NAMES
existing, not a plug working and not a way to DRIVE one** — the filed finding may
simply have looked for a pluggable under an older name. First step is therefore a
RE-VERIFICATION, not a build: plug `msxjoystick1` into `joyporta` from Tcl and see
whether `STICK(1)` moves.
🪜 Three rungs, cheapest first: (1) an existing pluggable driven by whatever host
event openMSX binds it to; (2) openMSX's Tcl surface poking the port directly;
(3) only if both fail, **an own testing pluggable device** — which for `PAD` may be
required anyway, since a paddle is an analogue axis no key matrix can express.
⚠️ **THE ROW IS THE POINT, NOT THE DEVICE.** What must come out of this is a
reading that CAN FAIL: today's 0 is correct-with-nothing-plugged-in and is also
what a stub returns, so the rig has to produce a NON-ZERO the stub cannot fake,
with the nothing-plugged 0 kept as the control.
🎚️ TIER 1 — happy path: three keywords stuck at 1/2, 1/2 and 2/3 forms for want of
an instrument, not for want of an implementation.
🤖 AUTONOMOUS — ruled 2026-09-16; re-verify the pluggable first.
⚡ **D-KWSTMTDEN — COMPOSITES BECOME FIRST-CLASS, AND THE DENOMINATOR MOVES**
(Joost, 2026-09-14, of the tier doc's *"Not keywords, and deliberately not in the
159-keyword denominator"*: **"why not? They should have the same TIER and
tests"**).
✅ **HE IS RIGHT, AND MY REASON WAS A PRESENTATION WORRY WEARING CORRECTNESS
CLOTHES.** I excluded them because splitting `ON` into eight "would inflate the
count by renaming" — which is a worry about how the sheet READS, not about what is
true. If `PRINT USING` is a different function from `PRINT`, it is a separate thing
that must work, with its own forms and its own tier.
🎯 **THE 159 IS A *TOKEN* DENOMINATOR** (`basic/kwtable.inc`), and `ON ERROR
GOTO` is ONE STATEMENT made of THREE tokens. Counting tokens is a proxy for "how
much of MSX BASIC works" and it breaks down exactly where composites exist: **it
says `ON` is one thing to get right when it is eight.**
✅ **SO THERE ARE TWO DENOMINATORS, EACH RIGHT FOR ITS OWN QUESTION, AND NEITHER
REPLACES THE OTHER.** TOKEN = **159**, guarded by selftest **S20** — *unchanged,
and not weakened to move a count*. STATEMENT = **171** = the 154 keywords with a
bare statement form (`DEF GET ON PUT USING` have none and would double-count
against their own composites) plus the 17 composite and channel statements.
🔪 **AND CONNECTEDNESS NOW COMES FROM THE CUT THE STATEMENT'S OWN ROW RESPONDS
TO.** `knife_connected()` was keyed by KEYWORD, so a composite could never be
connected. But the knife already proves the right thing per ROW: cutting `ON`'s
dispatch entry makes `ongoto` go red, and that row's SUBJECT is `ON GOTO`.
🔴 **`PRINT USING` IS WHY THIS HAD TO EXIST AT ALL** — `USING`'s token `$E4` is
not in `stmt_table`, so it can be connected NO OTHER WAY than through the cut its
own row responds to (`PRINT:using` → MISSING, LOAD-BEARING).
🔴 **AND THE PIN COULD NOT HOLD THE ANSWER: `rows` IS KEYED BY KEYWORD AND THE
LAST CUT WINS.** Measured: `ON:ongoto`, `ON:ongosub` and `ON:onkw` all write the key
`ON`, so two of three composites vanished — and **`PRINT:using` OVERWROTE PRINT's
own reading**, which is precisely the hazard `_warn_row_subject` exists to shout
about, happening by design instead of by mistake. ✅ A `subjects` map beside
`rows`, never overwritten by a DIFFERENT subject, so one keyword speaks for several
statements and each keeps its verdict. PRINT's own row (`tab`) re-cut afterwards.
🎯 **AND THE WARNING ITSELF WAS WRONG**: it used `stmt_keyword`, so it fired on
`PRINT:using` — a CORRECT pairing — and training the eye to ignore a warning is
worse than not having it. It speaks in SUBJECTS now.
🟢 **FOUR COMPOSITES AWARDED ON THE SAME BAR AS A KEYWORD**: `ON GOTO`,
`ON GOSUB`, `INPUT #`, `GET #`. **`ON ERROR GOTO` stands at 1/2** (missing the
`ON ERROR GOTO 0` disable, which is the form a program uses to hand an error back
to BASIC) and **`PRINT USING` at 2/5** — its format string is a small language and
its field types are the forms: integer, fraction, sign, string, exponential.
📊 **66 of 171 statements at TIER 1.** The count dropped against a bigger, truer
denominator, the same way keying evidence by SUBJECT made the table read worse
this morning. ⚠️ **A STATED IMPRECISION RATHER THAN A HIDDEN ONE:** the statement
set still counts SYNTAX PARTICLES (`THEN TO STEP ELSE AS OFF`) as statements. They
are not — but removing them is re-tiering the keyword umbrella, which is ⛔ ruled
out, so the count carries the flaw openly instead of being quietly adjusted.
✅ Selftests **S31** (the statement set is exactly keywords − bare-formless ∪
composites, each once) and **S32** (a composite CAN be awarded, and is refused for
the same three reasons a keyword is).
⚡ **D-KWSTMTDEN2 — SIX COMPOSITES AWARDED, AND THE SUBJECT SCAN FOUND THREE MORE
READINGS SCORED FOR THE WRONG THING. 68 of 171.**
🟢 **`PUT #` AND `PRINT #` GET ROWS OF THEIR OWN AND REACH TIER 1**, joining
`GET #`, `INPUT #`, `ON GOTO` and `ON GOSUB`.
🎯 **`getkw` COULD NOT SPEAK FOR `PUT #`, AND THE REASON IS WORTH THE ROW:** it
round-trips record 1 only, so **a PUT # that ignored the record number entirely
would pass it**. `puthash` writes TWO records with DIFFERENT values and reads BOTH
back — `[ 75  90 ]`, K from record 1 and Z from record 2 — so the record number is
part of the reading rather than an assumption. `printhash` reads the bytes back
through a SECOND OPEN: `[ABC]`, where a PRINT # that wrote nothing leaves an empty
file and the read fails instead.
🔍 **AND THE SUBJECT SCAN PAID AGAIN — THREE MORE MIS-ATTRIBUTIONS.** `deffn`'s
crunch body is `def fna(x)=x+1`, and **`FNA` is not the keyword `FN`**, so
derivation stopped at `DEF` and the row scored for a token with no bare form at
all. It now declares `SUBJECT:DEF_FN`, and `DEF FN` stands at **1/2** — the
string-valued FN is the missing form, and it is not a detail: it needs a GC root
the numeric one does not (Joost ruled that root takes the control-frame pool), so
the two are different machinery.
🔴 **BARE `PRINT` DROPS TO 2/5, AND THAT IS THE FINDING.** Its only two rows are
the PRINT ITEMS (`TAB(`, `SPC(`); the SEPARATORS have never been scored — `;`
concatenates, `,` advances to the next 14-column zone, and a TRAILING separator
suppresses the newline. ⚠️ **PRINT IS THE APPARATUS OF ALMOST EVERY ROW IN THIS
SWEEP AND IS THEREFORE CONSTANTLY EXERCISED AND ALMOST NEVER THE SUBJECT. BEING
USED IS NOT BEING MEASURED** — the same confusion that let `LEN(MKI$(1))` stand in
for MKI$'s content.
🔭 **`PUT SPRITE` AT 1/2.** The attribute entry carries a POSITION and a
colour/pattern pair in different bytes, and the existing row reads ONE byte of the
attribute table — so it sees the position and nothing else. N=2 says so rather
than letting one reading stand for the whole entry.
📋 **STILL UNRATED, AND EACH FOR A NAMED REASON:** `DEF USR` and `LINE INPUT`
have no row (LINE INPUT needs typed input, the same block as bare console
`INPUT`), and the four remaining ON-traps (`ON KEY/STOP/SPRITE/STRIG GOSUB`) have
dedicated acceptance suites but no kwsweep row — firing a trap inside a sweep row
is apparatus this sweep does not have.
⚡ **D-KWPARTIAL — EVERY NAMED PARTIAL CLOSED THAT WAS NOT A DELIBERATE
DEVIATION. 73 of 171.** `PRINT` 5/5, `PRINT USING` 5/5, `DEF FN` 2/2,
`PUT SPRITE` 2/2, `ON ERROR GOTO` 2/2 — all now TIER 1.
🟢 **BARE `PRINT`'S SEPARATORS, AT LAST.** Each row reads a POSITION back
rather than looking at the text, so the reading is a number both machines must
agree on: the COMMA advances to the next 14-column zone (`[0t 15 ]`, where a comma
treated as a plain separator leaves 2), the SEMICOLON concatenates with no gap
(`[0u 4 ]`), and a TRAILING separator suppresses the newline (`[0v 0 ]`, still on
row 0).
🟢 **`PRINT USING`'s FORMAT STRING IS A SMALL LANGUAGE AND ITS FIELD TYPES ARE
THE FORMS**: the explicit sign (`[ +7]`), the string field `!` which takes only
the FIRST character (`ABC` prints as `A` — a numeric-only format handler cannot do
it at all), and the exponential `^^^^` (`[ 1.23E+02]`; the exact spacing is not
predicted, what makes it a reading is that both machines produce the same one).
🟢 **`ON ERROR GOTO 0`** — with it working `ERROR 7` is untrapped and the
program stops with `Out of memory in 20`; with it ignored the handler runs.
🔴 **AND THAT ROW'S FIRST CUT PROVED NOTHING WHILE SCORING SUPPORTED, BECAUSE
**REM SWALLOWS THE REST OF THE LINE**.** I padded with `REM ZZZ...:ERROR 7` to
force the handler target onto line 40 — which COMMENTED THE ERROR OUT. No error
was ever raised, execution fell through to the handler line, and the row read
`[0w1]` on BOTH machines: agreement about nothing. ⚠️ `troff_b` gets away with REM
padding ONLY because its REMs are the LAST statement on their lines. The padding
is `A=n` now.
🎯 **AND THE ROW CARRIES NO `NOECHO:` MARKER ON PURPOSE.** When the disable
WORKS the program stops before printing, so a marker-anchored capture would read
`?nomarker` — a refusal, not a reading. Echo-anchored, the capture holds the ERROR
MESSAGE, and the failing case holds `[0w1]` instead.
🟢 **`PUT SPRITE` 2/2** — the attribute entry is four bytes (y, x, PATTERN,
COLOUR) and the old row read only the first. `putsprite_b` reads bytes 2 and 3 of
plane 0's entry: `[0x 1  13 ]`.
🟢 **`DEF FN` 2/2** — the string-valued definition, whose result lives in the
string pool where the numeric one is a float.
⛔ **NOT CHASED, AND FOR GOOD REASON: `LOCATE` 3/4, `SCREEN` 2/3 and `VARPTR`
1/2 ARE BLOCKED BY DELIBERATE DEVIATIONS AND DEFERRALS**, not by missing rows.
Writing a row for a form the tree does not implement would measure nothing.
🔪 **D-KWSTRCUT — THE THIRD CUT SHAPE, AND A FIRST VERSION OF IT THAT WAS WORSE
THAN THE GAP IT CLOSED (2026-09-13).** `basic/sysvars.inc:250` named the shape in
prose written long before the knife existed: **MKI$ is evaluated in
`basic/strvar.asm` because it RETURNS A STRING.** The site at
`basic/strvar.asm:284` was always there. Two assumptions in `plant_fn` hid it: it
matched only opcode `$CA` (`jp z,nn`) and never the RELATIVE `jr z,d` (`$28`) the
short string chain uses, and it accepted only `ev_*` targets, never the `str_*`
evaluators.
🔴 **THE UNGUARDED WIDENING THEN REPORTED `INT` AND `PEEK` AS BLIND, AND BOTH
WERE FINE.** An MSX token byte lives in **TWO NAMESPACES** — `$xx` as a statement
token, `$FF $xx` as a function selector — and the same byte names DIFFERENT
keywords in each. The tree says so twice, in lines nobody had to discover:
`INPUT_TOKEN equ $85` sits beside `INT_TOKEN equ $85`, and `sysvars.inc:2361`
reads *"`DEF_TOKEN equ $97` ; PEEK's $97 is the 2nd byte after `$FF`"*. A raw
`cp <tok>` BYTE search cannot tell them apart, so the widened rule handed `INT`
the site belonging to `INPUT$` **in the string chain**. 🎯 **THAT IS NOT A MISS.
A FALSE `BLIND` SAYS THE ROW IS DEFECTIVE ABOUT A ROW THAT IS FINE, SO AN HONEST
REFUSAL IS STRICTLY BETTER THAN A CONFIDENT WRONG VERDICT** — the instrument
failing the way the thing it replaced failed, one turn after being built.
✅ **THE NARROWED RULE**, admitting the new shape on the tightest terms that still
reach `MKI$`: `jp z` + `ev_*` is **UNCHANGED BYTE FOR BYTE**, so no prior reading
moves; `jr z` + `str_*` is accepted ONLY for the **12 string-returning selectors**
(`BIN$ CHR$ HEX$ LEFT$ MID$ MKD$ MKI$ MKS$ OCT$ RIGHT$ SPACE$ STR$`). ⚠️ And
string-ness is **DERIVED FROM `basic/kwtable.inc`'s two-byte crunch form, NOT
from how the caller spelled the keyword** — the CLI takes the equate stem (`MKI`,
because the equate is `MKI_TOKEN`) while the table holds `MKI$`, so testing the
argument would have made the guard depend on the ENTRY POINT: green from
`--allfn`, refused from the command line, same keyword and same ROM.
🔴 **D-KWPINLOSS — THE KNIFE PIN WAS DESTROYED AND NOTHING NOTICED.** It lived in
gitignored `build/`, and a `make kwcover` run (which forces `gates-full`, and
cleans) wiped it; the pin came back holding **ONE** row, from which
`tier_table.knife_connected()` would have returned a set of size 1 and printed a
perfectly plausible ladder. **TWO holes at once, and the first is the sharper
one**: `kwknife.record`'s own docstring PROMISED that *"a pin whose fingerprint no
longer matches the built ROM describes a machine that no longer exists, and the
reader says so"* — **and the reader never read the field at all.** The writer's
guarantee and the reader's behaviour were two halves of one mechanism disagreeing
on the load-bearing rule, with the docstring carrying the half nobody had
implemented. The second: no floor, so a DESTROYED pin is indistinguishable from a
thin one.
✅ **FIXED, AND THE FIX WAS VERIFIED BY RUNNING IT, NOT ASSUMED.** The pin moved
to **TRACKED `scratchpad/kwknife-connected.json`** — `build/kwsweep-verdicts.json`
may live in `build/` because EVERY battery regenerates it; **nothing regenerates
the knife pin, and that asymmetry is what decides where a pin belongs.**
`knife_connected()` now verifies the recorded fingerprint against the live ROMs
and REFUSES below a 20-row floor, naming the command that rebuilds it — the same
answer `kwcover`'s `SUITE_FLOOR` gives for the same failure.
📏 **THE DENOMINATOR, RE-MEASURED FROM A DELETED PIN SO NOTHING CONTAMINATED
SURVIVED THE OR-MERGE: 99 KNIFED, 96 CONNECTED, 3 NOT** — `CALL` and `MAX`
UNCONNECTABLE BY CONSTRUCTION (their rows test that the word is RESERVED, which
exercises the tokeniser, not a handler) and `PAD` BLIND (it needs simulated touch
input). ⚠️ **The remembered "94 knifed, 91 connected, 30 refused" DID NOT SURVIVE
to be compared against — which is precisely the weakness D-KWPINLOSS fixes.** The
string cut is worth **five** keywords: `CHR$ MKD$ MKI$ MKS$ STR$`. ⚠️ `BASE`,
`TIME` and `VDP` need EXPLICIT CLI runs: they are function-dispatched but carry
ONE-byte tokens, and `--allfn` enumerates only the two-byte `kwtable` form.
🔭 **AND THE NEXT LEAD IS NAMED RATHER THAN COUNTED.** 25 keywords still refuse:
the math group, and **seven string functions — `BIN$ HEX$ LEFT$ MID$ OCT$ RIGHT$
SPACE$` — that HAVE `str_fn_*` symbols and yet present ZERO `cp`/`jr z` sites.**
Only the `MKI$`/`MKS$`/`MKD$` trio uses the explicit comparison chain
(`str_eval_maybe_mki`); the rest are reached from inside `str_func_ff` by a shape
that is neither of the three. ~~That is a FOURTH shape~~ — **RETRACTED THE SAME
NIGHT, see D-KWSTRCUT2: there is no fourth shape. MY OWN GUARD DREW THAT LINE.**
🔧 **D-KWSTRCUT2 — THREE ITERATIONS ON ONE RULE, AND EVERY SYMMETRIC-LOOKING
WIDENING BROKE SOMETHING (2026-09-13).** Only the narrowest rule the ACTUAL CODE
justifies survived, and each wrong version was caught by MEASURING, never by
reasoning about the change — which is the only reason none of them shipped.
| attempt | what it did | what it broke |
|---|---|---|
| widen `ev_`+`str_` across both opcodes | reached MKI$ | reported `INT` and `PEEK` **BLIND** when both are fine |
| tie `str_` to `jr z` only | fixed INT/PEEK | falsely REFUSED seven string functions — and I read that as a FOURTH dispatch shape |
| untie both | fixed the seven | reintroduced the false BLIND for `PEEK` |
🔴 **(i) AN MSX TOKEN BYTE LIVES IN TWO NAMESPACES** — `$xx` as a statement token,
`$FF $xx` as a function selector — **and the same byte names DIFFERENT keywords in
each.** `INPUT_TOKEN equ $85` sits beside `INT_TOKEN equ $85`; `sysvars.inc:2361`
reads *"`DEF_TOKEN equ $97` ; PEEK's $97 is the 2nd byte after `$FF`"*. A raw `cp`
byte search cannot tell them apart.
🔴 **(ii) WHEN A SET SPLITS SUSPICIOUSLY CLEANLY, CHECK WHETHER YOUR OWN
INSTRUMENT DREW THE LINE.** `str_func_ff` (`basic/str-engine.asm:991`) tests every
selector with the SAME `cp <TOK>` chain; it reaches `CHR$`/`STR$` by `jr z` and
`LEFT$`/`RIGHT$`/`MID$`/`HEX$`/`OCT$`/`BIN$`/`SPACE$` by `jp z`, purely a matter of
which targets sit inside a RELATIVE jump's reach. The five that passed were exactly
the `jr z` ones and the seven that refused were exactly the `jp z` ones. **That
split was my filter, and I filed it as a property of the interpreter.**
🔴 **(iii) AND THE ASYMMETRY IS REAL, SO THE RULE IS ASYMMETRIC.** `PEEK` (`$97`)
has exactly ONE `cp`-site: a `jr z` to **`ev_ff_ckaddr`, a SHARED ADDRESS-CHECK
HELPER, not PEEK's evaluator.** Rejected, `plant_fn` declines and PEEK falls
through to the `ev_ff_argtab` cpir cut — which IS its dispatch, and cuts
correctly. Accepted, the knife cuts the shared helper, PEEK keeps working, and the
row is called BLIND. [[a-shared-tail-is-not-a-decision]] in a new place. So:
**`ev_*` via `jp z` ONLY** (expr.asm's chain is a `jp z` chain by construction —
`plant_fn`'s own opening note says a `jr` to the error tail would usually be out of
range, so an `ev_` symbol reached by `jr z` is a HELPER, not a selector), and
**`str_*` via EITHER opcode but only for the 12 string-returning selectors.**
Verified simultaneously: PEEK load-bearing via argtab, `LEFT$`/`MID$`/`SPACE$` via
`jp z`+`str_`, `MKI$` via `jr z`+`str_`, `INT` refusing honestly.
🔧 **AND THE CLI WAS POISONING THE PIN WITH KEYS NOTHING READS.** It takes the
EQUATE STEM (`LEFTD`, because the equate is `LEFTD_TOKEN`) while `tier_table`
matches pin keys against KWTABLE words (`LEFT$`) — so a run left
`BIND HEXD LEFTD MIDD OCTD RIGHTD SPACED` in the pin: **entries contributing NO
evidence for the keyword they were measured for, while still inflating the row
count `knife_connected`'s own floor reads.** Normalised at the source
(`_kwtable_name`), and the new sweep is checked for stem-named keys rather than
trusted.
📏 **THE DENOMINATOR, from the pin alone, every key a kwtable word, fingerprint
matching the live ROMs: 106 KNIFED, 103 CONNECTED, 3 NOT** — `CALL` and `MAX`
unconnectable by construction, `PAD` blind. **18 refuse**, and they are now ONE
coherent family rather than a mixed bag: `ABS ASC ATN CDBL CINT COS CSNG ELSE EXP
FIX INT LEN LOG RND SGN SIN SQR TAN`. Against the remembered `94/91/30` that
**+12 connected, −12 refused** is the whole string group arriving at once.
🔴 **`PAD` IS THE FIRST GENUINELY BLIND ROW, AND THE REASON GENERALISES: ITS
OBSERVATION IS AN ERROR (2026-09-13).** The row is `PRINT PAD(9)` —
deliberately out of range, so a real `PAD` raises `Illegal function call`
while an absent one auto-dims an array and prints 0. That discriminates
**TOKENISED from NOT**. Cut `PAD`'s dispatch and the word is still tokenised,
the fallback still errors, and **the row sees no difference**.
➡️ **A ROW WHOSE READING IS AN ERROR CANNOT TELL A WORKING FEATURE FROM A
DIFFERENTLY-FAILING ONE**, because the failure mode it is blind to produces
the same error it is looking for. That is a sixth silent-failure shape and it
is not in the list of five: the others are ways two machines agree about
NOTHING, this is a way they agree about the WRONG THING.
🔬 **AND THE OBVIOUS FIX IS MEASURED SHUT.** Reading a VALUE instead of an
error would be immune — a cut turns a number into an error — but every
in-range `PAD(0..7)` answers **0 on BOTH machines**, and an absent `PAD`
answers 0 too ([readings](scratchpad/kwknife_padchk.out)). That is
silent-failure mode 2 exactly, so a value row would be blind for the classic
reason instead of this one.
⚠️ **PLUGGING THE DEVICE IS NOT ENOUGH EITHER, ALSO MEASURED**: openMSX has a
touchpad (`plug joyporta touchpad`, already used by
`basic_probe_input_devices.py`) and with it plugged every `PAD(n)` still reads
0 — an UNTOUCHED pad reports nothing, which is correct behaviour. A connected
row therefore needs **SIMULATED TOUCH INPUT**, not merely a present device,
and that is the apparatus this keyword is actually blocked on.
🎯 **TWO INSTRUMENTS REACHED THIS INDEPENDENTLY**, which is why it is worth
trusting: `make kwcover` had already shown `PAD` appearing only inside a
blank-sweep line — coverage existing solely as someone else's setup — and the
knife then found its row unmoved by cutting the dispatch. Neither knew of the
other's finding.
📏 **94 KEYWORDS MEASURED, 91 CONNECTED — and the earlier function numbers are
RETRACTED, because they were taken on a corrupted ROM (2026-09-13).**
| | n | |
|---|---|---|
| **connected** | **91** | a cut makes the row notice |
| cannot be, by construction | 2 | `CALL`, `MAX` — their rows test that the word is RESERVED, which exercises the TOKENISER, not a handler |
| 🔴 **genuinely BLIND** | **1** | **`PAD`** — the cut landed and the row still did not notice |
| refused, not measured | 30 | the math and string groups dispatch through neither shape |
🔴 **FOUR FAULTS, EVERY ONE IN THE KNIFE'S BOOKKEEPING RATHER THAN ITS CUT.**
That is the pattern worth keeping: an instrument that modifies BUILD ARTEFACTS
has a far larger blast radius than its logic suggests, and each of these
reported success while it happened.
| fault | how it showed |
|---|---|
| it ate the kwsweep pin it depends on | each cut's single-row sweep overwrites `build/kwsweep-verdicts.json`; the pin came back holding ONE row |
| its write hid a knifed machine from `make` | a knifed artefact is NEWER than its sources, so `make repack-machine` does nothing — the installed ROM was `63721706` where a clean build gives `e3dbed36` |
| its restore hard-coded a 2-byte width | statement cuts save two bytes, function cuts ONE, so the slice **shortened the ROM**; every keyword after `EOF` was measured against a shifted image, which is why `PEEK` read as missing from `ev_ff_argtab` — that table's FIRST byte |
| its merge took the LAST cut, not the OR | `BASE` `TIME` `VDP` were marked unconnected after a later statement sweep overwrote a function cut that had already proved them connected |
⚠️ **AND A TAXONOMY ERROR OF MINE: TOKEN WIDTH DOES NOT DETERMINE DISPATCH.**
`BASE`, `VDP` and `TIME` carry SINGLE-byte tokens and are nonetheless
function-dispatched, so an enumeration that selected two-byte tokens skipped
them silently. The 1-byte/2-byte split in `kwtable.inc` is about TOKENISATION,
not about which chain executes the word.
🎯 **`PAD` IS THE FIRST GENUINELY BLIND ROW THE TREE HAS FOUND**, and it was
already suspected from the other direction: `make kwcover` showed `PAD`
appearing only inside a blank-sweep line, i.e. as someone else's setup. Now the
knife says its row does not notice when `PAD`'s dispatch is removed. **Two
independent instruments, one conclusion — the row needs rewriting.**
⚠️ **THE 30 REFUSALS ARE A THIRD DISPATCH SHAPE, not a failure**: `LEN` `LEFT$`
`ASC` `ABS` `SQR` `SIN` `CHR$` and the rest of the math/string groups reach
neither a `cp`-with-`ev_*`-target nor `ev_ff_argtab`. The knife REPORTS them
rather than guessing, which is the behaviour that makes the other 94 readings
worth anything.
🟢 **THE FUNCTION CUT CLOSES THE GAP: 75 OF 77 CONNECTED, 2 BY DESIGN, ZERO
VACUOUS (2026-09-13).** The five that the statement sweep could not move split
cleanly once the right path was cut.
| | n | |
|---|---|---|
| connected by the **statement** cut | 72 | the dispatch entry |
| connected by the **function** cut | 3 | `VDP` MISSING, `BASE` and `TIME` UNREADABLE |
| **reservedness rows**, which never dispatch | 2 | `CALL`, `MAX` |
| vacuous | **0** | |
🔬 **THE FUNCTION CUT PATCHES THE COMPARISON OPERAND, not the jump target.**
`$FF` selectors dispatch through a `cp <TOK>` / `jp z,<handler>` chain in
`expr.asm`, so changing the operand to a byte no keyword uses ($FE) makes the
selector never match and the chain fall through to its own error path. It
works for `jp z` and `jr z` alike, where repointing a `jr` would usually be
out of range.
⚠️ **AND IT REFUSES AMBIGUITY RATHER THAN GUESSING.** Matching `cp <tok>`
followed by any conditional jump found **2-3 sites per keyword** — the token
byte recurs in the tokeniser, the detokeniser, and by coincidence inside other
operands. Requiring the jump's target to resolve to a known `ev_*` symbol cuts
each to exactly one; a keyword with no such site is REPORTED, not guessed at.
🎯 **`CALL` AND `MAX` CANNOT BE CONNECTED TO A DISPATCH ENTRY, BY DESIGN**, and
both rows say so in their own notes: `MAX` is *"the 1st half of MAXFILES"* and
its row asserts *"bare MAX is a Syntax error on a real machine; a stub prints
0"*, while `CALL`'s tests reservedness — `CALL=1` must be a Syntax error. A row
that deliberately tests that a word is RESERVED is testing the tokeniser, not
the handler, and no handler cut can move it.
🔴 **AND `TIME` IS CONNECTED BUT STILL WEAK — the two are different properties.**
It notices the function cut, yet its `WEAK:` tag stands for an unrelated
reason: absent `TIME` reads as the variable `TI` = 0 and `0>=0` is still true,
which no dispatch cut can simulate. **Connectedness is not strength**, and this
is the cleanest example of a row having one without the other.
📏 **THE FULL STATEMENT SWEEP IS IN: 77 keywords, and NO ROW IS VACUOUS
(D-KWKNIFE, 2026-09-13, [readings](scratchpad/kwknife_all.out)).** Every
statement keyword in `stmt_table` that has a kwsweep row was knifed — its
dispatch entry cut in the built ROM, the machine re-installed, its row re-run.
| | n | |
|---|---|---|
| **CONNECTED** — the row noticed | **72** | MISSING, UNREADABLE or DIVERGENT |
| did not notice | 5 | and every one has a reason its own row already states |
🎯 **THE FIVE ARE NOT FIVE BAD ROWS**, which is the whole point of reading what
the row saw instead of the verdict it printed:
| keyword | why the cut changed nothing |
|---|---|
| `VDP` `BASE` `MAX` | the row exercises the **FUNCTION** form (`VDP(1)`, `BASE(2)`, `MAX` as a value) while the knife cut the **STATEMENT** entry — the wrong path was cut, and the function cut is the next slice |
| `CALL` | the row tests **RESERVEDNESS** by design — `CALL=1` must be a Syntax error — and never dispatches |
| `TIME` | **already tagged `WEAK:`** by the sweep and excluded from its own tally |
🟢 **AND THE `TIME` ROW IS THE BEST VALIDATION THIS INSTRUMENT COULD HAVE GOT.**
Its note, written long before the knife existed, says: *"absent => variable TI,
always 0, and `0>=0` is STILL true, so this row passes on a machine with no
TIME."* The knife rediscovered that weakness by cutting the ROM, with no
knowledge of the note — a human judgement and a mechanical one agreeing by
completely different routes. The knife now reads the `WEAK:` tag and reports
such a row as *already excluded* rather than as a discovery, because
double-counting a known weakness would inflate its own findings.
⚠️ **WHAT THIS DOES AND DOES NOT SAY.** It says 72 rows are CONNECTED to their
keyword: a total failure of the handler is noticed. It does **not** say any
keyword is correct, and it does not touch BREADTH — one connected row is still
one expression. Both halves are needed and only one is now measured.
🔬 **TWO SELF-INFLICTED FAULTS ON THE WAY, both caught by the `--list` dry run
or by counting the output**: token bytes COLLIDE between statement tokens and
the `$FF` function selectors, so reading `sysvars.inc` equates listed `EXP`
`SIN` `ATN` `ASC` as statements (`kwtable.inc` is authoritative: `db len,
"NAME",1,TOK` is a statement, `…,2,PEEK_PREFIX,TOK` a function); and the first
full run **stopped at keyword 27 of 77** because a second token lookup by NAME
cannot spell `DSKO$`, and it exited rather than skipping. **Its 26-line tally
looked exactly like a finished measurement** — a partial sweep and a complete
one differ by nothing visible in the summary, so the count of result lines is
now checked against the dry run's total.
🔪 **THE NON-VACUITY HALF IS BUILT AND HAS ITS FIRST READING (D-KWKNIFE,
2026-09-13, [`scratchpad/kwknife.py`](scratchpad/kwknife.py),
[readings](scratchpad/kwknife.out)).** Cut a statement's dispatch entry in the
BUILT ROM, re-install, re-run only that keyword's kwsweep row: a row still
`SUPPORTED` with the handler dead is **BLIND**.
| keyword | row | knifed verdict | |
|---|---|---|---|
| `POKE` `VPOKE` `SOUND` `RESTORE` `ERASE` `SWAP` | their happy rows | all **MISSING** | ✅ connected, 6 of 6 |
🎯 **AND THE CLAIM IS DELIBERATELY SMALL, because D-TIER0's lesson is one day
old**: the knife cuts the DISPATCH ENTRY, so the keyword becomes
undispatchable — a TOTAL failure. A row that notices a total failure is
**CONNECTED** to its keyword. It is NOT thereby shown to notice a SUBTLE one,
and `docs/spec-basic-kwcover.md` §2 says exactly that: *"Not claimed: that a
green sweep means the keyword is CORRECT. It means a total failure of its
handler is noticed."* So this closes the **vacuity** question and leaves the
**breadth** question untouched — both are needed to establish a tier.
🔬 **WHY THE TABLE ENTRY AND NOT THE HANDLER**: handlers are shared (a shared
tail is a label, not a decision — `ev_f_err` had eight jumps and only one was
the subject), so cutting a handler can disable keywords the run never names.
A `db token / dw handler` entry belongs to exactly one keyword.
⚠️ **THE PLANT IS READ BACK BEFORE EVERY RUN.** An unplanted knife and a
keyword with nothing to find report identically, which is how thirteen runners
shipped inert [[a-knife-can-be-inert-because-the-build-did-not-happen]]. The
ROM bytes are verified after writing and the run REFUSES if they are not what
was written.
📏 **THE SCALING NUMBER, which is what decides whether this reaches 159**: about
a minute per keyword — one ROM patch, one re-install, one single-row sweep, no
rebuild. ⚠️ **STATEMENT keywords only**: the `$FF` FUNCTION selectors dispatch
through a `cp`/`jr` chain in `expr.asm`, not a table, so they need a different
cut and are not covered by this reading.
📏 **WHAT WOULD ESTABLISH A TIER, so this is a state with an exit and not a
permanent disclaimer**: (a) **BREADTH** — agreement points covering a verb's
real FORMS (argument shapes, optional clauses, modes, direct vs stored), not
one expression; and (b) **NON-VACUITY** — a mutation spot-check showing those
rows go RED if the keyword breaks. Both, together. (b) is the knife, demoted
from primary attribution (it finds no defects) but exactly right for vacuity
and cheap on a SAMPLE.
🔴 **HOW THE WRONG READING GOT IN, because it is a class and not a typo.** The
tool inferred "reached" from the ABSENCE of a filed defect — a fair
bookkeeping device, and its own source said so: *"the 'reached' column becomes
a measurement only when gate rows declare their keyword; until then this is
the honest ceiling on what is known."* Then the drain filled the unattributed
column and the group was labelled **`"1 — happy path reached, scored by
kwsweep"`**. That single label merged absence-of-evidence with
presence-of-evidence, and the caveat two hundred lines above it was never read
against it. `kw3` was then added BY SYMMETRY, inheriting the flaw.
⚠️ **AND THE RULE THAT WOULD HAVE CAUGHT IT WAS ALREADY IN THIS FILE, APPLIED
ONE LEVEL TOO LOW**: *a case that agrees can agree for the wrong reason* was
checked on every new ROW all session — `CSAVE` agreeing on an EMPTY capture,
four wrong readings before one right one — while the COLUMN that aggregates
those rows quietly promoted agreement to attainment. **An instrument can be
careful per-measurement and still overclaim in aggregate, and the aggregate
label is the one people read.**
🎚️ **AND A COUNTABLE GOAL MADE IT FEEL LIKE PROGRESS**: the drain's 114 → 0 was
a real number that really went down. What was wrong was never the count.
🎯 **RULED (Joost, 2026-09-13), TWO STANDING ANSWERS:**
1. **`kwsweep` MAY SIT AT `DIVERGENT > 0`.** The number means *unfixed defects
   the sweep can see*, and a filed row is NOT pinned back to zero — pinning
   would hide exactly what the row exists to show. A rising count is a new
   finding; a steady one is the backlog.
2. **"WOULD A 1985 LISTING PLAUSIBLY HIT THIS?" GOVERNS BYTES, not just
   rows.** It was already the TIER 3 legend's test for what to WRITE A ROW
   about; it is now also the test for whether an obscure error case earns
   scarce ROM. An item that fails it is RE-TIERED or RETIRED rather than left
   open forever against a wall it will never be worth crossing.

**Every open item carries a `🎚️` line** naming its tier — or, for items that are
not about a keyword at all, its class: **APPARATUS** (gates, probes, tooling),
**BUDGET** (ROM bytes), **STANDING** (a ruling, not work), **OTHER** (DOS
Tier-2, architecture). Non-keyword classes rank below every keyword tier for the
PRODUCT; an APPARATUS item is picked only when it blocks a keyword tier or when
nothing at TIERS 1–4 is autonomous. **Count the tiers, never quote a count:**
`grep -cE "🎚️ TIER (1)" TODO.md` and so on (the regex form, so this legend does not count itself). 🔴 A tag is a READING of the block's
headline on 2026-09-10 — argue with it by reading the block, and re-tag when an
item's residual changes tier (an item filed at TIER 5 whose fix turns out to
break a happy path is TIER 1).
🏗️ **AN ARCHITECTURE ITEM IS TAGGED AT THE LOWEST TIER ANY SYMPTOM OF IT CAN
PRODUCE — AND WHEN THAT IS UNMEASURED, IT IS SCOUTED, NOT PARKED** (Joost,
2026-09-10, reading the table: *"some of the tier 5 ones seem fundamental/urgent,
like 'THE Z80 STACK IS IN THE WRONG PLACE'"*). The `DEF FN` cap is that item's
only MEASURED symptom, but the same stack carries every expression's recursion;
whether an ordinary nested formula hits the floor is one ramp probe away
(`scratchpad/parennest_probe.py`), and the answer is the tag.
**Answered the same hour: TIER 1.** Depth 16 parentheses wrecks the machine,
16 nested `ABS` is a bogus ERR 50, 12 nested string functions crash; both
references are fine to 32. The rule paid for itself on its first use.
**What this supersedes:** the 2026-09-02 sequencing ruling below, in part — see
its tail. **What it does not change:** the standing ≤20 B budget, style splits
to the VG-8020, diskless as an official target, and every rule about HOW to
measure. **The pick rule for the loop:** lowest tier with an autonomous gap
first; within a tier, the most-used keyword first; TIER 5 and apparatus only
when TIERS 1–4 are clean or blocked on Joost.

🎯 **RULED 2026-09-10 (Joost, item by item — the rulings are on the blocks).**
Every TIER 1 item is now 🤖; every TIER 5 item is PARKED until TIERS 1–4 are
clean and its order is a joint pass; the ROM-budget items carve freely under the
20 B rule and the three stale wall items are closed; apparatus stays as classed.
**THE TIER 1 PICK ORDER, most-used first** (a proposal from the rule, not a
ruling — argue with it by reading the blocks; recount with the `🎚️` tags):

  0. the per-keyword table — the instrument that generates the rest of this list
  1. the line / screen editor (Joost: *"should also be in the list"*)
  2. the missing keywords: the eight the reference tokenises, the
     keyword-completeness remainder, `KEY n,"str"` / `KEY LIST`, the editor
     keywords, `DSKI$` / `DSKO$`
  3. `LOF` −256 / `PUT` past record 255 — the u32 → float shape
  4. the string-`FN` GC-root scout (🔭)

**RE-CHECKED 2026-09-01: 116 open blocks, 116 markers, 0 unmarked.** 🔴 **AND THAT SENTENCE
IS THE PROBLEM, NOT THE PROOF — IT WAS TRUE ONLY OF THE RULE THAT WROTE IT.**
Re-run 2026-09-05 by [`tools/check_todo_markers.py`](tools/check_todo_markers.py):
**8** open blocks carried no marker, and `--count` — the instrument that produced
the line above — reported **4**. See the D-MARKGATE record below; this paragraph
stands as taken, and it is now GATED rather than re-asserted. It was
**118 blocks / 115 markers** when this session opened — 🔴 **THREE OPEN ITEMS HAD
NO MARKER, WHICH IS THE FAILURE THIS INVARIANT EXISTS TO CATCH, AND IT HAD BEEN
FAILING SILENTLY**: nothing runs `--count`, so the line below said "checked"
about a day in August. Two of the three (`subrom-closure-check`'s `equ` alias;
the truncated tokenised load) were **finished work still spelled `- [ ]`** — both
re-verified by RUNNING, not reading, then closed — and the third (D-NGRAM) is the
arc this loop has shipped nineteen slices of, invisible to the pick-up rule for
want of one emoji. The figures in the table above are **2026-08-27** and stand as
taken; these are today's. Recount, never quote.

🔴 **A MISFILED 🤖 IS NOT A STOP CONDITION — WRAP UP AND REFILE.** If an item
marked autonomous turns out to need a decision of his: **finish and commit
whatever was actually measured** (the finding, the probe, the row — nothing is
thrown away), **re-mark the item 🙋 with the reason on its marker line**, and
**pick up the next 🤖**. Never decide on his behalf; never idle waiting for an
answer. That discipline is what makes a generous 🤖 list safe.

⚠️ **TIES GO TO 🙋, AND AN UNMARKED OPEN ITEM IS UNCLASSIFIED, NOT AUTONOMOUS.**
Misfiling toward 🤖 is the expensive direction; misfiling the other way only
costs a question.
⚠️ **THE MARKERS ARE A HEURISTIC OVER THE BLOCK TEXT PLUS THREE HAND
CORRECTIONS**, not a reading of all 111. Three were re-marked by hand because
the signal that caught them was not their reason — the override list is in the
classifier, because tuning the pattern until it agrees is fitting an answer you
already hold.

⚠️ **This section exists so a residual cannot be lost by being written up inside a
`- [x]` block.** Several of the items below were filed that way — accurate, dated,
and invisible to anyone scanning for `- [ ]`. Each line here is a **one-line
pointer**: the detail stays where the slice wrote it, at the cited line. Keep this
list short — close items, do not restate them.

Also the reason `MEMORY.md` no longer carries a copy of this list: the memory index
is loaded every session and must stay compact, so it points here instead of
duplicating (and drifting from) what is written below.

📏 **DATED 2026-08-09 BY A STALENESS SWEEP**,
[`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md).
All **56** open items were enumerated mechanically and classified; the **17** that
assert a concrete, checkable behavioural divergence were re-run on both references
and on zerobas from a clean build (164 case-runs, 48 s). **6 were STALE** and are
closed below with the measurement that closed them; **11 are LIVE** and carry a
`RE-MEASURED 2026-08-09` line; **3** more are behavioural but not reachable by this
instrument and say so; the remaining 36 are apparatus, carve prices, doc debt or
scope and were excluded **by kind**, listed by line in §6 of that document —
and the partition is **machine-checked complete and disjoint** against this
file's own `- [ ]` lines (§1.1), so no open item was skipped without leaving a
trace.
🔴 **Two of the eleven live items no longer read as filed** — see the `ON ERROR
GOTO 0` and `DEFINT` entries. 🔴 **And five of the six stale ones were closable
from evidence already in this file or in a gate that runs on every build**: a
residual gets closed by a slice aiming at something else, and nothing re-reads the
list. **When a slice lands, grep this list for what it just shipped.**

**BASIC surface**

- [ ] **`check_todo_citations.py` VERIFIES THAT AN ID MATCHES ITS LINE, NEVER THAT THE CITED BLOCK IS THE ONE THE P...** -> [X-CHECK-TODO-CITATIONS-PY-VERIFIES-THAT](todo/open/X-CHECK-TODO-CITATIONS-PY-VERIFIES-THAT.md) <!-- item:open/X-CHECK-TODO-CITATIONS-PY-VERIFIES-THAT -->

- [x] **`tools/split_todo_archive.py --apply` IS A ONE-SHOT TOOL THAT DOES NOT SAY SO, AND THE SECOND RUN DAMAGED T...** -> [X-TOOLS-SPLIT-TODO-ARCHIVE-PY-APPLY](todo/done/X-TOOLS-SPLIT-TODO-ARCHIVE-PY-APPLY.md) <!-- item:done/X-TOOLS-SPLIT-TODO-ARCHIVE-PY-APPLY -->

- [ ] **D-NGRAM: EXACT REPEATED INSTRUCTION SEQUENCES — `req_letter` SHIPPED (−50 B), THREE CANDIDATES LEFT.** -> [D-NGRAM](todo/open/D-NGRAM.md) <!-- item:open/D-NGRAM -->

- [ ] **ANY BATTERY OR KNIFE SCORE TAKEN 2026-08-30 EVENING .. 2026-08-31 04:30 IS SUSPECT — THE HOST WAS ASLEEP UN...** -> [X-ANY-BATTERY-OR-KNIFE-SCORE-TAKEN](todo/open/X-ANY-BATTERY-OR-KNIFE-SCORE-TAKEN.md) <!-- item:open/X-ANY-BATTERY-OR-KNIFE-SCORE-TAKEN -->

- [ ] **A FILED FACE ROTS WITHOUT THE ROW CEASING TO DIVERGE, AND NOTHING DETECTS THAT.** -> [X-A-FILED-FACE-ROTS-WITHOUT-THE](todo/open/X-A-FILED-FACE-ROTS-WITHOUT-THE.md) <!-- item:open/X-A-FILED-FACE-ROTS-WITHOUT-THE -->

- [ ] **SEVEN FILED PROBES PRINT DIVERGENCES AND EXIT 0.** -> [X-SEVEN-FILED-PROBES-PRINT-DIVERGENCES-AND](todo/open/X-SEVEN-FILED-PROBES-PRINT-DIVERGENCES-AND.md) <!-- item:open/X-SEVEN-FILED-PROBES-PRINT-DIVERGENCES-AND -->

- [ ] **A PER-KEYWORD TABLE (implementation · error handling · performance) — PARKED BY JOOST 2026-09-10, WITH THE...** -> [X-A-PER-KEYWORD-TABLE-IMPLEMENTATION-ERROR](todo/open/X-A-PER-KEYWORD-TABLE-IMPLEMENTATION-ERROR.md) <!-- item:open/X-A-PER-KEYWORD-TABLE-IMPLEMENTATION-ERROR -->

- [ ] **THE CORRECTNESS SCOREBOARD — WHAT "FULL CORRECTNESS" ACTUALLY REQUIRES, 2026-09-02.** -> [X-THE-CORRECTNESS-SCOREBOARD-WHAT-FULL-CORRECTNESS](todo/open/X-THE-CORRECTNESS-SCOREBOARD-WHAT-FULL-CORRECTNESS.md) <!-- item:open/X-THE-CORRECTNESS-SCOREBOARD-WHAT-FULL-CORRECTNESS -->

- [ ] **STANDING (Joost, 2026-09-04): A PURELY STYLISTIC ORACLE SPLIT GOES TO THE VG-8020, ON BOTH TARGETS.** -> [X-STANDING-JOOST-2026-09-04-A](todo/open/X-STANDING-JOOST-2026-09-04-A.md) <!-- item:open/X-STANDING-JOOST-2026-09-04-A -->

- [ ] **STANDING SEQUENCING (Joost, 2026-09-02): SPEED MATTERS AND WE SHOULD AT LEAST TRY — BUT CORRECTNESS COMES F...** -> [X-STANDING-SEQUENCING-JOOST-2026-09-02](todo/open/X-STANDING-SEQUENCING-JOOST-2026-09-02.md) <!-- item:open/X-STANDING-SEQUENCING-JOOST-2026-09-02 -->

- [ ] **STANDING TIER (Joost, 2026-08-31): WHEN THE 🤖 QUEUE DRAINS, REVIEW EACH STATEMENT'S IMPLEMENTATION IN FULL,...** -> [X-STANDING-TIER-JOOST-2026-08-31](todo/open/X-STANDING-TIER-JOOST-2026-08-31.md) <!-- item:open/X-STANDING-TIER-JOOST-2026-08-31 -->

- [ ] **THE LAST THREE UNATTRIBUTED KEYWORDS ARE AN APPARATUS PRICE, NOT A METHOD — `CLOAD`, `CSAVE`, `INKEY$`.** -> [X-THE-LAST-THREE-UNATTRIBUTED-KEYWORDS-ARE](todo/open/X-THE-LAST-THREE-UNATTRIBUTED-KEYWORDS-ARE.md) <!-- item:open/X-THE-LAST-THREE-UNATTRIBUTED-KEYWORDS-ARE -->

- [ ] **STANDING BUDGET (Joost, 2026-09-09): SPEND UP TO 20 B OF MAIN PAGE 1 ON A MEASURED DIVERGENCE WITHOUT ASKING.** -> [X-STANDING-BUDGET-JOOST-2026-09-09](todo/open/X-STANDING-BUDGET-JOOST-2026-09-09.md) <!-- item:open/X-STANDING-BUDGET-JOOST-2026-09-09 -->

- [x] **D-USING (2026-09-09): PRINT USING'S FORMAT VOCABULARY HAS THREE REFERENCE SPLITS, AND ZEROBAS FOLLOWS A DIF...** -> [D-USING](todo/done/D-USING.md) <!-- item:done/D-USING -->

- [ ] **THE NEGATIVE-EXP DEVIATION IS WIDER THAN §12.9 RECORDED — and it is DELIBERATE, not a defect.** -> [X-THE-NEGATIVE-EXP-DEVIATION-IS-WIDER](todo/open/X-THE-NEGATIVE-EXP-DEVIATION-IS-WIDER.md) <!-- item:open/X-THE-NEGATIVE-EXP-DEVIATION-IS-WIDER -->

- [ ] **D-PEEPHOLE: THE CLASSIC Z80 SIZE IDIOMS, COUNTED — SAFE CLASS TAKEN, FLAG-CHANGING CLASS STILL OPEN (20 B).** -> [D-PEEPHOLE](todo/open/D-PEEPHOLE.md) <!-- item:open/D-PEEPHOLE -->

- [ ] **IXH/IXL/IYH/IYL: MEASURED** -> [X-IXH-IXL-IYH-IYL-MEASURED](todo/open/X-IXH-IXL-IYH-IYL-MEASURED.md) <!-- item:open/X-IXH-IXL-IYH-IYL-MEASURED -->

- [x] **A DEAD REFERENCE MACHINE WAS CACHED AS A READING — FIXED 2026-09-02 (D-SCRAPEMODE), AND THE HARNESS HAD DIA...** -> [D-SCRAPEMODE](todo/done/D-SCRAPEMODE.md) <!-- item:done/D-SCRAPEMODE -->

- [ ] **A HAND-WRITTEN ERROR-MESSAGE ALPHABET IS A BLIND SPOT, AND 19 PROBES CARRY ONE.** -> [X-A-HAND-WRITTEN-ERROR-MESSAGE-ALPHABET](todo/open/X-A-HAND-WRITTEN-ERROR-MESSAGE-ALPHABET.md) <!-- item:open/X-A-HAND-WRITTEN-ERROR-MESSAGE-ALPHABET -->

- [ ] **A 2 B CARVE WITH ITS EVIDENCE ALREADY ATTACHED: `ems_typecheck`'s two `pop de` ARE PROVABLY UNNECESSARY.** -> [X-A-2-B-CARVE-WITH-ITS](todo/open/X-A-2-B-CARVE-WITH-ITS.md) <!-- item:open/X-A-2-B-CARVE-WITH-ITS -->

- [x] **FIVE MORE NON-ATOMIC PUBLISHES INTO THE SHARED openMSX TREE, AND NO GATE WOULD SEE A SIXTH.** -> [X-FIVE-MORE-NON-ATOMIC-PUBLISHES-INTO](todo/done/X-FIVE-MORE-NON-ATOMIC-PUBLISHES-INTO.md) <!-- item:done/X-FIVE-MORE-NON-ATOMIC-PUBLISHES-INTO -->

- [ ] **A 4 B DUP-SPAN THE D-ONLIST FIX CREATED, AND ITS OWN KNIFE FOUND IT.** -> [D-ONLIST](todo/open/D-ONLIST.md) <!-- item:open/D-ONLIST -->

- [x] **`KEY n,"str"` AND `KEY LIST` ARE UNIMPLEMENTED — A WELL-FORMED STATEMENT IS `Syntax error` HERE AND SILENT...** -> [X-KEY-N-STR-AND-KEY-LIST](todo/done/X-KEY-N-STR-AND-KEY-LIST.md) <!-- item:done/X-KEY-N-STR-AND-KEY-LIST -->

- [x] **D-TODOSWEEP'S OWN ELEVEN PROBES RE-IMPLEMENT THE `[...]` READER, WHICH IS THE TRAP THE ITEM BELOW DESCRIBES.** -> [D-TODOSWEEP](todo/done/D-TODOSWEEP.md) <!-- item:done/D-TODOSWEEP -->

- [x] **A TRACKED `scratchpad/` SCRIPT CAN HARDCODE THE AUTHOR'S ABSOLUTE PATH, AND NOTHING CHECKS IT.** -> [X-A-TRACKED-SCRATCHPAD-SCRIPT-CAN-HARDCODE](todo/done/X-A-TRACKED-SCRATCHPAD-SCRIPT-CAN-HARDCODE.md) <!-- item:done/X-A-TRACKED-SCRATCHPAD-SCRIPT-CAN-HARDCODE -->

- [ ] **122 HARDCODED `/tmp/...` LITERALS ARE OUTSIDE THE TEMP ROOT** -> [X-122-HARDCODED-TMP-LITERALS-ARE-OUTSIDE](todo/open/X-122-HARDCODED-TMP-LITERALS-ARE-OUTSIDE.md) <!-- item:open/X-122-HARDCODED-TMP-LITERALS-ARE-OUTSIDE -->

- [x] **ARC: CONTROL FRAMES BELONG IN ONE HIMEM-BOUNDED POOL, NOT THREE FIXED ARRAYS.** -> [X-ARC-CONTROL-FRAMES-BELONG-IN-ONE](todo/done/X-ARC-CONTROL-FRAMES-BELONG-IN-ONE.md) <!-- item:done/X-ARC-CONTROL-FRAMES-BELONG-IN-ONE -->

- [ ] **D-SESSIONS -- TYPED SESSIONS AS INTEGRATION TESTS: THE PROMPT, NOT A LOADED PROGRAM (started 2026-11-06; Jo...** -> [D-SESSIONS](todo/open/D-SESSIONS.md) <!-- item:open/D-SESSIONS -->

- [ ] **D-RECHOLE -- A RANDOM RECORD NEVER WRITTEN READS THE CF-3300'S STALE SECTOR BUFFER, AND BLANKS HERE (found...** -> [D-RECHOLE](todo/open/D-RECHOLE.md) <!-- item:open/D-RECHOLE -->

- [ ] **D-DISKCARVE -- TWO FIXES WAIT ON DISK-ROM BYTES THAT ARE NOT THERE (filed 2026-11-07)** -> [D-DISKCARVE](todo/open/D-DISKCARVE.md) <!-- item:open/D-DISKCARVE -->

- [ ] **THE HARNESS'S WALL TIME HAS A ~5.7 s PERIODIC STALL THAT COSTS ~50 % OF AN EMULATOR GATE — AND IT MUST BE R...** -> [X-THE-HARNESS-S-WALL-TIME-HAS](todo/open/X-THE-HARNESS-S-WALL-TIME-HAS.md) <!-- item:open/X-THE-HARNESS-S-WALL-TIME-HAS -->

- [~] 🕐 **SENTINEL — SHIPPED AS A *STOPWATCH* (`f6bb5a0`); SHIPPED BUT *NOT
      ADOPTED* AS A CAPTURE TRIGGER (`c04606b`).** Both modes exist and are gated;
      what changed is which one is justified.
      🟢 **ADOPTED — the emulated-time stopwatch.** `sentinel=(addr,val)` +
      `settle_out` logs `(emulated instant, value)` for every write the case's own
      BASIC makes, so marks either side of an operation give its EXACT duration,
      on the black-box references too. **Emulated time is DETERMINISTIC** —
      measured bit-identical across repeats (14.736728 s twice, 46.252527 s twice)
      — so this is the only basis on which a performance differential can be gated
      **without flaking**, which wall-clock timing (±0.2 s noise here) can never
      offer. It produced the exact PAINT figures in the item above.
      ✅ **SHIPPED 2026-08-25 (D-SNCAP) — THE REFUSAL IS LIFTED AND THE PAINT
      PHASES CAPTURE ON SIGNAL.** `graphics-acceptance` 216.7 → 186 s solo
      (−14 %), battery **502 → 445 s**, 37/37 green, ROM hashes unchanged.
      🟢 **THE DIFFERENTIAL THAT CARRIES IT** (`scratchpad/sentinel_screen_diff.py`,
      6 rows × 2 machines): **RAW differs on every row** — the `Ok`/`ZB` prompt,
      exactly as the old measurement said, *and that is also the proof the
      sentinel FIRED* — while the **ANSWER after `_points` is identical on every
      row**, with a teeth control (flood `[15,15]` vs box `[7,1]`) so a 0-DIFF
      tally cannot be vacuous. The 2 characters are precisely what `_answer()`
      documents itself as stripping.
      🔬 **AND THE ADOPTION IS FALSIFIABLE, WHICH MATTERS MORE THAN THE 14 %.** A
      case whose sentinel never fires falls back to the budget and passes
      IDENTICALLY, so a green phase proves nothing on its own
      ([[savestate-slice]]). Each converted phase now prints its tally: **28 / 34
      / 52 captured on signal, 0 fallbacks**, in the battery as well as solo.
      🎯 **THE BUDGETS ARE NOW FAILURE DETECTORS**: `PAINT_STEP` = 90 s fires only
      if a case never signals at all. Deterministically the captures land at
      **23.2–50.6 emulated s** against that 90 s.
      ⚠️ **PHASE J (PAINT errors) IS DELIBERATELY NOT CONVERTED** — a case that
      raises never reaches its `POKE`. Measured, not assumed: an `ONERRORGOTO` row
      falls back (`fallback 113.0 s`) and saves nothing. That is the intended
      backstop.
      ✅ **EXTENDED TO EVERY BOOT-PER-CASE PHASE (2026-08-25): 321 captures on
      signal, 0 fallbacks**, `graphics-acceptance` PASS, battery 37/37 at 452 s,
      ROM hashes unchanged. Phases A, C, E, G, I, K, N, P, Q1, Q3, R joined
      H/H-V/H-MC. `paint_mark()` handles all four program shapes this module
      produces — a `:END` readout, a `GOTO`-self hold (renumbered so the hold
      stays self-referential and the poke runs ONCE), a program that runs off its
      end, and a two-exit `ON ERROR` case which is marked on **BOTH** paths.
      🔬 **THE CHECK THE TALLY CANNOT MAKE**: a fallback proves a mark was never
      REACHED, but nothing in the tally would catch a mark placed too EARLY —
      that would capture a half-finished machine on both sides and could agree
      wrongly. So each conversion round was verified by diffing all **395 row
      values** against the previous run: byte-identical every time.
      ⛔ **THE 8 BATCHED PHASES ARE DELIBERATELY NOT CONVERTED** (B, D, F, J, L,
      M, O, Q2). With one boot per matrix the later cases are scheduled at FIXED
      emulated instants and the generated Tcl only exits early on the LAST case,
      so capturing early reclaims nothing there. PHASE J additionally cannot
      work: its programs raise, so they never reach a `POKE`.
      📏 **AND CONVERTING THE SMALL BUDGETS BOUGHT NO WALL, MEASURED**: the
      90 s/30 s/25 s phases went 186 → 184 s. The remaining phases run at the
      2.5 s default and were converted for the FAILURE-DETECTOR property and
      uniformity, not for speed — stated so nobody reads a performance claim into
      them later.
      ✅ **EXTENDED TO SIX MORE GATES (2026-08-25, D-SNCAP2): 1344 captures on
      signal, 1 fallback**, `penderr` / `screenerr` / `stmtpend` / `tmfp` /
      `lineerr` / `deffn-strict`, all 6/6 green, ROM hashes unchanged. The
      plumbing moved to **`probes/lib/probe_signal.py`** (address, kwargs,
      tally) so it is no longer copy-pasted; `basic_probe_graphics.py` delegates
      to it and its `paint_mark()` — the part that is NOT shareable, because
      where the mark goes is the only part that can be silently wrong — stays
      local. See `docs/spec-probe-mark.md`.
      🔬 **VERIFIED THE ONLY WAY THAT HAS TEETH: 557 report rows across 13
      reports, byte-identical before vs after** (`scratchpad/sncap/rowdiff.py`,
      itself teeth-checked against a mutated log).
      🎯 **THE DETECTOR EARNED ITS KEEP ON ITS FIRST RUN.** `deffn`'s
      `o.clearwipe3` never signalled — its `CLEAR` wipes the `ON ERROR` handler
      along with the DEF FN table, so the row aborts UNTRAPPED and reaches
      neither `END`. Its reading is unchanged and correct; the tally is the only
      thing in the tree that could have said so. 🔴 **AND THE FIRST TALLY COULD
      NOT NAME IT** — it printed `1 fell back` out of 72 and the gate had to be
      re-run to find out which row. `Tally.add(label=...)` now names them: an
      unnamed outcome reads as no outcome.
      📏 **THE DETERMINISTIC COST/BENEFIT, COMPUTED NOT TIMED**
      (`scratchpad/sncap/emutotal.py` reads `_tcl`'s own generated timeline, no
      emulator): **71 104 → 63 927 emulated s, −10.1 %** over the six gates ≈
      **21 s of wall** at §5's measured 0.003 s/emulated s. 🔴 **NO WALL CLAIM IS
      MADE AND NONE CAN BE**: the emulator-free warm-up control moved **7 s →
      14 s** between the before and after batteries, and two converted runs of
      the same battery differed by **59 s** — both an order of magnitude above
      the effect. Measured signal instants land within **0.1–0.7 emulated s** of
      the computed `t_run` floor, so the old budgets were pure idle.
      ⚠️ **`screenerr` IS THE OUTLIER AT −5.1 %, AND THE REASON IS THE MARK
      ITSELF.** `POKE&HE000,255` pushes its line 50 from 36 to 51 characters,
      past the 38-char KEYBUF chunk boundary, buying an extra typing slot that
      gives back half the reclaim. A mark is BASIC TEXT and text is not free.
      ⛔ **STILL UNCONVERTED, AND EACH FOR A STATED REASON.** `array`, `math`,
      `float` and every other `batch=True` matrix (rule 1 — capturing early
      reclaims nothing in a shared boot). `interval-trap-acceptance` does not go
      through `run_cases` at all and its subject IS emulated timing. The
      untrapped/cold rows of the six converted suites (rules 2 and the
      `screen_tail` prompt burden). `deffn`'s five `ADDR` rows (rule 3).

      🟢 **DECIDED 2026-08-25 (user): ADOPT IT FOR SCREEN CAPTURES TOO —
      *"even if we verify via a screenshot, a sentinel still makes sense"*.** The
      refusal below was measured but it was WEIGHED WRONG, and the item may not
      keep quoting the measurement as if it settled the question.
      ✅ **DONE 2026-08-25 — the refusal was lifted, both graphics and six more
      gates adopted it, and `probes/lib/probe_signal.py` carries the burden that
      replaced it. The block below is the record of what the refusal SAID; read
      it as history, not as current behaviour.**
      ⏸️ **~~IMPLEMENTED, GATED, NOT YET ADOPTED~~ — `sentinel_capture=True`.** It
      makes the budget a pure failure detector and measures 1.1 s → 0.2 s with the
      capture byte-identical. It is currently refused for `capture="screen"`, and
      that refusal is MEASURED, not caution: the sentinel fires before the
      interpreter prints its `Ok`/`ZB` prompt, and text captures differed by
      exactly those 2 characters on all three machines. **Every PAINT-phase case
      in `graphics-acceptance` is a screen capture whose program `END`s** — i.e.
      exactly that shape.
      🔴 **AND THOSE 2 CHARACTERS ARE THE ONE THING EVERY TEXT READOUT ALREADY
      THROWS AWAY.** `basic_probe_graphics.py`'s `_answer()` says so in its own
      docstring — *"the trailing BASIC prompt / 'Ok' / 'No RESUME' text (which
      differs per machine) is ignored"* — and `_points` is built on it. A capture
      taken BEFORE the prompt is not a degraded reading of the same screen, it is
      the screen WITHOUT the machine-specific noise the readouts exist to strip,
      and `screen_tail` terminating AT the prompt is a property of the
      TERMINATOR, not evidence that the reading is wrong. The real argument for
      the sentinel was never the 0.3 s: it is that **a fixed-time budget captures
      a half-finished machine and a partial result reads as SEMANTICS**, and that
      hazard is identical whether the capture is text or VRAM.
      ~~To pick up: lift the `capture="screen"` refusal in `omsx_repl`, prove each
      phase's readout is prompt-independent (assert the sentinel-captured and
      fixed-time answers are equal AFTER `_answer`, not before), then adopt
      per-phase behind that differential with a teeth control.~~ ✅ **ALL THREE
      DONE** — refusal lifted, `sentinel_screen_diff.py` for graphics and
      `scratchpad/sncap/rowdiff.py` (557 rows) for the six error-shaped gates.
      ⛔ BLOCKED — neither of us can start it now (needs an idle host).

- [ ] **CAPTURE ON A `done` SENTINEL** -> [X-CAPTURE-ON-A-DONE-SENTINEL](todo/open/X-CAPTURE-ON-A-DONE-SENTINEL.md) <!-- item:open/X-CAPTURE-ON-A-DONE-SENTINEL -->

- [ ] **KEY / STRIG / SPRITE / STOP were NOT run against the D-TRAPSVC rows.** -> [D-TRAPSVC](todo/open/D-TRAPSVC.md) <!-- item:open/D-TRAPSVC -->

- [ ] **AN UNNAMED OUTCOME READS AS NO OUTCOME, AND THE FIX MOVES THE HOLE ONE MESSAGE ALONG.** -> [X-AN-UNNAMED-OUTCOME-READS-AS-NO](todo/open/X-AN-UNNAMED-OUTCOME-READS-AS-NO.md) <!-- item:open/X-AN-UNNAMED-OUTCOME-READS-AS-NO -->

- [x] **`CLEARPOOL=0` IS UNTESTED AND CANNOT BE ADDED TO `switch-build-check`.** -> [X-CLEARPOOL-0-IS-UNTESTED-AND-CANNOT](todo/done/X-CLEARPOOL-0-IS-UNTESTED-AND-CANNOT.md) <!-- item:done/X-CLEARPOOL-0-IS-UNTESTED-AND-CANNOT -->

- [x] **NO GATE READS THE BOOT BANNER, AND D-MISSOPFIX MOVED IT.** -> [D-MISSOPFIX](todo/done/D-MISSOPFIX.md) <!-- item:done/D-MISSOPFIX -->

- [ ] **A RULE WITNESSED ONLY BY A DEFERRED ERROR IS WITNESSED BY NOTHING — and one shipped guard was in exactly...** -> [X-A-RULE-WITNESSED-ONLY-BY-A](todo/open/X-A-RULE-WITNESSED-ONLY-BY-A.md) <!-- item:open/X-A-RULE-WITNESSED-ONLY-BY-A -->

- [ ] **DEF FN's knife roster is EIGHT, and eight is a candidate roster, not a verdict.** -> [X-DEF-FN-S-KNIFE-ROSTER-IS](todo/open/X-DEF-FN-S-KNIFE-ROSTER-IS.md) <!-- item:open/X-DEF-FN-S-KNIFE-ROSTER-IS -->

- [ ] **`clone_scout` prices LABEL-BLOCKS, so a routine split by an interior label is priced at a fraction of its c...** -> [X-CLONE-SCOUT-PRICES-LABEL-BLOCKS-SO](todo/open/X-CLONE-SCOUT-PRICES-LABEL-BLOCKS-SO.md) <!-- item:open/X-CLONE-SCOUT-PRICES-LABEL-BLOCKS-SO -->
- [ ] **D-DUPSPAN2 shipped 28 aliases with NO per-site row set.** -> [D-DUPSPAN2](todo/open/D-DUPSPAN2.md) <!-- item:open/D-DUPSPAN2 -->

- [ ] **A probe with an honest `rc` that NO battery collects is not an oracle.** -> [X-A-PROBE-WITH-AN-HONEST-RC](todo/open/X-A-PROBE-WITH-AN-HONEST-RC.md) <!-- item:open/X-A-PROBE-WITH-AN-HONEST-RC -->

- [x] **`DEF FN`: two formals of ONE call can alias, and no row separates it.** -> [X-DEF-FN-TWO-FORMALS-OF-ONE](todo/done/X-DEF-FN-TWO-FORMALS-OF-ONE.md) <!-- item:done/X-DEF-FN-TWO-FORMALS-OF-ONE -->

- [x] **`DEF FN`: a STRING formal's shadow slot is not a GC root.** -> [X-DEF-FN-A-STRING-FORMAL-S](todo/done/X-DEF-FN-A-STRING-FORMAL-S.md) <!-- item:done/X-DEF-FN-A-STRING-FORMAL-S -->

- [x] **THE GENERIC ERROR-LAYER SEAM: per-verb error checks that duplicate a layer that already exists — a carve AN...** -> [X-THE-GENERIC-ERROR-LAYER-SEAM-PER](todo/done/X-THE-GENERIC-ERROR-LAYER-SEAM-PER.md) <!-- item:done/X-THE-GENERIC-ERROR-LAYER-SEAM-PER -->

- [x] **zerobas does NOT implement the `PLAY(n)` FUNCTION (background-queue status).** -> [X-ZEROBAS-DOES-NOT-IMPLEMENT-THE-PLAY](todo/done/X-ZEROBAS-DOES-NOT-IMPLEMENT-THE-PLAY.md) <!-- item:done/X-ZEROBAS-DOES-NOT-IMPLEMENT-THE-PLAY -->

🔬 **D-CFARCH (2026-09-15) — HOW THE CF-3300 ACTUALLY WIRES DISK BASIC, OBSERVED
RATHER THAN GUESSED.** Joost asked for this directly: *"I'd expect most if not all
of disk basic to be in the disk rom, and installed via the hooks"*, then *"do a
thorough investigation how the 3300 actually handles this first, lets get rid of
guesses and faulty invented implementations"*.
⚠️ **THE LINE THIS STAYS ON IS THE ONE `expansion-protocol.md` §2 ALREADY DREW**: a
claimed hook cell holds `F7 <slot> <lo> <hi> C9`, and reading it is allowed
practice — §2 records exactly such a dump — while the target addresses are *"an
internal detail of the reference ROM"* we note and never call. **NO INSTRUCTION OF
THE REFERENCE IS READ OR RECORDED. This is not a disassembly.**
🟢 **THE CENSUS — 35 CLAIMED CELLS, AND NOT ONE EXCEPTION**
([`scratchpad/cf3300_arch_probe.py`](scratchpad/cf3300_arch_probe.py), the whole
`$FD9A`–`$FFCF` hook area read through the debugger):
| | |
|---|---|
| claimed cells | **35** |
| slot byte | **`$87` on all 35** — expanded slot 3-1, the disk ROM |
| entry page | **PAGE 1 (`$4000`–`$7FFF`) on all 35** |
| tail byte | **`C9` (RET) on all 35** |
🎯 **SO JOOST IS RIGHT, 35 FOR 35: EVERY Disk-BASIC HANDLER LIVES IN THE DISK ROM
AND IS REACHED THROUGH A HOOK.** None in page 0, none in another slot, no RAM
stubs, no exceptions to the idiom.
🔴 **AND IT CORRECTS THIS TREE'S OWN EARLIER NUMBER.** D-NODISKDEN reported **27**
claimed cells; that came from a BASIC `PEEK` sweep whose output was a single
screen line and was **TRUNCATED**. The debugger reads memory directly and finds
35. ⚠️ A census taken through the SCREEN is bounded by the screen.
🔬 **THE BEHAVIOURAL HALF, BECAUSE THE CENSUS CANNOT SAY WHETHER THEY CALL BASIC
BACK** — and a handler that evaluates an expression must reach the interpreter
somehow, whatever the mechanism:
| case | CF-3300 | |
|---|---|---|
| `FROG` | ERR 2 | control — an unknown word IS a Syntax error |
| `FILES"*.BAS"` | ERR 70 | baseline |
| **`FILES 5`** | **ERR 13** | **Type mismatch, NOT Syntax error → it EVALUATED and type-checked** |
| **`A$="A":FILES A$+"B"`** | **ERR 70** | the CONCATENATION was evaluated, then the medium failed |
| `KILL 5`, `NAME 5 AS "B"` | ERR 13 | the same face |
❌ **AND THAT IS AS FAR AS IT GOES — AN EARLIER DRAFT OF THIS ENTRY OVERCLAIMED
AND JOOST CAUGHT IT.** It said *"therefore the handlers call back into the
interpreter across slots — measured, not inferred"*. **It was inferred.** The
Type mismatch is equally consistent with main BASIC evaluating the argument
BEFORE the handler ever runs, which is exactly the shape THIS tree uses
(`fname_expr` main-side, then `chan_gate`).
🔬 **SO THE ORDER WAS MEASURED INSTEAD, BY UN-CLAIMING**
([`scratchpad/whoevals.py`](scratchpad/whoevals.py),
[`whoevals2.py`](scratchpad/whoevals2.py)):
| case | CF-3300 |
|---|---|
| `FILES 5`, hook claimed | ERR 13 |
| **`FILES 5`, `$FE7B` un-claimed (`C9`)** | **ERR 5** |
| `A$="A":FILES A$+"B"` un-claimed | ERR 5 |
| `KILL 5`, `H_KILL` un-claimed | ERR 5 |
| `FILES 5` with the body stubbed `SCF;RET` | ERR 5 |
| `FILES 5` with the body stubbed `XOR A;RET` | ERR 5 |
🟢 **WHAT THAT DOES ESTABLISH, NARROWLY**: BASIC consults the hook's
EXISTENCE before evaluating the argument. If evaluation came first, an un-claimed
hook would still raise Type mismatch on `FILES 5`; it raises Illegal function
call instead.
❌ **AND WHAT IT DOES *NOT* ESTABLISH — JOOST CAUGHT THIS TOO, AND THE SECOND
EXPERIMENT WAS WORTHLESS.** He proposed: *"it could check if the hook exists, if
not give err 5, if it exists, evaluate and then call hook"*. That design produces
**every reading in the table above**. The `SCF;RET` / `XOR A;RET` stubs were meant
to be "a handler that returns immediately having done nothing" — but they poked
**byte 0, which IS the `F7` CALLF SIGNATURE**, so the cell stopped looking like a
hook at all and the existence check failed exactly as the `C9` case does. **They
measured nothing new.**
⚠️ **AN EXPERIMENT THAT BREAKS THE SIGNATURE CANNOT TEST THE HANDLER** — which
is what made the second one worthless, and what the third one fixes.
🔬 **THE EXPERIMENT THAT DISCRIMINATES** ([`scratchpad/whoevals3.py`](scratchpad/whoevals3.py),
control in [`whoevals4.py`](scratchpad/whoevals4.py)): keep byte 0's `F7` CALLF
signature and redirect ONLY the slot and address, so the cell still LOOKS claimed
while the TARGET is a `RET` we control. Two measured facts make it buildable
without touching the reference's code — the page-3 RAM slot in CALLF encoding is
**`$83`** (from `A8 = $FC` and `$FFFF` read inverted: page 3 = slot 3-0, slot 3
expanded), and **`$FFCF` — `H_ZKEY`, which the CF-3300 provably does NOT claim —
already holds `C9 C9 C9`**, because an unclaimed hook IS a `RET`.
🔴 **THE READ-BACK CONTROL, WITHOUT WHICH NONE OF IT COUNTS** (a knife can be
silently inert): cell `$FE7B` read `247 135 136 110 201` before and
**`247 131 207 255 201`** after — `F7 83 $FFCF C9`, exactly as intended — and the
target read `201 201`.
| case (cell signature INTACT) | CF-3300 |
|---|---|
| `FILES 5`, unredirected | ERR 13 |
| **`FILES 5`, target redirected to a RAM `RET`** | **ERR 5** |
| `FILES"*.BAS"`, same redirect | ERR 5 |
| `FILES 5`, target `SCF;RET` | ERR 5 |
| `FILES 5`, target `XOR A;RET` | ERR 5 |
🟢 **SO THE HOOK IS *CALLED*, NOT INSPECTED.** If BASIC merely read the cell's
bytes, a signature-valid `F7 83 …` would have passed and evaluation would have
followed. The outcome tracks WHAT THE TARGET DOES, not what the cell LOOKS LIKE.
🟢 **AND THE ARGUMENT IS NOT EVALUATED BEFORE THAT CALL** — with a do-nothing
handler, `FILES 5` never reaches its Type mismatch. **The handler is entered
BEFORE the argument is evaluated**, so control has crossed into the disk ROM
first, whatever ultimately does the evaluating. That refutes *"check if the hook
exists, evaluate, then call the hook"* as stated.
🟢 **ANSWERED 2026-09-15 (D-CFEVAL): THE HANDLER DOES *NOT* EVALUATE THE
ARGUMENT — IT CALLS BACK INTO MAIN BASIC, AND THAT CODE EVALUATES AND
TYPE-CHECKS.** Traced with a breakpoint on the inter-slot stub in RAM, the
instrument Joost proposed.
🎯 **THE DISCRIMINATOR IS THE STACK POINTER.** The stub at `$F38C` switches
page 1 IN to the disk ROM at `SP=DB85`, then switches it back OUT to slot 0 at
**`SP=DB79` — TWELVE BYTES DEEPER**. A return unwinds; a deeper frame is a CALL.
The handler's own frame is still live underneath it.
🔬 **AND THE CALL-BACK IS DOING THE EVALUATION, BY ITS OWN FOOTPRINTS**: inside
it, with page 1 = slot 0, `KBUF $F421..$F423` and `A$`'s variable entry are read
**at the same PCs the control `PRINT A$+".BAS"` uses**. `FILES 5` raises its Type
mismatch inside that call-back, and between switch-in and call-back the disk ROM
read **no** byte of the argument. Bare `FILES` skips the call-back entirely and
goes straight to the disk.
🔴 **CONTROLS, ALL ABLE TO FAIL AND ALL HELD**: `PRINT 1` → zero inter-slot
events; `FROG` → only the error hook; `PRINT A$+".BAS"` → no `H_FILE`, no slot
switch. The instrument demonstrably CAN see disk-ROM reads (it catches them
reading a staged name later), so the ABSENCE of disk-ROM reads of the expression
is a reading, not blindness. The stub's address was found EMPIRICALLY (the only
non-hook RAM code executed during a statement) rather than recalled.
📍 **SO THE FULL ORDER ON THE REFERENCE IS**: BASIC calls the hook → the disk
ROM's handler is entered → it CALLS BACK into main BASIC across slots to evaluate
the argument → control returns into the disk ROM → the disk work happens.
💰 **WHICH SETTLES THE ARCHITECTURAL QUESTION FOR US: AN INTER-SLOT CALL FROM
THE DISK ROM BACK INTO MAIN PAGE 1 IS NOT EXOTIC, IT IS WHAT THE REFERENCE DOES ON
EVERY ARGUMENT.** D-VERBCLASS's **STAY 155 B** is therefore a PRICE and not a
wall — it was measured under the SUB ROM's "no main-page-1 escape" rule, which the
DISK ROM is not bound by.
⛔ **STILL UNRESOLVED, AND DELIBERATELY NOT RECORDED**: WHICH routine the call-back
enters in slot 0 (an internal address of the reference); how the disk ROM reaches
the stub without passing `$0030`/`$001C`; and who writes the staged name. None
changes the answer.
🔴 **AND THE INVESTIGATION VOIDED ONE OF ITS OWN PROBES, WHICH LANDS ON AN EARLIER
READING OF MINE TOO: AT t=22 s THE CF-3300 IS STILL AT THE DISK ROM'S "Enter date"
PROMPT.** `scratchpad/cf_stubfind.py` typed into that prompt and saw page 1
permanently in slot 3-1; it is kept as the recorded blind instrument. **That is
also why my own slot trace read `A8 = $FC` with page 1 in slot 3** — it was
sampling the disk ROM's prompt, not BASIC. ✅ The 35-cell census was RE-RUN at
t=40 s and is unchanged (35 cells, all slot `$87`, all page 1), because the hooks
are installed at INIT before the prompt.
🔴 **AND THE OBVIOUS INSTRUMENT FOR IT IS BLIND — RECORDED SO NOBODY REBUILDS
IT.** Tracing the slot registers during `FILES 5` looked decisive: if the handler
reaches main BASIC, page 1 must leave the disk ROM's slot and come back. It
cannot be seen that way. `H.TIMI` is itself hooked to the disk ROM, so it must be
silenced first (`POKE $FD9F,201`) or every VBLANK floods the log — that part
works. The killer is that **slot 3 is EXPANDED**, so page 1's real selection lives
in the SECONDARY register at `$FFFF`, and a write there hits the
slot-expansion register rather than memory: openMSX's `write_mem` watchpoint never
fires on it. Measured: **508 writes to `$A8` with page-1 primary constant at 3,
and ZERO writes seen at `$FFFF`** — an instrument blind to exactly the switch it
was built to watch.
🔭 **THE INSTRUMENT THAT SHOULD WORK (Joost's suggestion): BREAK ON THE
INTER-SLOT CALL STUB IN RAM.** It lives in the documented work area — RAM, not the
reference's ROM — and every `CALLF`/`CALSLT` passes through it carrying the target
slot and address, so the call graph falls out directly. ⚠️ Three conditions:
FIND the stub's address empirically rather than from memory; silence `H.TIMI`
first; and give it a CONTROL THAT CAN FAIL — `FROG` and a plain `PRINT` must
produce no traffic to slot 3-1, or the log is measuring something else. **And what the "I handled it" signal IS: it is NOT CARRY**, since
`SCF;RET` and `XOR A;RET` both behaved exactly like an unclaimed cell. Settling
either needs tracing, which is disassembly-adjacent and not done here.
🎯 **AND THE ORDERING IS THE PART THAT WAS ACTIONABLE ANYWAY — WE ALREADY
MATCH IT.** `ex_fil_gate`, `ex_kill` and `ex_name` all call `chan_gate` BEFORE
`fname_expr`/`fname_fcb`, so zerobas gates on the hook and then evaluates, in the
same order the reference demonstrably uses.
⛔ **WHAT IS STILL UNKNOWN, AND IS LEFT UNKNOWN RATHER THAN GUESSED**: WHICH BIOS
entry they use to get there (`CALBAS $0159`, `CALSLT $001C`, or another). That is
not observable without disassembly, so it is not claimed.
📐 **WHAT IT MEANS FOR US.** Our disk ROM already calls main BASIC — but every
code address in `disk/basic-resident-abi.inc` is **below `$4000`**
(`widen_rhs_operand $3900`, `round_single_and_pack $343B`,
`round_and_finalize $33E1`), i.e. page 0, which stays mapped. The verbs need
`str_eval $49EE` and `var_find_typed $4853`, both **main page 1**. So hosting verb
bodies in `disk.rom` needs an inter-slot call back into BASIC — the thing the
reference demonstrably does and **zerobas has never done in that direction**
(`grep` finds CALSLT only main→disk).
⚠️ **AND THAT RE-PRICES D-VERBCLASS.** Its **STAY 155 B** bucket meant *cannot
move* under the sub-ROM's "no main-page-1 escape" rule. The DISK ROM is not bound
by that rule, so for this architecture the bucket means *cannot move WITHOUT an
inter-slot call* — a PRICE, not a wall, and an unmeasured one. **The 36 B figure
rung 3 was parked on was measuring the wrong thing for the architecture Joost is
describing.**
🙋 **NEEDS-JOOST — the next measurement is what one argument evaluation costs from
`disk.rom`, in BYTES at the call site and in TIME**, with one verb as the probe.
That number decides whether "most of Disk BASIC in the disk ROM" is reachable or
only correct-in-principle. ⚠️ This machine is already a flat ~3x slower than the
reference, so per-argument inter-slot overhead is a real cost, not a rounding
error.

⚡ **D-TAPEVERB (2026-09-15) — ONE OF THE SIX UNASKABLE VERBS IS NOW ASKED, AND
THE OTHER TWO TURN OUT TO NEED A DIFFERENT INSTRUMENT FOR A REASON THIS TREE
SHIPPED ITSELF THIS MORNING.**
🎯 D-NODISKDEN left `SAVE`/`BLOAD`/`BSAVE` out of the diskless denominator because
with no disk ROM a bare `SAVE"X"` is a **CASSETTE** save and waits on the tape
motor — it blocked the VG-8020 and poisoned nine later cases.
🟢 **THE BLANK-TAPE RIG UNBLOCKS THE DECK** (`cassetteplayer new <path>`, the same
prologue `NEEDS-BLANKTAPE:` uses) **and `BSAVE` is now measured on three sides and
AGREES**: VG-8020 runs, zerobas-NODISK runs, CF-3300 answers ERR 5. Controls green
(`FROG` → Syntax error, `FILES` → 5/70/5).
🔴 **BUT `SAVE` AND `BLOAD` ARE NOT A WINDOW PROBLEM, AND THREE WINDOWS PROVED
IT.** At `step=8` the reference read nothing; at 30 it reached `Ok`; at **60** it
still reached `Ok` and **never printed the fence**. That is not the capture
closing — **`SAVE` ENDS THE RUN**, which is exactly the behaviour **D-KWSAVEEND
shipped earlier the same day**, so a `PRINT` after it is unreachable BY
CONSTRUCTION. `BLOAD` against a tape with no matching file never returns either.
🎯 **SO THEIR READING MUST COME FROM THE TAPE, NOT FROM A MARKER PRINTED
AFTERWARDS** — `basic_probe_kwsweep.py`'s `NEEDS-BLANKTAPE:` rig already decodes
the recording, and that is the instrument these two need. The probe now carries
only what its shape can honestly measure, with the reason written where the two
missing cases used to be.
⚠️ **AND THE FIRST CUT WOULD HAVE CALLED IT A DIVERGENCE**: at `step=8` zerobas
read `<X>` for all three while the reference read nothing, which is the
`step`-window trap wearing a divergence's clothes for the second time today.

⚡ **D-DSKOHOOK (2026-09-15) — `H_DSKO` WAS THE WRONG ADDRESS IN BOTH FILES, AND
THAT IS EXACTLY WHY NOTHING WENT RED.**
🎯 **THE CONTRADICTION WAS SITTING IN THE TREE.** `basic/sysvars.inc` said
`H_DSKO equ $FDF4`; `disk/docs/expansion-protocol.md` §2's own hook table says
`$FDEF`. The CF-3300's claimed-cell census (D-NODISKDEN) showed `$FDEF` claimed
and `$FDF4` **not** — the one equate we name that the reference does not claim.
🔬 **SETTLED BY UN-CLAIMING, NOT BY READING** (`scratchpad/hookid_probe.py`'s
method: `POKE <cell>,201` is a bare `RET`, which is what an unclaimed hook IS):
| poke | `DSKO$ 0,0` on the CF-3300 |
|---|---|
| nothing (control) | ERR 70 |
| `H_FILE $FE7B` + `FILES` (method control) | ERR 5 |
| **`$FDEF`** | **ERR 5** — DSKO$ notices |
| `$FDF4` | ERR 70 — nothing happens |
🟢 **AND THE OTHER SIX VERB HOOKS WERE VERIFIED THE SAME WAY AND ARE ALL RIGHT**:
`FILE $FE7B`, `KILL $FDFE`, `NAME $FDF9`, `COPY $FE08`, `DSKI $FE17`,
`DSKF $FE12` — each reads ERR 70 at baseline and ERR 5 with its own cell
un-claimed. Only `DSKO` was wrong. ⚠️ (§2's table is not infallible either: it
calls `$FDF9` *"HSETS / SET statement"* and the machine says that cell is
**NAME**'s.)
🔴 **WHY IT WAS INVISIBLE, AND IT IS THE INTERESTING PART: WE CLAIMED OUR OWN
WRONG ADDRESS ON BOTH SIDES.** `disk/kernel.asm` claims whatever the equate says,
and `chan_gate` consults the same equate — so our BASIC and our disk ROM agreed
with each other and `h.dsko` read `ok` on all three `nodisk-acceptance` sides. It
would only ever have shown with a **FOREIGN** disk ROM, which claims the real
`$FDEF` and leaves `$FDF4` alone: `DSKO$` would have consulted an unclaimed cell
and **refused a verb the machine can do** — breaking the interop
`basic/fat.asm:11` calls *"the NECESSARY PRICE of the universal sector
interface"*.
⚠️ **THE EQUATE IS DEFINED TWICE AND FIXING ONE COPY WOULD HAVE BEEN WORSE THAN
THE BUG.** `basic/sysvars.inc` and `disk/equates.inc` each carry an `H_*` block
and **14 names appear in both**; the BASIC side consults, the disk side claims.
Change one and our own build refuses `DSKO$` outright.
🟢 **SO THE FIX IS BOTH FILES (0 B — an equate) PLUS A GATE THAT MAKES THE DRIFT
IMPOSSIBLE**: `tools/check_hook_equates.py` / `make hook-equate-check`, in the
battery. It does NOT verify addresses — only the reference can say those — it
verifies that the two copies cannot diverge unnoticed, and it REFUSES if it ever
finds zero shared names (a renamed block would otherwise make it silently blind).
📏 Main page 1 free: **3 B**, unchanged (2026-09-15) — an equate costs nothing.

- [ ] **D-FCBSHAPE — ADOPT THE MSX FCB LAYOUT FOR FILE CHANNELS (39 B A CHANNEL OVER THE REFERENCE; UNLOCKS `VARPTR...** -> [D-FCBSHAPE](todo/open/D-FCBSHAPE.md) <!-- item:open/D-FCBSHAPE -->

- [ ] **`PLAY(n)` READ IMMEDIATELY AFTER `PLAY` SEES A REFERENCE TRANSIENT THAT zerobas DOES NOT REPRODUCE.** -> [X-PLAY-N-READ-IMMEDIATELY-AFTER-PLAY](todo/open/X-PLAY-N-READ-IMMEDIATELY-AFTER-PLAY.md) <!-- item:open/X-PLAY-N-READ-IMMEDIATELY-AFTER-PLAY -->

- [ ] **The bare-`jp raise_error` carve family is worth ~2 B, and the reason is worth more than the bytes.** -> [X-THE-BARE-JP-RAISE-ERROR-CARVE](todo/open/X-THE-BARE-JP-RAISE-ERROR-CARVE.md) <!-- item:open/X-THE-BARE-JP-RAISE-ERROR-CARVE -->

- [ ] **A linear predecessor walk stops at `ENDIF` and calls it an instruction.** -> [X-A-LINEAR-PREDECESSOR-WALK-STOPS-AT](todo/open/X-A-LINEAR-PREDECESSOR-WALK-STOPS-AT.md) <!-- item:open/X-A-LINEAR-PREDECESSOR-WALK-STOPS-AT -->

- [x] **`castail-acceptance` VOIDS THE WHOLE BATTERY WHEN A CONTROL FAILS ON THE** -> [X-CASTAIL-ACCEPTANCE-VOIDS-THE-WHOLE-BATTERY](todo/done/X-CASTAIL-ACCEPTANCE-VOIDS-THE-WHOLE-BATTERY.md) <!-- item:done/X-CASTAIL-ACCEPTANCE-VOIDS-THE-WHOLE-BATTERY -->

- [x] **A DATA-ONLY SPAN STILL CONFERS FALLTHROUGH ON WHATEVER FOLLOWS IT** -> [X-A-DATA-ONLY-SPAN-STILL-CONFERS](todo/done/X-A-DATA-ONLY-SPAN-STILL-CONFERS.md) <!-- item:done/X-A-DATA-ONLY-SPAN-STILL-CONFERS -->

- [x] **THE `tools/` SEED ARM IS AN INTERSECTION, NOT AN ASSERTION** -> [X-THE-TOOLS-SEED-ARM-IS-AN](todo/done/X-THE-TOOLS-SEED-ARM-IS-AN.md) <!-- item:done/X-THE-TOOLS-SEED-ARM-IS-AN -->

- [x] **`CSAVE` AND `CLOAD` STILL TAKE A LITERAL FILENAME ONLY, AND THAT IS ✅** -> [X-CSAVE-AND-CLOAD-STILL-TAKE-A](todo/done/X-CSAVE-AND-CLOAD-STILL-TAKE-A.md) <!-- item:done/X-CSAVE-AND-CLOAD-STILL-TAKE-A -->

- [ ] **Two `fat-error` gaps left by the 8-of-8 closure** -> [X-TWO-FAT-ERROR-GAPS-LEFT-BY](todo/open/X-TWO-FAT-ERROR-GAPS-LEFT-BY.md) <!-- item:open/X-TWO-FAT-ERROR-GAPS-LEFT-BY -->
- [ ] **`file:LINE` CITATIONS ARE UNMAINTAINED AND BROADLY ROTTED — ONLY 31% OF THEM WERE STILL CORRECT, AND NO GAT...** -> [X-FILE-LINE-CITATIONS-ARE-UNMAINTAINED-AND](todo/open/X-FILE-LINE-CITATIONS-ARE-UNMAINTAINED-AND.md) <!-- item:open/X-FILE-LINE-CITATIONS-ARE-UNMAINTAINED-AND -->

- [ ] **`basic_probe_kwsweep.py` PRINTS ROWS NO RUNNER CAN PARSE, AND ITS EXIT-2 PATH PRINTS A DIFFERENT TABLE ENTI...** -> [X-BASIC-PROBE-KWSWEEP-PY-PRINTS-ROWS](todo/open/X-BASIC-PROBE-KWSWEEP-PY-PRINTS-ROWS.md) <!-- item:open/X-BASIC-PROBE-KWSWEEP-PY-PRINTS-ROWS -->
- [ ] **`s.fldarymix` IS A GATE ROW NO KNIFE CAN REDDEN, and that is recorded rather than fixed** -> [X-S-FLDARYMIX-IS-A-GATE-ROW](todo/open/X-S-FLDARYMIX-IS-A-GATE-ROW.md) <!-- item:open/X-S-FLDARYMIX-IS-A-GATE-ROW -->
- [x] **A KNIFE RUNNER STILL HAS NO SHARED WAY TO SCOPE A CUT TO ONE ✅** -> [X-A-KNIFE-RUNNER-STILL-HAS-NO](todo/done/X-A-KNIFE-RUNNER-STILL-HAS-NO.md) <!-- item:done/X-A-KNIFE-RUNNER-STILL-HAS-NO -->

- [x] **NOTHING IN 360 ROWS PINS THE TENANT'S `GRPACX` STORE.** -> [X-NOTHING-IN-360-ROWS-PINS-THE](todo/done/X-NOTHING-IN-360-ROWS-PINS-THE.md) <!-- item:done/X-NOTHING-IN-360-ROWS-PINS-THE -->

- [ ] **NINE ACCEPTANCE ROWS STILL NEED A REFUSAL CUT, ONE PER PATH.** -> [X-NINE-ACCEPTANCE-ROWS-STILL-NEED-A](todo/open/X-NINE-ACCEPTANCE-ROWS-STILL-NEED-A.md) <!-- item:open/X-NINE-ACCEPTANCE-ROWS-STILL-NEED-A -->

- [x] **PHASE Q3's CONTROL SHARES ITS SUBJECT'S STATEMENT, SO THE PAIR CANNOT ✅** -> [X-PHASE-Q3-S-CONTROL-SHARES-ITS](todo/done/X-PHASE-Q3-S-CONTROL-SHARES-ITS.md) <!-- item:done/X-PHASE-Q3-S-CONTROL-SHARES-ITS -->

- [x] **ZEROBAS DRAWS ARCS 5–6× SLOWER THAN THE REFERENCE, AND FULL CIRCLES 1.5× FASTER.** -> [X-ZEROBAS-DRAWS-ARCS-5-6-SLOWER](todo/done/X-ZEROBAS-DRAWS-ARCS-5-6-SLOWER.md) <!-- item:done/X-ZEROBAS-DRAWS-ARCS-5-6-SLOWER -->

- [x] **`t.zero` IS BLIND TO A CUT THAT ALSO DISABLES ITS SEED, AND THE PROBE ✅** -> [X-T-ZERO-IS-BLIND-TO-A](todo/done/X-T-ZERO-IS-BLIND-TO-A.md) <!-- item:done/X-T-ZERO-IS-BLIND-TO-A -->

- [ ] **Two type-code namespaces share the value `1`** -> [X-TWO-TYPE-CODE-NAMESPACES-SHARE-THE](todo/open/X-TWO-TYPE-CODE-NAMESPACES-SHARE-THE.md) <!-- item:open/X-TWO-TYPE-CODE-NAMESPACES-SHARE-THE -->

**Apparatus / gate limits (each is a stated limit, not a filed defect)**
      🎚️ OTHER — internal type-code namespaces (architecture)
      🔁 **RULED (Joost, 2026-09-10): stays as classed** — not before TIERS 1–4 unless it
      blocks a keyword tier; still his call when it is picked.
      🤖 AUTONOMOUS — 🏗️ **RULED BY JOOST 2026-10-27**: *"Merge to reference codes"* -- one namespace, the reference's (3 = string in both); see also the D-DEFSTR item below.

- [ ] **THE BATTERY IS NOW 846 s AND EACH EMULATOR UNIT PAYS ITS OWN BOOT — COLLAPSE SUITES THAT SHARE A MACHINE IN...** -> [X-THE-BATTERY-IS-NOW-846-S](todo/open/X-THE-BATTERY-IS-NOW-846-S.md) <!-- item:open/X-THE-BATTERY-IS-NOW-846-S -->

- [ ] **`check_probe_preflight.py` carries the IDENTICAL `SCAN_DIRS`** -> [X-CHECK-PROBE-PREFLIGHT-PY-CARRIES-THE](todo/open/X-CHECK-PROBE-PREFLIGHT-PY-CARRIES-THE.md) <!-- item:open/X-CHECK-PROBE-PREFLIGHT-PY-CARRIES-THE -->
- [ ] **`build/disk.rom` pad-only damage is invisible ON PURPOSE** -> [X-BUILD-DISK-ROM-PAD-ONLY-DAMAGE](todo/open/X-BUILD-DISK-ROM-PAD-ONLY-DAMAGE.md) <!-- item:open/X-BUILD-DISK-ROM-PAD-ONLY-DAMAGE -->
- [ ] **The raw-byte class beyond the dump row has NO mechanical floor, by measurement** -> [X-THE-RAW-BYTE-CLASS-BEYOND-THE](todo/open/X-THE-RAW-BYTE-CLASS-BEYOND-THE.md) <!-- item:open/X-THE-RAW-BYTE-CLASS-BEYOND-THE -->
- [ ] **The INLINE decoded form is measured UNDECIDABLE, and that is a standing hole, not a closed item** -> [X-THE-INLINE-DECODED-FORM-IS-MEASURED](todo/open/X-THE-INLINE-DECODED-FORM-IS-MEASURED.md) <!-- item:open/X-THE-INLINE-DECODED-FORM-IS-MEASURED -->
- [ ] **`lof-acceptance` intermittent oracle drift — two sightings, nothing since.** -> [X-LOF-ACCEPTANCE-INTERMITTENT-ORACLE-DRIFT-TWO](todo/open/X-LOF-ACCEPTANCE-INTERMITTENT-ORACLE-DRIFT-TWO.md) <!-- item:open/X-LOF-ACCEPTANCE-INTERMITTENT-ORACLE-DRIFT-TWO -->

## Phase 1 — committed loader-stub target (✅ closed)

The charter (README) is deliberate: *just enough MSX-BASIC to run the `.BAS` /
binary loader stubs that boot disk and tape games — **not** full-language
compatibility.* That loader-stub target is **complete**:

1. **Loader-stub BASIC** — ✅ done.
2. **Tape transport** (read + write) — ✅ done. `BLOAD"CAS:",R`/`CLOAD`/`LOAD"CAS:"`
   load and `CSAVE`/`SAVE"CAS:"`/`BSAVE"CAS:"` save on-device (tokenised-only SAVE;
   `,A`/ASCII save is a Phase-3 language item).
3. **Disk transport** (read + write) — ✅ done (`disk.rom`; see [`disk/TODO.md`](disk/TODO.md)).
4. **Disk interface standardization ("Phase 1.5")** — ✅ done. `zerobas-BASIC` reaches
   disk files through the **standard `$4010` DSKIO sector interface** (owning the
   FAT12/dir logic loader-side); `zerobas-disk` installs the standard **`HPHYD`→DSKIO**
   hook + a real `GETDPB`, so any standard disk ROM works under zerobas-BASIC **and** a
   real BIOS can drive zerobas-disk. Host + provider + the host-side and Tier-1 provider
   oracles all pass. *(Spike note: the drive-letter loader path is pure PHYDIO/DSKIO —
   the BASIC DEVICE/expansion mechanism is never called — so the basic-side FAT is the
   necessary price of the universal sector interface, not avoidable duplication. See
   [`disk/docs/expansion-protocol.md`](disk/docs/expansion-protocol.md).)*

The one open checkbox under Phase 1.5 — the **Tier-2** provider oracle (a real
DOS/Disk-BASIC *filesystem* host, the only organic `GETDPB` consumer) — is the seam
into the next phase and is carried into **Phase 2** below. Phase 1 is otherwise
closed; the per-item done-record follows further down.

## Status today — three components, two axes

zerobas is three separately-built artifacts, combined only at runtime: `basic/` →
`basic.rom` (cartridge, slot 0 page 1); `tape/` → the zerobas-tape IPS patch
(C-BIOS page 0 cassette signal layer); `disk/` → `disk.rom` (slot 3-1).

| | Device / transport layer | Interpreter statements (basic.rom) |
|---|---|---|
| **Tape** | ✅ read **and** write signal layer (MSX1/2/2+) | ✅ `BLOAD"CAS:",R`, `CLOAD`, `LOAD"CAS:"` load on-device; `CSAVE`, `SAVE"CAS:"`, `BSAVE"CAS:"` write on-device — full read+write parity (tokenised-only SAVE, `,A`/ASCII is Phase 3) |
| **Disk** | ✅ DSKIO + FAT12 + BDOS, read **and** write (differential vs CF-3300 & MSX-DOS 1) | ✅ `BLOAD`/`LOAD`/`RUN`/`SAVE`/`BSAVE` for `"A:"` † |

† `zerobas-BASIC` reaches the disk through zerobas-disk's **private** `bdos_entry`
(published at SYSTEM vector `$F37D`), **not** the standard `$4010` DSKIO sector
interface — so a *foreign* disk ROM does not work under it, and zerobas-disk is not
reachable by real BASIC/DOS. Phase 1.5 (below) closes this by driving standard
DSKIO loader-side and installing the standard `HPHYD` hook provider-side.

Language (Phase 1, done): byte-identical tokeniser (keywords, integer / `&H` /
`&O` constants, `= + - * / \ < >`, `MOD`/`AND`/`OR`/`XOR`/`NOT`), stored
numbered-line programs (`NEW`/`RUN`/edit), control flow (`GOTO`, `GOSUB`/`RETURN`,
`FOR`/`NEXT`, `IF`/`THEN`/`ELSE`, `ON … GOTO`/`GOSUB`, `END`/`STOP`, `CONT` +
Ctrl-STOP), `DATA`/`READ`/`RESTORE`, `POKE`/`PEEK`, `PRINT`, `CLEAR`,
`DEF USR`/`USR`, screen-setup verbs (`SCREEN`/`COLOR`/`CLS`/`WIDTH`/`KEY`),
`LIST`, the memory/I-O primitives (`VPOKE`/`VPEEK`, `OUT`/`INP`, `VARPTR`),
multi-character 16-bit integer vars, minimal string vars for `PRINT`, and the
storage statements above.

## Phase 1 record — committed work (all ✅ done)

➡️ **Moved to [`docs/TODO-done.md`](docs/TODO-done.md) on 2026-08-26** — its preamble says so: 'nothing here is outstanding'.
The record is unchanged there; this heading is kept only so the citations and
the phase narrative above still have somewhere to land.
## Phase 2 — full disk (Disk BASIC integration) — ✅ VERB SURFACE COMPLETE

**Close-out (2026-06-22).** The Disk BASIC verb surface zerobas's current
capabilities can faithfully support is **done and oracle-validated** — sequential
file I/O (`OPEN`/`CLOSE`/`PRINT#`/`INPUT#`/`LINE INPUT#`/`INPUT$`, `MAXFILES`,
`APPEND`), `PRINT USING` (+`PRINT# USING`), file/dir management
(`FILES`/`KILL`/`NAME`/`MERGE`), position/info (`EOF`/`LOF`/`DSKF`), random-access
records (`FIELD`/`GET`/`PUT`/`LSET`/`RSET` + `MKI$`/`CVI`), and `CALL FORMAT` (both
geometries + menu). The whole stack was also proven **host-BIOS-independent** on a
real Philips VG-8020. The in-RAM halves of these verbs now also carry a fast
emulator-free regression (`make unit-test`: `test_tokenise`/`test_field`/
`test_printusing`); the sector-moving halves stay in the openMSX probes.

**Explicitly carried / deferred (not part of "complete"):**
- **Tier-2 provider oracle** (a real MSX-DOS 1 host driving zerobas-disk) — a
  distinct DOS-boot sub-track. **ACTIVE again (2026-06-23):** an earlier "walled by
  policy" call (§8.12) was retracted — it forgot that undocumented disk-ROM entries are
  characterisable by **black-box oracle** (the same discipline that nailed GETDPB), not
  only by published docs. The boot already loads+executes MSXDOS.SYS byte-perfect off
  our `bdos_entry`; the gap is one disk-ROM entry (`$4030`), now under active black-box
  characterisation (oracle built, first contract captured). **Not** writing our own
  MSX-DOS 1 — existing disks drive our clean-room reimplementation of the observed entry
  contract. See below + provider-oracle-scope.md §8.13.
- **`DSKI$` / `DSKO$`** — investigated, **deferred to Phase 3** (obscure CF-3300
  semantics + needs the Phase-3 string heap; see the item below).
- **`MKS$`/`MKD$`/`CVS`/`CVD`** (random-access float conversions) and the float-only
  `PRINT USING` specs — gated on **Phase-3 floating point**.
- **`LOC(#n)`** (unclear sequential semantics) and **`LFILES`** (printer-bound) —
  deferred; observed + documented in PROVENANCE.

A deliberate **charter raise** from loader-stub toward a faithful disk experience.
Chosen as the next phase because it *completes the storage story* the
basic/tape/disk split is built around — a self-contained, oracle-validatable slice
— rather than boiling the ocean on the full language (that stays Phase 3+). The
disk *ROM* (`disk/`) is already complete (FDC + FAT12 + BDOS, read+write,
oracle-confirmed); this phase is the **interpreter-side Disk BASIC integration**.

**Approach — spike first, then decide, then build.** Unlike Phase-1 items the
protocol isn't pinned, so step 0 is a research spike; only after it do we pick the
architecture and write code. Each step is independently oracle-validatable.

### Step 0 — file-channel protocol spike (the gate) — ✅ DONE
      - [x] **read path: `OPEN…FOR INPUT` + `INPUT#` + `LINE INPUT#` + `CLOSE`** —
            DONE (basic/files.asm). EXTEND over the fat.asm sequential reader
            (`fat_io_open`/`fat_io_getbyte`); single channel; string vars only.
            Tokens OPEN=$B0/INPUT=$85/LINE=$AF/CLOSE=$B4 oracle-locked to the
            VG-8020 crunch; `OPEN"HI.TXT"…:LINE INPUT#1,A$:CLOSE#1:PRINT A$` prints
            the file's line byte-for-byte and the **real CF-3300 prints it
            identically** (`disk_probe_fileread.py` differential). See
            basic/PROVENANCE.md §file channel — sequential read.
      - [x] **write path: `OPEN…FOR OUTPUT` + `PRINT#` + `CLOSE`** — DONE
            (basic/files.asm + the PRDEST/`pchar` redirect in basic/print.asm).
            `PRINT#` reuses the screen-PRINT item loop redirected to the channel;
            CLOSE appends the `Ctrl-Z` ($1A) text-EOF marker. Tokens oracle-locked
            (`OUTPUT`→`OUT $9C`+`PUT $B3`, `PRINT#`→$91); write→read-back round-trips
            and the on-disk `OUT.TXT` is **byte-identical to the real CF-3300**
            (`b"hello world\r\n\x1a"`, `disk_probe_filewrite.py` differential). See
            basic/PROVENANCE.md §file channel — sequential write.
      - [x] 🔴 **`MAXFILES` + the multi-channel table** ➡️ *the two-disk-channel residual was a top-level TIER 1 item from 2026-09-10 (D-NESTED) and CLOSED BY MEASUREMENT 2026-09-11 (D-OPEN2: 17 of 18 rows SAME; the one left, `e.same2`, is its own TIER 5 item) — so this record is done too* — **DONE EXCEPT FOR TWO
            OPEN DISK CHANNELS** (measured 2026-08-30, D-OPEN2,
            [`docs/spec-basic-open2.md`](docs/spec-basic-open2.md), 9 DIFF of 13):
            a second concurrent DISK `OPEN` is `Syntax error`. Device+device,
            device+disk and disk+device all WORK, so the table and the ceiling
            are real — it is two open DISK channels that fail, which is what
            fat.asm's single global streaming state predicts. Was marked DONE (basic/files.asm channel
            manager + basic/sysvars.inc FCH_CTX). Retires the single-channel limit:
            up to `FCH_CEIL`(=2) channels open at once, via a **write-back context
            cache** over the UNCHANGED fat.asm (each channel owns a saved
            [state][512-buf] block; the globals hold the active channel; switching
            saves+loads). `MAXFILES` = MAX($CD)+FILES($B7) oracle-locked; default 1;
            bare CLOSE closes all. Two OUTPUT files written **interleaved** produce
            on-disk images **byte-identical to the real CF-3300**
            (`disk_probe_maxfiles.py`). RAM-bounded ceiling (real MSX=15) documented.
            See basic/PROVENANCE.md §MAXFILES.
      - [x] **`OPEN…FOR APPEND`** — DONE (basic/fat.asm `fat_io_append` +
            basic/files.asm OPEN mode parse). Opens an existing file positioned at
            EOF; "APPEND" = APP(ascii)+END($81), already byte-identical (no new
            token). Walks the chain reusing the read primitives, primes the write
            iterator at EOF, and overwrites a trailing Ctrl-Z (CP/M text append).
            On-disk result **byte-identical to the real CF-3300**
            (`disk_probe_append.py`: create "first" + append "second" ->
            `first\r\nsecond\r\n\x1a`). See basic/PROVENANCE.md §OPEN … FOR APPEND.
      - [x] **`INPUT$(n,#f)`** — DONE (basic/strvar.asm `str_eval` INPUT$ branch).
            Reads exactly n raw bytes from channel f as a string (no delimiters;
            cursor advances by n). zerobas's first string-returning function;
            "INPUT$" = INPUT($85)+'$' (no new token). `A$=INPUT$(5,#1)` then
            `INPUT$(6,#1)` on HI.TXT yield "Hello" then " from " **byte-identical to
            the CF-3300** (`disk_probe_inputdollar.py`). STRMAX clamp + keyboard form
            (no `#`) deferred. See basic/PROVENANCE.md §INPUT$.
      - [x] **`PRINT USING`** — DONE (basic/printusing.asm). Formatted output:
            numeric `#` fields (right-justified, `%` overflow, negative sign),
            string fields (`\ \` fixed width, `!` first char, `&` whole), literal
            passthrough, and format reuse when values outrun the template. USING token
            $E4 (oracle-locked). 7 cases incl. `PRINT USING "## ";1;2;3` →
            ` 1  2  3 ` **byte-identical to the real VG-8020** (`basic_probe_printusing.py`).
            This is the COMPLETE feature for zerobas's integer domain; the float-only
            specs (`.` decimal, `^^^^`, `+`/`,`/`**`/`$$`) arrive with Phase-3 floats.
            See PROVENANCE §PRINT USING.
      - [x] **`PRINT# USING`** — DONE (basic/print.asm). The file form: after
            `PRINT #n[,]` the USING token routes into the same ex_print_using formatter
            with PRDEST=1, so the formatted bytes stream to the channel via pchar. On-
            disk round-trip byte-identical to the CF-3300 (disk_probe_printusing_file.py).
            Oracle finding: the CF-3300 (National ROM) supports only `#`/`!` PRINT USING
            fields, not `\..\`/`&` (which the VG-8020 — and zerobas — do); see PROVENANCE.
      - [x] **`MERGE "name"`** — DONE (basic/files.asm `ex_merge`). Reads an ASCII
            (SAVE",A") line-numbered program file and feeds each line through the
            same `dispatch_line` (tokenise + `store_line`) path as a typed line, so
            lines insert/replace into the CURRENT program (kept, unlike LOAD). Token
            $B6 oracle-locked. Build-source-via-PRINT# + MERGE + RUN computes 123
            **identical to the CF-3300** (`disk_probe_merge.py`). ASCII-only (no
            tokenised MERGE). See basic/PROVENANCE.md §MERGE.
      - [x] **`NAME "old" AS "new"`** — DONE (basic/files.asm). Rewrites the dir
            entry's 8.3 name (no FAT change); token $D3 oracle-locked; post-rename
            disk image **byte-identical to the real CF-3300** (`disk_probe_name.py`).
            See PROVENANCE §NAME.
      - [x] **`KILL "name"`** — DONE (basic/files.asm + fat.asm `fat_delete`). Frees
            the FAT chain + marks the dir entry `$E5`; token $D4 oracle-locked; the
            post-KILL disk image is **byte-identical to the real CF-3300**
            (`disk_probe_kill.py`). Single file (no wildcard). See PROVENANCE §KILL.
      - [x] **`FILES`** — DONE (basic/files.asm). Lists the root directory by
            EXTEND over the fat.asm engine (`fat_mount` + directory walk + 8.3 field
            render); width-driven wrap via `CSRX`/`LINLEN`. Token `$B7` oracle-locked
            to the VG-8020 crunch (`basic_probe_crunch.py` case `files`); listing
            **byte-identical to the real CF-3300** at WIDTH 29 and correct at native
            width (`disk_probe_files.py` / `diskbasic_probe_files.py`); LIST detok +
            the host unit-test suite still pass. Divergence: optional `<filespec>`
            pattern parsed-past + ignored (full-dir listing only). See
            basic/PROVENANCE.md §FILES.
      - [x] **`EOF(#n)` + `LOF(#n)`** — DONE (basic/expr.asm `ev_f_ff`). $FF-prefixed
            function tokens ($FF$AB / $FF$AD), oracle-locked; `PRINT LOF(1);EOF(1)`
            after OPEN = `26 0` byte-for-byte vs the real CF-3300, and EOF→-1 once
            the file is exhausted (`disk_probe_eof.py`). See PROVENANCE §EOF / LOF.
      - [x] **`DSKF(d)`** — DONE (basic/expr.asm + fat.asm `fat_count_free`). Free-
            cluster count via a sector-cached FAT scan; $FF$A6 oracle-locked;
            `PRINT DSKF(0)`=707 matches a direct FAT12 count AND the real CF-3300
            (`disk_probe_dskf.py`). See PROVENANCE §DSKF.
      - [x] **`LOC(#n)`** ➡️ *promoted to a top-level TIER 1 item 2026-09-10 (D-NESTED) and SHIPPED 2026-09-11 (D-LOC, `loc-acceptance`, all four rows incl. `t.two` gated); this text stays as its record* — ~~deferred: CF-3300 `LOC(1)` returns 26 (file size) both
            before and after a read; sequential-file semantics unclear, so not
            cargo-culted.~~ **`LFILES`** — printer-bound (LPT), no device in zerobas.
            Both observed + documented in PROVENANCE §LOC / LFILES.
            🟢 **THE SEMANTICS ARE NOT UNCLEAR — MEASURED 2026-09-07 (D-LOCSEM),
            [`scratchpad/loc_probe.py`](scratchpad/loc_probe.py).** The filed
            observation was taken on a SEQUENTIAL file, which is the one case
            where MSX's `LOC` is least legible. On a RANDOM file — where it is
            defined — the CF-3300 is exact:
            | row | case | CF-3300 | zerobas |
            |---|---|---|---|
            | `s.seq` | sequential, LOC before / after 5 B / after 10 B | `26,26,26` | `0,0,0` |
            | `r.get` | random, `GET #1,3` then `GET #1,7` | **`0,3,7`** | `0,0,0` |
            | `w.put` | random, `PUT #1,4` | **`0,4,0`** | `0,0,0` |
            `r.get` reads the RECORD NUMBER exactly, and `w.put` shows the write
            side does too. The sequential column reproduces the filed `26` and
            extends it: it is CONSTANT at the file size across two reads, which
            is a stable rule and not an ambiguity. zerobas reads `0,0,0`
            throughout because it has no `LOC` — `LOC(1)` parses as an array
            reference and auto-dims, which is what the gap looks like from BASIC.
            🎯 **SO THE COST DRIVER IS NOT THE SEMANTICS, IT IS PER-CHANNEL
            STATE.** `ev_ff_lof` ([`basic/expr.asm:1257`](basic/expr.asm:1257)) is
            ~13 B and `LOC` mirrors it — except that the record number lives in
            **`GP_RECNO`, a SINGLE GLOBAL** written once in
            [`basic/field.asm:795`](basic/field.asm:795). A `LOC` built on it is
            right for one open random file and wrong the moment there are two.
            A faithful one needs a per-channel word array plus writes at GET/PUT.
            ⚠️ **ONE ORACLE ONLY.** The VG-8020 is diskless, so no row here can be
            cross-checked between two references.
            ⚠️ **THIS IS A CALL FOR JOOST, AND IT IS NOW A PRICED TRADE RATHER
            THAN AN UNCERTAINTY**: the cheap `LOC` (~15–20 B, correct for one
            open random file) or the faithful one (per-channel state), against
            23 B free in main page 1 (2026-09-07, and it rots). Written as prose
            rather than as a `NEEDS-JOOST` marker on purpose — this is a nested
            sub-item inside a block that already carries its own marker, and a
            second one there reads as an ambiguous item to
            `make todo-marker-check` rather than as a scoped question.
- [x] **Direct sector access — INVESTIGATED, DEFERRED to Phase 3** -> [X-DIRECT-SECTOR-ACCESS-INVESTIGATED-DEFERRED-TO](todo/done/X-DIRECT-SECTOR-ACCESS-INVESTIGATED-DEFERRED-TO.md) <!-- item:done/X-DIRECT-SECTOR-ACCESS-INVESTIGATED-DEFERRED-TO -->
- `CALL SYSTEM` **[out]** — exit to MSX-DOS = the DOS-boot path (Tier-2 sub-track).
- `CALL CHDRV` etc. **[out]** — Disk BASIC v2/v3 additions, beyond DOS1-class 1.0.
      🎯 **RULED (Joost, 2026-09-10): *"DSKI$ DSKO$ should also be implemented"* — no longer
      deferred. TIER 1 (missing keywords).
      🤖 AUTONOMOUS — shipped 2026-09-11 (D-DSKIO); the CF-3300 was the oracle, the VG-8020 the diskless one.

### Carried oracle — Tier-2 provider (DOS1; a distinct DOS-boot sub-track)
The only Phase-2 thread still genuinely open: a real **MSX-DOS 1** filesystem host
(black-box; **DOS1 is the confirmed ceiling**), the only organic `GETDPB` consumer,
driving zerobas-disk end-to-end. Per the circularity finding a real DOS only exists
once a disk ROM loads `MSXDOS.SYS`, so this is gated on building **MSX-DOS-boot
support** in zerobas-disk — a distinct sub-track from the verb surface above. **DOS2**
(Nextor / Sunrise 2.20 / the open MSX-DOS2 kernel) is a future axis, not this phase.

- [ ] **2-Tier2-a — DOS boot (steps 4–7).** -> [X-2-TIER2-A-DOS-BOOT-STEPS](todo/open/X-2-TIER2-A-DOS-BOOT-STEPS.md) <!-- item:open/X-2-TIER2-A-DOS-BOOT-STEPS -->
- [ ] **2-Tier2-b — organic GETDPB.** -> [X-2-TIER2-B-ORGANIC-GETDPB](todo/open/X-2-TIER2-B-ORGANIC-GETDPB.md) <!-- item:open/X-2-TIER2-B-ORGANIC-GETDPB -->
- [ ] **2-Tier2-c — regression.** -> [X-2-TIER2-C-REGRESSION](todo/open/X-2-TIER2-C-REGRESSION.md) <!-- item:open/X-2-TIER2-C-REGRESSION -->

**Charter note.** This raises the README's loader-stub charter toward "real MSX
BASIC" on the disk axis. That is the intended scope of Phase 2 — a conscious step
up, kept narrow to the disk/file story so it stays validatable.
      🎚️ OTHER — DOS Tier-2

### Phase 1 close-out — owed oracles (polish, non-blocking)
      🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).
## Done — Phase 1 (loader-stub BASIC)

➡️ **Moved to [`docs/TODO-done.md`](docs/TODO-done.md) on 2026-08-26** — 'Complete and oracle-validated; kept below as the provenance record'.
The record is unchanged there; this heading is kept only so the citations and
the phase narrative above still have somewhere to land.
## Phase 3+ — full MSX1 BASIC (active charter)

**Precondition solved — BASIC ROM space (the C-BIOS repack arc, ✅ 2026-07-10).** The
page-1 `basic.rom` was byte-full at 16 KB, so any Phase-3 feature would have hit a hard
wall. The repack arc ([`docs/spec-cbios-repack-tooling.md`](docs/spec-cbios-repack-tooling.md))
broke it: dropping C-BIOS's dead ROM-BASIC placeholder frees `$2812–$3FFF` in page 0,
contiguous below page 1, so the relocated BASIC grows to a **`$2812–$7FFF` ≈ 21.5 KB**
window (+37 %). Ships as one merged 32 KB main ROM
([`zerobas-main-eu.ips`](zerobas-main-eu.ips)/`.bps`, boots end to end via `make
repack-boot`) with the firewall proven in
[`docs/cbios-repack-provenance.md`](docs/cbios-repack-provenance.md). Shipping `basic.rom`
+ the page-1/tape patches are untouched (`ROM_BASE` defaults to `$4000`); the grown image
is the reloc build. Non-EU variants (br/jp) are a documented later add.

Beyond Phase 2's disk axis — the rest of "real MSX BASIC." **Charter raised
2026-07-17 from loader-stub to faithful, full MSX1 BASIC** (see the banner in
[`README.md`](README.md) and [`MISSION.md`](MISSION.md)); this section is the
**active work-face**, no longer aspirational. Several arcs have **concluded on
main** — floating point (F1+F2+F3), the string engine, arrays/`DIM`, math pack,
console `INPUT`, error handling, `SOUND`/`PLAY`/`BEEP`, D-F2-2 int-arg coercion —
each with a standing acceptance gate. The remaining unchecked items below are the
open work; the disk/file story (`OPEN`/`CLOSE`/`PRINT#`/…) already landed in
**Phase 2** above.

- [x] **Direct-mode control flow — ✅ DONE 2026-07-26** -> [X-DIRECT-MODE-CONTROL-FLOW-DONE-2026](todo/done/X-DIRECT-MODE-CONTROL-FLOW-DONE-2026.md) <!-- item:done/X-DIRECT-MODE-CONTROL-FLOW-DONE-2026 -->
- [x] **Screen-editor REPL** -> [X-SCREEN-EDITOR-REPL](todo/done/X-SCREEN-EDITOR-REPL.md) <!-- item:done/X-SCREEN-EDITOR-REPL -->
- [ ] **WHAT PROVES A RUNG? T2, T4, T5 AND T6 HAVE NO PROVING ROW TYPE, SO `0 of 159` KEYWORDS PROVE ANY OF THEM (D...** -> [D-KWPROVEN](todo/open/D-KWPROVEN.md) <!-- item:open/D-KWPROVEN -->

- [ ] **T6 — WHAT BOUNDS "THE EXHAUSTIVE ERROR SET"? THE ONE RUNG STILL WITHOUT A DEFINITION (split from D-KWPROVEN...** -> [D-KWPROVEN-2](todo/open/D-KWPROVEN-2.md) <!-- item:open/D-KWPROVEN-2 -->

- [ ] **D-BIOSCONTRACT2 — THE 108 BIOS ROWS ARE WITNESSED; THEIR CONTRACTS ARE NOT ALL COMPARED (filed 2026-11-14 u...** -> [D-BIOSCONTRACT2](todo/open/D-BIOSCONTRACT2.md) <!-- item:open/D-BIOSCONTRACT2 -->

- [ ] **D-DISKCONTRACT — THE DISK ROM'S BIOS-LEVEL ENTRIES AND THE BDOS: WHAT IS COMPARED, NOT ONLY CALLED (filed 2...** -> [D-DISKCONTRACT](todo/open/D-DISKCONTRACT.md) <!-- item:open/D-DISKCONTRACT -->
- [x] **VERIFY ON DOES NOTHING ON ZEROBAS; THE CF-3300 READS BACK EVERY SECTOR IT WRITES (D-VERIFYREAD, found 2026-...** -> [D-VERIFYREAD](todo/done/D-VERIFYREAD.md) <!-- item:done/D-VERIFYREAD -->
- [x] **CTRL-C AND CTRL-P DO NOTHING IN THE BDOS LINE INPUT: THEY ARE STORED AS CHARACTERS (D-BUFINCTL, found 2026-...** -> [D-BUFINCTL](todo/done/D-BUFINCTL.md) <!-- item:done/D-BUFINCTL -->
- [ ] **CTRL-C / CTRL-S DURING CONSOLE OUTPUT, AND THE LINE-EDITING KEYS THROUGH BASIC's $F37D -- NOT MEASURED (D-C...** -> [D-CTLOUTPUT](todo/open/D-CTLOUTPUT.md) <!-- item:open/D-CTLOUTPUT -->
- [x] **BDOS $00 (TERMINATE) THROUGH $F37D RETURNS ON ZEROBAS; ON THE CF-3300 IT ENDS THE BASIC PROGRAM (D-F37DTERM...** -> [D-F37DTERM](todo/done/D-F37DTERM.md) <!-- item:done/D-F37DTERM -->
- [ ] **BDOS $00 THROUGH $F37D: THE REST OF THE CALLING LINE STILL RUNS ON ZEROBAS (D-F37DTERMLINE, filed 2026-11-2...** -> [D-F37DTERMLINE](todo/open/D-F37DTERMLINE.md) <!-- item:open/D-F37DTERMLINE -->
- [ ] **THE DISK ROM PAIRED WITH A FOREIGN BASIC -- a goal, at LOWER priority (Joost 2026-11-26: "this is a goal, b...** -> [D-FOREIGNBASIC](todo/open/D-FOREIGNBASIC.md) <!-- item:open/D-FOREIGNBASIC -->
- [ ] **DISK-ROM ROOM BY RE-READING THE CODE, NEVER BY ADDING ROM SPACE (D-DISKREREAD, Joost 2026-11-26).** -> [D-DISKREREAD](todo/open/D-DISKREREAD.md) <!-- item:open/D-DISKREREAD -->
- [x] **D-NMSHOST — ZEROBAS WITHOUT ITS DISK ROM HOSTS A DISK INTERFACE CARTRIDGE AND RUNS MSX-DOS (the host half o...** -> [D-NMSHOST](todo/done/D-NMSHOST.md) <!-- item:done/D-NMSHOST -->

- [ ] **D-INITEDGES — INITXT / INIT32 / DSPFNK / ERAFNK / FNKSB: THE KEY LINE'S ROW AND MARGINS, R0'S KEPT BITS, TH...** -> [D-INITEDGES](todo/open/D-INITEDGES.md) <!-- item:open/D-INITEDGES -->

- [x] **D-DOSSESSION — MSX-DOS COMMANDS AS TYPED SESSIONS ON THE CF-3300 AND ZEROBAS: THE SCREEN AFTER EACH COMMAND...** -> [D-DOSSESSION](todo/done/D-DOSSESSION.md) <!-- item:done/D-DOSSESSION -->
- [x] **D-COPYDATE — A FILE COPIED UNDER MSX-DOS GETS THE CURRENT DATE ON ZEROBAS; THE CF-3300 KEEPS THE SOURCE'S** -> [D-COPYDATE](todo/done/D-COPYDATE.md) <!-- item:done/D-COPYDATE -->
- [ ] **D-MSX2SPEC — ELEPHANT / GOLDFISH SPEC PAGES FOR THE MSX2 AND MSX2+ BIOS CALLS (THE SUB-ROM AND THE NEW MAIN...** -> [D-MSX2SPEC](todo/open/D-MSX2SPEC.md) <!-- item:open/D-MSX2SPEC -->
- [ ] **D-CBIOSMSX2FIX — FIX C-BIOS'S MSX2 / MSX2+ SUB-ROM WHERE D-MSX2SPEC MEASURED IT WRONG -- POSTPONED** -> [D-CBIOSMSX2FIX](todo/open/D-CBIOSMSX2FIX.md) <!-- item:open/D-CBIOSMSX2FIX -->
- [ ] **D-DOCLINKS — ~3,400 RELATIVE LINKS IN TOP-LEVEL docs/.md AND ~900 IN scratchpad/.md DO NOT RESOLVE FROM T...** -> [D-DOCLINKS](todo/open/D-DOCLINKS.md) <!-- item:open/D-DOCLINKS -->
- [ ] **D-MSX1ON2 — THE MSX1 BIOS CALLS ON THE MSX2 / MSX2+ REFERENCES: SAME CASES, NOT ASSUMED THE SAME ANSWERS** -> [D-MSX1ON2](todo/open/D-MSX1ON2.md) <!-- item:open/D-MSX1ON2 -->
- [ ] **D-TRSPEC — ELEPHANT / GOLDFISH SPEC PAGES FOR THE MSX TURBO R BIOS CALLS** -> [D-TRSPEC](todo/open/D-TRSPEC.md) <!-- item:open/D-TRSPEC -->
- [ ] **D-KWSPEC — ELEPHANT / GOLDFISH SPEC PAGES FOR THE BASIC KEYWORDS** -> [D-KWSPEC](todo/open/D-KWSPEC.md) <!-- item:open/D-KWSPEC -->
- [x] **ENTERING A PROGRAM LINE RESETS RND'S SEQUENCE ON THE VG-8020 (BACK TO ITS POWER-ON START), NOT HERE (D-RNDL...** -> [D-RNDLINE](todo/done/D-RNDLINE.md) <!-- item:done/D-RNDLINE -->
- [ ] **WHEN RND'S STATE IS 0, ITS RESULT IS 8 ZERO BYTES ON THE VG-8020 AND A ZERO WITH LEFTOVER DIGIT BYTES HERE...** -> [D-RNDZERO](todo/open/D-RNDZERO.md) <!-- item:open/D-RNDZERO -->
- [ ] **RND OF A SIGN-BIT ZERO (A SINGLE 80 00 00 00) RESEEDS FROM m = 0 ON THE VG-8020; ZEROBAS TREATS IT AS A ZER...** -> [D-RNDNEGZERO](todo/open/D-RNDNEGZERO.md) <!-- item:open/D-RNDNEGZERO -->
- [ ] **`USR(CSNG(9.999995D62))` RUNS THE USR ROUTINE (VALTYP 8, DAC ZERO) BEFORE ERROR 6 ON ZEROBAS; THE VG-8020 R...** -> [D-CSNGOVERUSR](todo/open/D-CSNGOVERUSR.md) <!-- item:open/D-CSNGOVERUSR -->
- [ ] **CSNG AND CDBL OF A SINGLE WHOSE EXPONENT BYTE IS 0 OR &H80 (DIGIT BYTES LEFT IN IT) KEEP ITS BYTES ON THE V...** -> [D-CONVZERO](todo/open/D-CONVZERO.md) <!-- item:open/D-CONVZERO -->
- [ ] **`MKI$`, `MKS$` AND `MKD$` WITHOUT A PARENTHESIS (`S$=MKI$`) ARE ERROR 24 (MISSING OPERAND) ON ZEROBAS, ERRO...** -> [D-MKNOPAREN](todo/open/D-MKNOPAREN.md) <!-- item:open/D-MKNOPAREN -->
- [ ] **WITHOUT DISK BASIC, `MKI$("A")` / `MKS$("A")` / `MKD$("A")` AND `CVI(5)` / `CVS(5)` / `CVD(5)` ARE ERROR 13...** -> [D-DISKFNTYPE](todo/open/D-DISKFNTYPE.md) <!-- item:open/D-DISKFNTYPE -->
- [x] **`-NOT 0` IS A SYNTAX ERROR ON ZEROBAS; THE VG-8020 EVALUATES IT AS -(NOT 0) = 1 (D-MINUSNOT, found 2026-11-...** -> [D-MINUSNOT](todo/done/D-MINUSNOT.md) <!-- item:done/D-MINUSNOT -->
- [ ] **`A=1:SWAP A,B` WITH NO `B` IS ERROR 5 ON BOTH MACHINES, BUT ZEROBAS HAS CREATED `B` HOLDING A'S VALUE (1);...** -> [D-SWAPNEW](todo/open/D-SWAPNEW.md) <!-- item:open/D-SWAPNEW -->
- [ ] **AFTER A PLAIN POWER-ON, ZEROBAS'S PUBLISHED SYSTEM CELLS DIFFER FROM THE VG-8020'S: FRETOP, AND ~20 MS-BASI...** -> [D-BOOTCELLS](todo/open/D-BOOTCELLS.md) <!-- item:open/D-BOOTCELLS -->
- [ ] **ZEROBAS KEEPS 29 BYTES OF ITS OWN STATE IN BYTES MSX1 LEAVES UNDEFINED ($FAF5-$FB02, $FC88-$FC98), WHERE BO...** -> [D-OWNCELLS](todo/open/D-OWNCELLS.md) <!-- item:open/D-OWNCELLS -->
- [ ] **D-RAMATLAS — A MEASURED ATLAS OF HIGH RAM ($D000-$FFFF): WHO CLAIMS AND WHO WRITES EACH RANGE, AT EACH MOME...** -> [D-RAMATLAS](todo/open/D-RAMATLAS.md) <!-- item:open/D-RAMATLAS -->
- [ ] **D-DISKROMHOST — ZEROBAS'S OWN DISK ROM AS A CONTRACT-FOLLOWING CARTRIDGE: ITS MSX-DOS HALF STANDS ON ITS OW...** -> [D-DISKROMHOST](todo/open/D-DISKROMHOST.md) <!-- item:open/D-DISKROMHOST -->
- [ ] **A CARTRIDGE'S HIMEM CLAIM IS LOST AT BOOT: ZEROBAS BASIC PUTS HIMEM BACK TO $F380 (D-CARTCLAIM, found 2026-...** -> [D-CARTCLAIM](todo/open/D-CARTCLAIM.md) <!-- item:open/D-CARTCLAIM -->
- [ ] **ZEROBAS BASIC IGNORES BOTTOM: A CARTRIDGE'S CONVENTIONAL WORK AREA SITS INSIDE THE PROGRAM TEXT (D-BOTTOMIG...** -> [D-BOTTOMIGN](todo/open/D-BOTTOMIGN.md) <!-- item:open/D-BOTTOMIGN -->
- [ ] **`ABS("A"` (NO `)`) AND `ABS("A",2)` ARE A SYNTAX ERROR (2) ON THE VG-8020 AND A TYPE MISMATCH (13) HERE --...** -> [D-ARGTYPEORDER](todo/open/D-ARGTYPEORDER.md) <!-- item:open/D-ARGTYPEORDER -->
- [ ] **AN EXPONENT-0 ZERO TIMES 3 (`FIX(.5!)3`) IS A DOUBLE ZERO WITH DIGIT BYTES 30 00 ... ON THE VG-8020, EIGHT...** -> [D-ZEROMUL](todo/open/D-ZEROMUL.md) <!-- item:open/D-ZEROMUL -->
- [ ] **NEAR A HALF OR WHOLE TURN, ZEROBAS'S SIN / COS / TAN KEEP MORE OF THE ANGLE THAN THE VG-8020'S 14-DIGIT RED...** -> [D-TRIGHALF](todo/open/D-TRIGHALF.md) <!-- item:open/D-TRIGHALF -->
- [ ] **ZEROBAS'S SINE IS UP TO 6.1 UNITS OF THE 14TH DIGIT OFF THE REDUCED ANGLE'S SINE, WHERE THE VG-8020 STAYS W...** -> [D-SINDIGITS](todo/open/D-SINDIGITS.md) <!-- item:open/D-SINDIGITS -->
- [ ] **THE ZERO RESULTS OF SIN / COS / TAN / EXP / ATN CARRY OTHER DIGIT BYTES HERE THAN ON THE VG-8020 (D-TRANSZE...** -> [D-TRANSZERO](todo/open/D-TRANSZERO.md) <!-- item:open/D-TRANSZERO -->
- [ ] **`ABS(-32768%)` IS A SINGLE ON THE VG-8020 AND A DOUBLE HERE (D-ABSINTEDGE, found 2026-11-24 by D-KWSPEC's m...** -> [D-ABSINTEDGE](todo/open/D-ABSINTEDGE.md) <!-- item:open/D-ABSINTEDGE -->
- [ ] **`INT` OF A NEGATIVE NON-WHOLE SINGLE OR DOUBLE CHANGES TYPE ON THE VG-8020 -- THE INTEGER -1 ABOVE -1, A DO...** -> [D-INTNEGTYPE](todo/open/D-INTNEGTYPE.md) <!-- item:open/D-INTNEGTYPE -->
- [ ] **A SINGLE WHOSE EXPONENT BYTE IS 0 BUT WHOSE DIGIT BYTES ARE NOT (WHAT `FIX(.5!)` RETURNS) IS STORED AS ALL...** -> [D-ZEROLET](todo/open/D-ZEROLET.md) <!-- item:open/D-ZEROLET -->
- [ ] **`SQR(0%)` RETURNS A ZERO WITH LEFTOVER DIGIT BYTES HERE; THE VG-8020 RETURNS 8 ZERO BYTES (D-SQRZERO, found...** -> [D-SQRZERO](todo/open/D-SQRZERO.md) <!-- item:open/D-SQRZERO -->
- [ ] **`VAL("-32768%")` IS `Overflow` HERE AND -32768 ON THE VG-8020: zerobas TESTS `%`'S RANGE ON THE MAGNITUDE (...** -> [D-VALPCT](todo/open/D-VALPCT.md) <!-- item:open/D-VALPCT -->
- [x] **`INSTR` WITH AN EMPTY STRING TO FIND, AND A START PAST THE END: 0 ON THE VG-8020, `LEN(a$)+1` (OR THE START...** -> [D-INSTREMPTY](todo/done/D-INSTREMPTY.md) <!-- item:done/D-INSTREMPTY -->
- [x] **A SPACE BEFORE THE CLOSING PARENTHESIS AFTER `INSTR`'S / `STRING$`'S STRING ARGUMENT IS A SYNTAX ERROR (D-C...** -> [D-CLOSESPACE](todo/done/D-CLOSESPACE.md) <!-- item:done/D-CLOSESPACE -->
- [x] **`VAL` STOPS AT A TAB OR A LINE FEED INSIDE A NUMBER, AND REJECTS A GAP AFTER `&`: THE VG-8020 SKIPS BOTH (D...** -> [D-VALWS](todo/done/D-VALWS.md) <!-- item:done/D-VALWS -->
- [ ] **A GAP AFTER `&` (`& H10`, `&<TAB>H10`), OR A TAB / LF BEFORE IT: THE VG-8020 SKIPS IT IN VAL, READ AND THE...** -> [D-AMPGAP](todo/open/D-AMPGAP.md) <!-- item:open/D-AMPGAP -->
- [x] **A FOR THAT FAILS STILL PUSHES ITS LOOP FRAME ON ZEROBAS: THE NEXT THAT `RESUME NEXT` REACHES ITERATES -- FO...** -> [D-FORFRAME](todo/done/D-FORFRAME.md) <!-- item:done/D-FORFRAME -->
- [ ] **`FOR I%=1 TO 40000`: AN INTEGER LOOP VARIABLE WITH A LIMIT PAST 32767 IS OVERFLOW AT THE FOR ON THE VG-8020...** -> [D-FORINTLIM](todo/open/D-FORINTLIM.md) <!-- item:open/D-FORINTLIM -->
- [ ] **`FOR I=3 TO 1 STEP 0`: THE VG-8020 LOOPS FOR EVER, ZEROBAS RUNS THE BODY ONCE (D-FORSTEP0, found 2026-11-25...** -> [D-FORSTEP0](todo/open/D-FORSTEP0.md) <!-- item:open/D-FORSTEP0 -->
- [ ] **A FAILING `NEXT I` (NO FOR) CREATES THE VARIABLE I ON THE VG-8020, NOT ON ZEROBAS (D-NEXTCREATE, found 2026...** -> [D-NEXTCREATE](todo/open/D-NEXTCREATE.md) <!-- item:open/D-NEXTCREATE -->
- [ ] **A FAILED `NEXT J` DROPS THE OPEN FOR FRAME ON ZEROBAS; THE VG-8020 KEEPS IT (D-NEXTFRAME, found 2026-11-25...** -> [D-NEXTFRAME](todo/open/D-NEXTFRAME.md) <!-- item:open/D-NEXTFRAME -->
- [ ] **`FOR I=1 TO 2 STEP 1,2`: ONE SYNTAX ERROR ON THE VG-8020, TWO ON ZEROBAS (D-FORCOMMA, found 2026-11-25 by D...** -> [D-FORCOMMA](todo/open/D-FORCOMMA.md) <!-- item:open/D-FORCOMMA -->
- [ ] **`GOSUB 65000` (A MISSING LINE) PUSHES A RETURN FRAME ON ZEROBAS, NONE ON THE VG-8020 (D-GOSUBFRAME, found 2...** -> [D-GOSUBFRAME](todo/open/D-GOSUBFRAME.md) <!-- item:open/D-GOSUBFRAME -->
- [ ] **END CLOSES OPEN FILES ON THE VG-8020; ZEROBAS LEAVES THEM OPEN (D-ENDCLOSE, found 2026-11-25 by D-KWSPEC's...** -> [D-ENDCLOSE](todo/open/D-ENDCLOSE.md) <!-- item:open/D-ENDCLOSE -->
- [ ] **DELETING A LINE THAT DOES NOT EXIST AFTER A STOP: ZEROBAS SAYS `Undefined line number in 10`, AND THE NEXT...** -> [D-DELNOLINE](todo/open/D-DELNOLINE.md) <!-- item:open/D-DELNOLINE -->
- [ ] **`RUN 15` TO A MISSING LINE KEEPS THE CONT POINT ON ZEROBAS; THE VG-8020 DROPS IT FIRST (D-RUNCONT, found 20...** -> [D-RUNCONT](todo/open/D-RUNCONT.md) <!-- item:open/D-RUNCONT -->
- [x] **`RESUME 99` TO A MISSING LINE HANGS ZEROBAS (NO PROMPT EVER COMES BACK); THE VG-8020 STOPS WITH `Undefined...** -> [D-RESUMEMISS](todo/done/D-RESUMEMISS.md) <!-- item:done/D-RESUMEMISS -->
- [ ] **`ON ERROR GOTO A` IS `ON ERROR GOTO 0` ON THE VG-8020; ZEROBAS SAYS SYNTAX ERROR (D-ONERRVAR, found 2026-11...** -> [D-ONERRVAR](todo/open/D-ONERRVAR.md) <!-- item:open/D-ONERRVAR -->
- [ ] **A VARIABLE'S ENTRY IS [name0][name1][type][value] ON ZEROBAS, [type][name0][name1][value] ON THE VG-8020 (D...** -> [D-VARLAYOUT](todo/open/D-VARLAYOUT.md) <!-- item:open/D-VARLAYOUT -->
- [x] **`GO TO 100` (ONE SPACE) IS GOTO ON THE VG-8020 AND A SYNTAX ERROR ON ZEROBAS (D-GOTOSPACE, found 2026-11-25...** -> [D-GOTOSPACE](todo/done/D-GOTOSPACE.md) <!-- item:done/D-GOTOSPACE -->
- [ ] **`VAL`'S DECIMAL EXPONENT AT ITS 8-BIT EDGES: THE VG-8020 WRAPS PAST 255 DIGITS AND KEEPS THE DIGITS OF A ZE...** -> [D-VALEXP](todo/open/D-VALEXP.md) <!-- item:open/D-VALEXP -->
- [ ] **D-SETREGSCBIOS — SETTXT / SETT32 / SETGRP / SETMLT RETURN C-BIOS'S LEFTOVER REGISTERS SINCE THE REBASE** -> [D-SETREGSCBIOS](todo/open/D-SETREGSCBIOS.md) <!-- item:open/D-SETREGSCBIOS -->
- [ ] **D-VCBLAYOUT — PLAY'S VOICE-BLOCK BYTES: ZEROBAS'S OWN LAYOUT, NOT THE REFERENCE'S** -> [D-VCBLAYOUT](todo/open/D-VCBLAYOUT.md) <!-- item:open/D-VCBLAYOUT -->
- [ ] **D-INITIORACE — A FRAME INTERRUPT PENDING AT INITIO'S ENTRY PLAYS A STALE QUEUED NOTE ON THE REFERENCES; ZER...** -> [D-INITIORACE](todo/open/D-INITIORACE.md) <!-- item:open/D-INITIORACE -->
- [ ] **D-CALSLTSTACK — A CALSLT / CALLF TARGET RUNS 10 BYTES BELOW THE CALLER'S SP ON ZEROBAS; 6 ON THE VG-8020 AN...** -> [D-CALSLTSTACK](todo/open/D-CALSLTSTACK.md) <!-- item:open/D-CALSLTSTACK -->


- [ ] **D-CALSLTIY — IY IN A CALLF TARGET (AND IN A TARGET IN AN EXPANDED SLOT) DIFFERS FROM THE REFERENCES'** -> [D-CALSLTIY](todo/open/D-CALSLTIY.md) <!-- item:open/D-CALSLTIY -->


- [ ] **D-PLAYLONGTIME — A RING-FILLING PLAY RETURNS 14-15 JIFFIES EARLIER THAN ON THE VG-8020** -> [D-PLAYLONGTIME](todo/open/D-PLAYLONGTIME.md) <!-- item:open/D-PLAYLONGTIME -->
- [ ] **D-PHYDIOREGS — PHYDIO / DSKIO RETURN OTHER F, C, DE AND HL ON ZEROBAS** -> [D-PHYDIOREGS](todo/open/D-PHYDIOREGS.md) <!-- item:open/D-PHYDIOREGS -->
- [ ] **D-PHYDIOPAST — A READ PAST THE DISK'S LAST SECTOR RETURNS ERROR 8 ON ZEROBAS, 2 ON THE REFERENCE** -> [D-PHYDIOPAST](todo/open/D-PHYDIOPAST.md) <!-- item:open/D-PHYDIOPAST -->
- [ ] **D-PHYDIOB0 — PHYDIO WITH B 0 TRANSFERS NOTHING ON ZEROBAS; THE REFERENCE READS 256 SECTORS** -> [D-PHYDIOB0](todo/open/D-PHYDIOB0.md) <!-- item:open/D-PHYDIOB0 -->
- [ ] **D-GETDPBMEDIA — GETDPB READS THE DISK AND FILLS ITS FORMAT'S DPB; THE REFERENCE BUILDS IT FROM THE MEDIA BY...** -> [D-GETDPBMEDIA](todo/open/D-GETDPBMEDIA.md) <!-- item:open/D-GETDPBMEDIA -->
- [ ] **D-FMAKERS — FMAKE LEAVES THE FCB'S RECORD SIZE (+14 / +15); THE REFERENCES CLEAR +14 .. +31** -> [D-FMAKERS](todo/open/D-FMAKERS.md) <!-- item:open/D-FMAKERS -->
- [ ] **D-FCBEXTENT — SEQUENTIAL WRITES IGNORE THE FCB'S EXTENT AND CURRENT RECORD (THEY WRITE AT ZEROBAS'S OWN POS...** -> [D-FCBEXTENT](todo/open/D-FCBEXTENT.md) <!-- item:open/D-FCBEXTENT -->
- [ ] **D-FSIZERS — FSIZE LEAVES THE FCB'S +14; BOTH REFERENCES CLEAR IT (AND KEEP +15)** -> [D-FSIZERS](todo/open/D-FSIZERS.md) <!-- item:open/D-FSIZERS -->
- [ ] **D-WRZERHL — WRZER WITH HL 2 AND RECORD SIZE $0180 WRITES ANOTHER SIZE, CLUSTERS AND DTA THAN THE REFERENCES** -> [D-WRZERHL](todo/open/D-WRZERHL.md) <!-- item:open/D-WRZERHL -->
- [ ] **D-WRZEREXT — WRZER PAST 16 KB LEAVES +12 0 AND RR'S LOW BYTE IN +32; THE REFERENCES SPLIT RR INTO EXTENT AN...** -> [D-WRZEREXT](todo/open/D-WRZEREXT.md) <!-- item:open/D-WRZEREXT -->
- [ ] **D-WRBLKGAP — WRBLK PAST THE END: THE NEW-CLUSTER SECTOR IT WRITES INTO KEEPS THE DISK'S BYTES; BOTH REFEREN...** -> [D-WRBLKGAP](todo/open/D-WRBLKGAP.md) <!-- item:open/D-WRBLKGAP -->
- [ ] **D-SETRNDR36 — SETRND CLEARS THE FCB'S +36; BOTH REFERENCES LEAVE IT** -> [D-SETRNDR36](todo/open/D-SETRNDR36.md) <!-- item:open/D-SETRNDR36 -->
- [ ] **D-BDOSCARRY — SNEXT / SFIRST ANSWER "NOT FOUND" (A $FF) WITH THE CARRY CLEAR; BOTH REFERENCES SET IT** -> [D-BDOSCARRY](todo/open/D-BDOSCARRY.md) <!-- item:open/D-BDOSCARRY -->
- [ ] **D-DISKFORCBIOS — WHAT A C-BIOS DISK-DRIVER PORT NEEDS FROM ZEROBAS: DSKIO / CHOICE / MTOFF PAGES, AN NMS 82...** -> [D-DISKFORCBIOS](todo/open/D-DISKFORCBIOS.md) <!-- item:open/D-DISKFORCBIOS -->
- [ ] **D-F37DCONHOLD — CONST THROUGH $F37D LEAVES THE KEY IN THE BIOS BUFFER; THE REFERENCES MOVE IT INTO THE DOS'...** -> [D-F37DCONHOLD](todo/open/D-F37DCONHOLD.md) <!-- item:open/D-F37DCONHOLD -->
- [ ] **D-F37DEI — THE $F37D BDOS LEAVES INTERRUPTS ON; BOTH REFERENCES LEAVE THEM OFF** -> [D-F37DEI](todo/open/D-F37DEI.md) <!-- item:open/D-F37DEI -->
- [ ] **D-ALLOCIXIY — ALLOC THROUGH $F37D LEAVES IX / IY; THE REFERENCES RETURN THE DPB AND FAT-BUFFER ADDRESSES** -> [D-ALLOCIXIY](todo/open/D-ALLOCIXIY.md) <!-- item:open/D-ALLOCIXIY -->
- [ ] **D-F37DDTA — THE DTA CELL STARTS AT $0080 AND DSKRST DOES NOT RESET IT; THE REFERENCES: $0000, AND DSKRST ->...** -> [D-F37DDTA](todo/open/D-F37DDTA.md) <!-- item:open/D-F37DDTA -->
- [ ] **D-F37DREGS — THE $F37D BDOS RETURNS OTHER WORKING REGISTERS THAN BOTH REFERENCES** -> [D-F37DREGS](todo/open/D-F37DREGS.md) <!-- item:open/D-F37DREGS -->
- [ ] **D-DSKFMTHIGH — DSKFMT TAKES CHOICE $81 AS A SUCCESS AND FORMATS NOTHING; THE REFERENCE REFUSES IT** -> [D-DSKFMTHIGH](todo/open/D-DSKFMTHIGH.md) <!-- item:open/D-DSKFMTHIGH -->
- [ ] **D-DSKFMTREGS — DSKFMT RETURNS OTHER WORKING REGISTERS THAN THE CF-3300'S (THE DISKS ARE THE SAME)** -> [D-DSKFMTREGS](todo/open/D-DSKFMTREGS.md) <!-- item:open/D-DSKFMTREGS -->
- [ ] **D-DSKCHGFF — DSKCHG NEVER ANSWERS B $FF ("CHANGED"); THE REFERENCE DOES WHEN THE DISK'S MEDIA BYTE IS NOT C** -> [D-DSKCHGFF](todo/open/D-DSKCHGFF.md) <!-- item:open/D-DSKCHGFF -->
- [ ] **D-DSKCHGTIME — DSKCHG'S "UNCHANGED" WINDOW IS ~3 S IN ZEROBAS, LESS THAN 2 S (96 INTERRUPTS) ON THE REFERENCE** -> [D-DSKCHGTIME](todo/open/D-DSKCHGTIME.md) <!-- item:open/D-DSKCHGTIME -->
- [ ] **D-DSKCHGREGS — DSKCHG'S "UNKNOWN" ANSWER RETURNS WORKING VALUES WHERE THE REFERENCE RETURNS THE MEDIA BYTE** -> [D-DSKCHGREGS](todo/open/D-DSKCHGREGS.md) <!-- item:open/D-DSKCHGREGS -->
- [ ] **D-PHYDIOGEOM — A $FF DISK HAS 80 TRACKS IN ZEROBAS'S DSKIO; THE REFERENCE'S HAS 40** -> [D-PHYDIOGEOM](todo/open/D-PHYDIOGEOM.md) <!-- item:open/D-PHYDIOGEOM -->
- [ ] **D-PHYDIOWRAP16 — PHYDIO PAST SECTOR $FFFF GOES ON AT SECTOR 0; THE REFERENCE REFUSES THE CALL UP FRONT** -> [D-PHYDIOWRAP16](todo/open/D-PHYDIOWRAP16.md) <!-- item:open/D-PHYDIOWRAP16 -->
- [ ] **D-PHYDIOMEDIA — ZEROBAS TAKES MEDIA BYTES THE REFERENCE REFUSES ($00, $32: ERROR 12)** -> [D-PHYDIOMEDIA](todo/open/D-PHYDIOMEDIA.md) <!-- item:open/D-PHYDIOMEDIA -->
- [ ] **D-SCANKSKIP — A SCANR THAT ENDS IN ITS SKIP KEEPS K; ZEROBAS STORES THE SKIP'S HL 0** -> [D-SCANKSKIP](todo/open/D-SCANKSKIP.md) <!-- item:open/D-SCANKSKIP -->
- [ ] **D-TAPEPHASE — OUR TAPE CYCLES START HIGH; THE VG-8020'S START LOW (THE SIGNAL IS INVERTED)** -> [D-TAPEPHASE](todo/open/D-TAPEPHASE.md) <!-- item:open/D-TAPEPHASE -->
- [ ] **D-TAPOUTEI — TAPOUT LEAVES INTERRUPTS OFF; THE REFERENCES KEEP THE ENTRY STATE** -> [D-TAPOUTEI](todo/open/D-TAPOUTEI.md) <!-- item:open/D-TAPOUTEI -->
- [ ] **D-CHGETSTOP — CHGET WITH INTFLG 4 (STOP'S PAUSE) CLEARS IT AND RETURNS THE NEXT KEY** -> [D-CHGETSTOP](todo/open/D-CHGETSTOP.md) <!-- item:open/D-CHGETSTOP -->
- [ ] **D-SELECTKEY — THE SELECT KEY DELIVERS NOTHING; THE REFERENCES DELIVER $18** -> [D-SELECTKEY](todo/open/D-SELECTKEY.md) <!-- item:open/D-SELECTKEY -->
- [ ] **D-GRPPRTSETC — GRPPRT DRAWS EACH SET GLYPH BIT AS ONE SETC; docs/bios/GRPPRT.md R-GP-VRAM SAYS OTHERWISE** -> [D-GRPPRTSETC](todo/open/D-GRPPRTSETC.md) <!-- item:open/D-GRPPRTSETC -->
- [ ] **D-GCSC01 — IN SCREEN 0 / 1 THE GRAPHICS-CURSOR CALLS WORK AS IN SCREEN 3 ON THE VG-8020** -> [D-GCSC01](todo/open/D-GCSC01.md) <!-- item:open/D-GCSC01 -->
- [ ] **D-GTSTCKODDA — GTSTCK'S ODD-A PORT RULE (input-calls.patch) FAILS AT A 4** -> [D-GTSTCKODDA](todo/open/D-GTSTCKODDA.md) <!-- item:open/D-GTSTCKODDA -->
- [ ] **D-CNVCHRCP20 — CNVCHR'S UNDOCUMENTED F: `cp $20` MATCHES THE VG-8020 EXACTLY** -> [D-CNVCHRCP20](todo/open/D-CNVCHRCP20.md) <!-- item:open/D-CNVCHRCP20 -->
- [ ] **D-C032TEXT — TEXT-REGION FACTS TO CHECK: FSTPOS ON SCROLL, BUFMIN, LINL40 / LINL32 AT START, CLS SIZES** -> [D-C032TEXT](todo/open/D-C032TEXT.md) <!-- item:open/D-C032TEXT -->
- [ ] **D-C032GFX — GRAPHICS FACTS TO CHECK: SETC SCREEN 3 WITH ANY CMASK, CLRSPR IN SCREEN 0, INIT32'S ORDER** -> [D-C032GFX](todo/open/D-C032GFX.md) <!-- item:open/D-C032GFX -->
- [ ] **D-C032INPUT — INPUT FACTS TO CHECK: BREAKX ON CTRL+STOP, ISCNTC / CKCNTC IDLE, OUTDO WITH PRTFLG** -> [D-C032INPUT](todo/open/D-C032INPUT.md) <!-- item:open/D-C032INPUT -->
- [ ] **D-STRPTRDAC — THE REFERENCE KEEPS THE CURRENT STRING RESULT AT DAC+2; ZEROBAS KEEPS STRPTR APART** -> [D-STRPTRDAC](todo/open/D-STRPTRDAC.md) <!-- item:open/D-STRPTRDAC -->
- [ ] **D-INIREGS — INIGRP / INIMLT RETURN OTHER DE AND HL ON ZEROBAS** -> [D-INIREGS](todo/open/D-INIREGS.md) <!-- item:open/D-INIREGS -->


- [ ] **D-TAPECORPUSNOISE — THE TAPE CORPUS'S PER-TITLE DIFFERENCE COUNTS SWING WITH TIMING, NOT ONLY WITH CORRECTNESS** -> [D-TAPECORPUSNOISE](todo/open/D-TAPECORPUSNOISE.md) <!-- item:open/D-TAPECORPUSNOISE -->

- [ ] **D-CHRGTRSKIP — CHRGTR SKIPS ONLY THE SPACE; THE VG-8020'S SKIPS TAB AND LF TOO, AND ITS END-OF-LINE F IS $44** -> [D-CHRGTRSKIP](todo/open/D-CHRGTRSKIP.md) <!-- item:open/D-CHRGTRSKIP -->

- [ ] **D-CHRGTRTOK — CHRGTR TREATS THE NUMERIC-CONSTANT TOKENS $0B-$1F AS PLAIN CHARACTERS; THE VG-8020'S DECODES...** -> [D-CHRGTRTOK](todo/open/D-CHRGTRTOK.md) <!-- item:open/D-CHRGTRTOK -->

- [ ] **D-TEXTAF — THE TEXT CALLS' A / F ON RETURN DIFFER FROM THE VG-8020'S** -> [D-TEXTAF](todo/open/D-TEXTAF.md) <!-- item:open/D-TEXTAF -->

- [ ] **D-GATEKNIFESKIP — A DOCS / PROBE-ONLY GATE RE-PINS THE KNIVES AND RUNS THE WHOLE UNIT SUITE: ~15-20 MIN FOR...** -> [D-GATEKNIFESKIP](todo/open/D-GATEKNIFESKIP.md) <!-- item:open/D-GATEKNIFESKIP -->

- [x] **D-STIMERANGE — BDOS STIME TAKES ANY TIME: A = 0 WHERE THE CF-3300 ANSWERS $FF FOR AN OUT-OF-RANGE ONE** -> [D-STIMERANGE](todo/done/D-STIMERANGE.md) <!-- item:done/D-STIMERANGE -->

- [ ] **D-SLACK — A NEW FILE'S NEVER-WRITTEN RECORDS HOLD DIFFERENT GARBAGE** -> [D-SLACK](todo/open/D-SLACK.md) <!-- item:open/D-SLACK -->

- [x] **D-CONCOL — THE BDOS CONSOLE'S LOGICAL COLUMN AFTER A CONTROL CODE: TAB LANDS WRONG AFTER FF / BS / BEL / ESC** -> [D-CONCOL](todo/done/D-CONCOL.md) <!-- item:done/D-CONCOL -->

- [x] **D-DSKIOCYL — DSKIO ON A CYLINDER PAST THE LAST ANSWERS 8 (RECORD NOT FOUND); THE CF-3300 ANSWERS 2 (NOT READY)** -> [D-DSKIOCYL](todo/done/D-DSKIOCYL.md) <!-- item:done/D-DSKIOCYL -->
- [ ] **omsx_repl: a typed line whose CHUNK ends on `\` breaks the Tcl** -> [X-OMSX-REPL-A-TYPED-LINE-WHOSE](todo/open/X-OMSX-REPL-A-TYPED-LINE-WHOSE.md) <!-- item:open/X-OMSX-REPL-A-TYPED-LINE-WHOSE -->
- [ ] **A PLAY zeroes the OTHER voices' amplitudes on the VG-8020, not here** -> [X-A-PLAY-ZEROES-THE-OTHER-VOICES](todo/open/X-A-PLAY-ZEROES-THE-OTHER-VOICES.md) <!-- item:open/X-A-PLAY-ZEROES-THE-OTHER-VOICES -->
- [ ] **lptout_upframes: two VG-8020 readings of the same bytes disagree** -> [X-LPTOUT-UPFRAMES-TWO-VG-8020-READINGS](todo/open/X-LPTOUT-UPFRAMES-TWO-VG-8020-READINGS.md) <!-- item:open/X-LPTOUT-UPFRAMES-TWO-VG-8020-READINGS -->
- [ ] **OUTDLP on a non-MSX printer: the hiragana -> katakana transform** -> [X-OUTDLP-ON-A-NON-MSX-PRINTER](todo/open/X-OUTDLP-ON-A-NON-MSX-PRINTER.md) <!-- item:open/X-OUTDLP-ON-A-NON-MSX-PRINTER -->
- [ ] **SCREEN 3 leaves unused VRAM unlike the VG-8020** -> [X-SCREEN-3-LEAVES-UNUSED-VRAM-UNLIKE](todo/open/X-SCREEN-3-LEAVES-UNUSED-VRAM-UNLIKE.md) <!-- item:open/X-SCREEN-3-LEAVES-UNUSED-VRAM-UNLIKE -->
- [ ] **A BASIC output file and $F37D RDRND / WRRND in one program** -> [X-A-BASIC-OUTPUT-FILE-AND-F37D](todo/open/X-A-BASIC-OUTPUT-FILE-AND-F37D.md) <!-- item:open/X-A-BASIC-OUTPUT-FILE-AND-F37D -->
- [ ] **The NMS 1200 disk ROM beeps at boot (R0 = $55 at a cartridge's INIT); zerobas's disk ROM does not** -> [X-THE-NMS-1200-DISK-ROM-BEEPS](todo/open/X-THE-NMS-1200-DISK-ROM-BEEPS.md) <!-- item:open/X-THE-NMS-1200-DISK-ROM-BEEPS -->
- [ ] **D-FMTERR — FORMAT'S DIALOGUE OFF THE HAPPY PATH IS UNMEASURED (filed 2026-11-11 by D-DSKFMT's close)** -> [D-FMTERR](todo/open/D-FMTERR.md) <!-- item:open/D-FMTERR -->

- [ ] **D-F37DNODISK — WITH NO DISK INTERFACE $F37D HOLDS $C9 HERE, $00 ON THE VG-8020 (found 2026-11-10 by D-BIOSL...** -> [D-F37DNODISK](todo/open/D-F37DNODISK.md) <!-- item:open/D-F37DNODISK -->

- [ ] **D-LOOPPROF — WHERE A PLAIN STATEMENT'S TIME GOES: FIVE MEASURED LEVERS (filed 2026-10-20 from a host profile)** -> [D-LOOPPROF](todo/open/D-LOOPPROF.md) <!-- item:open/D-LOOPPROF -->

- [x] **DISK BASIC'S ERROR SURFACE: 32 OF 126 CASES DIVERGE FROM THE CF-3300, AND FOUR OF THEM LOSE DATA SILENTLY (...** -> [D-DISKERRS](todo/done/D-DISKERRS.md) <!-- item:done/D-DISKERRS -->

- [x] **D-TAPETAIL — THE CASSETTE SAVE VERBS' BAD TAILS PRINTED `load error`; THE VG-8020 RAISES 2 / 5, AND A TAPE...** -> [D-TAPETAIL](todo/done/D-TAPETAIL.md) <!-- item:done/D-TAPETAIL -->

- [ ] **D-STATICEMU — THE "STATIC" GATE TIER BOOTS EMULATORS: `kwsweep`, `kwtime` AND `kwram` SIT IN `tools/run_gat...** -> [D-STATICEMU](todo/open/D-STATICEMU.md) <!-- item:open/D-STATICEMU -->
- [ ] **D-PINSTALE — gates-fast SHOULD RE-MEASURE THE KEYWORD SWEEPS WHEN THE ROM HAS MOVED SINCE THEIR PINS (filed...** -> [D-PINSTALE](todo/open/D-PINSTALE.md) <!-- item:open/D-PINSTALE -->

- [ ] **D-CHANFORREF — kwsweep's `chanfor` HAS READ THE CF-3300'S FUNCTION-KEY BAR, NOT ITS VALUE, ON EVERY BATCH R...** -> [D-CHANFORREF](todo/open/D-CHANFORREF.md) <!-- item:open/D-CHANFORREF -->

- [x] **TWO FILES WRITTEN AND READ TOGETHER CAME BACK WRONG — TWO BUGS, ONE OF THEM MINE (D-CHANSWITCH, found and f...** -> [D-CHANSWITCH](todo/done/D-CHANSWITCH.md) <!-- item:done/D-CHANSWITCH -->

- [ ] **D-KWTIMESYMRACE — `kwtime` CAN DIE IN 0 s ON `KeyError: 'tokenise'` WHEN ANOTHER BATTERY UNIT REWRITES main...** -> [D-KWTIMESYMRACE](todo/open/D-KWTIMESYMRACE.md) <!-- item:open/D-KWTIMESYMRACE -->

- [ ] **A FILE WHOSE CLUSTER CHAIN POINTS PAST THE VOLUME LOADS AS AN EMPTY PROGRAM HERE, SILENTLY; THE CF-3300 SAY...** -> [D-BADCLUSTER](todo/open/D-BADCLUSTER.md) <!-- item:open/D-BADCLUSTER -->

- [ ] **D-BLKIOPERCALL — EVERY BLOCK I/O CALL STILL RE-MOUNTS AND RE-FINDS, AND EVERY WRBLK REWRITES THE DIRECTORY:...** -> [D-BLKIOPERCALL](todo/open/D-BLKIOPERCALL.md) <!-- item:open/D-BLKIOPERCALL -->


- [ ] **A kwtime ROW THAT REGRESSES FROM OK TO SLOW OR HANG FAILS NO GATE (D-KWTRATCHET, found 2026-09-28 while fix...** -> [D-KWTRATCHET](todo/open/D-KWTRATCHET.md) <!-- item:open/D-KWTRATCHET -->

- [ ] **`RUN`'S T5 RATIO FLIPS BETWEEN RUNS — 1.1×, 1.5× AND 1.7× ON 2026-09-28 — SO `tiers-md-check` GOES RED AFTE...** -> [D-RUNT5NOISE](todo/open/D-RUNT5NOISE.md) <!-- item:open/D-RUNT5NOISE -->

- [ ] **D-TEMPD10 — TEN NESTED PENDING STRING TEMPORARIES ARE `String formula too complex` ON THE VG-8020 AND ANSWE...** -> [D-TEMPD10](todo/open/D-TEMPD10.md) <!-- item:open/D-TEMPD10 -->

- [ ] **`CALL SYSTEM` WITH MSXDOS.SYS DELETED: THE CF-3300 LOOPS ON `Boot error` / `Press any key for retry`; ZEROB...** -> [D-SYSBOOTERR](todo/open/D-SYSBOOTERR.md) <!-- item:open/D-SYSBOOTERR -->

- [ ] **DATA DISK AT POWER-ON, MSX-DOS DISK INSERTED LATER: `CALL SYSTEM` RESTARTS DISK BASIC ON THE CF-3300 (banne...** -> [D-SYSLATE](todo/open/D-SYSLATE.md) <!-- item:open/D-SYSLATE -->

- [ ] **A KNIFE HARNESS SCORES THE ROWS A CRASHED PROBE NEVER PRINTED AS UNMOVED (D-KNIFEROWS, found 2026-10-09 by...** -> [D-KNIFEROWS](todo/open/D-KNIFEROWS.md) <!-- item:open/D-KNIFEROWS -->

- [ ] **THREE TAPE CASES NOBODY COMPARED (D-TAPEQ3, found 2026-10-09 by the cassette concept page).** -> [D-TAPEQ3](todo/open/D-TAPEQ3.md) <!-- item:open/D-TAPEQ3 -->

- [ ] **`COPY "A:X" TO "B:Y"` PROMPTS FOUR TIMES ON THE CF-3300 AND ONCE HERE (D-DSKIBCOPY, found 2026-10-27 by D-D...** -> [D-DSKIBCOPY](todo/open/D-DSKIBCOPY.md) <!-- item:open/D-DSKIBCOPY -->

- [ ] **SHIFT OR CTRL HELD AT BOOT — THE DISK ROM'S OWN BOOT OPTIONS FOR MORE FREE RAM (D-BOOTKEYS, raised by Joost...** -> [D-BOOTKEYS](todo/open/D-BOOTKEYS.md) <!-- item:open/D-BOOTKEYS -->

- [ ] **CONCEPT PAGES — HUMAN-FRONTING DOCS FOR WHAT IS NOT A KEYWORD (D-CONCEPTDOCS, Joost 2026-10-09).** -> [D-CONCEPTDOCS](todo/open/D-CONCEPTDOCS.md) <!-- item:open/D-CONCEPTDOCS -->

- [ ] **STALE COMMENTS AND DOCS THE KEYWORD-PAGE AGENTS FOUND (D-PAGEDEBT, 2026-10-09).** -> [D-PAGEDEBT](todo/open/D-PAGEDEBT.md) <!-- item:open/D-PAGEDEBT -->

- [ ] **Keyword-completeness gaps — the measured remainder of MSX1 BASIC.** -> [X-KEYWORD-COMPLETENESS-GAPS-THE-MEASURED-REMAINDER](todo/open/X-KEYWORD-COMPLETENESS-GAPS-THE-MEASURED-REMAINDER.md) <!-- item:open/X-KEYWORD-COMPLETENESS-GAPS-THE-MEASURED-REMAINDER -->
- [x] **A LINE STORE IS BOUNDED BY THE CONSTANT `TXTMAX`, NOT BY HIMEM.** -> [X-A-LINE-STORE-IS-BOUNDED-BY](todo/done/X-A-LINE-STORE-IS-BOUNDED-BY.md) <!-- item:done/X-A-LINE-STORE-IS-BOUNDED-BY -->

- [x] **README "Limitations (this slice)" IS STALE** -> [X-README-LIMITATIONS-THIS-SLICE-IS-STALE](todo/done/X-README-LIMITATIONS-THIS-SLICE-IS-STALE.md) <!-- item:done/X-README-LIMITATIONS-THIS-SLICE-IS-STALE -->

- [ ] **SLIM THE FILE-CHANNEL CONTEXT toward the reference** -> [X-SLIM-THE-FILE-CHANNEL-CONTEXT-TOWARD](todo/open/X-SLIM-THE-FILE-CHANNEL-CONTEXT-TOWARD.md) <!-- item:open/X-SLIM-THE-FILE-CHANNEL-CONTEXT-TOWARD -->
✂️ **D-KWPARTICLE — SYNTAX PARTICLES LEAVE THE STATEMENT DENOMINATOR** (Joost,
2026-09-14, asked whether the ⛔ on re-tiering the keyword umbrella covered the
DENOMINATOR as well as the tier assignment: **"Drop them and mark them"**).
🎯 **`THEN`, `ELSE`, `TO`, `STEP` and `OFF` APPEAR ONLY *INSIDE* ANOTHER
STATEMENT AND HAVE NOTHING OF THEIR OWN TO GET RIGHT.** There is no `THEN`
statement, only `IF ... THEN`. They stay in the TOKEN denominator — the reference
tokenises them, so we must too — and are MARKED in the table under their own class
rather than silently vanishing from the sheet. **STATEMENT: 171 → 166** (149
keywords with a bare form + 17 composites).
⚠️ **AND THE OPERATORS DELIBERATELY STAY, MARKED.** `AND OR NOT XOR EQV IMP MOD`
are never statements either, but **unlike a particle each HAS BEHAVIOUR OF ITS OWN
worth tiering** — `A AND B` has a truth table to get right and `THEN` has nothing.
I put that distinction to Joost explicitly rather than deciding it quietly.
🔴 **`AS` IS NOT IN THIS TREE'S TABLE AT ALL** — it is part of `OPEN ... AS #n`
and `FIELD ... AS` but `basic/kwtable.inc` does not tokenise it separately.
MEASURED, not assumed, and the reason the list is five and not six.
✅ Selftest **S33**: every particle is in the TOKEN set and in NO case in the
STATEMENT set, and every operator IS in the statement set.
🔴 **AND S33 FAILED ITS FIRST RUN FOR THE REASON S29/S30 ALREADY RECORD**: it
asked its question of the selftest's FIXTURE `kws`, which holds three invented
keywords and no particles at all, so **every clause would have passed vacuously**.
It reads `kwtable_keywords()` now. *A selftest that cannot see its subject agrees
with everything.*
🔬 **D-KWOVERLAP — MEASURED: THE SUITES AND THE SWEEP ARE ORTHOGONAL, NOT
REDUNDANT** (Joost, 2026-09-14, inverting my evidence question: *"maybe some of the
kwsweep tests can replace tests in the suites?"*).
📊 **47559 TYPED LINES FROM 83 SUITES** (`make kwcover`, `scratchpad/kwoverlap.py`).
🎯 **THE DISTRIBUTION IS BIMODAL AND THERE IS NO MIDDLE BAND.** A suite types a
statement either **hundreds** of times, because it IS that suite's subject
(`width-acceptance` types `WIDTH` 981× and `SCREEN` 1087×, against kwsweep's two
rows each; `math-acceptance` types `PRINT` 1350×), or **once or twice**, because it
is APPARATUS inside a test of something else. **There is nothing in between for a
sweep row to substitute for.**
🔴 **AND THE 528 LOW-COUNT PAIRS ARE NOT THIN TESTS — THEY ARE NOT TESTS AT ALL.**
Checked by READING THE LINES rather than the counts: `deffn-acceptance` types `ABS`
once, in `DEF FNA(X)=ABS(0)+X`, where ABS is the BODY of the DEF FN under test;
`ramfree-acceptance` types `LINE` to CONSUME VRAM before measuring free RAM;
`gicini-acceptance` types `SCREEN 1:SCREEN 0` as setup; `array-acceptance` types
`POKE` to PLANT the bytes it then reads as an array; `banner-acceptance` types
`PRINT` as its READOUT. **Deleting any of those does not remove a test of that
keyword — it breaks the test of a different one.**
🎚️ **kwsweep IS 1488 OF THE 47559 LINES, ABOUT 3%**, and the two are different
KINDS of instrument: the sweep is BREADTH (every statement, once or twice, each row
designed to fail if that statement breaks) and the suites are DEPTH (one statement,
hundreds of times, mostly error and geometry cases). **The battery is not carrying
duplicate work that could be cut**, and my prior that "the overlap is thin" was
right for the wrong reason — it is not that the numbers are small, it is that the
two instruments never meet.
🙋 **STILL OPEN AND NOT SETTLED BY THIS**: whether a dedicated acceptance suite may
SUPPLY TIER 1 breadth. `input-devices-acceptance` properly exercises
`STICK`/`STRIG`/`PDL` whose kwsweep rows read 0 — correct with nothing plugged in
AND exactly what a stub returns, so they are not awarded. Joost answered a
different question; this one waits.
⌨️ **D-KWRESPOND — THE TYPED-INPUT CHANNEL, AND IT FOUND A MISSING FORM ON ITS
FIRST USE** (Joost, 2026-09-14: **"Build it"**). **75 of 167 statements at TIER 1.**
🔴 **AND THE UNBLOCK I PROPOSED TO HIM WAS UNNECESSARY.** I offered to stuff
`KEYBUF` ($FBF0) with `GETPNT`/`PUTPNT` from inside the stored program — apparatus
INSIDE the program under test, which is exactly where this session kept getting
bitten. **Reading `probes/basic/basic_probe_input.py` first showed it does nothing
of the kind:** it types the response as a TRAILING RAW LINE AFTER `RUN`, the line
editor consumes it in order, and by the time it is injected RUN is executing and
the read is blocked — so the CR-terminated line lands in KEYBUF by itself and CHGET
hands it over. **No POKEs, and a mechanism `input-acceptance` has been proving for
months.** ⚠️ *Read the probe that already solved it before building the thing you
proposed.*
✅ **A `RESPOND:` TAG**, parsed like `FORM:`/`SUBJECT:` (`_` is a space, `|`
separates responses). A row carrying it is built as a **DIRECT** case with its own
numbered lines, `RUN`, then the responses — because `run_cases` appends `RUN`
itself in stored mode and has no hook for anything after it. **Nothing in
`omsx_repl` changed.**
🔬 **THE CONTROL ROW RAN FIRST AND WAS THE WRONG SHAPE, WHICH IS WHY IT RAN
FIRST.** Written with `INKEY$` it read `[0y]` on the reference and
`[0y]|ZBZ|Syntax error` on zerobas: **INKEY$ DOES NOT BLOCK**, so the program
finished before the response was typed and BASIC then tried to EXECUTE the response
as a command. **The channel works only while a read is WAITING** — which is the
whole mechanism, and the thing the control existed to pin. 🎯 And it also showed
the channel's failure mode is LOUD (a stray command and a syntax error), not a
silently wrong value.
🔴 **REBUILT AROUND `INPUT$(1)`, A BLOCKING READ THAT IS NOT `INPUT` — AND THAT
FOUND A GAP.** Reference `[0yZ]`, zerobas `Syntax error`: `str_inputd`
(`basic/strvar.asm`) requires `,#f` — its own comment says *"file form requires
'#f'"* — and falls to `str_eval_no` without it. **The CONSOLE form of `INPUT$` is
not implemented here**, and `inputdol` had been CRUNCH-ONLY (exec `None`, note
*"BLOCKS waiting for a keypress"*) since the day it was written, so it had never
been executed at all.
⚠️ **AND THE READING WAS SCORED FOR NOBODY UNTIL `INPUT$` BECAME A SUBJECT.**
`basic/kwtable.inc` says it outright — for MKI$, *"the '$' is PART of the keyword,
UNLIKE INPUT$"* — MSX tokenises `INPUT` and the `$` separately, so the table
rightly holds only `INPUT`. But `INPUT$(n)` is a FUNCTION with its own evaluator
and nothing to do with the INPUT STATEMENT, so crediting its gap to INPUT would
attribute a function's defect to a statement. It is an UNDERIVABLE subject now,
authored at N=2 (console, channel), standing at **0/2 with the console form
MISSING**.
🟢 **`INPUT` AT 3/3 AND `LINE INPUT` AT 2/2, BOTH AWARDED.** Bare console INPUT had
NEVER had a row — both of INPUT's rows drove the FILE form and belong to `INPUT #`
— so the console statement a 1985 listing uses most had never been measured.
`[0zHELLO]` promptless, `[1a 42 ]` with a prompt, `[1b 3  4 ]` splitting ONE typed
line on the comma into TWO variables. 🎯 **`LINE INPUT`'s reading is the
discriminator:** `[1c A,B C]` keeps the comma AND the leading space, where `INPUT`
would have split at the comma and eaten the space.
⚡ **D-KWBATCH9 — FIVE MORE AWARDED WITH NO NEW ROWS, AND FOUR BARS AUTHORED THAT
NAME WHAT IS MISSING. 80 of 167.**
🟢 **`ERROR`, `NEW`, `LLIST`, `LPRINT`, `LFILES` AT N=1**, each already holding a
row whose reading can FAIL: `ERROR`'s two rows raise 7 and 53 and read ERR **and**
ERL back, so a handler raising a constant or losing the line number shows; `NEW`'s
discriminator is that the statement after it is never reached AND no error is
raised (before D-NEWSTMT that row carried `Syntax error in 10`); the three printer
verbs read off the PRINTER LOG or through `LPOS`, because their output never
reaches the screen at all.
🔭 **AND FOUR BARS AUTHORED THAT AWARD NOTHING, WHICH IS THE POINT OF HAVING A
BAR.** `LIST` 1/3 — selecting WHICH lines to print is the part a bare LIST cannot
exercise. `FILES` 1/2 — the row is the PATTERN form, so a FILES that IGNORED its
pattern would pass the only row it has. `WAIT` 1/2 — the optional third operand
INVERTS the sense of the test, so a WAIT that dropped it would spin forever on
exactly the inputs the two-argument form returns on. `RESUME` 1/3 — three different
places to continue, and **re-running the failing statement is the form most likely
to loop forever if it is wrong**, which is the one with no row.
⛔ **`SET`, `IPL` and `CMD` ARE DELIBERATELY NOT AUTHORED.** All three are
refuse-on-sight words here — `ERR 5` on both references — so they have no HAPPY
PATH on this machine at all, and an N=1 meaning "refuses correctly" would be a
TIER 5 reading wearing a TIER 1 label. ⛔ `MOTOR` likewise waits: its row prints a
constant `[ok]`, which is the third screening axis.
🔴 **D-KWT1ITEM — I READ "NO OPEN ITEM" AS "NO OPEN ITEM AT ANY TIER", AND THAT
WAS WRONG** (found 2026-09-14 while measuring what "all items at TIER 1" would
actually take, after Joost said it *"should be within reach"*).
🎯 **AN ITEM AT TIER n SAYS TIER n IS NOT REACHED. IT SAYS NOTHING ABOUT TIER
n−1.** Joost's own ladder is HAPPY PATH → REASONABLE TIME → COMMON ERRORS → ON-PAR
SPEED → EVERY ERROR, so a keyword that is SLOWER THAN THE REFERENCE can still have
a perfect happy path — **and the TIER 4 item on `FOR`/`GOTO` says exactly that in
its own text**: *"the interpreter is 2.5–3.8× slower (TIER 2, reasonable time, is
met)"*. I had that sentence in front of me and still blocked TIER 1 on it.
📊 **MEASURED COST: FIFTEEN STATEMENTS HELD OUT OF TIER 1 BY ITEMS THAT ARE NOT
ABOUT THE HAPPY PATH** — eleven at TIER 5 (an exhaustive error case), three at
TIER 4 (speed) and one at TIER 3 (a common error).
✅ `blocks_tier1()` now reads the entry's FIRST element and compares it to **1**,
and selftest **S34** pins that items at 3, 4 and 5 do NOT block. ⚠️ It reads
`entry[0]`, not `bool(entry)` — the truthy-tuple trap S28 already records.
⚠️ **THE CORRECTION AWARDS NOTHING BY ITSELF**, and that is worth saying: all
fifteen ALSO have no authored bar, so they move from "blocked" to "unrated" and
join the ordinary queue. **What it removes is a FALSE blocker**, which would have
sent me implementing TIER 5 error cases to unlock TIER 1.
📋 **AND THE HONEST ANSWER TO "ALL ITEMS AT TIER 1 SHOULD BE WITHIN REACH": 157 of
167 ARE. TEN ARE NOT, AND NOT FOR WANT OF ROWS** — `LOCATE` (the cursor switch is
parsed, domain-checked and then IGNORED, deviation O-3), `SCREEN` (the key click
has no cell any row here can read), `VARPTR` (`VARPTR(#n)` is DEFERRED), `INPUT$`
(the console form is MISSING — `str_inputd` requires `,#f`), `SET`/`IPL`/`CMD`
(refuse-on-sight words with no happy path on this machine at all), and
`STICK`/`STRIG`/`PDL` (their rows read 0, which is correct with nothing plugged in
AND exactly what a stub returns — waiting on Joost's ruling about whether a
dedicated suite may supply the breadth). **Four of those need CODE, three need a
ruling, and three are not TIER 1 shaped at all.**
📈 **OF THE 87 REMAINING, 63 ALREADY HAVE AN AGREEING ROW AND NEED ONLY A BAR** —
the batch-8 shape, which awarded ten with no new rows. 14 need a row as well.
🚫 **D-KWREFUSE — `SET`, `IPL` AND `CMD` LEAVE THE STATEMENT DENOMINATOR** (Joost,
2026-09-14: *"Drop them and mark them"*, the same ruling he gave the particles).
All three answer **ERR 5 on BOTH references** — they are tokenised and then refused
— so they have **no happy path on this machine at all**, and a bar reading
"refuses correctly" would be a TIER 5 reading wearing a TIER 1 label. They stay in
the TOKEN denominator and get their own class in the table. **STATEMENT 167 → 164.**
Selftest **S35**. ⚠️ The class arm sits BEFORE the tier arms for the same reason
the particle arm does: all three have AGREEING rows, so without it they would
print as "1 row agrees" beside statements that actually do something.
🔪 **D-KWMATHCUT — THE FOURTH CUT SHAPE, AND IT WAS ONE PREFIX.** Hunting Joost's
goal showed the bottleneck is not bars: of the 63 statements holding an agreeing
row, **34 were NOT knife-connected**, so a bar would award them nothing.
🎯 `ev_ff_mathconv` (`basic/expr.asm:1698`) dispatches the arithmetic conversions
with **exactly the same `cp <TOK>` / `jp z,<target>` chain** as every other
selector — but its targets are named **`evmc_*`**, and `plant_fn` accepted only
`ev_*`. `evmc_abs` does not start with `ev_`. **Ten keywords had no cut at all for
the want of one prefix.**
🔴 **AND THE NAMESPACE GUARD IS WHY THIS WAS SAFE TO WIDEN.** `$86` really is in
both namespaces — `ABS_TOKEN equ $86` and `DIM_TOKEN equ $86` sit 53 lines apart
in `sysvars.inc` — but DIM dispatches through `stmt_table`'s `db token / dw
handler` entry, never through a `cp $86` followed by a `jp z` to an `evmc_*`
symbol, and the 23 `evmc_*` symbols exist ONLY in the math chain. The `jp z`
restriction is kept for the reason it was kept for `ev_`: the chain is a `jp z`
chain by construction, so an `evmc_` reached by `jr z` would be a HELPER, not a
selector [[a-shared-tail-is-not-a-decision]].
🔴 **AND THE FIRST SUCCESSFUL CUT WAS FILED UNDER THE WRONG KEYWORD — `ELSE`.**
`_kwtable_name` mapped a token back to a name by the TOKEN ALONE, and a two-byte
kwtable entry is `<prefix>,<token>`: `db 4,"ELSE",2,COLON,ELSE_TOKEN` and
`db 3,"FIX",2,PEEK_PREFIX,FIX_TOKEN` **share `$A1`**. So `--fn FIX:fix` recorded
its reading under ELSE — a keyword it has nothing to do with, and a PARTICLE,
therefore scored for nobody. ⚠️ **THE BYTE IS NOT THE KEYWORD; THE PREFIX IS PART
OF THE IDENTITY.** Same shape as every mis-attribution this sweep has turned up,
one level down. Fixed, and the stale `ELSE` entry removed from the pin by hand.
🟢 **TWELVE AWARDED: `ABS SGN INT FIX CINT CSNG CDBL SQR EXP LOG ERL ERR`** — all
N=1, one argument (or none) and one behaviour, each with a row already reading a
value a stub cannot fake. ⚠️ `INT` and `FIX` are separate keywords and NOT one form
sampled twice: INT FLOORS toward minus infinity where FIX TRUNCATES toward zero.
🔭 **`USR` STANDS AT 1/2** — MSX has TEN user-routine vectors and `USR<n>` selects
which, so the numbered form reaches a DIFFERENT ADDRESS and is not a second input
to the same behaviour. **92 of 164 at TIER 1.**
🔬 **AND THE REMAINING TWENTY NAME AT LEAST THREE MORE DISPATCH SHAPES**, each
refusing with its own count: the OPERATORS (`AND OR NOT XOR EQV IMP MOD` — the
expression parser's precedence walk, not a `cp` chain), the TRANSCENDENTALS (`ATN
SIN COS TAN RND` — `ev_ff_mathconv`'s own comment says they *"have no arm of their
own: they fall into the table scan below"*), and the string/number pair
(`ASC LEN` via `ev_ff_strnum`) plus `ATTR$ DSKI$ INKEY$ STRING$ CALL MAX`. **That
is the next apparatus slice, and it gates twenty statements.**
🔪 **D-KWOPCUT — THREE MORE CUT SHAPES, AND THE TWENTY ARE DOWN TO SIX.
106 of 164 at TIER 1.**
🔪 **FIFTH: the TRANSCENDENTAL TOKEN TABLE.** `ATN/SIN/COS/TAN/RND` have no `cp`
arm of their own — `ev_ff_mathconv`'s own comment says so — and `evmc_total_scan`
walks `evmc_total_tab`, five rows of `<selector token>, <entry low byte>`. The cut
is the row's TOKEN, the same *patch what the comparison reads* idea as every other
shape, and a miss falls through the function's own error path.
🔪 **SIXTH: the OPERATOR PRECEDENCE TABLE.** `IMP EQV XOR OR AND` are not reached
by a `cp` chain at all — the parser WALKS `logtab` (`db token, dw leaf`,
`$00`-terminated, loosest first). Stride 3, and DEADTOK `$FE` is a safe poison
there: it terminates nothing and matches nothing.
🔪 **SEVENTH: a `cp` SITE WHOSE ENCLOSING ROUTINE IS NAMED FOR THE KEYWORD.** The
standing rule is *"a conditional jump must follow, and its target must resolve to a
named evaluator"*, and three real shapes satisfy NEITHER half: `MOD` is
`cp MOD_TOKEN` / **`ret nz`** — no jump at all; `NOT` is `jr z,ev_not_do`, a `jr`,
which the `ev_*` arm deliberately refuses after the PEEK lesson; `ASC`/`LEN` are
`jr z,ev_ff_asc` / `jr z,ev_ff_len`. 🎯 **SO THE SITE IS IDENTIFIED BY WHERE IT
LIVES INSTEAD OF WHERE IT GOES.**
🔴 **AND THIS IS EXACTLY THE GUARD THE PEEK CASE NEEDED.** PEEK's lone `jr z` goes
to `ev_ff_ckaddr`, a SHARED ADDRESS-CHECK HELPER inside `ev_ff_arg` — neither name
contains "peek", so the shape declines and PEEK still falls through to the
`ev_ff_argtab` cut that IS its dispatch. **Re-measured: PEEK still cuts correctly.**
[[a-shared-tail-is-not-a-decision]]
🔴 **`LEN` THEN REFUSED WITH *TWO* SITES NAMED FOR IT, AND REFUSING WAS RIGHT.**
`$92`'s candidates were the real `jr z,ev_ff_len` and a byte coincidence beside
**`ev_ff_argtab_len`** — a LENGTH EQUATE, not a routine, whose name ends in "len"
by pure English. ✅ Ranked: **a jump TARGET naming the keyword outranks an
enclosing symbol that merely contains it**, because only one of them is something
the code JUMPS TO.
🟢 **FOURTEEN AWARDED: `ASC LEN ATN COS SIN TAN RND MOD AND OR XOR EQV IMP NOT`.**
⚠️ **THREE OF THEM NEEDED A ROW FIRST, ON THE OLDEST AXIS IN THE FILE: `SIN(0)` IS
0 AND SO IS A STUB**, and `TAN(0)` likewise; `COS(0)` is 1 and escapes it. New rows
read `SIN(1)*1000 -> 841` and `TAN(1)*1000 -> 1557`, scaled and truncated so the
reading is an INTEGER both machines must agree on rather than a float rendering.
🔴 **AND `RND` NEEDED ONLY A TAG — THE DUPLICATE-KEY GUARD CAUGHT THE ROW I WAS
ABOUT TO ADD, FOR THE SECOND TIME TODAY.** `rnd_b` already reads the RESEEDED draw
(438 on both references, since a negative argument reseeds and makes the sequence
reproducible); `rnd`'s `RND(1)<1` is a BOOLEAN true of any conforming
implementation. **Check whether the reading already exists before writing one.**
🔭 **SIX STILL REFUSE ALL SEVEN SHAPES: `ATTR$ DSKI$ INKEY$ STRING$ CALL MAX`** —
the next apparatus question, and a much smaller one than the twenty it started as.
🔬 **D-KWSIX — THE SIX ANSWERED, AND FOUR OF THEM WERE NOT CUT PROBLEMS AT ALL.**
**109 of 163 at TIER 1.**
🟢 **`DSKI$`, `STRING$` and `INKEY$` NEEDED NOTHING NEW.** The SEVENTH shape added
an hour earlier — *a `cp` site whose enclosing routine or jump target is named for
the keyword* — already reaches them: their `cp <TOK>` sites sit in
`basic/strvar.asm` inside routines named after them. ⚠️ **I WROTE A WIDENING FOR
THEM AND IT ASSERTED OUT, AND THE RUN SUCCEEDED ANYWAY** — the edit never applied,
which is how I learned it was not needed. *An edit script that refuses is cheaper
than one that silently works.*
🚫 **`ATTR$` IS A REFUSE-ON-SIGHT WORD AND THE EQUATE SAYS SO OUT LOUD**:
`ATTR_TOKEN equ $E9 ; ATTR$ — tokenised, then ERR 5 (no function)`, and the row's
own note agrees — *"bare ATTR$ raises Illegal function call"*. It joins
`SET`/`IPL`/`CMD` in `REFUSE_ONLY` and leaves the STATEMENT denominator.
🎯 **`MAX` HAS NO BARE FORM — IT IS `ON`'s SHAPE EXACTLY.** `MAX_TOKEN equ $CD ;
MAX — 1st half of MAXFILES`, and `kwtable.inc` holds `MAX` and `FILES` as SEPARATE
one-byte words. The row's note: *"bare MAX is a Syntax error on a real machine"*.
So `MAX` joins `NO_BARE_FORM` and **`MAX FILES` becomes a composite statement**
(UNRATED until it has a row of its own). **STATEMENT 164 → 163.**
🔴 **AND `CALL` AND `MAX` BOTH SCORE *RESERVEDNESS*, NOT BEHAVIOUR** — which is why
both came back 🔴 BLIND from a cut that WORKED. `callkw`'s exec is `CALL=1:...` and
`maxkw`'s is `PRINT"[";MAX;"]"`, and **both are a Syntax error on all three
machines**: cutting the handler cannot change a syntax error. ⚠️ **A BLIND VERDICT
ON A ROW THAT SCORES RESERVEDNESS IS NOT A BLIND ROW — IT IS A ROW MEASURING THE
TOKENISER.** `CALL <name>` needs an extension ROM the harness has no cartridge for,
so its happy path is not reachable here at all; that is a named block, not a
missing cut.
🔭 **`ATTR$`'s CUT SITE IS STILL UNEXPLAINED AND DOES NOT MATTER YET.**
`basic/expr.asm:547` is `cp ATTR_TOKEN` / `jp z,ev_f_attr` — a `jp z` to an `ev_*`
symbol, which the FIRST shape should match — and the knife reports **ZERO** sites,
not two. Left unchased because ATTR$ is refuse-only: it has no happy path to
connect to. ⚠️ **Worth returning to if another `ev_*`-targeted keyword ever reports
zero sites**, because the same cause would then be hiding a real cut.
⚡ **D-KWBARS — FIVE AWARDED AND THIRTEEN BARS AUTHORED THAT AWARD NOTHING.
114 of 163.**
🟢 **`SWAP` `DSKF` `MERGE` `FIELD` `CSAVE` AT N=1**, each with a row whose reading
can FAIL: `SWAP` reads BOTH variables back (` 2  1 `), so a swap that copied one
way shows; `DSKF` reads 707 free KB against a stub's 0; `FIELD` is a full
round trip — bind, LSET, PUT record 1, GET it back; `CSAVE` **reads the TAPE, not
the screen**, which is why it needs a blank-tape rig at all.
🎯 **`MERGE`'s READING IS AN ABSENCE, AND THAT IS THE POINT:** MERGE **returns to
command level**, so the row reads the marker BEFORE it and NOT the one after. The
marker before proves the program got that far, so the absence is a reading rather
than a silence.
🔴 **AND `SWAP` AND `DSKF` ARE THE FIRST AWARDS TO EXERCISE THE CORRECTED
OPEN-ITEM RULE.** `SWAP` carries an open **TIER 5** item and `DSKF` an open
**TIER 3** one; under the old reading of *"no open item"* both were barred from
TIER 1 by defects that say nothing about the happy path. Joost's ruling — *tier n
blocks tier n only* — is what lets them through, and the tier table still shows
their items beside them.
🔭 **THIRTEEN MORE BARS AUTHORED THAT AWARD NOTHING, WHICH IS WHAT A BAR IS FOR:**
`PAINT` 1/3 (a fill that ignored its BORDER leaks), `FRE` 1/2 (`FRE(0)` and
`FRE("")` are two different POOLS, not two inputs), `CLOAD` 1/2, `AUTO` 1/3,
`RESTORE` 1/2, `RETURN` 1/2, `RUN` 1/3, `IF` 1/3, `CLOSE` 1/2, `SAVE` 1/2
(tokenised against ASCII — two FILE FORMATS), `BSAVE` 1/2 (the optional ENTRY
address is what makes the image runnable), `BLOAD` 1/3.
🔴 **AND ONE OF THEM IS A REAL HOLE: `GOTO` HAS NO HAPPY-PATH ROW AT ALL.** Its
only row is the `PROVES-T3` `GOTO 9999` error case. **GOTO is the apparatus of
dozens of rows and the subject of none** — the same confusion as bare `PRINT`,
and the same answer: *being used is not being measured.*
⚠️ **`FRE`'s N=1 IS NOT MET BY `fre`**, which asks `FRE(0)>1000` — a BOOLEAN.
`fre_b` reads the DELTA across a `DIM`, which is what makes the reading
machine-independent; the absolute figure is not comparable between machines.
⚡ **D-KWGOTOROW — `GOTO`, `CLOSE` AND `FRE` CLOSE THEIR PARTIALS. 117 of 163.**
🔴 **`GOTO` HAD NO HAPPY-PATH ROW AT ALL** and now has one: `A=7` sits AFTER the
`GOTO 40` on line 10 and must be SKIPPED, so `[1e 0 ]` where a GOTO that parsed
and fell through reads `[1e 7 ]`. ⚠️ The padding is two long ASSIGNMENTS and not
`REM` — REM would swallow the rest of its line, the trap `onkw_b` already cost —
and it exists only to force the PRINT onto line 40 so the jump has a target.
Packing verified with `omsx_repl.as_stored` BEFORE the row ran.
🎯 **AND `GOTO` IS THE THIRD AWARD TO EXERCISE THE CORRECTED OPEN-ITEM RULE** — it
carries an open TIER 4 (speed) item, which says nothing about whether the jump
lands.
🟢 **`FRE` 2/2** — `FRE("")` reports the STRING pool, a different pool from
`FRE(0)`'s free RAM. Read as a DELTA across a 50-character allocation (`[ 50 ]`)
for the same reason `fre_b` is a delta: the absolute figure is machine-dependent.
🔴 **`CLOSE`'s BARE ROW TOOK THREE CUTS, AND THE FIRST TWO MEASURED THE APPARATUS.**
With two channels it read `Bad file number in 20` — **the default MAXFILES is
ONE**. With `MAXFILES=2` prepended it went DIVERGENT: zerobas `[ 5 ]`, the
reference a scrolled empty screen, because **MAXFILES performs an implicit CLEAR**
and the row was by then measuring five things at once. ✅ **ONE CHANNEL PROVES THE
SAME POINT** — bare `CLOSE` closes a channel it was NOT TOLD ABOUT, which is
exactly what `CLOSE #n` cannot exercise — with none of the apparatus.
⚠️ *Same lesson as `openkw_b`, which cost six sweeps: when a row needs a rig to
stand up, ask first whether a smaller row proves the same thing.*
⚡ **D-KWLISTSEL — `LIST` AND `FILES` CLOSE THEIR PARTIALS. 119 of 163.**
🟢 **`LIST` 3/3** — `LIST 20` reads `[A]|20 Z$="XXX..."` and `LIST 20-30` reads
both lines, so SELECTING is measured and not just printing. ⚠️ **THE FIRST CUT OF
BOTH LISTED NOTHING**, and the reason is the row: `PRINT"[A]":LIST 20` packs onto
ONE numbered line, so **line 20 did not exist**. Padded to three lines, verified
with `as_stored` first.
🟢 **`FILES` 2/2** — the BARE catalogue, whose whole listing is inside the compared
text. The existing row passes a PATTERN, so a FILES that IGNORED its argument
would pass it; this one has no argument to ignore.
🔭 **AND TWO ROWS WERE DROPPED RATHER THAN GUESSED AT A FOURTH TIME.**
**`PAINT` stays 1/3.** `PAINT(15,15),11,15` inside a drawn box read `?nomarker` on
BOTH machines; reduced to `SCREEN2:PAINT(15,15),11,15` with no box it read
`?nomarker` again — **but with nothing to stop it that floods the WHOLE screen**,
which is slow, so the second reading cannot separate *"the 3-argument form
faults"* from *"the flood outran the capture"*. 🔴 **THE BAR STAYS AT N=3**: the
spec is explicit that the border IS supported here (`spec-basic-graphics-g5.md` —
the FOURTH argument is the ERR 2, and the border is parsed and range-checked), so
this is a missing ROW, not a missing form.
**`SAVE` stays 1/2.** Its `,A` row read `[ 49 ]` on zerobas — the first byte of the
listing, exactly as designed — and NOTHING on the reference, which is a divergence
about the APPARATUS as easily as about SAVE: writing then reopening a file inside
one sweep row is the shape `openkw_b` needed six sweeps to get right.
⚠️ **BOTH NEED AN ISOLATED `scratchpad/` PROBE WITH ITS OWN TIMING**, the way
`clearhimem_probe.py` and `vdpie_probe.py` settled their questions. *Three
guesses is where guessing stops.*
🔴 **AND THE ISOLATED PROBE FAILED ITS OWN CONTROL — `scratchpad/paintarg_probe.py`
MEASURES NOTHING YET, AND SAYS SO.** `bounded2`, the known-good TWO-argument shape
the sweep scores successfully every run, reads EMPTY inside the probe. So the
capture shape is wrong, not PAINT — **the fourth apparatus fault in a row about
apparatus.** Three causes ruled out and recorded so the next attempt does not
repeat them: not the echo anchor alone (`capture="screen"` changed nothing), not
the refcache (`ZEROBAS_REFCACHE=0` changed nothing — though the FIRST run had been
served **3 cached readings**, which is the *a gate measures, it never replays*
hazard arriving in a scratchpad probe), and not slowness (`cap_gap=25.0`,
`timeout=420.0`, far beyond the sweep's).
🎯 **THE NEXT STEP IS TO MIRROR `basic_probe_kwsweep`'s NOECHO CAPTURE**
(`marker_tail` plus the `capture="screen"` contract) rather than assume
`run_cases`' defaults resemble it. ⚠️ **A PROBE WHOSE CONTROL FAILS MEASURES
NOTHING, AND SAYING SO IS THE WHOLE VALUE OF HAVING HAD A CONTROL** — without it
I would now be reporting that PAINT's 3-argument form faults on both machines.
✅ **AND THE PROBE NOW WORKS — THE FAULT WAS THE *REPORTING*, NOT THE CAPTURE.**
I was slicing `raw[-76:]`, the BOTTOM of a 24×40 screen dump, and **`SCREEN 0`
HOMES THE CURSOR**, so these cases print at the TOP and the tail holds nothing but
the function-key line. `clearhimem_probe.py` gets away with a tail slice only
because its cases never change SCREEN. ⚠️ **AND I ONLY FOUND IT BY DUMPING THE RAW
CAPTURE** — every earlier attempt reasoned about what the capture contained
without looking at it.
📊 **MEASURED, AND IT IS NEITHER OF THE TWO THINGS I SET OUT TO SEPARATE.** On
**BOTH** machines, identically:
| case | reading |
|---|---|
| `PAINT(15,15),15` — fill colour EQUAL to the box | `[P 15  4 ]` |
| `PAINT(15,15),11` — a DIFFERENT fill colour | never reaches the PRINT |
| `PAINT(15,15),11,15` — 3-argument, border = the box colour (CORRECT usage) | never reaches the PRINT |
| the same under `ON ERROR GOTO` | **the handler NEVER FIRES** |
🎯 **SO THE SWEEP'S `paintkw` ROW PASSES ONLY BECAUSE ITS FILL COLOUR EQUALS THE
BOX COLOUR** — the fill stops on its first cell. Every row with a different fill
colour, with or without an explicit border, outruns the capture. **And it is NOT
raising an error**: the trap never fires, so it has simply not finished 30 seconds
of capture gap later.
🔴 **WHAT THIS DOES NOT SAY: THAT THE 3-ARGUMENT FORM IS BROKEN.** No error is
raised, both machines behave identically, and `spec-basic-graphics-g5.md` is
explicit that the border is parsed and RANGE-CHECKED here. **PAINT stays at 1/3
for want of a ROW, not a form**, and the next question — *"the border is not
honoured so it floods"* versus *"PAINT is simply this slow in SCREEN 2"* — wants a
measurement below.
🔴 **AND IT IS NOT SPEED — MEASURED, NOT ASSUMED.** A TINY box,
`LINE(10,10)-(14,14),15,B` (an interior of about FOUR PIXELS), with an explicit
border EQUAL to the box colour, **does not complete either, on either machine**.
A four-pixel bounded fill cannot be a timing problem.
🛑 **SO THE STATE OF THE QUESTION IS:** `PAINT(x,y),C` with C different from
what it is filling over does not complete through this harness — bounded or
unbounded, with or without an explicit border, raising NO error — and **BOTH
MACHINES DO IT IDENTICALLY**. That last part is what matters: **it cannot be a
faithfulness defect, because the VG-8020 reference behaves the same.** It is a
property of PAINT under emulation, or of the harness, and it is NOT a divergence.
⚠️ **PAINT STAYS AT 1/3 AND ITS OTHER TWO FORMS ARE NOT MEASURABLE THROUGH THIS
INSTRUMENT.** The one question the probe has NOT yet asked, and the place to
start: **is the emulated machine still ALIVE after the PAINT?** Type a direct-mode
command after `RUN` and see whether it answers — that separates *"the interpreter
is stuck inside PAINT"* from *"the capture is looking in the wrong place"*.
⚡ **D-KWIF2 — `IF` AND `USR` CLOSE THEIR PARTIALS. 121 of 163.**
🟢 **`IF` 3/3.** `ifkw` takes the THEN branch, so it could see neither an ELSE
parsed and dropped nor `IF <expr> GOTO <line>`, which is a DIFFERENT GRAMMAR and
not a THEN with a GOTO after it. `ifkw_b` reads `[1h]` (the ELSE branch, taken
because the condition is FALSE) and `ifkw_c` reads `[1j 0 ]` (`A=7` sits AFTER the
jump and must be skipped).
🔴 **AND `ifkw_b` IS STORED THOUGH IT FITS DIRECT.** At **exactly 38 characters**
it clears the `MAX_DIRECT` guard and still came back `?noecho` on BOTH machines:
**the ceiling is reachable but the echo is not usable there.** Same lesson
`vpoke_b2`'s note already records at 37 — *"it passed alone and failed in
company"*. Stored with its own marker instead.
🟢 **`USR` 2/2.** MSX has TEN user-routine vectors and `USR<n>` selects which, so
the numbered form reaches a DIFFERENT ADDRESS — not a second input to one
behaviour. `DEFUSR1` points at a bare `ret` and `USR1(7)` returns its argument:
`[ 7 ]`. **A USR that ignored the digit would read vector 0, which this row never
sets.**
⚡ **D-KWRETRES — `RESTORE`, `RETURN`, `WAIT` AND `RESUME` CLOSE THEIR
PARTIALS, AND `MAX FILES` GETS ITS FIRST ROW. 125 of 163.**
🟢 **`RESTORE` 2/2 and `RETURN` 2/2 — both LINE forms.** `restorekw_b`
reads `[1k 7  11 ]`: the first `READ` takes line 30's `DATA 7`, `RESTORE 50` moves
the pointer to line 50 and the second takes 11. **A bare `RESTORE` would read 7
again and no `RESTORE` at all would read 9**, so 11 is reachable only by honouring
the LINE. `returnkw_b` reads `[1l 5 ]`: `GOSUB 50` lands on `A=5:RETURN 40` and
line 40 is the `PRINT`, while a bare `RETURN` would resume after the `GOSUB` and
run line 30's `A=A+1` — 6, not 5.
🟢 **`WAIT` 2/2 — the third operand, which INVERTS the test.** The same
port the existing row uses carries it: `INP(&HA8)` is 240 on both machines, so its
LOW NIBBLE is zero. `WAIT &HA8,&H0F` alone would spin **for ever**;
`WAIT &HA8,&H0F,&H0F` returns at once because the xor turns those four zero bits
into ones. **A `WAIT` that PARSED the xor and dropped it does not come back**, so
the `[1m]` is the operand being APPLIED and not merely accepted.
🟢 **`RESUME` 3/3 — the other two destinations.** `resumekw_b` (bare)
repairs the cause in the handler (`B=9`) and reads `[1n 3 ]`: `SQR(B)` **ran a
second time**. `RESUME NEXT` would skip it and print 0 — the value an unassigned
`A` already has, which is exactly why the repaired value had to be non-zero.
`resumekw_c` reads `[1o 7 ]`: the handler names line 40, and line 30's `A=8` sits
between the failure and that `PRINT`, so `RESUME NEXT` reads 8 and only an
honoured line number reads 7.
🌱 **`MAX FILES` now has a bar (N=1, `MAXFILES=<n>` is the whole syntax) and
a row.** `maxfiles` is disk-free and scores the part a parse-and-ignore cannot
fake: the assignment **re-allocates the file-control blocks and performs an
implicit CLEAR**, so the 7 assigned one statement earlier is gone — `[1p 0 ]`,
where a `MAXFILES` that only parsed reads `[1p 7 ]`. That the second channel then
really exists is shown independently by `openkw_b`'s `AS#2`.
🔴 **AND IT IS STILL NOT AT TIER 1, FOR A REASON THAT IS NOW THE BIGGEST
SINGLE BLOCKER LEFT: `knife_connected()` IS KEYED BY A `stmt_table` ENTRY AND A
COMPOSITE HAS NONE TO CUT.** All **19** composite and channel statements sit
behind that one missing instrument — nineteen of the 38 statements still short
of TIER 1. It is a missing cut shape, not a missing behaviour.
⚠️ **All five rows need EXACT NUMBERED LINES or an exact port value, and every
packing was verified with `omsx_repl.as_stored` BEFORE the row ran** — the
padding is long ASSIGNMENTS, never `REM`.
⚡ **D-KWONTRAP — THE COMPOSITES WERE NEVER BLOCKED ON AN INSTRUMENT. 129 of
163, and 15 of the 19 composite statements are at TIER 1.**
🔴 **THE BLOCKER I FILED YESTERDAY WAS A SENTENCE IN A DOCSTRING, NOT A
FACT.** `_composite_section` said *"none of them can reach TIER 1 today"* because
`knife_connected()` is keyed by the `stmt_table` entry a cut removes and a
composite has none of its own. **The instrument already existed**: `record()` also
files a cut under the SUBJECT of the row that responded to it, so cutting `ON`,
`DEF` or `MAX` connects the composite its row is about. `PRINT USING` — whose
`USING` token is not in `stmt_table` **at all** — was already TIER 1, which is the
proof the keying was the only thing in the way. ⚠️ **RE-VERIFY A BLOCKER BEFORE
BUILDING ON IT** cost nothing here only because I read the rendered table instead
of the docstring.
🟢 **`MAX FILES` 1/1** — the row from D-KWRETRES, now CONNECTED by cutting
`MAX`'s entry.
🔴 **AND ITS `SUBJECT:` TAG IS LOAD-BEARING FOR A REASON WORTH KEEPING:**
the crunch word is `maxfiles=2`, ONE word, and `stmt_keyword` reads WORDS — so the
row scored for NOBODY until the tag named the composite the tokeniser splits it
into.
🟢 **`ON INTERVAL GOSUB` 2/2 and `ON SPRITE GOSUB` 2/2** — the two of `ON`'s
six trap composites reachable from BASIC alone (a timer fires itself; a collision
is caused by putting two sprites on top of each other). Each has an ARM row and a
DISARM row, because the BARE form clears the handler slot while leaving the trap
enabled — measured in both specs (`R_bare_disarms`). The sprite pair is the sprite
-trap probe's own `HIT`: one solid 8x8 pattern at (100,100) and (104,100).
🔴 **`INTERVAL` IS NOT A KEYWORD-TABLE ENTRY** — it is a compound reserved
word (`iv_seq` = `INT` + `"ER"` + `VAL`), so `stmt_subject` could not see it and
derived **`ON GOSUB`**, crediting the INTERVAL trap's readings to a statement that
already had its own row. Measured, not feared: the first knife run recorded them
there, and the pin had to be repaired by hand. Both rows now declare
`SUBJECT:ON_INTERVAL_GOSUB`.
🟢 **`DEF USR` 2/2.** `usrkw`/`usrkw_b` are `USR`'s rows — their subject is
the FUNCTION that reads the vector, so cutting `DEF`'s entry is a cut neither can
speak for. The two new rows carry the same bodies under their own subject for
exactly that reason: what the reading proves here is that **the `DEF USR`
STATEMENT is what put the address in the cell**.
🔭 **FOUR COMPOSITES LEFT, AND NONE IS AN INSTRUMENT PROBLEM**: `ON KEY
GOSUB`, `ON STOP GOSUB` and `ON STRIG GOSUB` need a KEY OR A TRIGGER PRESSED (the
injection rig), and `INPUT$` needs its console form implemented. All three ON-trap
bars are still UNAUTHORED — author them from the specs in the same slice that
gives them rows, not before.
🚧 **The `IF` in a wait loop must END ITS LINE.** A FALSE condition skips
the REST OF THE LINE, not just the `THEN`, so `IF C=0 THEN 50:SCREEN0` never runs
`SCREEN0`. Every wait loop here is padded out to its own line.
⚠️ **And the loops count FRAMES, never ITERATIONS** — `IF C=0 THEN <own
line>` and `IF TIME-T<30`, never a `FOR`: the two machines differ in interpreter
speed by 2.5–3.8x, so a counted loop measures the INTERPRETER. For the same reason
the arm rows read `C>0` and not `C`.
⚡ **D-KWHOLD — THE INJECTION RIG (Joost: *“build the injection rig”*), AND IT
LANDS TWO COMPOSITES. 131 of 163, 17 of the 19 composite statements.**
🟢 **`NEEDS-HOLD:<row>,<mask>` IS THE SIXTH RIG, AND THE ONLY ONE THAT TAKES
AN ARGUMENT.** It holds one KEY-MATRIX bit down for the whole of a case's `RUN`.
`omsx_repl.run_cases` has carried the `holds=` seam since the input-devices arc;
this only routes it per row, and the argument is part of the capture GROUP KEY, so
two rows holding different keys are captured in different batches — one `holds`
value per batch is all the timeline can express.
🔬 **THE CONTROL CAME FIRST AND IS IN THE SWEEP FOR GOOD.** `strig_hold` holds
the SPACE BAR (row 8, bit 0) and waits up to 120 FRAMES for `STRIG(0)` to answer
−1. It reads `[1w-1 ]` on BOTH machines. It carries **no `FORM:` tag and awards
nothing**: if it ever reads `[1w 0 ]` the rig is not reaching the matrix and nothing
that depends on it may be believed. Every STICK/STRIG/PDL row in the file reads the
IDLE value, which is 0 — exactly what a stub returns.
🟢 **`ON STRIG GOSUB` 3/3 and `ON KEY GOSUB` 3/3**, authored from the two trap
specs: ARM from a single-entry list, the POSITIONAL list, and a listed-EMPTY slot
clearing that handler (`spec-traps-t2-strig.md` Q1/R5/S3, `spec-traps-t3-key.md`
K1/K8/T5). **Trigger 0 IS the space bar**, which is why all three STRIG forms are
reachable with a key matrix and no joystick; the KEY rows hold F1 (`6,$20`) and F2
(`6,$40`).
🎯 **ONE PRESS IS ENOUGH FOR THE POSITIONAL FORM**: the reference fires slot
*n* for trigger/key *n*, so `60,80` reads `[1y 1 ]` where a list that armed its LAST
entry would read 2 from the same press — and the KEY row reads `[2b 2 ]` because
only `KEY(2)` is enabled.
🔴 **AND THE FIRST CUT OF THE `ON KEY` ROWS WAS `?noecho` ON THE REFERENCE AND
A CLEAN READING ON ZEROBAS — AN APPARATUS FAILURE THAT READS EXACTLY LIKE A
DIVERGENCE.** The hold lasts ~12 emulated seconds and the program finishes in ~2.4,
so the key AUTO-REPEATS at ~17 Hz into the BASIC prompt for the rest of it and each
repeat types the function key's EXPANSION — `color ` × ~160, which scrolled the
marker off the screen. **The reference is 2.5–3.8× faster, so it got far more
repeats than zerobas did**: interpreter speed leaking into a reading for the sixth
time this arc. Fixed with `KEY n,""` as each row's FIRST statement — an empty
expansion still fires the trap (the event is upstream of string expansion,
`spec-traps-t3-key.md` §1.1 R8/R9) and types nothing.
🔭 **TWO COMPOSITES LEFT.** `ON STOP GOSUB` needs **Ctrl-STOP, which is TWO
keys on different matrix rows** (CTRL row 6 bit 1 + STOP row 7 bit 4) and `holds`
takes ONE `(row, mask)` per case — a real extension, not a row. `INPUT$` needs its
console form implemented (item D).
📏 **AND THE REAL SHAPE OF WHAT IS LEFT, COUNTED RATHER THAN GUESSED:** of the
32 statements still short of TIER 1, **~20 are UNRATED — they have rows and a knife
cut and no AUTHORED FORM LIST at all** (`CALL` `CONT` `DATA` `DELETE` `DRAW` `FN`
`FOR` `KEY` `LOAD` `MOTOR` `NAME` `OPEN` `PAD` `PDL` `PLAY` `RENUM` `SPRITE` `STICK`
`STRIG` `VAL`). The open TIER 4/5 items on several of them are **not** what holds
them back — `blocks_tier1()` reads tier 1 only. **Authoring those bars from the
reference's syntax is the next line of work**, and it is bookkeeping only where the
existing rows already cover the bar.
⚡ **D-KWBARS — FOUR UNRATED KEYWORDS GET A BAR, AND ONE OF THEM HANDS BACK A
SHIPPED DEFECT. 135 of 163.**
🟢 **`VAL` 5/5**, authored from `docs/spec-basic-val.md`, which measured the
reference across 40 shapes: a signed INTEGER, a FRACTION, an EXPONENT, a RADIX
PREFIX (`&H`/`&O`/`&B`) and a PARTIAL PARSE that stops at the first byte it cannot
use. **VAL never raises on junk — it returns 0** — so every one of these is a
SILENT wrong answer when it is missing. All five agree today; the 20 divergences
that doc recorded in August are closed.
🟢 **`FOR` 3/3.** Every `FOR` in the sweep was a `NEXT` row's apparatus, and a
loop that runs is not the same claim as a loop whose TERMINATION was decided
correctly. The implied step of 1 (`[ 6 ]`), an explicit `STEP 4` (`[ 15 ]`, where a
STEP parsed and dropped reads 45) and a NEGATIVE step (`[ 321 ]`, where the
ascending comparison runs the body once and reads 3).
🟢 **`FN` 2/2**, the CALL side of `DEF FN`. 🔴 **`fnkw` IS STORED THOUGH IT
FITS DIRECT, and the first cut says why: `DEF FN` IS ILLEGAL DIRECT, so the direct
form scored SUPPORTED on `Illegal direct` from BOTH machines** — an agreement about
nothing [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
🔴 **`DATA` 4/4 — AND IT TOOK A CODE FIX, FOUND BY THE KNIFE REPORTING BLIND.**
Cutting `DATA`'s `stmt_table` entry moved nothing, because with the `DATA` after the
`END` the statement is NEVER EXECUTED: READ finds the text by SCANNING the program.
Putting the `DATA` FIRST — `DATA 42:READ A:PRINT A` — put the handler on the path,
and the row came back **`Syntax error in 10` on zerobas where both references read
42**.
🔬 **ISOLATED IN `scratchpad/datacolon2_probe.py`, WITH A CONTROL, 6 rows:** the
DATA-after-END shape agrees (the control), `DATA 5:PRINT` agrees (nothing READS),
and every shape that READS an item out of a `DATA` with a statement after it fails
— `DATA AB:READ A$` read **the whole rest of the line, TOKENS and all**, into `A$`.
🎯 **THE PREMISE WAS RIGHT AND THE CONCLUSION WAS BACKWARDS.** The numeric arm
of `read_one_value` carried *"the tokeniser ends a DATA body AT a ':' (tk_data_rest),
so a stored body never contains one and this needs no ':' arm"*. The first half is
true and is exactly **why** the arm is needed: the body ends at the `:`, so the byte
the scan stops ON is that `:` — neither `,` nor NUL — and it fell into the TRAILING
JUNK path. **D-DATACOLON fixed the tokeniser and the runtime SKIP and left the
CONSUMER**; nothing had ever read an item out of such a DATA
[[a-fix-falsifies-the-justification-beside-it]].
💰 **+8 B, and they are SUB-ROM PAGE-0 bytes, not main page 1**: `readdata_tenant`
lives there. `make basic-reloc` from a clean tree, 2026-09-15: **sub page 0 free
513 B → 505 B**; page-1 free 8 B and the low region 0 B, both UNCHANGED. Two arms of
four bytes each: `cp COLON / jr z,rov_seek` in the numeric path and
`cp COLON / jr z,rovs_done` in the UNQUOTED string loop. ⚠️ **The QUOTED loop must
NOT have it** — a `:` inside quotes is content (D-DATACOLON `d.qcolon`).
🌱 **All four `DATA` rows now put the `DATA` FIRST**, so every one of them
exercises the colon terminator and the execution path at once.
⚡ **D-KWPLUG — THE SEVENTH RIG, AND FOUR INPUT-DEVICE BARS THAT SAY WHAT IS
REALLY MISSING. 136 of 163.**
🟢 **`NEEDS-PLUG:<port>,<device>` becomes openMSX's `plug joyport<port>
<device>`**, run once before the timeline. It exists because a device that is
merely PLUGGED already changes what the reference reports, and nothing else here
can drive one: openMSX offers no host paddle to TURN.
🔴 **AND THAT IS WHY `pdlkw` AND `padkw` PROVED LESS THAN THEY LOOKED.** They
read the IDLE line of an EMPTY port — **255 is as much a constant as 0 is**, so a
`PDL` that answered 255 to everything passed. With a paddle in port A the value is
**128**; with an arkanoidpad `PAD(0)` is **−1** (touch sense) and `PAD(1)` is
**255** (the X coordinate, a different quantity). Every figure is
`basic_probe_input_devices.py`'s own measured table, not a guess.
🟢 **`PDL` 1/1 → TIER 1.** One behaviour: read paddle *n*. Which port an index
falls in is addressing, not a second behaviour.
📏 **`PAD` 2/3, `STICK` 1/2, `STRIG` 1/2 — AND THE MISSING FORMS ARE NAMED
RATHER THAN LEFT AS A BLANK.** `PAD`'s SWITCH cannot get a row with this
instrument (openMSX offers no host button, and an unpressed switch reads 0 — what
a stub reads). `STICK(0)` reads the CURSOR KEYS off the matrix and `STICK(1)/(2)`
read a JOYSTICK PORT's direction lines — different hardware, different code inside
GTSTCK — and openMSX's joystick is driven from the HOST, which the emulated key
matrix cannot reach. `STRIG` splits the same way: the SPACE BAR off the matrix, the
triggers off the PSG.
🌱 **`stick_hold` reads `[2d 1 ]` with CURSOR-UP held** (matrix row 8, bit $20)
where `stick` reads the idle 0, and the direction CODE separates it from any
non-zero constant.
🔴 **`strig_hold` NOW CARRIES `FORM:space-bar` AS WELL AS BEING THE RIG'S
CONTROL, and that is not a conflict**: if it ever reads `[1w 0 ]` the matrix is not
being reached and STRIG loses the form in the same breath. One row, both jobs, and
the failure is loud either way.
⚡ **D-KWOSK — `OPEN` AND `SPRITE` REACH TIER 1, AND `KEY`'s TWO DISPLAY FORMS
ARE REFUSED A ROW ON PURPOSE. 138 of 163.**
🟢 **`OPEN` 4/4.** `openkw` is FOR OUTPUT and `openkw_b` FOR INPUT; APPEND and
the FOR-LESS RANDOM mode had no row of their own — the random-access rows USE the
FOR-less form, but their subject is `FIELD` / `GET #` / `PUT #`. `open_c` reads
**9 bytes, measured**: `AB`+CRLF twice is 8 and the sequential `CLOSE` adds the
`$1A` end marker, so an APPEND that TRUNCATED (what FOR OUTPUT does to an existing
file) reads 5. `open_d` reads `PQRS` back through `FIELD`/`PUT`/`GET`, which a
sequential channel refuses.
🟢 **`SPRITE` 3/3.** The existing rows write a PATTERN; the trap STATE is the
other half, and the only way to see it is the collision trap D-KWHOLD already
built. 🔴 **`SPRITE STOP` IS NOT A THIRD BEHAVIOUR** —
`docs/spec-traps-t4-sprite.md` §1.3 `G_stop_latch` measured it identical to
`SPRITE OFF`, no latch — so `sprite_stop` is the DISABLE form sampled twice. It is
there anyway: a tree that made STOP a no-op would leave the trap enabled and no OFF
row could see it.
🔴 **AND BOTH DISABLE ROWS CAME BACK `?nomarker` ON BOTH MACHINES AT FIRST —
THE PROGRAM WAS STILL WAITING WHEN THE CAPTURE WAS TAKEN.** They waited 120 frames
(2.4 s) for something that must NOT happen, which is the whole capture window; the
ENABLE row exits early on the first fire and so never showed it. **A trap that
fires once per COLLIDING FRAME needs no long window** — 30 frames.
🚫 **`KEY ON` / `KEY OFF` HAVE NO ROW, AND THE REASON IS MEASURED.** The obvious
instrument is the FUNCTION-KEY LINE in VRAM, which `KEY OFF` blanks — but its
layout is **not the same on the two machines**: `PEEK(&HF3B0)` (LINLEN) reads **37
on the VG-8020 and 39 on zerobas**, and the reference's assigned string lands at
name-table offset 922 where a fixed offset reads a space on the other side. The
first cut of those rows scored **SUPPORTED on `32` from BOTH machines — an
agreement about a blank cell**. `scratchpad/keyline_probe.py` is the scan that said
why; the display forms stay UNCOVERED rather than measured wrongly, and `KEY` is
1/4 with the gap NAMED.
⚡ **D-KWMOTOR — `MOTOR` AND `NAME` REACH TIER 1, AND THE SCOUT THAT GOT THEM
THERE ALSO CLOSED `DELETE` AND `RENUM`. 140 of 163.**
🟢 **`MOTOR` 3/3, and the row that was there PRINTED A CONSTANT.**
`MOTOR OFF:PRINT"[ok]"` scored ABSENCE and nothing else — a MOTOR that parsed and
did nothing passed it. **Bit 4 of PPI port C IS the motor line**: `INP(&HAA)AND16`
is 16 with the motor off and 0 with it on, so all three forms are readable, the
BARE one included — it TOGGLES, and started from OFF it reads 0.
🔴 **THE MASK IS LOAD-BEARING, NOT TIDINESS.** The WHOLE port reads **90/74 on
the VG-8020 and 87/71 on zerobas** (`scratchpad/mdr_probe.py`): the other bits
differ between the machines, and a raw `INP(&HAA)` row would report a DIVERGENCE
THAT IS NOT ONE. Masked to bit 4 both machines agree exactly.
🟢 **`NAME` 1/1**, which had no row at all. The reading is that the NEW name
carries the OLD file's bytes — create `NM.TXT` with `AB`, rename, reopen under the
new name, read `LOF`: **5**. That the statement did not raise is not the same
claim.
🚫 **AND THE SAME SCOUT CLOSED `DELETE` AND `RENUM` FOR THIS INSTRUMENT.**
`DELETE 20` inside a running program **stops it cleanly on both machines** — the
statement after it is never reached — so every range form of DELETE has the SAME
observable as every other and the bar cannot be separated. `RENUM 100` at line 20
answers **`Undefined line 100 in 20` on both**: the renumbering breaks the
execution pointer, so its only reading is an ERROR, which is a TIER 5 reading
wearing a TIER 1 label. Both stay UNRATED on purpose rather than carrying a bar
their rows could never satisfy.
🔴 **WITHDRAWN 2026-09-16 (D-KWEDIT) — THAT CLOSURE WAS ABOUT THE MODE, NOT THE
VERBS, AND BOTH ARE NOW AT TIER 1.** Joost: *"It seems easy to fix Renum and
delete tests. Just validate the program in ram or llist it."* He is right, and the
paragraph above measured two DIRECT-MODE EDITOR COMMANDS from inside a RUNNING
PROGRAM. That is what produced both symptoms: run mid-program, `DELETE` stops the
run (so every range form has the same observable — nothing) and `RENUM` breaks the
execution pointer (so its only reading is an error). Typed at the prompt there is
no run to stop and no pointer to break, and **the program text afterwards
separates every form exactly**.
🔬 **NEITHER READOUT HAD TO BE BUILT.** `NEEDS-LOG:` (D-KWLOG) already puts a
listing in a HOST FILE — not bounded by 40 columns, which is the trap a screen
scrape would have walked into — and `capture=("stored_line", TXTTAB)` already
reads program text out of RAM. What was missing was a row that could put a
MULTI-LINE program in place to be edited: the `PROGRAM:` tag, eight lines in
`basic_probe_kwsweep.py`, stating COMPLETE numbered lines.
⚠️ **NOT `as_stored`** — it PACKS statements greedily into ≤34-char bodies, so
`REM Z1:REM Z2:REM Z3` becomes ONE line; `DELETE 20` would then have deleted the
whole program **on both machines, agreeing, with nothing to see**. Padding the
REMs to defeat the packer would have made the rows' validity depend on a length
constant nobody would think to re-check.
📏 **MEASURED, EIGHT ROWS, `SUPPORTED` 362 → 370:**
| row | reference reading |
|---|---|
| `DELETE 20` | `10 REM Z1` / `30 REM Z3` |
| `DELETE 20-30` | `10 REM Z1` |
| `DELETE -20` | `30 REM Z3` |
| `DELETE 20-` | **`Illegal function call`** |
| `RENUM` on 5/7/9 | `10` / `20` / `30` |
| `RENUM 100` | `100` / `110` / `120` |
| `RENUM 100,7` | `5` / `100` / `110` |
| `RENUM 100,,20` | `100` / `120` / `140` |
🔴 **AND ONE OF THEM IS NOT A FORM.** `DELETE <from>-` is REFUSED where
`DELETE -<to>` is accepted, so MSX1 DELETE has **three** selections and not the
symmetrical four. Its row is kept without a `FORM:` tag: its reading is the same
`Illegal function call` the `deletekw` row already gets for a line that does not
exist, and a second row agreeing on the SAME ERROR would inflate the bar while
testing nothing new.
⚠️ **THE RENUM ROWS START AT 5/7/9 ON PURPOSE** — bare `RENUM` renumbers from 10
by 10, so on an already-10/20/30 program it is a no-op and the row would be
agreeing on a constant.
🎯 **`DELETE` 3/3 and `RENUM` 4/4, both CONNECTED, both TIER 1.**
⚡ **D-KWSTOP — THE RIG LEARNS A TWO-KEY COMBO, `ON STOP GOSUB` REACHES TIER 1,
AND THE PROBE THAT GOT IT THERE FOUND A DIVERGENCE. 141 of 163, and 18 of the 19
composite statements.**
🟢 **`holds` NOW TAKES A SEQUENCE OF `(row, mask)` PAIRS**, pressed at one
emulated instant in the order given and released in REVERSE — the modifier first,
released last, which is what `basic_probe_stop_trap.py` and `key_trap`'s
`shift_tap` already did by hand. Ctrl-STOP is CTRL row 6 bit `$02` plus STOP row 7
bit `$10`, two keys on DIFFERENT ROWS, and that is the whole reason `ON STOP
GOSUB` had no row while its five siblings got theirs. Backward compatible by
SHAPE, not by a flag.
🔴 **AND THE DEFAULT TIMING BLANKS THE REFERENCE'S SCREEN — BOTH HALVES OF IT.**
Measured one variable at a time (`scratchpad/ctrlstop_probe.py`): a **2 s**
Ctrl-STOP reads a clean `Break in 20`, while **5 s and the 12 s default leave the
VG-8020's screen COMPLETELY BLANK** — no program, no `RUN`, nothing; and pressing
at the default RUN+0.3 blanks it too, where RUN+step+0.5 (the program already
looping) is clean. CTRL alone and STOP alone at 12 s both leave the program running
to completion, so it is **the COMBO and it is the DURATION**, and it is the
reference's own behaviour rather than an injection fault. zerobas does not do it,
so its side of the same run read normally — **an apparatus asymmetry that reads
exactly like a divergence**, and it was found by DUMPING THE RAW CAPTURE.
🌱 The tag carries both: `NEEDS-HOLD:6,0x02+7,0x10@0.5/2.0` is keys, then
`@<lead>/<secs>`, and the whole tag is part of the capture GROUP KEY.
🟢 **`ON STOP GOSUB` 2/2.** `onstop` reads `[2q-1 ]` — Ctrl-STOP reached the
HANDLER instead of breaking the program, which is what the statement is FOR.
`onstop_b` reads `Break in 30`: the bare form CLEARS the slot, and 🔴 **unlike
SPRITE and KEY a cleared slot with the entry still ON does NOT swallow the event —
both machines BREAK**, which is exactly what makes the two forms separable. (It
also re-verifies `spec-traps-t4-sprite.md` §1.5: T1 shipped ERR 2 for the bare
form, and both machines accept it today.)
🔴 **THE ARM ROW DOES NOT `STOP OFF` BEFORE IT PRINTS, AND THAT IS THE FINDING**
— the shape that does diverges, and is now a TIER 3 item of its own.
⚡ **D-KWSAVE — `BSAVE` REACHES TIER 1, AND THE WRITER-ORDERING RULE IS PAID FOR
A SECOND TIME. 142 of 163.**
🟢 **`BSAVE` 2/2 — the optional ENTRY ADDRESS, read straight out of the file
HEADER rather than by running anything.** A BSAVE image is
`$FE,start:2,end:2,entry:2` little-endian, so byte 7 is the entry's HIGH byte:
`[2t 201 ]` = `$C9`. 🔴 **THE ENTRY IS `&HC900` AND THE RANGE IS `&HC800`, AND
THAT GAP IS THE WHOLE ROW**: the three-argument form writes an entry too — it
DEFAULTS to the start — so an entry equal to `&HC800` would read 200 either way
and separate nothing.
🔴 **AND IT HAD TO MOVE TO THE END OF THE DISK ROWS.** Placed beside `bsave` it
sat UPSTREAM of every reader, and `open_c` — green on its own and green in the
batch before this row existed — came back with a **BLANK REFERENCE SCREEN, echo
and all**. A writer goes LAST; `openkw_b`'s note already carries that rule, and
this is the second time it has been paid for.
🌱 **`open_c` is now TWO opens instead of three**: `LOF` on the APPEND channel
sees the `AB`+CRLF+`$1A` that is already there — 5, where an APPEND that TRUNCATED
reads 0 — and the three-open version was slow enough on the CF-3300 to be worth
losing anyway.
🔴 **`SAVE` STAYS 1/2 AND ITS SECOND FORM IS A FILED DEFECT, NOT A MISSING
ROW** — see the `SAVE"x",A` item above: it ends the run on the reference and
continues here, the fix is one tail instruction, and it costs 3 of the 8 bytes
left in main page 1, so it is priced and reported rather than spent.
⚡ **D-KWTAPE4 — `CLOAD` AND `BLOAD` BOTH CLOSE, AND THE OLD `CLOAD` ROW PROVED
LESS THAN IT LOOKED. 144 of 163.**
🔴 **WITH ONE FILE ON THE TAPE, `CLOAD"ZQ"` AND A BARE `CLOAD` READ THE SAME
FILE AND PRINTED THE SAME `Found:ZQ`** — two forms, one reading, and **a CLOAD
that ignored its name argument passed both.** The fixture now carries a SECOND
program, `ZR`, and the two logical `.cas` images concatenate with no encoder
change (each is `sync+header+sync+data`, which is exactly how a multi-program tape
is laid out).
🟢 **`CLOAD` 2/2.** The named row now reaches the SECOND file and reads
**`Skip :ZQ`** — the machine's own witness that it PASSED OVER a non-matching
file, which only a name can make it do. The bare row reads `Found:ZQ`, the NEXT
file from a rewound tape.
🔴 **AND THE TAPE RIG IS NOW BOOT-PER-CASE**, the moment there was a second
row: the capture waits `cap_gap` (90 s) but the next case is typed after `step`
(5 s), and a tape read is still running then — the same shape that blanked
`open_c`'s reference screen, structural here rather than marginal. A fresh boot
also REWINDS the tape, which the bare form depends on.
🟢 **`BLOAD` 3/3.** `,R` LOADS AND EXECUTES: six bytes of Z80 are POKEd,
BSAVEd with `&HC800` as the entry, and the landmark cleared before the load —
`3E 2A` = `LD A,42`, `32 06 C8` = `LD (&HC806),A`, `C9` = `RET` — so a plain
BLOAD reads 0 and only `,R` reads **42**. `,S` loads into **VRAM**: `&HC800` =
51200 wraps into a 16 KB VRAM at **2048**, the start of SCREEN 0's pattern
generator table, and the cell is cleared with `VPOKE` first so the **77** can only
come from the file — read back with `VPEEK`, not `PEEK`.
⚠️ Both BLOAD rows and `bsave_b` sit LAST in the disk group, because they WRITE.
🔴 **AND THE BATTERY WENT RED ON A LOG NAME I DID NOT CHECK.** The battery's own
output was redirected into the repo scratchpad under the slice name — and a slice
of that name landed on 2026-09-13, so **a file of exactly that name is already
TRACKED**. All 129 gates were green and the run still failed — correctly — on the
pool-write guard: *never write a tracked file while a battery is running*. The
rule the tree already carries for heredocs (`test -e <path> && exit 1`) is the
same rule, and it applies to a REDIRECT just as much. This slice is D-KWTAPE**4**
because 3 was taken, and the battery log now goes to the SESSION scratchpad,
outside the repo, where it cannot collide with anything.
⚡ **D-KWROADMAP — `RUN`'s BARE FORM, TWO HONEST BARS, AND A COUNTED ANSWER TO
"WHAT IS LEFT". 144 of 163.**
🟢 **`RUN` 2/3 — the BARE form RESTARTS, and seeing that needed state that
SURVIVES a RUN.** Variables do not — clearing them is half of what the statement
IS — but VRAM does, and `VPEEK(4096)` reads **0 on BOTH machines at boot**
(measured; 4096 is outside every table SCREEN 0 uses, and 8192 reads 244 on both,
so that zero is a real read and not an unset one). Pass 1 finds 0, writes 99 and
RUNs; pass 2 finds 99 and prints. **A `RUN` that did nothing prints nothing at
all**, so the marker is the RESTART and not merely that the word parsed.
📏 **`DRAW` 1/10 AND `PLAY` 0/11 — AUTHORED FROM THE TREE'S OWN SPECS AND
DELIBERATELY UNSATISFIABLE TODAY.** `spec-basic-graphics-g6.md` §1 enumerates
DRAW's whole MSX1 surface and `spec-basic-audio-play.md` §2.2 lists PLAY's MML
subset from published sources; both become bars, the same way `PRINT USING` was
authored at five knowing the tree met two. ⚠️ `drawkw`/`drawkw_b` both pass `C15`,
which is the DEFAULT FOREGROUND, so neither says anything about `C` — they are
one form, not two. And the sweep has **no PLAY row at all**: `make
play-acceptance` is where PLAY is measured, and the bar now says how much a row
set would have to cover.
🎯 **AND THE NINETEEN THAT ARE LEFT ARE ALL BLOCKED ON SOMETHING NAMED.** Not
one of them is "nobody looked":
| blocked on | statements |
|---|---|
| **CODE, priced, Joost's call** | `SAVE` (the ASCII tail, +3 B), `LOCATE` (cursor switch), `SCREEN` (key click), `VARPTR` (`#n`), `INPUT$` (console form) |
| **THE INSTRUMENT, measured** | `KEY` (the key line's layout differs — LINLEN 37 vs 39), `PAD` (no host button), `STICK`/`STRIG` (openMSX drives a joystick from the HOST, which the emulated matrix cannot reach), `RUN`/`LOAD` (the loaded program REPLACES ours, so nothing can print afterwards), `AUTO` (the increment needs a multi-line direct interaction this harness has no shape for), `CONT` (two-phase delivery), `DELETE`/`RENUM` (measured shut — every form has the same observable) |
| **A BAR THE TREE IS GENUINELY FAR FROM** | `DRAW` 1/10, `PLAY` 0/11 |
| **NO HAPPY PATH REACHABLE HERE** | `CALL`, `MAX` (both score RESERVEDNESS only) |
🔴 **`RUN"file"` AND `LOAD` SHARE ONE BLOCKER AND IT IS THE FIXTURE.** Both
load a program that REPLACES the running one, so the row cannot print afterwards —
and `PROG.BAS` on the test disk POKEs a landmark rather than PRINTING one. A
fixture whose program printed a marker would close both at once; changing
`disk/test720.dsk` touches `ramfree`, `diskbasic` and every other suite that
mounts it, so it is a decision rather than a tweak.
⚡ **D-KWDRAW9 — `DRAW` GOES 1/10 TO 8/10, AND THE TWO IT DOES NOT GET ARE
REFUSED ON A MEASUREMENT.**
🟢 **Seven new forms, every one read back with `POINT`** the way the two rows
that were there already are — SCREEN 2's background is 4 and its drawn colour 15,
so those two numbers are what every reading is built out of:
`M50,50` → 15 at the midpoint (**move-absolute**); `M+20,+0` → 15 at (25,10),
where an ABSOLUTE reading would go to (20,0) and leave it 4 (**move-relative**);
`BM50,50R5` → **`4 15`** — nothing on the way, something at the new place, and
reading only the first would be satisfied by a DRAW that did nothing at all
(**blank-prefix**); `NR5D3` → **`15 15`**, the `D3` starting from (10,10) again
because the cursor went back (**no-update-prefix**); `C7R5` → **7**
(**colour** — and the two old rows pass `C15`, which IS the default foreground, so
they said nothing about `C`); `S8R2` → 15 at (13,10), because `S` is in QUARTERS
and the default is 4, so the step doubles (**scale**); `A1R5` → **`15 4`**, which
says it turned UP rather than only that it turned (**angle**).
⛔ **`X<var>;` AND `=<var>;` HAVE NO ROW, AND THAT IS A MEASUREMENT RATHER THAN AN
OMISSION.** Written the way `spec-basic-graphics-g6.md` §1 names them —
`DRAW"XA$;"` with `A$="R5"`, and `DRAW"R=A;"` with `A=5` — **BOTH MACHINES DREW
NOTHING AND NEITHER RAISED**: the reading was `4` on each side, the background.
🔴 **A row agreeing on an ABSENCE both sides produce says nothing about either of
them**, so the rows are gone rather than banked. The spec's own error table has
`=var`/`X var` WITHOUT the `;` raising ERR 5, so the `;` form is reaching
something, and the MSX1 `X` command is documented elsewhere as taking a string
DESCRIPTOR ADDRESS rather than a name. **Two guesses is where guessing stops:**
that needs an isolated probe with a control, not a third row shape.
⚡ **D-KWDRAWX — AND THE ANSWER WAS THAT THEY WERE NEVER MISSING. `DRAW` CLOSES
AT 10/10. 145 of 163.**
🔴 **THE PARAGRAPH ABOVE IS REFUTED, AND IT IS KEPT RATHER THAN DELETED.** The
isolated probe it asked for (`scratchpad/drawsubst_probe.py`, eight cases with a
control) says every one of those spellings WORKS on both machines: `XA$;` draws,
`XAB$;` draws with a two-letter name, `R=L;` draws, `C=A;R5` reads **7** — the
substitution supplying a COLOUR — and both spellings WITHOUT the `;` raise ERR 5
exactly as `spec-basic-graphics-g6.md` §147 says. The control drew 15, so the
apparatus was sound.
🎯 **THE CAUSE IS A STATE LEAK BETWEEN BATCHED CASES, AND IT IS FAITHFUL MSX:
`DRAW`'s ANGLE AND SCALE PERSIST ACROSS PROGRAMS.** `drawkw_i` sets `A1`, and
every later row in that batch then drew ROTATED — measured directly
(`scratchpad/drawleak_probe.py`: `A1R5`, then a plain `R5` reads **4**, then the
same `R5` behind an `A0S4` reads **15**). The two rows were correct; their
NEIGHBOUR was the defect, and running them alone would have said so — which is
exactly what the isolated probe did.
🌱 **EVERY DRAW ROW NOW OPENS WITH `A0S4`** (and `C15` unless it is the colour
row). 🔴 **AND THAT MEANS `drawkw`/`drawkw_b` WERE ONLY EVER RIGHT BECAUSE
NOTHING BEFORE THEM HAD SET AN ANGLE** — they carried no reset and never needed
one until this slice put a row that sets `A1` in front of them.
📏 **A tenth entry for the row-failure list, and it is a new KIND:** a row can
be poisoned by a neighbour's leftover MACHINE STATE, not just by delivery timing
or a mutated fixture. The two earlier batch hazards were a WRITER upstream of a
reader and a case slower than the batch `step`; this one is neither, and none of
the three is visible from the row itself.
🏗️ **JOOST RULED, 2026-09-15 — FIVE DECISIONS, AND FOUR OF THEM CHANGE THE
NEXT SLICES. Do not re-ask.**
1. 🟢 **`SAVE"x",A`: SPEND THE 3 B NOW.** The ASCII save must END the run the
   way the reference does. Main page 1 goes 8 B → 5 B. ✅ **DONE, and the figure
   held exactly: 8 B → 5 B, low region 0 unchanged.** `SAVE` 2/2, TIER 1.
2. 🚧 **The four code forms — LOCATE's cursor switch, SCREEN's key click,
   `VARPTR(#n)`, `INPUT$`'s console form — CARVE FIRST, THEN IMPLEMENT ALL FOUR.**
   A carve slice is now the PREREQUISITE; they land together once there is room,
   not piecemeal into 5 B.
   🟢 **THE CARVE IS DELIVERED, AND BY RULING 5's OWN LEVER.** Moving the four
   FAT-light disk verbs into `disk.rom` (D-DISKVERB..4, 2026-09-15) took main
   page 1 from **3 B to 153 B** and the low region from **0 B to 36 B** — "disk
   code belongs in the disk ROM", pulled first, exactly as ruling 5 said. The
   first customer was `FIELD`/`LSET`/`RSET`'s diskless gate (D-FLDGATE, 20 B).
   ✅ **`LOCATE`'s CURSOR SWITCH IS THE FOURTH, SHIPPED 2026-09-16 (D-LOCCSR),
   10 B** — filed as a DECLINED deviation (O-3) rather than as missing code, and
   the decline rested on a false premise. `LOCATE` is **4/4, TIER 1**; STATEMENT
   **148 → 149**. 🎯 **Only `VARPTR(#n)` remains of ruling 2's four.**
   ✅ **`SCREEN`'s KEY CLICK IS THE THIRD, SHIPPED 2026-09-16 (D-SCRCLICK),
   9 B** — and it was filed as unmeasurable rather than as code: see the struck
   "no cell any row here can read" above. `SCREEN` is **3/3, TIER 1**, and the
   STATEMENT count moved **147 → 148**. Two of ruling 2's four remain:
   `LOCATE`'s cursor switch and `VARPTR(#n)`.
   ✅ **`INPUT$`'s CONSOLE FORM IS THE SECOND, SHIPPED 2026-09-16 (D-INPDCON),
   21 B.** `A$=INPUT$(1)` answered `Syntax error` where both references read a
   key — **the last MISSING keyword in the whole sweep, so `kwsweep` now reads
   `DIVERGENT=2 SUPPORTED=358` with no MISSING line at all.** It reuses the file
   form's loop rather than copying it: `str_inputd_read` already consumes
   `INDLR_N` bytes into `STRSCR` through the `ARL_GETBYTE` vector, so the console
   form is a FOURTH SOURCE (7 B of `CHGET`) plus the branch that points the
   vector at it. No channel, so no `fch_check` and no `fch_select`.
   🎯 **AND THE CHANNEL FORM HAD NO ROW OF ITS OWN**, which is why `INPUT$` read
   `0/2` while half of it worked: `INPUT$(n,#f)` was exercised only INSIDE the
   `printhash` row, as the INSTRUMENT that reads `PRINT #`'s bytes back, so it
   scored `PRINT_#`. **A form measured only as another verb's instrument is a
   form with no row** — the same class as `COPY` and `LFILES` having no row in
   the suite that appears to gate them. It has one now; `INPUT$` is **2/2**.
   🔴 **IT IS STILL TIER 0, AND THE REASON IS AN INSTRUMENT LIMIT WORTH ITS OWN
   ITEM: `INPUT$` CANNOT BE KNIFE-CUT.** `tools/tier_table.py` reads *"not
   knife-proven CONNECTED"*, and that is structural rather than a blind row:
   `kwknife.py`'s `plant_fn` cuts a `cp <TOKEN>` / conditional-jump chain, and
   **`INPUT$` HAS NO TOKEN** — MSX tokenises `INPUT` and `$` separately, which
   `tools/kwforms.py` says out loud. It is reached by a SUFFIX test
   (`str_eval_maybe_inputd`: `ld a,(hl) / cp '$' / jr z,str_inputd`), a shape the
   knife has no cut for. Same class as `MAX`, which "is not dispatched this way
   at all" — NOT the same as a row that fails to notice a cut.
   ⚠️ **A FOURTH CUT SHAPE IS THE FIX AND IT IS NOT A FREEBIE**: cutting on
   `cp '$'` by operand is ambiguous (a `$` compare is everywhere in a BASIC that
   has string suffixes), so it would have to anchor on the SYMBOL
   `str_eval_maybe_inputd` and patch the `cp` inside it. A wrong cut shape
   produces FALSE `CONNECTED` readings, which is worse than none — so it is filed
   here rather than improvised alongside the feature it would score.
3. 💾 **The disk fixture: ADD A SECOND `.BAS`, LEAVE `PROG.BAS` ALONE.** Nothing
   existing changes its bytes, so `ramfree`, `diskbasic` and every other suite
   that mounts `disk/test720.dsk` keeps reading what it read. The new file PRINTs
   a marker, which is what `RUN"<file>"` and `LOAD` need to be observable at all.
4. 🔧 **The unreachable forms: BUILD A RIG THAT CAN REACH THEM** — not an
   exemption. `KEY`'s display forms, `PAD`'s switch and `STICK`/`STRIG`'s joystick
   halves stay counting against us until a rig drives openMSX's HOST-side joystick
   and reads the key line where it actually sits.
5. 📍 **PLACEMENT (Joost, same message): DISK CODE BELONGS IN THE DISK ROM as
   much as possible, and TAPE CODE IS A GOOD CANDIDATE FOR THE SUB ROM.** That is
   the lever the carve should pull first: `make basic-reloc` on 2026-09-15 reads
   **8 B free in main page 1 and 0 in the low region**, against **~8820 B free in
   `disk.rom` across 32 runs, largest usable hole 3182 B**, and 505 B in sub
   page 0. 🔴 **`ascii_save` IS ITSELF DISK CODE SITTING IN THE MAIN IMAGE** —
   the `SAVE",A"` tail this arc is about — so it is a migration candidate, not
   only a +3 B edit. Instruction-level shaving is the LAST resort, not the first.
⚡ **D-KWSAVEEND — THE FIRST OF THE FIVE RULINGS, SHIPPED. `SAVE` 2/2. 146 of
163.**
🟢 **`ascii_save` now ends `call disk_write_end / jp end_line_end`** — the same
tail `ex_list` has, which is the whole point: this path DRIVES the LIST walk, and
`LIST` inside a program ends the run on both machines, so `ex_list` was right and
this tail simply did not inherit it.
⚠️ **`call` + `jp`, not the old `jp`:** `disk_write_end` ends in a `ret` whose own
comment says *"back to the prompt"*, so the tail jump unwound one frame further
than a handler body does. Calling it leaves the stack exactly where `ex_list` has
it when IT reaches `end_line_end`.
💰 **+3 B EXACTLY AS PRICED.** `make basic-reloc` from a clean tree,
2026-09-15: **main page 1 free 8 B → 5 B**, low region **0**, unchanged. All four
probe cases now read the SAME on both machines — the tokenised save still
continues (`< 72 >`), and after an ASCII one neither a readback nor a bare `PRINT`
nor a `FILES` is reached.
🎯 **AND THE ROW'S PLACEMENT IS THE ROW.** `save_b` is the LAST disk row: an
ASCII save ends the run MID-LINE, and a case that ends mid-line leaves the machine
somewhere the NEXT case cannot be typed into — an earlier cut of exactly this row
read cleanly on both sides and blanked `namekw` and `open_c` behind it. At the end
of the group there is no successor to poison.
🔴 **THE KNIFE PIN REFUSED, CORRECTLY, AND WAS RE-STAMPED BY ONE RUN.** A ROM
change moves the fingerprint, and `tier_table` will not render against a pin
measured on a machine that no longer exists. `SAVE`'s own cut was re-measured on
the new ROM (LOAD-BEARING); **the other rows' verdicts still date from the
pre-fix ROM**, and that is defensible here only because a 3-byte tail shifts
addresses without changing whether any row NOTICED its cut. A change that moved
code between regions would need the full `--all` / `--allfn` re-measure.
⚡ **D-KWRUNFILE — RULING 3 SHIPPED. `RUN` CLOSES AT 3/3. 147 of 163.**
🟢 **`PROG3.BAS` is `10 PRINT"[3h]"`, appended LAST to `disk/test720.dsk`.**
`RUN"<file>"` and `LOAD"<f>",R` REPLACE the running program, so the row that
typed them has nothing left to print with — **the only witness is output from the
LOADED program, and `PROG.BAS`/`PROG2.BAS` both only POKE.** That was the whole
blocker: not a missing behaviour, a fixture that says nothing out loud.
🎯 **`add_file` allocates clusters sequentially, so nothing before it moves** —
`TEST.BIN` keeps cluster 2, its mid-file chain hop and its chain EOF, and every
FAT row that pins them still reads what it read. That is what "leave `PROG.BAS`
alone" buys.
🟢 **`RUN` 3/3 → TIER 1** (`[3h]` from the loaded program), and `LOAD` gets a
bar of 2 with the `,R` form covered. ⛔ **`LOAD`'s PLAIN form cannot get a row
with this instrument** — it replaces the program and runs nothing, so its reading
would be an ABSENCE both machines produce. `LOAD` stays 1/2 on purpose.
🔴 **AND THE DISK GROUP'S `step` WENT 5.0 → 8.0, BECAUSE `open_c` BLANKED FOR
THE SECOND TIME.** A case SLOWER THAN `step` has its SUCCESSOR typed into a
still-running program, and on the CF-3300 a row with two open/write/close cycles
sits right at the 5 s edge: `open_c` read cleanly alone and came back with a BLANK
REFERENCE SCREEN as the group grew — once when `bsave_b` joined it, and again when
these two rows did. **Shrinking the row fixed it the first time and did not the
second: the fix belongs to the GROUP, not to whichever row happens to be at the
edge.**
🔴 **AND THE FIXTURE GATE'S OWN SELFTEST WENT RED WHILE THE GATE WAS RIGHT.**
`check_fixture_integrity.py`'s S4 asserted a LITERAL **6** — five generated files
plus the one it plants — so the moment the generator grew a sixth, the selftest
failed and the check itself still passed. **A count that must be edited every time
the fixture legitimately changes is a pin masquerading as a check**; S4 now derives
it (one MORE than a fresh generation), which is the property it actually means.
🔴 **AND THE BATTERY CAUGHT TWO MORE FIXTURE-COUPLED PINS — WHICH IS THE
GATES WORKING, NOT THE FIXTURE BEING WRONG.** `namspc-acceptance`'s POSITIVE
CONTROL `f.filesbare` pinned `5 entries + OK` (its own comment says *"change that
image and this goes red on a REFERENCE, which is the correct loud failure"* — and
it did, refusing to score all 138 rows rather than reporting a regression), and
`diskbasic-acceptance` pinned the five-name directory in two probes.
🎯 **THE CF-3300's WRAP WAS RE-MEASURED, NOT PREDICTED.** `disk_probe_files.py`
carries the reference listing at WIDTH 29 as a FROZEN CONSTANT, and its own
comment records that the second such constant *"froze from the polluted fixture"*
once already. Its `run()` does not answer the CF-3300's date prompt, so the
constant cannot be refreshed through the probe itself —
`scratchpad/cf3300_files_probe.py` does it with the reset the kwsweep already
uses for that machine. The real machine now reads
`PROG2   .BAS PROG3   .BAS` on the third line, byte-identical to what this tree
produces.
🔎 **D-REGIONSCOUT — THE CARVE'S FIRST MEASUREMENT, AND IT RUNS INTO A
DOCUMENTED CHARTER PROPERTY.** `scratchpad/regionscout.py` maps every main-image
symbol back to its source file and splits the bytes by region. It cross-checks
exactly against `basic-reloc` on 2026-09-15 (page 1: 12443 + 3936 = 16379,
leaving the 5 B free it reported that day; low region 6126 B, its string-engine
figure).
| file | kind | page 1 |
|---|---|---|
| `files.asm` | disk | 1600 |
| `cload.asm` | tape | 864 |
| `field.asm` | disk | 600 |
| `save.asm` | disk+tape | 533 |
| `fat.asm` | disk | 124 |
| `format.asm` | disk | 115 |
| `bload.asm` | disk | 100 |
| **disk-only** | | **2539** |
| **tape-only** | | **864** |
🎯 **3936 B OF DISK/TAPE CODE SAT IN MAIN PAGE 1 ON 2026-09-15, WHERE 5 B WERE
FREE.** The lever is real and it is enormous.
🔴 **THE PARAGRAPH BELOW IS CORRECTED (2026-09-19): THE SPIKE IS PROVEN, THE
DECISION IT IS USED TO DEFEND IS NOT.** "No standard open-by-name entry exists" is
measured and still true. "Therefore the BASIC-side FAT is the NECESSARY PRICE"
only follows if the universal sector interface is a REQUIREMENT, and Joost retired
that on 2026-09-15 (`spec-diskbasic-hook-rearchitecture.md` §Phase 4): a foreign
cartridge brings its own Disk BASIC, so DSKIO-only interop describes hardware that
does not exist. The analysis is kept; its conclusion is inverted. See
`spec-diskcode-eviction.md` §6.7.
🔴 ~~**AND THE DISK HALF OF THE PLACEMENT RULE CONTRADICTS A MEASURED,
ORACLE-PROVEN DECISION THIS TREE ALREADY MADE.**~~ `basic/fat.asm:11` states it and
`docs/TODO-done.md` records the spike behind it: a disk ROM's **only**
interchangeable interface is SECTORS — there is no standard "open file by name"
entry to delegate to, because a disk ROM's filename logic is locked inside its own
Disk BASIC. So *"the basic-side FAT is the NECESSARY PRICE of the universal sector
interface, not avoidable duplication"*, and the property is PROVEN, not asserted:
every disk verb passes under zerobas-BASIC with **our own `disk.rom` AND with the
foreign National CF-3300 disk ROM in slot 3-1**. Moving `files.asm`/`fat.asm` into
our disk ROM would spend that property. (True delegation — hosting the disk ROM's
own Disk BASIC extension — is already filed as the charter-raising Phase-2 item.)
🔴 **AND THE SUB ROM, WHICH IS WHERE THIS TREE ACTUALLY EVICTS, IS FULL.**
`fatprim_tenant`, `dirverb_tenant`, `save_tenant` and `bload_tenant` all live
there already — and `make basic-reloc` on 2026-09-15 reads **505 B free in sub
page 0 and 50 B in sub page 1**. Even `cload.asm`'s 864 B does not fit, so the
TAPE half of the rule needs its own carve first.
📍 **SO NEITHER HALF IS EXECUTABLE AT TODAY'S FREE SPACE**, and the disk half
costs a proven property on top. Put to Joost rather than resolved here.
🏗️ **JOOST RULED AGAIN, 2026-09-15, AFTER THE PRIOR DECISION WAS PUT IN FRONT
OF HIM: RE-DECIDE AFTER THE SEAM IS MEASURED, AND WRITE THE SPEC, NO CODE.**
🔴 **I ASKED A QUESTION THAT WAS ALREADY DECIDED.**
`disk/docs/spec-diskbasic-relocation.md` is headed *"Status: DIRECTION DECIDED
(user, 2026-07-09)"* and its decision is the ROLE-SPLIT — keep the loader path and
the FAT it needs in `basic.rom` for interop, move the disk-MANAGEMENT verbs to
`disk.rom` via the `$4004` STATEMENT expansion — with the alternative *"move all
disk-BASIC incl. `fat.asm`, drop the interop"* **considered and REJECTED**. My
first question framed the choice without that in view and got the rejected option
back. RE-VERIFY A FILED DECISION BEFORE ASKING ABOUT ITS SUBJECT, not only before
building on it.
📏 **THE SEAM IS MEASURED AND IT REFUTES THE ESTIMATE THE PARENT SPEC RESTS ON.**
Full write-up: [`disk/docs/spec-diskbasic-relocation-seam.md`](disk/docs/spec-diskbasic-relocation-seam.md).
* `files.asm → fat.asm` is **3** edges and `field.asm → fat.asm` **3**, not the
  *"~15"* and *"~13"* the parent spec estimates — **6, not 28.** The
  primitive/sector layer was evicted to the sub-ROM tenants after that estimate
  was written, and what was left of `basic/fat.asm` in main page 1 on 2026-09-15
  was **124 B**.
  The *"~28 cross-slot CALLSLTs"* it treats as the central obstacle **does not
  exist**, and options 1 and 2 die with it: both are capped at 124 B.
* **The seam that DOES exist is the INTERPRETER.** `files.asm` has **99**
  outbound edges to the rest of BASIC (53 to `interp.asm`) and **26** inbound;
  `field.asm` 41 and 4. Plus **19 `dw` dispatches** from `stmt_table` that the
  edge scan cannot see and that `$4004` would replace.
* **Option 4 (move `files`+`field`+`format`) was worth 2315 B** of page-1 relief
  on 2026-09-15, for 140 outbound calls turned cross-slot and 30 inbound entry
  points.
* **Option 3 is UNPRICED, and that is the next measurement.** A branch-reachability
  closure reaches 16 labels / 194 B against `files.asm`'s 1600, because control
  reaches most of these bodies by **FALLTHROUGH** — the blind spot `dupspan`
  already has. `seamscout.py` keeps the closure WITH that warning, because the
  negative result is the finding.
📌 **AND THE INTEROP IS UNGATED**, which cuts both ways: `expansion-protocol.md`
lists the host-direction test as an acknowledged *"Gap (small)"*, so nothing would
go red if it broke — the property is documented and spike-proven, not asserted by
any suite.
💰 **OPTION 3 IS PRICED: 256 B, MEASURED 2026-09-15.**
[`scratchpad/verbpartition.py`](scratchpad/verbpartition.py) sorts `files.asm`'s
symbols by address, cuts at each VERB ENTRY and attributes each span to the verb
that opens it — **and it sums to 1600 B, the same figure `regionscout.py` and
`basic-reloc` give.**
| group | verbs | bytes |
|---|---|---|
| **FAT-light** | `COPY`, `FILES`/`LFILES`, `KILL`, `NAME` | **256** |
| channel | `OPEN`, `LINE INPUT`/`INPUT#`, `CLOSE`, `MAX FILES`, `MERGE` | 975 |
| infra | `chan_gate`, `disk_error`, the `fch_*` channel manager | 369 |
🎯 **AND THE SHAPE OF `files.asm` IS THE FINDING: the bulk is the CHANNEL
MACHINERY (975 B), not the directory verbs (256 B)** — and the channel machinery
is exactly the entangled part, with `init_filechan`, `fch_select`, `fch_check` and
`fch_ctx_addr` called from `expr.asm`, `str-engine.asm`, `input.asm`, `strvar.asm`
and `print.asm`. The parent spec hoped for ~3 KB from a "minimal move"; the
minimal move is 256 B, and that difference is the whole value of measuring.
📏 **THE LADDER, CHEAPEST COUPLING FIRST: 3 (256 B) → 3b (1231 B) → 4
(2315 B)** — each step buys bytes by taking on more INTERPRETER entanglement, not
more FAT. Main page 1 had **5 B** free on 2026-09-15, so even option 3 is fifty
times today's entire headroom.
⚠️ **What the partition cannot say** is recorded with it: a span belongs to the
verb that opens it only if no other verb jumps in, so the labels called from
OUTSIDE `files`/`field` are listed separately — **15 labels, 164 B** in
`files.asm` and **3 labels, 39 B** in `field.asm`. Those do not travel with a
verb.

🟢 **JOOST APPROVED OPTION 3 ON 2026-09-15, VERBATIM: *"D-VERBPART — option 3
is priced -> approved"*.** `COPY`, `FILES`/`LFILES`, `KILL`, `NAME` move to
`disk.rom`; **256 B** of main page 1, which had **5 B** free on 2026-09-15.
⚠️ **THE APPROVAL IS FOR RUNG 3 AND NOTHING ELSE** — 3b (1231 B), option 4
(2315 B), `field.asm` and the 975 B channel machinery stay parked, and widening
the move is a NEW decision rather than an implementation detail. §5's interop
warning is attached to option 4, so `basic/fat.asm:11` and `expansion-protocol.md`
§251 are **not** to be touched on this rung: the BASIC-side FAT stays.
⚠️ **THAT SCOPING WAS CORRECT FOR RUNG 3 AND ITS REASON HAS SINCE BEEN WITHDRAWN
(2026-09-19).** The interop warning it defers to was retired by Joost on
2026-09-15; `basic/fat.asm` and the relocation specs were corrected on 2026-09-19.
The rung-3 scope is unaffected — nothing widened — but a later rung must NOT cite
this line as evidence that the BASIC-side FAT has a live justification.
🔴 **AND THE FIRST STEP IS NOT A MOVE.** Measured 2026-09-15:
`disk/init.asm:18` is `dw 0` — the `"AB"` header's `$4004` STATEMENT vector is a
STUB — and the CONSUMER slot-walk does not exist at all; an unknown statement falls
to `stmt_error`. That walk is **INTERPRETER code in `basic/interp.asm`**, it is the
step that can go wrong quietly, and §8's "one slice per step" puts it on its own.
📏 **Siting is not the constraint**: `disk.rom` has a **3182 B hole at `$6937`**
bounded by the pin at `$75A5` (`tools/check_disk_walls.py`, 2026-09-15), against
256 B of verb bodies.
🔪 **And the slice after the move is a FULL `kwknife.py --all` AND `--allfn`
re-measure** — §8 is explicit that a relocation moves code between REGIONS, so the
one-run re-stamp that sufficed for D-KWSAVEEND's 3-byte tail does not.
🎯 **This is ruling 2's prerequisite carve**: the four code forms (LOCATE cursor
switch, SCREEN key click, `VARPTR(#n)`, `INPUT$` console) land together after it.

⚡ **D-NODISKDEN (2026-09-15) — JOOST'S DENOMINATOR, AND THE ANSWER IS A CLEAN
NEGATIVE THAT IS WORTH AS MUCH AS A DEFECT WOULD HAVE BEEN.**
🎯 **THE RULING** (Joost, 2026-09-15): *"every hook claimed on 3300 we don't
presumably is a sign of a defect or divergence."* **TWO DENOMINATORS THAT SHOULD
AGREE**, and where they do not is where the next `LFILES` hides:
| denominator | count |
|---|---|
| hook cells the CF-3300 claims | **27** |
| equates `basic/sysvars.inc` names | 14 |
| …of those, also claimed by the CF-3300 | 13 |
| **claimed cells with NO name here** | **14** |
| …now identified (`H_LSET` `H_RSET` `H_FIELD`) | 3 |
| **still unidentified** | **11** |
| words `basic_probe_nodisk.py` asked about (before) | 17 |
| Disk-BASIC surface in `basic/kwtable.inc` | ~37 |
🟢 **EIGHT OF THE UNASKED VERBS ARE NOW MEASURED ON THREE SIDES AND ALL EIGHT
AGREE WITH THE DISKLESS ORACLE** — `CLOSE`, `CLOSE#1`, `LOC`, `MAXFILES`, `CVD`,
`INPUT#`, `LINE INPUT#`, `PRINT#`. Rows added for every one of them, because a
verb that AGREES still earns its row: that is the whole `LFILES` lesson, which
ran wrong for as long as it existed while `FILES` beside it was green. The set is
21 rows → **29**.
⚠️ **SO JOOST'S "PRESUMABLY" IS TEMPERED TWICE OVER, AND BOTH TEMPERINGS ARE
MEASUREMENTS.** `GET`/`PUT` are hooked on the reference and diverge NOT AT ALL;
and of the dozen unasked verbs, the eight that can be asked all agree. **A claimed
hook marks a CANDIDATE, not a defect** — which is exactly why the divergence is
measured before a slot is ever hunted, and why that order kept the last hunt to
two verbs instead of four.
🔴 **SIX VERBS CANNOT BE ASKED IN THIS SHAPE AT ALL, AND THE PROBE SAYS SO RATHER
THAN LEAVING A GAP.** `SAVE`/`BLOAD`/`BSAVE`: with no disk ROM a bare `SAVE"X"` is
a **CASSETTE** save and waits on the tape motor. `LOAD`/`RUN"<file>"`/`MERGE`:
they replace or merge into the running program and destroy the probe asking the
question. Both classes need the tape rig or boot-per-case.
🔴 **AND THE FIRST CUT OF THE SCOUT REPORTED NINE DIVERGENCES THAT WERE ONE
POISONED BATCH.** `SAVE` blocked on the VG-8020, every case after it read
`? color auto goto list run` — no fence — and the flag logic compared a FAILED
CAPTURE against a real one. An empty capture on one side is not a verdict; the
scout now prints **NO READING — apparatus, not a verdict** instead of inventing
one.
🔴 **THREE OF THE NEW ROWS WERE VACUOUS ON THEIR FIRST CUT, IN A WAY THAT LOOKED
LIKE COVERAGE.** `run()` appends `;` to the statement — harmless after a `PRINT`,
a **Syntax error** after a bare verb — so `CLOSE;`, `CLOSE#1;` and `MAXFILES=2;`
read ERR 2 on all three sides and scored as agreement **on an error the probe
itself caused**. The existing rows only escape that because their gate fires
BEFORE the syntax check. Fixed with a `:PRINT"K"` tail so the verb decides the
reading — and `K` rather than `""`, because an empty cell is an unnamed outcome
and reads exactly like a capture failure.

🔴 **D-DISKDISP (2026-09-15) — AND THE VERY FIRST STEP OF THE APPROVED PLAN IS
THE WRONG STEP. THE `$4004` SLOT-WALK IS NOT HOW THESE FIVE VERBS ARE REACHED.**
🎯 **TWO OF THIS TREE'S OWN DOCUMENTS DISAGREE ON THE LOAD-BEARING RULE, AND THE
SPEC CARRIED THE WRONG HALF.** `spec-diskbasic-relocation.md`'s Mechanism section
(restated verbatim as the seam spec's §7) says the dispatch is **`$4004` STATEMENT
expansion**. `disk/docs/expansion-protocol.md` §1's own header table says `+0004
STATEMENT` is the **`CALL`-statement expansion handler** — the route for
`CALL <name>` / `_<name>`, not for a tokenised keyword like `FILES`.
🔬 **MEASURED, WITH CONTROLS FIRST**
([`scratchpad/tokscout2.py`](scratchpad/tokscout2.py) — every word run as a bare
statement under `ON ERROR`, on three machines):
| word | VG-8020 (diskless) | zerobas NODISK | zerobas DISK |
|---|---|---|---|
| `FROG`, `ZQ` (controls) | **ERR 2** | ERR 2 | ERR 2 |
| `BEEP`, `CLS` (controls) | ran | ran | ran |
| `FILES` `KILL` `NAME` `COPY` | **ERR 5** | ERR 5 | 70 / 24 / 24 / 24 |
| `FIELD` | ERR 5 | ERR 24 | ERR 24 |
| `LFILES` | ERR 5 | **ran** | ERR 70 |
| `MERGE` | ERR 24 | ERR 24 | ERR 24 |
🎯 **ERR 5, NOT ERR 2, IS THE WHOLE READING.** A word BASIC does not know answers
**Syntax error** — that is what the two controls establish, and without them ERR 5
would mean nothing. The disk verbs answer **Illegal function call** on a machine
with NO DISK ROM AT ALL, so on a real MSX the **TOKEN AND ITS DISPATCH LIVE IN THE
MAIN BASIC ROM** and the disk ROM supplies only the implementation behind them.
🔴 **SO THE TOKENS AND THEIR `stmt_table` ENTRIES CANNOT MOVE — ONLY THE
BODIES CAN.** `FILES` must stay a keyword on the diskless target too, or a
`Syntax error` appears where an `Illegal function call` belongs and
`nodisk-acceptance` is right to go red. What moves is the HANDLER, reached by a
cross-slot thunk (`RST 30h` + slot + address + `RET`, the idiom
`expansion-protocol.md` §2 records from the hooks).
📏 **WHICH RE-PRICES THE RUNG: ~5 B of thunk per verb STAYS BEHIND**, so the
relief is nearer **~226 B than 256 B**. Not yet measured exactly — the slot byte
is discovered at boot, not a constant, so the thunk may be longer.
🟢 **THE GOOD NEWS IS THAT THE RISKIEST STEP IS DELETED.** "Write a consumer
slot-walk in `basic/interp.asm`" was the one interpreter change in the plan and
the one that could go wrong quietly; it is not needed for this rung at all.
❌ **I THEN CLAIMED OPTION 3 SPENDS THE FOREIGN-DISK-ROM INTEROP. THAT WAS
WRONG, AND JOOST ASKED THE QUESTION THAT KILLED IT: *"aren't those supposed to
work via hooks?"*** They are, and **this tree already does it**:
`basic/sysvars.inc:3139-3144` defines `H_NAME $FDF9`, `H_KILL $FDFE`,
`H_FILE $FE7B` and `H_COPY $FE08` — the STANDARD MSX hook slots, for exactly the
verbs this rung moves — and `disk/kernel.asm:2258-2263` claims all four.
🎯 **A HOOK IS CLAIMED BY WHICHEVER DISK ROM IS PRESENT, so interop is preserved
BY CONSTRUCTION rather than spent**: a foreign disk ROM patches the same five
bytes with its own `F7 <slot> <lo> <hi> C9`, and `FILES` reaches ITS body. That is
the entire point of the hook idiom, and my worry only looked real because I was
still reasoning from the spec's `$4004` route.
🟢 **AND THE ERR 5 THE SCOUT MEASURED IS THIS MECHANISM'S OWN SIGNATURE.**
`chan_gate` (`basic/files.asm:84`) calls THROUGH the hook cell; unclaimed it is a
bare `ret`, and the gate then raises **Illegal function call** — which is exactly
what the diskless VG-8020 answers for all four verbs, and what
`nodisk-acceptance`'s `v.dskf` row already pins for `DSKF`.
💰 **WHICH MAKES THE RUNG SMALLER AND SAFER THAN THE SPEC DESCRIBED.** Today the
hook is only a PRESENCE TEST — `disk/kernel.asm` claims it with `hk_present` and
the body then runs in main page 1. The relocation is: **point the hook at the real
body in `disk.rom` and delete the main-side body.** No `$4004`, no consumer
slot-walk, no new interpreter code, and the call site in `files.asm` already loads
the hook address and goes through `chan_gate`.
⚠️ **What still needs measuring before a byte moves**: what stays behind at each
call site (the `ld hl,H_*` + `call chan_gate` pair is already there, so the
question is what ELSE the bodies share with code that is not moving), and whether
`dirverb_op`'s sub-ROM tenant route changes. The ~226 B figure above is
provisional until that is counted.

🟢 **BOTH SPECS' MECHANISM SECTIONS ARE CORRECTED (2026-09-15).** They said
`$4004` STATEMENT expansion and that a consumer slot-walk had to be written in
`basic/interp.asm`; both are struck, with the original text kept beside the
correction for the paper trail. The real route is the **standard MSX hook table**,
which this tree already uses and already claims — so the move needs **no consumer
slot-walk and no new interpreter code at all**, which deletes the riskiest step
the plan had.
🔴 **BUT THE FIRST LOOK AT WHAT *STAYS* IS DISCOURAGING, AND IT HAS TO BE COUNTED
BEFORE ANY BYTE MOVES.** `scratchpad/verbpartition.py` on the 2026-09-15 build
puts the FAT-light group at **258 B** (`ex_copy` 24, `ex_files` 95, `ex_kill` 44,
`ex_name` 95 — up 2 B from 256 because of D-NODISKGAP's `LFILES` gate). Reading
`ex_kill`, the smallest of them, the 44 B breaks down as: the hook gate (8 B,
which STAYS and becomes the call-through), a cursor step, `call fname_fcb` —
**which evaluates a string EXPRESSION and therefore must run main-side** — then
`diskslot_test`, then `ld a,DISKOP_SEL_KILL` / `call dirverb_op`.
🎯 **AND `dirverb_op` IS THE PART THAT MATTERS: THE REAL WORK IS ALREADY A SUB-ROM
TENANT** (`SUBROM_IDX_DIRVERB`, `sub/dirverb.asm`). So the main-side 258 B is
largely ARGUMENT EVALUATION AND ERROR DISPATCH, not the verb's work — and
argument evaluation cannot leave, because it runs the interpreter's own
expression evaluator on the statement cursor.
⚠️ **So `256 B` is an upper bound on the SPAN, not on what can actually depart**,
and the realisable relief may be materially less. ⛔ **DO NOT MOVE ANYTHING UNTIL
EACH OF THE FOUR VERBS IS CLASSIFIED BYTE BY BYTE** into (i) must stay — touches
the statement cursor, evaluates an expression, or raises a BASIC error; (ii) can
move; (iii) already elsewhere (the sub-ROM tenant). If (ii) is small, that is a
finding about the rung and Joost should hear it before the work, not after — the
same way the seam measurement refuted the parent spec's ~3 KB.

🔴 **D-VERBCLASS (2026-09-15) — THE CLASSIFICATION IS DONE AND IT REFUTES THE
RUNG'S PRICE. 258 B OF SPAN IS 36 B OF DEPARTURE.**
[`scratchpad/verbclass.py`](scratchpad/verbclass.py) splits every label inside the
four verb spans by what its own source text DOES (comments stripped, so a label
that merely NAMES a helper is not misfiled), with sizes from
`build/basic-reloc.sym` exactly as `verbpartition.py` takes them — the buckets
reconcile to 258 B:
| bucket | bytes | what it is |
|---|---:|---|
| **STAY** | **155** | reads the PROGRAM TEXT — statement cursor, expression evaluator, a syntax error raised while parsing, and the gate itself |
| **TENANT** | **67** | pure marshalling into `dirverb_op`/`subrom_call`; the work is ALREADY in the sub ROM |
| **MOVE** | **36** | no interpreter contact — the only bytes that can simply leave |
| | **258** | |
🎯 **SO THE RUNG IS WORTH ~36 B, OR AT MOST ~103 B** if the marshalling goes too —
and that second number is not free, because moving the marshalling means
`disk.rom` calling back into the **sub ROM**: a cross-slot hop from one expansion
ROM into another, which needs proving reachable and costs bytes at both ends.
**Against the 256 B the approval was given for.**
📉 **AND IT IS THE THIRD TIME MEASUREMENT HAS CUT THIS ESTIMATE**: the parent spec
hoped ~3 KB, the seam measurement said 256 B, the classification says 36–103 B.
🔴 **MY FIRST CUT OF THE CLASSIFIER SAID 202 B STAY / 17 B MOVE AND IT WAS
WRONG.** It counted `jp exec_stmt` as a reason to stay — but that is the
**UNIVERSAL STATEMENT EPILOGUE**, the way every handler in the tree ends, and a
relocated body ends with a cross-slot return instead. `raise_error`/`load_error`/
`disk_error` are likewise an ERROR INTERFACE a moved body satisfies by returning a
status, which is exactly what `DISKOP_STATUS` already does for the sub-ROM tenant.
Counting them as blockers put `kill_status` (14 B) and `df_nofilespec` (28 B) in
STAY **on the strength of their last instruction**.
⚠️ **The span boundaries were wrong on the first cut too** — bounding `ex_files`
by the next FAT-LIGHT verb let its span run through `ex_open`, `ex_line`,
`ex_close` and `init_filechan`: **1190 B where the verb is 95**, and a 258 B
question answered with 1578 B. A span is only a verb's if the NEXT REGION HEAD
closes it, which is the rule `verbpartition.py` already used.
🛑 **JOOST RULED 2026-09-15, VERBATIM: *"Park it — carve somewhere else"*.**
**RUNG 3 IS PARKED.** The approval he gave earlier the same day was against
**256 B**; 36 B does not justify a relocation slice plus its verification cost
(full `kwknife.py --all` AND `--allfn`, `diskbasic-acceptance` 34/34, `bdos`, the
loader path, `nodisk-acceptance`). ⛔ **NO BYTES MOVE, AND RUNGS 3, 3b AND 4 DO
NOT RE-OPEN WITHOUT A NEW RULING.**
🎯 **WHAT STILL NEEDS THE BYTES**, and it is small enough to be worth finding
elsewhere: the three diskless gates — `FIELD $FE2B`, `LSET $FE21`, `RSET $FE26`,
all measured divergent, all with hook slots identified — cost **8 B per site**,
24 B for three or 16 B if `LSET`/`RSET` share a head the way `FILES`/`LFILES` now
do, against **3 B** free in main page 1 (2026-09-15).
📍 **WHERE TO CARVE INSTEAD, cheapest first**: Route D (`jp`→`jr`,
[`scratchpad/jr_mapper.py`](scratchpad/jr_mapper.py)), which **RENEWS ON EVERY
INSERTION** and has had bytes added to `files.asm` and `sub/playparse.asm` since
it last ran; then the INSTRUCTION-PAIR ngram sweep, worth 113 B the one time it
ran because it sees what a label-BLOCK scan cannot; then ruling 5's sub-ROM carve
for tape LAST (`cload.asm` is 864 B against sub p0's 505 B and p1's 87 B on
2026-09-15, so it fits neither island until the sub ROM itself is carved — which
is the order Joost already set). ⛔ **PROMOTION IS MEASURED SHUT**: the low region
had **0 B** free on 2026-09-15 and page 1 and low share ONE budget.

⚡ **D-NODISKGAP (2026-09-15) — `LFILES` WAS NEVER GATED, AND THE REASON IS THAT
`do_files` IS A SHARED TAIL WITH TWO HEADS.**
🎯 **D-CHANHOOK (2026-09-03) ROUTED `FILES`/`KILL`/`NAME` THROUGH THEIR HOOKS AND
LEFT THE FOURTH ENTRY POINT OF THE SAME FILE BEHIND.** Nobody decided against
`LFILES`; `ex_files` carried the `chan_gate` call and then `jr do_files`, and
`ex_lfiles` sat AFTER that jump — it set its selector and fell into the shared
tail having touched nothing. A diskless build RAN it.
🔬 **MEASURED ON FOUR SIDES, CONTROLS FIRST**
([`scratchpad/nodiskgap_probe.py`](scratchpad/nodiskgap_probe.py)) — and four is
the point: without the CF-3300 there is no way to tell *"wrong on the diskless
target"* from *"wrong everywhere"*.
| case | VG-8020 | CF-3300 | zb NODISK | zb DISK |
|---|---|---|---|---|
| `FROG`, `ZQ` (controls) | ERR 2 | ERR 2 | ERR 2 | ERR 2 |
| `CLS` (control) | ran | ran | ran | ran |
| `FILES` (family control) | ERR 5 | ERR 70 | ERR 5 | ERR 70 |
| `LFILES` **before** | ERR 5 | ERR 70 | **ran** | ERR 70 |
| `LFILES` **after** | ERR 5 | ERR 70 | **ERR 5** | ERR 70 |
🎯 **`FILES` BESIDE IT IS WHAT MADE THE HOLE INVISIBLE** — the family control
refuses correctly on every side, so nothing in the pinned set was red and nothing
looked wrong. The verb simply had no row: `basic_probe_nodisk.py` asked about
`FILES`, `KILL`, `NAME`, `COPY`, `OPEN`, `DSKO$`, `DSKI$` and `DSKF`, and never
about `LFILES`.
🟢 **FIXED, +2 B of main page 1 (5 B → 3 B free, 2026-09-15).** The selector now
goes in FIRST and the gate is SHARED, so a third head cannot repeat this: there is
nowhere to enter that skips it. A second inline gate would have cost 10 B.
🟢 **AND THE ROW EXISTS NOW** (`h.lfiles`), so the gate enforces it rather than
the next reader having to notice.
🔴 **`FIELD` DIVERGES THE SAME WAY AND IS *NOT* FIXED — IT IS PINNED, BECAUSE THE
FIX NEEDS A DECISION.** `ex_field` (`basic/field.asm:257`) has no disk-presence
gate at all; it goes straight to `fch_check`/`fch_mode_class`, so a diskless build
answers the CHANNEL's error where the oracle answers 5 because the verb is not
there. Both forms diverge, which is what says this is the GATE and not the parse:
| case | VG-8020 | CF-3300 | zb NODISK | zb DISK |
|---|---|---|---|---|
| `FIELD` (bare) | ERR 5 | ERR 24 | ERR 24 | ERR 24 |
| `FIELD#1,2 AS A$` | ERR 5 | ERR 59 | ERR 59 | ERR 59 |
⚠️ **The zb-DISK column matches the CF-3300 on both forms**, so this is a
diskless-only defect, not a broken verb.
📌 `h.field` is now in `basic_probe_nodisk.py`'s `PINNED` set — refilling it for
the first time since D-MKHOOK emptied it, and that is the set DOING ITS JOB: the
row is NEW, not newly broken.

⚡ **D-KWPLAY (2026-09-15) — `PLAY` GOES 0 → 9 OF 10 FORMS, AND DESIGNING THE
ROWS FOUND THREE DEFECTS. TWO ARE FIXED; THE THIRD IS THE ONLY THING LEFT
BETWEEN `PLAY` AND TIER 1.**
🎯 **THE BLOCKER WAS THE INSTRUMENT, NOT THE MACHINE.** `make play-acceptance`
observes music with `PLAY(n)`, which answers only WHICH VOICE is sounding — so it
covers `multi-voice` and nothing else. Pitch, volume, envelope and duration are
all invisible to it, and that is why a keyword with a whole MML language behind it
had **no kwsweep row at all**. **The PSG reads BACK**: `OUT&HA0,<reg>` selects and
`INP(&HA2)` returns, LIVE, while the interrupt drain is sounding the note — the
same trick `sound_b` already uses one row above. Control first
([`scratchpad/playpsg_probe.py`](scratchpad/playpsg_probe.py)): `SOUND 0,200` then
read R0 → **200 on both machines**, so everything below is a verdict.
🔴 **DEFECT 1 — `N n` WAS A SEMITONE FLAT, FOR EVERY n FROM 1 TO 96.** The
reference indexes its period table AT n; `pt_cmd_n` did `dec a` first.
[`scratchpad/playnote_probe.py`](scratchpad/playnote_probe.py) walked n = 0, 1, 2,
38…42, 96, 97 on both references: **zerobas(N n) == reference(N n−1)** on every
one, including both ends (ref `N1` = 3228 = `pt_period[1]`, ref `N96` = **13** =
an entry the table did not have). Fixed by deleting the `dec a` and appending the
97th entry — **−1 B, +2 B, net +1 B** of sub page 1 (2026-09-15).
⚠️ **THE HOST TEST AGREED WITH THE DEFECT AND COULD NOT HAVE CAUGHT IT.**
`tests/test_play_parse.py` asserted `note(39)` for `N40` because the asm table and
the host decoder are generated from the SAME `tests/mml_ref.py` — a closed loop.
**Only the differential could see it**, which is the whole argument for the
kwsweep row existing.
🔴 **DEFECT 2 — `>` AND `<` WERE IMPLEMENTED HERE AND ARE NOT MSX1 MML.** Both
references answer **Illegal function call** to all three spellings tried (`>C`,
` > C`, `O5<C`), on the VG-8020 **and** the CF-3300, while this tree happily
sounded the shifted note — an OVER-acceptance, the same class as `&` and found the
same way. Removed: **−37 B of sub page 1** (2026-09-15), which is where the `N`
fix's byte came from. `docs/spec-basic-audio-play.md` §2.2 had them from the same "published MSX
Wiki" list that once carried `&`, and `tools/kwforms.py`'s PLAY bar went from
**ELEVEN forms to TEN** with them.
🔴 **DEFECT 3 — `X<var>;` IS MSX1 MML AND IS NOT IMPLEMENTED HERE. THIS IS THE
OPEN TIER 1 ITEM.** Both references run `A$="O7L1C":PLAY"XA$;"` and sound O7 C
(tone period 53) in all three spellings tried; this tree raises ERR 5. So
`substring-exec` has no row and **`PLAY` stands at 9/10**. ⚠️ It is not a small
fix: the MML parser is a **sub-ROM page-1 tenant**, and resolving a BASIC string
variable by name means reaching the interpreter's variable lookup from inside it.
The closure check says a page-1 tenant may call main low-region/BIOS (`< $4000`),
so the route exists — **whether the lookup SITS there is the unanswered
question**, and it is a spec-sized one, not a row.
🟢 **THE NINE ROWS, ALL SUPPORTED, ALL MATCHING** (`playkw`…`playkw_i`): `notes`
172 (C4's tone period low byte), `note-number` 83, `rest` `8 0`, `octave` 53,
`volume` 3, `envelope` `10 208 7`, `multi-voice` `0 0 -1`, `default-length`
`0 -1`, `tempo` `0 -1`. **`PLAY`'s cut is LOAD-BEARING** (knifed → MISSING).
🎯 **THE `rest` ROW CARRIES ITS OWN CONTROL.** Voice 1 sounds a note and voice 2
rests, so the two channel amplitudes read `8 0`; give voice 2 a NOTE instead and
it reads `8 8`. Without that second reading the 0 is an absence, not a rest.
⚠️ **`AND 15` IS NOT COSMETIC, AND IT WAS MEASURED BEFORE IT WAS BELIEVED.** The
VG-8020 reads R8 back as `$80|value` and R13 as `$D0|value`. Reading the same
register **three times in one run gave three equal answers** (131 131 131), so it
is a stable read-back width difference between the two emulated PSGs, **not a race
against the drain** — which is what it would have to be for no volume or envelope
row to be trustworthy anywhere.
⚠️ **THE DURATION ROWS WAIT IN FRAMES, AND THE FIRST CUT OF THEM DID NOT.** A
`FOR` loop is INTERPRETER SPEED and the reference is ~3× faster: a 200-iteration
wait sat on the wrong side of `L64` there and the right side here, so the row read
`-1 -1` against `0 -1` and that divergence was the apparatus. `T=TIME` … `IF
TIME-T<40 THEN <own line>` is the same two-thirds of a second on every MSX, and
the two sides are then EXACT frame counts from the same formula: `L64`=1 vs
`L2`=50, `T255`=11 vs `T32`=93, both straddling 40.
🎯 **AND THE TWO DURATION ROWS GO LAST — THE `save_b` RULE AGAIN.** They END WITH
MUSIC STILL PLAYING (50 and 93 frames queued against a 40-frame wait), so anything
after them that read the PSG would read their leftovers.
⚠️ **EVERY ROW SETS ITS OWN `O`/`L`/`T`/`V` INSIDE ITS OWN MML STRING**, because
the VCB state PERSISTS ACROSS `PLAY` STATEMENTS — `DRAW`'s ANGLE/SCALE hazard
wearing a different hat.
🔴 **AND THE CF-3300 NEEDED ITS OWN BOOT BEFORE IT WOULD SAY ANYTHING.** Two
scout runs got `machine stored <none>` from it and reported APPARATUS FAILURE
rather than a reading — correctly. `basic_probe_kwsweep.py` already carries the
answer (`MACH_BOOT` 14.0 s and a `SCREEN 0` reset) and the two tables not knowing
about each other is the same gap D-KWORACLE filed in 2026-09-03.
📏 **Sub page 1 free: 50 B → 87 B (2026-09-15)** — the removal paid for the fix
and left 37 B behind.
      ⚠️ **`TXTMAX` IS NOW BOUNDED BY `DETOKBUF`, NOT BY FREE RAM** — at 1280 B
      it does not fit the 1024 B window, so `$BB00` is the stop until DETOKBUF
      is dealt with. Of D-LINEMAX's 1792 B, **1024 recovered, 768 still charged**.
      ✅ The ~12 KB string workload D-LINEMAX cost the suite is affordable again
      (the array rows' shrunken payloads were deliberately LEFT — restoring them
      is a separate call, not a silent side effect of a RAM change).
      **§3.2 ✅ BUILT + GATED 2026-07-29 — `MAXFILES` IS NOW FAITHFUL IN
      MECHANISM.** The channel table is CARVED OUT OF THE POOL at `MAXFILES`
      time, immediately below the string-pool floor
      (`min(HIMEM,TXTMAX) − POOLSIZE − MAXF×50`), so **`FRE(0)` moves −50 per
      channel** (14899 at `MAXFILES=0` → 14149 at 15), `FRE("")` stays 200,
      `OPEN` costs zero further, and **`FCH_CEIL` is 15** — the measured
      reference ceiling. `MAXFILES` now also **CLEARs variables
      unconditionally**, the `sem_same` behaviour.
      **Cost: 1 B of main page 1, 0 B of low region, NO CARVE** (measured by
      relaxing the `$8000` guard and reading `__MEAS_PAGE1_END`, then
      restoring). ⚠️ **Page 1 was at 0 B free on 2026-07-29** (`$8000` exactly).
      🔴 **THE COST WAS SITING, A THIRD TIME.** The first build overran by 8 B
      and all 8 were `MAXFILES`' `CLEAR` — which is verbatim `ex_clear`'s own
      tail. `jp clr_done` costs the 3 bytes the `jp exec_stmt` it replaced
      already spent, so the `CLEAR` came free. The allocation itself was ~free
      because its whole arithmetic chain (`strheap_varceil` →
      `strheap_floor` → `strheap_ceiling`) was ALREADY sub-ROM.
      **DECISION (user, 2026-07-29): charge 50 B/channel, not the reference's
      267.** A zerobas block genuinely IS 50 B (shared `FSECTOR_BUF` cache), so
      it charges what it uses; padding to 267 would reserve 217 B/channel that
      nothing reads and cost a user 4005 B at `MAXFILES=15` instead of 750.
      ⚠️ **This CORRECTS spec §6**, which asked the gate to assert 267 on both
      sides — the gate asserts the MECHANISM (linear per-channel, ceiling 15,
      both sides) and reports each machine's own constant.
      ⚠️ **THE SLOPE ALONE IS A GATE THAT CAN MEASURE NOTHING, AND THIS WAS
      FALSIFIED, NOT REASONED.** With the array ceilings reverted to
      `strheap_floor` — i.e. the carve REPORTED but not RESERVED — `mf0`/`mf2`/
      `mf15` still read a flawless 14899/14799/14149 while arrays grew straight
      through the channel table. The new two-sided `dim_fits`/`dim_over` rows
      catch it (`dim_over` returned 7777 instead of `Out of memory`); its +400 B
      overshoot is sized against the 750 B of slack the bug creates.
      ⚠️ **AND ONE EXISTING ROW WAS UNMEASURABLE**: `sem_str` typed
      `PRINT A$`, and a cleared A$ (empty line) and an uncleared one (`XY`) BOTH
      score `<none>` in this probe's readout — equal on both sides, PASS
      forever. Now `PRINT LEN(A$)` (0 vs 2) with a `REM` control.
      `make chancost-characterize` is now a real GATE (non-zero on unfiled
      divergence / oracle drift / a flat ladder), 31 cases, 9 filed divergences.
      **S-FCH-2 ✅ MEASURED 2026-07-29 (built all four parts, measured each,
      kept the free one).** Full cost **45 B page 1 + 41 B low region = 86 B**
      against **0 B / 9 B free** — the ~100 B estimate was close this time.
      ✅ **ERR 5 IS LANDED AND COST EXACTLY ZERO**: `gb_illegal` is already the
      ERR 5 raiser and already in page 1, so `jp cc,gb_illegal` spends the same
      3 bytes `jp cc,stmt_error` did. `MAXFILES=16`/`255` now raise **Illegal
      function call** and `err_over` traps **ERR 5** — the gate's filed
      divergences drop **9 → 6**.
      **Breakdown (spec §5c):** ERR 5 = 0 B · ERR 59 (closed-channel EOF/LOF)
      = 8 B page 1 · ERR 52 raiser + 2 message strings + sparse table = 14 B
      page 1 + 41 B low · the sparse lookup in `raise_error` = 23 B page 1.
      ⚠️ **64 of the 86 bytes are MESSAGE DATA + A TABLE WALK** — the most
      evictable shape there is. A page-0 sub-ROM tenant could own it and stage
      the message into the **208 B still free at `$EA30..$EAFF`**, leaving a
      shim; that would cut the resident need to ~35-40 B. **MEASURE THAT BEFORE
      SCOUTING A CARVE** — this arc has three times found the cost was siting.
      ✅ **THE EVICTION IS MEASURED TOO: the carve drops 77 B -> 26 B.** The
      table, both strings and the walk move to the EXISTING string-heap tenant
      as op 19 (no new dispatch index), staging the message into page-3 RAM at
      `$EA30`; the two raisers move to the low region. Result: page 1 20 over,
      low 6 over. Moving the shim down too only trades one wall for the other --
      the total stays 26 B, so ONLY A CARVE closes it.
      ⚠️ **BOTH S-FCH-2 BUILDS ARE COST PROBES: MEASURED, NEVER RUN.** ERR 5 is
      the only part executed and gated. Before any of the rest lands: (1)
      `err_bad_filenum` forces `ONEFLG=1` to reach the abort arm and LEAVES IT
      SET -- if the REPL return does not clear it, the NEXT error force-aborts
      instead of trapping; (2) the ten repointed `jp` sites are unconditional in
      the probe, so the LEAN CART WOULD NOT ASSEMBLE -- landing needs per-site
      gating, or the lean cart retired.
      ⚠️ **THE MEASUREMENT APPARATUS WAS WRONG FIRST AND READ PLAUSIBLY (77 B).**
      Relaxing the low region's guard removes its `ds $4000 - $` pad — and that
      pad is what puts the cartridge header at `$4000`. Without it page 1 slides
      down with the low region and `__MEAS_PAGE1_END` measures BOTH walls. Pin
      the header with an explicit `org $4000`. Corrected: 45 B, not 77.
      ✅ **THE CARVE IS DONE: D-MSGENC LANDED 2026-07-29 (`9a0300d`,
      docs/spec-basic-msgenc-carve.md).** Phrase-encoding the 25 resident error
      messages took page 1 from **0 → 24 B free** and the low region from
      **9 → 68 B free**. S-FCH-2's evicted form needs 20 + 15: **funded, with
      4 B and 53 B spare.**
      ✅ **S-FCH-2 LANDED ALL-RESIDENT 2026-07-29 (spec §5d).** ERR 52 `bad file
      number` and ERR 59 `file not open` are raised and printed by the resident
      ROM. It cost **11 B of page 1 + 59 B of low**, not the 45 + 32 estimated:
      page 1 **24 → 13 B free**, low **68 → 9 B free**, lean cart byte-identical.
      No eviction, no tenant op 19, no `ERRMSG_BUF` staging, no repointed `jp`
      sites — **both §5c blockers dissolved rather than gated.** The gate goes
      31 cases / 6 filed divergences → **39 / 4**, closing `sem_zero`,
      `sem_hinum`, `sem_reopen` and `err_notopen`.
      ⚠️ **AND IT WAS NEVER A DEMOTION.** The scout ran first and returned
      **zero**: page-0 tenants reach *no* main routine at all (709 routines,
      every one sub-local — the only main-side import list in the sub-ROM is
      `sub/basic-resident-abi.inc`, eleven page-1-tenant seeds already below
      `$4000`). Nothing in page 1 is pinned there by tenancy, so the cheap move
      was to site S-FCH-2's OWN new content low and leave existing code alone.
      **A shortfall stated as "N bytes short" invites relocating N bytes; ask
      first whether the NEW content has to be where the estimate put it.**
      🔴 **BLOCKER (2) — the lean cart — was dissolved by aliasing the LABEL,
      not by gating the SITES:** `IF ROM_BASE >= $4000 : oo_fail_bfn equ
      oo_fail_syn`. All six rejects keep their existing 3-byte `jp cc,`, which in
      the lean build assembles to the exact bytes it did before. Zero sites
      gated.
      🔴 **BLOCKER (1) — "ERR 52 is not trappable" — WAS A CONFOUND, and so was
      the ONEFLG forcing built on it.** The `err_badchan` row types `MAXFILES=1`
      BETWEEN the arm and the error, and that statement suppresses the handler
      on the reference. Measured three unconfounded ways on the CF-3300:
      `OPEN…AS #2`, `OPEN…AS #0` and `EOF(1)` on a closed channel ALL trap
      (ERR 52, 52, 59). So both codes go through the shared `raise_error_hl`
      trap decision like every other code and **write `ONEFLG` nowhere**.
      Gate rows `bfn_trap`/`bfn_zero`/`fno_eof` + the `bfn_ctl` two-sided
      control now measure the CODE instead of its neighbours.
      🎚️ BUDGET — file-channel context
      🙋 NEEDS-JOOST — a call that is yours to make (retire / delete).

- [ ] **THE TWO TYPE-CODE NAMESPACES SHOULD PROBABLY BECOME ONE.** -> [X-THE-TWO-TYPE-CODE-NAMESPACES-SHOULD](todo/open/X-THE-TWO-TYPE-CODE-NAMESPACES-SHOULD.md) <!-- item:open/X-THE-TWO-TYPE-CODE-NAMESPACES-SHOULD -->

- [ ] **HOW MUCH OF THE 311-BYTE `NO-ORACLE` BUCKET IS A POINTER?** -> [X-HOW-MUCH-OF-THE-311-BYTE](todo/open/X-HOW-MUCH-OF-THE-311-BYTE.md) <!-- item:open/X-HOW-MUCH-OF-THE-311-BYTE -->

- [ ] **THE `--say` SURFACE IS STILL UN-GATED OUTSIDE `ONLY=lnrd-`.** -> [X-THE-SAY-SURFACE-IS-STILL-UN](todo/open/X-THE-SAY-SURFACE-IS-STILL-UN.md) <!-- item:open/X-THE-SAY-SURFACE-IS-STILL-UN -->

- [ ] **A `--say` row with no brackets cannot have a reading.** -> [X-A-SAY-ROW-WITH-NO-BRACKETS](todo/open/X-A-SAY-ROW-WITH-NO-BRACKETS.md) <!-- item:open/X-A-SAY-ROW-WITH-NO-BRACKETS -->

- [ ] **A TRAILING BLANK at end of line is not measurable through the keyboard.** -> [X-A-TRAILING-BLANK-AT-END-OF](todo/open/X-A-TRAILING-BLANK-AT-END-OF.md) <!-- item:open/X-A-TRAILING-BLANK-AT-END-OF -->

- [ ] **`err_verify` AND `brk_msg` ARE THE LAST TWO MAIN-RESIDENT MESSAGES, AND THEY ARE BLOCKED FOR TWO DIFFERENT...** -> [X-ERR-VERIFY-AND-BRK-MSG-ARE](todo/open/X-ERR-VERIFY-AND-BRK-MSG-ARE.md) <!-- item:open/X-ERR-VERIFY-AND-BRK-MSG-ARE -->

- [x] **A PROBE'S MESSAGE LITERAL IS EITHER AN ASSERTION OR A CLASSIFIER ✅** -> [X-A-PROBE-S-MESSAGE-LITERAL-IS](todo/done/X-A-PROBE-S-MESSAGE-LITERAL-IS.md) <!-- item:done/X-A-PROBE-S-MESSAGE-LITERAL-IS -->

- [x] **CLOSED 2026-08-21 (D-FNEXPR2), 0 ROM BYTES — THE FACE FOR A NON-STRING FILENAME (`OPEN 5 AS #1`) WAS UNMEAS...** -> [D-FNEXPR2](todo/done/D-FNEXPR2.md) <!-- item:done/D-FNEXPR2 -->

- [x] **`.` — THE CURRENT-LINE PSEUDO-LINE-NUMBER — LANDED 2026-08-02 (D-DOTLINE). Four pins RETIRED, none added; `...** -> [D-DOTLINE](todo/done/D-DOTLINE.md) <!-- item:done/D-DOTLINE -->

## Beyond — post-MSX1 axes (out of charter, far future)

Two distinct axes past MSX1, captured so the boundaries aren't lost. **Neither is
scheduled**; both require a charter raise. They differ in *provenance*, which is the
whole point of listing them apart.

**A. Later generations — a *clone* axis (has oracles).** MSX2, MSX2+, Turbo-R.
Official ASCII BASIC shipped for these and real machines exist, so this is **today's
method with more surface**: clone-and-validate against an oracle. New ground would be
the V9938/V9958 `SCREEN 4–12` modes + blitter, MSX-DOS 2, R800 timing, and the extra
BASIC verbs each generation added. Methodologically identical to current work — just
bigger.

**B. Extension-cartridge hardware — a *greenfield* axis (no oracle).** Additive,
**own-design** BASIC support for cartridge hardware that **never had official BASIC**.
This is the project's only own-authorship corner: no reference implementation to
clone, no oracle to match — correctness is defined by our own spec + the hardware
documentation, and the rule is *additive-compatible* (new verbs / `SCREEN` numbers
above the built-in range; standard programs untouched). Provenance varies **per chip**:

- **Yamaha V9990 (E-VDP III)** — GFX9000 / Power Graph / Video9000 video cartridge.
  **Clean**: an official Yamaha datasheet exists (A; see `docs/allowed-sources.md`,
  gen `ext`). Not V99x8-register-compatible — its own P1/P2/Bx modes + I/O ports.
- **Konami SCC / SCC+** (K051649 / K052539) — wave-table sound in Konami carts
  (Snatcher, Metal Gear 2, Nemesis…). **Caveat**: *no published manufacturer
  datasheet* — the register interface is known only through community
  reverse-engineering. So support would need our **own black-box characterisation**
  of the chip (the oracle discipline applied to silicon), with community register
  maps as **C-tier corroboration only**, never an authoritative spec.
  **Two deliverables, and the document is the more lasting one:** because no
  datasheet exists, a careful black-box characterisation *produces* primary
  documentation rather than reproducing protected work — for once zerobas is
  *upstream*, a source not a sink. The result (register + waveform reference, with
  method and reproducible raw captures — the probe corpus *is* the document) would
  be an **A-grade, clean-provenance** artifact by our own scale, promoting the SCC
  from "C-tier community-RE only" to "A, our own characterisation," and a standalone
  gift to MSX preservation (emulator authors, homebrew musicians, the next
  reimplementation) **independent of whether the BASIC extension ever ships**.

(Third-party BASIC extensions exist for both — proprietary, **not** a source; design
our own from the hardware docs / our own characterisation.)

## Done — storage transports

➡️ **Moved to [`docs/TODO-done.md`](docs/TODO-done.md) on 2026-08-26** — a prose done-record of disk and tape; no items at all.
The record is unchanged there; this heading is kept only so the citations and
the phase narrative above still have somewhere to land.
