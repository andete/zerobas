# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""zerobas's own conventions (a program adapter). READ-ONLY use of the zerobas tree.

Facts taken from zerobas's source comments / build tool, not inferred:
  * the merged main ROM is build/zerobas-main-eu.rom at $0000; zerobas code is
    $2781..$7FFF, the cartridge header $4000..$400F is data;
  * page-0 "islands" of zerobas code inside the C-BIOS image
    (tools/build_mainrom.py ISLAND_RANGES);
  * sr_inl0/sr_inl1/sc_inl0/sc_inl1 take ONE inline byte after their call
    (basic/subromcall.asm, D-STUBINL) -- used only to CROSS-CHECK the inference;
  * subrom_call / subrom2_call / sc_call and the four inline stubs are the
    sub-ROM tenant call wrappers (far calls by IX);
  * p0cb (sub2/p0cb.asm) is sub2's call back into main, through CLPRIM; it lives
    in the sub2 image, which v0 does not analyse.
"""
import os

from . import annotate, inline, platform_msx
from .decode import ALLF, REAL
from .program import FarCall, Opaque, Program, load_pasmo_sym

ZEROBAS_LO, ZEROBAS_HI = 0x2781, 0x7FFF
HEADER = (0x4000, 0x400F)
ISLAND_RANGES = ((0x0160, 0x0200), (0x1AF5, 0x1BBF), (0x09D9, 0x09EE))
INLINE_STUBS = {"sr_inl0": 1, "sr_inl1": 1, "sc_inl0": 1, "sc_inl1": 1}
SUBROM_WRAPPERS = ["subrom_call", "subrom2_call", "sc_call", "sr_slot",
                   "sr_inl0", "sr_inl1", "sc_inl0", "sc_inl1"]
FAR_CONVENTIONS_LATER = {"p0cb": "sub2 page 0: IX = main address, via CLPRIM ($F38C); sub2 image, not analysed in v0"}


def in_island(a):
    return any(lo <= a < hi for lo, hi in ISLAND_RANGES)


# The sub-ROM contexts (see Program.add_context): a tenant runs with ONLY its
# own page switched in (docs/subrom-tenant-playbook.md section 2): a page-0
# tenant sees main page 1, a page-1 tenant sees main page 0 (BIOS + low region).
SUBROM_CTX = {"sub": (1, 2), "sub2": (3, 4)}      # image -> (page-0 ctx, page-1 ctx)
SUBROM_CODE = {"sub": (0x0040, 0x4010), "sub2": (0x0010, 0x4010)}   # first code byte per page
DISK_CTX = 5    # build/disk.rom: page 1 of slot 3-1 ($4000-$7FFF), main page 0 shared


def build(zerobas_dir, whole_image=False, hooks="practice", with_subroms=True, markers=True, ann_files=()):
    rom_path = os.path.join(zerobas_dir, "build", "zerobas-main-eu.rom")
    sym_path = os.path.join(zerobas_dir, "build", "basic-reloc.sym")
    rom = open(rom_path, "rb").read()
    syms = load_pasmo_sym(sym_path)
    p = Program("zerobas main ROM, whole image" if whole_image else "zerobas main ROM, zerobas code only")
    p.add_image(0x0000, rom, "zerobas-main-eu.rom")
    p.inputs = {"rom": rom_path, "sym": sym_path, "rom_len": len(rom)}
    lo = 0x0000 if whole_image else ZEROBAS_LO
    p.code_ranges = [(lo, HEADER[0] - 1), (HEADER[1] + 1, ZEROBAS_HI)]
    p.zerobas_range = (ZEROBAS_LO, ZEROBAS_HI)
    byname = {}
    for name, v in syms:
        byname[name] = v
        if v >= ZEROBAS_LO or (v < ZEROBAS_LO and not name.isupper()):
            # upper-case names below $2781 are constants or BIOS EQUs; the
            # platform names the BIOS entries itself
            p.add_label(v, name)
        if ZEROBAS_LO <= v <= ZEROBAS_HI and not (HEADER[0] <= v <= HEADER[1]):
            p.roots.setdefault(v, name)
        elif whole_image and v < ZEROBAS_LO and in_island(v) and not name.isupper():
            p.roots.setdefault(v, name)
    p.byname = byname
    for lo_, hi_ in ISLAND_RANGES:      # stop island names leaking onto C-BIOS bytes
        p.add_label(hi_, f"cbios_{hi_:04X}")
    # zerobas names code and data labels in lower case and constants in upper
    # case (a convention, not a rule, so it only feeds the straddle check)
    p.boundaries = {v for n, v in syms if not n.isupper() and v <= ZEROBAS_HI
                    and (v >= ZEROBAS_LO or in_island(v))}
    for n, k in INLINE_STUBS.items():
        if n in byname:
            p.declared_inline[byname[n]] = k
    for n in SUBROM_WRAPPERS:
        if n in byname:
            p.far_call_groups[byname[n]] = "sub-ROM tenant call"

    def cls(a):
        if in_island(a):
            return "zerobas page-0 island"
        return None
    p.classifier = cls
    platform_msx.apply(p, bios_in_code=whole_image, hooks=hooks)
    if with_subroms:
        add_subroms(p, zerobas_dir, byname, whole_image)
        add_diskrom(p, zerobas_dir, byname, whole_image, hooks)
    # zerobas's own RAM hook (cbios-repack key-trap-hook.patch: H_ZKEY at $FFCF,
    # just past the MSX hook area), declared like any MSX hook
    p.opaque[0xFFCF] = Opaque("H_ZKEY $FFCF", "hook", inputs=REAL, preserves=0, in_ram=True, patch_point=True,
                              note="zerobas function-key delivery hook (repack patch)")
    # ... but no other program knows it: zerobas installs `jp zkey_hook` there
    # at boot (basic/subrom-boot.asm zkey_install), so unless every hook is
    # taken as open, a call to it is followed into zkey_hook
    if hooks != "open" and "zkey_hook" in byname:
        zk = byname["zkey_hook"]
        p.far_calls[0xFFCF] = FarCall("H_ZKEY", (), lambda vals, site: [zk])
    # hand annotations: zerobas's own are `; z80flow:` markers in its sources
    # (inline.py); C-BIOS's, when it is analysed too, are a file of their own
    here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "annotations")
    files = [os.path.join(here, "cbios-in-zerobas.ann")] if whole_image else []
    files += list(ann_files or ())
    p.annotations = annotate.load([f for f in files if os.path.exists(f)], p)
    if markers:
        inline.resolve(zerobas_dir, source_images(zerobas_dir, p, with_subroms), p, p.annotations)
    p.notes.append("Candidate roots: every basic-reloc.sym name whose value lies in the code range; "
                   "the sym file does not separate labels from EQU constants, so data/constant roots "
                   "are expected and must be rejected by validation.")
    return p


def add_subroms(p, zerobas_dir, byname, whole_image):
    """Map build/sub.rom and build/sub2.rom as contexts of their own, seed
    their sym labels as roots, and resolve CALSLT (slot cell SUBSLOT /
    SUBSLOT2 + IX) and sub2's p0cb call-back (IX = a main address)."""
    from .decode import m
    imgs = {}
    for k in ("sub", "sub2"):
        data = open(os.path.join(zerobas_dir, "build", k + ".rom"), "rb").read()
        imgs[k] = data
        c0, c1 = SUBROM_CTX[k]
        p.add_context(c0, f"{k}p0", {0: (data, 0, k + ".rom"), 1: "shared"})
        p.add_context(c1, f"{k}p1", {0: "shared", 1: (data, 0x4000, k + ".rom")})
        lo0, lo1 = SUBROM_CODE[k]
        p.code_ranges += [(c0 << 16 | lo0, c0 << 16 | 0x3FFF), (c1 << 16 | lo1, c1 << 16 | 0x7FFF)]
        # the main pages each tenant context shares: page 1 for a page-0
        # tenant, page 0 for a page-1 tenant (only the part analysed in ctx 0)
        p.code_ranges.append((c0 << 16 | HEADER[1] + 1, c0 << 16 | ZEROBAS_HI))
        p.code_ranges.append((c1 << 16 | (0 if whole_image else ZEROBAS_LO), c1 << 16 | 0x3FFF))
        for name, v in load_pasmo_sym(os.path.join(zerobas_dir, "build", k + ".sym")):
            # skip constants and the main-ROM ABI equates (same name, same value)
            if name.isupper() or byname.get(name) == v or v > 0x7FFF:
                continue
            if name.startswith("p0_") and byname.get(name[3:]) == v:
                continue        # sub2's names for main addresses (its p0cb targets)
            page = v >> 14
            ctx = c0 if page == 0 else c1
            g = ctx << 16 | v
            p.add_label(g, name)
            p.boundaries.add(g)
            if v >= (lo0 if page == 0 else lo1) and imgs[k][v] != 0xFF:
                p.roots.setdefault(g, name)
    slot_of = {("m", byname["SUBSLOT"]): "sub", ("m", byname["SUBSLOT2"]): "sub2",
               ("m", byname["DISKSLOT"]): "disk"}

    def resolve(iyh, ixs):
        k = slot_of.get(iyh)
        if k is None:
            return None
        out = []
        for v in ixs:
            if k == "disk":
                if v >> 14 != 1:        # the disk ROM is page 1 only
                    return None
                out.append(DISK_CTX << 16 | v)
                continue
            if v >> 14 > 1:
                return None
            out.append(SUBROM_CTX[k][v >> 14] << 16 | v)
        return out
    p.far_calls[0x001C] = platform_msx.calslt_far(resolve)
    # sub2's call-back into main (sub2/p0cb.asm, docs/spec-sub2-p0cb.md:
    # "HL / DE / BC / A / F cross in BOTH directions; IX is consumed"; it
    # parks the caller's AF in AF', so AF' does not survive)
    cb = p.resolve("sub2p0:p0cb")
    if cb is not None:
        def back(vals, site):
            ix, = vals
            return list(ix) if ix else None      # main code, or a hook cell called through
        af_alt = REAL & ~m("A", "B", "C", "D", "E", "H", "L", "IXH", "IXL", "IYH", "IYL",
                            "B'", "C'", "D'", "E'", "H'", "L'") & ~ALLF      # A' and F'
        p.far_calls[cb] = FarCall("p0cb", ("IX",), back, kill=af_alt, gen=m("IXH", "IXL"))
    p.notes.append("build/sub.rom and build/sub2.rom are mapped as contexts sub/sub2 p0/p1 (each tenant "
                   "page with the main page it sees); their .sym labels are roots; CALSLT with a constant "
                   "IX and IYH from SUBSLOT/SUBSLOT2, and sub2's p0cb with a constant IX, are followed into "
                   "the routine they reach.")


