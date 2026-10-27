#!/usr/bin/env python3
"""K-KW1 (D-KWERRWORDS, 2026-10-27): is kwsweep still blind to `NEXT without FOR`?

D-ERRORARG's knife (scratchpad/errorarg_knife.out) cut ex_error back and kwsweep scored
`ERROR 1,1` EXTRA -- ref `Syntax error`, zb `NEXT without FOR`, which the hand-written
ERROR_WORDS could not name -- and EXTRA did not redden the sweep. This plants three NOPs over
ex_error's end-of-statement check (byte-neutral), so `ERROR 1,1` raises 1 again,
runs kwsweep's ERROR rows, and restores. The question is t6errorr2's verdict.

    python3 -u scratchpad/kwerrwords_knife.py
"""
import os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard  # noqa: E402

SRC = "basic/interp.asm"
NEW = """                inc     hl                  ; past the ERROR token
                call    eval_byte_checked   ; E = 0..255: 13 / 24 / 6 / 5 raised here
                call    mxf_require_end     ; anything after it -> ERR 2 (DE survives)
                ld      a,e
                or      a                   ; Z <=> value 0
"""
OLD = """                inc     hl                  ; past the ERROR token
                call    eval_byte_checked   ; E = 0..255: 13 / 24 / 6 / 5 raised here
                nop                         ; K-KW1: no end check -- `ERROR 1,1` raises 1
                nop                         ; (byte-neutral: a byte-ADDING cut is wall-
                nop                         ; dependent and failed the first build)
                ld      a,e
                or      a                   ; Z <=> value 0
"""
GATE = "make kwsweep ONLY=t6errorr5,t6errorr13,t6errorr24,t6errorr6,t6errorr2,error_t3"


def main():
    orig = open(SRC).read()
    assert orig.count(NEW) == 1, "anchor not unique / missing"
    base = knife_guard.hashes()
    g = None
    try:
        open(SRC, "w").write(orig.replace(NEW, OLD))
        ok, cut, rc = knife_guard.build("/tmp/kwerrwords_knife/mk_cut.log", base, clean=True)
        print(knife_guard.report("K-KW1", ok, base, cut, rc, "/tmp/kwerrwords_knife/mk_cut.log"), flush=True)
        if ok and not rc:
            g = subprocess.run(GATE, shell=True, capture_output=True, text=True)
    finally:
        open(SRC, "w").write(orig)
        _, back, rc2 = knife_guard.build("/tmp/kwerrwords_knife/mk_back.log", None, clean=True)
    same = back == base
    print(f"restore: {base} -> {back}  build rc={rc2}  {'BYTE-IDENTICAL (all five)' if same else 'DRIFT'}")
    if g is None:
        print("K-KW1: NOT SCORED -- the cut did not reach the ROM")
        sys.exit(2)
    print(f"K-KW1: gate rc={g.returncode}")
    for line in (g.stdout + g.stderr).splitlines():
        if ("t6error" in line or "error_t3" in line or "UNPINNED" in line or "ROWS" in line) \
                and not line.lstrip().startswith(("python3", "--zb")):
            print(line)
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
