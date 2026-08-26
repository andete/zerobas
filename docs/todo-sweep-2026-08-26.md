# TODO sweep — 2026-08-26 (D-TODOSWEEP), tranche 1

**Subject:** every open item in [`TODO.md`](../TODO.md), plus every closed block
carrying a residual marker. **Rule, set by the user: re-run everything, inherit
no claim** — an item is put to a machine even when it is recent and even when a
past sweep already blessed it.

🔴 **THIS IS TRANCHE 10 OF N, AND THE SUBJECT SET WAS WRONG. It is 176, not 146** (§1.2). 34 carry a verdict; **142** do not. The
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
