#!/usr/bin/env python3
"""🔪 IS THIS ROW LOAD-BEARING? Break the keyword and see whether its row notices.

Joost ruled 2026-09-13 that every keyword is TIER 0 — no tier established — because
a `SUPPORTED` verdict is ONE AGREEMENT POINT and agreement can be vacuous. This is
the non-vacuity half of what establishing a tier needs: disable a statement's
handler in the BUILT ROM and re-run only its kwsweep row. A row still SUPPORTED
with the handler dead is BLIND, and its keyword's evidence is worth nothing.

⚠️ A KNIFE CAN BE SILENTLY INERT because the plant never happened, and it reports
that the same way a keyword with no defect reports (TODO.md: 13 runners lacked the
guard). So the plant is VERIFIED here: the ROM bytes are read back after writing,
and the run refuses if they are not what was written.

The statement dispatch is a table (`db token / dw handler`), so a knife is a
two-byte write to one entry — no rebuild, and no risk of hitting a handler some
OTHER keyword shares, which is why the table entry is cut and not the handler.
"""
import io, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import knife_guard  # D-KNIFEROM: prove the cut reached the INSTALLED images
ROM = os.path.join(ROOT, "build", "zerobas-main-eu.rom")
SYM = os.path.join(ROOT, "build", "basic-reloc.sym")

def syms():
    out = {}
    for line in io.open(SYM, errors="replace"):
        m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out

def token_of(name):
    """The token byte for a statement keyword, from sysvars.inc's own equate."""
    src = io.open(os.path.join(ROOT, "basic", "sysvars.inc"), encoding="utf-8").read()
    m = re.search(r"^%s_TOKEN\s+equ\s+\$([0-9A-Fa-f]+)" % name, src, re.M)
    if not m:
        sys.exit(f"knife: no {name}_TOKEN equate — nothing was measured")
    return int(m.group(1), 16)

DEADTOK = 0xFE          # matches no kwtable entry, so a `cp` against it never fires


def _string_selectors():
    """Selectors whose kwtable entry names a STRING-returning function (`...$`).

    These, and only these, dispatch through `basic/strvar.asm`, so these and only
    these may be cut at a `jr z,str_*` site. Read from the two-byte crunch form
    `db <n>,"NAME$",2,<prefix>,<TOKEN>` — the same rule `enumerate_fn_targets`
    uses to decide a keyword is function-dispatched at all."""
    eq = {}
    for m in re.finditer(r"^(\w+)\s+equ\s+\$([0-9A-Fa-f]+)",
                         io.open(os.path.join(ROOT, "basic", "sysvars.inc"),
                                 encoding="utf-8").read(), re.M):
        eq[m.group(1)] = int(m.group(2), 16)
    out = set()
    for m in re.finditer(r'db\s+\d+,"([^"]+)",2,\w+,(\w+)',
                         io.open(os.path.join(ROOT, "basic", "kwtable.inc"),
                                 encoding="utf-8").read()):
        if m.group(1).endswith("$") and eq.get(m.group(2)) is not None:
            out.add(eq[m.group(2)])
    return out


