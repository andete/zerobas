#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Differential crunch probe — prove zerobas tokenises byte-for-byte like a real
MSX-BASIC ROM (Step A).

Mechanism (harness rework, 2026-07-12): each test body is injected as the STORED
line  `1 <body>`  (a numbered line, so it is tokenised into the program area but
never executed — no RUN, no BLOAD, no CPU freeze) via omsx_repl's typing-free
KEYBUF path. The crunched line then lives at TXTTAB ($F676): link(2) + lineno(2)
+ tokens + 0x00. We read the EXACT line back (`omsx_repl`'s ("stored_line", …)
capture dereferences the link pointer, so an embedded 0x00 in a value byte never
truncates it) and compare the body tokens (bytes after the 4-byte header) between
the two sides: equal == byte-identical crunch.

This shed the former per-line BLOAD-freeze-at-TAPION capture (KBUF on the
reference, TOKBUF on zerobas): a stored line neither freezes nor executes, so the
whole corpus shares ONE boot per side (batched), and the two execution disciplines
(LINES vs CRUNCH_ONLY, bload-trails vs bload-leads) collapse — nothing runs, so
every body is just `1 <body>`. Proven byte-identical to the old freeze capture
across the whole corpus on both machines before the switch (spike_crunch), and
strictly stronger: embedded-0x00 lines (a=256, goto 40, bsave …,&hc000) are now
compared in FULL instead of truncated at the first embedded zero.

Two zerobas targets:
  * `--cart build/basic.rom` -- the lean 16 KB cartridge on the reference machine
    (the original mode; runs LINES + CRUNCH_ONLY).
  * `--zb-machine C-BIOS_MSX1_EU_REPACK_DISK` -- the merged repack build, whose BASIC
    is baked into slot 0 (no cart). This mode ADDS the string-engine keywords
    (LEN/LEFT$/RIGHT$/MID$/CHR$/ASC/STR$/VAL) plus the string-functions slice
    (HEX$/OCT$/SPACE$ -- $FF-prefixed; STRING$/INSTR -- bare single-byte
    tokens): the lean build emits them as verbatim ASCII (they never tokenise),
    so only the repack build can be proven to crunch them byte-for-byte like
    the VG-8020 -- AND against the §4 captured token bytes
    (docs/spec-basic-string-engine.md, docs/spec-basic-string-functions.md).
    This is the crunch half of `string-acceptance`.

Clean-room: this only *compares observed outputs*. No disassembly; the reference
ROM is a black box. See the clean-room firewall (CONTRIBUTING.md).
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse

import omsx_repl  # typing-free KEYBUF-injection REPL driver (harness rework)

MACHINE = "Philips_VG_8020"
TXTTAB = 0xF676   # sysvar: 2-byte LE pointer to the BASIC text base (both machines)

# Test lines (the probe appends `:bload"cas:",r`). They exercise the integer
# encoding across magnitudes, &H, the operators, and representative whole lines.
LINES = [
    "a=0", "a=9", "a=10", "a=255", "a=256", "a=32767",
    "a=&h0", "a=&hff", "a=&hd000", "a=&hffff",
    "a=1+2", "a=5-1", "a=2*3",
    "poke &hd000,2*3+4",
    "a=peek(&hd000)",
    # DATA stores its items as verbatim ASCII (oracle), not crunched tokens;
    # these confirm zerobas copies the body byte-for-byte (and stops at ':').
    "data 5,6", "data -5,&hff", "data 300,abc",
]

