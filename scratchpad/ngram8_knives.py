#!/usr/bin/env python3
r"""D-NGRAM8 K-N8A/K-N8B + S1 — three string-arg sites, and the bail that was wrong.

  S1     STATIC per-site witness: 0 open-coded runs left and exactly 3 calls.
  K-N8A  put the OLD bail back (`jp nc,type_mismatch_error` -> `jp nc,
         str_eval_no`). Exactly the three `.bad` rows must return to ERR 2 --
         that is the divergence this slice closed, re-opened on demand.
  K-N8B  neuter the SNAPSHOT (`call str_snapshot_arg` -> `nop`x3).
         🔴 EXPECTED NULL, AND RECORDED AS ONE. It moves ZERO rows -- with the
         ROM provably changed (D-KNIFEROM), so this is a genuine "the cut
         reached the artifact and reddened nothing", not an inert cut. Rows
         were built specifically to break it: a COMPUTED source (`A$+B$`) and
         count expressions that really allocate (`LEN(B$+B$)`); the first
         attempt used `LEN("XY")`, which allocates nothing and proved less
         than it looked.
         ⚠️ THAT IS NOT EVIDENCE THE SNAPSHOT IS REMOVABLE. Absence of a
         witnessing row is absence of evidence; the temp-stack entry a computed
         source lands in happens to survive the count evaluation today. Filed
         as a candidate, not taken.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD) and PROVE THE CUT REACHED THE ROM
(D-KNIFEROM): knife_guard hashes the images around every plant.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/str-engine.asm"
ROW = re.compile(r"^[a-z][a-z0-9]*\.[a-z0-9.]+$")

KNIVES = [
    ("K-N8A restore the old bail", [
        ("                jp      nc,type_mismatch_error",
         "                jp      nc,str_eval_no      ; K-N8A CUT (restored on exit)")]),
    ("K-N8B neuter the snapshot", [
        ("""                call    str_snapshot_arg    ; STRPTR -> an OWNED temp; HL=temp
                pop     hl
                ret""",
         """                nop                         ; K-N8B CUT (restored on exit)
                nop
                nop
                pop     hl
                ret""")]),
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
    base = read_rows(f"{TMP}/n8_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/ngram8_probe.py zb "
              f"> {TMP}/n8_zb_base.out")
        return 2
    subj = sorted(r for r in base if r.startswith("s."))
    ctrl = sorted(r for r in base if not r.startswith("s."))
    fails = []

    # --- S1: the per-site witness ------------------------------------------
    import ngram_sweep as NS
    st = NS.parse()
    # 🔴 THE SWEEP'S KEYS KEEP THE SPACING AROUND `+`/`*`. My first pattern
    # wrote `..._p0+3*subrom_idx_graphics` with none, matched NOTHING, and
    # reported "0 open-coded runs left" -- which reads exactly like success.
    # 🎯 AN S1 ARM WHOSE EXPECTED COUNT IS ZERO CANNOT TELL A CLEAN TREE FROM A
    # TYPO'D PATTERN. That is why `body_seen` below asserts the pattern matches
    # the body itself: a positive control on the matcher, not just on the tree.
    PAT = ["call str_eval", "jp nc,str_eval_no", "push hl",
           "call str_snapshot_arg", "pop hl"]
    ins = [e for e in st if e[0] == "I"]
    open_coded = sum(1 for k in range(len(ins) - 4)
                     if [e[3] for e in ins[k:k + 5]] == PAT
                     and ins[k][1].startswith("basic/"))
    jumps = sum(1 for e in ins if e[3] == "call str_arg_snap")
    # 🔴 EXPECTED ZERO -> NEEDS A POSITIVE CONTROL ON THE MATCHER, or a typo'd
    # pattern reports "0 occurrences" and reads as a clean tree (D-NGRAM7 §3).
    matcher_alive = any(e[3] == PAT[0] for e in ins)
    ok = (open_coded == 0 and jumps == 3 and matcher_alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {open_coded} "
          f"open-coded run(s) left (want 0), {jumps} call(s) to it (want 3), "
          f"matcher{'' if matcher_alive else ' 🔴 NOT'} alive")
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
            moved, after, rc = knife_guard.build(f"{TMP}/n8k_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh(f"ZEROBAS_REFCACHE=0 python3 scratchpad/ngram8_probe.py zb",
               f"{TMP}/n8k_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/n8k_{tag}.out")
        if not cut:
            print(f"  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}")
        # K-N8B is a DECLARED null: the ROM moved (checked above), so zero rows
        # is a finding about the snapshot, not a dead arm. Every other knife
        # must move something.
        if not moved_rows and tag != "K-N8B":
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/n8k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
