# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## 🔴 STATE AS OF 2026-09-21 — READ THIS BEFORE THE FIRING PROMPT

⚠️ **THE 09-16 BLOCK BELOW IS SUPERSEDED IN ITS HEADLINE AND STILL GOOD IN ITS
LESSONS.** Read this section for WHERE the work is; read that one for HOW it
goes wrong. In particular its *"the autonomous queue is EMPTY except TIER 4"* is
no longer true — Joost's 09-20 ruling on the disk-code eviction (*"I think the
answer to Two is obvious: we do as the reference does"*) opened a TIER 2 arc that
is still running.

### The live arc: `disk/docs/spec-diskcode-eviction.md` §6.2, steps 9–14

Under his governing frame — *"a clear understanding of how the communication
between main rom and disk rom fully works"* — the FAT engine and the loader's
sector loop move OUT of main and INTO `disk.rom`, reached through the claimed
hook cell `$FE5D`.

**Shipped:** step 9 LOAD (`e458032b`) · step 11 MERGE + ASCII LOAD (`35eeafb7`) ·
step 12 SAVE (`3b8e1b57`) · and **step 13 COMPLETE**, all four slices —
`174bf887` D-NAMESTAMP, `407298e0` D-KILLLOCAL, `c9238e5a` D-COPYLOCAL,
`285b80e9` D-FILESLOCAL.

⚠️ **THOSE SHAS ARE READ BACK FROM `git log`, AND THE REASON THAT IS WORTH A
LINE:** the D-FILESLOCAL sha was first written into a hand-off as `c9238e5a`'s
neighbour from memory rather than from the log, and it was wrong. A sha is
exactly the kind of fact that looks checkable and is not, once it is in prose.

**Step 13 is NOT a 1895 B relocation** (that filing was wrong, §6.6av): the ported
disk verbs each made a three-ROM round trip — `hk_*` called BACK into main just
so main could marshal on to `sub.rom`'s `dirverb_tenant`, whose body ran FAT
primitives `disk.rom` has had since steps 9/11/12. Each slice deletes one.

🔴 **THE TIERED AUTONOMOUS QUEUE IS EMPTY AT *EVERY* TIER (re-checked 2026-09-21,
D-RETRYSUBJ) — AND "BELOW TIER 4" WAS THE WRONG BOUND.** Scanning every OPEN
item for its LAST work-bucket marker leaves **three** whose last marker is
`🤖 AUTONOMOUS`: the RAM-usage comparison (TIER 2 — **Joost's**, *"not
something for now"*), `refcache-check` (APPARATUS), and `ex_stop`'s missing edge
seed (TIER 5). **TIER 4 speed is NOT autonomous**: its LAST marker is
`🙋 NEEDS-JOOST` on the charter question (*does faithful include speed?*), and
the item says plainly that optimising is only worth starting once that is
answered — §5's autonomous half is already refuted.
🛑 **AND AS OF 2026-09-22 THE AUTONOMOUS QUEUE IS EXHAUSTED — THE LOOP WAS
STOPPED, NOT ABANDONED.** `ex_stop`'s edge-seed item closed (D-STOPSEED,
`348a6dba`). Re-running the marker scan leaves TWO open items whose last marker
is `🤖 AUTONOMOUS`, and **neither is actionable**:
* the **RAM-usage comparison** (TIER 2) — Joost's, *"This is not something for
  now"*;
* **`refcache-check`** (APPARATUS) — its actionable half shipped as D-RETRYSUBJ
  (`2c46d1e1`); the ROOT CAUSE is waiting on a **recurrence** of a red that has
  not happened again, so there is nothing to do until it does.

🙋 **WHAT THE NEXT SESSION SHOULD DO IS ASK JOOST**, not pick something. The
rulings that would re-open real work, in the order they unblock the most:
1. **Does faithful include SPEED?** (the TIER 4 charter question) — this gates
   the interpreter's 2.5–3.8× band, `PAINT` and `PUT`, i.e. all remaining
   TIERED work. The item says optimising is only worth starting once it is
   answered.
2. **Step 10 `OPEN`** — the PAINT span-stack RAM lever.
3. **The same-address question** — D-COPYLOCAL answered it only in miniature
   (cells with ONE consumer); `SECTOR_BUF`/`FSECTOR_BUF` and `WBUF`/`FWBUF` have
   two consumers each and 416 B of accidental overlap.
4. **The TIER 1 keyword tier re-ask** — the unattributed list is now 0, which
   the item itself named as the moment to re-ask.
5. The **RAM-usage comparison**, whenever he wants it.

⚠️ **RESTARTING THE LOOP WITHOUT ONE OF THOSE ANSWERS WILL SPIN.** The honest
move was to stop and say so.
⚠️ **THE RENAME RESIDUAL IS DECLINED, MEASURED** (§6.6ba): `dirverb_tenant` /
`dirverb_op` / `SUBROM_IDX_DIRVERB` are ~96 refs across **12 code + 11 doc**
files, and the docs are the eviction's HISTORICAL RECORD — renaming them would
falsify it, so no mechanical sed, and no gate would catch a
consistent-but-wrong rename. Document, do not half-change.
🔴 **CHECK THE CHECKBOX BEFORE THE BODY.** A `DSKF` blocker reading *"8 B free
on 2026-09-13"* looked like a prime stale blocker; the item is `- [x]` DONE
(D-DSKFDRV) and that text is its original, kept for the record. Several closed
items carry *"(the original item, for the record:)"* blocks that read exactly
like live work.

