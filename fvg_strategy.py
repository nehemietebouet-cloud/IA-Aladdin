# analyzer/fvg_strategy.py

import pandas as pd
import numpy as np
from datetime import datetime, time
from analyzer.liquidity_analyzer import LiquidityAnalyzer
from utils.indicators import identify_fvg, get_market_zone, detect_htf_trend, calculate_atr

class FVGSniper:
    def __init__(self, df, df_htf=None):
        self.df = df
        self.df_htf = df_htf
        self.liquidity = LiquidityAnalyzer(df)

    def get_fvg_score(self, fvg, ob_present=False):
        score = 0
        
        # 1. Structure HTF bullish (2 pts)
        if self.df_htf is not None and detect_htf_trend(self.df_htf):
            score += 2
            
        # 2. BOS clair (2 pts)
        if self.detect_bos():
            score += 2
            
        # 3. Displacement fort (2 pts)
        if fvg['displacement']:
            score += 2
            
        # 4. Liquidity sweep avant (2 pts)
        if self.liquidity.is_liquidity_taken_before_expansion(fvg['index']):
            score += 2
        elif self.detect_liquidity_sweep():
            score += 1 # Standard sweep if not immediately before
            
        # 5. FVG en Discount Zone (2 pts)
        swing_low = self.df['low'].iloc[-50:].min()
        swing_high = self.df['high'].iloc[-50:].max()
        zone = get_market_zone(fvg['mid'], swing_high, swing_low)
        if zone == "Discount Zone":
            score += 2
            
        # 6. Engineered Liquidity (EH/EL) target (1 pt)
        context = self.liquidity.get_liquidity_context()
        if context['engineered_liquidity']['has_eh']:
            score += 1 # Magnet for BSL
            
        return score

    def get_signal(self):
        all_fvgs = identify_fvg(self.df)
        bullish_fvgs = [f for f in all_fvgs if f['type'] == 'Bullish FVG']
        
        if not bullish_fvgs:
            return None
            
        # Get latest FVG
        latest_fvg = bullish_fvgs[-1]
        score = self.get_fvg_score(latest_fvg)
        
        # Thresholds
        if score < 5: return None
        
        setup_type = "IGNORE"
        if score >= 10: setup_type = "SNIPER"
        elif score >= 7: setup_type = "CORRECT"
        elif score >= 5: setup_type = "FAIBLE"
        
        if setup_type == "IGNORE": return None
        
        # Entry Levels
        aggressive_entry = latest_fvg['top']
        mid_entry = latest_fvg['mid']
        conservative_entry = latest_fvg['bottom']
        
        # SL & TP
        swing_low = self.df['low'].iloc[-20:].min()
        sl = min(latest_fvg['bottom'], swing_low) - (calculate_atr(self.df).iloc[-1] * 0.1)
        tp = aggressive_entry + (aggressive_entry - sl) * 2.0 # Min RR 1:2
        
        return {
            'type': setup_type,
            'action': 'BUY',
            'score': score,
            'entries': {
                'aggressive': aggressive_entry,
                'mid': mid_entry,
                'conservative': conservative_entry
            },
            'sl': sl,
            'tp': tp,
            'fvg': latest_fvg
        }
