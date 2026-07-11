#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""S2a boot gate for zerobas-sub — the built-in sub-ROM's discovery + two-page ABI.

Proves the S2a skeleton end-to-end WITHOUT any main-ROM change (the main-ROM
discovery + dispatch land in the eviction session, S2b). Boots a minimal C-BIOS
MSX1 with slot 3 expanded so that 3-0 = RAM, 3-2 = zerobas-sub (build/sub.rom,
the 32 KB two-page skeleton). No cartridge, no zerobas-BASIC, no disk — C-BIOS
just needs to bring RAM up and expose CALSLT at $001C.

Then it injects a 44-byte Z80 stub into RAM ($C000) and redirects the CPU to it.
The stub does the two CALSLTs the sub-ROM ABI defines (spec §3c), each under DI:

    di
    xor a / ld ($F105),a          ; clear SUB_PING
    ld iy,$8B00 / ld ix,$0010     ; slot 3-2 ($8B), page-0 entry $0010
    call $001C                    ; CALSLT -> sub_p0_ping writes SUB_PING=$C0
    ld a,($F105) / ld ($C100),a   ; stash the page-0 result
    ... repeat with ix=$4010      ; page-1 entry -> sub_p1_ping writes $C1
    ld a,($F105) / ld ($C101),a   ; stash the page-1 result
    halt                          ; capture breakpoint

A CALSLT to $0010 in slot 3-2 maps that subslot into PAGE 0 (main-BASIC-visible
island) and runs the page-0 ping; a CALSLT to $4010 maps it into PAGE 1 (the
BIOS-visible island) and runs the page-1 ping. The two pings write distinct tags
($C0 / $C1), so a correct round-trip proves BOTH pages are present and dispatch
page-selectively — i.e. the container is correctly placed in 3-2 and the
opposite-island two-page ABI works. This is a STRONGER proof than reading the
CD/S1 marker bytes (it proves executability, not just presence).

Needs build/sub.rom (make sub) and openMSX's bundled C-BIOS MSX1 ROMs. Installs a
throwaway machine into the openMSX user dir.

    python3 probes/basic/basic_probe_subrom_boot.py
"""
from __future__ import annotations

import glob
import os
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import openmsx_paths  # noqa: E402

SUB_ROM = os.path.join(REPO, "build", "sub.rom")
OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
MACHINE = "ZEROBAS_SUBROM_PROBE"

# The dual-CALSLT stub (assembled from the .asm in this file's docstring; bytes
# verified with pasmo). Loaded at $C000; halt sentinel at $C02B. Results land at
# $C100 (page-0 ping tag) and $C101 (page-1 ping tag).
STUB_ADDR = 0xC000
STUB_HALT = 0xC02B
RES_P0, RES_P1 = 0xC100, 0xC101
STUB_BYTES = bytes([
    0xF3,                    # di
    0xAF, 0x32, 0x05, 0xF1,  # xor a ; ld ($F105),a       (clear SUB_PING)
    0xFD, 0x21, 0x00, 0x8B,  # ld iy,$8B00                (slot 3-2)
    0xDD, 0x21, 0x10, 0x00,  # ld ix,$0010                (page-0 entry)
    0xCD, 0x1C, 0x00,        # call $001C                 (CALSLT)
    0x3A, 0x05, 0xF1,        # ld a,($F105)
    0x32, 0x00, 0xC1,        # ld ($C100),a               (page-0 result)
    0xAF, 0x32, 0x05, 0xF1,  # xor a ; ld ($F105),a       (clear SUB_PING)
    0xFD, 0x21, 0x00, 0x8B,  # ld iy,$8B00                (slot 3-2)
    0xDD, 0x21, 0x10, 0x40,  # ld ix,$4010                (page-1 entry)
    0xCD, 0x1C, 0x00,        # call $001C                 (CALSLT)
    0x3A, 0x05, 0xF1,        # ld a,($F105)
    0x32, 0x01, 0xC1,        # ld ($C101),a               (page-1 result)
    0x76,                    # halt                       (capture bp)
])
assert len(STUB_BYTES) == 44, f"stub size changed: {len(STUB_BYTES)}"
EXPECT_P0, EXPECT_P1 = 0xC0, 0xC1


def find_rom(pattern: str) -> str:
    base = os.path.dirname(openmsx_paths.find_share())
    hits = glob.glob(os.path.join(base, "**", pattern), recursive=True)
    for share in getattr(openmsx_paths, "SHARE_CANDIDATES", []):
        hits += glob.glob(os.path.join(share, "**", pattern), recursive=True)
    if not hits:
        sys.exit(f"{pattern} not found in any openMSX share dir")
    # Prefer the EU region to match the project's primary machine.
    eu = [h for h in hits if "_eu" in os.path.basename(h)]
    return (eu or hits)[0]


def install_machine() -> None:
    """Minimal C-BIOS MSX1: main ROM in slot 0, slot 3 expanded (3-0 = 64 KB RAM,
    3-2 = zerobas-sub). Mirrors the slot-map amendment (RAM 3-0, sub 3-2)."""
    main = find_rom("cbios_main_msx1*.rom")
    logo = find_rom("cbios_logo_msx1.rom")
    mdir = os.path.join(openmsx_paths.find_user(), "share", "machines")
    os.makedirs(mdir, exist_ok=True)
    cfg = f"""<?xml version="1.0" ?>
