# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Core analysis on tiny hand-assembled programs (no platform adapter)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from z80flow.analysis import Analysis  # noqa: E402
from z80flow.decode import m, fmt_units, REAL  # noqa: E402
from z80flow.program import FarCall, Opaque, Program  # noqa: E402
from z80flow import annotate  # noqa: E402


def prog(code_hex, roots, ann=None, setup=None):
    p = Program("t")
    b = bytes.fromhex(code_hex.replace(" ", ""))
    p.add_image(0x1000, b, "t")
    p.code_ranges = [(0x1000, 0x1000 + len(b) - 1)]
    for a, n in roots.items():
        p.roots[a] = n
        p.add_label(a, n)
    if setup:
        setup(p)
    if ann is not None:
        p.annotations = annotate.loads(ann, p)
        assert not p.annotations.errors, p.annotations.errors
    return Analysis(p).run()


def exit_keys(A, e):
    """A routine's exits as (level, x, k, delta), the flags they fix left out."""
    return sorted({k[:4] for k in A.frec[e]["exits"]})


def reasons(A, e):
    return sorted({k for k, _, _ in A.direct[e]})


class TestCore(unittest.TestCase):
    def test_push_pop_preserves(self):
        # 1000: push hl / ld hl,5 / ld a,l / pop hl / ret     ; preserves HL, A = 5
        A = prog("E5 210500 7D E1 C9", {0x1000: "f"})
        c = A.contract(0x1000)
        self.assertEqual(fmt_units(c["inputs"]), "-")        # HL saved, not an input
        self.assertEqual(fmt_units(c["clobbers"]), "A")
        self.assertEqual(A.status[0x1000], "inferred")

    def test_inline_skip_inferred(self):
        # 1000: call 1008 / db $AA / ld a,b / ret
        # 1006: (pad) nop nop
        # 1008: ex (sp),hl / inc hl / ex (sp),hl / ret          ; skips one inline byte
        A = prog("CD0810 AA 78 C9 00 00 E3 23 E3 C9", {0x1000: "main", 0x1008: "skip1"})
        self.assertEqual(A.kmap.get(0x1008), 1)
        self.assertIn(0x1004, A.code)          # decoding resumed after the db
        self.assertNotIn(0x1003, A.code)       # the db byte is not decoded
        c = A.contract(0x1008)
        self.assertEqual(fmt_units(c["clobbers"]), "-")      # HL restored by the 2nd ex (sp)
        self.assertEqual(A.status[0x1000], "inferred")

    def test_exx_swap_is_exact(self):
        # 1000: exx / ld b,1 / exx / ret   ; clobbers B' only
        A = prog("D9 0601 D9 C9", {0x1000: "f"})
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "B'")

    def test_return_to_callers_caller_is_an_exit(self):
        # 1000: pop hl / ret   ; returns to the caller's caller: a level-1 exit
        A = prog("E1 C9", {0x1000: "f"})
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(exit_keys(A, 0x1000), [(1, 0, 0, 0)])
        self.assertEqual(A.stack_conventions(0x1000), ["exits to the caller's caller"])

    def test_jp_hl_unresolved(self):
        A = prog("2A0080 E9", {0x1000: "f"})
        self.assertTrue(any(k == "jpind-unresolved" for k, _, _ in A.direct[0x1000]))

    def test_used_outputs(self):
        # main: call g / ld a,h / ld bc,0 / ld hl,0 / ret  ; only H of g's output is read
        # g (at main+11): ld hl,1 / ld bc,2 / ret          ; writes HL and BC
        # (main has no caller, so everything is live at ITS exit -- hence the kills)
        A = prog("CD0B10 7C 010000 210000 C9 210100 010200 C9", {0x1000: "main", 0x100B: "g"})
        c = A.contract(0x100B)
        self.assertEqual(fmt_units(c["clobbers"]), "BC HL")
        self.assertEqual(fmt_units(c["outputs_used"]), "H")



class TestExits(unittest.TestCase):
    def test_callers_caller_exit_becomes_callers_return(self):
        # 1000 main: call f / ld a,1 / ret      ; f never comes back here
        # 1006 f:    pop hl / ret
        A = prog("CD0610 3E01 C9 E1 C9", {0x1000: "main", 0x1006: "f"})
        self.assertNotIn(0x1003, A.code)                 # dead after the call
        self.assertEqual(exit_keys(A, 0x1000), [(0, 0, 0, 0)])
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "HL")

    def test_callee_pushes_a_frame_for_its_caller(self):
        # 1000 main: call f / pop de / ret      ; DE := the BC that f pushed
        # 1005 f:    pop hl / push bc / jp (hl) ; returns leaving +2
        A = prog("CD0510 D1 C9 E1 C5 E9", {0x1000: "main", 0x1005: "f"})
        self.assertEqual(exit_keys(A, 0x1005), [(0, 0, 0, 2)])
        self.assertEqual(A.status[0x1000], "inferred")
        out = A.frec[0x1000]["exits"][(0, 0, 0, 0)]["out"]
        from z80flow.decode import U
        self.assertEqual(out[U["D"]], ("o", U["B"]))      # tracked through the frame
        self.assertEqual(out[U["E"]], ("o", U["C"]))
        c = A.contract(0x1000)
        self.assertEqual(fmt_units(c["inputs"]), "BC")    # the slot is read
        self.assertEqual(fmt_units(c["clobbers"]), "DE HL")

    def test_callee_consumes_callers_slot(self):
        # 1000 main: push bc / call f / ret     ; f eats the pushed BC
        # 1005 f:    pop hl / pop de / jp (hl)  ; delta -2
        A = prog("C5 CD0510 C9 E1 D1 E9", {0x1000: "main", 0x1005: "f"})
        self.assertEqual(exit_keys(A, 0x1005), [(0, 0, 0, -2)])
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "DE HL")

    def test_tail_from_below_the_frame(self):
        # 1000 f: pop hl / jp g     ; g's ret then returns to f's caller's caller
        # 1004 g: ret
        A = prog("E1 C30410 C9", {0x1000: "f", 0x1004: "g"})
        self.assertEqual(exit_keys(A, 0x1000), [(1, 0, 0, 0)])
        self.assertEqual(A.status[0x1000], "inferred")

    def test_events_only_from_converged_states(self):
        # 1000 f: ld b,3 / l: push af / djnz l / ret
        # the first visit of `ret` sees depth 2; only the converged unknown
        # depth may be reported
        A = prog("0603 F5 10FD C9", {0x1000: "f"})
        kinds = {k for k, _, _ in A.frec[0x1000]["events"]}
        self.assertIn("ret-unknown-depth", kinds)
        self.assertNotIn("ret-push-jump", kinds)


