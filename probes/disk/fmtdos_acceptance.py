#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""fmtdos-acceptance: what D-DSKFMT shipped, seen from MSX-DOS, on the National CF-3300
and on ours.

  boot    A 720K disk as a format leaves it -- the FAT12 layout, sector 0 zero from $1E
          on, OUR boot loader (read out of this build's disk.rom by the fmt_boot /
          FMT_BOOTLEN symbols) at $1E -- plus MSXDOS.SYS and COMMAND.COM from the DOS
          disk. PASS = both machines reach COMMAND's date prompt. (The CF-3300 boots it
          with OUR loader too: the loader is the subject, not the ROM.) Knife:
          FMTBOOT_KNIFE=1 makes the loader a bare `ret`; both then fall into BASIC.
  format  MSX-DOS's own `format` on a copy of the DOS disk, through the $4025 FORMAT
          entry's dialogue: drive A, choice 1, a key. Each key is typed when the screen
          shows its prompt (polled from VRAM, screen output -- never ROM). PASS = both
          print "Format complete" and the two formatted images are byte-identical
          outside sector 0's boot code ($1E on: ours is our own loader, by design) --
          the WHOLE image, so the data sectors' fill ($40) and the zeroed span (logical
          0..13 on every choice) are compared too (D-FMTFILL). Choices 1 and 4 by
          default (1 side x 40 tracks, 2 x 80: the extremes, as dskfmt-acceptance).

Joost's 2026-11-10 ruling: the dialogue's WORDING may differ, its keys and results may
not -- so the prompts are matched on words both machines print, and the disk on bytes.

Usage: python3 probes/disk/fmtdos_acceptance.py [--dos-disk D] [--only boot|format]
                                               [--choices 1,4] [--work DIR]
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
from disk_bdos_acceptance import DEFAULT_DOS_DISK  # noqa: E402
from disk_probe_bdos import fat12_add  # noqa: E402
from disk_probe_format import read_fat_file  # noqa: E402
from omsx_session import OmsxRun, OURS_MACHINE, STOCK_MACHINE  # noqa: E402
import probe_tmp  # noqa: E402

# Tcl: the text screen as one string (name table from R2; 40 columns if R1 bit 4)
SCREEN_TCL = r"""
proc __scr {} {
  set r2 [debug read {VDP regs} 2]
  binary scan [debug read_block VRAM [expr {($r2 & 15) * 1024}] 960] a* t
  regsub -all {[^ -~]} $t { } t
  return $t
}
proc __dump {tag} {
  set r1 [debug read {VDP regs} 1]
  set r2 [debug read {VDP regs} 2]
  emit "SCREEN $tag $r1 [binary encode hex [debug read_block VRAM [expr {($r2 & 15) * 1024}] 960]]"
}
"""

# (text the screen must show, keys to type then); the last row types nothing
def format_steps(choice):
    return [("Enter new date", r"\r"), ("A>", r"format\r"), ("(A,B)", "a"),
            ("double track", str(choice)), ("trike a key", " "), ("Format complete", "")]


def steps_tcl(steps, limit):
    rows = " ".join("{" + "{" + w + "} {" + k + "}" + "}" for w, k in steps)
    return SCREEN_TCL + f"""
set ::__steps [list {rows}]
set ::__i 0
proc __poll {{}} {{
  if {{[machine_info time] > {limit}}} {{ __dump TIMEOUT; emit "STUCK $::__i"; emit "END"; exit }}
  set row [lindex $::__steps $::__i]
  if {{[string first [lindex $row 0] [__scr]] >= 0}} {{
    emit "STEP $::__i [format %.1f [machine_info time]]"
    incr ::__i
    if {{$::__i == [llength $::__steps]}} {{
      after time 1.0 {{ __dump DONE; emit "END"; exit }}
      return
    }}
    after time 0.3 [list type [subst -nocommands -novariables [lindex $row 1]]]
    after time 0.6 __poll
    return
  }}
  after time 0.25 __poll
}}
after time 1.0 __poll
"""


def show(lines):
    for ln in lines:
        if ln.startswith("SCREEN "):
            _, tag, r1, blob = ln.split(" ", 3)
            data = bytes.fromhex(blob.strip())
            cols = 40 if int(r1) & 0x10 else 32
            print(f"    --- screen at {tag} ---")
            for r in range(24):
                txt = "".join(chr(c) if 32 <= c < 127 else " " for c in data[r * cols:(r + 1) * cols]).rstrip()
                if txt:
                    print(f"    {r:2d}|{txt}")


def run(machine, disk, steps, limit):
    lines = OmsxRun(machine=machine, diska=disk).run_job_raw(
        'emit "END"; exit', settle=limit + 5, arm=steps_tcl(steps, limit), timeout=limit * 4 + 180)
    done = [ln for ln in lines if ln.startswith("STEP ")]
    return lines, len(done) == len(steps)


