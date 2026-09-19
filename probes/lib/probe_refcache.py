# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-REFCACHE — do not re-measure a constant.

A differential probe reads three sides. Two of them, the Philips VG-8020 and the
National CF-3300, are FIXED ROMs: given the same typed lines they return the same
screen today, tomorrow and in a year. zerobas's side changes on every build; the
references do not change at all. On 2026-08-28 D-STRLONG ran its 3-side matrix
FOUR times over rows whose reference answers could not have moved, and roughly
two thirds of every run was re-measuring constants.

This module caches the raw capture of a `run_cases` call so a repeat is served
from disk. It is deliberately paranoid, because the failure it could cause is
the worst one this project has:

  🔴 A CACHE IS ONE SLIP AWAY FROM "A PREDICTION COPIED INTO THE RESULT COLUMN".
  A key that is too loose serves an OLD answer for a NEW question and the run
  reports it as a reading. Every design decision below is about making a wrong
  hit impossible rather than unlikely, and about making a hit VISIBLE so a run
  that measured nothing cannot read like a run that measured everything.

═══ WHAT IS IN THE KEY ═══════════════════════════════════════════════════════

1. THE MACHINE'S ACTUAL BYTES, not its name. `machine_identity()` hashes the
   machine XML *and every ROM it references* (by content when the file is on
   disk, by the `<sha1>` the XML declares when openMSX resolves it from its own
   ROM database). 🎯 THIS IS WHAT MAKES THE CACHE SAFE FOR zerobas TOO, with no
   "is this a reference?" list for anyone to keep up to date: zerobas's ROM hash
   changes on every build, so its entries simply always miss -- and if a rebuild
   happens to be byte-identical, a hit is CORRECT, not lucky.
2. EVERY LINE TYPED, verbatim, including the reset/prologue sequence.
3. EVERY PARAMETER THAT CHANGES DELIVERY OR CAPTURE -- batch, reset, capture,
   holds, hold_secs, prologue, boot, step, cap_gap, timeout, cart, diska,
   verify_delivery, run_gap, sentinel, sentinel_capture.
4. A HARNESS FINGERPRINT: the bytes of omsx_repl.py and omsx_run.py. If HOW a
   line is delivered or a screen is read changes, every stored reading was taken
   by a different instrument and must be discarded. [[apparatus-is-part-of-the-measurement]]

═══ THREE RULES THAT ARE NOT OBVIOUS ═════════════════════════════════════════

🔴 ALL-OR-NOTHING PER CALL, NEVER PER CASE. Under `batch=True` a whole matrix
   shares ONE boot, and serving half of it from cache would change the batch
   COMPOSITION of the half that still runs. The harness has a `--boot-per-case`
   escape hatch precisely because inter-case leakage is possible, so a
   composition change could move an answer for a reason that has nothing to do
   with staleness -- and the disagreement would look like a stale cache. So a
   call is served entirely from cache or not at all. Probes that already run
   boot-per-case (one case per `run_cases` call, e.g. basic_probe_deffn) get
   full per-row caching from this rule for free; batched matrices get
   whole-matrix caching, which is what a re-run needs anyway.

🔴 THE OUT-PARAMETER IS STORED AND REPLAYED, NOT BYPASSED -- AND THE FIRST CUT
   OF THIS MODULE GOT THAT WRONG IN A WAY THAT LOOKED FINE. `settle_out` is a
   dict the CALLER reads afterwards (probe_signal.kwargs wires capture-on-signal
   through it), so leaving it empty on a hit would make the caller's tally
   silently under-count. The safe-looking answer was to bypass the cache for any
   call that passes one. 🎯 THEN I COUNTED: **23 of 23 rows** of a typical
   differential probe are marked, so that rule made the cache exactly 0% useful
   on the entire class of probe it was built for -- installed, green, and inert.
   [[an-unnamed-outcome-reads-as-no-outcome]] [[gateblind-slice]]

   So the dict round-trips (int keys and tuples preserved exactly, see `_enc`).
   ⚠️ BUT A REPLAYED PROVENANCE IS NOT A MEASUREMENT OF THIS RUN. Those values
   are emulated-time instants -- when the sentinel fired, or that it did not --
   and they are how the capture-on-signal apparatus is watched for health. A
   replayed dict therefore carries `replayed=True`, and probe_signal's tally
   reports those separately, so "1344 on signal, 1 fell back" can never be a
   recording of an older run wearing a live run's clothes.
   [[apparatus-is-part-of-the-measurement]] [[readout-blind-to-its-own-subject]]

🔴 A NON-READING IS NEVER STORED. `None`, an empty capture, `<NO OUTPUT>` and
   `<NO CAPTURE>` are apparatus FAULTS. Storing one would freeze a flake into a
   permanent answer that no rerun can dislodge -- the exact opposite of what the
   serial flake-retry exists to do. Misses are cheap; a cached ghost is not.

═══ MODES ════════════════════════════════════════════════════════════════════

  ZEROBAS_REFCACHE=1        (default) read + write
  ZEROBAS_REFCACHE=0        disabled entirely
  ZEROBAS_REFCACHE=verify   🎯 THE FALSIFICATION MODE. Run EVERYTHING for real,
                            then compare against whatever was stored and FAIL
                            LOUDLY on any mismatch. This is what says the cache
                            is telling the truth, rather than the cache being
                            trusted because it is convenient. Run it before
                            trusting a long-lived store.

