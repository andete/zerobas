#!/usr/bin/env python3
"""D-GAUNTBOOT: why GAUNT.DSK stopped booting at D-HERRO (81097b93, bisected).

Boots the image on both machines and records, black box: every execution of the RAM hook
H.ERRO ($FFB1) -- a breakpoint on that RAM address, logging the time and register E (the
code) -- and at fixed times the hook's 5 bytes, ERR ($F414), ERL ($F6B3), CURLINE
($F41C) and PC. Work-area RAM and registers only; no ROM byte is read.

    DISKCORPUS_DIR=... python3 -u scratchpad/gauntboot_probe.py
"""
import os, shutil, subprocess, sys, tempfile, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402
OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
TIMES = [2, 3, 4, 4.5, 6, 9, 12, 16, 20]


def run(machine, image):
    td = tempfile.mkdtemp(prefix="gaunt_")
    dsk = os.path.join(td, "d.dsk"); shutil.copy(image, dsk)
    out = os.path.join(td, "cap.txt")
    lines = ["set throttle off",
             f"proc __w {{s}} {{ set f [open {{{out}}} a]; puts $f $s; close $f }}",
             "debug set_bp 0xFFB1 {} { __w \"HOOK t=[format %.2f [machine_info time]] E=[reg e] A=[reg a]\" }",
             "proc __cap {tag} {",
             "  binary scan [debug read_block memory 0xFFB1 5] H* h",
             "  binary scan [debug read_block memory 0xF414 1] H* er",
             "  binary scan [debug read_block memory 0xF6B3 2] H* el",
             "  binary scan [debug read_block memory 0xF41C 2] H* cl",
             "  binary scan [debug read_block memory 0xFCC1 8] H* sl",
             "  __w \"$tag pc=[format %04X [reg pc]] hook=$h err=$er erl=$el curline=$cl exptbl_slttbl=$sl A8=[format %02X [debug read ioports 0xA8]]\"",
             "}"]
    if os.environ.get("GAUNT_TRANS"):
        # every distinct jump from RAM (>= $8000) into $0000-$7FFF between 3.5 s and 5 s:
        # PC values only (D-TAPELOAD's TRANS log shape); no ROM byte read, no game code decoded
        lines += ["set ::__last 0", "array set ::__seen {}",
                  "proc __tr {} { set p [reg pc]; if {$p < 0x8000 && $::__last >= 0x8000} {"
                  " set k [format %04X $p]; if {![info exists ::__seen($k)]} {"
                  " set ::__seen($k) 1; __w \"TRANS t=[format %.3f [machine_info time]] to=$k from=[format %04X $::__last]\" } };"
                  " set ::__last $p }",
                  "after time 3.5 { set ::__c [debug set_condition 1 __tr] }",
                  "after time 5.0 { debug remove_condition $::__c }"]
    if os.environ.get("GAUNT_ERRBP") and machine.startswith("C-BIOS"):
        # OUR ROM only: break on set_errflg and dump the stack's top words + the slot
        # register, to name the caller chain from our own .sym files
        lines.append("debug set_bp 0x" + os.environ["GAUNT_ERRBP"] + " {} {"
                     " binary scan [debug read_block memory [reg sp] 16] H* st;"
                     " __w \"ERRBP t=[format %.3f [machine_info time]] a=[reg a] sp=[format %04X [reg sp]] stack=$st A8=[format %02X [debug read ioports 0xA8]] ring=[join $::__ring ,]\" }")
        # the last 64 PCs before it (OUR code: C-BIOS repack + zerobas), from 4.70 s
        lines += ["set ::__ring {}",
                  "proc __rg {} { lappend ::__ring [format %04X [reg pc]]; if {[llength $::__ring] > 64} { set ::__ring [lrange $::__ring end-63 end] } }",
                  "after time 4.70 { set ::__rc [debug set_condition 1 __rg] }"]
    if os.environ.get("GAUNT_POKEBP") and machine.startswith("C-BIOS"):
        # OUR ROM only: do_poke's store `ld (bc),a` -- the address and the value of each POKE
        lines.append("debug set_bp 0x" + os.environ["GAUNT_POKEBP"] + " {} {"
                     " __w \"POKE t=[format %.3f [machine_info time]] addr=[format %04X [reg bc]] val=[format %02X [reg a]] A8=[format %02X [debug read ioports 0xA8]]\" }")
    for t in TIMES:
        lines.append(f"after time {t} {{ __cap T{str(t).replace('.', '_')} }}")
    lines.append(f"after time {TIMES[-1] + 0.5} {{ exit }}")
    tcl = os.path.join(td, "s.tcl"); open(tcl, "w").write("\n".join(lines) + "\n")
    p = subprocess.Popen(omsx_preflight.guarded([OMSX, "-machine", machine, "-diska", dsk,
                         "-command", "set renderer none; set sound_driver null", "-script", tcl]),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 900:
        time.sleep(0.2)
    if p.poll() is None:
        p.terminate(); p.wait()
    rows = open(out).read().splitlines() if os.path.exists(out) else ["<NO CAPTURE>"]
    shutil.rmtree(td, ignore_errors=True)
    return rows


def main():
    image = os.path.join(os.environ["DISKCORPUS_DIR"], "GAUNT.DSK")
    for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
        rows = run(m, image)
        for r in rows:
            if r.startswith(("TRANS", "ERRBP", "POKE")):
                print(f"  {side} {r}")
        rows = [r for r in rows if not r.startswith(("TRANS", "ERRBP", "POKE"))]
        hooks = [r for r in rows if r.startswith("HOOK")]
        print(f"{side}: {len(hooks)} H.ERRO call(s)")
        for r in hooks[:8]:
            print(f"  {side} {r}")
        for r in rows:
            if not r.startswith("HOOK"):
                print(f"  {side} {r}")


if __name__ == "__main__":
    main()
