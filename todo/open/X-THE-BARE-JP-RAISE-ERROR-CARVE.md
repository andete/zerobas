- [ ] ⚠️ **The bare-`jp raise_error` carve family is worth ~2 B, and the reason
      is worth more than the bytes.** Filed 2026-08-22 by D-DUPSPAN,
      [`docs/spec-basic-dupspan.md`](docs/spec-basic-dupspan.md) §2.1.
      `scratchpad/dupspan_sweep.py` ranks it fourth (six copies, 15 B nominal),
      but **five of the six are entered by FALLTHROUGH from a different
      `ld a,N`** — `ee_raise` (A=5), `sid_raise`/`exf_raise`/`gp_raise` (61),
      `tm_raise` (24) — so each needs a 3 B `jp` to replace 3 B removed. Only
      `pl_parse_err` is free and its one caller is a `jr` that must widen.
      **DECLINED at 2 B.** 🔴 **A span is byte-identical without being ENTERED
      the same way**; the sweep cannot see this and says so.
      🎚️ BUDGET — 2 B carve family
      ~~🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).~~ (re-marked 2026-09-10, see below)
      🎯 **RULED (Joost, 2026-09-10): carve freely under the standing ≤20 B rule.** BUDGET;
      picked when a keyword tier needs the bytes.
      🤖 AUTONOMOUS — a carve under the standing rule (ruled 2026-09-10).
