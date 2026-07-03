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

# OWN_RAM_RANGES — every RAM block WE install code into (base, end-exclusive), sourced
# from the equ's in init.asm/kernel.asm + build/disk.omsx.sym (checked 2026-07-01):
#   P1_BLIT..WA_SEG_RAM+len  $E77A-$E7B0 (p1_blit_tmpl+wa_seg_*_tmpl, one contiguous LDIR)
#   DRV_TRAMP                $E800-$E814 (4 CALLF trampolines, 5 B each)
#   RES_PRINT                $F1C9-$F1D0 (res_print_tmpl, 7 B)
#   RES_STUBS                $F24E-$F2B8 (no-op $C9 stub table)
#   WA_JMPTAB..SYSTEM        $F368-$F380 (7 JP slots + the SYSTEM BDOS vector JP)
# This exists because a blanket "PC >= 0x4000 on the ours-host" gate is WRONG: the
# loaded MSXDOS.SYS kernel's own resident code also lives in page-3 RAM (>= 0x4000) on
# the ours-host, interleaved with these blocks. A 2026-07-01 OI-5 trace (tier2-m15-spec
# §7.1/§8 OI-5) proved this by decoding ~35 instructions of kernel code at $D8xx/$CBxx
# after a wa_seg `ret` — a clean-room breach of the same class as the 2026-06-30 one
# below. Keep this list in sync with init.asm/kernel.asm if a resident block moves.
OWN_RAM_RANGES = [
    (0xE77A, 0xE7B0),  # P1_BLIT + WA_SEG_ROM/WA_SEG_RAM
    (0xE800, 0xE814),  # DRV_TRAMP
    (0xF1C9, 0xF1D0),  # RES_PRINT
    (0xF24E, 0xF2B8),  # RES_STUBS
    (0xF368, 0xF380),  # WA_JMPTAB + SYSTEM
]
_OWN_RAM_TCL = " || ".join(f"($pc >= {lo:#06x} && $pc < {hi:#06x})" for lo, hi in OWN_RAM_RANGES)

