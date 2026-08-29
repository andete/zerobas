#!/usr/bin/env python3
r"""D-NGRAM8 K-N8A/K-N8B + S1 — three string-arg sites, and the bail that was wrong.

  S1     STATIC per-site witness: 0 open-coded runs left and exactly 3 calls.
  K-N8A  re-open the FRAME-DEPTH bug: drop `sas_decline`'s `pop af`, so
         str_eval_no's `ret` lands back inside the verb instead of declining out
         of it. The `.pend` rows must move -- that is the breakage this slice
         actually hit and fixed.
  K-N8B  neuter the SNAPSHOT (`call str_snapshot_arg` -> `nop`x3). The three
         `.src` rows must move: the source string is truncated IN PLACE.

🔴 BOTH ARMS WERE WRONG WHEN THIS FILE SHIPPED, AND IN OPPOSITE DIRECTIONS
(found 2026-08-29, D-N8ARM).

K-N8A CUT A STRING THAT WAS NOT IN THE SOURCE. It looked for
`jp nc,type_mismatch_error`; the shipped shape is `jp nc,sas_decline`, because
the `pop af` fix landed AFTER this arm was written and nobody re-ran the file
against the final source. It has reported `KNIFE BROKEN` ever since -- loudly,
into a log nobody read. 🔴 And its stated claim was false as well: *"exactly the
three `.bad` rows must return to ERR 2 -- the divergence this slice closed"*.
D-NGRAM8 closed no such thing; `.bad` reads ERR 2 on this tree TODAY and the
divergence is filed open in TODO.md. The arm was describing D-NGRAM9's fix.
[[a-justification-parenthesis-is-an-unrun-claim]]

K-N8B WAS RECORDED AS AN "EXPECTED NULL" -- moving zero rows with the ROM
provably changed, which was read as *the cut reached the artifact and reddened
nothing*. It was a ROW-GEOMETRY HOLE. Every row in the probe printed the
FUNCTION'S RESULT and nothing read the SOURCE back afterwards, so in-place
truncation of the source -- the exact damage the snapshot prevents -- could not
appear: `LEFT$(A$,2)` returns `AB` whether or not it wrecked `A$` on the way.
Three rows that read `C$+"/"+A$` make it move immediately. The snapshot is
LOAD-BEARING; the filed carve candidate is DECLINED.
[[a-coverage-row-whose-geometry-cannot-reach-the-case]]

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD) and PROVE THE CUT REACHED THE ROM
(D-KNIFEROM): knife_guard hashes the images around every plant.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/str-engine.asm"
ROW = re.compile(r"^[a-z][a-z0-9]*\.[a-z0-9.]+$")

KNIVES = [
    ("K-N8A re-open the frame-depth bug", [
        ("                pop     af                  ; discard str_arg_snap's return address",
         "                nop                         ; K-N8A CUT (restored on exit)")]),
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

# Rows each arm MUST move -- an EXPECTED SET, not "did anything move". Both of
# this file's arms were wrong for a year of nobody re-reading them; a count is
# what let that happen.
EXPECT = {
    "K-N8A": {"s.left.pend", "s.right.pend", "s.mid.pend"},
    "K-N8B": {"s.left.src", "s.right.src", "s.mid.src"},
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
    PAT = ["call str_eval", "jp nc,sas_decline", "push hl",
           "call str_snapshot_arg", "pop hl"]
    ins = [e for e in st if e[0] == "I"]
    open_coded = sum(1 for k in range(len(ins) - 4)
                     if [e[3] for e in ins[k:k + 5]] == PAT
                     and ins[k][1].startswith("basic/"))
    jumps = sum(1 for e in ins if e[3] == "call str_arg_snap")
    # 🔴 D-N8ARM (2026-08-29): THIS ARM WANTED **0**, AND THAT WAS THE BUG.
    # PAT's second element was `jp nc,str_eval_no` -- a form the `pop af` fix had
    # already replaced with `jp nc,sas_decline`. It matched nothing, reported 0,
    # and passed: a vacuous arm that read exactly like a clean tree. With the
    # element repaired the pattern matches ONE run -- `str_arg_snap`'s OWN BODY,
    # which is the surviving copy, the same shape ngram7's arm already had. So
    # the honest expectation is 1, and a SECOND match is a site that got
    # re-open-coded.
    # 🟢 And the control now checks EVERY element, not just PAT[0]: the D-NGRAM7
    # control only validated the first, so a stale element anywhere after it
    # still passed.
    matcher_alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    ok = (open_coded == 1 and jumps == 3 and matcher_alive)
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {open_coded} "
          f"open-coded run(s) left (want 1 = the helper body itself), {jumps} "
          f"call(s) to it (want 3), "
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
        want = EXPECT[tag]
        ok = set(moved_rows) == want
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"   want {' '.join(sorted(want))}   {'OK' if ok else '🔴 MISMATCH'}")
        if not ok:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/n8k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
