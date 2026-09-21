; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; Tier-2 MSX-DOS-1 kernel veneers + relocated bodies (Interface A: the de-facto DOS ABI)
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- MSX-DOS-1 kernel continuation entry: $50A9 ($4000 + $10A9; a3 §8.26/§8.27) -
; The relocated kernel CALLs $50A9 right after publishing its BDOS vector; on the
; genuine CF-3300 this disk-ROM routine (`CALL $472D` + work-area setup) reaches A>.
; Our code ends far below $50A9, so the entry is positioned with a `ds` fill (like
; $4030). We reproduce the BLACK-BOX contract (disk_probe_dosboot_50a9.py):
;   side effect : W50A9_WRKB ($F242) := $00   (the only non-stack write observed)
;   returns     : A=$00, F=$42 (Z+N) ; DE=IX=$F1AA ; HL=$F359 ; BC, IY preserved
; `sub a` yields exactly A=$00 / F=$42 ($42 = Z|N: 0-0 sets Z+N, clears S/H/PV/C); the
; following loads do not disturb the flags, so the exit AF is exact. Inputs ignored
; (the kernel passes AF=C340 BC=0000 DE=DC80 HL=D606 IX=F195 IY=C0AB; none consumed).
                ds      $4E4B - $, $00  ; pad to the $4E4B kernel veneer (was $50A9 fill)
                jp      k_4E4B          ; $4E4B: COMMAND.COM-load kernel veneer
                ds      $4EDE - $, $00  ; pad to the $4EDE kernel veneer
                jp      k_4EDE          ; $4EDE: COMMAND.COM-load kernel veneer
