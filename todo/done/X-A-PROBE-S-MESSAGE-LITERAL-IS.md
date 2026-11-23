- [x] ⚠️ **A PROBE'S MESSAGE LITERAL IS EITHER AN ASSERTION OR A CLASSIFIER
      ✅ **CLOSED 2026-09-05.** Both halves are gated: `make needle-case-check` passes 1-2 (tables discovered as case-folded) and pass 3 (the table-free one-off), 8 arms, two of which go green under the old loose rule. Nothing outstanding.
      NEEDLE, AND THEY LOOK IDENTICAL.** Filed 2026-08-02 by D-MSGEXACT §6b,
      which silently broke **30 comparisons across 9 files** and every one failed
      by **agreeing**: a needle matched against an already-`.lower()`-ed screen
      string cannot match if it is capitalised, so the row reclassifies from
      `error:<phrase>` to `value` instead of going red.
      ⚠️ `badfnum` was invisible to two rounds of auditing — it has no `.lower()`
      at all; it `setdefault`s its needle into an `ERR_CLASSES` dict **imported
      from `lof`**. The gate caught it (12 oracle drifts), not the audit.
      ~~Worth a lint: a capitalised message literal reaching a case-folded
      comparison, across module boundaries. Until then the vocabularies carry
      explicit "MUST STAY LOWERCASE" comments
      ([`basic_probe_kwsweep.py`](probes/basic/basic_probe_kwsweep.py) has the
      worked one).~~
      ✅ **BUILT AND GATED 2026-09-05 (D-NEEDLECASE) — `make needle-case-check`,
      collected in the battery (33/33 static).**
      🎯 **THE TABLES ARE DISCOVERED, NOT LISTED**, because a hand-kept list of
      "vocabularies that must stay lowercase" is precisely the thing that already
      failed: nobody adds the entry for the module they are about to break. Pass
      1 finds every table CONSUMED case-folded — a `for … in TABLE` whose loop
      variable is then tested `in <x>.lower()` — and pass 2 flags a capitalised
      string written into one of those names ANYWHERE, which is what crosses the
      module boundary that hid `badfnum`. Found **3 tables** with no help:
      `ERR_CLASSES` (the one that broke, consumed in two files), `ERROR_WORDS`
      (this entry's own worked example) and `_ERR_TOKENS`. **46 needles, all
      lowercase — clean today.**
      🔴 **AND ITS FIRST RUN REPORTED 19 FINDINGS, ALL FALSE** — the dict KEYS
      (`'SYNTAX'`, `'IFC'`, `'FNF'`…), which are class labels matched against
      nothing. The walker took the whole dict where it should have taken only the
      values, **while carrying a comment asserting that keys were already
      excluded**. A needle table's keys are uppercase BY CONVENTION, so the bug
      produced a full, tidy, entirely wrong report
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      🔴 **The selftest PASSED with that bug present**, because its fixture had an
      uppercase key AND an uppercase needle and it only asserted "some uppercase
      literal was seen" — it agreed for the wrong reason. There is now an arm
      whose fixture has uppercase KEYS and lowercase NEEDLES and requires ZERO
      findings; reverting the walker makes that arm fail, verified.
      ⚠️ **SCOPE, stated in the tool's own output**: it checks needles in tables
      discovered as case-folded. A one-off `'Foo' in x.lower()` is a different
      shape — **measured separately at 0 occurrences today**, but not gated.
      🟢 **NOW GATED TOO — PASS 3 (D-ONEOFFCASE, 2026-09-05).** *"0 today,
      measured separately"* is a hand measurement with nothing keeping it at 0,
      which is the same shape as every other filed figure in this file. Re-run
      before extending: still **0**. Pass 3 compares a literal against an
      expression already `.lower()`/`.upper()`-ed **with no table between them** —
      `if "Type mismatch" in txt.lower():` can never be true and the branch
      simply never runs, so the row reclassifies instead of going red, exactly
      like D-MSGEXACT's 30.
      🔴 **AND AN EMPTY PASS IS INDISTINGUISHABLE FROM A BLIND ONE**, which is the
      trap this whole entry is about: "0 findings" from a working pass reads the
      same as "0 findings" from a pass that cannot see. **Eight arms plant the
      shape** — plain, negated, equality with the literal on either side, the
      `.upper()` mirror, and four that must NOT fire (a correctly-cased literal
      either way, no folding at all, and a `.lower(x)` that takes an argument and
      is therefore somebody else's method). K-OC1 disables the `.lower()` arm and
      **three of them go red**, verified rather than asserted
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      ➡️ **The last open half of this entry is closed.**
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
