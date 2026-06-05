from core.risk_manager import RiskManager


def test_risk_manager_position_size():
    rm = RiskManager(equity=10000.0)
    entry = 1900.0
    stop = 1880.0
    lots = rm.calculate_position_size(entry, stop, atr=5.0)
    assert isinstance(lots, float)
    assert lots >= 0.01
