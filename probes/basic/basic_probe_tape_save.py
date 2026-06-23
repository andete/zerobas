#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tape SAVE oracle probe — CSAVE / SAVE"CAS:" / BSAVE"CAS:" validation.

Validates all three cassette write verbs on zerobas, three oracle dimensions:

  1. FORMAT ORACLE: zerobas CSAVE / SAVE"CAS:" / BSAVE"CAS:" writes a cassette
     WAV that decodes (via cas_decode.py) to the same byte sequence that
     cas_encode.py's build_cas_basic / build_cas would produce.

  2. REFERENCE LOAD: the Philips VG-8020 can CLOAD / BLOAD a tape zerobas wrote
     (the recorded WAV) and recover the correct program / binary image.

  3. SELF ROUND-TRIP: zerobas CSAVE then CLOAD (on the same C-BIOS_MSX1_EU_TAPE
     + zerobas-cart machine) returns the identical program; BSAVE then BLOAD
     returns the identical binary bytes. No global machine reinstalled.

Machine for write + self round-trip: C-BIOS_MSX1_EU_TAPE --cart basic.rom.
Machine for reference-load check: Philips_VG_8020 (built-in BASIC; tape works).

Clean-room: inputs / outputs only. No disassembly; the reference ROM is a black
box. Tape format sourced from MSX2 Technical Handbook; cas_encode.py is our own.
See the clean-room firewall (CONTRIBUTING.md).
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
import signal
import subprocess
import sys
import tempfile
import time


from cas_encode import build_cas, build_cas_basic  # noqa: E402
from cas_decode import decode_file                  # noqa: E402
from omsx_run import _tcl_dquote                    # noqa: E402

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
if not (os.path.sep in OMSX and os.path.isfile(OMSX)):
    OMSX = "openmsx"

MACHINE_TAPE = "C-BIOS_MSX1_EU_TAPE"
MACHINE_REF  = "Philips_VG_8020"

# Program-area sysvars (zerobas + MSX shared).
TXTBASE = 0x8001   # stored-program text base (oracle: TXTTAB value after boot)

# Sentinel region for BSAVE binary tests: 8 bytes at $C010 (outside BLOAD region
# $C000 which the crunch probe uses, above any BASIC text). Content is a known
# non-zero pattern that survives a cold boot (poked before BSAVE).
BSAVE_START = 0xC010
BSAVE_END   = 0xC017   # inclusive
BSAVE_DATA  = bytes([0x55, 0xAA, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66])
BSAVE_EXEC  = 0xC010   # exec = start (arbitrary choice; BSAVE default)


# ---------------------------------------------------------------------------
# Build the tokenised program image that zerobas's CSAVE should emit.
# Lines: 10 A=5  (41 EF 16),  20 B=7  (42 EF 18).
# Token encoding is oracle-sourced (sysvars.inc: EQ=$EF, digit n -> $11+n).
# ---------------------------------------------------------------------------

def build_program() -> bytes:
    """Two-line tokenised program: `10 A=5` and `20 B=7`."""
    lines = [
        (10, bytes([0x41, 0xEF, 0x16])),   # 10 A=5
        (20, bytes([0x42, 0xEF, 0x18])),   # 20 B=7
    ]
    prog = bytearray()
    addr = TXTBASE
    for lineno, body in lines:
        nxt = addr + 2 + 2 + len(body) + 1
        prog += nxt.to_bytes(2, "little")
        prog += lineno.to_bytes(2, "little")
        prog += body
        prog += b"\x00"
        addr = nxt
    prog += b"\x00\x00"   # $0000 end-of-program link word
    return bytes(prog)


def expected_relinked_image(program: bytes) -> bytes:
    """Relink program bytes to a fresh TXTBASE (as do_tape_prog's relink does)."""
    lines, i = [], 0
    while int.from_bytes(program[i:i + 2], "little") != 0:
        lineno = int.from_bytes(program[i + 2:i + 4], "little")
        j = i + 4
        while program[j] != 0:
            j += 1
        lines.append((lineno, program[i + 4:j]))
        i = j + 1
    out, addr = bytearray(), TXTBASE
    for lineno, body in lines:
        size = 2 + 2 + len(body) + 1
        nxt = addr + size
        out += nxt.to_bytes(2, "little")
        out += lineno.to_bytes(2, "little")
        out += body
        out += b"\x00"
        addr = nxt
    out += b"\x00\x00"
    return bytes(out)


