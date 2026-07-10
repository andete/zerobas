#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""End-to-end boot gate for the cbios-repack main ROM (arc WS-3 / S4).

Boots the merged 32 KB main ROM -- repacked C-BIOS (page-0 dead ROM-BASIC dropped)
+ relocated BASIC ($2812-$7FFF, "AB" header pinned at $4000) + tape page-0
completions -- as a real MSX main ROM, with NO cartridge inserted, and asserts:

  1. cold boot reaches the zerobas title + `zb>` prompt (BASIC is found and INIT'd
     via C-BIOS's page-1 cartridge scan, exactly as the shipping stack), and
  2. the interpreter is live: typing `PRINT 12+34` prints `46`.

This is the proof the whole repack is sound end-to-end: BASIC relocated below the
old $4000 wall still boots and runs. Needs build/zerobas-main-eu.rom (Makefile
prerequisite) -- itself built from the user's C-BIOS checkout (no C-BIOS bytes
in-repo, D1). Installs a throwaway machine into the openMSX user dir.

    python3 probes/basic/basic_probe_repack_boot.py
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import openmsx_paths  # noqa: E402

MERGED = os.path.join(REPO, "build", "zerobas-main-eu.rom")
OMSX_RUN = os.path.join(REPO, "probes", "lib", "omsx_run.py")
MACHINE = "ZEROBAS_MAIN_EU_PROBE"
COLS, ROWS = 40, 24
NLEN = COLS * ROWS


def install_machine() -> None:
    logos = glob.glob(os.path.join(os.path.dirname(openmsx_paths.find_share()),
                                   "**", "cbios_logo_msx1.rom"), recursive=True)
    if not logos:
        for share in openmsx_paths.SHARE_CANDIDATES:
            logos += glob.glob(os.path.join(share, "**", "cbios_logo_msx1.rom"),
                               recursive=True)
    if not logos:
        sys.exit("cbios_logo_msx1.rom not found in any openMSX share dir")
    mdir = os.path.join(openmsx_paths.find_user(), "share", "machines")
    os.makedirs(mdir, exist_ok=True)
    cfg = f"""<?xml version="1.0" ?>
<!DOCTYPE msxconfig SYSTEM 'msxconfig2.dtd'>
<msxconfig>
  <info><manufacturer>zerobas</manufacturer><code>repack boot probe</code>
    <type>MSX</type></info>
  <CassettePort/>
  <devices>
    <primary slot="0">
      <ROM id="C-BIOS Main ROM"><mem base="0x0000" size="0x8000"/>
        <rom><filename>{MERGED}</filename></rom></ROM>
      <ROM id="C-BIOS Logo ROM"><mem base="0x8000" size="0x4000"/>
        <rom><filename>{logos[0]}</filename></rom></ROM>
    </primary>
    <primary external="true" slot="1"/>
    <primary external="true" slot="2"/>
    <primary slot="3"><RAM id="Main RAM"><mem base="0x0000" size="0x10000"/></RAM></primary>
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


def capture(type_events, settle):
    cap = f"/tmp/repack_boot_{settle}.txt"
    cmd = [sys.executable, OMSX_RUN, "--machine", MACHINE, "--time", str(settle),
           "--mem", f"VRAM:0x0000:{NLEN}", "--out", cap, "--timeout", "180"]
    for delay, text in type_events:
        cmd += ["--type", text, "--type-delay", str(delay)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    txt = open(cap).read() if os.path.exists(cap) else ""
    m = re.search(rf"mem\.VRAM:0x0000:{NLEN}=([0-9a-f]+)", txt)
    if not m:
        return None
    data = bytes.fromhex(m.group(1))
    return ["".join(chr(c) if 32 <= c < 127 else " " for c in data[i*COLS:(i+1)*COLS]).rstrip()
            for i in range(ROWS)]


def show(label, rows):
    print(f"----- {label} -----")
    for row in rows or []:
        if row:
            print(f"| {row}")


def main() -> int:
    if not os.path.isfile(MERGED):
        sys.exit(f"missing {MERGED}\n  build it: make build/zerobas-main-eu.rom")
    install_machine()

    boot = capture([], 5.0)
    if not boot:
        print("FAIL: no VRAM capture on cold boot"); return 1
    show("cold boot", boot)
    boot_ok = "zerobas" in "\n".join(boot) and "zb>" in "\n".join(boot)

    # zerobas drops a trailing CR sharing the text burst, so Enter is a separate,
    # later --type event (per basic_probe_print).
    run = capture([(6.0, "PRINT 12+34"), (9.0, "\r")], 14.0)
    show("after PRINT 12+34", run)
    print_ok = "46" in "\n".join(run or [])

    print("-------------------")
    print("cold boot title + zb> prompt:", "PASS" if boot_ok else "FAIL")
    print("live PRINT 12+34 -> 46      :", "PASS" if print_ok else "FAIL")
    ok = boot_ok and print_ok
    print("repack boot gate:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
