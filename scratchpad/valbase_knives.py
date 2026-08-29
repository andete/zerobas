#!/usr/bin/env python3
r"""D-VALBASE K-VB1/K-VB2/K-VB3 — the dispatch, the codes, and the register.

  K-VB1  disable the '&' dispatch. Every base row must collapse back to the
         old answer (0, or no refusal at all).
  K-VB2  swap the two SH_ERR codes -- the bug this slice actually shipped and
         then fixed. `VAL("&")` must go back to Overflow and `VAL("&H1FFFF")`
         to Syntax error, which is exactly how it was caught.
  K-VB3  🎯 THE ARM FOR A BUG NO ROW FOUND. The first draft used C as scratch
         for both the max digit and the shift count, so C no longer held the
         packed base constant on the SECOND digit. I caught that by tracing the
         register flow before running it -- this arm turns that reading into a
         row, so the next person who "simplifies" the register discipline gets
         told. Multi-digit literals must break; single-digit ones need not.
         [[a-scratch-register-that-was-the-callers-value]]
         🔴 AND THE FIRST VERSION OF THIS ARM WAS A DESIGNED NO-OP. It inserted
         `pop af / push af`, which leaves the stack exactly as it found it, and
         reported `moved 0` -- indistinguishable from a cut with nothing to say.
         Only the arm's "want ANY" expectation caught it. The cut now destroys C
         directly after the restore, which is what the bug actually did.
         [[popraise-slice]]
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP = "/tmp/zerobas"
SUB, MAIN = "sub/strheap.asm", "basic/str-engine.asm"
ROW = re.compile(r"^(?:p|j|b|e|s|g|c|ctl)\.")

KNIVES = [
    ("K-VB1 disable the base dispatch", SUB, [
        ("""                cp      '&'
                jp      z,svp_base""",
         """                cp      $00                 ; K-VB1 CUT (restored on exit)
                jp      z,svp_base""")]),
    ("K-VB2 swap the refusal codes", SUB, [
        ("""svp_amperr:
                ld      a,4                 ; SH_ERR 4 -> FPERR 4 -> ERR 2 (syntax)
                jr      svp_berr
svp_bovf:
                ld      a,5                 ; SH_ERR 5 -> FPERR 1 -> ERR 6 (overflow)""",
         """svp_amperr:
                ld      a,5                 ; K-VB2 CUT (restored on exit)
                jr      svp_berr
svp_bovf:
                ld      a,4                 ; K-VB2 CUT (restored on exit)""")]),
    ("K-VB3 clobber the packed base constant", SUB, [
        ("""                pop     bc                  ; count|packed both restored
                inc     de""",
         """                pop     bc                  ; K-VB3 CUT (restored on exit):
                ld      c,0                 ; destroy the packed base constant, so
                                            ; the NEXT digit is validated against a
                                            ; max of 0 -- the first draft's bug,
                                            ; with the count left intact
                inc     de""")]),
]

EXPECT = {
    "K-VB1": {"b.hex", "b.hexlow", "b.oct", "b.bin", "b.hextail", "b.hbig",
              "b.lead", "b.amp", "b.nopfx", "b.hover"},
    "K-VB2": {"b.amp", "b.nopfx", "b.hover"},
    # K-VB3's exact set is left to the run: it is a corruption, not a redirect.
    "K-VB3": None,
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
    base = read_rows(f"{TMP}/vb_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/val_probe.py zb "
              f"> {TMP}/vb_zb_base.out")
        return 2
    fails = []
    print(f"baseline: {len(base)} row(s)\n")

    for name, src, cuts in KNIVES:
        tag = name.split()[0]
        orig = open(src).read()
        if any(orig.count(o) != 1 for o, _ in cuts):
            print(f"{name}: KNIFE BROKEN"); fails.append(name); continue
        restore = lambda o=orig, p=src: open(p, "w").write(o)
        atexit.register(restore)
        try:
            t = orig
            for o, n in cuts:
                t = t.replace(o, n)
            open(src, "w").write(t)
            before = knife_guard.hashes()
            print(f"{name}: planted, rebuilding...")
            moved, after, rc = knife_guard.build(f"{TMP}/vbk_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/val_probe.py zb",
               f"{TMP}/vbk_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/vbk_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        if want is None:
            ok = len(moved_rows) > 0
            print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
                  f"   want ANY (a corruption, not a redirect)   "
                  f"{'OK' if ok else '🔴 MOVED NOTHING'}")
        else:
            ok = set(moved_rows) == want
            print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
                  f"\n  want  {len(want)}: {' '.join(sorted(want))}   "
                  f"{'OK' if ok else '🔴 MISMATCH'}")
        for r in ("b.hex", "b.amp", "b.hover"):
            print(f"    {r}: {base.get(r)!r} -> {cut.get(r)!r}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/vbk_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
