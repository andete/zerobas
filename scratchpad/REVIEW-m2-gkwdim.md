# Goldfish review (test-writer role), 2026-11-25: docs/keywords/DIM.md, ERASE.md, CLEAR.md (the specification sections)

**Records read.** I read all 42 records of `scratchpad/KDM_run1.out` (group FX, ref and zb). These are normalised
screens, so no decoding was needed. ref = zb on all 42. I read `kdim.py`, `kdim_model.py`, `kdim_controls.py`,
`dim_rules.py`, and the array / ERASE / CLEAR / `value()` / `reset()` parts of `kstop_model.py` (lines 90–215, 515–570,
640–780, 945–962). I ran `kdim_controls.py` (rc 0, 10 controls, every rule has one). I also ran the model through a
scratch harness on the typed lines proposed below. Every "model says" in this review comes from that harness. I ran
the dormant alt `clear-bound-65535` over all cases, and I swept `Basic.FREE`. I did **not** read `kwdoc_*.out`,
`clear3_run*.out`, `clearwrap_*.out`, `dimedge_*.out`, the arrdim characterisation docs, or `kdeftype_model.py`
beyond its description in spec-plan.md. I ran no emulator.

## 1. Rules not pinned by any measured case

1. **R-DIM-SIZE, the 65535-byte limit.** The cases bracket the byte threshold only to [40002, 80008):
   - `A%(20000)` (40002 B) gives 7;
   - `A(10000)` (80008 B) gives 9.

   Any threshold in that range passes, and so does "header + elements > 65535". To pin it, measure:
   - `10 DIM A%(32766)` / `RUN` (65534 B; the model says 7) against `10 DIM A%(32767)` (65536 B; the model says 9);
   - `10 DIM A!(16382)` against `10 DIM A!(16383)`;
   - `10 DIM A$(21844)` (65535 B) against `10 DIM A$(21845)`.

   The last two also give the first measurement of the 4-byte and 3-byte element sizes that the page states (2.6).
2. **R-DIM-SIZE, "a bound too large for an integer (70000) error 6".** The 6 edge is bracketed only to (10000, 70000].
   The model puts it at 32768. Measure `10 DIM A(32768)` and `10 DIM A(65535)`; the model says Overflow on both. This
   is the same shape as kerr's lesson (`ERROR 40000` is 6, where the rule had said 65535).
3. **R-DIM-BOUNDS, "bound 10 in every dimension".** Only a one-dimensional undeclared array was measured. Measure:
   - `10 B(10,10)=1:PRINT B(10,10)` (the model prints 1);
   - `10 B(0,11)=1` (9).
4. **R-DIM-BOUNDS, "any number of dimensions".** Only 2 dimensions are in KDM. The page's "32 subscripts" rests on an
   older record. Add a 3-dimensional case, for example `10 DIM A(1,1,1):A(1,1,1)=3:PRINT A(1,1,1)`, and the
   32-subscript line if the page keeps that claim.
5. **R-DIM-BOUNDS, "an integer array stores the whole part".** `1.7` gives 1, which refutes rounding. It does not
   separate truncation from flooring. `10 DIM A%(2):A%(1)=-1.7:PRINT A%(1)` gives -1 under truncation and -2 under
   flooring.
6. **R-DIM-FORMS, "a name without bounds … makes nothing".** KDM FX 16 prints `[ 0 ]` under three rival laws:
   - makes nothing;
   - makes a scalar `A`;
   - makes an array `A(10)` (the `PRINT A` reads the scalar either way).

   To separate them:
   - `10 DIM A:DIM A(2):PRINT "[M]"` (the array rival gives 10);
   - `10 X=FRE(0):DIM A:PRINT X-FRE(0)` (the scalar rival gives a non-zero result).

   The page's `DIM A,B(2)` has no case either: add `10 DIM A,B(2):B(2)=1:PRINT B(2)`.
7. **R-ERASE-REMOVE, "used, it is a new array of bound 10".** KDM FX 18 reads only `A(1)`, which is inside the old
   bound too. Measure:
   - `10 DIM A(2):ERASE A:A(10)=1:PRINT "[B]"` (the model prints `[B]`);
   - `10 DIM A(2):ERASE A:A(11)=1` (9).
8. **R-ERASE-ERRORS, "the suffix is part of the name".** Only one direction was measured (DIM `A`, then ERASE `A%`).
   - The page's "leaves `A%` and `A$` alone" has no case. Measure `10 DIM A(2),A%(2):A%(1)=3:ERASE A:PRINT A%(1)` (the
     model prints 3).
   - The table's `ERASE A,` and the Details' `ERASE A()` and `ERASE 5` have no case.
