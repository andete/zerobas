#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BDOSBASIC slice 3: WHICH BDOS functions does $F37D answer from a BASIC program,
and with what? One row per function, on the CF-3300, the VG-8020 + NMS 1200 and
zerobas.

The disk is our own (the collection's empty.dsk plus an AUTOEXEC.BAS written here,
ASCII). The program POKEs a 31-byte caller at $C000 -- C, DE, HL from $C0F0..$C0F5,
CALL $F37D, then AF, HL, DE, BC to $C0F6..$C0FF -- and runs it once per row,
copying the ten result bytes to $C800 + 10 * row. Black box: registers in and out,
and our own RAM read back through the emulator's debugger; no ROM byte is read.

Not called (they wait for a key, a printer or an aux device, reset the machine,
or write a sector): $00, $01, $03, $04, $05, $07, $08, $0A, $2B, $2D, $30.
    DISKCORPUS_DIR=... python3 -u scratchpad/bdosset_probe.py [cf,eu,zb]
"""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpbrule_probe as B  # noqa: E402

MACHINES = B.MACHINES
FCB_NO, FCB_WILD, FCB_NEW = 0xC020, 0xC0A0, 0xC0D0
# (function, DE, HL, what)
ROWS = [(0x1A, 0xD400, 0, "SETDTA $D400"), (0x02, 0x0041, 0, "CONOUT 'A'"),
        (0x06, 0x00FF, 0, "DIRIO in"), (0x09, 0xC060, 0, "STROUT"),
        (0x0B, 0, 0, "CONST"), (0x0C, 0, 0, "VERSION"), (0x0D, 0, 0, "DSKRST"),
        (0x0E, 0x0000, 0, "SELDSK A"), (0x0F, FCB_NO, 0, "OPEN nosuch"),
        (0x10, FCB_NO, 0, "CLOSE unopened"), (0x11, FCB_WILD, 0, "SFIRST *.BAS"),
        (0x12, FCB_WILD, 0, "SNEXT"), (0x13, FCB_NO, 0, "DELETE nosuch"),
        (0x14, FCB_NO, 0, "SEQRD unopened"), (0x16, FCB_NEW, 0, "CREATE PROBE.TMP"),
        (0x15, FCB_NEW, 0, "SEQWR"), (0x17, FCB_NO, 0, "RENAME nosuch"),
        (0x18, 0, 0, "LOGIN"), (0x19, 0, 0, "CURDRV"), (0x1B, 0x0000, 0, "ALLOC"),
        (0x24, FCB_NEW, 0, "SETRND"), (0x21, FCB_NEW, 0, "RNDRD"),
        (0x22, FCB_NEW, 0, "RNDWR"), (0x23, FCB_NEW, 0, "FSIZE"),
        (0x26, FCB_NEW, 0, "WRBLK 0"), (0x27, FCB_NEW, 1, "RDBLK 1"),
        (0x28, FCB_NEW, 0, "WRZER"), (0x10, FCB_NEW, 0, "CLOSE"),
        (0x2A, 0, 0, "GDATE"), (0x2C, 0, 0, "GTIME"), (0x2E, 0x0000, 0, "VERIFY"),
        (0x2F, 0x0000, 0x0100, "ABSRD s0")]
MC = [0x3A, 0xF0, 0xC0, 0x4F, 0xED, 0x5B, 0xF2, 0xC0, 0x2A, 0xF4, 0xC0, 0xCD, 0x7D,
      0xF3, 0x22, 0xFA, 0xC0, 0xED, 0x53, 0xFC, 0xC0, 0xED, 0x43, 0xFE, 0xC0, 0xF5,
      0xE1, 0x22, 0xF6, 0xC0, 0xC9]


def program():
    def fcb(addr, name):
        return (f'FOR I=0 TO 36:POKE &H{addr:X}+I,0:NEXT:N$="{name}":'
                f'FOR I=1 TO 11:POKE &H{addr:X}+I,ASC(MID$(N$,I,1)):NEXT')
    lines = ["10 CLEAR 200,&HBFFF",
             f"20 FOR I=0 TO {len(MC) - 1}:READ A:POKE &HC000+I,A:NEXT",
             "30 " + fcb(FCB_NO, "NOSUCH  XYZ"),
             "31 " + fcb(FCB_WILD, "????????BAS"),
             "32 " + fcb(FCB_NEW, "PROBE   TMP"),
             '33 S$="OK$":FOR I=1 TO 3:POKE &HC05F+I,ASC(MID$(S$,I,1)):NEXT',
             "40 DEFUSR=&HC000",
             f"50 FOR R=0 TO {len(ROWS) - 1}:READ F,D,H",
             "60 POKE &HC0F0,F:POKE &HC0F2,D-INT(D/256)*256:POKE &HC0F3,INT(D/256):"
             "POKE &HC0F4,H-INT(H/256)*256:POKE &HC0F5,INT(H/256)",
             "70 X=USR(0):FOR J=0 TO 9:POKE &HC800+R*10+J,PEEK(&HC0F6+J):NEXT:"
             "POKE &HC7FF,R",
             "80 NEXT:POKE &HC7FE,165",
             "90 DATA " + ",".join(str(b) for b in MC)]
    for i in range(0, len(ROWS), 6):
        chunk = ROWS[i:i + 6]
        lines.append(f"{100 + i} DATA " + ",".join(f"{f},{d},{h}" for f, d, h, _ in chunk))
    return ("\r\n".join(lines) + "\r\n").encode("ascii") + b"\x1a"


def image():
    b = bytearray(B.base())
    prog = program()
    data = 14 * 512
    nclus = -(-len(prog) // 1024)
    for f in (1, 4):                           # FAT: clusters 2 .. 2+nclus-1 chained
        o = f * 512
        for k in range(nclus):
            c = 2 + k
            v = c + 1 if k < nclus - 1 else 0xFFF
            p = o + c * 3 // 2
            if c & 1:
                b[p] = (b[p] & 0x0F) | ((v << 4) & 0xF0)
                b[p + 1] = (v >> 4) & 0xFF
            else:
                b[p] = v & 0xFF
                b[p + 1] = (b[p + 1] & 0xF0) | (v >> 8)
    root = 7 * 512
    b[root + 28:root + 32] = len(prog).to_bytes(4, "little")
    b[data:data + nclus * 1024] = prog.ljust(nclus * 1024, b"\0")
    return bytes(b)


def run(mkey, img):
    machine, extra = MACHINES[mkey]
    td = tempfile.mkdtemp(prefix="bdosset_")
    try:
        dsk = os.path.join(td, "v.dsk")
        open(dsk, "wb").write(img)
        out = os.path.join(td, "m.txt")
        tcl = ("set throttle off\n"
               "after time 150 {\n"
               f"  set f [open {{{out}}} w]\n"
               "  binary scan [debug read_block memory 0xC7FE 2] H* flag\n"
               f"  binary scan [debug read_block memory 0xC800 {10 * len(ROWS)}] H* v\n"
               '  puts $f "$flag $v"\n  close $f\n  exit\n}\n')
        open(os.path.join(td, "s.tcl"), "w").write(tcl)
        subprocess.run(["/opt/homebrew/bin/openmsx", "-machine", machine] + extra +
                       ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                        "-script", os.path.join(td, "s.tcl")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        if not os.path.exists(out):
            return None, None
        flag, v = open(out).read().split()
        return bytes.fromhex(flag), bytes.fromhex(v)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    keys = (sys.argv[1] if len(sys.argv) > 1 else "cf,eu,zb").split(",")
    img = image()
    res = {}
    for k in keys:
        flag, v = run(k, img)
        res[k] = (flag, v)
        print(f"# {k}: done-flag {flag.hex() if flag else None} (want a5 + last row "
              f"{len(ROWS) - 1:02x})", flush=True)
    print("fn  what               " + "  ".join(f"{k:>24s}" for k in keys))
    for i, (f, d, h, what) in enumerate(ROWS):
        cells = []
        for k in keys:
            flag, v = res[k]
            if not v:
                cells.append(f"{'<no run>':>24s}")
                continue
            r = v[10 * i:10 * i + 10]
            f_, a = r[0], r[1]
            # $C0F6 AF (F, A), $C0F8-9 unused, $C0FA HL, $C0FC DE, $C0FE BC
            hl, de, bc = (r[4] | r[5] << 8), (r[6] | r[7] << 8), (r[8] | r[9] << 8)
            cells.append(f"A={a:02X} HL={hl:04X} DE={de:04X} BC={bc:04X}".rjust(24))
        print(f"{f:02X}  {what:18s} " + "  ".join(cells))
    print("done")


if __name__ == "__main__":
    main()
