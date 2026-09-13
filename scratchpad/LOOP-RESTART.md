# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `448e2b29`. Recount everything — never quote a number
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

## Where the drain stands — THREE words, and a decision that is Joost's

`CLOAD CSAVE INKEY$`. Each needs APPARATUS rather than a cleverer row, and that is
filed as **its own 🙋 NEEDS-JOOST item** in TODO.md (it was briefly inside the
autonomous drain block, and `todo-marker-check` rightly refused an item carrying
two markers). The prices are in that item. What the drain already bought is beside
them, so the price is judged against something: **four TIER 1 defects came out of
this list** — `NEW` `FILES` `LFILES` `MERGE` — plus `LOAD`, which only the `MERGE`
sweep could have found.

## The next slice — the CLOAD ORACLE, which is a MEASUREMENT, not a build

🔴 **`CLOAD`'S BLOCKER HAS MOVED THREE TIMES UNDER MEASUREMENT** and the current
one is the only one left standing:

| filed as | measured |
|---|---|
| "nothing in this tree PLAYS a tape" | FALSE — `-cassetteplayer` mounts one; `cas_encode.build_cas_basic` makes the `.cas` |
| "no READBACK — it returns to command level" | FALSE — **`Found:ZQ` reaches the SCREEN**; no new capture needed |
| *(open)* | **the VG-8020 does not read the fixture.** zerobas prints `Found:ZQ`; the reference prints nothing and never reaches a prompt |

⚠️ **NOT TIMING AND NOT A MISSING PORT** — `cap_gap` 60 and 150 are identical, and
the VG-8020 config carries `<CassettePort/>` like the repack machine. And every
cassette probe in this tree runs on the REPACK MACHINE ONLY (its own header says
so), so this has never been asked before.
➡️ **SEPARATE THE TWO CAUSES, cheapest first**: (a) an openMSX setting the repack
machine has and the VG-8020 does not — compare the two machine XMLs and the
cassette-related settings the cas probes set; (b) the fixture is built to zerobas's
reading of the `.cas` format and a real BIOS wants something else — in which case
that is a FINDING ABOUT THE FORMAT, not about the verb, and worth more than the
keyword. A tape WRITTEN BY ZEROBAS (`basic_probe_cassave.py` records one) fed to
the VG-8020 separates them in one run.
🔴 **THE TAPE POSITION IS STATE THAT SURVIVES A CASE** — the `AUTO` lesson again.
Batched, a second `CLOAD` reads `load error` because the first consumed the tape,
and one poisoned VG-8020 run showed the same stale screen for every case INCLUDING
THE CONTROL. Boot per case, one fresh tape each.

⚠️ **THE OTHER TWO STAY PARKED** unless Joost rules: `CSAVE` needs a WAV-decode
capture and `INKEY$` needs the key injector's timing exposed to a row — a harness
change, and D-LATCH/D-LATCH2 are the races it must not reopen.

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

Paste this into a fresh session:

    /loop continue autonomously on zerobas — 🔴 TIER 1 BEFORE ANYTHING ELSE, then drain "no known gap" to ZERO (Joost's 2026-09-12 ruling, which outranks TIER 4). Read scratchpad/LOOP-RESTART.md FIRST, then the item's own block in TODO.md to its END. Run `make tiers`; recount keywords with `python3 tools/tier_table.py --keywords` — never quote a count. THREE WORDS LEFT and they are a 🙋 NEEDS-JOOST item now: CLOAD CSAVE INKEY$ each need APPARATUS rather than a row, and the prices are in that item. THIS SLICE IS THE ONE THAT IS STILL A MEASUREMENT: why does the VG-8020 not read the tape fixture? zerobas prints `Found:ZQ` off a mounted `.cas`; the reference prints nothing and never reaches a prompt. NOT timing (cap_gap 60 and 150 are identical) and NOT a missing port (its config carries `<CassettePort/>`) — both already checked. Separate the two remaining causes, cheapest first: (a) an openMSX setting the repack machine has and the VG-8020 does not — compare the machine XMLs and whatever the cas probes set; (b) the fixture is built to zerobas's reading of the `.cas` format and a real BIOS wants something else, which would be a FINDING ABOUT THE FORMAT and worth more than the keyword. A tape WRITTEN BY ZEROBAS (basic_probe_cassave.py records one) fed to the VG-8020 separates them in one run. 🔴 THE TAPE POSITION SURVIVES A CASE — boot per case, one fresh tape each; batched, a second CLOAD reads `load error` because the first consumed the tape, and a poisoned run shows the same stale screen for every case INCLUDING THE CONTROL. ⚠️ If it turns out to need real apparatus rather than a setting, STOP and leave it to Joost with the price written down — do not build it in a loop tick. ⚠️ `auto` MUST STAY LAST IN SWEEP (banner comment says so). Standing rules: full `make gates` before each commit and never commit red; an item may carry only ONE marker — todo-marker-check refuses 🙋 and 🤖 together; 🔴 AFTER ANY basic/ OR sub/ CHANGE stage zerobas-main-eu.ips/.bps WITH the commit; 🔴 `check_todo_citations.py --fix` REWRITES EVERY DOC THAT CITES A MOVED BLOCK — five files beyond TODO.md every time; read `git status --short` as a LIST; after a `--fix` re-run every gate that READS TODO.md; `rm -rf build && make basic-reloc` for any wall figure, and BACK UP build/kwsweep-verdicts.json first; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; re-run the five battery-excluded targets by hand after any slice touching a shared leaf; NEVER poll with a pattern that matches the polling command itself — use the background task's own completion notification; READ the output of every edit script.