class TestValues(unittest.TestCase):
    def test_inc_dec_pair_is_net_zero(self):
        # inc b / dec b / ret : B unchanged, flags clobbered
        A = prog("04 05 C9", {0x1000: "f"})
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "F(S,Z,H,PV,N)")
        # inc hl / inc hl / dec hl / dec hl / ret
        A = prog("23 23 2B 2B C9", {0x1000: "f"})
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "-")
        # or a / and a / ret : A unchanged
        A = prog("B7 A7 C9", {0x1000: "f"})
        self.assertNotIn("A", fmt_units(A.contract(0x1000)["clobbers"]))
        # inc b / ret : still a clobber
        A = prog("04 C9", {0x1000: "f"})
        self.assertIn("B", fmt_units(A.contract(0x1000)["clobbers"]))

    def test_stack_frame_by_sp_arithmetic(self):
        # ld hl,-6 / add hl,sp / ld sp,hl / ld hl,6 / add hl,sp / ld sp,hl / ret
        A = prog("21FAFF 39 F9 210600 39 F9 C9", {0x1000: "f"})
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(exit_keys(A, 0x1000), [(0, 0, 0, 0)])
        # releasing one word too many: returns to the caller's caller
        A = prog("21FAFF 39 F9 210800 39 F9 C9", {0x1000: "f"})
        self.assertEqual(exit_keys(A, 0x1000), [(1, 0, 0, 0)])

    def test_constant_jp_hl_is_followed(self):
        # 1000 f: ld hl,1005 / jp (hl) ; 1005 g: ret
        A = prog("210510 E9 00 C9", {0x1000: "f"})
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertTrue(any(k == "jpind-const" for k, _, _ in A.frec[0x1000]["events"]))

    def test_pair_constants_merge_jointly(self):
        # or a / jr z,L / ld hl,$1234 / jr J / L: ld hl,$5678 / J: jp (hl)
        # targets: $1234 and $5678 only, not $1278 / $5634 as well
        A = prog("B7 2805 213412 1803 217856 E9", {0x1000: "f"})
        d = [d for k, a, d in A.frec[0x1000]["events"] if k == "jpind-const"]
        self.assertEqual(d, ["jp (hl) with HL = $1234/$5678"])

    def test_push_then_ret_constant(self):
        # 1000 f: ld hl,1006 / push hl / ret ; 1006 g: ld a,1 / ret
        A = prog("210610 E5 C9 00 3E01 C9", {0x1000: "f"})
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "HL A")


