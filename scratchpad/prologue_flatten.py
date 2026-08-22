#!/usr/bin/env python3
"""Is the per-file fallthrough model wrong, and where?

Builds the FLATTENED line sequence (includes spliced in place, the assembler's
own view), recomputes spans over it, and compares its fallthrough edges against
the shipped per-file model. The question that decides the fix: for each file
whose prologue emits NOTHING, is its first label genuinely entered by
fallthrough from the code physically before the `include` line?
"""
import importlib.util, os, re, sys
spec = importlib.util.spec_from_file_location("cdc", "tools/check_dead_code.py")
cdc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cdc)

INC = re.compile(r'^\s*include\s+"([^"]+)"', re.IGNORECASE)


def flatten(top, build, seen=None):
    """[(file, lineno, code)] in assembly order, includes spliced in place."""
    out = []
    for i, raw in enumerate(open(top, errors='ignore'), 1):
        code = raw.split(';', 1)[0]
        m = INC.match(code)
        if m:
            tgt = cdc._resolve(m.group(1), build)
            if os.path.exists(tgt):
                out.extend(flatten(tgt, build))
                continue
        out.append((top, i, code))
    return out


def spans_over(flat):
    """[(label, file, [code lines])] in flat order."""
    spans, cur = [], None
    for f, ln, code in flat:
        mm = cdc.ctc._LBL.match(code)
        if mm:
            cur = [mm.group(1), f, []]
            spans.append(cur)
        elif cur is not None:
            cur[2].append(code)
    return spans


for top, build in [('basic/main.asm', 'main'), ('sub/sub.asm', 'sub')]:
    m = cdc.Spans(top, build)
    flat = flatten(top, build)
    fs = spans_over(flat)
    print(f"\n=== {build}: {len(flat)} flattened lines, {len(fs)} spans in flat order ===")

    # first labels of files whose prologue emits nothing
    empty_first = {}
    for f in m.files:
        order = m.seq[f]
        if len(order) >= 2 and not cdc.Spans._last_code(m.nodes.get(order[0], [])):
            empty_first[order[1]] = f

    # in FLAT order, who physically precedes each of those labels, and does it fall through?
    genuine, guarded = [], []
    for i, (name, f, lines) in enumerate(fs):
        if name not in empty_first or i == 0:
            continue
        pname, pf, plines = fs[i - 1]
        last = cdc.Spans._last_code(plines)
        if cdc.ctc._is_terminator(last):
            guarded.append((name, pname, last))
        else:
            genuine.append((name, pname, last))
    print(f"  first labels with an empty prologue, reached in flat order: "
          f"{len(guarded) + len(genuine)}")
    print(f"    predecessor ENDS in a terminator (no real fallthrough): {len(guarded)}")
    print(f"    predecessor FALLS THROUGH (edge is REAL)             : {len(genuine)}")
    for name, pname, last in genuine:
        print(f"      🔴 {name:24s} <- {pname:24s} last={last[:44]!r}")
