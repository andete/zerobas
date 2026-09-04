<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-TRAPSVC — leaving a trap handler without its `RETURN`

Status: **✅ MEASURED, and the headline hypothesis is CONFIRMED AS BEHAVIOUR and
REFUTED AS A DEFECT.** 2026-08-23, on `b8a8137`. **No source file changed and no
ROM byte moved** (`7942cc20` / `34bb8554` / `031184d9` before, under two knives,
and after). One divergence found, priced, and DECLINED with numbers (§6).

The candidate [`deferblind-scout-2026-08-23.md`](deferblind-scout-2026-08-23.md)
§5 filed and refused to fold in, because its trigger is a different one.

---

## 1. The question, and why the source shape justified asking it

`TRAPSVC` (`basic/sysvars.inc`) is *"count of live SERVICING entries == depth of
the service stack"*. Reading `basic/traps.asm`:

* `check_traps` **increments** it on dispatch (`traps.asm:369`), after pushing a
  `[GSP-after-frame-push:2][idx:1]` record onto `TRAPSTK`;
* `trap_return_check` — reached **only** from `ex_return` — is the sole
  **decrementer** (`traps.asm:421`) **and** the sole writer of the entry's
  `ZTS_SERVICING -> ZTS_ON` auto-resume (`traps.asm:431`);
* `ct_find` fires an entry only when its state is **exactly `ZTS_ON`**.

So a handler left by any door other than `RETURN` should leave its entry
`SERVICING` for good — **a silently dead trap**, the class this project ranks
worst — and leave a service record that is never popped, with `TRAPSTK_MAX` = 6.

🔴 **BUT THIS IS A FAITHFULNESS QUESTION, NOT A BUG HUNT.** MSX BASIC's own
contract is *"a trap handler must end in `RETURN`"*, so both references were
expected to leak too. **The references define the want.**

`ON INTERVAL` is the instrument because it is the only **self-firing** MSX1 trap
— KEY / STRIG / SPRITE / STOP need a human at the machine. See §7 for why that
is a scope statement and not a claim about them.

---

## 2. The instrument

