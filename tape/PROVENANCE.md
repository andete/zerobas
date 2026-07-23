# Provenance log

Every address, constant, and algorithm in zerobas-tape must appear here with an
independent **allowed** source, or be explicitly **quarantined**. An unexplained
magic value blocks release.

- **sourced** — the value itself is traceable to an allowed source (see
  [`README.md`](README.md) for the list) or to this project's own black-box
  **oracle observation**.
- **quarantined** — **not** "suspect": it means the value is validated by **oracle
  round-trip**, not by a citation, and is **never** lifted from a reference ROM or any
  BIOS disassembly. A timing-loop count cannot be `sourced` even when cleanly derived,
  because a bare count *could* coincide with the original's — so the firewall leans on
  the round-trip guarantee instead. Two sub-reasons appear below:
  - *derivable* — computed from allowed inputs (documented frequency + CPU clock +
    oracle-measured cost); the derivation is supporting evidence, but the count itself
    still carries no citation, hence quarantine. (The four FSK half-period counts.)
  - *our algorithm* — an original routine of ours with no analogue in any reference
    ROM, so no source exists or is possible. (The auto-baud lock, the threshold, the
    leader/flush/dead-tape guards, the baud cache.)

For a cassette signal, a quarantined *timing* constant is acceptable as long as the
resulting **waveform round-trips against the oracle**: the format (frequencies,
framing) is the interface, not the loop-iteration count. The behavioural oracle
observations zerobas-tape is built from are captured in
[`docs/spec-cassette.md`](docs/spec-cassette.md) here, by driving a real MSX /
openMSX as a black box.

## BIOS contract — entry points and conventions

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| TAPION / TAPIN / TAPIOF entry points | `$00E1` / `$00E4` / `$00E7` | MSX Assembly Page BIOS call list; MSX2 Tech Handbook | sourced |
| TAPOON / TAPOUT / TAPOOF entry points | `$00EA` / `$00ED` / `$00F0` | MSX Assembly Page BIOS call list; MSX2 Tech Handbook | sourced |
| STMOTR entry point | `$00F3` | MSX Assembly Page BIOS call list | sourced |
| Failure convention (TAPION/TAPIN/TAPOUT) | CF set = fail | MSX Assembly Page BIOS call list | sourced |
| Register clobber | "Changes: all" | MSX Assembly Page BIOS call list | sourced |
| TAPOON header selector | A=0 short, A≠0 long header | MSX2 Tech Handbook, cassette I/O | sourced |
| STMOTR motor input | A=0 off, A≠0 on | MSX Assembly Page BIOS call list | sourced |
| LPTOUT entry point | `$00A5` | MSX Assembly Page BIOS call list; MSX2 Tech Handbook | sourced |
| LPTOUT input / output | A = char in; CF set = fail | MSX Assembly Page BIOS call list ("Sends one character to printer"; Input A; Output CF on fail) | sourced |
| LPTOUT register clobber | "Changes: F" (A + others preserved) | MSX Assembly Page BIOS call list ("Affected: F") | sourced |
| GTPAD entry point | `$00DB` | MSX Assembly Page BIOS call list; MSX2 Tech Handbook | sourced |
| GTPAD input / output | A = 4·device + sub-function (0..19); out A = `$00`/`$FF` (sense/button) or 0..255 (X/Y) | MSX2 Tech Handbook ch.5 (device-ID table; List 5.8 calling sequence) | sourced |
| GTPDL entry point | `$00DE` | MSX Assembly Page BIOS call list; MSX2 Tech Handbook | sourced |
| GTPDL input / output | A = paddle 1..12; out A = 0..255 dial position | MSX2 Tech Handbook ch.5 §5.3 | sourced |

C-BIOS ships `$00DB`/`$00DE` as debug **stubs** (they `CHPUT` the literal text
"GTPAD"/"GTPDL"), so BASIC `PAD()`/`PDL()` return garbage on the C-BIOS target
until this fills them in — the same "complete a stubbed page-0 vector in the BIOS,
not in `basic.rom`" placement as LPTOUT (decision D-I-6, spec §6.2).

