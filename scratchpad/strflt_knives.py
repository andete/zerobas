#!/usr/bin/env python3
r"""D-STRFLT — three arms, and two of them are DISCRIMINATING rather than blanket.

  K-SF1  cut the FACTYP dispatch, so every STR$ takes the integer path again.
         Every float row must move -- and the set is exactly the 15 that were
         DIFF before the fix, which is the strongest form this arm can take.
  K-SF2  keep PRINT's trailing space (drop the `dec b`). 🎯 ONLY THE FENCE AND
         LEN ROWS MAY MOVE. The v.* rows print the string through a harness that
         STRIPS, and the r.* rows feed it to VAL, which skips blanks -- so if a
         v.* or r.* row moved here, the cut would not be doing what it says.
         This arm is what proves the fence/LEN rows were necessary.
  K-SF3  make flt_out skip flt_fmt. 🎯 THE INVERSE OF K-SF1: the CONTROLS must
         move and the SUBJECTS must not, because STR$ calls flt_fmt directly and
         only PRINT goes through flt_out. That is what says the split is a split
         and not a rename.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP = "/tmp/zerobas"
STR, FLT = "basic/str-engine.asm", "basic/float.asm"
ROW = re.compile(r"^[a-z]+\.")

KNIVES = [
    ("K-SF1 cut the FACTYP dispatch", STR, [
        ("""                cp      2                   ; print.asm's exp_num does
                jr      nz,sfs_float""",
         """                cp      2                   ; K-SF1 CUT (restored on exit)
                nop
                nop""")]),
    ("K-SF2 keep PRINT's trailing space", STR, [
        ("""                dec     b                   ; drop it""",
         """                nop                         ; K-SF2 CUT (restored on exit)""")]),
    ("K-SF3 flt_out skips flt_fmt", FLT, [
        ("""flt_out:
                call    flt_fmt
                jp      print_string""",
         """flt_out:
                ld      hl,FOUTBUF          ; K-SF3 CUT (restored on exit)
                jp      print_string""")]),
]

EXPECT = {
    # exactly the 15 rows that were DIFF before the fix.
    "K-SF1": {"v.frac", "v.negfrac", "v.small", "v.big", "v.efrm", "v.dbl",
              "v.expr", "q.frac", "q.big", "l.frac", "l.small", "l.big",
              "r.frac", "r.big", "r.neg"},
    # only the rows that can SEE a space: the two fences and the three float
    # lengths. l.int / l.neg / l.zero are integer rows and take the other arm.
    "K-SF2": {"q.frac", "q.big", "l.frac", "l.small", "l.big"},
    # the three float CONTROLS, and nothing else -- STR$ never calls flt_out.
    "K-SF3": {"ctl.frac", "ctl.big", "ctl.small"},
}


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def read_rows(path):
    rows = {}
    if not os.path.exists(path):
        return rows
    for line in open(path, errors="replace"):
        p = line.split()
        if len(p) >= 2 and ROW.match(p[0]):
            rows[p[0]] = (" ".join(p[1:]).replace(" SAME", "").replace(" DIFF", "")
                          .replace(" NO-ORACLE", "").strip())
    return rows


def main():
    base = read_rows(f"{TMP}/strflt_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/strflt_probe.py zb "
              f"> {TMP}/strflt_zb_base.out")
        return 2
    print(f"baseline: {len(base)} row(s)\n")
    only = set(sys.argv[1:])
    fails = []
    for name, src, cuts in KNIVES:
        tag = name.split()[0]
        if only and tag not in only:
            continue
        orig = open(src).read()
        if any(orig.count(o) != 1 for o, _ in cuts):
            print(f"{name}: KNIFE BROKEN (pattern not unique in {src})")
            fails.append(name); continue
        restore = lambda o=orig, s=src: open(s, "w").write(o)
        atexit.register(restore)
        try:
            t = orig
            for o, n in cuts:
                t = t.replace(o, n)
            open(src, "w").write(t)
            before = knife_guard.hashes()
            print(f"{name}: planted in {src}, rebuilding...")
            moved, after, rc = knife_guard.build(f"{TMP}/sf_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/strflt_probe.py zb",
               f"{TMP}/sf_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/sf_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: {' '.join(sorted(want)) or '(none)'}"
              f"   {'OK' if ok else '🔴 MISMATCH'}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/sf_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
