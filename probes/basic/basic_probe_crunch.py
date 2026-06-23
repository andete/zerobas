#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Differential crunch probe — prove zerobas tokenises byte-for-byte like a real
MSX-BASIC ROM (Step A).

For each test line we feed the *identical* line (ending in `:bload"cas:",r`) to
both sides and break both at TAPION ($00E1):

  * reference (Philips VG-8020, built-in BASIC) crunches into KBUF ($F41F);
  * zerobas (the cartridge) crunches into TOKBUF (its fixed sysvars.inc address).

Both reach TAPION mid-BLOAD with the *whole* line already crunched, so each
buffer holds the tokenised line, 0x00-terminated. We compare the two byte ranges
up to and including the terminator: equal == byte-identical crunch.

Clean-room: this only *compares observed outputs*. No disassembly; the reference
ROM is a black box. See the clean-room firewall (CONTRIBUTING.md).
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
import subprocess
import sys
import tempfile


from cas_encode import build_cas  # noqa: E402

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")
MACHINE = "Philips_VG_8020"
TAPION = 0x00E1
KBUF = 0xF41F     # reference crunch buffer (MSX2 TH sysvar map)
TOKBUF = 0xE160   # zerobas crunch buffer (zerobas/src/sysvars.inc)
DUMPLEN = 48

# Test lines (the probe appends `:bload"cas:",r`). They exercise the integer
# encoding across magnitudes, &H, the operators, and representative whole lines.
LINES = [
    "a=0", "a=9", "a=10", "a=255", "a=256", "a=32767",
    "a=&h0", "a=&hff", "a=&hd000", "a=&hffff",
    "a=1+2", "a=5-1", "a=2*3",
    "poke &hd000,2*3+4",
    "a=peek(&hd000)",
    # DATA stores its items as verbatim ASCII (oracle), not crunched tokens;
    # these confirm zerobas copies the body byte-for-byte (and stops at ':').
    "data 5,6", "data -5,&hff", "data 300,abc",
]

# Crunch-only lines: their bytes are validated, but the body must NOT execute
# (a direct `goto 40` errors with "undefined line"; `gosub`/`for`/`next`/`restore`
# aren't direct-executable; `end`/`stop` halt; a bare comparison isn't a
# statement). So the freeze-bload is *prepended* — it hands off at TAPION first,
# freezing the crunch buffer with the whole line already tokenised, while the
# body after the ':' is crunched but never run. (spec-controlflow.md:
# keyword tokens from Table 2.20, the $0E line-number code from Figure 2.12,
# and the '<' $F0 / '>' $EE relational tokens.)
CRUNCH_ONLY = [
    "goto 40", "gosub 100", "restore 50",
    # PRINT USING formatted output. USING = $E4 (oracle-locked); the format string is
    # kept verbatim ASCII in its quotes (`#`=$23, `\ \`=$5C 20 5C), then ';' + values.
    'print using"###";5',
    r'print using"\ \";a$',
    # CALL FORMAT. CALL = $CA; the extended-statement NAME after CALL (or the '_'
    # abbreviation) is kept verbatim, NOT keyword-crunched: `call format` -> CA 20
    # "FORMAT", `_format` -> 5F "FORMAT". The non-CALL `format=5` -> FOR($82)+MAT
    # confirms the verbatim rule is CALL-scoped (keywords still crunch inside names).
    "call format",
    "_format",
    "call music",
    "format=5",
    "if a then 40", "if a then b=1 else b=2",
    "for i=1 to 10 step 2", "next i", "end", "stop",
    "a<=b", "a>=5", "a<>0",
    # SAVE / BSAVE statement tokens (oracle-LOCKED, Philips VG-8020). BSAVE = $D0,
    # SAVE = $BA, both single-byte statement tokens; the quoted filename is kept
    # verbatim ASCII and each &H address crunches to $0C <lo> <hi>. These would
    # WRITE a file / error in direct mode, so they are CRUNCH_ONLY (the prepended
    # freeze-bload halts at TAPION with the whole line already crunched). The
    # &HC0C1/&HC031/&HC0C2 case has no embedded $00 so it is compared in FULL;
    # the &HC000 case (0C 00 C0) is compared up to its first embedded $00, exactly
    # like the line-number cases above (e.g. `goto 40` -> 0E 28 00).
    'bsave"x",&hc0c1,&hc031,&hc0c2',
    'bsave"a:prog.bin",&hc000,&hc031',
    'save"a:prog"',
    'save"a:prog",a',
    # Disk BASIC FILES token (Phase 2). FILES = $B7 (MSX2 TH Table 2.20); the
    # disk-extension keyword is in the MAIN ROM's reserved-word table even on the
    # diskless VG-8020 reference, so it crunches to the same single token byte.
    "files",
    # MERGE (merge an ASCII program from disk). Token $B6, in the main ROM table
    # like FILES; the filename is kept verbatim ASCII.
    'merge"prog.bas"',
    # Phase 2 sequential file-channel verbs. OPEN $B0, INPUT $85, LINE $AF,
    # CLOSE $B4; "AS" and "#" stay verbatim ASCII; the channel digit crunches to
    # the $11+n single-digit token (1 -> $12). All in the main ROM table.
    'open"hi.txt" for input as #1',
    'line input#1,a$',
    'input#1,a$',
    # INPUT$(n,#f): a string FUNCTION, but not a dedicated token — "INPUT$" crunches
    # to INPUT ($85) + '$' ($24); the args ( n , # f ) stay literal ASCII.
    'a$=input$(2,#1)',
    'close#1',
    # Write path. "OUTPUT" crunches to OUT($9C)+PUT($B3) — two reserved words, not
    # one keyword; PRINT# is the ordinary PRINT token ($91) + '#n,'.
    'open"o.dat" for output as #1',
    'print#1,"hello"',
    # APPEND mode. "APPEND" is NOT a reserved word on the main ROM — it crunches to
    # the name "APP" (verbatim ASCII 41 50 50) + the END token ($81), so OPEN's mode
    # parser matches APP+END. zerobas (no APPEND keyword either) emits the same bytes.
    'open"a.dat" for append as #1',
    # File management: KILL = $D4, NAME = $D3 (MSX2 TH Table 2.20); "AS" verbatim.
    'kill"a:out.txt"',
    'name"old.txt" as "new.txt"',
    # File-info functions: $FF-prefixed (EOF=$FF$AB, LOF=$FF$AD, DSKF=$FF$A6).
    'a=eof(1)',
    'a=lof(1)',
    'a=dskf(0)',
    # MAXFILES (Phase 2 multi-channel config): "MAXFILES" crunches to TWO reserved
    # words — MAX ($CD) + FILES ($B7) — exactly like OUTPUT = OUT+PUT; then `=2`.
    'maxfiles=2',
    # Random-access conversions (Phase 2c). $FF-prefixed function tokens: MKI$=$FF$AE
    # (the '$' is PART of the keyword), CVI=$FF$A8. Float siblings need Phase-3 floats.
    'a$=mki$(258)',
    'a=cvi(b$)',
    # Random-access record verbs (Phase 2c slice 1). Single-byte statement tokens
    # FIELD=$B1, LSET=$B8, RSET=$B9 (oracle-locked; MSX2 TH Table 2.20). "AS" stays
    # verbatim ASCII; the channel digit + small widths crunch to $11+n single-digit
    # tokens (#1 -> 23 12; the 2 -> 13). PUT/GET (the disk record I/O) are slice 2.
    'field#1,2 as a$',
    'lset a$="x"',
    'rset b$="y"',
    # GET/PUT random record I/O (slice 2). Single-byte statement tokens GET=$B2,
    # PUT=$B3 (oracle-locked); `#f` + record number crunch to $11+n digit tokens
    # (get#1 -> B2 23 12; put#1,1 -> B3 23 12 2C 12).
    "get#1",
    "put#1,1",
]


