# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `4036a9c4`. Recount everything — never quote a number
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

## 🛑 THE LOOP STOPPED HERE, AND WHY — read this before taking any item

The drain ran **114 → 3** and then hit a wall that is a DECISION, not a puzzle.
`CLOAD CSAVE INKEY$` each need APPARATUS rather than a cleverer row, and that is
filed as its own **🙋 NEEDS-JOOST** item in TODO.md with the prices in a table.

🔴 **A TICK THAT FINDS NOTHING ELSE PERMITTED SHOULD REPORT AND STOP, NOT BUILD.**
The standing order allows apparatus "if it blocks the drain ruling" — these three
do, so the letter of it permits building them. The reason not to is that they are
THREE SEPARATE pieces of apparatus for THREE words, after a run whose cheap words
had a very high hit rate and whose expensive tail does not. That is a
value judgement about Joost's project, and it is his.

## What the drain bought, so the price has something to be judged against

**Four TIER 1 defects came out of this list** — `NEW`, `FILES`, `LFILES`, `MERGE` —
plus `LOAD`, which only the `MERGE` sweep could have found. All are FIXED. The
kwsweep is clean for the first time (`DIVERGENT=0`), and TIER 1 is down to the
umbrella item whose own exit criterion is this list reaching zero.

## The last measurement, finished: `CLOAD` has NO ORACLE here

| run | result |
|---|---|
| zb `CSAVE"ZQ"` → 124 486-byte WAV, then zb `CLOAD"ZQ"` | **`Found:ZQ`** — the control |
| zb `LOAD"CAS:ZQ"` on the same tape | **`Found:ZQ`** |
| VG-8020, both verbs, same tape | nothing, no prompt |
| CF-3300, both verbs, same tape | nothing, no prompt |

🟢 The fixture and `cas_encode.py` are exonerated three ways; it is not
`CLOAD`-specific; the CF-3300 was tried because D-KWORACLE is the precedent.
⚠️ **ONE UNTESTED DIFFERENCE**: the cassette probes pass `-cassetteplayer` on the
openMSX COMMAND LINE and run on the repack machine only; these runs used the Tcl
prologue `run_cases` supports. Testing the command-line form against a REFERENCE
means going around `run_cases` — apparatus, and the reason this stopped.

## If Joost says "build it", the order is

1. **`CLOAD`/`CSAVE`'s oracle** — try `-cassetteplayer` against a reference outside
   `run_cases`; if that works, both words likely fall together, and the readback is
   already free (`Found:<name>` reaches the screen).
2. **`CSAVE`'s WAV-decode capture** — `basic_probe_cassave.py` has the decode;
   `NEEDS-LOG:` is the precedent for a per-rig capture.
3. **`INKEY$`'s injector timing** — a HARNESS change, and D-LATCH/D-LATCH2 are the
   races it must not reopen. Do this one last.

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

    /loop continue autonomously on zerobas — 🛑 READ THE STOP CONDITION AT THE TOP OF scratchpad/LOOP-RESTART.md FIRST. The "no known gap" drain ran 114 -> 3 and the last three words (CLOAD CSAVE INKEY$) are a 🙋 NEEDS-JOOST item: each needs APPARATUS rather than a row, the prices are in that item, and a tick that finds nothing else permitted should REPORT AND STOP rather than build them. Only pick work up again if Joost has ruled, or if `make tiers` shows something new at TIER 1/2/3. Run `make tiers`; recount keywords with `python3 tools/tier_table.py --keywords` — never quote a count. ⚠️ `auto` MUST STAY LAST IN SWEEP (banner comment says so). Standing rules if there IS work: full `make gates` before each commit and never commit red; an item may carry only ONE marker (todo-marker-check refuses 🙋 and 🤖 together); 🔴 AFTER ANY basic/ OR sub/ CHANGE stage zerobas-main-eu.ips/.bps WITH the commit; 🔴 `check_todo_citations.py --fix` REWRITES EVERY DOC THAT CITES A MOVED BLOCK — five files beyond TODO.md every time; read `git status --short` as a LIST; after a `--fix` re-run every gate that READS TODO.md; `rm -rf build && make basic-reloc` for any wall figure, and BACK UP build/kwsweep-verdicts.json first; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; re-run the five battery-excluded targets by hand after any slice touching a shared leaf; NEVER poll with a pattern that matches the polling command itself — use the background task's own completion notification; READ the output of every edit script.
