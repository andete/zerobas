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

GRANULARITY -- three layers, batched by default for a whole matrix:
  * `run_case(machine, mode, lines)`  -- ONE case, ONE boot: power-on-clean
    variables + default DEF table. The single-case primitive (= run_batch of one
    case, no reset) and the isolation escape hatch.
  * `run_cases(machine, specs, batch=, reset=)`  -- a whole matrix; batch=True
    (DEFAULT) ships it in one boot with `reset` between cases (~20x faster).
  * `run_differential(ref, zb, specs, compare, isolate=)`  -- the differential
    driver: batched delivery to both machines + a SELF-HEAL pass that re-runs any
    disagreeing case boot-per-case, so verdicts equal a full boot-per-case run.

Batching became safe on 2026-07-12: the `--selftest` isolation check established
that zerobas's `NEW`/`CLEAR` did NOT clear variables or the DEF table (the
reference does -- a real divergence), now FIXED in the repack build
(basic/clear.asm + basic/program.asm; gated `IF ROM_BASE < $4000` since the lean
build is byte-full and has no DEFtbl), proven reference-identical by
basic_probe_var_reset.py -- so `--selftest` reports "batching AVAILABLE" and a
`("NEW","CLS")` reset genuinely resets shared variable/DEF/screen state between
cases in one boot. The one residual hazard is a case that WEDGES the interpreter
(a tokeniser-derail literal spins the machine so no reset recovers it, poisoning
its shared-boot followers); run_differential's `isolate` + self-heal handle it
(see that function's docstring). A breakpoint-synced probe that FREEZES the CPU
at a landmark (basic_probe_floatlit, the crunch/tokenise probes on omsx_run.py)
cannot share a boot and stays boot-per-case.
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


def _cap_expr(capture) -> str:
    """The Tcl expression yielding one case's capture as a hex string.
    "screen" (default) scrapes the SCREEN-0 name table; ("mem_indirect", PTR,
    LEN) reads a 2-byte LE pointer at PTR and dumps LEN bytes from that base --
    used to read the crunched program from TXTTAB ($F676) without freezing the
    CPU (basic_probe_floatlit)."""
    if capture == "screen":
        return f"[__hex_v {SCR_ADDR} {SCR_LEN}]"
    if isinstance(capture, tuple) and capture and capture[0] == "mem_indirect":
        _, ptr, length = capture
        return f"[__hex_mi {ptr} {length}]"
    if isinstance(capture, tuple) and capture and capture[0] == "stored_line":
        _, ptr = capture
        return f"[__hex_line {ptr}]"
    if isinstance(capture, tuple) and capture and capture[0] == "vram":
        # ("vram", addr, len) -> LEN bytes of VRAM from ADDR (the graphics probes
        # read the pattern/colour planes back mid-draw). Case must hold the screen
        # (loop forever) so the capture reads before the prompt corrupts VRAM.
        _, addr, length = capture
        return f"[__hex_v {addr} {length}]"
    if isinstance(capture, tuple) and capture and capture[0] == "mem_abs":
        # ("mem_abs", [(addr,len),...]) -> absolute CPU-memory segments concatenated
        # as one hex string (graphics tenant RAM: GFX_*, GXPOS/GYPOS, CLOC/CMASK).
        _, segs = capture
        return "".join(f"[__hex_m {a} {l}]" for a, l in segs)
    if isinstance(capture, tuple) and capture and capture[0] == "vram_segs":
        # ("vram_segs", [(addr,len),...]) -> the segments concatenated as one hex
        # string (Tcl concatenates bracketed exprs inside the "case.N=..." string).
        _, segs = capture
        return "".join(f"[__hex_v {a} {l}]" for a, l in segs)
    raise ValueError(f"unknown capture spec: {capture!r}")


def _tcl(out_path: str, cases: list[tuple[str, list[str]]],
         boot: float, step: float, cap_gap: float,
         reset: tuple[str, ...], capture="screen") -> str:
    """Build the whole-batch Tcl timeline. Each scheduled action gets its own
    emulated-time slot spaced by `step`, so the previous chunk is fully consumed
    (CHGET drains KEYBUF into the line editor) before the next write resets it."""
    body: list[str] = []
    cap = _cap_expr(capture)

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
                    f'{cap}"; flush $__f }}')
        t += cap_gap
    body.append(f"after time {t:.1f} {{ close $__f; exit }}")
    return (
        "set throttle off\n"
        f"set __f [open {{{out_path}}} w]\n"
        "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
        " return $h }\n"
        "proc __hex_m {a l} { binary scan [debug read_block memory $a $l] H* h;"
        " return $h }\n"
        # __hex_mi: dereference a 2-byte LE pointer at $p, dump $l bytes from
        # that base as hex (e.g. TXTTAB $F676 -> the stored program).
        "proc __hex_mi {p l} {\n"
        "  set b [expr {[debug read memory $p] + 256*[debug read memory [expr {$p+1}]]}]\n"
        "  binary scan [debug read_block memory $b $l] H* h; return $h\n"
        "}\n"
        # __hex_line: dump the EXACT first stored program line -- deref TXTTAB at
        # $p to the text base, read that line's link (its first 2 bytes = absolute
        # address of the NEXT line), and return base..link (link+lineno+tokens+00).
        # Empty program (link <= base, i.e. the 00 00 end-marker) -> "" (rejected).
        # Using the link gives the line's precise extent so an embedded 0x00 in a
        # value byte never truncates it (the crunch/tokenise probes need this).
        "proc __hex_line {p} {\n"
        "  set base [expr {[debug read memory $p] + 256*[debug read memory [expr {$p+1}]]}]\n"
        "  set link [expr {[debug read memory $base] + 256*[debug read memory [expr {$base+1}]]}]\n"
        "  if {$link <= $base} { return \"\" }\n"
        "  binary scan [debug read_block memory $base [expr {$link - $base}]] H* h; return $h\n"
        "}\n"
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
              reset: tuple[str, ...] = (), capture="screen",
              timeout: float = 240.0, omsx: str | None = None,
              cart: str | None = None, diska: str | None = None) -> list[str | None]:
    """Boot `machine` once and drive `cases` (each `(mode, lines)`), returning one
    capture per case (or None where that case's capture is missing). `reset`
    injects the given lines before EACH case; on the repack build NEW/CLEAR now DO
    reset variables and the DEF table (fixed 2026-07-12, see module docstring), so
    `reset=("NEW",)` is a valid cheap inter-case reset there. Prefer run_case
    unless a probe has validated its reset. mode "direct": inject each line
    verbatim (<=39 chars). mode "stored": `lines` are body statements; numbered
    10/20/... + "RUN".

    `capture` selects what each case returns: "screen" (DEFAULT) -> the raw
    SCREEN-0 name-table string (length SCR_LEN, non-print bytes -> space);
    ("mem_indirect", PTR, LEN) -> the LEN captured bytes as a lowercase hex string
    (dereferenced through the 2-byte LE pointer at PTR); ("stored_line", PTR) ->
    the FIRST stored program line's exact bytes (link+lineno+tokens+00) as hex,
    "" when the program is empty (link == 00 00, i.e. the line was rejected on
    entry) -- reads the line's link pointer for its precise extent so an embedded
    0x00 never truncates it (the crunch/tokenise probes). The probe decodes a mem
    capture itself (e.g. floatlit's marker+trim, crunch's header-strip)."""
    binary = find_omsx(omsx)
    out = tempfile.NamedTemporaryFile(suffix=".txt", prefix="repl_", delete=False).name
    tcl = out + ".tcl"
    with open(tcl, "w") as f:
        f.write(_tcl(out, cases, boot, step, cap_gap, reset, capture))
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
                if capture == "screen":
                    data = bytes.fromhex(m.group(2))
                    caps[int(m.group(1))] = "".join(
                        chr(b) if 32 <= b < 127 else " " for b in data)
                else:                      # mem capture: hand back the raw hex
                    caps[int(m.group(1))] = m.group(2)
        os.unlink(out)
    os.unlink(tcl)
    if timed_out and not caps:
        raise SystemExit(f"omsx_repl: TIMEOUT running {machine}")
    return [caps.get(i) for i in range(len(cases))]


