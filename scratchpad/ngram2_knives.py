#!/usr/bin/env python3
r"""D-NGRAM2 K-NG1/K-NG2 — six sites, and every one of them must move.

🔴 THE HAZARD THIS SLICE ACTUALLY HAS is not "the helper is wrong" -- it is "one
of the six sites was never rewired". A site left open-coded behaves IDENTICALLY,
so every row stays green and the byte saving silently comes up short. A knife on
the helper is what turns that into a visible failure: retarget the helper and
EVERY site's own row must move. A row that does not move names the site that was
missed.

  K-NG1  `jp z,loc_missing` -> `jp z,stmt_error` in req_operand. ALL 11 subject
         rows must go ERR 24 -> ERR 2; the 6 green controls must NOT move.
  K-NG2  delete the `cp COLON / jp z,loc_missing` half.
         🔴 MY FIRST PREDICTION HERE WAS TOO WIDE AND THE RUN SAID SO: I expected
         all SIX colon rows to move, and exactly TWO do -- `PLAY:` and
         `PRINT USING:`. At LOCATE and SCREEN the colon rows hold their ERR 24
         through a SECOND CAUSE: with the helper's COLON test gone they fall
         through to the argument evaluation, and `eval` on a `:` defers ERR 24 of
         its own (D-MISSOP, ev_f_err). So the helper's COLON half is the SOLE
         cause of the verdict at 2 sites and a redundant-but-harmless first
         responder at the other 4.
         🎯 That is the point of keeping this arm: it is what makes the four
         agreeing rows say WHY they agree, instead of being counted as evidence
         for a test that is not what produces their answer.
         [[a-case-that-agrees-can-agree-for-the-wrong-reason]]

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): try/finally AND atexit.
"""
import atexit, hashlib, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard   # D-KNIFEROM: ONE implementation, not three

TMP, SRC = "/tmp/zerobas", "basic/interp.asm"
# The colon rows where the helper's COLON test is the SOLE cause of ERR 24.
# MEASURED, not predicted -- see K-NG2's header. The other colon rows
# (s.locate.colon, s.locate.arg3, s.screen.colon, s.screen.trailc) have a second
# cause downstream and hold their verdict without it.
SOLE_CAUSE_ROWS = {"s.play.colon", "s.using.colon"}

KNIVES = [
    ("K-NG1 retarget the helper", [
        ("""                jp      z,loc_missing       ; the slot ENDS here -> ERR 24
                cp      COLON
                jp      z,loc_missing       ; `... :` likewise -> ERR 24""",
         """                jp      z,stmt_error        ; K-NG1 CUT (restored on exit)
                cp      COLON
                jp      z,stmt_error        ; K-NG1 CUT""")]),
    ("K-NG2 drop the COLON half", [
        ("""                cp      COLON
                jp      z,loc_missing       ; `... :` likewise -> ERR 24""",
         """                cp      COLON               ; K-NG2 CUT (restored on exit)""")]),
]

ROW = re.compile(r"^[a-z][a-z0-9]*\.[a-z0-9.]+$")


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
    base = read_rows(f"{TMP}/ng_zb_base.out")
    if not base:
        print(f"NO BASELINE: python3 scratchpad/ngram2_probe.py zb > {TMP}/ng_zb_base.out")
        return 2
    subj = sorted(r for r in base if r.startswith("s."))
    ctrl = sorted(r for r in base if not r.startswith("s."))
    print(f"baseline: {len(subj)} subject row(s), {len(ctrl)} control(s)\n")
    fails = []
    for name, cuts in KNIVES:
        tag = name.split()[0]
        orig = open(SRC).read()
        bad = [o for o, _ in cuts if orig.count(o) != 1]
        if bad:
            print(f"{name}: KNIFE BROKEN -- anchor not unique"); fails.append(name); continue
        restore = lambda o=orig: open(SRC, "w").write(o)
        atexit.register(restore)
        try:
            t = orig
            for o, n in cuts:
                t = t.replace(o, n)
            open(SRC, "w").write(t)
            before = knife_guard.hashes()
            print(f"{name}: planted, rebuilding...")
            if sh("make repack-machine", f"{TMP}/ngk_{tag}_build.out"):
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            after = knife_guard.hashes()
            # 🔴 A KNIFE CAN BE SILENTLY INERT BECAUSE THE BUILD DID NOT HAPPEN.
            # Writing the source and immediately running `make` can leave the
            # previous ROM in place, and then the probe measures the UNCUT
            # machine -- which reports as "moved 0 rows", i.e. exactly what a
            # knife with nothing to say looks like. It cost a wrong reading on
            # this very slice: one run had K-NG2 reproduce K-NG1's answers
            # byte-for-byte. The ROM hash MUST move when a cut is planted.
            if after == before:
                print(f"{name}: 🔴 KNIFE INERT -- the ROM did not change "
                      f"({before}); the probe would measure the UNCUT machine")
                fails.append(name); continue
            print(f"  ROM {before}  ->  {after}")
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/ngram2_probe.py zb",
                   f"{TMP}/ngk_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/ngk_{tag}.out")
        if not cut:
            print(f"{name}: 🔴 NO ROWS READ BACK -- not 'reddened nothing'")
            fails.append(name); continue
        moved = {r for r in base if base[r] != cut.get(r)}
        want = set(subj) if tag == "K-NG1" else SOLE_CAUSE_ROWS
        missing, extra = sorted(want - moved), sorted(moved - want)
        print(f"  moved {len(moved)}: {' '.join(sorted(moved)) or '(none)'}")
        if missing:
            print(f"  🔴 DID NOT MOVE (site not wired to the helper?): {' '.join(missing)}")
            fails.append(name)
        if extra:
            print(f"  🔴 MOVED BUT SHOULD NOT HAVE: {' '.join(extra)}")
            fails.append(name)
        if not missing and not extra:
            print(f"  ✅ exactly the {len(want)} predicted row(s) moved, "
                  f"{len(ctrl)} control(s) held")
        print()
    sh("make repack-machine", f"{TMP}/ngk_restore.out")
    print("=" * 66)
    print("VERDICT:", "every site has its own live witness" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
