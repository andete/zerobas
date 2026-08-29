#!/usr/bin/env python3
r"""D-STRTM K-ST1/K-ST2 — the CODE and the ORDER, one arm each.

  K-ST1  answer a syntax error instead (`ev_f_tmm` -> `ev_f_empty`). The three
         clean non-string rows must return to ERR 2. `o.len` must NOT move: its
         operand's own division-by-zero is already armed and outranks either.
  K-ST2  🎯 THE ORDER ARM: drop the `call eval`, so the mismatch is armed without
         looking at the operand -- the shape this slice fixed, and the same
         mistake D-LEFTTM's K-LT2 and D-INSTRTM's K-IT2 pin in two other verbs.
         ONLY `o.len` moves, 11 -> 13; the three clean rows cannot tell.

🔴 A ROW SET OF ONLY THE CLEAN ROWS WOULD SCORE THE UNFIXED CODE GREEN. That is
the third time today, so it is the point of the file rather than a footnote.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/str-engine.asm"
ROW = re.compile(r"^(?:t|o|g|ctl)\.")

KNIVES = [
    ("K-ST1 syntax error instead of type mismatch", [
        ("                jp      ev_f_tmm            ; -> ERR 13, unless the operand beat us",
         "                jp      ev_f_empty          ; K-ST1 CUT (restored on exit)")]),
    ("K-ST2 arm the mismatch without evaluating", [
        ("""                call    eval                ; the operand, numerically -- it arms its
                                            ; OWN fault first if it has one
                jp      ev_f_tmm            ; -> ERR 13, unless the operand beat us""",
         """                nop                         ; K-ST2 CUT (restored on exit)
                nop
                nop
                jp      ev_f_tmm""")]),
]

EXPECT = {
    "K-ST1": {"t.len", "t.asc", "t.val"},
    "K-ST2": {"o.len"},
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
    base = read_rows(f"{TMP}/st_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/strtm_probe.py zb "
              f"> {TMP}/st_zb_base.out")
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
            moved, after, rc = knife_guard.build(f"{TMP}/stk_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/strtm_probe.py zb",
               f"{TMP}/stk_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/stk_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: {' '.join(sorted(want))}   "
              f"{'OK' if ok else '🔴 MISMATCH'}")
        for r in sorted(want):
            print(f"    {r}: {base.get(r)!r} -> {cut.get(r)!r}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/stk_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
