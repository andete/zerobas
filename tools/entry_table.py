#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ENTRYTIERS: one row per ENTRY POINT in the tier sheet, BDOS functions first.

Joost, 2026-11-08: *"having the bios and such stable and on par is of higher
priority then having basic stable"* (scratchpad/LOOP-RESTART.md, RULINGS
2026-11-08). The keyword rows count BASIC; nothing counted the surface a machine-
code program calls. This counts the MSX-DOS 1 BDOS ($00-$30) first; the disk-ROM
entries and the main BIOS calls are the next two tables (D-ENTRYTIERS, TODO.md).

HOW A ROW IS FILLED -- MECHANICALLY, AND WHAT THAT DOES NOT PROVE:
  * every probe source under probes/ that calls the BDOS (`call BDOS` / `$0005` /
    `$F37D`) is scanned; the last `ld c, N` before each call names the function
    (a number, the file's own `equ`, or the published function name);
  * a *-acceptance target REACHES that source when its recipe names the source,
    or names a script that -- in CODE, not a docstring or comment -- names it,
    followed to a fixed point (bdos-acceptance -> disk_bdos_acceptance.py ->
    build_bdosx_disk.py -> bdosx.asm is two hops);
  * the row says EXERCISED BY those gates. That is NOT "same as the reference":
    a call is counted whether or not its result is compared. A row nothing
    reaches says NOT MEASURED out loud (kwsweep's MISSING lesson: an absent row
    must read as absent, never as fine);
  * the open TODO item naming the function (its published name in the item's
    headline) gives the row its tier.

    python3 tools/entry_table.py            the BDOS table, plain text
    python3 tools/entry_table.py --markdown the section docs/tier-status.md carries
"""
import collections
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CALL = re.compile(r"^\s*call\s+(BDOS|\$0005|\$F37D|0005h|5)\b", re.I)
LDC = re.compile(r"^\s*ld\s+c\s*,\s*([$A-Za-z0-9_]+)\s*$", re.I)
EQU = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:?\s+equ\s+([$0-9A-Fa-fh]+)\s*$", re.I)

# MSX-DOS 1 function names, $00-$30 (the published function list); None = a number
# MSX-DOS 1 does not use.
DOS1 = ["TERM0", "CONIN", "CONOUT", "AUXIN", "AUXOUT", "LSTOUT", "DIRIO", "DIRIN",
        "INNOE", "STROUT", "BUFIN", "CONST", "CPMVER", "DSKRST", "SELDSK", "FOPEN",
        "FCLOSE", "SFIRST", "SNEXT", "FDEL", "RDSEQ", "WRSEQ", "FMAKE", "FREN", "LOGIN",
        "CURDRV", "SETDTA", "ALLOC", None, None, None, None, None, "RDRND", "WRRND",
        "FSIZE", "SETRND", None, "WRBLK", "RDBLK", "WRZER", None, "GDATE", "SDATE",
        "GTIME", "STIME", "VERIFY", "RDABS", "WRABS"]
NAMES = {n: i for i, n in enumerate(DOS1) if n}


def _num(tok):
    t = tok.lower()
    if t.startswith("$"):
        return int(t[1:], 16)
    if t.endswith("h"):
        return int(t[:-1], 16)
    return int(t)


def scan_asm(path):
    """-> Counter{function number: calls} for one probe source."""
    lines = open(path, errors="replace").read().splitlines()
    equ = {}
    for line in lines:
        m = EQU.match(line.split(";", 1)[0])
        if m:
            try:
                equ[m.group(1).upper()] = _num(m.group(2))
            except ValueError:
                pass
    funcs, last = collections.Counter(), None
    for line in lines:
        code = line.split(";", 1)[0]
        m = LDC.match(code)
        if m:
            tok = m.group(1)
            try:
                last = _num(tok)
            except ValueError:
                last = equ.get(tok.upper(), NAMES.get(tok.upper()))
            continue
        if CALL.match(code) and last is not None:
            funcs[last] += 1
    return funcs


def _targets():
    """*-acceptance target -> its recipe text."""
    out, cur = {}, None
    for line in open(os.path.join(REPO, "Makefile"), errors="replace"):
        m = re.match(r"^([A-Za-z0-9_.-]+-acceptance)\s*:", line)
        if m:
            cur = m.group(1)
            out[cur] = ""
            continue
        if cur and line.startswith("\t"):
            out[cur] += line
        elif cur and line.strip() and not line.startswith("#"):
            cur = None
    return out


def _scripts():
    """probe script name -> its CODE (docstrings and comments stripped: a script
    that only MENTIONS another in prose does not run it)."""
    out = {}
    for root, _, files in os.walk(os.path.join(REPO, "probes")):
        for f in files:
            if f.endswith(".py"):
                txt = open(os.path.join(root, f), errors="replace").read()
                txt = re.sub(r'(?s)("""|\'\'\').*?\1', "", txt)
                out[f] = "\n".join(l.split("#", 1)[0] for l in txt.splitlines())
    return out


