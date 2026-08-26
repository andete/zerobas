#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KNIFEGUARD — does the atexit restore actually fire on the FAILURE path?

Every knife runner writes a cut into a real source file and writes the pristine
bytes back at the END of the loop body -- after the asserts. An assertion that
fires in between leaves the SOURCE CUT, and the next thing measured is a knifed
machine. It happened: midop_knives.py exited on a sub.rom assertion and the next
invocation reported "anchor appears 0 times", which reads as a bad anchor and is
really a dirty tree. 🔴 THE ROM-HASH GUARD CANNOT SEE THIS -- the hash
legitimately differs from the baseline it was handed.

Two arms, because "the file came back" is only evidence if something could have
left it cut:

  RED    a runner WITH the hook dies mid-cut  -> the source must be PRISTINE
  GREEN  the same WITHOUT the hook            -> the source must stay CUT

⚠️ THE GREEN ARM IS THE LOAD-BEARING ONE. Without it, a red arm that passes
proves only that nothing cut the file -- not that the hook restored it.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402


def arm(with_hook: bool) -> str:
    d = probe_tmp.tmp("knifeguard")
    os.makedirs(d, exist_ok=True)
    src = os.path.join(d, "victim.asm")
    open(src, "w").write("PRISTINE\n")
    body = textwrap.dedent(f"""
        import atexit
        SRC = {src!r}
        original = open(SRC).read()
        {"atexit.register(lambda: open(SRC, 'w').write(original))"
         if with_hook else "pass"}
        open(SRC, "w").write("CUT\\n")
        assert False, "an assertion fires mid-cut, exactly as midop did"
    """)
    subprocess.run([sys.executable, "-c", body], capture_output=True)
    return open(src).read().strip()


def main() -> int:
    red, green = arm(True), arm(False)
    ok_red, ok_green = red == "PRISTINE", green == "CUT"
    print(f"  RED    with the hook, after a mid-cut assert -> {red!r}"
          f"   {'✅ restored' if ok_red else '🔴 NOT restored'}")
    print(f"  GREEN  without it,    after a mid-cut assert -> {green!r}"
          f"   {'✅ stayed cut' if ok_green else '🔴 control did not go red'}")
    if not ok_green:
        print("\n  🔴 THE CONTROL DID NOT GO RED, so the RED arm proves nothing:")
        print("     something other than the hook is restoring the file.")
        return 2
    if not ok_red:
        print("\n  🔴 the hook did not restore — do NOT ship.")
        return 1
    print("\n  ✅ 2 of 2: the hook restores on the failure path, and the control")
    print("     shows the file really would have stayed cut without it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
