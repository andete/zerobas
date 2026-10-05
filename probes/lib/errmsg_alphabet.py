# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""errmsg_alphabet — the error messages this ROM can print, DERIVED not typed.

🔴 A HAND-WRITTEN ERROR-MESSAGE ALPHABET IS A BLIND SPOT, AND 19 PROBES CARRY
ONE (TODO.md, filed 2026-09-02 by D-LSETTM). A probe classifies a screen against
a literal list; anything absent reads `<NO OUTPUT>`, which routes to *"without a
reference"* — **a sentence about the MACHINE for a fault in the PROBE**. It has
cost real readings twice in the recorded history:

  * `Missing operand` (ERR 24) was missing from three separate alphabets and had
    to be added by hand each time; rows read `<NO OUTPUT>` while BOTH machines
    had printed a perfectly good message.
  * four probes said `Field overflow` where the ROM says **`FIELD overflow`** —
    a message they DID name, spelled so it could never match.

The second one is the reason "just add the next name" is not the fix: a list can
be wrong about an entry it already has, and no row provokes most of these, so the
error is latent until the day it matters.

## What this derives, and from what

The ROM's own source, so the alphabet cannot drift from the machine:

  * `sub/errmsg.asm` — the sub-ROM tenant. Plain `db "...",0` bodies.
  * the main ROM's message strings. These WERE escape-encoded (D-MSGENC:
    `db "Subscript o",MSGESC_UTOF,"range",0`); DT-6 (space plan B-9, 2026-10-05) retired the phrase
    table, and every main string is plain `db "...",0` again. The phrase parser
    below is KEPT and now reads an EMPTY table (no `MSGESC_<NAME> equ n ; "..."`
    line is left in `basic/sysvars.inc`; `MSGESC_SUB`, the one escape that
    remains, carries no spelling and is not a phrase). So a body that still used
    a retired escape would be DROPPED, not half-expanded -- the same refusal as
    before, and the right one.

⚠️ (History.) The escapes dropped a leading letter on purpose -- `MSGESC_UTOF`
was `"ut of "`, so `"O",MSGESC_UTOF,"memory"` and a lowercase `"o"` shared one
table entry. A decoder that "helpfully" restored the letter would have produced
two plausible strings neither of which the machine printed.

## Using it

    import errmsg_alphabet
    errmsg_alphabet.MESSAGES          # tuple, longest-first
    errmsg_alphabet.classify(text)    # "<Type mismatch>" | "<UNREADABLE: ...>"
                                      # | "" when the screen is genuinely blank

🎯 `classify()` NEVER RETURNS `<NO OUTPUT>` FOR A SCREEN THAT HAD TEXT. An
unclassifiable non-empty screen comes back as `<UNREADABLE: ...>` carrying the
text — deliberately not a sentinel, so a gate scores it RED instead of routing it
to "no reference" [[an-unnamed-outcome-reads-as-no-outcome]].
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ESC = re.compile(r"^(MSGESC_[A-Z]+)\s+equ\s+(\d+)\s*;\s*\"(.*?)\"", re.M)
# A `db` body: a comma-separated list of "strings", numbers and MSGESC_ names.
_DB = re.compile(r"^\s*(?:([A-Za-z_][\w.]*)\s*:)?\s*db\s+(.+?)\s*(?:;.*)?$", re.M)
_PIECE = re.compile(r'"((?:[^"]|"")*)"|(MSGESC_[A-Z]+)|(\$?[0-9A-Fa-f]+)')


def _phrases(path=None):
    """MSGESC_* -> its expansion, read from the comment that defines it.

    The spelling lives in exactly one place in the tree (the `; \"ut of \"`
    comment beside the equ) and this reads THAT, rather than a second copy here.
    """
    src = open(path or os.path.join(ROOT, "basic", "sysvars.inc"),
               encoding="utf-8", errors="replace").read()
    return {m.group(1): m.group(3) for m in _ESC.finditer(src)}


