#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Phase-2 Step-2 spike — pin the exact `FILES` listing format of real Disk BASIC.

NOTE — PROVENANCE-CAPTURE SPIKE, NOT part of the acceptance gate. It recorded the
FILES listing format (cited in basic/PROVENANCE.md §FILES and basic/files.asm) and
does not self-assert. The standing regression differential for FILES is
disk_probe_files.py, run by `make diskbasic-acceptance` (see
disk/docs/diskbasic-verb-coverage.md). Kept for its provenance citations.

Before zerobas implements its own `FILES` statement handler it must reproduce the
on-screen layout the genuine National CF-3300 Disk BASIC produces: column count,
field width, name/extension spacing, ordering, and the leading/trailing lines.
This probe boots the real CF-3300 on a /tmp copy of test720.dsk (which holds
TEST.BIN, HI.TXT, PROG.BIN, PROG.BAS, PROG2.BAS), types `FILES`, and dumps the
SCREEN-1 name table so the format can be transcribed verbatim into the spec.

CLEAN-ROOM: black-box. We only read VRAM (the rendered screen) and never the disk
ROM's code bytes. DISK SAFETY: /tmp copy only (FILES is read-only, but keep the
discipline — see [[test-disk-mutation-gotcha]]).
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

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
MACHINE = "National_CF-3300"
SRC_DSK = os.path.expanduser("~/projects/zerobas/disk/test720.dsk")

# Each Enter is a separate event ~3s after its text, encoded as the \r ESCAPE
# (a raw CR byte breaks Tcl line parsing). See diskbasic_probe_filechannel.py.
SEQUENCE = [
    (12.0, "\r"),                 # clear "Enter date"
    (16.0, "FILES"), (19.0, "\r"),
]
SNAP_T = 24.0
QUIT_T = 26.0


def tcl_quote(s: str) -> str:
    out = []
    for ch in s:
        out.append("\\r" if ch == "\r" else ("\\" + ch if ch in '"\\[]$' else ch))
    return '"' + "".join(out) + '"'


def build_tcl(out_path: str) -> str:
    L = ["set throttle off",
         f"set __f [open {{{out_path}}} w]",
         "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }",
         "proc __scr {tag} {",
         "  global __f",
         f'  puts $__f "$tag.scr1=[__hex_v 0x1800 768]"',
         "  flush $__f",
         "}"]
    for t, text in SEQUENCE:
        L.append(f"after time {t} {{ type {tcl_quote(text)} }}")
    L.append(f"after time {SNAP_T} {{ __scr FILES }}")
    L.append(f"after time {QUIT_T} {{ close $__f; exit }}")
    return "\n".join(L) + "\n"


def show(out: str):
    for line in open(out):
        line = line.rstrip("\n")
        if ".scr1=" in line:
            tag, _, hexv = line.partition("=")
            d = bytes.fromhex(hexv)
            print(f"--- {tag} (32col) ---")
            for r in range(24):
                s = "".join(chr(c) if 32 <= c < 127 else " "
                            for c in d[r*32:(r+1)*32]).rstrip()
                if s.strip():
                    print(f"{r:2}|{s}")
        else:
            print(line)


def main() -> int:
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="files_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    out = "/tmp/diskbasic_files.txt"
    open(out + ".tcl", "w").write(build_tcl(out))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        omsx_preflight.guarded([OMSX, "-machine", MACHINE, "-diska", dsk,
         "-command", "set renderer none; set sound_driver null", "-script", out + ".tcl"]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 90
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        sys.exit("TIMEOUT")
    os.unlink(dsk)
    if not os.path.exists(out):
        sys.exit("no capture")
    show(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
