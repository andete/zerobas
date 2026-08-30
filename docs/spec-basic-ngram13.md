# D-NGRAM13 — one `dpl_get_store` for the disk loader's three byte copies

*2026-08-30. `basic/cload.asm`. Probe `scratchpad/ngram13_probe.py`, arms
`scratchpad/ngram13_knives.py`.*

**Cost: −11 B** — main page 1 344 → **355 B** free. **Rows: 9, 3 DIFF — all three
pre-existing and measured on the tree BEFORE the carve**, byte-identical after.

## 1. The carve

`disk_prog_load` open-coded the same six instructions three times — twice for
the line number, once per body byte:

```
                call    fat_io_getbyte
                jp      c,dpl_err_pop
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
```

14 B × 3 = 42 B. The helper is 13 B and each site becomes `call` + `jp c,` = 6 B,
so 31 B: **−11**.

## 2. 🔴 The 15 B version worked, and it was the wrong one

Folding `jp c,dpl_err_pop` *into* the helper is 4 B cheaper (**−15**) and needs a
frame fix. Every call site guards exactly one value across the read — the body
length, or the remaining count — and `dpl_err_pop` is written to drop it. From
inside a helper the helper's own return address sits on top of that value, so the
error tail must drop two:

```
dgs_err:        pop     hl                  ; drop OUR return address
                jp      dpl_err_pop         ; then the caller's guard
```

That builds, and every row agrees. **K-N13A cut the `pop hl` and moved ZERO
rows.**

## 3. 🔴 Two fixtures, two hostile return addresses, still nothing

The value left on the stack is the remaining byte count, and on a botched pop
count `dpl_err`'s `ret` uses it as an **address**.

| fixture | count at EOF | bogus return address | rows moved |
|---|---|---|---|
| `BODY.BAS` (7 B file) | 7 | `$0007` | 0 |
| `BIG.BAS` (claims a 3000-byte line, cut after 5) | 2995 | `$0BB3` | 0 |

`BIG.BAS` was built *specifically* because `$0007` looked too benign to be a
fair test. It changed nothing.

**The mechanism is the finding: the stack below the loader is the REPL's own.**
A stray `ret` into the middle of the ROM executes whatever is there and, sooner
or later, hits a `ret` that lands on one of the interpreter's own frames — so
the machine wanders back to the prompt and every row reads normally.

**A guard no row can see is one nobody can maintain.** 4 B were given back for
the CF-return shape, whose failure *is* a reading. This is the call D-ARGOPEN
made, for the same reason, on the same kind of guard.
[[a-guard-witnessed-only-by-a-deferred-error]]

## 4. The two arms, and one prediction that was too wide

| knife | cuts | predicted | moved |
|---|---|---|---|
| K-N13A | `ret c` → `or a` (swallow the EOF) | 7 rows | **3** — `d.body-l`, `d.lineno-l`, `d.body-res` |
| K-N13B | `inc hl` (the store advance) | 3 rows | 3 — `d.ok`, `d.body-l`, `d.body-res` |

🔴 **The two MESSAGE rows cannot move, and that is worth keeping.** With the EOF
swallowed the loader runs past the end of the file and hits EOF again at the next
**link-word** read, which has its own `jp c,dpl_link_err` and prints the
identical message. **A second check downstream makes the first one's failure
invisible to any row that reads only the message** — the rows that see it are the
ones that read the resulting *program*.

🎯 **The two knives say WHICH HALF each row exercises.** `d.lineno-l` moves under
K-N13A and holds under K-N13B: `LNO.BAS` is cut off after the link word, which
the loader stores with its own `ld (hl),c / inc hl / ld (hl),b` — so that row
reaches the helper's read and never its store.

## 5. 📌 A pre-existing divergence, measured on the way in

Nothing in the tree reached `dpl_err_pop` before this slice, so a truncated
tokenised BASIC file had never been read on either machine. Three rows diverge,
**on the unmodified tree**:

| row | CF-3300 | zerobas |
|---|---|---|
| `d.body` (message) | `<nothing>` | `load error` |
| `d.lineno` (message) | `<nothing>` | `load error` |
| `d.lineno-l` (listing) | `<nothing>` | `0` |

The reference **accepts a truncated file silently**; zerobas reports. The likely
mechanism is that the reference reads whole SECTORS and never sees a byte-level
EOF — the zero padding terminates the program cleanly — while `fat_io_getbyte`
honours the directory entry's byte length.

🟢 **And where they agree, they agree exactly**: `d.body-l` lists `10` on both,
and `d.body-res` — a truncated load over a resident program — produces the same
mangled `10 POKE ZQ1"` on both, byte for byte.

Filed in `TODO.md`; not opened here. **The carve left all three readings
unchanged**, which is what the rows were built to be able to say.
