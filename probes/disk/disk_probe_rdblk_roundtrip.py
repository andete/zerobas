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
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling probes
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse, don't duplicate)

# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

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


# --- APPARATUS-vs-SUBJECT retry policy (docs/spec-rdblk-anchor-flake.md §4.3) --------
# This probe was an intermittent gate row: on 2026-07-30 it failed once inside a full
# `make diskbasic-acceptance` (33/34) with stock never reaching the anchor, then
# converged standalone AND on a full re-run of the byte-identical build. The subject was
# innocent; a host-level event had been laundered into a subject-shaped verdict.
#
# capture now separates the two (disk_probe_diff.py §4.2), so retry EXACTLY the class
# that is not about the subject:
#   rc 3 APPARATUS -> the emulator never finished its emulated timeline. Retry, LOUDLY.
#   rc 2 LOGICAL   -> a real anchor/keys defect. NEVER retried; retrying it would be the
#                     forbidden "loosen the misalignment check", one level up.
# ⚠️ Every retry PRINTS, and the summary prints a total, because a silent retry turns a
# flaky gate into an invisible one [[gate-can-be-green-while-measuring-nothing]].
APPARATUS_RC = 3
MAX_ATTEMPTS = 3            # 1 try + 2 retries
RETRY_BUDGET = 120.0        # probe-wide host seconds spent on retries
# Sized from measurement, not arithmetic: one boot measured 0.4-1.2 s wall, so 45 s is
# ~40x headroom. The budgets were INVERTED before this (220 s per boot inside a 240 s
# per-probe cap for a 6-boot probe), so a single wedged boot blew the runner's cap and
# the same event surfaced as MISALIGNED or as TIMEOUT depending on which boot wedged.
CAPTURE_TIMEOUT = 45.0      # per boot, passed to capture --timeout
CASE_TIMEOUT = 120.0        # per case (2 boots), the subprocess wall cap
_RETRY = {"n": 0, "spent": 0.0}


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
           "--timeout", str(CAPTURE_TIMEOUT),
           "--machine", "both", "--mem", "0x0340:0x240", "--diska", out]

    print(f"\n===== case {key}: {blurb} "
          f"(RR={recnum} rs={rs} cnt={cnt} file={fsize}B) =====")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        t0 = time.time()
        try:
            p = subprocess.run(omsx_preflight.guarded(cmd), cwd=ROOT, capture_output=True, text=True,
                               timeout=CASE_TIMEOUT)
            rc, txt = p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired as e:
            # Previously this propagated and crashed the probe. A case that outruns its
            # wall cap is the APPARATUS class by construction: 2 boots measured at ~1 s
            # each cannot legitimately reach 120 s.
            rc = APPARATUS_RC
            txt = ((e.output or "") if isinstance(e.output, str) else "") + \
                  f"\n[case] TIMEOUT after {CASE_TIMEOUT:.0f}s — no capture output"
        wall = time.time() - t0
        if rc != APPARATUS_RC:
            break
        if attempt == MAX_ATTEMPTS:
            print(f"  APPARATUS-RETRY EXHAUSTED after {MAX_ATTEMPTS} attempts")
            break
        if _RETRY["spent"] + wall > RETRY_BUDGET:
            print(f"  APPARATUS-RETRY BUDGET SPENT ({_RETRY['spent']:.0f}s of "
                  f"{RETRY_BUDGET:.0f}s) — not retrying case {key} again")
            break
        _RETRY["n"] += 1
        _RETRY["spent"] += wall
        reason = next((l.strip() for l in txt.splitlines() if "miss class:" in l),
                      "no capture output")
        print(f"  APPARATUS-RETRY case {key} attempt {attempt + 1}/{MAX_ATTEMPTS} — "
              f"{reason} (wall {wall:.1f}s)")

    if "MISALIGNED" in txt or rc == APPARATUS_RC:
        if rc == APPARATUS_RC:
            print("  FAIL  APPARATUS — the emulator never completed its emulated "
                  "timeline, so this says NOTHING about $27. The host is the suspect, "
                  "not the ROM (see [[openmsx-coreaudio-wedge]]).")
        else:
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
    # NOT all(...): that short-circuits, so one failing case would skip the rest and the
    # denominator would silently shrink. Run every case, then decide.
    results = [run_case(k, args.dos_disk, done, com_base, args.tmp_dir) for k in keys]
    ok = all(results)
    print("\n" + ("ALL RDBLK ROUND-TRIP CASES PASSED (ours == CF-3300)"
                  if ok else "RDBLK ROUND-TRIP: FAILURE(S) ABOVE"))
    # Printed unconditionally so "0" is a MEASUREMENT, not the absence of a line — and
    # so a green run that needed a retry cannot read as a clean one.
    print(f"APPARATUS-RETRY TOTAL: {_RETRY['n']}"
          + (f"  ⚠ the host misbehaved during this run ({_RETRY['spent']:.0f}s spent "
             f"retrying); the RESULT is still ours-vs-stock" if _RETRY["n"] else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
