# utils/indicators.py

import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, period=20):
    return series.ewm(span=period, adjust=False).mean()

def calculate_bollinger_bands(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(window=period).mean()

def calculate_adx(df, period=14):
    # Plus/Minus Directional Movement
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)
    
    atr = calculate_atr(df, period)
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    return adx

def calculate_fib_levels(high, low):
    """
    Calculates Fibonacci Retracement levels including OTE (0.618, 0.705, 0.786)
    """
    diff = high - low
    levels = {
        '0': high,
        '0.236': high - 0.236 * diff,
        '0.382': high - 0.382 * diff,
        '0.5': high - 0.5 * diff,  # Equilibrium
        '0.618': high - 0.618 * diff,
        '0.705': high - 0.705 * diff,
        '0.786': high - 0.786 * diff,
        '1': low
    }
    return levels

def identify_fvg(df):
    """
    Identifies Fair Value Gaps (FVG) and returns detailed candle data for scoring
    """
    fvgs = []
    for i in range(2, len(df) - 1):
        # Bullish FVG (Gap between Candle 1 High and Candle 3 Low)
        # Candle 1: i-1, Candle 2: i, Candle 3: i+1
        if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
            # Check for displacement (Strong Candle 2)
            body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
            avg_body = abs(df['close'] - df['open']).rolling(50).mean().iloc[i]
            displacement = body_size > avg_body * 1.5
            
            fvg_data = {
                'type': 'Bullish FVG',
                'top': df['low'].iloc[i+1],
                'bottom': df['high'].iloc[i-1],
                'mid': (df['low'].iloc[i+1] + df['high'].iloc[i-1]) / 2,
                'index': i,
                'displacement': displacement,
                'candle_size': body_size
            }
            fvgs.append(fvg_data)
        
        # Bearish FVG
        elif df['high'].iloc[i+1] < df['low'].iloc[i-1]:
            body_size = abs(df['close'].iloc[i] - df['open'].iloc[i])
            avg_body = abs(df['close'] - df['open']).rolling(50).mean().iloc[i]
            displacement = body_size > avg_body * 1.5
            
            fvg_data = {
                'type': 'Bearish FVG',
                'top': df['low'].iloc[i-1],
                'bottom': df['high'].iloc[i+1],
                'mid': (df['low'].iloc[i-1] + df['high'].iloc[i+1]) / 2,
                'index': i,
                'displacement': displacement,
                'candle_size': body_size
            }
            fvgs.append(fvg_data)
    return fvgs

def detect_htf_trend(df_htf):
    """Returns 'Bullish', 'Bearish' or 'Neutral' based on HH/HL or LH/LL"""
    if len(df_htf) < 50: return 'Neutral'
    
    last_lows = df_htf['low'].rolling(20).min()
    last_highs = df_htf['high'].rolling(20).max()
    
    bullish = df_htf['high'].iloc[-1] > last_highs.iloc[-20] and df_htf['low'].iloc[-1] > last_lows.iloc[-20]
    bearish = df_htf['high'].iloc[-1] < last_highs.iloc[-20] and df_htf['low'].iloc[-1] < last_lows.iloc[-20]
    
    if bullish: return 'Bullish'
    if bearish: return 'Bearish'
    return 'Neutral'

def get_psychological_levels(price, interval=50):
    """Returns nearest psychological levels (round numbers)"""
    base = round(price / interval) * interval
    return [base - interval, base, base + interval]

def identify_order_blocks(df):
    """
    Identifies Order Blocks (OB) and Breaker Blocks
    """
    obs = []
    breakers = []
    for i in range(2, len(df) - 1):
        # Bullish OB: Last down candle before strong move up
        if df['close'].iloc[i-1] < df['open'].iloc[i-1] and df['close'].iloc[i] > df['high'].iloc[i-1]:
            obs.append({
                'type': 'Bullish OB',
                'high': df['high'].iloc[i-1],
                'low': df['low'].iloc[i-1],
                'index': i-1
            })
        
        # Bearish OB: Last up candle before strong move down
        elif df['close'].iloc[i-1] > df['open'].iloc[i-1] and df['close'].iloc[i] < df['low'].iloc[i-1]:
            obs.append({
                'type': 'Bearish OB',
                'high': df['high'].iloc[i-1],
                'low': df['low'].iloc[i-1],
                'index': i-1
            })

    # Identify Breakers (Failed OBs)
    current_price = df['close'].iloc[-1]
    for ob in obs:
        if ob['type'] == 'Bullish OB' and current_price < ob['low']:
            breakers.append({
                'type': 'Bearish Breaker',
                'high': ob['high'],
                'low': ob['low'],
                'index': ob['index']
            })
        elif ob['type'] == 'Bearish OB' and current_price > ob['high']:
            breakers.append({
                'type': 'Bullish Breaker',
                'high': ob['high'],
                'low': ob['low'],
                'index': ob['index']
            })
            
    return obs[-3:], breakers[-3:]

