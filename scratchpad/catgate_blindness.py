#!/usr/bin/env python3
r"""Can the two new concatenation gates actually go RED?

`make catterm-acceptance` and `make catusr-acceptance` were added to guard
D-CATFIX (2026-09-01), which nothing in probes/ covered: no gated probe carries
`"AB"+(0*(1/0)+1)` at all. Both probes already exited non-zero on DIFF, so the
gap was never "prints divergences and exits 0" -- it was an honest rc that no
battery collected, which is not an oracle either.

So D-CATFIX is undone three ways and each gate has to notice:

  N1  remove the ONE evaluation      -> the count drops to 0, the code to 13
  N2  arm the wrong error            -> the code changes, the count does not
  N3  decline instead of returning CF=1 -> the driver re-drives

  N0  CONTROL: a comment-only edit -> both gates GREEN, ROM byte-identical

🎯 N1 AND N2 SPLIT THE TWO GATES APART. catusr counts evaluations and catterm
reads error codes; N2 should move catterm and leave catusr alone. If one gate
caught everything the other would be redundant, and if neither distinguished them
the pair would be one gate wearing two names.
"""
import atexit, hashlib, os, signal, subprocess, sys

ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
S = "basic/str-engine.asm"
BAK = ".knifebak"
MUT = {
    "N1": ("                call    eval                ; the ONE evaluation; HL advances past",
           "                                            ; MUTANT: no evaluation", True),
    "N2": ("                ld      a,10                ; type mismatch, unless the operand's",
           "                ld      a,24                ; MUTANT: wrong error armed", True),
    # 🔴 N3's FIRST PLANT WAS WRONG AND THE CODE WAS FINE. It inserted `or a` /
    # `ret` BEFORE the `pop de`, which does not model "decline instead of CF=1"
    # -- it models "return with an unbalanced stack", and the rows still raised
    # the right errors, so both gates stayed green and the arm read FAIL.
    # The real decline is ONE instruction: the `scf` that makes the return
    # success-shaped becomes `or a`, with the stack already balanced. Third
    # mispredicted plant this session (K-PC4, K-PL3, this) -- every one of them a
    # fault in the arm, never in the code under it.
    "N3": ("                scf                         ; success-shaped: no re-drive",
           "                or      a                   ; MUTANT: decline -> re-drive", True),
    "N0": ("; D-CATFIX (2026-09-01, supersedes the BUG C NC-decline that stood",
           "; D-CATFIX (2026-09-01; supersedes the BUG C NC-decline that stood", False),
}


def _restore(verbose=True):
    n = 0
    if os.path.exists(S + BAK):
        os.replace(S + BAK, S); n = 1
        if verbose:
            print(f"🔴 LEFTOVER MUTANT in {S} -- restored from sidecar")
    return n


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        h.update(open(r, "rb").read() if os.path.exists(r) else b"ABSENT")
    return h.hexdigest()[:12]


def gates():
    a = sh("ZEROBAS_REFCACHE=0 caffeinate -i -s make catterm-acceptance",
           "/tmp/zerobas/cgb_term.out")
    b = sh("ZEROBAS_REFCACHE=0 caffeinate -i -s make catusr-acceptance",
           "/tmp/zerobas/cgb_usr.out")
    return a, b


def main():
    if _restore():
        print("   (a previous run was killed; tree repaired)\n")
    atexit.register(_restore, False)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    for r in ROMS:
        if os.path.exists(r):
            os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/cgb_build.out")
    base_hash = rom_hash()
    bt, bu = gates()
    print(f"baseline: roms={base_hash} catterm rc={bt} catusr rc={bu} "
          f"{'GREEN' if not (bt or bu) else '🔴 RED BEFORE ANY MUTANT'}\n")
    if bt or bu:
        return 2
    fails = 0
    for lab, (find, repl, want_red) in sorted(MUT.items()):
        orig = open(S).read()
        if find not in orig:
            print(f"{lab}: SITE NOT FOUND -- NOT scored"); fails += 1; continue
        open(S + BAK, "w").write(orig)
        open(S, "w").write(orig.replace(find, repl, 1))
        for r in ROMS:
            if os.path.exists(r):
                os.remove(r)
        try:
            rc_b = sh("make repack-machine", f"/tmp/zerobas/cgb_{lab}_build.out")
            h = rom_hash()
            moved = h != base_hash
            if want_red and (rc_b != 0 or not moved):
                print(f"{lab}: INERT (rc={rc_b} roms={h}) -- NOT scored")
                fails += 1; continue
            t, u = gates()
            ok = (t or u) if want_red else (not (t or u) and not moved)
            fails += not ok
            print(f"{lab}: roms={h} bytes-{'moved' if moved else 'same'}  "
                  f"catterm={'RED' if t else 'green'}  catusr={'RED' if u else 'green'}"
                  f"   {'PASS' if ok else 'FAIL'}"
                  f"{'' if want_red else '   (control)'}")
        finally:
            open(S, "w").write(orig)
            if os.path.exists(S + BAK):
                os.remove(S + BAK)
            for r in ROMS:
                if os.path.exists(r):
                    os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/cgb_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}\n"
          f"{len(MUT) - fails}/{len(MUT)} mutants scored as intended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
