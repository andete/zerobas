#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TAPEBIOS: the six cassette BIOS entries called DIRECTLY -- the VG-8020 against zerobas.

TAPION $00E1, TAPIN $00E4, TAPIOF $00E7, TAPOON $00EA, TAPOUT $00ED, TAPOOF $00F0 had no
gate that calls them (docs/tier-status.md: NOT MEASURED); the probes/tape/ carts measure
our own write -> read loop on an older machine, against no reference. Joost (2026-11-13):
"the tape ones we should definitely cover with tests". Our own code, in BASIC-POKEd
machine code (USR), on each machine:

  write  TAPOON (A = 1, a long header), TAPOUT x 64 of our own pattern, TAPOOF -- openMSX
         records the CAS-out signal; probes/lib/cas_decode.py turns each WAV back into
         bytes. Compared: the decoded bytes (the pattern, exactly), and Cy after TAPOON,
         after the last TAPOUT and after TAPOOF, plus how many TAPOUTs ran.
  read   the VG-8020's OWN write recording played into both: TAPION, TAPIN x 64, TAPIOF.
         Compared: Cy after TAPION / any TAPIN / TAPIOF, and the 64 bytes read.
  cas    a .cas of our own (openMSX plays it at 3744 baud, the VG-8020's fastest) read
         as BLOAD reads it: TAPION, the header, TAPION again, the data -- every byte exact.
  break  no tape: TAPION, Ctrl-STOP pressed while it waits -- Cy, INTFLG, an ON STOP trap
         and whether the key is still down when TAPION returns (SNSMAT row 7).
  wbreak a long TAPOUT run (1500 bytes) broken with Ctrl-STOP in its data -- the same.
  rbreak a long TAPIN run over the VG-8020's own 1500-byte recording, broken -- the same.

Registers other than Cy are stored and printed, not compared (no published contract).
Black box: our own code and bytes, the recorded signal; nothing of the reference is read.

    python3 -u probes/tape/bios_probe_tapdiff.py [write|read|cas|break|wbreak|rbreak ...]

Exit 0 all agree; 1 a divergence; 2 the reference gave no reading.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
from cas_decode import decode_file                 # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
N = 64
# the published cassette entries (and the two helpers the break rows use)
TAPION, TAPIN, TAPIOF, TAPOON, TAPOUT, TAPOOF = 0x00E1, 0x00E4, 0x00E7, 0x00EA, 0x00ED, 0x00F0
SNSMAT, INTFLG = 0x0141, 0xFC9B


def call(addr):
    return [0xCD, addr & 255, addr >> 8]


PAT = [((i * 53) + 0x1F) & 0xFF for i in range(N)]

# write: TAPOON A=1; AF -> $D200. TAPOUT each byte of $D100.. (stop on Cy); AF -> $D202,
# B (TAPOUTs left) -> $D204. TAPOOF; AF -> $D206. EI, RET. (`push af / pop hl`: L = F.)
WRITE = [0x3E, 0x01, *call(TAPOON), 0xF5, 0xE1, 0x22, 0x00, 0xD2,
         0x21, 0x00, 0xD1, 0x06, N,
         0x7E, 0xE5, 0xC5, *call(TAPOUT), 0xC1, 0xE1, 0x38, 0x03, 0x23, 0x10, 0xF3,
         0xF5, 0xE1, 0x22, 0x02, 0xD2, 0x78, 0x32, 0x04, 0xD2,
         *call(TAPOOF), 0xF5, 0xE1, 0x22, 0x06, 0xD2, 0xFB, 0xC9]
# read: TAPION; AF -> $D200 (Cy: straight to the close). TAPIN x N into $D300.. (stop on
# Cy); AF -> $D202, B -> $D204. TAPIOF; AF -> $D206. EI, RET.
READ = [*call(TAPION), 0xF5, 0xE1, 0x22, 0x00, 0xD2, 0x38, 0x12,
        0x21, 0x00, 0xD3, 0x06, N,
        0xE5, 0xC5, *call(TAPIN), 0xC1, 0xE1, 0x38, 0x04, 0x77, 0x23, 0x10, 0xF3,
        0xF5, 0xE1, 0x22, 0x02, 0xD2, 0x78, 0x32, 0x04, 0xD2,
        *call(TAPIOF), 0xF5, 0xE1, 0x22, 0x06, 0xD2, 0xFB, 0xC9]


def _rel(code, at):
    """The target index of the relative jump whose opcode is at `at`."""
    d = code[at + 1]
    return at + 2 + (d - 256 if d > 127 else d)


# every relative jump checked against the layout it is meant to reach
assert _rel(WRITE, 23) == 28 and _rel(WRITE, 26) == 15 and WRITE[15] == 0x7E
assert _rel(READ, 8) == 28 and _rel(READ, 22) == 28 and _rel(READ, 26) == 15
assert READ[15] == 0xE5 and READ[28] == WRITE[28] == 0xF5

# break: READ with INTFLG ($FC9B, the STOP / CTRL-STOP flag the interrupt handler sets)
# stored at $D208 after TAPIOF, before interrupts come back on
# and SNSMAT(7) ($0141, A = 7: bit 4 = STOP, 0 = held) the moment TAPION returns -> $D209
BREAKC = [*call(TAPION), 0xF5, 0xE1, 0x22, 0x00, 0xD2,      # TAPION; AF -> $D200
          0x3E, 0x07, *call(SNSMAT), 0x32, 0x09, 0xD2,      # SNSMAT(7) -> $D209
          *call(TAPIOF),                                    # TAPIOF
          0x3A, INTFLG & 255, INTFLG >> 8, 0x32, 0x08, 0xD2, 0xFB, 0xC9]      # INTFLG -> $D208; EI; RET

def asm(items):
    """A tiny two-pass assembler: bytes, ("L", name) a label, ("jr", cond, name) /
    ("djnz", name) a relative jump (cond None or one of nz z nc c)."""
    ops = {None: 0x18, "nz": 0x20, "z": 0x28, "nc": 0x30, "c": 0x38}
    for final in (False, True):
        out, lab = [], {} if not final else lab
        for it in items:
            if isinstance(it, tuple) and it[0] == "L":
                lab[it[1]] = len(out)
            elif isinstance(it, tuple) and it[0] in ("jr", "djnz"):
                op = 0x10 if it[0] == "djnz" else ops[it[1]]
                tgt = lab.get(it[-1], len(out) + 2) if final else len(out) + 2
                d = tgt - (len(out) + 2)
                assert -128 <= d <= 127, it
                out += [op, d & 0xFF]
            else:
                out += list(it) if isinstance(it, (list, tuple)) else [it]
    return out


LONG = 1500     # bytes: ~13 s of 1200-baud data, long enough to land a press in it
# the long write: TAPOON; TAPOUT of LONG bytes of $C000.. (RAM, whatever it holds) until
# Cy; AF -> $D202, BC (left) -> $D204; SNSMAT(7) -> $D209; TAPOOF; INTFLG -> $D208
WLONG = asm([0x3E, 0x01, *call(TAPOON), 0xF5, 0xE1, 0x22, 0x00, 0xD2,
             0x21, 0x00, 0xC0, 0x01, LONG & 255, LONG >> 8,
             ("L", "lp"), 0x7E, 0xE5, 0xC5, *call(TAPOUT), 0xC1, 0xE1, ("jr", "c", "out"),
             0x23, 0x0B, 0x78, 0xB1, ("jr", "nz", "lp"),
             ("L", "out"), 0xF5, 0xE1, 0x22, 0x02, 0xD2, 0xED, 0x43, 0x04, 0xD2,
             0x3E, 0x07, *call(SNSMAT), 0x32, 0x09, 0xD2,
             *call(TAPOOF), 0x3A, INTFLG & 255, INTFLG >> 8, 0x32, 0x08, 0xD2, 0xFB, 0xC9])
# the long read: TAPION (Cy -> out); TAPIN x LONG into $9000.. until Cy; then as WLONG
# but TAPIOF
RLONG = asm([*call(TAPION), 0xF5, 0xE1, 0x22, 0x00, 0xD2, 0x01, LONG & 255, LONG >> 8,
             ("jr", "c", "out"), 0x21, 0x00, 0x90,
             ("L", "lp"), 0xE5, 0xC5, *call(TAPIN), 0xC1, 0xE1, ("jr", "c", "out"),
             0x77, 0x23, 0x0B, 0x78, 0xB1, ("jr", "nz", "lp"),
             ("L", "out"), 0xF5, 0xE1, 0x22, 0x02, 0xD2, 0xED, 0x43, 0x04, 0xD2,
             0x3E, 0x07, *call(SNSMAT), 0x32, 0x09, 0xD2,
             *call(TAPIOF), 0x3A, INTFLG & 255, INTFLG >> 8, 0x32, 0x08, 0xD2, 0xFB, 0xC9])
assert WLONG[16] == 0x7E and RLONG[16] == 0xE5   # the loop heads

# cas: a .cas of our own, which openMSX plays at 3744 baud -- the fastest the VG-8020
# decodes, so TAPION's threshold and TAPIN's bit timing have no slack (Joost 2026-11-13).
# A BSAVE-shaped file (cas_encode.build_cas): the header block (10 x $D0 + the name, 16
# bytes) and the data block (start / end / exec + CASN bytes) -- every byte value, then
# long runs of 0-bits and 1-bits, then alternating ones. Read as BLOAD reads it: TAPION,
# 16 x TAPIN, TAPION again (the relock between blocks), 6 + CASN x TAPIN, TAPIOF.
CASN = 512
CASDATA = bytes(range(256)) + bytes(64) + b"\xff" * 64 + b"\x55\xaa" * 64
assert len(CASDATA) == CASN
CASRD = asm([*call(TAPION), 0xF5, 0xE1, 0x22, 0x00, 0xD2, ("jr", "c", "out"),
             0x21, 0x00, 0x90, 0x06, 16,
             ("L", "h"), 0xE5, 0xC5, *call(TAPIN), 0xC1, 0xE1, ("jr", "c", "out"),
             0x77, 0x23, ("djnz", "h"),
             0xE5, *call(TAPION), 0xF5, 0xD1, 0xED, 0x53, 0x0A, 0xD2, 0xE1, ("jr", "c", "out"),
             0x01, (6 + CASN) & 255, (6 + CASN) >> 8,
             ("L", "d"), 0xE5, 0xC5, *call(TAPIN), 0xC1, 0xE1, ("jr", "c", "out"),
             0x77, 0x23, 0x0B, 0x78, 0xB1, ("jr", "nz", "d"),
             ("L", "out"), 0x22, 0x0C, 0xD2, 0xF5, 0xE1, 0x22, 0x02, 0xD2,
             *call(TAPIOF), 0xFB, 0xC9])
RXC = re.compile(r"\[C((?:\s+-?\d+){5})\s*\]")


def cas_want():
    """(the bytes TAPIN must return, their weighted sum as the BASIC side computes it)."""
    import cas_encode
    blob = cas_encode.build_cas("ZBCAS", 0xA000, 0xA000, CASDATA)
    sync = bytes([0x1F, 0xA6, 0xDE, 0xBA, 0xCC, 0x13, 0x7D, 0x74])
    blocks = [b for b in blob.split(sync) if b]
    want = blocks[0][:16] + blocks[1][:6 + CASN]
    return blob, want, sum(b * (i % 251 + 1) for i, b in enumerate(want))


def cas_row(machine, casfile):
    """[C Cy-TAPION1 Cy-TAPION2 Cy-end bytes-read sum]."""
    lines = ["NEW", "10 CLEAR 200,&H8FFF",
             f"20 FOR I=0 TO {len(CASRD) - 1}:READ X:POKE &HD000+I,X:NEXT",
             "30 FOR I=&HD200 TO &HD20D:POKE I,255:NEXT:DEFUSR=&HD000:Q=USR(0)",
             "40 P=PEEK(&HD20C)+256*PEEK(&HD20D)-36864:S=0:IF P<0 OR P>1000 THEN P=-1:GOTO 50",
             "45 FOR I=0 TO P-1:S=S+PEEK(&H9000+I)*(I MOD 251+1):NEXT",
             '50 PRINT "[C";PEEK(&HD200) AND 1;PEEK(&HD20A) AND 1;PEEK(&HD202) AND 1;P;S;"]"',
             "60 DATA " + ",".join(str(b) for b in CASRD), "RUN"]
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"),
                              prologue=(f"cassetteplayer insert {{{casfile}}}",),
                              step=3.0, run_gap=30.0, timeout=600.0)[0] or ""
    m = RXC.findall(re.sub(r"\s+", " ", raw))
    return tuple(int(x) for x in m[-1].split()) if m else None


