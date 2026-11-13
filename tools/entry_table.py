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
import glob
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


# ---------------------------------------------------------------------------
# D-ENTRYTIERS step 4: the DISK-ROM entries.
#   * the six published ones ($4010 DSKIO .. $401F MTOFF, disk/init.asm's table);
#   * every PINNED address in disk/*.asm (a `ds $XXXX - $` pin and the label or
#     instruction after it): the reference's canonical entries the MSX-DOS kernel
#     calls. Their BDOS function is read from a `BDOS $NN` mention around the pin;
#     their status is that function's row. A pin naming no function says so.
# ---------------------------------------------------------------------------
PUBLISHED = [(0x4010, "DSKIO"), (0x4013, "DSKCHG"), (0x4016, "GETDPB"),
             (0x4019, "CHOICE"), (0x401C, "DSKFMT"), (0x401F, "MTOFF")]
PIN = re.compile(r"^\s+ds\s+\$([0-9A-Fa-f]{4})\s*-\s*\$")
LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
BDOSN = re.compile(r"BDOS\s+\$([0-9A-Fa-f]{2})")


def _gate_reach():
    """script / source basename -> the *-acceptance targets that reach it (code only)."""
    targets, pys = _targets(), _scripts()
    out = collections.defaultdict(set)
    for t, recipe in targets.items():
        seen = {p for p in pys if p in recipe}
        frontier = set(seen)
        while frontier:
            nxt = set()
            for p in frontier:
                for q, _ in pys.items():
                    if q not in seen and q in pys[p]:
                        nxt.add(q)
            seen |= nxt
            frontier = nxt
        for p in seen:
            out[p].add(t)
    return out, pys


def _probe_asms():
    """probe .asm basename -> its CODE (comments stripped): a probe a gate script
    builds witnesses an entry it calls (bios_rows' rule, shared since D-ENTRYTIERS
    step 3 -- dskent.asm's `ld ix, $4016` was invisible to the disk table)."""
    asms = {}
    for root, _, files in os.walk(os.path.join(REPO, "probes")):
        for f in files:
            if f.endswith(".asm"):
                asms[f] = "\n".join(l.split(";", 1)[0]
                                    for l in open(os.path.join(root, f), errors="replace"))
    return asms


def _witnesses(pat, reach, pys, asms):
    gates = set()
    for p, txt in pys.items():
        if pat.search(txt):
            gates |= reach.get(p, set())
    for a, txt in asms.items():
        if pat.search(txt):
            for p, ptxt in pys.items():
                if a in ptxt:
                    gates |= reach.get(p, set())
    return gates


def published_rows():
    reach, pys = _gate_reach()
    asms = _probe_asms()
    rows = []
    for addr, name in PUBLISHED:
        pat = re.compile(r"(\$%04X|0x%04x|%04Xh)\b|\b%s\b" % (addr, addr, addr, name), re.I)
        gates = _witnesses(pat, reach, pys, asms)
        rows.append(dict(addr=addr, name=name, gates=sorted(gates),
                         status="exercised" if gates else "NOT MEASURED"))
    return rows