def plant_fn(tok, kw=""):
    """Cut a FUNCTION selector by changing the COMPARISON OPERAND, not the target.

    🔴 THE STATEMENT CUT DOES NOT REACH THESE. `$FF`-prefixed selectors dispatch
    through a `cp <TOK>` / `jp z,<handler>` chain in expr.asm (plus the
    `ev_ff_argtab` cpir set), not through stmt_table — which is exactly why VDP,
    BASE and MAX came back unconnected from the statement sweep: their ROWS use the
    function form and the knife had cut the statement entry. The wrong path being
    cut is not the row being blind.
    🎯 PATCHING THE OPERAND rather than the jump target works for `jp z` and `jr z`
    alike (a `jr` to the error tail would usually be out of range), and it fails
    SAFELY: the selector simply never matches and the chain falls through to its own
    error path.
    ⚠️ AMBIGUITY IS REFUSED, NOT GUESSED: `FE <tok>` can occur by accident in data
    or inside another instruction's operand, so a site counts only if a conditional
    jump follows it, and the run stops unless EXACTLY ONE site qualifies."""
    rom = bytearray(io.open(ROM, "rb").read())
    # 🔴 THE JUMP TARGET MUST RESOLVE TO A KNOWN `ev_*` SYMBOL. Matching `cp <tok>`
    # followed by any conditional jump found 2-3 sites per keyword -- the token byte
    # recurs in the tokeniser, the detokeniser and by coincidence inside other
    # operands. Requiring the target to be a named evaluator entry cuts each to
    # exactly one, and a keyword with NO such site is reported rather than guessed
    # at (MAX has none: it is not dispatched this way at all).
    byaddr = {}
    for line in io.open(SYM, errors="replace"):
        m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m:
            byaddr[int(m.group(2), 16)] = m.group(1)
    # 🔪 THE THIRD CUT SHAPE (D-KWSTRCUT 2026-09-13), and it was NOT a mystery —
    # `basic/sysvars.inc:250` named it in prose written long before this knife
    # existed: MKI$ is evaluated in `basic/strvar.asm` BECAUSE IT RETURNS A STRING.
    # The site is real (`strvar.asm:284`), and TWO assumptions here hid it:
    #   1. only `$CA` (`jp z,nn`) was matched, but the string chain is short enough
    #      to use `jr z,d` ($28) — a RELATIVE target this code never resolved;
    #   2. only an `ev_*` target was accepted, but the string evaluators are named
    #      `str_*`.
    # Both are widened, and NEITHER loosens the ambiguity rule: a site still counts
    # only when a conditional jump follows AND its target resolves to a named
    # evaluator entry, and the run still stops unless EXACTLY ONE site qualifies.
    # 🔴 AND THE WIDENING IS NAMESPACE-GUARDED, BECAUSE THE FIRST ATTEMPT WAS NOT
    # AND THAT WAS WORSE THAN THE GAP IT CLOSED. An MSX token byte lives in TWO
    # namespaces: `$xx` as a statement token and `$FF $xx` as a function selector,
    # and the same byte names DIFFERENT keywords in each. `basic/sysvars.inc` says
    # so out loud in two places — `INPUT_TOKEN equ $85` beside `INT_TOKEN equ $85`,
    # and `DEF_TOKEN equ $97 ; PEEK's $97 is the 2nd byte after $FF`. A raw
    # `cp <tok>` byte search cannot tell them apart. Accepting `jr z` with any
    # `ev_*`/`str_*` target handed INT the site belonging to INPUT$ in the STRING
    # chain, and the run then reported INT as 🔴 BLIND — which does not merely miss,
    # it DEFAMES a row that is fine. A false BLIND is worse than an honest refusal.
    # So the new shape is admitted on the narrowest terms that still reach MKI$:
    #   * `jp z` + `ev_*`  — unchanged, byte for byte, so no prior reading moves;
    #   * `jr z` + `str_*` — ONLY for a keyword whose kwtable name ends in `$`,
    #                        i.e. one that actually RETURNS a string and therefore
    #                        actually dispatches through `basic/strvar.asm`.
    # ⚠️ DERIVED FROM `kwtable.inc`, NOT FROM HOW THE CALLER SPELLED IT. The CLI
    # takes the equate stem (`MKI`, because the equate is `MKI_TOKEN`) while the
    # table holds the real name (`MKI$`), so testing the argument would have made
    # the guard depend on which entry point was used — green from `--allfn`, a
    # refusal from the command line, for the same keyword and the same ROM.
    strok = tok in _string_selectors()
    hits = []
    for i in range(len(rom) - 4):
        if rom[i] != 0xFE or rom[i + 1] != tok:
            continue
        op = rom[i + 2]
        # ⚠️ THE OPCODE IS NOT THE GUARD — THE KEYWORD IS (D-KWSTRCUT2). Tying
        # `str_*` to `jr z` alone looked conservative and was simply wrong about
        # the code: `str_func_ff` (basic/str-engine.asm:991) tests its selectors
        # with the SAME `cp <TOK>` chain, reaching CHR$ and STR$ by `jr z` and
        # LEFT$/RIGHT$/MID$/HEX$/OCT$/BIN$/SPACE$ by `jp z` — purely a matter of
        # which targets sit within a relative jump's reach. So the five that got
        # through were exactly the `jr z` ones and the seven that refused were
        # exactly the `jp z` ones, and that had NOTHING to do with dispatch shape.
        # The namespace collision is held off by `strok` (a string-returning
        # selector, from kwtable.inc), which the opcode restriction never helped
        # with: INT is not string-returning, so no `str_*` target is admitted for
        # it under either opcode.
        if op == 0xCA:                      # jp z,nn
            tgt = rom[i + 3] | (rom[i + 4] << 8)
        elif op == 0x28:                    # jr z,d (relative)
            d = rom[i + 3]
            tgt = (i + 4) + (d - 256 if d > 127 else d)
        else:
            continue
        nm = byaddr.get(tgt, "")
        # 🔴 `jr z` IS UNTIED FOR THE STRING CHAIN ONLY, AND PEEK IS WHY. Untying
        # it for `ev_` targets too looked like symmetry and reintroduced the very
        # false BLIND this guard exists to stop. PEEK ($97) has exactly ONE
        # `cp`-site: a `jr z` to `ev_ff_ckaddr` — a SHARED ADDRESS-CHECK HELPER,
        # not PEEK's own evaluator. Rejected, `plant_fn` declines and PEEK falls
        # through to the `ev_ff_argtab` cpir cut, which IS its dispatch and cuts
        # correctly. Accepted, the knife cuts the shared helper, PEEK keeps working,
        # and the run calls the row BLIND. [[a-shared-tail-is-not-a-decision]]
        # The expr.asm selector chain is a `jp z` chain BY CONSTRUCTION (this
        # function's own opening note: a `jr` to the error tail would usually be out
        # of range), so an `ev_` symbol reached by `jr z` is a helper, not a
        # selector. `str_func_ff` genuinely uses BOTH, which is the whole asymmetry.
        # 🔪 THE FOURTH CUT SHAPE (D-KWMATHCUT 2026-09-14), and like the third it
        # was never a mystery -- `ev_ff_mathconv` (basic/expr.asm:1698) dispatches
        # the arithmetic conversions with the SAME `cp <TOK>` / `jp z,<target>`
        # chain as every other selector, but its targets are named `evmc_*`, and
        # `evmc_abs` does not start with `ev_`. One prefix, and ABS/SGN/INT/FIX/
        # CINT/CSNG/CDBL/SQR/EXP/LOG had no cut at all.
        # 🔴 AND THE NAMESPACE GUARD STILL HOLDS, WHICH IS WHY THIS IS SAFE TO
        # WIDEN. `$86` really is in BOTH namespaces -- `ABS_TOKEN equ $86` and
        # `DIM_TOKEN equ $86` sit 53 lines apart in sysvars.inc -- so a raw byte
        # search cannot tell them apart. But DIM dispatches through stmt_table's
        # `db token / dw handler` entry, NOT through a `cp $86` followed by a
        # `jp z` to an `evmc_*` symbol, and the 23 `evmc_*` symbols exist ONLY in
        # the math chain. The `jp z` restriction is kept for the same reason it was
        # kept for `ev_`: the selector chain is a `jp z` chain by construction, so
        # an `evmc_` symbol reached by `jr z` would be a helper, not a selector.
        ok = ((nm.startswith("ev_") or nm.startswith("evmc_")) and op == 0xCA) \
            or (strok and nm.startswith("str_"))
        if ok:
            hits.append(i)
    if len(hits) != 1:
        shape = "ev_*/evmc_*" + ("/str_*" if strok else "")
        return None, (f"{len(hits)} `cp ${tok:02X}` site(s) with a {shape} "
                      f"target — refusing")
    off = hits[0] + 1
    orig = bytes(rom[off:off + 1])
    rom[off] = DEADTOK
    io.open(ROM, "wb").write(bytes(rom))
    if io.open(ROM, "rb").read()[off] != DEADTOK:
        sys.exit("knife: the function plant did NOT take — nothing was measured")
    return (off, orig), None


def plant(tok, dead):
    """Point the statement's table entry at `dead`. Returns (offset, original)."""
    s = syms()
    base = s["stmt_table"]
    rom = bytearray(io.open(ROM, "rb").read())
    for i in range(0, 3 * 120, 3):
        if rom[base + i] == tok:
            off = base + i + 1
            orig = bytes(rom[off:off + 2])
            rom[off] = dead & 0xFF
            rom[off + 1] = dead >> 8
            io.open(ROM, "wb").write(bytes(rom))
            # 🔴 READ IT BACK: an unplanted knife and a keyword with no defect
            # report identically, so the plant is proved before the run.
            back = io.open(ROM, "rb").read()[off:off + 2]
            if back != bytes([dead & 0xFF, dead >> 8]):
                sys.exit("knife: the plant did NOT take — nothing was measured")
            return off, orig
    sys.exit(f"knife: token ${tok:02X} is not in stmt_table — nothing was measured")