# Crunch-only lines: their bytes are validated, but the body must NOT execute
# (a direct `goto 40` errors with "undefined line"; `gosub`/`for`/`next`/`restore`
# aren't direct-executable; `end`/`stop` halt; a bare comparison isn't a
# statement). So the freeze-bload is *prepended* — it hands off at TAPION first,
# freezing the crunch buffer with the whole line already tokenised, while the
# body after the ':' is crunched but never run. (spec-controlflow.md:
# keyword tokens from Table 2.20, the $0E line-number code from Figure 2.12,
# and the '<' $F0 / '>' $EE relational tokens.)
CRUNCH_ONLY = [
    "goto 40", "gosub 100", "restore 50",
    # PRINT USING formatted output. USING = $E4 (oracle-locked); the format string is
    # kept verbatim ASCII in its quotes (`#`=$23, `\ \`=$5C 20 5C), then ';' + values.
    'print using"###";5',
    r'print using"\ \";a$',
    # CALL FORMAT. CALL = $CA; the extended-statement NAME after CALL (or the '_'
    # abbreviation) is kept verbatim, NOT keyword-crunched: `call format` -> CA 20
    # "FORMAT", `_format` -> 5F "FORMAT". The non-CALL `format=5` -> FOR($82)+MAT
    # confirms the verbatim rule is CALL-scoped (keywords still crunch inside names).
    "call format",
    "_format",
    "call music",
    "format=5",
    "if a then 40", "if a then b=1 else b=2",
    "for i=1 to 10 step 2", "next i", "end", "stop",
    "a<=b", "a>=5", "a<>0",
    # SAVE / BSAVE statement tokens (oracle-LOCKED, Philips VG-8020). BSAVE = $D0,
    # SAVE = $BA, both single-byte statement tokens; the quoted filename is kept
    # verbatim ASCII and each &H address crunches to $0C <lo> <hi>. These would
    # WRITE a file / error in direct mode, so they are CRUNCH_ONLY (the prepended
    # freeze-bload halts at TAPION with the whole line already crunched). The
    # &HC0C1/&HC031/&HC0C2 case has no embedded $00 so it is compared in FULL;
    # the &HC000 case (0C 00 C0) is compared up to its first embedded $00, exactly
    # like the line-number cases above (e.g. `goto 40` -> 0E 28 00).
    'bsave"x",&hc0c1,&hc031,&hc0c2',
    'bsave"a:prog.bin",&hc000,&hc031',
    'save"a:prog"',
    'save"a:prog",a',
    # Disk BASIC FILES token (Phase 2). FILES = $B7 (MSX2 TH Table 2.20); the
    # disk-extension keyword is in the MAIN ROM's reserved-word table even on the
    # diskless VG-8020 reference, so it crunches to the same single token byte.
    "files",
    # MERGE (merge an ASCII program from disk). Token $B6, in the main ROM table
    # like FILES; the filename is kept verbatim ASCII.
    'merge"prog.bas"',
    # Phase 2 sequential file-channel verbs. OPEN $B0, INPUT $85, LINE $AF,
    # CLOSE $B4; "AS" and "#" stay verbatim ASCII; the channel digit crunches to
    # the $11+n single-digit token (1 -> $12). All in the main ROM table.
    'open"hi.txt" for input as #1',
    'line input#1,a$',
    'input#1,a$',
    # INPUT$(n,#f): a string FUNCTION, but not a dedicated token — "INPUT$" crunches
    # to INPUT ($85) + '$' ($24); the args ( n , # f ) stay literal ASCII.
    'a$=input$(2,#1)',
    'close#1',
    # Write path. "OUTPUT" crunches to OUT($9C)+PUT($B3) — two reserved words, not
    # one keyword; PRINT# is the ordinary PRINT token ($91) + '#n,'.
    'open"o.dat" for output as #1',
    'print#1,"hello"',
    # APPEND mode. "APPEND" is NOT a reserved word on the main ROM — it crunches to
    # the name "APP" (verbatim ASCII 41 50 50) + the END token ($81), so OPEN's mode
    # parser matches APP+END. zerobas (no APPEND keyword either) emits the same bytes.
    'open"a.dat" for append as #1',
    # File management: KILL = $D4, NAME = $D3 (MSX2 TH Table 2.20); "AS" verbatim.
    'kill"a:out.txt"',
    'name"old.txt" as "new.txt"',
    # File-info functions: $FF-prefixed (EOF=$FF$AB, LOF=$FF$AD, DSKF=$FF$A6).
    'a=eof(1)',
    'a=lof(1)',
    'a=dskf(0)',
    # MAXFILES (Phase 2 multi-channel config): "MAXFILES" crunches to TWO reserved
    # words — MAX ($CD) + FILES ($B7) — exactly like OUTPUT = OUT+PUT; then `=2`.
    'maxfiles=2',
    # Random-access conversions (Phase 2c). $FF-prefixed function tokens: MKI$=$FF$AE
    # (the '$' is PART of the keyword), CVI=$FF$A8. Float siblings need Phase-3 floats.
    'a$=mki$(258)',
    'a=cvi(b$)',
    # Random-access record verbs (Phase 2c slice 1). Single-byte statement tokens
    # FIELD=$B1, LSET=$B8, RSET=$B9 (oracle-locked; MSX2 TH Table 2.20). "AS" stays
    # verbatim ASCII; the channel digit + small widths crunch to $11+n single-digit
    # tokens (#1 -> 23 12; the 2 -> 13). PUT/GET (the disk record I/O) are slice 2.
    'field#1,2 as a$',
    'lset a$="x"',
    'rset b$="y"',
    # GET/PUT random record I/O (slice 2). Single-byte statement tokens GET=$B2,
    # PUT=$B3 (oracle-locked); `#f` + record number crunch to $11+n digit tokens
    # (get#1 -> B2 23 12; put#1,1 -> B3 23 12 2C 12).
    "get#1",
    "put#1,1",
]

