#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PINGATE — `tools/filed-row-known.txt` had NO GATE, and its own entry said so.

The filed-row adjudication set pins, per probe, the divergent rows an open
TODO.md item already OWNS. Its whole value is the COMPLEMENT: a divergence in
the file is *measured-and-known*, a divergence not in it is
*measured-and-unnoticed*. That only holds while the file tracks reality.

🔴 AND IT DOES NOT TRACK REALITY BY ITSELF. `filed_row_sweep.py` builds its
corpus from the probes cited by OPEN items, so **when an item closes, its probe
leaves the corpus and its pin stays behind, unvalidatable** -- the sweep can
neither confirm it nor call it stale. The owning entry (TODO.md, "SEVEN FILED
PROBES PRINT DIVERGENCES AND EXIT 0") records this happening three times:
`onerrarm_probe`, then `reqcomma_probe` -- which "sat stale for a day, `g.field`
agreeing on both machines while the pin still claimed it as a known divergence,
and the scoreboard built from these pins counted it as outstanding correctness
debt" -- and then twice more in one day, from that session's own commits. Its
verdict:

    "the rule is not carried by anything that runs: closing an item does not
     touch tools/filed-row-known.txt, and only --check-orphans notices, and only
     when someone runs it."

This is that "anything that runs". The check itself is not new -- it is
`filed_row_sweep.check_orphans()`, which has existed since 2026-09-06 and found
all three. What was missing was a caller in the battery.

🎯 IT IMPORTS THE SWEEP RATHER THAN REIMPLEMENTING IT. "Which probes are in the
corpus" and "which probes are pinned" are exactly the questions the sweep already
answers, and a gate that answered them its own way would be a SECOND denominator
free to drift from the first -- the failure mode this tree has paid for more than
once [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]. The import
direction (tools/ -> scratchpad/) is unusual and deliberate: the sweep is the
authority, and duplicating it here to satisfy a layering convention would trade a
real invariant for a tidy one.

⚠️ WHAT THIS GATE DOES NOT DO: it never boots a machine, so it cannot tell a pin
whose rows STOPPED diverging from one whose rows still diverge. That is the
sweep's own `⚠️ NO LONGER DIVERGING` arm and it costs a full serial run with the
refcache off. This gate covers only the failure that is invisible AND free to
detect: a pin the sweep can no longer reach at all.

<1 s, read-only, no emulator.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP = os.path.join(ROOT, "scratchpad", "filed_row_sweep.py")

# ⚠️ IMPORTED FOR ITS SIDE EFFECT, and `temp-root-check` is what asked for it:
# this gate's selftest plants files with `tempfile.TemporaryDirectory()`, and a
# bare `tempfile` call escapes the `/tmp/zerobas` root. `probe_tmp` sets
# `tempfile.tempdir` once, at import, so every bare call below lands under the
# root and is cleaned up at exit -- the one-line fix the gate's own message
# names, rather than a hardcoded path that would have to be pinned forever.
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402,F401

# `check_orphans()` finds pins with `([a-z0-9_]+_probe):`; `known_rows()` finds
# them with `": " in line`. TWO REGEXES OVER ONE FILE, and they disagree by one.
ORPHAN_SCAN = re.compile(r"([a-z0-9_]+_probe):")
# A pin the orphan scan cannot NAME can never be reported as orphaned, whatever
# the corpus says, so it must say out loud that something else validates it.
DECLARE = "NOT-IN-SWEEP"


def load_sweep():
    if not os.path.exists(SWEEP):
        print(f"🔴 REFUSING: {SWEEP} is missing. This gate delegates to it; "
              f"without it there is no corpus definition to check against, and "
              f"a green here would mean nothing.")
        raise SystemExit(2)
    spec = importlib.util.spec_from_file_location("filed_row_sweep", SWEEP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_orphans(sweep) -> tuple[int, str]:
    """check_orphans(), with its output captured so the selftest can read it."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = sweep.check_orphans()
    return rc, buf.getvalue()


def reconcile(sweep, pins) -> int:
    """🔴 THE SCAN THAT FINDS ORPHANS AND THE SCAN THAT READS PINS MUST SEE THE
    SAME SET.

    Found by this gate printing both counts and them differing by one:
    `basic_probe_nodisk` does not end in `_probe`, so `check_orphans()` cannot
    NAME it and could never report it however stale it got -- and `CITE` only
    matches `scratchpad/<x>_probe.py`, so it is not in the corpus either. A pin
    in a permanent blind spot, inside the instrument built to make blind spots
    loud.

    🎯 IT IS HARMLESS TODAY AND THAT IS NOT THE POINT. That entry's rows are
    ALSO pinned to exact values inside `basic_probe_nodisk.PINNED`, so
    `nodisk-acceptance` reddens if either column moves -- the file says so
    itself. The hazard is that the exclusion is SILENT: the next pin whose name
    does not fit the regex gets the blind spot without the belt and braces.
    So the exception stays, and has to DECLARE itself
    [[a-coverage-row-whose-geometry-cannot-reach-the-case]]."""
    lines = {}
    for ln in open(sweep.KNOWN_FILE, errors="replace"):
        st = ln.strip()
        if not st or st.startswith("#") or ": " not in st:
            continue
        lines[st.split(": ", 1)[0]] = st
    bad = []
    for name in pins:
        ln = lines.get(name, "")
        if ORPHAN_SCAN.match(name + ":"):
            continue                      # the orphan scan can name it
        if DECLARE in ln:
            continue                      # declared, with its reason in the line
        bad.append(name)
    if not bad:
        return 0
    print(f"🔴 {len(bad)} PIN(S) THE ORPHAN SCAN CANNOT NAME, and undeclared:")
    for b in bad:
        print(f"     {b}")
    print(f"  A pin whose name the orphan scan cannot match is invisible to it "
          f"forever -- it can never be reported stale. Either rename it to end "
          f"in `_probe`, or add `{DECLARE}` to its line WITH the thing that "
          f"validates it instead.")
    return 1


def selftest(sweep) -> bool:
    """🔴 PLANT BOTH DIRECTIONS. A gate that only ever sees the green case cannot
    distinguish "no orphans" from "the check no longer looks"
    [[a-knife-can-be-inert-because-the-build-did-not-happen]]."""
    real = sweep.KNOWN_FILE
    try:
        body = open(real, errors="replace").read()
        # (a) the CONTROL: the committed file, unmodified.
        rc_ctl, out_ctl = run_orphans(sweep)
        # (b) a pin naming a probe no OPEN item cites. `zzz_nosuch_probe` cannot
        #     be in the corpus, because the corpus comes from TODO.md citations.
        with tempfile.TemporaryDirectory() as d:
            planted = os.path.join(d, "planted.txt")
            with open(planted, "w") as fh:
                fh.write(body + "\nzzz_nosuch_probe: r.one -- PLANTED BY SELFTEST\n")
            sweep.KNOWN_FILE = planted
            rc_bad, out_bad = run_orphans(sweep)
    finally:
        sweep.KNOWN_FILE = real

    ok = True
    if rc_bad == 0 or "zzz_nosuch_probe" not in out_bad:
        print(f"🔴 SELFTEST: a planted orphan did NOT go red (rc={rc_bad}). "
              f"This gate cannot see the thing it exists for.")
        ok = False
    if rc_ctl != 0 and "ORPHANED" not in out_ctl:
        print("🔴 SELFTEST: the control run failed for a reason that is not an "
              "orphan — the check is broken, not the pin file.")
        ok = False
    # The second arm, planted the same way: an undeclared pin the orphan scan
    # cannot name. Without this the reconcile() check could rot to `return 0`
    # and every run would still print a confident green.
    with tempfile.TemporaryDirectory() as d:
        planted = os.path.join(d, "unnameable.txt")
        with open(planted, "w") as fh:
            fh.write(body + "\nzzz_nosuch_thing: r.one -- PLANTED BY SELFTEST\n")
        real2 = sweep.KNOWN_FILE
        try:
            sweep.KNOWN_FILE = planted
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc_un = reconcile(sweep, sweep.known_rows())
        finally:
            sweep.KNOWN_FILE = real2
    if rc_un == 0 or "zzz_nosuch_thing" not in buf.getvalue():
        print(f"🔴 SELFTEST: an undeclared pin the orphan scan cannot name did "
              f"NOT go red (rc={rc_un}).")
        ok = False
    if ok:
        print(f"selftest: a planted orphan goes RED (rc={rc_bad}) and names "
              f"itself; an undeclared unnameable pin goes RED (rc={rc_un}); the "
              f"committed file is judged by the same code ✅")
    return ok


def main() -> int:
    sweep = load_sweep()
    # `known_rows()` carries its own refuse-on-degenerate (it raises if fewer
    # than five probes parse). Calling it here means a pin file that has been
    # emptied or mangled fails THIS gate rather than silently scoring every
    # divergence as new the next time the sweep runs.
    pins = sweep.known_rows()
    if not selftest(sweep):
        return 2
    rc, out = run_orphans(sweep)
    sys.stdout.write(out)
    rc |= reconcile(sweep, pins)
    print(f"filed-pin-check: {len(pins)} pinned probe(s) parsed")
    if rc:
        print("  ➡️ An orphaned pin is not automatically WRONG — it is "
              "UNVALIDATABLE. Re-run that probe by hand with the refcache OFF; "
              "if its rows now agree, the pin leaves the set, and if they still "
              "diverge the owning entry closed with the divergence live.")
    return 1 if rc else 0


if __name__ == "__main__":
    sys.exit(main())
