#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Install the REPACK disk machine — the acceptance target for the reloc BASIC build.

The standing acceptance gates (diskbasic_acceptance.py / disk_bdos_acceptance.py) run on
"C-BIOS_MSX1_EU_BASIC_DISK": stock C-BIOS with zerobas BASIC applied as a page-1 IPS patch,
plus zerobas-disk in slot 3-1. That machine proves the LEAN 16 KB basic.rom against the
CF-3300 oracle. But the string-engine arc (S3+) introduced a second, BEHAVIOURALLY DISTINCT
build — the relocated BASIC ($2812-$7FFF, STRMAX=64, concat-aware str_eval, relocated
kwtable) merged into C-BIOS as build/zerobas-main-eu.rom. "lean matches the oracle" no
longer implies "repack matches the oracle" for the string-touching verbs.

This writes a sibling machine "C-BIOS_MSX1_EU_REPACK_DISK" that is the same disk hardware
(zerobas-disk behind a National-style WD2793 in slot 3-1, 64 KB RAM in slot 3-0) but whose
slot-0 main ROM is the MERGED repack ROM directly — no IPS patch, BASIC is baked in. With
--sub-rom it also places zerobas-sub (the built-in MSX2-style sub-ROM) in the previously-empty
slot 3-2, per the 2026-07-11 slot-map amendment (RAM stays 3-0, disk stays 3-1, sub takes 3-2).
Point the acceptance runner at it with the omsx_run remap:

    ZEROBAS_MACHINE_MAP=C-BIOS_MSX1_EU_BASIC_DISK=C-BIOS_MSX1_EU_REPACK_DISK \
        python3 probes/disk/diskbasic_acceptance.py

so every probe's zerobas side boots the repack build while its CF-3300 oracle side is
unchanged. See the Makefile `diskbasic-acceptance-repack` / `bdos-acceptance-repack` targets.

