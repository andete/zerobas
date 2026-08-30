#!/usr/bin/env python3
r"""D-RECLEN2 K-RL2 — the FACE of an out-of-range `LEN=`.

  K-RL2  send the reject back to `oo_fail_syn` -> the out-of-range rows go from
         `Illegal function call` to `Syntax error`. Only those three move: the
         ACCEPTED lengths never reach the reject at all.

🔴 THERE WAS A K-RL1, AND IT IS GONE BECAUSE THE CLAIM IT ARMED WAS WITHDRAWN.
It cut the power-of-two test, and scored 2/2 while the domain was widened. The
widening was then REVERTED: `mul_reclen` is a shift loop, so r=100 computes *64,
and `fat_rand_put`'s overlay would `ldir` 88 bytes past FWBUF for record 6.
An arm for a claim that no longer ships is not an arm.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/files.asm"
ROW = re.compile(r"^m\.")
KNIVES = [
    ("K-RL2 out-of-range back to Syntax error", [
        ("""                jp      c,oo_fail_ifc       ; D-RECLEN2: out-of-range record size is""",
         """                jp      c,oo_fail_syn       ; K-RL2 CUT (restored on exit)""")]),
]
EXPECT = {
    # only the out-of-range rows, and only their FACE. The accepted lengths
    # (1/128/256) never reach the reject; the non-tiling ones (100/255) are
    # rejected by the power-of-two branch and change face WITH this cut too --
    # which is why they are listed: the cut moves every row that reaches
    # oo_fail_ifc, and that is five, not three.
    "K-RL2": {"m.open0", "m.open257", "m.open512",
              "m.open100", "m.open255"},
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
            rows[p[0]] = " ".join(p[1:]).replace(" SAME", "").replace(" DIFF", "").strip()
    return rows


def main():
    base = read_rows(f"{TMP}/reclen2_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/reclen2_probe.py zb "
              f"> {TMP}/reclen2_zb_base.out")
        return 2
    print(f"baseline: {len(base)} row(s)\n")
    fails = []
    only = set(sys.argv[1:])
    for name, cuts in KNIVES:
        tag = name.split()[0]
        if only and tag not in only:
            continue
        orig = open(SRC).read()
        if any(orig.count(o) != 1 for o, _ in cuts):
            print(f"{name}: KNIFE BROKEN"); fails.append(name); continue
        restore = lambda o=orig: open(SRC, "w").write(o)
        atexit.register(restore)
        try:
            t = orig
            for o, n in cuts:
                t = t.replace(o, n)
            open(SRC, "w").write(t)
            before = knife_guard.hashes()
            print(f"{name}: planted, rebuilding...")
            moved, after, rc = knife_guard.build(f"{TMP}/rl2_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/reclen2_probe.py zb",
               f"{TMP}/rl2_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/rl2_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: {' '.join(sorted(want))}"
              f"   {'OK' if ok else '🔴 MISMATCH'}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/rl2_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
