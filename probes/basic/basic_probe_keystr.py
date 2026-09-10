#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KEYSTR — `KEY n,"str"`, `KEY LIST` and the function-key defaults, gated.

Both forms were `Syntax error` here and work on both references (D-MISSOP3's
`r.keyok`, D-KEYSCOUT2's eleven rows); the slots read `0 0 0 0` on a cold boot
where the references hold `color `, `auto `, ... The expectations below are the
references' MEASURED faces (scratchpad/keylist_probe.py, scratchpad/
keydef_probe.py): the two agree on every row, F6 excepted, and F6 ships the
VG-8020 value on both targets by the standing style ruling (Joost, 2026-09-04).

    d.*   the n domain and the empty string: the ERR number a trapped run
          prints, 0 = accepted (KEY 0 / 11 / -1 are ERR 5, measured)
    l.*   KEY LIST after a cold boot, a plant, a 20-char store, an empty store:
          the ten lines it prints. Fenced by row name; a CR inside a default
          ends its line early, exactly as on the references.

    python3 probes/basic/basic_probe_keystr.py            gate (zb only)
    python3 probes/basic/basic_probe_keystr.py --survey   all three machines
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402

ERRCASES = [
    ("d.n1",    'KEY 1,"X"'),
    ("d.n0",    'KEY 0,"X"'),
    ("d.n10",   'KEY 10,"X"'),
    ("d.n11",   'KEY 11,"X"'),
    ("d.nneg",  'KEY -1,"X"'),
    ("d.empty", 'KEY 1,""'),
    ("d.ctl",   'A=1'),
]
LISTCASES = [
    ("l.cold",  []),
    ("l.plant", ['KEY 1,"ZQX"']),
    ("l.trunc", ['KEY 1,"ABCDEFGHIJKLMNOPQRST"']),
    ("l.empty", ['KEY 1,""']),
]
# What the references SHOW for each default: control bytes render as blanks
# (F10's leading $0C is a space, F5/F8/F9's CR and $1E leave nothing visible),
# and the rows are compared stripped -- scratchpad/keydef_probe.py has the bytes.
DEFAULTS = ["color", "auto", "goto", "list", "run", "color 15,4,4",
            'cload"', "cont", "list.", "run"]
EXPECT_ERR = {"d.n1": "0", "d.n0": "5", "d.n10": "0", "d.n11": "5",
              "d.nneg": "5", "d.empty": "0", "d.ctl": "0"}
EXPECT_LIST = {
    "l.cold":  DEFAULTS,
    "l.plant": ["ZQX"] + DEFAULTS[1:],
    "l.trunc": ["ABCDEFGHIJKLMNO"] + DEFAULTS[1:],
    "l.empty": [""] + DEFAULTS[1:],      # provisional: whether an empty slot prints a
                                        # blank line is what --survey settles
}


def err_prog(tag, stmt):
    return ["10 ON ERROR GOTO 900", f"20 {stmt}",
            f'30 PRINT"[{tag} 0]":END',
            f'900 PRINT"[{tag}";ERR;"]":END', "RUN"]


def list_prog(tag, setup):
    return setup + [f'PRINT"[{tag}"', "KEY LIST", f'PRINT"{tag}]"']


def rows40(text):
    return [text[k:k + 40] for k in range(0, len(text), 40)]


def fence(tag, cap):
    """The screen text between `[tag` and `tag]`, from a flat 40-column dump."""
    c = cap or ""
    i = c.rfind("[" + tag)
    if i < 0:
        return None
    j = c.find("]", i)
    return c[i + len(tag) + 1:j] if j > 0 else None


def list_rows(tag, cap):
    """KEY LIST's lines: the screen ROWS strictly between the fence rows.

    \u26a0\ufe0f Sliced at the ORIGINAL row boundaries, not from the `[` -- the
    first cut sliced the fenced substring, which starts mid-row, so every
    later row was misaligned by the fence's own width. The `KEY LIST` echo
    (which wraps at column 40 when it lands late in a row) and `Ok` prompts
    are not lines KEY LIST printed; blank rows ARE kept -- an empty slot may
    print an empty line, and dropping blanks would hide which."""
    c = cap or ""
    rows = rows40(c)
    # the CLOSING fence row first, then the LAST opening-fence row before it:
    # `PRINT"[l.cold"` echoes one row above the printed `[l.cold`, and the first
    # cut anchored on the echo, so the printed fence came back as a LIST line
    end = next((k for k, r in enumerate(rows) if (tag + "]") in r), None)
    if end is None:
        return None
    start = max((k for k, r in enumerate(rows[:end]) if ("[" + tag) in r), default=None)
    if start is None:
        return None
    out = []
    skip_wrap = False
    for r in rows[start + 1:end]:
        t = r.strip()
        if skip_wrap:                      # the tail of a wrapped `KEY LIST` echo
            skip_wrap = False
            if t in ("T", "ST", "IST", "LIST"):
                continue
        if t in ("Ok", "ZB"):              # the two prompts (zerobas says ZB)
            continue
        if "KEY LIS" in t:                 # the echo -- `ZBKEY LIST` on zerobas,
            skip_wrap = not t.endswith("KEY LIST")   # wrapped when it lands late
            continue
        if t.startswith('PRINT"') or t.startswith('ZBPRINT"'):
            continue
        out.append(t)
    return out


def read_side(side, cfg):
    cases = [(t, err_prog(t, s)) for t, s in ERRCASES] + \
            [(t, list_prog(t, s)) for t, s in LISTCASES]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False,
                               boot=cfg["boot"], reset=cfg["reset"], run_gap=20.0)
    out = {}
    for (t, _), cap in zip(cases, caps):
        if t.startswith("d."):
            f = fence(t, cap)
            out[t] = None if f is None else f.strip()
        else:
            out[t] = list_rows(t, cap)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--survey", action="store_true")
    a = ap.parse_args()
    sides = ("vg8020", "cf3300", "zb") if a.survey else ("zb",)
    cfg = probe_sides.sides(*sides)
    got = {s: read_side(s, cfg[s]) for s in sides}
    if got["zb"].get("d.ctl") != "0":
        print(f"\U0001f534 THE CONTROL ROW did not read 0 ({got['zb'].get('d.ctl')!r}) "
              "-- the fixture never ran; nothing below is a statement about KEY.")
        return 2
    bad = []
    print("--- the n domain and the empty string (ERR printed; 0 = accepted)")
    for t, stmt in ERRCASES:
        g, w = got["zb"][t], EXPECT_ERR[t]
        ok = g == w
        bad += [] if ok else [t]
        extra = "  ".join(f"{s}={got[s][t]!r}" for s in sides if s != "zb") if a.survey else ""
        print(f"  {'ok  ' if ok else 'DIFF'} {t:8} {stmt:28} zb={g!r:6} want={w!r}  {extra}")
    print("--- KEY LIST")
    for t, _ in LISTCASES:
        g, w = got["zb"][t], EXPECT_LIST[t]
        ok = g == w
        bad += [] if ok else [t]
        print(f"  {'ok  ' if ok else 'DIFF'} {t:8} zb={g!r}")
        if not ok:
            print(f"                want={w!r}")
        if a.survey:
            for s in sides:
                if s != "zb":
                    print(f"                {s}={got[s][t]!r}")
    print(f"\n{len(ERRCASES) + len(LISTCASES)} rows, {len(bad)} diverge: {bad or 'none'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
