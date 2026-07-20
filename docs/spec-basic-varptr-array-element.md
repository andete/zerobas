# Spec / scope — `VARPTR` of an array element  `VARPTR(A(i[,j…]))` / `VARPTR(S$(i))`

Status: **SHIPPED 2026-07-18**, **DEFECT FIXED 2026-07-20** (see §8 post-ship
note). Shipped user-signed-off and Fable-reviewed "clean" — but it shipped with
one gate case RED (`arrelem.varptr.nested`), and that red was a REAL
slice-introduced bug (missing `FACTYP=2`), not the "pre-existing, unrelated"
divergence it was logged as. The ~30-case injection battery could not see it:
every varptr case used a **literal** subscript, which masks the whole defect
class. Net **+5 B** page-1 on ship, **+3 B** more for the fix.
Gate `array-acceptance` 140→150 on ship → **151** after the fix (all green).
Charter: faithful full MSX1 BASIC ([[charter-faithful-full-msx1-basic]]).
Closes the arrays/DIM arc's first logged remaining faithfulness candidate
(the arc itself is CONCLUDED; this is a post-arc faithfulness follow-up, the
sibling of the shipped `VARPTR(A$)` fix, commit d92c3da).

Build applicability: **repack build only** (`ROM_BASE < $4000`). The lean
16 KB build has no array engine, so `VARPTR(A(0))` stays `syntax error` there
(arrays do not exist) — and its bytes stay **byte-frozen** (the lean-identity
gate). Every change below is inside `IF ROM_BASE < $4000` or is a
lean-behaviour-preserving `IF/ELSE` split.

---

## 1. The gap

Today [`ev_f_varptr`](../basic/expr.asm) parses `VARPTR(` then a variable name,
then expects `)`. A subscript `(` after the name falls through to
`jp nz,ev_f_err` → **`syntax error`**. The reference (VG-8020) instead resolves
the array element and returns its value-field address. Pre-existing for numeric
arrays; became string-visible after slice-4c unified string scalars.

## 2. Reference behaviour (VG-8020, black-box characterised 2026-07-18)

All observed via the `omsx_repl` harness against `Philips_VG_8020`; PEEK reads
the byte(s) at the returned address (no address is pinned — a moving target).

| Program | Reference output | Meaning |
|---|---|---|
| `A%(0)=513 : PRINT PEEK(VARPTR(A%(0)))` | `1` | element **value field** (513=$0201, low byte 1) |
| `PRINT VARPTR(A(0))` (A undeclared) | valid high addr, **no error** | VARPTR **auto-dims** the array to 10 (read semantics) |
| `DIM B(2,3):B(1,1)=513 : PRINT PEEK(VARPTR(B(1,1)))` | first byte of the double | multi-dim resolves correctly |
| `DIM C(2) : PRINT VARPTR(C(5))` | `Subscript out of range` | out-of-range → that error |
| `DIM D(2) : PRINT VARPTR(D(-1))` | `Illegal function call` | negative subscript → that error |
| `S$(0)="hi" : PRINT PEEK(VARPTR(S$(0)))` | `2` | address of the `[len][ptr]` **descriptor** (len byte = 2) |
| `S$(0)="hi" : PRINT PEEK(VARPTR(S$(0))+1)+256*PEEK(…+2)` | ptr into string space | descriptor's `[ptr]` field is real |
| `DIM E(3):E(0)=9:E=8 : PRINT VARPTR(E(0))<>VARPTR(E)` | `-1` | element ≠ same-named scalar |
| `PRINT VARPTR(H())` | `Syntax error` | empty subscript |

**Conclusion — the behaviour is exactly an array-*rvalue* address resolution:**
auto-dim-on-read, the same `Subscript out of range` / `Illegal function call` /
`syntax error` surface, numeric value-field vs string `[len][ptr]` descriptor
address. It is `ev_f_arr` minus the FAC load.

## 3. Design — reuse `ary_op0_resolve`

[`ev_f_arr`](../basic/arrays.asm) already resolves an element address via
[`ary_op0_resolve`](../basic/arrays.asm) (op=0 RESOLVE, auto-dim; BC=key,
A=type, HL@`(` → **Z: HL=cursor past `)`, DE=element address**; **NZ: FPERR
already mapped+set, HL=cursor**, `[CURSOR]` popped exactly once). VARPTR wants
precisely `DE` and does **not** load FAC.

