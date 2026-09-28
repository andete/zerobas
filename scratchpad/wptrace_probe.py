"""D-WPROTECT: does OUR driver ever see the write-protect bit? (zerobas only)

scratchpad/errkeep2_probe.py (errkeep2_run3.out): SAVE / SAVE ,A / BSAVE / OPEN FOR
OUTPUT on a write-protected image raise 68 on the CF-3300 and answer OK on zerobas.
disk/driver.asm's fdc_write_data reads the WD2793 status after the transfer and
maps bit 6 (ST_WP) to DSKIO code 0 -> 68, so either that read never sees the bit
or the write never reaches it. This breaks on OUR OWN disk.rom (addresses from
build/disk.sym) and logs, with the primary-slot register so a hit can be told
from another ROM's code at the same page-1 address:
  W  fdc_write_phys entered      (a write reached the drive)
  S  just after fdc_wr_status's `ld a,(FDC_STATUS)` -- A = the status byte
Nothing of the reference's is read.

    python3 -u scratchpad/wptrace_probe.py [--rw]     (--rw: a WRITABLE control)
"""
import os, re, stat, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
CHAIN = ["hk_dpsave", "fatprim_write_sector", "dc_result", "dc_fail", "dc_map",
         "sv_load_error", "hk_claim_status"]
# round 3 (--open): the same SAVE with HI.TXT open FOR INPUT -- after D-WPROTECT's
# driver fix the bare SAVE raises 68 and this one still answers OK
PROG_OPEN = ["NEW", "10 ON ERROR GOTO 90", '20 OPEN "HI.TXT" FOR INPUT AS #1',
             '30 SAVE "X.BAS"', '40 PRINT"[OK]":END', '90 PRINT"[";ERR;ERL;"]":END', "RUN"]
PROG = ["NEW", "10 ON ERROR GOTO 90", '30 SAVE "X.BAS"', '40 PRINT"[OK]":END',
        '90 PRINT"[";ERR;ERL;"]":END', "RUN"]


def sym(name):
    for l in open(os.path.join(REPO, "build", "disk.sym")):
        p = l.split()
        if len(p) >= 3 and p[0] == name:
            return int(p[2].rstrip("Hh"), 16)
    raise SystemExit(f"no {name} in build/disk.sym")


def main():
    img = t._disk_image()
    if "--rw" not in sys.argv:
        os.chmod(img, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    log = tempfile.mkstemp(suffix=".log")[1]
    w, s = sym("fdc_write_phys"), sym("fdc_wr_status") + 3
    tcl = (f'set ::wl [open "{log}" w]\n'
           f'debug set_bp 0x{w:04X} {{}} {{ puts $::wl "W [format %02X '
           '[debug read ioports 0xA8]]"; flush $::wl }\n'
           f'debug set_bp 0x{s:04X} {{}} {{ puts $::wl "S [format %02X [reg a]] '
           '[format %02X [debug read ioports 0xA8]]"; flush $::wl }\n')
    # round 2: the driver DOES see ST_WP (every write, round 1) and SAVE still
    # reads OK -- so follow the failure UP: which of these run, and with what CF?
    for lab in CHAIN:
        a = sym(lab)
        tcl += (f'debug set_bp 0x{a:04X} {{}} {{ puts $::wl "B {lab} '
                '[format %02X [reg f]] [format %02X [reg a]] '
                '[format %02X [debug read ioports 0xA8]]"; flush $::wl }\n')
    tcl += ('debug set_watchpoint write_mem 0xE098 {} { puts $::wl "E [format %04X '
            '[reg pc]] $::wp_last_value [format %02X [debug read ioports 0xA8]]"; '
            'flush $::wl }\n')
    prog = PROG_OPEN if "--open" in sys.argv else PROG
    raw = omsx_repl.run_cases(ZB, [("direct", prog)], batch=False, reset=("CLS",),
                              boot=8.0, capture="screen", diska=img, step=8.0,
                              cap_gap=20.0, prologue=(tcl,))[0] or ""
    r = re.findall(r"\[[^\]\"]*\]", raw)
    print("image:", "WRITABLE (control)" if "--rw" in sys.argv else "read-only")
    print("reading:", " ".join(r[-1].split()) if r else "NO READING")
    lines = [l.split() for l in open(log) if l.strip()]
    print(f"{sum(1 for l in lines if l[0] == 'W')} write(s) reached fdc_write_phys")
    for l in lines:
        if l[0] == "B":
            print(f"  bp {l[1]:22} F={l[2]} A={l[3]} A8={l[4]}")
        elif l[0] == "E":
            print(f"    DISKOP_ERR <- {l[2]:>3}  pc={l[1]}  A8={l[3]}")
    for l in lines:
        if l[0] == "S":
            print(f"  status after a write: {l[1]}  (ST_WP $40 {'SET' if int(l[1], 16) & 0x40 else 'clear'})  A8={l[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
