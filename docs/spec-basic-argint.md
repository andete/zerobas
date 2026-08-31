# D-NGRAM19 — one `evmc_arg_int`, and why the sweep's 14 B was really 7

*2026-08-31. `basic/expr.asm`. Probe `scratchpad/argint_probe.py` (16 rows,
three machines), arms `scratchpad/argint_knives.py`.*

**Cost: −7 B** — main page 1 371 → **378**. **Rows: 16, DIFF 0 before and after.**

## 1. The run, and why it cannot be a plain subroutine

ABS, SGN, INT and FIX each opened with the same nine bytes:

```
                call    ev_mc_arg_checked
                ret     nz                  ; malformed -> deferred syntax error
                ld      a,(FACTYP)
                cp      2
```

🔴 **Two things leave that run for the caller**, and the sweep can see neither:

* the `ret nz` returns **from the verb**. Inside a helper it would return to the
  call site, one frame too shallow — the D-NGRAM8 bug exactly;
* the final `cp 2` publishes a **Z flag** that each of the four then branches on
  **differently**: `jr nz,evabs_float`, `jr z,evsgn_int`, `ret z`, `ret z`.

One flag cannot carry both answers, so the malformed case moves to **carry** and
each site keeps a one-byte `ret c`. That is the D-ARGOPEN shape — *a flag a row
can see beats a frame trick*.

📏 **Measured: +7 B, against the sweep's ranked 14.** The ranking prices a plain
subroutine; the frame and the published flag are properties of the **sites**, and
`ngram_sweep.py`'s own header already says its numbers are floors that "cannot
know a run is unfactorable". This is the same correction as D-NGRAM12's in the
other direction, where an `equ` alias made the true value *higher*.

## 2. Three paths per verb, because three things leave the run

`i.*` an int argument (the Z arm), `f.*` a float argument (the NZ arm), `b.*` a
malformed one (the return-from-the-verb arm, now carry). A row set with only the
first two cannot see the path this carve actually reshaped.

16 rows, three machines, **DIFF 0 both before and after** — including `ABS(-32768)`,
the escape ABS has its own arm for.

## 3. 🔴 The first K-A1 was masked, exactly like `req_gosub`'s second branch

`scf` → `or a` — so a malformed argument stops reporting carry — moved **zero
rows**. `ev_mc_arg_checked` has *already* armed the deferred D-F2-4 error, and
`check_expr_errors` reports it at the statement boundary whether or not the verb
returned early. **The `ret c` decides whether the verb's body runs on garbage,
not what is printed**, and no row reads that.

This is the third time today one check has been masked by another reporting the
same message (D-NGRAM13's second EOF test, D-CVISTRTM's link-word re-check,
D-NGRAM18b's syntax re-check). **When a cut moves nothing, ask what else produces
the identical output before concluding the code is dead.**

Re-aimed at **reachability**: a helper that returns carry immediately moves
**all fourteen** subject rows and leaves both controls alone.

🔴 **And I predicted ten, not fourteen.** The malformed rows move too — because
`ev_mc_arg_checked` is *inside* the helper, so skipping it never arms the
deferred error either and `ABS()` stops reporting `ERR 2`. The gate moved into
the helper along with the run.

## 4. 🔴 K-A2's inversion was backwards

`cp 2` → `cp 4` moved six rows, not the five int rows I predicted. FACTYP 4 is
**single precision**, so the cut does not merely stop ints taking the int arm —
it makes **singles take it instead**. Floats move *into* the arm and ints move
*out*, and `i.fix` / `x.abs8k` hold because their verbs' two arms agree on those
particular values.

## 5. Falsification

| claim | what would refute it | result |
|---|---|---|
| the four runs were identical | the assembler, or a moved row | 16 rows on three machines, identical across the carve |
| it cannot be a plain subroutine | a cheaper build that assembles | the `ret nz` frame and the published Z flag; measured at +7, not +14 |
| all four sites route through it | the reachability cut moving fewer | it moves all 14 subject rows, both controls hold |
| `S1`'s 0 is not a broken matcher | the `alive` control | matcher alive, and the body's `jr nz` is why 0 is the honest count here |