class TestAnnotations(unittest.TestCase):
    # 1000 f: ld a,(8000) / ld l,a / ld h,0 / jp (hl)   -> one of two handlers
    # 1007 h1: ld b,1 / ret
    # 100A h2: ld c,2 / ret
    # 100D tab: dw h1, h2
    DISPATCH = "3A0080 6F 2600 E9 0601 C9 0E02 C9 0710 0A10"

    def test_targets(self):
        ann = "# the two handlers\ntargets f+6 h1 h2\n"
        A = prog(self.DISPATCH, {0x1000: "f", 0x1007: "h1", 0x100A: "h2", 0x100D: "tab"}, ann)
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "BC HL A")
        e = A.p.annotations.targets[0x1006][0]
        # the targets decode as code, which is a sanity check, not evidence
        # that the dispatch goes there
        self.assertEqual(e.verdict(), "trusted")

    def test_table(self):
        ann = "# the table\ntable f+6 tab 2\n"
        A = prog(self.DISPATCH, {0x1000: "f", 0x100D: "tab"}, ann)
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(A.entries.get(0x1007), "dispatch target")

    def test_unannotated_dispatch_is_unknown(self):
        A = prog(self.DISPATCH, {0x1000: "f"})
        self.assertEqual(reasons(A, 0x1000), ["jpind-unresolved"])

    def test_noreturn_routine(self):
        # 1000 main: call err / db $FF / ...   1004: (data)  1005 err: jp (ix)
        # without the annotation the tool decodes $FF after the call
        code = "CD0510 FF 00 DDE9"
        A = prog(code, {0x1000: "main", 0x1005: "err"})
        self.assertIn(0x1003, A.code)
        A = prog(code, {0x1000: "main", 0x1005: "err"}, "# err: halt loop\nnoreturn err\n")
        self.assertNotIn(0x1003, A.code)
        # err ends in an unresolved jp (ix): nothing to check the claim against
        self.assertEqual(A.p.annotations.noreturn[0x1005].verdict(), "trusted")

    def test_noreturn_inferred(self):
        # err ends in ld sp,nn / jp: a frame reset; calls to it end the path
        # 1000 main: call err / db $FF   1004 err: ld sp,0 / jp 1004
        A = prog("CD0410 FF 310000 C30410", {0x1000: "main", 0x1004: "err"})
        self.assertNotIn(0x1003, A.code)

    def test_noreturn_mismatch(self):
        A = prog("C9", {0x1000: "f"}, "# wrong on purpose\nnoreturn f\n")
        self.assertEqual(A.p.annotations.noreturn[0x1000].verdict(), "MISMATCH")
        self.assertIn("annotation-mismatch", reasons(A, 0x1000))

    def test_depth_on_a_data_dependent_loop(self):
        # 1000 f: push af(sentinel) / l: call g / push af / djnz l /
        #         m: pop af / cp $FF / jr nz,m / ret      1009..: g: ret
        code = "F5 CD0D10 F5 10FA F1 FEFF 20FB C9 C9"
        A = prog(code, {0x1000: "f", 0x100D: "g"})
        self.assertEqual(reasons(A, 0x1000), ["ret-unknown-depth"])
        A = prog(code, {0x1000: "f", 0x100D: "g"}, "# the pops end at the sentinel\ndepth f+12 0\n")
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(A.p.annotations.depth[0x100C][0].verdict(), "trusted")

    def test_depth_mismatch(self):
        A = prog("C5 C1 C9", {0x1000: "f"}, "# wrong\ndepth f+2 2\n")
        self.assertIn("annotation-mismatch", reasons(A, 0x1000))

    def test_returns_to_callers_caller_annotation(self):
        # f: ld b,3 / l: push af / djnz l / ret  -- declared: back through the caller's slot
        A = prog("0603 F5 10FD C9", {0x1000: "f"}, "# declared\nreturns-to-callers-caller f+5\n")
        self.assertEqual(exit_keys(A, 0x1000), [(1, 0, 0, 0)])
        self.assertEqual(A.status[0x1000], "inferred")

    def test_stack_effect_var(self):
        # 1000 main: call g / ld a,1 / ret     (depth unknown after g; main's ret then too)
        # 1006 g: pop hl / ld b,3 / l: push af / djnz l / jp (hl)
        code = "CD0610 3E01 C9 E1 0603 F5 10FD E9"
        A = prog(code, {0x1000: "main", 0x1006: "g"})
        self.assertIn("jpind-return-unknown-depth", reasons(A, 0x1006))
        ann = "# g leaves its digits pushed\nstack-effect g var\n# main\ndepth main+5 0\n"
        A = prog(code, {0x1000: "main", 0x1006: "g"}, ann)
        self.assertEqual(A.status[0x1006], "inferred")
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(A.stack_conventions(0x1006), ["returns, SP variable"])

    def test_stack_effect_checked(self):
        A = prog("E1 C5 E9", {0x1000: "f"}, "# f pushes BC for its caller\nstack-effect f +2\n")
        self.assertEqual(A.p.annotations.stack_effect[0x1000].verdict(), "checked")
        A = prog("E1 C5 E9", {0x1000: "f"}, "# wrong\nstack-effect f +4\n")
        self.assertIn("annotation-mismatch", reasons(A, 0x1000))

    def test_abort_site(self):
        # 1000 f: or a / jr z,ok / ld hl,(8000) / jp (hl)  ; error exit through a vector
        # 1007 ok: ret
        code = "B7 2804 2A0080 E9 C9"
        A = prog(code, {0x1000: "f"})
        self.assertEqual(reasons(A, 0x1000), ["jpind-unresolved"])
        A = prog(code, {0x1000: "f"}, "# the error vector never returns\nabort f+6 reads=E\n")
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(fmt_units(A.contract(0x1000)["inputs"]), "A E")

    def test_same_as_callee(self):
        # 1000 f: jp (ix) (unknowable)   1002 g: ld a,1 / ret
        A = prog("DDE9 3E01 C9", {0x1000: "f", 0x1002: "g"}, "# f only ever reaches g\nsame-as-callee f g\n")
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "A")

    def test_return_through_memory(self):
        # 1000 f: pop hl / ld (8000),hl / ld hl,(8000) / jp (hl)   ; RA via RAM
        code = "E1 220080 2A0080 E9"
        A = prog(code, {0x1000: "f"})
        self.assertEqual(reasons(A, 0x1000), ["jpind-unresolved"])
        A = prog(code, {0x1000: "f"}, "# the RA went through $8000\nreturn f+7\n")
        self.assertEqual(exit_keys(A, 0x1000), [(0, 0, 0, 0)])
        self.assertEqual(A.status[0x1000], "inferred")

    def test_ld_sp_release_and_move(self):
        # 1000 f: push bc / push de / ld hl,(8000) / add hl,sp / ld sp,hl / ret
        # (an amount from memory: a constant one is tracked without help)
        code = "C5 D5 2A0080 39 F9 C9"
        A = prog(code, {0x1000: "f"})
        self.assertEqual(reasons(A, 0x1000), ["ldsp-reg"])
        A = prog(code, {0x1000: "f"}, "# releases both words\nld-sp f+6 0\n")
        self.assertEqual(A.status[0x1000], "inferred")
        # a stack move: ld hl,0 / add hl,sp / ld sp,hl / ret
        A = prog("210000 39 F9 C9", {0x1000: "f"}, "# the stack moved whole\nld-sp f+4 same\n")
        self.assertEqual(A.status[0x1000], "inferred")

    def test_site_annotation_in_qualifier(self):
        # two routines share a ret below the frame; only f's is declared
        # 1000 f: push af / ld b,3 / jr s     1005 g: push af / push af / ld b,3
        # 1009 s: l: push af / djnz l / pop af / ret
        code = "F5 0603 1804 F5 F5 0603 F5 10FD F1 C9"
        ann = "# only f\ndepth $100D 0 in=f\n"
        A = prog(code, {0x1000: "f", 0x1005: "g"}, ann)
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(reasons(A, 0x1005), ["ret-unknown-depth"])

    def test_values_from_a_table(self):
        # 1000 f: ld a,(8000) / ... / jp (hl) with HL = $10 << 8 | a byte of tab
        # 1006 tab: db $0A, $0D ; 100A: ld b,1 / ret ; 100D: ld c,1 / ret
        code = "3A0080 00 00 E9 0A0D 0000 0601 C9 0E01 C9"
        ann = "# HL comes from tab\nvalues f+5 HL tab 2 hi=$10\n"
        A = prog(code, {0x1000: "f", 0x1006: "tab"}, ann)
        self.assertEqual(A.p.annotations.values[0x1005][0].value, ("HL", [0x100A, 0x100D]))
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "BC HL A")

    def test_external_with_documented_inputs(self):
        # 1000 f: ld hl,(8000) / jp (hl)   -- user code; documented to read HL only
        code = "2A0080 E9"
        A = prog(code, {0x1000: "f"}, "# user code\ntargets f+3 external\n")
        self.assertEqual(A.status[0x1000], "conservative-boundary")
        self.assertEqual(fmt_units(A.contract(0x1000)["inputs"] & m("B", "C")), "BC")
        A = prog(code, {0x1000: "f"}, "# user code, gets HL\ntargets f+3 external reads=HL\n")
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertEqual(fmt_units(A.contract(0x1000)["inputs"]), "-")          # HL is set here
        self.assertIn("BC", fmt_units(A.contract(0x1000)["clobbers"]))         # still may change anything

    def test_missing_justification_is_an_error(self):
        p = Program("t")
        p.add_label(0x1000, "f")
        a = annotate.loads("noreturn f\n", p)
        self.assertEqual(len(a.errors), 1)


