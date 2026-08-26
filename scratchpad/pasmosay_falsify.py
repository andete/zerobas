#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PASMOSAY falsification — does the hook actually SAY, and does it stay quiet?

Three arms, because a hook that prints is only half the claim:

  RED-SYNTHETIC  a CalledProcessError carrying a known stderr must reach stderr.
  RED-REAL       a genuinely broken source must surface PASMO'S OWN message --
                 the synthetic arm cannot prove that, because it never runs the
                 assembler and so never tests that `capture_output=True` is
                 where the text is.
  GREEN          an ordinary uncaught exception must be UNCHANGED, and a healthy
                 run must print nothing extra. A hook that fires on everything
                 is noise, and noise is what got `except: pass` written the last
                 time this project had a guard that named a symptom.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

MARKER = "PASMO-SAID-THIS-EXACT-THING"

SYNTHETIC = f'''import sys, subprocess
sys.path.insert(0, "tests")
import _tmp                      # installs the hook as a side effect of import
raise subprocess.CalledProcessError(
    1, ["pasmo", "--bin", "x.asm"], output=b"", stderr=b"{MARKER}")
'''

REAL = '''import sys, subprocess, os
sys.path.insert(0, "tests")
from _tmp import tp
src = tp("pasmosay_broken.asm")
# 🔴 THE FIRST VECTOR HERE WAS NOT BROKEN. `THIS_IS_NOT_AN_INSTRUCTION` on its
# own line is a perfectly good LABEL, so pasmo exited 0 and the arm reported the
# hook silent when the hook had never been reached. A falsification arm that
# passes for the wrong reason is the same defect as a green row that agrees for
# the wrong reason. An UNDEFINED SYMBOL is an error pasmo cannot talk itself out
# of.
open(src, "w").write("    org 0\\n    ld a,(NO_SUCH_SYMBOL_XYZ)\\n")
subprocess.run(["pasmo", "--bin", src, tp("pasmosay.rom")],
               check=True, capture_output=True)
'''

GREEN_PLAIN = '''import sys
sys.path.insert(0, "tests")
import _tmp
raise ValueError("an ordinary error, which must pass through untouched")
'''

GREEN_OK = '''import sys
sys.path.insert(0, "tests")
import _tmp
print("healthy run")
'''


def run(src):
    p = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main():
    fails = 0

    rc, _, err = run(SYNTHETIC)
    ok = rc != 0 and MARKER in err and "what pasmo actually said" in err
    print(f"  RED-SYNTHETIC   rc={rc}  marker={'FOUND' if MARKER in err else 'ABSENT'}"
          f"   {'✅' if ok else '🔴 the hook did not say'}")
    fails += not ok

    rc, _, err = run(REAL)
    said = "what pasmo actually said" in err
    # pasmo's own wording is not pinned here -- only that SOMETHING of its own
    # reached stderr under the banner. Pinning its text would be a claim about
    # the assembler's version, not about this hook.
    body = err.split("what pasmo actually said", 1)[-1].strip() if said else ""
    ok = rc != 0 and said and len(body) > 20
    print(f"  RED-REAL        rc={rc}  banner={'yes' if said else 'NO'}  "
          f"body={len(body)} chars   {'✅' if ok else '🔴'}")
    if said:
        first = [l for l in body.splitlines() if l.strip() and not l.startswith("---")]
        print(f"                  pasmo said: {first[0][:90] if first else '<empty>'}")
    fails += not ok

    rc, _, err = run(GREEN_PLAIN)
    ok = rc != 0 and "actually said" not in err and "ValueError" in err
    print(f"  GREEN-PLAIN     rc={rc}  quiet={'yes' if 'actually said' not in err else 'NO'}"
          f"   {'✅' if ok else '🔴 the hook fired on a non-subprocess error'}")
    fails += not ok

    rc, out, err = run(GREEN_OK)
    ok = rc == 0 and "actually said" not in err
    print(f"  GREEN-OK        rc={rc}  quiet={'yes' if 'actually said' not in err else 'NO'}"
          f"   {'✅' if ok else '🔴'}")
    fails += not ok

    print()
    if fails:
        print(f"  🔴 {fails} of 4 arms failed — do NOT ship the hook on this evidence.")
        return 1
    print("  ✅ 4 of 4: it says when it should, stays silent when it should, and "
          "the REAL arm proves the text is pasmo's own.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
