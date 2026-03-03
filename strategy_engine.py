# analyzer/strategy_engine.py

import pandas as pd
import numpy as np
from utils.indicators import calculate_atr, calculate_rsi, calculate_bollinger_bands
from .market_regime import MarketRegime
from .market_structure import MarketStructure, MTFMarketStructure
from .risk_advanced import AdvancedRisk
from logger.log import logger

class StrategyEngine:
    """
    Adaptive Strategy Engine: Fuses SMC logic with Regime-specific rules.
    - Range: Mean Reversion, tight SL, short TP.
    - Bullish: Buy only at Discount OTE/Order Blocks.
    - Bearish: Sell only at Premium FVG/Breakers.
    """
    def __init__(self, df, account_balance=10000, htf_df=None, trade_history=[]):
        self.df = df.copy()
        self.htf_df = htf_df
        self.account_balance = account_balance
        self.trade_history = trade_history
        self.mr = MarketRegime(self.df)
        self.regime = self.mr.detect_regime()
        self.ms = MarketStructure(self.df)
        self.risk = AdvancedRisk(self.df, self.account_balance, self.trade_history)

    def is_market_quality_ok(self, min_atr_multiplier=1.5):
        """
        Market Quality Filter: 
        1. Min Volatility (ATR)
        2. No tight consolidation
        """
        atr = calculate_atr(self.df)
        avg_atr = atr.rolling(100).mean().iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Volatility check
        if current_atr < avg_atr * 0.8: # Low Volatility
            return False, "Market Quality: Too Low Volatility"
            
        # Consolidation check (Last 10 candles range vs ATR)
        recent_range = self.df['high'].iloc[-10:].max() - self.df['low'].iloc[-10:].min()
        if recent_range < current_atr * 2:
            return False, "Market Quality: Tight Consolidation"

        return True, "Quality OK"

    def is_time_safe(self):
        """
        Smart Time Filter: London & NY Sessions
        London: 08:00 - 17:00 UTC
        NY: 13:00 - 22:00 UTC
        Combined: 08:00 - 22:00 UTC
        """
        now = self.df.index[-1]
        hour = now.hour
        
        if not (8 <= hour <= 21):
            return False, "Outside Trading Sessions"
        
        return True, "Session Active"

    def check_overtrading(self, max_trades_per_session=3):
        """
        Anti-Overtrading Rules:
        - Max 3 trades per session
        - No revenge trading
        """
        today = self.df.index[-1].date()
        today_trades = [t for t in self.trade_history if pd.to_datetime(t.get('time')).date() == today]
        
        if len(today_trades) >= max_trades_per_session:
            return False, f"Anti-Overtrading: {len(today_trades)} trades today"
            
        # Revenge trading check: Stop if last trade was a loss < 1 hour ago
        if self.trade_history:
            last_trade = self.trade_history[-1]
            last_time = pd.to_datetime(last_trade.get('time'))
            if last_trade.get('profit', 0) < 0 and (self.df.index[-1] - last_time).seconds < 3600:
                return False, "Anti-Overtrading: Potential Revenge Trading"

        return True, "Overtrading Check OK"

    def is_volatility_safe(self, multiplier=2.5):
        """
        Volatility Filter: Detects extreme or dead markets.
        """
        atr = calculate_atr(self.df)
        avg_atr = atr.rolling(100).mean().iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Too volatile (Panic) or too dead (No liquidity)
        if current_atr > avg_atr * multiplier:
            return False, "Extreme Volatility Detected"
        if current_atr < avg_atr * 0.5:
            return False, "Low Liquidity Detected"
        
        return True, "Volatility Normal"

    def get_smc_bias(self):
        """
        Determines Premium vs Discount zones for SMC entries.
        """
        high = self.df['high'].rolling(50).max().iloc[-1]
        low = self.df['low'].rolling(50).min().iloc[-1]
        mid = (high + low) / 2
        current_price = self.df['close'].iloc[-1]
        
        if current_price > mid:
            return "Premium", high, mid
        else:
            return "Discount", mid, low

    def select_strategy(self, signals, current_spread=0):
        """
        Routes signals through regime-specific filters and global Kill Switch/Filters.
        """
        # 1. Global Kill Switch & Risk Check
        is_risk_ok, risk_msg = self.risk.check_kill_switch(current_spread=current_spread)
        if not is_risk_ok:
            return {"status": "Rejected", "reason": risk_msg}

        # 2. Time Filter
        is_time_ok, time_msg = self.is_time_safe()
        if not is_time_ok:
            return {"status": "Rejected", "reason": time_msg}

        # 3. Overtrading Check
        is_overtrading_ok, over_msg = self.check_overtrading()
        if not is_overtrading_ok:
            return {"status": "Rejected", "reason": over_msg}

        # 4. Market Quality Filter
        is_quality_ok, quality_msg = self.is_market_quality_ok()
        if not is_quality_ok:
            return {"status": "Rejected", "reason": quality_msg}

        # 5. Volatility Filter
        is_safe, msg = self.is_volatility_safe()
        if not is_safe:
            return {"status": "Rejected", "reason": msg}

        # 6. Dynamic Risk Calculation
        dynamic_risk_pct = self.risk.get_dynamic_risk()

        bias, top, bottom = self.get_smc_bias()
        
        strategy_result = None
        if "Range" in self.regime:
            strategy_result = self._range_strategy(signals, bias)
        elif "Bull" in self.regime:
            strategy_result = self._bullish_strategy(signals, bias)
        elif "Bear" in self.regime:
            strategy_result = self._bearish_strategy(signals, bias)
        
        if strategy_result and strategy_result['status'] == "Accepted":
            strategy_result['risk_pct'] = dynamic_risk_pct
            # Advanced Logging
            logger.trade_log(
                symbol=signals.get('symbol', 'UNKNOWN'),
                type=signals['type'],
                price=self.df['close'].iloc[-1],
                sl=strategy_result.get('sl', 0),
                tp=strategy_result.get('tp', 0),
                reason=strategy_result.get('note', 'No Reason'),
                regime=self.regime,
                rr_expected=strategy_result.get('max_rr', 0)
            )

        return strategy_result or {"status": "Neutral", "reason": "Undefined Regime"}

    def calculate_performance_metrics(self):
        """
        Calculates Win Rate, Profit Factor, Avg RR, Max Drawdown
        """
        if not self.trade_history:
            return None
            
        wins = [t for t in self.trade_history if t.get('profit', 0) > 0]
        losses = [t for t in self.trade_history if t.get('profit', 0) < 0]
        
        win_rate = (len(wins) / len(self.trade_history)) * 100 if self.trade_history else 0
        
        total_profit = sum(t.get('profit', 0) for t in wins)
        total_loss = abs(sum(t.get('profit', 0) for t in losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else total_profit
        
        rrs = [t.get('rr_realized', 0) for t in self.trade_history]
        avg_rr = np.mean(rrs) if rrs else 0
        
        balances = [t.get('balance_after', self.account_balance) for t in self.trade_history]
        peak = self.account_balance
        max_dd = 0
        for b in balances:
            if b > peak: peak = b
            dd = (peak - b) / peak
            if dd > max_dd: max_dd = dd
            
        return {
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_rr": round(avg_rr, 2),
            "max_dd": round(max_dd * 100, 2)
        }

    def _range_strategy(self, signals, bias):
        """
        Mean Reversion Logic for Range-bound markets.
        - Tight SL, Short TP, No breakouts.
        """
        # In a range, we trade towards the mean (mid)
        # Only allow signals that are at extremes
        rsi = calculate_rsi(self.df['close']).iloc[-1]
        
        if signals['type'] == "Bullish" and rsi < 35:
            return {
                "status": "Accepted", 
                "strategy": "Mean Reversion (Range)",
                "note": "RSI Oversold in Range",
                "max_rr": 2.5,
                "sl_style": "Tight"
            }
        elif signals['type'] == "Bearish" and rsi > 65:
            return {
                "status": "Accepted", 
                "strategy": "Mean Reversion (Range)",
                "note": "RSI Overbought in Range",
                "max_rr": 2.5,
                "sl_style": "Tight"
            }
        
        return {"status": "Rejected", "reason": "Range non-extreme"}

    def _bullish_strategy(self, signals, bias):
        """
        SMC Bullish Sniper Logic:
        1. HTF Bullish Bias (if htf_df provided)
        2. LTF Liquidity Sweep
        3. LTF MSS (Market Structure Shift)
        4. Buy in Discount / OTE Zone at OB or FVG
        5. Target External Liquidity (PH, EH)
        """
        if self.htf_df is not None:
            mtf = MTFMarketStructure(self.htf_df, self.df)
            analysis = mtf.analyze()
            
            if analysis['status'] == "Potential" and analysis['ltf_setups']:
                setup = analysis['ltf_setups'][-1]
                return {
                    "status": "Accepted",
                    "strategy": "Bullish Sniper (MTF SMC)",
                    "note": f"HTF Bullish + LTF Sweep & MSS. Zone: {setup['zone']}",
                    "sl": setup['sl'],
                    "tp": setup['tp'],
                    "max_rr": 5.0,
                    "sl_style": "Structural"
                }
            elif analysis['status'] == "Rejected":
                return {"status": "Rejected", "reason": analysis['reason']}

        # Fallback to basic SMC if MTF data not present
        if signals['type'] == "Bearish":
            return {"status": "Rejected", "reason": "Trend is Bullish - No Sells"}
            
        if bias == "Premium":
            return {"status": "Rejected", "reason": "Bullish Trend - Price in Premium (Wait for Pullback)"}
            
        return {
            "status": "Accepted", 
            "strategy": "Bullish Pullback (SMC)",
            "note": "Buying in Discount Zone",
            "max_rr": 5.0,
            "sl_style": "Structural",
            "partial_closure": True
        }

    def _bearish_strategy(self, signals, bias):
        """
        Breakout Continuation for Bearish Trends.
        - Sell only at Premium FVG/Breakers.
        - Max 2% SL, 4 RR TP.
        """
        if signals['type'] == "Bullish":
            return {"status": "Rejected", "reason": "Trend is Bearish - No Buys"}
            
        if bias == "Discount":
            return {"status": "Rejected", "reason": "Bearish Trend - Price in Discount (Wait for Retrace)"}
            
        return {
            "status": "Accepted", 
            "strategy": "Bearish Continuation (SMC)",
            "note": "Selling in Premium Zone",
            "max_rr": 4.0,
            "sl_style": "Structural",
            "partial_closure": True
        }