class TestBoundaries(unittest.TestCase):
    def test_ram_flags_not_kind_strings(self):
        def setup(p):
            p.ram_ranges = [(0x8000, 0xFFFF)]
            p.opaque[0x9000] = Opaque("hook", "whatever", in_ram=True, patch_point=True)
            # a declared RAM routine (not a patch point) is a declared boundary too
            p.opaque[0x9200] = Opaque("prim", "whatever", in_ram=True)
        # call 9000 (patch point) / call 9100 (plain RAM) / call 9200 (declared) / ret
        A = prog("CD0090 CD0091 CD0092 C9", {0x1000: "f"}, setup=setup)
        ev = [(k, a) for k, a, _ in A.direct[0x1000]]
        self.assertEqual(ev, [("call-into-ram", 0x1003)])

    def test_hook_policy(self):
        from z80flow import platform_msx
        from z80flow.program import coarse
        pr = platform_msx.hook_factory("practice")
        self.assertTrue(coarse(pr(0xFD9F)))          # H_TIMI: patched in practice
        self.assertTrue(coarse(pr(0xFDA0)))          # (any byte of its 5)
        self.assertFalse(coarse(pr(0xFDA4)))         # H_CHPU: its boot `ret`
        self.assertTrue(coarse(platform_msx.hook_factory("open")(0xFDA4)))
        self.assertFalse(coarse(platform_msx.hook_factory("unpatched")(0xFD9F)))

    def test_far_call_target_folded(self):
        def setup(p):
            p.opaque[0x001C] = Opaque("CALSLT", "inter-slot")
            p.far_target_regs[0x001C] = "IX"
        # ld ix,$4010 / call $001C / ld ix,(8000) / call $001C / ret
        A = prog("DD211040 CD1C00 DD2A0080 CD1C00 C9", {0x1000: "f"}, setup=setup)
        self.assertEqual(A.far_sites[0x1004], (0x001C, frozenset({0x4010})))
        self.assertEqual(A.far_sites[0x100B], (0x001C, None))

    def test_opaque_exit_to_callers_caller(self):
        # a declared boundary that pops its "return address" and returns
        # through the slot below (like MSX's CLPRIM, which pops the caller's AF)
        def setup(p):
            p.opaque[0x9000] = Opaque("prim", "x", in_ram=True, exit=(1, 0, 0, 0))
        # 1000 f: ld hl,1008 / push hl / push af / jp 9000   1008: ret
        A = prog("210810 E5 F5 C30090 C9", {0x1000: "f"}, setup=setup)
        self.assertEqual(A.status[0x1000], "conservative-boundary")



