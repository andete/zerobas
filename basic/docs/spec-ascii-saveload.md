<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec (for sign-off): ASCII program SAVE `,A` + ASCII LOAD

**Status: IMPLEMENTED 2026-07-07 (both milestones landed + gated).** Scope + design
for the two verbs zerobas Disk-BASIC used to reject, closing the gap documented in
[`../../disk/docs/spec-diskbasic-verbs.md`](../../disk/docs/spec-diskbasic-verbs.md) §7.
User-directed 2026-07-07 ("start on ASCII load and save"). **Sign-off (2026-07-07):**
(1) **disk-only** this pass, cassette ASCII a follow-on; (2) **redirect LIST's sink**
(§5) — the single-detokeniser approach approved; (3) **LOAD first, then SAVE**, each
its own commit + gate cell; (4) implement on Sonnet per [[opus-vs-sonnet-model-split]]
with the §6 oracle differential as the acceptance test.

> **As-built note (2026-07-07).** Milestone 1 (ASCII LOAD, commit 36c8734) landed as
> designed (§4). Milestone 2 (ASCII SAVE) landed with **one design refinement from §5,
> discovered during implementation**: instead of adding a *new* `LIST_OUT_VEC` sink
> vector, LIST's 17 `CHPUT` emits were routed through the **existing `pchar` sink**
> (basic/print.asm) — the redirectable emitter PRINT# already uses, selected by the
> `PRDEST` flag (0=screen, 1=open file channel). ASCII SAVE therefore reuses the proven
> PRINT#-to-file path wholesale: `disk_write_begin` (create) → `PRDEST:=1` →
> `list_walk` → Ctrl-Z → `PRDEST:=0` → `disk_write_end` (close). This honours the
> sign-off's intent ("redirect LIST's sink, one detokeniser") with **less** new code
> and no parallel redirection mechanism. Sonnet was not used: the dispatched agent died
> on a transient API error, so both milestones were implemented inline against this
> spec. Verified by the §6 CF-3300 differentials (`disk_probe_load_ascii`,
> `disk_probe_save_ascii`), the acceptance gate cells `LOAD(ASCII)`/`SAVE(ASCII)`
> (gate now 27/27), and `make unit-test` 34/34 (incl. `test_list`).

## 1. The gap (what errors today)

zerobas handles the **tokenised** program format only:

- `SAVE"A:F"` writes `$FF` (`BASIC_DISK_ID`) + the line-link image; `SAVE"A:F",A`
  (ASCII listing) is a documented `load_error` ([`../save.asm`](../save.asm) §34/§242).
- `LOAD"A:F"` / `RUN"A:F"` require the first byte to be `$FF`; `disk_prog_load`
  ([`../cload.asm:384`](../cload.asm)) rejects any non-`$FF` file (ASCII **or** BSAVE)
  with an error.
- The **only** ASCII-program path that works is `MERGE`, which reads a `SAVE",A"`-style
  line-numbered text file into the *current* program.

## 2. The ASCII program format (clean-room basis)

Public MSX-BASIC language reference (already cited by `MERGE`,
[`../files.asm:848`](../files.asm)): an ASCII-saved program is plain text —

```
<line-number decimal ASCII> <space> <detokenised statement text> CR LF
... one such record per program line ...
1A                          ; Ctrl-Z soft-EOF terminator
```

No `$FF` marker (that is exactly how `LOAD` distinguishes ASCII from tokenised). The
detokenised statement text is the **inverse of our own tokeniser** — the same
transform `LIST` already performs. So both halves are built from transforms zerobas
already owns; **no reference-ROM code is read or disassembled** — the format is the
public spec, the (de)tokeniser is our own ([[no-reference-rom-disasm]]).

Exact byte details (CR-only vs CR+LF on write; whether the trailing `$1A` is
mandatory) are **oracle-pinned** by a black-box differential (§6), not posited.

## 3. This is a bounded feature, not a "general LOAD rework"

The earlier deferral called ASCII-load "a general LOAD rework." That over-estimated
it: the machinery already exists and is reused wholesale.

| Need | Already exists | Reuse |
|---|---|---|
| detokenise program → ASCII text | `detok` + the `ex_list` line walk ([`../list.asm`](../list.asm)) | ASCII SAVE redirects its output sink |
| read ASCII text → tokenise + store | the `MERGE` reader loop `mrg_newline…mrg_storeline` ([`../files.asm:865`](../files.asm)) | ASCII LOAD reuses it after a program clear |
| clear the current program | `new_prog` ([`../program.asm:138`](../program.asm)) | ASCII LOAD calls it (LOAD replaces; MERGE keeps) |
| detect ASCII vs tokenised on load | the first-byte `$FF` gate in `disk_prog_load` ([`../cload.asm:384`](../cload.asm)) | becomes a branch, not an error |

## 4. Design — ASCII LOAD

**Detection.** In `disk_prog_load`, the first byte is already read for the `$FF`
check. Change the `nz → dpl_err` at [`../cload.asm:385`](../cload.asm) to `nz →
ascii_load` (only the BSAVE-binary case, first byte with the `$FE`/other marker, still
errors — but ASCII text never starts `$FF`, so "not `$FF`" = "ASCII program"; a stray
binary is caught by the "Direct statement in file" guard below, same as `MERGE`).

