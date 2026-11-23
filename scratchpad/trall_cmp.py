#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-TRSPEC: set each probe's turbo R reading (scratchpad/AE_trall/NAME.out, from trall_run.py; `CAP ref` = the
FS-A1GT, `CAP ours` = the FS-A1ST) against the reading the page it serves is based on, and the two turbo R references
against each other. The turbo R twin of scratchpad/m1on2_cmp.py.

Baseline per probe:
  MSX1  -- the probe has a committed VG-8020 reading (the `nodisk` / `disk` row of a TRACKED scratchpad run file; a
           probe with `; @disk` takes the `disk` row) -- m1on2_cmp.py's rule, imported from it;
  MSX2  -- otherwise the newest committed FS-A1WSX reading (`msx2p` row) of a tracked file (an MSX2 / MSX2+ page's
           reading). For an MSX1 probe the A1WSX reading (scratchpad/AE_m1on2/) is shown as a second column, so a turbo
           R difference that the MSX2+ already has is told apart from one that is new on the turbo R.
Verdict: SAME / DIFFERS / NO READING (no turbo R CAP, or no committed baseline); `gtst` = bytes where the FS-A1GT and
the FS-A1ST disagree (0 = they agree). Counts are RAW: no excuse list (jiffy-like cells are counted) -- read the
per-byte list (--bytes NAME) before calling any of it a difference. Captures are compared zero-padded (biosl_run.py
prints a capture only to its last non-zero byte); a committed baseline from an older version of a probe (fewer cases)
shows as differences past its end -- check the run file's date against the probe's.

    python3 scratchpad/trall_cmp.py [--bytes NAME] [--md]
"""
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import m1on2_cmp as M  # noqa: E402  -- blocks(), vg8020(), diff()


def a1wsx():
    """{probe: (hex, file)} -- the newest committed msx2p `CAP ref` per probe."""
    files = subprocess.run(["git", "ls-files", "scratchpad"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    out = {}
    for f in files:
        if not f.endswith(".out") or f.startswith("scratchpad/AE_trall/"):
            continue
        try:
            t = open(os.path.join(ROOT, f), errors="replace").read()
        except OSError:
            continue
        if " msx2p: " not in t:
            continue
        when = None
        for (name, row), caps in M.blocks(t).items():
            if row == "msx2p" and "ref" in caps:
                if when is None:
                    when = int(subprocess.run(["git", "log", "-1", "--format=%ct", "--", f], cwd=ROOT,
                                              capture_output=True, text=True).stdout.strip() or 0)
                cur = out.get(name)
                if cur is None or when > cur[0]:
                    out[name] = (when, caps["ref"], f)
    return {n: (v[1], v[2]) for n, v in out.items()}


def vg8020_files():
    """m1on2_cmp.vg8020() returns the hex only; find the file it came from (for the citation)."""
    files = subprocess.run(["git", "ls-files", "scratchpad"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    where = {}
    for f in files:
        if f.endswith(".out") and not f.startswith(("scratchpad/AE_trall/", "scratchpad/AE_m1on2/")):
            try:
                t = open(os.path.join(ROOT, f), errors="replace").read()
            except OSError:
                continue
            for (name, row), caps in M.blocks(t).items():
                if row in ("nodisk", "disk") and "ref" in caps:
                    where.setdefault((name, caps["ref"]), f)
    return where


TRONLY = {"xchgcpu", "xgetcpu", "xtrboot"}    # D-TRSPEC's own probes (CHGCPU / GETCPU / the boot): no earlier page


def block_text(text, name, rows):
    """The lines of NAME's block for the first row in ROWS present in TEXT."""
    cur, out = None, {}
    for ln in text.splitlines():
        m = M.HDR.match(ln)
        if m:
            cur = (os.path.splitext(os.path.basename(m.group(1)))[0], m.group(2))
            continue
        if cur and cur[0] == name:
            out.setdefault(cur[1], []).append(ln)
    for r in rows:
        if r in out:
            return out[r]
    return []


VR = re.compile(r"^  VRAM ([0-9A-Fa-f]{4}): ref=([0-9A-Fa-f]{2}) ours=([0-9A-Fa-f]{2})")
VRW = re.compile(r"^  VRAM(\d+) (ref |ours): ([0-9a-fA-F]+)$")


