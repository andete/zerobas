<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — BASIC console `INPUT` / `LINE INPUT` (Phase-3 interactivity slice)

**Status: SHIPPED (S3, 2026-07-11).** Implemented in `basic/input.asm` per this spec;
provenance in [`basic/PROVENANCE.md`](../basic/PROVENANCE.md) ("Phase 3: console INPUT / LINE
INPUT"). Standing gate `make input-acceptance` (8 cases, reference-locked + zerobas==reference);
host cover `tests/test_input.py` (29 cases, in `unit-test` 44/44); lean `basic.rom` byte-identical.
Decisions settled at
sign-off: **D-2 faithful** (`?redo from start` on a bad numeric field or too-few values with
re-read; `?extra ignored` + continue on too-many; zerobas's own lowercase wording); handler
in a **new `basic/input.asm`** (low region) with a **standalone `make input-acceptance`**
gate (§8 Q2/Q3); D-1/D-3/D-4/D-5/D-6 accepted as recommended; **S2 implemented Opus-solo**
(not the Sonnet-5 dispatch). Same shape as the string slice specs. **Repack-only** — the lean
`basic.rom` is byte-full and frozen, so all new bytes are
gated `IF ROM_BASE < $4000` and the lean image stays byte-for-byte unchanged (pinned sha256
`e21f61fe…`). User-selected 2026-07-11 as the next Phase-3 item after the string surface was
completed: the biggest missing *interactivity* primitive — a program can compute and `PRINT`
today but cannot read a typed line (only `INKEY$`, one key).

The **file forms** already ship (Phase-2 disk/tape work, `basic/files.asm`): `INPUT #n,A$`,
`LINE INPUT #n,A$`. Both explicitly stub the console form — `ex_input`/`ex_line` do
`cp '#' / jp nz,stmt_error  ; console INPUT = Phase 3` (files.asm). This slice fills that
stub: the **console/keyboard** forms.

## 1. Goal & scope

Add keyboard `INPUT` so interactive programs work: prompt the user, read a typed line, parse
it into one or more variables (numeric via the integer parser, string raw), with the standard
re-prompt on a bad line.

**In scope:**

| Form | Meaning |
|---|---|
| `INPUT A` , `INPUT N,M` | print `? `, read a line, parse comma-separated fields into the vars (numeric fields decimal-parsed, string vars `$` take the raw field) |
| `INPUT "prompt";A` | print `prompt? ` then read (the `;` adds the `? `) |
| `INPUT "prompt",A` | print `prompt` (no `? `) then read (the `,` suppresses the `? `) |
| `LINE INPUT A$` | read a whole line into one string var — no `? `, no comma-splitting, the entire line (incl. commas/leading spaces) is the value |
| `LINE INPUT "prompt";A$` | print `prompt` then read the whole line into `A$` |
| mixed lists | `INPUT "x,y";X,Y` — numeric and string vars in one list, comma-separated fields |

**Out of scope (deferred, each its own later slice):**

- `INPUT$(n)` — the *function* that reads exactly `n` keys (a numeric-arg string function, not
  a statement; the console read differs — no echo, no Enter). Deferred (D-1); the file form
  `INPUT$(n,#f)` scaffolding already exists (`INDLR_N`).
- Numeric `INPUT#` (file form) — still Phase 3 as noted in `files.asm` (this slice is the
  *console* counterpart; numeric file input is orthogonal).
- Floats — numeric fields are parsed as **signed 16-bit integers** (the whole engine is
  integer; same integer-only stance as `VAL`, string-engine D-E). A field with a fractional
  part / out-of-range value → the re-prompt (D-2), not a float.

## 2. Existing infrastructure this reuses (verified 2026-07-11)

The console form is almost entirely *composition* of shipped routines — the reason it is a
tractable slice, not a subsystem:

| Piece | Where | Role in console INPUT |
|---|---|---|
| `read_line` | `basic/repl.asm` | keyboard → `LINEBUF` ($E100), 0-terminated ASCII, echo + Backspace/DEL editing. The console line reader, verbatim. |
| `read_into_strscr` + `ARL_GETBYTE` vector + `FCH_RDMODE` | `basic/files.asm` | the field/line splitter the file forms use (mode 0 = stop at `,`/CR, mode 1 = stop at CR). Re-point `ARL_GETBYTE` at a new `linebuf_getbyte` source and it splits the console line into fields into `STRSCR` — sharing the exact splitter, `STRMAX` clamp, and `STRSCR` descriptor with `INPUT#`. |
| `str_val_parse` | `basic/str-engine.asm` | `STRSCR`-descriptor → signed decimal int16 in DE (VAL's integer parser; currently unused — the build warns `str_val_parse is never used`). Numeric fields go through it. |
| `var_name_key` + `var_set_key` | `basic/vars.asm` | numeric var assignment (`var[key]=DE`), exactly as `ex_let`. |
| `var_str_type` + `var_name_key` + `str_set_key` | `basic/vars.asm` | string var assignment from a `STRSCR` descriptor, exactly as `ex_let_str` / the file `ex_input`. |
| `INPUT`→`$85`, `LINE`→`$AF` keyword crunch | `basic/kwtable.inc` | already tokenised (the file forms use them). **No tokeniser / kwtable change.** |
| `pchar` / `CHPUT` | print path | emit the prompt literal + the `? `. |

## 3. Mechanism

`ex_input` (console entry) and `ex_line` already sit at the dispatch and already branch on
`#` (file) vs not (console = today's stub). This slice replaces the stub `jp stmt_error` — in
the repack build only — with a console handler; the lean build keeps the `stmt_error` stub, so
the lean image is unchanged.

**Console `INPUT` (repack, in the low region):**
1. **Prompt.** After the `INPUT` token, if the next token is a string literal, print it via the
   print char sink; then read the separator — `;` → also print `? ` (a `?` and a space); `,` →
   print nothing more. No literal → print `? ` (bare `INPUT A`). Advance past the prompt.
   Remember the cursor to the **start of the variable list**.
2. **Read.** `call read_line` → `LINEBUF` holds the typed ASCII line, 0-terminated.
3. **Parse + assign.** Reset a `LINEBUF` read cursor; `ARL_GETBYTE = linebuf_getbyte`. Walk the
   variable list from the remembered start: for each var, `FCH_RDMODE = 0` (field mode, stop at
   `,`/CR), `read_into_strscr` pulls the next field into `STRSCR`; then
   - **numeric var** → `str_val_parse(STRSCR)` → DE; if the field is empty or has trailing
     non-digit junk → **re-prompt** (D-2); else `var_set_key`.
   - **string var** (`$`) → `str_set_key(STRSCR)` (the raw field bytes).
   Between vars the list separator in the *program text* is `,` (advance past it). When the var
   list ends: if the input line still has an unconsumed field → **`?Extra ignored`** behaviour
   or re-prompt (D-2 decides); if the line ran out before the vars did → **re-prompt** (D-2).
4. **Re-prompt (D-2).** On any parse/count failure, print the re-prompt message and go to
   step 2 (re-read), preserving the original prompt-less `? ` (MSX re-reads without re-printing
   the quoted prompt).

**Console `LINE INPUT` (repack):** prompt (literal only, **no** `? ` — a `;` after the prompt
is required by MSX but adds nothing); `read_line`; `FCH_RDMODE = 1` (line mode, whole line);
`read_into_strscr` → `STRSCR` → `str_set_key` into the one string var. A non-`$` var after
`LINE INPUT` → `stmt_error`.

**`linebuf_getbyte`** — the one new source vector: returns the next `LINEBUF` byte and advances
a RAM cursor; reports EOF (CF set) at the 0 terminator, so `read_into_strscr`'s existing
CR/comma/EOF logic drives the split with no change. Byte-count parity with the file source: it
must present the terminator as the same end condition `fat_io_getbyte`/`cas_in_getbyte` do.

## 4. Decisions (recommendations for sign-off)

- **D-1 — scope = `INPUT` + `LINE INPUT` console forms; defer `INPUT$(n)`.**
  *Recommend: accept.* `INPUT`/`LINE INPUT` are the interactivity primitive and share one
  mechanism; `INPUT$(n)` is a different beast (a function, unbuffered no-echo key read) and a
  clean separate slice. Keeps this slice focused.

- **D-2 — re-prompt wording + policy on a bad line.** MSX prints `?Redo from start` (bad
  numeric field or too-few values, re-reads the whole line) and `?Extra ignored` (too-many
  values, keeps the parsed ones, continues). *Recommend:* implement the **re-read** on a bad
  numeric field **and** on too-few values, with zerobas's own lowercase wording
  `?redo from start` (same own-wording convention as `type mismatch` / `syntax error`); on
  **too-many** values, print `?extra ignored` and continue (assign what matched). This matches
  MSX behaviourally with our lowercase messages. *Alt (simpler):* treat too-many as a re-prompt
  too (one message, one policy) — call it if you prefer minimal surface.

- **D-3 — prompt separator semantics faithful.** `;`→`prompt? `, `,`→`prompt` (no `?`), bare→
  `? `. *Recommend: accept* (oracle-locked in S2).

- **D-4 — reuse `read_into_strscr` via a `linebuf_getbyte` vector**, not a fresh console field
  parser. *Recommend: accept.* Shares the splitter / `STRSCR` / `STRMAX` clamp / `str_set_key`
  with `INPUT#`; the only new code is the tiny source vector + the prompt/var-list driver.

- **D-5 — repack-only, gated `IF ROM_BASE < $4000`.** *Recommend: accept (forced).* The lean
  `basic.rom` is byte-full; the console handler lives in the reclaimed low region, and the
  `ex_input`/`ex_line` stub stays `stmt_error` in lean. Lean byte-identical by construction.

- **D-6 — numeric fields are signed 16-bit integer** (reuse `str_val_parse`); a fractional or
  out-of-range field triggers the D-2 re-prompt. *Recommend: accept* (engine is integer;
  consistent with `VAL`). Revisited when floats land.

## 5. Files touched (all repack-gated)

| File | Change |
|---|---|
| `basic/files.asm` | `ex_input` / `ex_line`: replace the console `jp stmt_error` stub with a gated `jp` to the console handler (near-zero-byte page-1 hook; lean keeps `stmt_error`). |
| `basic/str-engine.asm` (or a new `basic/input.asm` in the low region) | the console handler: prompt printer, var-list driver, `linebuf_getbyte`, numeric/string per-var assign, the D-2 re-prompt loop + `?redo from start` / `?extra ignored` messages. |
| `basic/sysvars.inc` | a 1-byte `LINEBUF` read cursor for `linebuf_getbyte` (from free page-3 RAM; reuse a transient if one is dead during a read, else claim a byte). |
| `probes/basic/basic_probe_input.py` (new) | oracle-lock the console forms on the VG-8020 via typed keys (numeric/string/multi-var/LINE INPUT/prompt-separators/redo), then zerobas == reference. |
| `tests/test_input.py` (new) | host cover for the BIOS-independent parts (field split, `str_val_parse` integration, the re-prompt decision) by pre-loading `LINEBUF` and trapping CHPUT. |
| `basic/PROVENANCE.md`, this spec, `TODO.md`, memory | S3 close-out; a new "Phase 3: console INPUT" section. |

No new token. No kwtable change. Lean `basic.rom` byte-identical.

## 6. Test plan / acceptance

- **Standing gates unchanged & green:** lean byte-identical; `unit-test`; `string-acceptance`
  PASS; `diskbasic-acceptance-repack` 34/34 (the file `INPUT#`/`LINE INPUT#` path shares
  `read_into_strscr` — must stay unregressed); `repack-boot` PASS; `audit-citations` clean.
- **New `input` acceptance** (folded into `string-acceptance` as a 7th half, or a standalone
  `make input-acceptance` — S2 decides): `basic_probe_input.py` types keys via openMSX and
  differentials against the VG-8020: `INPUT A` (numeric), `INPUT A$` (string with spaces/
  commas via `LINE INPUT`), `INPUT N,M` (multi), the three prompt separators, and the
  `?redo`/`?extra` cases (assert both machines re-prompt / continue; our wording differs, same
  convention as the compare/mid-stmt divergences).
- **Probe gotcha (from memory):** type each program line as short direct-mode lines, and drive
  the INPUT *response* keys as a separate deliberate keystroke burst (the INPUT read consumes
  the keyboard — the harness must feed the response after the prompt appears, not batched with
  the program). This is the one genuinely new harness wrinkle; S2 validates it against the
  reference first (reproduce a known result before trusting the mechanism).

## 7. Session plan

- **S1 — spec + sign-off (this document). No code.** ✅ DONE (50c231f).
- **S2 — oracle + implement.** ✅ DONE (d362551). Validated the typed-response harness against
  the VG-8020 first (numeric case reproduced a known result before trusting the mechanism);
  implemented `input_console` + `linebuf_getbyte` + `input_num_field` + the D-2 loop; host tests
  (29 cases); standalone `make input-acceptance` (8 cases, differential); all gates green.
  Opus-solo per sign-off. A harness fix (`type --` in `omsx_run.py`) let a negative-number
  response type verbatim.
- **S3 — acceptance + close-out.** ✅ DONE. Standalone `make input-acceptance` gate (Q2/Q3);
  PROVENANCE "Phase 3: console INPUT / LINE INPUT"; this spec → SHIPPED; TODO + memory;
  `zerobas-main-eu.ips`/`.bps` refreshed (in S2).

## 8. Open questions for sign-off

1. **Accept D-1…D-6 as recommended?** In particular D-2 (faithful `?redo`/`?extra` with our
   lowercase wording) vs the simpler single-policy re-prompt.
2. **Acceptance home:** a 7th half of `string-acceptance`, or a new standalone
   `make input-acceptance` gate (INPUT is not string-engine, so a dedicated gate may read
   cleaner)? *Lean recommendation: a standalone `input-acceptance`* — keeps the string gate
   about strings and gives INPUT its own home as more I/O verbs land.
3. **Handler home:** extend `basic/str-engine.asm`'s low region, or start a new
   `basic/input.asm` (cleaner, since INPUT is I/O not string-engine)? *Lean recommendation: new
   `basic/input.asm`.*
4. **Model dispatch:** S2 to Sonnet-5 on the signed spec (Opus review) — confirm?
