# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Per-invocation temp base for unit-test build artifacts (parallel-safety).

The unit tests historically hard-coded `/tmp/zb_*.rom` etc. Those fixed names
collide the moment two test *processes* touch the same one concurrently -- which
is what blocks running the suite in parallel (and bit the parallel gate battery
as a stochastic `pasmo` failure). Route every such path through `tp()`:

  * base is `$ZB_TEST_TMP` when set, else `/tmp` -- so with the variable UNSET the
    path is byte-identical to before (no behaviour change for `make unit-test`);
  * a runner that wants isolation sets `ZB_TEST_TMP` to a unique dir per
    invocation. Every test subprocess of that invocation inherits the SAME base,
    so a test that reuses another's build (e.g. test_rdblk_randrecord reads
    test_wrblk_body_e2e's ROM) still finds it -- the sharing is preserved, only
    the /tmp collision across *concurrent* invocations is removed.

Leading underscore so tests/run.py's `test_*.py` glob never collects this.
"""
import os
import sys

# 🎯 ONE SOURCE OF TRUTH FOR THE TEMP ROOT. `probes/lib/probe_tmp.py` owns it
# (`/tmp/zerobas`, overridable with $ZEROBAS_TMP) so that "clean up everything
# this project wrote" stays ONE `rm -rf`. Importing it also points `tempfile`
# at the root, which is what relocates the bare `tempfile.*` calls in tests.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import probe_tmp                                                 # noqa: E402

BASE = os.environ.get("ZB_TEST_TMP") or probe_tmp.ROOT
os.makedirs(BASE, exist_ok=True)


def tp(name: str) -> str:
    """A build-artifact path under the (isolatable) temp base."""
    return os.path.join(BASE, name)

# --- D-PASMOSAY: make a failed shell-out SAY WHY -----------------------------
# 🔴 A `pasmo` FAILURE REPORTED AN EXIT CODE AND NOTHING ELSE, AND THAT MADE A
# REAL FLAKE UNDIAGNOSABLE. The 2026-08-26 D-PLAYOP battery went 38/38 with one
# "recovered flake" on `unit-test`; the log held a full Python traceback ending
#
#   subprocess.CalledProcessError: Command '['pasmo', '--bin', ...]'
#   returned non-zero exit status 1.
#
# ...and pasmo's own explanation was in `e.stderr`, which
# `CalledProcessError.__str__` does not print. So the one thing that could say
# whether the tree was broken or the harness was could not be looked at, and the
# runner retried it into green.
#
# 🎯 THIS IS THE `omsx_repl._why_missing()` LESSON ON THE HOST SIDE
# (docs/spec-probe-omsx-settings.md, docs/spec-probe-machxml.md): when PASS is
# "nothing happened", spend the evidence the run already holds. There it was a
# `<NO CAPTURE>` that named its cause and immediately found the machine-XML
# race; here it is an exit status that names nothing.
#
# ⚠️ AND IT IS A HOOK, NOT A WRAPPER, BECAUSE 53 CALL SITES WOULD HAVE TO
# REMEMBER A WRAPPER. `sys.excepthook` fires for the UNCAUGHT exception that
# kills the test process -- which is exactly the shape every one of these
# shell-outs has (`subprocess.run(..., check=True)` at module or run() level).
# 📏 MEASURED: 53 test files shell out to `pasmo`, and **52 of them already
# import this module**; the 53rd is `tests/coverage.py`, which `tests/run.py`'s
# `test_*.py` glob does not collect. One file covers the suite. That is the same
# choice probe_tmp.py made when ONE `tempfile.tempdir` assignment relocated 140
# call sites: reach for the chokepoint before the wrapper.
#
# A test that CATCHES the error is unaffected -- the hook only runs when nothing
# else handled it.
import subprocess                                                # noqa: E402

_prev_excepthook = sys.excepthook


def _say_why(exc_type, exc, tb):
    if isinstance(exc, subprocess.CalledProcessError):
        argv = exc.cmd[0] if isinstance(exc.cmd, (list, tuple)) and exc.cmd else exc.cmd
        for stream in ("stderr", "stdout"):
            blob = getattr(exc, stream, None)
            if not blob:
                continue
            if isinstance(blob, (bytes, bytearray)):
                blob = blob.decode("utf-8", "replace")
            blob = blob.strip()
            if blob:
                sys.stderr.write(
                    f"\n--- what {argv} actually said ({stream}) ---\n{blob}\n")
    _prev_excepthook(exc_type, exc, tb)


sys.excepthook = _say_why
