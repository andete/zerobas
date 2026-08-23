#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""CLEAR statement probe — differential + functional oracle for zerobas.

Clean-room methodology: this probe treats both the Philips VG-8020 reference
BASIC ROM and the zerobas cartridge as black-box oracles.  We feed identical
REPL input to both sides and compare the observable RAM state afterwards.  No
BIOS or BASIC ROM disassembly is consulted; every sysvar address used below is
sourced from an allowed reference listed inline.

CLEAR syntax under test:
    CLEAR [<string-space>][,<memory-top>]

Bare `CLEAR`, `CLEAR n`, and `CLEAR n,himem` are legal forms (public MSX-BASIC
language reference).  zerobas evaluates + ignores <string-space>, records
<memory-top> in HIMEM ($FC4A — C-BIOS system variables / MSX2 Technical Handbook
work-area appendix), and then continues the statement line via `jp exec_stmt`.

🔴 THE SENTENCE ABOVE USED TO LIST `CLEAR ,himem` AS A FOURTH LEGAL FORM, AND IT
IS INVERTED RATHER THAN DELETED (D-CLRFIX 2026-08-23,
docs/spec-basic-clrfix.md).  It is a **Syntax error on the VG-8020 AND the
CF-3300** — measured on both, in a trapped program (`2 0`) and in direct mode.
This file is the Phase-1 CLEAR oracle and it is wired to NO make target, so its
group 2c below asserted the acceptance for the whole life of the tree without a
gate ever running it.  ⚠️ THAT IS THE POINT WORTH KEEPING: an oracle nothing
runs is a claim nothing checks, and this one was cited by basic/PROVENANCE.md.
Group 2c is re-pointed at the refusal below.

Three test groups:

 1. Differential — HIMEM ($FC4A, 2 bytes LE) after `CLEAR 200,&HD000`:
      reference Philips VG-8020  vs  zerobas (the repack machine).
      Both must store 0x00D0 (LE: 00 D0).

 2. Functional (zerobas only) — all four CLEAR forms parse correctly and let
    the rest of the statement line execute.  Proven by chaining a POKE after
    the CLEAR and reading the sentinel byte back.  ERRMARK ($E010, zerobas
    error landmark) must stay 0x00 (no error fired).

 3. Divergence observation — CLEAR on the reference adjusts heap-related
    sysvars (MEMSIZ $FC48, STKTOP $FC4C, FRETOP $F691, VARTAB pointer $F676 …)
    that zerobas does not touch (no string heap in Phase 1).  This case
    captures a representative set of those sysvars from both sides after a
    `CLEAR 200,&HD000` and prints the observed differences; it does NOT FAIL
    the run because the divergence is intentional and documented.
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
import signal
import subprocess
import shutil
import sys
import tempfile
import time

from omsx_run import _tcl_dquote  # noqa: E402
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
if not (os.path.sep in OMSX and os.path.isfile(OMSX)):
    OMSX = "openmsx"

# Machines
REF_MACHINE  = "Philips_VG_8020"   # real built-in MSX-BASIC (no --cart)
# ⚠️ zerobas now runs on the REPACK machine, which carries the merged main ROM in
# slot 0 -- there is no cartridge to insert. It used to be C-BIOS_MSX1 (or the
# VG-8020) with the retired lean 16 KB cart in a slot; that build is gone
# (RETIRE THE LEAN 16 KB CART S3, docs/spec-lean-retire-s3-gates.md).
ZB_MACHINE   = "C-BIOS_MSX1_EU_REPACK_DISK"

# Sysvar addresses
# HIMEM: $FC4A — C-BIOS system variables (BSD-2-Clause) / MSX2 Technical
#   Handbook work-area appendix / MSX Assembly Page.  2 bytes LE.
#   CLEAR's documented home for the memory-ceiling argument.
HIMEM        = 0xFC4A

# The following sysvars are from C-BIOS system variables / MSX2 Technical
# Handbook work-area appendix (allowed sources), captured here for the
# divergence observation only — we DO NOT enforce their values.
# MEMSIZ  $FC48 — highest available RAM address (set by BIOS at boot).
# STKTOP  $FC4C — initial GOSUB/FOR stack top (CLEAR adjusts it from HIMEM).
# FRETOP  $F691 — top of the string heap (CLEAR resets to new heap top).
# STREND  $F692 — end of string space (CLEAR sets from string-space arg).
# TXTTAB  $F676 — pointer to BASIC text base (CLEAR may move it for heap).
MEMSIZ       = 0xFC48
STKTOP       = 0xFC4C
FRETOP       = 0xF691
STREND       = 0xF693   # 2 bytes: end-of-string-space pointer
TXTTAB       = 0xF676   # 2 bytes: BASIC text base pointer

