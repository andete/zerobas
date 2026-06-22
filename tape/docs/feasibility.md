# Feasibility: clean-room cassette (tape) BIOS routines for C-BIOS

C-BIOS deliberately ships **no working cassette subsystem** — the seven cassette
entry points are stubs or blockers (our probes confirmed it; see below). Tape was a
primary load medium for early MSX1 software, so the gap matters for booting tape
titles and for `.cas`-backed preservation. This note records whether a clean-room
reimplementation of *just those routines* is feasible, at what scope, and how it
would be staged.

This is the index document for the cassette side project; see [`../README.md`](../README.md) for the repo layout.

## Verdict

**Yes — legally trivial and technically self-contained, with one real wrinkle:
the code is timing-critical hardware signalling, so validation is the hard part,
not the implementation.**

- **Legal.** Easier than the BASIC effort. There is no Microsoft-lineage code here
  and no contested provenance: the cassette routines are small, the format is fully
  documented (MSX2 Technical Handbook, MSX Assembly Page), and C-BIOS is itself the
  proof that clean-room MSX firmware is fine. Same discipline applies regardless —
  reference ROM is an *oracle, not an answer key* (see
  [`clean-room-policy.md`](clean-room-policy.md)).
- **Scope.** Exactly the seven entry points (`$00E1`–`$00F3`) and the work-area
  state they read/write — the leader-tone generator, the bit/byte FSK encoder and
  decoder, the motor relay, and the session open/close calls. Nothing else. This is
  a **small, bounded** surface, far smaller than the BASIC interpreter.
- **The wrinkle.** Unlike BASIC (logic over memory), tape code is **real-time
  hardware signalling** — bit timing on the CAS-out write line and edge detection on
  the CAS-in read line. "Correct" means *byte-compatible FSK at the documented baud
  rates*, which a black-box memory diff can't see. The oracle therefore has to drive
  an actual tape signal (see *How we validate*), not just break-and-dump.

