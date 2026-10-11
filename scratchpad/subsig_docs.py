#!/usr/bin/env python3
"""D-SUBSIG docs + gate wiring, anchored on text; refuses otherwise."""
import re, sys

def sub(path, old, new):
    s = open(path).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

R = "docs/concepts/rom-layout.md"
s = open(R).read()
s2, n = re.subn(r"> \*\*Status \(2026-10-\d\d\):\*\*", "> **Status (2026-10-11):**", s, count=1)
assert n == 1
open(R, "w").write(s2)
sub(R, """The sub-ROM is found by its
`"CD"` signature, and its slot is written to `EXBRSA` (`&HFAF8`), the
published MSX2 cell for it.
""", """The sub-ROM is found by its own
`"ZB"` marker at `&H0000`. It carried the MSX2 SUB-ROM's `"CD"` until
2026-10-11 and wrote its slot to `EXBRSA` (`&HFAF8`); both now belong to a real
MSX2 SUB-ROM only, and `EXBRSA` reads 0, as on both MSX1 references (D-SUBSIG).
""")
sub(R, """- **There is a sub-ROM.** An MSX1 has none; the MSX2 convention (a `"CD"` ROM,
  its slot in `EXBRSA`) holds the code that did not fit. Whether an MSX1
  program can tell, for example by reading `EXBRSA`, has not been measured.
""", """- **There is a sub-ROM.** An MSX1 has none; zerobas's own sub-ROM (marker
  `"ZB"`, slot 3-2) holds the code that did not fit. A program could tell by
  reading `EXBRSA` (`&HFAF8`) until 2026-10-11: both references leave it 0 and
  zerobas wrote its sub-ROM's slot, 139. It no longer writes it
  ([`subsig_probe.out`](../../scratchpad/subsig_probe.out)).
""")
sub(R, "## What we found, and how\n\n", "## What we found, and how\n\n"
    "- **The sub-ROM wore the MSX2 SUB-ROM's identity** (changed 2026-10-11,\n"
    "  D-SUBSIG, Joost's ruling). It carried `\"CD\"` and wrote `EXBRSA`; on an\n"
    "  MSX2, C-BIOS takes the first `\"CD\"` ROM it finds as the SUB-ROM, so ours\n"
    "  would have captured `EXTROM`. Found while weighing more sub-ROM space\n"
    "  ([`subrom_arch_report.md`](../../scratchpad/subrom_arch_report.md)).\n")

P = "sub/PROVENANCE.md"
sub(P, """- **`CD` signature at $0000** — sub-ROM identification convention (cartridges use
  `AB`, sub-ROMs use `CD`). *Source:* MSX2 TH sub-ROM section. Our discovery scan
  (`init_ext_roms`, S2b) RDSLT-checks $0000/$0001 for `'C'`/`'D'`.""",
    """- **`ZB` marker at $0000** — *own design* (D-SUBSIG, Joost 2026-10-11; it was
  the MSX2 SUB-ROM's `CD` -- MSX2 TH sub-ROM section -- which belongs to a real
  MSX2 SUB-ROM; not `AB` either, a cartridge). Our discovery scan
  (`init_ext_roms`, S2b) RDSLT-checks $0000/$0001 for `'Z'`/`'B'`.""")
sub(P, """  area (*source:* MSX2 TH work-area map), written for convention-compat but not
  read at dispatch (spec D-6/R4).""", """  area (*source:* MSX2 TH work-area map); NOT written since D-SUBSIG (both MSX1
  references leave it 0), and never read at dispatch (spec D-6/R4).""")

S = "docs/spec-basic-subrom.md"
sub(S, """Status: **SIGNED OFF 2026-07-11**""", """> 🔁 **AMENDED 2026-10-11 (D-SUBSIG, Joost's ruling):** the sub-ROM's marker at
> `$0000` is zerobas's own **`ZB`**, not the MSX2 SUB-ROM's `CD`, and boot no
> longer writes `EXBRSA` (`$FAF8`; both MSX1 references leave it 0). Every `CD`
> / EXBRSA below is this spec's 2026-07 design, kept as written. Why, and the
> options for more sub-ROM space (a second ROM in slot 3-3, ruled for later):
> [`subrom_arch_report.md`](../scratchpad/subrom_arch_report.md),
> [`subrom_demand_report.md`](../scratchpad/subrom_demand_report.md).

Status: **SIGNED OFF 2026-07-11**""")

sub("probes/basic/basic_probe_subrom_boot.py", "CD/S1 marker bytes (it proves executability, not just presence).",
    "ZB/S1 marker bytes (it proves executability, not just presence).")

sub("Makefile", """casrbrk-acceptance: repack-machine
	python3 probes/basic/basic_probe_casrbrk.py
""", """casrbrk-acceptance: repack-machine
	python3 probes/basic/basic_probe_casrbrk.py

# --- subsig-acceptance: our sub ROM's own "ZB" marker; EXBRSA left 0 (D-SUBSIG) --
# PEEK(&HFAF8) after boot against both MSX1 references (0; ours wrote 139), with a
# page-0 and a page-1 tenant as the controls a scan that finds nothing would fail.
subsig-acceptance: repack-machine
	python3 probes/basic/basic_probe_subsig.py
""")
sub("tools/run_gates.py", """caswbrk-acceptance casrbrk-acceptance\"\"\".split()""",
    """caswbrk-acceptance casrbrk-acceptance subsig-acceptance\"\"\".split()""")
