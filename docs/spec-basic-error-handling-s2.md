# Spec (DRAFT — sign-off pending): Error-handling arc **S2 — trapping**

Status: **DRAFT.** Sign-off required before any ROM code. Repack-only (every byte
behind `IF ROM_BASE < $4000`, like all Phase-3 surface); lean 16 KB `basic.rom` stays
byte-identical. Builds directly on **S1 (COMPLETE: D-1 abort + D-2 ` in <line>`)** —
see [spec-basic-error-handling.md](spec-basic-error-handling.md). This is the "its own
spec" that §7 of the S1 doc deferred.

S2 delivers user-level error trapping: `ON ERROR GOTO`, `RESUME` (+ `NEXT` / `<line>`),
the `ERR` / `ERL` functions, and the `ERROR n` statement.

---

## 1. What S1 already gives us (the substrate)

* **`fre_abort_low`** (basic/arrays.asm) — THE single run-mode abort funnel. Every error
  site reaches it: sets `ENDFLAG` (unwind to REPL), fresh-lines, then (D-2) branches on
  `DIRECTF` to print `<message>[ in <line>]`. Every site does `jp fre_abort_low`
  (lean: aliased to `print_string`, byte-identical).
* **`print_in_lineno`** (basic/program.asm) — ` in ` + `CURLINE+2` via `ln_div_entry` +
  CRLF. Reused verbatim; S2 adds no reporting code.
* **`DIRECTF`** ($E1C2) — 1 direct / 0 run, set before any statement runs.
* **`RESUMEFLAG` / `RESUMEPTR`** (basic/program.asm:209/242) — the run loop's existing
  mid-line resume machinery (today: `RETURN` / a continuing `NEXT`). `rp_resume` sets
  `RESUMEFLAG=0` and jumps to `(RESUMEPTR)` = the exact statement to resume at. **This is
  the reuse vehicle for `RESUME`.**
* **`ON_TOKEN`** ($95) — already tokenised (for `ON…GOTO/GOSUB`); `ON ERROR` reuses it +
  a new `ERROR` token.
* **FPERR** internal codes (1..10) + `check_fperr_only` / `check_expr_errors` statement-
  boundary realisation. Untouched; S2 maps FPERR→ERR at the funnel.

**What S1 deliberately did NOT build** (deferred here): the central `raise_error`
dispatcher that records `ERR`/`ERL` and checks the `ON ERROR` vector, and the `SAVSTK`
stack anchor. S1 shipped as a bolt-on on `fre_abort_low` precisely because *untrapped*
abort needs no code-recording and no stack anchor. **Trapping needs both.**

---

## 2. The core mechanism: `raise_error` at the funnel head

Trapping turns the funnel into a decision point. Introduce **`raise_error`** as the head
of `fre_abort_low`:

```
raise_error:        ; in: A = MSX ERR code (1..23). Never returns to its caller.
    ld   (ERRCODE),a            ; record ERR (§4)
    call record_errline         ; ERRLINE := run? CURLINE+2 : direct-sentinel (§4)
    ld   a,(ONELIN+1) | (ONELIN) ; handler set?  (ONELIN != 0)
    or   ...
    jr   z,ra_abort             ; no handler -> the S1 abort path (fre_abort_low body)
    ld   a,(ONEFLG)             ; already inside a handler with no RESUME?
    or   a
    jr   nz,ra_abort            ; nested error in handler -> forced abort (real MSX)
    ; --- take the trap ---
    ld   sp,(SAVSTK)            ; §3: unwind any call depth to the run anchor
    ld   a,1
    ld   (ONEFLG),a            ; inside a handler now
    <save RESUME context: ERRRESUME := erroring CURLINE + statement ptr>  (§5)
    ld   hl,(ONELIN)           ; handler line's text/link addr
    jp   <run-loop resume-at-HL entry>   ; branch into the handler (via SAVSTK-clean SP)
ra_abort:
    jp   fre_abort_low          ; S1 body: ENDFLAG + fresh-line + message[ in N]
```

