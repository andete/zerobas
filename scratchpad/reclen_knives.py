#!/usr/bin/env python3
"""D-RECLEN knives. Predictions written BEFORE the run (spec §7).

Per docs/dev-workflow.md: the PROBE is invoked directly (make exits 2 for any
failed recipe, so its rc cannot separate "tree regressed" from "instrument
broke"); restore is from a scratchpad SNAPSHOT in a `finally`; the build happens
BEFORE the baseline; and every cut is ROM-HASH GUARDED, because a green row under
a cut that never reached the ROM is a claim about the runner, not the tree.
"""
import hashlib, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path("/Users/joost/projects/zerobas")
SRC  = ROOT / "basic/field.asm"
SNAP = ROOT / "scratchpad/reclen_field.asm.snapshot"
ROM  = ROOT / "build/zerobas-main-eu.rom"
PROBE = ["python3", "probes/basic/basic_probe_fldwidth.py", "--gate"]

KNIVES = [
    # The bound becomes a CONSTANT 256 instead of FCH_RECLENS[ch]. Same length:
    # `ld e,(hl) / inc hl / ld d,(hl)` is 5E 23 56, `ld de,256` is 11 00 01.
    # This is the exact wrong implementation the old denominator could not rule
    # out, so it must redden precisely the rows built to discriminate them --
    # and NOT d.sum/d.sum1, whose totals (300, 257) exceed 256 either way.
    ("K-RC1  the bound becomes a constant 256",
     "                ld      e,(hl)\n                inc     hl\n                ld      d,(hl)              ; DE = FCH_RECLENS[ch], 1..256",
     "                ld      de,256              ; KNIFE: constant, not the record",
     {"r.over", "r.mid", "r.sum128"}),
    # Wrong error code: everything that raises still raises, with the wrong name.
    ("K-RC2  ERR 50 -> ERR 51",
     "                ld      a,50                ; ERR 50: FIELD overflow",
     "                ld      a,51                ; KNIFE: wrong code",
     {"d.sum", "d.sum1", "r.over", "r.mid", "r.sum128"}),
    # `total == record` stops fitting: `jr z` becomes a second `jr c`, so the
    # equal case falls through to the raise. Pins the boundary as INCLUSIVE.
    ("K-RC3  an exactly-full record stops fitting",
     "                jr      z,exf_fits          ; total == record -> exactly fills it",
     "                jr      c,exf_fits          ; KNIFE: equal now raises",
     {"r.ok", "d.sumok"}),
]

def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

def rom_hash():
    return hashlib.sha256(ROM.read_bytes()).hexdigest()[:8] if ROM.exists() else "<none>"

def diffs(out):
    """Rows the probe scored as DIFF. None if no report shape was found."""
    if "readings match their reference" not in out:
        return None
    return set(re.findall(r'^DIFF\s+(\S+)', out, re.M))

def main():
    shutil.copy2(SRC, SNAP)
    try:
        if sh(["make", "repack-machine"]).returncode:
            print("APPARATUS: repack failed"); return 3
        base_hash = rom_hash()
        r = sh(PROBE)
        base = diffs(r.stdout + r.stderr)
        print(f"baseline rc={r.returncode} rom={base_hash} diffs={sorted(base) if base is not None else 'UNPARSED'}")
        if base is None: print("APPARATUS: baseline unparsed"); return 3
        if base:        print(f"APPARATUS: baseline not clean {sorted(base)}"); return 3

        results = []
        for name, old, new, pred in KNIVES:
            txt = SNAP.read_text()
            if txt.count(old) != 1:
                results.append((name, "APPARATUS", f"cut site matched {txt.count(old)}x")); continue
            SRC.write_text(txt.replace(old, new))
            if sh(["make", "repack-machine"]).returncode:
                results.append((name, "APPARATUS", "build failed")); SRC.write_text(txt); continue
            h = rom_hash()
            if h == base_hash:
                results.append((name, "APPARATUS", "ROM UNCHANGED — cut never applied")); SRC.write_text(txt); continue
            r = sh(PROBE)
            got = diffs(r.stdout + r.stderr)
            SRC.write_text(txt)
            if got is None:
                results.append((name, "APPARATUS", f"report unparsed (rc={r.returncode})")); continue
            verdict = "EXACT" if got == pred else ("MISS" if not got else "PARTIAL")
            results.append((name, verdict, f"rom={h} pred={sorted(pred)} got={sorted(got)}"))

        print("\n== D-RECLEN knives ==")
        for n, v, d in results:
            print(f"  {v:9s} {n}\n            {d}")
        return 0
    finally:
        # 🔴 NOT shutil.copy2 — IT PRESERVES MTIME, AND THAT LEAVES A STALE ROM.
        # copy2 restored the correct SOURCE but stamped it with the snapshot's
        # (older) mtime, so `make` saw the ROM as newer than its input, rebuilt
        # nothing, and the next gate ran against the ROM built from the LAST
        # KNIFE. It read 45/47 with exactly K-RC3's two rows red -- a false
        # regression that looks precisely like a real one. Write the bytes so the
        # mtime moves, then rebuild.
        SRC.write_text(SNAP.read_text())
        sh(["make", "repack-machine"])
        print("\n[restored from snapshot and rebuilt]")

sys.exit(main())
