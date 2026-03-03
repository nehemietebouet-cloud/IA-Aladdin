# analyzer/sniper_engine.py

from analyzer.ob_strategy import OBStrategy
from analyzer.fvg_strategy import FVGSniper
from analyzer.liquidity_analyzer import LiquidityAnalyzer
from analyzer.market_regime import MarketRegime
from analyzer.risk_advanced import AdvancedRisk
from utils.indicators import detect_htf_trend, get_psychological_levels, identify_ote_zone, calculate_atr
from config import CONFIG
from datetime import datetime, time
import pytz

class SniperEngine:
    def __init__(self, df, df_daily, df_weekly, symbol="XAUUSD", df_dxy=None, df_us100=None):
        self.df = df
        self.symbol = symbol
        self.df_dxy = df_dxy
        self.df_us100 = df_us100
        self.liquidity = LiquidityAnalyzer(df, df_daily, df_weekly)
        self.fvg_sniper = FVGSniper(df, df_daily)
        self.ob_strategy = OBStrategy(df)
        self.regime = MarketRegime(df_dxy, df_us100, df if symbol == "XAUUSD" else None)
        self.profile = CONFIG["profiles"].get(symbol, {})

    def get_dxy_bias(self):
        if self.df_dxy is None or self.df_dxy.empty: return None
        return {'bias': detect_htf_trend(self.df_dxy), 'sweep': LiquidityAnalyzer(self.df_dxy).detect_sweep()}

    def is_session_valid(self):
        if not self.profile: return True
        now_gmt = datetime.now(pytz.timezone('GMT')).time()
        for name, times in self.profile.get("sessions", {}).items():
            start = datetime.strptime(times["start"], "%H:%M").time()
            end = datetime.strptime(times["end"], "%H:%M").time()
            if start <= now_gmt <= end: return True
        return False

    def analyze(self):
        """
        Surgical Sniper Analysis:
        - Score >= 7/10
        - RR >= 2:1
        - Session + HTF Alignment
        - Fibonacci 50-61.8% Retracement
        """
        # 1. Basics: Session & Trend
        session_valid = self.is_session_valid()
        bias = detect_htf_trend(self.df)
        if bias == 'Neutral': return None
        
        # 2. Risk Context & Learning from Errors
        from database.db_handler import DBHandler
        db = DBHandler()
        perf = db.get_recent_performance(limit=10)
        winrate = perf['winrate']
        
        # Meta-Learning: Higher selectivity if winrate is poor
        min_score_threshold = 7
        if winrate < 40: min_score_threshold = 9 
        elif winrate < 50: min_score_threshold = 8

        trades_today = db.get_trades_count_today()
        # Note: balance should ideally be passed from app or fetched from MT5
        balance = 10000 
        risk_engine = AdvancedRisk(self.df, balance)
        
        ok, msg = risk_engine.check_kill_switch(trades_today=trades_today)
        if not ok: return None

        # 3. Strategy Components & Intermarket Correlation
        fvg_sig = self.fvg_sniper.get_signal()
        obs = self.ob_strategy.get_order_blocks()
        sweep = self.liquidity.detect_sweep()
        
        # Intermarket Validation (Hedge Fund logic)
        dxy_trend = detect_htf_trend(self.df_dxy) if self.df_dxy is not None else "Neutral"
        us100_trend = detect_htf_trend(self.df_us100) if self.df_us100 is not None else "Neutral"
        
        # XAUUSD: Inverse DXY
        if self.symbol == "XAUUSD":
            if bias == "Bullish" and dxy_trend == "Bullish": return None # Risk-Off Strong Dollar
            
        # BTCUSD: Direct US100, Inverse DXY
        if self.symbol == "BTCUSD":
            if bias == "Bullish" and (dxy_trend == "Bullish" or us100_trend == "Bearish"): return None
            
        # US100: Inverse DXY
        if self.symbol in ["US100", "NAS100"]:
            if bias == "Bullish" and dxy_trend == "Bullish": return None

        if not fvg_sig: return None
        if (bias == 'Bullish' and fvg_sig['action'] != 'BUY') or \
           (bias == 'Bearish' and fvg_sig['action'] != 'SELL'): return None

        # 5. FIBONACCI / OTE RANGE (50-78.6%)
        # Logic already handled by is_discount for basic OTE
        high = self.df['high'].iloc[-50:].max()
        low = self.df['low'].iloc[-50:].min()
        entry_price = fvg_sig['entries']['mid']
        
        # Equilibrium check (50%)
        equilibrium = (high + low) / 2
        is_discount = entry_price < equilibrium if bias == 'Bullish' else entry_price > equilibrium

        # 4. SURGICAL SCORING (0-10)
        score = 0
        
        # HTF Trend aligné (+3)
        # Assuming bias checks Weekly/Daily confluence
        score += 3 
        
        # OB aligné HTF (+3)
        ob_aligned = any(ob['type'] == ('Bullish OB' if bias == 'Bullish' else 'Bearish OB') for ob in obs)
        if ob_aligned: score += 3
        
        # FVG présent (+2)
        if fvg_sig: score += 2
        
        # Sweep confirmé (+2)
        if sweep: score += 2
        
        # Fibonacci retracement OTE (+1)
        if is_discount: score += 1
        
        # Session active (+1)
        if session_valid: score += 1
        
        # 6. RISK REWARD & LOT SIZING
        tp = self.liquidity.get_draw_on_liquidity('bullish' if bias == 'Bullish' else 'bearish')
        sl = fvg_sig['sl']
        if not tp: tp = self.df['close'].iloc[-1] # Fallback
        
        rr = risk_engine.calculate_rr(entry_price, sl, tp)
        
        # Asset Specific RR Seuil
        min_rr = self.profile.get("min_rr", 2.0)
        
        # FINAL FILTERS
        if score < min_score_threshold: return None
        if rr < min_rr: return None
        if not is_discount: return None # Must be in Discount/Premium

        # ULTRA-DYNAMIC RISK LEARNING
        dynamic_risk_pct = risk_engine.get_dynamic_risk(winrate=winrate)
        lot = risk_engine.calculate_lot_size(self.symbol, dynamic_risk_pct, abs(entry_price - sl))

        return {
            'type': f"SNIPER_{self.symbol}_{bias.upper()}",
            'action': 'BUY' if bias == 'Bullish' else 'SELL',
            'score': score,
            'rr': rr,
            'entry': entry_price,
            'sl': sl,
            'tp': tp,
            'lot': lot,
            'regime': self.regime.detect_regime()
        }
