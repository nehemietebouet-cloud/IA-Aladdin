# analyzer/institutional_score.py

import pandas as pd
from utils.indicators import detect_htf_trend, identify_fvg, identify_order_blocks, identify_liquidity_zones
from analyzer.market_regime import MarketRegime
from utils.macro_data import MacroEngine

class InstitutionalScore:
    """
    Calculates a Global Institutional Score (0-100) for an asset.
    Combines Macro, Intermarket (Regime), and HTF Technicals.
    """
    def __init__(self, mt5_handler):
        self.mt5 = mt5_handler
        self.macro = MacroEngine()
        
    def get_score(self, symbol, df, df_dxy, df_us100, df_xau, df_btc=None):
        score = 0
        details = {}
        
        # 1. HTF Trend Alignment (+2.5)
        trend = detect_htf_trend(df)
        trend_score = 2.5 if trend in ["Bullish", "Bearish"] else 0
        score += trend_score
        details['HTF Trend'] = f"{trend} ({trend_score}/2.5)"
        
        # 2. Institutional OB (+2.5)
        obs, _ = identify_order_blocks(df)
        ob_score = 2.5 if obs else 0
        score += ob_score
        details['OB HTF'] = f"OBs: {len(obs)} ({ob_score}/2.5)"
        
        # 3. FVG Present (+1.5)
        fvgs = identify_fvg(df)
        fvg_score = 1.5 if fvgs else 0
        score += fvg_score
        details['FVG'] = f"FVGs: {len(fvgs)} ({fvg_score}/1.5)"
        
        # 4. Sweep Confirmed (+1.5)
        liq = identify_liquidity_zones(df)
        last_low, last_high = df['low'].iloc[-1], df['high'].iloc[-1]
        sweep = any(last_low < s['price'] for s in liq['SSL']) or any(last_high > b['price'] for b in liq['BSL'])
        liq_score = 1.5 if sweep else 0
        score += liq_score
        details['Liquidity Sweep'] = f"{sweep} ({liq_score}/1.5)"
        
        # 5. OTE Fibonacci (+1)
        high, low = df['high'].iloc[-50:].max(), df['low'].iloc[-50:].min()
        price = df['close'].iloc[-1]
        is_ote = (price < (high + low)/2) if trend == "Bullish" else (price > (high + low)/2)
        ote_score = 1 if is_ote else 0
        score += ote_score
        details['Fibonacci OTE'] = f"{is_ote} ({ote_score}/1)"

        # 6. Session Active (+1)
        # Check session based on symbol and current time
        is_session = self._check_session(symbol, df.index[-1])
        session_score = 1 if is_session else 0
        score += session_score
        details['Session'] = f"{'Active' if is_session else 'Inactive'} ({session_score}/1)"
        
        # 7. News Impact (-3)
        news_impact = self.macro.check_news_impact(symbol)
        if news_impact:
            score -= 3
            details['News Impact'] = "High Impact News Imminent (-3)"

        return {
            "total_score": round(max(0, score), 1),
            "grade": "S+" if score >= 9 else "A" if score >= 8 else "B" if score >= 7 else "C",
            "details": details,
            "regime": MarketRegime(df_dxy, df_us100, df_xau, df_btc).detect_regime()
        }

    def _check_session(self, symbol, current_time):
        """
        Validates if the symbol is in its preferred trading session.
        """
        hour = current_time.hour
        if "XAU" in symbol or "DXY" in symbol:
            return 8 <= hour <= 21 # London + NY
        elif "BTC" in symbol:
            return True # 24/7
        elif "US100" in symbol or "NAS100" in symbol:
            return 13 <= hour <= 20 # NY Focus
        return 8 <= hour <= 21 # Default
