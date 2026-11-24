#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""RAMREC -- the shared RAM-record harness of the keyword spec probes (docs/keywords/spec-plan.md §3, the "RAM record"
row; §7 item 2). Extracted from probes/basic/spec/kslice.py when the second probe (kstr.py) arrived; kslice's
program text, run file and decoded cases are byte-identical through it.

Clean room: typed BASIC in, RAM out. A probe's program is TYPED; it evaluates each case and POKEs a fixed-size record
per case from $C001 (above CLEAR's limit). $C000 is the done flag ($5A, written last); an end byte ($C3) follows the
last record. The harness captures RAM when the program raises the flag (omsx_repl's sentinel capture), and `frame`
refuses a capture without both the flag and the end byte. Values are read through VARPTR + PEEK, never through a
string function.

What a probe takes from here:
  head(clear)        line 10: CLEAR, DEFDBL A-Z / DEFINT I-K, ON ERROR GOTO 800, the flag cleared, A = $C001
  TAIL               the end byte, then the done flag, then END
  ERRLINE            800: E = ERR, RESUME NEXT
  STR_DIGEST         950-970: the string whose descriptor is at V -> RL (length), FB / LB (first / last byte), S (sum
                     of the bytes), W (sum of k * byte k, k from 1, mod 65536). Uses P, K, X.
  data(n0, values)   DATA lines, <= 8 values each
  measure(...)       run the typed lines on the reference and on zerobas, capture the record area
  frame(hex, n, rec) the n records' bytes, or (None, why)
  digest(b)          (RL, FB, LB, S, W) of a byte string, as STR_DIGEST computes it
  number(b)          the value of a BASIC number's own bytes (2: integer, 4: single, 8: double), exactly
  read_section / write_section   a run file's "===== GROUP" sections
"""
import os
import re
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
BASE = 0xC000
DONE, END = 0x5A, 0xC3

STR_DIGEST = [
    "950 RL=PEEK(V):P=PEEK(V+1)+256*PEEK(V+2):S=0:W=0:FB=0:LB=0:IF RL=0 THEN RETURN",
    "960 FB=PEEK(P):LB=PEEK(P+RL-1):FOR K=0 TO RL-1:X=PEEK(P+K):S=S+X:W=W+(K+1)*X:NEXT",
    "970 W=W-INT(W/65536!)*65536!:RETURN",
]
ERRLINE = "800 E=ERR:RESUME NEXT"
TAIL = "POKE A,&HC3:POKE &HC000,&H5A:END"


def head(clear=2000):
    """clear=None: no CLEAR at all -- the string space a program starts with (the record area is then unreserved
    free RAM between the variables and the stack; kstr's OSD group)"""
    if clear is None:
        return "10 DEFDBL A-Z:DEFINT I-K:ON ERROR GOTO 800:POKE &HC000,0:A=&HC001"
    return f"10 CLEAR {clear},&HC000:DEFDBL A-Z:DEFINT I-K:ON ERROR GOTO 800:POKE &HC000,0:A=&HC001"


def data(n0, values):
    """DATA lines from line n0, <= 8 values each"""
    out = []
    for i in range(0, len(values), 8):
        out.append(f"{n0 + i // 8} DATA " + ",".join(values[i:i + 8]))
    return out


DISK_REF, DISK_ZB = "National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"
DISK_TOP = 0xDE00          # a disk machine's records end below the disk ROM's claimed RAM (HIMEM $DE77 on both)


def measure(lines, n, rec, gap, machines=(("ref", REF), ("zb", ZB)), disk=False):
    """type `lines` (a numbered program ending in RUN) on each machine; {who: hex of the record area, or None}.
    disk=True: Disk BASIC machines, each booted with its own copy of disk/test720.dsk in drive A (as
    scratchpad/kwdoc_examples.py boots them)"""
    import omsx_repl
    import shutil
    import probe_tmp
    size = 1 + rec * n + 1
    if disk:
        assert BASE + size <= DISK_TOP, f"the records run past ${DISK_TOP:04X} (the disk ROM's RAM)"
    out = {}
    for who, machine in machines:
        kw = {}
        if disk:
            dsk = probe_tmp.tmp(f"ramrec_{machine}.dsk")
            shutil.copyfile(os.path.join(ROOT, "disk", "test720.dsk"), dsk)
            kw = dict(diska=dsk, boot=14.0)
        out[who] = omsx_repl.run_cases(machine, [("direct", lines)], batch=False, reset=("", "SCREEN 0:WIDTH 40"),
                                       step=1.0, run_gap=gap, capture=("mem_abs", [(BASE, size)]),
                                       sentinel=(BASE, DONE), sentinel_capture=True, **kw)[0]
    return out


def frame(hexs, n, rec):
    """the n records (bytes each) of a capture, or (None, why) without the done flag and the end byte"""
    if hexs is None:
        return None, "no capture"
    b = bytes.fromhex(hexs)
    if len(b) < 2 + rec * n or b[0] != DONE or b[1 + rec * n] != END:
        return None, f"incomplete (done flag {b[:1].hex()}, {len(b)} bytes, end byte " \
                     f"{b[1 + rec * n]:02x})" if len(b) > 1 + rec * n else f"short ({len(b)} bytes)"
    return [b[1 + rec * i:1 + rec * (i + 1)] for i in range(n)], None


def digest(b):
    """(RL, FB, LB, S, W) as STR_DIGEST records them for the string b"""
    if not b:
        return 0, 0, 0, 0, 0
    return len(b), b[0], b[-1], sum(b) & 0xFFFF, sum((k + 1) * x for k, x in enumerate(b)) & 0xFFFF


def number(b):
    """a BASIC number's value from its own bytes (VARPTR's), exactly: 2 bytes an integer (LE, signed); 4 / 8 bytes a
    single / double -- byte 0 the sign (bit 7) and the exponent (excess 64; 0: the value is 0), then 6 / 14 BCD digits,
    the value 0.d1d2... * 10^(exponent - 64). A BCD nibble above 9 raises ValueError (not a number)."""
    if len(b) == 2:
        v = b[0] | b[1] << 8
        return v - 65536 if v & 0x8000 else v
    if b[0] & 0x7F == 0:
        return Fraction(0)
    m = 0
    for x in b[1:]:
        hi, lo = x >> 4, x & 15
        if hi > 9 or lo > 9:
            raise ValueError(f"not BCD: {b.hex()}")
        m = m * 100 + hi * 10 + lo
    v = Fraction(m, 10 ** (2 * (len(b) - 1))) * Fraction(10) ** ((b[0] & 0x7F) - 64)
    return -v if b[0] & 0x80 else v


def read_section(path, group):
    """{"ref": hex, "zb": hex} of a run file's complete section, or exits"""
    text = open(path).read()
    m = re.search(rf"^===== {group}\n  CAP ref : (\w+)\n  CAP zb  : (\w+)$", text, re.M)
    if not m:
        sys.exit(f"FAIL: {os.path.basename(path)} has no complete {group} section")
    return {"ref": m.group(1), "zb": m.group(2)}


def write_section(text, group, cap, n, bad, machines=(REF, ZB)):
    """the run file's text with group's section replaced (appended at the end)"""
    sec = (f"===== {group}\n  CAP ref : {cap['ref'] or 'NONE'}\n  CAP zb  : {cap['zb'] or 'NONE'}\n"
           f"  ({n} cases; machines {machines[0]} / {machines[1]}; {'; '.join(bad) or 'both complete'})\n")
    return re.sub(rf"^===== {group}\n.*?(?=^===== |\Z)", "", text, flags=re.M | re.S) + sec
