<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-LINEMAX — the input line and the crunched line

Behavioural spec. Measurement:
[`linemax-vg8020-characterization.md`](linemax-vg8020-characterization.md).
Split out of D-ARR-C ([`spec-basic-arrdim-c.md`](spec-basic-arrdim-c.md)), which
measured the input-line divergence and could not reach it.

**Status: awaiting sign-off. No code written.**

---

## 1. What the measurement changed about the item

The item was filed as one constant: `LINEMAX = 96` against a reference that takes
more. That is real, and it is the smaller half.

| | reference | zerobas | disposition |
|---|---|---|---|
| input line | 254 chars | 95 | **agree**: both drop the tail, keep and store the line, raise nothing |
| crunched line | ≤ 314 body bytes, then `Line buffer overflow` (ERR 25) | **no bound at all** | **diverge** |

The crunch half is a **live memory-corruption defect at today's `LINEMAX`**,
reachable from a **27-character line**, and it is what actually sizes the buffers
this slice has to re-home. §2.1 of the characterization shows it is fatal: after
the overrun zerobas cannot execute `B=7`.

So this spec has two deliverables, and the second is the load-bearing one.

---

## 2. Behaviour to implement

### R-1 — the input line takes 254 characters

`LINEMAX` becomes **255** (254 characters + the 0 terminator), matching the
measured reference ceiling. Both readers are unchanged in *shape*:
[`repl.asm:75`](../basic/repl.asm:75) and
[`files.asm:1461`](../basic/files.asm:1461) keep
`cp (LINEBUF+LINEMAX-1) & $FF`.

**The one-page trick survives and is not the obstacle the item assumed.** That
compare, and `read_line`'s backspace `cp LINEBUF & $FF`, and console INPUT's
`ld h,high LINEBUF` ([`input.asm:239`](../basic/input.asm:239)/[`:258`](../basic/input.asm:258)),
are all correct for **any** `LINEBUF` at a page base with `LINEMAX ≤ 256`.
`$BB00 + 254 = $BBFE` is one page. The constraint is *page-aligned base, ≤ 256
bytes* — not ≤ 96. No reader logic changes.

Truncation semantics are **already correct** and must not change: characters past
the ceiling are dropped, the line is kept and stored, nothing is raised.

### R-2 — the crunch is bounded, and overflow raises ERR 25

The tokeniser must refuse a line whose crunched body would exceed **314 bytes**,
raising the reference's `Line buffer overflow` — **ERR 25**, measured — and
storing/executing nothing. `TOKBUF` is sized **315** bytes (314 + terminator).

* Message wording: `Line buffer overflow` (measured verbatim from the screen).
* `err_msgtab` ([`interp.asm:940`](../basic/interp.asm:940)) currently ends at 24;
  it gains entry 25, and `raise_error`'s range test moves `cp 24` → `cp 25` —
  the same two-places-one-fact pair the ERR-24 entry already noted.
* The refusal happens at line **entry**, like the existing `TKOVF` float-overflow
  reject ([`program.asm`](../basic/program.asm) `dl_overflow`), which is the
  established precedent for "crunch failed, never execute or store".

**Where the check goes.** Bounding every emit site in
[`tokenise.inc`](../basic/tokenise.inc) is expensive and easy to miss one. A
single test at the top of `tk_loop` is enough if the buffer carries slack for the
largest single emission — a double literal is 9 bytes
([`sysvars.inc:288`](../basic/sysvars.inc:288)), the largest of any one step — so
one compare per source character, with 9 bytes of headroom, covers every path.
The tokeniser body is a sub-ROM tenant in the repack build, which is *not* the
tight wall.

### R-3 — the ASCII-LOAD path comes along for free

`ascii_read_lines` shares the constant and the idiom, and §3 of the
characterization measures that both machines' ASCII paths already share their own
typed ceilings. Raising `LINEMAX` fixes it with no separate change; the `cas`
battery gates that it stays true.

---

## 3. The RAM move

`TOKBUF` is the blocker, not `LINEBUF`. It sits at `$E160` — **inside** a widened
`LINEBUF`'s span — and is live *simultaneously* with it (the crunch reads one and
writes the other). Both must move.

Page `$E0`–`$F3` is dense from `$E010` to `$F3FC`; there is no 570-byte hole.

**Proposed home: a page-2 window below `DETOKBUF`**, lowering `TXTMAX` from
`$BE00` to `$BB00` ([`sysvars.inc:1492`](../basic/sysvars.inc:1492)) — the same
move already made once for `DETOKBUF`:

