# `WIDTH n` — the VG-8020 differential (D-WID)

Instrument: [`probes/basic/basic_probe_width.py`](../probes/basic/basic_probe_width.py),
boot-per-case, reference `Philips_VG_8020` against
`C-BIOS_MSX1_EU_REPACK_DISK`. Baseline measured on a clean-built `92d3592`:
**36/62 rows agree, 26 diverge.** A second run added 14 gap rows (§6).

This closes the question
[`docs/spec-basic-abort-depth.md`](spec-basic-abort-depth.md) §7 deferred:

> **The `WIDTH 300` screen-width surface itself.** Once the error aborts
> correctly, `LINLEN` is never written; whether `WIDTH`'s *valid* domain matches
> the reference is a separate question this slice does not open.

---

## 1. The apparatus, and why it is not a screen scrape

**The subject under test moves the instrument.** Every other probe in this tree
reads the SCREEN-0 name table at a fixed stride of 40 bytes per row
(`omsx_repl.COLS`). `WIDTH` is the one statement whose entire job is to change
that stride: after `WIDTH 32` the console driver lays rows down 32 bytes apart
while the VDP still displays 40 per row, so the scrape shears and every row
readout — echo anchor included — silently stops meaning anything. Same class of
trap as the echo-anchored readout that could not measure a statement which moves
the cursor ([`docs/spec-basic-missing-class.md`](spec-basic-missing-class.md)).

So the readout is numeric and the restore comes first:

```
 10 SCREEN 1:WIDTH 32          ' PIN the instrument: LINL32 = 32 ...
 20 SCREEN 0:WIDTH 40          ' ... and LINL40 = 40, on BOTH machines
 30 <mode>                     ' the screen mode under test
 40 ON ERROR GOTO 100
 50 E=0:<subject>              ' the WIDTH under test
 60 L=PEEK(&HF3B0):M=PEEK(&HF3AE)
 70 N=PEEK(&HF3AF)
 80 SCREEN 0:WIDTH 40          ' restore the INSTRUMENT before any output
 90 PRINT"[";E;L;M;N;"]":END
100 E=ERR:RESUME 60
```

Readout `[ ERR LINLEN LINL40 LINL32 ]`, `ERR 0` meaning accepted. All three
sysvars are read **before** the restore, so a reject that scribbled on them
anyway is visible. They are published MSX system variables (MSX2 Technical
Handbook); nothing here is disassembled.

**Lines 10–20 are the whole reason the probe is readable.** The first draft
pinned the width only on rows whose subject *was* a `WIDTH`, and three control
rows that never execute a `WIDTH` at all came back diverging — `[5 37 37 29]`
against `[5 39 39 29]`. The `ERR` codes agreed; the machines simply **boot at
different text widths** (reference 37, zerobas 39), and both `LINL40` and
`LINL32` carried that difference into every readout. Unpinned, the probe would
have reported a defect in `WIDTH`'s domain that was really the boot default.
The pin also gives every reject row a *known* prior `LINLEN`, which is what
makes "did the reject write anything anyway?" a question the readout can answer.
[[cursor-cluster-slice]]'s rule again: **pin the instrument first.**

`ctl-restore` is the row that proves the restore works: it sets `WIDTH 20`,
a width the scrape cannot survive, and the readout still comes back
(`[0 20 20 32]`). Without it, an apparatus that returned `<none>` for every
accepted width would look like a machine that rejects every width.

**These batteries arm `ON ERROR` on purpose** — the opposite of the rule in
`basic_probe_abort_depth.py` and `basic_probe_str_domain.py`. Those measure the
*unwind*, which a handler hides. This measures the *domain*, and a trapped `ERR`
read is the only readout that survives a statement which has just destroyed the
screen. The unwind is not re-litigated here; `make abort-acceptance` gates it.
The `unt` battery keeps five untrapped rows as the seam between the two gates.

---

## 2. The reference's rule

### 2.1 The bound is MODE-DEPENDENT, and the per-mode slot goes with it

| mode | `SCRMOD` | legal `n` | per-mode default written |
|---|---|---|---|
| `SCREEN 0` text-1 | 0 | **1..40** | `LINL40` ($F3AE) |
| `SCREEN 1` text-2 | 1 | **1..32** | `LINL32` ($F3AF) |
| `SCREEN 2` graphics | 2 | **1..40** | **`LINL40`** |
| `SCREEN 3` multicolour | 3 | **1..40** | **`LINL40`** |