This repo (`zerobas-tape`) holds the **feasibility note, the behavioural spec, and the
implementation**. The validation harness — openMSX probes, `omsx_run.py`, oracle
captures — lives in the companion
[`msx-preservation`](https://github.com/andete/msx-preservation) analysis repo.

## What the probes already established

From [`docs/cbios-probe-results.md`](https://github.com/andete/msx-preservation/blob/main/docs/cbios-probe-results.md)
(§ *Cassette motor*), each call run on C-BIOS and on a Sony VG-8020 oracle:

| Entry | Addr | What we know today | Gap to fill |
|-------|------|--------------------|-------------|
| TAPION | `$00E1` | C-BIOS spins forever on the CAS-in pin; no leader detection | **read path: leader sync + phase lock** |
| TAPIN  | `$00E4` | same CAS-in block | **read path: one byte of FSK → A** |
| TAPIOF | `$00E7` | no-op with motor off (correct in isolation) | session-close state; pairs with TAPION |
| TAPOON | `$00EA` | **stub** — PPI-C unchanged, emits no leader tone | **write path: motor on + ~2s leader tone** |
| TAPOUT | `$00ED` | **stub** — returns carry=error, writes nothing | **write path: A → one byte of FSK** |
| TAPOOF | `$00F0` | no-op with motor off (correct in isolation) | session-close state; pairs with TAPOON |
| STMOTR | `$00F3` | toggles PPI-C bit 4 (motor relay) correctly | C-BIOS's works, but we reimplement it (PPI-C bit 4 via BSR) to drop the dependency |

So the **motor relay works** and the **session-terminate calls are correct in
isolation**; the entire **read FSK** (`TAPION`/`TAPIN`) and **write FSK**
(`TAPOON`/`TAPOUT`) signal layer is what we build. `STMOTR` is the one piece we can
lean on directly.

## What the routines actually do

The cassette format is documented and small:

- **Hardware lines** (i8255 PPI). The motor relay and the CAS-**out** write line are
  driven through PPI register C (port `$AA`); the CAS-**in** read line is sampled
  from PPI register B (port `$A9`, bit 7). Exact bit assignments are pinned in the
  spec from an allowed source and re-confirmed by oracle.
- **Encoding.** FSK: a `0` bit is one cycle at the low frequency, a `1` bit is two
  cycles at the high frequency. Standard baud rates are **1200 and 2400** (the BAUD
  word selects). Each byte is framed: start bit, 8 data bits LSB-first, stop bits.
- **Block structure.** A recording is a long **leader tone** (~2s of the high
  frequency for phase lock), then framed bytes. The header/data block split and the
  `0xD0`×10 binary file-type marker are already characterised in the BASIC project's
  [`spec-bload-r.md`](https://github.com/andete/msx-preservation/blob/main/basic-spec/docs/spec-bload-r.md); this project owns the
  layer *below* that — turning those bytes into edges and back.

## Three things that decide it

1. **The surface is tiny and bounded.** Seven entry points, one shared FSK codec,
   one leader generator. No open-ended language to scope (the BASIC project's main
   cost). This is the smallest self-contained C-BIOS gap we have.
2. **The format is a documented interface, not free design.** Baud rates, framing,
   leader length, sync header, file-type bytes are all public (TH / MAP) and
   independently confirmable by black-box oracle (write a known byte stream, read the
   resulting `.cas`/`.wav` edges back). Treated as an interface spec — reconstructed,
   never copied from a disassembly.
3. **Validation, not implementation, is the risk.** Headless break-and-dump cannot
   see signal timing, and the real VG-8020 oracle needs a physical tape transport to
   exercise the read path. The mitigation below is the load-bearing part of this
   project.

## How we validate (the part that differs from BASIC)

Memory diffs aren't enough; we need the signal. Three oracle tiers, cheapest first:

1. **openMSX with injected tape media (primary) — proven.** openMSX records CAS-out
   to a new tape via `cassetteplayer new` (wired into `omsx_run.py --record`) and runs
   the *emulated* write path with throttle off. **Phase 1 confirmed this works:** a
   probe cart drove `TAPOON`+`TAPOUT` on the VG-8020, the recording decoded back to
   the exact input bytes via `tools/omsx/cas_decode.py`. This is why C-BIOS's earlier
   headless probes *blocked* — no media was mounted, not because the path is
   untestable. The read direction (mount a known-good `.cas`, decode via `TAPIN`) is
   Phase 2.
2. **Cross-check against the `.cas` codec.** The host-side encode/decode in the companion
   [`cassette-tool/`](../cassette-tool/README.md) is an independent
   second implementation of the same format: bytes our on-MSX code writes must match
   what the host tool encodes, and vice-versa. Two implementations agreeing on the
   format is strong evidence neither copied the original.
3. **Real-machine confirmation (optional, last).** A VG-8020 reading/writing a real
   tape is the ground truth, but it is slow and manual; used to spot-confirm, not as
   the loop.

### Validation hardening still needed (synthetic signals are not enough)

Everything proven so far (Phases 1–3) round-trips against signals our *own* write
path generated under openMSX — clean, square, jitter-free by construction. That
proves the codec is self-consistent, not that the **reader tolerates real tapes**.
Two pieces of validation are outstanding and should be added before claiming the
read path is robust:

1. **Real WAV tape captures — done; found a real bug.** `TAPION`/`TAPIN` now read
   genuine analog captures (a local tape directory) byte-for-byte at 2400 baud,
   **both blocks** of a file (header + data), verified against the host decoder on
   `hero`/`br`/`HSPORT1`/`HSPORT2`/`ROADF`. Getting there exposed exactly the class
   of bug synthetic signals cannot: the mid-tape **motor-restart spin-up** (flat
   patch + stray very-long half + chatter) broke `TAPION`'s re-lock on the second
   block. Fixed by skipping the transient and waiting out flat patches while
   measuring the leader; see [`spec-cassette.md`](spec-cassette.md) (TAPION).
2. **A degradation generator — built.** [`cassette-tool/degrade_wav.py`](../cassette-tool/README.md)
   applies parameterised, *still-in-spec* impairments (speed error, wow/flutter,
   low-pass, DC bias/duty skew, gain, additive noise) and `tolerance_sweep.py` maps
   the pass/fail envelope. **First finding:** the read path is very tolerant of
   bandwidth limiting and of ±25–35% speed error, but **noise-sensitive (~0.05 of
   full scale)** — the 1-bit comparator input chatters at zero-crossings under
   noise. The synthetic round-trips hid this entirely; it is the headline reason
   this validation tier matters.

Both feed the same openMSX read harness; neither needs new on-MSX code, only host
tooling and sample captures. Tracked here so the dual-baud success is not mistaken
for real-world robustness.

## Phased roadmap

Each phase ships something useful and stands alone.

- **Phase 0 — Feasibility note + policy + spec.** This document,
  [`clean-room-policy.md`](clean-room-policy.md), and the behavioural spec
  [`spec-cassette.md`](spec-cassette.md). Pure docs; no code. **Done.**
- **Phase 1 — Oracle first light: capture the write path.** **Done.** The write FSK
  was captured end to end from the VG-8020 oracle: `tools/omsx/bios_probe_tapwrite.py`
  drives `TAPOON`+`TAPOUT[55 AA 4A 4F 4E 47]`+`TAPOOF`; `omsx_run.py --record` saves
  CAS-out; `tools/omsx/cas_decode.py` round-trips it to the exact bytes (1200 baud,
  1213/2393 Hz). C-BIOS writes nothing (carry=error) — the negative control. This
  establishes the *oracle* the implementer's write code must match. (The clean-room
  implementation `.asm` itself is the next step and lives in the cassette project's
  own repo, not here.)
- **Phase 2 — Read path: read one byte.** **Done.** `TAPION` (leader detect +
  auto-baud threshold via `LOWLIM`) and `TAPIN` (start-bit hunt + half-period
  classification, LSB-first) are implemented in `tape.asm` and **close the loop**:
  the recording our write path produced, fed back as cassette media, is read back
  by `TAPION`+`TAPIN` to the exact 6-byte pattern (carry=0), with a realistic ~2 s
  leader. Hardware correction landed here too — CAS-in is **PSG R14 bit 7**, not
  PPI-B (located empirically by `tools/omsx/bios_probe_casin.py`). Harness:
  `bios_probe_tapread.py`, `bios_probe_tapraw.py` (raw half-period diagnostic).
- **Phase 3 — Both baud rates + full block round-trip.** **Baud part done:** `TAPOON`
  reads the write baud from the live work area (the active signal-length word the
  system's `SCREEN ,,,baud` sets — oracle-pinned with `cas_baud_oracle.py --screen`)
  and read auto-derives the rate, closing the write→read loop at **1200 and 2400 baud**
  over six byte patterns (incl. `00`/`FF`/walking-ones). 2400 needed a quarter-count
  `LOWLIM` for fractional threshold precision. **Block round-trip also done:** a full BSAVE
  binary file — header block (`0xD0`×10 + filename) + data block (start/end/exec +
  payload) — round-trips through the byte-level entry points at both bauds, including
  the short header, a second block, and `TAPION` re-locking mid-tape after `TAPIOF`
  (the session open/close pairing). **Remaining:** error/timeout behaviour edges
  (carry semantics `TAPOUT` already signals), and the validation hardening above.
- **Phase 4 — Differential validation.** Run the full set under openMSX on the new
  code versus the reference oracle (real machine where feasible); byte/behaviour diff
  per the established classification (pass / quarantine / bug), tracked in a
  `docs/checklist.md` created then.

## Keep it a separate (or upstreamable) component

Like the BASIC project, the implementation graduates to a provenance-clean release
rather than being written into C-BIOS's tree here. **Unlike** the BASIC project,
there is a plausible case for *upstreaming into C-BIOS* eventually: the cassette
routines carry no Microsoft lineage and fill a real C-BIOS gap, so if provenance is
audited clean (see [`clean-room-policy.md`](clean-room-policy.md)) they could be
offered upstream. That decision is deferred to after Phase 4; until then the firewall
holds and nothing is folded into C-BIOS.

**Interim distribution: an IPS / BPS patch.** Until any upstreaming, the build ships
as a **patch against a stock C-BIOS v0.29 ROM** (this repo's `zerobas-tape-msx1.ips`/
`.bps`), not a modified ROM — both an IPS (universal) and a BPS (embeds a
source-ROM CRC so a wrong base fails cleanly instead of silently corrupting).
Applying it requires the user to already hold C-BIOS, and it pins the result to an
exact target (`baf2e9c6…` → `ff8bcf59…`).

The cassette routines are deliberately assembled into **unused ROM** (stock C-BIOS
fills ~71% of the 32 KB image with `0x00`; our ~323-byte block goes into the free
run at `$3A72`, within the first 16 KB). Because the code lands in spare space and
the originals are left in place, **nothing is displaced and nothing is removed**:
the patch is just two regions — six cassette jump vectors and our code block —
totalling 328 bytes (1.0% of the ROM), ~0.4 KB packed. STMOTR already works in
C-BIOS, so its vector is left pointing at the stock routine. This makes the patch
clean as a binary: it carries **no stock-C-BIOS code** at all (the original cassette
stubs stay byte-for-byte in place, merely unreferenced). The code sits entirely in
page 0 (`< 0x4000`) on purpose — the second 16 KB is paged out for BASIC/cartridges
— enforced by a `ds $4000 - $` build guard. An earlier in-place version grew the
cassette area and rippled a +212-byte relocation into ~40 references ROM-wide;
moving the code into free ROM removed all of it. The build still assembles full
C-BIOS and diffs (reproducible, no hard-coded addresses).

## Open decision

Whether to share one FSK codec routine between encode and decode or keep them
separate is deferred to Phase 2, when the read path reveals how much of the bit
timing actually mirrors the write path.
