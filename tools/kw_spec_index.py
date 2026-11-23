#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/keywords/spec-index.md -- every keyword page, its REGION and its SPEC state (D-KWSPEC; the plan is
docs/keywords/spec-plan.md, the method docs/spec-method.md). The keyword counterpart of tools/bios_spec_index.py.

The denominator is the keyword pages themselves (docs/keywords/<KW>.md, every one listed in docs/keywords/README.md).
Every page must have a REGION here: a page without one refuses, so the index cannot quietly lose a keyword; a
REGION naming no page refuses too. A page's spec state comes from its own `> **Spec:** <STATE>` line (DRAFT n /
REVIEWED n / FINAL); a page without one is still a USER page ("user page"), which is not an error while the loop
works region by region. Its open count is the number of `[A]` tags; its differences are the TODO items its
"Differences from the reference" section names.

    python3 tools/kw_spec_index.py            -- print the index
    python3 tools/kw_spec_index.py --write    -- write docs/keywords/spec-index.md
    python3 tools/kw_spec_index.py --check    -- fail when the index is stale
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, "docs", "keywords")
INDEX = os.path.join(PAGES, "spec-index.md")
NOT_KEYWORDS = {"README.md", "about.md", "spec-plan.md", "spec-index.md"}

# region -> (its concept page, relative to docs/keywords/, or None; the harness its probes use -- spec-plan.md §3)
REGION_INFO = {
    "strings": ("../concepts/strings-and-string-space.md", "RAM record"),
    "maths": ("../concepts/numbers.md", "RAM record"),
    "conversion": ("../concepts/numbers.md", "RAM record"),
    "operators": ("../concepts/numbers.md", "RAM record"),
    "composite": (None, "per statement"),
    "flow": ("../concepts/program-text.md", "RAM record + screen"),
    "errors": ("../concepts/errors.md", "RAM record + screen"),
    "program": ("../concepts/program-text.md", "screen + program text"),
    "memory": ("../concepts/memory-map.md", "RAM record + ports"),
    "text": ("../concepts/screen-editor.md", "screen + work area"),
    "graphics": ("../concepts/screen-modes.md", "VRAM + VDP registers"),
    "sound-input": ("../concepts/sound-calls.md", "PSG registers + held keys / rig"),
    "files": ("../concepts/files-and-devices.md", "tape image / disk image + screen"),
    "disk": ("../concepts/disk.md", "disk image + screen (CF-3300)"),
}
# the regions in the loop's ORDER (spec-plan.md §2); the keywords as docs/keywords/README.md groups them
REGIONS = {
    "strings": "LEN LEFT$ RIGHT$ MID$ ASC CHR$ INSTR SPACE$ STRING$ STR$ VAL HEX$ OCT$ BIN$",
    "maths": "ABS SGN INT FIX SQR EXP LOG SIN COS TAN ATN RND",
    "conversion": "CINT CSNG CDBL MKI$ MKS$ MKD$ CVI CVS CVD",
    "operators": "AND OR XOR EQV IMP NOT MOD LET SWAP",
    "flow": "GOTO GOSUB RETURN IF FOR NEXT END STOP CONT RUN",
    "errors": "ERR ERL ERROR RESUME TRON TROFF REM DEFINT DEFSNG DEFDBL DEFSTR",
    "program": "NEW LIST LLIST DELETE RENUM AUTO DATA READ RESTORE DIM ERASE CLEAR",
    "memory": "PEEK POKE VARPTR FRE USR FN BASE INP OUT WAIT TIME",
    "composite": "ON DEF GET PUT",
    "text": "PRINT LPRINT CLS LOCATE CSRLIN POS LPOS WIDTH SCREEN COLOR KEY",
    "graphics": "PSET PRESET LINE CIRCLE PAINT DRAW POINT SPRITE VDP VPEEK VPOKE",
    "sound-input": "BEEP SOUND PLAY INKEY$ INPUT STICK STRIG PAD PDL MOTOR",
    "files": "OPEN CLOSE EOF LOAD SAVE MERGE BLOAD BSAVE CLOAD CSAVE",
    "disk": "FILES LFILES KILL NAME COPY DSKF DSKI$ DSKO$ FIELD LSET RSET LOC LOF IPL CMD SET",
}
REGION_OF = {k: r for r, names in REGIONS.items() for k in names.split()}