In `ev_f_varptr`, after `var_name_key` (repack path), with `IX` at the char
after the name and `D` = string-ness (already computed by the shipped
`VARPTR(A$)` fix), branch on `(ix+0) == '('`:

- **array element** — set `A` = type (`D?1:VARTYPE`, reusing the existing
  selection), `HL = IX`, `call ary_op0_resolve`, `IX = HL`.
  - **Z**: `DE` = element address → `jp vptr_close` (the shared closing-`)` tail).
  - **NZ**: `ld de,0 : ret` — the `eva_deferred` convention (FPERR already the
    correct deferred error; the statement aborts at `check_expr_errors`). Do
    **not** run the `)` check (it could raise a *second*, wrong immediate
    `syntax error` and mask `Subscript out of range`).
- **scalar** — unchanged (`var_alloc_or_find`, entry+3).

`ary_op0_resolve` ($3F92) and the tail live in the low region / page-1 of the
same slot-0 ROM, both mapped in the repack build — the existing `ev_f_var →
ev_f_arr` cross-region call proves the linkage.

## 4. Byte budget — self-funding, no reclaim campaign

Free space (measured, `build/basic-reloc.sym`): **low region 3 B**
(`__MEAS_LOW_END $3FFD`), **page-1 8 B** (`__MEAS_PAGE1_END $7FF8`). The new
glue is page-1 (~16–20 B). It is funded **in place**: `vptr_none` currently
re-emits the 14-byte closing-`)` tail verbatim; deduping it **repack-only** to
`jr vptr_close` reclaims ~12 B, while an `ELSE` arm keeps the **lean bytes
identical**. Net page-1 delta ≈ +4…+8 B ≤ 8 B free. The lean build is
untouched (byte-frozen). Low region untouched.

## 5. Hazards (empirical-injection required — arc lesson: green suites + static
reasoning miss register/order bugs)

- **H1 — deferred-error trailing `)`**: the NZ path rets without consuming
  VARPTR's `)`. Verify `VARPTR(C(5))`, `VARPTR(D(-1))`, `VARPTR(H())` each
  surface the *reference* message (not a masking immediate `syntax error`) and
  that a following token in a larger expression doesn't derail the parse.
- **H2 — auto-dim side effect**: `VARPTR(A(0))` on undeclared `A` must actually
  dim `A` to 10 (observable: a later `A(10)` is in range, `A(11)` is not).
- **H3 — string descriptor address is a moving target**: after 4c a fresh
  string alloc shifts arrays. VARPTR returns the *current* descriptor address;
  the gate asserts the byte AT it *immediately* (never pins the number), per the
  `scalar.varptr.str.value` precedent.
- **H4 — register discipline**: `BC`=key must survive var_name_key →
  ary_op0_resolve; `A`=type set last; `IX` resynced from `HL` after the call
  (ary_op0_resolve clobbers IX). Inject a nested case `VARPTR(X(X(0)))` (the
  re-entrant subscript path ev_f_arr already guards).

## 6. Acceptance (differential, `basic_probe_arrays.py`; kind `value`/`err`)

New cases (zerobas == VG-8020), all repack build:

1. `arrelem.varptr.num` — `A%(0)=513`, `PEEK(VARPTR(A%(0)))` → `1`.
2. `arrelem.varptr.autodim` — undeclared, `VARPTR(A(0))<>0` resolves; then
   assert auto-dim (`A(10)` ok / `A(11)` `Subscript out of range`).
3. `arrelem.varptr.multidim` — `DIM B(2,3):B(1,1)=v`, PEEK byte matches.
4. `arrelem.varptr.oor` — `DIM C(2):VARPTR(C(5))` → `Subscript out of range`.
5. `arrelem.varptr.neg` — `DIM D(2):VARPTR(D(-1))` → `Illegal function call`.
6. `arrelem.varptr.empty` — `VARPTR(H())` → `syntax error`.
7. `arrelem.varptr.str` — `S$(0)="hi"`, `PEEK(VARPTR(S$(0)))` → `2`.
8. `arrelem.varptr.distinct` — `DIM E(3):E(0)=9:E=8`, `VARPTR(E(0))<>VARPTR(E)`
   → `-1`.
9. `arrelem.varptr.nested` — `VARPTR(X(X(0)))` re-entrancy (value/PEEK). This
   case FAILED on ship and stayed red until 2026-07-20 — see §8.
10. `arrelem.varptr.varsub` — `V=2`, `PEEK(VARPTR(X(V)))` (added 2026-07-20 with
    the §8 fix: the scalar-variable-subscript form of the same defect).
