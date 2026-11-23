- [ ] 📌 **`file:LINE` CITATIONS ARE UNMAINTAINED AND BROADLY ROTTED — ONLY
      31% OF THEM WERE STILL CORRECT, AND NO GATE READS ONE.** Filed 2026-08-19
      by D-DEFTYPEDOC's follow-up sweep, which found a drifted anchor by READING
      and then found the class by MACHINE.
      ✅ **MEASURED REPO-WIDE 2026-08-19, and 594 REPAIRED** — see the audit
      block below. **Denominator machine-produced, not hand-listed**: 1994
      `file:LINE` citations across 924 tracked text files, into 318 distinct
      targets; **1392 resolve to a tracked file** and are decidable (the rest are
      prose-relative or name no tracked path).

      | verdict, whole tree | n |
      |---|---|
      | STILL CORRECT | **426** |
      | REPAIRABLE (unique content match) — **all 594 fixed** | **594** |
      | CONTENT GONE (cited code deleted since) | **258** |
      | AMBIGUOUS (cited line too generic to locate) | **93** |
      | out of range even when written | **10** |
      | cited a blank line / target absent at birth | **11** |

      🔴 **426 of 1392 is 31%.** The original filing said "broadly rotted" on the
      evidence of a 212-anchor window; that was a rule claiming more than its
      evidence, so the whole tree was measured rather than the phrase softened.
      It turned out to UNDERSTATE the problem.
      Restricted to the five source files `7aadd36`..`840ed59` rewrote
      (`basic/interp.asm`, `basic/kwtable.inc`, `basic/sysvars.inc`,
      `basic/usr.asm`, `sub/deftype.asm`): **212 unique citations, of which 87
      now point at a line whose CONTENT differs from what stood there before
      those two commits.** ⚠️ **THAT 87 IS AN UPPER BOUND ON DAMAGE AND A LOWER
      BOUND ON ROT** — it says the anchors moved, NOT that they were right
      beforehand; several were already stale from earlier commits (the sweep's
      own control: `basic/vars.asm:174` was 4 lines off with `vars.asm` untouched
      by any of the three commits in this window).
      🔴 **AND THE SENTENCE THAT STOOD HERE WAS WRONG.** It said sorting "these
      commits broke it" from "it was already broken" *"needs a semantic notion of
      correct that this measurement does not have"*. It does not: **`git blame`
      supplies it exactly.** Blame the CITING line for the commit that wrote the
      citation, read the target file AT that commit to learn what the author
      actually pointed at, then find where that content lives today. Decidable,
      cheap, and it splits the 87 three ways: **61 correct-when-written and
      mechanically repairable · 18 citing content DELETED since · 8 undecidable**
      (7 citing a line too generic to locate uniquely — `ret`, `ENDIF`, `ret nz`
      — plus 1 already correct, which is `0936943`'s own repaired anchor and so
      doubles as the audit's control).
      ✅ **THE 61 ARE FIXED 2026-08-19** — 89 textual occurrences across 41 files,
      since a markdown link cites the same anchor twice. Verified **61/61**: every
      repaired anchor now lands on exactly the content its citing commit pointed
      at. That is a repair WITHIN the convention, not a change to it; option (b)
      below is still open and still the human's call.
      ✅ **THEN ALL 594 REPO-WIDE** (`scratchpad/anchor_audit_all.py`): 832 textual
      occurrences across 176 files, verified **594/594** by the same invariant.
      ⚠️ **A REPAIR MAY ONLY TOUCH PROSE, AND THAT IS ENFORCED, NOT HOPED.** The
      applier locates each citation inside a COMMENT or STRING span (`tokenize`
      for Python, first `;` for asm) and refuses anywhere else — a first, blunter
      guard rejected 17 legitimate ones sitting in docstrings, so it was replaced
      with the exact one rather than left to reject good repairs. **Zero live-code
      edits**, and the ROMs stayed byte-identical through both passes.
      🔴 **AND A DOC-ONLY SWEEP CAN EDIT A GATE INPUT.** The 594 included one
      anchor inside `tools/injector-record-allow.txt` — a prose description field
      in a file `make injector-check` PARSES. Byte-identical ROMs say nothing
      about that, so the gates that READ the touched files were run afterwards and
      are green: `injector-check` (one live injector across 407 files),
      `audit-citations` (CLEAN, 798 files swept), `latch-check` **16/16**,
      `basic-reloc`, `preflight-check`, `rowshape-check`, `deadcode`, `unit-test`
      **59/59**. ⚠️ `latch-check` first returned rc=2 — an APPARATUS refusal, not a
      regression: `rm -rf build` had removed `build/zerobas-main-eu.rom` and the
      preflight refused to measure rather than report a missing ROM as a missing
      FEATURE. `make repack-machine`, and it passes. **Byte-identity is the wrong
      instrument for a sweep that touches `tools/`, and the gates were run after
      the commit rather than before it — the wrong order.**
      ⚠️ **THE 18 AND THE 8 ARE DELIBERATELY NOT TOUCHED.** The 18 point at code
      that no longer exists (`err_overflow` msgtab rows, `TMISMATCH` reads,
      `fre_illegalfn_lc`), so moving a number cannot fix them — the prose around
      them has to be re-read by whoever knows what replaced that code. The 7
      generic ones have no unique target, and a guess is worse than a stale
      number. Both lists reproduce from
      [`scratchpad/anchor_audit.py`](../../scratchpad/anchor_audit.py).
      🔴 **A SYMBOL GREP CANNOT FIND ONE.** D-DEFTYPEDOC's `ex_def_type`/
      `ex_defint` grep was exhaustive and still missed
      `docs/spec-basic-deftbl-strcode.md`'s anchor, because a drifted line number
      contains no symbol. Found only by reading the cited line.
      🔴 **AND THE RE-ANCHORING ITSELF DRIFTED, INSIDE ONE COMMIT.** `0936943`
      corrected that anchor `:66` -> `:86` from a grep taken BEFORE its own
      `sub/deftype.asm` header edit, which shifted the target by one; the write is
      at `:87`. **Re-read an anchor AFTER the last edit to the file it points
      into, not before.** Both anchors in that sentence are corrected now.
      **Options, priced, none taken**: (a) do nothing, accept prose-only anchors
      as approximate — free, and honest only if the docs say so; (b) drop line
      numbers from citations that already name the symbol — a large mechanical
      edit, no gate needed afterwards; (c) a gate that verifies an anchor lands
      near a symbol named in the citing text — fuzzy, and the false-positive rate
      is the whole question. ⚠️ Cheapest EXACT sub-gate available today: flag
      anchors that are out of range or land on a blank line (zero false
      positives, low yield — the 87 above are none of those). This is a
      convention decision, not a defect fix, so it is filed rather than taken.
      🎚️ APPARATUS — citations
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
