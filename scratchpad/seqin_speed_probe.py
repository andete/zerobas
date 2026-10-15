#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.C C1: how long does reading a disk file with LINE INPUT # take?

The C1 draft refills an INPUT channel 256 bytes at a time and so reads each
512-byte sector TWICE (its unit test counts it); the reader it replaced read each
sector once. This times LINE INPUT # over a 16 400-byte text file (400 lines of
39 characters + CR LF) with TIME (VDP frames), on the CF-3300 and on zerobas's
disk machine. Run it on two builds to compare them; the screen row is
[frames lines].
PREDICTED (C1 build): slower than the build before it, within TIER 2's 10x.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                    # noqa: E402
import loadrun_probe as LR                          # noqa: E402

TEXT = b"".join(b"%03d" % i + b"x" * 36 + b"\r\n" for i in range(400))
PROG = ["NEW", '10 OPEN"T.TXT"FOR INPUT AS#1:T=TIME:N=0',
        "20 IF EOF(1) THEN 40", "30 LINE INPUT#1,A$:N=N+1:GOTO 20",
        '40 PRINT"[";TIME-T;N;"]":CLOSE:END', "RUN"]


def main():
    machines = sys.argv[1:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
    tmp = tempfile.mkdtemp(prefix="seqspeed_")
    for m in machines:
        dsk = os.path.join(tmp, f"{m}.dsk")
        LR.write_files(dsk, {"T       TXT": TEXT})
        scr = omsx_repl.run_cases(m, [("direct", PROG)], batch=False, reset=("", "SCREEN 0:WIDTH 40"),
                                  step=3.0, run_gap=120.0, diska=dsk, capture="screen")[0]
        rows = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)] if scr else []
        print(m, [r for r in rows if r.startswith("[") or "rror" in r], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
