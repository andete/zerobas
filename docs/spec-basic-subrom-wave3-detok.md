<!-- Provenance: original work (own-design spec over our own detokeniser + the ratified sub-ROM ABI). -->
# Spec — sub-ROM eviction WAVE 3: the detokeniser core

**🏁 Status: SHIPPED 2026-07-11.** Investigation, sign-off (Q3-a), and implementation
all complete; all 6 gates green (§7). The detokeniser core is evicted to sub-ROM
page 0 (`sub/detok.asm` + the shared `basic/detok.inc`), the resident `kwtable` is
DROPPED (sub copy sole, 626 B), page-1 free grew 704 B → **1354 B** and low-region
to 1348 B. Cross-refs: shared body [`basic/detok.inc`](../basic/detok.inc), resident
stub [`basic/list.asm`](../basic/list.asm), sub tenant [`sub/detok.asm`](../sub/detok.asm),
dispatch [`basic/subromcall.asm`](../basic/subromcall.asm), tokeniser eviction
[`basic/tokenise.inc`](../basic/tokenise.inc).

---

## 0. Investigation results (2026-07-11) — the two open forks, resolved

The §3 audit (Q2) and the §5 buffer bound (Q1) were the two things blocking sign-off.
Both are now settled from the actual source; only Q3 (buffer home) remains.

