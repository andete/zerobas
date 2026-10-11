#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASWBRK knives: each cut must move EXACTLY its predicted rows of
probes/basic/basic_probe_caswbrk.py, judged on the zerobas column (the VG-8020
column does not move with our ROM, so only our side is run).

  K-CW1  TAPOUT's BREAKX test cut (the write ignores Ctrl-STOP again)
         -> dcsave pcsave pbsave psave pprint phold
  K-CW2  tapout_brk's wait for the release cut -> the handler, entered with the
         key down, breaks at its first statement
         -> pcsave pbsave psave pprint phold
  K-CW3  cas_ascii_save's DIRECTF set cut (ERL 15, not 65535) -> psave
  K-CW4  sv_tenant's raise of SV_STAT 19 cut (back to disk_error -> `load
         error`, returned) -> dcsave pcsave pbsave phold (the tenant's verbs)
  K-CW5  cas_flush_block's `jp c,dpl_dio` cut -> psave pprint (the data flush)

🔴 RESTORE ON EVERY EXIT: originals in memory, put back by try/finally AND
atexit; knife_guard proves the cut reached the installed ROM. A run with rows
missing refuses (D-KNIFEROWS).
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
# 🔴 A FRESH PROCESS PER READING, AND A CLEAN BUILD PER CUT. The first cut of this
# runner imported the probe and called it in-process: the refcache memoises the
# ROM identity per process (omsx_repl's hit path says knife runners must not), so
# K-CW1's eight readings were served from the cache -- `moved []` -- and, being
# instant, let K-CW2's edit land in the same second as the last build, which
# `make` then did not see (knife_guard refused it as INERT).
ALL = {"dcsave", "pcsave", "pbsave", "psave", "pprint", "pleader", "pctl", "phold"}
KNIVES = {
    "K-CW1": ("tape/tape.asm",
              "                call    BREAKX          ; CF = Ctrl-STOP held\n"
              "                jr      c,tapout_brk\n",
              "",
              {"dcsave", "pcsave", "pbsave", "psave", "pprint", "phold"}),
    "K-CW2": ("tape/tape.asm",
              "tapout_brk:\n                call    BREAKX\n"
              "                jr      c,tapout_brk    ; Ctrl-STOP still down\n",
              "tapout_brk:\n",
              {"pcsave", "pbsave", "psave", "pprint", "phold"}),
    "K-CW3": ("basic/save.asm",
              "                ld      a,1\n                ld      (DIRECTF),a\n",
              "",
              {"psave"}),
    "K-CW4": ("basic/save.asm",
              "                cp      19                  ; D-CASWBRK: a tape write broken with\n"
              "                jp      z,raise_error       ; Ctrl-STOP -- Device I/O error (motor off)\n",
              "",
              {"dcsave", "pcsave", "pbsave", "phold"}),
    "K-CW5": ("basic/save.asm",
              "                call    TAPOUT              ; emit the byte\n"
              "                jp      c,dpl_dio           ; D-CASWBRK: Ctrl-STOP -> 19, raised\n",
              "                call    TAPOUT              ; emit the byte\n",
              {"psave", "pprint"}),
}
TMP = "/tmp/zerobas"


def ours(log):
    with open(log, "w") as fh:
        subprocess.call(["python3", "-u", "probes/basic/basic_probe_caswbrk.py"],
                        stdout=fh, stderr=subprocess.STDOUT,
                        env=dict(os.environ, CASWBRK_OURS_ONLY="1"))
    got = {m.group(1): m.group(2).strip() for m in
           re.finditer(r"^== (\S+)\s+ours (.*)$", open(log, errors="replace").read(), re.M)}
    return got          # "None" is a reading (nothing matched), a MISSING row is not


def main():
    only = sys.argv[1:] or list(KNIVES)
    os.makedirs(TMP, exist_ok=True)
    before0 = knife_guard.hashes()
    _, before0, rc = knife_guard.build(f"{TMP}/cwknife_base_build.out", before0, clean=True)
    if rc:
        print("BASELINE BUILD FAILED")
        return 2
    base = ours(f"{TMP}/cwknife_base.out")
    print(f"base: {base}", flush=True)
    if set(base) != ALL or "None" in base.values():
        print(f"BASELINE BROKEN: {base}")
        return 2
    fails = []
    for k in only:
        src, old, new, want = KNIVES[k]
        orig = open(src).read()
        if orig.count(old) != 1:
            print(f"KNIFE BROKEN: {k} anchor count {orig.count(old)} in {src}")
            return 2
        restore = lambda o=orig, f=src: open(f, "w").write(o)
        atexit.register(restore)
        try:
            open(src, "w").write(orig.replace(old, new))
            before = knife_guard.hashes()
            moved, after, rc = knife_guard.build(f"{TMP}/{k}_build.out", before, clean=True)
            print(knife_guard.report(k, moved, before, after), flush=True)
            if rc:
                print(f"{k}: BUILD FAILED with the cut in -- {TMP}/{k}_build.out")
                return 2
            if not moved:
                print(f"{k}: refusing to score an INERT cut")
                return 2
            cut = ours(f"{TMP}/{k}_probe.out")
        finally:
            restore()
            atexit.unregister(restore)
        if set(cut) != ALL:
            print(f"{k}: KNIFE RUN INCOMPLETE -- rows {sorted(ALL - set(cut))} never printed; "
                  f"refusing to score them as unmoved ({TMP}/{k}_probe.out)")
            return 2
        got = {r for r in ALL if cut[r] != base[r]}
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: moved {sorted(got)} (want exactly "
              f"{sorted(want)})  {cut}", flush=True)
        if not ok:
            fails.append(k)
    _, after, _ = knife_guard.build(f"{TMP}/cwknife_restore.out", clean=True)
    print(f"restored ROM hashes {after} (baseline {before0})")
    if after != before0:
        print("RESTORE MISMATCH: the installed ROM is not the baseline's")
        return 2
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
