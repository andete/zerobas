#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xva14.asm's and xva13.asm's capture (xva.asm's record grown to 32 bytes) --
per case and call, the 17-bit address the VDP holds after the call (R#14 x $4000 + the pointer's 14 bits), the port
$99 writes the call made, and the mode cells (SCRMOD after CHGMOD / at the end, R#25, MODE, ACPAGE).
    python3 scratchpad/xva14_decode.py RUNFILE [--side ref|ours] [--names xva14|xva13]"""
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from xva_decode import portlog  # noqa: E402

CALLS = ("NSETRD", "NSETWR", "NRDVRM", "NWRVRM", "BIGFIL")

NAMES = {
    "xva14": ["S8 control", "CHGMOD 12", "S12 (R25 08)", "S10/11 (R25 18)", "S12 +SCRMOD12", "S11 +SCRMOD11",
              "S10 +SCRMOD10", "S-BASE S12", "S-BASE S10/11", "AC1 C123 S12", "AC1 C123 S10/11",
              "AC1 C123 S12+SM12", "SM10 R25 08", "SM10 R25 00", "SM10 AC1 C123", "SM10 AC3 C123",
              "SM10 AC2 1234"],
    "xva13": ["VA-1", "VA-2", "VA-3", "VA-4", "VA-5", "VA-6", "VA-7 S8", "VA-7 S7", "VA-8", "VA-9", "VA-10 S0/40",
              "VA-10 S0/80", "VA-10 S2", "VA-10 S3", "VA-10 S4", "VA-11", "VA-12", "VA-15", "VA-13",
              "VA-13 AC2", "VA-13 AC3", "VA-13 S8 AC1 C123", "VA-13 MODE:=10"],
}


def main():
    path = sys.argv[1]
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    names = NAMES[sys.argv[sys.argv.index("--names") + 1] if "--names" in sys.argv else "xva14"]
    t = open(path).read()
    for blk in re.split(r"^===== ", t, flags=re.M)[1:]:
        head = blk.split("\n", 1)[0]
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            print("#", head, "-- no", side, "capture")
            continue
        b = bytes.fromhex(m.group(1)) + bytes(4000)
        print("#", head.split(".asm ")[-1], side)
        for r in range(b[1] * 5):
            rec = b[2 + 32 * r: 34 + 32 * r]
            a, f, r14, plo, phi, n = rec[:6]
            addr = r14 * 0x4000 + ((phi << 8 | plo) & 0x3FFF)
            nm = names[rec[14]] if rec[14] < len(names) else str(rec[14])
            print(f"  {nm:18} {CALLS[rec[15]] if rec[15] < 5 else rec[15]:7} A={a:02X} addr=${addr:05X} FFED={rec[13]:02X} "
                  f"SCRMOD={rec[16]}/{rec[22]} R25={rec[17]:02X} R0={rec[18]:02X} R1={rec[19]:02X} "
                  f"MODE={rec[20]:02X} AC={rec[21]} writes={n:2} {portlog(rec[6:6 + min(n, 7)])}")


if __name__ == "__main__":
    main()