📜 **SUPERSEDED, kept for its own record — the earlier reading:**
`tools/tier_table.py --keywords` reports the unattributed keyword list at **0**,
so the TIER 1 keyword-completeness item has no concrete target left and its own
text says the tier re-ask goes to Joost at exactly this point. TIER 2's two
autonomous items are step 13 (closed) and the RAM-usage comparison (Joost's,
*"not something for now"*). What is left autonomous is TIER 4 speed (`PAINT`,
`PUT`, the interpreter band) and the APPARATUS/BUDGET buckets.
⚠️ **`VARPTR` LOOKS LIKE A TIER 1 TARGET AND IS NOT:** its second authored
form is `file-channel` (`VARPTR(#n)`), which is Joost's filed stride ruling.
Re-verifying that blocker is what stopped a wasted tick.

📜 **HISTORICAL, kept because the lesson outlived the slice — `FILES`/`LFILES`
and SCOUT IT BEFORE PRICING IT:** This arc has now
had to correct the same over-confident sentence twice — *"`KILL`, `COPY` and
`FILES` are the same shape"* was measured on `KILL` alone and was false for
`COPY`, and then `COPY`'s own scout over-priced it by 17 B because it priced a
cell's home before grepping its consumers. `tnt_files` emits through
`CHPUT`/`LPTOUT` and spells `FSECTOR_BUF` in CODE at two sites
(`sub/dirverb.asm:196`, `:301`), which in `disk.rom` is MAIN's buffer at `$E5C0`.
After it, `dirverb_tenant` holds `DSKO$`/`DSKI$` only — both called from MAIN, so
it does not empty.