class TestReview(unittest.TestCase):
    """Regressions from the 2026-10-31 adversarial review: each was an
    optimistic (unsound) result."""

    def test_callee_rewriting_callers_slot_is_not_hidden(self):
        # f: push bc / call g / pop bc / ret ; g: pop hl / pop de / inc de / push de / push hl / ret
        A = prog("C5 CD0610 C1 C9 E1 D1 13 D5 E5 C9", {0x1000: "f", 0x1006: "g"})
        self.assertNotEqual(A.status[0x1000], "inferred")
        self.assertIn("caller-slot-changed", reasons(A, 0x1006))

    def test_callee_peeking_at_callers_slot(self):
        # f: push bc / call g / pop bc / ld a,d / ret ; g: pop hl / pop de / push de / push hl / ret
        # g reads f's pushed BC into DE and puts it back unchanged: fine, but BC is read
        A = prog("C5 CD0710 C1 7A C9 E1 D1 D5 E5 C9", {0x1000: "f", 0x1007: "g"})
        self.assertEqual(A.status[0x1007], "inferred")
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertIn("BC", fmt_units(A.contract(0x1000)["inputs"]))
        # and an error path that pops the caller's word but never returns is fine too
        # g2: or a / jr z,ok / pop hl / pop de / l: jr l ; ok: ret
        A = prog("C5 CD0710 C1 C9 00 00 B7 2804 E1 D1 18FE C9", {0x1000: "f", 0x1007: "g2"})
        self.assertEqual(A.status[0x1007], "inferred")

    def test_level1_exit_reads_consumed_slot(self):
        # f: push bc / call g / ret ; g: pop hl / pop de / ret  (g returns to f's caller, DE = f's BC)
        A = prog("C5 CD0510 C9 E1 D1 C9", {0x1000: "f", 0x1005: "g"})
        self.assertEqual(fmt_units(A.contract(0x1000)["inputs"] & m("B", "C")), "BC")

    def test_abort_on_conditional_keeps_fallthrough(self):
        # f: or a / jp z,err / ld b,1 / ret ; err: ld hl,(8000) / jp (hl)
        A = prog("B7 CA0810 0601 C9 2A0080 E9", {0x1000: "f", 0x1008: "err"}, "# err never returns\nabort f+1\n")
        self.assertEqual(exit_keys(A, 0x1000), [(0, 0, 0, 0)])
        self.assertIn("B", fmt_units(A.contract(0x1000)["clobbers"]))

    def test_call_to_rejected_root_is_unknown(self):
        # main: call X / ret ; X: ld a,1 / ld b,2 / db DD DD (invalid: X is rejected)
        A = prog("CD0410 C9 3E01 0602 DDDD", {0x1000: "main", 0x1004: "X"})
        self.assertNotEqual(A.status[0x1000], "inferred")

    def test_depth_annotation_inside_inlined_copy(self):
        # main: call stub / ld a,1 / ret ; stub: ld b,3 / l: push af / djnz l / m: pop af / cp $FF / jr nz,m / ret
        A = prog("CD0610 3E01 C9 0603 F5 10FD F1 FEFF 20FB C9", {0x1000: "main", 0x1006: "stub"},
                 "# stub\ninline stub\n# the pops end at the sentinel\ndepth stub+10 0\n")
        self.assertEqual(exit_keys(A, 0x1000), [(0, 0, 0, 0)])
        self.assertIn(0x1003, A.frec[0x1000]["nodes"])

    def test_continuation_reads_what_flows_through(self):
        # f: ld sp,$F000 / jp k ; k: ld a,b / ret  -- B reaches k's exit through A
        A = prog("3100F0 C30610 78 C9", {0x1000: "f"})
        self.assertIn("B", fmt_units(A.contract(0x1000)["inputs"]))
        # abort to a static target that is not an entry: its inputs count
        A = prog("B7 CA0810 0601 C9 0C C9", {0x1000: "f", 0x1008: "err"}, "# abort\nabort f+1\n")
        self.assertIn("C", fmt_units(A.contract(0x1000)["inputs"]))

    def test_abort_without_static_target_reads_everything(self):
        # f: ld hl,(8000) / ld sp,hl / jp k ; k: ld (9000),a / ret -- abort on the ld sp,hl
        A = prog("2A0080 F9 C30710 320090 C9", {0x1000: "f", 0x1007: "k"}, "# abort\nabort f+3\n")
        self.assertIn("A", fmt_units(A.contract(0x1000)["inputs"]))

    def test_vacuous_verdicts_are_not_checked(self):
        # f: ld b,3 / l: push af / djnz l / pop af / ret -- really leaves +4, declared 0
        A = prog("0603 F5 10FD F1 C9", {0x1000: "f"}, "# wrong on purpose\nstack-effect f 0\n")
        self.assertNotEqual(A.p.annotations.stack_effect[0x1000].verdict(), "checked")
        # noreturn on a routine the tool cannot follow
        A = prog("CD0410 FF 2A0080 E9", {0x1000: "main", 0x1004: "err"}, "# err\nnoreturn err\n")
        self.assertNotEqual(A.p.annotations.noreturn[0x1004].verdict(), "checked")

    def test_register_saved_by_inlined_copy_is_not_an_input(self):
        # main: call stub / ret ; stub: push bc / ld b,1 / pop bc / ret  (inlined)
        A = prog("CD0410 C9 C5 0601 C1 C9", {0x1000: "main", 0x1004: "stub"}, "# stub\ninline stub\n")
        self.assertEqual(fmt_units(A.contract(0x1000)["inputs"]), "-")
        self.assertEqual(fmt_units(A.contract(0x1000)["clobbers"]), "-")
        # the same inside a caller frame and with the call at a nonzero depth
        # main: push de / call stub / pop de / ret
        A = prog("D5 CD0610 D1 C9 C5 0601 C1 C9", {0x1000: "main", 0x1006: "stub"}, "# stub\ninline stub\n")
        self.assertEqual(fmt_units(A.contract(0x1000)["inputs"]), "-")
        # a copy that pushes the caller's register and the caller pops it: read
        # main: call stub / pop hl / ld a,(hl) / ret ; stub: pop de / push bc / ex de,hl / jp (hl)
        A = prog("CD0610 E1 7E C9 D1 C5 EB E9", {0x1000: "main", 0x1006: "stub"}, "# stub\ninline stub\n")
        self.assertIn("BC", fmt_units(A.contract(0x1000)["inputs"]))

    def test_jp_hl_through_inlined_return_address(self):
        # main: call stub / ld a,1 / ret ; stub: pop hl / jp (hl)   (inlined)
        A = prog("CD0610 3E01 C9 E1 E9", {0x1000: "main", 0x1006: "stub"}, "# stub\ninline stub\n")
        self.assertEqual(A.status[0x1000], "inferred")
        self.assertIn(0x1003, A.frec[0x1000]["nodes"])


