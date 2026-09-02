# D-ONERRGO — `ON ERROR GOTO`'s operand stage has THREE outcomes, not two

*Fixed 2026-09-02. +26 B on main page 1 (327 → 301 B free). Nine divergent rows closed.*
*Probes: [`scratchpad/onerrraw_probe.py`](../scratchpad/onerrraw_probe.py) (raw screens),
[`scratchpad/onerrarm_probe.py`](../scratchpad/onerrarm_probe.py) (the D-ONERRARM matrix).
Standing rows: [`probes/basic/basic_probe_onerr0.py`](../probes/basic/basic_probe_onerr0.py),
`make onerr0-acceptance`.*

## 1. The filed item, and what it got right

[D-ONERRARM](spec-basic-onerrarm.md) (2026-08-29) measured `ON ERROR GOTO A` as
raising `Syntax error` **untrapped** on both references while zerobas trapped it,
and refuted two hypotheses on the way: it is not "disarm before parsing" (the
stages either side of it both trap) and not a tokenise-time rejection (the line
is stored and executed). It concluded, correctly, that this is a **one-stage
asymmetry** at the operand.

It then filed two obstacles, and **both were wrong**:

> *"`req_lineno` is now shared by four verbs and only ON ERROR wants this exit,
> so it needs a second entry point or a flag"* — it needs neither; the caller can
> make the test itself before calling.
>
> *"'untrapped' must be EXPRESSIBLE: it needs a raise that skips the trap check,
> which is not what `stmt_error` does."* — **it was already expressible.**
> `raise_error`'s tail is split: `raise_error_hl` makes the trap decision and
> `ra_abort` is the abort body *below* it. Entering at `ra_abort` with the
> message in HL is the untrapped raise, and it is the same shape
> `raise_error_forced` (ERR 22) has always used.

## 2. 🔴 The stage has THREE outcomes, and the third nearly shipped as a new bug

The first draft of this fix was one test:

```
                cp      LINENO_TOKEN
                jp      nz,oe_badop         ; -> untrapped Syntax error
```

That is wrong, because `ON ERROR GOTO` with **no operand at all** also fails
that test — and on both references it is **not an error at all**. The draft
would have converted a row the old code got right *by accident* into a fresh
divergence. Measured before any code moved:

| row | typed at line 30 | VG-8020 | CF-3300 | zerobas (before) |
|---|---|---|---|---|
| `a.badtok` | `ON ERROR GOTO A` | `Syntax error in 30` | ″ | `[TRAPPED 2 30]` |
| `a.badstr` | `ON ERROR GOTO "X"` | `Syntax error in 30` | ″ | `[TRAPPED 2 30]` |
| `x.bare` | `ON ERROR GOTO` | `[REACHED40]` — **no error** | ″ | `[TRAPPED 2 30]` |
| `x.colon` | `ON ERROR GOTO :B=1` | `[REACHED40]` — **no error** | ″ | `[TRAPPED 2 30]` |
| **`x.goto`** | `GOTO A` | `[TRAPPED 2 30]` | ″ | `[TRAPPED 2 30]` |

`x.goto` is the row that keeps the fix honest: plain `GOTO` with the identical
bad operand **traps on every side**, so the new exit belongs to `ON ERROR` alone
and `req_lineno`'s other three callers must not move.
[[two-rules-that-coincide-on-every-row-you-have]]

## 3. "No operand" is exactly `ON ERROR GOTO 0` — three claims, three rows

