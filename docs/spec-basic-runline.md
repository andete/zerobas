# SPEC — D-RUNLINE: `RUN <lineno>` starts execution AT that line

Status: **✅ LANDED 2026-08-22** (R1; R2 + R3 filed). Parent: D-FNRUN §2.1
([`spec-basic-fnrun.md`](spec-basic-fnrun.md)), which filed this while
converting the verb next to it — *"filed precisely so that slice cannot be read
as having fixed a form it merely learned to RECOGNISE."*
Baseline: `ee2f18a`, clean build, low **46 B** / page 1 **31 B** free.

---

## 1. The defect, re-verified before it was ranked

Measured on the current ROM (`206101a`), not carried forward from the filing:

```
10 GOTO 40 : 20 PRINT"[B]" : 30 END : 40 RUN 20
vg8020 -> B      cf3300 -> B      zb -> <Syntax error>      (n.runline)
10 PRINT"[B]" : 20 END           all three -> B             (n.runlinectl 🟢)
```

Both references restart **at line 20**. zerobas routed `LINENO_TOKEN` to
`run_prog`, which starts from `TXTBASE`, so line 10's `GOTO 40` ran again and
the statement re-entered itself.

🔴 **The face was `Syntax error`, not the silent loop that shape alone would
produce.** D-FNRUN's E-FR1 already pinned that: the extra symptom is
D-RUNTAIL's nested-run corruption at the **one arm that slice did not convert**
(`dr_stored`'s `jp run_prog`). So this is two defects stacked at one site, and
the filing was right to refuse to ship the 0-byte half alone — neither state
matches the reference, so there was no measured reason to prefer a hang over a
bogus error.

## 2. The design — no line-finder and no run loop is written

`RUN <lineno>` **is** a bare `RUN` whose `CURLINE` starts somewhere else, and
both halves already existed:

| piece | what it already does | where |
|---|---|---|
| `goto_resolve` | `find_line_bc` + the undefined-line check (ERR 8) + the `GOTOTGT` store | `basic/interp.asm`, GOTO's own tail |
| `run_prog` | every RUN reset, then `CURLINE := TXTBASE` from **one** store | `basic/program.asm` |
| `rp_goto` | proves `GOTOTGT` holds a line **link** address — exactly what `CURLINE` wants | `basic/program.asm` |

The operand grammar is GOTO's too (`$0E` + the line number LE), so the parse is
four bytes of register loads.

**`GOTOTGT` carries the start line — its second tenant.** That is safe for a
reason, not by luck: `run_prog` clears `GOTOFLAG`, and `rp_goto` is the only
reader of `GOTOTGT`, so a stale value can never be consumed. Bare `RUN` seeds
`GOTOTGT := TXTBASE` at `run_prog`, which means `run_prog_at` is entered with
the invariant already true — **no flag, no second code path, and no new RAM
cell.**

⚠️ **`RESTORE_LINE` deliberately does NOT move.** `RUN` resets the DATA cursor
to the program top; starting at line 20 must not hide a `DATA` in line 10. The
two stores were one before this slice and are now two — that separation is the
only reason the +3 B in the tail exists, and §4 rows it.

## 3. Price — measured, not estimated

`rm -rf build && make basic-reloc`, page-1 free:

| | |
|---|---|
| baseline `ee2f18a` | **31 B** |
| after R1 + R3 | **8 B** |
| **cost** | **23 B** |

💰 **The carve funded it.** Page 1 read **11 B** before D-SEEDHOLE2; this fix
needs 23. The apparatus slice is what made the BASIC fix affordable, which is
the whole point of carving.

## 4. What is shipped, and what is filed

| | form | site | status |
|---|---|---|---|
| **R1** | `RUN <lineno>` as a **statement** | `do_run` → `dr_lineno` | ✅ shipped, 23 B |
| **R2** | `RUN <lineno>` in **DIRECT MODE** | `dispatch_line` → `dl_run` | filed, ~15–17 B |
| **R3** | bare `RUN` as a **statement** | `dr_stored`'s `jp run_prog` | filed, **0 B** |

### R3 — written, measured, and BACKED OUT, because the row could not be built

🔴 **I shipped R3 and then removed it.** `jp run_prog` → `jp run_prog_top` is
0 bytes and is the arm D-RUNTAIL did not convert, so it looked free. It is not:
it changes what a bare `RUN` **inside a running program** does, and D-FNRUN had
already filed that as *"a form no row drives"*.

Trying to write the row is what showed why. **A bare `RUN` clears variables, so
a program that reaches one restarts FOREVER — on the references too.** There is
no value to read. The row has to separate *"hangs silently"* (correct) from
*"prints a bogus error then stops"* (the defect) on a **timeout**, plus a control
proving the fixture would have printed at all — otherwise the reading is the
`<NO OUTPUT>`-means-two-things trap `n.runlinectl` exists to prevent.

⚠️ **Shipping a 0-byte behaviour change beside a measured one would have put an
unrowed claim inside a rowed slice.** A deferral honoured is worth more than one
filed: R3 stays exactly where D-FNRUN left it, now with the row-design cost
written down instead of the bare price.

🔴 **R2 IS THE SAME RULE AT A SECOND SITE, AND GUARDING ONE INSTANCE OF A CLASS
IS NOT GUARDING THE CLASS** (D-LOADERR-FIX's lesson, and it broke the cassette
last time). It is filed rather than skipped, with a price:

`dispatch_line` runs `is_cmd` against the **raw `LINEBUF`, before `tokenise`**,
so direct mode never sees `$0E` — the number is still ASCII. The parse is
therefore a different mechanism: `parse_lineno` (itself a **sub-ROM tenant**,
`SUBROM_IDX_PARSELN`), not GOTO's token grammar. **One rule, two mechanisms** —
the same shape D-FNARG2 found for filenames.

Estimated ~15–17 B against **8 B** remaining, so R2 needs a carve. Its row is
built RED rather than omitted, so the class is measured even where it is not
fixed.

## 5. Rows

`probes/basic/basic_probe_namspc.py`. `n.runline` graduates from DEFERRED; the
rest are new, and three of them exist because this slice makes claims nothing
previously measured:

| row | fixture | why it exists |
|---|---|---|
| `n.runline` | `10 GOTO 40 / 20 PRINT"[B]" / 30 END / 40 RUN 20` | the defect; graduates |
| `n.runlinectl` 🟢 | `10 PRINT"[B]" / 20 END` | separates "printed nothing" from "hung" |
| `n.runundef` | `10 RUN 99` | the `Undefined line number` claim — asserted by the design, never measured |
| `n.rundata` | `DATA` above the start line, `READ` below it | the `RESTORE_LINE` claim in §2 |

⚠️ **`n.runbare` was drafted and dropped** — see R3 above.

⚠️ **R2 has no row yet either, and the fixture kind is not the obstacle.** Every
`run` row in `basic_probe_namspc.py` goes through a stored program, so `RUN 20`
*typed at the prompt* has no home there — but
[`basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py) already has a
`dir-*` battery that types lines straight at the REPL (`dir-name`, `dir-print`),
which is exactly the shape R2 needs. `namspc`'s own DENOMINATOR already names
direct mode as NOT COVERED (TODO.md's `dir-name` residual). So R2's row is a
port of an existing fixture kind, not a new mechanism — its price is the ~15–17 B
of code, not the instrument.

## 6. Falsification — 4 rows, all EXACT, run twice

`scratchpad/runline_knives.py`. Predictions written before the run; the probe is
invoked directly (never `make`), both ROM images are hashed per knife, and the
restore writes the bytes back.

| row | knife | predicted divergent | got |
|---|---|---|---|
| K-RL1 | the operand → a constant EXISTING line (30 = `END`) | `n.runline` | ✅ EXACT |
| K-RL2 | `run_prog_at` reads `TXTBASE` again (pre-slice) | `n.runline`, `n.rundata` | ✅ EXACT |
| K-RL3 | `RESTORE_LINE` follows the start line (undoes §2's split) | `n.rundata` | ✅ EXACT |
| K-RL4 | the operand → a constant line that exists in EVERY fixture (10) | all three | ✅ EXACT |

**K-RL1 and K-RL4 differ only in the constant, and that pair is the point.**
Under K-RL1 `n.runundef` stays green — but *for the wrong reason*: its fixture
is one line, so the knifed target 30 is absent too and ERR 8 is still correct.
K-RL4 picks a line that exists in every fixture, and it is the only knife that
genuinely pins that row. `n.runlinectl` 🟢 stayed green under all four.

🔴 **THE KNIVES CAUGHT A DEFECT IN THE KNIFE RUNNER FIRST.** Draft 1 reported
**0/4** with all four ROMs provably moved — it grepped the probe's rows for
`MISS`, a token this probe never prints (the marker is `DIFF`). A parser that
cannot see a divergence **reports a broken tree as clean**, which is D-WALLDATE's
draft-1 failure exactly. Two things made it legible rather than a shrug: the
**ROM-hash guard** (cuts applied + nothing detected ⇒ the instrument, not the
subject), and the fix was then **calibrated on known positives** — a clean log, a
log with one `DIFF` planted, and a log with a row deleted — before being believed.
The runner now takes a **row census** and returns an apparatus fault, not an empty
set, when the probe does not print every row it asked for.

⚠️ Every one of these is an oracle differential against **both** references
(no disk is involved, so the VG-8020 is a legitimate second reference).
