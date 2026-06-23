#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box: capture the BDOS call/return REGISTER CONTRACT the MSX-DOS boot
relies on, stock vs Tier-1, in one pass (a3 §8.33 — the "batched" contract audit).

Motivation (§8.31/§8.32): the boot drives our disk ROM by CALLing the SYSTEM vector
$F37D (= our `JP bdos_entry`) to Open/SetDTA/Read MSXDOS.SYS, then MSXDOS.SYS init
consumes the registers those calls return. We have been discovering ONE wrong/missing
return register per session (e.g. bdos_rdblk leaves HL=records but not the BC byte
count MSXDOS.SYS reads, §8.32 -> the $027C derail). Rather than bump into them one at
a time, this probe captures the WHOLE return surface at once: for every $F37D call it
records the function code + entry regs + EXIT regs, on both the genuine stock and our
Tier-1, and diffs them so every divergent return register shows up together.

How it captures EXIT regs: $F37D is reached by `CALL $F37D` then a JP into the BDOS
body (JP doesn't push), so at $F37D entry the caller's return address is the word at
(SP). We read it, arm a one-shot breakpoint there, and snapshot the registers when it
fires = the BDOS call's exit state. (Boot BDOS calls are not reentrant, so one pending
return bp at a time is safe.)

Comparison: the call SEQUENCES stay aligned only while the returns match; once our
return diverges the boot may take a different path, so we compare the matching prefix
and flag the first call whose ENTRY conditions differ (everything after is
incomparable until the upstream return is fixed). The stock column is the spec: make
bdos_entry reproduce the stock's exit registers for each function.

WHAT IT MEASURES (black-box): the registers a documented call boundary ($F37D) leaves
on return — a pure input/output observation of the reference. No ROM/kernel code is
disassembled; the stock's BDOS body ($F37D -> $F331 -> resident kernel) is never read,
only its register effects.

DISK SAFETY: boots only a /tmp copy of the DOS disk.

    python3 probes/disk/disk_probe_dosboot_bdos_contract.py --dos-disk ~/Documents/msx/msx/disks/msxdos103-cmd111.dsk
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
TIER1_MACHINE = "National_CF-3300_ZEROBASDISK"
SYSTEM = 0xF37D

# MSX-DOS 1 BDOS function names (the ones the boot/init touch + a few neighbours).
FN = {0x0F: "Open", 0x10: "Close", 0x11: "SrchFirst", 0x12: "SrchNext",
      0x13: "Delete", 0x14: "SeqRead", 0x15: "SeqWrite", 0x16: "Create",
      0x1A: "SetDTA", 0x21: "RandRead", 0x22: "RandWrite",
      0x26: "WrBlk", 0x27: "RdBlk", 0x2F: "AbsRead", 0x30: "AbsWrite"}