| | address | size |
|---|---|---|
| `TOKBUF` | `$BB00..$BC3A` | 315 |
| *(spare)* | `$BC3B..$BCFF` | 197 |
| `LINEBUF` | `$BD00..$BDFE` | 255, page-aligned |
| `DETOKBUF` | `$BE00` | unchanged |

**Page 2 is safe during the crunch.** The tokeniser runs as a page-0 sub-ROM
tenant via `subrom_call`, whose contract is args "marshalled in **page-2/3 RAM**
by the caller" ([`subromcall.asm:34`](../basic/subromcall.asm:34)); `CALSLT`
switches page 0 only, and `sub/detok.asm` already fills `DETOKBUF` at `$BE00`
from a tenant. This was the item's stated risk and it does not hold.

**Cost: 768 bytes of BASIC program space** (`TXTBASE $8001..TXTMAX`: 15871 →
15103, −4.8%). This is a RAM-map cost, **not** a ROM-wall cost — the low region
(32 B free) and page 1 (10 B free) are not where this is paid. A real MSX pays the
same way: its own line buffers live in its system area and come off the same
pool.

**Freed:** `$E158..$E1BF` (104 B of page-3 RAM) once both buffers leave. Note it;
do not spend it in this slice.

### 3.1 The G3/G4/G5 aliasing argument is retired, not re-proved

`GFX_X1..GFX_CPHASE` (`$E100..$E157`) are homed on the documented argument that
`LINEBUF` is dead during any graphics statement
([`sysvars.inc:575`](../basic/sysvars.inc:575)). With `LINEBUF` gone from page 3
those cells stop aliasing anything and simply own free RAM — the argument becomes
unnecessary rather than weaker. **The comments that state it must be updated**, or
a later reader will re-derive a constraint that no longer exists.

---

## 4. Open questions for sign-off

**Q1 — the lean build. ANSWERED: the lean cart is RETIRED** (user, 2026-07-29).

The route here is worth recording, because both intermediate positions were wrong.
I first proposed repack-only on the reasoning that the lean cart has no float pack
and so cannot expand; §2.2 falsified that by measurement (line-number references
expand 2:1 in an `ON..GOTO` list — a **57-character line** overruns lean's
`TOKBUF`, and a variable set before it reads back `0`). That made "fix both
builds" correct — until the prior question was asked: whether a 16 KB cart with no
strings, floats, arrays, `INPUT` or error codes, and 68 free bytes, is a target at
all. It is not.

So this slice is **repack-only after all**, but because the other build is going
away rather than because it was safe. Consequences:

* R-2 lands once, in the repack build. **The ~68-byte lean ceiling — which was
  about to be the binding ROM constraint of this slice — is gone.**
* Lean's `ON..GOTO` overrun (§2.2) is recorded as a **known defect of a retired
  build**, not fixed.
* Retirement is its own item, not this one: the 276 `IF ROM_BASE` gates and the
  seven repack-only includes become removable, and
  [`tools/check_reloc.py`](../tools/check_reloc.py)'s lean-baseline comparison —
  which is what currently proves the relocated image is a pure relocation — needs
  a replacement before the lean build stops being built. **D-LINEMAX must not
  depend on that item having landed**, and does not: it neither adds nor removes a
  gate.

**Q2 — funding the message string. DEFERRED to implementation** (user's call,
2026-07-29). It is a placement question, not a behavioural one: `"Line buffer
overflow"` + CRLF + 0 is 23 bytes, page 1 has 10 B free, the low region has 32 B,
and the lean cart has ~68 B. Candidates when the time comes: beside
`err_missing_operand` in [`missing.asm`](../basic/missing.asm) (the precedent for
exactly this constraint), the low region, or rendered sub-side. Measure the walls
before choosing.

**Q3 — where the 570 bytes come from. ANSWERED BY MEASURING, on the faithfulness
criterion.** This was first posed as a preference (elastic program space vs a hard
capability). That was the wrong frame: the question is which number the reference
already agrees with. Measured on both machines, `PRINT FRE(0)` after `MAXFILES=n`:

| | boot | `MAXFILES=1` | `=2` | `=4` | `=8` | `=15` |
|---|---|---|---|---|---|---|
| reference `FRE(0)` | 28815 | 28815 | 28548 | 28014 | 26946 | 25077 |
| zerobas | 15667 | 15667 | 15667 | **syntax error** | syntax error | syntax error |