def install(before=None):
    """Re-install, and PROVE the images moved when a cut is in place.

    🔴 Verifying the bytes I wrote is not enough: the probe reads the INSTALLED
    machine, and an install that silently did not happen reports exactly like a
    keyword with nothing to find. `knife_guard.hashes()` is the shared
    implementation the tree already uses for this, and `knife-guard-check` refuses
    a runner that invokes repack-machine without it -- it refused THIS one, and was
    right [[a-knife-can-be-inert-because-the-build-did-not-happen]]."""
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "install-repack-machine.py"),
                    "--merged", ROM, "--disk-rom", os.path.join(ROOT, "build", "disk.rom"),
                    "--sub-rom", os.path.join(ROOT, "build", "sub.rom")],
                   check=True, capture_output=True)
    after = knife_guard.hashes()
    if before is not None and not knife_guard.moved(before, after):
        sys.exit("knife: the installed images did NOT move -- nothing was measured")
    return after

SWEEP_PIN = os.path.join(ROOT, "build", "kwsweep-verdicts.json")


def run_row(row):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "probes", "basic", "basic_probe_kwsweep.py"),
                        "--zb-machine", "C-BIOS_MSX1_EU_REPACK_DISK", "--only", row],
                       capture_output=True, text=True)
    for line in r.stdout.split("\n"):
        if line.startswith(("SUPPORTED", "DIVERGENT", "MISSING", "SILENT-GAP", "UNREADABLE")):
            return line.split()[0]
    # 🔴 D-KNIFENOREAD (2026-09-24): SAY WHY, because this verdict proves nothing
    # and used to be scored as proof (see NO_READING below).
    tail = [l for l in (r.stdout + r.stderr).split("\n") if l.strip()][-4:]
    print("      (no verdict from the sweep; rc=%d; tail: %s)" % (r.returncode, " | ".join(tail)))
    return "NO-VERDICT"


# 🔴 D-KNIFENOREAD (2026-09-24): A CUT THAT PRODUCED NO READING IS NOT A CUT THAT
# WAS NOTICED. `connected` and the console flag both used `v != "SUPPORTED"`, so
# NO-VERDICT -- the sweep printed no verdict at all -- counted as LOAD-BEARING.
# Measured: the D-BUFMERGE chain's knife run read NO-VERDICT on EVERY cut and
# pinned the whole statement set "knife-proven"; the next healthy run read real
# MISSING/DIVERGENT/UNREADABLE verdicts and exactly the four explained BLIND
# rows. An inert knife must never look like a sharp one
# [[a-knife-can-be-inert-because-the-build-did-not-happen]].
NO_READING = ("NO-VERDICT",)
_no_reading = []

WEAK = {}
# 🔴 THE PIN LIVES IN `scratchpad/`, TRACKED, AND NOT IN `build/` — MEASURED
# 2026-09-13 (D-KWPINLOSS). It sat in gitignored `build/` until a `make kwcover`
# run (which forces gates-full, and cleans) DESTROYED it. The reading it held —
# 94 keywords knifed, 91 connected — cost real machine time and was gone without
# a word; the pin came back holding ONE row. `build/kwsweep-verdicts.json` may
# live in `build/` because EVERY battery regenerates it. Nothing regenerates
# this one, and that asymmetry is what decides where a pin belongs.
PIN = os.path.join(ROOT, "scratchpad", "kwknife-connected.json")


def _row_subject(row):
    """The STATEMENT a sweep row is about -- `tier_table.stmt_subject`, honouring a
    row's own `SUBJECT:` tag. Returns None when it cannot be derived, so a pin
    written without the sweep importable simply carries no subject rather than a
    guess."""
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
        import tier_table, basic_probe_kwsweep as sweep
        kwset = set(tier_table.kwtable_keywords())
        for r in sweep.SWEEP:
            if r[0] == row:
                return tier_table.stmt_subject(r[1], kwset,
                                               sweep.row_subject(r[4]))
    except Exception:
        return None
    return None


def record(kw, row, verdict, mode):
    """MERGE this keyword's reading into scratchpad/kwknife-connected.json.

    🔴 A PIN, NOT A PARSE OF MY OWN CONSOLE OUTPUT. `tier_table` reads
    build/kwsweep-verdicts.json the same way, and a reader that scrapes a report's
    prose breaks the moment the report is reworded — the tree has been bitten by
    instruments that re-implement a consumer's parser. MERGED rather than
    overwritten so a statement sweep and a later `--fn` run accumulate instead of
    replacing one another.
    ⚠️ The ROM fingerprint rides along: a pin whose fingerprint no longer matches
    the built ROM describes a machine that no longer exists, and the reader says so
    rather than quietly reporting stale connectedness."""
    import json, time
    try:
        pin = json.load(open(PIN, encoding="utf-8"))
    except (OSError, ValueError):
        pin = {"rows": {}}
    pin["written"] = time.strftime("%Y-%m-%d %H:%M:%S")
    pin["rom_fingerprint"] = knife_guard.hashes()
    # 🔴 CONNECTED IS "ANY CUT NOTICED", NOT "THE LAST CUT NOTICED". A keyword can
    # have both a statement and a function dispatch, and its ROW exercises only one
    # of them -- so the other cut legitimately changes nothing. Measured 2026-09-13:
    # the function sweep proved BASE, TIME and VDP connected, then the statement
    # sweep overwrote their entries with its own SUPPORTED result and the pin
    # reported them unconnected. Per-mode verdicts are kept and `connected` is their
    # OR, so sweep ORDER can no longer change the answer.
    row_rec = pin.setdefault("rows", {}).setdefault(
        kw, {"row": row, "modes": {}, "weak": bool(WEAK.get(row))})
    row_rec["row"] = row
    row_rec["weak"] = row_rec.get("weak") or bool(WEAK.get(row))
    row_rec.setdefault("modes", {})[mode] = verdict
    row_rec["connected"] = any(v != "SUPPORTED" and v not in NO_READING
                               for v in row_rec["modes"].values())
    row_rec["verdict"] = verdict
    # 🎚️ D-KWSTMTDEN (Joost, 2026-09-14: composites "should have the same TIER and
    # tests"). THE PIN IS KEYED BY THE KEYWORD THIS RUN CUT, WHICH IS NOT ALWAYS
    # THE STATEMENT THE ROW IS ABOUT. Cutting `ON` makes `ongoto` go red, and that
    # row's subject is `ON GOTO` -- so the cut proves the COMPOSITE load-bearing,
    # and the pin threw that away by recording only `ON`.
    # 🔴 `USING` IS WHY THIS HAS TO EXIST AT ALL: its token $E4 is not in
    # stmt_table, so `PRINT USING` can never be connected by cutting a keyword of
    # its own. It can only ever be connected through the cut its own row responds
    # to, which is exactly what this field records.
    subj = _row_subject(row)
    row_rec["subject"] = subj
    # 🔴 AND THE SUBJECT ALSO GOES IN A MAP OF ITS OWN, BECAUSE `rows` IS KEYED BY
    # KEYWORD AND THE LAST CUT WINS. Measured 2026-09-14: `ON:ongoto`,
    # `ON:ongosub` and `ON:onkw` all write the key `ON`, so two of the three
    # composites vanished; and `PRINT:using` OVERWROTE PRINT's own reading with
    # `PRINT USING`'s -- the exact hazard `_warn_row_subject` warns about, now
    # happening by design rather than by mistake.
    # 🎯 A subject entry is never overwritten by a DIFFERENT subject, so one
    # keyword can speak for several statements and each keeps its own verdict.
    if subj:
        subs = pin.setdefault("subjects", {})
        rec = subs.setdefault(subj, {"rows": {}})
        rec["rows"][row] = verdict
        rec["connected"] = any(v != "SUPPORTED" for v in rec["rows"].values())
    os.makedirs(os.path.dirname(PIN), exist_ok=True)
    # 🔴 CLOSE THE FILE. `json.dump(..., open(...))` leaves the handle to the
    # garbage collector: `open(...,"w")` truncates AT ONCE, so an unflushed buffer
    # means the next read finds an empty file, the merge silently restarts from
    # scratch, and a pin that held 77 keywords comes back holding 12.
    with open(PIN, "w", encoding="utf-8") as fh:
        json.dump(pin, fh, indent=1, sort_keys=True)


