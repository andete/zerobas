# Reclaiming page-0 space by repacking C-BIOS (future option)

**Status: FUTURE / not scheduled.** Investigated 2026-07-09 to size the option the
user raised — evolve the tape IPS patch into a denser C-BIOS so BASIC can reclaim
page-0 space, recreating the real-MSX layout (BIOS + BASIC in one 32 KB main ROM).
Conclusion up front: the option is real and **much cheaper than a "rewrite" — it is
mostly a *repack*.** Deferred by decision; recorded so the budget isn't re-derived.

## Why this is clean-room-legal

C-BIOS is BSD 2-clause and an **allowed source** (tape/DESIGN.md "Allowed sources").
Reading, forking, and redistributing it (with attribution) is permitted — unlike the
stock MSX ROM, which is forbidden ([[no-reference-rom-disasm]]). This analysis was
done on the C-BIOS **source** at `~/projects/cbios` (v0.29, `git describe`
`v0.29-3-gb5ad9cb`), which rebuilds the exact target ROM
`cbios_main_msx1_eu.rom` sha1 `baf2e9c6…` byte-for-byte. Measurements come from the
build listing + the binary, not from any forbidden ROM.

## The finding: C-BIOS is not fat, it is *sparse*

The MSX1-EU main ROM's page-0 footprint runs `$0000–$3A70` (14 962 B), which is why
BASIC was boxed into page 1. But that footprint is **only ~8.3 KB of real content**;
**37 % (5 561 B) is ≥16-byte zero gaps** — C-BIOS pins routines/tables at
real-MSX-compatible addresses and pads the space between them.

| Region | Addr | ~Size | Note |
|---|---|---|---|
| BIOS jump table (JP stubs) | `$0000–$01B7` | 439 B | published entry contract — **keep pinned** |
| early BIOS + debug helpers | `$0200–$09D8` | ~2 KB | `print_debug_*` ~60 B (debug.asm, shipped) |
| **gap 1** | `$09D9–$0CFF` | **808 B** | pad before `chkram` |
| init / video / chput / inlin | `$0D12–$1AC9` | ~3.5 KB | core BIOS |
| **gap 2** | `$1ACA–$1BBE` | **253 B** | pad before font |
| `B_Font` character font | `$1BBF–$23BE` | 2048 B | incompressible; `CGTABL` points here — **keep** |
| slot routines (RDSLT/CALSLT/ENASLT) | `$23BF–$2555` | ~406 B | published entry bodies — keep |
| message strings | `$2556–$26BD` | ~360 B | several C-BIOS-boot-only ("No cartridge found") |
| scancode table (one locale) | `$26BE–$2805` | ~330 B | keyboard matrix — keep |
| `vdp_bios` init table | `$2806–$2811` | 12 B | keep |
| **gap 3** | `$2812–$3192` | **2 433 B** | — |
| `multiple`, `rombas`/`rombas_text` | `$3193–$31BA` | ~40 B | `rombas` = "Cannot execute BASIC" handler |
| **gap 4** | `$31BB–$392D` | **1 907 B** | — |
| `rombas_niy`/`_text` | `$3A3E–$3A70` | ~50 B | "ROM BASIC not implemented" message |

**Everything genuinely needed ends at `$2811`.** Above it float only ~90 B — `multiple`
(a real helper, relocatable) plus `rombas`/`rombas_niy` (the *"can't run a BASIC ROM"*
messages, which are **dead weight for a stack that ships BASIC**) — riding on 4.3 KB of gap.
Those two high pins are what drag the footprint to `$3A70`.

## Reclaim budget

### Approach 0 — Overwrite-and-fill (no relocation): ~5.3 KB, recommended first step

The cheapest path, and the tape-patch model extended: **touch no live C-BIOS byte** —
just neuter the dead handlers and drop BASIC routines into the existing holes. The IPS is
purely our own bytes at fixed offsets, no C-BIOS rebuild/diff.

| Hole | Range | Size | How |
|---|---|---|---|
| gap 3 | `$2812–$3192` | 2 433 B | fill as-is |
| `rombas` + gap 4 | `$31A0–$392D` | 1 934 B | neuter dead "can't run BASIC" handler, merges with gap 4 |
| `rombas_niy` | `$3A3E–$3A70` | 51 B | neuter (optional, tiny) |
| tail spare | `$3C43–$3FFF` | 957 B | page-0 spare above tape's block |

