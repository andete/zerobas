#!/usr/bin/env python3
r"""D-NGRAM14 / D-EXPNEG — arms for the shared tail and for the underflow alias.

  S1      STATIC: 0 open-coded `ld a,8 / ld (FACTYP),a / jp flt_to_int16` runs
          left, exactly 2 `jp fac_dbl_int16` reachers plus the fallthrough, and
          `fexp_underflow` is an EQU rather than a body.
  K-N14A  the shared tail publishes the WRONG TYPE (`ld a,8` -> `ld a,4`).
          PREDICTED: every row whose answer is a VALUE moves -- the four
          dispatch verbs, `^`, both round_and_finalize rows, and the two EXP
          rows that return a number. The rows whose answer is an ERROR do NOT:
          they never reach the tail. Controls hold.

🔴 K-N14B IS GONE, AND ITS ABSENCE IS PART OF THE RECORD. It cut the
`penderr_set` out of `fexp_overflow` to witness D-EXPNEG's underflow fold, and
it scored EXACTLY -- three rows, the right three. D-EXPNEG was then reverted in
full: the deviation it "fixed" is deliberate and adjudicated
(docs/spec-basic-mathpack-slice2.md §12.9), and `math-acceptance` encodes that
decision. An arm for a change that no longer ships is not an arm, so it was
deleted rather than left to pass against nothing.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP = "/tmp/zerobas"
EXPR, FARITH, FEXP = "basic/expr.asm", "basic/float-arith.asm", "sub/fp_exp.asm"
ROW = re.compile(r"^([rxc]\w*\.\S+)\s+(.*?)\s+(SAME|DIFF)\s*$")
PROBE = "python3 scratchpad/ngram14_probe.py zb"

KNIVES = [
    ("K-N14A the shared tail publishes the wrong type", FARITH, [
        ("""fac_dbl_int16:
                ld      a,8""",
         """fac_dbl_int16:
                ld      a,4                 ; K-N14A CUT (restored on exit)""")]),
]

EXPECT = {
    # 🔴 I PREDICTED NINE AND FOUR MOVED, and the four are exactly the rows
    # whose answer needs MORE THAN SIX SIGNIFICANT DIGITS. `SQR(9)`=3,
    # `LOG(1)`=0, `EXP(0)`=1, `2^10`=1024 and `1.5*3`=4.5 render identically
    # whether FAC is read as single or double, so a WRONG-TYPE knife is
    # invisible on them. The cut is real at all nine sites; the ROWS can only
    # see it where the rendering depends on the type.
    "K-N14A": {"r.atn", "r.round2", "x.m100", "x.p100"},
}

TAIL = ["ld a,8", "ld (factyp),a", "jp flt_to_int16"]


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
    p = f"{TMP}/n14_{tag}.out"
    sh(f"ZEROBAS_REFCACHE=0 {PROBE}", p)
    rows = read_rows(p)
    return rows, sorted(set(need or ()) - set(rows))


def main():
    fails = []
    import ngram_sweep as NS
    ins = [e for e in NS.parse() if e[0] == "I"]
    n = len(TAIL)
    occ = sum(1 for k in range(len(ins) - n + 1)
              if [e[3] for e in ins[k:k + n]] == TAIL
              and ins[k][1].startswith("basic/"))
    # the body itself IS one such run, so 1 is the honest expectation -- 0 would
    # mean the body had gone missing.
    reach = sum(1 for e in ins if e[3] == "jp fac_dbl_int16")
    # 🔴 THIS ARM ONCE ASSERTED A FIX THAT WAS REVERTED. D-EXPNEG folded
    # `fexp_underflow` into `fexp_overflow` to match the references, and
    # `math-acceptance` refused it -- the divergence is DELIBERATE
    # (docs/spec-basic-mathpack-slice2.md §12.9). What the arm guards now is
    # that the silent underflow tail is still THERE, which is the shipped
    # behaviour, and that its two callers still reach it.
    src = open(FEXP).read()
    und = len(re.findall(r"^\s+jp\s+(?:z,)?fexp_underflow\b", src, re.M))
    alias = (und == 2 and re.search(r"^fexp_underflow:", src, re.M) is not None)
    ok = (occ == 1 and reach == 3 and alias)
    print(f"{'PASS' if ok else 'FAIL'}  S1 one tail, three reachers: {occ} run(s) "
          f"in basic/ (want 1 -- the BODY is one, and 0 would mean it vanished), "
          f"{reach} `jp` reacher(s) (want 3; the fourth arrives by fallthrough), "
          f"silent underflow tail intact: {und} `fexp_underflow` caller(s) "
          f"(want 2) and the label {'present' if alias else '🔴 MISSING'} "
          f"-- the DELIBERATE §12.9 deviation, not a defect")
    if not ok:
        fails.append("S1")

    base, _ = capture("kbase")
    if not base:
        print("🔴 NO BASELINE ROWS READ BACK")
        return 2
    print(f"\nbaseline: {len(base)} row(s)\n")

    for name, src, cuts in KNIVES:
        tag = name.split()[0]
        orig = open(src).read()
        if any(orig.count(o) != 1 for o, _ in cuts):
            print(f"{name}: KNIFE BROKEN (pattern not unique in {src})")
            fails.append(name)
            continue
        restore = lambda o=orig, f=src: open(f, "w").write(o)
        atexit.register(restore)
        try:
            t = orig
            for o, nw in cuts:
                t = t.replace(o, nw)
            open(src, "w").write(t)
            before = knife_guard.hashes()
            print(f"{name}: planted in {src}, rebuilding...")
            moved, after, rc = knife_guard.build(f"{TMP}/n14k_{tag}_build.out",
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
              f"\n  want  {len(want)}: {' '.join(sorted(want))}"
              f"   {'OK' if good else '🔴 MISMATCH'}")
        if not good:
            fails.append(name)
        print()

    sh("make repack-machine", f"{TMP}/n14k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