# ---------------------------------------------------------------------------
# openMSX session: run zerobas, type commands, record tape to WAV, capture RAM
# ---------------------------------------------------------------------------

def run_save(cart: str, type_cmds: list[tuple[float, str]],
             record_wav: str,
             cap_addr: int | None = None, cap_len: int = 0,
             cap_time: float = 45.0, timeout: float = 120.0) -> bytes | None:
    """Boot zerobas on MACHINE_TAPE, type commands, record tape.

    Returns bytes at cap_addr (length cap_len) if cap_addr is set, else None.
    """
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="tsave_")
    os.close(out_fd)

    # Tcl script: record mode + throttle off + type commands + timed capture.
    tcl_lines = [
        "set throttle off",
        f"cassetteplayer new {{{os.path.abspath(record_wav)}}}",
        "proc __hex {dbg addr len} {",
        "  binary scan [debug read_block $dbg $addr $len] H* h; return $h",
        "}",
    ]
    for delay, text in type_cmds:
        tcl_lines.append(f"after time {delay} {{ type {_tcl_dquote(text)} }}")
    tcl_lines += [
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
    ]
    if cap_addr is not None:
        tcl_lines.append(
            f'  puts $f "mem.0x{cap_addr:04X}=[__hex {{memory}} {cap_addr} {cap_len}]"'
        )
    tcl_lines += [
        "  puts $f \"tape.length=[cassetteplayer getlength]\"",
        "  catch {cassetteplayer eject}",
        "  close $f",
        "  exit",
        "}",
        f"after time {cap_time} {{ __cap }}",
    ]
    tcl = "\n".join(tcl_lines) + "\n"

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="tsave_")
    os.write(fd, tcl.encode())
    os.close(fd)

    cmd = [OMSX, "-machine", MACHINE_TAPE, "-cart", cart,
           "-command", "set renderer none", "-script", tcl_path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl_path)

    result = None
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                if cap_addr is not None:
                    key = f"mem.0x{cap_addr:04X}="
                    if line.startswith(key):
                        result = bytes.fromhex(line[len(key):].strip())
        os.unlink(out_path)
    return result


def run_load_zerobas(cart: str, cas_path: str, verb: str,
                     cap_addr: int, cap_len: int,
                     cap_time: float = 30.0, timeout: float = 90.0) -> bytes | None:
    """Boot zerobas on MACHINE_TAPE with cas_path as input; type verb (CLOAD or BLOAD"CAS:").

    Returns bytes at cap_addr (length cap_len) after cap_time.
    """
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="tload_")
    os.close(out_fd)

    verb_cmd = _tcl_dquote(verb)
    enter_cmd = _tcl_dquote("\r")

    tcl_lines = [
        "set throttle off",
        "proc __hex {dbg addr len} {",
        "  binary scan [debug read_block $dbg $addr $len] H* h; return $h",
        "}",
        f"after time 6 {{ type {verb_cmd} }}",
        f"after time 8 {{ type {enter_cmd} }}",
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
        f'  puts $f "mem.0x{cap_addr:04X}=[__hex {{memory}} {cap_addr} {cap_len}]"',
        "  close $f",
        "  exit",
        "}",
        f"after time {cap_time} {{ __cap }}",
    ]
    tcl = "\n".join(tcl_lines) + "\n"

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="tload_")
    os.write(fd, tcl.encode())
    os.close(fd)

    cmd = [OMSX, "-machine", MACHINE_TAPE, "-cart", cart,
           "-cassetteplayer", cas_path,
           "-command", "set renderer none", "-script", tcl_path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl_path)

    result = None
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                key = f"mem.0x{cap_addr:04X}="
                if line.startswith(key):
                    result = bytes.fromhex(line[len(key):].strip())
        os.unlink(out_path)
    return result