RXL = re.compile(r"\[L((?:\s+-?\d+){6})\s*\]")


def long_row(machine, code, prologue, tail):
    """[L Cy-open Cy-loop left STOP-up INTFLG trapped] (an ON STOP trap, as break_row)."""
    lines = ["NEW", "5 Z=0:ON STOP GOSUB 90:STOP ON", "10 CLEAR 200,&H8FFF",
             f"20 FOR I=0 TO {len(code) - 1}:READ X:POKE &HD000+I,X:NEXT",
             "30 FOR I=&HD200 TO &HD209:POKE I,255:NEXT:DEFUSR=&HD000:Q=USR(0)",
             "40 FOR I=1 TO 50:NEXT",
             '50 PRINT "[L";PEEK(&HD200) AND 1;PEEK(&HD202) AND 1;PEEK(&HD204)+256*PEEK(&HD205);'
             'PEEK(&HD209) AND 16;PEEK(&HD208);Z;"]":END',
             "60 DATA " + ",".join(str(b) for b in code),
             "90 Z=Z+1:RETURN", "RUN"] + tail
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), prologue=prologue,
                              step=3.0, run_gap=40.0, timeout=600.0)[0] or ""
    m = RXL.findall(re.sub(r"\s+", " ", raw))
    return tuple(int(x) for x in m[-1].split()) if m else None


