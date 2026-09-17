#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SCROLLBOUND -- what governs the CONSOLE SCROLL region, and can we move it?

Joost: finish `KEY ON`/`KEY OFF` identical to the reference. D-FNKLINE shipped
the painting; the half left is that thirty `PRINT`s settle at row **22** on the
reference under `KEY ON` and at **23** here, so output reaching the bottom
scrolls the painted line away. Screen output goes through the BIOS `CHPUT`, so
the scroll region is the BIOS's -- the question is whether it reads a cell WE can
write.

`CRTCNT` ($F3B1) is the documented text-row count and the obvious candidate. ⚠️
IT READS 24 ON BOTH MACHINES IN BOTH KEY STATES (D-CNSDFG), so it is NOT how the
reference expresses `KEY ON` -- but that does not tell us whether our C-BIOS's
`CHPUT` USES it. Those are different questions and only the second one decides
whether a fix exists.

  * `*_poke` POKEs CRTCNT to 23, prints thirty lines and reads `CSRLIN`. If the
    settle row drops to 22, CRTCNT IS the scroll bound on that machine.
  * `*_plain` is the same case WITHOUT the poke -- the control, which must read
    23, or the poke proved nothing.
  * `ref_on_crtcnt` re-reads CRTCNT under `KEY ON` in this same run, so the
    "24 in both states" fact is not inherited from another probe.

🔴 BOTH MACHINES: if the poke moves the reference too, then CRTCNT is the BIOS
mechanism on both and the reference's `KEY ON` must drive it from somewhere we
have not found -- which is a different fix from "our CHPUT ignores it".
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")


def prog(*body: str) -> list[str]:
    lines = ["ON ERROR GOTO @T"] + list(body) + ["END", 'PRINT"<S";ERR;">":END']
    lines[0] = "ON ERROR GOTO %d" % (10 * len(lines))
    for l in lines:
        assert len(l) <= 34, (len(l), l)
        assert "@" not in l, l
    return lines


def settle(*setup: str):
    """`setup`, then thirty PRINTs, then where the cursor ended up."""
    return prog(*setup, "FOR I=1 TO 30", 'PRINT"x"', "NEXT",
                "A=CSRLIN", "CLS", 'PRINT"<S";A;">"')


CASES = [
    ("off_plain",      settle("KEY OFF")),
    ("off_poke23",     settle("KEY OFF", "POKE &HF3B1,23")),
    ("on_plain",       settle("KEY ON")),
    ("on_poke23",      settle("KEY ON", "POKE &HF3B1,23")),
    ("ref_on_crtcnt",  prog("KEY ON", 'PRINT"<S";PEEK(&HF3B1);">"')),
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
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("<S")
            j = txt.find(">", i + 1)
            cell = txt[i:j + 1] if i >= 0 and j > i else "<no reading>"
            print(f"  {name:15} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
