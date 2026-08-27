#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Install zerobas-equipped C-BIOS machines into your openMSX user folder.

This writes a "C-BIOS_MSX1_EU_BASIC" machine that is byte-for-byte the stock EU
machine with ONE load-time patch on its main ROM: zerobas-main-eu.ips, the merged
repack main ROM (repacked C-BIOS + the relocated BASIC spanning $2812-$7FFF + the
cassette patch, all in one image). C-BIOS's cold-boot cartridge scan finds zerobas's
"AB" header at $4000 and calls it, so the machine boots straight to the zerobas
prompt with no cartridge inserted, and the baked-in tape code fills in C-BIOS's
failing cassette stubs so `BLOAD"CAS:",R` completes.

Slot 3 is expanded so that 3-2 holds zerobas-sub (--sub-rom): the relocated BASIC
calls sub-ROM tenants for floats, CALL FORMAT, detokenising, arrays, the string
heap and PRINT USING. ⚠️ It is NOT optional and NOT merely a per-verb dependency --
a machine with an empty 3-2 never reaches the prompt at all (measured,
docs/spec-lean-retire-s2-switch.md §2.1), so --sub-rom defaults ON.

⚠️ EU ONLY. The repack rewrites C-BIOS's page-0 layout and is built for the EU ROM
(tools/build_repacked_cbios.py). Until 2026-07-29 this installed a region-universal
page-1 splice (zerobas-msx1.ips) carrying the LEAN 16 KB build, giving _BASIC machines
for all four MSX1 C-BIOS regions; lean is retired (RETIRE THE LEAN 16 KB CART,
docs/spec-lean-retire-s2-switch.md) and regionalising the repack is its own TODO
entry. The _TAPE machines below carry no BASIC and stay region-universal.

It also writes a "<name>_TAPE" machine for EVERY stock MSX1 C-BIOS machine (all four
regions): the same stock C-BIOS with ONLY the zerobas-tape cassette patch applied (no
zerobas-BASIC patch), leaving the external cartridge slots free. C-BIOS boots to its
no-cart screen. Stock C-BIOS already ships a <CassettePort/>, so the _TAPE machine
needs nothing but the patch.

⚠️ THESE MACHINES NO LONGER CARRY A zerobas BASIC, AND NOTHING INSERTS ONE. They used
to be driven with `-cart build/basic.rom`, the lean 16 KB build, which is retired and
unbuildable (docs/spec-lean-retire-s3-gates.md). The cassette corpus
(probes/basic/basic_probe_cas_*.py, _tape_save, _bload_openstack) now runs on the
REPACK machine, which bakes the merged main ROM into slot 0 and has its own
<CassettePort/>; those probes still accept `--machine C-BIOS_MSX1_EU_TAPE` if you want
the stock-BIOS rig, but you must supply your own `--cart`. _TAPE machines are kept
because tape/tools/run_tape_regression.py and the bios_probe_* carts (which build
their own Z80 probe ROMs) need a stock BIOS with a cassette port.

With `--disk-rom`, it ALSO writes a "C-BIOS_MSX1_EU_BASIC_DISK" variant:
the same patch, plus slot 3 expanded so that slot 3-1 holds the standalone
zerobas-disk ROM behind a National-style memory-mapped WD2793 FDC (the CF-3300
connection style), with slot 3-0 keeping the 64 KB RAM. C-BIOS's boot scan finds
the disk ROM's "AB" header in slot 3-1 page 1 and calls its INIT, installing the
disk hooks + BDOS vector. Attach a FAT12 image to drive A to exercise the stack:
    openmsx -machine C-BIOS_MSX1_BASIC_DISK -diska disk/test720.dsk

It does NOT copy or modify any ROM. The generated config points at openMSX's own
bundled ROMs by absolute path and lists the .ips files as load-time <patches>
entries, so openMSX still loads the pristine ROM and patches it in memory each boot.
The disk ROM is referenced by absolute path too.

