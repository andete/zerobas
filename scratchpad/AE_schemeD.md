# D-DISKROMHOST step 4 (d): scheme D, built

Built from the sizing in [AE_wasize.md](AE_wasize.md) and the step 4 ruling in
[todo/open/D-DISKROMHOST.md](../todo/open/D-DISKROMHOST.md): "match the references exactly on the outside, do better
inside". On 2026-11-26 the owner added a second ruling: publish SLTWRK as the references do.

No git operations were made. Raw outputs are the `scratchpad/AE_schemeD_*.out` files.

## Result

**A cartridge scanned before ours that claimed N bytes (HIMEM = `$F380 - N` at our INIT) no longer makes the disk ROM
decline for N ≤ 439.** zerobas installs as the CF-3300 does. Every cell stays at its address, and every published number
moves down by N:

* HIMEM at INIT (the H.RUNC entry), at MSX-DOS's start, at A> and in Disk BASIC;
* FRE, MEMSIZ and STKTOP;
* MSX-DOS's `$0006`;
* the `$4030` value and DRVTBL+1 / +3;
* the SLTWRK page-1 entry.

`make diskguard-acceptance` ([AE_schemeD_guard2.out](AE_schemeD_guard2.out)) has 10 rows: 8 are SAME as the CF-3300, and
the 2 at N = 440 are pinned as KNOWN.

* **Disk ROM: +59 B.** The wall tool's free total went from 583 to 515 B. That is 68 B, because the 9 B left of a 19 B
  hole fall under its 16-byte floor.
* **RAM: +2 B** (CLAIM_D).
* **NMAX = 439.**

## Method

1. The changes below, built with `rm -f build/disk.rom && make -s build/disk.rom`.
2. A claim-once test cartridge, `probes/disk/claimonce.asm`, and a rewritten `probes/disk/disk_probe_guard.py`. Each probe
   row boots zerobas's DISK machine and the CF-3300 at the same N, in two scenarios:
   * **DOS:** MSX-DOS 1 `test.dsk`, then `BASIC` typed at A>.
   * **DATA:** a blank 720 KB disk straight into Disk BASIC.
3. The probe reads RAM only:
   * HIMEM and SLTWRK at each H.RUNC entry, from a breakpoint on the RAM hook `$FECB`;
   * HIMEM at MSX-DOS's start, from a breakpoint on RAM `$0100` with page 0 not in slot 0;
   * HIMEM and `$0006` at A>, with `$0006` read from the RAM slot that RAMAD0 names, never through the CPU view, so no ROM
     byte is read;
   * at the end: HIMEM, FRE(0) and DSKF(0), which typed lines POKE to `$A000` / `$A002`; MEMSIZ, STKTOP, DRVTBL `$FB21-$FB22`,
     and every non-zero SLTWRK entry.

   No PC is recorded, and no ROM or RAM-resident code byte is read.
4. Reference readings go through `probe_refcache.cached_run`, with ZEROBAS_REFCACHE=refs as the default, so zerobas is
   measured on every run and the CF-3300 is replayed. The exit codes are 0 / 1 / 2. Instrument checks: the CF-3300 must
   install at every N, and must read HIMEM `$F195 - N` at its H.RUNC entry, which proves the cartridge claimed exactly N.
5. **A knife.** I built a temporary ROM in which INIT stores the fixed `$DD0E` and skips SLTWRK, ran the gate, then restored
   the source. Result: **8 of 8 SAME rows went RED** ([AE_schemeD_knife.out](AE_schemeD_knife.out)), each naming the fields
   that differ.
   * At N = 0 only SLTWRK differs. That is the subject of the new code.
   * At N = 16 / 300 / 439 the HIMEMs, FRE, MEMSIZ, STKTOP and SLTWRK differ, and `$0006` differs at N = 300.

## The changes, with their byte cost

**1. [disk/equates.inc](../disk/equates.inc): new cells and constants.**
* **CLAIM_D `$F1C6` (2 B), RAM only.** It lives in the INIT-private block below HOOK_SLOT. Nothing writes `$F195-$F1C7`
  through a DOS session, A>BASIC or a Disk BASIC write ([AE_claimuse_zb2.out](AE_claimuse_zb2.out)), and it lies below
  `$F1C9`, so no claim of N ≤ 439 reaches it.
