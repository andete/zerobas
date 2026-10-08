#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FCBHDR (D-FCBSHAPE's left-over, TIER 4): the FCB header bytes a program
can PEEK through VARPTR(#n) -- the MODE at +0, the DEVICE at +4, the buffer
POSITION at +6 -- against the reference that owns the device.

scratchpad/fcbfields_probe.py measured the layout on the references only
(VG-8020 CRT: `02 .. .. .. FD .. 00`, CF-3300 disk OUTPUT `02 .. .. .. 01 ..
00 -> 02 -> 03`); ours read 255 at +0 (varptrch_run.out `hdr`). The other
header bytes are a pointer into the disk work area (+1/+2) or whatever RAM
held: not compared. Clean room: work-area RAM contents through PEEK.

  diskless VG-8020 vs ours (NODISK):
    crt     OPEN"CRT:" FOR OUTPUT
    lpt     OPEN"LPT:" FOR OUTPUT
    casout  OPEN"CAS:T" FOR OUTPUT              (writes the header to a blank tape)
    casin   OPEN"CAS:D" FOR INPUT              (an ASCII tape, cas_encode)
  CF-3300 vs ours (DISK), on test720 (HI.TXT is 26 B):
    dout    OPEN"N.TXT" FOR OUTPUT, then PRINT#1,"AB";  (+6 before / after)
    din     OPEN"HI.TXT" FOR INPUT                 (the header at OPEN only: the
            moving position is filed -- the CF-3300 reads 0 0 1 2 3 4 5 over the
            first six INPUT$(1,1)s, the last byte's index, and ours does not keep it)
    dina    OPEN"A:HI.TXT" FOR INPUT               (the device is the drive AS TYPED)
    dapp    OPEN"HI.TXT" FOR APPEND
    drnd    OPEN"R.DAT" AS #1 LEN=32

Each row prints `<m,d,p>` (decimal) once, or twice for the before/after rows.
Exit 0 all agree; 1 a divergence; 2 a reference gave no reading.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402
import probe_tmp                                   # noqa: E402

VG, CF = "Philips_VG_8020", "National_CF-3300"
OURS_ND = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
OURS_D = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
HDR = 'F=VARPTR(#1):PRINT"<";PEEK(F);",";PEEK(F+4);",";PEEK(F+6);">"'
# name -> (diskless?, lines)
CASES = {
    "crt": (True, ['OPEN"CRT:" FOR OUTPUT AS #1', HDR, "CLOSE"]),
    "lpt": (True, ['OPEN"LPT:" FOR OUTPUT AS #1', HDR, "CLOSE"]),
    "casout": (True, ['OPEN"CAS:T" FOR OUTPUT AS #1', "@WAIT6", HDR]),
    "casin": (True, ['OPEN"CAS:D" FOR INPUT AS #1', "@WAIT12", HDR]),
    "dout": (False, ['OPEN"N.TXT" FOR OUTPUT AS #1', HDR, 'PRINT#1,"AB";', HDR, "CLOSE"]),
    "din": (False, ['OPEN"HI.TXT" FOR INPUT AS #1', HDR, "CLOSE"]),
    "dina": (False, ['OPEN"A:HI.TXT" FOR INPUT AS #1', HDR, "CLOSE"]),
    "dapp": (False, ['OPEN"HI.TXT" FOR APPEND AS #1', HDR, "CLOSE"]),
    "drnd": (False, ['OPEN"R.DAT" AS #1 LEN=32', HDR, "CLOSE"]),
}
NOPOS = ("crt", "lpt")     # their +6 is leftover RAM on the reference (255 here,
                          # 0 in fcbfields_probe.py): mode and device only
RX = re.compile(r"<\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*>")


def reading(machine, name):
    diskless, lines = CASES[name]
    kw = dict(batch=False, reset=("", "SCREEN 0"))
    if diskless:
        cas = probe_tmp.tmp("fcbhdr.cas")
        open(cas, "wb").write(cas_encode.build_cas_ascii("D", "HELLO\nWORLD\n"))
        kw["cassette"] = cas
    else:
        dsk = probe_tmp.tmp(f"fcbhdr_{name}_{machine[:6]}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        kw.update(diska=dsk, boot=14.0, step=3.0)
    raw = omsx_repl.run_cases(machine, [("direct", ["MAXFILES=1"] + lines)], **kw)[0] or ""
    got = RX.findall(re.sub(r"\s+", " ", raw))
    if name in NOPOS:
        return " ".join(f"{m}/{d}/-" for m, d, p in got) or None
    return " ".join(f"{m}/{d}/{p}" for m, d, p in got) or None


def main():
    only = sys.argv[1:] or list(CASES)
    rows = {}
    for n in only:
        ref, ours = (VG, OURS_ND) if CASES[n][0] else (CF, OURS_D)
        rows[n] = (ref.split("_")[-1], reading(ref, n), reading(ours, n))
    for n, (rn, r, o) in rows.items():
        print(f"== {n:6s} {rn:8s} {r!s:18s} ours {o!s}")
    if any(r is None for _, r, _ in rows.values()):
        print("\nINSTRUMENT FAULT: a reference gave no reading")
        return 2
    bad = [n for n, (_, r, o) in rows.items() if r != o]
    for n in bad:
        print(f"DIVERGES {n}: {rows[n][1]} vs ours {rows[n][2]}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: the FCB header's mode / device / position "
          f"({len(rows) - len(bad)}/{len(rows)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
