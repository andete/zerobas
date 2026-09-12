# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `150f1541`. Recount everything — never quote a number
  from this file.
* 🟢 **EVERY TIER 1 THE DRAIN PRODUCED IS CLOSED**: `NEW`, `FILES`, `LFILES`,
  `MERGE` — and `LOAD`, which only the MERGE sweep could have found. `make tiers`
  to recount; do not quote.
* 🟢 **THE WHOLE KWSWEEP IS CLEAN FOR THE FIRST TIME: `DIVERGENT=0`.** The only
  non-green row is the pre-existing WEAK `csrlin`, whose own note records CSRLIN
  measured CORRECT.

## What shipped this session

* **D-SPMERGE / D-NEWSTMT** (earlier): the stack into the control-frame pool;
  `NEW` as a statement.
* **D-KWDISK** (`89f43985`): kwsweep mounts the test image on BOTH sides. 36 -> 16.
* **D-KWRIG** (`0579b2f8`): `NEEDS-PRINTER:` joins `NEEDS-DISK:`. 16 -> 10.
* **D-KWTAPE** (`59937b12`): 10 -> 9, by a FILED defect rather than a row.
* **D-DFEND** (`c0bd895e`, docs `0de7219d`): `FILES`+`LFILES` were ONE tail.
  **8 B of sub page 1 back**; the sweep's first TWO-TAG row.
* **D-MERGERET** (`631157c0`, patches `150f1541`): `MERGE` *and* `LOAD` failed to
  return to command level. **+4 B of main page 1** (11 -> 7 free, inside the
  standing 20 B budget).

## The next item — the TIER 1 UMBRELLA, and its numbers are the first thing to fix

`make tiers` shows ONE TIER 1 left: **"Keyword-completeness gaps — the measured
remainder of MSX1 BASIC"**, marked ⛔. It is the drain's own parent, and the drain
has falsified its headline: it still says *"of **162** MSX1 reserved words,
**124** tokenise and **34** are genuinely absent"*. `kwtable.inc` has a different
count and the sweep now scores far more than 124.
🔴 **READ IT TO ITS END AND RE-VERIFY THE ⛔ BEFORE BELIEVING IT** — twelve
blockers were re-checked this session and ten were stale.
⚠️ **THE ITEM ITSELF WARNS ABOUT EXACTLY THIS FAILURE** (the `TAB(` story: a claim
of "already faithful" that a differential agreed with for the wrong reason), so
leaving its own counts stale is the same defect one level up.

## The drain after that — NINE words, two blockers MEASURED REAL

* `LLIST` — the program STOPS at it on both machines; direct mode has no program
  to list. Its printed bytes are identical on both. Needs the `screen_printer`
  capture (already in `basic_probe_lptverb.py`) plus BOOT-PER-CASE: the log
  accumulates. 🟢 **`_row_rigs` IS READY** — D-DFEND made it a tuple and `lfiles`
  proves the two-tag path.
* `CLOAD` `CSAVE` — the rig RECORDS and nothing here PLAYS (`cassetteplayer
  insert` appears nowhere under `probes/`). 🔴 **`TIME` DOES NOT ADVANCE DURING A
  TAPE SAVE** (interrupts off) — the no-CSAVE control reads the same.
* `INKEY$` `INPUT` `GET` — the key injector's TIMING, a harness change; must not
  reopen D-LATCH.
* `AUTO` `RENUM` need a row FORMAT, not a rig; `CALL` needs an extension that is
  safe to invoke.

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

Paste this into a fresh session:

    /loop continue autonomously on zerobas — 🔴 TIER 1 BEFORE ANYTHING ELSE, then resume draining "no known gap" to ZERO (Joost's 2026-09-12 ruling, which outranks TIER 4). Read scratchpad/LOOP-RESTART.md FIRST, then the item's own block in TODO.md to its END. Run `make tiers`; recount keywords with `python3 tools/tier_table.py --keywords` — never quote a count. THIS SLICE: the ONE remaining TIER 1, the "Keyword-completeness gaps" UMBRELLA item, which is the drain's own parent and is marked ⛔. Its headline still says "of 162 MSX1 reserved words, 124 tokenise and 34 are genuinely absent" — numbers this session's drain has falsified. 🔴 RE-VERIFY THE ⛔ BEFORE BELIEVING IT: twelve blockers were re-checked this session and ten were stale. Correct its counts from `tools/tier_table.py --keywords` and `make kwsweep` rather than from any file, and say what the item's exit criterion NOW is. ⚠️ The item itself warns about exactly this failure — the `TAB(` story, a claim of "already faithful" that a differential agreed with for the wrong reason — so leaving its own counts stale is that defect one level up. Then resume the drain: nine words (AUTO CALL CLOAD CSAVE GET INKEY$ INPUT LLIST RENUM), with LLIST the cheapest (the `screen_printer` capture already exists in basic_probe_lptverb.py and `_row_rigs` is already a tuple). Standing rules: full `make gates` before each commit and never commit red (a docs-only change gets a ~45 s static-tier run — the harness skips the emulator tier itself and says so); 🔴 AFTER ANY basic/ OR sub/ CHANGE, `git status --short` WILL SHOW zerobas-main-eu.ips/.bps REFRESHED BY THE BUILD — stage them with the commit, because patch-freshness-check can only see the omission one commit LATER; after a `--fix` of todo-citation-check re-run every gate that READS TODO.md; `rm -rf build && make basic-reloc` for any wall figure, and BACK UP build/kwsweep-verdicts.json first — a clean build deletes the pin tier_table reads; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; re-run the five battery-excluded targets by hand after any slice touching a shared leaf; NEVER poll with a pattern that matches the polling command itself — use the background task's own completion notification; READ the output of every edit script.
