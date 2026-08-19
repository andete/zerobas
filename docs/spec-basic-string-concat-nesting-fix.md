# Spec — string-concat nesting fix (`STRCAT_R` re-entrancy)

Status: **DEFERRED to slice 4** (2026-07-16). Root cause + fix + gate cases are
fully verified below; the fix is a correct +6-byte change to `sct_loop`, BUT the
repack **low region is at 0 free bytes after arrays slice 3** (`__MEAS_LOW_END ==
$4000`), so it trips the hard `$4000` overflow guard
(`STRING_ENGINE_OVERRAN_4000...LOW_REGION_FULL`). No clean incidental 6-byte
reclaim exists (the arrays error strings are oracle-locked capitalised
`fre_msgtab` entries, not dupes; other same-text strings differ in case/region).
Landing it now would require a sub-ROM offload of a low-region routine (real work
+ risk). **Slice 4 relocates the whole string engine (STRMAX→255 + a real string
heap), reworking `str_concat_tail`'s storage with room to spare — fold this fix in
there.** User decision 2026-07-16 (deferred over a sub-ROM offload; the bug is
pre-existing + narrow). This doc IS the slice-4 hand-in for it.

Scope: one focused defect fix in the repack-build string-concat spine. Repack-only.
Found: 2026-07-15, during arrays slice-3 adversarial review. **Not caused by the
arrays diff** — a pre-existing bug in `basic/str-engine.asm` `str_concat_tail`.

---

## 1. The bug

REPRO (differential, VG-8020 reference vs the `C-BIOS_MSX1_EU_REPACK_DISK` repack
build, via `probes/lib/omsx_repl.py`):

```
?"[";"A"+MID$("XY"+"Z",1,2)+"B";"]"
  reference : [AXYB]
  zerobas   : [XYZXYB]   (WRONG)
```

General shape affected: **`a$ + fn$(b$+c$, …) + d$`** — an outer `+` chain in which
some operand *after the first* is a string function whose own argument contains a
`+` concat. This includes a string-array element store whose RHS has that shape.

## 2. Root cause (confirmed by reading the code)

`str_concat_tail` ([str-engine.asm:414](../basic/str-engine.asm:414)) keeps the outer
accumulator's address in the **single global** `STRCAT_R` (`$E55D`, one word,
[sysvars.inc:497](../basic/sysvars.inc:497)) and **re-reads it from that global on
every loop iteration**:

```
sct_loop:
    ...
    call    str_eval_one        ; evaluate the next operand
    jr      nc,sct_err
    push    hl
    ld      de,(STRCAT_R)       ; <-- re-reads the global as the append destination
    ld      hl,(STRPTR)
    call    str_append_desc     ; R := R + operand
```

When the operand is a string function whose argument concats (`MID$("XY"+"Z",…)`),
evaluating it recurses back through `str_eval` → `str_concat_tail`, which allocates
its **own** accumulator and overwrites `STRCAT_R` with the *inner* address. It never
restores the caller's value. The outer loop's `ld de,(STRCAT_R)` then appends into
the *inner* temp and abandons its own: the `"A"` prefix is lost and the inner
`"XYZ"` scratch leaks into the result → `[XYZXYB]`.

Only operands *after* the first trigger it: operand 1 is copied via `str_copy_desc`
with `DE` set from the fresh alloc (not re-read from the global), and `sct_go`
re-stores `STRCAT_R` right after, so a function-with-concat in operand-1 position is
harmless.

### Not the documented depth deviation
The str-engine header documents an own-design N=3 temp-ring depth limit (a deeper
nest reuses the oldest slot). This repro has **one** function operand → peak live
temps = outer-R + inner-concat-R + function-result = **3 = N**, no wrap. So this is a
genuine re-entrancy bug, *within* the documented limit — not the depth deviation.
(A `a$ + f$(..) + g$(..)` chain with **two** function operands *would* wrap the ring
and hit the documented deviation; that is explicitly out of scope here — see §5.)

## 3. Proposed fix

Make `str_concat_tail` re-entrant w.r.t. `STRCAT_R` by **saving its own accumulator
across the operand eval and restoring the global afterward**, entirely inside the
loop (self-healing at every nesting level). Diff to `sct_loop` only:

```
sct_loop:
                inc     hl                  ; past the '+'
                call    skip_spaces         ; HL -> the next operand
                ld      de,(STRCAT_R)       ; DE = OUR accumulator R
                push    de                  ; preserve it across the operand eval: a nested
                                            ;   string-function arg runs its own str_concat_tail,
                                            ;   which overwrites STRCAT_R.
                call    str_eval_one        ; STRPTR -> operand, HL advanced, CF set/clear
                pop     de                  ; DE = OUR R again (pop leaves CF from str_eval_one)
                ld      (STRCAT_R),de       ; restore the global for the rest of this expression
                jr      nc,sct_err          ; malformed operand
                push    hl                  ; save advanced cursor
                ld      hl,(STRPTR)         ; HL = operand (source); DE already = R
                call    str_append_desc     ; R := R + operand (clamped)
                pop     hl                  ; restore cursor
                ; ... rest of loop (another-'+' check, tail) UNCHANGED ...
```

