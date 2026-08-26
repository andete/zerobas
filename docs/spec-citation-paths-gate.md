# A committed doc may not cite a `scratchpad/` path the repo does not contain

**D-CITEPATH, 2026-08-26.** Gate: `tools/check_citation_paths.py`, a step of
`make basic-reloc` (standalone alias `make citation-check`). Falsification:
`scratchpad/citepaths_falsify.py`, 12 arms.

Filed by D-KNIFEGUARD ([`TODO.md`](../TODO.md)), which hit the class while
patching the knife runners and discovered that `scratchpad/` is **tracked on
purpose** — knives, probes, characterisations and run summaries are the evidence
a spec's findings rest on. A citation that dead-ends means that spec's evidence
cannot be re-run by anybody.

## 1. The rule, and why it is anchored on the PATH

> For every `scratchpad/…` path named by a **committed** doc,
> `git ls-files` must find it.

Committed, twice over: the corpus is what `git ls-files` reports (an in-progress
doc citing a script staged in the same commit is not a dangling citation), and
the property under test is what a **fresh clone** gets.

🔴 **IT MATCHES THE PATH, NOT THE BASENAME, AND THE FILED ITEM IS WHY.**
D-KNIFEGUARD's first detector was basename-anchored and flagged one file whose
only "citation" was the TODO sentence listing it as **not** in the class. *A
checker whose corpus contains the note describing its exception will flag the
exception.* Requiring the prefix costs nothing and removes it:

> **PROSE NAMES A FILE. A CITATION NAMES A PATH.**

That single distinction is what lets a doc — including this one — discuss the
class at all. The pattern deliberately excludes `<` and `>` from its character
class, so the placeholder form every such doc has to write is not itself a
citation.

🎯 **AND THE SHAPE BIT TWICE MORE INSIDE THIS SLICE.** `fixpoint8000-msx1-sweep.md`
cited a runner and said *"(throwaway, not committed)"* in the same sentence — the
doc knew, and named a path anyway. And the first draft of the `p1scout.py`
repoint below wrote *"promoted to `tools/` from `scratchpad/…`"* — a fix that
restated the broken path while explaining it. **Three instances, one shape.**

## 2. Three finding classes, because there are three remedies

| class | state | remedy |
|---|---|---|
| `UNTRACKED` | on disk, trackable class, not committed | `git add` |
| `IGNORED` | on disk, `.gitignore` excludes its class | no `git add` fixes it — the citation or the ignore rule has to give |
| `GONE` | not on disk at all | a **judgement**: repoint, restore, or stop naming a path |

`GONE` splits again on `git log --all`: a path that was once committed can be
**repointed**; one that never was **cannot be restored by anyone**. That is a
worse hole than an untracked file — an untracked script still exists for its
author, a deleted one exists for no one.

## 3. The denominator, measured — and bigger than the filed one

| corpus | cited paths | dangling |
|---|---|---|
| filed 2026-08-26 (`docs/**` + `TODO.md`) | 165 | 9 |
| **measured here (every committed `.md`)** | **238** | **27** |

🔴 **THE FILED DENOMINATOR WAS A SCOPE CLAIM.** It swept `docs/**` and missed
`disk/docs/` and `tape/docs/` — 6 further `GONE` paths and 4 untracked ones lived
there. The rule was right; the corpus was hand-listed. The gate's corpus is
`git ls-files '*.md'`, so it cannot be narrower than the repo.

The 27, remediated:

* **15 `GONE`.** 14 were **never committed** (`git log --all` empty), so nothing
  can restore them; their docs now name the file in prose and say out loud that
  it is not in the repo. 1 — `p1scout.py` — *was* committed and moved to
  [`tools/p1scout.py`](../tools/p1scout.py) at `6f8ac0f`; repointed.
* **4 `IGNORED`.** Per-slice battery wrappers under the `scratchpad/*.sh` ignore
  rule, whose comment already reasons that ad-hoc gate drivers are per-session by
  design. Two are cited beside their `.out`, and `.out` **is** a tracked class —
  so the result already ships; only the scaffolding did not. One hardcodes an
  absolute `/Users/joost/…` path and so would not run in a clone even if
  committed. Decision (user, 2026-08-26): the citations give, the ignore rule
  stands.
* **8 `UNTRACKED`.** 7 are evidence and are now committed. The eighth was
  `scratchpad/gate_logs/…` — and committing it would have been **wrong**:
  `tools/run_gates.py` `rm -rf`s that directory at the start of every battery.
  The `scratchpad/*.log` ignore rule is **shallow** and never covered the
  subdirectory, so a per-run artifact looked trackable. `.gitignore` now covers
  it and the doc quotes the text instead of pointing at the file.

## 4. Falsification — `scratchpad/citepaths_falsify.py`, 12/12

Plants land in a real committed doc and are restored from an `atexit` hook
registered **beside the read**, so an arm that dies mid-run cannot leave the tree
planted (D-KNIFEGUARD).

* **RED (3):** one plant per class — `GONE`, `IGNORED`, `UNTRACKED` — each
  checked for its class label, not merely for rc 1.
* **GREEN (4), the load-bearing half:** a bare basename in prose (the shape that
  produced the false positive this rule exists to avoid), the `<name>` placeholder,
  a bare `scratchpad/` directory reference, and a path under another directory.
  Without these, a red arm proves only that *something* went red.
* **INSTRUMENT (3):** the self-test table emptied to `[]` → exit 2, not a clean
  `0/0` (`audit_citations.py` shipped four tables in exactly that state for the
  tool's whole life); the RULE broken while the table stands → exit 2; the corpus
  truncated → exit 2, not *"all resolve"*.
* **CONTROLS (2):** the tree green before, and byte-identical and green after.

🔴 **TWO INSTRUMENT ARMS PASSED FOR THE WRONG REASON, AND ONLY THE THIRD'S
FAILURE EXPOSED THEM.** The blinded copies were first written to a temp dir — and
the subject derives its repo root from `__file__`, so they ran their `git`
queries against `/tmp`. The two self-test arms passed anyway, because they exit
before ever reaching git. The corpus arm needs a working corpus, so it failed,
and that is the only reason the siting bug was found. **A green arm on a
mis-sited instrument is not evidence; it is a coincidence about where the exit
lives.**

## 5. What it does not do

* It does not check that the cited script still **runs**, or that it measures
  what the doc says. A tracked path resolves; that is all this claims.
* It does not police citations to any other directory. `probes/`, `tools/` and
  `tests/` are tracked wholesale, so the class cannot arise there the same way —
  unmeasured, not proven absent.
* It says nothing about **hardcoded absolute paths** inside a tracked script; one
  of the four `IGNORED` drivers has one, which is a separate unmeasured class
  (filed in [`TODO.md`](../TODO.md)).
