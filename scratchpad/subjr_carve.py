#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LISTFLT's carve: `jp` -> `jr` in the SUB-ONLY sources of sub page 0.

D-LISTFLT's float renderer needs ~190 B of sub page 0 (137 free, 2026-10-11).
Main's jp->jr passes (D-JRSLICE, D-JRSLICE2) never swept the sub-only files.

SCOPE, deliberately narrow:
  * files assembled into sub page 0 (sub/sub.asm's includes before
    __MEAS_SUB_P0_END, recursively);
  * MINUS every file main (basic/main.asm) or the disk ROM (disk/disk.asm)
    also includes -- a shared file's jr must be in range in every build
    (the standing pdfcb-body.inc lesson), and this tool builds only sub;
  * MINUS sub/sub.asm itself -- its tenant tables are `jp`s whose 3-byte
    stride IS the index (SUBROM_ENTRY_BASE + 3*idx).
Candidates: `jp label` and `jp z|nz|c|nc,label` (no `(hl)`, no p/m/pe/po).

METHOD: convert every candidate, assemble sub.rom into a temp file, and
revert each line pasmo names as "Relative jump out of range" -- one per
build -- until it assembles. jp->jr is semantically identical in range (the
same destination, the same condition, flags untouched); the assembler
enforces the range. Prints the page-0 free space before and after.

  python3 scratchpad/subjr_carve.py          # dry run: report only, restore
  python3 scratchpad/subjr_carve.py --write  # keep the conversions
  ... --page 1                             # sub page 1 instead (2026-10-12)
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                    # noqa: E402

INC = re.compile(r'^\s+include\s+"([^"]+)"', re.I)
CAND = re.compile(r"^(\s+)jp(\s+)((?:(?:z|nz|c|nc)\s*,\s*)?[A-Za-z_][\w]*)(\s*(?:;.*)?)$",
                  re.I)
ERR = re.compile(r"Relative jump out of range\s+on line (\d+) of file (\S+)")


def resolve(name, dirs):
    for d in dirs:
        p = os.path.normpath(os.path.join(d, name))
        if os.path.exists(p):
            return p
    raise SystemExit(f"REFUSED: include {name} not found in {dirs}")


def includes(path, dirs, stop=None, seen=None, start=None):
    seen = set() if seen is None else seen
    on = start is None
    for line in open(path, encoding="utf-8", errors="replace"):
        if not on:
            on = line.startswith(start)
            continue
        if stop and line.startswith(stop):
            break
        m = INC.match(line)
        if m:
            p = resolve(m.group(1), dirs)
            if p not in seen:
                seen.add(p)
                includes(p, dirs, None, seen)
    return seen


PAGE = 1 if "--page" in sys.argv and sys.argv[sys.argv.index("--page") + 1] == "1" else 0
END_LABEL = "__MEAS_SUB_P1_END" if PAGE else "__MEAS_SUB_P0_END"
PAGE_TOP = 0x8000 if PAGE else 0x4000


UNCOND = re.compile(r"^\s+jp\s+[A-Za-z_]\w*\s*(;.*)?$", re.I)
CODELINE = re.compile(r"^\s*[^\s;]")


def _neighbour(lines, i, step):
    """The next code line from i in direction step; a LABEL line counts (it
    breaks a table), comments and blanks do not."""
    j = i + step
    while 0 <= j < len(lines):
        if CODELINE.match(lines[j]) and not lines[j].lstrip().startswith(";"):
            return lines[j]
        j += step
    return ""


def is_table_row(lines, i):
    """🔴 A JUMP-TABLE ROW IS NOT A BRANCH. sub/fatprim.asm's fp_table is
    indexed in 3-byte strides; the first page-1 pass converted twelve of its
    rows to 2-byte `jr` and every disk op after the first dispatched to the
    wrong row (kwtime LOF hung, kwsweep's disk rows mangled -- 2026-10-12).
    A row is an unconditional `jp label` whose neighbouring code line (no
    label between) is another unconditional `jp label`."""
    if not UNCOND.match(lines[i]):
        return False
    return bool(UNCOND.match(_neighbour(lines, i, -1)) or UNCOND.match(_neighbour(lines, i, +1)))


def free_p0(sym):
    """Free bytes of the page being carved (named for its first use, page 0)."""
    for line in open(sym):
        m = re.match(END_LABEL + r"\s+EQU\s+0([0-9A-F]+)H", line)
        if m:
            return PAGE_TOP - int(m.group(1), 16)
    return None


def build():
    rom, sym = probe_tmp.tmp("subjr.rom"), probe_tmp.tmp("subjr.sym")
    for p in (rom, sym):
        if os.path.exists(p):
            os.unlink(p)
    r = subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", rom, sym],
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    m = ERR.search(out)
    if m:
        return ("range", int(m.group(1)), resolve(m.group(2), ["sub", "."]))
    if r.returncode or not os.path.exists(rom) or os.path.getsize(rom) == 0:
        return ("fail", out[-600:], None)
    return ("ok", free_p0(sym), None)


def main():
    write = "--write" in sys.argv
    # --page 1 (2026-10-12, for C5-LOW's sub page-1 cost): the files between the
    # two measurement labels instead of before the first.
    p0 = (includes("sub/sub.asm", ["sub", "."], stop="__MEAS_SUB_P1_END",
                   start="__MEAS_SUB_P0_END") if PAGE
          else includes("sub/sub.asm", ["sub", "."], stop="__MEAS_SUB_P0_END"))
    shared = includes("basic/main.asm", ["basic", "."]) | \
        includes("disk/disk.asm", ["disk", "."])
    files = sorted(p for p in p0 if p not in shared and p != "sub/sub.asm"
                   and os.path.normpath("sub/sub.asm") != p)
    st, base, _ = build()
    if st != "ok":
        raise SystemExit(f"REFUSED: the baseline does not build: {st} {base}")
    print(f"baseline sub page {PAGE} free: {base} B; {len(files)} sub-only page-{PAGE} files")
    orig = {f: open(f, encoding="utf-8").read().split("\n") for f in files}
    conv = {}
    tables = 0
    for f, lines in orig.items():
        new = list(lines)
        for i, l in enumerate(lines):
            m = CAND.match(l)
            if m and is_table_row(lines, i):
                tables += 1
                continue
            if m:
                new[i] = f"{m.group(1)}jr{m.group(2)}{m.group(3)}{m.group(4)}"
                conv[(f, i + 1)] = l
        open(f, "w", encoding="utf-8").write("\n".join(new))
    print(f"converted {len(conv)} candidate(s); {tables} jump-table row(s) left alone")
    reverted = 0
    try:
        while True:
            st, a, b = build()
            if st == "ok":
                break
            if st == "fail":
                raise SystemExit(f"BUILD FAILED for another reason:\n{a}")
            key = (b, a)
            if key not in conv:
                raise SystemExit(f"REFUSED: out of range at {b}:{a}, not a converted line")
            lines = open(b, encoding="utf-8").read().split("\n")
            lines[a - 1] = conv.pop(key)
            open(b, "w", encoding="utf-8").write("\n".join(lines))
            reverted += 1
        print(f"kept {len(conv)}, reverted {reverted} out of range; "
              f"sub page {PAGE} free {base} -> {a} B (+{a - base})")
        for (f, n), l in sorted(conv.items()):
            print(f"  {f}:{n}  {l.strip()}")
    finally:
        if not write:
            for f, lines in orig.items():
                open(f, "w", encoding="utf-8").write("\n".join(lines))
            print("dry run: sources restored")


if __name__ == "__main__":
    main()