# [T F1 A1 F2 A2 left F3 A3 sum] -- every byte in decimal
SHOW = ('PRINT "[T";PEEK(&HD200);PEEK(&HD201);PEEK(&HD202);PEEK(&HD203);PEEK(&HD204);'
        'PEEK(&HD206);PEEK(&HD207);S;"]"')


def prog(code, data=None, read=False):
    p = ["NEW", "10 CLEAR 200,&HCFFF",
         f"20 FOR I=0 TO {len(code) - 1}:READ X:POKE &HD000+I,X:NEXT"]
    if data:
        p.append(f"25 FOR I=0 TO {len(data) - 1}:READ X:POKE &HD100+I,X:NEXT")
    p += ["30 FOR I=&HD200 TO &HD207:POKE I,255:NEXT:DEFUSR=&HD000:Q=USR(0):S=0",
          f"40 FOR I=0 TO {N - 1}:S=S+PEEK(&HD300+I)*(I+1):NEXT" if read else "40 S=0",
          "50 " + SHOW,
          "60 DATA " + ",".join(str(b) for b in code)]
    if data:
        p.append("70 DATA " + ",".join(str(b) for b in data))
    return p + ["RUN"]


RX = re.compile(r"\[T((?:\s+-?\d+){8})\s*\]")


def _run(machine, lines, prologue=()):
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), prologue=prologue,
                              step=3.0, run_gap=25.0, timeout=420.0)[0] or ""
    m = RX.findall(re.sub(r"\s+", " ", raw))
    return [int(x) for x in m[-1].split()] if m else None


