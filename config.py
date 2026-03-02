# config.py

CONFIG = {
    "symbols": ["XAUUSD", "BTCUSD", "DXY", "NAS100"],
    "risk_per_trade": 0.02,  # 2% Risk
    "min_rr": 2.0,           # Minimum Risk/Reward
    "timeframes": ["1m", "5m", "15m", "1h", "4h", "D1"],
    "sessions": {
        "London": {"start": "08:00", "end": "16:00", "tz": "UTC"},
        "NewYork": {"start": "13:00", "end": "21:00", "tz": "UTC"},
        "Asia": {"start": "00:00", "end": "08:00", "tz": "UTC"}
    },
    "indicators": {
        "fib_ote": [0.618, 0.705, 0.786],
        "premium_zone": 0.5,
        "discount_zone": 0.5
    },
    "ai_model": "llama3.2-vision",  # Local model (Ollama)
    "ollama_url": "http://localhost:11434/api/generate",
    "api_key": None  # No API key required for local Ollama
}
