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

Typed harness on the repack machine (C-BIOS_MSX1_EU_REPACK_DISK), which carries
the merged main ROM in slot 0 and its own <CassettePort/>, so no cartridge is
inserted. Until 2026-07-29 this ran the retired lean 16 KB cart as a `-cart` on
C-BIOS_MSX1_EU_TAPE (docs/spec-lean-retire-s3-gates.md); that rig is still
selectable with --machine C-BIOS_MSX1_EU_TAPE + --cart, and is the only mode
in which --cart means anything.
our own cas codec / tokeniser; the reference ROM is never read. NB fixture .cas
files are named by test id (not by the tape-internal name) so macOS's case-
insensitive FS can't merge an "abc"/"ABC" pair (see the tape memory note).

$ZEROBAS_BASIC_MACHINE override (docs/spec-eviction-g5-space.md): cas_open_match
+ cas_skip_data are a sub-ROM page-1 tenant (SUBROM_IDX_CASMATCH) on the repack
build, unlike the lean cart where they stay inline -- so the lean run above never
exercises the tenant. Setting ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK
(the shared constant/mechanism, basic_probe_cas_verbs.py; installed by `make
repack-machine`) switches the harness to that machine instead: it already bakes
in the merged ROM (+ the sub-ROM in slot 3-2) as its own slot-0 primary AND ships
a <CassettePort/>, so `--cart` is simply unused there (run_typed's own machine
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
import os as _zbo, sys as _zbs
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(_zbo.path.dirname(
    _zbo.path.abspath(__file__))), "lib"))
# 🎯 the project temp root, as a side effect of import (probe_tmp.py).
import probe_tmp  # noqa: E402,F401

# CAS_SYNC/BASIC_ID are no longer imported: the only user here was the local
# nopad builder, which is now a shim on cas_encode's shared one. A dead import
# is a claim that a file still assembles a .cas by hand, and this one does not.
from cas_encode import build_cas_basic, build_cas_basic_nopad  # noqa: E402
from bas_tokenise import make_multiline_program         # noqa: E402
from basic_probe_cas_ascii import build_ascii_cas       # noqa: E402
from basic_probe_cas_verbs import (                     # noqa: E402
    run_typed, check, MACHINE_TAPE, TXTBASE, WITNESS, POISON)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
# 🗄️ DEFAULT_CART is GONE (D-PROBEREACH3, 2026-08-31). It named
# `build/basic.rom` -- the lean 16 KB cart retired by
# docs/spec-lean-retire-s1..s3, for which the Makefile says there is no rule
# any more -- and after `--cart` stopped defaulting to it, nothing referenced
# it. A dead constant naming a retired artifact is the same rot this slice is
# clearing; pass `--cart` explicitly with the MACHINE_TAPE rig instead.
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE") or "C-BIOS_MSX1_EU_REPACK_DISK"

WA = 0xA1   # witness for file "AAA" / first file
WB = 0xB2   # witness for file "BBB" / second file


def tok(witness: int) -> bytes:
    """Tokenised program image that POKEs `witness` into WITNESS."""
    return make_multiline_program([(10, f"POKE&H{WITNESS:04X},&H{witness:02X}")], TXTBASE)


def asc(witness: int) -> list[str]:
    return [f"10 POKE&H{WITNESS:04X},&H{witness:02X}"]


# 🔴 THIS FUNCTION WAS THE ORIGINAL AND IS NOW A SHIM ON THE SHARED ONE
# (2026-09-24). It lived here alone while `basic_probe_kwsweep.py` built its
# multi-file tape with the PADDED builder and manufactured a TIER 1 ROM
# accusation that had to be withdrawn (D-CLOADSKIP). A faithful-fixture rule
# that lives in ONE probe is a rule the next probe does not have.
# ⚠️ Kept as a NAME rather than replaced at its call sites: `two_tok_tape` and
# the ASCII builders below read as a set, and renaming half of them would cost
# more clarity than the indirection does.
def tok_file_nopad(name: str, program: bytes) -> bytes:
    """A tokenised .cas file ending EXACTLY at the program's $0000 end-link.

    See `cas_encode.build_cas_basic_nopad`, which this now calls and whose
    docstring carries the measurement."""
    return build_cas_basic_nopad(name, program)


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
                       TXTBASE, 6, cap_time=cap_time, poison_witness=True,
                       machine=ZB_MACHINE)
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
                       TXTBASE, 6, cap_time=34.0, poison_witness=True, machine=ZB_MACHINE)
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
    # 🔴 NO DEFAULT CART, AND THE CHECK ONLY FIRES WHEN ONE IS GIVEN. `--cart`
    # used to default to `build/basic.rom` -- the lean 16 KB cart retired by
    # docs/spec-lean-retire-s1..s3, which the Makefile says has no rule any more
    # -- so this probe REFUSED at startup on a cartridge that, by this file's own
    # header, "is simply unused" on the default repack rig. It only means
    # anything with --machine C-BIOS_MSX1_EU_TAPE. Same half-finished migration
    # as basic_probe_cas_verify (D-PROBEREACH3): the retirement landed in the
    # prose and not in the code, and nothing noticed because no `make` target
    # runs either probe.
    ap.add_argument("--cart", default=None,
                    help="only used with the %s rig" % MACHINE_TAPE)
    args = ap.parse_args()
    if args.cart and not os.path.exists(args.cart):
        print(f"cart not found: {args.cart}")
        return 2
    print(f"(machine={ZB_MACHINE})")
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
