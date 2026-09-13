# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand (rewritten 2026-09-13)

Recount everything — never quote a number from this file.

* 🟢 **THE TAPE TIER 1 IS CLOSED.** A tape zerobas saves now loads on a real MSX;
  the interop matrix is green in all four cells with the `[P9]` prompt witness.
* 🟢 **THE DRAIN IS DOWN TO `CSAVE` AND `INKEY$`** — `CLOAD` was attributed by
  D-KWTAPE2's `NEEDS-TAPE:` rig. The whole kwsweep is `DIVERGENT=0`.
* The one remaining TIER 1 is the keyword-completeness umbrella itself, and its
  exit criterion is that list being EMPTY. Run `make tiers` and
  `python3 tools/tier_table.py --keywords`.

## What the tape arc cost, and the rule it earned

Four slices went into the WAVEFORM — duty cycle, tone periods, leader lengths,
three refuted hypotheses — when the actual defect was **seven missing `$00`
bytes** at the end of the data block. The oracle had been sitting in
`cas_encode.build_cas_basic` the whole time: our own encoder already encoded the
right answer and no probe had ever diffed the WRITER against it.

➡️ **WHEN A CONSUMER HANGS, DIFF THE BYTES BEFORE THEORISING ABOUT TIMING.** A
format is finite and checkable; timing is an open-ended space that will always
absorb one more hypothesis. Both causes produce the identical symptom, and I
ranked them by which was more interesting rather than which was cheaper to check.

🔴 **AND TWO OF MY OWN REFUTATIONS WERE RETRACTED IN THE SAME ARC**: "leader
length is dead" had been measured on a DIFFERENT build (the lopsided writer,
where the leader was not the binding constraint), and the between-tone-outlier
histogram never predicted the outcome — the cleanest recording ever produced read
the WORST. **A refutation is only as general as the build it was measured on.**

## The next slice — `INKEY$`, the last word on the list

`CSAVE` is attributed (D-KWTAPE3: `NEEDS-BLANKTAPE:`, a capture that decodes the
recording back to bytes). **`INKEY$` is all that is left**, and it was always
named the one to do last: it needs the key injector's TIMING exposed to a row,
and it must not reopen D-LATCH/D-LATCH2. Read those two before designing the row.

⚠️ **THE TAPE ROWS COST FOUR WRONG READINGS BEFORE ONE RIGHT ONE**, every one of
them GREEN or honestly UNREADABLE, never a wrong answer: an empty capture, a tail
appended as ASCII to a capture that was never split, a tail appended as HEX to a
capture that comes back DECODED, and a missing fixture agreeing with a missing
fixture. **Read what the row SAW, not the verdict it printed.**

## Five ways a kwsweep row can pass while seeing NOTHING

Every one of these SHIPPED a green row before being caught, and mode 1 nearly
shipped again this session as `CSAVE`:

1. **A readback that never moves** — `KEY` via CRTCNT read 24 with `KEY OFF` and
   24 without. `scratchpad/kwdrain_discrim.py`.
2. **A predicate true of ZERO** — an absent keyword parses as an undefined array
   and reads 0, so `INP(&HA8)>=0` passed exactly like the real answer. The same
   trap hides in an ARGUMENT: `BASE(0)` and `DSKF(0)` are honestly 0.
3. **A crunch that names no keyword** — `tier_table`'s WORD regex keeps a
   trailing `$`, so `sprite$(0)=…` credited nothing while reporting SUPPORTED.
4. **An audit that re-implements the consumer's parser** — IMPORT
   `tier_table.kwtable_keywords()`; expect exactly ONE row crediting nothing.
5. **A row that leaves the machine in a MODE THAT EATS THE NEXT CASE** — `AUTO`
   scored itself correctly and took 21 unrelated rows down with it. After adding
   any row, read the WHOLE sweep summary, not just the new verdict.

Plus: **a FIX silently un-attributes its own keyword** — attribution comes from
OPEN items, so leave a row behind when closing a defect.

## 🔴 Re-verify every blocker before believing it

**TEN FOR TEN**, plus the two retractions above. The display verbs' "cannot take a
row", the multi-line words', the CF-3300 NO-ORACLE claim, the disk fixture,
`SCREEN`'s mode, `KEY`'s missing constant, `USR`'s "machine code to call",
`WAIT`'s port, and the printer log `LPOS`/`LPRINT`. Re-verifying has been cheaper
than the work it was hiding every single time.

⚠️ **A WAITER THAT MATCHES ITSELF**: `until ! pgrep -f run_gates.py; do sleep;
done` in the background NEVER EXITS — the waiter's own command line contains the
pattern. Use the background task's completion notification.

## Two staging traps

* **After any `basic/`, `sub/` or `tape/` change the build refreshes the patch
  pairs** — stage them WITH that commit; `patch-freshness-check` can only see the
  omission ONE COMMIT LATER, and it names the exact `make` target.
* **`check_todo_citations.py --fix` rewrites EVERY document citing a moved TODO
  block**, five files beyond TODO.md every time. It compares the WORKING TREE, so
  it is green before and after while a stale citation ships in HEAD.

## Open for Joost — do not pick up

* The `CONT` item (TIER 5): inside a program zerobas prints `Can't CONTINUE`
  where the reference prints `Can't CONTINUE in 10`. A DELIBERATE choice recorded
  at `basic/program.asm:1188`.
* Ranking the remaining apparatus blockers (AUTO's line-entry mode, keystroke
  injection, step (c)).

## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `ad7334af`. Recount everything — never quote a number
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

## Where things stand — JOOST RULED, and the oracle work found a TIER 1