🙋 **JOOST'S, FILED, DO NOT START:** the RAM-usage comparison against the
reference (`12cbc6fe` — *"not something for now"*, plus *"I have a hunch
reference is very economical with RAM"*) · the same-address question (`9d4f94b2`)
· step 10 `OPEN` (the PAINT span-stack RAM lever) · the *"Gap (small)"* entry in
`expansion-protocol.md` §6 · the merged remote branch `wip/saveport`.
⚠️ §6.6q's hazard is NOT retired in general: `PAINT` then `LOAD` is still
ungated and `GFX_PSTK` still sits in disk's `SECTOR_BUF` window.

### What this arc keeps re-learning

* **`DISKOP_STATUS` IS A SHARED CHANNEL — WRITE IT ONCE, LAST.** Main's FAT
  primitives marshal their own disposition through the same cell, so a handler
  that pre-sets it and lets later paths overwrite reads whatever they left.
  Measured: `NAME "A.BAS" AS "B.BAS"` at an EMPTY DRIVE answered `Syntax error`
  instead of `Disk offline`. A moved body should RETURN its status in `A`.
* **`FAT_DBUF`/`FAT_MBUF`, NEVER `FSECTOR_BUF`/`FWBUF`, in anything shared.**
  `disk.rom` binds them to `$E2A0`/`$E560`; main binds them to `$E5C0`/`$E7C0`.
  The wrong spelling ASSEMBLES CLEAN and reads a buffer nobody filled. It is a
  gate now (`make shared-body-check` rule 2) but only over `*-body.inc`.
* **A LOCAL `fat_find`'s RESULT MUST SURVIVE A CALL-BACK, OR THERE MUST BE NO
  CALL-BACK IN THE WINDOW.** `KILL` had one name so the question never arose;
  `NAME` sidesteps it by ORDER; `COPY` answers it with a main sysvar that has one
  consumer. §6.6av — the general question — is still open.
* **A ROM CHANGE INVALIDATES THE KNIFE PIN.** `tier_table.py` REFUSES until
  `scratchpad/kwknife.py --all` AND `--allfn` are re-run (~15 min, and they must
  not overlap another emulator probe). A comment-only `.inc` edit leaves the
  hashes identical and needs neither.

## 📦 STATE AS OF 2026-09-16 — superseded above, kept for its lessons

⚠️ **THE CRON PROMPT IS STALE AND HAS BEEN ALL SESSION.** It still says *"NEXT
VERBS: NAME, then COPY, then FILES/LFILES"* and *"DO NOT rely on CF across
CALSLT — it was never measured"*. All three verbs shipped; CF is measured
two-sided. **This file is the durable half — believe it over the prompt.**

### The autonomous queue is EMPTY except TIER 4

Every tiered 🤖 item below TIER 4 is closed. What is left:
* **TIER 4 speed** — the interpreter's 2.5–3.8× band, `PAINT` 1.9–2.0×, `PUT`.
  Large, open-ended, and the only tiered autonomous work remaining.
* 🙋 **THREE RULINGS WAIT ON JOOST, and none should be taken alone:**
  1. **`VARPTR(#n)`** — the references stride **265** (MSX's FCB: 256-byte record
     + 9 header), ours would be **306** (`FCH_STATESZ` 50 + `FCH_RECMAX` 256).
     The ADDRESS cannot agree between machines, so a row must read a DELTA — and
     ours cannot match. Implement anyway and document the divergence, or leave it
     deferred and score `VARPTR` 1/2 by design?
     ([`varptrn_probe.py`](varptrn_probe.py))
  2. **The channel-verb CLUSTER MOVE** — `$FE5D` is recovered (it is the cell
     BOTH `OPEN` and `MERGE` arrive through), but `ex_open` has **40** page-1
     call sites with **18 inside loops** against ~3 and none for the FAT-light
     four. The channel HELPERS must travel WITH the bodies; that is a slice shape
     phase 3 has not done. ([`xslot_chanprice.py`](xslot_chanprice.py))
  3. **`LOAD"CAS:"`** — bug-for-bug fidelity costs a working feature and the
     faithful behaviour is a HANG no row can carry.

### What the disk-verb carve bought, and it is the session's through-line

`make basic-reloc` on 2026-09-16: **main page 1 61 B free, low region 36 B,
`disk.rom` 8490 B** — from **3 B and 0 B**. Moving the FAT-light four into
`disk.rom` (`0f15a873` KILL · `b26857de` NAME · `3f6a6099` COPY · `e1bbf7e5`
FILES/LFILES) paid for **six** items that had been diagnosed, priced and parked
on bytes that did not exist:

| item | cost | what was actually wrong |
|---|---|---|
| `FIELD`/`LSET`/`RSET` gate | 20 B | genuinely blocked on bytes |
| `INPUT$` console form | 21 B | genuinely missing code |
| `SCREEN` key click | 9 B | *"no cell any row can read"* — **false** |
| `LOCATE` cursor switch | 10 B | a declined deviation whose premise was about the wrong side |
| `DSKF` drive range | 16 B | *"blocked on the same 8 bytes"* |
| `SWAP` type order | 10 B | *"priced at ten bytes, which had eight"* |

Plus `D-STOPEDGE`, which cost no bytes and turned out to be a hole in **shared
trap machinery** rather than in `STOP`.

📏 **`kwsweep` reads `SUPPORTED=362` — zero MISSING, zero scored DIVERGENT** (only
`csrlin`, WEAK-excluded by its own row note). **150 of 163** statements at TIER 1.
No keyword is unreachable by the knife. **Recount all of it; never quote it.**

### 🔴 What this session kept re-learning

* **RE-VERIFY THE BLOCKER BEFORE READING THE ITEM.** Fifteen re-verified, **fourteen
  stale**. Two were blocked by a SENTENCE, not by the machine. The one that
  survived (`VARPTR(#n)`) had NO stated reason at all until it was measured.
* **AN AGREEING ROW BESIDE EVERY ERROR ROW.** `DSKF`'s first cut made EVERY call
  answer `Bad drive name` — and the TIER 3 row PASSED, because a refusal is what
  it asserts. Only the happy-path row dissented.
* **A BATCHED SUITE'S RESET MUST RESTORE EVERY GLOBAL ITS CASES MOVE**, or a row
  measures its predecessors. Making `CSRSW` live broke three suites at once, and
  `missing-acceptance` reported the damage as *"good news about the tree"*.
* **A FIX THAT CHANGES NOTHING IS A QUESTION ABOUT THE MECHANISM.** D-STOPEDGE's
  first patch moved no reading because `STOP OFF` had already destroyed the bit
  it tested.
* **CORRECT CODE IN THE WRONG PLACE IN A CONTROL-FLOW GRAPH** is invisible in a
  diff: a block dropped into a fallthrough gap (`sea_click`), a shared RAM
  channel written too early (`DISKOP_STATUS`). Both caught by suites, neither by
  the probe written for the feature.
* **AN ITEM'S MARKER CAN BE SUPERSEDED INSIDE ITS OWN BLOCK** — take the LAST,
  not the first. Taking the first reported 🙋 work as autonomous AND hid a TIER 1
  item.
* **A MESSAGE CAN ASSERT A PROPERTY IT NEVER TESTED** and send you after useless
  work (`tier_table`'s nested-checkbox warning, D-KWBACKTICK).

## 🔴 CURRENT ORDER (2026-09-15, Joost): FINISH THE DISK KEYWORDS, THEN THE TODO

He ruled the mechanism proven once phase 2 shipped: *"the mechanism is proven I
guess ... continue with the disk keywords and afterwards back to the generic
todo"*.

The arc is [`spec-diskbasic-hook-rearchitecture.md`](../disk/docs/spec-diskbasic-hook-rearchitecture.md).
Shipped, do not redo: `f3188146` the spec · `7ad4f4ef` 0a cross-ROM dead code ·
`0d18d3d1` 0b the inter-slot call priced · `8a79c2b5` 0c htimi_guard ·
`cee9ce9b` 1 the ABI · `0f15a873` 2 KILL's body moved.

**The pattern phase 2 established, to copy verb by verb.** Main keeps the cursor
hand-off and the status decode; the body becomes an `hk_*` in `disk/kernel.asm`;
`hook_tab` points the hook at it; `chan_gate`'s presence test and `diskslot_test`
VANISH rather than move — that is where most of the saving is. The cursor crosses
in `FN_RESUME`, because `chan_gate` needs HL for the hook cell and clobbers DE.
Call-back targets go in `REQUIRED_DISK_CALLBACK`, 7 B a site, 0.156 ms a call.
**Measured ABI: HL/DE/BC/A cross BOTH ways intact**; IX/IY are the ABI's own; a
callee may RAISE and never return, so do nothing after a call-back that an abort
would skip. **CF crosses too** — measured two-sided in the NAME slice, a callee
that SETS carry comes back set and one that CLEARS it comes back clear, so a
disposition may be read from it (the earlier "never measured, do not rely on it"
is superseded).
🔴 **BUT `DISKOP_STATUS` IS A SHARED CHANNEL, NOT THE HANDLER'S.** Main's FAT
primitives are `ld a,DISKOP_SEL_* / jr fatprim_bounce` shims that marshal their
own disposition through that same cell, so a handler may only write it **once,
LAST**. Pre-setting it and letting later paths overwrite is what made `NAME ...
AS ...` answer `Syntax error` at an empty drive — and it passed the happy-path
row, because success rewrites the cell on the way out.
🔴 **AND `disk.rom` HAS ITS OWN FAT** (`disk/fat.asm`, for MSX-DOS). Importing
main's collides; NAME imports them aliased (`main_fat_mount=fat_mount`) because
main's `fat_find` writes the entry location the dirverb tenant reads. Which FAT a
disk verb should use is phase 4's question.

**Shipped so far in phase 3**: `0f15a873` KILL · `b26857de` NAME · `3f6a6099`
COPY (both halves, and it freed LOW-REGION bytes) · FILES/LFILES in flight.
⚠️ **CHECK EVERY VERB'S ROWS BY NAME.** `diskbasic-acceptance` says 34/34 and has
**no COPY row and no LFILES row**. COPY's gate is `copy-acceptance` (8 rows, with
byte-for-byte content checks); LFILES's is `lptverb-acceptance` (46 rows, and it
names the sides it cannot measure).

