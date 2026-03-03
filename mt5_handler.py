import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

class MT5Handler:
    def __init__(self, login=None, password=None, server=None):
        self.login = login
        self.password = password
        self.server = server
        self.connected = False

    def connect(self):
        if not mt5.initialize():
            print("MT5 Initialization failed")
            return False
        
        if self.login and self.password and self.server:
            authorized = mt5.login(self.login, password=self.password, server=self.server)
            if not authorized:
                print(f"Failed to connect to MT5, error code: {mt5.last_error()}")
                return False
        
        self.connected = True
        return True

    def get_market_data(self, symbol, timeframe=mt5.TIMEFRAME_H1, n=1000):
        if not self.connected:
            self.connect()
        
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
        if rates is None:
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df

    def place_order(self, symbol, order_type, volume, sl=None, tp=None, comment="", deviation=3):
        if not self.connected:
            self.connect()

        price = mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": float(sl) if sl else 0.0,
            "tp": float(tp) if tp else 0.0,
            "deviation": deviation,
            "magic": 123456,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        return result

    def close_partial(self, ticket, percentage=50, deviation=3):
        if not self.connected:
            self.connect()
            
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return None
            
        pos = position[0]
        close_volume = round(pos.volume * (percentage / 100.0), 2)
        
        # Minimum lot size check (usually 0.01)
        if close_volume < 0.01:
            close_volume = 0.01
            
        tick = mt5.symbol_info_tick(pos.symbol)
        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": close_volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": deviation,
            "magic": 123456,
            "comment": f"Partial Close {percentage}%",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        return result

    def get_open_positions(self):
        if not self.connected:
            self.connect()
        return mt5.positions_get()

    def update_sl_tp(self, ticket, sl, tp=0.0):
        if not self.connected:
            self.connect()
            
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": float(sl),
            "tp": float(tp),
        }
        result = mt5.order_send(request)
        return result

    def get_history(self, days=30):
        if not self.connected:
            self.connect()
        
        from_date = datetime.now().timestamp() - (days * 24 * 3600)
        to_date = datetime.now().timestamp()
        
        history = mt5.history_deals_get(from_date, to_date)
        if history is None:
            return pd.DataFrame()
            
        df = pd.DataFrame(list(history), columns=history[0]._asdict().keys())
        # Filter for closed deals (profit/loss)
        df = df[df['entry'] == mt5.DEAL_ENTRY_OUT]
        return df

    def get_performance_stats(self, days=30):
        df = self.get_history(days)
        if df.empty:
            return {"winrate": 0, "profit_factor": 0, "total_profit": 0, "equity_curve": [], "trades": 0}
            
        wins = df[df['profit'] > 0]
        losses = df[df['profit'] <= 0]
        
        winrate = (len(wins) / len(df)) * 100 if len(df) > 0 else 0
        total_profit = df['profit'].sum()
        
        gross_profit = wins['profit'].sum()
        gross_loss = abs(losses['profit'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
        
        equity_curve = df['profit'].cumsum().tolist()
        
        return {
            "winrate": winrate,
            "profit_factor": profit_factor,
            "total_profit": total_profit,
            "equity_curve": equity_curve,
            "trades": len(df)
        }

    def disconnect(self):
        mt5.shutdown()
        self.connected = False
