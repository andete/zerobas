#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CFARCH: how does the CF-3300 actually wire Disk BASIC?  Observed, not guessed.

Joost asked for a thorough investigation rather than invented implementations.
This stays on the line `disk/docs/expansion-protocol.md` §2 already drew: a
claimed hook cell holds `F7 <slot> <lo> <hi> C9`, and reading it tells us **which
SLOT hosts the handler** and **which PAGE the entry sits in**. §2 is explicit that
the target addresses are "an internal detail of the reference ROM -- zerobas does
not need or use them", so this reports the slot and the PAGE CLASS and prints the
address only as the evidence trail, never as something to call.

\U0001f534 WHAT THIS DELIBERATELY DOES NOT DO: disassemble. No instruction of the
reference is read or recorded. The question "does their handler call BASIC back"
cannot be answered this way and is NOT answered here -- it is answered
BEHAVIOURALLY by a separate probe (does `FILES` accept a string EXPRESSION?),
because a handler that evaluates an expression must reach the interpreter somehow,
whatever the mechanism.

What the census DOES settle, decisively:
  * how many hook cells the disk ROM claims, and which;
  * that every claimed handler lives in the DISK ROM's slot (or does not);
  * whether any handler sits in PAGE 0 (<$4000, always mapped) rather than
    PAGE 1 -- which is the difference between a handler that can call BASIC
    directly and one that needs an inter-slot call.
"""
import os, re, subprocess, sys, tempfile

MACHINE = "National_CF-3300"
LO, HI = 0xFD9A, 0xFFCF          # the MSX hook-table area
CALLF = 0xF7                     # RST 30h -- a claimed cell opens with it


def main() -> int:
    out = os.path.join(tempfile.gettempdir(), "cfarch.txt")
    tcl = os.path.join(tempfile.gettempdir(), "cfarch.tcl")
    with open(tcl, "w") as fh:
        fh.write(
            "after time 22 {\n"
            "  set f [open %s w]\n" % out +
            "  for {set a %d} {$a <= %d} {incr a} {\n" % (LO, HI) +
            "    if {[debug read memory $a] == %d} {\n" % CALLF +
            "      set s [debug read memory [expr {$a+1}]]\n"
            "      set l [debug read memory [expr {$a+2}]]\n"
            "      set h [debug read memory [expr {$a+3}]]\n"
            "      set t [debug read memory [expr {$a+4}]]\n"
            "      puts $f [format \"%04X %02X %04X %02X\" $a $s [expr {$h*256+$l}] $t]\n"
            "    }\n"
            "  }\n"
            "  close $f\n"
            "  exit\n"
            "}\n")
    subprocess.run(["openmsx", "-machine", MACHINE, "-command", "source %s" % tcl],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out):
        print("openMSX produced nothing -- the query failed, nothing was measured")
        return 1
    rows = [l.split() for l in open(out).read().split("\n") if l.strip()]
    print("claimed hook cells: %d" % len(rows))
    print("| cell | slot | page of entry | tail |")
    print("|---|---|---|---|")
    slots, pages = {}, {}
    for cell, slot, addr, tail in rows:
        a = int(addr, 16)
        page = "PAGE 0 (<$4000)" if a < 0x4000 else \
               "PAGE 1 ($4000-$7FFF)" if a < 0x8000 else "PAGE 2+"
        slots[slot] = slots.get(slot, 0) + 1
        pages[page] = pages.get(page, 0) + 1
        print("| $%s | $%s | %s | $%s |" % (cell, slot, page, tail))
    print()
    print("slot byte histogram :", dict(sorted(slots.items())))
    print("entry page histogram:", dict(sorted(pages.items())))
    print("tail byte should be C9 (RET) on every row; anything else is a finding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
