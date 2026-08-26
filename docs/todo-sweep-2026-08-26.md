# TODO sweep — 2026-08-26 (D-TODOSWEEP), tranche 1

**Subject:** every open item in [`TODO.md`](../TODO.md), plus every closed block
carrying a residual marker. **Rule, set by the user: re-run everything, inherit
no claim** — an item is put to a machine even when it is recent and even when a
past sweep already blessed it.

🔴 **THIS IS TRANCHE 39 OF N, AND THE SUBJECT SET IS 176, NOT 146** (§1.2). **60** carry a verdict; **116** do not. The
audit below names the other 135 by id, so an unfinished sweep cannot read as a
finished one.

## 1. The denominator is an instrument, not a heredoc

`tools/todo_inventory.py` parses `TODO.md` into checkbox blocks and emits one
record per block; `--audit` sets a verdict file against it and reports items with
no verdict and verdicts with no item.

🔴 **THE 2026-08-09 SWEEP BUILT ITS DENOMINATOR WITH AN INLINE HEREDOC** — which
cannot be re-run against a later commit without being retyped, while its own
central finding was that a list nobody re-runs cannot be trusted. **The
instrument had the property it was measuring.** It is a tool now.

| | |
|---|---|
| blocks parsed | 367 (346 top-level, **21 nested** — an indented `- [x]` under an open parent is not an independent item) |
| open / done (top-level) | **109 / 237** |
| subject = open + done-carrying-a-residual-marker | **146** |
| verdicted so far | **30** |

### 1.1 Two counts of my own disagreed, so I read

The done-block screen first reported **67**, then **37**. Reading settled it:
**27 of the 29 extra blocks matched on the bare word `OPEN`** — the BASIC verb,
in a file full of disk I/O. 37 is right.

⚠️ **AND NO CHEAP SCREEN EXISTS FOR THE OTHER 200 DONE BLOCKS.** The keyword
proxy flags 37 of 237; the file's own caveat convention (`⚠️`/`🔴`/`💰`/`🧹`/`📌`)
flags **171**; their union is 178. This project writes caveats on *closed* work
as a matter of style, so the convention cannot discriminate. **The only real
surface is reading 9,006 lines**, and that is filed as its own pass rather than
claimed here. The pickup list's own header records that this failure mode has
already happened.

## 2. Findings — tranche 1

Every row ran on `Philips_VG_8020`, `National_CF-3300` and the repack machine,
with a control on the same apparatus. Verdicts: `scratchpad/sweep_verdicts.json`.
Probes: `scratchpad/sweep_tranche1.py`, `scratchpad/sweep_paintflood.py`.

| id | item | verdict | reading |
|---|---|---|---|
| T131 | SCREEN-2 `PAINT` floods on the references | **LIVE** | `POINT(50,21)` below the wall: **vg8020 9, zb 4** — the filed claim exactly |
| T056 | `PLAY(n)` function unimplemented | **LIVE** | refs print `0`; zb raises **`Missing operand`** |
| T064 | `RUN <lineno>` in direct mode | **LIVE** | refs print `[B]`; zb prints **`[A][B]`** |
| T008 | `KEY n,"str"` unimplemented | **LIVE** | refs silent; zb raises **`Syntax error`** |
| T277 | Screen-editor REPL | **LIVE, REFRAMED** | see `docs/spec-basic-editscout.md` — the blocker named the wrong obstacle |
| T123 | third `SCREEN` argument's domain | **STALE AS FILED** | filed *UNMEASURED*; `SCREEN 0,0,0` and `0,0,99` are accepted on **all three** |
| T278 | editor / program-management bucket | **PARTLY STALE** | `TRON`/`TROFF`/`FRE`/`SWAP`/`ERASE` all SUPPORTED today; `RENUM`/`AUTO`/`DELETE` shipped. Down to `WAIT` + full `CLEAR` |
| T279 | keyword-completeness gaps | **STALE** | today's `kwsweep` has **no `MISSING=` line**; the item says "34 genuinely absent" |
| T029 | "main page 1 was 1 B free" | **STALE** | **89 B** |
| T047 | "page 1 2 B, low region 17 B" | **STALE** | **89 B / 39 B** |
| T122 | the pickup list's own RANKING | **STALE** | ranks 38/62 apparatus, 15 BASIC; the list is 109 open, split 60/39/3/7 |

**5 LIVE, 5 stale or partly stale, 1 live-but-reframed.** Nearly half the sample
did not survive re-running — and T122, the item that *is* the ranking, is one of
the stale ones.

🎯 **T056 IS THE SHARPEST.** A closed `D-PLAYOP` block sits directly beneath it
in the file, closed the same week, both about `PLAY` and a missing operand.
Reading would have merged them. **Running separated them**: D-PLAYOP fixed the
`PLAY` *statement*'s operand; the *function* form `PLAY(0)` still raises.

## 2a. Findings — tranche 2

Three items that filed an EXACT program. Each was re-run as its own fixture.
Probe: `scratchpad/sweep_tranche2.py`.

| item | verdict | reading |
|---|---|---|
| `SAVE`/`LOAD`/`BLOAD` with no argument | **STALE** | all three now raise **`Missing operand in 10`** — the divergence is gone |
| stored `DATA` literal charges the string pool | **LIVE** | refs `[OK]` / `[OK]`, zb **`Out of string space in 60`**, both rows |
| a line store is bounded by `TXTMAX`, not HIMEM | **LIVE** | `FRE(0)` after `CLEAR 300,TXTTAB+1000`: **148 / 148 / 646** — the filed numbers exactly; a 32-byte line then raises `Out of memory` on both references while zb stores it (646 → 615) |

⚠️ **THE `TXTMAX` ROW REPRODUCES THE SYMPTOM AND NOT THE MECHANISM.** The item
attributes it to *"`CLEAR`'s HIMEM argument does not reach the store check"* —
but the control shows plain `CLEAR 300` reads **148/148/646** as well, so the
HIMEM argument moves `FRE(0)` on NEITHER side. The divergence is real and the
numbers are exact; the stated cause is untested by these rows and is recorded as
such rather than inherited.

🟢 **THE `DATA` CONTROL IS LOAD-BEARING**: the same program with `READ`/`DATA`
removed prints `[OK]` on all three, so `CLEAR 60` + `DIM` + `STRING$(25)` is not
itself the cost — it is the `READ` of a stored literal.

Running total across both tranches: **8 LIVE, 6 stale or partly stale.**

## 2b. Findings — tranche 3, the disk-channel items

⚠️ **A STOCK VG-8020 HAS NO DRIVE.** It errors on every disk statement — the
`FIELD` control row raises `Bad file name` *and* `Illegal function call` on it —
so a disk row scores on the CF-3300 and zerobas only. That is a denominator
fact, stated rather than averaged away. Probe: `scratchpad/sweep_tranche3.py`.

| item | verdict | reading |
|---|---|---|
| non-tiling `LEN=r` | **LIVE** | `OPEN"TS.DAT"AS #1 LEN=100`: cf3300 `[OK]`, zb **`Syntax error`** — the filed row exactly. Control `LEN=128` is accepted on **both**, so zb's `OPEN..LEN` works and it is the non-tiling value it rejects |
| malformed filespec prints `load error` | **LIVE (first clause)** | `FILES"TOOLONGNAME.EXTRA"`: zb prints **`load error`**, cf3300 prints no error at all |
| `FIELD #(A$<5)` classification order | **REFRAMED — not resolvable here** | zb `Type mismatch`, cf3300 `Type mismatch`, vg8020 `Illegal function call` |

🔴 **THE `FIELD` ITEM IS FILED AS ZEROBAS-VS-REFERENCE AND THE TWO REFERENCES
DISAGREE.** zerobas matches the CF-3300 exactly. Worse, **the VG-8020 reading
that the item rests on may be an apparatus artifact**: that machine has no
drive and raises `Illegal function call` on every `FIELD`, so its reading cannot
be separated from "no drive" by this apparatus. Settling it needs a VG-8020 with
a disk interface. 🎯 **A filed divergence can be a disagreement between the two
oracles, and the item's own wording hides that by naming only one.**

⚠️ **THE MALFORMED-FILESPEC ITEM IS ONLY HALF SCORED.** Its second clause — *"and
`FILES` lists anyway"* — needs a screen read; an error scrape cannot see a
directory listing. Recorded as unverified rather than folded into the verdict.

Running total across three tranches: **10 LIVE, 6 stale or partly stale, 1
reframed-unresolvable.**

## 2c. Findings — tranche 4: the rows that could not share a batch

Probe: `scratchpad/sweep_tranche4.py`, plus the item's **own** probe re-run
(`scratchpad/trapsvc_probe.py --only int.six,gos.leak`).

### The `TRAPSVC` six-event cap — LIVE, exact

`int.six` reads **`9 18` / `9 18` / `6 18`** — the filed reading, unchanged.

