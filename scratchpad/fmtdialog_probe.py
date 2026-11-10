#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""What CALL FORMAT (and MSX-DOS's FORMAT) SAYS, step by step, on each machine:
types at fixed emulated times and dumps the text screen (the SCREEN 0 name table,
read from VRAM -- screen output, readable) after each step. D-DSKFMT follow-up (a).

    python3 scratchpad/fmtdialog_probe.py [--machine stock|ours|both]
        [--disk D] --step "T:KEYS" ... [--dump T ...] [--settle S]

KEYS use Tcl `type` escapes (\\r = Enter). A dump at time T prints 24 rows of 40.
The disk is a COPY; the original is never written.
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from omsx_session import OmsxRun, OURS_MACHINE, STOCK_MACHINE  # noqa: E402
import probe_tmp  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="both")
    ap.add_argument("--disk", default=os.path.join(REPO, "disk", "test720.dsk"))
    ap.add_argument("--step", action="append", default=[], help="T:KEYS")
    ap.add_argument("--dump", action="append", type=float, default=[])
    ap.add_argument("--settle", type=float, default=40.0)
    ap.add_argument("--cols", type=int, default=40)
    ap.add_argument("--ram", action="append", default=[], help="T:ADDR:LEN -- a RAM dump (hex)")
    ap.add_argument("--poke", action="append", default=[], help="T:ADDR:HEXBYTES -- write RAM (ours: a poke test)")
    a = ap.parse_args()
    machines = {"both": [STOCK_MACHINE, OURS_MACHINE], "stock": [STOCK_MACHINE],
                "ours": [OURS_MACHINE]}[a.machine]
    work = probe_tmp.tmp("fmtdialog")
    os.makedirs(work, exist_ok=True)
    for m in machines:
        dsk = os.path.join(work, f"{m}.dsk")
        shutil.copyfile(a.disk, dsk)
        arm = ""
        for st in a.step:
            t, _, keys = st.partition(":")
            arm += f'after time {float(t):.4f} {{ type "{keys}" }}\n'
        for t in sorted(set(a.dump + [a.settle - 0.5])):
            # the name table's base from VDP R2, the mode from R1 (bit 4: 40 columns)
            arm += (f'after time {t:.4f} {{ set r2 [debug read {{VDP regs}} 2]; '
                    f'set r1 [debug read {{VDP regs}} 1]; '
                    f'emit "SCREEN {t:.1f} $r1 [binary encode hex [debug read_block VRAM '
                    f'[expr {{($r2 & 15) * 1024}}] 960]]" }}\n')
        for r in a.ram:
            t, ad, ln = r.split(":")
            arm += (f'after time {float(t):.4f} {{ emit "RAM {t} {ad} '
                    f'[binary encode hex [debug read_block memory {int(ad, 0)} {int(ln, 0)}]]" }}\n')
        for pk in a.poke:
            t, ad, hx = pk.split(":")
            for k, byte in enumerate(bytes.fromhex(hx)):
                arm += f'after time {float(t):.4f} {{ debug write memory {int(ad, 0) + k} {byte} }}\n'
        run = OmsxRun(machine=m, diska=dsk)
        lines = run.run_job_raw('emit "END"; exit', settle=a.settle, arm=arm,
                                timeout=a.settle * 4 + 120)
        print(f"===== {m} =====")
        for ln in lines:
            if ln.startswith("SCREEN "):
                _, t, r1, blob = ln.split(" ", 3)
                data = bytes.fromhex(blob.strip())
                cols = 40 if int(r1) & 0x10 else 32
                print(f"--- t={t} ({cols} columns) ---")
                for r in range(24):
                    row = data[r * cols:(r + 1) * cols]
                    txt = "".join(chr(c) if 32 <= c < 127 else "." for c in row).rstrip(".").rstrip()
                    if txt:
                        print(f"  {r:2d}|{txt}")
            elif ln.startswith("RAM "):
                _, t, ad, blob = ln.split(" ", 3)
                b = bytes.fromhex(blob.strip())
                base = int(ad, 0)
                print(f"--- RAM t={t} ---")
                for k in range(0, len(b), 16):
                    print(f"  {base + k:04X}: " + " ".join(f"{x:02X}" for x in b[k:k + 16]))
            elif not ln.startswith(("HB", "BEAT")):
                print("  ", ln[:120])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
