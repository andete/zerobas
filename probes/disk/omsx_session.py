#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""openMSX investigation job-runner: one boot, a whole algorithm, structured output.

The Tier-2 hunt was dominated by a mechanical loop: hand-write a one-off Tcl
`-script`, launch openMSX, poll, parse, decide, repeat. This module folds the
*mechanical* part into reusable Python: it composes a Tcl job from validated
primitives (reverse-goto time bisection, forward per-instruction trace, interrupt
catch), runs it in ONE openMSX launch, and returns parsed records. It draws no
conclusions — that stays with the human/Opus (see disk_derail_locate.py for the
thin algorithmic driver built on top).

Why a job-runner and not an interactive `-control stdio` session: control-stdio
openMSX does not free-run its emulation between commands (verified — `debug cont`,
`set pause false`, and even `debug step` leave the CPU frozen at reset). The
`-script` + `after time` mechanism free-runs reliably and is what every manual
probe today used. So each high-level operation is one generated script / one boot.

Key Tcl facts this encodes (all validated):
  * inside an `after time T {...}` callback the machine sits at emulated time T with
    a full `reverse` timeline 0..T; `reverse goto` repositions instantly there.
  * `debug step` does NOT advance inside a callback; a forward trace must install a
    per-instruction `debug condition` and RETURN (let the reactor free-run).
  * `read_mem` watchpoints fire on the opcode fetch; `z80.acceptIRQ` probe catches
    interrupt acceptance; `{CPU regs}` byte 27 = IFF1/2 + can-accept.
"""
from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time

DEFAULT_OPENMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
OURS_MACHINE = "National_CF-3300_ZEROBASDISK"
STOCK_MACHINE = "National_CF-3300"

# A reusable Tcl preamble: throttle off, reverse on, symbol load, and an `emit`/`ctx`
# pair so every job reports state in one parseable line format.
_PREAMBLE = r"""
set throttle off
set renderer none
catch {{ debug symbols load {symfile} generic }}
reverse start
proc emit {{line}} {{ set f [open {{{out}}} a]; puts $f $line; close $f }}
proc ctx {{tag}} {{
  set pc [reg PC]
  set iff [debug read {{CPU regs}} 27]
  return [format "%s PC=%04X SP=%04X AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X IFF1=%d t=%.6f m4251=%02X m0038=%02X%02X%02X dis={{%s}}" \
    $tag $pc [reg SP] [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] \
    [expr {{$iff & 1}}] [machine_info time] [debug read memory 0x4251] \
    [debug read memory 0x38] [debug read memory 0x39] [debug read memory 0x3A] \
    [lindex [debug disasm $pc] 0]]
}}
proc P {{}} {{ return [expr {{{predicate}}}] }}
"""


def parse_ctx(line: str) -> dict:
    """Parse one `TAG key=val ... dis={...}` record into a dict (ints auto-hex)."""
    rec: dict = {}
    line = line.strip()
    if not line:
        return rec
    # split off the dis={...} tail first (may contain spaces)
    dis = None
    if "dis={" in line:
        head, _, tail = line.partition("dis={")
        dis = tail.rsplit("}", 1)[0]
        line = head.strip()
    toks = line.split()
    rec["tag"] = toks[0]
    for tk in toks[1:]:
        if "=" not in tk:
            continue
        k, v = tk.split("=", 1)
        if k == "t":
            rec[k] = float(v)
        else:
            try:
                rec[k] = int(v, 16)
            except ValueError:
                rec[k] = v
    if dis is not None:
        rec["dis"] = dis.strip()
    return rec


class OmsxRun:
    def __init__(self, machine: str = OURS_MACHINE, diska: str | None = None,
                 symfile: str = "build/disk.omsx.sym", openmsx: str = DEFAULT_OPENMSX):
        self.machine = machine
        self.diska = diska
        self.symfile = symfile
        self.openmsx = openmsx

    def run_job_raw(self, body: str, settle: float, predicate: str = "0",
                    timeout: float = 200.0, safety: float = 30.0, arm: str = "") -> list[str]:
        """As `run_job`, but returns the RAW `emit` lines (unparsed). Use this when the
        job emits its own record format (e.g. the differential harness's `CALL`/`BLOCK`
        lines) that `parse_ctx` would mis-parse. `run_job` is this + `parse_ctx`."""
        out = tempfile.mktemp(suffix=".rec")
        tcl_path = tempfile.mktemp(suffix=".tcl")
        preamble = _PREAMBLE.format(symfile=self.symfile, out=out, predicate=predicate)
        script = preamble + arm + f"""