🔴 **BUT ITS SUPPORTING CONTROL IS AN UNFILED SECOND DIVERGENCE.** `gos.leak`
reads **`12 0` on both references and `8 7` on zerobas**. The item says only
*"`gos.leak` caps at 8, which is what says the cap is `TRAPSTK_MAX` and not
`GOSUB_DEPTH`"* — it never records the reference value. So *the references reach
12 with no error while zerobas stops at 8 with ERR 7* is nowhere in the record.
🎯 **A row cited as a control can be carrying a divergence of its own, and citing
it for one property is how the other one goes unwritten.**

### `WAIT` — the gap tranche 1 could not measure

| | reading |
|---|---|
| VG-8020 | `WAIT 1,0` is typed and **no `Ok` prompt ever follows** — still inside it. The no-`WAIT` control shows `Ok` |
| zerobas | **`Syntax error`** — `WAIT` is unimplemented here |

🔴 **THE FIRST ATTEMPT WAS ABORTED BY THE HARNESS, AND THE ABORT WAS THE
EVIDENCE.** With a `PRINT` after the `WAIT`, the echo guard refused to report
anything at all: the reference was still inside `WAIT` when the next line was
injected, so 12 leading characters were swallowed and it declared the delivery
mangled. **A guard that declines to produce a reading told me more than the
reading would have.**

### `FILES` with a malformed name — the second clause is FALSE

The item reads *"a malformed filespec prints `load error` **and `FILES` lists
anyway**"*. An error scrape is structurally blind to the second half, so this row
draws the screen:

```
ZBFILES"TOOLONGNAME.EXTRA"        <- zerobas
load error
File not found
[END]                              <- no listing at all
```
against the bare-`FILES` control on the same disk, which lists six entries
(`TEST.BIN HI.TXT PROG.BIN PROG.BAS PROG2.BAS TS.DAT`) — so a listing **would**
have been visible.

🔴 **CLAUSE 1 IS LIVE AND CLAUSE 2 IS FALSE.** The half nobody ran is the half
that is wrong — the `a-justification-parenthesis-is-an-unrun-claim` shape, in an
item that had been carried for five days as a single finding.

⚠️ **The cf3300 side of that read is unusable**: `run_case` applies no reset, so
that machine stayed in SCREEN 1 and the scrape is VRAM garbage — obviously
garbage rather than plausibly wrong, which is the good failure mode. The
reference half of clause 1 rests on tranche 3's batched run, which did reset it.

Running total across four tranches: **12 LIVE, 6 stale or partly stale, 1
reframed-unresolvable, 1 split (half live, half false).**

## 2d. Findings — tranche 5: the space and gate items

These assert facts about the tree and the battery, so the instrument is a
targeted static check plus today's walls and the 39/39 battery. Every check
prints its evidence — *0 hits* and *I looked in the wrong place* read identically
otherwise. Probe: `scratchpad/sweep_tranche5.py`.

| item | verdict | reading |
|---|---|---|
| 5 non-atomic openMSX publishes | **LIVE, exact** | still at lines **379, 392, 401, 440, 455** — the filed line numbers — and **0** mentions of an atomic publish in the file |
| a tracked script may hardcode `/Users/joost` | **LIVE, now with a denominator** | **546** tracked `.py`/`.sh`; **26** lines contain it, a dozen being `ROOT = "/Users/joost/projects/zerobas"` in tracked scratchpad scripts. No checker exists |
| the tape patch pair is unguarded | **LIVE, confirmed** | the checker's `PAIR` is main-only; the tape pair is tracked and clean |
| no gate reads the boot banner | **LIVE, stale count** | no probe reads it; the battery is **39** gates, the item says 34 |
| "122 `/tmp` literals outside the root" | **STALE FIGURE, class live** | **104**, not 122 |
| "`latch-check` is THE ONE gate with no prerequisites" | **STALE AS WORDED** | **ten** `*-check` targets have an empty prerequisite list |

🔴 **TWO OF THOSE TEN ARE MINE, ADDED EARLIER TODAY.** `patch-freshness-check`
and `citation-check` both have empty prerequisite lists, so this session is part
of why the uniqueness claim is now false. The underlying hazard — `latch-check`
refuses after `rm -rf build` — is untested by this check and stays open.

🔴 **AND THE `/tmp` FIGURE NEARLY WENT THE WRONG WAY.** `make temp-root-check`
prints **124 pinned literal(s)**, which reads as a refutation of the item's 122 —
in the direction of *"it grew"*. It counts a different set: 20 of the 124 are
**inside** `/tmp/zerobas` and were never in the item's class. Outside the root is
**104**, so the set has *shrunk* by 18 — the shrink-only gate working as designed.
🎯 **Two numbers that disagree can both be right about different sets, and the
gate's number is not automatically the truer one.** Reading `check_temp_root.py`
settled it.

Running total across five tranches: **16 LIVE (3 with a stale figure inside),
8 stale / partly stale / reframed / split.**

## 2e. Findings — tranche 6

Probe: `scratchpad/sweep_tranche6.py`.

| item | verdict | reading |
|---|---|---|
| `CLEARPOOL=0` untested by `switch-build-check` | **LIVE, exact** | the gate flips `G6/G7/G8_RESIDENT`, `I1_RESIDENT`, `TRAPS_T3`, `TRAPS_T4` — **not** `CLEARPOOL`; and `basic/sysvars.inc` carries both `FPERR_MISSOP equ 12` and `equ 11`, the "12 with, 11 without" it describes |
| 28 aliases with no per-site row set | **LIVE** | **333** label-to-label `equ` aliases across `basic/` + `sub/` today, and **no** per-site row set anywhere in `probes/` |
| a `DEF FN` string formal's shadow slot | **LIVE (row-set half only)** | no probe row names the class |
| a wall figure hardcoded inside a gate | **CLASS MEASURED EMPTY TODAY** | **0** hardcoded 16-bit ceiling constants remain in `tools/` |
| the 4 B dup-span D-ONLIST created | **NOT VERIFIED — wrong instrument** | see below |

🔴 **I DECLINED TO SCORE ONE RATHER THAN SCORE IT BADLY.** The dup-span item
asserts two spans are **byte-identical**, and a `grep` cannot decide that — *a
span is byte-identical without being entered the same way* is a lesson this
project has already filed twice, and `tools/dupspan_indep.py` exists precisely
for it. Scoring it with a regex would have reproduced the mistake the tool was
built to prevent, so it is deferred to the proper instrument and says so.

⚠️ **AND ONE VERDICT IS DELIBERATELY HALF A VERDICT.** For the `DEF FN` shadow
slot, only the *row-set* half is scored (no probe names the class). My `shadow`
grep returned 63 hits and the ones I read were **sprite** shadows and **keyword**
shadowing — noise. Whether the slot actually is a GC root was **not determined**
and needs a read of the walk, not a grep.

🎯 **"CLASS EMPTY" IS NOT "CLOSED".** The hardcoded-wall item's named instance was
fixed in its own filing commit and nothing has re-grown — but 0 members is a fact
about today's `tools/`, not about the apparatus that still permits them. The right
restatement is *make the class unwritable*, not *close it*.

Running total across six tranches: **19 LIVE (3 with a stale figure, 1 scored
only in half), 8 stale / partly stale / reframed / split, 1 class-empty, 1
declined for want of the right instrument.**

## 2f. Findings — tranche 7: the deferred dup-span item, through the right tool

Tranche 6 declined to score the dup-span item with a regex. `tools/dupspan_indep.py`
re-run today settles **two** items at once.

### The byte-identical-span supply has halved, and the fundable figure is 20× smaller

| | filed | **today** |
|---|---|---|
| groups | 53 | **26** (over 1445 non-empty spans) |
| nominal | 403 B | **163 B** |
| **measured SAFE net** | *not stated* | **8 B** |

🎯 **THE NUMBER THAT MATTERS IS NOT THE NOMINAL ONE.** 163 B nominal is **8 B
safe** once the tool decides terminators, `jr` reach and fallthrough entry. An
item quoting only the nominal figure overstates the fundable amount by roughly
twentyfold — and this item quotes 403 B.

### And the 4 B dup-span is invisible to the whole toolchain, not merely unmeasured

**No `esn_` label appears in any of the 26 groups.** The tool works on
**label-to-label** spans — its own docstring, line 4 — and this item's subject is
an **interior fragment**: `esn_notlineno`'s discriminator against a test four
instructions above it, *inside the same label block*.

🎯 **THAT IS EXACTLY THE BLIND SPOT A SIBLING ITEM ALREADY FILES.** The
`clone_scout` item says it prices **label-blocks**, so a routine split by an
interior label is priced at a fraction of its collapse. Both dup-span tools share
that span model. So the 4 B item is not "unmeasured pending a run" — it is
**unreachable by the instrument**, and the two items are one finding seen twice.
They should be linked.

Running total across seven tranches: **19 LIVE, 9 stale / partly stale /
reframed / split, 1 class-empty, 1 unreachable-by-instrument.**

## 2g. Tranche 8 — a bulk screen, and the four ways it lied

