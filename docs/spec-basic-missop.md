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

| `ev_f` site | reached at | today | reference | |
|---|---|---|---|---|
| `ev_f_empty` | `)` and `,` | FPERR=4 → **ERR 2** | ERR 2 | ✅ already exact |
| `ev_f_err` | everything else that cannot start a factor — end of line, `:`, `+` | **silent, DE=0** | ERR 24 | 🔴 the hole |

**So the fix is one deferred code at one shared tail**, and `poke.plus` is the
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
`scratchpad/missop_probe.out`; the four design discriminators were first run
alone → `scratchpad/missop_disc.out`. ROMs `7942cc20` / `34bb8554` / `031184d9`
throughout; no source file changed.
