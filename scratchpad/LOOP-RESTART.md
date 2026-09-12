# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `0579b2f8`. Recount everything — never quote a number
  from this file.
* 🔴 **JOOST'S RULING (2026-09-12): the "no known gap" list is drained to ZERO
  before TIER 4 is picked up.** A keyword with no evidence can hide a TIER 1
  defect, and three now have — `NEW`, then `MERGE` and `FILES` out of the disk
  slice.
* **TIER 1 = 3** after this session (recount: `make tiers`). Two are the D-KWDISK
  findings below; the third is the pre-existing fixture-blocked one.

## What shipped this session

* **D-SPMERGE / D-NEWSTMT** (earlier): the stack moved into the control-frame
  pool, and `NEW` in a program stopped being a Syntax error.
* **D-KWDISK** (`89f43985`): `basic_probe_kwsweep.py` mounts a WRITABLE PRIVATE
  copy of `disk/test720.dsk` on BOTH sides. 36 -> 16. Twenty words.
* **D-KWRIG** (`0579b2f8`): `NEEDS-PRINTER:` joins `NEEDS-DISK:`, the two capture
  splitters collapse into one `capture()`, and `_row_rig` names what a row needs.
  16 -> 10. Six words: `USR SCREEN KEY WAIT LPOS LPRINT`.

## Two TIER 1 defects the drain produced — both FILED, neither FIXED

* **`MERGE` in a running program carries on here; the CF-3300 returns to command
  level.** The merge itself lands identically on both. `LOAD` and `RUN"file"`
  share the contract and should be swept with the fix.
* **`FILES` ends its listing with a newline the reference does not emit.** Same
  names, same wrap, same padding — only the cursor's resting place.

## The next slice

Ten words left: `AUTO CALL CLOAD CSAVE GET INKEY$ INPUT LFILES LLIST RENUM`.
Three clusters, each with named apparatus, and **the tape one is the next to
re-verify because it looks already built**:

* `LLIST` `LFILES` — the printer LOG. `basic_probe_lptverb.py` already has the
  `screen_printer` capture; it needs BOOT-PER-CASE (the log accumulates) and a
  row that needs BOTH tags, which is what generalises `_row_rig`.
* `CLOAD` `CSAVE` — a tape rig, and one EXISTS: `cassetteplayer new` +
  `probes/lib/cas_decode.py`, driven by nine `basic_probe_cas*` suites.
* `INKEY$` `INPUT` `GET` — the key injector's TIMING, a harness change
  (`run_cases` must expose the per-case run time); must not reopen D-LATCH.
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

    /loop continue autonomously on D-KWDRAIN — drain "no known gap" to ZERO, Joost's 2026-09-12 ruling, which outranks the TIER 4 speed items. Read scratchpad/LOOP-RESTART.md FIRST for the full state, then TODO.md's "no known gap" block to its END. Recount with `python3 tools/tier_table.py --keywords` — never quote a count. TEN WORDS LEFT: AUTO CALL CLOAD CSAVE GET INKEY$ INPUT LFILES LLIST RENUM. THIS SLICE: the TAPE pair (CLOAD/CSAVE) — RE-VERIFY the "needs a tape rig" blocker FIRST, because the rig looks already built (`cassetteplayer new` + probes/lib/cas_decode.py, driven by nine basic_probe_cas* suites); if it is, add a `NEEDS-TAPE:` rig alongside NEEDS-DISK/NEEDS-PRINTER in `_row_rig` (basic_probe_kwsweep.py), which is the same shape the printer rig took. Then LLIST/LFILES, which need the `screen_printer` capture from basic_probe_lptverb.py, BOOT-PER-CASE (the log accumulates across a batch and a batched row reads its predecessors' output as its own), and the first row that needs TWO tags — that row is what generalises `_row_rig`. Every row must clear the FIVE silent-failure modes in LOOP-RESTART.md, prove its readback MOVES before the row is kept, and after adding rows READ THE WHOLE SWEEP SUMMARY. Re-verify any blocker before believing it: TEN for ten were stale this session. Standing rules: full `make gates` before each commit and never commit red; after a `--fix` of todo-citation-check re-run every gate that READS TODO.md rather than the whole battery; `make basic-reloc` from a CLEAN tree for any wall figure; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned, `git status --short` first; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; NEVER poll with a pattern that matches the polling command itself — use the background task's own completion notification; READ the output of every edit script.
