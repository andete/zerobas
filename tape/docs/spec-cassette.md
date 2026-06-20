# Behavioural spec: the seven cassette BIOS entry points

Derived from **allowed public sources** (MSX2 Technical Handbook cassette I/O
chapter; MSX Assembly Page BIOS call list, sysvar map, i8255 PPI map) plus **this
project's own black-box oracle observations**. No disassembly consulted. See
[`clean-room-policy.md`](clean-room-policy.md).

This is the implementer-facing artefact. It pins the **contracts** (register I/O,
side effects, error semantics) for each entry point and records what the oracle has
confirmed so far versus what still needs Phase 1+ signal capture. The implementation
lives in the cassette project's own repo, not here.

> **Maturity.** Phase 0 records the documented contracts and the break-and-dump
> findings already in [`docs/cbios-probe-results.md`](https://github.com/andete/msx-preservation/blob/main/docs/cbios-probe-results.md).
> The **write-path** signal rows are now **captured** (Phase 1): a probe cart
> (`tools/omsx/bios_probe_tapwrite.py`) drove `TAPOON`+`TAPOUT` on the VG-8020,
> openMSX recorded CAS-out via `omsx_run.py --record`, and
> `tools/omsx/cas_decode.py` round-tripped the exact byte pattern. The **read-path**
> rows (leader detect, phase lock) remain *to capture* (Phase 2).

## Shared model

### Hardware lines (i8255 PPI)

| Line | Port | Bit | Direction | Role |
|------|------|-----|-----------|------|
| Motor relay | `$AA` (PPI reg C) | 4 | out | 0 = motor on, 1 = off — confirmed by STMOTR oracle (delta `$10`) |
| CAS-out (write) | `$AA` (PPI reg C) | — | out | drives the recording signal; exact bit pinned from MAP, re-confirmed by oracle |
| CAS-in (read) | PSG **R14** (read via `$A0`/`$A2`) | 7 | in | cassette read line; TAPION/TAPIN sample this bit |

> Exact CAS-out bit assignment is **to confirm** against the MAP i8255 map + oracle
> in Phase 1; the motor bit is oracle-confirmed today.

### Encoding (documented, to confirm by round-trip)

- **FSK.** A `0` bit = one cycle at the low frequency; a `1` bit = two cycles at the
  high frequency. Standard baud rates **1200 / 2400**; at 2400 both tones shift up an
  octave (its low tone = 1200 baud's high tone). **Oracle-confirmed (Phase 1):** the
  VG-8020 default write is **1200 baud** — measured **1213 Hz** (low) / **2393 Hz**
  (high). **Both rates implemented + round-tripped (Phase 3):** the code writes at the
  baud read from the live work area (`TAPOON` honours the active signal-length word
  the system's `SCREEN ,,,baud` sets) and reads either back with no selector (the
  reader auto-derives the rate); 6 byte patterns incl. `00`/`FF`/walking-ones close
  the write→read loop at each rate.
- **Byte framing.** Start bit, 8 data bits LSB-first, stop bit(s). **Oracle-confirmed:**
  decoding as start(0)/8-LSB-first/stop(1) recovered the written bytes exactly.
- **Leader.** ~2 s of the high frequency for phase lock at the start of a block, plus
  a short re-sync between header and data blocks. **Oracle-confirmed:** the long
  header is a continuous high-frequency tone (99.8% of half-periods in the capture).
- **Block layout** (header + data, `0xD0`×10 binary file-type marker) is characterised
  in the BASIC project's [`spec-bload-r.md`](https://github.com/andete/msx-preservation/blob/main/basic-spec/docs/spec-bload-r.md);
  this project owns the layer that turns those bytes into edges and back.

### Relevant work-area sysvars (addresses from MAP/TH; to wire up)

`BAUD`, `LOWLIM`, `WINWID`, `HEADER`, `MINDEL`/`MAXDEL`-class timing words, and the
motor state. Exact addresses go in the provenance log as they are used.

## Per-entry contracts

### TAPION — `$00E1` — open tape for reading
- **In:** none. **Out:** carry set on error/timeout (no leader found); on success the
  read session is open and phase-locked.
- **Side effects:** motor on; reads CAS-in to detect and lock onto the leader tone.
- **Baud auto-detection.** The read path is **not told** the baud rate — `TAPION`
  *measures* the leader tone's half-period and from it computes the discrimination
  windows (`LOWLIM` `$FCA4` / `WINWID` `$FCA5`, plus the current-speed words
  `LOW_`/`HIGH_`) that `TAPIN` then uses to tell a `0` cycle from a `1` cycle. So a
  tape written at any supported rate (1200 / 2400 / higher) reads back without the
  user specifying it; `TAPION` *is* the per-tape calibration step, not merely a
  "wait for tone" gate. (Write side is the inverse: the rate is *selected* via the
  `CS120`/`CS240` tables copied into `LOW_`/`HIGH_`/`HEADER`.)
- **C-BIOS today:** stub returns carry=error — **not implemented**.
- **Implemented (`tape.asm`):** motor on, `DI`, latch PSG R14; skip the spin-up
  transient, measure 16 leader half-periods, set `LOWLIM` = ~1.75× the average
  short half in quarter-count units (the auto-baud calibration). Returns carry=0
  once locked, carry=1 on timeout (no signal). **Proven:** locks onto a real ~2 s
  leader, and **re-locks mid-tape** on real captures (see multi-block note below).
- **Motor-restart robustness (the mid-tape re-lock fix).** When `TAPION` is called
  again for a later block, `STMOTR` restarts the motor and openMSX (like real
  hardware) injects a spin-up transient before the leader is clean: a flat patch,
  one stray ~100-count half, and zero-crossing chatter. A fixed "skip 8 then
  `ret c` on the first timeout" mis-handles this — it either aborts on the flat or
  averages the stray half into `LOWLIM`. The lock therefore (1) skips `CAS_SKIP`
  (=32) edges *tolerating* timeouts to outlast the transient, then (2) sums 16
  leader halves in a loop that **waits out** a flat patch (budgeted retry on
  timeout) rather than failing. The averaging loop is kept lean: its per-half
  overhead must match `TAPIN`'s, or missed edges during a heavier loop bias the
  counts (and `LOWLIM`) low — empirically that pushed the threshold into the
  middle of the 2400-baud leader and made every other byte slip a bit.

### TAPIN — `$00E4` — read one byte
- **In:** none. **Out:** A = byte read; carry set on error (framing/timeout).
- **Side effects:** consumes one framed byte from CAS-in; requires a prior TAPION.
- **C-BIOS today:** stub returns carry=error — **not implemented**.
- **Implemented (`tape.asm`):** hunt forward (16-bit timeout) for the first long half
  = a start bit; consume the start bit; read 8 data bits, classifying each
  half-period against `LOWLIM` (short→`1`, long→`0`) and assembling LSB-first.
  Returns A=byte, carry=0. **Proven:** reads back the exact 6-byte pattern our
  write path recorded.

### TAPIOF — `$00E7` — close read session
- **In/Out:** none documented. **Side effects:** ends the read session; motor off.
- **C-BIOS today:** no-op when motor already off — **correct in isolation**
  (oracle: PPI-C unchanged on both machines). Must still pair correctly after a real
  TAPION.

### TAPOON — `$00EA` — open tape for writing (leader tone)
- **In:** A selects long/short header (long for a new file, short between blocks),
  per TH. **Out:** none documented.
- **Side effects:** motor on; emits the leader tone (~2 s long / shorter re-sync) on
  CAS-out by toggling the PPI bit in a timed loop.
- **C-BIOS today:** **stub** — PPI-C unchanged, no tone (oracle: VG-8020 clears motor
  bit and toggles CAS-out; C-BIOS does neither).
- **Oracle-captured (Phase 1):** with A=`$FF` the VG-8020 returns **carry=0
  (success)** and emits a long continuous ~2400 Hz leader before any data. Exact
  leader-duration-vs-A and per-baud toggle counts are recoverable from the recording
  for the implementer; the round-trip is the acceptance test, not the loop count.
- **Implemented (`tape.asm`):** motor on via `STMOTR`, `DI`, then a continuous
  high-frequency carrier (CAS_LONGLEN/CAS_SHORTLEN cycles per the A selector) driven
  by toggling Port C bit 5 through the i8255 BSR register; returns carry=0.

### TAPOUT — `$00ED` — write one byte
- **In:** A = byte to write. **Out:** carry set on error.
- **Side effects:** emits one framed byte as FSK on CAS-out; requires a prior TAPOON.
- **C-BIOS today:** **stub** — returns carry = `$01` (error), writes nothing; consistent
  with TAPOON never opening the session.
- **Oracle-captured (Phase 1):** the VG-8020 returns **carry=0 (success)** and emits
  each byte as 1200-baud FSK, **LSB-first**, recoverable by `cas_decode.py`. A 6-byte
  pattern (`55 AA 4A 4F 4E 47`) round-tripped exactly.
- **Implemented (`tape.asm`):** frames the byte as start(0)/8-data-LSB-first/2-stop(1),
  each `0` bit one low-freq cycle and each `1` bit two high-freq cycles; returns
  carry=0. The same 6-byte pattern round-trips from our build's recording.

### TAPOOF — `$00F0` — close write session
- **In/Out:** none documented. **Side effects:** flush trailing tone; motor off.
- **C-BIOS today:** no-op when motor already off — **correct in isolation** (oracle:
  PPI-C unchanged). Must pair correctly after a real TAPOON.

### STMOTR — `$00F3` — set motor state
- **In:** A = `0` stop, `1` start, `$FF` reverse (toggle). **Out:** none.
- **Side effects:** drives PPI-C bit 4 (motor relay).
- **C-BIOS today:** **works** — oracle confirms bit 4 cleared on start, delta `$10`
  on both machines. **Reuse as-is**; the other routines call into this for motor
  control.

## Round-trip acceptance criterion

Because the interface is the *signal format*, not any timing-loop count, the
governing test is a **round-trip**: bytes written by `TAPOON`+`TAPOUT` and captured
by openMSX as tape media must decode — via both `TAPION`+`TAPIN` and the independent
host `.cas` codec — back to the identical bytes, at each baud rate. Any timing
constant that achieves this round-trip is acceptable even if quarantined (no exact
source), since the original's loop counts are neither observed nor needed.

**Status: closed (Phase 2).** The full loop now round-trips through our own
clean-room code:
1. **Write** — `TAPOON`/`TAPOUT`/`TAPOOF` produce a recording that the host
   `cas_decode.py` decodes to the exact bytes (`55 AA 4A 4F 4E 47`) at ~2388/1192 Hz
   (oracle: 2393/1213).
2. **Read** — feeding that same recording back as cassette media, `TAPION`+`TAPIN`
   recover the identical bytes (carry=0 throughout), with a realistic ~2 s leader.

Both halves use only public BIOS entry points and a black-box oracle.

**Phase 3 — dual baud (done).** The write path reads the baud from the live work
area: `TAPOON` inspects the active signal-length word (`$F406`) that the system's
`SCREEN ,,,baud` sets (oracle-confirmed — `cas_baud_oracle.py --screen` shows
`SCREEN ,,,1/2` copying `CS120`/`CS240` into the active slots), resolves 1200 vs 2400
(blank/unrecognised → 1200), and caches it for the session; the read path auto-derives
the rate from the leader. The write→read loop closes at **both 1200 and 2400 baud**
over six byte patterns including `00 00 00 00` (all low cycles), `FF FF FF FF`,
walking-ones and alternating bytes. Robustness fix that made 2400 work:
`LOWLIM` is kept in quarter-count units so the discrimination threshold has fractional
precision — at fast bauds the ~1.5× transition artifact and a real ~2× long differ by
only a count or two, and an integer threshold cannot separate them.

**Phase 3 — full file structure (done).** A faithful BSAVE binary file —
header block (`0xD0`×10 + 6-char filename) then data block (start/end/exec LE words
+ payload) — round-trips through the byte-level entry points at **both bauds**. The
block layout itself is assembled by the *caller* (the probe playing BASIC's role),
not by the seven entry points; this test confirms those entry points correctly carry
a real-world file, including the **short header**, a **second block**, and **TAPION
re-locking on the short leader mid-tape after TAPIOF** (the session open/close
pairing). On the audio tape the block boundary is the leader tone — the 8-byte
`1F A6 …` sync exists only in the `.cas` container, not on tape.

**Real-audio validation (first light).** Tested against genuine analog tape
captures (`~/Documents/msx/msx/tapes`, 2400-baud game tapes; catalogued by
[`cassette-tool/cas_identify.py`](../cassette-tool/README.md)):

- ✅ The BIOS read path reads **both blocks of a real capture exactly** at 2400
  baud from real analog audio — header (`EA`×10 + `"hero  "`) *and* the data block
  (`"10 COLOR15…"`), with `TAPION` re-locking mid-tape. Verified byte-for-byte
  against the host decoder on `hero`, `br`, `HSPORT1`/`2` and `ROADF`.
- ✅ **Resolved — mid-tape re-lock.** The second block originally returned garbage
  (the synthetic two-block file round-tripped fine, so it was a real-audio-only
  bug): the motor restart between blocks produces a spin-up transient — a flat
  patch, a stray ~100-count half, and chatter — that the old fixed "skip 8 /
  `ret c`" `TAPION` either timed out on or averaged into `LOWLIM`. Found with the
  `bios_probe_relock.py` diagnostic (dumps each `TAPION`'s `LOWLIM` and the raw
  half-period counts the re-lock lands on). Fixed by skipping the transient and
  waiting out flat patches while measuring (see TAPION above). This is the
  marquee example of validation-hardening: synthetic round-trips could not have
  surfaced it.
- The degradation sweeps (`cassette-tool/`) found the read path **noise-sensitive
  (~0.05 full scale)** — the 1-bit comparator input chatters at zero-crossings.

Remaining: cross-check against an independent host `.cas` codec; the broader
degradation-tolerance envelope in [`feasibility.md`](feasibility.md); and the
host-side `cas_decode`/`cas_identify` limits the full-corpus scan surfaced
(outlier-fragile baud auto-threshold; binary load/exec extraction that assumes
the data block is adjacent to the header — see
[`cassette-tool/README.md`](../cassette-tool/README.md)).

## Provenance log

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Entry points TAPION/TAPIN/TAPIOF | `$00E1`/`$00E4`/`$00E7` | MSX2 Technical Handbook / MSX Assembly Page BIOS call list | sourced |
| Entry points TAPOON/TAPOUT/TAPOOF/STMOTR | `$00EA`/`$00ED`/`$00F0`/`$00F3` | MSX2 Technical Handbook / MSX Assembly Page BIOS call list | sourced |
| Motor relay = PPI-C bit 4, 0=on | bit 4 | MSX Assembly Page i8255 map + STMOTR oracle (delta `$10`) | sourced |
| Motor port (PPI reg C) | `$AA` | MSX Assembly Page PPI map | sourced |
| CAS-in = PSG R14 bit 7 (read via latch `$A0`=14, data `$A2`) | R14 bit 7 | this project's `bios_probe_casin.py` oracle (PPI-B bit7 static; PSG R14 bit7 carries the FSK) + MSX Assembly Page PSG map | sourced — **corrects** an earlier wrong "PPI-B bit 7" note |
| CAS-out bit (PPI reg C) | TBD | MSX Assembly Page PPI map | to confirm |
| Baud rates | 1200 / 2400 | MSX2 Technical Handbook, cassette I/O chapter | sourced |
| VG-8020 default write baud | 1200 (1213/2393 Hz measured) | this project's Phase-1 oracle (`cas_decode.py`) | sourced |
| FSK 0=1 low cycle / 1=2 high cycles | — | MSX2 Technical Handbook + Phase-1 oracle round-trip | sourced |
| Byte framing LSB-first | start/8-LSB/stop | this project's Phase-1 oracle round-trip | sourced |
| Cassette sync header (8 bytes) | `1F A6 DE BA CC 13 7D 74` | MSX2 Technical Handbook (also in BASIC `spec-bload-r.md`) | sourced |
| Binary file-type ID | `0xD0` × 10 | MSX2 Technical Handbook, BSAVE file format | sourced |
| TAPOON A = long/short header | — | MSX2 Technical Handbook, cassette I/O chapter | sourced |
| TAPOUT carry=error semantics | carry on error | MSX2 Technical Handbook + oracle (C-BIOS stub returns `$01`) | sourced |
| Long-header leader = continuous high tone | confirmed | this project's Phase-1 oracle (99.8% short half-periods) | sourced |
| Leader duration / per-baud toggle counts | recoverable from recording | this project's Phase-1 oracle (not yet tabulated) | to tabulate |
| Read leader-detect / phase-lock thresholds | TBD | none yet (Phase 2 oracle) | to capture |
| CAS-out = PPI Port C bit 5, driven via i8255 BSR ($AB ← $0B/$0A) | bit 5 | MSX Assembly Page i8255 map (BSR mode) | sourced |
| Cassette timing work area CS120/CS240/LOW_/HIGH_/HEADER | `$F3FC`–`$F40A` | C-BIOS `src/systemvars.asm` (allowed, BSD-2) | sourced |
| LOWLIM / WINWID read-discrimination windows | `$FCA4` / `$FCA5` | C-BIOS `src/systemvars.asm` (allowed, BSD-2) | sourced |
| Read baud auto-derived from leader (no BAUD input on read) | — | MSX2 Technical Handbook, cassette I/O chapter | sourced |
| Write half-period delay counts (1200 + 2400 baud) | derived, tuned by round-trip | this project (Z80 3.58 MHz clock + documented 1200/2400 Hz) | sourced — round-trips at both rates |
| Write baud read from the active work area | active LOW `$F406` (vs `CS120` `$F3FC` / `CS240` `$F401`) | this project — `TAPOON` resolves the baud from the live table the system's `SCREEN ,,,baud` sets (oracle-confirmed by `cas_baud_oracle.py --screen`), no user flag | sourced |
| `CASBAUD` resolved-baud cache (one write session) | `$FCA5` (WINWID) | this project — derived cache TAPOON writes from the active table; read-side WINWID is idle during a write | quarantined |
| Read discrimination threshold `LOWLIM` in quarter-count units | 1.75× avg short half | this project — derived (long≈2× short, transition artifact≈1.5×) | sourced |

No copied constants. Open items are `to confirm`/`to capture`/`to wire up`, not
`sourced`, and will be filled from allowed sources or oracle round-trip before any
release.

## Determinism

openMSX captures are deterministic per
[`docs/openmsx-harness.md`](https://github.com/andete/msx-preservation/blob/main/docs/openmsx-harness.md); with mounted tape
media the read/write paths run under throttle-off and are expected to reproduce
byte-identically run to run — to be confirmed when Phase 1 capture exists.

## What the implementer must build (summary)

1. **Motor:** implement `STMOTR` (`$00F3`) ourselves — drive PPI Port C bit 4 via
   i8255 BSR (motor on/off = `$08`/`$09`), so the patch depends on no stock-C-BIOS
   routine.
2. **Write FSK:** `TAPOON` leader generator + `TAPOUT` byte framer toggling CAS-out
   at the `BAUD`-selected timing.
3. **Read FSK:** `TAPION` leader-detect/phase-lock + `TAPIN` byte deframer sampling
   CAS-in.
4. **Sessions:** `TAPIOF`/`TAPOOF` close, paired with their open calls.
5. **Errors:** carry-on-error/timeout per the TH contract (TAPOUT already models it).
