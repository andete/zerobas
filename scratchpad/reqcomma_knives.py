#!/usr/bin/env python3
r"""D-NGRAM17 K-C1/K-C2 + S1 — the two halves of `req_comma`.

  S1     STATIC: 0 open-coded runs left, exactly 10 calls (re-pinned 2026-10-05), matcher alive.
  K-C1   drop the `inc hl`, so the comma is matched but NOT CONSUMED and each
         verb reads it as the start of its next argument.
         PREDICTED: every `g.*` row moves; the `b.*` rows HOLD -- they already
         raise, and a comma that is never reached cannot be consumed twice.
  K-C2   `jp nz,stmt_error` -> `ret nz`, so a MISSING comma is accepted.
         PREDICTED: the `b.*` rows move; the `g.*` rows HOLD.
🎯 The two arms cut the two halves of one sentence, and each must leave the
other half's rows alone -- that is what says the helper is doing both jobs
rather than one.
⚠️ BOTH CUTS ARE SIZE-NEUTRAL ON PURPOSE. A cut that changes the byte count can
push a `jr` out of range; the build then FAILS, the ROM is left unchanged, and
knife_guard reports the knife INERT (which is what happened in D-RUNARG).
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/interp.asm"
ROW = re.compile(r"^(?:ok|DIFF|--)\s+(\S+)\s+(.*)$")
PROBE = "python3 scratchpad/reqcomma_probe.py zb"

KNIVES = [
    ("K-C1 the comma is matched but not consumed", [
        ("""                inc     hl                  ; consume it
                ret""",
         """                nop                         ; K-C1 CUT (restored on exit)
                ret""")]),
    ("K-C2 a missing comma is accepted", [
        ("                jp      nz,stmt_error       ; no comma: the statement aborts",
         "                ret     nz                  ; K-C2 CUT (restored on exit)\n"
         "                nop\n"
         "                nop")]),
]

# 🔴 BOTH SETS ARE NARROWER THAN I PREDICTED, AND EVERY OMISSION IS A ROW THAT
# CANNOT REACH ITS SITE -- which is the knives' real yield here.
#   g.field   reads `LEN(A$)` AFTER a `CLOSE`, and that is 0 either way: it is
#             the row carrying the separate CLOSE divergence (filed), and it is
#             blind to anything `req_comma` does.
#   b.field   raises `Bad file number` BEFORE the comma check is reached.
#   b.swap    never presents a missing comma: the crunch folds `A B` into one
#             variable name, so SWAP sees one argument and faults on the second
#             (`x.spacename` measures that folding directly).
# 🎯 `g.sound` IS IN K-C1's SET ONLY BECAUSE A KNIFE MOVED IT THERE. As two typed
# lines the row read the PRINT and was blind; joined with `:` it is not.
EXPECT = {
    "K-C1": {"g.swap", "g.sound", "g.input", "g.field2"},
    "K-C2": {"b.sound", "b.input"},
}
# 🔁 RE-SHAPED 2026-10-05 (space plan B-12): the body has been `call skip_comma
# / jp nz,stmt_error / inc hl` since a later pair carve folded `call skip_spaces
# / cp ','` into skip_comma, so the old 4-instruction PAT matched NOTHING and S1
# could only fail -- unnoticed, because this script is not in the battery.
PAT = ["call skip_comma", "jp nz,stmt_error", "inc hl"]


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
    p = f"{TMP}/rc_{tag}.out"
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
    calls = sum(1 for e in ins if e[3] == "call req_comma")
    alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    # the BODY is one such run, so 1 is the honest expectation, not 0.
    # 🔁 CALLS RE-PINNED 2026-10-05 (space plan B-12, C5-lite): 4 -> 10. The pin
    # had ALREADY drifted to 7 (later slices added req_comma callers; this script
    # is not in the battery, so nothing re-read it). B-12 then routed POKE's,
    # VDP()='s and MID$='s open-coded runs through it: 10. With PAT re-shaped
    # (above) the run count reads 1 -- the body -- measured, not assumed.
    ok = (occ == 1 and calls == 10 and alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 {occ} run(s) in basic/ (want 1 -- the "
          f"BODY is one, and 0 would mean it vanished), {calls} call(s) (want 10), "
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
            moved, after, rc = knife_guard.build(f"{TMP}/rck_{tag}_build.out",
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

    sh("make repack-machine", f"{TMP}/rck_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