**Body (`ascii_load`).** Reuse the `MERGE` loop verbatim, with two differences:
1. **Clear first:** `call new_prog` before the read loop (LOAD replaces the program;
   MERGE inserts into it). This is the *only* behavioural difference from MERGE.
2. **Re-prime the stream:** the detection consumed byte 0. Re-open the already-found
   file (`fat_io_open` again — cheap; `disk_prog_load` just found it) so the loop reads
   from offset 0, rather than threading the pushed-back first byte through.

Refactor: extract `mrg_newline…mrg_done` into a shared `ascii_read_lines` subroutine;
`MERGE` and `ascii_load` both call it (MERGE without the `new_prog`, LOAD with).
`,R` handling is unchanged — `disk_prog_load`'s caller already runs on `,R`/`RUN"`.

**Cost:** ~1 branch edit + a `new_prog`/re-open wrapper + a mechanical extract of the
existing loop. No new parsing, no tokeniser change.

## 5. Design — ASCII SAVE (`,A`)

**Parse.** In `do_save` ([`../save.asm`](../save.asm)) after the filename, accept an
optional `,A`. Present → `ascii_save`; absent → the existing tokenised path; anything
else → `load_error` (unchanged).

**Output-sink redirect (the one real refactor).** `detok`/`ex_list` emit every
character through `call CHPUT` (17 sites in [`../list.asm`](../list.asm)). Introduce a
one-cell indirect sink:

- add `list_emit` — `jp (LIST_OUT_VEC)`-style dispatch through a RAM vector cell
  (`LIST_OUT_VEC`), default = `CHPUT`;
- replace the 17 `call CHPUT` in `list.asm` with `call list_emit` (behaviour-identical
  for `LIST`: the vector defaults to `CHPUT`, re-pointed only during an ASCII save);
- `ascii_save` sets `LIST_OUT_VEC := save_putbyte` (a wrapper over `fat_io_putbyte`),
  walks the program with the **existing `ex_list` line loop** (line number, space,
  `detok`, line terminator — all now going to disk), appends `$1A`, `fat_io_close`,
  restores the vector.

This keeps a single detokeniser feeding both screen (`LIST`) and disk (`SAVE",A"`) —
no duplicated detokenise logic.

**Cost:** the sink-vector refactor of `list.asm` (mechanical, net-zero for `LIST`) +
a `,A` parse branch + the `ascii_save` frame (open/walk/terminate/close). The file
create/write path is the proven `fat_io_create`/`putbyte`/`close` set.

## 6. Verification

- **Oracle differential (pins the byte format):** a probe that (a) `SAVE"A:F",A`s a
  known program on zerobas and on the CF-3300 and compares the produced `.bas` bytes
  (read-only FAT12 artifact oracle, [[readonly-artifact-oracle]]); (b) drops a stock
  ASCII `.bas` on a disk, `LOAD`s it on both, and compares the resulting tokenised
  program image. Byte-identity is the pass condition; it also settles the CR-vs-CRLF /
  trailing-`$1A` questions of §2.
- **Round-trip:** `SAVE"A:F",A` → `NEW` → `LOAD"A:F"` reproduces the program
  (self-check, no oracle) — the natural `.bas`-on-disk / boot-auto-run harness
  ([`../../disk/docs/diskbasic-bas-harness-spec.md`](../../disk/docs/diskbasic-bas-harness-spec.md)),
  no keyboard typing.
- **Host unit tests:** detok-to-buffer for a few statement shapes; the ASCII line
  reader (already partly covered via MERGE) — `make unit-test`.
- **Gate:** add an `ASCII-SAVE`/`ASCII-LOAD` cell to `make diskbasic-acceptance`
  (currently 23/23); update [`../../disk/docs/diskbasic-verb-coverage.md`](../../disk/docs/diskbasic-verb-coverage.md)
  and unwind the §7 scope-wall note in `spec-diskbasic-verbs.md`.

## 7. Open decisions (need sign-off before coding)

1. **Scope — disk-only, or cassette too?** Real MSX also has `SAVE"CAS:",A` /
   ASCII `CLOAD`-equivalents. *Recommend: disk-only now* (that is the flagged gap and
   the whole file-channel is proven); cassette ASCII as a tracked follow-on.
2. **The `list.asm` sink-vector refactor** — acceptable to route LIST's 17 `CHPUT`
   sites through a `list_emit` vector (behaviour-preserving for LIST)? This is the one
   change touching existing, working code. *Recommend: yes* — it is the clean-room,
   no-duplication way to share the detokeniser; the alternative (a second detokeniser
   for files) is worse.
3. **Milestone split** — land ASCII LOAD first (smaller: reuses MERGE almost wholly),
   then ASCII SAVE (the sink refactor)? *Recommend: yes*, LOAD then SAVE, each its own
   commit + gate cell.
4. **Implementation model** — per [[opus-vs-sonnet-model-split]], a signed-off spec
   like this is Sonnet-implementation work; I'd drive it with the oracle differential
   as the acceptance test. Confirm.

## 8. Non-goals

- Numeric `INPUT#`, `LOC`/`DSKI$`/`DSKO$`, `CALL SYSTEM` — unchanged, still out of
  scope (they are separate gaps, not part of ASCII save/load).
- No change to the tokenised SAVE/LOAD paths, the tokeniser, or DSKIO/FAT.
