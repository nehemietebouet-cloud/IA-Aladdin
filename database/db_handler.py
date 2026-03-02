from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class TradeRecord(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)  # Long/Short
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    status = Column(String(20), default='Open') # Open, Win, Loss
    profit_loss = Column(Float, default=0.0)
    image_path = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)

class DBHandler:
    def __init__(self, db_url="sqlite:///aladdin_v4.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_trade(self, symbol, side, entry_price, image_path=None, notes=None):
        session = self.Session()
        new_trade = TradeRecord(
            symbol=symbol, 
            side=side, 
            entry_price=entry_price, 
            image_path=image_path,
            notes=notes
        )
        session.add(new_trade)
        session.commit()
        trade_id = new_trade.id
        session.close()
        return trade_id

    def close_trade(self, trade_id, exit_price):
        session = self.Session()
        trade = session.query(TradeRecord).filter_by(id=trade_id).first()
        if trade:
            trade.exit_price = exit_price
            # Simple win/loss logic for demonstration
            if trade.side == 'Long':
                trade.profit_loss = exit_price - trade.entry_price
            else:
                trade.profit_loss = trade.entry_price - exit_price
            
            trade.status = 'Win' if trade.profit_loss > 0 else 'Loss'
            session.commit()
        session.close()

    def get_all_trades(self):
        session = self.Session()
        trades = session.query(TradeRecord).all()
        session.close()
        return trades

    def calculate_winrate(self):
        session = self.Session()
        total = session.query(TradeRecord).filter(TradeRecord.status != 'Open').count()
        wins = session.query(TradeRecord).filter_by(status='Win').count()
        session.close()
        return (wins / total * 100) if total > 0 else 0.0
