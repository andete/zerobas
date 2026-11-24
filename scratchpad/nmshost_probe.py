#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-NMSHOST step 1 -- trace the Philips NMS 1200 disk cartridge's boot, step by step, on the VG-8020 (the reference)
and on zerobas's no-disk build (C-BIOS_MSX1_EU_REPACK_NODISK), both with `-ext Philips_NMS_1200` and a private copy of
the user's DOS disk in drive A.

Clean room: the cartridge and both BIOSes are black boxes. Recorded: the emulated time of every WRITE to the work-area
cells a disk ROM claims (HIMEM, DRVTBL, the disk hooks, the boot hand-off hooks), with the value written and the
PRIMARY / SECONDARY SLOT of the code doing it (page and slot only -- never a PC value, never a ROM byte); the first
time code runs in page 1 from the cartridge's slot; the slot map (configuration); the work area and the text screen
at the end. Disk activity is seen only through the disk image (sectors the machine changed) and the screen.

    python3 -u scratchpad/nmshost_probe.py [DOSDISK] > scratchpad/AE_nmshost_step1.out 2>&1
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
import openmsx_paths  # noqa: E402

DOS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
MACHINES = [("ref", "Philips_VG_8020"), ("zb", "C-BIOS_MSX1_EU_REPACK_NODISK")]
ONLY = os.environ.get("NMSHOST_ONLY")       # "ref" / "zb": run one machine
SECONDS = int(os.environ.get("NMSHOST_SECONDS", "30"))

# cell -> name; a watchpoint on each (writes only)
CELLS = [
    (0xFC4A, 2, "HIMEM"), (0xF349, 2, "DISK_HIMSAV?"), (0xFB21, 8, "DRVTBL"),
    (0xFFA7, 5, "H.PHYD"), (0xFFAC, 5, "H.FORM"), (0xFEDA, 5, "H.STKE"), (0xFEDF, 5, "H.ISFL"),
    (0xFDEF, 5, "H.DSKO"), (0xF37D, 3, "BDOS $F37D"), (0x0005, 1, "page-0 $0005"),
]

TCL = r"""
set renderer none
set throttle off
set ::log [open $::env(LOGF) w]
proc slotof {pg} { lassign [get_selected_slot $pg] ps ss; if {$ss eq "X"} {return "$ps"} ; return "$ps-$ss" }
proc who {} { set pc [reg pc]; set pg [expr {$pc >> 14}]; return "page$pg@[slotof $pg]" }
proc t {} { return [format %.6f [machine_info time]] }
set ::seen_p1 0
set ::nw 0
proc on_write {name addr} {
  if {$::seen_p1 && [info exists ::ring_on] && $::ring_on && [who] eq "page0@0" && $name eq "H.STKE"} {
    puts $::log "RESTART [t] the start-up's H.STKE write is back (by page0@0) -- the last 80 page@slot changes:"
    foreach l $::ring { puts $::log "  $l" }
    puts $::log "DIRECT-COUNT $::direct"
    flush $::log; exit
  }
  incr ::nw
  if {$::nw > 4000} { if {$::nw == 4001} { puts $::log "CAP [t] more than 4000 watched writes -- the rest not logged" }; return }
  puts $::log "W [t] $name [format %04X $::wp_last_address] := [format %02X $::wp_last_value] by [who]"
}
""" + "\n".join(
    f"debug set_watchpoint write_mem {{0x{a:04X} 0x{a + n - 1:04X}}} {{}} {{on_write \"{nm}\" 0x{a:04X}}}"
    for a, n, nm in CELLS) + r"""
proc sample {} {
  set pc [reg pc]
  if {!$::seen_p1 && ($pc >> 14) == 1 && [slotof 1] eq $::env(CARTSLOT)} {
    set ::seen_p1 1
    puts $::log "P1 [t] first code run in page 1 from the cartridge's slot $::env(CARTSLOT) SP=[format %04X [reg sp]] IFF=[reg iff]"
    # from here: every change of the executing page@slot, with SP, for 300 changes (page and slot only, no PC value)
    set ::trace_left [expr {[info exists ::env(NMSHOST_RING)] ? 0 : 300}]; set ::last_who ""
    set ::ring {}; set ::direct 0; set ::ring_on [info exists ::env(NMSHOST_RING)]
    debug set_condition {$::trace_left > 0 || $::ring_on} {
      set w [who]
      if {$w ne $::last_who} {
        set line "X [t] $w SP=[format %04X [reg sp]] IFF=[reg iff]"
        # zerobas ONLY (NMSHOST_ZBPC): the address entered, when it is zerobas's own ROM (page 0 / page 1 of slot 0)
        # or RAM (page 2 / 3) -- never on the reference machine, never an address inside the cartridge
        if {[info exists ::env(NMSHOST_ZBPC)] && ([string match "page0@0" $w] || [string match "page1@0" $w] || [string match "page3@*" $w] || [string match "page2@*" $w])} {
          append line " at=[format %04X [reg pc]]"
        }
        if {$::trace_left > 0} { puts $::log $line; incr ::trace_left -1 }
        if {$::ring_on} {
          # a jump from page-3 RAM straight into page 1 of slot 0: not a published (page-0) BIOS entry
          if {[string match "page3@*" $::last_who] && [string match "page1@0*" $w]} {
            incr ::direct; puts $::log "D [t] RAM -> page1@0 (direct, #$::direct) SP=[format %04X [reg sp]]"
            if {$::direct == 1} {
              puts $::log "FIRSTJUMP [t] -- the last 80 page@slot changes before it:"
              foreach l $::ring { puts $::log "  $l" }
            }
          }
          lappend ::ring $line; if {[llength $::ring] > 80} { set ::ring [lrange $::ring 1 end] }
        }
        set ::last_who $w
      }
    }
  }
  if {!$::seen_p1} { after time 0.0005 sample }
}
after time 0.0005 sample
proc tick {} { puts $::log "T [t]"; flush $::log; after time 1 tick }
after time 1 tick
after time """ + str(SECONDS) + r""" {
  puts $::log "END [t]"
  set s ""
  foreach {a n} {0xFC4A 2 0xFB21 8 0xFFA7 5 0xFEDA 5 0xFDEF 5 0xF37D 3} {
    set v ""; for {set i 0} {$i < $n} {incr i} { append v [format %02X [peek [expr {$a + $i}]]] }
    append s " [format %04X $a]=$v"
  }
  puts $::log "CELLS$s"
  puts $::log "PAGES [slotof 0] [slotof 1] [slotof 2] [slotof 3]"
  puts $::log "SCREEN"
  puts $::log [get_screen]
  close $::log
  exit
}
"""


