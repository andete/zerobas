# The program-written MARK: an emulated-time stopwatch, and a capture trigger

`probes/lib/omsx_repl.py` (`sentinel=`, `sentinel_capture=`, `settle_out=`)
· `probes/lib/probe_signal.py` (the shared plumbing)
· see also `docs/spec-probe-budget.md` §6, `TODO.md`

⚠️ **THIS FILE WAS REFERENCED BEFORE IT EXISTED.** `omsx_repl.py` and
`spec-probe-budget.md` §6 both cited it while the mechanism was documented only
in the source and in `TODO.md`. Written 2026-08-25 when a third adopter
(D-SNCAP2) made the dangling reference load-bearing.

## 1. What the mark is

A case's own BASIC writes a byte to a chosen RAM address:

    POKE &HE000,255

openMSX watches that address (`debug set_watchpoint write_mem`) and reports the
exact **emulated** instant of the write.

🔴 **THE CLEAN-ROOM RULE IS WHY THIS SHAPE, AND IT IS NOT A COMPROMISE.**
Breakpoints on *reference-ROM internals* are forbidden, which for years became
"completion cannot be detected", hence fixed-time schedules everywhere. But the
PROGRAM can announce its own completion. This watches emulated **RAM**, so it
needs no ROM knowledge on any machine — it works identically on a black-box
VG-8020, a CF-3300 and on zerobas.

## 2. The two uses

**A. STOPWATCH (`sentinel=` alone).** Every write is logged as
`(emulated instant, value)` into `settle_out["marks"]`. Marks either side of an
operation give its duration.

🟢 **Emulated time is DETERMINISTIC** — measured bit-identical across repeats
(14.736728 s twice, 46.252527 s twice). It is the only basis on which a
performance differential can be gated without flaking; wall clock (±0.2 s here,
and worse under the host stall in `TODO.md`) never can.

**B. CAPTURE TRIGGER (`sentinel_capture=True`).** The capture happens when the
program signals, and the scheduled budget becomes a pure **FAILURE DETECTOR** —
it fires only if the case never signalled at all. `settle_out["sentinel"][i]` is
the instant it captured; `settle_out["fallback"][i]` says the budget captured
instead.

🔴 **B IS NOT SOLD ON SPEED, AND MUST NOT BE.** Deterministic recomputation over
the six error-shaped gates converted in D-SNCAP2: **71 104 → 63 927 emulated s,
−10.1 %** ≈ 21 s of wall at the flat 0.003 s/emulated-second rate
`spec-probe-budget.md` §5 measured. In the environment that measured it, the
emulator-free warm-up control moved 7 s → 14 s between the before and after
batteries, and two *identical* converted runs of the same battery differed by
59 s. Both dwarf the effect. The value is that a fixed-time budget **captures a
half-finished machine, and a partial result reads as SEMANTICS**.

## 3. The four rules that decide whether a site can be converted

1. ⛔ **BATCHED MATRICES CANNOT BENEFIT.** With `batch=True` the later cases are
   scheduled at FIXED emulated instants and the generated Tcl only exits early on
   the LAST case. Convert `batch=False` (boot-per-case) sites only.

2. ⛔ **A CASE THAT RAISES NEVER REACHES ITS POKE.** It falls back to the budget:
   no saving, no harm. Measured — a graphics `ONERRORGOTO` row falls back at
   113.0 emulated s. Such rows should pass **no sentinel at all**, so they are not
   counted as fallbacks either; a fallback must mean something.

3. 🔴 **A LAYOUT-SENSITIVE READOUT CANNOT TAKE A MARK IN ITS OWN PROGRAM.**
   Learned on the third gate, not designed in. The mark is BASIC TEXT: it makes
   the tokenised program ~8 bytes longer per marked line, `VARTAB` sits directly
   above the program text, so **every reading that IS a RAM address moves by
   exactly that much**. `basic_probe_deffn.py`'s five `ADDR` rows report
   `VARPTR`s; marking them shifts `z.addr.ctl` and `o.sameaddr`. Neither is
   gated, so it would not have gone red — it would have quietly moved a recorded
   characterization number to accommodate the instrument, which is worse. Ask of
   every readout: **does it name a place, or a value?**