def row_boot(dos_disk, work):
    sym = {}
    for line in open(os.path.join(REPO, "build", "disk.sym")):
        p = line.split()
        if len(p) >= 3 and p[1] == "EQU":
            sym[p[0]] = int(p[2].rstrip("H"), 16)
    rom = open(os.path.join(REPO, "build", "disk.rom"), "rb").read()
    blob = rom[sym["fmt_boot"] - 0x4000:sym["fmt_boot"] - 0x4000 + sym["FMT_BOOTLEN"]]
    base = os.path.join(work, "fmtboot.dsk")
    import subprocess
    subprocess.run(["python3", os.path.join(REPO, "tools", "make_test_dsk.py"), "--empty", base],
                   check=True, capture_output=True)
    img = bytearray(open(base, "rb").read())
    img[0x1E:0x200] = bytes(0x200 - 0x1E)             # a format leaves the rest 0
    img[0x1E:len(blob)] = blob[0x1E:]                 # OUR loader (and its FCB name)
    img[0] = 0xEB                                     # a boot signature
    if os.environ.get("FMTBOOT_KNIFE"):
        img[0x1E] = 0xC9
        print("  KNIFE: the loader is a bare `ret`")
    src = open(dos_disk, "rb").read()
    for n8, e3 in (("MSXDOS", "SYS"), ("COMMAND", "COM")):
        data = read_fat_file(src, n8, e3)
        if data is None:
            print(f"  FAIL  boot: {n8}.{e3} is not on {dos_disk} -- NOTHING WAS MEASURED")
            return False
        fat12_add(img, n8, e3, data)
    open(base, "wb").write(img)
    print(f"  boot: our loader, {len(blob) - 0x1E} B at $1E")
    ok = True
    for m in (STOCK_MACHINE, OURS_MACHINE):
        d = os.path.join(work, f"boot_{m}.dsk")
        shutil.copyfile(base, d)
        lines, reached = run(m, d, [("Enter new date", "")], 60)
        t = [ln.split()[2] for ln in lines if ln.startswith("STEP ")]
        print(f"  {'PASS' if reached else 'FAIL'}  boot  {m:30s} date prompt "
              f"{'at t=' + t[0] if t else 'NEVER'}")
        if not reached:
            show(lines)
        ok &= reached
    return ok


def diff_runs(a, b, skip):
    runs, start = [], None
    for i in range(min(len(a), len(b)) + 1):
        same = i >= min(len(a), len(b)) or a[i] == b[i] or skip[0] <= i < skip[1]
        if not same and start is None:
            start = i
        elif same and start is not None:
            runs.append((start, i - 1))
            start = None
    return runs


def row_format(dos_disk, work, choice=1):
    imgs, ok = {}, True
    for m in (STOCK_MACHINE, OURS_MACHINE):
        d = os.path.join(work, f"format_c{choice}_{m}.dsk")
        shutil.copyfile(dos_disk, d)
        lines, reached = run(m, d, format_steps(choice), 400)
        t = [ln.split()[2] for ln in lines if ln.startswith("STEP ")]
        print(f"  {'PASS' if reached else 'FAIL'}  format c{choice} {m:27s} prompts seen {len(t)}/"
              f"{len(format_steps(choice))}{', Format complete at t=' + t[-1] if reached else ''}")
        if not reached:
            show(lines)
        ok &= reached
        imgs[m] = open(d, "rb").read()
    if ok:
        runs = diff_runs(imgs[STOCK_MACHINE], imgs[OURS_MACHINE], (0x1E, 0x200))
        print(f"  {'PASS' if not runs else 'FAIL'}  format: the two formatted images "
              f"{'are identical outside the boot code' if not runs else 'DIFFER at ' + ', '.join(f'${a:05X}-${b:05X}' for a, b in runs[:8])}")
        print(f"         sector 0 BPB (both): {imgs[OURS_MACHINE][0x0B:0x1E].hex(' ')}")
        ok &= not runs
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", default=DEFAULT_DOS_DISK)
    ap.add_argument("--only", choices=("boot", "format"))
    ap.add_argument("--choices", default="1,4", help="format choices, e.g. 1,2,3,4")
    ap.add_argument("--work", help="keep the images in this directory (default: a temp one)")
    a = ap.parse_args()
    if not os.path.isfile(a.dos_disk):
        print(f"DOS source disk not found: {a.dos_disk}", file=sys.stderr)
        return 2
    work = a.work or probe_tmp.tmp("fmtdos_acc")
    os.makedirs(work, exist_ok=True)
    res = []
    if a.only in (None, "boot"):
        res.append(row_boot(a.dos_disk, work))
    if a.only in (None, "format"):
        res += [row_format(a.dos_disk, work, int(c)) for c in a.choices.split(",")]
    print(f"===== fmtdos-acceptance: {sum(res)}/{len(res)} rows PASS =====")
    return 0 if all(res) else 1


if __name__ == "__main__":
    raise SystemExit(main())
