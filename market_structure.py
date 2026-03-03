# analyzer/market_structure.py

import pandas as pd
import numpy as np

class MarketStructure:
    """
    Market Structure Analysis: BOS, MSS, OrderBlocks, Liquidity Sweeps
    """
    def __init__(self, df: pd.DataFrame, timeframe="LTF"):
        self.df = df.copy()
        self.timeframe = timeframe

    def get_structure_bias(self):
        """
        Returns 'Bullish', 'Bearish', or 'Neutral' based on recent BOS.
        """
        points = self.identify_structure_points()
        events = self.detect_bos_mss(points)
        
        last_bos = next((e for e in reversed(events) if 'BOS' in e['type']), None)
        if last_bos:
            return "Bullish" if "Bullish" in last_bos['type'] else "Bearish"
        return "Neutral"

class MTFMarketStructure:
    """
    Multi-Timeframe Market Structure Analysis
    """
    def __init__(self, htf_df: pd.DataFrame, ltf_df: pd.DataFrame):
        self.htf = MarketStructure(htf_df, timeframe="HTF")
        self.ltf = MarketStructure(ltf_df, timeframe="LTF")

    def analyze(self):
        """
        HTF Bias + LTF Entry Logic
        """
        htf_bias = self.htf.get_structure_bias()
        
        # We only look for LTF entries if HTF is Bullish (for Bullish Sniper)
        if htf_bias != "Bullish":
            return {"status": "Rejected", "reason": f"HTF Bias is {htf_bias}"}
            
        # LTF Calculations
        from utils.indicators import identify_fvg
        ltf_fvgs = identify_fvg(self.ltf.df)
        
        ltf_points = self.ltf.identify_structure_points()
        ltf_events = self.ltf.detect_bos_mss(ltf_points)
        ltf_sweeps = self.ltf.detect_liquidity_sweep(ltf_points)
        ltf_obs = self.ltf.identify_order_blocks(ltf_fvgs)
        
        setups = self.ltf.identify_high_prob_setups(ltf_fvgs, ltf_obs, ltf_sweeps, ltf_events)
        
        return {
            "htf_bias": htf_bias,
            "ltf_setups": setups,
            "status": "Potential" if setups else "No Setup"
        }

    def detect_pivots(self, window=5):
        """
        Detects significant swing highs and swing lows.
        """
        highs = self.df['high'].values
        lows = self.df['low'].values
        
        self.df['swing_high'] = False
        self.df['swing_low'] = False
        
        for i in range(window, len(self.df) - window):
            if all(highs[i] > highs[i-j] for j in range(1, window+1)) and \
               all(highs[i] > highs[i+j] for j in range(1, window+1)):
                self.df.at[self.df.index[i], 'swing_high'] = True
                
            if all(lows[i] < lows[i-j] for j in range(1, window+1)) and \
               all(lows[i] < lows[i+j] for j in range(1, window+1)):
                self.df.at[self.df.index[i], 'swing_low'] = True
        
        return self.df

    def identify_structure_points(self):
        """
        Identifies HH, HL, LH, LL based on detected swing points.
        """
        self.detect_pivots()
        points = []
        last_high = None
        last_low = None
        
        for idx, row in self.df.iterrows():
            if row['swing_high']:
                label = "H"
                if last_high is not None:
                    label = "HH" if row['high'] > last_high else "LH"
                last_high = row['high']
                points.append({'index': idx, 'type': label, 'price': row['high']})
                
            if row['swing_low']:
                label = "L"
                if last_low is not None:
                    label = "HL" if row['low'] > last_low else "LL"
                last_low = row['low']
                points.append({'index': idx, 'type': label, 'price': row['low']})
        
        return points

    def detect_bos_mss(self, points):
        """
        Detects Break of Structure (BOS) and Market Structure Shift (MSS).
        BOS: Trend continuation (breaking a structural high/low).
        MSS: Trend reversal (breaking an internal high/low after a sweep).
        """
        events = []
        if len(points) < 4:
            return events

        for i in range(2, len(self.df)):
            current_close = self.df['close'].iloc[i]
            prev_points = [p for p in points if p['index'] < self.df.index[i]]
            
            if not prev_points:
                continue
                
            last_hh = next((p for p in reversed(prev_points) if p['type'] == "HH"), None)
            last_ll = next((p for p in reversed(prev_points) if p['type'] == "LL"), None)
            last_hl = next((p for p in reversed(prev_points) if p['type'] == "HL"), None)
            last_lh = next((p for p in reversed(prev_points) if p['type'] == "LH"), None)

            # Bullish BOS: Close above last HH
            if last_hh and current_close > last_hh['price']:
                events.append({'index': self.df.index[i], 'type': 'BOS Bullish', 'price': current_close})
            
            # Bearish BOS: Close below last LL
            if last_ll and current_close < last_ll['price']:
                events.append({'index': self.df.index[i], 'type': 'BOS Bearish', 'price': current_close})
            
            # MSS detection (Shift) - often occurs after a liquidity sweep
            # For simplicity, if we break the most recent HL/LH we call it MSS/ChoCh
            if last_hl and current_close < last_hl['price']:
                events.append({'index': self.df.index[i], 'type': 'MSS Bearish', 'price': current_close})
            if last_lh and current_close > last_lh['price']:
                events.append({'index': self.df.index[i], 'type': 'MSS Bullish', 'price': current_close})

        return events

    def detect_liquidity_sweep(self, points):
        """
        Detects if a recent low (bullish entry) or high (bearish entry) has been swept.
        Includes EH, EL, and PDL/PDH.
        """
        sweeps = []
        from utils.indicators import identify_liquidity_zones, calculate_session_levels
        
        liq_zones = identify_liquidity_zones(self.df)
        session_levels = calculate_session_levels(self.df)
        
        pdl = session_levels.get('PDL')
        pdh = session_levels.get('PDH')
        
        for i in range(1, len(self.df)):
            low = self.df['low'].iloc[i]
            high = self.df['high'].iloc[i]
            close = self.df['close'].iloc[i]
            
            prev_points = [p for p in points if p['index'] < self.df.index[i]]
            if not prev_points: continue
            
            # 1. Sweep of Swing Lows (HL, LL)
            recent_lows = [p for p in prev_points if "L" in p['type']][-5:]
            for rl in recent_lows:
                if low < rl['price'] and close > rl['price']:
                    sweeps.append({'index': self.df.index[i], 'type': 'Liquidity Sweep Low', 'level': rl['price'], 'target': rl['type']})
                    break
            
            # 2. Sweep of Equal Lows (EL)
            for el in liq_zones.get('EL', []):
                if low < el['price'] and close > el['price']:
                    sweeps.append({'index': self.df.index[i], 'type': 'Liquidity Sweep Low', 'level': el['price'], 'target': 'EL'})
                    break
                    
            # 3. Sweep of PDL
            if pdl and low < pdl and close > pdl:
                sweeps.append({'index': self.df.index[i], 'type': 'Liquidity Sweep Low', 'level': pdl, 'target': 'PDL'})

            # 4. Sweep of Swing Highs (HH, LH)
            recent_highs = [p for p in prev_points if "H" in p['type']][-5:]
            for rh in recent_highs:
                if high > rh['price'] and close < rh['price']:
                    sweeps.append({'index': self.df.index[i], 'type': 'Liquidity Sweep High', 'level': rh['price'], 'target': rh['type']})
                    break
                    
            # 5. Sweep of PDH
            if pdh and high > pdh and close < pdh:
                sweeps.append({'index': self.df.index[i], 'type': 'Liquidity Sweep High', 'level': pdh, 'target': 'PDH'})
                    
        return sweeps

    def identify_order_blocks(self, fvgs, events):
        """
        Professional Bullish Order Block (OB):
        1. Last bearish candle before a bullish impulse.
        2. Impulse MUST cause a BOS (Break of Structure) of a significant swing high.
        3. Impulse MUST create a Fair Value Gap (FVG).
        4. Impulse MUST have high volume.
        5. OB is invalidated if too small (ATR check) or in premium zone.
        """
        obs = []
        avg_volume = self.df['volume'].rolling(20).mean()
        atr = self.df['high'].rolling(14).max() - self.df['low'].rolling(14).min() # Simplified ATR
        avg_atr = atr.rolling(20).mean().iloc[-1]

        for i in range(2, len(self.df) - 5):
            # Bullish OB: Last down candle before strong move up
            if self.df['close'].iloc[i-1] < self.df['open'].iloc[i-1]:
                ob_candle = self.df.iloc[i-1]
                
                # Check OB size (not too small)
                if (ob_candle['high'] - ob_candle['low']) < avg_atr * 0.3:
                    continue

                # Check for strong impulse immediately after
                expansion_candle = self.df.iloc[i]
                if expansion_candle['close'] > ob_candle['high'] and \
                   self.df['volume'].iloc[i] > avg_volume.iloc[i] * 1.2:
                    
                    # 1. Did this move cause a BOS?
                    # We check if any candle in the next 5 periods closes above a recent HH/H
                    move_high = self.df['close'].iloc[i:i+5].max()
                    has_bos = any(e['type'] == 'BOS Bullish' and e['index'] >= self.df.index[i] and e['index'] <= self.df.index[min(i+5, len(self.df)-1)] for e in events)
                    
                    if not has_bos:
                        continue

                    # 2. Is there an FVG created by this impulse?
                    has_fvg = any(f['index'] in [i, i+1] and f['type'] == 'Bullish FVG' for f in fvgs)
                    if not has_fvg:
                        continue

                    # 3. Mitigation Check (Max 2 returns allowed)
                    ob_high = ob_candle['high']
                    ob_low = ob_candle['low']
                    future_lows = self.df['low'].iloc[i+1:]
                    mitigations = len([l for l in future_lows if l < ob_high])
                    
                    if mitigations >= 2:
                        continue

                    obs.append({
                        'type': 'Bullish OB',
                        'price': (ob_low + ob_high) / 2, # Equilibrium
                        'high': ob_high,
                        'low': ob_low,
                        'index': i-1,
                        'mitigations': mitigations,
                        'volume_score': 1 if self.df['volume'].iloc[i] > avg_volume.iloc[i] * 1.5 else 0
                    })
        
        return obs[-3:]

    def identify_high_prob_setups(self, fvgs, obs, sweeps, events):
        """
        SMC Scoring System (Setup only valid if Score >= 7):
        - Clean Sweep (under HL/PDL): 2 pts
        - Strong MSS (Market Structure Shift): 2 pts
        - Professional OB (Large, clean, unmitigated): 2 pts
        - Clean FVG (Gap presence): 1 pt
        - Deep Discount (OTE 61.8-79.6%): 1 pt
        - Impulsive Volume (>1.5x avg): 1 pt
        """
        setups = []
        
        # Check for recent sweep
        recent_sweep = next((s for s in reversed(sweeps) if s['type'] == 'Liquidity Sweep Low'), None)
        if not recent_sweep:
            return []

        # Check for MSS Bullish after that sweep
        recent_mss = next((e for e in reversed(events) if e['type'] == 'MSS Bullish' and e['index'] >= recent_sweep['index']), None)
        if not recent_mss:
            return []

        # Scoring components
        sweep_score = 2 # Validated by recent_sweep presence
        mss_score = 2 # Validated by recent_mss presence

        # Fibonacci for Discount check
        trend_low = recent_sweep['level']
        trend_high = self.df['high'].max()
        mid = (trend_low + trend_high) / 2
        ote_low = trend_high - 0.786 * (trend_high - trend_low)
        ote_high = trend_high - 0.618 * (trend_high - trend_low)

        for ob in obs:
            if ob['type'] != 'Bullish OB' or ob['index'] < recent_sweep['index']:
                continue
                
            # OB must be in discount
            if ob['price'] > mid:
                continue

            # OB Score
            ob_score = 2 if ob['mitigations'] == 0 else 1
            fvg_score = 1 # identify_order_blocks already checks for FVG presence
            discount_score = 1 if ote_low <= ob['price'] <= ote_high else 0
            volume_score = ob.get('volume_score', 0)
            
            total_score = sweep_score + mss_score + ob_score + fvg_score + discount_score + volume_score
            
            if total_score >= 7:
                setups.append({
                    "pattern": "Bullish Sniper (Institutional)",
                    "score": total_score,
                    "zone": f"OrderBlock @ {ob['price']} {'(OTE)' if discount_score else '(Discount)'}",
                    "bias": "Bullish",
                    "sl": min(recent_sweep['level'], ob['low']),
                    "tp": trend_high,
                    "max_rr": round((trend_high - ob['price']) / (ob['price'] - min(recent_sweep['level'], ob['low'])), 2)
                })

        return setups

    def full_report(self):
        """
        Generates a text report of the technical analysis
        """
        points = self.identify_structure_points()
        events = self.detect_bos_mss(points)
        sweeps = self.detect_liquidity_sweep(points)
        
        from utils.indicators import identify_fvg
        fvgs = identify_fvg(self.df)
        obs = self.identify_order_blocks(fvgs)
        setups = self.identify_high_prob_setups(fvgs, obs, sweeps, events)
        
        bias = self.get_structure_bias()
        
        report = f"Structure: {bias}\n"
        
        if setups:
            report += "\n🔥 INSTITUTIONAL SETUPS (SCORE >= 7):\n"
            for s in setups:
                report += f"- {s['pattern']} (Score: {s['score']}/9): {s['bias']} at {s['zone']} | RR: {s['max_rr']}\n"
        else:
            report += "\nNo institutional-grade setups detected (Score < 7).\n"
            
        report += "\nLast OrderBlocks:\n"
        for ob in obs:
            report += f"- {ob['type']} at {ob['price']} (Zone: {ob['low']:.2f}-{ob['high']:.2f})\n"
        
        report += "\nRecent Sweeps:\n"
        for sw in sweeps[-3:]:
            report += f"- {sw['type']} of {sw['target']} at {sw['level']:.2f}\n"
            
        return report
