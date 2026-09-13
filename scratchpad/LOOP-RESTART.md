# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `1a777438`. Recount everything — never quote a number
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

## The next slice — `CLOAD`, and the rig it needs ALREADY EXISTS

**THREE words: `CLOAD CSAVE INKEY$`.**

🔴 **FIRST, A CORRECTION I OWE THE NEXT READER: "nothing in this tree plays a
tape" was MY claim, filed twice, and it is FALSE.** The measurement was a grep for
`cassetteplayer insert` under `probes/`, which is not how this tree mounts a tape:
it uses the openMSX command-line flag **`-cassetteplayer <file>`**, in
`basic_probe_cas_options.py`, `basic_probe_cas_ascii.py` and
`basic_probe_cas_verbs.py`, all of which LOAD programs off tape today. And
**`probes/lib/cas_encode.py` is the encoder** — `build_cas_basic(name, program)`
synthesises a playable `.cas`. Eleven of thirteen stale blockers tonight were
inherited; this one I wrote. **A blocker is only as good as the string it was
measured with.**

➡️ **SO THE TAPE PAIR IS BLOCKED ON A READBACK, NOT A RIG:**

* **`CLOAD`** replaces the program and returns to COMMAND LEVEL, so nothing in the
  same case can observe it — exactly `LOAD`'s shape, and `LOAD` is attributed by
  an OPEN ITEM rather than a row. Two routes, both real: (a) a capture that reads
  the STORED PROGRAM back (Layer 1 already uses `("stored_line", TXTTAB)`, so the
  capture exists — it has never been used by Layer 2), or (b) an open item naming
  what `basic_probe_cas_options.py` already measures.
  🎯 **(a) IS THE SAME SHAPE `NEEDS-LOG:` TOOK FOR `LLIST`** — a per-rig CAPTURE,
  with the CLASS from the screen and the TEXT from the other half. That worked.
* **`CSAVE`**'s output is the recording, which needs the WAV decode
  `basic_probe_cassave.py` already does — a third capture, same shape.
* **`INKEY$`** is the one genuine keyboard block: the injector's TIMING, a harness
  change, and it must not reopen D-LATCH.

⚠️ **WHEN THESE THREE ARE THE ONLY ONES LEFT, THE QUESTION CHANGES** from "how" to
"is the capture worth it" — and that is Joost's to answer, with the prices above
on the table, not a decision to take silently in a loop tick.

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

    /loop continue autonomously on zerobas — 🔴 TIER 1 BEFORE ANYTHING ELSE, then drain "no known gap" to ZERO (Joost's 2026-09-12 ruling, which outranks TIER 4). Read scratchpad/LOOP-RESTART.md FIRST, then the item's own block in TODO.md to its END. Run `make tiers`; recount keywords with `python3 tools/tier_table.py --keywords` — never quote a count. THREE WORDS LEFT: CLOAD CSAVE INKEY$. THIS SLICE: `CLOAD`, and the rig it needs ALREADY EXISTS — `-cassetteplayer <file>` mounts a playable tape (basic_probe_cas_options.py, basic_probe_cas_ascii.py, basic_probe_cas_verbs.py all load off tape today) and probes/lib/cas_encode.py's `build_cas_basic(name, program)` synthesises the `.cas`. 🔴 I FILED "nothing in this tree plays a tape" TWICE AND IT IS FALSE — the grep was for `cassetteplayer insert`, which is not how this tree mounts one. What actually blocks CLOAD is a READBACK: it replaces the program and returns to COMMAND LEVEL, so nothing in the same case observes it — exactly LOAD's shape. Two routes, both real: (a) a per-rig CAPTURE that reads the STORED PROGRAM back — Layer 1 already uses `("stored_line", TXTTAB)`, so the capture exists and Layer 2 has never used it, and this is the same shape `NEEDS-LOG:` took for LLIST (class from the screen, text from the other half); or (b) an open item naming what basic_probe_cas_options.py already measures. Pick ONE and say why. ⚠️ Prove the readback MOVES before keeping the row, clear the FIVE silent-failure modes in LOOP-RESTART.md, and after adding rows READ THE WHOLE SWEEP SUMMARY. ⚠️ `auto` MUST STAY LAST IN SWEEP — a banner comment says so; anything appended after it inherits the line-entry poisoning. 🎚️ WHEN ONLY CLOAD/CSAVE/INKEY$ REMAIN, THE QUESTION IS NO LONGER "how" BUT "is the capture worth it" — that is Joost's call, so put the prices in TODO.md and say so rather than deciding it in a loop tick. Standing rules: full `make gates` before each commit and never commit red; 🔴 AFTER ANY basic/ OR sub/ CHANGE stage zerobas-main-eu.ips/.bps WITH the commit; 🔴 `check_todo_citations.py --fix` REWRITES EVERY DOC THAT CITES A MOVED BLOCK — five files beyond TODO.md every time; read `git status --short` as a LIST; after a `--fix` re-run every gate that READS TODO.md; `rm -rf build && make basic-reloc` for any wall figure, and BACK UP build/kwsweep-verdicts.json first; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; re-run the five battery-excluded targets by hand after any slice touching a shared leaf; NEVER poll with a pattern that matches the polling command itself — use the background task's own completion notification; READ the output of every edit script.