At five items a tranche the remaining 116 needed a faster instrument, so
`tools/todo_subject_check.py` asks a cheaper question of all 146 at once: **does
the thing this item names still exist?**

🔴 **WHAT IT MAY AND MAY NOT DO.** A named file or symbol that is GONE is
evidence the item's subject left the tree. A named symbol that is PRESENT proves
only that the subject exists — nothing about whether the behaviour still holds.
**The screen is allowed to retire an item and never to confirm one.**

It reported **54 candidates for stale**. The true figure is **9**. All four
false-positive classes were found by running it:

| # | class | example |
|---|---|---|
| 1 | **a bare basename is not a path** | `run_gates.py` declared GONE — it is `tools/run_gates.py` |
| 2 | a 7-hex token is a git revision | `a897bcd`, `b8a8137` reported as missing symbols |
| 3 | `.rom`/`.dsk` are gitignored build artifacts | absent from `ls-files`, present in `build/` |
| 4 | **an item may name a symbol because it is PROPOSING it** | `sg_walk_fnframe` |

🔴 **CLASS 1 IS THE ERROR THE CITATION GATE WRITTEN EARLIER THIS SESSION EXISTS
TO PREVENT** — *match the path, not the basename* — committed by me in the
inverse direction, a few hours later, in a different tool. Knowing a rule and
encoding it in one checker does not carry it to the next one.

🔴 **CLASS 4 CANNOT BE FIXED IN THE SCREEN, AND IT INVERTED A VERDICT.** The
`DEF FN` GC-root item names `sg_walk_fnframe`, which is absent — the screen
flagged it as stale. Reading the item shows it *proposes* that symbol: *"the fix
is either a `sg_walk_fnframe` or a snapshot at bind time"*. **A screen cannot
tell a named subject from a named remedy.**

And reading it settled the item the other way. The walk's actual members today
are `sg_walk_arrays`, `sg_walk_scalars`, `sg_walk_strtab`, `sg_walk_temps` —
exactly the *"variable chain and temp-descriptor stack"* the item names, with **no
FN-frame walker of any name**. So the shadow slot really is unwalked: tranche 6's
deliberately half-scored verdict is upgraded to **LIVE, mechanism confirmed**.

## 2h. Tranche 9 — reading the screen's candidates, and two more ways it lies

Of the 9 the screen flagged, **two more false-positive classes** turned up, so the
tally is six:

| # | class | example |
|---|---|---|
| 5 | **an external tool's command vocabulary** | `loadstate` is an openMSX command, not a repo symbol |
| 6 | **a shared-stem path pair** | `zerobas-main-eu.ips/.bps` parsed as one path |

🎯 **SIX FALSE-POSITIVE CLASSES, EVERY ONE FOUND BY RUNNING THE SCREEN AND
READING WHAT IT SAID.** None was predictable from the code. That is the argument
for the rule this sweep adopted: **a screen may retire an item and may never
confirm one.**

Four items settled:

| item | verdict |
|---|---|
| `CAPTURE ON A done SENTINEL` | **superseded by its own text** — the headline is already struck through and the body says the speed case is dead. It is kept for its reasoning and should not sit in the open list |
| `2-Tier2-c` regression | **LIVE, and its named probe does not exist** — `disk_probe_provider_dosboot.py` is absent from the tree |
| REGIONALISE THE REPACK BUILD | **LIVE — a standing decision, not a measurable claim** |
| SLIM THE FILE-CHANNEL CONTEXT | **not measurable — awaiting a human sign-off**; the measurement is done, the decision is open |

🔴 **AND ONE OF THEM IS THE MORNING'S CITATION CLASS IN A PLACE THE GATE CANNOT
SEE.** The Tier2 item names a probe that was never committed. `check_citation_paths.py`
polices `scratchpad/` paths in committed docs — and `TODO.md` *is* in its corpus,
so a dangling `scratchpad/` path there would be caught. A dangling **`probes/`**
path is policed by nothing.

🎯 **TWO OF THE FOUR ARE NOT FALSIFIABLE AT ALL** — a recorded coverage trade and
a decision awaiting sign-off. *"Re-run everything"* has a floor: an item whose
content is a judgement cannot be put to a machine, and saying so is the verdict.

## 1.2 🔴 The denominator was too small, and the missing 30 are the important ones

The subject set was scoped as *open + done-carrying-a-residual-**keyword***, and
that gave **146**. It is wrong.

**38 of the 237 done blocks open with a `🔴`/`⚠️`/`💰` headline that states a
divergence** — and **only 8 of those 38 also carry a residual keyword.** The
keyword screen silently dropped **30 blocks**. Subject is now *open +
keyword-marked + open-reading-headline* = **176**.

🎯 **AND THE 30 ARE EXACTLY THE CLASS THE PICKUP LIST'S OWN HEADER EXISTS TO
CATCH** — *"a residual cannot be lost by being written up inside a `- [x]`
block"*. The header warned about this; the sweep scoped itself with an instrument
that could not see it. A sample of what is sitting inside `- [x]`:

* `SCREEN 3 DRAWS ON BOTH REFERENCES; zerobas raises ERR 5`
* `LINE (0,0)-((A$<5),1)` is ERR 5 here and **ERR 13 on both references**
* `SCREEN (1<5)` is `Syntax error` here and **`Illegal function call`** on the reference
* `A BOX FILL WRITES A FULLY-COVERED BYTE AS BACKGROUND`
* `THE ARC MASK DIVERGES AT LARGE RADII`
* `ZEROBAS'S SPOKE ENDPOINT DIVERGES FROM THE REFERENCE AT NEAR-ZERO ANGLES`
* `DRAW's BOOT-DEFAULT SCALE STATE IS NOT S4`

🔴 **THESE ARE BASIC-SURFACE DIVERGENCES, AND THEY NEVER APPEARED IN ANY LISTING
OF "OPEN" WORK** — not in the pickup list, not in my earlier answer about what to
prioritise, because every one of them is marked `- [x]`. A dozen-plus graphics and
error-classification divergences have been invisible to prioritisation.

⚠️ **THIS IS THE THIRD TIME THIS SWEEP'S DENOMINATOR HAS MOVED** — the filed 165
cited paths became 238; the done-block screen read 67 then 37; and now 146 becomes
176. Each time the instrument, not the tree, was what changed.

## 2i. Tranche 11 — the hidden divergences, re-run: all three had HEALED

The first three of the 30 blocks §1.2 surfaced, each a BASIC-surface divergence
filed inside a `- [x]`. Probe: `scratchpad/sweep_tranche11.py`.

| item (as filed) | today, all three machines |
|---|---|
| `SCREEN 3` draws on both references; **zerobas raises ERR 5** | **`ok 15`** on all three — zerobas draws |
| `LINE (0,0)-((A$<5),1)` is **ERR 5 here**, ERR 13 on both references | **ERR 13** on all three |
| `SCREEN (1<5)` is **`Syntax error` here**, `Illegal function call` on the reference | **ERR 5** on all three |

**Three filed divergences, three healed.** Each carries a control on the same
apparatus (SCREEN 2, a numeric coordinate, a plain `SCREEN 1`) reading `ok` — so
the handler fires only on the subject, and the differing codes (13 vs 5) show it
reports the real one rather than a constant.

🔴 **AND THE FIRST DRAFT OF THIS PROBE WAS BLIND IN A WAY THAT READ AS
AGREEMENT.** Every row did `SCREEN <n>` … then `SCREEN 0:PRINT`, and **a mode
change clears the screen** — so an error raised in SCREEN 2/3 was wiped before the
SCREEN-0 scrape ran. All six rows came back identical with no error anywhere,
which reads as *"all three agree"* and was really *"the instrument erased the
answer"*. 🎯 **The right answer and the erased answer look the same**; only the
absence of *any* error on *any* machine gave it away. Fixed by trapping the error
and carrying its CODE out as a value, which survives any number of mode changes.

⚠️ A second draft stored the program without running it, and the `[...]` reader
returned the **echo** of the `PRINT` lines rather than their output — an explicit
`RUN` fixed it. Two instrument faults before one reading.

## 2j. Tranche 12 — and the §1.2 signal over-includes

| item | verdict |
|---|---|
| `RUN <lineno>` ignores the line number (in a PROGRAM) | **STALE — healed**; all three print `B` |
| `CIRCLE` r ≥ 256 product bound | **agrees at the sampled points** — weaker than the filing |
| `DRAW`'s boot-default scale state | **closed in its own body** |

🎯 **ONE VERB, TWO MECHANISMS, TWO OPPOSITE VERDICTS.** `RUN 30` *inside a
program* now honours the line number on all three machines — healed. `RUN 20`
*typed at the prompt* still runs from the top — **LIVE**, verdicted in tranche 1.
Merging them by name would have been wrong in both directions.

