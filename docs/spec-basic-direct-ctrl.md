# Direct-mode control flow — spec + as-built

Status: **LANDED**. Gate: `make direct-ctrl-acceptance` (40/40 vs Philips VG-8020).
Probe: `probes/basic/basic_probe_direct_ctrl.py`. Repack build only
(`IF ROM_BASE < $4000`); the lean 16 KB cart is byte-full at its `$8000` ceiling
and stays byte-identical.

Everything in §1 is **measured on a real Philips VG-8020 under openMSX**, black
box, observed outputs only. No reference-ROM disassembly (CONTRIBUTING.md).

---

## §0 — The report, and what was actually wrong

Reported 2026-07-26: a direct-mode `FOR ... NEXT` typed at the prompt raises
`out of memory` on the repack build, while the same loop inside a **stored**
program runs fine and the VG-8020 accepts both.

```
FORI=1TO7:NEXT                    -> out of memory
FORI=1TO7:NEXT:PRINT1             -> out of memory
A=1:A=2:PRINTCHR$(35);A;CHR$(35)  -> works ("# 2 #")
```

Characterizing it turned up **two independent defects on the same path**, and
the reported one is the less serious:

**D-DIR-1 — the control-stack pointers were never initialised.** `GSP` (`$E041`)
and `FSP` (`$E043`) were written in exactly one place, `run_program`. Cold boot
never touched them, so before the first `RUN` both held power-on RAM garbage.
openMSX leaves `$FFFF`, which is above both `GOSUB_STK_END` and `FOR_STK_END`,
so the very first typed `FOR` or `GOSUB` took the depth-overflow arm and raised
ERR 7. Readable straight from the prompt:

```
PRINT PEEK(&HE043)+256*PEEK(&HE044)
  ->  65535   at boot        (garbage: every direct FOR/GOSUB is ERR 7)
  ->  57456   after any RUN  ($E070 == FOR_STK)
```

**D-DIR-2 — `exec` is a statement walker, not the interpreter loop.**
`dispatch_line` ran a typed line with a bare `jp exec`. But every control
transfer in this interpreter is *deferred*: a statement raises a flag and
returns, and the loop **around** `exec` services it — `GOTOFLAG`+`GOTOTGT`
(branch to a line), `RESUMEFLAG`+`RESUMEPTR` (resume at an exact token
position), `ENDFLAG` (stop). In direct mode nothing serviced them, so the
transfer was computed and then dropped on the floor:

| typed line | before | after |
|---|---|---|
| `GOTO 10` | **silent no-op** | branches |
| `IF 1 THEN 10` | **silent no-op** | branches |
| `ON 1 GOTO 10` | **silent no-op** | branches |
| `FOR..NEXT` | ERR 7, and left `RESUMEFLAG` raised for the next `RUN` | loops |
| `GOSUB`/`RETURN` | ERR 7 | works |
| `RUN` | worked | worked |

`RUN` was the sole survivor because it is an *editor command* recognised before
the crunch, not a statement.

The two defects interact, and the order matters: **fixing D-DIR-1 alone would
have been worse than the bug.** With the stacks initialised but the loop still
absent, `FORI=1TO7:NEXT` stops erroring and instead silently executes its body
zero times — a loud failure traded for a wrong answer.

---

## §1 — Reference behaviour (VG-8020, measured)

### §1.1 Direct FOR/NEXT and GOSUB/RETURN

Ordinary semantics, identical to the stored-program case:

