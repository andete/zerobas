#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASBIN: BINARY (BSAVE, $D0) files in a tape search -- the VG-8020 against
zerobas's diskless machine.

Filed by D-CASTYPE, which made LOAD / RUN / MERGE / OPEN "CAS:" and CLOAD
step over a file of the wrong type: `cas_skip_data` has no $D0 arm (`unknown
id -> error`), so a binary file in the way still stops them here. And BLOAD's
own tape path (basic/bload-body.inc) takes the FIRST file on the tape and
never reads the name: a non-binary file there is an untrappable `load error`.

  X1 = binary X, &H9000 = 17      X2 = binary X, &H9000 = 34
  Y  = binary Y, &H9000 = 17      A  = ASCII X ("20 STOP")
  T  = tokenised X ("10 END", CSAVE-faithful)

  bnn    BLOAD"CAS:X" on Y + X2          -> PEEK(&H9000)  (name: skip Y)
  bty    BLOAD"CAS:X" on A + X2          -> PEEK          (type: skip A)
  bbare  BLOAD"CAS:" on A + X2           -> PEEK          (bare: skip A?)
  bnodev BLOAD"X" (no device) on Y + X2 -> PEEK          (diskless: the tape)
  bscr   BLOAD"CAS:X" on Y + X2          -> the search's Skip : / Found: rows
  lbin   LOAD"CAS:X" on X1 + A, LIST     -> 20 STOP       (LOAD skips a binary)
  cbin   CLOAD"X" on X1 + T, LIST        -> 10 END        (CLOAD likewise)

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
PROG = bytes([0x07, 0x80, 0x0A, 0x00, 0x81, 0x00, 0x00, 0x00])     # 10 END
BIN = {k: cas_encode.build_cas(n, 0x9000, 0x9000, bytes([v] * 16))
       for k, n, v in (("X1", "X", 17), ("X2", "X", 34), ("Y", "Y", 17))}
PARTS = dict(BIN, A=cas_encode.build_cas_ascii("X", "20 STOP\n"),
             T=cas_encode.build_cas_basic_csave("X", PROG))
WAIT = ["@WAIT25"]
PEEK = ['PRINT"[P";PEEK(&H9000);"]"']
CASES = {
    "bnn": (("Y", "X2"), ["NEW", "POKE&H9000,0", 'BLOAD"CAS:X"'] + WAIT + PEEK, "peek"),
    "bty": (("A", "X2"), ["NEW", "POKE&H9000,0", 'BLOAD"CAS:X"'] + WAIT + PEEK, "peek"),
    "bbare": (("A", "X2"), ["NEW", "POKE&H9000,0", 'BLOAD"CAS:"'] + WAIT + PEEK, "peek"),
    "bnodev": (("Y", "X2"), ["NEW", "POKE&H9000,0", 'BLOAD"X"'] + WAIT + PEEK, "peek"),
    "bscr": (("Y", "X2"), ["NEW", 'BLOAD"CAS:X"'] + WAIT + ['PRINT"[D]"'], "rows"),
    "lbin": (("X1", "A"), ["NEW", 'LOAD"CAS:X"'] + WAIT + ["LIST"], "list"),
    "cbin": (("X1", "T"), ["NEW", 'CLOAD"X"'] + WAIT + ["LIST"], "list"),
}


def tape(parts):
    path = probe_tmp.tmp(f"casbin_{'_'.join(parts)}.cas")
    open(path, "wb").write(b"".join(PARTS[p] for p in parts))
    return path


def reading(machine, name):
    parts, lines, how = CASES[name]
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), cassette=tape(parts))[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    errs = re.findall(r"Device I/O error|load error|[A-Z][a-z]+(?: [a-z/]+)* error", flat)
    if how == "peek":
        m = re.findall(r"\[P\s*(\d+)\s*\]", flat)
        return f"PEEK {m[-1]}" + (f" ({errs[-1]})" if errs else "") if m else (errs[-1] if errs else None)
    if how == "rows":
        rows = re.findall(r"(Skip :\s?\S+|Found:\s?\S+)", flat)
        return " | ".join(r.replace(" ", "") for r in rows) or (errs[-1] if errs else "no rows")
    tail = flat.split("LIST", 1)[1] if "LIST" in flat else ""
    got = re.findall(r"\b(10 END|20 STOP)\b", tail)
    return " + ".join(got) if got else (errs[-1] if errs else "nothing listed")


def main():
    only = sys.argv[1:] or list(CASES)
    got = {(t, n): reading(m, n) for t, m in (("VG-8020", REF), ("OURS", OURS)) for n in only}
    for n in only:
        print(f"== {n:5s} VG-8020 {got[('VG-8020', n)]!s:26s} ours {got[('OURS', n)]!s}")
    if any(got[("VG-8020", n)] is None for n in only):
        print("\nINSTRUMENT FAULT: the VG-8020 gave no reading -- no reference")
        return 2
    bad = [n for n in only if got[("VG-8020", n)] != got[("OURS", n)]]
    for n in bad:
        print(f"DIVERGES {n}: VG-8020 {got[('VG-8020', n)]} vs ours {got[('OURS', n)]}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: binary files in a tape search "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
