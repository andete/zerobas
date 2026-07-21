#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""PLAY acceptance — audio Slice 2a (docs/spec-basic-audio-play-slice2a.md).

Two halves:

  1. ERROR SURFACE (differential vs the Philips VG-8020) — give PLAY good and
     malformed MML and compare the trapped ERR between zerobas and the reference.
     This exercises the FULL resident path the tests/test_play_parse.py host layer
     cannot: tokenise PLAY -> ex_play -> str_eval each string arg -> marshal into
     the VCBs -> subrom_call into the page-1 parser tenant -> error propagation ->
     statement chaining. (That path is exactly where this arc's recurring lesson
     bit: the host test was green while the missing kwtable entry AND an HL clobber
     across the CALSLT were both broken -- only this differential caught them.)

  2. INTEGRATION SELF-CHECK (zerobas) — run PLAY on a fresh boot, then PEEK MUSICF
     ($FB3F, the reference work-area address, Q2 faithfulness) and confirm the
     expected voices are marked active and PLAY returned to the prompt (no hang).
     MUSICF is a zerobas-only assertion, not a differential: with no Slice-2a live
     drain our MUSICF stays set, whereas the reference's interrupt player clears it
     as the (short) music finishes -- a differential read would race.

Heavy + oracle-dependent (boots openMSX per case; the error-surface half needs
your VG-8020 reference ROM). Scope with `--only <substr>`. The emulator-free fast
layer is tests/test_play_parse.py under `make unit-test`."""
from __future__ import annotations
import argparse, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# --- ERROR SURFACE (differential; want == reference == zerobas) ----------------
# 'cont' = ran on to completion (valid MML); 'ERR<n>' = trapped MSX error code.
ERR_CASES = [
    ("ok_notes",   'PLAY"CDEFGAB"',      "cont"),   # linear notes -> ok
    ("ok_full",    'PLAY"O5L8T160V12CDE"', "cont"), # octave/length/tempo/vol -> ok
    ("ok_rest",    'PLAY"CR4C"',         "cont"),    # rest -> ok
    ("ok_env",     'PLAY"S10M2000C"',    "cont"),    # envelope shape/period -> ok
    ("ok_three",   'PLAY"C","E","G"',    "cont"),    # three voices -> ok
    ("ok_emptystr",'PLAY"","E"',         "cont"),    # empty-string voice (the faithful skip)
    ("ok_chain",   'PLAY"C":?"X"',       "cont"),    # chains into the next statement
    ("badcmd",     'PLAY"CZ"',           "ERR5"),    # unknown MML command -> Illegal fn call
    ("tie_unsup",  'PLAY"C&C"',          "ERR5"),    # '&' is not MSX1 MML -> Illegal fn call
    ("oct_hi",     'PLAY"O9"',           "ERR5"),    # octave > 8 -> Illegal fn call
    ("len_zero",   'PLAY"L0"',           "ERR5"),    # length 0 -> Illegal fn call
    ("tempo_lo",   'PLAY"T10"',          "ERR5"),    # tempo < 32 -> Illegal fn call
    ("vol_hi",     'PLAY"V16"',          "ERR5"),    # volume > 15 -> Illegal fn call
    ("bare_comma", 'PLAY,"E"',           "ERR2"),    # missing operand -> Syntax error
    ("numeric",    'PLAY 5',             "ERR13"),   # numeric arg -> Type mismatch
]

# --- INTEGRATION SELF-CHECK (zerobas only): (label, stmt, expected MUSICF) ------
MUSICF_CASES = [
    ("m_one",   'PLAY"CDE"',       1),   # voice 0 active
    ("m_three", 'PLAY"C","E","G"', 7),   # voices 0,1,2 active
    ("m_two",   'PLAY"C","E"',     3),   # voices 0,1 active
]


def err(machine, stmt):
    """Run `stmt` under ON ERROR; return 'ERR<n>' (trapped) or 'cont' (ran on)."""
    prog = ["10 ON ERROR GOTO 100", f"20 {stmt}",
            "30 PRINTCHR$(67);CHR$(35):END", "100 PRINTCHR$(35);ERR;CHR$(35)", "RUN"]
    raw = omsx_repl.run_case(machine, "direct", prog) or ""
    e = re.findall(r"#([^#]*)#", raw)
    if e:
        return f"ERR{e[-1].strip()}"
    return "cont" if "C#" in raw else f"?({re.sub(r'\\s+', ' ', raw).strip()[-30:]!r})"


def musicf(machine, stmt):
    """Run `stmt`, then PEEK MUSICF ($FB3F). Returns the int, or None."""
    prog = ["10 ON ERROR GOTO 100", f"20 {stmt}",
            "30 PRINTCHR$(35);PEEK(&HFB3F);CHR$(35):END",
            "100 PRINTCHR$(35);CHR$(69);ERR;CHR$(35)", "RUN"]
    raw = omsx_repl.run_case(machine, "direct", prog) or ""
    m = re.findall(r"#\s*(\d+)\s*#", raw)
    return int(m[-1]) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE, help="reference machine")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only")
    ap.add_argument("--no-ref", action="store_true",
                    help="skip the reference side (zerobas self-check only)")
    args = ap.parse_args()
    ok = True

    print("--- PLAY error surface (differential vs VG-8020) ---")
    for label, stmt, want in ERR_CASES:
        if args.only and args.only not in label:
            continue
        zb = err(args.zb_machine, stmt)
        ref = None if args.no_ref else err(args.machine, stmt)
        good = (zb == want) and (args.no_ref or ref == want)
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {label:9} {stmt:22} "
              f"zb={zb:7} ref={ref if ref else '-':7} want={want}")

    print("\n--- PLAY -> MUSICF integration (zerobas self-check) ---")
    for label, stmt, want in MUSICF_CASES:
        if args.only and args.only not in label:
            continue
        got = musicf(args.zb_machine, stmt)
        good = got == want
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {label:9} {stmt:22} MUSICF zb={got} want={want}")

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
