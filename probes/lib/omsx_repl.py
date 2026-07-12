#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""omsx_repl -- typing-free REPL driver for the differential acceptance probes.

Boots openMSX once and drives a batch of BASIC test *cases* by injecting each
REPL line straight into the BIOS type-ahead buffer (KEYBUF), rather than
emulating the keyboard MATRIX with openMSX `type`. `CHSNS`/`CHGET` deliver the
injected bytes and the ROM tokenises them exactly as if typed -- but no matrix
scan is involved, so the two matrix-typing flake modes vanish:

  * a leading key can no longer double (`print`->`pprint` -> spurious syntax
    error) -- the whole line lands atomically via `debug write`;
  * an Enter can no longer be swallowed mid-type -- there is no per-char type
    schedule to race.

Published MSX2-TH system-variable contract only, NO ROM disassembly:
  KEYBUF $FBF0  40-byte circular type-ahead buffer
  GETPNT $F3FA / PUTPNT $F3F8  read / write cursors (empty when equal)
Verified black-box that C-BIOS honours it (a real MSX1 does by construction --
this is where the standard comes from). Lifted from the proven `__inj` proc in
probes/disk/disk_probe_getput.py.

Design (docs/spec-acceptance-harness-rework.md):
  * KEYBUF is the DEFAULT line driver. A line up to MAX_DIRECT (38) source chars
    injects in one write; a LONGER line is CHUNKED -- written in <=38-char pieces
    with the submitting CR only on the last, so the ROM line editor accumulates
    an arbitrarily long line (to ~255 chars) while the 40-byte buffer never
    overflows. So a long DIRECT line needs no special handling at the call site.
  * `as_stored()` + mode="stored" is still available to run a `:`-joined line as
    a multi-line stored program (needed where stored-vs-direct semantics differ,
    e.g. a re-entrant FOR/NEXT).
  * The write_block->TXTTAB tokenised-injection fallback (spec s2.2) is therefore
    UNNEEDED for line length -- chunking covers it -- and remains unbuilt.

The driver draws NO conclusions: it delivers bytes and scrapes the SCREEN 0 name
table from VRAM, returning one raw 40x24 screen string per case. Span/tail
extraction (the `[...]` bracket convention) lives in the reusable helpers below.

DEFAULT GRANULARITY -- BOOT PER CASE (`run_case`): a fresh boot gives every case
power-on-clean variables AND a default (all-double) DEF type table, exactly like
the matrix-typing harness it replaces, so the conversion is differential-inert.
This is the default because batching is NOT safe on the current zerobas build:
the `--selftest` isolation check established (2026-07-12) that zerobas's `NEW` and
`CLEAR` do NOT clear variables or the DEF table (the reference does -- a real
zerobas divergence, flagged separately), so there is no cheap way to reset state
between cases in one boot. `run_batch` (many cases/boot) is retained for probes
whose cases are provably independent (share no variable/DEF state), and MUST NOT
be used for a shared-state matrix until that divergence is fixed.
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omsx_run import find_omsx  # reuse headless-binary discovery

# --- published sysvar contract (MSX2 Technical Handbook; no disasm) ----------
KEYBUF = 0xFBF0
GETPNT = 0xF3FA
PUTPNT = 0xF3F8
KEYBUF_SZ = 40
# A 40-byte CIRCULAR buffer holds at most 39 bytes unambiguously: with 40 bytes
# written, PUTPNT wraps to equal GETPNT (full is indistinguishable from empty),
# and the ROM re-reads the buffer -> the line executes TWICE (observed for a
# 39-char line: 39 + CR = 40). So an injected line + its CR must be <= 39, i.e.
# the line itself is at most 38 source chars.
MAX_DIRECT = KEYBUF_SZ - 2  # 38: longest line injectable verbatim (CR excluded)

# SCREEN 0 name table (both Philips_VG_8020 and the repack disk machine boot
# 40-column text; a stock SCREEN-1 machine would need 0x1800/768/32 instead).
SCR_ADDR = 0x0000
COLS, ROWS = 40, 24
SCR_LEN = COLS * ROWS


