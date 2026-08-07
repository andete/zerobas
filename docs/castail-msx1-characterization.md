<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-CASTAIL — what an MSX1 prints AFTER `RUN"CAS:x"` / `LOAD"CAS:x",R`

Measured 2026-08-07 on the **Philips VG-8020** *and* the **National CF-3300**
against zerobas at `3e84afa`, by
[`probes/basic/basic_probe_castail.py`](../probes/basic/basic_probe_castail.py)
(`make castail-characterize`). Spec: [spec-basic-castail.md](spec-basic-castail.md).

This is the reference reading the [spec-basic-runtail.md](spec-basic-runtail.md)
§9 residual was blocked on: *"this battery has no cassette instrument and does
not read them."* **Nothing had ever measured what a reference prints after a
tape program load.**

## 0. 🟢 Why the VG-8020 **is** a side here, unlike the disk battery

[runtail-msx1-characterization.md](runtail-msx1-characterization.md) §0 refuses a
VG-8020 column because `RUN"A:name"` needs a **disk interface** and a diskless
MSX1 answers `Syntax error` — a column measuring the absence of hardware.

`RUN"CAS:x"` needs a **cassette port**, which every MSX1 has, including the
VG-8020. So the decision is the opposite one, and it is made explicitly rather
than inherited: **the VG-8020 is a full side of this battery.** Its value is not
politeness. The CF-3300 boots into Disk BASIC, and a reading taken only there
cannot say whether an answer is the MSX1 rule or a property of one machine's
disk ROM. **The two references agree row for row on all ten readings below**,
which is what promotes the reading from "what a CF-3300 does" to "what an MSX1
does".

## 1. The reading, all three sides, pre-fix

Every row is the **whole tail** of the subject command — the rows between its
echo and the next prompt-or-echo — not a substring. `<nothing>` = the machine
printed nothing. `<load-failed>` = the tail was **exactly** the side's own
aborted-load message (`Device I/O error` on both references, `load error` on
zerobas): the wording divergence `basic/PROVENANCE.md` quarantines for the whole
no-disk / mount / I-O class, normalised to one token so these rows can be scored
on **shape**. The two tape-search progress rows are dropped and pinned instead —
§5.

| row | typed | VG-8020 | CF-3300 | zerobas @ `3e84afa` |
|---|---|---|---|---|
| `cas-run-hit` 🟢 | `RUN"CAS:RT"` | `ZQ9` | `ZQ9` | `ZQ9 / Illegal function call in 3346` |
| `cas-run-hit-res` | `10 PRINT"ZQ1"` / `RUN"CAS:RT"` | `ZQ9` | `ZQ9` | `ZQ9 / Illegal function call in 3346` |
| `cas-loadr-hit` | `LOAD"CAS:RT",R` | `ZQ9` | `ZQ9` | `ZQ9 / Illegal function call in 3346` |
| `cas-run-brk` | `RUN"CAS:NOSUCH"` + Ctrl-STOP | `<load-failed>` | `<load-failed>` | `<load-failed> / Illegal function call in 3346` |
| `cas-run-brk-res` | `10 PRINT"ZQ1"` / `RUN"CAS:NOSUCH"` + Ctrl-STOP | `<load-failed>` | `<load-failed>` | `<load-failed> / ZQ1 / Illegal function call in 3346` |
| `cas-loadr-brk-res` | `10 PRINT"ZQ1"` / `LOAD"CAS:NOSUCH",R` + Ctrl-STOP | `<load-failed>` | `<load-failed>` | `<load-failed> / ZQ1 / Illegal function call in 3346` |
| `bare-run` 🟢 | `10 PRINT"ZQ1"` / `RUN` | `ZQ1` | `ZQ1` | `ZQ1` |
| `cas-load-plain` | `10 PRINT"ZQ1"` / `LOAD"CAS:RT"` / `LIST` | `<nothing>` | `<nothing>` | `<nothing>` |
| `cas-load-plain:listing` 🟢 | (the `LIST` above) | `10 PRINT"ZQ9"` | `10 PRINT"ZQ9"` | `10 PRINT"ZQ9"` |
| `cas-load-plain:search` 📌 | (the `LOAD` above, UNFILTERED) | `Found:RT` | `Found:RT` | `<nothing>` |

