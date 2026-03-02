# logger/log.py

import logging
import sys
from datetime import datetime

class TradingLogger:
    """
    Centralized logging for the Aladdin Trading AI
    """
    def __init__(self, name="AladdinAI"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console Handler
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        self.logger.addHandler(sh)

        # File Handler
        fh = logging.FileHandler(f"trading_log_{datetime.now().strftime('%Y%m%d')}.log")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def info(self, msg): self.logger.info(msg)
    def error(self, msg): self.logger.error(msg)
    def warning(self, msg): self.logger.warning(msg)

# Singleton instance
logger = TradingLogger()
