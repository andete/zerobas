<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — Arrays slice 4a: string heap + STRMAX→255 (+ STRCAT_R absorption)

Status: **SHIPPED 2026-07-17** (commits `a6194c3` impl → `8d2cc95` root-cause fix →
`b1107ec` S1–S8 → `372b795` GC-stack-floor→DETOKBUF → `6b442a4` bugs A/B/C →
`577b81d` bug-C class sweep → `14e579c` residual log). `make array-acceptance`
**106/106** + `make string-acceptance` 6/6; lean SHA byte-identical; tenant closure
clean; 9 B low / 14 B page-1 free. Hardened across **4 Fable adversarial passes**
(they caught the root-cause HL clobber, S1–S8, a disk-work-area GC overwrite, and a
one-line interpreter hang — all invisible to the green suites; the standing arc
lesson). Final GC design as built = **shell sort (O(n^1.5)) into the idle DETOKBUF
buffer** for ≤256 roots, in-place `gc_slow` (O(n²), zero-scratch = real-MSX mode)
beyond — `GC_STACK_FLOOR` retired (see §5 as-built note). Two PRE-EXISTING value-error
message residuals logged (§11 KNOWN RESIDUAL 2), handed to a follow-up session.

Originally **SIGNED OFF 2026-07-16.** §17 resolved as recommended: (1) temp-stack
depth `D` = implementation maximizes within the freed window (≥8); (2) tenant
boundary = `heap_alloc`+GC in the sub-ROM tenant, temp-stack + `+`-chain walk
main-side; (3) GC sort — signed off as radix O(n)/transient-stack; **as-built = shell
sort into DETOKBUF** (radix's stack buffer would have trampled the disk work area —
that was one of the Fable finds); (4) `String formula too complex` added to
`fre_msgtab`; (5) 4a/4b split kept hard.

Implementation contract for the first
half of the split slice 4 (space plan
[`decision-arrays-slice4-space.md`](decision-arrays-slice4-space.md), SIGNED OFF;
`4a = string heap + STRMAX→255 + STRCAT_R`, `4b = scalar relocation`, deferred).
Per spec-before-implementation, nothing here is a green light until signed off;
Sonnet implements against this contract, then a Fable adversarial review
([[opus-vs-sonnet-model-split]]).

Repack build only (`IF ROM_BASE < $4000`). The lean 16 KB `basic.rom` stays
byte-identical (§13). Grounded on the current tree (commit `80f60d7`).

---

## 1. Goal & what changes

Replace the fixed-pool inline string store with a **compacting string heap** and
widen `STRMAX` 64→255. Today a `$`-var slot is `[name0][name1][len][bytes:64]`
(67 B inline) in the packed `$E240..$E560` window; `STRMAX=64` is the largest the
window holds, and computed strings live in an N=3 round-robin ring that silently
truncates depth. All three limits (64-byte length, 8 vars, N=3 temps) are RAM-wall
artifacts the heap removes.

| Concern | Today | After 4a |
|---|---|---|
| String value home | inline in the `$E240` fixed slot | a **body in the heap** (low RAM region); the slot holds a descriptor |
| `$`-var slot | `[name0][name1][len][bytes:STRMAX]` = 67 B | `[name0][name1][len:1][ptr:2]` = **5 B** (frees ~500 B of `$E2xx`) |
| Max length | `STRMAX=64` | **`STRMAX=255`** |
| Computed-string temps | `STRTMP` N=3 ring (truncates) | **temp-descriptor stack** (bounded by heap, not N=3) |
| Concat accumulator | global `STRCAT_R` (re-entrancy bug) | **eliminated** (§7) → STRCAT_R bug gone |
| GC | none (bump-only, silent reuse) | **O(n) compacting collector**, zero per-string overhead (§5) |

Non-goals (out of scope for 4a): numeric-scalar relocation (that is 4b — scalars
stay at `VARTAB $E1C0` untouched); any change to array *element* layout beyond what
STRMAX widening forces (§8); floats-in-VAL/STR$ or other numeric follow-ups.

## 2. Memory model — heap ⨝ array region in the low RAM span