def key(t):
    """The compared part: Cy after the open, Cy after the loop, calls left, Cy after
    the close, the read sum."""
    return None if t is None else (t[0] & 1, t[2] & 1, t[4], t[5] & 1, t[7])


def write_row(side, machine):
    wav = probe_tmp.tmp(f"tapdiff_w_{side}.wav")
    if os.path.exists(wav):
        os.remove(wav)
    t = _run(machine, prog(WRITE, PAT), prologue=(f"cassetteplayer new {{{wav}}}",))
    data, _info = decode_file(wav) if os.path.exists(wav) else ([], {})
    return t, list(data), wav


def read_row(machine, wav):
    return _run(machine, prog(READ, read=True), prologue=(f"cassetteplayer insert {{{wav}}}",))


RXB = re.compile(r"\[B\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\]")


def break_row(machine):
    """TAPION with no tape, Ctrl-STOP pressed while it waits. An ON STOP trap lets the
    program reach its PRINT on both. [B Cy-after-TAPION INTFLG-after-TAPIOF trapped
    STOP-key-up-at-return (16 = released, 0 = still held)]."""
    lines = ["NEW", "5 Z=0:ON STOP GOSUB 90:STOP ON", "10 CLEAR 200,&HCFFF",
             f"20 FOR I=0 TO {len(BREAKC) - 1}:READ X:POKE &HD000+I,X:NEXT",
             "30 POKE &HD208,255:POKE &HD209,255:DEFUSR=&HD000:Q=USR(0)",
             "40 FOR I=1 TO 50:NEXT",
             '50 PRINT "[B";PEEK(&HD200) AND 1;PEEK(&HD208);Z;PEEK(&HD209) AND 16;"]":END',
             "60 DATA " + ",".join(str(b) for b in BREAKC),
             "90 Z=Z+1:RETURN", "RUN", "@WAIT6", "@BREAK", "@WAIT6"]
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), prologue=("cassetteplayer eject",),
                              step=3.0, run_gap=25.0, timeout=420.0)[0] or ""
    m = RXB.findall(re.sub(r"\s+", " ", raw))
    return tuple(int(x) for x in m[-1]) if m else None


