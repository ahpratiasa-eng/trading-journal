import pandas as pd
import numpy as np
import yfinance as yf
from dataclasses import dataclass
from datetime import datetime
from utils import calculate_ema, calculate_rsi

@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    metrics: dict
    df_data: pd.DataFrame  # Processed data for charting

# =============================================================================
# STRATEGIES
# =============================================================================

def strategy_ma_cross(df: pd.DataFrame, fast_period=20, slow_period=50) -> pd.DataFrame:
    """
    Strategy: Golden Cross / Death Cross
    Buy: Fast MA crosses above Slow MA
    Sell: Fast MA crosses below Slow MA
    """
    df = df.copy()
    df['Fast_MA'] = calculate_ema(df['Close'], fast_period)
    df['Slow_MA'] = calculate_ema(df['Close'], slow_period)
    
    # Signal: 1 (Buy), -1 (Sell), 0 (Hold)
    df['signal'] = 0
    
    # Vectorized signal generation
    # Cross Over (Buy)
    df.loc[(df['Fast_MA'] > df['Slow_MA']) & (df['Fast_MA'].shift(1) <= df['Slow_MA'].shift(1)), 'signal'] = 1
    
    # Cross Under (Sell)
    df.loc[(df['Fast_MA'] < df['Slow_MA']) & (df['Fast_MA'].shift(1) >= df['Slow_MA'].shift(1)), 'signal'] = -1
    
    return df

def strategy_rsi_reversal(df: pd.DataFrame, period=14, oversold=30, overbought=70) -> pd.DataFrame:
    """
    Strategy: RSI Reversal
    Buy: RSI crosses above Oversold (30) from below
    Sell: RSI crosses below Overbought (70) from above
    """
    df = df.copy()
    df['RSI'] = calculate_rsi(df['Close'], period)
    df['signal'] = 0
    
    # Buy: RSI < 30 yesterday AND RSI > 30 today
    df.loc[(df['RSI'] > oversold) & (df['RSI'].shift(1) <= oversold), 'signal'] = 1
    
    # Sell: RSI > 70 yesterday AND RSI < 70 today
    df.loc[(df['RSI'] < overbought) & (df['RSI'].shift(1) >= overbought), 'signal'] = -1
    
    return df

def strategy_breakout(df: pd.DataFrame, lookback=20) -> pd.DataFrame:
    """
    Strategy: Donchian Channel Breakout
    Buy: Close > Highest High of last N days
    Sell: Close < Lowest Low of last N/2 days
    """
    df = df.copy()
    df['High_Roll'] = df['High'].rolling(lookback).max().shift(1)
    df['Low_Roll'] = df['Low'].rolling(int(lookback/2)).min().shift(1)
    
    df['signal'] = 0
    
    df.loc[df['Close'] > df['High_Roll'], 'signal'] = 1
    df.loc[df['Close'] < df['Low_Roll'], 'signal'] = -1
    
    return df

# =============================================================================
# BACKTEST ENGINE
# =============================================================================

