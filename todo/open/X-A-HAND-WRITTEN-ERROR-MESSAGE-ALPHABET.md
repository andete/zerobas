- [ ] 🔬 **A HAND-WRITTEN ERROR-MESSAGE ALPHABET IS A BLIND SPOT, AND 19 PROBES
      CARRY ONE.** Found 2026-09-02 by D-LSETTM
      ([`docs/spec-basic-lsettm.md`](../../docs/spec-basic-lsettm.md) §5).
      `basic_probe_lrvar.bracket()` classifies a screen against a literal list of
      error strings; anything absent reads `<NO OUTPUT>`, which routes to
      *"without a reference"* — **a sentence about the MACHINE, for a fault in
      the PROBE.** Three new rows whose answer is `Missing operand` (ERR 24, not
      in the list) were reported as unscored while BOTH machines had printed it.
      ✅ **FIXED IN `lrvar` ONLY**: alphabet re-derived from `sub/errmsg.asm` +
      main's `err_msgtab` (15 → 37), and an unclassifiable NON-EMPTY screen now
      returns `<UNREADABLE: …>`, deliberately **not** a sentinel, so the gate
      scores it RED and carries the text. K-LT3 plants the omission back and the
      loud path fires. 27/27 scored, 0 without a reference.
      📏 **THE CLASS IS 19 PROBES** (`grep -rln '"Type mismatch"' probes/`), and a
      sweep of every message literal against the ROM source found the SAME
      casing defect in **four more**: `fldary`, `lvfix`, `lvsites`, `tgtspc` all
      said `Field overflow` where the ROM says **`FIELD overflow`**.
      ⚠️ **THOSE FOUR ARE FIXED BUT UNWITNESSED** — no row in any of them
      provokes a FIELD overflow (`fldary` names it in its own NOT-COVERED list:
      *"unchecked today, unchanged here"*), so the fix removes a latent blindness
      and **changes no current reading**. Do not read it as a measured win.
      ➡️ **OPEN: the `<UNREADABLE>` fallback in the other 18**, and better, ONE
      shared classifier (there is precedent — `probe_report`) so the alphabet
      cannot drift per-probe again.
      🎚️ APPARATUS — error-message alphabet
      🤖 AUTONOMOUS — the alphabet is derivable from the ROM source and each
      probe's own rows are the control.
      🟢 **BOTH OPEN HALVES DONE (D-ALPHAGATE, 2026-09-05), AND THE FILED
      COUNT WAS WRONG IN THE SAFE DIRECTION.**
      📏 **"THE OTHER 18" WAS 4.** Walked with an AST sweep for the actual
      shape — a function that iterates an error alphabet AND can return a bare
      sentinel — not for `grep '"Type mismatch"'`, which counts comments and
      probes with no classifier at all. **16 such classifiers exist; 12 already
      had the arm**; the four that did not were `basic_probe_namspc.py`'s
      `bracket()`, `errface()` and `listface()` and `basic_probe_strparen.py`'s
      `face()`. All four now carry it; the sweep re-reads **0**.
      🎯 **`listface()` WAS THE INTERESTING ONE**: its miss-face is `<none>`,
      i.e. *"the listing ended cleanly"* — so an unmodelled screen would have
      been reported as a clean directory listing, not as a silence. Its arm
      subtracts the directory lines first, or every `FILES` row would read
      unreadable.
      ➡️ **ONE SHARED, DERIVED ALPHABET EXISTS**:
      [`probes/lib/errmsg_alphabet.py`](../../probes/lib/errmsg_alphabet.py) reads the
      messages out of `sub/errmsg.asm` **and** the escape-encoded main-ROM
      strings, expanding `MSGESC_*` from the `equ` comments in
      [`basic/sysvars.inc`](../../basic/sysvars.inc) rather than restating them — 39
      messages, with known-answer arms including a NEGATIVE one for the
      `Field overflow`/`FIELD overflow` casing that started this.
      🟢 **AND THE CASING CLASS MEASURES EMPTY TODAY — a negative result this
      entry did not have.** The sweep raised 58 literals differing from the ROM
      by case; **57 are the case-folding idiom** (`"type mismatch" in
      txt.lower()`), and the 58th, `basic_probe_fldwidth.py`'s `File not open`,
      is **correct**: that probe folds case ON PURPOSE because `File not OPEN`
      vs `File not open` is D-MSGEXACT's separately-owned surface. 🔴 **The first
      cut of the advisory printed all 58** — an advisory that loud is one nobody
      reads, which is the same instrument failure by another route
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      🔒 `make error-alphabet-check` keeps both halves: RED on a classifier with
      no UNREADABLE arm (6 arms, two of which are the shape that was broken),
      ADVISORY on spelling. 💰 0 ROM bytes.
      ⚠️ **NOT DONE: the 12 existing classifiers still each own their own list.**
      The gate makes an omission LOUD rather than impossible, which is the
      bounded fix; a single shared `classify()` now exists for the next probe to
      use, and retrofitting the 12 is unpriced. **The item stays open for that.**
      [[a-coverage-row-whose-geometry-cannot-reach-the-case]]