def add_diskrom(p, zerobas_dir, byname, whole_image, hooks):
    """build/disk.rom (zerobas-disk, slot 3-1 page 1) as context `disk`.

    disk/disk.asm: an "AB" ROM whose INIT claims hooks with the standard
    CALLF stub `F7 <slot> <lo> <hi> C9` (disk/kernel.asm install_hook, from
    the (hook, handler) pairs of hook_tab, plus HPHYD -> DSKIO in disk/init.asm),
    and whose handlers call back into main page 1 through `calbak` (IX = the
    main target; "A/HL/DE/BC pass through in both directions; IY is ours and
    IX is consumed", kernel.asm). The CALSLT resolver (add_subroms) maps the
    DISKSLOT cell to this context."""
    from .decode import m
    path = os.path.join(zerobas_dir, "build", "disk.rom")
    if not os.path.exists(path):
        return
    data = open(path, "rb").read()
    p.add_context(DISK_CTX, "disk", {0: "shared", 1: (data, 0, "disk.rom")})
    p.code_ranges.append((DISK_CTX << 16 | 0x4010, DISK_CTX << 16 | 0x7FFF))
    p.code_ranges.append((DISK_CTX << 16 | (0 if whole_image else ZEROBAS_LO), DISK_CTX << 16 | 0x3FFF))
    dsym = {}
    for name, v in load_pasmo_sym(os.path.join(zerobas_dir, "build", "disk.sym")):
        dsym.setdefault(name, v)
        if name.isupper() or byname.get(name) == v or not 0x4000 <= v <= 0x7FFF:
            continue
        g = DISK_CTX << 16 | v
        p.add_label(g, name)
        p.boundaries.add(g)
        # the ROM is padded with $00 between its pinned regions; a `*_tmpl` is
        # code assembled to be copied to (and run at) a RAM address, not here
        if v >= 0x4010 and data[v - 0x4000] != 0x00 and not name.endswith("_tmpl"):
            p.roots.setdefault(g, name)
    # P1_BLIT: install_p1blit (disk/driver.asm) LDIRs p1_blit_tmpl to P1_BLIT
    # in page-3 RAM "on EVERY host"; the template is position-independent
    # (no absolute jump or call inside), so a call there runs its code
    if "P1_BLIT" in dsym and "p1_blit_tmpl" in dsym:
        g = DISK_CTX << 16 | dsym["p1_blit_tmpl"]
        p.far_calls[dsym["P1_BLIT"]] = FarCall("P1_BLIT (RAM copy)", (), lambda vals, site, g=g: [g])
    cb = dsym.get("calbak")
    allbut = REAL & ~(m("A", "B", "C", "D", "E", "H", "L") | ALLF)     # IX, IY, the alternate set
    if cb is not None:
        def back(vals, site):
            ix, = vals
            return list(ix) if ix else None      # main code, or a hook cell called through
        p.far_calls[DISK_CTX << 16 | cb] = FarCall("calbak", ("IX",), back, kill=allbut, gen=m("IXH", "IXL"))
    # the hooks it claims, read from its own hook_tab (pairs of words, $0000
    # ends it) and HPHYD -> DSKIO_ENTRY; "practice" policy: on a disk machine
    # the hook is the CALLF into the handler, on a diskless one its boot
    # `ret` -- both, as alternatives
    if hooks == "open" or "hook_tab" not in dsym:
        return
    claimed = {}
    a = dsym["hook_tab"] - 0x4000
    while True:
        h, t = data[a] | data[a + 1] << 8, data[a + 2] | data[a + 3] << 8
        if h == 0:
            break
        claimed[h] = t
        a += 4
    if "HPHYD" in byname and "DSKIO_ENTRY" in dsym:
        claimed[byname["HPHYD"]] = dsym["DSKIO_ENTRY"]
    p.disk_hooks = claimed
    for h, t in claimed.items():
        g = DISK_CTX << 16 | t
        p.far_calls[h] = FarCall(f"hook ${h:04X} (disk.rom)", (), lambda vals, site, g=g: [g, FarCall.FALLBACK],
                                 kill=allbut)


