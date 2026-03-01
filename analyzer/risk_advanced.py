# analyzer/risk_advanced.py

import numpy as np
import pandas as pd
from scipy.stats import norm

class AdvancedRisk:
    """
    Advanced Risk Analytics: Expected Shortfall, Monte Carlo, Crash Prob
    """
    def __init__(self, df, balance):
        self.df = df
        self.balance = balance
        self.returns = df['close'].pct_change().dropna()

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
