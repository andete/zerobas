#!/usr/bin/env python3
r"""D-DIMBARE K-DB1..K-DB3 — three claims, three cuts.

The fix is 3 bytes (`pop af / jr ed_next` where `jr ee_synerr_pop` stood), so
each of its parts is separately checkable:

  K-DB1  revert the arm entirely -> the 11 fixed rows must go BACK to ERR 2.
         Proves the fix is what moves them, not something else in the build.
  K-DB2  `jr ed_next` -> `jr ed_done`: an ignored item stops the LIST instead of
         continuing it. Must redden the multi-item rows (DIM A,B / DIM A,B(2) /
         DIM B,A(2)) and leave the single-item ones green. Proves the
         continuation target is load-bearing, not an arbitrary landing.
  K-DB3  🔴 THE ONE THAT MATTERS FOR THE RULE. ed_lp's `is_letter` guard is what
         still rejects `DIM A,` / `DIM` / `DIM 1` / `DIM $` -- four rows that are
         GREEN BOTH BEFORE AND AFTER the fix, and therefore prove nothing on
         their own. Cutting the guard to ed_next makes the wider rule ("DIM is
         lax about anything that is not `(`") real; those four rows must go RED.
         Without this arm, "rule (b) would have shipped three regressions" is a
         story rather than a measurement.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit.
"""
import atexit, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM: prove the cut reached the ROM

TMP = "/tmp/zerobas"
SRC = "basic/arrays.asm"

KNIVES = [
    ("K-DB1 revert the arm",
     "                pop     af                  ; discard [STR?] -- nothing is created\n"
     "                jr      ed_next             ; +1 B of the low region",
     "                jr      ee_synerr_pop       ; K-DB1 CUT (restored on exit)"),
    ("K-DB2 stop the list",
     "                jr      ed_next             ; +1 B of the low region",
     "                jr      ed_done             ; K-DB2 CUT (restored on exit)"),
    ("K-DB3 widen past is_letter",
     "                call    is_letter           ; a DIM target must START with a letter;\n"
     "                jp      nc,stmt_error       ; reject bare `$` / a digit name (D1,",
     "                call    is_letter           ; K-DB3 CUT (restored on exit)\n"
     "                jp      nc,ed_next          ; reject bare `$` / a digit name (D1,"),
]


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def read_rows(path):
    rows = {}
    for line in open(path, errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[0][:2] in ("d.", "e.", "s.", "f."):
            rows[p[0]] = " ".join(p[1:])
    return rows


def main():
    os.makedirs(TMP, exist_ok=True)
    base = read_rows(f"{TMP}/pm_dimfix_zb.out")
    if not base:
        print(f"NO BASELINE: popmerge_probe.py zb > {TMP}/pm_dimfix_zb.out first")
        return 2
    print(f"baseline (WITH the fix in): {len(base)} rows\n")

    results = {}
    for name, old, new in KNIVES:
        orig = open(SRC).read()
        if orig.count(old) != 1:
            print(f"{name}: KNIFE BROKEN -- anchor matches {orig.count(old)}x")
            results[name] = None
            continue
        restore = lambda o=orig: open(SRC, "w").write(o)
        atexit.register(restore)
        tag = name.split()[0]
        try:
            open(SRC, "w").write(orig.replace(old, new))
            print(f"{name}: planted, rebuilding...")
            _before = knife_guard.hashes()
            _moved, _after, _rc = knife_guard.build(f"{TMP}/dbk_{tag}_build.out", _before)
            print(knife_guard.report(tag, _moved, _before, _after))
            if not _moved and not _rc:
                results[name] = None; continue
            if _rc:
                print(f"{name}: BUILD FAILED"); results[name] = None; continue
            sh("python3 scratchpad/popmerge_probe.py zb", f"{TMP}/dbk_{tag}.out")
        finally:
            restore()
            atexit.unregister(restore)
        cut = read_rows(f"{TMP}/dbk_{tag}.out")
        moved = sorted(r for r in base if base[r] != cut.get(r))
        results[name] = moved
        print(f"{name}: moved {len(moved)} row(s): {' '.join(moved) or '(none)'}")
        for r in moved:
            print(f"      {r:<11s} {base[r]:>14s}  ->  {cut.get(r)}")
        print()

    sh("make repack-machine", f"{TMP}/dbk_restore.out")
    print("=" * 68)
    dead = [n for n, m in results.items() if not m]
    for n, m in results.items():
        print(f"  {n:<28s} {'🔴 REDDENED NOTHING' if not m else str(len(m)) + ' row(s)'}")
    print()
    print("VERDICT:", "every claim has a live arm" if not dead
          else f"🔴 ARMS THAT NEVER FIRED: {dead}")
    return 0 if not dead else 1


if __name__ == "__main__":
    sys.exit(main())
