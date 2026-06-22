# How MSX cassette I/O works — an internals reference

*What the MSX tape subsystem actually does, as learned by reimplementing it
clean-room for C-BIOS.* This is the synthesis document: it pulls the scattered
findings of the zerobas-tape effort — the per-call contracts in
[`spec-cassette.md`](spec-cassette.md), the sourcing in [`PROVENANCE.md`](../PROVENANCE.md),
and the upstream oracle work in
[andete/msx-preservation](https://github.com/andete/msx-preservation) — into one
narrative of how the hardware, the signal, and the seven BIOS routines fit
together.

It is written for someone who wants to *understand* MSX cassette I/O, not just
build the patch. For the build-and-audit view, read the two documents above.

> **Provenance firewall — read this first.** This reference is a *spec-author*
> artefact under [`clean-room-policy.md`](clean-room-policy.md). Everything here is
> derived **only** from allowed public sources (MSX2 Technical Handbook, MSX
> Assembly Page, the i8255/AY-3-8910 datasheets, C-BIOS's own BSD-2 source, and the
> GPL openMSX source) **plus this project's own black-box oracle observations**. It
> deliberately contains **no** knowledge that could only come from reading a
> reference BIOS ROM or any disassembly — including the cassette routines of the
> Philips VG-8020 used as the oracle. Where a value can only be known by measuring
> (timing-loop counts, leader length), it is marked *quarantined* and traced to a
> round-trip, never to a citation. If you extend this doc, keep it black-box: a
> behavioural difference is a *bug report to resolve from an allowed source*, never
> a reason to read the original.

---

## 1. The shape of the problem

Cassette tape was a primary load medium for early MSX1 software. The MSX BIOS
exposes the whole subsystem through **seven entry points** in page 0, and the
machine's data layer (Disk-BASIC's `CLOAD`/`CSAVE`/`BLOAD"CAS:"`) is built
entirely on top of them. C-BIOS — the free, clean-room MSX BIOS — ships these
seven as **stubs**: the motor relay and the session-terminate calls do something
plausible, but the read calls block forever and the write calls are no-ops. So on
C-BIOS, tape simply does not work.

zerobas-tape fills exactly that gap: a tiny binary patch into spare page-0 ROM
that supplies the missing **signal layer** — turning bytes into the audio
waveform a cassette recorder expects, and turning that waveform back into bytes.
Understanding the subsystem means understanding three stacked things:

1. the **hardware lines** the CPU toggles and samples,
2. the **signal format** (FSK) those lines carry, and
3. the **seven routines** that compose those into read and write *sessions*.

The rest of this document walks up that stack.

---

## 2. The hardware model

The CPU never touches a "tape" peripheral directly. It drives two single-bit
lines on two different chips, in real time, with interrupts disabled:

| Line | Chip / register | How accessed | Direction | Role |
|------|-----------------|--------------|-----------|------|
| **CAS-out** (write) | i8255 PPI, Port C **bit 5** | BSR command to control port `$AB` (`$0B`=set, `$0A`=reset) | out | the recording signal — toggled to synthesise the audio tone |
| **CAS-in** (read) | AY-3-8910 PSG, **register 14 bit 7** | latch reg 14 via `$A0`, read value via `$A2` | in | the playback signal — sampled to recover the tone |
| **Motor relay** | i8255 PPI, Port C **bit 4** | BSR command to `$AB` (`$08`=on/clear, `$09`=off/set) | out | starts/stops the cassette motor (0 = on) |

Two facts here were *not* obvious from the documentation and had to be pinned by
the oracle:

