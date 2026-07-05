#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Phase-2 Step-0b spike — black-box the `CALL FORMAT` dispatch on Disk BASIC.

NOTE — PROVENANCE-CAPTURE SPIKE, NOT part of the acceptance gate. It recorded the
CALL FORMAT dispatch evidence (cited in disk/docs/file-channel-protocol.md) and
does not self-assert. The standing regression differential for CALL FORMAT is
disk_probe_format.py, run by `make diskbasic-acceptance` (see
disk/docs/diskbasic-verb-coverage.md). Kept for its provenance citations.

Complements diskbasic_probe_filechannel.py. The file verbs are built-in tokens
that leave PROCNM ($FD89) zero. `CALL FORMAT` / `_FORMAT` is instead a CALL-
dispatched extended statement, routed through the STATEMENT expansion ($4004),
which should populate PROCNM with the call name "FORMAT". This probe types
`CALL FORMAT` on the real National CF-3300, snapshots PROCNM + the screen at the
format prompt (the dispatch evidence), then answers the prompt and logs the
DSKIO ($4010) writes the format performs (the pattern an own DSKFMT must emit).

CLEAN-ROOM: black-box. BP on the documented DSKIO entry + read register/RAM/VRAM;
the disk ROM's code bytes are never read. DISK SAFETY: /tmp copy only.
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

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
MACHINE = "National_CF-3300"
SRC_DSK = os.path.expanduser("~/projects/zerobas/disk/test720.dsk")
DSKIO = 0x4010

# `type` needs each Enter as a separate event ~3s after its text, encoded as the
# \r ESCAPE (a raw CR byte breaks Tcl line parsing). See the file-channel probe.
SEQUENCE = [
    (12.0, "\r"),                 # clear "Enter date"
    # DSKIO logger installed at t=14
    (16.0, "CALL FORMAT"), (19.0, "\r"),
    # snap1 at t=23 — at the format prompt, PROCNM should read "FORMAT"
    (25.0, "A"),                  # answer "Drive name?(A,B)" (single key, usually no CR)
    (28.0, " "),                  # "Strike a key when ready"
    (31.0, "\r"),                 # belt-and-braces
    (40.0, "1"),                  # in case CHOICE asks a numbered format option
    (43.0, "\r"),
]
BP_INSTALL_T = 14.0
SNAP1_T = 23.0
DUMP_T = 52.0
QUIT_T = 54.0


def tcl_quote(s: str) -> str:
    out = []
    for ch in s:
        out.append("\\r" if ch == "\r" else ("\\" + ch if ch in '"\\[]$' else ch))
    return '"' + "".join(out) + '"'


def build_tcl(out_path: str) -> str:
    L = ["set throttle off",
         f"set __f [open {{{out_path}}} w]",
         "proc __hex {a l} { binary scan [debug read_block memory $a $l] H* h; return $h }",
         "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }",
         "proc __dskio {} {",
         "  global __f",
         "  set cy [expr {[reg F] & 1}]",
         '  puts $__f [format "DSKIO A=%02X B=%02X C=%02X DE=%04X HL=%04X CY=%d procnm=%s"'
         "    [reg A] [reg B] [reg C] [reg DE] [reg HL] $cy [__hex 0xFD89 6]]",
         "  flush $__f",
         "}",
         "proc __scr {tag} {",
         "  global __f",
         f'  puts $__f "$tag.procnm=[__hex 0xFD89 16]"',
         f'  puts $__f "$tag.scr1=[__hex_v 0x1800 768]"',
         "  flush $__f",
         "}",
         f"after time {BP_INSTALL_T} {{ debug set_bp 0x{DSKIO:04X} {{}} {{ __dskio }} }}",
         f"after time {SNAP1_T} {{ __scr SNAP1 }}"]
    for t, text in SEQUENCE:
        L.append(f"after time {t} {{ type {tcl_quote(text)} }}")
    L.append(f"after time {DUMP_T} {{ __scr FINAL }}")
    L.append(f"after time {QUIT_T} {{ close $__f; exit }}")
    return "\n".join(L) + "\n"


def show(out: str):
    for line in open(out):
        line = line.rstrip("\n")
        if ".scr1=" in line:
            tag, _, hexv = line.partition("=")
            d = bytes.fromhex(hexv)
            print(f"--- {tag} ---")
            for r in range(24):
                s = "".join(chr(c) if 32 <= c < 127 else " "
                            for c in d[r*32:(r+1)*32]).rstrip()
                if s.strip():
                    print(f"{r:2}|{s}")
        elif ".procnm=" in line:
            tag, _, hexv = line.partition("=")
            b = bytes.fromhex(hexv)
            txt = "".join(chr(c) if 32 <= c < 127 else "." for c in b)
            print(f"{tag} = {hexv}  ('{txt}')")
        else:
            print(line)


def main() -> int:
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="fmt_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    out = "/tmp/diskbasic_format.txt"
    open(out + ".tcl", "w").write(build_tcl(out))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        [OMSX, "-machine", MACHINE, "-diska", dsk,
         "-command", "set renderer none", "-script", out + ".tcl"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 130
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