class BacktestEngine:
    def __init__(self, initial_capital=10_000_000, fee_buy=0.0015, fee_sell=0.0025):
        self.initial_capital = initial_capital
        self.fee_buy = fee_buy
        self.fee_sell = fee_sell

    def fetch_data(self, ticker: str, start_date, end_date):
        symbol = f"{ticker}.JK"
        try:
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if df.empty:
                return pd.DataFrame()
            
            # Flatten multi-index if present (yfinance update compatibility)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()

    def run(self, ticker: str, start_date, end_date, strategy_type="MA Cross", **params) -> BacktestResult:
        # 1. Fetch Data
        df = self.fetch_data(ticker, start_date, end_date)
        if df.empty:
            return None
        
        # 2. Apply Strategy
        if strategy_type == "MA Cross":
            df = strategy_ma_cross(df, **params)
        elif strategy_type == "RSI Reversal":
            df = strategy_rsi_reversal(df, **params)
        elif strategy_type == "Breakout":
            df = strategy_breakout(df, **params)
        else:
            # Default fallback
            df = strategy_ma_cross(df)

        # 3. Simulate Trades
        capital = self.initial_capital
        position_lots = 0
        trades = []
        equity_curve = []
        
        # We define states
        in_position = False
        
        for date, row in df.iterrows():
            price = row['Close']
            signal = row.get('signal', 0)
            
            # Record Equity (Mark to Market)
            current_val = capital
            if in_position:
                market_value = position_lots * 100 * price
                current_val += market_value
            
            equity_curve.append({
                'timestamp': date,
                'equity': current_val,
                'drawdown': 0 # Calculated later
            })
            
            # --- EXECUTION LOGIC ---
            
            # SELL SIGNAL
            if in_position and signal == -1:
                shares = position_lots * 100
                gross_proceeds = shares * price
                fee = gross_proceeds * self.fee_sell
                net_proceeds = gross_proceeds - fee
                
                capital += net_proceeds
                
                # Update Trade Record
                last_trade = trades[-1]
                last_trade['exit_date'] = date
                last_trade['exit_price'] = price
                last_trade['gross_pnl'] = gross_proceeds - last_trade['gross_cost']
                last_trade['net_pnl'] = net_proceeds - last_trade['total_cost']
                last_trade['return_pct'] = (last_trade['net_pnl'] / last_trade['total_cost']) * 100
                last_trade['status'] = 'WIN' if last_trade['net_pnl'] > 0 else 'LOSS'
                
                in_position = False
                position_lots = 0
                
            # BUY SIGNAL
            elif not in_position and signal == 1:
                # Calculate max lots affordable
                # Cost = (Lots * 100 * Price) * (1 + Fee)
                max_val = capital / (1 + self.fee_buy)
                shares = int(max_val / price)
                lots = shares // 100
                
                if lots > 0:
                    shares_cost = lots * 100 * price
                    fee = shares_cost * self.fee_buy
                    total_cost = shares_cost + fee
                    
                    capital -= total_cost
                    position_lots = lots
                    in_position = True
                    
                    trades.append({
                        'ticker': ticker,
                        'entry_date': date,
                        'entry_price': price,
                        'lots': lots,
                        'gross_cost': shares_cost,
                        'total_cost': total_cost,
                        'exit_date': None,
                        'exit_price': None,
                        'net_pnl': 0,
                        'return_pct': 0,
                        'status': 'OPEN'
                    })

        # Close open position at end
        if in_position:
            last_price = df.iloc[-1]['Close']
            last_date = df.index[-1]
            
            shares = position_lots * 100
            gross = shares * last_price
            fee = gross * self.fee_sell
            net = gross - fee
            
            trade = trades[-1]
            trade['exit_date'] = last_date
            trade['exit_price'] = last_price
            trade['net_pnl'] = net - trade['total_cost']
            trade['return_pct'] = (trade['net_pnl'] / trade['total_cost']) * 100
            trade['status'] = 'OPEN (End)'
            
            # Update final equity
            equity_curve[-1]['equity'] = capital + net

        # 4. Process Results
        trades_df = pd.DataFrame(trades)
        equity_df = pd.DataFrame(equity_curve)
        if not equity_df.empty:
            equity_df = equity_df.set_index('timestamp')
            # Calculate Drawdown
            equity_df['peak'] = equity_df['equity'].cummax()
            equity_df['drawdown_pct'] = ((equity_df['equity'] - equity_df['peak']) / equity_df['peak']) * 100

        metrics = self._calculate_metrics(trades_df, equity_df)
        
        return BacktestResult(trades_df, equity_df, metrics, df)

    def generate_live_signal(self, ticker: str, strategy_type="MA Cross", **params):
        """
        Check the latest signal based on the strategy.
        Fetches 6 months of data to ensure indicators are stable.
        """
        end_date = datetime.now()
        start_date = end_date - pd.DateOffset(months=6)
        
        df = self.fetch_data(ticker, start_date, end_date)
        if df.empty:
            return "UNKNOWN", "Data tidak tersedia"
        
        # Apply Strategy
        if strategy_type == "MA Cross":
            df = strategy_ma_cross(df, **params)
            last_row = df.iloc[-1]
            signal = last_row.get('signal', 0)
            
            fast = last_row['Fast_MA']
            slow = last_row['Slow_MA']
            
            if signal == 1:
                return "BUY", f"Golden Cross! Fast MA ({fast:.0f}) > Slow MA ({slow:.0f})"
            elif signal == -1:
                return "SELL", f"Death Cross! Fast MA ({fast:.0f}) < Slow MA ({slow:.0f})"
            else:
                # Check current state if no signal today
                if fast > slow:
                    return "HOLD_BUY", f"Uptrend (Harga > MA). Fast ({fast:.0f}) > Slow ({slow:.0f})"
                else:
                    return "HOLD_SELL", f"Downtrend (Harga < MA). Fast ({fast:.0f}) < Slow ({slow:.0f})"
                    
        elif strategy_type == "RSI Reversal":
            df = strategy_rsi_reversal(df, **params)
            last_row = df.iloc[-1]
            signal = last_row.get('signal', 0)
            rsi = last_row['RSI']
            
            if signal == 1:
                return "BUY", f"RSI Reversal Up! RSI ({rsi:.1f}) crossed above {params.get('oversold', 30)}"
            elif signal == -1:
                return "SELL", f"RSI Reversal Down! RSI ({rsi:.1f}) crossed below {params.get('overbought', 70)}"
            else:
                if rsi > 50:
                    return "NEUTRAL", f"RSI Bullish Zone ({rsi:.1f})"
                else:
                    return "NEUTRAL", f"RSI Bearish Zone ({rsi:.1f})"
                    
        elif strategy_type == "Breakout":
            df = strategy_breakout(df, **params)
            last_row = df.iloc[-1]
            signal = last_row.get('signal', 0)
            close = last_row['Close']
            high_roll = last_row['High_Roll']
            
            if signal == 1:
                return "BUY", f"Breakout! Close ({close}) > High {params.get('lookback', 20)} days ({high_roll})"
            elif signal == -1:
                return "SELL", "Breakdown Low!"
            else:
                return "NEUTRAL", f"Consolidation. Price {close}"
        
        return "NEUTRAL", "Strategy not recognized"

    def _calculate_metrics(self, trades_df, equity_df):
        if trades_df.empty:
            return {
                "total_trades": 0, "win_rate": 0, "net_profit": 0, 
                "max_drawdown": 0, "profit_factor": 0, "final_equity": self.initial_capital
            }
            
        wins = trades_df[trades_df['net_pnl'] > 0]
        losses = trades_df[trades_df['net_pnl'] <= 0]
        
        total_trades = len(trades_df)
        win_rate = (len(wins) / total_trades) * 100
        net_profit = trades_df['net_pnl'].sum()
        
        gross_profit = wins['net_pnl'].sum()
        gross_loss = abs(losses['net_pnl'].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        max_dd = equity_df['drawdown_pct'].min() if not equity_df.empty else 0
        final_equity = equity_df['equity'].iloc[-1] if not equity_df.empty else self.initial_capital
        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "net_profit": net_profit,
            "max_drawdown": max_dd,
            "profit_factor": profit_factor,
            "final_equity": final_equity,
            "return_pct": ((final_equity - self.initial_capital) / self.initial_capital) * 100
        }
