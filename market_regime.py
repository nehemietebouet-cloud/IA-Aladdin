# analyzer/market_regime.py

import pandas as pd
from utils.indicators import detect_htf_trend

class MarketRegime:
    def __init__(self, df_dxy, df_us100, df_xau, df_btc=None):
        self.df_dxy = df_dxy
        self.df_us100 = df_us100
        self.df_xau = df_xau
        self.df_btc = df_btc

    def detect_regime(self):
        """
        Detects the global market regime: Risk-On, Risk-Off, or Neutral.
        Risk-On: DXY Down, US100 Up, BTC Up.
        Risk-Off: DXY Up, US100 Down, XAU Up (Refuge).
        """
        if self.df_dxy is None or self.df_us100 is None:
            return "Neutral"

        dxy_bias = detect_htf_trend(self.df_dxy)
        us100_bias = detect_htf_trend(self.df_us100)
        xau_bias = detect_htf_trend(self.df_xau) if self.df_xau is not None else "Neutral"
        btc_bias = detect_htf_trend(self.df_btc) if self.df_btc is not None else "Neutral"

        # Risk-On Logic (Growth assets and Crypto performance)
        if dxy_bias == "Bearish" and (us100_bias == "Bullish" or btc_bias == "Bullish"):
            return "RISK-ON (Expansion Tech/Crypto)"
        
        # Risk-Off Logic (Dollar strength or Gold as safety)
        if dxy_bias == "Bullish":
            if us100_bias == "Bearish" or btc_bias == "Bearish":
                if xau_bias == "Bullish":
                    return "RISK-OFF (Flight to Safety/Gold)"
                return "RISK-OFF (Defensive Dollar)"

        # Specific Anti-Yield / Gold regime
        if xau_bias == "Bullish" and dxy_bias == "Bearish" and us100_bias == "Bearish":
            return "DEFLATIONARY / RECESSIONARY (Gold only)"

        return "NEUTRAL (Consolidation)"

    def get_institutional_bias(self, symbol):
        regime = self.detect_regime()
        
        # Scoring modifier based on regime
        if "RISK-ON" in regime:
            if symbol in ["US100", "NAS100", "BTCUSD"]: return 2 # Boost
            if symbol == "XAUUSD": return -1 # Caution
        
        if "RISK-OFF" in regime:
            if symbol == "XAUUSD": return 2 # Boost
            if symbol in ["US100", "NAS100", "BTCUSD"]: return -2 # Danger
            
        return 0
