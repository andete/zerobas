# D-CASINSETTLE — the tape archive batch, and a probe that printed the refutation of its own finding

*2026-08-31. Closes the last two unverified groups of the archive sweep
(`probes/tape/`, 12; `probes/lib/`, 1) that D-PROBEREACH4 (BASIC) and
D-PROBEREACH5 (disk) left open. Companion to
[spec-probe-reach.md](spec-probe-reach.md).*

## 1. The question, restated

Joost's framing: *a probe that proved a documented fact may be worth keeping as
an archived probe* — but only **if it still runs**, because otherwise the fact
is no longer re-provable. The sweep answers that per probe.

## 2. The first batch asked the wrong question — twice

`archive_batch.py probes/tape 300` returned **10 of 12 non-zero in 0.1 s each**.
Read, not counted: every one was `argparse` refusing a **required argument**
(`--out`, `--corpus`, `--analyze`). That is the probe working, not rot.

The re-run with arguments supplied then returned **`rc=127` in 0 s for all
nine** — `timeout(1)` is not on macOS. An apparatus failure that would have
read, in a table, as nine dead probes. Re-run with the deadline in Python: nine
`rc=0` in 0.1 s.

**And 0.1 s is still the wrong answer**, because these are **cart minters**:
`bios_probe_tapoon.py --out x.rom` writes a Z80 cartridge and stops. The
measurement is the *second* phase — boot the cart under openMSX and read the
result buffer. A bare `rc=0` scores the generator, not the finding.

> 🔴 **THREE TIMES IN ONE SITTING, A TABLE OF PLAUSIBLE EXIT CODES ANSWERED A
> QUESTION NOBODY ASKED.** `rc=2` meant "you forgot a flag", `rc=127` meant
> "your runner is broken", `rc=0` meant "phase one of two succeeded". Only
> reading the OUTPUT, never the code, separated them.

## 3. What was actually measured: seven facts, re-proved on the reference

Minted, booted on the **Philips VG-8020**, result buffer read back, scored
against [tape/docs/spec-cassette.md](../tape/docs/spec-cassette.md):

| probe | measured today | the recorded fact | |
|---|---|---|---|
| `stmotr` | PPI-C `$5A` → `$4A`, delta `$10` | "b4 cleared on start, delta `$10`" | ✅ |
| `tapoon` | PPI-C `$5A` → `$47`, b4 cleared | "clears motor bit" | ✅ |
| `tapiof` | `$5A` → `$5A` | "PPI-C unchanged" | ✅ |
| `tapoof` | `$5A` → `$5A` | "PPI-C unchanged" | ✅ |
| `tapout` | carry byte `$00` | "returns carry=0 (success)" | ✅ |
| `tapfile` | header **and** data byte-identical | "full two-block round-trip" | ✅ |
| `tapraw` | R14 half-periods ~4 (`.cas`) / ~14 (WAV) | 3.5× against the 3744/1200 = 3.1× the two encodings imply | ✅ |

`tapfile` is the flagship: `--write-cas` mints the fixture, `--read` mints the
read cart, `--analyze` scores it — **self-contained**, so it cannot rot on a
missing file. It printed `MATCH -- full two-block file round-trip closed`.

## 4. `bios_probe_casin` printed the opposite of its own finding, and exited 0

The recorded fact ([tape/docs/tape-internals.md:66](../tape/docs/tape-internals.md#L66)):

> PPI-B bit 7 sits *static* while PSG R14 bit 7 carries the FSK transitions.

Re-run today, on a `.cas` **and** on a freshly recorded 1200-baud WAV:

```
PPI Port B $A9 bit7     :   0 transitions, 256/256 high  (static)
PSG R14 bit7            :   0 transitions, 256/256 high  (static)
```

**Both static** — which is not a weaker version of the finding, it is the
*refutation* of it: the probe exists to say which of the two candidates carries
the signal, and it said neither. It exited **0**.

### 4.1 The green control is what convicted it

`bios_probe_tapraw.py`, on the **same WAV, same machine, same sitting**, read
steady ~14-iteration half-periods off PSG R14. So the signal was there, the
tape played, the rig worked. The defect was in `casin` alone.

### 4.2 Two hypotheses refuted before the right one

- **"The settle window is too long"** — shortened `0x4000` → `0x0100`: still
  static. Refuted.
- **"Re-latching R14 inside the sample loop breaks the read"** (`tapraw`
  latches once outside) — hoisted the latch: still static. Refuted.
- **"The settle window is too SHORT"** — `2 × 0xFFFF` (~0.9 s): **23
  transitions, 127/256 high.** The finding, exactly.

openMSX's cassette player needs roughly half an emulated second after motor-on
before signal reaches the port. The shipped settle was ~119 ms and sampled the
silence. `tapraw` never saw this because it **blocks on edges** instead of
counting down — it waits the start-up out for free.

> 🔴 **A COUNTDOWN AND A BLOCKING WAIT ARE NOT TWO SPELLINGS OF "SETTLE".** The
> blocking one is correct by construction; the countdown is a guess about a
> component's start-up latency, and it was wrong by a factor of eight while
> reading like a finished measurement.

## 5. The fix, and why it is two changes and not one

1. **Settle widened** to ~0.9 s, with the three measured points in the comment
   so the next reader does not re-derive them.
2. **`analyze()` now refuses.** If *neither* candidate moves it prints
   `NEITHER candidate carries signal -- NOTHING WAS MEASURED` and returns **2**.

The second is the load-bearing one. Widening the delay fixes today's symptom;
the refusal fixes the *class*. A characterisation printer that can state the
opposite of its subject in the same calm voice as the real answer, and exit 0,
is the [readout blind to its own subject](spec-probe-reach.md) shape — here it
was blind by *agreeing to print anything at all*.

Scored both ways on the same apparatus:

| arm | capture | result |
|---|---|---|
| 🔴 RED | the old both-static capture | `rc=2`, refusal printed |
| 🟢 GREEN | fixed cart, booted end to end | `rc=0`, PPI-B static, R14 23 transitions |

## 6. What is left, named

- **`bios_probe_tapread`** — mints fine; its assertion is against `PATTERN
  55 AA 4A 4F 4E 47`, which only `bios_probe_tapwrite` lays down, and the
  fixture this repo can mint (`tapfile --write-cas`) carries different bytes.
  Pairing the two carts is a job, not a rot.
- **`bios_probe_realtape`** — needs an external tape corpus
  (`--corpus` / `--wav-dir` / `$MSX_TAPE_CORPUS` / `$MSX_TAPE_WAVS`) that is not
  in this repo. Refuses legibly, naming both the flags and the env vars.
- **`probes/lib/probe_cart.py`** — **not a probe**: it mints the sentinel
  cartridge the whole harness rests on, and two documents instruct the reader to
  run it by hand. Nothing to collect because it measures nothing.

Every verdict above is written into
[tools/probe-reach-allow.txt](../tools/probe-reach-allow.txt), so the reason a
probe is kept now names what it re-proved and on what date.

## 7. The lesson, in one line

**An archived probe is only archived if someone ran it — and "it ran" is not
"it still says what the document says it says."**
