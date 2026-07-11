<!-- Provenance: original work (own-design spec over our own detokeniser + the ratified sub-ROM ABI). -->
# Spec SKETCH — sub-ROM eviction WAVE 3: the detokeniser core

**Status: SKETCH — not for sign-off yet.** Gated behind wave 2 shipping
([spec-basic-subrom-wave2-tokeniser.md](spec-basic-subrom-wave2-tokeniser.md)), and
needs its own investigation pass (the buffer-sizing fork, §5, is unresolved). This
records the design while it's fresh so wave 2's `kwtable` duplication is understood
as *temporary*. Cross-refs: LIST/detok [`basic/list.asm`](../basic/list.asm),
dispatch [`basic/subromcall.asm`](../basic/subromcall.asm), wave-1 tenant
[`sub/tkfloat.asm`](../sub/tkfloat.asm).

---

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
  page-1 include, [`main.asm:133`](../basic/main.asm:133)).
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

## 5. THE open fork — buffer sizing (must resolve before sign-off)

detok output is **not** bounded by the ≤255-char source line, because some tokens
*expand*: `?` (1 byte) → `PRINT` (5), keyword tokens → full keyword text. A
pathological `?:?:?:…` line (~127 `?:` pairs in 255 source chars) detokenises to
~760+ chars. So a whole-line buffer is not simply 256 B. Two designs:

- **(A) One-shot worst-case buffer** (~1–1.5 KB in page-2/3 RAM): the core
  detokenises the **whole line** in one `CALSLT`, the resident side drains it once.
  **Simple** — no resumable state, one `CALSLT` per line, the core keeps its natural
  straight-through walk. Costs RAM. *Leaning here* — RAM is cheaper than ABI
  complexity, and LIST is cold.
- **(B) Bounded buffer + resumable chunked core**: a small (e.g. 64–128 B) buffer,
  the core fills it and returns "more pending", the resident side drains and re-
  `CALSLT`s. Less RAM, but the core must **save/restore its walk state** (HL source
  cursor + which `dt_*` state + partial multi-byte lookahead) across `CALSLT`s, and a
  keyword/`?`-expansion must not straddle a chunk boundary mid-emit. This is the
  fiddly part; it's the reason wave 3 is a real refactor, not a lift.

Resolving (A) vs (B) — including the exact worst-case output bound — is wave 3's
first investigation task.

## 6. Risks

- **R-W3-1 — resumable-state ABI** (only under design B): multi-byte lookahead across
  a chunk boundary. Mitigated by choosing design A if the worst-case buffer is
  affordable.
- **R-W3-2 — a `dt_*` renderer needs the BIOS** (§3 audit). Mitigated: named
  pre-gate; clone or descope.
- **R-W3-3 — LIST/SAVE output byte-drift.** Mitigated: LIST + ASCII-SAVE output
  byte-identical is a hard gate; the oracle (openMSX) is the arbiter (wave-1 lesson).
- **R-W3-4 — the same core serves LIST *and* ASCII SAVE** (`PRDEST` 0/1). Both must
  route through the buffered path; the drain honours `PRDEST` exactly as today.

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

- **Q1.** Buffer design **(A)** one-shot worst-case vs **(B)** bounded resumable
  (§5). Needs the exact worst-case output bound first.
- **Q2.** Does any `dt_*` number renderer touch the BIOS (§3 audit)? Determines
  whether the core is a clean lift or needs clones.
- **Q3.** Buffer home + size in page-2/3 RAM, below stack.
