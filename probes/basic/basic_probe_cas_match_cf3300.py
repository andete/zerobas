#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Oracle characterization: stock National_CF-3300 CLOAD"name" is CASE-SENSITIVE.

This is the black-box provenance behind spec-cas-tier3-cload.md §A.5 — the
evidence that our Tier-3 name-matching (case-sensitive, byte-exact; implemented
in basic/cload.asm cas_open_match, gated by basic_probe_cas_match.py) matches the
documented reference machine's behaviour. Strictly OBSERVED behaviour: a disk is
built per the public FAT12 spec, the stock CF-3300 is cold-booted, and RAM is
read. The CF-3300 ROM is NEVER read or disassembled (no-reference-rom-disasm).

Method (ZERO typed keys — the CF-3300 disk-BASIC date prompt hijacks typed input,
but an AUTOEXEC.BAS auto-runs regardless): an auto-running ASCII AUTOEXEC.BAS =
`10 CLOAD"<key>"` on a data disk, plus a cassette whose one file is
`10 POKE&HD005,&HA5`. CLOAD loads (does NOT run) the tape program, REPLACING the
AUTOEXEC program in memory, so the first token byte at TXTBASE+4 tells us whether
the tape loaded: 0x98 (POKE) = the tape program is resident (name MATCHED);
0x9B (CLOAD) = the AUTOEXEC line is still resident (did NOT match).

Controls make the case answer conclusive:
  exact  key==filecase -> MATCHED  (chain works + name-matching is active)
  absent key not on tape -> no-match (matching is REAL, not "load next")
  variant key!=filecase -> the answer

Result (reproduced): exact loads; both case variants do NOT -> CASE-SENSITIVE.
Bonus observed: an absent name loads nothing (the CF-3300 does real name-matching,
so Tier-3 aligns us TOWARD the oracle); and LOAD"CAS:" is a no-op on MSX1 stock
(CLOAD is the working stock cassette-load verb).

Prerequisites: `make machines-oracle` (installs National_CF-3300 with YOUR own
CF-3300 reference BIOS in ~/.openMSX/share/systemroms). Oracle-dependent + HEAVY;
NOT part of the emulator-free unit-test. Fixtures are named by unique index, NOT
by the case-varying tape name — macOS's case-insensitive FS silently merges
abc/ABC paths otherwise (a real gotcha during characterization).

    python3 probes/basic/basic_probe_cas_match_cf3300.py
"""
from __future__ import annotations

import os as _os
import sys as _sys
_PROBES = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_ROOT = _os.path.dirname(_PROBES)
_sys.path[:0] = [_os.path.join(_PROBES, "lib"), _os.path.join(_PROBES, "disk"),
                 _os.path.join(_ROOT, "tools")]

import argparse
import shutil
import signal
import subprocess
import tempfile
import time

from cas_encode import build_cas_basic                  # noqa: E402
from bas_tokenise import make_multiline_program         # noqa: E402
from make_test_dsk import Fat12Image                    # noqa: E402
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = _os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MACHINE = "National_CF-3300"     # stock oracle, its own BIOS (no --cart)
TXTBASE = 0x8001
PROG = make_multiline_program([(10, "POKE&HD005,&HA5")], TXTBASE)
POKE_TOK, CLOAD_TOK = 0x98, 0x9B

_n = [0]                          # collision-safe fixture counter (see docstring)


def _tape(name, tmp):
    _n[0] += 1
    p = _os.path.join(tmp, f"tape{_n[0]}.cas")
    open(p, "wb").write(build_cas_basic(name, PROG))
    return p


def _disk(key, tmp):
    _n[0] += 1
    d = Fat12Image()
    d.add_file("AUTOEXEC", "BAS", f'10 CLOAD"{key}"\r\n'.encode())
    p = _os.path.join(tmp, f"disk{_n[0]}.dsk")
    open(p, "wb").write(d.finish())
    return p


def _run(dk, tp, cap=34.0, timeout=90.0):
    subprocess.run(["pkill", "-9", "openmsx"], capture_output=True)
    time.sleep(1.0)
    out = tempfile.mktemp(suffix=".txt", prefix="cf3300_match_")
    tcl = (f"set throttle off\nset renderer none\nset sound_driver null\n"
           f"proc cap {{}} {{ set f [open {{{out}}} w]; "
           f"binary scan [debug read_block {{memory}} 0x{TXTBASE:04X} 8] H* p; "
           f'puts $f "prog=$p"; close $f; exit }}\n'
           f"after time {cap} {{ cap }}\n")
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if _os.path.exists(out):
        _os.unlink(out)
    cmd = [OMSX, "-machine", MACHINE, "-diska", dk, "-cassetteplayer", tp,
           "-script", tcl_path]
    p = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    dl = time.time() + timeout
    while p.poll() is None and time.time() < dl:
        time.sleep(0.1)
    if p.poll() is None:
        _os.killpg(_os.getpgid(p.pid), signal.SIGKILL)
    prog = ""
    if _os.path.exists(out):
        for ln in open(out):
            k, _, v = ln.strip().partition("=")
            if k == "prog":
                prog = v
    return prog


def _loaded(prog):
    if len(prog) < 10:
        return None
    return int(prog[8:10], 16) == POKE_TOK


def main() -> int:
    argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    tmp = tempfile.mkdtemp(prefix="cas_match_cf3300_")
    cases = [
        ('tape=abc  CLOAD"abc"  (exact control)',  _disk("abc", tmp), _tape("abc", tmp)),
        ('tape=abc  CLOAD"xyz"  (absent control)', _disk("xyz", tmp), _tape("abc", tmp)),
        ('tape=abc  CLOAD"ABC"  (UC key/LC file)', _disk("ABC", tmp), _tape("abc", tmp)),
        ('tape=ABC  CLOAD"abc"  (LC key/UC file)', _disk("abc", tmp), _tape("ABC", tmp)),
    ]
    print("Stock National_CF-3300  CLOAD name-match (AUTOEXEC, 0 typed keys)\n")
    res = []
    for label, dk, tp in cases:
        prog = _run(dk, tp)
        ld = _loaded(prog)
        print(f"  {label:42s} -> prog={prog}  "
              f"{'MATCHED' if ld else 'no-match' if ld is False else '??'}")
        res.append(ld)
    exact, absent, uc, lc = res
    print()
    if not exact:
        print("INCONCLUSIVE: exact control did not load (oracle/chain issue).")
        return 2
    if absent:
        print("UNEXPECTED: absent control loaded (matching not behaving as expected).")
        return 1
    if (uc is False) and (lc is False):
        print("RESULT: CLOAD name-matching is CASE-SENSITIVE on the CF-3300 "
              "(matches our Tier-3 implementation).")
        return 0
    if uc and lc:
        print("RESULT: CASE-INSENSITIVE (contradicts the spec §A.5 decision!).")
        return 1
    print(f"RESULT: ASYMMETRIC — UCkey={uc} LCkey={lc}.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
