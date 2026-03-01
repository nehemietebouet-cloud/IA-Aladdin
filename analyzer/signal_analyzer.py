# analyzer/signal_analyzer.py

import numpy as np
import pandas as pd
from scipy.stats import norm
from config import CONFIG

class SignalAnalyzer:
    """
    Advanced Risk Engine: VaR, Drawdown, Intelligent SL
    """
    def __init__(self, account_balance=10000):
        self.account_balance = account_balance
        self.risk_pct = CONFIG["risk_per_trade"]

    def calculate_var(self, df, confidence=0.95):
        """
        Value at Risk (VaR) calculation
        """
        returns = df['close'].pct_change().dropna()
        mu = np.mean(returns)
        sigma = np.std(returns)
        var = norm.ppf(1 - confidence, mu, sigma)
        return float(abs(var * self.account_balance))

    def calculate_drawdown(self, df):
        """
        Calculates Maximum Drawdown of the price
        """
        rolling_max = df['close'].cummax()
        drawdown = (df['close'] - rolling_max) / rolling_max
        return float(drawdown.min())

    def get_intelligent_sl(self, df, entry, bias):
        """
        Calculates SL based on ATR (Volatility)
        """
        # Simple ATR implementation
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        tr = ranges.max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        
        if bias == "Bullish":
            sl = entry - (2 * atr)
        else:
            sl = entry + (2 * atr)
            
        return float(sl)

    def calculate_trade_params(self, entry, sl, tp, bias):
        """
        Ensures risk is strictly below 2% and RR > 2
        """
        risk_per_unit = abs(entry - sl)
        reward_per_unit = abs(tp - entry)
        rr = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0
        
        dollar_risk = self.account_balance * self.risk_pct
        lot_size = dollar_risk / risk_per_unit if risk_per_unit > 0 else 0
        
        return {
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "rr": round(rr, 2),
            "lot_size": round(lot_size, 4),
            "dollar_risk": round(dollar_risk, 2),
            "is_valid": rr >= CONFIG["min_rr"]
        }
