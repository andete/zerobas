#!/usr/bin/env python3
r"""D-NGRAM11 K-N11A/K-N11B + S1 — one `str_eval_next`, and its TAIL.

  S1      STATIC: 0 open-coded runs left, exactly 6 calls, every pattern element
          alive (the arm expects ZERO, so it cannot do without that control).
  K-N11A  drop the `inc hl`, so the delimiter is never consumed and `str_eval`
          is handed the '=' / ',' itself. Every SUCCESS row must move; the
          decline rows are already declining and cannot.
  K-N11B  turn the TAIL JUMP into `call` + `ret`. **Asserted to move ZERO**, and
          the zero is the point: it is what says the tail jump's value is a
          STRUCTURAL guarantee (identical depth at str_eval, by construction)
          plus one saved byte -- NOT a measured hazard at these six sites. Saying
          so with an arm beats claiming it in a comment.
          🔴 A DESIGNED NO-OP THAT REPORTS "moved 0" AND IS READ AS AN ARM IS THE
          D-POPRAISE MISTAKE. This one asserts its zero.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/interp.asm"
ROW = re.compile(r"^(?:g|b|ctl)\.")

KNIVES = [
    ("K-N11A drop the delimiter step", [
        ("""str_eval_next:
                inc     hl                  ; past the delimiter""",
         """str_eval_next:
                nop                         ; K-N11A CUT (restored on exit)""")]),
    ("K-N11B tail jump -> call + ret", [
        ("""                jp      str_eval            ; TAIL jump -- see the note above""",
         """                call    str_eval            ; K-N11B CUT (restored on exit)
                ret""")]),
]

# 🔴 I PREDICTED SEVEN ROWS FOR K-N11A AND TWELVE MOVED. Recorded, because both
# surprises were real:
#   * The `b.*` rows for LET / LSET / MID$ move too -- 13 (or 2) -> **24**. With
#     the delimiter unconsumed str_eval is handed the '=' itself, so the decline
#     reason changes from "there is a non-string here" to "there is NOTHING
#     here", which is Missing operand. I had assumed a row already declining
#     could not move; the CODE it declines with is part of the reading.
#   * `ctl.cat` moved -- because its own setup was two `LET A$=` statements, one
#     of the six sites. It was never a control. Renamed `g.letcat`, and a real
#     control (`ctl.lit`, literals only) put in its place.
# b.instr / b.instrp do NOT move: their ERR 2 comes from an earlier stage that
# this cut does not reach. ctl.num and ctl.lit do not move -- the actual controls.
EXPECT = {
    "K-N11A": {"g.letary", "g.lset", "g.rset", "g.let", "g.mid",
               "g.instr", "g.instrp", "g.letcat",
               "b.let", "b.letary", "b.lset", "b.mid"},
    # MASKED BY DESIGN, asserted: str_eval returns normally, so an extra frame
    # that is popped before the caller sees anything changes no reading.
    "K-N11B": set(),
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
    base = read_rows(f"{TMP}/n11_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/ngram11_probe.py zb "
              f"> {TMP}/n11_zb_base.out")
        return 2
    fails = []

    import ngram_sweep as NS
    st = NS.parse()
    PAT = ["inc hl", "call skip_spaces", "call str_eval"]
    ins = [e for e in st if e[0] == "I"]
    open_coded = sum(1 for k in range(len(ins) - 2)
                     if [e[3] for e in ins[k:k + 3]] == PAT
                     and ins[k][1].startswith("basic/"))
    jumps = sum(1 for e in ins if e[3] == "call str_eval_next")
    # 🔴 EXPECTED ZERO -> the matcher control is not optional (D-N8ARM): every
    # element, not just the first. The helper's own tail is `jp str_eval`, so the
    # body does NOT match PAT and 0 is the honest expectation here.
    matcher_alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    ok = (open_coded == 0 and jumps == 6 and matcher_alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {open_coded} "
          f"open-coded run(s) left (want 0 -- the body's tail is a `jp`, so it "
          f"does not match), {jumps} call(s) to it (want 6), "
          f"matcher{'' if matcher_alive else ' 🔴 STALE: ' + str(stale)} alive")
    if not ok:
        fails.append("S1")
    print(f"\nbaseline: {len(base)} row(s)\n")

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
            moved, after, rc = knife_guard.build(f"{TMP}/n11k_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/ngram11_probe.py zb",
               f"{TMP}/n11k_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/n11k_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: "
              f"{' '.join(sorted(want)) or '(none -- MASKED BY DESIGN, reason in the docstring)'}"
              f"   {'OK' if ok else '🔴 MISMATCH'}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/n11k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