Slices 1–3 put the array region in the low free RAM span, growing **up** from
`ARYBASE = (PRGEND)+2` (the byte after the program's `$0000` line-link terminator),
ceiling `C = min(HIMEM, TXTMAX)` where `TXTMAX = $BE00` (repack). The string heap
shares that same span, MSX-classically, growing **down from the ceiling**:

```
$8001  [ program text ][ arrays → ARYEND ][ ····· free ····· ][ FRETOP ← string heap ]  C = min(HIMEM,$BE00)
       ^PRGEND+2 = ARYBASE          ^$0000 sentinel                                     ^ ceiling
```

- **`ARYEND`** = the array region's `$0000` sentinel (existing; `ary_reset` maintains
  it). Arrays grow up toward it.
- **`FRETOP`** (new sysvar, 2 B) = the string heap's low boundary; the heap occupies
  `[FRETOP, C)` and grows **downward** as strings allocate. Reset to `C` (empty heap)
  at cold start / `NEW` / `RUN` / `CLEAR` (alongside the existing `ary_reset`).
- **The gap `[ARYEND, FRETOP)` is the shared free pool.** Two allocators draw from
  opposite ends; the collision test is the single invariant `ARYEND ≤ FRETOP`.
- **Array ceiling changes from `C` to `FRETOP`.** `ary_alloc`'s ceiling (currently
  `min(HIMEM,TXTMAX)`, `sub/arrays.asm` `aal_ceil_*`) becomes **`FRETOP`** — because
  the string heap now occupies `[FRETOP, C)`, an array may not grow past `FRETOP`.
  Initially `FRETOP == C`, so behaviour is unchanged until the first string alloc.
  A failing array alloc first triggers a string **GC** (compact the heap tight to
  `C`, maximizing the gap) and retries before raising `Out of memory` (§5.4).

Rationale for down-from-ceiling (vs a second up-growing region): it keeps the array
region's derived-base + `$0000`-sentinel walk **completely unchanged** (strings live
*above* the sentinel, never interleaved), and it mirrors the reference model
(`FRETOP`, top-down string space) so the mental model and error semantics transfer.

## 3. Descriptor format — the zero-overhead heap

A **string descriptor** stays `[len:1][ptr:2]` where `ptr` → the body's first byte in
the heap. This is a small superset of today's `[len][bytes...]` convention (the
consumer reads `len` then follows `ptr` instead of reading inline bytes) — see §10 for
the codec change. **Heap bodies carry NO header** (no length, no back-pointer): a
body is exactly `len` raw bytes. Length/location live *only* in the owning descriptor.
This is the crux of the "no extra RAM" collector (§5): zero per-string overhead, and
the fixed `$`-slot shrinks 67→5 B.

Three descriptor **homes** (the GC root set, §5.2):
- **`$`-var slot** — `STRTAB` slot becomes `[name0][name1][len:1][ptr:2]` = 5 B.
  `STRENTSZ = 5`, `STRSLOTS` unchanged (8), so `STRTAB` store = 40 B (was 536 B).
- **String array element** — `[len:1][ptr:2]` = 3 B (was `1+STRMAX` = 65 B inline).
  `elsize_from_type(1)` becomes **3**, not `1+STRMAX` (`sub/arrays.asm:943`). This
  shrinks string arrays dramatically and decouples them from STRMAX (§8, §15).
- **Temp-descriptor stack entry** — `[len:1][ptr:2]` = 3 B (§6).

A string **literal** in the token stream is described in place without a heap body
(`ptr` → the bytes in the tokenised line, `len` = literal length) — a literal is
never mutated, so it needs no heap allocation; it is only *copied* into the heap when
stored or when it becomes a concat operand (§7). `STR_EMPTY` (the shared `db 0`) still
serves the len-0 rvalue.

## 4. The heap allocator (`heap_alloc`)

A bump allocator on the downward frontier `FRETOP`, reusing the arrays allocator's
carry-checked ceiling arithmetic (the terminator-wrap fix, `sub/arrays.asm`
`aal_oom_pop1` pattern):

