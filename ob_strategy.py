# analyzer/ob_strategy.py

import pandas as pd
import numpy as np
from datetime import datetime, time
from utils.indicators import calculate_atr, identify_fvg, get_market_zone

class OBStrategy:
    def __init__(self, df, risk_per_trade=0.01):
        self.df = df
        self.risk_per_trade = risk_per_trade

    def detect_bos_mss(self, window=20):
        """Detect Break of Structure (BOS) or Market Structure Shift (MSS)"""
        highs = self.df['high'].rolling(window=window).max()
        lows = self.df['low'].rolling(window=window).min()
        
        bos_bullish = self.df['close'].iloc[-1] > highs.iloc[-2]
        bos_bearish = self.df['close'].iloc[-1] < lows.iloc[-2]
        
        return bos_bullish, bos_bearish

    def detect_liquidity_sweep(self, lookback=30):
        """Detect if the last few candles swept liquidity below/above previous swing points"""
        recent_lows = self.df['low'].iloc[-lookback:-1].min()
        recent_highs = self.df['high'].iloc[-lookback:-1].max()
        
        sweep_bullish = self.df['low'].iloc[-1] < recent_lows and self.df['close'].iloc[-1] > recent_lows
        sweep_bearish = self.df['high'].iloc[-1] > recent_highs and self.df['close'].iloc[-1] < recent_highs
        
        return sweep_bullish, sweep_bearish

    def get_order_blocks(self):
        """Professional OB Detection with Scoring"""
        obs = []
        df = self.df
        
        # 1. Look for the last bearish candle before a bullish impulse
        for i in range(len(df) - 5, 1, -1):
            # Bullish OB candidate (Last red candle before green impulse)
            if df['close'].iloc[i] < df['open'].iloc[i]:
                # Strong impulse check (at least 2 strong green candles after)
                if df['close'].iloc[i+1] > df['open'].iloc[i+1] and df['close'].iloc[i+2] > df['open'].iloc[i+2]:
                    # Impulse must break a swing high (BOS/MSS)
                    swing_high = df['high'].iloc[max(0, i-20):i].max()
                    if df['close'].iloc[i+2] > swing_high:
                        
                        # OB identified, now score it
                        score = 0
                        
                        # a. Sweep (2 points)
                        sweep_bull, _ = self.detect_liquidity_sweep(lookback=20)
                        if sweep_bull: score += 2
                        
                        # b. MSS/BOS (2 points)
                        if df['close'].iloc[i+2] > swing_high: score += 2
                        
                        # c. Clear OB (2 points)
                        ob_body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
                        avg_body_size = abs(df['close'] - df['open']).tail(50).mean()
                        if ob_body_size > avg_body_size * 0.5: score += 2
                        
                        # d. FVG (1 point)
                        fvgs = identify_fvg(df.iloc[:i+5])
                        has_fvg = any(f['type'] == 'Bullish FVG' and f['index'] > i for f in fvgs)
                        if has_fvg: score += 1
                        
                        # e. Discount Zone (1 point)
                        swing_low = df['low'].iloc[max(0, i-50):i+5].min()
                        swing_high_after = df['high'].iloc[i:i+5].max()
                        zone = get_market_zone(df['close'].iloc[i], swing_high_after, swing_low)
                        if zone == "Discount Zone": score += 1
                        
                        # f. Volume (1 point)
                        volume_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
                        if volume_col in df.columns and df[volume_col].iloc[i+1] > df[volume_col].iloc[i]: 
                            score += 1
                        
                        obs.append({
                            'type': 'Bullish OB',
                            'index': i,
                            'high': df['high'].iloc[i],
                            'low': df['low'].iloc[i],
                            'open': df['open'].iloc[i],
                            'close': df['close'].iloc[i],
                            'score': score,
                            'fvg': has_fvg,
                            'discount': zone == "Discount Zone"
                        })
        return obs

    def is_time_valid(self):
        """Check if current time is within London or NY sessions (UTC)"""
        now_utc = datetime.utcnow().time()
        
        london_start, london_end = time(8, 0), time(16, 0)
        ny_start, ny_end = time(13, 0), time(21, 0)
        
        is_london = london_start <= now_utc <= london_end
        is_ny = ny_start <= now_utc <= ny_end
        
        return is_london or is_ny

    def get_signal(self):
        # Time Filter
        if not self.is_time_valid():
            return None

        obs = self.get_order_blocks()
        if not obs: return None
        
        best_ob = max(obs, key=lambda x: x['score'])
        
        if best_ob['score'] >= 7:
            # 3 green candles check: don't chase if expansion already far
            last_3 = self.df['close'].tail(3) > self.df['open'].tail(3)
            if last_3.all():
                return None # "Chasseur fatigué"

            # Entry points: 50% or High
            entry_high = best_ob['high']
            entry_mid = (best_ob['high'] + best_ob['low']) / 2
            
            # Risk Management
            sl = best_ob['low'] - (calculate_atr(self.df).iloc[-1] * 0.2)
            tp = entry_high + (entry_high - sl) * 2.5 # RR 2.5
            
            return {
                'action': 'Buy',
                'entry': entry_mid, # Sniper entry at 50%
                'sl': sl,
                'tp': tp,
                'score': best_ob['score'],
                'ob': best_ob
            }
        return None