`scratchpad/trapsvc_probe.py`, the shape D-DEFERBLIND calibrated: whole
programs, **boot-per-case**, run on **both references and zerobas**, each
printing one fenced value; a row that printed nothing reads `<NO OUTPUT>` and is
scored **NOT MEASURED**, never as agreement. Frame windows are bounded by a
**JIFFY delta** (`$FC9E`, with the T5 probe's high-byte re-read guard), never by
an iteration count, so the same program means the same thing on three machines.

🎯 **EVERY ROW PRINTS TWO NUMBERS AND THE FIRST ONE IS A GUARD.** `B` = *the
trap fired at least once at all*; `C` = *it fired in the window AFTER the
handler was left*. A row reading `0` because the trap **died** and one reading
`0` because the trap **never armed** are different facts, and one number cannot
tell them apart. Every row below reads `B` = 1.

---

## 3. The measurement — 7 rows × 3 machines, `scratchpad/trapsvc_probe.out`

| row | what it asks | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `int.ctl` | handler RETURNs normally; does it fire in a second window? | `1 1` | `1 1` | **`1 1`** |
| `int.one` | …with **exactly one** fire in window 1 | `1 1` | `1 1` | **`1 1`** |
| `int.resume` | **THE SUBJECT** — a trapped error in the handler, left via `RESUME <line>`, so `RETURN` is never reached | `1 0` | `1 0` | **`1 0`** |
| `int.resnext` | **THE SEPARATOR** — same fault, `RESUME NEXT`, which lands *on* the `RETURN` | `1 1` | `1 1` | **`1 1`** |
| `int.goto` | the same abandonment with **no error anywhere**: a plain `GOTO` out of the handler | `1 0` | `1 0` | **`1 0`** |
| `int.six` | seven leak-and-re-arm cycles: `N` = cycles that fired, `E` = last ERR | `9 18` | `9 18` | **`6 18`** 🔴 |
| `gos.leak` | the GOSUB-depth separator, **no trap in it at all** | `12 0` | `12 0` | **`8 7`** 🔴 |

### 3.1 The answer

**YES — `RESUME <line>` out of a trap handler permanently disables that trap, on
all three machines, and zerobas is FAITHFUL.** The reference machines agree with
each other on every row and zerobas agrees with both on the five rows that ask
the headline question.

🎯 **`int.resnext` IS WHAT MAKES THAT A MECHANISM AND NOT A CORRELATION.** It is
the *same program* as `int.resume` — same trap, same period, same handler, same
fault, same windows — differing in **one keyword**, and it reads the opposite
answer on all three machines. The missed `RETURN` is the mechanism and nothing
else is.

🎯 **AND `int.goto` WIDENS IT OFF THE ERROR PATH.** No `ON ERROR`, no fault, no
`RESUME`: a plain `GOTO` out of the handler kills the trap identically. The rule
is *"the handler did not RETURN"*, not *"an error happened"* — which means the
filed candidate's name (**RESUME** out of a handler) was narrower than the class
it belongs to.

### 3.2 What ELSE would make these rows read this way

* `int.resume` reading `1 0` because the trap never armed — excluded by `B` = 1
  and by `int.ctl`/`int.one` reading `1 1` on the same shape.
* `int.resume` reading `1 0` because the **program** stopped rather than the
  trap — excluded because line 70 printed, which is downstream of the second
  window.
* Every green row reading green because the apparatus cannot see the subject —
  excluded by §5, which makes the same rows go red.

---

## 4. 🔴 The one divergence: zerobas caps at six abandoned dispatches

`int.six` re-arms the trap explicitly (`INTERVAL ON`) after each leak, so the
*entry* comes back — `set_state` takes `SERVICING -> ON` like any other
transition. What does **not** come back is `TRAPSVC`. After six such cycles it
sits at `TRAPSTK_MAX`, and the seventh dispatch takes `ct_svc_full`:

    ld      a,(TRAPSVC)         ; service-stack depth guard
    cp      TRAPSTK_MAX
    jr      nc,ct_svc_full      ; -> jp gosub_stk_over -> ERR 7

**and that arm leaves the entry `ON` + `PENDING` and `TRAPPEND` set** — only
`ct_none` clears `TRAPPEND`. So the ERR 7 is raised again at the *very next*
statement boundary, which falls inside the `ON ERROR` handler that is still
active, where it is **untrapped**. The measured screen (`scratchpad/trapsvc_six_zb.out`):

    Out of memory in 800

The references complete all nine cycles: `9 18`.

### 4.1 The number is what says which cap it is

zerobas has **two** candidate caps in this program — `TRAPSTK_MAX` = 6 and
`GOSUB_DEPTH` = 8 (each abandoned dispatch also leaks one GOSUB frame) — and
"ERR 7 / Out of memory" is the answer to both. `gos.leak` measures the second
one **on its own, with no trap in the program**: it caps at **8**. The subject
caps at **6**. 🎯 **A confounded row was separated by a row that contains none
of the subject**, not by reasoning about which limit "should" have fired.

`gos.leak`'s own divergence (`8 7` vs `12 0`) is the already-filed own-design
`GOSUB_DEPTH`, not a finding of this slice.

---

## 5. 🔴 …and none of that is worth anything until the shape can go red

`scratchpad/trapsvc_calib.py`. The **same seven rows**, zerobas only, under two
size-neutral cuts inside `trap_return_check` — the routine that owns both halves
of the re-enable. Both cut a **VALUE, not a call** (a deleted call fails
`make deadcode` and builds no ROM), and each build is preceded by `rm -rf build`
and asserted to move `basic-reloc.rom` + the merged image and **not** `sub.rom`.

| knife | the cut | moved | wanted |
|---|---|---|---|
| **K-TR1** | `or ZTS_ON` → `or ZTS_SERVICING` (the auto-resume value) | `int.ctl`, `int.one`, `int.resnext` | same → **EXACT** |
| **K-TR2** | `dec (hl)` → `nop` (the `TRAPSVC` decrement) | `int.ctl`, `int.resnext` | same → **EXACT** |

    baseline roms=7942cc20 / 34bb8554 / 031184d9
    K-TR1    roms=8a92bb32 / 34bb8554 / a8e8a729     (main moved, sub did not)
    K-TR2    roms=99e62e71 / 34bb8554 / 021778c8
    restored roms=7942cc20 / 34bb8554 / 031184d9
    2/2 knife rows EXACT

🎯 **`int.one` EXISTS ONLY TO SEPARATE THE TWO KNIVES, AND IT DID.** K-TR1 kills
the trap after **one** normal RETURN; K-TR2 only kills it once the
un-decremented count reaches 6. So `int.one` (period 60 in a 90-frame window —
exactly one fire) **must** move under K-TR1 and **must not** under K-TR2. It
moved `1 1 -> 1 0`, and stayed `1 1`. Without it the two knives would have moved
identical sets and the suite could not have told the re-enable from the count:
**one knife wearing two names**.

⚠️ **THE SETS WERE EXACT; ONE PREDICTED VALUE WAS NOT.** K-TR2's moved rows were
predicted to read `1 0` and read `<NO OUTPUT>` — because window 1 fires ~9 times,
so the un-decremented count reaches 6 *inside the run* and the program takes §4's
abort instead of finishing. Right row, right direction, wrong face; §4's
mechanism is what explains it, which is a small independent confirmation of §4.

---

## 6. 💰 The divergence, priced — and DECLINED

Main page 1 is ~2 B free. Three candidate fixes:

1. **Raise `TRAPSTK_MAX`.** RAM only, and `TRAPPEND` sits at `TRAPSTK_END`, so it
   moves. **Rejected on principle, not on price:** the leak is unbounded, so a
   bigger number is a different wrong answer, not a fix.
2. **Make `ct_svc_full` decline to fire instead of raising** (clear `PENDING` +
   `TRAPPEND`, return CF=0). Roughly the bytes it replaces. **Rejected:** it
   trades a loud wrong answer for a *silently dead trap*, which is the class
   this project ranks worst — the very thing §1 set out to look for.
3. **Pop the stale record when a `SERVICING` entry is explicitly re-armed.** The
   semantically right fix, and the only one that closes the class. `set_state`
   holds `HL -> entry` but **not** the index, so it must compare against
   `TRAPSTK`'s top record (`ztrap_entry` + a 16-bit compare + the guard),
   **~25–30 B of main page 1** — and it still handles only a top-of-stack
   record, so a *nested* leak escapes it.

⚠️ **AND THE OBVIOUS CHEAPER VERSION OF (3) IS WRONG.** "Pop the record whenever
the entry leaves `SERVICING`" breaks the documented case of a handler that
re-enables its own trap **inside** the handler and then RETURNs: the record is
what `trap_return_check` matches the RETURN against, so popping it early
recreates the leak it was meant to close.

**DECLINED today**: ~25–30 B against ~2 B free, no carve in hand, and partial.
Filed in `TODO.md` with this section as its detail.

---

## 7. ⚠️ What this does NOT establish

* **KEY / STRIG / SPRITE / STOP were not run.** They share `check_traps`,
  `ct_find`, `set_state` and `trap_return_check` **verbatim** — the trap index is
  a parameter and nothing on the abandonment path reads it except
  `ztrap_entry` — so the argument for not paying for four device-driven rows is
  a *code* argument, not a measurement. Stated here so it can be attacked.
* 🔴 **`CLEAR` IS AN UNMEASURED WEDGE UNDER THE SAME MECHANISM.** After a leak
  the abandoned GOSUB frame is still on the stack, so the only RETURN that can
  reach `record.gsp` is the one popping the trap's own frame — the match is
  sound *by construction*. **`clear_vars` resets `GSP` and does not call
  `trap_init`**, which breaks that construction: a later, unrelated `GOSUB` /
  `RETURN` pair can then land on the stale record's `gsp` and re-enable a trap
  the program believes is dead. The references have no `TRAPSTK` and would
  discard the frame, so a divergence is plausible. **Not measured** — a program
  that survives `CLEAR` cannot carry its flags in variables, so the row needs the
  T5 probe's POKE-based readout, not this one's. Filed.
* **`int.six`'s `E` column is uninformative on zerobas** (`18`, the fence printed
  at the top of the aborting cycle). `N` is the reading.

---

## 8. 🔴 The instrument fault this slice found in itself

The first `int.six` draft printed its fence **only at the end**, and zerobas
never reaches the end (§4). The readout then matched the **typed echo of that
unreached line** — `PRINT"[";N;E;"]"` echoes as `[";N;E;"]` — and tabulated
`";N;E;"` as a value beside `9 18`. It is [[apparatus-is-part-of-the-measurement]]'s
echo-anchored readout again, in a probe whose fence is *by construction* also
present in the program text.

