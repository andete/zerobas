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

🎯 AND EVERYTHING GOES UNDER **ONE ROOT**, so cleaning up is one command:

    rm -rf /tmp/zerobas

That is the whole point of this module, and it is why importing it has a SIDE
EFFECT: it sets `tempfile.tempdir`. Python resolves every bare
`mkstemp`/`mkdtemp`/`NamedTemporaryFile` through that one global, so setting it
once relocates ~140 call sites across the probe tree without touching any of
them -- and, more importantly, without a future one being able to escape by
being written the ordinary way. A per-site helper would have had to be
remembered 140 times; this has to be right once.

⚠️ WHAT IS *NOT* COVERED, AND IS ENFORCED SEPARATELY: hardcoded `"/tmp/..."`
string literals. There are 122 of them in 67 files, and they cannot be moved
blindly -- eleven are `argparse` defaults, i.e. a documented output location a
person may be relying on. `tools/check_temp_root.py` pins the set so it can
shrink but never grow.

⚠️ `$ZEROBAS_TMP` overrides the root; `tests/_tmp.py` derives its own base from
`ROOT` so unit-test artefacts land under it too; and `run_gates.py` still points
`$ZB_TEST_TMP` at a per-battery tree it wipes, which is where the probe scratch
directories go during a battery.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile

# 🔴 ONE ROOT, AND IT IS A LITERAL PATH ON PURPOSE. `tempfile.gettempdir()` is
# `$TMPDIR`, which on macOS is a per-user `/var/folders/…` path nobody can type
# from memory -- and "cleaning up" has to be a command a person will actually
# run. This is the path the operator asked for.
ROOT = os.environ.get("ZEROBAS_TMP") or "/tmp/zerobas"
os.makedirs(ROOT, exist_ok=True)

# 🔴 THE SIDE EFFECT THAT MAKES THIS WORK AT ALL. Every bare `tempfile.*` call
# in any module imported after this one now lands under ROOT. Importing this
# module IS the policy; see the docstring.
tempfile.tempdir = ROOT

BASE = os.environ.get("ZB_TEST_TMP") or ROOT

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
