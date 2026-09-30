#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CHANHOOK round 2 -- which of the cells the channel verbs enter are CLAIMED?

An entered cell is not a crossing (§6.6v: `$FE67` is entered and is a bare RET).
A claimed slot's FIRST byte is `F7` (RST 30h, the inter-slot call idiom); an
unclaimed one is `C9`. This reads ONLY that first byte of each published slot
($FD9A..$FFE7, 5 bytes apart), after boot at the BASIC prompt -- never the slot or
target address that follows it, never anything the cell points at
(expansion-protocol.md §2 permits the slot and the idiom; this takes less).
Both machines: the CF-3300 (the reference with its disk ROM) and zerobas's DISK
build, so the table says which of the reference's crossings we already offer.
"""
import os, shutil, signal, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                                              # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
LO, HI, STEP = 0xFD9A, 0xFFE7, 5
# the cells D-CHANHOOK round 1 saw a channel verb enter (scratchpad/chanhook_run.out)
WATCH = [0xFE4E, 0xFE53, 0xFE58, 0xFE5D, 0xFE62, 0xFE85, 0xFE8A, 0xFE8F, 0xFE94,
         0xFE9E, 0xFEA3, 0xFEB2, 0xFEB7, 0xFEDF, 0xFEE4, 0xFEE9, 0xFF75, 0xFF7A,
         0xFFCF, 0xFFD4]


def first_bytes(machine, cap=25.0, timeout=120.0):
    tmp = tempfile.mkdtemp(prefix="hookclaim_")
    dk = os.path.join(tmp, "d.dsk")
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dk)
    out = os.path.join(tmp, "o.txt")
    cells = " ".join(str(a) for a in range(LO, HI + 1, STEP))
    tcl = (f"set throttle off\nset renderer none\nset sound_driver null\n"
           f"proc cap {{}} {{ set f [open {{{out}}} w]; "
           f"foreach a {{{cells}}} {{ puts $f \"$a [debug read memory $a]\" }}; "
           f"close $f; exit }}\n"
           f"after time {cap} {{ cap }}\n")
    tp = os.path.join(tmp, "s.tcl")
    open(tp, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dk, "-script", tp]
    p = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    dl = time.time() + timeout
    while p.poll() is None and time.time() < dl:
        time.sleep(0.1)
    if p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)   # our own child only
    if not os.path.exists(out):
        return None
    return {int(a): int(v) for a, v in (ln.split() for ln in open(out))}


def main():
    ref = first_bytes("National_CF-3300")
    zb = first_bytes("C-BIOS_MSX1_EU_REPACK_DISK")
    if not ref or not zb:
        print("INSTRUMENT FAULT: no dump")
        return 2
    def kind(b):
        return "CLAIMED" if b == 0xF7 else ("ret" if b == 0xC9 else f"?{b:02X}")
    print(f"claimed slots: CF-3300 {sum(1 for b in ref.values() if b == 0xF7)}, "
          f"zerobas {sum(1 for b in zb.values() if b == 0xF7)} of {len(ref)}")
    print(f"\n{'cell':6} {'CF-3300':>8} {'zerobas':>8}")
    for c in WATCH:
        print(f"${c:04X}  {kind(ref[c]):>8} {kind(zb[c]):>8}")
    print("\nclaimed on the CF-3300 and NOT here:",
          " ".join(f"${c:04X}" for c in sorted(ref) if ref[c] == 0xF7 and zb.get(c) != 0xF7))
    print("claimed here and NOT on the CF-3300:",
          " ".join(f"${c:04X}" for c in sorted(zb) if zb[c] == 0xF7 and ref.get(c) != 0xF7))
    return 0


if __name__ == "__main__":
    sys.exit(main())