⚠️ **A ROM CHANGE COSTS THREE RE-RUNS**, and until they happen `selftest-check`
and `tiers-md-check` are red as ONE fact reported twice: `kwknife.py --all` AND
`--allfn`, then full `make kwsweep`, then `make tiers-md`.
⚠️ **A NEW SECTION HEADER NEEDS AN INLINE CITATION** or the clean-room audit
fails the battery in WARM-UP (rc=2) before a single unit runs.

## Where things stand (rewritten 2026-09-15)

🏗️ **JOOST RULED 2026-09-15 — READ THIS BEFORE PICKING ANYTHING UP. Five
decisions, and they set the order of the next slices. Do not re-ask.**

0. 🛑 **PARKED THE SAME DAY IT WAS APPROVED — READ BOTH RULINGS.** Joost
   approved rung 3 on 2026-09-15 (*"D-VERBPART — option 3 is priced ->
   approved"*) against **256 B**, then ruled *"Park it — carve somewhere else"*
   once D-VERBCLASS measured the realisable relief at **36 B** (a 258 B span is
   STAY 155 / TENANT 67 / MOVE 36). ⛔ **NO BYTES MOVE; RUNGS 3, 3b AND 4 DO NOT
   RE-OPEN WITHOUT A NEW RULING.** The carve must come from elsewhere — Route D
   (`jp`→`jr`, which RENEWS on every insertion) first, then the instruction-pair
   ngram sweep, then ruling 5's sub-ROM carve for tape. What needs the bytes: the
   three diskless gates (`FIELD $FE2B`, `LSET $FE21`, `RSET $FE26`), 16-24 B
   against main page 1's 3 B free (2026-09-15).
   *(The superseded approval, for the record:)* the relocation was unblocked at
   its cheapest rung: `COPY`, `FILES`/`LFILES`, `KILL`, `NAME` move to `disk.rom`, **256 B** of
   main page 1. ⚠️ **RUNG 3 AND NOTHING ELSE** — 3b (1231 B), 4 (2315 B),
   `field.asm` and the 975 B channel machinery are NOT approved by it.
   🔴 **AND THE FIRST STEP IS NOT A MOVE**: the `$4004` consumer slot-walk does
   not exist (`disk/init.asm:18` is `dw 0`, an unknown statement falls to
   `stmt_error`), so that INTERPRETER change lands on its own slice first. Then the
   verbs; then `kwknife.py --all` AND `--allfn`, because a relocation moves code
   between REGIONS and the one-run re-stamp is not enough. Spec:
   [`disk/docs/spec-diskbasic-relocation-seam.md`](../disk/docs/spec-diskbasic-relocation-seam.md).
   **This is ruling 2's prerequisite carve** — the four code forms land after it.
1. **`SAVE"x",A` — SPEND THE 3 B.** The ASCII save must END the run.
2. **The four code forms (LOCATE cursor switch, SCREEN key click, `VARPTR(#n)`,
   `INPUT$` console form) — CARVE FIRST, THEN ALL FOUR TOGETHER.** A carve slice
   is the prerequisite; do not dribble them into the leftover bytes.
   🟢 **THE CARVE IS NAMED AND APPROVED: ruling 0's option 3, 256 B.**
3. ✅ **DONE (D-KWRUNFILE): `PROG3.BAS` = `10 PRINT"[3h]"`, appended last.**
   `RUN` 3/3; `LOAD` 1/2 (its plain form cannot get a row here). The disk group's
   `step` went 5.0 → 8.0 in the same slice — a case slower than `step` has its
   successor typed into a still-running program, and `open_c` blanked twice before
   the fix moved from the row to the GROUP.
   *(original ruling: ADD A SECOND `.BAS`, LEAVE `PROG.BAS` ALONE.)* It must
   PRINT a marker; that is what makes `RUN"<file>"` and `LOAD` observable. Nothing
   existing changes its bytes, so every suite mounting `disk/test720.dsk` keeps
   reading what it read.
4. **The unreachable forms — BUILD A RIG, not an exemption.** `KEY`'s display
   forms, `PAD`'s switch, `STICK`/`STRIG`'s joystick halves keep counting against
   us until a rig drives openMSX's HOST-side joystick and reads the key line where
   it actually sits.
5. 📍 **PLACEMENT: DISK CODE BELONGS IN THE DISK ROM as much as possible; TAPE
   CODE IS A GOOD CANDIDATE FOR THE SUB ROM.** This is the carve's FIRST lever,
   ahead of any instruction-level shaving: main page 1 has **8 B** free and the
   low region **0**, against **~8820 B in `disk.rom`** (32 runs, largest usable
   hole 3182 B) and 505 B in sub page 0. `ascii_save` is disk code sitting in the
   main image and is a migration candidate in its own right.

Recount everything — never quote a number from this file. `make tiers-md` then
read `docs/tier-status.md`; the headline is in its **STATEMENT — 163** paragraph.

* 🎯 **THE WORK IS TIER 1 OVER THE STATEMENT DENOMINATOR.** TWO denominators:
  TOKEN **159** (`basic/kwtable.inc`, guarded by selftest S20, never to be
  weakened) and STATEMENT **163** = 144 keywords with a bare statement form plus
  the 19 composite and channel statements. As of 2026-09-15 the second reads
  **140** — it was 121 at the start of that night's run.
* 🎚️ **TIER 1 = CONNECTED + every AUTHORED FORM covered by an agreeing row +
  no open TIER **1** item** (tier n blocks tier n ONLY — Joost confirmed
  2026-09-14, `blocks_tier1()`, selftest S34). N is authored per statement in
  `tools/kwforms.py` **from the REFERENCE's syntax, never from our handler**. No
  entry ⇒ UNRATED, never satisfied. **A FORM IS A DISTINCT BEHAVIOUR, NOT A
  DISTINCT INPUT.**
* 🔧 **SEVEN RIGS NOW, AND THE LAST TWO ARE THE NEW ONES.** `NEEDS-DISK:`,
  `NEEDS-PRINTER:`, `NEEDS-LOG:`, `NEEDS-TAPE:`, `NEEDS-BLANKTAPE:`, and then
  **`NEEDS-HOLD:<row>,<mask>`** (holds one KEY-MATRIX bit down for a case's whole
  RUN — row 8 bit 0 is SPACE, bits 4/5/6/7 are left/up/down/right, row 6 $20/$40
  are F1/F2) and **`NEEDS-PLUG:<port>,<device>`** (openMSX `plug joyport<port>
  <device>`). Both take an ARGUMENT, which is part of the capture group key.
  `strig_hold` is the matrix rig's CONTROL and is in the sweep for good: if it
  ever reads `[1w 0 ]` the matrix is not being reached and nothing that depends on
  it may be believed.
* ⛔ **WHAT IS LEFT, AND WHY — and not one of them is "nobody looked".** Recount
  the number; the KINDS are stable. **Blocked on CODE, priced, Joost's call:**
  `SAVE` (the ASCII-save tail ends the run on the reference, +3 B against 8 B free
  in main page 1), `LOCATE` (cursor switch), `SCREEN` (key click), `VARPTR` (`#n`),
  `INPUT$` (console form). **Blocked on the INSTRUMENT, measured:** `KEY` (the
  function-key line's layout differs — LINLEN 37 vs 39), `PAD` (no host button),
  `STICK`/`STRIG` (openMSX drives a joystick from the HOST, which the emulated key
  matrix cannot reach), `RUN"file"`/`LOAD` (the loaded program REPLACES ours so
  nothing can print afterwards — `PROG.BAS` POKEs a landmark instead of PRINTING
  one, and changing the fixture touches every suite that mounts it), `AUTO` (the
  increment needs a multi-line direct interaction this harness has no shape for),
  `CONT` (two-phase delivery). **A bar the tree is genuinely far from:** `DRAW`
  1/10, `PLAY` 0/11, both authored from the tree's own specs. **No happy path
  reachable here:** `CALL`, `MAX` — reservedness only.
* 🔴 **`DELETE` AND `RENUM` ARE MEASURED SHUT FOR THIS INSTRUMENT** and should
  not be re-opened with rows: `DELETE 20` inside a running program stops it
  cleanly on BOTH machines (so every range form has the same observable) and
  `RENUM 100` answers `Undefined line 100 in 20` on BOTH (its only reading is an
  error). `scratchpad/mdr_probe.py`.
* 📏 **THE MEASURED CADENCE**, so a fresh session can plan: a full battery is
  **~910 s** and `make gates-fast` **~70 s**; `make kwsweep` alone is ~120 s.
  One battery per slice, and batch several statements into each.

## Twelve blockers re-verified, twelve stale

Not one survived contact with a measurement. `INKEY$` was the last and the most
convincing: filed as needing a HARNESS change to time a keystroke against
D-LATCH/D-LATCH2 — all true, and beside the point, because **a key does not have
to be TYPED to be waiting.** The BIOS type-ahead buffer is ordinary work area and
BASIC can POKE it.

➡️ **A blocker is written down at the moment of most confusion about a problem,
and then never re-read against what was learned afterwards.** Re-verifying has
been cheaper than the work it was hiding every single time.

## What the tape arc cost, and the rule it earned

Four slices went into the WAVEFORM — duty cycle, tone periods, leader lengths,
three refuted hypotheses — when the actual defect was **seven missing `$00`
bytes** at the end of the data block. The oracle had been sitting in
`cas_encode.build_cas_basic` the whole time: our own encoder already encoded the
right answer and no probe had ever diffed the WRITER against it.

➡️ **WHEN A CONSUMER HANGS, DIFF THE BYTES BEFORE THEORISING ABOUT TIMING.** A
format is finite and checkable; timing is an open-ended space that will always
absorb one more hypothesis. Both causes produce the identical symptom, and I
ranked them by which was more interesting rather than which was cheaper to check.

🔴 **AND TWO OF MY OWN REFUTATIONS WERE RETRACTED IN THE SAME ARC**: "leader
length is dead" had been measured on a DIFFERENT build (the lopsided writer,
where the leader was not the binding constraint), and the between-tone-outlier
histogram never predicted the outcome — the cleanest recording ever produced read
the WORST. **A refutation is only as general as the build it was measured on.**

## The next slice — keep taking TIER 1 over the 163

THE LOOP: handler first (if any) → rows + `tools/kwforms.py` in ONE edit pass →
`make kwsweep ONLY=a,b,c` → **READ EACH READING ONE AT A TIME** → knife
(`--fn` for functions) → `make repack-machine` → `check_todo_citations.py --fix`
→ `make kwsweep && make tiers-md` → `make gates-fast` → stage → ONE full battery
plus the five excluded targets → ONE commit naming every statement.

🚩 **THE FIVE APPARATUS FAULTS THIS ARC KEEPS REPEATING**, every one of which
produced a row that agreed while proving nothing:
1. **A ROW CAN AGREE ON AN ERROR.** `fnkw` scored SUPPORTED on `Illegal direct`
   from both machines because `DEF FN` is illegal in direct mode. Read the VALUE,
   not the verdict.
2. **A ROW CAN AGREE ON FURNITURE THAT DIFFERS.** The `KEY ON`/`OFF` rows read a
   fixed VRAM offset and scored SUPPORTED on a BLANK CELL, because the key line
   sits somewhere else on the reference (LINLEN 37 vs 39).
3. **A ROW CAN AGREE ON A CONSTANT.** `pdlkw` read 255 — the IDLE line of an
   EMPTY port — which a PDL answering 255 to everything passes. `motor` printed
   `[ok]`. Plug something in; mask to the bit that moves.
4. **INTERPRETER SPEED LEAKS IN.** The `ON KEY` rows came back `?noecho` on the
   REFERENCE only: it finishes ~3x sooner, so it collected far more function-key
   auto-repeats and scrolled the marker away. And a row that waits 120 frames for
   something that must NOT happen is still waiting when the capture is taken —
   30 frames, and count FRAMES (`TIME`) not iterations.
5. **THE KNIFE REPORTING BLIND IS A FINDING, NOT A NUISANCE.** `DATA`'s cut moved
   nothing because the `DATA` sat after the `END` and was never executed. Putting
   it on the execution path turned up a SHIPPED DEFECT.

⚠️ **Rows with NUMBERED LINE TARGETS are fragile under `as_stored`'s greedy
≤34-char packing — VERIFY WITH `omsx_repl.as_stored` FIRST**, pad with long
ASSIGNMENTS, never `REM` (it swallows the rest of its line). **And an `IF` must END
ITS LINE**: a FALSE condition skips the REST OF THE LINE, not just the `THEN`.

## Five ways a kwsweep row can pass while seeing NOTHING

Every one of these SHIPPED a green row before being caught, and mode 1 nearly
shipped again this session as `CSAVE`:

1. **A readback that never moves** — `KEY` via CRTCNT read 24 with `KEY OFF` and
   24 without. `scratchpad/kwdrain_discrim.py`.
2. **A predicate true of ZERO** — an absent keyword parses as an undefined array
   and reads 0, so `INP(&HA8)>=0` passed exactly like the real answer. The same
   trap hides in an ARGUMENT: `BASE(0)` and `DSKF(0)` are honestly 0.
3. **A crunch that names no keyword** — `tier_table`'s WORD regex keeps a
   trailing `$`, so `sprite$(0)=…` credited nothing while reporting SUPPORTED.
4. **An audit that re-implements the consumer's parser** — IMPORT
   `tier_table.kwtable_keywords()`; expect exactly ONE row crediting nothing.
5. **A row that leaves the machine in a MODE THAT EATS THE NEXT CASE** — `AUTO`
   scored itself correctly and took 21 unrelated rows down with it. After adding
   any row, read the WHOLE sweep summary, not just the new verdict.

🔴 **6. A ROW WHOSE READING IS AN ERROR CANNOT TELL A WORKING FEATURE FROM A
DIFFERENTLY-FAILING ONE.** Added 2026-09-13 from `PAD`, and it is general. Modes
1–5 are ways two machines agree about NOTHING; this is a way they agree about the
WRONG THING. `PRINT PAD(9)` is out of range, so a real `PAD` errors while an
absent one auto-dims an array and prints 0 — which discriminates TOKENISED from
NOT. Cut `PAD`'s dispatch and the word is still tokenised, the fallback still
errors, and the row sees no difference. **Prefer a VALUE reading over an ERROR
reading wherever the reference offers one**: a cut turns a number into an error,
which no error-reading row can see. ⚠️ And check the value is not 0 on both sides,
or you have merely traded this mode for mode 2 — `PAD(0..7)` reads 0 on both
machines even with openMSX's touchpad plugged, because an untouched pad correctly
reports nothing.


Plus: **a FIX silently un-attributes its own keyword** — attribution comes from
OPEN items, so leave a row behind when closing a defect.

## 🔴 AN EDIT SCRIPT NEVER SHARES A BACKGROUNDED COMMAND WITH A BATTERY

Learned 2026-09-13, and it cost two silent failures. Batteries are backgrounded
because they are slow; an edit script is foregrounded because **its output is the
only proof it worked**. Bundled together, the script's `AssertionError` scrolled
past under a green battery tail and TWO TODO.md filings were reported as landed
when neither had — the D-TIER0 ruling-and-lesson block and the D-KWKNIFE block.
The second was a cascade: its anchor was text the first would have created.

⚠️ **The anchor that failed was self-inflicted too**: that block had been
DE-INDENTED for the legend section and the later anchor still carried the item
indentation. An anchor copied from what you MEANT to write is not an anchor.

➡️ **Run the edit, READ its output, and only then start the battery.** After any
filing, `grep` the file for the text you think you added: the assert proves the
anchor matched, the grep proves the write landed. (This very rule needed two
attempts — its own first anchor matched TWICE, because the file embeds the whole
restart command and every heading appears in both halves.)


## 🔴 Re-verify every blocker before believing it

**TEN FOR TEN**, plus the two retractions above. The display verbs' "cannot take a
row", the multi-line words', the CF-3300 NO-ORACLE claim, the disk fixture,
`SCREEN`'s mode, `KEY`'s missing constant, `USR`'s "machine code to call",
`WAIT`'s port, and the printer log `LPOS`/`LPRINT`. Re-verifying has been cheaper
than the work it was hiding every single time.

⚠️ **A WAITER THAT MATCHES ITSELF**: `until ! pgrep -f run_gates.py; do sleep;
done` in the background NEVER EXITS — the waiter's own command line contains the
pattern. Use the background task's completion notification.

## Two staging traps

* **After any `basic/`, `sub/` or `tape/` change the build refreshes the patch
  pairs** — stage them WITH that commit; `patch-freshness-check` can only see the
  omission ONE COMMIT LATER, and it names the exact `make` target.
* **`check_todo_citations.py --fix` rewrites EVERY document citing a moved TODO
  block**, five files beyond TODO.md every time. It compares the WORKING TREE, so
  it is green before and after while a stale citation ships in HEAD.

## Open for Joost — do not pick up

* The `CONT` item (TIER 5): inside a program zerobas prints `Can't CONTINUE`
  where the reference prints `Can't CONTINUE in 10`. A DELIBERATE choice recorded
  at `basic/program.asm:1188`.
* Ranking the remaining apparatus blockers (AUTO's line-entry mode, keystroke
  injection, step (c)).

## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `ad7334af`. Recount everything — never quote a number
  from this file.
* 🟢 **EVERY TIER 1 THE DRAIN PRODUCED IS CLOSED** (`NEW` `FILES` `LFILES`
  `MERGE`, plus `LOAD` which only the MERGE sweep could have found), and **the
  whole kwsweep is clean: `DIVERGENT=0`.**
* 🟢 **THE LAST TIER 1 IS UNBLOCKED.** The "Keyword-completeness gaps" umbrella
  item was ⛔ on a fixture that had existed all along; it is now 🤖 AUTONOMOUS,
  its stale counts are replaced by the two COMMANDS that compute them, and its
  exit criterion is runnable: **DONE = the "no known gap" list is EMPTY.**

## What shipped this session

* **D-KWDISK** (`89f43985`) mount the test image on both sides · **D-KWRIG**
  (`0579b2f8`) the printer rig · **D-KWTAPE** (`59937b12`) a filed defect instead
  of a row · **D-DFEND** (`c0bd895e`) `FILES`+`LFILES` were ONE tail, −8 B sub
  page 1 · **D-MERGERET** (`631157c0`) `MERGE` *and* `LOAD`, +4 B main page 1 ·
  **D-KWUMB** (`b4177c61`) the umbrella item · **D-KWLOG** (`ca271f77`)
  `NEEDS-LOG:`, the third rig — a CAPTURE rather than a device — and `LLIST` ·
  **D-KWGET** (`a7dbb7d4`) `GET` (a random-file read, not a keyboard verb) and
  `CALL` (reservedness only, with the shortfall named) · **D-KWINP** (`c6215324`)
  `INPUT`'s FILE form and `RENUM` · **D-KWAUTO** (`21481b1a`) `AUTO`, placed LAST
  with a kwsweep-local tail rule · **the D-KWTAPE retraction** (`1a777438`).
* 🔴 **TWICE NOW A WORD WAS IN THE LIST FOR ITS NAME**: `GET` (a random-file read)
  and `INPUT` (`INPUT #n` reads a file), each filed next to a word with a real
  blocker and inheriting it by adjacency. Check the shape before the blocker.

## Where things stand — JOOST RULED, and the oracle work found a TIER 1

Joost answered the 🙋 item with **"make the 3 missing oracles"**. The first one
paid immediately and not as expected: building it exposed a TIER 1 defect and
retired the 🙋 blocker for `CLOAD` entirely.

* 🟢 **`CLOAD`'s oracle is DONE.** `omsx_repl.run_cases` takes `cassette=` (the
  `-cassetteplayer` seam every cas probe used and none could reach through the
  harness). The VG-8020 reads a clean-room `.cas` — the earlier "no oracle" was a
  FIXTURE that was itself the defect. A `NEEDS-TAPE:` kwsweep rig is now small.
