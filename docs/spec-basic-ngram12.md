# D-NGRAM12 — one `load_commit_prog` for the tape and disk program loaders

*2026-08-30. `basic/cload.asm` (body + alias + one widened jump). Arms
`scratchpad/ngram12_knives.py`, scored on the STANDING batteries
`runtail-acceptance` (disk) and `castail-acceptance` (tape).*

**Cost: −21 B** — main page 1 323 → **344 B** free. Low region, sub p0 and sub
p1 unchanged. **Rows: 9 disk + 2 tape, all agreeing with the references before
and after.**

## 1. The carve

`do_tape_prog` (CLOAD, a tokenised tape) and `disk_prog_load` (`LOAD"file"`)
each ended with the SAME ten instructions, byte for byte:

```
                ld      hl,(CLPTR)
                ld      (PRGEND),hl
                ld      (hl),0
                inc     hl
                ld      (hl),0
                ld      hl,TXTBASE
                ld      (TXTTAB),hl
                call    relink
                or      a
                ret
```

22 B each. `dpl_done`'s **entire body** was those ten instructions, so this is
not a shared tail costing a jump per site — it is an `equ` alias costing
**nothing**:

```
dpl_done        equ     load_commit_prog
```

`do_tape_prog` falls through into the body from its `CAS_VERIFY` test, so it
needs no jump either. The gross saving is the full 22 B.

## 2. −22, then +1: the `jr` that no longer reached

`disk_prog_load`'s `jr z,dpl_done` was in relative range of a body sitting a few
lines below it. Aliased to `load_commit_prog` — some 250 B earlier in the file —
it is not, and pasmo says so:

```
ERROR: Relative jump out of range  on line 992 of file basic/cload.asm
```

Widened to `jp`. **The net is 21 B, and the assembler is the thing that priced
it** — the estimate said 22. This is the fourth time in this arc that adding or
moving bytes has pushed a `jr` out of range; it is a routine cost of the shape,
not a surprise, and the comment at the site now records why the jump is long.

## 3. Why the dup-span sweep never found it

`tools/dupspan_indep.py` compares whole LABEL BLOCKS. Here only one of the two
blocks is the run: `ctp_done` opens with `call TAPIOF`, a `CAS_VERIFY` test and
a conditional exit, and *then* runs the ten instructions. A sweep keyed on label
blocks sees a 14-instruction block and a 10-instruction block and reports no
match — which is exactly the hole recorded as *a span is byte-identical without
being entered the same way*, seen from the other side: here the spans ARE
entered compatibly, and the sweep still cannot see it because one of them starts
mid-block.

**The n-gram sweep finds it because it does not care about labels** — only that
a run of instructions repeats and cannot be entered in the middle.

## 4. 🔴 K-N12A cut the end marker and every disk row held — and they were right to

The first knife cut the `$0000` end-of-program marker the shared body writes.
**Predicted: five rows, on both transports. Moved: one — the tape row.**

`cas2-cload:listing` became `10 PRINT"ZQ9" / 0`: a spurious line listed past the
program, exactly what an unterminated store looks like. Every disk row read
correctly.

The disk rows were not wrong; they were **blind, for a reason that is worth
stating**. `runtail`'s fixture is

```
10 PRINT"ZQ9"  :  SAVE"A:RT.BAS"  :  NEW  :  LOAD"A:RT.BAS"  :  LIST
```

so the program being loaded is **byte-identical to the one just typed**, and the
`$0000` the cut failed to write is still in RAM from the typed copy. Nine rows
agreed with the reference for a reason that had nothing to do with the marker.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

**The fix is a row, not a looser expectation.** `load-short` leaves a *longer*
program resident (`10`/`20`/`30`) and loads the one-line file over it, so the
bytes past the loaded line are a real line the loader must terminate away. Under
K-N12A it moves; on a clean tree it agrees with the CF-3300.

⚠️ **`runtail-acceptance` had this hole for as long as it has existed** — it is
not a hole this slice opened. What the slice did was give it a knife.

## 5. The two knives separate the body's two outputs

| knife | cuts | moves |
|---|---|---|
| K-N12A | the `$0000` marker it **writes** | `cas2-cload:listing` (tape), `load-short:listing` (disk) |
| K-N12B | `or a` → `scf`, the CF it **returns** | `run-hit`, `run-hit-res`, `loadr-hit` (disk) |

Neither knife alone witnesses both callers; **together they do**, and that is
what the collapse needed. K-N12A is entered from the tape side and now the disk
side; K-N12B proves `disk_prog_load` genuinely returns *through* the shared body
— under it the three rows that RUN what was loaded print nothing at all, because
CF set means *the load failed and has already reported* (D-CASTAIL / D-RUNTAIL).

🟢 **The controls hold under both.** `bare-run` (a program TYPED in, never
loaded), `run-miss`, `run-miss-res`, `loadr-miss-res` (nothing is loaded), and
`load-plain` / `load-short` (LOAD without `,R` has nothing to refuse) do not
move. K-N12B moves the *running* half and leaves the *listing* half alone; if a
knife to one output moved everything, it would be evidence the apparatus, not
the body, was what broke.

## 6. 🔴 A partial read scored as a total reddening

K-N12B breaks a POSITIVE CONTROL, so `basic_probe_runtail` stops scoring and
re-prints every row with a `....  (not scored)` prefix — a prefix the knife
runner's row regex did not know. It parsed the two TAPE rows, parsed none of the
nine disk rows, and then scored all nine as **moved**, because
`cut.get(label)` is `None` for a row that was never read.

The `if not cut:` guard could not catch it: `cut` was not empty. The verdict —
*K-N12B reddens everything* — was wrong in the most flattering possible
direction, and would have read as an unusually strong arm.

`capture()` now returns the baseline labels a run did **not** print, and the
runner refuses on any. **An unread row is not a moved row.**
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]

## 7. Falsification

| claim | what would refute it | result |
|---|---|---|
| the two tails were byte-identical | the assembler, or a moved row on a clean tree | 11 disk + 31 tape rows agree with the references, before and after |
| the collapse saves 22 B | `make basic-reloc` | −21: the estimate was right and the `jr` widening cost the 22nd |
| both callers enter the shared body | a knife at the body that moves only one transport's rows | K-N12A moves a tape row and a disk row; K-N12B moves three disk rows — **and the first pass of K-N12A moved only the tape row, which is how §4 was found** |
| `dpl_done` may be an `equ` | anything falling through into it, or a second reference | one reference (`jp z,dpl_done`), and `dpl_oom_pop` above it ends in an unconditional `jr` |
| the run occurs once now | S1 counts it in the source | 1 (it was 2), alias present, matcher alive |

## 8. What the ranking said, and what it was worth

`scratchpad/ngram_sweep.py --main` ranked this shape **first among live
candidates at 19 B**, priced as a shared tail — one site keeping the body, the
other paying a 3 B jump. It is worth **22 gross** instead, because `dpl_done`'s
*whole body* is the run and an alias costs nothing.

⚠️ **The sweep cannot see that**, and it is a floor rather than an estimate for
the same reason `clone_scout` was: the tool prices a shape, and whether a site
can be reached by a free `equ` is a property of the SITE. Worth checking on any
candidate whose second site is a whole label block.

The rest of the live `--main` board is now thin — 18 B, 16 B, 15 B, then a wall
of 14s. The two 16 B rows are ⛔ DECLINED frame-protocol shapes.
