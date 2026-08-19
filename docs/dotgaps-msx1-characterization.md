# `.` — the three gaps D-DOTLINE left as CHOICES, measured on MSX1

**D-DOTGAPS.** D-DOTLINE shipped `.` (the current-line pseudo-line-number,
`DOT $F6B5`) with three questions answered by *reasoning* rather than by a
reading, and said so in as many words
([`spec-basic-dotline.md`](spec-basic-dotline.md) §5.1/§10.4,
[`dotline-msx1-characterization.md`](dotline-msx1-characterization.md) §5.1).
This measures all three, on two reference machines, before a line of `basic/` or
`sub/` is touched.

Sides: **vg8020** (Philips VG-8020, MSX1, cassette) · **cf3300** (National
CF-3300, MSX1 + disk + cassette) · **zb** (zerobas at HEAD `638a141`).
`--repeat 2` on every reference row: two independent boots, any row whose two
readings differ is `UNSTABLE` and fatal.

Probe: [`basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py), four
new batteries — `cld-` (line-storing inputs), `csv-` (the save walk over
cassette), `dsk-` (the same two rules over disk), `crf-` (refused stores).

---

## 0. What was a choice, and what each one decided

| gap | the choice, in its own words | what it decided |
|---|---|---|
| **1** | *"whether an ASCII LOAD/MERGE … writes `.` per line. zerobas's `cload.asm` reaches `store_line`, so it will inherit writer (a) whether or not the reference does. **Unmeasured, and the implementation is therefore a choice, not a reading.**"* (characterization §5.1) | shipped behaviour on every ASCII load path |
| **2** | *"§4 is **one reference**. `SAVE"CAS:",A` would give a second, and needs cassette support this probe does not have."* (§5.1) | a **12 B** design point — the `DOT` write lives *in* the shared `list_walk` rather than in `ex_list` (§4) |
| **3** | *"⚠️ Here rather than at `le_store`'s head, so an OOM store — which did not store anything — leaves `.` alone. UNMEASURED (no row fills TXTMAX and then reads `.`); the reasoning is 'the line the editor last touched', and a refused line was not touched."* ([`sub/lineedit.asm:155`](../sub/lineedit.asm:155)) | where the write instruction sits |

---

## 1. The apparatus, and the five things it had to be taught

### 1.1 A variable-free readout

`clp`'s readout is two typed lines, `Z=PEEK(&HF6B5)+256*PEEK(&HF6B6)` then
`PRINT"[";Z;"]"`, split because one line was a single column too long (§3 of the
D-DOTLINE characterization). **It cannot be used by the `crf` rows**: the
assignment CREATES A VARIABLE, and those rows read `.` on a machine deliberately
left with ~150 free bytes, where creating a variable is itself `Out of memory` —
the readout would report the state of its own failure.

    PRINT"[";PEEK(63157);PEEK(63158);"]"      36 chars, allocates nothing

Decimal `63157`/`63158` rather than `&HF6B5`/`&HF6B6` purely to fit: the hex form
is 39 characters, and the binding cap is **COLS(40) minus the 2-column margin**,
not the 40-byte KEYBUF. A wrapped echo returns `<none>` — a sentinel that also
means *no reading*. The readout prints both bytes, so it says `[ 40  0 ]` where
the `cle` rows say `[ 13  0 ]`: same shape, one fewer allocation.

### 1.2 The cassette seam — and one tape, not three

`omsx_repl.run_cases` already takes a `prologue` of raw Tcl (the
`plug joyporta` seam); `cassetteplayer insert {file}` and `cassetteplayer new
{file}` ride it with **no library change at all**. One prologue per call, so a
row that wants a mounted tape and one that wants a recording tape are delivered
in separate groups (`DEVICE` in the probe).

The read tape carries **three files in one image** — `DOTA` (ASCII, lines
10,20,30,40), `DOTD` (ASCII, the same four lines in DESCENDING file order),
`DOTT` (tokenised) — because the ROM searches forward by name. No remount, no
per-row prologue.

🔴 **`LOAD"CAS:"` ON A TOKENISED TAPE NEVER RETURNS ON THE REFERENCE.** With only
the $D3 file on the tape, the VG-8020 printed no `Found:` line and no error and
sat there; it searches past a non-ASCII header to the end of the tape and waits.
zerobas **answers** it (its 3-way header dispatch accepts $D3 through
`LOAD"CAS:"` too). So the natural row is a HANG row, it is not in the battery,
and the tokenised-load question is asked with `CLOAD"DOTT"` instead. The
divergence it exposes is filed in §6, not measured here — *a row that hangs one
side cannot gate anything.*

### 1.3 The capability lock

`SIDE_LOCK` held one global reason string for one cohort (`kwgz-`: AUTO and
LLIST hang a reference). That shape cannot express the disk rows, and it is
exactly why the ASCII-SAVE reading sat in a doc for a slice and a half: dropping
a row from the default three-side gate makes it gate **nothing**, and running it
on the VG-8020 would measure a machine with no `A:` device. It is now per row,
with a reason and a **kind**:

| kind | what the runner does | why |
|---|---|---|
| `hang` | the ROW leaves any run that includes a side it would wedge | running it is unsafe |
| `capability` | the row runs on the sides that HAVE the device and **gates across those** | running it elsewhere is merely meaningless |

A capability-locked row left with fewer than two sides is printed under
`MEASURED BUT NOT GATING` and counted nowhere — the `dir-name` shape (*a row
reported as if it had gated*) reached through a lock instead of through a
`--only` filter.

### 1.4 🔴 A control row that measured the exact opposite of its subject

`cld-cload` exists to say *a tokenised load stores no lines and writes nothing*.
Written as a bare `CLOAD`, it takes the **first file on the tape** — which is
`DOTA`, the ASCII one. On zerobas it read ` 40  0 `: a stored program, the same
value as `cld-asc`, i.e. the control agreeing with the positive row it was
supposed to contrast; on the references it would have gone looking for a $D3
header past the end of the tape. Named (`CLOAD"DOTT"`) it skips both ASCII files
and loads the file it is about. **The non-writer control was the row most able
to be silently wrong, because its expected value is "nothing happened".**

### 1.4b 🔴 …and the way a tape row bought TIME cost it the echo guard

A cassette LOAD or SAVE runs for 10–30 emulated seconds while the harness keeps
injecting on schedule, so a tape row has to advance the clock past the operation
before its readout is typed. The obvious way — pad the case with harmless `REM`
lines — **costs two screen rows apiece**, and the display is 24 rows deep.

`lnblank-echo` reported `MANGLED not echoed: ['10 REM A', '20 REM B']` for the
save rows on the CF-3300, whose Disk BASIC prints more per row than the
VG-8020's: the case's own payload had scrolled off the top. Shortening the
program moved the failure rather than removing it — the next run flagged
`['60 REM Y', 'LOAD"CAS:DOTD"']` on the **load** rows, which the run before had
passed. **The rows were sitting exactly on the boundary, so the same case passed
in one run and failed in the next.**

⚠️ **The values were right and stable at `--repeat 2` on every side** — what
failed was the ability to VERIFY the payload, which is the whole point of the
guard ([[decblank-echo-guard-blind]]: a delivery that cannot be verified may not
gate). ⚠️ **And a guard that passes intermittently is worse than one that fails**:
tuning the pad count would have bought a green run, not a verified one.

Fixed in the harness instead: `@WAIT<seconds>` (`omsx_repl.WAIT_PREFIX`) is a
pseudo-line that advances the emulated timeline and **types nothing** — no screen
rows, no echo to find, deterministic. The tape rows carry one each
(`@WAIT20`/`@WAIT35`/`@WAIT50`, sized by how far the ROM must seek along the
shared tape), and `echo_missing`/`say` skip them because nothing was typed.

### 1.5 🔴 A refusal row needs a companion that proves the refusal

`crf-oom` shrinks memory and stores a line that does not fit. In the pilot it
read ` 20  0 ` on **all three sides** and would have been written down as
agreement. It was not:

| | free after the shrink | the 32-byte line |
|---|---:|---|
| vg8020 / cf3300 | **148 B** | refused, `Out of memory` |
| zb | **646 B** | **stored** |

Both references wrote `.` on a REFUSAL; zerobas wrote it on an ordinary
SUCCESSFUL store. Same value, opposite events, one green row. Only
`crf-oomlst` — which lists the program and must show `99 REM Z` alone — can tell
them apart, and it is in the battery for that reason.
[[apparatus-is-part-of-the-measurement]], on a row whose subject is *something
not happening*.

🔴 **AND THE SAME COMPANION CAUGHT THE ROW A SECOND TIME, ON THE REFERENCE
SIDE.** The first version written into the probe typed `99 REM Z` *before* the
shrink. In that order `CLEAR 300,A+1000` itself raises `Out of memory`, so the
shrink never happens: free memory reads **409**, the "refused" line is an
ordinary successful store, and `crf-oomlst` listed **both** lines on the VG-8020
and the CF-3300 — a two-reference walk agreeing perfectly about nothing. Shrink
first, then store, and the refusal is real on both. Twice in one battery, the
row that carried the answer was fine and the row that proved the answer was
about the right event was the only thing that moved.

---

## 2. Gap 1 — does a line-storing INPUT write `.`?

Pre-state `.` = 60 (`60 REM Y` typed); no line of the loaded program is numbered
60, so any other value is a write.

| row | stimulus | vg8020 | cf3300 | zb |
|---|---|---:|---:|---:|
| `cld-ctl` ^ | tape mounted, nothing loaded | ` 60  0 ` | ` 60  0 ` | ` 60  0 ` |
| `cld-asc` | `LOAD"CAS:DOTA"` (ASCII 10,20,30,40) | ` 40  0 ` | ` 40  0 ` | ` 40  0 ` |
| **`cld-desc`** | `LOAD"CAS:DOTD"` (ASCII **40,30,20,10**) | **` 10  0 `** | **` 10  0 `** | **` 10  0 `** |
| `cld-mrg` | `MERGE"CAS:DOTA"` | ` 40  0 ` | ` 40  0 ` | ` 40  0 ` |
| `cld-cload` ^ | `CLOAD"DOTT"` (tokenised) | ` 60  0 ` | ` 60  0 ` | ` 60  0 ` |
| `cld-list` | `LIST .` after the ASCII load | `40 REM D` | `40 REM D` | `40 REM D` |
| `dsk-load` | `LOAD"A:DOTX.BAS"` (ASCII, disk) | — | ` 40  0 ` | ` 40  0 ` |
| `dsk-mrg` | `MERGE"A:DOTX.BAS"` | — | ` 40  0 ` | ` 40  0 ` |

🎯 **AN ASCII LOAD AND AN ASCII MERGE BOTH WRITE `.`, PER STORED LINE, ON EVERY
SIDE AND OVER BOTH DEVICES — AND `cld-desc` IS THE ONLY ROW THAT SAYS *PER
LINE*.** With the file in descending order the last line STORED is 10 while the
last line of the resulting PROGRAM is still 40; the reading is **10**. Every
other row in the battery is blind to that difference, and "an ASCII load writes
the program's last line" would have fitted all of them.

🎯 **THE TOKENISED LOAD IS THE CONTRAST, MEASURED.** `CLOAD"DOTT"` leaves `.` at
60 on all three sides: this is a rule about **storing lines**, not about the
verb `LOAD`. Writer (a) is exactly what it was measured to be in D-DOTLINE, and
it does not care who calls `store_line`.

**Gap 1 closes GREEN.** zerobas inherits writer (a) through `cload.asm`, the
reference does the same thing, and the inheritance shipped in D-DOTLINE is
correct — for the first time by measurement rather than by construction. The
value of the row set is that it is now **gated**: nothing about the ASCII load
paths could previously move without a `.` row noticing.

---

## 3. Gap 2 — the ASCII-SAVE reading, on a second reference

### 3.1 The cassette table

Program `10 REM A` + `40 REM D`, with `5 REM E` typed last, so `.` = 5 before the
save and the walk's last emitted line is 40. (The pilot used five program lines;
§1.4b is why the battery uses three.)

| row | stimulus | vg8020 | cf3300 | zb |
|---|---|---:|---:|---:|
| `csv-ctl` ^ | nothing saved | ` 5  0 ` | ` 5  0 ` | ` 5  0 ` |
| `csv-asc` | `SAVE"CAS:D",A` | ` 40  0 ` | ` 40  0 ` | ` 40  0 ` |
| `csv-tok` | `SAVE"CAS:E"` (no `,A`) | ` 40  0 ` | ` 40  0 ` | **` 5  0 `** 🔴 |
| `csv-csave` ^ | `CSAVE"F"` | ` 5  0 ` | ` 5  0 ` | ` 5  0 ` |

🎯 **THE ASCII-SAVE WRITER IS CONFIRMED ON A SECOND REFERENCE, AND ON A SECOND
DEVICE.** The 12 B design point D-DOTLINE bought with a one-machine reading
(§4: the write belongs *inside* the shared walk, not in `ex_list`) is no longer
one machine's word: `SAVE",A"` writes `.` on the VG-8020 over cassette exactly
as it does on the CF-3300 over disk. **`CSAVE` is the contrast** — a tokenised
write, no walk, `.` untouched — so "an ASCII save writes it" cannot be read as
"any cassette save writes it".

### 3.2 🎯 …and the second reference contradicted the INTERPRETATION, not the reading

`csv-tok` looked at first like a cassette-specific tokenised writer: the same
verb without `,A` writes `.` on both references but not on zerobas, while the
DISK tokenised save writes nothing anywhere. **The tape says otherwise.**
Recorded to WAV and decoded ([`cas_decode.py`](../probes/lib/cas_decode.py)):

| what wrote it | first bytes of the tape | format |
|---|---|---|
| vg8020 `SAVE"CAS:E"` (no `,A`) | `ea ea ea … 45 20 20 20 20 20 35 20 52 45 4d …` → `E     5 REM E` | **$EA, ASCII** |
| vg8020 `SAVE"CAS:D",A` | `ea ea ea …` | $EA, ASCII |
| **zb `SAVE"CAS:E"`** | `d3 d3 d3 … 45 20 20 20 20 20 09 80 05 00 8f …` | **$D3, tokenised** |

✅ **CLOSED 2026-08-07 by D-CASSAVE** ([spec-basic-cassave.md](spec-basic-cassave.md),
reading [cassave-msx1-characterization.md](cassave-msx1-characterization.md)) for
**0 B**. That battery decoded the **CF-3300** too (this table is the VG-8020
alone, which is not enough to re-specify a shipped format), decoded `,A` and
`CSAVE` as well, and confirmed what this section could only infer: `CSAVE` really
is `$D3` on all three sides, and `SAVE"CAS:x"` and `SAVE"CAS:x",A` are one
behaviour. `csv-tok` now reads ` 40  0 ` and is **de-pinned into the scored set**
— green with no `.` change at all, exactly as predicted below.

🔴 **`SAVE"CAS:name"` IS AN ASCII SAVE ON MSX1.** It drives the same walk `,A`
does, which is why it writes `.`; `CSAVE` is the tokenised one. zerobas wrote a
tokenised tape there — its own [`basic/save.asm:12`](../basic/save.asm:12) says
*"SAVE "CAS:F" -> tape tokenised"* — so **`csv-tok`'s `.` divergence is a
symptom of a SAVE-FORMAT divergence, not of a `.` defect** (§6, D2). The rule
this slice is measuring survives intact and gets simpler: *the ASCII output walk
writes `.`; a tokenised write does not.*

### 3.3 The disk table, now GATING rather than doc-only

cf3300 + zb (capability-locked away from the VG-8020, §1.3):

| row | stimulus | cf3300 | zb |
|---|---|---:|---:|
| `dsk-ctl` ^ | nothing saved | ` 5  0 ` | ` 5  0 ` |
| `dsk-savasc` | `SAVE"A:DOTX.BAS",A` | ` 40  0 ` | ` 40  0 ` |
| `dsk-savtok` ^ | `SAVE"A:DOTY.BAS"` | ` 5  0 ` | ` 5  0 ` |

This reproduces the D-DOTLINE characterization §4 table (which read 40 / 20
against a `.`=20 pre-state) through a different readout and a different
pre-state, and it is now a row in a standing gate instead of a paragraph in a
document.

---

## 4. Gap 3 — does a REFUSED store write `.`?

### 4.1 Two refusal shapes, refusing at different stages

| shape | stimulus | refused with | refused where |
|---|---|---|---|
| ceiling | `65530 REM B` | `Syntax error` | at the LINE NUMBER (65529 is the ceiling, `lnblank-msx1-characterization.md` §3) |
| store | a 32-byte line into ~148 free bytes | `Out of memory` | at the MEMORY CHECK, after the number was accepted |

If both wrote, the rule would be *the number typed, whatever happens next*; if
neither did, *the success path*. **The pair is what locates the write between
them**, and one row alone could not have — [[one-row-cannot-separate-two-rules]].

### 4.2 The readings

| row | stimulus (pre-state) | vg8020 | cf3300 | zb |
|---|---|---:|---:|---:|
| `crf-ovrctl` ^ | `10 REM A` | ` 10  0 ` | ` 10  0 ` | ` 10  0 ` |
| `crf-ovr` | + `65530 REM B` | ` 10  0 ` | ` 10  0 ` | ` 10  0 ` |
| `crf-huge` | + `99999 REM B` | ` 10  0 ` | ` 10  0 ` | ` 10  0 ` |
| `crf-ovrsay` | the same, read as a message | `Syntax error` | `Syntax error` | `Syntax error` |
| `crf-oomctl` ^ | shrink, then `99 REM Z` | ` 99  0 ` | ` 99  0 ` | ` 99  0 ` |
| **`crf-oom`** | + a line that does not fit | **` 20  0 `** | **` 20  0 `** | ` 20  0 ` ⚠️ |
| `crf-oomsay` | the same, read as a message | `Out of memory` | `Out of memory` | `<nothing listed>` 🔴 |
| `crf-oomlst` | the same, program listed | `99 REM Z` | `99 REM Z` | **`20 REM …\|99 REM Z`** 🔴 |

🎯 **AN OOM-REFUSED STORE WRITES `.` TO THE LINE NUMBER THAT WAS TYPED, ON BOTH
REFERENCES, WHILE NOTHING WAS STORED.** `crf-oomctl` says `.` was 99 going in,
`crf-oomlst` says the program never changed, and `crf-oom` says `.` is 20.

🎯 **AND A REFUSAL AT THE LINE NUMBER WRITES NOTHING.** So the write is *after*
the number is validated and *before or regardless of* the memory check — which
is a placement, not a preference. It is also perfectly consistent with the rule
D-DOTLINE already measured for the bare-line-number delete (`cln-sdel`: `.`
records a line that no longer exists): **the number typed, not the line stored.**

⚠️ **THE `zb` COLUMN OF `crf-oom` IS NOT A READING OF THE SAME EVENT** (§1.5).
zerobas bounds a line store against **`TXTMAX`, an assembly-time constant**
([`sub/lineedit.asm:139`](../sub/lineedit.asm:139)) rather than against HIMEM,
so no `CLEAR` and no typed row can reach its OOM path at all: `crf-oomlst` shows
the line stored. The refusal is **bounded away, not measured**
([[gate-row-setup-can-expire]]), and gap 3's fix therefore cannot be gated by
any emulator row on the zerobas side — see §6/D1.

---

## 5. The rules, as an implementation has to state them

Amending [`dotline-msx1-characterization.md`](dotline-msx1-characterization.md)
§5:

* **R-DOT3a** (writer (a), *widened and now measured*) — **storing a line
  records the line number TYPED**, per line, whatever drove the store: the line
  editor, an **ASCII LOAD**, or an **ASCII MERGE**, over cassette or disk
  (`cld-asc` `cld-desc` `cld-mrg` `dsk-load` `dsk-mrg`). The **last line in FILE
  order** wins, not the program's highest line (`cld-desc` = 10).
  A **tokenised** load stores no lines and writes nothing (`cld-cload`).
* **R-DOT3a′** (*new, and the one zerobas does not implement*) — the write
  happens **after the line number is validated and regardless of whether the
  line is stored**: a store refused for `Out of memory` writes it (`crf-oom`), a
  line number refused for being past the 65529 ceiling does not (`crf-ovr`,
  `crf-huge`).
* **R-DOT3b** (writer (b), *second reference*) — the **ASCII output walk**
  records the last line it emitted, whether it is driven by `LIST`, by
  `SAVE",A"` on disk, or by `SAVE"CAS:name"` — which **is** an ASCII save on
  MSX1, with or without `,A` (§3.2). A **tokenised** write (`CSAVE`, disk
  `SAVE"file"`) walks nothing and writes nothing.
* **R-DOT4** (non-writers, *added*) — `CLOAD` (tokenised), `CSAVE`, and a
  mounted cassette by itself.

---

## 6. Divergences this measurement leaves on the table

| | what | where | evidence |
|---|---|---|---|
| **D1** | a **refused (OOM) store does not write `.`** on zerobas; both references write the typed number | [`sub/lineedit.asm:143`](../sub/lineedit.asm:143) (`le_ok`, the success path) | `crf-oom` + `crf-oomctl` + `crf-oomlst` on both references |
| **D2** | **`SAVE"CAS:name"` writes a TOKENISED tape**; both references write ASCII | [`basic/save.asm`](../basic/save.asm) `sav_is_cas` | the decoded tapes, §3.2 |
| **D3** | **`LOAD"CAS:"` accepts a tokenised tape** on zerobas; the reference searches past it and never returns | [`basic/cload.asm`](../basic/cload.asm) header dispatch | §1.2 |
| **D4** | a line store is bounded by the **constant `TXTMAX`**, not by HIMEM/`CLEAR`, so zerobas accepts lines both references refuse | [`sub/lineedit.asm:139`](../sub/lineedit.asm:139) | §4.2, `crf-oomlst` |

D1 is this slice's subject. D2 explains one row of it and is a **save-format**
question with its own probe consequences
([`basic_probe_tape_save.py`](../probes/basic/basic_probe_tape_save.py) asserts
the tokenised form). D3 and D4 are found-in-passing and owned by neither.

## 7. What is still NOT measured

* **whether the OOM write happens before or after the old line is deleted.** A
  replacement that runs out of memory could plausibly leave the program without
  its old line; no row types one. `crf-oom` inserts a line that does not exist
  yet, so it cannot see the difference.
* **what an ASCII LOAD does to `.` when the load itself runs out of memory**
  (`dpl_oom`). The same bound as D4 makes it unreachable by typing.
* **`MERGE` over a program that shares line numbers with the file** — the merge
  measured here adds four lines to a one-line program.
* the **cold** value, unchanged from D-DOTLINE §5.1: openMSX zero-fills RAM, so
  no emulator reading can separate a written 0 from power-on RAM.
