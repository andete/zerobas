# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOADRUN speed: every FDC command zerobas's driver writes during a program,
stamped in emulated time, with the sector and track registers -- so the gap from
one sector's end to the next read command is visible. RAM-mapped FDC registers of
OUR disk ROM's slot ($7FB8 command, $7FB9 track, $7FBA sector); clean room.

    [FDC_MACH=National_CF-3300] python3 -u scratchpad/fdccmd_probe.py [program-name]

FDC_MACH (2026-11-07): another disk machine -- the CF-3300's WD2793 is the same chip in
the same "National" layout at slot 3-1 (openMSX's machine config), so the same
watchpoints read its commands. Each command also logs BC / DE / HL (registers only;
where the bytes are headed, and which sector) -- no ROM byte read.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs as r  # noqa: E402
import probe_tmp  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 else "loadspeed_prog"
dump = probe_tmp.tmp("fdccmd.txt")
if os.path.exists(dump):
    os.unlink(dump)
r.GAP_TCL = r.GAP_TCL + """
set ::__cf [open {%s} w]
proc __fc {} {
  puts $::__cf "[format %%.4f [machine_info time]] C [format %%02X $::wp_last_value] [format %%04X [reg PC]] cl=[format %%04X [__rd16 0xF41C]] bc=[format %%04X [reg bc]] de=[format %%04X [reg de]] hl=[format %%04X [reg hl]]"
}
proc __fs {} {
  puts $::__cf "[format %%.4f [machine_info time]] S [format %%02X $::wp_last_value]"
}
debug set_watchpoint write_mem 0x7FB8 {[pc_in_slot 3]} __fc
debug set_watchpoint write_mem 0x7FBA {[pc_in_slot 3]} __fs
""" % dump
if os.environ.get("FDC_DRQ"):
    # FDC_DRQ=1 (2026-11-07, D-LOSTDATA): a D row at the FIRST data-register read after each
    # command (the moment the transfer starts) and a J row at every JIFFY write (an
    # interrupt taken). A J between a command and its D = the wait ran with interrupts on.
    # Addresses and times only: the data register is I/O, JIFFY a documented work-area cell.
    r.GAP_TCL = r.GAP_TCL + """
set ::__armed 0
proc __fc2 {} { set ::__armed 1 }
proc __fd {} {
  if {$::__armed} {
    set ::__armed 0
    puts $::__cf "[format %.4f [machine_info time]] D [format %04X [reg PC]]"
  }
}
proc __fj {} { puts $::__cf "[format %.4f [machine_info time]] J" }
debug set_watchpoint write_mem 0x7FB8 {[pc_in_slot 3]} __fc2
debug set_watchpoint read_mem 0x7FBB {[pc_in_slot 3]} __fd
debug set_watchpoint write_mem 0xFC9E {} __fj
"""
_pp = os.path.join(REPO, "probes", "programs", name + ".bas")
text = open(_pp if os.path.exists(_pp) else os.path.join(REPO, "scratchpad", name + ".bas")).read()
res = r.run(os.environ.get("FDC_MACH", r.DISK_ZB[0]), "fdccmd", text, gaps=True)
print(res[0])
rows = open(dump).read().splitlines()
print(len(rows), "rows")
for line in rows:
    print(line)
