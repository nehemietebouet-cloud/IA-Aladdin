# app.py

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from analyzer.mt5_handler import MT5Handler
from analyzer.sniper_engine import SniperEngine
from analyzer.ob_strategy import OBStrategy
from analyzer.liquidity_analyzer import LiquidityAnalyzer
from analyzer.institutional_score import InstitutionalScore
from utils.indicators import identify_fvg, identify_liquidity_zones
from config import CONFIG
import MetaTrader5 as mt5

# --- PAGE CONFIG ---
st.set_page_config(page_title="Aladdin Sniper Bot v3", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for Dark Dashboard
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2130; padding: 10px; border-radius: 10px; border: 1px solid #3e4451; }
    .stTabs [data-baseweb="tab-list"] { background-color: #1e2130; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { color: #8e94a1; }
    .stTabs [aria-selected="true"] { color: #00d4ff; border-bottom-color: #00d4ff; }
    </style>
""", unsafe_allow_html=True)

# --- AUTO-CONNECT MT5 ---
MT5_LOGIN = 5047361383
MT5_PWD = "Ne@a2vKg"
MT5_SERVER = "MetaQuotes-Demo"

@st.cache_resource
def get_mt5_connection():
    handler = MT5Handler(login=MT5_LOGIN, password=MT5_PWD, server=MT5_SERVER)
    if handler.connect(): return handler
    return None

handler = get_mt5_connection()
if not handler:
    st.error("❌ Échec de la connexion à MT5.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎯 Aladdin Sniper Bot")
    symbol = st.selectbox("🎯 Actif", CONFIG["symbols"], index=0)
    timeframe_str = st.selectbox("⏳ Timeframe", ["M1", "M5", "M15", "H1", "H4", "D1"], index=1)
    
    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
    }
    tf = tf_map[timeframe_str]

# --- LOAD HTF & DXY DATA ---
df = handler.get_market_data(symbol, tf, n=500)
df_daily = handler.get_market_data(symbol, mt5.TIMEFRAME_D1, n=50)
df_weekly = handler.get_market_data(symbol, mt5.TIMEFRAME_W1, n=20)

# Fetch DXY & US100 for Intermarket Analysis
dxy_symbol = next((s for s in CONFIG["intermarket"]["DXY_symbols"] if handler.connect() and mt5.symbol_info(s)), "DXY")
us100_symbol = "US100" if mt5.symbol_info("US100") else "NAS100"

df_dxy = handler.get_market_data(dxy_symbol, tf, n=100)
df_us100 = handler.get_market_data(us100_symbol, tf, n=100)
df_btc = handler.get_market_data("BTCUSD", tf, n=100)
df_xau = handler.get_market_data("XAUUSD", tf, n=100)

if df is None or df_daily is None or df_weekly is None:
    st.warning("⚠️ HTF Data indisponibles")
    st.stop()

# --- UNIFIED SNIPER ENGINE ---
engine = SniperEngine(df, df_daily, df_weekly, symbol=symbol, df_dxy=df_dxy, df_us100=df_us100)
signal = engine.analyze()

# --- DASHBOARD ---
st.title(f"📊 Aladdin Sniper Pro - {symbol} ({timeframe_str})")

# Auto-refresh every 10 seconds for autonomous scanning
st_autorefresh(interval=10000, key="autoscanner")

t1, t2, t3, t4 = st.tabs(["⚔️ SNIPER EXECUTION", "🧠 Institutional", "📈 Performance", "📓 Positions"])

with t1:
    col1, col2, col3, col4 = st.columns(4)
    
    if signal:
        col1.metric("Sniper Status", signal['type'], delta=f"Score: {signal['score']}/10")
        col2.metric("RR Ratio", f"1:{signal['rr']}")
        col3.metric("Entry", f"{signal['entry']:.5f}")
        col4.metric("Target (Draw)", f"{signal['tp']:.5f}")
        
        st.success(f"🎯 **Surgical Setup :** Score {signal['score']}/10 | RR 1:{signal['rr']} | Lot: {signal['lot']}")
        
        # --- AUTONOMOUS EXECUTION ---
        # Prevent multiple entries for the same signal timestamp
        last_signal_time = df.index[-1].strftime("%Y-%m-%d %H:%M:%S")
        if "last_executed_signal" not in st.session_state:
            st.session_state.last_executed_signal = None

        if st.session_state.last_executed_signal != last_signal_time:
            st.warning(f"🚀 AUTONOMOUS DEPLOYMENT: {signal['type']} - {signal['lot']} Lot")
            res = handler.place_order(symbol, mt5.ORDER_TYPE_BUY if signal['action'] == 'BUY' else mt5.ORDER_TYPE_SELL, signal['lot'], sl=signal['sl'], tp=signal['tp'])
            
            if res and res.retcode == 10009: 
                st.success(f"✅ Order {res.order} Executed Autonomously!")
                st.session_state.last_executed_signal = last_signal_time
                from database.db_handler import DBHandler
                db = DBHandler()
                db.add_trade(symbol, signal['action'], signal['entry'], lot_size=signal['lot'], sl=signal['sl'], tp=signal['tp'], ticket_id=str(res.order), rr_ratio=signal['rr'])
            else: 
                st.error(f"❌ Execution Failed: {res.comment if res else 'Unknown'}")
    else:
        col1.metric("Signal", "SCANNING", delta="No Sniper Setup")
        st.info("💡 En attente de confluence : Structure + Liquidité + Engine Fuel...")

    # Chart with all institutional levels
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Prix")])
    
    # HTF Levels
    from utils.indicators import get_htf_levels, get_psychological_levels
    htf = get_htf_levels(df_daily, df_weekly)
    psy = get_psychological_levels(df['close'].iloc[-1], interval=50)
    
    # Plot Psychological Levels
    for level in psy:
        fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=level, y1=level, line=dict(color="#4a4e69", width=1, dash="dot"), name=f"Psy {level}")
        
    fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=htf['Weekly_High'], y1=htf['Weekly_High'], line=dict(color="orange", width=2, dash="dot"), name="Weekly High")
    fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=htf['Weekly_Low'], y1=htf['Weekly_Low'], line=dict(color="orange", width=2, dash="dot"), name="Weekly Low")
    fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=htf['Daily_High'], y1=htf['Daily_High'], line=dict(color="red", width=1.5, dash="dash"), name="Daily High")
    fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=htf['Daily_Low'], y1=htf['Daily_Low'], line=dict(color="green", width=1.5, dash="dash"), name="Daily Low")

    # Liquidity
    liq = identify_liquidity_zones(df)
    for eh in liq['EH']: fig.add_annotation(x=df.index[eh['indices'][0]], y=eh['price'], text="EH", showarrow=False, font=dict(color="red"))
    for el in liq['EL']: fig.add_annotation(x=df.index[el['indices'][0]], y=el['price'], text="EL", showarrow=False, font=dict(color="green"))

    # OBs/FVGs
    from analyzer.ob_strategy import OBStrategy
    obs = OBStrategy(df).get_order_blocks()
    for ob in obs:
        color = "rgba(0, 255, 127, 0.1)" if ob['type'] == 'Bullish OB' else "rgba(255, 69, 0, 0.1)"
        fig.add_shape(type="rect", x0=df.index[ob['index']], x1=df.index[-1], y0=ob['low'], y1=ob['high'], fillcolor=color, line_width=0)

    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with t2:
    st.subheader("🏦 Institutional Intelligence Deck")
    inst_engine = InstitutionalScore(handler)
    inst_data = inst_engine.get_score(symbol, df, df_dxy, df_us100, df_xau, df_btc)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    c1.metric("Institutional Grade", inst_data['grade'], delta=f"Score: {inst_data['total_score']}/100")
    c2.info(f"🌐 **Market Regime :** {inst_data['regime']}")
    
    st.markdown("---")
    cols = st.columns(3)
    for i, (key, val) in enumerate(inst_data['details'].items()):
        cols[i % 3].write(f"**{key}** : {val}")

    st.markdown("---")
    st.write("### 🧠 Intermarket Correlations")
    cc1, cc2, cc3 = st.columns(3)
    
    # Calculate simple correlations
    if df_dxy is not None:
        dxy_corr = df['close'].corr(df_dxy['close'])
        cc1.metric("DXY Correlation", f"{dxy_corr:.2f}", delta="Inverse" if dxy_corr < 0 else "Direct")
        
    if df_us100 is not None:
        nas_corr = df['close'].corr(df_us100['close'])
        cc2.metric("NAS100 Correlation", f"{nas_corr:.2f}", delta="Growth Driver" if nas_corr > 0.7 else "")

    if df_btc is not None:
        btc_corr = df['close'].corr(df_btc['close'])
        cc3.metric("BTC Correlation", f"{btc_corr:.2f}")

with t3:
    stats = handler.get_performance_stats(days=30)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Winrate Sniper", f"{stats['winrate']:.1f}%")
    c2.metric("Profit Factor", f"{stats['profit_factor']:.2f}")
    c3.metric("Profit ($)", f"${stats['total_profit']:.2f}")
    c4.metric("Trades", stats['trades'])

with t4:
    positions = handler.get_open_positions()
    if positions:
        st.subheader("🛡️ ACTIVE SHIELD : Trade Management")
        if st.button("🔄 AUTO-PROTECT ALL (Break-Even & Trail)"):
            for pos in positions:
                # Logic: If profit > 30 points, move SL to entry
                current_profit_points = (pos.price_current - pos.price_open) / mt5.symbol_info(pos.symbol).point
                if pos.type == mt5.ORDER_TYPE_SELL: current_profit_points *= -1
                
                if current_profit_points > 30:
                    res = handler.update_sl_tp(pos.ticket, pos.price_open, pos.tp)
                    if res.retcode == 10009: st.success(f"✅ Position {pos.ticket} secured at Break-Even!")
        
        pos_df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
        st.dataframe(pos_df[['ticket', 'symbol', 'volume', 'price_open', 'price_current', 'sl', 'tp', 'profit']], use_container_width=True)
    else:
        st.write("Aucune position active.")
