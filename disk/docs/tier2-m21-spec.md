<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M21 spec — running a typed `.COM` other than COMMAND.COM itself

**Status: M21a + M21b BOTH LANDED (2026-07-02) — Tier-2 can now load and run an arbitrary named
`.COM`, not just COMMAND.COM.** After the first implementation attempt was reverted (see §0/§0.1
for the full hard-stop-and-recharacterise story), the `DC5B`-instance isolation pass (§0.1) found
both hard-stop hypotheses FALSE and pinned the correct M21a fix shape (one generic FOPEN-fill
body, unconditional `+14:=0`, found-fill including the `+20..23` date/time field, miss-exit
`A=$FF`). M21a landed clean: relocation (§5.3) + `fopen_fill_body` in disk/fat.asm, veneer at
`$4462` in disk/driver.asm — plain-boot 27/27 aligned, miss-path `AF=$FF45` exact, FOPEN's FCB
byte-identical to stock (only the already-accepted cosmetic `dirloc` differs).

M21b (`$47B2`/`k_47B2`, RC-2) followed immediately: rewrote the boot-only diagnostic loader into
a generic body that trusts the FAT_FIRSTCLUS/FAT_FILESIZE already seeded by the preceding FOPEN,
re-primes the iterator (`fat_open`) and streams to EOF via the existing, already-proven
`bdos_seqread`, reproducing the pinned exit contract (§5.5: `AF=$0142`, `HL=BC=`bytes
transferred, `IY=`entry DE, `IX=DRVA_DPB`) via an explicit flag-construction trick (`or a / ld
b,1 / dec b` for the `Z=1,N=1,C=0` half of `$42`, then `ld a,1` last). Hit one real bug beyond the
characterisation's scope during implementation: our own internal `BDOS_DTA` cell (used by
`bdos_seqread`) is a **separate** cell from the kernel's real DTA pointer (`DOS_DTAPTR`, $F23D,
M19) — the kernel's SETDTA only ever writes `DOS_DTAPTR`, so `BDOS_DTA` was stale (leftover from
the boot-time COMMAND.COM read, landing all runtime transfers at the wrong address `$1A80`
instead of `$0100`) until `k_47B2` was fixed to reseed it from `DOS_DTAPTR` at entry. Found via a
register-value capture at `$47B2`'s entry (`--mem 0xE4C0:0x2` vs `--mem 0xF23D:0x2`), not stock
disassembly.

Verified, regression-first, on the full stack: `make unit-test` 19/19; plain-boot `callseq`
27/27 ALIGNED; `capture --at 0xC51D --nth 1`: **every register byte-identical to stock**
(`AF=0142 HL=0480 BC=0000 IX=F195 IY=DA40`, zero diffs); `callseq --at 0x0100 --log 0x0005` for
a typed `BDOSX\r`: **all 47 shared calls ALIGNED** (n=37-47 = BDOSX.COM's own FSIZE/FOPEN/RDSEQ
×2/SETRND/RDBLK/WRBLK/FCLOSE sequence, exactly [tier2-bdos-exerciser-spec.md](tier2-bdos-exerciser-spec.md)'s
Phase-1 acceptance target); `capture --at 0x01bc --mem 0x0400:0x180` (the exerciser's 384-byte
read-back data buffer) and `--mem 0x0300:0x180` (its FCB + 8-call register-snapshot buffer):
**0 of 384 bytes differ, on both**, registers at the final self-loop also byte-identical. `screen
--keys DIR` byte-identical; `make probe` all green; `disk.rom` == 16384 B throughout.
Resume board: [tier2-STATE.md](tier2-STATE.md). Discovered while building
[tier2-bdos-exerciser-spec.md](tier2-bdos-exerciser-spec.md)'s `BDOSX.COM` tool, which is now
UNBLOCKED and fully exercised as part of this milestone's own verification.

## 0. What's still needed before another implementation attempt (2026-07-02)
`$4462` is called with at least THREE distinct `DE` values, not one: `DA40` (the typed-command
SFIRST/SNEXT/FOPEN path, §5 below — fully characterised, its own acceptance check passed) and
TWO more found only by re-running the M18 plain-boot regression: `DC5B` ("COMMAND COM", a boot
self-check) and `DA40` again but for "AUTOEXEC.BAT" (an existence probe that should legitimately
miss on this disk). For `DC5B`: even after generalising the body to read/write via the caller's
own DE (fixing a real bug — the first cut hardcoded `$DA40` and searched garbage for this
caller), fed the correct name, correctly found "COMMAND COM" (`FAT_FIRSTCLUS=$003E`,
`FAT_FILESIZE=$1980`=6528, matching), and wrote the SAME field pattern already validated for the
`DA40`/BDOSX case into `$DC5B+14..+31` — the boot sequence STILL derails downstream. Two
un-eliminated hypotheses: (a) stock's real fill contract differs per calling instance (the
`DA40` case's field pattern doesn't generalise to `DC5B`'s), or (b) writing `$DC5B+14..+31`
collides with something else live at that address for this specific caller. **Needed:** a
falsify-first isolation of the `DC5B` instance specifically (writewatch on `$DC5B+14..+31`
during a plain boot on STOCK, to see whether/what it writes there at all) before trusting any
fix. Do not re-attempt M21a without this. **(DONE 2026-07-02 — see §0.1.)**

## 0.1 `DC5B` isolation results (2026-07-02, stock-only writewatch pass — no ROM changes)
Falsify-first isolation of the `DE=$DC5B` instance, run on the known-good baseline tree
(27/27 re-verified first). All probes `disk_probe_diff.py`, test.dsk, plain boot
(`--keys '\r' --keys-at 22 --settle 35`). Exact commands inline per fact.