With `--real-bios-disk`, it ALSO writes a Tier-1 *provider-oracle* machine
"<MACHINE>_ZEROBASDISK" (default MACHINE: National_CF-3300): the genuine MSX1
main BIOS is kept untouched (no zerobas/tape patches -- we are NOT booting
zerobas-BASIC here), but the machine's built-in slot-3-1 disk ROM is swapped to
zerobas-disk. The real BIOS cold-boot scan finds our "AB" header, calls our INIT
(installing the H.PHYD hook), and then dispatches its own PHYDIO through that hook
into our DSKIO -- proving a real BIOS can drive zerobas-disk as a standard
provider, with no probe-injected hook in the path (see probes/disk/
disk_probe_provider_phydio.py and disk/docs/provider-oracle-scope.md):
    python3 tools/install-openmsx-machine.py --real-bios-disk --disk-rom build/disk.rom

    python3 tools/install-openmsx-machine.py            # auto-detect everything
    python3 tools/install-openmsx-machine.py --dry-run   # show what it would write
    python3 tools/install-openmsx-machine.py --disk-rom build/disk.rom  # + _DISK variants
    python3 tools/install-openmsx-machine.py --share /path/to/openmsx/share \
                                             --user  /path/to/.openMSX

Then launch openMSX and pick e.g. "C-BIOS_MSX1_EU_BASIC", or:
    openmsx -machine C-BIOS_MSX1_EU_BASIC

