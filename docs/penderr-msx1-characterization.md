# MSX1 characterization — of two pending faults, the FIRST one is reported

Black-box measurement on **Philips VG-8020** and **National CF-3300**, driven by
[`probes/basic/basic_probe_penderr.py`](../probes/basic/basic_probe_penderr.py)
(`make penderr-acceptance`). Both reference ROMs are oracles only: identical
programs in, observed screen output out. No disassembly, no ROM reads.

Every row is a **stored program driven by `RUN`** — in direct mode an abort on
one line does not stop the next, so a direct-mode tail can read a value where the
reference stopped. Trapped rows print `ERR` from inside an `ON ERROR` handler
before anything else reaches the screen; untrapped rows read the clipped screen
tail, which is what makes the message TEXT, its line number and "printed once"
part of the reading rather than just a code.

Companion to [`tmfp-msx1-characterization.md`](tmfp-msx1-characterization.md),
which established the rule for a type fault against a numeric one. **This note
records that the rule is not about fault KINDS at all.**

---

## 1. The finding, in one table

`0*<faulting expression>` contributes 0 to the sum and leaves a fault pending, so
two of them concatenated put two faults up in a known order. Three distinct codes
are used so no reading of the result as a rank between kinds survives.

| program | first fault | second fault | VG-8020 | CF-3300 |
|---|---|---|---|---|
| `WIDTH 0*(1/0)+0*SQR(-1)` | div by zero | SQR domain | ` 11 ` | ` 11 ` |
| `WIDTH 0*SQR(-1)+0*(1/0)` | SQR domain | div by zero | ` 5 ` | ` 5 ` |
| `WIDTH 0*(1/0)+0*(1E38*1E38)` | div by zero | overflow | ` 11 ` | ` 11 ` |
| `WIDTH 0*(1E38*1E38)+0*(1/0)` | overflow | div by zero | ` 6 ` | ` 6 ` |
| `WIDTH 0*SQR(-1)+0*(1E38*1E38)` | SQR domain | overflow | ` 5 ` | ` 5 ` |
| `WIDTH 0*(1E38*1E38)+0*SQR(-1)` | overflow | SQR domain | ` 6 ` | ` 6 ` |

🎯 **THREE CODES, SIX ROWS, AND THE ANSWER IS ALWAYS THE FIRST ONE.** Every
possible ordered pair of three fault kinds is here, and in each the reported code
is the operand that comes first in source order. There is no rank between
"division by zero", "illegal function call" and "overflow": the reference raises
**eagerly**, the first fault aborts the statement on the spot, and the second one
never occurs at all. D-TMFP proved that for one pair; this is the general case.

The same pairs answer identically at every driver measured — `WIDTH`,
`V=<expr>`, `W(0)=<expr>`, `PRINT <expr>` — which is what says the rule belongs
to evaluation and not to any statement handler.

## 2. It holds across the transcendental boundary too

| program | VG-8020 | CF-3300 |
|---|---|---|
| `WIDTH 0*(1/0)+0*EXP(1000)` | ` 11 ` | ` 11 ` |
| `WIDTH 0*EXP(1000)+0*(1/0)` | ` 6 ` | ` 6 ` |
| `WIDTH 0*(1/0)+0*(2^10000)` | ` 11 ` | ` 11 ` |
| `WIDTH 0*(2^10000)+0*(1/0)` | ` 6 ` | ` 6 ` |
| `WIDTH 0*SQR(-1)+0*EXP(1000)` | ` 5 ` | ` 5 ` |

`EXP` overflow and `^` overflow are both ERR 6, and both lose to an earlier
fault and win over a later one.

## 3. A pending fault is reported instead of the WRONG-CHANNEL answer

🔴 **THIS IS THE ROW THAT IS EASY TO GET WRONG, AND IT IS EASY TO GET WRONG IN A
WAY THAT LOOKS DELIBERATE.** A faulting channel expression evaluates to 0, and
channel 0 is a legitimate thing to have an opinion about — `PRINT LOF(0)` is
`File not open`, ERR 59. So an implementation that checks the channel *before* it
checks for a pending fault answers 59 with complete confidence.

| program | VG-8020 | CF-3300 |
|---|---|---|
| `PRINT LOF(0*(1/0)+1)` | ` 11 ` | ` 11 ` |
| `PRINT LOF(0*SQR(-1)+1)` | ` 5 ` | ` 5 ` |
| `PRINT EOF(0*(1/0)+1)` | ` 11 ` | ` 11 ` |
| `PRINT #0*(1/0)+1,"X"` | ` 11 ` | ` 11 ` |
| `V=PDL(0*(1/0)+1)` | ` 11 ` | ` 11 ` |
| `V=PDL(0*SQR(-1)+1)` | ` 5 ` | ` 5 ` |

The last two are the same shape one domain over: `PDL`'s argument domain excludes
0, so a hard-zeroed argument is an `Illegal function call` on its own merits —
and the reference still reports the earlier fault instead.

⚠️ **These are the rows zerobas was answering ` 59 ` on.** `LOF`/`EOF` on a
faulting channel derailed to `File not open` before this slice. The
characterization is the reason the fix is a fix and not a preference.

## 4. Deferred parse-time codes lose to earlier runtime ones

| program | VG-8020 | CF-3300 |
|---|---|---|
| `V=SIN(1/0,2)` | ` 11 ` | ` 11 ` |
| `V=0*(1/0)+SQR()` | ` 11 ` | ` 11 ` |
| `Q2$=LEFT$(0*(1/0)+1)` | ` 11 ` | ` 11 ` |

Each of these has a malformed call that is `Syntax error` (ERR 2) on its own —
a second argument `SIN` does not take, an empty argument, a missing one. The
earlier division by zero is reported instead. This corroborates D-F2-4, measured
independently.

