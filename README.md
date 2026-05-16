# 🤖 Advanced Forex/Crypto Trading Bot

A production-ready autonomous trading system featuring ML signal enhancement, real-time WebSocket data, smart order execution, and comprehensive backtesting.

## ✨ Key Features

- **Machine Learning Signal Enhancement** - XGBoost + LSTM ensemble
- **Real-time WebSocket Data** - Sub-100ms latency with auto-reconnection
- **Order Book Analysis** - Imbalance detection & trade flow analysis
- **Smart Order Execution** - Risk-based position sizing & dynamic stops
- **Cross-pair Correlation** - Cointegration detection & portfolio risk monitoring
- **Advanced Backtesting** - Walk-forward optimization & Monte Carlo simulation
- **Production Monitoring** - Health checks, comprehensive logging, alerts

## 📁 Project Structure

```
trading-bot/
├── core/
│   ├── websocket_manager.py      # Real-time data management
│   ├── order_executor.py         # Smart order execution
│   ├── ml_signal_enhancer.py     # ML signal generation
│   ├── correlation_analyzer.py   # Cross-pair analysis
│   └── backtest_engine.py        # Backtesting framework
├── tests/
│   ├── test_websocket_manager.py
│   ├── test_order_executor.py
│   ├── test_ml_enhancer.py
│   └── test_backtest_engine.py
├── utils/
│   ├── logger.py
│   ├── config.py
│   └── database.py
├── examples/
│   ├── simple_strategy.py
│   └── advanced_strategy.py
├── requirements.txt
└── config.yaml
```

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/thahapc2-cyber/thahapc2-cyber-trading-bot.git
cd thahapc2-cyber-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -v

# Start trading
python examples/simple_strategy.py
```

## 📊 Usage Example

```python
import asyncio
from core.websocket_manager import WebSocketDataManager
from core.order_executor import SmartOrderExecutor

async def main():
    # Initialize managers
    ws_manager = WebSocketDataManager(
        pairs=['BTCUSDT', 'ETHUSDT'],
        exchange='bybit'
    )
    
    executor = SmartOrderExecutor(exchange_name='bybit')
    
    # Connect and run
    if await ws_manager.connect():
        asyncio.create_task(ws_manager.run())
        
        # Get live price data
        while True:
            btc = ws_manager.get_current_price('BTCUSDT')
            if btc:
                print(f"BTC: {btc.mid_price} | Spread: {btc.spread_pct}bps")
            await asyncio.sleep(1)

asyncio.run(main())
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core tests/

# Run specific test
pytest tests/test_websocket_manager.py -v

# Run marked tests
pytest -m unit
pytest -m integration
```

## ⚙️ Configuration

Create `config.yaml`:

```yaml
exchange:
  name: bybit
  api_key: ${BYBIT_API_KEY}
  api_secret: ${BYBIT_API_SECRET}

strategy:
  fast_ema: 9
  slow_ema: 21
  pairs: [BTCUSDT, ETHUSDT]

risk_management:
  max_risk_per_trade: 0.02      # 2% of capital
  max_leverage: 10
  max_positions: 3
  
ml_models:
  model_dir: ./models
  retrain_frequency: 24h  # hours

logging:
  level: INFO
  file: trading_bot.log
```

## 📚 Documentation

- [WebSocket Manager Guide](docs/websocket_manager.md)
- [Order Executor Reference](docs/order_executor.md)
- [ML Enhancement Guide](docs/ml_enhancer.md)
- [Backtesting Tutorial](docs/backtesting.md)

## ⚠️ Security

**Never commit API keys!** Use environment variables:

```bash
export BYBIT_API_KEY=your_key
export BYBIT_API_SECRET=your_secret
```

## 📋 Disclaimer

This software is for **educational and research purposes only**. Trading involves **substantial financial risk**. The authors are not responsible for losses. Always test thoroughly before live trading.

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

**Built with ❤️ for the trading community**