Two integration choices for sign-off (§9 Q1): **(A)** every error site keeps
`jp fre_abort_low` and we thread the code separately, or **(B, recommended)** every site
becomes `ld a,<code>` + `jp raise_error`, and `fre_abort_low`'s body becomes `raise_error`'s
`ra_abort` tail. (B) is the §5.3 site-funnelling; it makes `ERR` correct for *every* error
with no second path, at the cost of touching ~15 sites (each mostly byte-neutral: a site
that today does `jp fre_abort_low` becomes `ld a,n` + `jp raise_error`, +2 B). The FPERR
sites map FPERR→ERR with a small 10-entry table at `fp_runtime_error`'s tail.

`record_errline`: run mode → `ERRLINE := (CURLINE+2)`; direct mode (`DIRECTF`≠0) →
`ERRLINE := 65535` (the `ERL`-in-direct sentinel, S1 §9.3 — pin the exact value black-box
in this slice).

---

## 3. `SAVSTK` — the stack anchor

A trap jumps to the handler line from *any* call depth, so the stack must be reset. Save
SP at the two flow anchors and restore on trap:

* **Run anchor** — `run_prog` (basic/program.asm, at RUN entry before the run loop):
  `ld (SAVSTK),sp`.
* **Direct anchor** — `dispatch_line` direct entry: `ld (SAVSTK),sp` (so a direct-mode
  `ERROR n` with a handler — rare/degenerate — still resets cleanly; direct-mode error
  without a handler is already correct via S1's REPL return).

`raise_error`'s trap branch does `ld sp,(SAVSTK)` before jumping to the handler. The abort
branch (`ra_abort`) does **not** need it (S1's `ENDFLAG` unwind already returns through the
run loop). This is strictly the trap path's requirement. (Untrapped abort keeps working
exactly as S1 shipped.)

---

## 4. New RAM state

Freed VARTAB/STRTAB window (repack-only; lean uses it for the fixed var pool), below the
live `ARYTAB` ($E1C0) and `DIRECTF` ($E1C2), clear of `RVDESC`/`STRSCR` ($E26A+):

| Cell | Size | Addr (proposed) | Meaning | Set by |
|---|---|---|---|---|
| `SAVSTK` | 2 | $E1C3 | stack anchor for trap unwind | run_prog / dispatch_line |
| `ERRCODE` | 1 | $E1C5 | last error's MSX code → `ERR` | `raise_error` |
| `ERRLINE` | 2 | $E1C6 | last error's line, 65535 = direct → `ERL` | `raise_error` |
| `ONELIN` | 2 | $E1C8 | `ON ERROR` handler line addr, 0 = none | `ON ERROR` |
| `ONEFLG` | 1 | $E1CA | 1 = inside a handler (nested → forced abort) | trap / `RESUME` |
| `ERRRESUME` | 4 | $E1CB | resume context: erroring CURLINE + stmt ptr | trap |

Cold boot + `clear_vars` zero `ONELIN`/`ONEFLG`/`ERRCODE`/`ERRLINE` (so `ON ERROR` state
does not survive `NEW`/`RUN`; `ERR`/`ERL` read 0 before any error — reference-correct).
`SAVSTK` needs no init (written before use). Exact addresses pinned at impl (measure the
window is still clear post-arrays-arc).

---

## 5. The statements & functions

### 5.1 Tokens (must land first)

