#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SUBSIG: what does EXBRSA ($FAF8, the MSX2 SUB-ROM slot cell) hold after
boot on the MSX1 references, and on zerobas, whose sub ROM writes it "for
convention compat" (basic/subrom-boot.asm)? Work-area RAM contents only.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = (("VG-8020", "Philips_VG_8020"), ("CF-3300", "National_CF-3300"),
            ("ZB-NODISK", "C-BIOS_MSX1_EU_REPACK_NODISK"),
            ("ZB-DISK", "C-BIOS_MSX1_EU_REPACK_DISK"))
LINE = 'PRINT"[X";PEEK(&HFAF8);PEEK(&HFAF9);"]"'


def main():
    for name, m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", [LINE])], batch=False,
                                  reset=("", "SCREEN 0"))[0] or ""
        got = re.findall(r"\[X\s*(\d+)\s+(\d+)\s*\]", re.sub(r"\s+", " ", raw))
        print(f"== {name:10s} FAF8 FAF9 = {got[-1] if got else None}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
