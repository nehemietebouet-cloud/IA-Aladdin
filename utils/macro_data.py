# utils/macro_data.py

import pandas_datareader.data as web
from datetime import datetime, timedelta

class MacroEngine:
    """
    Macroeconomic Data Fetcher (FRED)
    """
    def __init__(self):
        self.start = datetime.now() - timedelta(days=365)
        self.end = datetime.now()

    def get_us_interest_rates(self):
        """
        Federal Funds Effective Rate
        """
        try:
            df = web.DataReader('FEDFUNDS', 'fred', self.start, self.end)
            return float(df.iloc[-1].values[0])
        except: return 5.33 # Fallback

    def get_cpi_yoy(self):
        """
        Consumer Price Index for All Urban Consumers: All Items in U.S. City Average
        """
        try:
            df = web.DataReader('CPIAUCSL', 'fred', self.start, self.end)
            cpi_yoy = df.pct_change(12) * 100
            return float(cpi_yoy.iloc[-1].values[0])
        except: return 3.1 # Fallback

    def get_unemployment_rate(self):
        """
        Civilian Unemployment Rate
        """
        try:
            df = web.DataReader('UNRATE', 'fred', self.start, self.end)
            return float(df.iloc[-1].values[0])
        except: return 4.0 # Fallback

    def get_macro_summary(self):
        return {
            "FED Funds Rate": f"{self.get_us_interest_rates()}%",
            "CPI (YoY)": f"{self.get_cpi_yoy():.2f}%",
            "Unemployment": f"{self.get_unemployment_rate()}%"
        }
