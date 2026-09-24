"""D-KWTDISK: kwtime times the DISK rows too, against the CF-3300. Anchored edits."""
import sys
f = 'probes/basic/basic_probe_kwtime.py'
s = open(f).read()
def rep(o, n):
    global s
    if s.count(o) != 1:
        sys.exit(f'REFUSE x{s.count(o)}: {o[:70]!r}')
    s = s.replace(o, n)

rep('''REF_FLOOR = 100''', '''REF_FLOOR = 100
# 💽 D-KWTDISK (2026-09-24): THE DISK ROWS ARE TIMED AGAINST THE CF-3300. The
# VG-8020 has no drive, so a disk verb has no time there at all; the CF-3300 is
# the reference kwsweep already scores those rows against, and it is the rule
# Joost ruled for the RAM rung -- *"prefer the vg8020"*, disk-only cells take
# the CF-3300. Its boot is ~6 s longer than the VG's (kwsweep's MACH_BOOT).
DISK_REF = "National_CF-3300"
DISK_REF_BOOT = 14.0''')

rep('''TIMED: dict = {}               # row key -> the declared timed occurrence, or None''',
'''TIMED: dict = {}               # row key -> the declared timed occurrence, or None
GROUP: dict = {}               # row key -> "plain" or "disk" (D-KWTDISK)''')

rep('''    Plain = no rig (disk/printer/tape/hold/plug), not an editor (`PROGRAM:`) row,
    not a `RESPOND:` row: those need machinery this shape does not drive, and a
    keyword whose only rows are rigged simply has no T2 reading yet."""
    out = []
    for key, _crunch, line, mode, note in kw.SWEEP:
        if line is None or kw._row_rigs(note) or kw.row_program(note) \\
                or kw.row_respond(note) or not kw.row_form(note):
            continue
        if only and key not in only:
            continue
        out.append((key, line, mode, row_keyword(_crunch, note)))''',
'''    Plain = no rig (printer/tape/hold/plug), not an editor (`PROGRAM:`) row,
    not a `RESPOND:` row: those need machinery this shape does not drive, and a
    keyword whose only rows are rigged simply has no T2 reading yet.
    💽 A row whose ONLY rig is the disk IS selected (D-KWTDISK) -- mounting a
    fresh image is all it needs -- and is timed in its own group against
    DISK_REF. A disk row with a SECOND rig (`lfiles`: disk + printer) is not."""
    out = []
    for key, _crunch, line, mode, note in kw.SWEEP:
        rigs = kw._row_rigs(note)
        if line is None or (rigs and rigs != ("disk",)) or kw.row_program(note) \\
                or kw.row_respond(note) or not kw.row_form(note):
            continue
        if only and key not in only:
            continue
        GROUP[key] = "disk" if rigs else "plain"
        out.append((key, line, mode, row_keyword(_crunch, note)))''')

rep('''def calibrate(machine):''', '''def group_kwargs(group, machine):
    """-> the extra run_cases kwargs a group needs on `machine`, built FRESH per
    call: the disk rig hands out a private copy of the test image each time, so
    the plain run and its twin both start from the image as shipped -- a row
    that KILLs or NAMEs a file cannot change what the next measurement sees."""
    if group != "disk":
        return {}
    extra = kw._rig_kwargs(("disk",))
    extra.pop("batch", None)
    if machine == DISK_REF:
        extra["boot"] = DISK_REF_BOOT
    return extra


def calibrate(machine, extra=None):''')

rep('''    omsx_repl.run_cases(machine, [("direct", lines)], batch=True, reset=(),
                        capture="screen", boot=8.0, sentinel=(MARK_ADDR, END),
                        settle_out=so, watch_values=((CURLIN_HI, 0xFF),))''',
'''    rk = dict(capture="screen", boot=8.0, sentinel=(MARK_ADDR, END),
              settle_out=so, watch_values=((CURLIN_HI, 0xFF),))
    rk.update(extra or {})
    omsx_repl.run_cases(machine, [("direct", lines)], batch=True, reset=(), **rk)''')

rep('''def measure(machine, rows, pad=None, twin=False, caps_out=None):''',
'''def measure(machine, rows, pad=None, twin=False, caps_out=None, extra=None):''')

rep('''    caps = omsx_repl.run_cases(machine, specs, batch=True, reset=(),
                               capture="screen", boot=8.0,
                               sentinel=(MARK_ADDR, END), settle_out=so,
                               watch_values=((CURLIN_HI, 0xFF),))''',
'''    rk = dict(capture="screen", boot=8.0, sentinel=(MARK_ADDR, END),
              settle_out=so, watch_values=((CURLIN_HI, 0xFF),))
    rk.update(extra or {})
    caps = omsx_repl.run_cases(machine, specs, batch=True, reset=(), **rk)''')

