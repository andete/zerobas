<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The MSX turbo R BIOS — inventory

**References:** Panasonic FS-A1GT (openMSX `turbor` links to it) and Panasonic FS-A1ST — the two turbo R models
openMSX has; Joost's ruling for the generic machines, 2026-11-23.
**Subject:** none yet. C-BIOS has no turbo R build, so for now the two references are measured against each other
([`--row turbor`](../../probes/bios/biosl_run.py): "ref" = FS-A1GT, "ours" = FS-A1ST; a diff is where the two
references disagree).
**Method:** [docs/spec-method.md](../spec-method.md) — one page per call, `docs/turbor/main/<NAME>.md`.

## What the turbo R adds

Sources for the list: the MSX Assembly Page's compiled BIOS list (`map.grauw.nl/resources/msxbios.php`; **MAP**,
rated C / scoped in [allowed-sources.md](../allowed-sources.md): names and addresses only), section "MSX turbo R BIOS
Entries". The official source, the MSX turbo R Technical Handbook (ASCII, Japanese; rated B / scoped there), has not
been read for these pages: every interface line below is MAP's, to be corroborated.

| address | name | ROM | standard | listed in | page | spec |
|---|---|---|---|---|---|---|
| $0180 | CHGCPU | main | turbo R | MAP only | [main/CHGCPU.md](main/CHGCPU.md) | DRAFT 1 |
| $0183 | GETCPU | main | turbo R | MAP only | [main/GETCPU.md](main/GETCPU.md) | DRAFT 1 |
| $0186 | PCMPLY | main | turbo R | MAP only | [main/PCMPLY.md](main/PCMPLY.md) | DRAFT 0 |
| $0189 | PCMREC | main | turbo R | MAP only | [main/PCMREC.md](main/PCMREC.md) | DRAFT 0 |

Nothing else, per the public sources read on 2026-11-23:
- **Sub-ROM:** MAP's sub-ROM list says no new sub-ROM calls came with the MSX2+ or the turbo R.
- **Work area:** MAP's system-variable list names one turbo R RAM cell, **$FFFD** (2 bytes), "temporary stack pointer
  for CHGCPU" — measured on [CHGCPU](main/CHGCPU.md). It lists two main-ROM bytes with turbo R values ($002D, the MSX
  version, 3 = turbo R; $002E bit 0, internal MSX-MIDI): ROM bytes, which the clean room does not read, so they are
  listed here and not measured.
- **Found by measurement, not listed by MAP:** $FCB1 holds the byte CHGCPU last wrote to port $A7 (the LED bits);
  see [CHGCPU](main/CHGCPU.md). MAP's list has no entry for $FCB1.

## The calls of earlier generations — pending

Nothing is inherited ([spec method](../spec-method.md) §2 item 6 and §4: "we cannot assume that e.g. msx1 bios calls
behave exactly the same on an msx2"). Every MSX1, MSX2 and MSX2+ call is to be re-measured on both turbo R references
in later units, each with its own reading:

| generation | calls | inventory | turbo R status |
|---|---|---|---|
| MSX1 main BIOS | every entry | [docs/bios/index.md](../bios/index.md) | first pass 2026-11-23: every existing probe run, [remeasured.md](remeasured.md); the NEW findings are on their pages, the SAME / AS-MSX2+ ones not yet |
| disk ROM / BDOS | every entry | [docs/bios/index.md](../bios/index.md), [docs/bdos/](../bdos/CONOUT.md) | first pass 2026-11-23 (the turbo R has MSX-DOS 2 built in): as the FS-A1WSX in every call result, [remeasured.md](remeasured.md) |
| MSX2 / MSX2+ main ROM | $015C-$017D | [docs/msx2/index.md](../msx2/index.md) | first pass 2026-11-23, [remeasured.md](remeasured.md) |
| MSX2 sub-ROM | every entry | [docs/msx2/index.md](../msx2/index.md) | first pass 2026-11-23, [remeasured.md](remeasured.md) |

**First pass (2026-11-23): [remeasured.md](remeasured.md)** — all 206 existing BIOS probes on both turbo Rs, each set
against the reading its page is based on (VG-8020 for MSX1, FS-A1WSX for MSX2 / MSX2+). 53 SAME, 74 differ from the
VG-8020 only as the MSX2+ already does (30 of them with non-behaviour bytes besides), 54 machine / timing / power-on
only, **21 NEW on the turbo R** (port $F4 / RDRES / WRRES inverted, CHKSLZ hangs on the A1GT, NEWPAD / GTPAD 0-11 and
GTPDL do nothing, the cassette entries -- TAPION / TAPIN / TAPOUT included -- are stubs that return with the carry set,
the key line at out-of-range widths, BEEP's C, a soft reset that never returns), 4 not comparable (xva13, needing a
64 KB-VRAM machine, and the 3 turbo R probes). The 3 `@tape` probes run since `biosl_run.py`'s `@tape` records "no
cassette port" instead of hanging on a machine without one. Every NEW finding was re-checked against its run file (the
MSX1 ones with the page's own rules, scratchpad/trnew_recheck.py) and is on its call's page as an "On the turbo R"
bullet or section; the SAME / AS-MSX2+ pages do not carry a turbo R column yet (remeasured.md, "Where each finding is
on its call's page").

Machine facts a later unit must keep apart from call behaviour (spec method §2 item 6): the turbo R boots in the
Z80 and finishes its boot in the R800 (measured on [CHGCPU](main/CHGCPU.md)), so a call is measured in each CPU mode a
caller can be in; its timing and any undocumented-flag result can differ by CPU.

## Harness

[`probes/bios/biosl_run.py --row turbor`](../../probes/bios/biosl_run.py) boots both models (built-in drive empty)
with the probe cartridge; at the dump it also reports the active CPU, $FCB1 and every change of the S1990's
register 6 (polled each 0.1 s of emulated time). `@cpusnap ADDR PTR` writes the active CPU and the emulated time
into the probe's capture when the CPU reaches ADDR. Both read machine state through openMSX's debugger (the S1990's
register, as for the VDP's registers), never a ROM byte.