Routing the bare form to `oe_disable` inherits **D-ONERR0's special case**: `ON
ERROR GOTO 0` inside an *active* handler does not merely disarm, it re-raises the
error that entered the handler, untrapped. That is measured for `GOTO 0`; for the
bare form it was not, and `oe_disable`'s own header warns that *"disarming is
special"*. So each claim got its own row:

| claim | row | VG-8020 / CF-3300 | control |
|---|---|---|---|
| it DISARMS | `h.bare`, `h.colon` | `Illegal function call in 40` | `h.off` (`GOTO 0`) reads the same; `h.ctl` (untouched) reads `[TRAPPED 5 40]` |
| it RE-RAISES inside a handler | `i.bare` | `Illegal function call in 30` | `i.zero` (`GOTO 0`) reads the same; `i.rearm` reads `[HANDLERRAN]` |
| the next statement still runs | `j.colonrun` | `[B= 7 ]` | — |

Both controls behaved as designed in both directions, which is what lets the
subject rows mean anything.

## 4. ERR/ERL after the untrapped abort — the row that sites `record_errline`

| row | after the run, `PRINT ERR;ERL` | |
|---|---|---|
| `e.errl` (`ON ERROR GOTO A` at 30) | `[ 2  30 ]` on both references | so ERRFLG **and** ERRLIN are set |
| `e.ctl` (`B=ASC("")` at 20) | `[ 5  20 ]` on both references | the ordinary-abort convention |

A fix that skipped `record_errline` would read `[ 0  0 ]` here **and every other
row in §2 and §3 would still be green.** This is the only row that sites it.

## 5. The fix

`basic/program.asm`, `ex_on_error`:

```
                or      a
                jr      z,oe_disable        ; `ON ERROR GOTO` <eol>  == GOTO 0
                cp      COLON
                jr      z,oe_disable        ; `ON ERROR GOTO :`      == GOTO 0
                cp      LINENO_TOKEN
                jp      nz,oe_badop         ; present, not a line number
                call    req_lineno
```

and the untrapped raise:

```
oe_badop:
                ld      a,2
                ld      (ERRFLG),a
                call    record_errline      ; ERRLIN := this line (ERL reads 30)
                ld      hl,err_syntax       ; err_msgtab entry 2, low-region pool
                jp      ra_abort            ; PAST raise_error_hl -> never traps
```

12 B at the site + 14 B of body = **+26 B**; page-1 free 327 → 301 B.

## 6. Knives — falsify by planting

[`scratchpad/onerrgo_knives.py`](../scratchpad/onerrgo_knives.py). Four arms,
each rebuilt clean, scored on the eight `o.*` rows against `cf3300,zb`.

| arm | plant | ROM sha1 | rows moved | expected | `o.gotoctl` |
|---|---|---|---|---|---|
| baseline | — | `7a7acfdb` | — | — | ✅ |
| **K-OG1** | drop the no-operand route | `6ad4aa56` | `o.bare o.barecol o.barerun o.bareinh` | same | ✅ |
| **K-OG2** | drop the not-a-lineno route | `8c184ae4` | `o.badop o.badstr o.badoperl` | same | ✅ |
| **K-OG3** | drop `call record_errline` | `f7538171` | **`o.badoperl` alone** | same | ✅ |
| **K-OG4** | `ra_abort` → `raise_error_hl` | `baace08e` | `o.badop o.badstr o.badoperl` | same | ✅ |

🎯 **K-OG3 IS THE ARM WORTH HAVING.** It moves exactly one row, which is the
proof that `o.badoperl` is load-bearing rather than a decorative duplicate of
`o.badop`: with `record_errline` gone, the message is still right, the raise is
still untrapped, and **seven of the eight rows stay green** while ERR/ERL read
`[ 0  0 ]`.

**K-OG4** separates the two halves of `raise_error`'s tail: retargeting the final
jump from `ra_abort` up to `raise_error_hl` restores the trap, confirming that
the untrapped-ness comes from *where the jump lands*, not from anything else in
`oe_badop`.

`o.gotoctl` stayed green in all four arms — no knife leaked into `req_lineno`'s
other three callers. Four distinct ROM hashes, restored to baseline at the end.
[[a-knife-can-be-inert-because-the-build-did-not-happen]]

## 7. Result

**17/17 raw-screen rows identical to both references** (nine moved). The
D-ONERRARM matrix goes **4/12 DIFF → 0/12**. Eight standing rows added to
`onerr0-acceptance`, including `o.gotoctl` — the leak detector for
`req_lineno`'s other callers.

⚠️ **NOT COVERED, named rather than implied:** `ON ERROR GOTO` with a bad operand
in DIRECT mode (every row here is run-mode; the abort's ` in <line>` suffix has
no direct-mode analogue and the references' direct-mode face is unmeasured);
`ON ERROR GOSUB` and the other `ON <expr> GOTO` forms, which share no code with
this site; and whether a bare `ON ERROR` with no `GOTO` at all differs — that is
stage 1, which `a.nogoto` shows already agrees.
