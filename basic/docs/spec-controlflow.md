# Behavioural spec: control-flow tokens + line-number references (Step B)

Source basis differs from the earlier slices. The REM/POKE/PEEK and Step-A crunch
specs were derived **oracle-first** (KBUF dumps) and cross-checked against the
documented token table. The control-flow keyword set is large, so this spec is
derived **documented-source-first** — the MSX2 Technical Handbook, an allowed
source — and cross-checked against the bytes zerobas has *already* oracle-confirmed
where they overlap. Every value below that overlaps an existing oracle observation
agrees with it, which is strong corroboration for the rest. An oracle sweep
(`basic_probe_*` typing `GOTO`/`FOR`/… lines and dumping KBUF) remains a worthwhile
belt-and-suspenders cross-check but is **not** a prerequisite: the documented table
is a valid clean-room source on its own (see `clean-room-policy.md`). No
disassembly was consulted.

The implementation lives in the **zerobas** repo, not here.

## Sources

- **MSX2 Technical Handbook, Chapter 2, Table 2.20 — "List of intermediate codes."**
  Read directly from the markdown/figure transcription at
  `Konamiman/MSX2-Technical-Handbook` (`md/Chapter2.md`). The keyword → token
  bytes below are quoted from that table verbatim.
- **MSX2 Technical Handbook, Chapter 2, Figure 2.12 — "Numeral formats in text."**
  Read directly from the figure image (`pics/Figure 2.12.png`). Gives the
  identification (numeric) codes `0B`–`1F`, including the line-number tokens that
  Table 2.20's text does not list.

## 1. Keyword tokens (Table 2.20)

Single-byte statement keywords (all confirmed against the handbook table; the
starred rows are already oracle-confirmed in zerobas and match exactly):

| Keyword  | Token | | Keyword   | Token | | Keyword   | Token |
|----------|-------|-|-----------|-------|-|-----------|-------|
| END      | `81`  | | INPUT     | `85`  | | RETURN    | `8E`  |
| FOR      | `82`  | | DIM       | `86`  | | STOP      | `90`  |
| NEXT     | `83`  | | READ      | `87`  | | PRINT *   | `91`  |
| DATA     | `84`  | | LET       | `88`  | | RUN       | `8A`  |
| GOTO     | `89`  | | GOSUB     | `8D`  | | NEW       | `94`  |
| IF       | `8B`  | | RESTORE   | `8C`  | | ON        | `95`  |
| REM *    | `8F`  | | LIST      | `93`  | | CLEAR     | `92`  |
| POKE *   | `98`  | | BLOAD *   | `CF`  | | DEF       | `97`  |

Tokens that sit in the operator/secondary-keyword range (used *inside* a
statement, not as a leading statement token):

