#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KOFFRAW -- print the answer FROM row 23, exactly as missing-acceptance does.

`WIDTH 40:CLS:KEY OFF:LOCATE 5,23` reads `23 5` on both machines when the answer
is printed after a `CLS` (D-KOFF23). `missing-acceptance` prints it from wherever
`LOCATE` left the cursor -- row 23, the last row -- and reports `<aborted>`,
which that file defines as "a `[` with no `]`". So this reproduces the suite's
shape and prints the RAW tail, to see whether the `]` is scrolled away rather
than never written.

🔴 FOUR HYPOTHESES HAVE ALREADY BEEN WRONG (an inc/dec drift on CRTCNT, `WIDTH`
resetting it, the statement itself, and batch contamination through the reset).
This stops guessing at the CAUSE and looks at the ARTEFACT.
⚠️ The KEY ON twin is the control: it leaves the cursor on row 22, so its `]`
has a row below it to survive on. If BOTH lose the `]`, the print position is
the whole story and `KEY` is incidental.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")


def prog(*body: str) -> list[str]:
    lines = list(body) + ["END"]
    for l in lines:
        assert len(l) <= 34, (len(l), l)
    return lines


CASES = [
    # the suite's shape: no CLS, the answer printed from the clamped row
    ("off23_raw", prog("WIDTH 40", "CLS", "KEY OFF", "LOCATE 5,23",
                       "Y=CSRLIN:X=POS(0)", 'PRINT"[";Y;X;"]"')),
    # the control: KEY ON leaves the cursor a row higher
    ("on23_raw",  prog("WIDTH 40", "KEY ON", "CLS", "LOCATE 5,23",
                       "Y=CSRLIN:X=POS(0)", 'PRINT"[";Y;X;"]"')),
    # and row 22 under KEY OFF, which the suite says PASSES
    ("off22_raw", prog("WIDTH 40", "CLS", "KEY OFF", "LOCATE 5,22",
                       "Y=CSRLIN:X=POS(0)", 'PRINT"[";Y;X;"]"')),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=12.0)
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}: "
                  f"{str(exc).splitlines()[0][:160]}", flush=True)
            continue
        for (name, _), raw in zip(CASES, raws):
            txt = "".join(raw or "")
            tail = " ".join(txt[-90:].split())
            print(f"  {name:11} tail={tail!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
