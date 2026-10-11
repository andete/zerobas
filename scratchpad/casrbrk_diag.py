#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASRBRK diagnostic: a tape READ broken with Ctrl-STOP in its DATA -- the
VG-8020 against zerobas's diskless machine, under ON ERROR. The read twin of
D-CASWBRK (D-CASBRK measured only the SEARCH, with no tape).

Tapes (cas_encode): `bin` -- binary X, 4 KB at &HC000 (&H8000, the first cut, loaded over the program: `Syntax error in 12592` on both); `asc` -- ASCII X, forty
lines. Each verb is broken at three points after RUN (`b8` / `b15` / `b25`),
so at least one lands in the data; `nb` is the unbroken control.
Read as `[E err erl]`, `no error` (`[N 1 ]`), or the last message line.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
TEXT = "".join(f"{n} REM {'Y' * 60}\n" for n in range(100, 140))
TAPES = {"bin": cas_encode.build_cas("X", 0xC000, 0xC000, bytes(range(256)) * 16),
         "asc": cas_encode.build_cas_ascii("X", TEXT)}
VERB = {"bin": 'BLOAD"CAS:X"', "asc": 'LOAD"CAS:X"'}


def prog(tape, tail):
    return ["NEW", "10 ON ERROR GOTO 90", f"15 {VERB[tape]}", '30 PRINT"[N";1;"]":END',
            '90 PRINT"[E";ERR;ERL;"]":END', "RUN"] + tail


CASES = {}
for t in TAPES:
    CASES[f"{t}_nb"] = (t, prog(t, ["@WAIT60"]))
    for w in (8, 15, 25):
        CASES[f"{t}_b{w}"] = (t, prog(t, [f"@WAIT{w}", "@BREAK", "@WAIT40"]))
RX_E = re.compile(r"\[E\s+(-?\d+)\s+(-?\d+)\s*\]")


def reading(machine, name):
    t, lines = CASES[name]
    path = probe_tmp.tmp(f"casrbrk_{t}.cas")
    open(path, "wb").write(TAPES[t])
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), cassette=path)[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    e = RX_E.findall(flat)
    if e:
        return f"E{e[-1][0]} in {e[-1][1]}"
    m = re.findall(r"Device I/O error|load error|Break in \d+|Break|Found:\S*", flat)
    if "[N 1 ]" in flat:
        # 🔴 a message BESIDE `[N` is the finding (BLOAD's `load error`, then ran
        # on) -- the first cut read `no error` and hid it
        msg = [x for x in m if not x.startswith("Found:")]
        return "no error" + (f" (+{msg[-1]})" if msg else "")
    return (m[-1] if m else None, flat[-100:])


def main():
    only = sys.argv[1:] or list(CASES)
    for n in only:
        for side, m in (("VG-8020", REF), ("OURS", OURS)):
            print(f"== {n:7s} {side:8s} {reading(m, n)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
