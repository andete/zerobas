#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-AUTORUN: call H.READ after the prompt and H.MAIN before each line read.
Anchored on text; refuses on a missing or non-unique anchor."""
import sys

EDITS = [
    ("basic/sysvars.inc",
     "H_TIMI          equ     $FD9F",
     "; D-AUTORUN: the two prompt hooks, as the VG-8020 calls them (measured,\n"
     "; scratchpad/autorun_order_probe.out / autorun_seq_probe.out): H.READ once\n"
     "; the prompt is printed, H.MAIN before every line is read. openMSX's tape\n"
     "; autorun waits on both. Unclaimed (a bare RET) on all four machines,\n"
     "; scratchpad/autorun_cell_probe.out.\n"
     "H_READ          equ     $FF07   ; prompt printed (\"Ok\" / ZB)\n"
     "H_MAIN          equ     $FF0C   ; about to read a line at command level\n"
     "H_TIMI          equ     $FD9F"),
    ("basic/repl.asm",
     "                ld      hl,prompt_text\n"
     "                call    print_string\n"
     "repl_read:\n"
     "                call    read_line           ; LINEBUF <- typed line (ASCII, 0-term)\n",
     "                ld      hl,prompt_text\n"
     "                call    print_string\n"
     "                call    H_READ              ; D-AUTORUN: the prompt is up (the\n"
     "                                            ; reference: every prompt, R then M)\n"
     "repl_read:\n"
     "                call    H_MAIN              ; D-AUTORUN: a line is about to be\n"
     "                                            ; read -- also after a STORED line,\n"
     "                                            ; which has no prompt (M alone)\n"
     "                call    read_line           ; LINEBUF <- typed line (ASCII, 0-term)\n"),
]

texts = {}
for path, old, new in EDITS:
    s = texts.get(path) or open(path, encoding="utf-8").read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSED: {path}: anchor count {n}: {old[:60]!r}")
    texts[path] = s.replace(old, new)
for path, s in texts.items():
    open(path, "w", encoding="utf-8").write(s)
    print("edited", path)