## 5. Inside a string function's parentheses

| program | VG-8020 | CF-3300 |
|---|---|---|
| `Q2$=HEX$(0*(1/0)+(Q$<5))` | ` 11 ` | ` 11 ` |
| `Q2$=OCT$(0*(1/0)+(Q$<5))` | ` 11 ` | ` 11 ` |
| `Q2$=STR$(0*(1/0)+(Q$<5))` | ` 11 ` | ` 11 ` |
| `PRINT HEX$(0*(1/0)+(Q$<5))` | ` 11 ` | ` 11 ` |
| `Q2$=HEX$((Q$<5)+0*(1/0))` | ` 13 ` | ` 13 ` |

The first is D-TMFP's deferred `r.hex`. The last is its mirror and is the control
that says the answer tracks ORDER here too, not the function.

## 6. The untrapped face

| program | VG-8020 | CF-3300 |
|---|---|---|
| `WIDTH 0*(1/0)+0*SQR(-1)` | `Division by zero in 10` | same |
| `WIDTH 0*SQR(-1)+0*(1/0)` | `Illegal function call in 10` | same |
| `WIDTH 0*(1/0)+0*EXP(1000)` | `Division by zero in 10` | same |
| `WIDTH (Q$<5)+0*(1/0)` | `Type mismatch in 10` | same |

One message, naming the line, and line 20's `PRINT"[RANON]"` never runs — the
abort stops the program, it does not merely report.

## 7. Apparatus

### 7.1 The controls are single-fault rows, on purpose
Four positive controls (`n.tm.loc`, `n.dz.w`, `u.tm.loc`, `u.dz.w`) and thirteen
negative ones. 🔴 **Every one has exactly ONE fault or none**, so each already
agrees for a reason independent of anything this slice claims. D-TMFP's first
control set named a both-flags SUBJECT row and would have exited 2 on a sound run
(`tmfp-msx1-characterization.md` §3); that failure mode is designed out here
rather than watched for.

`n.ok.w` (`WIDTH 30`) and `n.ok.pdl` (`V=PDL(1)`) are the other half of it: a
row with no fault at all, which is what catches a change that *invents* one.

### 7.2 The before-column was measured, not remembered
The zerobas column was taken twice: once on the shipped build, and once on a tree
reverted to `38becce` and rebuilt clean — verified by reproducing the baseline's
four ROM hashes exactly (`basic-reloc af0a69ef`, `sub 071347df`, `disk 2c630d3d`,
`main-eu 9a066a2f`) before a single row was read, and by re-verifying after the
restore that the ROMs were byte-identical to the slice build again.

**44 of 61 rows already agreed; 17 moved; all 17 moved from a wrong answer to the
reference's answer; none moved the other way.** A slice that reports only its
after-column cannot tell "I fixed 17 rows" from "these rows were never broken".

### 7.3 What the 17 were

| rows | was | is | what it was |
|---|---|---|---|
| `o.nn.5dz`, `o.nn.tel`, `o.nn.yra`, `o.nn.rp` | ` 11 ` | ` 5 ` | a later div-by-zero overwriting an earlier SQR domain error |
| `o.nn.dzov`, `o.nn.5ov` | ` 6 ` | ` 11 `/` 5 ` | a later overflow overwriting an earlier fault |
| `o.nn.ovdz` | ` 11 ` | ` 6 ` | the mirror |
| `o.sub.exdz`, `o.sub.pwdz` | ` 11 ` | ` 6 ` | a later div-by-zero over a tenant-raised overflow |
| `r.hex`, `r.oct`, `r.str`, `r.hexp` | ` 2 ` | ` 11 ` | `str_arg_empty`'s unconditional `FPERR := 4` |
| `w.lof.dz`, `w.lof.5`, `w.eof.dz` | ` 59 ` | ` 11 `/` 5 ` | §3 — the confident wrong answer |
| `u.nn.5dz` | `Division by zero in 10` | `Illegal function call in 10` | the untrapped face of row 1 |

## 8. What the knives added to the characterization

Full results in [`spec-basic-penderr.md`](spec-basic-penderr.md) §9. One of them
measured something about **zerobas** that belongs here, because it changes what
the rows mean.

🎯 **AFTER A DEFERRED TYPE FAULT, ZEROBAS DOES NOT RAISE A SECOND FAULT FROM THE
REST OF THE EXPRESSION. AFTER A NUMERIC ONE, IT DOES.** K-PE2 deletes
first-error-wins from every writer and then:

| row | program | K-PE2 |
|---|---|---|
| `o.nn.dzov` | `WIDTH 0*(1/0)+0*(1E38*1E38)` | ` 11 ` → ` 6 ` — **moved** |
| `o.tm.tmov` | `WIDTH (Q$<5)+0*(1E38*1E38)` | ` 13 ` → ` 13 ` — **did not** |

Identical second operand; the only difference is whether the first fault was a
type fault. The screen cannot separate *"the tail was never evaluated"* from
*"it was evaluated and did not fault"*, and this note does not claim to know
which. What it does establish is that on zerobas the type/numeric rows —
including `dfe-tmfp`, the row two previous slices were designed around — are
**insensitive to the write rule**, and that the reference-matching behaviour
there comes from somewhere other than the ordering those slices reasoned about.

⚠️ D-TMFP §8's **defect 1** (after a string-compare mismatch the cursor does not
land on the closing `)`) predicts the "never evaluated" reading, and `r.hex.tm`
falling to ERR 2 under both K-PE2 and K-PE4 — i.e. the parser arriving at
`str_arg_empty` — is consistent with it. That is corroboration, not proof; the
cursor question is still open and still filed.
