import pytest
from core.psychological_system import PsychologicalSystem
from tests.common import make_ohlcv


def test_psychological_detects_structure():
    # Create data with a volatility spike
    df = make_ohlcv(n=120)
    # artificially create a large range candle
    df.iloc[-3, df.columns.get_loc('High')] = df['High'].iloc[-3] + 10
    df.iloc[-3, df.columns.get_loc('Low')] = df['Low'].iloc[-3] - 10
    psy = PsychologicalSystem(df)
    sig = psy.analyze()

    assert hasattr(sig, 'sentiment')
    assert 0 <= sig.score <= 100
    assert isinstance(sig.exhaustion, bool)
