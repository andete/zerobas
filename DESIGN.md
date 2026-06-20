# cbios-tape

A **clean-room reimplementation of the MSX cassette (tape) BIOS routines** that
C-BIOS leaves unimplemented, shipped as a tiny **patch** against a stock C-BIOS
v0.29 ROM. Scoped to *just* the seven cassette entry points (`$00E1`–`$00F3`) and
the work-area state they touch — the read and write signal paths C-BIOS ships as
stubs.

cbios-tape is a deliberately **separate project**. It is combined with C-BIOS only
*at runtime* — as a binary patch the user applies to their own ROM — never merged
into the C-BIOS source tree. This is a legal firewall: a provenance challenge to
the cassette code can never contaminate the mature, uncontested BIOS it plugs into.

## The gap it fills

C-BIOS ships tape **stubs**, not a tape subsystem. Against a real Philips VG-8020 as
oracle: `STMOTR` (motor relay) and the session-terminate calls work, but
`TAPION`/`TAPIN` (read) block forever and `TAPOON`/`TAPOUT` (write) are no-ops.
cbios-tape implements that missing signal layer: FSK leader detection with
auto-baud, byte framing, and the write waveform, at both 1200 and 2400 baud.

## Traceability is the whole point

Every constant, address, and algorithm in this repo **must trace to an allowed
source.** This is not a guideline — it is the load-bearing property that makes the
code distributable.

- **[`PROVENANCE.md`](PROVENANCE.md)** — the provenance log: one row per item, each
  marked `sourced` (traced to an allowed source or this project's own black-box
  oracle observation) or `quarantined` (no copied source; derived from the
  documented format + CPU clock, justified by oracle round-trip, never lifted from
  a reference ROM).
- **Inline citations** — non-obvious values in [`src/tape.asm`](src/tape.asm) name
  their basis in a comment (e.g. `; CAS-in is PSG R14 bit 7`, the FSK derivation).

**Allowed sources:** the MSX2 Technical Handbook, the MSX Assembly Page
(`map.grauw.nl`), hardware datasheets (AY-3-8910 PSG / i8255 PPI), C-BIOS sources
(BSD 2-clause, for entry-point and work-area addresses, and the single v0.29 ROM
layout fact `FREE_ORG`), and this project's own black-box **oracle observations**.

**Forbidden, without exception:** any reference MSX BIOS disassembly or commented
listing — including the cassette routines of any reference ROM (e.g. the VG-8020
used as the oracle). A reference ROM is only ever an *oracle*: identical inputs in,
observed bytes/edges out.

The behavioural specifications cbios-tape is built from live in [`docs/`](docs/)
here, produced by driving a real MSX (and openMSX) as a black box.

## Build

