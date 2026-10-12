#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""C5-LOW (docs/plan-main-rom-space-2026-10.md, phase C-3): ERR 9, 10, 14 and
16's texts move from main (program.asm, str-engine.asm) into the sub-ROM's
errmsg tenant; err_msgtab's four rows point at err_subhosted. Anchored on
text; refuses on a missing or non-unique anchor."""
import sys

EDITS = [
    ("basic/program.asm",
     "err_subscript:  db      \"Subscript out of range\",0\n"
     "err_redim:      db      \"Redimensioned array\",0\n",
     "; C5-LOW (2026-10-12): err_subscript and err_redim are GONE from main -- ERR\n"
     "; 9 / 10's text is sub-hosted (sub/errmsg.asm em_subscript / em_redim) and\n"
     "; err_msgtab's rows 9 / 10 point at err_subhosted; the table was their only\n"
     "; reader.\n"),
    ("basic/str-engine.asm",
     "err_too_complex:                            ; D-MSGENC: no phrase hit here (the corpus\n"
     "                db      \"String formula too complex\",0  ; has one \"String\"); 29 B -> 27 B\n",
     "; C5-LOW (2026-10-12): err_too_complex is GONE from main -- ERR 16's text is\n"
     "; sub-hosted (sub/errmsg.asm em_too_complex); err_msgtab's row 16 points at\n"
     "; err_subhosted, its only reader.\n"),
    ("basic/str-engine.asm",
     "    IF CLEARPOOL\n"
     "err_out_of_str:\n"
     "                db      \"Out of string space\",0\n"
     "    ENDIF\n",
     "; C5-LOW (2026-10-12): err_out_of_str is GONE too -- ERR 14 is sub-hosted\n"
     "; (em_out_of_str) on BOTH switch settings, so CLEARPOOL=0's old\n"
     "; `Unprintable error` hole for ERR 14 closes with it.\n"),
    ("basic/islands.asm",
     "                dw      err_subscript       ; 9: subscript out of range (arrays' own\n"
     "                                            ; capitalised string; §9.5 keep)\n"
     "                dw      err_redim           ; 10: redimensioned array (arrays' own\n"
     "                                            ; capitalised string; §9.5 keep)\n",
     "                dw      err_subhosted       ; 9: Subscript out of range (C5-LOW:\n"
     "                                            ; sub-hosted, em_subscript)\n"
     "                dw      err_subhosted       ; 10: Redimensioned array (C5-LOW:\n"
     "                                            ; sub-hosted, em_redim)\n"),
    ("basic/islands.asm",
     "    IF CLEARPOOL\n"
     "                dw      err_out_of_str      ; 14: out of string space (D-CLP; was a\n"
     "    ELSE                                    ; hole until the pool could raise it)\n"
     "                dw      err_unprintable     ; 14: out of string space (hole)\n"
     "    ENDIF\n"
     "                                            ; hole until the pool could raise it)\n",
     "                dw      err_subhosted       ; 14: Out of string space (C5-LOW:\n"
     "                                            ; sub-hosted, em_out_of_str, on both\n"
     "                                            ; CLEARPOOL settings)\n"),
    ("basic/islands.asm",
     "                dw      err_too_complex     ; 16: string formula too complex\n",
     "                dw      err_subhosted       ; 16: String formula too complex (C5-LOW:\n"
     "                                            ; sub-hosted, em_too_complex)\n"),
    ("sub/errmsg.asm",
     "                db      8\n"
     "                dw      em_line\n",
     "                db      8\n"
     "                dw      em_line\n"
     "                db      9                   ; C5-LOW (2026-10-12): 9, 10, 14, 16\n"
     "                dw      em_subscript        ; moved here from main's low region\n"
     "                db      10\n"
     "                dw      em_redim\n"),
    ("sub/errmsg.asm",
     "                db      13\n"
     "                dw      em_type_mismatch\n",
     "                db      13\n"
     "                dw      em_type_mismatch\n"
     "                db      14\n"
     "                dw      em_out_of_str\n"),
    ("sub/errmsg.asm",
     "                db      15\n"
     "                dw      em_str_too_long\n",
     "                db      15\n"
     "                dw      em_str_too_long\n"
     "                db      16\n"
     "                dw      em_too_complex\n"),
    ("sub/errmsg.asm", "EM_ROWS         equ     31\n", "EM_ROWS         equ     35\n"),
    ("sub/errmsg.asm",
     "em_line:            db  \"Undefined line number\",0       ; ERR 8\n",
     "em_line:            db  \"Undefined line number\",0       ; ERR 8\n"
     "em_subscript:       db  \"Subscript out of range\",0      ; ERR 9  (C5-LOW)\n"
     "em_redim:           db  \"Redimensioned array\",0         ; ERR 10 (C5-LOW)\n"
     "em_out_of_str:      db  \"Out of string space\",0         ; ERR 14 (C5-LOW)\n"
     "em_too_complex:     db  \"String formula too complex\",0  ; ERR 16 (C5-LOW)\n"),
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
