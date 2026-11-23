- [ ] 🏗️ **JOOST RULED 2026-09-17: EVERY HOOK-IMPLEMENTABLE KEYWORD MUST USE ITS
      HOOK, AND EVERY DISK COMMAND'S IMPLEMENTATION BELONGS IN `disk.rom`
      BEHIND IT — NO EXCEPTIONS.**
      🎚️ STANDING — a ruling, not a task; the tasks it creates are listed below.
      🤖 AUTONOMOUS — the ruling is given; each step below is ordinary work.
      Verbatim, in three messages: *"every one of the hook implementable
      keywords must use its hook obviously"*; *"any keyword implemented by the
      disk rom should go via the hook to the disk rom"*; and of `MKI$`'s filed
      exemption, *"perhaps we need to work around this; all disk commands need
      to be in the disk rom"*. The reason is COMPATIBILITY, in his words:
      without the hook *"we would be incompatible with the reference"* — a
      third-party extension ROM that claims a cell is never reached.
      🟢 **THE HOOK HALF IS ALREADY DONE, MEASURED 2026-09-17: all 16 verb hooks
      ARE consulted.** ⚠️ And the first measurement said four were not —
      `H_DSKI` `H_DSKO` `H_LSET` `H_RSET` — because it grepped `ld hl,H_*`, and
      those four load the cell through **DE** (`basic/field.asm:492`, HL being
      the statement cursor). 🔴 **A GREP THAT ASSUMES ONE SPELLING IS NOT A
      MEASUREMENT** — the inverse of [[a-shared-tail-is-not-a-decision]]'s "grep
      instructions, not the symbol". `H_TIMI`/`H_ZKEY` are inbound (we install
      into them) and `H_ERRP` offers outward, so they are not verb offers.
      📏 **WHAT REMAINS IS THE BODY HALF.** Six bodies already live in
      `disk.rom` behind their hook — `hk_mkfloat` (`MKS$`/`MKD$`), `hk_name`,
      `hk_kill`, `hk_files` (`FILES`+`LFILES`), `hk_copy`, `hk_errp` — and ten
      cells are gate-only with the body main-side (`disk/kernel.asm:2250`).
      The cluster to move: **`MKI$` `DSKF` `CVI` `CVS` `CVD` `LSET` `RSET`
      `FIELD`** (`DSKI$`/`DSKO$` bodies are already a sub-ROM tenant).
      🔴 **CORRECTION 2026-09-17, SAME DAY: "THE PRICE IS NOT ON THE CRITICAL
      PATH" AND "ALL SIX MOVED BODIES DID IT WITH NO DISK→BASIC CALL" ARE BOTH
      FALSE, AND I WROTE THEM HERE.** `calbak` (`disk/kernel.asm:2362`) is
      `ld iy,(EXPTBL-1) / jp CALSLT` and stands at **19 call sites**, reaching
      six PAGE-1 targets declared in `gen_resident_abi.py`'s CALLBACK list —
      `fname_expr` `$6E72`, `pdfcb_resume`, `dirverb_op`, `main_fat_mount`,
      `main_fat_find`, `parse_disk_fcb`. Its ABI is MEASURED two-sided
      (D-XSLOTABI: HL/DE/BC/A and CF all cross both ways). 🎯 **I REPEATED A
      STALE NOTE INSTEAD OF CHECKING** — the loop prompt's, and the generator's
      own paragraph saying that list was "empty today" while it held six names.
      **SO `FIELD`/`LSET`/`RSET` ARE NOT BLOCKED ON AN UNPRICED MECHANISM**;
      they call back like the others. What remains below is still true:
      all six moved bodies ALSO reach main's LOW REGION directly, which is
      cheaper than a call-back and is why most of them need one rarely: `disk.rom` is a PAGE-1 ROM, so while it is mapped, page 0 still
      holds slot 0 and main's **LOW REGION is callable by absolute address**
      (every code address in `disk/basic-resident-abi.inc` is below `$4000` —
      `$38DC` `$3417` `$33BD` — the rest are RAM cells, and `make
      diskrom-abi-check` regenerates them per build). So the per-verb question
      is only whether the helpers a body needs sit in the low region or in page
      1; a page-1 helper is a **promotion** (`scratchpad/promote_scout.py`,
      1:1, free), not a blocker. `str_eval $49EE` / `var_find_typed $4853`
      become the gate ONLY if we decide the disk side should parse its own
      arguments the way the reference does — and we do not need that for
      compatibility, because our main-side parse produces the same observable
      errors D-CFARCH measured (`FILES 5` → ERR 13, not ERR 2).
      💰 **THE ECONOMICS INVERT, WHICH IS WHY THIS OUTRANKS CARVING.** A carve
      returns ~12 B at a time ([[carve-routes-measured-shut]]); moving a verb
      body out of the main image returns its WHOLE SIZE, into a region that had
      8490 B free in 32 runs on 2026-09-17 against main page 1's 38 B.
      🔑 **THE ABI IS ALREADY WRITTEN AND IT ANSWERS THE `MKI$` EXEMPTION**:
      `hk_mkfloat`'s header says *"EVERYTHING CROSSES IN RAM, NOT IN
      REGISTERS"*. `MKI$`'s filed reason — *"needs DE, which does not survive
      CALSLT"* — is a register-lifetime argument, and RAM is the answer this
      ABI already gives to register lifetime.
      ✅ **`MKI$` DONE 2026-09-17 (D-MKINT), +13 B** — its exemption described
      MARSHALLING, not implementation; the conversion is the identity, so
      `hk_present` was already truthful and `ld (STRSCR+1),de` replaced an
      eight-byte hand-written store.
      ✅ **`CVI`/`CVS`/`CVD` DONE 2026-09-17 (D-CVMOVE), +14 B** (page 1 51 → 65,
      `disk.rom` 8490 → 8452 B) — and this one was a COMPATIBILITY FIX, not a
      carve: main ran the whole conversion after the hook returned REGARDLESS of
      whether it was claimed, so a foreign disk ROM's answer was overwritten on
      the way out. 🔴 **THAT IS TRUE OF ALL TEN GATE-ONLY CELLS** — the hook is
      offered as a PRESENCE TEST and the work is redone main-side — so each
      remaining verb is the same fix rather than a fresh judgement.
      🔴 **AND THE FIRST CUT OF D-CVMOVE MARSHALLED THROUGH `STRSCR`, WHICH IS
      WHERE `MKI$`/`MKS$`/`MKD$` STAGE THEIR RESULT.** `CVI(MKI$(258))` hands the
      body a string whose body IS `STRSCR+1`, so the pointer wrote over the value
      being converted: **12 of 32 rows DIFF**, and the 20 that stayed green were
      the arguments that are not staged strings. **A ROUND TRIP IS WHERE A SHARED
      SCRATCH BUFFER ALIASES ITSELF**, and it is the case these verbs exist for.
      The fix REMOVED the marshalling instead of moving it: the width rides
      `FACTYP` (the width IS the FACTYP code) and the body derefs `STRPTR`
      itself via `pu_deref_body`, already at `$28C1` in the low region. 🎯 **SO
      BEFORE MARSHALLING ANYTHING, ASK WHETHER IT IS ALREADY IN RAM OR ALREADY
      BELOW `$4000`** — for these three it was both, and the marshalling was pure
      risk. Declared in `tools/gen_resident_abi.py`'s checked lists, which is
      what that file is for.
      🟢 **A PAGE-1 HELPER IS USUALLY NOT A BLOCKER**: `flt_int_result` was one
      instruction's worth of work (`FACTYP := 2`) and VANISHED rather than
      moving. Only a substantial helper — `fat_count_free`, the channel engine —
      forces the promote-or-call-back decision.
      ✅ **`DSKF` DONE 2026-09-17 (D-DSKFMOVE), +4 B** (page 1 65 → 69,
      `disk.rom` 8452 → 8415 B) — identical to the CF-3300 on all six drive
      points (0 and 1 answer 706; 3, 4, 8, 9 `Bad drive name`). The drive
      argument crosses in RAM because `chan_gate` clobbers `DE`, and the `IY`
      guard moved from the count to the GATE, because the count now runs inside
      the handler. ⚠️ The COUNT is still a call-back: `fat_count_free` is a 13 B
      stub onto the SUB ROM's `fatprim` tenant, so the walk is in neither ROM
      the call crosses between — that is the eviction spec's step 5, not this
      verb's business.
      📋 **AND THE WHOLE DIRECTION NOW HAS A SPEC, RULED BY JOOST 2026-09-17**
      (*"there should probably be hardly any disk code left in the main Rom"*):
      [`disk/docs/spec-diskcode-eviction.md`](../../disk/docs/spec-diskcode-eviction.md).
      **Measured 2026-09-17: 2394 B left page 1** if the six disk-only files
      move — 250 B
      of that is INTERFACE that must stay (the parse, the raise, the channel
      readers, cold-boot init) and **2144 B is private**, against 69 B free on
      2026-09-17. ⚠️ `disk.rom`'s 8415 B is **fragmented into 32 runs** by pinned
      kernel addresses; the largest is 2777 B, so the bulk fits ONCE and nothing
      else does. The spec carries the eight rules each of today's three moves
      paid for, the diskless obligation (D-NODISKGAP: one entry, and it is the
      gate), and what it does NOT claim.
      🏗️ **RE-FRAMED BY JOOST 2026-09-18 — READ spec §0.0 BEFORE ANY OF THE
      ORDER BELOW.** *"Lets consider main + sub our replacement of reference
      main; the end result should be similar to the reference both for with disk
      and without disk."* Three consequences: (1) `sub.rom`'s ~4.8 KB of
      disk-only tenants are IN SCOPE — sub is ours, so disk implementation there
      is as misplaced as in main; (2) **there must be NO diskless build** — the
      reference ships ONE BASIC ROM for both machines, so the same-ROM
      slot-3-1-empty arrangement we already have is the faithful one and a
      `DISK_RESIDENT` switch was WITHDRAWN after being recommended; (3) the
      target becomes checkable — *no disk-implementation symbol reachable in
      main+sub* is an invariant a gate can hold.
      🏗️ **AND ONE FAT12 ENGINE, NOT TWO (Joost, same day)**: *"we'd obviously
      don't want two FAT12 engines; if needed we need to parametrize where it has
      its buf"*. 🟢 The two control blocks are ALREADY byte-identical in layout
      (only the base differs, `$E4A0` vs `$E9C0`), so parametrising is a base
      change. 🔬 **BUT THE FIRST MEASUREMENT IS HIS OWN QUESTION** — *"unless
      bdos actually uses the same buf as disk basic, on the reference"* — which
      is BLACK-BOX observable through the debugger.
      🟢 **MEASURED 2026-09-18 (D-FATBUF, `scratchpad/fatbuf_probe.py`): THE
      REFERENCE KEEPS THEM SEPARATE.** After a chain walk on the CF-3300 FOUR
      regions are resident at once — file data at `$DD77` (256 B) and `$ED95`
      (512 B), FAT sector at `$E595` and `$EF95` (512 B each) — and the second
      pair is ADJACENT, 512 B of data immediately followed by 512 B of FAT. So
      our `FSECTOR_BUF`/`FWBUF` split is **not** our invention; the reference
      does the same. The one-engine plan therefore does not collapse to a single
      buffer — it must ADDRESS TWO, which is exactly the parameter §0.1 asks for,
      and the byte-identical control-block layout is what makes it cheap.
      ⚠️ **NARROWER THAN JOOST'S QUESTION**: this measures file-data vs FAT
      WITHIN Disk BASIC's file I/O. Whether BDOS shares those regions is
      unattributed — the probe reads which bytes are resident, never which
      routine wrote them. The two extra regions are unexplained.
      🔴 **AND THE INSTRUMENT TOOK EIGHT CORRECTIONS, EVERY FAILURE PLAUSIBLE**
      (spec §0.1a lists them). The one that ended it: stop hand-rolling keyboard
      injection and drive `probes/lib/omsx_repl.py`, which had already solved all
      five typing defects — `$` substitution, the boot date prompt, SCREEN 1
      geometry, dropped characters, a lost CR. **A probe that types its own keys
      is re-deriving a solved problem.**
      🟢 **STEP 7 ALSO MEASURED 2026-09-18 (D-SEQIO, `scratchpad/seqio_stopwatch.py`)
      AND IT INVERTS THE ASSUMPTION §6.3 WAS BUILT ON.** Per byte of sequential
      file input, normalised against each machine's own calibration loop so the
      50/60 Hz tick difference cancels: the **CF-3300 spends 2.66 empty-loop
      iterations per byte, zerobas 0.14** — we are **20× faster per byte**, on a
      tree otherwise 2.5–3.8× SLOWER at interpretation. In ms: 4.297 vs 0.703.
      Adding one inter-slot crossing per byte to our path gives 0.859 ms/byte,
      still **0.20× the reference**.
      ➡️ So step 11's loop duplication is **NOT FORCED** and step 12's `PRINT#`
      may cross per byte without being a regression.
      🔴 **BUT IT SETTLES STEPS 11 AND 12 ONLY, NOT STEP 9.** `INPUT#`/`INPUT$`/
      `PRINT#` pay a whole BASIC statement's worth of interpretation per byte,
      which is what a crossing hides behind. The tokenised `LOAD` loop runs
      INSIDE the ROM with no such overhead, so a crossing there is pure addition
      against nothing — **unmeasured, and not inferable from this table.**
      🔴 **AND THE SPEC HAS NOW BEEN WRONG ABOUT THE FAT LAYER THREE TIMES** —
      the order (step 5 as "the bulk": it is ~394 B, ~16 %), the blocker (§6.1
      listed three files that are `include`d only by `sub/`, and MISSED
      `input.asm:278`, which installs the per-byte `ARL_GETBYTE` RAM vector — the
      real pin is a VECTOR, not a call count), and the subject (§0.0). All three
      were caught by re-deriving from the tree, not by reading the document.
      ➡️ **ORDER:** ~~`MKI$`~~ ~~`CVI`/`CVS`/`CVD`~~ ~~`DSKF`~~ ~~`LSET`/`RSET`~~
      ~~`FIELD`~~ done — the channel trio is complete (D-LRSETMOVE, D-FIELDMOVE);
      then **spec §6.2's re-ordered list, which begins with TWO MEASUREMENTS and
      no code**; then the
      stub-extension rig, which is what makes
      every offer LOAD-BEARING — today `h.lset`/`h.rset` AGREE on the diskless
      target while the hook is bypassed, so agreement is not evidence the hook
      is honoured [[a-case-that-agrees-can-agree-for-the-wrong-reason]]; then
      the remaining six bodies; then the keywords with NO hook equate at all
      (`ATTR$`, `CALL`, and check `SET`/`IPL`/`CMD`), gated on identifying their
      cells among the 32 unidentified claimed ones.
      ⚠️ **`ATTR$` IS UNUSED IN PRACTICE (Joost, same day) AND STILL NEEDS ITS
      HOOK** — the hook is the compatibility surface, not the feature.
      ⚠️ **`CALL` IS MIS-AUTHORED AND THAT IS MY ERROR FROM D-AKCM (same day)**:
      `tools/kwforms.py` has it in `REFUSE_ONLY` with its form list `("refuse",)`,
      yet this tree IMPLEMENTS `CALL FORMAT` (`basic/format.asm:50`, bulk in
      `sub/format.asm`, tested by `probes/disk/diskbasic_probe_format.py`). Its
      real form is `format`. 🎯 **AND THE KNIFE'S `BLIND` VERDICT ON `CALL` WAS
      THE TRUE SIGNAL**: cutting `ex_call` cannot change `CALL FOO`'s ERR 2,
      because an unknown name errors either way — the knife was saying the row
      does not reach the code. A `CALL FORMAT` row IS cut-sensitive. Also:
      `ex_call` matches only `"FORMAT"` and otherwise `jp nc,stmt_error`, with
      **no offer to any other extension**, which is the same gap as `ATTR$`.
