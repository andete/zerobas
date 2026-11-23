- [ ] **2-Tier2-a — DOS boot (steps 4–7).** Deeper than first scoped: a build attempt
      proved the boot is a **four-step environment hand-off** (MSX2 TH ch.3), not a
      one-call bridge — see [`provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md) §8.
      🎚️ OTHER — DOS Tier-2
      ⛔ BLOCKED — neither of us can start it now (needs a fixture).
      - [x] **a1 — steps 4–5 (boot bridge). DONE + regression-gated.** `boot_disk` in
            INIT reads sector 0 → `$C000`, checks the `$EB`/`$E9` signature, and `CALL
            $C01E` CY-reset; the data-disk `RET NC` fall-through is preserved. **Now
            committed to `disk.asm`** (not reverted): regression-gated on
            `C-BIOS_MSX1_BASIC_DISK` + `test720.dsk` — `disk_probe_files` and
            `disk_probe_bload_disk` both PASS (BASIC+disk boots, byte-identical FILES,
            BLOAD `,R`/plain), and oracle-confirmed on `National_CF-3300_ZEROBASDISK` +
            a DOS disk (`$C01E` reached, `AF=$EBAC` ⇒ A=`$EB`, carry reset).
      - [ ] **a2 — step 6 (the real work): page-0 MSX-DOS environment.** Designed:
            see [`provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md) §8.1
            (documented page-0 layout pinned + the step-5→7 RAM-in-page-0 delta
            traced). Order: (1) page RAM into page 0 (slot paging — the hang-prone
            part, validate in isolation); (2) lay the page-0 env per the CP/M-style
            layout (`$0000` warm-boot, `$0005`→a trampoline to our existing
            **`bdos_entry`**, `$0006-7` TPA top, `$0038` int, `$0080` DMA); (3) the
            two-phase `$C01E`. **Reuse:** `bdos_entry` (oracle-validated MSX-DOS-1 FCB
            BDOS) IS the resident BDOS — don't rebuild it. **Open Q (resolve by
            experiment, not by tracing the MS boot code):** does the boot code load
            MSXDOS.SYS via `$0005` BDOS or via direct PHYDIO sector reads?
            **(1) is VALIDATED** (§8.2): the RAM-into-page-0 slot dance works on the live
            Tier-1 machine (`$A8` page-0→slot 3 + `$FFFF` page-0 subslot→0, run from
            page 1, `di`; wrote/read `$A5` at `$0000`, ROM `$F3` restored after).
            **Open Q RESOLVED** (§8.3): the boot loads MSXDOS.SYS by **direct sector
            reads, NOT `$0005` BDOS** (the first BDOS calls come from already-relocated
            high-RAM DOS, not the boot sector) → no resident-BDOS/TPA needed.
            **Real core of step 6 found** (§8.4): with RAM in page 0, `H.PHYD`'s
            `RST 30h`/CALLF breaks (page-0 BIOS gone), so step 6 must stand up a minimal
            RAM-resident inter-slot path. **Advantage:** page 1 stays our ROM, so DSKIO
            is directly `CALL $4010`-able — next build = a tiny `$0030` CALLF shim in RAM
            page 0 + the two-phase `$C01E`, then observe whether `A>` appears.
            **First full build done + reverted** (§8.5): the DOS boot path now RUNS
            (both `$C01E` calls reached, RAM in page 0, code executes in page-0 RAM,
            screen "MSX system version 1.0" not the BASIC fall-through). Two concrete
            gaps remain: **(A) CHARACTERISED (§8.6):** a black-box trace of the *working*
            CF-3300 boot shows it **does** reach standard DSKIO (`$4010`, 5×) via a *full*
            page-0 `JP`-vector table (`$000C`/`$001C`/`$0024`/`$0030`/`$0038`). Our build
            hung at `$1418` *before* the DSKIO call because our minimal env (`$0030` shim +
            `$0038` stub) lacked a vector the boot calls. Fix: lay the fuller vector set
            (shape per TH ch.3, our own RAM targets), disk path via `$0030`→direct `CALL
            $4010` (our ROM stays in page 1). Residual: trap which vector fires at `$1418`
            in the next bridge build. **(B) RESOLVED + VALIDATED:**
            the paging hardcoded "RAM = slot 3-0" (`or $03`/`and $FC`) — broke the C-BIOS
            host; corrected to **derive the RAM slot from page 3's bits** (`$A8`/`$FFFF`
            bits 7-6 → page-0 bits). `page0_ram_in`/`page0_ram_out` are now in `disk.asm`,
            **self-tested on `C-BIOS_MSX1_BASIC_DISK`** (the previously-hanging host):
            `$0000` accepts `$A5` after RAM-in, reads `$F3` after restore, machine running
            (§8.2). Routines committed but uncalled; **step 6 wires them in next.**
            **STEP 6 BUILT + regression-green (§8.7).** The `$0030` CALLF handler (register-
            preserving → direct `CALL $4010`), the `lay_page0_env` JP-vector set
            (`$000C`/`$0014`/`$001C`/`$0024`/`$0030`/`$0038` → our own page-1 handlers),
            and the step-6/7 wiring (`di`→`page0_ram_in`→`lay_page0_env`→`scf`→step-7
            `$C01E`→ data-disk return → `page0_ram_out`→`ei`→BASIC) are in `disk.asm`.
            `disk_probe_files` + `disk_probe_bload_disk` PASS on `C-BIOS_MSX1_BASIC_DISK`
            (step 6 paging runs there: sig `$EB`, `$1E` stub `D0 C9`); `disk_probe_init`
            PASS (`bdos_entry` now `$439F`). a3 trap verified the env is laid correctly at
            step-7 entry — **but REFUTED the §8.4 inter-slot premise** (§8.7): the real
            MSX-DOS boot uses **none** of H.PHYD / DSKIO / our page-0 vectors / our ROM
            header; it expects the standard **disk WORK AREA** (`DRVTBL` + driver slot/entry)
            and, absent it, falls back to a slot scan that wedges on the expanded slot 3.
            ⛔ BLOCKED — inherits `2-Tier2-a`'s own ⛔ (the no-disassembly wall). Stated here rather than left implicit: `tools/tier_table.py` warns on a NESTED open checkbox carrying no tier and no marker, because a keyword such an item names cannot be certified `no known gap` — and a warning that fires on items whose status is merely UNWRITTEN is noise that hides the case it exists for.
      - [ ] **a3 — SIZED by black-box differential = charter-level subsystem (§8.8).** A
            clean-room RAM differential (stock CF-3300 vs Tier-1, data disk → BASIC) shows
            the base BIOS sets only `EXPTBL`; the **disk ROM** installs `RAMAD0-3`
            (`83 00 83 83` stock vs **`FF` ours**), the `$F348` disk work-area/DRVTBL JP
            table (into high-RAM `$95xx/$DFxx`), the `$FE/$FF` DOS hook set, per-drive DPBs,
            and the device table — all absent in ours. Those targets are a **resident DOS
            kernel the stock relocates into high RAM**, i.e. the opaque proprietary code the
            clean-room rule forbids. ⇒ DOS-boot = build the disk ROM's full resident DOS
            environment, a multi-slice Phase-2+ effort that abuts the no-disassembly wall.
            **REOPENED + progressing (2026-06-22, §8.9) — §8.8 pessimism refuted.** The boot
            drives our OWN `bdos_entry`, not a rebuilt kernel. **Slice-1 DONE + committed**
            (`f1035a0`): `$F37D` is the disk system's BDOS-call JP vector (the boot calls it
            with C=$0F Open, DE=FCB "MSXDOS  SYS"); INIT had written a raw word there → the
            `$0038` wedge. INIT now publishes `$F37D` = `JP bdos_entry` (safe — Phase-1.5
            loader no longer reads it). Wedge gone; boot reaches bdos_entry/Open/fat_mount,
            finds MSXDOS.SYS. Regression-green (files+bload_disk+init on C-BIOS; bdos oracle
            PASS via `$F37E`). **Slice-3 (next):** the boot loads MSXDOS.SYS via BDOS **`$27`
            (Random Block Read)**, which `bdos_entry` doesn't implement (returns `$FF`) →
            implement it (DE=FCB, HL=rec count, start=FCB random-record `+33`, recsize `+14`,
            read into DTA), validate via a `$27` case in `disk_probe_bdos.py`, re-trap. The
            whole remaining gap to `A>` is that one BDOS function.
            **Slices 3–4 DONE; gap relocated to disk-ROM entry `$4030` (§8.10/§8.11), then
            mis-declared "walled by policy" (§8.12) — that verdict is RETRACTED (§8.13).** The
            §8.12 wall conflated *no published doc* with *no allowed method*: it forgot the
            project's core discipline, **black-box oracle observation** (how undocumented GETDPB
            was nailed byte-identical). `$4030` is the same kind of undocumented disk-ROM entry,
            characterisable as a black box on the genuine CF-3300 and reimplementable from the
            observed contract — no charter change, and **not** writing our own MSX-DOS 1.
            **Oracle built + first contract captured (2026-06-23, `probes/disk/disk_probe_dosboot_4030.py`):**
            deterministic — `$4030` returns a pointer in `HL` (`$F1C9`→`$DD0E`), preserves
            AF/BC/DE/IX/IY, writes nothing in `$F1xx`; on entry `IX` points at drive A's DPB
            (byte-identical to our CF-3300 GETDPB), confirming the disk-driver context.
            **`$4030` IMPLEMENTED + work-area characterised (§8.13-8.15).** Boot drives our
            BDOS, loads MSXDOS.SYS byte-perfect, consumes the `$4030` pointer; derailed at `$0038`.
            **RAMAD0-3 lever found + fixed (2026-06-23, §8.16; `disk_probe_dosboot_lowstore.py`).**
            §8.15's "work-area-layout" theory was REFUTED by oracle (MSXDOS makes 0 post-`$4030`
            low-storage writes; `$0038→$0C3C`, not the work area). The real lever: the Tier-1 vs
            stock differential showed page 0 = all `$FF` (unmapped slot) → `$0038` `RST 38h` wedge,
            because MSXDOS reads **RAMAD0-3 (`$F341-4`, 84×)** to re-page page-0 RAM and the disk
            ROM's INIT (ours) never set it. `set_ramad` (host-adaptive, `$FF`-gated, C-BIOS-safe)
            now sets it `83 83 83 83` = byte-identical to stock; **page-0 RAM maps and MSXDOS
            installs its BDOS (`$0005→$E106`)** — a real advance. `bdos_entry`→`$43EA`; regression
            green (init/files/bload/dskio). **Next gap PINNED (§8.17):** after RAMAD, MSXDOS.SYS's
            init does **`CALL $F368`** — a fixed disk-work-area **jump table** (`$F368-$F37C`, stock:
            `$F368→JP $DF57`, `$F36B→$DF59`, `$F36E→$DF70`, `$F371→$F327`, `$F374→$F32C`,
            `$F37D→SYSTEM`) the disk ROM builds; ours has only RAMAD + `$F37D`, so `$F368` is `$FF`
            and the call slides through `$FF` (`RST 38h`). (The apparent "interrupt storm" was a
            SYMPTOM of that slide — `int_h` clears the VDP fine, the FDC is idle; §8.16's ISR guess
            was refuted.) See §8.17.
            **`$F368` TABLE BUILT (§8.18, `disk_probe_dosboot_f368.py`).** Profile: only `$F368`
            (32×) + `$F36B` (31×) are called (IX=drive-A DPB); both are **no-ops on this 64K
            machine** (register/flag-transparent, zero mem/FDC/I/O effects — the disk system's
            RAM-segment-switch hooks, no-op without a mapper). `build_wa_table` lays `JP wa_stub`
            (a `RET`) into `$F368-$F37A` (gated like `set_ramad`; `$F37D`=SYSTEM left intact).
            `bdos_entry`→`$43FB`; regression-green. **Result — biggest advance yet:** the slide is
            gone, MSXDOS.SYS runs its init and is caught **executing inside our disk driver**
            (`PC=$431x/$436x`, `SP=$C004`) reading the directory — stack holds `"VOL_ID"`. **New gap
            (next):** a downstream **stack-corruption derail** — MSXDOS reaches `$4010` once with
            garbage args (`Cy=1`, `B=232`, `DE=$E880`) because `SP` points into ASCII data, not a
            stack. See §8.18.
            **ROOT CAUSE FOUND (§8.19) = HIGH-RAM COLLISION.** The derail is a `RST 38h` slide at
            `$8004` reached via a corrupted stack: `SP=$E6FE` points into MSXDOS.SYS's relocated
            kernel jump table at `$E700+`. MSXDOS's kernel sits at `$E1xx-$E7xx` (BDOS `$E106`),
            **overlapping our disk-ROM scratch** (`SECTOR_BUF $E2A0`, `WBUF $E560`, `GETWRK_AREA
            $E780`). The stock avoids it by reserving high RAM (`HIMEM $FC4A=$DF93`, work area
            `$DD0E`); ours never reserves, so MSXDOS relocates up into our scratch → collision.
            **Lever narrowed (§8.20): NOT HIMEM.** Stock BDOS base (`$0005`) = `$D606`, ours =
            `$E106` — differ by exactly `$1000` (4KB). Setting `HIMEM=$DF93` did NOT move the kernel
            (and regressed the boot) → reverted. MSXDOS-1 reads some other top-of-RAM source `$1000`
            higher on our host. See §8.20.
            **CONCRETE LEVER FOUND (§8.21).** A no-disk VG-8020 control confirms our disk ROM does
            **zero** high-RAM reservation (HIMEM `$F380` = the no-disk baseline; stock reserves to
            `$F1BF`/`$DF93`) — the `$1000` is the disk resident footprint we under-reserve. And the
            decisive find: **MSXDOS.SYS reads the `$F348` DRVTBL 208×** after `$4030`, but **ours is
            unbuilt/garbage**, so MSXDOS dispatches disk ops through garbage pointers → the bad jumps
            (the `$8004` slide = a garbage `$95xx`→`$80xx` driver pointer). Stock DRVTBL =
            `87 93df 0edd 95ef..95f1` = slot id | HIMEM top | `$4030` work area | driver-routine
            pointers. **Resume:** build the `$F368`-style `$F348` DRVTBL — slot `$87`, reserved-top +
            `$4030` ptr, driver pointers aimed at OUR `$4010-$401F` entries (never the stock `$95xx`
            kernel); reserve the high RAM alongside; re-trap. This is §8.8's table, now a confirmed
            live dependency — data + pointers to code we have, not a kernel to write. See §8.21.
            **DRVTBL FULLY CHARACTERISED (§8.22, probe `disk_probe_dosboot_drvtbl.py`).** Corrected
            layout: `$95` is the *low* byte — driver pointers are `$EF95/$ED95/$EB95/$F195`, evenly
            `$0200`-spaced and **all above HIMEM `$DF93` in page 3 (always-mapped RAM)**. Decisive
            write-watch: **the disk ROM builds the whole table** (every meaningful write from page 1
            `$453D-$5EAE`; MSXDOS never writes it; reader is one routine at `$0368`, hot field `+5`
            `$EF95`). The pointers are **always-mapped high-RAM trampolines** that CALSLT (slot `$87`)
            into the `$4010` BIOS — needed because under DOS page 1 is the TPA, so `$4xxx` isn't
            directly callable; this IS the `$1000` reservation's purpose. **Build spec:** in INIT,
            under the `$FF` gate — (1) reserve high RAM (lower HIMEM, claim a page-3 block); (2) build
            CALSLT trampolines there, one per driver routine, into our `$4010-$401F`; (3) write `$F348`
            = slot id | reserved-top | `$4030` ptr | trampoline addrs | sentinel. Next micro-step:
            map each trampoline → its `$401x` entry (trap the CALSLT target per pointer), then build.
            **BUILT + COMMITTED (§8.23): `build_drvtbl` in INIT (4 CALLF trampolines @`$E800` +
            the `$F348` DRVTBL), `$FF`-gated, regression-green; bdos_entry `$43FB`→`$4453`.
            VALIDATED CONSUMED** — Tier-1 MSXDOS reads our `$F348` 37× from PC `$0368` (the stock's
            reader). **But NEGATIVE: reserved-top in DRVTBL+1 does NOT move the kernel** — BDOS stays
            `$E106` (stock `$D606`); the §8.19/§8.20 `$1000` collision persists. Derail re-measured:
            the `$0038` wedge is GONE (set_ramad/`$F368`); MSXDOS now re-enables ints (idle in our
            `int_h`) but the main thread runs away to `$FFFF` (98.7% of int samples) — garbage-RET
            from the `$E106` kernel overlapping our `$E2A0-$E780` scratch. **NEXT LEVER: find MSXDOS-1's
            real top-of-RAM source** — trap the stock's kernel-base computation (where it derives
            `$D606`) for the cell/probe it reads, then set it on ours. Strong candidate: a RAM-size
            probe skewed by our ROM's page-2 `$FF` ($8000-$BFFF) vs the stock disk ROM's mapped
            content. (Trampolines built but not yet exercised; their `$401x` mapping unverified until
            the collision clears.) See §8.23.
            **KERNEL LEVER FOUND + FIXED (§8.24, probe `disk_probe_dosboot_ramtop.py`).** Black-box
            differential of the `$0006-7` BDOS-base write: stock `LD ($0006),HL`@`$D7C0` HL=`$D606`
            DE=`$DC80`; Tier-1 same routine @`$E2C0` HL=`$E106` DE=`$E780`. **Invariant DE−HL=`$067A`
            on both** ⇒ `$067A` = kernel size, **DE = kernel TOP = the `$4030` work-area pointer
            (DRVTBL+3)** — so DRVTBL+3 is the lever, NOT DRVTBL+1/HIMEM. (Real gap is `$0B00`, not the
            `$1000` §8.20 mis-arithmetic'd.) **Fix = one equate: `GETWRK_AREA $E780→$DD0E`** (stock
            value); kernel now relocates to **`$D606`, byte-identical to stock**, below our `$E29A`
            scratch. Equate-only, `bdos_entry` stays `$4453`, C-BIOS regression green. **Validated:**
            `final_bdos=c306d6`, `$FFFF`-runaway GONE, boot reads disk heavily through our driver
            (64× `$4030`, 24 open, 37 RDBLK), gets through the MSX banner. **NEXT GAP: a re-init /
            warm-boot spin** — BDOS vector re-published 6× (stock: once); DOS loads but loops before
            `A>`. Characterise what fails between publications (COMMAND.COM load/exec or a disk op
            erroring → warm-boot); trampolines now finally reachable. See §8.24.
            **SPIN ROOT-CAUSED (§8.25, probe `disk_probe_dosboot_reinit.py`).** After a clean
            publication the kernel does `CALL $50A9` (page 1) on BOTH machines (identical regs,
            identical `ppi $A8=$FF` — page-1 slot-3 RAM, NOT corruption). Stock `$50A9` = real
            MSXDOS.SYS loader (boots, publishes once); Tier-1 `$50A9` = **all zeros** → NOP-slide
            crash → warm-boot loop (publishes 6×). No real DSKIO ever fires (crash precedes the first
            sector read). **Root: MSXDOS.SYS's page-1 portion (`$4000+`) was never written to RAM
            during our DOS-boot bridge** — page 1 held our disk ROM during the load, so the upper
            sectors went to ROM / were discarded; the kernel's `$50A9` continuation is empty. The
            page-1 analog of the §8.16 page-0 RAMAD fix. **NEXT: the boot bridge must map page-1 RAM
            (not our ROM) while storing the loaded MSXDOS.SYS**, so `$50A9` holds its loader when the
            kernel calls it. See §8.25.
            ⛔ BLOCKED — inherits `2-Tier2-a`'s own ⛔ (the no-disassembly wall).
            Stated here rather than left implicit, for the reason a2 above gives.
