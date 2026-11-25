- [x] 🔴 **`KEY n,"str"` AND `KEY LIST` ARE UNIMPLEMENTED — A WELL-FORMED
      STATEMENT IS `Syntax error` HERE AND SILENT ON BOTH REFERENCES.** Filed
      2026-08-26 by D-MISSOP3. `KEY1,"X"` reads **0 / 0 / 2**: both references
      complete it, zerobas refuses it. [`basic/screen.asm`](../../basic/screen.asm):294
      is `jp stmt_error` with the comment *"KEY <n>,\"str\" / KEY LIST
      unsupported"*, so `ex_key` handles only `KEY ON` / `KEY OFF` (plus the T3
      `KEY(n)` arming form).
      🔴 **IT WAS ALREADY WRITTEN DOWN, INSIDE A `- [x]` BLOCK, AND THEREFORE
      INVISIBLE** — TODO.md:15425 (T-529ABE), a Phase-1 entry ending *"all Phase-3 scope"*.
      That is the exact failure this section's own preamble exists to prevent,
      and it survived the 2026-08-09 staleness sweep because the sweep
      enumerated `- [ ]` items. `docs/kwsweep-msx1-coverage.md` cannot see it
      either: its scope claim is **reserved words only**, and it says so —
      *"a word can be present and still wrong in its third argument"*. So
      `make kwsweep` printing no `MISSING=` line is not evidence about this.
      🎯 **FOUND BY A CONTROL, NOT BY THE SUBJECT.** `r.keyok` was a
      throwaway well-formed row expected to be green on all three; the filed
      residual it sits next to (`KEY1,` reading ERR 2 where the references say
      24) is a SYMPTOM of the whole form being absent, and "fix the error code"
      would have been the wrong repair. Under the charter the reference wins.
      📏 **SCOUTED 2026-08-26 — D-KEYSTR,
      [`docs/spec-basic-keystr-scout.md`](../../docs/spec-basic-keystr-scout.md)**
      (`scratchpad/keystr_probe.py`, 6 rows x 3 machines, measurement only).
      The storage is MEASURED, not assumed: a distinctive plant (`KEY n,"ZQX"`)
      reads back at **base `$F87F`, stride 16, NUL-terminated**, with two
      controls making it a reading rather than a coincidence — planting slot 1
      and reading slot 2 returns `"auto"` (F2's default), and planting nothing
      returns `"colo"` (the head of F1's `"color "`).
      🔴 **AND THE GAP IS BIGGER THAN THIS ITEM SAYS: zerobas reads `0 0 0 0` AT
      EVERY SLOT WITH NOTHING PLANTED.** The references' DEFAULTS are present on
      a cold boot and zerobas's are not — so the function-key string area is
      **UNPOPULATED**, not merely unwritable, and `KEY ON` renders it. A fix
      that added only the parse and the copy would leave nine slots holding
      zeros where the reference holds `color `/`auto`/`goto`/`list`/…
      ⚠️ **SECOND REFRAMING OF THIS ITEM BY A CONTROL RATHER THAN ITS SUBJECT** —
      D-MISSOP3's `r.keyok` turned *"wrong error code"* into *"the form is
      absent"*; this scout's `k.none` turns that into *"the storage is empty
      too"*.
      ✅ **MEASURED AND PRICED 2026-09-04 — D-KEYSCOUT2**
      ([`docs/spec-basic-keystr-scout.md`](../../docs/spec-basic-keystr-scout.md),
      [`scratchpad/keylist_probe.py`](../../scratchpad/keylist_probe.py), 11 rows x 3
      machines). All three unmeasured things are now read off machines:
      • **the `n` domain is 1..10**, and `KEY 0,` / `KEY 11,` / `KEY -1,` are
        **ERR 5**; the empty string is legal. zerobas answers **ERR 2 to every
        form**, and the `A=1` control is green on all three, so that is a reading
        about zerobas and not about the program.
      • **truncation is 15**, measured (`KEY 1,"ABCDEFGHIJKLMNOPQRST"` lists back
        `ABCDEFGHIJKLMNO`) — it AGREES with the stride inference, but it is now a
        reading rather than a deduction from a memory map.
      • **`KEY LIST` works on both references** and is `Syntax error` here — and
        it is also the cheapest way to read the defaults: one row instead of
        forty PEEK rows over FNKSTR.
      🔴 **THE DEFAULTS ARE NOT UNIVERSAL, WHICH THIS ITEM DID NOT KNOW.** Slot
      **F6** is `color 15,4,4` on the VG-8020 and `color 15,4,7` on the CF-3300.
      zerobas has TWO official targets with different oracles, so "F6's default"
      is a per-target answer, not a constant.
      ⚠️ `KEY LIST` cannot show trailing spaces or a CR, and the real defaults
      have both (`color `, and a CR is what makes `run` execute). The first
      scout's PEEK read `"colo"` from `"color "`, consistent. So a packed figure
      is a LOWER bound and a straight 160-byte image sidesteps the question.
      💰 **PRICED: ~7 B of main page 1, everything else sub-side.** `ex_key` is
      at `$5AB8` — main page 1, the constrained region — but only the dispatch
      needs to live there: `jp stmt_error` (3 B) becomes `ld ix` / `call
      subrom_call` / `jp c,...` (~10 B). A page-0 tenant may call main page 1, so
      it can reach the expression evaluator (the D-PUSIGN / D-PUEMIT pattern).
      The 160-byte FNKSTR image plus ~120 B of parse/store/list code go in sub
      page 0. **Run `make basic-reloc` for the walls — do not quote this line.**
      ✅ **THE F6 QUESTION IS ANSWERED (Joost, 2026-09-04): "when there is
      stylish differences (color, screen) between the oracles, pick the VG8020".**
      So F6 ships **`color 15,4,4`** — the VG-8020 value — on **BOTH** targets,
      including the disk build whose oracle is otherwise the CF-3300. A cosmetic
      split does not fork the ROMs. This is a STANDING rule, not a one-off: see
      the "Settled decisions" note below.
      🔭 **ONLY THE IMPLEMENTATION DECISION IS LEFT** — whether to spend the ~7 B
      of main page 1 (read `make basic-reloc`; it was 8 B free 2026-09-04) plus
      the sub-side body. Everything the fix needs is measured.
      🎚️ TIER 1 — happy path: `KEY` — its `n,"str"` assignment form and its LIST form are MISSING (the keyword is KEY; LIST itself is fine)
      ~~🙋 NEEDS-JOOST — everything the fix needs is measured; what is left is a~~ (re-marked 2026-09-10, see below)
      main page-1 spend (the dated figure is on the 🔭 line above — read the wall
      with `make basic-reloc`, never from here), and spends are his. That 🔭 line
      said exactly this and was invisible to the old marker readout.
      🎯 **RULED (Joost, 2026-09-10): *"missing keywords obviously need to be implemented."*** TIER 1.
      ✅ **SHIPPED 2026-09-10 (D-KEYSTR) — BOTH FORMS WORK AND THE DEFAULTS ARE
      PRESENT AT COLD BOOT; 11 rows on all three machines agree
      (`make keystr-acceptance`, [`probes/basic/basic_probe_keystr.py`](../../probes/basic/basic_probe_keystr.py)).**
      The ten defaults are a MEASUREMENT ([`scratchpad/keydef_probe.py`](../../scratchpad/keydef_probe.py),
      all 160 bytes on both references; they differ only at F6, and the VG-8020
      value ships on both targets by the standing style ruling). Shape: a page-0
      tenant, `SUBROM_IDX_KEYSTR` = 18 ([`sub/keystr.asm`](../../sub/keystr.asm)) —
      the image, the store (cleared slot, truncated to the measured 15) and LIST
      rendered into `DETOKBUF` for the resident drain (the D-PUEMIT shape); the
      resident half is the parse. Cost from a clean tree: **main page 1 89 → 13 B
      (76 B)**, sub page 0 1100 → 820 B — well over the ~7 B this block priced,
      which counted the dispatch alone; D-PDFCBRESUME carved 20 B back the same
      hour.
      🔴 **THREE CUTS TO GET THERE, EACH CAUGHT BY THE GATE'S OWN CONTROL ROW:**
      the cold-boot copy sat ABOVE `init_ext_roms` and ran against power-on
      garbage in `SUBSLOT_OK` (the machine never reached the prompt); the tenant's
      `pchar` is the sub-side DETOKBUF appender, not the resident printer; and
      `fname_expr` stages `"`-terminated bytes without a length byte, so every
      store carried a trailing quote until the length was taken from the
      descriptor. `KEY LIST` renders control bytes as blanks — measured on both
      references (F10's `$0C` shows as a space; F5/F8/F9's CR and `$1E` vanish).
      ⚠️ And this filing is a commit LATER than the code: the shell chain that
      carried it died in a parse error before the edit ran, and the "closed" line
      I acted on had never been printed. Read the output; do not remember it.
      🤖 AUTONOMOUS — implement; the references settle the behaviour (ruled 2026-09-10).
