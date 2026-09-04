#!/usr/bin/env python3
r"""Can `make namegate-acceptance` go RED -- in BOTH directions?

A pinned face has to redden on drift EITHER WAY. A regression is the obvious
half; the half that gets forgotten is a row being FIXED while its pin still says
it diverges, which is how a fixed row goes back to looking normal.

  P1  revert D-NAMEORD's reorder            -> name.as5 regresses  -> RED
  P2  set the pin to the FIXED pair, ROM untouched -> pin drift     -> RED
      (and the ROM is ASSERTED byte-identical, not assumed: that is the claim)
  P0  CONTROL: a comment-only edit          -> GREEN, ROM byte-identical

🎯 P2 IS THE POINT OF THE WHOLE FILE. P1 alone would be satisfied by an ordinary
"does it still diverge" check -- the kind `filed_row_sweep` already does, and the
kind that missed three stale faces on 2026-09-04.
"""
import atexit, hashlib, os, signal, subprocess, sys

ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
F, G = "basic/files.asm", "probes/basic/basic_probe_namegate.py"
BAK = ".knifebak"
MUT = {
    "P1": (F, "                ld      (FN_RESUME),hl      ; park the cursor: the new-name text",
           "                call    fname_expr          ; MUTANT: evaluate early again",
           True, True),
    "P2": (G, '"name.ex5": ("13", "2"),',
           '"name.ex5": ("13", "13"),   # MUTANT: the pin says FIXED', True, False),
    "P0": (F, "; ✅ FIXED 2026-09-04 (D-NAMEORD): the new name is now evaluated",
           "; ✅ FIXED 2026-09-04 (D-NAMEORD). The new name is now evaluated", False, True),
}


def _restore(v=True):
    n = 0
    for f in {m[0] for m in MUT.values()}:
        if os.path.exists(f + BAK):
            os.replace(f + BAK, f); n += 1
            if v:
                print(f"🔴 LEFTOVER MUTANT in {f} -- restored")
    return n


def sh(c, o):
    with open(o, "w") as fh:
        return subprocess.call(c, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        h.update(open(r, "rb").read() if os.path.exists(r) else b"ABSENT")
    return h.hexdigest()[:12]


def gate():
    return sh("ZEROBAS_REFCACHE=0 caffeinate -i -s make namegate-acceptance",
              "/tmp/zerobas/ngb_gate.out")


def main():
    if _restore():
        print("   (a previous run was killed; tree repaired)\n")
    atexit.register(_restore, False)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    for r in ROMS:
        if os.path.exists(r):
            os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/ngb_build.out")
    base, rc0 = rom_hash(), gate()
    print(f"baseline: roms={base} gate rc={rc0} "
          f"{'GREEN' if rc0 == 0 else '🔴 RED BEFORE ANY MUTANT'}\n")
    if rc0:
        return 2
    fails = 0
    for lab, (f, find, repl, want_red, is_rom) in sorted(MUT.items()):
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: SITE NOT FOUND in {f} -- NOT scored"); fails += 1; continue
        open(f + BAK, "w").write(orig)
        open(f, "w").write(orig.replace(find, repl, 1))
        # 🔴 REBUILD FOR EVERY ARM, INCLUDING THE PROBE-ONLY ONE. The first cut
        # skipped it when is_rom was False -- but the PREVIOUS arm's cleanup had
        # deleted the ROMs, so P2 hashed ABSENT files and printed "bytes-moved"
        # for an arm that touches no assembly at all. P2's entire claim is "the
        # gate reddens with the ROM BYTE-IDENTICAL", and that was the one thing
        # the readout was not checking.
        for r in ROMS:
            if os.path.exists(r):
                os.remove(r)
        sh("make repack-machine", f"/tmp/zerobas/ngb_{lab}_build.out")
        try:
            h = rom_hash()
            moved = h != base
            if want_red and is_rom and not moved:
                print(f"{lab}: INERT -- NOT scored"); fails += 1; continue
            if not is_rom and moved:
                print(f"{lab}: 🔴 ROM MOVED on a probe-only arm -- NOT scored")
                fails += 1; continue
            rc = gate()
            ok = (rc != 0) if want_red else (rc == 0 and not moved)
            fails += not ok
            print(f"{lab}: roms={h} bytes-{'moved' if moved else 'same'}  "
                  f"gate={'RED' if rc else 'GREEN'}   {'PASS' if ok else 'FAIL'}"
                  f"{'' if want_red else '   (control)'}")
        finally:
            open(f, "w").write(orig)
            if os.path.exists(f + BAK):
                os.remove(f + BAK)
            if is_rom:
                for r in ROMS:
                    if os.path.exists(r):
                        os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/ngb_restore.out")
    print(f"\nrestored {rom_hash()} (base {base}) "
          f"{'OK' if rom_hash() == base else '*** MISMATCH ***'}\n"
          f"{len(MUT) - fails}/{len(MUT)} mutants scored as intended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
