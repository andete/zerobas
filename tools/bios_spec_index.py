#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/index.md -- every MSX1 BIOS entry, its region, its contract level and its PAGE's spec
state (docs/spec-method.md: one page per call, docs/bios/<NAME>.md, which is both the user page
and the specification).

The entry list is tools/entry_table.py's BIOS (the same denominator as docs/tier-status.md), the
level is tools/bios_levels.py's. A page's state comes from its own `> **Spec:** <STATE>` line
(none / DRAFT n / REVIEWED n / FINAL); its open count is the number of `[A]` (assumed, not
measured) tags on it. Every entry must have a REGION here: a new BIOS row without one refuses,
so the index cannot quietly lose a call.

    python3 tools/bios_spec_index.py            -- print the index
    python3 tools/bios_spec_index.py --write    -- write docs/bios/index.md
    python3 tools/bios_spec_index.py --check    -- fail when docs/bios/index.md is stale, or a
                                                   page names no known entry
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import entry_table  # noqa: E402
import bios_levels  # noqa: E402

PAGES = os.path.join(ROOT, "docs", "bios")
INDEX = os.path.join(PAGES, "index.md")

# region -> (the concept page that carries its shared facts, or None: not written yet)
REGION_PAGE = {
    "text": "../concepts/screen-editor.md",
    "vdp": "../concepts/screen-modes.md",
    "graphics": None,
    "input": None,
    "sound": None,
    "slots": None,
    "system": "../concepts/interrupts-and-traps.md",
    "interpreter": None,
    "devices": "../concepts/files-and-devices.md",
    "tape": "../concepts/cassette.md",
    "disk": "../concepts/disk.md",
}
REGIONS = {
    "text": "CHSNS CHGET CHPUT CNVCHR PINLIN INLIN QINLIN CLS POSIT FNKSB ERAFNK DSPFNK TOTEXT "
            "INIFNK INITXT INIT32",
    "vdp": "DISSCR ENASCR WRTVDP RDVRM WRTVRM SETRD SETWRT FILVRM LDIRMV LDIRVM CHGMOD CHGCLR "
           "CLRSPR INIGRP INIMLT SETTXT SETT32 SETGRP SETMLT CALPAT CALATR GSPSIZ RDVDP",
    "graphics": "GRPPRT RIGHTC LEFTC UPC TUPC DOWNC TDOWNC SCALXY MAPXYC FETCHC STOREC SETATR "
                "READC SETC NSETCX GTASPC PNTINI SCANR SCANL",
    "input": "BREAKX ISCNTC CKCNTC KILBUF SNSMAT GTSTCK GTTRIG GTPAD GTPDL CHGCAP",
    "sound": "GICINI WRTPSG RDPSG STRTMS BEEP CHGSND LFTQ PUTQ GETVCP GETVC2",
    "slots": "RDSLT WRSLT CALSLT ENASLT CALLF RSLREG WSLREG CALBAS",
    "system": "CHKRAM KEYINT NMI INITIO",
    "interpreter": "SYNCHR CHRGTR DCOMPR GETYPR",
    "devices": "LPTOUT LPTSTT OUTDO OUTDLP ISFLIO",
    "tape": "TAPION TAPIN TAPIOF TAPOON TAPOUT TAPOOF STMOTR",
    "disk": "PHYDIO FORMAT",
}
REGION_OF = {n: r for r, names in REGIONS.items() for n in names.split()}


def page_items(name):
    """the TODO items (D-...) the page's own "Differences from the reference" section names, in order"""
    path = os.path.join(PAGES, f"{name}.md")
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^## Differences from the reference\n(.*?)(?=^## )", text, re.S | re.M)
    seen = []
    for d in re.findall(r"\bD-[A-Z0-9]+\b", m.group(1) if m else ""):
        if d not in seen:
            seen.append(d)
    return seen


