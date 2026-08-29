#!/usr/bin/env python3
r"""D-NGRAM9 K-N9A/K-N9B + S1 — three string-target sites, and BOTH of its bails.

  S1     STATIC per-site witness: 0 open-coded runs left, exactly 3 calls, AND
         a positive control that the matcher still finds something.
  K-N9A  put the OLD type-check target back (`type_mismatch_error` ->
         `stmt_error`). Exactly the two numeric-target rows must return to
         ERR 2 -- the divergence this slice closed, re-opened on demand.
  K-N9B  break the DEFERRED-FAULT bail (`jp nz,fp_runtime_error` -> `nop`x3).
         🔴 DECLARED NULL, AND STRUCTURALLY SO. It moves ZERO rows, with the ROM
         provably changed. The reason is not a missing row: that bail changes
         WHEN the fault is raised, not WHETHER. Nop it and the fault stays
         pending, and exec_stmt's statement-boundary check raises the SAME
         ERR 11 a few instructions later -- so no differential row can separate
         them, because the machine's observable behaviour is identical.
         ⚠️ That makes the three `jp nz,fp_runtime_error` at these sites a 9 B
         CANDIDATE, filed and not taken: "no row can see it" is a statement
         about the row set only if the difference is observable at all, and here
         it may genuinely not be. Reading the exec_stmt contract settles it,
         not another knife.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD) and PROVE THE CUT REACHED THE ROM
(D-KNIFEROM): knife_guard hashes the images around every plant.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/interp.asm"
ROW = re.compile(r"^[a-z][a-z0-9]*\.[a-z0-9.]+$")

KNIVES = [
    ("K-N9A restore the old type-check target", [
        ("                jp      z,type_mismatch_error   ; D-NGRAM9: BOTH REFERENCES ANSWER",
         "                jp      z,stmt_error        ; K-N9A CUT (restored on exit)")]),
    ("K-N9B break the deferred-fault bail", [
        ("""                jp      nz,fp_runtime_error ; a deferred fault from the subscript
                ret""",
         """                nop                         ; K-N9B CUT (restored on exit)
                nop
                nop
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
    base = read_rows(f"{TMP}/n9_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/ngram9_probe.py zb "
              f"> {TMP}/n9_zb_base.out")
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
    PAT = ["call var_str_type", "or a", "jp z,stmt_error", "call tgt_parse",
           "jp nz,fp_runtime_error"]
    ins = [e for e in st if e[0] == "I"]
    open_coded = sum(1 for k in range(len(ins) - 4)
                     if [e[3] for e in ins[k:k + 5]] == PAT
                     and ins[k][1].startswith("basic/"))
    jumps = sum(1 for e in ins if e[3] == "call str_target_parse")
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
            moved, after, rc = knife_guard.build(f"{TMP}/n9k_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh(f"ZEROBAS_REFCACHE=0 python3 scratchpad/ngram9_probe.py zb",
               f"{TMP}/n9k_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/n9k_{tag}.out")
        if not cut:
            print(f"  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}")
        # K-N8B is a DECLARED null: the ROM moved (checked above), so zero rows
        # is a finding about the snapshot, not a dead arm. Every other knife
        # must move something.
        if not moved_rows and tag != "K-N9B":
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/n9k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
