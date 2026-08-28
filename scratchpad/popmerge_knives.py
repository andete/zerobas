#!/usr/bin/env python3
r"""D-POPRAISE K-PR1..K-PR4: witness each fp_runtime_error discard-tail ALONE.

Four tails (18 B of main page 1) are "discard k words, then jp fp_runtime_error".
Before merging them into one 5 B chain, each must be shown to be separately LIVE
-- otherwise the merge is verified by rows that never looked at it.

🔴 THE KNIFE IS ON THE TARGET, NOT THE POPS. D-MIDOP's K-MD2 deleted both pops at
`ems_typecheck` and moved 0 rows of 9: raise_error resets SP, so the discards are
unobservable and a pop-count knife reddens NOTHING. Each knife here retargets one
tail's `jp fp_runtime_error` to `jp gb_illegal`, which raises ERR 5 and is
therefore visible in scratchpad/popmerge_probe.py.

🔴 THE FIRST CUT OF THIS KNIFE RETARGETED TO `stmt_error` AND WAS A DESIGNED
NO-OP. stmt_error opens with `call check_expr_errors` (D-STMTPEND, first-error-
wins: a syntax error must not outrank a fault that already happened), so with
FPERR set it re-raises THE SAME ERR CODE -- three of four tails read
"UNWITNESSED" for a reason that had nothing to do with the tails. The fourth,
cee_abort_fp, was worse: retargeting IT to stmt_error made check_expr_errors
jump back into cee_abort_fp, and the "movement" that arm reported was a runaway,
not a signal. `gb_illegal` (`ld a,5 / jp raise_error`) consults no pending cell.

A tail whose knife moves no row is UNWITNESSED and is reported as such.
🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit.
"""
import atexit, os, subprocess, sys

TMP = "/tmp/zerobas"

# (name, file, unique anchor, replacement)
KNIVES = [
    ("K-PR1 cee_abort_fp",  "basic/interp.asm",
     "cee_abort_fp:\n"
     "                pop     hl                  ; discard our own dead resume addr\n"
     "                jp      fp_runtime_error",
     "cee_abort_fp:\n"
     "                pop     hl                  ; K-PR1 CUT (restored on exit)\n"
     "                jp      gb_illegal"),
    ("K-PR2 cepb_abort_fp", "basic/interp.asm",
     "cepb_abort_fp:\n"
     "                pop     hl                  ; discard our own dead resume addr\n"
     "                pop     bc                  ; discard the caller's saved key\n"
     "                jp      fp_runtime_error",
     "cepb_abort_fp:\n"
     "                pop     hl                  ; K-PR2 CUT (restored on exit)\n"
     "                pop     bc\n"
     "                jp      gb_illegal"),
    ("K-PR3 ela_abort_fp",  "basic/vars.asm",
     "ela_abort_fp:\n"
     "                pop     af\n"
     "                pop     hl\n"
     "                jp      fp_runtime_error",
     "ela_abort_fp:\n"
     "                pop     af                  ; K-PR3 CUT (restored on exit)\n"
     "                pop     hl\n"
     "                jp      gb_illegal"),
    ("K-PR4 elas_abort_fp", "basic/vars.asm",
     "elas_abort_fp:\n"
     "                pop     de                  ; discard [OFFSET]\n"
     "                jp      fp_runtime_error",
     "elas_abort_fp:\n"
     "                pop     de                  ; K-PR4 CUT (restored on exit)\n"
     "                jp      gb_illegal"),
]


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def read_rows(path):
    rows = {}
    for line in open(path, errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[0].startswith("f."):
            rows[p[0]] = " ".join(p[1:])
    return rows


def main():
    os.makedirs(TMP, exist_ok=True)
    base = read_rows(f"{TMP}/pm_base_zb.out")
    if not base:
        print(f"NO BASELINE: run popmerge_probe.py zb > {TMP}/pm_base_zb.out first")
        return 2
    print(f"baseline: {len(base)} rows\n")

    results = {}
    for name, src, old, new in KNIVES:
        orig = open(src).read()
        if orig.count(old) != 1:
            print(f"{name}: KNIFE BROKEN -- anchor matches {orig.count(old)}x in {src}")
            results[name] = None
            continue
        restore = lambda o=orig, s=src: open(s, "w").write(o)
        atexit.register(restore)
        tag = name.split()[0]
        try:
            open(src, "w").write(orig.replace(old, new))
            print(f"{name}: planted, rebuilding...")
            if sh("make repack-machine", f"{TMP}/pmk_{tag}_build.out"):
                print(f"{name}: BUILD FAILED"); results[name] = None; continue
            sh(f"python3 scratchpad/popmerge_probe.py zb",
               f"{TMP}/pmk_{tag}.out")
        finally:
            restore()
            atexit.unregister(restore)
        cut = read_rows(f"{TMP}/pmk_{tag}.out")
        moved = sorted(r for r in base if base[r] != cut.get(r))
        results[name] = moved
        print(f"{name}: moved {len(moved)} row(s): {' '.join(moved) or '(none)'}")
        for r in moved:
            print(f"      {r:<10s} {base[r]:>16s}  ->  {cut.get(r)}")
        print()

    sh("make repack-machine", f"{TMP}/pmk_restore.out")
    print("=" * 68)
    unwitnessed = [n for n, m in results.items() if not m]
    for n, m in results.items():
        print(f"  {n:<22s} {'UNWITNESSED' if not m else str(len(m)) + ' row(s)'}")
    # the controls must never move -- a knife that reddens them broke the harness
    bad = {n: [r for r in (m or []) if r.startswith("f.ctl")] for n, m in results.items()}
    for n, c in bad.items():
        if c:
            print(f"  🔴 {n} moved a CONTROL row {c} -- harness fault, not a witness")
    print()
    print("VERDICT:", "every tail separately witnessed" if not unwitnessed
          else f"🔴 UNWITNESSED: {unwitnessed}")
    return 0 if not unwitnessed and not any(bad.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