11. `arrelem.varptr.noparen` — `B=VARPTR(A(0)` (subscript consumed, no outer
    `)`) → the checked deferred `syntax error` (see the Fable follow-up below).

Gate: `make array-acceptance` (140 → **150**) green; `make string-acceptance`,
`make input-acceptance`, `make unit-test` unchanged; **lean basic.rom
byte-identical** (reloc/lean-identity gate); page-1 free 3 B (≥ 0).

### Fable review follow-up (SHIPPED, byte-neutral)

Fable's one slice-introduced divergence: `VARPTR(A(0)` (subscript consumed, no
outer `)`) now returns a silent `0` where the reference aborts — because
`vptr_close`'s `)`-reject went through the bare `ev_f_err` (ERRMARK only, which
`check_expr_errors` never reads; the pre-existing landmine also affects scalar
`VARPTR(A%`). Fixed **byte-neutrally**: in the repack build `vptr_close` rejects
through `ev_f_empty` (the CHECKED deferred `FPERR=4` syntax error, itself
repack-only), lean keeps the frozen `ev_f_err`. Strictly more faithful for BOTH
scalar and array malformed-VARPTR in repack. The other two divergences Fable
found (`FOR I=VARPTR(C(5))` — FOR doesn't call `check_expr_errors`, the logged
durable landmine; and a space before the subscript `(` — the same `ev_f_var`
no-space-skip gap the whole array surface already has) are **pre-existing
classes**, not slice-introduced — out of scope.

## 7. Non-goals

- No change to the lean build (arrays absent there).
- No change to scalar `VARPTR` (shipped) or `VARPTR(A$)` (shipped).
- INPUT# mid-statement FP-error ordering (the arc's *other* candidate) is out
  of scope — a separate slice. **Shipped 2026-07-18**, see TODO.md.

## 8. Review

Fable adversarial pass after green (arc precedent: every slice hid ≥1
matrix-invisible bug), with the H1–H4 injection battery run empirically, not
reasoned. Implementation model per [[opus-vs-sonnet-model-split]] /
[[spec-before-implementation]].

### Post-ship defect — `FACTYP` (found + fixed 2026-07-20, commits 7afc3d0 / a9de159)

The slice shipped with `arrelem.varptr.nested` **RED** (`array-acceptance`
149/150), and it stayed red across the whole D-F2-2 arc, wrongly logged there
as an unrelated pre-existing divergence. It was neither unrelated nor a
re-entrancy bug: it was introduced by THIS slice.

`ev_f_varptr` returns the address in `DE` but never asserted `FACTYP=2`. The
scalar path got that for free (`eval()` sets `FACTYP=2` on entry and nothing
between there and the return changes it), but the array-element path added
here runs a **nested `eval()`** — the subscript list — which leaves `FACTYP` as
the *subscript's* type. Consumers (`print.asm` `exp_num`, LET) then read FAC
and **ignore DE**, so `VARPTR(X(X(0)))` evaluated to `2` (=`X(0)`);
`PEEK(2)`=18 vs the reference's 67.

Fix: `call flt_int_result` in `vptr_arr`, after `ary_op0_resolve` and before
the `jr z` (LD sets no flag, CALL preserves them, so the branch still reads the
resolve's own result; DE untouched; covers the `vptr_none` fall-through).
+3 B page-1, repack-only, lean byte-identical.

**Why the ~30-case battery and the review both missed it.** Every varptr case
in the battery used a **LITERAL** subscript, and a literal leaves `FACTYP=2` —
which masks the defect completely. The one case that did not (`.nested`) was
the one that failed, and its red was rationalised as pre-existing instead of
being root-caused. Two durable lessons:

- A factor returning an int16 in `DE` must ALSO set `FACTYP=2`. `grep
  flt_int_result` is the audit tool for this; the 2026-07-20 audit found
  VARPTR was the ONLY factor missing it (PEEK/INP/VPEEK/EOF/LOF/DSKF, CVI,
  BASE, USR, LEN/ASC/VAL, INSTR and the string compares all had it).
- Exercise argument-taking functions with a **non-literal** argument. A literal
  argument is a masking value for the whole FACTYP class, so a battery built
  only from literals is structurally blind to it regardless of case count.
- A red case at ship time must be root-caused, not annotated. "Pre-existing
  and unrelated" was asserted, never verified — and was false on both counts.
