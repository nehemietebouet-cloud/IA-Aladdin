# analyzer/market_structure.py

import pandas as pd
import numpy as np

class MarketStructure:
    """
    Market Structure Analysis: BOS, ChoCh, OrderBlocks
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def detect_pivots(self, window=5):
        self.df['hh'] = self.df['high'] == self.df['high'].rolling(window=window*2+1, center=True).max()
        self.df['ll'] = self.df['low'] == self.df['low'].rolling(window=window*2+1, center=True).min()
        return self.df

    def detect_bos_choch(self):
        # Simplistic BOS/ChoCh detection logic
        # BOS: Break of recent high in uptrend, or low in downtrend
        # ChoCh: Change of character (first sign of reversal)
        
        last_high = self.df['high'].rolling(window=20).max().iloc[-1]
        last_low = self.df['low'].rolling(window=20).min().iloc[-1]
        
        current_close = self.df['close'].iloc[-1]
        prev_close = self.df['close'].iloc[-2]

        structure = "Neutral"
        if current_close > last_high:
            structure = "BOS Bullish"
        elif current_close < last_low:
            structure = "BOS Bearish"
            
        return structure

    def identify_order_blocks(self):
        # OrderBlock: The last opposite candle before a strong move
        obs = []
        for i in range(2, len(self.df) - 1):
            # Bullish OB: Bearish candle followed by a strong bullish move (expansion)
            if self.df['close'].iloc[i-1] < self.df['open'].iloc[i-1]: # Bearish
                if self.df['close'].iloc[i] > self.df['high'].iloc[i-1]: # Expansion
                    obs.append({'type': 'Bullish OB', 'price': self.df['low'].iloc[i-1], 'index': i-1})
            
            # Bearish OB: Bullish candle followed by a strong bearish move
            if self.df['close'].iloc[i-1] > self.df['open'].iloc[i-1]: # Bullish
                if self.df['close'].iloc[i] < self.df['low'].iloc[i-1]: # Expansion
                    obs.append({'type': 'Bearish OB', 'price': self.df['high'].iloc[i-1], 'index': i-1})
        
        return obs[-3:] # Return last 3 OBs

    def identify_high_prob_setups(self, fvgs, obs):
        """
        Filters for "Unicorn" and "Silver Bullet" patterns based on historical alignment
        """
        setups = []
        current_price = self.df['close'].iloc[-1]
        
        # 1. Unicorn Setup (Breaker Block + FVG)
        # We need to check if an FVG is nested or overlapping with a Breaker
        for ob in obs:
            if "Breaker" in ob.get('type', ''):
                for fvg in fvgs:
                    if (fvg['bottom'] <= ob['high'] and fvg['top'] >= ob['low']):
                        setups.append({
                            "pattern": "Unicorn Setup",
                            "probability": "High",
                            "zone": f"Breaker @ {ob['price']} + FVG",
                            "bias": "Bullish" if "Bullish" in fvg['type'] else "Bearish"
                        })
        
        # 2. MSS (Market Structure Shift) + Return to OrderBlock
        bos = self.detect_bos_choch()
        if "BOS" in bos:
            last_ob = obs[-1] if obs else None
            if last_ob and abs(current_price - last_ob['price']) / last_ob['price'] < 0.01:
                setups.append({
                    "pattern": "MSS + Retest",
                    "probability": "Very High",
                    "zone": f"OrderBlock @ {last_ob['price']}",
                    "bias": "Bullish" if "Bullish" in bos else "Bearish"
                })
        
        return setups

    def full_report(self, fvgs, fib_levels):
        """
        Generates a text report of the technical analysis
        """
        bos = self.detect_bos_choch()
        obs = self.identify_order_blocks()
        setups = self.identify_high_prob_setups(fvgs, obs)
        
        report = f"Structure: {bos}\n"
        
        if setups:
            report += "\n🔥 HIGH PROBABILITY PATTERNS DETECTED:\n"
            for s in setups:
                report += f"- {s['pattern']} ({s['probability']}): {s['bias']} at {s['zone']}\n"
        else:
            report += "\nNo high-probability patterns currently active.\n"
            
        report += "\nLast OrderBlocks:\n"
        for ob in obs:
            report += f"- {ob['type']} at {ob['price']}\n"
        
        report += "\nFVGs Found:\n"
        for fvg in fvgs:
            report += f"- {fvg['type']} between {fvg['bottom']} and {fvg['top']}\n"
            
        report += f"\nOTE Zones: {fib_levels['0.618']:.2f} - {fib_levels['0.786']:.2f}"
        
        return report