# String-engine keywords (repack-only; --zb-machine). Each is a $FF-prefixed function
# token from the same contiguous MSX-BASIC function table as LEN/STR$/VAL; the lean
# build keeps them verbatim ASCII, so they are proven only against the repack build.
# EXPECT is the §4 captured $FF-suffix (docs/spec-basic-string-engine.md) -- the crunch
# is checked BOTH ways: zerobas == VG-8020 reference, and the suffix == the table.
# bload LEADS (freeze at TAPION with the line crunched; the body never executes).
STR_KEYWORDS = [
    ('a=len("ab")',      0x92),   # LEN
    ('a$=left$("hi",1)', 0x81),   # LEFT$
    ('a$=right$("hi",1)',0x82),   # RIGHT$
    ('a$=mid$("hi",1,1)',0x83),   # MID$
    ('a$=chr$(65)',      0x96),   # CHR$
    ('a=asc("a")',       0x95),   # ASC
    ('a$=str$(5)',       0x93),   # STR$
    ('a=val("5")',       0x94),   # VAL
    # string-functions slice (spec-basic-string-functions.md §4, S2-locked):
    # HEX$/OCT$/SPACE$ are $FF-prefixed function tokens, same table as above.
    ('a$=hex$(255)',     0x9B),   # HEX$
    ('a$=oct$(8)',       0x9A),   # OCT$
    ('a$=space$(3)',     0x99),   # SPACE$
]

# string-functions slice, the other half: STRING$ ($E3) and INSTR ($E5) are
# SINGLE-BYTE reserved-word tokens (spec §4), NOT $FF-prefixed -- they don't
# arrive through the $FF function table, so the STR_KEYWORDS suffix checker
# (which looks for FF <suffix>) does not apply. Checked as bare token bytes
# instead (same crunch byte-identity assertion vs the VG-8020 reference).
STR_KEYWORDS_1B = [
    ('a$=string$(3,65)', 0xE3),   # STRING$
    ('a=instr("ab","b")',0xE5),   # INSTR
    # INKEY$ slice: single-byte reserved word $EC, the '$' PART of the keyword
    # (S2 capture: `a$=inkey$` -> 41 24 EF EC, no separate $24). No args.
    ('a$=inkey$',        0xEC),   # INKEY$
    # Audio slice 1: SOUND is a single-byte STATEMENT token $C4 (docs/spec-basic-
    # audio-play.md; VG-8020 capture `sound 1,255` -> C4 20 12 2C 0F FF 00). The
    # lean build keeps "SOUND" verbatim ASCII, so this is proven repack-only.
    ('sound 1,255',      0xC4),   # SOUND
    # Audio slice 2a: PLAY is a single-byte STATEMENT token $C1 (docs/spec-basic-
    # audio-play-slice2a.md; VG-8020 capture). Lean keeps "PLAY" verbatim ASCII, so
    # like SOUND this crunch is proven repack-only.
    ('play"cde"',        0xC1),   # PLAY
    # Audio close-out: BEEP is a single-byte STATEMENT token $C0, no arguments
    # (docs/spec-basic-audio-beep.md; VG-8020 capture `beep` -> C0 00, `beep:beep`
    # -> C0 3A C0 00). Lean keeps "BEEP" verbatim ASCII, so proven repack-only.
    ('beep',             0xC0),   # BEEP (no args)
    ('beep:beep',        0xC0),   # BEEP chained -> C0 3A C0
]