* **The value I chose for CLAIM_D: GETWRK_AREA - N** (`$DD0E - N`), not -N or N. It is the `$4030` value itself, and that
  choice is what costs nothing at `$4030`.
* **CLAIM_NMAX** = `$F380 - (HOOK_SLOT+1)` = 439.
* **SLTWRK** `$FD09`, and **SLTWRK_BASE** = INIT_HIMEM + `$2A` = `$F1BF`.
* `make -s ram-map-doc` was rerun, and [docs/ram-map.md](../docs/ram-map.md) gained the CLAIM_D row.

**2. `init_gate` in [disk/kernel.asm](../disk/kernel.asm): +10 B.**
* It computes HIMEM - `$F381` = -N-1 (Cy is set by the `jr c` above it), then adds NMAX+1. The add carries exactly when
  0 ≤ N ≤ NMAX; anything else declines as before. That includes a HIMEM above `$F380`.
* It then stores GETWRK_AREA - N in CLAIM_D and jumps to `sltwrk_pub`.

**3. `layout_rebuild` in [disk/kernel.asm](../disk/kernel.asm): +5 B.**
* At entry it runs `ld de,(CLAIM_D) / add hl,de`.
* Its three callers now pass offsets of the same size: INIT_HIMEM / DOS_RESV_TOP / DISK_HIMEM / CTRL_HIMEM `- GETWRK_AREA`.
  All four claim steps follow from that one add.
* The "Clobbers AF? no" comment was already loose, because its own `add hl,de` instructions set the carry. It is now noted.

**4. `$4030` in [disk/init.asm](../disk/init.asm): 0 B.**
* `ld hl,GETWRK_AREA / ret` became `ld hl,(CLAIM_D) / ret`. That is still 4 bytes, still at `$4030`, and still keeps AF and
  every other register.

**5. `build_drvtbl` in [disk/init.asm](../disk/init.asm): +13 B.**
* After the LDIR it stores +3 := CLAIM_D and +1 := CLAIM_D + (DOS_RESV_TOP - GETWRK_AREA).
* This code runs only under the existing `$FF` RAMAD gate, the CF-3300-main-ROM host. On zerobas's own machine DRVTBL+1 / +3
  are not written, as before.
* **Not gated:** the C-BIOS machine never reaches it.

**6. `sltwrk_pub` (new, after layout_rebuild): +31 B.** Owner's ruling.
* It writes SLTWRK_BASE - N into SLTWRK[PP][SS] page 1, which is `$FD09 + PP*32 + SS*8 + 2`, indexed from the slot byte in
  A that INIT received. Then it falls into `pop af / jp init`.
* **Reference values, read as RAM cells:**
  * the CF-3300 holds `$F1BF - N` in its 3-1 page-1 entry, already set at its first H.RUNC after INIT. That is 
    `$F1BF` / `$F1AF` / `$F19F` / `$F093` at N = 0 / 16 / 32 / 300 in [AE_wasize_ref.out](AE_wasize_ref.out) and
    [AE_wasize_claimN.out](AE_wasize_claimN.out), and `$F008` / `$F007` at N = 439 / 440 in this gate.
  * The HBD-F1 holds `$F1C0 - N` in 1-0.
  * Both values are the machine's INIT HIMEM + `$2A`.
* zerobas now matches the CF-3300 at every N tested.

**7. `bt_keep` in [disk/kernel.asm](../disk/kernel.asm): comment only.** See the next section.

**Total: 10 + 5 + 0 + 13 + 31 = 59 B.** By hole:
* `$74CD`: 216 -> 180 B (layout_rebuild, sltwrk_pub);
* `$41B1`: 62 -> 49 B (build_drvtbl);
* `$5FD2`: 19 -> 9 B (init_gate).

**Every other fixed-number writer was checked by grep** (`$F380`, `$DE77`, `$DF93`, `$F195`, `$DD0E`, `$D606`, `$E48D`,
`(HIMEM)`, `(STKTOP)`, `(MEMSIZ)`, `$0006`, the equate names):
* the only remaining HIMEM writes are layout_rebuild and bt_keep;
* `DOS_RESV_TOP` in disk.asm is an assembly-time assert;
* no disk code writes `$0006` or names a `$Dxxx` literal.

