# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
import os
from datetime import datetime
from analyzer import TradingAI, MarketStructure, SignalAnalyzer, PredictiveModels, MarketRegime, AdvancedRisk, SentimentNLP
from utils.indicators import (
    calculate_fib_levels, 
    identify_fvg, 
    identify_order_blocks, 
    identify_liquidity_zones, 
    calculate_session_levels,
    identify_ote_zone
)
from utils.analytics import MarketAnalytics
from utils.helpers import save_plot_as_image, format_currency, format_percentage
from database.db_handler import DBHandler

# --- INITIALIZE DATABASE ---
db = DBHandler()
from utils.macro_data import MacroEngine
from utils.reporting import DailyReport
from config import CONFIG

# --- PAGE CONFIG ---
st.set_page_config(page_title="Aladdin Quantum Pro v4", layout="wide")

# --- LOAD DATA ---
@st.cache_data
def get_market_data(symbol, timeframe):
    ticker_map = {"XAUUSD": "GC=F", "BTCUSD": "BTC-USD", "DXY": "DX-Y.NYB", "NAS100": "NQ=F"}
    
    tf_map = {
        "H1": "1h", "H2": "1h", "H3": "1h", "H4": "1h", "H5": "1h", "H6": "1h",
        "JOUR (Daily)": "1d", "SEMAINE (Weekly)": "1wk", "MOIS (Monthly)": "1mo", "ANNÉE (Yearly)": "1mo"
    }
    
    period_map = {
        "H1": "2y", "H2": "2y", "H3": "2y", "H4": "2y", "H5": "2y", "H6": "2y",
        "JOUR (Daily)": "10y", "SEMAINE (Weekly)": "max", "MOIS (Monthly)": "max", "ANNÉE (Yearly)": "max"
    }
    
    interval = tf_map.get(timeframe, "1d")
    period = period_map.get(timeframe, "10y")
    
    df = yf.download(ticker_map[symbol], period=period, interval=interval)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    
    # Resample for H2-H6 if needed (Yahoo Finance doesn't provide them directly)
    if timeframe in ["H2", "H3", "H4", "H5", "H6"]:
        hours = int(timeframe[1])
        df = df.resample(f"{hours}h").agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
    
    # VWAP Calculation
    df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
    return df

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧙‍♂️ Aladdin Quantum v4")
    selected_asset = st.selectbox("🎯 Actif Cible", CONFIG["symbols"])
    
    tf_options = ["H1", "H2", "H3", "H4", "H5", "H6", "JOUR (Daily)", "SEMAINE (Weekly)", "MOIS (Monthly)", "ANNÉE (Yearly)"]
    selected_tf = st.selectbox("⏳ Unité de Temps", tf_options, index=6)
    
    balance = st.number_input("💰 Solde du Compte ($)", value=10000)
    
    # Load Data
    with st.spinner("Chargement des données..."):
        df = get_market_data(selected_asset, selected_tf)
    
    # 1. Regime Detection
    mr = MarketRegime(df)
    regime = mr.detect_regime()
    # Simple French Translation for regimes
    regime_fr = {
        "Trending": "Tendance",
        "Ranging": "Range (Latéral)",
        "Volatile": "Volatil"
    }.get(regime, regime)
    st.success(f"État du Marché : {regime_fr}")
    
    # 2. Daily Report Generation
    if st.button("📄 Générer le Rapport PDF Quotidien", use_container_width=True):
        pm = PredictiveModels(df)
        preds = pm.get_consensus_prediction()
        ar = AdvancedRisk(df, balance)
        risk_stats = {"var": balance*0.02, "es": ar.expected_shortfall(), "prob_crash": ar.probability_of_crash()}
        
        pdf = DailyReport()
        pdf_file = pdf.generate(selected_asset, regime, risk_stats, preds)
        with open(pdf_file, "rb") as f:
            st.download_button("Télécharger le Rapport", f, file_name=pdf_file)

# --- MAIN DASHBOARD ---
t1, t2, t3, t4, t5 = st.tabs(["⚡ Moteur d'Intelligence", "🛡️ Contrôle des Risques", "🧠 Sentiment NLP", "📓 Journal de Trading", "📊 Analyse d'Exécution"])

