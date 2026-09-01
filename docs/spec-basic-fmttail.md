# D-FMTTAIL — `CALL FORMAT`'s name-tail and argument skip, measured at last

**2026-09-01.** The review tier filed this by *reading* `basic/format.asm`: after
matching the six chars `FORMAT`, everything up to `':'`/EOL was silently
swallowed, so `CALL FORMATFOO` and `CALL FORMAT anything` both formatted, and the
skip was quote-blind. The reference's surface was recorded as **unknown**.

It is now measured, and the reference is **strict on every count**.

| row | typed | CF-3300 | zerobas (before) |
|---|---|---|---|
| `f.ctl` | `CALL FORMAT` | accepted (format prompt) | accepted |
| `f.us` | `_FORMAT` | accepted (format prompt) | accepted |
| `f.colon` | `CALL FORMAT:PRINT 1` | accepted (format prompt) | accepted |
| `f.bad` | `CALL FORMA` | **Syntax error** | **Syntax error** |
| `f.tail` | `CALL FORMATX` | **Syntax error** | accepted — **formats** |
| `f.tail2` | `CALL FORMATFOO` | **Syntax error** | accepted — **formats** |
| `f.arg` | `CALL FORMAT X` | **Syntax error** | accepted — **formats** |
| `f.quote` | `_FORMAT("A:")` | **Syntax error** | accepted — **formats** |

**4 divergences of 8 rows → 0, for ZERO bytes** (page 1 free 358 B before and
after).

🔴 **AND THE DIVERGENCE DESTROYS DATA.** These are not cosmetic message rows: on
zerobas `CALL FORMATX` — a typo, one key past the verb — **silently formatted
the disk**, where the reference refuses with a `Syntax error` and touches
nothing. The filed item called the behaviour "sloppy-accept"; the accurate name
is *a typo wipes the disk*.

## The fix

`exc_skip`'s swallow-to-delimiter loop becomes a requirement that the name **end
the statement**: `skip_spaces`, then EOL or `':'`, else `stmt_error` — raised
**before** `do_format`, because the reference's error lands before its prompt
appears.

⚠️ **`f.colon` IS WHY THE TEST IS NOT A BARE `or a`.** `CALL FORMAT:PRINT 1` is
accepted on both references, so this is end-of-STATEMENT, not end-of-line. Every
other row in the table passes under the stricter rule too — the two rules
coincide on all seven of them, and only `f.colon` separates them
[[two-rules-that-coincide-on-every-row-you-have]].

The idiom was checked for aggregation first: `or a / jr z / cp COLON / <error>`
occurs at **0** other main-ROM sites, so there is nothing to share.

🟢 **AND A GATE MADE IT FREE.** The first cut cost 1 byte and `redundant-load-check`
went **REAL red on the serial retry** — not a flake — naming
`basic/format.asm:73` as a dead load, because `skip_spaces` **already returns
`A = (HL)`**. Dropping the reload put page 1 back to 358 B, so four divergences
close for nothing. 🎯 The gate knew a calling contract that the code being
written did not, which is the whole point of asserting contracts rather than
documenting them.

## Measuring it without formatting anything

🎯 **THE ROWS NEED NO FORMAT TO COMPLETE.** A rejected row errors *before*
anything happens; an accepted row parks the CF-3300 at its interactive prompt. So
the comparable observable is **REJECTED vs ACCEPTED**, read off the screen with
the prompt **never answered** — the reference formats no disk at any point. Every
side still gets its own scratch copy per row, because zerobas has no prompt (one
geometry) and an accepted row formats immediately.

## Three instrument faults, and the control that caught the first

🔴 **The negative control earned its place on the first run.** `f.bad`
(`CALL FORMA`) must be rejected on both machines. It read *ACCEPTED*, which is
impossible — and that is the only reason the following three faults were found
instead of being published as a result.

1. **The plane was chosen by a heuristic, and the pattern generator won.** The
   first cut captured both `$0000` and `$1800` and kept "whichever renders more
   non-blank rows". Two *different* typed lines produced **byte-identical**
   screens — a readout that fails by agreeing
   [[readout-blind-to-its-own-subject]].
2. **The two machines put their name table at different addresses.** Measured:
   the **CF-3300 at `$1800`**, **zerobas at `$0000`**, both stride 40. `$F3B3`
   reads `0000` on *both*, so it is not the discriminator.
3. **The screen wraps mid-word, and `rstrip()` broke the only string that
   matters.** `Syntax` occupies the last six columns of one row and ` error` the
   first six of the next; stripping rows and joining with a space yields
   `"Syntax  error"`, matching no error name. Concatenating the untouched
   40-column rows reconstructs the text, because the wrap carries its own
   spacing.

➡️ **The plane is now chosen by the one thing that proves it is the screen: it
must contain the ECHO of the line we typed.** A plane that cannot show its own
subject is refused as `<NO SCREEN>` rather than reported. That is a principled
selector where "more non-blank rows" was a guess wearing a measurement's clothes.

## Side finding

`probes/disk/diskbasic_probe_format.py` — the kept provenance spike — renders
that same `$1800` at **width 32**. Its `PROCNM` evidence is a hex read and is
unaffected, but every screen dump it has ever printed was scrambled. Corrected to
40 here.
