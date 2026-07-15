# Arrays slice 2 — `ERASE` implementation contract

Sign-off input for the `ERASE` statement (arrays arc slice 2). Companion to
[spec-basic-arrays.md](spec-basic-arrays.md) (the arc spec) and
[docs/subrom-tenant-playbook.md](subrom-tenant-playbook.md). Slice 1 (numeric
arrays) shipped 2026-07-15; this slice adds array *freeing* + clean re-`DIM`.
Repack build only; must stay lean byte-identical.

**Provenance:** every behaviour below is a black-box observation of stock
`Philips_VG_8020` (MSX-BASIC 1.0) captured 2026-07-15 via the KEYBUF REPL driver
(`probes/lib/omsx_repl.py`, no ROM disassembly). Char scripts:
`scratchpad/erase_char{,2,3}.py`. Fold the value/error cases into
`make array-acceptance` when this lands.

---

## 1. Surface & scope

`ERASE <name>[,<name>...]` — free one or more arrays. Each `<name>` is a **bare
array name with an optional type suffix** (`%` `!` `#` `$` or none). **No parens,
no subscript.** Freeing an array reverts it to *undeclared*: a later reference
auto-dims it fresh (bound 10), and a later `DIM` succeeds with **no
`Redimensioned array`**.

Type is part of array identity (slice-1 §4.1 #7): `ERASE A` frees only the
default-type `A` (≡ `A#`, double) and leaves `A%`, `A!`, `A$` untouched.

Out of scope (unchanged deferrals): string arrays are slice 3 — so in slice 2 an
`A$` array can never *exist*, hence `ERASE A$` always hits the undeclared path
(§3) → `Illegal function call`. This is a **documented slice divergence** (the
reference erases a declared `A$` cleanly); it disappears in slice 3.

> **CORRECTION (2026-07-15, review F1 — do not repeat my error).** An earlier
> draft of this contract (and §4.1) claimed a `$` name "simply forms a
> string-typed key `ary_find` never matches." **That is false at the code
> level.** `var_name_key`'s `vnk_dollar` path (basic/vars.asm) hardcodes
> `VARTYPE=8` for a `$` suffix (documented there as defined-garbage the string
> store never reads) — which is **identical to a default-double `A` (also
> type 8)**. So parsing `ERASE A$` with `var_name_key` alone yields key
> `(A,0,type=8)`, and `ary_find` **matches and destructively frees the numeric
> `A`**. The string type code is **`1`** (int/single/double = 2/4/8; string =
> 1). The fix (§4.1) is to detect string-ness with `var_str_type` (which
> correctly returns 1 for both an explicit `$` **and** a DEFSTR-defaulted bare
> name) and force `ARY_TYPE=1`, so `ary_find` can never match a numeric
> descriptor → Tier-B IFC. The DEFSTR-bare case already worked by accident
> (`var_name_key`→`deftbl_lookup` gives 1); only the **explicit `$`** was
> broken. The adversarial review caught this; the green matrix did not (the §5
> minimum lacked the `erase.str.after.dim` case — now added).

## 2. Token

`ERASE` = **`$A5`** (captured, cross-checked vs MSX2 TH Table 2.20 / MAP — never
asserted from memory). Single-byte statement token, exactly like `DIM`=`$86`.
Crunch pins (stock VG-8020, stored-line deref):

| Source | Crunch | Note |
|---|---|---|
| `ERASE A`    | `a5 20 41 00`          | token, space, `A`, EOL |
| `ERASE A,B`  | `a5 20 41 2c 42 00`    | `,`=`$2c` list separator |
| `ERASE A%`   | `a5 20 41 25 00`       | `%`=`$25` |
| `ERASE A$`   | `a5 20 41 24 00`       | `$`=`$24` |
| `ERASE A()`  | `a5 20 41 28 29 00`    | tokenises, but Syntax error at RUN (§3) |
| `ERASE A(1)` | `a5 20 41 28 12 29 00` | tokenises, but Syntax error at RUN (§3) |

Wiring: add `ERASE_TOKEN equ $A5` to [basic/sysvars.inc](../basic/sysvars.inc)
(next to `DIM_TOKEN`); add `db 5,"ERASE",1,ERASE_TOKEN` to
[basic/kwtable.inc](../basic/kwtable.inc) (verify crunch-order placement — the
table is prefix-match-ordered; add a crunch-identity gate case per §5); add
`cp ERASE_TOKEN : jp z,ex_erase` at the [basic/interp.asm](../basic/interp.asm)
exec dispatch, inside the same `IF ROM_BASE < $4000` block as `ex_dim`.

## 3. Error surface — two tiers (both oracle-locked)

The reference splits `ERASE` errors into exactly two dispositions:

**Tier A — `Syntax error`** (a malformed *token where a name is expected*, or a
`(` after a name). Raised at statement execution (line-numbered). Cases:

| Source | Result |
|---|---|
| `ERASE` (no arg)        | Syntax error |
| `ERASE ,A` (leading comma) | Syntax error |
| `ERASE A,` (trailing comma)| Syntax error |
| `ERASE A,,B` (double comma)| Syntax error |
| `ERASE 5` (numeric)     | Syntax error |
| `ERASE A()` (empty paren)  | Syntax error |
| `ERASE A(1)` (subscript)   | Syntax error |

**Tier B — `Illegal function call`** (a well-formed bare name that is **not a live
array**). Cases:

| Source | Result |
|---|---|
| `ERASE A` where `A` never dimmed/touched | Illegal function call |
| `ERASE A` a second time (already erased)  | Illegal function call |
| `ERASE A%` where only default `A` exists (wrong type) | Illegal function call |
| `ERASE A!`/`A#`/`A$` undeclared           | Illegal function call |

Mapping to existing zerobas machinery — **no new error plumbing**:
- Tier A → `jp stmt_error` (the existing lowercase-`syntax error` raiser,
  interp.asm:376). **House-style deviation applies:** zerobas prints lowercase
  `syntax error` where the VG-8020 prints `Syntax error` — the same documented
  divergence as every other zerobas syntax error (slice-1 `err_syntax`). So Tier
  A cases are **NOT** byte-for-byte differential-gateable; gate them against the
  zerobas-expected lowercase text (see §5), consistent with the rest of the
  codebase.
- Tier B → tenant returns `ARY_ERR=2`, which `ary_errmap` already maps to
  `FPERR=8` → the **reference-verbatim capitalised** `Illegal function call`
  (arrays' own string, basic/arrays.asm). Tier B **is** byte-for-byte
  differential-gateable.

**Left-to-right, first-bad-name-wins.** `ERASE A,B` with `A` live and `B`
undeclared raises `Illegal function call` at the point `B` is reached; the
already-processed `A` is freed before the abort (only observable via `ON ERROR`,
out of scope). `ERASE Z,B` with `Z` undeclared aborts on `Z`; `B` is never
reached. Confirmed on the oracle (`erase.partial.A.first`, `erase.badname.first`).

## 4. Implementation (glue-in-main + pure-RAM leaf, the slice-1 split)

### 4.1 Main glue — `ex_erase` (basic/arrays.asm)

Model on `ex_dim` (arrays.asm:289), minus the bound list. Unlike `ex_dim` it
does **not reject** a `$` name (DIM defers string arrays to slice 3); instead it
**forces the array-lookup type to `1` (string)** for any string name so
`ary_find` can never match a numeric descriptor → Tier-B IFC (§3, and the F1
CORRECTION under §1 — this is the whole subtlety of the slice, get it right):

```
ex_erase:               ; HL enters on the ERASE token
    inc  hl             ; past ERASE
ee_lp:
    call skip_spaces
    ; expect a NAME start (letter). Anything else (EOL, ':', ',', digit, '(')
    ; -> Syntax error. This one peek covers Tier-A "no name where a name is
    ; expected": bare ERASE, leading/trailing/double comma, numeric arg.
    call is_letter          ; CF set = letter
    jp   nc,stmt_error
    ; string-ness detector FIRST (var_str_type: A=1/CF iff a `$` suffix OR a
    ; DEFSTR-defaulted bare name; HL NOT advanced). Remember it across
    ; var_name_key, which clobbers everything.
    call var_str_type
    push af                 ; [STR?] -- CF = "string name"
    call var_name_key       ; BC=key, (VARTYPE)=type, HL past name
    call skip_spaces
    ld   a,(hl)
    cp   '('
    jr   z,ee_synerr_pop    ; Tier A: 'ERASE A(' -> syntax error. MUST pop [STR?] first!
    ld   (ARY_KEY),bc
    pop  af                 ; recover [STR?]
    ld   a,(VARTYPE)        ; numeric: 2/4/8 as parsed
    jr   nc,ee_settype
    ld   a,1                ; string name -> type 1: never matches a numeric array
                            ; (2/4/8) -> Tier-B IFC. Uniform for explicit `$` AND
                            ; DEFSTR-bare. Slice 3 makes string arrays real and this
                            ; begins to match them (the divergence closes).
ee_settype:
    ld   (ARY_TYPE),a
    ld   a,2
    ld   (ARY_OP),a         ; op = ERASE
    push hl                 ; [CURSOR] -- ary_engine_call passes HL into the tenant
                            ; (CALSLT), which clobbers it; nothing restores it.
                            ; (Review-caught: without this, a successful `ERASE A`
                            ; on a live array corrupts the cursor -> phantom syntax
                            ; error on the FOLLOWING statement. The Tier-B path hid
                            ; it because fp_runtime_error abandons the cursor anyway.)
    call ary_engine_call    ; -> Z ok / NZ: FPERR already mapped+set (ARY_ERR=2 -> IFC)
    pop  hl                 ; [CURSOR] restored (harmless on the abort path)
    jp   nz,fp_runtime_error
    call skip_spaces
    ld   a,(hl)
    cp   ','
    jr   nz,ee_done
    inc  hl
    jr   ee_lp              ; next name
ee_done:
    jp   exec_stmt
ee_synerr_pop:
    pop  af                 ; balance [STR?] before the Tier-A exit
    jp   stmt_error
```

Two non-obvious stack obligations (trace every exit): the `[STR?]` AF pushed
before `var_name_key` must be popped on **both** the normal path (`pop af` after
the `(` check) and the `ERASE A(` Tier-A path (`ee_synerr_pop`); and `[CURSOR]`
must bracket `ary_engine_call`. Both were review findings — the second was
caught live by the implementer's own adversarial pass, the first by the F1 fix.

Notes:
- `ERASE A,` (trailing comma): after the `,` the loop re-enters `ee_lp`, the
  `is_letter` peek sees EOL → `stmt_error`. ✔ matches oracle.
- No `[CURSOR]`-on-stack dance (unlike `ex_dim`, which pushes across
  `ary_parse_subs_kt`) — `ex_erase` never parses a subscript list, so HL is a
  plain register cursor throughout. Simpler than `ex_dim`.
- Reuse `ex_dim`'s exact name-parse instructions (`var_str_type` +
  `var_name_key`) so the key/type derivation is identical to DIM/RESOLVE (the
  slice-1 lesson: identity is `(name0,name1,type)`; any drift desyncs `ary_find`).

### 4.2 Tenant leaf — `aeng_erase` (op=2, sub/arrays.asm)

Add `op=2` to the `ary_engine` dispatch (currently `op` `nz` → `aeng_dim`; make
it `op==1 → aeng_dim`, `op==2 → aeng_erase`). Pure-RAM, reuses `ary_find` +
`ary_stride`:

```
aeng_erase:                 ; ARY_KEY/ARY_TYPE set by the glue
    ld   bc,(ARY_KEY)
    ld   a,(ARY_TYPE)
    call ary_find           ; CF set + HL=desc base if found; CF clear if not
    jr   nc,aer_notfound
    ; found: compact. src = desc+stride ; dst = desc ; count = ARYTOP - src
    ; where ARYTOP = byte past the $0000 terminator (walk descriptors to term +2).
    ; LDIR shifts every following descriptor + the terminator down by `stride`.
    ; Nothing stores ARYEND (it is the self-describing $0000 sentinel), so the
    ; moved terminator IS the fix-up -- no pointer patch. ARYBASE=(PRGEND)+2 is
    ; unchanged. Erasing the last/only array lands the terminator at desc/ARYBASE
    ; = the "no arrays" state (same as ary_reset).
    ...compute src/dst/count, LDIR...
    xor  a
    ld   (ARY_ERR),a        ; 0 ok
    ret
aer_notfound:
    ld   a,2
    ld   (ARY_ERR),a        ; 2 -> IFC (ary_errmap -> FPERR=8)
    ret
```

ARYTOP walk: from `ARYBASE` (or from `desc+stride`), step `ary_stride` per
descriptor until `name0==0`, then `+2` for the terminator word — the same
terminator walk `ary_alloc` already does (aal_walk). Consider factoring a shared
`ary_top` helper if it saves bytes; otherwise inline (measure both).

**Paging invariant (unchanged):** `aeng_erase` touches only RAM (descriptor
region in the low free area, pages 2/3 always mapped) + reads `PRGEND` — no main
page-0/page-1 access, so the page-0-tenant paging story is moot exactly as for
`aeng_dim`/`ary_resolve`. No ABI extension.

## 5. Gate additions (`make array-acceptance`)

Extend the slice-1 differential probe. **Tier B + all value cases are
differential** (screen tail byte-for-byte vs VG-8020). **Tier A syntax-error
cases** assert the zerobas lowercase `syntax error` (house deviation, not
differential). Plus a **crunch-identity** case per §2 row.

> **Mode discipline (review F2).** The error-tier cases (Tier A **and** Tier B)
> MUST be run in **direct mode**, exactly as the slice-1 error cases are.
> zerobas's stored-`RUN` does **not** abort on a runtime error (a pre-existing,
> already-review-queue-logged landmine: `stmt_error`/`fp_runtime_error` `ret`
> into the run loop, so the program keeps executing after the error prints) —
> so a stored-mode error case diffs on the tail shape (ours prints the error
> *then the following lines' output*; the reference stops). Value/behaviour
> cases are fine stored (they carry no error). This is not an ERASE bug — slice
> 1's `DIM E(-1)` / re-DIM show the identical stored divergence.

Minimum new cases (all captured, expected values in `erase_char*.py` output):

- value/behaviour: `erase.then.print`→`0`, `erase.then.redim.value`→`0`,
  `erase.enables.redim`→ok (no Redimensioned), `erase.then.autodim`→`4 0`,
  `erase.preserves.other`→`9`, `erase.middle.compacts`→`9`,
  `erase.list.two`→`1 2`, `erase.type.independence`→`7`,
  `erase.typed.pct`→`0`, `erase.redim.diffdim`→`3`, `erase.longname`→`1`.
- Tier B (IFC, differential, **direct mode**): `undeclared.erase`,
  `double.erase`, `erase.wrongtype`, `erase.str.undeclared`,
  `erase.bang.matches`, and the **F1 regression** `erase.str.after.dim`
  (`DIM A(5):A(3)=7:ERASE A$` → IFC, `A(3)` still `7`) — the case the original
  green matrix lacked.
- Tier A (syntax error, house text, **direct mode**): `erase.bare.noarg`,
  `erase.trailing.comma`, `erase.leading.comma`, `erase.number`,
  `erase.double.comma`, `erase.sub.form` (`ERASE A(1)`),
  `erase.paren.form` (`ERASE A()`).
- crunch identity: `ERASE A`, `ERASE A,B`, `ERASE A%`, `ERASE A$`.

**Adversarial battery before "done"** (the standing slice-1 lesson): variable
context is minimal here (no subscripts), but exercise nesting/ordering:
mid-list erase then continue, erase inside a loop (`FOR I=1 TO 2:ERASE A:...`
after re-dim), erase the middle of 3 arrays and read *both* neighbours,
erase-all-then-redim-all. Run a fresh matrix, not just the pinned cases.

## 6. Fits / measurement

Slice 1 shipped at **148 B low / 6 B page-1 free** — page 1 is razor-thin. Keep
`ex_erase` (main glue) in the **low region** (page 0 of main is where arrays.asm
glue lives) and `aeng_erase` in the **sub-ROM tenant** (nearly empty). The only
page-1 cost is the `ERASE_TOKEN` dispatch (`cp`/`jp z` ≈ 5 B) + the kwtable entry
— watch the 6 B page-1 headroom; if it overflows, the fix is the same low-region
offload the playbook prescribes (move a page-1 byte down, not grow page 1).
Measure via `make build/basic-reloc.rom` then read
`__MEAS_LOW_END`/`__MEAS_PAGE1_END` from `build/basic-reloc.sym`; sub free =
trailing-`$FF` run per 16 KB page of `build/sub.rom`.

## 7. Deltas from slice 1 (checklist)

- [ ] `ERASE_TOKEN equ $A5` (sysvars.inc) + kwtable entry (+ crunch gate case).
- [ ] exec dispatch `cp ERASE_TOKEN : jp z,ex_erase` (interp.asm, in the
      `ROM_BASE < $4000` block).
- [ ] `ex_erase` glue (basic/arrays.asm): name+type parse loop, Tier-A
      `stmt_error`, `op=2` dispatch, Tier-B `fp_runtime_error`.
- [ ] `aeng_erase` tenant leaf (sub/arrays.asm): `op==2`, `ary_find`, compaction
      `LDIR`, `ARY_ERR` 0/2.
- [ ] ARY_OP doc comment update (`2=ERASE`) in sysvars.inc §10.2.
- [ ] host unit tests (tests/): compaction (erase middle/last/only), not-found →
      err=2, type-scoped key match, **F1 regression** (string-typed key never
      matches a numeric descriptor).
- [ ] `array-acceptance` gate cases (§5, error tiers **direct mode**) + fresh
      adversarial matrix.
- [ ] page-1 headroom check after build; lean byte-identical (`make ...` diff).

## 8. Documented deviations (pre-existing, NOT slice-2 blockers)

Two divergences the review confirmed are **shared, pre-existing zerobas
behaviour** that `ERASE` merely makes newly observable — not to be "fixed" in
this slice (each is its own separate arc/landmine):

1. **Stored-`RUN` does not abort on a runtime error** (review F2). After an
   `ERASE` error (either tier) inside a stored program, the reference stops the
   RUN; zerobas prints the error and continues to the next line. This is the
   already-review-queue-logged `stmt_error`/`fp_runtime_error`-`ret`-into-the-
   run-loop landmine (identical for slice-1 `DIM E(-1)` / re-DIM, and the whole
   deferred-error family). Consequence here is only the §5 direct-mode gate
   discipline.

2. **Whitespace inside an identifier is skipped** (review F3). The reference
   parses `ERASE A B` as the single name `AB` (CHRGET-style space skipping) →
   `Illegal function call`, nothing freed; zerobas's `var_name_key` stops at the
   space, so `ERASE A B` **frees `A`** then treats `B` as a junk statement
   (`syntax error`). This is the shared name-parser deviation (`A B=7` assigns
   `AB` on the reference; `DIM A B(5)` too) — `ERASE` just gives it a
   *destructive* observable. Documented; a name-parser fix is out of charter for
   the arrays arc.
