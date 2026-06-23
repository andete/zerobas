# Behavioural spec: keyword tokens for REM / POKE / PEEK (and `'`)

Derived from **oracle observation only** (openMSX headless, Philips VG-8020,
black-box input→output capture) plus allowed public sources. No disassembly
consulted. See `CONTRIBUTING.md`.

Implementer-facing artefact for the **REM / POKE / PEEK** statement slice and the
**Step A byte-identical-crunch** milestone (§3–§4). The implementation lives in
the zerobas repo, not here. It extends `spec-tokenise.md` (the BLOAD-slice crunch
spec) with token bytes for more keywords, the integer/`&H` constant encoding, the
operator tokens, and the letter-upcasing rule.

## What was tested

`probes/basic/basic_probe_tokens.py` types four direct-mode lines and, the
instant the interpreter reaches `TAPION` (`$00E1`), dumps the crunch buffer
**KBUF** `$F41F`. Every line embeds `bload"cas:",r` purely as a deterministic
landmark: by the time BLOAD opens the tape the whole line is already crunched, so
KBUF holds the tokenised form of all of it. (Same landmark trick as
`spec-tokenise.md`. A cassette is inserted only so BLOAD reaches TAPION; its
bytes are never read.) POKE/PEEK precede the bload (they execute harmlessly);
REM/`'` follow it (they swallow the rest of the line, so the bload must run
first).

## Observed crunch buffers

```
poke 0,0:bload"cas:",r
KBUF: 98 20 11 2C 11 3A CF 22 63 61 73 3A 22 2C 52 00
      ^P ^_ ^0 ,  ^0 :  ^B "  c  a  s  :  "  ,  R  \0

b=peek(0):bload"cas:",r
KBUF: 42 EF FF 97 28 11 29 3A CF 22 63 61 73 3A 22 2C 52 00
      B  =  ^^PEEK^ (  ^0 )  :  ^B "  c  a  s  :  "  ,  R \0

bload"cas:",r:rem AB
KBUF: CF 22 63 61 73 3A 22 2C 52 3A 8F 20 41 42 00
      ^B "  c  a  s  :  "  ,  R  :  ^R sp A  B  \0

bload"cas:",r:'AB
KBUF: CF 22 63 61 73 3A 22 2C 52 3A 3A 8F E6 41 42 00
      ^B "  c  a  s  :  "  ,  R  :  <----'---->  A  B  \0
```

(`^P`=POKE `$98`, `^B`=BLOAD `$CF`, `^R`=REM `$8F`, `^0`=numeric-constant token
for `0` = `$11`.)

## 1. Keyword token bytes

| Keyword | Token (hex) | Notes | Source |
|---------|-------------|-------|--------|
| `POKE`  | `$98`       | single statement-keyword byte | oracle (this dump); cross-checks MSX Assembly Page token table |
| `PEEK`  | `$FF $97`   | **two bytes**: `$FF` function prefix + `$97` | oracle; MSX Assembly Page token table |
| `REM`   | `$8F`       | single byte; swallows the rest of the line | oracle; MSX Assembly Page token table |
| `'`     | `$3A $8F $E6` | the `'` abbreviation crunches to `:` + REM + `$E6` ("remark-quote" marker) | oracle |

Lowercase input was used (`poke`, `peek`, `rem`); each still crunched to its
token, confirming keywords are **case-folded** (consistent with `spec-tokenise.md`
§2). Functions use a `$FF` prefix; statement keywords are a single byte.

## 2. REM swallows the rest of the line, verbatim

After the `$8F` REM token the remaining bytes are byte-identical ASCII (`20 41 42`
= ` AB`) — the comment text is **not** crunched (a keyword inside a comment would
not be tokenised). The interpreter does nothing with it. The `'` form does the
same after its `$3A 8F E6` sequence.

## 3. Full crunch fidelity (Step A) — numeric constants ARE tokenised, and zerobas now replicates them byte-for-byte

The earlier REM/POKE/PEEK slice deliberately kept numbers and operators verbatim.
That decision is **reversed**: a stored zerobas program must be byte-for-byte
identical to a real ROM's, so the tokeniser now reproduces the reference's
constant and operator encoding exactly. The encoding below is an **observed
output** — captured by `basic_probe_tokens.py`'s fidelity sweep
(`a=<expr>:bload"cas:",r`, break at TAPION, read the crunched `<expr>` between the
`=` token `$EF` and the `:` `$3A`). Never copied from a disassembly, never
assumed from memory; the **MSX Assembly Page** token table is an after-the-fact
cross-check only.

### Observed crunch (fidelity sweep)

```
a=0       -> 11                 a=&h0     -> 0C 00 00
a=9       -> 1A                 a=&hff    -> 0C FF 00
a=10      -> 0F 0A              a=&hd000  -> 0C 00 D0
a=99      -> 0F 63              a=&hffff  -> 0C FF FF
a=255     -> 0F FF
a=256     -> 1C 00 01           a=1+2     -> 12 F1 13
a=1000    -> 1C E8 03           a=5-1     -> 16 F2 12
a=32767   -> 1C FF 7F           a=2*3     -> 13 F3 14
a=32768   -> 1D 45 32 76 80     (= single-precision float; OUT OF SCOPE)
a=65535   -> 1D 45 65 53 50     (= float; OUT OF SCOPE)

poke &hd000,2*3+4 -> 98 20 0C 00 D0 2C 13 F3 14 F1 15
a=peek(&hd000)    -> 41 EF FF 97 28 0C 00 D0 29
```

### Integer constant encoding (observed)