| case | typed | result |
|---|---|---|
| sum | `A=0:FORI=1TO7:A=A+I:NEXT:PRINT#;A;#` | `28` |
| exitvar | `FORI=1TO7:NEXT:PRINT#;I;#` | `8` |
| body | `FORI=1TO3:PRINT#;I;#;:NEXT` | `1 2 3` |
| step3 | `A=0:FORI=1TO9STEP3:A=A+I:NEXT` | `12` |
| stepneg | `A=0:FORI=3TO1STEP-1:A=A+I:NEXT` | `6` |
| zerotrip | `A=0:FORI=2TO1:A=A+1:NEXT:PRINT#;A;I;#` | `1 3` — **bottom-tested**, body runs once |
| nest | 2×3 nested, bare `NEXT`s | `6` |
| nestnamed | same with `NEXTC:NEXTB` | `6` |
| gosub | `10 A=A+5:RETURN` / `A=0:GOSUB10:PRINT#;A;#` | `5` |
| gosubnest | GOSUB from inside a GOSUB | `6` |
| forgosub | `A=0:FORI=1TO3:GOSUB10:NEXT` | `6` |

`zerotrip` reproduces the oracle value already recorded in
`basic_probe_loops.py`: MSX-BASIC's `FOR` is bottom-tested.

### §1.2 A control frame OUTLIVES the typed line that made it

This is the measurement that decides the whole design.

| case | typed | result |
|---|---|---|
| for_then_next | `FORI=1TO3` ⏎ `NEXT:PRINT…` | **`Syntax error`** |
| next_alone | `NEXT:PRINT…` | `NEXT without FOR` |
| return_alone | `RETURN:PRINT…` | `RETURN without GOSUB` |
| gosub_noret | `10 A=7` ⏎ `GOSUB10` ⏎ `PRINT#;A;#` | `7` |

`for_then_next` is **not** `NEXT without FOR` — so the frame from the first
typed line was still on the stack when the second line ran. Its resume pointer
then addressed a buffer the second line had already overwritten, and the ROM
resumed into that garbage. So: **command level does not empty the control
stacks.** A blanket "reset at every prompt" would have been measurably wrong,
and would also have broken CONT (§1.4).

`gosub_noret` shows a typed `GOSUB` into a line with no `RETURN` runs to the end
of the program and returns to command level normally.

### §1.3 What DOES empty the control stacks

| after `FORI=1TO3`, then… | `NEXT` reports |
|---|---|
| `NEW` | `NEXT without FOR` |
| `CLEAR` | `NEXT without FOR` |
| `RUN` | `NEXT without FOR` |
| (nothing — next typed line) | frame survives, §1.2 |

Cold boot, `RUN`, `NEW`, `CLEAR`. Exactly the four.

### §1.4 Break, STOP, END and CONT at the prompt

| case | typed | result |
|---|---|---|
| stop_direct | `PRINT#;1;#:STOP:PRINT#;2;#` | `# 1 #` then **`Break`** — no line suffix |
| stop_run | same as lines 10/20/30, `RUN` | `# 1 #` then **`Break in 20`** |
| stop_cont | direct STOP, then `CONT` | **`Can't CONTINUE`** |
| cont_in_for | stored program STOPs *inside* a live FOR, then `CONT` | resumes and finishes the loop (`6`) |
| end_direct | `PRINT#;1;#:END:PRINT#;2;#` | `# 1 #`, silent |

Two hard constraints fall out. A direct-mode break prints a **bare** `Break`
and leaves **no** CONT resume point. And `cont_in_for` is why the §1.3 reset
hook cannot be widened: `CONT` must find the FOR frame still live.

### §1.5 Direct mode is a property of the LINE, not of how it was reached

| case | typed | result |
|---|---|---|
| err_in_line | `10 PRINT#;1;#:FNORD 3` ⏎ `GOTO10` | `# 1 #` then **`Syntax error in 10`** |
| — | `10 FNORD 3` ⏎ `GOSUB10` | **`Syntax error in 10`** |
| err_after_ret | `10 A=7:RETURN` ⏎ `GOSUB10:FNORD 3` | **`Syntax error`** (no suffix) |

A typed `GOSUB` into a stored line reports **run mode**; the `RETURN` back into
the rest of the typed line reports **direct mode** again. So the mode flag must
track the line currently executing, and must flip back — it cannot be a sticky
"this dispatch was a typed line" bit.

---

## §2 — Design decisions