def bdos_map():
    """-> ({function: {(probe stem, gate)}}, [probe sources no gate reaches])."""
    targets, pys = _targets(), _scripts()
    table, unreached = collections.defaultdict(set), []
    for root, _, files in sorted(os.walk(os.path.join(REPO, "probes"))):
        for f in sorted(files):
            if not f.endswith(".asm"):
                continue
            fn = scan_asm(os.path.join(root, f))
            if not fn:
                continue
            stem = f[:-4]
            users = {p for p, txt in pys.items() if f in txt or f'"{stem}"' in txt}
            while True:
                more = {p for p, txt in pys.items()
                        if p not in users and any(u in txt for u in users)}
                if not more:
                    break
                users |= more
            hit = {t for t, r in targets.items() if f in r or any(u in r for u in users)}
            if not hit:
                unreached.append(f)
            for n in fn:
                for t in (hit or {None}):
                    table[n].add((stem, t))
    return table, unreached


def open_items_by_name(its):
    """function number -> [(tier, item id)] for open items whose HEADLINE names it."""
    out = collections.defaultdict(list)
    for it in its:
        head = it.get("head", "")
        for n, name in enumerate(DOS1):
            if name and re.search(r"\b%s\b" % name, head):
                out[n].append((it.get("tier", "?"), it.get("id") or f"line {it['line']}"))
    return out


def rows(its=()):
    table, unreached = bdos_map()
    named = open_items_by_name(its)
    res = []
    for n in range(0x31):
        got = table.get(n, set())
        gates = sorted({t for _, t in got if t})
        probes = sorted({s for s, _ in got})
        ungated = sorted({s for s, t in got if t is None})
        if DOS1[n] is None:
            status = "unused in MSX-DOS 1"
        elif gates:
            status = "exercised"
        else:
            status = "NOT MEASURED"
        res.append(dict(num=n, name=DOS1[n] or "—", status=status, gates=gates,
                        probes=probes, ungated=ungated, items=named.get(n, [])))
    return res, unreached


def fmt_markdown(its=()):
    rs, unreached = rows(its)
    real = [r for r in rs if r["name"] != "—"]
    nm = [r for r in real if r["status"] == "NOT MEASURED"]
    out = ["## Entry points first — the BDOS functions", "",
           "🎚️ **RULED (Joost, 2026-11-08): the entry points outrank BASIC** -- *\"having "
           "the bios and such stable and on par is of higher priority then having basic "
           "stable\"*. These rows count the surface a machine-code program calls; the "
           "keyword rows below count BASIC. Disk-ROM entries and the main BIOS calls are "
           "the next two tables (D-ENTRYTIERS).", "",
           "⚠️ **EXERCISED IS NOT SAME.** A row is filled mechanically "
           "(`tools/entry_table.py`): a gate that runs a probe calling the function. "
           "Whether that gate compares the function's RESULT with the reference is not "
           "read here. **NOT MEASURED** means no gate calls it at all.", "",
           f"**{len(real) - len(nm)} of {len(real)}** MSX-DOS 1 functions are exercised by "
           f"a gate; **{len(nm)} are NOT MEASURED**: "
           + ", ".join(f"`{r['name']}`" for r in nm) + ".", "",
           "| fn | name | status | exercised by | open item (tier) |",
           "|---|---|---|---|---|"]
    for r in rs:
        by = ", ".join(f"`{g}`" for g in r["gates"]) or "—"
        if r["ungated"]:
            by += " (also probes no gate runs: " + ", ".join(r["ungated"]) + ")"
        it = ", ".join(f"{t} {i}" for t, i in r["items"]) or "—"
        out.append(f"| ${r['num']:02X} | {r['name']} | {r['status']} | {by} | {it} |")
    if unreached:
        out += ["", "Probe sources that call the BDOS but no `*-acceptance` target runs: "
                + ", ".join(f"`{u}`" for u in unreached) + "."]
    return "\n".join(out) + "\n"


def main(argv):
    if "--markdown" in argv:
        sys.stdout.write(fmt_markdown())
        return 0
    rs, unreached = rows()
    for r in rs:
        print(f"${r['num']:02X} {r['name']:7} {r['status']:20} {', '.join(r['gates'])}")
    if unreached:
        print("\nno gate runs:", ", ".join(unreached))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