def as_stored(line: str) -> list[str]:
    """Split a `:`-joined direct-mode line into body statements for stored mode.
    `A=1:A%=2:PRINT"[";A;"]"` -> ['A=1:A%=2', 'PRINT"[";A;"]"'] chunked so each
    resulting numbered line ("10 " + chunk) fits the 39-char KEYBUF budget. A
    `:` inside a string literal is NOT a statement separator, so split only on
    top-level colons."""
    stmts, cur, in_str = [], [], False
    for ch in line:
        if ch == '"':
            in_str = not in_str
            cur.append(ch)
        elif ch == ":" and not in_str:
            stmts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    stmts.append("".join(cur))
    # greedily pack statements into <=34-char bodies so a numbered line
    # ("NNN " prefix, up to 4 chars) still fits MAX_DIRECT (38); a single
    # statement longer than that is emitted alone and, if the numbered line
    # still overflows, trips the length guard in _tcl (-> TXTTAB fallback).
    bodies, cur_body = [], ""
    for s in stmts:
        cand = s if not cur_body else cur_body + ":" + s
        if len(cand) <= 34:
            cur_body = cand
        else:
            if cur_body:
                bodies.append(cur_body)
            cur_body = s
    if cur_body:
        bodies.append(cur_body)
    return bodies


MAX_BUF = 250  # MSX line-input buffer (BUF/LINBUF) holds ~255 chars incl CR


def _tcl(out_path: str, cases: list[tuple[str, list[str]]],
         boot: float, step: float, cap_gap: float,
         reset: tuple[str, ...]) -> str:
    """Build the whole-batch Tcl timeline. Each scheduled action gets its own
    emulated-time slot spaced by `step`, so the previous chunk is fully consumed
    (CHGET drains KEYBUF into the line editor) before the next write resets it."""
    body: list[str] = []

    def emit(t: float, s: str) -> float:
        """Schedule injection of one CR-terminated line `s` at/after time `t`;
        return the next free time. A line longer than the 40-byte KEYBUF cap is
        CHUNKED into <=MAX_DIRECT pieces written with NO CR until the last -- the
        ROM line editor accumulates them into its own (~255-byte) buffer, so an
        arbitrarily long DIRECT line works without a tokeniser or TXTTAB. (The
        TXTTAB tokenised-injection fallback, spec s2.2, is thus still unneeded.)"""
        if len(s) > MAX_BUF:
            raise ValueError(f"line exceeds MSX line buffer (~{MAX_BUF}): "
                             f"{len(s)} chars {s!r}")
        if len(s) <= MAX_DIRECT:
            body.append(f'after time {t:.1f} {{ __inj {{{s}}} }}')
            return t + step
        chunks = [s[i:i + MAX_DIRECT] for i in range(0, len(s), MAX_DIRECT)]
        for k, ch in enumerate(chunks):
            proc = "__inj" if k == len(chunks) - 1 else "__key"  # CR only on last
            body.append(f'after time {t:.1f} {{ {proc} {{{ch}}} }}')
            t += step
        return t

    t = boot
    for idx, (mode, lines) in enumerate(cases):
        for r in reset:                       # power-on-clean vars + DEFtbl + screen
            t = emit(t, r)
        if mode == "stored":
            seq = [f"{10 * (i + 1)} {ln}" for i, ln in enumerate(lines)] + ["RUN"]
        else:
            seq = list(lines)
        for ln in seq:
            t = emit(t, ln)
        body.append(f'after time {t:.1f} {{ puts $__f "case.{idx}='
                    f'[__hex_v {SCR_ADDR} {SCR_LEN}]"; flush $__f }}')
        t += cap_gap
    body.append(f"after time {t:.1f} {{ close $__f; exit }}")
    return (
        "set throttle off\n"
        f"set __f [open {{{out_path}}} w]\n"
        "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
        " return $h }\n"
        # __key: write the raw bytes of `s` into KEYBUF and point GETPNT/PUTPNT at
        # them so CHGET delivers them (no CR). Cursors reset each call -- safe
        # because the per-slot step guarantees the prior chunk was consumed.
        "proc __key {s} {\n"
        "  set n [string length $s]\n"
        "  for {set i 0} {$i < $n} {incr i} {\n"
        f"    debug write memory [expr {{{KEYBUF} + $i}}] "
        "[scan [string index $s $i] %c]\n"
        "  }\n"
        f"  debug write memory {GETPNT} [expr {{{KEYBUF} & 0xFF}}]\n"
        f"  debug write memory [expr {{{GETPNT}+1}}] [expr {{({KEYBUF} >> 8) & 0xFF}}]\n"
        f"  set p [expr {{{KEYBUF} + $n}}]\n"
        f"  debug write memory {PUTPNT} [expr {{$p & 0xFF}}]\n"
        f"  debug write memory [expr {{{PUTPNT}+1}}] [expr {{($p >> 8) & 0xFF}}]\n"
        "}\n"
        # __inj: __key plus the submitting CR (appended here so a literal CR byte
        # never has to survive Tcl brace-quoting).
        "proc __inj {s} { append s \"\\r\"; __key $s }\n"
        + "\n".join(body) + "\n")


