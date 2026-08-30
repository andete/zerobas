# D-TRUNCLOAD — a truncated tokenised BASIC file: the rule is mapped, the repair is not

*2026-08-30. `basic/cload.asm` (the EOF policy) + `sub/lineedit.asm` (the
bounded relink). Probe `scratchpad/truncload_probe.py`, 24 rows, two references.*

**Rows: 18 scored, 18 agree, 0 diverge, 6 NO-ORACLE.** All five message
divergences closed. **Cost: main page 1 −4 B (355 → 351), sub page 1 +1 B.**

⚠️ **Read §3 before §6.** Two repairs were built and REVERTED before the one
that ships, and the reason the third works is not in the loader at all.

Opened by D-NGRAM13 §5, which found the divergence while building rows for a
carve: nothing in the tree had ever reached `dpl_err_pop`, so a truncated
tokenised BASIC file had never been read on either machine.

## 1. The rule, at every site the loader can hit EOF

`disk_prog_load` checks EOF at **five** distinct points. Measured on the
unmodified tree:

| fixture | cut after | CF-3300 | zerobas |
|---|---|---|---|
| `NIL.BAS` | nothing (0 bytes) | `<nothing>` | `load error` |
| `BARE.BAS` | the `$FF` marker | `<nothing>` | `load error` |
| `LINK.BAS` | marker + 1 link byte | `<nothing>` | `load error` |
| `LNO.BAS` | marker + link word | `<nothing>` | `load error` |
| `ZERO.BAS` | marker + link + lineno + 2 body bytes | `<nothing>` | `load error` |

**The reference is silent at all five.** A truncated tokenised BASIC file is not
an error condition on an MSX; it simply ends the load.

One listing row diverges too: after `LNO.BAS`, `LIST` shows nothing on the
reference and `0` on zerobas — zerobas took the error path, so it never wrote the
end marker and `LIST` wanders into stale memory.

## 2. 🔬 The filed hypothesis was REFUTED by a controlled pair

D-NGRAM13 filed this reasoning: *the reference reads whole SECTORS, so it never
sees a byte-level EOF — the zero padding after the recorded length reads as a
`$0000` link word, which is a legitimate end-of-program marker.*

`GARB.BAS` separates that rule from "honour the recorded length": it is the same
truncation, with the **same recorded size**, followed by non-zero garbage inside
the same sector. The directory size is written down *after* `add_file`, because
passing the garbage as content would also make the file longer — and a longer
file is a different question.

| | `t.zero` | `t.garb` |
|---|---|---|
| CF-3300 message | `<nothing>` | `<nothing>` |
| CF-3300 listing | `10` | `10` |

**Identical.** The reference honours the recorded length and sees the EOF — it
just does not report it. The sector theory is dead.

## 3. 🔴 Two repairs, two hangs — and the third fix is not in the loader

**Repair A — EOF joins the completion path.** Hoist the `CLPTR`/`CLINK` init
above the marker read (so a zero-byte file has a cursor to commit), point the two
unguarded EOF arms at `dpl_done`, and add a 4 B shared tail for the three sites
that guard one stack word:

```
dpl_eof:        pop     af                  ; drop the caller's guarded word
                jp      dpl_done
```

🟢 **All five message rows closed.** 🔴 **And three rows became `<NO ECHO>`: the
machine HUNG.**

**Repair B — terminate the partial line first.** The body case stopped hanging
and read `10 POKE` against the reference's `10`; **the hang moved** to two other
rows, one of which repair A had got right. Both reverted.

## 4. 🎯 The instrument the spec asked for, and what it said

§4 of the reverted draft named what was missing: *the memory image the reference
is left holding*. `PRINT PEEK(...)`, three rows per fixture, both machines:

| | `$8001-2` (link) | `$8003-4` (lineno) | `$8005-6` (body) |
|---|---|---|---|
| well-formed, both | `14 128` | `10 0` | `152 32` |
| truncated mid-body, CF-3300 | `12 192` | `10 0` | `152 32` |
| truncated mid-body, zerobas *(pre-fix)* | `14 128` | `10 0` | `152 32` |

**The stores are identical.** Both machines wrote link + line number + the two
body bytes that arrived. The only difference is the **link word**: the reference
had **relinked** (`$C00C`), zerobas had not, because it took the error path.

So the reference's rule is exactly repair A — commit normally on EOF. Repair A
hung zerobas and not the reference for a reason in a completely different file.

## 5. 🔴 The hang was `relink`, and it was an equality test

`sub/lineedit.asm`, `rlb_lp`, stopped **only when `HL == PRGEND` exactly**:

```
                ld      a,(PRGEND+1)
                cp      h
                jr      nz,rlb_more
                ld      a,(PRGEND)
                cp      l
                jr      nz,rlb_more
```

A truncated store's last line has no `$00` terminator, so `skip_to_eol`
**overshoots** PRGEND looking for one — and past it an equality test never fires
again. relink walks RAM forever.

The reference survives the identical store, so its test is `>=`. Bounded:

```
                ld      de,(PRGEND)
                push    hl
                or      a
                sbc     hl,de
                pop     hl
                jr      c,rlb_more
```

**On a well-formed program the two tests agree exactly** — HL lands on PRGEND —
so this is strictly more robust, and it is **2 B smaller** than the pair of byte
compares it replaces. `ctl.edit` (type three lines out of order, `LIST`) is the
control that says the normal path did not move.

## 6. 6 rows have no oracle, and they are named rather than dropped

After the fix, six rows still differ — and **not one of them is about the
loader**. A truncated store's last line is unterminated, so relink's forward scan
stops wherever memory happens to hold a `$00`: the CF-3300 reaches these rows
over uninitialised RAM (`$FF`), zerobas over RAM a preceding `NEW` zeroed.

🟢 **The stores agree, which is what says this is history and not behaviour.**
`m.zero1`/`m.zero2` are identical; `m.lno0` — the relinked link of the
header-only fixture — agrees too (`12 192` on both). What diverges is what `LIST`
renders *past* the bytes the loader wrote.

## 7. 🔴 Two apparatus faults and one wrong mechanism, all in the memory read

* `FORI=0TO15:PRINTPEEK(&H8001+I);"/";:NEXT` is 40 characters, so the **echo
  wrapped** — and `tail_after` matches a typed line against one screen row. Every
  memory row read `<NO ECHO>`, **the well-formed-file control included**, which
  is what caught it.
* Split into four short lines it **mis-echoed** instead: after the `load error`
  the machine swallowed 36 leading characters of the next line. `omsx_repl`
  refused the run rather than reporting it.
* 🔴 **And I wrote a wrong mechanism into the file.** `?PEEK(-32767);…` (39
  characters) read `<NO ECHO>` on zerobas and measured cleanly on the CF-3300, so
  I commented *"`?` is not accepted as PRINT here"* — a mechanism claim from a
  one-sided silence. `ctl.qmark` asks it directly: **both machines print `2`**.
  The cause is the 39-character line; one column of usable width between the two
  machines is enough to wrap on one and not the other.
  **An unverified mechanism in a comment is worse than a row.** The row stays.

## 8. Falsification

| claim | what would refute it | result |
|---|---|---|
| the reference is silent at every EOF site | one site printing a message | five fixtures, five silences, including a zero-byte file |
| it is not a sector-read effect | garbage padding changing the reading | identical to zero padding, §2 |
| both machines write the same store | a PEEK row disagreeing on a byte the loader wrote | `m.*1` / `m.*2` agree; `m.lno0` agrees after the fix |
| the bounded relink does not move the normal path | `ctl.edit`, `ctl.ok`, or the battery | green, and 47/47 |
| `?` was the problem | asking directly | **refuted** — `ctl.qmark` prints `2` on both |