Two fixes, both kept:

* `face()` now accepts a fenced match only if it is **digits, spaces, dots and
  minus signs**; anything else is the SOURCE, not the output, and reads
  `<NO OUTPUT>` → **NOT MEASURED**. A lie became an honest blank.
* `int.six` **reprints its fence at the top of every cycle**, so the cap is
  readable on a machine that aborts. That is what turned `<NO OUTPUT>` into the
  `6` that §4.1 is built on.

🎯 **AND THE HONEST BLANK ALONE WOULD HAVE LOST THE FINDING.** `<NO OUTPUT>` is
scored NOT MEASURED, so the six-event cap would have been a hole in the table,
not a 🔴 DIFF. **Making a readout honest is not the same as making it able to
measure**; this row needed both fixes, and only the second one produced a number.

---

## 9. What was run

`scratchpad/trapsvc_probe.py` (7 rows × 3 machines, boot-per-case) →
`scratchpad/trapsvc_probe.out`; `scratchpad/trapsvc_six.out` (the redesigned row,
3 machines); `scratchpad/trapsvc_screen.py` → `scratchpad/trapsvc_six_zb.out`
(the raw screen that read `Out of memory in 800`);
`scratchpad/trapsvc_calib.py` → `scratchpad/trapsvc_calib.out` (2 knives × 7
rows, 3 clean builds). Predictions written before the matrix:
`scratchpad/trapsvc_predictions.md`. Gates in §10.

---

## 9.1 Gates — all rc=0, from a clean build, ROMs byte-identical throughout

`basic-reloc`, `unit-test` **59/59**, `deadcode`, `wall-assertion-check`,
`redundant-load-check`, `rowshape-check`, `injector-check`, `preflight-check`,
`latch-check`, `diskdep-check`, `switch-build-check` **6/6**, `kwsweep`
(`SUPPORTED=30`, no `MISSING`), `deffn-selftest`, `interval-trap-acceptance`
**ALL PASS**. `7942cc20` / `34bb8554` / `031184d9` before and after.

⚠️ `kwsweep`'s `DIVERGENT=1` is `csrlin`, the documented probe artifact
(`TODO-done.md:1152 (T-A88F7F)`) — pre-existing, and it cannot be this slice's: no source file
changed and all three images are byte-identical to `b8a8137`.

**Walls, read from this run's `make basic-reloc` (2026-08-23, `b8a8137`), not
quoted from memory:** main page-1 free **2 B**, page-0 low region free **17 B**,
sub page-0 **2563 B**, sub page-1 **1624 B**. §6's ~25–30 B is measured against
the 2.

## 10. 🔴 D-TRAPDEPTH (2026-09-04) — the references leak too, and §6's principle is refuted

§6 declined the fix and ranked three options on a premise nobody had measured:
that the reference **reclaims** the abandoned dispatch, so zerobas's cap is a
leak the reference does not have. `scratchpad/trapdepth_probe.py` measures it.

### The reference leaks at the same rate we do

Recurse until the control stack overflows and report the depth reached. Two rows,
**byte-for-byte the same program** except that one has its `INTERVAL ON` removed,
so the trap never fires:

| | 20 abandoned dispatches | 0 dispatches | cost |
|---|---|---|---|
| VG-8020 | 4016 | 4040 | **24 frames** |
| CF-3300 | 3247 | 3271 | **24 frames** |

**≈1 frame per abandoned dispatch — the same as zerobas.** Nothing is reclaimed
on either reference. The plain depth is **4071 / 3302 / 8**, and the two
references differ from *each other* because the limit is free RAM, not a
constant.

### So the difference is CAPACITY, and §6's own principle inverts

* **Option 3 ("pop the stale record") is not what the reference does.** It would
  invent a mechanism the oracles do not have, to patch one symptom — and still
  leave zerobas at 8 against their ~4040. It also cannot make `int.six` pass:
  `TRAPSTK_MAX` is 6 and `GOSUB_DEPTH` is 8, so popping the record moves the cap
  to 8 and the row needs 9.
* **Option 1 ("raise the number") was rejected as *"a bigger number is a
  different wrong answer, not a fix"*.** Measured, the reference's leak is
  **also** unbounded and a bigger number is exactly what it has. The principle
  was sound in the abstract and false about this machine.

⚠️ **This is therefore not a trap defect.** It is the already-filed fixed-size
control-stack design (`GOSUB_DEPTH` = 8, `TRAPSTK_MAX` = 6) seen through a trap,
and it should be priced there — against a RAM-bounded stack, not a bigger array.

### ⚠️ Two faults in these rows, both caught by a counter I nearly left out

`F` counts actual handler entries. Without it:

1. `d.depth20`'s handler resumed **past** the loop tail, so it fired **once** and
   fell through to the recursion. The row would have read "nineteen more
   dispatches are free" — the exact conclusion the slice was testing for, arrived
   at because nothing happened.
2. An earlier `d.depth1` resumed to the **print** line and read `0 18` on all
   three sides. It agreed everywhere because the program ended before the
   measurement began.

Both are the same shape: **a row that agrees, or reads flat, because its subject
never ran.** `d.ctl20` — same text, trap unarmed — is what turns the remaining
number into a per-dispatch cost rather than a program-size artefact.

## 11. ✅ D-STACKPOOL — the references use the GENERIC stack, measured three ways

Joost's read of §10: *"does that smell like they use the generic stack?"* — ~4000
frames, nothing reclaimed, and the two references disagreeing with **each other**.
`scratchpad/stackpool_probe.py` tests it with `CLEAR`, which resizes the string
space (`CLEAR n`) and sets HIMEM outright (`CLEAR n,addr`).

| row | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|
| baseline, no `CLEAR` | 4080 | 3311 | 8 |
| `CLEAR 200` | 4079 | 3310 | 8 |
| `CLEAR 2200` (+2000 B) | 3793 | 3024 | **8** |
| `CLEAR 4200` (+4000 B) | 3508 | 2738 | **8** |
| `CLEAR 200,&HC000` | **2195** | **2195** | **8** |

**1. The pool is shared, and the rate is linear.** +2000 bytes of string space
costs **286** frames on the VG-8020 and **286** on the CF-3300; the next +2000
costs **285** and **286**. That is **7.0 bytes per frame**, four times over, on
two different machines.