**Fact 1 — the `DC5B` instance is PRE-`$0100` (MSXDOS.SYS's own COMMAND.COM load), not any
post-boot BDOS call.** `writewatch --range 0xDC5B:0x20 --in-func 0x0F --machine both` (default
arm = COMMAND.COM resident at `$0100`): **0 gated writes on BOTH machines.** The only post-arm
FOPEN in a plain boot is n=2 (`callseq`: `C=0F DE=D62F HL=C284 ret=C24E`), and `capture --at
0x0005 --nth 2 --arm-check-val 0x05 --mem 0xD62F:0x25 --machine stock` shows that FCB names
**"AUTOEXEC BAT"** (fresh, all-zero fields; `IY=$DC5B` even here). The "COMMAND COM" self-check
is not COMMAND.COM checking itself after boot — it is the boot loader's own FOPEN of
COMMAND.COM, before `$0100` is ever reached.

**Fact 2 — stock DOES write `$DC5B+14..+31`, from the SAME PAGE1 PCs with the SAME field
semantics as the `DA40` case.** `writewatch --range 0xDC5B:0x20 --no-gate --at 0x4010
--arm-cond 1 --machine stock` (armed at the first canonical `$4010` DSKIO hit, well before
`$0100`) captures the full boot-window write history at t≈10.46:
1. A MAINROM/BIOS-region copy (`writerPC=$027D`, block-copy-shaped: BC counts down from `$25`,
   HL source `$0A5B..`) lays down a 37-byte fresh-FCB image: drive `$00`, "COMMAND COM",
   `+12..+31` all `$00`.
2. **`$42AA`** writes `+14:=$00` — the same boundary-byte PC as §5.2's `DA40` case.
3. **The `$4488-$44C8` cluster** (PCs `$4488/$4492/$4498/$449A/$449F/$44A1/$44AE/$44B3/$44B8/
   $44BB/$44C0/$44C3/$44C6/$44C8` — the §5.2 set) fills: `+15 RC:=$33` (51 = 6528/128 ✓),
   `+16..19 size:=$00001980` (=6528 ✓), **`+20..23 := $50 $2D $14 $A0` (dir-entry date/time —
   a fill field §5.2's list MISSED; stock writes it in the `DA40` case too, PCs
   `$4498/$449A/$449F/$44A1`)**, `+24 devid:=$40`, `+25 dirloc:=$06` (COMMAND.COM's own dir
   slot; was `$2C` for BDOSX — per-file, consistent), `+26/27 top clus:=$003E` ✓,
   `+28/29 last clus:=$003E`, `+30/31 relloc:=$0000`.
4. **Immediately after the fill returns, KERNEL PC `$D812` overwrites `+14:=$01`, `+15:=$00`**
   (S2=1, RC=0) — exactly the "textbook fresh-open FCB" image §5.4 captured at the boot-time
   `$47B2` call. The boot caller does not even preserve the fill's `+14/+15`.
5. Later (t≈11.29, during the boot read), PAGE1 `$4C29/$4C2C/$4C32/$4C35` update
   `+28/29:=$0044`, `+30/31:=$0006` — the read loop's cluster bookkeeping (COMMAND.COM spans
   clusters `$3E..$44`, 6 clusters in at EOF ✓).

**⇒ Hypothesis (a) is FALSE at the fill level: the fill contract IS uniform across calling
instances** (same PCs, same fields, same semantics; only the per-file DATA differs).
**⇒ Hypothesis (b) is FALSE: `$DC5B+14..+31` is not doing double duty in the boot window** —
it is exactly the FCB, and stock itself writes the same fields there. Writing the `DA40`
pattern there cannot, by itself, be what broke the boot.

**Fact 3 — on a MISS, the fill machinery writes NOTHING beyond `+14:=$00`.**
`writewatch --range 0xDA40:0x20 --in-func 0x0F --machine stock` (default arm; catches n=2's
AUTOEXEC.BAT probe): kernel `$D880` block-copies the name in from the user FCB (`$D62F`→`$DA40`),
then **`$42AA` writes `+14:=$00` and the `$4488-$44C8` cluster NEVER fires.** The `$42AA`
boundary-byte zero is an unconditional PRE-search write; the `+15..+31` fill is found-only.

**Fact 4 — `$4462` is a TAIL-CALL; its exit registers ARE the FOPEN return values.**
`capture --at 0x4462 --nth 1 --arm-check-val 0x05 --machine stock --mem 0xDBFE:0x8`: at entry
`SP=$DBFE` and the top-of-stack return address is **`$D88A`** — the common BDOS-exit
trampoline (§5.5). There is no post-`$4462` kernel FOPEN logic on this path (which is also why
the earlier `$D7FD`-return-site guess never fired). Whatever A/flags the body exits with go
straight into the `$D8AA`/`$F306`-gated BDOS exit as the FOPEN result.

