<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-TODOSPLIT — the pickup list is now the length of the work that is left

Status: **✅ SHIPPED.** 2026-08-26. `TODO.md` **12577 → 3722 lines**;
[`docs/TODO-done.md`](TODO-done.md) holds the closed record. No ROM byte moved.

---

## 1. The split rule is the VERDICT, not the checkbox

The obvious rule — *move every `- [x]`* — was **unsafe until this morning**.
D-TODOSWEEP found **30 of its 178 subject blocks were live residuals written up
inside a closed block**; `## Open — standing residuals` exists precisely because
a residual can be lost that way. So the rule is:

> a top-level block moves **iff** it is `- [x]` **and** its D-TODOSWEEP verdict
> does not begin `LIVE`.

**Four closed blocks stayed behind** on that rule — the arc-timing item
(`T-8462D6`), direct-mode traps (`T-48AC8B`), `NAME`'s non-string filename
(`T-B42E11`, reopened by the sweep's own last tranche) and the `.` pseudo-line
residuals (`T-2148BA`). Had the split been done before the sweep, all four would
have been archived as finished.

| | blocks | lines |
|---|---|---|
| moved to `docs/TODO-done.md` | **233** + 3 whole sections | 8829 |
| stayed — open | 111 | 2963 |
| stayed — closed but verdict LIVE | **4** | 177 |

Three sections moved **whole** because their items had all gone and the
remaining prose was itself a done-record (`Phase 1 record`, `Done — Phase 1`,
`Done — storage transports`). They are named **explicitly** in the tool, not
detected: *"has no surviving items"* is also true of `Phases at a glance`,
`Status today` and `Beyond`, and a heuristic would have moved the charter out of
the charter file.

---

## 2. Lossless by construction, and by check

[`tools/split_todo_archive.py`](../tools/split_todo_archive.py) emits every
source line to exactly one of the two files, in order, and records an
`old line -> (file, new line)` map. `--apply` **refuses to write** unless
reconstructing the original through that map is byte-identical to the source,
and then **repoints every citation from that same map, in the same process**.

🔴 **THE REPOINTER WAS A SECOND TOOL, AND THAT WAS THE DEFECT.** Handing the map
between two processes needed a temp file, which `make temp-root-check` correctly
refused — `probe_tmp` owns a per-process directory and gives it back at exit, so
the handoff had no lifetime. But the lint was the smaller half: the split and the
repoint are **one operation**, and running them as two is exactly how the first
pass shipped a repoint that rewrote link labels and left their targets. Merged.
Section headings are mirrored into the archive as
`## From `TODO.md` § …` so a moved block is still read under the phase it
belonged to — **a block without its heading is a block without its subject.**

---

## 3. 🔴 42 citations pointed at line numbers, and the split moved every one

A bare `TODO.md` line reference in another doc is a rotting citation the moment
`TODO.md` is edited; this change moved 8829 lines at once. All 42 were repointed
**from the map, not by hand**, and each gained the block's **content-derived
id** — a block that stayed keeps the `TODO.md` spelling at its new line, a block
that moved is respelled onto `TODO-done.md`:

    TODO.md:<old>      ->   TODO.md:<new> (T-529ABE)          stayed
    ../TODO.md:<old>   ->   TODO-done.md:<new> (T-FE1732)     moved

⚠️ **THE PLACEHOLDERS ARE NOT COYNESS.** Written out as real numbers, this
example is indistinguishable from a live citation — and it was: the gate below
read the illustration as data and `--fix` cheerfully rewrote half of it to a
line the example was never about. An example that looks like its subject will be
processed like its subject.

**The line is for a human's click; the id is what the check trusts.** The id is
`tools/todo_inventory.py`'s digest of the block headline — it survives reflow,
renumbering, and moving the block to the other file, which is the entire reason
the sweep adopted it after positional ids rotted on the very next edit.

### 3.1 The repointer's first pass shipped the bug the gate now catches

The first cut matched a bare `TODO.md:NNN` and its lookbehind excluded a
preceding `/` — so it **skipped every `../TODO.md:NNN`**, which is the *href*
half of every markdown link written from `docs/`. It rewrote the **label** and
left the **link**:

    [`TODO.md:<new line>`](../TODO.md:<old line>)   <- reads right, goes elsewhere

Caught by inspecting the leftovers rather than the count, reverted, and redone
against `(\.\./)?TODO\.md:` — and the check below now has an arm for exactly
this: **an href is verified against the label beside it, and a link whose two
halves disagree is RED.** 9 citations are link targets checked that way.

---

## 4. The gate — `make todo-citation-check`

[`tools/check_todo_citations.py`](../tools/check_todo_citations.py), a step of
`basic-reloc` and a unit of `make gates`. <1 s, read-only, no emulator.

* **RED** when a cited line no longer sits inside the block whose id it names —
  and the message says where that id *is* now.
* `--fix` rewrites a drifted line number from the id; `--annotate` attaches a
  missing id from the block currently at that line. Both idempotent.
* **The id-less count is printed and the citations NAMED**, never passed over: a
  check reporting 100 % while a third of its subject is uncheckable is the
  0/0-ALL-CONVERGED shape. It is currently **0** — 33 verified by id, 9 by
  label/target agreement, 42 total.

### 4.1 🔬 Falsified by planting, both senses, every run

`--selftest` runs before the gate proper on every invocation. It copies the real
tree, confirms a real citation is **GREEN** on the copy, then plants a drift in
that same citation and requires **RED**. A red arm that passes because it never
fired is not an arm; exit **2** (instrument fault) if either sense fails, and
exit 2 also if there is no green citation to plant against at all.

### 4.2 🔴 Two defects the gate found in its own first run

* **It reddened five correct citations.** `resolve()` was relative-to-the-citing-
  file only, so a bare `TODO.md` in a probe docstring under `scratchpad/`
  resolved to a sibling of that probe — a file which has never existed. The
  check was wrong about the convention, not the repo. Now: relative first, then
  repo root.
  🎯 **AND WRITING THAT SENTENCE THE OBVIOUS WAY REDDENED A DIFFERENT GATE**:
  spelling the non-existent sibling out as a path made `citation-check` (shipped
  this same day) report a dangling citation, correctly — *"the doc must stop
  naming a path"*. Described, not spelled.
* **It called 12 citations uncheckable that were not.** `block_at` looked only at
  depth-0 blocks, and those 12 point **into nested items** — which is where the
  detail lives. A nested block has an id too. Now the deepest covering block
  wins, and all 12 are verified.

---

## 5. What this does NOT establish

* **The archive is not re-verified.** It is the sweep's verdicts, moved. If a
  block there turns out to be live it belongs back in `TODO.md` as an open item
  — *moved*, not re-opened in place.
* **The gate checks citations, not prose.** A doc that describes a TODO item
  wrongly without citing a line is invisible to it, as it is to every other gate
  here.
* **`- [x]` blocks in the archive are not re-checkable by the sweep's own
  denominator**: `tools/todo_inventory.py` reads `TODO.md` by default. Pass
  `--file docs/TODO-done.md` to inventory the archive.