class TestResets(unittest.TestCase):
    # top: call r / jr top ; r: ld ($8000),sp / call stmt / ret
    # stmt: ld sp,($8000) ; cont: <tail>
    LOOP = "CD0510 18FB ED730080 CD0D10 C9 ED7B0080 "

    def test_reset_lands_in_the_frame_that_saved_sp(self):
        # cont: ret -- returns as r returns, to top, where nothing is read
        A = prog(self.LOOP + "C9", {0x1000: "top"})
        self.assertEqual(A.anchor_frame.get(0x1011), {0x1005})
        self.assertEqual(fmt_units(A.contract(0x100D)["inputs"]), "-")

    def test_cell_written_otherwise_is_not_an_anchor_unless_declared(self):
        # ... plus w: ld ($8000),hl / ret: the cell may hold anything
        code = self.LOOP + "C9 220080 C9"
        roots = {0x1000: "top", 0x1012: "w"}
        A = prog(code, roots)
        self.assertNotIn(0x1011, A.anchor_frame)
        self.assertIn("B", fmt_units(A.contract(0x100D)["inputs"]))
        A = prog(code, roots, "# w relocates the saved SP\nstack-anchor $8000\n")
        self.assertEqual(fmt_units(A.contract(0x100D)["inputs"]), "-")
        self.assertEqual(A.p.annotations.anchor[0x8000].verdict(), "checked")

    def test_reset_cycle_starts_from_nothing_live(self):
        # s: ld sp,$F000 ; c: call s / jr c -- the continuation re-enters s
        # and never returns: nothing is ever read
        A = prog("3100F0 CD0010 18FB", {0x1000: "s"})
        self.assertEqual(fmt_units(A.contract(0x1000)["inputs"]), "-")

    def test_normal_view_leaves_out_reads_after_an_unwind(self):
        # cont: ld a,b / ld ($9000),a / ret -- B is read only after the reset
        A = prog(self.LOOP + "78 320090 C9", {0x1000: "top"}, "# the run loop anchor\nstack-anchor $8000 unwind\n")
        self.assertIn("B", fmt_units(A.contract(0x100D)["inputs"]))
        V = A.normal_view()
        self.assertEqual(fmt_units(A.contract(0x100D, V)["inputs"]), "-")
        self.assertIn("B", fmt_units(A.contract(0x100D)["inputs"]))     # left as it was
        # an abort that unwinds: f: or a / jp z,err / ld b,1 / ret ; err: inc c / ret
        A = prog("B7 CA0810 0601 C9 0C C9", {0x1000: "f", 0x1008: "err"}, "# abort\nabort f+1 unwind\n")
        self.assertIn("C", fmt_units(A.contract(0x1000)["inputs"]))
        self.assertNotIn("C", fmt_units(A.contract(0x1000, A.normal_view())["inputs"]))


class TestFlags(unittest.TestCase):
    def test_returned_carry_picks_the_callers_branch(self):
        # caller: call rb / jr nc,no / ld a,b / ld ($9000),a / no: ret
        # rb: cp 1 / jr z,lt / or a / ret / lt: ld b,1 / scf / ret
        # (B is written exactly on the carry-set return the caller reads it on)
        A = prog("CD0A10 3004 78 320090 C9 FE01 2802 B7 C9 0601 37 C9", {0x1000: "caller", 0x100A: "rb"})
        self.assertEqual(sorted(dict(k[4])["fC"] for k in A.frec[0x100A]["exits"]), [0, 1])
        self.assertNotIn("B", fmt_units(A.contract(0x1000)["inputs"]))
        self.assertIn("A", fmt_units(A.contract(0x1000)["inputs"]))
        # nop for the `or a`: carry unknown on the return that keeps B -- read
        A = prog("CD0A10 3004 78 320090 C9 FE01 2802 00 C9 0601 37 C9", {0x1000: "caller", 0x100A: "rb"})
        self.assertIn("B", fmt_units(A.contract(0x1000)["inputs"]))

    def test_condition_on_a_known_flag_takes_one_edge(self):
        # scf / jr c,skip / ld a,b / ld ($9000),a / skip: ret -- never falls through
        A = prog("37 3804 78 320090 C9", {0x1000: "f"})
        self.assertNotIn("B", fmt_units(A.contract(0x1000)["inputs"]))
        self.assertNotIn(0x1003, A.frec[0x1000]["nodes"])
        # xor a / jr nz,skip / ...: always falls through, B is read
        A = prog("AF 2004 78 320090 C9", {0x1000: "f"})
        self.assertIn("B", fmt_units(A.contract(0x1000)["inputs"]))


