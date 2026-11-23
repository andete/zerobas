#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX1ON2: set each MSX1 spec probe's MSX2 / MSX2+ REFERENCE capture (scratchpad/AE_m1on2/NAME.out, from
m1on2_run.py) against the VG-8020's committed one (the `nodisk` row of the tracked scratchpad run files), and the
C-BIOS MSX2 build against its own MSX2 reference.

Per probe, one line per machine:  gen=<bytes differing VG-8020 vs this MSX2 ref>  cbios=<bytes differing this ref vs
C-BIOS's build of it>, or a reason there is no reading. A probe whose committed VG-8020 lines disagree among
themselves is flagged (the reference is never re-run, so they should not). Byte counts are RAW: no excuse list
(jiffy-like cells are counted) -- read the per-byte list (--bytes NAME) before calling any of it a difference.

    python3 scratchpad/m1on2_cmp.py [--bytes NAME]
"""
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HDR = re.compile(r"^===== (\S+?) (\w+): ")
CAP = re.compile(r"^  CAP (ref |ours): ([0-9a-fA-F]+)$")


def blocks(text):
    """{(name, row): {'ref': hex, 'ours': hex}} from a biosl_run output."""
    out, cur = {}, None
    for ln in text.splitlines():
        m = HDR.match(ln)
        if m:
            cur = (os.path.splitext(os.path.basename(m.group(1)))[0], m.group(2))
            out.setdefault(cur, {})
            continue
        m = CAP.match(ln)
        if m and cur:
            out[cur][m.group(1).strip()] = m.group(2).lower()
    return out


def vg8020():
    files = subprocess.run(["git", "ls-files", "scratchpad"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    refs = {}
    for f in files:
        if not f.endswith(".out"):
            continue
        try:
            t = open(os.path.join(ROOT, f), errors="replace").read()
        except OSError:
            continue
        if "nodisk:" not in t and "disk:" not in t:
            continue
        when = None
        for (name, row), caps in blocks(t).items():
            if row in ("nodisk", "disk") and "ref" in caps:
                if when is None:
                    when = int(subprocess.run(["git", "log", "-1", "--format=%ct", "--", f], cwd=ROOT,
                                              capture_output=True, text=True).stdout.strip() or 0)
                refs.setdefault(name, []).append((row == "nodisk", when, caps["ref"], f))
    # the NEWEST committed reading (a probe's cases grow over time), nodisk before disk (both are the VG-8020)
    return {n: {max(v)[2]} for n, v in refs.items()}


def diff(a, b):
    ba, bb = bytes.fromhex(a), bytes.fromhex(b)
    d = [(i, x, y) for i, (x, y) in enumerate(zip(ba, bb)) if x != y]
    return d, len(ba) != len(bb)


def main():
    want = sys.argv[sys.argv.index("--bytes") + 1] if "--bytes" in sys.argv else None
    refs = vg8020()
    for p in sorted(glob.glob(os.path.join(ROOT, "scratchpad", "AE_m1on2", "*.out"))):
        name = os.path.basename(p)[:-4]
        if want and name != want:
            continue
        b = blocks(open(p).read())
        vg = refs.get(name)
        line = [f"{name:10s}"]
        if not vg:
            line.append("VG-8020: no committed nodisk / disk run")
        elif len(vg) > 1:
            line.append(f"VG-8020: {len(vg)} DIFFERENT committed ref lines")
        for row in ("msx2eu", "msx2jp", "msx2p"):
            caps = b.get((name, row), {})
            r, o = caps.get("ref"), caps.get("ours")
            g = c = "-"
            if r and vg and len(vg) == 1:
                d, ln = diff(next(iter(vg)), r)
                g = f"{len(d)}{'+LEN' if ln else ''}"
                if want:
                    print(f"  {row} gen: " + " ".join(f"+{i:02X}:{x:02X}>{y:02X}" for i, x, y in d))
            if r and o:
                d, ln = diff(r, o)
                c = f"{len(d)}{'+LEN' if ln else ''}"
                if want:
                    print(f"  {row} cbios: " + " ".join(f"+{i:02X}:{x:02X}>{y:02X}" for i, x, y in d))
            line.append(f"{row}: gen={g if r else 'NOREF'} cbios={c if o else 'NOREAD'}")
        print("  ".join(line))


if __name__ == "__main__":
    main()
