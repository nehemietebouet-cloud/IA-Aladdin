# utils/analytics.py

import pandas as pd
import numpy as np

class MarketAnalytics:
    """
    Volatility & Correlation Analysis
    """
    def __init__(self, data_dict):
        self.data_dict = data_dict # Dict of DataFrames for each asset

    def calculate_correlations(self):
        """
        Matrix of correlations between all assets
        """
        closes = {symbol: df['close'] for symbol, df in self.data_dict.items()}
        df_closes = pd.DataFrame(closes).dropna()
        return df_closes.corr()

    def analyze_volatility(self, symbol, window=20):
        """
        Calculates Historical Volatility and Volatility Clusters
        """
        df = self.data_dict[symbol]
        returns = df['close'].pct_change().dropna()
        hist_vol = returns.rolling(window=window).std() * np.sqrt(252) # Annualized
        
        # Volatility Clustering detection
        is_cluster = (returns.abs() > returns.abs().rolling(window=window).mean()).iloc[-1]
        
        return {
            "current_vol": round(hist_vol.iloc[-1], 4),
            "is_cluster": bool(is_cluster)
        }

    def beta_analysis(self, asset_symbol, benchmark_symbol="NAS100"):
        """
        Calculates Beta of an asset relative to a benchmark
        """
        asset_ret = self.data_dict[asset_symbol]['close'].pct_change().dropna()
        bench_ret = self.data_dict[benchmark_symbol]['close'].pct_change().dropna()
        
        # Align indices
        common_idx = asset_ret.index.intersection(bench_ret.index)
        asset_ret = asset_ret.loc[common_idx]
        bench_ret = bench_ret.loc[common_idx]
        
        covariance = np.cov(asset_ret, bench_ret)[0][1]
        variance = np.var(bench_ret)
        
        return round(covariance / variance, 2)
