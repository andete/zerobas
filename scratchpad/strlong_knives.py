#!/usr/bin/env python3
r"""D-STRLONG K-SL1..K-SL4 — four claims, four cuts, three source files.

The fix is small and spread across the main/sub boundary, so each part is
separately checkable and NONE of them is allowed to be inert:

  K-SL1  put the CLAMP back (sub/strheap.asm). The over-STRMAX rows must go
         back to 255 / "AAA". Proves the raise is what moves them.
  K-SL2  `ld a,FPERR_STRLONG` -> `ld a,FPERR_STROOM` (basic/str-engine.asm).
         The rows must report ERR 14 again. Proves main's 3-way SH_ERR map is
         load-bearing and not shadowed by the old 2-way fallthrough.
  K-SL3  the `db 15` table entry -> `db 14` (basic/interp.asm). Same visible
         movement by a DIFFERENT site -- proves the dense fperr_to_err slot is
         really the one being indexed, and that FPERR_MISSOP+1 lands on it.
  K-SL5  put the old `ret` back in the error tail (basic/str-engine.asm), i.e.
         leave the fold instead of rejoining it. The four rows with a term
         PENDING to the right of the failing append (`f.len3`, `x.oom3`,
         `x.long4`, `x.longtail`) must go back to `Type mismatch`, and the
         rows with nothing pending (`f.right`, `x.oom2`, `e.256`) must not
         move. That split is the whole claim of §6.
  K-SL4  🔴 THE ONE THAT SCORES THE GREEN ROWS. `e.255` and `e.255x3` are
         legal 255-byte concatenations, green BEFORE and AFTER the fix, so on
         their own they prove nothing. Raising at >= 255 instead of > 255 must
         turn exactly those two red and leave every other row alone. Without
         this arm "the boundary is exact" is a story, not a measurement.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit, for EVERY file a knife touched -- not just the last one.
"""
import atexit, os, re, subprocess, sys

TMP = "/tmp/zerobas"
STRHEAP, STRENG, INTERP = "sub/strheap.asm", "basic/str-engine.asm", "basic/interp.asm"

SL1_CUT = (STRHEAP,
    "                jr      c,sap_toolong       ; D-STRLONG: over STRMAX -> ERR 15, and",
    "                jr      nc,sap_ok\n"
    "                ld      a,255               ; CUT (restored on exit)\n"
    "                jr      sap_ok              ; D-STRLONG: over STRMAX -> ERR 15, and")
SL5_CUT = (STRENG,
    "                jr      sct_cont            ; consume whatever is still pending",
    "                pop     hl                  ; CUT (restored on exit)\n"
    "                pop     de\n"
    "                ld      (STRPTR),de\n"
    "                scf\n"
    "                ret")

KNIVES = [
    # 🔴 K-SL0 IS NOT A FALSIFICATION ARM, IT IS THE DENOMINATOR. The probe grew
    # four rows mid-slice (§6), so "14 DIFF before, 3 after" would be two counts
    # on two different row sets. This reverts BOTH code sites at once and reads
    # the FINAL 20-row set, which is the only like-for-like before/after there is.
    ("K-SL0 revert the whole slice (the before/after denominator)", [SL1_CUT, SL5_CUT]),
    ("K-SL1 put the clamp back", [(STRHEAP,
        "                jr      c,sap_toolong       ; D-STRLONG: over STRMAX -> ERR 15, and",
        "                jr      nc,sap_ok\n"
        "                ld      a,255               ; K-SL1 CUT (restored on exit)\n"
        "                jr      sap_ok              ; D-STRLONG: over STRMAX -> ERR 15, and")]),
    ("K-SL2 mis-map SH_ERR=3", [(STRENG,
        "                ld      a,FPERR_STRLONG     ; SH_ERR=3 -> ERR 15 \"String too long\"",
        "                ld      a,FPERR_STROOM      ; K-SL2 CUT (restored on exit)")]),
    ("K-SL3 mis-point the table slot", [(INTERP,
        "                db      15                  ; FPERR_STRLONG (= FPERR_MISSOP+1, sysvars.inc,",
        "                db      14                  ; K-SL3 CUT (restored on exit)  FPERR_STRLONG (")]),
    ("K-SL5 leave the fold instead of rejoining", [(STRENG,
        "                jr      sct_cont            ; consume whatever is still pending",
        "                pop     hl                  ; K-SL5 CUT (restored on exit)\n"
        "                pop     de\n"
        "                ld      (STRPTR),de\n"
        "                scf\n"
        "                ret")]),
    ("K-SL4 raise one byte early", [(STRHEAP,
        "                jr      c,sap_toolong       ; D-STRLONG: over STRMAX -> ERR 15, and",
        "                jr      c,sap_toolong\n"
        "                cp      255                 ; K-SL4 CUT (restored on exit)\n"
        "                jr      z,sap_toolong       ; D-STRLONG: over STRMAX -> ERR 15, and")]),
]


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


