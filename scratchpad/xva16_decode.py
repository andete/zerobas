#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xva16.asm's capture (VA-16: a frame interrupt swept through NSETRD / NSETWR /
NRDVRM / NWRVRM / BIGFIL and the probe's own four port writes).  Per row and side: the calibration, then per call each step k
-- where the interrupt landed (`-` none before the snapshot, `pre` before the call's log was armed, `in@n` while
INCALL was set with n port $99 writes logged, `post@n` after the return), the address after (R#14 x $4000 + the
pointer's 14 bits, `!` = not the no-interrupt address), IFF2 after the return (twice), the writes logged in all.
    python3 scratchpad/xva16_decode.py RUNFILE [--side ref|ours] [--all]   (--all: every step, else a summary)"""
import re
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from xva_decode import portlog  # noqa: E402

CALLS = ("NSETRD", "NSETWR", "NRDVRM", "NWRVRM", "control", "BIGFIL")
# the address after the call with no interrupt (VA-1 in xva.asm / xva14.asm): a read setting pre-fetches (+1),
# NRDVRM's read, NWRVRM's write and BIGFIL's one byte add one more
EXPECT = (0x01235, 0x01234, 0x01236, 0x01235, 0x01234, 0x01235)


def where(mark, at):
    if not mark & 0x80:
        return "-"
    if at == 0xFF:
        return "pre"
    return f"{'in' if mark & 1 else 'post'}@{at}"


def main():
    path = sys.argv[1]
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    t = open(path).read()
    for blk in re.split(r"^===== ", t, flags=re.M)[1:]:
        head = blk.split("\n", 1)[0]
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(9000)
        print("#", head.split(".asm ")[-1].rstrip(" ="), side, f"-- calibration {b[2] | b[3] << 8} iterations/frame")
        for c in range(b[1]):
            cnt, wrong, logs = Counter(), [], Counter()
            r0 = b[4 + 16 * c * 96: 20 + 16 * c * 96]
            print(f"  {CALLS[c]}: (calibration {r0[14] | r0[15] << 8})")
            for k in range(96):
                rec = b[4 + 16 * (c * 96 + k): 20 + 16 * (c * 96 + k)]
                kk, cc, mark, at, n, r14, plo, phi, f1, f2 = rec[:10]
                assert kk == k and cc == c, (c, k, kk, cc)
                addr = r14 * 0x4000 + ((phi << 8 | plo) & 0x3FFF)
                w = where(mark, at)
                ok = addr == EXPECT[c]
                cat = w.split("@")[0] + ("@" + w.split("@")[1] if "@" in w and w.startswith("in") else "")
                cnt[(cat, ok, f"IFF {f1 >> 2 & 1}{f2 >> 2 & 1}", n)] += 1
                lg = portlog(rec[10:10 + min(n, 4)])
                logs[lg] += 1
                if "--all" in sys.argv:
                    print(f"    k={k:2} irq={w:7} addr=${addr:05X}{' ' if ok else '!'} IFF2={f1 >> 2 & 1}{f2 >> 2 & 1} "
                          f"writes={n} {lg}")
                if not ok:
                    wrong.append((k, w, f"${addr:05X}", lg))
            for key, v in sorted(cnt.items(), key=lambda kv: str(kv[0])):
                print(f"    {v:3} x irq {key[0]:5} addr {'right' if key[1] else 'WRONG'}, {key[2]}, {key[3]} writes")
            for k, w, a, lg in wrong:
                print(f"    WRONG k={k} irq={w} addr={a} log={lg}")
            print(f"    logs: {dict(logs)}")


if __name__ == "__main__":
    main()