def source_label_kinds(zerobas_dir):
    """name -> 'code' | 'data' | 'equ' from the asm source: the line after `name:`.

    Used ONLY to cross-check root acceptance, never as analysis input.
    """
    import glob
    import re
    kinds = {}
    files = glob.glob(os.path.join(zerobas_dir, "basic", "*.asm")) + \
        glob.glob(os.path.join(zerobas_dir, "basic", "*.inc"))
    lab = re.compile(r"^([A-Za-z_][\w.]*):?\s*(.*)$")
    for f in files:
        lines = open(f, errors="replace").read().split("\n")
        for i, line in enumerate(lines):
            if not line or line[0] in " \t;":
                continue
            mt = lab.match(line)
            if not mt:
                continue
            name, rest = mt.group(1), mt.group(2).split(";")[0].strip()
            if rest.lower().startswith("equ") or rest.lower().startswith("defl"):
                kinds.setdefault(name, "equ")
                continue
            nxt = rest
            j = i + 1
            while not nxt and j < len(lines):
                s = lines[j].split(";")[0].strip()
                if s and lines[j][0] not in " \t":
                    nxt = "LABEL"
                    if lab.match(lines[j]) and lab.match(lines[j]).group(2).split(";")[0].strip():
                        nxt = lab.match(lines[j]).group(2).split(";")[0].strip()
                    else:
                        j += 1
                        nxt = ""
                        continue
                    break
                nxt = s
                j += 1
            w = nxt.split()[0].lower() if nxt else ""
            if w in ("db", "dw", "ds", "defb", "defw", "defs", "defm", "dm"):
                kinds.setdefault(name, "data")
            elif w in ("if", "else", "endif", "include", "org", "macro", "endm", "label"):
                kinds.setdefault(name, "unknown")
            elif w:
                kinds.setdefault(name, "code")
    return kinds


