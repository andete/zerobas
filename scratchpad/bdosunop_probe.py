#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BDOSUNOP: CLOSE ($10) and SEQREAD ($14) through $F37D on an FCB that was never opened.
bdosset_probe.py's one row (NOSUCH.XYZ after a failed OPEN) read $FF / 1 on the CF-3300
and 0 / 0 here. Two rules fit it -- the CF-3300 SEARCHES the directory for the name, or it
reads a mark OPEN leaves in the FCB -- and they part only on a FILE THAT EXISTS but was
never opened, so that row is here, beside the opened control and the failed-OPEN case.
Black box: registers out, and every FCB's 37 bytes afterwards (RAM).

    DISKCORPUS_DIR=... python3 scratchpad/bdosunop_probe.py [cf,eu,zb]
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import omsx_preflight  # noqa: E402
import bdosset_probe as P  # noqa: E402

FCBS = {"NO": (0xC020, "NOSUCH  XYZ"), "EX": (0xC0A0, "SECOND  DAT"),
        "OP": (0xC0D0, "AUTOEXECBAS"), "NF": (0xC100, "NOSUCH  XYZ")}
F = {k: v[0] for k, v in FCBS.items()}
ROWS = [(0x1A, 0xD400, 0, "SETDTA $D400"), (0x0D, 0, 0, "DSKRST"),
        (0x10, F["NO"], 0, "CLOSE nosuch, fresh"), (0x14, F["NO"], 0, "SEQRD nosuch, fresh"),
        (0x10, F["EX"], 0, "CLOSE exists, fresh"), (0x14, F["EX"], 0, "SEQRD exists, fresh"),
        (0x0F, F["OP"], 0, "OPEN exists"), (0x14, F["OP"], 0, "SEQRD exists, open"),
        (0x10, F["OP"], 0, "CLOSE exists, open"), (0x10, F["OP"], 0, "CLOSE again"),
        (0x14, F["OP"], 0, "SEQRD after CLOSE"),
        (0x0F, F["NF"], 0, "OPEN nosuch"), (0x10, F["NF"], 0, "CLOSE after fail"),
        (0x14, F["NF"], 0, "SEQRD after fail")]
DUMP = 0xCA00
RUN_ROOT = {}                                 # the four FCBs, 37 B each, after the run


def program():
    def fcb(addr, name):
        return (f'FOR I=0 TO 36:POKE &H{addr:X}+I,0:NEXT:N$="{name}":'
                f'FOR I=1 TO 11:POKE &H{addr:X}+I,ASC(MID$(N$,I,1)):NEXT')
    lines = ["10 CLEAR 200,&HBFFF",
             f"20 FOR I=0 TO {len(P.MC) - 1}:READ A:POKE &HC000+I,A:NEXT"]
    lines += [f"{30 + k} " + fcb(a, n) for k, (a, n) in enumerate(FCBS.values())]
    lines += ["40 DEFUSR=&HC000",
              f"50 FOR R=0 TO {len(ROWS) - 1}:READ F,D,H",
              "60 POKE &HC0F0,F:POKE &HC0F2,D-INT(D/256)*256:POKE &HC0F3,INT(D/256):"
              "POKE &HC0F4,H-INT(H/256)*256:POKE &HC0F5,INT(H/256)",
              "70 X=USR(0):FOR J=0 TO 9:POKE &HC800+R*10+J,PEEK(&HC0F6+J):NEXT:"
              "POKE &HC7FF,R",
              "80 NEXT",
              "85 " + ":".join(f"FOR I=0 TO 36:POKE &H{DUMP + 37 * k:X}+I,PEEK(&H{a:X}+I):NEXT"
                               for k, (a, _) in enumerate(FCBS.values())),
              "86 POKE &HC7FE,165",
              "90 DATA " + ",".join(str(b) for b in P.MC)]
    for i in range(0, len(ROWS), 6):
        chunk = ROWS[i:i + 6]
        lines.append(f"{100 + i} DATA " + ",".join(f"{f},{d},{h}" for f, d, h, _ in chunk))
    return ("\r\n".join(lines) + "\r\n").encode("ascii") + b"\x1a"


def run(mkey, img):
    machine, extra = P.MACHINES[mkey]
    td = tempfile.mkdtemp(prefix="bdosunop_")
    try:
        dsk = os.path.join(td, "v.dsk")
        open(dsk, "wb").write(img)
        out = os.path.join(td, "m.txt")
        tcl = ("set throttle off\n"
               "after time 150 {\n"
               f"  set f [open {{{out}}} w]\n"
               "  binary scan [debug read_block memory 0xC7FE 2] H* flag\n"
               f"  binary scan [debug read_block memory 0xC800 {10 * len(ROWS)}] H* v\n"
               f"  binary scan [debug read_block memory {DUMP} {37 * len(FCBS)}] H* d\n"
               '  puts $f "$flag $v $d"\n  close $f\n  exit\n}\n')
        open(os.path.join(td, "s.tcl"), "w").write(tcl)
        subprocess.run(omsx_preflight.guarded(["/opt/homebrew/bin/openmsx", "-machine", machine] + extra +
                       ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                        "-script", os.path.join(td, "s.tcl")]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        img_after = open(dsk, "rb").read()
        RUN_ROOT[mkey] = img_after[7 * 512:7 * 512 + 64]  # root entries 0 and 1
        if not os.path.exists(out):
            return None, None, None
        flag, v, d = open(out).read().split()
        return bytes.fromhex(flag), bytes.fromhex(v), bytes.fromhex(d)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    keys = (sys.argv[1] if len(sys.argv) > 1 else "cf,eu,zb").split(",")
    P.program = program                       # bdosset_probe.image() builds from these
    P.ROWS = ROWS
    img = bytearray(P.image())
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "disk"))
    from disk_probe_bdos import fat12_add
    fat12_add(img, "SECOND", "DAT", b"HELLO, SECOND FILE\r\n" * 8)   # root entry 1
    img = bytes(img)
    res = {k: run(k, img) for k in keys}
    for k in keys:
        print(f"# {k}: done-flag {res[k][0].hex() if res[k][0] else None} (want a5 + last row "
              f"{len(ROWS) - 1:02x})")
    print("fn  what                 " + "  ".join(f"{k:>24s}" for k in keys))
    for i, (f, _d, _h, what) in enumerate(ROWS):
        cells = []
        for k in keys:
            v = res[k][1]
            if not v:
                cells.append(f"{'<no run>':>24s}")
                continue
            r = v[10 * i:10 * i + 10]
            hl, de, bc = (r[4] | r[5] << 8), (r[6] | r[7] << 8), (r[8] | r[9] << 8)
            cells.append(f"A={r[1]:02X} HL={hl:04X} DE={de:04X} BC={bc:04X}".rjust(24))
        print(f"{f:02X}  {what:20s} " + "  ".join(cells))
    print("# the FCBs afterwards, bytes +12..+36 (the name is the same everywhere)")
    for n, name in enumerate(FCBS):
        for k in keys:
            d = res[k][2]
            if d:
                print(f"  FCB {name} {k}: {d[37 * n + 12:37 * n + 37].hex(' ')}")
    for e in (0, 1):
        print(f"# root entry {e} before: {img[7 * 512 + 32 * e:7 * 512 + 32 * e + 32].hex(' ')}")
        for k in keys:
            print(f"# root entry {e} after {k}: {RUN_ROOT.get(k, b'')[32 * e:32 * e + 32].hex(' ')}")
    print("done")


if __name__ == "__main__":
    main()