def slotmap(machine):
    """the cartridge's slot, from openMSX's slot map (configuration, not ROM content)"""
    cmd = [openmsx_paths.find_openmsx_binary(), "-machine", machine, "-ext", "Philips_NMS_1200", "-command",
           "set renderer none; after time 1 { set f [open $::env(LOGF) w]; puts $f [slotmap]; close $f; exit }"]
    out = probe_tmp.tmp(f"nmshost_slotmap_{machine}.txt")
    subprocess.run(omsx_preflight.guarded(cmd), env=dict(os.environ, LOGF=out), stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=120)
    text = open(out).read()
    slot = None
    for line in text.splitlines():
        if line.strip().startswith("slot") and "NMS 1200" not in line:
            cur = line.split(":")[0].replace("slot", "").strip().split(" ")[0]   # "1 (slota)" -> "1", "3-1" kept
        if "NMS 1200" in line or "1200" in line:
            slot = cur if slot is None else slot
    return slot, text


def run(tag, machine):
    cart, smap = slotmap(machine)
    dsk = probe_tmp.tmp(f"nmshost_{tag}.dsk")
    shutil.copyfile(DOS, dsk)
    before = open(dsk, "rb").read()
    tcl = probe_tmp.tmp(f"nmshost_{tag}.tcl")
    open(tcl, "w").write(TCL)
    keep = "/tmp/zerobas/nmshost_keep"            # survives probe_tmp's cleanup, so a timed-out run can be read
    os.makedirs(keep, exist_ok=True)
    log = os.path.join(keep, f"nmshost_{tag}.log")
    cmd = [openmsx_paths.find_openmsx_binary(), "-machine", machine, "-ext", "Philips_NMS_1200", "-diska", dsk,
           "-script", tcl]
    extra = {"NMSHOST_ZBPC": "1"} if tag == "zb" else {}
    try:
        subprocess.run(omsx_preflight.guarded(cmd), env=dict(os.environ, LOGF=log, CARTSLOT=str(cart), **extra),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    except subprocess.TimeoutExpired:
        print(f"!! {tag}: openMSX did not finish {SECONDS} s emulated within 300 s real -- log so far below")
    after = open(dsk, "rb").read()
    changed = [i // 512 for i in range(0, len(after), 512) if after[i:i + 512] != before[i:i + 512]]
    print(f"===== {tag}: {machine} + Philips_NMS_1200 (cartridge slot {cart}) =====")
    print("slot map:")
    for line in smap.splitlines():
        if line.strip():
            print("   " + line)
    body = open(log).read() if os.path.exists(log) else "<NO LOG>"
    print(body.rstrip())
    print(f"disk sectors changed by the run: {changed if changed else 'none'}")
    print()


def main():
    print(f"D-NMSHOST step 1: DOS disk = private copy of {os.path.basename(DOS)}; {SECONDS} s emulated per machine")
    for tag, m in MACHINES:
        if ONLY and tag != ONLY:
            continue
        run(tag, m)


if __name__ == "__main__":
    main()
