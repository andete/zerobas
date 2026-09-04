<!-- Copyright (c) 2026 Joost Yervante Damad — SPDX-License-Identifier: 0BSD -->

# The `load error` family, and the face D-FNEXPR declined to guess

**D-FNEXPR2, 2026-08-21**, on `main`, based on `cffb34d` (D-FNEXPR). Closes the
half of the filename-argument residual that D-FNEXPR left open: `SAVE` / `BSAVE`
/ `LOAD` / `BLOAD` / `FILES` take a string EXPRESSION, and a **non-string**
filename raises `Type mismatch` at every verb instead of three different things.

⚠️ **ONE REFERENCE.** Every row is Disk BASIC; a diskless Philips VG-8020 reads
`<NO DISK ON THIS SIDE>` and cannot express the question. Everything rests on
the National CF-3300. The two `t.*` token rows are the exception — they have
both references and agree byte for byte.

---

## 1. Two filed claims, both refuted before a line of ROM changed

### 1.1 🔴 Two of the eight "open" rows had been green for a day

`TODO.md` and [`docs/fnarg2-msx1-characterization.md`](fnarg2-msx1-characterization.md)
§4.2 both described the remainder as the **`load error` family**: a face that is
PRINTED and returns rather than raised. Re-reading the eight deferred rows at
`cffb34d`, before any edit:

| row | cf3300 | zb at `cffb34d` | the filing said zb |
|---|---|---|---|
| `f.loadlit` | `File not found` | **`File not found`** ✅ | `load error` |
| `f.bloadlit` | `File not found` | **`File not found`** ✅ | `load error` |

**D-LOADERR-FIX (2026-08-20) and D-BLNF (2026-08-21) had already retired the
printed face at `LOAD` and `BLOAD`**, as a side effect of other slices, and
nobody re-read the deferred table. 🎯 **So the residual's own name was wrong.**
What actually remained was four rows — `f.savevar`, `f.loadvar`, `f.bloadvar`,
`f.filesvar` — and every one of them is the **argument shape**, i.e. D-FNEXPR's
rule at four more verbs. The "different mechanism, not leftover scope" framing
described a state of the tree that had stopped being true.

This is the gap sweep's own lesson one week later: *re-verify an item before
ranking it*. A deferred row is a denominator only while somebody re-reads it.

### 1.2 🔴 `RUN`'s "genuine ambiguity" is refuted by the stored bytes

D-FNEXPR §2 and `TODO.md` both name `RUN`'s bare-`RUN` fallthrough
([`basic/cload.asm:185`](../basic/cload.asm:185)) as *"genuinely ambiguous with
`RUN <lineno>`"* and price it as a probable **decline**. That is a claim about
the token stream, and this probe has an instrument for those — the `t.*` rows,
which read the STORED LINE BYTES rather than the screen:

| row | line | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `t.runnum` | `1 RUN 30` | `8a 20 0e 1e 00 00` | same | same |
| `t.runvar` | `1 RUN A$` | `8a 20 41 24 00` | same | same |

`$0E` is `LINENO_TOKEN`. **The tokeniser has already separated the two forms, on
all three machines**, so a parser that tests for `$0E` first is not guessing at
anything. The filed blocker names an obstacle that is not there.

And what `do_run` does instead is worse than a refusal — it reads the non-quote
as a bare `RUN` and **restarts the program, forever**:

| row | cf3300 | zb |
|---|---|---|
| `n.runvar` `RUN A$` | `File not found` | **`<RUN SCROLLED OFF>`** (the loop) |
| `n.runlit` 🟢 `RUN"FCZ.DAT"` | `File not found` | `File not found` |

🎯 **The `[R]` marker in `n.runvar`'s fixture is what makes the hang a reading.**
A silent infinite loop reads `<NO OUTPUT>` — indistinguishable from a machine
that printed nothing. Printing a marker every iteration fills the screen instead,
so `RUN` scrolls off, which this probe already treats as a reading and not a
silence. **Not fixed here** (§7), but filed against a measurement rather than
against a guess.

---

## 2. The face: measured, and D-FNEXPR's preserved guess was wrong