def enumerate_targets():
    """Every statement keyword in stmt_table, paired with the kwsweep row that
    claims it -- read from the TABLE and from the SWEEP, never hand-listed.

    🔴 THE KEYWORD-PER-ROW MAPPING IMPORTS `tier_table.stmt_keyword`, the
    CONSUMER'S OWN parser. An ad-hoc regex here would be silent-failure mode 4:
    the last one admitted a bare `A` as a keyword and hid a real miss. The table
    ends at a $00 token, which `es_scan` itself uses as its sentinel."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
    import tier_table
    import basic_probe_kwsweep as sweep
    kwset = set(tier_table.kwtable_keywords())
    # 🔴 TOKEN BYTES COLLIDE between statement tokens and the $FF-prefixed FUNCTION
    # selectors, so scanning sysvars.inc's `<NAME>_TOKEN equ` lines maps a byte to
    # whichever equate comes first -- the dry run listed EXP, SIN, ATN and ASC as
    # statements. kwtable.inc is authoritative and says which is which: an entry
    # `db len,"NAME",1,TOK` is a ONE-BYTE statement token, while `db len,"NAME",2,
    # PEEK_PREFIX,TOK` is a function.
    eq = {}
    for m in re.finditer(r"^(\w+)\s+equ\s+\$([0-9A-Fa-f]+)",
                         io.open(os.path.join(ROOT, "basic", "sysvars.inc"),
                                 encoding="utf-8").read(), re.M):
        eq[m.group(1)] = int(m.group(2), 16)
    tok2kw = {}
    for m in re.finditer(r'db\s+\d+,"([^"]+)",1,(\w+)',
                         io.open(os.path.join(ROOT, "basic", "kwtable.inc"),
                                 encoding="utf-8").read()):
        t = eq.get(m.group(2))
        if t is not None:
            tok2kw[t] = m.group(1)
    # keyword -> the row that is ABOUT it. Several rows can credit one keyword --
    # `PRINT TAB(..)` credits PRINT -- so prefer a row whose KEY names the keyword
    # and fall back to the first crediting row, rather than taking sweep order.
    kw2row, kw2any = {}, {}
    for row in sweep.SWEEP:
        key, body = row[0], row[1]
        if row[2] is None:                      # crunch-only: nothing to knife
            continue
        kw = tier_table.stmt_keyword(body, kwset)
        if not kw:
            continue
        # 🔴 A `WEAK:` ROW IS ALREADY EXCLUDED FROM THE SWEEP'S OWN TALLY, so the
        # knife must not report it as a discovery. Measured 2026-09-13: the `time`
        # row came back SUPPORTED under the knife and its note ALREADY said why --
        # "absent => variable TI, always 0, and `0>=0` is STILL true". The knife
        # rediscovering a documented weakness is a good sign for the knife and NOT
        # a new finding; labelling it BLIND would double-count a known one.
        note = row[4] if len(row) > 4 else ""
        WEAK[key] = note.startswith("WEAK:")
        kw2any.setdefault(kw, key)
        base = kw.lower().rstrip("$")
        if kw not in kw2row and (key == base or key.startswith(base)):
            kw2row[kw] = key
    for kw, key in kw2any.items():
        kw2row.setdefault(kw, key)
    rom = io.open(ROM, "rb").read()
    base = syms()["stmt_table"]
    out, i = [], 0
    while True:
        tok = rom[base + i * 3]
        if tok == 0:
            break
        kw = tok2kw.get(tok)
        if kw and kw in kw2row:
            # 🔴 CARRY THE TOKEN. It was re-derived later from the keyword NAME as
            # `<NAME>_TOKEN`, which cannot work for `DSKO$` / `DSKI$` / `ATTR$` --
            # the `$` is not an identifier character -- and the run EXITED on the
            # first one instead of skipping it, losing the remaining 51 keywords.
            # The enumeration already resolved the byte; nothing should look it up
            # a second time by a different route.
            out.append((kw, kw2row[kw], tok))
        i += 1
    return out, i

def enumerate_fn_targets():
    """Every FUNCTION keyword (a 2-byte `$FF <sel>` token in kwtable.inc) paired
    with the kwsweep row that claims it.

    🔴 TWO DISPATCH SHAPES, TWO CUTS. Most selectors are tested by a `cp <SEL>` /
    `jp z,<handler>` chain in expr.asm, which `plant_fn` cuts by changing the
    comparison operand. The single-numeric-argument group instead lives in
    `ev_ff_argtab` and is matched by `cpir` — there is no `cp` to patch, so the cut
    is the TABLE BYTE itself. A keyword reachable by neither is reported, never
    guessed at."""
    tg, _ = enumerate_targets()          # reuse the row mapping; ignore its stmt list
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
    import tier_table
    import basic_probe_kwsweep as sweep
    kwset = set(tier_table.kwtable_keywords())
    kw2row = {}
    for row in sweep.SWEEP:
        key, body = row[0], row[1]
        if row[2] is None:
            continue
        kw = tier_table.stmt_keyword(body, kwset)
        if not kw:
            continue
        WEAK[key] = (row[4] if len(row) > 4 else "").startswith("WEAK:")
        base = kw.lower().rstrip("$")
        if kw not in kw2row and (key == base or key.startswith(base)):
            kw2row[kw] = key
        kw2row.setdefault(kw, key)
    eq = {}
    for m in re.finditer(r"^(\w+)\s+equ\s+\$([0-9A-Fa-f]+)",
                         io.open(os.path.join(ROOT, "basic", "sysvars.inc"),
                                 encoding="utf-8").read(), re.M):
        eq[m.group(1)] = int(m.group(2), 16)
    out = []
    for m in re.finditer(r'db\s+\d+,"([^"]+)",2,\w+,(\w+)',
                         io.open(os.path.join(ROOT, "basic", "kwtable.inc"),
                                 encoding="utf-8").read()):
        kw, sel = m.group(1), eq.get(m.group(2))
        if sel is not None and kw in kw2row:
            out.append((kw, kw2row[kw], sel))
    # 🔴 AND THE TOKEN-FREE SUBJECTS, which this enumeration cannot reach: it
    # walks kwtable.inc, and a keyword with no table entry has none to walk.
    # They carry tok=None, which every token-keyed shape skips.
    # ⚠️ THEIR ROW CANNOT COME FROM `kw2row` EITHER, for the same reason -- that
    # map is keyed on `stmt_keyword` against the kwtable set. It comes from the
    # row's OWN `SUBJECT:` tag, which is how `INPUT$` is already attributed
    # everywhere else in the tree (tools/kwforms.py, tier_table).
    for kw in SUFFIX_CUTS:
        if any(o[0] == kw for o in out):
            continue
        for r in sweep.SWEEP:
            if r[2] is None or len(r) < 5:
                continue
            if sweep.row_subject(r[4]) == kw:
                out.append((kw, r[0], None))
                break
    return out


# 🔪 THE SEVENTH CUT SHAPE'S TABLE (D-KWSUFCUT 2026-09-16): keywords that have
# NO TOKEN AT ALL and are dispatched by a SUFFIX CHARACTER.
# 🔴 `INPUT$` IS THE WHOLE REASON. It was the last keyword `tier_table` held at
# TIER 0 "not knife-proven CONNECTED" with BOTH its forms agreeing -- and it is
# not merely uncut, it is structurally outside `enumerate_fn_targets`, which is
# driven by `kwtable_keywords()`. MSX tokenises `INPUT` and `$` SEPARATELY, so
# there is no `INPUT$` entry to enumerate and no token byte for any of the six
# token-keyed shapes to compare against (`tools/kwforms.py` says so in its own
# words). It is reached instead by a suffix test:
#     str_eval_maybe_inputd:  inc hl / ld a,(hl) / cp '$' / jr z,str_inputd
# 🎯 AND IT IS A DECLARED TABLE RATHER THAN A HEURISTIC, DELIBERATELY. Matching
# "a `cp <printable>` inside a routine whose name contains the stem" would sweep
# up `ex_input`, `input_common`, `str_inputd` and `str_inputd_read` as well --
# the same substring trap `plant_cp_named` records for LEN, where a length EQUATE
# ending in "len" nearly outranked the real site. Naming the routine is honest
# about being a mapping; guessing at it would be a shape that can be wrong.
SUFFIX_CUTS = {
    # keyword: (enclosing symbol, the suffix character its dispatch compares)
    "INPUT$": ("str_eval_maybe_inputd", ord("$")),
}


def plant_suffix(kw):
    """🔪 Cut a SUFFIX-dispatched keyword by patching the compared character.

    The `cp <char>` must live INSIDE the named routine and be followed by a
    conditional jump, and EXACTLY ONE site must qualify -- the same ambiguity
    rule every other shape carries. A missing symbol, a missing site or two
    sites all REFUSE; none of them guess.
    Patching the OPERAND rather than the jump fails safely: the suffix simply
    never matches and the caller falls to its own not-a-string-operand path,
    which for `INPUT$` is `str_eval_no` -> Syntax error. That is exactly what a
    row observing the keyword must notice."""
    ent = SUFFIX_CUTS.get(kw)
    if ent is None:
        return None, "no suffix-cut entry for this keyword"
    name, ch = ent
    st = syms().get(name)
    if st is None:
        return None, f"no `{name}` symbol"
    rom = bytearray(io.open(ROM, "rb").read())
    end = min(st + 64, len(rom) - 4)
    hits = [i for i in range(st, end)
            if rom[i] == 0xFE and rom[i + 1] == ch and rom[i + 2] in (0x28, 0xCA, 0x20, 0xC2)]
    if len(hits) != 1:
        return None, (f"{len(hits)} `cp ${ch:02X}` site(s) in {name} — refusing")
    off = hits[0] + 1
    orig = bytes(rom[off:off + 1])
    rom[off] = DEADTOK                  # a byte no suffix character can be
    io.open(ROM, "wb").write(bytes(rom))
    if io.open(ROM, "rb").read()[off] != DEADTOK:
        sys.exit("knife: the suffix plant did NOT take — nothing was measured")
    return (off, orig), f"suffix `cp ${ch:02X}` in {name} at ${off:04X}"


def plant_argtab(tok):
    """Cut a cpir-dispatched selector by removing its byte from `ev_ff_argtab`."""
    st = syms().get("ev_ff_argtab")
    ln = syms().get("ev_ff_argtab_len")
    if st is None or ln is None:
        return None, "no ev_ff_argtab symbols"
    rom = bytearray(io.open(ROM, "rb").read())
    where = [st + i for i in range(ln) if rom[st + i] == tok]
    if len(where) != 1:
        return None, f"{len(where)} occurrence(s) in ev_ff_argtab — refusing"
    off = where[0]
    orig = bytes(rom[off:off + 1])
    rom[off] = DEADTOK
    io.open(ROM, "wb").write(bytes(rom))
    if io.open(ROM, "rb").read()[off] != DEADTOK:
        sys.exit("knife: the argtab plant did NOT take — nothing was measured")
    return (off, orig), None


def plant_totaltab(tok):
    """🔪 THE FIFTH CUT SHAPE: the transcendentals' TOKEN-TABLE row (D-KWTOTALCUT
    2026-09-14).

    `ATN/SIN/COS/TAN/RND` have no `cp` arm of their own -- `ev_ff_mathconv`'s own
    comment says so: *"they have no arm of their own: they fall into the table scan
    below"*. `evmc_total_scan` walks `evmc_total_tab`, five rows of
    `<selector token>, <low byte of the sub-ROM entry>`, and a miss falls through
    to `ev_ff_strnum` and then `ev_f_err`.
    🎯 SO THE CUT IS THE SAME IDEA AS EVERY OTHER ONE HERE: patch the byte the
    comparison READS, never the target it jumps to. The row's token becomes
    DEADTOK, the scan never matches, and the function fails through its own error
    path -- no shared helper is disturbed and nothing else moves.
    ⚠️ The row STRIDE is 2 and the table length is `EVMC_TOTAL_N`, taken from the
    symbol rather than assumed, so a sixth row added later is cut correctly and a
    table that moved is refused rather than mis-patched."""
    st = syms().get("evmc_total_tab")
    if st is None:
        return None, "no evmc_total_tab symbol"
    n = syms_equ().get("EVMC_TOTAL_N")
    if n is None:
        # the equate is an `equ` in expr.asm, not sysvars.inc -- read it there
        m = re.search(r"^EVMC_TOTAL_N\s+equ\s+(\d+)",
                      io.open(os.path.join(ROOT, "basic", "expr.asm"),
                              encoding="utf-8").read(), re.M)
        n = int(m.group(1)) if m else None
    if not n:
        return None, "no EVMC_TOTAL_N"
    rom = bytearray(io.open(ROM, "rb").read())
    where = [st + 2 * i for i in range(n) if rom[st + 2 * i] == tok]
    if len(where) != 1:
        return None, f"{len(where)} row(s) in evmc_total_tab — refusing"
    off = where[0]
    orig = bytes(rom[off:off + 1])
    rom[off] = DEADTOK
    io.open(ROM, "wb").write(bytes(rom))
    if io.open(ROM, "rb").read()[off] != DEADTOK:
        sys.exit("knife: the total-tab plant did NOT take — nothing was measured")
    return (off, orig), None


def _enclosing(off):
    """The name of the symbol the ROM offset `off` sits inside -- the greatest
    symbol address not past it. Used to decide whether a `cp <tok>` site BELONGS
    to a keyword when no jump target can say so."""
    best, bestn = -1, ""
    for line in io.open(SYM, errors="replace"):
        m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m:
            a = int(m.group(2), 16)
            if best < a <= off:
                best, bestn = a, m.group(1)
    return bestn


def plant_cp_named(tok, kw):
    """🔪 THE SIXTH CUT SHAPE: a `cp <tok>` whose ENCLOSING ROUTINE is named after
    the keyword (D-KWOPCUT 2026-09-14).

    🔴 THE EXISTING RULE IS "A CONDITIONAL JUMP MUST FOLLOW, AND ITS TARGET MUST
    RESOLVE TO A NAMED EVALUATOR", and three real dispatch shapes satisfy neither
    half:
      * `MOD` is `cp MOD_TOKEN` / **`ret nz`** (basic/expr.asm, ev_mod_lp) -- no
        jump at all;
      * `NOT` is `cp NOT_TOKEN` / `jr z,ev_not_do` -- a `jr`, which the `ev_*` arm
        deliberately refuses after the PEEK lesson;
      * `ASC`/`LEN` are `jr z,ev_ff_asc` / `jr z,ev_ff_len` in `ev_ff_strnum`.
    🎯 SO THE SITE IS IDENTIFIED BY WHERE IT LIVES INSTEAD OF WHERE IT GOES: the
    enclosing symbol must NAME the keyword. `ev_mod_lp` names MOD, `ev_not` names
    NOT, `ev_ff_strnum` does not name ASC -- but the JUMP TARGET does, so both are
    accepted and either alone is enough.
    🔴 AND THIS IS EXACTLY THE GUARD THE PEEK CASE NEEDED. PEEK's lone `jr z` goes
    to `ev_ff_ckaddr`, a SHARED ADDRESS-CHECK HELPER, inside `ev_ff_arg` -- neither
    name contains "peek", so this shape declines and PEEK still falls through to
    the `ev_ff_argtab` cut that IS its dispatch. A shared tail is not a decision
    [[a-shared-tail-is-not-a-decision]].
    ⚠️ Tried LAST, after every narrower shape, so no existing reading can move."""
    stem = kw.rstrip("$").lower()
    if len(stem) < 2:
        return None, "keyword stem too short to match a symbol"
    rom = bytearray(io.open(ROM, "rb").read())
    byaddr = {}
    for line in io.open(SYM, errors="replace"):
        m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m:
            byaddr[int(m.group(2), 16)] = m.group(1)
    hits = []
    for i in range(len(rom) - 4):
        if rom[i] != 0xFE or rom[i + 1] != tok:
            continue
        names = [_enclosing(i)]
        op = rom[i + 2]
        if op == 0xCA:
            names.append(byaddr.get(rom[i + 3] | (rom[i + 4] << 8), ""))
        elif op == 0x28:
            d = rom[i + 3]
            names.append(byaddr.get((i + 4) + (d - 256 if d > 127 else d), ""))
        # 🔴 A JUMP TARGET NAMING THE KEYWORD OUTRANKS AN ENCLOSING SYMBOL THAT
        # MERELY CONTAINS IT, and LEN is why. `$92`'s two candidate sites were the
        # real one (`jr z,ev_ff_len`) and a byte coincidence sitting near
        # `ev_ff_argtab_len` -- a LENGTH EQUATE, not a routine, whose name ends in
        # "len" by pure English. Substring matching cannot tell those apart and
        # correctly REFUSED rather than guess; ranking can, because only one of
        # them is something the code JUMPS TO.
        by_target = len(names) > 1 and names[1] and stem in names[1].lower()
        if by_target or any(stem in n.lower() for n in names if n):
            hits.append((i, by_target))
    strong = [h for h in hits if h[1]]
    hits = [h[0] for h in (strong or hits)]
    if len(hits) != 1:
        return None, (f"{len(hits)} `cp ${tok:02X}` site(s) named for {kw} "
                      f"— refusing")
    off = hits[0] + 1
    orig = bytes(rom[off:off + 1])
    rom[off] = DEADTOK
    io.open(ROM, "wb").write(bytes(rom))
    if io.open(ROM, "rb").read()[off] != DEADTOK:
        sys.exit("knife: the named-cp plant did NOT take — nothing was measured")
    return (off, orig), None


def plant_logtab(tok):
    """🔪 THE SEVENTH: the LOGICAL-OPERATOR precedence table (D-KWOPCUT).

    `logtab` (basic/expr.asm) is `db token, dw leaf`, $00-terminated, loosest
    first: IMP, EQV, XOR, OR, AND. The operators are not reached by a `cp` chain
    at all -- the parser WALKS this table -- so the cut is the row's token byte,
    the same "patch what the comparison reads" idea as every other shape here.
    ⚠️ STRIDE 3, and the walk stops at a $00 token, so DEADTOK ($FE) is a safe
    poison: it terminates nothing and matches nothing."""
    st = syms().get("logtab")
    if st is None:
        return None, "no logtab symbol"
    rom = bytearray(io.open(ROM, "rb").read())
    where, i = [], 0
    while i < 64 and rom[st + i] != 0x00:
        if rom[st + i] == tok:
            where.append(st + i)
        i += 3
    if len(where) != 1:
        return None, f"{len(where)} row(s) in logtab — refusing"
    off = where[0]
    orig = bytes(rom[off:off + 1])
    rom[off] = DEADTOK
    io.open(ROM, "wb").write(bytes(rom))
    if io.open(ROM, "rb").read()[off] != DEADTOK:
        sys.exit("knife: the logtab plant did NOT take — nothing was measured")
    return (off, orig), None


FNMODE = "--fn" in sys.argv
if FNMODE:
    sys.argv = [a for a in sys.argv if a != "--fn"]
TARGETS = None
if len(sys.argv) > 1 and sys.argv[1] == "--list":
    tg, n = enumerate_targets()
    print(f"stmt_table holds {n} entries; {len(tg)} have a kwsweep row to knife\n")
    for kw, row, tok in tg:
        print("   %-10s %-12s $%02X" % (kw, row, tok))
    sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1] == "--allfn":
    TARGETS = enumerate_fn_targets()
    FNMODE = True
elif len(sys.argv) > 1 and sys.argv[1] == "--all":
    TARGETS, _ = enumerate_targets()
elif len(sys.argv) > 1:
    TARGETS = [tuple(a.split(":")) for a in sys.argv[1:]]
else:
    TARGETS = [("POKE", "pokekw", 0x98), ("VPOKE", "vpoke", 0xC6)]
def _kwtable_name(tok, fallback):
    """The name `kwtable.inc` gives a function selector, e.g. $81 -> "LEFT$".

    🔴 THE CLI TAKES THE EQUATE STEM AND THE PIN MUST NOT. The equate for LEFT$ is
    `LEFTD_TOKEN`, so the command line says `LEFTD:left` — and recording that stem
    wrote a key NOTHING reads: `tier_table` matches pin keys against kwtable
    keywords, where the word is `LEFT$`. Measured 2026-09-13: a CLI run left
    BIND/HEXD/LEFTD/MIDD/OCTD/RIGHTD/SPACED in the pin beside the real names —
    seven entries contributing no evidence to the keyword they were measured for,
    while still inflating the row count that `knife_connected`'s floor reads. A pin
    key is a keyword or it is noise, so the name is normalised at the source.

    🔴 AND THE **PREFIX** IS PART OF THE IDENTITY, WHICH THIS IGNORED (D-KWMATHCUT
    2026-09-14). A two-byte entry is `<prefix>,<token>`, and two of them can share
    the TOKEN while differing in the PREFIX: `kwtable.inc` holds
    `db 4,"ELSE",2,COLON,ELSE_TOKEN` and `db 3,"FIX",2,PEEK_PREFIX,FIX_TOKEN`,
    and `ELSE_TOKEN` and `FIX_TOKEN` are BOTH `$A1`. Matching on the token alone
    returned whichever appears first in the file, so a `--fn FIX:fix` cut was
    recorded in the pin under **ELSE** -- a keyword it has nothing to do with, and
    one that is a PARTICLE and therefore scored for nobody at all.
    ⚠️ Same shape as every mis-attribution this sweep has turned up, one level
    down: the byte is not the keyword. In function mode the prefix must be the
    `$FF` one."""
    src = io.open(os.path.join(ROOT, "basic", "kwtable.inc"),
                  encoding="utf-8").read()
    eq = syms_equ()
    hits = [(m.group(1), m.group(2), m.group(3))
            for m in re.finditer(r'db\s+\d+,"([^"]+)",2,(\w+),(\w+)', src)
            if eq.get(m.group(3)) == tok]
    if not hits:
        return fallback
    ff = [h for h in hits if eq.get(h[1]) == 0xFF]
    if FNMODE and ff:
        return ff[0][0]
    if len(hits) > 1 and not ff:
        print(f"  \u26a0\ufe0f  token ${tok:02X} names {len(hits)} kwtable entries "
              f"({', '.join(h[0] for h in hits)}) and none is $FF-prefixed -- "
              f"recording the first")
    return hits[0][0]


def syms_equ():
    eq = {}
    for m in re.finditer(r"^(\w+)\s+equ\s+\$([0-9A-Fa-f]+)",
                         io.open(os.path.join(ROOT, "basic", "sysvars.inc"),
                                 encoding="utf-8").read(), re.M):
        eq[m.group(1)] = int(m.group(2), 16)
    return eq


def _warn_row_subject(kw, row):
    """Warn when a CLI pair names a row whose SUBJECT is a DIFFERENT keyword.

    🔴 THE PIN IS MERGED BY KEYWORD, SO A WRONG PAIR OVERWRITES A GOOD READING.
    Measured 2026-09-14: `GOSUB:ongosub` recorded GOSUB as connected=False with
    row='ongosub', silently replacing the full sweep's correct `gosubkw` result --
    because `ON n GOSUB` is dispatched ENTIRELY by ON's handler (it consumes the
    GOSUB token inline) so cutting GOSUB's stmt_table entry changes nothing and the
    run reports 🔴 BLIND. That verdict was about the PAIRING, not the row.
    🎯 A BLIND VERDICT CAN MEAN "YOU CUT THE WRONG KEYWORD FOR THIS ROW". The row's
    subject is what `tier_table.stmt_keyword` says it is, and a mismatch is worth
    saying out loud rather than writing into the pin unremarked."""
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
        import tier_table, basic_probe_kwsweep as sweep
        kwset = set(tier_table.kwtable_keywords())
        for r in sweep.SWEEP:
            if r[0] == row:
                # 🎚️ D-KWSTMTDEN: `stmt_subject`, not `stmt_keyword`. A row whose
                # SUBJECT is a composite (`PRINT:using` -> `PRINT USING`) is a
                # CORRECT pairing -- cutting PRINT is the only way that composite
                # can be shown load-bearing -- and warning on it trained the eye
                # to ignore the warning that matters.
                subj = tier_table.stmt_subject(r[1], kwset,
                                               sweep.row_subject(r[4]))
                if subj and kw.rstrip("$") not in subj.split():
                    print(f"  \u26a0\ufe0f  row {row} is ABOUT {subj}, not {kw} -- a BLIND "
                          f"verdict here would be about the PAIRING, and the pin is "
                          f"merged BY KEYWORD so it would overwrite {kw}'s real "
                          f"reading")
                return
    except Exception:
        return


if TARGETS and len(TARGETS[0]) == 2:        # explicit KW:row pairs on the command line
    TARGETS = [(_kwtable_name(token_of(k), k) if FNMODE else k, r, token_of(k))
               for k, r in TARGETS]
    for _k, _r in [(t[0], t[1]) for t in TARGETS]:
        _warn_row_subject(_k, _r)

# 🔴 THE KNIFE DESTROYS THE PIN IT DEPENDS ON, unless this guard exists. Each cut
# runs `basic_probe_kwsweep --only <row>`, and the sweep WRITES
# build/kwsweep-verdicts.json every run — so a single-row invocation replaces the
# whole-battery pin with ONE row. Measured 2026-09-13: after a knife session the
# pin held exactly `vdpkw`, and `tier_table` (which reads that pin for evidence)
# silently lost every other keyword's verdict. The pin is saved before the first
# cut and restored after the last, whatever happens in between.
_sweep_pin_backup = None
if os.path.exists(SWEEP_PIN):
    _sweep_pin_backup = io.open(SWEEP_PIN, "rb").read()
import atexit
@atexit.register
def _restore_sweep_pin():
    if _sweep_pin_backup is not None:
        io.open(SWEEP_PIN, "wb").write(_sweep_pin_backup)


@atexit.register
def _force_clean_rom():
    """🔴 A KNIFE'S WRITE DEFEATS `make`'s UP-TO-DATE CHECK, and that is worse than
    it sounds. Writing build/zerobas-main-eu.rom makes the artifact NEWER than its
    sources, so a later `make repack-machine` does nothing and the tree keeps a
    KNIFED machine while every command reports success. Measured 2026-09-13: after
    an interrupted run the installed main ROM was 63721706 where a clean build
    gives e3dbed36, and `make repack-machine` would not replace it. The battery's
    own fingerprint line was the only thing that showed it.
    So the ROM is DELETED and rebuilt at exit -- once per session, not per cut --
    and the machine re-installed from those canonical bytes."""
    try:
        os.remove(ROM)
    except OSError:
        pass
    subprocess.run(["make", "repack-machine"], cwd=ROOT, capture_output=True)

dead = syms()["stmt_error"]
print("knife: statement handlers -> stmt_error $%04X; a row still SUPPORTED is BLIND\n" % dead)
for kw, row, tok in TARGETS:
    before = knife_guard.hashes()
    if FNMODE:
        # 🔴 A TOKEN-FREE SUBJECT DECLINES EVERY TOKEN-KEYED SHAPE BY CONSTRUCTION
        # rather than by each one happening to miss: `tok is None` cannot be
        # compared against a ROM byte, and a shape that quietly treated None as 0
        # would cut whatever happens to hold a zero operand.
        res = None
        why = why2 = why3 = why4 = why5 = why6 = "not tried"
        if tok is not None:
            res, why = plant_fn(tok, kw)
            if res is None:                  # no `cp` site: try the cpir table
                res, why2 = plant_argtab(tok)
            if res is None:                  # nor that: the transcendental table
                res, why3 = plant_totaltab(tok)
            if res is None:                  # nor that: the operator precedence table
                res, why4 = plant_logtab(tok)
            if res is None:                  # a `cp` site NAMED for the keyword
                res, why5 = plant_cp_named(tok, kw)
        else:
            why = "no token -- every token-keyed shape skipped"
        if res is None:                      # LAST: a SUFFIX-dispatched keyword
            res, why6 = plant_suffix(kw)     # (no token at all -- see SUFFIX_CUTS)
            if res is None:
                print("  %-8s row %-10s %s / %s / %s / %s / %s / %s"
                      % (kw, row, why, why2, why3, why4, why5, why6)); continue
        off, orig = res
    else:
        off, orig = plant(tok, dead)
    try:
        install(before)
        v = run_row(row)
    finally:
        rom = bytearray(io.open(ROM, "rb").read())
        # 🔴 len(orig), NOT 2. The statement cut saves TWO bytes (the `dw`) and the
        # function/argtab cuts save ONE, so a hard-coded 2 replaced two bytes with
        # one -- SHORTENING the ROM and shifting every byte after it. Measured
        # 2026-09-13: the first function sweep cut EOF on a clean ROM and every
        # keyword after it was measured on a corrupted one, which is why PEEK was
        # reported missing from ev_ff_argtab when it is that table's FIRST byte.
        before_len = len(rom)
        rom[off:off + len(orig)] = orig
        assert len(rom) == before_len, "restore changed the ROM length"
        io.open(ROM, "wb").write(bytes(rom))
        install()
    record(kw, row, v, "fn" if FNMODE else "stmt")
    if v in NO_READING:
        _no_reading.append(kw)
    flag = ("⚠️ NO-READING (not proof)" if v in NO_READING
            else "LOAD-BEARING" if v != "SUPPORTED"
            else "WEAK (already excluded)" if WEAK.get(row) else "🔴 BLIND")
    print("  %-8s row %-10s knifed -> %-12s %s" % (kw, row, v, flag))
    sys.stdout.flush()

if _no_reading:
    print("\nknife: %d cut(s) produced NO READING -- they prove nothing and are NOT "
          "recorded as connected: %s" % (len(_no_reading), " ".join(_no_reading)))
    sys.exit(3)