`ERROR`, `RESUME`, `ERR`, `ERL` are **not yet tokenised** (grep: only `ON` exists). Add
them to the keyword table — which now lives sub-side (basic/kwtable.inc is resident-thin;
the crunch/decrunch readers are the wave-2/wave-3 sub-ROM tenant, sub/sub.asm). So this
touches the **sub kwtable** and needs a sub.rom rebuild (mind `SUB_PARTS` staleness,
[makefile-subparts-stale-tenant]). Token bytes are **oracle-locked**: crunch each keyword
on the VG-8020 black-box and read the tokenised bytes (the method every existing token
used), cross-checked against the published MSX-BASIC token table (allowed-source L110,
grade B). Do NOT invent values. `ERR`/`ERL` are functions (evaluated in expr.asm); `ERROR`
/`RESUME` are statements (dispatched in interp.asm's statement switch).

### 5.2 `ON ERROR GOTO <line>` / `ON ERROR GOTO 0`

`ON` (interp.asm:204 already branches on `ON_TOKEN`) + `ERROR` → resolve `<line>` to its
link/text address (reuse GOTO's line-number lookup), store in `ONELIN`. `GOTO 0` (line 0)
→ `ONELIN := 0` (disable; and if currently in a handler, re-enable normal aborts). An
undefined `<line>` → `Undefined line number` at definition time (reference behaviour).

### 5.3 `RESUME` / `RESUME 0` / `RESUME NEXT` / `RESUME <line>`

Clears `ONEFLG`. Uses `ERRRESUME` (the erroring CURLINE + statement pointer):

* `RESUME` / `RESUME 0` — re-execute the **erroring** statement: set `RESUMEPTR` = the
  erroring statement ptr, `RESUMEFLAG=1`, `CURLINE` = erroring line; return into the run
  loop's `rp_resume`.
* `RESUME NEXT` — the statement **after** the one that erred: advance the saved stmt ptr
  past the erroring statement (to the next `:` or line), then as above.
* `RESUME <line>` — `RESUMEPTR` = `<line>`'s first statement.
* `RESUME` with `ONEFLG=0` → **`RESUME without error`** (ERR 22).

This is the delicate part — the erroring-statement pointer must be captured at trap time
(§2, into `ERRRESUME`) since `raise_error` reset the stack. `RESUME NEXT`'s "skip one
statement" reuses the tokeniser's statement-skip (the `:`/EOL scan the run loop already
has). Acceptance must cover mid-`:`-line errors (resume to the *next* statement on the
same line, not the next line).

### 5.4 `ERR` / `ERL` functions

expr.asm function-token evaluators: `ERR` → `ERRCODE` (as a 1-byte int widened to the
numeric domain), `ERL` → `ERRLINE`. Trivial once §2 records them. (`ERL` after a direct-
mode error = the 65535 sentinel.)

### 5.5 `ERROR n`

Statement: `eval` the code arg, `ld a,<code>` + `jp raise_error`. A code outside the table
→ `Unprintable error` (ERR 23) with the code echoed (reference). Doubles as the cheapest
black-box ERR-code verifier (`ERROR 5` must print `Illegal function call`).

---

## 6. Acceptance & gates

New probe `basic_probe_error_trap.py` (repack + VG-8020 differential where the reference
runs; observable-variable + screen for structure). Oracle = the S1 §3 transcript, extended:

```
10 ON ERROR GOTO 100
20 A = SQR(-1)          ' Illegal function call (ERR 5)
30 PRINT "AFTER"
100 PRINT "TRAP"; ERR; ERL
110 RESUME NEXT
->  TRAP 5  20
    AFTER
```

Cases: trap fires + `ERR`/`ERL` correct; `RESUME` (retry), `RESUME NEXT` (skip), `RESUME
<line>`; `RESUME NEXT` across a mid-`:`-line error; nested error in handler → forced
abort with the *inner* message; `ON ERROR GOTO 0` disables (falls back to S1 abort);
`ERROR n` for a representative ERR code; `RESUME without error` (22). **Standing gates
that must stay green** (S2 touches shared error tails + the tokeniser): `unit-test`,
`array-acceptance` (150), `input`/`string`/`float`/`math`-acceptance, `diskbasic-
acceptance` (34 lean + 34 repack), the tape battery, `repack-boot`, **lean `basic.rom`
byte-identity**, and the S1 `error-acceptance` families A/B (untrapped abort + ` in N`
must be unchanged when no handler is set).

---

## 7. Space budget

Current free (post §5.7 gaps): **page-1 5 B, low 3 B** (`tools/check_reloc.py`). S2 adds:
`raise_error` head (~15–25 B), `SAVSTK` saves (2×4 B at the anchors), the FPERR→ERR map
(~10 B), the four statement/function handlers (`ON ERROR`, `RESUME`, `ERR`, `ERL`,
`ERROR`), and the new keywords (sub kwtable — sub-side bytes, not main). This **will not
fit** the 5 B/3 B main-ROM headroom. Levers, in order:

1. **Site-funnelling reclaim** (§2 choice B): rewriting the direct-print sites to
   `ld a,n`+`jp raise_error` is roughly byte-neutral-to-positive vs today's `jp
   fre_abort_low`; the FPERR sites already funnel. Measure the net first.
2. **Sub-ROM tenant** ([subrom-tenant-playbook]): the `raise_error` body, the FPERR→ERR
   map, and the `RESUME`/`ON ERROR` leaves are natural page-1/page-0 tenants — the glue
   (`ld a,n` + `jp`/`call`) stays in main. The tokens are *already* sub-side.

**Measure before deciding** (standing discipline; estimates run ~1.4×). The tenant is the
fallback, not the default. Lean stays byte-identical regardless (all repack-only).

---

## 8. Slicing (proposed)

To keep each step gate-verifiable (and honour one-item-per-session):

* **S2a — dispatcher + ERR/ERL + ERROR n.** `raise_error` head, `SAVSTK`, RAM cells,
  site-funnelling (choice B), FPERR→ERR map, the `ERR`/`ERL` functions, `ERROR n`, and
  the `ERROR`/`ERR`/`ERL` tokens. NO trapping yet (`ONELIN` always 0) — so this is
  behaviour-preserving for untrapped errors (S1 gates stay green) and independently
  testable via `ERROR n` + `PRINT ERR`. This is the big structural slice.
* **S2b — `ON ERROR GOTO` + the trap branch + `RESUME`.** Adds `ONELIN`/`ONEFLG` writers,
  the trap branch in `raise_error`, `ERRRESUME` capture, the `RESUME` family, and the
  `ON`/`RESUME` tokens. This is where trapping goes live.

Each slice: its own DoD includes running the openMSX acceptance suites (the
[gate-during-implementation] lesson — a green build that was never RUN can be
catastrophically broken).

---

## 9. Open decisions (need sign-off)

1. **§2 integration A vs B.** Recommend **B** (site-funnelling into `raise_error`) — it
   makes `ERR` correct everywhere with one path and is ~byte-neutral. Confirm.
2. **`ERL` direct-mode sentinel.** Recommend 65535 (GW/MSX convention); pin exact black-
   box in S2a. Confirm the method (crunch+run on VG-8020) is acceptable given the clean-
   room firewall (it is a black-box behaviour read, not a ROM disassembly).
3. **`RESUME` context capture point.** Recommend capturing the erroring statement ptr at
   trap time into `ERRRESUME` (not reconstructing later). Confirm.
4. **Slice boundary S2a/S2b** as above (dispatcher-without-trap, then trap+RESUME), or a
   single combined slice. Recommend the split (each independently gate-able).
5. **Scope confirm:** `ERROR n`, `ON ERROR GOTO`/`GOTO 0`, `RESUME`/`NEXT`/`<line>`,
   `ERR`, `ERL`. Out of S2: `ON ERROR RESUME NEXT` (MSX2), disk/`FIELD` ERR codes ≥ 50,
   `load_error` (ERR 19) unification (still its own later item, S1 §9.1).

---

## 10. Clean-room

Original code; statement/function semantics + ERR-code numbering from the published
MSX-BASIC language reference (allowed-source L110, grade B); token bytes oracle-locked by
black-box crunch on the VG-8020 (no ROM disassembly, [no-reference-rom-disasm]). The
`ON ERROR` transcript oracle (§6) is a black-box behaviour capture.
