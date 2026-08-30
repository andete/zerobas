#!/usr/bin/env python3
r"""D-PCTTRUNC / D-VALUNDER / D-ERLENTRY — the arms for one sweep's three fixes.

  K-PT1  restore the old `%` digit count (TKDCOUNT as scanned), i.e. undo the
         truncation. Every fractional-`%` literal must go back to CONCATENATING
         its fraction digits.
  K-PT2  cut the FIRST clamp only (the negative difference, `.5%` / `0.7%`,
         where the first significant digit is past the dot). Those two must go
         to Overflow -- a 255-digit count -- and nothing else may move.
  K-VU1  send the below-`-64` exponent back to tcr_leadok instead of the reject,
         so the lead byte becomes dec_exp+64 wrapped rather than an error.
  K-EL1  drop the ERL sentinel store at the line-entry report.

🔴 THERE IS NO ARM FOR THE tcr_ovf FRAME FIX IN THIS RUNNER, AND THAT IS SAID
OUT LOUD RATHER THAN LEFT AS A GAP. In tokenise mode the leaked word is absorbed
by the error path's stack reset, so cutting it moves ZERO rows -- which is
exactly the shape D-POPRAISE mistook for an arm. Its witness is VAL mode, where
tkf_rej ends in `ret`; the arm lands with the VAL activation, not here.
[[a-guard-witnessed-only-by-a-deferred-error]]
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP = "/tmp/zerobas"
TKF, PRG = "sub/tkfloat.asm", "basic/program.asm"
ROW = re.compile(r"^[a-z]+\.")

KNIVES = [
    ("K-PT1 undo the % truncation", TKF, [
        ("""                ld      (TKDCOUNT),a
                cp      5""",
         """                ld      a,(TKDCOUNT)        ; K-PT1 CUT (restored on exit)
                cp      5""")]),
    ("K-PT2 cut the negative-difference clamp", TKF, [
        ("""                jr      nc,tkcp_pos
                xor     a                   ; the number starts past the dot""",
         """                nop                         ; K-PT2 CUT (restored on exit)
                nop""")]),
    ("K-VU1 below -64 is not a reject", TKF, [
        ("""                jp      z,tcr_ovf           ; dec_exp <= -65 -> Overflow""",
         """                jp      z,tcr_leadok        ; K-VU1 CUT (restored on exit)""")]),
    ("K-EL1 drop the ERL sentinel", PRG, [
        ("""                ld      de,65535
                ld      (ERRLIN),de""",
         """                                            ; K-EL1 CUT (restored on exit)""")]),
]

# Predictions, written BEFORE the run and corrected in place with the reason if
# they miss (this project scores the miss, not the guess).
EXPECT = {
    # every fractional-% literal; `0%` and `12%` have no fraction to concatenate
    # and cannot move, and the VAL x.pct* rows do not reach tk_float yet.
    "K-PT1": {"c.pctlit", "c.pct9lit", "c.pct25lit", "c.pct0lit", "c.pctdot"},
    # only the two whose first significant digit is past the dot: 0-1 = 255.
    # 🔴 PREDICTED {c.pct0lit, c.pctdot} AND MEASURED ZERO, because the row set
    # had no case that reaches this clamp at all. TKPOS counts DIGITS -- the dot
    # does not advance it -- so `.5%` is TKINTLEN=0/TKNZPOS=0 and `0.7%` is 1/1,
    # both a difference of ZERO. TKNZPOS only passes TKINTLEN when the FRACTION
    # carries its own leading zeros, which is what `0.07%` / `.007%` do. The
    # knife did its job: it found a hole in the ROWS, not in the code.
    "K-PT2": {"c.pct007lit", "c.pctd07lit"},
    # 1E-66 .. 1E-99. 1E-65 is dec_exp == -64 exactly and stays on the kept path.
    "K-VU1": {"c.underlit", "c.e66lit", "c.e67lit", "c.e68lit", "c.e69lit",
              "c.e70lit"},
    # both line-entry arms, plus every row that reads ERL through line 60 having
    # been rejected. c.erlnone types no bad line and cannot move.
    "K-EL1": {"c.erlovf", "c.erlbadln", "c.ovflit", "c.underlit", "c.pctbig",
              "c.e66lit", "c.e67lit", "c.e68lit", "c.e69lit", "c.e70lit"},
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
            rows[p[0]] = (" ".join(p[1:]).replace(" SAME", "").replace(" DIFF", "")
                          .replace(" NO-ORACLE", "").strip())
    return rows


def main():
    base = read_rows(f"{TMP}/crunch_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/val_probe.py zb "
              f"> {TMP}/crunch_zb_base.out")
        return 2
    print(f"baseline: {len(base)} row(s)\n")
    fails = []
    only = set(sys.argv[1:])
    for name, src, cuts in KNIVES:
        tag = name.split()[0]
        if only and tag not in only:
            continue
        orig = open(src).read()
        if any(orig.count(o) != 1 for o, _ in cuts):
            print(f"{name}: KNIFE BROKEN (pattern not unique in {src})")
            fails.append(name); continue
        restore = lambda o=orig, s=src: open(s, "w").write(o)
        atexit.register(restore)
        try:
            t = orig
            for o, n in cuts:
                t = t.replace(o, n)
            open(src, "w").write(t)
            before = knife_guard.hashes()
            print(f"{name}: planted in {src}, rebuilding...")
            moved, after, rc = knife_guard.build(f"{TMP}/ck_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/val_probe.py zb",
               f"{TMP}/ck_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/ck_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: {' '.join(sorted(want)) or '(none)'}"
              f"   {'OK' if ok else '🔴 MISMATCH'}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/ck_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