# zerobas error landmark (basic/sysvars.inc — own source)
ERRMARK      = 0xE010

# A free RAM sentinel location clear of all cart regions
SENT         = 0xD000   # free RAM; used by POKE continuation tests


# ---------------------------------------------------------------------------
# openMSX run helper (mirrors basic_probe_cont.py's run() / lines_for())
# ---------------------------------------------------------------------------

def run(machine, cart, events, mems, cap_at=None, timeout=90):
    """Boot one openMSX, inject REPL events, capture memory blocks, exit.

    machine  : openMSX machine id string.
    cart     : path to cartridge ROM, or None (for the reference machine).
    events   : list of (emu_time, text) keyboard injections.
    mems     : list of (addr, length) blocks to read at cap_at.
    cap_at   : emulated-seconds capture time (default: last event + 8 s).
    Returns  : dict  hex(addr) -> hex-string (e.g. "0xFC4A" -> "00d0")
               or empty dict on timeout/failure.
    """
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="clear_cap_")
    os.close(out_fd)
    if cap_at is None:
        cap_at = (max((t for t, _ in events), default=6.0)) + 8.0
    lines = [
        "set throttle off",
        "proc __hex {dbg addr len} {",
        "  binary scan [debug read_block $dbg $addr $len] H* h; return $h",
        "}",
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
    ]
    for addr, length in mems:
        lines.append(
            f'  puts $f "mem.0x{addr:04X}=[__hex {{memory}} {addr} {length}]"')
    lines += ["  close $f", "  exit", "}"]
    for t, text in events:
        lines.append(f"after time {t:g} {{ type {_tcl_dquote(text)} }}")
    lines.append(f"after time {cap_at:g} {{ __cap }}")
    tcl = "\n".join(lines) + "\n"

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="clear_")
    os.write(fd, tcl.encode())
    os.close(fd)
    cmd = [OMSX, "-machine", machine]
    if cart:
        cmd += ["-cart", cart]
    cmd += ["-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    try:
        proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            print(f"  [TIMEOUT after {timeout}s]", file=sys.stderr)
    finally:
        os.unlink(tcl_path)
    vals = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            for ln in f:
                if ln.startswith("mem.0x"):
                    k, _, v = ln.strip().partition("=")
                    vals[k[len("mem."):]] = v
        os.unlink(out_path)
    return vals


def lines_for(*stmts):
    """Build a (time, text) event list: each stmt typed then Enter as a
    separate, later event (zerobas REPL drops a trailing CR in the same burst
    under throttle off, so Enter must be its own event; the reference is
    tolerant but we use the same schedule for both to keep the helper shared).
    """
    ev = []
    t = 6.0
    for text in stmts:
        ev.append((t, text)); t += 2.0
        ev.append((t, "\r")); t += 2.0
    return ev


def get(vals, addr):
    """Return the hex-string for addr, or None."""
    return vals.get(f"0x{addr:04X}")


def le16(hexstr):
    """Decode a 4-hex-char LE word from a captured block and return as int."""
    if hexstr is None or len(hexstr) < 4:
        return None
    lo = int(hexstr[0:2], 16)
    hi = int(hexstr[2:4], 16)
    return lo | (hi << 8)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def check(ok_ref, label, cond, detail=""):
    ok_ref[0] = ok_ref[0] and cond
    tag = "PASS" if cond else "FAIL"
    print(f"{tag}  {label}" + (f"  [{detail}]" if detail else ""))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    args = ap.parse_args()

    ok = [True]   # mutable so check() can write it

    # -----------------------------------------------------------------------
    # Case 1 — Differential: HIMEM after CLEAR 200,&HD000
    # -----------------------------------------------------------------------
    print("\n--- Case 1: Differential — HIMEM after CLEAR 200,&HD000 ---")
    HIMEM_TARGET = 0xD000   # clean address, clear of all probe-used RAM

    # Reference side (Philips VG-8020, no cart)
    ref_ev = lines_for("CLEAR 200,&HD000")
    ref_v  = run(REF_MACHINE, None, ref_ev, [(HIMEM, 2)])
    ref_himem_raw = get(ref_v, HIMEM)
    ref_himem_val = le16(ref_himem_raw)
    print(f"  ref HIMEM ($FC4A): {ref_himem_raw!r}  -> 0x{ref_himem_val:04X}"
          if ref_himem_val is not None else f"  ref HIMEM ($FC4A): <capture failed>")

    check(ok, "reference stores 0xD000 in HIMEM ($FC4A)",
          ref_himem_val == HIMEM_TARGET,
          f"got 0x{ref_himem_val:04X}" if ref_himem_val is not None else "no capture")

    # zerobas side
    zb_ev = lines_for("CLEAR 200,&HD000")
    zb_v  = run(ZB_MACHINE, None, zb_ev, [(HIMEM, 2)])
    zb_himem_raw = get(zb_v, HIMEM)
    zb_himem_val = le16(zb_himem_raw)
    print(f"  zb  HIMEM ($FC4A): {zb_himem_raw!r}  -> 0x{zb_himem_val:04X}"
          if zb_himem_val is not None else f"  zb  HIMEM ($FC4A): <capture failed>")

    check(ok, "zerobas stores 0xD000 in HIMEM ($FC4A)",
          zb_himem_val == HIMEM_TARGET,
          f"got 0x{zb_himem_val:04X}" if zb_himem_val is not None else "no capture")

    check(ok, "ref and zerobas agree on HIMEM value",
          ref_himem_val == zb_himem_val == HIMEM_TARGET,
          f"ref={ref_himem_raw!r} zb={zb_himem_raw!r}")

    # -----------------------------------------------------------------------
    # Case 2 — Functional (zerobas): syntax + line continuation
    # -----------------------------------------------------------------------
    print("\n--- Case 2: Functional — all CLEAR forms parse, line continues ---")

    # ERRMARK ($E010) starts at whatever RAM value the C-BIOS left (typically
    # 0xFF on a fresh boot).  zerobas only WRITES to ERRMARK on error, so to
    # detect a clean run we must pre-zero it with a POKE before the CLEAR, then
    # confirm it stayed 0x00.  The sentinel for continuation proof is a SEPARATE
    # POKE *after* the CLEAR on the same line — that only fires if CLEAR itself
    # parsed and executed without aborting the line.

    # 2a: CLEAR 200,&HD000 : POKE &HD000,&H5A
    #     read SENT ($D000) == 5A (line continued); ERRMARK pre-zeroed, must stay 00
    v = run(ZB_MACHINE, None,
            lines_for(f"POKE &H{ERRMARK:04X},0:CLEAR 200,&HD000:POKE &H{SENT:04X},&H5A"),
            [(SENT, 1), (ERRMARK, 1), (HIMEM, 2)])
    check(ok, "CLEAR n,himem: line continues (POKE fires, SENT=5A)",
          get(v, SENT) == "5a",
          f"SENT={get(v, SENT)!r}")
    check(ok, "CLEAR n,himem: no error (ERRMARK stays 00 after pre-zero)",
          get(v, ERRMARK) == "00",
          f"ERRMARK={get(v, ERRMARK)!r}")
    check(ok, "CLEAR n,himem: HIMEM stored correctly",
          le16(get(v, HIMEM)) == HIMEM_TARGET,
          f"HIMEM={get(v, HIMEM)!r}")

    # 2b: bare CLEAR : POKE &HD001,&H7B
    #     line continues (SENT2=7B); ERRMARK pre-zeroed, must stay 00
    SENT2 = 0xD001
    v = run(ZB_MACHINE, None,
            lines_for(f"POKE &H{ERRMARK:04X},0:CLEAR:POKE &H{SENT2:04X},&H7B"),
            [(SENT2, 1), (ERRMARK, 1)])
    check(ok, "bare CLEAR: line continues (POKE fires, SENT2=7B)",
          get(v, SENT2) == "7b",
          f"SENT2={get(v, SENT2)!r}")
    check(ok, "bare CLEAR: no error (ERRMARK stays 00 after pre-zero)",
          get(v, ERRMARK) == "00",
          f"ERRMARK={get(v, ERRMARK)!r}")

    # 2c: CLEAR ,&HD000 -- string-space omitted. 🔴 REVERSED 2026-08-23 BY
    # D-CLRFIX. This group used to assert that the line CONTINUES, that no error
    # is raised, and that HIMEM is stored. All three are the OPPOSITE of both
    # references, which answer Syntax error and store nothing. The statement now
    # ABORTS, so the trailing POKE must NOT fire and HIMEM must NOT move --
    # which is exactly what the same three probes read, with the verdicts
    # inverted. The sentinel is pre-zeroed, so "did not fire" is a reading and
    # not an absence.
    SENT3 = 0xD002
    v = run(ZB_MACHINE, None,
            lines_for(f"POKE &H{SENT3:04X},0:CLEAR ,&HD000:POKE &H{SENT3:04X},&H3C"),
            [(SENT3, 1), (HIMEM, 2)])
    check(ok, "CLEAR ,himem: the line ABORTS (POKE does NOT fire, SENT3 stays 00)",
          get(v, SENT3) == "00",
          f"SENT3={get(v, SENT3)!r}")
    check(ok, "CLEAR ,himem: HIMEM is NOT stored (the statement never got there)",
          le16(get(v, HIMEM)) != HIMEM_TARGET,
          f"HIMEM={get(v, HIMEM)!r}")

    # 2d: CLEAR 200 (himem omitted, string-space only)
    SENT4 = 0xD003
    v = run(ZB_MACHINE, None,
            lines_for(f"POKE &H{ERRMARK:04X},0:CLEAR 200:POKE &H{SENT4:04X},&H11"),
            [(SENT4, 1), (ERRMARK, 1)])
    check(ok, "CLEAR n (himem omitted): line continues (POKE fires, SENT4=11)",
          get(v, SENT4) == "11",
          f"SENT4={get(v, SENT4)!r}")
    check(ok, "CLEAR n (himem omitted): no error (ERRMARK stays 00 after pre-zero)",
          get(v, ERRMARK) == "00",
          f"ERRMARK={get(v, ERRMARK)!r}")

    # -----------------------------------------------------------------------
    # Case 3 — Divergence observation (informational, does not fail the run)
    # -----------------------------------------------------------------------
    print("\n--- Case 3: Divergence observation (informational only) ---")
    # Capture several heap-related sysvars from both sides after CLEAR 200,&HD000.
    # Sources for addresses: C-BIOS system variables / MSX2 Technical Handbook
    # work-area appendix.
    obs_mems = [(HIMEM, 2), (MEMSIZ, 2), (STKTOP, 2), (FRETOP, 2),
                (STREND, 2), (TXTTAB, 2)]

    ref_obs = run(REF_MACHINE, None,
                  lines_for("CLEAR 200,&HD000"),
                  obs_mems)
    zb_obs  = run(ZB_MACHINE, None,
                  lines_for("CLEAR 200,&HD000"),
                  obs_mems)

    sysvar_names = {
        HIMEM:  "HIMEM  $FC4A (CLEAR ceiling)",
        MEMSIZ: "MEMSIZ $FC48 (highest avail RAM)",
        STKTOP: "STKTOP $FC4C (initial GOSUB/FOR stack top)",
        FRETOP: "FRETOP $F691 (string-heap top)",
        STREND: "STREND $F693 (end of string space)",
        TXTTAB: "TXTTAB $F676 (BASIC text base pointer)",
    }
    print("  Sysvar comparison (ref vs zerobas) — divergences expected for"
          " heap-related vars:")
    any_diff = False
    for addr, length in obs_mems:
        ref_raw = get(ref_obs, addr)
        zb_raw  = get(zb_obs,  addr)
        same = ref_raw == zb_raw
        tag  = "  SAME" if same else "  DIFF"
        name = sysvar_names.get(addr, f"${ addr:04X}")
        print(f"  {tag}  {name}: ref={ref_raw!r}  zb={zb_raw!r}")
        if not same:
            any_diff = True
    if any_diff:
        print("  NOTE: divergences above are EXPECTED — zerobas has no string"
              " heap in Phase 1;\n"
              "        only HIMEM ($FC4A) is documented to match; the others"
              " are informational.")

    # -----------------------------------------------------------------------
    # Final verdict
    # -----------------------------------------------------------------------
    print()
    if ok[0]:
        print("ALL PASS")
    else:
        print("SOME FAILED")
    return 0 if ok[0] else 1


if __name__ == "__main__":
    raise SystemExit(main())