def run(machine: str, dsk: str, settle: float, timeout: float, maxcalls: int) -> list[dict]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::log {{}}
set ::retbp -1
proc rw {{a}} {{ binary scan [debug read_block memory $a 2] s v; return [expr {{$v & 0xFFFF}}] }}
debug set_bp 0x{SYSTEM:04X} {{[llength $::log] < {maxcalls}}} {{
  set fn [expr {{[reg BC] & 0xFF}}]
  set entry [format "%02X|AF=%04X|BC=%04X|DE=%04X|HL=%04X" $fn [reg AF] [reg BC] [reg DE] [reg HL]]
  set ret [rw [reg SP]]
  set ::cur_entry $entry
  if {{$::retbp != -1}} {{ catch {{ debug remove_bp $::retbp }} }}
  set ::retbp [debug set_bp $ret {{}} {{
    lappend ::log [format "%s||AF=%04X|BC=%04X|DE=%04X|HL=%04X|IX=%04X|IY=%04X" \\
      $::cur_entry [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY]]
    catch {{ debug remove_bp $::retbp }}
    set ::retbp -1
  }}]
}}
proc cap {{}} {{
  set f [open {{{out}}} w]
  foreach e $::log {{ puts $f $e }}
  close $f
  exit
}}
after time {settle:.1f} {{ cap }}
"""
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={machine})")
    calls = []
    for line in open(out):
        line = line.strip()
        if "||" not in line:
            continue
        entry, exit = line.split("||", 1)
        ef = entry.split("|")
        xf = exit.split("|")
        d = {"fn": int(ef[0], 16),
             "in": {k.split("=")[0]: k.split("=")[1] for k in ef[1:]},
             "out": {k.split("=")[0]: k.split("=")[1] for k in xf}}
        calls.append(d)
    os.unlink(out)
    os.unlink(tcl_path)
    return calls


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--settle", type=float, default=16.0)
    ap.add_argument("--timeout", type=float, default=70.0)
    ap.add_argument("--max-calls", type=int, default=24)
    args = ap.parse_args()

    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")

    results = {}
    for tag, machine in (("stock", STOCK_MACHINE), ("tier1", TIER1_MACHINE)):
        tmp = tempfile.mktemp(suffix=".dsk")
        shutil.copyfile(args.dos_disk, tmp)
        try:
            results[tag] = run(machine, tmp, args.settle, args.timeout, args.max_calls)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    s, t = results["stock"], results["tier1"]
    print(f"stock BDOS calls: {len(s)}   tier1 BDOS calls: {len(t)}\n")

    def dump(tag, calls):
        print(f"--- {tag} $F37D calls ---")
        for i, c in enumerate(calls):
            fn = FN.get(c["fn"], f"#{c['fn']:02X}")
            ci, co = c["in"], c["out"]
            print(f" {i:2} {fn:10} in  AF={ci['AF']} BC={ci['BC']} DE={ci['DE']} HL={ci['HL']}")
            print(f"    {'':10} out AF={co['AF']} BC={co['BC']} DE={co['DE']} HL={co['HL']} IX={co['IX']} IY={co['IY']}")
        print()
    dump("stock", s)
    dump("tier1", t)

    print("seq fn          | entry (AF BC DE HL)          | EXIT  AF   BC   DE   HL   IX   IY   stock-vs-tier1")
    print("-" * 104)
    n = min(len(s), len(t))
    first_div = None
    for i in range(n):
        sc, tc = s[i], t[i]
        fn = FN.get(sc["fn"], f"#{sc['fn']:02X}")
        entry_div = (sc["in"] != tc["in"])
        # which exit registers differ
        xdiff = [k for k in ("AF", "BC", "DE", "HL", "IX", "IY")
                 if sc["out"].get(k) != tc["out"].get(k)]
        ein = sc["in"]
        print(f"{i:2}  {fn:11} | {ein['AF']} {ein['BC']} {ein['DE']} {ein['HL']} "
              f"| stk {sc['out']['AF']} {sc['out']['BC']} {sc['out']['DE']} {sc['out']['HL']} {sc['out']['IX']} {sc['out']['IY']}")
        print(f"{'':16}| {'(tier1 entry differs!)' if entry_div else '':27}"
              f"| t1  {tc['out']['AF']} {tc['out']['BC']} {tc['out']['DE']} {tc['out']['HL']} {tc['out']['IX']} {tc['out']['IY']}"
              f"   {'EXIT DIFF: '+','.join(xdiff) if xdiff else 'exit ok'}")
        if entry_div and first_div is None:
            first_div = i
            print(f"   ^^^ entry conditions diverge here — calls beyond this are not directly comparable")
            break
    print()
    if first_div is None:
        print(f"entry conditions stayed aligned for all {n} compared calls.")
    # summary of functions whose exit contract differs (within aligned prefix)
    print("\nExit-contract divergences to fix in bdos_entry (aligned prefix):")
    seen = set()
    lim = first_div if first_div is not None else n
    for i in range(lim):
        sc, tc = s[i], t[i]
        xdiff = [k for k in ("AF", "BC", "DE", "HL", "IX", "IY")
                 if sc["out"].get(k) != tc["out"].get(k)]
        fn = FN.get(sc["fn"], f"#{sc['fn']:02X}")
        if xdiff and fn not in seen:
            seen.add(fn)
            regs = ", ".join(f"{k}: stock={sc['out'][k]} ours={tc['out'][k]}" for k in xdiff)
            print(f"  {fn}: {regs}")
    if not seen:
        print("  (none in the aligned prefix)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
