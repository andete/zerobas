#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Differential PRINT probe — prove zerobas's PRINT produces byte-identical
*screen output* to a real MSX-BASIC ROM, focused on MULTI-ITEM PRINT.

Motivation. zerobas once dropped every item after the first numeric one in
`PRINT a;b` (`print_number` divides the value in HL, clobbering the PRINT token
cursor, and `exp_num` lacked the push/pop HL guard that `exp_strvar` has — fixed
in zerobas basic/print.asm). The host unit test locks the documented format in,
but only a reference machine can establish that the *hardware* prints the same
thing. The pre-existing basic_probe_statements only ever exercised SINGLE-item
PRINT, so this gap is exactly what slipped the bug through.

Method (true differential, no hand-coded oracle for the visible bytes). For each
test line we type the IDENTICAL direct-mode line into the REPL of:

  * the reference Philips VG-8020 (built-in MSX-BASIC, no cartridge), and
  * zerobas -- either `--zb-machine <name>` (a zerobas openMSX machine of its own)
    or `--cart <rom>` (the LEAN 16 KB cartridge inserted into that same VG-8020),

then read each machine's SCREEN 0 name table from VRAM (offset 0x0000, the 40x24
text grid — same technique as basic_probe_strvar / _list / _screen), locate the
PRINT *output* row (the row right after the echoed command), and assert the two
rows are byte-identical. Equal == zerobas prints what the real ROM prints.

This covers what the host test cannot: it confirms the multi-item `;` framing AND
the `,` comma-tab-zone column accounting (the host harness doesn't model CSRX, so
`PRINT a,b` is untestable there) match real hardware. NB the SCREEN grid pads
every row with spaces, so a number's *trailing* sign-space is not screen-
observable on either machine — that nicety stays locked by the host test; here we
prove the visible inter-item spacing and the dropped-item regression.

Clean-room: this only *compares observed outputs*. The reference ROM is a black
box; no disassembly. See the clean-room firewall (CONTRIBUTING.md).
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import re
import subprocess
import sys
import tempfile
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402


OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")
MACHINE = "Philips_VG_8020"   # the reference; zerobas runs on the same HW via --cart
COLS = 40                     # SCREEN 0 (TEXT1) name-table width
ROWS = 24
NAMETBL_LEN = COLS * ROWS