The graphics row is the one that is not guessable. `SCREEN 2 : WIDTH 1` reads
`[0 1 1 32]` — `LINLEN` **and `LINL40`** move, `LINL32` does not — and
`SCREEN 2 : WIDTH 41` raises. So the rule is not "text-1 versus everything
else"; it is **`LINL32`/32 for `SCREEN 1` alone, `LINL40`/40 for every other
mode**, graphics included.

Boundary rows, both sides, in every mode: `s0-40` accepted / `s0-41` rejected,
`s1-32` accepted / `s1-33` rejected, `s2-40` accepted / `s2-41` rejected,
`s3-32` accepted / `s3-41` rejected, and `s0-0` / `s1-0` / `s2-0` all rejected.

### 2.2 A reject writes NOTHING

Every rejected row reads back the pinned state unchanged —
`s0-41` → `[5 40 40 32]`, `s1-40` → `[5 32 40 32]`. The reference checks
before it writes, and it does not partially apply.

### 2.3 Four distinct errors, not one

| input | reference |
|---|---|
| `n` outside the mode's `1..max`, still inside int16 | `Illegal function call` (ERR 5) |
| `n` beyond int16 (`32768`, `99999`, `-32769`) | `Overflow` (ERR 6) |
| a STRING argument (`WIDTH "40"`, `WIDTH A$`) | **`Type mismatch` (ERR 13)** |
| no argument (`WIDTH`, `WIDTH :X=1`, `X=1:WIDTH`) | **`Missing operand` (ERR 24)** |
| `WIDTH ,` | `Syntax error` (ERR 2) |

The bottom two were on nobody's list. `Missing operand` is the same ERR 24
`LOCATE` turned up — the distinct error whose message
[`basic/missing.asm:70`](../basic/missing.asm:70) had to add because `err_msgtab`
stopped at 23.

**The int16/byte stage already agrees exactly.** `-32768` → ERR 5 and `-32769` →
ERR 6, `32767` → ERR 5 and `32768` → ERR 6: `get_byte_arg`'s existing two-stage
rule (the range −32768..32767, not the magnitude) is already the reference's,
verified at both boundaries. The mode bound sits **on top of** it, and none of
that half needs touching.

### 2.4 Coercion truncates toward zero BEFORE the bound check

`WIDTH 40.9` → 40, accepted. `WIDTH 41.9` → 41, **rejected**. `WIDTH 32.9` in
`SCREEN 1` → 32, accepted. `WIDTH -0.5` → 0, rejected.

Three orderings are ruled out at once: rounding would reject 40.9, checking the
bound before truncating would also reject 40.9, and flooring would send −0.5 to
−1 rather than 0. Truncate-toward-zero, then bound — the same rule
[`docs/spec-basic-str-domain.md`](spec-basic-str-domain.md) measured for the
string family.

### 2.5 The domain check BEATS the deferred syntax error

`WIDTH 41,` has both a domain error and a trailing-comma syntax error. The
reference reports **ERR 5**, not ERR 2 — so the argument is checked before the
rest of the line is scanned. (`WIDTH 0,` likewise.) Identical to `MID$(A$,0,)`
→ `Illegal function call` in the string-domain slice, and it fixes the
implementation's ordering.

The converse row pins the other half: `WIDTH 32,` reads `[2 32 32 32]` — the
**accepted** width is applied and *then* the trailing comma is a syntax error.
So an accepted argument is not rolled back by a later parse failure.

### 2.6 The per-mode default persists across a mode switch

`SCREEN 0 : WIDTH 32 : SCREEN 1 : SCREEN 0` → `[0 32 32 32]`, and
`SCREEN 1 : WIDTH 29 : SCREEN 0 : SCREEN 1` → `[0 29 40 29]`. Returning to a
mode re-applies that mode's recorded default. Both already agree.

---

## 3. What zerobas does today — five divergences, every one SILENT

[`basic/screen.asm:223`](../basic/screen.asm:223) evaluates the argument, runs it
through `get_byte_arg` (whose whole domain is 0..255), then writes `LINLEN`, a
per-mode default and calls `CHGMOD` **unconditionally**. There is no bound
anywhere and no correct mode-dependence.

