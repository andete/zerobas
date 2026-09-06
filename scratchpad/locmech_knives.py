#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LOCMECH — WHY does `u.str` survive K-LP1? The filed hypothesis, tested.

TODO.md's `locarg` apparatus item ends with a question, not a finding:

    ➡️ WHAT IS OPEN: why `u.str` survives. `ENDFLAG` is set by `fre_abort_low`
    before its `ret`, so the run may simply stop at the next `rp_run` check
    before a second message can print — that is a hypothesis, not a reading.

🔴 THAT QUESTION IS ANSWERED AND THE HYPOTHESIS IS THE WRONG WAY ROUND — the
quote above is kept because it is what this runner was built to test, not
because it still stands. `u.str` was never the row that carries the property
(`u.trail` is), and `K-LM3` shows `ENDFLAG` alone moves nothing: with the SP
reset in place it is `ld sp,(SAVSTK)` plus the tail `ret` that ends the run.

K-LP1 cuts `fre_abort_low`'s `ld sp,(SAVSTK)`, putting the depth-dependence back.
Exactly one row of forty-five moves — `u.bare`, to `''` — and `u.str`
(`LOCATE "5",3`) stays green, so the battery detects the property at one row, by
a symptom other than the one D-LOCARG §3.2 advertises.

🎯 THE ARMS, AND WHY THE THIRD ONE IS NOT OPTIONAL.

  K-LP1  `ld sp,(SAVSTK)` -> 4 nops.  Reproduce the filed reading first: if
         `u.bare` does not move, the whole question is about a machine that no
         longer exists and nothing below means anything.
  K-LM2  K-LP1 **plus** `ld (ENDFLAG),a` -> 3 nops.  The hypothesis: if ENDFLAG
         is what stops a second message, removing BOTH should let `u.str` move.
  K-LM3  `ld (ENDFLAG),a` -> 3 nops, ALONE.  🔴 THE CONTROL. Without it, a
         moved `u.str` in K-LM2 is equally explained by "cutting ENDFLAG moves
         this row on its own" -- two rules that agree on every arm I would
         otherwise have [[two-rules-that-coincide-on-every-row-you-have]]. The
         hypothesis is about an INTERACTION, so the single-cut arm has to be run.

⚠️ THE ARM NAMES. `K-LP1` is the SAME cut docs/spec-basic-locarg.md §11.4
already names, deliberately -- this run is a re-take of it. `K-LP2`/`K-LP3` in
that table are DIFFERENT cuts (`loc_next`'s `scf`, `loc_omit`'s `or a`), so the
two new arms here are `K-LM2`/`K-LM3` and not a second meaning for names that
are taken.

PREDICTIONS, WRITTEN BEFORE THE RUN:
  K-LP1  u.bare -> ''            u.str unchanged
  K-LM2  u.bare -> ''            u.str MOVES (a second message, or garbage)
  K-LM3  u.bare unchanged        u.str unchanged
Any other pattern refutes the filed hypothesis rather than confirming it, and
the entry says so: *"Either the mechanism is established and §3.2 is narrowed to
what it can support, or a row is added that DOES see it."*