def pinned_rows(bdos=None):
    bdos = bdos or {r["num"]: r for r in rows()[0]}
    out = []
    for f in sorted(glob.glob(os.path.join(REPO, "disk", "*.asm"))):
        lines = open(f, errors="replace").read().splitlines()
        prev_entry = -1                     # the line of the previous pin's entry
        for i, l in enumerate(lines):
            m = PIN.match(l)
            if not m:
                continue
            addr = int(m.group(1), 16)
            if not 0x4000 <= addr < 0x8000 or 0x4010 <= addr <= 0x401F:
                continue
            j, name = i + 1, None
            while j < len(lines) and j < i + 80:
                c = lines[j].split(";", 1)[0].strip()
                lm = LABEL.match(lines[j])
                if lm:
                    name = lm.group(1)
                    break
                if c:
                    name = "(" + c.split()[0] + " " + " ".join(c.split()[1:])[:24] + ")"
                    break
                j += 1
            # the comment that names this pin's function lies between the PREVIOUS
            # pin's entry and this entry's own line -- never across a pin (a wider
            # window credited fdc_write_phys with the FREN veneer in front of it)
            # (a label alone on its line: its instruction -- and the comment naming
            # the function -- is the next line, so the window takes it too)
            j = min(j, len(lines) - 1)
            end = j + 2 if LABEL.match(lines[j]) and not lines[j].split(":", 1)[1].split(";")[0].strip() else j + 1
            ctx = "\n".join(lines[max(prev_entry + 1, i - 12):end])
            prev_entry = end - 1
            fn = BDOSN.search(ctx)
            fn = int(fn.group(1), 16) if fn else None
            how = ""
            if fn is None:
                # a comment may name the function instead of numbering it (SFIRST,
                # _GDATE, GETALLOC -- the kernel's own words for ALLOC); weaker
                # evidence, so the row says how it was tied
                alias = dict(NAMES, GETALLOC=0x1B, GETDAT=0x2A, SETDAT=0x2B, GDATE=0x2A, SDATE=0x2B)
                # the entry's OWN label (getalloc -> GETALLOC, setdta_cache -> SETDTA)
                first = (name or "").strip("(`").split()[0].split("_")[0].upper() if name else ""
                if first in alias:
                    fn, how = alias[first], " (by its label)"
                # (a name merely MENTIONED in the comment window was tried and dropped:
                # it tied fdc_di_save to WRZER and a pad to WRBLK -- comments name the
                # routines that moved past a pin as readily as the pin's own function)
            if fn is not None and fn in bdos:
                st = f"BDOS ${fn:02X} {bdos[fn]['name']}{how}: {bdos[fn]['status']}"
            else:
                st = "no BDOS function named"
            out.append(dict(addr=addr, name=name or "?", fn=fn, status=st,
                            where=f"{os.path.relpath(f, REPO)}:{i + 1}"))
    return sorted(out, key=lambda r: r["addr"])


def fmt_disk_markdown():
    pub, pins = published_rows(), pinned_rows()
    out = ["## Entry points — the disk ROM", "",
           "The six published entries, then every PINNED address in `disk/*.asm` -- the "
           "reference's canonical entries the MSX-DOS kernel calls (each one a `ds $XXXX - $` "
           "pin; D-WRZER and D-AUXOUT were two such addresses never planted). A pin's status is "
           "the BDOS function its comment names; a pin naming none is a kernel-internal entry "
           "this table cannot tie to a function yet. Same rule as above: exercised is not same.", "",
           "| address | entry | status | exercised by |", "|---|---|---|---|"]
    for r in pub:
        out.append(f"| ${r['addr']:04X} | {r['name']} | {r['status']} | "
                   + (", ".join(f"`{g}`" for g in r["gates"]) or "—") + " |")
    out += ["", "| pin | label | function and its status | source |", "|---|---|---|---|"]
    for r in pins:
        out.append(f"| ${r['addr']:04X} | `{r['name']}` | {r['status']} | {r['where']} |")
    named = sum(1 for r in pins if r["fn"] is not None)
    out += ["", f"{len(pins)} pinned addresses; {named} name a BDOS function, "
            f"{len(pins) - named} do not."]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# D-ENTRYTIERS step 5: the MAIN BIOS calls -- the published MSX1 BIOS jump table