**D-DIR-1 (a): reset the control stacks in `clear_vars`, not `run_prog`.**
`clear_vars` has exactly the four call sites §1.3 requires — cold boot
(`interp.asm init`), `RUN`, `NEW`, `CLEAR` — and already carries the same
"single hook covering all four" argument for the RND seed. The 12 bytes move out
of `run_prog`, so the change is **net zero** and the lean build keeps its inline
copy byte-identical.

**D-DIR-2 (a): execute a typed line as a VIRTUAL LINE through the existing run
loop.** Rejected alternative: a second, direct-mode-only statement loop
duplicating the flag servicing. It would have had to re-derive the same
`GOTOFLAG`/`RESUMEFLAG`/`ENDFLAG` handling, and §1.2/§1.5 mean it would then
need to hand control to the *real* loop on a branch and take it back on a
`RETURN` — two seams instead of none.

**D-DIR-2 (b): the line header lives in ROM and overlaps itself.** See §3.

**D-DIR-2 (c): `DIRECTF` is DERIVED, never carried.** See §5.

**D-DIR-3: interrupt traps do NOT dispatch in direct mode — DEFERRED, not
decided.** See §6.

---

## §3 — `dir_line`: the virtual line header

A stored line is `[link:2][lineno:2][tokens…][00]`, and the loop's end-of-line
step is "`CURLINE := link`, then a `$0000` link means end of program". Give the
typed line a header of that shape and the loop needs no direct-mode special case
anywhere:

```asm
dir_line:       dw      dir_line + 2        ; [link] -> the word below
                dw      0                   ; [lineno] = 0 == the $0000 end marker
```

Four bytes of **ROM**, and the two words **overlap on purpose**: the link points
at the lineno field, whose value `0` is simultaneously the end-of-program
marker. Running off the end of a typed line therefore takes the loop's ordinary
fall-through and then its ordinary "end of program" exit, back to the REPL.

Why ROM and not RAM: the header is entirely constant, so a per-line write is
pure cost; nothing can corrupt it; and it claims no RAM.

Why not the stored program's own end marker at `(PRGEND)`: a typed `NEW` /
`LOAD` / line edit moves that **mid-line**, so a snapshot taken at dispatch
would already be stale by the time the line ended.

The `[lineno]` field is never printed — `print_in_lineno` and `record_errline`
are the only two readers of `CURLINE+2` in this build and both take their
`DIRECTF` branch first (§5). Its value is `0` anyway, so even a missed gate
could only print `in 0` rather than garbage.

---

## §4 — Entry: `dispatch_line`

```asm
                ld      hl,dir_line
                ld      (CURLINE),hl        ; CURLINE == dir_line IS direct mode
                xor     a
                ld      (ENDFLAG),a
                ld      (RESUMEFLAG),a
                ld      (GOTOFLAG),a
                ld      hl,TOKBUF
                jp      rp_exec
```

The three flag clears are load-bearing, not hygiene. Direct mode never read
`ENDFLAG` before, so a leftover `1` from the previous `STOP` would abort the new
line before its first statement; and a stale `RESUMEFLAG` — exactly what the
broken direct `NEXT` used to leave behind — would divert it. `run_prog` clears
the same three for the same reason.

`CONTVALID` is deliberately **not** cleared: typing a statement must not
invalidate a pending `CONT`.

---

## §5 — `DIRECTF` is derived at `rp_exec`

§1.5 rules out a sticky flag. `rp_exec` is the single point every line entry
**and** every mid-line resume passes through, so the flag is recomputed there
and cannot go stale:

```asm
                ld      a,(CURLINE+1)
                cp      dir_line >> 8
                ld      a,0                 ; (xor a would clobber the flags)
                jr      nz,rpe_mode
                inc     a
rpe_mode:       ld      (DIRECTF),a
```

