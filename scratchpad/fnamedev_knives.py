#!/usr/bin/env python3
r"""D-NGRAM16 / D-RUNARG — arms for the carve and for the REPL gate.

  S1      STATIC: 0 open-coded `fname_expr / ld de,dev_cas / dev_cmp` runs left,
          exactly 4 calls to the helper, and `dl_bare` is wired into `dl_cmd`.
  K-N16A  drop `call fname_expr` from the shared helper, so no verb parses its
          filename. PREDICTED: every row that names a file moves; the two
          controls hold.
  K-RA1   make `dl_bare` always answer "bare", which is the behaviour D-RUNARG
          replaced. PREDICTED: the seven `RUN <argument>` rows move and NOTHING
          else -- `LOAD`/`SAVE`/`BSAVE` never reach the REPL gate, and that they
          hold is what says the gate is RUN-specific rather than a parser change.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP = "/tmp/zerobas"
SAVE, PROG = "basic/save.asm", "basic/program.asm"
ROW = re.compile(r"^(?:ok|DIFF|--)\s+(\S+)\s+(.*)$")
PROBE = "python3 scratchpad/fnamedev_probe.py zb"

KNIVES = [
    ("K-N16A the helper never parses the filename", SAVE, [
        ("""fname_dev:
                call    fname_expr          ; HL -> the staged '"'-terminated copy""",
         """fname_dev:
                nop                         ; K-N16A CUT (restored on exit)
                nop
                nop""")]),
    # 🔴 SIZE-NEUTRAL ON PURPOSE. The first cut inserted `scf`+`ret` at the top
    # of dl_bare -- two extra bytes, which pushed another `jr` out of relative
    # range, so the BUILD FAILED and the ROM did not change. knife_guard called
    # it INERT rather than letting the probe measure the uncut machine. Swapping
    # the final `or a` for `scf` is one byte for one and answers "bare" for every
    # input, which is precisely the pre-D-RUNARG behaviour.
    ("K-RA1 the REPL gate calls everything bare", PROG, [
        ("""                or      a                   ; anything else -> an ARGUMENT: crunch it
                ret""",
         """                scf                         ; K-RA1 CUT (restored on exit)
                ret""")]),
]

EXPECT = {
    "K-N16A": {"n.load", "n.run", "n.save", "n.bsave", "g.save", "g.load",
               "g.run", "g.miss", "g.var", "n.runres", "n.loadres", "n.runstr",
               "n.runexpr", "n.runparen", "g.runquote", "n.runspq"},
    # 🎯 `n.runline` and `g.runline` are NOT here, and the omission is measured:
    # `RUN 20` / `RUN20` take `do_run`'s LINENO arm and never reach `fname_dev`
    # at all. I predicted 18 and 16 moved; the two that held are exactly those.
    "K-RA1": {"n.run", "n.runres", "n.runstr", "n.runexpr", "n.runparen",
              "n.runline", "n.runspq"},
}
PAT = ["call fname_expr", "ld de,dev_cas", "call dev_cmp"]


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
    p = f"{TMP}/fd_{tag}.out"
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
    calls = sum(1 for e in ins if e[3] == "call fname_dev")
    gate = "call    c,dl_bare" in open(PROG).read()
    # 🔴 EXPECTED ZERO, so the matcher gets its own control: the helper's tail is
    # a `jp`, so its own body does not match PAT either.
    alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    ok = (occ == 0 and calls == 4 and gate and alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 {occ} open-coded run(s) left (want 0), "
          f"{calls} call(s) to fname_dev (want 4), REPL gate "
          f"{'wired' if gate else '🔴 NOT wired'}, "
          f"matcher{'' if alive else ' 🔴 STALE: ' + str(stale)} alive")
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
            moved, after, rc = knife_guard.build(f"{TMP}/fdk_{tag}_build.out",
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

    sh("make repack-machine", f"{TMP}/fdk_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
