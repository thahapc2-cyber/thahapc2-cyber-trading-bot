"""
Multi-dimensional Analyzer - Entry point to run TA, FA, Psy and generate fused signals
"""

import logging
import os
import json
from datetime import datetime

import pandas as pd
import yfinance as yf

from core.technical_system import TechnicalSystem
from core.fundamental_system import FundamentalSystem
from core.psychological_system import PsychologicalSystem
from core.signal_fusion import SignalFusion
from core.risk_manager import PortfolioRiskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_dirs():
    """Create necessary directories for signals and logs."""
    os.makedirs('signals', exist_ok=True)
    os.makedirs('logs', exist_ok=True)


def fetch_price_data(
    symbol: str = 'GC=F',
    period: str = '2d',
    interval: str = '1m'
) -> pd.DataFrame:
    """Fetch price data from Yahoo Finance.
    
    Args:
        symbol: Trading symbol (default: 'GC=F' for Gold futures)
        period: Time period for data (default: '2d')
        interval: Candle interval (default: '1m')
    
    Returns:
        DataFrame with OHLCV data
    """
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df.empty:
        raise RuntimeError(
            'Price data fetch failed or returned empty DataFrame'
        )
    # Ensure required columns are present
    df = df.rename(columns={'Adj Close': 'Adj_Close'})
    return df


def run(equity: float = 10000.0):
    """Run the multi-dimensional analysis pipeline.
    
    Args:
        equity: Account balance/equity (default: 10000.0)
    """
    ensure_dirs()

    try:
        df = fetch_price_data()
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Price data error: %s", e)
        return

    # Initialize modules
    try:
        tech = TechnicalSystem(df)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Technical module init failed: %s", e)
        return

    fa = FundamentalSystem()
    psy = PsychologicalSystem(df)

    # Run analyses
    ta_signal = tech.analyze()
    fa_signal = None
    try:
        fa_signal = fa.analyze()
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Fundamental analysis failed: %s", e)
        # Proceed with neutral FA
        from core.fundamental_system import (
            FundamentalSignal,
            FundamentalBias
        )
        fa_signal = FundamentalSignal(
            bias=FundamentalBias.NEUTRAL,
            score=0,
            reason='FA failed',
            dxy_change=0,
            rate_level=None,
            strength_factors={}
        )

    psy_signal = psy.analyze()

    # Setup risk manager (example config)
    rm = PortfolioRiskManager(config={
        'max_total_risk': 0.06,
        'max_correlated_risk': 0.04,
        'max_positions': 5,
        'max_drawdown': 0.20,
        'max_position_size': 0.05,
        'max_leverage': 10,
        'daily_loss_limit': -0.04
    })

    fusion = SignalFusion(risk_manager=rm)
    signal = fusion.generate(
        technical=ta_signal,
        fundamental=fa_signal,
        psychological=psy_signal,
        price_df=df,
        account_balance=equity
    )

    # Output to console and log file
    if signal:
        print(json.dumps(signal, indent=2))
        logger.info('Signal written to signals/multidimensional_signal.json')
    else:
        logger.info('No valid signal generated')


if __name__ == '__main__':
    run()
