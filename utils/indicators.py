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
    Identifies Fair Value Gaps (FVG) and Nested FVGs (FVG in FVG)
    """
    fvgs = []
    for i in range(1, len(df) - 1):
        # Bullish FVG
        if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
            fvg_data = {
                'type': 'Bullish FVG',
                'top': df['low'].iloc[i+1],
                'bottom': df['high'].iloc[i-1],
                'index': i,
                'nested': False
            }
            # Check for Nested FVG (FVG in FVG)
            if i > 2:
                # If current FVG is within the previous FVG range
                prev_fvg = next((f for f in reversed(fvgs) if f['type'] == 'Bullish FVG'), None)
                if prev_fvg and fvg_data['bottom'] >= prev_fvg['bottom'] and fvg_data['top'] <= prev_fvg['top']:
                    fvg_data['nested'] = True
            fvgs.append(fvg_data)
        
        # Bearish FVG
        elif df['high'].iloc[i+1] < df['low'].iloc[i-1]:
            fvg_data = {
                'type': 'Bearish FVG',
                'top': df['low'].iloc[i-1],
                'bottom': df['high'].iloc[i+1],
                'index': i,
                'nested': False
            }
            # Check for Nested FVG
            if i > 2:
                prev_fvg = next((f for f in reversed(fvgs) if f['type'] == 'Bearish FVG'), None)
                if prev_fvg and fvg_data['top'] <= prev_fvg['top'] and fvg_data['bottom'] >= prev_fvg['bottom']:
                    fvg_data['nested'] = True
            fvgs.append(fvg_data)
    return fvgs[-5:]

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

def identify_liquidity_zones(df, tolerance=0.001):
    """
    Identifies BSL, SSL, EH (Equal Highs), EL (Equal Lows) and Swing Points (HH, HL, LH, LL)
    """
    bsl = df['high'].rolling(window=20).max().iloc[-1]
    ssl = df['low'].rolling(window=20).min().iloc[-1]
    
    # Simple Swing Point Detection (3-candle pattern)
    highs = df['high'].values
    lows = df['low'].values
    structure = []
    
    for i in range(2, len(df) - 2):
        # Swing High
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            label = "H"
            if len(structure) > 0:
                prev_high = next((s for s in reversed(structure) if "H" in s['type']), None)
                if prev_high:
                    label = "HH" if highs[i] > prev_high['price'] else "LH"
            structure.append({'type': label, 'price': highs[i], 'index': i})
            
        # Swing Low
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            label = "L"
            if len(structure) > 0:
                prev_low = next((s for s in reversed(structure) if "L" in s['type']), None)
                if prev_low:
                    label = "HL" if lows[i] > prev_low['price'] else "LL"
            structure.append({'type': label, 'price': lows[i], 'index': i})

    # Equal Highs / Lows (EH / EL)
    eq_highs = []
    eq_lows = []
    last_highs = [s for s in structure if "H" in s['type']][-5:]
    last_lows = [s for s in structure if "L" in s['type']][-5:]
    
    for i in range(len(last_highs)):
        for j in range(i + 1, len(last_highs)):
            if abs(last_highs[i]['price'] - last_highs[j]['price']) / last_highs[i]['price'] < tolerance:
                eq_highs.append({'price': last_highs[i]['price'], 'indices': [last_highs[i]['index'], last_highs[j]['index']]})

    for i in range(len(last_lows)):
        for j in range(i + 1, len(last_lows)):
            if abs(last_lows[i]['price'] - last_lows[j]['price']) / last_lows[i]['price'] < tolerance:
                eq_lows.append({'price': last_lows[i]['price'], 'indices': [last_lows[i]['index'], last_lows[j]['index']]})

    return {
        'BSL': bsl, 
        'SSL': ssl, 
        'Structure': structure[-5:], 
        'EH': eq_highs[-2:] if eq_highs else [], 
        'EL': eq_lows[-2:] if eq_lows else []
    }

def calculate_session_levels(df):
    """
    Calculates Highs and Lows for main sessions (Asian, London, NY) and PDH/PDL
    Assumes df has a DatetimeIndex
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except:
            return {}

    # Current Day Levels
    today = df.index[-1].date()
    today_df = df[df.index.date == today]
    
    # Previous Day Levels (PDH / PDL)
    yesterday_df = df[df.index.date < today]
    if not yesterday_df.empty:
        last_day = yesterday_df.index[-1].date()
        pd_df = yesterday_df[yesterday_df.index.date == last_day]
        pdh = pd_df['high'].max()
        pdl = pd_df['low'].min()
    else:
        pdh = pdl = None

    # Session Hours (UTC)
    sessions = {
        'Asian': ('00:00', '09:00'),
        'London': ('08:00', '17:00'),
        'New York': ('13:00', '22:00')
    }
    
    session_levels = {
        'PDH': pdh,
        'PDL': pdl
    }
    
    for session, (start, end) in sessions.items():
        # Filter by time
        session_df = today_df.between_time(start, end)
        if not session_df.empty:
            session_levels[f'{session}_High'] = session_df['high'].max()
            session_levels[f'{session}_Low'] = session_df['low'].min()
        else:
            session_levels[f'{session}_High'] = None
            session_levels[f'{session}_Low'] = None
            
    return session_levels

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