def run_case(machine: str, mode: str, lines: list[str], **kw) -> str | None:
    """Boot `machine` and drive ONE case (`mode`, `lines`), returning its raw
    SCREEN-0 name-table string (or None on capture failure). THE DEFAULT ENTRY
    POINT: one boot per case = power-on-fresh vars + DEFtbl, matching the
    matrix-typing harness this replaces (differential-inert). See module docstring
    on why batching is unsafe on the current zerobas build."""
    return run_batch(machine, [(mode, lines)], reset=(), **kw)[0]


def run_batch(machine: str, cases: list[tuple[str, list[str]]], *,
              boot: float = 8.0, step: float = 2.5, cap_gap: float = 2.5,
              reset: tuple[str, ...] = (),
              timeout: float = 240.0, omsx: str | None = None,
              cart: str | None = None, diska: str | None = None) -> list[str | None]:
    """Boot `machine` once and drive `cases` (each `(mode, lines)`), returning one
    raw SCREEN-0 name-table string (length SCR_LEN, non-print bytes -> space) per
    case, or None where that case's capture is missing. `reset` injects the given
    lines before EACH case -- but note NEW/CLEAR do not reset zerobas state (see
    module docstring), so multi-case batching is only safe for state-independent
    cases; prefer run_case. mode "direct": inject each line verbatim (<=39 chars).
    mode "stored": `lines` are body statements; numbered 10/20/... + "RUN"."""
    binary = find_omsx(omsx)
    out = tempfile.NamedTemporaryFile(suffix=".txt", prefix="repl_", delete=False).name
    tcl = out + ".tcl"
    with open(tcl, "w") as f:
        f.write(_tcl(out, cases, boot, step, cap_gap, reset))
    if os.path.exists(out):
        os.unlink(out)

    cmd = [binary, "-machine", machine]
    if cart:
        cmd += ["-cart", cart]
    if diska:
        cmd += ["-diska", diska]
    cmd += ["-command", "set renderer none", "-script", tcl]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.05)
    timed_out = proc.poll() is None
    if timed_out:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)

    caps: dict[int, str] = {}
    if os.path.exists(out):
        for ln in open(out):
            m = re.match(r"case\.(\d+)=([0-9a-f]*)", ln.strip())
            if m and m.group(2):
                data = bytes.fromhex(m.group(2))
                caps[int(m.group(1))] = "".join(
                    chr(b) if 32 <= b < 127 else " " for b in data)
        os.unlink(out)
    os.unlink(tcl)
    if timed_out and not caps:
        raise SystemExit(f"omsx_repl: TIMEOUT running {machine}")
    return [caps.get(i) for i in range(len(cases))]


# --- reusable span/tail extraction (the `[...]` bracket convention) ----------
# Machine-agnostic: the reference closes each command with 'Ok', zerobas with a
# bare 'zb>' prompt, and prefixes its echo with 'zb>' -- so echo matching is
# ends-with and both prompt shapes terminate a tail.

def result_span(raw: str | None) -> str | None:
    """Text between the LAST '[' and the following ']' (the printed value).
    None if the ']' never printed (statement aborted before the PRINT)."""
    if raw is None:
        return None
    i = raw.rfind("[")
    if i < 0:
        return None
    j = raw.find("]", i)
    return raw[i + 1:j] if j >= 0 else None


def _echo_idx(rows: list[str], cmdline: str) -> int | None:
    key = cmdline.strip()
    idx = None
    for i, r in enumerate(rows):
        if r == key or r.endswith(key):
            idx = i  # keep the LAST occurrence
    return idx


def screen_tail(raw: str | None, cmdline: str) -> str | None:
    """Rows between the echoed command and the closing prompt, right-stripped,
    '|'-joined -- pins error text + abort-vs-continue shape. None if no echo."""
    if raw is None:
        return None
    rows = [raw[r * COLS:(r + 1) * COLS].strip() for r in range(ROWS)]
    idx = _echo_idx(rows, cmdline)
    if idx is None:
        return None
    out: list[str] = []
    for r in rows[idx + 1:]:
        if r == "Ok" or r == "zb>":
            break
        out.append(r)
    while out and out[-1] == "":
        out.pop()
    return "|".join(out)