# main: per-group measurement
old_main = s[s.index('    fp_before = kw._rom_fingerprint()\n'):s.index('    timed = sum(1 for p in ref if p[0] is not None)\n')]
new_main = '''    fp_before = kw._rom_fingerprint()
    res = {}
    tally: dict = {}
    n_alone = 0
    n_curlin = 0
    timed = 0
    biases = {}
    print(f"{'row':16} {'ref ms':>9} {'zb ms':>9} {'zb/ref':>7} {'alone':>6}  status")
    for group, refm in (("plain", REF), ("disk", DISK_REF)):
        grows = [r for r in rows if GROUP[r[0]] == group]
        if not grows:
            continue
        rcap, zcap = [], []
        ref = measure(refm, grows, caps_out=rcap,
                      extra=group_kwargs(group, refm))
        zb = measure(a.zb_machine, grows, caps_out=zcap,
                     extra=group_kwargs(group, a.zb_machine))
        ref_t = measure(refm, grows, twin=True,
                        extra=group_kwargs(group, refm))
        zb_t = measure(a.zb_machine, grows, twin=True,
                       extra=group_kwargs(group, a.zb_machine))
        rfall, zfall = machine_bias(ref), machine_bias(zb)
        rend = calibrate(refm, group_kwargs(group, refm))
        zend = calibrate(a.zb_machine, group_kwargs(group, a.zb_machine))
        biases[group] = {"ref_machine": refm,
                         "ref": {"fall_off": rfall, "end_path": rend},
                         "zb": {"fall_off": zfall, "end_path": zend}}
        for side, b, e in (("ref", rfall, rend), ("zb", zfall, zend)):
            print(f"kwtime: [{group}] {side} CURLIN bias -- fall-off "
                  + ("none" if b[0] is None else
                     f"{b[0] * 1e3:.3f} ms (spread {b[1] * 1e3:.3f}..{b[2] * 1e3:.3f})")
                  + " · END path " + ("none" if e is None else f"{e * 1e3:.3f} ms"))
        rb, zbb = (rend,), (zend,)
        for (key, _l, _m, word), rp, zp, rtp, ztp, rc_, zc_ in zip(
                grows, ref, zb, ref_t, zb_t, rcap, zcap):
            if not curlin_ok(_l, (rc_, zc_)):
                # CURLIN is not the same event here (see DIRECT_RETURNERS)
                rp, zp, rtp, ztp = ((p[0], None) for p in (rp, zp, rtp, ztp))
            r, rv = resolve(rp, rb[0])
            z, zv = resolve(zp, zbb[0])
            rt, _ = resolve(rtp, rb[0])
            zt, _ = resolve(ztp, zbb[0])
            if rv and zv and rv != zv:
                # one side reached its end mark and the other only ended: the two
                # machines took DIFFERENT PATHS through the same program -- a
                # behaviour difference, never a timing
                st, r, z, rt, zt = "PATH-DIFFERS", None, None, None, None
            else:
                st = status(r, z)
                n_curlin += rv == "curlin" and st == "OK"
            tally[st] = tally.get(st, 0) + 1
            ratio = z / r if r and z else None
            al = alone(r, z, rt, zt)
            n_alone += al is not None
            res[key] = {"ref": r, "zb": z, "ratio": ratio, "status": st,
                        "via": rv if rv == zv else None,
                        "word": word, "form": FORMS.get(key),
                        "twin_ref": rt, "twin_zb": zt, "alone": al,
                        "ref_machine": refm}
            print(f"{key:16} {r * 1e3 if r else float('nan'):9.3f} "
                  f"{z * 1e3 if z else float('nan'):9.3f} "
                  f"{(f'{ratio:.2f}' if ratio else '-'):>7} "
                  f"{(f'{al:.2f}' if al else '~'):>6}  {st}"
                  + ("" if group == "plain" else f"  [{group}: {refm}]"))
        timed += sum(1 for p in ref if p[0] is not None)
    fp_after = kw._rom_fingerprint()
'''
s = s.replace(old_main, new_main)
rep('''    timed = sum(1 for p in ref if p[0] is not None)
''', '')
rep('''                       "curlin_bias": {"ref": {"fall_off": rfall, "end_path": rend},
                                       "zb": {"fall_off": zfall, "end_path": zend}}},''',
'''                       "curlin_bias": biases},''')
open(f, 'w').write(s)
print('ok')