`3/9 agree` (the pinned row is not an agreement row). 🟢 = a **positive
control**: its agreed reading carries program output (`ZQ9` / `ZQ1`) or a
listing, so the battery is not satisfied by three dead machines. All three held
on all three sides, which is what makes the six DIFFs measurements rather than
an instrument reading. 📌 = the pinned divergence, §5.

## 2. R-CT1 — the reference prints NOTHING after a successful tape `RUN`

`RUN"CAS:RT"` on both references prints `ZQ9` — the loaded program's own output
— and then `Ok`. **zerobas appends `Illegal function call in 3346`.**

This is [runtail-msx1-characterization.md](runtail-msx1-characterization.md)
§2's R-RT1, *on the tape verbs*, and it is the same mechanism to the byte: §6
there traces `3346` = `$0D12` = the word at `$0002`, printed as `CURLINE+2`
after the enclosing run loop walked off into `CURLINE := $0000` and dispatched
page-0 ROM as BASIC. `basic/cload.asm`'s `dr_is_cas` and `dl_cas_close` end in
the identical `jp run_prog` from a **statement** context that `do_run`'s disk arm
did.

⚠️ **This is a shipped verb's SUCCESS path, and it has been divergent for the
whole life of the tape verbs.** `basic_probe_cas_verbs.py`'s `RUN"CAS:"` tests
could not see it: they assert a **witness byte** (`$D0FF` → `$99`), which the
program sets before the stray message is printed. A memory witness cannot see an
extra screen row.

## 3. R-CT2 — `LOAD"CAS:x",R` is the same verb, and diverges identically

`cas-loadr-hit` and `cas-loadr-brk-res` read exactly what their `RUN"CAS:"`
twins read on all three sides. As on disk, the rule is not `RUN`-token-specific.

## 4. R-CT3 — the reference does NOT run the resident program after a failed tape load

`cas-run-brk-res` and `cas-loadr-brk-res` type `10 PRINT"ZQ1"` first, then abort
the tape read. Both references print their message and stop: **`ZQ1` never
appears.** zerobas prints its message, then **runs the resident program**
(`ZQ1`), then the stray error — `do_tape_prog`'s failure exits `jp load_error`,
`load_error` prints and **returns**, and the next instruction at both call sites
is `jp run_prog`. Defect B of [spec-basic-runtail.md](spec-basic-runtail.md) §2,
verbatim, on the tape path.

🔴 **AND THE `-res` ROWS ARE THE ONLY ONES THAT CAN SEE IT.** `cas-run-brk` — the
same abort with **nothing** resident — reads `<load-failed>` on the references
and `<load-failed> / …` on zerobas, and the difference there is defect **A**
alone. With defect A fixed, that row would agree on all three sides *whether or
not* zerobas refuses to run, because running an **empty** program is silent.
Measured under two knives in D-RUNTAIL and recorded as
[[an-empty-program-hides-a-wrong-run]]; the row set here was built from that
lesson rather than re-learning it.

## 5. 📌 R-CT4 — a NEW divergence, found by building the instrument: no tape-search progress line

Both references print the BIOS tape-search progress row before anything else:

* `Found:RT` — the search took this file;
* `Skip :RT` — the search stepped over this file (a name that did not match).

**zerobas prints neither**, on any row. Nothing in `basic/PROVENANCE.md` or
`TODO.md` recorded this; the closest entry
([dotgaps-msx1-characterization.md](dotgaps-msx1-characterization.md) §1.2)
mentions `Found:` only as the reference row whose *absence* proves a hang.