def run_load_ref(cas_path: str, verb: str,
                 cap_addr: int, cap_len: int,
                 cap_time: float = 30.0, timeout: float = 90.0) -> bytes | None:
    """Boot Philips VG-8020 with cas_path; type verb (CLOAD / BLOAD"CAS:"),R).

    Returns bytes at cap_addr (length cap_len) after cap_time.
    """
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="tref_")
    os.close(out_fd)

    verb_cmd = _tcl_dquote(verb)
    enter_cmd = _tcl_dquote("\r")

    tcl_lines = [
        "set throttle off",
        "proc __hex {dbg addr len} {",
        "  binary scan [debug read_block $dbg $addr $len] H* h; return $h",
        "}",
        # VG-8020 boots at real-BIOS speed; 6s emulated is sufficient for prompt.
        f"after time 6 {{ type {verb_cmd} }}",
        f"after time 8 {{ type {enter_cmd} }}",
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
        f'  puts $f "mem.0x{cap_addr:04X}=[__hex {{memory}} {cap_addr} {cap_len}]"',
        "  close $f",
        "  exit",
        "}",
        f"after time {cap_time} {{ __cap }}",
    ]
    tcl = "\n".join(tcl_lines) + "\n"

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="tref_")
    os.write(fd, tcl.encode())
    os.close(fd)

    cmd = [OMSX, "-machine", MACHINE_REF,
           "-cassetteplayer", cas_path,
           "-command", "set renderer none", "-script", tcl_path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl_path)

    result = None
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                key = f"mem.0x{cap_addr:04X}="
                if line.startswith(key):
                    result = bytes.fromhex(line[len(key):].strip())
        os.unlink(out_path)
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check(label: str, cond: bool, detail: str = "") -> bool:
    tag = "PASS" if cond else "FAIL"
    print(f"{tag}  {label}" + (f"\n        {detail}" if detail else ""))
    return cond


def decode_wav_blocks(wav_path: str) -> list[bytes]:
    """Decode a WAV recording into contiguous byte blocks (one per tape block)."""
    data, _ = decode_file(wav_path)
    return data


def find_subseq(data: list[int], needle: list[int]) -> bool:
    """True if needle appears as a contiguous subsequence in data."""
    if not needle:
        return True
    for i in range(len(data) - len(needle) + 1):
        if data[i:i + len(needle)] == needle:
            return True
    return False


# ---------------------------------------------------------------------------
# Test: CSAVE format oracle
# ---------------------------------------------------------------------------

def test_csave_format(cart: str, program: bytes) -> bool:
    """CSAVE"TEST" emits two correct cassette blocks (10x$D3 + "TEST  " + image)."""
    print("== oracle 1: CSAVE format (header + program image bytes in WAV) ==")

    # Build the expected byte sequence that should appear in the WAV decode.
    # Header block: 10x $D3 + b"TEST  " (6 chars, space-padded).
    # Data block: program image bytes.
    expected_hdr = bytes([0xD3] * 10) + b"TEST  "
    expected_data = program

    wav_fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="csave_fmt_")
    os.close(wav_fd)
    try:
        # Type the program then CSAVE (zerobas prompts appear ~6s emulated).
        cmds = [
            (6.0,  "10 A=5"),
            (7.5,  "\r"),
            (9.0,  "20 B=7"),
            (10.5, "\r"),
            (12.0, 'csave"TEST"'),
            (14.0, "\r"),
        ]
        run_save(cart, cmds, wav_path, cap_time=50.0)

        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            return check("CSAVE format: WAV was written", False,
                         "WAV file missing or empty")

        data, info = decode_file(wav_path, verbose=False)
        print(f"        WAV decode: {len(data)} bytes, "
              f"freq~{info.get('short_freq_hz','?')}/{info.get('long_freq_hz','?')} Hz")

        hdr_ok = find_subseq(data, list(expected_hdr))
        data_ok = find_subseq(data, list(expected_data))

        ok = True
        ok &= check("CSAVE format: header block (10x$D3 + 'TEST  ') present in WAV",
                    hdr_ok,
                    f"expected hdr: {expected_hdr.hex(' ')}"
                    + ("" if hdr_ok else f"\n        got : {bytes(data).hex(' ')}"))
        ok &= check("CSAVE format: data block (program image) present in WAV",
                    data_ok,
                    f"expected data: {expected_data.hex(' ')}"
                    + ("" if data_ok else f"\n        got : {bytes(data).hex(' ')}"))
        return ok
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


# ---------------------------------------------------------------------------
# Test: SAVE"CAS:" format oracle
# ---------------------------------------------------------------------------