def run_cases(machine: str, cases: list[tuple[str, list[str]]], *,
              batch: bool = True, reset: tuple[str, ...] = ("CLS",),
              capture="screen",
              boot: float = 8.0, step: float = 2.5, cap_gap: float = 2.5,
              timeout: float | None = None, omsx: str | None = None,
              cart: str | None = None, diska: str | None = None) -> list[str | None]:
    """Deliver `cases` (each `(mode, lines)`) and return one raw SCREEN-0 string
    per case, aligned with `cases`. THE DEFAULT ENTRY POINT for a whole probe
    matrix -- it picks the delivery granularity:

      batch=True (DEFAULT): ONE boot for the whole matrix, `reset` injected
        before EACH case (see run_batch). This amortises the ~0.5s openMSX boot
        across every case -> ~20x faster than boot-per-case on a large matrix.
        Safe since 2026-07-12 (5cde8a8) made NEW/CLEAR reset variables + DEFtbl
        on the repack build, confirmed by omsx_repl --selftest reporting
        "batching AVAILABLE". Pick `reset` per matrix: ("CLS",) when no case sets
        a variable (screen-clean is all that's needed); ("NEW", "CLS") when cases
        assign typed vars / DEF defaults that must not leak between cases.

      batch=False: boot-per-case (the historical default) -- each case gets
        power-on-fresh variables AND a default DEFtbl, and `reset` is ignored.
        The isolation escape hatch: when a batched case looks wrong, re-run with
        --boot-per-case to rule out inter-case leakage vs a real divergence.

    `timeout` defaults to a generous cap that scales with the matrix size so a
    long batched timeline (throttle-off but still many emulated seconds) has room
    to finish; the batch self-terminates via `exit`, so this is only a safety net.
    """
    kw = dict(boot=boot, step=step, cap_gap=cap_gap, capture=capture,
              omsx=omsx, cart=cart, diska=diska)
    if batch:
        # scale the safety-net timeout with the emulated timeline length
        to = timeout if timeout is not None else max(240.0, 1.5 * len(cases) + 120.0)
        return run_batch(machine, cases, reset=reset, timeout=to, **kw)
    to = timeout if timeout is not None else 240.0
    return [run_batch(machine, [c], reset=(), timeout=to, **kw)[0] for c in cases]