def clobber_comments(zerobas_dir):
    """name -> (set of register names, text, 'file:line') from header comments.

    A `; ... Clobbers X, Y.` line in the comment block directly above a label.
    Only the capitalised word counts (prose "clobbers" is usually about callees).
    Used ONLY to compare against the inference.
    """
    import glob
    import re
    out = {}
    lab = re.compile(r"^([a-z_][\w]*):")
    for f in sorted(glob.glob(os.path.join(zerobas_dir, "basic", "*.asm"))):
        lines = open(f, errors="replace").read().split("\n")
        pending = None
        for i, line in enumerate(lines):
            if line.startswith(";"):
                mt = re.search(r"Clobbers\s+([^.;]*)", line)
                if mt and "everything" not in mt.group(1):
                    pending = (mt.group(1), i + 1)
                continue
            mt = lab.match(line)
            if mt and pending:
                text, ln = pending
                regs = set()
                for tok in re.findall(r"\b(AF|BC|DE|HL|IX|IY|A|B|C|D|E|H|L|F|flags)\b", text):
                    if tok in ("AF",):
                        regs |= {"A", "F"}
                    elif tok in ("BC", "DE", "HL"):
                        regs |= set(tok)
                    elif tok == "flags":
                        regs.add("F")
                    else:
                        regs.add(tok)
                if regs and i + 1 - ln <= 3:
                    out.setdefault(mt.group(1), (regs, text.strip(), f"basic/{os.path.basename(f)}:{ln}"))
                pending = None
            elif line.strip() and not line.startswith(";") and not mt:
                pending = None
    return out


