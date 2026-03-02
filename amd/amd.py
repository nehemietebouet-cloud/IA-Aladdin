# amd.py

import pandas as pd
import numpy as np


class AMD:
    """
    AMD Phase Detection Engine
    Detects:
        - Accumulation
        - Manipulation
        - Distribution
        - Current Phase
        - Confidence Score
    """

    def __init__(self, df: pd.DataFrame, window: int = 20):
        required = ["open", "high", "low", "close", "volume"]
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        self.df = df.copy()
        self.window = window
        self.result = {}

    # ==========================================================
    # VOLATILITY CALCULATION
    # ==========================================================

    def _compute_volatility(self):
        returns = np.log(self.df["close"] / self.df["close"].shift(1))
        self.df["volatility"] = returns.rolling(self.window).std()

    # ==========================================================
    # ACCUMULATION
    # Low volatility + tight range
    # ==========================================================

    def _detect_accumulation(self):
        self.df["range_high"] = self.df["high"].rolling(self.window).max()
        self.df["range_low"] = self.df["low"].rolling(self.window).min()
        self.df["range_size"] = self.df["range_high"] - self.df["range_low"]

        avg_range = self.df["range_size"].rolling(self.window).mean()

        self.df["is_accumulation"] = (
            (self.df["range_size"] < avg_range) &
            (self.df["volatility"] < self.df["volatility"].rolling(self.window).mean())
        )

    # ==========================================================
    # MANIPULATION
    # Liquidity sweep (false breakout)
    # ==========================================================

    def _detect_manipulation(self):
        prev_high = self.df["high"].shift(1)
        prev_low = self.df["low"].shift(1)

        sweep_high = (
            (self.df["high"] > prev_high) &
            (self.df["close"] < prev_high)
        )

        sweep_low = (
            (self.df["low"] < prev_low) &
            (self.df["close"] > prev_low)
        )

        self.df["is_manipulation"] = sweep_high | sweep_low

    # ==========================================================
    # DISTRIBUTION
    # Expansion after range
    # ==========================================================

    def _detect_distribution(self):
        self.df["break_high"] = self.df["close"] > self.df["range_high"]
        self.df["break_low"] = self.df["close"] < self.df["range_low"]

        self.df["is_distribution"] = (
            self.df["break_high"] | self.df["break_low"]
        )

    # ==========================================================
    # PHASE LOGIC
    # ==========================================================

    def _get_phase(self, last_row):
        if last_row["is_manipulation"]:
            return "Manipulation"
        elif last_row["is_distribution"]:
            return "Distribution"
        elif last_row["is_accumulation"]:
            return "Accumulation"
        else:
            return "Neutral"

    # ==========================================================
    # SCORING SYSTEM (AMD ONLY)
    # ==========================================================

    def _compute_score(self, last_row):
        score = 0

        if last_row["is_accumulation"]:
            score += 1

        if last_row["is_manipulation"]:
            score += 2

        if last_row["is_distribution"]:
            score += 3

        confidence = min(score / 6, 1)

        return score, confidence

    # ==========================================================
    # MAIN ANALYSIS FUNCTION
    # ==========================================================

    def analyze(self):

        self._compute_volatility()
        self._detect_accumulation()
        self._detect_manipulation()
        self._detect_distribution()

        last = self.df.iloc[-1]

        phase = self._get_phase(last)
        score, confidence = self._compute_score(last)

        self.result = {
            "phase": phase,
            "score": score,
            "confidence": confidence,
            "range_high": last["range_high"],
            "range_low": last["range_low"],
            "close": last["close"]
        }

        return self.result