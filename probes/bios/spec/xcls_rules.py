#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CLS.md's EXECUTABLE RULES (docs/spec-method.md §3a): CLS ($00C3) and POSIT ($00C6), from the XCLS matrix
-- scratchpad/XCLS_run2.out (run 1 is run 2's first 27 cases; run 2 adds the separating ones: CRTCNT 13 under POSIT,
values unlike the garbage cursor in SCREEN 2, a second colour set). The case list, the setup and the record are in
xcls_cases.py."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import xcls_cases as X  # noqa: E402
import xscr_model as M  # noqa: E402
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/CLS.md"
SP, GB, LTG = 32, 0x5A, 0x55            # a space; the VRAM garbage; the LINTTB garbage
OUTPUTS = {"XC": ["cnsdfg", "crtcnt", "csrx", "csry", "linlen", "scrmod", "lt", "namesum", "row1", "rowc", "row24",
                  "sum0", "sum2", "vsum"],
           "XS": M.OUTPUTS, "XS3": M.OUTPUTS}
LABELS = [b"key%d" % k for k in range(5)]   # the first five of the setup's FNKSTR


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XCLS_fix4.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        cs = X.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1)))
        for c in cs:
            c.src, c.id = "XC", f"XC {c.idx:02}"
        out[who] = cs + M.load(who, {"CLS", "POSIT"})
    return out


def xs(c):
    return c.src in ("XS", "XS3")


def cols(c):
    return 40 if c.mode == 0 else 32


def text_cls(c):
    return c.name == "CLS" and c.zf and c.mode != 2


def key_row(c):
    """A cleared row with the key line drawn as DSPFNK draws it (docs/bios/DSPFNK.md R-K-DSP)."""
    n, w = cols(c), c.width
    m, slot = (n - w + 1) // 2, (w + 1) // 5
    row = [SP] * n
    for k in range(5):
        for j, ch in enumerate(LABELS[k][:slot - 1]):
            row[m + k * slot + j] = ch
    return row


def cleared(c):
    """The name table after a text-mode CLS: spaces, plus the key line on row CRTCNT when CNSDFG was on. The 40 cells
    read from a 32-column row run on into the next row (spaces) or, after row 24, past the table (garbage)."""
    n = cols(c)
    total = 960 if n == 40 else 768
    key = key_row(c) if c.cns else [SP] * n
    nxt = lambda r: ([] if n == 40 else ([GB] * 8 if r == 24 else [SP] * 8))  # noqa: E731
    row24 = key if c.crt == 24 else [SP] * n
    ns = (SP * (total - n) + sum(key)) & 0xFFFF
    return (c.namesum == ns and c.row1 == [SP] * n + nxt(1) and c.rowc == key + nxt(c.crt)
            and c.row24 == row24 + nxt(24) and c.vsum == (GB * (16384 - total) + ns) & 0xFFFF
            and c.sum0 == ((ns + GB * (2048 - total)) if n == 40 else GB * 2048) & 0xFFFF
            and c.sum2 == (GB * 2048) & 0xFFFF)


def vram_untouched(c):
    return (c.vsum == (GB * 16384) & 0xFFFF and c.namesum == (GB * (960 if cols(c) == 40 else 768)) & 0xFFFF
            and c.row1 == [GB] * 40 and c.rowc == [GB] * 40 and c.row24 == [GB] * 40
            and c.sum0 == (GB * 2048) & 0xFFFF and c.sum2 == (GB * 2048) & 0xFFFF)


def clamp(v, top):
    return v if 1 <= v <= top else top


S1, S2, S3 = "1. CLS ($00C3): clear the screen", "2. POSIT ($00C6): place the cursor", "3. Both"

