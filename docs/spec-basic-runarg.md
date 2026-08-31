# D-NGRAM16 / D-RUNARG — a carve, and the seven-row divergence its row set found

*2026-08-31. `basic/save.asm` (helper), `basic/cload.asm` + `basic/save.asm`
(4 sites), `basic/program.asm` (the REPL gate). Probe
`scratchpad/fnamedev_probe.py` (20 rows), arms `scratchpad/fnamedev_knives.py`.*

**Cost: −6 B net** — the carve gives +15, the fix spends 21. Page 1 355 → 349.
**Rows: 20, DIFF 7 → 0.**

## 1. The carve, and the hazard that had to be checked first

`call fname_expr / ld de,dev_cas / call dev_cmp` opened four verbs — `LOAD`,
`RUN"name"`, `SAVE`, `BSAVE` — 9 B each. One tail-jump helper: 21 B for 36.

🔴 **The risk was not the `Z` flag but `fname_expr`'s outward jump.** It does
`jp nc,els_tc_common` when the filename is not a string, and behind a helper
that jump sits one frame deeper — the D-NGRAM8 shape, where a `call` moved an
outward jump and a decline stopped declining. Read first: **both** of
`els_tc_common`'s exits (`stmt_error`, `type_mismatch_error`) raise and never
return, so the extra frame is discarded with the rest.

That is an argument, so it got rows: `n.load`, `n.save`, `n.bsave` drive a
**non-string** filename through three of the four verbs. All hold.

## 2. 🔴 And the fourth verb was already broken — silently

`n.run` (`RUN A`, A numeric) read `<nothing>` where the CF-3300 says `Type
mismatch`. `<nothing>` is equally consistent with *"refused quietly"* and
*"ran an empty program"*, so one row separated them: with `10 PRINT"ZQ1"`
resident, `RUN A` prints **ZQ1**.

**zerobas ran the resident program.** Not a wrong message — a wrong *program
run*, which is the class this project ranks worst.

Narrowing found it is not about filenames at all:

| typed | CF-3300 | zerobas (before) |
|---|---|---|
| `RUN 20` | runs from line 20 | **runs from the TOP** |
| `RUN "A:NOSUCH.BAS"` | `File not found` | **runs the resident program** |
| `RUN A$` | `File not found` | **runs the resident program** |
| `RUN A+0`, `RUN (A)` | `Type mismatch` | **runs the resident program** |
| `RUN20`, `RUN"A:NOSUCH.BAS"` | — | **agree** ✅ |

## 3. The cause is one word in a delimiter test

The REPL's `dl_cmd` matches `RUN` with `is_cmd`, whose contract is:

> CF set iff (HL) case-folds to the template **AND the next input byte is a
> delimiter (end / space / ':')**, so "RUN" matches but "RUNNER" does not.

That is exactly right for telling `RUN` from `RUNNER`, and exactly wrong as a
*"takes no argument"* test. **A space is a delimiter**, so `RUN <anything>`
matched the bare-RUN fast path and the argument was discarded. The no-space
forms work only because `"` and `2` are not delimiters, so `is_cmd` never
matched and the line was crunched into `do_run`, which handles arguments
correctly.

`dl_bare` now asks the second question — *is there anything but `:` or
end-of-line after the keyword?* — and only the bare form keeps the fast path.

⚠️ **`jr` → `jp` at the call site**: `dl_bare`'s body pushed `dl_run` out of
relative range.

## 4. Two arms, and one that the ROM-hash guard caught being inert

| knife | cut | moved |
|---|---|---|
| K-N16A | the helper never parses the filename | 16 |
| K-RA1 | the gate calls everything bare | the 7 `RUN <arg>` rows, and nothing else |

🎯 **K-RA1 moving *only* the RUN rows is the content**: `LOAD`/`SAVE`/`BSAVE`
never reach the REPL gate, so their holding says the change is RUN-specific
rather than a parser change.

🎯 **And K-N16A's two non-movers were the prediction I got wrong**: I expected
18 and 16 moved. `RUN 20` / `RUN20` take `do_run`'s **LINENO** arm and never
reach `fname_dev` at all.

🔴 **K-RA1's first cut was INERT and said so.** Inserting `scf`+`ret` at the top
of `dl_bare` added two bytes, pushed another `jr` out of range, and the build
**failed** — leaving the previous ROM in place. `knife_guard` compared hashes,
reported `KNIFE INERT — the ROM did not change`, and refused to let the probe
measure the uncut machine. Re-cut size-neutrally (`or a` → `scf`).

## 5. 🔴 The helper landed on top of the file header, and a gate caught it

The insertion script anchored on the comment block *above* `do_bsave` — and
`save.asm`'s first `; ---` block is its **file header**, so the helper was
written at line 1 and displaced the copyright, SPDX line and clean-room
attestation.

The build was clean. Every row still agreed. `basic-reloc` was happy.
`audit_citations` said:

```
[NO-ATTEST] basic/save.asm:1: no clean-room / no-disassembly / PROVENANCE
            attestation in header
```

**A mechanical insertion can be correct about the code and wrong about the
file.** Nothing in the ROM, the rows or the walls could see it; the only
instrument that could was the one that reads headers.
[[a-mechanical-fix-can-break-a-different-invariant]]

## 6. Falsification

| claim | what would refute it | result |
|---|---|---|
| the four runs were identical | the assembler, or a moved row | 20 rows, identical across the carve |
| the extra frame cannot bite | a non-string filename row moving | `n.load`/`n.save`/`n.bsave` hold |
| the gate is RUN-specific | K-RA1 moving a LOAD/SAVE row | it moves exactly 7, all `RUN` |
| only the bare form should fast-path | either reference | `RUN 20` runs from 20 on both now |