def image(parts, size):
    """bytes of `size` with hex snippets placed at their offsets."""
    b = bytearray(size)
    for off, h in parts.items():
        x = bytes.fromhex(h.replace(" ", ""))
        b[off:off + len(x)] = x
    return bytes(b)


def two_slot(main, sub, roots, sub_roots, ann=None):
    """Context 0: `main` at $0000 (pages 0-1). Context 1 ("sub0"): page 0 is
    `sub`, page 1 is main's (shared) -- a page-0 tenant's view. A far entry
    at $001C takes IX and IYH (the slot) and resolves into context 1."""
    p = Program("t2")
    p.add_image(0x0000, main, "main")
    p.add_context(1, "sub0", {0: (sub, 0, "sub"), 1: "shared"})
    p.code_ranges = [(0x0040, 0x7FFF), (0x1_0040, 0x1_3FFF), (0x1_4000, 0x1_7FFF)]
    for a, n in roots.items():
        p.roots[a] = n
        p.add_label(a, n)
    for a, n in sub_roots.items():
        p.roots[0x1_0000 | a] = n
        p.add_label(0x1_0000 | a, n)
    p.opaque[0x001C] = Opaque("CALSLT", "inter-slot")
    p.ram_ranges = [(0x8000, 0xFFFF)]
    from z80flow.decode import m as mk

    def res(vals, site):
        ix, iyh = vals
        if ix is None or iyh != ("m", 0xF000):
            return None
        return [0x1_0000 | v for v in ix]
    p.far_calls[0x001C] = FarCall("CALSLT", ("IX", "IYH"), res, kill=mk("IXH", "IXL", "IYH", "IYL"),
                                  gen=mk("IXH", "IXL", "IYH", "IYL"))
    if ann is not None:
        p.annotations = annotate.loads(ann, p)
        assert not p.annotations.errors, p.annotations.errors
    return Analysis(p).run()