- **CAS-in lives on the PSG, not the PPI.** An early note had it as "PPI Port B
  bit 7"; the `bios_probe_casin.py` probe showed PPI-B bit 7 sits *static* while
  PSG R14 bit 7 carries the FSK transitions. The corrected reading is in the
  [provenance log](spec-cassette.md#provenance-log).
- **The write line is driven through the i8255's BSR mode**, not a read-modify-write
  of the port. A single `OUT ($AB),$0B`/`$0A` flips Port C bit 5 atomically — which
  matters because the toggle loop's timing *is* the signal frequency.

The motor relay is the one piece C-BIOS got right, and the only routine the oracle
confirmed working on a stock stub (`STMOTR` clears bit 4; the probe saw a `$10`
delta on Port C). zerobas-tape nonetheless reimplements it, so the patch depends on
*no* stock-C-BIOS routine.

---

## 3. The signal: frequency-shift keying

Tape audio is **FSK** — two tones, distinguished only by frequency:

- a **`0` bit** is one cycle of the **low** tone, and
- a **`1` bit** is two cycles of the **high** tone.

The high tone is exactly twice the low tone, so a `1` and a `0` take the *same
wall-clock time* — the bit rate is constant regardless of the data. At the
standard **1200 baud**, that is ~1200 Hz (low) / ~2400 Hz (high); at **2400 baud**
everything shifts up an octave (~2400 / ~4800 Hz), so 2400 baud's low tone is the
same pitch as 1200 baud's high tone. The oracle measured a real VG-8020 writing its
default at **1213 Hz / 2393 Hz** — i.e. genuinely 1200 baud.

Because the line is a single bit, the decoder never sees "a tone" — it sees a
stream of **edges** and measures the **half-period** between them. A short half =
high tone = part of a `1`; a long half (≈2× the short) = low tone = a `0`. The
whole read path is half-period arithmetic.

### Why half-period counts are *derived*, not copied

The write path needs to know how many CPU cycles to wait between toggles to hit
1200/2400 Hz. Those loop counts are computed, not lifted: invert the documented
tone frequency through the measured per-half cost,
`C = round((3579545 / (2·f) − 26) / 14.4)`, where 3.58 MHz is the Z80 clock
(hardware), the frequency is documented (Tech Handbook), and the `26 + 14.4·C`
per-half cost was measured from openMSX **as a black box**. That yields the
constants `CAS_HHALF=50 / CAS_LHALF=102` (1200) and `24 / 50` (2400). They are
[*quarantined*](../PROVENANCE.md#timing-and-algorithm-constants-derived-round-trip-justified):
all inputs are allowed, but a bare loop count *could* coincide with the original's,
so the firewall leans on the round-trip guarantee rather than a citation.

---

## 4. Byte and block framing

On top of the bit encoding sits a simple asynchronous frame, and on top of *that*,
a block structure:

- **Byte frame:** one **start bit (0)**, **8 data bits LSB-first**, one or more
  **stop bits (1)**. The oracle confirmed the bit order by round-trip — decoding a
  written byte as start/8-LSB/stop recovered it exactly.
- **Leader:** before a block, a continuous run of the **high** tone (~2 s at the
  start of a file) lets the reader lock onto the signal; a shorter re-sync leader
  separates the header block from the data block. The oracle saw the long leader as
  99.8% short half-periods — i.e. an unbroken high carrier.
- **Block layout:** a **header block** (a file-type marker `0xD0`×10 for a binary
  `BSAVE` file, plus a 6-character filename) followed by a **data block** (start /
  end / exec little-endian addresses, then the payload). This layer is assembled by
  the *caller* — BASIC, or a probe playing BASIC's role — not by the seven entry
  points; the byte-level routines just carry whatever bytes they are handed. The
  block format itself is characterised in the BASIC project's
  [`spec-bload-r.md`](https://github.com/andete/msx-preservation/blob/main/basic-spec/docs/spec-bload-r.md).

> **A container vs. tape gotcha.** The 8-byte sync sequence `1F A6 DE BA CC 13 7D 74`
> that appears in MSX `.cas` *files* is a property of the **container format**, not
> of the audio. On real tape, the block boundary is the **leader tone**; there is no
> `1F A6 …` on the wire. Tools that read `.cas` blobs key off those bytes; tools that
> read the analog signal must key off the leader. Conflating the two is a classic
> source of "works on `.cas`, fails on `.wav`" bugs.

---

## 5. The seven entry points as a system

The routines come in two trios plus the shared motor call. Each trio is an
**open → transfer → close** session:

```
WRITE:  TAPOON ($00EA) ──▶ TAPOUT ($00ED) ×N ──▶ TAPOOF ($00F0)
READ:   TAPION ($00E1) ──▶ TAPIN  ($00E4) ×N ──▶ TAPIOF ($00E7)
shared: STMOTR ($00F3)  — motor on/off, called by both
```

The error convention throughout is **carry set = failure** (no leader found,
framing error, timeout). Registers are documented as "changes: all".

### Write session

- **`TAPOON` — open for writing.** Motor on, then emit the leader carrier. `A`
  selects a **long** header (new file) or **short** header (re-sync between blocks).
  zerobas-tape drives the high-frequency carrier for `CAS_LONGLEN`/`CAS_SHORTLEN`
  (4000/2000) cycles by toggling Port C bit 5 through the BSR register.
- **`TAPOUT` — write one byte.** Frame `A` as start(0) / 8 data LSB-first / stop(1)
  and emit it as FSK — each `0` one low-tone cycle, each `1` two high-tone cycles.
- **`TAPOOF` — close.** Flush a short trailing carrier (`CAS_FLUSHLEN`=32 cycles) so
  the final stop bits clear the decoder, then motor off.

### Read session

- **`TAPIN` — read one byte.** Hunt forward for the first long half (a start bit),
  consume it, then classify 8 data half-periods against the threshold (short→`1`,
  long→`0`) and assemble LSB-first.
- **`TAPIOF` — close.** End the session, motor off. (C-BIOS's stub is a correct
  no-op *in isolation* — but it must still pair after a real `TAPION`.)

**`TAPION` — open for reading — is where the cleverness lives**, so it gets its own
section.

---

## 6. The read path's hard parts (the empirical layer)

Writing tape is timed output — once the half-period counts are right, it just
works. **Reading** tape is where the real engineering — and the parts with *no
analogue in any reference ROM* — concentrate. These are this project's own
algorithms, validated by signal round-trip, not by any citation.

### Auto-baud: TAPION measures, it doesn't select

The documented design has the *write* side pick a baud (the system copies a
1200- or 2400-baud reference table into the active work area). But the **read side
is never told the rate**. The insight that shaped the whole read path: `TAPION`
*measures* the leader tone's half-period and from it computes the discrimination
threshold (`LOWLIM` `$FCA4`) that `TAPIN` uses to separate `0` cycles from `1`
cycles. **`TAPION` is the per-tape calibration step**, not merely a "wait for tone"
gate.

This is why the design generalises for free: a tape written at *any* rate reads back
without the user specifying it. The same property is what let the read path later
extend to openMSX's **3744-baud `.cas`** synthesis — a rate neither standard nor
selectable — purely by widening the discrimination range, with no new "mode". (That
saga is documented upstream:
[`finding-openmsx-cas-3744-baud.md`](https://github.com/andete/msx-preservation/blob/main/basic-spec/docs/finding-openmsx-cas-3744-baud.md).)

### The threshold needs fractional precision

A real long half is ~2× a short one; the artifact half at the leader→data
transition is ~1.5×. To reject the artifact with symmetric margin, `LOWLIM` is set
to **1.75× the average short half**. At fast bauds those two differ by only a count
or two, so the threshold is kept in **quarter-count units** — an integer threshold
cannot separate them, and that single change is what made 2400 baud work.

### The mid-tape re-lock bug (the marquee validation lesson)

A synthetic two-block file round-tripped fine, yet real analog captures returned
**garbage on the second block**. The cause: when `TAPION` is called again for a
later block, the motor restarts, and real hardware (faithfully reproduced by
openMSX) injects a **spin-up transient** before the leader is clean — a flat patch,
a stray ~100-count half, and zero-crossing chatter. A naive "skip 8 edges, then fail
on the first timeout" lock either aborted on the flat patch or averaged the stray
half into `LOWLIM`, poisoning the threshold.

The fix: (1) skip `CAS_SKIP`=32 edges *tolerating* timeouts to outlast the
transient, then (2) average `CAS_RUNLEN`=16 clean leader halves in a loop that
**waits out** flat patches rather than failing. A subtle constraint fell out of
this: the averaging loop's per-half overhead must **match `TAPIN`'s**, or missed
edges during a heavier loop bias the counts (and `LOWLIM`) low.

This bug is the single best argument for the project's validation discipline:
**synthetic round-trips could not have surfaced it.** It took a real cassette
capture and a diagnostic (`bios_probe_relock.py`) that dumps each `TAPION`'s
`LOWLIM` and the raw half-period counts to find and fix.

### Where the baud actually comes from (write side)

For *writing*, the rate is not a flag — `TAPOON` reads the **live work area**. The
system's `SCREEN ,,,baud` BASIC command copies the 1200-baud (`CS120` `$F3FC`) or
2400-baud (`CS240` `$F401`) reference table into the **active** `LOW` signal-length
word (`$F406`). `TAPOON` inspects that active word (`25 2D` ⇒ 2400; a `CS120` match,
blank, or anything unrecognised ⇒ the MSX-standard 1200) and caches the result for
the session. This was oracle-confirmed by typing `SCREEN ,,,N` as a black box and
dumping the work area (`cas_baud_oracle.py --screen`) — and it fixed a real bug,
where an earlier 0/1 selector sat on `$F3FC` and **stomped the live `CS120` table**.

---

## 7. The validation methodology — oracle, not answer key

None of the above could be sourced from a citation, because timing-critical signal
code is exactly the kind of thing the documentation describes only loosely. The
project's answer is a **black-box oracle**:

- **The reference (a real Philips VG-8020, or openMSX running its ROM) is used only
  as a black box** — known bytes in, observed edges/bytes out. A behavioural
  difference is a *bug report*, resolved from an allowed source, never by reading the
  original's code. This is the "oracle, not answer key" rule, extended to tape from
  [`openmsx-harness.md`](https://github.com/andete/msx-preservation/blob/main/docs/openmsx-harness.md).
- **The governing acceptance test is a round-trip.** Because the *signal format* is
  the interface — not any loop count — bytes written by `TAPOON`/`TAPOUT` and
  recorded by openMSX as tape media must decode back to the identical bytes, via
  *both* the BIOS read path (`TAPION`/`TAPIN`) and an **independent host `.cas`
  codec** (`cas_decode.py`), at every baud rate. Any quarantined timing constant that
  achieves this round-trip is acceptable.
- **A two-role split** keeps the firewall intact even when one person does the work:
  the *spec author* observes only oracle outputs and writes from allowed sources; the
  *implementer* writes Z80 from the spec and failing tests, and never sees the
  reference ROM's bytes.

The full loop is closed: a clean-room write produces a recording the host codec
decodes exactly, and feeding that recording back as tape media, the clean-room read
path recovers the identical bytes — at **both 1200 and 2400 baud**, over six byte
patterns (`00`, `FF`, walking-ones, alternating), and including a faithful two-block
`BSAVE` file with a short header and mid-tape re-lock. It has been validated against
**genuine analog game-tape captures** (`hero`, `br`, `HSPORT1/2`, `ROADF`) read
byte-for-byte at 2400 baud. The known soft spot is noise: the 1-bit comparator input
chatters at zero-crossings (sensitive at ~0.05 full scale).

The regression net that guards all of this lives upstream as three tiers
(deterministic / `.cas` corpus / analog `.wav`):
[`tape-regression.md`](https://github.com/andete/msx-preservation/blob/main/docs/tape-regression.md).

---

## 8. Where to go next

| You want… | Read |
|-----------|------|
| The per-entry-point contracts (registers, side effects, error semantics) | [`spec-cassette.md`](spec-cassette.md) |
| Every constant traced to a source, or quarantined with justification | [`PROVENANCE.md`](../PROVENANCE.md) |
| Why this is legally and technically feasible, and how it was staged | [`feasibility.md`](feasibility.md) |
| The clean-room firewall rules in full | [`clean-room-policy.md`](clean-room-policy.md) |
| The host-side `.cas`/`.wav` tooling | [`cassette-tool/README.md`](../cassette-tool/README.md) |
| The deterministic openMSX harness | [openmsx-harness.md](https://github.com/andete/msx-preservation/blob/main/docs/openmsx-harness.md) |
| The 3744-baud read-margin saga | [finding-openmsx-cas-3744-baud.md](https://github.com/andete/msx-preservation/blob/main/basic-spec/docs/finding-openmsx-cas-3744-baud.md) |
| The regression suite (three tiers) | [tape-regression.md](https://github.com/andete/msx-preservation/blob/main/docs/tape-regression.md) |