# A reusable Tcl preamble: throttle off, reverse on, symbol load, and an `emit`/`ctx`
# pair so every job reports state in one parseable line format.
#
# CLEAN-ROOM GUARD (`DISOK`): `ctx` only decodes a mnemonic (`dis={...}`) when DISOK is
# set AND the PC is inside our own authored code. Decoding a REFERENCE ROM's or the
# loaded reference KERNEL's code bytes is disassembly (a ✗ source — see
# docs/allowed-sources.md / [[no-reference-rom-disasm]]). Two independent breaches have
# tripped variants of this:
#   * 2026-06-30: a trace on the STOCK machine surfaced the stock disk-ROM console
#     routine's decoded internals (fixed by gating DISOK off for the whole STOCK host).
#   * 2026-07-01: a trace on the OURS host, after returning from our own `wa_seg` hook,
#     surfaced decoded MSXDOS.SYS resident-kernel instructions — because that shared,
#     non-authored kernel ALSO runs at PC >= 0x4000 on the ours-host. Fixed by replacing
#     the blanket "PC >= 0x4000" RAM check with the OWN_RAM_RANGES allowlist below.
# The guard now decodes only:
#   * our disk ROM, $4000-$7FFF, on EITHER machine (page 1 is always our ROM by design);
#   * the specific RAM blocks we install into via LDIR/table-build (OWN_RAM_RANGES);
#   * never: the whole STOCK machine (DISOK=0 there, see OmsxRun.__init__), main-BIOS
#     ROM / a proprietary binary loaded low (PC < 0x4000), or any other page-3 address
#     (that's the loaded, shared, non-authored MSXDOS.SYS kernel).
# The black-box signal (PC, flow transitions, regs, call-targets-via-flow, symbol
# labels) is fully preserved; only the byte-decode of non-our-own code is withheld.
_PREAMBLE = r"""
set throttle off
set renderer none
set ::DISOK {disok}
catch {{ debug symbols load {symfile} generic }}
reverse start
proc emit {{line}} {{ set f [open {{{out}}} a]; puts $f $line; close $f }}
proc own_code {{pc}} {{
  return [expr {{($pc >= 0x4000 && $pc < 0x8000) || """ + _OWN_RAM_TCL + r"""}}]
}}
proc ctx {{tag}} {{
  set pc [reg PC]
  set iff [debug read {{CPU regs}} 27]
  set d "-"
  if {{$::DISOK && [own_code $pc]}} {{ set d [lindex [debug disasm $pc] 0] }}
  return [format "%s PC=%04X SP=%04X AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X IFF1=%d t=%.6f m4251=%02X m0038=%02X%02X%02X dis={{%s}}" \
    $tag $pc [reg SP] [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY] \
    [expr {{$iff & 1}}] [machine_info time] [debug read memory 0x4251] \
    [debug read memory 0x38] [debug read memory 0x39] [debug read memory 0x3A] \
    $d]
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
                 symfile: str = "build/disk.omsx.sym", openmsx: str = DEFAULT_OPENMSX,
                 allow_disasm: bool | None = None):
        self.machine = machine
        self.diska = diska
        self.symfile = symfile
        self.openmsx = openmsx
        # Clean-room: NEVER decode the reference (stock) machine's code. Default off for
        # the stock machine, on for ours; an explicit bool overrides. (The PC>=0x4000 gate
        # in the preamble still applies on top, so even ours never decodes main-BIOS/$0100.)
        self.allow_disasm = (machine != STOCK_MACHINE) if allow_disasm is None else allow_disasm

    def run_job_raw(self, body: str, settle: float, predicate: str = "0",
                    timeout: float = 200.0, safety: float = 30.0, arm: str = "",
                    keys: str = "", keys_at: float = 0.0,
                    keys2: str = "", keys2_at: float = 0.0) -> list[str]:
        """As `run_job`, but returns the RAW `emit` lines (unparsed). Use this when the
        job emits its own record format (e.g. the differential harness's `CALL`/`BLOCK`
        lines) that `parse_ctx` would mis-parse. `run_job` is this + `parse_ctx`.

        `keys`, if given, is typed into the emulated keyboard (openMSX `type`) at emulated
        time `keys_at` — the black-box way to drive console input (e.g. answer a BUFIN
        prompt, then drive past it to `A>`). Use `\\r` for Enter. Keys play under
        throttle-off, so a small `keys_at` < `settle` lets them land before the body runs.

        `keys2`/`keys2_at` is an optional SECOND, independently-timed injection (default
        off, byte-unchanged behavior when omitted) — for the case where the first burst
        must land during one program phase (e.g. a command name at `A>`) and a second
        burst must land later, after that phase's own disk activity is done (M22: ours
        was found to drop type-ahead typed during disk-heavy foreground work, so a
        console-input probe must stage its keys at an idle window, not alongside the
        command-name burst — see tier2-bdos-remaining-spec.md §3)."""
        out = tempfile.mktemp(suffix=".rec")
        tcl_path = tempfile.mktemp(suffix=".tcl")
        disok = 1 if self.allow_disasm else 0
        preamble = _PREAMBLE.format(symfile=self.symfile, out=out, predicate=predicate,
                                    disok=disok)
        inject = ""
        if keys:
            inject = f'after time {keys_at:.4f} {{ type "{keys}" }}\n'
        if keys2:
            inject += f'after time {keys2_at:.4f} {{ type "{keys2}" }}\n'
        script = preamble + arm + inject + f"""
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
                timeout: float = 200.0, safety: float = 30.0, arm: str = "",
                keys: str = "", keys_at: float = 0.0,
                keys2: str = "", keys2_at: float = 0.0) -> list[dict]:
        """Run one job. `body` is Tcl executed inside an `after time {settle}` callback
        (machine at emulated time `settle`, reverse timeline 0..settle ready). `body`
        is responsible for finishing with `exit` or installing a condition that exits.
        `arm` is Tcl run immediately (before boot proceeds) — for watchpoints that must
        be live from t=0. `predicate` is a Tcl expr available as `[P]`. `keys`/`keys_at`
        (and optional `keys2`/`keys2_at`) inject keystrokes (see run_job_raw). Returns
        records."""
        return [parse_ctx(l) for l in self.run_job_raw(
            body, settle, predicate=predicate, timeout=timeout, safety=safety, arm=arm,
            keys=keys, keys_at=keys_at, keys2=keys2, keys2_at=keys2_at)]

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
              set d "-"
              if {$::DISOK && [own_code $a]} { set d [lindex [debug disasm $a] 0] }
              emit [format "CHAIN-%04X op=%02X dis={%s}" $a $op $d]
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
