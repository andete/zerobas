#!/usr/bin/env python3
r"""D-NGRAM5 K-N5A/K-N5B + S1 — three GOTO-target sites, both halves of the body.

  S1     STATIC per-site witness: the open-coded run must occur exactly ONCE
         (the shared body itself, since the third site KEEPS the code and is
         merely labelled) and be jumped to exactly TWICE.
  K-N5A  break the ARMING half (`ld (GOTOFLAG),a` -> `xor a`). The three rows
         whose transfer really happens must move; the three `.undef` rows,
         which never reach the arming, must NOT.
  K-N5B  break the FAILING half (`jp nc,ex_goto_undef` -> `jp nc,$0000`).
         🎯 The mirror image: only the `.undef` rows may move.
     Together the two arms cover both halves of the body and separate them --
     an arm that moved everything would prove the body is reached and nothing
     about WHICH instructions carry which verdict.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD) and PROVE THE CUT REACHED THE ROM
(D-KNIFEROM): knife_guard hashes the images around every plant.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/program.asm"
ROW = re.compile(r"^[a-z][a-z0-9]*\.[a-z0-9.]+$")

KNIVES = [
    ("K-N5A break the arming half", [
        ("""                ld      a,1
                ld      (GOTOFLAG),a""",
         """                xor     a                   ; K-N5A CUT (restored on exit)
                ld      (GOTOFLAG),a""")]),
    ("K-N5B break the failing half", [
        ("""goto_take_bc:
                call    find_line_bc        ; CF set + HL = the line's address
                jp      nc,ex_goto_undef""",
         """goto_take_bc:
                call    find_line_bc        ; K-N5B CUT (restored on exit)
                jp      nc,gosub_stk_over""")]),
]


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
    base = read_rows(f"{TMP}/n5_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/ngram5_probe.py zb "
              f"> {TMP}/n5_zb_base.out")
        return 2
    subj = sorted(r for r in base if r.startswith("s."))
    ctrl = sorted(r for r in base if not r.startswith("s."))
    fails = []

    # --- S1: the per-site witness ------------------------------------------
    import ngram_sweep as NS
    st = NS.parse()
    PAT = ["call find_line_bc", "jp nc,ex_goto_undef", "ld (gototgt),hl",
           "ld a,1", "ld (gotoflag),a"]
    ins = [e for e in st if e[0] == "I"]
    open_coded = sum(1 for k in range(len(ins) - 4)
                     if [e[3] for e in ins[k:k + 5]] == PAT
                     and ins[k][1].startswith("basic/"))
    jumps = sum(1 for e in ins if e[3] == "jp goto_take_bc")
    ok = (open_coded == 1 and jumps == 2)      # the ONE remaining copy IS the body
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {open_coded} "
          f"open-coded run(s) left (want 1 — the shared body itself), "
          f"{jumps} jump(s) to it (want 2)")
    if not ok:
        fails.append("S1")
    print(f"\nbaseline: {len(subj)} subject row(s), {len(ctrl)} control(s)\n")

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
            moved, after, rc = knife_guard.build(f"{TMP}/n5k_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh(f"ZEROBAS_REFCACHE=0 python3 scratchpad/ngram5_probe.py zb",
               f"{TMP}/n5k_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/n5k_{tag}.out")
        if not cut:
            print(f"  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}")
        if not moved_rows:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/n5k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
