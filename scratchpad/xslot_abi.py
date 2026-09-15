#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-XSLOTABI phase 1 -- what does a page-1 inter-slot call actually PRESERVE?

hk_mkfloat reasons from "CALSLT is documented to affect most of them" and stages
everything in RAM as a result. That is a safe default, but it is a DOCUMENT
talking, not this machine -- and every staged byte is work the call-back ABI
would have to pay on every argument. So ask the machine.

The disk side loads HL/DE/BC/A with distinct values, calls through to a bare
`ret` that already exists in main page 1, and writes them all back. IX is absent
because CALSLT consumes it as the target; IY is read back because it carries the
slot id and is expected to be gone.

⚠️ THE BUFFER IS ZEROED FIRST, from BASIC, so "the value survived" is separable
from "nothing was ever written there". Without that a stale byte reads as a pass.
"""
from __future__ import annotations
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
BUF = 0xE700
# what the disk side loaded, little-endian as stored
WANT = [("HL", 0, [0x34, 0x12]), ("DE", 2, [0x78, 0x56]),
        ("BC", 4, [0xBC, 0x9A]), ("A", 6, [0x5A])]

PROG = [
    "10 FOR I=0 TO 18:POKE &HE700+I,0:NEXT",
    '20 X=CVI("AB")',
    '30 PRINT "[";',
    "40 FOR I=0 TO 18",
    "50 PRINT PEEK(&HE700+I);",
    "60 NEXT",
    '70 PRINT "]"',
    "RUN",
]


def main() -> int:
    for ln in PROG:
        if len(ln) > 38:
            print(f"INSTRUMENT FAULT: {len(ln)} cols: {ln!r}")
            return 2
    caps = omsx_repl.run_cases(ZB, [("abi", PROG)], batch=False, reset=(),
                               boot=8.0, step=3.0, cap_gap=45.0, timeout=600.0)
    scr = caps[0] or ""
    m = re.search(r"\[((?:\s+-?\d+){19})\s*\]", scr)
    if not m:
        print("=== screen ===\n" + scr)
        print("\nINSTRUMENT FAULT (rc 2): the fence never printed.")
        return 2
    got = [int(x) for x in m.group(1).split()]
    print(f"read back from ${BUF:04X}: " + " ".join(f"{b:02X}" for b in got))
    if all(b == 0 for b in got):
        print("\nINSTRUMENT FAULT (rc 2): every byte is still zero -- the probe "
              "never ran, so this says nothing about preservation.")
        return 2
    print()
    for name, off, want in WANT:
        have = got[off:off + len(want)]
        ok = have == want
        print(f"  {name:3s} in ${''.join(f'{b:02X}' for b in reversed(want))} "
              f"-> out ${''.join(f'{b:02X}' for b in reversed(have))}  "
              f"{'PRESERVED' if ok else 'CLOBBERED'}")
    iy = got[7] | (got[8] << 8)
    print(f"  IY  -> ${iy:04X}  (carries the slot id; expected to be gone)")
    print("\n  INBOUND leg -- what the hook (RST 30h / CALLF) delivered:")
    hl_in = got[9] | (got[10] << 8); de_in = got[11] | (got[12] << 8)
    bc_in = got[13] | (got[14] << 8)
    print(f"    HL ${hl_in:04X}  (main set the hook cell: H_CVI = $FE3F)")
    print(f"    DE ${de_in:04X}  (main set ev_cv_back, a main page-1 address)")
    print(f"    BC ${bc_in:04X}, C = {got[15]}  (main set C = the width = 2)")
    hl_mod = got[17] | (got[18] << 8)
    print("\n  MODIFIED-REGISTER return -- callee was `inc hl / ret` at $40A3:")
    print(f"    HL in $1111 -> out ${hl_mod:04X}  "
          + ("the callee's OWN value came back" if hl_mod == 0x1112
             else "🔴 NOT the callee's value"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