# (MSX2 Technical Handbook ch. 2; names as published). C-BIOS's, patched by
# cbios-repack where a row differs. Exercised = a gate-reached script names the
# entry or its address in CODE; the same "exercised is not same" rule.
# ---------------------------------------------------------------------------
BIOS = [(0x0000, "CHKRAM"), (0x0008, "SYNCHR"), (0x000C, "RDSLT"), (0x0010, "CHRGTR"),
        (0x0014, "WRSLT"), (0x0018, "OUTDO"), (0x001C, "CALSLT"), (0x0020, "DCOMPR"),
        (0x0024, "ENASLT"), (0x0028, "GETYPR"), (0x0030, "CALLF"), (0x0038, "KEYINT"),
        (0x003B, "INITIO"), (0x003E, "INIFNK"), (0x0041, "DISSCR"), (0x0044, "ENASCR"),
        (0x0047, "WRTVDP"), (0x004A, "RDVRM"), (0x004D, "WRTVRM"), (0x0050, "SETRD"),
        (0x0053, "SETWRT"), (0x0056, "FILVRM"), (0x0059, "LDIRMV"), (0x005C, "LDIRVM"),
        (0x005F, "CHGMOD"), (0x0062, "CHGCLR"), (0x0066, "NMI"), (0x0069, "CLRSPR"),
        (0x006C, "INITXT"), (0x006F, "INIT32"), (0x0072, "INIGRP"), (0x0075, "INIMLT"),
        (0x0078, "SETTXT"), (0x007B, "SETT32"), (0x007E, "SETGRP"), (0x0081, "SETMLT"),
        (0x0084, "CALPAT"), (0x0087, "CALATR"), (0x008A, "GSPSIZ"), (0x008D, "GRPPRT"),
        (0x0090, "GICINI"), (0x0093, "WRTPSG"), (0x0096, "RDPSG"), (0x0099, "STRTMS"),
        (0x009C, "CHSNS"), (0x009F, "CHGET"), (0x00A2, "CHPUT"), (0x00A5, "LPTOUT"),
        (0x00A8, "LPTSTT"), (0x00AB, "CNVCHR"), (0x00AE, "PINLIN"), (0x00B1, "INLIN"),
        (0x00B4, "QINLIN"), (0x00B7, "BREAKX"), (0x00BA, "ISCNTC"), (0x00BD, "CKCNTC"),
        (0x00C0, "BEEP"), (0x00C3, "CLS"), (0x00C6, "POSIT"), (0x00C9, "FNKSB"),
        (0x00CC, "ERAFNK"), (0x00CF, "DSPFNK"), (0x00D2, "TOTEXT"), (0x00D5, "GTSTCK"),
        (0x00D8, "GTTRIG"), (0x00DB, "GTPAD"), (0x00DE, "GTPDL"), (0x00E1, "TAPION"),
        (0x00E4, "TAPIN"), (0x00E7, "TAPIOF"), (0x00EA, "TAPOON"), (0x00ED, "TAPOUT"),
        (0x00F0, "TAPOOF"), (0x00F3, "STMOTR"), (0x00F6, "LFTQ"), (0x00F9, "PUTQ"),
        (0x00FC, "RIGHTC"), (0x00FF, "LEFTC"), (0x0102, "UPC"), (0x0105, "TUPC"),
        (0x0108, "DOWNC"), (0x010B, "TDOWNC"), (0x010E, "SCALXY"), (0x0111, "MAPXYC"),
        (0x0114, "FETCHC"), (0x0117, "STOREC"), (0x011A, "SETATR"), (0x011D, "READC"),
        (0x0120, "SETC"), (0x0123, "NSETCX"), (0x0126, "GTASPC"), (0x0129, "PNTINI"),
        (0x012C, "SCANR"), (0x012F, "SCANL"), (0x0132, "CHGCAP"), (0x0135, "CHGSND"),
        (0x0138, "RSLREG"), (0x013B, "WSLREG"), (0x013E, "RDVDP"), (0x0141, "SNSMAT"),
        (0x0144, "PHYDIO"), (0x0147, "FORMAT"), (0x014A, "ISFLIO"), (0x014D, "OUTDLP"),
        (0x0150, "GETVCP"), (0x0153, "GETVC2"), (0x0156, "KILBUF"), (0x0159, "CALBAS")]


# Joost's per-entry rulings (2026-11-13) for rows no gate calls DIRECTLY, and why that is
# not a gap. A ruled row with a direct witness still reads "exercised"; a STUB outranks both.
BIOS_RULED = {
    0x0038: "covered INDIRECTLY (Joost 2026-11-13: every interrupt-driven row -- keys, "
            "ON INTERVAL, PLAY, TIME -- runs through it)",
    0x0066: "out of scope (Joost 2026-11-13: NMI is not used on MSX)",
}


