import pandas as pd
import numpy as np

def make_ohlcv(n=200, start_price=1900.0, volatility=1.0, seed=42):
    np.random.seed(seed)
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=n, freq='T')
    prices = start_price + np.cumsum(np.random.randn(n) * volatility)
    high = prices + np.abs(np.random.randn(n) * 0.5)
    low = prices - np.abs(np.random.randn(n) * 0.5)
    openp = np.roll(prices, 1)
    openp[0] = prices[0]
    close = prices
    volume = np.random.randint(100, 1000, size=n)
    df = pd.DataFrame({'Open': openp, 'High': high, 'Low': low, 'Close': close, 'Volume': volume}, index=timestamps)
    return df