with t1:
    st.header(f"Intelligence Quantique : {selected_asset} ({selected_tf})")
    
    # --- SMC ANALYSIS ---
    fvgs = identify_fvg(df)
    obs, breakers = identify_order_blocks(df)
    liq = identify_liquidity_zones(df)
    sessions = calculate_session_levels(df)
    
    # Layout for metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    ms = MarketStructure(df)
    
    # Simple French for structure
    structure_raw = ms.detect_bos_choch()
    structure_fr = structure_raw.replace("BOS", "Cassure de Structure (BOS)").replace("CHoCH", "Changement de Caractère (CHoCH)")
    
    col1.metric("Structure", structure_fr)
    
    # Find active FVG
    last_fvg = fvgs[-1] if fvgs else None
    fvg_text = "Zone de Déséquilibre" if last_fvg else "Aucun"
    col2.metric("Zone de Prix (FVG)", fvg_text)
    
    # Predictive Consensus
    pm = PredictiveModels(df)
    preds = pm.get_consensus_prediction()
    col3.metric("Prédiction IA", f"${preds['consensus']}", delta=preds['trend'])
    
    # Reliability
    col4.metric("Fiabilité IA", preds['reliability'])
    
    # ML Trend
    trend_fr = preds['trend'].replace("Bullish", "Haussier").replace("Bearish", "Baissier").replace("Neutral", "Neutre")
    col5.metric("Tendance ML", trend_fr)
    
    with st.expander("🔬 Performance des Modèles (10 dernières années)"):
        st.json(preds['weights'])

    # --- CHARTING ---
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Bougies"),
                          go.Scatter(x=df.index, y=df['vwap'], line=dict(color='orange', width=1, dash='dot'), name="VWAP")])
    
    # Add FVGs to chart
    for fvg in fvgs:
        color = "rgba(0, 255, 0, 0.2)" if "Bullish" in fvg['type'] else "rgba(255, 0, 0, 0.2)"
        fig.add_shape(type="rect", x0=df.index[fvg['index']], x1=df.index[-1], y0=fvg['bottom'], y1=fvg['top'], 
                      fillcolor=color, line=dict(width=0), name="Déséquilibre (FVG)")

    # Add Order Blocks
    for ob in obs:
        color = "rgba(0, 150, 255, 0.3)" if "Bullish" in ob['type'] else "rgba(255, 100, 0, 0.3)"
        fig.add_shape(type="rect", x0=df.index[ob['index']], x1=df.index[-1], y0=ob['low'], y1=ob['high'], 
                      fillcolor=color, line=dict(width=1, color="blue"), name="Zone d'Ordres (OB)")

    # Add Session Levels
    for level_name, price in sessions.items():
        if price:
            fig.add_hline(y=price, line_dash="dash", line_color="gray", annotation_text=level_name)

    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- AI VISION ANALYSIS ---
    if st.button("👁️ Analyser le Graphique (Vision IA SMC)", use_container_width=True):
        with st.spinner("Analyse du graphique avec Llama-3.2-Vision..."):
            ai = TradingAI()
            # Save chart temporarily
            chart_path = save_plot_as_image(fig)
            if chart_path:
                technical_data = {
                    "regime": regime,
                    "structure": ms.detect_bos_choch(),
                    "fvg": fvg_text,
                    "prediction": preds['consensus'],
                    "trend": preds['trend']
                }
                analysis = ai.analyze_chart(chart_path, technical_data)
                
                if "error" in analysis:
                    st.error(f"Erreur IA : {analysis['error']}")
                else:
                    st.markdown("### 🧙‍♂️ Analyse Vision d'Aladdin")
                    st.write(analysis.get("response", "Aucune réponse de l'IA"))
                    # Clean up
                    if os.path.exists(chart_path):
                        os.remove(chart_path)
            else:
                st.error("Échec de la capture du graphique. Vérifiez que 'kaleido' est correctement installé.")

    # --- SMC DETAILS ---
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        with st.expander("📊 Structure de Marché & Liquidité"):
            # High Probability Patterns
            setups = ms.identify_high_prob_setups(fvgs, obs)
            if setups:
                st.subheader("🔥 Patterns Haute Probabilité")
                for s in setups:
                    st.success(f"**{s['pattern']}** ({s['bias']}) en zone {s['zone']}")
            
            st.write("**Points Swing Récents :**")
            for s in liq['Structure']:
                st.write(f"- {s['type']} à {s['price']:.2f}")
            
            if liq['EH']: st.warning(f"⚠️ Hauts Égaux (Equal Highs) détectés vers {liq['EH'][0]['price']:.2f}")
            if liq['EL']: st.warning(f"⚠️ Bas Égaux (Equal Lows) détectés vers {liq['EL'][0]['price']:.2f}")

    with exp_col2:
        with st.expander("🕒 Sessions & Niveaux Quotidiens"):
            st.json(sessions)

