#!/usr/bin/env python3
"""K-XR1 (D-KWERRWORDS, the EXTRA half, 2026-10-27): does an EXTRA row redden kwsweep now?

Plants the pre-D-DEFUSRRANGE DEF USR reader -- `call inc_eval`, padded with NOPs to the
fix's seven bytes (a byte-adding cut is wall-dependent) -- so `DEF USR=70000` is accepted
again, and runs kwsweep's DEF USR rows. Before the EXTRA rule, the same divergence read
EXTRA and the sweep exited 0 (scratchpad/defusrrange_knife.out).

    python3 -u scratchpad/extrared_knife.py
"""
import os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard  # noqa: E402

SRC = "basic/usr.asm"
NEW = """                inc     hl                  ; D-DEFUSRRANGE (2026-10-27): POKE's own address
                call    eval_addr           ; reader -- -32768..65535, FPERR=1 past it -- and
                call    check_fperr_only    ; its check, BEFORE the store: `DEF USR=70000` is
"""
OLD = """                call    inc_eval            ; K-XR1: the reader before D-DEFUSRRANGE
                nop
                nop
                nop                         ; (padded to the fix's 7 bytes)
                nop                         ; its check, BEFORE the store: `DEF USR=70000` is
"""
GATE = "make kwsweep ONLY=t7defusrdefault2,t7defusrdefault6,t7defusrdefault13,t7defusrnumbered2,t7defusrnumbered6,t7defusrnumbered13"


def main():
    orig = open(SRC).read()
    assert orig.count(NEW) == 1, "anchor not unique / missing"
    base = knife_guard.hashes()
    g = None
    try:
        open(SRC, "w").write(orig.replace(NEW, OLD))
        ok, cut, rc = knife_guard.build("/tmp/extrared_knife/mk_cut.log", base, clean=True)
        print(knife_guard.report("K-XR1", ok, base, cut, rc, "/tmp/extrared_knife/mk_cut.log"), flush=True)
        if ok and not rc:
            g = subprocess.run(GATE, shell=True, capture_output=True, text=True)
    finally:
        open(SRC, "w").write(orig)
        _, back, rc2 = knife_guard.build("/tmp/extrared_knife/mk_back.log", None, clean=True)
    same = back == base
    print(f"restore: {base} -> {back}  build rc={rc2}  {'BYTE-IDENTICAL (all five)' if same else 'DRIFT'}")
    if g is None:
        print("K-XR1: NOT SCORED -- the cut did not reach the ROM")
        sys.exit(2)
    print(f"K-XR1: gate rc={g.returncode}")
    for line in (g.stdout + g.stderr).splitlines():
        if ("t7defusr" in line or "UNPINNED" in line or "ROWS" in line) \
                and not line.lstrip().startswith(("python3", "--zb")):
            print(line)
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
