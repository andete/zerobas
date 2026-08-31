#!/usr/bin/env python3
r"""D-NGRAM18b — the two finer `req_gosub` cuts, scored against a probe that
makes the trap FIRE.

D-NGRAM18 built two cuts and neither moved a row, so it filed the gap as needing
"an input fixture this probe does not build". 🔴 THAT WAS WRONG ABOUT THE TREE:
`probes/basic/basic_probe_stop_trap.py` already presses Ctrl-STOP through
openMSX's key matrix, and there are five trap probes beside it. The fixture
existed; my probe simply was not it.

  K-G1b  drop the `inc hl`, so GOSUB is matched but NOT consumed.
         PREDICTED: `ON STOP GOSUB <line>` then finds no line number at the GOSUB
         token and SILENTLY CLEARS the handler, so the trap does not fire --
         every row that asserts a FIRING moves.
  K-G2b  `jp nz,trap_syntax` -> `ret nz`, so a MISSING GOSUB is accepted.
         PREDICTED: the firing rows all supply GOSUB, so they should HOLD; only a
         row that OMITS it could move, and whether this probe has one is the
         question the run answers.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/interp.asm"
ROW = re.compile(r"^(PASS|FAIL)\s+\[(ref|zb )\]\s+(\S+)\s+(.*)$")
PROBE = "python3 probes/basic/basic_probe_stop_trap.py --trials 1"

KNIVES = [
    ("K-G1b GOSUB matched but not consumed", [
        ("""                jp      nz,trap_syntax      ; no GOSUB: malformed trap statement
                inc     hl                  ; consume it""",
         """                jp      nz,trap_syntax      ; no GOSUB: malformed trap statement
                nop                         ; K-G1b CUT (restored on exit)""")]),
    ("K-G2b a missing GOSUB is accepted", [
        ("                jp      nz,trap_syntax      ; no GOSUB: malformed trap statement",
         "                ret     nz                  ; K-G2b CUT (restored on exit)\n"
         "                nop\n"
         "                nop")]),
]


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh,
                               stderr=subprocess.STDOUT)


def read_rows(path):
    """(side,label) -> verdict. Only the `zb` side: the reference cannot move."""
    rows = {}
    if not os.path.exists(path):
        return rows
    for line in open(path, errors="replace"):
        m = ROW.match(line.rstrip())
        if m and m.group(2).strip() == "zb":
            rows[m.group(3)] = m.group(1)
    return rows


def capture(tag, need=None):
    p = f"{TMP}/st_{tag}.out"
    sh(f"ZEROBAS_REFCACHE=0 {PROBE}", p)
    rows = read_rows(p)
    return rows, sorted(set(need or ()) - set(rows))


def main():
    fails = []
    base, _ = capture("kbase")
    if not base:
        print("🔴 NO BASELINE ROWS READ BACK")
        return 2
    bad = sorted(r for r, v in base.items() if v != "PASS")
    print(f"baseline: {len(base)} zb row(s), "
          f"{'all PASS' if not bad else '🔴 already failing: ' + str(bad)}\n")
    if bad:
        fails.append("baseline")

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
            moved, after, rc = knife_guard.build(f"{TMP}/stk_{tag}_build.out",
                                                 before)
            print(knife_guard.report(tag, moved, before, after))
            if rc or not moved:
                print(f"{name}: BUILD FAILED / INERT")
                fails.append(name)
                continue
            cut, miss = capture(f"k_{tag}", need=base)
        finally:
            restore()
            atexit.unregister(restore)
        if not cut:
            print("  🔴 NO ROWS READ BACK")
            fails.append(name)
            continue
        if miss:
            print(f"  🔴 {len(miss)} baseline row(s) NOT PRINTED ({' '.join(miss)})")
            fails.append(name)
            continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}")
        print()

    sh("make repack-machine", f"{TMP}/stk_restore.out")
    print("=" * 68)
    print("VERDICT:", "ran" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
