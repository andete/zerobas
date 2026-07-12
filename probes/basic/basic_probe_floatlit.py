#!/usr/bin/env python3

"""Float-literal crunch probe — characterise, then differentially prove, how
MSX-BASIC crunches decimal floating-point literals (Phase-3 float pack F1;
docs/spec-basic-float-core.md §3c).

Mechanism (harness rework, 2026-07-12): each literal L is injected as the STORED
line  `1 A=L`  (a numbered line, so it is tokenised into the program area but
never executed — no RUN), via omsx_repl's typing-free KEYBUF path. The crunched
line then lives in the program at TXTTAB ($F676): after the 2-byte link and
2-byte line number come the tokens `A` `=` (41 EF) followed by the literal's
crunched form — for a float literal that IS the stored representation (token $1D
+ 4 value bytes single / $1F + 8 value bytes double; int forms $0F/$1C/$11-$1A),
the same bytes this probe pins. So reading TXTTAB captures the classification
rule AND the BCD encoding, black-box, WITHOUT freezing the CPU — which lets the
whole matrix share ONE boot (batched, ~35x faster than the former one-boot-per-
literal BLOAD-freeze, and free of the matrix-typing flake).

The prior mechanism (BLOAD-freeze at TAPION with the line crunched in KBUF) was
proven byte-identical to this stored-line capture across all 66 literals on BOTH
machines before the switch (incl. the "both rejected" 1e63/65535% cases, which
here leave the program empty -> no `A=` marker -> rejected).

Characterisation mode (default, reference only): print each literal's crunched
bytes.  Differential mode (--zb-machine, F1 acceptance): also crunch on the
zerobas repack build and assert the bytes are identical.

Clean-room: observed outputs only; the reference ROM is a black box. No
disassembly. See the clean-room firewall (CONTRIBUTING.md).
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse

import omsx_repl  # typing-free KEYBUF-injection REPL driver (harness rework)

REF_MACHINE = "Philips_VG_8020"
TXTTAB = 0xF676   # sysvar: 2-byte LE pointer to the BASIC text base (both machines)
DUMPLEN = 32      # bytes read from the text base (link+lineno+A=+longest literal)
MARKER = bytes([0x41, 0xEF])   # 'A' '=' — the crunched literal starts after this

# The classification/encoding matrix (spec §3c working rules — this probe is
# what pins them). Grouped for the analysis write-up; each entry is stored as
# the line `1 A=<lit>`.
LITERALS = [
    # int forms stay int (regression anchors)
    "0", "9", "10", "255", "256", "32767",
    # integer > 32767: the int16 wall
    "32768", "40000", "65535", "65536", "99999", "999999",
    # digit-count wall (single holds 6 BCD digits)
    "1000000", "9999999", "10000000", "99999999", "123456789012345678",
    # decimal point forms
    ".5", "0.5", "1.5", "1.", "1.0", "3.14159", "3.1415926", "0.1",
    ".000001", "123456.7", "1234567.8",
    # rounding probes (7+ significant digits into a 6-digit single?)
    "1234567", "1234564", "9999995",
    # E/D exponent forms
    "1e5", "1e10", "1.5e2", "1e-3", "2.5e-10", "1d5", "1.5d-3",
    # exponent range walls (excess-64: ±63?)
    "1e38", "1e62", "1e63", "1e64", "1e-63", "1e-64", "1e-65",
    # explicit type suffixes
    "1!", "1#", "32767#", "1.5!", "1.5#", "100000!", "1234567!", "65535%",
    # rounding tie-breakers (exact half at the kept-digit wall: half-up vs even)
    "1234565!", "1234575!", "123456789012345", "1234567890123455",
    # rounding carry-out-of-all-digits (PRINT 9999995! shows 1000000 = 1e6, not
    # 1e7 — does the crunch renormalise the exponent after the carry?)
    "9999995!", "9999999999999999",
    # zero forms
    "0!", "0#", ".0", "0e0",
    # %-suffix in range: is the '%' consumed into the int token or kept?
    "1%", "100%", "30000%",
]


def crunched(raw: str | None) -> bytes | None:
    """The crunched literal from a TXTTAB hex capture (`raw` = the bytes from the
    text base): the bytes after the `A=` marker (41 EF), up to and including the
    first 0x00 terminator. None when the literal was REJECTED at crunch time
    (e.g. 1e63 / 65535%).

    Rejection is detected by the LINK POINTER, not the marker: a rejected `1 A=L`
    line is never stored, and the preceding NEW leaves the 2-byte link at the
    base = 00 00 (the empty-program marker) — but NEW only rewrites that link, it
    does NOT wipe the prior line's physical bytes, so a raw `41 EF` search would
    read STALE data past a zero link. A stored line always has a link whose high
    byte is >= $80 (the program lives in page 2, $8000+), so link == 00 00 ⇔
    empty ⇔ rejected.

    Trimming at the first 0x00 can truncate a value with an embedded zero
    MID-value (e.g. 256 -> 1C 00, 1e-65 -> 1D 00) rather than only at the real
    terminator — a known, deliberate weakening that the exhaustive byte-for-byte
    proof in tests/test_float.py covers. (basic_probe_crunch.py avoids the
    truncation entirely by dereferencing the line's link pointer for its exact
    extent; floatlit keeps the simpler first-0x00 trim because every float
    literal's terminator IS its first 0x00 unless the value embeds one, and the
    embedded-zero cases are what test_float.py locks byte-for-byte.) It also makes
    the check immune to the cold-boot ambient RAM past the terminator (which
    differs between a real VG-8020 and the C-BIOS repack)."""
    if not raw:
        return None
    b = bytes.fromhex(raw)
    if len(b) < 2 or (b[0] == 0 and b[1] == 0):
        return None                       # empty program -> literal rejected
    i = b.find(MARKER)
    if i < 0:
        return None
    tail = b[i + len(MARKER):]
    j = tail.find(0)
    return tail if j < 0 else tail[:j + 1]


def _hex(bs: bytes | None) -> str:
    return " ".join(f"{b:02X}" for b in bs) if bs else "<rejected>"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help=f"reference oracle machine (default {REF_MACHINE})")
    ap.add_argument("--zb-machine", dest="zb_machine",
                    help="differential mode: also crunch on this repack machine "
                         "(BASIC in slot 0) and assert byte equality")
    ap.add_argument("--only", help="substring filter on the literal")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot (slow) instead of the "
                         "default single-boot batch — use to rule out inter-case "
                         "leakage when a batched case looks wrong")
    args = ap.parse_args()

    lits = [l for l in LITERALS if not (args.only and args.only not in l)]
    # each literal is a numbered STORED line -> tokenised, never executed; NEW
    # between cases clears the program so a REJECTED literal reads back empty.
    specs = [("direct", [f"1 A={lit}"]) for lit in lits]
    cap = ("mem_indirect", TXTTAB, DUMPLEN)

    # Characterisation mode: reference only -> plain batch.
    if not args.zb_machine:
        for lit, raw in zip(lits, omsx_repl.run_cases(
                args.machine, specs, batch=not args.boot_per_case,
                reset=("NEW",), capture=cap)):
            print(f"a={lit:<22} {_hex(crunched(raw))}")
        return 0

    def compare(i, ref_raw, zb_raw):
        ref, zb = crunched(ref_raw), crunched(zb_raw)
        if ref is None and zb is None:
            return True   # pre-authorised: crunch-time rejection on BOTH sides
        return ref is not None and zb is not None and ref == zb

    verdicts, ref_raws, zb_raws = omsx_repl.run_differential(
        args.machine, args.zb_machine, specs, compare,
        batch=not args.boot_per_case, reset=("NEW",), capture=cap)

    ok = True
    for lit, good, ref_raw, zb_raw in zip(lits, verdicts, ref_raws, zb_raws):
        ok = ok and good
        ref = crunched(ref_raw)
        note = "  [both rejected]" if ref is None and crunched(zb_raw) is None else ""
        print(f"{'PASS' if good else 'FAIL'}  a={lit:<22} ref: {_hex(ref)}{note}")
        if not good:
            print(f"{'':>32}zb : {_hex(crunched(zb_raw))}")

    print("\nALL PASS — float-literal crunch is byte-identical" if ok
          else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