def bios_rows(stubs=None):
    # D-BIOSRUNG (2026-11-12): a STUB outranks "exercised" -- C-BIOS's stub body still in
    # our built main ROM (tools/stub_scan.py) is a TIER 1 failure whatever row names it;
    # three such rows had read "exercised" (a stub that does nothing agrees in the idle
    # state). The scan REFUSES on a degenerate ROM, and that refusal is not caught here:
    # tiers-md then leaves the page unchanged rather than printing "0 stubs".
    # `stubs`: a caller that needs only the table's SHAPE passes {} (tests/test_entry_table.py
    # -- CI runs it before the merged main ROM exists, and the scan's refusal kept CI red
    # on all three OSes for eleven pushes, 2026-11-12); None scans the built ROM.
    if stubs is None:
        import stub_scan
        stubs = stub_scan.stubs()
    st = stubs
    reach, pys = _gate_reach()
    asms = _probe_asms()
    out = []
    for addr, name in BIOS:
        pat = re.compile(r"(\$%04X|0x%04x|%04Xh)\b|\b%s\b" % (addr, addr, addr, name), re.I)
        gates = _witnesses(pat, reach, pys, asms)
        if addr in st:
            status = f"🔴 STUB ({st[addr]['kind']})"
        elif gates:
            status = "exercised"
        else:
            status = BIOS_RULED.get(addr, "NOT MEASURED")
        out.append(dict(addr=addr, name=name, gates=sorted(gates), status=status,
                        stub=addr in st))
    return out


def fmt_bios_markdown():
    rs = bios_rows()
    nm = [r for r in rs if r["status"] == "NOT MEASURED"]
    ruled = [r for r in rs if not r["stub"] and not r["gates"] and r["addr"] in BIOS_RULED]
    stubs = [r for r in rs if r["stub"]]
    blind = [r for r in stubs if r["gates"]]
    out = ["## Entry points — the main BIOS calls", "",
           "The published MSX1 BIOS jump table (C-BIOS's on both targets, patched by "
           "cbios-repack where a row differs). Exercised = a gate whose script (or a probe "
           "source it runs) names the entry or its address in code. Every BASIC program "
           "calls dozens of these INDIRECTLY; a row here counts only a DIRECT witness. "
           "Exercised is not same.", "",
           f"**{len(rs) - len(nm) - len(ruled) - len(stubs)} of {len(rs)}** have a direct witness "
           f"and are not stubs; **{len(ruled)} are RULED** not to need one ("
           + ", ".join(r["name"] for r in ruled) + f"); **{len(nm)} are NOT MEASURED**; "
           f"**{len(stubs)} are STUBS** -- C-BIOS's stub "
           "body still in our built main ROM (`tools/stub_scan.py`: `push hl / push af / ld hl,"
           "name / call print_debug`, or a bare `ret`), a TIER 1 failure whatever names it "
           f"(D-BIOSRUNG). {len(blind)} of the stubs ARE named by a gate, whose row therefore "
           "cannot tell the stub from the entry: "
           + (", ".join(r["name"] for r in blind) or "none") + ".", "",
           "| address | call | status | exercised by |", "|---|---|---|---|"]
    for r in rs:
        by = ", ".join(f"`{g}`" for g in r["gates"][:6]) + (" …" if len(r["gates"]) > 6 else "")
        out.append(f"| ${r['addr']:04X} | {r['name']} | {r['status']} | {by or '—'} |")
    return "\n".join(out) + "\n"


def main(argv):
    if "--markdown" in argv:
        sys.stdout.write(fmt_markdown())
        return 0
    if "--disk" in argv:
        sys.stdout.write(fmt_disk_markdown())
        return 0
    if "--bios" in argv:
        sys.stdout.write(fmt_bios_markdown())
        return 0
    rs, unreached = rows()
    for r in rs:
        print(f"${r['num']:02X} {r['name']:7} {r['status']:20} {', '.join(r['gates'])}")
    if unreached:
        print("\nno gate runs:", ", ".join(unreached))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
