#!/usr/bin/env python3
r"""D-INSTRTM K-IT1/K-IT2 — the SPLIT and the ORDER, each with its own arm.

  K-IT1  put the shared tail back (`efi_tm_p`/`efi_tm_pa` -> `efi_reject_p`/
         `efi_reject_pa`). Exactly the five rows this slice closed must return
         to ERR 2 -- and the seven that must NOT move had better not.
  K-IT2  🎯 THE ARM THAT MATTERS: arm TYPEMM *BEFORE* evaluating the operand
         instead of after. That is the mirror-image wrong fix D-NGRAM8 made once
         and D-LEFTTM's K-LT2 already pins in another verb: first-error-wins then
         lets the type mismatch BLOCK the operand's real fault. The three
         `t.*num` rows keep reading ERR 13 -- they are CLEAN expressions and
         cannot tell the two fixes apart -- and THREE rows move: `o.pend` and
         `o.pendp` 11 -> 13, plus `m.dangle` 2 -> 13. That third one was NOT
         predicted and is the sharpest of the three; see EXPECT below.
         🔴 A ROW SET WITHOUT `o.pend*` AND `m.dangle` WOULD SCORE THE WRONG
         FIX GREEN.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD) and PROVE THE CUT REACHED THE ROM
(D-KNIFEROM): knife_guard hashes the images around every plant.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/str-engine.asm"
ROW = re.compile(r"^(?:t|m|o|g|ctl)\.")

KNIVES = [
    ("K-IT1 restore the shared tail", [
        ("                jr      nc,efi_tm_p         ; D-INSTRTM: a$ present but NOT a string",
         "                jr      nc,efi_reject_p     ; K-IT1 CUT (restored on exit)"),
        ("                jr      nc,efi_tm_pa        ; D-INSTRTM: b$ present but NOT a string",
         "                jr      nc,efi_reject_pa    ; K-IT1 CUT (restored on exit)")]),
    ("K-IT2 arm the mismatch BEFORE evaluating", [
        ("""                call    eval                ; the operand, numerically -- it arms its
                                            ; OWN fault first if it has one
                ld      e,FPERR_TYPEMM      ; -> ERR 13, unless the operand beat us
                jp      ev_f_defer""",
         """                ld      a,FPERR_TYPEMM      ; K-IT2 CUT (restored on exit): armed
                call    penderr_set         ; FIRST, so it BLOCKS the operand's fault
                call    eval
                ld      e,FPERR_TYPEMM
                jp      ev_f_defer""")]),
]

# Rows each arm MUST move -- an EXPECTED SET, never "did anything move".
# 🔴 I PREDICTED TWO ROWS FOR K-IT2 AND THREE MOVED. The extra one is
# `m.dangle` (`INSTR("AB",)`), and it is the most interesting row in the file.
# It is a MALFORMED shape that reaches the new tail: `str_eval_next` declines on
# the ')', so `efi_tm_pa` runs -- and in the SHIPPED order `call eval` then fails
# on that ')' and defers a SYNTAX error, which first-error-wins keeps. ERR 2,
# correct, and correct BECAUSE the raise comes after the evaluation.
# 🎯 So the ordering is not merely "nicer for pending faults": without it the
# split would have BROKEN a malformed shape that was already right. Three rows
# discriminate the two fixes, not two.
EXPECT = {
    "K-IT1": {"t.a2num", "t.p_anum", "t.p_bnum", "o.pend", "o.pendp"},
    "K-IT2": {"m.dangle", "o.pend", "o.pendp"},
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
    base = read_rows(f"{TMP}/it_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/instrtm_probe.py zb "
              f"> {TMP}/it_zb_base.out")
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
            moved, after, rc = knife_guard.build(f"{TMP}/itk_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/instrtm_probe.py zb",
               f"{TMP}/itk_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/itk_{tag}.out")
        if not cut:
            print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(want)}: {' '.join(sorted(want))}   "
              f"{'OK' if ok else '🔴 MISMATCH'}")
        for r in sorted(want):
            print(f"    {r}: {base.get(r)!r} -> {cut.get(r)!r}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/itk_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