| Keyword | Token   | Notes |
|---------|---------|-------|
| TO      | `D9`    | `FOR i = a TO b` |
| STEP    | `DC`    | optional `STEP c` |
| THEN    | `DA`    | `IF … THEN …` |
| ELSE    | `3A A1` | two bytes — a leading `:` (`3A`) then `A1`, mirroring REM's `3A 8F` |
| TAB(    | `DB`    | (for later `PRINT TAB(`) |
| SPC(    | `DF`    | (for later `PRINT SPC(`) |

REM (`3A 8F`) and PEEK (`FF 97`), `=`/`+`/`-`/`*` (`EF`/`F1`/`F2`/`F3`) already in
zerobas all match Table 2.20.

## 2. Line-number references (Figure 2.12)

A line number written as a *branch target* (the operand of `GOTO`, `GOSUB`,
`THEN`, `ELSE`, `RESTORE`, `RUN`, and each target in an `ON … GOTO/GOSUB` list)
is NOT crunched as an ordinary integer constant. It uses a dedicated
identification code:

```
0E  <lineno low>  <lineno high>      ; line number "before RUN" (as typed)
```

i.e. token `$0E` followed by the 2-byte line number, low byte first. Figure 2.12,
verbatim: *"Destination line number for the branch instruction. After RUN,
identification code is made 0DH and the line number is changed to the absolute
address."* So at run time the reference may be rewritten in place to:

```
0D  <addr low>  <addr high>          ; line number "after RUN" (resolved address)
```

`$0D` carries the absolute address of the target line's link field. zerobas may
adopt the same two-form scheme, or resolve `$0E` lazily each branch (simpler;
slower) — an implementation choice, not a format question. To keep stored
programs byte-identical to a reference ROM **as typed**, the tokeniser must emit
the `$0E` form; the `$0D` rewrite is a post-RUN runtime mutation.

### Tokeniser rule

After emitting one of the branch keywords above, a following decimal number is
crunched as `0E <lo> <hi>` rather than via the ordinary integer rule
(`$11+n` / `$0F` / `$1C`). For `ON x GOTO 10,20,30` every comma-separated number
in the list is a line-number reference. Elsewhere, numbers keep the ordinary
integer encoding from `spec-tokens-statements.md §3`.

## 3. Stored-line format (recap, from spec-bload-r.md §4 + Table 2.20 text)

Each stored line:

```
[link:2 LE]  [lineno:2 LE]  [intermediate-code text…]  [00]
```

ended by a link word of `0000`. Handbook text (Chapter 2): *"Link pointers and
line numbers are stored with their low bytes first and high bytes last"*; the
link is the **absolute address** of the next line. `TXTTAB` (`$F676`) points at
the first line; oracle-confirmed value after boot is `$8001`. zerobas implements
this in `basic/program.asm` (storage + NEW + sequential RUN already landed).

## 4. Implementation checklist (zerobas)

1. **Tokeniser** (`interp.asm`): add the keyword rows above to `kwtable`; add the
   branch-target rule so a number after a branch keyword crunches to `0E <lo> <hi>`.
2. **Executor** (`exec`): dispatch `GOTO` (`89`), `GOSUB`/`RETURN` (`8D`/`8E`),
   `IF…THEN…ELSE` (`8B`/`DA`/`A1`), `FOR…TO…STEP`/`NEXT` (`82`/`D9`/`DC`/`83`),
   `END`/`STOP` (`81`/`90`). These need run-time state RUN does not yet keep: a
   current-line cursor that `GOTO`/`NEXT` can redirect, a GOSUB return stack, and a
   FOR stack (var, limit, step, loop-line).
3. **Line resolver**: map a `$0E` line number to the address of that line's link
   field (walk the link chain). Optionally rewrite to `$0D`+address on first use.
4. **DATA/READ/RESTORE**: a DATA cursor walking `84`-tagged statements. **DATA
   items are stored as verbatim ASCII text, not crunched number tokens** — oracle
   (VG-8020, KBUF after crunch):

   ```
   data 5,6      -> 84 20 35 2C 36            ( "DATA" ' ' '5' ',' '6' )
   data -5,&hff  -> 84 20 2D 35 2C 26 68 66 66
   data 300,abc  -> 84 20 33 30 30 2C 61 62 63
   ```

   So `DATA` crunches like `REM` (body copied verbatim) **but stops at `:`** (the
   `:` ends the statement; the next statement is crunched normally). `READ` then
   parses the ASCII at run time. zerobas reproduces these byte-for-byte
   (`basic_probe_crunch.py`) and READs them back (`basic_probe_data.py`).

### `FOR` loop semantics (oracle observation)

The trip count of an "already finished" loop is dialect-sensitive, so it was
observed on the oracle rather than assumed. Driving a real **Philips VG-8020** in
direct mode (`basic_probe_loops.py` notes; direct execution is the only
reference path this harness reaches):

```
poke&hd000,0:for i=2 to 1:poke&hd000,1:next i:poke&hd001,i
  -> D000 = 01  (loop body ran once)   i = 03
```

So MSX-BASIC's `FOR` is **bottom-tested**: the body always runs at least once;
the limit comparison happens at `NEXT` (which first adds `STEP`, then tests).
zerobas reproduces `D000=01, i=03` for the same program (run as a stored program
+ `RUN`). Recorded here as the source of truth for the implementation's loop
test, since the reference can't be driven through stored-program `RUN` here.

## 5. Provenance summary

| Item | Value | Source | Status |
|------|-------|--------|--------|
| Keyword tokens (FOR/NEXT/GOTO/GOSUB/RETURN/IF/THEN/ELSE/TO/STEP/DATA/READ/RESTORE/RUN/NEW/END/STOP/ON/LIST/PRINT/LET/INPUT/DIM) | per §1 | MSX2 Technical Handbook, Table 2.20 (read directly) | sourced |
| Overlap with existing oracle tokens (POKE `98`, BLOAD `CF`, PEEK `FF 97`, REM `3A 8F`, `=`/`+`/`-`/`*`) | match | this project's oracle + Table 2.20 | sourced (double-confirmed) |
| Line-number ref `0E <lineno LE>` (before RUN) | `$0E` | MSX2 Technical Handbook, Figure 2.12 (read directly) | sourced |
| Line-number ref `0D <addr LE>` (after RUN) | `$0D` | MSX2 Technical Handbook, Figure 2.12 | sourced |
| Numeric id codes `0B`/`0C`/`0F`/`11–1A`/`1C`/`1D`/`1F` | per §2 table | Figure 2.12; `0C`/`0F`/`11`/`1C`/`1D` cross-confirmed by zerobas oracle | sourced |
| `FOR` is bottom-tested (body runs ≥ once; test at `NEXT`) | `D000=01, i=03` for `for i=2 to 1` | VG-8020 oracle, direct mode (§4) | sourced |
| `DATA` items stored as verbatim ASCII (not crunched); body ends at `:` | `data 5,6` -> `84 20 35 2C 36` | VG-8020 oracle, KBUF crunch (§4) | sourced |
| Oracle KBUF cross-check of the control-flow keywords | — | crunch probe: keywords + `<= >= <>` byte-identical | sourced |
