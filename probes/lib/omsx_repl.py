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

DELIVERY IS VERIFIED, NOT ASSUMED (D-DELIVER, docs/spec-probe-delivery.md). A
batched `mode="stored"` case can lose a whole program line to an alignment race
-- measured 1 in 30 at the default `step` on the zerobas machine, 0 in 30 on the
reference -- and the loss is INVISIBLE in the capture: the two standing
`graphics-acceptance` reds were one case that lost `10 ON ERROR GOTO 40` and one
that lost its `PRINT` line, both reading as plausible semantics on both sides.
So every stored case now reports the line-number chain the machine actually
held, just before its `RUN`; `run_cases` re-runs a mangled case boot-per-case
and says so, `run_batch` (which IS that path) refuses.

TWO INDEPENDENT ORACLES WATCH DELIVERY, AND EACH OTHER (D-ECHO,
docs/spec-probe-echo.md). The stored-program oracle above covers `mode="stored"`
-- 8 of the 53 probe files that drive this module. The SAME race mangles a
`direct`-mode line: phase O re-expressed in direct mode, with byte-identical
injections on byte-identical slots, loses the same line of the same case. So
EVERY injected line is also checked against what the machine ECHOED: `_tcl` dumps
SCRMOD, LINLEN and the name table after each slot, and `echo_verdicts` compares.
Where both oracles can see they must agree, and `run_cases` announces it when
they do not -- which is the only positive control either has, since a batch of
IDENTICAL cases does not reproduce the race at all. `ZEROBAS_ECHOGUARD=off`
disarms the echo half; `verify_delivery=False` opts a probe out of both.

THE RACE ITSELF IS GONE AT SOURCE (D-LATCH, docs/spec-probe-latch.md). Its
trigger is one instruction wide: a callback landing between C-BIOS `chget`'s
`ld hl,(GETPNT)` and `ld de,(PUTPNT)` sees an injector that has moved GETPNT
BACKWARDS under a CPU that already latched it. `key_proc` therefore writes at
the current GETPNT and never moves it -- immune by construction, verified by
forcing the injection onto that exact boundary with a breakpoint (100% mangled
before, 0% after: `make latch-check`). BOTH ORACLES STAY ARMED. A fix removes a
fault; it does not remove the need to detect one, and spec §2.5 names a second,
never-observed window this does not close.

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

import glob
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from xml.etree import ElementTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omsx_run import find_omsx  # reuse headless-binary discovery
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.dirname(_zbo.path.abspath(__file__)))
import omsx_preflight  # noqa: E402
# 🎯 ESTABLISHES THE PROJECT TEMP ROOT (`/tmp/zerobas`) AS A SIDE EFFECT OF
# IMPORT -- see probes/lib/probe_tmp.py. Imported here, at a chokepoint every
# probe reaches, so a bare `tempfile.*` anywhere lands under the one root.
import probe_tmp  # noqa: E402,F401
# 🎯 AND HOLDS OFF macOS IDLE SLEEP, ALSO AS A SIDE EFFECT OF IMPORT, for the
# same chokepoint reason -- probes/lib/probe_awake.py carries the night it cost.
# D-NOSLEEP covered `make gates` only; every ad-hoc probe and knife runner, which
# is what an unattended session runs BEFORE the battery, was still exposed.
import probe_awake  # noqa: E402
probe_awake.hold_once()

# --- published sysvar contract (MSX2 Technical Handbook; no disasm) ----------
KEYBUF = 0xFBF0
GETPNT = 0xF3FA
PUTPNT = 0xF3F8
TXTTAB = 0xF676                  # -> the stored program's text base ($8001 here)
SCRMOD = 0xFCAF                  # current screen mode (0 = 40-column text)
LINLEN = 0xF3B0                  # width of the text window, in columns
KEYBUF_SZ = 40
# A 40-byte CIRCULAR buffer holds at most 39 bytes unambiguously: with 40 bytes
# written, PUTPNT wraps to equal GETPNT (full is indistinguishable from empty),
# and the ROM re-reads the buffer -> the line executes TWICE (observed for a
# 39-char line: 39 + CR = 40). So an injected line + its CR must be <= 39, i.e.
# the line itself is at most 38 source chars.
MAX_DIRECT = KEYBUF_SZ - 2  # 38: longest line injectable verbatim (CR excluded)

# D-LATCH2 (docs/spec-probe-latch2.md §5.5): how long `__key` will wait for a
# NON-DRAINED buffer before injecting anyway.
#
# THE WORST CASE IS A PROPERTY OF THE BUFFER, NOT OF USAGE, so it can be priced
# exactly: 40 circular bytes hold at most 39 (MAX_DIRECT + CR), and a pending
# line of exactly that length drains in **10 retries / 20 ms** measured
# (11 B -> 3, 20 B -> 6, 39 B -> 10; ~0.5 ms per echoed character). 40 retries
# is 4x that worst case.
#
# The ceiling is ECHO_GAP (0.8 s) below -- the echo guard dumps the screen that
# long after the scheduled injection, so a deferral approaching it would make
# the guard judge a line that had not landed yet -- and the 2.5 s default
# `step`. 40 x 2 ms = 80 ms is 10% of the tighter one.
#
# Exhausting the bound is not a failure mode: it injects anyway, which is
# byte-for-byte the behaviour that shipped for the whole D-LATCH era.
KEY_DEFER_STEP = 0.002
KEY_DEFER_MAX = 40

# A case "line" of the form `@WAIT<seconds>` types NOTHING and simply advances the
# emulated timeline. It exists because the obvious way to wait -- padding the case
# with harmless `REM` lines -- COSTS SCREEN ROWS, and the screen is 24 rows deep.
#
# 🔴 THAT COST IS NOT COSMETIC: IT BROKE THE ECHO GUARD. A cassette LOAD or SAVE
# runs for ~10-30 emulated seconds while the harness keeps injecting on schedule
# (each __key call OVERWRITES whatever is still pending, so lines delivered
# mid-operation collapse into one -- D-LATCH changed WHERE that write lands, not
# that it discards), so a tape row needs the clock advanced past the operation before its
# readout is typed. Padding with `REM` did that at two screen rows apiece, and on
# the CF-3300 -- whose Disk BASIC prints more per row -- the case's own payload
# scrolled off the top: `MANGLED not echoed: ['60 REM Y', ...]` for rows whose
# VALUES were right and stable at --repeat 2 (docs/dotgaps-msx1-characterization.md
# §1.4b). Worse, it sat exactly on the boundary, so the same row passed in one run
# and failed in the next. A wait that types nothing is deterministic and free.
WAIT_PREFIX = "@WAIT"

# `@BREAK` -- press Ctrl-STOP, mid-case (D-EDITVERB). A second pseudo-line, and
# it exists for the same reason `holds` does: KEYBUF injection writes DECODED
# CHARACTERS, and Ctrl-STOP is not a character. It is a key-matrix combination
# (row 6 bit 1 = CTRL, row 7 bit 4 = STOP), so only `keymatrixdown` can deliver
# it and only a routine that SCANS the matrix (BREAKX $00B7) can see it.
#
# ⚠️ NOT the same seam as `holds`. `holds` presses ONE (row, mask) after a case's
# LAST line and releases it just before the capture, which suits a program
# sampling a joystick for its whole run. A modal statement has to be broken
# BETWEEN typed lines and then typed at again -- an AUTO session is entered,
# fed, broken, and only then asked to LIST -- so this rides the line list where
# the ordering is explicit.
BREAK_PREFIX = "@BREAK"
BREAK_KEYS = ((6, 0x02), (7, 0x10))     # CTRL, STOP
# ⚠️ HOLD IT BRIEFLY. MEASURED: at 1.5 emulated seconds the VG-8020 emits about
# ELEVEN blank lines after leaving the session, which scrolls the AUTO command's
# own echo off a 24-row screen -- so the readout loses its anchor and every
# `aut-` row reads `<NO ECHO>`. The break itself works at both values; only the
# screen differs, which is why this was invisible until the readout was widened
# to span the session (basic_probe_editverb.anchor_for). 0.4 s is ~24 VDP frames,
# far more than any matrix poll needs, and leaves the screen clean.
BREAK_HOLD = 0.4                        # emulated seconds the pair is held down


def is_wait(line) -> bool:
    """True for a `@WAIT<seconds>` pseudo-line (see WAIT_PREFIX). Callers that
    iterate a case's typed lines -- echo guards, screen scrapers, alphabet
    builders -- must skip these: nothing was typed, so nothing can be echoed."""
    return isinstance(line, str) and line.startswith(WAIT_PREFIX)


def is_break(line) -> bool:
    """True for a `@BREAK` pseudo-line. Like `is_wait`, callers that iterate a
    case's typed lines MUST skip these -- nothing is typed, so nothing can be
    echoed and nothing can appear in an alphabet."""
    return isinstance(line, str) and line.startswith(BREAK_PREFIX)

# SCREEN 0 name table (both Philips_VG_8020 and the repack disk machine boot
# 40-column text; a stock SCREEN-1 machine would need 0x1800/768/32 instead).
SCR_ADDR = 0x0000
COLS, ROWS = 40, 24
SCR_LEN = COLS * ROWS

# D-ECHO (docs/spec-probe-echo.md): where in a slot the echo dump is taken --
# after the ROM has consumed and echoed the line, before the next line is
# written. A `puts` callback is atomic w.r.t. the emulated CPU and costs ZERO
# emulated time, so this schedules no new alignment; splitting an injection into
# body-then-CR to get a cleaner window WOULD, which is why it is not done.
ECHO_GAP = 0.8


def echo_guard_on() -> bool:
    """False when `ZEROBAS_ECHOGUARD=off` -- emission AND judgement are skipped
    and the delivered Tcl is byte-identical to the pre-D-ECHO one. Mirrors
    `ZEROBAS_PREFLIGHT=off`: an operator escape hatch that is also the K1 knife."""
    if os.environ.get("ZEROBAS_ECHOGUARD", "").lower() in ("off", "0", "no"):
        if not getattr(echo_guard_on, "_said", False):
            echo_guard_on._said = True
            sys.stderr.write(
                "⚠️  ZEROBAS_ECHOGUARD=off -- the delivery echo guard is "
                "DISABLED; a mangled line will be reported as a value.\n")
        return False
    return True


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


# The longest line a machine will take. 254 characters is MEASURED, not assumed:
# the VG-8020 stores a 254-character line intact and SATURATES there (255, 256,
# 257, 260 and 300 all store exactly 254 -- the tail is dropped, the line is
# kept). See docs/linemax-vg8020-characterization.md §1, probes/basic/
# basic_probe_linemax.py `rem` battery. This was 250 with the comment "holds ~255
# chars incl CR" -- a guess that REFUSED to inject anything longer, so every
# length past it was unreachable rather than tested. A probe that needs to drive
# a machine PAST its ceiling raises this deliberately (that probe does).
MAX_BUF = 254


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
    if isinstance(capture, tuple) and capture and capture[0] == "screen_printer":
        # ("screen_printer", PATH) -> the SCREEN-0 name table, a "7c" ('|')
        # separator, and the whole of openMSX's printer log file so far, all as
        # one hex string (D-EDITVERB).
        #
        # WHY A FILE AND NOT A PORT TRACE. `plug printerport logger` reports
        # READY unconditionally and flushes one byte per strobe edge, so LLIST
        # cannot block and the log is complete the instant the statement ends.
        # The reading is the byte stream the program SENT -- no 40-column wrap,
        # no scroll-off, no cursor, and CR/LF visible as bytes -- which is a
        # strictly better readout than a screen scrape, not a workaround for a
        # worse one.
        #
        # ⚠️ THE LOG ACCUMULATES ACROSS A BATCH AND IS NEVER TRUNCATED. openMSX
        # holds the file open for writing, so truncating it from a second Tcl
        # handle would leave the emulator writing at its old offset into a
        # sparse file. Each case therefore captures the WHOLE log and the probe
        # takes the per-case DELTA, which needs no cooperation from the
        # emulator and cannot desynchronise.
        _, path = capture
        return "[__hex_v %d %d]7c[__file_hex {%s}]" % (SCR_ADDR, SCR_LEN, path)
    if isinstance(capture, tuple) and capture and capture[0] == "vram_segs":
        # ("vram_segs", [(addr,len),...]) -> the segments concatenated as one hex
        # string (Tcl concatenates bracketed exprs inside the "case.N=..." string).
        _, segs = capture
        return "".join(f"[__hex_v {a} {l}]" for a, l in segs)
    raise ValueError(f"unknown capture spec: {capture!r}")


