#!/usr/bin/env python3
"""D-FORRET knife runner. Predictions written BEFORE the run (spec §7).

Conventions from docs/dev-workflow.md 'Knives':
  * the subject is the PROBE invoked directly, never `make <gate>` (make exits 2
    for any failed recipe, so rc cannot separate 'tree regressed' from
    'instrument broke');
  * restore from a scratchpad SNAPSHOT, never `git checkout --`;
  * build BEFORE the baseline;
  * ROM-HASH GUARD: a cut that does not move the ROM was never applied, and a
    green row under an unapplied cut is a claim about the runner, not the tree;
  * restore in `finally`.
"""
import hashlib, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC  = ROOT / "basic/program.asm"
SNAP = ROOT / "scratchpad/forret_program.asm.snapshot"
ROM  = ROOT / "build/zerobas-main-eu.rom"
PROBE = ["python3", "probes/basic/basic_probe_lnblank.py", "--gate", "--say",
         "--sides", "vg8020,cf3300,zb", "--only", "lnrt-for", "--repeat", "1"]

# (name, old, new, predicted DIVERGENT set)
KNIVES = [
    ("K-FR1  ex_ret_under's clear -> a dead cell",
     "                ld      hl,FOR_STK\n                ld      (FSP),hl\n",
     "                ld      hl,FOR_STK\n                ld      (FOR_CUR),hl\n",
     {"lnrt-forret"}),
    ("K-FR2  ret_frame's restore -> a dead cell",
     "                ld      (FSP),de            ; every FOR opened since the GOSUB is gone",
     "                ld      (FOR_CUR),de        ; every FOR opened since the GOSUB is gone",
     {"lnrt-forgsb", "lnrt-forgdeep", "lnrt-forgline"}),
    ("K-FR3  gosub_push records a CONSTANT empty depth",
     "                ld      hl,(FSP)\n                ld      a,l\n                ld      (de),a",
     "                ld      hl,FOR_STK\n                ld      a,l\n                ld      (de),a",
     {"lnrt-forgctl"}),
]

def sh(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)

def rom_hash():
    return hashlib.sha256(ROM.read_bytes()).hexdigest()[:8] if ROM.exists() else "<none>"

def divergent(out):
    """Parse the probe's DIVERGENT block. Returns None if no report shape found."""
    if "DIVERGENT:" not in out:
        if "gating rows agree" in out:
            return set()
        return None
    tail = out.split("DIVERGENT:", 1)[1]
    return set(re.findall(r"^\s{2}(lnrt-\S+)\s*$", tail, re.M))

def main():
    shutil.copy2(SRC, SNAP)
    try:
        print("== build BEFORE the baseline ==")
        r = sh(["make", "repack-machine"])
        if r.returncode: print("APPARATUS: repack failed"); return 3
        base_hash = rom_hash()
        r = sh(PROBE)
        base = divergent(r.stdout + r.stderr)
        print(f"baseline rc={r.returncode} rom={base_hash} divergent={sorted(base) if base is not None else 'UNPARSED'}")
        if base is None: print("APPARATUS: baseline report unparsed"); return 3
        if base: print(f"APPARATUS: baseline is not clean ({sorted(base)})"); return 3

        results = []
        for name, old, new, pred in KNIVES:
            txt = SNAP.read_text()
            if txt.count(old) != 1:
                results.append((name, "APPARATUS", f"cut site matched {txt.count(old)}x")); continue
            SRC.write_text(txt.replace(old, new))
            r = sh(["make", "repack-machine"])
            if r.returncode:
                results.append((name, "APPARATUS", "build failed")); SRC.write_text(txt); continue
            h = rom_hash()
            if h == base_hash:
                results.append((name, "APPARATUS", "ROM UNCHANGED - cut never applied")); SRC.write_text(txt); continue
            r = sh(PROBE)
            got = divergent(r.stdout + r.stderr)
            SRC.write_text(txt)
            if got is None:
                results.append((name, "APPARATUS", f"report unparsed (rc={r.returncode})")); continue
            verdict = "EXACT" if got == pred else ("MISS" if not got else "PARTIAL")
            results.append((name, verdict, f"rom={h} pred={sorted(pred)} got={sorted(got)}"))

        print("\n== D-FORRET knives ==")
        for n, v, d in results:
            print(f"  {v:9s} {n}\n            {d}")
        return 0
    finally:
        shutil.copy2(SNAP, SRC)
        sh(["make", "repack-machine"])
        print("\n[restored from snapshot and rebuilt]")

sys.exit(main())
