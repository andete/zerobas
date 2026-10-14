#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TAPLEAD (gate: tapionlead-acceptance): TAPION called while DATA is playing.

A machine-code tape loader calls the BIOS TAPION to lock onto the next file's
leader. When it does that while the previous file's data is still playing,
TAPION must skip the data and wait for a real leader. zerobas's TAPION accepted
any carrier without a silent gap: it locked onto the data in ~27 ms, derived a
long-half threshold from it, and the loader's next TAPIN failed. Five reported
titles share one loader that stopped there with its own `Load error` (found
2026-10-14 by D-TAPELOAD's triage; the tapes run outside the repo, never decoded).

The tape is OUR OWN, built per run with cas_encode: binary file A (200 payload
bytes) then binary file B. The routine, OUR OWN machine code POKEd from DATA and
run by USR, calls TAPION and reads A's 16-byte header, calls TAPION and reads K
bytes of A's 206-byte data block, then calls TAPION AGAIN and reads one byte --
B's header byte, $D0 = 208 -- storing A and both carries:
  `mid`  K = 8: the third TAPION runs while A's data is still playing.
  `end`  K = 206: the whole block first -- the control.
Each row prints `ROW <name> VG=[...] ZB=[...] <verdict>`.
Exit 0 as pinned; 1 an unpinned divergence or a rotted pin; 2 the VG-8020
gave no reading.
Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402

TAPE = build_cas("A", 0xD200, 0xD200, bytes(range(200))) + \
       build_cas("B", 0xD200, 0xD200, bytes([0xC9]))


def routine(k):
    return bytes([
        0xCD, 0xE1, 0x00,        # call TAPION        (A's header leader)
        0x06, 0x10,              # ld b,16
        0xC5,                    # push bc
        0xCD, 0xE4, 0x00,        # call TAPIN         (A's 16-byte header)
        0xC1,                    # pop bc
        0x10, 0xF9,              # djnz -7
        0xCD, 0xE1, 0x00,        # call TAPION        (A's data-block leader)
        0x06, k & 0xFF,          # ld b,K
        0xC5,                    # push bc
        0xCD, 0xE4, 0x00,        # call TAPIN         (K bytes of A's data)
        0xC1,                    # pop bc
        0x10, 0xF9,              # djnz -7
        0xCD, 0xE1, 0x00,        # call TAPION        (must find B's leader)
        0x9F,                    # sbc a,a            ($FF if it failed)
        0x32, 0x01, 0xD1,        # ld (&HD101),a
        0xCD, 0xE4, 0x00,        # call TAPIN         (B's first header byte)
        0x32, 0x00, 0xD1,        # ld (&HD100),a
        0x9F,                    # sbc a,a
        0x32, 0x02, 0xD1,        # ld (&HD102),a
        0xCD, 0xE7, 0x00,        # call TAPIOF
        0xC9,                    # ret
    ])


def program(k):
    code = routine(k)
    data = ",".join(str(b) for b in code)
    return ["NEW",
            f"10 FOR I=0 TO {len(code) - 1}:READ A:POKE &HD000+I,A:NEXT",
            '20 DEFUSR=&HD000:X=USR(0):PRINT"[";PEEK(&HD100);PEEK(&HD101);PEEK(&HD102);"]"',
            f"30 DATA {data[:200]}"] + ([f"40 DATA {data[201:]}"] if len(data) > 200 else []) + ["RUN"]


CASES = {"mid": 8, "k190": 190, "k200": 200, "k204": 204, "end": 206}
# ⚠️ RESIDUAL, PINNED (2026-10-14): `mid` -- a TAPION started DEEP in data can
# measure a run of LONG halves (zero bits) as its "short", and then every half
# classifies short and the verify passes on data (LOWLIM read 41 against a
# leader's 21: scratchpad/taplead_lowlim.out). A lower bound would catch it, but
# at these counts (~3 per half at 1200 baud, ~1.5 at 2400) one would also reject
# real 2400-baud leaders. The rows near the END of a block are the reported
# loaders' case and are fixed. A pinned row that starts agreeing is a ROTTED pin.
KNOWN_DIVERGE = {"mid"}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    keep = [x for x in r if x.startswith("[") or "error" in x.lower()]
    return " | ".join(keep)


def main():
    only = sys.argv[1:] or list(CASES)
    tmp = tempfile.mkdtemp(prefix="tapionlead_")
    path = os.path.join(tmp, "ab.cas")
    open(path, "wb").write(TAPE)
    bad, blind = [], []
    for name in only:
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = rows(omsx_repl.run_cases(m, [("direct", program(CASES[name]))], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=40.0, cassette=path)[0])
        if not got["VG"]:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME (PIN ROTTED)" if name in KNOWN_DIVERGE else "SAME"
            if name in KNOWN_DIVERGE:
                bad.append(name)
        else:
            verdict = "DIVERGES (pinned)" if name in KNOWN_DIVERGE else "DIVERGES"
            if name not in KNOWN_DIVERGE:
                bad.append(name)
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: TAPION called while data is playing "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