> **Implementation note (2026-07-11).** The forward audit below was necessary but
> not sufficient: two *reverse* deps also had to move-or-stay. `ln_div_entry`
> (program.asm's error line-number print), `hex_digit` and `oct_digit`
> (str-engine.asm's HEX$/OCT$, which reimplement the nibble/group loop but reuse the
> digit leaves) all have RESIDENT consumers, so they are kept as resident copies in
> the repack `list.asm` stub block while the sub-side gets byte-identical twins via
> the shared include. Same class of trap as wave-1's `neg_de` — run the reverse
> leaf-audit (who calls INTO the evicted body), not just the forward one.

### 0.1 Q2 — the leaf-audit: the core is a CLEAN LIFT (no BIOS in any `dt_*`)

The full call-graph of the detok region ([`list.asm:245-611`](../basic/list.asm:245))
resolves to exactly **three** symbols defined *outside* `list.asm`:

| symbol | defined in | role | disposition |
|---|---|---|---|
| `pchar` | [`print.asm:421`](../basic/print.asm:421) | the I/O sink (CHPUT / fat_io_putbyte / LPTOUT / cas_wbyte) | **STAYS RESIDENT** — this is the drain |
| `print_string` | [`repl.asm`](../basic/repl.asm) | a 0-terminated-buffer→`pchar` loop | resident; the number renderers stop calling it (see §0.3) |
| `div10` | [`print.asm:332`](../basic/print.asm:332) | HL/=10, shift-and-subtract — **pure compute, no BIOS** | **clone sub-side** (the `neg_de`/`upcase` pattern) |

Everything else (`dt_*`, `detok_*`, `dop_*`, `dk_*`/`dk2_*`, `dh_*`, `do_*`,
`hex_digit`, `oct_digit`, `ln_div_entry`, `de_shift3`) is **local to `list.asm` and
pure compute**. **No `dt_*` path touches the BIOS** — every emit routes through
`pchar`, and the only external compute leaf is `div10`. So R-W3-2 (a renderer needs
the BIOS) is **discharged**: the core is a clean lift plus one `div10` clone.

### 0.2 Q1 — worst-case output bound: ≤475 B → the fork collapses to design A

The sketch (§5) feared a 255-char source line → ~767 B output. **The source line is
capped at 96 bytes, not 255**: `LINEMAX equ 96`, `LINEBUF` is one page `$E100..$E15F`
([`sysvars.inc:317`](../basic/sysvars.inc:317)), and **both** program-line entry
paths bound to it — `read_line` ([`repl.asm`](../basic/repl.asm), Enter guard at
`LINEBUF+LINEMAX-1`) and `ascii_read_lines` ([`files.asm:1579`](../basic/files.asm:1579),
same guard, covering MERGE / ASCII-LOAD / CLOAD). So every stored line LIST can
encounter came from **≤95 source chars**.

The **only** source-expanding token is `?`→`PRINT` (1 char → 5;
[`tokenise.inc:416`](../basic/tokenise.inc:416)) — all keywords are typed in full,
so they render at their typed length; numbers render at their typed length. Bounds:

- **Realistic worst case** — densest valid `?:?:…?` in 95 chars = 48 `?` + 47 `:` →
  `48×5 + 47 = 287` chars.
- **Absolute ceiling** — every char a `?`→PRINT (5× per char) = `95×5 = 475` chars.

A **512 B one-shot buffer** covers the 475 ceiling with margin. That is trivial RAM,
so **design B (bounded resumable chunked core) is unnecessary** and **risk R-W3-1
(resumable-state ABI) is eliminated**. Wave 3 is design **A**: one `CALSLT` per line,
whole line detokenised into a ≤512 B buffer, drained once.

### 0.3 Consequence for the number renderers — near-zero reshape

`detok_dec` / `detok_hex16` / `detok_oct16` already build their **full** text into
`NUMBUF` and only touch I/O via a terminal `jp print_string`
([`list.asm:326`](../basic/list.asm:326), `:345`, `:400`). Reshaping them = replace
that terminal drain with a **`NUMBUF`→`DETOKBUF` append**. They are already
buffer-shaped; only `dt_*`/`detok_op`/`detok_kw*`'s direct `pchar` calls become
`DETOKBUF` appends.

## 1. Proposal

Split the LIST/ASCII-SAVE **detokeniser** into a **pure-compute core** (token → text
into a RAM buffer, sub-side) and a **thin resident drain** (buffer → `pchar`/
`PRDEST`). This is the detok counterpart of wave 2's tokeniser eviction — but where
the tokeniser was pure by nature (its output is already a RAM buffer), detok is a
*stream* and must be reshaped to qualify.

## 2. Why it's worth the refactor (the `kwtable` payoff)

`kwtable`'s only two code readers are `match_kw` (tokenise) and `detok_kw`/
`detok_kw2` (LIST — [`list.asm:495`](../basic/list.asm:495),
[`list.asm:555`](../basic/list.asm:555)). Wave 2 sends the first sub-side, leaving
**two** copies (resident + sub). Wave 3 sends the second sub-side too, so:

- **Both readers are sub-side → drop the resident `kwtable`** — recovers wave-2's
  duplication *and* frees its page-0 low-region bytes.
- **Frees the detok-core code from page 1** (the byte-full wall — `list.asm` is a
  page-1 include, [`main.asm:188`](../basic/main.asm:188)).
- One shared table, one source of truth (the drift risk R-W2-3 disappears).

The core is also cold (LIST/SAVE are peripheral verbs), so the DI span is cosmetic,
same as wave 2.

## 3. The split — what moves, what stays

**Stays resident (the drain + all I/O):** the `PRDEST` sink and every `pchar` call.
LIST→screen (`PRDEST=0`) and ASCII SAVE→disk channel (`PRDEST=1`) both keep full
BIOS/disk access — **the I/O never moves**, only the token→text *mapping* compute
does. The resident side becomes: set up walk → loop { `CALSLT` core to fill a buffer
→ drain buffer to `pchar` } → done.

**Moves sub-side (the core):** the token-walk (`dt_lp` + all `dt_*` states),
`detok_op`, `detok_kw`/`detok_kw2`, and the number renderers (`dt_byte`/`dt_word`/
`dt_hex`/`dt_oct`/`dt_lineno`/`dt_digit`) — each rewritten to write into the buffer
instead of calling `pchar`. Plus the sub-side `kwtable` (shared with wave-2's
tokeniser) and leaf clones (`upcase` etc., already present from wave 2).

**Named pre-gate audit:** confirm **no `dt_*` path needs the BIOS** — especially the
number renderers. If any calls a resident/BIOS number-format routine, that call must
be a pure-compute clone sub-side (the wave-2 `neg_de` trap, re-applied). detok's
lookahead states (`dt_colon`→`:'`/`:ELSE`, `dt_func` `$FF`, `dt_rem`/`dt_data`
verbatim tails) must all be pure buffer writes.

## 4. Reused mechanism

Dispatch (D-5), absence path, the separate-machine RAM-shuttle test bridge, and the
`kwtable` byte-identity discipline all exist from waves 1–2. New: the buffer ABI (§5)
and one drain-loop stub site (the LIST/SAVE caller). Buffer lives in page-2/3 RAM,
below the stack (same discipline as [[tape-realtime-read-buffering]]), byte-address-
identical sub/main via `sysvars.inc`.

## 5. Buffer sizing — RESOLVED: design A, ≤512 B (see §0.2)

The sketch's fork assumed a 255-char source line (→ ~767 B); the real cap is 96
(§0.2), so the worst-case output is **≤475 B** (realistic ~287). Design **A** —
one-shot whole-line buffer, one `CALSLT` per line — is adopted:

- **(A) ADOPTED.** A **512 B `DETOKBUF`** in RAM, byte-address-identical sub/main via
  `sysvars.inc`, below the stack. The core does a straight-through walk into it; the
  resident side drains it once (LIST→screen or ASCII-SAVE→channel, per `PRDEST`). No
  resumable state, natural walk, one `CALSLT`/line.
- **(B) REJECTED.** Its only justification was an unaffordable worst-case buffer;
  512 B is trivial. Dropping B eliminates its save/restore-walk-state ABI (R-W3-1).

**Q3 (the one open sign-off item) — where the 512 B `DETOKBUF` lives.** It must be
free during *both* LIST→screen and ASCII-SAVE→disk, not collide with the stored
program (which LIST reads) or the disk sector buffers (which ASCII-SAVE writes), and
be a fixed `equ` (repack-only). Candidates:

- **(Q3-a) RECOMMENDED — reserve the top 512 B of the program-text region:** lower
  `TXTMAX` from `$C000` to `$BE00` in the repack build, `DETOKBUF equ $BE00`. Clean:
  a fixed address, free in both sinks (it is neither program text nor a disk buffer),
  below the stack, byte-identical trivially. Cost: repack program capacity −512 B
  (~3% of the ~16 KB text area) → a documented divergence; the `OUT OF MEMORY`
  threshold moves down 512 B in the repack build only.
- **(Q3-b) Dedicated page-3 free window** (e.g. inside `$C000..$DFFF` BLOAD region):
  rejected — BLOADed ML routines persist there; not reliably free.
- **(Q3-c) Reuse the idle FAT sector buffers** (`FSECTOR_BUF`, page `$E5+`, two
  512 B): free during LIST but **in use during ASCII-SAVE** — fails R-W3-4, rejected.

## 6. Risks

- ~~**R-W3-1** — resumable-state ABI~~ **ELIMINATED** (design B dropped, §5).
- ~~**R-W3-2** — a `dt_*` renderer needs the BIOS~~ **DISCHARGED** by the §0.1 audit
  (only `pchar` is I/O; only `div10` is an external compute leaf, cloned sub-side).
- **R-W3-3 — LIST/SAVE output byte-drift.** Mitigated: LIST + ASCII-SAVE output
  byte-identical is a hard gate; the oracle (openMSX) is the arbiter (wave-1 lesson).
- **R-W3-4 — the same core serves LIST *and* ASCII SAVE** (`PRDEST` 0/1). Both route
  through `DETOKBUF`; the drain honours `PRDEST` exactly as today. (This is why Q3-c
  is rejected — the ASCII-SAVE sink owns the FAT buffers.)
- **R-W3-5 — `div10` clone drift.** The sub-side `div10` clone must stay
  byte-behaviour-identical to [`print.asm:332`](../basic/print.asm:332); same trap as
  wave-2's leaf clones. Mitigated: it is a 12-instruction pure loop; the byte-
  identical LIST oracle catches any drift.

## 7. Gates (all must pass)

1. **`kwtable` single-copy assert** — resident copy is *gone*; only the sub copy
   remains; both `match_kw` and `detok_*` resolve to it.
2. **`diskbasic-acceptance-repack` 34/34** — LIST + ASCII SAVE (`SAVE",A"`) output
   byte-identical.
3. **`string-acceptance` / `float-acceptance` / `subrom-acceptance`** still green.
4. **Page-1 relief measured** (`__MEAS_*`): detok-core body − drain stub, plus the
   dropped resident `kwtable` low-region bytes.
5. **Host `unit-test`** — LIST/detok paths through the separate-machine bridge.
6. **Lean `basic.rom` byte-identical** — all sub-ROM code `IF ROM_BASE < $4000`; the
   lean cart keeps its inline streaming detok + inline `kwtable`.

## 8. Scope boundary

- **In:** detok-core sub-side + resident drain + the buffer ABI + `kwtable` dedup.
- **Out:** the lean-build detok (unchanged, streaming); the `PRDEST`/`pchar` sink and
  all I/O (stays resident); keyword-text *content*; the `$0038` interrupt trampoline
  (wave-2 deferred item).
- **Effort:** > wave 2 — the buffer ABI + the number-renderer audit are the work.

## 9. Open questions for sign-off

- **Q1. RESOLVED → design A, 512 B.** Worst-case output ≤475 B (source cap 96, only
  `?`→PRINT expands; §0.2). Design B dropped.
- **Q2. RESOLVED → clean lift + one `div10` clone.** No `dt_*` path touches the BIOS;
  the number renderers are already `NUMBUF`-buffered (§0.1, §0.3).
- **Q3. DECIDED 2026-07-11 → Q3-a** (user sign-off). Lower repack `TXTMAX`
  `$C000`→`$BE00`, `DETOKBUF equ $BE00` (512 B), accepting the documented −512 B
  repack program-capacity divergence (`OUT OF MEMORY` threshold moves down 512 B,
  repack build only). **Spec SIGNED OFF; implement wave 3.**