zerobas is MSX1 BASIC, so only the MSX1 C-BIOS variants are targeted.
"""
from __future__ import annotations

import argparse, glob, os, re, sys

import openmsx_paths  # shared cross-platform share/user dir discovery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The shipped BASIC patch: the merged repack main ROM, diffed against a pristine
# C-BIOS EU built from the pinned tag -- which is byte-identical to openMSX's own
# bundled cbios_main_msx1_eu.rom, so this applies with no C-BIOS checkout
# (measured, docs/spec-lean-retire-s2-switch.md §2).
MAIN_IPS = os.path.join(REPO, "zerobas-main-eu.ips")
TAPE_IPS = os.path.join(REPO, "tape", "zerobas-tape-msx1.ips")
DISK_ROM = os.path.join(REPO, "build", "disk.rom")
SUB_ROM = os.path.join(REPO, "build", "sub.rom")
# The repack is EU-only by construction: tools/build_repacked_cbios.py applies
# cbios-repack/eu-drop-statements.patch and reads derived/bin/cbios_main_msx1_eu.rom.
# The retired lean splice was region-universal; regionalising the repack is its own
# TODO entry. _TAPE machines are unaffected and stay region-universal.
MAIN_REGION = "C-BIOS_MSX1_EU"


def patch_config(text: str, share_machines: str, ips_list) -> str:
    """Make every bare ROM <filename> absolute, then add the .ips files as
    load-time patches on the main ROM (filename cbios_main_msx1*.rom). The
    patches are applied in the given order; they touch disjoint ROM regions."""
    def absolutize(m):
        name = m.group(2)
        if "/" in name:                      # already a path -- leave it
            return m.group(0)
        return f"{m.group(1)}{os.path.join(share_machines, name)}{m.group(3)}"
    text = re.sub(r"(<filename>)([^<]+)(</filename>)", absolutize, text)

    # Inject <patches> right after the main ROM's (now absolute) filename line.
    pat = re.compile(r"^([ \t]*)<filename>([^<]*cbios_main_msx1[^<]*)</filename>\s*$",
                     re.MULTILINE)
    def inject(m):
        ind = m.group(1)
        entries = "\n".join(f"{ind}  <ips>{p}</ips>" for p in ips_list)
        return (f"{m.group(0)}\n"
                f"{ind}<patches>\n"
                f"{entries}\n"
                f"{ind}</patches>")
    text, n = pat.subn(inject, text)
    if n != 1:
        raise RuntimeError(f"expected exactly one main-ROM filename, found {n}")
    return text


def expand_slot3(text: str, disk_rom_abs: str = "", sub_rom_abs: str = "") -> str:
    """Expand the (unexpanded) slot-3 RAM block of a stock C-BIOS MSX1 machine
    into subslots: 3-0 keeps the 64 KB RAM, 3-1 holds the zerobas-disk ROM behind
    a National-style memory-mapped WD2793 (CF-3300 connection style; the register
    map our driver targets at $7FB8), 3-2 holds zerobas-sub (the built-in MSX2-style
    sub-ROM, a plain 32 KB ROM mapped linearly across BOTH pages). Slot 3-3 is left
    empty. Either ROM may be omitted, leaving its subslot empty.

    ⚠️ The SUB-ROM is not optional for a working repack BASIC. It hosts the page-0
    and page-1 tenants (fp_sqrt..fp_rnd, format_tenant, detok/arrays/strheap/
    printusing), and BASIC reaches into them during startup: with 3-2 empty the machine
    does not reach a prompt at all -- the screen fills with garbage (measured,
    docs/spec-lean-retire-s2-switch.md §2.1). It is placed in 3-2 per the
    2026-07-11 slot-map amendment, matching tools/install-repack-machine.py.

    The stock block is:
        <primary slot="3">
          <RAM id="Main RAM">
            <mem base="0x0000" size="0x10000"/>
          </RAM>
        </primary>
    """
    pat = re.compile(r'[ \t]*<primary slot="3">.*?</primary>\s*', re.DOTALL)
    if disk_rom_abs:
        disk_block = (
            '      <secondary slot="1">\n'
            '        <WD2793 id="zerobas-disk FDC">\n'
            '          <connectionstyle>National</connectionstyle>\n'
            '          <drives>1</drives>\n'
            '          <rom>\n'
            f'            <filename>{disk_rom_abs}</filename>\n'
            '          </rom>\n'
            '          <mem base="0x4000" size="0x8000"/>\n'
            '        </WD2793>\n'
            '      </secondary>\n\n'
        )
    else:
        disk_block = '      <secondary slot="1"/>\n\n'
    if sub_rom_abs:
        sub_block = (
            '      <secondary slot="2">\n'
            '        <ROM id="zerobas-sub ROM">\n'
            '          <rom>\n'
            f'            <filename>{sub_rom_abs}</filename>\n'
            '          </rom>\n'
            '          <mem base="0x0000" size="0x8000"/>\n'
            '        </ROM>\n'
            '      </secondary>\n\n'
        )
    else:
        sub_block = '      <secondary slot="2"/>\n\n'
    block = (
        '    <primary slot="3">\n\n'
        '      <secondary slot="0">\n'
        '        <RAM id="Main RAM">\n'
        '          <mem base="0x0000" size="0x10000"/>\n'
        '        </RAM>\n'
        '      </secondary>\n\n'
        + disk_block
        + sub_block +
        '      <secondary slot="3"/>\n\n'
        '    </primary>\n\n'
    )
    text, n = pat.subn(block, text)
    if n != 1:
        raise RuntimeError(f"expected exactly one slot-3 primary block, found {n}")
    return text


def zerobas_disk_extension(disk_rom_abs: str) -> str:
    """A pluggable openMSX EXTENSION that puts zerobas-disk behind a National-style
    WD2793 in any free slot. Lets a *real-BIOS* host machine (e.g. a Philips VG-8020
    loaded with the zerobas-BASIC cartridge) drive it through the standard $4010 DSKIO
    -- a cross-host validation that the whole stack is BIOS-independent (works on a
    real MSX BIOS, not just C-BIOS). Same WD2793 wiring as the C-BIOS _BASIC_DISK
    slot-3-1 block, but slot="any" so openMSX auto-slots it.
        openmsx -machine C-BIOS_MSX1_EU_BASIC \\
                -ext zerobas-disk -diska disk/test720.dsk
    NOTE: zerobas-disk provides only the sector DRIVER (DSKIO/BDOS), not a Disk BASIC
    language extension -- so the disk verbs come from zerobas BASIC itself, not from
    the host's own BASIC (a bare host BASIC sees no FILES/DSKI$)."""
    return (
        '<?xml version="1.0" ?>\n'
        "<!DOCTYPE msxconfig SYSTEM 'msxconfig2.dtd'>\n"
        "<msxconfig>\n"
        "  <info>\n"
        "    <name>zerobas-disk</name>\n"
        "    <manufacturer>zerobas</manufacturer>\n"
        "    <code>zerobas-disk</code>\n"
        "    <release_year></release_year>\n"
        "    <description>zerobas-disk standard MSX disk interface (National-style"
        " WD2793) as a pluggable cartridge, for cross-host BIOS-independence"
        " validation.</description>\n"
        "    <type>external disk interface</type>\n"
        "  </info>\n"
        "  <devices>\n"
        '    <primary slot="any">\n'
        '      <secondary slot="any">\n'
        '        <WD2793 id="zerobas-disk FDC">\n'
        "          <connectionstyle>National</connectionstyle>\n"
        "          <drives>1</drives>\n"
        "          <rom>\n"
        f"            <filename>{disk_rom_abs}</filename>\n"
        "          </rom>\n"
        '          <mem base="0x4000" size="0x8000"/>\n'
        "        </WD2793>\n"
        "      </secondary>\n"
        "    </primary>\n"
        "  </devices>\n"
        "</msxconfig>\n"
    )


