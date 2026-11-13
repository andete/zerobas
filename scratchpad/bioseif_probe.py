#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Does a BIOS entry called under DI return with interrupts ENABLED? The VG-8020 against
zerobas, for the entries Demonia's code calls in the last ~60 ms before it crashes
(scratchpad/demonia_trace5.out): a game that borrows SP as a copy pointer under DI dies if
a BIOS call re-enabled interrupts behind its back. Our own code: DI, harmless arguments,
call the entry, `ld a,i` (P/V = IFF2), store F; then EI, RET. BASIC prints P/V per entry
(1 = interrupts enabled on return). Black box: registers only.

    python3 -u scratchpad/bioseif_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
# name, address, A, BC, DE, HL -- arguments that touch only VRAM $3F00.. / nothing
ENTRIES = [("DCOMPR", 0x0020, 0, 0, 0x1234, 0x1234), ("RDVRM", 0x004A, 0, 0, 0, 0x3F00),
           ("WRTVRM", 0x004D, 0x55, 0, 0, 0x3F00), ("FILVRM", 0x0056, 0x55, 1, 0, 0x3F00),
           ("LDIRVM", 0x005C, 0, 1, 0x3F00, 0xC000), ("CALPAT", 0x0084, 1, 0, 0, 0),
           ("CALATR", 0x0087, 1, 0, 0, 0), ("SNSMAT", 0x0141, 6, 0, 0, 0),
           ("GTTRIG", 0x00D8, 0, 0, 0, 0), ("SETWRT", 0x0053, 0, 0, 0, 0x3F00),
           ("SETRD", 0x0050, 0, 0, 0, 0x3F00), ("RDVDP", 0x013E, 0, 0, 0, 0),
           ("WRTVDP", 0x0047, 0, 0x0701, 0, 0), ("GTSTCK", 0x00D5, 0, 0, 0, 0)]


def code():
    c = []
    for k, (_, addr, a, bc, de, hl) in enumerate(ENTRIES):
        c += [0xF3, 0x3E, a, 0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8,
              0x21, hl & 255, hl >> 8, 0xCD, addr & 255, addr >> 8,
              0xED, 0x57, 0xF5, 0xE1, 0x7D, 0x32, (0x00 + k) & 255, 0xD1]   # ld a,i / F -> $D100+k
    return c + [0xFB, 0xC9]


def main():
    c = code()
    prog = ["NEW", "10 CLEAR 200,&HBFFF", f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:Q=USR(0):S$=\"\"",
            f'40 FOR I=0 TO {len(ENTRIES) - 1}:S$=S$+STR$((PEEK(&HD100+I)\\4) AND 1):NEXT:PRINT "[E";S$;"]"',
            *[f"{50 + n} DATA " + ",".join(str(b) for b in c[i:i + 40])
              for n, i in enumerate(range(0, len(c), 40))], "RUN"]
    for side, m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", prog)], batch=False, reset=("", "SCREEN 0"),
                                  step=3.0, run_gap=10.0)[0] or ""
        f = re.findall(r"\[E([ \d]+)\]", re.sub(r"\s+", " ", raw))
        v = f[-1].split() if f else None
        print(side, " ".join(f"{n}={x}" for (n, *_), x in zip(ENTRIES, v)) if v else "<none>", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
