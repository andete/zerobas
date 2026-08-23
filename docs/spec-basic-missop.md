<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-MISSOP — the silent `POKE addr,` write is ONE RULE at SIXTEEN slots

Status: **✅ SWEPT. The filed one-verb defect is a language-wide rule, and the
sweep also produced the DESIGN.** 2026-08-23, on `051630f`. **Measurement only —
no source file changed, no ROM byte moved** (`7942cc20` / `34bb8554` /
`031184d9` throughout). The fix is priced in §6 and **blocked on page-1 bytes**,
not on knowledge.

`TODO.md` filed this on 2026-08-22 with an instruction rather than a price:
*"likely one rule at several verbs — **sweep the verbs that take a trailing
value before pricing**."* This is that sweep.

---

## 1. The root, read from the source before any machine was booted

`basic/expr.asm`'s `ev_f` (the factor decoder) explicitly catches an empty
operand at **`)`** and at **`,`**, deferring FPERR=4 → ERR 2 *Syntax error*
(`ev_f_empty`, D-F2-3). It does **not** catch **end of statement**. A `$00` or
`:` falls past every `cp`, reaches `ev_f_var`, fails `is_letter`, and lands on
the shared tail:

    ev_f_err:
                ld      a,$DD               ; expression error marker
                ld      (ERRMARK),a
                ld      de,0
                ret

That sets the `ERRMARK` landmark and returns **a value of zero with no
`penderr_set` call at all**. So `do_poke`'s own `ld a,(FPERR) / or a` sees a
clean machine, and the store proceeds with `E` = 0.

🎯 **THE MECHANISM IS NOT MISSING FROM THE TREE — THE END-OF-STATEMENT CASE IS
MISSING FROM `ev_f`.** `basic/time.asm:62` raises ERR 24 by hand for `TIME=`,
and four other verbs do the same thing at their own parse. That is why the fix
is small and why five rows below are already green.

---

## 2. The denominator, and what kind of claim it is

📏 **MECHANICAL SEED: 66 evaluator call sites reachable from statement parsing**
— 49 bare `call eval`, 7 `eval_addr`, 5 `eval_byte_checked`, 3 `eval_pos_arg`,
2 `eval_chan` — across **19 files**. Not all are reachable-empty; many sit
behind a delimiter check of their own.

⚠️ **THE ROWS BELOW ARE A HAND-LISTED BASIC-SURFACE SAMPLE OF THAT SET, WHICH IS
A SCOPE CLAIM AND NOT A COVERAGE ONE** ([[a-hand-listed-denominator-is-a-scope-claim]]).
"16 slots" is a floor on the class, not its size.

---

## 3. The instrument

`scratchpad/missop_probe.py` — D-TRAPSVC's shape: whole programs,
**boot-per-case**, on **both references and zerobas**, one fenced value per row,
a non-numeric fence rejected as the source echo ([[trapsvc-echo-fence]]).

Readout is `[ERR R]`:

* **`ERR`** is `0` when the statement **completed** and the MSX error code when
  it **aborted** — so *"did it abort, and with what?"* needs no guessing at
  message wording, and no `Missing operand` string has to be matched.
* **`R`** is a read-back where the statement has an observable side effect, so a
  row can say the machine not only failed to abort but **WROTE**. Rows with
  nothing to read print `0` there.

⚠️ `R` is read **before** the exit line's `SCREEN0:CLS`, because `CLS` clears
VRAM and the `VPOKE` row reads it back; and `SCREEN0` precedes the print on both
exits because the graphics rows leave the machine in SCREEN 2, where a SCREEN-0
scrape reads a zeroed pattern table as 960 blanks.

---

## 4. The measurement — 26 rows × 3 machines, `scratchpad/missop_probe.out`

`[ERR R]`. **The two references agree with each other on all 26 rows**, so every
row is a want or a green.

