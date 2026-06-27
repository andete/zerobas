<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 — MSX-DOS-1 BDOS coverage scoreboard

**What this is:** a living per-function scoreboard of how much of the MSX-DOS-1 BDOS the
zerobas-disk ROM correctly services on the path to the `A>` prompt. The kernel dispatches every
BDOS call through a per-function table (`$D8BE + 3*C` → {segment, handler}, see
[tier2-gdate-spec.md](tier2-gdate-spec.md) §3), so "BDOS function number" is the natural unit.

**How it's maintained (don't hand-guess):** seed each row from `disk_probe_diff.py callseq`
output — it reports, per call, whether ours matches stock at the same logical point. Mark only
what a probe has shown; leave the rest `unknown`. Re-run after each slice lands and update.
Repro: `python3 probes/disk/disk_probe_diff.py callseq --maxhits 40 --diska
~/Documents/msx/msx/disks/test.dsk` (oracle disk = **test.dsk**).

**Status legend:**
- ✅ **converges** — ours matches stock at this call (same params, return, branch). A mature ✅
  has **two backings**: the emulator differential (proven once vs the oracle) AND a host unit test
  (`tests/test_<fn>.py`, locks the contract in every build) — see [[host-unit-test-harness]]. Add
  the unit test as each implemented slice lands; assert oracle-pinned values, not invented ones.
- ⚠ **diverges** — ours runs unrelated code / a stub at the canonical handler (collision); returns
  garbage. The active Tier-2 work.
- 🔲 **not yet exercised / untested** — not seen on the boot path so far, or reached but behavior
  past entry not yet checked.
- — **n/a** — not part of MSX-DOS 1 / not expected on the boot path.

**Scope of "boot path" so far:** COMMAND.COM startup → the date prompt → BUFIN (date input).
This is NOT the full BDOS surface a running shell + user programs exercise — it is what stands
between us and `A>`. Functions not yet on this path are 🔲 by default, not ✅.

## Scoreboard (boot → `A>`)

| C | fn | on boot path? | ours | evidence / handler | notes |
|------|--------|---------------|------|--------------------|-------|
| `$02` | CONOUT | yes (n=5–16) | ✅ | real CONOUT at `$5454` (M8) | faithfully prints the bytes given; date garbage was upstream, not CONOUT |
| `$09` | STROUT | yes (n=1,3,17) | ✅ | banner + prompt print byte-identical | settled fact |
| `$0A` | BUFIN | yes (n=18) | 🔲 | stock parks here (date input wait) | ours reaches it only AFTER the `_GDATE` fix; headless BUFIN behavior untested ([[tier2-storms-are-downstream]]) |
| `$0E` | SELDSK | seen (early derail) | 🔲 | — | appeared in the pre-`$F338`-fix loop; not characterized on the clean path |
| `$0F` | FOPEN | yes (n=2) | ⚠ partial | COMMAND.COM-load FOPEN ✅; full dir-search / not-found path ⚠ (`$4462` chain) | [tier2-bdos-scope.md](tier2-bdos-scope.md): 23-addr path, 2 covered |
| `$19` | CURDRV | seen (early derail) | 🔲 | — | not characterized on the clean path |
| `$2A` | GDATE | yes (n=4) | ⚠ → fixing | handler canonical `$553C` (ours: `bdos_create_body`) | THE current blocker; [tier2-gdate-spec.md](tier2-gdate-spec.md) — clock-less default 1984-01-01 |
| `$2B` | SDATE | likely (past BUFIN) | 🔲 | own table entry → own canonical handler | next slice: accepting the date prompt probably calls this; possibly a no-op `ret` suffices |
| `$2C` | GTIME | unknown | 🔲 | — | clock-group; may be called like GDATE |
| `$2D` | STIME | unknown | 🔲 | — | clock-group |

### Not yet observed on the boot path (full MSX-DOS-1 BDOS, for completeness)
`$00` TERM0 · `$01` CONIN · `$0B` CONST · `$0C` CPMVER · `$0D` DSKRST · `$10` FCLOSE · `$11`
SFIRST · `$12` SNEXT · `$13` FDEL · `$14` RDSEQ · `$15` WRSEQ · `$16` FMAKE · `$17` FREN · `$18`
LOGIN · `$1A` SETDTA · `$1B` ALLOC · `$21` RDRND · `$22` WRRND · `$23` FSIZE · `$24` SETRND ·
`$25`–`$28` block/rand · `$2E` VERIFY · `$2F` RDABS · `$30` WRABS — all 🔲 (a running shell /
user programs will exercise these; out of scope until `A>` is reached, then re-survey).

## Reading the score
- **Reached `A>` requires:** every function COMMAND.COM calls on the boot path = ✅. Today the
  one ⚠ blocker on the critical path is `$2A` GDATE (this slice); `$0F` FOPEN is ⚠-partial but
  its COMMAND.COM-load subset works, and the not-found path is a separate downstream concern.
- **Pattern (the Tier-2 lesson):** a ⚠ is almost always a **canonical-address collision** — the
  kernel calls a fixed handler address that ours repurposed for Tier-1 Disk-BASIC/BDOS code. Each
  fix = clean-room handler at that address + net-zero relocation of the displaced Tier-1 body.
