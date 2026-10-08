#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASWBRK: a tape WRITE broken with Ctrl-STOP -- the VG-8020 against
zerobas's diskless machine, under ON ERROR. The write side of D-CASBRK: the
tape header writes in basic/files.asm (OPEN "CAS:" FOR OUTPUT) and
basic/save.asm still `jp c,load_error`, which prints and RETURNS.

Each row records onto a fresh `cassetteplayer new` tape and breaks about a
second in, inside the header's leader tone:

  pcsave  10 ON ERROR GOTO 90 : 20 CSAVE"X"
  psave   ... 20 SAVE"CAS:X"
  pasave  ... 20 SAVE"CAS:X",A
  pbsave  ... 20 BSAVE"CAS:X",&H9000,&H90FF
  popen   ... 20 OPEN"CAS:X"FOR OUTPUT AS#1

Read as `[E err erl]`, `[N 1 ]` (no error: the program ran on) or the last
message. ⚠️ A write that FINISHES before the break also reads `[N 1 ]` -- so
`no error` on BOTH sides is an instrument suspect, not an agreement.

Exit 0 all agree; 1 a divergence; 2 the reference gave no reading.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
BRK = ["@WAIT1", "@BREAK", "@WAIT6"]


def prog(verb):
    return ["NEW", "10 ON ERROR GOTO 90", f"20 {verb}", '30 PRINT"[N";1;"]":END',
            '90 PRINT"[E";ERR;ERL;"]":END', "RUN"] + BRK


CASES = {
    "pcsave": prog('CSAVE"X"'),
    "psave": prog('SAVE"CAS:X"'),
    "pasave": prog('SAVE"CAS:X",A'),
    "pbsave": prog('BSAVE"CAS:X",&H9000,&H90FF'),
    "popen": prog('OPEN"CAS:X"FOR OUTPUT AS#1'),
}
RX_E = re.compile(r"\[E\s+(-?\d+)\s+(-?\d+)\s*\]")


def reading(machine, name):
    wav = probe_tmp.tmp(f"caswbrk_{name}_{machine[:6]}.wav")
    if os.path.exists(wav):
        os.remove(wav)
    raw = omsx_repl.run_cases(machine, [("direct", CASES[name])], batch=False,
                              reset=("", "SCREEN 0"),
                              prologue=(f"cassetteplayer new {{{wav}}}",))[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    e = RX_E.findall(flat)
    if e:
        return f"E{e[-1][0]} in {e[-1][1]}"
    if "[N 1 ]" in flat:
        return "no error"
    m = re.findall(r"Device I/O error|load error|Break in \d+|Break", flat)
    return m[-1] if m else None


def main():
    only = sys.argv[1:] or list(CASES)
    got = {(t, n): reading(m, n) for t, m in (("VG-8020", REF), ("OURS", OURS)) for n in only}
    for n in only:
        print(f"== {n:6s} VG-8020 {got[('VG-8020', n)]!s:16s} ours {got[('OURS', n)]!s}")
    if any(got[("VG-8020", n)] is None for n in only):
        print("\nINSTRUMENT FAULT: the VG-8020 gave no reading -- no reference")
        return 2
    bad = [n for n in only if got[("VG-8020", n)] != got[("OURS", n)]]
    for n in bad:
        print(f"DIVERGES {n}: VG-8020 {got[('VG-8020', n)]} vs ours {got[('OURS', n)]}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a tape write broken with Ctrl-STOP "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
