#!/usr/bin/env python3
r"""D-NGRAM19 K-A1/K-A2 + S1 — the two answers `evmc_arg_int` returns.

  S1    STATIC: 0 open-coded runs left, exactly 4 calls, matcher alive.
  K-A1  `scf` -> `or a`, so a MALFORMED argument no longer reports CARRY and the
        caller's `ret c` does not fire. PREDICTED: the four `b.*` rows move; the
        int/float rows HOLD, because a well-formed argument never reaches it.
  K-A2  `cp 2` -> `cp 4`, so the "already an int" answer is wrong for every
        caller. PREDICTED: the rows whose argument IS an int move (`i.*` and
        `x.abs8k`), and the float rows HOLD -- each verb branches on that flag
        differently, which is exactly why the run could not become a plain
        subroutine.
🎯 The two arms cut the two ANSWERS the helper publishes -- carry and zero -- and
each must leave the other's rows alone.
⚠️ Both cuts are size-neutral: a byte-count change can push a `jr` out of range,
the build then fails, the ROM is unchanged and knife_guard calls the knife INERT.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/expr.asm"
ROW = re.compile(r"^([ifbxc]\w*\.\S+)\s+(.*?)\s+(SAME|DIFF)\s*$")
PROBE = "python3 scratchpad/argint_probe.py zb"

KNIVES = [
    # 🔴 K-A1 WAS `scf` -> `or a` (a malformed argument stops reporting carry)
    # and it moved ZERO rows: `ev_mc_arg_checked` has ALREADY armed the deferred
    # D-F2-4 error, and `check_expr_errors` reports it at the statement boundary
    # whether or not the verb returned early. The `ret c` decides whether the
    # verb's BODY runs on garbage, not what is printed -- and nothing here reads
    # that. Same masking as `req_gosub`'s second branch (D-NGRAM18b).
    # What IS observable is REACHABILITY, so that is what this arm now cuts.
    ("K-A1 the helper always reports malformed", [
        ("""evmc_arg_int:
                call    ev_mc_arg_checked   ; D-F2-4 gate""",
         """evmc_arg_int:
                scf                         ; K-A1 CUT (restored on exit)
                ret
                call    ev_mc_arg_checked   ; D-F2-4 gate""")]),
    ("K-A2 the int test asks the wrong type", [
        ("""                ld      a,(FACTYP)
                cp      2
                ret                         ; CF clear; Z = already an int""",
         """                ld      a,(FACTYP)
                cp      4                   ; K-A2 CUT (restored on exit)
                ret""")]),
]

EXPECT = {
    # 🔴 ALL FOURTEEN, INCLUDING THE MALFORMED ROWS -- and that is the point I
    # missed when predicting ten. `ev_mc_arg_checked` is INSIDE the helper, so a
    # helper that returns before calling it never arms the deferred D-F2-4 error
    # either: `ABS()` stops reporting ERR 2 as well. The two CONTROLS hold, which
    # is what makes this a reachability arm rather than "the machine broke".
    "K-A1": {"i.abs", "f.abs", "b.abs", "i.sgn", "f.sgn", "b.sgn",
             "i.int", "f.int", "b.int", "i.fix", "f.fix", "b.fix",
             "x.abs8k", "x.fixneg"},
    # 🔴 I PREDICTED THE INVERSION BACKWARDS. `cp 4` does not merely stop ints
    # taking the int arm -- FACTYP 4 is SINGLE, so SINGLES take it instead. The
    # measured set is what that produces: the float rows that are singles move
    # INTO the int arm, and the int rows move OUT of it. `i.fix` and `x.abs8k`
    # hold because their verbs' two arms agree on those particular values.
    "K-A2": {"f.abs", "f.fix", "f.int", "i.abs", "i.sgn", "x.fixneg"},
}

PAT = ["call ev_mc_arg_checked", "ret nz", "ld a,(factyp)", "cp 2"]


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
    p = f"{TMP}/ai_{tag}.out"
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
    calls = sum(1 for e in ins if e[3] == "call evmc_arg_int")
    alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    # 🔴 ZERO IS THE HONEST EXPECTATION HERE, unlike req_comma/req_gosub where
    # the BODY itself matched the pattern and 1 was correct. This helper's second
    # instruction is `jr nz,eai_bad`, not `ret nz`, so the body does NOT match
    # its own pattern -- and the `matcher alive` control is what stops a 0 that
    # means "the regex matches nothing" reading as a 0 that means "all rewired".
    ok = (occ == 0 and calls == 4 and alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 {occ} open-coded run(s) left (want 0 "
          f"-- the body's `jr nz` breaks the pattern, so it does not match "
          f"itself), {calls} call(s) (want 4), "
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
            moved, after, rc = knife_guard.build(f"{TMP}/aik_{tag}_build.out",
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
            print("  🔴 NO ROWS READ BACK")
            fails.append(name)
            continue
        if miss:
            print(f"  🔴 {len(miss)} baseline row(s) NOT PRINTED ({' '.join(miss)})")
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

    sh("make repack-machine", f"{TMP}/aik_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
