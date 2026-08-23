#!/usr/bin/env python3
"""K-DE1 -- does the servicer's `push de`/`pop de` actually carry anything?

The claim (docs/spec-basic-deffnland.md §3.2): an INT-typed value lives in DE
with FAC unwritten, and the tenant bounce between request 1 (`call eval`) and
request 2 (`call var_store_fac`) destroys it. Two bytes in basic/deffn.asm's
fn_lp are the whole fix.

🔴 A FIX THAT COSTS BYTES AND CHANGES NOTHING HAS NOT HAPPENED. This cuts the
two bytes out and requires `make deffn-strict` to go RED, specifically at the
DEFINT rows; a knife that reddens nothing would mean the guard is dead weight
and should be deleted, not documented.

House rules this obeys, each of which has cost this project a measurement:
  * restore by WRITING THE BYTES (an asserted string replacement), never a file
    copy -- copy2 preserves mtime and make then rebuilds nothing;
  * `rm -rf build` before EVERY build, because a write landing in the same mtime
    tick as the previous restore can still leave make deciding nothing changed;
  * ASSERT THE ROM MOVED before scoring, on the image the cut belongs to. A
    page-1-only edit does NOT move sub.rom (the resident ABI lives below $4000
    and is unchanged), so this asserts main MOVED and sub did NOT -- getting
    that expectation the wrong way round is how a green knife reads as a knife
    that could not cut.
"""
from __future__ import annotations
import hashlib
import os
import subprocess
import sys

SRC = "basic/deffn.asm"
GUARD_IN = """                push    de
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_DEFFN
                call    subrom_call         ; A = the tenant's request
                pop     de                  ; (a `pop` does not touch CF)"""
GUARD_OUT = """                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_DEFFN
                call    subrom_call         ; A = the tenant's request"""


def swap(frm: str, to: str) -> None:
    s = open(SRC).read()
    if s.count(frm) != 1:
        raise SystemExit(f"FAIL: {SRC} has {s.count(frm)} copies of the block")
    open(SRC, "w").write(s.replace(frm, to, 1))


def build() -> tuple[str, str]:
    subprocess.run(["rm", "-rf", "build"], check=True)
    r = subprocess.run(["make", "repack-machine"], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("FAIL: build\n" + r.stdout[-3000:] + r.stderr[-3000:])
    return tuple(
        hashlib.sha256(open(f, "rb").read()).hexdigest()[:8]
        for f in ("build/zerobas-main-eu.rom", "build/sub.rom"))


def strict(tag: str) -> tuple[int, str]:
    r = subprocess.run(["make", "deffn-strict"], capture_output=True, text=True)
    open(f"scratchpad/de_knife_{tag}.out", "w").write(r.stdout + r.stderr)
    tail = [l for l in r.stdout.splitlines() if l.startswith("ROWS:")]
    return r.returncode, (tail[-1] if tail else "<no ROWS line>")


def main() -> int:
    base = build()
    rc0, rows0 = strict("base")
    print(f"  BASE  main={base[0]} sub={base[1]}  rc={rc0}  {rows0}", flush=True)
    if rc0 != 0:
        raise SystemExit("FAIL: the baseline is not green -- score nothing")

    swap(GUARD_IN, GUARD_OUT)
    try:
        cut = build()
        print(f"  KNIFE main={cut[0]} sub={cut[1]}", flush=True)
        assert cut[0] != base[0], "the MAIN rom did not move -- the knife did not cut"
        assert cut[1] == base[1], "sub.rom moved; a page-1 edit should not touch it"
        rc1, rows1 = strict("cut")
        print(f"  KNIFE rc={rc1}  {rows1}", flush=True)
        red = [l.strip() for l in open("scratchpad/de_knife_cut.out")
               if l.startswith("DIFF")]
        print(f"  {len(red)} row(s) reddened:", flush=True)
        for l in red:
            print(f"      {l}", flush=True)
    finally:
        swap(GUARD_OUT, GUARD_IN)               # raises if it cannot be undone
        back = build()
        print(f"  BACK  main={back[0]} sub={back[1]}", flush=True)
        d = subprocess.run(["git", "diff", "--stat", "--", SRC],
                           capture_output=True, text=True).stdout.strip()
        print(f"  source restored to the working tree: "
              f"{'as before the knife' if back == base else 'ROM DIFFERS -- ' + str(back)}"
              f"   (git diff vs HEAD: {d.splitlines()[0] if d else 'clean'})", flush=True)
    verdict = "CUT" if (rc1 != 0 and red) else "🔴 REDDENED NOTHING"
    print(f"\n  K-DE1: {verdict}", flush=True)
    return 0 if verdict == "CUT" else 1


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.exit(main())
