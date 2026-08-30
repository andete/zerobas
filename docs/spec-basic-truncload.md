# D-TRUNCLOAD — a truncated tokenised BASIC file: the rule is mapped, the repair is not

*2026-08-30. Probe `scratchpad/truncload_probe.py`, 13 rows, two references.
**No ROM change** — two repairs were built, measured, and reverted.*

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

## 3. 🔴 Two repairs, two hangs

**Repair A — EOF joins the completion path.** Hoist the `CLPTR`/`CLINK` init
above the marker read (so a zero-byte file has a cursor to commit), point the two
unguarded EOF arms at `dpl_done`, and add a 4 B shared tail for the three sites
that guard one stack word:

```
dpl_eof:        pop     af                  ; drop the caller's guarded word
                jp      dpl_done
```

🟢 **All five message rows closed**, and `t.link-l`, `t.bare-l`, `t.nil-l`
agreed. 🔴 **And three rows became `<NO ECHO>`: the machine HUNG.** Committing a
half-stored line leaves a body with no `$00` terminator, so `relink` reads the
line's *saved absolute* link word, jumps past the end marker, and never returns.

**Repair B — terminate the partial line first** (write one `$00` at `CLPTR` and
advance, then commit). The body case stopped hanging and reads `10 POKE` against
the reference's `10` — closer, still divergent — **and the hang moved to
`t.lno-l` and `t.link-l`**, one of which repair A had already got right.

| row | before | repair A | repair B | reference |
|---|---|---|---|---|
| `t.zero-l` | `10` ✅ | `<NO ECHO>` | `10 POKE` | `10` |
| `t.lno-l` | `0` | `<NO ECHO>` | `<NO ECHO>` | `<nothing>` |
| `t.link-l` | `<nothing>` ✅ | `<nothing>` ✅ | `<NO ECHO>` | `<nothing>` |

**Reverted.** A loader that hangs on some truncated files is worse than one that
prints a message the reference does not. The tree is back to the committed
state, and `make gates-fast` reports the identical four ROM hashes — checked,
not assumed.

## 4. What the next attempt needs

The rows exist and the rule is not in doubt. What is missing is the **memory
image the reference is left holding** — repair B shows zerobas keeps two body
bytes (`10 POKE`) where the reference keeps fewer (`10`), so the reference is
doing something more than "stop and commit". Candidates, none tested:

* it rolls `CLPTR` back to the start of the incomplete line **only when the line
  number was never completed** (which would explain `LNO`/`LINK` listing nothing
  while `ZERO` still lists a line);
* its `relink` is bounded by `PRGEND` and simply stops, making the terminator
  question moot;
* it writes the end marker at the point of EOF and its `LIST` stops at `PRGEND`
  rather than at a `$0000` link.

**A `PEEK` sweep of `$8001..` after each truncated load on both machines settles
it**, and that instrument does not exist yet. Until then the divergence is one
message and one stray `0` line — visible, harmless, and filed.
