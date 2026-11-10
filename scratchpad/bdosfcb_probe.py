#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BDOSFCB step 1: what the $F37D BDOS does, from a BASIC program, to ONE REAL FILE.

scratchpad/bdosset_probe.py asked every function once, mostly of FCBs never opened;
this one makes a file and runs the random-record and block functions on it, as a
BASIC program calling the BDOS would: FMAKE, four SEQWRITEs, FCLOSE; FOPEN; RDRND,
FSIZE, RDBLK at RR 1, SETRND, WRRND past the end, WRBLK, WRZER, FSIZE, FCLOSE; FOPEN
again and read back the gap, the zeroed record and record 0.

Each row records the registers ($C0F6..: AF, HL, DE, BC -- the caller of
bdosset_probe.py), the whole 37-byte FCB and the DTA's bytes 0 and 128, all OUR RAM
read back through the emulator's debugger. Black box: no ROM byte is read.

    DISKCORPUS_DIR=... python3 -u scratchpad/bdosfcb_probe.py [cf,eu,zb]
"""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
sys.path.insert(0, HERE)
import omsx_preflight  # noqa: E402
import bdosset_probe as S  # noqa: E402  (the caller, the image, the machines)

FCB, DTA = 0xC020, 0xD400
NONE = 256
# (function, HL, DTA fill byte or NONE, re-zero the FCB first, RS or -1, RR or -1, what)
ROWS = [
    (0x1A, 0, NONE, 0, -1, -1, "SETDTA $D400"),
    (0x16, 0, NONE, 1, -1, -1, "FMAKE R.DAT"),
    (0x15, 0, 0x11, 0, -1, -1, "SEQWR rec0 $11"),
    (0x15, 0, 0x22, 0, -1, -1, "SEQWR rec1 $22"),
    (0x15, 0, 0x33, 0, -1, -1, "SEQWR rec2 $33"),
    (0x15, 0, 0x44, 0, -1, -1, "SEQWR rec3 $44"),
    (0x10, 0, NONE, 0, -1, -1, "FCLOSE"),
    (0x0F, 0, NONE, 1, -1, -1, "FOPEN R.DAT"),
    (0x21, 0, 0xEE, 0, 128, 2, "RDRND RR2"),
    (0x23, 0, NONE, 0, -1, -1, "FSIZE"),
    (0x27, 2, 0xEE, 0, 128, 1, "RDBLK RR1 x2"),
    (0x24, 0, NONE, 0, -1, -1, "SETRND"),
    (0x22, 0, 0x66, 0, 128, 5, "WRRND RR5 $66"),
    (0x23, 0, NONE, 0, -1, -1, "FSIZE"),
    (0x26, 1, 0x77, 0, 128, 6, "WRBLK RR6 x1 $77"),
    (0x28, 0, 0x88, 0, 128, 9, "WRZER RR9"),
    (0x23, 0, NONE, 0, -1, -1, "FSIZE"),
    (0x10, 0, NONE, 0, -1, -1, "FCLOSE"),
    (0x0F, 0, NONE, 1, -1, -1, "FOPEN again"),
    (0x23, 0, NONE, 0, -1, -1, "FSIZE"),
    (0x21, 0, 0xEE, 0, 128, 4, "RDRND RR4 (gap)"),
    (0x21, 0, 0xEE, 0, 128, 9, "RDRND RR9 (WRZER)"),
    (0x21, 0, 0xEE, 0, 128, 6, "RDRND RR6 (WRBLK)"),
    (0x14, 0, 0xEE, 0, -1, -1, "SEQRD"),
    (0x10, 0, NONE, 0, -1, -1, "FCLOSE"),
]
REC = 50                                         # regs 10, FCB 37, DTA[0], DTA[128], pad


def program():
    p = (f'FOR I=0 TO 36:POKE &H{FCB:X}+I,0:NEXT:N$="R       DAT":'
         f'FOR I=1 TO 11:POKE &H{FCB:X}+I,ASC(MID$(N$,I,1)):NEXT')
    lines = ["10 CLEAR 200,&HBFFF",
             f"20 FOR I=0 TO {len(S.MC) - 1}:READ A:POKE &HC000+I,A:NEXT",
             "30 DEFUSR=&HC000",
             f"40 FOR R=0 TO {len(ROWS) - 1}:READ F,H,V,Z,S,Q",
             f"50 IF Z THEN {p}",
             f"60 IF V<256 THEN FOR I=0 TO 255:POKE &H{DTA:X}+I,V:NEXT",
             f"70 IF S>=0 THEN POKE &H{FCB + 14:X},S:POKE &H{FCB + 15:X},0",
             f"80 IF Q>=0 THEN POKE &H{FCB + 33:X},Q:POKE &H{FCB + 34:X},0:POKE &H{FCB + 35:X},0",
             f"90 IF F=26 THEN D={DTA} ELSE D={FCB}",
             "100 POKE &HC0F0,F:POKE &HC0F2,D-INT(D/256)*256:POKE &HC0F3,INT(D/256):"
             "POKE &HC0F4,H-INT(H/256)*256:POKE &HC0F5,INT(H/256)",
             f"110 X=USR(0):B=&HC800+R*{REC}:FOR J=0 TO 9:POKE B+J,PEEK(&HC0F6+J):NEXT",
             f"120 FOR J=0 TO 36:POKE B+10+J,PEEK(&H{FCB:X}+J):NEXT:"
             f"POKE B+47,PEEK(&H{DTA:X}):POKE B+48,PEEK(&H{DTA + 128:X}):POKE &HC7FF,R",
             "130 NEXT:POKE &HC7FE,165",
             "140 DATA " + ",".join(str(b) for b in S.MC)]
    for i in range(0, len(ROWS), 5):
        chunk = ROWS[i:i + 5]
        lines.append(f"{200 + i} DATA " + ",".join(
            f"{f},{h},{v},{z},{s},{q}" for f, h, v, z, s, q, _ in chunk))
    return ("\r\n".join(lines) + "\r\n").encode("ascii") + b"\x1a"


def run(mkey, img):
    machine, extra = S.MACHINES[mkey]
    td = tempfile.mkdtemp(prefix="bdosfcb_")
    try:
        dsk = os.path.join(td, "v.dsk")
        open(dsk, "wb").write(img)
        out = os.path.join(td, "m.txt")
        tcl = ("set throttle off\n"
               "after time 300 {\n"
               f"  set f [open {{{out}}} w]\n"
               "  binary scan [debug read_block memory 0xC7FE 2] H* flag\n"
               f"  binary scan [debug read_block memory 0xC800 {REC * len(ROWS)}] H* v\n"
               '  puts $f "$flag $v"\n  close $f\n  exit\n}\n')
        open(os.path.join(td, "s.tcl"), "w").write(tcl)
        subprocess.run(omsx_preflight.guarded(["/opt/homebrew/bin/openmsx", "-machine", machine] + extra +
                       ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                        "-script", os.path.join(td, "s.tcl")]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        if not os.path.exists(out):
            return None, None
        flag, v = open(out).read().split()
        return bytes.fromhex(flag), bytes.fromhex(v)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def image():
    S.program = program                        # bdosset's image() embeds program()
    return S.image()


def main():
    keys = (sys.argv[1] if len(sys.argv) > 1 else "cf,zb").split(",")
    img = image()
    res = {k: run(k, img) for k in keys}
    for k in keys:
        flag = res[k][0]
        print(f"# {k}: done-flag {flag.hex() if flag else None} (want a5 + last row "
              f"{len(ROWS) - 1:02x})", flush=True)
    for i, (f, *_rest, what) in enumerate(ROWS):
        print(f"{i:2d} {f:02X} {what}")
        for k in keys:
            v = res[k][1]
            if not v:
                print(f"     {k}: <no run>")
                continue
            r = v[REC * i:REC * i + REC]
            a, hl, bc = r[1], r[4] | r[5] << 8, r[8] | r[9] << 8
            fcb = r[10:47]
            print(f"     {k}: A={a:02X} HL={hl:04X} BC={bc:04X} "
                  f"FCB+12..35={fcb[12:36].hex(' ')} DTA0={r[47]:02X} DTA128={r[48]:02X}")
    print("done")


if __name__ == "__main__":
    main()