def spans(name):
    for d in ("spec", "biosl"):
        f = os.path.join(ROOT, "probes", "bios", d, name + ".asm")
        if os.path.exists(f):
            return [(int(a, 16), int(n, 16)) for a, n in
                    re.findall(r"^;\s*@vram\s+([0-9A-Fa-f]+):([0-9A-Fa-f]+)", open(f).read(), re.M)]
    return []


def vram_cmp(name, trtext, bfile, rows):
    """(n_listed, [(addr, base, gt)]) -- the baseline's VRAM ref values are known only at the cells its DIFF listed
    (a non-turbor row prints a VRAM cell only where the reference and C-BIOS disagree)."""
    sp = spans(name)
    whole = {}
    for ln in block_text(trtext, name, ("turbor",)):
        m = VRW.match(ln)
        if m and m.group(2).strip() == "ref" and int(m.group(1)) < len(sp):
            a0 = sp[int(m.group(1))][0]
            for k, b in enumerate(bytes.fromhex(m.group(3))):
                whole[a0 + k] = b
    if not whole or not bfile or bfile == "?":
        return None
    listed = {}
    for ln in block_text(open(os.path.join(ROOT, bfile), errors="replace").read(), name, rows):
        m = VR.match(ln)
        if m:
            listed[int(m.group(1), 16)] = int(m.group(2), 16)
    return len(listed), [(a, v, whole[a]) for a, v in sorted(listed.items()) if a in whole and whole[a] != v]


def hung(text):
    m = re.search(r"NO READING: DONE never set on ([a-z, ]+) \(", text)
    return m.group(1).replace("ref", "A1GT").replace("ours", "A1ST") if m else None


_CT = {}


def caplen(name):
    for d in ("spec", "biosl"):
        f = os.path.join(ROOT, "probes", "bios", d, name + ".asm")
        if os.path.exists(f):
            m = re.search(r"^;\s*@caplen\s+([0-9A-Fa-f]+)", open(f).read(), re.M)
            return int(m.group(1), 16) if m else 0xFF
    return 0xFF