9. **R-CLEAR-RESET, "clears the variables".** Only a numeric scalar was measured. Arrays, strings and DEF FN (the
   Details say "all variables and arrays … and DEF FN definitions") have no case:
   - `10 DIM A(2):CLEAR:DIM A(2):PRINT "[C]"`;
   - `10 A$="X":CLEAR:PRINT "[";A$;"]"`;
   - `10 DEF FN F(X)=X:CLEAR:PRINT FN F(1)`.
10. **R-CLEAR-ERRORS, "past 65535 6".** The 6 edge is bracketed only to (30000, 70000]. Measure `10 CLEAR 32768`,
    `10 CLEAR 40000` and `10 CLEAR 65535`. The rule's sentence predicts 7 for all three; the model predicts 6 (see 2.1).
11. **R-CLEAR-ERRORS, the top's upper limit.** The model refuses a top above &HF380, but no rule says so. The page
    Details give "between &H8000 and &HF380", and the table has `CLEAR 200,65535`. Measure
    `10 CLEAR 200,&HF380:PRINT "[F]"` against `10 CLEAR 200,&HF381`.
12. **R-CLEAR-ERRORS, "every argument is checked before anything changes".** Only a negative size (5) was measured under
    ON ERROR. Measure the same frame with a top error and with an Out-of-memory error:
    - `10 A=5:ON ERROR GOTO 90:CLEAR 200,&H7000`;
    - `10 A=5:ON ERROR GOTO 90:CLEAR 30000`;

    each followed by `90 PRINT "[";A;"]":END`. The page also says the old string-space size stays. No case shows it:
    `10 CLEAR 500:ON ERROR GOTO 90:CLEAR 30000` / `90 PRINT FRE(""):END` should give 500.

## 2. Model laws no rule states, and rule clauses the model does not compute

1. **The CLEAR Overflow edge: the sentence states the rival's law, not the model's.**
   - `kstop_model.py:661` raises 6 at `n > 32767`. The 65535 form exists only as the dormant alt `clear-bound-65535`.
   - R-CLEAR-ERRORS says "past 65535 6".
   - I ran the alt over every case: it is FALSE on **0** of the CLEAR cases. So nothing separates the two, no control
     uses the alt, and the generated table prints a sentence the check does not compute.
   - CLEAR.md's history (D-CLEARWRAP: 32100–32767 gives 7 on both references) is consistent with both.

   Measure 1.10, then make sentence and model agree.
2. **`FREE = 28000`: one constant for DIM and CLEAR.** It ignores the string space, the program, the arrays already
   made, and the top that CLEAR n,top sets. No rule states it. The sweep shows that any `FREE` in [500, 29999] passes
   every case. So it is unpinned, which was the design, but the model still predicts with it:
   - `10 CLEAR 20000:DIM A%(5000):PRINT "[M]"`: the model prints `[M]`, but a 32 K machine cannot hold 20000 + 10002
     bytes beside the system.
   - `10 DIM A%(10000),B%(10000):PRINT "[M]"`: the model prints `[M]` (two arrays of 20002 B each).
   - `10 CLEAR 200,&H8050`: the model runs it without error. CLEAR.md's table says 7. **The model contradicts the page.**

   Either state "free memory is a fixed 28000, whatever is in use" as a law, which is false, or make FREE depend on
   `strsize`, the arrays made and `top`.