class TestContexts(unittest.TestCase):
    # main $0100: ld a,($F000) / ld d,a / ld e,0 / push de / pop iy /
    #             ld ix,$0050 / call $001C (at $010D) / ret
    # sub0 $0050: ld b,5 / ret
    CALL = "3A00F0 57 1E00 D5 FDE1 DD215000 CD1C00 C9"

    def test_far_call_resolved_into_the_tenant(self):
        A = two_slot(image({0x100: self.CALL}, 0x8000), image({0x50: "0605 C9"}, 0x4000),
                     {0x0100: "f"}, {0x0050: "tenant"})
        self.assertEqual(A.far_resolved[0x010D], ("CALSLT", frozenset({0x1_0050})))
        self.assertEqual(A.status[0x0100], "inferred")          # not CALSLT's assumed effect
        c = fmt_units(A.contract(0x0100)["clobbers"])
        self.assertIn("B", c)                                     # the tenant's write
        self.assertIn("IX", c)                                    # CALSLT's own
        self.assertNotIn("H", c)
        self.assertEqual(A.p.name_of(0x1_0050), "tenant")
        self.assertEqual(A.p.fmt(0x1_0052), "sub0:$0052")

    def test_unresolved_far_call_stays_the_boundary(self):
        call = self.CALL.replace("DD215000", "DD2A0080")      # IX from memory
        A = two_slot(image({0x100: call}, 0x8000), image({0x50: "0605 C9"}, 0x4000),
                     {0x0100: "f"}, {0x0050: "tenant"})
        self.assertEqual(A.far_resolved[0x010D], ("CALSLT", None))
        self.assertEqual(A.status[0x0100], "conservative-boundary")

    def test_tenant_sees_its_own_page_0_and_main_page_1(self):
        # main $4000: ld c,7 / ret   (page 1, visible from the tenant)
        # main $0060: ld h,9 / ret   (page 0: NOT visible from the tenant)
        # sub0 $0050: call $4000 / call $0060 / ret ; sub0 $0060: ld l,1 / ret
        main = image({0x60: "2609 C9", 0x4000: "0E07 C9"}, 0x8000)
        sub = image({0x50: "CD0040 CD6000 C9", 0x60: "2E01 C9"}, 0x4000)
        A = two_slot(main, sub, {0x0060: "low", 0x4000: "p1"}, {0x0050: "tenant", 0x0060: "sublow"})
        c = fmt_units(A.contract(0x1_0050)["clobbers"])
        self.assertIn("C", c)          # main's page-1 routine, run in the tenant's context
        self.assertIn("L", c)          # the tenant's own page-0 routine at $0060
        self.assertNotIn("H", c)       # not main's $0060
        self.assertIn(0x1_4000, A.entries)
        self.assertEqual(A.p.exact_name(0x1_4000), "p1@sub0")

    def test_store_forwarded_to_a_load(self):
        # ld a,($F000) / ld ($F101),a / ld iy,($F100) / ld ix,$0050 / call $001C / ret
        main = image({0x100: "3A00F0 3201F1 FD2A 00F1 DD21 5000 CD1C00 C9"}, 0x8000)
        A = two_slot(main, image({0x50: "0605 C9"}, 0x4000), {0x0100: "f"}, {0x0050: "tenant"})
        self.assertEqual(A.status[0x0100], "inferred")
        # ... but not across a call, which may have written the cell
        main = image({0x100: "3A00F0 3201F1 CD3001 FD2A 00F1 DD21 5000 CD1C00 C9", 0x130: "C9"}, 0x8000)
        A = two_slot(main, image({0x50: "0605 C9"}, 0x4000), {0x0100: "f"}, {0x0050: "tenant"})
        self.assertEqual(A.status[0x0100], "conservative-boundary")

    def test_inlined_twice_in_one_routine(self):
        # two inline calls of the same stub at different depths must not merge
        # main $0100: call stub / db $50 / push bc / call stub / db $50 / pop bc / ret
        main = image({0x100: "CD2001 50 C5 CD2001 50 C1 C9",
                      0x120: "E3 7E 23 E3 DD6F DD2600 3A00F0 57 1E00 D5 FDE1 C31C00"}, 0x8000)
        A = two_slot(main, image({0x50: "0605 C9"}, 0x4000), {0x0100: "f", 0x0120: "stub"},
                     {0x0050: "tenant"}, ann="# analysed in each caller\ninline stub\n")
        self.assertEqual(A.status[0x0100], "inferred")
        self.assertEqual(exit_keys(A, 0x0100), [(0, 0, 0, 0)])

    def test_table_in_another_context(self):
        # a jump table in the tenant's own image, `inplace` (a table of jp's)
        # sub0 $0050: ld a,(F001) / ld l,a / ld h,0 / ld de,$0060 / add hl,de / jp (hl)
        # sub0 $0060: jp $0070 / jp $0074 ; $0070: ld b,1 / ret ; $0074: ld c,1 / ret
        sub = image({0x50: "3A01F0 6F 2600 116000 19 E9", 0x60: "C37000 C37400",
                     0x70: "0601 C9", 0x74: "0E01 C9"}, 0x4000)
        ann = "# the two arms\ntable sub0:$005A sub0:$0060 2 stride=3 inplace\n"
        A = two_slot(image({}, 0x8000), sub, {}, {0x0050: "tenant", 0x0060: "tab"}, ann=ann)
        self.assertEqual(A.status[0x1_0050], "inferred")
        self.assertEqual(fmt_units(A.contract(0x1_0050)["clobbers"]), "BC DE HL A F(H,N,C)")

    def test_qualified_table_not_decoded_in_another_context(self):
        # context 2 shares main's page 0 and has an image of its own in page 1.
        # main $0100 main_r: jp $0200 ; $0200 d: ld hl,(F002) / jp (hl) -> table
        # (declared for main_r only): $0300: jp $4000 ; main $4000: ret.
        # ctx2 $4010 tenant: jp $0200 (into the shared page). Seen from ctx2,
        # $0300's jump lands in ctx2's OWN page 1 (other bytes): discovery must
        # not decode the main-only table's targets there.
        p = Program("t3")
        p.add_image(0, image({0x100: "C30002", 0x200: "2A02F0 E9", 0x300: "C30040", 0x4000: "C9"}, 0x8000), "main")
        other = image({0x0000: "3E01 C9", 0x10: "C30002"}, 0x4000)
        p.add_context(2, "p1", {0: "shared", 1: (other, 0, "other")})
        p.code_ranges = [(0x0100, 0x7FFF), (0x2_0100, 0x2_3FFF), (0x2_4000, 0x2_7FFF)]
        for a_, n in {0x100: "main_r", 0x200: "d", 0x300: "r", 0x4000: "back", 0x2_4010: "tenant"}.items():
            p.roots[a_] = n
            p.add_label(a_, n)
        p.annotations = annotate.loads("# only main_r's\ntargets d+3 r in=main_r\n", p)
        A = Analysis(p).run()
        self.assertNotIn(0x2_4000, A.code)
        self.assertEqual(A.status[0x0100], "inferred")

    def test_rom_byte_and_inline_index(self):
        # an inline-index stub, inlined: the IX low byte is the ROM byte after
        # the call, and the return address skips it
        # main $0100: call stub / db $50 / ret
        # main $0120 stub: ex (sp),hl / ld a,(hl) / inc hl / ex (sp),hl / ld ixl,a /
        #   ld ixh,0 / ld a,($F000) / ld d,a / ld e,0 / push de / pop iy / jp $001C
        main = image({0x100: "CD2001 50 C9",
                      0x120: "E3 7E 23 E3 DD6F DD2600 3A00F0 57 1E00 D5 FDE1 C31C00"}, 0x8000)
        A = two_slot(main, image({0x50: "0605 C9"}, 0x4000), {0x0100: "f", 0x0120: "stub"},
                     {0x0050: "tenant"}, ann="# analysed in each caller\ninline stub\n")
        self.assertEqual(A.status[0x0100], "inferred")
        self.assertIn("B", fmt_units(A.contract(0x0100)["clobbers"]))
        self.assertIn(0x0104, A.code)       # the ret after the inline byte


if __name__ == "__main__":
    unittest.main()