Store: $ZEROBAS_REFCACHE_DIR, else ~/.cache/zerobas/refcache. NOT under
/tmp/zerobas -- that root is wiped on purpose and the whole point is to persist
across sessions. Entries are one JSON file per key, sharded by the first two hex
characters, written to a temp file in the SAME directory and `os.replace`d into
place: the battery runs 8-wide and a shared path written non-atomically is how
the machine-XML race produced 412 torn reads of 1200. [[machxml-race]]
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import tempfile
import time

import probe_tmp                        # noqa: F401 -- sets tempfile.tempdir
# 🎯 NOT DECORATION. `store()` writes its temp file with an explicit `dir=` (it
# MUST land beside the entry it replaces, or the rename is not atomic), but the
# selftest's scratch dirs have no such constraint and would otherwise escape to
# the system temp. `temp-root-check` caught exactly that. [[one-temp-root]]

_MODE = (os.environ.get("ZEROBAS_REFCACHE") or "1").strip().lower()
ENABLED = _MODE not in ("0", "no", "off", "false")
VERIFY = _MODE in ("verify", "check")

ROOT = (os.environ.get("ZEROBAS_REFCACHE_DIR")
        or os.path.join(os.path.expanduser("~"), ".cache", "zerobas", "refcache"))

# a reading that is not a reading -- never stored, never served
NON_READINGS = ("<NO OUTPUT>", "<NO CAPTURE>")

STATS = {"hit": 0, "miss": 0, "store": 0, "bypass": 0, "verify_ok": 0,
         "verify_bad": 0, "refused": 0, "replayed": 0, "expired": 0}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _file_sha(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return _sha(fh.read())
    except OSError:
        return "ABSENT"


# --- the machine's actual bytes ---------------------------------------------
_MACHINE_ID: dict[str, str] = {}


def _machine_xml(machine: str) -> str | None:
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "tools"))
    try:
        import openmsx_paths as P
    except Exception:
        return None
    cands = []
    try:
        cands.append(os.path.join(P.find_user(), "share", "machines", machine + ".xml"))
    except Exception:
        pass
    for share in getattr(P, "SHARE_CANDIDATES", []):
        cands.append(os.path.join(share, "machines", machine + ".xml"))
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def machine_identity(machine: str) -> str:
    """sha256 over the machine XML AND every ROM it names.

    🎯 CONTENT, NOT NAME. A machine is only "the same machine" if the bytes it
    boots are the same bytes. zerobas's merged ROM moves on every build, so its
    entries expire by construction -- there is no list of "cacheable machines"
    to get wrong, and no judgement call about which side is a reference.
    """
    if machine in _MACHINE_ID:
        return _MACHINE_ID[machine]
    xml = _machine_xml(machine)
    if xml is None:
        # unknown machine -> a per-process unique identity, so nothing is ever
        # served for it. Refusing to cache is always safe; guessing is not.
        ident = "UNRESOLVED:" + _sha(os.urandom(16).hex().encode())
        _MACHINE_ID[machine] = ident
        return ident
    ident = identity_of_xml(xml)
    _MACHINE_ID[machine] = ident
    return ident


def identity_of_xml(xml: str) -> str:
    """The identity computation itself, on an explicit path.

    Split out so `--selftest` can plant a machine and mutate a ROM it names
    WITHOUT writing into openMSX's shared machines tree -- the tree whose
    non-atomic publication produced 412 torn reads of 1200. [[machxml-race]]
    A falsification arm that has to corrupt the real environment to fire is not
    one anybody will run twice.
    """
    with open(xml, "rb") as fh:
        text = fh.read()
    parts = [_sha(text)]
    body = text.decode("utf-8", "replace")
    for tag in ("filename", "sha1"):
        cursor = 0
        while True:
            a = body.find(f"<{tag}>", cursor)
            if a < 0:
                break
            b = body.find(f"</{tag}>", a)
            if b < 0:
                break
            val = body[a + len(tag) + 2:b].strip()
            cursor = b
            if tag == "sha1":
                parts.append("sha1:" + val)        # openMSX resolves it from its
                continue                            # own ROM database by content
            for p in sorted(glob.glob(val)) or [val]:
                parts.append(f"file:{os.path.basename(p)}:{_file_sha(p)}")
    return _sha("\n".join(parts).encode())


# --- the instrument ----------------------------------------------------------
_HARNESS: str | None = None


def harness_fingerprint() -> str:
    """The bytes of the delivery/capture code itself.

    A reading is taken BY something. Change how lines are typed or how the
    screen is scraped and every stored reading was taken by a different
    instrument, whatever the machine and the typed text say.
    """
    global _HARNESS
    if _HARNESS is None:
        here = os.path.dirname(os.path.abspath(__file__))
        _HARNESS = _sha(b"".join(
            open(os.path.join(here, n), "rb").read()
            for n in sorted(("omsx_repl.py", "omsx_run.py"))
            if os.path.exists(os.path.join(here, n))))
    return _HARNESS