**2. Pinning HIMEM makes the references agree exactly — 2195 = 2195.** They
differed at all only because Disk BASIC had taken RAM on the CF-3300. Fix the top
of the pool and both machines have the same room, which is what a HIMEM-bounded
stack predicts and what a fixed array cannot produce.

**3. zerobas reads 8 in every row.** `CLEAR` and HIMEM change nothing, because
the frames are in a fixed array.

### What this settles

The gap is not a number, it is an **allocation model**. The reference takes
control frames from one RAM pool bounded by HIMEM at ~7 B each; zerobas has two
fixed arrays (`GOSUB_DEPTH` = 8, `TRAPSTK_MAX` = 6). That single fact explains
everything §10 measured: the thousands of frames, the two references disagreeing,
and why nothing is ever "reclaimed" — `SP` simply moves.

So **both** of §6's surviving options are the wrong shape. "Pop the stale record"
adds a reclaim the reference does not do; "raise `TRAPSTK_MAX`" swaps one fixed
array for a bigger fixed array, and would still be insensitive to `CLEAR` and
HIMEM — measurably unlike the reference on all three rows above.

⚠️ **And the CLEAR rows were `<NO OUTPUT>` on all three sides at first**, because
`CLEAR` resets the error vector: with `ON ERROR` armed *before* it, the overflow
was untrapped and nothing printed. The probe's digits-only guard refused rather
than reporting a value, which is the only reason that read as an instrument fault
and not as "CLEAR breaks recursion".

## 12. 🔴 D-CTLCROSS — a `NEXT` cannot see a `FOR` frame below a live `GOSUB` frame

Measured 2026-09-04, `probes/basic/basic_probe_ctlcross.py`, both references
agreeing on every row.

§11 settled *where the frames live*. Designing the pooled replacement raised a
question the current shape makes **invisible**: with three separate arrays
(`GOSUB_STK`, `FOR_STK`, `TRAPSTK`) a `NEXT` can always reach its `FOR` frame,
because no GOSUB frame can ever be between them. Put the frames in one pool and
they interleave, and the machine has to answer.

| row | what it does | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `x.ctl` | `FOR` opened **inside** the sub — nothing interleaves | `1 0` | `1 0` | `1 0` |
| `x.nxgos` | `NEXT` inside a sub, `FOR` opened outside | `0 1` | `0 1` | **`1 0`** |
| `x.nxdeep` | `NEXT I` across `[FOR J][GOSUB][FOR I]` | `0 1` | `0 1` | **`1 0`** |
| `x.nxagain` | …and the loop-**continues** arm | `0 1` | `0 1` | **`2 0`** |
| `x.retfor` | `RETURN` over an inner `FOR` (D-FORRET's direction) | `1 1` | `1 1` | `1 1` |

Each row prints `[R E]`: `R` = the statement after the cross-`NEXT` ran
(`x.nxagain` reports the handler-entry **count** there), `E` = the stopping
`ERR`, 0 = none.

**Both references raise `NEXT without FOR` (ERR 1) on all three interleaved
rows.** Their `NEXT` search stops at the first frame that is not a `FOR` frame;
it neither walks past a GOSUB frame nor discards one to reach the loop. zerobas
matches straight across and runs the loop — **three divergences, and they exist
precisely *because* the stacks are separate.**

🎯 **So the pool is not only about depth: it closes these for free.** A single
descending pool whose `NEXT` search stops at the first non-`FOR` frame answers
all three the way both references do, with no extra mechanism and no walk. The
rows are pinned as known-divergent in the gate and are the arc's **behavioural**
acceptance; the pins come out in the commit that lands the pool.

### What this fixes about the pooled design

The frame layout follows from the rows rather than from taste:

* **No per-frame type tag is needed.** Because a `NEXT` never crosses a GOSUB
  frame, the `FOR` frames it may match are exactly the contiguous run at the top
  of the pool — everything newer than the newest GOSUB frame. `GSP` *is* that
  run's floor.
* **D-FORRET's `FSP-at-push` field becomes `GSP-at-push`**, and `x.retfor` (which
  zerobas already answers faithfully) keeps working for the same reason it does
  now: `RETURN` truncates the pool back to its own frame, discarding every `FOR`
  opened since.
* **A trap's service record must be pushed *before* its GOSUB frame**, so it ends
  up below it and stays out of the `FOR` run a `NEXT` walks.

### The same thing in a program a person would write

[`scratchpad/ctlpool_demo.py`](../scratchpad/ctlpool_demo.py) runs this on all
three machines — a `NEXT` that belongs to a `FOR` opened before the `GOSUB` it
now sits inside:

```basic
10 ONERRORGOTO200
20 FORI=1TO1
30 GOSUB100
40 PRINT"BACK IN LOOP"
50 GOTO300
100 PRINT"IN SUB: NEXT I"
110 NEXTI
120 PRINT"NEXT MATCHED"
130 RETURN
200 PRINT"ERR";ERR;"IN";ERL
210 RESUME300
300 PRINT"DONE"
```

| VG-8020 and CF-3300 | zerobas |
|---|---|
| `IN SUB: NEXT I` | `IN SUB: NEXT I` |
| `ERR 1 IN 110` | `NEXT MATCHED` |
| `DONE` | `BACK IN LOOP` |
| | `DONE` |

The references stop at line 110. zerobas matches the frame, ends the loop, falls
through to 120, `RETURN`s into line 40 and finishes with no error anywhere.

⚠️ **The prompt is part of the apparatus.** The demo's first reader looked for a
screen row equal to `RUN` and to `Ok`; zerobas prompts `ZB`, so its echo row
reads `ZBRUN` and its terminator is `ZB`, and the run that had measured the whole
divergence printed *"nothing was measured"*
[[an-unnamed-outcome-reads-as-no-outcome]].

### ⚠️ `x.ctl` is a precondition, not a row

It is the same program with the `FOR` opened **inside** the subroutine, so
nothing interleaves and every machine must read `1 0`. The probe refuses with no
verdict if it diverges: with the no-interleave control broken, none of the rows
above is readable as a finding.

## 13. Gates — the three probes are COLLECTED now, and falsified by planting