It is a divergence of the **search**, not of what the verb does after the load,
so scoring it inside every row would DIFF all six subject rows for a reason none
of them is asking about. The probe therefore drops those two exact strings from
every scored tail — **and pins them**: `cas-load-plain:search` reads the same
`LOAD` line unfiltered and holds all three sides' readings verbatim, so the
filter cannot hide the thing it removes.

⚠️ **The filter only ever fires on a reference.** A normalisation that is a no-op
on the side under test is a normalisation that blesses one machine's silence
([[readout-blind-to-its-own-subject]]), and the pin is what makes it a
measurement instead. Filed as a residual in `TODO.md`; **not** fixed here.

## 6. 🎯 The only tape failure a reference can be asked about is Ctrl-STOP

This is the design constraint the whole failure half of the battery turns on,
and it is a measurement, not a preference.

A **missing tape file is not an error on an MSX1.** The BIOS searches forward by
name; a name that never matches means it searches past the end of the tape and
**waits on silence forever**. Independently measured for the type mismatch in
[dotgaps-msx1-characterization.md](dotgaps-msx1-characterization.md) §1.2
(`LOAD"CAS:"` on a `$D3` tape *"printed no `Found:` line and no error and sat
there"*), and it is the same search. So:

* there is no `<file-missing>` row on tape — the disk battery's `run-miss` has no
  tape twin, because the reference has no answer to print;
* the only failure a reference **reports and returns from** is an operator abort:
  Ctrl-STOP during the search → `Device I/O error`;
* which makes Ctrl-STOP the only shape in which *"did the resident program run
  afterwards?"* is a question a reference can answer at all.

Delivered with `omsx_repl`'s `@BREAK` pseudo-line (CTRL row 6 bit 1 + STOP row 7
bit 4 via `keymatrixdown`; KEYBUF injection cannot deliver Ctrl-STOP because it
is not a character). The abort lands inside a ~12 s search window, so its timing
is not delicate — and the readings are stable at `--repeat 2` on every side.

## 7. 🎯 The instrument already existed, and §9 was wrong about that

[spec-basic-runtail.md](spec-basic-runtail.md) §9 filed the blocker as
*"`omsx_repl.run_cases` mounts a disk, not a `.cas`"*. That is true of its
**signature** and false of the **module**: the `prologue` seam (input-devices arc
I2) runs raw Tcl before the timeline, and `basic_probe_lnblank`'s `cld` rows
already mount a tape with `cassetteplayer insert {file}`. No library change was
needed for the mount at all — what this battery adds is the tape **fixture** and
the per-row `@WAIT` budget.

⚠️ **The fixture is `$EA` ASCII, and the reference forces that.**
`LOAD"CAS:"`/`RUN"CAS:"` on a real MSX search for an **ASCII** file and skip a
tokenised (`$D3`) one — to the end of the tape, where they hang (§6). A `$D3`
fixture would therefore hang both references and gate nothing. zerobas accepts
both formats through its 3-way header dispatch, which is the separate divergence
already filed in `TODO.md` from D-DOTGAPS and **not** re-opened here.

## 8. What is NOT claimed here

* **The wording of the failure message is untouched.** `load error` vs
  `Device I/O error` is the quarantined divergence recorded in
  `basic/PROVENANCE.md`. Every row above normalises it away on purpose.
* **`CLOAD` / `CLOAD?` / `MERGE"CAS:"` are not measured.** `CLOAD` has no `,R`
  and reaches `do_tape_prog` by `jp`, so it consumes no return carry and has no
  defect A to fix; `CLOAD?` (verify) and `MERGE` are separate verbs with their
  own batteries. The CF contract in spec §3.2 nonetheless covers their exits —
  stated there as contract completeness, explicitly **not** as coverage.
* **The tokenised (`$D3`) tape path is not exercised by any row here**, for the
  reason in §7: the references hang on it. Its `ctp_done` / `ctp_oom` exits get
  the contract for completeness and no row scores them (spec §5, K-DONE-CAS is a
  **predicted miss**).
