#!/usr/bin/env python3
r"""D-NGRAM18 K-G1 + S1 — every trap verb routes through `req_gosub`.

  S1     STATIC: 1 run left (the BODY), exactly 4 calls, matcher alive.
  K-G1   make the helper ALWAYS raise. PREDICTED: all four `g.*` rows move and
         the three controls hold -- which is the observable form of "every site
         was rewired", complementing S1's static count.

🔴 TWO FINER CUTS WERE BUILT, RUN, AND FOUND INVISIBLE TO THESE ROWS. They are
recorded here rather than dropped, because each says something about the ROW SET:

  * drop the `inc hl` (GOSUB matched, not consumed): moved NOTHING. Reading the
    code says why -- the slot loop then finds no line number at the GOSUB token
    and SILENTLY CLEARS the handlers, and the trailing `:PRINT "ZQ1"` still runs.
    The failure mode is a cleared trap, and no row here reads a trap FIRING.
  * `jp nz,trap_syntax` -> `ret nz` (a missing GOSUB accepted): also moved
    nothing. `ON KEY 100` still reports Syntax error, so that rejection comes
    from somewhere later, not from this check -- the `b.*` rows are blind to the
    helper even though the `g.*` rows are not.

➡️ WHAT WOULD SEE THEM: a row that ARMS a trap and then makes it FIRE (e.g.
`ON STOP GOSUB` plus a Ctrl-STOP), which needs an input-injection fixture this
probe does not build. Named rather than left as a silent gap.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/interp.asm"
ROW = re.compile(r"^(?:ok|DIFF|--)\s+(\S+)\s+(.*)$")
PROBE = "python3 scratchpad/reqgosub_probe.py zb"

KNIVES = [
    ("K-G1 req_gosub always raises", [
        ("""req_gosub:
                call    skip_spaces""",
         """req_gosub:
                jp      trap_syntax         ; K-G1 CUT (restored on exit)
                call    skip_spaces""")]),
]

EXPECT = {
    # every site routes through the helper, and the three controls do not.
    "K-G1": {"g.key", "g.stop", "g.interval", "g.strig"},
}

PAT = ["call skip_spaces", "cp gosub_token", "jp nz,trap_syntax", "inc hl"]


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
        if m and "=" in m.group(2):
            rows[m.group(1)] = m.group(2).strip()
    return rows


def capture(tag, need=None):
    p = f"{TMP}/rg_{tag}.out"
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
    calls = sum(1 for e in ins if e[3] == "call req_gosub")
    alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    # the BODY is one such run, so 1 is the honest expectation, not 0.
    ok = (occ == 1 and calls == 4 and alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 {occ} run(s) in basic/ (want 1 -- the "
          f"BODY is one, and 0 would mean it vanished), {calls} call(s) (want 4), "
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
            moved, after, rc = knife_guard.build(f"{TMP}/rgk_{tag}_build.out",
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

    sh("make repack-machine", f"{TMP}/rgk_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