Three things fall out, and together they decide it:

1. **The reference supports at least 15 channels**, charging a flat **267 bytes**
   each ((28815 − 25077)/14). zerobas caps at 2
   ([`sysvars.inc:2224`](../basic/sysvars.inc:2224)) and already refuses 4.
   Dropping `FCH_CEIL` to 1 moves **further from** the reference on an axis where
   zerobas is already 13 channels short — option **(b) is the unfaithful one**.
2. **Free program space already diverges by 13148 bytes** (15667 vs 28815). Option
   (a) moves a number that is structurally ours — zerobas's RAM map is its own —
   and is already 46% short; 768 bytes is 4.9% of what remains.
3. ⚠️ **The reference funds its own buffers out of exactly this pool.**
   `MAXFILES=15` costs 3738 bytes of the very `FRE(0)` that programs live in. So
   (a) is not merely the lesser harm — **it is the mechanism the reference uses.**

**Decision: (a)** — the page-2 window, `TXTMAX` down 768 bytes.

**Filed, not acted on — and my number is NOT yet a target.** zerobas charges
**562 bytes** per file-channel context ([`sysvars.inc:2227`](../basic/sysvars.inc:2227),
50 B state + a 512 B sector buffer) against the 267 B/channel measured above. That
2.1x is the reason the channel contexts, not the program area, are where RAM
should be found — but ⚠️ **the 267 came from the VG-8020, which has no disk
hardware at all.** A diskless channel needs no sector buffer, so 267 is not the
cost of a channel that does FAT12 I/O and cannot be used as the goal for one.

The right oracle is the disk-capable **CF-3300**. It could not be measured here:
`omsx_repl`'s readout scrapes the SCREEN 0 name table, and the CF-3300 boots to a
VRAM state that scrape returns garbage for, so every row read `<none>` — an
apparatus failure, not a finding. Measuring it needs the disk-probe harness
(`probes/disk/`). **Establishing that number is the first step of the slimming
item, not an input this spec already has.**

---

## 5. The gate

New `make linemax-acceptance` — [`basic_probe_linemax.py`](../probes/basic/basic_probe_linemax.py) `--gate`,
**61 rows** across seven batteries (`rem` 18, `tok` 12, `lnum` 6, `tokx` 7,
`bnd` 9, `corrupt` 4 + `code` 2), plus `--cas` (3 rows, one tape and one boot per
row).

⚠️ **THE `tok` AND `lnum` BATTERIES CANNOT GATE THIS ALONE.** Their verdict is
"the two machines produced the same bytes", and every `lnum` row PASSES today —
both machines crunch an identical 174 bytes, and only the one with a 96-byte
buffer is harmed (§2.2). **Agreement on what was produced is not agreement on
whether it fit.** The `corrupt` rows, which read the damage rather than the
output, are the ones with teeth; the byte batteries exist to pin *where* the
boundary is, not to prove safety.

Two-sided controls that must stay green throughout, and whose failure voids the
whole run (the probe enforces this before any verdict is read as a finding):
`rem-40`, `tok-5`, `tokx-5`, `corrupt-ctl`, `code-ctl`, plus the `rem-100`
calibration row.

Also: promote the **8 never-gated rows** in
[`basic_probe_arrdim.py`](../probes/basic/basic_probe_arrdim.py)
(`line-96`/`-97`/`-100`/`-250`, `cap-44`/`-64`/`-100`/`-120`) as they go green,
and re-run `make unit-test`, `make array-acceptance` (149/151 standing baseline),
`make clearpool-acceptance` (52/52), `make arrdim-acceptance` (65/65) and the
byte-identical crunch probe.

### 5.1 Apparatus changes this slice already made

* [`omsx_repl.py`](../probes/lib/omsx_repl.py) `MAX_BUF` 250 → **254**, measured,
  replacing a guess that *refused to inject* anything longer — the reason the
  reference's ceiling read as 250 for a whole slice.
* [`omsx_repl.py`](../probes/lib/omsx_repl.py) no longer discards an **empty**
  capture. `__hex_line` returns `""` for an empty program — "the line was refused
  on entry" — and that was being collapsed into the `None` a probe also gets when
  the machine never reached the capture at all. Callers that folded both
  (`if not raw`) are unaffected.
* [`arrdim-c-vg8020-characterization.md`](arrdim-c-vg8020-characterization.md) §4
  needs a correction note: "the reference's is 250" was the harness's cap.
