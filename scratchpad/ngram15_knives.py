#!/usr/bin/env python3
r"""D-NGRAM15 K-N15A/K-N15B + S1 — one `str_eval_ix`, and what its TAIL is worth.

  S1      STATIC: 0 open-coded runs left, exactly 7 calls, matcher alive.
  K-N15A  `pop hl` -> `pop de`, so the cursor never reaches HL and `str_eval`
          parses from whatever HL held. The stack stays BALANCED on purpose --
          cutting the `pop` outright would leave `push ix` unmatched and
          `str_eval`'s `ret` would jump to the cursor VALUE, which crashes the
          machine rather than moving rows. A knife has to break the SUBJECT, not
          the harness.

🔴 A THIRD ARM WAS BUILT, RUN, AND DISCARDED -- K-N15C, which forced CF SET on
the way out so that no site would take its `jr nc` arm. It was meant to reach the
half K-N15A cannot: a garbage cursor still DECLINES, so rows whose answer IS a
decline (`b.cvi`, `b.len`, `g.frenum`, `g.relnum`) hold under K-N15A --
**declining for the wrong reason is indistinguishable from declining for the
right one**. K-N15C moved **all fourteen rows, both CONTROLS included**. A knife
that moves the controls has broken the machine, not the subject: with CF forced,
every site proceeds on a STRPTR pointing at nothing and the interpreter does not
survive to answer the next row. It is deleted rather than kept with an
"everything moves" expectation, which would assert nothing.
➡️ So the decline half is covered by the ROWS (they agree with both references)
and by K-N15B's asserted zero -- the frame question D-NGRAM8 actually got wrong
-- and NOT by a cut of its own. Said plainly rather than papered over.
  K-N15B  tail `jp str_eval` -> `call str_eval` + `ret`. **Asserted to move
          ZERO**, and the zero is the claim: `str_eval` returns normally, so the
          extra frame is popped before any of the seven callers sees it. The tail
          jump's value here is one saved byte plus a STRUCTURAL guarantee for the
          next caller anyone adds -- not a measured hazard at these seven sites.
          🔴 A DESIGNED NO-OP THAT REPORTS "moved 0" AND IS READ AS AN ARM IS THE
          D-POPRAISE MISTAKE. This one asserts its zero.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/strvar.asm"
ROW = re.compile(r"^([gbc]\w*\.\S+)\s+(.*?)\s+(SAME|DIFF|NO-ORACLE)\s*$")
PROBE = "python3 scratchpad/ngram15_probe.py zb"

KNIVES = [
    ("K-N15A the cursor never reaches HL", [
        ("""                push    ix
                pop     hl                  ; HL = cursor""",
         """                push    ix
                pop     de                  ; K-N15A CUT (restored on exit)""")]),
    ("K-N15B tail jump -> call + ret", [
        ("""                jp      str_eval            ; TAIL -- CF, HL and STRPTR go to OUR caller""",
         """                call    str_eval            ; K-N15B CUT (restored on exit)
                ret""")]),
]

EXPECT = {
    # 🔴 I PREDICTED TWELVE AND EIGHT MOVED, AND THE FOUR THAT HELD ARE THE
    # FINDING: `b.cvi`, `b.len`, `g.frenum`, `g.relnum` are all rows whose
    # expected answer is "str_eval DECLINED". A garbage cursor declines too --
    # **declining for the wrong reason is indistinguishable from declining for
    # the right one** -- so this cut cannot move them. They are real coverage
    # (they agree with the references) but they are NOT witnessed by THIS knife.
    # K-N15C below is the arm that reaches them.
    "K-N15A": {"g.rel", "g.relvar", "g.cvi", "g.fre", "g.len", "g.instr",
               "g.ersrhs", "b.instr"},
    # MASKED BY DESIGN, asserted -- see the docstring.
    "K-N15B": set(),
}

PAT = ["push ix", "pop hl", "call str_eval"]


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
    p = f"{TMP}/n15_{tag}.out"
    sh(f"ZEROBAS_REFCACHE=0 {PROBE}", p)
    rows = read_rows(p)
    return rows, sorted(set(need or ()) - set(rows))


def main():
    fails = []
    import ngram_sweep as NS
    ins = [e for e in NS.parse() if e[0] == "I"]
    n = len(PAT)
    occ = sum(1 for k in range(len(ins) - n + 1)
              if [e[3] for e in ins[k:k + n]] == PAT
              and ins[k][1].startswith("basic/"))
    calls = sum(1 for e in ins if e[3] == "call str_eval_ix")
    # 🔴 EXPECTED ZERO, so the matcher needs its own control: the helper's body
    # ends `jp str_eval`, not `call`, so it does NOT match PAT either.
    alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    ok = (occ == 0 and calls == 7 and alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {occ} open-coded "
          f"run(s) left (want 0 -- the body's tail is a `jp`, so it does not "
          f"match), {calls} call(s) (want 7), "
          f"matcher{'' if alive else ' 🔴 STALE: ' + str(stale)} alive")
    if not ok:
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
            moved, after, rc = knife_guard.build(f"{TMP}/n15k_{tag}_build.out",
                                                 before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED")
                fails.append(name)
                continue
            if not moved:
                fails.append(name)
                continue
            cut, missing = capture(f"k_{tag}", need=base)
        finally:
            restore()
            atexit.unregister(restore)
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name)
            continue
        if missing:
            print(f"  🔴 {len(missing)} baseline row(s) NOT PRINTED "
                  f"({' '.join(missing)}) — an unread row is not a moved row")
            fails.append(name)
            continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        good = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: "
              f"{' '.join(sorted(want)) or '(none -- MASKED BY DESIGN, reason in the docstring)'}"
              f"   {'OK' if good else '🔴 MISMATCH'}")
        if not good:
            fails.append(name)
        print()

    sh("make repack-machine", f"{TMP}/n15k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