The **high byte alone** decides it. `CURLINE`'s value set is small and
enumerable: a stored line's link address, always in `[TXTBASE $8001, TXTMAX
$BE00)`; `dir_line`; and `dir_line+2` (what the fall-through leaves behind after
a typed line ends). ROM and the text area are disjoint, so the only address
sharing `dir_line`'s page is `dir_line+2` — and `rp_lp` returns to the REPL on
that one before ever reaching `rp_exec`.

Three consumers then follow from §1.4/§1.5, all reading the same flag:

* `print_in_lineno` suppresses the ` in <line>` suffix. The gate lives **there**,
  at the single place that reads `CURLINE+2` for output, so `do_break`'s tail
  stays one unconditional jump and §3's lineno field never needs initialising.
  (`fre_abort_low` keeps its own `DIRECTF` test — it picks `print_string` vs
  `print_string_stopcr`, so it must branch *before* it prints.)
* `do_break` skips `CONTVALID` (`ld a,(DIRECTF) : xor 1` — the whole gate).
* `rp_break` takes the classic break directly, bypassing the STOP-trap latch arm
  (§6).

---

## §6 — DEFERRED: interrupt traps at the prompt (D-DIR-3)

Before this slice a typed line never entered the run loop, so **no trap could
ever fire at the prompt**. Routing direct mode through the loop would have made
that start happening as a *side effect* of a FOR/NEXT fix.

Whether the reference dispatches `ON KEY` / `ON SPRITE` / `ON INTERVAL` handlers
at command level is **UNMEASURED**. Until it is characterized, `rp_trapchk`
returns the conservative answer — preserve today's behaviour — with one RAM
load:

```asm
                ld      a,(DIRECTF)
                or      a
                jr      nz,rp_run
```

`rp_break` skips the STOP-trap latch arm for the same reason; without that, a
`STOP ON` armed by a program would make Ctrl-STOP stop breaking typed lines.

**To close this:** characterize `ON KEY GOSUB` + `KEY(1) ON` armed by a stored
program that then `STOP`s, followed by a keypress at the prompt. If the
reference fires, delete both gates.

---

## §7 — Known divergence: resuming into a clobbered buffer

§1.2's surviving frame holds a resume pointer into the line buffer, which the
*next* typed line overwrites. Both ROMs then resume into whatever their own
buffer now holds, so the exact aftermath is an artifact of buffer layout:

| case | VG-8020 | zerobas |
|---|---|---|
| `FORI=1TO3` ⏎ `NEXT:PRINT…` | `Syntax error` | `Syntax error` |
| `10 A=1` ⏎ `GOSUB10` ⏎ `RETURN:PRINT…` | (silent, `Ok`) | `Syntax error` |

Not reproducible clean-room and not worth reproducing. The gate judges these two
cases on the **semantic** claim only — that the frame was still there, i.e.
neither side reports `next without for` / `return without gosub` — and marks
them `ok*`. `for_then_next` is judged that way **even though the two sides agree
exactly**: an agreement reached for the wrong reason is not evidence
(cf. the `PRINT TAB(99999)` case in the MSX1 keyword sweep).

---

## §8 — The gate

`probes/basic/basic_probe_direct_ctrl.py`, six groups, 40 cases:
`direct` (16) · `cross` (4) · `stored` (4) · `xfer` (6) · `break` (6) ·
`reset` (4).

**It is boot-per-case, and must stay that way.** D-DIR-1 is a cold-boot-state
defect: in a batched run the first case that `RUN`s a stored program initialises
`FSP`/`GSP` for the whole boot, and every later direct-mode case then passes — a
green gate over a live bug. `--batch` exists for a quick look and prints a
warning.

Three apparatus traps found while building it, all worth remembering:

* **The `break` group was green while measuring nothing.** `_norm` reduced a
  case to its `#…#` marker spans and fell back to the last screen row *only when
  no marker printed* — but five of the six `break` cases print a marker, so the
  ` in <line>` suffix that is the group's entire subject never entered the
  comparison. All six passed; deleting the §5 suffix gate outright would not have
  turned one red. Proved by doing exactly that: with the gate removed the build
  prints `break in 0` and the group now reports **4/6**. `_norm(with_report=True)`
  appends the break/error report rows for that group, and the suffixes are
  compared on both sides: `break` (direct) vs `break in 20` (run), `syntax error
  in 10` (typed `GOTO` into a stored line) vs bare `syntax error` (back in the
  typed line). Same family as the T4 cadence gate — **a gate's denominator must
  be measured, not assumed.**

