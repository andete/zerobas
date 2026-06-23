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
  * zerobas (the same VG-8020 with --cart basic.rom),

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


OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")
MACHINE = "Philips_VG_8020"   # the reference; zerobas runs on the same HW via --cart
COLS = 40                     # SCREEN 0 (TEXT1) name-table width
ROWS = 24
NAMETBL_LEN = COLS * ROWS


def run_line(cart, line, base=6.0, tail=8.0):
    """Type one direct-mode line (+ a separately-timed Enter) on MACHINE, with or
    without `cart`, then capture the SCREEN 0 name table once output settles."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="print_cap_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", MACHINE]
    if cart:
        cmd += ["--cart", cart]
    # zerobas (and the reference) drop a trailing CR that shares a burst with
    # text, so Enter is a SEPARATE, later --type event.
    cmd += ["--type", line, "--type-delay", str(base),
            "--type", "\r", "--type-delay", str(base + 3),
            "--time", str(base + 3 + tail),
            "--mem", f"VRAM:0x0000:{NAMETBL_LEN}",
            "--out", out_path, "--timeout", "180"]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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


def output_row(rows, typed):
    """The PRINT output is the row immediately after the echoed command line.
    The command echoes verbatim (`typed` appears as a substring of its row), so
    find that row and return the next one."""
    for i, row in enumerate(rows):
        if typed in row:
            return rows[i + 1] if i + 1 < len(rows) else ""
    return None


def output_block(rows, typed):
    """All output rows after the echoed command, up to the next prompt line
    (`Ok` / `zb>`). Used for the multi-line comma-wrap divergence case."""
    out = []
    started = False
    for row in rows:
        if not started:
            if typed in row:
                started = True
            continue
        if row.strip() in ("Ok", "zb>") or row.strip().endswith("zb>"):
            break
        out.append(row)
    # drop trailing blanks
    while out and not out[-1].strip():
        out.pop()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    args = ap.parse_args()

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
        zb_out = output_row(screen_rows(run_line(args.cart, line)), line)
        located = ref_out is not None and zb_out is not None
        cond = located and ref_out == zb_out
        detail = (f"ref={ref_out!r} zb={zb_out!r}" if not cond else f"out={zb_out!r}")
        check(f"{line!r}  ref==zerobas", cond, detail)

    # DOCUMENTED DIVERGENCE (observed, reported, NOT failed) — comma tab-zone
    # line-wrap. Real MSX-BASIC moves a `,` tab to a NEW LINE once the next 14-col
    # zone would run past the screen width; zerobas's print_comma_zone keeps
    # tabbing on the same line (it tracks the zone width but not the width-wrap).
    # Out of loader-stub scope (a stub never PRINTs enough comma items to wrap);
    # measured here so the divergence is on record, mirroring the disk-probe
    # FCB-field divergences. PASS/FAIL above does not hinge on it.
    wrap_line = "print 1,2,3"
    ref_blk = output_block(screen_rows(run_line(None, wrap_line)), wrap_line)
    zb_blk = output_block(screen_rows(run_line(args.cart, wrap_line)), wrap_line)
    print(f"\n--- documented divergence (reported, not failed): {wrap_line!r} ---")
    print(f"    reference (wraps 3rd zone to a new line): {ref_blk}")
    print(f"    zerobas   (no width-wrap, one line):      {zb_blk}")
    wrapped = len(ref_blk) > len(zb_blk)
    print(f"    => divergence present as documented: {'yes' if wrapped else 'NO (re-check)'}")

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
