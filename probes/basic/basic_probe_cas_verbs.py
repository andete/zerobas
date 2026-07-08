#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Cassette verb probe: RUN"CAS:", MERGE"CAS:", OPEN"CAS:" (tape Tier-2 follow-ons).

Companion to basic_probe_cas_ascii.py (LOAD) and the M2 cells of
basic_probe_tape_save.py (SAVE). These verbs reuse the M1/M2 cassette-ASCII byte
machinery — do_tape_prog's 3-way header dispatch, cas_ascii_setup/cas_ascii_drive,
cal_getbyte/cal_refill, cas_wbyte/cas_flush_block — so the tests prove the *wiring*.

  RUN"CAS:"  — load a cassette program (tokenised $D3 OR ASCII $EA) then run it.
    Witnessed like the LOAD"CAS:",R option test (basic_probe_cas_options.py): the
    program POKEs a sentinel to $D0FF (poisoned to $11 at boot); after RUN"CAS:"
    the witness must be $99. Run for BOTH a tokenised and an ASCII cassette.

  MERGE"CAS:" — merge an ASCII cassette program into the CURRENT program (keep
    existing lines, insert/replace by number). A base program (lines 10 + 30) is
    typed, an ASCII cassette carrying line 20 is MERGEd, and the resulting program
    image at TXTBASE is asserted byte-identical to tokenising {10,20,30} together.

  OPEN"CAS:" — cassette sequential data channels. FOR OUTPUT: OPEN + PRINT# +
    CLOSE writes an $EA data file (header + line data + Ctrl-Z), asserted by
    decoding the recorded WAV. Round-trip: a written line is read back with OPEN
    FOR INPUT + LINE INPUT# (captured byte-identically from the STRSCR read scratch,
    since zerobas's subset has no BASIC-level string-length assert). A 2nd read past
    the data hits the Ctrl-Z EOF -> empty string.

Typed harness on C-BIOS_MSX1_EU_TAPE --cart build/basic.rom (the established
cassette-probe method; --cart reads build/basic.rom directly). Clean-room: our own
programs, our own cas codec / tokeniser; the reference ROM is never read.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))         # sibling probes
_PROBES = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))    # probes/
_ROOT = _os.path.dirname(_PROBES)                                          # repo root
_sys.path.insert(0, _os.path.join(_PROBES, "lib"))                        # cas codec
_sys.path.insert(0, _os.path.join(_PROBES, "disk"))                       # bas_tokenise

import argparse
import os
import shutil
import signal
import subprocess
import tempfile
import time

from cas_encode import build_cas_basic              # noqa: E402
from cas_decode import decode_file                   # noqa: E402
from bas_tokenise import make_multiline_program      # noqa: E402
from basic_probe_cas_ascii import build_ascii_cas    # noqa: E402
from basic_probe_tape_save import run_save, find_subseq  # noqa: E402
from omsx_run import _tcl_dquote                      # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MACHINE_TAPE = "C-BIOS_MSX1_EU_TAPE"
TXTBASE = 0x8001
WITNESS = 0xD0FF
POISON = 0x11
RAN = 0x99


def run_typed(cart: str, cas_path: str, type_cmds: list[tuple[float, str]],
              cap_addr: int, cap_len: int,
              cap_time: float, timeout: float = 120.0,
              poison_witness: bool = False,
              inject: tuple[int, bytes] | None = None):
    """Mount cas_path, type the timed commands, capture cap_len bytes at cap_addr.

    inject=(addr, bytes) writes a tokenised program image into RAM before typing
    (so a long OPEN/LINE INPUT#/POKE program is set up without typing a 90-char line
    at emulator keyboard speed; the test then just types RUN). Returns
    (hex_at_cap_addr, witness_byte_or_None).
    """
    out = tempfile.mktemp(suffix=".txt", prefix="casverb_")
    lines = [
        "set throttle off",
        "set renderer none",
        "proc __hex {a n} { binary scan [debug read_block {memory} $a $n] H* h; return $h }",
    ]
    if poison_witness:
        lines.append(f"after time 1 {{ debug write memory 0x{WITNESS:04X} 0x{POISON:02X} }}")
    if inject is not None:
        addr, img = inject
        lines.append(f"after time 4 {{ debug write_block memory 0x{addr:04X} "
                     f"[binary decode hex {img.hex()}] }}")
    for delay, text in type_cmds:
        lines.append(f"after time {delay} {{ type {_tcl_dquote(text)} }}")
    lines += [
        "proc __cap {} {",
        f"  set f [open {{{out}}} w]",
        f'  puts $f "mem=[__hex 0x{cap_addr:04X} {cap_len}]"',
        f'  puts $f "wit=[format %02X [debug read memory 0x{WITNESS:04X}]]"',
        "  close $f",
        "  exit",
        "}",
        f"after time {cap_time} {{ __cap }}",
    ]
    tcl = "\n".join(lines) + "\n"
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", MACHINE_TAPE, "-cart", cart,
           "-cassetteplayer", cas_path, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    mem, wit = None, None
    if os.path.exists(out):
        for ln in open(out):
            k, _, v = ln.strip().partition("=")
            if k == "mem":
                mem = v
            elif k == "wit":
                wit = int(v, 16)
    return mem, wit