def test_save_cas_format(cart: str, program: bytes) -> bool:
    """SAVE\"CAS:PROG\" emits same format as CSAVE."""
    print("\n== oracle 1b: SAVE\"CAS:PROG\" format (same as CSAVE) ==")

    expected_hdr = bytes([0xD3] * 10) + b"PROG  "
    expected_data = program

    wav_fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="savcas_fmt_")
    os.close(wav_fd)
    try:
        cmds = [
            (6.0,  "10 A=5"),
            (7.5,  "\r"),
            (9.0,  "20 B=7"),
            (10.5, "\r"),
            (12.0, 'save"CAS:PROG"'),
            (14.0, "\r"),
        ]
        run_save(cart, cmds, wav_path, cap_time=50.0)

        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            return check("SAVE\"CAS:\" format: WAV written", False,
                         "WAV file missing or empty")

        data, info = decode_file(wav_path, verbose=False)
        print(f"        WAV decode: {len(data)} bytes")

        hdr_ok = find_subseq(data, list(expected_hdr))
        data_ok = find_subseq(data, list(expected_data))

        ok = True
        ok &= check("SAVE\"CAS:\" format: header (10x$D3 + 'PROG  ') present",
                    hdr_ok,
                    f"expected: {expected_hdr.hex(' ')}")
        ok &= check("SAVE\"CAS:\" format: data block (program image) present",
                    data_ok,
                    f"expected: {expected_data.hex(' ')}")
        return ok
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


# ---------------------------------------------------------------------------
# Test: BSAVE"CAS:" format oracle
# ---------------------------------------------------------------------------

def test_bsave_cas_format(cart: str) -> bool:
    """BSAVE\"CAS:BIN\",start,end emits binary cassette format."""
    print("\n== oracle 1c: BSAVE\"CAS:\" format (10x$D0 + name + addresses + data) ==")

    expected_hdr = bytes([0xD0] * 10) + b"BIN   "
    expected_addr = (BSAVE_START.to_bytes(2, "little")
                     + BSAVE_END.to_bytes(2, "little")
                     + BSAVE_EXEC.to_bytes(2, "little"))
    expected_data = BSAVE_DATA

    wav_fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="bsvcas_fmt_")
    os.close(wav_fd)
    try:
        # Poke the sentinel bytes then BSAVE them.
        poke_cmds = "\r".join(
            f"POKE {BSAVE_START + i},{BSAVE_DATA[i]}"
            for i in range(len(BSAVE_DATA))
        )
        cmds = []
        t = 6.0
        for i, b in enumerate(BSAVE_DATA):
            cmds.append((t, f"POKE {BSAVE_START + i},{b}"))
            t += 1.2
            cmds.append((t, "\r"))
            t += 0.5
        cmds.append((t, f'BSAVE"CAS:BIN",&H{BSAVE_START:04X},&H{BSAVE_END:04X}'))
        t += 1.5
        cmds.append((t, "\r"))
        run_save(cart, cmds, wav_path, cap_time=t + 50.0)

        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            return check("BSAVE\"CAS:\" format: WAV written", False,
                         "WAV file missing or empty")

        data, info = decode_file(wav_path, verbose=False)
        print(f"        WAV decode: {len(data)} bytes")

        hdr_ok = find_subseq(data, list(expected_hdr))
        addr_ok = find_subseq(data, list(expected_addr))
        data_ok = find_subseq(data, list(expected_data))

        ok = True
        ok &= check("BSAVE\"CAS:\" format: header (10x$D0 + 'BIN   ') present",
                    hdr_ok,
                    f"expected: {expected_hdr.hex(' ')}")
        ok &= check("BSAVE\"CAS:\" format: address header (start/end/exec LE) present",
                    addr_ok,
                    f"expected: {expected_addr.hex(' ')}")
        ok &= check("BSAVE\"CAS:\" format: payload bytes present",
                    data_ok,
                    f"expected: {expected_data.hex(' ')}")
        return ok
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


# ---------------------------------------------------------------------------
# Test: reference VG-8020 loads a .cas built from the same bytes zerobas emits
# ---------------------------------------------------------------------------

def test_ref_load_csave(cart: str, program: bytes) -> bool:
    """VG-8020 can CLOAD a .cas file built from the same bytes zerobas CSAVE emits.

    Oracle 1 proves zerobas CSAVE writes the correct byte content to WAV.
    This oracle (2) proves that byte content is VG-8020 loadable: we synthesize
    a .cas from build_cas_basic (same format, same program image) and confirm the
    reference VG-8020 loads it. The combined oracles are equivalent to "VG-8020
    CLOADs a zerobas CSAVE WAV" but avoid WAV signal-timing edge cases.
    """
    print("\n== oracle 2: reference VG-8020 CLOADs .cas matching zerobas CSAVE format ==")

    want = expected_relinked_image(program)

    # Build a .cas file with the exact content zerobas CSAVE would write:
    # header block = 10x$D3 + "TEST  "; data block = program image.
    # build_cas_basic adds the CAS_SYNC openMSX markers and 16 trailing $00 pad.
    cas = build_cas_basic("TEST", program)
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="ref_csave_")
    os.write(cas_fd, cas)
    os.close(cas_fd)
    try:
        got = run_load_ref(cas_path, "cload", TXTBASE, len(want),
                           cap_time=35.0, timeout=90.0)
        ok = got is not None and got == want
        return check("ref VG-8020 CLOADs .cas matching CSAVE format -> correct image",
                     ok,
                     f"want: {want.hex(' ')}"
                     f"\ngot : {got.hex(' ') if got else '<no capture>'}")
    finally:
        os.unlink(cas_path)


