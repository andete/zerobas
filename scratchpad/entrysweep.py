#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ENTRYTIERS step 3: where does MSX-DOS's kernel FIRST enter our disk ROM for each
BDOS function -- a planted entry, or the middle of a routine?

D-WRZER ($47D1), D-AUXOUT ($5474) and D-AUXIN ($546E) were canonical entries never
planted, each found only because a probe happened to call that function. This runs
every BDOS exerciser disk (bdosx .. bdosx9, bufinx, auxinx) on OURS with
`disk_probe_diff.py callwatch --no-gate --per-call` -- our own ROM's PCs only, the
permitted side -- and maps each call's FIRST page-1 PC to build/disk.sym. A PC that
is exactly a label is a planted entry; label+N is suspect and printed with 🔴.

    python3 -u scratchpad/entrysweep.py
"""
import bisect, collections, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
TMP = "/tmp/zerobas"
NAMES = ["bdosx", "bdosx0", "bdosx2", "bdosx3", "bdosx4", "bdosx5", "bdosx6", "bdosx7",
         "bdosx8", "bdosx9", "bufinx", "auxinx"]

syms = []
for line in open(os.path.join(REPO, "build", "disk.sym")):
    p = line.split()
    if len(p) >= 2:
        try:
            syms.append((int(p[-1].rstrip("H").lstrip("$"), 16), p[0].rstrip(":")))
        except ValueError:
            pass
syms = sorted(x for x in syms if 0x4000 <= x[0] < 0x8000 and not x[1].startswith("__"))
addrs = [a for a, _ in syms]
# every pinned address is a planted entry even when no label names it ($4462's
# `jp fopen_fill_body` has none; the first sweep called it "wx_out+9")
sys.path.insert(0, os.path.join(REPO, "tools"))
import entry_table  # noqa: E402
PINS = {r["addr"] for r in entry_table.pinned_rows()} | {a for a, _ in entry_table.PUBLISHED}


def where(pc):
    i = bisect.bisect_right(addrs, pc) - 1
    a, n = syms[i]
    return n, pc - a


first = collections.defaultdict(set)          # fn -> {(pc, name, off)}
for nm in NAMES:
    script = os.path.join(REPO, "probes", "disk", f"build_{nm}_disk.py")
    dsk = os.path.join(TMP, f"sweep_{nm}.dsk")
    out = subprocess.run(["python3", script, "--dos-disk", DOS, "--out", dsk, "--tmp-dir", TMP],
                         capture_output=True, text=True).stdout
    keys = re.search(r"--keys2 '([^']*)' --keys2-at (\d+)", out)
    arm = re.search(r"--arm-check-val (0x[0-9a-fA-F]+)", out)
    cmd = ["python3", "-u", os.path.join(REPO, "probes", "disk", "disk_probe_diff.py"),
           "callwatch", "--no-gate", "--per-call", "--machine", "ours", "--settle", "60",
           "--maxhits", "4000", "--diska", dsk]
    if arm:
        cmd += ["--arm-check-val", arm.group(1)]
    if keys:
        cmd += ["--keys2", keys.group(1).encode().decode("unicode_escape"), "--keys2-at", keys.group(2)]
    res = subprocess.run(cmd, capture_output=True, text=True).stdout
    n = 0
    for m in re.finditer(r"FIRST call=\d+ fn=\$([0-9A-F]{2}) PC=([0-9A-F]{4})", res):
        fn, pc = int(m.group(1), 16), int(m.group(2), 16)
        name, off = where(pc)
        first[fn].add((pc, name, off))
        n += 1
    print(f"{nm:8} {n} calls", flush=True)

print()
for fn in sorted(first):
    for pc, name, off in sorted(first[fn]):
        planted = off == 0 or pc in PINS
        flag = "  " if planted else "🔴"
        print(f"{flag} fn ${fn:02X}  first PC ${pc:04X}  {name}+{off}" + ("  (pinned)" if pc in PINS and off else ""))
