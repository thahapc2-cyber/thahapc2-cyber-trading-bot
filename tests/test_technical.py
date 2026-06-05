import pytest
import core.technical_system as ts
from tests.common import make_ohlcv


def test_technical_analyze_basic():
    df = make_ohlcv(n=250)
    tech = ts.TechnicalSystem(df)
    result = tech.analyze()

    assert isinstance(result, dict)
    assert 'direction' in result
    assert 'score' in result
    assert 0 <= result['score'] <= 100
    assert 'entry_price' in result
    assert result['entry_price'] == round(float(df['Close'].iloc[-1]), 4)
