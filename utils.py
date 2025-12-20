import pandas as pd
import numpy as np

# Optional import for charting
try:
    import mplfinance as mpf
    import matplotlib.pyplot as plt
    CHART_AVAILABLE = True
except ImportError:
    CHART_AVAILABLE = False

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=period).mean()

def calculate_pivot_points(df):
    if len(df) < 2:
        return 0, 0, 0
    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]
    high = prev_candle['High']
    low = prev_candle['Low']
    close = prev_candle['Close']
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    return int(pivot), int(r1), int(s1)

def calculate_obv(df):
    obv = [0]
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
            obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=df.index)

def calculate_vwap(df):
    v = df['Volume']
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * v).cumsum() / v.cumsum()

def format_currency(amount: float, compact: bool = False) -> str:
    """Format jumlah sebagai Rupiah Indonesia."""
    if compact:
        if abs(amount) >= 1_000_000_000:
            return f"Rp {amount/1_000_000_000:.1f}M"
        elif abs(amount) >= 1_000_000:
            return f"Rp {amount/1_000_000:.1f}Jt"
        elif abs(amount) >= 1_000:
            return f"Rp {amount/1_000:.0f}Rb"
        else:
            return f"Rp {amount:,.0f}"
    return f"Rp {amount:,.0f}"

def format_percentage(value: float) -> str:
    """Format nilai sebagai persentase."""
    return f"{value:.2f}%"

def render_chart(df, title="Chart"):
    if not CHART_AVAILABLE or df is None or df.empty:
        return None
    try:
        if len(df) > 100:
            plot_df = df.tail(100)
        else:
            plot_df = df
        
        # Calculate indicators for chart
        plot_df = plot_df.copy()
        plot_df['EMA20'] = calculate_ema(plot_df['Close'], 20)
        plot_df['EMA50'] = calculate_ema(plot_df['Close'], 50)
        
        apds = [
            mpf.make_addplot(plot_df['EMA20'], color='blue', width=1.0),
            mpf.make_addplot(plot_df['EMA50'], color='orange', width=1.0)
        ]
        
        # Style
        mc = mpf.make_marketcolors(up='g', down='r', inherit=True)
        s = mpf.make_mpf_style(base_mpf_style='yahoo', marketcolors=mc)
        
        fig, axes = mpf.plot(
            plot_df,
            type='candle',
            style=s,
            volume=True,
            addplot=apds,
            title=title,
            returnfig=True,
            figsize=(10, 6),
            tight_layout=True
        )
        return fig
    except Exception as e:
        print(f"Error rendering chart: {e}")
        return None
