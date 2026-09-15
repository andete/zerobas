#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional oracle for zerobas-BASIC `FILES` (Phase 2 Step 2).

Boots the combined zerobas machine (zerobas-BASIC slot 0 page 1 + zerobas-disk
slot 3-1) on a /tmp copy of test720.dsk, types `FILES` into the REPL, and dumps
the text screen so the listing can be compared to the real National CF-3300
Disk BASIC reference (diskbasic_probe_files.py). It also reads LINLEN ($F3B0) so
the width-driven wrap can be reconciled with the reference's WIDTH.

Expected directory (raw order): TEST.BIN, HI.TXT, PROG.BIN, PROG.BAS, PROG2.BAS.
Each renders as an 8.3 field "NAME    .EXT" (8 + '.' + 3), single-space separated,
wrapped to the active width.

Strictly black-box: types a REPL line, reads VRAM + one RAM sysvar. No ROM read.
DISK SAFETY: /tmp copy only (FILES is read-only, but keep the discipline).
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

# 🔴 D-FILESROT RE-MEASURED THIS AGAINST A POLLUTED FIXTURE AND FROZE THE
# POLLUTION (found and reverted the same day, D-FIXTUREPOLL). It observed that
# "test720.dsk gained TS.DAT (a zero-byte data file another probe's fixture work
# added)", booted the CF-3300 on THAT disk, and correctly recorded six fields.
# The re-measure was done exactly as prescribed. The FIXTURE was the wrong one.
# 🎯 `disk/test720.dsk` IS UNTRACKED AND GENERATED (`make test-dsk`; commit
# e7c5eab removed it from git precisely to kill "the openMSX write-back hazard
# on a committed image"). TS.DAT, attr $00 where every generated file is $20, is
# a PROBE WRITING INTO THE LOCAL COPY. A freshly generated image has FIVE files.
# 🔴 AND `make test-dsk` DOES NOT NOTICE: it is timestamp-driven, so a polluted
# image is never rebuilt. `make fixture-integrity-check` now compares the working
# fixture's directory against a hermetic regeneration.
# ⚠️ RE-MEASURING IS NOT ENOUGH IF THE THING MEASURED IS CONTAMINATED. The rule
# "re-measure, never edit the constant into agreement" is right and was followed;
# it just cannot see a bad input [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
# ⚠️ FIXTURE-COUPLED: this IS the directory of disk/test720.dsk, in directory
# order. `PROG3.BAS` joined it on 2026-09-15 (D-KWRUNFILE) because
# `RUN"<file>"` and `LOAD",R"` REPLACE the running program, so the only witness
# a kwsweep row can have is output from the LOADED program -- and every other
# `.BAS` on the image only POKEs. Joost ruled: add a second `.BAS`, leave
# `PROG.BAS` alone.
EXPECT = ["TEST    .BIN", "HI      .TXT", "PROG    .BIN", "PROG    .BAS",
          "PROG2   .BAS", "PROG3   .BAS"]


def build_tcl(out_path: str, width: int | None) -> str:
    pre = ""
    if width is not None:
        # set the active text width first, so the width-driven wrap can be checked
        # against the CF-3300 reference (which runs at WIDTH 29).
        pre = (f'after time 6  {{ type "WIDTH {width}" }}\n'
               f'after time 7  {{ type "\\r" }}\n')
    return f"""set throttle off
set __f [open {{{out_path}}} w]
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc __hex_v {{a l}} {{ binary scan [debug read_block VRAM $a $l] H* h; return $h }}
{pre}after time 8  {{ type "FILES" }}
after time 11 {{ type "\\r" }}
after time 16 {{
  puts $__f "linlen=[__hex 0xF3B0 1]"
  puts $__f "scr0=[__hex_v 0x0000 960]"
  flush $__f
  close $__f
  exit
}}
"""


