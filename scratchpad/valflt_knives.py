#!/usr/bin/env python3
r"""D-VALFLT — the arms for routing VAL's number through tk_float.

  K-VF1  point TKVALEND at the body's START instead of its end, so every scan is
         immediately out of range. Every VAL row with a nonzero answer must go
         to 0 -- the bound is READ.
  K-VF2  drop the float sign flip, so a negative float loses its sign. Only the
         rows whose answer is a NEGATIVE FLOAT may move; `VAL("-34")` is an
         integer and takes the other arm, which is what makes it a control.
  K-VF3  drop the TKOVF -> SH_ERR route, so a refused literal answers a value
         instead of Overflow.
  K-VF4  🎯 THE ARM PROMISED BY docs/spec-basic-pcttrunc.md §3. Cut tcr_ovf's
         `inc sp` pair -- the frame-depth fix that was UNWITNESSED while VAL did
         not use that path. In VAL mode tkf_rej ends in `ret`, and with the leak
         restored that `ret` goes to the emit destination.
         [[a-guard-witnessed-only-by-a-deferred-error]]
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP = "/tmp/zerobas"
TKF, SHP, STR = "sub/tkfloat.asm", "sub/strheap.asm", "basic/str-engine.asm"
ROW = re.compile(r"^[a-z]+\.")

KNIVES = [
    ("K-VF1 bound at the body START", SHP, [
        ("""                add     hl,de
                ld      (TKVALEND),hl       ; one past the last body byte""",
         """                ld      (TKVALEND),hl       ; K-VF1 CUT (restored on exit)
                add     hl,de""")]),
    ("K-VF2 drop the float sign flip", SHP, [
        ("""                xor     $80
                ld      (FAC),a""",
         """                                            ; K-VF2 CUT (restored on exit)""")]),
    ("K-VF3 drop the overflow route", SHP, [
        ("""                jp      nz,svp_bovf         ; `VAL("1E99")` -> Overflow on both""",
         """                nop                         ; K-VF3 CUT (restored on exit)
                nop
                nop                         ;""")]),
    ("K-VF4 restore the tcr_ovf frame leak", TKF, [
        ("""                inc     sp                  ; discard tkf_calc_and_round's own
                inc     sp                  ; return address""",
         """                nop                         ; K-VF4 CUT (restored on exit)
                nop""")]),
]

# Predictions, written from the shipped row set BEFORE the arms were run.
_VF1 = """p.int p.neg p.plus p.frac p.lead p.trail p.negfrac
j.tail j.mid j.spacelead j.spacemid j.tabish
w.sp10 w.sp40 w.spsign w.spdot w.spexp w.tail40
e.e3 e.eneg e.d3 e.ebare e.big e.plus e.fracexp
x.40000 x.n32768 x.n40000 x.ovf x.ovfd x.under x.bang x.hash
x.pct x.pctfrac x.dbl x.pct9 x.pct25 x.pctbig
g.plus1 g.var s.roundtrip"""

EXPECT = {
    # every row that reaches tk_float AND has a nonzero answer. The rows that
    # ALREADY answer 0 (`VAL("")`, `VAL("ABC")`, `VAL("-")`, `VAL(".")`,
    # `VAL("0.07%")`) cannot move, and neither can the `&` literals -- the base
    # scan never reads TKVALEND -- which is what makes them the controls.
    "K-VF1": set(_VF1.split()),
    # a negative FLOAT only. `VAL("-34")`, `VAL(" - 12")` and `VAL("-          12")`
    # are negative INTEGERS and take the negate arm, so they are controls for
    # this cut rather than subjects.
    "K-VF2": {"x.n32768", "x.n40000", "p.negfrac"},
    # every VAL row whose answer is the Overflow refusal.
    "K-VF3": {"x.ovf", "x.ovfd", "x.under", "x.pctbig"},
    # 🎯 THE DISCRIMINATING PREDICTION. Only the overflows raised from INSIDE
    # tkf_calc_and_round are one frame deep: 1E99 / 1D99 (dec_exp > 63) and
    # 1E-99 (dec_exp <= -65). `VAL("40000.5%")` refuses from tkf_check_percent,
    # which is at tk_float's own frame level and is therefore ALREADY correct --
    # so it must NOT move. And every c.* literal row goes through tokenise mode,
    # where the leaked word is absorbed by the error path's stack reset.
    "K-VF4": {"x.ovf", "x.ovfd", "x.under"},
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
    base = read_rows(f"{TMP}/valflt_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/val_probe.py zb "
              f"> {TMP}/valflt_zb_base.out")
        return 2
    print(f"baseline: {len(base)} row(s)\n")
    only = set(sys.argv[1:])
    fails = []
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
            moved, after, rc = knife_guard.build(f"{TMP}/vf_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/val_probe.py zb",
               f"{TMP}/vf_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/vf_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT.get(tag)
        if want is None:
            print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
                  f"\n  🔴 NO PREDICTION RECORDED for {tag} — an arm without one is"
                  f" a report, not an arm")
            fails.append(name); continue
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: {' '.join(sorted(want)) or '(none)'}"
              f"   {'OK' if ok else '🔴 MISMATCH'}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/vf_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