| Decimal value | Token + bytes | Form |
|---------------|---------------|------|
| `0`–`9`       | `$11 + n` (one byte, no value byte) | single-digit token |
| `10`–`255`    | `$0F`, `<1 byte value>` | one-byte unsigned int |
| `256`–`32767` | `$1C`, `<2 bytes value, little-endian>` | two-byte signed int |
| `≥ 32768`     | `$1D`, `<float>` | single-precision float — **out of scope** |

So `$11`–`$1A` are the digit tokens for `0`–`9`; operand digits in the operator
rows confirm it (`1`→`$12`, `2`→`$13`, `3`→`$14`, `4`→`$15`, `5`→`$16`).

### `&H` hex constant encoding (observed)

| Form | Token + bytes |
|------|---------------|
| `&H<hex>` | `$0C`, `<2 bytes value, little-endian>` (always 3 bytes; full `0`–`FFFF`) |

`&H` is **case-insensitive** (`&h` worked). zerobas uses `&H` for all 16-bit
address/values, so the entire `0`–`FFFF` range is byte-identical.

### Operator tokens (observed)

| Operator | Token |
|----------|-------|
| `=` | `$EF` |
| `+` | `$F1` |
| `-` | `$F2` |
| `*` | `$F3` |

`(` `)` `,` `:` and space stay **verbatim** (`$28 $29 $2C $3A $20`), as seen in
the whole-line dumps.

## 4. Letters are upcased in the crunch (outside string literals)

Lowercase input crunches to uppercase outside string literals: the variable `a`
→ `$41` (`A`), and even the BLOAD option `,r` → `$2C $52` (`,R`). Inside a string
literal the bytes are preserved (`"cas:"` → `22 63 61 73 3A 22`, lowercase
intact). zerobas's tokeniser must therefore upcase letters everywhere except
inside string literals and the REM/`'` comment tail (which stay verbatim per §2).

### What is OUT OF SCOPE this step

Octal (`&O`), binary (`&B`), and floating-point constants (incl. decimal
`≥ 32768`, which the reference floats — use `&H` instead); and line-number-
reference tokens (the `$0E`-style GOTO targets). These arrive with their
consuming features in later steps.

## Determinism

Re-running the probe produces byte-identical KBUF dumps (harness determinism
guarantee), so this spec is reproducible.

## Provenance log

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `POKE` token | `$98` | oracle (KBUF dump); MSX Assembly Page token table | sourced |
| `PEEK` token | `$FF $97` | oracle; MSX Assembly Page token table | sourced |
| `REM` token | `$8F` | oracle; MSX Assembly Page token table | sourced |
| `'` crunch | `$3A $8F $E6` | oracle | sourced |
| REM/`'` keep the rest of the line verbatim | — | oracle observation | sourced |
| Keyword case-folding | — | oracle (lowercase input → token) | sourced |
| KBUF address | `$F41F` | MSX2 Technical Handbook sysvar map / MSX Assembly Page | sourced |
| TAPION landmark | `$00E1` | MSX Assembly Page BIOS call list | sourced |
| Digit constant tokens `0`–`9` | `$11`–`$1A` (`$11 + n`) | oracle (fidelity sweep); MSX Assembly Page token table | sourced |
| One-byte int constant (`10`–`255`) | `$0F`, value | oracle (fidelity sweep) | sourced |
| Two-byte int constant (`256`–`32767`) | `$1C`, value LE | oracle (fidelity sweep) | sourced |
| `&H` hex constant | `$0C`, value16 LE | oracle (fidelity sweep) | sourced |
| Operator `=` | `$EF` | oracle | sourced |
| Operator `+` | `$F1` | oracle (fidelity sweep) | sourced |
| Operator `-` | `$F2` | oracle (fidelity sweep) | sourced |
| Operator `*` | `$F3` | oracle (fidelity sweep) | sourced |
| `( ) , :` and space kept verbatim | `$28 $29 $2C $3A $20` | oracle (whole-line dumps) | sourced |
| Letters upcased outside string literals (vars + options) | — | oracle (`a`→`A`, `,r`→`,R`; `"cas:"` preserved) | sourced |
| Float constant token (decimal `≥ 32768`) | `$1D …` | oracle (boundary observation) | sourced (recorded; **out of scope** — not implemented) |

No quarantined items.

## What the implementer builds (zerobas)

### REM / POKE / PEEK slice (done)

1. **Tokeniser**: `REM` (`$8F`), `POKE` (`$98`), `PEEK` (`$FF $97`) in the keyword
   table (case-folded); on the REM token (and `'`, treated as REM) copy the rest
   of the line verbatim and stop crunching.
2. **Statement loop + `:`**; **integer expression evaluator**; **POKE/PEEK**
   semantics from the public MSX-BASIC language reference.

### Step A: byte-identical crunch + token-decoding evaluator

3. **Tokeniser fidelity** (per §3/§4): emit the integer-constant tokens
   (`$11+n` / `$0F`,b / `$1C`,w-LE), the `&H` token (`$0C`,w-LE), and the operator
   tokens (`= $EF`, `+ $F1`, `- $F2`, `* $F3`); keep `( ) , :`/space verbatim;
   upcase letters outside string literals; fix `'` → `$3A $8F $E6`.
4. **Evaluator decodes tokens** (not ASCII): a constant token yields its binary
   value; operator tokens drive precedence; variables are upcased letters; `PEEK`
   is `$FF $97`. Assignment detects the `=` token (`$EF`).
5. **Validation**: `basic_probe_crunch.py` compares zerobas's `TOKBUF` against the
   reference's `KBUF` byte-for-byte (both broken at TAPION). Out of scope: `&O`,
   `&B`, float (decimal `≥ 32768` — use `&H`), and line-number-reference tokens.
