#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xmode.asm (the sub-ROM screen-mode calls).
    python3 scratchpad/xmode_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

NAMES = [f"CHGMOD {a}" for a in list(range(10)) + [255]] + ["INITXT", "INIT32", "INIGRP", "INIMLT", "SETTXT",
         "SETT32", "SETGRP", "SETMLT", "SETPAG 1/0", "SETPAG 0/1", "SETPAG 3/2", "CHGMDP 5", "CHGMOD 10",
         "CHGMOD 11", "CHGMOD 12"]


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(4000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side, "cases", b[1])
        for k in range(b[1]):
            r = b[2 + 96 * k: 98 + 96 * k]
            vdp = r[4:32]
            cp = list(r[32:40]) + list(r[40:62])
            # the copies that disagree with the VDP (R#0-7 vs $F3DF.., R#8-27 vs $FFE7..)
            dis = [f"R{i}" for i in range(8) if cp[i] != vdp[i]] + [f"R{8 + i}" for i in range(20) if cp[8 + i] != vdp[8 + i]]
            cells = " ".join(f"{r[66 + 2 * i] | r[67 + 2 * i] << 8:04X}" for i in range(5))
            print(f"  {NAMES[r[3]]:12} A={r[0]:02X} F={r[1]:02X} IFF={r[2]} R0-9={vdp[:10].hex()} R25-27={vdp[25:28].hex()}"
                  f" SCRMOD={r[62]} OLD={r[63]} LINLEN={r[64]} CRTCNT={r[65]} cells={cells} DP/AC={r[76]}/{r[77]}"
                  f" copy!=vdp:{','.join(dis) or '-'}")


if __name__ == "__main__":
    main()