def run(machine: str, out: str, width=None, timeout: float = 90.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zfiles_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    tcl = out + ".tcl"
    open(tcl, "w").write(build_tcl(out, width))
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine, "-diska", dsk,
           "-command", "set renderer none; set sound_driver null", "-script", tcl]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        sys.exit(f"TIMEOUT running {machine}")
    os.unlink(dsk)
    if not os.path.exists(out):
        sys.exit(f"no capture from {machine} (machine missing? disk absent?)")
    rows, linlen = [], None
    for line in open(out):
        line = line.rstrip("\n")
        if line.startswith("scr0="):
            d = bytes.fromhex(line.partition("=")[2])
            rows = ["".join(chr(c) if 32 <= c < 127 else " "
                            for c in d[r*40:(r+1)*40]).rstrip() for r in range(24)]
        elif line.startswith("linlen="):
            linlen = int(line.partition("=")[2], 16)
    return rows, linlen


# The CF-3300 reference listing at WIDTH 29, as the sequence of non-empty
# logical lines the directory produces.
# 🔴 THE SECOND CONSTANT D-FILESROT FROZE FROM THE POLLUTED FIXTURE, reverted
# with EXPECT above (see the note there). Its measuring method was sound and is
# worth keeping: boot the CF-3300, CLEAR THE DATE PROMPT FIRST (skipping the
# `\r` lets the prompt swallow both typed lines, which reads as a listing of
# nothing), WIDTH 29, FILES -- two entries per 29-column line, directory order.
# 🟢 RE-MEASURED 2026-09-15 (D-KWRUNFILE) when `PROG3.BAS` joined the image:
# `scratchpad/cf3300_files_probe.py` runs the procedure above -- the `run()`
# below does NOT answer the date prompt, which is why the refresh needs its own
# entry point. The third line gained `PROG3   .BAS`; the wrap was MEASURED on the
# real machine, not predicted from the width.
CF3300_W29 = ["TEST    .BIN HI      .TXT",
              "PROG    .BIN PROG    .BAS",
              "PROG2   .BAS PROG3   .BAS"]


def _files_lines(rows):
    """The FILES listing lines = the rows after the 'FILES' echo up to the prompt."""
    out, started = [], False
    for r in rows:
        s = r.strip()
        if not started:
            if s.endswith("FILES"):
                started = True
            continue
        if s == "ZB" or s == "Ok" or s == "":
            if out:
                break
            continue
        out.append(r.strip())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")
    rc = 0

    # Case 1 — native width: content + directory order.
    rows, linlen = run(args.machine, "/tmp/disk_files.txt")
    print(f"--- zerobas FILES (native, LINLEN={linlen}) ---")
    for i, r in enumerate(rows):
        if r.strip():
            print(f"{i:2}|{r}")
    blob = "\n".join(rows)
    missing = [e for e in EXPECT if e not in blob]
    if missing:
        print("FAIL — missing entries:", missing); rc = 1
    elif _ordered(rows):
        print(f"PASS — all {len(EXPECT)} expected 8.3 fields present, in directory order")
    else:
        print("FAIL — fields present but out of order"); rc = 1

    # Case 2 — WIDTH 29: byte-exact wrap match vs the real CF-3300 reference.
    rows2, linlen2 = run(args.machine, "/tmp/disk_files_w29.txt", width=29)
    got = _files_lines(rows2)
    print(f"\n--- zerobas FILES (WIDTH 29 -> LINLEN={linlen2}) vs CF-3300 ---")
    for i, r in enumerate(rows2):
        if r.strip():
            print(f"{i:2}|{r}")
    print("got     :", got)
    print("CF-3300 :", CF3300_W29)
    if got == CF3300_W29:
        print("PASS — listing byte-identical to the real CF-3300 at WIDTH 29")
    else:
        print("FAIL — wrap/format differs from CF-3300"); rc = 1
    return rc


def _ordered(rows) -> bool:
    blob = "\n".join(rows)
    idx = [blob.find(e) for e in EXPECT]
    return all(i >= 0 for i in idx) and idx == sorted(idx)


if __name__ == "__main__":
    raise SystemExit(main())
