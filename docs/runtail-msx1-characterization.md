<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-RUNTAIL — what an MSX1 prints AFTER `RUN"file"` / `LOAD"file",R`

Measured 2026-08-07 on the **National CF-3300** (the oracle for Disk-BASIC
words) against zerobas at `e98e77d`, by
[`probes/basic/basic_probe_runtail.py`](../probes/basic/basic_probe_runtail.py)
(`make runtail-characterize`). Spec: [spec-basic-runtail.md](spec-basic-runtail.md).

This is the reference reading the
[spec-fat-error-verb-control.md](spec-fat-error-verb-control.md) §8.6 residual
was blocked on. **Nothing had ever measured what the reference prints here.**

## 0. Why the VG-8020 is not a side

`RUN"A:name"` needs a disk interface. The Philips VG-8020 has no disk ROM and
answers `Syntax error` to every word in this battery, so a VG-8020 column would
measure the absence of hardware, not a language rule. The probe **refuses** a
`--sides vg8020` run rather than dropping it silently — the
`basic_probe_dskmsg` pattern.

## 1. The reading, both sides, pre-fix

Every row is the **whole tail** of the subject command — the rows between its
echo and the next prompt-or-echo — not a substring. `<nothing>` = the machine
printed nothing. `<file-missing>` = the tail was **exactly** the side's own
missing-file message (`File not found` on the CF-3300, `load error` on zerobas):
the wording divergence `basic/PROVENANCE.md` quarantines for the whole no-disk /
mount / I-O class, normalised to one token so these rows can be scored on
**shape** without re-opening it.

| row | typed | CF-3300 | zerobas @ `e98e77d` |
|---|---|---|---|
| `run-hit` 🟢 | `10 PRINT"ZQ9"` / `SAVE"A:RT.BAS"` / `NEW` / `RUN"A:RT.BAS"` | `ZQ9` | `ZQ9 / Illegal function call in 3346` |
| `run-miss` | `RUN"A:NOSUCH.BAS"` | `<file-missing>` | `<file-missing> / Illegal function call in 3346` |
| `run-miss-res` | `10 PRINT"ZQ1"` / `RUN"A:NOSUCH.BAS"` | `<file-missing>` | `<file-missing> / ZQ1 / Illegal function call in 3346` |
| `run-hit-res` | …`NEW` / `10 PRINT"ZQ1"` / `RUN"A:RT.BAS"` | `ZQ9` | `ZQ9 / Illegal function call in 3346` |
| `loadr-hit` | …`NEW` / `LOAD"A:RT.BAS",R` | `ZQ9` | `ZQ9 / Illegal function call in 3346` |
| `loadr-miss-res` | `10 PRINT"ZQ1"` / `LOAD"A:NOSUCH.BAS",R` | `<file-missing>` | `<file-missing> / ZQ1 / Illegal function call in 3346` |
| `bare-run` 🟢 | `10 PRINT"ZQ1"` / `RUN` | `ZQ1` | `ZQ1` |
| `load-plain` | …`NEW` / `10 PRINT"ZQ1"` / `LOAD"A:RT.BAS"` / `LIST` | `<nothing>` | `<nothing>` |
| `load-plain:listing` 🟢 | (the `LIST` above) | `10 PRINT"ZQ9"` | `10 PRINT"ZQ9"` |

`3/9 agree`. 🟢 = a **positive control**: its agreed reading carries program
output (`ZQ9` / `ZQ1`) or a listing, so the battery is not satisfied by two dead
machines. All three held on both sides, which is what makes the six DIFFs
measurements rather than an instrument reading.

## 2. R-RT1 — the reference prints NOTHING after a successful `RUN"file"`

`RUN"A:RT.BAS"` on the CF-3300 prints `ZQ9` — the loaded program's own output —
and then `Ok`. **zerobas appends `Illegal function call in 3346`.**

🔴 **THE DEFECT IS IN THE SUCCESS PATH OF A SHIPPED VERB, AND THE FILED
RESIDUAL NAMED ONLY THE MISS.** §8.6 recorded `run-missing`'s two rows; the
same second message follows a `RUN"file"` that finds its file, loads it and runs
it correctly. `fat-error`'s `run-alive` control could not see it: that control
reads the tail of its **last** typed line (`PRINT PEEK`), and the stray message
lands on the `RUN` line above. Three rows here (`run-hit`, `run-hit-res`,
`loadr-hit`) are hit rows and all three diverge.

## 3. R-RT2 — `LOAD"file",R` is the same verb, and diverges identically

`loadr-hit` and `loadr-miss-res` read exactly what their `RUN` twins read on
both sides. Whatever the rule is, it is not `RUN`-token-specific.