def check(label: str, cond: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"\n        {detail}" if detail else ""))
    return cond


def test_run_cas(cart: str, tmp: str) -> bool:
    """RUN"CAS:" of a tokenised cassette program runs it (witness $D0FF -> $99)."""
    print('RUN"CAS:" (tokenised program):')
    prog = make_multiline_program([(10, f"POKE&H{WITNESS:04X},&H{RAN:02X}")], TXTBASE)
    cas = os.path.join(tmp, "run_tok.cas")
    open(cas, "wb").write(build_cas_basic("RUNT", prog))
    _, wit = run_typed(cart, cas, [(6.0, 'RUN"CAS:"'), (8.0, "\r")],
                       TXTBASE, 6, cap_time=34.0, poison_witness=True)
    return check(f'RUN"CAS:" ran tokenised program: (${WITNESS:04X})='
                 f'${wit if wit is not None else 0:02X} (expect ${RAN:02X})', wit == RAN)


def test_run_cas_ascii(cart: str, tmp: str) -> bool:
    """RUN"CAS:" of an ASCII ($EA) cassette program runs it too (3-way dispatch)."""
    print('RUN"CAS:" (ASCII program):')
    cas = os.path.join(tmp, "run_asc.cas")
    open(cas, "wb").write(build_ascii_cas("RUNA", [f"10 POKE&H{WITNESS:04X},&H{RAN:02X}"]))
    _, wit = run_typed(cart, cas, [(6.0, 'RUN"CAS:"'), (8.0, "\r")],
                       TXTBASE, 6, cap_time=34.0, poison_witness=True)
    return check(f'RUN"CAS:" ran ASCII program: (${WITNESS:04X})='
                 f'${wit if wit is not None else 0:02X} (expect ${RAN:02X})', wit == RAN)


def test_merge_cas(cart: str, tmp: str) -> bool:
    """MERGE"CAS:" inserts an ASCII cassette line into the current program."""
    print('MERGE"CAS:" (insert line 20 into a typed 10+30 program):')
    cas = os.path.join(tmp, "merge.cas")
    open(cas, "wb").write(build_ascii_cas("MRG", ["20 B=2"]))
    expect = make_multiline_program([(10, "A=1"), (20, "B=2"), (30, "C=3")], TXTBASE)
    cmds = [
        (6.0,  "10 A=1"), (7.5, "\r"),
        (9.0,  "30 C=3"), (10.5, "\r"),
        (12.0, 'MERGE"CAS:"'), (14.0, "\r"),
    ]
    mem, _ = run_typed(cart, cas, cmds, TXTBASE, len(expect) + 4,
                       cap_time=40.0, timeout=110.0)
    ok = mem is not None and mem.startswith(expect.hex())
    return check("MERGE\"CAS:\" merged {10,20,30} byte-identically", ok,
                 f"expect: {expect.hex()}\n        got:    {mem}")


def test_open_cas_output(cart: str, tmp: str) -> bool:
    """OPEN"CAS:D"FOR OUTPUT + PRINT# writes an $EA data file (header + lines + EOF)."""
    print('OPEN"CAS:" FOR OUTPUT (PRINT# -> $EA cassette data file):')
    wav = os.path.join(tmp, "open_out.wav")
    # Direct-mode: open, two PRINT#s, close. run_save records the tape signal.
    cmds = [
        (6.0,  'OPEN"CAS:D"FOR OUTPUT AS#1'), (8.0, "\r"),
        (10.0, 'PRINT#1,"HELLO"'),            (11.5, "\r"),
        (13.0, 'PRINT#1,"WORLD"'),            (14.5, "\r"),
        (16.0, 'CLOSE'),                      (17.5, "\r"),
    ]
    run_save(cart, cmds, wav, cap_time=60.0)
    data, _ = decode_file(wav, verbose=False)
    print(f"        WAV decode: {len(data)} bytes")
    hdr = bytes([0xEA] * 10) + b"D     "
    body = b"HELLO\r\nWORLD\r\n"
    ok = True
    ok &= check("OPEN OUTPUT: $EA header + 'D     ' name present",
                find_subseq(data, list(hdr)), f"hdr {hdr.hex(' ')}")
    ok &= check("OPEN OUTPUT: PRINT# data 'HELLO\\r\\nWORLD\\r\\n' present",
                find_subseq(data, list(body)),
                "" if find_subseq(data, list(body)) else f"got {bytes(data).hex(' ')}")
    ok &= check("OPEN OUTPUT: Ctrl-Z ($1A) EOF present", 0x1A in data)
    return ok