Requires [pasmo](https://pasmo.speccy.org/) and `python3`:

```sh
make                        # -> cbios-tape-msx1.ips + .bps
```

`pasmo` assembles `src/tape.asm` to just the bytes the patch adds, then
`tools/rom_patch.py forge` slices the two changed regions out (vectors at `0xE2`,
code from `0x3A72` to the `tape_end` label). **No C-BIOS is compiled.** A stock
C-BIOS v0.29 ROM is the patch *target*, not a build input — it is used only to
stamp the BPS source/target CRC32 and verify the result (apply → `ff8bcf59…`); the
build auto-detects openMSX's bundled copy, or pass one: `make STOCK=/path/to.rom`.

## What the patch changes (2 regions)

The routines are assembled into **unused** page-0 ROM, so adding them displaces no
stock C-BIOS code. The patch touches exactly two places:

- `0x00E2–0x00F5` (20 B) — the targets of **all seven** cassette jump vectors
  (TAPION, TAPIN, TAPIOF, TAPOON, TAPOUT, TAPOOF, STMOTR), repointed to the new code.
  STMOTR (`$00F3`) now dispatches to *our own* motor routine, so the patch relies on
  no stock-C-BIOS code at all — only on the spare ROM being free.
- `0x3A72–0x3BC8` (347 B) — our routines, over former `0x00` fill.

Everything else is byte-identical to stock, including C-BIOS's original cassette
stubs (`0x16B2`), which are left untouched. The code lives entirely in the first
16 KB (`< 0x4000`), because the second 16 KB is paged out for BASIC/cartridges; a
`ds $4000 - tape_end` guard in the source enforces this.

| | |
|---|---|
| Target ROM | C-BIOS **v0.29** `cbios_main_msx1_eu.rom`, sha1 `baf2e9c69252fd9b350b488d89c71887b9d05eec` (openMSX's bundled `C-BIOS_MSX1`) |
| Result ROM | tape-enabled, sha1 `ff8bcf59e457aad5352ec018feeebe236fc0f12b` |
| Changed | 367 bytes, 1.1% of the 32 KB ROM, in 2 regions |

## Apply it

```sh
python3 tools/rom_patch.py apply cbios_main_msx1_eu.rom \
    cbios-tape-msx1.bps  cbios_main_msx1_eu_tape.rom
```

Standard patchers work too (`flips`, `Lunar IPS`, emulators' patch-on-load). **BPS**
embeds CRC32 of source and target, so a wrong base ROM fails cleanly — prefer it.
**IPS** is universally supported but carries no checksum: apply it only to the
`baf2e9c6…` ROM and verify the result is `ff8bcf59…`. openMSX can apply the IPS at
load time via a `<patches><ips>` element on the ROM.

### Applies to every C-BIOS ROM (own motor routine)

The patch carries its own `STMOTR` (it toggles i8255 PPI Port C bit 4 via the same
BSR control port `$AB` the write path uses for `CASW`), so it no longer depends on
the stock motor routine's address. Its **only** remaining ROM-specific fact is
`FREE_ORG = $3A72` — the spare `0x00` fill it lands in.

That fact holds in **all 12** C-BIOS main ROMs openMSX ships — every MSX1, MSX2, and
MSX2+ variant: each has `$3A72–$3BC8` as `0x00` fill and `$00E1 = $C3` (the cassette
jump table). So the *same* IPS bytes apply, byte-safely, to all of them, and the
repointed dispatch (incl. `$00F3 → $3A72`) is live in each. (The **BPS** stays
EU-specific — its CRC32 is keyed to `baf2e9c6…` — so use the IPS for the others, or
`tools/install-openmsx-machine.py`, which patches each on load.)

The cassette signal path itself is CPU-clock-derived (the same 3.58 MHz Z80
everywhere) and uses only standard work-area sysvars, so it behaves identically across
generations. The full two-block write/read **round-trip is validated on MSX1, MSX2,
and MSX2+** (EU and JP), at both 1200 and 2400 baud, via the companion repo's openMSX
probe harness — a write cart records CAS-out to a `.wav`, a read cart reads it back,
and the bytes match.

## Status

Write path (`TAPOON`/`TAPOUT`/`TAPOOF`) and read path (`TAPION` leader-detect +
auto-baud, `TAPIN` start-bit hunt + half-period classification) are implemented and
**close the loop**: a full BSAVE-style file (header block + data block) round-trips
through the byte-level entry points at **both 1200 and 2400 baud**, including
mid-tape `TAPION` re-lock. The write baud is **read from the live work area**, not a
private flag: `TAPOON` inspects the active signal-length word (`$F406`, which the
system's `SCREEN ,,,baud` sets) and honours whatever baud was chosen, defaulting to
1200 for a blank/unrecognised table (see `PROVENANCE.md`). Validated byte-for-byte
against genuine analog 2400-baud captures (`hero`/`br`/`HSPORT1`/`HSPORT2`/`ROADF`).
Remaining: an independent host `.cas` codec cross-check and a wider
degradation-tolerance envelope.

## Validation

The openMSX probe harness and oracle captures live in the companion
[`msx-preservation`](https://github.com/andete/msx-preservation) analysis repo
(`tools/omsx/bios_probe_tap*.py`). They boot a stock C-BIOS ROM with this patch
applied on load and exercise the routines — a write cart records CAS-out to a `.wav`,
a read cart reads it back, and the bytes must match. See
[`docs/dev-setup.md`](docs/dev-setup.md).

## Note on C-BIOS

C-BIOS (https://github.com/cbios/cbios, BSD 2-clause) is the open MSX BIOS this
patch targets. cbios-tape carries **no** stock-C-BIOS code: the patch's only
substantive region is our clean-room code written over `0x00` fill, and the other
is seven vector addresses. The original stubs stay byte-for-byte in place, and — now
that we ship our own motor routine — the patch calls into no stock C-BIOS code at all.
