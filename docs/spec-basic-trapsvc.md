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

## 10. Gates — all rc=0, from a clean build, ROMs byte-identical throughout

`basic-reloc`, `unit-test` **59/59**, `deadcode`, `wall-assertion-check`,
`redundant-load-check`, `rowshape-check`, `injector-check`, `preflight-check`,
`latch-check`, `diskdep-check`, `switch-build-check` **6/6**, `kwsweep`
(`SUPPORTED=30`, no `MISSING`), `deffn-selftest`, `interval-trap-acceptance`
**ALL PASS**. `7942cc20` / `34bb8554` / `031184d9` before and after.

⚠️ `kwsweep`'s `DIVERGENT=1` is `csrlin`, the documented probe artifact
(`TODO.md:2519`) — pre-existing, and it cannot be this slice's: no source file
changed and all three images are byte-identical to `b8a8137`.

**Walls, read from this run's `make basic-reloc` (2026-08-23, `b8a8137`), not
quoted from memory:** main page-1 free **2 B**, page-0 low region free **17 B**,
sub page-0 **2563 B**, sub page-1 **1624 B**. §6's ~25–30 B is measured against
the 2.
