#!/usr/bin/env python3
r"""D-NGRAM12 K-N12A/K-N12B + S1 — one `load_commit_prog`, entered from BOTH
transports.

The slice collapsed the ten-instruction completion tail that `do_tape_prog`
(CLOAD, tokenised tape) and `disk_prog_load` (LOAD"file") each carried verbatim
into ONE routine; `dpl_done` is now an `equ` alias of it. That is a MECHANISM
argument. These knives are the OBSERVABLE half: a cut made ONCE, at the shared
body, must move rows on BOTH transports -- if a tape row holds while a disk row
moves, the two callers are not sharing what the collapse says they share.

  S1      STATIC: the run occurs exactly ONCE in basic/ (it was twice), the
          alias exists, and the matcher itself is alive -- the expected count is
          1, not 0, so a matcher that silently matched NOTHING would report
          `0` and read as an even better result. The `alive` arm is what stops
          that.
  K-N12A  cut the `$0000` END-OF-PROGRAM MARKER the shared body writes.
          PREDICTED: every row that LISTs or RUNs a LOADED program moves, on
          BOTH transports -- disk `run-hit`, `run-hit-res`, `loadr-hit`,
          `load-plain:listing`, and tape `cas2-cload:listing`. The rows that
          never reach the body must HOLD: `bare-run` (a program TYPED in, the
          control that says the machine still works), `run-miss`,
          `run-miss-res`, `loadr-miss-res`, `load-plain` (whose subject tail is
          empty either way), and `cas2-cload` (the tape SEARCH line, printed
          before the load finishes).
  K-N12B  turn the shared body's `or a` into `scf` -- CF SET means "the load
          failed and has already reported" to every caller (D-CASTAIL /
          D-RUNTAIL). PREDICTED: the rows that RUN what was loaded refuse --
          `run-hit`, `run-hit-res`, `loadr-hit` -- and `load-plain:listing`
          HOLDS, because LOAD without `,R` has nothing to refuse. Tape:
          `cas2-cload:listing` holds for the same reason (CLOAD does not run).
          🔴 This one is a PREDICTION ABOUT WHICH HALF MOVES, not a "cut it and
          see everything go red" -- the two knives separate the body's two
          outputs (the bytes it writes, and the CF it returns).
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/cload.asm"
# `ok`/`DIFF`/`PIN` + label + readings -- the one row grammar both probes print
# (docs/spec-probe-rowshape.md).
# 🔴 EVERY PREFIX THE ROW GRAMMAR CAN PRINT, AND TWO OF THEM WERE LEARNED THE
# HARD WAY.
#   `--`   the one-side CHARACTERIZATION prefix: a knife runs `--sides zb`, so
#          NO row is `ok`. The first cut matched only scored prefixes, read back
#          zero rows, and the runner refused -- correctly.
#   `FAIL` / `....`  a knife that breaks a POSITIVE CONTROL makes the probe stop
#          scoring and re-print every row as `....  (not scored)`. Those rows are
#          real readings. Matching neither prefix, the K-N12B pass read back the
#          TAPE rows only -- and then scored all nine unread DISK rows as MOVED,
#          because `cut.get(label)` is None for a row that was never parsed.
#          🔴 A PARTIAL READ LOOKED EXACTLY LIKE A TOTAL REDDENING. The `if not
#          cut` guard could not catch it: `cut` was non-empty. The coverage check
#          in `capture()` is what catches it now.
# Later lines win, so the `....` re-print supersedes the `FAIL` line above it.
ROW = re.compile(r"^(?:ok|DIFF|PIN|MISS|FAIL|\.\.\.\.|--)\s+(\S+)\s+(.*)$")
ZB = re.compile(r"zb='([^']*)'")

RUNS = [
    ("disk", "python3 probes/basic/basic_probe_runtail.py --sides zb"),
    ("tape", "python3 probes/basic/basic_probe_castail.py --sides zb "
             "--only cas2-cload"),
]

KNIVES = [
    ("K-N12A cut the $0000 end-of-program marker", [
        ("""                ld      (PRGEND),hl         ; end marker sits at the store cursor
                ld      (hl),0
                inc     hl
                ld      (hl),0""",
         """                ld      (PRGEND),hl         ; end marker sits at the store cursor
                nop                         ; K-N12A CUT (restored on exit)
                nop
                nop""")]),
    ("K-N12B or a -> scf (the CF the body returns)", [
        ("""                call    relink
                or      a                   ; D-CASTAIL: the SUCCESS half of the CF""",
         """                call    relink
                scf                         ; K-N12B CUT (restored on exit)
                                            ; D-CASTAIL: the SUCCESS half of the CF""")]),
]

EXPECT = {
    # 🔴 RE-PREDICTED AFTER THE FIRST RUN, AND THE REASON IS RECORDED IN THE
    # SPEC (§4): the disk rows CANNOT see this cut, because they re-load a
    # program byte-identical to the one just typed and the terminator is already
    # in RAM. `load-short` is the row added to close exactly that blindness.
    "K-N12A": {"cas2-cload:listing", "load-short:listing"},
    "K-N12B": {"run-hit", "run-hit-res", "loadr-hit"},
}

# The ten-instruction run the slice collapsed, in ngram_sweep's key form.
PAT = ["ld hl,(clptr)", "ld (prgend),hl", "ld (hl),0", "inc hl", "ld (hl),0",
       "ld hl,txtbase", "ld (txttab),hl", "call relink", "or a", "ret"]


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh,
                               stderr=subprocess.STDOUT)


def read_rows(paths):
    """label -> zb reading, merged across the two probes."""
    rows = {}
    for path in paths:
        if not os.path.exists(path):
            continue
        for line in open(path, errors="replace"):
            m = ROW.match(line.strip())
            if not m:
                continue
            z = ZB.search(m.group(2))
            if z:
                rows[m.group(1)] = z.group(1)
    return rows


def capture(tag, need=None):
    """(rows, missing) -- `missing` is the baseline labels this run did NOT
    print. A run that produced no reading for a row says NOTHING about that row;
    treating its absence as a changed value is how an unparsed probe output
    reads as a total reddening."""
    paths = []
    for kind, cmd in RUNS:
        p = f"{TMP}/n12_{tag}_{kind}.out"
        sh(f"ZEROBAS_REFCACHE=0 {cmd}", p)
        paths.append(p)
    rows = read_rows(paths)
    return rows, sorted(set(need or ()) - set(rows))


def main():
    fails = []

    import ngram_sweep as NS
    ins = [e for e in NS.parse() if e[0] == "I"]
    n = len(PAT)
    occ = sum(1 for k in range(len(ins) - n + 1)
              if [e[3] for e in ins[k:k + n]] == PAT
              and ins[k][1].startswith("basic/"))
    alias = "dpl_done        equ     load_commit_prog" in open(SRC).read()
    alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    ok = (occ == 1 and alias and alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 one body, two entries: {occ} "
          f"occurrence(s) of the run in basic/ (want 1 -- it was 2), alias "
          f"{'present' if alias else '🔴 MISSING'}, "
          f"matcher{'' if alive else ' 🔴 STALE: ' + str(stale)} alive")
    if not ok:
        fails.append("S1")

    base, _ = capture("base")
    if not base:
        print("🔴 NO BASELINE ROWS READ BACK")
        return 2
    print(f"\nbaseline: {len(base)} row(s) across both transports\n")

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
            moved, after, rc = knife_guard.build(f"{TMP}/n12k_{tag}_build.out",
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
            print(f"  🔴 {len(missing)} baseline row(s) NOT PRINTED by this run "
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

    sh("make repack-machine", f"{TMP}/n12k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