def key_proc() -> str:
    """The Tcl `__key` proc: write the raw bytes of `s` into KEYBUF so CHGET
    delivers them (no CR).

    🔴 IT WRITES AT THE CURRENT GETPNT AND NEVER MOVES GETPNT (D-LATCH,
    docs/spec-probe-latch.md §3.2). The obvious injector -- write at KEYBUF,
    set GETPNT=KEYBUF, PUTPNT=KEYBUF+n -- moves GETPNT BACKWARDS, and that is
    the entire delivery race D-DELIVER and D-ECHO characterised:

      C-BIOS `chget` is  ld hl,(GETPNT) / ld de,(PUTPNT) / rst $20 / ...
                         ^ $1194         ^ $1197

    an `after time` callback that lands on the ONE instruction boundary at
    $1197 leaves HL holding the PRE-injection GETPNT -- which the drained
    predecessor left at KEYBUF+len(that line incl. CR) -- while `ld de` reads
    the fresh PUTPNT. The compare then says "a key is waiting" and `ld a,(hl)`
    starts reading at KEYBUF+N. That is why the swallow count is exactly the
    length of the preceding injection, and why the race is alignment-sensitive:
    one boundary out of a whole `step`. Measured, forced with a breakpoint at
    that address, and 100% -> 0% under this proc (spec §4.2 K1/K5).

    Writing at GETPNT is immune BY CONSTRUCTION, not by alignment: C-BIOS only
    ever holds a stale GETPNT in HL while it still equals its in-memory value,
    so a latched HL points exactly at the first byte written here. The discard
    semantics are unchanged (anything pending is overwritten, PUTPNT is moved
    to the end of the new payload) and so is the 39-byte limit.

    ⚠️ The buffer is CIRCULAR, so successive injections walk it and wrap at
    KEYBUF+KEYBUF_SZ; `chget` wraps on exactly that address. A payload is at
    most MAX_DIRECT+1 = 39 bytes, so `g + i` never exceeds one wrap.

    🔴 AND IT MAY NOT WRITE INTO A BUFFER THE MACHINE IS STILL CONSUMING
    (D-LATCH2, docs/spec-probe-latch2.md §5.5). Writing at GETPNT is immune at
    $1197 but NOT inside `chget_char`:

      $11A2  chget_char  ld a,(hl)       <-- still safe: HL == GETPNT, and the
      $11A3              push af             payload was written AT GETPNT
      $11A4              inc hl          <-- the window: A already holds the
      $11A5              ld a,l              PRE-injection byte, and HL is
      ...                                    about to be stored one PAST the
      $11AD              ld (GETPNT),hl  <-- payload's first byte

    a callback landing anywhere in $11A3..$11AD is overwritten by that store,
    so the machine reads the fresh payload from offset 1 and the head of the
    line is lost. Measured, forced at every boundary: this proc swallowed
    EXACTLY 1 byte at 7 boundaries out of 9, k-independent (the pre-D-LATCH
    injector swallows k there, and D-LATCH's own fix OPENED the `ld hl,KEYBUF`
    wrap sub-window at $11AA, which the pre-D-LATCH body could not reach at
    all -- spec §4.1). The stray leading character is NOT fixable by any
    injector: the machine received it before the injection existed.

    The precondition is exact and it is the whole fix: `chget_char` is reached
    ONLY when GETPNT != PUTPNT, so a NON-DRAINED buffer is the necessary and
    sufficient condition for this window, and both pointers are published
    sysvars readable on ANY machine (a PC-range test would not be: locating
    `chget` in the reference needs a disassembly this project does not do).
    So: while the buffer is non-drained, DEFER.

    ⚠️ THE RETRY BOUND IS LOAD-BEARING, NOT DECORATION. Line 133 records a
    standing contract: during a cassette LOAD/SAVE the harness keeps injecting
    for 10-30 emulated seconds while the machine is NOT reading the keyboard,
    and each __key OVERWRITES whatever is still pending. An UNBOUNDED wait
    would turn that documented collapse into a hang. After KEY_DEFER_MAX
    attempts this injects anyway, restoring the old behaviour exactly -- and
    the states in which the bound is exhausted are the states in which the CPU
    is not inside `chget_char` at all. KEY_DEFER_STEP * KEY_DEFER_MAX must stay
    far below ECHO_GAP (0.8 s), or the echo guard would dump the screen before
    the line it is judging has landed.

    On a DRAINED buffer -- 2039/2039 injections in D-LATCH, 490/490 in
    D-DELIVER -- this defers zero times and costs one extra `debug read
    memory`, which is zero emulated time, so no existing probe's alignment
    moves. `::__zbdefer` / `::__zbforced` count the two paths so a gate can
    prove the guard FIRED rather than merely that it was present
    ([[wired-in-and-silent-tcl-global]])."""
    end = KEYBUF + KEYBUF_SZ
    return (
        "set ::__zbdefer 0\n"
        "set ::__zbforced 0\n"
        "proc __key {s {tries 0}} {\n"
        "  set n [string length $s]\n"
        f"  set g [expr {{[debug read memory {GETPNT}]"
        f" + 256*[debug read memory {GETPNT + 1}]}}]\n"
        # --- the drain guard (D-LATCH2 §5.5) -------------------------------
        f"  set q [expr {{[debug read memory {PUTPNT}]"
        f" + 256*[debug read memory {PUTPNT + 1}]}}]\n"
        "  if {$g != $q} {\n"
        f"    if {{$tries < {KEY_DEFER_MAX}}} {{\n"
        "      incr ::__zbdefer\n"
        f"      after time {KEY_DEFER_STEP} "
        "[list __key $s [expr {$tries + 1}]]\n"
        "      return\n"
        "    }\n"
        "    incr ::__zbforced\n"
        "  }\n"
        "  for {set i 0} {$i < $n} {incr i} {\n"
        "    set a [expr {$g + $i}]\n"
        f"    if {{$a >= {end}}} {{ incr a -{KEYBUF_SZ} }}\n"
        "    debug write memory $a [scan [string index $s $i] %c]\n"
        "  }\n"
        "  set p [expr {$g + $n}]\n"
        f"  if {{$p >= {end}}} {{ incr p -{KEYBUF_SZ} }}\n"
        f"  debug write memory {PUTPNT} [expr {{$p & 0xFF}}]\n"
        f"  debug write memory {PUTPNT + 1} [expr {{($p >> 8) & 0xFF}}]\n"
        "}\n")


def tcl_writes(body: str, addr: int) -> bool:
    """True if this Tcl `body` carries a memory write aimed at `addr`.

    THE WIRE FORMAT BELONGS TO THE MODULE THAT WRITES IT (D-INJSINK,
    docs/spec-probe-injsink.md §3.2). A host test asserting that `key_proc()`
    does not move GETPNT has to know what a write to GETPNT looks like -- and a
    test that RESTATES that format is a file whose string literals compose an
    injector's vocabulary, which is exactly what `make injector-check`
    classifies. D-LATCH2 hit that and closed it with an exemption; the exemption
    was not forced. Stating the format once, here, is the non-evasive close:
    every future assertion-about-the-injector file names this predicate and
    needs no exemption at all.

    🔴 IT RETURNS A BOOL, AND THAT IS WHY IT IS SAFE TO NAME. A *string* exported
    from this module would be a laundering channel -- §2.2 measures one that
    already existed -- because a caller can concatenate a string into the Tcl it
    hands to openMSX. Nothing can be composed out of a predicate.

    The address is a decimal literal in the Tcl this module generates. The
    detector is knifed by its caller: `tests/test_key_drain_guard.py` row R4
    scores it against `latch_check.OLD_KEY`, the frozen pre-D-LATCH body that
    DOES move GETPNT, so a gutted predicate reddens rather than passing
    everything [[coverage-gate-cannot-see-a-gutted-guard]]."""
    return bool(re.search(rf"debug write memory\s+{addr}\b", body))


# --- emulated-time heartbeat (parallel-safety) -------------------------------
# openMSX runs `throttle off`, so the WALL time to reach a scheduled `after time`
# capture varies with how much host CPU the process gets -- on a slow/contended
# core a capture that is fine solo can miss a fixed WALL deadline and read as a
# `None` wedge (docs/spec-probe-emutime-watchdog.md). The kill is therefore gated
# on EMULATED-time PROGRESS, not wall time.
#
# 🔴 THE HEARTBEAT BEATS ON A *WALL* CADENCE (`after realtime`), NOT an emulated
# one. A first cut scheduled beats every N EMULATED seconds -- but under severe
# contention emulation can run below N/HB_STALL realtime, so the beats themselves
# arrive >HB_STALL apart in wall time and the watchdog FALSE-FIRES on a
# slow-but-advancing emulator (it killed graphics-acceptance reference boots).
# `after realtime` fires on the host clock regardless of emulation speed, so a
# beat lands every HB_WALL wall-seconds as long as openMSX's event loop is alive;
# it self-reschedules. A stall (no beat for HB_STALL wall-s) then means the loop
# is TRULY stuck -- a frozen/crashed emulator, or a guest that escaped the timeline
# and dropped every pending callback -- never merely slow. The capture+exit are
# emulated-time `after time` events fired by openMSX independent of guest code, so
# a guest infinite/reset loop still completes at emulated `t`.
# 🔴 EVERY openMSX PROCESS READS AND REWRITES ONE SHARED `settings.xml`, AND
# THAT IS THE PARALLEL BATTERY'S FLAKE. openMSX saves its settings on exit; a
# process STARTING while another is mid-rewrite reads a torn file, refuses to
# boot and exits 1 within 0 s wall:
#
#   Uncaught exception: Failed to parser settings file 'settings.xml':
#   systemID doesn't match (expected 'settings.dtd' got '')
#
# MEASURED 2026-08-25: six of seven full batteries that day recovered a "FLAKE
# (green on retry)", each one a single `<NO CAPTURE>` on a random row and a
# random side, with NOT ONE diagnostic line anywhere -- because openMSX's own
# stderr went to `DEVNULL`. `_why_missing` is what finally printed the sentence
# above, on the very first battery that had it.
#
# 🎯 SO GIVE EACH RUN ITS OWN COPY. `-setting <file>` is openMSX's own knob; the
# user's file is copied in so behaviour is unchanged, and the copy is deleted
# with the rest of the run's temp files. ⚠️ SIDE EFFECT, AND IT IS A GOOD ONE:
# probe runs no longer WRITE the user's openMSX settings. Eight probes fighting
# over a person's config was never intended.
# ⚠️ If the user has no settings file yet there is nothing to copy and nothing
# to tear, so the flag is omitted and openMSX uses its own defaults.
#
# 🔴 AND THE FIRST CUT OF THIS MOVED THE RACE INSTEAD OF REMOVING IT. A plain
# `shutil.copyfile` isolates the DESTINATION and still READS the shared source
# while another openMSX is mid-rewrite of it -- so the run got a torn copy of
# its own and died on that instead, with the temp path in the message:
#
#   Fatal error: Failed to parser settings file '/var/…/repl_XXXX.txt.settings.xml'
#
# Two flakes in the very next battery, found by the diagnosis this same commit
# added. **A copy is a READ.** So the source is read through `_settings_read`,
# which VALIDATES what it got as XML before believing it -- a torn read is not a
# rare event to hope past, it is a return value to check -- and retries briefly,
# because the tear lasts microseconds. If it never validates, the flag is
# omitted: back to today's behaviour, which is no worse, rather than handing
# openMSX a file that is certainly broken.
OMSX_SETTINGS = os.path.expanduser("~/.openMSX/share/settings.xml")
SETTINGS_TRIES = 8

HB_WALL = 3.0            # WALL seconds between heartbeats (host clock, not emulated)
HB_STALL = 90.0          # wall seconds with no heartbeat at all -> declare a hang
HB_ABSCAP = 1800.0       # paranoia backstop (wall s); stall detection is primary


