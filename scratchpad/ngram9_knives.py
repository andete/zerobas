#!/usr/bin/env python3
r"""D-NGRAM9 K-N9A/K-N9B + S1 — three string-target sites, and BOTH of its bails.

  S1     STATIC per-site witness: 0 open-coded runs left, exactly 3 calls, AND
         a positive control that the matcher still finds something.
  K-N9A  put the OLD type-check target back (`type_mismatch_error` ->
         `stmt_error`). Exactly the two numeric-target rows must return to
         ERR 2 -- the divergence this slice closed, re-opened on demand.
  K-N9B  RETARGET the deferred-fault bail (`fp_runtime_error` ->
         `type_mismatch_error`). `s.mid.sub` MUST move ERR 11 -> ERR 13: that is
         what says the bail is REACHED AND TAKEN.
  K-N9C  NOP the deferred-fault bail. **Asserted to move ZERO** -- and the whole
         point of the arm is that the zero has a NAMED CAUSE.

🔴 D-N9BAIL (2026-08-29) OVERTURNED THIS FILE'S OWN PRIOR VERDICT.
K-N9B used to BE the nop, and it was written up as a "declared null, and
structurally so": the bail supposedly changed WHEN the fault was raised and not
WHETHER, with exec_stmt's statement-boundary check raising the same ERR 11 a few
instructions later. That made the bail a 9 B carve candidate. **All of it was
wrong.** Retarget the jump instead of nopping it and `s.mid.sub` moves ERR 11 ->
ERR 13 on the spot, so the bail is taken. The zero came from a SECOND CAUSE OF
GREEN inside the SAME statement, not from the statement boundary at all:
ex_mid_stmt's next act is `eval_pos_arg` -> `get_int16_checked`, which ends
`jp check_fperr_only` and re-raises the still-pending FPERR before the boundary
is ever reached.
🔴 AND THE COVER IS MID$'s ALONE. `inpc_line` (input.asm) and `inp_readvar`
(files.asm) reach their `check_expr_errors` only AFTER `read_line` /
`read_into_strscr` and `tgt_store_str`. Remove the bail and `LINE INPUT
A$(0*(1/0))` WAITS ON THE KEYBOARD where both references raise at once, and both
sites then store through a TGT_ADDR that `tgt_parse`'s `ret nz` never wrote.
🎯 So the carve is DECLINED and the arm is now two: a live one that proves the
bail is taken, and a masked one that asserts its own zero. A knife that reports
"moved 0" for a masked cut and for a broken plant is not telling you which.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

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
    ("K-N9B retarget the deferred-fault bail", [
        ("                jp      nz,fp_runtime_error ; a deferred fault from the subscript",
         "                jp      nz,type_mismatch_error ; K-N9B CUT (restored on exit)")]),
    ("K-N9C nop the deferred-fault bail", [
        ("""                jp      nz,fp_runtime_error ; a deferred fault from the subscript
                ret""",
         """                nop                         ; K-N9C CUT (restored on exit)
                nop
                nop
                ret""")]),
]

# Rows each arm MUST move. A tag mapped to the empty set is a MASKED arm: its
# zero is asserted, with the cause named in the module docstring -- so a plant
# that silently stopped reaching the ROM cannot hide inside it.
EXPECT = {
    "K-N9A": {"s.line.num", "s.mid.num"},
    "K-N9B": {"s.mid.sub"},
    "K-N9C": set(),
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
    # D-N8ARM: EVERY element, not just PAT[0] -- a stale element in any
    # later position made 2 of 7 of these arms vacuous.
    matcher_alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    ok = (open_coded == 0 and jumps == 3 and matcher_alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {open_coded} "
          f"open-coded run(s) left (want 0), {jumps} call(s) to it (want 3), "
          f"matcher{'' if matcher_alive else ' 🔴 STALE: ' + str(stale)} alive")
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
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"   want {' '.join(sorted(want)) or '(none -- MASKED, cause named in the docstring)'}"
              f"   {'OK' if ok else '🔴 MISMATCH'}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/n9k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