RULES = [
    Rule("R-C-TEXT", S1, "CLS with the Z flag set, in SCREEN 0 / 1: the whole name table (960 / 768 cells) becomes "
         "spaces -- at any width, CRTCNT 13 included -- and nothing else in VRAM changes (the whole 16 KB's sum "
         "read). With CNSDFG non-zero the key line is redrawn on row CRTCNT as DSPFNK draws it (the first five "
         "labels; docs/bios/DSPFNK.md) and CNSDFG becomes 255.",
         lambda c: text_cls(c), lambda c: cleared(c) and c.cnsdfg == (255 if c.cns else 0)),
    Rule("R-C-HOME", S1, "It homes the cursor (CSRX 1, CSRY 1) and sets LINTTB to 24, 23, …, 1 down the rows.",
         lambda c: text_cls(c), lambda c: (c.csrx, c.csry) == (1, 1) and c.lt == [24 - r for r in range(24)]),
    Rule("R-C-ZCLEAR", S1, "CLS with the Z flag CLEAR does nothing at all: VRAM, the cursor, LINTTB and CNSDFG as "
         "found, in every mode.", lambda c: c.name == "CLS" and not c.zf,
         lambda c: vram_untouched(c) and (c.csrx, c.csry) == (7, 5) and c.lt == [LTG] * 24 and c.cnsdfg == c.cns),
    Rule("R-C-GRP", S1, "CLS with the Z flag set in SCREEN 2: the pattern table ($0000, 6 KB) becomes 0 and the "
         "colour table ($2000, 6 KB) BAKCLR AS IT IS (FORCLR is not used): read here only as sums, which for 2048 "
         "equal bytes keep the byte mod 32 -- XSCR's byte reads pin it ($16, $C5: R-C-SEVERAL); the name and "
         "sprite tables are left as found, and so are the cursor, LINTTB and CNSDFG.",
         lambda c: c.name == "CLS" and c.zf and c.mode == 2,
         lambda c: (c.sum0 == 0 and c.sum2 == (2048 * c.bg) & 0xFFFF
                    and c.vsum == (GB * 4096 + 6144 * c.bg) & 0xFFFF
                    and c.namesum == (GB * 768) & 0xFFFF and c.row1 == c.rowc == c.row24 == [GB] * 40
                    and (c.csrx, c.csry) == (7, 5) and c.lt == [LTG] * 24 and c.cnsdfg == c.cns)),
    Rule("R-P-CLAMP", S2, "POSIT in SCREEN 0 / 1: CSRX := H and CSRY := L, each CLAMPED -- a column of 0 or above "
         "LINLEN becomes LINLEN (0 / 41 / 255 at width 40 give 40; 38 at 37 gives 37; 31 / 30 at 29 give 29), a row "
         "of 0 or above the LIMIT (CRTCNT + CNSDFG) mod 256 becomes that limit: CRTCNT with the key line off (0 / 14 "
         "/ 20 give 13 with CRTCNT 13; 25 / 30 / 255 give 24 with 24), CRTCNT − 1 with CNSDFG's usual $FF (25 / 24 "
         "/ 0 give 23: the key line's row is not the cursor's), and -- the same sum -- 25 with CNSDFG 1, 26 with 2, 152 "
         "with $80 (L 100 stays, 153 gives 152), 12 at CRTCNT 13 with $FF. It ignores the Z flag (Z clear: still "
         "clamped).",
         lambda c: c.name == "POSIT" and c.mode < 2,
         lambda c: ((c.csrx, c.csry) == (clamp(c.h, c.width), clamp(c.l, (c.crt + c.cns) & 0xFF))) if not xs(c)
         else M.matches(c, ["csrx_out", "csry_out"])),
    Rule("R-P-GRP", S2, "POSIT in SCREEN 2 and 3 does nothing: the cursor stays as found -- (7, 5) and (11, 3) -- for "
         "H / L 3 / 9 and 0 / 0.",
         lambda c: c.name == "POSIT" and c.mode >= 2,
         lambda c: (c.csrx, c.csry) == (7, 5) if not xs(c) else M.matches(c, ["csrx_out", "csry_out"])),
    Rule("R-P-ONLY", S2, "POSIT changes nothing else: VRAM, LINTTB and CNSDFG as found.",
         lambda c: c.name == "POSIT", lambda c: vram_untouched(c) and c.lt == [LTG] * 24 and c.cnsdfg == c.cns),
    Rule("R-CP-STATE", S3, "Neither changes CRTCNT, LINLEN or SCRMOD.", lambda c: True,
         lambda c: (c.crtcnt, c.scrmod) == (c.crt, c.mode) and (c.mode == 2 or c.linlen == c.width)),
]

