# D-DEFSTR — the DEFtbl string code, and the two namespaces it was hiding

*Spec + measurement. Filed as **"`DEFTBL_STR` should be `3`, not `1`"** by
D-REHOME ([`docs/sysvar-rehoming-decisions.md:279`](sysvar-rehoming-decisions.md:279)),
which deliberately unbundled it from the address move.*

Status: ✅ **LANDED.** Signed off as F1 + F2 + F3; implemented, measured, gated.
Result summary in §7.

---

## 1. The filed item, and why it is not the subject

The item as filed:

> **`DEFTBL_STR` should be `3`, not `1`.** Both references store `$03` for a
> `DEFSTR`'d letter; zerobas stores `$01`. It is the only one of `DEFTBL`'s 26
> bytes that differs.
> ⚠️ Deliberately NOT bundled with the address move: the type code is also a
> value WIDTH on the numeric side (2 int / 4 single / 8 double), and `3` is
> likewise the string DESCRIPTOR size — so this changes a type-dispatch constant
> and deserves its own knives, not a ride-along.

The caution was right and the **reason given for it was not the live one.** The
hazard is not a collision with the numeric widths `2/4/8`. It is a collision
with a *string* code:

* **Namespace P (published).** `DEFTBL[letter]` — a float type code. Both
  references: `2` int / **`3` string** / `4` single / `8` double. zerobas today:
  `2` / **`1`** / `4` / `8`.
* **Namespace C (chain).** The variable-chain entry's `type` byte, alias
  `ARY_TYPE` — zerobas' own design, `2/4/8` numeric and **`1` string**, with
  [`elsize_from_type`](../sub/arrays.asm:943) mapping `1 → 3` because a string
  element is a 3-byte `[len][ptr]` descriptor. (On the references the two
  namespaces are ONE: `3` is both the code and the descriptor width, so the
  identity `elsize == type` holds and no map is needed.)

**The two namespaces are distinct, and they happen to agree on the value `1`.**
`DEFTBL_STR` is used symmetrically for the write ([`sub/deftype.asm:87`](../sub/deftype.asm:87))
and the test ([`basic/vars.asm:178`](../basic/vars.asm:178)), so namespace P is
internally consistent whatever its value. But **three sites feed a namespace-P
code straight into namespace C**, and today that is invisible because `1 == 1`:

| | site | what it does with the value |
|---|---|---|
| **B1** | [`basic/vars.asm:147`](../basic/vars.asm:147) `vnk_suffix` | writes it into `(VARTYPE)`, read by `ev_f_var` / `ev_f_arr` |
| **B2** | [`basic/vars.asm:583`](../basic/vars.asm:583) `var_get` | passes it to `var_load_fac` as the chain type **and byte count** |
| **B3** | [`basic/vars.asm:595`](../basic/vars.asm:595) `var_set` | passes it to `var_store_fac` as the chain type **and byte count** |

"Byte count" is literal: [`var_load_fac`](../basic/vars.asm:585) and
[`var_store_fac`](../basic/vars.asm:392) both reach `ld c,a` / `ld b,0` / `ldir`
for any type that is not `2`. **A is the width.** So B2/B3 do not merely mislabel
a variable — they `ldir` `A` bytes.

The source comment at [`basic/vars.asm:147`](../basic/vars.asm:147) calls the B1
leak *"harmless: the numeric path is never entered for a name `var_str_type`
routed to STRTAB"*. §3 shows that claim is **false**, and that the rows which
appear to confirm it confirm it for a different reason.

---

## 2. Apparatus

