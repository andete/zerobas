#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M31 $27 RDBLK random-record round-trip (spec tier2-m31-rdblk-randrecord-spec.md
§6.2). LIVE-oracle positive proof that our faithful $27 positions to the FCB
random-record, honors the record count/size, zero-pads a final partial record,
and advances FCB+33..35 — byte-identically to the real National CF-3300.

Method (clean-room, black-box): assemble rdblk_rt.asm (RDBLK.COM), patch its
per-case param block ($0102: recnum/rs/cnt), inject RDBLK.COM + a position-varying
RDTEST.BIN into a /tmp copy of a real MSX-DOS-1 disk, then run the ONE differential
engine (disk_probe_diff.py `capture`) to snapshot the DTA + return cells at RDBLK's
`done` self-loop on BOTH machines and diff them. RDBLK sets FCB+33..35 DIRECTLY (our
$24 SETRND is still a no-op — the deferred gate-green piece), which is exactly how a
program computing its own random-record position behaves. Stock ROM code is never
read/disassembled; only its RAM RESULT is compared. Test disks are always /tmp copies.

  python3 probes/disk/disk_probe_rdblk_roundtrip.py
  python3 probes/disk/disk_probe_rdblk_roundtrip.py --only a
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling probes
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse, don't duplicate)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ASM = os.path.join(HERE, "rdblk_rt.asm")
DIFF = os.path.join(HERE, "disk_probe_diff.py")
DEFAULT_DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")

# Position-varying file content: byte i = (i*5 + 7) & 0xFF. Any read that lands at
# the WRONG file offset copies different bytes -> the ours/stock diff catches it.
def rdtest_bin(size: int) -> bytes:
    return bytes([(i * 5 + 7) & 0xFF for i in range(size)])


# case -> (recnum, rs, cnt, filesize, blurb)
CASES = {
    # (a) mid-file positioning: read record 1 (not 0). THE core positioning proof.
    "a":  (1, 128, 1, 384, "mid-file RR=1 cnt=1 -> record 1"),
    # (b') partial tail: cnt overshoots EOF; final record zero-padded to RS.
    "bp": (1, 128, 4, 300, "EOF mid-transfer + zero-pad tail (300B file)"),
    # (c) positioned AT EOF: HL=0, DTA untouched (all sentinel), RR unchanged.
    "c":  (3, 128, 1, 384, "at-EOF RR=3 -> 0 records, DTA untouched"),
}


def assemble(tmp_dir: str) -> tuple[bytearray, int]:
    com = os.path.join(tmp_dir, "rdblk.com")
    sym = os.path.join(tmp_dir, "rdblk.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    done = None
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        if name.strip() == "done":
            done = int(rest.strip().split()[-1].rstrip("H"), 16)
    if done is None:
        sys.exit("could not find `done` in rdblk.sym")
    return bytearray(open(com, "rb").read()), done


def patch_params(com: bytearray, recnum: int, rs: int, cnt: int) -> int:
    """Patch the $0102 param block; return recnum[0] (the capture arm signature)."""
    off = 0x0102 - 0x0100          # .com is loaded at $0100; byte 0 == $0100
    com[off + 0] = recnum & 0xFF
    com[off + 1] = (recnum >> 8) & 0xFF
    com[off + 2] = (recnum >> 16) & 0xFF
    com[off + 3] = rs & 0xFF
    com[off + 4] = (rs >> 8) & 0xFF
    com[off + 5] = cnt & 0xFF
    com[off + 6] = (cnt >> 8) & 0xFF
    return com[off + 0]


def run_case(key: str, dos_src: str, done: int, com_base: bytearray, tmp_dir: str) -> bool:
    recnum, rs, cnt, fsize, blurb = CASES[key]
    com = bytearray(com_base)
    sig = patch_params(com, recnum, rs, cnt)
    out = os.path.join(tmp_dir, f"zerobas_rdblk_{key}.dsk")
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "RDTEST", "BIN", rdtest_bin(fsize))
    fat12_add(img, "RDBLK", "COM", bytes(com))
    open(out, "wb").write(img)

    # Capture WINDOW = the result snapshot cells ($0340: res_a/hl/bc/rr — the
    # returned A/HL/BC + the FCB+33..35 write-back) + the RDSEQ scratch ($0380,
    # must match) + the delivered DTA ($0400). This is exactly what M31's $27
    # governs. It DELIBERATELY EXCLUDES the raw FCB ($0300-$0324): FCB+32 (CR,
    # current-record bookkeeping) and FCB+25 (dirloc) diverge for reasons OUTSIDE
    # $27 — CR is the deferred gate-green CR-bookkeeping piece (M31 is $27-only),
    # dirloc is the M22a accepted-cosmetic class (already gate-allowlisted). The
    # RR write-back is still proven, via res_rr ($0345), which snapshots FCB+33..35
    # right after the call.
    cmd = ["python3", DIFF, "capture",
           "--at", f"{done:#06x}", "--arm-check-val", f"{sig:#04x}",
           "--keys", "\\rRDBLK\\r", "--keys-at", "20", "--settle", "40",
           "--machine", "both", "--mem", "0x0340:0x240", "--diska", out]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    txt = p.stdout + p.stderr

    print(f"\n===== case {key}: {blurb} "
          f"(RR={recnum} rs={rs} cnt={cnt} file={fsize}B) =====")
    if "MISALIGNED" in txt:
        print("  FAIL  MISALIGNED — a machine never reached RDBLK's `done` (diff "
              "meaningless). Anchor/keys/timing problem, not a $27 result.")
        _tail(txt)
        return False
    m = re.search(r"memory 0x[0-9a-fA-F]+\+\d+:\s+(\d+) of (\d+) bytes differ", txt)
    if not m:
        print("  FAIL  could not parse the mem-diff summary from capture output.")
        _tail(txt)
        return False
    ndiff = int(m.group(1))
    if ndiff == 0:
        print(f"  PASS  DTA + return snapshot BYTE-IDENTICAL ours==stock "
              f"({m.group(2)} bytes compared) — faithful $27 confirmed on the live oracle.")
        return True
    print(f"  FAIL  {ndiff} of {m.group(2)} bytes differ ours-vs-stock — $27 does NOT "
          f"match stock for this case:")
    for ln in txt.splitlines():
        if re.match(r"\s+0[0-9A-Fa-f]{3}: stock=", ln):
            print("   " + ln.strip())
    return False


def _tail(txt: str, n: int = 12) -> None:
    print("    --- capture tail ---")
    for ln in txt.splitlines()[-n:]:
        print("    " + ln)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", default=DEFAULT_DOS)
    ap.add_argument("--tmp-dir", default="/tmp")
    ap.add_argument("--only", choices=list(CASES), help="run a single case")
    args = ap.parse_args()

    if not os.path.exists(args.dos_disk):
        sys.exit(f"missing DOS oracle disk: {args.dos_disk}")
    com_base, done = assemble(args.tmp_dir)
    print(f"RDBLK.COM assembled; done = {done:#06x}")

    keys = [args.only] if args.only else list(CASES)
    ok = all(run_case(k, args.dos_disk, done, com_base, args.tmp_dir) for k in keys)
    print("\n" + ("ALL RDBLK ROUND-TRIP CASES PASSED (ours == CF-3300)"
                  if ok else "RDBLK ROUND-TRIP: FAILURE(S) ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
