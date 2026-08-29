#!/usr/bin/env python3
r"""D-NGRAM10 K-N10A/K-N10B + S1 — one `req_lineno`, and BOTH halves of it.

  S1      STATIC per-site witness: 0 open-coded runs left, exactly 4 calls, and
          a positive control that every element of the pattern still EXISTS.
  K-N10A  retarget the BAIL (`stmt_error` -> `type_mismatch_error`). The three
          READABLE bail rows must move ERR 2 -> ERR 13.
  K-N10B  break the SUCCESS half: drop the last `inc hl`, so HL is left ON the
          line-number's high byte instead of past it. Every success row must
          move.

🔴 RETARGET, DO NOT NOP. D-N8ARM: a nop can be masked by a downstream guard and
then reports `moved 0`, which reads exactly like an arm with nothing to say. A
retarget cannot be masked. Both arms score against an EXPECTED ROW SET.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/interp.asm"
ROW = re.compile(r"^(?:g|b|n|ctl)\.")
ROW_ALL = ["g.goto", "g.gosub", "g.resume", "g.onerr",
           "b.goto", "b.gosub", "b.onerr", "b.resume",
           "n.goto0", "n.gotoud", "n.ifthen", "ctl.num", "ctl.str"]

KNIVES = [
    ("K-N10A retarget the bail", [
        ("""req_lineno:
                cp      LINENO_TOKEN
                jp      nz,stmt_error""",
         """req_lineno:
                cp      LINENO_TOKEN
                jp      nz,type_mismatch_error  ; K-N10A CUT (restored on exit)""")]),
    ("K-N10B drop the last cursor advance", [
        ("""                ld      b,(hl)
                inc     hl
                ret

; --- str_target_parse""",
         """                ld      b,(hl)
                nop                         ; K-N10B CUT (restored on exit)
                ret

; --- str_target_parse""")]),
]

# 🔴 I PREDICTED BOTH OF THESE WRONG, AND THE ARMS CAUGHT IT. Recorded rather
# than quietly corrected, because the corrections are the interesting part.
#
# K-N10A: I predicted `b.resume` would NOT move -- "it reads `<Syntax error>`
# UNTRAPPED, so the message is the same either way". Nonsense: an UNTRAPPED
# message is the error's TEXT, and the text follows the code. It moved
# `<Syntax error>` -> `<Type mismatch>` like the other three. So the honest
# expectation is ALL FOUR `b.*` rows -- every row whose reading the bail
# produces -- and the controls must stay put.
#
# K-N10B: I predicted the six success rows. **All thirteen moved**, every one to
# `ERR 2 AT 10`, controls included -- because LINE 10 OF EVERY FIXTURE IS
# `ON ERROR GOTO 900`, which now goes through this very helper. Break the cursor
# and the fixture cannot parse its own first line.
# 🎯 That is a fact about the coverage, not a defect in the arm: `req_lineno` is
# on the path of EVERY row in this suite. It makes K-N10B blunt but decisive.
# The PER-SITE success witnesses are the four `g.*` rows, each carrying a value
# only its own site can produce (jumped / 7 / resumed / ERR 11 AT 30).
EXPECT = {
    "K-N10A": {"b.goto", "b.gosub", "b.onerr", "b.resume"},
    "K-N10B": set(ROW_ALL),
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
    base = read_rows(f"{TMP}/n10_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/ngram10_probe.py zb "
              f"> {TMP}/n10_zb_base.out")
        return 2
    fails = []

    import ngram_sweep as NS
    st = NS.parse()
    PAT = ["cp lineno_token", "jp nz,stmt_error", "inc hl", "ld c,(hl)",
           "inc hl", "ld b,(hl)", "inc hl"]
    ins = [e for e in st if e[0] == "I"]
    open_coded = sum(1 for k in range(len(ins) - 6)
                     if [e[3] for e in ins[k:k + 7]] == PAT
                     and ins[k][1].startswith("basic/"))
    jumps = sum(1 for e in ins if e[3] == "call req_lineno")
    # D-N8ARM: EVERY element of PAT, not just the first -- a stale element in any
    # later position made one of seven of these arms vacuous.
    matcher_alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    ok = (open_coded == 1 and jumps == 4 and matcher_alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {open_coded} "
          f"open-coded run(s) left (want 1 = the helper body itself), {jumps} "
          f"call(s) to it (want 4), "
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
            moved, after, rc = knife_guard.build(f"{TMP}/n10k_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/ngram10_probe.py zb",
               f"{TMP}/n10k_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/n10k_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: {' '.join(sorted(want))}   "
              f"{'OK' if ok else '🔴 MISMATCH'}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/n10k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
