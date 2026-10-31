# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""`; z80flow:` markers in a pasmo source: where each lands, and when it must refuse."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from z80flow import annotate, inline  # noqa: E402
from z80flow.annotate import EXT_READS  # noqa: E402
from z80flow.decode import m  # noqa: E402
from z80flow.program import Program  # noqa: E402

# f: ld a,1 / push bc / ret        g: ld hl,0 / jp (hl)
CODE = "3E01 C5 C9 210000 E9"
SYMS = {"f": 0x1000, "g": 0x1004, "CELL": 0xF000}

MAIN = """\
; f's header
f:      ld      a,1
        push    bc
        ; the caller pops it
        ; z80flow: depth 2
        ret
; g jumps to code the user loaded
g:                              ; z80flow: inline
        ld      hl,0
        jp      (hl)            ; user code: z80flow: targets external reads=HL
CELL    equ     $F000           ; an SP anchor: z80flow: stack-anchor unwind
"""


def setup(files, code=CODE, syms=SYMS):
    p = Program("t")
    p.add_image(0x1000, bytes.fromhex(code.replace(" ", "")), "t")
    for n, v in syms.items():
        if v < 0x8000:
            p.add_label(v, n)
    p.byname = dict(syms)
    img = inline.Image("main", "main.asm", [], syms, lambda v: 0 if v < 0x8000 else None, lambda c: "")
    A = annotate.Annotations()
    inline.resolve("/src", [img], p, A, read=lambda root, rel: files.get(rel))
    return p, A


def by_kind(A, k):
    return [e for e in A.entries if e.kind == k]


class TestPlacement(unittest.TestCase):
    def test_every_form_lands(self):
        p, A = setup({"main.asm": MAIN})
        self.assertEqual(A.errors, [])
        d, = by_kind(A, "depth")              # on a comment line: the next instruction
        self.assertEqual((d.addr, d.value, d.where, d.line), (0x1003, 2, "f+3", "main.asm:5"))
        self.assertIn("the caller pops it", d.why)
        i, = by_kind(A, "inline")             # on a label line: the routine
        self.assertEqual(i.addr, 0x1004)
        t, = by_kind(A, "targets")            # trailing on the instruction
        self.assertEqual(t.addr, 0x1007)
        self.assertEqual(t.value, [EXT_READS - m("H", "L")])
        self.assertIn("user code", t.why)
        c, = by_kind(A, "stack-anchor")       # on an equ line: the cell it defines
        self.assertEqual((c.addr, c.value), (0xF000, True))

    def test_include_followed(self):
        files = {"main.asm": '        include "more.inc"\n',
                 "more.inc": MAIN}
        p, A = setup(files)
        self.assertEqual(A.errors, [])
        self.assertEqual(len(A.entries), 4)

    def test_stacked_markers_share_the_reason(self):
        src = MAIN.replace("        ; z80flow: depth 2\n",
                           "        ; z80flow: depth 2\n        ; z80flow: return\n")
        p, A = setup({"main.asm": src})
        self.assertEqual(A.errors, [])
        r, = by_kind(A, "return")
        self.assertEqual(r.addr, 0x1003)
        self.assertIn("the caller pops it", r.why)


class TestRefusals(unittest.TestCase):
    def errors(self, src):
        p, A = setup({"main.asm": src})
        return [msg for _, msg in A.errors]

    def test_source_out_of_step_with_build(self):
        # the source says pop where the image has push: never a guess
        es = self.errors(MAIN.replace("push    bc", "pop     bc"))
        self.assertTrue(any("source says `pop`" in x for x in es), es)

    def test_data_between_label_and_site(self):
        es = self.errors(MAIN.replace("        push    bc\n", "        db      $C5\n"))
        self.assertTrue(any("put a label closer" in x for x in es), es)

    def test_no_justification(self):
        es = self.errors(MAIN.replace("        ; the caller pops it\n", ""))
        self.assertTrue(any("no justification" in x for x in es), es)

    def test_marker_whose_label_no_image_has(self):
        es = self.errors(MAIN.replace("g:  ", "h:  "))
        self.assertTrue(any("in no analysed image" in x for x in es), es)

    def test_marker_with_nothing_below(self):
        es = self.errors(MAIN + "; why\n; z80flow: inline\n\n")
        self.assertTrue(any("no code line below" in x for x in es), es)


class TestContexts(unittest.TestCase):
    def test_own_names_qualified(self):
        """A file of another image: WHERE and the image's own names in the
        arguments get its context, a RAM name does not."""
        p = Program("t")
        p.add_image(0x1000, bytes.fromhex(CODE), "t")
        p.add_context(1, "sub", {0: (bytes.fromhex(CODE), -0x1000, "sub")})
        for n, v in SYMS.items():
            if v < 0x8000:
                p.add_label(1 << 16 | v, n)
        p.byname = {"HOOK": 0xF000, "CELL": 0xF000}
        syms = dict(SYMS, HOOK=0xF000)
        src = MAIN.replace("targets external reads=HL", "targets f HOOK")
        img = inline.Image("sub", "main.asm", [], syms, lambda v: 1 if v < 0x8000 else None, lambda c: "sub")
        A = annotate.Annotations()
        inline.resolve("/src", [img], p, A, read=lambda root, rel: {"main.asm": src}.get(rel))
        self.assertEqual(A.errors, [])
        t, = by_kind(A, "targets")
        self.assertEqual(t.where, "sub:g+3")
        self.assertEqual(t.addr, 1 << 16 | 0x1007)
        self.assertEqual(t.value, [1 << 16 | 0x1000, 0xF000])


class TestLineSyntax(unittest.TestCase):
    def test_semicolon_in_quotes_and_af_prime(self):
        self.assertEqual(inline.split_comment("  db ';'  ; c"), ("  db ';'  ", " c"))
        self.assertEqual(inline.split_comment("  ex af,af'  ; c"), ("  ex af,af'  ", " c"))

    def test_label_forms(self):
        self.assertEqual(inline.parse_code("lab:  ld a,1"), ("lab", "ld", "a,1"))
        self.assertEqual(inline.parse_code("NAME equ $10"), ("NAME", "equ", "$10"))
        self.assertEqual(inline.parse_code("    ret"), (None, "ret", ""))


if __name__ == "__main__":
    unittest.main()