| row | statement | VG-8020 | CF-3300 | zerobas | |
|---|---|---|---|---|---|
| `poke.ok` | `POKE&HE000,65` | `0 65` | `0 65` | `0 65` | control |
| `poke.addr` | `POKE,1` | `2 0` | `2 0` | `2 0` | control |
| `poke.paren` | `POKE&HE000,)` | `2 99` | `2 99` | `2 99` | control |
| `locate.addr` | `LOCATE,1` | `0 0` | `0 0` | `0 0` | optional slot |
| `color.val` | `COLOR15,` | `0 0` | `0 0` | `0 0` | optional slot |
| `time.val` | `TIME=` | `24 0` | `24 0` | `24 0` | already right |
| `locate.val` | `LOCATE1,` | `24 0` | `24 0` | `24 0` | already right |
| `screen.val` | `SCREEN0,` | `24 0` | `24 0` | `24 0` | already right |
| `base.val` | `BASE(0)=` | `24 0` | `24 0` | `24 0` | already right |
| `line.val` | `LINE(0,0)-(10,10),` | `24 0` | `24 0` | `24 0` | already right |
| **`poke.val`** | `POKE&HE000,` | `24 99` | `24 99` | **`0 0`** | 🔴 **WROTE** |
| **`poke.plus`** | `POKE&HE000,+` | `24 99` | `24 99` | **`0 0`** | 🔴 **WROTE** |
| **`poke.colon`** | `POKE&HE000,:X=1` | `24 99` | `24 99` | **`0 0`** | 🔴 **WROTE** |
| **`vpoke.val`** | `VPOKE0,` | `24 99` | `24 99` | **`0 0`** | 🔴 **WROTE** |
| `out.val` | `OUT&H98,` | `24 0` | `24 0` | **`0 0`** | 🔴 |
| `sound.val` | `SOUND0,` | `24 0` | `24 0` | **`0 0`** | 🔴 |
| `let.val` | `A=` | `24 0` | `24 0` | **`0 0`** | 🔴 |
| `let.plus` | `A=+` | `24 0` | `24 0` | **`0 0`** | 🔴 |
| `defusr.val` | `DEFUSR=` | `24 0` | `24 0` | **`0 0`** | 🔴 |
| `pset.val` | `PSET(10,10),` | `24 0` | `24 0` | **`0 0`** | 🔴 |
| `circle.val` | `CIRCLE(50,50),20,` | `24 0` | `24 0` | **`0 0`** | 🔴 |
| `sprite.val` | `PUTSPRITE0,(10,10),` | `24 0` | `24 0` | **`0 0`** | 🔴 |
| `print.val` | `PRINT1+` | `24 0` | `24 0` | **`0 0`** | 🔴 |
| `key.val` | `KEY1,` | `24 0` | `24 0` | **`2 0`** | 🔴 wrong code |
| `lets.val` | `A$=` | `24 0` | `24 0` | **`2 0`** | 🔴 wrong code |
| `midd.val` | `MID$(A$,2)=` | `24 0` | `24 0` | **`2 0`** | 🔴 wrong code |

**16 DIFF, 10 agree, 0 NOT MEASURED.**

### 4.1 Two sub-classes, and they are not equally bad

* **13 rows SILENTLY COMPLETE** (`ERR` = 0). **Four of them WRITE**: `POKE`
  three ways and `VPOKE` once, each turning a byte that held `99` into `0`. A
  program with a typo in a `POKE` gets no error and a corrupted byte.
