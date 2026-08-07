"""Fault injection: duplicates + reorder-within-window + drop-with-retry must produce a
byte-identical applied ledger vs the clean run (PRD-2 acceptance)."""

import json
import random

from cosmos77_cop.net.receiver import Receiver


def scripted_stream(n=12):
    return [{"step": s, "commit": f"c{s:02d}", "hint": f"h{s}"} for s in range(1, n + 1)]


def ledger_of(arrivals, window=4):
    r = Receiver(window=window)
    applied = []
    for msg in arrivals:
        applied.extend(r.ingest(dict(msg)))
    assert r.equivocations == [] and r.violations == []
    return json.dumps(applied, sort_keys=True)


def test_clean_run_baseline():
    clean = ledger_of(scripted_stream())
    assert json.loads(clean)[0]["step"] == 1
    assert len(json.loads(clean)) == 12


def test_duplicate_every_message_is_byte_identical():
    stream = scripted_stream()
    duplicated = [m for msg in stream for m in (msg, msg)]
    assert ledger_of(duplicated) == ledger_of(stream)


def test_reorder_within_window_is_byte_identical():
    stream = scripted_stream()
    rng = random.Random(55)
    reordered = list(stream)
    for i in range(0, len(reordered) - 3, 4):
        chunk = reordered[i : i + 4]
        rng.shuffle(chunk)
        reordered[i : i + 4] = chunk
    assert ledger_of(reordered) == ledger_of(stream)


def test_drop_with_retry_is_byte_identical():
    stream = scripted_stream()
    lossy = []
    for msg in stream:
        if msg["step"] % 3 == 0:
            lossy.append({**msg, "commit": msg["commit"]})
        lossy.append(msg)
    dropped_then_retried = [m for m in lossy]
    assert ledger_of(dropped_then_retried) == ledger_of(stream)


def test_combined_chaos_is_byte_identical():
    stream = scripted_stream()
    rng = random.Random(77)
    chaos = []
    for i in range(0, len(stream), 3):
        chunk = stream[i : i + 3]
        rng.shuffle(chunk)
        for msg in chunk:
            chaos.append(msg)
            if rng.random() < 0.5:
                chaos.append(dict(msg))
    assert ledger_of(chaos) == ledger_of(stream)
