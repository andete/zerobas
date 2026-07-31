# Spec — port the echo guard into `diskbasic_probe_chancost.py`

Status: ✅ **LANDED 2026-07-31.** Signed off, implemented, falsified (K1 + K2),
gate green: **39 cases · 0 mangled · 0 oracle drift · 0 unfiled divergence ·
`KNOWN_DIVERGE` EMPTY · ceiling 15 both machines**. Results in
[`chancost-cf3300-characterization.md`](chancost-cf3300-characterization.md) §0.1.
Owner item: the `TODO.md` entry "`diskbasic_probe_chancost.py` has no echo guard".

⚠️ **One thing this spec did not predict, found by the port:** the sharpest
consequence is not that a mangled line reads as an `FRE(0)` finding (§1) but that
it reads as a **`Syntax error`** — which is exactly what `ctl_syntax`, the
probe's own harness control, is recorded as expecting. **The control that proves
the harness is typing cannot notice the harness not typing**; it fails toward
"pass". K1 measured mangled lines landing on `SYNTAX` on both machines in one run.
§5's predicted red rows did **not** materialise at the 4.5 s default — the run was
clean on all 39 — so rule (A)/(C) were never reached and the cadence is unchanged.

**Zero ROM bytes.** No file under `basic/` or `sub/` is touched. This is pure
apparatus: it changes what the probe is *willing to call a reading*, and must
change no reading.

## 1. The defect

[`probes/disk/diskbasic_probe_chancost.py`](../probes/disk/diskbasic_probe_chancost.py)
types BASIC into a real National CF-3300 at a **4.5 s per-line cadence** and reads
the answer off the name table. It has **no check that the line it typed ever
arrived.**

That is the exact cadence at which D-LOF measured the CF-3300 eating whole chunks
of any line typed after a line that touched the disk — `PRINT LOF(1)` arriving as
`PRO)`, `OPEN "ZQ.DAT" FOR INPUT AS #1` as `OZQ R INPUT AS #1`
([`lof-cf3300-characterization.md`](lof-cf3300-characterization.md) §0). The
machine answers the *mangled* line with a **completely real `Syntax error`**, so
the failure is indistinguishable from a semantic finding by its answer alone.

In this probe a mangled line would read as an `FRE(0)` finding, an oracle drift,
or a divergence — never as an apparatus failure. Two rows here are error-class
rows (`ctl_syntax` expects `SYNTAX`; `mf16`/`mf255` expect `IFC`), and a mangled
line landing on `SYNTAX` would make a *broken* run look like a *passing* one.

⚠️ The probe has been stable for many sessions. Stability is not attribution —
that is the whole content of the filed item.

## 2. What is ported, and from where

