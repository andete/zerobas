#!/usr/bin/env python3
r"""D-POPRAISE K-EL1: witness `ela_err` before aliasing it away.

The stmt_error group's ONLY zero-reach-cost member. Its body is
`pop af / pop hl / jp stmt_error` (5 B, page 1) -- byte-for-byte the job
`ems_err_pop2` does in the low region, and its single call site
(basic/arrays.asm:849) already reaches by `jp`, so the alias costs nothing.
Precedent: `elas_err equ ems_err_pop1` (D-XREG), same file, same shape, gated by
check_tenant_closure.py.

🔴 The knife retargets to `gb_illegal`, NOT `fp_runtime_error` and NOT
`stmt_error`'s own siblings: D-POPRAISE §5 showed a retarget that re-consults a
pending cell is a designed no-op. gb_illegal is `ld a,5 / jp raise_error` and
consults nothing, so ERR 2 -> ERR 5 is a clean signal.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD).
"""
import atexit, os, subprocess, sys

TMP, SRC = "/tmp/zerobas", "basic/vars.asm"
OLD = ("ela_err:\n"
       "                pop     af\n"
       "                pop     hl                  ; discard [TYPE],[OFFSET]\n"
       "                jp      stmt_error")
NEW = ("ela_err:\n"
       "                pop     af                  ; K-EL1 CUT (restored on exit)\n"
       "                pop     hl\n"
       "                jp      gb_illegal")


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def read_rows(path):
    rows = {}
    for line in open(path, errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[0][:2] in ("d.", "e.", "s.", "f."):
            rows[p[0]] = " ".join(p[1:])
    return rows


def main():
    os.makedirs(TMP, exist_ok=True)
    base = read_rows(f"{TMP}/pm_dimfix_zb.out")
    if not base:
        print("NO BASELINE"); return 2
    orig = open(SRC).read()
    if orig.count(OLD) != 1:
        print(f"KNIFE BROKEN: anchor matches {orig.count(OLD)}x in {SRC}")
        return 2
    restore = lambda: open(SRC, "w").write(orig)
    atexit.register(restore)
    try:
        open(SRC, "w").write(orig.replace(OLD, NEW))
        print("K-EL1 planted, rebuilding...")
        if sh("make repack-machine", f"{TMP}/elk_build.out"):
            print("BUILD FAILED"); return 2
        sh("python3 scratchpad/popmerge_probe.py zb", f"{TMP}/elk_probe.out")
    finally:
        restore()
        atexit.unregister(restore)
    sh("make repack-machine", f"{TMP}/elk_restore.out")
    cut = read_rows(f"{TMP}/elk_probe.out")
    moved = sorted(r for r in base if base[r] != cut.get(r))
    print(f"\nK-EL1 moved {len(moved)} row(s): {' '.join(moved) or '(none)'}")
    for r in moved:
        print(f"    {r:<11s} {base[r]:>14s}  ->  {cut.get(r)}")
    ctl = [r for r in moved if r.startswith("f.ctl")]
    if ctl:
        print(f"🔴 a CONTROL moved {ctl} -- harness fault, not a witness")
    print("\nVERDICT:", "ela_err witnessed" if moved and not ctl
          else "🔴 UNWITNESSED — do not alias it on faith")
    return 0 if moved and not ctl else 1


if __name__ == "__main__":
    sys.exit(main())
