- [x] ✅ **CLOSED 2026-08-21 (D-FNEXPR2), 0 ROM BYTES — THE FACE FOR A
      NON-STRING FILENAME (`OPEN 5 AS #1`) WAS UNMEASURED.**
      [`docs/spec-basic-fnexpr2.md`](../../docs/spec-basic-fnexpr2.md) §2. Measured at
      SIX verbs, not the three this item named: `OPEN 5 AS #1` / `KILL 5` /
      `SAVE 5` / `LOAD 5` / `BLOAD 5` / `FILES 5` are **`Type mismatch`** on the
      CF-3300. 🎯 So the hunch recorded below — *"if `OPEN` agrees with `PLAY`
      on the reference, the fix is one instruction at one site"* — was right in
      both halves, and it was right about MORE verbs than it claimed: zerobas
      answered a non-quote with THREE different things and the reference answers
      one thing at all six.
      🔴 **BUT "NON-STRING → Type mismatch" IS NOT THE WHOLE RULE, AND THE ROW
      THAT SAYS SO WAS NOT IN THIS ITEM'S PLAN.** `SAVE 1/0` and
      `OPEN 1/0 AS #1` are **`Division by zero`** — the reference EVALUATES the
      operand and the operand's own fault wins. That is D-MISS-1's `A$=1/0`
      rule at the filename position, and a blanket ERR 13 would have matched six
      rows and been wrong on two.
      💰 **The item priced 0–3 B and it cost ZERO**: `els_tc_common`
      ([`basic/missing.asm`](../../basic/missing.asm)) already IS that whole tail
      (clear ERRMARK → `eval` → `check_expr_errors` → `Syntax error` if nothing
      parsed, else `type_mismatch_error`) and already had two entry points that
      each pop their own saved word before falling in. `fname_expr` has none to
      pop, so it enters at the common label and one jump target changed.
      *The original filing:*
      ⚠️ **THE FACE FOR A NON-STRING FILENAME (`OPEN 5 AS #1`) IS UNMEASURED.**
      Filed 2026-08-21 by D-FNEXPR §3.3, which deliberately PRESERVED today's
      answer rather than guess at a better one. zerobas says `Syntax error`,
      before the change (a non-quote failed `cp '"'`) and after it (`str_eval`
      returns CF clear on a numeric operand and `fname_expr` jumps to the same
      `stmt_error`). **No row drives it on either reference.**
      🎯 The reason to doubt it is inside this tree: `ex_play`
      ([`basic/play.asm`](../../basic/play.asm)) answers `Type mismatch` for exactly
      this shape — a numeric expression where a string operand is required — and
      that face was measured against the reference. If `OPEN` agrees with `PLAY`
      on the reference, the fix is one instruction at one site.
      💰 A row on each of `OPEN`/`KILL`/`NAME`, then 0–3 B. Cheap, and it is a
      MEASUREMENT before it is a change.
