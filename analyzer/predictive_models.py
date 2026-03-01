# analyzer/predictive_models.py

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import Ridge
from utils.indicators import calculate_rsi, calculate_ema, calculate_bollinger_bands, calculate_atr

class PredictiveModels:
    """
    Price Prediction Suite: Ridge Regression, Random Forest, XGBoost
    """
    def __init__(self, df):
        self.df = df.copy()
        self._prepare_data()

    def _prepare_data(self):
        # Technical Indicators
        self.df['rsi'] = calculate_rsi(self.df['close'])
        self.df['ema_20'] = calculate_ema(self.df['close'], 20)
        self.df['ema_50'] = calculate_ema(self.df['close'], 50)
        up, mid, low = calculate_bollinger_bands(self.df['close'])
        self.df['bb_upper'] = up
        self.df['bb_lower'] = low
        self.df['atr'] = calculate_atr(self.df)
        
        # Momentum & Volatility
        self.df['return'] = self.df['close'].pct_change()
        self.df['volatility'] = self.df['return'].rolling(window=10).std()
        self.df['target'] = self.df['close'].shift(-1)
        
        self.data = self.df.dropna()
        
        self.features = ['open', 'high', 'low', 'close', 'volatility', 'rsi', 'ema_20', 'ema_50', 'bb_upper', 'bb_lower', 'atr']
        self.X = self.data[self.features]
        self.y = self.data['target']

    def run_random_forest(self):
        model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)
        model.fit(self.X[:-1], self.y[:-1])
        prediction = model.predict(self.X.tail(1))
        return float(prediction[0])

    def run_xgboost(self):
        model = XGBRegressor(n_estimators=200, learning_rate=0.03, max_depth=6)
        model.fit(self.X[:-1], self.y[:-1])
        prediction = model.predict(self.X.tail(1))
        return float(prediction[0])

    def run_ridge(self, lookback=20):
        """
        Ridge Regression for stable time-series prediction (TensorFlow alternative)
        """
        model = Ridge(alpha=1.0)
        model.fit(self.X[:-1], self.y[:-1])
        prediction = model.predict(self.X.tail(1))
        return float(prediction[0])

    def get_historical_weights(self):
        """
        Runs a quick historical test to find which model performed best on THIS specific asset
        """
        # Split data for quick backtest
        split = int(len(self.X) * 0.9)
        X_train, X_test = self.X[:split], self.X[split:]
        y_train, y_test = self.y[:split], self.y[split:]
        
        # Train RF
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X_train, y_train)
        rf_score = rf.score(X_test, y_test)
        
        # Train XGB
        xgb = XGBRegressor(n_estimators=100, learning_rate=0.05)
        xgb.fit(X_train, y_train)
        xgb_score = xgb.score(X_test, y_test)
        
        # Train Ridge
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_train, y_train)
        ridge_score = ridge.score(X_test, y_test)
        
        # Normalize scores to weights (min weight 0.1 to avoid total exclusion)
        scores = np.array([max(0.1, rf_score), max(0.1, xgb_score), max(0.1, ridge_score)])
        weights = scores / scores.sum()
        
        return weights

    def get_consensus_prediction(self):
        rf = self.run_random_forest()
        xgb = self.run_xgboost()
        ridge = self.run_ridge()
        
        # Dynamic Weights based on 10-year historical performance
        weights = self.get_historical_weights()
        avg_pred = (rf * weights[0]) + (xgb * weights[1]) + (ridge * weights[2])
        
        current_price = self.df['close'].iloc[-1]
        trend = "Strong Bullish" if avg_pred > current_price * 1.01 else \
                "Bullish" if avg_pred > current_price else \
                "Strong Bearish" if avg_pred < current_price * 0.99 else \
                "Bearish"
        
        # Calculate reliability based on R-squared scores
        reliability = (weights.max() * 100)
        
        return {
            "rf": round(rf, 2),
            "xgb": round(xgb, 2),
            "ridge": round(ridge, 2),
            "consensus": round(avg_pred, 2),
            "trend": trend,
            "reliability": f"{reliability:.2f}%",
            "weights": {
                "RF": round(weights[0], 2),
                "XGB": round(weights[1], 2),
                "Ridge": round(weights[2], 2)
            }
        }
