# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""MSX1 platform facts. Everything MSX-specific lives here, not in the core.

Sources: the public MSX BIOS entry list (MSX Technical Handbook / MSX2
Technical Handbook entry tables) -- names, addresses and documented register
contracts only. No ROM disassembly was consulted.
"""
from .decode import m, ALLF, REAL
from .program import FarCall, Opaque, external

# The documented MSX1 BIOS jump-table entries that are CODE ($0004..$0007 and
# $002B..$002F are data bytes and are deliberately absent).
BIOS_ENTRIES = {
    0x0000: "CHKRAM", 0x0008: "SYNCHR", 0x000C: "RDSLT", 0x0010: "CHRGTR",
    0x0014: "WRSLT", 0x0018: "OUTDO", 0x001C: "CALSLT", 0x0020: "DCOMPR",
    0x0024: "ENASLT", 0x0028: "GETYPR", 0x0030: "CALLF", 0x0038: "KEYINT",
    0x003B: "INITIO", 0x003E: "INIFNK", 0x0041: "DISSCR", 0x0044: "ENASCR",
    0x0047: "WRTVDP", 0x004A: "RDVRM", 0x004D: "WRTVRM", 0x0050: "SETRD",
    0x0053: "SETWRT", 0x0056: "FILVRM", 0x0059: "LDIRMV", 0x005C: "LDIRVM",
    0x005F: "CHGMOD", 0x0062: "CHGCLR", 0x0066: "NMI", 0x0069: "CLRSPR",
    0x006C: "INITXT", 0x006F: "INIT32", 0x0072: "INIGRP", 0x0075: "INIMLT",
    0x0078: "SETTXT", 0x007B: "SETT32", 0x007E: "SETGRP", 0x0081: "SETMLT",
    0x0084: "CALPAT", 0x0087: "CALATR", 0x008A: "GSPSIZ", 0x008D: "GRPPRT",
    0x0090: "GICINI", 0x0093: "WRTPSG", 0x0096: "RDPSG", 0x0099: "STRTMS",
    0x009C: "CHSNS", 0x009F: "CHGET", 0x00A2: "CHPUT", 0x00A5: "LPTOUT",
    0x00A8: "LPTSTT", 0x00AB: "CNVCHR", 0x00AE: "PINLIN", 0x00B1: "INLIN",
    0x00B4: "QINLIN", 0x00B7: "BREAKX", 0x00BA: "ISCNTC", 0x00BD: "CKCNTC",
    0x00C0: "BEEP", 0x00C3: "CLS", 0x00C6: "POSIT", 0x00C9: "FNKSB",
    0x00CC: "ERAFNK", 0x00CF: "DSPFNK", 0x00D2: "TOTEXT", 0x00D5: "GTSTCK",
    0x00D8: "GTTRIG", 0x00DB: "GTPAD", 0x00DE: "GTPDL", 0x00E1: "TAPION",
    0x00E4: "TAPIN", 0x00E7: "TAPIOF", 0x00EA: "TAPOON", 0x00ED: "TAPOUT",
    0x00F0: "TAPOOF", 0x00F3: "STMOTR", 0x00F6: "LFTQ", 0x00F9: "PUTQ",
    0x00FC: "RIGHTC", 0x00FF: "LEFTC", 0x0102: "UPC", 0x0105: "TUPC",
    0x0108: "DOWNC", 0x010B: "TDOWNC", 0x010E: "SCALXY", 0x0111: "MAPXY",
    0x0114: "FETCHC", 0x0117: "STOREC", 0x011A: "SETATR", 0x011D: "READC",
    0x0120: "SETC", 0x0123: "NSETCX", 0x0126: "GTASPC", 0x0129: "PNTINI",
    0x012C: "SCANR", 0x012F: "SCANL", 0x0132: "CHGCAP", 0x0135: "CHGSND",
    0x0138: "RSLREG", 0x013B: "WSLREG", 0x013E: "RDVDP", 0x0141: "SNSMAT",
    0x0144: "PHYDIO", 0x0147: "FORMAT", 0x014A: "ISFLIO", 0x014D: "OUTDLP",
    0x0150: "GETVCP", 0x0153: "GETVC2", 0x0156: "KILBUF", 0x0159: "CALBAS",
}
JUMP_TABLE = (0x0000, 0x015F)
RST_VECTORS = [0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38]
ISR = 0x0038
HOOKS = (0xFD9A, 0xFFC9)
# The hooks the $0038 interrupt handler calls. Any program may patch any hook,
# but in practice (Joost, 2026-10-31) only these are commonly patched, so the
# default policy keeps them open and takes the others as their boot content.
INTERRUPT_HOOKS = {0xFD9A: "H_KEYI", 0xFD9F: "H_TIMI"}
WORKAREA = (0xF380, 0xFD99)
IO_PORTS = {0x98: "VDP data", 0x99: "VDP ctrl", 0xA0: "PSG addr", 0xA1: "PSG wr",
            0xA2: "PSG rd", 0xA8: "PPI A (slots)", 0xA9: "PPI B (keys)",
            0xAA: "PPI C", 0xAB: "PPI ctrl", 0x90: "printer", 0x91: "printer data"}

ALL_BUT = lambda *names: REAL & ~m(*names)   # noqa: E731

# Inter-slot entries: their real target comes from registers or inline data, so
# they are declared, never entered. Effects are the documented contracts.
FAR_CALLS = {
    0x000C: Opaque("RDSLT", "inter-slot", inputs=m("A", "H", "L"),
                   preserves=ALL_BUT("A", "B", "C", "D", "E") & ~ALLF,
                   note="A=slot HL=addr -> A=byte; changes AF BC DE"),
    0x0014: Opaque("WRSLT", "inter-slot", inputs=m("A", "H", "L", "E"),
                   preserves=ALL_BUT("A", "B", "C", "D") & ~ALLF,
                   note="A=slot HL=addr E=byte; changes AF BC D"),
    0x001C: Opaque("CALSLT", "inter-slot", inputs=REAL, preserves=0,
                   note="IY(high)=slot IX=addr; target's contract unknown"),
    0x0024: Opaque("ENASLT", "inter-slot", inputs=m("A", "H"), preserves=0,
                   note="A=slot H=page; maps another slot in"),
    0x0030: Opaque("CALLF", "inter-slot", inputs=REAL, preserves=0, inline=3,
                   note="rst $30 / call $0030 + db slot + dw addr"),
    0x0159: Opaque("CALBAS", "inter-slot", inputs=REAL, preserves=0,
                   note="IX=BASIC address in the BASIC slot"),
}


# The slot primitives the BIOS copies into page-3 work area RAM at boot
# (RDPRIM/WRPRIM/CLPRIM, documented MSX system work area). Effects from the
# C-BIOS source, src/slot.asm:412 m_rdprim..m_cl_jp (BSD): RDPRIM `out
# (A8),a / ld e,(hl) / ld a,d / out (A8),a / ret`; WRPRIM `... ld (hl),e
# ...`; CLPRIM `out (A8),a / ex af,af' / call (ix) / ex af,af' / pop af /
# out (A8),a / ex af,af' / ret` -- it pops the AF word its caller pushed
# where a return address would be, and returns through the slot below it
# (CALSLT pushes its restore address, then AF, then `jp clprim`).
RAM_PRIMS = {
    0xF380: Opaque("RDPRIM", "ram-prim", inputs=m("A", "D", "H", "L"),
                   preserves=ALL_BUT("A", "E"), in_ram=True,
                   note="A=new slot reg, D=old, HL=addr -> E=byte; A=D"),
    0xF385: Opaque("WRPRIM", "ram-prim", inputs=m("A", "D", "E", "H", "L"),
                   preserves=ALL_BUT("A"), in_ram=True,
                   note="A=new slot reg, D=old, HL=addr, E=byte; A=D"),
    0xF38C: Opaque("CLPRIM", "ram-prim", inputs=REAL, preserves=0, in_ram=True, exit=(1, 0, 0, 0),
                   note="A=slot reg, IX=target; pops the caller's AF; target's contract unknown"),
}


def calslt_far(resolve):
    """CALSLT ($001C) as a far-call entry: the target is IY(high) = slot id and
    IX = address (MSX BIOS entry list). resolve(slot value, [IX values]) -> a
    list of global targets, or None; the program adapter knows which slot is
    which image. Around the callee CALSLT changes IX, IY and the alternate
    set (the documented contract; C-BIOS src/slot.asm calslt keeps IX/IY but
    uses the alternate set for its own work), and reads IX and IY."""
    shadows = REAL & ~(m("A", "B", "C", "D", "E", "H", "L", "IXH", "IXL", "IYH", "IYL") | ALLF)
    ixiy = m("IXH", "IXL", "IYH", "IYL")

    def res(vals, site):
        ix, iyh = vals
        if not ix:
            return None
        return resolve(iyh, ix)
    return FarCall("CALSLT", ("IX", "IYH"), res, kill=ixiy | shadows, gen=ixiy)


def hook_opaque(a):
    base = HOOKS[0] + (a - HOOKS[0]) // 5 * 5
    return Opaque(f"hook ${base:04X}", "hook", inputs=REAL, preserves=0, in_ram=True, patch_point=True,
                  note="RAM hook: RET by default, an extension may patch it")


def hook_opaque_unpatched(a):
    """The same hook as it is at boot: five bytes of `ret` (C9)."""
    base = HOOKS[0] + (a - HOOKS[0]) // 5 * 5
    return Opaque(f"hook ${base:04X}", "hook-unpatched", inputs=0, preserves=REAL, in_ram=True,
                  patch_point=True, note="RAM hook as initialised: a bare RET")


def classify(a):
    if JUMP_TABLE[0] <= a <= JUMP_TABLE[1]:
        n = BIOS_ENTRIES.get(a)
        return f"bios-entry {n}" if n else "bios-entry (unnamed)"
    if a < 0x4000:
        return "bios-internal"
    if HOOKS[0] <= a <= HOOKS[1]:
        return "hook"
    if WORKAREA[0] <= a <= WORKAREA[1]:
        return "ram-workarea"
    if a >= 0x8000:
        return "ram"
    return "page-1-outside-code"


HOOK_POLICIES = ("practice", "open", "unpatched")


def hook_factory(policy):
    """practice: a hook is the bare RET it is at boot, except the interrupt
    hooks, which may run anything; open: every hook may run anything;
    unpatched: every hook is a bare RET."""
    if policy == "open":
        return hook_opaque
    if policy == "unpatched":
        return hook_opaque_unpatched

    def practice(a):
        base = HOOKS[0] + (a - HOOKS[0]) // 5 * 5
        return hook_opaque(a) if base in INTERRUPT_HOOKS else hook_opaque_unpatched(a)
    return practice


def apply(prog, bios_in_code, hooks="practice"):
    """Declare the MSX boundaries on a Program.

    bios_in_code: whether $0000..$3FFF BIOS bytes are part of the analysed code.
    hooks: the hook policy (see hook_factory). A contract that differs between
    "practice" and "open" depends on no program patching a hook.
    """
    for a, n in BIOS_ENTRIES.items():
        prog.add_label(a, n)
    for a, o in FAR_CALLS.items():
        prog.opaque[a] = o
    for a, o in RAM_PRIMS.items():
        prog.opaque[a] = o
    prog.far_target_regs[0x001C] = "IX"      # CALSLT: IY(high) = slot, IX = address
    prog.far_target_regs[0x0159] = "IX"      # CALBAS: IX = BASIC address
    prog.opaque_ranges.append((HOOKS[0], HOOKS[1], hook_factory(hooks)))
    prog.ram_ranges.append((0x8000, 0xFFFF))   # page 2/3 RAM (MSX1, 32K+ RAM)
    prev = prog.classifier

    def cls(a):
        c = prev(a) if prev else None
        return c or classify(a)
    prog.classifier = cls
    if bios_in_code:
        for a, n in BIOS_ENTRIES.items():
            if a not in FAR_CALLS and a != ISR:
                prog.roots.setdefault(a, n)
        for v in RST_VECTORS:
            if v != 0x30 and v != ISR:
                prog.roots.setdefault(v, f"RST{v:02X}")
        prog.interrupt_entries[ISR] = "KEYINT ($0038 ISR)"
        prog.notes.append("BIOS roots seeded from the MSX jump table, the RST vectors "
                          "and the $0038 ISR (no symbol file matches the merged C-BIOS bytes).")
    return prog


def io_name(port):
    if port is None:
        return "(C)"
    return f"${port:02X} {IO_PORTS.get(port, '')}".strip()