## Printer (Centronics) interface — hardware ports

The LPTOUT routine (`tape.asm`, added as a "select improvement" beyond cassette —
see [`DESIGN.md`](DESIGN.md)) drives the standard MSX printer port. C-BIOS ships
`$00A5` as a stub, so list output (BDOS `$05` LSTOUT, BASIC `LPRINT`) produces
nothing on the C-BIOS target until this fills it in.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Data latch port | `$91` (write, 8-bit) | MSX2 Tech Handbook Ch.5a §4.1 "Printer interface" | sourced |
| Status port | `$90` read, **bit 1** = status, 0 = READY / 1 = BUSY | MSX2 Tech Handbook Ch.5a §4.1 (table: "0: Printer READY / 1: Printer BUSY") | sourced |
| Strobe | `$90` write, **bit 0** = STROBE\*, active-low (assert with 0, release with 1) | MSX2 Tech Handbook Ch.5a §4.1 (table: "STROBE\* (send data when '0')") | sourced |
| On-the-wire per char | READ `$90` → WRITE `$91` → WRITE `$90` `$00` → WRITE `$90` `$FF` | project black-box oracle [`../disk/docs/tier2-lstout-characterisation.md`](../disk/docs/tier2-lstout-characterisation.md) §3.2 (whole-byte `$00`/`$FF` strobe writes), cross-checked against the MSX2 TH spec above | sourced |

## Hardware ports and bit assignments

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| PSG register-select write port | `$A0` (PSG_REGS) | MSX Assembly Page I/O map; AY-3-8910 datasheet | sourced |
| PSG value write port | `$A1` (PSG_WRITE) | MSX Assembly Page I/O map; AY-3-8910 datasheet | sourced |
| PSG value read port | `$A2` (PSG_STAT) | MSX Assembly Page I/O map; AY-3-8910 datasheet | sourced |
| i8255 PPI control (BSR) register | `$AB` (PPI_REGS) | MSX Assembly Page i8255 map; Intel i8255 datasheet | sourced |
| CAS-in line | PSG register 14, bit 7 | MSX2 Tech Handbook (PSG R14/port A); confirmed by oracle (`bios_probe_casin`) | sourced |
| CAS-out line | i8255 Port C bit 5 | MSX Assembly Page i8255 map; MSX2 Tech Handbook | sourced |
| PPI BSR command: Port C bit 5 := 1 / := 0 | `$0B` / `$0A` (CASW_1/CASW_0) | Intel i8255 BSR encoding (bit-set/reset for bit 5) | sourced |
| Motor relay (our own STMOTR) | PPI Port C bit 4 | MSX Assembly Page i8255 map; confirmed by oracle (STMOTR probe) | sourced |
| PPI BSR command: Port C bit 4 := 0 / := 1 (motor on / off) | `$08` / `$09` (MOTOR_ON/MOTOR_OFF) | Intel i8255 BSR encoding (bit-set/reset for bit 4) | sourced |
| i8255 PPI Port C read port (motor toggle read-back) | `$AA` (PPI_PORTC) | MSX Assembly Page i8255 map; Intel i8255 datasheet | sourced |

## Joystick-port analog inputs — GTPDL (paddle) and GTPAD (touch panel)