<!DOCTYPE msxconfig SYSTEM 'msxconfig2.dtd'>
<msxconfig>
  <info><manufacturer>zerobas</manufacturer><code>subrom S2a probe</code>
    <type>MSX</type></info>
  <CassettePort/>
  <devices>
    <primary slot="0">
      <ROM id="C-BIOS Main ROM"><mem base="0x0000" size="0x8000"/>
        <rom><filename>{main}</filename></rom></ROM>
      <ROM id="C-BIOS Logo ROM"><mem base="0x8000" size="0x4000"/>
        <rom><filename>{logo}</filename></rom></ROM>
    </primary>
    <primary external="true" slot="1"/>
    <primary external="true" slot="2"/>
    <primary slot="3">
      <secondary slot="0">
        <RAM id="Main RAM"><mem base="0x0000" size="0x10000"/></RAM>
      </secondary>
      <secondary slot="1"/>
      <secondary slot="2">
        <ROM id="zerobas-sub ROM"><mem base="0x0000" size="0x8000"/>
          <rom><filename>{SUB_ROM}</filename></rom></ROM>
      </secondary>
      <secondary slot="3"/>
    </primary>
    <PPI id="ppi"><io base="0xA8" num="4"/><sound><volume>16000</volume></sound>
      <key_ghosting>false</key_ghosting><keyboard_type>int</keyboard_type>
      <has_keypad>false</has_keypad><code_kana_locks>false</code_kana_locks>
      <graph_locks>false</graph_locks></PPI>
    <VDP id="VDP"><io base="0x98" num="2" type="O"/><io base="0x98" num="2" type="I"/>
      <version>TMS9929A</version><vram>16</vram></VDP>
    <PSG id="PSG"><type>YM2149</type><io base="0xA0" num="4" type="IO"/>
      <sound><volume>21000</volume></sound></PSG>
    <PrinterPort id="Printer Port"><io base="0x90" num="2"/></PrinterPort>
  </devices>
</msxconfig>
"""
    open(os.path.join(mdir, MACHINE + ".xml"), "w").write(cfg)


def run() -> dict | None:
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="subrom_cap_")
    os.close(out_fd)
    stub_hex = "".join(f"{b:02x}" for b in STUB_BYTES)
    lines = [
        "set throttle off",
        "proc __hex {addr} {",
        "  binary scan [debug read_block memory $addr 1] H* h; return $h",
        "}",
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
        f'  puts $f "p0=[__hex {RES_P0}]"',
        f'  puts $f "p1=[__hex {RES_P1}]"',
        "  close $f",
        "  exit",
        "}",
        # After C-BIOS has brought RAM up (no-cart screen), inject the stub,
        # clear the result cells, arm a breakpoint at the stub's halt, and
        # redirect the CPU into the stub. The bp fires the moment both CALSLTs
        # have returned.
        f"after time 4.5 {{",
        f"  debug write_block memory {STUB_ADDR} [binary format H* {{{stub_hex}}}]",
        f"  debug write memory {RES_P0} 0x00",
        f"  debug write memory {RES_P1} 0x00",
        f"  debug set_bp {STUB_HALT} {{}} {{ __cap }}",
        f"  reg PC {STUB_ADDR}",
        f"}}",
        # Safety net: if a CALSLT hangs (missing/misplaced sub-ROM), capture
        # anyway so the gate FAILs cleanly instead of the host watchdog killing it.
        "after time 8.0 { __cap }",
    ]
    tcl = "\n".join(lines) + "\n"
    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="subrom_")
    os.write(fd, tcl.encode())
    os.close(fd)

    cmd = [OMSX, "-machine", MACHINE, "-command", "set renderer none", "-script", tcl_path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + 60
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            print("TIMEOUT")
            return None
    finally:
        os.unlink(tcl_path)

    if not os.path.exists(out_path):
        return None
    res = {}
    for ln in open(out_path):
        if "=" in ln:
            k, v = ln.strip().split("=", 1)
            res[k] = int(v, 16) if v else None
    os.unlink(out_path)
    return res


def main() -> int:
    if not os.path.isfile(SUB_ROM):
        sys.exit(f"missing {SUB_ROM}\n  build it: make sub")
    install_machine()
    res = run()
    if res is None:
        print("subrom boot gate: FAIL (no capture)")
        return 1

    p0, p1 = res.get("p0"), res.get("p1")
    p0_ok = p0 == EXPECT_P0
    p1_ok = p1 == EXPECT_P1
    print(f"page-0 CALSLT $0010 -> SUB_PING = ${p0:02X} (expect ${EXPECT_P0:02X}): "
          f"{'PASS' if p0_ok else 'FAIL'}")
    print(f"page-1 CALSLT $4010 -> SUB_PING = ${p1:02X} (expect ${EXPECT_P1:02X}): "
          f"{'PASS' if p1_ok else 'FAIL'}")
    ok = p0_ok and p1_ok
    print("-------------------")
    print("subrom S2a boot gate:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
