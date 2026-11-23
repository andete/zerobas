- [x] ⚠️ **FIVE MORE NON-ATOMIC PUBLISHES INTO THE SHARED openMSX TREE, AND NO
      GATE WOULD SEE A SIXTH.** Filed 2026-08-26 by D-MACHXML
      ([`docs/spec-probe-machxml.md`](../../docs/spec-probe-machxml.md)), which fixed
      the one that FIRED. `tools/install-openmsx-machine.py`:379/392/401/440/455
      all publish with `open(out, "w").write(...)` into
      `~/.openMSX/share/{machines,extensions}` — the same truncate-then-write
      window, **measured at 34.3 % of concurrent reads torn**
      (`scratchpad/machxml_repro.py`).
      🟢 **THEY ARE OFF THE HOT PATH, AND THAT IS MEASURED NOT ASSUMED**: they
      are reached only from `machines` / `machines-oracle`, and the Makefile's
      own comment says *"`machines` is the RELEASE-INSTALL path, not a gate
      path"*. The one that fired, `install-repack-machine.py`, is a prerequisite
      of **112 targets** that `make gates` runs in parallel. So this is a real
      but cold instance of a hot class.
      ✅ **FIXED 2026-08-26 — ALL SIX PUBLISH SITES NOW GO THROUGH ONE HELPER,
      `openmsx_paths.publish()`.** The cure sits beside `find_user()` because
      the module that knows where the shared tree IS should know how to write
      into it; `install-repack-machine.py`'s inline copy was folded in too, so
      the mechanism and its 34.3 %-torn measurement are documented at **one**
      site rather than six. **Verified, not assumed**: `make repack-machine`
      publishes an XML that parses and leaves no `.tmp`, and the five rewritten
      sites were driven with `--user` pointed at a scratch tree —
      **5 XML files, all parse, no `.tmp`** — so the release-install path was
      exercised without touching the real `~/.openMSX`.
      🔴 **THE CHECKER IS STILL OPEN, AND IT IS NOW TRACTABLE.** The filed
      obstacle was the DENOMINATOR: the destination is built by
      `openmsx_paths.find_user()` at runtime, so a textual sweep cannot resolve
      it. `publish()` sidesteps that — the rule no longer needs to resolve a
      path, it needs a **file set**: within `tools/install-*.py` and
      `openmsx_paths.py`, any `open(..., "w")` outside `publish()` itself is the
      finding. That denominator is small, complete and statable.
      ✅ **CHECKER SHIPPED 2026-08-26 as rule PUBLISH of `make chokepoint-check`**
      ([`docs/spec-chokepoint-gate.md`](../../docs/spec-chokepoint-gate.md)) — one gate
      for three items, because they were one property. Denominator **3 files**.
      🔴 Its first cut reddened `openmsx_paths.py` **twice, on the COMMENT that
      explains why the raw call is forbidden** — a regex cannot tell code from
      prose ABOUT code, and a file documenting a chokepoint is the likeliest
      place to contain its own subject. AST now.
      ✅ **DONE** — both halves.
