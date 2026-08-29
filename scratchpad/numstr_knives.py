#!/usr/bin/env python3
r"""D-NUMSTR K-NS1/K-NS2 — the site is reached, and the CODE is chosen.

  K-NS1  remove the string test entirely. All six rows must return to ERR 24 --
         including `s.fn` (`5+LEFT$("AB",1)`), which is the interesting one:
         the cut is nowhere near ev_ff_strnum, and that row moves anyway,
         because its D-LEFTTM arm evaluates the argument numerically and THAT
         inner eval is what lands here.
  K-NS2  keep the test, change the CODE (`ev_f_tmm` -> `ev_f_empty`). The same
         six move, to ERR 2. Two arms over one row set on purpose: K-NS1 says
         the site is REACHED, K-NS2 says 13 was CHOSEN rather than inherited.

🔴 AND WHAT MUST NOT MOVE IS HALF THE POINT. D-MISSOP's own statement-argument
slots (`k.poke`, `k.locate`) answer 24 on all three references and are reached
through this very label; if either moves, the fix has taken the missing-operand
rule with it.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/expr.asm"
ROW = re.compile(r"^(?:s|m|k|o|g|ctl)\.")

KNIVES = [
    ("K-NS1 remove the string test", [
        ("""                cp      '"'
                jr      z,ev_f_tmm          ; -> ERR 13
                ld      e,FPERR_MISSOP""",
         """                nop                         ; K-NS1 CUT (restored on exit)
                nop
                nop
                nop
                ld      e,FPERR_MISSOP""")]),
    ("K-NS2 same test, different code", [
        ("""                jr      z,ev_f_tmm          ; -> ERR 13""",
         """                jr      z,ev_f_empty        ; K-NS2 CUT (restored on exit)""")]),
]

STRING_ROWS = {"s.addlit", "s.sublit", "s.mullit", "s.divlit", "s.unary", "s.fn"}
EXPECT = {"K-NS1": STRING_ROWS, "K-NS2": STRING_ROWS}


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
    base = read_rows(f"{TMP}/ns_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/numstr_probe.py zb "
              f"> {TMP}/ns_zb_base.out")
        return 2
    fails = []
    print(f"baseline: {len(base)} row(s)\n")

    for name, cuts in KNIVES:
        tag = name.split()[0]
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
            moved, after, rc = knife_guard.build(f"{TMP}/nsk_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/numstr_probe.py zb",
               f"{TMP}/nsk_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/nsk_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: {' '.join(sorted(want))}   "
              f"{'OK' if ok else '🔴 MISMATCH'}")
        for r in ("s.fn", "k.poke", "k.locate"):
            print(f"    {r}: {base.get(r)!r} -> {cut.get(r)!r}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/nsk_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
