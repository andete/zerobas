#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Phase-2 Step-0 spike — black-box the MSX Disk BASIC file-channel contract.

NOTE — PROVENANCE-CAPTURE SPIKE, NOT part of the acceptance gate. It recorded
observed facts (cited in disk/docs/file-channel-protocol.md) and does not
self-assert. The standing regression differentials for these verbs are
disk_probe_filewrite/fileread/append.py, run by `make diskbasic-acceptance`
(see disk/docs/diskbasic-verb-coverage.md). Kept for its provenance citations.

Drives the REAL National CF-3300 Disk BASIC (a genuine MSX1 disk machine) through
a full sequential file-channel sequence and logs every DSKIO ($4010) call's input
registers + carry (read/write direction), to learn how `OPEN`/`PRINT#`/`INPUT#`/
`CLOSE` move bytes under the hood.

What the prior observation already established (do not re-derive):
  * file verbs reach disk via DSKIO ($4010), NOT via HPHYD ($FFA7);
  * the STATEMENT handler ($4004 word) does NOT fire for `FILES` (built-in token,
    not a CALL-expansion); the DEVICE handler word ($4006) is $0000;
  * PROCNM ($FD89) / DEVICE ($FD99) stay zero for these verbs.

This probe adds the I/O *contract*: the DSKIO trace for a write+read round trip.

CLEAN-ROOM: black-box only. We set a breakpoint on the DOCUMENTED DSKIO entry
offset ($4010) and read the live Z80 register file; we never read or disassemble
the disk ROM's code bytes. Disk-ROM behaviour is observed, not inspected.

DISK SAFETY: runs on a /tmp COPY of the test image — the committed .dsk is never
mounted (Disk BASIC OPEN-for-OUTPUT / PRINT# would mutate it).
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
HPHYD = 0xFFA7

# Typed file-channel sequence (emulated-seconds schedule). The real BIOS boots
# slowly, so timings are generous; each Enter is a SEPARATE, slightly-later event
# (a CR sharing a burst with text is dropped under `throttle off`).
# openMSX `type` drops a CR that follows text too closely under `throttle off`,
# so each Enter is a SEPARATE event ~3s after its command (proven by datecheck).
SEQUENCE = [
    (12.0, "\r"),                                    # clear the "Enter date" prompt
    # DSKIO logger installed at t=14 (see tcl)
    (16.0, 'OPEN "O.DAT" FOR OUTPUT AS #1'), (19.0, "\r"),
    (22.0, 'PRINT #1,"HELLO"'),               (25.0, "\r"),
    (28.0, "CLOSE #1"),                        (31.0, "\r"),
    (34.0, 'OPEN "O.DAT" FOR INPUT AS #1'),   (37.0, "\r"),
    (40.0, "LINE INPUT #1,A$"),               (43.0, "\r"),
    (46.0, "CLOSE #1"),                        (49.0, "\r"),
]
BP_INSTALL_T = 14.0
DUMP_T = 52.0
QUIT_T = 54.0


def tcl_quote(s: str) -> str:
    # Tcl double-quoted literal. CR must be the ESCAPE \r (backslash-r), never a
    # raw 0x0d byte — a literal CR mid-script breaks Tcl's line parsing, which
    # silently drops the Enter event (the bug that made every command sit unentered).
    out = []
    for ch in s:
        if ch == "\r":
            out.append("\\r")
        elif ch in '"\\[]$':
            out.append("\\" + ch)
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def build_tcl(out_path: str) -> str:
    L = ["set throttle off",
         f"set __f [open {{{out_path}}} w]",
         # DSKIO logger: log input regs + carry (F bit0) + page-1 slot if available
         "proc __dskio {} {",
         "  global __f",
         "  set cy [expr {[reg F] & 1}]",
         '  set slot "?"',
         "  catch { set slot [get_selected_slot 1] }",
         '  puts $__f [format "DSKIO A=%02X B=%02X C=%02X DE=%04X HL=%04X CY=%d slot=%s"'
         "    [reg A] [reg B] [reg C] [reg DE] [reg HL] $cy $slot]",
         "  flush $__f",
         "}",
         "proc __hex {a l} { binary scan [debug read_block memory $a $l] H* h; return $h }",
         "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }",
         "proc __dump {} {",
         "  global __f",
         f'  puts $__f "hphyd=[__hex 0x{HPHYD:04X} 5]"',
         '  puts $__f "procnm=[__hex 0xFD89 16]"',
         '  puts $__f "device=[__hex 0xFD99 1]"',
         # broad sweep of the disk/BASIC work area for file-channel structures
         '  puts $__f "wrk_F320=[__hex 0xF320 64]"',
         '  puts $__f "wrk_F860=[__hex 0xF860 48]"',
         '  puts $__f "scr1=[__hex_v 0x1800 768]"',     # CF-3300 Disk BASIC = SCREEN 1
         "  flush $__f",
         "}",
         f"after time {BP_INSTALL_T} {{ debug set_bp 0x{DSKIO:04X} {{}} {{ __dskio }} }}"]
    for t, text in SEQUENCE:
        L.append(f"after time {t} {{ type {tcl_quote(text)} }}")
    L.append(f"after time {DUMP_T} {{ __dump }}")
    L.append(f"after time {QUIT_T} {{ close $__f; exit }}")
    return "\n".join(L) + "\n"


def main() -> int:
    if not os.path.isfile(SRC_DSK):
        sys.exit(f"missing test image: {SRC_DSK}")
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="fc_", delete=False).name
    shutil.copy(SRC_DSK, dsk)                       # /tmp copy — never the committed image
    out = "/tmp/diskbasic_filechannel.txt"
    tcl = out + ".tcl"
    open(tcl, "w").write(build_tcl(out))
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", MACHINE, "-diska", dsk,
           "-command", "set renderer none", "-script", tcl]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 130
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        sys.exit("TIMEOUT")
    os.unlink(dsk)
    if not os.path.exists(out):
        sys.exit("no capture (machine/ROMs missing?)")
    # Print DSKIO trace + work-area lines verbatim; decode the screen dumps.
    for line in open(out):
        line = line.rstrip("\n")
        if line.startswith(("scr0=", "scr1=")):
            tag, _, hexv = line.partition("=")
            cols = 40 if tag == "scr0" else 32
            data = bytes.fromhex(hexv)
            rows = [("".join(chr(c) if 32 <= c < 127 else " "
                             for c in data[r*cols:(r+1)*cols])).rstrip()
                    for r in range(len(data)//cols)]
            shown = [f"{i:2}|{r}" for i, r in enumerate(rows) if r.strip()]
            print(f"--- {tag} ({cols}col) ---")
            print("\n".join(shown) if shown else "(blank)")
        else:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
