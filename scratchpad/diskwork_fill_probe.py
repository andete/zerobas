#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BOOTKEYS residual (2026-10-20): after a SHIFT boot the CF-3300 leaves $F347 at 255
(untouched) and zerobas reads 201 ($C9). C-BIOS's init_ram fills $F300..$F37F ("Disk work")
with $C9 on every boot. Does the VG-8020 (diskless) leave that range alone too, and what does
zerobas NODISK hold there? Counts the bytes of $F300..$F37F by value: [$C9 $FF $00 other].
Work-area RAM only; no ROM byte is read.
    python3 -u scratchpad/diskwork_fill_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

BODY = ["A=0:B=0:C=0:D=0:FOR I=&HF300 TO &HF37F:P=PEEK(I)",
        "IF P=201 THEN A=A+1 ELSE IF P=255 THEN B=B+1 ELSE IF P=0 THEN C=C+1 ELSE D=D+1",
        'NEXT:PRINT"[";A;B;C;D;"]"']


def main():
    for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        r = omsx_repl.run_cases(m, [("stored", BODY)], reset=("CLS",), batch=False, run_gap=30.0,
                                cap_gap=15.0)[0]
        v = re.findall(r"\[([\s\d]+)\]", (r or "").replace("\n", ""))
        print(f"{m:30} $F300..$F37F  [C9 FF 00 other] = [{' '.join(v[-1].split()) if v else 'NO READING'}]",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