def page_state(name):
    """(state, open [A] count, relative link) for a call's page, or ("none", None, None)."""
    path = os.path.join(PAGES, f"{name}.md")
    if not os.path.exists(path):
        return "none", None, None
    text = open(path, encoding="utf-8").read()
    m = re.search(r"\*\*Spec:\*\*\s*(FINAL|REVIEWED \d+|DRAFT \d+)", text)
    if not m:
        sys.exit(f"FAIL: docs/bios/{name}.md has no `> **Spec:** <FINAL | REVIEWED n | DRAFT n>` "
                 f"line (docs/spec-method.md)")
    return m.group(1), text.count("[A]"), f"{name}.md"


def rows():
    missing = [n for _, n in entry_table.BIOS if n not in REGION_OF]
    if missing:
        sys.exit(f"FAIL: BIOS entries with no REGION in tools/bios_spec_index.py: {missing}")
    extra = sorted(set(REGION_OF) - {n for _, n in entry_table.BIOS})
    if extra:
        sys.exit(f"FAIL: REGION names no BIOS entry: {extra}")
    out = []
    for addr, name in entry_table.BIOS:
        lv = bios_levels.LEVELS.get(addr)
        level = f"L{lv[0]}" if lv else "—"
        ruled = addr in entry_table.BIOS_RULED
        state, nopen, link = page_state(name)
        out.append((addr, name, REGION_OF[name], level, ruled, state, nopen, link))
    return out


def render():
    rs = rows()
    known = {n for _, n in entry_table.BIOS}
    strays = sorted(f for f in os.listdir(PAGES) if f.endswith(".md") and f != "index.md"
                    and f[:-3] not in known) if os.path.isdir(PAGES) else []
    if strays:
        sys.exit(f"FAIL: docs/bios/ pages that name no BIOS entry: {strays}")
    n_page = sum(1 for r in rs if r[5] != "none")
    n_final = sum(1 for r in rs if r[5] == "FINAL")
    L = ["<!--",
         "Copyright (c) 2026 Joost Yervante Damad",
         "SPDX-License-Identifier: 0BSD",
         "-->",
         "<!-- GENERATED by tools/bios_spec_index.py -- do not edit; `make bios-spec-index` -->",
         "",
         "# The MSX1 BIOS calls",
         "",
         "One page per BIOS call: what it does, its contract as measured against the reference "
         "machines, and how zerobas differs. How the pages are made: "
         "[docs/spec-method.md](../spec-method.md). What every call shares (where the BIOS lives, how to call "
         "it, hooks, the work area): [the BIOS concept page](../concepts/bios.md). The shared facts of a region "
         "live in its concept page, not repeated on each call's page.",
         "",
         f"**{n_page} of {len(rs)} calls have a page; {n_final} are FINAL.**",
         "",
         "| address | call | region | contract level | page | open (not measured) | differences (TODO items, from the page) |",
         "|---|---|---|---|---|---|---|"]
    for addr, name, region, level, ruled, state, nopen, link in rs:
        rp = REGION_PAGE[region]
        reg = f"[{region}]({rp})" if rp else f"{region} (concept page to come)"
        lvl = level + (" · ruled indirect" if ruled else "")
        page = f"[{state}]({link})" if link else "—"
        op = str(nopen) if nopen is not None else "—"
        items = ", ".join(page_items(name)) or "—"
        L.append(f"| ${addr:04X} | {name} | {reg} | {lvl} | {page} | {op} | {items} |")
    L.append("")
    L.append("Contract level: tools/bios_levels.py (L1 called · L2 happy path · L3 full contract · "
             "L4 errors / edges), measured against the VG-8020. It says how much a GATE compares; the "
             "page says what the call DOES.")
    return "\n".join(L) + "\n"


def main():
    text = render()
    if "--write" in sys.argv:
        os.makedirs(PAGES, exist_ok=True)
        open(INDEX, "w", encoding="utf-8").write(text)
        print(f"wrote {os.path.relpath(INDEX, ROOT)}")
    elif "--check" in sys.argv:
        cur = open(INDEX, encoding="utf-8").read() if os.path.exists(INDEX) else ""
        if cur != text:
            print("🔴 bios-spec-index-check: docs/bios/index.md DIFFERS from its generator -- run "
                  "`make bios-spec-index`")
            return 1
        print("bios-spec-index-check: docs/bios/index.md matches its generator")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
