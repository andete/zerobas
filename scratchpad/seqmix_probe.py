#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SEQMIX: SEQWRITE records still BUFFERED for file A, then RDBLK on another file B.

zerobas's sequential writer buffers its records in the shared sector buffer
(bdos_seqwrite_body -> SECTOR_BUF + BDOS_WRBUFLEN). seq_flush writes them out before
RDRND / WRRND read into that buffer (D-BDOSSEQ), but k47b2_seek (RDBLK) deliberately
does not flush -- so A's buffered record may be lost under B's sector. This asks both
machines. Two FCBs ($C020 = A.DAT, $C060 = B.DAT); scratchpad/bdosfcb_probe.py's
machinery (its USR caller, its disk image, its row record). Black box: RAM only.

    python3 -u scratchpad/seqmix_probe.py [cf,zb]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdosfcb_probe as F  # noqa: E402
import bdosset_probe as S  # noqa: E402

NONE = F.NONE
FCBA, FCBB, DTA = 0xC020, 0xC060, F.DTA
# (function, HL, DTA fill or NONE, re-zero + name the FCB first, RS or -1, RR or -1, FCB 0=A 1=B, what)
ROWS = [
    (0x1A, 0, NONE, 0, -1, -1, 0, "SETDTA $D400"),
    (0x16, 0, NONE, 1, -1, -1, 1, "FMAKE B.DAT"),
    (0x15, 0, 0xAA, 0, -1, -1, 1, "SEQWR B rec0 $AA"),
    (0x15, 0, 0xAA, 0, -1, -1, 1, "SEQWR B rec1 $AA"),
    (0x15, 0, 0xAA, 0, -1, -1, 1, "SEQWR B rec2 $AA"),
    (0x15, 0, 0xAA, 0, -1, -1, 1, "SEQWR B rec3 $AA"),
    (0x10, 0, NONE, 0, -1, -1, 1, "FCLOSE B"),
    (0x0F, 0, NONE, 1, -1, -1, 1, "FOPEN B"),
    (0x16, 0, NONE, 1, -1, -1, 0, "FMAKE A.DAT"),
    (0x15, 0, 0x11, 0, -1, -1, 0, "SEQWR A rec0 $11 (buffered)"),
    (0x27, 1, 0xEE, 0, 128, 0, 1, "RDBLK B RR0 x1"),
    (0x15, 0, 0x22, 0, -1, -1, 0, "SEQWR A rec1 $22"),
    (0x10, 0, NONE, 0, -1, -1, 0, "FCLOSE A"),
    (0x10, 0, NONE, 0, -1, -1, 1, "FCLOSE B"),
    (0x0F, 0, NONE, 1, -1, -1, 0, "FOPEN A"),
    (0x23, 0, NONE, 0, -1, -1, 0, "FSIZE A"),
    (0x21, 0, 0xEE, 0, 128, 0, 0, "RDRND A RR0 (want $11)"),
    (0x21, 0, 0xEE, 0, 128, 1, 0, "RDRND A RR1 (want $22)"),
    (0x10, 0, NONE, 0, -1, -1, 0, "FCLOSE A"),
]
REC = F.REC


def program():
    def name(fcb, n):
        return (f'FOR I=0 TO 36:POKE &H{fcb:X}+I,0:NEXT:N$="{n}":'
                f'FOR I=1 TO 11:POKE &H{fcb:X}+I,ASC(MID$(N$,I,1)):NEXT')
    lines = ["10 CLEAR 200,&HBFFF",
             f"20 FOR I=0 TO {len(S.MC) - 1}:READ A:POKE &HC000+I,A:NEXT",
             "30 DEFUSR=&HC000",
             f"40 FOR R=0 TO {len(ROWS) - 1}:READ F,H,V,Z,S,Q,C:D={FCBA}+C*{FCBB - FCBA}",
             f"50 IF Z AND C=0 THEN {name(FCBA, 'A       DAT')}",
             f"55 IF Z AND C=1 THEN {name(FCBB, 'B       DAT')}",
             f"60 IF V<256 THEN FOR I=0 TO 255:POKE &H{DTA:X}+I,V:NEXT",
             "70 IF S>=0 THEN POKE D+14,S:POKE D+15,0",
             "80 IF Q>=0 THEN POKE D+33,Q:POKE D+34,0:POKE D+35,0",
             f"90 IF F=26 THEN D={DTA}",
             "100 POKE &HC0F0,F:POKE &HC0F2,D-INT(D/256)*256:POKE &HC0F3,INT(D/256):"
             "POKE &HC0F4,H-INT(H/256)*256:POKE &HC0F5,INT(H/256)",
             f"110 X=USR(0):B=&HC800+R*{REC}:FOR J=0 TO 9:POKE B+J,PEEK(&HC0F6+J):NEXT",
             f"120 E={FCBA}+C*{FCBB - FCBA}:FOR J=0 TO 36:POKE B+10+J,PEEK(E+J):NEXT:"
             f"POKE B+47,PEEK(&H{DTA:X}):POKE B+48,PEEK(&H{DTA + 128:X}):POKE &HC7FF,R",
             "130 NEXT:POKE &HC7FE,165",
             "140 DATA " + ",".join(str(b) for b in S.MC)]
    for i in range(0, len(ROWS), 4):
        chunk = ROWS[i:i + 4]
        lines.append(f"{200 + i} DATA " + ",".join(
            f"{f},{h},{v},{z},{s},{q},{c}" for f, h, v, z, s, q, c, _ in chunk))
    return ("\r\n".join(lines) + "\r\n").encode("ascii") + b"\x1a"


if os.environ.get("SEQMIX_READ") == "seq":
    # the copy loop's usual read: SEQREAD (which runs seq_flush first) instead of RDBLK
    ROWS = [(0x14, 0, 0xEE, 0, -1, -1, 1, "SEQRD B rec0") if r[0] == 0x27 else r for r in ROWS]

if __name__ == "__main__":
    F.ROWS = [r[:6] + (r[7],) for r in ROWS]    # main() reads (f, ..., what); run() reads len(ROWS)
    F.program = program
    sys.exit(F.main())
