"""
Signal Fusion Engine - Combine Technical, Fundamental, and Psychological analyses into a final signal
Produces JSON output, robust error handling, and logging for production use.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Optional

from core.risk_manager import PortfolioRiskManager
from core.technical_system import TechnicalSignal
from core.fundamental_system import FundamentalSignal
from core.psychological_system import PsychologicalSignal

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SignalFusion:
    """Combine pillar outputs into a single actionable signal"""

    def __init__(self, risk_manager: PortfolioRiskManager, weights: Dict = None):
        # Default weights (TA, FA, Psy)
        self.weights = { 'ta': 0.6, 'fa': 0.25, 'psy': 0.15 }
        if weights:
            self.weights.update(weights)
        self.risk_manager = risk_manager

    def _normalize_fa_score(self, fa_score: float) -> float:
        """Map FA score from -100..100 to 0..100 (higher = bullish for XAUUSD)
        FA score is centered at 0 where negative = bearish, positive = bullish for gold.
        """
        return max(0.0, min(100.0, (fa_score + 100.0) / 2.0))

    def _direction_match(self, ta_dir: Optional[str], fa_bias: Optional[str], psy_sent: Optional[str]) -> bool:
        """Check if pillars generally align for a coherent signal"""
        # Map FA and Psy to LONG/SHORT/NEUTRAL
        fa_map = {
            'STRONGLY_BULLISH': 'LONG',
            'MODERATELY_BULLISH': 'LONG',
            'NEUTRAL': 'NEUTRAL',
            'MODERATELY_BEARISH': 'SHORT',
            'STRONGLY_BEARISH': 'SHORT'
        }
        psy_map = {
            'EXTREME_PANIC': 'LONG',
            'PANIC': 'LONG',
            'FEAR': 'LONG',
            'NEUTRAL': 'NEUTRAL',
            'GREED': 'SHORT',
            'EXTREME_GREED': 'SHORT'
        }
        fa_dir = fa_map.get(fa_bias, 'NEUTRAL') if fa_bias else 'NEUTRAL'
        psy_dir = psy_map.get(psy_sent, 'NEUTRAL') if psy_sent else 'NEUTRAL'

        # If TA is neutral we don't consider a match
        if not ta_dir:
            return False

        # Simple rule: require at least one of FA or Psy to not contradict TA strongly
        contradictions = 0
        if fa_dir != 'NEUTRAL' and fa_dir != ta_dir:
            contradictions += 1
        if psy_dir != 'NEUTRAL' and psy_dir != ta_dir:
            contradictions += 1

        return contradictions < 2

    def generate(self,
                 technical: TechnicalSignal,
                 fundamental: FundamentalSignal,
                 psychological: PsychologicalSignal,
                 price_df,
                 account_balance: float = 10000.0) -> Optional[Dict]:
        """
        Build final signal JSON. Returns dict or None if no signal.
        """
        try:
            ta_score = technical.score if technical else 0.0
            fa_score_norm = self._normalize_fa_score(fundamental.score if fundamental else 0.0)
            psy_score = psychological.score if psychological else 50.0

            final_score = (
                ta_score * self.weights['ta'] +
                fa_score_norm * self.weights['fa'] +
                psy_score * self.weights['psy']
            )

            # Determine TA direction
            ta_dir = technical.direction if technical else None

            # Alignment check
            aligned = self._direction_match(
                ta_dir,
                fundamental.bias.name if fundamental and fundamental.bias else None,
                psychological.sentiment.name if psychological and psychological.sentiment else None
            )

            # Minimum confidence threshold
            if not ta_dir or final_score < 60 or not aligned:
                logger.info(f"Signal rejected by fusion: ta_dir={ta_dir}, score={final_score:.1f}, aligned={aligned}")
                return None

            # Build trade parameters
            entry = technical.entry_price
            atr = technical.atr_value if hasattr(technical, 'atr_value') else price_df['High'].iloc[-20] - price_df['Low'].iloc[-20]

            # Dynamic stop loss using ATR
            if ta_dir == 'LONG':
                stop_loss = entry - 2.0 * atr
                tp1 = entry + 15.0
                tp2 = entry + 30.0
            else:
                stop_loss = entry + 2.0 * atr
                tp1 = entry - 15.0
                tp2 = entry - 30.0

            # Position sizing via RiskManager
            # Build minimal signal dict for validation
            minimal_signal = {
                'pair': 'XAUUSD',
                'direction': 'LONG' if ta_dir == 'LONG' else 'SHORT',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit_1': tp1,
                'take_profit_2': tp2
            }

            valid, reason = True, 'VALID'
            # If risk manager provided, validate
            try:
                valid, reason = self.risk_manager.validate_new_signal(minimal_signal, account_balance)
            except Exception:
                # risk manager might be async; try synchronous fallback
                import asyncio
                valid, reason = asyncio.get_event_loop().run_until_complete(
                    self.risk_manager.validate_new_signal(minimal_signal, account_balance)
                )

            if not valid:
                logger.info(f"Risk manager rejected signal: {reason}")
                return None

            lots = self.risk_manager._calculate_safe_position_size(minimal_signal, account_balance)

            signal = {
                'action': 'BUY' if ta_dir == 'LONG' else 'SELL',
                'symbol': 'XAUUSD',
                'entry': round(entry, 4),
                'stop_loss': round(stop_loss, 4),
                'take_profits': [round(tp1, 4), round(tp2, 4)],
                'lots': round(lots, 2),
                'confidence': round(final_score, 1),
                'pillars': {
                    'technical': {
                        'direction': technical.direction,
                        'score': technical.score,
                        'reason': technical.reason
                    },
                    'fundamental': {
                        'bias': fundamental.bias.name if fundamental and fundamental.bias else None,
                        'score': fundamental.score if fundamental else 0,
                        'reason': fundamental.reason if fundamental else 'FA missing'
                    },
                    'psychological': {
                        'sentiment': psychological.sentiment.name if psychological and psychological.sentiment else None,
                        'score': psychological.score if psychological else 50,
                        'reason': psychological.reason if psychological else 'Psy missing'
                    }
                },
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }

            # Safe JSON dump to file
            try:
                with open('signals/multidimensional_signal.json', 'w') as fh:
                    json.dump(signal, fh, indent=2, default=str)
            except Exception as e:
                logger.warning(f"Could not write signal to file: {e}")

            logger.info(f"Signal generated: {signal['action']} confidence={signal['confidence']}")
            return signal

        except Exception as e:
            logger.exception(f"Signal fusion error: {e}")
            return None
