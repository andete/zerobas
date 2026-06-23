# Behavioural spec: line tokenisation (crunch) — minimal, BLOAD slice

Derived from **oracle observation only** (openMSX headless, Philips VG-8020,
black-box input→output capture) plus allowed public sources. No disassembly
consulted. See `CONTRIBUTING.md`.

This is the implementer-facing artefact for the **tokeniser + execution-loop**
slice. The implementation lives in this repo, not here. It covers only
as much of MSX-BASIC's "crunch" as the `BLOAD"CAS:",R` game-loader path needs.

## What was tested

`probes/basic/basic_probe_tokenise.py` types the direct-mode line

    bload"cas:",r

into a real MSX-BASIC, then breaks the moment the interpreter executes the
statement (PC reaches `TAPION` `$00E1`) and dumps two work-area buffers:

- **BUF** `$F55E` — the raw ASCII line as entered.
- **KBUF** `$F41F` — the *crunched* (tokenised) line being interpreted.

(Breaking at `TAPION` is convenient because the line is fully crunched by then.
A cassette is inserted only so BLOAD reaches `TAPION`; its bytes are never read.)

## Observed behaviour

Captured buffers (the input line `bload"cas:",r` typed at the start of the line):

```
BUF  $F55E:  62 6C 6F 61 64 22 63 61 73 3A 22 2C 52 00   "bload"cas:",R\0"
KBUF $F41F:  CF          22 63 61 73 3A 22 2C 52 00       "<CF>"cas:",R\0"
```

### 1. Keywords crunch to a single token byte

The five ASCII letters `bload` (offsets 0–4 in BUF) collapse to the **single
byte `$CF`** at the head of KBUF. Everything after it shifts left by four.

| Keyword | Token | Source |
|---------|-------|--------|
| `BLOAD` | `$CF` | oracle observation (this dump); cross-checks MSX Assembly Page token table |

### 2. Keywords are case-folded

The input was lowercase `bload`; it still crunched to `$CF`. The tokeniser
recognises keywords regardless of case.

### 3. Everything that is not a keyword is kept verbatim

After the `$CF` token the bytes are byte-identical to the ASCII tail, **case
included** — the lowercase `cas:` is preserved exactly:

```
22 63 61 73 3A 22 2C 52     =  " c a s : " , R
```

The quoted string `"cas:"` (both quote characters included), the comma, and the
`R` option are **not** tokenised — they are copied through as literal ASCII. The
interpreter re-parses them when it executes the statement. (An implementation
that wants to match `CAS:` case-insensitively must fold the device name itself.)

### 4. The crunched line is `0x00`-terminated

A single `$00` byte ends the token stream.

### 5. Leading whitespace is preserved, not stripped

The cruncher copies any leading spaces through verbatim and the interpreter
skips them at execution; an implementer's own tokeniser writes no such padding.
(Direct-mode entry here has no leading spaces — the semantic point is only that
leading spaces, if present, are harmless and skipped.)

## Determinism

Re-running the probe produces byte-identical KBUF/BUF dumps (per the harness
determinism guarantee), so this spec is reproducible.

## Provenance log

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `BLOAD` keyword token | `$CF` | oracle observation (KBUF dump); MSX Assembly Page token table | sourced |
| Keyword case-folding | — | oracle observation (lowercase input → `$CF`) | sourced |
| Non-keyword bytes kept verbatim (strings, punctuation, options) | — | oracle observation (ASCII tail unchanged) | sourced |
| Crunched-line terminator | `$00` | oracle observation | sourced |
| KBUF (crunch buffer) address | `$F41F` | MSX2 Technical Handbook sysvar map / MSX Assembly Page | sourced |
| BUF (line input buffer) address | `$F55E` | MSX2 Technical Handbook sysvar map / MSX Assembly Page | sourced |
| TAPION entry point (sync landmark) | `$00E1` | MSX Assembly Page BIOS call list | sourced |

No quarantined items.

## What the implementer must build (this slice)

A minimal crunch + dispatch front-end, replacing the hard-coded "INIT *is* the
BLOAD" tracer bullet:

1. **Tokenise** an ASCII line into a buffer: walk the line; at each position try
   to match a keyword from a small keyword→token table (one entry so far,
   `BLOAD`→`$CF`, case-folded); on a match emit the token byte, otherwise copy
   the byte verbatim; terminate with `$00`.
2. **Execute**: skip leading spaces, read the first token; dispatch on it. For
   `$CF` (`BLOAD`) call the BLOAD statement handler, passing a pointer to the
   bytes after the token.
3. The **BLOAD handler** (refactor of the existing tracer bullet) parses its
   verbatim args from the token stream — the `"CAS:"` device string and the
   optional `,R` — then performs the cassette load and the `,R` handoff exactly
   as specified in `spec-bload-r.md`.

The end-to-end behaviour (load + handoff) is unchanged from `spec-bload-r.md`;
this slice only changes *how the statement is reached* — crunched and dispatched
rather than hard-wired.