def result_span_after_echo(raw: str | None, cmdline: str) -> str | None:
    """Like result_span but restricted to rows AFTER the echoed command line, so
    an aborted case's echoed '[' is not misread as printed output. None if the
    echo row can't be found."""
    if raw is None:
        return None
    rows = [raw[r * COLS:(r + 1) * COLS] for r in range(ROWS)]
    idx = _echo_idx([r.strip() for r in rows], cmdline)
    if idx is None:
        return None
    return result_span("".join(rows[idx + 1:]))


# --- self-test: earn trust by reproduction + fix the batching-safety boundary -
# Reproduction cases -- each run BOOT-PER-CASE (run_case), so power-on-fresh
# state; expectations are hand-verified against MSX-BASIC. Covers: a direct value,
# an abort shape, a stored FOR/NEXT (the resume path), and a long line expressed
# as a split stored program (the KEYBUF 40-byte-cap workaround).
_REPRO = [
    # (label, mode, lines, kind, expect)  kind: value|abort
    ("direct.add",   "direct", ['PRINT"[";1+1;"]"'],                 "value", " 2 "),
    ("direct.abort", "direct", ['A%="X":PRINT"[";1;"]"'],            "abort", None),
    ("stored.fornext", "stored",
        ["FOR I=1 TO 3:NEXT", 'PRINT"[";I;"]"'],                     "value", " 4 "),
    ("stored.split", "stored",
        ["A=1:A%=2:A!=3:A#=4", 'PRINT"[";A;A%;A!;A#;"]"'],           "value", " 4  2  3  4 "),
    # a 44-char DIRECT line (no top-level ':', unsplittable) -> exercises the
    # chunked KEYBUF injection; 1.5-1.5=0 is false so ELSE runs -> prints [y].
    ("direct.long", "direct",
        ['IF 1.5-1.5 THEN PRINT"[n]" ELSE PRINT"[y]"'],             "value", "y"),
]


def _isolation_ok(machine: str, **kw) -> bool:
    """Informational: can multiple cases share one boot? True iff a variable set
    in case 0 is gone (unset -> 0) in case 1 after the reset. Currently False on
    zerobas (NEW/CLEAR don't clear vars); when it flips True, run_batch multi-case
    becomes safe for shared-state matrices."""
    scr = run_batch(machine, [("direct", ['B%=5:PRINT"[";B%;"]"']),
                              ("direct", ['PRINT"[";B%;"]"'])],
                    reset=("NEW", "CLS"), **kw)
    return result_span(scr[1]) == " 0 "


def _selftest(machine: str, omsx: str | None = None,
              cart: str | None = None, diska: str | None = None) -> int:
    kw = dict(omsx=omsx, cart=cart, diska=diska)
    ok = True
    print(f"=== omsx_repl self-test on {machine} ===")
    for label, mode, lines, kind, expect in _REPRO:
        raw = run_case(machine, mode, lines, **kw)
        if kind == "value":
            span = result_span(raw)
            good = span == expect
            print(f"  {'PASS' if good else 'FAIL'}  {label:<16} "
                  f"[{span}] (want [{expect}])")
        else:
            span = result_span_after_echo(raw, lines[-1])
            tail = screen_tail(raw, lines[-1])
            good = span is None and bool(tail)
            print(f"  {'PASS' if good else 'FAIL'}  {label:<16} "
                  f"abort span={span!r} tail={tail!r}")
        ok = ok and good
    iso = _isolation_ok(machine, **kw)
    print(f"--- multi-case batching {'AVAILABLE' if iso else 'UNSAFE'} on this "
          f"build (NEW/CLEAR var-reset {'works' if iso else 'is broken'}); "
          f"{'run_batch ok' if iso else 'use run_case (boot-per-case)'} ---")
    print(f"=== {'ALL PASS' if ok else 'SOME FAILED'} ===")
    return 0 if ok else 1


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", metavar="MACHINE",
                    help="run the reproduction + isolation self-test on MACHINE")
    ap.add_argument("--omsx", help="path to openmsx binary")
    ap.add_argument("--cart", help="cartridge ROM to insert")
    ap.add_argument("--diska", help="disk image for drive A")
    args = ap.parse_args()
    if args.selftest:
        return _selftest(args.selftest, omsx=args.omsx, cart=args.cart, diska=args.diska)
    ap.error("nothing to do; pass --selftest MACHINE (this module is imported by probes)")


if __name__ == "__main__":
    raise SystemExit(main())
