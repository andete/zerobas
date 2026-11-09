#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Move one disk.rom routine (a label through the line before the next top-level
label, with the comment block directly above it) to just in front of a pinned
`ds $PIN - $` line. Refuses on a missing / ambiguous anchor. Builds nothing:
run `make build/disk.rom` and scratchpad/pinguard.py after.

    python3 scratchpad/move_routine.py LABEL PIN      e.g. calbak 436C
"""
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


def main():
    label, pin = sys.argv[1], sys.argv[2].upper().lstrip("$")
    files = [os.path.join(REPO, "disk", f) for f in os.listdir(os.path.join(REPO, "disk")) if f.endswith(".asm")]
    src = [f for f in files if any(l.startswith(label + ":") for l in open(f))]
    if len(src) != 1:
        sys.exit(f"label {label}: found in {len(src)} files")
    lines = open(src[0]).read().split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith(label + ":"))
    j = next((k for k in range(i + 1, len(lines)) if LABEL.match(lines[k])), len(lines))
    while j > i + 1 and (lines[j - 1].strip() == "" or lines[j - 1].lstrip().startswith(";")):
        j -= 1                                   # leave the NEXT routine's comment where it is
    c = i
    while c > 0 and lines[c - 1].lstrip().startswith(";") and not lines[c - 1].lstrip().startswith(";;"):
        c -= 1
    block = lines[c:j]
    pinre = re.compile(r"^\s+ds\s+\$%s\s*-\s*\$" % pin, re.I)
    dst = [(f, k) for f in files for k, l in enumerate(open(f).read().split("\n")) if pinre.match(l)]
    if len(dst) != 1:
        sys.exit(f"pin ${pin}: found {len(dst)} `ds` lines")
    del lines[c:j]
    open(src[0], "w").write("\n".join(lines))
    f, k = dst[0]
    dl = open(f).read().split("\n")
    note = f"; (moved here from {os.path.basename(src[0])} by the D-DSKFMT defrag, 2026-11-09)"
    dl[k:k] = [note] + block
    open(f, "w").write("\n".join(dl))
    print(f"moved {label} ({j - c} lines) {os.path.basename(src[0])} -> {os.path.basename(f)} before ${pin}")


if __name__ == "__main__":
    main()
