"""Smoke tests for the Streamlit dashboard (streamlit.testing.v1.AppTest).

Covers the default (precomputed) path, custom regression-period recomputation
for both models, and the too-short-period refusal. Run from the project root.
"""

import datetime as dt

from streamlit.testing.v1 import AppTest

APP = "dashboard/app.py"


def _run() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    return at


def _period_slider(at: AppTest):
    sliders = [s for s in at.slider if s.label == "Regression period"]
    assert sliders, "Regression period slider not found"
    return sliders[0]


def test_default_run_clean():
    at = _run()
    assert not at.exception
    assert not at.error
    assert len(at.tabs) == 7
    # Default = precomputed 252d window ending at the FF through-date
    s = _period_slider(at)
    assert s.value[1] == dt.date(2026, 5, 29)


def test_custom_period_ff_model():
    at = _run()
    _period_slider(at).set_value((dt.date(2025, 9, 1), dt.date(2026, 5, 29)))
    at.run()
    assert not at.exception
    assert not at.error
    captions = [c.value for c in at.caption]
    assert any("2025-09-01 → 2026-05-29" in c for c in captions)
    assert any("recomputed on the fly" in c for c in captions)


def test_custom_period_market_model():
    at = _run()
    at.radio[0].set_value("Market-only (through yesterday)")
    at.run()
    # Market model reaches the price through-date (no FF lag)
    s = _period_slider(at)
    assert s.value[1] == dt.date(2026, 7, 30)
    s.set_value((dt.date(2026, 1, 5), dt.date(2026, 7, 30)))
    at.run()
    assert not at.exception
    assert not at.error
    assert any("2026-01-05 → 2026-07-30" in c.value for c in at.caption)


def test_too_short_period_refused():
    at = _run()
    _period_slider(at).set_value((dt.date(2026, 5, 20), dt.date(2026, 5, 29)))
    at.run()
    assert not at.exception  # st.error + st.stop, not a crash
    assert any("too few" in e.value for e in at.error)