def source_images(zerobas_dir, p, with_subroms=True):
    """zerobas's images as inline.Image: top source, include dirs (the
    Makefile's `pasmo -I`), symbols, and the context each address is
    analysed in."""
    def syms(f):
        path = os.path.join(zerobas_dir, "build", f)
        return dict(load_pasmo_sym(path)) if os.path.exists(path) else None
    main = syms("basic-reloc.sym")
    out = [inline.Image("main", "basic/main.asm", [], main,
                        lambda v: 0 if v <= ZEROBAS_HI else None, lambda c: "")]
    if not with_subroms:
        return out
    for k, top in (("sub", "sub/sub.asm"), ("sub2", "sub2/sub2.asm")):
        s = syms(k + ".sym")
        if s is None:
            continue
        c0, c1 = SUBROM_CTX[k]

        def own(n, v):
            # not one of main's names (the resident ABI equates, sub2's p0_*)
            return main.get(n) != v and not (n.startswith("p0_") and main.get(n[3:]) == v)
        out.append(inline.Image(k, top, ["sub"], s,
                                lambda v, c0=c0, c1=c1: c0 if v < 0x4000 else c1 if v <= 0x7FFF else None,
                                lambda c: p.contexts[c], own))
    d = syms("disk.sym")
    if d is not None and DISK_CTX in p.contexts:
        out.append(inline.Image("disk", "disk/disk.asm", ["disk"], d,
                                lambda v: DISK_CTX if 0x4000 <= v <= 0x7FFF else None,
                                lambda c: p.contexts[c], lambda n, v: main.get(n) != v))
    return out