All three were `scratchpad/` probes with **no gate** until 2026-09-04 — an honest
rc that no battery collects is not an oracle (D-CATGATE). Promoted, given `make`
targets, and added to `tools/run_gates.py`'s `EMULATOR` list:

| target | probe | what it gates |
|---|---|---|
| `make stackpool-acceptance` | `basic_probe_stackpool.py` | the allocation **model** |
| `make trapdepth-acceptance` | `basic_probe_trapdepth.py` | the leak rate + the `d.selfarm` guard |
| `make ctlcross-acceptance` | `basic_probe_ctlcross.py` | the interleave semantics |

Faces are pinned, not row names (D-NAMEGATE): a row that still diverges but to a
*different* face would otherwise adjudicate as `known` and read green.

⚠️ **`stackpool-acceptance` gates a RELATION and never an absolute depth.** The
two machines have different memory maps by construction, so the reachable depth
is not a shared quantity — the same rule `basic_probe_clearpool.py` states for
`FRE(0)`. What it asserts is sensitivity, linearity, the stopping `ERR`, and —
*between the two references, where it means something* — that pinning HIMEM makes
them agree exactly.

### The knives, `scratchpad/ctlpool_knives.py` — 9 cells, 9 as predicted

| knife | `stackpool` | `trapdepth` | `ctlcross` |
|---|---|---|---|
| K-CP1 `GOSUB_DEPTH` 8→7 | green 🟢 | **RED** 🔴 | green 🟢 |
| K-CP2 `FOR_DEPTH` 8→1 | green 🟢 | green 🟢 | **RED** 🔴 |
| K-CP3 overflow `ERR 7`→`3` | **RED** 🔴 | **RED** 🔴 | green 🟢 |

🎯 **K-CP1's green is the sharpest cell.** Shrinking the GOSUB array moves the
depth zerobas reaches (8 → 7) and changes nothing about the allocation model — it
is still a fixed array, still insensitive to `CLEAR`. A `stackpool` gate that
reddened there would be pinning the absolute number its own docstring argues
against pinning. The controls are the half that carries the information.

⚠️ **K-CP3's anchor had to be three lines**, and the knife's own guard caught it:
`ld a,7` occurs **twice** in `basic/program.asm`, so a one-line anchor would have
cut the wrong overflow path. It also lands on the shared tail `gosub_stk_over`,
of which `ef_over` is an alias (D-DUPSPAN2), so the one cut moves **both** the
GOSUB and the FOR overflow error [[a-shared-tail-is-not-a-decision]].

Every plant hashes the four built images round itself (D-KNIFEROM2) and the tree
is restored byte-identically; the ROM hash after the run is identical to the one
before it.

## 14. ✅ D-CTLSTACK — the oracle says WHERE, not just how deep

§11 concluded *"the references use the GENERIC stack"* from **depth alone** —
~4080 frames, 7.0 B/frame, linear in `CLEAR`, the two machines agreeing once
HIMEM is pinned. That is an inference from a behaviour, and it never asked the
machine where the stack **is**. MSX publishes the answer, so on 2026-09-04
(`scratchpad/ctlstack_probe.py`) the inference was replaced by a reading.

The system variables are documented (MSX2 Technical Handbook / MSX Assembly Page
`map.grauw.nl`; already named in `basic/sysvars.inc:951` and `:1561`) and BASIC
can `PEEK` them: `MEMSIZ` `$F672`, `STKTOP` `$F674`, `STREND` `$F6C6`,
`FRETOP` `$F69B`.

⚠️ **This is RAM read through `PEEK`, not a disassembly.** Documented addresses
in, observed values out — the same black-box use every other row in this document
makes of these machines. The rows ask **where** and **how big**, deliberately
never *"what does a frame look like"*: that answer would be an implementation to
copy rather than a contract to meet.

### 1. `CLEAR n` lowers `STKTOP` by exactly n — `MEMSIZ` does not move

| `CLEAR` | VG-8020 `STKTOP` | CF-3300 `STKTOP` |
|---|---|---|
| none | 61600 | 56215 |
| `CLEAR 2200` | 59600 (**−2000**) | 54215 (**−2000**) |
| `CLEAR 4200` | 57600 (**−2000**) | 52215 (**−2000**) |

The stack top is bounded by the string space, and that is the whole of §11's
"+2000 B costs 286 frames".

### 2. 🎯 7.0 B/frame, reached a second way — from ADDRESSES

`STKTOP` and `STREND` are read **before** the recursion (which creates no
variables, so `STREND` cannot move under it), then the machine is driven to
control-stack overflow:

| | depth | `STKTOP − STREND` | B/frame |
|---|---|---|---|
| VG-8020 | 4067 | 28651 | **7.0** |
| CF-3300 | 3298 | 23266 | **7.1** |

§11 got 7.0 from the `CLEAR` ladder alone. **Two independent routes to one
number**: the control frames occupy the gap between the stack top and the
variable area. It is the generic stack, read rather than inferred.

### 3. 🔴 `CLEAR n,addr` does NOT set `MEMSIZ` to `addr` — 267 B per file buffer

`CLEAR 200,&HC000` reads `MEMSIZ` = **48616**, 536 below the requested 49152,
**identically on both references**. `MAXFILES` explains all of it:

| `MAXFILES` | `MEMSIZ` (both refs) | vs. MAXFILES 1 |
|---|---|---|
| 0 | 48883 | +267 |
| 1 (default) | 48616 | — |
| 2 | 48349 | −267 |