Correctness notes:
- `pop de` and `ld (STRCAT_R),de` do not touch flags, so the `CF` from
  `str_eval_one` survives to `jr nc,sct_err` unchanged.
- After the restore, `STRCAT_R` is authoritative again, so the unchanged tail
  (`ld hl,(STRCAT_R)` → `ld (STRPTR),hl`) and every later iteration read the caller's
  own accumulator.
- The original `ld de,(STRCAT_R)` after the eval is deleted (DE already holds R).

Alternative considered — a full restructure that keeps R on the CPU stack for the
whole loop and drops the global reads. Rejected: the loop's cursor push/pop/peek
discipline is intricate and this is a clean-room, reference-locked routine at a tight
byte margin; the localized save/restore is the lower-risk change. (This is option 1
of the handoff's fix-shape, applied per-iteration rather than whole-loop.)

## 4. Byte budget

Net size change: **+6 bytes** (added `ld de,(STRCAT_R)`+`push de`+`pop de`+
`ld (STRCAT_R),de` = 10; removed the post-eval `ld de,(STRCAT_R)` = 4). HL can't
be used for the cheaper 3-byte `ld hl,(nn)` encoding — HL holds the live cursor at
that point; and a stack-resident accumulator is not viable (Z80 has no SP-relative
load, which is precisely why the routine uses the `STRCAT_R` global).

**Space status (2026-07-16, arrays slices 1+2+3 SHIPPED):** the repack low region
(`$2812–$3FFF`) is **0 bytes free** — `__MEAS_LOW_END == $4000`. Slice 3 consumed
the last of it (65-B string elements + the D1 `is_letter` guard + the
`ary_op0_resolve` dedup). So the +6 fix **overflows the hard `$4000` guard**
([main.asm:114](../basic/main.asm:114), the
`STRING_ENGINE_OVERRAN_4000...LOW_REGION_FULL` tripwire — confirmed 2026-07-16 by
applying the fix and building). The old "77 bytes free at HEAD" note above was the
PRE-slice-3 baseline and no longer holds.

→ **Deferred to slice 4** (§Status). When slice 4 relocates the string engine
(STRMAX→255 + real heap), `str_concat_tail`'s accumulator handling is rebuilt and
this +6 lands trivially — likely for free, since a heap-based accumulator may not
need the global round-trip at all. No page-1 pressure either way (str-engine is a
page-0 low-region tenant). Alternatively, if this must ship BEFORE slice 4, a
sub-ROM offload of a self-contained low-region routine reclaims the 6 bytes.

## 5. Lean build

Unaffected and must stay **byte-identical**. `str-engine.asm` is wholly inside
`IF ROM_BASE < $4000`; the lean 16 KB build has no concat (`str_eval ≡ str_eval_one`,
[strvar.asm:42](../basic/strvar.asm:42)). Verify with the lean-identical check.

## 6. Gate cases (add to the string-acceptance corpus)

Add to the EXECUTE half, `probes/basic/basic_probe_string.py` `CASES` (repack-only;
each expected value is short — no STRMAX clamp — so it equals the VG-8020 reference,
i.e. differential-in-effect). All cases have **exactly one** function-with-concat
operand (peak = N=3 live temps, within the documented ring depth):

| label | line | expect |
|---|---|---|
| `concat.fn-mid`  | `PRINT "[";"A"+MID$("XY"+"Z",1,2)+"B";"]"` | `[AXYB]` (the repro) |
| `concat.fn-last` | `PRINT "[";"A"+MID$("XY"+"Z",1,2);"]"`     | `[AXY]`  |
| `concat.fn-var`  | `A$="A":PRINT "[";A$+MID$("XY"+"Z",1,2)+"B";"]"` | `[AXYB]` (var-lead operand 1) |
| `concat.fn-rt`   | `PRINT "[";"P"+RIGHT$("XY"+"ZW",2);"]"`    | `[PZW]`  (different function) |

Explicitly **excluded** (documented N=3 deviation, not this bug): a two-function
chain such as `"A"+MID$("XY"+"Z",1,2)+LEFT$("PQ"+"R",2)` — the 2nd function's inner
concat wraps the ring onto the outer accumulator. Out of scope; do not gate it as
reference-equal.

Before/after: all four FAIL on the current build (mis-nested result), PASS after the
fix. Re-run `make string-acceptance` (full six halves) to confirm no regression.

## 7. Provenance

Clean-room: the concat spine + temp ring + `STRCAT_R` are zerobas's own design (no
disassembly). The fix is a re-entrancy correction to own code. Note in
`basic/PROVENANCE.md` alongside the existing concat entry if the arc requires; the
concat semantics remain the public MSX-BASIC left-to-right/truncate reference.

## 8. Acceptance

1. Four gate cases go red → green.
2. `make string-acceptance` (full) green.
3. Lean build byte-identical.
4. Repack reloc image assembles under the `$4000` guard (low-region free ≥ 0).
