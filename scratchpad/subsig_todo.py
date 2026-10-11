#!/usr/bin/env python3
"""D-SUBSIG: the TODO entries -- the closed slice and Joost's two forward rulings."""
import sys
p = "TODO.md"
s = open(p).read()
anchor = """- [ ] 🎚️ **~~TIER 5~~ TIER 4 (SWAPPED 2026-09-24) IS NOW "MATCHES THE REFERENCE'S
      RAM USAGE" """
if s.count(anchor) != 1:
    sys.exit("REFUSE anchor")
new = """- [x] ✅ **D-SUBSIG — THE SUB ROM WORE THE MSX2 SUB-ROM'S IDENTITY: `CD` AT $0000, ITS
      SLOT WRITTEN TO EXBRSA ($FAF8). NOW ITS OWN `ZB`, AND $FAF8 STAYS 0 (2026-10-11)**
      🎚️ TIER 4 — RAM usage, goal (b) same addresses: `PEEK(&HFAF8)` after boot
      is 0 on the VG-8020 and the CF-3300 and was 139 here.
      🏗️ **RULED BY JOOST, 2026-10-11:** *"Our msx1 sub rom is our invention and
      should probably have it's own ID separate from the CD"*; marker chosen:
      **`ZB`** (asked: ZB / ZS / a 4-byte tag). Found while weighing more sub-ROM
      space with two read-only analyses
      ([`subrom_arch_report.md`](scratchpad/subrom_arch_report.md),
      [`subrom_demand_report.md`](scratchpad/subrom_demand_report.md)): C-BIOS
      MSX1 never scans for `CD`, but C-BIOS MSX2 takes the FIRST `CD` in any
      subslot as the SUB-ROM -- ours in a lower subslot would have captured
      EXBRSA and broken EXTROM. Nothing in the tree read EXBRSA.
      📏 [`subsig_probe.out`](scratchpad/subsig_probe.out): $FAF8/$FAF9 = 0 0 on
      both references, 139 0 on both zerobas builds (predicted: HIT).
      🔧 `db "ZB"` (sub/sub.asm), the boot scan compares 'Z'/'B' and no longer
      writes EXBRSA (basic/subrom-boot.asm, main page 1 +3 B), the wall
      checker's anchor (tools/check_sub_walls.py), docs (spec amendment,
      concepts/rom-layout, sub/PROVENANCE).
      Gate **`subsig-acceptance`** ([`basic_probe_subsig.py`](probes/basic/basic_probe_subsig.py),
      [`subsig_gate.out`](scratchpad/subsig_gate.out)): faf8, p1 (a page-1
      tenant), p0 (the page-0 array engine) against both references, 6/6. 🔪
      [`subsig_knives.out`](scratchpad/subsig_knives.out): K-SG2 (the EXBRSA
      write back) → faf8 on both; K-SG1 (the scan looks for 'C') → EVERY row --
      predicted p1 p0 only, MISSED ([run 1](scratchpad/subsig_knives_run1.out)):
      with no sub ROM nothing typed runs at all, the tokeniser being a tenant.

- [ ] 🏗️ **D-SUB2 — A SECOND PLAIN 32 KB SUB ROM IN SLOT 3-3, WHEN THE FIRST
      SUB-BLOCKED ITEM REACHES THE QUEUE (ruled 2026-10-11)**
      🎚️ BUDGET — supply: it unblocks the items the SUB walls hold, not main's.
      🏗️ **RULED BY JOOST, 2026-10-11** (asked with the two analyses above):
      *"Stage 1 now, plain 3-3 later"* -- a second plain sub ROM in the empty
      secondary slot 3-3 (same CALSLT mechanism, own marker, zero per-call
      cost, +16 KB on both islands), built when the first item the sub walls
      block comes up: SCREEN 3 (sub page 0), PAINT's span-stack re-architect,
      FCBSHAPE S1-S3, Phase C's main→sub move. The 8 KB-bank mapper (a fixed
      $4000 window + a swapped $6000 one) stays a LATER stage, only if 3-3's
      page 1 fills too. Do not re-ask.
      ⚠️ The demand analysis: MAIN is the binding wall (39 B on 2026-10-11) and
      more sub space converts to little main space (page-0 eviction is closed:
      anything that prints or raises needs the BIOS; page-1 candidates are hot).
      Carving main stays its own work.
      🤖 **AUTONOMOUS** once triggered. Staged plan
      ([`subrom_arch_report.md`](scratchpad/subrom_arch_report.md), Stage 2):
      (a) the interrupt trampoline restores page 0 to a BOOT-TIME subslot
      (`INT_SUB_SUBSL`) -- save/restore the live $FFFF byte instead (~8 B,
      inside the 64 B reservation), alone, gated; (b) a `sub2.rom` skeleton +
      both machine configs + tool parameters, gated by injected pings, ZERO main
      bytes; (c) main's dispatch (`SUBSLOT2`, a second call entry, discovery --
      ~12-15 B low, or 0 B through a gateway tenant in 3-2); (d) the first
      tenant, with a nested-call gate and an EI gate. Measure one tenant call's
      T-states first (estimated ~0.9-1 k T, mostly C-BIOS's CALSLT).

- [ ] 🏗️ **D-PAGE2ISLAND — TENANTS MAPPED INTO PAGE 2 ($8000-$BFFF), FOR AUDITED
      TENANTS ONLY (ruled open 2026-10-11)**
      🎚️ BUDGET — supply, and only for a tenant that can prove its RAM footprint.
      🏗️ **RULED BY JOOST, 2026-10-11:** *"Open it for audited tenants"*. A
      tenant mapped into page 2 hides the BASIC program text, variables,
      arrays and strings while it runs, so each one needs its footprint proven
      to stay in page 3 (work area, stack) -- a write watchpoint over $8000-$BFFF
      across its gate rows, and a knife that plants one such access.
      🤖 **AUTONOMOUS** when a candidate needs it; none is named yet. Do not
      re-ask whether page 2 is allowed.

"""
s = s.replace(anchor, new + anchor)
open(p, "w").write(s)
print("ok")
