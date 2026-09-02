# D-OPEN2FIX — the second disk `OPEN`'s `Syntax error` was a register clobber, and the guard was one call too late

*Fixed 2026-09-02. **+2 B** on main page 1 (301 → 299 B free). 8 of 9 divergent
rows closed. Closes the open half of
[`docs/spec-basic-open2.md`](spec-basic-open2.md).*

## 1. Where the item had got to

D-OPEN2 (2026-08-30) had done the hard part and said so: the OPEN **completes**
(the channel table shows both channels open and usable), the error is raised
*afterwards*, six hypotheses were refuted by rows, and diagnostic knives located
the raise to `fch_ctx_addr` — the op-18 CALSLT that asks the string-heap tenant
for a channel's context block. Its stated next step:

> ⚠️ **NEXT NEEDS A DEBUGGER, NOT A READING**: a breakpoint on the second
> `fch_ctx_addr` with a register/RAM dump. BASIC-level bisection has bottomed
> out — guessing further is what produced the six refutations.

## 2. The debugger, and what it showed

openMSX is driven through Tcl, so breakpoints and watchpoints are available to
the same harness that runs the probes. Breakpoints on the OPEN path, logging the
order they are hit during the **second** open:

```
check_expr_errors   A=00 HL=EC00
ex_open             A=B0 HL=EC00
do_open             A=B0 HL=EC01
fch_claim           A=02 HL=EC15
fch_save_active     A=01 HL=EC15
fch_flush_active    A=01 HL=EC15
fch_ctx_addr        A=01 HL=EA01
check_expr_errors   A=00 HL=E9FB      <-- the cursor MOVED
stmt_error          A=0F HL=E9FB
raise_error         A=02
```

**`HL` is the token cursor.** It enters `fch_claim` as `$EC15` and the statement
boundary reads it back as `$E9FB`, so the parser resumes on garbage and raises
`Syntax error` — *after* the OPEN has done all its work, which is exactly why
the channel table looked correct and why `oo_nodisk`/`oo_fail` never matched.

🔴 **AND TWO OF D-OPEN2's CONCLUSIONS WERE WRONG, BOTH IN THE SAME DIRECTION.**
A watchpoint on `FPERR` ($F069) recorded **only two writes in the whole run, both
`00`**, the second from inside `record_errline` — the *consume*. Breakpoints on
`penderr_set` and `ev_f_empty` never fired. So it is **not** a deferred error and
**nothing sets `FPERR`=4**; the item's "what remains is finding what sets FPERR=4"
was chasing something that does not happen. It is a direct `jp stmt_error`.

## 3. The cause, in the caller's own words

```
                push    de
                ld      a,e
                call    fch_claim           ; FCH_ACTIVE = e (no stale load)
                pop     de
                push    hl                  ; guard the text cursor — CALSLT (inside
                push    de                  ; fat_io_*) clobbers HL + regs
```

The caller **does** guard `HL` — one call too late. That guard protects the
`fat_io_*` CALSLT below it; `fch_claim` runs its own CALSLT (via
`fch_save_active` → `fch_ctx_addr`) and is not covered. `fch_claim`'s header says
`Clobbers regs.`, so the contract was documented and the call site simply did not
honour it.

🎯 **WHY NOTHING CAUGHT IT, AND IT IS THE SAME REASON D-OPEN2 GAVE.**
`fch_claim` opens with `ret z` when the channel already owns the globals, so with
a single channel it never reaches a CALSLT at all. The missing guard is
unreachable until a **second disk channel** exists — untested by construction.
`fch_select`, the sibling entry, guards `IX` across both its CALSLTs with a
comment explaining that IX-critical callers enter through there; the HL-carrying
caller was left to guard itself, and half did.
[[a-scratch-register-that-was-the-callers-value]]

## 4. The fix

`push hl` / `pop hl` around `call fch_claim` in `basic/files.asm`. **+2 B.**

## 5. Result

`open2-*` rows, CF-3300 vs repack: **9 DIFF → 1 DIFF of 18.**

Everything that was failing now passes: two random channels in either order, two
sequential channels, mixed random/sequential, with and without `LEN=`, at
`MAXFILES=2` and `3`. The controls stay green — one channel in every shape, and
`n.nomaxf` still reads `Bad file number` on both sides, which is what says
`MAXFILES` is doing its job and the fixture is sound.

## 6. The one row left, which the Syntax error was hiding

| row | CF-3300 | zerobas |
|---|---|---|
| `e.same2` — the SAME file on two channels | `File already open` | **`OK`** |

zerobas permits it. That is a missing duplicate-file check, a **different** defect
from this one, and it was invisible while every two-channel open died earlier. It
is filed rather than fixed here: the face is known (`File already open`, ERR 54)
but where the reference performs the check — at name-parse time, or at claim time
against the other channels' names — is unmeasured, and the rows that would
separate those do not exist yet.