* The VG-8020 paints a **function-key bar** on the bottom SCREEN-0 row and
  zerobas does not. Left in, it became the "last text on screen" for every case
  that printed no marker, so three different reference errors (`Syntax error`,
  `NEXT without FOR`, `RETURN without GOSUB`) all reduced to the same string —
  the comparison was blind to exactly the error-identity distinction the `cross`
  group exists to make.
* Falling back to *the last 40 characters* of the flattened screen cut at a
  different point on each machine, because the prompts differ in width (`Ok` on
  its own row vs a `zb>` **prefix**). That reported `err_after_ret` as a
  divergence when both machines had printed exactly `syntax error`. The fallback
  now takes the last meaningful **row**.

### Results

Same base, same day, boot-per-case both times:

```
pre-fix   10/40
post-fix  40/40
```

Re-run boot-per-case on the GOLFED tree that actually ships (`180ac02` base,
clean build), after the `break` group was repaired per the third apparatus trap
above: **40/40**. Both numbers matter — the pre-golf 40/40 was measured on a
draft that did not fit, and the `break` group's six cases were passing without
comparing the suffix at all, so neither reading alone gated the shipped bytes.

Falsification of the repaired group, same tree: delete the §5 `DIRECTF` gate in
`print_in_lineno`, rebuild, re-run → **4/6**, `stop_direct` and `stop_cont` both
reporting `break in 0`. The gate can produce a non-zero answer.

Regression suites on the shipped build: `unit-test` **52/52 files**; the
trap/error/time battery re-run in full (see the commit).

### Cost

Page-1 free after the slice: **8 B**, from a CLEAN tree
(`rm -rf build && make basic-reloc`) on the `180ac02` base — i.e. with T5
INTERVAL landed. The low region has 5 B free.

The last 3 B of that came from the slice paying itself back. Deriving `DIRECTF`
(§5) made `ex_cont`'s explicit `DIRECTF := 0` **dead**: `ex_cont` ends in
`jp rp_lp`, which reaches `rp_exec` via `rp_resume` before any statement runs,
and `rp_exec` recomputes the same 0. "The same 0" is the part that needed
proving rather than asserting — it holds because `do_break` gates `CONTVALID`
on `DIRECTF`, so a direct-mode break stores no resume point and `CONTLINE` is
therefore *always* a stored line's link address, never `dir_line`. Traced, not
inferred from the comment: no label sits between `ex_cont:` and `ex_cont_no:`,
so nothing enters the tail mid-block; and none of the six `DIRECTF` readers is
reachable between the removed write and the derive (four are past `rp_exec`,
the other two are error-raise paths and the tail cannot raise).

⚠️ An earlier draft of this section read **60 B**, measured on the older
`1addfbc` base. That figure was never wrong for what it measured and is
useless as a ceiling check: `1addfbc` predates T5 INTERVAL, which took the
tree 14 B **over** the page-1 ceiling on its own (`f973e1c`). The slice's
first draft then landed on top of that overrun, and only the golf below
brought the combined tree back under. Read the wall from a clean build of the
tree you are actually shipping — [[measure-the-wall-from-clean]].

The first draft overran the ceiling and was golfed by ~20 B — the ROM header of §3
(−6 B, and one fewer RAM cell), the high-byte compare of §5 (−4 B), moving the
suffix gate into `print_in_lineno` (−1 B), dropping the now-dead explicit
`DIRECTF := 1` in `dispatch_line` (−5 B), and not writing the `[lineno]` field
(−6 B).