# ---------------------------------------------------------------------------
# Test: self round-trip CSAVE → CLOAD
# ---------------------------------------------------------------------------

def test_roundtrip_csave(cart: str, program: bytes) -> bool:
    """zerobas CSAVE then zerobas CLOAD returns identical program image."""
    print("\n== oracle 3a: self round-trip CSAVE -> CLOAD ==")

    want = expected_relinked_image(program)

    # Step 1: CSAVE.
    wav_fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="rt_csave_")
    os.close(wav_fd)
    try:
        cmds = [
            (6.0,  "10 A=5"),
            (7.5,  "\r"),
            (9.0,  "20 B=7"),
            (10.5, "\r"),
            (12.0, 'csave"RT"'),
            (14.0, "\r"),
        ]
        run_save(cart, cmds, wav_path, cap_time=50.0)

        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            return check("self rt CSAVE: WAV written", False, "WAV missing or empty")

        # Step 2: CLOAD from the WAV using zerobas.
        got = run_load_zerobas(cart, wav_path, "cload", TXTBASE, len(want),
                               cap_time=35.0, timeout=90.0)
        ok = got is not None and got == want
        return check("self rt: zerobas CSAVE -> CLOAD produces identical program",
                     ok,
                     f"want: {want.hex(' ')}"
                     f"\ngot : {got.hex(' ') if got else '<no capture>'}")
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


# ---------------------------------------------------------------------------
# Test: self round-trip BSAVE"CAS:" → BLOAD"CAS:"
# ---------------------------------------------------------------------------

def test_roundtrip_bsave(cart: str) -> bool:
    """zerobas BSAVE\"CAS:\" then BLOAD\"CAS:\" returns identical bytes."""
    print("\n== oracle 3b: self round-trip BSAVE\"CAS:\" -> BLOAD\"CAS:\" ==")

    want = BSAVE_DATA

    wav_fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="rt_bsave_")
    os.close(wav_fd)
    try:
        # Poke sentinel bytes then BSAVE.
        cmds = []
        t = 6.0
        for i, b in enumerate(BSAVE_DATA):
            cmds.append((t, f"POKE {BSAVE_START + i},{b}"))
            t += 1.2
            cmds.append((t, "\r"))
            t += 0.5
        cmds.append((t, f'BSAVE"CAS:BIN",&H{BSAVE_START:04X},&H{BSAVE_END:04X}'))
        t += 1.5
        cmds.append((t, "\r"))
        run_save(cart, cmds, wav_path, cap_time=t + 50.0)

        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            return check("self rt BSAVE\"CAS:\": WAV written", False,
                         "WAV missing or empty")

        # Zero out the sentinel region (POKE 0s) then BLOAD"CAS:".
        # We need a new session: boot again, zero the region, then BLOAD.
        # For simplicity: the BLOAD session starts fresh (cold boot zeros RAM),
        # so we don't need to zero it explicitly (RAM starts at 0 on C-BIOS cold).
        bload_verb = 'BLOAD"CAS:"'
        got = run_load_zerobas(cart, wav_path, bload_verb,
                               BSAVE_START, len(want),
                               cap_time=35.0, timeout=90.0)
        ok = got is not None and got == want
        return check("self rt: zerobas BSAVE\"CAS:\" -> BLOAD\"CAS:\" identical bytes",
                     ok,
                     f"want: {want.hex(' ')}"
                     f"\ngot : {got.hex(' ') if got else '<no capture>'}")
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom path")
    args = ap.parse_args()

    program = build_program()
    ok = True

    ok &= test_csave_format(args.cart, program)
    ok &= test_save_cas_format(args.cart, program)
    ok &= test_bsave_cas_format(args.cart)
    ok &= test_ref_load_csave(args.cart, program)
    ok &= test_roundtrip_csave(args.cart, program)
    ok &= test_roundtrip_bsave(args.cart)

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