def key_for(machine: str, cases, params: dict) -> str:
    payload = {
        "v": 1,
        "machine_id": machine_identity(machine),
        "harness": harness_fingerprint(),
        "cases": [[c[0], list(c[1])] for c in cases],
        "params": {k: (list(v) if isinstance(v, tuple) else v)
                   for k, v in sorted(params.items())},
    }
    return _sha(json.dumps(payload, sort_keys=True, default=str).encode())


def _enc(o):
    """JSON cannot hold an int dict key or a tuple, and settle_out is full of
    both (`marks[3] = [(12.5, 255)]`). Round-tripping through plain JSON would
    turn `3` into `"3"` and the tuple into a list -- and the consumer indexes by
    int. So dicts and tuples are tagged rather than flattened."""
    if isinstance(o, dict):
        return {"__d__": [[_enc(k), _enc(v)] for k, v in o.items()]}
    if isinstance(o, tuple):
        return {"__t__": [_enc(x) for x in o]}
    if isinstance(o, list):
        return [_enc(x) for x in o]
    return o


def _dec(o):
    if isinstance(o, dict):
        if "__d__" in o:
            return {_dec(k): _dec(v) for k, v in o["__d__"]}
        if "__t__" in o:
            return tuple(_dec(x) for x in o["__t__"])
    if isinstance(o, list):
        return [_dec(x) for x in o]
    return o


def _path(key: str) -> str:
    return os.path.join(ROOT, key[:2], key + ".json")


# --- D-REFAGE (2026-08-29): entries EXPIRE ----------------------------------
# 🔴 THE HAZARD WAS NEVER DISK, IT WAS STALENESS. A well-formed but WRONG
# reference reading -- taken while the reference machine misbehaved in a way
# `storable()` does not catch -- was frozen FOREVER, because nothing ever
# re-measured it and nothing scheduled `ZEROBAS_REFCACHE=verify`.
# 🎯 AN AGE CAP DOES NOT DETECT A BAD READING; it BOUNDS HOW LONG ONE CAN SURVIVE,
# which is the honest thing to claim for it. After MAX_AGE_DAYS an entry reads as
# a MISS and is re-measured against the live machine -- self-healing, needing no
# scheduling and no operator step. `rm -rf` stops being the recovery procedure.
# ⚠️ Deliberately NOT a random re-verify sample: a probe that re-measures a
# different subset on every run makes its own wall-clock unpredictable, and this
# cache exists to make repeats cheap.
MAX_AGE_DAYS = float(os.environ.get("ZEROBAS_REFCACHE_MAX_AGE_DAYS", "14"))
_MAX_AGE = MAX_AGE_DAYS * 86400.0


def _age(path: str, now: float | None = None) -> float:
    """Seconds since the entry was written. -1 when it cannot be told.

    🔴 `now` IS NOT A TEST HOOK, IT IS THE FIX. Reading the clock afresh per
    call makes every age relative to a DIFFERENT instant, and `maintain` walks
    the store twice -- once to prune, once to report. An entry at cap minus a
    hair survives the prune and is over the cap when the report measures it, so
    the gate fails ITSELF (D-REFRACE, TODO).""" 
    try:
        t = time.time() if now is None else now
        return max(0.0, t - os.path.getmtime(path))
    except OSError:
        return -1.0


def expired(path: str, now: float | None = None) -> bool:
    """An entry older than the cap. A cap of 0 or less disables expiry."""
    if _MAX_AGE <= 0:
        return False
    a = _age(path, now)
    return a >= 0 and a > _MAX_AGE


def load(key: str):
    """-> (result, settle) or (None, None)."""
    path = _path(key)
    if expired(path):
        # Read as a MISS, so the caller re-measures against the live machine.
        STATS["expired"] += 1
        return None, None
    try:
        with open(path, "r") as fh:
            d = json.load(fh)
        return d["result"], _dec(d.get("settle")) if d.get("settle") else None
    except (OSError, ValueError, KeyError):
        return None, None


# 🔴 WHAT THE LAST prune() COULD NOT DELETE, AND WHY THAT NEEDED A NAME.
# `except OSError: kept += 1` counted a FAILED unlink as a kept entry, which is
# indistinguishable from a legitimately young one -- so an over-cap entry that
# cannot be removed makes `maintain()` go red while reporting only "an entry
# survived the prune", with no path, no age and no hint that a delete FAILED.
# D-REFDIAG reproduced exactly that on demand (a read-only parent directory) and
# could not reproduce the failure actually filed, so the deliverable is to make
# the NEXT occurrence explain itself rather than to guess at the last one.
# A list of (path, age_seconds, errno-ish string); reset at the start of a prune.
PRUNE_FAILED: list = []


def prune(max_age_days: float | None = None,
          now: float | None = None) -> tuple[int, int]:
    """Delete every entry past the cap. -> (removed, kept). Disk is the SECOND
    reason this exists; the first is that an expired entry left on disk is a
    stale reading waiting for the cap to be raised.

    Entries that were over the cap and could NOT be unlinked are counted in
    `kept` (the return shape is unchanged) AND recorded in `PRUNE_FAILED`, so
    the caller can say WHICH entry defeated it."""
    limit = _MAX_AGE if max_age_days is None else max_age_days * 86400.0
    removed = kept = 0
    PRUNE_FAILED.clear()
    for dirpath, _dirs, files in os.walk(ROOT):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dirpath, fn)
            a = _age(fp, now)
            if limit > 0 and a > limit:
                try:
                    os.unlink(fp); removed += 1
                except OSError as e:
                    PRUNE_FAILED.append((fp, a, e.__class__.__name__
                                         + (f"/{e.errno}" if e.errno else "")))
                    kept += 1
            else:
                kept += 1
    return removed, kept