🔴 **AND ONE ROW IS WEAKER THAN THE CLAIM IT TESTS.** The `CIRCLE` item was
measured *"on the whole pattern plane"*; my row samples **three points** and they
agree on all three machines. A 3-point signature can agree while the planes
differ, so **this row cannot retire the item** — it says only that the divergence
is not at those points. Recorded as such rather than as a heal. The control
(r=128, reading `15 4 4` against r=256's `4 4 4`) proves the fixture discriminates
radius, which is what makes the negative meaningful at all.

⚠️ **A NEW CLASS IN THE §1.2 SET: the open-reading headline OVER-INCLUDES.** The
`DRAW` scale block opens `🔴 …ZEROBAS TREATS IT AS IF IT WERE` and its body says
*"✅ CLOSED 2026-08-11 by D-DSCALE … Both rows below are undeferred and green"*.
The headline is the **original filing**; the body records the closure. So the 38
are not all hidden live work — some are filed-and-closed in one block, and only
reading separates them. The signal is still right to widen the subject set (three
of the four read so far were genuinely live-as-filed), but it is a *reason to
read*, never a verdict — the same rule the symbol screen earned in tranche 8.

## 2k. Tranche 13 — the 38 sort themselves, and a calibration on a sample of two

Of the 38 open-reading headlines §1.2 surfaced, **10 declare their own disposition
in the body** — `✅ CLOSED`, `DECLINED`, `WITHDRAWN`, `SUPERSEDED` — within the
first few lines. **3 of the 38 are struck through** (`~~…~~`), the file's
retraction marker, and all three also say `DECLINED` in the body.

So the 38 sort into:

| | n |
|---|---|
| self-declares closed / declined / withdrawn / superseded | **10** |
| does not — needs reading or running | **28** |

⚠️ **THESE 10 ARE VERDICTED FROM A BODY CLAIM, NOT A MEASUREMENT**, and the
sweep's whole rule is to inherit nothing. Each is recorded as **`how: read — NOT
re-run`** so it can never be mistaken for a machine result.

🟢 **THE CALIBRATION, AND ITS SIZE.** Two of these ten were independently re-run
in tranche 11 — the `LINE` string-relational row and `SCREEN (1<5)` — and the
machine agreed with the body **both times, 2 of 2**. That is a reason to believe
the marker is honest in this file. **It is calibration on a sample of two, not a
licence**, and the distinction is written into every one of the ten verdicts
rather than resolved silently in favour of speed.

## 2l. Tranche 14 — closed by MECHANISM, which beats closed by claim

Three of the 25 non-self-declaring hidden blocks, each verified by finding the
fix **in the tree** rather than by believing the block:

| item | evidence |
|---|---|
| a re-run probe overwrites its own pre-fix measurement | `bank_guard` present in all three `spokeline_char*.py`; `drawclamp_bands.py` uses the versioned `.pre.json`/`.post.json` paths |
| `injector-check` classifies its own detector as an injector | an `EXEMPT` table exists, each entry stating its CLASS, consulted at the walk site |
| a knife runner read a complete exit-2 report as truncated | `tools/check_report_shape.py` exists and its **own docstring names this defect** — *"the exit-2 rows are indented two spaces"* |

🟢 **THE THIRD IS THE STRONGEST KIND OF CLOSED**: the fix is a **standing gate**
(`rowshape-check`, one of the 39 green today), so it cannot lapse the way a note
can. *"Closed by a gate"* and *"closed by a paragraph"* are different claims and
this sweep records which one it found.

⚠️ **AND TRANCHE 13'S MARKER REGEX UNDER-MATCHED.** It required `✅ **CLOSED`;
this block writes `**CLOSED 2026-08-17 by D-DRAWCLAMP**` with no tick, so it was
never swept into the self-declaring set. **The 10 are a LOWER BOUND on that class,
not its size** — which is the safe direction (it sends blocks to be read rather
than retiring them unread), but it means "28 still need reading" is an
over-estimate of the real work.

## 2m. Tranche 15 — the lower bound was a lower bound

Tranche 14 predicted the strict `✅ **CLOSED` marker under-counted. Broadening it
(no tick required, twelve lines deep) matches **9 more** of the pending hidden
blocks. So of the 38:

| | n |
|---|---|
| self-declares closure | **19** (10 strict + 9 broadened) |
| still needs reading or running | **13** |

🟢 **AND THE BROADENED MARKER WAS SPOT-CHECKED BEFORE BEING TRUSTED IN BULK**,
because a 12-line window can match a sentence about somebody *else's* closure.
Two were read in full:

* the **box-fill byte rule** — *"CLOSED 2026-08-17 by D-BFBYTE — `gbf_split` +
  `gbf_row` + a corner sort, 153 B … gate 355/0 with 11 new rows … knives 3
  predicted, 3 EXACT"*, and a named 21 % regression on the narrowest case,
  accepted against 35.8× on the common one.
* **LINE's two work-area writers** — *"CLOSED THE SAME DAY … `w_err_scr0` and
  `w_err_step` (gate 358 → 360/0) … Knives both EXACT"*.

Both carry byte counts, gate row totals and knife results. **The marker is not
decorative in this file** — which is a statement about a sample of two, and is
recorded as one.

⚠️ All 9 are still labelled **`how: read — NOT re-run`**. Nineteen of the 176
verdicts now rest on a body claim rather than a machine, and the verdict file
says so on every one of them, so a later reader can re-run exactly that subset.

## 2n. Tranche 16 — a row that agreed, and could not have disagreed

The spoke-endpoint item was *"measured from BANKED data, no gate row covers it"*,
so this is the first time it has been put to a live machine. The item's own
fixture — `PSET(75,60),9 : CIRCLE(60,60),15,6,-0.01,1.57` — reads **`6 6 6` on all
three machines**.

🔴 **THAT IS NOT A HEAL, AND THE ROW COULD NOT HAVE SHOWN ONE.** `(75,60)` is
centre + `(15,0)` — a point **on the arc itself**, and the arc spans `-0.01..1.57`,
which includes angle 0. **The `CIRCLE` paints that pixel whether or not the SPOKE
reaches it.** The row cannot separate the two writers, so agreement is not
evidence the endpoints agree. Recorded **unresolved**, not healed.

⚠️ **AND THE FIRST DRAFT WAS NOT THE ITEM'S FIXTURE AT ALL** — it dropped the
`PSET(75,60),9` seed, which turns *"does colour 6 reach and overwrite a pixel
holding 9"* into *"does the spoke paint the pixel"*. Same coordinates, a
different experiment. It had to be re-run verbatim before the confound above was
even visible.

🎯 **TWO FAULTS, ONE SHAPE**: both were the row failing to ask the item's
question. This is the sibling of the `PAINT`-flood row in tranche 1, where a
second control (`POINT` *above* the wall) was what made a negative meaningful —
here no such control exists yet, so the honest output is a **named gap** and what
would close it: a point on the spoke but **off** the arc, or the banked
full-plane capture the item was originally measured from.

## 2o. Tranche 17 — the control that turns a non-answer into a verdict

Tranche 16 could not separate the spoke from the arc. This row samples the spoke
**strictly inside** the radius, where the arc cannot reach:

| row | vg8020 | cf3300 | zb |
|---|---|---|---|
| y=60 at r=5/9/13 (inside the arc) | `6 6 6` | `6 6 6` | **`6 6 6`** |
| y=59, same radii — where a `(15,−1)` ray must pass | `4 4 4` | `4 4 4` | **`4 4 4`** |
| **positive** start angle, so **no spoke at all** | `4 4 4` | `4 4 4` | `4 4 4` |

🟢 **THE THIRD ROW IS THE ONE THAT MATTERS.** A positive start angle draws no
spoke, and the same y=60 pixels go background on all three — **that is what proves
those pixels belong to the SPOKE and not to the arc.** Without it this would have
been tranche 16's non-answer again, with better coordinates.

**Verdict: the filed `(15,−1)` ray is refuted** — all three machines draw the
spoke along y=60 for every sampled radius, and the y=59 alternative is empty
everywhere.

⚠️ **BUT THE ENDPOINT PIXEL ITSELF IS STILL UNSEPARABLE**: centre+`(15,0)` lies on
the arc, painted either way. So the claim is refuted **for the ray** (13 of 15
pixels measured identical) and **untested for the single last pixel**. 🎯 That is
a far narrower claim than *"zerobas's spoke endpoint diverges"*, and the item
should be **restated to it**, not closed outright — closing it would discard a
live, unmeasured one-pixel question, and leaving it as filed would overstate a
refuted one.

## 2p. Tranche 18 — an instrument that counted bytes the screen may not show

The remaining arc items were filed as `ref N px <hash> / zb M px <hash>` over the
whole plane, so this tranche captured raw VRAM instead of sampling `POINT`. It
produced **no verdicts**, and the reason is worth more than one would have been.

| after `SCREEN 2:CLS` | empty plane | with a circle | XOR |
|---|---|---|---|
| zerobas | **0 px** | 536 | 536 |
| VG-8020 | **4923 px** | 5198 | **275** |

🔴 **THE REFERENCE'S PATTERN TABLE IS NOT EMPTY AFTER `CLS`.** So a whole-plane
bit count compares a 4923-pixel baseline against a 0-pixel one — and the obvious
repair, XOR against the empty plane, is no better: where the figure sets a bit the
leftover **already** set, nothing changes, so the count *under-reports* what was
drawn. The same circle reads **275 on the reference and 536 here**, and neither
number is the figure.

🎯 **THE INSTRUMENT NEEDS THE NAME TABLE, NOT JUST THE PATTERN TABLE.** The
leftover is almost certainly unreferenced by the name table — which is why the
items' own figures are small (170/127/97/135) while mine are ~5000. Counting the
pattern generator alone measures bytes the screen may never display.

⚠️ **AND THE TEMPTING READING IS THE ONE TO REFUSE.** zerobas's counts came out at
**exactly the filed REFERENCE values on all four rows** — 170, 127, 97, 135
against filed ref 170, 127, 97, 135. That looks like four heals. It is **not
evidence**, because the reference side of the very same run is invalid; a number
that matches expectation is not thereby measured. All three items are recorded
**NOT MEASURED**.

🔬 **ONE NEW QUESTION, UNFILED ANYWHERE**: `SCREEN 2:CLS` leaves **4923** set
pixels in the VG-8020's pattern generator and **0** in zerobas's. If the name
table does not reference them it is invisible and harmless; if it does, it is a
visible divergence. Nothing in the sweep or the battery asks.

## 2q. Tranche 19 — the instrument fixed, and one row that validates it

Tranche 18's plane count was wrong. The fix is one rule: **count a pattern bit
only where its colour-table row has fg nibble ≠ 0** — fg 0 is *transparent* on
MSX and shows the backdrop. (Both machines' name tables are identity-mapped
768/768, so every pattern byte really is referenced; the leftover was invisible
for the colour reason, not the reference reason.)

🟢 **THE RULE IS VALIDATED, NOT ASSUMED**: with it applied, the reference
reproduces a **filed figure exactly** — 170 on the r200 row — and every reading
below is stable across 25 s and 45 s capture windows.

| row | filed | **today** |
|---|---|---|
| `CIRCLE(128,352),200,15,1.1,2.04` | ref 170 / zb **181** | ref 170 / zb **170** ✅ healed |
| `CIRCLE(128,96),700,15,0,1.57,.137` | ref 127 / zb 126 | **ref 18 / zb 127** |
| `CIRCLE(128,96),400,15,-1.57,0` | ref 97 / zb 97 | **ref 125 / zb 97** |
| `CIRCLE(128,96),95,15,0,1.5707963` | ref 135 / zb 134 | **ref 103 / zb 135** |

The first row is a clean heal: zerobas moved 181 → 170 and now matches.

🔴 **ON THE OTHER THREE, BOTH SIDES DIFFER FROM THE FILING — AND ZEROBAS READS
THE VALUE FILED FOR THE *REFERENCE* EVERY TIME** (127, 97, 135 against filed ref
127, 97, 135). Two readings fit: the rows moved, or the filed figures used a
different visibility rule than mine. **The r200 row argues for the first**, since
my reference matched its filed value exactly — but **one validating case is not
enough to reinterpret three**, and saying so is the verdict. The divergences are
real and measured today; their relationship to the filing is **not settled**.

## 2r. Tranche 20 — three counting rules, three answers, and knowing when to stop

The VG-8020's SCREEN 2 pattern plane holds **4923 leftover bits that `CLS` does
not clear** — and a colour-0 `LINE …,BF` fill does not clear them either. Every
counting rule is then wrong in a different direction:

| rule | failure | `r400` reference reads |
|---|---|---|
| raw bits | counts invisible bits (fg 0 is transparent) | **4955** |
| visible (fg ≠ 0) | drawing **recolours** a row, making leftovers in it visible | **125** |
| baseline-subtracted | a drawn pixel landing **on** a leftover bit is subtracted away | **32** |

🎯 **AN EXACT WHOLE-PLANE COUNT OF A FIGURE IS NOT AVAILABLE ON THIS MACHINE BY
ANY OF THEM**, and each rule looked correct until the next one contradicted it.

🟢 **WHICH IS EXACTLY WHY THE `r200` ROW IS THE ONE TO TRUST**: it is the only row
that **agrees under two independent rules** — visible-only and baseline-subtracted
both give **ref 170 / zb 170** — and 170 is the filed reference value.
**A reading that survives a change of rule is a reading.** The other three *move
with the rule* (r400's reference: 125 vs 32), so they are artefacts of the
instrument rather than measurements of the machine, and are recorded **NOT
MEASURABLE** rather than reported as divergences.

⚠️ **AND THAT IS THE END OF BUILDING THIS INSTRUMENT.** Three tranches went into
it; the remaining graphics items need the project's **own** apparatus
(`probes/basic/basic_probe_graphics.py`, which compares per-cell VRAM *segments*
rather than whole-plane counts). Discovering why that apparatus is shaped the way
it is has been worth the three tranches — continuing to rebuild it would not be.

## 2s. Tranche 21 — back to the open items

| item | verdict |
|---|---|
| `ems_typecheck`'s two `pop de` (2 B carve) | **LIVE, exact** |
| `run_gates.py` still calls a contended unit REAL | **LIVE, confirmed** |
| the `unit-test` flake is open and uncaused | **diagnostic shipped; the flake is unfalsifiable** |

The carve item is exact down to its aside: `ems_typecheck:` is followed by
exactly two `pop de` and `jp els_tc_common`, **and** its remark that *"the same
2 B sit in `ems_err_pop2`/`ems_err_pop1` next door"* is true — four `pop de` in
the region.

The classifier item is confirmed by absence: `run_gates.py` has **no load
awareness of any kind** — no `getloadavg`, no `uptime`, only a `--nice` flag —
and the verdict line is unchanged at `'FLAKE (green on retry)' if rc == 0 else
'REAL (still red)'`. The diagnostic half really did ship; the classifier half is
untouched, exactly as filed.

🎯 **AND ONE ITEM CANNOT BE MEASURED BY ANYONE, EVER.** The `unit-test` flake's
subject is a **past event whose evidence was discarded** — `capture_output=True`
held pasmo's message and `CalledProcessError.__str__` does not print it. The
diagnostic that would have named it is now installed, so the *next* one will
name itself, but no re-run recovers this one. **An open item whose subject
cannot be measured is a WAIT, not a task**, and it should be restated as *"the
diagnostic is armed; close this when a flake next fires and is named"*.

## 2t. Tranche 22 — a class that closed itself while nobody re-read it

| item | verdict |
|---|---|
| the `Missing operand` class: 3 rows still diverge | **STALE — the last surviving row healed too** |
| `clone_scout` prices label-blocks | **LIVE, exact** |
| `DEF FN` has NO knives | **STALE — nine knives exist** |
| `DEF FN`'s knife roster is EIGHT | **stale figure — it is nine** |

🎯 **THE `Missing operand` ITEM CLOSED ITSELF IN THREE STAGES AND NOBODY NOTICED
UNTIL THE THIRD.** It already carried an in-place re-measurement (D-MISSOP3)
retiring two of its three rows and reframing `KEY1,` as *`KEY n,"str"` is
unimplemented*, leaving `MID$(A$,2)=` as *"the ONE row of the three that survives
as filed"*. Measured today: **`MID$(A$,2)=` reads ERR 24 on vg8020 and on
zerobas** — filed as zb 2 / refs 24. Healed, consistent with D-MIDOP's `MID$()=`
fix. ⚠️ cf3300 produced no reading in that quick fixture, so the final row rests
on **one reference**.

🎯 **AND TWO ITEMS TURN OUT TO BE ONE CAUSE.** `clone_scout`'s span model is
exactly as filed — *"groups of label-blocks … only structurally identical
label-blocks"* — and that is **the same blind spot** that made the 4 B dup-span
item unreachable in tranche 7. Both dup-span tools share it. Two entries on the
list, one defect underneath.

The DEF FN pair shows the two ways a filed item goes stale: one claim is now
**false** (knives exist), the other's **point stands and its number doesn't** — a
roster is still not a verdict, but it is nine, not eight.

## 2u. Tranche 23 — three live, and one rule that never crossed the corridor

| item | verdict |
|---|---|
| bare `RUN` inside a running program re-enters nested | **LIVE, exact** |
| the bare-`jp raise_error` carve family | **LIVE**, 29 sites measured |
| `castail-acceptance` voids on a zerobas-side control failure | **LIVE, exact** |

🟢 **ONE OF THESE CANNOT ROT UNNOTICED, AND IT IS THE ONE ANNOTATED AT THE
SITE.** `dr_stored:` is still `jp run_prog`, and the comment directly beneath it
says *"⚠️ STILL THE ONE ARM D-RUNTAIL DID NOT CONVERT, and D-RUNLINE deliberately
left…"*. The next reader of that routine sees the residual whether or not they
ever open `TODO.md` — which is more than can be said for the 30 divergences §1.2
found buried in `- [x]` blocks.

🎯 **AND THE CURE FOR THE THIRD IS ALREADY SHIPPED, TWENTY FILES AWAY.**
`basic_probe_castail.py` gates its controls with `for lab in CONTROLS: for s in
sides:` — every side, zerobas included — so a control failing on **zb** voids the
run, exactly as filed. It contains **zero** occurrences of the split-by-side
rule. `basic_probe_namspc.py:1036` carries that rule verbatim: *"ONLY A REFERENCE
CAN SAY THE APPARATUS IS BROKEN."*

**One probe has the rule, the other does not, and nothing carries it across** —
the same shape as tranche 8, where a rule I had encoded in one checker that
morning did not reach the next one I wrote that afternoon. A rule that lives in a
comment travels no further than the file it is in.

## 2v. Tranche 24 — two items the code concedes, and one I would not score

| item | verdict |
|---|---|
| a data-only span still confers fallthrough | **LIVE, exact** |
| the `tools/` seed arm is an intersection | **LIVE — the gate concedes it** |
| a predecessor walk stops at `ENDIF` | **partly addressed — not scored** |

🎯 **BOTH LIVE VERDICTS COME FROM THE GATE'S OWN COMMENTS.** `check_dead_code.py`
gates its fallthrough edge on `_last_code(...)` not being a terminator, and fix (7)
skips a prologue that emits nothing — with the comment stating the exemption's
limit outright: *"⚠️ Only a PROLOGUE is skipped, never any other empty span"*. A
data-only span emits bytes, its last code line is a `db`, and a `db` is not a
terminator. And the seed arm's header says *"⚠️ Fix (5) still matters — for
`tools/`, which still seeds."* **Two residuals confirmed by the code admitting
them**, which is the cheapest evidence available and the most durable.

⚠️ **AND ONE I DECLINED TO SCORE.** `dupspan_indep.py` does decode the predecessor
span and has an explicit *"predecessor … does not decode → UNKNOWN"* path — the
safe handling the item asks for. But I could only establish that **a safe path
exists**, not that **this input takes it**. Those are different claims and only
the second answers the item. Scoring it closed on the strength of the first is
precisely the move that put the stale entries on this list to begin with.

## 2w. Tranche 25 — absence as a measurement, and a subject I could not identify

| item | verdict |
|---|---|
| two `DEF FN` formals of one call can alias, no row separates it | **LIVE — confirmed by absence** |
| the generic error-layer seam | **LIVE — the source names the kept sites** |
| an unnamed outcome reads as no outcome | **not scored** |

🎯 **ABSENCE IS THE RIGHT MEASUREMENT FOR THE FIRST ONE.** The item's claim is
that **no row separates the case** — so finding no such row in
`basic_probe_deffn.py` is not a weak form of evidence, it *is* the evidence.
Elsewhere in this sweep absence has been the weakest signal (tranche 8's symbol
screen); here it is the strongest, and the difference is whether the item's claim
is about presence or about a gap.

The error-layer seam is confirmed with the sites documenting themselves:
`graphics.asm:748` still carries `jp z,ep_syntax`, and the comments around it
record D-PAINT4 removing one such site while **deliberately keeping this one**.

⚠️ **AND ONE ITEM I COULD NOT IDENTIFY THE SUBJECT OF.** `face()` exists in two
probes and `UNTRAPPED` naming in two others — **four candidates**, and the item
names none of them (it cites a spec section instead). Picking one and scoring
against it would be scoring a **different subject**, so it is deferred to a read
of the spec rather than guessed. 🎯 *Which artefact an item is about* is itself a
thing that can go unrecorded, and a citation to a spec section is not a citation
to a file.

## 2x. Tranche 26 — the deferred item, read instead of guessed

Tranche 25 refused to score the *"unnamed outcome"* item because `face()` exists
in two probes and `UNTRAPPED` naming in two others, and the item named none of
them. Reading `docs/spec-basic-clrtrap.md`:150-156 identifies the subject in one
line: **`scratchpad/circmiss_sib2.py`**.

**Verdict: LIVE structurally.** The `UNTRAPPED` branch shipped — and the probe's
own comment narrates the item verbatim:

> `<NO OUTPUT>` ON ALL THREE MACHINES for one reason only: *"Division by zero"*
> was [missing] … That is the SAME failure the UNTRAPPED branch was added to fix,
> one message along.

The cure is an **alternation of 16 named messages — a closed list** — so message
17 still reads as nothing. The residual is exactly as filed, and the fix's own
shape is what keeps it open.

⚠️ **THE SEVERITY IS UNQUANTIFIED AND I COULD NOT QUANTIFY IT.** *16 of N* has no
N here: the main build yields 14 message strings and the rest live in the
sub-ROM's `errmsg` tenant, so a quick count of MSX1's full message set was not
available. The item is confirmed **live**; how much of the message space it
leaves blind is **not measured**.

🎯 **AND THE DEFERRAL WAS WORTH ONE TRANCHE.** Guessing among four probes would
have had a 1-in-4 chance of scoring the right subject, and a wrong guess would
have produced a confident verdict about a file the item was not about.

## 2y. Tranche 27 — three live, and one of them is a limit rather than a defect

| item | verdict |
|---|---|
| `CSAVE`/`CLOAD` take a literal filename only | **LIVE, exact** |
| the `do_files` op-selector guard is pinned by nothing | **LIVE — by absence** |
| KEY/STRIG/SPRITE/STOP not run against the D-TRAPSVC rows | **LIVE — a stated limit** |

`do_csave` does `cp '"'` / `jp nz,load_error` under the comment *"must be a
quoted name"*, then `tape_parse_name`, and calls `str_eval` **zero** times — so no
expression is accepted, exactly the divergence filed while every other filename
verb moved to the expression path.

Nothing in `probes/` or `scratchpad/` executes `FILES INPUT$(n,#ch)`, so the
clobber guard is unwitnessed exactly as filed. (Its push/pop **balance** is still
pinned by every `FILES` row; only the clobber protection is blind — the item was
precise about which half.)

🎯 **AND THE THIRD IS NOT A DEFECT TO FIX.** `trapsvc_probe.py` has no `ON KEY`,
`ON STRIG`, `ON SPRITE` or `ON STOP` row, and says why at line 26: *"ON INTERVAL
is the instrument because it is the ONLY self-firing MSX1 trap"*. The item
**already concedes** the other four rest on a code argument. So re-running does
not overturn it — it confirms **the limit is still exactly where it was put**.

That distinction matters for what this sweep hands back: *stated limits* and
*unfixed defects* both sit as `- [ ]` on the list and read identically, but only
one of them is work.

## 2z. Tranche 28 — a number that neither confirms nor refutes the filed one

The `file:LINE` citation item was filed as *"only 31% were still correct"*.
Walking every one of them in every committed doc:

| | |
|---|---|
| `file:LINE` citations in committed docs | **1990** |
| target file does not resolve | 66 |
| line number **past the end** of the cited file | **24** |
| line exists | 1900 — **95%** |

🔴 **95% IS AN UPPER BOUND ON CORRECTNESS, NOT A CORRECTNESS RATE.** *"The line
exists"* and *"the line still says what the doc claims"* are different properties,
and only the second is what the filed **31%** measured — by reading. **My walk
cannot read; it can only prove a citation wrong, never right.** The two numbers
measure different things and neither refutes the other, which is the honest
result and not a hedge.

🎯 **BUT IT PRODUCES SOMETHING THE FILING DID NOT: A MECHANICALLY DECIDABLE
SUBSET.** **90 citations are provably broken** — 66 unresolvable, 24 past EOF
(`disk/disk.asm:742` where the file has **62** lines; `PROVENANCE.md:3591` where
it has **29**). Nothing checks them. That subset is a gate's worth of work
tomorrow, where the semantic majority is not.

⚠️ Some of the 66 may be basename-only forms my resolver failed on rather than
genuinely absent files.

### The family this belongs to

🎯 **THREE TRANCHES HAVE NOW FOUND THE SAME CLASS ON THREE SURFACES.** This
project cites many kinds of thing and gates exactly one:

* `scratchpad/` paths in committed docs — **gated** (`check_citation_paths.py`, shipped this morning)
* `probes/` paths — **ungated** (tranche 9 found a dangling one)
* `file:LINE` anchors — **ungated**, 90 provably broken

One rule, three surfaces, one gate. The morning's gate was scoped to the surface
that had just bitten; the sweep is what shows the surface had siblings.

## 2aa. Tranche 29 — gates that annotate what they cannot judge

| item | verdict |
|---|---|
| `kwsweep` prints rows no runner can parse | **LIVE — a declared exception inside the gate** |
| `s.fldarymix` is a row no knife can redden | **LIVE, exact — the probe records its own provenance** |

`check_report_shape.py` walks every probe and names this one at line 29: the
kwsweep case is handled *"out loud (`basic_probe_kwsweep.py`, spec §2.4) — never
silently skipped"*. And `basic_probe_fldary.py`:34 says *"🎯 `s.fldary2` AND
`s.fldarymix` EXIST BECAUSE A KNIFE WAS DRAFTED FIRST"* — the row was written to
satisfy a knife that then could not redden it, and the file says so.

🎯 **THIS IS THE FOURTH SIGHTING OF ONE PATTERN, AND IT EXPLAINS THE SWEEP'S OWN
ECONOMICS.** Four gates annotate the cases they cannot judge:

* `injector-check`'s `EXEMPT` table, each entry stating its class (tranche 14)
* `check_report_shape`'s named kwsweep exception (here)
* `check_dead_code`'s *"⚠️ Only a PROLOGUE is skipped, never any other empty span"* (tranche 24)
* `check_dead_code`'s *"⚠️ Fix (5) still matters — for `tools/`, which still seeds"* (tranche 24)

**The residual and its record live in the same file**, which is why so many items
here are confirmable by reading the gate rather than running anything — and why
these particular residuals have **not** rotted, unlike the 30 divergences §1.2
found buried in `- [x]` blocks, which had no such home.

## 2ab. Tranche 30 — halfway, and a duplication problem gets its denominator

**88 of 176 verdicted — the halfway mark.**

| item | verdict |
|---|---|
| `ex_mid_stmt`'s resolve abort is shadowed (3 B) | **LIVE, exact** |
| no knife runner shares a way to scope a cut | **LIVE — 30 runners, 0 sharing** |
| `a.spr` is blind to a cut stopping the sprite size | **LIVE, exact** |

`str-engine.asm`:988 still carries `call tgt_parse` / `jp nz,fp_runtime_error` —
the 3 B unchanged. And `a.spr` is `("a.spr", "t", "SCREEN 1,3")`: it scores the
`SCREEN` statement's own outcome and reads back **nothing** about the resulting
sprite size, so a cut that stops the size being applied leaves it green.

🎯 **THE MIDDLE ITEM GAINS THE THING IT WAS FILED WITHOUT: A COUNT.** *"No shared
way to scope a cut"* is a nicety at two runners and a duplication problem at
**thirty** — which is what there are, with **zero** sharing such a helper. The
filed sentence and the measured one say the same thing and mean different things.

That is the third time this sweep has attached a denominator to an item that had
none (29 bare `jp raise_error` sites, 333 `equ` aliases, 30 knife runners), and
each time the number is what turns a note into a priority.

## 2ac. Tranche 31 — an item true as written and misleading as read

**`GRPACX`: LIVE for the gate it names — and the store is pinned by a different
one.** The 360 rows are `graphics-acceptance`, which only *mentions* `GRPACX` in
comments. But `basic_probe_lineerr.py`:42 **reads it back**:
`X = PEEK(&HFCB7)+256*PEEK(&HFCB8)` — a live readout of the very address `K-GR4`
diverts.

🎯 **THE ITEM IS TRUE AS WRITTEN AND MISLEADING AS READ.** *"Nothing pins the
store"* is what a reader takes away; what was measured is *"nothing in **these**
360 rows"*. A knife aimed at that store may well redden a **lineerr** row — a
different gate, a different battery unit, and a place nobody scoring `K-GR4`
would look. ⚠️ Whether it actually does redden is untested here; that needs the
knife run.

**And two I declined to score:**

* *Phase Q3's control shares its subject's statement* — the closest pairing found
  (`("ie_off", "VDP(1)=VDP(1)AND223")` against control `"A=0"`) does **not** share
  the statement, which would make the item stale. But **I could not confirm that
  pairing is Phase Q3**, and scoring an item stale against a site I have not
  established is its subject is precisely the tranche-25 mistake.
* *Two `fat-error` gaps* — the three `*-alive` landmarks exist. The item's claim
  is about **knives**, and finding the **rows** says nothing about them.

🎯 Both refusals share a shape worth naming: **locating something with the item's
vocabulary is not the same as locating the item's subject.** Three tranches have
now turned on that distinction.

## 2ad. Tranche 32 — the deferral paid, and it would have been a wrong verdict

Both of tranche 31's refusals resolved by reading the source the items cite.

**`fat-error` gaps — LIVE.** The probe's knife roster is exactly three: `K-FE1`
cuts `tnt_name_stamp`'s write-sector (NAME), `K-FE2` undoes D-DKNAME's
disposition (NAME), `K-FE3` zeroes `build/disk.rom` (dead subject, nothing
scored). **None** separates `bload-alive`/`open-alive`/`append-alive` from the
shared `fat_io_getbyte` layer.

**Phase Q3 — LIVE, exact.** `docs/gate-blindness-sweep.md`:250 says it outright:

> Q3's control exists to prove the emulator is alive when the subject case
> freezes TIME — but its **restore line** is `VDP(1)=VDP(1)OR32`, **the very
> statement the subject uses**. A cut to the VDP grammar takes the control down
> with the subject.

🔴 **AND LAST TRANCHE I NEARLY SCORED THIS ITEM STALE.** I had found
`cases = [("ie_off", …), ("control", "A=0")]` — where the control's **case**
genuinely does *not* share the subject's statement — and that reads as a fix. The
sharing is in the **restore line, one line further down**. Scoring on the first
plausible site would have produced a **confident wrong verdict**, and the only
thing that prevented it was refusing to score a subject I had not established.

🎯 **THAT IS THE ARGUMENT FOR THE REFUSALS, MADE CONCRETE.** Three tranches have
now declined to score something on vocabulary alone; this is the first one where
the answer came back **opposite** to what the plausible site suggested. The
refusals are not caution for its own sake — one in three of them was about to be
wrong.

## 2ae. Tranche 33 — "not swept" turns out to mean two different things

| item | verdict |
|---|---|
| `pat_8_empty` cannot see an 8-byte sprite base shift | **LIVE, exact** |
| the three scale states are not swept through `X` substrings | **LIVE — but narrower than it reads** |
| nine acceptance rows still need a refusal cut | **LIVE — shape proven, cuts unwritten** |

`pat_8_empty` is `SPRITE$(3)=STRING$(8,170):SPRITE$(3)=""` — it writes eight
bytes then blanks them, so its final state is eight zeros and an 8-byte base
shift moves zeros onto zeros. The row is blind by geometry, exactly as filed.

🎯 **AND THE MIDDLE ITEM IS SMALLER THAN ITS WORDING.** *"Not swept through `X`
substrings"* could mean *no such rows exist* or *rows exist but do not cross the
dimension*. It is the second: `xsub` (`DRAW"A0S4XA$;D5"`), `xnest` and
`x_nosemi` are all there — and **every one pins the scale at `S4`**. Two of the
three scale states are simply never combined with an `X` substring. **The fixture
is already built and only the scale axis is missing**, which is a far smaller job
than the item implies.

That distinction has now shown up twice in three tranches (`GRPACX` was *"true as
written, misleading as read"*), and both times the correction made the work
**smaller**, not larger. A list re-read without measurement tends to inflate.

## 2af. Tranche 34 — the carve scout: conclusions stand, every number moved

The item opens *"Read this BEFORE opening any slice that needs main page-1
bytes"* — so its figures are load-bearing for exactly the decision the
screen-editor question turns on.

| | filed 2026-08-24 | **today** |
|---|---|---|
| Route A spans walked | 1440 | 1445 |
| byte-identical groups | 27 | **26** |
| nominal | 190 B | **163 B** |
| **measured SAFE NET** | **4 B** | **8 B** |
| Route B free (sub p0) | 2563 B | **2464 B** |

🎯 **ROUTE A IS TWICE AS OPEN AS FILED** — 8 B safe net, not 4 B — **while its
nominal figure fell**. The two move in opposite directions: carves since have
eaten the easy groups, while the safe/unsafe classification shifted in the other
direction. Route B's free space fell by 99 B, consistent with D-PAINTVRAM landing
there.

🟢 **AND THE STRUCTURAL CONCLUSIONS ARE UNTOUCHED.** *A verb that can PRINT or
RAISE reaches the BIOS transitively* (`pchar → CHPUT`, `raise_error → BREAKX`)
and a page-0 tenant runs with that region switched out — five candidates at
177–762 B all refused for those two paths. **That is an argument about
reachability, not a number**, and re-running cannot touch it.

That split is the useful shape: *this item's reasoning survived a month and every
one of its figures did not*. Both halves sit in the same block, and only one of
them rots.

## 2ag. Tranche 35 — a residual that is not just open but growing

**Instance: verified closed.** The rows the item says were added are present —
`o.errfend13` and `o.errfend18` in `basic_probe_deffn.py`, both with an `ON ERROR`
handler and an `X;E` readout, exactly as described.

**Class: open, and the denominator has moved.**

| | filed 2026-08-23 | **today** |
|---|---|---|
| `penderr_set` call sites | **21** | **22** |
| of which raise on the spot | 1 | 1 |

🔴 **A NEW SITE WAS ADDED SINCE THE ITEM WAS FILED.** The class of guards
witnessable only by a deferred error is not merely open — it is **expanding while
unwatched**. The item's own point is that *the ERR code a row expects carries no
information about whether that row can witness an ordering-sensitive guard*, so
each new site inherits the blindness silently and **nothing counts them**.

🎯 **EVERY OTHER STALE FIGURE IN THIS SWEEP SHRANK OR HELD** — 403 B of carve
supply became 8 B safe, 122 `/tmp` literals became 104, three divergences healed.
**This is the first one that grew.** A list that is only ever re-read cannot tell
those two directions apart; a list that is re-run can, and the growing one is the
one that matters.

## 2ah. Tranche 36 — an item that said "not enumerated", enumerated

Last tranche found the first residual whose denominator had **grown**, so this
one went looking for other countable claims. Only three pending items carry one —
and the most interesting says outright *"Not enumerated; not known to be
affected."*

| | |
|---|---|
| probe `.py` files | **201** |
| import `omsx_repl` (reach the shared injector + both oracles) | **72** |
| **build their own Tcl and do not** | **59** |

Of the 59: **43 under `probes/disk/`** and `basic_probe_printusing.py` — exactly
what the item names — **plus fifteen further `probes/basic/` scripts it does
not** (`graphics_floor`, `subrom_inttest`, `key_trap`, `strig_trap`, `usr`,
`cas_verify`, `cas_leader_budget`, `cas_verbs`, …).

🔴 **THE ITEM UNDERSTATES ITS OWN SCOPE.** Nearly half the probes that do either
thing bypass the shared injector — and D-LATCH already promoted this from a
coverage item to a **correctness** one, because a local copy of the pre-D-LATCH
`__key` still carries the race the shared injector no longer has, with no oracle
that would notice.

⚠️ **HEURISTIC COUNT**, and labelled as one: *builds its own Tcl* is detected as
(mentions `build_tcl`/`debug write`/`set tcl`) **and** (does not import
`omsx_repl`). Some of the 59 may not inject keystrokes at all. It is an upper
bound on the exposed set — and a genuine lower bound on the item's scope, **which
was previously zero**.

🎯 *"Not enumerated"* is the most actionable phrase on a list, because enumerating
is cheap and the number is what decides whether anyone cares.

## 2ai. Tranche 37 — a live item whose own citation has rotted

Applying the heuristic: **7 of the 41 pending open items declare their own scope
unknown** (*"unmeasured"*, *"unpriced"*, *"not enumerated"*, *"not measured"*).
Two are countable; both were taken.

**Type-code namespaces — LIVE.** `elsize_from_type` still exists and is still
deletable in principle. Call sites: **6** today against the item's *"~7"*.

🔴 **AND THE ITEM CITES `sub/arrays.asm:943`. THE ROUTINE IS AT `:1037`** — a
drift of **94 lines**. That is a live instance of tranche 28's class (90 provably
broken `file:LINE` anchors, nothing checking them) sitting **inside a pending item
on the same list**.

🎯 **AND IT IS THE INSTRUCTIVE KIND**: the anchor still points at a line that
*exists*, so tranche 28's walk counted it under *"line exists — 95%"*. **This is
what that 95% is hiding.** The upper bound was correctly labelled an upper bound;
here is one of the cases that separates it from the real rate.

**The `NO-ORACLE` bucket — partly answered.** `SAME-DELTA` **is** implemented
(`basic_probe_sysvarsweep.py`:802). But the item's claim is narrower — that the
verdict is applied *only* in the re-homing table while the 3199-byte census still
classifies absolutely — and establishing that needs a read of which path the
census takes, not a grep for the string. **The question it asks (how much of the
311 B is a pointer) remains unanswered**, and its own ⚠️ explains why: a byte-wise
delta pass needs a rule for what counts as a pointer *pair*, since naive per-byte
deltas agree by luck on the high byte.

## 2aj. Tranche 38 — the semantic measurement, on a subset small enough to make it

Tranche 28 could only ask *"does the cited line exist"* (95%) and said so; the
filed claim was *"only 31% were still correct"*, a **semantic** rate. Tranche 37
found a live item citing a 94-line drift that the structural walk had counted as
fine. So: the semantic check, on the 28 citations inside **pending items** —
small enough to decide, because each item names the symbols its citation is about.

| | |
|---|---|
| citations checked | **28** |
| a named symbol within ±4 lines of the cited line | **9** |
| **drifted** — symbol defined elsewhere in the same file | **10** |
| decidable rate | **9 of 19 = 47%** |

Drift magnitudes:

| cited | for | actually at | drift |
|---|---|---|---|
| `basic/vars.asm:1061` | `clear_vars` | `:1047` | 14 |
| `basic/cload.asm:580` | `err_verify` | `:664` | 84 |
| `basic/interp.asm:574` | `skip_spaces` | `:712` | 138 |
| `basic/cload.asm:840` | `dpl_nf` | `:1113` | **273** |

🔴 **THE FILED 31% AND THIS 47% ARE THE SAME KIND OF NUMBER. MY 95% IS NOT.**
Structural and semantic differ by roughly a factor of two — exactly what the
upper-bound label was warning about, now with a figure attached instead of a
caveat. **The item's spirit is confirmed**, and tranche 28's tension resolves in
the item's favour.

⚠️ **HEURISTIC, and it matters per-row**: a citation may legitimately point at a
**call site** rather than a definition. *Drift* here means *the named symbol is
not near the cited line but is defined elsewhere* — suggestive in aggregate, not
proof on any single row.

🎯 **AND THE SUBSET IS WHY IT WAS DECIDABLE AT ALL.** 1990 citations repo-wide
cannot be checked semantically without reading; 28 inside items that name their
own symbols can. **Narrowing the denominator is what turned an unmeasurable claim
into a measured one** — the opposite move from §1.2, where widening it was.

## 2ak. Tranche 39 — my own heuristic, caught false-positiving

| item | verdict |
|---|---|
| `CLEAR` breaks `TRAPSTK`'s GSP construction | **LIVE as filed** |
| `GFX_OP=1` marshalling aliased to the work area | **LIVE for `PSET`/`PRESET`** |
| K-FA5's falsifiability premise is stale | **LIVE — its own spec says so** |

🔴 **AND THE FIRST ONE FALSIFIES PART OF TRANCHE 38.** That measurement flagged
this item's citation — `basic/vars.asm:1061` — as **drifted**, because
`clear_vars` is defined 14 lines earlier at `:1047`. **The citation is exactly
right**: `:1061` is the `ld (GSP),hl` the item is *about*. This is the
*call-site-versus-definition* false positive I attached as a caveat to that
measurement, **caught firing on a real row**.

🎯 So the citation rate is **bracketed, not pinned**: 95% (structural, an
over-estimate) and 47% (semantic, now demonstrably an **under**-estimate). The
filed 31% sits below both. Naming the direction of each error is the most that
can be said without reading all 1990 by hand — and saying that is better than
picking the number that sounds most decisive.

**And one item is narrower than it reads, again.** `graphics.asm`:22 confirms
`GXPOS`/`GYPOS` still move on every `PSET`/`PRESET` — but `:106-111` records that
D-GIRDOM **already moved `POINT` off them** (*"marshal through POINT'S OWN cells,
NOT GXPOS/GYPOS"*). The decision the item says *"nothing re-examines"* **has** been
re-examined for one verb and left for the other two.

## 3. What the apparatus cost, said out loud

* 🔴 **THE FIRST RUN INHERITED EVERY PREVIOUS CASE'S SCREEN.** `reset=("NEW",)`
  does not clear, so the `[...]` span reader returned earlier cases' values —
  T008 "read" a `9` that `PAINT` had printed two cases before. **An accumulating
  screen reads as a plausible value.** Fixed by resetting with `CLS`.
* 🔴 **`WAIT 1,0` HUNG BOTH REFERENCES AND VOIDED EVERY CASE AFTER IT.** `WAIT`
  blocks on a port condition. In a batch that is not one lost row: T123 came back
  empty on both references for that reason alone, reading as *"the references
  printed nothing"* rather than *"the machine is still inside the previous
  case"*. **A blocking statement may not share a batch.** `WAIT` is therefore
  still UNMEASURED.
* ⚠️ **T131 NEEDED ITS OWN BOOT AND A 25 s STEP** — the references flood the
  whole screen, which does not finish inside a batch `step`. In tranche 1 it
  read as "no output on either reference", the `<NO OUTPUT>`-means-two-things
  trap.
* ⚠️ **`cf3300` RETURNED NO SPAN ON ANY T131 ROW, CONTROL INCLUDED** — an
  apparatus gap, not a finding. **T131 rests on ONE reference.**
* 🟢 **T131's SECOND CONTROL IS LOAD-BEARING**: `POINT` *above* the wall reads
  `9` on both sides, so zb's `PAINT` does fill — it just does not cross. Without
  it, zb's `4` could have meant "PAINT did nothing at all".

## 4. Audit — the sweep cannot pretend to be finished

```
subject ids            : 146
verdicts supplied      : 11
subject with NO verdict: 135
verdicts for NON-subject: 0
```

Re-run with `python3 tools/todo_inventory.py --audit scratchpad/sweep_verdicts.json`.
