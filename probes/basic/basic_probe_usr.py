#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""USR calling-convention oracle — observe how MSX-BASIC passes the argument
to, and reads the result from, a DEF USR machine-code routine.

METHODOLOGY (clean-room)
------------------------
The reference MSX-BASIC ROM (Philips VG-8020) is a black box: we inject a
small hand-authored Z80 stub via openMSX's `debug write_block` command, call
USR0() from BASIC with two distinctive argument values (12345 = $3039, and
258 = $0102), and inspect the RAM snapshot the stub writes.  No disassembly
of any reference ROM, BIOS, or MSX-BASIC source was consulted.  Every sysvar
address cited has an inline allowed-source citation.

HAND-AUTHORED STUB DISASSEMBLY
-------------------------------
The stub is loaded at $D000 (free page-3 RAM, same region used by
basic_probe_cont.py).  The snapshot area starts at $D100.  Every byte was
authored here; no byte was lifted from any disassembly.

Opcodes cited from: Z80 CPU User Manual (Zilog, 1979/public) and the Z80
instruction-set tables on the MSX Assembly Page (map.grauw.nl), an allowed
source.

  Addr  Bytes         Mnemonic / comment
  ----  -----------   --------------------------------------------------
  D000  32 06 D1      LD ($D106), A     ; save entering A before clobbering it
  D003  22 00 D1      LD ($D100), HL    ; save entering HL (arg register pair)
  D006  7B            LD A, E           ; A = E (entering DE low byte)
  D007  32 02 D1      LD ($D102), A     ; store E
  D00A  7A            LD A, D           ; A = D (entering DE high byte)
  D00B  32 03 D1      LD ($D103), A     ; store D
  D00E  79            LD A, C           ; A = C (entering BC low byte)
  D00F  32 04 D1      LD ($D104), A     ; store C
  D012  78            LD A, B           ; A = B (entering BC high byte)
  D013  32 05 D1      LD ($D105), A     ; store B
  D016  3A 63 F6      LD A, ($F663)     ; read VALTYP ($F663, MSX2 TH work-area)
  D019  32 07 D1      LD ($D107), A     ; save VALTYP to snapshot
  D01C  21 F6 F7      LD HL, $F7F6     ; HL = DAC base ($F7F6, MSX2 TH work-area)
  D01F  11 08 D1      LD DE, $D108     ; DE = snapshot dest for DAC
  D022  01 08 00      LD BC, 8          ; BC = 8 (DAC is 8 bytes)
  D025  ED B0         LDIR              ; copy DAC[0..7] → $D108..$D10F
  D027  C9            RET               ; return to BASIC (do not crash it)

Stub is 40 bytes ($D000..$D027).

Snapshot layout at $D100 (16 bytes):
  $D100-$D101  entering L, H  (i.e. entering HL low-byte-first = LE)
  $D102        entering E
  $D103        entering D
  $D104        entering C
  $D105        entering B
  $D106        entering A
  $D107        VALTYP ($F663, 1 byte) at the moment USR is called
  $D108-$D10F  DAC    ($F7F6, 8 bytes) at the moment USR is called

Address sources (all allowed):
  VALTYP = $F663 — MSX2 Technical Handbook work-area appendix (sysvars).
  DAC    = $F7F6 — MSX2 Technical Handbook work-area appendix (sysvars).
  USRTAB = $F39A — C-BIOS system variables (BSD 2-clause); the 10 USR
                   vectors used by DEF USR 0..9 (zerobas/basic/sysvars.inc).

CASES RUN
---------
  ref-12345 : Philips_VG_8020,   USR0(12345)  — 12345 = $3039
  ref-258   : Philips_VG_8020,   USR0(258)    — 258   = $0102
  zb-12345  : C-BIOS_MSX1+cart,  USR0(12345)
  zb-258    : C-BIOS_MSX1+cart,  USR0(258)

For each case we report:
  * the full snapshot hex
  * which slot(s) carry the argument value ($3039 or $0102)
  * the VALTYP byte ($D107)
  * a PASS/FAIL based on whether the measurements confirm the
    expected calling convention (DAC for reference; HL for zerobas).
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

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
if not (os.path.sep in OMSX and os.path.isfile(OMSX)):
    OMSX = "openmsx"