def page_text(kw):
    return open(os.path.join(PAGES, f"{kw}.md"), encoding="utf-8").read()


def state(text):
    m = re.search(r"\*\*Spec:\*\*\s*(FINAL|REVIEWED \d+|DRAFT \d+)", text)
    return m.group(1) if m else "user page"


def items(text):
    m = re.search(r"^## Differences from the reference\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    seen = []
    for d in re.findall(r"\bD-[A-Z0-9]+\b", m.group(1) if m else ""):
        if d not in seen:
            seen.append(d)
    return seen


def reference(text):
    m = re.search(r"<!-- example:.*?reference=(\S+)", text)
    return m.group(1) if m else "—"


def rows():
    pages = sorted(f[:-3] for f in os.listdir(PAGES) if f.endswith(".md") and f not in NOT_KEYWORDS)
    missing = [k for k in pages if k not in REGION_OF]
    if missing:
        sys.exit(f"FAIL: keyword pages with no REGION in tools/kw_spec_index.py: {missing}")
    extra = sorted(set(REGION_OF) - set(pages))
    if extra:
        sys.exit(f"FAIL: REGIONS names a keyword with no page: {extra}")
    out = []
    for region, names in REGIONS.items():
        for kw in names.split():
            t = page_text(kw)
            st = state(t)
            out.append((kw, region, reference(t), st, t.count("[A]") if st != "user page" else None, items(t)))
    return out


def render():
    rs = rows()
    n_spec = sum(1 for r in rs if r[3] != "user page")
    n_final = sum(1 for r in rs if r[3] == "FINAL")
    L = ["<!--",
         "Copyright (c) 2026 Joost Yervante Damad",
         "SPDX-License-Identifier: BSD-2-Clause",
         "-->",
         "<!-- GENERATED by tools/kw_spec_index.py -- do not edit; `make kw-spec-index` -->",
         "",
         "# The BASIC keywords as a specification",
         "",
         "← [Keyword pages](README.md)",
         "",
         "Every keyword page, the region the spec loop takes it in, and how far its page has become a "
         "SPECIFICATION: measured rules, each checked against the reference machine's cases "
         "([the plan](spec-plan.md), [the method](../spec-method.md)). A page that is not yet a spec is a "
         "\"user page\": it says what the keyword does and was checked by its example, but its sentences are not "
         "yet executable rules. The reference is the Philips VG-8020; disk statements, the National CF-3300.",
         "",
         f"**{n_spec} of {len(rs)} keyword pages are specs; {n_final} are FINAL.**",
         "",
         "| keyword | region | harness | reference | page | open (not measured) | differences (TODO items, from the page) |",
         "|---|---|---|---|---|---|---|"]
    for kw, region, ref, st, nopen, its in rs:
        cp, harness = REGION_INFO[region]
        reg = f"[{region}]({cp})" if cp else region
        L.append(f"| `{kw}` | {reg} | {harness} | {ref} | [{st}]({kw}.md) | "
                 f"{'—' if nopen is None else nopen} | {', '.join(its) or '—'} |")
    L.append("")
    L.append("Reference: the machine the page's example and cases were measured on (its `<!-- example: -->` line). "
             "Harness: how the region's probes read a keyword's behaviour ([spec-plan.md §3](spec-plan.md)).")
    return "\n".join(L) + "\n"


def main():
    text = render()
    if "--write" in sys.argv:
        open(INDEX, "w", encoding="utf-8").write(text)
        print(f"wrote {os.path.relpath(INDEX, ROOT)}")
    elif "--check" in sys.argv:
        cur = open(INDEX, encoding="utf-8").read() if os.path.exists(INDEX) else ""
        if cur != text:
            print("🔴 kw-spec-index-check: docs/keywords/spec-index.md DIFFERS from its generator -- run "
                  "`make kw-spec-index`")
            return 1
        print("kw-spec-index-check: docs/keywords/spec-index.md matches its generator")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
