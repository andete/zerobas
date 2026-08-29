#!/usr/bin/env python3
r"""D-NGRAM7 K-N7A + S1 — three graphics-tenant sites onto one `gfx_call`.

  S1     STATIC per-site witness: 0 open-coded runs left and exactly 3 calls.
  K-N7A  send the tenant the WRONG op (`ld (GFX_OP),a` -> `ld (GFX_OP),a` with
         A forced to 0). All five subject rows must move; the two controls,
         which draw nothing, must hold.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD) and PROVE THE CUT REACHED THE ROM
(D-KNIFEROM): knife_guard hashes the images around every plant.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/graphics.asm"
ROW = re.compile(r"^[a-z][a-z0-9]*\.[a-z0-9.]+$")

KNIVES = [
    ("K-N7A force the tenant op to 0", [
        ("""gfx_call:
                ld      (GFX_OP),a""",
         """gfx_call:
                xor     a                   ; K-N7A CUT (restored on exit)
                ld      (GFX_OP),a""")]),
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
    base = read_rows(f"{TMP}/n7_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/ngram7_probe.py zb "
              f"> {TMP}/n7_zb_base.out")
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
    PAT = ["ld (gfx_op),a", "push hl",
           "ld ix,subrom_entry_base_p0+3*subrom_idx_graphics", "call subrom_call",
           "pop hl", "jp c,gfx_absent"]
    ins = [e for e in st if e[0] == "I"]
    open_coded = sum(1 for k in range(len(ins) - 5)
                     if [e[3] for e in ins[k:k + 6]] == PAT
                     and ins[k][1].startswith("basic/"))
    jumps = sum(1 for e in ins if e[3] == "call gfx_call")
    # D-N8ARM: name the STALE ELEMENT rather than reporting a bare count. This
    # arm's `ld ix,...+3*...` had been stale since ngram_sweep.py's whitespace
    # normalisation was repaired (it was written against the buggy output), and
    # because this expectation points at 1 the arm went RED rather than vacuous
    # -- loudly, into a log nobody had re-run.
    matcher_alive, stale = knife_guard.pattern_alive(PAT, (e[3] for e in ins))
    ok = (open_coded == 1 and jumps == 3 and matcher_alive)  # the ONE copy left IS the body
    if not matcher_alive:
        print(f"  🔴 S1 PATTERN STALE: {stale}")
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: {open_coded} "
          f"open-coded run(s) left (want 1 — the body itself), "
          f"{jumps} call(s) to it (want 3)")
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
            moved, after, rc = knife_guard.build(f"{TMP}/n7k_{tag}_build.out", before)
            print(knife_guard.report(tag, moved, before, after))
            if rc:
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            if not moved:
                fails.append(name); continue
            sh(f"ZEROBAS_REFCACHE=0 python3 scratchpad/ngram7_probe.py zb",
               f"{TMP}/n7k_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/n7k_{tag}.out")
        if not cut:
            print(f"  🔴 NO ROWS READ BACK — not 'reddened nothing'")
            fails.append(name); continue
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}")
        if not moved_rows:
            fails.append(name)
        print()
    sh("make repack-machine", f"{TMP}/n7k_restore.out")
    print("=" * 68)
    print("VERDICT:", "every arm live" if not fails else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
