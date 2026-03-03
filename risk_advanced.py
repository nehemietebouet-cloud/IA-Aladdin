# analyzer/risk_advanced.py

import numpy as np
import pandas as pd
from scipy.stats import norm
import MetaTrader5 as mt5

class AdvancedRisk:
    """
    Advanced Risk Analytics: Expected Shortfall, Monte Carlo, Crash Prob
    And Kill Switch & Dynamic Risk Management
    """
    def __init__(self, df, balance, trade_history=[]):
        self.df = df
        self.balance = balance
        self.trade_history = trade_history # List of dicts with 'result' (profit/loss)
        self.returns = df['close'].pct_change().dropna()

    def calculate_lot_size(self, symbol, risk_pct, sl_distance):
        """
        Calculates lot size based on capital risk and SL distance.
        Max risk_pct = 0.02 (2%) for Hedge Fund stability
        """
        if sl_distance <= 0: return 0.01
        
        # Ensure risk doesn't exceed 2%
        risk_pct = min(risk_pct, 0.02)
        risk_amount = self.balance * risk_pct
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None: return 0.01
        
        # Lot calculation logic: risk_amount / (sl_dist * tick_value_per_lot)
        # Simplified for common forex/gold: 1 lot = 100,000 units
        # tick_value = symbol_info.trade_tick_value
        # tick_size = symbol_info.trade_tick_size
        
        if symbol_info.trade_tick_value == 0 or symbol_info.trade_tick_size == 0:
            return 0.01
            
        points_risk = sl_distance / symbol_info.point
        lot = risk_amount / (points_risk * symbol_info.trade_tick_value / (symbol_info.trade_tick_size / symbol_info.point))
        
        return round(max(0.01, lot), 2)

    def calculate_rr(self, entry, sl, tp):
        """Calculates Risk-Reward Ratio"""
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk == 0: return 0
        return round(reward / risk, 2)

    def check_kill_switch(self, max_consecutive_losses=3, max_drawdown=0.05, current_spread=0, max_spread=5, current_slippage=0, max_slippage=3, trades_today=0):
        """
        Kill Switch Rules:
        1. Stop if consecutive losses > 3
        2. Stop if drawdown > 5% (Daily/Hedge Fund Limit)
        3. Stop if spread or slippage too wide
        4. Max 5 trades per day
        """
        # Max Trades Today
        if trades_today >= 5:
            return False, f"Kill Switch: Max Daily Trades Reached ({trades_today})"

        # Consecutive Losses
        losses = 0
        for trade in reversed(self.trade_history):
            if trade.get('profit', 0) < 0:
                losses += 1
            else:
                break
        
        if losses >= max_consecutive_losses:
            return False, f"Kill Switch: {losses} Consecutive Losses"

        # Drawdown check (from peak)
        if self.trade_history:
            balances = [t.get('balance_after', self.balance) for t in self.trade_history]
            peak = max(balances) if balances else self.balance
            drawdown = (peak - self.balance) / peak
            if drawdown > max_drawdown:
                return False, f"Kill Switch: Drawdown {drawdown:.2%} > {max_drawdown:.2%}"

        # Spread & Slippage
        if current_spread > max_spread:
            return False, f"Kill Switch: High Spread ({current_spread})"
        if current_slippage > max_slippage:
            return False, f"Kill Switch: High Slippage ({current_slippage})"

        return True, "Risk OK"

    def get_dynamic_risk(self, winrate=50.0):
        """
        Institutional Money Management:
        - Winrate < 40% -> 0.5% Risk (Micro)
        - Winrate 40-60% -> 1.0% Risk (Base)
        - Winrate 60-75% -> 1.5% Risk (Aggressive)
        - Winrate > 75% -> 2.0% Risk (Max/Elite)
        """
        if winrate < 40: return 0.005 
        if winrate < 60: return 0.010 
        if winrate < 75: return 0.015 
        return 0.020 

    def expected_shortfall(self, confidence=0.95):
        """
        Calculates Expected Shortfall (Conditional VaR)
        """
        var = np.percentile(self.returns, (1 - confidence) * 100)
        es = self.returns[self.returns <= var].mean()
        return float(abs(es * self.balance))

    def monte_carlo_simulation(self, days=30, simulations=1000):
        """
        Monte Carlo Simulation for future portfolio values
        """
        mu = self.returns.mean()
        sigma = self.returns.std()
        
        results = []
        for _ in range(simulations):
            prices = [self.balance]
            for _ in range(days):
                prices.append(prices[-1] * (1 + np.random.normal(mu, sigma)))
            results.append(prices[-1])
            
        return {
            "mean_future": float(np.mean(results)),
            "worst_case": float(np.percentile(results, 5)),
            "best_case": float(np.percentile(results, 95))
        }

    def probability_of_crash(self, threshold=-0.10):
        """
        Calculates probability of a price drop greater than threshold (%)
        """
        mu = self.returns.mean()
        sigma = self.returns.std()
        
        prob = norm.cdf(threshold, mu, sigma)
        return float(prob)

    def stress_test(self, scenario_pct=-0.15):
        """
        Simulates impact of a specific market event (e.g. -15% Flash Crash)
        """
        impact = self.balance * scenario_pct
        return {
            "scenario": f"{scenario_pct*100}% Crash",
            "loss": float(abs(impact)),
            "remaining_balance": float(self.balance + impact)
        }
