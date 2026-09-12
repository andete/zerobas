# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `59937b12`. Recount everything — never quote a number
  from this file.
* 🔴 **JOOST'S RULING (2026-09-12): the "no known gap" list is drained to ZERO
  before TIER 4.** A keyword with no evidence can hide a TIER 1 defect, and FOUR
  now have: `NEW`, then `MERGE`, `FILES` and `LFILES`.
* 🔴 **AND THE ORDER ON TOP OF IT (the hourly backstop's own wording): TIER 1
  BEFORE ANYTHING ELSE.** There are now four open TIER 1 items and nine words
  left, so the next tick FIXES, it does not drain.

## What shipped this session

* **D-SPMERGE / D-NEWSTMT** (earlier): the stack moved into the control-frame
  pool; `NEW` in a program stopped being a Syntax error.
* **D-KWDISK** (`89f43985`): kwsweep mounts a writable private copy of
  `disk/test720.dsk` on BOTH sides. 36 -> 16, twenty words.
* **D-KWRIG** (`0579b2f8`): `NEEDS-PRINTER:` joins `NEEDS-DISK:`, the two capture
  splitters collapse into one `capture()`. 16 -> 10, six words.
* **D-KWTAPE** (`59937b12`): 10 -> 9, and NOT by a row — by a filed defect.

## The four open TIER 1 items — FIX THESE FIRST

1. **`FILES` ends its listing with a newline the reference does not emit** (the
   SCREEN sink).
2. **`LFILES` does not zero `LPTPOS`** (the PRINTER sink): park the head with
   `LPRINT"AB";` and zerobas reads `LPOS` 2 / 79 log bytes where the CF-3300
   reads 0 / 77. Both controls agree. `docs/spec-basic-lfiles.md` §3.3 records
   this as a CHOICE whose justification — "the head is at column 0 when the
   statement ends ... no row measures it" — is false once something parks it.
   🎯 **(1) AND (2) ARE PLAUSIBLY ONE WALK ENDING DIFFERENTLY ON TWO SINKS. Rule
   that in or out BEFORE changing either.**
3. **`MERGE` in a running program carries on; the CF-3300 returns to command
   level.** The merge itself lands identically on both. Sweep `LOAD` and
   `RUN"file"` with the fix — same contract.
4. The pre-existing fixture-blocked one (read it; do not assume).

## The drain after the fixes — NINE words, and two blockers now MEASURED REAL

* `LLIST` — the program STOPS at it on both machines, so nothing reaches the
  screen; direct mode has no program to list. Its printed bytes are identical on
  both (54 B). Needs the `screen_printer` capture (already written in
  `basic_probe_lptverb.py`) plus BOOT-PER-CASE: the log accumulates.
* `CLOAD` `CSAVE` — the rig RECORDS and nothing in this tree PLAYS
  (`cassetteplayer insert` appears nowhere under `probes/`). `cas_decode` is
  WAV->bytes only, so a playable fixture needs an encoder that does not exist.
  🔴 **AND THE CHEAP IDEA IS DEAD: `TIME` DOES NOT ADVANCE DURING A TAPE SAVE**
  (interrupts off) — 4 jiffies for a ~6 s recording, and the no-CSAVE control
  reads the same.
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

    /loop continue autonomously on zerobas — 🔴 TIER 1 BEFORE ANYTHING ELSE, then resume draining "no known gap" to ZERO (Joost's 2026-09-12 ruling, which outranks TIER 4). Read scratchpad/LOOP-RESTART.md FIRST, then the item's own block in TODO.md to its END. Run `make tiers`; recount keywords with `python3 tools/tier_table.py --keywords` — never quote a count. THIS SLICE: the `FILES` / `LFILES` pair, which are plausibly ONE walk ending differently on two sinks — rule that in or out BEFORE changing either. `FILES` emits a trailing newline to the SCREEN that the reference does not; `LFILES` does not zero `LPTPOS`, so `LPOS` reads 2 where the CF-3300 reads 0 and R-LP16's flush puts two extra bytes on the printer. Both are measured with agreeing controls (scratchpad/kwdrain_fileseol.out, scratchpad/kwdrain_lfflush.out). 🔴 docs/spec-basic-lfiles.md §3.3 records the LPTPOS behaviour as a deliberate CHOICE — read that paragraph and INVERT the conclusion rather than deleting the analysis, and leave a gate row behind or the keyword falls straight back into the unattributed pile. Re-verify any filed claim before building on it. Standing rules: full `make gates` before each commit and never commit red; after a `--fix` of todo-citation-check re-run every gate that READS TODO.md rather than the whole battery; `make basic-reloc` from a CLEAN tree for any wall figure; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned, `git status --short` first; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; NEVER poll with a pattern that matches the polling command itself — use the background task's own completion notification; READ the output of every edit script.
