#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tokenisation oracle probe — capture how real MSX-BASIC crunches a line.

Clean-room methodology (see the clean-room firewall (CONTRIBUTING.md)): the
reference ROM is a *black box*. We type `BLOAD"CAS:",R` into a real MSX-BASIC
(Philips VG-8020) and, the instant the interpreter executes the statement (PC
reaches TAPION, $00E1), dump the crunch buffer KBUF. The bytes that come back
are an observed *output*: they reveal the token byte for BLOAD and the
direct-mode crunch layout (token + verbatim args + 0x00) without reading the
ROM's code.

Why break at TAPION: by the time BLOAD opens the tape, the whole line has
already been crunched into KBUF and is being interpreted, so KBUF still holds
the tokenised form. A cassette is inserted only so BLOAD gets far enough to
reach TAPION; its contents are never read (the breakpoint fires first).

Output feeds basic/docs/spec-tokenise.md. No disassembly is consulted.
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import os
import subprocess
import sys
import tempfile


from cas_encode import build_cas  # noqa: E402

# Crunch / input buffers (source: MSX2 Technical Handbook sysvar map / MSX
# Assembly Page; addresses also in tools/msx_symbols.py).
KBUF = 0xF41F  # crunch buffer: the tokenised line
BUF = 0xF55E   # line input buffer: the raw ASCII line
BUF_LEN = 48

TAPION = 0x00E1  # cassette open; interpreter is mid-BLOAD when PC reaches here

MACHINE = "Philips_VG_8020"
OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")

# Lowercase on purpose: BASIC stores the keyword *token*, not the letters, so a
# match proves case-folding. Ends with \r (Enter).
LINE = 'bload"cas:",r\r'

# Expected crunch (oracle-confirmed): BLOAD -> single token byte, the rest of
# the line kept verbatim as ASCII, 0x00 terminator.
BLOAD_TOKEN = 0xCF


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE,
                    help=f"openMSX machine id (default {MACHINE})")
    ap.add_argument("--type-delay", type=float, default=5.0,
                    help="emulated seconds to wait before typing (default 5)")
    args = ap.parse_args()

    # Minimal valid .cas so BLOAD reaches TAPION (payload never executed).
    cas = build_cas("TOK", 0xC000, 0xC000, bytes([0x18, 0xFE]))
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="tok_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="tok_cap_")
    os.close(out_fd)

    cmd = [
        sys.executable, OMSX_RUN,
        "--machine", args.machine,
        "--cassette", cas_path,
        "--type", LINE,
        "--type-delay", str(args.type_delay),
        "--bp", hex(TAPION),
        "--reg", "PC",
        "--mem", f"memory:0x{KBUF:04X}:{BUF_LEN}",
        "--mem", f"memory:0x{BUF:04X}:{BUF_LEN}",
        "--out", out_path,
        "--timeout", "120",
    ]
    print(f"typing: {LINE!r}")
    print(f"running: {' '.join(cmd)}\n")

    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"\nomsx_run exited with code {rc}", file=sys.stderr)
        return rc

    with open(out_path) as f:
        capture = f.read()
    print(capture)

    kbuf = _extract(capture, f"mem.memory:0x{KBUF:04X}:{BUF_LEN}=")
    buf = _extract(capture, f"mem.memory:0x{BUF:04X}:{BUF_LEN}=")
    _dump("KBUF (crunched)", KBUF, kbuf)
    _dump("BUF  (raw ASCII)", BUF, buf)

    ok = True
    if kbuf is None or BLOAD_TOKEN not in kbuf:
        print(f"FAIL  BLOAD token 0x{BLOAD_TOKEN:02X} not found in KBUF")
        ok = False
    else:
        i = kbuf.index(BLOAD_TOKEN)
        tail = kbuf[i + 1:]
        term = tail.index(0x00) if 0x00 in tail else -1
        args_ascii = tail[:term] if term >= 0 else tail
        print(f"PASS  BLOAD -> token 0x{BLOAD_TOKEN:02X} at KBUF offset {i}")
        print(f"PASS  args kept verbatim: {args_ascii!r}, 0x00-terminated"
              if term >= 0 else "FAIL  no 0x00 terminator after args")
        if term < 0:
            ok = False

    os.unlink(cas_path)
    os.unlink(out_path)
    return 0 if ok else 1


def _extract(capture: str, key: str) -> bytes | None:
    for line in capture.splitlines():
        if line.startswith(key):
            return bytes.fromhex(line[len(key):])
    return None


def _dump(label: str, base: int, data: bytes | None) -> None:
    if data is None:
        print(f"\n{label}: <not captured>")
        return
    print(f"\n{label} (0x{base:04X}..):")
    for i in range(0, len(data), 16):
        row = data[i:i + 16]
        hexs = " ".join(f"{b:02X}" for b in row)
        asc = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in row)
        print(f"  {base + i:04X}  {hexs:<47}  {asc}")


if __name__ == "__main__":
    raise SystemExit(main())
