#!/usr/bin/env python3
r"""D-PUSTAR knives — the WIDTH change and the FILL change are separate claims.

`**##` does two things: it consumes two characters that still COUNT toward the
field width, and it makes the pad character `*`. Three rows went green together,
which is equally consistent with one change doing all the work.

  K-PS1  drop the `inc b / inc b` (asterisks stop counting)  a.basic a.neg a.dot a.full
  K-PS2  pad with a space again (fill flag ignored)          a.basic a.neg a.dot -- NOT a.full

⚠️ ROUND 1 PREDICTED BOTH SETS WITHOUT `a.dot` AND BOTH ARMS READ FAIL. `**#.##`
exercises `**` perfectly well even though its `.` half is still unimplemented, so
killing either half changes that row too. The arms were right and the prediction
was short -- the discriminating evidence (K-PS1 moves `a.full`, K-PS2 does not)
was present in the data either way.

🎯 THE ASYMMETRY IS THE POINT. `a.full` is `**##` with 1234 -- four digits in a
four-wide field, so it emits NO padding at all. Killing the fill cannot touch it;
killing the width makes it overflow to `%1234`. If both arms moved the same rows,
the two claims would be indistinguishable and one of them unproven.

Hashes both ROMs; refuses a probe run with no verdict line.
"""
import hashlib, os, re, subprocess, sys

ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
ARMS = {
    "K-PS1": ("basic/pu-render.inc",
              "                inc     b\n                inc     b\nptf_num_w:",
              "ptf_num_w:", {"a.basic", "a.neg", "a.full", "a.dot"}),
    "K-PS2": ("basic/printusing.asm",
              "                ld      a,'*'\npu_num_pad:",
              "                ld      a,' '\npu_num_pad:", {"a.basic", "a.neg", "a.dot"}),
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
    """{row: zb value}; None if the run produced no table."""
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
    sh("make repack-machine", "/tmp/zerobas/ps_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 scratchpad/pufloat_probe.py vg8020,cf3300,zb",
       "/tmp/zerobas/ps_base.out")
    base = rows("/tmp/zerobas/ps_base.out")
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
            rc = sh("make repack-machine", f"/tmp/zerobas/ps_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h}; DISCARDED"); continue
            sh("caffeinate -i -s python3 scratchpad/pufloat_probe.py vg8020,cf3300,zb",
               f"/tmp/zerobas/ps_{lab}.out")
            got = rows(f"/tmp/zerobas/ps_{lab}.out")
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
    sh("make repack-machine", "/tmp/zerobas/ps_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