# 🔴 THE FIRST CUT OF THIS PARSER LISTED THE ROW PREFIXES BY HAND -- ("f", "s",
# "e", "v", "d") -- and the probe grew an `x.*` family mid-slice. It then read 16
# of 20 rows and reported K-SL5 as moving ONE row when it moves four: the knife
# was blind to exactly the rows it exists to score, and its verdict line said
# "live arm" while understating the arm by 4x. A row set is a DENOMINATOR; do
# not hardcode it in the reader. [[readout-blind-to-its-own-subject]]
ROW = re.compile(r"^[a-z][a-z0-9]*\.[a-z0-9.]+$")

def read_rows(path):
    rows = {}
    if not os.path.exists(path):
        return rows
    for line in open(path, errors="replace"):
        p = line.split()
        if len(p) >= 2 and ROW.match(p[0]) and not p[0].startswith("ctl."):
            rows[p[0]] = " ".join(p[1:])
    return rows


def main():
    os.makedirs(TMP, exist_ok=True)
    base = read_rows(f"{TMP}/sl_zb_base.out")
    if not base:
        print(f"NO BASELINE: python3 scratchpad/strlong_probe.py zb "
              f"> {TMP}/sl_zb_base.out  first")
        return 2
    print(f"baseline (WITH the fix in): {len(base)} rows\n")

    only = sys.argv[1:]
    results = {}
    for name, cuts in KNIVES:
        if only and name.split()[0] not in only:
            continue
        tag = name.split()[0]
        originals = {f: open(f).read() for f, _, _ in cuts}
        broken = [f for f, old, _ in cuts if originals[f].count(old) != 1]
        if broken:
            print(f"{name}: KNIFE BROKEN -- anchor not unique in {broken}")
            results[name] = None
            continue
        restore = lambda o=dict(originals): [open(f, "w").write(t) for f, t in o.items()]
        atexit.register(restore)
        try:
            for f, old, new in cuts:
                open(f, "w").write(originals[f].replace(old, new))
            print(f"{name}: planted, rebuilding...")
            if sh("make repack-machine", f"{TMP}/slk_{tag}_build.out"):
                print(f"{name}: BUILD FAILED (see {TMP}/slk_{tag}_build.out)")
                results[name] = None
                continue
            sh("python3 scratchpad/strlong_probe.py zb", f"{TMP}/slk_{tag}.out")
        finally:
            restore()
            atexit.unregister(restore)
        cut = read_rows(f"{TMP}/slk_{tag}.out")
        if not cut:
            print(f"{name}: 🔴 NO ROWS READ BACK -- the probe's controls failed or it "
                  f"died; this is NOT 'reddened nothing' (see {TMP}/slk_{tag}.out)")
            results[name] = None
            continue
        moved = sorted(r for r in base if base[r] != cut.get(r))
        results[name] = moved
        print(f"{name}: moved {len(moved)} row(s): {' '.join(moved) or '(none)'}")
        for r in moved:
            print(f"      {r:<10s} {base[r]:>24s}  ->  {cut.get(r)}")
        print()

    sh("make repack-machine", f"{TMP}/slk_restore.out")
    print("=" * 72)
    dead = [n for n, m in results.items() if not m]
    for n, m in results.items():
        print(f"  {n:<34s} {'🔴 REDDENED NOTHING' if not m else str(len(m)) + ' row(s)'}")
    print()
    print("VERDICT:", "every claim has a live arm" if not dead
          else f"🔴 ARMS THAT NEVER FIRED: {dead}")
    return 0 if not dead else 1


if __name__ == "__main__":
    sys.exit(main())
