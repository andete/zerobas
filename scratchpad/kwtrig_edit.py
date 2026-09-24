"""D-KWTRIG: kwtime times single-rig printer and tape-write rows too. Anchored edits."""
import sys
f = 'probes/basic/basic_probe_kwtime.py'
s = open(f).read()
def rep(o, n):
    global s
    if s.count(o) != 1:
        sys.exit(f'REFUSE x{s.count(o)}: {o[:70]!r}')
    s = s.replace(o, n)

rep('''DISK_REF = "National_CF-3300"
DISK_REF_BOOT = 14.0''', '''DISK_REF = "National_CF-3300"
DISK_REF_BOOT = 14.0
# 🖨 D-KWTRIG (2026-09-24): the rigs a row may carry ALONE and still be timed.
# kwtime reads RAM marks, never the artefact, so a rig only has to be PRESENT:
# the printer plugged, a blank tape in the deck. ⚠️ `tape` (CLOAD) is left out
# ON PURPOSE: a CLOAD replaces the running program with the one it loads, so
# the end mark can never fire -- it would read UNTIMEABLE by construction after
# a 90 s leader per case, twice. `log`/hold/plug rows are not here yet.
TIMEABLE_RIGS = {("disk",): "disk", ("printer",): "printer", ("tapew",): "tapew"}''')

rep('''        rigs = kw._row_rigs(note)
        if line is None or (rigs and rigs != ("disk",)) or kw.row_program(note) \\
                or kw.row_respond(note) or not kw.row_form(note):
            continue
        if only and key not in only:
            continue
        GROUP[key] = "disk" if rigs else "plain"''',
'''        rigs = kw._row_rigs(note)
        if line is None or (rigs and rigs not in TIMEABLE_RIGS) \\
                or kw.row_program(note) \\
                or kw.row_respond(note) or not kw.row_form(note):
            continue
        if only and key not in only:
            continue
        GROUP[key] = TIMEABLE_RIGS[rigs] if rigs else "plain"''')

rep('''    if group != "disk":
        return {}
    extra = kw._rig_kwargs(("disk",))
    extra.pop("batch", None)
    if machine == DISK_REF:
        extra["boot"] = DISK_REF_BOOT
    return extra''',
'''    if group == "plain":
        return {}
    extra = kw._rig_kwargs((group,))
    # the artefact is not read here -- only the marks -- so the rig's own
    # capture override and tape path are dropped; its `batch` is KEPT: the
    # tape-write rig needs a boot per case (a fresh tape each time).
    extra.pop("capture", None)
    extra.pop("_tape_path", None)
    if machine == DISK_REF:
        extra["boot"] = DISK_REF_BOOT
    return extra''')

rep('''    rk = dict(capture="screen", boot=8.0, sentinel=(MARK_ADDR, END),
              settle_out=so, watch_values=((CURLIN_HI, 0xFF),))
    rk.update(extra or {})
    omsx_repl.run_cases(machine, [("direct", lines)], batch=True, reset=(), **rk)''',
'''    rk = dict(batch=True, capture="screen", boot=8.0, sentinel=(MARK_ADDR, END),
              settle_out=so, watch_values=((CURLIN_HI, 0xFF),))
    rk.update(extra or {})
    omsx_repl.run_cases(machine, [("direct", lines)], reset=(), **rk)''')

rep('''    rk = dict(capture="screen", boot=8.0, sentinel=(MARK_ADDR, END),
              settle_out=so, watch_values=((CURLIN_HI, 0xFF),))
    rk.update(extra or {})
    caps = omsx_repl.run_cases(machine, specs, batch=True, reset=(), **rk)''',
'''    rk = dict(batch=True, capture="screen", boot=8.0, sentinel=(MARK_ADDR, END),
              settle_out=so, watch_values=((CURLIN_HI, 0xFF),))
    rk.update(extra or {})
    caps = omsx_repl.run_cases(machine, specs, reset=(), **rk)''')

rep('''    for group, refm in (("plain", REF), ("disk", DISK_REF)):''',
'''    for group, refm in (("plain", REF), ("disk", DISK_REF),
                        ("printer", REF), ("tapew", REF)):''')
open(f, 'w').write(s)
print('ok')