def dump_buf(machine, cart, full_line, addr, separate_enter):
    """Run one side, break at TAPION, return the crunch buffer bytes."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="crunch_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine]
    if cart:
        cmd += ["--cart", cart]
    cmd += ["--cassette", CAS_PATH]
    if separate_enter:
        # zerobas REPL: a trailing CR in the same burst is dropped under
        # `throttle off`, so inject Enter as a separate, later event.
        cmd += ["--type", full_line, "--type-delay", "8",
                "--type", "\r", "--type-delay", "12"]
    else:
        cmd += ["--type", full_line + "\r", "--type-delay", "5"]
    cmd += ["--bp", hex(TAPION), "--reg", "PC",
            "--mem", f"memory:0x{addr:04X}:{DUMPLEN}",
            "--out", out_path, "--timeout", "30"]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    if f"reg.PC=0x{TAPION:04X}" not in cap:
        return None  # never reached TAPION (crunch/exec failed before BLOAD)
    key = f"mem.memory:0x{addr:04X}:{DUMPLEN}="
    for cl in cap.splitlines():
        if cl.startswith(key):
            return bytes.fromhex(cl[len(key):])
    return None


def crunched(buf):
    """The crunched line, up to and including its terminator.

    A constant's value bytes can contain 0x00 (e.g. 256 -> 1C 00 01, &HD000 ->
    0C 00 D0), so the *first* 0x00 is not necessarily the terminator. Every test
    line ends in `:bload"cas:",r`, whose crunch (CF 22 63 61 73 3A 22 2C 52 00)
    has no embedded 0x00 — so the real terminator is the first 0x00 at or after
    the BLOAD token (CF). Including the value bytes means embedded-0x00 cases are
    actually compared, not truncated."""
    if buf is None or 0xCF not in buf:
        return None
    i = buf.index(0xCF)
    if 0 not in buf[i:]:
        return None
    z = i + buf[i:].index(0)
    return buf[:z + 1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    args = ap.parse_args()

    global CAS_PATH
    cas = build_cas("TOK", 0xC000, 0xC000, bytes([0x18, 0xFE]))
    cas_fd, CAS_PATH = tempfile.mkstemp(suffix=".cas", prefix="crunch_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    ok = True

    def test(body, full_line):
        nonlocal ok
        ref = crunched(dump_buf(args.machine, None, full_line, KBUF, separate_enter=False))
        zb = crunched(dump_buf(args.machine, args.cart, full_line, TOKBUF, separate_enter=True))
        same = ref is not None and zb is not None and ref == zb
        ok = ok and same
        rs = " ".join(f"{b:02X}" for b in ref) if ref else "<no TAPION>"
        zs = " ".join(f"{b:02X}" for b in zb) if zb else "<no TAPION>"
        print(f"{'PASS' if same else 'FAIL'}  {body}")
        print(f"        ref: {rs}")
        if not same:
            print(f"        zb : {zs}")

    for body in LINES:                       # executable lines: bload trails
        test(body, f'{body}:bload"cas:",r')
    for body in CRUNCH_ONLY:                 # non-executing bodies: bload leads
        test(body, f'bload"cas:",r:{body}')

    os.unlink(CAS_PATH)
    print("\nALL PASS — crunch is byte-identical" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
