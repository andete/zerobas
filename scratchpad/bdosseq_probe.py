#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BDOSSEQ: a random write into a file still open from FMAKE, from BASIC's $F37D.

bdosset_probe.py's sequence (FMAKE, one SEQWRITE, ..., SETRND, RDRND, WRRND) never
returns from WRRND on zerobas since D-BDOSFCB stage A, but there the CF-3300's own
odd SETRND (RR $400001) aims its WRRND at record ~4 M. This drops SETRND: RR is
POKEd, as a program patching a record of the file it is writing would. Rows as
scratchpad/bdosfcb_probe.py (its machinery, its row record); black box: RAM only.

    DISKCORPUS_DIR=... python3 -u scratchpad/bdosseq_probe.py [cf,zb]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdosfcb_probe as F  # noqa: E402

NONE = F.NONE
F.ROWS = [
    (0x1A, 0, NONE, 0, -1, -1, "SETDTA $D400"),
    (0x16, 0, NONE, 1, -1, -1, "FMAKE R.DAT"),
    (0x15, 0, 0x11, 0, -1, -1, "SEQWR rec0 $11"),
    (0x22, 0, 0x22, 0, 128, 1, "WRRND RR1 $22"),
    (0x23, 0, NONE, 0, -1, -1, "FSIZE"),
    (0x22, 0, 0x33, 0, 128, 0, "WRRND RR0 $33"),
    (0x10, 0, NONE, 0, -1, -1, "FCLOSE"),
    (0x0F, 0, NONE, 1, -1, -1, "FOPEN"),
    (0x23, 0, NONE, 0, -1, -1, "FSIZE"),
    (0x21, 0, 0xEE, 0, 128, 0, "RDRND RR0"),
    (0x21, 0, 0xEE, 0, 128, 1, "RDRND RR1"),
    (0x10, 0, NONE, 0, -1, -1, "FCLOSE"),
]
if __name__ == "__main__":
    sys.exit(F.main())
