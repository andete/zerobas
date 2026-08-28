#!/usr/bin/env python3
r"""D-ENDIFWALK: does correcting the 30 phantom edges REVEAL any dead code?

30 of the 68 directive-ending span pairs get a corrected verdict of "this span
DOES terminate", so check_dead_code currently carries 30 fallthrough edges that
should not exist. Every one of them makes a label reachable that may not be, so
this is the direction that HIDES dead code.

Whether that matters is an empirical question, not a rhetorical one: run the
gate's own dead-set computation with the corrected `_last_code` monkeypatched in
and diff the verdict. The patch returns a SYNTHETIC `ret` when the corrected walk
says the span terminates, so `_is_terminator` -- which is fine and is not being
changed -- reaches the right answer through the same code path it always uses.
"""
import os, re, sys, io, contextlib
sys.path.insert(0, "tools")
import check_dead_code as cdc
import check_tenant_closure as ctc
import endif_walk_verdict as V          # the corrected walk, reused not re-written

orig = cdc.Spans._last_code.__func__ if hasattr(cdc.Spans._last_code, "__func__") \
       else cdc.Spans._last_code


def patched(lines):
    last = orig(lines)
    if last and V.DIRECTIVE.match(last.strip()):
        v = V.terminates(lines)
        if v is True:
            return "ret"                 # decided: it terminates
        if v is False:
            # decided: it does not -- hand back the last REAL instruction
            for c in reversed(lines):
                t = c.strip()
                if t and not V.LBL.match(t) and not V.DIRECTIVE.match(t):
                    return t
            return ""
        return last                      # UNDECIDED -> unchanged, edge kept
    return last


def run():
    buf = io.StringIO()
    rc = 0
    with contextlib.redirect_stdout(buf):
        try:
            rc = cdc.main(["check_dead_code.py",
                           "build/basic-reloc.sym", "build/sub.sym", "--report"])
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1
    return rc, buf.getvalue()


sys.path.insert(0, "scratchpad")
rc_before, out_before = run()
cdc.Spans._last_code = staticmethod(patched)
rc_after, out_after = run()

def dead_lines(o):
    return sorted(l.strip() for l in o.splitlines()
                  if re.search(r"\bdead\b", l, re.I) and l.strip().startswith(("-", "*", " ")))

print(f"rc BEFORE (stock walk)     : {rc_before}")
print(f"rc AFTER  (corrected walk) : {rc_after}")
b, a = set(dead_lines(out_before)), set(dead_lines(out_after))
print(f"\ndead-report lines: before {len(b)}, after {len(a)}, NEW {len(a - b)}")
for l in sorted(a - b):
    print("  NEW:", l[:140])
tb = [l for l in out_before.splitlines() if "TOTAL" in l.upper() or "dead" in l.lower()][-4:]
ta = [l for l in out_after.splitlines() if "TOTAL" in l.upper() or "dead" in l.lower()][-4:]
print("\ntail BEFORE:"); [print("   ", l.strip()[:150]) for l in tb]
print("tail AFTER :"); [print("   ", l.strip()[:150]) for l in ta]