`$0006` is MSX-DOS's own work, from the `$4030` value. Main ROM's boot (basic/interp.asm) keeps a HIMEM whose high byte is
under `high TXTMAX`. Disk BASIC's `$DE77 - N` (≥ `$DCC0`) always is, and INIT's `$F195 - N` (≥ `$EFDE`) never is, so its
branch is the same as at N = 0.

## The bt_keep decision

**Kept: `HIMEM := $F380` before rerunning the main INIT, and not `$F380 - N`.**

* On A>BASIC, or a `$4022` call from a program, zerobas's main ROM reruns every cartridge INIT, including the foreign one.
  Handing that cartridge `$F380` puts it back in its power-on state, so it claims its N again, and init_gate measures the
  same N.
* `$F380 - N` would make a cartridge that subtracts from HIMEM (like probes/disk/claimer.asm) take 2N.
* The CF-3300 reruns no INIT at A>BASIC and simply goes `$DF93 - N` -> `$DE77 - N`. The resulting HIMEM is the same: the DOS
  rows' `HIMEM@BASIC`, which go through bt_keep, are SAME at every N.
* **Residual risk, not covered:** a foreign cartridge whose INIT does not claim again when rerun would lose its claim on
  zerobas at A>BASIC.

## Gate rows

From [AE_schemeD_guard2.out](AE_schemeD_guard2.out); the same values as the first run,
[AE_schemeD_guard1.out](AE_schemeD_guard1.out). The CF-3300 values below match zerobas's exactly in every SAME row.

| N | scenario | HIMEM@INIT / SLTWRK | HIMEM@DOS / A> | `$0006` | HIMEM@BASIC | FRE | DSKF | MEMSIZ / STKTOP | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 0 | DOS | `$F195` / 3-1p1 `$F1BF` | `$DF93` | `$D606` | `$DE77` | 23426 | 367 | `$DC5F` / `$DB97` | SAME |
| 0 | DATA | `$F195` / `$F1BF` | | | `$DE77` | 23426 | 706 | `$DC5F` / `$DB97` | SAME |
| 16 | DOS | `$F185` / `$F1AF` | `$DF83` | `$D606` | `$DE67` | 23410 | 367 | `$DC4F` / `$DB87` | SAME |
| 16 | DATA | `$F185` / `$F1AF` | | | `$DE67` | 23410 | 706 | | SAME |
| 300 | DOS | `$F069` / `$F093` | `$DE67` | `$D506` | `$DD4B` | 23126 | 367 | `$DB33` / `$DA6B` | SAME |
| 300 | DATA | `$F069` / `$F093` | | | `$DD4B` | 23126 | 706 | | SAME |
| 439 | DOS | `$EFDE` / `$F008` | `$DDDC` | `$D406` | `$DCC0` | 22987 | 367 | `$DAA8` / `$D9E0` | SAME |
| 439 | DATA | `$EFDE` / `$F008` | | | `$DCC0` | 22987 | 706 | | SAME |
| 440 | DOS | CF `$EFDD` / `$F007`; ZB `$F1C8` / none | CF `$DDDB`; ZB no DOS | CF `$D406` | CF `$DCBF`; ZB `$F380` | CF 22986; ZB 28800 | CF 367; ZB none | | KNOWN |
| 440 | DATA | the same; ZB DRVTBL `00 00` | | | CF `$DCBF`; ZB `$F380` | ZB 28811 | ZB none | | KNOWN |

**The N = 440 rows.**
* zerobas declines exactly as SHIFT held does: no drives, plain BASIC, and HIMEM `$F380` at the prompt because of the filed
  D-CARTCLAIM.
* The CF-3300 installs; it works up to N = 473 ([AE_wasize_threshold*.out](AE_wasize_threshold.out)).
* The row fails if zerobas ever reads the same as the CF-3300, or if the decline stops reading as a decline.