4. ⚠️ **A `capture="screen"` ROW CARRIES A BURDEN** (§4).

📏 **AND THE MARK IS NOT FREE EVEN WHEN ALL FOUR PASS.** `POKE&HE000,255` is 15
characters. `screenerr`'s printing line goes 36 → 51, past the 38-char KEYBUF
chunk boundary, buying an extra typing slot: its reclaim is **−5.1 %** against
−11 to −13 % on the gates where the line still fits. Check the length.

## 4. The `capture="screen"` burden (the refusal that was lifted)

The blanket refusal for text captures was lifted 2026-08-25 (user decision). The
measurement behind it **stands**: a screen captured at signal time is missing the
`Ok`/`ZB` prompt — exactly 2 characters, on all three machines — which is also
the proof the sentinel fired.

🔴 Those 2 characters are the one thing every text readout already throws away.
So the ban became a burden: **a probe converting a screen-captured row must show
ITS OWN readout is prompt-independent.**

| readout | prompt-independent? | why |
|---|---|---|
| `omsx_repl.result_span` | ✅ | the text between the LAST `[` and its `]`; neither prompt is a bracket |
| `basic_probe_deffn.face` | ✅ | the FIRST such span, else a closed set of `err_msgtab` messages |
| `basic_probe_graphics._answer` | ✅ | its own docstring says it ignores the trailing prompt |
| `omsx_repl.screen_tail` | ⛔ | **TERMINATES AT the prompt** — never convert a row that reads through it |

## 5. Verifying an adoption — the check with teeth

🔴 **THE TALLY CANNOT MAKE THIS CHECK.** A fallback proves a mark was never
REACHED. Nothing in the tally would catch a mark placed too **EARLY** — that
captures a half-finished machine on BOTH sides and can agree wrongly, which is
precisely the failure the budget existed to prevent, now firing deterministically
instead of occasionally.

The protocol, per gate:

1. run the probe BEFORE the change, save the output;
2. convert, run again;
3. **diff the report rows** — they must be identical. `scratchpad/sncap/rowdiff.py`
   does it through `probe_report.parse`, so a layout change cannot silently turn
   it into a line differ, and it is itself teeth-checked against a mutated log;
4. confirm the tally shows the expected number on signal;
5. `make gates` before committing.

🔬 **AND THE ADOPTION MUST BE VISIBLE OR IT IS UNFALSIFIABLE.** A case whose
sentinel never fires falls back and passes IDENTICALLY, so a green gate says
nothing about whether capture-on-signal is happening at all. Every converted
probe prints `probe_signal.Tally.line()`.

🔴 **AND THE TALLY MUST NAME ITS MISSES.** The first converted `deffn-strict`
printed `1 fell back` out of 72 and could not say which row; the gate had to be
re-run to find out. `Tally.add(label=...)` now names them. (It was
`o.clearwipe3`: its `CLEAR` wipes the `ON ERROR` handler along with the DEF FN
table, so the row aborts untrapped and reaches neither `END` — rule 2, behaving
exactly as designed, and the tally is the only thing in the tree that could have
said so.)

## 6. Adoption record

| date | subject | on signal | fell back | verified by |
|---|---|---|---|---|
| 2026-08-25 (D-SNCAP) | `graphics-acceptance`, all 14 boot-per-case phases | 321 | 0 | 395 row values, byte-identical |
| 2026-08-25 (D-SNCAP2) | `penderr` `screenerr` `stmtpend` `tmfp` `lineerr` `deffn-strict` | 1344 | 1 (named, explained) | 557 report rows across 13 reports, byte-identical |

⛔ **Deliberately unconverted:** every `batch=True` matrix (`array`, `math`,
`float`, and graphics phases B/D/F/J/L/M/O/Q2) — rule 1;
`interval-trap-acceptance`, which does not go through `run_cases` and whose
subject IS emulated timing; the untrapped and cold-boot rows of the six
error-shaped suites — rule 2 and the `screen_tail` burden; `deffn`'s `ADDR`
rows — rule 3.