def _write_cas_data(cart: str, wav: str, name: str, lines: list[str]) -> None:
    """Session 1: direct-mode OPEN"CAS:name"FOR OUTPUT + a PRINT# per line + CLOSE,
    recording the tape to `wav`."""
    cmds = [(6.0, f'OPEN"CAS:{name}"FOR OUTPUT AS#1'), (8.0, "\r")]
    t = 10.0
    for ln in lines:
        cmds += [(t, f'PRINT#1,"{ln}"'), (t + 1.5, "\r")]
        t += 3.0
    cmds += [(t, 'CLOSE'), (t + 1.5, "\r")]
    run_save(cart, cmds, wav, cap_time=t + 45.0)


# STRSCR = the string-input scratch descriptor ([len:1][bytes]) that read_into_strscr
# fills as it reads a field/line. We verify the CAS INPUT read by capturing STRSCR
# right after a RUN whose last statement is a LINE INPUT#, because zerobas's BASIC
# subset has no working string-length/inspection path to assert on from BASIC
# (LEN/ASC etc. don't round-trip a value out — confirmed), whereas STRSCR holds the
# exact bytes read and is stable in the post-RUN idle REPL. This is the same scratch
# the shared (disk + CAS) reader fills, so it evidences the read faithfully.
STRSCR = 0xE360


def test_open_cas_roundtrip(cart: str, tmp: str) -> bool:
    """Round-trip: OPEN OUTPUT/PRINT# writes "HELLOWORLD"; a RUN then OPENs it FOR
    INPUT and LINE INPUT#s it — the bytes land in STRSCR as [len=10]"HELLOWORLD"."""
    print('OPEN"CAS:" round-trip (OUTPUT/PRINT# "HELLOWORLD" -> INPUT/LINE INPUT#):')
    wav = os.path.join(tmp, "open_rt.wav")
    _write_cas_data(cart, wav, "R", ["HELLOWORLD"])
    # Stored program (short typed lines so the ROM maintains VARTAB); RUN then read.
    r_cmds = [
        (6.0,  '10 OPEN"CAS:"FOR INPUT AS#1'), (8.0,  "\r"),
        (10.0, '20 LINE INPUT#1,A$'),          (11.5, "\r"),
        (13.0, 'RUN'),                         (14.5, "\r"),
    ]
    mem, _ = run_typed(cart, wav, r_cmds, STRSCR, 11, cap_time=34.0, timeout=110.0)
    want = (bytes([10]) + b"HELLOWORLD").hex()
    ok = mem == want
    return check('LINE INPUT#1 read back "HELLOWORLD" (len 10) byte-identically',
                 ok, f"expect {want}, got {mem}")


def test_open_cas_eof(cart: str, tmp: str) -> bool:
    """A 2nd LINE INPUT# past the single data line hits the Ctrl-Z EOF and yields an
    empty string — STRSCR length 0 — proving cas_in_getbyte terminates the read."""
    print('OPEN"CAS:" Ctrl-Z EOF (2nd LINE INPUT# past the data -> empty):')
    wav = os.path.join(tmp, "open_eof.wav")
    _write_cas_data(cart, wav, "E", ["ONE"])
    r_cmds = [
        (6.0,  '10 OPEN"CAS:"FOR INPUT AS#1'), (8.0,  "\r"),
        (10.0, '20 LINE INPUT#1,A$'),          (11.5, "\r"),  # reads "ONE"
        (14.0, '30 LINE INPUT#1,B$'),          (15.5, "\r"),  # hits Ctrl-Z EOF -> ""
        (18.0, 'RUN'),                         (19.5, "\r"),
    ]
    mem, _ = run_typed(cart, wav, r_cmds, STRSCR, 1, cap_time=42.0, timeout=120.0)
    ok = mem == "00"
    return check("2nd LINE INPUT# at Ctrl-Z EOF yields an empty string (STRSCR len 0)",
                 ok, f"expect 00, got {mem}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", default=os.path.join(_ROOT, "build", "basic.rom"))
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="casverb_")
    ok = True
    ok &= test_run_cas(args.cart, tmp)
    ok &= test_run_cas_ascii(args.cart, tmp)
    ok &= test_merge_cas(args.cart, tmp)
    ok &= test_open_cas_output(args.cart, tmp)
    ok &= test_open_cas_roundtrip(args.cart, tmp)
    ok &= test_open_cas_eof(args.cart, tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    print("CAS-verbs:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
