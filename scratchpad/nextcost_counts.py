#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""How many times does ONE `NEXT` call each float-core routine?

D-BRKFRAME's corrected profile puts an EMPTY `FOR I=1 TO n:NEXT` at 17.5% in
`d10_lp` -- a binary divide-by-ten -- with no arithmetic in the program text at
all. That is a reading. This counts the CALLS, with openMSX breakpoints, at two
loop lengths so every fixed cost (tokenising, the FOR setup, the final PRINT)
cancels in the difference and only the per-iteration cost survives.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp

WANT = ["div10", "widen_uint_to", "widen_int_to", "wsrc_unpack",
        "round_and_finalize", "fp_add", "cmp16_bits", "exec_stmt"]
syms = {}
for line in open(os.path.join(REPO, "build", "basic-reloc.sym"), encoding="utf-8", errors="replace"):
    m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
    if m and m.group(1) in WANT:
        syms[m.group(1)] = int(m.group(2), 16)
missing = [w for w in WANT if w not in syms]
assert not missing, f"symbols not found, so nothing would be counted: {missing}"

def run(n):
    cfg = probe_sides.sides("zb")["zb"]
    log = probe_tmp.tmp(f"nextcost_{n}.log")
    bps = "\n".join(f'debug set_bp 0x{a:04X} {{}} {{ incr ::c({k}) }}' for k, a in syms.items())
    dump = " ; ".join(f'puts $::f "{k} $::c({k})"' for k in syms)
    pro = ("array set ::c { " + " ".join(f"{k} 0" for k in syms) + " }\n" + bps + "\n"
           f'after time 55 {{ set ::f [open "{log}" w] ; {dump} ; flush $::f ; close $::f }}\n')
    lines = [f'10 FOR I=1 TO {n}:NEXT', '20 PRINT"[done]"', "RUN"]
    omsx_repl.run_cases(cfg["machine"], [("c", lines)], batch=False, boot=cfg["boot"],
                        reset=cfg["reset"], prologue=(pro,), run_gap=65.0)
    return {k: int(v) for k, v in (l.split() for l in open(log).read().split("\n") if l.strip())}

LO, HI = 20, 220
a, b = run(LO), run(HI)
print(f"  per NEXT, from ({HI}-{LO}) iterations:")
for k in WANT:
    d = b[k] - a[k]
    print(f"    {k:20} {d/(HI-LO):8.2f}   (n={LO}: {a[k]}, n={HI}: {b[k]})")
