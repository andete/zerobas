#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""CLOAD? cassette-verify probe (tape Tier-3, Item B).

Spec: tape/docs/spec-cas-tier3-cload.md Item B. CLOAD? reads a tokenised tape
program and COMPARES it against the in-memory program WITHOUT mutating memory:
identical -> Ok, any byte difference -> "Verify error". Our tokeniser maps '?'
to PRINT, so `CLOAD?` = CLOAD_TOKEN + PRINT_TOKEN, which do_cload detects
(basic/cload.asm); the tokenised reader then runs in compare-mode via cas_put
(no store), CAS_VMIS holds the verdict. Scope: tokenised ($D3) only; an $EA
ASCII file under CLOAD? -> load error.

Cases (typed harness; the outcome is the ON-SCREEN message, read from VRAM):
  B1 verify OK    : type `10 POKE..99`, CLOAD? a byte-identical tokenised tape
                    -> NO "Verify error" (program matches).
  B2 verify diff  : type `10 POKE..98`, CLOAD? the ..99 tape -> "Verify error".
  B3 non-destruct : after B2, the in-memory program still RUNs (POKEs its own
                    witness) -> verify left memory untouched.
  B4 ASCII reject : CLOAD? an $EA ASCII tape -> "load error" (tokenised-only).

C-BIOS_MSX1_EU_TAPE --cart build/basic.rom (the established cassette-probe
method). Clean-room: our own programs + cas codec; the reference ROM is never
read. IPS note: --cart reads build/basic.rom directly, so `make build/basic.rom`
suffices (no IPS reinstall).
"""
from __future__ import annotations

import os as _os
import sys as _sys
_PROBES = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(_PROBES, "lib"))
_sys.path.insert(0, _os.path.join(_PROBES, "disk"))

import argparse
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time

from cas_encode import build_cas_basic
from bas_tokenise import make_multiline_program
from basic_probe_cas_ascii import build_ascii_cas
from omsx_run import _tcl_dquote

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MACHINE = "C-BIOS_MSX1_EU_TAPE"
DEFAULT_CART = os.path.join(os.path.dirname(_PROBES), "build", "basic.rom")
TXTBASE = 0x8001
WITNESS = 0xD0FF
RAN = 0x99


def prog(val: int) -> bytes:
    return make_multiline_program([(10, f"POKE&H{WITNESS:04X},&H{val:02X}")], TXTBASE)


def run_typed_scr(cart, cas, type_cmds, cap_time=40.0, timeout=110.0):
    """Type timed commands, capture the text screen (VRAM) + the witness byte."""
    subprocess.run(["pkill", "-9", "openmsx"], capture_output=True)
    time.sleep(1.0)
    out = tempfile.mktemp(suffix=".txt", prefix="casver_")
    lines = ["set throttle off", "set renderer none",
             f"after time 1 {{ debug write memory 0x{WITNESS:04X} 0x11 }}"]
    for delay, text in type_cmds:
        lines.append(f"after time {delay} {{ type {_tcl_dquote(text)} }}")
    lines += [
        "proc cap {} {",
        f"  set f [open {{{out}}} w]",
        "  binary scan [debug read_block {VRAM} 0x0000 960] H* h0; puts $f \"s0=$h0\"",
        "  binary scan [debug read_block {VRAM} 0x1800 768] H* h1; puts $f \"s1=$h1\"",
        f"  puts $f \"wit=[format %02X [debug read memory 0x{WITNESS:04X}]]\"",
        "  close $f; exit }",
        f"after time {cap_time} {{ cap }}",
    ]
    tcl = out + ".tcl"
    open(tcl, "w").write("\n".join(lines) + "\n")
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", MACHINE, "-cart", cart, "-cassetteplayer", cas, "-script", tcl]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    dl = time.time() + timeout
    while p.poll() is None and time.time() < dl:
        time.sleep(0.1)
    if p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    scr, wit = "", None
    if os.path.exists(out):
        for ln in open(out):
            k, _, v = ln.strip().partition("=")
            if k in ("s0", "s1"):
                scr += "".join(chr(c) if 32 <= c < 127 else " " for c in bytes.fromhex(v))
            elif k == "wit":
                wit = int(v, 16)
    return re.sub(r"\s+", " ", scr), wit


def check(label, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"\n        {detail}" if detail else ""))
    return cond


def type_prog(val):
    # type `10 POKE&HD0FF,&Hxx` then Enter, at emulator keyboard speed
    return [(6.0, f"10 POKE&H{WITNESS:04X},&H{val:02X}"), (9.0, "\r")]


def test_verify_ok(cart, tmp):
    print("B1  CLOAD? of a byte-identical tape -> Ok (no Verify error):")
    cas = os.path.join(tmp, "v_ok.cas")
    open(cas, "wb").write(build_cas_basic("V", prog(RAN)))
    scr, _ = run_typed_scr(cart, cas, type_prog(RAN) + [(12.0, "CLOAD?"), (14.0, "\r")])
    return check("no 'Verify error' on the screen",
                 "verify error" not in scr.lower(), f"screen: ...{scr[-90:].strip()}")


def test_verify_diff(cart, tmp):
    print("B2  CLOAD? of a 1-byte-different tape -> Verify error:")
    cas = os.path.join(tmp, "v_diff.cas")
    open(cas, "wb").write(build_cas_basic("V", prog(RAN)))          # tape POKEs 0x99
    scr, _ = run_typed_scr(cart, cas, type_prog(0x98) +            # memory POKEs 0x98
                           [(12.0, "CLOAD?"), (14.0, "\r")])
    return check("'Verify error' shown", "verify error" in scr.lower(),
                 f"screen: ...{scr[-90:].strip()}")


def test_non_destructive(cart, tmp):
    print("B3  after a CLOAD? mismatch, the in-memory program still RUNs (untouched):")
    cas = os.path.join(tmp, "v_nd.cas")
    open(cas, "wb").write(build_cas_basic("V", prog(RAN)))          # tape POKEs 0x99
    # memory program POKEs 0x99 too (its own witness); mismatch is forced by name?
    # No -- to prove non-destruction we need memory != tape yet memory still runs.
    # Use memory POKEs 0x99 but tape POKEs 0x98 so CLOAD? errors, then RUN must
    # still set 0x99 from the untouched in-memory program.
    open(cas, "wb").write(build_cas_basic("V", prog(0x98)))
    _, wit = run_typed_scr(cart, cas, type_prog(RAN) +
                           [(12.0, "CLOAD?"), (14.0, "\r"),
                            (24.0, "RUN"), (25.0, "\r")], cap_time=32.0)
    return check(f"witness=${wit if wit else 0:02X} (expect ${RAN:02X} -- program intact)",
                 wit == RAN)


def test_ascii_reject(cart, tmp):
    print("B4  CLOAD? of an $EA ASCII tape -> load error (tokenised-only):")
    cas = os.path.join(tmp, "v_asc.cas")
    open(cas, "wb").write(build_ascii_cas("V", [f"10 POKE&H{WITNESS:04X},&H{RAN:02X}"]))
    scr, _ = run_typed_scr(cart, cas, type_prog(RAN) + [(12.0, "CLOAD?"), (14.0, "\r")])
    return check("'load error' shown (ASCII not verifiable)", "load error" in scr.lower(),
                 f"screen: ...{scr[-90:].strip()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", default=DEFAULT_CART)
    args = ap.parse_args()
    if not os.path.exists(args.cart):
        print(f"cart not found: {args.cart} (run: make build/basic.rom)")
        return 2
    tmp = tempfile.mkdtemp(prefix="cas_verify_")
    ok = True
    for t in (test_verify_ok, test_verify_diff, test_non_destructive, test_ascii_reject):
        ok = t(args.cart, tmp) and ok
    print("\n" + ("ALL PASS -- CLOAD? verifies a tokenised tape non-destructively, "
                  "flags a mismatch, and rejects ASCII" if ok else
                  "FAIL -- see per-case results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
