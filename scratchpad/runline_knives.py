#!/usr/bin/env python3
"""D-RUNLINE knife runner. Predictions written BEFORE the run (spec §6).

Conventions from docs/dev-workflow.md 'Knives' and the project's operating rules:
  * the subject is the PROBE invoked directly, never `make <gate>` (make exits 2
    for any failed recipe, so rc cannot separate 'tree regressed' from
    'instrument broke');
  * restore by WRITING THE BYTES back, never shutil.copy2 (copy2 preserves mtime
    and make then rebuilds nothing);
  * `rm -rf build` before EVERY knife build -- writing a source in the same mtime
    tick as the last restore's artifacts can leave make deciding nothing changed;
  * ROM-HASH GUARD ON BOTH IMAGES: a cut that does not move the ROM was never
    applied, and a green row under an unapplied cut is a claim about the runner;
  * cut a VALUE, not a call (deleting a call fails `make deadcode`, so no ROM
    gets built and the knife cannot run);
  * restore in `finally`.

THE THREE CLAIMS UNDER TEST, one knife each, plus a fourth that pins the row the
others leave agreeing-for-the-wrong-reason:
  K-RL1  the OPERAND is genuinely read (not "any RUN restarts somewhere")
  K-RL2  GOTOTGT is what run_prog_at consumes  (the pre-slice `ld hl,TXTBASE`)
  K-RL3  RESTORE_LINE is deliberately NOT the start line (§2's split)
  K-RL4  n.runundef is not just agreeing because its knifed target is also absent
"""
import hashlib, pathlib, re, subprocess, sys

ROOT  = pathlib.Path("/Users/joost/projects/zerobas")
CLOAD = ROOT / "basic/cload.asm"
PROG  = ROOT / "basic/program.asm"
ROMS  = [ROOT / "build/basic-reloc.rom", ROOT / "build/sub.rom"]
ROWS  = ("n.runline", "n.runundef", "n.rundata", "n.runlinectl")
PROBE = ["python3", "probes/basic/basic_probe_namspc.py", "--gate",
         "--sides", "vg8020,cf3300,zb", "--only", ",".join(ROWS)]

ORIG = {p: p.read_text() for p in (CLOAD, PROG)}

# (name, file, old, new, PREDICTED divergent set)  -- written before the run
KNIVES = [
    ("K-RL1  the lineno operand -> a constant EXISTING line (30 = END)",
     CLOAD,
     "                ld      c,(hl)              ; target line number, LE (GOTO's grammar)",
     "                ld      c,30                ; K-RL1",
     {"n.runline"}),
    ("K-RL2  run_prog_at reads TXTBASE again (the pre-slice behaviour)",
     PROG,
     "                ld      hl,(GOTOTGT)        ; D-RUNLINE: the line to begin at (TXTBASE",
     "                ld      hl,TXTBASE          ; K-RL2",
     {"n.runline", "n.rundata"}),
    ("K-RL3  RESTORE_LINE FOLLOWS the start line (undoes the §2 split)",
     PROG,
     "                ld      hl,TXTBASE\n                ld      (RESTORE_LINE),hl   ; ⚠️ DATA restores from the PROGRAM TOP even",
     "                ld      hl,(GOTOTGT)        ; K-RL3\n                ld      (RESTORE_LINE),hl   ; ⚠️ DATA restores from the PROGRAM TOP even",
     {"n.rundata"}),
    ("K-RL4  the operand -> a constant line that EXISTS in every fixture (10)",
     CLOAD,
     "                ld      c,(hl)              ; target line number, LE (GOTO's grammar)",
     "                ld      c,10                ; K-RL4",
     {"n.runline", "n.runundef", "n.rundata"}),
]


def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def hashes():
    return tuple(hashlib.sha256(r.read_bytes()).hexdigest()[:8] if r.exists()
                 else "<none>" for r in ROMS)


def restore():
    for p, txt in ORIG.items():
        p.write_text(txt)                 # WRITE THE BYTES, never copy2


def divergent(out):
    """The probe's divergent set, or None if the report shape was not found.

    🔴 THE MARKER IS `DIFF`, NOT `MISS`. Draft 1 of this runner grepped for
    `MISS` -- a token this probe never prints -- so every knife came back
    `got=[]` and the runner reported 0/4 with all four ROMs provably moved. A
    parser that cannot see a divergence reports a BROKEN TREE AS CLEAN, which is
    the failure D-WALLDATE's draft 1 had (0 of 4 target defects, reported CLEAN).
    Hence the seen-row census below: if the probe does not print every row this
    runner asked for, that is an APPARATUS fault, not an empty divergent set.
    """
    seen, rows = set(), set()
    for line in out.splitlines():
        mm = re.match(r"^(ok|DIFF|\.\.\.\.)\s+(\S+)", line.strip())
        if not mm:
            continue
        tag, lab = mm.group(1), mm.group(2)
        if lab not in ROWS:
            continue
        seen.add(lab)
        if tag == "DIFF":
            rows.add(lab)
    if seen != set(ROWS):
        missing = sorted(set(ROWS) - seen)
        print(f"        APPARATUS: probe printed {len(seen)}/{len(ROWS)} of the "
              f"rows asked for; missing {missing}")
        return None
    return rows


def build():
    sh(["rm", "-rf", "build"])
    r = sh(["make", "repack-machine"])
    return r.returncode == 0


def main():
    try:
        print("== build BEFORE the baseline ==")
        if not build():
            print("APPARATUS: repack failed"); return 3
        base_h = hashes()
        r = sh(PROBE)
        base = divergent(r.stdout + r.stderr)
        print(f"baseline rc={r.returncode} roms={base_h} divergent="
              f"{sorted(base) if base is not None else 'UNPARSED'}")
        if base is None:
            print("APPARATUS: baseline report unparsed"); return 3
        if base:
            print(f"APPARATUS: baseline is not clean ({sorted(base)})"); return 3

        results = []
        for name, path, old, new, pred in KNIVES:
            restore()
            txt = ORIG[path]
            if txt.count(old) != 1:
                print(f"APPARATUS: {name}: anchor matched {txt.count(old)}x"); return 3
            path.write_text(txt.replace(old, new))
            if not build():
                print(f"{name}: BUILD FAILED -- a knife that cannot run")
                results.append((name, pred, None, False)); continue
            h = hashes()
            if h == base_h:
                print(f"{name}: ROM DID NOT MOVE {h} -- the cut was never applied")
                results.append((name, pred, None, False)); continue
            rr = sh(PROBE)
            got = divergent(rr.stdout + rr.stderr)
            ok = got == pred
            print(f"{'EXACT' if ok else 'MISS '}  {name}\n"
                  f"        roms={h}  want={sorted(pred)}  got="
                  f"{sorted(got) if got is not None else 'UNPARSED'}")
            results.append((name, pred, got, ok))
    finally:
        restore()
        sh(["rm", "-rf", "build"])
        sh(["make", "repack-machine"])
        print(f"\nrestored: roms={hashes()}")
        for p in ORIG:
            assert p.read_text() == ORIG[p], f"{p} not restored!"
        print("both sources byte-identical to their originals")

    n_ok = sum(1 for *_, ok in results if ok)
    print(f"\n{n_ok}/{len(results)} knife rows EXACT")
    return 1 if n_ok != len(results) else 0


if __name__ == "__main__":
    sys.exit(main())