def store_stats(now: float | None = None) -> tuple[int, int, float]:
    """-> (entries, bytes, oldest_age_seconds) over the whole store."""
    n = size = 0
    oldest = 0.0
    for dirpath, _dirs, files in os.walk(ROOT):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dirpath, fn)
            n += 1
            try:
                size += os.path.getsize(fp)
            except OSError:
                pass
            oldest = max(oldest, _age(fp, now))
    return n, size, oldest


def storable(result) -> bool:
    """Only a COMPLETE set of real readings is worth keeping."""
    if not isinstance(result, list) or not result:
        return False
    for r in result:
        if r is None or not isinstance(r, str) or not r.strip():
            return False
        if any(n in r for n in NON_READINGS):
            return False
    return True


def store(key: str, result, machine: str, settle=None) -> bool:
    if not storable(result):
        STATS["refused"] += 1
        return False
    d = _path(key)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    # atomic: temp file in the SAME dir, then replace. 8-wide batteries share
    # this tree and a partially-written entry would be read as a short answer.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(d), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump({"key": key, "machine": machine, "result": result,
                       "settle": _enc(settle) if settle else None}, fh)
        os.replace(tmp, d)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False
    STATS["store"] += 1
    return True


def summary() -> str:
    s = STATS
    # 🔴 THIS GUARD USED TO OMIT verify_ok AND store, WHICH SILENCED THE TALLY IN
    # EXACTLY THE RUN THAT NEEDED IT. A `verify` battery where every entry AGREES
    # increments only verify_ok -- so the report said nothing, and "no output"
    # was indistinguishable from "verify never ran". The first verify battery
    # was read as evidence on that silence; it was not evidence of anything until
    # this line listed every counter.
    if not any(s[k] for k in ("hit", "miss", "bypass", "verify_ok",
                              "verify_bad", "store", "refused", "expired")):
        return ""
    bits = [f"{s['hit']} hit", f"{s['miss']} miss"]
    if VERIFY:
        bits = [f"VERIFY MODE (nothing served; every row re-measured)"] + bits
    if s["store"]:
        bits.append(f"{s['store']} stored")
    if s["refused"]:
        bits.append(f"{s['refused']} refused (non-reading)")
    if s["replayed"]:
        bits.append(f"{s['replayed']} replayed provenance")
    if s["bypass"]:
        bits.append(f"{s['bypass']} bypassed")
    if s["expired"]:
        # Named, not folded into `miss`: an expired entry is a reading this run
        # DELIBERATELY refused to reuse, and that is a different fact from never
        # having had one. [[an-unnamed-outcome-reads-as-no-outcome]]
        bits.append(f"{s['expired']} EXPIRED past {MAX_AGE_DAYS:g}d "
                    f"(re-measured)")
    if VERIFY:
        bits.append(f"{s['verify_ok']} entries CONFIRMED against a fresh reading"
                    f", {s['verify_bad']} MISMATCH")
    return "refcache: " + ", ".join(bits)


def report() -> None:
    """Print the tally. 🔴 A RUN THAT MEASURED NOTHING MUST NOT READ LIKE A RUN
    THAT MEASURED EVERYTHING -- so this is printed even when every row hit."""
    line = summary()
    if line:
        sys.stderr.write(line + "\n")


# 🔴 REGISTERED HERE, NOT ASKED OF 200 CALLERS. The first full battery under
# this cache stored 3132 entries and NOT ONE unit log said so, because `report()`
# existed and nothing called it. A cache whose hits are invisible is precisely
# the thing this module's header says must not exist: a run that measured
# nothing reading exactly like a run that measured everything. The chokepoint
# owns its own visibility, the same way it owns its own key.
# [[an-unnamed-outcome-reads-as-no-outcome]] [[one-temp-root]]
import atexit                                                    # noqa: E402
atexit.register(report)


