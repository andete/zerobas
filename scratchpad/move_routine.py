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
    # 🔴 a pin's `ds $XXXX - $` line ENDS a block too (2026-11-10: seq_k30 and, before
    # it, fpl_split each dragged their pin's pad -- and seq_k30 the pinned veneer)
    PADRE = re.compile(r"^\s+ds\s+\$[0-9A-Fa-f]{4}\s*-\s*\$", re.I)
    j = next((k for k in range(i + 1, len(lines)) if LABEL.match(lines[k]) or PADRE.match(lines[k])), len(lines))
    while j > i + 1 and (lines[j - 1].strip() == "" or lines[j - 1].lstrip().startswith(";")):
        j -= 1                                   # leave the NEXT routine's comment where it is
    c = i
    while c > 0 and lines[c - 1].lstrip().startswith(";") and not lines[c - 1].lstrip().startswith(";;"):
        c -= 1
    block = lines[c:j]
    # 🔴 refuse a block whose jr / djnz leaves it: out of reach after the move
    # (hk_auto / hk_kill, 2026-11-10: each ended in a `jr` to its own continuation).
    own = {m.group(1) for l in block for m in [LABEL.match(l)] if m}
    for l in block:
        code = l.split(";", 1)[0]
        m = re.match(r"\s+(jr|djnz)\s+(?:(?:nz|z|nc|c)\s*,\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*$", code, re.I)
        if m and m.group(2) not in own:
            sys.exit(f"{label}: `{code.strip()}` leaves the block -- not movable")
    pinre = re.compile(r"^\s+ds\s+\$%s\s*-\s*\$" % pin, re.I)
    dst = [(f, k) for f in files for k, l in enumerate(open(f).read().split("\n")) if pinre.match(l)]
    if len(dst) != 1:
        sys.exit(f"pin ${pin}: found {len(dst)} `ds` lines")
    del lines[c:j]
    open(src[0], "w").write("\n".join(lines))
    # 🔴 re-find the pin AFTER the delete: in the same file, a source block above it
    # shifted it up (mulacc_cmp, 2026-11-10, landed inside frl_div).
    f = dst[0][0]
    dl = open(f).read().split("\n")
    k = next(i for i, l in enumerate(dl) if pinre.match(l))
    note = f"; (moved here from {os.path.basename(src[0])} by the D-DSKFMT defrag)"
    dl[k:k] = [note] + block
    open(f, "w").write("\n".join(dl))
    print(f"moved {label} ({j - c} lines) {os.path.basename(src[0])} -> {os.path.basename(f)} before ${pin}")


if __name__ == "__main__":
    main()