The config is self-contained (like probes/basic/basic_probe_repack_boot.py's machine): it
does NOT patch a stock C-BIOS config, it points slot 0 straight at the merged ROM. Slot 3 is
expanded exactly like tools/install-openmsx-machine.py's `_BASIC_DISK` variant.

    python3 tools/install-repack-machine.py --merged build/zerobas-main-eu.rom \
                                            --disk-rom build/disk.rom
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import openmsx_paths  # noqa: E402

MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"


def find_logo() -> str:
    """Locate cbios_logo_msx1.rom in any openMSX share dir (same search the repack-boot
    probe uses)."""
    cands = []
    share = openmsx_paths.find_share()
    cands.append(os.path.join(os.path.dirname(share), "**", "cbios_logo_msx1.rom"))
    for s in getattr(openmsx_paths, "SHARE_CANDIDATES", []):
        cands.append(os.path.join(s, "**", "cbios_logo_msx1.rom"))
    for pat in cands:
        hits = glob.glob(pat, recursive=True)
        if hits:
            return hits[0]
    sys.exit("cbios_logo_msx1.rom not found in any openMSX share dir")


def sub_secondary(sub_rom_abs: str) -> str:
    """The slot-3-2 secondary block holding zerobas-sub — the built-in MSX2-style
    sub-ROM, a plain 32 KB ROM mapped linearly across BOTH pages ($0000-$7FFF).
    RAM stays in 3-0 and disk in 3-1 (the 2026-07-11 slot-map amendment: the
    sub-ROM takes the previously-empty 3-2 so RAM does not move). Empty string
    when no sub ROM is supplied, so the machine falls back to an empty 3-2."""
    if not sub_rom_abs:
        return '      <secondary slot="2"/>'
    return (
        '      <secondary slot="2">\n'
        '        <ROM id="zerobas-sub ROM">\n'
        '          <rom>\n'
        f'            <filename>{sub_rom_abs}</filename>\n'
        '          </rom>\n'
        '          <mem base="0x0000" size="0x8000"/>\n'
        '        </ROM>\n'
        '      </secondary>'
    )


def config(merged_abs: str, logo_abs: str, disk_rom_abs: str, sub_rom_abs: str = "") -> str:
    """Slot 0 = merged repack main ROM (0x0000-0x7FFF) + C-BIOS logo (0x8000-0xBFFF);
    slot 3 expanded: 3-0 = 64 KB RAM, 3-1 = zerobas-disk behind a National WD2793,
    3-2 = zerobas-sub (the built-in sub-ROM, when --sub-rom is given). Hardware
    (PPI/VDP/PSG/Printer/Cassette) mirrors the stock C-BIOS MSX1 EU machine and
    the repack-boot probe machine so the only difference from the lean disk machine is the
    baked-in relocated BASIC (plus the sub-ROM in the previously-empty 3-2)."""
    sub_block = sub_secondary(sub_rom_abs)
    return f"""<?xml version="1.0" ?>
<!DOCTYPE msxconfig SYSTEM 'msxconfig2.dtd'>
<msxconfig>
  <info>
    <manufacturer>zerobas</manufacturer>
    <code>repack disk (acceptance)</code>
    <type>MSX</type>
  </info>
  <CassettePort/>
  <devices>
    <primary slot="0">
      <ROM id="C-BIOS Main ROM"><mem base="0x0000" size="0x8000"/>
        <rom><filename>{merged_abs}</filename></rom></ROM>
      <ROM id="C-BIOS Logo ROM"><mem base="0x8000" size="0x4000"/>
        <rom><filename>{logo_abs}</filename></rom></ROM>
    </primary>
    <primary external="true" slot="1"/>
    <primary external="true" slot="2"/>

    <primary slot="3">

      <secondary slot="0">
        <RAM id="Main RAM">
          <mem base="0x0000" size="0x10000"/>
        </RAM>
      </secondary>

      <secondary slot="1">
        <WD2793 id="zerobas-disk FDC">
          <connectionstyle>National</connectionstyle>
          <drives>1</drives>
          <rom>
            <filename>{disk_rom_abs}</filename>
          </rom>
          <mem base="0x4000" size="0x8000"/>
        </WD2793>
      </secondary>

{sub_block}

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


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--merged", default=os.path.join(os.path.dirname(HERE), "build",
                                                      "zerobas-main-eu.rom"),
                    help="merged repack main ROM (default build/zerobas-main-eu.rom)")
    ap.add_argument("--disk-rom", default=os.path.join(os.path.dirname(HERE), "build",
                                                       "disk.rom"),
                    help="zerobas-disk ROM (default build/disk.rom)")
    ap.add_argument("--sub-rom", nargs="?", const=os.path.join(os.path.dirname(HERE),
                                                               "build", "sub.rom"),
                    default=None, metavar="ROM",
                    help="also place zerobas-sub (the built-in sub-ROM) in slot 3-2 "
                         "(default ROM: build/sub.rom). Omit to leave 3-2 empty.")
    ap.add_argument("--dry-run", action="store_true", help="print the config, do not write")
    args = ap.parse_args()

    merged = os.path.abspath(args.merged)
    disk = os.path.abspath(args.disk_rom)
    for p, what in ((merged, "merged main ROM (build it: make build/zerobas-main-eu.rom)"),
                    (disk, "disk ROM (build it: make disk)")):
        if not os.path.isfile(p):
            sys.exit(f"missing {what}: {p}")

    sub = ""
    if args.sub_rom is not None:
        sub = os.path.abspath(args.sub_rom)
        if not os.path.isfile(sub):
            sys.exit(f"missing sub ROM (build it: make sub): {sub}")

    cfg = config(merged, find_logo(), disk, sub)
    if args.dry_run:
        print(cfg)
        return 0

    mdir = os.path.join(openmsx_paths.find_user(), "share", "machines")
    os.makedirs(mdir, exist_ok=True)
    out = os.path.join(mdir, MACHINE + ".xml")
    open(out, "w").write(cfg)
    subtail = ", zerobas-sub in slot 3-2" if sub else ""
    print(f"wrote {MACHINE}  (-> machine \"{MACHINE}\": merged repack ROM in slot 0, "
          f"zerobas-disk in slot 3-1{subtail})")
    print(f"     {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
