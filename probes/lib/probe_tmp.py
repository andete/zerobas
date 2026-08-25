#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""probe_tmp — a scratch path THIS PROCESS owns, and gives back when it exits.

Probes hard-coded `os.path.join(tempfile.gettempdir(), f"zb_line_{side}_{label}.dsk")`
and friends: a fixed name, derived from the CASE, with no process identity in it
and no cleanup after it. That is two defects wearing one line.

🔴 **COLLISION.** `tools/run_gates.py` shards `lineerr-acceptance` across eight
concurrent processes and REPLICATES the four `CONTROLS` into every shard, so
eight processes `shutil.copy` onto the same twelve paths while others have them
mounted as `-diska`. `tests/_tmp.py` already carries this lesson for the unit
tests -- its own docstring says the fixed names "bit the parallel gate battery
as a stochastic `pasmo` failure" -- but the fix was never carried across to the
probes, which are the half that actually runs eight at a time.
⚠️ It is NOT what caused the flakes measured on 2026-08-25: those were the
shared `settings.xml` (see `omsx_repl.OMSX_SETTINGS`), and none of the four rows
examined was a control. Same class, different member, closed before it fires.

🔴 **LEAK.** Nothing ever deleted them. Measured on the machine that found this:
**2165 orphaned `zb_*` files, 1.1 GB**, accumulated across sessions. Adding
process identity WITHOUT adding cleanup would have made that strictly worse --
today's names are at least reused between batteries.

So: one directory per process, made on first use, removed at exit. Names inside
it stay exactly as they were, so a probe that reuses one path across cases
(`zb_runtail_{side}.dsk`) keeps doing so.

⚠️ `atexit` does not run on SIGKILL, so a probe killed outright leaks ONE
directory rather than N files. The watchdog in `omsx_repl` kills the EMULATOR,
not the probe, so this is the rare path.

⚠️ The base honours `$ZB_TEST_TMP` exactly as `tests/_tmp.py` does, so a runner
that isolates an invocation isolates the probes too -- and `run_gates.py`, which
sets it and then `rm -rf`s that tree on the next battery, sweeps up even the
SIGKILL leftovers.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile

BASE = os.environ.get("ZB_TEST_TMP") or tempfile.gettempdir()

_dir: str | None = None


def _own() -> str:
    global _dir
    if _dir is None:
        os.makedirs(BASE, exist_ok=True)
        # the PID is in the NAME as well as in the uniqueness, so an operator
        # looking at a leftover directory can tell whether its owner is alive.
        _dir = tempfile.mkdtemp(prefix=f"zbprobe_{os.getpid()}_", dir=BASE)
        atexit.register(shutil.rmtree, _dir, ignore_errors=True)
    return _dir


def tmp(name: str) -> str:
    """A path under this process's own scratch directory."""
    return os.path.join(_own(), name)