def ctime(path):
    if path in _CT:
        return _CT[path]
    _CT[path] = int(subprocess.run(["git", "log", "-1", "--format=%ct", "--", path], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip() or 0)
    return _CT[path]


def stale(name, bfile):
    """True when the probe's source was committed AFTER the baseline run file (its cases may have changed)."""
    for d in ("spec", "biosl"):
        f = f"probes/bios/{d}/{name}.asm"
        if os.path.exists(os.path.join(ROOT, f)):
            return ctime(f) > ctime(bfile)
    return False


def zdiff(a, b):
    """m1on2_cmp.diff, but the shorter capture is padded with zeros: biosl_run.py prints a capture only up to its last
    non-zero byte (>= 32 B), so a length difference alone is a run of trailing zeros, not a difference."""
    ba, bb = bytes.fromhex(a), bytes.fromhex(b)
    n = max(len(ba), len(bb))
    ba, bb = ba.ljust(n, b"\0"), bb.ljust(n, b"\0")
    return [(i, x, y) for i, (x, y) in enumerate(zip(ba, bb)) if x != y], False


def fmt(d):
    return " ".join(f"+{i:02X}:{x:02X}>{y:02X}" for i, x, y in d)


def main():
    want = sys.argv[sys.argv.index("--bytes") + 1] if "--bytes" in sys.argv else None
    md = "--md" in sys.argv
    vg, wsx, vgf = M.vg8020(), a1wsx(), vg8020_files()
    tally = {}
    if md:
        print("| probe | gen | baseline | turbo R (A1GT) vs baseline | vs A1WSX | A1GT vs A1ST | run |")
        print("|---|---|---|---|---|---|---|")
    for p in sorted(glob.glob(os.path.join(ROOT, "scratchpad", "AE_trall", "*.out"))):
        name = os.path.basename(p)[:-4]
        if want and name != want:
            continue
        text = open(p, errors="replace").read()
        rc = text.splitlines()[0][len("# rc="):] if text.startswith("# rc=") else "?"
        caps = M.blocks(text).get((name, "turbor"), {})
        gt, st = caps.get("ref"), caps.get("ours")
        base = gen = None
        if vg.get(name) and len(vg[name]) == 1:
            base, gen = next(iter(vg[name])), "MSX1"
            bfile = vgf.get((name, base), "?")
        elif name in wsx:
            (base, bfile), gen = wsx[name], "MSX2"
        elif name in TRONLY:
            gen = "TR"
        w = wsx.get(name)
        cols = {}
        if not gt:
            why = "TIMEOUT" if rc == "TIMEOUT" else ("no turbo R CAP" + (" (build failed)" if "missing" in text or
                                                                         "rror" in text.split("=====")[0] else ""))
            verdict = "NO READING"
            cols["base"] = why
        elif gen == "TR":
            verdict = "TR PROBE"
            cols["base"] = "a turbo R probe: its own page, nothing earlier to compare"
        elif not base:
            verdict = "NO READING"
            cols["base"] = "no committed baseline"
        else:
            d, ln = zdiff(base, gt)
            verdict = "DIFFERS" if (d or ln) else "SAME"
            last = caplen(name) - 1
            if d and all(i == last for i, _, _ in d):
                cols["last"] = "only the capture's last byte (+%X), which no case writes" % last
            if d and stale(name, bfile):
                cols["stale"] = "probe newer than baseline"
            cols["base"] = f"{len(d)}{'+LEN' if ln else ''}"
            if want:
                print(f"  {gen} baseline {bfile}\n  vs base: {fmt(d)}")
        h = hung(text)
        if h:
            cols["hang"] = f"DONE never set on {h}"
        if gt and base:
            v = vram_cmp(name, text, bfile, ("disk", "nodisk") if gen == "MSX1" else ("msx2p",))
            if v is not None:
                cols["vram"] = f"VRAM {len(v[1])}/{v[0]} listed cells differ"
                if v[1] and verdict == "SAME":
                    verdict = "DIFFERS"
                if want:
                    print("  VRAM vs base (listed cells only): " + " ".join(f"{a:04X}:{x:02X}>{y:02X}" for a, x, y in v[1]))
        if gt and w and gen == "MSX1":
            d, ln = zdiff(w[0], gt)
            cols["wsx"] = f"{len(d)}{'+LEN' if ln else ''}"
            if want:
                print(f"  vs A1WSX ({w[1]}): {fmt(d)}")
        if gt and st:
            d, ln = zdiff(gt, st)
            m = re.search(r"^  DIFF \((\d+) unexcused", text, re.M)
            cols["gtst"] = m.group(1) if m else f"{len(d)}{'+LEN' if ln else ''}"   # biosl's count: CAP + VRAM + ...
            if want:
                print(f"  A1GT vs A1ST (CAP): {fmt(d)}")
                for ln_ in text.splitlines():
                    if ln_.startswith("  VRAM ") and ": ref=" in ln_:
                        print("  A1GT vs A1ST" + ln_[1:])
        elif gt:
            cols["gtst"] = "A1ST no reading"
        if cols.get("gtst", "0") not in ("0",) and verdict != "NO READING":
            tag = verdict + " + GT/ST DIFF"
        else:
            tag = verdict
        tally[tag] = tally.get(tag, 0) + 1
        if md:
            print(f"| {name} | {gen or '-'} | {os.path.basename(bfile) if base else '-'} | {verdict}"
                  f"{' (' + cols['base'] + ')' if verdict not in ('SAME', 'TR PROBE') else ''} | {cols.get('wsx', '-')} | "
                  f"{cols.get('gtst', '-')} | [{name}.out](../../scratchpad/AE_trall/{name}.out) |")
        else:
            print(f"{name:10s} {gen or '-':4s} {verdict:10s} base={cols['base']:<6s} wsx={cols.get('wsx', '-'):<6s} "
                  f"gtst={cols.get('gtst', '-')}  rc={rc}  {cols.get('vram', '')}  {cols.get('hang', '')}  {cols.get('stale', '')}  {cols.get('last', '')}")
    print("\nTALLY: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))


if __name__ == "__main__":
    main()
