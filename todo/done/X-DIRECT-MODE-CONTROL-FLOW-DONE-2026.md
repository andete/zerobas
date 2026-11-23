- [x] **Direct-mode control flow — ✅ DONE 2026-07-26**, spec + as-built
      [`docs/spec-basic-direct-ctrl.md`](../../docs/spec-basic-direct-ctrl.md), gate
      [`make direct-ctrl-acceptance`](../../Makefile) **40/40** vs the VG-8020
      (probe [`probes/basic/basic_probe_direct_ctrl.py`](../../probes/basic/basic_probe_direct_ctrl.py),
      boot-per-case, 6 groups). `FOR`/`NEXT`, `GOSUB`/`RETURN`, `GOTO`,
      `IF..THEN <line>` and `ON..GOTO` **typed at the prompt** — an execution
      MODE that had **zero** coverage: every earlier loop/trap/graphics gate runs
      its BASIC as a stored program + `RUN`.
      Two defects, and the reported one (`FORI=1TO7:NEXT` → `out of memory`) was
      the milder: `GSP`/`FSP` had exactly one init site (`run_program`), so before
      the first `RUN` they held power-on garbage (**D-DIR-1**); and
      `dispatch_line` ran a typed line with a bare `jp exec`, which walks
      statements but never services the deferred-transfer flags, so a direct
      `GOTO`/`IF..THEN`/`ON..GOTO` was a **silent no-op** (**D-DIR-2**). Fixing
      D-DIR-1 alone would have been *worse* than the bug — a loud ERR 7 traded for
      a `FOR` body silently running zero times.
      As built: a typed line executes as a **virtual line** (`dir_line`, a 4-byte
      **ROM** header whose two words overlap so the link doubles as the `$0000`
      end marker) through the real run loop, so no direct-mode special case exists
      anywhere in the loop; `DIRECTF` is **derived** at `rp_exec` from `CURLINE`'s
      high byte, never carried, because direct mode is a property of the line
      *being run* (a typed `GOSUB` into line 10 reports `Syntax error in 10`, the
      `RETURN` back into the typed line reports a bare `Syntax error` — measured);
      and the control-stack reset moved from `run_prog` into `clear_vars`, whose
      four call sites are exactly the four the reference resets on (cold boot,
      `RUN`, `NEW`, `CLEAR` — and a frame does **not** die at the next prompt).
      **DEFERRED (D-DIR-3):** interrupt traps still do not dispatch in direct
      mode. Before this slice no trap *could* fire at the prompt, and whether the
      reference fires them there is UNMEASURED — so the conservative answer is
      gated in at one RAM load rather than changed as a side effect. Spec §6 names
      the characterization that closes it.
