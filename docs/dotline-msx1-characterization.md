# `.` — the current-line pseudo-line-number, measured on MSX1

**D-DOTLINE.** What `.` resolves to, who writes it, and in which argument
positions it is accepted — measured on two reference machines before a line of
`basic/` or `sub/` was touched.

Sides: **vg8020** (Philips VG-8020, MSX1) · **cf3300** (Sanyo CF-3300, MSX1 +
disk) · **zb** (zerobas at HEAD `40647bd`). `--repeat 2` on every side: two
independent boots per row, any row whose two readings differ is `UNSTABLE` and
fatal.

Probe: [`basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
batteries `lna-*dot*` (stored bytes), `cln-` (a listing), `cle-` (a bracketed
value), `clp-` (the published cell).

---

## 0. What was already known, and what it could not say

D-DELETE ([`docs/spec-basic-delete.md`](spec-basic-delete.md) §6) and D-LSTRNG
([`docs/spec-basic-listrange.md`](spec-basic-listrange.md) §6) each measured `.`
on one verb and declined to implement it. Between them they established:

| | |
|---|---|
| `dlt-dot` / `lst-dot` | `.` names **line 40** with 10..40 entered in order |
| `dlt-dotedit` / `lse-dotedit` | …**line 20** once line 20 is re-entered |
| `lna-deldot` / `lna-listdot` | `.` is **not crunched** — it reaches the statement as the literal `$2E` |

🔴 **All four rows measure ONE writer — storing a line — and one argument
position.** "The line the editor last touched" is a claim about `store_line`;
it says nothing about what a `RUN`, an error, a `LIST`, a `DELETE`, a `NEW` or a
cold machine leave in the same cell, and nothing about `.` anywhere but alone.
A resolver built on those four rows would be a rule one **writer** and one
**position** wide, which is the same mistake D-DELETE declined to make one
**verb** wide.

## 0.1 🔴 The behavioural readout is structurally blind to the cold machine

`LIST .` is the natural readout: it prints the line, and the line's text names
its own number back. It cannot answer the cold question, and not for want of
care — **on a cold machine the program is necessarily empty.** The only way to
get program text into a cold machine is a path that itself writes the cell, so
`LIST .` prints nothing whatever `.` holds, on every side, and every reading
compares EQUAL. That is [[readout-blind-to-its-own-subject]] exactly: a readout
that agrees on all sides while seeing nothing.

🎯 **The published work area names the variable, which is what makes the cold
value readable at all.** C-BIOS `systemvars.asm`:

```
; F6B5-F6B6: line number of last used (changed, listed, added) line
DOT:            equ     $F6B5
```

That is the same allowed source ([`allowed-sources.md:121`](allowed-sources.md:121),
rated **B / Conditional** *for published sysvar addresses*) the sysvar
denominator is generated from, and the same one D-REHOME honoured `ERRFLG` /
`ERRLIN` / `ONELIN` / `ONEFLG` / `DEFTBL` out of. `$F6B5` sits in the gap
between two cells zerobas **already** holds at their published addresses —
`ERRLIN $F6B3` and `ONELIN $F6B9`.

So the walk is run **twice, through two independent readouts**:

* **`cln`/`cle` — behaviour.** What `LIST .` lists and what `DELETE .` deletes.
  This is the reading about the *language*.
* **`clp` — the cell.** `PRINT"[";PEEK(&HF6B5);PEEK(&HF6B6);"]"` after the same
  stimulus. This is a reading about a *byte*.

⚠️ **A PEEK is evidence about `.` only where it AGREES with its behavioural
twin.** Every `clp` row below has a `cln`/`cle` twin asking the same question,
and the pairing is the check: if the two ever part company, `$F6B5` is not what
`.` resolves and the whole `clp` battery is measuring the wrong byte. Where they
agree, the cell readout extends into the rows behaviour cannot reach — the cold
machine, and `NEW`.

⚠️ **The published description is a HINT, not a reading.** "changed, listed,
added" predicts that `LIST` writes the cell; `cln-list`/`clp-list` are what
decide it. Nothing below is taken from the comment.

---

## 1. The crunch: does a `.` disarm line-number mode?

Stored bytes, `20 <verb> …` typed and read back. **8/8 gating rows agree across
all three sides**, 0 allowlisted.

| row | typed | stored |
|---|---|---|
| `lna-listdot` | `20 LIST .` | `<93> .` |
| `lna-deldot` | `20 DELETE .` | `<A8> .` |
| **`lna-listdotd`** | `20 LIST .-30` | **`<93> .<F2><0E><1E><00>`** |
| **`lna-listddot`** | `20 LIST 10-.` | **`<93> <0E><0A><00><F2>.`** |
| `lna-listdotb` | `20 LIST . -30` | `<93> . <F2><0E><1E><00>` |
| **`lna-deldotd`** | `20 DELETE .-30` | **`<A8> .<F2><0E><1E><00>`** |
| **`lna-delddot`** | `20 DELETE 10-.` | **`<A8> <0E><0A><00><F2>.`** |
| `lna-deldotdd` | `20 DELETE .-.` | `<A8> .<F2>.` |

🎯 **A `.` DOES NOT DISARM LINE-NUMBER MODE, AND NOTHING HAD LOCKED THAT.** The
`30` behind the `-` in `LIST .-30` is still an armed `$0E` reference
(`<0E><1E><00>`), on both references and on zerobas's own tokeniser. This is not
the obvious answer: `.` is a **name** character everywhere else in this probe —
the whole `dot` battery exists because `B.5` is one identifier — and a name
character is exactly what R-L3 says disarms the mode. Had it disarmed,
`LIST .-30`'s `30` would arrive as ASCII digits and a resolver written against
`$0E` would parse garbage.

⚠️ **`.` is the literal `$2E` in every position**, never a token, so **every
verb resolves it itself**. That is what makes this editor state rather than a
`LIST`/`DELETE` feature, and it is why the resolver belongs at the one place
both verbs already read a line number from.

⚠️ **The blank in `LIST . -30` is STORED** (`<93> . <F2>…`), as the editor stores
every typed blank (D-LNBLANK's R-N1). A resolver that reads `.` and then expects
the `-` immediately must skip blanks first, exactly as `ldr_num` already does
for a `$0E`.

---

## 2. What `.` resolves to — the behavioural walk

24 `cln` rows (readout: the listing between the command's echo and the prompt)
and 12 `cle` rows (readout: a bracketed value). **Both references agree on every
row**, on two independent boots each. zerobas reads `Syntax error` / ERR 2
throughout — R-LS6 / R-D6 answering the unknown `$2E`, the pinned state D-LSTRNG
and D-DELETE left behind.

### 2.1 Who writes `.`

`.` = 20 is arranged by re-entering line 20 last, so "last touched" (20) and
"highest" (40) give different answers; `10 REM A / 20 REM B / 30 REM C /
40 REM D` throughout unless noted.

| row | after… | `LIST .` reads | verdict |
|---|---|---|---|
| `cln-store` | 10..40 entered in order | `40 REM D` | storing **writes** |
| `cln-edit` | …line 20 RE-ENTERED | `20 REM B` | a replacement **writes** |
| `cln-ins` | …line 25 INSERTED | `25 REM E` | an insert **writes** |
| `cln-sdel` | …bare `20` (delete via store_line) | `<nothing listed>` | **writes**, to a line now GONE |
| `cln-sdelctl` | (control) `LIST` | `10 REM A\|30 REM C\|40 REM D` | line 20 really is gone |
| `cln-direct` | `.`=20, then `C=1` | `20 REM B` | a direct statement does **not** write |
| `cln-del` | `.`=20, then `DELETE 40` | `20 REM B` | 🔴 the DELETE **verb** does **not** write |
| `cln-delctl` | (control) `LIST` | `10 REM A\|20 REM B\|30 REM C` | line 40 really is gone |
| `cln-list` | `.`=20, then `LIST 40` | `40 REM D` | 🎯 `LIST` **writes** |
| `cln-clear` | `.`=20, then `CLEAR` | `20 REM B` | `CLEAR` does **not** reset |
| `cln-runctl` | (control) line 10 re-entered, no RUN | `10 A=A+1` | `.` really is 10 first |
| `cln-run` | …then `RUN` (runs to line 30) | `10 A=A+1` | `RUN` does **not** write |
| `cln-err` | …`20 ERROR 7`, then `RUN` | `20 ERROR 7` | 🎯 an **error** writes |
| `cln-stop` | …`20 STOP`, then `RUN` | `10 A=A+1` | a **break** does **not** write |
| `cln-cont` | …then `CONT` | `10 A=A+1` | `CONT` does **not** write |

🔴 **THE TWO DELETE PATHS DISAGREE, AND ONLY A WALK COULD HAVE FOUND THAT.**
Deleting line 20 by typing a bare `20` writes `.` (`cln-sdel` lists nothing, and
its control proves the line is gone rather than the readout blind); deleting
line 40 with the `DELETE` **verb** leaves `.` alone (`cln-del` still reads
`20 REM B`). Two ways to remove a line, the same visible effect on the program,
**different effects on `.`** — the bare number goes through the editor's store
path and the verb does not. Sampling one of the two would have produced a rule
that is wrong about the other half of the time.

🔴 **AN ERROR WRITES `.` AND A BREAK DOES NOT, AND `cln-stop` IS THE ONLY REASON
THAT IS A READING.** `cln-err` alone would have supported "anything that halts a
RUN records where"; `cln-stop` is the identical program with `STOP` in place of
`ERROR 7` and reads `10 A=A+1` — unchanged. This is [[one-row-cannot-separate-two-rules]]
again: `ERROR` is the variable, halting is not. (The published work area agrees
by having a *separate* cell for the break line, `OLDLIN $F6BE`.)

🎯 **`LIST` WRITES IT — the published description said so, and this is the row
that decides it rather than the comment.** `.` = 20, `LIST 40`, and `.` is 40.

### 2.2 🔴 `cln-list` says *that* LIST writes it and cannot say *what*

In `LIST 40`, line 40 is the argument, the low end, the high end **and** the only
line printed — four candidate rules with one reading, the `dlt-dot` ambiguity
exactly. §2.4 walks them apart.

### 2.3 `.` in every argument position

All with `.` = 20. `DELETE` rows read the surviving-lines bitmask
(`10 A=A+1 / 20 A=A+2 / 30 A=A+4 / 40 A=A+8`, so 15 = all four standing).

| row | typed | refs | means |
|---|---|---|---|
| `cln-lo` | `LIST .-` | `20 REM B\|30 REM C\|40 REM D` | low end, open high |
| `cln-hi` | `LIST -.` | `10 REM A\|20 REM B` | high end, open low |
| `cln-both` | `LIST .-.` | `20 REM B` | both ends |
| `cln-lonum` | `LIST .-30` | `20 REM B\|30 REM C` | `.` low, number high |
| `cln-numhi` | `LIST 10-.` | `10 REM A\|20 REM B` | number low, `.` high |
| `cln-rev` | `LIST 30-.` | `<nothing listed>` | lo>hi: LIST still has no reversal RULE |
| `cln-blank` | `LIST . -30` | `20 REM B\|30 REM C` | the stored blank is skipped |
| `cle-dctl` | (control) no DELETE | ` 15  0 ` | all four standing |
| `cle-donly` | `DELETE .` | ` 13  0 ` | line 20 gone |
| `cle-dlo` | `DELETE .-40` | ` 1  0 ` | 20, 30, 40 gone |
| `cle-dhi` | `DELETE 10-.` | ` 12  0 ` | 10, 20 gone |
| `cle-dboth` | `DELETE .-.` | ` 13  0 ` | line 20 gone |
| `cle-drev` | `DELETE 30-.` | ` 15  5 ` | lo>hi: R-D4 **does** apply to a `.` end |
| `cle-dgone` | `DELETE 20` then `DELETE 10-.` | ` 13  5 ` | R-D2 **does** apply to a `.` end |

🎯 **`.` IS AN ORDINARY LINE NUMBER ONCE RESOLVED, IN BOTH POSITIONS AND BOTH
VERBS — and `cle-drev`/`cle-dgone` are what say so rather than assume it.**
`DELETE 30-.` is ERR 5 because 30 > 20 (R-D4), and `DELETE 10-.` after line 20
has been deleted is ERR 5 because the high end names no stored line (R-D2). Both
of DELETE's asymmetric end rules fire on a `.`-resolved end exactly as on a typed
one. ⚠️ `cle-dgone` is a **compound** row — it reads R-D2 only because `cln-del`
independently says the `DELETE` verb does not move `.` — and its ` 13 ` confirms
that from the other side: line 20 was deleted and nothing else was.

### 2.4 The cold machine — bounded here, measured in §3

| row | typed | refs | zb |
|---|---|---|---|
| `cln-cold` | `LIST .` | `<nothing listed>` | `Syntax error` |
| `cln-coldctl` | `LIST 10` | `<nothing listed>` | `<nothing listed>` |
| `cle-cold` | `LIST .` → `ERR` | ` 0 ` | ` 2 ` |
| `cle-coldlist` | `LIST 0` → `ERR` | ` 0 ` | ` 0 ` |
| `cle-colddel` | `DELETE .` → `ERR` | ` 5 ` | ` 2 ` |
| `cle-colddel0` | `DELETE 0` → `ERR` | ` 5 ` | ` 5 ` |

`LIST .` on a cold machine is **not a refusal** (ERR 0, and this readout demonstrably
prints an error message into the tail when there is one — `lst-comma` is the
precedent), and `DELETE .` is ERR 5 exactly like `DELETE 0`. So the cold value is
**bounded to "behaves like 0"** and is **not measured** by any of these rows: an
empty program cannot distinguish 0 from any other number. §3 reads the value
itself.

### 2.5 🔴 What exactly does `LIST` record? Four candidate rules, one reading

`cln-list` (`LIST 40` → `40 REM D`) says *that* `LIST` writes `.` and cannot say
*what*: line 40 is the argument, the low end, the high end **and** the only line
printed. That is `dlt-dot`'s ambiguity a second time, and the answer is a walk,
not a sample.

| row | `.` before | typed | `LIST .` then reads | kills |
|---|---|---|---|---|
| `cln-list` | 20 | `LIST 40` | `40 REM D` | (nothing — all four fit) |
| `cln-listrng` | 20 | `LIST 10-30` | **`30 REM C`** | "the low end", "the argument" |
| `cln-listbare` | 20 | `LIST` | `40 REM D` | "the high end" (it is 65535 here) |
| `cln-listmiss` | 20 | `LIST 25` | **`20 REM B`** | "any LIST writes" |
| `cln-dotthen` | 20 | `LIST .-30` | `30 REM C` | "the write precedes the resolve" |

🎯 **`LIST` RECORDS THE LAST LINE IT ACTUALLY PRINTED — and a `LIST` that prints
nothing writes nothing.** `LIST 10-30` records 30, not the low end and not the
argument; bare `LIST` records 40, so it is not the high end (which is 65535
here); and `LIST 25`, which matches no stored line, leaves `.` at 20 untouched.
Three rows, three rules killed; `cln-list` alone would have supported all four.

🎯 **`cln-dotthen` settles the ORDER, which an implementation has to get right
and no other row asks.** `LIST .-30` with `.` = 20 resolves `.` to 20 (it lists
lines 20 and 30, per `cln-lonum`) and only *then* records 30. Resolve first,
write after — a resolver that updated `.` before parsing its own argument would
list from 30, or from whatever the previous listing left.

⚠️ **This is the one rule in the slice that is not free**, and §3 of the spec is
where that is costed: "the last line printed" is known only inside the walk, and
zerobas's walk (`list_walk`, [`basic/list.asm:122`](../basic/list.asm:122)) has
**three callers** — `ex_list` and the two ASCII-SAVE paths through `list_all`.
D-LSTRNG's §3.3 found the mirror-image hazard in the same routine (a `LIST`
range leaking into `SAVE",A"`); a `DOT` write placed in the walk would leak the
same way.

---

## 3. The cell — what `LIST .` cannot ask

`clp` rows, readout `Z=PEEK(&HF6B5)+256*PEEK(&HF6B6)` then `PRINT"[";Z;"]"`.
**Both references agree on every row**; every row has a behavioural twin in §2
and **every twin agrees**, which is what makes `$F6B5` evidence about `.` rather
than about a byte.

| row | after… | refs | zb | §2 twin |
|---|---:|---:|---:|---|
| `clp-cold` | (nothing typed) | **0** | 0 | — *(behaviour cannot ask)* |
| `clp-store` | 10..40 entered | 40 | 0 | `cln-store` ✅ |
| `clp-edit` | …20 re-entered | 20 | 0 | `cln-edit` ✅ |
| `clp-ins` | …25 inserted | 25 | 0 | `cln-ins` ✅ |
| `clp-sdel` | …bare `20` | 20 | 0 | `cln-sdel` ✅ |
| `clp-direct` | `C=1` | 20 | 0 | `cln-direct` ✅ |
| `clp-del` | `DELETE 40` | 20 | 0 | `cln-del` ✅ |
| `clp-list` | `LIST 40` | 40 | 0 | `cln-list` ✅ |
| `clp-clear` | `CLEAR` | 20 | 0 | `cln-clear` ✅ |
| **`clp-new`** | **`NEW`** | **20** | 0 | — *(behaviour cannot ask)* |
| `clp-runctl` | (control) no RUN | 10 | 0 | `cln-runctl` ✅ |
| `clp-run` | `RUN` | 10 | 0 | `cln-run` ✅ |
| `clp-err` | `RUN` over `20 ERROR 7` | 20 | 0 | `cln-err` ✅ |
| `clp-stop` | `RUN` over `20 STOP` | 10 | 0 | `cln-stop` ✅ |
| `clp-cont` | …then `CONT` | 10 | 0 | `cln-cont` ✅ |
| **`clp-direrr`** | `ERROR 7` **typed directly** | **20** | 0 | `cln-direrr` ✅ |
| **`clp-trap`** | trapped error, handler at 50 | **50** | 0 | `cln-trap` ✅ |
| `clp-untouch` | `C=1` `D=2` on a cold machine | 0 | 0 | — |

🎯 **THE COLD VALUE IS 0.** `clp-cold` reads 0 on both references, which §2.4
could only bound. `clp-untouch` reads 0 after two direct statements, so it is a
value the machine holds rather than one nothing has written yet.

🎯 **`NEW` DOES NOT RESET `.`, AND ONLY THE CELL READOUT COULD HAVE SAID SO.**
`clp-new` reads 20 after a `NEW` that emptied the program. `LIST .` is
structurally blind here — after a `NEW` there is nothing to list either way —
so this is a rule an implementation would have had to guess. It is also the
opposite of `TRACEFLAG`, whose *only* writer besides its own statements is
`new_prog` (sysvars.inc:1131); "NEW clears the editor's state" would have been
the natural assumption and it is wrong.

🔴 **A DIRECT-MODE ERROR DOES NOT WRITE `.` — IT IS NOT `ERRLIN`'S 65535
CONVENTION, IT IS NO WRITE AT ALL.** `clp-direrr` types `ERROR 7` at the prompt
with `.` = 20 and reads **20**, unchanged. This matters because the obvious
implementation is to hang the write on `record_errline`
([`basic/interp.asm:925`](../basic/interp.asm:925)), which already computes
"the erroring line, or 65535 in direct mode" — and its direct arm would file
65535 where the reference files nothing. Two cells, two conventions, one
routine: `ERRLIN` and `DOT` part company exactly here.

🔴 **A TRAPPED ERROR READS THE HANDLER'S LINE (50), NOT THE ERRORING LINE (20).**
`cln-err`'s untrapped error records 20; `clp-trap`/`cln-trap` record **50**.
Two rules predict that and one row cannot separate them — see §3.1.

### 3.1 Trapped errors: two candidate rules, walked apart

`cln-err` (untrapped) records the erroring line 20; `cln-trap` records the
handler's line 50. Either (H1) a trapped error records where control WENT, or
(H2) `ON ERROR GOTO 50` writes `.` when it RESOLVES its target — which would
make a **line-number lookup** the writer and have nothing to do with errors.

| row | program | refs | kills |
|---|---|---:|---|
| `clp-onerr` | handler armed at 50, **no error ever raised** | **10** | **H2** |
| `clp-goto` | `20 GOTO 40`, no handler, no error | **10** | a branch is not a writer |
| `clp-gosub` | `20 GOSUB 40` | **10** | …nor is a call |
| `clp-trapend` | trapped error, handler is `50 END` | **20** | **H1** |
| `clp-trap` | trapped error, handler is `50 RESUME NEXT` | 50 | — |
| `clp-reslin` | …handler is `50 RESUME 30` | **50** | "the line RESUME goes TO" |
| `clp-res15` | …handler moved to `15 RESUME NEXT` | **15** | "50 is a coincidence" |

> 🔴 **THE CONCLUSION BELOW WAS WRONG, AND THE SLICE'S OWN KNIFE K5 CAUGHT IT
> AFTER THE CODE HAD SHIPPED.** It is kept, struck through by this note rather
> than quietly rewritten, because the *reason* it was wrong is the finding:
> every row it rested on had **two sufficient causes**. `RESUME NEXT` sends
> control to line 30, which then **falls into line 50 again**, where a second
> `RESUME` with no error active raises **ERR 22 in line 50** — so writer (c)
> produces 50 unaided, and a RESUME writer would too. `clp-res15` was never a
> RESUME row at all: its handler sits *before* the erroring line, so it runs in
> sequence and raises the same ERR 22 there. §3.2 has the row that settles it.

~~**BOTH HYPOTHESES ARE WRONG, AND THE WRITER IS `RESUME`.**~~ `ON ERROR GOTO`
resolving line 50 leaves `.` at 10, so a line lookup is not a writer (H2 dead);
entering the handler leaves `.` at **20**, the erroring line, so control transfer
is not one either (H1 dead). The single variable between `clp-trapend` (20) and
`clp-trap` (50) is `50 END` against `50 RESUME NEXT`. `clp-reslin` then shows
`RESUME 30` records **50**, not its target 30, and `clp-res15` moves the handler
to 15 and the answer moves with it.

~~**A `RESUME` records the line it is IN.**~~ — withdrawn, see §3.2.
⚠️ `cln-trap`'s single reading would have been written up as "a trapped error
records the handler" — a rule that is wrong about `50 END` and wrong about
*why* — and `clp-trapend` is one row. The correction below is the same lesson
one level up: `clp-trapend` was enough to kill H1 and **not** enough to
establish what replaced it.

### 3.2 🎯 There is no `RESUME` writer — the knife that reddened NOTHING said so

§3.1 concluded that `RESUME` writes `.`, and D-DOTLINE **implemented it**: ~12 B
of main page 1 in `ex_resume`. Knife **K5** cut that write and moved **zero of
139 rows**. A rule gated by nothing is the finding, not a clean run
([[knife-that-reddens-nothing-is-the-finding]]) — so the rule itself was put
back under the microscope instead of the knife being called uninformative.

Every row §3.1 rested on has **two sufficient causes**:

* `clp-trap` (`50 RESUME NEXT`) and `clp-reslin` (`50 RESUME 30`) resume into
  line 30, which then **falls through into line 50 again**. A second `RESUME`
  with no error active is **ERR 22, raised in line 50** — so writer (c) files 50
  by itself, with or without a RESUME writer;
* `clp-res15` puts the handler at line 15, **before** the erroring line, so it
  simply executes in sequence and raises that same ERR 22 there. K4 (cut the
  error writer) moves it; K5 does not.

**`clp-resend` is the row that separates them** — `30 A=A+4:END` stops the
program before line 50 can be re-entered, so the only thing that could write 50
is the `RESUME` itself:

| row | program | vg8020 | cf3300 | zerobas *as first shipped* |
|---|---|---:|---:|---:|
| `clp-resend` | `…30 A=A+4:END / 50 RESUME NEXT` | **20** | **20** | ~~50~~ |

🔴 **BOTH REFERENCES READ 20 — THE ERRORING LINE. `RESUME` IS NOT A WRITER**, and
the first implementation of this slice was measurably wrong in a case no row in
the 139 could see. Writer (d) is **deleted**; **14 B of main page 1 recovered**
(287 → 301 free). After the removal `clp-trap` still reads 50, `clp-reslin` 50
and `clp-res15` 15 on all three sides — writer (c) covers every one of them.

⚠️ **The order matters and is the whole lesson.** K5 could not fail: it was
written to score a rule, the rule was fiction, and "0 RED" is exactly what a
fiction produces. What turned that into a defect report was *refusing to accept
0 RED as a pass* and constructing the case the machine would get wrong.

🔴 **AND THE ERROR WRITER IS NOT `ERRLIN`'S.** `clp-direrr` types `ERROR 7` at
the prompt and `.` does not move at all, where `ERRLIN` files its measured
direct-mode sentinel 65535. The two cells are written by the same event with
different rules.

---

## 4. Does the ASCII-SAVE walk write `.` too?

⚠️ **cf3300 only — vg8020 has no disk, so this is a ONE-REFERENCE reading** and
is labelled as such wherever it is used. The disk is a throwaway copy (the same
`tempfile` + `shutil.copy` `run_side` makes), so nothing is written to the
oracle image. `.` = 20 throughout.

| case | typed | cf3300 |
|---|---|---:|
| control | (nothing saved) | ` 20 ` |
| **ASCII** | `SAVE"A:DOTT.BAS",A` | **` 40 `** |
| tokenised | `SAVE"A:DOTU.BAS"` | ` 20 ` |

🎯 **AN ASCII SAVE WRITES `.`, AND A TOKENISED SAVE DOES NOT — WHICH IS EXACTLY
WHAT "THE LIST WALK IS THE WRITER" PREDICTS.** The ASCII path renders the whole
program through the same line walk `LIST` drives, so it records the last line it
emitted (40); the tokenised path is a block write and touches nothing.

🔴 **THIS INVERTS THE OBVIOUS DESIGN, AND D-LSTRNG IS THE REASON IT LOOKED
OBVIOUS.** That slice found a real hazard in this very routine — a `LIST` range
leaking into `SAVE",A"` would have silently written two lines — and fixed it by
splitting the callers (`spec-basic-listrange.md` §3.3). Reading `.` the same way
says: put the `DOT` write in `ex_list` only, keep it out of `SAVE`, and pay ~16 B
of main page 1 for the separation. **The measurement says the opposite.** The
write belongs *in the shared walk*, where it costs ~4 B and is right about both
callers. Same routine, two shared-code questions, opposite answers — and
inheriting the earlier answer would have bought a more expensive bug.

---

## 5. The rules, as an implementation has to state them

* **R-DOT1** — `.` reaches the statement as the literal `$2E`, in every argument
  position, and does **not** disarm line-number mode: the number behind a `-` is
  still an armed `$0E` (§1). Every verb resolves it itself.
* **R-DOT2** — `.` resolves to a 2-byte cell holding a line number. Published
  name and address: **`DOT`, `$F6B5`**. **Cold value 0** (`clp-cold`).
* **R-DOT3** — the writers, and nothing else is one:
  * **(a) storing a line** — insert, replace, *or* the bare-line-number delete —
    records the line number **typed**, even when the line is thereby removed
    (`cln-store` `cln-edit` `cln-ins` `cln-sdel`);
  * **(b) the LIST walk** — records the **last line it printed**; a walk that
    prints nothing writes nothing (`cln-listrng` `cln-listbare` `cln-listmiss`).
    ⚠️ This includes **ASCII SAVE**, which drives the same walk (§4, cf3300
    only); a tokenised SAVE does not;
  * **(c) an error in a STORED line** — records the erroring line (`cln-err`).
    A **direct-mode** error writes nothing (`clp-direrr`);
  * ~~**(d) `RESUME`**~~ — **WITHDRAWN, §3.2.** There is no RESUME writer; the
    rows that suggested one are writer (c) firing on an ERR 22 raised inside the
    handler line. `clp-resend` reads **20** on both references.
* **R-DOT4** — measured **non**-writers, each with its own row: `RUN`,
  `STOP`/break, `CONT`, `CLEAR`, **`NEW`**, the `DELETE` **verb**, a direct-mode
  statement, `GOTO`, `GOSUB`, `ON ERROR GOTO`, a direct-mode error, a tokenised
  `SAVE`, and **`RESUME` in any form** (§3.2).
* **R-DOT5** — once resolved, `.` is an ordinary line number in **either** end of
  **either** verb's range: DELETE's asymmetric R-D2/R-D4 and LIST's
  R-LS1/R-LS3/R-LS5 all fire on it unchanged (§2.3).
* **R-DOT6** — a verb **resolves `.` before it writes it** (`cln-dotthen`).

### 5.1 What is still NOT measured

✅ **ALL THREE OF THESE WERE MEASURED BY D-DOTGAPS, 2026-08-03** —
[`dotgaps-msx1-characterization.md`](dotgaps-msx1-characterization.md),
[`spec-basic-dotgaps.md`](spec-basic-dotgaps.md). Two of the three reasoned
answers were right and one was wrong, which is the reason the exercise was worth
doing at all:

| | answer |
|---|---|
| ASCII LOAD/MERGE | **writes it, per stored line**, from cassette and from disk — zerobas' inherited behaviour was correct (§2). The last line in FILE order wins (`cld-desc` = 10), which no row of this slice could have said |
| §4's one reference | **confirmed on a second** (VG-8020, cassette) and a second device — and the tape decode showed `SAVE"CAS:name"` is itself an ASCII save, so the walk rule got simpler rather than wider (§3) |
| the OOM store | 🔴 **WRONG — the reference WRITES it**, to the line number typed, with nothing stored (§4). A line-number refusal does not, so the write sits between the two checks. Fixed by moving one instruction; the placement below is superseded |

The **cold** value is the one item still not measured, for the reason given here.

* whether an **ASCII LOAD/MERGE** (which stores each line through the editor)
  writes `.` per line. zerobas's `cload.asm` reaches `store_line`, so it will
  inherit writer (a) whether or not the reference does. **Unmeasured, and the
  implementation is therefore a choice, not a reading.**
* §4 is **one reference**. `SAVE"CAS:",A` would give a second, and needs
  cassette support this probe does not have.
* whether the cold **0** is a written value or power-on RAM. openMSX zero-fills
  RAM, so no emulator reading can tell; the same argument `init`'s ERR/ERL reset
  already carries (`basic/interp.asm:41`).
