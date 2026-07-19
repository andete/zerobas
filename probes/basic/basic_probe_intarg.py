#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-F2-2 int-argument coercion acceptance (docs/spec-basic-df2-2-intarg-coercion.md).

VG-8020 differential: give each int-argument statement/function an out-of-domain
argument and check the trapped ERR matches the reference (or `cont` = no error).
Out-of-domain integer args must raise the reference's Overflow (ERR 6) or Illegal
function call (ERR 5), not silently coerce to a wrong value.

Capture: CHR$(35)='#' delimiters so the marker appears ONLY in runtime output, never
in the echoed source. The CONT branch ENDs so it cannot fall into the handler line.

Stages (spec §4): A1 = OUT (LANDED). A2 = PEEK/INP. B = STRING$/SPACE$/ON/WIDTH + the
VPOKE VRAM-domain correction. ASSERTED cases gate; PENDING cases are reported as a
straight differential (no hardcoded expectation) until their stage lands."""
from __future__ import annotations
import argparse, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# (label, statement). Each runs at line 20 under ON ERROR GOTO 100.
# result = "ERR<n>" (trapped) or "cont" (no error, ran on).
ASSERTED = [
    # --- A1: OUT — full address domain (0..65535 wrap, Overflow beyond) ----------
    ("out_port_ovf",  "OUT 99999,0",  "ERR6"),
    ("out_val_ovf",   "OUT 0,99999",  "ERR6"),
    ("out_addr_hi",   "OUT 40000,0",  "cont"),   # 40000 in address domain -> ok
    ("out_neg",       "OUT -1,0",     "cont"),   # -1 wraps -> ok
    ("out_ok",        "OUT 254,7",    "cont"),
    # --- regression guards: already-faithful address-domain sites (POKE, F2) ------
    ("poke_addr_ovf", "POKE 99999,0", "ERR6"),
    ("poke_addr_hi",  "POKE 40000,0", "cont"),
    ("poke_neg",      "POKE -1,0",    "cont"),
    ("poke_ok",       "POKE 32768,0", "cont"),
    # --- regression guards: VPOKE overflow (>int16) + normal still hold -----------
    ("vpoke_ovf",     "VPOKE 99999,0","ERR6"),
    ("vpoke_ok",      "VPOKE 100,42", "cont"),
    # --- A2: PEEK/INP — ADDRESS domain (function form), inline FPERR check at -----
    # ev_ff_arg so it fires even in non-checking consumers (FOR bounds). LANDED.
    ("peek",          "A=PEEK(99999)",             "ERR6"),  # >addr -> ERR6
    ("inp",           "A=INP(99999)",              "ERR6"),  # >addr -> ERR6
    ("peek_for",      "FOR I=PEEK(99999) TO 1:NEXT","ERR6"), # non-checking consumer -> ERR6
    ("peek_hi",       "A=PEEK(65535)",             "cont"),  # in address domain -> cont
    # --- A2+VPEEK: VPEEK — VRAM domain 0..16383 (int16-coerce ERR6 >32767, then -----
    # 0..16383 range-check ERR5 outside). Same inline leaf. LANDED (commit-of-A2).
    ("vpeek_ill",     "A=VPEEK(16384)", "ERR5"),  # >VRAM, <=int16 -> ERR5
    ("vpeek_ovf",     "A=VPEEK(40000)", "ERR6"),  # >int16 -> ERR6
    ("vpeek_neg",     "A=VPEEK(-1)",    "ERR5"),  # <0 -> ERR5
    ("vpeek_ok",      "A=VPEEK(16383)", "cont"),  # VRAM max -> cont
]

# Not yet faithful — reported as a straight differential until their stage lands.
PENDING = [
    # A2 (PEEK/INP) and VPEEK LANDED 2026-07-19 -> promoted to ASSERTED above.
    # Remaining = stage B: the VPOKE VRAM-domain correction + the byte-range sites.
    ("B",  "vpoke_vram","VPOKE 40000,0"),   # VRAM domain 0..16383 -> ref ERR6, zb cont
    ("B",  "vpoke_ill", "VPOKE 16384,0"),   # -> ref ERR5 (illegal fn), zb cont
    ("B",  "string_n",  "A$=STRING$(99999,42)"),
    ("B",  "string_c",  "A$=STRING$(5,256)"),
    ("B",  "space_n",   "A$=SPACE$(99999)"),
    ("B",  "on_n",      "ON 99999 GOTO 30"),
    ("B",  "width_n",   "WIDTH 256"),
]


def run(machine, stmt):
    prog = ["10 ON ERROR GOTO 100", f"20 {stmt}",
            "30 PRINTCHR$(67);CHR$(35):END", "100 PRINTCHR$(35);ERR;CHR$(35)", "RUN"]
    raw = omsx_repl.run_case(machine, "direct", prog) or ""
    e = re.findall(r"#([^#]*)#", raw)
    if e:
        return f"ERR{e[-1].strip()}"
    return "cont" if "C#" in raw else f"?({re.sub(chr(92)+'s+',' ',raw).strip()[-30:]!r})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only")
    args = ap.parse_args()
    ok = True

    print("--- ASSERTED (landed stages: A1 OUT + address-domain regression guards) ---")
    for label, stmt, want in ASSERTED:
        if args.only and args.only not in label:
            continue
        ref = run(args.machine, stmt)
        zb = run(args.zb_machine, stmt)
        good = (zb == want) and (ref == want)   # zb faithful AND oracle still agrees
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {label:16} {stmt:16} "
              f"zb={zb:7} ref={ref:7} want={want}")

    print("\n--- PENDING (reported, not gated — later stages) ---")
    for stage, label, stmt in PENDING:
        if args.only and args.only not in label:
            continue
        ref = run(args.machine, stmt)
        zb = run(args.zb_machine, stmt)
        tag = "MATCH" if ref == zb else "DIVERGE"
        print(f"  [{stage}] {label:12} {stmt:22} zb={zb:7} ref={ref:7} {tag}")

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