**Fact 5 — the miss-exit register contract, pinned at `$D88A` nth=2** (`capture --at 0xD88A
--nth 2 --arm-check-val 0x05 --machine both --mem 0xF306:0x1`; nth=1 is n=1 STROUT's exit,
nth=2 is n=2 FOPEN's): **stock `AF=$FF45` (A=$FF = published FOPEN not-found), BC=$0004,
HL=$EBB5**; baseline-ours (accidental no-op `$4462`) `AF=$2100, BC=$0000, HL=$C284`;
`DE=$DA40 IY=$DC5B` identical; `$F306` byte identical on both. Both machines then boot 27/27
identically — so **A is the found/not-found channel** (ours' nonzero `$21` happens to read as
"miss" too), and BC/HL at this exit are don't-care within the proven envelope. Target value
for a real body: **A=$FF on miss, matching stock exactly.**

**⇒ Verdict: neither (a) nor (b). The `DC5B` write pattern was never the killer.** The
un-eliminated prime suspect for the M21a regression is now the **MISS path of the generic
body at boot's n=2 (the AUTOEXEC.BAT probe)**: `$4462` is a tail-call whose exit A is the
FOPEN result; stock exits a miss with A=$FF having written nothing but `+14:=$00`; a body
that exits a miss with A=$00 — or fills `+15..+31` anyway — makes COMMAND.COM believe
AUTOEXEC.BAT exists, and COMMAND.COM's documented AUTOEXEC branch **skips the date prompt**
— exactly the observed derail shape (n=1/n=2 aligned, n=3's date-prompt STROUT replaced by
the `A>` redraw). This is labeled PRIME SUSPECT, not proven: M21a's body was reverted
uncommitted, so its actual miss-path exit can't be inspected retroactively. A secondary,
unexcluded contributor: the body's own `fat_find` sector reads clobbering live kernel/boot
state during the pre-`$0100` window (would need a new-build probe to test).

**Correct M21a fix shape for `DC5B` (and all instances):** ONE generic body, no per-caller
branch — the fill contract is uniform and the kernel itself repairs `+14/+15` after the boot
call. Required behavior: (i) unconditional `+14:=$00` before the search (mirrors `$42AA`);
(ii) on FOUND, fill `+15..+31` via the caller's DE per §5.2 **plus the `+20..23` date/time
field §5.2's list omitted**; (iii) on MISS, write nothing else and exit **A=$FF**; (iv) exit
registers ARE the BDOS return (tail-call semantics — get A right in BOTH arms; found-arm
target remains §6's `AF=$0044 HL=$0000` at `$C4A1`). Acceptance for the next attempt MUST run
the plain-boot 27/27 regression FIRST (before the BDOSX check), plus a targeted miss probe:
`capture --at 0xD88A --nth 2 ... --machine both` → ours' A must be `$FF` matching stock. If
27/27 still fails with the miss path correct, re-run this section's probes on the new build
to test the fat_find-side-effect secondary suspect.

Clean-room note: all observations above are writer/entry PC addresses, registers, stack DATA
(2 bytes at SP read as data), and RAM values — the same allowed classes as §7; no stock
instruction bytes read or decoded.

## 1. Symptom
Typing any program name other than `COMMAND.COM` itself at the `A>` prompt silently returns to
a fresh `A>` on **ours** — no error, no execution. `DIR` lists the file fine (M19's SFIRST/SNEXT
is not implicated); stock loads and runs it normally. Every prior M13-M20 milestone only ever
exercised COMMAND.COM loading *itself* (`k_47B2`) — "run an arbitrary named `.COM`" was never
before on the tested path.

## 2. The load sequence (pinned, byte-identical call prefix on both machines)
`SETDTA($D403) → SFIRST → SNEXT → FOPEN(FCB=$D403) → SETDTA($0100) → RDBLK $27 (DE=$D403,
HL=$C200 records, record size 1) → SETDTA($0080) → jump $0100`. `callseq --log 0x0005
--maxhits 60`: ours == stock byte-identical through n=35 (RDBLK issued, `C=27 DE=D403 HL=C200
ret=C51D`); **diverges at n=36's exit: stock `HL=$0480`, ours `HL=$0001`.** Stock then runs
BDOSX.COM's own 11 calls (n=37-47); ours falls through to the `A>` redraw loop instead.

## 3. Root cause — TWO independent broken page-1 entries, either alone fatal

### RC-1 — kernel FOPEN's dir-fill entry `$4462` collides with live `fdc_di_save` code
FOPEN's kernel handler delegates dir lookup + opened-FCB fill to page-1 `$4462` (the long-known
"`$4462` chain" — [tier2-bdos-scope.md](tier2-bdos-scope.md) already flagged "collides with our
FDC/DSKIO code, no contract"; caller pinned at `$D7FA`). On ours, `$4462` lands **mid**
`fdc_di_save` (disk/driver.asm; `fdc_di_save`=$445B, `fdc_di_on`=$4466). Our own ROM bytes there
(own artifact, allowed to read): `$4461: AF` / **`$4462: 32 99 E2` = `ld ($E299),a`** /
`$4465: C9` = `ret`. The kernel's CALL into $4462 stores A into our IFF-save cell `$E299`
(a latent clobber in its own right — every runtime FOPEN corrupts it) and returns immediately.
**The FCB is never transformed into opened form.**

Evidence (`capture --at 0xC4A1 --nth 1 --arm-check-val 0x05 --mem 0xD403:0x25`, FOPEN's return
site): stock's FCB is in opened form per the published CP/M / MSX-DOS-1 FCB layout (map.grauw.nl
/ MSX2 TH) — `+15 RC=$09` (9×128=1152), `+16..19 size=$00000480`, `+24 devid=$40`,
`+25 dirloc=$2C`, `+26/27 top cluster=$0151`, `+28/29 last cluster=$0151`, `+30/31 relloc=$0000`.
Ours still holds the raw SFIRST "found-FCB" dir-entry image (size at +16 = 0). Exit regs: stock
`AF=$0044 HL=$0000`; ours `AF=$2100 HL=$0021` (the M20 `$F306` `H:=B,L:=A` mirror — `$4462`
never clears the dispatcher flag, same class as every M20-pattern handler needs to). `callwatch
--in-func 0x0F --machine both`: ours executes only 2 distinct page-1 PCs (`$4462`, `$4465`);
stock runs 60+ (`$44xx/$45xx/$56xx/$5Fxx/$60xx/$78xx` — the real dir-search + fill machinery,
entry-PC counts only, no bytes decoded).

Why not caught before: runtime FOPEN was only ever probed on the **not-found** path (boot n=2,
AUTOEXEC.BAT probes), where "return immediately" at `$4462` happens to yield the same observable
outcome as stock's real not-found path — the found-path divergence was invisible until now.

### RC-2 — kernel RDBLK's entry `$47B2` is generic; our `k_47B2` hardcodes COMMAND.COM
The kernel's RDBLK (`$27`) handler CALLs page-1 **`$47B2`** from **`$D887`** (`ret=$D88A`) with
**HL = the requested record count**, DE = a kernel work pointer — i.e. `$47B2` is the **generic**
"read the current FCB's records into the DTA" entry, not a COMMAND.COM-boot-only hook as
previously assumed. Every prior milestone only ever exercised it via MSXDOS.SYS's own boot call
(`~$D821, DE=$DC5B`); our body (`k_47B2`, disk/kernel.asm:452) is a first-cut diagnostic that
**ignores the caller's FCB entirely** — it opens its own ROM-resident FCB naming `"COMMAND COM"`
through our private mini-BDOS (`bdos_entry`) and sequential-reads it to `(BDOS_DTA)=$0100`.

At the typed-BDOSX RDBLK, ours therefore **re-loads COMMAND.COM over the TPA** — byte-identical
to the already-resident image, which is why the TPA looked "untouched" in the original
`[$0102]==$05` capture (that was never "no load attempted"; it was "the wrong file reloaded").
Proof (`capture --at 0xC51D --machine ours --mem 0xE4AE:0x14`, our own work cells, one-sided):
`FAT_FILESIZE` ($E4AE) = `$00001980` = 6528 = **COMMAND.COM's size**, not BDOSX.COM's 1152;
`BDOS_DTA` ($E4C0) = `$1A80` = `$0100 + 51×128` — exactly `k_47B2`'s open+seq-read loop having
run to COMMAND.COM's EOF. Corroborated by timing (ours' RDBLK takes ~3.3s vs stock's ~0.8s) and
`callwatch --in-func 0x27`: ours' 66 entry-PCs are our own FDC machinery (`dskio`≈$4257 region,
`$435E/$4361/$4365` wait-loop ×112) plus `$47B2`×1. The kernel then hands COMMAND.COM a wrong
read count (`HL=$0001`, again the `$F306` mirror; stock: `HL=$0480` = BDOSX.COM's exact size),
so COMMAND.COM's post-read check fails silently → fresh `A>`.

### 3.1 Causal poke test (run) — RC-1's fix alone would NOT be sufficient
`callseq --poke-at 0xC4A1 --poke-nth 1` injecting stock's exact post-FOPEN FCB image into ours
(`$D412:=$09,$D413:=$80,$D414:=$04,$D41B:=$40,$D41C:=$2C,$D41D:=$51,$D41E:=$01,$D41F:=$51,
$D420:=$01,$D421:=$00`) — poke **applied**, ours **still fails byte-identically** (n=36
`HL=$0001`, fresh `A>`). **⇒ RC-2 is independently fatal**, confirming BOTH fixes are required,
not just one. (A positive-direction poke that makes ours load isn't achievable with data pokes
alone — the missing piece is code behavior at `$4462`/`$47B2`, not a memory cell; both mechanisms
are nonetheless pinned by direct register/memory observation, not inference.)

## 4. WARNING — this is bigger scope than any prior M1x/M2x fix
Every fix from M13 through M20 was a **3-byte `jp` into existing free `$00` pad**, net-zero,
low-risk. **M21a is not that shape**: `$4462` sits *inside currently-live* `fdc_di_save` code
(disk/driver.asm), so wiring a real handler there means **relocating** the FDC tail elsewhere in
the ROM and repointing its callers — the same "3b-relocation-class" treatment
[tier2-bdos-scope.md](tier2-bdos-scope.md) already flagged as the harder tier of this ROM's
known gaps, not a drop-in veneer. Net-zero and no-canonical-shift still apply, but the diff
surface and regression risk are materially larger than M13-M20. M21b (`$47B2`) is closer to the
familiar shape (rewrite one body) but still a generic-behavior change to a boot-critical entry
(must not regress the COMMAND.COM self-load path M13-M20 already proved green).

## 5. Proposed fix shape + resolved characterisation (2026-07-02 follow-up span)
Two milestones, **ordered** — M21a is a prerequisite for M21b, because a generic FCB-driven
`$47B2` can only work at boot if the boot-time kernel FOPEN of COMMAND.COM actually fills the
kernel FCB (RC-1's job). The four items below (spec's original open list) are now answered.

### 5.1 New harness capability used: `writewatch`
`readwatch` (M14/M15) classifies READERS of a data range by PC; item 1 needed the write-side
mirror. Added `disk_probe_diff.py writewatch --range BASE:LEN --in-func N` (same shape as
`readwatch`: per-byte `write_mem` watchpoints, gated to "while BDOS func N is in flight", caps
at 64 B). Each hit reports **writer PC + the region it falls in** (`PAGE1` = `$4000-$7FFF`,
`KERNEL` = `>=$C000`, `MAINROM/BIOS` = `<=$3FFF`) plus `BC/DE/HL` at the moment of the write —
the extra registers were needed here (not in `readwatch`) because the writer turned out to be
a single block copy, and `BC` (remaining count) / `DE` (destination) / `HL` (source) are what
identify the block copy's source buffer and progress, itself an allowed black-box (register) read, no
instruction decoded. Same clean-room class as every other probe in the file.

### 5.2 Item 1 — kernel↔`$4462` division of labor: the kernel writes 100% of the FCB body;
### `$4462` fills a SEPARATE, EARLIER work buffer that the kernel then block-copies into the FCB
`writewatch --in-func 0x0F --range 0xD403:0x25` (both machines) shows **every** byte of the
FCB at `$D403` is written by **KERNEL** code (a block copy at `$D8A8`, plus 3 tail stores at
`$C4A4/$C4A7/$C4AB`) — `$4462` (or any PAGE1 PC) never writes `$D403` directly, on EITHER
machine. This looked at first like "the kernel does all the work," but `writewatch` on the
LDIR's SOURCE (found via the same hit's `HL`/`DE`/`BC`: `$D8A8` runs `HL=$DA40..$DA5F ->
DE=$D403..$D422, BC=$20->0`, i.e. **`$D8A8` is a block copy of a 32-byte kernel-RAM work buffer
at `$DA40` into the FCB** — the same buffer `$47B2` is later called with, see §5.3) shows the
REAL division of labor is one level up, at `$DA40`, not at `$D403`:
- `writewatch --in-func 0x0F --range 0xDA40:0x20`: on **stock**, `$DA40` is first LDIR-filled by
  the SAME kernel `$D880` block copy (name+ext+EX+S1+S2, i.e. FCB bytes +0..+13 = the search-FCB the
  caller supplied) — that part IS pure kernel, both machines match here. Then, at
  `t≈22.28` (mid-FOPEN, AFTER the name fill), stock's writer PCs shift to **`$42AA`
  (`dskio_rd` on our numbering) / `$4488/$4492/$4498/$449F/$44A1/$44AE/$44B3/$44B8/$44BB/
  $44C0/$44C3/$44C6/$44C8` — all `PAGE1`** — filling `$DA4F..$DA5F` (FCB offsets +15..+31:
  RC, and the 16-byte allocation-map/cluster-chain field) with the real directory-entry's
  record-count/size/cluster data. **`$DA4E` (FCB +14, S2's high byte / reserved) is written by
  BOTH kernel (`$D880`, zeroed first) and PAGE1 (`$42AA`, re-zeroed) on stock — a boundary
  byte.** On **ours**, the SAME `$DA40:$20` range gets ONLY the kernel `$D880` name-fill
  (writer=KERNEL for the whole range, confirmed 0 PAGE1 writer-PC hits) — offsets +15..+31
  (`$DA4F..$DA5F`) stay at whatever `$D880`'s own zero-fill left them (**not** even
  re-touched — `$4462`'s 2-instruction no-op body never reaches this address at all,
  consistent with RC-1: it returns before doing anything).