| # | input | reference | zerobas |
|---|---|---|---|
| D-WID-1 | `WIDTH 0` (any mode) | `Illegal function call` | accepted → **width 0** |
| D-WID-2 | `WIDTH 41`..`255` (`SCREEN 0`/`2`/`3`), `WIDTH 33`..`255` (`SCREEN 1`) | `Illegal function call` | accepted → **that width** |
| D-WID-3 | `SCREEN 2 : WIDTH 29` | records `LINL40` = 29 | records **`LINL32`** = 29 |
| D-WID-4 | `WIDTH "40"` / `WIDTH A$` | `Type mismatch` | accepted → **width 0** |
| D-WID-5 | `WIDTH` / `WIDTH :` / `X=1:WIDTH` | `Missing operand` | accepted → **width 0** |

**Every one of them destroys the display with no error.** That is precisely the
`WIDTH 300` symptom `4d35b6d` fixed — reached through the ACCEPT path instead of
the reject path, and so completely untouched by that fix. The untrapped battery
shows it directly: `WIDTH 41`, `WIDTH 200`, `WIDTH 0`, `WIDTH` and `WIDTH "40"`
typed at the prompt each report `<no echo>` on zerobas, meaning the echo the
readout anchors on is *gone* — the same signature `basic_probe_abort_depth.py`
recorded for `WIDTH 300` before the abort fix. The reference prints a clean
`Illegal function call` / `Missing operand` / `Type mismatch` and leaves the
screen usable.

D-WID-3 is user-visible, not merely a sysvar difference:
`SCREEN 2 : WIDTH 29 : SCREEN 0` leaves the reference at width 29 and zerobas at
width 40, because zerobas wrote the width into the slot `SCREEN 0` does not read.

D-WID-4 and D-WID-5 were **found by batteries written to cover the argument
surface rather than to confirm the known defect** — the fifth consecutive slice
whose calibration turned up live defects nobody was looking for.

---

## 4. What already agrees, and must keep agreeing

Not padding: a bound check's failure mode is rejecting what it should accept.

- every legal width in every mode (`1`, `2`, `29`, `32`, `39`, `40` in
  `SCREEN 0`; `1`, `29`, `32` in `SCREEN 1`; `1`, `32`, `33`, `40` in `SCREEN 2`);
- the whole int16/byte error boundary (§2.3) — five rows, already exact;
- truncation of a fractional argument in range (`40.7`, `40.5`);
- an expression argument (`WIDTH 20+12`) and an integer-typed variable
  (`A%=32:WIDTH A%`);
- `WIDTH ,` → `Syntax error`; `WIDTH 32,` and `WIDTH 32,40` → apply 32, then
  `Syntax error`;
- the per-mode persistence rows of §2.6 (except through the D-WID-3 slot bug);
- `WIDTH 300` and `WIDTH 99999` untrapped — `4d35b6d` holds.

---

## 5. Where the fix lands

`ex_width` is at **$5905 — page 1**, and so are the three raisers it needs:
`gb_illegal` ($4565), `type_mismatch_error` ($424B), `loc_missing` ($7ED1). So
this slice is charged entirely to the **page-1 wall**, which a clean build of
`92d3592` leaves at **30 B free** (low region 30 B, untouched).

Both rejects run at `ex_width`'s **own** stack depth — `exec_stmt` `jp`s to the
handler — so neither needs the `LOC_RET`-style return-address parking `loc_next`
uses. Same reason `ex_swap` tests its operands at the handler's depth
([[missing-class-slice]]).

`LINL40` ($F3AE) and `LINL32` ($F3AF) are **adjacent**, so one `ld de,LINL40`
plus a conditional `inc de` picks the slot and the bound rides the same test.

---

## 6. Coverage

62 rows in the baseline matrix, 14 added afterwards to close gaps the first run
left: the low/negative end in `SCREEN 1` and `SCREEN 2` (a bound is two-sided
and only the top was covered), the string argument as a **variable** as well as
a literal (a literal can mask a bug a variable exposes — the `VARPTR` `FACTYP`
precedent), the truncation boundary at the *mode's* bound rather than at 255,
the missing-argument forms mid-line, the ordering rows of §2.5, and the
untrapped `WIDTH` / `WIDTH "40"` rows.

⚠️ **The gap run's zerobas column was contaminated and is discarded.** The
installed machine XML references `build/*.rom` by absolute path, and the tree
was rebuilt while that differential was in flight — so the ROM under measurement
changed mid-run. The reference column is a stock VG-8020 and is unaffected,
which is the half those rows were added for; every §2 fact above is a `ref:`
reading. **Do not rebuild while a differential is running.**
