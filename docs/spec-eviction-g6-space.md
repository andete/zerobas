# Spec — Eviction slice (G6 space): `DEFtype` → page-0 sub tenant

The third space carve of the graphics arc (after the G4 `fat_rand_*`/line-editor
pair and the G5 cassette name-match), funding `DRAW`'s resident half
([spec-basic-graphics-g6.md](spec-basic-graphics-g6.md) §8).

Unlike its predecessors this one was **found by a tool, not by inspection**, and
it is the first carve to use **page-0** tenancy.

## 1. The rule this carve is built on

The two sub-ROM tenancies have **complementary reach**, because `CALSLT`
switches only the page it targets:

| | BIOS | page-0 low region (float pack) | page-1 residents |
|---|---|---|---|
| **page-1 tenant** | ✅ | ✅ | ❌ |
| **page-0 tenant** | ❌ | ❌ | ✅ |

A carve is clean iff its **transitive** callee closure lands on one side. The
transitivity is the trap: `eval` is page-1 resident, so a page-0 tenant may call
it — but `eval` itself calls the float pack at `$34xx`, which *is* page 0 and is
the sub-ROM while the tenant runs. Judged on direct callees alone, half the
interpreter looks page-0-carvable; judged transitively, almost none of it is.

`scratchpad/g6_carve_scout.py` applies exactly this rule to every resident
routine (closure, size, and how many labels outside the carve call into it), so
the search is a shortlist to read rather than a file to eyeball.

## 2. Why the previously-scouted runway failed

`do_tape_prog`/`ctp_*` (224 B), banked as the G6 runway, fits **neither**
tenancy: six of its callees (`load_error`, `cas_open_match`, `cas_put`,
`verify_error`, `cas_ascii_load`, `new_prog`, `relink`) are page-1 residents,
which rules out page-1 tenancy, and it calls BIOS `TAPION`/`TAPIN`/`TAPIOF`,
which rules out page-0. Recorded here because the estimate that named it had
been carried across two slices without being checked.

## 3. Target (verified)

**`ex_def_type`** — `DEFINT` / `DEFSNG` / `DEFDBL` / `DEFSTR`
([basic/usr.asm](../basic/usr.asm) → [sub/deftype.asm](../sub/deftype.asm)),
tenant index `SUBROM_IDX_DEFTYPE = 9` in the **page-0** table.

Why it is clean:

- **Closure never touches page 0.** The body is a mnemonic parse plus a `DEFTBL`
  fill: no `eval`, no float work, no BIOS. Its only helpers are `skip_spaces`,
  `is_letter`, `upcase` — `upcase` and `is_letter` already exist in this page of
  the sub-ROM and are reused; `skip_spaces` (5 instructions) is duplicated
  sub-locally, the same choice the G5 carve made for `cal_refill`.
- **Single entry.** Only the `DEF` dispatch reaches it.
- **Cold path.** A declaration, run once at the top of a program — the `CALSLT`
  round trip is invisible.
- **Repack-only already** (`IF ROM_BASE < $4000`), so the lean 16 KB cart never
  had this code and stays byte-identical **by construction** — no `-body.inc`
  dance, unlike the cassette carve.

## 4. ABI

The token cursor travels in RAM (`CALSLT` clobbers the registers):

| cell | direction |
|---|---|
| `DEFT_PTR` (`$E54F`) | resident → tenant, and back with the cursor advanced |
| `DEFT_STATUS` (= `DISKOP_STATUS`) | tenant → resident: 0 ok / 1 = raise `stmt_error` |

`DEFT_PTR` lives in the repack-only graphics window above `DRAW`'s cells: a
`DEFtype` statement and a graphics statement can never be in flight at once, the
same one-statement-at-a-time aliasing `LE_*`/`CM_*` already use against
`DISKOP_*`. It is defined **beside the graphics cells** rather than beside its
`SUBROM_IDX_*` equate, because that block sits inside `IFNDEF
SUBROM_ENTRY_BASE_P0` — which the sub-ROM build skips, and the tenant needs the
address. (That cost one build failure to discover.)

The body moved **verbatim** bar three edits: the cursor arrives/leaves through
`DEFT_PTR`, `jp stmt_error` becomes a status the stub raises, and `jp exec_stmt`
becomes a `ret`. Nothing about the language changed.

## 5. Net bytes

The carve, plus the two DRY levers G5 wrote and had to revert (`gfx_eval_int16`
at six sites, `gfx_store_colour_checked` at `circ_c`, 46 B) and the D-G6-1b
co-routine rewrite (124 B), took the page-1 image from a **239 B overrun** to
**45 B free with `DRAW` resident** — more headroom than the arc had *before* G6
started, which matters because G7 (sprites) is next.

## 6. Verification

- `make graphics-acceptance` **PASS** — all phases, including the new G6
  Phases K/L/M (pixel differential, the 25-case error surface, the
  across-`RUN` persistence).
- `make unit-test` 51/51, including the new `gdrw_scale`/`gdrw_rotate` leaves.
- `make diskbasic-acceptance` 34/34, `make bdos-acceptance`.
- Lean cart **byte-identical** to its frozen baseline; `check_reloc.py` clean.
- Makefile `SUB_PARTS` updated — the stale-tenant trap that has bitten before.
- The carve's own behaviour is covered by the smoke fixture in
  `scratchpad/g6_smoke.py` (`DEFSTR`/`DEFINT` still take effect) and by every
  existing suite that declares typed variables.