`scratchpad/deftbl_leak_scout.py` — 18 rows, three sides, batched one boot per
side. Every RED candidate is paired with a GREEN control differing **only in the
`DEF` mnemonic**, so the DEFtbl byte is the sole moving part; that byte is
already known to move (D-REHOME's `s10`/`s11`, `[ 0 ]` vs `[]`).

Two apparatus faults were found and fixed before any row counted as a reading:

* 🔴 **The CF-3300 answered `None` on all 13 rows of the first cut**, and that
  reads as "the machine declined" when it means "the probe never asked". Without
  the bare-CR date-prompt answer and an explicit `SCREEN 0`, the CF-3300 sits at
  its date prompt rendering a SCREEN 1 name table into a SCREEN 0 scraper. Per-
  side `reset` lifted from [`basic_probe_lnblank.py:88`](../probes/basic/basic_probe_lnblank.py:88).
* 🔴 **A stored row read with `result_span` reports the ECHO of its own source
  line when `RUN` prints nothing.** `l2.str.for` came back `'";I;"'` and
  `l3.str.read` came back `'42'` — both are the *listing*, not output, and both
  looked like plausible values. Anchoring after the `RUN` echo instead turns a
  silent non-reading into the error text it actually was. *A sentinel that also
  means "no reading" is not a measurement* — [[say-row-without-brackets]], hit
  again in a fresh probe.

**Oracle-lock order honoured:** both references first
(`scout_refs2.txt`, `scout_nested_refs.txt`), zerobas only afterwards. The two
references agree on **all 18 rows**. Delivery is guarded on **every** side: each
row's own echo must be locatable or the row reports no reading.

---

## 3. The measurement

`Type mismatch` is matched on the stem only — zerobas prints lowercase by design
(D-2), so the wording is not compared.

| row | line | refs (both) | zerobas | |
|---|---|---|---|---|
| `cal.int.print` | `DEFINT A:PRINT"[";A;"]"` | `[ 0 ]` | `[ 0 ]` | 🟢 calibration |
| `cal.str.print` | `DEFSTR A:PRINT"[";A;"]"` | `[]` | `[]` | 🟢 calibration |
| `l1.int.rvalue` | `DEFINT S:B=S:…` | `[ 0 ]` | `[ 0 ]` | 🟢 control |
| `l1.str.rvalue` | `DEFSTR S:B=S:…` | Type mismatch | type mismatch | 🟢 |
| `l1.int.rvalue.set` | `DEFINT S:S=7:B=S:…` | `[ 7 ]` | `[ 7 ]` | 🟢 control |
| `l1.str.rvalue.set` | `DEFSTR S:S="AB":B=S:…` | Type mismatch | type mismatch | 🟢 |
| `l1b.int.arr` | `DEFINT S:B=S(1):…` | `[ 0 ]` | `[ 0 ]` | 🟢 control |
| `l1b.str.arr` | `DEFSTR S:B=S(1):…` | Type mismatch | type mismatch | 🟢 |
| `l1c.int.nested` | `DEFINT S:B=1+S:…` | `[ 1 ]` | `[ 1 ]` | 🟢 control |
| **`l1c.str.nested`** | `DEFSTR S:B=1+S:…` | Type mismatch | **`[ 1 ]`** | 🔴 **B1** |
| **`l1c.str.nested.set`** | `DEFSTR S:S="AB":B=1+S:…` | Type mismatch | **`[ 1 ]`** | 🔴 **B1** |
| **`l1c.str.nested.arr`** | `DEFSTR S:B=1+S(1):…` | Type mismatch | **`[ 1 ]`** | 🔴 **B1** |
| `l1d.str.arr.store` | `DEFSTR S:S(1)="AB":PRINT"[";S(1);"]"` | `[AB]` | `[AB]` | 🟢 control |
| `l2.int.for` | `DEFINT I:FOR I=1 TO 3:NEXT:…` | `[ 4 ]` | `[ 4 ]` | 🟢 control |
| **`l2.str.for`** | `DEFSTR I:FOR I=1 TO 3:NEXT:…` | Type mismatch in 10 | **`#   $  4$ ! s$ '  9   N X]`** | 🔴 **B2/B3** |
| `l3.int.read` | `DEFINT X:READ X:…:DATA 42` | `[ 42 ]` | `[ 42 ]` | 🟢 control |
| **`l3.str.read`** | `DEFSTR X:READ X:…:DATA 42` | `[42]` | **`#   $  4$ ! s$ '  9   N X ]`** | 🔴 **B2/B3** |
| **`l3.str.read.str`** | `DEFSTR X:READ X:…:DATA AB` | `[AB]` | `[]` | 🔴 **B2/B3** |

**11 green controls, 6 red rows.**

### 3.1 🔴 The rows that AGREED agreed for the wrong reason

`l1.str.rvalue` / `.set` / `l1b.str.arr` are green, and it is tempting to read
them as *"B1 is guarded, the comment is right."* They do not say that. The
guard they exercise is [`ev_rel`](../basic/expr.asm:203)'s `str_eval` probe,
which runs **at the top of an operand only** — LHS once, RHS once per relational.
It is not inside `ev_e`'s term/factor recursion. So `B=S` is intercepted and
`B=1+S` is not, and the three `l1c` rows say so: **the same variable, the same
declaration, one `1+` apart, and the answer changes from an error to `[ 1 ]`.**

Three rows agreeing was not evidence about B1; it was evidence about where the
string probe sits. *One row cannot separate two rules* —
[[one-row-cannot-separate-two-rules]]. Had the battery stopped at the top-level
shape it would have concluded B1 was dead code and left it leaking.

### 3.2 🔴 The sentinel was MASKING a live memory corruption

`l2.str.for` does not print a wrong number. It prints arbitrary RAM. Mechanism,
read off the three sites above:

1. `ex_for` guards `FOR A$=` explicitly ([`basic/program.asm:1152`](../basic/program.asm:1152),
   *measured VG-8020*) and **does not consult the DEFtbl at all**, so a
   `DEFSTR`'d bare letter walks straight past it.
2. `var_set` → `deftbl_lookup` → `A = 1` → `var_store_fac`. `1` is neither `2`
   nor `4`, so it takes the **double** coercion arm.
3. `var_alloc_or_find` is called with type `1` — and `1` **is** namespace C's
   string tag, so it finds (or creates) a real **string scalar entry**.
4. `ld c,a` with `A = 1` → `ldir` **one byte of FAC over the descriptor's `len`
   field.** The next read walks a corrupted `[len][ptr]` and PRINT dumps memory.

**The collision with `1` is what made the corruption quiet.** It kept the write
inside a legitimately-allocated entry, so the failure presented as a wrong value
rather than as a crash. Changing the constant to `3` **alone** would not fix it —
it would relocate it: `var_alloc_or_find(3)` allocates a **phantom type-3 entry**
(`elsize_from_type(3) = 3`, stride 6 — indistinguishable in size from a string
entry) that no other code in the chain understands, and `ld c,3` writes 3 bytes
into it. A different corruption, no better.

> This is the answer to *"why could this not be a free edit?"*, and it is not the
> answer the item predicted. The knife had to be aimed at the **use** of the
> constant, not at the constant.

### 3.3 What the references actually do with a `DEFSTR`'d name

* **Numeric context — always `Type mismatch`.** Unset or set, scalar or array
  element, top-level or nested. The DEFtbl default is as binding as a `$`.
* **`READ` — a genuine STRING read.** `DATA 42` gives `[42]`, not `[ 42 ]`: no
  leading/trailing space, so it is the *string* `"42"`, not the number. `DATA AB`
  gives `[AB]`. zerobas has no string `READ` at all —
  [`ex_read`](../basic/program.asm:1815) consumes one letter and calls
  `read_one_value` for an int16, with no `$` handling anywhere.

---

## 4. Proposed change

### F1 — the filed item (namespace P)

[`basic/sysvars.inc:3375`](../basic/sysvars.inc:3375): `DEFTBL_STR equ 1` → `3`,
and rewrite the note beside it (and D-REHOME's block above it) to state the
two-namespace split rather than the "0/1 sentinel" reading the measurement
refuted. All 26 published bytes then match both references in every state.
**0 ROM bytes.**

### F2 — close B2/B3 (required; this is the corruption)

`var_get`/`var_set` must not hand a namespace-P code to `var_load_fac` /
`var_store_fac`. They gain a checking wrapper that raises **ERR 13 type
mismatch** when the letter's resolved default is `DEFTBL_STR` — the same
disposition `ex_for` already applies to `FOR A$=`, and exactly what both
references do for `l2.str.for`.

`raise_error` is depth-independent (`fre_abort_low` resets `SP` from `SAVSTK` as
its first act, [`basic/interp.asm:974`](../basic/interp.asm:974)), so raising
from inside `var_set` with the caller's cursor still pushed is safe — the same
contract `ex_for`'s own `jp z,type_mismatch_error` relies on.

After F2: `l2.str.for` matches both references exactly. `l3.str.read` /
`.read.str` change from **memory corruption** to a clean deterministic ERR 13.
They stay divergent from the references' string read — that is a missing feature
(string `READ`), filed in §6, not something this slice can invent.

### F3 — close B1 (proposed; behaviour parity, 3 red rows)

One guard in [`ev_f_var`](../basic/expr.asm:543), placed after `var_name_key`
and **before** the `cp '('` dispatch to `ev_f_arr`, so it covers the scalar and
the array-element road with one check. Makes `l1c.str.nested`, `.set` and `.arr`
match both references.

F3 is **not** required for safety: with F2 in place a type-`3` code can never be
allocated into the chain, so `var_load_fac(3)` always misses and returns 0. It is
required for *parity* on three measured rows.

### 4.1 Space — the wall decides the shape

All three leak sites are in **page 1**, which has **8 B free** (low region: 23 B).
So the checks live in the **low region** and page 1 pays only for the calls
(page-1 → low is an ordinary in-slot call; low-region moves are always legal —
[[rom-region-structure-review]]):

```
; low region
deftbl_num_type:                            ; F2: B = letter -> A = NUMERIC default
                call    deftbl_lookup       ; 3
                jr      dnt_check           ; 2
check_vartype_num:                          ; F3: (VARTYPE) must not be a string code
                ld      a,(VARTYPE)         ; 3
dnt_check:
                cp      DEFTBL_STR          ; 2
                jp      z,type_mismatch_error ; 3
                ret                         ; 1
```

| | low region | page 1 |
|---|---|---|
| F1 | 0 | 0 |
| F2 | **+14 B** (the block above) | **0** — `var_get`/`var_set` retarget an existing `call` |
| F3 | 0 | **+3 B** — one `call check_vartype_num` |
| **budget** | 23 B free | 8 B free |

Both walls hold, F3 included. If the built figures disagree with this table that
is a finding, not a rounding error.

---

## 5. Gates

* **New rows go into [`probes/basic/basic_probe_float_vars.py`](../probes/basic/basic_probe_float_vars.py)** —
  the F3 typed-vars matrix, which already owns the `DEF` battery including
  `def.str.numeric_rhs`, `def.int.for.stored` and `def.int.read.stored`. The six
  red rows and their controls join it; `make float-acceptance` becomes a standing
  gate on them. The both-reference agreement recorded in §3 is the oracle-lock;
  the standing gate compares vg8020 vs zerobas, as the whole probe already does.
* **Control-inversion check (D-REHOME inverted three and missed one).** All five
  `sysvarsweep` controls re-read against this change:
  * `C-REPRO` / `C-INSTR` — `$F414` under `s1-err`. Untouched. ✅
  * `C-REPRO-2` — `$F414` under `s7-fired`. Untouched. ✅
  * `C-PRIV` — `ARYTAB $E1C0` between `s12-scal1`/`s13-scal3`, both plain
    **numeric** scalars. No DEFtbl involvement, entry sizes unchanged. ✅
  * `C-VACATED` — the five vacated addresses incl. `DEFTBL' $F153`. Nothing here
    reintroduces a writer there. ✅
  * The `s11-defstr` **evidence guard** (`[]` on screen) is the one to watch:
    it survives only because `DEFTBL_STR` is used symmetrically by
    `sub/deftype.asm`'s write and `var_str_type`'s test. Asserted by running it,
    not by this argument.
* **Full corpus** after the `basic/`/`sub/` change: `unit-test` 55/55 ·
  `lnblank-acceptance` **251/251** `--repeat 2`, allowlist **EMPTY** ·
  `array-acceptance` 149/151 (standing `ifc.instr.*`) · `arrdim-acceptance`
  73/73 · `clearpool-acceptance` 52/52 — the three load-bearing ones for a
  variable-typing change — plus `float-acceptance`, `badfnum` 93, `lof` 45,
  `diskbasic` 34/34, `bdos` 12/12, `abort` 49/49, `linemax` 60/60, the trap
  suites, `chancost`, `fat-error`, `error-trap`, and `sysvarsweep` exit 0 with
  all five controls green. Dead-code gate 0/0 both builds.

---

## 6. To file

* **zerobas has no string `READ`.** Both references read `DATA 42` into a
  `DEFSTR`'d `X` as the *string* `"42"`; `ex_read` has no `$` path at all. After
  F2 this is a clean ERR 13 instead of corruption, but it is still a divergence.
* **The two namespaces should probably become one.** The references use `3` for
  both the DEFtbl code and the chain type, which makes `elsize == type` an
  identity and `elsize_from_type` (plus ~7 call sites) deletable. That is a
  RAM-observable change to the chain's stored type byte and needs its own
  oracle-lock on that byte — a separate slice, not a ride-along on this one.
* **`ex_for`'s `$` guard and the DEFtbl default are two rules for one condition.**
  F2 closes the hole from underneath; whether the guard belongs in `ex_for`
  itself is a tidiness question left open.

---

## 7. Result

**16 of 18 rows now match both references, up from 12.** All 11 green controls
stayed green — including `l1d.str.arr.store` (`[AB]`), which is the row whose job
was to catch a fix that broke `DEFSTR` arrays while chasing the numeric leak.

| row | refs | zb before | zb after | |
|---|---|---|---|---|
| `l1c.str.nested` | Type mismatch | `[ 1 ]` | **type mismatch** | ✅ fixed |
| `l1c.str.nested.set` | Type mismatch | `[ 1 ]` | **type mismatch** | ✅ fixed |
| `l1c.str.nested.arr` | Type mismatch | `[ 1 ]` | **type mismatch** | ✅ fixed |
| `l2.str.for` | Type mismatch in 10 | `#   $  4$ ! s$ …` | **type mismatch** | ✅ fixed |
| `l3.str.read` | `[42]` | `#   $  4$ ! s$ …` | type mismatch | ⚠️ §6 |
| `l3.str.read.str` | `[AB]` | `[]` | type mismatch | ⚠️ §6 |

The two remaining rows are the **missing string `READ`** (§6). They moved from
memory corruption to a clean, deterministic ERR 13 — strictly closer, still
divergent, and **not** added as gate rows, because a row that can only ever be
red is doc debt, not a gate. They are filed instead.

### 7.1 Space — the §4.1 table was right to the byte

|  | before | after | Δ | predicted |
|---|---|---|---|---|
| page-0 low region free | 23 B | **9 B** | −14 B | −14 B |
| page-1 free | 8 B | **5 B** | −3 B | −3 B |

Relocated image 22510 B → 22510 B (the block is inside the low region's own
tail, so the image length is unchanged). ⚠️ **The low region is now at 9 B and
page 1 at 5 B** — both walls are tighter than the ROM REGION STRUCTURE REVIEW
left them, and the `input.asm` promotion work is blocked harder than before.

### 7.2 Gates

`unit-test` 55/55 · dead-code **0/0 both builds**, every allowlist entry still
verified dead · `lnblank-acceptance` **251/251** at `--repeat 2` with the
allowlist still **EMPTY** · `array-acceptance` 149/151, the two confirmed **by
name** (`ifc.instr.zero`, `ifc.instr.neg`) · `arrdim` · `clearpool` · `badfnum` ·
`lof` · `chancost` · `diskbasic` 34/34 · `bdos` 12/12 · `fat-error` 8/8 ·
`error-trap` · `abort` · `stop`/`strig`/`key`-trap · `linemax`.

`sysvarsweep` exit 0, **all five controls green** — and `s11-defstr`'s DEFTBL row
is now `SAME-VAR`, `refs …->03…` / `zb@pub …->03…`, all 26 bytes identical on
three sides in all 13 states. That is F1, measured.

A **second batch** was run beyond the standing list, because F3's guard sits in
`ev_f_var` — on *every* variable read in the interpreter — so the string and
expression suites are load-bearing for this change even though a generic `basic/`
change would not need them: `string`, `str-domain`, `input`, `missing`,
`logicops`, `math`, `intarg`, `direct-ctrl`, `error`, `width`, `binfre`, `time`,
`cursor`.

### 7.3 The gate rows were falsified by DELETING the code under test

Nine rows joined [`basic_probe_float_vars.py`](../probes/basic/basic_probe_float_vars.py)
(371 PASS). Run against the **reverted** build, exactly the four that should go
red go red — `def.str.nested`, `.nested_set`, `.nested_arr` and `def.str.fornext`
— while all six green controls stay green in **both** builds. The controls move
their own subject.

🔴 **And the first cut of `def.str.fornext` was VACUOUS.** The standing `abort`
shape is *"no span, non-empty tail"* — and the corruption this row exists to
catch produced **exactly that**: no span, and a tail that was a line of dumped
RAM (`#   $  4$ ! s$ '  9   N X]`), indistinguishable from an error message under
a `bool()` test. **The row would have passed on the broken build.** It now
requires the abort to be a *type mismatch*, matched on the lowercase stem only
(the same rule `sysvarsweep`'s `_has_error` uses) — a shape dumped RAM cannot
satisfy. Under the old test the reverted build showed 3 failures; under the new
one, 4. *A gate can be green while measuring nothing*
[[gate-can-be-green-while-measuring-nothing]] — and this one was written **in the
same slice that wrote §2's warning about non-readings**.

The probe's stored-row reader was fixed at the same time and for the same reason
(§2): every existing `stored` row still passes under it.

### 7.4 🔴 Two pre-existing failures surfaced, and NEITHER was ours

* **`float-acceptance` → `reg.C.if_skip_over_float`.**
  `IF 0 THEN A=1.5 ELSE PRINT"[";9;"]"` prints ` 9 ` on the reference and
  **nothing at all** on zerobas. Likely the standing `$0E`/`ELSE` class.
* **`logicops-acceptance` → 50 rows, all `EQV`/`IMP`**, which are a known
  unimplemented pair — but the block is headed *"CALIBRATION (implemented
  operators, ref vs zerobas must AGREE)"*, which is now false of its contents.

**Both falsified by deleting the code under test** — with `basic/` stashed and
rebuilt, the float failure is byte-identical and the logicops failures match at
50/50 `FAIL` lines exactly. Both predate this slice; both filed in TODO.md.

⚠️ The real lesson is that **two suites were already non-green and nothing said
so.** A suite expected to fail teaches nothing until the expectation is pinned BY
NAME, the way `array-acceptance`'s 149/151 is (`ifc.instr.zero`/`ifc.instr.neg`)
— the same argument the dead-code gate's allowlist rests on ([[deadcode-gate]]:
an allowlist that must keep matching is a control; one that only suppresses is
rot). Until then a corpus run cannot separate a regression from the status quo,
which cost this slice two A/B rebuilds to establish.
