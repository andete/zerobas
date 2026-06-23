#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Keyword-token oracle probe — capture how real MSX-BASIC crunches REM / POKE /
PEEK (and the `'` REM abbreviation).

Clean-room methodology (see the clean-room firewall (CONTRIBUTING.md)): the
reference ROM is a *black box*. We type a direct-mode line into a real MSX-BASIC
(Philips VG-8020) and, the instant the interpreter reaches a known landmark,
dump the crunch buffer KBUF ($F41F). The bytes that come back are an observed
*output*: they reveal each keyword's token byte and the surrounding crunch
layout without reading the ROM's code.

The landmark trick (same one spec-tokenise.md used): every probe line contains
`bload"cas:",r`, and we break at TAPION ($00E1). By the time BLOAD opens the
tape the *entire* line is already crunched into KBUF, so KBUF holds the
tokenised form of all of it -- including whatever keyword we are studying.

  * POKE / PEEK go BEFORE the bload (they execute harmlessly: POKE 0,0 writes to
    ROM = no-op; a=PEEK(0) just reads). Then bload reaches TAPION and we stop.
  * REM and `'` swallow the rest of the line, so the bload goes FIRST -- it
    reaches TAPION (break) before the comment would ever execute, and KBUF still
    holds the crunched REM/`'` tail.

A cassette is inserted only so BLOAD reaches TAPION; its contents are never
read. Output feeds docs/spec-tokens-statements.md. No disassembly.
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

KBUF = 0xF41F   # crunch buffer: the tokenised line (MSX2 TH sysvar map)
KBUF_LEN = 48
TAPION = 0x00E1  # cassette open; interpreter is mid-BLOAD when PC reaches here
BLOAD_TOKEN = 0xCF  # already sourced in spec-tokenise.md; used as a structural anchor

MACHINE = "Philips_VG_8020"
OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")

# Each case: (label, typed line). All reach TAPION so the break is deterministic.
# Lowercase keywords on purpose: a match proves case-folding (the token, not the
# letters, is what lands in KBUF).
CASES = [
    ("POKE", 'poke 0,0:bload"cas:",r\r'),
    ("PEEK", 'b=peek(0):bload"cas:",r\r'),
    ("REM",  'bload"cas:",r:rem AB\r'),
    ("'",    "bload\"cas:\",r:'AB\r"),
]

# Full-crunch fidelity sweep (Step A). Each line is `a=<expr>:bload"cas:",r`, so
# the crunched <expr> lands in KBUF between the `=` token ($EF) and the `:` ($3A)
# that precedes the BLOAD landmark. We read off how the reference encodes integer
# constants (across magnitudes), `&H` hex constants, and the arithmetic
# operators. These bytes are an *observed output* -- never copied from a
# disassembly, never assumed from memory.
CRUNCH_CASES = [
    # decimal integers across magnitudes -> derive the constant encoding + its
    # boundaries (single-digit / one-byte / two-byte / where it turns into float)
    ("dec 0",     'a=0:bload"cas:",r\r'),
    ("dec 9",     'a=9:bload"cas:",r\r'),
    ("dec 10",    'a=10:bload"cas:",r\r'),
    ("dec 99",    'a=99:bload"cas:",r\r'),
    ("dec 255",   'a=255:bload"cas:",r\r'),
    ("dec 256",   'a=256:bload"cas:",r\r'),
    ("dec 1000",  'a=1000:bload"cas:",r\r'),
    ("dec 32767", 'a=32767:bload"cas:",r\r'),
    ("dec 32768", 'a=32768:bload"cas:",r\r'),   # int->float boundary (out of scope; documented)
    ("dec 65535", 'a=65535:bload"cas:",r\r'),
    # &H hex constants -> hex token + how the 16-bit value is carried
    ("hex 0",     'a=&h0:bload"cas:",r\r'),
    ("hex ff",    'a=&hff:bload"cas:",r\r'),
    ("hex d000",  'a=&hd000:bload"cas:",r\r'),
    ("hex ffff",  'a=&hffff:bload"cas:",r\r'),
    # arithmetic operators (and `=` already known = $EF)
    ("op +",      'a=1+2:bload"cas:",r\r'),
    ("op -",      'a=5-1:bload"cas:",r\r'),
    ("op *",      'a=2*3:bload"cas:",r\r'),
    # representative whole lines (must match zerobas byte-for-byte in Step A)
    ("whole poke", 'poke &hd000,2*3+4:bload"cas:",r\r'),
    ("whole peek", 'a=peek(&hd000):bload"cas:",r\r'),
]


def run_case(machine: str, line: str, type_delay: float, cas_path: str) -> bytes | None:
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="tokn_cap_")
    os.close(out_fd)
    cmd = [
        sys.executable, OMSX_RUN,
        "--machine", machine,
        "--cassette", cas_path,
        "--type", line,
        "--type-delay", str(type_delay),
        "--bp", hex(TAPION),
        "--reg", "PC",
        "--mem", f"memory:0x{KBUF:04X}:{KBUF_LEN}",
        "--out", out_path,
        "--timeout", "120",
    ]
    rc = subprocess.call(cmd)
    capture = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            capture = f.read()
        os.unlink(out_path)
    if rc != 0:
        print(f"  omsx_run exited {rc}", file=sys.stderr)
        return None
    key = f"mem.memory:0x{KBUF:04X}:{KBUF_LEN}="
    for cl in capture.splitlines():
        if cl.startswith(key):
            return bytes.fromhex(cl[len(key):])
    return None