def _tcl(out_path: str, cases: list[tuple[str, list[str]]],
         boot: float, step: float, cap_gap: float,
         reset: tuple[str, ...], capture="screen",
         holds: list[tuple[int, int] | None] | None = None,
         hold_secs: float = 12.0, prologue: tuple[str, ...] = (),
         slots_out: list[tuple[int, str]] | None = None,
         hb_path: str | None = None, settle_n: int = 0,
         sentinel: tuple[int, int] | None = None,
         run_gap: float | None = None,
         sentinel_capture: bool = False,
         # 🔴 D-KWSTOP: **AT THE END, AND KEYWORD-ONLY IN PRACTICE.** The first cut
         # put `hold_lead` beside `hold_secs`, which reads better and SHIFTED EVERY
         # POSITIONAL ARGUMENT AFTER IT: `tests/test_echo_oracle.py` passes
         # `..., None, 12.0, (), slots_out` positionally, so its `slots_out` landed
         # on `prologue` and two echo-guard assertions went red. The test caught a
         # real contract break, so the contract is what changed back.
         hold_lead: float | None = None) -> str:
    """Build the whole-batch Tcl timeline. Each scheduled action gets its own
    emulated-time slot spaced by `step`, so the previous chunk is fully consumed
    (CHGET drains KEYBUF into the line editor) before the next write overwrites
    it. Measured drained before 1794/1794 injections across six batches (D-LATCH).

    `holds` (input-devices arc I1, docs/spec-basic-input-devices.md §8 phase C)
    optionally holds a KEY-MATRIX bit down while a case RUNs: one `(row, mask)`,
    a SEQUENCE of them for a multi-key combo (D-KWSTOP -- Ctrl-STOP is CTRL row 6
    bit $02 plus STOP row 7 bit $10), or None per case, aligned with `cases`. This exists because KEYBUF injection
    -- what every other phase here uses -- writes the decoded characters straight
    into the ROM's buffer and so BYPASSES the matrix entirely; a routine that
    SCANS the matrix (STICK/STRIG via GTSTCK/GTTRIG, and later ON KEY / ON STRIG)
    therefore reads idle no matter what the driver "types". openMSX's
    `keymatrixdown`/`keymatrixup` drive the matrix directly and do reach them.

    The key goes down AFTER the case's last line (which is `RUN` in stored mode)
    and comes up `hold_secs` emulated seconds later, just before the capture -- so
    the sampling loop inside the program sees it held for its whole span. Cases
    with a None hold are unaffected and cost no extra time.

    `prologue` (input-devices arc I2) is raw Tcl run ONCE, immediately, before the
    timeline is scheduled -- the seam for `plug joyporta paddle` and friends. It
    exists because a device that is merely PLUGGED already changes what the
    reference reports (PDL reads 128 for a paddle, PAD(0) reads -1 for an
    arkanoidpad) with no host input at all, which is the only source of teeth the
    PDL/PAD gate has: openMSX offers no mouse, so a value cannot be DRIVEN. The
    connectors exist at script start, so plugging here needs no scheduling. Cheap
    and machine-agnostic; the interrupt-trap arc will want the same seam.

    `slots_out` (D-ECHO, docs/spec-probe-echo.md §3.2) collects one
    `(case_index, typed_text)` record per INJECTION SLOT, in schedule order, and
    each such slot gets an `echo.<k>=` dump at ECHO_GAP into it. The comparison
    downstream is therefore against what this function actually SCHEDULED, not
    against a reconstruction of it -- a reconstruction would have to re-derive
    the chunking and the `10 *` numbering, and would agree with a bug in either."""
    # 🔬 $ZEROBAS_RUN_GAP RAISES EVERY CASE'S RUN->CAPTURE BUDGET, FOR THE
    # BUDGET CONTROL (D-CAPGAP). A suite whose rows are IDENTICAL with and
    # without it had an adequate budget; a row that MOVES was being captured
    # before the machine had finished. That question cannot be answered by
    # reconstructing a suite's cases in a separate driver -- a reconstruction
    # agrees with its own mistakes -- so the switch acts on the REAL suite.
    # 🔴 IT LIVES HERE, NOT IN `_run_cases_impl`, BECAUSE THIS IS THE ONE PLACE
    # THE SCHEDULE IS BUILT. The first cut put it at the `run_cases` entry point
    # and `run_batch` walked straight past it; tests/test_capture_budget.py's
    # R4 caught that before it could make a suite look adequate by not applying.
    # ⚠️ IT ONLY EVER RAISES. The schedule takes max(t, t_run + run_gap), so a
    # case that already asks for more (an explicit `@WAIT`, or a larger
    # `run_gap` at the call site) is untouched and no capture is pulled EARLIER.
    # ⚠️ A TEST-HARNESS SWITCH, NOT A TUNABLE: the runner never sets it.
    _rg = os.environ.get("ZEROBAS_RUN_GAP")
    if _rg:
        try:
            run_gap = max(run_gap or 0.0, float(_rg))
        except ValueError:
            sys.stderr.write(f"⚠️  ZEROBAS_RUN_GAP={_rg!r} is not a number; "
                             f"ignored\n")
    body: list[str] = []
    cap = _cap_expr(capture)
    echo = echo_guard_on() and slots_out is not None
    case_idx = 0
    pre: list[str] = []
    if sentinel_capture:
        # one "already captured" flag per case: the sentinel and the scheduled
        # fallback must not BOTH emit a `case.N=` line -- the host takes the last
        # match, so a late fallback would silently overwrite the sentinel's and
        # reinstate exactly the guessed-time reading this replaces.
        pre += [f"set ::__cap({i}) 0" for i in range(len(cases))]

    def emit(t: float, s: str) -> float:
        """Schedule injection of one CR-terminated line `s` at/after time `t`;
        return the next free time. A line longer than the 40-byte KEYBUF cap is
        CHUNKED into <=MAX_DIRECT pieces written with NO CR until the last -- the
        ROM line editor accumulates them into its own (~255-byte) buffer, so an
        arbitrarily long DIRECT line works without a tokeniser or TXTTAB. (The
        TXTTAB tokenised-injection fallback, spec s2.2, is thus still unneeded.)"""
        if is_wait(s):
            return t + float(s[len(WAIT_PREFIX):])   # advance the clock, type nothing
        if is_break(s):
            for row, mask in BREAK_KEYS:
                body.append(f'after time {t:.1f} {{ keymatrixdown {row} {mask} }}')
                t += 0.5
            t += BREAK_HOLD
            for row, mask in reversed(BREAK_KEYS):
                body.append(f'after time {t:.1f} {{ keymatrixup {row} {mask} }}')
                t += 0.5
            return t + step
        if len(s) > MAX_BUF:
            raise ValueError(f"line exceeds MSX line buffer (~{MAX_BUF}): "
                             f"{len(s)} chars {s!r}")

        def slot(t: float, proc: str, text: str) -> None:
            # remember when the last REAL injection was scheduled -- see
            # `last_inj` below; a trailing `@WAIT` must not move this.
            last_inj[0] = t
            body.append(f'after time {t:.1f} {{ {proc} {{{text}}} }}')
            if echo:
                body.append(f'after time {t + ECHO_GAP * step:.2f} '
                            f'{{ __echo {len(slots_out)} }}')
                slots_out.append((case_idx, text))

        if len(s) <= MAX_DIRECT:
            slot(t, "__inj", s)
            return t + step
        chunks = [s[i:i + MAX_DIRECT] for i in range(0, len(s), MAX_DIRECT)]
        for k, ch in enumerate(chunks):
            # CR only on the last chunk; each chunk is its own slot, and each is
            # judged on its own -- the echo ACCUMULATES, so a chunk's text is a
            # substring of the stream whether or not the line has been submitted.
            slot(t, "__inj" if k == len(chunks) - 1 else "__key", ch)
            t += step
        return t

    # The emulated instant of the LAST REAL INJECTION in the current case.
    # 🔴 IT CANNOT BE DERIVED AS `t - step`. A case may END IN A `@WAIT` (tape
    # cases do, and any case that must let an operation finish before its
    # readout is typed), and a wait advances `t` by its own length -- so
    # `t - step` lands an arbitrary distance PAST the last thing that was typed.
    # Measured: with a trailing `@WAIT120` the sentinel watchpoint armed 117.5
    # emulated seconds late, i.e. after the program had already written its
    # marks, and every timing came back None.
    last_inj = [boot]
    t = boot
    for idx, (mode, lines) in enumerate(cases):
        # a reset line belongs to the case it precedes: a swallowed `NEW` leaks
        # the PREVIOUS case's variables into THIS one, so this one is the reading
        # that was spoiled and this one is what gets re-run.
        case_idx = idx
        for r in reset:                       # power-on-clean vars + DEFtbl + screen
            t = emit(t, r)
        if mode == "stored":
            for ln in [f"{10 * (i + 1)} {ln}" for i, ln in enumerate(lines)]:
                t = emit(t, ln)
            # D-DELIVER: ask the machine what it actually STORED, just before RUN
            # (docs/spec-probe-delivery.md §3.2). Before RUN, so a case whose own
            # program calls NEW/CLEAR cannot erase the evidence -- and before the
            # capture, so a case that never reaches its reporting line is still
            # attributable. A line the screen editor rejected is simply absent
            # from the chain, which is exactly the reading this needs.
            body.append(f'after time {max(boot, t - min(0.4, step / 5)):.2f} '
                        f'{{ puts $__f "prog.{idx}=[__lines {TXTTAB}]"; flush $__f }}')
            t = emit(t, "RUN")
        else:
            for ln in lines:
                t = emit(t, ln)
        # BUDGET INSTRUMENT (docs/spec-probe-budget.md): sample the capture
        # region `settle_n` times across the gap between the LAST injected line
        # (`RUN`, in stored mode) and the capture, so the host can say WHEN the
        # machine actually stopped changing it -- the ACTUAL -- against the
        # scheduled capture -- the BUDGET. Emitted only when asked; a `puts`
        # callback is atomic w.r.t. the emulated CPU and costs ZERO emulated
        # time, so the sampled timeline is the un-sampled one (asserted, not
        # assumed: the instrument's own gate compares captures with it on and
        # off). `run_at`/`cap_at` travel with the samples because a margin is
        # meaningless without the two ends it is measured between.
        # The instant the LAST line (`RUN`, in stored mode) was injected: `emit`
        # has already advanced `t` one `step` past it, and the capture is
        # scheduled at `t` -- so the window a case's budget actually buys between
        # RUN and capture is exactly `step`. (`cap_gap` is the gap AFTER the
        # capture, i.e. inter-case spacing, and buys this case nothing.)
        t_run = last_inj[0]
        # 🔴 `step` USED TO DO DOUBLE DUTY, AND THAT WAS THE EXPENSIVE MISTAKE.
        # It is (a) the inter-line injection spacing that guarantees the previous
        # chunk was consumed -- the drained-buffer property the whole
        # D-LATCH/D-DELIVER apparatus rests on -- and it WAS also (b) the
        # RUN->capture completion budget. A phase that needs a long budget for
        # (b) therefore paid it on EVERY typed line: a graphics PAINT case bought
        # 6 slots x 90 = 540 emulated seconds to cover one 46-second fill.
        # `run_gap` separates them. MEASURED on a bounded PAINT case, capture
        # BYTE-IDENTICAL: 2.9s -> 0.5s on the VG-8020 (5.5x), 1.9s -> 0.5s on
        # zerobas (3.6x), with NO budget made tighter than its measured need --
        # only stopping the completion budget from being charged to the typing.
        #
        # ⚠️ IT IS A *MINIMUM*, AND NEVER PULLS THE CAPTURE EARLIER. A case may
        # end in an explicit `@WAIT`, which advances the clock on purpose so the
        # readout is taken after a long operation (tape rows are built that way).
        # A first cut assigned `t = t_run + run_gap` outright and moved such a
        # case's capture from 45.5 back to 15.5 -- discarding the wait the case
        # asked for. Caught by the byte-identical check against the
        # pre-instrument version, which is exactly what that check is for.
        if run_gap is not None:
            t = max(t, t_run + run_gap)
        hold = holds[idx] if holds else None
        if hold:
            # Press at the RUN slot itself (t - step), not after it: the program
            # starts executing as soon as the line is consumed, so a press one
            # full `step` later can land after a short sampling loop has already
            # finished -- which reads as an idle-vs-held divergence between two
            # machines of different speed rather than as the timing bug it is.
            # 🔴 D-KWSTOP: ONE PAIR **OR A SEQUENCE OF THEM**, because Ctrl-STOP
            # is TWO keys on DIFFERENT MATRIX ROWS (CTRL row 6 bit $02 + STOP
            # row 7 bit $10) and a single `(row, mask)` cannot express it. Every
            # key goes DOWN at the same emulated instant in the order given and
            # comes UP in the REVERSE order -- the modifier is pressed first and
            # released last, which is what basic_probe_stop_trap.py and
            # basic_probe_key_trap.py's `shift_tap` already do by hand.
            # ⚠️ Backward compatible by SHAPE, not by a flag: a 2-tuple of ints
            # is one key, a sequence of pairs is a combo. The input-devices arc's
            # single-key calls are untouched.
            keys = (tuple(hold) if isinstance(hold[0], (tuple, list))
                    else (tuple(hold),))
            # 🔴 D-KWSTOP: `hold_lead` MOVES THE PRESS AFTER THE `RUN`, AND
            # Ctrl-STOP IS WHY. The default below presses one STEP EARLY, which is
            # right for a key the program SAMPLES -- but the reference's ROM FLUSHES
            # THE TYPE-AHEAD BUFFER while Ctrl-STOP is down, so a press that early
            # ate every injected line and the VG-8020 came back with a COMPLETELY
            # BLANK SCREEN: no program, no `RUN`, nothing. (zerobas does not flush,
            # so ITS side of the same run typed and ran normally -- an apparatus
            # asymmetry that reads exactly like a divergence.) A positive
            # `hold_lead` presses that many seconds AFTER the RUN slot, once the
            # line has been consumed and the program is already looping.
            down = (max(boot, t - step) + 0.3 if hold_lead is None
                    else t + hold_lead)
            for row, mask in keys:
                body.append(f'after time {down:.1f} '
                            f'{{ keymatrixdown {row} {mask} }}')
            t += hold_secs
            for row, mask in reversed(keys):
                body.append(f'after time {t:.1f} {{ keymatrixup {row} {mask} }}')
            t += 1.0
        if settle_n > 0 and t > t_run:
            # `settle_n` LOG-SPACED samples over (t_run, t]: the window the
            # budget actually buys. Each records the emulated instant and the
            # capture region itself, so the host finds the LAST sample at which
            # the region still changed -- everything after it is pure margin.
            #
            # 🔴 LOG-SPACED, NOT EVEN, AND THAT IS THE DIFFERENCE BETWEEN A
            # MEASUREMENT AND A RESOLUTION ARTEFACT. An even grid over a 90 s
            # window samples first at 2.25 s -- but the operations these budgets
            # are sized for finish FAR inside that, so every sample came back
            # identical and the readout printed "used 2.25 s / 2.5%" for both a
            # circle draw and a text error: not a reading of the work, a reading
            # of the grid. Log spacing puts the first sample at window/1000 and
            # keeps ~3 decades of resolution where fast cases actually settle,
            # while still reaching the far end for the slow ones.
            for k in range(1, settle_n + 1):
                ts = t_run + (t - t_run) * 10.0 ** (-3.0 * (1 - k / settle_n))
                body.append(f'after time {ts:.3f} {{ puts $__f '
                            f'"settle.{idx}.{k}={ts:.3f},{cap}"; flush $__f }}')
            body.append(f'after time {t:.3f} {{ puts $__f '
                        f'"span.{idx}={t_run:.3f},{t:.3f}"; flush $__f }}')
        if sentinel is not None:
            # 🕐 A PROGRAM-DRIVEN EMULATED-TIME STOPWATCH (docs/spec-probe-mark.md).
            # `POKE <addr>,<v>` from the case's own BASIC, watched here, logs the
            # EXACT emulated instant of each write. Mark before an operation and
            # after it and the delta is that operation's precise duration -- on
            # the black-box reference machines too, because this watches emulated
            # RAM and so needs no ROM knowledge anywhere.
            #
            # 🔴 ON ITS OWN IT ONLY *READS* THE CLOCK; `sentinel_capture`
            # BELOW IS WHAT MOVES THE CAPTURE. Keep the two apart when reading
            # this: a probe may want the emulated stopwatch and NOT want its
            # capture rescheduled. Reading the clock is where the first value
            # turned out to be, and it is risk-free: EMULATED time is
            # DETERMINISTIC -- measured bit-identical across repeats
            # (14.736728 s twice, 46.252527 s twice) -- so it is the only basis
            # on which a performance differential can be gated without flaking,
            # which wall-clock timing can never offer.
            # 🔴 ARM IT AT THE `RUN` SLOT, NOT AT SCRIPT START. MEASURED: with
            # the watchpoint created up front it fired at emulated t=0.458 on
            # BOTH references -- during their BOOT, hundreds of emulated seconds
            # before `RUN` -- because they write the sentinel address while
            # sizing/clearing RAM, so the capture read a booting screen. Hunting
            # for an address no ROM ever touches is not a contract anyone can
            # keep; arming AFTER the program starts is, and it makes the choice
            # of address nearly free. (The value test stays as a second filter.)
            # 🔴 ARM IT AT THE LAST INJECTION, NOT AT SCRIPT START. MEASURED:
            # created up front it fired at emulated t=0.458 on BOTH references --
            # during their BOOT -- because they write this address while
            # sizing/clearing RAM, so it timed the boot instead of the program.
            # Hunting for an address no ROM ever touches is not a contract anyone
            # can keep; arming after the program starts is, and it makes the
            # choice of address nearly free.
            s_addr, s_val = sentinel
            # `sentinel_capture` additionally CAPTURES when the program signals,
            # turning the scheduled capture below into the pure FAILURE detector
            # it should always have been -- so the budget stops being a guess
            # that fires whether or not the work finished.
            #
            # ⚠️ THE `capture="screen"` REFUSAL THAT USED TO BE STATED HERE WAS
            # LIFTED 2026-08-25 -- see `_run_batch`, which carries the whole
            # note and the burden that replaced it. The MEASUREMENT is unchanged
            # and still worth knowing at this line: byte-identical for VRAM
            # captures (9/9), and text captures differ by exactly 2 characters
            # on all three machines -- the `Ok`/`ZB` PROMPT, which the
            # interpreter has not printed yet when the program signals. What
            # changed is the conclusion drawn from it: a readout that already
            # strips the prompt is unaffected, and one that TERMINATES at the
            # prompt (`screen_tail`) may not be converted.
            grab = (f'      set ::__cap({idx}) 1\n'
                    f'      puts $__f "case.{idx}={cap}"\n'
                    f'      puts $__f "sentinel.{idx}=[machine_info time]"\n'
                    f'      flush $__f\n'
                    # Capturing early reclaims nothing unless the run also ENDS --
                    # the timeline still holds a scheduled exit at the far end.
                    # Only on the LAST case: in a shared boot the later cases are
                    # scheduled at fixed times and would be aborted.
                    + (f'      close $__f\n      exit\n'
                       if idx == len(cases) - 1 else ''))
            body.append(
                f'after time {t_run:.3f} {{\n'
                f'  debug set_watchpoint write_mem {s_addr} {{}} {{\n'
                f'    puts $__f "mark.{idx}=[machine_info time],$::wp_last_value"\n'
                f'    flush $__f\n'
                + (f'    if {{$::wp_last_value == {s_val} && !$::__cap({idx})}} {{\n'
                   + grab + '    }\n' if sentinel_capture else '')
                + f'  }}\n'
                f'}}')
        if sentinel_capture:
            body.append(f'after time {t:.1f} {{ if {{!$::__cap({idx})}} {{ '
                        f'set ::__cap({idx}) 1; puts $__f "case.{idx}={cap}"; '
                        f'puts $__f "fallback.{idx}=[machine_info time]"; '
                        f'flush $__f }} }}')
        else:
            body.append(f'after time {t:.1f} {{ puts $__f "case.{idx}='
                        f'{cap}"; flush $__f }}')
        t += cap_gap
    # wall-cadence heartbeat (see HB_* above): __hb self-reschedules on the HOST
    # clock, so the watchdog's mtime always updates every HB_WALL s unless openMSX
    # itself is stuck -- immune to how slow emulation runs under contention.
    if hb_path:
        body.append("after realtime 0 __hb")
    body.append(f"after time {t:.1f} {{ close $__f; exit }}")
    # A REDUNDANT emulated-time safety-exit a margin past the real one. The primary
    # exit above is guest-independent (openMSX fires `after time` from its own
    # scheduler, so a BASIC/ROM infinite loop cannot suppress it), but if that
    # callback were ever dropped this bounds the run in EMULATED time regardless of
    # host speed -- the guest can loop forever and openMSX still self-terminates.
    # Host FREEZES (emulated clock stops) are caught by the wall-side stall watchdog.
    body.append(f"after time {t + 30.0:.1f} {{ catch {{close $__f}}; exit }}")
    return (
        "set throttle off\n"
        + "".join(f"{p}\n" for p in prologue)
        + f"set __f [open {{{out_path}}} w]\n"
        "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
        " return $h }\n"
        "proc __hex_m {a l} { binary scan [debug read_block memory $a $l] H* h;"
        " return $h }\n"
        # __file_hex: a HOST file as hex -- the printer-log readout (D-EDITVERB).
        # A missing file is the empty string, which is DATA ("the machine printed
        # nothing"), not a failure: it is the correct reading for `LLIST 30-20`.
        "proc __file_hex {p} {\n"
        "  if {[catch {set h [open $p rb]; set d [read $h]; close $h}]} { return {} }\n"
        "  binary scan $d H* x; return $x\n"
        "}\n"
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
        # __lines: the stored program's LINE NUMBERS, comma-joined -- the
        # delivery oracle (docs/spec-probe-delivery.md §3.2). Walks the
        # line-link chain from the text base at $p; an empty program returns "".
        # The 128-iteration cap and the non-advancing-link break are so a
        # corrupted chain cannot spin the emulator instead of reporting.
        "proc __lines {p} {\n"
        "  set cur [expr {[debug read memory $p] + 256*[debug read memory [expr {$p+1}]]}]\n"
        "  set out {}\n"
        "  for {set i 0} {$i < 128} {incr i} {\n"
        "    set link [expr {[debug read memory $cur] + 256*[debug read memory [expr {$cur+1}]]}]\n"
        "    if {$link == 0} { break }\n"
        "    lappend out [expr {[debug read memory [expr {$cur+2}]] +"
        " 256*[debug read memory [expr {$cur+3}]]}]\n"
        "    if {$link <= $cur} { break }\n"
        "    set cur $link\n"
        "  }\n"
        "  return [join $out ,]\n"
        "}\n"
        # __echo: one injection slot's delivery evidence -- the screen mode, the
        # width of the text window, and the SCREEN-0 name table (D-ECHO,
        # docs/spec-probe-echo.md §3.2). SCRMOD and LINLEN travel WITH the dump
        # because both differ per machine and per moment: the reference runs a
        # 37-column window, zerobas a 39-column one, and a case left in SCREEN 2
        # by an untrapped error makes this scrape read the pattern generator
        # table instead of any text at all.
        # ⚠️ `global __f` IS LOAD-BEARING. Every other emission here is written
        # from an `after time` body, which runs in the global scope where `$__f`
        # resolves; inside a proc it does not, the proc errors, and openMSX drops
        # the callback WITHOUT A WORD -- the guard then reports nothing at all
        # while its emission and its call site are both plainly present. That is
        # the K2 shape by accident, and only the cross-oracle disagreement check
        # (§3.5) caught it.
        + (f"proc __echo {{k}} {{ global __f; puts $__f \"echo.$k="
           f"[debug read memory {SCRMOD}],[debug read memory {LINLEN}],"
           f"[__hex_v {SCR_ADDR} {SCR_LEN}]\"; flush $__f }}\n" if echo else "")
        + key_proc()
        # __inj: __key plus the submitting CR (appended here so a literal CR byte
        # never has to survive Tcl brace-quoting).
        + "proc __inj {s} { append s \"\\r\"; __key $s }\n"
        # __hb: rewrite the heartbeat file, then RE-ARM on the WALL clock. The host
        # watchdog watches this file's MTIME: a beat that stops arriving means the
        # emulator's event loop is stuck -- a frozen/crashed emulator OR a guest
        # that escaped the timeline and dropped its callbacks -- both must be
        # killed. Beating on `after realtime` (not `after time`) keeps the cadence
        # on the host clock, so a merely SLOW emulator still beats and is not
        # killed. `catch` so a transient write error never derails the run.
        + (f"proc __hb {{}} {{ catch {{set __h [open {{{hb_path}}} w];"
           f" puts $__h [machine_info time]; close $__h}};"
           f" after realtime {HB_WALL:g} __hb }}\n" if hb_path else "")
        + "".join(f"{p}\n" for p in pre)
        + "\n".join(body) + "\n")


