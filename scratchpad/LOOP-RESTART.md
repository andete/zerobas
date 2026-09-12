# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `51dabf6b`; battery **128/128** plus all five
  battery-excluded targets green (bdos, diskbasic, fat-error, input-devices,
  lnblank-say). Recount everything — never quote a number from this file.
* **TIER 1 = 1**, and it is ⛔ BLOCKED on a fixture. **TIER 2 and TIER 3 = 0.**
* 🔴 **JOOST'S RULING (2026-09-12): the "no known gap" list is drained to ZERO
  before TIER 4 is picked up.** A keyword with no evidence can hide a TIER 1
  defect, and one just did — `NEW` came out of that list.

## What shipped this session

* **D-SPMERGE landed**: the Z80 stack moved into the control-frame pool, closing
  the TIER 1 expression defect (a legal 16-deep parenthesised formula used to
  wreck the machine). All nine `parennest` pins flipped in the shipping commit.
* **D-NEWSTMT**: `NEW` inside a running program was a Syntax error and ran on the
  reference — fixed, and BYTE-NEGATIVE (page 1 2 B -> 11 B free).
* **D-KWDRAIN**: "no known gap" 114 -> 36, kwsweep evidence 33 -> 110.

## The next slice

Mount the EXISTING disk image in `basic_probe_kwsweep.py`. The fixture is not
missing: `DISK_TEST_DSK := disk/test720.dsk` (Makefile:663) from
`tools/make_test_dsk.py`, mounted via `probe_sides.diska()`, already used by
`ramfree-acceptance`, guarded by `diskdep-check`. kwsweep names neither `diska`
nor `DISK_TEST_DSK` — that is the whole blocker for ~23 of the 36 words.

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

Four for four this session were STALE: the display verbs' "cannot take a kwsweep
row", the multi-line words' "cannot be expressed in one row", the CF-3300
NO-ORACLE claim, and the disk fixture. Re-verifying has been cheaper than the
work it was hiding every single time.

## Open for Joost — do not pick up

* The `CONT` item (TIER 5): inside a program zerobas prints `Can't CONTINUE`
  where the reference prints `Can't CONTINUE in 10`. The cause is a DELIBERATE
  `print_msg`-instead-of-`raise_error` choice recorded at `basic/program.asm:1188`.
* Ranking the remaining apparatus blockers (printer log + its LSTOUT hang hazard,
  AUTO's line-entry mode, keystroke injection, step (c)).

## The command

Paste this into a fresh session:

    /loop continue autonomously on D-KWDRAIN — drain "no known gap" to ZERO, Joost's 2026-09-12 ruling, which outranks the TIER 4 speed items. Read scratchpad/LOOP-RESTART.md FIRST for the full state, then TODO.md's "no known gap" block to its END. Recount with `python3 tools/tier_table.py --keywords` — never quote a count. THIS SLICE: mount the EXISTING disk image in probes/basic/basic_probe_kwsweep.py (DISK_TEST_DSK := disk/test720.dsk, via probe_sides.diska(), pattern in ramfree-acceptance, declare it in the make target or diskdep-check refuses) and convert the disk/tape verbs; tag them NEEDS-DISK like the `cvi` row or they measure a diskless VG-8020 against a disk-equipped zerobas. Mount a WRITABLE COPY where a row writes. Re-measure DSKF with the image in — it read 0 like a stub only because nothing was mounted. Every row must clear the FIVE silent-failure modes in LOOP-RESTART.md, and after adding rows READ THE WHOLE SWEEP SUMMARY. Re-verify any blocker before believing it: four for four were stale this session. Standing rules: full `make gates` before each commit and never commit red; `make basic-reloc` from a CLEAN tree for any wall figure; stage explicit paths, `git add -A` banned, `git status --short` first; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; re-run the five battery-excluded targets by hand after any slice touching a shared leaf; READ the output of every edit script.
