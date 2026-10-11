#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASWBRK: a tape WRITE broken with Ctrl-STOP -- the VG-8020 against
zerobas's diskless machine. The write side of D-CASBRK, and D-LOADERRRET's
tape-write sites: zerobas's TAPOUT never looked at the keyboard, so a CSAVE /
BSAVE / SAVE / PRINT # to tape ran to the end where the VG-8020 raises
`Device I/O error` (19) in the statement's line, trapped.

Every write here is long enough that the break lands in its DATA (a short write
is mostly its ~7 s header leader, and the VG-8020 does not break a leader --
row `pleader`). `REMS` makes the program ~1.6 KB.

  dcsave   CSAVE"X" typed, broken in the data         -> the message text
  pcsave   10 ON ERROR GOTO 90 : 15 CSAVE"X"           -> `[E err erl]`
  pbsave   ... 15 BSAVE"CAS:X",&H8000,&H87FF (2 KB)
  psave    ... 15 SAVE"CAS:X" (the ASCII listing, block by block)
  pprint   ... 15 OPEN"CAS:X"FOR OUTPUT AS#1 + forty 200-char PRINT #1
  pleader  pbsave broken 2 s in: inside the header LEADER -> no error, on both
  pctl     pcsave not broken                            -> no error
  phold    pbsave, the handler then loops; Ctrl-STOP held 0.9 s -- the press
           that broke the write is consumed on both (no `Break` in the handler)

Read as `[E err erl]` (+ `X` if the handler's loop finished, + `Break in n`),
`no error` (`[N 1 ]`), or the last message line.

Exit 0 all agree; 1 a divergence; 2 the reference gave no reading.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
BRK = ["@WAIT12", "@BREAK", "@WAIT12"]
REMS = [f"{n} REM " + "X" * 200 for n in range(1, 9)]
HANDLER = '90 PRINT"[E";ERR;ERL;"]":END'
LOOPH = '90 PRINT"[E";ERR;ERL;"]":FOR I=1 TO 300:NEXT:PRINT"[X]":END'


def prog(verb, tail=BRK, rems=False, handler=HANDLER):
    return ["NEW"] + (REMS if rems else []) + [
        "10 ON ERROR GOTO 90", f"15 {verb}", '30 PRINT"[N";1;"]":END',
        handler, "RUN"] + tail


BIG = 'BSAVE"CAS:X",&H8000,&H87FF'
CASES = {
    "dcsave": ["NEW"] + REMS + ['CSAVE"X"'] + BRK,
    "pcsave": prog('CSAVE"X"', rems=True),
    "pbsave": prog(BIG),
    "psave": prog('SAVE"CAS:X"', rems=True),
    "pprint": prog('OPEN"CAS:X"FOR OUTPUT AS#1:FOR J=1 TO 40:'
                   'PRINT#1,STRING$(200,65):NEXT:CLOSE'),
    "pleader": prog(BIG, tail=["@WAIT2", "@BREAK", "@WAIT30"]),
    "pctl": prog('CSAVE"X"', tail=["@WAIT20"]),
    "phold": prog(BIG, handler=LOOPH),
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
        r = f"E{e[-1][0]} in {e[-1][1]}"
        if "[X]" in flat:
            r += " X"
        b = re.findall(r"Break in \d+", flat)
        return r + (f" {b[-1]}" if b else "")
    if "[N 1 ]" in flat:
        return "no error"
    m = re.findall(r"Device I/O error|load error|Break in \d+|Break", flat)
    return m[-1] if m else None


def main():
    only = sys.argv[1:] or list(CASES)
    if os.environ.get("CASWBRK_OURS_ONLY"):
        # the knife runner's switch (scratchpad/caswbrk_knives.py): the VG-8020
        # column cannot move with our ROM, so a cut is judged on ours alone
        for n in only:
            print(f"== {n:7s} ours {reading(OURS, n)!s}", flush=True)
        return 0
    got = {(t, n): reading(m, n) for t, m in (("VG-8020", REF), ("OURS", OURS)) for n in only}
    for n in only:
        print(f"== {n:7s} VG-8020 {got[('VG-8020', n)]!s:18s} ours {got[('OURS', n)]!s}")
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