# Machines
REF_MACHINE = "Philips_VG_8020"   # real built-in MSX-BASIC
ZB_MACHINE  = "C-BIOS_MSX1"       # zerobas under test (needs --cart)

# Stub and snapshot addresses (free page-3 RAM; same $D000 region as cont.py)
STUB_ADDR    = 0xD000   # where we write the hand-authored Z80 stub
SNAP_ADDR    = 0xD100   # where the stub writes its snapshot
SNAP_LEN     = 16       # bytes: HL(2) DE(2) BC(2) A(1) VALTYP(1) DAC(8)

# Sysvar addresses cited from MSX2 Technical Handbook work-area appendix
# (an allowed source).
VALTYP_ADDR  = 0xF663   # VALTYP: floating-point accumulator type byte (1 byte)
DAC_ADDR     = 0xF7F6   # DAC: floating-point accumulator data (8 bytes)

# Hand-authored stub bytes (see disassembly in module docstring above).
# Each instruction annotated: op1 [op2 [op3]] — see Z80 CPU User Manual.
#
#  32 06 D1  = LD ($D106),A   ; save entering A to snap[6]
#  22 00 D1  = LD ($D100),HL  ; save entering HL to snap[0..1]
#  7B        = LD A,E          ; A = E
#  32 02 D1  = LD ($D102),A   ; save E to snap[2]
#  7A        = LD A,D          ; A = D
#  32 03 D1  = LD ($D103),A   ; save D to snap[3]
#  79        = LD A,C          ; A = C
#  32 04 D1  = LD ($D104),A   ; save C to snap[4]
#  78        = LD A,B          ; A = B
#  32 05 D1  = LD ($D105),A   ; save B to snap[5]
#  3A 63 F6  = LD A,($F663)   ; A = VALTYP (MSX2 TH work-area)
#  32 07 D1  = LD ($D107),A   ; save VALTYP to snap[7]
#  21 F6 F7  = LD HL,$F7F6    ; HL = DAC base (MSX2 TH work-area)
#  11 08 D1  = LD DE,$D108    ; DE = snap[8] destination
#  01 08 00  = LD BC,8        ; 8 bytes to copy
#  ED B0     = LDIR           ; block copy DAC → snap[8..15]
#  C9        = RET            ; return to BASIC
STUB_BYTES = bytes([
    0x32, 0x06, 0xD1,  # LD ($D106),A
    0x22, 0x00, 0xD1,  # LD ($D100),HL
    0x7B,              # LD A,E
    0x32, 0x02, 0xD1,  # LD ($D102),A
    0x7A,              # LD A,D
    0x32, 0x03, 0xD1,  # LD ($D103),A
    0x79,              # LD A,C
    0x32, 0x04, 0xD1,  # LD ($D104),A
    0x78,              # LD A,B
    0x32, 0x05, 0xD1,  # LD ($D105),A
    0x3A, 0x63, 0xF6,  # LD A,($F663)
    0x32, 0x07, 0xD1,  # LD ($D107),A
    0x21, 0xF6, 0xF7,  # LD HL,$F7F6
    0x11, 0x08, 0xD1,  # LD DE,$D108
    0x01, 0x08, 0x00,  # LD BC,8
    0xED, 0xB0,        # LDIR
    0xC9,              # RET
])
assert len(STUB_BYTES) == 40, f"stub size changed: {len(STUB_BYTES)}"

# Tcl hex string for debug write_block
STUB_HEX = " ".join(f"{b:02x}" for b in STUB_BYTES)


