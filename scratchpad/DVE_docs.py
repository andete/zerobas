#!/usr/bin/env python3
"""D-DISKVE (2026-11-17): gate BDOSXE, drop its PENDING reach pin, close the TODO item."""
import sys


def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)}: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))


G = "probes/disk/disk_bdos_acceptance.py"
edit(G, '''    # (BDOSXE, D-DISKCONTRACT gap 2: NOT gated yet -- it DIVERGES, TODO D-DISKVE: our BDOS
    #  never calls a program's DISKVE handler. Run it with `--only BDOSXE` after adding it
    #  back here once D-DISKVE lands.)
''', '''    # BDOSXE (D-DISKCONTRACT gap 2, D-DISKVE, 2026-11-17): a disk ERROR through the BDOS --
    # FMAKE / WRABS on a write-protected disk, RDABS past the last cylinder -- with the
    # program's own DISKVE handler answering Ignore: the handler's entry registers per call
    # and each BDOS return. (Retry / Abort measured by hand: scratchpad/DVE_retry.out,
    # DVE_abort_ours.out.)
    ("BDOSXE", "build_bdosxe_disk.py"),
''')
edit(G, '''    "BDOSX8": {
        # Item 5''', '''    "BDOSXE": {
        # D-DSKIOCYL (TODO, TIER 6): RDABS of sector 1440, past the 720 KB disk's last
        # cylinder -- DSKIO's code is 8 (record not found) here, 2 (not ready) on the
        # CF-3300. OURS is pinned, so the excuse cannot hide a regression
        # (scratchpad/DVE_run2.out).
        0x0250: (0x08, "regs rec2 RDABS C -- the code the handler was given (D-DSKIOCYL)"),
        0x0267: (0x08, "hrec slot 2 C -- the handler's C on that read (D-DSKIOCYL)"),
    },
    "BDOSX8": {
        # Item 5''')

R = "tools/probe-reach-allow.txt"
s = open(R).read()
line = [l for l in s.splitlines(True) if l.startswith("build_bdosxe_disk ")]
if len(line) != 1:
    sys.exit("reach pin")
open(R, "w").write(s.replace(line[0], ""))

A = "probes/disk/bdosxe.asm"
edit(A, '''                ; D-DISKVE (2026-11-17): an Abort answer -- where does the BDOS go? $F325's
                ; value before, then $F325 -> our landing cell (abcell holds abland; abcell's
                ; own bytes, run as code, are `nop / dec b` into abland -- direct or indirect)''',
     '''                ; D-DISKVE (2026-11-17): an Abort answer -- where does the BDOS go? $F325's
                ; value before, then $F325 -> our landing cell (abcell holds abland; abcell's
                ; own bytes, run as code, are `nop / dec b` into abland -- direct or indirect).
                ; MEASURED: the CF-3300 never lands there -- Abort is a warm boot to
                ; COMMAND.COM's prompt (scratchpad/XE4_stock.out, XE4_scr_stock.out).''')

T = "TODO.md"
edit(T, '''      ➡️ NEXT: D-DISKVE into the hole (~55 B); then D-DOSDRVB, D-CONCOL, D-DSKIOCYL (more of the reserve).''',
     '''      ➡️ NEXT: ~~D-DISKVE into the hole~~ ✅ LANDED 2026-11-17 (74 of the 76 B); then D-DOSDRVB, D-CONCOL,
      D-DSKIOCYL -- the plan's reserve (skip_sp, fmt_err) first.''')
edit(T, '''- [ ] 🎯 **D-DISKVE — OUR BDOS NEVER CALLS THE DISK-ERROR HANDLER (DISKVE, $F323): A DOS PROGRAM'S DISK ERROR IS SILENT**''',
     '''- [x] 🎯 **D-DISKVE — OUR BDOS NEVER CALLS THE DISK-ERROR HANDLER (DISKVE, $F323): A DOS PROGRAM'S DISK ERROR IS SILENT**
      ✅ **LANDED 2026-11-17.** `bdos_dskio` (disk/kernel.asm, in D-DISKCARVE6's hole: 2 B left) wraps dskio for
      write_sector, dskio_calslt and RDABS / WRABS (one body now, disk/fat.asm). On an error with a handler
      installed it enters the handler as the CF-3300 does -- A = the drive, B = 1, C = the code | the write bit,
      DE = the DISKVE cell + 1, HL = the handler -- and acts on C: 1 Retry, 2 Abort (`jp 0`: the warm boot,
      measured -- the CF-3300 lands at COMMAND.COM's prompt, never through $F325: [`XE4_scr_stock.out`](scratchpad/XE4_scr_stock.out)),
      0 Ignore (FMAKE carries on; RDABS / WRABS return A = $FF, B = 1, C = the code given, DE = the sector,
      HL = $01FF). The KEY is DISKVE's high byte: MSX-DOS leaves $D609 there on both machines
      ([`XE3_stock.out`](scratchpad/XE3_stock.out), [`XE3_ours.out`](scratchpad/XE3_ours.out)), and our init now zeroes it under BASIC (it held $C9C9), so
      BASIC's own disk errors are unchanged. BDOSXE is GATED (bdos-acceptance): Ignore
      [`DVE_run2.out`](scratchpad/DVE_run2.out), Retry [`DVE_retry.out`](scratchpad/DVE_retry.out), Abort's screen [`DVE_abort_ours.out`](scratchpad/DVE_abort_ours.out) -- byte-identical but
      for the two RDABS-1440 bytes that are D-DSKIOCYL's (pinned in the gate's allowlist). 🔮 2 B left: HIT;
      🔮 "Abort lands at $F325's target": MISS (a warm boot). WRABS's success F is now $42 as RDABS's (one
      body). ⚠️ Residual: a DOS boot sector's step-5 code (HL = $F323) could leave a page-3 pointer there
      if that disk then falls back to BASIC -- unmeasured, not filed until a disk does it.''')
edit(T, '''      stays in its allotted space). Pinned in phydioerr-acceptance (rows read_far / read_1440 / read_1500). (1) FORMAT''',
     '''      stays in its allotted space). Pinned in phydioerr-acceptance (rows read_far / read_1440 / read_1500), and since
      D-DISKVE in bdos-acceptance's BDOSXE allowlist (RDABS 1440's C, ours 8). (1) FORMAT''')
print("ok")
