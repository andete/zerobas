#!/usr/bin/env python3
"""D-DUPSPAN2/D-XREG left 38 `X equ Y` aliases behind. This asks the ONE question
neither tools/dupspan_indep.py nor check_tenant_closure.py can: does the alias
cross a CONDITIONAL-ASSEMBLY boundary?

An `equ` to a symbol that only exists when a build switch is 1 makes that switch
UNFLIPPABLE -- the disabled build stops assembling with an undefined symbol, far
from the alias, and no gate in this tree runs with a switch flipped. It is found
only by someone flipping one, which is what a scaffold does.

Prints every alias whose TARGET sits under a gate its own SITE does not.
"""
from __future__ import annotations
import glob
import re

ALIAS = re.compile(r"^(\w+)\s+equ\s+([A-Za-z_]\w*)\s*(?:;.*)?$")
IFS = re.compile(r"^\s*IF\s+(.+?)\s*$", re.I)
ENDIF = re.compile(r"^\s*ENDIF\s*$", re.I)
ELSE = re.compile(r"^\s*ELSE\s*$", re.I)
LABEL = re.compile(r"^(\w+):")


def scan(paths):
    """-> {symbol: (file, line, gate-stack)} for labels, and a list of aliases."""
    labels, aliases = {}, []
    for p in paths:
        stack = []
        for n, line in enumerate(open(p), 1):
            code = line.split(";", 1)[0].rstrip()
            if IFS.match(code):
                stack.append(IFS.match(code).group(1))
                continue
            if ENDIF.match(code):
                if stack:
                    stack.pop()
                continue
            if ELSE.match(code):
                if stack:
                    stack[-1] = "!(" + stack[-1] + ")"
                continue
            m = LABEL.match(line)
            if m:
                labels.setdefault(m.group(1), (p, n, tuple(stack)))
            m = ALIAS.match(line)
            if m:
                aliases.append((m.group(1), m.group(2), p, n, tuple(stack)))
    return labels, aliases


def main():
    paths = sorted(glob.glob("basic/*.asm") + glob.glob("basic/*.inc"))
    labels, aliases = scan(paths)
    bad = 0
    for name, tgt, p, n, site_gates in aliases:
        if tgt not in labels:
            continue
        tp, tn, tgt_gates = labels[tgt]
        unmet = [g for g in tgt_gates if g not in site_gates]
        if unmet:
            bad += 1
            print(f"  {p}:{n}  {name} equ {tgt}")
            print(f"      target {tp}:{tn} is under {unmet}; the site is under "
                  f"{list(site_gates) or 'nothing'}")
    print(f"\n  {len(aliases)} label aliases in basic/, {bad} cross a build gate")


if __name__ == "__main__":
    main()
