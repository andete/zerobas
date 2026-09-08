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
    # --- D-WAIT: WAIT shares OUT's argument domain, because it shares the guard --
    # 🔴 EVERY WAIT ROW HERE MUST ABORT IN THE PARSE. `check_fperr_only` runs
    # AFTER both evals and BEFORE the spin loop, so an out-of-domain argument
    # raises and the loop is never entered. A row whose arguments were VALID would
    # spin until its mask was satisfied -- which is WAIT's documented behaviour and
    # not something a batch can host. The terminating forms are measured in
    # scratchpad/wait_probe.py instead, each constructed to finish.
    ("wait_port_ovf", "WAIT 99999,1", "ERR6"),
    ("wait_mask_ovf", "WAIT 0,99999", "ERR6"),
    ("wait_xor_ovf",  "WAIT 0,1,99999", "ERR6"),
    ("wait_nocomma",  "WAIT 254",     "ERR2"),   # the mask is not optional
    # --- D-RAWVAL: the SECOND argument is a BYTE (0..255), not an address --------
    # 🔴 EVERY ROW IN THIS FILE FOR POKE/VPOKE/OUT USED TO BE ABOUT THE FIRST
    # ARGUMENT. All three handlers evaluated the VALUE with `eval_addr` -- the
    # ADDRESS domain, which WRAPS by design -- and then took `ld a,e`, the low
    # byte, silently. Measured on BOTH references: `POKE x,256` wrote 0 and
    # `POKE x,-1` wrote 255 with no error, where the references raise ERR 5 and
    # write NOTHING (scratchpad/rawval_probe.py primes the target with 65 and
    # PEEKs it back, so "refused" and "wrote something" are distinguishable).
    # Fixed byte-neutrally onto `eval_byte_checked`, which already existed.
    ("poke_val_hi",   "POKE &HD020,256", "ERR5"),
    ("poke_val_neg",  "POKE &HD020,-1",  "ERR5"),
    ("poke_val_max",  "POKE &HD020,255", "cont"),   # 255 IS legal -- the boundary
    ("vpoke_val_hi",  "VPOKE 100,256",   "ERR5"),
    ("vpoke_val_neg", "VPOKE 100,-1",    "ERR5"),
    ("out_val_hi",    "OUT 0,256",       "ERR5"),
    ("out_val_neg",   "OUT 0,-1",        "ERR5"),
    # 🎯 AND THE PORT IS *NOT* A BYTE -- MEASURED, NOT INHERITED. `OUT 256,0` is
    # ACCEPTED on both references: the port wraps in the address domain where the
    # value raises. `out_neg` above says the same for -1. These two rows are what
    # stops the next reader "harmonising" OUT's two arguments onto one domain and
    # shipping a regression [[two-rules-that-coincide-on-every-row-you-have]].
    ("out_port_hi",   "OUT 256,0",       "cont"),
    # 🎯 PRECEDENCE: OVERFLOW BEATS DOMAIN, and no row had ever paired a bad
    # address with a bad VALUE -- every existing one pairs a bad address with a
    # legal value, so the fix could have changed this answer unobserved.
    ("poke_both_bad", "POKE 99999,256",  "ERR6"),
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
    # --- B: VPOKE VRAM-domain correction (0..16383, NOT the 0..65535 address ------
    # domain F2 wired) + STRING$/SPACE$/ON/WIDTH byte domain 0..255. Shared leaf
    # get_byte_arg (0..255) / get_vram_arg (0..16383): int16-coerce (ERR6 >32767)
    # then per-site range-check (ERR5 outside). LANDED (this commit).
    ("vpoke_vram",    "VPOKE 40000,0",       "ERR6"),  # >int16 -> ERR6
    ("vpoke_ill",     "VPOKE 16384,0",       "ERR5"),  # >VRAM, <=int16 -> ERR5
    ("vpoke_neg",     "VPOKE -1,0",          "ERR5"),  # <0 -> ERR5 (was cont: wrapped)
    ("vpoke_vmax",    "VPOKE 16383,0",       "cont"),  # VRAM max -> cont
    ("string_n",      "A$=STRING$(99999,42)","ERR6"),  # count >int16 -> ERR6
    ("string_c",      "A$=STRING$(5,256)",   "ERR5"),  # char code >255 -> ERR5
    ("string_neg",    "A$=STRING$(-1,65)",   "ERR5"),  # negative count -> ERR5
    ("string_ok",     "A$=STRING$(3,255)",   "cont"),  # count 3, char 255 -> cont
    ("space_n",       "A$=SPACE$(99999)",    "ERR6"),  # >int16 -> ERR6
    ("space_neg",     "A$=SPACE$(-1)",       "ERR5"),  # negative -> ERR5
    ("space_ok",      "A$=SPACE$(100)",      "cont"),  # in byte domain + fits string pool -> cont
    #  (SPACE$(255) is NOT used here: the ref's default 200-byte string pool
    #   raises ERR 14 out-of-string-space first — a memory limit, not coercion.)
    ("on_n",          "ON 99999 GOTO 30",    "ERR6"),  # >int16 -> ERR6
    ("on_ill",        "ON 256 GOTO 30",      "ERR5"),  # >255, <=int16 -> ERR5
    ("on_ok",         "ON 1 GOTO 30",        "cont"),  # branches to 30 -> C# -> cont
    ("width_n",       "WIDTH 256",           "ERR5"),  # >255, <=int16 -> ERR5
    ("width_ovf",     "WIDTH 99999",         "ERR6"),  # >int16 -> ERR6
    ("width_ok",      "WIDTH 32",            "cont"),  # in byte domain (valid both modes) -> cont
]

# Not yet faithful — reported as a straight differential until their stage lands.
# (Empty: stage B was the last of the arc; every site is now ASSERTED above.)
PENDING = []


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
