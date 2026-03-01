# analyzer/market_regime.py

import pandas as pd
import numpy as np
from utils.indicators import calculate_adx, calculate_atr

class MarketRegime:
    """
    Detects Market Regimes: Bull, Bear, Range, Volatile, Panic
    """
    def __init__(self, df):
        self.df = df.copy()

    def detect_regime(self, window=20):
        """
        Advanced Regime Detection: Trend, Volatility, Strength (ADX)
        """
        # 1. Trend (EMA 50 vs Price)
        ema_50 = self.df['close'].ewm(span=50, adjust=False).mean()
        price = self.df['close']
        trend = "Bull" if price.iloc[-1] > ema_50.iloc[-1] else "Bear"
        
        # 2. Strength (ADX)
        adx = calculate_adx(self.df)
        strength = "Strong" if adx.iloc[-1] > 25 else "Weak"
        
        # 3. Volatility (ATR-based)
        atr = calculate_atr(self.df, period=window)
        avg_atr = atr.rolling(window=100).mean()
        
        volatility_state = "Normal"
        if atr.iloc[-1] > avg_atr.iloc[-1] * 2.0:
            volatility_state = "Panic"
        elif atr.iloc[-1] > avg_atr.iloc[-1] * 1.5:
            volatility_state = "High"
        elif atr.iloc[-1] < avg_atr.iloc[-1] * 0.7:
            volatility_state = "Consolidation (Range)"

        # 4. Final Classification
        if volatility_state == "Panic":
            return "Extreme Volatility (Panic Mode)"
        if volatility_state == "Consolidation (Range)":
            return "Range-Bound Market (Low Liquidity)"
        
        return f"{strength} {trend}ish Regime ({volatility_state} Volatility)"

    def get_strategy_adjustment(self, regime):
        """
        Adapts strategy parameters based on regime
        """
        if "Panic" in regime:
            return {"risk_multiplier": 0.5, "tp_target": 1.5, "sl_type": "Tight"}
        elif "Range" in regime:
            return {"risk_multiplier": 0.8, "tp_target": 2.0, "sl_type": "ATR"}
        else:
            return {"risk_multiplier": 1.0, "tp_target": 3.0, "sl_type": "Structural"}
