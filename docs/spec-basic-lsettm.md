# D-LSETTM — the `LSET`/`RSET` RHS decline has TWO causes, and zerobas gave both one answer

*Fixed 2026-09-02. +4 B on main page 1 (331 → 327 B free). Six divergent rows closed.*
*Probe: [`scratchpad/lsetref_probe.py`](../scratchpad/lsetref_probe.py); standing rows in
[`probes/basic/basic_probe_lrvar.py`](../probes/basic/basic_probe_lrvar.py) (`make lrvar-acceptance`).*

## 1. What was wrong

`basic/field.asm` `lrs_haveeq` — the RHS parse shared by BOTH the FIELDed and the
non-FIELDed arm — read:

```
                call    str_eval_next       ; past '=', STRPTR -> [len][ptr]
                jp      nc,stmt_error       ; RHS not a string operand
```

One `jp nc,stmt_error` for every way the evaluation can decline. Measured against
the National CF-3300 (the oracle — see §2):

| typed | CF-3300 | zerobas (before) |
|---|---|---|
| `A$="12345":LSET A$=5` | **Type mismatch** (13) | Syntax error (2) |
| `A$="12345":RSET A$=5` | **Type mismatch** (13) | Syntax error (2) |
| `A$="12345":N=5:LSET A$=N` | **Type mismatch** (13) | Syntax error (2) |
| `A$="12345":LSET A$=` | **Missing operand** (24) | Syntax error (2) |
| `A$="12345":LSET A$=:PRINT` | **Missing operand** (24) | Syntax error (2) |
| `A$="12345":RSET A$=` | **Missing operand** (24) | Syntax error (2) |

## 2. Why the CF-3300 is allowed to be the oracle at all

Because [D-LSETREF](spec-basic-lsetref.md) settled it the same day. `LSET A$=5`
reads ERR 5 on the cassette VG-8020, and this row sat in a NO-ORACLE bucket as a
three-way disagreement (5 / 13 / 2). It is not one: the **National CF-3000**, a
cassette machine whose main BASIC ROM is **byte-identical** to the CF-3300's
(sha1 `c7a2c5ba…`), also answers ERR 5. A cassette machine refuses the *verb*;
it holds no opinion about the RHS. zerobas ships a disk ROM, so the CF-3300 is
the reference and this is a plain divergence.

## 3. 🎯 The repair was already written down, in this same machinery

[`basic/printusing.asm:66`](../basic/printusing.asm) records the identical trap
and the identical fix, for `PRINT USING`:

> *"The EOL/':' test must come FIRST, and that is what SPLITS the old shared
> `jp nc,stmt_error`: str_eval declines both for "there is nothing here" and for
> "there is something and it is not a string", and the references answer 24 and
> 13 respectively. With the missing case taken off the front, an NC below can
> only mean the second."*

Applied here:

```
                inc     hl                  ; past '='
                call    req_operand         ; `LSET A$=` / `= :` -> ERR 24
                call    str_eval            ; STRPTR -> [len][ptr]; HL advanced
                jp      nc,type_mismatch_error  ; a non-string RHS -> ERR 13
```

`str_eval_next` (`inc hl / call skip_spaces / jp str_eval`) is unrolled because
`req_operand` must run **past the `=` but before the evaluation**, and
`req_operand` does its own `skip_spaces`, so no second one is needed.
Cost: `inc hl` 1 B + `call req_operand` 3 B, less the `call str_eval_next` it
replaces = **+4 B**; the `jp nc,` retarget is **0 B**, the same instruction with
a different address. Measured: page-1 free 331 → 327 B.

⚠️ **I DID NOT TAKE THE ONE-LINE VERSION, AND THE REASON IS THE ROWS.** Retargeting
`jp nc,stmt_error` → `type_mismatch_error` alone is 0 B and fixes three of the six
— and silently converts `LSET A$=` from ERR 2 to ERR 13, where the reference says
24. The three `*miss*` rows are the ones that separate the rules; without them
the cheap fix looks complete.
[[two-rules-that-coincide-on-every-row-you-have]]

## 4. Knives — falsify by planting

[`scratchpad/lsettm_knives.py`](../scratchpad/lsettm_knives.py). Three arms, each
reverting one half of the fix, rebuilt CLEAN, scored on the six `d.*` rows plus
`n.ctl` as a positive control that must stay green in every arm.

| arm | plant | ROM sha1 | rows moved | expected | control |
|---|---|---|---|---|---|
| baseline | — | `e9eed5f1` | — | — | ✅ |
| **K-LT1** | `type_mismatch_error` → `stmt_error` | `64e32458` | `d.num d.rnum d.numvar` | same | ✅ |
| **K-LT2** | drop `call req_operand` | `c8a4483e` | `d.miss d.misscol d.rmiss` | same | ✅ |
| **K-LT3** | drop `"Missing operand"` from the probe's alphabet | `e9eed5f1` | `d.miss d.misscol d.rmiss` | same | ✅ + loud path fired |

The two halves move **disjoint** row sets, which is the claim: each fixes what
the other cannot.

🔴 **THE FIRST CUT OF THIS RUNNER HAD A DECORATIVE GUARD.** It hashed
`build/basic.rom` — a file this build never produces — printed `rom=ABSENT`
three times and carried on. That is the *inert-knife* hazard rebuilt as a guard
that cannot fire. Armed against the real artifact
(`build/zerobas-main-eu.rom`), it now REFUSES rather than prints.
⚠️ **And the expectation had to be made PER-ARM**: K-LT3 patches the probe, not
the assembly, so its ROM *must* equal the baseline — a guard demanding movement
everywhere would have reddened a correct arm.
[[a-knife-can-be-inert-because-the-build-did-not-happen]]

## 5. Result

All 14 rows of the scratch matrix identical to the CF-3300 after the fix (6 were
divergent before). `lrvar-acceptance` carries six of them as standing rows
(`d.miss`, `d.misscol`, `d.rmiss`, `d.num`, `d.rnum`, `d.numvar`), marked
disk-only for the reason in §2.

## 6. 🔴 The rows exposed a blind spot in the probe that was to carry them

The first `lrvar-acceptance` run with the new rows printed:

```
.... d.miss   cf3300='<NO OUTPUT>'  zb='<NO OUTPUT>'   [NO REFERENCE ON ANY REQUESTED SIDE]
```

on all three `*miss*` rows — while both machines had printed `Missing operand`
perfectly well. Cause: `bracket()` classifies a screen against a **hand-written
list of 15 error-message strings**, and ERR 24's message was not in it. Anything
the alphabet cannot name reads `<NO OUTPUT>`, which routes to *"without a
reference"* — a sentence about the MACHINE, for a fault in the PROBE.

The same list was **already wrong for a message it did name**: `Field overflow`,
where `sub/errmsg.asm` says `FIELD overflow`. Nothing had ever provoked that row,
so the fault had never shown.

Both fixed: the alphabet is re-derived from `sub/errmsg.asm` + main's
`err_msgtab` (15 → 37 strings), and — the part that matters — an unclassifiable
**non-empty** screen now returns `<UNREADABLE: …first 48 chars…>`, which is
deliberately **not** a sentinel, so the gate scores it RED and carries the text
instead of dropping the row. A closed alphabet will drift again; the point is
that the next omission is loud.
[[a-coverage-row-whose-geometry-cannot-reach-the-case]]
[[an-unnamed-outcome-reads-as-no-outcome]]