def run_differential(ref_machine: str, zb_machine: str,
                     specs: list[tuple[str, list[str]]], compare, *,
                     batch: bool = True, reset: tuple[str, ...] = ("CLS",),
                     isolate: frozenset[int] | set[int] = frozenset(),
                     **kw) -> tuple[list[bool], list[str | None], list[str | None]]:
    """Deliver `specs` (each `(mode, lines)`) to BOTH the reference and zerobas
    machines and return `(verdicts, ref_raws, zb_raws)`, all aligned with `specs`.

    Batched by default (ONE boot per machine, `reset` between cases -> ~20x). Two
    mechanisms make batching as trustworthy as boot-per-case:

      * `isolate` -- indices of cases KNOWN to wedge the interpreter (a
        tokeniser-derail literal like `1e10#` leaves a stray token that spins the
        machine so no `reset` recovers it, and every FOLLOWER in that shared boot
        captures garbage). Isolated cases skip the batch and run boot-per-case, so
        they never get a chance to poison the batch. Pre-declaring the handful the
        matrix already knows about keeps the batch clean and full-speed.
      * SELF-HEAL -- after the batch, `compare(i, ref_raw, zb_raw) -> bool` judges
        each case, and ANY case that does NOT agree is RE-RUN boot-per-case on both
        machines and re-judged, its isolated raws replacing the batched ones. This
        catches an UNDECLARED wedger's fallout (its poisoned followers re-run
        clean) and guarantees the final verdicts equal a full boot-per-case run.

    So a clean matrix re-runs nothing (full batch speed); a declared wedger costs
    one boot-per-case pair; an undeclared wedger self-heals at the price of
    re-running the tail it poisoned (add it to `isolate` to reclaim that speed).
    `batch=False` forces boot-per-case throughout (the isolation escape hatch)."""
    n = len(specs)
    ref_raws: list[str | None] = [None] * n
    zb_raws: list[str | None] = [None] * n

    if batch:
        bidx = [i for i in range(n) if i not in isolate]
        if bidx:
            rb = run_cases(ref_machine, [specs[i] for i in bidx], batch=True,
                           reset=reset, **kw)
            zbb = run_cases(zb_machine, [specs[i] for i in bidx], batch=True,
                            reset=reset, **kw)
            for j, i in enumerate(bidx):
                ref_raws[i], zb_raws[i] = rb[j], zbb[j]
        iso = [i for i in range(n) if i in isolate]
    else:
        iso = list(range(n))            # boot-per-case for everything
    if iso:
        ri = run_cases(ref_machine, [specs[i] for i in iso], batch=False, **kw)
        zi = run_cases(zb_machine, [specs[i] for i in iso], batch=False, **kw)
        for j, i in enumerate(iso):
            ref_raws[i], zb_raws[i] = ri[j], zi[j]

    verdicts = [compare(i, ref_raws[i], zb_raws[i]) for i in range(n)]
    if batch:
        fails = [i for i, ok in enumerate(verdicts) if not ok and i not in isolate]
        if fails:
            r2 = run_cases(ref_machine, [specs[i] for i in fails], batch=False, **kw)
            z2 = run_cases(zb_machine, [specs[i] for i in fails], batch=False, **kw)
            for j, i in enumerate(fails):
                ref_raws[i], zb_raws[i] = r2[j], z2[j]
                verdicts[i] = compare(i, ref_raws[i], zb_raws[i])
    return verdicts, ref_raws, zb_raws


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
