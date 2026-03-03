# analyzer/liquidity_analyzer.py

import pandas as pd
import numpy as np
from utils.indicators import identify_liquidity_zones, calculate_session_levels

class LiquidityAnalyzer:
    def __init__(self, df, df_daily=None, df_weekly=None):
        self.df = df
        self.liquidity = identify_liquidity_zones(df)
        self.sessions = calculate_session_levels(df)
        self.htf_levels = None
        if df_daily is not None and df_weekly is not None:
            from utils.indicators import get_htf_levels
            self.htf_levels = get_htf_levels(df_daily, df_weekly)

    def get_liquidity_score(self, current_price):
        score = 0
        if not self.htf_levels: return 0
        
        # 1. Weekly H/L (3 pts)
        if abs(current_price - self.htf_levels['Weekly_High']) / current_price < 0.001: score += 3
        if abs(current_price - self.htf_levels['Weekly_Low']) / current_price < 0.001: score += 3
        
        # 2. Daily H/L (2 pts)
        if abs(current_price - self.htf_levels['Daily_High']) / current_price < 0.001: score += 2
        if abs(current_price - self.htf_levels['Daily_Low']) / current_price < 0.001: score += 2
        
        # 3. EH/EL (1 pt)
        if self.liquidity['EH']: score += 1
        if self.liquidity['EL']: score += 1
        
        # 4. Old High non testé (2 pts)
        for oh in self.htf_levels['Old_Highs']:
            if current_price < oh and (oh - current_price) / current_price < 0.002:
                score += 2
                break
        return score

    def get_draw_on_liquidity(self, trend='bullish'):
        if not self.htf_levels: return None
        if trend == 'bullish':
            targets = [self.htf_levels['Weekly_High'], self.htf_levels['Daily_High']]
            if self.liquidity['EH']: targets.append(self.liquidity['EH'][-1]['price'])
            return max(targets)
        else:
            targets = [self.htf_levels['Weekly_Low'], self.htf_levels['Daily_Low']]
            if self.liquidity['EL']: targets.append(self.liquidity['EL'][-1]['price'])
            return min(targets)

    def detect_sweep(self):
        last_low = self.df['low'].iloc[-1]
        last_high = self.df['high'].iloc[-1]
        last_close = self.df['close'].iloc[-1]
        
        for bsl in self.liquidity['BSL']:
            if last_high > bsl['price'] and last_close < bsl['price']:
                return {'type': 'BSL_SWEEP', 'price': bsl['price']}
        for ssl in self.liquidity['SSL']:
            if last_low < ssl['price'] and last_close > ssl['price']:
                return {'type': 'SSL_SWEEP', 'price': ssl['price']}
        return None

    def get_liquidity_context(self):
        return {
            'sweep': self.detect_sweep(),
            'external_bsl': self.liquidity['BSL'][-1]['price'] if self.liquidity['BSL'] else None,
            'external_ssl': self.liquidity['SSL'][-1]['price'] if self.liquidity['SSL'] else None,
            'engineered_liquidity': {
                'has_eh': len(self.liquidity['EH']) > 0,
                'has_el': len(self.liquidity['EL']) > 0
            }
        }

    def is_liquidity_taken_before_expansion(self, expansion_index):
        pre_expansion_df = self.df.iloc[max(0, expansion_index-10):expansion_index]
        if pre_expansion_df.empty: return False
        recent_lows = [s['price'] for s in self.liquidity['SSL'] if s['index'] < expansion_index-10]
        if not recent_lows: return False
        major_low = min(recent_lows)
        return pre_expansion_df['low'].min() < major_low and pre_expansion_df['close'].iloc[-1] > major_low
