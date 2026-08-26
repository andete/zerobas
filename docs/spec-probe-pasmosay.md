<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-PASMOSAY — a failed `pasmo` reported an exit code and nothing else

Status: **✅ FIXED.** 2026-08-26, on `8bc614e`. One hook in `tests/_tmp.py`, no
ROM byte moved.

---

## 1. What happened, and what could not be looked at

The D-PLAYOP battery went **38/38 green with one *"recovered flake"* on
`unit-test`**. The log held a full Python traceback ending:

```
subprocess.CalledProcessError: Command '['pasmo', '--bin', 'basic/main.asm',
  '.../test_tmp/zb_eval.rom', '.../zb_eval.sym']' returned non-zero exit status 1.
```

**pasmo's own explanation was in `e.stderr` and `CalledProcessError.__str__`
does not print it.** So the one thing that could say whether the *tree* was
broken or the *harness* was could not be looked at at all, and `run_gates.py`
retried it into green.

🎯 **THIS IS `omsx_repl._why_missing()`'S LESSON ON THE HOST SIDE.** On the
emulator side, spending the evidence a failed run already holds turned a bare
`<NO CAPTURE>` into *"Loading of hardware configuration failed … Document
doesn't contain mandatory root Element"* and found the machine-XML race the same
morning (`docs/spec-probe-machxml.md`). Here the same failure mode was sitting in
the assembler path, uncaught.

---

## 2. 📏 The chokepoint, measured

**53 test files shell out to `pasmo` with `capture_output=True`.** A wrapper
would be 53 edits that 53 future sites must remember.

**52 of the 53 already `import _tmp`** — and the 53rd is `tests/coverage.py`,
which `tests/run.py`'s `test_*.py` glob does not collect. **One file covers the
suite.**

That is the choice `probes/lib/probe_tmp.py` made when a single
`tempfile.tempdir` assignment relocated 140 call sites: **reach for the
chokepoint before the wrapper.**

`sys.excepthook` is the right hook because it fires for the **uncaught**
exception that kills the test process — which is exactly the shape all of these
have (`subprocess.run(..., check=True)` at module or `run()` level). A test that
*catches* the error is unaffected.

---

## 3. 🔬 Falsified — four arms, and the first RED arm was WRONG

`scratchpad/pasmosay_falsify.py`. A hook that prints is only half the claim; one
that prints on *everything* is noise, and noise is what gets `except: pass`
written.

| arm | asserts | result |
|---|---|---|
| **RED-SYNTHETIC** | a `CalledProcessError` carrying a known stderr reaches stderr | ✅ |
| **RED-REAL** | a genuinely broken source surfaces **pasmo's own** message | ✅ 826 chars |
| **GREEN-PLAIN** | an ordinary uncaught `ValueError` is **unchanged** | ✅ |
| **GREEN-OK** | a healthy run prints **nothing extra** | ✅ |

🔴 **AND THE FIRST RED-REAL VECTOR WAS NOT BROKEN.**
`THIS_IS_NOT_AN_INSTRUCTION` on its own line is a perfectly good **label**, so
pasmo exited 0, the arm reported the hook silent, and the runner said *"do not
ship"* — correctly, for the wrong reason. **A falsification arm that passes for
the wrong reason is the same defect as a green row that agrees for the wrong
reason** ([[a-case-that-agrees-can-agree-for-the-wrong-reason]]), and it is only
visible because the arm also checks `rc != 0`. An undefined symbol is an error
pasmo cannot talk itself out of.

⚠️ **RED-REAL DELIBERATELY DOES NOT PIN PASMO'S WORDING** — only that something
of its own reached stderr under the banner. Pinning the text would be a claim
about the assembler's version, not about this hook.

What a failure looks like now:

```
--- what pasmo actually said (stderr) ---
ERROR: Symbol 'NO_SUCH_SYMBOL_XYZ' is undefined  on line 2 of file …
```

Green control on the real suite: `make unit-test` **59 PASS / 0 FAIL**.

---

## 4. 🔴 What this does NOT do

* **IT DOES NOT DIAGNOSE THE FLAKE THAT PROMPTED IT.** That run's `pasmo` stderr
  is gone; the hook makes the *next* occurrence self-describing and says nothing
  about this one. The `unit-test` flake remains **open and uncaused** — filed.
* It covers the 52 collected test files. `tests/coverage.py` and anything
  outside `tests/` (e.g. `tools/`) shell out to `pasmo` unhooked.
* It is not a gate. Nothing fails if a future test stops importing `_tmp`, and
  such a test would silently lose the diagnostic.
* `sys.excepthook` is a side effect of *importing* `_tmp`, which is consistent
  with what that module already does (`makedirs`, and `probe_tmp` pointing
  `tempfile` at the root) but is worth knowing before adding a fifth.