def _strings(path, phrases):
    """Every NUL-terminated `db` body in one file, escapes expanded.

    Bodies that use an escape this table does not define are DROPPED rather than
    half-expanded: a half-expanded string is a plausible answer that the machine
    never prints, which is the failure mode this module exists to stop.
    """
    out = []
    src = open(path, encoding="utf-8", errors="replace").read()
    for m in _DB.finditer(src):
        body, ok, terminated = [], True, False
        for p in _PIECE.finditer(m.group(2)):
            lit, esc, num = p.group(1), p.group(2), p.group(3)
            if lit is not None:
                body.append(lit.replace('""', '"'))
            elif esc is not None:
                if esc not in phrases:
                    ok = False
                    break
                body.append(phrases[esc])
            elif num is not None:
                terminated = num in ("0", "$00", "00")
        s = "".join(body)
        # What counts as a MESSAGE, each clause carrying its own reason:
        #  * terminated -- a `db` with no NUL is a fragment or a fixed field
        #    (`db "ZEROBAS "`, `db "AB"`), not a printed string;
        #  * an interior space and a lowercase letter -- excludes `db "CAS:",0`,
        #    `db "RUN",0` and `db "AUTOEXECBAS"`;
        #  * \U0001f534 s == s.strip() -- excludes the PREFIXES that get a number
        #    appended (`db "Undefined line ",0`, `db " in ",0`). A prefix in the
        #    alphabet would match a longer real message's screen and name the row
        #    after the fragment;
        #  * not a phrase expansion -- `msg_phrase_tab` stores `" error"`,
        #    `"ut of "` and `"llegal function call"` as `db` strings of its own,
        #    and `" error"` in the alphabet would classify ANY screen containing
        #    those six characters as an error called " error".
        # \u26a0\ufe0f `Break` IS DELIBERATELY OUT: it is not an error message and no
        # ERRFLG names it -- probes read it through omsx_repl.is_break().
        if not (ok and terminated and " " in s and re.search(r"[a-z]", s)):
            continue
        if s != s.strip() or s in phrases.values():
            continue
        out.append(s)
    return out


def _derive():
    ph = _phrases()
    seen, out = set(), []
    for rel in ("sub/errmsg.asm", "basic/arrays.asm", "basic/str-engine.asm",
                "basic/interp.asm", "basic/cload.asm", "basic/program.asm",
                "basic/missing.asm"):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        for s in _strings(p, ph):
            if s not in seen:
                seen.add(s)
                out.append(s)
    # Longest first: `File not found` must win over any shorter substring of it,
    # and `Out of string space` over `Out of memory`'s prefix-sharing neighbours.
    return tuple(sorted(out, key=len, reverse=True))


MESSAGES = _derive()
PHRASES = _phrases()


def classify(txt: str) -> str:
    """`<Name>` for a message this ROM can print, `<UNREADABLE: ...>` for text it
    cannot name, `""` for a genuinely blank screen."""
    for e in MESSAGES:
        if e in txt:
            return f"<{e}>"
    rest = txt.replace("Ok", "").strip()
    return f"<UNREADABLE: {rest[:48]}>" if rest else ""


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        bad = 0
        # Known-answer arms, hand-verified against the ROM source. Each is a
        # string the machine PRINTS, so a derivation that misses one is red.
        for want in ("Syntax error", "Type mismatch", "Subscript out of range",
                     "Out of memory", "Out of string space", "FIELD overflow",
                     "Missing operand", "Illegal function call",
                     "Undefined user function", "String formula too complex",
                     "Line buffer overflow", "Unprintable error"):
            if want not in MESSAGES:
                print(f"  FAIL  derived alphabet is missing {want!r}")
                bad += 1
        # 🔴 THE CASING ARM. Four probes shipped `Field overflow`; the ROM says
        # `FIELD overflow`. A derivation that lowercased would pass every arm
        # above and reintroduce exactly the defect this replaces.
        if "Field overflow" in MESSAGES:
            print("  FAIL  `Field overflow` is not what the ROM says")
            bad += 1
        # A half-expanded escape must never appear.
        for m in MESSAGES:
            if "MSGESC" in m or any(c for c in m if ord(c) < 0x20):
                print(f"  FAIL  {m!r} is not a decoded message")
                bad += 1
        if classify("") != "":
            print("  FAIL  a blank screen must classify as empty")
            bad += 1
        if not classify("Nonsense here").startswith("<UNREADABLE"):
            print("  FAIL  unnameable text must be UNREADABLE, never a sentinel")
            bad += 1
        if classify("Ok") != "":
            print("  FAIL  a bare prompt is a blank screen")
            bad += 1
        print(f"{len(MESSAGES)} message(s) derived; "
              f"{'0 failures' if not bad else f'{bad} FAILURE(S)'}")
        raise SystemExit(1 if bad else 0)
    for m in MESSAGES:
        print(m)