; --- MSX-DOS-1 kernel SFIRST/SNEXT dir-search entries: $4FB8/$5006 (M19) -------
; While processing BDOS SFIRST ($11) / SNEXT ($12) the relocated kernel CALLs these
; two page-1 disk-ROM entries to walk the root directory for entries matching the
; search FCB's 8.3 pattern. Both are our own $00 pad (inside the $4EE1..$50A9 fill,
; below the $50A9/$50C4/$50D5/$50E0 veneers), so before this the CALL NOP-slid into
; the $50A9 stub tail and returned a bogus "entry found" -> DIR hung (M19 §3). Each
; is inserted as an additional descending ds-anchor in this chain ($4FB8, $5006 slot
; in address order between $4EDE and $50A9), consuming existing pad -> net-zero.
; Black-box entry contract (M19 §2, callseq/capture, no stock CODE decoded): entry
; DE -> the kernel's search-FCB copy (drive byte + 11-byte 8.3 pattern, ?=$3F
; wildcard); the runtime DTA base lives in the fixed work-area cell $F23D (the
; kernel's current-DTA pointer, set via its own SETDTA before the search). Bodies
; (sfirst_body/snext_body/dirscan_match) live in the free tail; clean-room -- our
; own fat_mount/fat_find root-dir walk + published SFIRST/SNEXT contract. See
; docs/tier2-m19-spec.md.
                ds      $4FB8 - $, $00  ; pad up to the pinned $4FB8 SFIRST entry
sfirst:
                jp      sfirst_body     ; -> free-tail: find FIRST matching dir entry (M19)
                ds      $5006 - $, $00  ; pad up to the pinned $5006 SNEXT entry
snext:
                jp      snext_body      ; -> free-tail: find NEXT matching dir entry (M19)
; --- MSX-DOS-1 kernel FSIZE entry: $501E (M28 §3.1/§3.2, [LANDED-B]) ----------
; While processing BDOS FSIZE ($23) the relocated kernel CALLs this page-1 disk-
; ROM entry (same dispatcher class as $4788/$4793, M26: DE=$DA40 kernel FCB
; copy, A=$25/B=$00/C=$00, ret=$D88A). Sits in the dead-$00 pad between snext
; ($5006, ends $5008) and $504E LOGIN -- a 3-byte `jp fsize_body` wires directly,
; RDABS/M26-style, no relocation needed. Body = fsize_body (free tail): a real
; GET FILE SIZE (fat_mount + fat_find, ceil(size/128) -> copy+33..35); the prior
; stub returned a constant A=L=$03 for every input and never searched at all.
                ds      $501E - $, $00  ; pad up to the pinned $501E FSIZE entry (M28)
k_501E:
                jp      fsize_body      ; $501E: BDOS $23 FSIZE canonical entry (M28)
; --- MSX-DOS-1 kernel LOGIN entry: $504E (M22a; tier2-m22-cpmver-spec.md) ------
; While processing BDOS LOGIN ($18) the relocated kernel CALLs this page-1 disk-
; ROM entry for the online-drive bitmap. Was un-wired $00 pad, NOP-sliding into
; the $5058 SETDTA-cache veneer below: garbage exit AND a silent stomp of
; DOS_DTAPTR from whatever DE happened to hold (benign-by-luck only because DE
; was $0080 at the observed call site, §4.3). Body = login_body (free tail).
; CLEAN-ROOM: published LOGIN online-drive-bitmap contract (map.grauw.nl) +
; our own DRVCNT cell; no stock routine internals decoded.
                ds      $504E - $, $00  ; pad up to the pinned $504E LOGIN entry (M22a)
k_504E:
                jp      login_body      ; $504E: BDOS $18 LOGIN canonical entry (M22a)
; --- MSX-DOS-1 kernel SETDTA-time entry: $5058 (M19) --------------------------
; While processing BDOS SETDTA ($1A) the relocated kernel CALLs this page-1
; disk-ROM entry to cache the new DTA pointer into the disk work area. Black-box
; contract (M19, callseq/capture/callwatch causal pin, no stock CODE decoded):
; entry DE = the new DTA pointer (=$D403 for DIR; register-identical ours==stock,
; 51 calls each), and stock's routine stores it at the fixed work-area cell $F23D
; (proven: on stock $F23D=$D403 and SFIRST reads it via PCs $4FCC/$4FEF; on ours,
; before this veneer, $F23D was never written -> SFIRST/SNEXT wrote the found entry
; to a stale/garbage DTA -> DIR reported "File not found"). Wiring $5058 to cache
; DE at $F23D makes SFIRST/SNEXT (which read DOS_DTAPTR=$F23D) target the real
; runtime DTA. Same un-wired-$50xx-entry class as M13/M17/M18. Body =
; setdta_cache_body (free tail). CLEAN-ROOM: our own DE->$F23D store + the observed
; entry-register / write-target contract; no stock routine internals decoded.
                ds      $5058 - $, $00  ; pad up to the pinned $5058 SETDTA-cache entry
setdta_cache:
                jp      setdta_cache_body ; -> free-tail: ($F23D) := DE (runtime DTA; M19)
; --- MSX-DOS-1 kernel GETALLOC entry: $505D (M20 REVISION 3; tier2-m20-spec.md) -----
; While processing BDOS GETALLOC ($1B) the relocated kernel CALLs this page-1 disk-ROM
; entry to compute the DIR "nn bytes free" footer. Black-box contract (M20 §2, no stock
; CODE decoded): entry regs byte-identical ours==stock (C=$1B BC=$5D1B DE=$D100
; HL=$C924 IX=$F195); the un-wired $00 pad here made the CALL NOP-slide into the $50A9
; stub tail (garbage exit -> "0 bytes free"). Exit contract (map.grauw.nl _ALLOC):
; A=sectors/cluster, BC=bytes/sector, DE=total data clusters, HL=free clusters.
; REVISION 3 (this span): Revisions 1 (register-only) and 2 (+ resident FAT buffer +
; IY + a per-drive DPB+19 field) were both BUILT and FALSIFIED -- the A/BC/DE/HL scan
; math was correct in both (host-unit-tested + confirmed at getalloc_body's own ret),
; but the DIR footer was wrong regardless, IDENTICALLY so both with and without the
; IY/DPB+19 wiring. Root cause (this span, a narrow read of 20 RAM-KERNEL bytes at the
; shared post-handler exit path $D8AA-$D8BD -- NOT stock ROM/COMMAND.COM code -- to
; answer one question, "what does the branch at $D8AE test"; same technique already
; used to pin $F23D/$F247/$F347/$F306 in prior milestones): the kernel's common BDOS-
; exit path gates HL passthrough on a flag cell, $F306 (set to $01 by the dispatcher on
; every BDOS call, per tier2-gdate-spec.md's earlier pin) -- a handler that leaves
; $F306 set has its HL SILENTLY OVERWRITTEN with H:=B,L:=A (the CP/M single-byte-result
; B:A->HL mirror) instead of passed through. Stock's $505D handler clears it; ours never
; did, so our correct HL was replaced by a mirror of our own A/BC (explaining the exact
; wrong constant observed, `$0202`=514, in both falsified revisions). Causally proven by
; a poke test (forcing $F306:=0 flips the branch and the handler's real HL survives).
; `gdate_handler` below already clears $F306 (previously assumed "harmless stock
; parity" -- it is in fact load-bearing, and the only reason GDATE's HL reaches its
; caller). Revision 3 = Revision 1's register-only body (own FAT scan via read_sector/
; WBUF, reusing fat.asm's fac_entry_from_wbuf unpack -- no new RAM cell, no IY, no
; DPB+19, both proven unnecessary) + one added store: clear $F306 before `ret`, loading
; the final A value AFTER the clear (order matters: A must hold sectors/cluster at
; `ret`; the clear only needs A=0 transiently as the store source).
; CLEAN-ROOM: our own FAT scan (fat_mount + read_sector + fat.asm's fac_entry_from_wbuf,
; all pre-existing oracle-validated primitives) + the published GETALLOC A/BC/DE/HL
; contract (map.grauw.nl) + the black-box-pinned $F306 dispatcher-flag semantics
; (register/memory VALUES + one narrow RAM-kernel byte read, no stock ROM decoded).
                ds      $505D - $, $00  ; pad up to the pinned $505D GETALLOC entry
getalloc:
                jp      getalloc_body   ; -> free-tail: FAT free-cluster scan (M20 rev3)
; --- MSX-DOS-1 kernel DSKRST entry: $509F (M22a; tier2-m22-cpmver-spec.md) -----
; While processing BDOS DSKRST ($0D) the relocated kernel CALLs this page-1
; disk-ROM entry to flush/reset the disk work area. Was un-wired $00 pad,
; NOP-sliding into our OWN $50A9 continuation stub below — which happens to
; reproduce the exact register contract by coincidence (§4.4: "pad-slide
; luck", the same class of latent bug M21a-RC-1 broke later). Body =
; dskrst_body (free tail): a wired `jp` to the same stub, replacing luck with
; an explicit entry. Real flush semantics are unverifiable here (no dirty
; buffers at these call sites); the register contract is the observable
; surface (§8.4 residual).
                ds      $509F - $, $00  ; pad up to the pinned $509F DSKRST entry (M22a)
k_509F:
                jp      dskrst_body     ; $509F: BDOS $0D DSKRST canonical entry (M22a)
                ds      $50A9 - $, $00  ; pad remainder up to the kernel's $50A9 target
w50a9_stub:
                sub     a               ; A=$00, F=$42 (Z+N) -- the exact exit AF
                ld      (W50A9_WRKB), a ; $F242 := $00  (the only persistent write)
                ld      de, W50A9_RET_DE ; DE = $F1AA
                ld      ix, W50A9_RET_DE ; IX = $F1AA (= DE)
                ld      hl, W50A9_RET_HL ; HL = $F359
                ret                     ; AF=$0042, BC/IY untouched

; --- MSX-DOS-1 kernel CONIN line-read entry: $50E0 (M12d pin; tier2-conin-spec.md v3) --
; BUFIN (BDOS func $0A) has the relocated kernel CALL a disk-ROM console-line routine;
; the M12d black-box pin (guarded callseq, no stock bytes decoded) fixed the entry as the
; CALL target $50E0 (regs byte-identical ours==stock at first entry: DE=$DA40 HL=$C924
; ret=$D88A) and the register convention as DE -> buffer, [DE]=max length (the published
; BDOS func-$0A layout: [+0]=max/[+1]=count/[+2..]=chars; confirmed by a second pin
; walking HL/D/E across 7 CHGET calls with an injected keystroke). No return register --
; the result lives in the buffer (func-$0A contract). Our `$50B7-$5453` region is our own
; $00 padding (active code ends at the $50A9 routine above), so before this veneer BUFIN
; NOP-slid straight into the $5454 CONOUT veneer below (one garbage char, no block) --
; the M12 root cause. Body = conin_line_body (free tail): reimplements the func-$0A
; buffered-line read from the published CHGET ($009F) / CHPUT ($00A2) / func-$0A buffer
; ABI, clean-room -- the stock routine's internals were never read (spec §3 Option A).
;
; --- MSX-DOS-1 kernel SELDSK-time entry: $50D5 (M17; tier2-m17-spec.md) --------
; While processing BDOS SELDSK (func $0E) the relocated kernel CALLs this page-1
; disk-ROM entry (register-identical ours==stock at entry: AF=0044 BC=D50E DE=D3FF
; HL=D349 IX=F459 IY=DC5B, ret=D88A -- a real CALL boundary, M17 §2.1). Black-box
; contract: read the logical-drive count from $F347 into A, preserve BC/DE/HL/IX/IY
; (return F irrelevant so far, §4). Our $50B8-$5453 block is our own $00 padding, so
; before this veneer the CALL NOP-slid into the $5454 CONOUT veneer and never
; returned to the trampoline -> the M17 SELDSK stall (no A> prompt). Body =
; seldsk_drv_body (free tail); clean-room -- the stock routine's internals were never
; read (only its entry/exit registers + a DATA-cell read-watch of $F347).
; --- MSX-DOS-1 kernel CURDRV-time entry: $50C4 (M18; tier2-m18-spec.md) ---------
; While processing BDOS CURDRV (func $19) the relocated kernel CALLs this page-1
; disk-ROM entry (register-identical ours==stock at entry: AF=0044 BC=C419 DE=D3FF
; HL=D502 SP=DBFE IY=DC5B, ret=D88A -- a real CALL boundary, M18 §2.1). Black-box
; contract (readwatch causal pin): read the CURRENT-drive index from $F247 into A,
; preserve BC/DE/HL/IX/IY. Our $50B8-$50D4 block is our own $00 padding, so before
; this veneer the CALL NOP-slid and never read the drive -> the kernel's later
; 'A'+drive letter math used a bogus index ($C400 + 2 = 'C>') instead of A>. Body =
; curdrv_body (free tail); clean-room -- the stock routine's internals were never
; read (only its entry/exit registers + a DATA-cell read-watch of $F247).
                ds      $50C4 - $, $00  ; pad up to the pinned $50C4 kernel entry
curdrv:
                jp      curdrv_body     ; -> free-tail: A = ($F247) current drive (M18)
; --- MSX-DOS-1 kernel SETRND entry: $50C8 (M32; tier2-m33-m32-fcb-position-
; spec.md §3) --------------------------------------------------------------
; While processing BDOS $24 SETRND the relocated kernel CALLs this page-1
; disk-ROM entry (same FCB-copy dispatcher class as M26 RDRND/WRRND: entry
; A=$25, DE=IY=$DA40 kernel FCB copy, BC=HL=$0000, SP=$DBFE, captured
; black-box on both machines). Carved from the $50C4-$50D5 pad (curdrv above
; occupies $50C4-$50C6; $50C7..$50D4 was un-wired $00 pad -- 14 bytes, ample
; for this 3-byte veneer) -- net-zero, no canonical address shifts. Was
; un-wired $00 pad -> ours' $24 NOP-slid -> no write -> RR stayed 0. Body =
; setrnd_body (free tail): computes the CORRECT CP/M func-36 rr = cr +
; ex*128 + s2*4096 from the FCB-copy position fields M33 now maintains -- an
; INTENTIONAL, DOCUMENTED divergence from stock's known-broken RR:=1 stub
; (§4, allowlisted; ours' $27 stays independently gate-verified by M31's
; dedicated round-trip probe, not by the BDOSX $24-chained bytes). CLEAN-
; ROOM: hook address + register convention from black-box capture (call-
; target + register/RAM observation, same M26 dispatcher class); rr formula
; from the published CP/M func-36 contract; no stock ROM code decoded.
                ds      $50C8 - $, $00  ; pad the single leftover pad byte ($50C7)
setrnd:
                jp      setrnd_body     ; $50C8: BDOS $24 SETRND canonical entry (M32)
                ds      $50D5 - $, $00  ; pad up to the pinned $50D5 kernel entry
seldsk_drv:
                jp      seldsk_drv_body ; -> free-tail: A = ($F347) drive count (M17)
                ds      $50E0 - $, $00  ; pad up to the pinned CONIN line-routine entry
conin:
                jp      conin_line_body ; -> free-tail buffered-line CHGET loop (M13)

; --- MSX-DOS-1 kernel CONOUT-worker entry: $53A7 (M22b; tier2-m22b-conout53a7-spec.md) --
; The relocated kernel CALLs this page-1 disk-ROM entry for EVERY BDOS CONOUT
; ($02) character (ret=$D88A, B=$A7 fingerprint, C=$02, char in E — the same
; dispatcher class as the M22a eleven). It was un-wired $00 pad; pre-M22a the
; CALL NOP-slid 173 bytes into the $5454 CONOUT veneer below, which happens to
; implement the exact right observable contract (emit E via CHPUT, A:=E) — the
; accident every M8-M21 console-parity probe rode. M22a's new $543C CONST
; veneer (below) now sits earlier in that same slide and intercepts it instead,
; silently dropping every func-2 char (date/A>/echo/DIR listing). This veneer
; restores the pre-M22a behavior explicitly instead of by accident; net-zero,
; 3 bytes carved from the existing pad before $543C. CLEAN-ROOM: $53A7 is a
; de-facto page-1 kernel-ABI address (class of $4010/$5454), pinned by
; call-target + register observation only (400/400 region-entry samples);
; body = conout_body, the proven $5454 implementation (M8/M10).
                ds      $53A7 - $, $00  ; pad up to the pinned $53A7 CONOUT-worker entry (M22b)
k_53A7:
                jp      conout_body     ; $53A7: BDOS $02 CONOUT canonical entry (M22b slice 1)

; --- MSX-DOS-1 kernel console entries: $543C/$5445/$544E (M22a) ---------------
; While processing BDOS CONST ($0B) / CONIN ($01) / INNOE ($08) the relocated
; kernel CALLs these page-1 disk-ROM entries. All three were un-wired $00 pad,
; NOP-sliding into the $5454 CONOUT veneer below — each would have emitted a
; garbage char via CONOUT (E's leftover value) instead of polling/reading the
; keyboard, without ever consuming a queued key (tier2-m22-cpmver-spec.md §4.5).
; Bodies (const_body/conin_body/innoe_body, free tail) use the same CHSNS/CHGET
; inter-slot primitives conin_line_body/conout_body already use.
; CLEAN-ROOM: published CONST/CONIN/INNOE contracts (map.grauw.nl) + our own
; pg0_mainrom_in/out inter-slot path; no stock routine internals decoded.
                ds      $543C - $, $00  ; pad up to the pinned $543C CONST entry (M22a)
k_543C:
                jp      const_body      ; $543C: BDOS $0B CONST canonical entry (M22a)
                ds      $5445 - $, $00  ; pad up to the pinned $5445 CONIN entry (M22a)
k_5445:
                jp      conin_body      ; $5445: BDOS $01 CONIN canonical entry (M22a)
                ds      $544E - $, $00  ; pad up to the pinned $544E INNOE entry (M22a)
k_544E:
                jp      innoe_body      ; $544E: BDOS $08 INNOE canonical entry (M22a)

; --- MSX-DOS-1 kernel CONOUT entry: $5454 ($4000 + $1454; a3 §8.38) ---------
; The relocated kernel CALLs $5454 to emit its sign-on banner one character at a
; time (the boot's first divergence point, disk_probe_dosboot_pctrace.py). It is
; the disk ROM's CONOUT: output the char in A via the BIOS CHPUT path, preserving
; BC/DE/HL/IX/IY. Black-box call-chain on the stock: $5454 -> $408F -> $001C
; (CALSLT) -> resident kernel -> $F398 -> $00A2 (CHPUT); first call A=$0D (the
; banner's leading CR). $5454 is reached by a fixed immediate call in MSXDOS.SYS
; (the call TARGET is $5454 in the pristine just-loaded image, unchanged at call
; time -- observed via the call landing at $5454, not a relocated vector).
; CLEAN-ROOM: $5454 is a cross-vendor de-facto-standard entry,
; byte-identical across seven vendors' disk ROMs in the shared ASCII-kernel block
; ($4768-$576F) -- the same ABI class as $4010 DSKIO / $4016 GETDPB, never a byte
; copy (oracle-artifacts.md "Cross-vendor disk-ROM set"; spec-diskrom-kernel.md
; §1.3). Our code ends far below $5454, so the entry is positioned with a `ds`
; fill (like $4030/$50A9), consuming otherwise-$00 page padding -- nothing shifts.
; M8/§8.67: the first-cut no-op was PROVEN to be the COMPLETE COMMAND.COM-load
; blocker (aligned pctrace from $0100 diverges at exactly $5454; ours spins in the
; banner loop forever, 56 distinct PCs, while stock proceeds, 482). So CONOUT now
; does the real thing: emit A via the main-ROM CHPUT ($00A2) through a genuine
; inter-slot call. The body lives in the free tail (conout_body); $5454 just diverts
; to it (the 2 extra bytes shift the $5456 bodies gap, absorbed by `ds $5FE5 - $`).
                ds      $5454 - $, $00  ; pad up to the kernel's $5454 CONOUT target
conout:
                jp      conout_body     ; -> free-tail inter-slot CHPUT call (M8)

; --- MSX-DOS-1 kernel DIRIN entry: $5462 (M22a; tier2-m22-cpmver-spec.md) ------
; While processing BDOS DIRIN ($07) the relocated kernel CALLs this page-1
; disk-ROM entry. Was inside fat_find_body's span (relocated to the free tail
; below, §4.6) — fat_find_body never had a canonical-address requirement of its
; own (only reached by label from fat.asm's `fat_find` veneer), so moving it
; frees this slot outright. Body = dirin_body (free tail).
                ds      $5462 - $, $00  ; pad up to the pinned $5462 DIRIN entry (M22a)
k_5462:
                jp      dirin_body      ; $5462: BDOS $07 DIRIN canonical entry (M22a)
k_5465:
                jp      lstout_body     ; $5465: BDOS $05 LSTOUT canonical entry
                                        ; (lands naturally at $5465 = k_5462 + 3 bytes;
                                        ;  was squatted by callf_body_body, M27 §4)

; --- lstout_body - the real $5465 LSTOUT (BDOS $05); characterised 2026-07-04 -----
; Output the char (in E) to the list device via the main-ROM LPTOUT ($00A5),
; preserving BC/DE/HL. Entry E=char is the $5465 LSTOUT contract (= the $5454 CONOUT
; contract; black-box confirmed: kernel func-5 worker entry has E=char, A=$00,
; ret=$D88A -- disk/docs/tier2-lstout-characterisation.md §3.3). Pages the main BIOS
; ROM into page 0 (pg0_mainrom_in), calls LPTOUT, restores (pg0_mainrom_out); DI spans
; the half-mapped window; EI on exit -- the same structure conout_body uses for CHPUT.
;   in:  E = char ; out: BC/DE/HL preserved (IX/IY untouched)
; BIOS-DELEGATING by design (two-interface rule, [[cbios-target-cf3300-oracle]]):
; LSTOUT does NOT poke the printer ports ($90/$91) itself -- it calls the main BIOS's
; LPTOUT and inherits whatever the host BIOS does. On real CF-3300 hardware this drives
; the printer (and, faithfully, blocks if none is attached -- matching stock, which
; tight-polls status port $90). On C-BIOS it inherits C-BIOS's own $00A5, TODAY A STUB
; -> LSTOUT safely no-ops (no port poll, no hang). *** C-BIOS LPTOUT is a LATER FIX ***
; (tier2-lstout-characterisation.md §4): once C-BIOS grows a real $00A5, LSTOUT here
; starts working with no change to this ROM. NB: the DI window means a real-hardware
; no-printer poll would block with interrupts off (no Ctrl-STOP escape) -- an authentic-
; hang edge case, not reachable on our targets (C-BIOS no-op / real-hw-with-printer).
; CLEAN-ROOM: E=char is the BDOS LSTOUT ($05) ABI; $00A5 LPTOUT is the published BIOS
; entry (same documented class as CHPUT $00A2 already called by conout_body); no oracle
; bytes decoded. Lives in the $5456-$5FE4 gap section (net-zero: absorbed by the
; `ds $5FE5 - $` pad below, so nothing downstream shifts / the FDC-window guard holds).
lstout_body:
                ld      a, e                ; char arrives in E ($5465 LSTOUT contract)
                ld      (CONOUT_CHAR), a    ; stash across the slot work (A needed for paging)
                push    bc
                push    de
                push    hl
                di                          ; no interrupt while the BIOS is half-mapped
                call    pg0_mainrom_in
                ld      a, (CONOUT_CHAR)
                call    $00A5               ; LPTOUT - output A to the list device
                call    pg0_mainrom_out     ; restore page 0
                ei
                pop     hl
                pop     de
                pop     bc
                ret

; ===== Tier-2 3b: relocated Disk-BASIC routine bodies ($5456-$5FE4 gap) =====
; Each colliding routine's body lives here; its low-region slot holds `entry:
; jp entry_body` + the ds-anchored veneer(s) + padding, sized to exactly fill the
; original span (net-zero — nothing downstream shifts). Each body ends with a `jp`
; back to the label that followed it, so fall-through is preserved. Callers reach
; the routine through its unchanged low-region entry label.
; (fat_find_body relocated to runtime.asm, M22a — its old span here collided
; with the $5462 DIRIN canonical entry above, tier2-m22-cpmver-spec.md §4.6.)

; callf_body_body — the $0030 RST 30h / CALLF handler (the load-bearing one).
; CALLF is `F7 <slot> <lo> <hi>`: RST 30h pushes the return address (which points
; at the inline operand) and lands here. H.PHYD ($FFA7 = F7 87 10 40 C9) is exactly
; this — every PHYDIO from the boot/DOS reaches our DSKIO through it. The callee
; (DSKIO, $4010) takes A,B,C,DE,HL and CY=read/write, so this handler must deliver
; ALL of them UNTOUCHED. It saves the caller's registers to page-3 scratch, reads
; the operand off the stack to find the target address + the post-operand return,
; then arranges the stack so a plain `ret` jumps to the target with every register
; (and the carry flag) restored, and the target's own RET lands on the byte after
; the operand (H.PHYD's trailing C9). Our disk ROM is in page 1, so the target is
; directly reachable — no real inter-slot switch needed. (§8.4) Reached directly
; from p0_env_tab's $0030 entry (pageenv.asm, free tail) since M22a removed the
; 3-byte `callf_body` veneer that used to sit at $41F0 (it collided with the
; CPMVER canonical entry, tier2-m22-cpmver-spec.md §4.1).
; Only `ld`/`inc hl`/`pop`/`push`/`ret` are used between entry and the call, none
; of which touch the flags, so the caller's CY (the DSKIO read/write bit) survives.
callf_body_body:                        ; ends in ret
                ld      (R30_HL), hl    ; stash caller HL
                ld      (R30_BC), bc    ; stash caller BC
                ld      (R30_DE), de    ; stash caller DE
                push    af              ; copy AF out without disturbing the return ptr
                pop     hl              ; HL = AF image (push/pop is SP-neutral)
                ld      (R30_AF), hl    ; stash caller AF (incl. carry)
                pop     hl              ; HL = return addr -> inline operand [slot][lo][hi]
                inc     hl              ; -> lo
                ld      e, (hl)
                inc     hl              ; -> hi
                ld      d, (hl)         ; DE = target address (e.g. $4010)
                inc     hl              ; HL = operand+3 = byte after CALLF (H.PHYD's C9)
                push    hl              ; ultimate return: target's RET lands here
                push    de              ; target address on top
                ld      hl, (R30_AF)    ; restore caller AF (carry = DSKIO read/write)
                push    hl
                pop     af
                ld      bc, (R30_BC)    ; restore caller BC
                ld      de, (R30_DE)    ; restore caller DE
                ld      hl, (R30_HL)    ; restore caller HL (DSKIO transfer address)
                ret                     ; -> target; its RET -> operand+3 -> caller

bdos_seqread_body:                      ; [bdos_seqread, bsr_have) -> falls into bsr_have
                ; EOF once every file byte has been delivered (BYTESLEFT == 0).
                ld      hl, (BDOS_BYTESLEFT)        ; low word
                ld      de, (BDOS_BYTESLEFT + 2)    ; high word
                ld      a, h
                or      l
                or      d
                or      e
                jp      z, bsr_eof                  ; no bytes left -> EOF (jr->jp: relocated)
                ld      a, (BDOS_RECIDX)
                cp      RECPERSEC
                jp      c, bsr_have     ; records still left in SECTOR_BUF (jr->jp)
                call    fat_read_file_sector
                jp      c, bsr_eof      ; chain ended early -> EOF (jr->jp)
                xor     a
                ld      (BDOS_RECIDX), a    ; back to record 0
                jp      bsr_have

bdos_create_body:                       ; [bdos_create, bdos_create_failpop) — ends in ret
                push    de              ; FCB across fat_mount
                call    fat_mount
                jp      c, bdos_create_failpop      ; jr->jp: relocated
                pop     hl              ; HL = FCB
                inc     hl              ; HL = FCB+1 = 8.3 name
                call    fat_dir_create  ; find/make a dir slot, write the entry
                jp      c, bdos_create_err          ; jr->jp: relocated
                ; prime the write iterator: no cluster yet, empty buffer, 0 bytes.
                xor     a
                ld      (BDOS_WRSECIDX), a
                ld      hl, 0
                ld      (BDOS_WRCLUS), hl
                ld      (BDOS_WRFIRST), hl
                ld      (BDOS_WRBUFLEN), hl
                ld      (BDOS_WRBYTES), hl
                ld      (BDOS_WRBYTES + 2), hl
                ; Item 5 (spec-diskbasic-option-closure.md): reset the per-open
                ; sequential record counter for the WRITE session too, mirroring
                ; the read-open reset in fopen_fill_body (fat.asm; M33 §2.1). A file
                ; is opened read XOR write, so BDOS_SEQREC is the single per-open
                ; counter shared by wrseq_writeback (read) and wrseq_wr_writeback
                ; (write); write-open must zero it or a prior read session's count
                ; would poison the first WRSEQ position.
                ld      (BDOS_SEQREC), hl
                ld      a, 1
                ld      (BDOS_WRMODE), a    ; file is open for write
                xor     a                   ; A = $00 success
                ret

write_sector:                           ; relocated (entry collided with $4935 veneer)
                ld      b, 1            ; one sector
                ld      c, $F9          ; media byte (ignored, single drive)
                ld      a, 0            ; drive 0 (ignored)
                scf                     ; Cy = 1 = WRITE direction (MSX2 TH DSKIO)
                jp      dskio           ; tail-call: dskio returns to our caller

; --- MSX-DOS-1 kernel _GDATE entry: $553C ($4000 + $153C; M9 date slice) ----
; The kernel BDOS dispatcher ($D831; table $D8BE + 3*C) routes _GDATE ($2A) here
; after paging in the disk ROM via the $F368 hook. CF-3300 and C-BIOS are
; clock-less MSX1, so _GDATE returns the documented MSX-DOS-1 default date
; 1984-01-01 (a Sunday) -- a constant, NOT a reproduction of stock's stored
; day-count -> Y/M/D math. Return contract (observed black-box at the GDATE
; return $CC04): HL=year, D=month, E=day, A=day-of-week(0=Sun), BC=0, F=$44.
; `xor a` yields A=$00 and F=$44 (Z|P/V) exactly; the preceding loads do not
; disturb the flags. CLEAN-ROOM: documented default + black-box return contract;
; no stock bytes. $553C fell inside fac_loop_body; that body is relocated just
; below (label-referenced via fat.asm `jp fac_loop_body`; net-zero -- the tail
; `ds $5FE5 - $` absorbs the shift). See docs/tier2-gdate-spec.md.
                ds      $553C - $, $00      ; pad to the canonical _GDATE entry
gdate_handler:
                ld      hl, $07C0           ; year = 1984
                ld      de, $0101           ; D = month 01, E = day 01
                ld      bc, $0000
                xor     a                   ; A = 0 (Sunday); F = $44 (Z,P/V), as stock
                ld      ($F306), a          ; clear dispatcher re-entrancy flag (stock parity)
                ret

; --- MSX-DOS-1 kernel GTIME/STIME/VERIFY entries: $55DB/$55E6/$55FF (M22a) ----
; While processing BDOS GTIME ($2C) / STIME ($2D) / VERIFY ($2E) the relocated
; kernel CALLs these page-1 disk-ROM entries. All three fell inside the
; fdc_entloop_body/fdc_useslot_body span (now relocated above): STIME executed
; FDC-flavored retry-loop code (wrong exit registers), and GTIME's walk ended in
; a WARM BOOT — killing whatever program was running (the M22a root cause;
; tier2-m22-cpmver-spec.md §4.2). Bodies (gtime_body/stime_body/verify_body,
; free tail) reproduce the pinned oracle contracts (§5.1); none clear $F306 —
; every exit HL is the kernel's own H:=B,L:=A mirror (§5.2, the M20 rule
; inverted for this tier).
; CLEAN-ROOM: published GTIME/STIME/VERIFY contracts (map.grauw.nl, MSX2 TH
; §BDOS) + the black-box-pinned oracle register buffer; no stock CODE decoded.
                ds      $55DB - $, $00  ; pad up to the pinned $55DB GTIME entry (M22a)
k_55DB:
                jp      gtime_body      ; $55DB: BDOS $2C GTIME canonical entry (M22a)
                ds      $55E6 - $, $00  ; pad up to the pinned $55E6 STIME entry (M22a)
k_55E6:
                jp      stime_body      ; $55E6: BDOS $2D STIME canonical entry (M22a)
                ds      $55FF - $, $00  ; pad up to the pinned $55FF VERIFY entry (M22a)
k_55FF:
                jp      verify_body     ; $55FF: BDOS $2E VERIFY canonical entry (M22a)

; ===== Tier-2: COMMAND.COM-load kernel entries — veneer scaffold (milestone 3a) =====
; The relocated MSX-DOS-1 kernel + COMMAND.COM call back into ~21 disk-ROM entry
; points at fixed page-1 addresses (the de-facto-standard shared-kernel ABI;
; spec-diskrom-kernel.md §5). zerobas exposes each as a 3-byte `jp k_XXXX` veneer
; at its canonical address, with the contract body in this free-tail region.
; This 3a pass places the FIVE free-region entries (no relocation needed); $402D
; (in the $4022-$402F pad) is the sixth non-colliding entry, wired above. Bodies
; are register-preserving stubs for now — our ROM does not yet reach the
; COMMAND.COM-load phase — so this scaffold changes no current behaviour; the 14
; entries that collide with active code arrive in the 3b relocation pass, and
; milestone 4 fills each contract. CLEAN-ROOM: exposing ABI entry points + own
; contract code, never shared-kernel bytes — same legitimacy class as the $4010
; BIOS jump table. Veneer safety confirmed by disk_probe_dosboot_veneer.py.
                ds      $5FE5 - $, $00  ; pad to the first free-region kernel entry
                jp      k_5FE5          ; $5FE5
                ds      $607B - $, $00
                jp      k_607B          ; $607B  (BDOS callback; spec §5.2)

; ===== FDC-window P0 fix (2026-07-04): position-free bodies relocated OUT of the
; $7F80-$7FBF FDC register window into this free-region corridor ==================
; The National WD2793 FDC registers ($7FB8-$7FBF) are memory-mapped AND mirrored x8
; across the whole $7F80-$7FBF window, so ROM bytes there read back as register
; values. fdc_useslot_body (create's dir-slot claim) and p0_env_tab's head had drifted
; into that window (~M27), silently breaking create/write persistence. All three
; blocks are reached only by label -- their absolute address is irrelevant -- so they
; live here, in the 5.4 KB of dead $00 pad between the $607B and $75A5 COMMAND.COM-load
; kernel veneers (0 canonical entries, no FDC window). The trailing `ds $75A5 - $`
; still pins k_75A5 exactly -> net-zero canonical addresses. Spec:
; disk/docs/tier2-remediation-spec.md Phase B.

; fdc_entloop_body / fdc_useslot_body — create's directory-slot scan + claim.
; Position-free: reached only by fat.asm's `fdc_entloop`/`fdc_useslot` veneers.
; Kept contiguous, same relative order (M21a-RC-1 convention). Neither falls through
; (each ends in an absolute jp), so the relocation is byte-for-byte behaviour-neutral.
; p0_env_tab — the page-0 RST/CALLF/INT vector template, read by lay_page0_env
; THROUGH the ROM page (`ld hl, p0_env_tab`; pageenv.asm). Formerly pinned at $7FB7,
; straddling the FDC window (its head entries read back as register garbage, tolerated
; only empirically); now fully clear of every window so EVERY entry reads correctly.
; The $0030 entry points DIRECTLY at callf_body_body (M22a: no intermediate veneer).
; (cell, handler) pairs; terminated by a 0 cell. No two JP triples overlap.
p0_env_tab:
                dw      $000C, rdslt_h  ; RST 8  RDSLT  (read byte from a slot)
                dw      $0014, wrslt_h  ; RST 10 WRSLT  (write byte to a slot)
                dw      $001C, calslt_h ; RST 18 CALSLT (inter-slot call)
                dw      $0024, enaslt_h ; ENASLT (enable slot in a page)
                dw      $0030, callf_body_body ; RST 30 CALLF (M22a: direct, no veneer)
                dw      $0038, INT_H_HIRAM ; maskable-int vector -> A-3 high-RAM handler
                                           ; (NOT page-1 int_h: page 1 is reclaimed by the TPA)
                dw      0               ; end of table

; ===== M28 (tier2-m28-blockrandom-spec.md): $23 FSIZE + $26 WRBLK ===============
; Completes the block/random FCB surface: a real GET FILE SIZE and a real RANDOM
; BLOCK WRITE. Both land here, in the same free-region corridor as the FDC-window
; fix bodies (0 canonical entries, no FDC window) -- net-zero, `ds $75A5 - $` below
; still pins k_75A5 exactly.

; ff_secloop..ff_found — RELOCATED VERBATIM from disk/fat.asm's old $47B9-$4828 span
; (M28 §3.1/§4, [LANDED-B]). $47BE (5 bytes inside the old ff_secloop, the `jr z,
; ff_notfound`) is the kernel's FIXED canonical $26 WRBLK dispatch entry -- a
; collision freed the same way the FDC-window fix and M26 free colliding canonical
; addresses: relocate OUR code, not the kernel's $D8BE dispatch table (not ours to
; edit). Position-free: reached only by fat_find_body's `jp ff_secloop` (runtime.asm)
; and its own internal `jr ff_secloop` back-edge; every ff_* label below is local to
; this block, so the whole unit moves as one byte-identical piece (no jr/jp
; conversions needed -- unlike fdc_entloop_body/fdc_useslot_body, which split into
; two separately-addressed routines, this block keeps its single entry point).
; fsize_body — MSX-DOS-1 kernel FSIZE ($23) canonical entry $501E's real body
; (M28 §3.2). Wired IN PLACE at $501E (dead-$00 pad, no relocation -- [LANDED-B]).
; Entry: DE=$DA40 (kernel 37-byte FCB copy, name pre-filled at copy+1..11),
; A=$25/B=$00/C=$00, ret=$D88A -- same dispatcher class as $4788/$4793 (M26).
; Locates the file (fat_mount + fat_find, reused wholesale from the existing dir
; search) and sets copy+33..35 = ceil(size/128) as a 24-bit little-endian count;
; not found -> A=L=$FF (map.grauw.nl _FSIZE contract). The prior stub returned a
; constant A=L=$03 for every input and never searched or wrote the field at all.
; CLEAN-ROOM: reuses fat_mount/fat_find (our own, pre-existing) + the published
; GET FILE SIZE contract; no stock routine internals decoded.
fsize_body:
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer ($DA40)
                push    ix
                pop     de
                call    fat_mount
                jp      c, fsize_miss
                push    ix
                pop     de
                inc     de                  ; DE -> copy+1 (11-byte 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found -> FAT_FILESIZE set
                jp      c, fsize_miss
                ; r0..r2 := ceil(FAT_FILESIZE / 128) = (size + 127) >> 7, 24-bit.
                ld      hl, (FAT_FILESIZE)
                ld      de, (FAT_FILESIZE + 2)
                ld      bc, 127
                add     hl, bc
                jr      nc, fsize_noc
                inc     de
fsize_noc:
                ; 32-bit DE:HL >>= 7 (7 iterations of a whole-value logical shift right;
                ; the discarded top byte, D, is always 0 for any file this ROM's FAT12
                ; volumes can hold).
                ld      b, 7
fsize_shift:
                srl     d
                rr      e
                rr      h
                rr      l
                djnz    fsize_shift
                ; r0..r2 = low 24 bits of DE:HL = L, H, E (LE)
                ld      (ix+33), l
                ld      (ix+34), h
                ld      (ix+35), e
                xor     a                   ; A = 0 = found
                ld      l, a                ; L := A (A=L=0, the pinned success contract)
                jp      rrnd_finish         ; jp: rrnd_finish is far below (out of jr range)
fsize_miss:
                ld      a, $FF
                ld      l, a                ; L := A (A=L=$FF, not-found)
                jp      rrnd_finish

; ===========================================================================
; $26 WRBLK — RANDOM BLOCK WRITE (M28 §3.3, [LANDED-A]/[LANDED-B])
; ===========================================================================
; wrblk_body — the real $47BE canonical WRBLK entry. Entry: DE=$DA40 (kernel FCB
; copy), HL = requested record count, A=$26/B=$00/C=$00, ret=$D88A. Contract
; ([LANDED-A]): RS = copy+14..15 (0 -> 128); start record RR = copy+33..35
; (24-bit LE); byte budget = (HL*RS) & $FFFF; CR/EX (copy+32/+12) untouched;
; past-EOF writes grow the file with a CONTIGUOUS FAT chain through the gap (no
; sparse holes; gap bytes stay whatever was already on disk -- no zero-fill);
; size := max(old, new_RR*RS); RR += HL_REQUESTED (not actual -- the write-side
; advance asymmetry vs RDBLK's actual-based advance); return A=0, HL = the
; ORIGINAL requested count (preserved, carries no result). HL=0 is a size-only
; call: RR-at-or-past-EOF just bumps the size field (no data, no chain change);
; RR-before-EOF is the SHRINK path, which stock gets wrong (leaves the FAT
; inconsistent -> a later FCLOSE fails) -- signed off (§6 Q3) to do the SANE
; thing instead: free the tail chain + EOF-mark so FCLOSE keeps succeeding. This
; is an INTENTIONAL, DOCUMENTED divergence from stock's known-broken behaviour,
; not a regression (see tier2-bdos-coverage.md).
; Unlike RDRND/WRRND (which only reuse the kernel's OWN preceding FOPEN state,
; FAT_FIRSTCLUS/FAT_FILESIZE, never touching the directory entry), WRBLK must
; persist size/first-cluster back to disk -- so it re-locates the entry itself
; (fat_mount + fat_find on copy+1..11) to recover FAT_DIRSEC/a dirent offset for
; fat_dir_update, exactly like fsize_body/fopen_fill_body/fren_body already do.
; This also freshly re-confirms FAT_FIRSTCLUS/FAT_FILESIZE (redundant with the
; kernel's own FOPEN for the same file, but harmless) before the per-record loop.
; CLEAN-ROOM: reuses fat_mount/fat_find/fat_alloc_cluster/fat_next_cluster/
; fat_write_fat_entry/fat_dir_update/write_sector (our own, pre-existing) + the
; published RANDOM BLOCK WRITE contract (map.grauw.nl) + the [LANDED-A] oracle
; contract; no stock routine internals decoded.
wrblk_body:
                ld      (WRBLK_REQ), hl     ; capture the requested count FIRST -- everything
                                            ; below clobbers HL (fat_mount/fat_find/the multiply)
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer ($DA40)
                push    ix
                pop     de
                call    fat_mount
                jp      c, wrblk_ioerr
                push    ix
                pop     de
                inc     de                  ; DE -> copy+1 (11-byte 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found -> FAT_FIRSTCLUS/FAT_FILESIZE set
                jp      c, wrblk_ioerr
                ; recover the dirent's own location for the eventual fat_dir_update
                ; (fat_find leaves HL -> the matched entry inside SECTOR_BUF).
                ld      de, SECTOR_BUF
                or      a
                sbc     hl, de
                ld      (BDOS_DIROFF), hl
                ld      hl, (FAT_DIRSEC)
                ld      (BDOS_DIRSEC), hl
                ; reseed our own DTA cell (M19 lesson: the kernel's real SETDTA only
                ; ever touches DOS_DTAPTR, never BDOS_DTA).
                ld      hl, (DOS_DTAPTR)
                ld      (BDOS_DTA), hl
                ; resolve RS := copy+14..15, 0 -> 128 (RECSIZE)
                ld      a, (ix+14)
                ld      e, a
                ld      a, (ix+15)
                ld      d, a
                ld      a, d
                or      e
                jr      nz, wrblk_rs_ok
                ld      de, RECSIZE
wrblk_rs_ok:
                ld      (WRBLK_RS), de
                ; load RR (24-bit, copy+33..35) into WRBLK_REC
                ld      a, (ix+33)
                ld      (WRBLK_REC), a
                ld      a, (ix+34)
                ld      (WRBLK_REC + 1), a
                ld      a, (ix+35)
                ld      (WRBLK_REC + 2), a
                ; HL_requested == 0 ? -> size-only / shrink path (no per-record loop)
                ld      hl, (WRBLK_REQ)
                ld      a, h
                or      l
                jp      z, wrblk_zero_path
                ld      (WRBLK_CNT), hl
                ; M29: reset the position cursor once before the per-record loop
                ; starts -- wrblk_position_ext will (re)validate it on its first
                ; call this wrblk_body invocation (wrblk_zero_path never calls
                ; wrblk_position_ext, so this is unreached/irrelevant there).
                xor     a
                ld      (WRBLK_CURVALID), a
; --- main per-record loop: position (extending through any gap), overlay RS DTA
; bytes at the record's (rec&3)*128 slot within its 512-byte sector, persist. ---
wrblk_loop:
                ld      hl, (WRBLK_CNT)
                ld      a, h
                or      l
                jp      z, wrblk_loop_done
                call    wrblk_position_ext  ; Cy=0 ok, SECTOR_BUF <- target sector's bytes
                jp      c, wrblk_full
                ld      a, (WRBLK_RECSEC)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = WRBLK_RECSEC * 128 (0/128/256/384)
                ld      de, SECTOR_BUF
                add     hl, de
                ex      de, hl              ; DE = dest in SECTOR_BUF
                ld      hl, (BDOS_DTA)      ; HL = source record in the caller's DTA
                ld      bc, (WRBLK_RS)
                ldir
                call    rrnd_sector         ; DE = absolute logical sector to persist
                                            ; (reused unchanged: pure function of
                                            ; FAT_CURCLUS/FAT_CLUSSEC, valid regardless
                                            ; of how they were last set)
                ld      hl, SECTOR_BUF
                call    write_sector
                jp      c, wrblk_ioerr
                ; advance DTA by RS
                ld      hl, (BDOS_DTA)
                ld      de, (WRBLK_RS)
                add     hl, de
                ld      (BDOS_DTA), hl
                ; WRBLK_REC += 1 (24-bit)
                ld      hl, (WRBLK_REC)
                inc     hl
                ld      (WRBLK_REC), hl
                ld      a, h
                or      l
                jr      nz, wrblk_reci_noc
                ld      a, (WRBLK_REC + 2)
                inc     a
                ld      (WRBLK_REC + 2), a
wrblk_reci_noc:
                ld      hl, (WRBLK_CNT)
                dec     hl
                ld      (WRBLK_CNT), hl
                jp      wrblk_loop
wrblk_loop_done:
                ; new_RR := RR_start + HL_requested (24-bit + 16-bit)
                ld      a, (ix+33)
                ld      l, a
                ld      a, (ix+34)
                ld      h, a
                ld      de, (WRBLK_REQ)
                add     hl, de
                ld      (ix+33), l
                ld      (ix+34), h
                ld      a, (ix+35)
                adc     a, 0
                ld      (ix+35), a
                ; size := max(old size, new_RR * RS)
                call    wrblk_mul_rr_rs     ; WRBLK_MULACC := (ix+33..35, = new_RR) * RS
                call    wrblk_size_max
                call    wrblk_set_wrfirst
                call    fat_dir_update
                jp      c, wrblk_ioerr2
                xor     a
                ld      hl, (WRBLK_REQ)
                jp      wrblk_finish
wrblk_zero_path:
                ; HL_requested == 0: compute target := RR (unchanged) * RS, then either
                ; grow-or-hold (target >= old size) or shrink (target < old size). RR
                ; itself is NOT advanced (+= 0, a no-op) per [LANDED-A].
                call    wrblk_mul_rr_rs     ; WRBLK_MULACC := (ix+33..35, = RR unchanged) * RS
                ; compare WRBLK_MULACC vs FAT_FILESIZE (32-bit unsigned, MSB first)
                ld      a, (WRBLK_MULACC + 3)
                ld      hl, FAT_FILESIZE + 3
                cp      (hl)
                jr      nz, wzp_decided
                ld      a, (WRBLK_MULACC + 2)
                dec     hl
                cp      (hl)
                jr      nz, wzp_decided
                ld      a, (WRBLK_MULACC + 1)
                dec     hl
                cp      (hl)
                jr      nz, wzp_decided
                ld      a, (WRBLK_MULACC)
                dec     hl
                cp      (hl)
wzp_decided:
                jr      c, wzp_shrink       ; MULACC < FAT_FILESIZE -> shrink path
                call    wrblk_size_max      ; MULACC >= old size -> grow-or-hold (no chain change)
                call    wrblk_set_wrfirst
                jr      wzp_dirupdate
wzp_shrink:
                call    wrblk_shrink        ; frees the tail chain + EOF-marks; sets
                                            ; BDOS_WRBYTES itself (not via wrblk_size_max)
                jp      c, wrblk_ioerr2
                call    wrblk_set_wrfirst
wzp_dirupdate:
                call    fat_dir_update
                jp      c, wrblk_ioerr2
                xor     a
                ld      hl, (WRBLK_REQ)     ; = 0
                jp      wrblk_finish
wrblk_full:
                ld      a, 1                ; disk-full path ([C]-only, not black-box-provoked)
                ld      hl, (WRBLK_REQ)
                jp      wrblk_finish
wrblk_ioerr:
wrblk_ioerr2:
                ld      a, 2                ; generic FDC I/O error (fdc_read_data convention)
                ld      hl, (WRBLK_REQ)
wrblk_finish:                              ; shared tail: M20 dispatcher-flag rule, preserve A/HL
                push    af
                push    hl
                xor     a
                ld      ($F306), a
                pop     hl
                pop     af
                ret

; wrblk_position_ext — position (or extend) the file's iterator to record
; WRBLK_REC (24-bit). M29 (tier2-m29-wrblk-position-cursor-spec.md): keeps an
; incremental cursor (WRBLK_CURVALID/WRBLK_CURSEC) across calls within one
; wrblk_body invocation instead of re-fat_open-ing and re-walking from the head
; every time -- WRBLK_REC is strictly non-decreasing per call (kernel.asm:884),
; so the target sector-in-file is always >= the cursor's last position. First
; call this wrblk_body invocation (or any call once positioned) still walks
; forward via wrblk_read_or_extend_sector exactly as the old from-head walk did;
; only the redundant re-walk of already-visited sectors is elided. Unlike
; rrnd_position, EXTENDS the chain contiguously through any gap instead of
; returning EOF ([LANDED-A]/§6 Q2 full past-EOF extend).
;   out: Cy = 0 ok (SECTOR_BUF holds the target sector's current on-disk bytes --
;        a freshly allocated sector reads back whatever is already on the disk,
;        "uninitialised", no zero-fill, EXCEPT the delta==0 same-sector case,
;        where SECTOR_BUF already holds it from the previous call -- no I/O);
;        Cy = 1 = disk full / I/O error
;        WRBLK_RECSEC := WRBLK_REC & 3 (record-in-sector; the codebase's fixed
;        4-records/512-byte-sector convention -- independent of RS, which only
;        scales the byte quantity copied per record and the RR/byte-budget
;        bookkeeping, per spec §3.3)
wrblk_position_ext:
                ld      a, (WRBLK_REC)
                and     3
                ld      (WRBLK_RECSEC), a
                ; target sector-in-file = WRBLK_REC >> 2 (24-bit value; D:E:A below)
                ld      a, (WRBLK_REC + 2)
                ld      d, a
                ld      a, (WRBLK_REC + 1)
                ld      e, a
                ld      a, (WRBLK_REC)
                ld      b, 2
wpe_shr:
                srl     d
                rr      e
                rra
                djnz    wpe_shr
                ; D:E:A = target sector-in-file; D is always 0 for any file this ROM's
                ; FAT12 (720K-class floppy) volumes can hold, so BC below is a safe
                ; 16-bit sector-in-file count.
                ld      c, a
                ld      b, e                ; BC = target_sec (16-bit; D/high byte always 0)
                ld      a, (WRBLK_CURVALID)
                or      a
                jr      z, wpe_fresh
                ; --- cursor valid: incremental path, no fat_open ---------------
                push    bc                  ; save target_sec
                pop     hl                  ; HL = target_sec
                ld      de, (WRBLK_CURSEC)
                or      a
                sbc     hl, de              ; HL = target_sec - WRBLK_CURSEC (>=0, monotonic)
                ld      a, h
                or      l
                jr      z, wpe_same         ; delta==0 -> already positioned, no I/O
                ; delta >= 1: advance HL steps via wrblk_read_or_extend_sector
                ld      (WRBLK_CURSEC), bc  ; bc still holds target_sec
                ex      de, hl              ; DE = delta
wpe_adv:
                push    de                  ; wrblk_read_or_extend_sector clobbers BC/DE
                                            ; internally (wroe_mul's djnz counter) -- same
                                            ; save/restore rrnd_position uses around
                                            ; fat_read_file_sector for the identical reason
                call    wrblk_read_or_extend_sector
                pop     de
                ret     c
                dec     de
                ld      a, d
                or      e
                jr      nz, wpe_adv
                ret                         ; Cy=0 (wrblk_read_or_extend_sector cleared it)
wpe_same:
                or      a                   ; Cy=0, no I/O -- SECTOR_BUF already holds
                ret                         ; the target sector from the previous call
wpe_fresh:
                call    fat_open            ; iterator -> FAT_FIRSTCLUS, clussec 0
                ld      (WRBLK_CURSEC), bc
                ld      a, 1
                ld      (WRBLK_CURVALID), a
                inc     bc                  ; BC = walk-loop count (>=1; sector 0 needs 1 step)
wpe_walk:
                push    bc                  ; wrblk_read_or_extend_sector clobbers BC
                                            ; internally (wroe_mul's djnz counter) -- same
                                            ; save/restore rrnd_position uses around
                                            ; fat_read_file_sector for the identical reason
                call    wrblk_read_or_extend_sector
                pop     bc
                ret     c
                dec     bc
                ld      a, b
                or      c
                jr      nz, wpe_walk
                ret

; wrblk_read_or_extend_sector — like fat.asm's fat_read_file_sector, but when the
; chain runs out (cluster<2 empty-file case, or cluster>=$0FF8 end-of-chain) this
; ALLOCATES a new cluster and links it CONTIGUOUSLY instead of returning EOF. Does
; NOT modify fat_read_file_sector itself (kept byte-identical -- same non-goal
; precedent as M26): a parallel routine, reusing fat_advance/fat_next_cluster/
; fat_alloc_cluster/fat_write_fat_entry. Captures FAT_CURCLUS BEFORE this step's
; own advance/allocate (WRBLK_PREVCLUS) so a freshly allocated cluster links onto
; the TRUE last-good cluster, not a stale EOC/free value fat_advance may have just
; produced; also seeds FAT_FIRSTCLUS when the allocation is the file's very first
; cluster (empty file), so a LATER call in the same wrblk_body loop (re-fat_opens
; every record) walks the newly-grown chain correctly.
;   out: Cy = 0 ok (SECTOR_BUF holds the sector's current on-disk bytes); Cy = 1 =
;        disk full / I/O error
wrblk_read_or_extend_sector:
                ld      hl, (FAT_CURCLUS)
                ld      (WRBLK_PREVCLUS), hl
                ld      a, (FAT_CLUSSEC)
                ld      hl, FAT_SECPERCLUS
                cp      (hl)
                jr      c, wroe_incluster
                call    fat_advance
wroe_incluster:
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                jr      c, wroe_need_extend ; cluster < 2 (free / empty file)
                ld      hl, (FAT_CURCLUS)
                ld      de, $0FF8
                or      a
                sbc     hl, de
                jr      nc, wroe_need_extend ; cluster >= $0FF8 = end-of-chain
                jr      wroe_have_valid
wroe_need_extend:
                call    fat_alloc_cluster   ; HL = new cluster; Cy=1 disk full
                ret     c
                ld      de, (WRBLK_PREVCLUS)
                ld      a, d
                or      e
                jr      z, wroe_first
                push    hl                  ; save new cluster
                ex      de, hl              ; HL = previous (last-good) cluster
                pop     de                  ; DE = new cluster (link value)
                push    de
                call    fat_write_fat_entry ; previous -> new
                pop     hl                  ; HL = new cluster
                ret     c
                jr      wroe_have_new
wroe_first:
                ld      (FAT_FIRSTCLUS), hl ; file's very first cluster (was empty)
wroe_have_new:
                ld      (FAT_CURCLUS), hl
                xor     a
                ld      (FAT_CLUSSEC), a
wroe_have_valid:
                ; sector = firstData + (cluster-2)*secPerClus + clussec (identical
                ; tail shape to fat_read_file_sector/frs_mul_body -- deliberately NOT
                ; shared/modified, a new parallel routine per the §4 non-goal precedent)
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                ex      de, hl              ; DE = cluster - 2
                ld      hl, 0
                ld      a, (FAT_SECPERCLUS)
                ld      b, a
wroe_mul:
                add     hl, de
                djnz    wroe_mul            ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (FAT_CLUSSEC)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl
                ld      hl, SECTOR_BUF
                call    read_sector
                ret     c
                ld      a, (FAT_CLUSSEC)
                inc     a
                ld      (FAT_CLUSSEC), a
                or      a                   ; Cy = 0 success
                ret

; wrblk_mul_rr_rs — WRBLK_MULACC(32-bit LE, WBUF+500) := RR(24-bit, ix+33..35) *
; RS(16-bit, WRBLK_RS). Classic LSB-first shift-add multiply, 24 iterations: a
; 32-bit zero-extended copy of RS (WRBLK_MULOP, WBUF+504) is doubled each
; iteration and added into WRBLK_MULACC whenever the corresponding bit of a
; shifting 24-bit copy of RR (WRBLK_MULN, WBUF+508) is 1. Deliberately
; register-free (RAM-only state) so every step is an independently-checkable
; byte operation -- host-unit-tested (tests/test_wrblk_mul.py). Runs after
; fat_find's SECTOR_BUF scan and before fat_dir_update's own WBUF read/write, so
; WBUF's tail is safe transient scratch here (§ equates.inc note).
;   out: WRBLK_MULACC = the 32-bit product; trashes AF, BC, DE, HL
wrblk_mul_rr_rs:
                xor     a
                ld      (WRBLK_MULACC), a
                ld      (WRBLK_MULACC + 1), a
                ld      (WRBLK_MULACC + 2), a
                ld      (WRBLK_MULACC + 3), a
                ld      hl, (WRBLK_RS)
                ld      (WRBLK_MULOP), hl
                xor     a
                ld      (WRBLK_MULOP + 2), a
                ld      (WRBLK_MULOP + 3), a
                ld      a, (ix+33)
                ld      (WRBLK_MULN), a
                ld      a, (ix+34)
                ld      (WRBLK_MULN + 1), a
                ld      a, (ix+35)
                ld      (WRBLK_MULN + 2), a
                ld      b, 24
wmr_loop:
                ld      a, (WRBLK_MULN)
                and     1
                jr      z, wmr_noadd
                ld      a, (WRBLK_MULACC)
                ld      hl, WRBLK_MULOP
                add     a, (hl)
                ld      (WRBLK_MULACC), a
                ld      a, (WRBLK_MULACC + 1)
                inc     hl
                adc     a, (hl)
                ld      (WRBLK_MULACC + 1), a
                ld      a, (WRBLK_MULACC + 2)
                inc     hl
                adc     a, (hl)
                ld      (WRBLK_MULACC + 2), a
                ld      a, (WRBLK_MULACC + 3)
                inc     hl
                adc     a, (hl)
                ld      (WRBLK_MULACC + 3), a
wmr_noadd:
                ld      a, (WRBLK_MULN + 2)
                srl     a
                ld      (WRBLK_MULN + 2), a
                ld      a, (WRBLK_MULN + 1)
                rra
                ld      (WRBLK_MULN + 1), a
                ld      a, (WRBLK_MULN)
                rra
                ld      (WRBLK_MULN), a
                ld      a, (WRBLK_MULOP)
                add     a, a
                ld      (WRBLK_MULOP), a
                ld      a, (WRBLK_MULOP + 1)
                adc     a, a
                ld      (WRBLK_MULOP + 1), a
                ld      a, (WRBLK_MULOP + 2)
                adc     a, a
                ld      (WRBLK_MULOP + 2), a
                ld      a, (WRBLK_MULOP + 3)
                adc     a, a
                ld      (WRBLK_MULOP + 3), a
                djnz    wmr_loop
                ret

; wrblk_size_max — BDOS_WRBYTES(32) := max(FAT_FILESIZE, WRBLK_MULACC). Simple
; 32-bit unsigned compare (MSB byte first); copies the winner into BDOS_WRBYTES.
wrblk_size_max:
                ld      a, (WRBLK_MULACC + 3)
                ld      hl, FAT_FILESIZE + 3
                cp      (hl)
                jr      nz, wsm_decided
                ld      a, (WRBLK_MULACC + 2)
                dec     hl
                cp      (hl)
                jr      nz, wsm_decided
                ld      a, (WRBLK_MULACC + 1)
                dec     hl
                cp      (hl)
                jr      nz, wsm_decided
                ld      a, (WRBLK_MULACC)
                dec     hl
                cp      (hl)
wsm_decided:
                jr      c, wsm_keepold      ; MULACC < FILESIZE -> old size wins
                ld      hl, WRBLK_MULACC
                ld      de, BDOS_WRBYTES
                ld      bc, 4
                ldir
                ret
wsm_keepold:
                ld      hl, FAT_FILESIZE
                ld      de, BDOS_WRBYTES
                ld      bc, 4
                ldir
                ret

; wrblk_set_wrfirst — BDOS_WRFIRST := FAT_FIRSTCLUS (may have just been updated by
; wrblk_read_or_extend_sector's very-first-cluster case, or zeroed by wrblk_shrink's
; empty-file case) -- the field fat_dir_update stamps into the dirent's first-
; cluster word.
wrblk_set_wrfirst:
                ld      hl, (FAT_FIRSTCLUS)
                ld      (BDOS_WRFIRST), hl
                ret

; wrblk_shrink — HL_requested==0 and the target size (WRBLK_MULACC, already =
; RR*RS) is BEFORE the file's current end -- shrink to that size ([LANDED-A]/§6
; Q3 "DO THE SANE THING": stock corrupts the FAT here so a later FCLOSE fails;
; ours frees the tail chain + EOF-marks the new last cluster so FCLOSE keeps
; succeeding -- an INTENTIONAL, DOCUMENTED divergence from stock, not a
; regression). Sets BDOS_WRBYTES itself (the target size) -- does NOT go through
; wrblk_size_max, which would wrongly keep the OLD (larger) size.
;   out: Cy = 0 ok, Cy = 1 = I/O error
wrblk_shrink:
                ld      hl, WRBLK_MULACC
                ld      de, BDOS_WRBYTES
                ld      bc, 4
                ldir                        ; BDOS_WRBYTES := target size
                ld      a, (WRBLK_MULACC)
                ld      hl, WRBLK_MULACC + 1
                or      (hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)                ; Z iff target size == 0 (all 4 bytes)
                jp      z, wshrink_empty
                ; keep_sectors = ceil(target_size / 512) = (target_size + 511) >> 9
                ld      hl, (WRBLK_MULACC)
                ld      de, 511
                add     hl, de
                ld      a, (WRBLK_MULACC + 2)
                adc     a, 0                ; A:HL = target_size + 511 (24-bit-safe)
                ld      l, h
                ld      h, a                ; HL = (target_size+511) >> 8
                srl     h
                rr      l                   ; HL = (target_size+511) >> 9 = keep_sectors
                ; keep_clusters = ceil(keep_sectors / SECPERCLUS), repeated subtraction
                ; (SECPERCLUS is a small BPB constant; keep_sectors is bounded to a
                ; floppy's few-thousand-sector range -- cheap either way)
                ld      a, (FAT_SECPERCLUS)
                ld      c, a
                ld      b, 0                ; BC = SECPERCLUS
                push    bc
                pop     de
                dec     de
                add     hl, de              ; HL = keep_sectors + SECPERCLUS - 1
                ld      de, 0               ; DE = quotient accumulator
wshrink_divloop:
                or      a
                sbc     hl, bc
                jr      c, wshrink_divdone
                inc     de
                jr      wshrink_divloop
wshrink_divdone:
                ld      (WRBLK_KEEPCNT), de ; keep_clusters (>= 1, since target size > 0)
                ld      hl, (FAT_FIRSTCLUS)
wshrink_walk:
                ld      de, (WRBLK_KEEPCNT)
                dec     de
                ld      a, d
                or      e
                jr      z, wshrink_atlast   ; consumed keep_clusters-1 steps -> HL = last-to-keep
                ld      (WRBLK_KEEPCNT), de
                call    fat_next_cluster
                push    hl
                ld      de, $0FF8
                or      a
                sbc     hl, de
                pop     hl
                jr      nc, wshrink_atlast  ; chain shorter than expected -- stop defensively
                jr      wshrink_walk
wshrink_atlast:
                ; HL = the cluster to KEEP as the file's new (and only surviving) tail.
                push    hl
                call    fat_next_cluster    ; HL := its CURRENT link (the old tail start)
                ld      (WRBLK_NEXTCLUS), hl
                pop     hl                  ; HL = the keep-cluster
                ld      de, EOC
                call    fat_write_fat_entry ; keep-cluster := EOC in every FAT copy
                jp      c, wshrink_ioerr
                ld      hl, (WRBLK_NEXTCLUS)
                jr      wshrink_freeloop
wshrink_empty:
                ld      hl, (FAT_FIRSTCLUS) ; HL = old first cluster (the whole chain to free)
                push    hl
                ld      hl, 0
                ld      (FAT_FIRSTCLUS), hl ; file becomes clusterless
                pop     hl
wshrink_freeloop:
                ld      a, h
                or      l
                jr      z, wshrink_freedone ; HL == 0 -> nothing to free
                push    hl
                ld      de, $0FF8
                or      a
                sbc     hl, de
                pop     hl
                jr      nc, wshrink_freedone ; HL >= $0FF8 (EOC) -> nothing more to free
                push    hl                  ; HL = cluster to free
                call    fat_next_cluster    ; HL := its current link
                ld      (WRBLK_NEXTCLUS), hl
                pop     hl                  ; HL = the cluster to free (restored)
                ld      de, 0
                call    fat_write_fat_entry ; mark it free ($000)
                jp      c, wshrink_ioerr
                ld      hl, (WRBLK_NEXTCLUS)
                jr      wshrink_freeloop
wshrink_freedone:
                or      a
                ret
wshrink_ioerr:
                scf
                ret

; ===== M31: k_47B2 faithful Random Block Read body (tier2-m31-rdblk-randrecord-
; spec.md §3.2) — relocated out of $47B2's cramped span (3b-relocation, the
; M24/M28/M29 idiom); reached only via the k_47B2 veneer's `jp`.
;
; Faithful $27: position to the FCB's random-record field (FCB+33..35), then
; transfer up to HL records of the FCB's record size (FCB+14..15, 0 -> 128),
; zero-padding a final partial record, and report the true delivered count;
; RR is advanced by the delivered count on return (unified contract for both
; boot loaders, at RR=0/RS=1/huge-HL, and any user-level $27 caller, §2/§3.2).
; Register discipline: entry DE = FCB ptr, HL = requested record count. Both
; are needed AFTER we start touching HL/DE for FCB-field reads below, so both
; are parked in dedicated cells immediately (RDBLK_REQ / the FCB ptr survives
; on the stack, popped back for the RR write-back + IY return at the end).
k47b2_body:
                push    de                  ; save entry FCB ptr (RR write-back + IY return)
                ld      (RDBLK_REQ), hl     ; save entry HL = requested record count (step 3)
                ; --- step 2: record size <- FCB+14..15, 0 -> 128 default ----------
                ld      hl, 14
                add     hl, de
                ld      a, (hl)
                ld      (RDBLK_RECSIZE), a
                inc     hl
                ld      a, (hl)
                ld      (RDBLK_RECSIZE + 1), a
                ld      hl, (RDBLK_RECSIZE)
                ld      a, h
                or      l
                jr      nz, k47b2_rs_ok
                ld      hl, RECSIZE
                ld      (RDBLK_RECSIZE), hl
k47b2_rs_ok:
                ; --- step 4: RR start <- FCB+33..35 (24-bit) -> RDBLK_RRSTART -----
                pop     hl                  ; HL = entry FCB ptr (peek without losing it)
                push    hl
                ld      de, 33
                add     hl, de
                ld      de, RDBLK_RRSTART
                ld      bc, 3
                ldir                        ; RDBLK_RRSTART := FCB+33..35
                ; --- step 5: DTA <- (DOS_DTAPTR) -> RDBLK_DST + BDOS_DTA ----------
                ; (M19 lesson: the kernel's real SETDTA only ever touches
                ; DOS_DTAPTR, never our own mini-BDOS's BDOS_DTA cell -- do NOT
                ; trust BDOS_DTA itself here, see k_47B2's original M21b note.)
                ld      hl, (DOS_DTAPTR)
                ld      (BDOS_DTA), hl
                ld      (RDBLK_DST), hl
                ; --- step 6: open + size -------------------------------------------
                call    fat_open            ; re-prime the iterator (FAT_FIRSTCLUS already found)
                ld      hl, (FAT_FILESIZE)
                ld      (BDOS_BYTESLEFT), hl
                ld      hl, (FAT_FILESIZE + 2)
                ld      (BDOS_BYTESLEFT + 2), hl
                ld      hl, 512
                ld      (RDBLK_BUFPOS), hl  ; force a sector refill on the first byte
                ld      hl, 0
                ld      (RDBLK_DONE), hl    ; no records delivered yet
                ; --- step 7: position to record RR ---------------------------------
                ; Skip RR whole records by discarding RS bytes each via the shared
                ; k47b2_nextbyte helper (below), bounded by EOF (no multiply, no
                ; overflow; sector-seek is a deferred optimisation, §3.2 step 7 -- $27
                ; is not a hot loop and files are small). RR is a 24-bit FCB field, but
                ; (same narrowing as the M26 RDRND/WRRND precedent, and this
                ; milestone's realistic-file-size scope) only the low 16 bits of
                ; RDBLK_RRSTART are used as the skip count.
                ; RDBLK_RRSTART must survive UNTOUCHED for step 9's write-back, so the
                ; skip loop counts records SKIPPED SO FAR (0 upward) in RDBLK_DONE
                ; instead of counting RRSTART down -- RDBLK_DONE is otherwise unused
                ; until step 8, and is reset to 0 again right after this loop.
k47b2_pos_recloop:
                ld      hl, (RDBLK_DONE)
                ld      de, (RDBLK_RRSTART)
                or      a
                sbc     hl, de
                jr      z, k47b2_pos_done   ; skipped RR records -> positioned at record RR
                ld      hl, (RDBLK_RECSIZE)
                ld      (RDBLK_CNT), hl     ; bytes to discard for this record
k47b2_pos_byteloop:
                ld      hl, (RDBLK_CNT)
                ld      a, h
                or      l
                jr      nz, k47b2_pos_needbyte
                ld      hl, (RDBLK_DONE)    ; whole record discarded -> count it, next record
                inc     hl
                ld      (RDBLK_DONE), hl
                jr      k47b2_pos_recloop
k47b2_pos_needbyte:
                call    k47b2_nextbyte      ; discard A; Cy=1 -> EOF/chain-end
                jr      c, k47b2_pos_done
                ld      hl, (RDBLK_CNT)
                dec     hl
                ld      (RDBLK_CNT), hl
                jr      k47b2_pos_byteloop
k47b2_pos_done:
                ld      hl, 0
                ld      (RDBLK_DONE), hl    ; reset for step 8's real delivered-count use
                ; --- step 8: transfer loop (zero-pad variant of rdb_recloop_body) --
                ; "Partial record" (>=1 byte already copied this record) is recovered
                ; by comparing RDBLK_CNT (bytes still owed) against RDBLK_RECSIZE (the
                ; full record size): CNT < RECSIZE iff at least one byte already
                ; landed -- no extra flag cell needed (RDBLK_RRSTART's 3 bytes are the
                ; spec's whole free-tail budget, §3.1).
k47b2_xfer_rec:
                ld      hl, (RDBLK_DONE)
                ld      de, (RDBLK_REQ)
                or      a
                sbc     hl, de
                jr      z, k47b2_ok         ; delivered every requested record -> A=0
                ld      hl, (RDBLK_RECSIZE)
                ld      (RDBLK_CNT), hl     ; bytes still to copy for this record
k47b2_xfer_byteloop:
                ld      hl, (RDBLK_CNT)
                ld      a, h
                or      l
                jr      z, k47b2_xfer_recdone       ; whole record copied -> next record
                call    k47b2_nextbyte      ; A = next byte / Cy=1 EOF-or-chain-end
                jr      c, k47b2_xfer_eofcheck
                ld      hl, (RDBLK_DST)
                ld      (hl), a
                inc     hl
                ld      (RDBLK_DST), hl
                ld      hl, (RDBLK_CNT)
                dec     hl
                ld      (RDBLK_CNT), hl
                jr      k47b2_xfer_byteloop
k47b2_xfer_eofcheck:
                ; EOF (or chain-end, treated the same). Partial record (RDBLK_CNT <
                ; RDBLK_RECSIZE, i.e. a byte already copied this record) -> zero-pad
                ; the remainder and COUNT it; clean boundary (CNT == RECSIZE, no bytes
                ; copied) -> EOF without counting this record.
                ld      hl, (RDBLK_CNT)
                ld      de, (RDBLK_RECSIZE)
                or      a
                sbc     hl, de
                jr      z, k47b2_eof        ; clean boundary -> EOF, uncounted
k47b2_xfer_padloop:
                ld      hl, (RDBLK_CNT)
                ld      a, h
                or      l
                jr      z, k47b2_xfer_padded
                ld      hl, (RDBLK_DST)
                ld      (hl), 0
                inc     hl
                ld      (RDBLK_DST), hl
                ld      hl, (RDBLK_CNT)
                dec     hl
                ld      (RDBLK_CNT), hl
                jr      k47b2_xfer_padloop
k47b2_xfer_padded:
                ld      hl, (RDBLK_DONE)
                inc     hl
                ld      (RDBLK_DONE), hl    ; the zero-padded final record counts
                jr      k47b2_eof
k47b2_xfer_recdone:
                ld      hl, (RDBLK_DONE)
                inc     hl
                ld      (RDBLK_DONE), hl
                jr      k47b2_xfer_rec
                ; --- step 9 (8a): one exit, both A values fall through here --------
k47b2_ok:
                xor     a                   ; A = $00 all requested records delivered
                jr      k47b2_return
k47b2_eof:
                ld      a, 1                ; A = $01 EOF-first
k47b2_return:
                ld      e, a                ; E = the 0/1 result, parked here (A itself is
                                            ; clobbered by the 24-bit add below; DE is
                                            ; otherwise dead at this exit) -- restored to
                                            ; A as the very last step before ret.
                ; RR := entry-RR + HL(delivered), write back to FCB+33..35 (24-bit;
                ; carry into the high byte via ADC). At/past EOF, HL=0 -> RR unchanged
                ; (§3.2 step 9). Entry FCB ptr is still on the stack (untouched since
                ; the routine's initial `push de`) -- pop it into IY now: this both
                ; satisfies the IY-return contract AND gives indexed (iy+33/+34/+35)
                ; addressing for the write-back, so the FCB ptr need not be re-derived.
                pop     iy                  ; IY = entry FCB ptr (§5.4/§8.50 IY contract)
                ld      hl, (RDBLK_DONE)    ; HL = records actually delivered
                ld      a, (RDBLK_RRSTART)
                add     a, l
                ld      (iy+33), a
                ld      a, (RDBLK_RRSTART + 1)
                adc     a, h
                ld      (iy+34), a
                ld      a, (RDBLK_RRSTART + 2)
                adc     a, 0
                ld      (iy+35), a
                ; HL = BC = records delivered (the $47B2-boundary count, §1-Q3); HL
                ; itself is already RDBLK_DONE (untouched above -- only A was used for
                ; the 24-bit add), so just copy it to BC.
                ld      b, h
                ld      c, l
                ld      ix, DRVA_DPB        ; IX = $F195 drive-A DPB (§8.50)
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      a, e                ; A = the 0/1 EOF result (restored)
                ret

; k47b2_nextbyte — shared byte-fetch-or-EOF helper (used by BOTH the step-7
; positioning loop and the step-8 transfer loop; folding the BDOS_BYTESLEFT==0
; test + rdblk_getbyte call into one place keeps k47b2_body's two structurally
; identical byte loops small).
;   out: Cy=0, A=the next file byte (BDOS_BYTESLEFT>0; rdblk_getbyte's normal
;        path -- advances BDOS_BYTESLEFT + the sector buffer)
;        Cy=1  BDOS_BYTESLEFT==0 (clean EOF) OR rdblk_getbyte's own chain-end
;        (defensive; caller treats both alike, §3.2 step 7/8)
k47b2_nextbyte:
                ld      hl, BDOS_BYTESLEFT
                ld      a, (hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)
                jr      nz, k47b2_nextbyte_get      ; BDOS_BYTESLEFT != 0 -> fetch for real
                scf                                 ; BDOS_BYTESLEFT == 0 -> Cy=1, clean EOF
                ret
k47b2_nextbyte_get:
                jp      rdblk_getbyte       ; tail-call: A=byte/Cy=0, or Cy=1 chain-end;
                                            ; either way its own `ret` is our `ret` too

; wrseq_writeback — M33 (tier2-m33-m32-fcb-position-spec.md §2.2): mirror the
; sequential-read iterator's position into the kernel FCB copy at the fixed
; base $DA40 after a DELIVERED RDSEQ record (wrseq_body's read branch calls
; this only when A=$00; see wrseq_body above). K = BDOS_SEQREC after this
; call's increment (records delivered so far, 1-based).
;   copy+32 (CR)          := K mod 128
;   copy+12 (EX)          := K div 128         (floppy -> fits a byte, §2.2)
;   copy+28/29 (word)     := FAT_CURCLUS       (cluster of the just-read record)
;   copy+30               := (K-1) div recPerClus, recPerClus = FAT_SECPERCLUS*RECPERSEC
; Does not touch copy+14/15/16/17/24/25/26/27/31 (already correct/out of scope,
; §2.2/§1). Leaf routine: preserves A (the caller's bdos_seqread exit code)
; across the whole body; trashes BC/DE/HL/IX (dead in wrseq_body at the call
; site -- bdos_seqread's own exit values are only A, per the dispatcher's
; H:=B,L:=A mirror rule already noted above). PLACEMENT: this position-free
; corridor (same class as fdc_entloop_body/p0_env_tab/ff_secloop above --
; 0 canonical entries, no FDC window, ample slack), not kernel.asm's own tail
; (which is already tight against the $7F80 FDC-window guard).
wrseq_writeback:
                push    af                  ; preserve bdos_seqread's exit A
                ; K := BDOS_SEQREC + 1
                ld      hl, (BDOS_SEQREC)
                inc     hl
                ld      (BDOS_SEQREC), hl   ; HL = K
                push    hl                  ; keep K on the stack (K-1 div needs it again)
                ; copy+32 := K mod 128 (low 7 bits of K's low byte)
                ld      a, l
                and     $7F
                ld      ($DA40+32), a
                ; copy+12 := K div 128 = (HL >> 7), low byte (fits a byte, floppy range)
                pop     hl                  ; HL = K
                push    hl
                ld      b, 7
wsw_shr7:
                srl     h
                rr      l
                djnz    wsw_shr7            ; HL = K >> 7
                ld      a, l
                ld      ($DA40+12), a
                ; copy+28/29 := FAT_CURCLUS (word)
                ld      hl, (FAT_CURCLUS)
                ld      ($DA40+28), hl
                ; copy+30 := (K-1) div recPerClus, recPerClus = FAT_SECPERCLUS*RECPERSEC
                pop     hl                  ; HL = K
                dec     hl                  ; HL = K-1
                ; recPerClus = FAT_SECPERCLUS * RECPERSEC, by repeated addition
                ; (RECPERSEC is a small compile-time constant, currently 4; this
                ; stays correct even if it is ever redefined -- own choice, no
                ; oracle bytes, same idiom as wshrink_divloop's repeated-sub div).
                ld      a, (FAT_SECPERCLUS)
                ld      c, a                ; C = FAT_SECPERCLUS (addend)
                ld      b, RECPERSEC - 1    ; RECPERSEC-1 more additions after the seed
wsw_recperclus:
                add     a, c
                djnz    wsw_recperclus      ; A = FAT_SECPERCLUS * RECPERSEC
                ld      c, a
                ld      b, 0                ; BC = recPerClus
                ld      de, 0               ; DE = quotient accumulator
wsw_divloop:
                or      a
                sbc     hl, bc
                jr      c, wsw_divdone
                inc     de
                jr      wsw_divloop
wsw_divdone:
                ld      a, e                ; quotient fits a byte (floppy record range)
                ld      ($DA40+30), a
                pop     af                  ; restore bdos_seqread's exit A
                ret

; setrnd_body — M32 (tier2-m33-m32-fcb-position-spec.md §3.2): the real BDOS
; $24 SETRND canonical entry ($50C8's body). Entry: DE=IY=$DA40 (kernel FCB
; copy), A=$25 (unused). Computes the CP/M func-36 random record:
;   ex = copy+12 (extent low), s2 = copy+14 (extent high / module 128),
;   cr = copy+32 (current record); rr(24-bit) = cr + ex*128 + s2*4096.
; Written to copy+33 (r0, bits 0-7), copy+34 (r1, bits 8-15), copy+35 (r2,
; bits 16-23). On a floppy s2 is always 0 and rr < 2^16 (r2 normally 0), but
; the math is done in full 24-bit precision per spec (cheap, and correct for
; any s2). INTENTIONAL, DOCUMENTED divergence from stock (§4): stock writes
; the constant rr=1 here; ours computes the true position, which M33 now
; keeps live in copy+12/+32 after every delivered RDSEQ record (before M33
; those were stuck at 0, which would have made this compute 0 too).
; Exit: A=$00, H=$00, L=$00 (M26 dispatcher-class default, §3.3), $F306
; cleared (M24 rule, own inline epilogue -- same pattern as rrnd_finish,
; kept local since this body lives far from that tail label).
setrnd_body:
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer ($DA40)
                ; HL := cr + ex*128 (16-bit; cr<=127, ex<=255 -> max 32767, no
                ; overflow past bit 15).
                ld      a, (ix+12)          ; A = ex
                ld      h, 0
                ld      l, a
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = ex * 128
                ld      a, (ix+32)          ; A = cr
                add     a, l
                ld      l, a
                jr      nc, srb_nocarry1
                inc     h
srb_nocarry1:                               ; HL = cr + ex*128 (rr bits 0..15, s2 not yet added)
                ; s2 contribution (24-bit): s2*4096 = ((s2 & $0F) << 12) [bits 0..15]
                ; + (s2 >> 4) [bits 16..23] -- splits the byte shift-by-12 so no
                ; intermediate exceeds 16 bits.
                ld      a, (ix+14)          ; A = s2
                ld      b, a                ; B = s2 (keep for the >>4 half below)
                and     $0F
                ld      c, a                ; C = s2 & $0F (0..15)
                ld      d, 0
                ld      e, c                ; DE = s2 & $0F
                ld      a, e
                or      d
                jr      z, srb_no_lo_s2     ; low nibble 0 -> skip the <<12 shift/add
                ; DE := (s2 & $0F) << 12 (12 doublings; DE <= 15 so DE never
                ; exceeds 15*4096=61440, safely within 16 bits throughout)
                ld      a, 12
srb_shl12:
                sla     e
                rl      d
                dec     a
                jr      nz, srb_shl12       ; DE = (s2&$0F) * 4096
                add     hl, de              ; HL += (s2&$0F)*4096 (Cy = carry into bit 16)
                jr      srb_have_lo
srb_no_lo_s2:
                or      a                   ; Cy = 0 (nothing added)
srb_have_lo:
                ld      a, 0
                adc     a, 0                ; A = 0/1 = the bit-16 carry, stashed before
                                            ; the shifts below trash the flag
                ld      c, a                ; C = stashed carry
                ld      a, b                ; A = s2 again
                srl     a
                srl     a
                srl     a
                srl     a                   ; A = s2 >> 4 (bits 16..23 contribution)
                add     a, c                ; propagate the stashed bit-16 carry
                                            ; (s2>>4 <= 15, +1 carry never overflows a byte)
                ld      (ix+33), l          ; r0
                ld      (ix+34), h          ; r1
                ld      (ix+35), a          ; r2
                ; Epilogue — match stock's $24 EXIT registers exactly (§3.3, now
                ; pinned by the acceptance capture, NOT part of the intended rr
                ; divergence): stock passes the entry A=$25 dispatcher value
                ; straight through and returns HL=$0000. Clear $F306 (M20 rule).
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule (A=0 here)
                ld      h, a                ; H = $00 (stock exit)
                ld      a, $25              ; exit A = $25 (stock dispatcher passthrough)
                ld      l, a                ; L = $25 (= A; stock's $24 exit HL = $0025,
                                            ; pinned by the BDOSX snap: rec4 A@0361 + L@0367)
                ret

; fat_have_free_cluster — M34 (tier2-m34-wrseq-diskfull-spec.md §3.2): scan-only,
; non-committing sibling of fat_alloc_cluster (fat.asm). Answers "does a $000
; (free) cluster exist anywhere in FAT copy 0?" WITHOUT claiming one -- no
; fat_write_fat_entry call, FAT_ALLOCHINT untouched. Reuses fat_total_clusters
; (scan bound) + fac_entry_from_wbuf (the shared straddle-correct 12-bit
; unpack) + the same FAT-sector-load bookkeeping fac_loop_body uses (FAT_WRTMP
; = total, FAT_WRTMP2 = cached FAT sector, FAT_BYTEIDX/FAT_PARITY/FAT_FATSEC).
; Always scans from cluster 2 (NOT the M30 FAT_ALLOCHINT) so "none free" is
; answered correctly even when the hint has advanced past a since-deleted
; cluster. Does not touch FAT_CURCLUS/FAT_CLUSSEC (the read iterator's own
; cells) -- fac_entry_from_wbuf doesn't either, so this is safe to call from
; bdos_seqwrite_body mid-sequential-write.
;   out: Cy = 0 a free cluster exists; Cy = 1 none (disk full)
; CLEAN-ROOM: our own routine, mirroring fat_alloc_cluster's own scan structure
; (already our own clean-room code) minus the claim step; Microsoft FAT spec
; §3.2 ($000 = free).
fat_have_free_cluster:
                call    fat_total_clusters  ; DE = total clusters (reads boot sector)
                ld      (FAT_WRTMP), de
                ld      hl, $FFFF
                ld      (FAT_WRTMP2), hl    ; cached-sector = none
                ld      hl, 2               ; always scan from cluster 2 (not the hint)
fhfc_loop:
                ld      de, (FAT_WRTMP)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jr      nc, fhfc_none       ; scanned past the last cluster -> none free
                push    hl
                ld      a, l
                and     1
                ld      (FAT_PARITY), a
                ld      e, l
                ld      d, h
                srl     d
                rr      e                   ; DE = cluster >> 1
                add     hl, de              ; HL = fatofs = cluster * 3/2
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a    ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                   ; FAT sector offset = fatofs >> 9
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de              ; HL = absolute FAT sector
                ld      de, (FAT_WRTMP2)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jr      z, fhfc_have_sec    ; already loaded -> no re-read
                ld      (FAT_WRTMP2), hl    ; remember the new cached sector
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                jr      c, fhfc_rderr       ; read error -> treat as no free cluster
fhfc_have_sec:
                pop     hl                  ; HL = cluster
                push    hl
                call    fac_entry_from_wbuf ; DE = entry value
                ld      a, d
                or      e
                pop     hl
                jr      z, fhfc_found       ; $000 -> free
                inc     hl
                jr      fhfc_loop
fhfc_rderr:
                pop     hl                  ; balance the stack (cluster pushed at fhfc_loop)
fhfc_none:
                scf                         ; Cy = 1 -- disk full
                ret
fhfc_found:
                or      a                   ; Cy = 0 -- a free cluster exists
                ret

; wrrnd_extend — M36 (tier2-m35-m36-tierc-fixes-spec.md §M36): WRRND ($22)
; past-EOF file-size extension. Called by wrrnd_body (below, in the kernel.asm
; tail) right after the record's write_sector succeeds, BEFORE the CR side
; effect -- growing the file's recorded size when a random-record write lands
; past the previous end-of-file, exactly like stock. PLACEMENT: this
; position-free corridor (0 canonical entries, no FDC window, ample slack),
; not wrrnd_body's own tail (already tight against the $7F80 FDC-window
; guard) -- same relocation idiom as wrseq_writeback/setrnd_body above.
;
; in:  IX = kernel FCB-copy pointer ($DA40); ix+16..19 = current size (LE),
;      ix+33 = r0 (the record just written, 0..255), ix+1 = 11-byte 8.3 name.
; out: ix+16..19 updated in place if the write extended the file; the on-disk
;      directory entry is patched to match (see step 2). Cy=1 = I/O error
;      finding/writing the directory entry (caller must treat as wrrnd_ioerr);
;      Cy=0 otherwise (including the "no extension needed" no-op path).
; Trashes AF/BC/DE/HL; IX preserved (fat_mount/fat_find/write_sector touch no IX).
;
; Step 1: newsize = max(oldsize, (r0+1)*RECSIZE). (r0+1) is computed as a
; 16-bit value BEFORE the x128 shift (r0 <= 255 -> r0+1 <= 256, safe in HL);
; the product is <= 32768 ($8000), so it always fits 16 bits and its own
; (would-be) +18/+19 word is 0 -- no separate high-word compute needed. If
; the CURRENT size's own high word (ix+18/19) is nonzero, oldsize is already
; >= 65536 > any possible newsize, so old wins outright (skip). Otherwise a
; plain 16-bit unsigned compare of newsize against oldsize's low word decides
; it: newsize <= oldsize skips the whole extension (this is what keeps every
; happy-path within-file WRRND, including BDOSX3 rec18-20, byte-unchanged).
wrrnd_extend:
                ld      a, (ix+18)
                or      (ix+19)
                ret     nz                  ; oldsize >= 65536 -- old wins, no extension
                ld      a, (ix+33)          ; A = r0
                ld      l, a
                ld      h, 0
                inc     hl                  ; HL = r0+1 (<= 256, safe before the x128 shift)
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = (r0+1)*RECSIZE = newsize (<= 32768)
                ld      e, (ix+16)
                ld      d, (ix+17)          ; DE = oldsize (low word; high word already 0 here)
                push    hl                  ; keep newsize
                or      a
                sbc     hl, de              ; HL = newsize - oldsize
                pop     hl                  ; HL = newsize again (sbc preserved it via the push)
                jr      c, wre_noext        ; newsize < oldsize -- no extension
                jr      z, wre_noext        ; newsize == oldsize -- no extension
                ; --- extending: HL = newsize; store into ix+16..19 (+18/+19 = 0) ---
                push    hl                  ; preserve newsize across the dirent-persist work
                ld      (ix+16), l
                ld      (ix+17), h
                ld      (ix+18), 0
                ld      (ix+19), 0
                ; --- Step 3: persist to the on-disk directory entry -----------------
                ; Mirror fren_body's in-place idiom: ensure geometry is mounted, then
                ; fat_find the file's own name (ix+1) -> HL = &dirent in SECTOR_BUF,
                ; FAT_DIRSEC = its sector. Patch dirent+DIRENT_FILESIZE (+28..31) only
                ; -- leave +26/27 (first cluster) and the name untouched (do NOT call
                ; fat_dir_update: it rewrites first-cluster from BDOS_WRFIRST, which is
                ; the SEQUENTIAL-write bookkeeping cell, not meaningful for a file
                ; opened for random access -- WRRND must not touch first-cluster).
                push    ix
                pop     de
                call    fat_mount
                jp      c, wre_ioerr
                push    ix
                pop     de
                inc     de                  ; DE -> FCB+1 (11-byte 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found; HL = &matched dirent (in SECTOR_BUF)
                jp      c, wre_ioerr
                ld      de, DIRENT_FILESIZE
                add     hl, de              ; HL -> dirent+28 (file size field)
                pop     de                  ; DE = newsize (restore across fat_mount/fat_find)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (hl), 0
                inc     hl
                ld      (hl), 0             ; dirent+28..31 = newsize (32-bit LE; hi word 0)
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    write_sector
                ret                         ; Cy propagates: 0 ok, 1 = wre_ioerr's caller test
wre_ioerr:
                pop     de                  ; discard the stacked newsize, keep the stack balanced
                scf
                ret
wre_noext:
                or      a                   ; Cy = 0 -- no extension needed, NOT an error
                ret                         ; (the preceding sbc's Cy/Z must not leak to the caller)

; wrseq_wr_writeback — Item 5 (spec-diskbasic-option-closure.md): the WRITE-side
; twin of wrseq_writeback. Mirrors the SAME FCB-position field set the read
; branch advances, into the fixed FCB copy at $DA40, after a WRITTEN sequential
; record (wrseq_body_write calls this only on A=$00). K = BDOS_SEQREC after this
; call's increment (records written so far, 1-based).
;   copy+32 (CR)      := K mod 128
;   copy+12 (EX)      := K div 128            (floppy -> fits a byte, §2.2)
;   copy+28/29 (word) := BDOS_WRCLUS          (the WRITE iterator's current cluster;
;                        NOT FAT_CURCLUS -- that is the READ iterator's cluster)
;   copy+30           := (K-1) div recPerClus, recPerClus = FAT_SECPERCLUS*RECPERSEC
; Placement/register discipline differ deliberately from wrseq_writeback: this
; lives in the $607B-$75A5 free-region corridor (the `ds $75A5 - $` pad below
; absorbs its size -> net-zero canonical addresses), and it is FULLY
; register-transparent -- preserves AF/BC/DE/HL so wrseq_body_write returns
; bdos_seqwrite's exact registers unchanged (keeps the BDOSX3/BDOSX4 WRSEQ
; register snaps byte-identical; only the FCB position memory moves). The
; source cluster is the ONLY logic difference from the read twin; the CR/EX/+30
; arithmetic is identical (deliberate duplication over sharing: the proven read
; routine stays byte-for-byte untouched, and the corridor has ample slack).
wrseq_wr_writeback:
                push    af
                push    bc
                push    de
                push    hl
                ; K := BDOS_SEQREC + 1
                ld      hl, (BDOS_SEQREC)
                inc     hl
                ld      (BDOS_SEQREC), hl   ; HL = K
                push    hl                  ; keep K (the (K-1) div needs it again)
                ; copy+32 := K mod 128 (low 7 bits of K's low byte)
                ld      a, l
                and     $7F
                ld      ($DA40+32), a
                ; copy+12 := K div 128 = (HL >> 7), low byte (fits a byte, floppy)
                pop     hl                  ; HL = K
                push    hl
                ld      b, 7
wsww_shr7:
                srl     h
                rr      l
                djnz    wsww_shr7           ; HL = K >> 7
                ld      a, l
                ld      ($DA40+12), a
                ; copy+28/29 := BDOS_WRCLUS (word) -- the write iterator's cluster
                ld      hl, (BDOS_WRCLUS)
                ld      ($DA40+28), hl
                ; copy+30 := (K-1) div recPerClus, recPerClus = FAT_SECPERCLUS*RECPERSEC
                pop     hl                  ; HL = K
                dec     hl                  ; HL = K-1
                ld      a, (FAT_SECPERCLUS)
                ld      c, a                ; C = FAT_SECPERCLUS (addend)
                ld      b, RECPERSEC - 1    ; RECPERSEC-1 more additions after the seed
wsww_recperclus:
                add     a, c
                djnz    wsww_recperclus     ; A = FAT_SECPERCLUS * RECPERSEC
                ld      c, a
                ld      b, 0                ; BC = recPerClus
                ld      de, 0               ; DE = quotient accumulator
wsww_divloop:
                or      a
                sbc     hl, bc
                jr      c, wsww_divdone
                inc     de
                jr      wsww_divloop
wsww_divdone:
                ld      a, e                ; quotient fits a byte (floppy record range)
                ld      ($DA40+30), a
                ; copy+16..19 := BDOS_WRBYTES (running file size, 4-byte LE). Stock
                ; maintains the in-memory FCB size on every written record (proven
                ; by the pre-FCLOSE fcbsnap differential, BDOSX8); the read twin
                ; never needed this (FOPEN loads +16..19 from the dirent), but FMAKE
                ; zeroes it, so the write session must grow it here.
                ld      hl, BDOS_WRBYTES
                ld      de, $DA40+16
                ld      bc, 4
                ldir
                ; copy+26/27 := BDOS_WRFIRST (file's first cluster). Also maintained
                ; per stock's post-WRSEQ FCB, and also zero after FMAKE.
                ld      hl, (BDOS_WRFIRST)
                ld      ($DA40+26), hl
                pop     hl
                pop     de
                pop     bc
                pop     af
                ret

; --- the disk ROM's banner line (docs/disk-rom-layout.md) -------------------
; Own text, own code: nothing here is derived from any reference ROM. The only
; external facts are documented BIOS/cartridge interface points already used
; throughout this file -- CHPUT ($00A2) and the disk-ROM entry table, MSX2
; Technical Handbook (see disk/PROVENANCE.md). The placement rule this block
; relies on is our own: docs/disk-rom-layout.md.
; 🧭 2026-09-01 (Joost's call). The CF-3300 prints `Disk BASIC version 1.0` from
; its disk ROM, under the main banner; zerobas printed nothing -- `disk/` held no
; text at all but the "AB" signature. NO VERSION NUMBER: the main banner already
; carries `version 0.1`, and a second one would have to be kept in step with it
; for no benefit.
; 🔴 SITED HERE, IN THE PAD BELOW, AND THAT IS THE WHOLE POINT. The disk ROM is a
; PINNED-ADDRESS layout and its appendable tail is 2 B: three attempts to add
; this inline in `init` drove a `ds $XXXX - $` count NEGATIVE and ran pasmo past
; 64 KB. Code placed immediately BEFORE a pad shrinks that pad by exactly what it
; adds and moves no pinned address at all. `make diskmap` prints where the pads
; are; this one is the largest.
; 🟢 CHPUT direct: during the boot scan page 0 is still the main ROM, so this
; needs none of conout_emit_e's page-0 swap. Every register is preserved because
; `init` falls THROUGH into boot_disk.
disk_show_banner:
                push    af
                push    bc
                push    de
                push    hl
                ld      hl, disk_banner
dsb_lp:
                ld      a,(hl)
                or      a
                jr      z,dsb_end
                inc     hl
                push    hl
                call    CHPUT
                pop     hl
                jr      dsb_lp
dsb_end:
                pop     hl
                pop     de
                pop     bc
                pop     af
                ret
disk_banner:
                db      "zerobas Disk BASIC",13,10,0

; --- hk_present: the handler ALL SEVEN conversion hooks are installed at ------
; D-MKHOOK, docs/spec-basic-nodisk.md §6/§9.
; ⚠️ DELIBERATELY A SPIKE, AND THE SMALLEST ONE THAT PROVES ANYTHING. Nothing in
; zerobas had ever CALLED an installed hook -- HPHYD is installed for foreign
; hosts and never invoked here -- so the whole round trip (main page 1 -> a RAM
; CALLF stub -> RST 30h across slots -> this ROM -> back) was unproven. This body
; therefore does the minimum that is still a real answer: it says "a disk ROM is
; present and claims MKI$".
;
; ⚠️ THE CONVERSIONS THEMSELVES STAY MAIN-SIDE FOR NOW, AND THAT IS A SCOPE
; DECISION RECORDED, NOT AN OVERSIGHT. §8 measured how little can actually move:
; the parse/marshalling half of every one of these verbs calls main PAGE 1
; (`eval`, `str_eval_no`, `ev_sp`, `str_eval_ix`, `cvi_tmm`), which is switched
; OUT while this ROM is mapped. Only the float coercion could follow, and it is
; ~50 B against ~36 B of call overhead. So this slice buys the thing that was
; actually broken -- a diskless build must REFUSE -- and leaves the byte-shuffling
; to a follow-up that has to justify itself on its own.
;
; One body for all seven because today they all answer the same question. When a
; conversion does move here, it gets its own entry and this one keeps the rest.
;
; Contract (own-design signalling over the published layout, §6):
;   in   nothing; the argument is already evaluated and the width is in STRSCR
;   out  CF=1  handled. An unclaimed slot is C-BIOS's `ret`, which leaves CF
;              exactly as the caller set it -- so CF=0 means "no disk ROM".
;   Clobbers nothing but the flags.
hk_present:
                scf
                ret

; --- hk_mkfloat: MKS$/MKD$'s conversion, RUNNING IN THE DISK ROM -------------
; D-DISKABI, docs/spec-basic-nodisk.md §13. The FIRST disk-verb body actually to
; live here rather than merely being gated from here -- which is what Joost asked
; for ("the implementation ... should probably be in the disk rom").
;
; It is possible because this is a PAGE-1 ROM: while we are mapped at
; $4000-$7FFF, page 0 still holds slot 0, so main's LOW REGION is callable by
; absolute address. Those addresses arrive through disk/basic-resident-abi.inc,
; GENERATED per build from build/basic-reloc.sym, so a low-region shift cannot
; leave this routine calling stale ones (`make diskrom-abi-check`).
;
; ⚠️ EVERYTHING CROSSES IN RAM, NOT IN REGISTERS. CALSLT is documented to affect
; most of them, so the width arrives in STRSCR, the value in FAC/FACTYP, and the
; result goes back into STRSCR -- all work-area cells, all mapped throughout.
;   in   STRSCR = the width (4 or 8); FAC/FACTYP = the evaluated argument
;   out  STRSCR+1.. = the packed bytes; CF set (handled)
hk_mkfloat:
                ; ⚠️ THE WIDEN IS NOT HERE, AND THAT IS NOT AN OVERSIGHT.
                ; `widen_rhs_operand` reads the live RHS, which for an INTEGER
                ; argument is DE -- a register CALSLT does not preserve. It runs
                ; main-side; by the time we are entered, ARGA already holds the
                ; widened value and everything we touch is RAM.
                ld      a, (STRSCR)
                cp      4
                jr      nz, hkm_dbl
                call    round_single_and_pack   ; 6-digit half-up round -> single
                jr      hkm_copy
hkm_dbl:
                call    round_and_finalize      ; exact widen -> double
hkm_copy:
                ld      a, (STRSCR)
                ld      c, a
                ld      b, 0
                ld      hl, FAC
                ld      de, STRSCR + 1
                ldir                        ; the packed bytes ARE the string
                scf
                ret

; --- hk_lrset: LSET/RSET's body, RUNNING IN THE DISK ROM --------------------
; docs/spec-basic-nodisk.md §9 for the hook; disk/docs/spec-diskcode-eviction.md
; §7.3-§7.5 for the slice. D-LRSETMOVE, Joost 2026-09-17: *"cut it anyway, it is
; the correct place for it"*.
;
; 🎯 WHAT IS ACTUALLY HERE IS THE FIELD-ENTRY WALK, AND THAT IS THE WHOLE POINT
; OF THE ACCOUNTING IN THE SPEC: of the old 122 B body, ~25 B is disk work and
; the rest is PARSE, which stays in main behind three bundled call-backs. A verb
; that is mostly parse moves almost nothing however the crossings are arranged.
;
;   in   FN_RESUME = the statement cursor, just past the LSET/RSET token
;        LRSET_JUST = 0 left / 1 right, set by main before the gate
;   out  the statement is DONE; FN_RESUME = the resume cursor
;        CF = 1 (claimed), which is what chan_gate tests
;
; ⚠️ THE FLD_TAB ENTRY LAYOUT IS READ HERE AND WRITTEN NOWHERE ELSE IN THIS ROM:
; [chan][key:2][off:2][width]. It is main's table in main's RAM -- this body
; walks it, it does not own it -- so a change to that shape is a change to TWO
; files. basic/field.asm builds it.
; --- hk_field: FIELD's body, RUNNING IN THE DISK ROM -----------------------
; docs/spec-basic-nodisk.md §9 for the hook; disk/docs/spec-diskcode-eviction.md
; §7.3-§7.5 for the slice. D-FIELDMOVE, the last member of the channel trio.
;
; 🎯 THIS IS THE THINNEST HANDLER IN THE ROM AND THAT IS THE FINDING, NOT A
; DEFECT. FIELD is a parse, a channel classify and a write into main's FLD_TAB;
; none of it is disk work, so what moves is the DECISION to run rather than any
; body. It is here because the alternative -- main gating on H_FIELD and then
; doing the job anyway -- discards the answer of any ROM that claims the cell.
;
; 🔑 THE LOOP IS THE REASON THE ITEM BUNDLE RETURNS A CARRY. main's field_item
; parses ONE `w AS v$`, adds it, checks the ERR 50 bound and reports whether a
; comma followed; the crossings therefore scale with the ITEM COUNT (1 + N),
; unlike LSET/RSET's fixed three. A four-field FIELD is five crossings.
;
;   in   FN_RESUME = the statement cursor, just past the FIELD token
;   out  the statement is DONE; FN_RESUME = the resume cursor
;        CF = 1 (claimed), which is what chan_gate tests
;
; ⚠️ FLD_TAB IS NEITHER READ NOR WRITTEN HERE. Joost's rule: main owns the
; table, so FLD_ENTSZ and FLD_TABEND never need hand-mirroring in this ROM --
; the hazard disk/equates.inc's FSECTOR_BUF mirror actually caused (D-LRSETMOVE).
hk_field:
                ld      ix,field_prologue
                call    calbak              ; channel, mode class, table reset
hkf_item:
                ld      ix,field_item
                call    calbak              ; one `w AS v$`; CF=1 -> another follows
                jr      c,hkf_item
                scf
                ret

hk_lrset:
                ld      ix,lrset_tgt
                call    calbak              ; CF=1 -> HL = the FLD_TAB entry;
                jr      nc,hklr_rhs         ; CF=0 -> not fielded, main set up
                ld      a,(hl)              ; chan
                ld      (FLD_CHAN),a        ; non-zero: fld_find never returns a free
                inc     hl
                inc     hl
                inc     hl                  ; -> off lo
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = off
                inc     hl
                ld      a,(hl)              ; width
                ld      (LRSET_W),a
                ld      hl,FSECTOR_BUF
                add     hl,de
                ld      (LRSET_DEST),hl     ; = the field's first byte
hklr_rhs:
                ld      ix,lrset_rhs
                call    calbak              ; the `=` and the RHS expression
                ld      ix,lrset_finish
                call    calbak              ; destination, then the store
                scf
                ret

; --- hk_dskf: DSKF's body, RUNNING IN THE DISK ROM --------------------------
; docs/spec-basic-nodisk.md §9 for the hook, and D-DSKFDRV
; (scratchpad/kwt3_dskfchk.py) for the bound below. D-DSKFMOVE, Joost 2026-09-17:
; *"any keyword implemented by the disk rom should go via the hook to the disk
; rom"*.
;
;   in   FAC          = the drive argument, staged by main because chan_gate
;                       clobbers DE building its own return address
;   out  FAC          = the free cluster count (when DISKOP_STATUS = 0)
;        DISKOP_STATUS= 0 counted, 1 drive out of range -> main raises ERR 62
;        CF = 1 (claimed), which is what chan_gate tests
;
; 📏 THE BOUND IS MEASURED, NOT JUDGED, and it moved here with the code it
; guards: on the CF-3300 drives 0, 1 and 2 are ACCEPTED (0 and 1 answer 707; 2
; prompts for the phantom B:) while 3, 4, 8 and 9 all answer `Bad drive name` --
; four points above the line and two below it. So the rule is `drive <= 2`.
; 🔴 THE CHECK WAS MISSING ENTIRELY RATHER THAN TOO WIDE when D-DSKFDRV added
; it: this tree answered the same 707 for 0, 1 AND 9, so nothing was validating
; the argument at all. ⚠️ WHAT DRIVE 2 *DOES* IS STILL UNMEASURED -- on the
; reference it prompts and WAITS, and a row that prompts eats its successors, so
; the probe excludes it and this only places the REFUSAL boundary.
;
; 🎯 THE COUNT ITSELF IS A CALL-BACK, and that is the honest shape today: main's
; `fat_count_free` is a 13 B stub that dispatches DISKOP_SEL_FAT_COUNT_FREE to
; the SUB ROM's fatprim tenant, so the walk is neither here nor in main. Moving
; the walk itself is part of the 2394 B question (TODO), not of this verb.
hk_dskf:
                ld      de,(FAC)            ; the drive argument
                ld      a,d
                or      a                   ; >255 cannot be a drive
                jr      nz,hkdf_bad
                ld      a,e
                cp      3                   ; 0..2 accepted, 3+ refused
                jr      nc,hkdf_bad
                ld      ix,fat_count_free   ; DE = free clusters, via the tenant
                call    calbak
                ld      (FAC),de
                xor     a
                ld      (DISKOP_STATUS),a   ; counted
                scf
                ret
hkdf_bad:
                ld      a,1
                ld      (DISKOP_STATUS),a   ; main raises ERR 62 `Bad drive name`
                scf
                ret

; --- hk_cv: CVI/CVS/CVD's conversion, RUNNING IN THE DISK ROM ---------------
; docs/spec-basic-nodisk.md §9 (D-MKHOOK) is where these three are established as
; the DISK ROM's verbs rather than ours -- the same section basic/expr.asm's gate
; cites -- and §13 is the ABI hk_mkfloat above follows. The conversion itself is
; measured, not derived: MKS$/MKD$ emit exactly what the variable store holds
; (docs/spec-basic-faczero.md §0, byte-identical on all three machines), so the
; packed bytes ARE the value and the inverse is a copy, not an algorithm.
; D-CVMOVE (Joost, 2026-09-17: *"any keyword implemented by the disk rom should
; go via the hook to the disk rom"*). The inverse of hk_mkfloat above, and it
; lands here for a COMPATIBILITY reason rather than a byte one: until now these
; three hooks were a PRESENCE TEST ONLY -- main did the whole conversion after
; the call returned, so a foreign disk ROM that claimed H_CVI and computed the
; answer had it overwritten on the way out.
;
; ⚠️ EVERYTHING CROSSES IN RAM, NOT IN REGISTERS -- the same ABI hk_mkfloat
; states, for the same reason (CALSLT is documented to affect most of them).
;   in   FACTYP = the width, 2 / 4 / 8 -- the width IS the FACTYP code, so one
;                 cell carries the argument in and the answer's type out
;        STRPTR = the evaluator's DESCRIPTOR pointer, length-checked main-side
;                 (the D-CVITM check stays there: it must fire BEFORE the
;                 descriptor becomes a body pointer)
;   out  width 2:   FAC = the two bytes, FACTYP = 2
;        width 4/8: FAC = the packed value, FACTYP unchanged (= the width)
;        CF set (handled) in both arms
; 🔴 NOTHING CROSSES THROUGH STRSCR, AND THE FIRST CUT OF THIS ROUTINE DID.
; STRSCR is where MKI$/MKS$/MKD$ STAGE THEIR RESULT, so `CVI(MKI$(258))` hands
; this routine a string whose body IS STRSCR+1 -- and marshalling a pointer
; there wrote over the very value being converted. 12 of 32 rows DIFF; the ones
; that stayed green were the arguments that are not staged strings. A ROUND TRIP
; IS WHERE A SHARED SCRATCH BUFFER ALIASES ITSELF.
; 🎯 So the deref happens HERE instead: `pu_deref_body` is in main's LOW REGION
; ($28C1), which stays mapped while this ROM is, so the body can reach it by
; absolute address and nothing has to cross that was not already across.
hk_cv:
                ld      a,(FACTYP)          ; the width
                ld      c,a
                ld      b,0                 ; BC = the byte count for the ldir
                ld      hl,(STRPTR)         ; the descriptor...
                call    pu_deref_body       ; ...and its body (low region: $28C1)
                ld      a,c                 ; ⚠️ RELOAD: the call clobbers A
                cp      2
                jr      nz,hkcv_float
                ld      e,(hl)              ; low byte
                inc     hl
                ld      d,(hl)              ; high byte -- DE = the int (LE)
                ld      (FAC),de
                ld      a,2                 ; CVI returns an int; a float nested in
                ld      (FACTYP),a          ; the string arg must not stick
                scf
                ret
hkcv_float:
                ld      de,FAC
                ldir                        ; the string's bytes ARE the packed value
                scf                         ; FACTYP is already the width
                ret

; --- ; --- install_basic_hooks: claim every BASIC-extension hook this ROM answers --
; Table-driven so init.asm costs ONE call: the pad before its $41EF pin is 31 B
; and seven inline installs need 45. docs/spec-basic-nodisk.md §9.
; Clobbers A, BC, DE, HL.
; --- hk_errp: print the disk error codes this ROM hosts (D-DISKERR) ---------
; Layout source: MSX2 Technical Handbook §2 (the hook table -- H.ERRP $FEFD is the
; error-print hook a disk ROM claims; CALLF stub layout as install_hook) and the
; BIOS entry list (CHPUT $00A2). Texts: black-box CF-3300 (`ERROR 68/69/70`).
; Reached from the errmsg tenant's H_ERRP call with A = ERR code, for codes main
; does not host. Prints the text through CHPUT (BIOS, page 0) and returns CF=1;
; a code that is not ours returns CF=0 and main prints `Unprintable error`.
; Texts measured on the CF-3300 (`ERROR 68/69/70` in a program): `Disk write
; protected`, `Disk I/O error`, `Disk offline`.
hk_errp:
                ld      hl, dk_errtab
hke_lp:
                ld      b, (hl)             ; the row's code; 0 ends the table
                inc     hl
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl
                ld      c, a
                ld      a, b
                or      a
                jr      z, hke_no
                cp      c
                ld      a, c
                jr      nz, hke_lp
                ex      de, hl
hke_pr:
                ld      a, (hl)
                inc     hl
                or      a
                scf                         ; printed: CF=1 (SCF leaves Z alone)
                ret     z
                call    CHPUT
                jr      hke_pr
hke_no:
                or      a                   ; CF=0: not ours
                ret
dk_errtab:
                db      68
                dw      dk_e68
                db      69
                dw      dk_e69
                db      70
                dw      dk_e70
                db      0
dk_e68:         db      "Disk write protected", 0
dk_e69:         db      "Disk I/O error", 0
dk_e70:         db      "Disk offline", 0

; --- fdc_wp_chkrdy: the write path's NOT READY test (D-DISKERR) --------------
; Source: WD2793 data sheet via MSX2 Technical Handbook (type-I status bit 7 =
; NOT READY); the read command reports it on its own, the write command with no
; medium is accepted and completes clean on the emulated FDC (measured, 3/3), so
; the write path asks the seek's status first. Out: CY, A = 2 (not ready) / NC.
fdc_wp_chkrdy:
                ld      a, (FDC_STATUS)
                and     ST_NOTRDY
                ret     z
                ld      a, 2
                scf
                ret

install_basic_hooks:
                ld      hl, FSECTOR_BUF     ; D-DSKIO: publish the DSKI$/DSKO$ buffer at the
                ld      (DSKBUF_PTR), hl    ; cell the MSX idiom PEEKs (docs/spec-basic-dskio.md)
                ld      hl, hook_tab
ibh_lp:
                ld      c, (hl)             ; the hook cell
                inc     hl
                ld      b, (hl)
                inc     hl
                ld      a, b
                or      c
                ret     z                   ; $0000 terminates the table
                ld      e, (hl)             ; ...and ITS OWN handler: the table is
                inc     hl                  ; pairs now, because MKS$/MKD$ answer
                ld      d, (hl)             ; with a real body while the rest only
                inc     hl                  ; report presence
                push    hl
                ld      h, b
                ld      l, c
                call    install_hook
                pop     hl
                jr      ibh_lp
; The seven conversion hooks, each one of the 35 slots the CF-3300's disk ROM
; claims (scratchpad/hookdiff_probe.py) and each named in the MSX2 TH table.
hook_tab:
                dw      H_DSKF, hk_dskf     ; D-DSKFMOVE: body here, not just
                                             ; its presence
                dw      H_MKI,  hk_present   ; MKI$'s store needs DE, which does
                                             ; not survive CALSLT -- stays main-side
                dw      H_MKS,  hk_mkfloat   ; the float coercion LIVES HERE now
                dw      H_MKD,  hk_mkfloat
                dw      H_CVI,  hk_cv       ; D-CVMOVE: the conversion lives HERE
                dw      H_CVS,  hk_cv       ; now, not just its presence -- so a
                dw      H_CVD,  hk_cv       ; claiming ROM's answer is not overwritten
                dw      H_NAME, hk_name      ; D-DISKVERB2: body here too
                dw      H_KILL, hk_kill      ; D-DISKVERB: the FIRST verb whose
                                             ; BODY lives here, not just its gate
                dw      H_FILE, hk_files     ; D-DISKVERB4: FILES + LFILES
                dw      H_LSET, hk_lrset     ; D-LRSETMOVE: both bodies HERE now
                dw      H_RSET, hk_lrset     ; (one body; LRSET_JUST says which)
                dw      H_FIELD, hk_field    ; D-FIELDMOVE: the trio is complete --
                                             ; body here, not just its presence
                dw      H_DSKO, hk_present   ; D-DSKIO: both bodies are a sub-ROM tenant,
                dw      H_DSKI, hk_present   ; the hook buys the diskless ERR 5
                dw      H_COPY, hk_copy      ; D-DISKVERB3: body here too
                dw      H_ERRP, hk_errp      ; D-DISKERR: the disk codes' messages live HERE
                ; --- H_FOPEN: INSTALLED 2026-09-20 (D-STOPRELATCH) --------
                ; 🏗️ Joost ruled §6.6m, re-affirmed in §6.7's *"we do as the
                ; reference does"*: LOAD arrives at the cell the REFERENCE uses,
                ; and which verb is asking comes from a SELECTOR in RAM (§6.6n).
                ;
                ; 🟢 THREE EXPLANATIONS FOR WHY THIS ROW COULD NOT EXIST WERE
                ; RETRACTED IN TURN, AND THE LAST ONE WAS REAL AND IS FIXED.
                ; §6.6p blamed the CELL ($FE5D is H.NULO, a file-buffer-0
                ; subsystem cell). §6.6t retracted that and blamed the hook
                ; COUNT -- "we cannot install an 18th". §6.6af withdrew that
                ; too: the row carrying it reads RED on the UNMODIFIED ROM at
                ; 15 of 20 timing configurations. §6.6ag then installed the row
                ; and ran a full battery -- 129/132, the only behavioural red
                ; being that same row. §6.6ah fixed the divergence underneath
                ; it (a held Ctrl-STOP now re-fires, `basic/traps.asm`), and
                ; the row is green at 20 of 20 with a 127x margin.
                ;
                ; ⚠️ MAIN DOES NOT CALL THIS YET. The main-ROM side (write
                ; FOPEN_SEL, call the cell, decode DISKOP_STATUS) is the next
                ; slice. Until it lands this row is inert on this machine:
                ; nothing enters $FE5D -- C-BIOS defines the name and never
                ; references it -- so every path behaves exactly as before.
                ; 🔴 AND THE SELECTOR IS WHY IT IS SAFE EVEN IF IT IS ENTERED:
                ; FOPEN_SEL_LOAD is $4C, outside DISKOP_SEL_*'s whole 0..7
                ; range, so a call arriving with the cell merely idle takes
                ; hk_dpload's `ret nz` and answers CF=0 -- "not mine" -- without
                ; touching the drive. That is the fix §6.6p's own footnote
                ; records, and it is what makes landing the row ahead of its
                ; caller a safe intermediate state rather than a half-wired one.
                dw      H_FOPEN, hk_dpload
                dw      0

; --- install_hook: write one 5-byte CALLF stub into a hook slot -------------
; Layout source: MSX2 Technical Handbook §2 (inter-slot call / CALLF) --
; `RST 30H (0F7H) ; slot byte ; addr-lo ; addr-hi ; RET (0C9H)`, the same five
; bytes disk/equates.inc cites for HPHYD. CORROBORATED black-box: a diff of the
; hook region between the diskless VG-8020 and the CF-3300 shows exactly that
; shape in all 35 slots the reference disk ROM claims
; (scratchpad/hookdiff_probe.py, docs/spec-basic-nodisk.md §5.2). No stock
; routine internals decoded -- only the RAM cell's own byte layout, which is
; published interface.
; in:  HL = hook address (a RAM cell in $FD9A..$FFE7)
;      DE = target address in THIS ROM
; out: HL advanced past the stub. Clobbers A, HL.
; Sited here rather than in init.asm because the pad before the $41EF pin is only
; 25 B and one inline install already spent all of it.
; --- fat_bufinit: point the FAT engine at the BDOS buffer pair ---------------
; disk/docs/spec-diskcode-eviction.md §6.4a (the fork and its ruling) and §0.1
; (why a base parameter is needed at all, and what D-FATBUF measured).
; D-FATENG, Joost's ruling (b): the engine loads its buffer bases from RAM
; instead of assembling them in, so ONE engine can serve two callers. This sets
; the BDOS pair; a later slice sets the Disk-BASIC pair before its own calls.
; Sited HERE and not in init.asm for the reason install_hook records below: the
; pad before the $41EF pin is 25 B and one inline install already spent it.
; --- ftc_totsec: total sectors from the boot sector's BPB +19 ----------------
; disk/docs/spec-diskcode-eviction.md §6.4a. Split out of fat_total_clusters
; because that routine sits in a region pinned by `ds $4B59 - $` with no slack:
; the 3-byte `ld hl,(WBUF + 19)` it replaces could not grow in place. Reached by
; label only, so it is position-free here.
;   in   the boot sector is already in the METADATA buffer
;   out  HL = total sectors (16-bit, BPB +19). Clobbers DE.
fat_bufinit:
                ld      hl, SECTOR_BUF
                ld      (DBUF_PTR), hl
                ld      hl, WBUF
                ld      (MBUF_PTR), hl
                ret

; 🏗️ D-FATENG Option 2 (Joost, 2026-09-18): ONE FAT12 ENGINE, ONE SOURCE, TWO
; ROMs -- the same file sub.rom assembles. disk/fat.asm keeps only the
; BDOS-specific half and the pinned M26 trampolines, which resolve to these
; labels BY NAME.
; ⚠️ INCLUDED **HERE**, IN THE FREE CORRIDOR, AND THE POSITION IS NOT A
; PREFERENCE. Placed after fat.asm it pushed kernel.asm past a pin and pasmo
; wrapped the image; appended after runtime.asm it overran the ROM by 1369 B,
; because disk.rom's 8314 B of free space is 32 INTERIOR HOLES, not a tail. This
; corridor is the largest (2712 B at $6B0D) and is where install_hook below
; already lives for the same reason.
                ; ⚠️ REPO-ROOT RELATIVE, NOT "../basic/...". pasmo accepts
                ; both, but tools/check_tenant_closure.py's _resolve_include
                ; treats any path containing "/" as repo-root relative -- so
                ; "../basic/..." resolved ABOVE the repo and the body was
                ; SILENTLY DROPPED from the disk closure, leaving five of its
                ; labels looking like unresolved main references. sub/fatprim.asm
                ; uses this form for the same file.
                include "basic/fat-prim-body.inc"

                ; --- the FAT STREAM layer, the primitives' caller ----
                ; D-DPLPORT (spec-diskcode-eviction.md §6.6b). Option 2
                ; brought the PRIMITIVE body here; the tokenised LOAD loop
                ; calls `fat_io_getbyte` ONCE PER BYTE, and §6.2c measured
                ; that an inter-slot crossing per byte costs 1.72x the
                ; whole load. So the stream layer is assembled here too --
                ; same file, same one source, second ROM.
                ; ⚠️ It names FAT_DBUF, never FSECTOR_BUF: this ROM fills
                ; $E2A0 while basic-resident-abi.inc binds FSECTOR_BUF to
                ; $E5C0, so the old spelling assembled clean and read a
                ; buffer nobody filled (§6.6c). Its 6 bytes of cursor state
                ; are FREAD_OFF/FREAD_LEFT, aliased onto the RDBLK scratch
                ; in init.asm (§6.6f).
                include "basic/fatio-body.inc"
                ; --- the WRITE side, for step 12's hk_dpsave ----------------
                ; D-SAVEPORT. The same four bodies the SUB-ROM save tenant
                ; includes, in the same order, byte-identical: the sequential
                ; write cursor, then the helpers over it, then SAVE's engine.
                ; Beside fat-prim-body.inc above, fat_mount / fat_dir_create /
                ; fat_flush_data_sector / fat_dir_update are IN-PAGE calls here
                ; exactly as they are in the tenant -- which is the whole reason
                ; the move costs no marshalling.
                include "basic/fatiocreate-body.inc" ; fat_io_create
                include "basic/fatiow-body.inc"      ; fat_io_putbyte / fat_io_close
                include "basic/sv-diskwr.inc"        ; disk_write_begin/putbyte/
                                                     ; putword/write_end
                include "basic/sv-savdisk.inc"       ; sav_disk_write .. sav_fin

; --- hk_dpsave: the tokenised SAVE write engine, in the disk ROM ------------
; D-SAVEPORT, step 12 of spec-diskcode-eviction.md §6.2, under the same ruling
; as step 9: *"we do as the reference does"*. Reached through the SAME claimed
; cell as LOAD with FOPEN_SEL = FOPEN_SEL_SAVE ($53).
;
; 🎯 WHY THIS IS A FAITHFULNESS MOVE AND NOT A CARVE. The body was ALREADY
; evicted from main page 1 -- `do_save` used to end `jp sv_tenant`, running
; `sav_disk_write` in the SUB-ROM (SUBROM_IDX_SAVE). So this frees no main byte.
; What it buys is §0.0's point (3): before it, `do_save` reached no hook at all,
; so a machine with a FOREIGN disk ROM still saved through OUR engine. Now the
; cell decides, and a cartridge that claims $FE5D gets the verb.
;
; 🔴 THE BODY IS THE SAME SOURCE, NOT A COPY. `basic/sv-savdisk.inc` and the
; helpers below it are included byte-identically by main, sub and disk; the
; names they spell resolve in all three because the four they needed from main
; (PRGEND, DSV_PTR, DSV_END, DISKSLOT_OK) are published through the GENERATED
; basic-resident-abi.inc. Forking the body for a third ROM was the alternative
; and it is exactly what that generator exists to avoid.
;
;   in   FOPEN_SEL = FOPEN_SEL_SAVE; DISK_FCB_NAME = the 8.3 name main parsed
;   out  CF = 1 claimed; DISKOP_STATUS = 0 written / 3 mount, disk-full or I-O
hk_dpsave:
                xor     a
                ld      (DISKOP_ERR),a      ; D-DISKERR: no DSKIO failure pending
                ld      (DISKOP_STATUS),a   ; assume written; sv_load_error flips it
                call    sav_disk_write      ; `call`, not `jp`: sv_load_error's
                                            ; `ret` lands here, which is the sub
                                            ; tenant's own discipline preserved
                scf                         ; claimed, whatever the disposition
                ret

; sv_load_error -- the disk-local reporter, rebound exactly as the sub-ROM
; tenant rebinds it. Resident it is a zero-byte EQU onto `load_error`, which
; PRINTS; here it must not print, because main's `disk_error` reports ONCE from
; the status this leaves behind -- the same contract step 9's arm already uses.
; No TAPIOF: a disk SAVE never armed the tape.
; --- hk_aopen: open an ASCII program file and prime the read (step 11) -------
; `MERGE` and ASCII `LOAD` arrive here. Main keeps the LINE loop and the
; tokeniser -- that is not a concession, it is what the reference does: its disk
; side never owns MERGE's line loop, the crossing is entered exactly ONCE for a
; 2-line file and once for a 100-line one, and the per-LINE cells sit in a band
; NEITHER measured vendor claims (expansion-protocol.md §8.6a, D-MERGESHAPE).
;
; 🔴 MOUNT AND FIND SEPARATELY, for hk_dpload's reason: their two carries are
; what tells `File not found` from a mount/I-O fault. `fat_io_find` is the
; zero-byte label inside fat_io_open that splits them (D-BLNF), and it leaves
; the stream primed, which is why nothing else is needed here.
; ⚠️ DISKOP_STATUS IS WRITTEN ONCE, LAST, on every arm -- it is a SHARED channel
; (main's FAT primitives marshal through the same cell) and pre-setting it is
; what made `NAME ... AS ...` answer Syntax error at an empty drive (§6.6an).
hk_aopen:
                call    fat_mount
                jr      c,hka_io            ; 3: mount / I-O
                call    fat_io_find
                jr      c,hka_nf            ; 1: not found
                xor     a                   ; 0: open and primed
hka_st:
                ld      (DISKOP_STATUS),a
                scf                         ; CF=1: mine
                ret
hka_nf:
                ld      a,1
                jr      hka_st
hka_io:
                ld      a,3
                jr      hka_st

; --- hk_agetb: one byte of the open ASCII file (step 11) ---------------------
; Sources: the per-byte shape is MEASURED, not chosen -- disk/docs/
; expansion-protocol.md §8.6a (D-MERGESHAPE) counts $FE8A (H.INDS) entered
; exactly once per byte of an ASCII LOAD or MERGE on both reference vendors,
; and zero times on the tokenised path. The register contract (BC crossing
; intact both ways) is spec-diskbasic-hook-rearchitecture.md's measured ABI.
; Clean-room: entry counts and register file only; no reference ROM byte read.
; 🔴 THE BYTE COMES BACK IN C, NOT IN CF+A, AND chan_gate IS WHY. The gate uses
; CF as the CLAIMED/unclaimed answer (`or a` / `jp (hl)` / `cg_back: ret c`), so
; a handler cannot also return a disposition in it. C carries the byte -- BC
; crosses intact both ways (the measured ABI) -- and DISKOP_STATUS carries EOF.
; Main's dsk_agetbyte turns the pair back into the `A = byte, CF = EOF` contract
; ARL_GETBYTE's other sources already honour.
hk_agetb:
                call    fat_io_getbyte      ; A = byte, CF set = EOF
                ld      c,a
                ld      a,1                 ; 1 = EOF
                jr      c,hkg_st
                xor     a                   ; 0 = C holds a byte
hkg_st:
                ld      (DISKOP_STATUS),a
                scf
                ret

sv_load_error:
                ld      a,3                 ; mount / disk full / write / I-O
                ld      (DISKOP_STATUS),a
                ret

; --- hk_dpload: the tokenised LOAD loop, in the disk ROM ---------------------
; D-DPLMOVE. Step 9 of disk/docs/spec-diskcode-eviction.md §6.2, unblocked by
; Joost's ruling in §6.6m: the hook is the cell the REFERENCE uses ($FE5D,
; H_FOPEN), and the verb comes from a SELECTOR.
;
;   in   FOPEN_SEL = FOPEN_SEL_LOAD; DISK_FCB_NAME = the 8.3 name main parsed
;   out  CF = 1 claimed; DISKOP_STATUS = 0 loaded / 1 not found / 2 not
;        tokenised (main's ASCII path takes it) / 3 mount or I-O / 4 out of
;        memory.  CF = 0 = "not my selector" -- main carries on as if unhooked.
;
; THE CODE COMES BACK IN RAM, NOT IN A. §6.6h designed this hook as "CF=1 and
; A = a code"; this answers through DISKOP_STATUS instead, because that is what
; every hook already in hook_tab does -- hk_files, hk_kill and hk_copy all put
; their disposition there and main decodes it. CF still rides the CALLF return,
; which chan_gate has always relied on.
; ⚠️ HONESTY ABOUT WHY THIS CHANGED: it was my first guess at §6.6o's red
; `l.load` row and it was WRONG -- the row stayed red. The real cause was that
; disk.rom never wrote DISKOP_ERR at all. This is kept because consistency with
; the other four hooks is worth having, NOT because it fixed anything; a comment
; claiming otherwise would be the same class of unverified claim §6.6l is about.
;
; 🎯 WHY THE LOOP AND NOT JUST THE OPEN. §6.2c MEASURED the alternative: leaving
; the byte loop in main and reaching the stream across the slot costs one
; inter-slot crossing PER BYTE, 1.72x the whole load. `fat_io_getbyte` resolves
; LOCALLY here (the stream layer is included above), so every byte of a 14 KB
; program is an in-page call.
;
; 🔴 NO CALL-BACKS, AND THAT IS A PROPERTY TO KEEP. The body reaches main only
; through RAM -- CLPTR/CLINK/TXTBASE/TXTMAX out of the GENERATED
; basic-resident-abi.inc, so a repack that moves the text ceiling cannot leave
; the bounds check reading the old one. Every decision main has to make it makes
; from A, on its own side. If an arm here ever needs `calbak`, re-read
; FOPEN_SEL's mutual-exclusion note in disk/equates.inc first.
hk_dpload:
                ld      a,(FOPEN_SEL)
                cp      FOPEN_SEL_SAVE
                jr      z,hk_dpsave         ; step 12 (D-SAVEPORT)
                cp      FOPEN_SEL_AOPEN
                jr      z,hk_aopen          ; step 11 (D-MERGEPORT)
                cp      FOPEN_SEL_GETB
                jr      z,hk_agetb          ; step 11, once per BYTE
                cp      FOPEN_SEL_LOAD
                ret     nz                  ; CF=0: not mine. Step 10 (OPEN) adds
                                            ; its arm right here.
                ; mount and find SEPARATELY: their two carries are what tells
                ; `file not found` from a mount/I-O fault, which is the whole
                ; reason fatio-body.inc carries the zero-byte `fat_io_find`
                ; label (D-BLNF). DISKOP_OP is not read on this path -- and it
                ; could not be, it is carrying the selector.
                call    fat_mount
                jp      c,hdl_io            ; 3: mount / I-O (`jp`: the exits
                                            ; sit past the whole loop body)
                call    fat_io_find
                jp      c,hdl_nf            ; 1: not found (`jp`, same reason)
                ; seed the store cursor. ⚠️ HOISTED ABOVE THE MARKER READ for
                ; D-TRUNCLOAD's reason, unchanged by the move: an EOF on the
                ; very first byte (a ZERO-BYTE file) must commit an EMPTY
                ; program like every other EOF here, and cannot with CLPTR
                ; unset. Seeded AFTER the open, exactly where main seeded it,
                ; so a failed load leaves these cells as untouched as before.
                ld      hl,TXTBASE
                ld      (CLPTR),hl
                ld      (CLINK),hl          ; A_0 = saving machine's text base
                ; first byte selects the format: $FF = tokenised.
                call    fat_io_getbyte
                jp      c,hdl_ok            ; D-TRUNCLOAD: EOF here is an empty
                                            ; program, not an error
                cp      BASIC_DISK_ID
                jp      nz,hdl_ascii        ; 2: main re-opens and tokenises
hdl_line:
                call    fat_io_getbyte      ; link low
                jp      c,hdl_ok            ; EOF between lines = normal end
                push    af                  ; preserve link-low across the read
                call    fat_io_getbyte      ; link high
                jr      c,hdl_eof
                ld      b,a
                pop     af
                ld      c,a                 ; BC = saved link word L_n
                ld      a,b
                or      c
                jp      z,hdl_ok            ; $0000 link -> program complete
                ; body length = L_n - A_n - 4   (A_n = CLINK)
                ld      hl,(CLINK)
                ld      (CLINK),bc
                ld      a,c
                sub     l
                ld      e,a
                ld      a,b
                sbc     a,h
                ld      d,a
                dec     de
                dec     de
                dec     de
                dec     de                  ; DE = body length (incl. its $00)
                ; this line's header (>=4 B) must fit below TXTMAX
                push    de
                ld      hl,(CLPTR)
                ld      de,TXTMAX-4
                or      a
                sbc     hl,de
                jr      nc,hdl_oom_pop
                ; store the saved link word verbatim; relink fixes it later
                ld      hl,(CLPTR)
                ld      (hl),c
                inc     hl
                ld      (hl),b
                inc     hl
                ld      (CLPTR),hl
                call    hdl_get_store       ; line number, 2 bytes
                jr      c,hdl_eof
                call    hdl_get_store
                jr      c,hdl_eof
                pop     de                  ; DE = body length
hdl_body:
                ld      a,d
                or      e
                jr      z,hdl_line          ; whole body copied -> next line
                push    de
                ld      hl,(CLPTR)
                ld      de,TXTMAX
                or      a
                sbc     hl,de
                jr      nc,hdl_oom_pop
                call    hdl_get_store
                jr      c,hdl_eof
                pop     de
                dec     de
                jr      hdl_body

; hdl_get_store: read ONE file byte and store it at CLPTR, advancing.
;   out CF = EOF (nothing stored) / clear = stored, CLPTR advanced.
; D-NGRAM13's shape, carried over with the move: it returns CF and the CALLER
; raises, because each call site guards exactly one value across the read and
; folding the drop in here would need a frame fix no row can witness.
hdl_get_store:
                call    fat_io_getbyte
                ret     c
                ld      hl,(CLPTR)
                ld      (hl),a
                inc     hl
                ld      (CLPTR),hl
                ret

; hdl_eof: EOF with ONE guarded word on the stack -- three sites guard a 16-bit
; count (`push de`) and one the link-low byte (`push af`); both are one word and
; main's load_commit_prog reads neither, so the pop only has to be the right
; SIZE. D-TRUNCLOAD: a truncated tokenised file is NOT an error -- the reference
; is silent at all five EOF sites (docs/spec-basic-truncload.md §2).
hdl_eof:
                pop     af                  ; drop the guarded word
hdl_ok:
                xor     a                   ; 0: loaded
                jr      hdl_answer
hdl_oom_pop:
                pop     de
                ld      a,4                 ; 4: out of memory
                jr      hdl_answer
hdl_nf:
                ld      a,1                 ; 1: file not found
                jr      hdl_answer
hdl_ascii:
                ld      a,2                 ; 2: not tokenised
                jr      hdl_answer
hdl_io:
                ld      a,3                 ; 3: mount / I-O
; hdl_answer: the ONE exit. DISKOP_STATUS carries the code across the hook
; return -- see the header for why it is not A -- and CF=1 says "claimed".
hdl_answer:
                ld      (DISKOP_STATUS),a
                ; 🔴 DISARM THE SELECTOR ON THE WAY OUT. The cell is shared and
                ; $FE5D is reached by callers that are not this verb (§6.6p);
                ; leaving it armed means the NEXT such call falls through into a
                ; FAT mount. Cleared here rather than in main because the side
                ; that CONSUMED the selector is the side that should retire it,
                ; and a main-side clear leaves a window between the two.
                ; 0 is DISKOP_OP's own idle value, and is not the magic.
                xor     a
                ld      (FOPEN_SEL),a
                scf
                ret

install_hook:
                ld      a, $F7              ; +0: RST 30h (CALLF)
                ld      (hl), a
                inc     hl
                ld      a, (HOOK_SLOT)      ; +1: this ROM's slot byte
                ld      (hl), a
                inc     hl
                ld      (hl), e             ; +2: target lo
                inc     hl
                ld      (hl), d             ; +3: target hi
                inc     hl
                ld      a, $C9              ; +4: RET
                ld      (hl), a
                ret

; --- calbak: ONE inter-slot call back into main page 1 (MSX2 TH) ------------
; D-DISKVERB. IX = the main page-1 target (an address from the GENERATED
; basic-resident-abi.inc, so a page-1 shift cannot leave us calling a stale one).
; A/HL/DE/BC pass through in both directions -- MEASURED, not assumed
; (D-XSLOTABI, scratchpad/xslot_abi.py); IY is ours and IX is consumed.
; `jp CALSLT` rather than call+ret: CALSLT's own `ret` lands on OUR caller.
calbak:
                ld      iy,(EXPTBL-1)   ; IYh = main-ROM slot id (MSX2 TH idiom)
                jp      CALSLT

; --- hk_kill: KILL's body, RUNNING IN THE DISK ROM --------------------------
; D-DISKVERB, spec-diskbasic-hook-rearchitecture.md phase 2. The first verb whose
; body follows its hook, which is what the reference does on all 35 of its cells
; (D-CFARCH) and what Joost directed.
;
; Main's ex_kill is now the cursor hand-off and the status decode; everything
; between is here. Two things it used to do are GONE rather than moved:
; `chan_gate`'s presence test (we ARE the answer to it) and `diskslot_test`
; (likewise). The diskless ERR 5 is unaffected -- it comes from chan_gate finding
; the cell UNCLAIMED, which is exactly the case where this body does not exist.
;
;   in   FN_RESUME = the statement cursor, just past the KILL token
;   out  DISKOP_STATUS = the dirverb disposition; FN_RESUME = the resume cursor;
;        CF = 1 (claimed), which is what chan_gate tests
;
; 🔴 THERE IS NO `ei` HERE, AND 0c PREDICTED THERE WOULD BE. 0c measured that a
; handler is entered with interrupts OFF and that this stops the clock outright
; (~1 s of disk-ROM work advanced TIME by 3 frames), and concluded the call-back
; ABI should let them back on. So an `ei` was written here -- and then MEASURED,
; with and without, one line apart: `KILL "NOSUCH.XYZ"` against a real disk
; advanced TIME by 2 frames BOTH WAYS (scratchpad/xslot_kill_ei.py).
; It changed nothing, for two reasons worth keeping:
;   * this verb is ~33 ms, so any freeze is below the resolution of the thing
;     being protected; 0c's figure was for a ~1 s window.
;   * `subrom_call` already does `di / call CALSLT / ei` UNCONDITIONALLY, so the
;     moment dirverb_op runs, interrupts come back on regardless of us. The only
;     window an `ei` here would have covered is entry -> the first call-back:
;     a handful of instructions.
; It is not shipped, because a byte whose measured effect is zero should not be.
; ⚠️ THAT IS A STATEMENT ABOUT *THIS* VERB'S SIZE, NOT A GENERAL ONE. A phase-3
; body that does long work in THIS ROM rather than inside a call-back re-opens
; it, and 0c's numbers are the ones to re-read then.
hk_kill:
                ld      hl,(FN_RESUME)  ; the cursor main staged for us
                ld      ix,fname_expr
                call    calbak          ; a string EXPRESSION -> STRSCR; may RAISE
                                        ; (ERR 13) and NOT return -- see the ABI
                ld      ix,pdfcb_resume
                call    calbak          ; -> DISK_FCB_NAME (8.3, wildcards)
                ; 🔴 PRE-SET THE FAILURE DISPOSITION rather than read CF back.
                ; dirverb_op returns CF=1 when the sub-ROM is absent, but whether
                ; CF survives CALSLT is NOT among the things D-XSLOTABI measured
                ; -- so it is not relied on. A tenant that never runs leaves the 2
                ; standing, which is the mount/I-O disposition main already
                ; decodes; one that runs overwrites it.
                ld      a,2
                ld      (DISKOP_STATUS),a
                ld      a,DISKOP_SEL_KILL
                ld      ix,dirverb_op
                call    calbak
                scf                     ; CF=1: the hook is claimed
                ret

; --- hk_name: NAME's body, RUNNING IN THE DISK ROM (MSX2 TH hook) -----------
; D-DISKVERB2, spec-diskbasic-hook-rearchitecture.md phase 3. The second verb to
; follow its hook, on the pattern hk_kill established.
;
;   in   FN_RESUME = the statement cursor, just past the NAME token
;   out  DISKOP_STATUS, and main's ex_name decodes it; CF = 1 (claimed)
;
; 🎯 NAME'S THREE OUTCOMES ARE ALREADY KILL'S THREE, so main shares kill_status
; rather than keeping NAME's own tails: nm_notfound was `jp df_notfound` (ERR 53)
; = status 0, nm_fail/nm_fail2 were `jp disk_error` = status 2, and success was
; `jp exec_stmt` = status 1. Only the missing-`AS` syntax error needs a fourth
; value, and main tests for it before handing over to the shared decode.
; ⚠️ THE TENANT'S OWN STATUS HAS THE OPPOSITE POLARITY and is translated here,
; not passed through: for NAME_STAMP the dirverb tenant answers 0 = OK, nonzero =
; I/O error, where kill_status reads 0 as `File not found`. Forwarding it raw
; would turn every successful rename into ERR 53.
;
; 🎯 THE `AS` KEYWORD IS READ STRAIGHT OUT OF THE PROGRAM TEXT. That is RAM, and
; RAM is mapped throughout -- so two characters do not need a call-back apiece,
; and skip_spaces/upcase stay where they are.
hk_name:
                ld      hl,(FN_RESUME)
                ld      ix,fname_expr
                call    calbak              ; OLD name -> STRSCR; may RAISE (ERR 13)
                ld      ix,pdfcb_resume
                call    calbak              ; -> DISK_FCB_NAME
                ld      hl,(FN_RESUME)
hkn_sp:
                ld      a,(hl)              ; skip blanks before `AS`
                cp      ' '
                jr      nz,hkn_a
                inc     hl
                jr      hkn_sp
hkn_a:
                call    hkn_up
                cp      'A'
                jr      nz,hkn_syn
                inc     hl
                ld      a,(hl)
                call    hkn_up
                cp      'S'
                jr      nz,hkn_syn
                inc     hl
                ld      (FN_RESUME),hl      ; the NEW name's text starts here
                ld      ix,main_fat_mount
                call    calbak
                jr      c,hkn_io            ; no disk / bad BPB
                ld      hl,DISK_FCB_NAME
                ld      ix,main_fat_find
                call    calbak              ; locate the OLD file
                jr      c,hkn_nf
                ld      hl,(FN_RESUME)
                ld      ix,fname_expr
                call    calbak              ; NEW name -> STRSCR, FN_RESUME moved
                ld      hl,STRSCR + 1
                ld      ix,parse_disk_fcb
                call    calbak              ; new -> DISK_FCB_NAME
                ld      a,DISKOP_SEL_NAME_STAMP
                ld      ix,dirverb_op
                call    calbak
                ld      a,(DISKOP_STATUS)   ; the tenant's polarity: 0 = OK
                or      a
                jr      nz,hkn_io
                ld      a,1                 ; renamed
                jr      hkn_done
hkn_nf:
                xor     a                   ; 0 = old file not found -> ERR 53
                jr      hkn_done
hkn_io:
                ld      a,2                 ; mount / I-O -> the mapped disk code
                jr      hkn_done
hkn_syn:
                ld      a,4                 ; no `AS` -> Syntax error
hkn_done:
                ; 🔴 DISKOP_STATUS IS WRITTEN ONCE, HERE, AFTER EVERY CALL-BACK.
                ; The first cut PRE-SET it to 2 and let the later paths overwrite
                ; it -- which cannot work, because main's fat_mount and fat_find
                ; are `ld a,DISKOP_SEL_* / jr fatprim_bounce` shims that marshal
                ; their own disposition THROUGH THIS SAME CELL (basic/fat.asm).
                ; So a failed mount wrote the FAT primitive's status over mine and
                ; main decoded whatever that happened to be: measured, `NAME "A.BAS"
                ; AS "B.BAS"` at an EMPTY DRIVE answered `Syntax error` instead of
                ; `Disk offline`, because the cell held 4. The cell is a SHARED
                ; channel, not ours; the only safe time to write it is last.
                ld      (DISKOP_STATUS),a
                scf                         ; CF=1: the hook is claimed
                ret
; hkn_up: upcase A. Six bytes of our own rather than a call-back for one
; character -- own-design, and the same fold main's `upcase` does.
hkn_up:
                cp      'a'
                ret     c
                cp      'z' + 1
                ret     nc
                sub     32
                ret

; --- hk_copy: COPY's body, BOTH HALVES, in the disk ROM (MSX2 TH hook) ------
; D-DISKVERB3, spec-diskbasic-hook-rearchitecture.md phase 3, third verb.
;
; 🎯 THIS ONE PAYS IN THE SCARCER CURRENCY. COPY's parse half was `copy_parse` in
; the page-0 LOW REGION, which stands at 0 B free -- and `fname_fcb`, its only
; caller's only helper, goes with it now that KILL and NAME no longer route
; through either. Both leave, so the saving is low-region bytes, not page-1 ones.
;
;   in   FN_RESUME = the statement cursor, just past the COPY token
;   out  DISKOP_STATUS, decoded by main's ex_copy; CF = 1 (claimed)
;
; Dispositions are the dirverb tenant's own 0/1/2 plus 3, and main maps 3 to ERR 5
; before handing 0/1/2 to the shared kill_status. A MISSING `TO` folds into 3
; because that is what the reference answers -- ERR 5, measured on the CF-3300,
; the one-argument form PARSING and being refused rather than ERR 2 (D-COPY).
;
; ⚠️ THE ONE 8.3 BUFFER IS REUSED, which is why the source is stashed first: the
; COPYSTASH op moves DISK_FCB_NAME into COPY_SRC so the destination can overwrite
; it. Getting that order wrong copies a file onto itself.
hk_copy:
                ld      hl,(FN_RESUME)
                ld      ix,fname_expr
                call    calbak              ; SOURCE name; may RAISE (ERR 13)
                ld      ix,pdfcb_resume
                call    calbak              ; -> DISK_FCB_NAME
                ld      a,DISKOP_SEL_COPYSTASH
                ld      ix,dirverb_op
                call    calbak              ; -> COPY_SRC, freeing the 8.3 buffer
                ld      hl,(FN_RESUME)      ; the tenant clobbers HL
hkc_sp:
                ld      a,(hl)              ; skip blanks before `TO`
                cp      ' '
                jr      nz,hkc_to
                inc     hl
                jr      hkc_sp
hkc_to:
                cp      TO_TOKEN
                jr      nz,hkc_ref          ; no `TO` -> ERR 5 (measured), not ERR 2
                inc     hl
                ld      ix,fname_expr
                call    calbak              ; DESTINATION name
                ld      ix,pdfcb_resume
                call    calbak              ; -> DISK_FCB_NAME
                ld      a,DISKOP_SEL_COPY
                ld      ix,dirverb_op
                call    calbak
                ld      a,(DISKOP_STATUS)   ; the tenant's own 0/1/2/3
                jr      hkc_done
hkc_ref:
                ld      a,3                 ; refused -> ERR 5
hkc_done:
                ; DISKOP_STATUS written ONCE, LAST -- see hk_name for why that is
                ; not a style choice: the cell is a channel main's FAT primitives
                ; marshal through too.
                ld      (DISKOP_STATUS),a
                scf                         ; CF=1: the hook is claimed
                ret

; --- hk_files: FILES and LFILES, in the disk ROM (MSX2 TH hook) -------------
; D-DISKVERB4, spec-diskbasic-hook-rearchitecture.md phase 3, the last of the
; FAT-light four.
;
; 🎯 ONE HOOK, TWO VERBS, AND THE TOKEN SAYS WHICH. H_FILE is the only cell the
; reference gives this pair, so the selector cannot come from the hook. It is
; read from the PROGRAM TEXT instead: FN_RESUME points just past the verb's own
; token, so the byte before it is FILES_TOKEN or LFILES_TOKEN. Same trick as
; NAME's `AS` and COPY's `TO` -- the text is RAM and mapped throughout, so no
; call-back and no new sysvar.
;
;   in   FN_RESUME = the statement cursor, just past the FILES/LFILES token
;   out  DISKOP_STATUS 0/1/2, decoded by the shared kill_status; CF = 1 (claimed)
;
; ⚠️ THE SELECTOR RIDES THE STACK ACROSS THE EVALUATOR, and that is D-FNEXPR2's
; finding carried over rather than re-learned: the filespec is a string
; EXPRESSION, and `FILES INPUT$(5,#1)` reaches the drive through fatprim_bounce,
; whose FIRST instruction is `ld (DISKOP_OP),a`. Writing the selector before the
; evaluator hands the dirverb tenant a FAT-primitive selector. An abort inside
; the evaluator cannot leak the pushed word: raise_error resets SP from SAVSTK.
hk_files:
                ld      hl,(FN_RESUME)
                dec     hl
                ld      a,(hl)              ; the verb's own token
                inc     hl
                cp      LFILES_TOKEN
                ld      a,DISKOP_SEL_FILES
                jr      nz,hkf_sel
                ld      a,DISKOP_SEL_LFILES
hkf_sel:
                push    af                  ; the selector, ACROSS the evaluator
                xor     a
                ld      (FILES_HASPAT),a    ; no pattern yet
hkf_sp:
                ld      a,(hl)              ; skip blanks before the filespec
                cp      ' '
                jr      nz,hkf_chk
                inc     hl
                jr      hkf_sp
hkf_chk:
                or      a
                jr      z,hkf_run           ; end of statement -> whole directory
                cp      COLON
                jr      z,hkf_run           ; `FILES:...` -> ditto
                ld      ix,fname_expr
                call    calbak              ; an EXPRESSION; may RAISE (ERR 13)
                ld      ix,pdfcb_resume
                call    calbak              ; -> DISK_FCB_NAME (8.3 wildcard)
                ld      a,1
                ld      (FILES_HASPAT),a
hkf_run:
                pop     af                  ; the selector, asserted only now
                ld      ix,dirverb_op
                call    calbak
                jr      nc,hkf_done         ; CF crosses -- MEASURED two-sided
                ld      a,2                 ; sub-ROM absent -> the mount/I-O face
                ld      (DISKOP_STATUS),a
hkf_done:
                scf                         ; CF=1: the hook is claimed
                ret

                ds      $75A5 - $, $00
                jp      k_75A5          ; $75A5
                ds      $77B8 - $, $00
                jp      k_77B8          ; $77B8
                ds      $782B - $, $00
                jp      k_782B          ; $782B
; --- contract bodies (stubs; filled in milestone 4; added as each veneer lands) ---
k_402D:         ret
k_41FD:         ret
k_4558:         ret
k_46C8:         ret
; k_47B2 — M31: faithful Random Block Read (tier2-m31-rdblk-randrecord-spec.md
; §3); was M21b's "stream-from-0" simplification (ignored FCB+33..35, always
; read to EOF). The kernel's $27 RDBLK handler ($D887, ret=$C51D) CALLs $47B2
; for BOTH the boot-time COMMAND.COM self-load (DE=$DC5B) and the runtime
; typed-command TPA load (DE=$DA40) AND every running program's user-level $27
; (arbitrary RR/RS/HL, e.g. BDOSX) — one unified body serves all three by
; *contract*, never by caller identity (§2): position to the FCB's
; random-record field (FCB+33..35), transfer up to HL records of the FCB's
; record size (FCB+14..15, 0 -> 128 default), zero-pad a final partial record,
; and report the true delivered count. The boot callers pass RR=0/RS=1/huge-HL
; (§1-Q2), which is just this same contract instantiated at those values (§3.2
; "boot instantiation check") — no branching on caller shape.
;   in:  DE = FCB pointer (kernel work buffer); HL = requested record count
;   out: A = $00 all HL requested records delivered / $01 EOF-first (§1-Q3)
;        HL = BC = records actually delivered
;        FCB+33..35 (RR) := entry-RR + HL (write-back; unchanged when HL=0,
;        i.e. positioned at/past EOF already)
;        IY = the entry DE (kernel work pointer, §5.4/§8.50); IX = the drive-A
;        DPB (§8.50's original boot contract, extended unconditionally, §2).
;        $F306 cleared (Tier-2 dispatcher-flag rule, M20).
; Reuses the byte-granular rdblk_getbyte/fat_open engine (disk/driver.asm) —
; the same machinery bdos_rdblk uses — but with k_47B2's OWN record loop, so
; bdos_rdblk/rdb_recloop_body (the pre-kernel boot MSXDOS.SYS-load path, never
; reached once a program is running, §1-Q1) stay byte-identical.
; CLEAN-ROOM: our own file layer streaming into the caller's own DTA; COMMAND.COM
; is data we copy, never disassembled. Contract from the public map.grauw.nl
; _RDBLK doc + black-box behavioural characterisation (§1).
; 3b-relocation (M24/M28/M29 idiom): the faithful body outgrew the $47B2..
; $4919 span, so this veneer diverts to k47b2_body in the free kernel tail
; (below k_47B2 in this file); every k_* canonical address stays net-zero.
k_47B2:         jp      k47b2_body          ; Tier-2 3b: divert; veneer fills the gap
k_4919:         ret
k_4935:         ret
k_498C:         ret
k_49B4:         ret
k_4A39:         ret
k_4B59:         ret
k_4BE5:         ret
k_4C25:         ret
k_4E4B:         ret
k_4EDE:         ret
k_5FE5:         ret
k_607B:         ret
k_75A5:         ret
k_77B8:         ret
k_782B:         ret

; p1_blit_tmpl — clean-room blit routine (§8.35), LDIR'd to P1_BLIT ($E77A) by
; build_resident.  Called from dskio (page-1 ROM) via `call P1_BLIT` when the
; DSKIO transfer destination is in page 1 ($4000-$7FFF): the FDC read was
; redirected to SECTOR_BUF; this copies SECTOR_BUF to the original page-1 target
; by briefly switching page-1 sub-slot from disk ROM (3-1) to RAM (3-0).
;
; Runs from page-3 RAM (always-mapped), so the page-1 sub-slot flip is safe.
; The call return address (a page-1 ROM address) is still on the stack while
; page 1 = RAM; sub-slot 1 is restored BEFORE `ret`, so the RET lands in the ROM.
;
; $FFFF secondary register: write = direct sub-slot IDs (bits [3:2] = page-1
; sub-slot); read = complement of the written value (MSX2 TH §2.4).  We CPL
; after reading to recover the "write" form, mask bits 3:2 to 00 (sub-slot 0 =
; RAM), then write; on return CPL to restore original sub-slot 1.
;
; Source: MSX2 TH §2.4 (expanded-slot secondary register semantics); sub-slot
; layout confirmed by black-box differential (set_ramad / page0_ram_in, same
; host).  Clean-room: never reads the stock $EF95 or any proprietary driver.
; Lives in the free tail (LDIR-relocated; moved here from the cramped pre-$41FD
; region so the wa_seg M5.6 additions fit, §8.58). wa_seg_*_tmpl follows it
; immediately so build_resident copies BOTH with one LDIR (RAM-contiguous).
;   in:  P1_DEST = page-1 target address (word in page-3 scratch)
;   out: 512 bytes from SECTOR_BUF copied to (P1_DEST); page-1 sub-slot restored
p1_blit_tmpl:
                ld      a, ($FFFF)          ; A = inverted sub-slot state (MSX2 TH)
                cpl                         ; A = actual sub-slot write value
                push    af                  ; save original state for restore
                and     $F3                 ; bits 3:2 -> 00: page 1 = sub-slot 0 (RAM)
                ld      ($FFFF), a          ; page 1 now maps to RAM
                ld      hl, SECTOR_BUF      ; source: FDC data was read here
                ld      de, (P1_DEST)       ; dest: original page-1 target (now RAM)
                ld      bc, 512
                ldir
                pop     af                  ; A = original sub-slot write value
                ld      ($FFFF), a          ; page 1 back to disk ROM (sub-slot 1)
                ret
p1_blit_end:

; wa_seg_*_tmpl — clean-room bodies for the $F368/$F36B work-area segment-switch
; hooks (§8.58), LDIR'd to WA_SEG by build_resident and wired into the $F368 table
; by build_wa_table. The relocated kernel CALLs $F368 to map the disk ROM into
; page 1 (so it can run a page-1 disk-ROM routine) and $F36B to map RAM into page 1
; (so it can read its data living UNDER the page-1 ROM). On this expanded slot 3,
; subslot 1 = disk ROM, subslot 0 = RAM (machine config); the page-1 subslot is
; bits [3:2] of the slot-3 secondary register, $04 = subslot 1, $00 = subslot 0.
;
; Contract (measured stock, §8.58): register-TRANSPARENT (entry regs == exit regs);
; only persistent effect = SLTTBL[3] ($FCC8) and the live secondary register
; ($FFFF) set to $04 (rom) / $00 (ram). We read-modify-WRITE only the page-1 bits
; (mask $F3) so the other pages' subslots are preserved, source the current value
; from the SLTTBL mirror (write-form; $FFFF reads back complemented, so the mirror
; is the safe source), update the mirror then the live register, under DI. No EI:
; faithful -- the kernel calls these with interrupts already off (§8.58 trace).
; Bodies run from page-3 RAM (always mapped), so the page-1 flip never unmaps them.
; Lives in the free tail (LDIR-relocated; ROM position must not disturb canonical
; addresses -- the inline-before-$41FD placement overflowed that gap, §M5.6).
;
; Clean-room: our own standard expanded-slot switch (MSX2 TH §2.4 secondary-slot +
; SLTTBL); the stock $DF57/$DF59 bytes are never read. Straight-line + one PC-
; relative jr, so a plain LDIR relocates it verbatim.
;   in:  -            ; out: page-1 subslot of slot 3 set; all registers preserved
wa_seg_rom_tmpl:                            ; $F368 body: map disk ROM into page 1
                push    af
                push    bc                  ; B is our scratch -> preserve (transparent)
                ld      a, $04              ; page-1 bits = subslot 1 (disk ROM)
                jr      wa_seg_set_tmpl     ; (relocatable: PC-relative)
wa_seg_ram_tmpl:                            ; $F36B body: map RAM into page 1
                push    af
                push    bc
                ld      a, $00              ; page-1 bits = subslot 0 (RAM)
wa_seg_set_tmpl:
                di
                ld      b, a                ; B = desired page-1 subslot bits
                ld      a, (SLTTBL3)        ; current slot-3 subslot (write-form mirror)
                and     $F3                 ; clear page-1 bits, keep pages 0/2/3
                or      b                   ; merge new page-1 bits
                ld      (SLTTBL3), a         ; update RAM mirror first
                ld      ($FFFF), a          ; ...then the live secondary-slot register
                pop     bc
                pop     af
                ret
wa_seg_end_tmpl:
WA_SEG_ROM      equ     WA_SEG + (wa_seg_rom_tmpl - wa_seg_rom_tmpl)   ; = WA_SEG
WA_SEG_RAM      equ     WA_SEG + (wa_seg_ram_tmpl - wa_seg_rom_tmpl)

; f365_iord_tmpl — clean-room body for the fixed disk-work-area slot-read stub at
; $F365 (M15 OI-1/§7 pin: unbuilt/FF on ours; §7.1 causally BOUNDS the func-9 STROUT
; output blocker to completing `wa_seg` + this stub). Reads the PPI primary-slot-
; select register (port $A8) and returns; the disk-ROM work area's own per-char
; output loop CALLs this fixed address (observed black-box: reader PC = $F365 itself,
; i.e. an executed 2-instruction stub, never disassembled — see docs/tier2-m15-spec.md
; §7.2). Installed at the FIXED address $F365 (not WA_SEG-relative: the kernel calls
; it by that absolute address, like WA_JMPTAB), by install_f365 below.
; CLEAN-ROOM: IN A,(n) reading port $A8 is the documented i8255 PPI primary-slot-
; select register (MSX2 TH ch.2 / i8255 PPI datasheet, docs/allowed-sources.md class
; A) — our own encoding of a public 2-instruction sequence, not read from the ROM.
;   in: - ; out: A = primary-slot register; other registers preserved
f365_iord_tmpl:
                in      a, ($A8)
                ret
f365_iord_end:

; install_f365 — copies f365_iord_tmpl to the fixed address $F365. Lives in the
; free tail (no budget limit) and is reached by a single 3-byte `call` from
; build_resident's cramped pre-$41FD path (see init.asm) instead of inlining the
; ld/ld/ld/ldir sequence there, which overflows that region's canonical-address
; budget (M15 §7.1/§7.2: verified — an inline second copy there makes 3-pass/
; symbol-table assembly silently emit an empty object file, no error printed).
install_f365:
                ld      hl, f365_iord_tmpl
                ld      de, F365_STUB
                ld      bc, f365_iord_end - f365_iord_tmpl
                ldir
                ret

; res_print_tmpl — clean-room body for the resident $-string print routine, relocated
; to RES_PRINT ($F1C9) by install_res_print (M15 §9.2/§9.3(ii)). The kernel CALLs
; $F1C9 with DE -> a '$'-terminated string. Emits each char via conout_body (the
; proven $5454 CONOUT path func-2/conin_line_body already use) before advancing --
; the M15 root cause was that our first cut consumed the string without emitting it.
; conout_body preserves BC/DE/HL/IX/IY internally, but only across ITS OWN entry
; state; since E is overwritten with the char before the call, DE (the string
; pointer) is saved/restored around the call here. Straight-line + one PC-relative
; jr, so a plain LDIR relocates it verbatim.
; CLEAN-ROOM: derives from the published func-9 STROUT contract ('$'-terminated
; string at DE) + our own conout_body; no stock bytes (never reads $F392/$F2AC/
; $F237/$D88A-region routine bytes, docs/tier2-m15-spec.md §5/§9).
;   in:  DE -> '$'-terminated string ; out: DE past the '$', A=$24, others as Z80 CP
res_print_tmpl:
                ld      a, (de)         ; A = next string byte
                inc     de
                cp      '$'             ; $24 = MS-DOS string terminator
                ret     z               ; done -> return to the kernel
                push    de              ; save the string pointer (E about to change)
                ld      e, a            ; conout_body's ABI: char in E (M10)
                call    conout_body     ; emit via $5454 CONOUT path -> CHPUT
                pop     de              ; restore the string pointer
                jr      res_print_tmpl  ; (relocatable: PC-relative loop)
res_print_end:

; install_res_print — copies res_print_tmpl to RES_PRINT ($F1C9). Lives in the free
; tail (no budget limit) and is reached by a single 3-byte `call` from build_resident's
; cramped pre-$41FD path (init.asm), same rationale as install_f365 (§7.1/§7.2/§9.3).
install_res_print:
                ld      hl, res_print_tmpl
                ld      de, RES_PRINT
                ld      bc, res_print_end - res_print_tmpl
                ldir
                ret

; seldsk_drv_body — the $50D5 kernel SELDSK-time entry (M17; tier2-m17-spec.md).
; The relocated kernel CALLs $50D5 while processing BDOS SELDSK ($0E) to read the
; logical-drive count. Black-box contract (M17 §2.1, readwatch causal pin): read
; $F347 into A, preserve BC/DE/HL/IX/IY. Reached directly from the fixed $50D5 veneer
; (jp seldsk_drv_body) -- lives here in the free tail like conin_line_body/conout_body.
; CLEAN-ROOM: derives from the observed DATA-cell read contract (return [$F347]) +
; our own code; no stock/kernel bytes decoded (only entry/exit regs + the $F347 read).
;   in: -    ; out: A = ($F347) = drive count ; BC/DE/HL/IX/IY preserved
seldsk_drv_body:
                ld      a, (DRVCNT)     ; DRVCNT = $F347 = logical-drive count ($02)
                ret

; curdrv_body — the $50C4 kernel CURDRV-time entry (M18; tier2-m18-spec.md).
; The relocated kernel CALLs $50C4 while processing BDOS CURDRV ($19) to read the
; CURRENT-drive index. Black-box contract (M18 §2.1, readwatch causal pin): read
; $F247 into A, preserve BC/DE/HL/IX/IY. Reached directly from the fixed $50C4 veneer
; (jp curdrv_body) -- lives here in the free tail like seldsk_drv_body.
; CLEAN-ROOM: derives from the observed DATA-cell read contract (return [$F247]) +
; our own code; no stock/kernel bytes decoded (only entry/exit regs + the $F247 read).
;   in: -    ; out: A = ($F247) = current drive ; BC/DE/HL/IX/IY preserved
curdrv_body:
                ld      a, (CURDRV_CELL) ; CURDRV_CELL = $F247 = current-drive index ($00)
                ret

; ===== M19: runtime directory search (BDOS SFIRST $11 / SNEXT $12) =============
; sfirst_body / snext_body / dirscan_match / name_cmp_wild — the bodies behind the
; $4FB8 (SFIRST) / $5006 (SNEXT) page-1 kernel entries. They walk our own root
; directory (reusing fat_mount + the fat_find ff_secloop/ff_entloop structure),
; match each 8.3 name against the kernel's search-FCB pattern (with the ? wildcard),
; copy the found entry's drive-byte + 32-byte directory image to the runtime DTA,
; and persist the scan position in BDOS_SRCHIDX so SNEXT resumes where the prior
; call stopped. Return A=$00 found / A=$FF exhausted (published SFIRST/SNEXT
; contract; the flags are irrelevant to the caller — M19 §2.4).
;
; PINNED black-box contract (M19 §2/§4, callseq/capture — NO stock CODE decoded):
;   - entry DE -> the kernel's search-FCB copy: drive byte at +0, 11-byte 8.3 name
;     pattern at +1..+11 (?=$3F matches any single char; DIR issues all-? -> lists
;     every entry). Observed DE=$DA40, [$DA40]=80 3F 3F ... (M19 §2.3/§4.5).
;   - the runtime DTA base is the kernel's current-DTA pointer, the fixed work-area
;     word at DOS_DTAPTR ($F23D) (=$D403 here, set via the kernel's own SETDTA just
;     before the search); read fresh each call (M19 §4.1). It receives one drive
;     byte (current drive + 1) then the 32-byte raw dir entry (observed: DTA=
;     01 <32-byte entry>, M19 §4.4).
;   - NO attribute filter: SFIRST/SNEXT surface EVERY non-$E5, non-$00 entry incl.
;     volume-label ($08) and subdir ($10) entries (stock returned the SandStone
;     volume label as match #1; COMMAND.COM's formatter does the label filtering /
;     "nn files" count, not us — M19 §4.4/§7, verified against test.dsk).
; CLEAN-ROOM: our own dir walk over our own fat_* layer + the published FCB /
; directory-entry / SFIRST-SNEXT contract; the stock routine's internals (108/101
; page-1 PCs) were never decoded — only entry/exit registers, call counts, and
; one-sided DATA reads of OUR OWN memory. See docs/tier2-m19-spec.md.

; setdta_cache_body — the $5058 kernel SETDTA-time entry (M19). Caches the new DTA
; pointer (DE) into the disk work-area cell DOS_DTAPTR ($F23D), so the SFIRST/SNEXT
; bodies can read the runtime DTA from a fixed cell (as stock's SFIRST does, PCs
; $4FCC/$4FEF). Register-transparent (like curdrv_body/wa_seg): preserves A/BC/DE/
; HL/IX/IY. Reached from the fixed $5058 veneer (jp setdta_cache_body).
; CLEAN-ROOM: our own DE->$F23D store + the observed entry DE=DTA / write-$F23D
; contract; no stock routine internals decoded. See docs/tier2-m19-spec.md.
;   in:  DE = new DTA pointer ; out: ($F23D) := DE ; all registers preserved
setdta_cache_body:
                ld      (DOS_DTAPTR), de    ; $F23D := DE (runtime DTA pointer)
                ret

; getalloc_body — the $505D kernel GETALLOC-time entry (M20 REVISION 3;
; tier2-m20-spec.md). BDOS $1B GETALLOC: return the volume's allocation geometry.
;
; Walks clusters 2..(rawTotal-1) sector-by-sector into WBUF (the SAME fatofs/byteidx/
; parity math and the SAME shared fac_entry_from_wbuf unpack that fat_alloc_cluster
; uses -- fat.asm; not modified, not called in place, so the Tier-1 write path stays
; byte-unchanged), counting $000 (free) entries instead of stopping at the first one.
; The cluster/free-counter/loop-bound live on the CPU stack across each
; fac_entry_from_wbuf call (it clobbers AF/BC/DE/HL and preserves nothing -- same
; push/pop-around-the-call idiom as fat.asm's own fac_have_sec).
;
; The FIX (Revision 3, see the $505D veneer comment above for the full root-cause
; writeup): clear the dispatcher's HL-passthrough flag ($F306) before `ret`, loading
; the final A value AFTER the clear. Without this the kernel's common BDOS-exit path
; silently overwrites our correct HL with a mirror of our own A/BC.
;
; Any FDC read error takes the fail-safe exit (A=0 BC=$0200 DE=0 HL=0) -- matches
; fat_total_clusters' own "report no free space" error posture.
;
; CLEAN-ROOM: our own FAT scan (fat_mount + read_sector, reusing fat.asm's existing
; fac_entry_from_wbuf unpack) + the published GETALLOC A/BC/DE/HL contract (map.grauw.nl
; MSX-DOS BDOS functions) + the black-box-pinned $F306 dispatcher-flag semantics (no
; stock CODE decoded).
;   out (success): A=(FAT_SECPERCLUS) BC=$0200 DE=total data clusters
;                  HL=free-cluster count ; ($F306):=$00
;   out (fail-safe): A=0 BC=$0200 DE=0 HL=0
getalloc_body:
                call    fat_mount               ; geometry -> FAT_* scratch (SECTOR_BUF)
                jp      c, ga_fail
                call    fat_total_clusters       ; DE = dataClusters + 2 (rawTotal)
                push    de                       ; stack[0] = rawTotal (stays for the scan)
                ld      hl, $FFFF
                ld      (FAT_WRTMP2), hl         ; no FAT sector cached yet (fat_alloc_
                                                 ; cluster's own init, same convention)
                ld      de, 0                    ; DE = free-cluster counter
                ld      hl, 2                    ; HL = cluster under test
ga_scanloop:
                pop     bc                       ; BC = rawTotal (peek: pop then re-push)
                push    bc
                push    hl                       ; save cluster across the compare
                or      a
                sbc     hl, bc                   ; HL = cluster - rawTotal
                pop     hl                       ; restore cluster
                jp      z, ga_scandone           ; cluster == rawTotal -> scan complete
                ; fatofs = cluster + (cluster>>1)  (== floor(cluster*3/2), the same
                ; math fac_loop_body uses -- Microsoft FAT spec §3.2 12-bit packing)
                push    de                       ; save free counter across the call below
                push    hl                       ; save cluster (need it after the call)
                ld      a, l
                and     1
                ld      (FAT_PARITY), a
                ld      e, l
                ld      d, h
                srl     d
                rr      e                        ; DE = cluster >> 1
                add     hl, de                   ; HL = fatofs
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a     ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                        ; FAT sector offset = fatofs >> 9
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de                   ; HL = absolute FAT sector for this cluster
                ld      de, (FAT_WRTMP2)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jp      z, ga_havesec            ; already the cached sector -> no re-read
                ld      (FAT_WRTMP2), hl
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                jp      c, ga_rderr
ga_havesec:
                call    fac_entry_from_wbuf      ; DE = 12-bit entry value (clobbers
                                                 ; AF/BC/DE/HL -- fat.asm's own contract)
                ld      a, d
                or      e
                pop     hl                       ; restore cluster
                pop     de                       ; restore free counter
                jr      nz, ga_notfree
                inc     de                       ; entry == $000 -> free, bump counter
ga_notfree:
                inc     hl                       ; next cluster
                jp      ga_scanloop
ga_rderr:
                pop     hl                       ; discard saved cluster
                pop     de                       ; discard saved free counter
                pop     hl                       ; discard rawTotal
                jp      ga_fail
ga_scandone:
                ex      de, hl                   ; HL := free-cluster count (final)
                pop     de                       ; DE := rawTotal
                dec     de
                dec     de                       ; DE := total data clusters (final)
                xor     a
                ld      ($F306), a               ; clear dispatcher HL-passthrough flag
                                                 ; (M20 REVISION 3 fix -- see $505D veneer)
                ld      bc, $0200                ; BC := bytes/sector (final)
                ld      a, (FAT_SECPERCLUS)      ; A := sectors/cluster (final)
                or      a                        ; Cy = 0 (success)
                ret
ga_fail:
                xor     a
                ld      ($F306), a               ; clear here too (consistent with the
                                                 ; success path; harmless -- A=0 already
                                                 ; forces free_bytes=0 either way)
                ld      bc, $0200                ; BC := 512 (belt-and-braces)
                ld      de, 0
                ld      hl, 0
                ret

; sfirst_body — BDOS SFIRST ($11): find the FIRST matching root-dir entry.
;   in:  DE -> search FCB (name pattern at DE+1) ; out: A=$00 found / $FF none
sfirst_body:
                inc     de                  ; DE -> the 11-byte 8.3 pattern (FCB+1)
                ld      (FAT_NAMEPTR), de   ; dirscan_match compares against this
                call    fat_mount           ; (re)parse BPB -> FAT_FIRSTROOT/FAT_ROOTSECS
                jp      c, ds_none          ; disk error -> no entry
                ld      hl, 0
                ld      (BDOS_SRCHIDX), hl  ; scan cursor := entry 0
                jr      dirscan_match

; snext_body — BDOS SNEXT ($12): resume from BDOS_SRCHIDX, find the NEXT match.
;   in:  DE -> search FCB (name pattern at DE+1) ; out: A=$00 found / $FF exhausted
snext_body:
                inc     de                  ; DE -> the 11-byte 8.3 pattern (FCB+1)
                ld      (FAT_NAMEPTR), de
                call    fat_mount           ; geometry back into scratch (idempotent)
                jp      c, ds_none
                ; fall through: BDOS_SRCHIDX already points at the next entry.

; dirscan_match — walk the root dir from BDOS_SRCHIDX; on the first entry matching
; the pattern (name_cmp_wild) copy its drive-byte + 32-byte image to the DTA, set
; BDOS_SRCHIDX := match-index + 1, return A=$00. On $00 end-mark or all sectors
; scanned, return A=$FF. Reconstructs the sector cursor from BDOS_SRCHIDX alone
; (idx>>4 = sectors to skip; idx&15 = entry-in-sector) so it never persists
; FAT_DIRSEC/FAT_DIRREM across calls (M19 §4.3/§4.4).
dirscan_match:
                ; sectorsToSkip = BDOS_SRCHIDX >> 4  (16 entries per 512-B sector)
                ld      hl, (BDOS_SRCHIDX)
                ld      b, 4
dsm_shr:
                srl     h
                rr      l
                djnz    dsm_shr             ; HL = idx >> 4 = sector offset
                ; FAT_DIRSEC := FAT_FIRSTROOT + sectorOffset
                ld      de, (FAT_FIRSTROOT)
                add     hl, de
                ld      (FAT_DIRSEC), hl
                ; FAT_DIRREM := FAT_ROOTSECS - sectorOffset
                ld      hl, (BDOS_SRCHIDX)
                ld      b, 4
dsm_shr2:
                srl     h
                rr      l
                djnz    dsm_shr2            ; HL = idx >> 4 again (sector offset)
                ex      de, hl              ; DE = sector offset
                ld      hl, (FAT_ROOTSECS)
                or      a
                sbc     hl, de
                jp      z, ds_none          ; already past the last root sector
                jp      c, ds_none          ; (defensive) offset beyond root
                ld      (FAT_DIRREM), hl
dsm_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jp      z, ds_none          ; scanned every remaining root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    read_sector
                jp      c, ds_none          ; FDC error -> exhausted (no entry)
                ; start entry-in-sector = BDOS_SRCHIDX & 15
                ld      a, (BDOS_SRCHIDX)
                and     $0F
                ld      c, a                ; C = entry index within this sector
                ; HL = SECTOR_BUF + entry*32
                ld      hl, SECTOR_BUF
                ld      b, a
                or      a
                jr      z, dsm_athl
dsm_addent:
                ld      de, 32
                add     hl, de
                djnz    dsm_addent
dsm_athl:
                ld      a, 16
                sub     c
                ld      b, a                ; B = entries left in THIS sector (16-C)
dsm_entloop:
                ld      a, (hl)
                or      a
                jp      z, ds_none          ; $00 = end of directory -> exhausted
                cp      $E5
                jr      z, dsm_skip         ; deleted entry -> skip (no filter else)
                ld      de, (FAT_NAMEPTR)
                push    hl
                push    bc
                call    name_cmp_wild       ; Z if the 8.3 name matches the pattern
                pop     bc
                pop     hl
                jr      z, dsm_found
dsm_skip:
                ld      de, 32
                add     hl, de              ; next 32-byte directory entry
                call    dsm_bump            ; BDOS_SRCHIDX += 1 (advance past this one)
                djnz    dsm_entloop
                ; sector done: advance FAT_DIRSEC, dec FAT_DIRREM, next sector.
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jr      dsm_secloop
dsm_found:
                ; HL = matched 32-byte directory entry. Build the runtime DTA as the
                ; MSX-DOS SFIRST/SNEXT "found FCB" (drive + unopened FCB), matching
                ; stock byte-for-byte in every field COMMAND.COM's DIR reads (name,
                ; attribute, time, date, first cluster, size). The field layout was
                ; pinned black-box against stock's DTA + a readwatch of the DIR
                ; formatter's DTA reads (M19 §4.4):
                ;   DTA[0]      = drive (current drive + 1)
                ;   DTA[1..11]  = entry[0..10]  (11-byte 8.3 name)
                ;   DTA[12]     = 0  (FCB extent/EX)
                ;   DTA[13]     = entry[11]     (attribute)
                ;   DTA[14..22] = 0  (incl. the computed record-count field DIR
                ;                 never reads; left 0 -- black-box confirmed unread)
                ;   DTA[23..32] = entry[22..31] (time, date, first cluster, size)
                ; The attribute at DTA[13] is what lets DIR filter volume-label /
                ; subdir entries and count "nn files" correctly -- writing a verbatim
                ; raw entry (attr at DTA[12]) mis-set that filter (the alternating-
                ; garbage / wrong-count bug). CLEAN-ROOM: our own field copy from our
                ; own dir walk into the published FCB-result layout; no stock code.
                push    hl                  ; save entry ptr
                ld      de, (DOS_DTAPTR)    ; DE = runtime DTA base
                push    de                  ; save DTA base
                ; zero DTA[0..32] (33 bytes) so all gap/unset fields are $00.
                ld      h, d
                ld      l, e                ; HL = DTA base
                ld      (hl), 0
                push    hl
                pop     de                  ; DE = DTA base
                inc     de                  ; DE = DTA+1
                ld      bc, 32
                ldir                        ; propagate the $00 across DTA[1..32]
                pop     de                  ; DE = DTA base
                pop     hl                  ; HL = matched dir entry
                ; DTA[0] = drive (current drive + 1)
                ld      a, (CURDRV_CELL)
                inc     a
                ld      (de), a
                inc     de                  ; DE = DTA+1
                ; DTA[1..11] = entry[0..10] (name)
                push    hl                  ; keep entry base
                ld      bc, 11
                ldir                        ; -> DTA[1..11]; HL=entry+11, DE=DTA+12
                ; DTA[12] stays 0; DTA[13] = entry[11] (attr)
                inc     de                  ; DE = DTA+13
                ld      a, (hl)             ; entry[11] = attribute
                ld      (de), a
                ; DTA[14..22] stay 0; DTA[23..32] = entry[22..31]
                pop     hl                  ; HL = entry base
                ld      bc, 22
                add     hl, bc              ; HL = entry+22 (time/date/clus/size)
                ld      de, (DOS_DTAPTR)
                ld      a, e
                add     a, 23
                ld      e, a
                jr      nc, dsm_nohc
                inc     d
dsm_nohc:
                ld      bc, 10
                ldir                        ; -> DTA[23..32]
                call    dsm_bump            ; BDOS_SRCHIDX := match-index + 1
                xor     a                   ; A = $00 = found
                ret
ds_none:
                ld      a, $FF              ; A = $FF = no (more) matching entry
                ret

; dsm_bump — BDOS_SRCHIDX += 1 (advance the persistent scan cursor). Preserves all
; registers (HL is the live entry pointer at both call sites).
dsm_bump:
                push    hl
                ld      hl, (BDOS_SRCHIDX)
                inc     hl
                ld      (BDOS_SRCHIDX), hl
                pop     hl
                ret

; name_cmp_wild — compare an 11-byte dir name against the search pattern, with the
; FCB ? wildcard: a pattern byte of $3F matches any single character. Otherwise
; identical to name_cmp (case-insensitive via toupper). (Published CP/M-2.2 /
; MSX-DOS FCB match rule; M19 §4.5 — verified DIR issues an all-? pattern.)
;   in:  HL = directory-entry name, DE = search pattern ; out: Z set if match;
;        trashes A, B, DE, HL (HL/DE advanced 11 bytes; C preserved)
name_cmp_wild:
                ld      b, 11
ncw_loop:
                ld      a, (de)
                cp      $3F                 ; '?' pattern byte matches anything
                jr      z, ncw_next
                ld      a, (de)
                call    toupper
                ld      c, a
                ld      a, (hl)
                call    toupper
                cp      c
                ret     nz                  ; mismatch -> Z clear
ncw_next:
                inc     hl                  ; 16-bit inc: leaves flags intact
                inc     de
                djnz    ncw_loop
                ret                         ; Z set (all 11 positions matched)

; --- M24 slice B relocated bodies (tier2-m24-fclose-multicluster-spec.md §6) --

; rdb_recloop_body — verbatim relocation of disk/driver.asm's bdos_rdblk
; record/byte move loop (rdb_recloop..rdb_eof, unchanged since M21b). Moved
; here only because its old span's tail byte collided with the new $461D
; FMAKE-worker canonical entry; reached solely by driver.asm's own
; `jp rdb_recloop_body` fall-through (position-free, no external caller).
rdb_recloop_body:
                ld      hl, (RDBLK_DONE)
                ld      de, (RDBLK_REQ)
                or      a
                sbc     hl, de
                jr      z, rdb_ok           ; delivered every requested record
                ld      hl, (RDBLK_RECSIZE)
                ld      (RDBLK_CNT), hl     ; bytes still to copy for this record
rdb_byteloop:
                ld      hl, (RDBLK_CNT)
                ld      a, h
                or      l
                jr      z, rdb_recdone      ; whole record copied
                ; EOF when every file byte has been delivered (BYTESLEFT == 0)
                ld      hl, (BDOS_BYTESLEFT)
                ld      de, (BDOS_BYTESLEFT + 2)
                ld      a, h
                or      l
                or      d
                or      e
                jr      z, rdb_eof
                call    rdblk_getbyte       ; A = next file byte (advances buffer)
                jr      c, rdb_eof          ; chain ended early (defensive)
                ld      hl, (RDBLK_DST)
                ld      (hl), a
                inc     hl
                ld      (RDBLK_DST), hl
                ld      hl, (RDBLK_CNT)
                dec     hl
                ld      (RDBLK_CNT), hl
                jr      rdb_byteloop
rdb_recdone:
                ld      hl, (RDBLK_DONE)
                inc     hl
                ld      (RDBLK_DONE), hl
                jr      rdb_recloop_body
rdb_ok:
                xor     a                   ; A = $00 all requested records read
                ld      hl, (RDBLK_DONE)
                ld      b, h                ; BC = HL = records read (§8.33): the genuine
                ld      c, l                ; BDOS $27 returns the count in BOTH HL and BC,
                ret                         ; and MSXDOS.SYS init reads BC (§8.32 $024A branch)
rdb_eof:
                ld      a, $01              ; A = $01 EOF before all requested
                ld      hl, (RDBLK_DONE)    ; HL = records actually read
                ld      b, h                ; BC = HL = records read (§8.33; see rdb_ok)
                ld      c, l
                ret

; fat_mount_tail — verbatim relocation of disk/fat.asm's fat_mount continuation
; (from the numFATs*secPerFAT multiply setup through the final `ret`,
; unchanged). Moved here only because the multiply's `ld hl,0` tail byte
; collided with the new $477D WRSEQ-worker canonical entry; reached solely by
; fat_mount's own `jp fat_mount_tail` fall-through (position-free, no
; external caller). The diversion point had to move one instruction earlier
; than the collision itself (to `ld b,a`) to leave enough room for the
; 3-byte veneer to land exactly at $477D (a 3-byte-for-3-byte swap at the
; collision point alone leaves zero slack).
; wrseq_body — MSX-DOS-1 kernel per-record sequential-I/O worker entry
; $477D's body. CORRECTED (M25, tier2-m24-fclose-multicluster-spec.md
; "UPDATE 2"): the RAM kernel CALLs $477D for EVERY sequential record
; access -- BOTH BDOS $15 WRSEQ *and* BDOS $14 RDSEQ share this ONE page-1
; entry (confirmed black-box via `callwatch --in-func 0x14`; no register at
; entry distinguishes direction -- BC/DE/HL/AF identical in shape between a
; genuine WRSEQ hit and a RDSEQ hit), so direction is read from OUR OWN
; BDOS_WRMODE cell instead: nonzero forwards to bdos_seqwrite (unchanged);
; zero forwards to bdos_seqread. The companion fix in fopen_fill_body
; (disk/fat.asm) seeds the read-iterator state (fat_open, BDOS_RECIDX,
; BDOS_BYTESLEFT) that bdos_seqread depends on and that a real kernel-driven
; FOPEN never populated before -- without it bdos_seqread ran but always
; reported false EOF.
; DTA staleness (M21b lesson, see k_47B2 above): the kernel's real SETDTA
; only ever writes DOS_DTAPTR ($F23D), never our own mini-BDOS's BDOS_DTA
; cell, so BDOS_DTA must be reseeded from DOS_DTAPTR before EITHER
; bdos_seqread or bdos_seqwrite consumes it -- both directions need the
; reseed, not just write. DE (=IY=$DA40 kernel FCB pointer) is not consumed
; by either -- both are single-open-file global state, same as Tier-1. Exit
; A=$00/$01/$FF passes straight through from whichever real routine ran.
; $F306 left untouched (M24 spec §5 item 4: no observed load-bearing exit HL
; for this entry family -- default to the kernel's own H:=B,L:=A mirror
; unless the acceptance diff proves otherwise).
;
; M33 (tier2-m33-m32-fcb-position-spec.md §2.2) added the RDSEQ FCB position
; write-back HERE, in the read branch only -- NOT inside bdos_seqread_body,
; which is a SHARED routine also reached by RRND $21 (rdrnd_body, kernel.asm
; ~2697, which does its own M26 copy+32:=copy+33 bookkeeping) and by the boot
; mini-BDOS (driver.asm bdos_entry, which must stay byte-identical). Putting
; the write-back inside bdos_seqread_body would corrupt those other callers'
; FCBs / the boot path, so instead the read branch's tail-jump becomes a call
; + inline write-back + ret. Only on a DELIVERED record (A=$00 on return; on
; A=$01 EOF, §2.3, skip it -- stock's position stops at/after EOF). Body =
; wrseq_writeback (free tail): writes copy+32/+12/+28/29/+30 from the fixed
; FCB-copy base $DA40 (a constant here -- no register to preserve across the
; call). A is stashed across the write-back and restored before ret so
; bdos_seqread's pass-through A/HL exit contract is unchanged.
wrseq_body:
                ld      hl, (DOS_DTAPTR)
                ld      (BDOS_DTA), hl
                ld      a, (BDOS_WRMODE)
                or      a
                jr      nz, wrseq_body_write
                call    bdos_seqread
                or      a
                call    z, wrseq_writeback  ; only on a delivered record (A=$00)
                ret
wrseq_body_write:
                ; Item 5 (spec-diskbasic-option-closure.md): the write-side twin of
                ; the M33 read-branch FCB-position write-back. M33 advanced the
                ; caller-visible FCB position (+32 CR / +12 EX / +28,29 cluster /
                ; +30 rec-in-cluster) after each DELIVERED read record but wired it
                ; to the read branch only; stock MSX-DOS-1 advances the FCB on
                ; sequential WRITES too. Our file bytes were already correct (the
                ; write-iterator tracks position internally); only the caller-visible
                ; FCB position went stale, observable via a WRSEQ-then-$24-SETRND
                ; sequence (SETRND reads +12/+32). Mirror the read branch: advance
                ; only on a WRITTEN record (A=$00; on A=$01 disk-full / A=$FF
                ; not-open, do NOT advance -- no record was stored). The twin is
                ; fully register-transparent (preserves AF/BC/DE/HL), so the write
                ; branch still returns bdos_seqwrite's exact registers -- BDOSX3/
                ; BDOSX4 register snaps are unchanged; only the FCB position moves.
                call    bdos_seqwrite
                or      a
                call    z, wrseq_wr_writeback   ; advance FCB position on a written record
                ret

; fdc_read_data_body — relocated fdc_read_data (M26, tier2-m26-spec.md): its
; old span at driver.asm's $435A collided with the real kernel's canonical
; $17 FREN dispatch entry, $4392 (56 bytes into the original 74-byte body --
; the fdc_rd_n1/fdc_rd_n2 status-decode tail). Logic below is byte-for-byte
; unchanged from the original; driver.asm's fdc_read_data is now a 3-byte
; `jp` thunk to here, freeing $4392 for the real `jp fren_body` veneer.
fdc_read_data_body:
                ld      e, 2            ; two 256-byte halves
fdc_rd_blk:
                ld      b, 0            ; djnz 0 -> 256 iterations
fdc_rd_wait:
                ld      a, (FDC_STATUS)
                bit     1, a            ; DRQ?
                jr      nz, fdc_rd_byte
                bit     0, a            ; BUSY?
                jr      nz, fdc_rd_wait
                jr      fdc_rd_status   ; finished with no DRQ -> short/error
fdc_rd_byte:
                ld      a, (FDC_DATA)
                ld      (hl), a
                inc     hl
                djnz    fdc_rd_wait
                dec     e
                jr      nz, fdc_rd_blk
fdc_rd_drain:
                ld      a, (FDC_STATUS) ; all 512 read; wait for command end
                bit     0, a
                jr      nz, fdc_rd_drain
fdc_rd_status:
                ld      a, (FDC_STATUS)
                and     ST_NOTRDY + ST_RNF + ST_CRC + ST_LOST
                jr      z, fdc_rd_ok
                ld      b, a            ; keep the error bits
                and     ST_NOTRDY
                jr      z, fdc_rd_n1
                ld      a, 2            ; not ready
                scf
                ret
fdc_rd_n1:
                ld      a, b
                and     ST_RNF
                jr      z, fdc_rd_n2
                ld      a, 8            ; record not found
                scf
                ret
fdc_rd_n2:
                ld      a, b
                and     ST_CRC
                jr      z, fdc_rd_n3
                ld      a, 4            ; CRC / data error
                scf
                ret
fdc_rd_n3:
                ld      a, 12           ; lost data / other
                scf
                ret
fdc_rd_ok:
                or      a               ; A = 0, Cy = 0
                ret

; bdos_seqwrite_body — relocated bdos_seqwrite (M26, tier2-m26-spec.md): its old
; span at disk/fat.asm's $46EE collided with the real kernel's canonical $30
; WRABS dispatch address, $4720 -- the displacement byte of the `jr c,
; bsw_full` that used to live there (trace --resync: ours fell through into
; live bdos_seqwrite tail code, silently zeroing BDOS_WRBUFLEN via the
; buffer-drain path before reaching bsw_ok's false-success `ret`). Logic
; below is byte-for-byte unchanged; disk/fat.asm's bdos_seqwrite is now a
; 3-byte `jp` thunk to here, freeing $4720 for the real `jp wrabs_body`
; veneer. Only symbolic callers (`jp bdos_seqwrite` in driver.asm/kernel.asm)
; reference this routine -- no external code jumps into bsw_ok/bsw_full/
; bsw_err/wrbytes_add_recsize's middle, so the whole unit relocates cleanly.
bdos_seqwrite_body:
                ld      a, (BDOS_WRMODE)
                or      a
                jr      z, bsw_err          ; not open for write
                ; --- M34 (tier2-m34-wrseq-diskfull-spec.md §3.1): eager disk-full
                ; onset parity with stock. At a sector start that would need a
                ; NEW cluster, confirm one is available BEFORE buffering/counting
                ; this record -- mirrors ffds_nopad_body's own needs-a-new-cluster
                ; test (kernel.asm ffds_nopad_body) so the real allocation (still
                ; at flush time, unchanged) never fails after we've claimed A=$00.
                ld      hl, (BDOS_WRBUFLEN)
                ld      a, h
                or      l
                jr      nz, bsw_m34_buffer  ; mid-sector: cluster already validated
                ld      hl, (BDOS_WRCLUS)
                ld      a, h
                or      l
                jr      z, bsw_m34_needclus ; no cluster yet (fresh file)
                ld      a, (BDOS_WRSECIDX)
                ld      hl, FAT_SECPERCLUS
                cp      (hl)
                jr      c, bsw_m34_buffer   ; room in current cluster -> no new one
bsw_m34_needclus:
                call    fat_have_free_cluster ; Cy=0 a $000 cluster exists; Cy=1 none
                jr      nc, bsw_m34_buffer
                ld      a, $01              ; disk full -- BEFORE any buffering
                ret
bsw_m34_buffer:
                ; copy RECSIZE bytes DTA -> SECTOR_BUF + BDOS_WRBUFLEN
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, SECTOR_BUF
                add     hl, de              ; HL = dest in SECTOR_BUF
                ex      de, hl              ; DE = dest
                ld      hl, (BDOS_DTA)      ; HL = source record (settable DTA)
                ld      bc, RECSIZE
                ldir                        ; copy 128 bytes into the buffer
                ; advance buffered length and total byte count by RECSIZE.
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, RECSIZE
                add     hl, de
                ld      (BDOS_WRBUFLEN), hl
                call    wrbytes_add_recsize ; BDOS_WRBYTES += RECSIZE (4-byte LE)
                ; if the 512-byte buffer is now full, flush it to the file.
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, 512
                or      a
                sbc     hl, de
                jr      c, bsw_ok           ; buffer not full yet
                call    fat_flush_data_sector
                jr      c, bsw_full         ; disk full / write error
                ld      hl, 0
                ld      (BDOS_WRBUFLEN), hl ; buffer drained
bsw_ok:
                xor     a                   ; A = $00 success
                ret
bsw_full:
                ld      a, $01              ; disk full (MSX-DOS seq-write code)
                ret
bsw_err:
                ld      a, $FF
                ret

; wrbytes_add_recsize — BDOS_WRBYTES += RECSIZE, 4-byte little-endian add.
wrbytes_add_recsize:
                ld      hl, BDOS_WRBYTES
                ld      a, (hl)
                add     a, RECSIZE
                ld      (hl), a
                inc     hl
                ld      b, 3                ; carry through the upper 3 bytes
wba_loop:
                ld      a, (hl)
                adc     a, 0
                ld      (hl), a
                inc     hl
                djnz    wba_loop
                ret

; fdel_body — MSX-DOS-1 kernel FDEL ($13) canonical entry $436C's real body
; (M26, tier2-m26-spec.md sec 2.2). CLEAN-ROOM, single exact-match only
; (same fat_find precedent as fren_body -- BDOSX3 only exercises an exact
; name; '?' wildcard multi-delete is out of scope, confirmed at sign-off).
; PLACEMENT NOTE: this body first landed appended to disk/fat.asm's own end
; (next to fren_ioerr/rdabs_ioerr/wrabs_ioerr, following those three's own
; precedent), but that broke test_gdate.py/test_getdpb.py -- fat.asm's tail
; feeds straight into kernel.asm's own tightly-packed pinned-address
; corridor (GDATE $553C etc, disk/kernel.asm) with no slack for a body this
; size (same "64KB limit passed" class of hazard the FREN slice already hit
; once and worked around by using kernel.asm's OWN free tail instead -- see
; fdc_read_data_body below). Moved here for the same reason.
; Entry is a kernel-side FCB copy pointed to by DE (drive byte + 11-byte
; 8.3 name, zero-filled tail) -- same +1 name-field convention fren_body
; uses. Two things this body must do that fren_body didn't: (a) free the
; file's FAT12 chain (every cluster zeroed in EVERY on-disk FAT copy, via
; fat_next_cluster/fat_write_fat_entry) -- confirmed necessary by black-box
; on-disk $E5 forensics: stock frees both clusters of BDOSX3's 2-cluster
; scratch file, so a bare $E5 stamp alone would under-match stock (leak the
; chain); (b) only THEN stamp the directory entry's first byte $E5 and
; persist it. Order matters: fat_next_cluster/fat_write_fat_entry both use
; SECTOR_BUF as scratch, clobbering the dirent fat_find first located -- so
; the chain-free walk runs BEFORE re-locating the entry (a second fat_find
; call, cheap and reuses already-verified code rather than tracking a
; pointer across a clobbering call). IX holds the FCB-copy pointer across
; every helper call in this body (confirmed by inspection: fat_mount,
; fat_find, fat_next_cluster, fat_write_fat_entry, read_sector, and
; write_sector never touch IX -- only fopen_fill_body/fren_body do, in
; disk/fat.asm), so re-deriving the name pointer for the second fat_find is
; just IX+1 again.
fdel_body:
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer (held throughout)
                push    ix
                pop     de
                call    fat_mount
                jp      c, fdel_miss
                push    ix
                pop     de
                inc     de                  ; DE -> FCB-copy+1 (target 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found; FAT_FIRSTCLUS/FAT_FILESIZE set
                jp      c, fdel_miss
                ld      hl, (FAT_FIRSTCLUS)
                ld      a, h
                or      l
                jr      z, fdel_relocate    ; zero-length file: no chain to free
fdel_free_loop:
                push    hl                  ; stack: [cur cluster]
                call    fat_next_cluster    ; HL := next link (cur was consumed as input)
                ex      (sp), hl            ; stack: [next]; HL := cur
                ld      de, 0               ; free = $000 (Microsoft FAT spec sec 3.2)
                call    fat_write_fat_entry ; zero cur's entry in every on-disk FAT copy
                jp      c, fdel_chain_ioerr
                pop     hl                  ; HL := next
                ld      de, $0FF8           ; >= $0FF8 = end-of-chain (fat_next_cluster's own convention)
                or      a
                sbc     hl, de
                jr      nc, fdel_relocate   ; next >= $0FF8 -> chain fully freed
                add     hl, de              ; HL := next again (undo the probe subtraction)
                jr      fdel_free_loop
fdel_chain_ioerr:
                pop     hl                  ; discard the saved "next", keep the stack balanced
                jp      fdel_ioerr
fdel_relocate:
                ; SECTOR_BUF now holds FAT-sector content (clobbered by the chain
                ; walk above, or untouched if this file was zero-length) -- re-run
                ; fat_find for a fresh, valid dirent pointer + FAT_DIRSEC.
                push    ix
                pop     de
                inc     de
                ex      de, hl
                call    fat_find
                jp      c, fdel_miss
                ld      (hl), $E5           ; CP/M delete marker (Microsoft FAT spec sec 3.1)
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    write_sector
                jp      c, fdel_ioerr
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      h, a
                ld      l, a                ; HL = $0000 on success (pinned exit value)
                ret
fdel_miss:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, $FF              ; not-found (fren_miss convention; untested by BDOSX3)
                ret
fdel_ioerr:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, 2                ; generic FDC I/O error (fdc_read_data convention)
                ret

; rrnd_position / rrnd_sector / rdrnd_body / wrrnd_body — MSX-DOS-1 kernel
; RDRND ($21) / WRRND ($22) canonical entries $4788/$4793's real bodies (M26,
; tier2-m26-spec.md §2.3). CLEAN-ROOM. Entry is the same kernel FCB-copy
; convention as fdel_body/rdabs_body/wrabs_body: DE -> a 37-byte scratch copy
; of the FCB at $DA40; copy+33 = the FCB random-record field r0 (BDOS $18 SETRND
; / direct FCB poke). SCOPE (signed off at implementation time, same class of
; narrowing as FREN's/FDEL's single-exact-match precedent): only r0 (0..255,
; up to a 32640-byte file) positions the record; r1/r2 (copy+34/+35) are NOT
; read -- BDOSX3 only exercises r0 in {1,2} and no on-disk MSX-DOS-1 floppy
; file needs more than r0 to stay within this milestone's verified acceptance
; bar. PLACEMENT: kernel.asm's free tail (not disk/fat.asm's own end), per the
; FDEL slice's placement lesson (fat.asm's tail starves kernel.asm's own
; pinned-address corridor of slack for a body this size).
;
; rrnd_position seeds the existing sequential-read iterator (FAT_CURCLUS/
; FAT_CLUSSEC/BDOS_RECIDX/BDOS_BYTESLEFT/BDOS_DTA) to point at record r0,
; reusing fat_open + repeated fat_read_file_sector calls (each one reads
; exactly one more sector and advances the cluster chain as needed) rather
; than a dedicated fast-seek -- correct and simple, and the only sector-
; addressing arithmetic (firstData + (cluster-2)*secPerClus + clussec)
; already exists inside fat_read_file_sector/frs_mul_body. rdrnd_body then
; reuses bdos_seqread verbatim for the actual transfer (§4 non-goal: no
; change to bdos_seqread_body itself). wrrnd_body CANNOT reuse
; wrseq_body/bdos_seqwrite the same way -- that engine is append-oriented
; (BDOS_WRMODE-gated, a 512-byte-flush model for a file opened by FMAKE) and
; wrong for overlaying 128 bytes mid-file into a file opened for READ by
; FOPEN -- so it is a small, new read-modify-write body instead: overlay the
; DTA's 128 bytes into the sector rrnd_position already loaded into
; SECTOR_BUF, then persist via write_sector. Because fat_read_file_sector
; does not expose the absolute sector number it just read (only frs_mul_body,
; entered by `jp`, computes it, mid an unrelated read call already committed
; to SECTOR_BUF), wrrnd_body's rrnd_sector helper mirrors that same formula
; independently (does NOT modify frs_mul_body -- §4 non-goal) using the
; POST-call FAT_CURCLUS/FAT_CLUSSEC state: fat_read_file_sector always
; finishes with FAT_CURCLUS already advanced to the sector it read (if
; needed) and FAT_CLUSSEC incremented by exactly one past it -- so
; `FAT_CLUSSEC - 1` safely recovers the clussec of the sector just read, with
; no off-by-one or cluster-boundary hazard (confirmed by reading
; fat_read_file_sector's own body: the increment always follows the read,
; never precedes it, and is never separately normalised/wrapped).
;
; Register contract (capture, tier2-m26-spec.md §2.3): entry A=$25 B=$00
; C=$00 DE=$DA40 SP=$DBFE ret=$D88A (FDEL-dispatcher class, not RDABS's — no
; addr-low fingerprint, C is not the function number); exit A=$00 H=$00
; L=$00 on success. Stock's one clear random-op FCB side effect: CR (user
; FCB+32, mirrored at copy+32) := r0's low byte post-call -- reproduced here
; explicitly (copy+32 := copy+33) since it is a per-call random-op effect,
; not a generic kernel copy-back artifact (contrast fdel_body's DE=$03D0,
; which the kernel already reproduced with no fdel_body code at all).
rrnd_position:
                ld      hl, (DOS_DTAPTR)
                ld      (BDOS_DTA), hl      ; reseed our own DTA cell (M19 lesson:
                                            ; the kernel's real SETDTA only ever
                                            ; touches DOS_DTAPTR, never BDOS_DTA)
                ld      a, (ix+33)          ; A = r0 (target record, 0..255; see scope note)
                push    af
                call    fat_open            ; reset iterator to file start (FAT_FIRSTCLUS)
                pop     af
                ld      c, a                ; C = r0 (preserved across fat_open)
                and     3
                ld      (RRND_RECSEC), a    ; stash record-in-sector for after the seek loop
                                            ; (RAM: a ROM cell here silently no-op'd -> wrong record)
                ld      a, c
                srl     a
                srl     a                   ; A = target sector-in-file (r0 >> 2)
                inc     a                   ; A = seek-loop count (>= 1)
                ld      b, a
                ; BDOS_BYTESLEFT := FAT_FILESIZE - r0*RECSIZE (r0*128 <= 32640, always
                ; fits 16 bits, so only the filesize low word can matter here)
                ld      h, 0
                ld      l, c                ; HL = r0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = r0 * 128
                ld      de, (FAT_FILESIZE)
                ex      de, hl              ; HL = filesize_lo16, DE = r0*128
                or      a
                sbc     hl, de              ; HL = filesize_lo16 - r0*128; Cy=1 if r0 is past EOF
                jr      c, rrnd_pos_beyond
                ld      (BDOS_BYTESLEFT), hl
                ld      hl, (FAT_FILESIZE + 2)
                ld      (BDOS_BYTESLEFT + 2), hl
                jr      rrnd_pos_seek
rrnd_pos_beyond:
                ld      hl, 0
                ld      (BDOS_BYTESLEFT), hl
                ld      (BDOS_BYTESLEFT + 2), hl
rrnd_pos_seek:
rrnd_pos_loop:
                push    bc
                call    fat_read_file_sector
                pop     bc
                jr      c, rrnd_pos_err     ; seek ran off the end of the chain
                djnz    rrnd_pos_loop
                ld      a, (RRND_RECSEC)
                ld      (BDOS_RECIDX), a
                or      a                   ; Cy = 0 ok
                ret
rrnd_pos_err:
                scf
                ret
                ds      1, $00              ; (was rrnd_recsector db 0 — cell moved to RAM
                                            ; RRND_RECSEC; byte retained for net-zero layout)

; rrnd_sector — recover the absolute logical sector number rrnd_position's
; seek loop last landed on (see the placement note above for why this is
; safe: FAT_CLUSSEC - 1, FAT_CURCLUS as-is).
;   out: DE = absolute logical sector number; trashes AF, BC, HL
rrnd_sector:
                ld      a, (FAT_CLUSSEC)
                dec     a
                ld      (RRND_CLUSSEC), a   ; (RAM: ROM cell here silently no-op'd)
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de              ; HL = cluster - 2
                ex      de, hl              ; DE = cluster - 2
                ld      hl, 0
                ld      a, (FAT_SECPERCLUS)
                ld      b, a
rrnd_sector_mul:
                add     hl, de
                djnz    rrnd_sector_mul     ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (RRND_CLUSSEC)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl              ; DE = absolute logical sector (write_sector's convention)
                ret
                ds      1, $00              ; (was rrnd_clussec_tmp db 0 — cell moved to RAM
                                            ; RRND_CLUSSEC; byte retained for net-zero layout)

rdrnd_body:
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer
                call    rrnd_position
                jp      c, rrnd_eof
                call    bdos_seqread        ; A=$00 record delivered / $01 EOF
                or      a
                jr      nz, rrnd_finish     ; EOF from seqread -- pass A through, HL untested
                ld      a, (ix+33)          ; CR (copy+32) := r0 (stock's random-op side effect)
                ld      (ix+32), a
                xor     a
                ld      h, a
                ld      l, a                ; HL = $0000 (pinned exit value, success)
                jr      rrnd_finish
rrnd_eof:
                ld      a, $01              ; positioned past end-of-file
                jr      rrnd_finish

wrrnd_body:
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer
                call    rrnd_position
                jp      c, wrrnd_ioerr      ; positioned past EOF -- FAT growth is out of
                                            ; scope this milestone (§4 non-goal), same as
                                            ; every other M26 fix
                ; SECTOR_BUF now holds the target sector (loaded by rrnd_position's seek
                ; loop) -- overlay the caller's DTA record into it at BDOS_RECIDX*RECSIZE.
                ld      a, (BDOS_RECIDX)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = BDOS_RECIDX * 128
                ld      de, SECTOR_BUF
                add     hl, de              ; HL -> target record within SECTOR_BUF
                ex      de, hl              ; DE = dest in SECTOR_BUF
                ld      hl, (BDOS_DTA)      ; HL = source record in the caller's DTA
                ld      bc, RECSIZE
                ldir
                call    rrnd_sector         ; DE = absolute logical sector to persist
                ld      hl, SECTOR_BUF
                call    write_sector
                jp      c, wrrnd_ioerr
                call    wrrnd_extend        ; M36: grow ix+16..19 + the on-disk dirent if this
                                            ; write landed past the previous end-of-file
                jp      c, wrrnd_ioerr
                ld      a, (ix+33)          ; CR (copy+32) := r0 (stock's random-op side effect)
                ld      (ix+32), a
                xor     a
                ld      h, a
                ld      l, a                ; HL = $0000 (pinned exit value, success)
                jr      rrnd_finish
wrrnd_ioerr:
                ld      a, 2                ; generic FDC I/O error (fdc_read_data convention,
                                            ; untested by BDOSX3 -- no negative-path record)
rrnd_finish:                                ; shared tail: M20 dispatcher-flag rule, preserve A
                push    af
                xor     a
                ld      ($F306), a
                pop     af
                ret

