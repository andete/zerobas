#!/usr/bin/env python3
r"""D-NGRAM13 K-N13A/K-N13B + S1 — one `dpl_get_store`, and the FRAME it needs.

  S1      STATIC: 0 open-coded runs left, exactly 3 calls, matcher alive.
  K-N13A  drop the `pop hl` from the helper's error tail -- the frame fix
          itself. `dpl_err_pop` then drops the helper's RETURN ADDRESS instead of
          the caller's guarded count, and `dpl_err`'s own `ret` returns to that
          count as if it were an address.
          PREDICTED: the four rows that need the machine to SURVIVE the failed
          load move -- `d.alive`, `d.body-l`, `d.lineno-l`, `d.body-res`. The two
          message-only rows (`d.body`, `d.lineno`) HOLD: `load_error` prints
          before the bad `ret` is taken, so their subject is already on the
          screen. `d.ok` and `ctl.typed` never take the path.
  K-N13B  drop the `inc hl` from the STORE half -- every byte lands on the same
          address.
          PREDICTED: `d.ok`, `d.body-l`, `d.body-res` move. 🎯 `d.lineno-l` HOLDS,
          and that is the sharp half: LNO.BAS is cut off after the LINK WORD,
          which is stored by the loader's own `ld (hl),c / inc hl / ld (hl),b`
          and NOT by this helper -- so that row reaches the helper's `call
          fat_io_getbyte` and never its store. The two knives therefore say
          WHICH HALF of the helper each row exercises, not merely that it is
          reached.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/cload.asm"
ROW = re.compile(r"^(?:ok|DIFF|PIN|MISS|FAIL|\.\.\.\.|--)\s+(\S+)\s+(.*)$")
ZB = re.compile(r"zb='([^']*)'")
PROBE = "python3 scratchpad/ngram13_probe.py zb"

KNIVES = [
    ("K-N13A swallow the EOF (ret c -> or a)", [
        ("""                ret     c                   ; EOF -> the CALLER raises, in ITS frame""",
         """                or      a                   ; K-N13A CUT (restored on exit)""")]),
    ("K-N13B drop the store advance (inc hl)", [
        ("""                ret     c                   ; EOF -> the CALLER raises, in ITS frame
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl""",
         """                ret     c                   ; EOF -> the CALLER raises, in ITS frame
                ld      hl,(CLPTR)
                ld      (hl),a
                nop                         ; K-N13B CUT (restored on exit)""")]),
]

EXPECT = {
    # 🔴 THIS IS THE ARM THE *OTHER* SHAPE COULD NOT HAVE. The first cut of this
    # slice folded `jp c,dpl_err_pop` into the helper and needed a frame fix
    # (`pop hl`); cutting THAT moved ZERO rows on two fixtures picked to make the
    # bogus return address hostile ($0007, then $0BB3). The stack below the
    # loader is the REPL's own, so a stray `ret` finds a plausible address there.
    # 4 B were given back for the CF-return shape, whose failure IS a reading:
    # swallow the EOF and every truncated-file row changes.
    # 🔴 AND I PREDICTED SEVEN AND THREE MOVED. The three are exactly the rows
    # that read the PROGRAM (`d.body-l`, `d.lineno-l`, `d.body-res`).
    # The two MESSAGE rows cannot move, and the reason is worth keeping: with
    # the EOF swallowed the loader runs past the end of the file and hits EOF
    # again at the next LINK-WORD read, which has its own `jp c,dpl_link_err`
    # and prints the IDENTICAL message. A second check downstream makes the
    # first one's failure invisible to any row that reads only the message.
    # `d.alive` / `d.bigalive` do not move either: the machine survives both
    # ways. They are controls here, not subjects.
    "K-N13A": {"d.body-l", "d.lineno-l", "d.body-res"},
    "K-N13B": {"d.ok", "d.body-l", "d.body-res"},
}

PAT = ["call fat_io_getbyte", "jp c,dpl_err_pop", "ld hl,(clptr)",
       "ld (hl),a", "inc hl", "ld (clptr),hl"]


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh,
                               stderr=subprocess.STDOUT)


def read_rows(path):
    rows = {}
    if not os.path.exists(path):
        return rows
    for line in open(path, errors="replace"):
        m = ROW.match(line.strip())
        if m:
            z = ZB.search(m.group(2))
            if z:
                rows[m.group(1)] = z.group(1)
    return rows


def capture(tag, need=None):
    """(rows, missing). An unread row is not a moved row -- D-NGRAM12 scored
    nine of them as reddened when it had read none."""
    p = f"{TMP}/n13_{tag}.out"
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
    calls = sum(1 for e in ins if e[3] == "call dpl_get_store")
    # 🔴 THE OBVIOUS MATCHER CONTROL IS WRONG HERE, AND THE FIRST RUN SAID SO.
    # `knife_guard.pattern_alive(PAT, ...)` asks "does every element of the
    # pattern still exist in the tree?" -- the arm that stops a matcher scoring
    # 0 because it matches nothing. But this carve EXTINGUISHES one of its own
    # elements: `jp c,dpl_err_pop` was written at the three sites and nowhere
    # else, so after the collapse it is gone by design and the control reported
    # STALE on a correct tree. Controlled instead on the pattern that MUST still
    # exist -- the helper's own two opening instructions.
    HELPER = ["call fat_io_getbyte", "ret c"]
    alive, stale = knife_guard.pattern_alive(HELPER, (e[3] for e in ins))
    ok = (occ == 0 and calls == 3 and alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {occ} open-coded "
          f"run(s) left (want 0), {calls} call(s) (want 3), "
          f"matcher{'' if alive else ' 🔴 STALE: ' + str(stale)} alive "
          f"(controlled on the HELPER's own body -- `jp c,dpl_err_pop` is "
          f"EXTINCT by design and cannot be the control)")
    if not ok:
        fails.append("S1")

    base, _ = capture("base")
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
            moved, after, rc = knife_guard.build(f"{TMP}/n13k_{tag}_build.out",
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

    sh("make repack-machine", f"{TMP}/n13k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
