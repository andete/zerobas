#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKROMHOST (d), scheme D's premise on the CF-3300 (Joost 2026-11-26: "the CF-3300 is the more interesting one").

Three questions, one 16 KB test cartridge built three ways (own code, published cells only):
  (a) ORDER  -- is a cartridge in external slot 1 / slot 2 initialised BEFORE the internal disk ROM (3-1)? The
                cartridge claims 16 B from the top only while HIMEM is still $F380: the final HIMEM is $DE77 - 16 when
                it ran first, $DE77 when it ran after the disk ROM.
  (b) TOPREC -- the same top claim, but RECORDED in the cartridge's own SLTWRK entry (base address), with a 16-byte
                signature written into the claimed bytes: does the disk ROM still write over them?
  (c) BOTTOM -- the published convention (MSX2 Technical Handbook ch.5 sec.7): BOTTOM ($FC48) into the SLTWRK entry,
                BOTTOM += 64, a signature at the old BOTTOM: does it survive, and does BASIC's text start above it?
Each runs on the CF-3300 and on zerobas's DISK machine, from slot 1 and from slot 2, with a data disk, read at the
BASIC prompt. Clean room: RAM cells only (HIMEM, BOTTOM, TXTTAB, SLTWRK, the signature bytes).
"""
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402

MACHINES = (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))
DISK = os.path.join(REPO, "disk", "test720.dsk")

ASM = r"""
HIMEM   equ $FC4A
BOTTOM  equ $FC48
TXTTAB  equ $F676
SLTWRK  equ $FD09
EXPTBL  equ $FCC1
SLTTBL  equ $FCC5
RSLREG  equ $0138
MODE    equ {mode}              ; 0 order, 1 top+record, 2 bottom
        org $4000
        db "AB"
        dw init, 0, 0, 0
        ds 6, 0
init:
        call slotwrk            ; HL -> our SLTWRK entry (page 1)
        ld a, (hl)
        inc hl
        or (hl)
        dec hl
        ret nz                  ; recorded already: the page-2 mirror's second run
 if MODE EQ 2
        push hl
        ld de, (BOTTOM)
        ld (hl), e
        inc hl
        ld (hl), d              ; SLTWRK entry := old BOTTOM
        ex de, hl
        call sig                ; 16-byte signature at old BOTTOM
        ld hl, (BOTTOM)
        ld de, 64
        add hl, de
        ld (BOTTOM), hl
        pop hl
        ret
 else
        push hl
        ld hl, (HIMEM)
        ld de, $F380
        or a
        sbc hl, de
        pop hl
        ret nz                  ; HIMEM already moved: someone claimed before us -> no claim
        ld de, $F370
        ld (HIMEM), de
  if MODE EQ 1
        ld (hl), e
        inc hl
        ld (hl), d              ; SLTWRK entry := $F370 (the base)
  endif
        ld hl, $F370
        jp sig
 endif
sig:    ld b, 16                ; HL = where: $A5,$5A,... x8
        ld a, $A5
sigl:   ld (hl), a
        inc hl
        cpl
        djnz sigl
        ret
; slotwrk -- HL := SLTWRK + 32*primary + 8*secondary + 2 (page 1), from RSLREG and SLTTBL (published)
slotwrk:
        call RSLREG
        rrca
        rrca
        and 3                   ; page-1 primary
        ld c, a
        ld b, 0
        ld hl, EXPTBL
        add hl, bc
        ld a, (hl)
        and $80
        ld e, 0
        jr z, sw_ne
        ld hl, SLTTBL
        add hl, bc
        ld a, (hl)
        rrca
        rrca
        and 3
        ld e, a                 ; page-1 secondary
sw_ne:  ld a, c
        add a, a
        add a, a
        add a, e                ; 4*prim + sec
        add a, a
        add a, a
        add a, a                ; *8
        add a, 2                ; page 1
        ld l, a
        ld h, 0
        ld de, SLTWRK
        add hl, de
        ret
"""


def build(td, mode):
    src = os.path.join(td, f"c{mode}.asm")
    out = os.path.join(td, f"c{mode}.bin")
    open(src, "w").write(ASM.format(mode=mode))
    subprocess.run(["pasmo", "--bin", src, out], check=True, stdout=subprocess.DEVNULL)
    b = open(out, "rb").read()
    rom = os.path.join(td, f"c{mode}.rom")
    open(rom, "wb").write(b + b"\xFF" * (16384 - len(b)))
    return rom


def run(machine, rom, slot, td):
    out = os.path.join(td, "o.txt")
    if os.path.exists(out):
        os.unlink(out)
    dsk = os.path.join(td, "d.dsk")
    shutil.copyfile(DISK, dsk)
    tcl = os.path.join(td, "s.tcl")
    open(tcl, "w").write(f"""set throttle off
proc w {{a}} {{ return [format %04X [expr {{[debug read memory $a] + 256*[debug read memory [expr {{$a+1}}]]}}]] }}
after time 25 {{
  set f [open {{{out}}} w]
  set s ""
  set bases {{}}
  for {{set p 0}} {{$p < 4}} {{incr p}} {{ for {{set q 0}} {{$q < 4}} {{incr q}} {{
     set a [expr {{0xFD09 + 32*$p + 8*$q + 2}}]
     if {{[w $a] ne "0000"}} {{ append s "$p-$q:[w $a] "; lappend bases "0x[w $a]" }} }} }}
  puts $f "HIMEM=[w 0xFC4A] BOTTOM=[w 0xFC48] TXTTAB=[w 0xF676] SLTWRK(p1)=\\[$s\\]"
  # CLEAN ROOM: only a verdict on OUR signature leaves the emulator -- never the bytes (on the CF-3300 $F370 holds
  # its RAM-resident code; a first version dumped them, redacted from AE_claimconv.out the same day)
  foreach base [lsort -unique [concat 0xF370 $bases]] {{
    binary scan [debug read_block memory $base 16] H* v
    if {{$v eq "a55aa55aa55aa55aa55aa55aa55aa55a"}} {{ set r INTACT }} elseif {{[string range $v 0 25] eq "a55aa55aa55aa55aa55aa55aa5"}} {{ set r "INTACT but its last 3 B" }} else {{ set r "not our signature" }}
    puts $f "  sig@[format %04X $base]: $r" }}
  close $f; exit }}
""")
    cmd = ["openmsx", "-machine", machine, f"-cart{'a' if slot == 1 else 'b'}", rom, "-diska", dsk,
           "-command", "set renderer none; set sound_driver null", "-script", tcl]
    subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    return open(out).read().strip() if os.path.exists(out) else "NO READING"


def main():
    td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
    try:
        roms = {m: build(td, m) for m in (0, 1, 2)}
        for name, mode in (("ORDER", 0), ("TOPREC", 1), ("BOTTOM", 2)):
            for slot in (1, 2):
                for side, mach in MACHINES:
                    print(f"{name:6s} slot{slot} {side}: {run(mach, roms[mode], slot, td)}")
                    sys.stdout.flush()
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    main()
