# D-CATUSR — counting the evaluations, and the fix that trades one divergence for another

*2026-08-31. No ROM change. Probes `scratchpad/catusr_probe.py` (5 rows) and
`scratchpad/catterm_probe.py` (9 rows), three machines.*

## 1. The row D-CATTM named, built

D-CATTM closed with one thing unmeasured and said it decides the fix:

> whether the re-drive actually reaches the operand. **THE ERROR CODE CANNOT
> TELL** — armed-and-outranked and never-evaluated both read `13`. Separating
> them needs an operand with an observable **side effect**.

Five bytes of machine code, POKEd in and installed with `DEFUSR`:

```
21 10 D0   ld hl,$D010
34         inc (hl)
C9         ret
```

Every evaluation of `USR(0)` increments `$D010`, so `PEEK` afterwards is a
**count**, not a verdict.

🔴 **Direct mode, not a program, and that is forced.** The subject statement
raises, so inside a program the harness's `ON ERROR` reports and the run ends
before the counter can be read — measured: every subject row came back
`ERR 13 AT 50` with no count at all.

## 2. Both hypotheses were wrong, and the count says so

| row | | vg8020 | cf3300 | zerobas |
|---|---|---|---|---|
| `u.ctl` | `1+USR(0)` | 1 | 1 | 1 🟢 the mechanism works |
| `u.none` | `"AB"+5` | 0 | 0 | 0 🟢 the setup counts nothing |
| `u.catl` | `USR(0)+"AB"` | 1 | 1 | 1 |
| **`u.cat`** | **`"AB"+USR(0)`** | **1** | **1** | **0** |

* **D-CATTM's reading is refuted.** I wrote that the operand's fault was
  *"reachable and merely outranked"*. It is not reachable: zerobas evaluates the
  operand **zero times**, which is why its Division by zero never happens.
* **`TODO.md`'s hazard is refuted as stated.** It barred a fix because the
  operand would be evaluated *twice*. The references evaluate it **once** — one
  evaluation is the correct behaviour, not the hazard.
* 🔴 **And a divergence nobody had noticed**: the pre-existing evaluation count
  is already wrong, 0 against 1. The error code was never the only symptom.

## 3. The fix works on every error row and breaks the count

Applying the D-STRTM route inside `sct_err2` — `call eval` before
`type_mismatch_set`, with `pop de` so the operand cursor in `HL` survives:

* **every error row agrees, 0/9 DIFF**, including `"AB"+(0*(1/0)+1)` → `11`;
* **and `u.cat` becomes 2**, against the references' 1.

A second variant that restores `HL = R` exactly as the old `pop hl` left it — so
the caller sees precisely what it always saw — gives **the same count of 2**.
So the extra evaluation is **not** the cursor handling.

## 4. Why it was reverted

Before: a wrong error code, operand evaluated **0** times.
After: every error code right, operand evaluated **2** times.

Neither matches the reference, and the second failure mode is the worse kind:
a **silent** doubled side effect (a `USR` that POKEs, a `DEF FN` with a
side effect) against a **loud** wrong error code. This project already ranks
that way — Bug C kept the deferred mismatch precisely because the alternative
printed `" 0"` silently.

Reverted; the tree is byte-identical to `492e9ac` and `gates-fast` reports the
same four ROM hashes.

## 5. The question this hands on, which is much narrower than the one it found

Pre-change the caller's re-drive does **not** reach the operand (count 0). With
`call eval` inserted it does (count 2 = ours + theirs). `type_mismatch_set` arms
FPERR before the return in both cases, and the cursor is not the cause.

➡️ **So: what makes the numeric re-drive skip the operand when the mismatch is
armed with no prior evaluation, but reach it when an evaluation has already
happened?** Answer that and the fix is a one-evaluation version of §3 — every
error row is already known to land correctly.