So `MEMSIZ = addr − 269 − MAXFILES × 267`, and **`MAXFILES` moves the stack
top**, because `STKTOP` tracks `MEMSIZ`. ⚠️ That settles an open ⚠️ in the
control-frame-pool arc (*"`MAXFILES=n` moves the pool top; measure what the
references do before assuming it is benign"*): it is **not** benign, and the
reference has the same dependency. The 267 B/channel figure independently
matches the ladder already recorded in
[`docs/clearpool-vg8020-characterization.md`](clearpool-vg8020-characterization.md) §2.

### 4. 🎯 What this settles for the design — the address is already right

    reference   STKTOP          = (addr − 269 − MAXFILES*267) − <string space>
    zerobas     strheap_varceil = min(HIMEM,TXTMAX) − MAXF*FCH_CTXSZ − POOLSIZE

**Those are the same formula.** zerobas already computes the reference's
`STKTOP` — it derives it sub-side for the string pool and the channel table
(`sub/strheap.asm`) — and simply puts no control frames there. So the two
candidate designs (relocate the Z80 `SP`, or run a software pointer down from
`varceil`) place the frames at **exactly the same addresses**; they differ only
in which pointer walks the range.

⚠️ **And zerobas's own `SP` is still C-BIOS's.** Its `$F674` reads 62336 =
`$F380` — C-BIOS's stack top, ~870 B of headroom — and `basic/` contains no
`ld sp,nn` at all: `SP` is only ever anchored and restored through `SAVSTK`.
Relocating it is therefore a change to a register nothing in this tree currently
initialises.

⚠️ **NOT MEASURED, and deliberately:** what a reference frame contains, or how
`NEXT` finds its entry among the return addresses. Those are implementation, not
contract; §12's `x.*` rows already pin the behaviour that any implementation has
to produce.

## 15. ✅ D-CTLFRE — `FRE(0)` counts down as you nest, and here it does not

A third independent route to the same 7.0, and the one that answers *"are we
working the same way as the oracles?"* directly. §14 put the reference's control
frames in the `STKTOP..STREND` gap — which is the memory `FRE(0)` reports. So
nesting a `GOSUB` must visibly shrink `FRE(0)`. Measured 2026-09-04,
`scratchpad/ctlfre_probe.py`; each row reads `[FRE(0)@top − FRE(0)@depth N, ERR]`.

| row | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|
| `f.g0` — GOSUB depth 1 | `7 0` | `7 0` | **`0 0`** |
| `f.g10` — depth 10 | `70 0` | `70 0` | **`22865 7`** |
| `f.g20` — depth 20 | `140 0` | `140 0` | **`22865 7`** |
| `f.n10` — 10 GOSUB+FOR pairs | `320 0` | `320 0` | **`22840 7`** |

**7, 70, 140 — exactly 7.0 B per level, marginally, on both references.** That is
the same figure §11 got from the `CLEAR` ladder and §14 got from
`(STKTOP − STREND)/depth`: three independent routes, one number.

🟢 **And a new one: `f.n10` − `f.g10` = 250 B over ten `FOR` entries = 25 B per
`FOR` frame** on both references (against zerobas's 11 B frame, which is smaller
because zerobas keeps 16-bit limits and steps where the reference keeps floats).

🔴 **zerobas reads `0` at depth 1 and cannot reach depth 10 at all.** Its frames
are in a fixed page-3 array `FRE(0)` has never seen, and its Z80 `SP` is still
C-BIOS's at `$F380` — neither is in the gap `FRE(0)` reports.

⚠️ **The `22865 7` readings are an OUTCOME, not a measurement**, and the first cut
of this probe reported them as `<NO OUTPUT>`. zerobas caps `GOSUB` at 8, so depth
10 raises ERR 7; untrapped, the program aborted before its fence. Every row now
arms `ON ERROR` and reports the `ERR` beside the delta, and the summary refuses
to read a delta whose `ERR` is non-zero — `A−B` there is `A` (B was never
written), a large and entirely plausible number
[[an-unnamed-outcome-reads-as-no-outcome]].

🔴 **This claim had been asserted twice in this arc and run zero times.**
`basic_probe_clearpool.py`'s docstring records the reference half in passing —
*"`FRE(0)` counts down to SP at ~6 bytes per nesting level"* — and then cancels
it out by reading every pair at equal depth, which is correct for what that probe
measures and is exactly why the zerobas half was never looked at. (The figure
there is ~6 for *evaluator* nesting; a `GOSUB` level is 7.)
[[a-justification-parenthesis-is-an-unrun-claim]]

### What §12–§15 together say about "the same way"

| | reference | zerobas |
|---|---|---|
| frame carries line number + resume pointer | yes | yes |
| stack top = `ceiling − files − string space` | `STKTOP` | `strheap_varceil` — **same formula** |
| nothing reclaimed on an abandoned trap dispatch | yes | yes |
| frames come out of the memory `FRE(0)` reports | **yes, 7 B/level** | 🔴 **no, 0** |
| depth responds to `CLEAR` / HIMEM | **yes** | 🔴 no |
| reachable depth | ~4080 / ~3311 | 🔴 **8** |
| `NEXT` can cross a `GOSUB` frame | **no** | 🔴 yes (§12) |

🎯 **The frame and the address arithmetic already match; the allocation does
not.** zerobas computes the reference's stack top and then puts nothing there.

## 16. 🔴 D-EVALDEPTH — the EVALUATOR nests out of the same pool there, and out of 384 B here

§15 asked whether *control* frames come from the memory `FRE(0)` reports. This
asks the same of the interpreter's **own** recursion, because on the reference
both live on one Z80 stack — so if evaluator nesting also comes out of that pool,
`CLEAR` bounds **both** depths with one number. Measured 2026-09-04,
`scratchpad/evaldepth_probe.py`. Each row reads `[FRE(0)@shallow − FRE(0)@deep,
ERR]`; the instrument is a chain of `DEF FN`s (`FNE`→`FND`→…→`FNA`, whose body is
`FRE(0)`), the one evaluator recursion whose depth is countable from BASIC.

| row | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|
| `e.ctl` — both reads at the **same** depth | `0 0` | `0 0` | `0 0` |
| `e.fn1` — one extra level | `25 0` | `25 0` | `0 0` |
| `e.fn2` — two | `50 0` | `50 0` | `0 0` |
| `e.fn3` — three | `75 0` | `75 0` | 🔴 **`ERR 7`** |
| `e.fn4` — four | `100 0` | `100 0` | 🔴 **`ERR 7`** |
| `e.def5` — **five definitions, depth ONE** | `0 0` | `0 0` | `0 0` |
| `e.paren8` — eight nested parentheses | `48 0` | `48 0` | `0 0` |

**25 B per `DEF FN` level, exactly linear, both references identical** — and
48 B for eight parentheses is **6 B per level**, which is precisely the *"`FRE(0)`
counts down to SP at ~6 bytes per nesting level"* that
`basic_probe_clearpool.py`'s docstring recorded in passing and never gated.

### 🔴 zerobas caps `DEF FN` nesting at THREE, and `e.def5` is what names it

`e.fn4` **defines** five functions and **nests** four, so its `ERR 7` had two
sufficient causes that coincide on every other row: a nesting-depth cap and a
definition-*count* cap. `e.def5` defines the same five and calls only `FNA` —
depth one — and reads `0 0`. **The cap is on DEPTH.**
[[two-rules-that-coincide-on-every-row-you-have]]

This is **not** the already-agreed `b.recurse` row (`DEF FNA(X)=FNA(X)`, infinite
recursion → `Out of memory` on all three, deffn slice). That is unbounded
recursion, which every machine must refuse. This is *finite* nesting three deep,
which both references take in their stride, and it had never been asked.

**The cause is in our own source, not inferred:** `basic/deffn.asm:192` guards a
nested FN's live-prefix save against `FN_STK_FLOOR` = `$F200`
(`basic/sysvars.inc:3453`), and `SP` starts at C-BIOS's `$F380` — **384 usable
bytes** for every nested save plus the evaluator's own frames. The comment there
already says it: *"this machine's Z80 stack is a few hundred bytes"*.

### 🎯 What this does to the arc's design choice

zerobas now has **two** functional depth caps, and they have **one** cause — the
frames are not in the HIMEM-bounded region the reference puts them in:

| | reference | zerobas | in the `FRE(0)` pool? |
|---|---|---|---|
| `GOSUB` depth | ~4080 | **8** | there yes (7 B/level), here no |
| `DEF FN` nesting | ≥4, 25 B/level | **3** | there yes, here no |

⚠️ **A software pointer running down from `varceil` fixes only the first.** It
moves `GOSUB`/`FOR` frames into the free gap and leaves `SP` at `$F380`, so
`DEF FN` nesting stays capped at 3 and evaluator depth stays un-bounded-by-`CLEAR`.
Relocating `SP` fixes both with one mechanism — which is exactly why the
reference has one stack and not two.

⚠️ **And the two cannot simply both descend from `varceil` independently**: they
would collide. That is the structural reason the reference merges them, and the
honest cost of the merge is the per-frame type tag a `NEXT` then needs to scan
past return addresses. §12's rows say what the behaviour must be; they do not say
which mechanism produces it.

🟢 The `DEF FN` cap is separable and could be addressed on its own (more room for
the save, or a different save strategy). It is filed here because it was found
here, not because it must be fixed here.

## 17. ✅ D-CTLPOOL — the pool, implemented

Landed 2026-09-04. `GSP`/`FSP`/`TRAPSVC` stop indexing three fixed arrays and
become pointers into one descending pool, which is what §11–§16 said the
references do. **105/105 gates green, 59/59 unit-test files.**

### The map, and it is the reference's own

    [PRGEND+2 .. ARYEND+2)  variables + arrays, growing UP
         [ the free gap ]
                             control frames, growing DOWN   <- CSP
    CTLTOP = strheap_varceil()
    [varceil .. floor)      the MAXFILES channel table
    [floor .. C)            the string pool     C = min(HIMEM,TXTMAX)

🎯 **`CTLTOP` is `strheap_varceil()` — the address §14 measured the reference
publishing as `STKTOP`.** Nothing new is derived: zerobas already computed it for
the string pool and the channel table, and simply put nothing there.

| cell | was | is |
|---|---|---|
| `GSP` | index into `GOSUB_STK` | the newest GOSUB frame's address |
| `FSP` | index into `FOR_STK` | **the `FOR` run's floor** — the run is `[CSP, FSP)` |
| `CSP` | — | the allocation frontier |
| `CTLTOP` | — | the pool's top, re-derived at every `clear_vars` |
| `TSP` | — | the newest trap service record |
| `CTLLIM` | — | the collision floor, `ARYEND+2` |
| `TRAPSVC` | count | count (kept: `ex_return` gates on it every RETURN) |

`GOSUB_STK` (48 B), `FOR_STK` (88 B) and `TRAPSTK` (18 B) are retired — **146 B
of page-3 RAM recovered** net of the four new cells.

### Results

| | before | after | reference |
|---|---|---|---|
| `GOSUB` depth | **8** | **2866** | 4080 / 3311 |
| responds to `CLEAR n` | no | **yes, 8.0 B/frame linear** | yes, 7.0 |
| responds to `CLEAR n,addr` | no | **yes (2000)** | yes (2195) |
| `x.nxgos` / `x.nxdeep` / `x.nxagain` | `1 0` / `1 0` / `2 0` | **`0 1` ×3** | `0 1` ×3 |
| 20 abandoned dispatches | aborted at `TRAPSTK_MAX`=6 | **completes, leaks 29 frames** | leaks 24 |
| `d.selfarm` | `9 0` | **`9 0`** | `9 0` |

The absolute depth and the 8.0 B/frame rate are **not gated** — they are
properties of this machine's map and frame layout, and the two references cannot
agree on them either (4080 vs 3311). What is gated is the model.

### Three design points the measurements settled

1. **No per-frame type tag.** §12 measured that a `NEXT` never crosses a GOSUB
   frame, so the frames it may match are exactly the contiguous run above the
   newest one — `[CSP, FSP)`, with `FSP` set to the frame base by `gosub_push`.
   The search stops at the floor and D-CTLCROSS falls out with no walk.
2. **D-FORRET's field survives under a new name.** The frame is
   `[CURLINE][resume][prevGSP][prevFSP]`; restoring `prevFSP` discards every
   `FOR` opened since the GOSUB. `prevGSP` is new and unavoidable — the GOSUB
   frames are no longer contiguous.
3. **The trap record loses its `gsp` key.** It is pushed *after* its GOSUB frame,
   so it sits immediately below it and `TSP + TRAP_FRAME == GSP` *is* the match.
   `ret_frame`'s single `CSP := GSP + GOSUB_FRAME` then frees the frame, the
   record and every `FOR` above them at once. ⚠️ `FSP` moves to the record too,
   or the next `NEXT` would read those 3 bytes as a `FOR` frame.

### 🔴 The one stored derivation, and why it is not `ctl_alloc`'s ceiling

`CTLLIM` (= `ARYEND+2`) is **cached**, against `strheap_floor`'s own
"DERIVED, NEVER STORED" rule. The reason is speed: `ARYEND` needs an array-chain
walk, which is sub-ROM knowledge, and every push would then cost a `CALSLT` —
`FOR I=1 TO 1000:GOSUB 100:NEXT` pushes a thousand times, on an interpreter
already 2.5–3.8× the CF-3300. So `sub/strheap.asm`'s `strheap_ctllim` is the one
definition and it is refreshed at every point the region's end can move (both
allocator success paths, and `sh_ctl_reset`). ⚠️ **A path that grows the region
without passing one of those leaves `CTLLIM` stale-LOW — the dangerous
direction.** That is this design's weakest joint and it needs a gate of its own.

