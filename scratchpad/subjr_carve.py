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


def includes(path, dirs, stop=None, seen=None):
    seen = set() if seen is None else seen
    for line in open(path, encoding="utf-8", errors="replace"):
        if stop and line.startswith(stop):
            break
        m = INC.match(line)
        if m:
            p = resolve(m.group(1), dirs)
            if p not in seen:
                seen.add(p)
                includes(p, dirs, None, seen)
    return seen


def free_p0(sym):
    for line in open(sym):
        m = re.match(r"__MEAS_SUB_P0_END\s+EQU\s+0([0-9A-F]+)H", line)
        if m:
            return 0x4000 - int(m.group(1), 16)
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
    p0 = includes("sub/sub.asm", ["sub", "."], stop="__MEAS_SUB_P0_END")
    shared = includes("basic/main.asm", ["basic", "."]) | \
        includes("disk/disk.asm", ["disk", "."])
    files = sorted(p for p in p0 if p not in shared and p != "sub/sub.asm"
                   and os.path.normpath("sub/sub.asm") != p)
    st, base, _ = build()
    if st != "ok":
        raise SystemExit(f"REFUSED: the baseline does not build: {st} {base}")
    print(f"baseline sub page 0 free: {base} B; {len(files)} sub-only page-0 files")
    orig = {f: open(f, encoding="utf-8").read().split("\n") for f in files}
    conv = {}
    for f, lines in orig.items():
        new = list(lines)
        for i, l in enumerate(lines):
            m = CAND.match(l)
            if m:
                new[i] = f"{m.group(1)}jr{m.group(2)}{m.group(3)}{m.group(4)}"
                conv[(f, i + 1)] = l
        open(f, "w", encoding="utf-8").write("\n".join(new))
    print(f"converted {len(conv)} candidate(s)")
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
              f"sub page 0 free {base} -> {a} B (+{a - base})")
        for (f, n), l in sorted(conv.items()):
            print(f"  {f}:{n}  {l.strip()}")
    finally:
        if not write:
            for f, lines in orig.items():
                open(f, "w", encoding="utf-8").write("\n".join(lines))
            print("dry run: sources restored")


if __name__ == "__main__":
    main()
