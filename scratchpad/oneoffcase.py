#!/usr/bin/env python3
"""Is the ONE-OFF shape really 0 today? `'Foo' in x.lower()` and its mirrors."""
import ast, glob, os
def folded(n, meth):
    """Does this expression end in .lower()/.upper()?"""
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == meth)
hits = []
for p in sorted(glob.glob("probes/**/*.py", recursive=True)
                + glob.glob("tools/**/*.py", recursive=True)
                + glob.glob("tests/**/*.py", recursive=True)
                + glob.glob("scratchpad/*.py")):
    try:
        t = ast.parse(open(p, encoding="utf-8", errors="replace").read())
    except SyntaxError:
        continue
    for n in ast.walk(t):
        if not isinstance(n, ast.Compare) or len(n.ops) != 1:
            continue
        L, R, op = n.left, n.comparators[0], n.ops[0]
        for lit, other in ((L, R), (R, L)):
            if not (isinstance(lit, ast.Constant) and isinstance(lit.value, str)):
                continue
            v = lit.value
            for meth, wrong in (("lower", v != v.lower()), ("upper", v != v.upper())):
                if folded(other, meth) and wrong and v.strip():
                    hits.append((p, n.lineno, v, meth,
                                 type(op).__name__))
for p, l, v, m, o in hits:
    print(f"🔴 {p}:{l}  {v!r} {o} <expr>.{m}()  -- can never match")
print(f"{len(hits)} one-off case-folded comparison(s) that can never match")