🟢 The symmetric half is one comparison: `strheap_varceil` now answers
`min(varceil, CSP)`, so the variable/array region cannot grow into live frames
either. At rest `CSP == CTLTOP` and every existing caller keeps its answer.

### Three faults this cost, all worth recording

1. 🔴 **A nested `IF CLEARPOOL` closed the OUTER block early.** The new ops were
   inserted inside an existing conditional; pasmo assembles the unbalanced pair
   **without complaint**, and the only symptom was a ROM that booted to a screen
   of pattern-table noise.
2. 🔴 **`SUBSLOT_OK` is power-on garbage at `init` line 28.** `clear_vars` reaches
   `ctl_reset` a hundred lines before `init_ext_roms` records the sub-ROM slot,
   and RAM there reads `$FF` (D-VALTYP) — so `subrom_call`'s `or a` guard does
   **not** fire and it `CALSLT`s into a wild slot. No caller had ever dispatched
   the tenant that early. `ctl_reset` now tests `cp 1`, the value the scan
   actually writes, so garbage reads as absent.
3. 🔴 **`sh_ctl_alloc` publishes the new `CSP` in `SH_PTR` — the cell the caller
   passed its resume pointer in.** Caught before a build. The parameter block is
   shared; an op that writes a cell another op reads is not a private register.