* 🔴 **NEW TIER 1: a tape zerobas writes cannot be read by a real MSX.** Filed with
  the full matrix; `CSAVE`'s kwsweep row should wait for the fix, because the
  defect IS its subject.
* `INKEY$` is untouched — still the injector's timing, still the one to do last.

## The next slice — the tape-writer COMPENSATION, and it is well specified

**MECHANISM CONFIRMED**: the per-bit loop overhead lands inside the LAST
half-period of every bit.

| bit | VG-8020 | zerobas |
|---|---|---|
| `0` (one low-tone cycle) | `18 19` | `18` **`20`** |
| `1` (two high-tone cycles) | `9 9 9 9` | `9 9 9` **`11`** |

Inside a `1` bit the FIRST cycle is clean, so it is the BIT boundary, not
`cas_cycle` (a tight `djnz` pair, constant by construction). The stretch is ~2
samples ≈ 160 T-states ≈ 12 `djnz` iterations against `CAS_HHALF` = 50 — about a
quarter of a short half, enough to push `9` to `11`, above the midpoint between the
tones and unclassifiable by a threshold derived from the leader.

➡️ **THE FIX**: shorten the trailing low half of each bit by the per-bit overhead
so the total stays correct — a `cas_cycle_last` variant taking a reduced count,
with the leader loop keeping the uncompensated one (the leader measures clean).
⚠️ **Byte cost unmeasured** — the tape ROM is its own region; price it first.
⚠️ **FOUR HYPOTHESES ARE ALREADY DEAD** and are in the item: leader length (rebuilt
to the reference's own), inter-block silence (spliced), leading silence (spliced),
mount form. Do not re-run them.
🎯 **THE TEST IS DECISIVE AND WRITTEN**: `scratchpad/kwdrain_wavread.py` (the VG
reads a tape zerobas wrote, with a prompt witness) and
`scratchpad/kwdrain_wavhist.py`, which must come back CLEANLY BIMODAL — nothing
between the tones, which is what the reference produces.

## 🔴 Two staging traps, both paid for on 2026-09-12/13

* **After any `basic/` or `sub/` change the build refreshes
  `zerobas-main-eu.ips`/`.bps`** — stage them WITH that commit.
  `patch-freshness-check` can only see the omission ONE COMMIT LATER.
* **`check_todo_citations.py --fix` rewrites EVERY document that cites a moved
  TODO block**, not just TODO.md. `todo-citation-check` compares the WORKING TREE,
  so it is green before and after and a stale citation ships in HEAD with nothing
  red. Read `git status --short` as a LIST, not a glance.

## Five ways a kwsweep row can pass while seeing NOTHING

Every one of these SHIPPED a green row this session before being caught:

1. **A readback that never moves** — `KEY` via CRTCNT read 24 with `KEY OFF` and
   24 without, on both machines. `scratchpad/kwdrain_discrim.py`.
2. **A predicate true of ZERO** — an absent keyword parses as an undefined array
   and reads 0, so `INP(&HA8)>=0` passed as -1 exactly like the real answer. The
   same trap hides in an ARGUMENT: `BASE(0)` and `DSKF(0)` are honestly 0.
   `scratchpad/kwdrain_boolcheck.py`.
3. **A crunch that names no keyword** — `tier_table`'s WORD regex keeps a
   trailing `$`, so `sprite$(0)=…` credited nothing while reporting SUPPORTED.
4. **An audit that re-implements the consumer's parser** — my ad-hoc regex
   admitted `A` as a keyword and hid a real miss. IMPORT
   `tier_table.kwtable_keywords()`; expect exactly ONE row crediting nothing,
   `swapctl` stmt `a=1`, the intentional bare-assign control.
5. **A row that leaves the machine in a MODE THAT EATS THE NEXT CASE** — `AUTO`
   scored itself correctly and took 21 unrelated rows down with it. After adding
   any row, read the WHOLE sweep summary, not just the new verdict.

Plus: **a FIX silently un-attributes its own keyword**, because attribution comes
from OPEN items — leave a row behind when closing a defect.

## 🔴 Re-verify every blocker before believing it

**TEN FOR TEN this session.** The display verbs' "cannot take a kwsweep row", the
multi-line words' "cannot be expressed in one row", the CF-3300 NO-ORACLE claim,
the disk fixture, `SCREEN`'s mode ("SCREEN 1 is 32 columns" — nothing makes the
row STAY in the mode, and `SCRMOD` IS declared), `KEY`'s missing constant
(`KEY LIST` prints to the SCREEN and needs none), `USR`'s "machine code to call"
(one POKEd `$C9` is machine code), `WAIT`'s port (measure `INP`, then choose the
mask), and the printer log `LPOS`/`LPRINT` never needed (the head COLUMN reaches
the screen; only the printed TEXT needs the log). Re-verifying has been cheaper
than the work it was hiding every single time.

