- [ ] 🏗️ **D-PAGE2ISLAND — TENANTS MAPPED INTO PAGE 2 ($8000-$BFFF), FOR AUDITED
      TENANTS ONLY (ruled open 2026-10-11)**
      🎚️ BUDGET — supply, and only for a tenant that can prove its RAM footprint.
      🏗️ **RULED BY JOOST, 2026-10-11:** *"Open it for audited tenants"*. A
      tenant mapped into page 2 hides the BASIC program text, variables,
      arrays and strings while it runs, so each one needs its footprint proven
      to stay in page 3 (work area, stack) -- a write watchpoint over $8000-$BFFF
      across its gate rows, and a knife that plants one such access.
      🤖 **AUTONOMOUS** — when a candidate needs it; none is named yet. Do not
      re-ask whether page 2 is allowed.
      🅿️ **PARKED BY JOOST, 2026-10-11 (*"park"*): A ROM IN SLOT 0, PAGE 2.** The
      C-BIOS logo ROM holds slot 0 $8000-$BFFF (16 KB, used only to draw the boot
      logo). Code there is reached by a primary-slot write to port $A8 -- a few
      dozen T against a tenant CALSLT's ~0.9-1 k T (2026-10-11 estimates) -- so a
      page-2-safe tenant there would be cheaper AND roomier. Candidates named,
      unaudited: the math pack (FAC/ARG work cells are page 3), graphics inner
      loops (VRAM + work area), maybe number formatting; not PLAY's string
      (the string heap). Open checks if reopened: SP never below $C000 during
      such a call (else switch stacks), the ISR touches no page-2 RAM, a
      page-2 footprint audit per candidate, a trampoline in the low region
      (~15-20 B, estimated 2026-10-11). Do not pursue until Joost reopens it.