def run_line(zb, line, base=6.0, tail=8.0):
    """Type one direct-mode line (+ a separately-timed Enter) and capture the SCREEN 0
    name table once output settles.

    `zb` selects the zerobas side: None runs the bare reference MACHINE; a ("cart", path)
    pair inserts a zerobas cartridge into that same reference machine; a ("machine", name)
    pair boots a zerobas machine of its own instead. The cart form is the more controlled
    comparison -- both sides are then the identical VG-8020 and differ only in the
    cartridge -- but it only exists for the LEAN 16 KB build, which is a cartridge. The
    repack build is a slot-0 32 KB main ROM, so it can only be compared machine-to-machine
    (S2 of RETIRE THE LEAN 16 KB CART, docs/spec-lean-retire-s2-switch.md)."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="print_cap_")
    os.close(out_fd)
    machine = zb[1] if zb and zb[0] == "machine" else MACHINE
    cmd = [sys.executable, OMSX_RUN, "--machine", machine]
    if zb and zb[0] == "cart":
        cmd += ["--cart", zb[1]]
    # zerobas (and the reference) drop a trailing CR that shares a burst with
    # text, so Enter is a SEPARATE, later --type event.
    cmd += ["--type", line, "--type-delay", str(base),
            "--type", "\r", "--type-delay", str(base + 3),
            "--time", str(base + 3 + tail),
            "--mem", f"VRAM:0x0000:{NAMETBL_LEN}",
            "--out", out_path, "--timeout", "180"]
    subprocess.call(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    return cap


def screen_rows(cap):
    """Decode the captured name table into ROWS text rows (printable bytes only;
    others -> space). Rows keep their leading spaces; only trailing pad stripped."""
    m = re.search(rf"mem\.VRAM:0x0000:{NAMETBL_LEN}=([0-9a-f]+)", cap)
    if not m:
        return []
    data = bytes.fromhex(m.group(1))
    rows = []
    for r in range(ROWS):
        row = data[r * COLS:(r + 1) * COLS]
        rows.append("".join(chr(c) if 32 <= c < 127 else " " for c in row).rstrip())
    return rows


def _margin(row):
    """The screen's LEFT MARGIN, in columns, read off a row we know starts at it.

    ⚠️ PIN THE INSTRUMENT. The two sides of this differential are no longer the same
    machine (see run_line), and MACHINES DISAGREE ABOUT COLUMN 0: measured, a Philips
    VG-8020 lays SCREEN 0 text out at column 2 and a C-BIOS machine at column 1. That
    is a property of the BIOS's screen setup, not of BASIC -- the identical lean build
    prints ' 1  2  3' at margin 2 on the VG-8020 and at margin 1 on C-BIOS. Comparing
    raw name-table rows across machines therefore diffs the MARGIN and reports it as a
    PRINT defect: every row differs by exactly one leading space while the output is
    byte-identical. Both sides are made margin-relative before comparison, each against
    its OWN capture, so a machine with a third margin cannot shift the result either."""
    return len(row) - len(row.lstrip(" "))


def _strip_margin(row, margin):
    """Drop exactly `margin` leading columns -- never more, so the sign space in ` 1`
    (which IS in scope) survives."""
    return row[margin:] if row[:margin].strip() == "" else row


def output_row(rows, typed):
    """The PRINT output is the row immediately after the echoed command line, with the
    screen's left margin removed. The command echoes verbatim (`typed` appears as a
    substring of its row), and that echo row starts AT the margin -- so it is both the
    locator and the instrument pin."""
    for i, row in enumerate(rows):
        if typed in row:
            if i + 1 >= len(rows):
                return ""
            return _strip_margin(rows[i + 1], _margin(row))
    return None


def output_block(rows, typed):
    """All output rows after the echoed command, up to the next prompt line
    (`Ok` / `zb>`), margin-stripped as in output_row. Used for the multi-line
    comma-wrap divergence case."""
    out = []
    margin = 0
    started = False
    for row in rows:
        if not started:
            if typed in row:
                started = True
                margin = _margin(row)
            continue
        if row.strip() in ("Ok", "ZB"):
            break
        out.append(_strip_margin(row, margin))
    # drop trailing blanks
    while out and not out[-1].strip():
        out.pop()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # Exactly one of the two zerobas-side forms. NO DEFAULT on either: a hardcoded
    # default is what silently decides which BUILD a gate measures (S1, S2).
    side = ap.add_mutually_exclusive_group(required=True)
    side.add_argument("--zb-machine", metavar="NAME",
                      help="zerobas openMSX machine (e.g. C-BIOS_MSX1_EU_REPACK_DISK)")
    side.add_argument("--cart", metavar="ROM",
                      help="zerobas cartridge inserted into the reference machine "
                           "(LEAN 16 KB build only -- the repack build is a slot-0 "
                           "main ROM, not a cartridge)")
    args = ap.parse_args()
    zb = ("machine", args.zb_machine) if args.zb_machine else ("cart", args.cart)
    print(f"[probe] reference: {MACHINE}   zerobas: {zb[0]}={zb[1]}")

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
        if not cond:
            ok = False

    # In-scope, must be byte-identical REF-vs-ZEROBAS. String literals are typed
    # lower-case (kept verbatim by both ROMs) so the row is unambiguous. These are
    # single-output-row cases: the `;` multi-item framing (the flagged regression)
    # and the SINGLE comma tab zone that fits on the line.
    match_lines = [
        "print 1;2",        # the core regression: 2nd numeric item must survive
        "print 1;2;3",      # three items
        "print 10;20",      # multi-digit, no leading-zero artefacts
        'print 7;"hi"',     # number then string literal (cursor survives number)
        "print 1;-2",       # sign framing across items (' 1 -2 ')
        "print 1,2",        # COMMA tab zone (14-col), fits — untestable host-side
    ]

    for line in match_lines:
        ref_out = output_row(screen_rows(run_line(None, line)), line)
        zb_out = output_row(screen_rows(run_line(zb, line)), line)
        located = ref_out is not None and zb_out is not None
        cond = located and ref_out == zb_out
        detail = (f"ref={ref_out!r} zb={zb_out!r}" if not cond else f"out={zb_out!r}")
        check(f"{line!r}  ref==zerobas", cond, detail)

    # Comma tab-zone WIDTH-WRAP. Real MSX-BASIC moves a `,` tab to a NEW LINE once the
    # next 14-col zone would run past the screen width.
    #
    # This was a REPORTED-ONLY "documented divergence" for the lean 16 KB build, whose
    # print_comma_zone tracked the zone width but not the width-wrap and so kept tabbing
    # on one line. ⚠️ IT IS NO LONGER A DIVERGENCE: measured 2026-07-29 on the repack
    # build, zerobas wraps the third zone exactly as the reference does, and the stale
    # note printed "divergence present as documented: NO (re-check)" -- a readout still
    # describing a build the project had stopped shipping. Promoted to a real assertion
    # here (S2, docs/spec-lean-retire-s2-switch.md): a converged row should be GATED,
    # not narrated. Running the retired lean cart via --cart will now go red on this
    # row, correctly -- that build really does diverge.
    wrap_line = "print 1,2,3"
    ref_blk = output_block(screen_rows(run_line(None, wrap_line)), wrap_line)
    zb_blk = output_block(screen_rows(run_line(zb, wrap_line)), wrap_line)
    print(f"\n--- comma tab-zone WIDTH-WRAP: {wrap_line!r} ---")
    print(f"    reference: {ref_blk}")
    print(f"    zerobas  : {zb_blk}")
    check(f"{wrap_line!r}  ref==zerobas (comma width-wrap)", ref_blk == zb_blk,
          "" if ref_blk == zb_blk else
          "— the RETIRED lean build does not width-wrap; on the repack build this "
          "converges")

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