def get_htf_levels(df_daily, df_weekly):
    """
    Returns Weekly and Daily Highs/Lows as magnetic liquidity levels
    """
    levels = {
        'Weekly_High': df_weekly['high'].iloc[-2],
        'Weekly_Low': df_weekly['low'].iloc[-2],
        'Daily_High': df_daily['high'].iloc[-2],
        'Daily_Low': df_daily['low'].iloc[-2],
        'Old_Highs': df_daily['high'].tail(10).tolist(), # Simplified Old Highs
        'Old_Lows': df_daily['low'].tail(10).tolist()
    }
    return levels

def identify_liquidity_zones(df, tolerance=0.0005):
    """
    Identifies BSL (Buy-Side), SSL (Sell-Side), EH (Equal Highs), EL (Equal Lows)
    and Major Swing Points (Daily/Weekly)
    """
    highs = df['high'].values
    lows = df['low'].values
    
    swing_highs = []
    swing_lows = []
    
    # Precise Swing Point Detection (Fractal-like)
    for i in range(5, len(df) - 5):
        if all(highs[i] > highs[i-j] for j in range(1, 6)) and all(highs[i] > highs[i+j] for j in range(1, 6)):
            swing_highs.append({'price': highs[i], 'index': i, 'type': 'BSL'})
        if all(lows[i] < lows[i-j] for j in range(1, 6)) and all(lows[i] < lows[i+j] for j in range(1, 6)):
            swing_lows.append({'price': lows[i], 'index': i, 'type': 'SSL'})
            
    # Equal Highs / Lows (EH / EL) - Engineering Detection
    eh = []
    el = []
    for i in range(len(swing_highs)):
        for j in range(i + 1, len(swing_highs)):
            diff = abs(swing_highs[i]['price'] - swing_highs[j]['price']) / swing_highs[i]['price']
            if diff < tolerance:
                eh.append({'price': max(swing_highs[i]['price'], swing_highs[j]['price']), 'indices': [swing_highs[i]['index'], swing_highs[j]['index']]})

    for i in range(len(swing_lows)):
        for j in range(i + 1, len(swing_lows)):
            diff = abs(swing_lows[i]['price'] - swing_lows[j]['price']) / swing_lows[i]['price']
            if diff < tolerance:
                el.append({'price': min(swing_lows[i]['price'], swing_lows[j]['price']), 'indices': [swing_lows[i]['index'], swing_lows[j]['index']]})

    return {
        'BSL': swing_highs[-10:],
        'SSL': swing_lows[-10:],
        'EH': eh[-5:],
        'EL': el[-5:]
    }

def calculate_session_levels(df):
    """
    Calculates Asian High/Low, London Open, NY Open
    Assumes df has a DatetimeIndex
    """
    if df.index.empty: return {}
    
    # Ensure DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except:
            return {}

    today = df.index[-1].date()
    today_df = df[df.index.date == today]
    
    # Session UTC
    asian = today_df.between_time('00:00', '08:00')
    london_open = today_df.between_time('08:00', '09:00')
    ny_open = today_df.between_time('13:00', '14:00')
    
    return {
        'Asian_High': asian['high'].max() if not asian.empty else None,
        'Asian_Low': asian['low'].min() if not asian.empty else None,
        'London_Open_High': london_open['high'].max() if not london_open.empty else None,
        'London_Open_Low': london_open['low'].min() if not london_open.empty else None,
        'NY_Open_High': ny_open['high'].max() if not ny_open.empty else None,
        'NY_Open_Low': ny_open['low'].min() if not ny_open.empty else None,
    }

def identify_ote_zone(high, low, trend='bullish'):
    """
    Determines the Optimal Trade Entry (OTE) Zone
    """
    diff = high - low
    if trend == 'bullish':
        # OTE is 61.8% to 78.6% retracement
        return {
            'entry_start': high - 0.618 * diff,
            'ideal_entry': high - 0.705 * diff,
            'entry_end': high - 0.786 * diff
        }
    else:
        return {
            'entry_start': low + 0.618 * diff,
            'ideal_entry': low + 0.705 * diff,
            'entry_end': low + 0.786 * diff
        }

def get_market_zone(price, high, low):
    """
    Determines if the current price is in the Premium or Discount zone
    """
    eq = (high + low) / 2
    if price > eq:
        return "Premium Zone"
    elif price < eq:
        return "Discount Zone"
    else:
        return "Equilibrium"
