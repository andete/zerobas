#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LATCH2 (docs/spec-probe-latch2.md) -- the injector's two standing rules.

Pure host Python: no emulator, no ROM. `make latch-check` proves both rules on
the machine, but it needs openMSX and a built repack machine; these rows need
neither and cannot go silent. They pin the two invariants that two slices' worth
of measurement bought:

  D-LATCH   the injector writes AT the current GETPNT and NEVER MOVES IT.
            Moving it backwards is invisible to a CPU that latched it into HL
            one instruction earlier ($1197), and the head of the line is lost.
            🔴 That fix shipped in D-LATCH with NO host-level pin at all.

  D-LATCH2  the injector does not write into a buffer the machine is still
            CONSUMING. Inside `chget_char` ($11A3-$11AD) the CPU is holding an
            HL it is about to store into GETPNT, which overwrites the injection
            and swallows exactly one byte. GETPNT != PUTPNT is the necessary
            AND sufficient precondition, so the guard reads both and defers.

R4 is the knife aimed at this file: R1's detector must be able to SEE a GETPNT
write, or R1 passes for every possible injector body and pins nothing
([[coverage-gate-cannot-see-a-gutted-guard]]).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl  # noqa: E402
import latch_check  # noqa: E402

# The measured worst case the bound must cover: 40 circular bytes hold at most
# 39 (MAX_DIRECT + CR), and a pending line of exactly that length drained in 10
# retries / 20 ms (docs/latch2-window-characterization.md §5). The worst case is
# a property of the BUFFER, not of usage, so this number is not a sample.
WORST_DRAIN_S = 0.020

fails = []


def check(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r}, want {want!r}")
    print(f"  {'PASS' if got == want else 'FAIL'}  {label:<52} {got!r}")


def writes(body: str, addr: int) -> bool:
    """True if this Tcl body has a `debug write memory` aimed at `addr`. The
    address is a decimal literal in the generated Tcl."""
    return bool(re.search(rf"debug write memory\s+{addr}\b", body))


key = omsx_repl.key_proc()

print("R1  D-LATCH: the shipped injector never MOVES GETPNT")
check("writes the payload relative to GETPNT (reads it)",
      bool(re.search(rf"debug read memory {omsx_repl.GETPNT}\b", key)), True)
check("never writes GETPNT", writes(key, omsx_repl.GETPNT), False)
check("never writes GETPNT+1", writes(key, omsx_repl.GETPNT + 1), False)
check("does write PUTPNT (the payload end still moves)",
      writes(key, omsx_repl.PUTPNT), True)

print("R2  D-LATCH2: the drain guard is present and BOUNDED")
check("reads PUTPNT (the precondition, not just the write target)",
      bool(re.search(rf"debug read memory {omsx_repl.PUTPNT}\b", key)), True)
check("compares the two pointers", "if {$g != $q}" in key, True)
check("defers by re-scheduling itself", "after time" in key
      and "__key $s" in key, True)
check("the retry is bounded", f"$tries < {omsx_repl.KEY_DEFER_MAX}" in key,
      True)
check("counts BOTH paths so a gate can prove it fired",
      ("incr ::__zbdefer" in key) and ("incr ::__zbforced" in key), True)

print("R3  the bound sits inside both contracts it has to satisfy")
bound = omsx_repl.KEY_DEFER_STEP * omsx_repl.KEY_DEFER_MAX
check(f"bound {bound * 1000:.0f} ms covers the {WORST_DRAIN_S * 1000:.0f} ms "
      "worst-case drain", bound >= WORST_DRAIN_S, True)
# ECHO_GAP is when the echo guard dumps the screen to judge the line. A
# deferral anywhere near it would make that guard judge a line that had not
# landed yet -- the guard would then be measuring the harness, not the machine.
check(f"bound stays under a quarter of ECHO_GAP ({omsx_repl.ECHO_GAP}s)",
      bound <= omsx_repl.ECHO_GAP / 4, True)
# The 39-byte limit is what makes the worst case a CONSTANT rather than a
# sample, so it is pinned here too: raise the buffer and this bound is a guess.
check("the 39-byte payload limit that bounds the worst case still holds",
      omsx_repl.MAX_DIRECT + 1, 39)

print("R4  KNIFE on this file: the detector can SEE a GETPNT write")
# latch_check.OLD_KEY is the frozen pre-D-LATCH body -- it DOES move GETPNT.
# Without this row, R1 would pass just as happily against a regex that matches
# nothing at all.
check("OLD_KEY (frozen pre-D-LATCH fault) writes GETPNT",
      writes(latch_check.OLD_KEY, omsx_repl.GETPNT), True)
# and GETPNT_KEY (frozen pre-D-LATCH2) passes R1 but must FAIL R2 -- the two
# rules are independent, and the era between them satisfied exactly one.
check("GETPNT_KEY (frozen pre-D-LATCH2) satisfies R1",
      writes(latch_check.GETPNT_KEY, omsx_repl.GETPNT), False)
check("GETPNT_KEY has NO drain guard (R2 is a separate rule)",
      bool(re.search(rf"debug read memory {omsx_repl.PUTPNT}\b",
                     latch_check.GETPNT_KEY)), False)

print()
if fails:
    print(f"{len(fails)} FAILED:")
    for f in fails:
        print(f"  {f}")
    sys.exit(1)
print("test_key_drain_guard: all rows passed")