**The spot checks with N = 0,** run with ZEROBAS_REFCACHE=refs after the final build:
* `dosctl-acceptance`: [AE_schemeD_dosctl.out](AE_schemeD_dosctl.out)
* `bufinctl-acceptance`: [AE_schemeD_bufinctl.out](AE_schemeD_bufinctl.out)
* `dossession-acceptance`: [AE_schemeD_dossession.out](AE_schemeD_dossession.out)

Results: dosctl PASS (every row SAME), bufinctl PASS (11 of 11 SAME), dossession PASS (21 of 21). The final diskguard run, on the restored build, is GREEN with the same 10 rows.

**The other checks** all passed:
* `make -s basic-reloc`: 0 dead code in main, sub and disk ([AE_schemeD_reloc.out](AE_schemeD_reloc.out));
* `make -s ram-map-check` ([AE_schemeD_rammapcheck.out](AE_schemeD_rammapcheck.out));
* `tools/audit_citations.py` ([AE_schemeD_cit.out](AE_schemeD_cit.out));
* `tests/run.py`, 100 of 100 ([AE_schemeD_tests.out](AE_schemeD_tests.out)).

## Surprises

* **`$0006` moves in 256-byte steps, not by N.**
  * On the CF-3300 it reads `$D606` at N = 0 and at N = 16, `$D506` at 300, and `$D406` at 439 and 440. MSX-DOS places its
    kernel on a page boundary below the `$4030` value.
  * zerobas gives the same, because the shift is in `$4030`.
  * The sizing's "`$0006` moves by -N" was true only to the page. N = 16 does not test `$0006`; N = 300 does, as the knife
    showed.
* **FRE in these rows is 4 below the banner's 23430** on both machines. This comes from the typed direct statement, and it
  is the same on both.
* **The HOOK_SLOT move to reach NMAX 472 was NOT done.**
  * The request asked for a free byte of `$F1C9-$F37F` "that neither reference uses". The readings show both references
    write all 439 B of that range at every working N, and its contents are their RAM-resident code, which the clean room
    cannot read. So no byte there can be shown unused.
  * Also, at N ≥ 440 the claim reaches down into `$F1A8-$F1C8`. The references leave that range alone (it is the foreign
    cartridge's RAM), but CLAIM_D (`$F1C6`) sits in it, so CLAIM_D would have to move as well.

## Not covered

* **N = 440..473:** zerobas declines and the CF-3300 installs; the row is pinned KNOWN. **Open (the owner: "dunno"): is 439 B
  enough?** No real cartridge's claim was measured. Going higher needs HOOK_SLOT and CLAIM_D out of `$F195-$F1C8`, and DRVA_DPB
  following N from 473.
* **DRVTBL+1 / +3:** written only on the CF-3300-main-ROM host, the `$FF` RAMAD gate, which no gate row boots.
* **The `$50A9` return values** (DE = IX = `$F1AA`, HL = `$F359`) and the `$F34D-$F355` pointers are unchanged. The CF-3300's
  `$F355` is `$F195 - N`; zerobas does not fill these pointers at all (class 3, as before).
* **The HBD-F1** (`$F1C0`-based) and the VG-8020 host were not gated: the CF-3300 is the DISK build's reference.
* **The CTRL-held boot** (CTRL_HIMEM - N) is untested under a claim. **The disk corpus was not rerun**: N = 0 is unchanged in
  every number, but the code paths changed.
* **D-CARTCLAIM** is unchanged: declined, zerobas BASIC still drops the cartridge's claim.

## Files touched

* [disk/equates.inc](../disk/equates.inc), [disk/kernel.asm](../disk/kernel.asm), [disk/init.asm](../disk/init.asm)
* [docs/ram-map.md](../docs/ram-map.md) (generated)
* [probes/disk/claimonce.asm](../probes/disk/claimonce.asm) (new)
* [probes/disk/disk_probe_guard.py](../probes/disk/disk_probe_guard.py) (rewritten)
* [Makefile](../Makefile) (the target's comment)
* [docs/disk/port-readiness.md](../docs/disk/port-readiness.md) (row 4c)
* [todo/open/D-DISKROMHOST.md](../todo/open/D-DISKROMHOST.md) (a new block)

`probes/disk/claimer.asm` is kept but no gate uses it any more.
