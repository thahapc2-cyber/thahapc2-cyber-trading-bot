"""
Telegram Signal Bot Integration - Professional signal distribution with alerts
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class SignalNotification:
    """Signal notification payload"""
    signal_id: str
    pair: str
    direction: str
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    position_size: float
    confidence: float
    risk_reward: float
    risk_percent: float
    setup_type: str
    ml_score: float
    timestamp: datetime


class TelegramSignalBot:
    """
    Professional Telegram bot for signal distribution and alerts
    Features: Premium signals, daily reports, alerts, inline management
    """
    
    def __init__(self, token: str, channel_id: str, admin_id: Optional[str] = None):
        """
        Initialize Telegram bot
        
        Args:
            token: Telegram bot token
            channel_id: Destination channel ID
            admin_id: Admin user ID for special commands
        """
        self.token = token
        self.channel_id = channel_id
        self.admin_id = admin_id
        
        # Try to import telegram library
        try:
            from telegram import Bot
            self.bot = Bot(token=token)
        except ImportError:
            logger.warning("python-telegram-bot not installed, notifications disabled")
            self.bot = None
        
        self.message_history = {}
        self.signal_messages = {}
    
    async def send_signal(self, signal: SignalNotification) -> Optional[int]:
        """
        Send premium signal to channel with professional formatting
        
        Args:
            signal: Signal notification object
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.bot:
            logger.warning("Bot not initialized")
            return None
        
        try:
            message_text = self._format_signal(signal)
            
            # Send to channel
            message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=message_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # Store for updates
            self.signal_messages[signal.signal_id] = {
                'message_id': message.message_id,
                'timestamp': datetime.now(),
                'status': 'PENDING'
            }
            
            logger.info(f"✅ Signal sent to Telegram: {signal.signal_id}")
            return message.message_id
            
        except Exception as e:
            logger.error(f"Failed to send signal to Telegram: {e}")
            return None
    
    async def update_signal_status(self, signal_id: str, status: str, details: Dict = None):
        """
        Update signal status (FILLED, TP1_HIT, SL_HIT, etc.)
        
        Args:
            signal_id: Signal identifier
            status: New status
            details: Additional details (price, time, etc.)
        """
        if not self.bot or signal_id not in self.signal_messages:
            return
        
        try:
            msg_data = self.signal_messages[signal_id]
            status_text = self._format_status_update(signal_id, status, details)
            
            # Edit original message with update
            await self.bot.edit_message_text(
                chat_id=self.channel_id,
                message_id=msg_data['message_id'],
                text=status_text,
                parse_mode='HTML'
            )
            
            msg_data['status'] = status
            logger.info(f"✅ Signal status updated: {signal_id} → {status}")
            
        except Exception as e:
            logger.error(f"Failed to update signal status: {e}")
    
    async def send_daily_report(self, report: Dict):
        """
        Send daily performance report
        
        Args:
            report: Daily statistics
        """
        if not self.bot:
            return
        
        try:
            message_text = self._format_daily_report(report)
            
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message_text,
                parse_mode='HTML'
            )
            
            logger.info("✅ Daily report sent to Telegram")
            
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
    
    async def send_alert(self, title: str, body: str, level: str = 'INFO'):
        """
        Send system alert
        
        Args:
            title: Alert title
            body: Alert message
            level: INFO, WARNING, or CRITICAL
        """
        if not self.bot:
            return
        
        try:
            emoji_map = {
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'CRITICAL': '🚨',
                'ERROR': '❌',
                'SUCCESS': '✅'
            }
            
            emoji = emoji_map.get(level, 'ℹ️')
            
            message = f"""<b>{emoji} {title}</b>

<code>{body}</code>

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"""
            
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"✅ Alert sent: {title} [{level}]")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def send_position_update(self, pair: str, update: Dict):
        """
        Send real-time position updates
        
        Args:
            pair: Trading pair
            update: Position update data
        """
        if not self.bot:
            return
        
        try:
            unrealized_pnl = update.get('unrealized_pnl', 0)
            unrealized_pct = update.get('unrealized_pct', 0)
            
            emoji = '📈' if unrealized_pnl > 0 else '📉' if unrealized_pnl < 0 else '⏸️'
            
            message = f"""<b>{emoji} Position Update: {pair}</b>

<b>Entry:</b> <code>{update['entry_price']:.6f}</code>
<b>Current:</b> <code>{update['current_price']:.6f}</code>
<b>Size:</b> <code>{update['size']:.4f}</code>

<b>P&L:</b> {unrealized_pnl:+.2f} ({unrealized_pct:+.2f}%)

<i>{datetime.now().strftime('%H:%M:%S')}</i>"""
            
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Failed to send position update: {e}")
    
    def _format_signal(self, signal: SignalNotification) -> str:
        """Format signal for display"""
        direction_emoji = '📈' if signal.direction == 'BUY' else '📉'
        
        # Color coding for confidence
        if signal.confidence >= 0.8:
            confidence_indicator = '🟢'
        elif signal.confidence >= 0.6:
            confidence_indicator = '🟡'
        else:
            confidence_indicator = '🟠'
        
        return f"""<b>{direction_emoji} PREMIUM SIGNAL #{signal.signal_id}</b>

<b>━━━━━━━━━━━━━━━━━</b>
<code>{signal.pair.ljust(10)} {signal.direction.ljust(5)}</code>

<b>Entry:</b> <code>{signal.entry:.6f}</code>
<b>Stop:</b> <code>{signal.stop_loss:.6f}</code>

<b>🎯 Take Profits:</b>
  TP1: <code>{signal.tp1:.6f}</code>
  TP2: <code>{signal.tp2:.6f}</code>
  TP3: <code>{signal.tp3:.6f}</code>

<b>━━━━━━━━━━━━━━━━━</b>
<b>Position Size:</b> {signal.position_size:.4f}
<b>Risk/Reward:</b> 1:{signal.risk_reward:.2f}
<b>Risk %:</b> {signal.risk_percent:.2f}%

<b>📊 Analysis:</b>
  ML Score: {signal.ml_score:.2f}/1.0
  Confidence: {confidence_indicator} {signal.confidence:.0%}
  Setup: {signal.setup_type}

<b>━━━━━━━━━━━━━━━━━</b>
<i>Generated: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>

#Premium #{signal.pair} #{signal.direction}"""
    
    def _format_daily_report(self, report: Dict) -> str:
        """Format daily report"""
        total_pnl = report.get('total_pnl', 0)
        win_rate = report.get('win_rate', 0)
        pnl_emoji = '📈' if total_pnl > 0 else '📉' if total_pnl < 0 else '⏸️'
        
        return f"""<b>📊 Daily Performance Report</b>
<code>{datetime.now().strftime('%Y-%m-%d')}</code>

<b>━━━━━━━━━━━━━━━━━</b>
<b>📈 Trading Activity:</b>
  Total Signals: {report.get('total_signals', 0)}
  Executed: {report.get('executed', 0)}
  Pending: {report.get('pending', 0)}

<b>✅ Results:</b>
  Wins: {report.get('wins', 0)} ({report.get('win_rate', 0):.1f}%)
  Losses: {report.get('losses', 0)}
  Breakeven: {report.get('breakeven', 0)}

<b>{pnl_emoji} P&L:</b>
  Today: {total_pnl:+.2f} pips
  Week: {report.get('weekly_pnl', 0):+.2f} pips
  Month: {report.get('monthly_pnl', 0):+.2f} pips

<b>📉 Risk Metrics:</b>
  Max Drawdown: {report.get('max_dd', 0):.2f}%
  Sharpe Ratio: {report.get('sharpe', 0):.2f}
  Avg Trade: {report.get('avg_trade', 0):.2f} pips

<b>━━━━━━━━━━━━━━━━━</b>
<b>🎯 Tomorrow's Outlook:</b>
{report.get('outlook', 'Market conditions neutral')}

<i>Report Time: {datetime.now().strftime('%H:%M:%S UTC')}</i>"""
    
    def _format_status_update(self, signal_id: str, status: str, details: Dict = None) -> str:
        """Format status update message"""
        status_emoji_map = {
            'FILLED': '✅',
            'TP1_HIT': '🎯',
            'TP2_HIT': '🎯🎯',
            'TP3_HIT': '🎯🎯🎯',
            'SL_HIT': '❌',
            'CANCELLED': '⏹️',
            'TIMEOUT': '⏱️'
        }
        
        emoji = status_emoji_map.get(status, '⏸️')
        details = details or {}
        
        return f"""<b>{emoji} Signal Update</b>

<b>Signal ID:</b> <code>{signal_id}</code>
<b>Status:</b> <code>{status}</code>

<b>Details:</b>
  Price: {details.get('price', 'N/A')}
  Time: {details.get('time', 'N/A')}
  P&L: {details.get('pnl', 'N/A')}

<i>{datetime.now().strftime('%H:%M:%S UTC')}</i>"""


class AlertManager:
    """Manages different types of alerts and routing"""
    
    def __init__(self, telegram_bot: TelegramSignalBot):
        self.bot = telegram_bot
        self.alert_queue = asyncio.Queue()
        self.alert_history = []
    
    async def queue_alert(self, alert_type: str, message: str, level: str = 'INFO'):
        """Queue alert for sending"""
        await self.alert_queue.put({
            'type': alert_type,
            'message': message,
            'level': level,
            'timestamp': datetime.now()
        })
    
    async def process_alerts(self):
        """Process queued alerts"""
        while True:
            try:
                alert = await asyncio.wait_for(self.alert_queue.get(), timeout=1)
                
                await self.bot.send_alert(
                    title=alert['type'],
                    body=alert['message'],
                    level=alert['level']
                )
                
                self.alert_history.append(alert)
                
                # Keep only last 1000 alerts
                if len(self.alert_history) > 1000:
                    self.alert_history = self.alert_history[-1000:]
                
            except asyncio.TimeoutError:
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Alert processing error: {e}")