def tokens(raw: str | None) -> bytes | None:
    """Body tokens (up to and including the 0x00 terminator) from a stored_line
    capture: the bytes after the 4-byte header (link + line number). None when
    the line was NOT stored -- a crunch that errored on entry leaves the program
    empty, so ("stored_line", …) captures "" (link == 00 00). The link-pointer
    extraction gives the line's exact extent, so an embedded 0x00 in a value byte
    (a=256 -> 1C 00 01, goto 40 -> 0E 28 00) is INSIDE the tokens, never a false
    terminator."""
    if not raw:
        return None
    b = bytes.fromhex(raw)
    return b[4:] if len(b) >= 5 else None


def _capture(machine: str, specs, *, cart: str | None, batch: bool):
    return omsx_repl.run_cases(machine, specs, batch=batch, reset=("NEW",),
                               capture=("stored_line", TXTTAB), cart=cart)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE,
                    help="reference machine (built-in BASIC oracle; default VG-8020)")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--cart", help="lean zerobas basic.rom (cartridge on --machine)")
    grp.add_argument("--zb-machine", dest="zb_machine",
                     help="repack machine with BASIC baked into slot 0 (no cart); "
                          "runs the string-engine keywords")
    ap.add_argument("--full", action="store_true",
                    help="repack mode: also re-run the full LINES+CRUNCH_ONLY corpus on "
                         "the repack build (the exhaustive relocated-kwtable proof). "
                         "Default repack run is just the string keywords.")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot instead of the default "
                         "single-boot batch (to rule out inter-case leakage)")
    args = ap.parse_args()

    # Assemble the corpus: (body, expect_suffix, expect_token). Every body is the
    # stored line `1 <body>`; nothing executes, so LINES and CRUNCH_ONLY need no
    # distinct handling. The full corpus runs on the lean cart always; on the
    # repack build only with --full (its cases are the relocated-kwtable proof,
    # not the gate). The string keywords run repack-only (the lean build keeps
    # them verbatim ASCII, so only the repack build can crunch them).
    tests: list[tuple[str, int | None, int | None]] = []
    if not args.zb_machine or args.full:
        tests += [(body, None, None) for body in LINES + CRUNCH_ONLY]
    if args.zb_machine:
        tests += [(body, suf, None) for body, suf in STR_KEYWORDS]
        tests += [(body, None, tok) for body, tok in STR_KEYWORDS_1B]

    specs = [("direct", [f"1 {body}"]) for body, _, _ in tests]
    batch = not args.boot_per_case

    ref_raws = _capture(args.machine, specs, cart=None, batch=batch)
    if args.zb_machine:
        zb_raws = _capture(args.zb_machine, specs, cart=None, batch=batch)
    else:
        zb_raws = _capture(args.machine, specs, cart=args.cart, batch=batch)

    ok = True
    for (body, expect_suffix, expect_token), ref_raw, zb_raw in zip(
            tests, ref_raws, zb_raws):
        ref, zb = tokens(ref_raw), tokens(zb_raw)
        same = ref is not None and zb is not None and ref == zb
        # For the string keywords also lock the observed FF-suffix / single-byte
        # token to the §4 table, so the gate stands even if the reference happened
        # to agree by accident.
        note = ""
        if expect_suffix is not None:
            got = zb[zb.index(0xFF) + 1] if zb and 0xFF in zb else None
            suffix_ok = got == expect_suffix
            same = same and suffix_ok
            note = (f"  [FF {expect_suffix:02X} ok]" if suffix_ok
                    else f"  [want FF {expect_suffix:02X}, got "
                         f"{('FF %02X' % got) if got is not None else 'none'}]")
        if expect_token is not None:
            token_ok = zb is not None and expect_token in zb
            same = same and token_ok
            note = (f"  [{expect_token:02X} ok]" if token_ok
                    else f"  [want token {expect_token:02X}, not found]")
        ok = ok and same
        rs = " ".join(f"{b:02X}" for b in ref) if ref else "<not stored>"
        zs = " ".join(f"{b:02X}" for b in zb) if zb else "<not stored>"
        print(f"{'PASS' if same else 'FAIL'}  {body}{note}")
        print(f"        ref: {rs}")
        if not same:
            print(f"        zb : {zs}")

    print("\nALL PASS — crunch is byte-identical" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
