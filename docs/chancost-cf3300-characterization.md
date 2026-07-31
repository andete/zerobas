# File-channel cost — CF-3300 characterization

What one open file channel costs on a **real disk-capable MSX1**, measured
black-box on the National CF-3300 (Disk BASIC 1.0) and compared against zerobas.

Probe: [`probes/disk/diskbasic_probe_chancost.py`](../probes/disk/diskbasic_probe_chancost.py)
(`--side ref|zb|both`, `--only <labels>`, `-v` for full screens). Boot-per-case,
both machines, a `/tmp` copy of `disk/test720.dsk` per case.

Written for the **SLIM THE FILE-CHANNEL CONTEXT** item in [`TODO.md`](../TODO.md),
whose premise was that the previously-recorded **267 B** came from a *diskless*
VG-8020 and therefore could not be a valid target for a channel doing FAT12 I/O.
**That premise is now refuted by measurement: the disk-capable reference charges
exactly the same 267 B.**

## 0. The apparatus — why the earlier attempt read `<none>`

The earlier attempt to read this on the CF-3300 with `omsx_repl` returned
`<none>` on all six rows and was recorded as "the readout returns garbage on
that machine". That is an **apparatus failure with a specific, now-measured
cause**, not a property of the machine:

| | measured |
|---|---|
| `SCRMOD` (`$FCAF`) | **`$01`** — CF-3300 Disk BASIC boots to **SCREEN 1** |
| `LINLEN` (`$F3B0`) | **`$1D` = 29** |
| name table | **`$1800`, 32 columns** |