The two general-I/O ports (PSG registers 14 read / 15 write) carry the joystick
connectors' terminals. GTPDL times a paddle's one-shot; GTPAD clocks a touch
panel's NEC µPD7001 serial ADC. The full characterization record is
[`../scratchpad/i2_input_notes.md`](../scratchpad/i2_input_notes.md); the probes
are `i2_char.py` / `i2_pinmap.py` / `i2_frame.py`.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| R15 b6 selects the connector read on R14 b0..b5 | 0 = interface 1, 1 = interface 2 | MSX2 Tech Handbook ch.5 figs. 5.21/5.22 | sourced |
| R15 b4 / b5 = 8th terminal (pulse/clock out) of interface 1 / 2 | — | MSX2 Tech Handbook ch.5 fig. 5.22 B | sourced |
| R14 b0..b5 = terminals 1,2,3,4,6,7 of the selected interface | — | MSX2 Tech Handbook ch.5 | sourced |
| Paddle = a one-shot on terminal 1, pulsed via the 8th terminal, ~10 µs..3 ms | ⇒ ~11.8 µs/count (3 ms/255), cap 255 | MSX2 Tech Handbook ch.5 §5.3 fig. 5.24 | sourced |
| PDL index → interface / terminal | odd `n` = if 1, even = if 2; paddle `(n+1)>>1` = R14 bit `((n+1)>>1)−1` | MSX2 TH published circuit **and** our black-box mirror test (i2_input_notes.md §2, settled twice) | sourced |
| Paddle trigger edge / count polarity / 36 T loop period | 8th-terminal HIGH→LOW edge triggers; data terminal held high for the dial-proportional window; count while high, 36 T/iter lands centred paddle on 128 | project black-box oracle (openMSX device, `paddle_probe`/`win_probe`); **pinned by the Phase D differential** (idle 255, centred 128) | quarantined |
| Touch panel interface chip | NEC µPD7001 4-channel 8-bit serial ADC | 1982 NEC Microcomputer Catalog pp.479–482 (`7001DS-REV 2-1-82-CAT`), bitsavers scan; a **manufacturer** data book | sourced |
| µPD7001 serial protocol | 2 addr bits on SI latched by DL; conversion at CS rise; 8 result bits MSB-first on open-drain SO clocked by SCK; EOC low during conversion | µPD7001 datasheet (above) | sourced |
| Touch-panel terminal mapping | 8th terminal (R15 b4/b5) = CS/SCK; terminal 3 (R14 b2) = SO; terminal 1 (R14 b0) = contact line, active low | project black-box oracle (i2_input_notes.md §4.5/4.6; paddle run first as a known-answer control) | quarantined |
| µPD7001 channel address (X = ch 0, Y = ch 3) — the ADDRESS PHASE | **omitted (documented deviation, D-I-7):** the two channel bits through the port's single output line were never pinnable by the oracle, so X and Y run the same read frame | µPD7001 datasheet gives the channels; the joyport encoding is unrecoverable under our oracle (i2_input_notes.md §4.6) | quarantined |
| GTPAD X/Y contact-gating / latch behaviour | sense latches X/Y only when contacted; empty port 2 X/Y still read the last contacted value in an in-order sweep | **pinned by the Phase E differential** (arkanoidpad in port A / B); reproduced bit-for-bit (user's call: bug-for-bug where achievable) | quarantined |

## Cassette format (the signal)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| FSK bit encoding | '0' = 1 low-freq cycle, '1' = 2 high-freq cycles | MSX2 Tech Handbook, cassette I/O | sourced |
| Tone frequencies (1200 baud) | ~1200 Hz low / ~2400 Hz high | MSX2 Tech Handbook, cassette I/O | sourced |
| Tone frequencies (2400 baud) | one octave up (~2400 / ~4800 Hz) | MSX2 Tech Handbook, cassette I/O | sourced |
| Leader tone | continuous high-frequency carrier | MSX2 Tech Handbook, cassette I/O | sourced |
| Byte framing | start bit (0), 8 data LSB-first, stop bit(s) (1) | MSX2 Tech Handbook, cassette I/O | sourced |

## Work area (system variables)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| LOWLIM (read discrimination threshold) | `$FCA4` | MSX Assembly Page sysvar map; MSX2 Tech Handbook | sourced |
| WINWID (read window width) | `$FCA5` | MSX Assembly Page sysvar map; MSX2 Tech Handbook; C-BIOS `systemvars.asm` | sourced |
| PADY / PADX (touch-panel latched Y / X, written by GTPAD sense, read by its X/Y sub-calls) | `$FC9C` / `$FC9D` | C-BIOS `systemvars.asm` ("FC9C last read Y-position of a touchpad", "FC9D last read X"); the standard MSX GTPAD work bytes | sourced |
| CS120 (1200-baud reference signal lengths) | `$F3FC` | C-BIOS `systemvars.asm`; corroborated by boot-state oracle dump | sourced |
| CS240 (2400-baud reference signal lengths) | `$F401` | C-BIOS `systemvars.asm`; corroborated by boot-state oracle dump | sourced |
| Active LOW signal length (the live baud) | `$F406` | C-BIOS `systemvars.asm`; oracle confirmed `SCREEN ,,,baud` copies CS120/CS240 here | sourced |
| CASBAUD (our resolved-baud cache for one write) | parked on `WINWID` `$FCA5` | our own derived cache (not a selector): TAPOON resolves the baud from the active table each session and stores it; `$FCA5` is a read-side sysvar **oracle-confirmed idle during a write** — the `winwid_idle` probe (`probes/tape/bios_probe_winwid_idle.py`) sets openMSX `write_mem`+`read_mem` watchpoints on `$FCA5` across a full TAPOON+TAPOUT+TAPOOF session and measures **0 hits** on the VG-8020 oracle at both 1200 and 2400 baud (`--self-test` confirms the watchpoints catch a deliberate access, so the clean reading is not a blind instrument) | quarantined |

> **Baud selection — now read from the live work area (steps A and B done).**
>
> *Solid* (C-BIOS `systemvars.asm`, an allowed source — corroborated by a
> deterministic boot-state RAM dump of the VG-8020, which needs no keyboard input):
> the cassette **write**-timing work area is `CS120` `$F3FC` (1200-baud signal
> lengths), `CS240` `$F401` (2400-baud), the **active** `LOW` `$F406` / `HIGH`
> `$F408`, and `HEADER` `$F40A`. At boot the active `LOW`/`HIGH`/`HEADER` hold the
> 1200 values (a copy of `CS120`). Our original 0/1 selector sat on `$F3FC` — i.e.
> it **stomped the live `CS120` table**. That was the confirmed bug.
>
> **How the system records the baud (resolved).** Verified on the VG-8020 as a
> black box (`SCREEN ,,,N` typed as one keystroke with a real Enter, gated on a
> sentinel POKE that proves the line ran — see `cas_baud_oracle.py --screen`):
> `SCREEN ,,,1` leaves the active `LOW` word at `53 5C` (a copy of `CS120`),
> `SCREEN ,,,2` sets it to `25 2D` (`CS240`). So the **active `LOW` word is the
> live baud indicator**; the system copies the chosen reference table into the
> active slots. The candidate baud byte `CONLO` `$F66A` is *not* it — it reads the
> same after either `SCREEN` baud (generic BASIC scratch). (The earlier "flaky
> keyboard" was a CR-escaping bug in the harness invocation, not the emulator.)
>
> **A (done):** stopped colliding with the write tables.
>
> **B (done):** `TAPOON` now reads the active `LOW` word (`cas_baud`) and resolves
> the baud — `25 2D` ⇒ 2400, a `CS120` match / unrecognised / blank ⇒ the
> MSX-standard 1200 — then caches the result in `CASBAUD` for `TAPOUT`/`TAPOOF` to
> read cheaply (a per-byte table compare stretched the inter-cycle gap and
> desynced 2400 framing). No user-set flag: the system's `SCREEN` choice is
> honoured. Validated end-to-end — full two-block file round-trips at both bauds,
> tones measured at 2387/1169 Hz (1200) vs 4638/2210 Hz (2400), and a blank work
> area correctly defaults to 1200. Probe: `cas_baud_oracle`
> (`probes/tape/cas_baud_oracle.py`).

## v0.29 ROM layout facts

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Free page-0 ROM origin for our code | `$09EE` | C-BIOS v0.29 build — `0x00` fill in ALL main variants (was `$3A72` until the 2026-07-11 D5 revision) | sourced |
| Page-0 size limit | code must end `< $4000` | MSX2 Tech Handbook, memory map (page 1 paged out) | sourced |

## Timing and algorithm constants (derived; round-trip justified)

These are loop-iteration counts and thresholds, **not** copied from any ROM. Each is
derived from the documented FSK frequencies and the 3.58 MHz Z80 clock, then tuned
until the recording round-trips through the host decoder and against the oracle.

| Item | Value | Basis | Status |
|------|-------|-------|--------|
| CAS_HHALF / CAS_LHALF (1200 baud half-period counts) | 50 / 102 | *derivable:* invert the documented 2400/1200 Hz tones through the half-period cost, `C = round((3579545/(2·f) − 26)/14.4)` ⇒ 49.98→50, 101.77→102. Inputs are all allowed: documented FSK freqs (Tech Handbook), the 3.58 MHz Z80 clock (hardware), and the `26 + 14.4·C` per-half cost measured from openMSX as a **black box** (oracle, not a ROM listing). Confirmed by round-trip | quarantined |
| CAS_HHALF24 / CAS_LHALF24 (2400 baud) | 24 / 50 | *derivable:* same derivation one octave up (4800/2400 Hz) ⇒ 24.09→24, 49.98→50; 2400's low tone = 1200's high tone, so CAS_LHALF24 == CAS_HHALF | quarantined |
| CAS_LONGLEN / CAS_SHORTLEN (leader cycles) | 4000 / 2000 | *our algorithm:* our own choice, order of magnitude from the documented ~2 s leader (4000 carrier cycles ≈ 1.7 s at 2400 Hz; short = half, for between-blocks re-sync). The exact count is deliberately *not* the original's HEADER value — long enough to lock, confirmed by round-trip | quarantined |
| CAS_SKIP / CAS_RUNLEN (auto-baud window) | 32 / 16 | *our algorithm:* lock window with no original analogue — the reference reads a fixed baud from a sysvar, it does not measure the leader. Skip the motor-restart spin-up transient, then average 16 clean leader halves. Validated by round-trip | quarantined |
| CAS_FLATMAX (leading-silence timeout budget) | 1500 | *our algorithm:* dead-tape guard — flat-timeout iterations (~3 ms each) tolerated before the first edge; ~1500 covers ~5 s, covering openMSX's ~2 s `LONG_SILENCE` pre-leader gap with margin, and only spent while the signal is absent | quarantined |
| CAS_FLUSHLEN (TAPOOF trailing carrier) | 32 | *our algorithm:* write-tail length — short high-freq carrier flushed after the last byte so the final stop bits clear the decoder; chosen long enough to register, short enough to not bloat the tail | quarantined |
| LOWLIM derivation | 1.75 × avg-short, in quarter-count units | *our algorithm:* discrimination threshold paired with the auto-baud lock above (the reference has no measured threshold) — a real long half is ~2×, the leader→data transition half ~1.5×, so 1.75× rejects the artifact with symmetric margin. Validated by round-trip | quarantined |
| CASIN_R14 | 14 | PSG register number carrying CAS-in (see hardware table) | sourced |

## Audit

Before release, every constant and table in [`tape.asm`](tape.asm) must map
to a `sourced` row above or be `quarantined` with a round-trip justification. The
quarantined rows split into two kinds, **neither copied from a reference ROM**:

- **derived** — the four FSK half-period counts, *computed* by inverting the
  documented tone frequencies through the openMSX-measured half-period cost (see the
  `CAS_HHALF` rows). The inputs are all allowed (documented frequency + hardware clock
  + black-box oracle timing); the count is an arithmetic consequence, not a lifted
  value. Formally quarantined only because a timing-loop count *could* coincide with
  the original — and confirmed by round-trip regardless.
- **our algorithm** — the auto-baud lock window (`CAS_SKIP`/`CAS_RUNLEN`), the
  `LOWLIM` discrimination threshold, the leader/flush/dead-tape guards
  (`CAS_LONGLEN`/`CAS_SHORTLEN`/`CAS_FLUSHLEN`/`CAS_FLATMAX`), and the `CASBAUD` cache
  placement. These have *no* original analogue (the reference reads a fixed baud from
  a sysvar and never measures the leader), so no source exists or is possible; each is
  validated by the cassette signal round-tripping byte-for-byte against the oracle
  (both bauds; real analog captures).

No stock-C-BIOS code is carried, and (now that the motor routine is our own) the patch
calls into none: the sole remaining C-BIOS-specific *address* is the free-ROM origin
(`$09EE`; `$3A72` before the 2026-07-11 D5 revision), from C-BIOS's own BSD-2 source.