def real_bios_disk_machine(stock_text: str, share_machines: str,
                           disk_rom_abs: str) -> str:
    """Build a Tier-1 provider-oracle machine from a *real-BIOS* MSX1 machine
    that already ships a disk ROM in slot 3-1 (e.g. openMSX's National_CF-3300):
    keep the genuine main BIOS untouched, but swap the slot-3-1 disk ROM to
    zerobas-disk. The point is that the *real* BIOS cold-boot scan finds our
    "AB" header in slot 3-1 and calls our INIT (installing the H.PHYD hook) and
    then dispatches its own PHYDIO through that hook into our DSKIO -- with no
    probe-injected hook anywhere in the path.

    This differs from the C-BIOS _BASIC_DISK variant in two ways: (1) the main
    BIOS is the stock machine's genuine MSX1 BIOS (no zerobas/tape IPS patches --
    we are NOT booting zerobas-BASIC here, we are letting a real BIOS drive us as
    a provider); (2) slot 3 is already expanded with a WD2793 in the stock XML,
    so we only retarget the disk ROM's <rom> block rather than expanding slot 3.

    Mechanics: absolutize every bare ROM <filename> (so the genuine BIOS ROM
    resolves), then replace the WD2793's disk-ROM <rom>...</rom> block (filename
    + the stock <sha1>) with a single <filename> pointing at zerobas-disk. The
    stock disk ROM's sha1 must go: it would no longer match our ROM and openMSX
    would refuse to load. The BIOS ROM keeps its sha1 (still the genuine ROM)."""
    def absolutize(m):
        name = m.group(2)
        if "/" in name:                      # already a path -- leave it
            return m.group(0)
        return f"{m.group(1)}{os.path.join(share_machines, name)}{m.group(3)}"
    text = re.sub(r"(<filename>)([^<]+)(</filename>)", absolutize, stock_text)

    # Replace the WD2793's disk-ROM block. Match the <rom>..</rom> that sits
    # inside the WD2793 device (the only <WD2793> in a stock disk MSX1 XML).
    pat = re.compile(
        r"(<WD2793\b[^>]*>.*?)<rom>\s*<filename>[^<]*</filename>\s*"
        r"(?:<sha1>[^<]*</sha1>\s*)?</rom>",
        re.DOTALL)
    repl = (r"\1<rom>\n"
            f"            <filename>{disk_rom_abs}</filename>\n"
            r"          </rom>")
    text, n = pat.subn(repl, text)
    if n != 1:
        raise RuntimeError(
            f"expected exactly one WD2793 disk-ROM block, found {n} "
            f"(is this a real-BIOS MSX1 machine with a built-in disk ROM?)")
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--share", help="openMSX share dir (contains machines/)")
    ap.add_argument("--user", help="openMSX user dir (e.g. ~/.openMSX)")
    ap.add_argument("--disk-rom", nargs="?", const=DISK_ROM, default=None,
                    metavar="ROM",
                    help="also write _BASIC_DISK variants with zerobas-disk in "
                         f"slot 3-1 (default ROM: {DISK_ROM})")
    ap.add_argument("--real-bios-disk", nargs="?", const="National_CF-3300",
                    default=None, metavar="MACHINE",
                    help="also write a Tier-1 provider-oracle machine "
                         "<MACHINE>_ZEROBASDISK that keeps a real MSX1 BIOS but "
                         "swaps its built-in disk ROM to zerobas-disk "
                         "(default MACHINE: National_CF-3300). Uses --disk-rom's "
                         "ROM, or build/disk.rom if --disk-rom is absent.")
    # NOT opt-in, unlike --disk-rom: a _BASIC machine with an empty slot 3-2 does not
    # boot at all -- measured, docs/spec-lean-retire-s2-switch.md §2.1. Defaulting it ON
    # means the installer cannot quietly write an unbootable release machine.
    ap.add_argument("--sub-rom", default=SUB_ROM, metavar="ROM",
                    help=f"zerobas-sub ROM for slot 3-2 (default: {SUB_ROM}). The "
                         "relocated BASIC calls its tenants during startup; a machine "
                         "without it does not reach a prompt.")
    ap.add_argument("--dry-run", action="store_true", help="print, don't write")
    args = ap.parse_args()

    if not os.path.isfile(MAIN_IPS):
        sys.exit(f"error: shipped BASIC patch not found: {MAIN_IPS}\n"
                 f"       it is a TRACKED deliverable; regenerate it with "
                 f"`make release` (needs CBIOS=<c-bios checkout>).")
    if not os.path.isfile(TAPE_IPS):
        sys.exit(f"error: tape patch not found: {TAPE_IPS} (run `make -C tape` first)")
    # ONE patch for the BASIC machines: the merged repack main ROM already bakes in
    # tape/tape.asm, so applying the tape patch on top would double-patch page 0.
    # (The retired lean splice touched page 1 only and needed the tape patch beside it.)
    ips_list = [MAIN_IPS]

    sub_rom = os.path.abspath(args.sub_rom)
    if not os.path.isfile(sub_rom):
        sys.exit(f"error: sub ROM not found: {sub_rom} (run `make sub` first)\n"
                 f"       it is not optional -- the relocated BASIC calls its slot-3-2 "
                 f"tenants during startup, and a machine without it does not boot.")

    disk_rom = None
    if args.disk_rom is not None:
        disk_rom = os.path.abspath(args.disk_rom)
        if not os.path.isfile(disk_rom):
            sys.exit(f"error: disk ROM not found: {disk_rom} (run `make disk` first)")

    # The Tier-1 provider machine needs a zerobas-disk ROM too; default to
    # --disk-rom's value, else the built-in build/disk.rom.
    real_disk_rom = None
    if args.real_bios_disk is not None:
        real_disk_rom = disk_rom or os.path.abspath(DISK_ROM)
        if not os.path.isfile(real_disk_rom):
            sys.exit(f"error: disk ROM not found: {real_disk_rom} "
                     f"(run `make disk` first)")

    share = openmsx_paths.find_share(args.share)
    user = openmsx_paths.find_user(args.user)
    share_machines = os.path.join(share, "machines")
    user_machines = os.path.join(user, "share", "machines")

    # MSX1 C-BIOS only -- zerobas is MSX1 BASIC.
    stock = sorted(p for p in glob.glob(os.path.join(share_machines, "C-BIOS_MSX1*.xml"))
                   if "_BASIC" not in p)
    if not stock:
        sys.exit(f"error: no MSX1 C-BIOS machines in {share_machines}")

    if not args.dry_run:
        os.makedirs(user_machines, exist_ok=True)

    print(f"source machines : {share_machines}")
    print(f"install into    : {user_machines}")
    print(f"zerobas patch   : {MAIN_IPS}  ({MAIN_REGION} only)")
    print(f"tape patch      : {TAPE_IPS}  (all regions, _TAPE machines)")
    if sub_rom:
        print(f"sub ROM         : {sub_rom}")
    if disk_rom:
        print(f"disk ROM        : {disk_rom}")
    print()
    seen_region = False
    for src in stock:
        base = os.path.splitext(os.path.basename(src))[0]      # C-BIOS_MSX1_EU
        stock_text = open(src).read()
        # _TAPE: stock C-BIOS + ONLY the tape patch (no zerobas patch), cart slots
        # free -- the open-stack / round-trip tape regression runs on this. Region-
        # universal: it carries no BASIC, so the repack's EU-only-ness does not apply.
        tout = os.path.join(user_machines, f"{base}_TAPE.xml")
        ttext = patch_config(stock_text, share_machines, [TAPE_IPS])
        if args.dry_run:
            print(f"would write {os.path.basename(tout)}")
        else:
            openmsx_paths.publish(tout, ttext)
            print(f"wrote {base}_TAPE   (-> machine \"{base}_TAPE\")")
        # The BASIC machines exist for the ONE region the repack is built for.
        if base != MAIN_REGION:
            continue
        seen_region = True
        out = os.path.join(user_machines, f"{base}_BASIC.xml")
        # Slot 3 is expanded even with no disk, because the sub-ROM lives in 3-2.
        out_text = expand_slot3(patch_config(stock_text, share_machines, ips_list),
                                "", sub_rom)
        if args.dry_run:
            print(f"would write {os.path.basename(out)}")
        else:
            openmsx_paths.publish(out, out_text)
            print(f"wrote {base}_BASIC   (-> machine \"{base}_BASIC\")")
        if disk_rom:
            dout = os.path.join(user_machines, f"{base}_BASIC_DISK.xml")
            dtext = expand_slot3(patch_config(stock_text, share_machines, ips_list),
                                 disk_rom, sub_rom)
            if args.dry_run:
                print(f"would write {os.path.basename(dout)}")
            else:
                openmsx_paths.publish(dout, dtext)
                print(f"wrote {base}_BASIC_DISK  (-> machine \"{base}_BASIC_DISK\")")
    # A silent zero-BASIC-machine run is the vacuity failure here: openMSX renaming or
    # dropping its EU C-BIOS machine would leave _TAPE machines written and no BASIC at
    # all, which reads as "installed fine" (S1's §3.1.3-§3.1.6 lesson, one layer up).
    if not seen_region:
        sys.exit(f"error: no {MAIN_REGION} machine among the C-BIOS MSX1 configs in "
                 f"{share_machines}\n       the repack BASIC is built for that region "
                 f"only, so NO BASIC machine was written.\n"
                 f"       found: {', '.join(os.path.splitext(os.path.basename(p))[0] for p in stock)}")

    # --- stale LEAN machines from a pre-2026-07-29 install ---------------------
    # This used to write a _BASIC/_BASIC_DISK per region from zerobas-msx1.ips. That
    # patch is deleted from the tree, so any config still naming it now points at a
    # missing file -- and it sits in the user's openMSX dir under a name that reads
    # like a current machine. Report, never delete: removing files from someone's
    # openMSX folder is not this tool's call.
    stale = []
    for p in sorted(glob.glob(os.path.join(user_machines, "C-BIOS_MSX1*_BASIC*.xml"))):
        try:
            if "zerobas-msx1.ips" in open(p, encoding="utf-8", errors="replace").read():
                stale.append(os.path.splitext(os.path.basename(p))[0])
        except OSError:
            pass
    if stale:
        print()
        print("warning: these installed machines still reference the RETIRED lean build")
        print("         (zerobas-msx1.ips, deleted from the tree) and will not boot:")
        for name in stale:
            print(f"           {name}")
        print(f"         remove them from {user_machines} when convenient.")
    # --- pluggable zerobas-disk extension (cross-host BIOS-independence) ------
    if disk_rom:
        user_ext = os.path.join(user, "share", "extensions")
        eout = os.path.join(user_ext, "zerobas-disk.xml")
        if args.dry_run:
            print("would write extensions/zerobas-disk.xml")
        else:
            os.makedirs(user_ext, exist_ok=True)
            openmsx_paths.publish(eout, zerobas_disk_extension(disk_rom))
            print("wrote zerobas-disk extension  (-> -ext zerobas-disk)")
    # --- Tier-1 provider-oracle machine: real BIOS + zerobas-disk ------------
    if real_disk_rom:
        src = os.path.join(share_machines, f"{args.real_bios_disk}.xml")
        if not os.path.isfile(src):
            sys.exit(f"error: real-BIOS machine not found: {src} "
                     f"(pass --real-bios-disk <MACHINE> for one openMSX ships)")
        base = args.real_bios_disk                              # National_CF-3300
        out = os.path.join(user_machines, f"{base}_ZEROBASDISK.xml")
        out_text = real_bios_disk_machine(open(src).read(), share_machines,
                                          real_disk_rom)
        if args.dry_run:
            print(f"would write {os.path.basename(out)}")
        else:
            openmsx_paths.publish(out, out_text)
            print(f"wrote {base}_ZEROBASDISK  (-> machine \"{base}_ZEROBASDISK\", "
                  f"real {base} BIOS + zerobas-disk in slot 3-1)")

    tail = " (attach a FAT12 image: -diska disk/test720.dsk)" if disk_rom else ""
    print(f"\nDone. Launch openMSX and pick one of the *_BASIC machines.{tail}")


if __name__ == "__main__":
    main()
