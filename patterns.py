# amd/patterns.py

import pandas as pd
import numpy as np

class PatternEngine:
    """
    Japanese Candlestick and SMC Patterns Detection
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def detect_candlesticks(self):
        """
        Detects common high-probability candlestick patterns
        """
        patterns = []
        for i in range(1, len(self.df)):
            # 1. Pinbar (Hammer/Shooting Star)
            body = abs(self.df['close'].iloc[i] - self.df['open'].iloc[i])
            range_cand = self.df['high'].iloc[i] - self.df['low'].iloc[i]
            
            if range_cand > 0:
                # Bullish Pinbar: Large lower wick
                if (self.df['low'].iloc[i] < min(self.df['open'].iloc[i], self.df['close'].iloc[i]) - 2 * body):
                    patterns.append({'type': 'Bullish Pinbar', 'index': i, 'price': self.df['low'].iloc[i]})
                
                # Bearish Pinbar: Large upper wick
                elif (self.df['high'].iloc[i] > max(self.df['open'].iloc[i], self.df['close'].iloc[i]) + 2 * body):
                    patterns.append({'type': 'Bearish Pinbar', 'index': i, 'price': self.df['high'].iloc[i]})

            # 2. Engulfing
            if i > 1:
                prev_body = abs(self.df['close'].iloc[i-1] - self.df['open'].iloc[i-1])
                curr_body = abs(self.df['close'].iloc[i] - self.df['open'].iloc[i])
                
                # Bullish Engulfing
                if (self.df['close'].iloc[i] > self.df['open'].iloc[i] and 
                    self.df['close'].iloc[i-1] < self.df['open'].iloc[i-1] and 
                    curr_body > prev_body):
                    patterns.append({'type': 'Bullish Engulfing', 'index': i, 'price': self.df['low'].iloc[i]})
                
                # Bearish Engulfing
                elif (self.df['close'].iloc[i] < self.df['open'].iloc[i] and 
                      self.df['close'].iloc[i-1] > self.df['open'].iloc[i-1] and 
                      curr_body > prev_body):
                    patterns.append({'type': 'Bearish Engulfing', 'index': i, 'price': self.df['high'].iloc[i]})

        return patterns[-5:]

    def detect_liquidity_sweep(self):
        """
        Detects stop hunts/liquidity sweeps: Price breaks a pivot and reverses quickly
        """
        sweeps = []
        for i in range(10, len(self.df)):
            lookback = self.df.iloc[i-10:i]
            prev_high = lookback['high'].max()
            prev_low = lookback['low'].min()
            
            # Liquidity Sweep High: Price goes above previous high then closes below it
            if self.df['high'].iloc[i] > prev_high and self.df['close'].iloc[i] < prev_high:
                sweeps.append({'type': 'Sweep High (BISI)', 'index': i, 'price': self.df['high'].iloc[i]})
                
            # Liquidity Sweep Low: Price goes below previous low then closes above it
            elif self.df['low'].iloc[i] < prev_low and self.df['close'].iloc[i] > prev_low:
                sweeps.append({'type': 'Sweep Low (SIBI)', 'index': i, 'price': self.df['low'].iloc[i]})
                
        return sweeps[-3:]