```
heap_alloc(len) ->  ; want `len` bytes
  new = FRETOP - len            ; carry-checked (len ≤ 255, FRETOP ≥ $8001, no wrap in practice — assert anyway)
  if new < ARYEND:              ; collision with the array region top
      GC()                      ; §5 — compact heap up to C, raising FRETOP
      new = FRETOP - len
      if new < ARYEND: return OOM   ; genuinely full → "Out of memory" (§11)
  FRETOP = new
  return new                    ; caller copies `len` bytes here, sets descriptor [len][new]
```

`len ≤ STRMAX = 255`, so a single allocation is ≤255 B. The `< ARYEND` test is the
`sbc hl,de; jr c,…` shape already proven in `ary_alloc`. No free-list, no per-block
size — freeing is implicit (a descriptor overwritten/reassigned simply abandons its
old body as garbage, reclaimed by the next GC).

## 5. The garbage collector — O(n) compaction, zero per-string overhead

**Design note (own-design improvement, documented divergence).** The reference
MS-BASIC/MSX collector is O(n²): lacking any per-string linkage, it repeatedly
rescans *all* descriptors to find the highest-address body not yet moved, once per
body — the cause of the notorious multi-second `GARBAGE COLLECTION` freeze. GC is
**unobservable** (it changes only timing, never a program's results), so
[bug-for-bug compat](bug-for-bug-compat-over-accuracy.md) does not bind it; zerobas
uses a strictly better collector. The back-pointer fix (O(n) via a 2-B/body owner
link) is rejected on the **no-extra-RAM** constraint. Instead we get O(n) by
**sorting the roots, not tagging the bodies**.

### 5.1 Algorithm

```
GC():
  roots = enumerate_live_descriptors()          ; §5.2 — addresses of live [len][ptr] descriptors
  counting_sort(roots) by descriptor.ptr, DESCENDING (highest heap addr first)
  dest = C                                       ; compact tight against the ceiling
  for d in roots (highest ptr first):
      body = d.ptr ; n = d.len
      dest = dest - n
      if dest != body: memmove_up(dest, body, n) ; overlap-safe (dest ≥ body since compacting up)
      d.ptr = dest                               ; fix the owner in place
  FRETOP = dest
```

Compacting **downward-frontier heap toward the ceiling** means processing bodies in
**descending address order**; each live body slides *up* to abut the growing
compacted block at the top. Because we move highest-first and `dest ≥ body` always,
moves never clobber an unprocessed body (overlap-safe `LDDR`-style copy). One linear
pass after the sort → **O(n)**.

### 5.2 Root enumeration (the complete live-descriptor set)

Every place a live string descriptor can sit — miss one and its body is lost/corrupted
on the next GC. Exhaustive list (the tenant walks these):
1. **`$`-var slots** — scan `STRTAB` (stride `STRENTSZ=5`), skip free (`name0=0`) and
   len-0/`ptr`-outside-heap slots (literals/empties never point into the heap).
2. **String array elements** — walk the array descriptor list (`ARYBASE`, stride =
   cached `stride`), and for each `type==1` array, iterate its elements (`3 B` stride),
   including each live element descriptor whose `ptr` is in-heap.
3. **Temp-descriptor stack** — every live entry (§6), `[$TEMPTOP, TEMPBASE)`.
4. **`STRPTR`** if it currently points at a heap body mid-expression (the operand in
   flight). GC only runs *inside* `heap_alloc`, i.e. mid string-expression, so the
   in-flight operand must be a root. Design: ensure any live intermediate is on the
   temp stack before an alloc that can GC, so (3) already covers it — **assert
   STRPTR's target is a temp-stack entry at any GC-reachable alloc** (design
   obligation for §7's concat rework; simpler than special-casing STRPTR).

A descriptor whose `ptr` is **not** inside `[FRETOP, C)` (a literal in the token
stream, `STR_EMPTY`, or `FLD_DESC $EF00`) is **not** a heap root — skipped by the
`ptr`-in-range test. (FIELD's `FLD_DESC` is already a 255-wide standalone buffer,
§8; it never lives in the heap.)

### 5.3 The sort (O(n), transient RAM only)

Counting/radix sort the root `ptr`s by address into a transient buffer **on the
hardware stack** (LIFO frame via `dec sp`, freed on return — the same
stack-frame-scratch technique `sub/arrays.asm` already uses because no fixed RAM was
claimable). Two byte-radix passes over ≤`n` 2-byte keys with a 256-entry count array =
O(n) time, ~256 B + 2·n B transient, **zero permanent cost**. (Root count `n` is
small — 8 vars + array elements + temps; for tiny `n` a plain insertion pass is fine,
but spec the radix for the string-array-heavy case that made the reference GC pause.)

### 5.4 When GC runs

- Inside `heap_alloc` on collision (§4), before declaring OOM.
- Inside `ary_alloc` on collision (before its OOM), to reclaim the gap for arrays
  (§2). Array growth benefits from string compaction; string growth does not benefit
  from array compaction (arrays are already dense), so `ary_alloc` needs no reciprocal
  trigger beyond calling `GC`.
- Never speculatively. Deterministic, only under memory pressure.

## 6. Temp-descriptor stack (replaces the `STRTMP` ring)

Computed strings (concat/function results, snapshotted operands) need a transient
descriptor whose *body* lives in the heap and whose *descriptor* is a GC root. Replace
the fixed `STRTMP` N=3 ring with a **descriptor stack**: a downward-growing array of
`[len:1][ptr:2]` (3 B) entries in a small fixed RAM window (reclaimed from the
~500 B the shrunken `STRTAB` frees — §12).

- **`TEMPBASE`** (top) / **`TEMPTOP`** (current, grows down). Depth `D` entries.
- Push a temp = reserve a 3-B descriptor slot; its body is a `heap_alloc`.
- Pop/free at statement boundaries and when a temp is *consumed* (copied into a var
  slot / array element, or appended into a result). The stack is emptied at each
  statement end (mirroring today's implicit ring reset) — temps do not survive a
  statement.
- **Overflow → `String formula too complex`** (new error, MSX-authentic — the
  reference raises exactly this when its temp-descriptor stack fills). Sizing: `D`
  chosen so realistic expressions never hit it (reference uses ~8; pick `D ≥ 8`,
  final value set in implementation against the freed-RAM budget §12). This
  **removes the N=3 depth-truncation deviation** (a genuine correctness improvement:
  `a$+f$(..)+g$(..)` two-function chains, explicitly out of scope for the old ring,
  now work).

## 7. Concat spine rework — STRCAT_R eliminated

Today `str_concat_tail` keeps the accumulator address in the single global
`STRCAT_R` and re-reads it every loop iteration; a nested string-function operand
whose argument concats overwrites the global → the
[STRCAT_R re-entrancy bug](spec-basic-string-concat-nesting-fix.md)
(`"A"+MID$("XY"+"Z",1,2)+"B"` → `XYZXYB`). The heap rework removes the global entirely:

**New concat = evaluate-all-operands-then-allocate-once:**
1. Walk the `+` chain; evaluate each operand with `str_eval_one`, pushing its
   descriptor onto the **temp-descriptor stack** (§6). A nested concat/function
   operand recurses and leaves its own result as a temp — no shared mutable accumulator
   to clobber, so the bug **cannot occur by construction**.
2. Sum the operand lengths, clamp to `STRMAX=255` (reference left-to-right truncation
   at the cap).
3. **One `heap_alloc(total)`**, then copy each operand's bytes in order into it.
   (This alloc can GC; per §5.2(4), all operands are already temp-stack roots, so
   their `ptr`s are fixed up if GC fires mid-concat.)
4. Result = a single temp descriptor; free the operand temps consumed into it.

This is the reference model (temp-descriptor stack + heap) and **folds in the deferred
STRCAT_R fix as a structural consequence** — retiring
[`spec-basic-string-concat-nesting-fix.md`](spec-basic-string-concat-nesting-fix.md).
Its four gate cases (§14) must go green.

## 8. STRMAX → 255 (the clamp-math blast radius)

`STRMAX` becomes 255. The layout constants (§3) already handle the store; the
remaining work is the **byte-compare clamp sites**, which today assume `STRMAX < 256`
and break at exactly 255 (`cp STRMAX+1` = `cp 0`; `ld a,STRMAX+1` = `ld a,0`). Each
must be rewritten to compare against 255 directly / use the length as a full byte.
Sites (from the map):
- `basic/vars.asm` `ssk_store` (`:687,689`) — LET store clamp → now clamps the
  *descriptor+heap-copy* path (§10), not an inline slot.
- `sub/arrays.asm` `aeng_copy_str` (`:273,275`) + `elsize_from_type` (`:411`, → 3).
- `basic/str-engine.asm` `str_copy_desc`/`str_append_desc` (`:57,85`), `SPACE$`
  (`:990`), `STRING$` (`:1067`), INSTR (`:1243`) — length/room arithmetic at 255.
- `basic/strvar.asm` literal lift (`:104`), INPUT$ (`:248`).
- `basic/files.asm` `read_into_strscr` (`:825`).
- **`str_min_bc` / SPACE$ / STRING$ boundary math** (`str-engine.asm`) — the
  "count ≥ 256 → clamp" reasoning must be re-derived for the 255 boundary.

**`STRSCR`** (literal/INPUT/MKI$ scratch) grows `1+STRMAX` = 256 B; it moves into the
freed `$E2xx` window (§12). **`FLD_DESC $EF00` is already 255-wide** — no change.

**Input-length caveat (documented, not fixed here):** `LINEMAX=96` bounds a *typed*
line, so a 255-char string literal can't be entered directly; STRMAX>96 benefits only
*computed* strings (concat, `STRING$`, `SPACE$`, file reads). Widening `LINEBUF` is a
separate concern — **out of scope for 4a**, noted in the spec's deviations.

## 9. The sub-ROM tenant cut (shape C, page-0 pure-RAM leaf)

Per the space plan, the mechanism (pointer/memory work) is a **new page-0 pure-RAM
sub-ROM tenant** (`SUBROM_IDX_STRHEAP = 5`, append-only); the eval-adjacent glue stays
main-side (§10). The tenant handles **`heap_alloc` + GC (enumerate/sort/compact)** —
all pure-RAM (reads `FRETOP`/`ARYEND`/`ARYBASE`/`STRTAB`/temp-stack in RAM pages 2/3,
always mapped; `call`s nothing outside its own file → passes the §3f leaf-audit by
construction, like `sub/arrays.asm`).

- **Entry:** append `jp strheap_engine` at page-0 table index 5 (`sub/sub.asm`);
  `SUBROM_IDX_STRHEAP equ 5` (`sub/equates.inc`, never renumber existing).
- **Param block:** a new `SH_*` block (op / len / result-ptr / err). RAM is scarce —
  **claim it from the ~500 B the shrunken `STRTAB` frees** (§12), not the full
  `$E028`/`$E2xx` windows. Ops: `SH_OP_ALLOC` (len→ptr or OOM), `SH_OP_GC`
  (compact; returns new FRETOP). Root enumeration reads the tables directly.
- **Glue wrapper** mirrors `ary_engine_call`: set `IX = $0010 + 3*5`, `call
  subrom_call`, `jp c,subrom_absent_error`, read `SH_ERR` → map to `Out of memory`.
- **Closure:** self-contained (no resident-ABI seed needed for a page-0 leaf).

Open sub-decision (§17 Q-2): whether the concat/temp-stack *bookkeeping* also moves
into the tenant or stays main-side calling it per-alloc. Lean: temp-stack push/pop and
the `+`-chain walk stay **main-side** (they touch `eval`/the token cursor — page-1
services); only `heap_alloc`/`GC` are the tenant. This matches the arrays split
(parse/eval main, pure-RAM engine sub).

## 10. Main-side glue (the codec change)

- **`str_get_key`** (`vars.asm`): today returns `HL=entry+2` (zero-copy inline
  descriptor). Now the slot *is* a `[len][ptr]` descriptor already — return a pointer
  to it (still zero-copy: the descriptor, not the body). Consumers that read bytes
  follow `ptr`. `STR_EMPTY` on miss unchanged.
- **`str_set_key`** (`vars.asm` `ssk_store`): the LET store. Now: `heap_alloc(len)`
  (clamped 255), copy the source bytes into the heap, write `[len][heapptr]` into the
  slot. **Value-copy semantics preserved** (a fresh body per store; `A$=B$` copies
  bytes, no aliasing). The old body (if the slot was occupied) becomes garbage. The
  three duplicated clamped-LDIR bodies (`ssk_store`, `aeng_copy_str`, FIELD/INPUT)
  converge on "alloc + copy to heap".
- **`str_eval` / `str_eval_one`**: return an rvalue descriptor whose body may be in the
  heap (temp), the token stream (literal), a var slot (via get_key), or `FLD_DESC`.
  The temp-stack discipline (§6/§7) replaces the ring.
- **String array element load/store** (`basic/arrays.asm` glue): element is now a
  `[len][ptr]` descriptor → load returns it (follow ptr); store = `heap_alloc` + copy
  + write descriptor (value semantics preserved, as today).

## 11. Error surface

| Condition | Error | Raise point | Notes |
|---|---|---|---|
| Heap + array collision after GC | **`Out of memory`** | glue maps `SH_ERR` (§9) | same wording/disposition as arrays OOM; the existing `fre_msgtab` entry |
| Temp-descriptor stack overflow | **`String formula too complex`** | main-side temp push (§6) | **new** message; MSX-authentic; add to `fre_msgtab` |
| String longer than 255 | (no error) truncate to 255 | clamp sites (§8) | reference left-to-right truncation at the cap |

Placement discipline (phase-3 §8d): the tenant is page-0 pure-RAM leaf; the glue and
error raises are page-1/low-region main-side. Errors surface via the existing
`stmt_error`/FPERR path; the same "stored-RUN doesn't abort on runtime error" landmine
applies → **gate error cases in DIRECT mode** (the standing arrays-arc rule).

**KNOWN RESIDUAL (Fable 2026-07-17, deferred — same family as the empty-expr /
`check_expr_errors` landmine):** `str_concat_tail`'s mid-chain OOM/overflow exit
(`sct_append_err`, str-engine.asm) sets `FPERR` (`Out of memory` / `String formula
too complex`) and returns CF set with the result = the partial accumulator, but it
leaves the *remaining* `+ operand …` terms UNCONSUMED in the token stream. A driver
that checks `FPERR` right after `str_eval` (PRINT / LET / IF) raises the correct OOM
message and never sees the leftover. A driver that does NOT check `FPERR` would hit
the stray `+` and raise a spurious `syntax error` instead. Not fixed here: consuming
the tail correctly means skipping tokens to the statement boundary (fragile, and the
low region + page 1 are byte-full). All current string-value drivers do check `FPERR`,
so it is latent. Fix when a non-checking string driver is added, or when a token-skip
helper already exists to reuse.

**KNOWN RESIDUAL 2 (Fable pass 4, 2026-07-17 — PRE-EXISTING `ev_f_err`-silent-0 family,
NOT a slice-4a regression):** a few malformed-input edge cases raise the deferred error
via the bare `ev_f_err` path (sets `ERRMARK` only, not `FPERR`), so the numeric driver
prints a silent ` 0` instead of surfacing the error. Two were swept to `ev_f_empty`
(deferred `FPERR=4` syntax) during the pass-4 fixes — the STRING$/LEFT$/MID$/CVI-`(`
cases; `PRINT CVI` now → `syntax error` (ref = `Syntax error`). **Two remain, because
they need a non-syntax deferral the sweep pattern doesn't produce.** A 21-case malformed-
input **hang battery confirms NO remaining hangs / no corruption** — the severe
(slice-4a-introduced, garbage-IX-spin) members are all closed; what's left is only a
*wrong error message* on two value-error edge cases, both pre-existing (`ev_f_err`
sets `ERRMARK` only, no `FPERR`, since before slice-4a) and both a silent ` 0` where the
reference raises **`Illegal function call`**: (1) `INSTR(0,…)` / negative-p (str-engine.asm
`efi_p_nonneg`/`efi_p_ok`, the `p<1` exits ~:1256/:1263); (2) `ASC("")` (str-engine.asm
~:517, `jp z,ev_f_err`).

**FIXED 2026-07-17 (follow-up session).** Added `ev_f_ifc` (expr.asm, repack-gated) — a
deferred **`FPERR=3`** ("illegal function call") sibling of `ev_f_empty`, sharing its
first-error-wins tail via a dead code-carrier register (E, which `ev_f_err` zeroes), so
**+5 bytes page-1 only, low region untouched**. Routed the three exits above through it.
`FPERR=3` (house-lowercase, `fre_msgtab` entry 3) chosen over the arrays' capitalised
`FPERR=8` because these are function-domain value errors exactly like `SQR(x<0)`/`LOG` —
so `INSTR(0,…)`/`ASC("")` → `illegal function call`, matching the reference disposition
with the standing house-lowercase convention. Gate cases `ifc.instr.zero/neg`, `ifc.asc.empty`
+ regression guards `ifc.instr.ok/ok2`, `ifc.asc.ok`.

**LEN(5) FIXED 2026-07-17 (same follow-up session).** A string function given a
NUMERIC arg (`LEN(5)`/`ASC(5)`/`VAL(5)`) now raises **`type mismatch`** (ref
`Type mismatch`), was a wrong `syntax error`. `ev_str_arg`'s non-string exit routes to a
new **`ev_f_tmm`** (deferred **`FPERR=10`** → `err_type_mismatch`, a new `fre_msgtab`
entry pointing at the existing house-lowercase string; +6 B page-1, reuses the
`ev_f_defer` first-error-wins tail). First-error-wins **splits** the two NC causes:
a genuinely-numeric arg → type mismatch, a *nested malformed* string fn
(`LEN(LEFT$("AB"))`) → **stays** `syntax error` — the latter enabled by routing the
18 structural `str_fn_*` missing-delimiter exits (`cp '('/','/')' ; jp nz,str_eval_no`)
through `str_arg_empty` (0-byte retargets; direct-mode behaviour unchanged by
first-error-wins, only the nested leak corrected). The negative-n value exit
(str-engine.asm ~:1043, `bit 7,d`) was deliberately NOT retargeted. Gates `tmm.len/asc/val.num`
→ type mismatch, `tmm.len/rt.nested.syn` → syntax error, `tmm.len.chr/str.ok` value guards.
**All KNOWN RESIDUAL 2 items now resolved.** Final: array-acceptance **119/119**, string 6/6,
lean SHA held, closure clean, 9 B low / 3 B page-1 free.

## 12. RAM budget

Net RAM effect is **positive** (the point of "no extra RAM cost"):

| Item | Was | Now | Δ |
|---|---|---|---|
| `STRTAB` store (8 slots) | 536 B (8×67) | **40 B** (8×5) | **+496 B freed** |
| `STRSCR` scratch | 65 B | 256 B (`1+255`) | −191 B (moves into freed window) |
| `STRTMP` ring | 195 B | replaced by temp stack (`D`×3 B, ~24–48 B) | +~150 B freed |
| `STRCAT_R`/`STRTMP_IDX` | 3 B | 0 (eliminated) | +3 B freed |
| New: `FRETOP` | — | 2 B | −2 B |
| New: `SH_*` param block + temp stack | — | ~30–60 B | from the freed window |
| Heap bodies | inline in slots | in the low RAM region `[FRETOP,C)` | (no fixed-window cost; shares the arrays span) |
| GC sort buffer | — | ~256 B **transient on stack** | zero permanent |

The shrunken `STRTAB` frees ~500 B of the `$E240..$E560` window, which absorbs the
widened `STRSCR`, the new param/temp-stack RAM, and `FRETOP` — **no new fixed RAM
claimed past the current `$E560` wall**. Confirm the exact repacked window layout in
implementation; the freed space must cover the widened scratch + new blocks (it does
by the table above, with margin).

## 13. Lean build

`STRMAX=32`, fixed pool, no concat, no heap — **unchanged, byte-identical**. Every 4a
addition is inside `IF ROM_BASE < $4000`. The lean `str_eval ≡ str_eval_one`
(`strvar.asm:42`) path is untouched. Verify with the lean-identical SHA check.

## 14. Gate plan

- **Differential** (VG-8020 reference vs repack, `probes/lib/omsx_repl.py`): extend
  `probes/basic/basic_probe_string.py`. New/again cases:
  - The four **STRCAT_R** cases (`concat.fn-mid/last/var/rt`, §7) red→green.
  - **STRMAX→255**: `STRING$(255,"A")`, `SPACE$(255)`, concat past 255 (clamp), a
    200-char computed string round-tripped through a var and PRINTed.
  - **N=3 removal**: `a$+f$(x$+y$)+g$(p$+q$)` (two-function chain) now correct.
  - String-array element with a >64-char value (heap-backed, decoupled from STRMAX).
- **GC stress** (the reason for the better collector): allocate/reassign many strings
  (loop building/discarding strings; a string array churned in a `FOR`) to force
  repeated GC; assert results correct after compaction and no corruption of live vars/
  array elements/temps. Include a case that forces GC **mid-concat** (long operands
  that collide during step 3) to exercise §5.2(4).
- **Array coexistence**: interleave `DIM` growth and string allocation to exercise the
  shared gap + the `ary_alloc`→GC→retry path (§5.4).
- **Adversarial battery + Fable review** (the standing arc lesson — every slice hid
  ≥1 matrix-invisible bug): variable/nested/self-referential string exprs, GC root
  completeness (esp. array elements + in-flight operand), the 255 boundary math.
- Standing gates: `check_tenant_closure` (leaf), `__MEAS_LOW_END`/`__MEAS_PAGE1_END`
  re-measure (prove the shape-C split nets neutral-to-positive on the main ROM),
  lean byte-identity, full `make string-acceptance` + `make array-acceptance`.

## 15. 4a ↔ 4b boundary

4a keeps **numeric scalars** at the fixed `VARTAB $E1C0` pool (typed-var chain from
F3) — untouched. Only the **string** subsystem relocates to the heap. String array
*elements* become `[len][ptr]` descriptors (3 B) here, so string arrays fully join the
heap in 4a. 4b (later) relocates numeric scalars into the contiguous
`VARTAB→ARYTAB` chain — independent of the string heap, lower payoff, mechanically
simpler.

## 16. Provenance

Clean-room. The compacting heap, the O(n) sorted-root compaction, the temp-descriptor
stack, and the `[len][ptr]` descriptor are zerobas's **own design** — the collector is
a **documented deliberate improvement** over the reference's O(n²) GC (§5, permissible
because GC is unobservable; note in `basic/PROVENANCE.md`). The MSX-faithful *contracts*
kept: string space top-down from a `FRETOP`-style boundary, `Out of memory` / `String
formula too complex` errors, left-to-right truncation at the length cap. No disassembly.

## 17. Open questions for sign-off

1. **Temp-stack depth `D`** — set from the freed-RAM budget (§12); recommend `D` in
   the 8–16 range (≥ reference's ~8, removing the N=3 truncation). Any preference, or
   leave it to the implementation to maximize within the freed window?
2. **Tenant boundary (§9)** — confirm: `heap_alloc` + `GC` in the sub-ROM tenant;
   temp-stack bookkeeping + `+`-chain walk stay main-side (matches the arrays split).
   Or push more into the tenant?
3. **GC sort** — radix (O(n), 256 B transient) as specced, or an insertion pass
   (O(n²)-compares but zero buffer) given real `n` is small? Recommend radix (it's the
   whole point of beating the weak collector); confirm the transient-stack buffer is
   acceptable (it is zero *permanent* RAM).
4. **`String formula too complex`** as the temp-overflow error — confirm adding this
   new (MSX-authentic) message to `fre_msgtab`.
5. Anything to fold from 4b forward, or keep the string/scalar split hard?
