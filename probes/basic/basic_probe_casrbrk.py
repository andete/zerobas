#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASRBRK: a tape READ broken with Ctrl-STOP in its DATA -- the VG-8020
against zerobas's diskless machine. The read twin of D-CASWBRK; D-CASBRK
measured only the SEARCH. zerobas's TAPION / TAPIN never asked BREAKX, BLOAD's
data arms printed `load error`, and the ASCII loader took a cut read for the
end of the file -- it kept the lines read so far and said nothing.

Tapes (cas_encode): `bin` -- binary X, 4 KB at &HC000; `asc` -- ASCII X,
forty 70-character lines; `tok` -- the same forty lines tokenised, laid out as
CSAVE writes them. Ctrl-STOP lands `@WAIT` seconds after the verb starts.

  bnb / bb2 / bb8   BLOAD under ON ERROR, not broken / broken at 2 s (the
              header leader) / at 8 s (the data)
  bhold       bb8 with a handler that then loops: the press is consumed
  anb / ab2 / ab8 / ab15   LOAD (it replaces the program: no handler, no line)
  cnb / cb8   CLOAD typed
  mb2 / mb8   MERGE under ON ERROR, broken in the first block's priming / later
  inb / ob2 / ib8   LINE INPUT # from a tape channel, in a loop, under ON ERROR
              (ob2: broken while OPEN primes the first block)

Read as `[E err erl]` (+ ` X` when the handler's loop finished), the last
message, or `no error` / `no message`.

Exit 0 all agree; 1 a divergence; 2 the reference gave no reading.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
LINES = [(n, " " + "Y" * 60) for n in range(100, 140)]
TEXT = "".join(f"{n} REM{t}\n" for n, t in LINES)


def tokenised(lines, base=0x8001):
    """The program image CSAVE writes: [link][line no][REM $8F + text][0] per
    line, links absolute from `base`, then the $0000 end-link."""
    out, addr = b"", base
    for n, t in lines:
        body = bytes([0x8F]) + t.encode() + b"\x00"
        nxt = addr + 4 + len(body)
        out += nxt.to_bytes(2, "little") + n.to_bytes(2, "little") + body
        addr = nxt
    return out + b"\x00\x00"


TAPES = {"bin": cas_encode.build_cas("X", 0xC000, 0xC000, bytes(range(256)) * 16),
         "asc": cas_encode.build_cas_ascii("X", TEXT),
         "tok": cas_encode.build_cas_basic_csave("X", tokenised(LINES))}
HANDLER = '90 PRINT"[E";ERR;ERL;"]":END'
LOOPH = '90 PRINT"[E";ERR;ERL;"]":FOR I=1 TO 300:NEXT:PRINT"[X]":END'


def brk(w):
    return [f"@WAIT{w}", "@BREAK", "@WAIT40"]


def prog(verb, tail, handler=HANDLER):
    return ["NEW", "10 ON ERROR GOTO 90", f"15 {verb}", '30 PRINT"[N";1;"]":END',
            handler, "RUN"] + tail


INP = 'OPEN"CAS:X"FOR INPUT AS#1:FOR J=1 TO 40:LINE INPUT#1,A$:NEXT:CLOSE'
CASES = {
    "bnb": ("bin", prog('BLOAD"CAS:X"', ["@WAIT40"])),
    "bb2": ("bin", prog('BLOAD"CAS:X"', brk(2))),
    "bb8": ("bin", prog('BLOAD"CAS:X"', brk(8))),
    "bhold": ("bin", prog('BLOAD"CAS:X"', brk(8), handler=LOOPH)),
    "anb": ("asc", prog('LOAD"CAS:X"', ["@WAIT60"])),
    "ab2": ("asc", prog('LOAD"CAS:X"', brk(2))),
    "ab8": ("asc", prog('LOAD"CAS:X"', brk(8))),
    "ab15": ("asc", prog('LOAD"CAS:X"', brk(15))),
    "cnb": ("tok", ["NEW", 'CLOAD"X"', "@WAIT40"]),
    "cb8": ("tok", ["NEW", 'CLOAD"X"'] + brk(8)),
    "mb2": ("asc", prog('MERGE"CAS:X"', brk(2))),
    "mb8": ("asc", prog('MERGE"CAS:X"', brk(8))),
    "inb": ("asc", prog(INP, ["@WAIT60"])),
    "ob2": ("asc", prog(INP, brk(2))),
    "ib8": ("asc", prog(INP, brk(8))),
}
RX_E = re.compile(r"\[E\s+(-?\d+)\s+(-?\d+)\s*\]")
MSG = re.compile(r"Device I/O error|load error|Input past end|Break in \d+|Break|"
                 r"Syntax error(?: in \d+)?")


def reading(machine, name):
    t, lines = CASES[name]
    path = probe_tmp.tmp(f"casrbrk_{t}.cas")
    open(path, "wb").write(TAPES[t])
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), cassette=path)[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    after = flat[flat.rfind('CLOAD"X"') + 8:] if name.startswith("c") else \
        flat[flat.rfind(" RUN ") + 5:] if " RUN " in flat else None
    if after is None:
        return None
    e = RX_E.findall(after)
    m = MSG.findall(after)
    if e:
        r = f"E{e[-1][0]} in {e[-1][1]}" + (" X" if "[X]" in after else "")
        b = [x for x in m if x.startswith("Break")]
        return r + (f" {b[-1]}" if b else "")
    tail = f" (+{m[-1]})" if m else ""
    if "[N 1 ]" in after:
        return "no error" + tail
    return m[-1] if m else "no message"


def main():
    only = sys.argv[1:] or list(CASES)
    if os.environ.get("CASRBRK_OURS_ONLY"):
        for n in only:
            print(f"== {n:6s} ours {reading(OURS, n)!s}", flush=True)
        return 0
    got = {(t, n): reading(m, n) for t, m in (("VG-8020", REF), ("OURS", OURS)) for n in only}
    for n in only:
        print(f"== {n:6s} VG-8020 {got[('VG-8020', n)]!s:22s} ours {got[('OURS', n)]!s}")
    if any(got[("VG-8020", n)] is None for n in only):
        print("\nINSTRUMENT FAULT: the VG-8020 gave no reading -- no reference")
        return 2
    bad = [n for n in only if got[("VG-8020", n)] != got[("OURS", n)]]
    for n in bad:
        print(f"DIVERGES {n}: VG-8020 {got[('VG-8020', n)]} vs ours {got[('OURS', n)]}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a tape read broken with Ctrl-STOP "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
