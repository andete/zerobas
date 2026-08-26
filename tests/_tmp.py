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
