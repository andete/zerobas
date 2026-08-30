#!/usr/bin/env python3
r"""D-ARGOPEN — the shared LEFT$/RIGHT$/MID$ prologue, and its TWO frame pops.

  S1     STATIC: exactly 1 `call str_arg_snap` (the double pop in sas_decline is
         correct only while that is true), exactly 3 `call str_arg_open`, and 0
         open-coded copies of the run left.
  K-AO1  drop the SECOND `pop af` in sas_decline, i.e. put it back to the depth
         it had before this helper existed. The decline then returns INSIDE
         str_arg_open instead of out of the verb.
  K-AO2  drop all three callers' `nc,str_arg_empty` guards. 🎯 DISCRIMINATING:
         only the MALFORMED-CALL rows may move. A well-formed LEFT$/RIGHT$/MID$
         never returns CF clear, and a non-string first argument never returns at
         all (it takes sas_decline, K-AO1's site) -- so if a `.pend` or `.bad`
         row moved here, the two failure paths would not be the separate sites
         this design says they are.

🔴 THIS FILE'S FIRST VERSION KNIFED A DIFFERENT SHAPE AND MOVED ZERO ROWS, AND
THE ZERO WAS RIGHT. str_arg_open originally discarded its own return address
(`pop af`) and jumped to str_arg_empty in the verb's frame -- correct, and
UNWITNESSABLE: that bail's only outcome is a DEFERRED error, and every path that
reports one resets SP, so the frame damage is erased before any row reads
anything. The helper now returns CF clear instead and each caller raises at its
own depth: 6 bytes more, and a guard a row can see.
[[a-guard-witnessed-only-by-a-deferred-error]]
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/str-engine.asm"
ROW = re.compile(r"^[a-z]+\.")

KNIVES = [
    ("K-AO1 sas_decline back to one frame", [
        ("""                pop     af                  ; discard str_arg_snap's return address
                pop     af                  ; ...and str_arg_open's""",
         """                pop     af                  ; K-AO1 CUT (restored on exit)""")]),
    ("K-AO2 drop the callers' malformed-call guards", [
        ("""                jr      nc,str_arg_empty    ; malformed -> raise HERE, not one frame in
                push    bc                  ; save it across the numeric eval""",
         """                nop                         ; K-AO2 CUT (restored on exit)
                nop
                push    bc                  ; save it across the numeric eval"""),
        ("""                jr      nc,str_arg_empty    ; malformed -> raise HERE, not one frame in
                push    bc
""",
         """                nop                         ; K-AO2 CUT (restored on exit)
                nop
                push    bc
"""),
        ("""                jp      nc,str_arg_empty    ; malformed -> raise HERE, not one frame in""",
         """                nop                         ; K-AO2 CUT (restored on exit)
                nop
                nop""")]),
]

EXPECT = {
    # every row whose first argument is not a string: the three `.bad` type
    # mismatches and the five pending-fault declines.
    # every row whose first argument is not a string: three type mismatches and
    # five pending-fault declines.
    # 🔴 AND I "CORRECTED" THIS TO TWO ROWS ONCE, FROM A NUMBER TAKEN ON A
    # SUPERSEDED BUILD. The first run measured 2 -- but that build still had
    # str_arg_open discarding its own return address, so TWO frame errors were
    # cancelling and six rows stayed put. Re-measured on the shipping shape it is
    # 8, which is what the original prediction said. A measurement is scoped to
    # the tree it was taken on; fitting a prediction to one from another tree is
    # how a ranked candidate rots.
    "K-AO1": {"s.left.bad", "s.right.bad", "s.mid.bad",
              "s.left.pend", "s.right.pend", "s.mid.pend",
              "s.left.pexp", "s.mid.pexp"},
    # only the malformed calls.
    # 🔴 PREDICTED FOUR AND MEASURED ONE, and the three that did not move are a
    # finding about this whole family rather than about the cut. With the guard
    # gone the verb runs on and evaluates the malformed tail -- and `LEFT$("AB")`,
    # `MID$("AB")` and `RIGHT$()` all leave the cursor on a `)`, whose evaluation
    # raises the SAME deferred ERR 2 the guard would have raised. The answer
    # converges no matter which path produced it.
    # 🎯 `LEFT$"AB"` is the one row that separates them, because with no `(` the
    # cursor is on a STRING literal, which evaluates to something else entirely.
    # ONE witnessed row is what the 6 bytes of the CF-return shape buy over the
    # `pop af` shape's ZERO -- and that is still the right trade, because a guard
    # no row can see is not a guard this project ships.
    # [[a-guard-witnessed-only-by-a-deferred-error]]
    "K-AO2": {"s.left.nopar"},
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
    base = read_rows(f"{TMP}/argopen_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/ngram8_probe.py zb "
              f"> {TMP}/argopen_zb_base.out")
        return 2
    fails = []
    src = open(SRC).read()
    snap = src.count("call    str_arg_snap")
    opens = src.count("call    str_arg_open")
    run = src.count("""                cp      ')'
                jr      z,str_arg_empty""") + src.count("""                cp      ')'
                jp      z,str_arg_empty""")
    # 🔴 COUNT INSTRUCTIONS, NOT TEXT. The first version of this line was
    # `src.count("nc,str_arg_empty")` and reported FOUR -- the fourth being the
    # COMMENT in str_arg_open's own header that documents the guard. An
    # instrument that counts the prose written to explain it is the same fault
    # as one that hands back a plausible table from an input it misread, and it
    # is the SECOND time in one session (the FOUTBUF writer grep listed
    # sub/strheap.asm for a comment).
    # [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]
    guards = len(re.findall(r"^\s+(?:jr|jp)\s+nc,str_arg_empty", src, re.M))
    ok = (snap == 1 and opens == 3 and run == 0 and guards == 3)
    print(f"{'PASS' if ok else 'FAIL'}  S1 {snap} call(s) to str_arg_snap (want 1 -- "
          f"the double pop is correct ONLY at one), {opens} to str_arg_open (want 3), "
          f"{run} open-coded copies left (want 0), {guards} caller guard(s) "
          f"`nc,str_arg_empty` INSTRUCTION(S) (want 3 -- one per call site, at "
          f"the CALLER's depth; a text count reads 4, the fourth being a comment)")
    if not ok:
        fails.append("S1")
    print(f"\nbaseline: {len(base)} row(s)\n")
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
            moved, after, rc = knife_guard.build(f"{TMP}/ao_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/ngram8_probe.py zb",
               f"{TMP}/ao_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/ao_{tag}.out")
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
    sh("make repack-machine", f"{TMP}/ao_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
