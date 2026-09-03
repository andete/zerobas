#!/usr/bin/env python3
r"""D-PUSIGN knife — is the trailing-NEGATIVE move real, or did the six rows go
green on one blunter rule?

`##+` and `##-` do three different things depending on the value's sign, and the
one most easily got wrong is the negative case: the `-` pu_fmt_int wrote at the
FRONT has to MOVE to the end, and it stays `-` even when the specifier is `+`
(measured: `##+` with -5 is ` 5-`, not ` 5+`).

  K-PG1  drop the leading `-` removal, so it is appended without being moved
         -> p.trailneg and n.neg change; p.trail and n.pos MUST NOT.

🎯 THE ROWS THAT MUST NOT MOVE ARE THE CLAIM. If the positive trailing rows moved
too, the arm would only be saying "trailing signs are implemented", which the six
green rows already say.
"""
import hashlib, os, re, subprocess, sys

ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
ARMS = {
    "K-PG1": ("sub/printusing.asm",
              "                ld      hl,NUMBUF+1\n                ld      de,NUMBUF\n"
              "                call    pst_end_hl          ; BC = bytes remaining incl. terminator\n"
              "                ldir\n",
              "", {"p.trailneg", "n.neg"}),
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
    sh("make repack-machine", "/tmp/zerobas/pg_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 scratchpad/pufloat_probe.py vg8020,cf3300,zb",
       "/tmp/zerobas/pg_base.out")
    base = rows("/tmp/zerobas/pg_base.out")
    if base is None:
        print("🔴 BASE RUN UNREADABLE -- refusing to run any arm"); return 2
    print(f"base ROMs {base_hash}   {len(base)} rows read\n")
    for lab, (f, find, repl, want) in ARMS.items():
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: PLANT SITE NOT FOUND in {f} -- arm skipped, NOT green")
            continue
        open(f, "w").write(orig.replace(find, repl, 1))
        for r in ROMS:
            if os.path.exists(r):
                os.remove(r)
        try:
            rc = sh("make repack-machine", f"/tmp/zerobas/pg_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h}; DISCARDED"); continue
            sh("caffeinate -i -s python3 scratchpad/pufloat_probe.py vg8020,cf3300,zb",
               f"/tmp/zerobas/pg_{lab}.out")
            got = rows(f"/tmp/zerobas/pg_{lab}.out")
            if got is None:
                print(f"{lab}: roms={h} 🔴 UNREADABLE run -- NOT scored"); continue
            moved = {k for k in base if got.get(k) != base[k]}
            print(f"{lab}: roms={h}  moved={sorted(moved) or '<none>'}  "
                  f"want={sorted(want)}  {'PASS' if moved == want else 'FAIL'}")
        finally:
            open(f, "w").write(orig)
            for r in ROMS:
                if os.path.exists(r):
                    os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/pg_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