def run(machine, cart, arg_val, cap_at=None, timeout=80):
    """Boot openMSX, inject the stub, call USR0(<arg_val>), capture snapshot.

    Returns a bytes object of length SNAP_LEN, or None on failure.

    Protocol:
      t= 6.0  type "DEFUSR0=&HD000"  (register the stub)
      t= 8.0  type Enter
      t=10.0  type "A=USR0(<arg_val>)"
      t=12.0  type Enter
      t=18.0  debug read_block snapshot → file → exit

    The stub injection (debug write_block) runs before any typing, at Tcl
    startup time, inside the same -script file.  The `set throttle off` at
    the top of the script ensures emulated time advances as fast as the host
    allows, so the absolute-time schedule is robust.
    """
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="usr_cap_")
    os.close(out_fd)
    if cap_at is None:
        cap_at = 18.0

    lines = [
        "set throttle off",
        # Capture helper and proc defs first (no timing dependency).
        "proc __hex {dbg addr len} {",
        "  binary scan [debug read_block $dbg $addr $len] H* h; return $h",
        "}",
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
        f'  puts $f "snap=[__hex {{memory}} {SNAP_ADDR} {SNAP_LEN}]"',
        "  close $f",
        "  exit",
        "}",
        # Inject stub AFTER machine boot (t=4.5 s — well after the BIOS/BASIC
        # has initialised RAM; the real VG-8020 takes ~3 s to reach the REPL
        # under `throttle off`).  Use `after time` so injection happens in the
        # emulation timeline, not at Tcl-script-parse time.
        # debug write_block: write_block <debuggable> <address> <binary-data>
        # binary format H* converts a hex string to raw bytes.
        f'after time 4.5 {{ debug write_block memory {STUB_ADDR} [binary format H* {{{STUB_HEX.replace(" ", "")}}}] }}',
        # Keyboard events: each text then Enter as a SEPARATE later event.
        # t=6.0 / 8.0: DEFUSR0=&HD000  (after stub is injected at 4.5)
        # t=10.0 / 12.0: A=USR0(<arg>)
        f'after time 6.0  {{ type {_tcl_dquote("DEFUSR0=&HD000")} }}',
        f'after time 8.0  {{ type {_tcl_dquote(chr(13))} }}',
        f'after time 10.0 {{ type {_tcl_dquote(f"A=USR0({arg_val})")} }}',
        f'after time 12.0 {{ type {_tcl_dquote(chr(13))} }}',
        f'after time {cap_at:g} {{ __cap }}',
    ]

    tcl = "\n".join(lines) + "\n"
    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="usr_")
    os.write(fd, tcl.encode())
    os.close(fd)

    cmd = [OMSX, "-machine", machine]
    if cart:
        cmd += ["-cart", cart]
    cmd += ["-command", "set renderer none", "-script", tcl_path]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl_path)

    snap = None
    if os.path.exists(out_path):
        with open(out_path) as f:
            for ln in f:
                if ln.startswith("snap="):
                    hexstr = ln.strip()[5:]
                    if len(hexstr) == SNAP_LEN * 2:
                        snap = bytes.fromhex(hexstr)
        os.unlink(out_path)
    return snap


def decode_snap(snap, arg_val):
    """Decode the snapshot bytes and return a dict with labelled fields."""
    if snap is None or len(snap) < SNAP_LEN:
        return None
    entering_l  = snap[0]
    entering_h  = snap[1]
    entering_hl = entering_l | (entering_h << 8)
    entering_e  = snap[2]
    entering_d  = snap[3]
    entering_de = entering_e | (entering_d << 8)
    entering_c  = snap[4]
    entering_b  = snap[5]
    entering_bc = entering_c | (entering_b << 8)
    entering_a  = snap[6]
    valtyp      = snap[7]
    dac         = snap[8:16]

    # Does DAC[0..1] (little-endian 16-bit word at start of DAC) hold arg_val?
    # Hypothesis A: arg at DAC+0..DAC+1 LE
    dac_w0      = dac[0] | (dac[1] << 8)
    # Does DAC[2..3] (LE 16-bit word at offset 2 into DAC) hold arg_val?
    # Hypothesis B (to confirm by observation): arg at DAC+2..DAC+3 LE
    dac_w2      = dac[2] | (dac[3] << 8)

    return {
        "HL":      entering_hl,
        "DE":      entering_de,
        "BC":      entering_bc,
        "A":       entering_a,
        "VALTYP":  valtyp,
        "DAC":     dac,
        "DAC_w0":  dac_w0,   # 16-bit LE word at DAC+0
        "DAC_w2":  dac_w2,   # 16-bit LE word at DAC+2
        "raw_snap": snap,
    }


