#!/usr/bin/env python3
r"""D-PUNUM knife — rendering floats and rounding half-up are two claims.

Four rows went green together. That is equally consistent with ONE change doing
all the work: if simply reaching the float formatter were enough, the rounding
code would be decoration.

  K-PN1  make the renderer TRUNCATE (never take the half-up branch)
         -> c.round, c.round2, d.roundup move;  c.over16 MUST NOT.

🎯 `c.over16` IS THE DISCRIMINATOR. `USING"#######";1234567` has no fraction at
all, so rounding cannot touch it -- only reaching the float path can. If it moved
too, the arm would be saying "the tenant is wired up", which the four green rows
already say.
"""
import hashlib, os, re, subprocess, sys

ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
ARMS = {
    "K-PN1": ("sub/punum.asm",
              "                cp      '5'\n                jr      c,pnt_point         ; below half -> plain truncation",
              "                jr      pnt_point           ; KNIFE: always truncate",
              {"c.round", "c.round2", "d.roundup"},   # MUST move
              {"c.over16"}),                          # MUST NOT move
}


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        h.update(open(r, "rb").read() if os.path.exists(r) else b"ABSENT")
    return h.hexdigest()[:12]


def rows(path):
    txt = open(path).read()
    if "references agree on" not in txt:
        return None
    out = {}
    for line in txt.splitlines():
        m = re.match(r"^(\S+)\s+('.*?')\s+('.*?')\s+('.*?')\s", line)
        if m:
            out[m.group(1)] = m.group(4)
    return out or None


def main():
    for r in ROMS:
        if os.path.exists(r):
            os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/pn_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 scratchpad/pufloat_probe.py vg8020,cf3300,zb",
       "/tmp/zerobas/pn_base.out")
    base = rows("/tmp/zerobas/pn_base.out")
    if base is None:
        print("🔴 BASE RUN UNREADABLE -- refusing to run any arm"); return 2
    print(f"base ROMs {base_hash}   {len(base)} rows read\n")
    for lab, (f, find, repl, want, keep) in ARMS.items():
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: PLANT SITE NOT FOUND in {f} -- arm skipped, NOT green")
            continue
        open(f, "w").write(orig.replace(find, repl, 1))
        for r in ROMS:
            if os.path.exists(r):
                os.remove(r)
        try:
            rc = sh("make repack-machine", f"/tmp/zerobas/pn_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h}; DISCARDED"); continue
            sh("caffeinate -i -s python3 scratchpad/pufloat_probe.py vg8020,cf3300,zb",
               f"/tmp/zerobas/pn_{lab}.out")
            got = rows(f"/tmp/zerobas/pn_{lab}.out")
            if got is None:
                print(f"{lab}: roms={h} 🔴 UNREADABLE run -- NOT scored"); continue
            moved = {k for k in base if got.get(k) != base[k]}
            # 🎯 SCORE THE DISCRIMINATION, NOT AN EXACT SET. Twice this session an
            # exact-set arm read FAIL because rows that were ALREADY WRONG changed
            # too -- truncating instead of rounding moves every fractional row,
            # including the ten still waiting on `.`. That is noise. The claim is:
            # the rounding rows MOVE and the no-fraction row does NOT.
            ok = want <= moved and not (keep & moved)
            print(f"{lab}: roms={h}\n"
                  f"    moved   {sorted(moved) or '<none>'}\n"
                  f"    must-move {sorted(want)} -> {'yes' if want <= moved else 'NO'}\n"
                  f"    must-hold {sorted(keep)} -> "
                  f"{'held' if not (keep & moved) else 'MOVED'}   "
                  f"{'PASS' if ok else 'FAIL'}")
        finally:
            open(f, "w").write(orig)
            for r in ROMS:
                if os.path.exists(r):
                    os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/pn_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