# ===========================================================================
# --- SELFTEST: every way a cache can lie, planted and shown to fail --------
# ===========================================================================
def _selftest() -> int:
    r"""🔴 A CACHE IS TRUSTED ONLY AS FAR AS ITS WRONG-HIT ARMS ACTUALLY FIRE.

    Each arm below PLANTS the difference and asserts a MISS. An arm that passes
    because the two inputs were never really different is not an arm -- so every
    one prints the two keys it compared, and K0 is the green control that says
    identical inputs really do produce a hit on this same apparatus.
    """
    import shutil
    fails = []

    def arm(name, cond, detail=""):
        print(f"{'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
        if not cond:
            fails.append(name)

    M = "Philips_VG_8020"
    CASES = [("direct", ["NEW", 'PRINT "HI"'])]
    P = dict(batch=False, reset=("NEW",), capture="screen", holds=None,
             hold_secs=12.0, prologue=(), boot=8.0, step=8.0, cap_gap=10.0,
             timeout=300.0, omsx=None, cart=None, diska=None,
             verify_delivery=True, run_gap=None, sentinel=None,
             sentinel_capture=False)
    k0 = key_for(M, CASES, P)

    # --- K0 GREEN CONTROL: identical inputs -> the SAME key --------------
    arm("K0 identical inputs give the same key (green control)",
        key_for(M, CASES, P) == k0, k0[:12])

    # --- K1 one character of one typed line ------------------------------
    k = key_for(M, [("direct", ["NEW", 'PRINT "HJ"'])], P)
    arm("K1 one character of a typed line -> MISS", k != k0, f"{k0[:8]} vs {k[:8]}")

    # --- K2 an extra line ------------------------------------------------
    k = key_for(M, [("direct", ["NEW", 'PRINT "HI"', "END"])], P)
    arm("K2 an extra typed line -> MISS", k != k0, f"{k0[:8]} vs {k[:8]}")

    # --- K3 a delivery parameter -----------------------------------------
    for field, val in (("batch", True), ("reset", ("CLS",)), ("boot", 9.0),
                       ("capture", "text"), ("sentinel_capture", True)):
        p2 = dict(P); p2[field] = val
        k = key_for(M, CASES, p2)
        arm(f"K3 param {field!r} -> MISS", k != k0, f"{k0[:8]} vs {k[:8]}")

    # --- K4 THE MACHINE'S BYTES, not its name ----------------------------
    # plant a machine XML naming a ROM, then change ONE BYTE of that ROM.
    tmp = tempfile.mkdtemp(prefix="refcache-selftest-")
    try:
        rom = os.path.join(tmp, "fake.rom")
        open(rom, "wb").write(b"\x00" * 64)
        xml = os.path.join(tmp, "Fake_Machine.xml")
        open(xml, "w").write(
            f"<msxconfig><machine><devices><primary><ROM><rom>"
            f"<filename>{rom}</filename></rom></ROM></primary>"
            f"</devices></machine></msxconfig>")
        a = identity_of_xml(xml)
        open(rom, "wb").write(b"\x00" * 63 + b"\x01")     # ONE byte
        b = identity_of_xml(xml)
        arm("K4 one byte of a ROM the machine names -> different identity",
            a != b, f"{a[:8]} vs {b[:8]}")
        # and the same bytes give the same identity (the control for K4)
        open(rom, "wb").write(b"\x00" * 64)
        arm("K4b restoring the ROM restores the identity (control)",
            identity_of_xml(xml) == a, a[:12])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- K5 the instrument -----------------------------------------------
    global _HARNESS
    saved, _HARNESS = _HARNESS, "PRETEND-THE-HARNESS-CHANGED"
    k = key_for(M, CASES, P)
    _HARNESS = saved
    arm("K5 a changed harness fingerprint -> MISS", k != k0, f"{k0[:8]} vs {k[:8]}")

    # --- K6 a non-reading is never stored --------------------------------
    for bad, why in ((None, "None"), ([], "empty list"), ([None], "[None]"),
                     ([""], "empty string"), (["  "], "blank"),
                     (["x <NO OUTPUT> y"], "<NO OUTPUT>"),
                     (["<NO CAPTURE>"], "<NO CAPTURE>"),
                     (["ok", None], "one good one None")):
        arm(f"K6 refuse to store {why}", not storable(bad))
    arm("K6b a real reading IS storable (control)", storable(["READY", "OK"]))

    # --- K7 round trip ---------------------------------------------------
    global ROOT
    saved_root, ROOT = ROOT, tempfile.mkdtemp(prefix="refcache-rt-")
    try:
        val = ["line one\nline two", "second case"]
        settle = {"sentinel": {0: 56.0, 1: 80.125}, "fallback": {},
                  "marks": {0: [(56.0, 255)]}, "span": {0: (1.5, 9.0)}}
        store("deadbeef" * 8, val, M, settle=settle)
        got, gs = load("deadbeef" * 8)
        arm("K7 store -> load round-trips the result exactly", got == val)
        # 🔴 INT KEYS AND TUPLES, NOT "3" AND [3]. The consumer indexes settle_out
        # by int and unpacks tuples; plain JSON would hand back strings and lists
        # and the tally would read empty while looking fine.
        arm("K7b settle_out round-trips int keys and tuples exactly", gs == settle,
            f"{gs}")
        arm("K7c an unknown key loads as (None, None)", load("f0" * 32) == (None, None))
        # a result stored WITHOUT settle must not be served to a caller that
        # wants one -- otherwise the caller gets an empty dict and under-counts
        store("cafe" * 16, val, M, settle=None)
        arm("K7d a settle-less entry stores no provenance",
            load("cafe" * 16)[1] is None)

        # --- K8 concurrent writers never yield a torn read ---------------
        import threading
        keys = [f"{i:064x}" for i in range(24)]
        payload = ["A" * 4000]
        ths = [threading.Thread(target=store, args=(k, payload, M)) for k in keys]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        torn = [k for k in keys if load(k)[0] != payload]
        arm("K8 24 concurrent writers, 0 torn reads", not torn,
            f"torn: {torn[:3]}" if torn else "")
    finally:
        shutil.rmtree(ROOT, ignore_errors=True)
        ROOT = saved_root

    # --- K9 THE VERIFY MODE, END TO END ON A REAL MACHINE ----------------
    # 🎯 EVERY ARM ABOVE IS PURE ARITHMETIC ON KEYS. This one plants a WRONG
    # answer in the store and shows that `ZEROBAS_REFCACHE=verify` catches it
    # against a real emulator reading -- which is the only thing that says the
    # store can be trusted after it has been sitting on disk for a month.
    # 🔴 RUN AS `__main__`, THIS FILE IS NOT THE MODULE omsx_repl IMPORTS.
    # `python3 probe_refcache.py --selftest` binds this code as `__main__`, and
    # omsx_repl's `import probe_refcache` then creates a SECOND, independent
    # module object. The first cut of K9 set VERIFY/ROOT on one instance while
    # the wrapper read the other, and the arm reported "did not fire" -- which
    # would have read as "the cache cannot be falsified" when it was really two
    # copies of the instrument. Bind the IMPORTED one explicitly.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import probe_refcache as RC          # the instance omsx_repl will use
    print(f"NOTE  K9 binds the IMPORTED module instance "
          f"({'same object' if RC.STATS is STATS else 'DISTINCT from __main__'})"
          f" -- see the comment above; this is a statement of fact, not an arm.")
    saved_root, RC.ROOT = RC.ROOT, tempfile.mkdtemp(prefix="refcache-verify-")
    saved_verify, RC.VERIFY = RC.VERIFY, True
    # 🔴 AND `ENABLED` TOO. The battery now forces ZEROBAS_REFCACHE=0 for every
    # unit (a gate measures, it never replays -- spec-refcache.md §6), which
    # made this gate's own K9 arms go dark: run_cases bypassed the module
    # entirely, so the tamper could not be caught and the arm reported "did not
    # fire". The suite must drive the module it is testing rather than inherit
    # the environment's opinion of whether that module is switched on.
    saved_enabled, RC.ENABLED = RC.ENABLED, True
    try:
        import omsx_repl
        CASE = [("direct", ["NEW", 'PRINT "REFCACHE"'])]
        KW = dict(batch=False, boot=8.0, step=8.0, cap_gap=10.0, timeout=300.0)
        real = omsx_repl.run_cases(M, CASE, **KW)
        arm("K9a a real reading came back", bool(real and real[0]),
            (real[0][:40] if real and real[0] else "NOTHING"))
        import inspect
        b = inspect.signature(omsx_repl._run_cases_impl).bind(M, CASE, **KW)
        b.apply_defaults()
        a2 = dict(b.arguments); a2.pop("machine"); a2.pop("cases"); a2.pop("settle_out", None)
        k = RC.key_for(M, CASE, a2)
        # 🟢 GREEN CONTROL WITH TEETH: re-run against the entry just stored and
        # require an ACTUAL agreement (verify_ok incremented), not merely the
        # absence of a mismatch -- "0 bad" is also what a VERIFY that never ran
        # would report. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
        omsx_repl.run_cases(M, CASE, **KW)
        arm("K9b VERIFY agreed with the untampered entry (green control)",
            RC.STATS["verify_ok"] >= 1, f"verify_ok={RC.STATS['verify_ok']}")
        RC.store(k, ["A DELIBERATE LIE"], M)           # tamper
        before = RC.STATS["verify_bad"]
        omsx_repl.run_cases(M, CASE, **KW)
        arm("K9c VERIFY caught a tampered entry (the arm that matters)",
            RC.STATS["verify_bad"] == before + 1,
            f"verify_bad {before} -> {RC.STATS['verify_bad']}")
    except Exception as e:                       # an emulator-less host
        print(f"SKIP  K9 end-to-end verify: {type(e).__name__}: {e}")
    finally:
        RC.VERIFY, RC.ENABLED = saved_verify, saved_enabled
        shutil.rmtree(RC.ROOT, ignore_errors=True)
        RC.ROOT = saved_root

    # --- D-REFAGE: expiry, prune, and the store readout --------------------
    saved_root = RC.ROOT
    RC.ROOT = tempfile.mkdtemp(prefix="refage-")
    try:
        RC.store("a" * 40, ["r1"], "M")
        p_fresh = RC._path("a" * 40)
        arm("KA1 a FRESH entry is not expired (the green control -- without it "
            "every arm below passes on a store that simply never wrote)",
            os.path.exists(p_fresh) and not RC.expired(p_fresh))
        arm("KA2 a fresh entry LOADS", RC.load("a" * 40)[0] == ["r1"])

        old_t = time.time() - (RC.MAX_AGE_DAYS + 1) * 86400
        os.utime(p_fresh, (old_t, old_t))
        arm("KA3 an entry past the cap reads as EXPIRED", RC.expired(p_fresh))
        before = RC.STATS["expired"]
        arm("KA4 🔴 THE ARM THAT MATTERS: an expired entry LOADS AS A MISS, so "
            "the caller re-measures against the live machine",
            RC.load("a" * 40)[0] is None)
        arm("KA5 and the refusal is COUNTED, not silent",
            RC.STATS["expired"] == before + 1)
        arm("KA6 the summary NAMES the expiry rather than folding it into miss",
            "EXPIRED" in RC.summary())

        n, _sz, oldest = RC.store_stats()
        arm("KA7 store_stats sees the entry and its age", n == 1 and oldest > 0)
        removed, kept = RC.prune()
        arm("KA8 prune deletes the expired entry", (removed, kept) == (1, 0))

        RC.store("b" * 40, ["r2"], "M")
        removed, kept = RC.prune()
        arm("KA9 prune KEEPS a fresh entry (negative control -- a prune that "
            "deletes everything would pass KA8)", (removed, kept) == (0, 1))

        saved_max = RC._MAX_AGE
        RC._MAX_AGE = 0
        os.utime(RC._path("b" * 40), (old_t, old_t))
        arm("KA10 a cap of 0 DISABLES expiry (the escape hatch works)",
            not RC.expired(RC._path("b" * 40)))
        RC._MAX_AGE = saved_max

        # --- D-REFRACE: maintain must not race its own post-condition -------
        for fn in os.listdir(RC.ROOT):
            fp = os.path.join(RC.ROOT, fn)
            if os.path.isfile(fp):
                os.unlink(fp)
        RC.store("c" * 40, ["r3"], "M")
        edge = RC._path("c" * 40)
        # plant it a HAIR under the cap: survives a prune taken now, and is
        # over the cap a second later. This is the real store's situation on
        # the day an entry ages out mid-battery.
        t_now = time.time()
        os.utime(edge, (t_now - RC._MAX_AGE + 0.5, t_now - RC._MAX_AGE + 0.5))
        arm("KA11 GREEN CONTROL (and only that): maintain() is green on an "
            "entry under the cap. 🔴 IT PASSES WITH OR WITHOUT THE ONE-CLOCK "
            "FIX -- a mutation reverting `prune(now=now)` left it PASSING -- "
            "because the real gap between the two walks is microseconds and "
            "this fixture plants half a second of margin. Named for what it "
            "is; KA12 is the arm with content.", RC.maintain(now=t_now) == 0)
        arm("KA12 🔴 THE ARM WITH CONTENT: measure the post-condition a second "
            "LATER than the prune -- the shape the code had before D-REFRACE -- "
            "and the SAME store goes RED. That is what makes `maintain` capable "
            "of failing ITSELF on the calendar, and why one clock reading is "
            "now threaded through both walks.",
            RC.maintain(now=t_now, stats_now=t_now + 1.0) == 1)
        arm("KA13 and a genuinely over-cap entry is still PRUNED, so KA11 did "
            "not buy its green by disabling expiry",
            (os.utime(edge, (t_now - RC._MAX_AGE * 3, t_now - RC._MAX_AGE * 3)),
             RC.maintain(now=t_now, stats_now=t_now,
                         ) == 0)[1] and not os.path.exists(edge))
        # --- D-REFDIAG: the one-clock fix finally has a COVERING arm ---------
        # 🔴 KA11 AND KA12 DO NOT COVER IT, AND A MUTATION PROVED THAT. Reverting
        # `prune(now=now)` to `prune()` -- undoing D-REFRACE's entire fix -- left
        # EVERY arm passing: KA11 plants half a second of margin, and KA12 passes
        # `stats_now` by hand so it exercises the SHAPE without ever checking
        # that `maintain` threads its clock into `prune`.
        # This one separates them. Plant an entry 20 days old, then run the whole
        # of `maintain` against a clock 30 days in the PAST. Threading that clock
        # through makes the entry's age NEGATIVE (clamped to 0), so it survives;
        # reading the wall clock inside `prune` makes it 20 days old, so it is
        # deleted. Survival IS the fix.
        for fn in os.listdir(RC.ROOT):
            fp = os.path.join(RC.ROOT, fn)
            if os.path.isfile(fp):
                os.unlink(fp)
        RC.store("e" * 40, ["r5"], "M")
        ent = RC._path("e" * 40)
        t20 = time.time() - 20 * 86400
        os.utime(ent, (t20, t20))
        past = time.time() - 30 * 86400
        RC.maintain(now=past, stats_now=past)
        arm("KA15 🔴 THE ARM THAT COVERS D-REFRACE: maintain() threads ITS clock "
            "into prune(), so an entry that is 'not yet written' at that clock "
            "SURVIVES -- revert `prune(now=now)` and this entry is deleted",
            os.path.exists(ent))
        RC.maintain()
        arm("KA15 NEGATIVE: at the REAL clock the same 20-day entry is pruned, "
            "so KA15 is about the clock and not about expiry being broken",
            not os.path.exists(ent))

        # --- D-REFDIAG: a failed unlink must NAME itself ---------------------
        # 🔴 THE ARM THAT MATTERS HERE. `except OSError: kept += 1` made an
        # entry prune COULD NOT DELETE look exactly like a young one, so the
        # gate went red saying only "an entry survived the prune". Reproduced on
        # demand with a read-only parent directory.
        for fn in os.listdir(RC.ROOT):
            fp = os.path.join(RC.ROOT, fn)
            if os.path.isfile(fp):
                os.unlink(fp)
        RC.store("d" * 40, ["r4"], "M")
        stuck = RC._path("d" * 40)
        way_old = time.time() - RC._MAX_AGE * 2
        os.utime(stuck, (way_old, way_old))
        holder = os.path.dirname(stuck)
        mode = os.stat(holder).st_mode
        os.chmod(holder, 0o555)
        try:
            rc_stuck = RC.maintain()
            failed_named = bool(RC.PRUNE_FAILED) and \
                RC.PRUNE_FAILED[0][0] == stuck
        finally:
            os.chmod(holder, mode)
        arm("KA14 an over-cap entry that CANNOT be unlinked makes maintain red "
            "AND is named in PRUNE_FAILED, so the post-mortem has the path",
            rc_stuck == 1 and failed_named)

        removed2, _kept2 = RC.prune()
        arm("KA14 NEGATIVE: once it IS removable the same entry prunes and "
            "PRUNE_FAILED is EMPTY -- so the list means 'could not delete', "
            "not merely 'an over-cap entry existed'",
            removed2 == 1 and not RC.PRUNE_FAILED)
    finally:
        shutil.rmtree(RC.ROOT, ignore_errors=True)
        RC.ROOT = saved_root

    print()
    print("ALL PASS — refcache falsification suite" if not fails
          else f"🔴 {len(fails)} ARM(S) FAILED: {fails}")
    return 1 if fails else 0


def maintain(now: float | None = None,
             stats_now: float | None = None) -> int:
    """Prune expired entries and print what the store looks like.

    🟢 THE PRUNE HAS TO BE SOMEWHERE THAT ACTUALLY RUNS. An age cap that only
    takes effect on `load` bounds STALENESS but never reclaims disk, and the
    filed item's whole complaint was that `rm -rf` was the entire recovery
    procedure. `make refcache-check` runs every battery, costs nothing, and is
    already the file's gate."""
    # 🔴 ONE CLOCK READING FOR BOTH WALKS. The prune and the post-condition
    # must agree about what time it is, or the check is a race against the gate
    # itself: an entry at cap-epsilon passes the prune and is at cap+delta when
    # the report measures it. That is what made `refcache-check` go red on the
    # CALENDAR and the battery's retry arm call it REAL -- a second run inside
    # one battery is a second run at the same instant, so a retry cannot
    # classify a clock-driven red (D-REFRACE).
    # `stats_now` exists ONLY for the selftest's negative control, which
    # reproduces the old two-readings behaviour and must go red.
    now = time.time() if now is None else now
    removed, kept = prune(now=now)
    n, size, oldest = store_stats(now=now if stats_now is None else stats_now)
    print(f"refcache store: {n} entr(ies), {size / 1e6:.1f} MB, "
          f"oldest {oldest / 86400:.1f}d, cap {MAX_AGE_DAYS:g}d; "
          f"pruned {removed}, kept {kept}")
    # 🔴 A READOUT THAT CANNOT GO RED IS A PRINT STATEMENT. After a prune no
    # entry may be past the cap -- if one is, expiry is not doing what the two
    # sentences above claim.
    if MAX_AGE_DAYS > 0 and oldest > _MAX_AGE:
        # 🔴 SAY WHICH ENTRY AND WHY, NOT JUST THAT ONE EXISTS. The filed red
        # (TODO, apparatus (d)) could not be diagnosed after the fact because
        # this message named nothing: the run that investigated it also REPAIRED
        # it, so the evidence was gone. Everything below is free to compute and
        # is what a post-mortem needs.
        print(f"🔴 an entry survived the prune at {oldest / 86400:.1f}d "
              f"> {MAX_AGE_DAYS:g}d cap")
        if PRUNE_FAILED:
            print(f"   CAUSE: {len(PRUNE_FAILED)} over-cap entr(ies) could NOT "
                  f"be unlinked -- this is the `except OSError` arm, and it is "
                  f"counted in `kept`, which is why it used to look like a "
                  f"young entry:")
            for fp, a, err in PRUNE_FAILED[:5]:
                print(f"     {a / 86400:.2f}d  {err}  {fp}")
        else:
            # No unlink failed, so the survivor was UNDER the cap when the prune
            # looked and OVER it when the report did -- or it appeared between
            # the two walks. Name the offender so the next reader has the datum
            # this gate denied its own investigator.
            worst = None
            for dirpath, _dirs, files in os.walk(ROOT):
                for fn in files:
                    if not fn.endswith(".json"):
                        continue
                    fp = os.path.join(dirpath, fn)
                    ag = _age(fp, now if stats_now is None else stats_now)
                    if worst is None or ag > worst[1]:
                        worst = (fp, ag)
            print("   CAUSE: no unlink failed, so this is NOT the "
                  "`except OSError` arm. The oldest survivor was under the cap "
                  "when prune looked and over it when the report did, or it "
                  "arrived between the two walks.")
            if worst:
                print(f"     oldest survivor: {worst[1] / 86400:.4f}d  "
                      f"{worst[0]}")
                print(f"     margin over cap: "
                      f"{(worst[1] - _MAX_AGE):.3f}s")
        return 1
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    if "--maintain" in sys.argv:
        raise SystemExit(maintain())
    raise SystemExit((print(summary() or "refcache: idle"), 0)[1])