All of it already exists in
[`probes/disk/diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py).
**Nothing is re-invented**; §0 of the characterization is the record of the three
wrong versions and is not to be re-derived.

| # | change | site |
|---|---|---|
| 1 | `MACHINES` gains a fourth field, the **per-side prompt**: `""` (ref) / `"ZB"` (zb) | `MACHINES` |
| 2 | `decode_raw()` added (UNSTRIPPED rows); `decode()` becomes a strip over it | module scope |
| 3 | `echo_missing(raw_rows, lines, prompt)` ported **with its docstring** | module scope |
| 4 | `run_case` runs the guard **before any value is read off the screen**; on failure returns `"MANGLED"` and appends `NOT ECHOED: …` to the row dump | `run_case` |
| 5 | `main()` checks `MANGLED` **first** — before oracle drift, before comparison | `main` |
| 6 | `--line-delay` (default **4.5**, the current cadence) plumbed to `build_tcl` | `main`/`build_tcl`/`run_case` |

Item 6 exists so the guard can be shown to **cut**; the lof probe keeps its knob
for the same reason. The default is unchanged, so the probe's cadence — and
therefore every number it reports — is unchanged.

### 2.1 Why the guard is shaped the way it is (do not re-derive)

Matching is done **with all whitespace removed**, against every single row and
every run of 2–3 consecutive rows, and **anchored on the prompt with an exact
match**. The three wrong versions:

* comparing against full 32-cell name-table rows flags rows with **perfect
  screens** — Disk BASIC boots SCREEN 1 at `linlen=$1d` = **29 columns**, so a
  30-character line wraps and the unused cells land between the halves;
* slicing rows to `linlen` is **also** wrong — the reference indents SCREEN 1 by a
  **left margin of 2** (C-BIOS uses 1), so `r[:29]` truncates every full-width line;
* squeezing whitespace fixes both, but a plain **substring** test then *passes*
  `ZBPPRINT LOF(1)`, because `PRINTLOF(1)` is still inside it. **A guard against
  DROPPED text is not a guard against INSERTED text.** Hence the prompt anchor
  and the exact match.

## 3. Ordering, and why it is load-bearing

`MANGLED` is checked **before** the oracle comparison and before the two-machine
comparison, for two independent reasons:

* two mangled sides **compare equal** and would print `agree`
  (memory: `gate-can-be-green-while-measuring-nothing`);
* a mangled *reference* row would otherwise be reported as **`ORACLE DRIFT`** —
  which is loud, but attributes the failure to the CF-3300 rather than to the
  typing. Attribution is the point of the item.

`MANGLED` is **fatal unconditionally** (exit 3). This probe has no `--gate` flag;
it is always a gate.

⚠️ **And the derived answer is SUPPRESSED, not printed-then-ignored.** The
per-channel slope, the ceiling and the `HEADLINE` are computed from the `mf*`
ladder. A slope derived from a mangled ladder is a number the run never measured,
and printing it would be exactly the failure mode this item exists to close. On
any mangled row the run prints the table, names the mangled rows, and returns 3
**without** printing a slope, a ceiling or a headline.

## 4. Controls — what this change must NOT move

The change is apparatus-only, so the whole readout is the control. Pinned
explicitly, because a cell pinned as a control *because it agrees* is what caught
D-BADFNUM's regression:

* **39 cases**, unchanged — no case is added, removed or shortened;
* `REF_EXPECT` reproduces on **every** row — 0 oracle drift;
* **0 unfiled divergences**; `KNOWN_DIVERGE` stays **EMPTY** (asserted in words:
  it is not to gain an entry as a way of accommodating a red row);
* both machines: per-channel, **linear**, **ceiling 15**; headline
  267 B/channel (ref) and 50 B/channel (zb);
* the `--line-delay` default stays **4.5**, so the cadence — and every reading —
  is byte-for-byte the pre-change run.

If any of those move, the port broke something and the port is wrong.

## 5. Pre-committed decision rules for a RED row

⚠️ The brief for this session predicts red rows: chancost runs at the cadence
where mangling was *measured*. **A red row is the guard working.** But every red
row must be **attributed**, never accommodated. Decided in advance so the decision
is not made under pressure of a failing gate:

* **(A) red once, green on re-run at a higher `--line-delay`** → real mangling,
  guard correct, no probe change. Record it.
* **(B) red reproducibly with a visibly PERFECT screen** (`-v`) → the guard is
  wrong or the case **scrolled off**. See §5.1. Fix the cause.
* **(C) red reproducibly with visibly mangled text** → the guard is right and
  4.5 s is not safe for that row. Then the **default cadence rises** for the whole
  probe and the doc says so. A gate that needs re-runs to go green is not a gate.
  ⚠️ Raising the cadence changes nothing about the *readings* (§4 still holds);
  `FRE(0)` does not depend on typing speed.
* **(D) NEVER**: loosen the match, add a per-row exemption list, drop the prompt
  anchor, make `MANGLED` non-fatal, or move a row into `KNOWN_DIVERGE`.

### 5.1 The scroll-off risk — chancost-specific, NOT covered by the lof material

`echo_missing` assumes **nothing scrolls off**; the lof probe holds that by
keeping every case ≤ 5 typed lines. chancost has ten cases that type a 5-line
program **and then `RUN` it**, on top of the CF-3300's boot banner and its date
prompt. If an early echo has scrolled off the top of the 24-row screen, the guard
reports `MANGLED` on a row whose screen was perfect — the identical failure mode
to the guard's first two versions.

This is **measured, not assumed**: the `-v` screen dump distinguishes the two
cases immediately (scrolled-off = the echo is simply absent while everything after
it is clean and the answer is correct; mangled = the corrupted text is visible).
If it occurs, the fix is to the **case or the screen**, not to the guard —
options, in preference order: (i) accept, if in fact nothing scrolls; (ii) `CLS`
is not available before the boot banner, so shorten the case's typed lines; (iii)
if neither works, the row is recorded as outside the guard's reach **in the probe
and in this spec** — an honest hole beats a guard that lies.

## 6. Falsification — both halves, before believing it

⚠️ **A ported guard that has never been shown to cut is decoration.** Two knives,
both required:

* **K1 — the DROPPED half, end to end.** Re-run a small `--only` subset at a
  deliberately short `--line-delay` (≈1.5 s) and show rows go **MANGLED**, with
  the `-v` dump showing genuinely truncated echoes. Control: the same subset at
  the 4.5 s default is **green**.
* **K2 — the INSERTED half, deterministically.** A scratch script imports
  `echo_missing` and feeds it three synthetic screens: (a) a doubled-character
  row (`ZBPPRINT FRE(0)`) → must be **RED**; (b) a clean unwrapped row → **GREEN**;
  (c) a **wrapped** reference echo of a >29-character line split across two rows,
  with the left margin present → **GREEN**. (a) is the case the "working" version
  still passed; (c) is the case versions 1 and 2 wrongly failed. A knife whose
  subject and control read the same is not a measurement, so (a) and (b) are
  reported together or not at all.

Additionally, the **prompt anchor is verified, not assumed**, from a `-v` run of
both sides: the reference's echo row must squeeze to exactly the typed line, and
zerobas's to `"ZB"` + the typed line. The lof probe established this on the same
two machines, but chancost types different lines (`RUN`, program lines) and the
claim is re-checked here rather than inherited.

## 7. Gate

Python-only change; only the affected probe's gate is due (the precedent set by
D-RNDDIR, which ran `make lof-acceptance` alone for a probe-only change and said
so).

```
make chancost-characterize
```

Required: **39 cases · 0 oracle drift · 0 unfiled divergence · `KNOWN_DIVERGE`
EMPTY · 0 mangled · both machines per-channel/linear/ceiling 15.**

No `rm -rf build` and no wall measurement: no ROM byte moves. `make
chancost-characterize` already depends on `repack-machine`, so the installed
machine is current when the probe runs.

## 7.1 BEYOND THE SIGNED-OFF SCOPE — found by the gate this item installed

Added after sign-off, and called out rather than folded in silently.

The second full run came back **`lof_new` reference = `None` → `ORACLE DRIFT`**.
Re-run: a clean **0** with a perfect screen. So it was not a reading — and the
guard had not fired, because `run_case`'s **TIMEOUT** and **NO CAPTURE** paths
return *before* the guard runs, both returning `None`. `None` is also what a clean
screen with no number on it reads as.

⚠️ **A sentinel that also means "no reading" is not a measurement.** A run that
never finished arrived at the verdict column wearing the same face as a reading,
and was then reported as `ORACLE DRIFT` — **blaming the CF-3300 for the host**.
That is the identical defect class this item exists to close, one layer further
out, so it is fixed here rather than filed: both paths now return the distinct
markers `TIMEOUT` / `NOCAPTURE`, handled exactly like `MANGLED` (fatal, exit 3,
derivation suppressed) under the verdict `RUN FAILED`.

**K3 — falsified.** Subject: `ZEROBAS_BASIC_MACHINE=No_Such_Machine_XYZ … --only
lof_new --side zb` → `NOCAPTURE`, `RUN FAILED`, derivation suppressed, **exit 3**.
Control: the identical command with the real machine → **`0`, exit 0**. `TIMEOUT`
shares the marker path with `NOCAPTURE` and is falsified through it.

⚠️ **The deadline itself is left alone at 200 s.** Which of the two paths fired on
that run is not known — the run had no `-v` — and raising a timeout to fix a
failure not yet attributed to timing would be a guess. With the markers in place
the next occurrence names itself, which is the point.

## 8. Out of scope

* The `MAXFILES=16` error-class defect (ERR 5 vs ERR 2), gated by the `mf16`/
  `mf255` rows in this very probe. It is the next item and it touches ROM at a
  23 B low wall; it is not smuggled in here.
* Any other probe. `diskbasic_probe_lof.py` is the source and is not modified.
