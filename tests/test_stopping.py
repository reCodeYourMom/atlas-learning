"""Tests T4.2 — règles d'arrêt de session. 1 test = 1 AC."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine.stopping import StopConfig, should_stop

CFG = StopConfig(confidence_threshold=0.75, max_items=25, max_time_s=1200.0)


def test_ac1_confidence_reached():
    d = should_stop([0.8, 0.9, 0.76], n_items_served=10, elapsed_s=100, config=CFG)
    assert d.stop is True and d.reason == "confidence"


def test_ac2_max_items_before_confidence():
    d = should_stop([0.5, 0.4], n_items_served=25, elapsed_s=100, config=CFG)
    assert d.stop is True and d.reason == "max_items"


def test_ac3_no_condition_met():
    d = should_stop([0.5, 0.4], n_items_served=10, elapsed_s=100, config=CFG)
    assert d.stop is False and d.reason is None


def test_ac4_reason_time():
    d = should_stop([0.5], n_items_served=10, elapsed_s=1300, config=CFG)
    assert d.stop is True and d.reason == "time"


def test_confidence_takes_priority_over_plafond():
    # toutes confiances OK ET plafond atteint → raison = confidence (ordre)
    d = should_stop([0.8, 0.8], n_items_served=25, elapsed_s=100, config=CFG)
    assert d.reason == "confidence"


def test_empty_targets_never_stops_on_confidence():
    d = should_stop([], n_items_served=10, elapsed_s=100, config=CFG)
    assert d.stop is False


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