### ⚠️ And a probe was squatting in memory BASIC now uses

`basic_probe_stop_trap.py` keeps its sentinels at `$D000..$D003`, which is inside
BASIC's free area on **every** one of these machines. It worked by luck: the
reference's stack starts ~8 KB above and never descends that far, and zerobas
kept its frames in page 3. With the pool starting at ~`$DA38`, this suite's
held-key case — which abandons dispatch after dispatch, and neither machine
reclaims those (§10) — walked the pool down over `$D002`, and `ran` read **208**,
i.e. `$D0`: the high byte of a frame pointer, read as a flag. The fix is
`CLEAR 200,&HCFFF` in the fixture: reserving the memory is what an MSX program
would do, and moving the sentinels would only relocate the same accident.

## 18. ✅ D-CTLLIM — the stored floor is gated now, and the first gate was blind

§17 shipped `CTLLIM` (= `ARYEND+2`) as a **cache**, against `strheap_floor`'s own
"DERIVED, NEVER STORED" rule, because deriving it needs an array-chain walk and a
`subrom_call` per push is not affordable. Its failure mode is silent: a growth
with no subsequent refresh leaves the floor **stale-LOW** and control frames land
inside live variables. `make ctllim-acceptance`
(`probes/basic/basic_probe_ctllim.py`) is the gate §17 said it needed.

🎯 **The rows test the corruption, not the pointer.** Reading `CTLLIM` back would
assert the implementation against itself. Instead each row fills memory with a
known pattern, drives the pool **all the way to its floor** by recursing to
`Out of memory`, and counts cells that changed.

| row | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|
| `l.ctl` — five scalars, no bulk allocation | `4051 0 7` | `3282 0 7` | `2840 0 7` |
| `l.ary` — `DIM A(300)`, filled | `3715 0 7` | `2946 0 7` | `2549 0 7` |
| `l.scal` — 60 scalars, the *other* allocator | `3800 0 7` | `3031 0 7` | `2621 0 7` |

`[depth, corrupted cells, ERR]`. **Zero corruption everywhere**, and the `DIM`
costs depth on every machine (333 / 333 / 291) — the floor rises with `ARYEND`.
🟢 The references pass too, which makes this a differential rather than a
zerobas-only assertion: their frames come out of the same gap, bounded by
`STREND`.

⚠️ **Both allocators are exercised, and that is not padding.** `scv_alloc` and
`ary_alloc` have **separate** refresh hooks; a gate that only `DIM`med would
leave the scalar one untested — which knife K-CL1 proves.

### 🔴 The knives scored 0/3 first, and found two defects in the gate

`scratchpad/ctllim_knives.py` removes a refresh — the real failure, not a proxy.
The first matrix reddened **nothing**:

1. **The hooks cover for each other.** `CTLLIM` is recomputed from scratch by
   whichever allocator ran last, so a scalar created *after* a `DIM` refreshes
   the floor and hides a missing array hook completely. `l.ary` now creates every
   scalar it will use **before** the `DIM`, which is what lets K-CL2 fire at all.
   (K-CL3's first cut removed the *reset* hook — invisible for the same reason:
   the first variable allocation refreshes it.)
2. 🔴 **The gate reported its own subject as an instrument fault.** A floor stale
   enough to reach the interpreter's state takes the machine with it, so the row
   prints **nothing** — and `<NO OUTPUT>` returned rc 2, "not measured". That is
   how **every** knife scored green. A blank on a *reference* is an instrument
   fault; a blank on zerobas alone while both references answer is the finding in
   its loudest form [[an-unnamed-outcome-reads-as-no-outcome]]. Every knifed row
   fails exactly this way, so without the fix the matrix stays 0/3.

The second matrix is **3/3, and orthogonal**:

| knife | rows named corrupted |
|---|---|
| K-CL1 `scv_alloc` refresh removed | `l.ctl`, `l.scal` — 🟢 `l.ary` green, its own `DIM` refreshes last |
| K-CL2 `ary_alloc` refresh removed | `l.ary` **only** — 🟢 the others have no array |
| K-CL3 **both** removed | all three |

Each cut reddens exactly the rows whose last growth went through the hook it
removed. A knife that reddened everything would prove only that the machine
broke; the greens are what say each row isolates the hook it names.

⚠️ **The runner rebuilds before taking its baseline.** A restore puts the *source*
back but leaves `build/` holding the last knifed image, so a baseline without it
measures the previous knife and refuses — which is what happened, and the ROM
hash in the log is what made it obvious rather than mysterious.

### ⚠️ What this gate still does not cover

It proves the two *known* hooks are load-bearing and that the floor tracks both
allocators. It cannot prove no **third** growth path exists — that would need the
derivation back, not a cache. If one is ever added without a refresh, these rows
catch it only if that path is exercised by a row here.
