#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PLAYX2b -- HOW DEEP does `X<var>;` nest? It is 3 B of RAM per level.

D-PLAYX2 found 2, 3, 4, 5 and 6 levels ALL working on the VG-8020 and found no
ceiling, which is not an answer -- it is the absence of one. The design in
`docs/spec-basic-audio-play.md` §7 needs a NUMBER, because the source-cursor
stack is a fixed table and every level costs 3 B of scarce RAM. This walks the
chain out to 24.

⚠️ A CHAIN IS BUILT FROM ONE-LETTER NAMES A$..X$, three per typed line (the
34-char stored-line budget). The DEEPEST variable carries the note; every
shallower one is `X<next>;` and nothing else, so a level that fails takes the
whole chain with it and the reading is unambiguous: the note sounds (53/0) or an
error is trapped.
🔴 THE CONTROL IS THE UNNESTED NOTE -- if that ever stops reading 53/0 the rig
is broken and no depth row means anything.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020",)
NOTE = "O7L1C"


def tone(*setup: str) -> list[str]:
    body = list(setup) + [
        "T=TIME",
        "IF TIME-T<30 THEN %d",
        'PRINT"<";',
        "OUT&HA0,0:PRINT INP(&HA2);",
        "OUT&HA0,1:PRINT INP(&HA2);",
        'PRINT">":END',
        'PRINT"<E";ERR;">":END',
    ]
    lines = ["ON ERROR GOTO %d" % (10 * (len(body) + 1))] + body
    for i, l in enumerate(lines):
        if "%d" in l:
            lines[i] = l % (10 * (i + 1))
    for l in lines:
        assert len(l) <= 34, (len(l), l)
    return lines


def chain(depth: int) -> list[str]:
    """A$ -> B$ -> ... -> the note, `depth` levels of X in all."""
    names = [chr(ord("A") + i) for i in range(depth)]
    asn = [f'{n}$="X{names[i + 1]}$;"' for i, n in enumerate(names[:-1])]
    asn.append(f'{names[-1]}$="{NOTE}"')
    out, cur = [], ""
    for a in asn:
        cand = a if not cur else cur + ":" + a
        if len(cand) <= 34:
            cur = cand
        else:
            out.append(cur)
            cur = a
    if cur:
        out.append(cur)
    return out + ['PLAY"XA$;"']


CASES = [("d00_control", tone(f'PLAY"{NOTE}"'))]
for d in (8, 10, 12, 16, 20, 24):
    CASES.append((f"d{d:02d}_deep", tone(*chain(d))))


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=8.0)
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            r = txt.rfind("RUN")
            tail = txt[r + 3:] if r >= 0 else txt
            i = tail.find("<")
            j = tail.find(">", i + 1)
            cell = tail[i:j + 1] if i >= 0 and j > i else "?" + tail[:40]
            print(f"  {name:13} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