with t2:
    st.header("Gestion Avancée des Risques & Stress Test")
    ar = AdvancedRisk(df, balance)
    
    col_r1, col_r2, col_r3 = st.columns(3)
    es = ar.expected_shortfall()
    crash_p = ar.probability_of_crash()
    
    col_r1.metric("Expected Shortfall (ES)", f"${es:.2f}")
    col_r2.metric("Probabilité de Crash (>10%)", f"{crash_p*100:.2f}%")
    
    # Monte Carlo Stress Test
    mc = ar.monte_carlo_simulation()
    col_r3.metric("Pire Cas MC (30j)", f"${mc['worst_case']:.2f}")

    st.subheader("Distribution des Chemins Monte Carlo (30 Jours)")
    st.progress(crash_p, text=f"Facteur de risque de crash : {crash_p*100:.1f}%")

with t3:
    st.header("Analyse de Sentiment (NLP)")
    nlp = SentimentNLP()
    
    news_input = st.text_area("Coller les titres de presse (un par ligne)", "Le marché bondit suite aux annonces de la FED\nInquiétudes sur l'inflation dans le secteur tech\nLa demande d'or atteint un niveau record")
    
    col_s1, col_s2 = st.columns(2)
    
    if col_s1.button("Analyse Rapide", use_container_width=True):
        headlines = news_input.split('\n')
        sentiment_res = nlp.analyze_news_list(headlines)
        
        st.write(f"### Biais de Sentiment Global : **{sentiment_res['bias']}**")
        st.metric("Score de Sentiment", sentiment_res['avg_score'])

    if col_s2.button("Analyse IA Approfondie", use_container_width=True):
        headlines = [h for h in news_input.split('\n') if h.strip()]
        with st.spinner("L'IA analyse l'actualité..."):
            llm_res = nlp.analyze_with_llm(headlines)
            if llm_res:
                st.write(f"### Biais IA Approfondi : **{llm_res['bias']}**")
                st.metric("Score de Sentiment IA", llm_res['score'])
                st.info(f"**Résumé IA :** {llm_res['summary']}")
            else:
                st.error("L'analyse LLM a échoué. Assurez-vous qu'Ollama est lancé.")

with t4:
    st.header("Journal de Trading Minimaliste & Performance")
    
    # Calculate Winrate
    wr = db.calculate_winrate()
    all_trades = db.get_all_trades()
    
    col_w1, col_w2, col_w3 = st.columns(3)
    col_w1.metric("Total Trades", len(all_trades))
    col_w2.metric("Taux de Réussite", format_percentage(wr))
    
    total_pl = sum([t.profit_loss for t in all_trades])
    col_w3.metric("P/L Total", format_currency(total_pl))
    
    st.divider()
    
    with st.expander("➕ Ajouter une Entrée"):
        j_asset = st.selectbox("Actif", CONFIG["symbols"], key="j_asset_db")
        j_bias = st.radio("Côté", ["Achat", "Vente"], horizontal=True, key="j_side_db")
        j_entry = st.number_input("Prix d'Entrée", key="j_entry_db")
        j_notes = st.text_area("Notes", key="j_notes_db")
        
        # Capture current chart as image
        if st.button("Enregistrer le Trade"):
            db.add_trade(j_asset, j_bias, j_entry, notes=j_notes)
            st.success("Trade enregistré !")
            st.rerun()
    
    # Display History
    for entry in reversed(all_trades):
        status_color = "#00ff88" if entry.status == 'Gagnant' else "#ff4b4b" if entry.status == 'Perdant' else "#888888"
        st.markdown(f"""
            <div style="background: #1a1a1a; padding: 15px; border-left: 5px solid {status_color}; margin-bottom: 10px;">
                <b>{entry.timestamp.strftime('%Y-%m-%d %H:%M')} - {entry.symbol} ({entry.side})</b><br>
                Statut : {entry.status} | Entrée : {entry.entry_price} | P/L : {format_currency(entry.profit_loss)}<br>
                <i>{entry.notes}</i>
            </div>
        """, unsafe_allow_html=True)
        if entry.image_path and os.path.exists(entry.image_path):
            st.image(entry.image_path)


with t5:
    st.header("Analyse d'Exécution")
    st.write("Détection de Liquidité & Benchmarks Algorithmiques")
    
    # TWAP (Simple Average Price over window)
    window = st.slider("Fenêtre TWAP (Périodes)", 5, 50, 20)
    df['twap'] = df['close'].rolling(window=window).mean()
    
    col_e1, col_e2 = st.columns(2)
    col_e1.metric("VWAP Actuel", round(df['vwap'].iloc[-1], 2))
    col_e2.metric(f"TWAP Actuel ({window})", round(df['twap'].iloc[-1], 2))

    st.info("💡 Conseil Pro : Quand Prix > VWAP & Le Marché est Bullish, évitez les entrées FOMO.")

st.divider()
st.caption("Aladdin Quantum v4.0 - Système de Décision Ultra Avancé")