def print_snap(label, snap, arg_val):
    """Print a formatted snapshot report."""
    print(f"  [{label}] arg={arg_val} (${arg_val:04X})")
    if snap is None:
        print("    <no snapshot captured>")
        return
    d = decode_snap(snap, arg_val)
    snap_hex = " ".join(f"{b:02x}" for b in d["raw_snap"])
    print(f"    raw snapshot : {snap_hex}")
    print(f"    entering HL  = ${d['HL']:04X}  (arg? {'YES' if d['HL'] == arg_val else 'no'})")
    print(f"    entering DE  = ${d['DE']:04X}  (arg? {'YES' if d['DE'] == arg_val else 'no'})")
    print(f"    entering BC  = ${d['BC']:04X}  (arg? {'YES' if d['BC'] == arg_val else 'no'})")
    print(f"    entering A   = ${d['A']:02X}")
    print(f"    VALTYP       = ${d['VALTYP']:02X}  (hypothesis: 2=integer for ref; 0=unused for zb)")
    dac_hex = " ".join(f"{b:02x}" for b in d["DAC"])
    print(f"    DAC[0..7]    = {dac_hex}")
    print(f"      DAC+0..1   = ${d['DAC_w0']:04X}  (arg? {'YES' if d['DAC_w0'] == arg_val else 'no'})")
    print(f"      DAC+2..3   = ${d['DAC_w2']:04X}  (arg? {'YES' if d['DAC_w2'] == arg_val else 'no'})")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    args = ap.parse_args()
    cart = args.cart

    # Two distinctive argument values to disambiguate byte order and location.
    ARGS = [12345, 258]   # 12345=$3039, 258=$0102
    # 12345 in LE = 39 30;  258 in LE = 02 01 — easy to spot in the snapshot.

    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        print(f"{status}  {label}" + (f"  [{detail}]" if detail else ""))
        ok = ok and cond

    # ------------------------------------------------------------------ #
    # Reference side (Philips_VG_8020 — real MSX-BASIC, no cart)          #
    # We hypothesize: VALTYP=2 (integer), arg in DAC[0..1] (LE word).     #
    # ------------------------------------------------------------------ #
    print("\n=== Reference (Philips_VG_8020) ===")
    ref_snaps = {}
    for av in ARGS:
        s = run(REF_MACHINE, cart=None, arg_val=av)
        ref_snaps[av] = s
        print_snap("ref", s, av)

    # Measure: does DAC[2..3] (LE 16-bit word at offset 2 into DAC) carry the arg?
    # Initial hypothesis was DAC+0..1; measurement below confirms the actual offset.
    ref_dac_w0_carries = all(
        ref_snaps[av] is not None and decode_snap(ref_snaps[av], av)["DAC_w0"] == av
        for av in ARGS
    )
    ref_dac_w2_carries = all(
        ref_snaps[av] is not None and decode_snap(ref_snaps[av], av)["DAC_w2"] == av
        for av in ARGS
    )
    # Measure: does VALTYP == 2 (integer) in both cases?
    ref_valtyp_2 = all(
        ref_snaps[av] is not None and decode_snap(ref_snaps[av], av)["VALTYP"] == 2
        for av in ARGS
    )
    # Measure: is HL the arg value itself?
    ref_hl_carries = all(
        ref_snaps[av] is not None and decode_snap(ref_snaps[av], av)["HL"] == av
        for av in ARGS
    )
    # Measure: does HL == DAC base address ($F7F6)?
    ref_hl_is_dac = all(
        ref_snaps[av] is not None and decode_snap(ref_snaps[av], av)["HL"] == DAC_ADDR
        for av in ARGS
    )

    print()
    # The critical measurement: where in DAC is the integer argument?
    check("ref: DAC+2..3 (LE word at offset 2 in DAC) carries the argument value",
          ref_dac_w2_carries,
          f"12345→DAC+2..3=${decode_snap(ref_snaps[12345], 12345)['DAC_w2']:04X}"
          if ref_snaps[12345] else "no data")
    check("ref: DAC+0..1 does NOT carry the argument (arg is at DAC+2, not DAC+0)",
          not ref_dac_w0_carries,
          f"12345→DAC+0..1=${decode_snap(ref_snaps[12345], 12345)['DAC_w0']:04X}"
          if ref_snaps[12345] else "no data")
    check("ref: VALTYP == 2 (integer) when an integer argument is passed",
          ref_valtyp_2,
          f"12345→VALTYP=${decode_snap(ref_snaps[12345], 12345)['VALTYP']:02X}"
          if ref_snaps[12345] else "no data")
    check("ref: HL == DAC base address $F7F6 on entry (ref leaves HL pointing at DAC)",
          ref_hl_is_dac,
          f"12345→HL=${decode_snap(ref_snaps[12345], 12345)['HL']:04X}"
          if ref_snaps[12345] else "no data")
    check("ref: HL is not the raw argument value (arg is in DAC, not HL itself)",
          not ref_hl_carries,
          f"12345→HL=${decode_snap(ref_snaps[12345], 12345)['HL']:04X}"
          if ref_snaps[12345] else "no data")

    # ------------------------------------------------------------------ #
    # zerobas side (C-BIOS_MSX1 + cart)                                   #
    # We expect: arg in HL, VALTYP ($F663) not set to 2 by zerobas.       #
    # ------------------------------------------------------------------ #
    print("\n=== zerobas (C-BIOS_MSX1 + cart) ===")
    zb_snaps = {}
    for av in ARGS:
        s = run(ZB_MACHINE, cart=cart, arg_val=av)
        zb_snaps[av] = s
        print_snap("zb", s, av)

    zb_hl_carries = all(
        zb_snaps[av] is not None and decode_snap(zb_snaps[av], av)["HL"] == av
        for av in ARGS
    )
    zb_dac_w2_carries = all(
        zb_snaps[av] is not None and decode_snap(zb_snaps[av], av)["DAC_w2"] == av
        for av in ARGS
    )
    # zerobas's own VALTYP ($E0C8) is unrelated to the reference's $F663;
    # we expect $F663 to be untouched (not set to 2) by zerobas.
    zb_valtyp_not_2 = all(
        zb_snaps[av] is not None and decode_snap(zb_snaps[av], av)["VALTYP"] != 2
        for av in ARGS
    )

    print()
    check("zb: HL carries the argument value (own-design integer-only convention)",
          zb_hl_carries,
          f"12345→HL=${decode_snap(zb_snaps[12345], 12345)['HL']:04X}"
          if zb_snaps[12345] else "no data")
    check("zb: DAC+2..3 does NOT carry the argument (zerobas skips the DAC/VALTYP protocol)",
          not zb_dac_w2_carries,
          f"12345→DAC+2..3=${decode_snap(zb_snaps[12345], 12345)['DAC_w2']:04X}"
          if zb_snaps[12345] else "no data")
    check("zb: VALTYP ($F663) not set to 2 by zerobas (DAC/VALTYP protocol not used)",
          zb_valtyp_not_2,
          f"12345→VALTYP=${decode_snap(zb_snaps[12345], 12345)['VALTYP']:02X}"
          if zb_snaps[12345] else "no data")

    # ------------------------------------------------------------------ #
    # Summary of measured divergence                                        #
    # ------------------------------------------------------------------ #
    print()
    print("=== Measured divergence ===")
    if ref_snaps[12345] and zb_snaps[12345]:
        rd = decode_snap(ref_snaps[12345], 12345)
        zd = decode_snap(zb_snaps[12345], 12345)
        ref_conv = (
            f"DAC+2..3 = LE-word ${rd['DAC_w2']:04X} (= 12345), "
            f"VALTYP=${rd['VALTYP']:02X} (integer), "
            f"HL=${rd['HL']:04X} (= DAC base address, not the arg itself)"
        )
        zb_conv = (
            f"HL=${zd['HL']:04X} (= 12345 = arg), "
            f"DAC+2..3=${zd['DAC_w2']:04X} (not the arg), "
            f"VALTYP=${zd['VALTYP']:02X} (not set to integer)"
        )
        print(f"  reference passes USR arg via {ref_conv}")
        print(f"  zerobas  passes USR arg via {zb_conv}")
        print()
        print("  MEASURED DIVERGENCE:")
        print("  reference: integer USR argument in DAC+2..3 (LE word); VALTYP=$02")
        print("             (integer); HL points to DAC base ($F7F6), not the arg.")
        print("  zerobas:   integer USR argument in HL (direct); DAC untouched;")
        print("             VALTYP ($F663) not set by zerobas (own-design HL-only")
        print("             calling convention, no DAC/VALTYP protocol).")
    else:
        print("  (insufficient data — one or more snapshots not captured)")

    print()
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