`omsx_repl` scrapes `SCR_ADDR = $0000` at `COLS = 40` — the SCREEN 0 name table
([`probes/lib/omsx_repl.py:91`](../probes/lib/omsx_repl.py:91), whose own comment
already flags that "a stock SCREEN-1 machine would need `0x1800`/768/32
instead"). Reading a SCREEN 1 machine through a SCREEN 0 scrape yields the
pattern-table bytes, which decode to noise. Dumping `$0000` on this machine is
reproduced in the probe's first smoke run and is unambiguous garbage while
`$1800` reads cleanly.

**This probe measures the geometry out of RAM and picks the name table from it**,
so the same code drives both the SCREEN 1 reference and the SCREEN 0 zerobas
machine. ⚠️ Do not "simplify" that back to a constant.

### 0.1 The echo guard — and the reason this probe's harness control could not fail

Added 2026-07-31 ([`spec-probe-chancost-echo-guard.md`](spec-probe-chancost-echo-guard.md)),
ported from [`diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py).
§0 of [`lof-cf3300-characterization.md`](lof-cf3300-characterization.md) is the
record of the guard's **three wrong versions** and is not re-derived here.

Every typed line is now checked against the screen before any answer is read off
it. A line that is not echoed returns **`MANGLED`**, which is **fatal** and which
**suppresses the derived slope, ceiling and headline** — a slope computed from a
ladder that never received `MAXFILES=8` is a number the run did not measure.

⚠️ **The reason this mattered here is not the one the item was filed for.** The
filed worry was that a mangled line would read as an `FRE(0)` finding. The sharper
problem is what mangling actually produces: **a `Syntax error`** — which is what
`ctl_syntax`, this probe's own harness control, is *recorded as expecting*. A
mangled `ctl_syntax` row reads `SYNTAX`, matches its oracle, compares equal
across the machines and prints **`agree`**. The control that exists to prove the
harness is typing **fails toward "pass" when the harness stops typing.** That is
not hypothetical: K1 below shows mangled lines landing on `SYNTAX` on both
machines in the same run.

**Falsified before being believed, both halves:**

* **K1 — real captures, end to end.** `--only lof_new,lof_existing,open_after
  --line-delay 3.1` → **3/3 `MANGLED`, exit 3**, derivation suppressed. The
  screens are D-LOF's failure mode reproduced inside this probe: on the reference
  `PRINT LOF(1)` arrived as **`RIT OF1)`** and `OPEN "ZQ.DAT" FOR OUTPUT AS #1` as
  **`PE "Q.AT FR UTUTAS#1`**, each answered with a **completely real
  `Syntax error`**; on zerobas the same lines arrived as `T`, `(1`,
  `ZBPN"Z.A"FO UPU S#`. **Both sides mangled, both reading `SYNTAX` — they would
  have compared EQUAL.**
  Control: **the identical command with the one flag removed** (default 4.5 s) →
  **exit 0**, `lof_new` 0/0, `lof_existing` 26/26, `open_after` 23163/14799.
* **K2 — the INSERTED half, deterministically.** `echo_missing` fed synthetic
  screens, **8/8**: a doubled-character row (`ZBPPRINT FRE(0)`) is **RED** — the
  case a plain substring test passes, because `PRINTFRE(0)` is still inside it —
  while a clean row, and a **wrapped** reference echo split across two rows at a
  left margin of 2 *and* at margin 1, are all **GREEN**. Wrapping is the shape
  versions 1 and 2 wrongly failed; a scrolled-off first line is **RED**.

⚠️ **And the gate immediately found one more non-reading wearing a reading's
face.** A full run came back `lof_new` reference = `None` → **`ORACLE DRIFT`**;
re-run, a clean **0** on a perfect screen. The guard had not fired because
`run_case`'s **TIMEOUT** and **NO CAPTURE** paths return *before* it, both
returning `None` — the same value a clean screen with no number on it reads as.
**A sentinel that also means "no reading" is not a measurement**: a run that never
finished was being reported as the CF-3300 failing to reproduce its own oracle.
Both paths now return `TIMEOUT` / `NOCAPTURE` and are handled like `MANGLED`
(fatal, derivation suppressed) under the verdict `RUN FAILED`. **K3:** a bogus
`ZEROBAS_BASIC_MACHINE` → `NOCAPTURE`, exit **3**; the identical command with the
real machine → `0`, exit **0**. The 200 s deadline is deliberately left alone —
which path fired is not known, and raising a timeout to fix an unattributed
failure would be a guess. The markers make the next occurrence name itself.

The wrap case is also confirmed on a real capture rather than only synthetically:
`err_badchan` types a 32-character line 30, which the reference wraps across two
rows (`30 OPEN "HI.TXT" FOR INPUT AS` / `#2`), and the guard passes it.

**The port moved no reading.** Full run after: **39 cases, 0 mangled, 0 oracle
drift, 0 unfiled divergence, `KNOWN_DIVERGE` empty**, both machines per-channel
and linear with ceiling 15, headline 267 B (ref) / 50 B (zb) — identical to
before. That is the control on the change itself.

### 0.2 `NOREAD` — the third thing wearing a reading's face (D-MFDOM, 2026-07-31)

§0.1 fixed `TIMEOUT`/`NOCAPTURE` returning the same `None` a clean screen does.
**One layer further in, the value derivation had the same shape.** `err_class`
returns `None` for any message not in `ERR_CLASSES`; the number scan then also
returned `None`. So a screen carrying an **unclassified error** was indistinguishable
from a screen carrying no number — and `ERR_CLASSES` had **no entry for
`Overflow`**, which is precisely what the reference answers for `MAXFILES=65536`.

⚠️ **That is not a hypothetical, it is this slice's own defect.** A reference
raising `Overflow` against a zerobas that silently accepts reads `None` vs
`None`, compares **equal**, and prints **`agree`** — the exact defect the rows
were written to find, scored as a pass.

Fixed: `OVF` and `TM` added to `ERR_CLASSES`; an unreadable screen now returns
**`NOREAD`**, fatal like `MANGLED` and likewise suppressing the derivation. The
derivation was lifted into `read_value()` so it can be falsified without booting
a machine.

⚠️ **And K4 is COMMITTED, unlike K1/K2/K3.** Those were run ad hoc and survive
only as claims in this document; a guard whose falsification cannot be re-run is
a guard nobody can check. `python3 probes/disk/selftest_chancost_readvalue.py`
boots no machine and needs no reference ROMs.

**K4 12/12** on synthetic screens — four RED (unclassified error, empty screen,
`Ok` only, an un-mapped message) and eight GREEN (a number, a negative number,
`IFC`, `SYNTAX`, `Overflow` in both cases, `Type mismatch`, and an error
outranking a later number, which pins that the refactor moved nothing).
**K4b CUTS**: replaying the old rule on the same two screens returns
`None`/`None` → `agree`.

## 1. `FRE(0)` is the instrument, and it is impure

`FRE(0)` counts down to the **stack pointer**; every extra expression-nesting
level costs 6 bytes ([`binfre-vg8020-characterization.md` §3.1](binfre-vg8020-characterization.md)).
Every reading below is therefore the **byte-identical expression `PRINT FRE(0)`
at identical depth**. A row that "simplifies" its expression is measuring a
different thing.

`FRE(0)` is the *variable/program* pool; `FRE("")` is the *string* pool — two
separate allocators.

## 2. The ladder — 267 B per channel, exactly linear

| `MAXFILES` | `FRE(0)` | Δ | per channel |
|---|---|---|---|
| 0 | 23697 | — | — |
| 1 | 23430 | 267 | 267 |
| 2 | 23163 | 267 | 267 |
| 3 | 22896 | 267 | 267 |
| 4 | 22629 | 267 | 267 |
| 8 | 21561 | 1068 | 267 |
| 15 | 19692 | 1869 | 267 |

**267 B per channel, linear with no intercept term across the whole legal range.**
The non-adjacent points (8, 15) fit the same slope, so this is a measured line,
not a two-point subtraction.

### 2.1 Controls — because a ladder this clean is when to try hardest to falsify

| control | reads | what it rules out |
|---|---|---|
| `ctl_syntax` — types `MAXFILEZ=2` | **`Syntax error`** | the harness is provably typing; a clean screen here would invalidate every number above |
| `ctl_noop` — types `REM MAXFILES=8` | echoed, `FRE(0)` **unmoved** (23430) | the ladder's movement is attributable to the *statement*, not to the typing |

⚠️ **`MAXFILES=1` is NOT load-bearing.** It reads 23430, identical to an
untouched boot — because **1 is the Disk BASIC default**. That row cannot
distinguish "the statement ran" from "the line was never typed", and would
agree for the wrong reason. The rows that carry the result are 0/2/3/4/8/15,
all of which move.

## 3. The ceiling is exactly 15, and it fails with IFC

| typed | reference |
|---|---|
| `MAXFILES=15` | accepted |
| `MAXFILES=16` | **`Illegal function call`** |
| `MAXFILES=255` | **`Illegal function call`** |

TODO recorded "at least 15". It is **exactly 15**, and the rejection is
**ERR 5 (Illegal function call)** — measured, not assumed.

⚠️ **Both rows above have a zero high byte**, so this table pins ONE arm of the
argument test. The full domain — including the `Overflow` class these two rows
cannot reach, and the two zerobas defects hiding behind them — is **§11**.

## 4. When is the buffer charged? At `MAXFILES` time, not at `OPEN` time

| row | `FRE(0)` |
|---|---|
| `MAXFILES=2` | 23163 |
| `MAXFILES=2 : OPEN "ZQ.DAT" FOR OUTPUT AS #1` | **23163 — unchanged** |

The `OPEN` demonstrably succeeded (`Ok`, and `LOF(1)` answers). **Opening a
channel costs zero additional `FRE(0)`** — `MAXFILES=n` reserves all n buffers
up front, and `OPEN` just claims one.

## 5. Which pool pays, and by what mechanism

| row | reads |
|---|---|
| `MAXFILES=0 : PRINT FRE("")` | 200 |
| `MAXFILES=8 : PRINT FRE("")` | 200 |

The **string pool is untouched**; the entire charge lands in the
variable/program pool.

And the mechanism, from the pointers read at dump time:

| | `MAXFILES=0` | `MAXFILES=4` |
|---|---|---|
| `TXTTAB` (`$F676`) | `$8001` | `$8001` |
| `HIMEM` (`$FC4A`) | `$DE77` | `$DE77` |

**Both are constant.** Neither the bottom of program text nor the user-visible
memory ceiling moves. Combined with §1 — `FRE(0)` counts down to **SP** — the
buffers are carved **downward from the top**, pushing the stack (and therefore
the number `FRE(0)` reports) down by 267 per channel. `HIMEM` stays put because
`HIMEM` is the *user-settable* ceiling (`CLEAR ,himem`), not the allocation
pointer.

### 5.1 What the 267 does **not** include

267 < 512, so a **512-byte sector staging buffer is not in it**. The disk
system keeps its sector buffer in its own reserved high-RAM work area — the
same reservation already characterized from the other direction in
[`TODO.md`](../TODO.md) §8.21/§8.22 as the disk resident footprint. So the
reference's shape is:

> **one shared sector buffer, plus a small per-channel state+record block.**

That is exactly the shape the TODO item hypothesized, now measured rather than
assumed.

## 6. zerobas, measured the same way

| | reference (CF-3300) | zerobas, as measured | zerobas, after D-FCH ✅ |
|---|---|---|---|
| per channel | **267 B**, from the `FRE(0)` pool | **562 B** (`FCH_CTXSZ` = 50 B state + a private 512 B sector-buffer **save copy**) | **50 B**, from the `FRE(0)` pool |
| when charged | dynamically, at `MAXFILES` time | **statically, always** — `FCH_CTX $EA00..$EE63`, reserved whether or not any channel is open | **dynamically, at `MAXFILES` time** |
| `FRE(0)` response to `MAXFILES` | −267 per channel | **0 — does not move at all** (13875 at `MAXFILES` 0, 1 and 2) | **−50 per channel** (14899 at 0 → 14149 at 15) |
| ceiling | **15** | **2** (`FCH_CEIL`) | **15** |
| over-ceiling error | `Illegal function call` (ERR 5) | **`syntax error` (ERR 2)** | `syntax error` — still S-FCH-2 |

The MECHANISMS now match; the CONSTANTS deliberately do not. A zerobas block
genuinely IS 50 B — its sector staging is the shared `FSECTOR_BUF` write-back
cache (S-FCH-1) — so it charges what it uses. Padding to 267 for numeric parity
would reserve 217 B per channel that nothing reads; see
[`spec-basic-filechan-alloc.md` §6](spec-basic-filechan-alloc.md).

Note zerobas's private 512 B per channel is **purely a save area**: a single
global `FSECTOR_BUF` (`$E5C0..$E7BF`) is the working buffer, and the context
switch `memcpy`s it in and out ([`basic/files.asm:994`](../basic/files.asm:994)
`fch_save_active` / `fch_load_ctx`). The reference gets the same effect by
treating the shared buffer as a **cache** — flush on switch away, re-read on
switch back — which is why its per-channel block is small.

⚠️ Error-message **wording** is not compared. zerobas prints its own lowercase
messages by deliberate provenance policy
([`basic/PROVENANCE.md`](../basic/PROVENANCE.md) §851) — `syntax error` vs
`Syntax error` is the firewall working as designed. The probe therefore
compares error **classes**; comparing raw text would emit a false divergence on
every error row and bury the real findings.

## 7. Incidental findings (found by the controls, not aimed at)

### 7.1 ✅ `LOF(#n)` on a freshly-created OUTPUT channel — FIXED 2026-07-31

> **LANDED as D-LOF** ([`spec-basic-lof-size-field.md`](spec-basic-lof-size-field.md),
> [`lof-cf3300-characterization.md`](lof-cf3300-characterization.md)). `lof_new`
> now reads **0** on both machines and has left this probe's `KNOWN_DIVERGE`,
> which is now EMPTY. The guess recorded below was right in outline and wrong in
> its scope: the field is uninitialised on **three** create paths, not on the one
> this row walks, and −1 is not a marker of anything — it is a **stale reading**,
> measured at 26 and at 2048 when a known-size file was opened and closed first.

| row | reference | zerobas |
|---|---|---|
| `OPEN "ZQ.DAT" FOR OUTPUT AS #1 : PRINT LOF(1)` | **0** | **−1** |
| …then `PRINT #1,"ABCDE"` and re-ask | **0** | **−1** |
| `OPEN "HI.TXT" FOR INPUT AS #1 : PRINT LOF(1)` — **control** | **26** | **26** |

The control agrees on both machines, so this is neither apparatus nor a broken
`LOF`: it is specific to a channel opened `FOR OUTPUT` on a file that did not
previously exist. −1 = `$FFFF` suggests an uninitialized size field being
reported rather than a zero. (The reference staying at 0 after `PRINT #1` is its
own documented behaviour — the directory entry is not updated until `CLOSE`.)

### 7.2 ✅ Over-ceiling `MAXFILES` raises the wrong error class — FIXED

> **LANDED.** The class half was fixed by `61e3a48` (ERR 5, at zero cost); the
> rest of the argument domain was measured and fixed 2026-07-31 as **D-MFDOM**
> ([`spec-basic-maxfiles-domain.md`](spec-basic-maxfiles-domain.md)) — see §11
> below, which is the full domain rather than this one row.

The finding as filed: `MAXFILES=16` → reference **`Illegal function call`**;
zerobas raised **`syntax error`**. The error *class* was wrong independently of
where the ceiling sat, so it was fixable without changing the ceiling.

⚠️ **And closing it on that row alone would have been wrong.** `mf16` and
`mf255` both have a **zero high byte**, so both land on the same arm of the
domain test; nothing in the corpus reached the other arm, and the two defects in
§11 were sitting behind it the whole time.

## 11. The `MAXFILES` argument DOMAIN — measured (D-MFDOM, 2026-07-31)

Fourteen rows, `mfd_*`. The reference's answers were recorded **before zerobas
was run on a single one of them**, so the oracle cannot have been back-fitted.

### 11.1 The reference's rule — three parts

| typed | reference | rule |
|---|---|---|
| `MAXFILES=300` | `Illegal function call` | in int16, outside `0..15` → **ERR 5** |
| `MAXFILES=8+8` | `Illegal function call` | …reached by an expression, same answer |
| `MAXFILES=-1`, `=-16` | `Illegal function call` | negatives are ERR 5, not Overflow |
| `MAXFILES=32767` | `Illegal function call` | …up to the int16 edge |
| `MAXFILES=-32768` | `Illegal function call` | **the range, not the magnitude** |
| `MAXFILES=32768` | **`Overflow`** | outside int16 → **ERR 6** |
| `MAXFILES=-32769` | **`Overflow`** | …and symmetrically below |
| `MAXFILES=65536`, `=70000` | **`Overflow`** | …however far out |
| `MAXFILES=2.5` | *(effective 2)* | fractional **TRUNCATES** |
| `MAXFILES=15.9` | *(effective 15, accepted)* | …truncation, not rounding — rounding would be ERR 5 |
| `MAXFILES 2` | `Syntax error` | the missing `=` is still syntax |

⚠️ **The int16 boundary is the RANGE −32768..32767, not the magnitude
|x| ≤ 32767.** That asymmetry was already recorded in `get_byte_arg`'s header
for `CHR$` on the VG-8020; §11 **measures it for `MAXFILES` on the CF-3300**
rather than assuming it carries across verbs.

### 11.2 Two zerobas defects, and only one of them was the filed one

`ex_maxfiles` took its argument through `eval` plus a hand-inlined
`ld a,d / or a / jp nz,gb_illegal`. Measured against the rule above:

| typed | reference | zerobas (before) | |
|---|---|---|---|
| `MAXFILES=65536` | `Overflow` | **`FRE(0)` = mf0's value** | 🔴 **SILENT ACCEPT** |
| `MAXFILES=70000` | `Overflow` | **`FRE(0)` = mf0's value** | 🔴 **SILENT ACCEPT** |
| `MAXFILES=32768` | `Overflow` | `Illegal function call` | wrong class |
| `MAXFILES=-32769` | `Overflow` | `Illegal function call` | wrong class |
| `MAXFILES=32767` | `Illegal function call` | `Illegal function call` | *control — green* |
| `MAXFILES=-32768` | `Illegal function call` | `Illegal function call` | *control — green* |

🔴 **The severe one is the silent accept.** `eval`'s `flt_to_int16` **zeroes
`DE`** for an out-of-int16 value (`interp.asm`'s own header says so), so the
high-byte test could never fire for exactly the arguments it existed to catch:
`MAXFILES=65536` arrived as `DE=0` and was accepted as an ordinary request for
**zero channels — disabling every file channel with no error at all.**

🔴 **And the second defect was invisible to the rows that found the first.**
`32768` and `-32769` are *representable* in 16 bits, so `DE` is non-zero and the
old test *did* fire — with ERR 5 where the reference says ERR 6. The two rows
that triggered this slice (`65536`, `70000`) could not have exposed it; only the
boundary rows could, and they were added to pin **the denominator of the FIX**,
not of the defect.

### 11.3 The fix

`call eval` + the five hand-inlined bytes → **`call eval_byte_arg`**, which *is*
the reference rule (int16 stage → ERR 6, then `0..255` → ERR 5). The `FCH_CEIL`
test stays, because that bound is the statement's own. Nine bytes become three:
**page 1 free 63 → 69 B, low region unchanged at 23 B** — a net saving.

### 11.4 Falsification

Reverting `basic/files.asm` alone and re-running: **4 rows RED, 10 GREEN**, the
red ones exactly `mfd_65536` / `mfd_70000` / `mfd_32768` / `mfd_n32769`, with
`mfd_32767` and `mfd_n32768` — the *same* boundary, one step inside — staying
green. The knife is attributable to crossing int16, not to "large arguments
behave differently".

⚠️ The prediction written before that run said `MAXFILES=32768` would be a
**silent accept** too. It is not; it read `IFC`. The measurement corrected the
prediction, which is the whole reason the knife is run instead of reasoned.

## 9. `MAXFILES` semantics — measured

| row | reference | zerobas |
|---|---|---|
| `A=5 : MAXFILES=2 : PRINT A` | **0** — variables CLEARed | `5` |
| `A=5 : REM MAXFILES=2 : PRINT A` — *control* | `5` | `5` |
| `A=5 : MAXFILES=1 : PRINT A` (value **unchanged**) | **0** — clears anyway | `5` |
| `A$="XY" : MAXFILES=2 : PRINT A$` | empty | empty |
| `CLEAR 500 : MAXFILES=2 : PRINT FRE("")` | **500** — pool size survives | `500` |
| `OPEN…AS #1 : MAXFILES=2 : PRINT LOF(1)` | **`File not OPEN`** | `-1` |
| `MAXFILES=0 : OPEN…AS #1` | **`Bad file number`** | `syntax error` |
| `MAXFILES=1 : OPEN…AS #2` | **`Bad file number`** | `syntax error` |

⚠️ **`MAXFILES` clears UNCONDITIONALLY — even when the value does not change.**
`sem_same` is the row that pins it; without it the natural reading is "clears
only when it reallocates", which is wrong.

## 10. The disk error block — code → message, measured

`ERROR n` prints its own message, which maps the block black-box:

| code | message | code | message |
|---|---|---|---|
| 50 | FIELD overflow | 58 | Sequential I/O only |
| 51 | Internal error | **59** | **File not OPEN** |
| **52** | **Bad file number** | 60 | Bad FAT |
| 53 | File not found | 61 | Bad file mode |
| 54 | File already open | 62 | Bad drive name |
| 55 | Input past end | 63 | Bad sector number |
| 56 | Bad file name | 64 | File still open |
| 57 | Direct statement in file | 65 | File already exists |

Trapped with `ON ERROR`/`ERR`: `MAXFILES=16` → **5**, `LOF` on a closed channel
→ **59**.

⚠️ **`Bad file number` is NOT trappable.** With a handler installed the other two
trap cleanly, but the bad-channel `OPEN` prints `Bad file number in 30` and never
reaches it — which is why 52 comes from the `ERROR n` map rather than from `ERR`.

## 8. What this licenses

* **267 B is a valid target** — it is what a channel doing real FAT12 I/O costs
  on the reference, not an artifact of a diskless machine. The TODO caveat is
  resolved.
* zerobas's 512 B per channel is a **save copy, not a requirement**; the
  reference proves a shared sector buffer with flush/re-read is sufficient.
* At `FCH_CEIL=2`, dropping the save copy frees **1024 B** of page 3
  (1124 → 100). At `FCH_CEIL=15` — full reference parity on the ceiling — the
  table costs 750 B, still **374 B less than today**.
* ⚠️ **Not measured: the ROM cost.** Replacing `memcpy` save/restore with
  flush-and-re-read is a change to `basic/files.asm` of unknown size, against a
  low region with **9 B free** and page 1 with **6 B free**. Any estimate here
  would be a risk assessment written from reading code — a hypothesis, not a
  measurement ([`arrdim-c-slice`](../../.claude/projects/-Users-joost-projects-zerobas/memory/arrdim-c-slice.md)).
  It must be built to be known.
* ⚠️ Freeing page-3 RAM does **not** by itself return program space. `TXTMAX`
  rises only if a page-2 buffer *moves* into the freed page-3 window:
  `TOKBUF` (576 B at `$B700`) and the input line buffer are the movable
  candidates; `DETOKBUF` (1280 B at `$BB00`) does not fit in 1024 B.
