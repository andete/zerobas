#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CNSDFG -- does the KEY state already live in a cell, so we need no new RAM?

Building option (c) needs the window bound to follow `KEY ON`/`KEY OFF`. The
obvious move is a new RAM byte -- but RAM HAS NO GATE here and both cells this
tree documents as retired-and-free are already spent (`GFX_DJ` $E220, `GFX_BAD`
$E3E5). MSX documents **`CNSDFG` ($F3DE)**, the function-key DISPLAY FLAG, which
`DSPFNK`/`ERAFNK` maintain -- and `key_on`/`key_off` already call both. If it
moves on our target too, the bound derives from it and costs ZERO new RAM.

⚠️ IT MUST MOVE ON BOTH MACHINES OR IT IS NOT USABLE: a cell that tracks KEY on
the reference and sits still here would make the clamp read a constant, which is
the mistake `CRTCNT` already was (24 on both, in both states).
🔴 THE READING IS A PAIR, NOT A VALUE. What matters is ON vs OFF on the SAME
machine; the absolute number is allowed to differ between machines.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")


def prog(*body: str) -> list[str]:
    lines = ["ON ERROR GOTO @T"] + list(body) + ["END", 'PRINT"<C";ERR;">":END']
    lines[0] = "ON ERROR GOTO %d" % (10 * len(lines))
    for l in lines:
        assert len(l) <= 34, (len(l), l)
        assert "@" not in l, l
    return lines


CASES = [
    ("on_cnsdfg",  prog("KEY ON",  'PRINT"<C";PEEK(&HF3DE);">"')),
    ("off_cnsdfg", prog("KEY OFF", 'PRINT"<C";PEEK(&HF3DE);">"')),
    # the pair, read in ONE run so no boot difference can explain a change
    ("pair",       prog("KEY OFF", "A=PEEK(&HF3DE)", "KEY ON",
                        'PRINT"<C";A;PEEK(&HF3DE);">"')),
    # 🔴 the control: a cell NOBODY claims must NOT move with KEY, or the probe
    # is reading something that changes for another reason entirely
    ("ctl_crtcnt", prog("KEY OFF", "A=PEEK(&HF3B1)", "KEY ON",
                        'PRINT"<C";A;PEEK(&HF3B1);">"')),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=10.0)
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}: "
                  f"{str(exc).splitlines()[0][:160]}", flush=True)
            continue
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("<C")
            j = txt.find(">", i + 1)
            cell = txt[i:j + 1] if i >= 0 and j > i else "<no reading>"
            print(f"  {name:12} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