def main():
    rows = sys.argv[1:] or ["write", "read", "cas", "break", "wbreak", "rbreak"]
    bad = blind = 0
    ref_wav = None
    want_sum = sum(b * (i + 1) for i, b in enumerate(PAT))
    if "write" in rows or "read" in rows:
        w = {side: write_row(side, m) for side, m in (("VG", REF), ("ZB", OURS))}
        ref_wav = w["VG"][2]
        for side in ("VG", "ZB"):
            t, data, _ = w[side]
            print(f"WRITE {side}: [T {t}] key {key(t)}  decoded {len(data)} B, "
                  f"pattern {'FOUND' if bytes(PAT) in bytes(data) else 'absent'}", flush=True)
        if "write" in rows:
            if not w["VG"][0] or bytes(PAT) not in bytes(w["VG"][1]):
                blind += 1
                print("ROW write NO-REFERENCE (the VG-8020's write did not decode to the pattern)")
            else:
                same = key(w["ZB"][0]) == key(w["VG"][0]) and bytes(PAT) in bytes(w["ZB"][1])
                bad += not same
                print(f"ROW write {'SAME' if same else 'DIVERGES'}")
    if "read" in rows:
        if not ref_wav or not os.path.exists(ref_wav):
            blind += 1
            print("ROW read NO-REFERENCE (no VG-8020 recording)")
        else:
            r = {side: read_row(m, ref_wav) for side, m in (("VG", REF), ("ZB", OURS))}
            for side in ("VG", "ZB"):
                print(f"READ {side}: [T {r[side]}] key {key(r[side])}  "
                      f"(want left 0, sum {want_sum})", flush=True)
            if not r["VG"]:
                blind += 1
                print("ROW read NO-REFERENCE")
            else:
                same = key(r["ZB"]) == key(r["VG"])
                bad += not same
                print(f"ROW read {'SAME' if same else 'DIVERGES'}")
    if "break" in rows:
        b = {side: break_row(m) for side, m in (("VG", REF), ("ZB", OURS))}
        for side in ("VG", "ZB"):
            print(f"BREAK {side}: [B Cy INTFLG trapped STOP-up] = {b[side]}", flush=True)
        if not b["VG"]:
            blind += 1
            print("ROW break NO-REFERENCE")
        else:
            same = b["ZB"] == b["VG"]
            bad += not same
            print(f"ROW break {'SAME' if same else 'DIVERGES'}")
    if "cas" in rows:
        blob, want, wsum = cas_want()
        casf = probe_tmp.tmp("tapdiff_3744.cas")
        open(casf, "wb").write(blob)
        exp = (0, 0, 0, len(want), wsum)
        c = {side: cas_row(m, casf) for side, m in (("VG", REF), ("ZB", OURS))}
        for side in ("VG", "ZB"):
            print(f"CAS {side}: [C Cy1 Cy2 Cy-end read sum] = {c[side]}  (want {exp})", flush=True)
        if not c["VG"]:
            blind += 1
            print("ROW cas NO-REFERENCE")
        else:
            # both must read the file exactly, not merely agree
            same = c["ZB"] == c["VG"] == exp
            bad += not same
            print(f"ROW cas {'SAME' if same else 'DIVERGES'}"
                  f"{'' if c['VG'] == exp else ' (the VG-8020 itself did not read it whole)'}")
    if "wbreak" in rows or "rbreak" in rows:
        # a long write with no break on the VG-8020 makes the recording rbreak reads
        lw = probe_tmp.tmp("tapdiff_long_VG.wav")
        if os.path.exists(lw):
            os.remove(lw)
        base = long_row(REF, WLONG, (f"cassetteplayer new {{{lw}}}",), ["@WAIT45"])
        print(f"WLONG VG (no break): [L open loop left STOP-up INTFLG trapped] = {base}", flush=True)
        brk = ["@WAIT8", "@BREAK", "@WAIT20"]
        for row in ("wbreak", "rbreak"):
            if row not in rows:
                continue
            got = {}
            for side, m in (("VG", REF), ("ZB", OURS)):
                if row == "wbreak":
                    wav = probe_tmp.tmp(f"tapdiff_wb_{side}.wav")
                    if os.path.exists(wav):
                        os.remove(wav)
                    got[side] = long_row(m, WLONG, (f"cassetteplayer new {{{wav}}}",), brk)
                else:
                    got[side] = long_row(m, RLONG, (f"cassetteplayer insert {{{lw}}}",), brk)
                print(f"{row.upper()} {side}: [L open loop left STOP-up INTFLG trapped] = {got[side]}",
                      flush=True)
            if not got["VG"]:
                blind += 1
                print(f"ROW {row} NO-REFERENCE")
                continue
            # compared: Cy after the open, Cy after the loop (the break), STOP still held
            # at the return, INTFLG, the trap -- not `left` (where the press landed)
            k = lambda t: None if t is None else (t[0], t[1], t[3], t[4], t[5])
            same = k(got["ZB"]) == k(got["VG"])
            bad += not same
            print(f"ROW {row} {'SAME' if same else 'DIVERGES'}")
    if blind:
        print("INSTRUMENT FAULT: the VG-8020 gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: the cassette BIOS entries against the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
