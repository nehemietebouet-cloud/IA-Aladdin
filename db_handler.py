from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from contextlib import contextmanager

Base = declarative_base()

class TradeRecord(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(String(50), unique=True) # MT5 Ticket ID
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)  # Long/Short
    lot_size = Column(Float, default=0.01)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    sl = Column(Float)
    tp = Column(Float)
    status = Column(String(20), default='Open') # Open, Win, Loss, Partial
    profit_loss = Column(Float, default=0.0)
    rr_ratio = Column(Float, default=1.0)
    image_path = Column(String(255))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text)

class DBHandler:
    def __init__(self, db_url="sqlite:///aladdin_v4.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_trade(self, symbol, side, entry_price, lot_size=0.01, sl=None, tp=None, ticket_id=None, image_path=None, notes=None, rr_ratio=1.0):
        with self.session_scope() as session:
            new_trade = TradeRecord(
                symbol=symbol, 
                side=side, 
                entry_price=entry_price,
                lot_size=lot_size,
                sl=sl,
                tp=tp,
                ticket_id=ticket_id,
                image_path=image_path,
                notes=notes,
                rr_ratio=rr_ratio
            )
            session.add(new_trade)
            return new_trade.id

    def get_trades_count_today(self):
        with self.session_scope() as session:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            count = session.query(TradeRecord).filter(TradeRecord.timestamp >= today_start).count()
            return count

    def close_trade(self, ticket_id, exit_price, pnl=None):
        with self.session_scope() as session:
            trade = session.query(TradeRecord).filter_by(ticket_id=ticket_id).first()
            if trade:
                trade.exit_price = exit_price
                if pnl is not None:
                    trade.profit_loss = pnl
                else:
                    if trade.side == 'Long':
                        trade.profit_loss = (exit_price - trade.entry_price) * (trade.lot_size * 100000) # Simple lot conversion
                    else:
                        trade.profit_loss = (trade.entry_price - exit_price) * (trade.lot_size * 100000)
                
                trade.status = 'Win' if trade.profit_loss > 0 else 'Loss'

    def get_recent_performance(self, limit=10):
        with self.session_scope() as session:
            trades = session.query(TradeRecord).filter(TradeRecord.status != 'Open').order_by(TradeRecord.timestamp.desc()).limit(limit).all()
            if not trades:
                return {"winrate": 0.0, "total_pnl": 0.0, "count": 0}
            
            wins = len([t for t in trades if t.status == 'Win'])
            total_pnl = sum([t.profit_loss for t in trades])
            return {
                "winrate": (wins / len(trades)) * 100,
                "total_pnl": total_pnl,
                "count": len(trades)
            }

    def get_all_trades(self):
        with self.session_scope() as session:
            return session.query(TradeRecord).all()

    def calculate_winrate(self):
        perf = self.get_recent_performance(limit=1000)
        return perf["winrate"]
