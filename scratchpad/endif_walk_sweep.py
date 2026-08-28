#!/usr/bin/env python3
r"""D-ENDIFWALK scout: how many spans does the backwards walk end on a DIRECTIVE?

TODO.md (filed 2026-08-22 by D-DUPSPAN §2.1): `check_dead_code._last_code` skips
blank lines and bare labels but NOT conditional-assembly directives, so a span
whose last source line is `ENDIF` gets asked "is `endif` a terminator?" --
and `_is_terminator` correctly answers no, because it is not an instruction.

The consequence is a fallthrough EDGE that should not exist. In check_dead_code
that edge makes the next label reachable, so it is the direction that HIDES dead
code -- a gate going quiet, not a gate crying wolf.

Measure the denominator first: which spans end on a directive, and for each, what
does the construct's last REAL instruction do?
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.chdir(ROOT)
import check_dead_code as cdc
import check_tenant_closure as ctc

DIRECTIVE = re.compile(
    r"^(endif|else|endm|end|if|ifdef|ifndef|macro|local|proc|endp|public|"
    r"module|endmodule|align|org|include|incbin|rept|endr|\.\w+)\b", re.I)

for top, build in (("basic/main.asm", "main"), ("sub/sub.asm", "sub")):
    sp = cdc.Spans(top, build)
    tot = ends_directive = 0
    rows = []
    for order in sp.seq.values():
        for a, b in zip(order, order[1:]):
            last = cdc.Spans._last_code(sp.nodes.get(a, []))
            if not last:
                continue
            tot += 1
            if DIRECTIVE.match(last.strip()):
                ends_directive += 1
                rows.append((a, b, last.strip(), sp.owner.get(a, "?")))
    print(f"=== {build}: {tot} span pairs with a last code line; "
          f"{ends_directive} END ON A DIRECTIVE")
    for a, b, last, f in rows:
        # what is the last REAL instruction before that directive?
        real = ""
        for c in reversed(sp.nodes.get(a, [])):
            t = c.strip()
            if t and not re.match(r"^\w+:$", t) and not DIRECTIVE.match(t):
                real = t
                break
        verdict = ("terminates" if ctc._is_terminator(real) else "FALLS THROUGH")
        print(f"  {f}: {a} -> {b}")
        print(f"      last line   : {last!r}   (_is_terminator -> "
              f"{ctc._is_terminator(last)})")
        print(f"      last REAL   : {real!r}   -> {verdict}")
