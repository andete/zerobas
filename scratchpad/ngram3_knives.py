#!/usr/bin/env python3
r"""D-NGRAM3 K-N3A/K-N3B — five lineedit sites, and every one of them must move.

🔴 THE HAZARD THIS SLICE ACTUALLY HAS is not "the helper is wrong" -- it is "one
of the six sites was never rewired". A site left open-coded behaves IDENTICALLY,
so every row stays green and the byte saving silently comes up short. A knife on
the helper is what turns that into a visible failure: retarget the helper and
EVERY site's own row must move. A row that does not move names the site that was
missed.

  S1     🎯 THE PER-SITE WITNESS IS STATIC, AND IT HAS TO BE. See below.
  K-N3A  `ld a,(LE_STATUS)` -> `ld a,7` in le_call. EVERY row moves, controls
         INCLUDED -- and that is the prediction, not a failure. The line STORE is
         one of the five sites and this harness TYPES its own program through it,
         so a broken le_call takes the fixture with it. 🔴 THERE IS NO CONTROL ON
         THIS APPARATUS THAT SURVIVES A KNIFE ON le_call, and saying so is worth
         more than a control set that pretends otherwise. What this arm proves is
         that the helper is load-bearing -- nothing about which SITES call it.
  K-N3B  delete `ld (LE_OP),a` from the `le_call_op` entry. Same reach, same
         reason: the STORE drives the wrong op and the fixture collapses.

🔴 SO THE "WAS EVERY SITE REWIRED?" QUESTION IS ANSWERED STATICALLY (S1), which
is the RIGHT instrument for it: the open-coded 5-instruction run must occur ZERO
times in the tree, and `call le_call`/`call le_call_op` exactly five. That is an
exact enumeration at INSTRUCTION level (scratchpad/ngram_sweep.py's parser --
comment lines sit inside the sequence at one site, so a line-based grep is wrong
here as it was in D-NGRAM2), and a site left open-coded fails it immediately --
which is the failure a runtime knife cannot see.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): try/finally AND atexit.
"""
import atexit, hashlib, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard   # D-KNIFEROM: ONE implementation, not three

TMP, SRC = "/tmp/zerobas", "basic/program.asm"

KNIVES = [
    ("K-N3A retarget the status byte", [
        ("""                ld      a,(LE_STATUS)
                or      a
                ret""",
         """                ld      a,7                 ; K-N3A CUT (restored on exit)
                or      a
                ret""")]),
    ("K-N3B drop the LE_OP store", [
        ("""le_call_op:
                ld      (LE_OP),a
le_call:""",
         """le_call_op:                                 ; K-N3B CUT (restored on exit)
le_call:""")]),
]

ROW = re.compile(r"^[a-z][a-z0-9]*\.[a-z0-9.]+$")


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
    base = read_rows(f"{TMP}/ng3_zb_base.out")
    if not base:
        print(f"NO BASELINE: python3 scratchpad/ngram3_probe.py zb > {TMP}/ng3_zb_base.out")
        return 2
    subj = sorted(r for r in base if r.startswith("s."))
    ctrl = sorted(r for r in base if not r.startswith("s."))
    print(f"baseline: {len(subj)} subject row(s), {len(ctrl)} control(s)\n")
    fails = []

    # --- S1: the per-site witness ------------------------------------------
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ngram_sweep as NS
    st = NS.parse()
    PAT = ["ld ix,subrom_entry_base_p1+3*subrom_idx_lineedit", "call subrom_call",
           "jp c,subrom_absent_error", "ld a,(le_status)", "or a"]
    ins = [e for e in st if e[0] == "I"]
    open_coded = sum(1 for k in range(len(ins) - 4)
                     if [e[3] for e in ins[k:k + 5]] == PAT)
    calls = sum(1 for e in ins if e[3] in ("call le_call", "call le_call_op")
                and e[1].startswith("basic/"))
    ok = (open_coded == 0 and calls == 5)
    print(f"{'PASS' if ok else 'FAIL'}  S1 every site rewired: "
          f"{open_coded} open-coded copy(ies) left (want 0), "
          f"{calls} call(s) to the helper (want 5)")
    if not ok:
        fails.append("S1 every site rewired")
    print()

    for name, cuts in KNIVES:
        tag = name.split()[0]
        orig = open(SRC).read()
        bad = [o for o, _ in cuts if orig.count(o) != 1]
        if bad:
            print(f"{name}: KNIFE BROKEN -- anchor not unique"); fails.append(name); continue
        restore = lambda o=orig: open(SRC, "w").write(o)
        atexit.register(restore)
        try:
            t = orig
            for o, n in cuts:
                t = t.replace(o, n)
            open(SRC, "w").write(t)
            before = knife_guard.hashes()
            print(f"{name}: planted, rebuilding...")
            if sh("make repack-machine", f"{TMP}/n3k_{tag}_build.out"):
                print(f"{name}: BUILD FAILED"); fails.append(name); continue
            after = knife_guard.hashes()
            # 🔴 A KNIFE CAN BE SILENTLY INERT BECAUSE THE BUILD DID NOT HAPPEN.
            # Writing the source and immediately running `make` can leave the
            # previous ROM in place, and then the probe measures the UNCUT
            # machine -- which reports as "moved 0 rows", i.e. exactly what a
            # knife with nothing to say looks like. It cost a wrong reading on
            # this very slice: one run had K-NG2 reproduce K-NG1's answers
            # byte-for-byte. The ROM hash MUST move when a cut is planted.
            if after == before:
                print(f"{name}: 🔴 KNIFE INERT -- the ROM did not change "
                      f"({before}); the probe would measure the UNCUT machine")
                fails.append(name); continue
            print(f"  ROM {before}  ->  {after}")
            sh("ZEROBAS_REFCACHE=0 python3 scratchpad/ngram3_probe.py zb",
                   f"{TMP}/n3k_{tag}.out")
        finally:
            restore(); atexit.unregister(restore)
        cut = read_rows(f"{TMP}/n3k_{tag}.out")
        if not cut:
            print(f"{name}: 🔴 NO ROWS READ BACK -- not 'reddened nothing'")
            fails.append(name); continue
        moved = {r for r in base if base[r] != cut.get(r)}
        want = set(base)          # every row, controls included -- see the header
        missing, extra = sorted(want - moved), sorted(moved - want)
        print(f"  moved {len(moved)}: {' '.join(sorted(moved)) or '(none)'}")
        if missing:
            print(f"  🔴 DID NOT MOVE (site not wired to the helper?): {' '.join(missing)}")
            fails.append(name)
        if extra:
            print(f"  🔴 MOVED BUT SHOULD NOT HAVE: {' '.join(extra)}")
            fails.append(name)
        if not missing and not extra:
            held = sorted(set(ctrl) - moved)
            print(f"  ✅ exactly the {len(want)} predicted row(s) moved"
                  + (f", {len(held)} control(s) held" if held else
                     f" — INCLUDING all {len(ctrl)} controls, as the header "
                     f"predicts: the line STORE is one of the five sites"))
        print()
    sh("make repack-machine", f"{TMP}/n3k_restore.out")
    print("=" * 66)
    print("VERDICT:", "every site has its own live witness" if not fails
          else f"🔴 {sorted(set(fails))}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
