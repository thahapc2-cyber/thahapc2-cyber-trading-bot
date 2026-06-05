import pytest
from core.signal_fusion import SignalFusion
from core.risk_manager import RiskManager
from core.fundamental_system import FundamentalSignal, FundamentalBias
from core.psychological_system import PsychologicalSignal, MarketSentiment

import pandas as pd


def test_signal_fusion_integration():
    # minimal price df
    df = pd.DataFrame({
        'Open': [1900.0, 1901.0, 1902.0, 1903.0, 1904.0],
        'High': [1901.0, 1902.0, 1903.0, 1904.0, 1905.0],
        'Low': [1899.0, 1900.0, 1901.0, 1902.0, 1903.0],
        'Close': [1901.0, 1902.0, 1903.0, 1904.0, 1905.0],
        'Volume': [100, 120, 110, 130, 140]
    })

    technical = {
        'direction': 'LONG',
        'score': 85.0,
        'entry_price': 1905.0,
        'atr': 1.5,
        'reason': 'Test long'
    }

    fa = FundamentalSignal(bias=FundamentalBias.MODERATELY_BULLISH, score=60.0, reason='Test FA', dxy_change_pct=-0.2, rate_level=1.2)
    psy = PsychologicalSignal(sentiment=MarketSentiment.PANIC, score=75.0, reason='Test Psy', volatility_level='HIGH', volume_imbalance=-0.2, exhaustion=True)

    rm = RiskManager(equity=10000.0)
    fusion = SignalFusion(risk_manager=rm)
    signal = fusion.generate(technical=technical, fundamental=fa, psychological=psy, price_df=df, account_balance=10000.0)

    assert signal is not None
    assert 'action' in signal and signal['action'] in ('BUY', 'SELL')
    assert isinstance(signal.get('take_profits'), list) and len(signal['take_profits']) == 2
    assert signal['lots'] >= 0.01
