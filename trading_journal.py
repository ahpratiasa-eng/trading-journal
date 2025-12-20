"""
Pro Trading Journal & Kalkulator
================================
Alat disiplin untuk Day Trading/Scalping di Bursa Efek Indonesia (IDX).
Memaksa perhitungan Risiko, Reward, dan Fee sebelum eksekusi trade.

Author: Trading Systems Architect
Version: 1.1.0 - Bahasa Indonesia
"""

# File paths
DEFAULT_JOURNAL_FILE = "trading_journal.csv"


import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt

# Imports Refactored
from utils import (calculate_ema, calculate_atr, calculate_rsi, calculate_pivot_points,
                   calculate_obv, calculate_vwap, render_chart, format_currency,
                   format_percentage, CHART_AVAILABLE)
from models import (TradeSetup, TradeRecord, LOT_SIZE, MIN_RRR_THRESHOLD, 
                    DEFAULT_BUY_FEE_PCT, DEFAULT_SELL_FEE_PCT)
from data_manager import DataPersistence, CSVPersistence, FirestorePersistence, DEFAULT_JOURNAL_FILE
from market_client import (get_market_insight, batch_scan, scan_gem, scan_dragon,
                           scan_daytrade, parse_ticker_input, MARKET_INTEL_AVAILABLE)
from analytics import render_analytics_dashboard


# =============================================================================
# MARKET INTELLIGENCE (Auto-fetch data dari Yahoo Finance)
# =============================================================================

# Helper functions moved to utils.py and market_client.py


# Models and Persistence moved to models.py and data_manager.py



# Future: Implementasi Google Sheets
# class GoogleSheetsPersistence(DataPersistence):
#     """
#     Implementasi persistensi data berbasis Google Sheets.
#     Membutuhkan: pip install gspread oauth2client
#     """


def get_persistence() -> DataPersistence:
    """
    Factory function untuk mendapatkan layer persistensi.
    Auto-detect Cloud vs Local based on secrets.
    """
    if "gcp_service_account" in st.secrets:
        return FirestorePersistence()
    return CSVPersistence(DEFAULT_JOURNAL_FILE)


# =============================================================================
# FUNGSI HELPER UI
# =============================================================================

# format_currency moved to utils.py, format_percentage moved to utils.py



def get_rrr_status(rrr: float) -> tuple[str, str]:
    """Dapatkan status RRR dan warna berdasarkan threshold."""
    if rrr >= MIN_RRR_THRESHOLD:
        return "✅ BAGUS", "green"
    elif rrr >= 1.0:
        return "⚠️ MARGINAL", "orange"
    else:
        return "❌ JELEK", "red"


def create_metric_card(label: str, value: str, delta: str = None, delta_color: str = "normal"):
    """Buat tampilan metrik bergaya."""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


# =============================================================================
# APLIKASI UTAMA
# =============================================================================

