#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The main BIOS calls' CONTRACT LEVEL (Joost 2026-11-14: "yes add the level column").

docs/tier-status.md's "exercised" only says a gate NAMES an entry; five of the seven
contract gaps closed on 2026-11-14 were real differences on rows that read "exercised, vs
reference: yes". The level says how much of the answer is COMPARED with the VG-8020:

  L1  called         a gate calls it (the mechanical witness; the default)
  L2  happy path     its main result -- registers, VRAM, work area, port -- is compared
  L3  full contract  every published output, flags and non-idle states included
  L4  errors / edges the abort paths too (STOP, no device, bad input)
  L5  speed          on par -- NOT SCORED under the BIOS-only focus (Joost 2026-11-14)

An entry's level is the highest one whose lower levels all hold. Each claim names the gate
that proves it and what still keeps it from the next level (the source:
scratchpad/bios_contract_inventory.md, the D-BIOSCONTRACT2 gaps closed since). 🔴 A claim
is CHECKED against entry_table's mechanical witnesses: its gate must be one of the gates
that name the entry, or check() refuses -- a claim cannot outlive its gate. It cannot check
that the gate COMPARES what the claim says; that is the claim's own prose.

    python3 tools/bios_levels.py      -- the claims against the witnesses, refusals first
"""
import sys

# addr -> (level, gate proving it, note: what keeps it from the next level, or how an L3 / L4
# was earned; "" when nothing needs saying)
LEVELS = {
    0x0000: (1, None, "its witnesses are spurious ($0000 constants); its contract is the boot "
                      "state every gate inherits"),
    0x0008: (4, "synchr-acceptance", "the Syntax error path compared"),
    0x000C: (3, "slotregs-acceptance", ""),
    0x0010: (3, "biosflags-acceptance", ""),
    0x0014: (3, "slotregs-acceptance", ""),
    0x0018: (3, "outdlp-acceptance", "PTRFIL against PRTFLG precedence not separated"),
    0x001C: (2, "p1vec-acceptance", "IX / IY / AF' on return"),
    0x0020: (3, "biosflags-acceptance", ""),
    0x0024: (3, "slotregs-acceptance", ""),
    0x0028: (3, "biosflags-acceptance", ""),
    0x0030: (2, "p1vec-acceptance", "IX / IY / AF' on return"),
    0x003B: (3, "initio-acceptance", "exit registers diffed since D-GICINIQ"),
    0x003E: (3, "biosregs-acceptance", ""),
    0x0041: (3, "biosvdp-acceptance", ""),
    0x0044: (3, "biosvdp-acceptance", ""),
    0x0047: (3, "biosvdp-acceptance", ""),
    0x004A: (3, "biosregs-acceptance", ""),
    0x004D: (3, "biosvram-acceptance", ""),
    0x0050: (3, "biosvram-acceptance", ""),
    0x0053: (3, "biosvram-acceptance", ""),
    0x0056: (3, "biosvram-acceptance", ""),
    0x0059: (3, "biosvram-acceptance", ""),
    0x005C: (3, "biosvram-acceptance", ""),
    0x005F: (3, "biosvdp-acceptance", ""),
    0x0062: (3, "biosvdp-acceptance", ""),
    0x0069: (3, "biosvram-acceptance", ""),
    0x006C: (2, "biosmode-acceptance", "the cleared VRAM"),
    0x006F: (2, "biosmode-acceptance", "the cleared VRAM"),
    0x0072: (2, "biosmode-acceptance", "the cleared VRAM"),
    0x0075: (2, "biosmode-acceptance", "the cleared VRAM"),
    0x0078: (3, "biosvdp-acceptance", ""),
    0x007B: (3, "biosvdp-acceptance", ""),
    0x007E: (3, "biosvdp-acceptance", ""),
    0x0081: (3, "biosvdp-acceptance", ""),
    0x0084: (3, "biosregs-acceptance", ""),
    0x0087: (3, "biosregs-acceptance", ""),
    0x008A: (3, "biosflags-acceptance", ""),
    0x008D: (2, "biosregs-acceptance", "the glyph drawn"),
    0x0090: (3, "biosq-acceptance", "queues / MUSICF / PLYCNT compared; the voice blocks' BYTES are zerobas PLAY's own encoding (filed, BASIC-side)"),
    0x0093: (3, "biosregs-acceptance", ""),
    0x0096: (3, "biosregs-acceptance", ""),
    0x0099: (3, "strtms-acceptance", ""),
    0x009C: (2, "biosflags-acceptance", "Z with a key waiting"),
    0x009F: (3, "biosregs-acceptance", ""),
    0x00A2: (3, "biostext-acceptance", ""),
    0x00A5: (4, "outdlp-acceptance", "the no-printer CTRL-STOP abort compared"),
    0x00A8: (3, "biosflags-acceptance", "ready state: outdlp's lptstt_rdy (DATA bytes, which "
                                        "the name scan cannot see)"),
    0x00AB: (3, "biosflags-acceptance", ""),
    0x00AE: (2, "biosregs-acceptance", "HL not diffed (an `:END` row); the STOP exit IS "
                                       "compared (outdlp's pinlin_stop, DATA bytes)"),
    0x00B1: (2, "biosregs-acceptance", "HL not diffed (an `:END` row); the STOP exit IS "
                                       "compared (outdlp's inlin_stop, DATA bytes)"),
    0x00B4: (2, "biosregs-acceptance", "HL and the `? ` prompt not diffed; the STOP exit IS "
                                       "compared (outdlp's qinlin_stop, DATA bytes)"),
    0x00B7: (3, "biosflags-acceptance", "STOP held: outdlp's breakx_loop (DATA bytes)"),
    0x00BA: (3, "iscntc-acceptance", ""),
    0x00BD: (3, "iscntc-acceptance", ""),
    0x00C0: (3, "beep-acceptance", ""),
    0x00C3: (2, "biostext-acceptance", "the graphics modes"),
    0x00C6: (3, "biostext-acceptance", ""),
    0x00C9: (3, "biosregs-acceptance", ""),
    0x00CC: (3, "biostext-acceptance", ""),
    0x00CF: (3, "biostext-acceptance", ""),
    0x00D2: (3, "biosvdp-acceptance", ""),
    0x00D5: (3, "biosq-acceptance", "ports 0 (keys held), 1 / 2 (the PSG latch) compared"),
    0x00D8: (3, "biosq-acceptance", "triggers 0 (SPACE held), 1..4 (the PSG latch) compared"),
    0x00DB: (3, "biosq-acceptance", "arkanoidpad in port A / B, PAD 0..7"),
    0x00DE: (3, "biosq-acceptance", "paddle in port A / B, PDL 1..6"),
    0x00E1: (3, "tapebios-acceptance", ""),
    0x00E4: (3, "tapebios-acceptance", ""),
    0x00E7: (3, "tapebios-acceptance", ""),
    0x00EA: (3, "tapebios-acceptance", ""),
    0x00ED: (3, "tapebios-acceptance", ""),
    0x00F0: (3, "tapebios-acceptance", ""),
    0x00F3: (3, "biosregs-acceptance", ""),
    0x00F6: (3, "biosq-acceptance", "a non-empty queue, two queues apart"),
    0x00F9: (3, "biosq-acceptance", "filled until Z: 127 bytes"),
    0x00FC: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x00FF: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x0102: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x0105: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x0108: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x010B: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x010E: (3, "biosflags-acceptance", ""),
    0x0111: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x0114: (3, "biosregs-acceptance", ""),
    0x0117: (3, "biosregs-acceptance", ""),
    0x011A: (3, "biosflags-acceptance", ""),
    0x011D: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x0120: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x0123: (2, "biosregs-acceptance", "SCREEN 3 (gap 10)"),
    0x0126: (3, "biosregs-acceptance", ""),
    0x0129: (3, "paintbios-acceptance", ""),
    0x012C: (3, "paintbios-acceptance", ""),
    0x012F: (3, "paintbios-acceptance", ""),
    0x0132: (3, "biosregs-acceptance", ""),
    0x0135: (3, "biosregs-acceptance", ""),
    0x0138: (3, "biosregs-acceptance", ""),
    0x013B: (3, "slotregs-acceptance", ""),
    0x013E: (3, "biosregs-acceptance", ""),
    0x0141: (3, "tapebios-acceptance", ""),
    0x0144: (3, "diskbasic-acceptance", ""),
    0x0147: (1, None, "its witnesses are spurious (the word FORMAT); the body is the disk "
                      "ROM's -- only the main-BIOS side is in focus"),
    0x014A: (3, "biosflags-acceptance", ""),
    0x014D: (4, "outdlp-acceptance", "the Device I/O error abort compared"),
    0x0150: (3, "biosq-acceptance", "voices 1 and 2"),
    0x0153: (3, "biosq-acceptance", "voice 2, offset 5"),
    0x0156: (3, "biostext-acceptance", ""),
    0x0159: (3, "biosregs-acceptance", ""),
}
NAMES = {1: "L1 called", 2: "L2 happy path", 3: "L3 full contract", 4: "L4 errors / edges"}


def level_of(row):
    """(label, note, refusal or None) for one entry_table.bios_rows() row."""
    if row["stub"]:
        return "L0 stub", "", None
    if not row["gates"]:
        return "—", "", None                            # ruled / NOT MEASURED: no claim
    claim = LEVELS.get(row["addr"])
    if claim is None:
        return NAMES[1], "no claim recorded", None
    lvl, gate, note = claim
    if gate is not None and gate not in row["gates"]:
        return (NAMES[1], note,
                f"{row['name']}: the L{lvl} claim names {gate}, which no longer witnesses it")
    return NAMES[lvl], note, None


def check(rows):
    """Every refusal (a claim whose gate does not witness its entry, or a claim for an entry
    the table does not have)."""
    bad = [r for r in (level_of(x)[2] for x in rows) if r]
    known = {x["addr"] for x in rows}
    bad += [f"${a:04X}: a level claim for an entry not in the BIOS table" for a in LEVELS
            if a not in known]
    return bad


def main():
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    import entry_table
    rows = entry_table.bios_rows(stubs={})
    bad = check(rows)
    for b in bad:
        print("REFUSED:", b)
    tally = {}
    for r in rows:
        tally[level_of(r)[0]] = tally.get(level_of(r)[0], 0) + 1
    print("  ".join(f"{k}: {v}" for k, v in sorted(tally.items())))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