3. **Names: the model keys arrays by their full text, suffix included.** That law is in the rules ("the suffix is part
   of the name"). It differs from MSX typing and from the tree's own `kdeftype_model`, which has two significant
   characters, suffixed = unsuffixed, and DEFINT. What the model says:
   - `10 DIM A#(2):ERASE A:PRINT "[S]"`: Illegal function call, but `A` *is* `A#` under the default type;
   - `10 DIM A(3):A#(3)=1:PRINT A(3)`: 0, where 1 is expected;
   - `10 DEFINT A:DIM A(2):ERASE A%:PRINT "[D]"`: Syntax error (the model has no DEFINT);
   - `10 DIM AB1(2):ERASE AB2:PRINT "[2]"`: Illegal function call (MSX keeps 2 characters).

   The rule's real law is "the **type** is part of the name". The ERASE page's "leaves `A%` alone" holds only without a
   DEFINT.
4. **element(): negative subscript and wrong dimension count.** Both give 9 in the model; no rule states either.
   - DIM's negative bound is 5. `10 DIM A(3):A(-1)=0` (the model says 9) separates "subscript out of range" from "the
     same integer reader as DIM, so 5".
   - `10 DIM A(3):A(1,1)=0` (the model says 9) is not measured.
5. **Bounds and subscripts are converted by `int()` (truncation).** No rule states it.
   `10 DIM A(2.5):A(3)=1:PRINT "[T]"` gives 9 in the model, and `[T]` if bounds are rounded.
6. **Element sizes {%: 2, $: 3, !: 4, default: 8}.** These are the size law. The rule sentence omits them (only the
   Details state them), and only 2 and 8 are exercised (1.1).
7. **`FRE("")` returns `strsize`, whatever strings are held.** R-CLEAR-SIZE's "FRE of an empty string reads n" is true
   only with an empty string space. `10 CLEAR 500:A$="ABC"+"":PRINT FRE("")`: the model prints 500; MSX should print
   497.
8. **CLEAR empties the GOSUB/FOR stack (`reset()`: `self.stack = []`).** No rule states it; the page lists it as Open.
   The model predicts:
   - `RETURN without GOSUB in 20` for `10 GOSUB 20:END` / `20 CLEAR:RETURN`;
   - `NEXT without FOR in 10` for `10 FOR I=1 TO 2:CLEAR:NEXT`.

   Either measure these or name the law as unmeasured.
9. **CLEAR's argument order contradicts the page.** CLEAR.md says "only `Overflow` while reading an argument, and a
   negative first argument, come first" (before the trailing-junk Syntax error). The model gives 2 for both
   `10 CLEAR -1,2,3` and `10 CLEAR 70000,2,3`; the page predicts 5 and 6. The model also reaches 2 by accident: the
   `value()` fallthrough, not an "end of statement" check. 13 is tested before 5 or 6 on either argument
   (`CLEAR -1,"A"` gives 13 in the model), which is unmeasured.
10. **DIM's check order inside one array.** The redimension check (10) comes before the bound errors, and the bound
    errors come in bound order. No rule states this. `10 DIM A(2):DIM A(-1)` gives 10 in the model; the rival gives 5.

## 3. Weak controls and unseparated rivals

1. **Each rule has one control, and its other clauses have none.**
   - R-DIM-BOUNDS: only "bound 9". There is no control for 0-based subscripts, past-bound = 9, multi-dimensional, or
     truncation.
   - R-DIM-SIZE: only the order. There is none for 5 / 6 / 13.
   - R-CLEAR-RESET: there is no control for "clears the variables" or "goes on".
   - R-CLEAR-ERRORS: 2 controls cover 2 of its 9 clauses.

   With a whole-interpreter `ok`, a clause without a control is pinned only by the data, never by a stated rival.
2. **`dim-memory-first` is the same, on observation, as "there is no 65535-byte limit".** FREE < 65535 on any 32 K
   machine, so a memory-first check can never yield 9. The control shows that a byte limit exists. It does not show
   the "checked before free memory" order, which no case on this machine can separate. Rephrase the clause as "past
   65535 bytes is 9, not 7", or say that the order is not observable here.
3. **Every control is FALSE on exactly 1 case, except the order control (2).** Each rule therefore hangs on a single
   record: FX 2, 15, 21, 24, 27, 28, 32, 39, 41. A second separating case per control would make the result robust to
   one bad capture.
4. **Rivals that agree on every case.** The byte threshold anywhere in [40002, 80008) (1.1); the Overflow edge at
   32768 or at 70000 (1.2, 1.10, 2.1); truncation against flooring (1.5); "makes nothing" against "makes a scalar or
   A(10)" (1.6); FREE anywhere in [500, 29999] (2.2); the name law (2.3).
5. **R-CLEAR-SIZE's clause "and so does moving the top (CLEAR n,top)" is refuted by its own case under the literal
   reading.** "Keeps the last size" would print 200 at KDM FX 33; the reference printed 300, which is `n`. The case
   pins "CLEAR n,top sets the size to n", not "keeps". By the page's own table (`CLEAR ,&HD000` is 2), no form moves
   the top without giving a size, so "keeps" is vacuous. spec-plan.md's unit paragraph repeats "a moved top keeping
   the size".

## 4. Page claims with no case, or contradicted by the record

1. **DIM.md, "the measured set of errors is {2, 5, 6, 9, 10, 13} for one dimension".** This contradicts its own table
   row (7, more than free memory) and KDM FX 9, where `DIM A%(20000)`, a one-dimensional DIM, gives
   `Out of memory in 10`.
2. **CLEAR.md, "{5, 13, 24} for the memory-top form".** This contradicts its own table row `CLEAR 200,&H8050` (7) and
   the trailing-junk row (2).
3. **CLEAR.md's table rows with no KDM case.**
   - `CLEAR 200,"A"`, `CLEAR 200,65535`, `CLEAR 200,&H8050` and `CLEAR ,&HD000`: the last three are in Open.
   - The whole trailing-junk row.

   Of these, the model **contradicts** two:
   - `&H8050` (2.2);
   - the "negative first / Overflow first" order (2.9).
4. **CLEAR.md Details.** "DEF FN definitions with them", "CONT … after a typed CLEAR" (not in KDM; kstop may hold it),
   "NEW and RUN keep whatever size" (RUN in KDM FX 32 re-runs `CLEAR 500` itself, so it shows nothing about RUN) and
   "the old string-space size … stay[s]" after a refused CLEAR: none has a KDM case.
5. **DIM.md Details.**
   - "32 subscripts", "4 per single, 3 per string", `DIM A,B(2)` and "`A` is not created" (1.6) have no KDM case.
   - "unless a `DEFINT`/`DEFSNG`/`DEFSTR` says otherwise" has no case and is not modelled (2.3).
   - The Example uses `B$(2,1)` while Open says string arrays are not measured. That is true of KDM, but the example
     run did measure one.
6. **ERASE.md Details.** "leaves `A%` and `A$` alone", `ERASE A()`, `ERASE 5`, `ERASE A,` and "frees its memory" have
   no case. Only the last is in Open.
7. **The three page headers say "every rule is pinned by a control of its own".** That is true by count. But
   R-CLEAR-ERRORS's 65535 clause is the one sentence the model does not compute (2.1), and the CLEAR n,top clause is
   contradicted by its case (3.5).
8. **spec-plan.md: "Every page claim held".** It held for the claims that were cased. Items 4.1–4.6 are page claims
   with no case, and two of them (4.3) the model would fail.

## 5. Probe-apparatus risks

1. **The memory-limit cases are "far from the edge", and that holds only partly.**
   - `DIM A%(20000)` is far: about 10 KB above any 32 K ceiling and 25 KB below 65535.
   - `CLEAR 30000` is outside free memory **by arithmetic**, since &HF380 − &H8000 = 29568. But it is only 432 bytes
     past that ceiling, and about 2 KB above the size the VG-8020 was measured accepting (28000, CLEAR.md).

   The case is safe. "Far" overstates it, and the docstring's reason ("exceed ANY free memory") rests on the top
   being ≤ &HF380, which the probe does not assert.
2. **The model's FREE (28000) sits inside the reference's unknown region (28000 < ref edge < 30000).** Any future case
   between 28001 and the real edge will be mispredicted, without the reason being visible. zerobas's own edge (27000–27500)
   is below FREE as well.
3. **The check compares the whole screen (`ok`), echo wrapping included.** KDM FX 17, 24 and 25 wrap their echoed line
   at 37 characters (`…ERASE P,` / `Q`). So R-ERASE-REMOVE's and R-DIM-BOUNDS's ✓ also rest on the shared wrap law.
   If zerobas wrapped differently, the difference would be charged to DIM and ERASE, which is the same blind spot as
   gkwnum 2.1.
4. **`normalise` drops blank 40-column rows.** An empty string element (`PRINT A$(1)`) is invisible. Future string-array
   or ERASE-of-`A$` cases must bracket their output (`PRINT "[";A$(1);"]"`), as FX 16 does.
5. **One run file, one boot per case (`batch=False`).** FX 31's "200 at start-up" depends on that: under batching,
   FX 30's `CLEAR 500` would leak. Note that `run_cases` caches references (D-REFCACHE), so a stale reference capture
   would not show. Neither risk is visible in the run file.
6. **The shared interpreter now holds two name laws in the tree.** kdeftype_model has two significant characters and
   suffixed = unsuffixed; kstop_model has full text with the suffix as the key. Any future screen case that mixes
   `A` and `A#`, or long names, in the DIM / ERASE family will read FALSE against the model and not against the
   machine.

**Findings: 41 numbered items** (§1: 12, §2: 10, §3: 5, §4: 8, §5: 6). Some overlap: 1.10 with 2.1, 1.1 with 2.6,
and 4.3 with 2.2 and 2.9.