UNREAD = {f"XC {i:02}": (["linlen"], "SCREEN 2 cases: the setup does not set LINLEN there (INIGRP does not), so its "
                                    "value is the previous case's")
          for i, c in enumerate(X.CASES) if c.mode == 2}

# The rules above state XCLS run 2 (group XC), apart from R-P-CLAMP / R-P-GRP which state both. XSCR (group XS,
# xscr_model.py) gives the inputs several values; its rules follow.
for _r in RULES:
    if _r.id not in ("R-P-CLAMP", "R-P-GRP"):
        _r.select = (lambda s: (lambda c: not xs(c) and s(c)))(_r.select)

_ALL = ["cnsdfg", "crtcnt", "csrx_out", "csry_out", "linl40", "linl32", "lt", "namesum", "row1", "rowc", "row24",
        "vsum", "win", "scrmod"]


def _model(c):
    return M.matches(c, _ALL + ([] if c.mode >= 2 else ["linlen"]))


RULES += [
    Rule("R-C-GATE", S1, "CLS acts exactly when the Z flag is set: A = 0 with Z set and A = 1 with Z and carry set "
         "clear the screen; A = 1 and A = 0 with Z clear do nothing -- A and the carry do not matter.",
         lambda c: xs(c) and c.name == "CLS" and (c.ea, c.ef) != (1, 0x40), _model),
    Rule("R-C-SEVERAL", S1, "And with the inputs at several values (XSCR): CNSDFG 2 / $80 / $FF all redraw the key "
         "line (CNSDFG becomes 255); a second garbage set; H / L 3 / 9 ignored; the name table moved (TXTNAM $1000, "
         "T32NAM $1C00 -- cleared there); CRTCNT 13 in SCREEN 1; 15-character labels cut to slot − 1; in SCREEN 2 "
         "the colour table's BYTES read BAKCLR as it is ($16, $C5) and the pattern table's 0 -- every cell, the "
         "cursor, LINTTB and the whole VRAM's sum as the model says. With the cursor ON the key line's row (24, or 13 at "
         "CRTCNT 13) CLS does not scroll: it clears, homes, and draws the line. With TXTNAM / T32NAM changed AFTER "
         "INITXT / INIT32 it clears the table the mode's call set up, not the one TXTNAM now names.",
         lambda c: xs(c) and c.name == "CLS" and (c.ea, c.ef) == (1, 0x40) and c.mode < 3, _model),
    Rule("R-C-MLT", S1, "CLS in SCREEN 3 (Z set): the multicolour pattern table ($0000, 1.5 KB) becomes $66 -- "
         "BAKCLR 6 in both nibbles, one BAKCLR measured -- and nothing else changes: the name table, the cursor, "
         "LINTTB.", lambda c: xs(c) and c.name == "CLS" and c.mode == 3, _model),
    Rule("R-P-SEVERAL", S2, "POSIT changes nothing else, with the inputs at several values: VRAM (the whole sum), "
         "LINTTB, CNSDFG, CRTCNT, LINL40 / LINL32 as found.",
         lambda c: xs(c) and c.name == "POSIT",
         lambda c: M.matches(c, [f for f in _ALL if f not in ("csrx_out", "csry_out")]
                             + ([] if c.mode >= 2 else ["linlen"]))),
    Rule("R-CP-AF", S3, "A / F on return (not published): the reference's values -- CLS 00 / 54 in SCREEN 0 / 1 without "
         "the key line, 00 / 44 with it and in SCREEN 2, 66 / 24 in SCREEN 3, A / F unchanged when Z was clear; POSIT "
         "24 / 30 in SCREEN 0 / 1, 22 / 30 in SCREEN 2 / 3, 48 / 18 with A / F 00 / 00 on entry.",
         lambda c: xs(c), lambda c: (c.a, c.f) == M.REF_AF[c.id]),
]

UNREAD.update({c.id: (["linlen"], "SCREEN 2 / 3 cases: the setup does not set LINLEN there (INIGRP / INIMLT do "
                                  "not), so its value is the previous case's")
               for c in M.load("ref", {"CLS", "POSIT"}) if c.mode >= 2})
