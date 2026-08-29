#!/usr/bin/env python3
r"""D-LEFTTM K-LT1/K-LT2 — the order of evaluation IS the fix.

  K-LT1  put the old answer back (`jp ev_f_empty`, FPERR=4). All FIVE rows must
         return to ERR 2 -- the divergence this slice closed.
  K-LT2  🎯 THE ARM THAT MATTERS: arm TYPEMM *BEFORE* evaluating the argument
         instead of after. That is the MIRROR-IMAGE WRONG FIX D-NGRAM8 already
         made once and measured wrong -- first-error-wins then lets the type
         mismatch BLOCK the real fault. The three `.bad` rows keep reading
         ERR 13 (they are clean expressions and cannot tell), and ONLY the two
         `.pexp` rows move, 11 -> 13. A row set that had just the `.bad` rows
         would call this fix green.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD) and PROVE THE CUT REACHED THE ROM
(D-KNIFEROM): knife_guard hashes the images around every plant.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/str-engine.asm"
ROW = re.compile(r"^(?:s|g|ctl)\.")

KNIVES = [
    ("K-LT1 restore the syntax-error answer", [
        ("""                inc     ix                  ; past the selector
                call    ev_sp
                cp      '('
                jr      nz,evff_strnum_tm   ; malformed: no argument to evaluate
                inc     ix
                call    ev_e                ; the argument, numerically -- it arms its
                                            ; OWN fault first if it has one
evff_strnum_tm:
                ld      e,FPERR_TYPEMM      ; -> ERR 13, unless the argument beat us
                jp      ev_f_defer""",
         """                jp      ev_f_empty          ; K-LT1 CUT (restored on exit)""")]),
    ("K-LT2 arm the mismatch BEFORE evaluating", [
        ("""                inc     ix
                call    ev_e                ; the argument, numerically -- it arms its
                                            ; OWN fault first if it has one
evff_strnum_tm:
                ld      e,FPERR_TYPEMM      ; -> ERR 13, unless the argument beat us
                jp      ev_f_defer""",
         """                inc     ix
                ld      a,FPERR_TYPEMM      ; K-LT2 CUT (restored on exit): armed FIRST,
                call    penderr_set         ; so it BLOCKS the argument's own fault
                call    ev_e
evff_strnum_tm:
                ld      e,FPERR_TYPEMM
                jp      ev_f_defer""")]),
]

# Rows each arm MUST move -- an EXPECTED SET, never "did anything move".
EXPECT = {
    "K-LT1": {"s.left.bad", "s.right.bad", "s.mid.bad", "s.left.pexp", "s.mid.pexp"},
    "K-LT2": {"s.left.pexp", "s.mid.pexp"},
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
            rows[p[0]] = " ".join(p[1:]).replace(" SAME", "").replace(" DIFF", "").strip()
    return rows


def main():
    base = read_rows(f"{TMP}/lt_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/ngram8_probe.py zb "
              f"> {TMP}/lt_zb_base.out")
        return 2
    fails = []
    print(f"baseline: {len(base)} row(s)\n")

    for name, cuts in KNIVES:
        tag = name.split()[0]
        orig = open(SRC).read()
        if any(orig.count(o) != 1 for o, _ in cuts):
            print(f"{name}: KNIFE BROKEN"); fails.append(name); continue
        restore = lambda o=orig: open(SRC, "w").write(o)
        atexit.register(restore)
        try:
            t = orig
            for o, n in cuts:
                t = t.replace(o, n)
            open(SRC, "w").write(t)
            before = knife_guard.hashes()
            print(f"{name}: planted, rebuilding...")
            moved, after, rc = knife_guard.build(f"{TMP}/ltk_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/ngram8_probe.py zb",
               f"{TMP}/ltk_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/ltk_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"   want {' '.join(sorted(want))}   {'OK' if ok else '🔴 MISMATCH'}")
        for r in sorted(want):
            print(f"    {r}: {base.get(r)!r} -> {cut.get(r)!r}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/ltk_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