⚠️ **AND A SIXTH SILENT-FAILURE MODE, FOUND THE HARD WAY: A WAITER THAT MATCHES
ITSELF.** `until ! pgrep -f run_gates.py; do sleep; done` run in the background
NEVER EXITS — the waiter's own command line contains `run_gates.py`, so seven of
them sat waiting on each other while the battery they were watching had long
finished. Use the background task's own completion notification; do not poll with
a pattern that appears in the polling command.

## Open for Joost — do not pick up

* The `CONT` item (TIER 5): inside a program zerobas prints `Can't CONTINUE`
  where the reference prints `Can't CONTINUE in 10`. The cause is a DELIBERATE
  `print_msg`-instead-of-`raise_error` choice recorded at `basic/program.asm:1188`.
* Ranking the remaining apparatus blockers (printer log + its LSTOUT hang hazard,
  AUTO's line-entry mode, keystroke injection, step (c)).

## The command

Paste this into a fresh session. ⚠️ **It supersedes the 27-minute cron prompt,
which went stale within an hour of being armed** — a cron prompt is fixed at
creation and cannot learn, which is the whole reason this file exists.

    /loop continue autonomously on zerobas — 🔴 READ scratchpad/LOOP-RESTART.md FIRST and BELIEVE IT OVER THIS PROMPT; then the item's own block in TODO.md to its END. 📊 RE-VERIFY THE BLOCKER *BEFORE* READING THE ITEM — fifteen re-verified, FOURTEEN STALE, two of them blocked by a sentence rather than by the machine. ➡️ THE AUTONOMOUS QUEUE IS EMPTY BELOW TIER 4: the disk keywords are done as far as the pattern reaches, the six items the carve funded have shipped, and `kwsweep` reads SUPPORTED=362 with zero missing and zero scored divergences. What is left is TIER 4 speed (the 2.5–3.8× interpreter band, PAINT, PUT) and THREE RULINGS that are Joost's, not yours: VARPTR(#n)'s FCB stride (265 vs our 306), the channel-verb CLUSTER move (ex_open has 40 page-1 call sites, 18 in loops — the helpers must travel with the bodies), and LOAD"CAS:" (fidelity costs a working feature; the faithful behaviour is a hang no row can carry). DO NOT take any of the three alone. ⚠️ AN ITEM'S MARKER CAN BE SUPERSEDED INSIDE ITS OWN BLOCK — take the LAST, not the first; taking the first reports 🙋 work as autonomous AND hides TIER 1 items. ⚠️ CHECK ROWS BY NAME, NEVER A CONVERGED TOTAL — diskbasic-acceptance says 34/34 and has no COPY row and no LFILES row. ⚠️ KEEP AN AGREEING ROW BESIDE EVERY ERROR ROW: DSKF's first cut made every call answer `Bad drive name` and the TIER 3 row PASSED on it. ⚠️ A BATCHED SUITE'S RESET MUST RESTORE EVERY GLOBAL ITS CASES MOVE. ⚠️ A ROM CHANGE INVALIDATES THE KNIFE PIN: `kwknife.py --all` AND `--allfn`, then full `make kwsweep`, then `make tiers-md`, and the ORDER for docs is TODO edit -> check_todo_citations.py --fix -> tiers-md (the tier table cites TODO LINE NUMBERS). Standing rules: full `make gates` before each commit and never commit red; STAGE EVERYTHING BEFORE THE BATTERY AND WRITE NOTHING WHILE IT RUNS; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; re-run the five battery-excluded targets ONLY when the ROMs actually changed; WRITE EDIT SCRIPTS TO A FILE, anchor on TEXT, refuse on a missing or non-unique anchor, and ACCUMULATE PER FILE; READ the output of every edit script; never poll with a pattern that matches the polling command itself.
