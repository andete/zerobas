# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `ca271f77`. Recount everything — never quote a number
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
  `NEEDS-LOG:`, the third rig — a CAPTURE rather than a device — and `LLIST`.

## The next slice — `GET` and `CALL`, the two that need NO new apparatus

**EIGHT words: `AUTO CALL CLOAD CSAVE GET INKEY$ INPUT RENUM`.** The printer
cluster is closed (D-KWRIG, D-DFEND, D-KWLOG). Of the eight, two look reachable
with the rigs already built — **measure before believing either**:

* **`GET` — MSX1's `GET` is the RANDOM-FILE record read (`GET #n[,record]`), not
  a keyboard verb.** `PUT` already ships (it sits at TIER 3, "slower than the
  reference"), and the disk rig is mounted, so a round trip is expressible in one
  row: `OPEN ... AS#1`, `FIELD`, `LSET`, `PUT`, then `GET` the record back and
  read the field. 🔴 **PROVE THE READBACK MOVES**: read the field BEFORE the GET
  as the blind shape, or a row that never re-read anything passes.
* **`CALL` — the question is whether an UNKNOWN extension separates.** `CALL ZZQ`
  on a real Disk BASIC may answer something other than `Syntax error`; a machine
  with no `CALL` answers `Syntax error`. If the two coincide the row is blind and
  `CALL` stays out, WITH the measurement filed. ⚠️ Do NOT reach for `CALL SYSTEM`
  or `CALL FORMAT` — one exits to DOS and one formats the disk.

The other six each need apparatus, all named and measured:
`CLOAD`/`CSAVE` a tape PLAYER (nothing here plays one; and `TIME` does not advance
during a tape save, so the cheap readback is dead); `INKEY$`/`INPUT`/`GET`'s
keyboard cousins the key injector's TIMING (a harness change, must not reopen
D-LATCH); `AUTO` a case slot that survives line-entry mode; `RENUM` a read-back the
row format cannot express — it STOPS the program, so no statement after it runs,
and the printer log cannot help because a `LLIST` after it never executes.

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

    /loop continue autonomously on zerobas — 🔴 TIER 1 BEFORE ANYTHING ELSE, then drain "no known gap" to ZERO (Joost's 2026-09-12 ruling, which outranks TIER 4). Read scratchpad/LOOP-RESTART.md FIRST, then the item's own block in TODO.md to its END. Run `make tiers`; recount keywords with `python3 tools/tier_table.py --keywords` — never quote a count. THIS SLICE: `GET` and `CALL`, the two of the eight that need NO new apparatus. 🔴 MSX1's `GET` is the RANDOM-FILE record read (`GET #n[,record]`), NOT a keyboard verb — `PUT` already ships and the disk rig is mounted, so a round trip fits one row: OPEN AS#1, FIELD, LSET, PUT, then GET the record back and read the field. PROVE THE READBACK MOVES — read the field BEFORE the GET as the blind shape, or a row that never re-read anything passes. For `CALL`, measure whether an UNKNOWN extension (`CALL ZZQ`) separates from a machine that has no CALL at all: both may answer `Syntax error`, in which case the row is BLIND and CALL stays out WITH the measurement filed. ⚠️ Never `CALL SYSTEM` or `CALL FORMAT` — one exits to DOS, one formats the disk. Every row must clear the FIVE silent-failure modes in LOOP-RESTART.md, prove its readback MOVES before the row is kept, and after adding rows READ THE WHOLE SWEEP SUMMARY. Re-verify any blocker before believing it. Standing rules: full `make gates` before each commit and never commit red; 🔴 AFTER ANY basic/ OR sub/ CHANGE stage zerobas-main-eu.ips/.bps WITH the commit (patch-freshness-check only sees the omission one commit LATER); 🔴 `check_todo_citations.py --fix` REWRITES EVERY DOC THAT CITES A MOVED BLOCK — it touched FIVE files beyond TODO.md last time; read `git status --short` as a LIST, because that gate compares the working tree and stays green either way; after a `--fix` re-run every gate that READS TODO.md; `rm -rf build && make basic-reloc` for any wall figure, and BACK UP build/kwsweep-verdicts.json first — a clean build deletes the pin tier_table reads; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; re-run the five battery-excluded targets by hand after any slice touching a shared leaf; NEVER poll with a pattern that matches the polling command itself — use the background task's own completion notification; READ the output of every edit script.
