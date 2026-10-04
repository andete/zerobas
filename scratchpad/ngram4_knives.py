#!/usr/bin/env python3
r"""D-NGRAM4 K-N4A/K-N4B + S1 — four tail sites, and every one must be wired.

  S1     STATIC, and it is the per-site witness: the open-coded 4-instruction
         tail must occur ZERO times and `jp shx_tail`/`jp shx_op_tail` exactly
         FOUR. A site left open-coded behaves identically at runtime, so this is
         the only instrument that sees it. Enumerated at INSTRUCTION level --
         one site carries comment lines inside the run.
  K-N4A  retarget `jp str_eval_ok` in the shared body. EVERY subject row must
         move; the controls that do not go through it must NOT.
  K-N4B  🎯 THE DISCRIMINATING ONE. Drop `ld (SH_OP),a` from the `shx_op_tail`
         entry. The three sites that enter THERE lose their op; the fourth
         (STRING$'s two-arg form, which sets SH_OP itself and jumps straight to
         `shx_tail`) must be UNAFFECTED. If every row moves, the fourth site is
         not really using the second entry the way the source says it is.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD) and PROVE THE CUT REACHED THE ROM
(D-KNIFEROM): knife_guard hashes the images around every plant.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/str-engine.asm"
ROW = re.compile(r"^[a-z][a-z0-9]*\.[a-z0-9.]+$")

KNIVES = [
    ("K-N4A retarget the shared body", [
        # space plan B-3 (C4, 2026-10-04): shx_tail's `pop hl / jp str_eval_ok`
        # became `jr sfi_done` (that tail, shared); the cut replaces the jr, so it
        # still lands on THIS body only, not on INKEY$/slice/sprite's shared exit.
        ("""                call    shx_finish
                jr      sfi_done            ; pop hl (the caller's cursor guard), then""",
         """                call    shx_finish
                pop     hl                  ; K-N4A CUT (restored on exit)
                jp      str_arg_empty""")]),
    ("K-N4B drop the SH_OP store from the second entry", [
        ("""shx_op_tail:
                ld      (SH_OP),a
shx_tail:""",
         """shx_op_tail:                                ; K-N4B CUT (restored on exit)
shx_tail:""")]),
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
    base = read_rows(f"{TMP}/n4_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/ngram4_probe.py zb "
              f"> {TMP}/n4_zb_base.out")
        return 2
    subj = sorted(r for r in base if r.startswith("s."))
    ctrl = sorted(r for r in base if not r.startswith("s."))
    fails = []

    # --- S1: the per-site witness ------------------------------------------
    import ngram_sweep as NS
    st = NS.parse()
    PAT = ["call call_strheap", "call shx_finish", "pop hl", "jp str_eval_ok"]
    ins = [e for e in st if e[0] == "I"]
    open_coded = sum(1 for k in range(len(ins) - 3)
                     if [e[3] for e in ins[k:k + 4]] == PAT
                     and ins[k][1].startswith("basic/"))
    jumps = sum(1 for e in ins if e[3] in ("jp shx_tail", "jp shx_op_tail"))
    ok = (open_coded == 1 and jumps == 4)      # the ONE remaining copy IS the body
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {open_coded} "
          f"open-coded run(s) left (want 1 — the shared body itself), "
          f"{jumps} jump(s) to it (want 4)")
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
            moved, after, rc = knife_guard.build(f"{TMP}/n4k_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh(f"ZEROBAS_REFCACHE=0 python3 scratchpad/ngram4_probe.py zb",
               f"{TMP}/n4k_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/n4k_{tag}.out")
        if not cut:
            print(f"  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}")
        if not moved_rows:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/n4k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
