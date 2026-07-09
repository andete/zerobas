#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Cassette name-matching probe (tape Tier-3, Item A): CLOAD"name" /
LOAD"CAS:name" / RUN"CAS:name" / MERGE"CAS:name" find the NAMED file on a
multi-file tape, skipping earlier non-matching files.

Spec: tape/docs/spec-cas-tier3-cload.md Item A. Before Tier-3 the tape verbs
accepted-and-discarded the name and loaded the NEXT file; now cas_open_match reads
each file's 6-char header name and compares it BYTE-EXACT (case-sensitive — the
behaviour of the stock National_CF-3300, characterized black-box in spec §A.5),
consuming a non-matching file's data (cas_skip_data: tokenised $D3 link-chain, or
$EA 256-byte blocks to the Ctrl-Z) and trying the next header.

Fixtures are MULTI-file tapes = concatenated build_cas_basic / build_ascii_cas
images. A matched program POKEs a distinct witness byte, so the witness proves
WHICH file loaded (i.e. that the right one was found and earlier ones skipped).
RUN"CAS:name" both finds AND runs, so it witnesses matching in one step.

Typed harness on C-BIOS_MSX1_EU_TAPE --cart build/basic.rom (the established
cassette-probe method — --cart reads build/basic.rom directly, so a plain
`make build/basic.rom` suffices, no IPS reinstall). Clean-room: our own programs,
our own cas codec / tokeniser; the reference ROM is never read. NB fixture .cas
files are named by test id (not by the tape-internal name) so macOS's case-
insensitive FS can't merge an "abc"/"ABC" pair (see the tape memory note).
"""
from __future__ import annotations

import os as _os
import sys as _sys
_PROBES = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))         # sibling probes
_sys.path.insert(0, _os.path.join(_PROBES, "lib"))                        # cas codec
_sys.path.insert(0, _os.path.join(_PROBES, "disk"))                       # bas_tokenise

import argparse
import os
import shutil
import tempfile

from cas_encode import build_cas_basic, CAS_SYNC, BASIC_ID  # noqa: E402
from bas_tokenise import make_multiline_program         # noqa: E402
from basic_probe_cas_ascii import build_ascii_cas       # noqa: E402
from basic_probe_cas_verbs import (                     # noqa: E402
    run_typed, check, MACHINE_TAPE, TXTBASE, WITNESS, POISON)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
DEFAULT_CART = os.path.join(os.path.dirname(_PROBES), "build", "basic.rom")

WA = 0xA1   # witness for file "AAA" / first file
WB = 0xB2   # witness for file "BBB" / second file


def tok(witness: int) -> bytes:
    """Tokenised program image that POKEs `witness` into WITNESS."""
    return make_multiline_program([(10, f"POKE&H{WITNESS:04X},&H{witness:02X}")], TXTBASE)


def asc(witness: int) -> list[str]:
    return [f"10 POKE&H{WITNESS:04X},&H{witness:02X}"]


def tok_file_nopad(name: str, program: bytes) -> bytes:
    """A tokenised .cas file whose data block ends EXACTLY at the program's $0000
    end-link, with NO trailing in-block padding — matching what our own CSAVE
    writes (save.asm: payload then TAPOOF). cas_encode.build_cas_basic appends 16
    $00 pad bytes for single-file framing; on a multi-file tape those unread pad
    bytes would leave a SKIPPED tokenised file mid-block so the next TAPION cannot
    relock. Real CSAVE tapes have no such pad, so this is the faithful skip fixture
    (see spec §A + cload.asm cas_skip_data: tokenised skip assumes end-at-$0000)."""
    return CAS_SYNC + bytes([BASIC_ID] * 10) + name[:6].ljust(6).encode("ascii") \
        + CAS_SYNC + program


def two_tok_tape(tmp: str, tag: str) -> str:
    """AAA (POKE WA) then BBB (POKE WB), both tokenised, CSAVE-faithful (no pad)."""
    p = os.path.join(tmp, f"{tag}.cas")
    open(p, "wb").write(tok_file_nopad("AAA", tok(WA)) + tok_file_nopad("BBB", tok(WB)))
    return p


def two_asc_tape(tmp: str, tag: str) -> str:
    p = os.path.join(tmp, f"{tag}.cas")
    open(p, "wb").write(build_ascii_cas("AAA", asc(WA)) + build_ascii_cas("BBB", asc(WB)))
    return p


def run_cmd(cart, cas, cmd, cap_time=40.0):
    """Type `cmd` + Enter, return the witness byte (poisoned to POISON first)."""
    _, wit = run_typed(cart, cas, [(6.0, cmd), (8.0, "\r")],
                       TXTBASE, 6, cap_time=cap_time, poison_witness=True)
    return wit


def test_skip_match_tok(cart, tmp):
    print('RUN"CAS:BBB" on [AAA,BBB] tokenised -> skips AAA, runs BBB:')
    cas = two_tok_tape(tmp, "a1")
    wit = run_cmd(cart, cas, 'RUN"CAS:BBB"')
    return check(f'  witness=${wit if wit else 0:02X} (expect ${WB:02X}, not ${WA:02X})',
                 wit == WB)


def test_skip_match_asc(cart, tmp):
    print('RUN"CAS:BBB" on [AAA,BBB] ASCII -> skips AAA (multi-block), runs BBB:')
    cas = two_asc_tape(tmp, "a2")
    wit = run_cmd(cart, cas, 'RUN"CAS:BBB"')
    return check(f'  witness=${wit if wit else 0:02X} (expect ${WB:02X})', wit == WB)


def test_mixed_skip(cart, tmp):
    print('RUN"CAS:BBB" on [AAA ASCII, BBB tokenised] -> id-dispatched skip:')
    cas = os.path.join(tmp, "a3.cas")
    open(cas, "wb").write(build_ascii_cas("AAA", asc(WA)) + build_cas_basic("BBB", tok(WB)))
    wit = run_cmd(cart, cas, 'RUN"CAS:BBB"')
    return check(f'  witness=${wit if wit else 0:02X} (expect ${WB:02X})', wit == WB)


def test_bare_no_regression(cart, tmp):
    print('bare CLOAD + RUN on [AAA,BBB] -> loads the FIRST file (unchanged):')
    cas = two_tok_tape(tmp, "a4")
    _, wit = run_typed(cart, cas, [(6.0, "CLOAD"), (8.0, "\r"), (20.0, "RUN"), (21.0, "\r")],
                       TXTBASE, 6, cap_time=34.0, poison_witness=True)
    return check(f'  witness=${wit if wit else 0:02X} (expect ${WA:02X})', wit == WA)


def test_not_found(cart, tmp):
    print('RUN"CAS:ZZZ" on [AAA,BBB] -> not found, nothing runs (no hang):')
    cas = two_tok_tape(tmp, "a5")
    wit = run_cmd(cart, cas, 'RUN"CAS:ZZZ"', cap_time=50.0)
    return check(f'  witness=${wit if wit else 0:02X} (expect poison ${POISON:02X})',
                 wit == POISON)


def test_case_sensitive(cart, tmp):
    print('RUN"CAS:bbb" on [AAA,BBB] -> case-sensitive, "bbb" != "BBB", not found:')
    cas = two_tok_tape(tmp, "a6")
    wit = run_cmd(cart, cas, 'RUN"CAS:bbb"', cap_time=50.0)
    return check(f'  witness=${wit if wit else 0:02X} (expect poison ${POISON:02X} '
                 f'-- matches the CF-3300)', wit == POISON)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", default=DEFAULT_CART)
    args = ap.parse_args()
    if not os.path.exists(args.cart):
        print(f"cart not found: {args.cart} (run: make build/basic.rom)")
        return 2
    tmp = tempfile.mkdtemp(prefix="cas_match_")
    tests = [test_skip_match_tok, test_skip_match_asc, test_mixed_skip,
             test_bare_no_regression, test_not_found, test_case_sensitive]
    ok = True
    for t in tests:
        ok = t(args.cart, tmp) and ok
    print("\n" + ("ALL PASS -- cassette name-matching finds the named file, skips "
                  "earlier files, is case-sensitive, and fails cleanly when absent"
                  if ok else "FAIL -- see per-case results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
