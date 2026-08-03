# `graphics-acceptance` delivery characterisation — every reading, D-DELIVER

Companion to [`docs/spec-probe-delivery.md`](spec-probe-delivery.md). Everything
below was measured on `4243343` (tree clean, `make -q build/zerobas-main-eu.rom`
exit 0, `make repack-machine` run first). Reference `Philips_VG_8020`, subject
`C-BIOS_MSX1_EU_REPACK_DISK`.

---

## 1. The baseline

```
make graphics-acceptance     290 rows, 2 FAIL, exit 2, 3 m 20 s

FAIL  put_pat64_16   ref='ZE 5'      zb=None
FAIL  rd_base_s0     ref='ZK 6144'   zb='ZE 5'
```

Both rows live in a batched phase built on the same four-line shape:

```
10 ON ERROR GOTO 40
20 <statement under test>
30 SCREEN0:PRINT"ZK"[;A]:END
40 SCREEN0:PRINT"ZE";ERR:END
```

`put_pat64_16` is phase O case **22** (`SPRITE_BEHAV`), `rd_base_s0` is phase Q2
case **12** (`G8_BEHAV`).

## 2. Isolation — the ROM answers correctly

Boot-per-case (`batch=False`), both machines:

| case | ref | zb |
|---|---|---|
| `SCREEN2,2:PUT SPRITE 0,(10,20),4,64` | `ZE 5` | `ZE 5` |
| `SCREEN2,2:PUT SPRITE 0,(10,20),4,63` | `ZK` | `ZK` |
| `SCREEN2:PUT SPRITE 0,(10,20),4,256` | `ZE 5` | `ZE 5` |
| `SCREEN0:A=BASE(10)` | `ZK 6144` | `ZK 6144` |

So `PUT SPRITE`'s 16×16 pattern domain and `BASE(n)`'s mode-independence
([`spec-basic-graphics-g7.md`](spec-basic-graphics-g7.md) §, 
[`spec-basic-graphics-g8.md`](spec-basic-graphics-g8.md) §4.1) are both intact
and neither needed a line of code.

⚠️ **A confounded row I wrote and kept.** `cp_64_16b` put `SCREEN2,2` on its own
line, which renumbered the reporting lines and left `ON ERROR GOTO 40` pointing
at the **`ZK`** line — so it read `ZK` on both machines and carried no
information. Recorded rather than deleted [[row-with-two-candidate-causes]].

## 3. What the blank capture actually is

`zb=None` means `_outcome` found no tag. The raw capture for that case is
**960 bytes of `$00`** — not `$20`. In SCREEN 0 a cleared name table is `$20`;
`$00` at VRAM `$0000` is the **SCREEN-2 pattern generator table**, which
`SCREEN 2` zeroes. So the machine was still in SCREEN 2 when the capture fired,
and the case never reached its `SCREEN0:PRINT` line.

Reading the SCREEN-2 **name** table (`$1800`) at the same moment showed it
pristine (the default `0,1,2,…,255 ×3`), i.e. no error message had been printed
on the graphics screen either.

🔴 Two apparatus facts fall out of this and are worth carrying forward:

* **The SCREEN-0 scrape is structurally blind to a machine left in a graphics
  mode**, and `_outcome`'s abort guard with it: the docstring's reasoning ("a
  case that ABORTS never reaches SCREEN0, leaving the program echo up") holds
  only in text mode. In SCREEN 2 the echo is at `$1800` and the scrape reads
  `$0000`. [[readout-blind-to-its-own-subject]]
* **`$00` and `$20` both render as blanks.** The decoded string cannot tell them
  apart; only the raw hex can. A probe that reasons about "a blank screen" is
  reasoning about two different machine states.

## 4. What the machine stored

Walking the line-link chain from `TXTTAB` immediately before each case's `RUN`,
in the same batches that produce the reds:

| batch | case | index | typed | stored |
|---|---|---|---|---|
| phase O | `put_pat64_16` | 22 | 10,20,30,40 | **20,30,40** |
| phase Q2 | `rd_base_s0` | 12 | 10,20,30,40 | **10,20,40** |
| phase Q2 | `wr_v255fr` | 22 | 10,20,30,40 | **20,30,40** |
| phase M | `SCREEN2:DRAW"B"` | 22 | 10,20,30,40 | **20,30,40** |
| all other cases, both batches | — | — | 10,20,30,40 | 10,20,30,40 |
| every case, `Philips_VG_8020` | — | — | 10,20,30,40 | 10,20,30,40 |

That is the entire defect, and it explains both readings exactly:

* **Lose line 10** → the ERR 5 is untrapped → RUN aborts in SCREEN 2 → §3.
* **Lose line 30** → line 20 falls through into the handler → it prints
  `"ZE";ERR`, and `ERR` still holds **5** from the preceding case `rd_baseneg`
  (`SCREEN2:A=BASE(-1)`). D-PREFLIGHT's filed guess that `'ZE 5'` "is the
  neighbouring row's answer" is *literally correct*, by a mechanism nobody
  guessed. A right conclusion from a wrong model still has to be re-derived.

🎯 **Three of the four losses are at index 22** — the 23rd case of a batch — in
three unrelated phases. Strongly positional, but see §5.

## 5. It is an alignment race

| experiment | result |
|---|---|
| full phase-O batch (35 cases) | case 22 mangled |
| slice `[11:24]` (13 cases, same predecessors) | clean |
| 11 harmless fillers + slice `[11:24]` | case 22 mangled again |
| 6 fillers + slice `[11:24]` | clean |
| 22 fillers + the 2 real cases (target at index 22) | **clean** |
| `step=5.0`, 11 fillers + slice | clean |
| 30 identical filler cases, `step=2.5`, zb | **1 mis-delivery** |
| 30 identical filler cases, `step=1.2`, zb | 0 |
| 30 identical filler cases, `step=0.7`, zb | 1 |
| the same three, `Philips_VG_8020` | **0, 0, 0** |

So neither position alone nor predecessor content alone accounts for it; both
shift the alignment. Raising `step` moves the race, it does not remove the class
— and note the rate at the **default** `step=2.5` on a batch of thirty identical
harmless cases: **one in thirty**.

## 6. 🔴 Both hypotheses about the injector are wrong

`omsx_repl`'s own docstring names the suspect: "each `__key` call resets
GETPNT/PUTPNT, so lines delivered mid-operation collapse into one". Instrumented
**in the same run that reproduced the fault** (the reproduction was checked, not
assumed — [[knife-runner-false-negatives]]):

| check | result |
|---|---|
| KEYBUF drained (`GETPNT == PUTPNT`) before every injection | **490 / 490 yes** |
| `GETPNT == KEYBUF` after every injection | **490 / 490 yes** |
| case 22's capture in that run | all-`$00` — the fault reproduced |

So all 20 characters of `10 ON ERROR GOTO 40` were written, the pointers were
correct, and the openMSX `after time` callback is atomic with respect to the
emulated CPU. **Nothing was lost in the injector.** The tempting
"GETPNT-written-before-PUTPNT leaves a transient non-empty buffer" story is
refuted by the second row of that table.

What the screen says, 0.02 s of emulated time after that injection:

```
 ZBN ERROR GOTO 40
 Syntax error
```

against the passing neighbour's

```
 ZB10 ON ERROR GOTO 40
```

The machine consumed the first **four** characters (`10 O`) without echoing
them; the MSX screen editor then read `N ERROR GOTO 40` back off the screen and
BASIC rejected it. Four is also the length of the preceding injection (`CLS`+CR)
— suggestive, **not** established.

## 7. What it is NOT

A deliberate type-ahead differential: type a line *while* a program prints
(`10 FORI=1TO1200:PRINT"X";:NEXT`) and again while it spins silently
(`10 FORI=1TO1200:NEXT`), then let it finish.

| machine | silent loop | printing loop |
|---|---|---|
| `C-BIOS_MSX1_EU_REPACK_DISK` | typed line survives and executes | survives |
| `Philips_VG_8020` | survives | survives |

So zerobas does **not** systematically drop type-ahead, and the loss is not the
print path eating the buffer. The floor of the race is **not established**; the
guard makes the class unmissable rather than impossible. [[apparatus-is-part-of-the-measurement]]

## 8. After the guard

`make graphics-acceptance` → **290/290, exit 0, 2 m 58 s**. Row-by-row diff
against the baseline — exactly two rows moved, to exactly the predicted values,
and nothing else:

```
186c186
<   FAIL put_pat64_16   ref='ZE 5' zb=None
>   PASS put_pat64_16   ref='ZE 5' zb='ZE 5'
241c241
<   FAIL rd_base_s0   ref='ZK 6144' zb='ZE 5'
>   PASS rd_base_s0   ref='ZK 6144' zb='ZK 6144'
```

🎯 **The same four cases fire in every run** — openMSX is deterministic, so the
race is too, which is exactly why it read as semantics rather than as flake
[[deterministic-mangle-is-still-a-mangle]]. Confirmed on two full gate runs.

The run announced **four** mis-deliveries — the two red rows plus `wr_v255fr`
and `SCREEN2:DRAW"B"`, which had been **passing vacuously**: both are value rows
that never raise, so the `ON ERROR GOTO 40` they lost was never reached. The
gate could not have told anyone; the guard could.

## 9. Knives

Every cut was verified to have *cut* before its verdict was read.

| knife | cut (verified) | predicted | measured |
|---|---|---|---|
| **K1** | `prog.N=` emission deleted (`'prog.0=' in tcl` → False) | the two rows RED, byte-identical to the filed reading | `put_pat64_16 ref='ZE 5' zb=None`, `rd_base_s0 ref='ZK 6144' zb='ZE 5'` — **identical**; all other rows green |
| **K2** | emission and call kept, `mis_delivered` gutted to `return []` (both verified) | same two rows, same values | **same two rows, same values** |
| **K3** | detection kept, repair replaced by `pass` | the two rows RED but **attributed** | RED, with `MIS-DELIVERED case 22` (phase O) and `case 12` + `case 22` (phase Q2) on stderr |
| **K4** | positive control, 30 filler cases at three step values | fires and repairs; verdicts unchanged | fired 1× at `step=2.5`, 0× at `1.2`, 1× at `0.7`; **all 30 verdicts `ZE 5` in every run** |
| **K5** | zero-RED: the same three runs on the reference | **zero** fires | **0, 0, 0** — and the zb half of the identical batch fired |

K2 is the one that matters most: the emission was present, the call was present,
`preflight`-style coverage would have called it wired in — and the incident
returned verbatim. **Coverage is not efficacy**
[[coverage-gate-cannot-see-a-gutted-guard]].

K5 was written as a zero-RED knife on purpose
[[knife-that-reddens-nothing-is-the-finding]]: a guard that fired on the
reference would be measuring something other than the class §4 identified.

## 10. Open

* **The floor of the race** (§6). Characterised, not explained.
* **`direct`-mode delivery is unguarded** — there is no stored program to
  interrogate, so the same race in a `direct`-mode matrix still reads as a value.
  Given the §5 rate at the default step, this is not hypothetical.
* **Vacuous rows.** `wr_v255fr` and the phase-M `DRAW"B"` row passed while
  missing their error handler. Not enumerated
  [[gate-can-be-green-while-measuring-nothing]].
