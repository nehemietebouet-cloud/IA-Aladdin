# config.py

CONFIG = {
    "symbols": ["XAUUSD", "BTCUSD", "US100", "NAS100", "DXY", "USDX"],
    "risk_per_trade": 0.01,  # 1% for safety
    "max_spread": 0.50,      # Max spread for XAUUSD in USD
    "intermarket": {
        "DXY_symbols": ["DXY", "USDX", "US Dollar Index"],
        "correlation_map": {
            "XAUUSD": "inverse",
            "BTCUSD": "inverse",
            "US100": "inverse",
            "NAS100": "inverse",
            "EURUSD": "inverse",
            "GBPUSD": "inverse",
            "USDJPY": "direct"
        }
    },
    "profiles": {
        "XAUUSD": {
            "sessions": {
                "London": {"start": "08:00", "end": "10:00", "tz": "GMT"},
                "NewYork": {"start": "13:30", "end": "16:00", "tz": "GMT"}
            },
            "news_buffer": 60,
            "min_rr": 2.5,
            "round_numbers_interval": 50,
            "mandatory_sweep": True
        },
        "BTCUSD": {
            "sessions": {
                "US_Open": {"start": "13:30", "end": "20:00", "tz": "GMT"}
            },
            "news_buffer": 30,
            "min_rr": 3.0,
            "round_numbers_interval": 1000,
            "mandatory_sweep": True,
            "weekend_penalty": -1
        },
        "US100": {
            "sessions": {
                "NY_Open": {"start": "13:30", "end": "16:00", "tz": "GMT"},
                "London_Fake": {"start": "08:00", "end": "10:00", "tz": "GMT"}
            },
            "news_buffer": 60,
            "min_rr": 2.5,
            "round_numbers_interval": 100,
            "mandatory_sweep": True,
            "ny_displacement_bonus": 3
        },
        "NAS100": { # Alias for US100
            "sessions": {
                "NY_Open": {"start": "13:30", "end": "16:00", "tz": "GMT"},
                "London_Fake": {"start": "08:00", "end": "10:00", "tz": "GMT"}
            },
            "news_buffer": 60,
            "min_rr": 2.5,
            "round_numbers_interval": 100,
            "mandatory_sweep": True,
            "ny_displacement_bonus": 3
        }
    },
    "indicators": {
        "fib_ote": [0.618, 0.705, 0.786],
        "premium_zone": 0.5,
        "discount_zone": 0.5
    }
}
