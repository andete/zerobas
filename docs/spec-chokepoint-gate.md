<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-CHOKEPOINT — three items asked for three checkers; they were one property

Status: **✅ SHIPPED.** 2026-08-26. `make chokepoint-check`, one unit of
`make gates`. No ROM byte moved.

---

## 1. The property, not the three subjects

Three open items each ended *"and nothing checks it"* and each proposed its own
cheap checker: the openMSX publish rule, the absolute-home-path rule, the
scratch-probe reader rule. Building three tools would have been three times the
surface for one idea:

> 🎯 **A SHARED HELPER EXISTS BECAUSE THE OBVIOUS HAND-WRITTEN VERSION WAS
> MEASURED WRONG.** Writing the obvious version again is not a style
> preference — it re-introduces a defect that has a *number* attached to it.

| rule | helper | the measurement that created it |
|---|---|---|
| **PUBLISH** | `openmsx_paths.publish()` | **412/1200 (34.3 %)** concurrent reads torn vs 0/1200 atomic |
| **ROOT** | `dirname(dirname(abspath(__file__)))` | the tree had already voted **190 to 25** |
| **READER** | the echo fence (`result_span_after_echo` / `screen_tail`) | separated from a whole-screen scan on **4/4** cases |

Each rule prints **its own denominator** — 3, 495 and 23 files. A checker that
cannot say what it looked at is the shape this tree keeps paying for.

---

## 2. 🔴 Three defects the gate found in its own bring-up

* **A regex cannot tell code from prose *about* code.** The PUBLISH rule matched
  `open(..., "w")` textually and reddened `openmsx_paths.py` **twice — on the
  comment that explains why the raw call is forbidden.** A file that documents a
  chokepoint is the single most likely place to contain its own subject. Every
  rule with an AST form now uses one.
* **The READER rule tested a NAME and reddened 24 correct gate probes.**
  `basic_probe_arylv.bracket()` calls `screen_tail(raw, "RUN")` and *then* adds
  `<NO CAPTURE>` / `<NO OUTPUT>` sentinels — a richer **wrapper** around the
  fence, which is exactly the behaviour wanted. The rule is *"reaches a fence"*,
  never *"defines a function named `bracket`"*. Wrapping a chokepoint is good;
  only **bypassing** it is the finding. 24 findings → 11.
* **A plant that lands in a file already satisfying the rule tests nothing.**
  The READER arm appended a `spans()` to `spanreader_diff.py` and did not go
  red — correctly, because that file calls the fence. The arm now builds its own
  unfenced file.

---

## 3. And two findings in the tree, one of them in my own fix

* 🔴 **`scratchpad/runline_knives.py` still hardcoded `ROOT`** after the sweep
  that fixed the other 24 reported *zero remaining*. The sweep's regex required
  exactly one space before `=`; the file says `ROOT  = pathlib.Path(...)`. **The
  AST does not care about whitespace, and that is the whole argument for it.**
* 🔴 **THE READER ITEM'S SCOPE CLAIM IS FALSIFIED.** It states *"None of the
  nine is a GATE — so the exposure is to wrong readings in this sweep's own
  record, not to a green battery."* Two **gate** probes define an unfenced
  reader: `basic_probe_direct_ctrl.py` and `basic_probe_time.py`. On reading
  them both are *safe* — they use `#…#` markers, so `result_span`'s `[` never
  applies, and both handle the echo explicitly and say so — but the item's
  reason for not worrying was wrong even though its conclusion held.

### 3.1 🔴 And the ROOT fix itself broke a DIFFERENT gate

`make injector-check` went RED on the very battery that first ran this gate.
`scratchpad/i1_input_char2.py` is one of three **FROZEN characterization
RECORDS** pinned by digest in `tools/injector-record-allow.txt` — *"a RECORD's
whole claim is that it is FROZEN"*. It composes the pre-D-LATCH injector body
that `make latch-check` row A requires to MANGLE, and `basic/PROVENANCE.md`
cites it as evidence of what the apparatus **was**. The portability sweep
rewrote its `REPO` along with 23 others and silently destroyed that claim.

Restored to its frozen contents and pinned here instead: the portability defect
in it is real, and it is **outranked** by the freeze.

> 🎯 **A MECHANICAL FIX CAN BE CORRECT BY ITS OWN RULE AND STILL BREAK A
> DIFFERENT INVARIANT.** No sweep for "hardcoded paths" could have known this
> file was load-bearing *as bytes*. Only the other gate caught it — which is the
> argument for running the whole battery after a sweep that touched 24 files,
> not just the gate you are building.

---

## 4. Falsification — one arm per rule, both senses, every run

`--selftest` runs before the gate proper on every invocation. It copies the
tree, requires the copy **GREEN**, then plants one violation **per rule** and
requires exactly that rule **RED**. Exit **2** (instrument fault) if any sense
fails. *A gate with three rules needs three arms: proving one proves nothing
about the others.*

---

## 5. Pins

`tools/chokepoint-allow.txt`, `RULE:path  reason`. **They may shrink, never
grow, and a pin that stops being a finding is reported RED as a STALE PIN** — an
exception nobody can retire is indistinguishable from a rule nobody enforces.
Eleven today: the two `#`-marker gate probes, and nine one-shot sweep
instruments whose printed output *is* the D-TODOSWEEP record, so editing them
would change what that record is reproducible from. Retire those by deleting the
probes when the record is superseded, not by rewriting them.

---

## 6. What this does NOT establish

* **It does not check that a helper is CORRECT**, only that it is reached.
* **PUBLISH is scoped to `tools/install-*.py` + `openmsx_paths.py`.** A publish
  into the shared tree from anywhere else is invisible to it. That is the
  bargain that made the rule possible at all: the filed obstacle was that
  `find_user()` builds the path at runtime, so no textual sweep can resolve it —
  constraining the *file set* is what replaces resolving the *path*.
* **ROOT sweeps `.py` by AST and `.sh` by regex**, and `.log`/`.out` captures
  not at all: they hold 343 of the 372 raw hits, and an absolute path inside a
  captured log is evidence of what ran, not a portability bug.
