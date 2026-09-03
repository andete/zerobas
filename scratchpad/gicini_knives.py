#!/usr/bin/env python3
r"""D-GICINI knives — falsify the fix by planting, one site at a time.

Four arms, each a SOURCE edit + rebuild + re-measure. An arm that removes a call
must turn its OWN rows red and leave the others green; an arm that keeps MUSICF
but drops the amplitude writes must leave the ROW probe entirely green and be
caught only by the PSG trace.

🔴 EVERY ARM HASHES THE ROM. "moved 0 rows" is what an inert knife and a
legitimately-empty arm look like alike, and 13 runners in this tree still cannot
tell them apart. The base hash is recorded first; an arm whose ROM did not move
is reported as INERT and its row verdict is discarded, not believed.
[[a-knife-can-be-inert-because-the-build-did-not-happen]]

🎯 K-GI4 IS THE POINT OF THE SET. It keeps `ld (MUSICF),a` and deletes only the
amplitude loop. Every row in `gicini_probe.py` reads MUSICF, so every one of them
stays GREEN -- while the machine holds the note forever. If that arm comes back
"no rows moved", the row probe has a blind spot the size of the actual user-
visible symptom, and the PSG trace is the only thing covering it.
"""
import hashlib, os, re, subprocess, sys

ROM = "build/zerobas-main-eu.rom"
ARMS = {
    # label: (file, find, replace, rows that MUST move)
    "K-GI1": ("basic/arrays.asm",
              "                call    psg_silence\n                ld      a,1\n                ld      (ENDFLAG),a         ; D-1",
              "                ld      a,1\n                ld      (ENDFLAG),a         ; D-1",
              {"e.untrap", "e.errnat", "e.errdir"}),
    "K-GI2": ("basic/program.asm",
              "                call    psg_silence\n                ld      a,1\n                ld      (ENDFLAG),a         ; stop the run",
              "                ld      a,1\n                ld      (ENDFLAG),a         ; stop the run",
              {"e.stop", "e.cont"}),
    "K-GI3": ("basic/sound.asm",
              "                call    psg_silence\n                ; The body is a PAGE-0 sub-ROM tenant",
              "                ; The body is a PAGE-0 sub-ROM tenant",
              {"m.beep"}),
    "K-GI4": ("basic/sound.asm",
              "                ld      b,8                 ; R8/R9/R10 = the three tone amplitudes\npsgs_lp:        ld      a,b\n                out     (PSG_ADDR),a        ; latch the amplitude register\n                xor     a\n                out     (PSG_DATW),a        ; amplitude 0\n                inc     b\n                ld      a,b\n                cp      11\n                jr      c,psgs_lp\n",
              "",
              set()),   # deliberately EMPTY: the row probe cannot see this arm
}


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def rom_hash():
    if not os.path.exists(ROM):
        return "ABSENT"
    return hashlib.sha1(open(ROM, "rb").read()).hexdigest()[:12]


def diff_rows(path):
    for line in open(path):
        if line.startswith("DIFF:"):
            return set(line.split()[2:])
    return None


def main():
    sh("make repack-machine", "/tmp/zerobas/knife_build_base.out")
    base_hash = rom_hash()
    print(f"base ROM {base_hash}")
    sh("caffeinate -i -s python3 scratchpad/gicini_probe.py",
       "/tmp/zerobas/knife_base.out")
    base = diff_rows("/tmp/zerobas/knife_base.out")
    print(f"base DIFF rows: {sorted(base) if base is not None else '<UNREADABLE>'}\n")

    for lab, (f, find, repl, want) in ARMS.items():
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: PLANT SITE NOT FOUND in {f} -- arm skipped, NOT green")
            continue
        open(f, "w").write(orig.replace(find, repl, 1))
        try:
            rc = sh("make repack-machine", f"/tmp/zerobas/knife_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} rom={h} (base {base_hash}); "
                      f"row verdict DISCARDED")
                continue
            sh("caffeinate -i -s python3 scratchpad/gicini_probe.py",
               f"/tmp/zerobas/knife_{lab}.out")
            got = diff_rows(f"/tmp/zerobas/knife_{lab}.out")
            if got is None:
                print(f"{lab}: rom={h} <UNREADABLE probe output>")
                continue
            moved = got - base
            ok = moved == want
            print(f"{lab}: rom={h}  moved={sorted(moved) or '<none>'}  "
                  f"want={sorted(want) or '<none>'}  {'PASS' if ok else 'FAIL'}")
        finally:
            open(f, "w").write(orig)
    sh("make repack-machine", "/tmp/zerobas/knife_restore.out")
    print(f"\nrestored ROM {rom_hash()} (base was {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
