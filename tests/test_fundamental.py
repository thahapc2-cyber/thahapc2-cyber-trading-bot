import pytest
from core.fundamental_system import FundamentalSystem, FundamentalSignal, FundamentalBias


def test_fundamental_returns_signal_without_crash():
    fa = FundamentalSystem()
    # Call with explicit values to avoid network dependency
    sig = fa.analyze(dxy_value=104.0, rate_value=1.5)

    assert isinstance(sig, FundamentalSignal)
    assert -100.0 <= sig.score <= 100.0
    assert isinstance(sig.bias, FundamentalBias)
    assert 'DXY' in sig.reason or sig.reason is not None