def main():
    # Konfigurasi halaman
    st.set_page_config(
        page_title="Jurnal Trading Pro",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS untuk desain mobile-first dan styling
    st.markdown("""
    <style>
        /* Desain responsif mobile-first */
        .stMetric {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #0f3460;
        }
        
        .stMetric label {
            color: #a0a0a0 !important;
            font-size: 0.9rem !important;
        }
        
        .stMetric [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
            font-weight: 700 !important;
            color: #e94560 !important;
        }
        
        /* Banner Keputusan */
        .strong-buy {
            background: linear-gradient(135deg, #00b894 0%, #00cec9 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            font-size: 2rem;
            font-weight: bold;
            margin: 20px 0;
            box-shadow: 0 10px 30px rgba(0, 184, 148, 0.3);
            animation: pulse 2s infinite;
        }
        
        .no-trade {
            background: linear-gradient(135deg, #d63031 0%, #e17055 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            font-size: 2rem;
            font-weight: bold;
            margin: 20px 0;
            box-shadow: 0 10px 30px rgba(214, 48, 49, 0.3);
        }
        
        .caution {
            background: linear-gradient(135deg, #fdcb6e 0%, #f39c12 100%);
            color: #2d3436;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            font-size: 2rem;
            font-weight: bold;
            margin: 20px 0;
            box-shadow: 0 10px 30px rgba(253, 203, 110, 0.3);
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); }
            100% { transform: scale(1); }
        }
        
        /* Styling sidebar */
        .css-1d391kg {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        }
        
        /* Kotak info */
        .info-box {
            background: #16213e;
            border-left: 4px solid #e94560;
            padding: 15px;
            border-radius: 0 10px 10px 0;
            margin: 10px 0;
        }
        
        /* Kotak peringatan */
        .warning-box {
            background: #3d1f1f;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            border-radius: 0 10px 10px 0;
            margin: 10px 0;
        }
        
        /* Kotak sukses */
        .success-box {
            background: #1f3d2d;
            border-left: 4px solid #27ae60;
            padding: 15px;
            border-radius: 0 10px 10px 0;
            margin: 10px 0;
        }
        
        /* Styling header */
        h1 {
            color: #e94560 !important;
            font-weight: 700 !important;
        }
        
        h2, h3 {
            color: #0f3460 !important;
        }
        
        /* Styling checkbox */
        .stCheckbox label {
            font-size: 1rem !important;
        }
        
        /* Kolom responsif */
        @media (max-width: 768px) {
            .stMetric [data-testid="stMetricValue"] {
                font-size: 1.4rem !important;
            }
            .strong-buy, .no-trade, .caution {
                font-size: 1.5rem;
                padding: 15px;
            }
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        [data-testid="stToolbar"] {display: none;}
        [data-testid="stDecoration"] {display: none;}
        [data-testid="stStatusWidget"] {display: none;}
        .viewerBadge_container__1QSob {display: none !important;}
        .styles_viewerBadge__1yB5_ {display: none !important;}
        .viewerBadge_link__1S137 {display: none !important;}
        .css-15zrgzn {display: none !important;}
        .css-eczf16 {display: none !important;}
        .css-jn99sy {display: none !important;}
    </style>
    """, unsafe_allow_html=True)
    
    # Inisialisasi persistensi
    persistence = get_persistence()
    
    # Show Database Mode
    if isinstance(persistence, FirestorePersistence):
        st.sidebar.success("☁️ Cloud Mode (Firestore)")
    else:
        st.sidebar.info("📂 Local Mode (CSV)")
    
    # ==========================================================================
    # LOAD/SAVE USER SETTINGS (Auto-save modal & risk)
    # ==========================================================================
    
    SETTINGS_FILE = "user_settings.json"
    
    def load_user_settings() -> dict:
        """Load user settings dari file JSON."""
        import json
        default_settings = {
            "capital": 5_000_000,
            "risk_percent": 1.0,
            "buy_fee_pct": 0.15,
            "sell_fee_pct": 0.25
        }
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    return {**default_settings, **json.load(f)}
        except:
            pass
        return default_settings
    
    def save_user_settings(settings: dict):
        """Simpan user settings ke file JSON."""
        import json
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f)
        except:
            pass
    
    # Load saved settings
    if 'user_settings' not in st.session_state:
        st.session_state.user_settings = load_user_settings()
    
    # ==========================================================================
    # PROFIL CEPAT (Quick Profiles)
    # ==========================================================================
    
    QUICK_PROFILES = {
        "🛡️ Konservatif": {"risk_percent": 0.5, "desc": "Risiko rendah"},
        "⚖️ Moderat": {"risk_percent": 1.0, "desc": "Risiko seimbang"},
        "🔥 Agresif": {"risk_percent": 2.0, "desc": "Risiko tinggi"},
        "💀 YOLO": {"risk_percent": 5.0, "desc": "All-in!"},
    }
    
    # ==========================================================================
    # SIDEBAR - Setup Trade Lanjutan
    # ==========================================================================
    
    with st.sidebar:
        st.title("🎯 Setup Trade")
        
        # === 🏆 WIN RATE KEEPER (Pressure Bar) ===
        try:
            trades_df = persistence.load_trades()
            if not trades_df.empty and 'result' in trades_df.columns:
                total_trades = len(trades_df)
                # Assuming 'result' column has 'WIN' or 'LOSS' values
                wins = len(trades_df[trades_df['result'].str.upper() == 'WIN'])
                win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                
                # Color based on performance
                if win_rate >= 70:
                    wr_color = "🟢"
                    wr_status = "EXCELLENT"
                elif win_rate >= 50:
                    wr_color = "🟡"
                    wr_status = "GOOD"
                else:
                    wr_color = "🔴"
                    wr_status = "NEEDS WORK"
                
                st.markdown(f"### 🏆 Win Rate Keeper")
                st.progress(min(win_rate / 100, 1.0))
                st.markdown(f"**{wr_color} {win_rate:.1f}%** ({wins}W/{total_trades - wins}L) - {wr_status}")
                
                if win_rate < 50:
                    st.warning("⚠️ Win Rate di bawah 50%. Evaluasi strategi!")
                st.markdown("---")
        except:
            pass  # Skip if no journal data yet
        
        # === PROFIL CEPAT ===
        st.markdown("### ⚡ Profil Cepat")
        st.caption("Klik untuk set risiko instan")
        
        profile_cols = st.columns(2)
        for idx, (profile_name, profile_data) in enumerate(QUICK_PROFILES.items()):
            col = profile_cols[idx % 2]
            with col:
                if st.button(profile_name, key=f"profile_{idx}", use_container_width=True):
                    st.session_state.selected_risk = profile_data["risk_percent"]
        
        st.markdown("---")
        
        # === STRATEGY MODE SELECTOR ===
        strategy_modes = {
            "📈 Swing/Normal (EMA-based)": "swing",
            "⚡ Scalper (Open=Low)": "scalper",
            "🐋 Mini-Bandar (VWAP Flow)": "minibandar"
        }
        
        strategy_mode = st.selectbox(
            "🎮 Strategy Mode",
            options=list(strategy_modes.keys()),
            help="Pilih gaya trading - logic checklist berubah sesuai mode"
        )
        is_scalping_mode = strategy_modes[strategy_mode] == "scalper"
        is_minibandar_mode = strategy_modes[strategy_mode] == "minibandar"
        
        # Store in session
        st.session_state.strategy_mode = strategy_mode
        st.session_state.is_scalping_mode = is_scalping_mode
        st.session_state.is_minibandar_mode = is_minibandar_mode
        
        st.markdown("---")
        
        # Input Ticker (with support for selected_ticker from batch scanner)
        # Initialize ticker_input in session state if not exists
        if "ticker_input" not in st.session_state:
            st.session_state.ticker_input = ""
        
        # If selected_ticker is set (from Quick Analyze), update ticker_input
        if "selected_ticker" in st.session_state:
            st.session_state.ticker_input = st.session_state.selected_ticker
            del st.session_state.selected_ticker
        
        ticker = st.text_input(
            "📌 Kode Saham",
            key="ticker_input",
            placeholder="contoh: BBCA",
            help="Masukkan kode saham atau pilih dari Batch Scanner"
        ).upper().strip()
        
        # === MARKET INTELLIGENCE ===
        market_price = 0
        ema20_price = 0
        ema50_price = 0
        sl_atr_price = 0
        tp_atr_price = 0
        r1_price = 0
        s1_price = 0
        
        # Initialize smart checklist flags
        auto_checks = {
            "is_uptrend": False,
            "vol_above_avg": False,
            "rsi_ok": True,
            "is_morning_spike": False,
            "price_above_vwap": False,
            "vol_above_5d": False
        }
        
        if ticker and MARKET_INTEL_AVAILABLE:
            with st.expander("📊 Market Intel & Chart", expanded=False):
                if st.button("🔍 Analisa Saham", use_container_width=True):
                    with st.spinner("Mengambil data..."):
                        df_hist, market_result = get_market_insight(ticker)
                        if "error" not in market_result:
                            st.session_state.market_data = market_result
                            st.session_state.chart_df = df_hist  # Store for chart
                        else:
                            st.error(market_result["error"])
                
                # Show cached insight
                if 'market_data' in st.session_state and st.session_state.market_data.get("price", 0) > 0:
                    md = st.session_state.market_data
                    
                    # === CHART SECTION ===
                    if CHART_AVAILABLE and 'chart_df' in st.session_state:
                        chart_df = st.session_state.chart_df
                        
                        # Adaptive timeframe based on strategy mode
                        if is_scalping_mode:
                            # Scalper: Try to get intraday 5-min data
                            st.caption("⚡ Mode Scalper: Mencoba ambil data 5 menit...")
                            try:
                                intraday_df = yf.download(f"{ticker}.JK", period="1d", interval="5m", progress=False)
                                if not intraday_df.empty:
                                    chart_df = intraday_df
                                    chart_title = f"{ticker} - Intraday (5 Menit)"
                                else:
                                    chart_title = f"{ticker} - Daily Chart"
                            except:
                                chart_title = f"{ticker} - Daily Chart"
                        else:
                            chart_title = f"{ticker} - Daily Chart (3 Bulan)"
                        
                        # Get date range from chart data
                        if chart_df is not None and not chart_df.empty:
                            start_date = chart_df.index[0].strftime("%d %b %Y")
                            end_date = chart_df.index[-1].strftime("%d %b %Y")
                            date_range_text = f"📅 {start_date} - {end_date} ({len(chart_df)} candles)"
                        else:
                            date_range_text = ""
                        
                        # Render chart
                        fig = render_chart(chart_df, chart_title)
                        if fig:
                            st.pyplot(fig)
                            st.caption(f"📈 Garis: MA 20 (biru) & MA 50 (orange) | Volume di bawah")
                            if date_range_text:
                                st.caption(date_range_text)
                            plt.close(fig)  # Clean up
                        
                        st.markdown("---")
                    elif not CHART_AVAILABLE:
                        st.warning("📊 Install mplfinance untuk chart: `pip install mplfinance`")
                    
                    # Show insight text
                    st.markdown("### 🤖 AI Analysis")
                    st.markdown(md["insight"])
                    st.success(f"💰 **Harga: Rp {md['price']:,}**")
                    
                    # Show EMA & ATR levels
                    if md.get("ema20", 0) > 0:
                        st.caption(f"📈 EMA20: {md['ema20']:,} | EMA50: {md['ema50']:,}")
                    if md.get("atr", 0) > 0:
                        st.caption(f"📊 ATR: {md['atr']:,} | SL(ATR): {md['sl_atr']:,} | TP(ATR): {md['tp_atr']:,}")
                    
                    # Show Pivot Points
                    if md.get("pivot", 0) > 0:
                        st.info(f"🎯 **Pivot:** S1: {md['s1']:,} | P: {md['pivot']:,} | R1: {md['r1']:,}")
                    
                    # Trend indicator
                    if md["trend_score"] >= 2:
                        st.markdown("🟢 **Trend: STRONG**")
                    elif md["trend_score"] >= 1:
                        st.markdown("🟡 **Trend: MODERATE**")
                    else:
                        st.markdown("🔴 **Trend: WEAK**")
                    
                    # Debug info for auto-checks
                    st.caption(f"🤖 Auto-check: Trend={md.get('is_uptrend', False)} | Vol={md.get('vol_above_avg', False)} | RSI_OK={md.get('rsi_ok', True)}")
        
        # Get data from session state
        if 'market_data' in st.session_state:
            md = st.session_state.market_data
            market_price = md.get("price", 0)
            ema20_price = md.get("ema20", 0)
            ema50_price = md.get("ema50", 0)
            sl_atr_price = md.get("sl_atr", 0)
            tp_atr_price = md.get("tp_atr", 0)
            r1_price = md.get("r1", 0)
            s1_price = md.get("s1", 0)
            # Smart checklist auto-check flags - explicit bool conversion
            auto_checks["is_uptrend"] = bool(md.get("is_uptrend", False))
            auto_checks["vol_above_avg"] = bool(md.get("vol_above_avg", False))
            auto_checks["rsi_ok"] = bool(md.get("rsi_ok", True))
            # Additional flags for different strategies
            auto_checks["is_morning_spike"] = bool(md.get("is_morning_spike", False))
            auto_checks["price_above_vwap"] = bool(md.get("price_above_vwap", False))
            auto_checks["vol_above_5d"] = bool(md.get("vol_above_5d", False))
            
            # Tier 1 Automation Flags
            auto_checks["is_ihsg_uptrend"] = bool(md.get("is_ihsg_uptrend", False))
            auto_checks["is_weekly_uptrend"] = bool(md.get("is_weekly_uptrend", False))
            auto_checks["is_candle_pattern"] = bool(md.get("is_candle_pattern", False))
            auto_checks["pattern_name"] = str(md.get("pattern_name", ""))
        
        # Store auto_checks in session for checklist
        st.session_state.auto_checks = auto_checks
        
        st.markdown("---")
        st.subheader("💰 Modal & Harga")
        
        # Input Modal (dengan auto-save)
        capital = st.number_input(
            "Total Modal (Rp)",
            min_value=0,
            value=st.session_state.user_settings.get("capital", 5_000_000),
            step=500_000,
            format="%d",
            help="Modal tersimpan otomatis",
            key="capital_input"
        )
        
        # Auto-save capital
        if capital != st.session_state.user_settings.get("capital"):
            st.session_state.user_settings["capital"] = capital
            save_user_settings(st.session_state.user_settings)
        
        # Default entry price from market data if available
        default_entry = market_price if market_price > 0 else 500
        
        # Input Harga
        st.markdown("##### 📊 Harga")
        if market_price > 0:
            st.caption(f"💡 Entry dari harga pasar: Rp {market_price:,}")
        
        # Entry Price
        entry_price = st.number_input("Entry", min_value=0, value=default_entry, step=5)
        
        # === STOP LOSS dengan tombol cepat ===
        st.markdown("**Stop Loss**")
        
        # SL suggestion buttons - EMA, ATR, dan S1 (only if below entry)
        # Show label with Support info if available
        if s1_price > 0 and s1_price < entry_price:
            st.caption(f"Support1: Rp {s1_price:,}")
        elif s1_price > 0 and s1_price >= entry_price:
            st.caption(f"⚠️ S1 ({s1_price:,}) > Entry - Harga sudah breakdown support")
        
        has_sl_buttons = ema20_price > 0 or sl_atr_price > 0
        if has_sl_buttons:
            sl_cols = st.columns(4)
            col_idx = 0
            # Only show EMA20 if below entry
            if ema20_price > 0 and ema20_price < entry_price:
                with sl_cols[col_idx]:
                    if st.button("EMA20", key="sl_ema20", help=f"Rp {ema20_price:,}"):
                        st.session_state.sl_value = ema20_price
                col_idx += 1
            # Only show EMA50 if below entry
            if ema50_price > 0 and ema50_price < entry_price:
                with sl_cols[col_idx]:
                    if st.button("EMA50", key="sl_ema50", help=f"Rp {ema50_price:,}"):
                        st.session_state.sl_value = ema50_price
                col_idx += 1
            # ATR is always calculated relative to price, so OK to show
            if sl_atr_price > 0 and sl_atr_price < entry_price:
                with sl_cols[col_idx]:
                    if st.button("ATR", key="sl_atr", help=f"2xATR: Rp {sl_atr_price:,}"):
                        st.session_state.sl_value = sl_atr_price
                col_idx += 1
            # Only show S1 if it's BELOW entry price (valid support for long)
            if s1_price > 0 and s1_price < entry_price:
                with sl_cols[col_idx]:
                    if st.button("S1", key="sl_s1", help=f"Support1: Rp {s1_price:,}"):
                        st.session_state.sl_value = s1_price
        
        # Get SL value from session or calculate default
        if 'sl_value' in st.session_state and st.session_state.sl_value > 0:
            default_sl = st.session_state.sl_value
        else:
            default_sl = int(default_entry * 0.95) if default_entry > 0 else 475
        
        stop_loss = st.number_input("SL", min_value=0, value=default_sl, step=5, label_visibility="collapsed")
        
        # === TAKE PROFIT dengan tombol cepat ===
        st.markdown("**Take Profit**")
        
        # TP suggestion buttons - ATR dan R1 (only if above entry)
        has_tp_buttons = tp_atr_price > 0 or r1_price > 0
        if has_tp_buttons:
            tp_cols = st.columns(3)
            col_idx = 0
            # ATR TP is calculated above price, should be OK
            if tp_atr_price > 0 and tp_atr_price > entry_price:
                with tp_cols[col_idx]:
                    if st.button("ATR", key="tp_atr", help=f"3xATR: Rp {tp_atr_price:,}"):
                        st.session_state.tp_value = tp_atr_price
                col_idx += 1
            # Only show R1 if it's ABOVE entry price (valid resistance target)
            if r1_price > 0 and r1_price > entry_price:
                with tp_cols[col_idx]:
                    if st.button("R1", key="tp_r1", help=f"Resistance1: Rp {r1_price:,}"):
                        st.session_state.tp_value = r1_price
        
        # Get TP value from session or calculate default
        if 'tp_value' in st.session_state and st.session_state.tp_value > 0:
            default_tp = st.session_state.tp_value
        else:
            default_tp = int(default_entry * 1.10) if default_entry > 0 else 550
        
        take_profit = st.number_input("TP", min_value=0, value=default_tp, step=5, label_visibility="collapsed")
        
        st.markdown("---")
        st.subheader("⚠️ Risiko")
        
        # Slider Risiko (dengan profil cepat support)
        default_risk = st.session_state.get("selected_risk", st.session_state.user_settings.get("risk_percent", 1.0))
        risk_percent = st.slider(
            "Max Risiko (%)",
            min_value=0.5,
            max_value=5.0,
            value=default_risk,
            step=0.25
        )
        
        # Auto-save risk
        if risk_percent != st.session_state.user_settings.get("risk_percent"):
            st.session_state.user_settings["risk_percent"] = risk_percent
            save_user_settings(st.session_state.user_settings)
        
        # Fee Broker (hidden by default)
        with st.expander("🏦 Fee Broker"):
            col1, col2 = st.columns(2)
            with col1:
                buy_fee_pct = st.number_input(
                    "Beli (%)", min_value=0.0, max_value=1.0,
                    value=st.session_state.user_settings.get("buy_fee_pct", 0.15),
                    step=0.01, format="%.2f"
                ) / 100
                with col2:
                    sell_fee_pct = st.number_input(
                    "Jual (%)", min_value=0.0, max_value=1.0,
                    value=st.session_state.user_settings.get("sell_fee_pct", 0.25),
                    step=0.01, format="%.2f"
                ) / 100
        
        st.markdown("---")
        
        # === 🌍 FOREIGN FLOW (Manual Input dari OLT) ===
        st.subheader("🌍 Foreign Flow")
        st.caption("Input dari OLT/Stockbit/Sekuritas lo")
        
        foreign_status = st.radio(
            "Posisi Asing Hari Ini:",
            options=["⚪ Netral / Tidak Jelas", "🟢 Net Buy (Akumulasi)", "🔴 Net Sell (Distribusi)"],
            index=0,
            horizontal=True,
            key="foreign_flow_radio"
        )
        
        # Store in session for decision engine
        st.session_state.foreign_status = foreign_status
        
        st.markdown("---")
        st.info(f"📊 Total Trade: **{persistence.get_trade_count()}**")
        st.caption("💾 Setting tersimpan otomatis")
    
    # ==========================================================================
    # INTERFACE UTAMA
    # ==========================================================================
    
    st.title("📊 Jurnal Trading Akbar")
    st.markdown("*Disiplin adalah jembatan antara tujuan dan pencapaian*")
    
    # === TABS NAVIGATION ===
    tab_calc, tab_scanner, tab_journal = st.tabs([
        "🧮 Kalkulator & Analisa", 
        "🔍 Batch Scanner", 
        "📋 Jurnal & Riwayat"
    ])
    
    # ==========================================================================
    # TAB 1: KALKULATOR & ANALISA
    # ==========================================================================
    with tab_calc:
        # Validasi input
        input_valid = True
        validation_errors = []
    
        if not ticker:
            validation_errors.append("Silakan masukkan kode saham")
            input_valid = False
        
        if entry_price <= 0:
            validation_errors.append("Harga entry harus lebih dari 0")
            input_valid = False
        
        if stop_loss >= entry_price:
            validation_errors.append("Stop Loss harus di bawah Harga Entry (untuk posisi long)")
            input_valid = False
        
        if take_profit <= entry_price:
            validation_errors.append("Take Profit harus di atas Harga Entry (untuk posisi long)")
            input_valid = False
        
        if capital <= 0:
            validation_errors.append("Modal harus lebih dari 0")
            input_valid = False
        
        if not input_valid:
            for error in validation_errors:
                st.warning(f"⚠️ {error}")
            st.info("💡 Lengkapi data di sidebar untuk mulai analisa")
            # Stop only this tab's execution - other tabs still work because they have separate with blocks
        else:
            # Buat setup trade
            trade = TradeSetup(
                ticker=ticker,
                capital=capital,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_percent=risk_percent,
                buy_fee_pct=buy_fee_pct,
                sell_fee_pct=sell_fee_pct
            )
            
            # Hitung metrik
            max_lots = trade.calculate_max_lots()
            total_shares = max_lots * LOT_SIZE
            position_value = trade.calculate_position_value(max_lots)
            buy_fee = trade.calculate_buy_fee(max_lots)
            total_cost = trade.calculate_total_buy_cost(max_lots)
            potential_profit = trade.calculate_potential_profit(max_lots)
            potential_loss = trade.calculate_potential_loss(max_lots)
            rrr = trade.rrr
            rrr_status, rrr_color = get_rrr_status(rrr)
        
            # ==========================================================================
            # DASHBOARD METRIK UTAMA
            # ==========================================================================
            
            st.markdown("## 📈 Analisis Sniper")
        
            # Baris pertama - Metrik utama
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="🎯 Max Lot",
                    value=f"{max_lots:,}",
                    delta=f"{total_shares:,} lembar"
                )
            
            with col2:
                st.metric(
                    label="📊 RRR",
                    value=f"1:{rrr:.2f}",
                    delta=rrr_status,
                    delta_color="normal" if rrr >= MIN_RRR_THRESHOLD else "inverse"
                )
            
            with col3:
                st.metric(
                    label="💰 Nilai Posisi",
                    value=format_currency(position_value, compact=True),
                    delta=f"Fee: {format_currency(buy_fee, compact=True)}"
                )
            
            with col4:
                st.metric(
                    label="💵 Total Biaya",
                    value=format_currency(total_cost, compact=True),
                    delta=f"{(total_cost/capital*100):.1f}% Modal"
                )
            
            st.markdown("---")
    
            # Baris kedua - Proyeksi PnL
            st.markdown("### 💹 Proyeksi Profit/Loss Bersih")
    
            col1, col2, col3 = st.columns(3)
    
            with col1:
                profit_pct = (potential_profit / capital * 100) if capital > 0 else 0
                st.markdown(f"""
                <style>
                .proyeksi-text {{
                    color: #ffffff !important;
                    text-shadow: 0px 1px 3px rgba(0,0,0,0.8) !important;
                    font-family: sans-serif !important;
                }}
                </style>
                <div style="background-color: #2E7D32; 
                            padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #43A047;">
                    <div class="proyeksi-text" style="margin: 0; font-size: 1.0rem; font-weight: 600;">🚀 Profit</div>
                    <div class="proyeksi-text" style="margin: 8px 0; font-size: 1.4rem; font-weight: 700;">{format_currency(potential_profit, compact=True)}</div>
                    <div class="proyeksi-text" style="margin: 0; font-size: 0.9rem; font-weight: 500;">+{profit_pct:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
    
            with col2:
                loss_pct = (potential_loss / capital * 100) if capital > 0 else 0
                st.markdown(f"""
                <div style="background-color: #C62828; 
                        padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #E57373;">
                <div class="proyeksi-text" style="margin: 0; font-size: 1.0rem; font-weight: 600;">📉 Loss</div>
                <div class="proyeksi-text" style="margin: 8px 0; font-size: 1.4rem; font-weight: 700;">{format_currency(potential_loss, compact=True)}</div>
                <div class="proyeksi-text" style="margin: 0; font-size: 0.9rem; font-weight: 500;">-{loss_pct:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
    
            with col3:
                net_expected = potential_profit - potential_loss
                net_color = "#00b894" if net_expected > 0 else "#d63031"
                st.markdown(f"""
                <div style="background-color: #4527A0; 
                        padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #7E57C2;">
                <div class="proyeksi-text" style="margin: 0; font-size: 1.0rem; font-weight: 600;">⚖️ Risiko</div>
                <div class="proyeksi-text" style="margin: 8px 0; font-size: 1.4rem; font-weight: 700;">{format_currency(trade.max_risk_amount, compact=True)}</div>
                <div class="proyeksi-text" style="margin: 0; font-size: 0.9rem; font-weight: 500;">{risk_percent:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
    
            # Peringatan RRR
            if rrr < MIN_RRR_THRESHOLD:
                st.markdown(f"""
                <div class="warning-box">
                    <h4 style="color: #e74c3c; margin: 0;">⚠️ Peringatan Risk/Reward Jelek</h4>
                    <p style="color: #ccc; margin: 5px 0 0 0;">
                        RRR adalah 1:{rrr:.2f} yang di bawah threshold minimum 1:{MIN_RRR_THRESHOLD}. 
                        Pertimbangkan untuk menyesuaikan level TP/SL Anda.
                    </p>
                </div>
            """, unsafe_allow_html=True)
    
            st.markdown("---")
    
            # ==========================================================================
            # SMART CHECKLIST VALIDASI (Auto-check technical items)
            # ==========================================================================
    
            st.markdown("## ✅ Smart Checklist Pra-Trade")
            st.markdown("*Item teknikal otomatis dicentang berdasarkan data market*")
    
            # Get auto-check flags from session
            auto_checks = st.session_state.get("auto_checks", {
            "is_uptrend": False,
            "vol_above_avg": False,
            "rsi_ok": True
            })
    
            # Get strategy mode from session
            is_scalping_mode = st.session_state.get("is_scalping_mode", False)
            is_minibandar_mode = st.session_state.get("is_minibandar_mode", False)
            current_mode = st.session_state.get("strategy_mode", "📈 Swing/Normal (EMA-based)")
    
            # === STRATEGY-BASED CHECKLIST LOGIC (Bypass) ===
    
            # Struktur Pasar - changes based on strategy mode
            if is_scalping_mode:
                # Scalper: Use Open=Low instead of EMA20
                structure_val = auto_checks.get("is_morning_spike", False)
                structure_label = "⚡ **Struktur Scalping** - Open=Low Valid (HAKA Setup)"
            elif is_minibandar_mode:
                # Mini-Bandar: Use VWAP
                structure_val = auto_checks.get("price_above_vwap", False)
                structure_label = "🐋 **Struktur Flow** - Harga > VWAP (Bandar Jaga Harga)"
            else:
                # Normal/Swing: Use EMA20
                structure_val = auto_checks.get("is_uptrend", False)
                structure_label = "📊 **Struktur Pasar** - Trend bullish (Harga > EMA20)"
    
            # Volume - also changes based on strategy
            if is_minibandar_mode:
                # Mini-Bandar: Use 5-day volume (short-term flow)
                volume_val = auto_checks.get("vol_above_5d", False)
                volume_label = "📉 **Volume Flow** - Volume > Rata-rata 5 Hari"
            else:
                # Normal: Use 20-day volume
                volume_val = auto_checks.get("vol_above_avg", False)
                volume_label = "📉 **Konfirmasi Volume** - Volume di atas rata-rata"
    
            # Define checklist items - some auto-checked, some manual
            # Format: (key, label, is_auto, auto_value)
            
            # Auto-check Risk (RRR >= Threshold)
            risk_ok = rrr >= MIN_RRR_THRESHOLD
            
            checklist_config = [
                # Technical items - AUTO-CHECKED (Strategy-based)
                ("structure", structure_label, True, structure_val),
                ("volume", volume_label, True, volume_val),
                ("timing", "⏰ **Timing** - RSI tidak overbought (<70)", True, auto_checks.get("rsi_ok", True)),
                
                # Risk & Plan - NOW AUTO-CHECKED
                ("risk", f"💰 **Risk Management** - RRR >= 1:{MIN_RRR_THRESHOLD} ({'OK' if risk_ok else 'Kurang'})", True, risk_ok),
                ("plan", "📝 **Rencana Trade** - Entry, SL, TP sudah valid", True, True),
                
                # Tier 1 Automation (Tier 1)
                ("candle", f"🕯️ **Pattern Candle** - {auto_checks.get('pattern_name', 'None') if auto_checks.get('is_candle_pattern') else 'Tidak ada pattern valid'}", True, auto_checks.get("is_candle_pattern", False)),
                ("sragam", "🎨 **Keseragaman** - Timeframe D1 & W1 Selaras (Uptrend)", True, auto_checks.get("is_weekly_uptrend", False)),
                ("sentiment", f"📰 **Sentimen Pasar** - IHSG Kondisi {'Bullish' if auto_checks.get('is_ihsg_uptrend') else 'Bearish/Weak'}", True, auto_checks.get("is_ihsg_uptrend", False)),

                # Manual items (Subjective) - Tier 2
                ("bidoffer", "📈 **Aliran Bid/Offer** - Tekanan beli kuat di order book", False, False),
                ("broker_sum", "🏦 **Broker Summary** - Broker kunci sedang akumulasi", False, False),
                ("news", "📢 **Cek Berita** - Tidak ada aksi korporasi negatif", False, False),
            ]
    
            # Show mode indicator and auto-check legend
            st.info(f"🎮 **Mode: {current_mode}** — Item teknikal otomatis sesuai strategi")
    
            col1, col2 = st.columns(2)
            checked_items = 0
    
            mid_point = len(checklist_config) // 2
    
            with col1:
                for key, label, is_auto, auto_value in checklist_config[:mid_point]:
                    if is_auto:
                        # Auto-checked items - show as styled text (disabled checkboxes don't work in Streamlit)
                        if auto_value:
                            st.markdown(f"✅ 🔒 {label}")
                            checked_items += 1
                        else:
                            st.markdown(f"❌ {label}")
                    else:
                        # Manual items - user can check
                        if st.checkbox(label, key=key):
                            checked_items += 1
    
            with col2:
                for key, label, is_auto, auto_value in checklist_config[mid_point:]:
                    if is_auto:
                        # Auto-checked items - show as styled text
                        if auto_value:
                            st.markdown(f"✅ 🔒 {label}")
                            checked_items += 1
                        else:
                            st.markdown(f"❌ {label}")
                    else:
                        # Manual items
                        if st.checkbox(label, key=key):
                            checked_items += 1
    
            checklist_score = checked_items
            total_items = len(checklist_config)
            checklist_perfect = checklist_score == total_items
            checklist_percentage = (checklist_score / total_items) * 100
    
            # Progress checklist
            st.progress(checklist_percentage / 100)
            auto_count = sum(1 for _, _, is_auto, val in checklist_config if is_auto and val)
            manual_count = checked_items - auto_count
            st.markdown(f"**Skor: {checklist_score}/{total_items} ({checklist_percentage:.0f}%)** — 🤖 Auto: {auto_count} | ✋ Manual: {manual_count}")
    
            st.markdown("---")
    
            # ==========================================================================
            # MESIN KEPUTUSAN (dengan Foreign Flow Integration)
            # ==========================================================================
    
            st.markdown("## 🎯 Keputusan Trade")
    
            # Get foreign status from session
            foreign_status = st.session_state.get("foreign_status", "⚪ Netral / Tidak Jelas")
    
            # Calculate foreign score modifier
            foreign_score = 0
            foreign_msg = ""
            foreign_warning = False
    
            if "Net Buy" in foreign_status:
                foreign_score = 1
                foreign_msg = "🌍 Asing: Net Buy (Support)"
            elif "Net Sell" in foreign_status:
                foreign_score = -2  # Penalty lebih berat
                foreign_msg = "⚠️ Asing: Net Sell (Rawan Guyur!)"
                foreign_warning = True
            else:
                foreign_msg = "🌍 Asing: Netral"
    
            # Display Foreign Flow status
            if "Net Buy" in foreign_status:
                st.success(f"🟢 {foreign_msg}")
            elif "Net Sell" in foreign_status:
                st.error(f"🔴 {foreign_msg}")
            else:
                st.info(f"⚪ {foreign_msg}")
    
            rrr_good = rrr >= MIN_RRR_THRESHOLD
    
            # Adjusted final score with foreign
            final_score = checklist_score + foreign_score
    
            # Decision Logic with Foreign Flow
            if rrr_good and checklist_perfect and not foreign_warning:
                decision = "STRONG BUY"
                st.markdown("""
                <div class="strong-buy">
                    🚀 STRONG BUY - SIAP EKSEKUSI! 🚀
                </div>
                """, unsafe_allow_html=True)
                st.success(f"""
                ✅ **Setup Trade Tervalidasi:**
                - RRR: 1:{rrr:.2f} (Bagus)
                - Checklist: {checklist_score}/{total_items} (Sempurna)
                - Foreign: {foreign_msg}
                - Max Posisi: {max_lots} Lot @ {format_currency(entry_price)}
                - Jumlah Risiko: {format_currency(trade.max_risk_amount)}
                """)
            elif rrr_good and checklist_perfect and foreign_warning:
                # Teknikal bagus TAPI asing jualan - BAHAYA!
                decision = "BAHAYA"
                st.markdown("""
                <div class="caution">
                    ☔ BAHAYA - RAWAN BULL TRAP! ☔
                </div>
                """, unsafe_allow_html=True)
                st.error(f"""
                ⚠️ **Teknikal Oke, Tapi Asing Jualan!**
                - RRR: 1:{rrr:.2f} (Bagus)
                - Checklist: {checklist_score}/{total_items} (Sempurna)
                - 🔴 **{foreign_msg}** ← PROBLEM!
            
                **Saran:** Kurangi lot setengah, atau tunggu asing stop jualan.
                """)
            elif rrr_good and checklist_percentage >= 75:
                decision = "HATI-HATI"
                st.markdown("""
                <div class="caution">
                    ⚠️ LANJUTKAN DENGAN HATI-HATI ⚠️
                </div>
                """, unsafe_allow_html=True)
                st.warning(f"""
                ⚠️ **Setup Trade Sebagian Valid:**
                - RRR: 1:{rrr:.2f} (Bagus)
                - Checklist: {checklist_score}/{total_items} (Belum Lengkap)
                - Foreign: {foreign_msg}
                - Review item yang belum dicentang sebelum lanjut
                """)
            else:
                decision = "JANGAN TRADE"
                st.markdown("""
                <div class="no-trade">
                    🛑 JANGAN TRADE - TUNGGU DULU 🛑
                </div>
                """, unsafe_allow_html=True)
        
            reasons = []
            if not rrr_good:
                reasons.append(f"- RRR: 1:{rrr:.2f} (Di bawah minimum 1:{MIN_RRR_THRESHOLD})")
            if not checklist_perfect:
                reasons.append(f"- Checklist: {checklist_score}/{total_items} (Belum Lengkap)")
            if foreign_warning:
                reasons.append(f"- 🔴 Asing Net Sell (Distribusi)")
        
            st.error(f"""
            ❌ **Setup Trade Tidak Valid:**
            {chr(10).join(reasons)}
        
            Tunggu setup yang lebih baik!
            """)
    
            st.markdown("---")
    
            # ==========================================================================
            # LOGGING TRADE
            # ==========================================================================
    
            st.markdown("## 📝 Catat Trade Ini")
    
            col1, col2 = st.columns([3, 1])
    
            with col1:
                notes = st.text_area(
                "Catatan Trade (opsional)",
                placeholder="Tambahkan catatan tentang setup trade ini...",
                height=100
                )
    
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Simpan ke Jurnal", use_container_width=True, type="primary"):
                    record = TradeRecord(
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ticker=ticker,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        lots=max_lots,
                        capital=capital,
                        risk_percent=risk_percent,
                        rrr=rrr,
                        potential_profit=potential_profit,
                        potential_loss=potential_loss,
                        checklist_score=checklist_score,
                        decision=decision,
                        notes=notes
                    )
                
                    if persistence.save_trade(record):
                        st.success("✅ Trade berhasil dicatat!")
                        st.balloons()
                    else:
                        st.error("❌ Gagal menyimpan trade")
    
            # ==========================================================================
            # RIWAYAT JURNAL
            # ==========================================================================
    
            with st.expander("📚 Lihat Riwayat Jurnal Trading"):
                df = persistence.load_trades()
                if not df.empty:
                    # Tampilkan trade terbaru
                    st.dataframe(
                        df.sort_values('timestamp', ascending=False).head(20),
                        use_container_width=True,
                        hide_index=True
                    )
            
                    # Tombol download
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Jurnal Lengkap (CSV)",
                        data=csv,
                        file_name=f"jurnal_trading_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Belum ada trade tercatat. Mulai catat trade Anda!")
    
            # ==========================================================================
            # RINGKASAN TRADE (Expandable)
            # ==========================================================================
    
            with st.expander("📋 Ringkasan Trade Lengkap"):
                st.markdown(f"""
                ### Ringkasan Setup Trade untuk {ticker}
            
                | Parameter | Nilai |
                |-----------|-------|
                | Harga Entry | {format_currency(entry_price)} |
                | Stop Loss | {format_currency(stop_loss)} |
                | Take Profit | {format_currency(take_profit)} |
                | Risiko per Lembar | {format_currency(trade.risk_per_share)} |
                | Reward per Lembar | {format_currency(trade.reward_per_share)} |
                | Risk-Reward Ratio | 1:{rrr:.2f} |
                | Jumlah Risiko Max | {format_currency(trade.max_risk_amount)} |
                | Max Lot | {max_lots:,} ({total_shares:,} lembar) |
                | Nilai Posisi | {format_currency(position_value)} |
                | Fee Beli ({buy_fee_pct*100:.2f}%) | {format_currency(buy_fee)} |
                | Total Biaya | {format_currency(total_cost)} |
                | Penggunaan Modal | {(total_cost/capital*100):.2f}% |
                | Potensi Profit (Bersih) | {format_currency(potential_profit)} |
                | Potensi Loss (Bersih) | {format_currency(potential_loss)} |
                | Skor Checklist | {checklist_score}/{total_items} |
                | Keputusan | **{decision}** |
                """)
    
    # ==========================================================================
    # TAB 2: BATCH SCANNER
    # ==========================================================================
    with tab_scanner:
        st.markdown("## 🔍 Batch Scanner (Stockbit Integrator)")
        st.caption("Paste kode saham dari screener Stockbit/RTI untuk scan massal")
    
        # Scanner mode selector
        scanner_col1, scanner_col2 = st.columns([1, 1])
        with scanner_col1:
            scanner_mode = st.radio(
                "Pilih Mode Scanner:",
                ["💎 GEM (Swing DN)", "🐉 Dragon (Momentum)", "🎯 Day Trade (DN)"],
                horizontal=True,
                key="scanner_mode_radio"
            )
        
        with scanner_col2:
            if "GEM" in scanner_mode:
                st.markdown("""
                **💎 GEM Logic:**
                - Uptrend (Harga > EMA20)
                - Konsolidasi (-3% s/d +2%)
                """)
            elif "Dragon" in scanner_mode:
                st.markdown("""
                **🐉 Dragon Logic:**
                - Volume > 1.5x rata-rata
                - Change > +2%
                """)
            else:
                st.markdown("""
                **🎯 Day Trade Logic:**
                - Change +2% s/d +10%
                - Likuiditas > 5 Miliar
                - Volume > 1.2x rata-rata
                """)
        
        # Ticker input
        ticker_input = st.text_area(
            "Paste Kode Saham (pisahkan dengan koma, enter, atau titik koma):",
            placeholder="BBRI, TLKM, ASII, BMRI\natau\nBBRI\nTLKM\nASII\nBMRI",
            height=100,
            key="batch_ticker_input"
        )
        
        # Scan button
        scan_col1, scan_col2 = st.columns([1, 3])
        with scan_col1:
            scan_button = st.button("🚀 Mulai Scan", use_container_width=True, type="primary")
        with scan_col2:
            if ticker_input:
                tickers = parse_ticker_input(ticker_input)
                st.caption(f"📊 {len(tickers)} ticker akan di-scan")
    
        # Run scan
        if scan_button and ticker_input:
            tickers = parse_ticker_input(ticker_input)
            
            if tickers:
                # Determine scan type
                if "GEM" in scanner_mode:
                    scan_type = "gem"
                elif "Dragon" in scanner_mode:
                    scan_type = "dragon"
                else:
                    scan_type = "daytrade"
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Run batch scan
                results = []
                for i, ticker in enumerate(tickers):
                    status_text.text(f"Scanning {ticker}... ({i+1}/{len(tickers)})")
                    
                    if scan_type == "gem":
                        result = scan_gem(ticker)
                    elif scan_type == "dragon":
                        result = scan_dragon(ticker)
                    else:
                        result = scan_daytrade(ticker)
                    
                    results.append(result)
                    progress_bar.progress((i + 1) / len(tickers))
                    
                    # Rate limiting
                    if i < len(tickers) - 1:
                        time.sleep(0.3)
                
                status_text.empty()
                progress_bar.empty()
                
                # Store results in session
                st.session_state.scan_results = results
                st.session_state.scan_type = scan_type
            else:
                st.warning("Masukkan minimal 1 kode saham.")
        
        # Display results
        if 'scan_results' in st.session_state and st.session_state.scan_results:
            results = st.session_state.scan_results
            scan_type = st.session_state.get('scan_type', 'gem')
            
            # Count matches
            if scan_type == "gem":
                matches = [r for r in results if r.get('is_gem', False)]
                match_label = "💎 GEM"
            elif scan_type == "dragon":
                matches = [r for r in results if r.get('is_dragon', False)]
                match_label = "🐉 DRAGON"
            else:
                matches = [r for r in results if r.get('is_daytrade', False)]
                match_label = "🎯 DAYTRADE"
            
            st.success(f"✅ Scan selesai: **{len(matches)}/{len(results)}** saham lolos filter {match_label}")
            
            # Results table
            st.markdown("### 📊 Hasil Scan")
            
            # Sort: matches first
            sorted_results = sorted(results, key=lambda x: x.get('status', '') != '❌', reverse=True)
            
            # Create DataFrame for display
            table_data = []
            for r in sorted_results:
                if r.get('status') == 'error':
                    continue
                
                row = {
                    "Ticker": r.get('ticker', ''),
                    "Harga": f"Rp {r.get('price', 0):,}",
                    "Change": f"{r.get('change_pct', 0):+.1f}%",
                    "Vol (x)": f"{r.get('vol_ratio', 0):.1f}x",
                }
                
                # Add Liquidity column for Day Trade mode
                if scan_type == "daytrade":
                    row["Liq (B)"] = f"{r.get('liquidity_b', 0):.1f}B"
                
                row["Status"] = r.get('status', '')
                row["Alasan"] = r.get('reason', '')
                
                table_data.append(row)
            
            if table_data:
                df_results = pd.DataFrame(table_data)
                st.dataframe(df_results, use_container_width=True, hide_index=True)
                
                # Quick select buttons for matched tickers
                if matches:
                    st.markdown("### 🎯 Quick Analyze")
                    st.caption("Klik untuk analisa detail:")
                    
                    match_cols = st.columns(min(len(matches), 5))
                    for i, match in enumerate(matches[:5]):
                        with match_cols[i]:
                            if st.button(f"📊 {match['ticker']}", key=f"analyze_{match['ticker']}"):
                                st.session_state.selected_ticker = match['ticker']
                                st.rerun()
            
            # Clear results button
            if st.button("🗑️ Clear Results"):
                del st.session_state.scan_results
                if 'scan_type' in st.session_state:
                    del st.session_state.scan_type
                st.rerun()
    
    # ==========================================================================
    # TAB 3: JURNAL & RIWAYAT
    # ==========================================================================
    with tab_journal:
        st.markdown("## 📋 Jurnal Trade & Riwayat")
        st.caption("Lihat riwayat trade yang sudah dicatat")
        
        # Load journal data
        journal_df = persistence.load_trades()
        
        if not journal_df.empty:
            # === ANALYTICS DASHBOARD ===
            render_analytics_dashboard(journal_df)
            
            st.markdown("---")
            
            # === PARTIAL EXIT CALCULATOR ===
            with st.expander("🧮 Kalkulator Average Exit (Partial Take Profit)"):
                st.caption("Gunakan ini untuk menghitung rata-rata harga jual jika Anda TP bertahap.")
                
                col_calc1, col_calc2 = st.columns(2)
                with col_calc1:
                    calc_entry = st.number_input("Harga Entry (Opsional)", min_value=0, step=5, help="Untuk estimasi PnL")
                
                # Dynamic inputs
                exits = []
                cols = st.columns(4)
                with cols[0]:
                    e1_p = st.number_input("Exit 1 Price", min_value=0, step=5, key="e1p")
                    e1_l = st.number_input("Exit 1 Lot", min_value=0, step=1, key="e1l")
                    if e1_p > 0 and e1_l > 0: exits.append((e1_p, e1_l))
                with cols[1]:
                    e2_p = st.number_input("Exit 2 Price", min_value=0, step=5, key="e2p")
                    e2_l = st.number_input("Exit 2 Lot", min_value=0, step=1, key="e2l")
                    if e2_p > 0 and e2_l > 0: exits.append((e2_p, e2_l))
                with cols[2]:
                    e3_p = st.number_input("Exit 3 Price", min_value=0, step=5, key="e3p")
                    e3_l = st.number_input("Exit 3 Lot", min_value=0, step=1, key="e3l")
                    if e3_p > 0 and e3_l > 0: exits.append((e3_p, e3_l))
                with cols[3]:
                    e4_p = st.number_input("Exit 4 Price", min_value=0, step=5, key="e4p")
                    e4_l = st.number_input("Exit 4 Lot", min_value=0, step=1, key="e4l")
                    if e4_p > 0 and e4_l > 0: exits.append((e4_p, e4_l))
                
                if exits:
                    total_lot = sum(x[1] for x in exits)
                    total_val = sum(x[0] * x[1] for x in exits)
                    avg_price = total_val / total_lot if total_lot > 0 else 0
                    
                    st.info(f"💵 **Average Exit Price: {avg_price:,.0f}** (Total Lot: {total_lot})")
                    
                    if calc_entry > 0:
                        gross_pnl = (avg_price - calc_entry) * total_lot * 100
                        pnl_color = "green" if gross_pnl > 0 else "red"
                        st.markdown(f"**Est. Gross PnL:** :{pnl_color}[{format_currency(gross_pnl)}]")
                        st.caption("Masukkan 'Average Exit Price' ke kolom Exit di tabel jurnal.")

            st.markdown("---")

            # Trade history table with editing capability
            st.markdown("### 📜 Riwayat Trade (Edit untuk Update)")
            
            edited_journal_df = st.data_editor(
                journal_df,
                column_order=["timestamp", "ticker", "entry_price", "lots", "exit_price", "status", "realized_pnl", "notes"],
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Waktu", disabled=True),
                    "ticker": st.column_config.TextColumn("Saham", disabled=True),
                    "entry_price": st.column_config.NumberColumn("Entry", format="Rp %d", disabled=True),
                    "lots": st.column_config.NumberColumn("Lot", disabled=True),
                    "exit_price": st.column_config.NumberColumn("Exit (Jual)", format="Rp %d", required=True),
                    "status": st.column_config.SelectboxColumn(
                        "Status", 
                        options=["OPEN", "WIN", "LOSS", "BEP"],
                        required=True,
                        width="small"
                    ),
                    "notes": st.column_config.TextColumn("Catatan", width="medium"),
                    "realized_pnl": st.column_config.NumberColumn("Realized PnL", format="Rp %d", disabled=True),
                },
                hide_index=True,
                use_container_width=True,
                key="journal_editor"
            )

            # Detect changes and update PnL
            if not edited_journal_df.equals(journal_df):
                has_updates = False
                for index, row in edited_journal_df.iterrows():
                    # Calculate PnL if Exit Price is set
                    current_exit = row['exit_price']
                    current_status = row['status']
                    current_pnl = row['realized_pnl']
                    
                    if current_exit > 0:
                        # Auto-calculate PnL: (Exit - Entry) * Lots * 100
                        new_pnl = (current_exit - row['entry_price']) * row['lots'] * 100
                        
                        # Auto-update status if it matches PnL logic (optional helper)
                        if current_status == "OPEN":
                            if new_pnl > 0: current_status = "WIN"
                            elif new_pnl < 0: current_status = "LOSS"
                            else: current_status = "BEP"
                        
                        # Apply update if different
                        if abs(new_pnl - current_pnl) > 1 or row['status'] != current_status:
                            edited_journal_df.at[index, 'realized_pnl'] = new_pnl
                            edited_journal_df.at[index, 'status'] = current_status
                            has_updates = True
                
                # Save if PnL/Status updated or if user just edited other fields (which are already in edited_journal_df)
                # But if we updated PnL, we need to save the versions with PnL
                if persistence.save_all_trades(edited_journal_df):
                    st.success("✅ Jurnal diperbarui: PnL dihitung otomatis!")
                    st.rerun()
            
            # Download button
            csv = journal_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Jurnal (CSV)",
                data=csv,
                file_name=f"jurnal_trading_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📝 Belum ada trade tercatat. Mulai catat trade Anda di tab Kalkulator!")


if __name__ == "__main__":
    main()
