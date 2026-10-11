#!/usr/bin/env python3
"""D-PASMO053, part 2: pasmo 0.5.3 assembles a use of a label ALIAS (`X equ lbl`)
that comes ABOVE the alias's own equ line as $0000 -- two passes, and the
alias's pass-1 value was taken before `lbl` existed. 13 operands in main differed
from 0.5.5's. Every involved alias moves to basic/aliases-early.inc, included
right after sysvars.inc, so it is defined before any use. Zero bytes."""
import re, sys

ALIASES = [  # (file, name) -- order matters for chains: err_illegal_fn first
    ("basic/interp.asm", "err_illegal_fn"), ("basic/subromcall.asm", "err_subrom_absent"),
    ("basic/float.asm", "flt_int_result"), ("basic/input.asm", "inpc_synpop"),
    ("basic/float-arith.asm", "raf_zero_ok"), ("basic/vars.asm", "vlf_unset_int"),
    ("basic/program.asm", "rn_in"), ("basic/program.asm", "eoi_err5"),
    ("basic/files.asm", "fchk_ifc"), ("basic/interp.asm", "ex_donothing"),
    ("basic/interp.asm", "ev_f_attr"), ("basic/graphics.asm", "elg_syntax"),
    ("basic/graphics.asm", "ep_syntax"), ("basic/graphics.asm", "gfx_syntax"),
    ("basic/print.asm", "exp_pos_syn"),
]
moved = []
for f, n in ALIASES:
    s = open(f).read()
    rx = re.compile(r"^(" + n + r"\s+equ\s+(\S+)[^\n]*)\n", re.M)
    m = rx.findall(s)
    if len(m) != 1:
        sys.exit(f"REFUSE {f}: {n} found {len(m)}x")
    line, target = m[0]
    s = rx.sub(f"; ({n} = {target}: its equ is in basic/aliases-early.inc -- "
               f"pasmo 0.5.3, D-PASMO053)\n", s)
    open(f, "w").write(s)
    moved.append((f, line))
    print(f"ok {f}: {n}")

hdr = """; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; aliases-early.inc -- label ALIASES that must be defined before any use.
; ===========================================================================
; 🔴 D-PASMO053 (2026-10-11). pasmo 0.5.3 -- the version Debian / Ubuntu ship --
; assembles in two passes, and an alias `X equ lbl` is evaluated in pass 1 before
; `lbl` exists: it is 0 then. In pass 2 every use of X ABOVE its equ line still
; reads that 0. 0.5.5 resolves it; 0.5.3 built a main ROM with 13 jump and
; pointer operands of $0000, silently. So these aliases live HERE, included
; right after sysvars.inc, above every use. (Plain forward references to LABELS
; are fine on both versions; only an alias of a label defined later bites.)
; A new alias used above its own definition needs the same treatment; the CI
; build with the distribution's pasmo 0.5.3, checked against the committed
; images, is what catches one that does not get it.
; Each comment says where the alias used to live, beside its notes.
; ===========================================================================
"""
body = "".join(f"{line}\n                                ; (was {f})\n" for f, line in moved)
open("basic/aliases-early.inc", "w").write(hdr + body)
print("wrote basic/aliases-early.inc")

M = "basic/main.asm"
s = open(M).read()
a = """DISK_BUILD      equ     0
                include "basic/sysvars.inc"
"""
b = """DISK_BUILD      equ     0
                include "basic/sysvars.inc"
                include "basic/aliases-early.inc"   ; D-PASMO053: before any use
"""
if s.count(a) != 1:
    sys.exit("REFUSE main include")
s = s.replace(a, b)
a2 = """; forward references across `include`s are fine for a whole-file multi-pass
; assembler like pasmo; only ORG-based layout needs include order."""
b2 = """; forward references across `include`s are fine for a whole-file multi-pass
; assembler like pasmo; only ORG-based layout needs include order. (Forward
; references to LABELS. An `equ` ALIAS of a later label used above its own
; line is $0000 under pasmo 0.5.3 -- basic/aliases-early.inc, D-PASMO053.)"""
if s.count(a2) != 1:
    sys.exit("REFUSE main comment")
open(M, "w").write(s.replace(a2, b2))
print("ok basic/main.asm")