[`docs/spec-basic-fnexpr.md`](spec-basic-fnexpr.md) §3.3 kept `Syntax error` for
a non-string filename and filed the question:

> The reference may well answer `Type mismatch` (PLAY's own string operand does),
> but **that is UNMEASURED** — so today's face is preserved rather than guessed at.

Eight rows, taken before any decision about the ROM:

| row | statement | cf3300 | zb before |
|---|---|---|---|
| `n.opennum` | `OPEN 5 AS #1` | **`Type mismatch`** | `Syntax error` |
| `n.killnum` | `KILL 5` | **`Type mismatch`** | `Syntax error` |
| `n.savenum` | `SAVE 5` | **`Type mismatch`** | `load error` |
| `n.loadnum` | `LOAD 5` | **`Type mismatch`** | `load error` |
| `n.bloadnum` | `BLOAD 5` | **`Type mismatch`** | `load error` |
| `n.filesnum` | `FILES 5` | **0 entries + `Type mismatch`** | 5 entries + `Syntax error` |
| `n.savediv` | `SAVE 1/0` | **`Division by zero`** | `load error` |
| `n.opendiv` | `OPEN 1/0 AS #1` | **`Division by zero`** | `Syntax error` |

🎯 **THE THREE FACES DO CONVERGE — and that is now a reading, not the assumption
it would have been.** The brief for this slice said *"do not assume the three
faces should converge"*, and refusing to assume it is exactly what turned it into
evidence: zerobas answered a non-quote with three different things and the
reference answers one thing at all six verbs.

🔴 **But `Type mismatch` is not the whole rule, and the last two rows are why.**
`SAVE 1/0` answers **`Division by zero`**. The reference EVALUATES the operand
and the operand's own fault wins — bit for bit the rule D-MISS-1 measured at the
LET mirror (`A$=1/0` → `Division by zero`, not `Type mismatch`,
[`basic/missing.asm`](../basic/missing.asm) `els_typecheck`). A blanket
"non-string → ERR 13" would have matched six rows and been wrong on two.

### 2.1 🔴 The classifier read two of these as SILENCE, twice

`n.savediv` and `n.opendiv` first read `<NO OUTPUT>` on the CF-3300, and the
three bare-form rows did too. Both times the machine had printed a perfectly
good error the probe's `ERRORS` tuple could not name — `Division by zero`, then
`Missing operand`. **A classifier that cannot name an error reports it as a
silence, and a silence is what a diverging pair agrees on.** This is the
identical failure D-FNARG2 hit when `File not found` fell through, one slice
earlier, in the same file.

The second one was not diagnosed by guessing a third name: the screen was read
directly (`screen_tail`), which returned `'Missing operand in 10'`.

---

## 3. The change

### 3.1 The face costs **zero bytes**, because the routine already ships

```
fname_expr:     call    skip_spaces
                call    str_eval
                jp      nc,els_tc_common    ; was: jp nc,stmt_error
```

`els_tc_common` ([`basic/missing.asm`](../basic/missing.asm)) is D-MISS-1's tail:
clear the `ERRMARK` landmark, `eval` the operand as numeric, `check_expr_errors`
(so the operand's own fault aborts first), then `Syntax error` if nothing parsed
and `type_mismatch_error` otherwise. It already had two entry points —
`els_typecheck` and `elas_typecheck`, each popping its own saved word before
falling in — and this caller has none to pop, so it enters at the common label.
**One instruction changed, same three bytes, and it serves all seven verbs.**

⚠️ The dead return address `fname_expr` leaves on the stack is discarded by
`raise_error`'s own `ld sp,(SAVSTK)` unwind, which every exit from there takes.

### 3.2 The argument shape, at five more verbs

| site | before | after |
|---|---|---|
| `do_save` | `skip_spaces` / `cp '"'` / `jp nz,load_error` / `inc hl` | `call fname_expr` |
| `sav_is_disk`, `sav_is_cas` | `ld a,(hl)` / `cp '"'` / `jp nz` / `inc hl` | `ld hl,(FN_RESUME)` |
| `do_bsave`, `bsv_is_disk`, `bsv_is_cas` | ditto ×3 | ditto ×3 |
| `do_load` | ditto + a hand-rolled `"CAS:"` loop | `call fname_expr` + `dev_cmp` |
| `dl_is_cas`, `dl_is_disk` | `call parse_close_run` | `ld hl,(FN_RESUME)` / `call pcr_noquote` |
| `do_bload` (resident stub) | — | `call fname_expr` before `ld (BL_PTR),hl` |
| `do_bload` (tenant body) | the opening quote gate | gone; two arms take `FN_RESUME` |
| `do_files` | `cp '"'` / `jr nz,df_nofilespec` | end/`:` test, else `fname_expr` |

**`pcr_noquote`** is a **zero-byte label** inside `parse_close_run`, just past the
four-instruction closing-quote check: once the filename is an expression there is
no quote in the program text to consume, so the `,R` / `,S` tail is entered
directly with the cursor reloaded from `FN_RESUME`.

### 3.3 🎯 BLOAD's filename must be evaluated in the RESIDENT half, and that is forced

`do_bload`'s whole body lives in a sub-ROM **page-1 tenant**
([`sub/bload.asm`](../sub/bload.asm)), and `str_eval` is main page 1 — switched
OUT while that tenant runs. This is the constraint
[`basic/save.asm`](../basic/save.asm)'s header already states for the rest of the
family (*"every one of these verbs PARSES with `eval`, which is main page 1 and
therefore switched out"*); BLOAD's opening quote gate was the one piece of parse
still on the far side of it. It comes back to the resident stub, and what crosses
is the staged name in `STRSCR` (RAM, mapped from both sides) plus `FN_RESUME`.

It costs the tenant nothing: the 9 B gate it drops pays for the two
`ld hl,(FN_RESUME)` its arms gain.

### 3.4 🔴 The deadcode gate found what that left behind

With both tenant arms entering at `pcr_noquote`, the sub-ROM copy of
`parse_close_run`'s **head** had no caller left and `check_dead_code.py` reported
a 6 B unreachable span. Deleted there and kept resident, where `do_run` still
parses a literal quote out of program text. *"Dead" is per-build* — the same body
live on one side and unreachable on the other, exactly as that gate documents.

### 3.5 🔴 `do_files` could no longer park its tenant op-selector across the parse

`do_files` wrote `DISKOP_OP` at the **head** of the statement — the one verb in
the family that did; `do_kill` and `do_name` write theirs immediately before
their `subrom_call`. The note beside it justified the head placement by checking
that `parse_disk_fcb`'s fcbname tenant *"touches `DISKOP_OP` nowhere"*.

**That claim is still true and stopped being sufficient the moment the filespec
became an expression.** The parse now begins with `str_eval`, which can run
arbitrary BASIC, and `INPUT$(n,#ch)` reaches the drive through `fatprim_bounce`,
whose *first instruction* is `ld (DISKOP_OP),a`. `FILES INPUT$(5,#1)` would have
handed the dirverb tenant a FAT-primitive selector.

The selector rides the stack across the parse and is written where the other two
verbs write theirs. **+5 B**, and the `DISKSLOT_OK` abort — the one exit that
RETURNS rather than raising — is balanced by hand, because the original note's
other warning (*"before the `push hl`, so this abort cannot leak a stack slot"*)
is still live. ⚠️ **This guard is not pinned by any row** (§6.4).

### 3.6 🔴 `skip_spaces` belongs to `fname_expr`, and four callers had been hiding that

D-FNEXPR's five call sites each did `call skip_spaces` immediately before
`call fname_expr`, so the contract *"HL → the filename argument"* was satisfied by
every caller and **never stated**. The new sites replaced gates that had BEEN
that `skip_spaces`, and dropping the gate dropped the skip: `SAVE A$` handed
`str_eval` a SPACE, and three rows read `Type mismatch` where the CF-3300 says
`OK`.

🎯 **The 🟢 literal controls were structurally blind to it.** `SAVE"FC1.DAT"` has
no space between verb and argument, and a variable form cannot not have one — so
`f.savelit` was green in the very run where `f.savevar` was red, and the pair
separated the two only by an accident of how each is spelled. Absorbing the skip
into `fname_expr` states the contract once, enforces it once, and is **−9 B**
rather than +12: four callers drop theirs, `do_files` keeps its own because it
READS the skipped byte.

---

## 4. Cost

Measured from clean, never counted:

| wall | at `cffb34d` | after | delta |
|---|---|---|---|
| main page 1 | 14 B | **50 B** | **+36 B recovered** |
| page-0 low | 22 B | 22 B | 0 |
| sub page 0 | 3299 B | 3299 B | 0 |
| sub page 1 | 1615 B | **1624 B** | **+9 B recovered** |

ROM ids after: `build/basic-reloc.rom` sha256[:8] = **`f3c2a739`**,
`build/sub.rom` = **`cf712906`** (was `257af791` / `d4427e18`). Both moved, and
both are the images the knives of §6 were scored against.

🎯 **THE FIX IS A CARVE.** Nine literal-quote gates cost more than the calls that
replace them, `dev_cmp` absorbs a third hand-rolled copy, `skip_spaces` absorbs
four call sites, and the tenant sheds a gate and a dead span. The three deliberate
spends inside that — `fname_expr`'s skip (+3), the `do_files` argument test (+7),
the op-selector park (+5) — are each named above.

---

## 5. Result

`make namspc-acceptance`: **75/75 → 95/95**, deferred **10 → 5**. Nine rows
graduated (the eight D-FNARG2 rows plus D-FILESIDE's `f.filesvarl`), and eleven
new rows were added and score green.

| row | statement | cf3300 | zb before | zb after |
|---|---|---|---|---|
| `f.savelit` 🟢 | `SAVE"FC1.DAT"` | `OK` | `OK` | `OK` |
| `f.savevar` | `SAVE A$` | `OK` | **`load error`** | **`OK`** ✅ |
| `f.loadlit` 🟢 | `LOAD"FCZ.DAT"` | `File not found` | `File not found` | `File not found` |
| `f.loadvar` | `LOAD A$` | `File not found` | **`load error`** | **`File not found`** ✅ |
| `f.bloadlit` 🟢 | `BLOAD"FCY.BIN"` | `File not found` | `File not found` | `File not found` |
| `f.bloadvar` | `BLOAD A$` | `File not found` | **`load error`** | **`File not found`** ✅ |
| `f.fileslit` 🟢 | `FILES"FC*.*"` | `File not found` | `File not found` | `File not found` |
| `f.filesvar` | `FILES A$` | `File not found` | **`Syntax error`** | **`File not found`** ✅ |
| `f.filesvarl` | `FILES A$`, counted | `0 entries + File not found` | **`5 entries + Syntax error`** | **`0 entries + File not found`** ✅ |
| `n.opennum` | `OPEN 5 AS #1` | `Type mismatch` | **`Syntax error`** | **`Type mismatch`** ✅ |
| `n.killnum` | `KILL 5` | `Type mismatch` | **`Syntax error`** | **`Type mismatch`** ✅ |
| `n.savenum` | `SAVE 5` | `Type mismatch` | **`load error`** | **`Type mismatch`** ✅ |
| `n.loadnum` | `LOAD 5` | `Type mismatch` | **`load error`** | **`Type mismatch`** ✅ |
| `n.bloadnum` | `BLOAD 5` | `Type mismatch` | **`load error`** | **`Type mismatch`** ✅ |
| `n.filesnum` | `FILES 5` | `0 entries + Type mismatch` | **`5 entries + Syntax error`** | **`0 entries + Type mismatch`** ✅ |
| `n.savediv` | `SAVE 1/0` | `Division by zero` | **`load error`** | **`Division by zero`** ✅ |
| `n.opendiv` | `OPEN 1/0 AS #1` | `Division by zero` | **`Syntax error`** | **`Division by zero`** ✅ |

🎯 **`f.filesvarl` is the row that proves the fix is a fix.** The FACE alone reads
the same whether the machine refuses at the parse or lists five files first —
which is why D-FILESIDE built `listface` — and it is the entry COUNT that
separates them, 5 → 0.

---

## 6. The knives

Three claims, three predictions written before the runs. See §6.4 for the one
guard this slice ships **unpinned**, said out loud rather than left to be found.

| knife | cut | predicted |
|---|---|---|
| **K-F2-1** | `jp nc,els_tc_common` → `jp nc,stmt_error` (the pre-slice target) | the 8 NON-STRING FACE rows, and no argument-shape row |
| **K-F2-3** | `sav_is_disk`'s `ld hl,(FN_RESUME)` → `ld hl,(STRPTR)` | `f.savelit`, `f.savevar`, `d.savedev` |
| **K-F2-4** | the tenant's `ld hl,(FN_RESUME)` → `ld hl,(BL_PTR)` | exactly `f.bloadlit` and `f.bloadvar` |

**All three EXACT**, on rows and on faces, first run.

| knife | measured |
|---|---|
| **K-F2-1** | `n.opennum` `n.killnum` `n.savenum` `n.loadnum` `n.bloadnum` `n.filesnum` → `<Syntax error>`, `n.savediv` `n.opendiv` → `<Syntax error>`. **8 rows, and not one argument-shape row moved.** ✅ |
| **K-F2-3** | `f.savelit` `f.savevar` `d.savedev` → `<load error>`. **3 rows.** ✅ |
| **K-F2-4** | `f.bloadlit` `f.bloadvar` → `<load error>`. **2 rows.** ✅ |

**K-F2-1 is the load-bearing one.** It says the eight face rows are pinned by
exactly the one jump target that makes them pass, *and* — the half that is easy
to forget to check — that no argument-shape row depends on it. The two halves of
this slice are separately pinned, not jointly.

🎯 **And it separates `Type mismatch` from `Division by zero` with one cut.**
Under the pre-slice target both `n.savediv` and `n.opendiv` fall to
`<Syntax error>`, because `stmt_error`'s own `check_expr_errors` never sees a
fault — `str_eval` refuses `1/0` at `is_letter` without evaluating anything.
Only `els_tc_common`'s `call eval` creates the fault that then wins.

### 6.4 🔴 One guard ships UNPINNED, and it is said out loud

The op-selector park of §3.5 is **not pinned by any row**. No battery executes
`FILES INPUT$(n,#ch)`, so a knife that unparked the selector would redden
nothing — and a green knife there would be a claim about the ROW SET, not about
the code, which is precisely what D-FNFUND's K-FF1 was. What *is* pinned is the
push/pop BALANCE: every `FILES` row would derail without it. The CLOBBER
protection is not.

Filed in `TODO.md` with the row that would make it live, and with the reason it
was not built here: the capture window. `OPEN` + `CLOSE` + `KILL` did not fit
the default `step` in this battery (D-FNFUND measured that), and the row needs an
OPEN, a channel read and a directory walk — so it wants a shape control or a
per-row `step` override, not a guess.

### 6.5 🔴 The `assert ROM != baseline` guard fired on the WRONG ARTIFACT

K-F2-4's first run aborted with *"ROM IDENTICAL TO BASELINE — make skipped the
build"*. It had not: `basic/bload-body.inc` is included **only** into
`sub/bload.asm`, so the cut moves `sub.rom` and leaves `basic-reloc.rom`
byte-identical. The guard [`spec-basic-fnexpr.md`](spec-basic-fnexpr.md) §6.3
added one day earlier — after a knife really was scored on a stale machine — was
**watching one ROM in a two-ROM tree**.

It was right to fire and wrong about why, which is the more useful failure of the
two: a guard that halts on a condition it has misidentified still stops you, but
its message sends you to the wrong place. It asserts on both images now and
prints which one moved (`moved: sub`). Same family as D-GATEBLIND's first knife
cutting the wrong ROM, one level out.

---

## 7. What is NOT closed, and where it went

Five rows stay DEFERRED, and each has an open `TODO.md` entry rather than a note
inside a `- [x]`:

* **`RUN A$`** — restarts the program forever; blocker refuted (§1.2), priced at
  ~+17 B against a 50 B wall. `n.runvar` built and waiting, `n.runlit` 🟢 green.
* **the bare forms** — `SAVE` / `LOAD` / `BLOAD` with no argument are
  `Missing operand` on the CF-3300 and `Syntax error` here. The DISPOSITION is
  fixed (they raise now; they printed before); the WORDING is D-MISS-1's own open
  residual at three more verbs — one message, five known sites.
* **`f.paren`** — `(A$)` in every string context; unchanged, but its note is
  corrected: the face is `Type mismatch` in all three contexts now instead of
  two-faces-by-context, so it is one divergence to fix rather than two to
  reconcile.
* **`CSAVE` / `CLOAD`** — the last two literal-only filename gates. Unmeasured,
  and the apparatus is the obstacle: they are cassette verbs and `namspc` has no
  tape. The reading belongs in `cassave` / `castail`.
* **the `do_files` guard** (§6.4) and the **nested-reject** hazard (a malformed
  filespec prints `load error` from *inside* `parse_disk_fcb` and `FILES` lists
  anyway — pre-existing, not widened here).


## D-FSPEC (2026-09-04) — a malformed filespec, measured; and the filed symptom is not what happens

TODO.md carried *"A MALFORMED FILESPEC PRINTS `load error` AND `FILES` LISTS
ANYWAY"*, noticed 2026-08-21 while walking this slice's sites and filed
explicitly as *not measured on the reference*. Measured now, twelve rows in
`basic_probe_namspc.py` through `listface`, whose reading is `N entries + <face>`
— the entry COUNT beside the message, because "printed an error" and "listed
anyway" are two independent facts and either alone is satisfied by the wrong
machine.

| `FILES` argument | CF-3300 | zerobas |
|---|---|---|
| *(bare)* | 5 entries + OK | 5 entries + OK |
| `"FC*.*"` | 0 + `File not found` | 0 + `File not found` |
| `"TOOLONGNAME.EXT"` | 0 + `File not found` | 0 + `File not found` |
| `"AB.EXTRA"` | 0 + `File not found` | 0 + `File not found` |
| `"TOOLONGNAME.EXTRA"` | 0 + `File not found` | 0 + `File not found` |
| `"A:B"` | 0 + `File not found` | 0 + `File not found` |
| `"A.B.C"` | 0 + **`Bad file name`** | 🔴 0 + `File not found` |
| `""` | 0 + **`Bad file name`** | 🔴 0 + `File not found` |
| `"."` | 0 + **`Bad file name`** | 🔴 0 + `File not found` |
| `".."` | 0 + **`Bad file name`** | 🔴 0 + `File not found` |
| `" "` | **5 entries + OK** | 🔴 0 + `File not found` |

### 🔴 The filed symptom is NOT reproduced, and the item's own row is why

`FILES"TOOLONGNAME.EXTRA"` — the exact string the filing named — reads
`0 entries + File not found` on **both** machines. **Every** zerobas row above
reads `0 entries`: nothing lists after a reject, and no row shows `load error`.
So the reasoning in the filing — that `parse_disk_fcb`'s 8.3 reject reaches
`jp bl_load_error`, which prints and RETURNS into `do_files`, which then walks
the directory with a half-built pattern — does not describe what these inputs do.

⚠️ **That does not retire the hazard**, which `sub/bload.asm` names in prose and
which is real in the source ([[load-error-is-not-abort]]). It says only that
`FILES` with a malformed filespec **does not reach it**: an over-long name is
accepted into a pattern that simply matches nothing. The filing's premise was an
unrun claim and the row it proposed would have measured nothing
[[a-justification-parenthesis-is-an-unrun-claim]].

### 🟢 What IS there: filespec validation, and a blank that means "no filespec"

Two rules, both missing here:

1. **A structurally malformed name is `Bad file name`**, not a pattern that
   fails to match — a second dot, an empty string, or a name that is only dots.
   Length is *not* part of it: an over-long name is `File not found` on both.
2. **A BLANK filespec is no filespec at all** and lists the whole directory,
   where zerobas treats it as a pattern and finds nothing.

⚠️ **DEFERRED ON A MEASURED BLAST RADIUS, NOT ON A WALL.** The check belongs in
`parse_disk_fcb`, which `basic/files.asm:768` records as having **eleven call
sites** — LOAD, SAVE, BLOAD, KILL, NAME and FILES among them — so one routine
serves every disk verb and a change there changes all of them
[[a-shared-tail-is-not-a-decision]]. The same eleven forms have **not** been
measured on those verbs, and doing that is the next step, not writing the check.
The disk ROM has 8910 B free (2026-09-04), so this is not a space decline.