**⇒ Division of labor (pinned): the KERNEL is responsible for the search-FCB header
(drive/name/ext/extent/S1/S2, FCB +0..+13, written via `$D880`'s block copy from the SFIRST/SNEXT
"found" DTA image — already proven byte-identical by M19). The PAGE1 FOPEN-fill entry
(reached as the `$4462`-class call, but stock's actual fill code spans multiple addresses —
`$42AA` then the `$4488-$44C8` cluster, i.e. it runs THROUGH what are, on our ROM, `dskio_rd`
and `getdpb`'s bodies) is responsible ONLY for FCB +14..+31 (S2-high/reserved boundary byte,
record-count, and the 16-byte allocation-map/cluster-chain — i.e. "resolve the found
directory entry's disk-resident metadata into the FCB's random-access fields").** This matches
the published FCB layout's own natural seam (name/ext/extent = "what you asked for", RC +
allocation map = "what BDOS found for you") and tells M21a's body exactly what NOT to
duplicate: it must NOT re-fill +0..+13 (the kernel already did, correctly, via SFIRST/SNEXT +
$D880 — M19's machinery is untouched and still correct); it must ONLY compute and write
+14(high)..+31 from the SFIRST/SNEXT-found directory entry (already sitting in the runtime DTA
per M19) — cluster start (+26/27 per §3 RC-1's field list), size (+16..19 mirrored /
record-count +15 derived from it), and devid/dirloc bookkeeping (+24/+25) that stock's cluster
also wrote (`$44AE/$44B3` -> `$DA58/$DA59` = FCB+24/+25 = devid/dirloc). **A second, smaller
consequence: `getdpb`'s own PROVIDER-direction contract ($4016) is untouched by this finding —
stock's fill routine merely happens to route through the same numeric addresses our `getdpb`
occupies; nothing here implies `getdpb`'s black-box contract (disk/driver.asm:437-465) needs to
change.**

### 5.3 Item 2 — relocation plan for the colliding PAGE1 span (`$4462` through `$44C8`)
Ground truth from our OWN `disk.rom` (16384 B, base `$4000`) + `disk.omsx.sym` (allowed: own
artifact) plus a full-ROM zero-run scan (own bytes, `disk.rom`):

**What collides.** Stock's fill routine's writer PCs land on TWO of our routines, not one:
1. `$42AA` = `dskio_rd` (inside `dskio`, disk/driver.asm — the physical-sector-read path,
   +$10 canonical entry `$4010`). Only ONE write observed there (`$DA4E:=00`) — a single
   incidental instruction inside `dskio_rd`'s body, not its entry point.
2. `$4488-$44C8` = the tail of `div9` (`fdc_div_nob`/`fdc_div_done`) + **all of `dskchg`
   ($448C) and `getdpb` ($448E-$44F3, 102 bytes, ending at `gdpb_popdone`+3)** — `getdpb` is
   itself a **canonical, load-bearing disk-ROM entry** (`$4016`, disk/init.asm:31, and also
   called directly at disk/init.asm:579), so it is NOT a free-standing internal helper —
   relocating it must repoint `$4016`'s `jp` target, which pasmo does automatically from the
   symbol (no hardcoded address anywhere in our source references `getdpb`/`dskchg` except the
   two `jp`s in init.asm and the one `call` in init.asm:579 — confirmed by grep, all
   symbol-based).
   `$4462`/`$4465` themselves (RC-1's exact collision point) fall inside `fdc_di_save`
   (`$445B-$4465`) / `fdc_di_on` (`$4466-$446B`) — called from `dskio`'s three transfer sites
   (disk/driver.asm:55,131,238) and internally by `fdc_di_save`→`fdc_di_on` (driver.asm:388),
   all symbol-based `call`/`jp`, no hardcoded addresses.

**Byte budget needed.** The full span that must vacate `$445B-$44F3` (`fdc_di_save` through
`getdpb`'s end) is **152 bytes** (`0x44F3 - 0x445B + 1`; `fdc_io_done`/`fdc_iod_x`/`div9`
$4476-$4487 also sit in this span and must move too, since they're between the vacating
routines and would otherwise be orphaned mid-gap — moving the whole contiguous block
`fdc_di_save..getdpb` (`$445B-$44F3`, **153 bytes** measured off `disk.omsx.sym`:
`getdpb`-end $44F4 minus `fdc_di_save` $445B) is simplest and avoids fragmenting `div9`/
`fdc_io_done` away from their callers' expectations of contiguity (they have none — pasmo
resolves symbols — but moving the whole run is the smallest diff).

**Free-tail budget available** (own-ROM zero-run scan, `disk.rom`, all unused `$00` pad —
none of these are "guessed," each is read directly off our built ROM):

| region | free bytes | currently reserved for |
|---|---|---|
| `$4C77-$4E4B` | 468 | (free, pre-M19) |
| `$4EE1-$4FB8` | 215 | (free, pre-M19, ends at the M19 `$4FB8` SFIRST entry) |
| `$561B-$5FE5` | 2506 | (free, ends at the `$5FE5` free-region kernel entry) |
| `$607E-$7000` | 3970 | (free) |
| `$7000-$75A5` | 1445 | (free, ends at the `$75A5` free-region kernel entry) |

Any ONE of these comfortably fits the 153-byte relocated block (e.g. `$4C77-$4E4B`, the
nearest one, leaving 315 bytes spare — headroom for M21a's new FOPEN-fill body to live
alongside the relocated FDC/GETDPB code in the SAME free region, keeping the diff localized).

**Plan:**
1. Move `fdc_di_save, fdc_di_on, fdc_io_done, fdc_iod_x, div9, fdc_div_loop, fdc_div_sub,
   fdc_div_nob, fdc_div_done, dskchg, getdpb` (+ its `gdpb_*` sub-labels) as one contiguous
   block from `$445B-$44F3` to the free tail (proposed: `$4C77` onward — 153 of the 468 free
   bytes there, 315 left over for M21a's new body). Pure `ds`-anchor relocation: cut the block
   out of driver.asm's current position, paste it (unchanged) into the free-tail region genre
   already established by M13/M17/M18/M19 (`k_XXXX`-style bodies in the free tail called via a
   `jp` veneer) — except here the routines keep their OWN names/labels (`getdpb` etc.) since
   pasmo re-resolves every internal `call getdpb`/`jp dskchg` automatically; no veneer needed
   for THESE callers.
2. At the vacated `$445B-$44F3` span (now free `$00` pad, 153 bytes), place the NEW `$4462`
   real-FOPEN-fill veneer (`ds $4462-$, $00` then `jp fopen_fill_body`, 3 bytes) — this consumes
   3 of the 153 newly-freed bytes, net **+150 bytes free** at the old location (a wash against
   the ROM's total free-byte accounting; net-zero is about total ROM size, $16384 B, which is
   unaffected by moving code from one internal region to another).
3. The canonical `$4010/$4013/$4016/...` disk-ROM entry table (disk/init.asm:28-34) is
   UNTOUCHED — it already `jp`s to `dskio`/`dskchg`/`getdpb` by symbol; pasmo re-links to
   wherever those symbols now live. **No canonical-address shift for anything external**
   (`$4010-$401F`'s six entries keep their fixed offsets; only their JP TARGETS' addresses
   move, which is invisible to any external caller).
4. `disk.rom` stays exactly 16384 B (nothing added or removed, only moved + the new 3-byte
   veneer replacing 3 of the vacated `$00` bytes). Verify post-relocation with the standard
   invariant checks (§6): `make unit-test` 19/19, `disk.rom` size, DSKIO/BLOAD/FILES vs
   CF-3300 (this relocation touches `dskio_rd`'s neighborhood and ALL of `getdpb`, both
   Tier-1-load-bearing — regression risk is real and this is exactly why §4's WARNING flagged
   this as bigger than a veneer; the existing Tier-1 probe suite is the safety net).

**Confirmed NOT needed:** no other symbol in the tree references `$4462`, `$4465`, `fdc_di_save`,
`fdc_di_on`, `dskchg`, or `getdpb` by raw hex address (grep-verified); every caller is
symbol-based, so relocation is mechanically safe from pasmo's perspective. The regression risk
is behavioral (getdpb/dskio_rd are real, tested Tier-1 code, not the low-risk padding this
class of fix usually touches), not linkage risk.

### 5.4 Item 3 — `$47B2`'s call-context identity: SAME structure kind, DIFFERENT instances,
### and (new fact) never the same call in the same boot — the two contexts are temporally disjoint
Direct captures at the ARMED `$47B2` anchor (`--at 0x0100 --arm-check-val 0x05`, which arms only
once COMMAND.COM is resident — i.e. AFTER the boot-time self-load already ran) vs the UNARMED
anchor (which catches the earliest, boot-time hit) show:
- **Boot-time call** (`DE=$DC5B`): `$DC5B` dump = `00 43 4F 4D 4D 41 4E 44 20 43 4F 4D 00 00 01
  00 00...` = drive=$00(default), name="COMMAND COM", EX=$00, S1=$00, S2=$01, RC=$00,
  allocation-map all zero. **A textbook fresh-open FCB, drive=default.**
- **Runtime typed-command call** (`DE=$DA40`): dump = `01 42 44 4F 53 58 20 20 20 43 4F 4D 00
  20 01 00 00...00 51 01 80 04 00...` = drive=$01(A:), name="BDOSX   COM", EX=$00, S1=$20,
  S2=$01, RC=$00, then (offsets +27..+30) cluster=$0151, size=$0480 — **the SAME textbook FCB
  shape, byte-identical in field layout to the boot case, differing only in the DATA it holds**
  (a different file, an explicit drive letter, and — because this capture is AFTER FOPEN
  already ran — the allocation-map fields FOPEN itself fills, confirming §5.2's finding that
  those fields are populated by the time `$47B2` is called).
- **This same `$DA40` dump is BYTE-IDENTICAL between ours and stock** at the armed `$47B2`
  call (captured independently, `--machine ours` and `--machine stock`, same nth=1, same
  gate) — i.e. **the caller-supplied contract is proven correct and identical on both
  machines going INTO `$47B2`**; the entire M21b problem is what OUR `$47B2` body (`k_47B2`)
  does with that correct input, not what it's handed.
- **`IY` at the `$47B2` call differs (ours `$DC5B`-boot / runtime instance vs stock
  `$ED15`-boot / `$DC5B`? — see raw dumps) only in WHICH kernel-internal work-slot address
  is used, an implementation-internal allocation difference between machines, not a
  structural difference** — same role (a kernel work-context pointer), different instance
  address per machine's own internal bookkeeping, exactly analogous to `DE=$DA40`(runtime)
  vs `DE=$DC5B`(boot) both being "the current FCB pointer," just two different instances.
- **New, previously-unstated fact:** the runtime path (`$C51D`, the kernel's `$27` RDBLK
  handler return site immediately after `$47B2`) **never fires during an ordinary boot with no
  typed external command** (`callseq --log 0xC51D` during a plain `\r`-only boot: 0 hits, both
  machines) — confirming the boot-time COMMAND.COM self-load and the runtime typed-command
  load are structurally TWO SEPARATE CALL CHAINS into the shared `$47B2` entry (boot via
  MSXDOS.SYS's own loader per the original §3 RC-2 note; runtime via the relocated kernel's
  `$27` handler), not a single path that happens to carry different data. **⇒ M21b's new body
  does NOT need to branch on caller identity at all — it can be a single generic "read HL
  records of the FCB at DE-ish work-context into (DTA)" routine, because both callers already
  hand it a fully-formed, same-shape FCB and the same generic contract (HL=count in, HL=records
  read out) is exactly what both need.** The only per-context nuance is that the boot caller
  currently gets its correct behavior from `k_47B2`'s HARDCODED open+read (which must keep
  working); M21b replaces that hardcoding with a real generic body that serves BOTH callers
  identically, using the FCB/DTA the KERNEL already set up (SETDTA, proven working both
  contexts) rather than opening its own private "COMMAND COM" FCB.

### 5.5 Item 4 — exact exit-register contract at `$47B2`'s effective return site
`$D88A` itself is **not usable** as originally hoped: it is a shared BDOS-common-exit
trampoline (the same `$D8AA`-family region M20 pinned) reached after EVERY BDOS call
regardless of function — an `nth`-sweep at the armed anchor shows 8 hits inside the first
~0.003 s of settle time alone (n=1..8, one per CONOUT/etc.), making "the `$47B2`-specific hit"
impossible to isolate by `nth` or timestamp alone without a lot of extra bookkeeping.

**Resolved by using a BETTER anchor instead: `$C51D`**, the runtime kernel's own `$27` RDBLK
HANDLER's return site (one level IN from `$D88A`, i.e. the first kernel code to see `$47B2`'s
raw return values before the generic `$D8AA`/`$F306`-gated exit massages them). This address:
(a) is proven to fire **exactly once per RDBLK call** (`--log 0xC51D --maxhits` during a plain
boot = 0 hits; during the typed-command run = exactly the RDBLK moments, matching callseq's
n=35/40 `C=27` entries one-for-one); (b) needs no disambiguation — every hit IS a `$47B2`
return, full stop. **Pinned contract at `$C51D` (already captured in §2/§3, restated here as
the answer to item 4):**
- **Stock:** `AF=$0142` (A=$01: EOF/success-with-remainder per the published RDBLK contract —
  1 record delivered, matching BDOSX.COM's 1-record `$27` call), `HL=$0480` = **1152 decimal =
  exactly BDOSX.COM's file size in bytes, NOT a record count** — i.e. on this specific call
  (the COMMAND.COM loader's `$27` with `HL=$C200`-shaped "read everything" request) the kernel
  hands the CALLER (COMMAND.COM) the byte count it loaded, which COMMAND.COM uses to know
  where the loaded program ends. `IY=$DA40` unchanged (still the FCB pointer, register-stable
  across the call, matching M20's "register-transparent except the documented outputs" pattern
  already proven for `$47B2`'s boot use at `k47b2_done`, disk/kernel.asm:481-485).
- **Ours (unfixed, for contrast — NOT the target contract):** `AF=$0100`, `HL=$0001` — the
  M20 `$F306`-mirror artifact (`H:=B,L:=A` with `B=0,A=1`), because `k_47B2`'s hardcoded
  COMMAND.COM-reload path never clears `$F306` and its own `A` (EOF flag from ITS OWN
  bdos_entry sub-call) leaks through the mirror.
- **⇒ M21b's body contract:** on success, return **A = $01 (EOF, matching stock's constant
  observed value) and HL = total bytes transferred** (not a record count — confirmed by the
  1152/$0480 value, which is exactly `RECSIZE(128) × records-read`, i.e. whatever the real
  read loop accumulates in bytes, mirroring `k47b2_done`'s existing `HL=(FAT_FILESIZE)`
  pattern already proven correct for the boot contract — §2 of tier2-m5.4-spec.md). **Clear
  `$F306` before `ret`, per the now-general M20 rule**, so this HL survives the kernel's
  `$D8AA-$D8BD` exit path intact instead of being mirrored.
- **Boot-context cross-check (not yet captured this span, flagged as the one remaining
  verification step before implementation):** `k47b2_done`'s EXISTING contract (HL=BC=
  FAT_FILESIZE, IX=DRVA_DPB, IY=saved entry DE) was pinned by a DIFFERENT prior probe
  (disk/kernel.asm:470-480, "measured at the $0100 entry") rather than at `$C51D`/`$D88A` —
  because, per §5.4, the boot call doesn't route through `$C51D` at all (different caller). A
  clean implementation of M21b must therefore satisfy TWO independently-pinned contracts at
  TWO different observation points (boot: register state at COMMAND.COM's `$0100` entry;
  runtime: register state at `$C51D`) — both are now pinned, but they were never diffed
  against EACH OTHER for internal consistency (e.g. does the boot caller also expect
  `HL=bytes`, or does it want `HL=BC=filesize` specifically because ITS caller reads `HL`
  differently than the runtime kernel's `$C51D`-adjacent code does?). **This is flagged as an
  open verification step for the M21b implementation pass, not a gap in the characterisation
  above** — both contracts are independently solid; only their mutual compatibility in a
  SINGLE shared body is unverified.

- **Collateral cleanup from M21a for free:** stop runtime FOPEN clobbering `$E299` (=`FDC_IFF`,
  disk/equates.inc:35, "saved caller IFF2 across a sector op") — RC-1's `ld ($E299),a` side
  effect, harmless today only because no sector op is concurrently in flight during FOPEN, but
  latent corruption of a real work cell that goes away automatically once `$4462` is a real
  veneer instead of a slide into `fdc_di_save`'s body.

## 6. Acceptance sketch (now firm — §5's items are resolved)
### M21a (`$4462` real FOPEN-fill body + relocation)
- Relocation alone (before the new body lands) is a pure no-op refactor: `make unit-test`
  19/19, DSKIO/BLOAD/FILES byte-identical to CF-3300, `disk.rom` == 16384 B, and
  `writewatch --in-func 0x0F --range 0xDA40:0x20` on ours STILL shows zero PAGE1 writer-PC
  hits (i.e. relocating the collision alone changes nothing observable — confirms the
  relocation didn't accidentally fix or break anything by itself, isolating the new body's
  effect in the next step).
- With the new `fopen_fill_body` wired at `$4462`: `capture --at 0xC4A1 --mem 0xD403:0x25` —
  ours' FCB matches stock's fully-opened form (§3 RC-1's field list: RC=$09, size=$00000480,
  devid=$40, dirloc=$2C, cluster=$0151/$0151, relloc=$0000) byte-identical, `AF=$0044 HL=$0000`
  (not the `$F306` mirror — confirms `fopen_fill_body` clears `$F306`).
- `writewatch --in-func 0x0F --range 0xDA40:0x20 --machine ours`: PAGE1 writer-PC hits now
  appear at ours' OWN `fopen_fill_body` address(es), filling exactly FCB +14(high)..+31 (not
  re-touching +0..+13, confirming §5.2's division-of-labor boundary was respected).
- Regression: `$E299`/`FDC_IFF` no longer written during FOPEN (readwatch/writewatch check);
  boot 27/27 BDOS parity intact; `DIR` 100% parity intact (M19/M20 unaffected, since SFIRST/
  SNEXT + the `$D880` header-fill block copy are untouched by this fix).

### M21b (`$47B2` generic record-read body)
- `capture --at 0xC51D --mem ...`: runtime typed-command RDBLK returns `AF=$0142 HL=$0480`
  (byte-identical to stock, §5.5) instead of the `$F306`-mirror `AF=$0100 HL=$0001`.
- Boot-context regression (the ORIGINAL, still load-bearing contract): `capture` at
  COMMAND.COM's `$0100` entry — `HL=BC=$1A00` (COMMAND.COM's own size), `IX=$F195`,
  `IY=$DC5B` UNCHANGED from the current `k47b2_done` contract (disk/kernel.asm:481-485) —
  M21b's generic body must reproduce this exactly for the boot caller while ALSO satisfying
  the `$C51D` contract for the runtime caller (§5.5's flagged open verification: confirm both
  are simultaneously satisfiable by one body before declaring this closed).
- `screen --machine both --keys '\rBDOSX\r' ...`: ours parks in BDOSX.COM's self-loop like
  stock (no fresh `A>` reprompt).
- `callseq --log 0x0005`: n=36 `HL=$0480` (was `$0001`); n=37-47 = BDOSX.COM's own 11 calls
  (`FSIZE/FOPEN/RDSEQ×2/SETRND/RDBLK/WRBLK/FCLOSE`) byte-identical to stock — this is exactly
  [tier2-bdos-exerciser-spec.md](tier2-bdos-exerciser-spec.md)'s Phase 1 acceptance criteria,
  now unblockable.
- `capture --at 0xC51D --mem 0x0100:0x10`: TPA = BDOSX.COM's own image on both sides.
- Regression: boot 27/27 BDOS parity intact, `DIR` 100% parity intact (M19/M20 unaffected),
  Tier-1 `make unit-test` 19/19, `disk.rom` == 16384 B.

## 7. Clean-room statement
Observations used: BDOS entry/exit registers, kernel-PC values (addresses only — `$D7FA`,
`$D880`, `$D887`/`$D88A`/`$D8A8`, `$C4A1`/`$C4A4`/`$C4A7`/`$C4AB`, `$C51D`), page-1 entry-PC and
writer-PC counts/regions (never instruction bytes — the `writewatch`/`readwatch`/`callwatch`
allowed class), DATA memory (the FCB at `$D403`, the kernel work buffers at `$DA40`/`$DC5B`
read as data, TPA bytes read as data, our own work cells `$E4AE`/`$E4C0`/`$E299`), our own ROM
bytes/symbols (disk.rom/disk.omsx.sym/kernel.asm/driver.asm/init.asm/equates.inc — including a
full-ROM zero-byte-run scan of our own built `disk.rom` for the relocation free-space budget),
and published FCB/BDOS/DPB contracts (map.grauw.nl, MSX2 TH, Nextor 2.1 Driver Development
Guide, CP/M 2.2; disk/PROVENANCE.md §FCB layout). No stock ROM / MSXDOS.SYS / COMMAND.COM code
bytes were read, dumped, or decoded as instructions; `trace` mode was not used on stock for
this investigation. The new `writewatch` harness mode (§5.1) reads the same allowed classes as
`readwatch` — PC, address, value, and (new) `BC/DE/HL` registers at the moment of a write —
never decoding an instruction on either machine.
