# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ASAVEDOUT (gate: asavedev-acceptance): the file `SAVE"Q.BAS",A` writes,
read back from the IMAGE, byte for byte against the CF-3300's.

  plain  10 REM HELLO, then SAVE ,A                  -- the control
  big    28 REM lines of 64 characters (~2 KB: more than one cluster on
         test720, so sector flushes and a cluster link are in the stream).
         A first cut typed eight 240-character lines and the CF-3300 stored
         NONE of them (it saved an empty program, 0 B) -- typed screen lines
         that long are not a program here, so the row measured the typing.
         🔴 AND THAT DIAGNOSIS WAS WRONG: it was the session ending before
         the CF-3300 had committed the file. Two lines after the SAVE and it
         reads 2064 B, ours' size. The row shape was never the fault.
  crt    OPEN"CRT:"FOR OUTPUT AS#1 : PRINT#1,"X" : CLOSE#1, then SAVE ,A.
         SEPARATES "the ASCII save writes to the disk" from "it writes to the
         sink the last PRINT# chose": PRDEV is the PRINT# device selector
         and SAVE ,A did not set it.

S10 increment 3 moves SAVE ,A onto disk.rom's writer (H_FOPEN's OPEN FOR
OUTPUT selector, then H_CHOUT / H_CHCLOSE, all with no channel live), so this is
the file it must keep writing. Size and every byte are compared; cluster
NUMBERS are not.

Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402

LONG = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" * 2      # 72
CASES = {
    "plain": ["NEW", "10 REM HELLO", 'SAVE"Q.BAS",A'],
    "big": ["NEW"] + [f"{10 * i} REM {LONG[:64]}" for i in range(1, 29)]
           + ['SAVE"Q.BAS",A'],
    "crt": ["NEW", "10 REM HELLO", 'OPEN"CRT:"FOR OUTPUT AS#1', 'PRINT#1,"X"',
            "CLOSE#1", 'SAVE"Q.BAS",A'],
}


def file_of(path):
    fat = RT.Fat12(path)
    ent = fat.dirent("Q", "BAS")
    if not ent:
        return None
    if not ent.get("cluster"):
        return ent["size"], b""
    chain, _ = fat.chain(ent["cluster"])
    data = b"".join(fat.cluster_bytes(c) for c in chain)
    return ent["size"], data[:ent["size"]]


def main():
    only = sys.argv[1:] or list(CASES)
    got = {}
    for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
        for name in only:
            dsk = probe_tmp.tmp(f"asavedev_{name}_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            # 🔴 the trailing lines are TIME, not output: with SAVE last, the
            # session ended before the CF-3300's 2 KB write had committed its
            # directory entry, and the image read 0 B (ours 2064)
            omsx_repl.run_cases(machine, [("direct", CASES[name] + ['PRINT"[D]"', "FILES"])],
                                batch=False,
                                reset=("", "SCREEN 0"), boot=14.0, step=3.0, diska=dsk)
            got[(tag, name)] = file_of(dsk)
            q = got[(tag, name)]
            print(f"== {tag} {name}: Q.BAS "
                  + ("absent" if q is None else f"{q[0]} B {q[1][:48]!r}"
                     + ("..." if len(q[1]) > 48 else "")))
    if any(got[("STOCK", n)] is None for n in only):
        print("\nINSTRUMENT FAULT: the CF-3300 left no Q.BAS -- no reference")
        return 2
    bad = []
    for name in only:
        s, o = got[("STOCK", name)], got[("OURS", name)]
        if o is None:
            bad.append(f"{name}: ours wrote no Q.BAS (CF-3300 {s[0]} B)")
        elif s != o:
            i = next((k for k in range(min(len(s[1]), len(o[1])))
                      if s[1][k] != o[1][k]), min(len(s[1]), len(o[1])))
            bad.append(f"{name}: CF-3300 {s[0]} B vs ours {o[0]} B, first difference "
                       f"at byte {i}: {s[1][i:i + 16]!r} vs {o[1][i:i + 16]!r}")
    for b in bad:
        print("DIVERGES " + b)
    print(f"\n{'PASS' if not bad else 'FAIL'}: SAVE ,A writes the CF-3300's file "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