Joost answered the 🙋 item with **"make the 3 missing oracles"**. The first one
paid immediately and not as expected: building it exposed a TIER 1 defect and
retired the 🙋 blocker for `CLOAD` entirely.

* 🟢 **`CLOAD`'s oracle is DONE.** `omsx_repl.run_cases` takes `cassette=` (the
  `-cassetteplayer` seam every cas probe used and none could reach through the
  harness). The VG-8020 reads a clean-room `.cas` — the earlier "no oracle" was a
  FIXTURE that was itself the defect. A `NEEDS-TAPE:` kwsweep rig is now small.
* 🔴 **NEW TIER 1: a tape zerobas writes cannot be read by a real MSX.** Filed with
  the full matrix; `CSAVE`'s kwsweep row should wait for the fix, because the
  defect IS its subject.
* `INKEY$` is untouched — still the injector's timing, still the one to do last.

## The next slice — the tape-writer COMPENSATION, and it is well specified

**MECHANISM CONFIRMED**: the per-bit loop overhead lands inside the LAST
half-period of every bit.

| bit | VG-8020 | zerobas |
|---|---|---|
| `0` (one low-tone cycle) | `18 19` | `18` **`20`** |
| `1` (two high-tone cycles) | `9 9 9 9` | `9 9 9` **`11`** |

Inside a `1` bit the FIRST cycle is clean, so it is the BIT boundary, not
`cas_cycle` (a tight `djnz` pair, constant by construction). The stretch is ~2
samples ≈ 160 T-states ≈ 12 `djnz` iterations against `CAS_HHALF` = 50 — about a
quarter of a short half, enough to push `9` to `11`, above the midpoint between the
tones and unclassifiable by a threshold derived from the leader.

➡️ **THE FIX**: shorten the trailing low half of each bit by the per-bit overhead
so the total stays correct — a `cas_cycle_last` variant taking a reduced count,
with the leader loop keeping the uncompensated one (the leader measures clean).
⚠️ **Byte cost unmeasured** — the tape ROM is its own region; price it first.
⚠️ **FOUR HYPOTHESES ARE ALREADY DEAD** and are in the item: leader length (rebuilt
to the reference's own), inter-block silence (spliced), leading silence (spliced),
mount form. Do not re-run them.
🎯 **THE TEST IS DECISIVE AND WRITTEN**: `scratchpad/kwdrain_wavread.py` (the VG
reads a tape zerobas wrote, with a prompt witness) and
`scratchpad/kwdrain_wavhist.py`, which must come back CLEANLY BIMODAL — nothing
between the tones, which is what the reference produces.

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

    /loop continue autonomously on zerobas — 🔴 TIER 1 BEFORE ANYTHING ELSE. Read scratchpad/LOOP-RESTART.md FIRST, then the item's own block in TODO.md to its END. Run `make tiers`; recount keywords with `python3 tools/tier_table.py --keywords` — never quote a count. THE LAST TIER 1 IS THE KEYWORD-COMPLETENESS UMBRELLA and its exit criterion is the "no known gap" list being EMPTY. IT IS DOWN TO ONE WORD: INKEY$. THIS SLICE: attribute INKEY$ and CLOSE THE UMBRELLA. It was always named the one to do last because it needs the key injector's TIMING exposed to a kwsweep row — read D-LATCH and D-LATCH2 in TODO.md FIRST and do not reopen them. The four rigs that already exist are the design vocabulary: NEEDS-DISK: and NEEDS-PRINTER: mount a DEVICE, NEEDS-LOG: and NEEDS-BLANKTAPE: are CAPTURES that read an artefact the screen never shows. If INKEY$ needs a fifth shape, say which of those it is. ⚠️ EVERY NEW ROW MUST CLEAR THE FIVE SILENT-FAILURE MODES listed in LOOP-RESTART.md, and the tape rows cost FOUR wrong readings before one right one — every one of them GREEN or honestly UNREADABLE, never a wrong answer: an empty capture, a tail appended as ASCII to a capture that was never split, a tail appended as HEX to a capture that comes back DECODED, and a missing fixture agreeing with a missing fixture. READ WHAT THE ROW SAW, NOT THE VERDICT IT PRINTED, and after adding rows read the WHOLE sweep summary. 🎯 THE RULE THE TAPE ARC EARNED: when a consumer hangs, DIFF THE BYTES AGAINST OUR OWN ENCODER BEFORE THEORISING ABOUT TIMING — four slices went into a waveform when the defect was seven missing $00 bytes. 🔴 RE-VERIFY EVERY BLOCKER BEFORE BELIEVING IT, and note that TWO refutations were themselves retracted this session — a refutation is only as general as the build it was measured on. Standing rules: full `make gates` before each commit and never commit red; STAGE EVERYTHING BEFORE THE BATTERY AND WRITE NOTHING WHILE IT RUNS; an item may carry only ONE marker; 🔴 `check_todo_citations.py --fix` REWRITES EVERY DOC THAT CITES A MOVED BLOCK — five files beyond TODO.md every time; read `git status --short` as a LIST; after a `--fix` re-run every gate that READS TODO.md; `rm -rf build && make basic-reloc` for any wall figure, and BACK UP build/kwsweep-verdicts.json first; `test -e <path> && exit 1` before any `cat >` heredoc; stage explicit paths, `git add -A` banned; commit message to a FILE with `git commit -F`; commit AND push after each fix without asking; never write a tracked file while a battery runs; re-run the five battery-excluded targets by hand after any slice touching a shared leaf; NEVER poll with a pattern that matches the polling command itself — use the background task's own completion notification; READ the output of every edit script.