def run_case(machine: str, mode: str, lines: list[str], **kw) -> str | None:
    """Boot `machine` and drive ONE case (`mode`, `lines`), returning its raw
    SCREEN-0 name-table string (or None on capture failure). THE DEFAULT ENTRY
    POINT: one boot per case = power-on-fresh vars + DEFtbl, matching the
    matrix-typing harness this replaces (differential-inert). See module docstring
    on why batching is unsafe on the current zerobas build."""
    return run_batch(machine, [(mode, lines)], reset=(), **kw)[0]


def _settings_read() -> str | None:
    """The user's openMSX settings, read WHOLE -- or None.

    🔴 A COPY IS A READ, AND THE SOURCE IS THE CONTENDED FILE. Every openMSX
    rewrites `~/.openMSX/share/settings.xml` on exit, so reading it during a
    parallel battery can return a torn document; handing that to openMSX as a
    private `-setting` file just relocates the crash (measured: two flakes,
    naming the temp path). A torn read is not a rare event to hope past -- it is
    a return value, and this checks it. `fromstring` is the exact test openMSX
    itself will apply, not a heuristic about the first and last line."""
    for _ in range(SETTINGS_TRIES):
        try:
            blob = open(OMSX_SETTINGS, encoding="utf-8", errors="strict").read()
        except OSError:
            return None                 # no settings file at all: nothing to tear
        try:
            if ElementTree.fromstring(blob).tag == "settings":
                return blob
        except ElementTree.ParseError:
            pass
        time.sleep(0.02)                # the tear lasts microseconds
    return None                         # never clean: omit the flag, as before


