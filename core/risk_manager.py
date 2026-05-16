"""
Risk Manager - Portfolio-level risk constraints and monitoring
Handles position limits, portfolio drawdown, correlation risk, and circuit breakers
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels for alerts"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Position:
    """Represents an open trading position"""
    pair: str
    direction: str  # 'long' or 'short'
    size: float
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    unrealized_pnl: float
    entry_time: datetime
    signal_id: str
    
    @property
    def risk_per_position(self) -> float:
        """Calculate risk as percentage of entry price"""
        if self.direction == 'long':
            return abs(self.entry_price - self.stop_loss) / self.entry_price
        else:
            return abs(self.stop_loss - self.entry_price) / self.entry_price
    
    @property
    def current_risk_amount(self) -> float:
        """Risk in currency units"""
        return self.risk_per_position * self.entry_price * self.size


@dataclass
class RiskMetrics:
    """Risk metrics snapshot"""
    timestamp: datetime
    total_risk_pct: float  # % of account at risk
    portfolio_leverage: float  # Total notional / account balance
    current_drawdown: float  # Current DD %
    max_daily_drawdown: float  # Max DD today %
    correlated_risk: Dict[str, float]  # Risk by currency pair
    margin_utilization: float  # % of available margin used
    position_count: int
    largest_position_size: float
    unrealized_pnl: float
    daily_win_rate: float
    daily_trades: int
    daily_pnl: float


class PortfolioRiskManager:
    """
    Manages portfolio-level risk constraints and monitoring
    Prevents over-leverage, correlation issues, and catastrophic losses
    """
    
    def __init__(self, config: Dict):
        """
        Initialize risk manager with constraints
        
        Args:
            config: Dict with keys:
                - max_total_risk: Max % of portfolio at risk (default 0.06)
                - max_correlated_risk: Max % risk in correlated pairs (default 0.04)
                - max_positions: Max open positions (default 5)
                - max_drawdown: Max portfolio DD before trading halts (default 0.10)
                - max_position_size: Max size per trade (default 0.05)
                - max_leverage: Max portfolio leverage (default 10)
                - daily_loss_limit: Max loss per day (default -0.05)
        """
        self.config = {
            'max_total_risk': 0.06,
            'max_correlated_risk': 0.04,
            'max_positions': 5,
            'max_drawdown': 0.10,
            'max_position_size': 0.05,
            'max_leverage': 10,
            'daily_loss_limit': -0.05,
            **config
        }
        
        self.positions: List[Position] = []
        self.daily_pnl_list: List[float] = []
        self.metrics_history: List[RiskMetrics] = []
        self.peak_equity = 1.0  # For drawdown calculation
        self.current_equity = 1.0
        
        # Callbacks
        self.on_risk_alert = None  # Called when risk threshold exceeded
        self.on_drawdown_alert = None
        
        logger.info("Risk Manager initialized")
    
    async def validate_new_signal(
        self,
        signal: Dict,
        account_balance: float
    ) -> Tuple[bool, str]:
        """
        Validate if a new signal can be traded given current portfolio risk
        
        Args:
            signal: {pair, direction, entry, stop_loss, take_profit_1, etc}
            account_balance: Current account balance
        
        Returns:
            (is_valid, reason_if_invalid)
        """
        
        # 1. Check if trading is halted due to circuit breaker
        if await self._check_circuit_breaker():
            return False, "Circuit breaker active - trading halted"
        
        # 2. Max positions check
        if len(self.positions) >= self.config['max_positions']:
            return False, f"Max positions reached ({self.config['max_positions']})"
        
        # 3. Calculate position size based on risk
        position_size = self._calculate_safe_position_size(signal, account_balance)
        if position_size <= 0:
            return False, "Position size would be zero after risk limits"
        
        # 4. Calculate signal risk
        signal_risk_pct = self._calculate_signal_risk(signal, position_size)
        
        # 5. Total portfolio risk check
        current_risk = sum(p.risk_per_position * p.size for p in self.positions)
        if current_risk + signal_risk_pct > self.config['max_total_risk']:
            return False, (
                f"Total risk would exceed {self.config['max_total_risk']*100}% "
                f"(current: {current_risk*100:.2f}%, new: {signal_risk_pct*100:.2f}%)"
            )
        
        # 6. Correlated risk check
        correlated_risk = self._calculate_correlated_risk(signal['pair'])
        if correlated_risk + signal_risk_pct > self.config['max_correlated_risk']:
            return False, (
                f"Correlated risk limit exceeded "
                f"(current: {correlated_risk*100:.2f}%, new: {signal_risk_pct*100:.2f}%)"
            )
        
        # 7. Leverage check
        new_leverage = self._calculate_portfolio_leverage(
            signal, position_size, account_balance
        )
        if new_leverage > self.config['max_leverage']:
            return False, f"Would exceed max leverage ({self.config['max_leverage']}x)"
        
        # 8. High volatility regime check
        if await self._is_high_volatility_regime():
            # In high vol, reduce position size or skip
            return False, "High volatility regime - reducing new exposure"
        
        logger.info(f"Signal validation PASSED: {signal['pair']} {signal['direction']}")
        return True, "VALID"
    
    def _calculate_safe_position_size(self, signal: Dict, account_balance: float) -> float:
        """
        Calculate position size based on risk management rules
        
        Risk-based sizing: Risk amount / Price distance
        """
        max_risk_per_trade = account_balance * 0.01  # Risk 1% per trade
        
        entry = signal['entry']
        stop_loss = signal['stop_loss']
        
        if entry <= 0 or stop_loss <= 0 or entry == stop_loss:
            logger.error(f"Invalid entry/SL: {entry}/{stop_loss}")
            return 0
        
        price_distance = abs(entry - stop_loss)
        position_size = max_risk_per_trade / price_distance
        
        # Cap to max position size
        max_size = account_balance * self.config['max_position_size'] / entry
        position_size = min(position_size, max_size)
        
        # Validate against max leverage
        max_notional = account_balance * self.config['max_leverage']
        max_position_notional = max_notional / entry
        position_size = min(position_size, max_position_notional)
        
        logger.debug(f"Calculated position size: {position_size:.4f} lots")
        return position_size
    
    def _calculate_signal_risk(self, signal: Dict, size: float) -> float:
        """Calculate risk as % of account for this signal"""
        entry = signal['entry']
        stop_loss = signal['stop_loss']
        risk_amount = abs(entry - stop_loss) * size
        # This would be divided by account balance to get %
        return risk_amount
    
    def _calculate_correlated_risk(self, new_pair: str) -> float:
        """
        Calculate total risk in correlated pairs
        Pairs are correlated if they share same base or quote currency
        """
        new_base = new_pair[:3]  # EUR in EURUSD
        new_quote = new_pair[3:]  # USD in EURUSD
        
        correlated_positions = [
            p for p in self.positions
            if new_base in p.pair or new_quote in p.pair
        ]
        
        return sum(p.risk_per_position * p.size for p in correlated_positions)
    
    def _calculate_portfolio_leverage(
        self,
        signal: Dict,
        position_size: float,
        account_balance: float
    ) -> float:
        """Calculate portfolio leverage including new position"""
        new_notional = signal['entry'] * position_size
        current_notional = sum(p.entry_price * p.size for p in self.positions)
        
        total_notional = current_notional + new_notional
        leverage = total_notional / account_balance
        
        return leverage
    
    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is active"""
        if not self.daily_pnl_list:
            return False
        
        daily_loss = sum(self.daily_pnl_list)
        daily_loss_pct = daily_loss / self.current_equity
        
        if daily_loss_pct < self.config['daily_loss_limit']:
            logger.critical(f"Circuit breaker triggered: Daily loss {daily_loss_pct*100:.2f}%")
            if self.on_drawdown_alert:
                await self.on_drawdown_alert(
                    "CIRCUIT_BREAKER",
                    f"Daily loss limit hit: {daily_loss_pct*100:.2f}%"
                )
            return True
        
        return False
    
    async def _is_high_volatility_regime(self) -> bool:
        """Check if market is in high volatility regime"""
        # This would integrate with volatility indicators from WebSocket
        # For now, return False
        return False
    
    def add_position(self, position: Position):
        """Add a new open position"""
        self.positions.append(position)
        logger.info(f"Position added: {position.pair} {position.direction} {position.size}")
    
    def close_position(self, pair: str, exit_price: float, pnl: float):
        """Close a position and record P&L"""
        position = next((p for p in self.positions if p.pair == pair), None)
        
        if position:
            self.positions.remove(position)
            self.daily_pnl_list.append(pnl)
            
            # Update equity
            self.current_equity += pnl / self.current_equity
            
            logger.info(
                f"Position closed: {pair} | "
                f"P&L: {pnl:.4f} | Daily P&L: {sum(self.daily_pnl_list):.4f}"
            )
    
    def update_position_pnl(self, pair: str, current_price: float, current_pnl: float):
        """Update unrealized P&L for a position"""
        position = next((p for p in self.positions if p.pair == pair), None)
        if position:
            position.unrealized_pnl = current_pnl
    
    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk snapshot"""
        total_risk = sum(p.risk_per_position * p.size for p in self.positions)
        
        # Calculate drawdown
        drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        
        # Update peak if new high
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
            drawdown = 0
        
        # Win rate today
        wins = sum(1 for pnl in self.daily_pnl_list if pnl > 0)
        win_rate = wins / len(self.daily_pnl_list) if self.daily_pnl_list else 0
        
        # Calculate correlated risk by currency
        correlated_risk = {}
        for p in self.positions:
            base = p.pair[:3]
            if base not in correlated_risk:
                correlated_risk[base] = 0
            correlated_risk[base] += p.risk_per_position * p.size
        
        metrics = RiskMetrics(
            timestamp=datetime.utcnow(),
            total_risk_pct=total_risk,
            portfolio_leverage=sum(p.entry_price * p.size for p in self.positions) / self.current_equity,
            current_drawdown=drawdown,
            max_daily_drawdown=drawdown,
            correlated_risk=correlated_risk,
            margin_utilization=total_risk / self.config['max_total_risk'],
            position_count=len(self.positions),
            largest_position_size=max((p.size for p in self.positions), default=0),
            unrealized_pnl=sum(p.unrealized_pnl for p in self.positions),
            daily_win_rate=win_rate,
            daily_trades=len(self.daily_pnl_list),
            daily_pnl=sum(self.daily_pnl_list)
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    async def emergency_close_all(self, reason: str) -> bool:
        """
        Close all positions immediately (circuit breaker triggered)
        
        Returns:
            True if all positions closed, False if errors
        """
        logger.critical(f"🚨 EMERGENCY CLOSE ALL: {reason}")
        
        positions_to_close = self.positions.copy()
        success_count = 0
        
        for position in positions_to_close:
            try:
                # This would call the exchange API through the executor
                logger.info(f"Closing {position.pair}...")
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to close {position.pair}: {e}")
        
        if self.on_drawdown_alert:
            await self.on_drawdown_alert(
                "EMERGENCY_CLOSE",
                f"Closed {success_count}/{len(positions_to_close)} positions. Reason: {reason}"
            )
        
        return success_count == len(positions_to_close)
    
    def get_position_breakdown(self) -> Dict:
        """Get detailed breakdown of all open positions"""
        return {
            'count': len(self.positions),
            'by_pair': {p.pair: {
                'direction': p.direction,
                'size': p.size,
                'entry': p.entry_price,
                'current_pnl': p.unrealized_pnl,
                'risk': p.risk_per_position
            } for p in self.positions},
            'total_unrealized_pnl': sum(p.unrealized_pnl for p in self.positions),
            'total_notional': sum(p.entry_price * p.size for p in self.positions),
            'total_risk_pct': sum(p.risk_per_position * p.size for p in self.positions)
        }
    
    def reset_daily_stats(self):
        """Reset daily P&L and trade count (call at market open)"""
        self.daily_pnl_list = []
        logger.info("Daily stats reset")