after time {settle:.4f} {{
  if {{[catch {{ {body} }} err]}} {{ emit "ERROR $err"; exit }}
}}
after time {settle + safety:.4f} {{ emit "TIMEOUT-SAFETY"; exit }}
"""
        open(tcl_path, "w").write(script)
        cmd = [self.openmsx, "-machine", self.machine, "-script", tcl_path]
        if self.diska:
            cmd += ["-diska", self.diska]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.2)
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
        lines: list[str] = []
        if os.path.exists(out):
            lines = [l for l in open(out).read().splitlines() if l.strip()]
            os.unlink(out)
        os.unlink(tcl_path)
        return lines

    def run_job(self, body: str, settle: float, predicate: str = "0",
                timeout: float = 200.0, safety: float = 30.0, arm: str = "") -> list[dict]:
        """Run one job. `body` is Tcl executed inside an `after time {settle}` callback
        (machine at emulated time `settle`, reverse timeline 0..settle ready). `body`
        is responsible for finishing with `exit` or installing a condition that exits.
        `arm` is Tcl run immediately (before boot proceeds) — for watchpoints that must
        be live from t=0. `predicate` is a Tcl expr available as `[P]`. Returns records."""
        return [parse_ctx(l) for l in self.run_job_raw(
            body, settle, predicate=predicate, timeout=timeout, safety=safety, arm=arm)]

    # -- composed primitives ----------------------------------------------
    def bisect_locate(self, predicate: str, lo: float, settle: float,
                      trace_n: int = 48, iters: int = 26) -> list[dict]:
        """Boot to `settle`; if `predicate` holds there, binary-search emulated time
        in [lo, settle] for the first instant it becomes true, report the LAST-GOOD /
        FIRST-BAD context, then forward-trace `trace_n` instructions from just before
        the flip. The composite of every manual derail probe, in one boot."""
        body = f"""
        if {{![P]}} {{ emit "NO-FAILURE-AT-SETTLE"; emit [ctx STATE]; exit }}
        set lo {lo:.6f}
        set hi [machine_info time]
        for {{set k 0}} {{$k < {iters}}} {{incr k}} {{
          set mid [expr {{($lo + $hi) / 2.0}}]
          reverse goto $mid
          if {{[P]}} {{ set hi $mid }} else {{ set lo $mid }}
        }}
        reverse goto $lo ; emit [ctx LAST-GOOD]
        reverse goto $hi ; emit [ctx FIRST-BAD]
        set sp [reg SP]
        set sw "STACK"
        for {{set i 0}} {{$i < 8}} {{incr i}} {{
          set a [expr {{($sp + 2*$i) & 0xFFFF}}]
          set sw "$sw [format %04X [expr {{[debug read memory $a] | ([debug read memory [expr {{($a+1)&0xFFFF}}]] << 8)}}]]"
        }}
        emit $sw
        reverse goto $lo
        reverse truncatereplay
        set ::n 0
        debug condition create -command {{
          incr ::n
          emit [ctx [format "T%03d" $::n]]
          if {{$::n >= {trace_n}}} {{ exit }}
        }}
        """
        return self.run_job(body, settle=settle, predicate=predicate, timeout=200.0)

    def forward_from(self, at_time: float, trace_n: int = 60,
                     settle: float | None = None) -> list[dict]:
        """Forward per-instruction trace of `trace_n` steps starting at `at_time`."""
        s = settle if settle is not None else at_time + 4.0
        body = f"""
        reverse goto {at_time:.6f}
        reverse truncatereplay
        emit [ctx START]
        set ::n 0
        debug condition create -command {{
          incr ::n
          emit [ctx [format "T%03d" $::n]]
          if {{$::n >= {trace_n}}} {{ exit }}
        }}
        """
        return self.run_job(body, settle=s, timeout=200.0)

    def irq_chain(self, settle: float = 12.0) -> list[dict]:
        """Catch the first maskable-interrupt acceptance after `settle` and dump the
        $0038 jp-chain + page-1 mapping signature. Comparable across machines (the
        int vector and page-1 window are at fixed addresses), so it answers 'how is
        the interrupt routed, and is the disk ROM still mapped?' on ours vs stock."""
        body = r"""
        debug probe set_bp z80.acceptIRQ {} {
          emit [ctx ACCEPT]
          set a 0x38
          for {set h 0} {$h < 8} {incr h} {
            set op [debug read memory $a]
            if {$op == 0xC3} {
              set t [expr {[debug read memory [expr {$a+1}]] | ([debug read memory [expr {$a+2}]] << 8)}]
              emit [format "CHAIN-%04X jp=%04X" $a $t]
              set a $t
            } else {
              emit [format "CHAIN-%04X op=%02X dis={%s}" $a $op [lindex [debug disasm $a] 0]]
              break
            }
          }
          emit [format "PAGE1 sig4000=%02X%02X b4251=%02X" \
            [debug read memory 0x4000] [debug read memory 0x4001] [debug read memory 0x4251]]
          exit
        }
        """
        return self.run_job(body, settle=settle, timeout=120.0)

    def write_watch(self, addr: int, n: int = 8, max_time: float = 9.0) -> list[dict]:
        """Report the first `n` writes to `addr` (armed from t=0): the writer PC,
        regs, and the resulting bytes at $0038 (ctx carries m0038). Answers 'who
        installs this RAM vector, when, and to what'."""
        arm = f"""
set ::wn 0
debug watchpoint create -type write_mem -address {{0x{addr:04X}}} -command {{
  incr ::wn
  emit [ctx [format "W%02d" $::wn]]
  if {{$::wn >= {n}}} {{ exit }}
}}
"""
        body = 'emit "REACHED-MAXTIME"; exit'
        return self.run_job(body, settle=max_time, timeout=max_time + 40, arm=arm)

    def read_block(self, addr: int, length: int, settle: float) -> list[int]:
        """Read `length` bytes at `addr` once the machine has run to `settle`."""
        body = f"""
        set s "BLOCK_{addr:04X}_"
        for {{set i 0}} {{$i < {length}}} {{incr i}} {{
          set s "$s[format %02X [debug read memory [expr {{({addr} + $i) & 0xFFFF}}]]]"
        }}
        emit $s
        exit
        """
        recs = self.run_job(body, settle=settle, timeout=settle + 40)
        for r in recs:
            tag = r.get("tag", "")
            if tag.startswith(f"BLOCK_{addr:04X}_"):
                hexpart = tag.split("_", 2)[2]
                return [int(hexpart[i:i + 2], 16) for i in range(0, len(hexpart), 2)]
        return []

    def time_sweep(self, predicate: str, lo: float, hi: float, step: float,
                   settle: float | None = None) -> list[dict]:
        """Sample state at regular emulated times in [lo, hi] (coarse bracketing)."""
        s = settle if settle is not None else hi + 0.5
        body = f"""
        set t {lo:.4f}
        while {{$t <= {hi:.4f}}} {{
          reverse goto $t
          emit [ctx [format "S%.3f" $t]]
          set t [expr {{$t + {step:.4f}}}]
        }}
        exit
        """
        return self.run_job(body, settle=s, predicate=predicate, timeout=200.0)
