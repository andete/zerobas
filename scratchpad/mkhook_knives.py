#!/usr/bin/env python3
r"""D-MKHOOK knives — is the hook actually load-bearing, or does MKI$ just work?

The gate went from 8 pinned divergences to 5 and `nodisk-acceptance` passes. That
is consistent with the hook working -- and equally consistent with MKI$ having
started raising ERR 5 on the diskless build for some unrelated reason, with the
disk build unaffected because it never needed the hook at all.

TWO ARMS, EACH KILLING ONE HALF OF THE MECHANISM:
  K-MH1  disk/init.asm no longer INSTALLS H.MKI$  -> the slot stays C-BIOS's
         `ret`, so even the DISK build must lose MKI$ (k.mki/v.mkifld/k.cvi go
         ERR 5 on zb-disk too).
  K-MH2  hk_mki returns CF CLEAR (`or a` instead of `scf`) -> installed, reached,
         but signalling "not handled". Same visible outcome as K-MH1 on the disk
         side, reached by a completely different route: it proves the CF
         convention carries the answer, not merely the presence of a stub.

🎯 IF EITHER ARM MOVES NOTHING, THE HOOK IS DECORATION and the ERR 5 came from
somewhere else entirely.

Every arm hashes BOTH ROMs -- the plant is in disk.rom, and a guard watching only
the main ROM would call K-MH1 inert (the mistake the D-MKSD knives made).
"""
import hashlib, os, re, subprocess, sys, time

ROMS = ("build/zerobas-main-eu.rom", "build/disk.rom")
ARMS = {
    "K-MH1": ("disk/init.asm",
              "                ld      hl, H_MKI\n                ld      de, hk_mki\n                call    install_hook\n",
              "", {"k.mki", "v.mkifld", "k.cvi"}),
    "K-MH2": ("disk/kernel.asm",
              "hk_mki:\n                scf\n                ret\n",
              "hk_mki:\n                or      a\n                ret\n",
              {"k.mki", "v.mkifld", "k.cvi"}),
}


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        h.update(open(r, "rb").read() if os.path.exists(r) else b"ABSENT")
    return h.hexdigest()[:12]


def disk_side(path):
    """rows where zb-DISK disagrees with the vg8020 oracle -- the arm's subject.

    🔴 RETURNS None ON AN UNREADABLE RUN. A preflight refusal prints an
    explanation and NO table, and an empty table read as data means "agrees
    everywhere" -- which is how this harness reported all 8 rows moving off a
    run that measured nothing at all."""
    txt = open(path).read()
    if "APPARATUS FAILURE" in txt or "NODISK:" not in txt:
        return None
    out = set()
    for line in open(path):
        m = re.match(r'\s*(\S+)\s+(\'[^\']*\'|\S+)\s+(\'[^\']*\'|\S+)\s+', line)
        if m and m.group(1)[1:2] == '.':
            row, ref, dsk = m.group(1), m.group(2), m.group(3)
            if ref != dsk:
                out.add(row)
    return out


def main():
    sh("make repack-machine", "/tmp/zerobas/mh_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 probes/basic/basic_probe_nodisk.py",
       "/tmp/zerobas/mh_base.out")
    base = disk_side("/tmp/zerobas/mh_base.out")
    if base is None:
        print("🔴 BASE RUN UNREADABLE -- refusing to run any arm"); return 2
    print(f"base ROMs {base_hash}   zb-disk differs from oracle on: {sorted(base)}\n")
    for lab, (f, find, repl, want) in ARMS.items():
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: PLANT SITE NOT FOUND in {f} -- arm skipped, NOT green")
            continue
        open(f, "w").write(orig.replace(find, repl, 1))
        # 🔴 NO MTIME GAMES AT ALL -- DELETE THE ROMS AND LET make REBUILD.
        # Two rounds were lost to this. Stamping the RESTORE forward (D-MKSD's
        # lesson) left files dated in the FUTURE, so the next arm's plant looked
        # OLDER than the ROM and make skipped it -> INERT. Stamping the PLANT
        # forward too then made the SOURCE permanently newer than the built ROM,
        # so `probes/lib/omsx_preflight` correctly REFUSED to measure -- and the
        # scorer below read that refusal page as "agrees on everything" and
        # reported all 8 rows moving. Removing the artefact is unambiguous.
        for r in ROMS:
            if os.path.exists(r):
                os.remove(r)
        try:
            rc = sh("make repack-machine", f"/tmp/zerobas/mh_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h} (base {base_hash}); DISCARDED")
                continue
            sh("caffeinate -i -s python3 probes/basic/basic_probe_nodisk.py",
               f"/tmp/zerobas/mh_{lab}.out")
            got = disk_side(f"/tmp/zerobas/mh_{lab}.out")
            if got is None:
                print(f"{lab}: roms={h} 🔴 UNREADABLE probe run (preflight refused "
                      "or no verdict line) -- NOT scored"); continue
            # 🔴 THE DIRECTION IS `base - got`, AND ROUND 1 HAD IT BACKWARDS.
            # zb-disk SHOULD differ from the DISKLESS oracle at base -- it has a
            # disk, so MKI$ works where the VG-8020 raises ERR 5. Killing the hook
            # makes zb-disk STOP differing (it starts raising ERR 5 too). Looking
            # for newly-DIFFERING rows therefore found nothing and failed both arms
            # on a fix that was already correct -- the same inverted-subject mistake
            # in a knife harness for the third time today.
            moved = base - got
            print(f"{lab}: roms={h}  zb-disk LOST the verb on {sorted(moved) or '<none>'}  "
                  f"want={sorted(want)}  {'PASS' if moved == want else 'FAIL'}")
        finally:
            open(f, "w").write(orig)
            for r in ROMS:
                if os.path.exists(r):
                    os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/mh_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
