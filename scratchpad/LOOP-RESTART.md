# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `0de7219d`. Recount everything — never quote a number
  from this file.
* 🔴 **TIER 1 BEFORE ANYTHING ELSE**, then the drain ruling (Joost, 2026-09-12:
  "no known gap" to ZERO before TIER 4). Four TIER 1 items came OUT of the drain,
  which is the ruling working.
* 🟢 **D-DFEND CLOSED TWO OF THEM.** `make tiers` to recount; do not quote.

## What shipped this session

* **D-SPMERGE / D-NEWSTMT** (earlier): the stack into the control-frame pool;
  `NEW` in a program.
* **D-KWDISK** (`89f43985`): kwsweep mounts a writable private copy of
  `disk/test720.dsk` on BOTH sides. "no known gap" 36 -> 16.
* **D-KWRIG** (`0579b2f8`): `NEEDS-PRINTER:` joins `NEEDS-DISK:`. 16 -> 10.
* **D-KWTAPE** (`59937b12`): 10 -> 9, by a FILED defect rather than a row.
* **D-DFEND** (`c0bd895e`, docs `0de7219d`): `FILES` and `LFILES` were ONE
  statement's two halves — 4 arms -> 0, **8 bytes of sub page 1 back**, and the
  sweep's first TWO-TAG row (`NEEDS-DISK:` + `NEEDS-PRINTER:`).

## The next item — `MERGE`, and it is the LAST drain-produced TIER 1

**`MERGE` inside a running program carries on here; the CF-3300 returns to
command level.** The merge itself LANDS identically on both (`LIST 100` shows the
merged line on each), so the divergence is purely what the statement does with the
interpreter's cursor when `DIRECTF` says a program is running. Measured three ways
(`scratchpad/kwdrain_mergechk.out`, `scratchpad/kwdrain_mergechk_cf.out`), and the
kwsweep `merge` row reads DIVERGENT until it is fixed — it is the only DIVERGENT
row in the whole sweep.
🎯 **SWEEP `LOAD` AND `RUN"file"` WITH IT** — same "return to command level"
contract, and D-DFEND is the standing lesson that two verbs filed separately can
be one tail.
⚠️ **LEAVE A ROW BEHIND**: attribution comes from OPEN items, so closing this
without a kwsweep row hands `MERGE` straight back to the unattributed pile. The
row already exists and will simply go green — check that it does, and that it goes
green for the RIGHT reason.

## The drain after that — NINE words, two blockers MEASURED REAL

* `LLIST` — the program STOPS at it on both machines, so nothing reaches the
  screen; direct mode has no program to list. Its printed bytes are identical on
  both. Needs the `screen_printer` capture (written already in
  `basic_probe_lptverb.py`) plus BOOT-PER-CASE: the log accumulates.
  🟢 **`_row_rigs` IS READY FOR IT** — D-DFEND generalised it to a tuple and
  `lfiles` proves the two-tag path works.
* `CLOAD` `CSAVE` — the rig RECORDS and nothing in this tree PLAYS
  (`cassetteplayer insert` appears nowhere under `probes/`). `cas_decode` is
  WAV->bytes only. 🔴 **`TIME` DOES NOT ADVANCE DURING A TAPE SAVE** (interrupts
  off) — 4 jiffies for a ~6 s recording, and the no-CSAVE control reads the same.
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

    /loop continue autonomously on zerobas — 🔴 TIER 1 BEFORE ANYTHING ELSE, then resume draining "no known gap" to ZERO (Joost's 2026-09-12 ruling, which outranks TIER 4). Read scratchpad/LOOP-RESTART.md FIRST, then the item's own block in TODO.md to its END. Run `make tiers`; recount keywords with `python3 tools/tier_table.py --keywords` — never quote a count. THIS SLICE: `MERGE` inside a running program carries on here where the CF-3300 RETURNS TO COMMAND LEVEL. The merge itself lands identically on both (LIST 100 shows the merged line on each), so the divergence is what the statement does with the interpreter's cursor when DIRECTF says a program is running — measured in scratchpad/kwdrain_mergechk.out and scratchpad/kwdrain_mergechk_cf.out. 🎯 SWEEP `LOAD` AND `RUN"file"` WITH IT: same "return to command level" contract, and D-DFEND is the standing lesson that two verbs filed separately can be ONE tail. ⚠️ The kwsweep `merge` row is the only DIVERGENT row in the sweep and must go green FOR THE RIGHT REASON — leave it in place, because attribution comes from OPEN items and closing the item without a row hands MERGE back to the unattributed pile. Re-verify any filed claim before building on it. Standing rules: full `make gates` before each commit and never commit red (a docs-only change gets a ~45 s static-tier run — the harness skips the emulator tier itself and says so); after a `--fix` of todo-citation-check re-run every gate that READS TODO.md; `rm -rf build && make basic-reloc` for any wall figure, and BACK UP build/kwsweep-verdicts.json first — a clean build deletes the pin tier_table reads; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned, `git status --short` first; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; re-run the five battery-excluded targets by hand after any slice touching a shared leaf; NEVER poll with a pattern that matches the polling command itself — use the background task's own completion notification; READ the output of every edit script.
