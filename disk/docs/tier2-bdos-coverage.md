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
| `$02` | CONOUT | yes (n=5–16) | ⚠ render | reaches CHPUT with the right char but VRAM gets constant tile `$80` (COMMAND.COM phase) | **DOWNGRADED 2026-06-30**: calls match stock byte-for-byte, but `screen`+`iowrite` show ours writes `$80` per glyph (early MSXDOS.SYS phase WORKS — `$0BEE` nth=1 == stock). Pure data divergence (same PC path); BC/DE/HL register-faithfulness tested + DISPROVEN. Next suspect IX/IY or page-0-map read. THE active blocker. |
| `$09` | STROUT | yes (n=1,3,17) | ⚠ render | calls match byte-identically, but renders via the same broken CHPUT path | same `$80` render bug as CONOUT (STROUT loops over CHPUT) — call-verified, not VRAM-verified |
| `$0A` | BUFIN | yes (n=18, 28, …) | ✅* | stock parks for a key; ours' headless BUFIN returns empty → ours runs into the A> loop | *headless: ours reaches BUFIN at the date prompt (n=18) AND at the A> command prompt (n=28+), looping cleanly. Real keyboard input untested ([[tier2-storms-are-downstream]]); the call/return is correct |
| `$0E` | SELDSK | yes (n=22) | ✅* | called in the A> command loop past BUFIN; ours proceeds | *now on the clean post-BUFIN path (earlier it only appeared in the pre-`$F338`-fix derail) |
| `$0F` | FOPEN | yes (n=2) | ⚠ partial | COMMAND.COM-load FOPEN ✅; full dir-search / not-found path ⚠ (`$4462` chain) | [tier2-bdos-scope.md](tier2-bdos-scope.md): 23-addr path, 2 covered |
| `$19` | CURDRV | yes (n=25,30,…) | ✅* | called each A> prompt redraw; ours proceeds | *the A> idle loop calls it to print the drive letter |
| `$2A` | GDATE | yes (n=4) | ✅ | handler `gdate_handler` @ `$553C` + `$F30D/$F30E` format defaults | DONE 2026-06-27 — returns 1984-01-01 default; `$CC04` diff NONE; backed by callseq + test_gdate.py |
| `$2B` | SDATE | yes (n=21) | ✅* | called past BUFIN with DE=0101 HL=07C0; RETURNS, ours proceeds to SELDSK | *NOT a blocker (refuted the prior hypothesis): ours accepts the default date and continues into the A> loop. No host unit test yet; behavior past entry is "returns cleanly" |
| `$2C` | GTIME | unknown | 🔲 | — | clock-group; may be called like GDATE |
| `$2D` | STIME | unknown | 🔲 | — | clock-group |

### Not yet observed on the boot path (full MSX-DOS-1 BDOS, for completeness)
`$00` TERM0 · `$01` CONIN · `$0B` CONST · `$0C` CPMVER · `$0D` DSKRST · `$10` FCLOSE · `$11`
SFIRST · `$12` SNEXT · `$13` FDEL · `$14` RDSEQ · `$15` WRSEQ · `$16` FMAKE · `$17` FREN · `$18`
LOGIN · `$1A` SETDTA · `$1B` ALLOC · `$21` RDRND · `$22` WRRND · `$23` FSIZE · `$24` SETRND ·
`$25`–`$28` block/rand · `$2E` VERIFY · `$2F` RDABS · `$30` WRABS — all 🔲 (a running shell /
user programs will exercise these; out of scope until `A>` is reached, then re-survey).

## Reading the score
- **Control flow reaches `A>` (2026-06-30):** every BDOS function COMMAND.COM calls on the boot path
  through the A> idle loop now sequences correctly — GDATE/SDATE/SELDSK/CURDRV/BUFIN all return and
  ours proceeds. `$0F` FOPEN is ⚠-partial but its COMMAND.COM-load subset works (not-found path is
  downstream of A>). **But `A>` is NOT yet VISIBLE** — see the render blocker below.
- **THE active blocker is rendering, not control flow:** `$02` CONOUT / `$09` STROUT are ⚠-render —
  the calls match stock byte-for-byte but ours' CHPUT writes tile `$80` for every glyph, so the
  whole screen (banner, prompts, `A>`) is garbage. This was hidden because coverage was scored from
  the *call sequence*; the new `screen` mode scores the *side effect* (VRAM). Lesson: **a ✅ needs
  the OUTPUT verified, not just the call.**
- **Pattern (the Tier-2 lesson):** most ⚠ are a **canonical-address collision** — the kernel calls a
  fixed handler ours repurposed for Tier-1 code; fix = clean-room handler + net-zero relocation. The
  CONOUT ⚠ is a different species: a **faithful-inter-slot-call** bug (ours' hand-rolled page-in +
  direct `call $00A2` doesn't reproduce stock's CALSLT/`$F398` register context CHPUT needs).
