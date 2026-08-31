#!/usr/bin/env python3
r"""D-CVITM K-CV1/K-CV2/K-CV3 — one arm per change, each isolating its own rows.

The slice made THREE distinct corrections inside `ev_ff_cvi`, and they are
separable, so each gets a cut that must move ITS rows and no others:

  K-CV1  the non-string decline goes back to `ev_f_empty` (Syntax error).
         PREDICTED: `a.num`, `a.numvar`. 🎯 `b.nested` must HOLD -- it is the row
         that says FIRST-ERROR-WINS is doing the separating, not the branch.
  K-CV2  drop the 2-byte length guard.
         PREDICTED: `g.short` alone.
  K-CV3  drop the empty-argument test.
         PREDICTED: `c.empty` alone -- it falls through to the type error, which
         is the mistake the first cut of this slice actually made.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/expr.asm"
ROW = re.compile(r"^([abcgm]\w*\.\S+|ctl\.\S+)\s+(.*?)\s+(SAME|DIFF)\s*$")
PROBE = "python3 scratchpad/cvitm_probe.py zb"

KNIVES = [
    ("K-CV1 non-string decline -> Syntax error again", [
        ("                jp      nc,ev_f_tmm",
         "                jp      nc,ev_f_empty       ; K-CV1 CUT (restored on exit)")]),
    ("K-CV2 drop the 2-byte length guard", [
        ("""                ld      a,(hl)              ; descriptor length
                cp      2
                jp      c,ev_f_ifc          ; fewer than 2 bytes -> deferred ERR 5""",
         """                nop                         ; K-CV2 CUT (restored on exit)
                nop
                nop
                nop
                nop
                nop""")]),
    ("K-CV3 drop the empty-argument test", [
        ("""                cp      ')'
                jp      z,ev_f_empty        ; CVI() -> deferred Syntax error""",
         """                nop                         ; K-CV3 CUT (restored on exit)
                nop
                nop
                nop
                nop""")]),
]

EXPECT = {
    "K-CV1": {"a.num", "a.numvar"},
    "K-CV2": {"g.short"},
    "K-CV3": {"c.empty"},
}


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh,
                               stderr=subprocess.STDOUT)


def read_rows(path):
    rows = {}
    if not os.path.exists(path):
        return rows
    for line in open(path, errors="replace"):
        m = ROW.match(line.rstrip())
        if m:
            rows[m.group(1)] = m.group(2).strip()
    return rows


def capture(tag, need=None):
    p = f"{TMP}/cvi_{tag}.out"
    sh(f"ZEROBAS_REFCACHE=0 {PROBE}", p)
    rows = read_rows(p)
    return rows, sorted(set(need or ()) - set(rows))


def main():
    fails = []
    src = open(SRC).read()
    # S1: all three corrections present, each exactly once.
    bits = {
        "the non-string decline defers TYPE MISMATCH": "jp      nc,ev_f_tmm",
        "the 2-byte length guard": "jp      c,ev_f_ifc          ; fewer than 2 bytes",
        "the empty-argument test": "jp      z,ev_f_empty        ; CVI() -> deferred",
    }
    missing = [k for k, v in bits.items() if src.count(v) != 1]
    print(f"{'PASS' if not missing else 'FAIL'}  S1 all three corrections present "
          f"exactly once{'' if not missing else ' 🔴 MISSING: ' + str(missing)}")
    if missing:
        fails.append("S1")

    base, _ = capture("kbase")
    if not base:
        print("🔴 NO BASELINE ROWS READ BACK")
        return 2
    print(f"\nbaseline: {len(base)} row(s)\n")

    for name, cuts in KNIVES:
        tag = name.split()[0]
        orig = open(SRC).read()
        if any(orig.count(o) != 1 for o, _ in cuts):
            print(f"{name}: KNIFE BROKEN (pattern not unique)")
            fails.append(name)
            continue
        restore = lambda o=orig: open(SRC, "w").write(o)
        atexit.register(restore)
        try:
            t = orig
            for o, nw in cuts:
                t = t.replace(o, nw)
            open(SRC, "w").write(t)
            before = knife_guard.hashes()
            print(f"{name}: planted, rebuilding...")
            moved, after, rc = knife_guard.build(f"{TMP}/cvik_{tag}_build.out",
                                                 before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED")
                fails.append(name)
                continue
            if not moved:
                fails.append(name)
                continue
            cut, miss = capture(f"k_{tag}", need=base)
        finally:
            restore()
            atexit.unregister(restore)
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name)
            continue
        if miss:
            print(f"  🔴 {len(miss)} baseline row(s) NOT PRINTED ({' '.join(miss)})"
                  f" — an unread row is not a moved row")
            fails.append(name)
            continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        good = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: {' '.join(sorted(want))}"
              f"   {'OK' if good else '🔴 MISMATCH'}")
        if not good:
            fails.append(name)
        print()

    sh("make repack-machine", f"{TMP}/cvik_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