≈ **5.3 KB usable** (up to ~6.3 KB if gap 1 `$09D9`/gap 2 `$1ACA` are also used — ~1 KB
more but deep in live BIOS, more fragmented). Trade-offs vs. the repack below: it's
**fragmented** (small live islands `multiple`@`$3193` and a ~272 B blob@`$392E` stay put),
so BASIC routines are evicted to page 0 *individually* — each fits one hole, reached by
plain `CALL`; and it yields ~1.7 KB less than a consolidating repack. Neutering
`rombas`/`rombas_niy` is safe: C-BIOS's boot scan always finds our `"AB"` BASIC cart in
page 1 and calls INIT, so those "no cartridge / can't run BASIC" paths never execute
(verify-on-execute: confirm nothing else jumps into them).

### Approach 1 — Repack (relocate live content): ~7 KB contiguous, the escalation

Keep only the **jump table** (`$0000–$01B7`) and the **font** (`$1BBF–$23BE`) pinned;
everything else is relocatable. The font-pin forces a ~1.4 KB empty gap just below it
(the core BIOS below reaches only ~`$1734`) — we *fill that gap* with the ~1.4 KB of
keep-content stranded above the font (slot routines, strings, scancodes, `vdp_bios`,
`multiple`). That clears the whole region above the font.

- **Tier A — Repack, no golfing (the win): ~7.1 KB.** Drop `rombas`/`rombas_niy`
  (zerobas *is* the BASIC), relocate the above-font keep-content into the pre-font gap,
  remove the `ds` pins, rebuild. Frees **`$23BF–$3FFF` = 7 233 B**, **contiguous with
  page 1** → BASIC becomes one image ~`$23BF–$7FFF` ≈ **23 KB** (+44 % over today's
  16 KB) — the real-VG-8020 BASIC envelope. Font stays pinned at `$1BBF` (all reclaim is
  *above* it), so no `CGTABL`/font-compat risk. Page-0's real content is only ~8.4 KB, so
  ~7.8 KB is the theoretical free ceiling — Tier A captures nearly all of it.
- **Tier B — Trim genuine BIOS to approach ~10 KB: ~2–3 KB extra, real work.** Getting
  past ~7.8 KB means *cutting content*, not just repacking: drop debug.asm helpers
  (~60 B code), boot-only strings, and BIOS routines a game-loader doesn't need, and/or
  golf hot routines. Each cut needs full re-validation against the oracle + self-check
  gates. This is the only way to reach a ~10 KB / ~26 KB-BASIC figure.
- **Tier C — Deep golf of the remaining core BIOS: diminishing returns.** Not needed —
  Tier A alone reaches ~23 KB.

## How it ships (and the honest caveats)

It ships as an **IPS patch on a pristine C-BIOS — exactly like the tape and basic
patches today.** The user brings their own C-BIOS; we distribute a diff, not a BIOS.
The provenance firewall holds (a diff is not a merge; our BASIC bytes stay an overlay in
the freed region). No fork, no "own the BIOS" pivot — that framing was wrong.

What differs from today's patches is build-tooling only. Today's tape patch just fills
spare and repoints a few vectors, so stock bytes stay byte-identical outside the fill.
This patch **relocates C-BIOS's own page-0 code**, so the way to produce it is: make
small edits to C-BIOS *source* (allowed BSD source) — delete the `ds` pins + the dead
`rombas`/`rombas_niy` handlers, move above-font content into the pre-font gap — rebuild,
and **diff against stock to emit the IPS** (the assembler does all address fixups).

Remaining caveats:
1. **Relocating, not additive.** The patched ROM is no longer "stock plus fill" — a much
   bigger diff than the tape patch. Still a pristine-base overlay, just larger.
2. **Per-variant.** Each C-BIOS variant's page-0 layout differs, so the relocating IPS is
   computed per target (the tape build already does per-variant work — same machinery).
3. **Minor binary-compat.** Relocating C-BIOS internals above the font breaks software
   that peeks those fixed addresses — irrelevant for our own-stack loader; font stays put.

## Verify-on-execute (if this is ever taken up)

- Confirm `multiple`/`rombas`/`rombas_niy` are reached **only via relocatable internal
  CALL/JP**, with no fixed-address expectation from boot or hooks, before moving/removing.
- Re-validate every `$00xx` jump-table entry + `CGTABL` after the repack (the standing
  `bdos-cbios-selfcheck` / tape probes are the harness).
- Re-measure gaps per variant if more than MSX1-EU is targeted.

## Bottom line

The user's instinct is validated and then some: recreating the real-MSX BIOS+BASIC
32 KB layout does **not** require a dense BIOS rewrite — C-BIOS already fits its work in
~8.4 KB and merely spreads it out. A **repack** (drop the dead BASIC-can't-run handlers,
relocate the above-font content into the font-pin gap, rebuild) reclaims **~7 KB
contiguous with page 1**, giving BASIC a ~23 KB window. It **ships as an IPS on a
pristine C-BIOS, just like today's patches** — no fork, no identity pivot. The only
blocker is building the per-variant relocating-IPS tooling: real but bounded work.
Parked on priority, not on a strategic call.
