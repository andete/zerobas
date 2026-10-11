#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SUBSIG: zerobas's sub ROM carries its own "ZB" marker (Joost, 2026-10-11),
not the MSX2 SUB-ROM's "CD", and boot no longer writes EXBRSA ($FAF8).

  faf8   PEEK(&HFAF8) / PEEK(&HFAF9) after boot -- both MSX1 references leave
         them 0 (scratchpad/subsig_probe.out); ours wrote the sub-ROM slot, 139
  p1     SQR(16): a PAGE-1 sub-ROM tenant (fp_sqrt) -- found and callable
  p0     an array store and read: the PAGE-0 array engine (ary_engine)

p1 / p0 are the controls that make faf8 mean something: a boot scan that no
longer finds the ROM leaves $FAF8 0 too, and THEY then fail (no tenant).
The diskless build is compared with the VG-8020, the disk build with the CF-3300.

Exit 0 all agree; 1 a divergence; 2 a reference gave no reading.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

PAIRS = (("VG-8020", "Philips_VG_8020",
          os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")),
         ("CF-3300", "National_CF-3300",
          os.environ.get("ZEROBAS_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")))
CASES = {
    "faf8": 'PRINT"[R";PEEK(&HFAF8);PEEK(&HFAF9);"]"',
    "p1": 'PRINT"[R";SQR(16);"]"',
    "p0": 'DIM Q(5):Q(3)=7:PRINT"[R";Q(3);"]"',
}
RX = re.compile(r"\[R\s*([^\]]*?)\s*\]")


def reading(machine):
    raw = omsx_repl.run_cases(machine, [("direct", ["NEW", CASES[n]]) for n in CASES],
                              batch=False, reset=("", "SCREEN 0"))
    out = {}
    for n, r in zip(CASES, raw):
        m = RX.findall(re.sub(r"\s+", " ", r or ""))
        out[n] = re.sub(r"\s+", " ", m[-1]) if m else None
    return out


def main():
    bad, fault = [], False
    for ref, rm, zm in PAIRS:
        a, b = reading(rm), reading(zm)
        for n in CASES:
            print(f"ROW {n:5s} {ref} [{a[n]}] zerobas[{b[n]}] "
                  f"{'SAME' if a[n] == b[n] else 'DIVERGES'}")
            fault |= a[n] is None
            if a[n] != b[n]:
                bad.append(f"{ref}:{n}")
    if fault:
        print("\nINSTRUMENT FAULT: a reference gave no reading")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: the sub-ROM marker and EXBRSA "
          f"({2 * len(CASES) - len(bad)}/{2 * len(CASES)})" + (f" -- {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