## 4. R-RT3 — the reference does NOT run the resident program after a failed load

`run-miss-res` and `loadr-miss-res` type `10 PRINT"ZQ1"` first. The CF-3300
prints `File not found` and stops: **`ZQ1` never appears.** zerobas prints its
message, then **runs the resident program** (`ZQ1`), then the stray error.

⚠️ This contradicts `basic/PROVENANCE.md` §disk RUN, whose table row reads
*"reuses `disk_prog_load` (§disk LOAD), **always runs**"*. "Always runs" is
true of the code and wrong about the machine: a load that failed must run
nothing. The claim was never measured.

## 5. R-RT4 — the two paths this slice must NOT move

`bare-run` (the REPL's own `RUN` command) and `load-plain` (`LOAD` without `,R`)
**already agree** with the reference, including the listing that proves the file
arrived. They are the green half of every falsification below.

## 6. 🎯 Where `3346` comes from — mechanically confirmed, not inferred

`3346` = `$0D12`. It is **constant** across every divergent row — empty program,
one-line program, two-line program, the disk fixture — which is what says it is
not program text.

`print_in_lineno` (`basic/program.asm`) prints the word at **`CURLINE+2`**. The
first four bytes of the page-0 ROM on this machine are

```
$0000: F3 C3 12 0D        ; DI / JP $0D12
```

so the word at `$0002` is **`$0D12` = 3346 exactly**. `CURLINE` is `$0000`, and
the interpreter is executing the byte at `$0004` as a BASIC statement.

The full chain, every step of which is code in this tree:

1. A typed `RUN"A:RT.BAS"` is **not** the REPL's `RUN` command — `is_cmd`
   requires the next byte to be end/space/`:` and this one is `"`. So it is
   crunched and executed as a statement, under `CURLINE := dir_line`.
2. `do_run` (`basic/cload.asm`) ends `call disk_prog_load` / `jp run_prog`.
   `run_prog` is entered **nested**, from inside the enclosing line's own run
   loop, and it overwrites `CURLINE`, `DIRECTF`, `ENDFLAG`, `SAVSTK`.
3. The loaded program runs and reaches its `$0000` end-link. `run_prog`'s exit
   is a `ret`, which returns into `exec` — **not** to the prompt — and the
   **enclosing** loop resumes at `rp_run` with `CURLINE` now pointing at the
   loaded program's end marker instead of `dir_line`.
4. `rp_run` falls through to "next line": `CURLINE := (CURLINE)` = the `$0000`
   end-link = **`$0000`**.
5. `rp_lp` reads the link at `$0000` — `$C3F3`, not zero — so it does not stop.
   `rp_exec` re-derives `DIRECTF` from `CURLINE+1`, gets **run mode**, and
   `exec` dispatches the byte at `$0004` as a statement token. It raises
   `Illegal function call`, reported in run mode as `in <word at $0002>` =
   `in 3346`.

**The discriminator that confirms it, and it is decisive:** a loaded program
whose last statement is `END` sets `ENDFLAG`, which **survives** into the
enclosing loop's `ld a,(ENDFLAG) / ret nz` — step 4 never happens. Measured:

| loaded program | zerobas tail |
|---|---|
| `10 PRINT"ZQ9"` | `ZQ9 / Illegal function call in 3346` |
| `10 END` | `<nothing>` ✅ |

and `bare-run` is silent for the mirror reason: the REPL's `dl_run` reaches
`run_prog` at the depth its `ret` returns to the **prompt** from, so there is no
enclosing loop to resume.

⚠️ **The stray message is the symptom, not the defect.** Step 5 is the
interpreter **executing ROM as BASIC text**. That it lands on ERR 5 rather than
somewhere worse is a property of the four bytes at `$0004`, not of any guard.

## 7. What is NOT claimed here

* **The wording of the first message is untouched.** `load error` vs
  `File not found` is the quarantined divergence recorded in
  `basic/PROVENANCE.md` and filed separately in `TODO.md`. Every row above
  normalises it away on purpose.
* **The tape twins are not measured.** `LOAD"CAS:x",R` and `RUN"CAS:x"`
  (`basic/cload.asm` `dl_cas_close` / `dr_is_cas`) end in the identical
  `jp run_prog` from a statement context and are therefore structurally the same
  defect — but this battery has no cassette instrument and does not read them.
  See [spec-basic-runtail.md](spec-basic-runtail.md) §9.
* **`ERR` / `ERL` are not a witness here.** They are read-back sysvars with no
  cold init; a `PRINT ERR;ERL` on a batched run reports whatever a previous case
  left. Every reading above is screen text.