⚠️ THE CUTS ARE PADDED TO THEIR OWN SIZE (`ld sp,(nn)` is 4 bytes, `ld (nn),a`
is 3) so the image does not shift under the knife. A knife that moves every
later byte can fail the build on an unrelated `jr` and report that as a finding.
"""
import atexit
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                                                # noqa: E402

TMP, SRC = "/tmp/zerobas", "basic/arrays.asm"

SP_CUT = ("                ld      sp,(SAVSTK)",
          "                nop\n                nop\n                nop\n"
          "                nop                 ; K-LP1 CUT (restored on exit)")
EF_CUT = ("                ld      (ENDFLAG),a         ; D-1 (docs/spec-basic-error-handling.md",
          "                nop\n                nop\n"
          "                nop                 ; K-LM3 CUT — D-1 (docs/spec-basic-error-handling.md")

ARMS = [
    ("K-LP1", [SP_CUT],          {"u.bare": "MOVE", "u.str": "SAME"}),
    ("K-LM2", [SP_CUT, EF_CUT],  {"u.bare": "MOVE", "u.str": "MOVE"}),
    ("K-LM3", [EF_CUT],          {"u.bare": "SAME", "u.str": "SAME"}),
]


# 🔴 THE PROBE HAS A REFUSAL AND THE FIRST CUT OF THIS RUNNER SCORED IT AS DATA.
# When a POSITIVE CONTROL fails, basic_probe_locarg prints
# `*** A POSITIVE CONTROL FAILED, so nothing below it was measured.` and stops.
# K-LM2 tripped it, every row came back absent, and the runner reported
# "45 of 45 rows moved" and ticked both predictions OK. A missing row is an
# INSTRUMENT outcome; scoring it as a machine reading is the same fault this
# tree keeps finding in probes [[an-unnamed-outcome-reads-as-no-outcome]].
CONTROL_FAILED = "A POSITIVE CONTROL FAILED"


def read_rows(path):
    """-> ({label: zb reading}, control_failure_text or None)."""
    out, refused = {}, None
    txt = open(path, errors="replace").read()
    if CONTROL_FAILED in txt:
        for line in txt.splitlines():
            if line.startswith("FAIL") and "zb='" in line:
                refused = " ".join(line.split())
                break
        refused = refused or CONTROL_FAILED
    for line in txt.splitlines():
        f = line.split()
        if len(f) >= 3 and f[0] == "--" and "zb='" in line:
            out[f[1]] = line.split("zb='", 1)[1].rsplit("'", 1)[0]
    return out, refused


def run_probe(tag):
    """🎯 ALL 45 ROWS, NOT THE TWO THE HYPOTHESIS NAMES. The filed claim is
    "exactly ONE row of forty-five moves", and a runner that reads only the two
    rows in the sentence cannot check the "exactly one" half -- it would report
    a silent SAME for a knife that had reddened four other rows. The full
    zb-only sweep costs ~3 s."""
    log = f"{TMP}/locmech_{tag}.out"
    with open(log, "w") as fh:
        subprocess.call("python3 probes/basic/basic_probe_locarg.py --sides zb",
                        shell=True, stdout=fh, stderr=subprocess.STDOUT)
    return read_rows(log)


def main():
    orig = open(SRC).read()
    restore = lambda: open(SRC, "w").write(orig)                  # noqa: E731
    atexit.register(restore)

    base, refused = run_probe("base")
    if refused:
        print(f"🔴 the BASELINE tripped the probe's own control refusal: "
              f"{refused}\n   Nothing can be scored against it.")
        return 1
    print("BASE (unmodified):")
    for k in ("u.bare", "u.str"):
        print(f"    {k:8s} {base.get(k, '<NO READING>')!r}")
    print(f"    ({len(base)} rows read in total)")
    if len(base) < 40 or "u.bare" not in base or "u.str" not in base:
        print("🔴 the baseline itself is short — refusing to score arms against it")
        return 1

    fails = []
    for tag, cuts, want in ARMS:
        src = orig
        for anchor, repl in cuts:
            if src.count(anchor) != 1:
                print(f"KNIFE BROKEN: anchor not unique for {tag}: {anchor!r}")
                return 1
            src = src.replace(anchor, repl)
        open(SRC, "w").write(src)
        before = knife_guard.hashes()
        moved, after, rc = knife_guard.build(f"{TMP}/locmech_{tag}_build.out",
                                             before, clean=True)
        print(f"\n{tag}: " + knife_guard.report(tag, moved, before, after))
        if rc or not moved:
            print(f"{tag}: 🔴 BUILD FAILED or ROM UNCHANGED — the cut is INERT, "
                  f"not 'reddened nothing'")
            restore()
            return 1
        got, refused = run_probe(tag)
        if refused:
            # NOT scored, and NOT counted as 45 moved rows. The refusal itself is
            # the finding, so it is printed in full.
            print(f"    ⚠️ NOT A ROW READING — the probe REFUSED this arm:")
            print(f"       {refused}")
            print(f"       ({len(got)} of {len(base)} rows reached the output at "
                  f"all; the predictions for this arm are UNTESTED, not met)")
            fails += [f"{tag}/refused"]
            restore()
            continue
        allmoved = sorted(k for k in base if got.get(k, "<NO READING>") != base[k])
        for k in ("u.bare", "u.str"):
            b, g = base.get(k), got.get(k, "<NO READING>")
            verdict = "SAME" if g == b else "MOVE"
            ok = verdict == want[k]
            fails += [] if ok else [f"{tag}/{k}"]
            print(f"    {k:8s} {g!r:42s} {verdict:5s} "
                  f"(predicted {want[k]}) {'OK' if ok else '🔴 MISS'}")
        # The "exactly one of forty-five" half of the filed claim, which the two
        # named rows cannot answer on their own -- and which is where this run's
        # real finding turned out to be.
        print(f"    ALL rows that moved ({len(allmoved)} of {len(base)}): "
              f"{allmoved if allmoved else '— none —'}")
        for k in allmoved:
            print(f"       {k:10s} {base[k]!r}\n"
                  f"       {'':10s} -> {got.get(k, '<NO READING>')!r}")
        restore()

    atexit.unregister(restore)
    subprocess.call("make repack-machine", shell=True,
                    stdout=open(f"{TMP}/locmech_restore.out", "w"),
                    stderr=subprocess.STDOUT)
    print("\n" + "=" * 70)
    if fails:
        print(f"🔴 {len(fails)} prediction(s) MISSED: {fails}")
        print("   The filed hypothesis is NOT established by this run. Read the "
              "rows above and narrow §3.2 to what they support.")
    else:
        print("all predictions hold — ENDFLAG is why u.str survives K-LP1, and "
              "K-LM3 shows it is the INTERACTION and not ENDFLAG alone")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
