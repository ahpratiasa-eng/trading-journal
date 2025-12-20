import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils import format_currency

def calculate_equity_curve(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menghitung kurva ekuitas kumulatif berdasarkan Realized PnL.
    Asumsi: df sudah di-filter untuk trade yang 'closed' (punya realized_pnl).
    """
    if df.empty:
        return pd.DataFrame()
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Pastikan realized_pnl adalah numeric
    df['realized_pnl'] = pd.to_numeric(df['realized_pnl'], errors='coerce').fillna(0)
    
    # Calculate cumulative PnL
    df['cumulative_pnl'] = df['realized_pnl'].cumsum()
    
    return df

def get_performance_summary(df: pd.DataFrame):
    """
    Menghitung statistik performa trading.
    """
    if df.empty:
        return None
        
    closed_trades = df[df['status'] != 'OPEN'].copy()
    if closed_trades.empty:
        return None
        
    closed_trades['realized_pnl'] = pd.to_numeric(closed_trades['realized_pnl'], errors='coerce').fillna(0)
    
    wins = closed_trades[closed_trades['realized_pnl'] > 0]
    losses = closed_trades[closed_trades['realized_pnl'] <= 0]
    
    num_trades = len(closed_trades)
    num_wins = len(wins)
    num_losses = len(losses)
    
    win_rate = (num_wins / num_trades * 100) if num_trades > 0 else 0
    
    gross_profit = wins['realized_pnl'].sum()
    gross_loss = abs(losses['realized_pnl'].sum())
    
    net_profit = gross_profit - gross_loss
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    
    avg_win = wins['realized_pnl'].mean() if not wins.empty else 0
    avg_loss = losses['realized_pnl'].mean() if not losses.empty else 0
    
    return {
        "total_trades": num_trades,
        "win_rate": win_rate,
        "net_profit": net_profit,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_drawdown": 0, # Placeholder, logic DD agak kompleks
        "wins": num_wins,
        "losses": num_losses
    }

def render_analytics_dashboard(df: pd.DataFrame):
    """
    Render dashboard analitik lengkap di Streamlit.
    """
    if df.empty:
        st.info("Belum ada data trade untuk dianalisa.")
        return

    # Filter hanya trade yang closed untuk PnL
    closed_df = df[df['status'].isin(['WIN', 'LOSS', 'BEP'])].copy()
    
    if closed_df.empty:
        st.info("Belum ada trade yang ditutup (Closed Trades). Selesaikan trade untuk melihat analitik.")
        return

    stats = get_performance_summary(closed_df)
    
    st.markdown("### 📊 Performa Trading")
    
    # 1. Scorecards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Net Profit", format_currency(stats['net_profit'], compact=True), 
                 delta=f"{stats['total_trades']} Trades")
    with col2:
        st.metric("Win Rate", f"{stats['win_rate']:.1f}%", 
                 delta=f"{stats['wins']}W - {stats['losses']}L")
    with col3:
        pf_color = "normal" if stats['profit_factor'] > 1.5 else "off"
        st.metric("Profit Factor", f"{stats['profit_factor']:.2f}", delta_color=pf_color)
    with col4:
        avg_trade = closed_df['realized_pnl'].mean()
        st.metric("Avg Trade", format_currency(avg_trade, compact=True))
    
    st.markdown("---")
    
    # 2. Equity Curve & Bar Chart (Side by Side)
    col_chart1, col_chart2 = st.columns([2, 1])
    
    with col_chart1:
        st.markdown("**📈 Equity Curve (Pertumbuhan Modal)**")
        eq_df = calculate_equity_curve(closed_df)
        
        # Menggunakan Streamlit native line chart biar ringan
        # Kita set index ke timestamp atau counter
        chart_data = eq_df[['timestamp', 'cumulative_pnl']].set_index('timestamp')
        st.line_chart(chart_data, color="#00b894")
        
    with col_chart2:
        st.markdown("**⚖️ Win vs Loss Distribution**")
        # Simple Pie Chart using Plotly Express if available, else standard metrics
        try:
            fig = px.pie(names=['Win', 'Loss'], values=[stats['wins'], stats['losses']], 
                         color_discrete_sequence=['#00b894', '#d63031'], hole=0.4)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
        except:
             st.progress(stats['win_rate'] / 100)
             st.caption(f"Win Rate: {stats['win_rate']:.1f}%")

    # 3. PnL per Ticker (Horizontal Bar)
    st.markdown("**🏆 Performa per Saham (Ticker)**")
    ticker_stats = closed_df.groupby('ticker')['realized_pnl'].sum().sort_values()
    
    if not ticker_stats.empty:
        # Warnai bar: Hijau cuan, Merah loss
        colors = ['#d63031' if x < 0 else '#00b894' for x in ticker_stats.values]
        
        # Gunakan Plotly untuk kontrol warna yang lebih baik
        fig_bar = go.Figure(go.Bar(
            x=ticker_stats.values,
            y=ticker_stats.index,
            orientation='h',
            marker_color=colors
        ))
        
        fig_bar.update_layout(
            title="Net PnL per Ticker",
            xaxis_title="Profit/Loss (Rp)",
            height=400,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig_bar, use_container_width=True)