* **3 rows abort with the WRONG CODE** (ERR 2 instead of 24). All three are the
  **string**-operand paths (`KEY`'s string, `A$=`, `MID$()=`), which reach an
  abort by a different route.

### 4.2 A within-family separator nobody planted

`line.val` is **green** while `pset.val` and `circle.val` are red — same file,
same colour argument, same statement family. `basic/graphics.asm:215` has LINE's
own hand-written *"end of line -> Missing operand"*; PSET and CIRCLE do not.
🎯 **The five green rows are not evidence that the class is small — they are
five verbs that each paid for the check separately**, which is exactly the shape
a missing shared rule leaves behind.

---

## 5. 🎯 THE RULE, AND THE SWEEP PRODUCED THE DESIGN

Measured, not assumed:

> **A required argument slot that ends where a value was needed is `Missing
> operand` (ERR 24). An empty operand terminated by `)` or `,` is `Syntax
> error` (ERR 2). An OPTIONAL slot may simply be omitted and the statement
> completes.**

Three rows separate those three cases, and all three are unanimous across the
references: `poke.val` / `poke.plus` (→ 24), `poke.paren` / `poke.addr` (→ 2),
`color.val` / `locate.addr` (→ complete).

🎯 **AND THAT PARTITION IS ALREADY THE PARTITION `ev_f` HAS.** Two sites, and
they divide the space on exactly the reference's line:

> ⚠️ **AND THAT SENTENCE IS TRUE OF `ev_f`'s *decision*, NOT OF ITS *code
> layout* — which is the trap this slice fell into.** `ev_f_empty` really is
> reached only at `)` and `,`. But `ev_f_err` is **not** reached only when a
> factor was required: it is the shared tail for **eight** different jump sites,
> seven of which are other malformed-expression cases. Siting the fix on the
> label rather than on the decision cost a shipped regression. See §13.

| `ev_f` site | reached at | today | reference | |
|---|---|---|---|---|
| `ev_f_empty` | `)` and `,` | FPERR=4 → **ERR 2** | ERR 2 | ✅ already exact |
| `ev_f_err` | everything else that cannot start a factor — end of line, `:`, `+` | **silent, DE=0** | ERR 24 | 🔴 the hole |

**So the fix is one deferred code**, and `poke.plus` is the
row that says so: had `POKE a,+` been *Syntax error* on the references, a single
code at `ev_f_err` would have been wrong and the fix would have needed its own
end-of-statement test. It is `24`. Optional slots are decided by each verb
*before* `eval` and are untouched either way.

⚠️ **THIS WAS WORTH FOUR EXTRA ROWS AND IT CHANGED THE DESIGN.** The 22-row
matrix already proved the class; `poke.plus` / `poke.paren` / `poke.colon` /
`let.plus` were added afterwards for no other purpose than to decide **where**
the fix goes, and they moved it from a new test inside `ev_f` to five bytes at a
tail that already exists.

---

## 6. 💰 Price — and it is blocked on bytes, not on knowledge

> ⚠️ **SUPERSEDED BY §10.** This section is the estimate as it stood before the
> fix was built, kept because §10's "the estimate was exact" is only meaningful
> beside the estimate that was made. **What actually shipped is 5 B at its own
> label, not 6 B at the shared tail — §13 is why.**

    ev_f_err:   ld  a,<new code>      ; +2 B   basic/expr.asm   (PAGE 1)
                call penderr_set      ; +3 B
    fperr_to_err: db 24               ; +1 B   basic/interp.asm (PAGE 1)

⚠️ **~6 B is an ESTIMATE AND THEREFORE A LOWER BOUND** — this tree's own
repeated lesson is that a size from arithmetic is not a measurement. Both files
are **page 1**, which **was 2 B free on 2026-08-23** at `051630f`
(`make basic-reloc`, this session).

**Funding routes, neither costed here:**

1. A **6 B page-1 carve**.
2. **PROMOTE `ev_f_err` into the low region** (which was 17 B free on
   2026-08-23). ⚠️ `ev_f_defer` falls
   **through** into `ev_f_err`, so promotion costs a `jp` back and the net gain
   must be MEASURED, not arithmetic'd.

### 6.1 What a knife must attack, stated before anyone writes the fix

* `ev_f_err` is the shared tail for **every** byte that cannot start a factor,
  and `basic/missing.asm`'s `ex_let_str` deliberately **clears `ERRMARK`** and
  uses the landmark as its discriminator (*"did the RHS parse as anything
  well-formed"*). Its own header records that *"did eval consume any bytes"* was
  tried first and measured wrong. A deferred FPERR changes which error wins
  there — and for `A$=` / `A$=+` the references say the new answer (24) is the
  **right** one, so this is a row to re-measure, not a reason to stop.
* `basic/str-engine.asm` has backtracking `jp ev_f_err` sites (`:544`, `:579`)
  whose comments already note that the bare form *"set only ERRMARK"*. A string
  path that falls through `ev_f_err` **benignly** would be poisoned by a
  deferred error. **This is the one that can sink the design**, and it is
  measurable: `str-*` rows across the existing string suites.
* `penderr_set`'s first-error-wins already protects the case where the operand
  raised its own error first.
* The three ERR-2 string rows (`key.val`, `lets.val`, `midd.val`) may or may not
  move to 24 under this fix — they abort by another route. **Predict each before
  running it.**

---

## 7. 🔴 What the sweep refuted in its own filing

`TODO.md` justified *"likely one rule at several verbs"* with:

> *(`LOCATE ,` correctly gives ERR 24, so the mechanism exists)*

**Measured: `LOCATE,1` reads `0` on all three machines — it COMPLETES.** An
omitted `LOCATE` row is an *optional slot*, not a caught error, so the row cited
as evidence measures a different fact entirely. The **conclusion** was right —
the mechanism does exist, at `TIME=`, `LOCATE1,`, `SCREEN0,`, `BASE(0)=` and
`LINE(...)-(...)`, all measured green here — but **the row named for it was the
wrong row**, and `LOCATE1,` (the trailing slot) is the one that shows it.

🎯 A justification parenthesis is a claim, and this one had never been run.
Same family as [[a-case-that-agrees-can-agree-for-the-wrong-reason]] — except
here the cited row was not even green for the wrong reason, it was green for a
*different question*.

---

## 8. ⚠️ What this does NOT establish

* **The 16 is a floor.** §2's denominator is 66 evaluator call sites; 26 BASIC
  rows sample it. Verbs not run here (`SWAP`, `ON n GOTO`, `FIELD`, `PRINT#`,
  `INPUT`, `PLAY`, `DRAW`, `OPEN`, `WIDTH`, the `PRINT USING` family) are
  **unmeasured**, not green.
* **No fix was written and nothing was knifed**, so §5's design is a *prediction*
  about where the bytes go, supported by a source read and by `poke.plus` — not
  by a build.
* `OUT&H98,` writes one byte to the VDP data port on the failing machines. It is
  harmless here (the exit line does `SCREEN0:CLS`) but it is a side effect the
  row does not read back, so `out.val`'s `R` column is `0` by construction, not
  by measurement.

---

## 9. What was run

`scratchpad/missop_probe.py` (26 rows × 3 machines, boot-per-case, 78 runs) →
`scratchpad/missop_probe.out`; the four design discriminators first run alone →
`scratchpad/missop_disc.out`; `scratchpad/missop_blast.py` (11 rows × 3) against
both the wide and the narrowed build → `scratchpad/missop_blast_wide.out` and
`scratchpad/missop_blast.out`; the narrowed build's verb matrix →
`scratchpad/missop_after2_zb.out`. Predictions were written before each round:
`scratchpad/missop_fix_predictions.md`. Knives: `scratchpad/missop_knives.py` →
`scratchpad/missop_knives.out`. Gates in §15.

## 10. ✅ AS BUILT — 5 B at its own label, funded by a 7 B promotion

Landed 2026-08-23 on `4dd24f6`. **`sub.rom` does not move**, which is the right
signature for a `basic/*.asm` edit.

    ev_f_missop:                             ; basic/expr.asm, beside ev_f_tmm/ev_f_ifc
                ld      e,FPERR_MISSOP       ; +2 B
                jr      ev_f_defer           ; +2 B
    expr.asm:556  jr nc,ev_f_err -> jr nc,ev_f_missop      0 B (same instruction)

    fperr_to_err:  db 24                     ; +1 B  basic/interp.asm
    FPERR_MISSOP   equ 12 / 11               ;  0 B  basic/sysvars.inc

**Cost: 5 B.** ⚠️ **THE FIRST DRAFT WAS 6 B AND SAT ON THE SHARED `ev_f_err`
TAIL. IT WAS WRONG, A SHIPPED GATE SAID SO, AND §13 IS THAT STORY** — the
correction is both narrower *and* a byte cheaper.

`FPERR_MISSOP` is equated **inside the same `IF CLEARPOOL`** as `FPERR_STROOM`
(12 with, 11 without) because `fperr_to_err` is a **dense** table whose next free
index moves with that switch. Getting it wrong is silent: it would read a
neighbouring byte and report some other error.

### 10.1 The funding: a PROMOTION, not a carve

`basic/title.asm` moved from page 1 into the low region — a **7 B** stub
(`ld ix,<tenant slot>` + `jp subrom_call`) whose only callee, `subrom_call`, is
**already low-region**, and whose only caller is `init`, once, before the REPL.
`basic/main.asm`'s own header already argues the direction is the safe one:
*promoting DOWN cannot break reachability, because low-region code is visible
whenever page 0 is mapped.*

**Walls (`make basic-reloc`, 2026-08-23): page-1 free 4 B (was 2), low-region
free 10 B (was 17).** Net **+2 B** on the hard wall — the slice pays for itself
and leaves the page-1 ceiling looser than it found it.

### 10.2 How the cost was measured before it fit

`make basic-reloc` fails hard on overrun (it references an undefined symbol
whose NAME is the diagnostic), so the 6 B draft could not be weighed by
building it. A **scaffolded build** with the ceiling temporarily raised to
`$8200` read `__MEAS_PAGE1_END = $8004` against a clean `$7FFE` — **6 B added,
4 B over**. ⚠️ That build was a different machine and was used for a SIZE
READING ONLY ([[a-scaffolded-build-is-a-different-machine]]); the ceiling was
restored immediately.

## 11. ✅ AS MEASURED — 16 DIFF → 3, and one prediction MISSED

⚠️ The table below was taken on the 6 B draft and **re-taken byte-for-byte on
the narrowed 5 B build** (`scratchpad/missop_after2_zb.out`): all 26 verb-matrix
readings are identical on both, which is the point of §13.2's claim that the
narrowing changes only the seven sites that were never this slice's subject.

Row predictions were written before the edit
(`scratchpad/missop_fix_predictions.md`): **14 of 16 close, `key.val` and
`midd.val` stay**. Measured: **13 close**, and the extra miss is a finding.

| | predicted | measured | |
|---|---|---|---|
| 12 rows → `24` (`poke.val` `poke.plus` `poke.colon` `vpoke.val` `out.val` `sound.val` `let.val` `let.plus` `defusr.val` `pset.val` `sprite.val` `print.val`) | close | close | ✅ |
| `lets.val` (`A$=`, `2` → `24`) — flagged "less certain" | close | close | ✅ |
| `key.val`, `midd.val` (stay `2`) | stay | stay | ✅ |
| **`circle.val`** | close | **still `0 0`** | 🔴 **MISS** |

**Cost prediction (6 B, 4 B over the ceiling): EXACT.**
**Row-set prediction: 15 of 16 right, one miss.**

The four POKE/VPOKE rows now keep their byte at **`99`** where they used to
report `0`: the silent write is gone, on every one of its three shapes.

### 11.1 🔴 The miss is a SECOND MECHANISM, at a second site, in another ROM

`CIRCLE(50,50),20,` still completes silently — and it can never have been fixed
here, because **`eval` is never called on that operand**. CIRCLE's grammar walk
lives in a sub-ROM page-1 tenant (`sub/circleparse.asm`), and `cpt_at_c` decides
for itself that the colour is absent:

    cpt_at_c:
                call    cpt_skipsp
                cp      ','
                jp      z,cpt_start_intro   ; c omitted; this comma also intros start
                or      a
                jp      z,cpt_finish        ; <-- end of line after the comma: DRAW
                cp      COLON
                jp      z,cpt_finish        ; <-- ':' after the comma: DRAW

🎯 **SO THE CLASS HAS THREE MECHANISMS, NOT ONE, AND ONLY THE SWEEP'S ROW SET
COULD HAVE SHOWN THAT:**

1. **`ev_f_err`** — the operand reaches the evaluator and it yields a silent 0.
   **13 rows. Closed by this slice.**
2. **A verb's own grammar swallows the dangling comma before `eval` is ever
   reached.** `circle.val`. **Open** — and it is *not* byte-blocked: it lives in
   sub page 1, which had **1624 B free on 2026-08-23**. It is a scope decision.
3. **The operand aborts by another route with the wrong code** (ERR 2, not 24).
   `key.val`, `midd.val` — the string paths. **Open.**

⚠️ And `cpt_at_start` / `cpt_after_aspect` have the **same shape** as `cpt_at_c`,
so CIRCLE likely has three more slots with the same hole
(`CIRCLE(50,50),20,5,`). **Unmeasured** — the filing carries the recipe.

### 11.2 What did not move, and why that matters

`poke.paren` (`POKE&HE000,)`) and `poke.addr` (`POKE,1`) still read **`2`**.
They read `2` because they reach **`ev_f_empty`**, a different label, and the
narrowed fix never touches it. ⚠️ **THAT IS A STRUCTURAL ARGUMENT NOW, AND IT
USED TO BE A FIRST-ERROR-WINS ONE** — the 6 B draft sat on a tail `ev_f_empty`
falls through, so those two rows staying at `2` depended on `penderr_set` being
set-if-empty. The narrowing removes that dependency entirely: `ev_f_missop`
jumps *over* `ev_f_empty` to `ev_f_defer`, so the two codes never meet.
**A design change can retire a subtlety rather than pin it**, and this one did.
`color.val` and `locate.addr` (optional slots) still complete.

---

## 12. 🔬 Knives — 3 of 3 EXACT, and one of them re-creates the bug

`scratchpad/missop_knives.py`. Each knife is size-neutral, is preceded by
`rm -rf build`, restores by WRITING THE BYTES, and asserts that
`basic-reloc.rom` + the merged image moved and **`sub.rom` did not**. All three
score the **union of both probes — 37 rows** (26 verb matrix + 11 blast
radius), because a knife that only sees the rows the fix was aimed at cannot say
anything about the rows it was aimed *past*.

    baseline roms=abfefa7f / 34bb8554 / a8173c25
    K-MO1    roms=ca376dd5 / 34bb8554 / 0c6058af
    K-MO2    roms=393afaa6 / 34bb8554 / ae621e6a
    K-MO3    roms=a56f33c6 / 34bb8554 / 0c75ae80
    restored roms=abfefa7f / 34bb8554 / a8173c25
    3/3 knife rows EXACT

| knife | the cut | moved | |
|---|---|---|---|
| **K-MO1** | `ld e,FPERR_MISSOP` → `ld e,0` (`penderr_set` with A=0 is a no-op) | the **13** closed rows, back to their pre-fix faces | EXACT |
| **K-MO2** | `db 24` → `db 5` in `fperr_to_err` | the same **13**, now answering `5` | EXACT |
| **K-MO3** | site `:807` `jp nz,ev_f_err` → `jp nz,ev_f_missop` | **`b.paren` alone**, `0` → `24` | EXACT |

### 12.1 What each one actually established

* **K-MO1 is what makes "pre-existing" a READING.** §14.2 claims `b.paren`
  (`A=(1+2`) and `b.vpnoclose` (`A=VARPTR(B`) diverge for reasons that have
  nothing to do with this slice. Under a knife that neutralises the deferred
  code entirely, **neither moved.** They are independent of the fix, measured,
  not argued.
* **K-MO2 pins the DENSE-TABLE INDEX**, which is the hazard `sysvars.inc`'s new
  comment warns about: `FPERR_MISSOP` is 12 with `CLEARPOOL` and 11 without, and
  an off-by-one would silently read a neighbouring byte and report some *other*
  error. The 13 rows answering exactly `5` say the entry being read is the one
  this slice added.
  🎯 **AND IT SHOWED SOMETHING NOBODY ASKED IT:** under K-MO2 the POKE rows read
  `5 99` — **wrong code, byte still intact.** It is the *abort* that protects
  memory, not the particular code. The silent write and the wrong wording are
  two independent properties, and only a knife that scores the read-back column
  can separate them.
* **K-MO3 IS THE REGRESSION, RE-CREATED ON PURPOSE.** Pointing one of the seven
  other jump sites at the new label reproduces exactly what
  `make lineerr-acceptance` caught — and moves **nothing else**, in 37 rows.
  That is the narrowness claim, measured: the fix reaches the site it is
  supposed to reach and no other.

⚠️ **NOT CLAIMED:** three knives is a candidate roster. Unknifed: the
`FPERR_MISSOP` equ's `CLEARPOOL=0` arm (§15 — it cannot be built by any gate in
this tree), the `title.asm` promotion (no gate reads the boot banner), and
the interaction between `ev_f_missop` and a code already deferred by an inner
expression — `penderr_set`'s first-error-wins covers it by construction, and
`poke.paren` is a row that would notice, but no knife aims at it.

## 13. 🔴 THE FIX SHIPPED TOO WIDE, AND A GATE NOBODY WROTE FOR IT SAID SO

The first draft put the deferred code **on `ev_f_err` itself**. That looked
contained: `sub/` never names it, and `basic/str-engine.asm`'s five mentions
read like live call sites.

**They are not.** Every one of them is a HISTORICAL COMMENT about code converted
away in earlier slices — *"the old bare `jp ev_f_err`"*, *"was a bare ev_f_err
-> silent 0"*. Grepping for actual `jp`/`jr` **instructions** finds the real
set, and it is **eight sites, all inside `expr.asm`, of which exactly ONE is the
missing operand**:

| site | what reaches it | correct error |
|---|---|---|
| `:556` | `ev_f_var`'s `is_letter` fails — end of line, `:`, a stray operator | **24** ← the subject |
| `:807` | a parenthesised expression closed by something other than `)` | **2** |
| `:1095` / `:1116` | `EOF(n)` / `LOF(n)` on a device or cassette channel | — |
| `:1880` / `:1884` | `VARPTR` with no `(`, or of a non-variable | — |
| `:2026` / `:2031` | `BASE` with no `(`, or with no closing `)` | — |

🎯 **`make lineerr-acceptance` FOUND IT — 209 of 210:**

    DIFF a.noclose   vg8020=' 2 , 7 , 4 '  cf3300=' 2 , 7 , 4 '  zb=' 24 , 7 , 4 '

`a.noclose` is `LINE (11,12-(20,21)`: the inner `(20,21)` is a parenthesised
expression closed by a `,`, i.e. site `:807`, and **both references call that
Syntax error**.

### 13.1 The instrument this slice built could not have found it

`missop_probe.py`'s denominator is **BASIC verbs with a trailing value**. The
defect is in the **expression grammar**, at a slot no verb row visits.
`lineerr-acceptance`'s `a.*` class sweeps *"every slot that can END where a
value was required"* structurally through `LINE`'s own grammar — **a different
axis**, written for a different slice, years of commits earlier.

⚠️ **THE PURPOSE-BUILT PROBE HAD A HOLE THE STANDING GATE DID NOT.** The lesson
is not "run the gates" (that was never in doubt) — it is that a new instrument's
denominator is shaped by the hypothesis that motivated it, and a shared tail's
blast radius is exactly the thing that hypothesis does not describe.
**Grep the MECHANISM, not the symbol**: five mentions of `ev_f_err` in
`str-engine.asm` said "wide and risky", and all five were about code that no
longer exists; eight `jp`/`jr` instructions in one file said "wide in a
DIFFERENT direction", and that was the true shape.

### 13.2 The narrowing, and it is CHEAPER

    ev_f_missop:  ld   e,FPERR_MISSOP     ; +2 B   the same idiom ev_f_tmm /
                  jr   ev_f_defer         ; +2 B   ev_f_ifc / ev_f_empty use
    expr.asm:556  jr nc,ev_f_err  ->  jr nc,ev_f_missop      0 B (same instruction)
    ev_f_err                             reverted             -5 B

**Slice cost 4 B + 1 table byte = 5 B**, one byte less than the wide version.
`ev_f_err` goes back to being the silent landmark it is for its other seven
sites, and the deferred code is reached from the one site that means *a factor
was required and what is here cannot start one*.

---


## 14. The blast radius, measured — `scratchpad/missop_blast.py`

11 rows × 3 machines, run against the **wide** build
(`scratchpad/missop_blast_wide.out`) and again against the **narrowed** one
(`scratchpad/missop_blast.out`).

| row | statement | refs | wide | narrowed | |
|---|---|---|---|---|---|
| `b.paren` | `A=(1+2` | `2` | **`24`** | `0` | 🔴 broken by the draft; **pre-existing** underneath |
| `b.vpnopar` | `A=VARPTR 5` | `2` | **`24`** | `2` ✅ | broken by the draft, restored |
| `b.vpbadarg` | `A=VARPTR(5)` | `2` | **`24`** | `2` ✅ | broken by the draft, restored |
| `b.vpnoclose` | `A=VARPTR(B` | `2` | `5` | `5` | 🔴 **pre-existing**, newly found |
| `b.basenopar` | `A=BASE 5` | `2` | `2` | `2` ✅ | site never reached |
| `b.basenoclose` | `A=BASE(0` | `2` | `2` | `2` ✅ | site never reached |
| `b.eofdev` / `b.lofdev` | `A=EOF(0)` / `A=LOF(0)` | `59` | `59` | `59` ✅ | |
| `b.parenok` / `b.vpok` / `b.baseok` | well formed | `0`/`5`/`0` | same | same ✅ | controls |

**Wide: 4 DIFF. Narrowed: 2 DIFF, and both are pre-existing.**

### 14.1 🔴 Predictions scored — 4 exact of 10, and the misses are the lesson

I read the eight jump sites out of the source and predicted all seven
non-subject rows would read `24` under the wide fix. **Only three did.**

* `b.basenopar` / `b.basenoclose` never reach `ev_f_err` at all — `BASE` is
  descoped and carries its **own inline** `ERRMARK` body, so the
  `jp nz,ev_f_err` I read at `:2026`/`:2031` is not on the path those statements
  take.
* `b.vpnoclose` answers `5`, not `24` — `VARPTR`'s own domain check gets there
  first.
* `b.eofdev` / `b.lofdev` answer `59` on all three, agreeing; the source comment
  claiming `PRINT EOF(0)` *"printed a plausible ` 0` with no error at all"* is
  **stale** — some later slice fixed it and the comment was not updated.
* `b.vpok` (`A=VARPTR(B)`, my *control*) is ERR 5 on **all three machines**, not
  the `0` I predicted. It is still a control, but only because the references
  agreed with each other.

🎯 **READING JUMP SITES TELLS YOU WHERE CODE GOES, NOT WHICH ROWS REACH IT.**
Every miss is one error wearing different clothes: a **static reachability claim
used as a dynamic one**. The three predictions that were right were right for
the same reason the four were wrong — nothing had been measured either way.

### 14.2 Two divergences this probe FOUND rather than caused

Both survive the narrowing and neither is this slice's doing:

* **`A=(1+2` completes silently on zerobas** (`0`) where both references say
  Syntax error. Same site as `lineerr-acceptance`'s `a.noclose` (`:807`) but a
  *different construct*, and here it is **silent** rather than wrongly-coded.
* **`A=VARPTR(B` answers ERR 5** where both references say ERR 2.

⚠️ **"Pre-existing" is an argument until a knife makes it a reading.** K-MO1
neutralises the deferred code, so if these two rows do not move under it they
are independent of this slice — §12 reports what the knives actually said.

---

## 15. Gates — 34 of 34 green, on the shipping tree

`scratchpad/missop_final.out`, from a clean build, ROMs `abfefa7f` /
`34bb8554` / `a8173c25` throughout (**`sub.rom` unmoved**):

`basic-reloc`, `unit-test`, `deadcode`, `wall-assertion-check`,
`redundant-load-check`, `rowshape-check`, `injector-check`, `preflight-check`,
`latch-check`, `diskdep-check`, `switch-build-check`, `kwsweep`,
`deffn-selftest`, `string-acceptance`, `str-domain-acceptance`,
`strparen-acceptance`, `penderr-acceptance`, `missing-acceptance`,
`error-acceptance`, `error-trap-acceptance`, `onerr0-acceptance`,
`math-acceptance`, `float-acceptance`, `intarg-acceptance`,
`logicops-acceptance`, **`lineerr-acceptance` 210/210**, `screenerr-acceptance`,
`tmfp-acceptance`, `stmtpend-acceptance`, `array-acceptance`, `deffn-strict`,
`graphics-acceptance`, `abort-acceptance`, `interval-trap-acceptance`.

⚠️ **`CLEARPOOL=0` IS NOT AMONG THEM AND CANNOT BE.** `FPERR_MISSOP` is equated
inside the `IF CLEARPOOL` because `fperr_to_err` is a **dense** table whose next
free index moves with the switch — 12 with, 11 without — and an off-by-one is
**silent**: it reads a neighbouring byte and reports some other error. The
`ELSE` arm has never been assembled. `tools/check_switch_builds.py` cannot cover
it: its scope claim is *"no switch is read outside `basic/`"*, and CLEARPOOL is
read from `sub/arrays.asm` and `sub/strheap.asm`, so adding it trips the tool's
own `scope_holds()`. Filed.

### 15.1 ✅ The boot banner, checked by hand because no gate reads it

The 5 B was funded by promoting `basic/title.asm` out of page 1. **Every probe
program in this tree opens with `CLS`**, which wipes the startup header — so not
one of the 34 gates above would notice if `show_title` stopped printing.
`scratchpad/missop_circle.py`'s `banner` row runs a program with no `CLS` and
asserts the header text is on screen: **PRESENT.** ⚠️ It is a one-off, not a
gate. Filed.

---

## 16. 🔴 CIRCLE has FOUR of these slots, not one — measured

`scratchpad/missop_circle.out`, 5 rows × 3 machines. `circle.val`'s survival
(§11.1) was not a one-slot exception:

| row | statement | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `c.colour` | `CIRCLE(50,50),20,` | `24` | `24` | **`0`** 🔴 |
| `c.start` | `CIRCLE(50,50),20,5,` | `24` | `24` | **`0`** 🔴 |
| `c.end` | `CIRCLE(50,50),20,5,0.1,` | `24` | `24` | **`0`** 🔴 |
| `c.aspect` | `CIRCLE(50,50),20,5,0.1,0.2,` | `24` | `24` | **`0`** 🔴 |
| `c.ok` | every slot present | `0` | `0` | `0` ✅ |

**Every optional slot in CIRCLE's grammar accepts a dangling comma and draws.**
`sub/circleparse.asm`'s `cpt_at_c`, `cpt_at_start` and `cpt_after_aspect` all
carry the same `or a / jp z,cpt_finish` + `cp COLON / jp z,cpt_finish` pair, and
the measurement says all three are wrong the same way — the prediction that they
*"have the same shape"* (§11.1) held at 3 of 3.

⚠️ **NOT byte-blocked**: this is sub page 1, which was **1624 B free on
2026-08-23**. It is a scope decision, not a wall — and it wants its own slice
with its own knives, because a fix there must not break the *legitimate* omitted
slot (`CIRCLE(50,50),20` with no trailing comma at all, which `c.ok`'s family
does not yet cover).