def dump(label: str, data: bytes) -> None:
    print(f"\nKBUF for {label}:")
    for i in range(0, len(data), 16):
        row = data[i:i + 16]
        hexs = " ".join(f"{b:02X}" for b in row)
        asc = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in row)
        print(f"  {KBUF + i:04X}  {hexs:<47}  {asc}")


def crunched_expr(kbuf: bytes) -> bytes | None:
    """For an `a=<expr>:bload...` line, return the crunched <expr> bytes: the
    span between the first `=` token ($EF) and the next `:` ($3A)."""
    if 0xEF not in kbuf:
        return None
    i = kbuf.index(0xEF) + 1
    if 0x3A not in kbuf[i:]:
        return None
    j = i + kbuf[i:].index(0x3A)
    return kbuf[i:j]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE,
                    help=f"openMSX machine id (default {MACHINE})")
    ap.add_argument("--type-delay", type=float, default=5.0,
                    help="emulated seconds before typing (default 5)")
    args = ap.parse_args()

    # Minimal valid .cas so BLOAD reaches TAPION (payload never executed).
    cas = build_cas("TOK", 0xC000, 0xC000, bytes([0x18, 0xFE]))
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="tokn_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    results: dict[str, bytes] = {}
    for label, line in CASES:
        print(f"\n=== {label}: typing {line!r} ===")
        kbuf = run_case(args.machine, line, args.type_delay, cas_path)
        if kbuf is None:
            print(f"  <KBUF not captured for {label}>")
            continue
        results[label] = kbuf
        dump(label, kbuf)

    os.unlink(cas_path)

    # --- interpret: read off each keyword's token relative to known anchors ---
    print("\n" + "=" * 60)
    print("Observed keyword tokens:")
    ok = True

    def first_nonspace_token(kbuf: bytes) -> int | None:
        # POKE is the leading statement: token is the first non-space byte.
        for b in kbuf:
            if b != 0x20:
                return b
        return None

    if "POKE" in results:
        tok = first_nonspace_token(results["POKE"])
        print(f"  POKE  -> 0x{tok:02X}  (leading token of `poke 0,0:...`)")
        if tok == BLOAD_TOKEN or tok is None:
            print("  FAIL  POKE token looks wrong"); ok = False
    else:
        ok = False

    if "PEEK" in results:
        kb = results["PEEK"]
        # `b=peek(0)...`: PEEK token sits between the `=` token and the `(` (0x28).
        if 0x28 in kb:
            lp = kb.index(0x28)
            # bytes just before `(`, after the leading `b` and `=` token (2 bytes)
            seg = kb[2:lp]
            tok_hex = " ".join(f"{x:02X}" for x in seg)
            print(f"  PEEK  -> {tok_hex}  (bytes between `=` token and `(`)")
        else:
            print("  FAIL  no `(` found in PEEK KBUF"); ok = False

    if "REM" in results:
        kb = results["REM"]
        # after `bload\"cas:\",r` the next bytes are `:` then the REM token then
        # the verbatim comment. Find the BLOAD anchor, then the `:` (0x3A).
        if BLOAD_TOKEN in kb:
            i = kb.index(BLOAD_TOKEN)
            tail = kb[i + 1:]
            print(f"  REM   -> tail after BLOAD token: "
                  f"{' '.join(f'{x:02X}' for x in tail[:tail.index(0) if 0 in tail else len(tail)])}")
        else:
            print("  FAIL  no BLOAD anchor in REM KBUF"); ok = False

    if "'" in results:
        kb = results["'"]
        if BLOAD_TOKEN in kb:
            i = kb.index(BLOAD_TOKEN)
            tail = kb[i + 1:]
            print(f"  '     -> tail after BLOAD token: "
                  f"{' '.join(f'{x:02X}' for x in tail[:tail.index(0) if 0 in tail else len(tail)])}")
        else:
            print("  FAIL  no BLOAD anchor in ' KBUF"); ok = False

    # --- full-crunch fidelity sweep (constants / operators) --------------------
    print("\n" + "=" * 60)
    print("Full-crunch fidelity sweep (a=<expr>:bload...):")
    cas2 = build_cas("TOK", 0xC000, 0xC000, bytes([0x18, 0xFE]))
    cas2_fd, cas2_path = tempfile.mkstemp(suffix=".cas", prefix="tokn_probe2_")
    os.write(cas2_fd, cas2)
    os.close(cas2_fd)
    for label, line in CRUNCH_CASES:
        print(f"\n=== {label}: typing {line!r} ===")
        kbuf = run_case(args.machine, line, args.type_delay, cas2_path)
        if kbuf is None:
            print(f"  <KBUF not captured for {label}>")
            continue
        dump(label, kbuf)
        expr = crunched_expr(kbuf)
        if expr is not None:
            print(f"  crunched <expr> = {' '.join(f'{x:02X}' for x in expr)}")
        else:
            print("  (whole line; read the dump above)")
    os.unlink(cas2_path)

    print("\nRecord these bytes in spec-tokens-statements.md.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
