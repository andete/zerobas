# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PUTDIR (gate: putdir-acceptance): WHEN does a RANDOM file's directory entry
change -- at each PUT, or at CLOSE? Read from the disk IMAGE the machine leaves.

  noclose  OPEN"R.DAT" AS #1 LEN=128 : FIELD : LSET : PUT #1,1, NO CLOSE
           -> the entry's size and first cluster as the medium holds them
  close    the same, then CLOSE              -> the entry after CLOSE
  lof      PUT #1,1 then PRINT LOF(1), no CLOSE  (LOF is live meanwhile)

D-LOF §4c measured the reference's face: after `PUT #1,1` LOF reads the new
size while the on-disk entry still holds 0. Ours stamped the directory at
EVERY PUT (a directory read + write each time; 20 PUTs + CLOSE were 4.5x the
CF-3300, scratchpad/putstopwatch20.out) until D-PUTDIR moved the stamp to
CLOSE. Cluster NUMBERS are compared as "allocated or not", never by value.

Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402

PUT = ['OPEN"R.DAT" AS #1 LEN=128', "FIELD#1,128 AS A$", 'LSET A$="Q"', "PUT#1,1"]
CASES = {
    "noclose": PUT + ['PRINT"[D]"'],
    "close": PUT + ["CLOSE", 'PRINT"[D]"'],
    "lof": PUT + ['PRINT"[L";LOF(1);"]"'],
}


def reading(machine, tag, name):
    dsk = probe_tmp.tmp(f"putdir_{name}_{tag}.dsk")
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    raw = omsx_repl.run_cases(machine, [("direct", ["MAXFILES=1"] + CASES[name] + ["FILES"])],
                              batch=False, reset=("", "SCREEN 0"), boot=14.0, step=4.5,
                              diska=dsk)[0] or ""
    if name == "lof":
        m = re.findall(r"\[L\s*(\d+)\s*\]", re.sub(r"\s+", " ", raw))
        return f"LOF {m[-1]}" if m else None
    ent = RT.Fat12(dsk).dirent("R", "DAT")
    if ent is None:
        return "no entry"
    return f"size {ent['size']}, cluster {'yes' if ent['cluster'] else 'none'}"


def main():
    only = sys.argv[1:] or list(CASES)
    got = {(t, n): reading(m, t, n) for t, m in (("CF-3300", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE))
           for n in only}
    for n in only:
        print(f"== {n:8s} CF-3300 {got[('CF-3300', n)]!s:26s} ours {got[('OURS', n)]!s}")
    if any(got[("CF-3300", n)] is None for n in only):
        print("\nINSTRUMENT FAULT: the CF-3300 gave no reading")
        return 2
    bad = [n for n in only if got[("CF-3300", n)] != got[("OURS", n)]]
    for n in bad:
        print(f"DIVERGES {n}: CF-3300 {got[('CF-3300', n)]} vs ours {got[('OURS', n)]}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a RANDOM file's entry changes at CLOSE, not per PUT "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
