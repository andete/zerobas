#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-READFLT knives: each cut must move EXACTLY its predicted rows of
probes/basic/basic_probe_readflt.py, judged on the zerobas column against the
uncut build's (three rows are KNOWN divergences, so the verdict cannot be used).

  K-RF1  the tenant's numeric capture cut (`jr rovs_unq` -> `jr rovs_done`)
         -> every row
  K-RF2  VAL's overflow code read as syntax (`cp 5` -> `cp 99`)  -> e99
  K-RF3  a refused item is consumed (the DATAPTR rewind cut)      -> again

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ALL = {"frac", "big", "exp", "neg", "dbl", "int", "intovf", "e99", "junk", "quote",
       "empty", "spaces", "hex", "sign", "again", "dbltyp"}
KNIVES = {
    "K-RF1": ("basic/readdata-body.inc",
              "                ld      b,0\n                jr      rovs_unq\n",
              "                ld      b,0\n                jr      rovs_done           ; K-RF1 CUT\n",
              ALL),
    "K-RF2": ("basic/program.asm",
              "                cp      5                   ; VAL's code 5: `1E99` -> Overflow (6)\n",
              "                cp      99                  ; K-RF2 CUT\n",
              {"e99"}),
    "K-RF3": ("basic/program.asm",
              "                ld      (DATAPTR),hl        ; second READ refuses it again (`again`\n",
              "                nop                         ; K-RF3 CUT\n                nop\n                nop\n",
              {"again"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/basic/basic_probe_readflt.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def zb(log):
    return {m.group(1): m.group(2) for m in
            re.finditer(r"^ROW (\w+) VG=\[.*?\] ZB=\[(.*?)\] ", open(log, errors="replace").read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    sh("make repack-machine", f"{TMP}/rfknife_base_build.out")
    sh(PROBE, f"{TMP}/rfknife_base.out")
    base = zb(f"{TMP}/rfknife_base.out")
    if set(base) != ALL:
        print(f"BASELINE BROKEN: rows {sorted(base)}")
        return 2
    fails = []
    for k, (src, old, new, want) in KNIVES.items():
        orig = open(src).read()
        if orig.count(old) != 1:
            print(f"KNIFE BROKEN: {k} anchor count {orig.count(old)} in {src}")
            return 2
        restore = lambda o=orig, f=src: open(f, "w").write(o)
        atexit.register(restore)
        try:
            open(src, "w").write(orig.replace(old, new))
            before = knife_guard.hashes()
            moved, after, rc = knife_guard.build(f"{TMP}/{k}_build.out", before)
            print(knife_guard.report(k, moved, before, after))
            if rc:
                print(f"{k}: BUILD FAILED with the cut in -- {TMP}/{k}_build.out")
                return 2
            if not moved:
                print(f"{k}: refusing to score an INERT cut")
                return 2
            sh(PROBE, f"{TMP}/{k}_probe.out")
        finally:
            restore()
            atexit.unregister(restore)
        got = {r for r, v in zb(f"{TMP}/{k}_probe.out").items() if v != base.get(r)}
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: moved {sorted(got)} (want exactly {sorted(want)})")
        if not ok:
            fails.append(k)
    sh("make repack-machine", f"{TMP}/rfknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