def _rm(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _why_missing(machine: str, got: int, want: int, killer: str | None,
                 rc: int, elapsed: float, out_lines: int, err_path: str,
                 hb_emu: float | None = None,
                 hb_rate: float | None = None) -> str:
    """ONE line naming WHY a capture is missing -- the evidence the run already
    held and used to throw away.

    🔴 `<NO CAPTURE>` IS THE SAME STRING FOR AT LEAST FOUR DIFFERENT EVENTS, and
    which one it was decides what to do next:

      stall     the heartbeat stopped. ⚠️ NOT automatically REAL: a host-clock
                deadline cannot tell a FROZEN emulator from a STARVED one, so
                this line now reports the last EMULATED instant and its ratio to
                wall time. Emulated time advancing means a contended host.
      abscap    the paranoia backstop -- the run was merely enormous.
      exit N    openMSX terminated ON ITS OWN before its scheduled capture:
                a crash, a bad machine, a busy or missing disk image. Its own
                message is quoted, because it usually says exactly which.
      exit 0    openMSX ran to completion and the capture callback never fired
                -- the guest escaped the timeline, or the schedule is wrong.

    ⚠️ AND THE FOURTH IS THE ONE THAT MATTERS: a case whose MACHINE genuinely
    wedges looks, to `tools/run_gates.py`, exactly like a contention flake, and
    its retry turns it green and prints "FLAKE". Nothing else in the tree can
    tell those apart, so this line is what a red gate is read with."""
    tail = ""
    try:
        txt = open(err_path, errors="replace").read().strip()
        if txt:
            last = [l for l in txt.splitlines() if l.strip()][-3:]
            tail = "  emulator said: " + " | ".join(last)[:300]
    except OSError:
        pass
    if killer:
        cause = f"the {killer} watchdog killed it after {elapsed:.0f}s wall"
        if killer == "stall":
            # 🔴 THIS USED TO ASSERT "a stall is a FROZEN OR CRASHED emulator,
            # NOT A SLOW ONE -- the heartbeat is on the HOST clock", and that is
            # the one thing a host-clock deadline cannot know. The reasoning is
            # recorded at the HB_* block above: a FIRST design beat on EMULATED
            # time and false-fired on a slow-but-advancing emulator, so it moved
            # to `after realtime` -- which lands "regardless of emulation speed
            # ... as long as the event loop is ALIVE". That holds only if the
            # process is SCHEDULED. The dependency moved from emulation speed to
            # process scheduling; both fail under host contention.
            # 🎯 MEASURED 2026-08-26 (D-DRAWOP): two batteries at 3509s and
            # longer against a normal ~420s, 20 stall kills, two DIFFERENT
            # machines killed at the same 947s deadline to the second -- and
            # runs that had written 1886, 90 and 88 LINES before being declared
            # frozen. A frozen emulator does not write 1886 lines. The refutation
            # was already printed in the same sentence as the claim.
            # So: report the emulated instant, which actually separates them,
            # and let the reader conclude.
            # 🔴 AND THE REPLACEMENT IS EVIDENCE, NOT A DIFFERENT ASSERTION.
            # The first cut here classified on a RATE THRESHOLD -- "emulated/wall
            # > 0.02 means starved" -- and its own falsification vector killed
            # it: 12.4 emulated seconds in 947 wall is 0.013x, plainly ADVANCING
            # and plainly below the line. The LAST beat's value cannot separate
            # "froze at emulated 12.4s" from "starved at emulated 12.4s"; only a
            # DELTA could, and the watchdog keeps no previous value. A threshold
            # invented to look decisive is the same defect as the sentence it
            # replaced, one layer along.
            # 🎯 So state the two fields that bear on it and stop. `out_lines` is
            # already in this message and is the strongest liveness signal there
            # is: the runs that provoked this had written 1886, 90 and 88 lines.
            emu = (f"last beat at emulated {hb_emu:.1f}s"
                   f" ({hb_emu / elapsed:.3f}x over the whole run)"
                   if hb_emu is not None and hb_emu == hb_emu and elapsed > 0
                   else "no emulated instant was recorded")
            # 🎯 D-STALLRATE: THE FIGURE THAT ACTUALLY SEPARATES THEM. The rate
            # over the FINAL beat interval says what emulation was doing in the
            # moment before it went quiet; the whole-run average above cannot,
            # because a fast boot then a freeze averages to the same place as a
            # slow crawl throughout.
            if hb_rate is None:
                rate = ("fewer than two beats arrived, so there is no final"
                        " interval to rate -- this run was killed during boot")
            elif hb_rate < 0.05:
                rate = (f"the final beat interval ran at {hb_rate:.3f}x realtime"
                        f" -- emulation was ALREADY CRAWLING when the beats"
                        f" stopped, which is what a STARVED host looks like")
            else:
                rate = (f"the final beat interval ran at {hb_rate:.3f}x realtime"
                        f" -- emulation was HEALTHY and then stopped, which is"
                        f" what a genuine freeze or crash looks like")
            cause += (f"  ({emu}; {rate}; a host-clock deadline CANNOT by itself"
                      f" separate a frozen emulator from one starved of CPU --"
                      f" read those figures and the line count below together,"
                      f" and check host load before calling this REAL)")
    elif rc:
        sig = f"signal {-rc}" if rc < 0 else f"exit {rc}"
        cause = (f"openMSX terminated ON ITS OWN ({sig}) after {elapsed:.0f}s "
                 f"wall, before its scheduled capture")
    else:
        cause = (f"openMSX exited CLEANLY (0) after {elapsed:.0f}s wall without "
                 f"writing the capture -- the callback never fired")
    return (f"omsx_repl: {want - got} of {want} capture(s) MISSING on {machine} "
            f"-- {cause}; the run wrote {out_lines} line(s).{tail}")


def _run_batch(machine: str, cases: list[tuple[str, list[str]]], *,
               boot: float = 8.0, step: float = 2.5, cap_gap: float = 2.5,
               reset: tuple[str, ...] = (), capture="screen",
               holds: list[tuple[int, int] | None] | None = None,
               hold_secs: float = 12.0, hold_lead: float | None = None,
               prologue: tuple[str, ...] = (),
               timeout: float = 240.0, omsx: str | None = None,
               cart: str | None = None, diska: str | None = None,
               cassette: str | None = None,
               stall: float | None = None, abscap: float | None = None,
               settle_n: int = 0, settle_out: dict | None = None,
               sentinel: tuple[int, int] | None = None,
               run_gap: float | None = None, sentinel_capture: bool = False
               ) -> tuple[list[str | None], dict[int, list[int]], list]:
    """One boot, `cases` driven, returning `(captures, delivered, echo)` -- the
    raw engine. `delivered` maps a stored-mode case index to the line-number
    chain the machine actually held (D-DELIVER); `echo` is the D-ECHO verdict
    list, one entry per injection slot (empty when the guard is off). Callers go
    through `run_batch` (which verifies and refuses) or `run_cases` (which
    verifies and repairs).

    Boot `machine` once and drive `cases` (each `(mode, lines)`), returning one
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
    if sentinel_capture:
        if sentinel is None:
            raise SystemExit("omsx_repl: sentinel_capture needs a sentinel")
        # 🟢 THE `capture="screen"` REFUSAL WAS LIFTED 2026-08-25 (user decision).
        # It was measured, and it was WEIGHED WRONG. The measurement stands: the
        # sentinel fires before the interpreter prints its `Ok`/`ZB` prompt and
        # `screen_tail` terminates AT that prompt, so a RAW text capture differs
        # by exactly those 2 characters on all three machines.
        # 🔴 BUT THOSE 2 CHARACTERS ARE THE ONE THING EVERY TEXT READOUT ALREADY
        # THROWS AWAY. basic_probe_graphics `_answer()` says so in its own
        # docstring -- "the trailing BASIC prompt / 'Ok' / 'No RESUME' text
        # (which differs per machine) is ignored" -- and `_points` is built on it.
        # A capture taken BEFORE the prompt is not a degraded reading of the same
        # screen; it is the screen WITHOUT the machine-specific noise the
        # readouts exist to strip. `screen_tail` terminating at the prompt is a
        # property of the TERMINATOR, not evidence the reading is wrong.
        # ⚠️ THE BURDEN MOVED, IT DID NOT VANISH: a probe adopting this for a
        # screen capture must show its OWN readout is prompt-independent, with a
        # differential taken AFTER normalisation and carrying a teeth control
        # (scratchpad/sentinel_screen_diff.py). Comparing RAW screens will still
        # differ by 2 characters, by construction, and that is not a defect.
    binary = find_omsx(omsx)
    out = tempfile.NamedTemporaryFile(suffix=".txt", prefix="repl_", delete=False).name
    tcl = out + ".tcl"
    hb = out + ".hb"                     # emulated-time heartbeat (parallel-safety)
    # 🔴 EVERY TEMP NAME IN THIS FUNCTION IS `out` OR `out + <suffix>`, AND THEY
    # USED TO BE UNLINKED ONE BY ONE ON THE SUCCESS PATH ONLY. Anything that
    # raised in between leaked all five -- and one of them raises by design:
    # `omsx_preflight.guarded()` refuses a bad machine at the `Popen` call, after
    # the Tcl has been written. Measured: 44 orphaned `repl_*` files, mostly
    # `.tcl`. Small, but it is the same class as the 1.1 GB of `zb_*` that
    # `probe_tmp` was written for, and the same answer -- sweep, do not enumerate.
    try:
        slots: list[tuple[int, str]] = []
        with open(tcl, "w") as f:
            f.write(_tcl(out, cases, boot, step, cap_gap, reset, capture,
                         holds, hold_secs, prologue, slots,
                         hold_lead=hold_lead, hb_path=hb,
                         settle_n=settle_n, sentinel=sentinel, run_gap=run_gap,
                         sentinel_capture=sentinel_capture))
        for p in (out, hb):
            if os.path.exists(p):
                os.unlink(p)

        settings = out + ".settings.xml"    # see OMSX_SETTINGS: the parallel flake
        blob = _settings_read()
        if blob is None:
            settings = None
        else:
            with open(settings, "w") as sf:
                sf.write(blob)

        cmd = [binary, "-machine", machine]
        if settings:
            cmd += ["-setting", settings]
        if cart:
            cmd += ["-cart", cart]
        if diska:
            cmd += ["-diska", diska]
        if cassette:
            # 🔴 D-CASORACLE (2026-09-13): THE COMMAND-LINE FORM, AND IT IS NOT THE
            # SAME AS THE Tcl ONE. A tape mounted from a `prologue` with
            # `cassetteplayer <file>` is read by zerobas's repack machine and by
            # NEITHER reference: VG-8020 and CF-3300, `CLOAD` and `LOAD"CAS:"`, on a
            # clean-room `.cas` AND on a WAV zerobas recorded itself, all silent
            # (scratchpad/kwdrain_casoracle*.out). Every cassette probe in this tree
            # passes `-cassetteplayer` HERE instead -- and every one of them runs on
            # the repack machine only, so the difference had never been tested
            # against a reference. This is that seam, added so it can be.
            cmd += ["-cassetteplayer", cassette]
        cmd += ["-command", "set renderer none; set sound_driver null", "-script", tcl]

        # 🔴 openMSX's OWN OUTPUT USED TO GO TO `DEVNULL`, AND SO DID THE ONE
        # QUESTION AN OPERATOR ACTUALLY ASKS. A missing capture surfaces as
        # `<NO CAPTURE>`, which is the same string for at least four different
        # events: the stall watchdog fired, the abscap backstop fired, openMSX died
        # on its own, or the guest genuinely wedged. Four flakes measured across six
        # batteries on 2026-08-25 were each ONE `<NO CAPTURE>`, on a random row and
        # a random side, with NOT ONE diagnostic line in any log -- and the retry in
        # `tools/run_gates.py` turned every one of them green and printed "FLAKE".
        # A row that wedges for a REAL reason is indistinguishable from that.
        # So: keep the emulator's stderr, keep its exit status, and spend both when
        # (and only when) a capture goes missing. See `_why_missing` below.
        err = out + ".err"
        with open(err, "w") as ef:
            proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=ef,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        # EMULATED-TIME watchdog (docs/spec-probe-emutime-watchdog.md). openMSX runs
        # `throttle off`, so wall-time to reach a scheduled capture is host-speed-
        # dependent -- a fixed wall deadline SIGKILLs slow/contended (or E-core) runs
        # mid-timeline and reads as a `None` wedge, which is what broke the parallel
        # battery. Instead: kill only when the heartbeat file stops ADVANCING for
        # `stall` wall-seconds (a frozen/crashed emulator, or a guest that escaped the
        # scheduled timeline and dropped its callbacks), never for merely running slow.
        # A guest infinite loop / reset loop can't hang the run: the capture+exit are
        # openMSX `after time` events fired from its own scheduler, independent of guest
        # code. `abscap` is a generous final backstop only. Env overrides:
        # ZEROBAS_OMSX_STALL / ZEROBAS_OMSX_ABSCAP.
        stall_s = float(os.environ.get("ZEROBAS_OMSX_STALL", stall if stall is not None else HB_STALL))
        abscap_s = max(timeout, float(os.environ.get("ZEROBAS_OMSX_ABSCAP",
                                                     abscap if abscap is not None else HB_ABSCAP)))
        start = time.time()
        last_beat = now = start             # wall time of the most recent heartbeat
        last_mtime = None                   # (`now` pre-bound: the loop may not run)
        # 🔴 D-STALLRATE: KEEP THE LAST **TWO** BEATS, VALUE AND WALL TIME. Until
        # now the loop watched only the file's MTIME and the kill message read the
        # file's CONTENT once, at the end -- so it could report the last emulated
        # instant but not whether emulation was ADVANCING when the beats stopped.
        # D-STALLSLOW's first cut tried to get that from the single last value via
        # a rate threshold and its own falsification vector killed it: 12.4
        # emulated seconds in 947 wall is 0.013x, plainly advancing and plainly
        # below any line drawn there. The LAST value cannot separate "froze at
        # 12.4s" from "starved at 12.4s". Two consecutive beats can: they give the
        # INSTANTANEOUS emulation rate in the moment before the beats stopped.
        #   ~1x then silence  -> the emulator was healthy and then stopped: a
        #                        genuine freeze or crash, and the kill is REAL.
        #   ~0.01x then silence -> it was already crawling: the host was starving
        #                        it, and the kill is contention, not a defect.
        # ⚠️ THE WHOLE-RUN AVERAGE ALREADY IN THE MESSAGE CANNOT DO THIS. It
        # divides the last instant by total wall, so a fast boot followed by a
        # freeze and a slow crawl throughout average to similar figures.
        beats: list[tuple[float, float]] = []   # (emulated instant, wall time)
        while proc.poll() is None:
            time.sleep(0.05)
            now = time.time()
            try:
                m = os.path.getmtime(hb)
            except OSError:
                m = None
            if m is not None and m != last_mtime:
                last_mtime, last_beat = m, now
                try:
                    v = float(open(hb).read().strip() or "nan")
                except (OSError, ValueError):
                    v = float("nan")
                if v == v:                       # not NaN
                    beats.append((v, now))
                    del beats[:-2]               # only the last two are ever read
            if now - last_beat > stall_s or now - start > abscap_s:
                break
        timed_out = proc.poll() is None
        killer = None
        if timed_out:
            # WHICH watchdog. They mean different things -- a stall is a frozen or
            # crashed emulator, an abscap is a run that was merely far too long --
            # and "killed" alone tells the operator neither.
            killer = ("stall" if now - last_beat > stall_s else "abscap")
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        rc = proc.wait()
        elapsed = time.time() - start
        # D-STALLSLOW: the heartbeat file's CONTENT is `[machine_info time]` --
        # the EMULATED instant of the last beat -- and until now only its MTIME
        # was ever read. That threw away the one field that separates a FROZEN
        # emulator from a STARVED one, which is exactly the distinction the kill
        # message went on to assert. Read it before unlinking.
        hb_emu = None
        if os.path.exists(hb):
            try:
                hb_emu = float(open(hb).read().strip() or "nan")
            except (OSError, ValueError):
                pass
            os.unlink(hb)
        # D-STALLRATE: the instantaneous rate over the FINAL beat interval, or
        # None when fewer than two beats ever arrived (a run killed during boot
        # has no interval, and saying so is better than dividing by zero).
        hb_rate = None
        if len(beats) == 2:
            d_emu, d_wall = beats[1][0] - beats[0][0], beats[1][1] - beats[0][1]
            if d_wall > 0:
                hb_rate = d_emu / d_wall

        caps: dict[int, str] = {}
        delivered: dict[int, list[int]] = {}
        echoes: dict[int, tuple[int, int, str]] = {}
        out_lines = 0                       # what the run DID write, for _why_missing
        if os.path.exists(out):
            out_lines = sum(1 for _ in open(out))
            for ln in open(out):
                d = re.match(r"prog\.(\d+)=([\d,]*)$", ln.strip())
                if d:                              # D-DELIVER: what the machine STORED
                    delivered[int(d.group(1))] = [
                        int(x) for x in d.group(2).split(",") if x]
                    continue
                if settle_out is not None:
                    s = re.match(r"settle\.(\d+)\.(\d+)=([\d.]+),([0-9a-f]*)$",
                                 ln.strip())
                    if s:                          # BUDGET INSTRUMENT: one sample
                        settle_out.setdefault("samples", {}).setdefault(
                            int(s.group(1)), []).append(
                                (float(s.group(3)), s.group(4)))
                        continue
                    sp = re.match(r"span\.(\d+)=([\d.]+),([\d.]+)$", ln.strip())
                    if sp:                         # the window the budget bought
                        settle_out.setdefault("span", {})[int(sp.group(1))] = (
                            float(sp.group(2)), float(sp.group(3)))
                        continue
                mk = re.match(r"mark\.(\d+)=([\d.]+),(\d+)$", ln.strip())
                if mk:      # (emulated instant, value) for every sentinel write
                    if settle_out is not None:
                        settle_out.setdefault("marks", {}).setdefault(
                            int(mk.group(1)), []).append(
                                (float(mk.group(2)), int(mk.group(3))))
                    continue
                fb = re.match(r"fallback\.(\d+)=([\d.]+)$", ln.strip())
                if fb:      # the sentinel did NOT fire; the budget captured instead
                    if settle_out is not None:
                        settle_out.setdefault("fallback", {})[int(fb.group(1))] = \
                            float(fb.group(2))
                    continue
                sn = re.match(r"sentinel\.(\d+)=([\d.]+)$", ln.strip())
                if sn:      # the case ANNOUNCED completion; emulated time it fired
                    if settle_out is not None:
                        settle_out.setdefault("sentinel", {})[int(sn.group(1))] = \
                            float(sn.group(2))
                    continue
                e = re.match(r"echo\.(\d+)=(\d+),(\d+),([0-9a-f]*)$", ln.strip())
                if e:                              # D-ECHO: what the machine ECHOED
                    # ⚠️ decoded EXACTLY as the `screen` capture is -- non-print ->
                    # blank -- so the comparison sees the same characters a probe's
                    # readout does. The cursor is a live cell in the name table and
                    # decodes to a blank on both machines.
                    raw = bytes.fromhex(e.group(4))
                    echoes[int(e.group(1))] = (
                        int(e.group(2)), int(e.group(3)),
                        "".join(chr(b) if 32 <= b < 127 else " " for b in raw))
                    continue
                m = re.match(r"case\.(\d+)=([0-9a-f]*)", ln.strip())
                # An EMPTY capture is DATA, not a missing one. `__hex_line` returns ""
                # for an empty program -- i.e. "the line was REFUSED on entry", which
                # is a behaviour a probe has to be able to read. Dropping it here
                # collapsed that into the None a probe also gets when the machine
                # never reached the capture at all (a wedge), so the two were
                # indistinguishable; D-LINEMAX needs them apart. Callers that folded
                # both together (`if not raw`) are unaffected.
                if m:
                    if capture == "screen":
                        data = bytes.fromhex(m.group(2))
                        caps[int(m.group(1))] = "".join(
                            chr(b) if 32 <= b < 127 else " " for b in data)
                    else:                      # mem capture: hand back the raw hex
                        caps[int(m.group(1))] = m.group(2)
        if len(caps) < len(cases):
            why = _why_missing(machine, len(caps), len(cases), killer, rc, elapsed,
                               out_lines, err, hb_emu, hb_rate)
            if timed_out and not caps:
                raise SystemExit(why)
            sys.stderr.write(why + "\n")
        return ([caps.get(i) for i in range(len(cases))], delivered,
                echo_verdicts(slots, echoes))
    finally:
        # by GLOB, so a suffix added later is covered without editing this line.
        for _p in glob.glob(out + "*"):
            _rm(_p)
        _rm(out)


# --- D-DELIVER: the stored-program delivery oracle --------------------------
# docs/spec-probe-delivery.md. A batched case whose program the machine did not
# store AS TYPED has produced no reading: the two standing graphics-acceptance
# reds were one case that lost `10 ON ERROR GOTO 40` (its ERR then went
# UNTRAPPED, leaving the machine in SCREEN 2, whose zeroed pattern table the
# SCREEN-0 scrape reads as 960 blanks) and one that lost its `PRINT"ZK"` line
# (falling through into the handler, which printed the PREVIOUS case's ERR).
# Both looked like semantics on both sides. Neither was.


def expected_lines(mode: str, lines: list[str]) -> list[int] | None:
    """The line-number chain `_tcl` types for a case, or None when the case has
    no stored program to interrogate (`direct` mode -- an unguarded class, §9.3)."""
    return [10 * (i + 1) for i in range(len(lines))] if mode == "stored" else None


def mis_delivered(cases, delivered: dict[int, list[int]]) -> list[tuple[int, list, list]]:
    """`(index, typed, stored)` for every case whose stored program differs from
    what was typed. A case with NO chain at all is deliberately NOT flagged: the
    absent chain means the machine never reached the check (a wedge or a
    timeout), which the caller already sees as a None capture -- flagging it
    would turn one apparatus failure into a storm of re-runs that measure the
    same wedge."""
    bad = []
    for i, (mode, lines) in enumerate(cases):
        want = expected_lines(mode, lines)
        got = delivered.get(i)
        if want is not None and got is not None and got != want:
            bad.append((i, want, got))
    return bad


def _delivery_note(machine: str, cases, i: int, want, got) -> str:
    """Name the CAUSE and the remedy, not just the symptom: a message that only
    says "case 22 differs" is the kind that gets an `except: pass` wrapped round
    it ([[test-reads-ram-after-runaway]])."""
    lines = cases[i][1]
    missing = sorted(set(want) - set(got))
    return (f"MIS-DELIVERED case {i} on {machine}: typed "
            f"{','.join(map(str, want))}, machine stored "
            f"{','.join(map(str, got)) or '<none>'}"
            f" -- line(s) {missing or 'n/a'} never entered "
            f"(the screen editor rejected a mangled echo). Body: {lines!r}")


# --- D-ECHO: the per-injection echo oracle ----------------------------------
# docs/spec-probe-echo.md. The stored-program oracle above covers `mode="stored"`
# only -- 8 of the 53 probe files that drive this module. The SAME race mangles a
# `direct`-mode line (MEASURED: phase O re-expressed in direct mode, byte-identical
# injections on byte-identical slots, mangles the same case 22 on the same line),
# and there it reads as a value. So every injected line is now checked against
# what the machine ECHOED.


def screen_stream(txt: str, linlen: int) -> str | None:
    """One capture as a CONTIGUOUS text stream, so a wrapped echo is a plain
    substring. None when the screen carries no text at all.

    🔴 NEITHER THE MARGIN NOR THE WIDTH MAY BE HARD-CODED -- the two machines
    disagree on both (spec §2.1): `Philips_VG_8020` indents every row by 2 and
    runs a 37-column window, `C-BIOS_MSX1_EU_REPACK_DISK` indents by 1 and runs
    39. A row is `[margin][linlen columns][pad]` and a line too long for the
    window resumes at the MARGIN of the next row, so slicing each row to exactly
    the window and concatenating rejoins what wrapping split.

    The margin is MEASURED per capture -- the narrowest indent on the screen,
    which the prompt row always supplies (basic_probe_lnblank.py's method, which
    it reached after comparing against `rstrip()` reported every row mangled on
    both references). `linlen` is READ from the machine, not assumed."""
    rows = [txt[r * COLS:(r + 1) * COLS] for r in range(ROWS)]
    live = [r for r in rows if r.strip()]
    if not live or not 1 <= linlen <= COLS:
        return None
    margin = min(len(r) - len(r.lstrip(" ")) for r in live)
    return "".join(r[margin:margin + linlen] for r in rows)


def echo_verdicts(slots: list[tuple[int, str]],
                  echoes: dict[int, tuple[int, int, str]]) -> list[tuple]:
    """`(slot, case_index, typed, verdict)` per injection slot. Verdicts:

       OK             the typed text is in the screen's text stream
       MANGLED        it is NOT, the screen only GAINED, and a proper SUFFIX of
                      the typed text is on it -- a truncated echo
       BLIND/mode     SCRMOD != 0 -- this scrape is not looking at the text plane
       BLIND/rewrote  the screen lost content, so the echo may have been erased
                      rather than never written
       BLIND/noecho   nothing resembling a truncated echo is on the screen
       NODUMP         no dump arrived for this slot

    🔴 A MANGLED VERDICT CARRIES ITS OWN CONTROL, AND IT HAS TO. "The typed text
    is absent" is NOT sufficient, and every weaker control tried here was
    MEASURED producing false positives on the corpus:

      * a payload that CLEARS the screen -- `CLS`, `SCREEN n`, a `RUN` whose
        program does either -- erases its own echo. Every case in this repo is
        preceded by a `CLS` reset, so a bare absence test reports a mangle on
        every case in every suite.
      * a payload whose OUTPUT scrolls its own echo off the top. `linemax` types
        a 254-character line and then `LIST`s it: the screen ends with MORE rows
        than before, so a row-count growth test cannot see this -- that test
        called it MANGLED and turned a 60/60 gate into exit 2.
      * a payload that clears and then prints. `missing` types
        `WIDTH 40:CLS:PRINT "AB";CHR$(35)`; afterwards the screen holds `AB#`
        and `Ok`, and since the PREVIOUS screen held only `Ok` and the reference's
        permanent function-key row -- both of which come BACK after a clear --
        a "nothing was lost" test cannot see this either. It reported 59 mangles
        in one suite.

    So the positive evidence is taken from the MECHANISM instead of from the
    shape of the screen. The race swallows a PREFIX of the injected line -- and
    exactly as many characters as the PRECEDING injection occupied, its CR
    included, measured at 4, 8, 9, 14 and 16 (spec §2.5) -- so what the screen
    editor reads back, and what the machine therefore echoes, is a proper SUFFIX
    of what was typed. `10 ON ERROR GOTO 40` echoes as `N ERROR GOTO 40`,
    `PRINT "[";(0 AND 0) IMP 0;"]"` as `T "[";(0 AND 0) IMP 0;"]"`. A wiped echo
    leaves no such suffix; a truncated one always does.

    MANGLED therefore needs all three: the typed text absent, the screen having
    lost nothing (so the echo was not erased or scrolled away), and a proper
    suffix of the typed text present (so an echo WAS written, just not this
    line's). Anything less refuses [[guard-that-cannot-judge-must-say-so]].

    ⚠️ NAMED BLIND SPOTS, not hidden ones: a mangled `CLS`, a mangled
    `SCREEN n`, a mangled `RUN` whose program clears, a mangled line on a
    screen that scrolls, and a mangle that swallows the line ENTIRE (no suffix
    survives to be found) are all invisible here. The stored-program oracle is
    the second opinion for the stored-mode half of that (spec §5); the rest is a
    stated coverage limit.

    A blind slot also destroys the BASELINE, so the slot after it is blind too:
    with no trustworthy previous screen there is nothing to compare against, and
    guessing would manufacture exactly the false positive this function exists to
    avoid."""
    out: list[tuple] = []
    prev: list[str] | None = None
    for k, (case_idx, typed) in enumerate(slots):
        got = echoes.get(k)
        if got is None:
            out.append((k, case_idx, typed, "NODUMP", []))
            prev = None
            continue
        if any(not 0x20 <= ord(c) < 0x7F for c in typed):
            # 🔴 A PAYLOAD THE SCREEN CANNOT SPELL BACK. `lnblank` types
            # `2\t0 REMX`; the ROM RENDERS that tab as cursor movement, so the
            # screen holds blanks where the character was and the typed text can
            # never be a substring of it. The capture decodes every byte outside
            # 0x20..0x7E to a blank for the same reason, so neither side of the
            # comparison can represent one.
            #
            # This was caught by the ZERO-RED control, not by inspection: it
            # fired on the REFERENCE, which mis-delivers nothing, so the guard
            # was measuring something other than the race
            # [[knife-that-reddens-nothing-is-the-finding]]. Refusing keeps the
            # baseline -- the screen is perfectly readable, it is this PAYLOAD
            # that cannot be checked -- so the next slot is judged normally.
            out.append((k, case_idx, typed, "BLIND/unprintable", []))
            prev = [r for r in (got[2][i * COLS:(i + 1) * COLS].strip()
                                for i in range(ROWS)) if r]
            continue
        scrmod, linlen, txt = got
        if scrmod != 0:
            # a mode change makes the screens incomparable ACROSS this slot, not
            # merely unreadable AT it -- hence the baseline goes too.
            out.append((k, case_idx, typed, "BLIND/mode", []))
            prev = None
            continue
        stream = screen_stream(txt, linlen)
        rows = [r for r in (txt[i * COLS:(i + 1) * COLS].strip()
                            for i in range(ROWS)) if r]
        if stream is not None and typed in stream:
            verdict = "OK"          # positive evidence; it needs no baseline
        elif (stream is None or prev is None
                or any(r not in stream for r in prev)):
            verdict = "BLIND/rewrote"
        elif echoed_suffix(typed, stream) is None:
            verdict = "BLIND/noecho"
        else:
            verdict = "MANGLED"
        out.append((k, case_idx, typed, verdict, rows))
        prev = rows
    return out


# The shortest suffix worth believing. A 1-character suffix matches almost any
# screen by chance -- `Ok`, the reference's function-key row and the case's own
# output are all in the stream -- and would buy a false positive for nothing.
MIN_ECHO_SUFFIX = 2


def echoed_suffix(typed: str, stream: str) -> str | None:
    """The LONGEST proper suffix of `typed` that is on the screen, or None.

    Longest, not any: it names how many characters were swallowed, which is the
    measurable quantity the mechanism predicts (spec §2.5 -- the count equals the
    length of the preceding injection including its CR). Reporting the shortest
    match would throw that away."""
    for cut in range(1, len(typed) - MIN_ECHO_SUFFIX + 1):
        if typed[cut:] in stream:
            return typed[cut:]
    return None


# --- D-SCRAPEMODE: the scrape was pointed at the WRONG PLANE ----------------
# 🔴 THIS IS NOT A BLIND SPOT, IT IS A POSITIVE READING, AND IT WAS BEING
# DISCARDED. `BLIND/mode` is emitted when the echo oracle reads SCRMOD out of
# the machine's own RAM and finds it non-zero -- "this scrape is not looking at
# the text plane". `mis_echoed` below counts only MANGLED, correctly (a blind
# SLOT is a refusal to judge), so every one of these was dropped.
#
# Measured 2026-09-02 (D-LSETREF §6): `National_CF-3000` booted without the
# `SCREEN 0` this module's 40-column scrape assumes returned
# `['BLIND/mode', 'BLIND/mode', 'BLIND/mode']`, `mis_echoed() == []`, a capture
# of the SCREEN-1 PATTERN GENERATOR TABLE read as text -- and
# `probe_refcache.storable()` said True. Seven ghost entries were written that
# no re-run would have dislodged.
#
# ⚠️ THE PREDICATE IS `BLIND/mode` SPECIFICALLY, NOT "all blind". A probe that
# CLSes early legitimately produces `BLIND/rewrote` for every slot; refusing on
# that would redden correct runs. Only the mode verdict says the instrument was
# aimed wrong, and only it is used here.
#
# 🎯 IT REFUSES TO **CACHE**, NOT TO RUN. The readings are still returned and
# printed: an early refusal is how 08-31 buried two real divergences
# ([[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]), so the
# operator still sees whatever the probe made of the garbage -- it simply never
# becomes permanent.
_LAST_SCRAPE_INVALID: str | None = None


def scrape_invalid(echo: list[tuple]) -> str | None:
    """A one-line reason iff EVERY judged slot says the scrape was off-plane."""
    verdicts = [v for _, _, _, v, _ in echo]
    if len(verdicts) >= 2 and all(v == "BLIND/mode" for v in verdicts):
        return (f"all {len(verdicts)} echo slots read BLIND/mode (SCRMOD != 0): "
                f"the capture is not the text plane")
    return None


def mis_echoed(echo: list[tuple]) -> list[tuple[int, int, str, list]]:
    """`(case_index, slot, typed, screen_rows)` for every injection the machine
    did not echo as typed. Only MANGLED counts -- a BLIND slot is a refusal to
    judge, not a finding, and treating it as one would re-run most of every
    suite."""
    return [(c, k, t, rows) for k, c, t, v, rows in echo if v == "MANGLED"]


def _echo_note(machine: str, cases, case_idx: int, slot: int, typed: str,
               rows: list[str]) -> str:
    """⚠️ CARRIES THE SCREEN, because the first question anyone asks of this
    message is "is it real?" -- and answering it otherwise means re-deriving the
    probe's matrix by hand. What the machine echoed INSTEAD is the evidence:
    `ZBN ERROR GOTO 40` under a typed `10 ON ERROR GOTO 40` is the fault,
    whereas a screen that simply does not hold the line is a hint that this
    oracle has found a new blind spot rather than a new mangle."""
    body = cases[case_idx][1] if case_idx < len(cases) else "?"
    suffix = next((s for r in rows
                   for s in [echoed_suffix(typed, r)] if s), None)
    lost = f"{len(typed) - len(suffix)} leading char(s)" if suffix else "its head"
    return (f"MIS-ECHOED case {case_idx} on {machine} (slot {slot}): typed "
            f"{typed!r}, machine echoed {suffix!r} -- {lost} swallowed, and the "
            f"screen lost nothing, so no clear or scroll erased them. The line "
            f"was delivered mangled (docs/spec-probe-echo.md). Body: {body!r}\n"
            f"            screen: {rows!r}")


def _oracle_disagreement(machine: str, bad_stored, bad_echo) -> str | None:
    """🔴 THE TWO ORACLES ARE THE ONLY CHECK EACH OTHER HAS (spec §3.5). They are
    independent -- one walks the line-link chain from TXTTAB, the other reads the
    screen -- so where both can see, they must agree. A self-contained batch of
    IDENTICAL cases does NOT reproduce the race (predecessor content moves the
    alignment, D-DELIVER §8.4), so there is no frozen positive control that would
    not go silent the day a ROM change shifted it; this agreement check fires
    exactly when the race does, whatever provoked it."""
    s, e = {b[0] for b in bad_stored}, {b[0] for b in bad_echo}
    if s == e:
        return None
    return (f"omsx_repl: ORACLES DISAGREE on {machine}: stored-program oracle "
            f"flags {sorted(s) or '{}'}, echo oracle flags {sorted(e) or '{}'}. "
            f"Both repairs still run. Cases only one oracle sees are EXPECTED "
            f"where the other is structurally blind (spec §5): direct mode and "
            f"`RUN` are echo-only; a case typed in SCREEN 2, and any line whose "
            f"own execution clears the screen, are stored-only.\n")


def run_batch(machine: str, cases: list[tuple[str, list[str]]], *,
              verify_delivery: bool = True, **kw) -> list[str | None]:
    """`_run_batch` plus the D-DELIVER verdict. THIS path has no repair to fall
    back on -- it is the boot-per-case path itself (`run_case`, and `run_cases`
    with batch=False), the one measured immune -- so a mis-delivery here is an
    APPARATUS FAILURE and is raised, never returned as a value. A guard that
    cannot judge must say so.

    `verify_delivery=False` opts out of BOTH oracles, for a probe that
    deliberately drives line entry to refusal. No probe needs it today (spec
    §3.4)."""
    caps, delivered, echo = _run_batch(machine, cases, **kw)
    global _LAST_SCRAPE_INVALID
    _LAST_SCRAPE_INVALID = scrape_invalid(echo) if verify_delivery else None
    bad = mis_delivered(cases, delivered) if verify_delivery else []
    bad_echo = mis_echoed(echo) if verify_delivery else []
    if bad or bad_echo:
        raise SystemExit(
            "omsx_repl: APPARATUS FAILURE -- boot-per-case delivery was mangled; "
            "nothing was measured.\n  "
            + "\n  ".join([_delivery_note(machine, cases, *b) for b in bad]
                          + [_echo_note(machine, cases, *b) for b in bad_echo]))
    return caps


# Machines whose preflight has already passed in THIS process (see run_cases).
_PREFLIGHTED: set = set()


def _kwcover_log(machine, cases):
    """D-KWCOVER: with $ZEROBAS_KWCOVER set, append every line this call TYPES to
    that file, tagged with the suite ($ZEROBAS_KWCOVER_TAG, set by the Makefile
    recipe) and the case label. The keyword-coverage question -- which of the 159
    keywords does the collected battery actually run? -- was first attacked by
    scanning the probes' Python strings for BASIC, and three rounds of heuristics
    still scored English prose and Z80 assembly as BASIC (`AND` "exercised by 125
    suites", the UNEXERCISED set empty). The only honest source for what the
    battery runs is the battery running, and this is the one function it all goes
    through, so the capture is two lines here instead of a guess per string.
    Costs nothing when the variable is unset [[apparatus-is-part-of-the-measurement]].
    """
    path = os.environ.get("ZEROBAS_KWCOVER")
    if not path:
        return
    tag = os.environ.get("ZEROBAS_KWCOVER_TAG", "?")
    try:
        with open(path, "a", encoding="utf-8") as fh:
            for label, lines in cases:
                for ln in lines:
                    fh.write(f"{tag}\t{machine}\t{label}\t{ln}\n")
    except OSError:
        pass                        # a capture that cannot write must not break a gate


def run_cases(machine: str, cases: list[tuple[str, list[str]]], **kw):
    """D-REFCACHE wrapper around `_run_cases_impl` (the real body, below).

    🎯 ONE CHOKEPOINT, NOT 200 CALL SITES. Every probe in the tree reaches the
    emulator through this function, so the cache is installed HERE rather than
    in a helper each caller must remember to use -- the same reasoning that put
    the temp root in one `tempfile.tempdir` assignment instead of a wrapper 140
    sites had to call. [[one-temp-root]]

    The parameters are normalised through the impl's own signature with defaults
    applied, so a caller that OMITS `boot=8.0` keys identically to one that
    passes it. (Getting that wrong would only ever cause a miss, never a wrong
    hit -- but a cache that misses on equivalent calls is not worth having.)
    """
    _kwcover_log(machine, cases)
    # 🔬 $ZB_BATCH FORCES A MODE, FOR THE CONVERSION CONTROL (D-BATCH2).
    # `batch=False` is passed by 35 of the tree's 60 emulator probes -- the
    # docstring calls it "the historical default" -- and it dominates the
    # battery: strparen went 35 s -> 5 s on the flip. But D-EDITVERB records what
    # a WRONGLY batched suite does: one case's capture becomes a whole log and
    # every later delta is silently wrong "in the direction of a plausible-
    # looking divergence". So a conversion must be proved by running the suite
    # BOTH ways and diffing its rows.
    # 🔴 THIS ONLY WORKS BECAUSE `reset` NOW APPLIES IN BOTH MODES. D-BATCH1's
    # first attempt at this switch was WITHDRAWN as unsound: `reset` meant
    # something batched and nothing boot-per-case, so forcing the other mode
    # produced a THIRD behaviour rather than the old one. The fix was in
    # `_run_cases_impl`, not here -- see the `if not batch:` branch.
    # ⚠️ A TEST-HARNESS SWITCH, NOT A TUNABLE: the runner never sets it, and
    # `scratchpad/batchcheck.py` is its only consumer.
    import inspect
    bound = inspect.signature(_run_cases_impl).bind(machine, cases, **kw)
    bound.apply_defaults()
    # 🔴 AND RECORD THE MATRIX SIZE, BECAUSE FORCING `batch=True` ON A
    # ONE-CASE LIST BATCHES NOTHING. Probes that loop in PYTHON and call this
    # once per case cannot be tested by flipping the flag: both modes boot per
    # case, every row matches, and batchcheck reported four suites CONVERTIBLE
    # having compared two identical runs. The 1.0x "speedup" was the only tell.
    # `scratchpad/batchcheck.py` reads this to refuse that verdict.
    _stat = os.environ.get("ZB_BATCH_STAT")
    if _stat:
        try:
            with open(_stat, "a") as _fh:
                _fh.write(f"{len(cases)}\n")
        except OSError:
            pass
    _force = os.environ.get("ZB_BATCH")
    if _force in ("0", "1"):
        want = (_force == "1")
        bound.arguments["batch"] = want
        kw = dict(kw); kw["batch"] = want
    args = dict(bound.arguments)
    args.pop("machine"); args.pop("cases")
    settle = args.pop("settle_out", None)

    try:
        import probe_refcache as rc
    except Exception:
        rc = None
    if rc is None or not rc.ENABLED:
        return _run_cases_impl(machine, cases, **kw)

    key = rc.key_for(machine, cases, args)
    cached, settle_cached = rc.load(key)
    # 🔴 ALL-OR-NOTHING: `cached` covers the WHOLE call or none of it, so a
    # batched matrix is never re-composed (see the module header).
    servable = (cached is not None and len(cached) == len(cases)
                and (settle is None or settle_cached is not None))
    if servable and not rc.VERIFY:
        # 🔴 D-CACHEPRE (2026-08-29): THE STALENESS GUARD LIVES ON THE HIT PATH.
        # `omsx_preflight.guarded()` is applied at the `Popen` call inside
        # `_run_cases_impl`, so it only ever ran when the emulator actually
        # LAUNCHED -- and a served hit returns before that. THE REFCACHE SILENTLY
        # DISABLED THE GUARD: with a warm store and a ROM that no longer matches
        # its sources, a probe printed a complete, self-consistent, entirely
        # plausible table and said nothing. It bit twice in ten minutes, after a
        # `make repack-machine` failed on an assembler error (pasmo fails
        # cleanly, leaving the PREVIOUS ROM in place, so the cache's ROM-identity
        # key was unchanged and every row hit). Caught only by reading the
        # build's exit code. [[apparatus-is-part-of-the-measurement]]
        #
        # ⚠️ THE HIT PATH, NOT run_cases ENTRY -- and the reason is cost, not
        # safety. A MISS goes on to Popen, which is already guarded, so an entry
        # check buys no extra cover and adds a `make -q` to every one of the
        # thousands of run_cases calls a batched probe makes: ~20 s per battery
        # for an answer that cannot change. The hit path is the one that had no
        # guard at all.
        # 🔴 AN EARLIER NOTE HERE BLAMED THE ENTRY PLACEMENT FOR A RED BATTERY.
        # That was wrong and is recorded in docs/spec-basic-numstr.md §5.1: the
        # emulator tier forces ZEROBAS_REFCACHE=0 and never takes this branch, so
        # neither placement can affect it. Those failures were host CPU
        # starvation, which the stall watchdog names in its own message.
        # Memoised per process: within one process the ROM is fixed, and a knife
        # runner rebuilds BETWEEN probe invocations, each a fresh process.
        if machine not in _PREFLIGHTED:
            omsx_preflight.preflight(machine)
            _PREFLIGHTED.add(machine)
        rc.STATS["hit"] += 1
        if settle is not None:
            # give the caller EXACTLY the dict it would have got, plus the flag
            # that says these instants were replayed rather than measured now
            settle.clear()
            settle.update(settle_cached)
            settle["replayed"] = True
            rc.STATS["replayed"] += 1
        return cached

    result = _run_cases_impl(machine, cases, **kw)
    if rc.VERIFY and cached is not None and len(cached) == len(cases):
        if cached == result:
            rc.STATS["verify_ok"] += 1
        else:
            rc.STATS["verify_bad"] += 1
            bad = [i for i, (a, b) in enumerate(zip(cached, result)) if a != b]
            sys.stderr.write(
                f"🔴 refcache VERIFY MISMATCH on {machine}: case(s) {bad} differ "
                f"between the stored reading and a fresh one. The store is WRONG "
                f"or the machine moved; key {key[:12]}\n")
    else:
        rc.STATS["miss"] += 1
    # D-SCRAPEMODE: never freeze an off-plane scrape into the cache.
    if _LAST_SCRAPE_INVALID:
        sys.stderr.write(
            f"🔴 omsx_repl: NOT CACHING {machine} -- {_LAST_SCRAPE_INVALID}. "
            f"The readings below are returned as measured, but they are a scrape "
            f"of the wrong VRAM plane, not the text screen. A stock MSX1 boots "
            f"SCREEN 1; this module's scrape assumes SCREEN 0 (40 cols at "
            f"{SCR_ADDR:#06x}), so a machine whose `reset` does not put it there "
            f"reads the pattern generator table as if it were text.\n")
    else:
        rc.store(key, result, machine, settle=settle)
    return result


def _run_cases_impl(machine: str, cases: list[tuple[str, list[str]]], *,
              batch: bool = True, reset: tuple[str, ...] = ("CLS",),
              capture="screen",
              holds: list[tuple[int, int] | None] | None = None,
              hold_secs: float = 12.0, hold_lead: float | None = None,
              prologue: tuple[str, ...] = (),
              boot: float = 8.0, step: float = 2.5, cap_gap: float = 2.5,
              timeout: float | None = None, omsx: str | None = None,
              cart: str | None = None, diska: str | None = None,
              cassette: str | None = None,
              verify_delivery: bool = True,
              run_gap: float | None = None,
              sentinel: tuple[int, int] | None = None,
              sentinel_capture: bool = False,
              settle_out: dict | None = None) -> list[str | None]:
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

    `prologue` is raw Tcl run once before the timeline (see `_tcl`) -- the
    `plug joyporta <device>` seam. It applies to the WHOLE batch, so a matrix that
    needs several device configurations runs one `run_cases` call per
    configuration rather than mixing them in one boot.

    `verify_delivery` (default True, D-DELIVER) checks every stored-mode case's
    program against what was typed and re-runs a mangled one boot-per-case,
    announcing it on stderr. Set it False only for a probe that deliberately
    drives line entry to refusal.

    🔴 **`run_gap` IS THE RUN->CAPTURE BUDGET; `cap_gap` IS NOT.** A case's
    capture fires `run_gap` past its `RUN` when one is given and `step` past it
    otherwise, and `cap_gap` -- the gap AFTER the capture -- never moves it
    (docs/spec-probe-budget.md §1, pinned by tests/test_capture_budget.py). So a
    case whose program needs longer than `step` to finish needs `run_gap`;
    raising `cap_gap` only delays the NEXT case and the scheduled exit.
    ⚠️ **AND A CAPTURE TAKEN TOO EARLY LOOKS LIKE A DEFECT, NOT LIKE A TIMEOUT.**
    D-TWOFILE read a half-drawn screen as a hang, then as a silent abort, then
    as dead screen output, across five wrong diagnoses; the program had simply
    not reached its later `PRINT`s yet. The fact was already in §1 in bold and
    in `_tcl`'s own comment -- neither of which is where a CALLER looks, which
    is why it is also here.
    """
    kw = dict(boot=boot, step=step, cap_gap=cap_gap, capture=capture,
              hold_secs=hold_secs, hold_lead=hold_lead, prologue=prologue,
              omsx=omsx, cart=cart, diska=diska, cassette=cassette, run_gap=run_gap,
              sentinel=sentinel, sentinel_capture=sentinel_capture)
    if settle_out is not None:
        kw["settle_out"] = settle_out
    to_single = timeout if timeout is not None else 240.0
    if not batch:
        # 🔬 THE CALLER'S `reset` APPLIES IN BOTH MODES (D-BATCH2, 2026-09-01).
        # This used to be `reset=()`, so `reset` meant something in the batched
        # path and nothing in the boot-per-case one -- and every boot-per-case
        # probe therefore PREPENDS its own reset to each case body. That
        # asymmetry is what made a generic "run it both ways" control impossible:
        # forcing the other mode from outside produced a THIRD behaviour (no
        # reset, or two), which is exactly how D-BATCH1's first control failed.
        # 🟢 SAFE BECAUSE EVERY RESET IN THE TREE IS IDEMPOTENT -- swept: only
        # NEW / CLS / SCREEN 0 / blank lines, in ten combinations. A probe that
        # already prepends its own now runs it twice, which costs a little
        # emulated time and changes nothing observable; a probe that does NOT
        # prepend (i.e. a converted one) now behaves the same in both modes,
        # which is the whole point.
        return [run_batch(machine, [c], reset=reset, timeout=to_single,
                          holds=[holds[i]] if holds else None,
                          verify_delivery=verify_delivery, **kw)[0]
                for i, c in enumerate(cases)]

    # scale the safety-net timeout with the emulated timeline length
    to = timeout if timeout is not None else max(240.0, 1.5 * len(cases) + 120.0)
    if holds:                           # a held case adds hold_secs+1 to the timeline
        to += (hold_secs + 1.0) * sum(1 for h in holds if h)
    caps, delivered, echo = _run_batch(machine, cases, reset=reset, holds=holds,
                                       timeout=to, **kw)
    # D-DELIVER (docs/spec-probe-delivery.md §3.3) and D-ECHO
    # (docs/spec-probe-echo.md §3.4): a batched case the machine did not store as
    # typed, or did not ECHO as typed, produced NO reading. Re-run that case
    # alone, on the boot-per-case path measured immune to the race -- and SAY SO,
    # because a matrix that genuinely depends on batch context would answer
    # differently on the repair path and the operator has to be able to see it.
    global _LAST_SCRAPE_INVALID
    _LAST_SCRAPE_INVALID = scrape_invalid(echo) if verify_delivery else None
    bad_stored = mis_delivered(cases, delivered) if verify_delivery else []
    bad_echo = mis_echoed(echo) if verify_delivery else []
    notes = ([(i, _delivery_note(machine, cases, i, want, got))
              for i, want, got in bad_stored]
             + [(b[0], _echo_note(machine, cases, *b)) for b in bad_echo])
    if verify_delivery:
        dis = _oracle_disagreement(machine, bad_stored, bad_echo)
        if dis:
            sys.stderr.write(dis)
    # one re-run per CASE however many lines of it were mangled, and however many
    # oracles saw it: the repair is a fresh boot of the whole case either way.
    for i in sorted({i for i, _ in notes}):
        for _, note in [n for n in notes if n[0] == i]:
            sys.stderr.write("omsx_repl: " + note + "\n")
        sys.stderr.write("            -> re-running that case boot-per-case\n")
        caps[i] = run_batch(machine, [cases[i]], reset=(), timeout=to_single,
                            holds=[holds[i]] if holds else None,
                            verify_delivery=verify_delivery, **kw)[0]
    return caps


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
# bare 'ZB' prompt on a LINE OF ITS OWN -- so echo matching is ends-with and
# both prompt shapes terminate a tail.
#
# ⚠️ zerobas's prompt is 'ZB' and every probe that has to find the end of a
# command's output goes through THIS tuple. It was 'zb>' until 2026-07-27.
PROMPTS = ("Ok", "ZB")
#
# The prompt used to be 'zb>' and used to be printed wherever the cursor stood.
# Since 2026-07-27 it is 'ZB' and always OPENS a fresh line (basic/repl.asm),
# matching the reference.
#
# ⚠️ "Always starts a line" is NOT "always alone on a line": the prompt is still
# followed on that row by the ECHO of whatever the user typed, which is what a
# prompt is for. So a row equal to a prompt is a prompt with nothing typed after
# it (what terminates a tail, below), while a row that STARTS with one is an
# echo -- probes that read echo rows must still strip the leading prompt.

def result_span(raw: str | None, why: dict | None = None) -> str | None:
    """Text between the LAST '[' and the following ']' (the printed value).
    None if the ']' never printed (statement aborted before the PRINT).

    🔴 `None` MEANS FOUR DIFFERENT THINGS AND A CALLER CANNOT TELL THEM APART.
    Nothing captured, no '[' anywhere, a '[' with no ']', and -- in
    `result_span_after_echo` -- no echo row to search after. A payload that
    prints NO BRACKETS therefore reads `None` on EVERY side, and sides that all
    failed compare EQUAL and report *agrees*: `basic_probe_lnblank.py`'s
    `dir-print` sat in that state from the day it was written
    (TODO.md, D-NAMBLANK). A sentinel that also means "no reading" is not a
    measurement.

    🎯 SO PASS A `why` DICT AND GET THE DIAGNOSIS. Same out-parameter idiom this
    module already uses for `settle_out`, and the same cure as `_why_missing`:
    the evidence was always there, it was just thrown away. Callers that pass
    nothing are completely unaffected -- the return contract is unchanged.
    """
    if raw is None:
        if why is not None:
            why["reason"] = "no capture at all (the run produced no screen)"
        return None
    i = raw.rfind("[")
    if i < 0:
        if why is not None:
            why["reason"] = ("no '[' anywhere in the searched text -- either the "
                             "statement aborted before its PRINT, or THE PAYLOAD "
                             "HAS NO BRACKETS AND CAN NEVER PRODUCE A READING")
        return None
    j = raw.find("]", i)
    if j < 0:
        if why is not None:
            why["reason"] = "a '[' with no ']' after it -- aborted mid-PRINT"
        return None
    if why is not None:
        why["reason"] = "ok"
    return raw[i + 1:j]


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
        if r in PROMPTS:
            break
        out.append(r)
    while out and out[-1] == "":
        out.pop()
    return "|".join(out)


def result_span_after_echo(raw: str | None, cmdline: str,
                           why: dict | None = None) -> str | None:
    """Like result_span but restricted to rows AFTER the echoed command line, so
    an aborted case's echoed '[' is not misread as printed output. None if the
    echo row can't be found. `why` as in result_span -- with one more reason
    only this function can give."""
    if raw is None:
        if why is not None:
            why["reason"] = "no capture at all (the run produced no screen)"
        return None
    rows = [raw[r * COLS:(r + 1) * COLS] for r in range(ROWS)]
    idx = _echo_idx([r.strip() for r in rows], cmdline)
    if idx is None:
        if why is not None:
            why["reason"] = (f"the echo row for {cmdline.strip()!r} was never "
                             f"found, so there is no 'after' to search -- an "
                             f"INSTRUMENT result, not a machine one")
        return None
    return result_span("".join(rows[idx + 1:]), why)


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
