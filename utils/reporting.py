# utils/reporting.py

from fpdf import FPDF
from datetime import datetime

class DailyReport(FPDF):
    """
    Automated Daily Trading PDF Report
    """
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Aladdin Quantum Daily Market Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 0, 'C')

    def generate(self, asset, regime, risk_data, predictions, filename="daily_report.pdf"):
        self.add_page()
        self.set_font('Arial', '', 12)
        
        # 1. Market Context
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, f'Asset: {asset}', 0, 1)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f'Market Regime: {regime}', 0, 1)
        
        self.ln(5)
        
        # 2. Risk Metrics
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Risk & Stress Metrics', 0, 1)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f'Value at Risk (VaR 95%): ${risk_data["var"]:.2f}', 0, 1)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, f'Expected Shortfall: ${risk_data["es"]:.2f}', 0, 1)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f'Prob. of Crash (>10%): {risk_data["prob_crash"]*100:.2f}%', 0, 1)
        
        self.ln(5)

        # 3. AI Predictions
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'AI Predictive Consensus', 0, 1)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f'Consensus Prediction: ${predictions["consensus"]:.2f}', 0, 1)
        self.cell(0, 10, f'Predicted Trend: {predictions["trend"]}', 0, 1)
        
        self.ln(10)
        self.set_text_color(255, 0, 0)
        self.cell(0, 10, 'Disclaimer: This report is for analysis only, not financial advice.', 0, 1, 'C')
        
        self.output(filename)
        return filename
