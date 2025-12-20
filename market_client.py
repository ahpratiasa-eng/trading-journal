import streamlit as st
import pandas as pd
import time
from utils import calculate_ema, calculate_rsi, calculate_atr, calculate_pivot_points, calculate_obv, calculate_vwap

try:
    import yfinance as yf
    MARKET_INTEL_AVAILABLE = True
except ImportError:
    MARKET_INTEL_AVAILABLE = False

def detect_sleeping_dragon(df, sideways_days=20, vol_multiplier=2.0):
    """
    🐉 Sleeping Dragon Detector
    Deteksi saham sideways yang tiba-tiba ada volume spike (potensi mark-up).
    """
    if len(df) < sideways_days:
        return False, 0, 0
    
    # Cek range harga 20 hari terakhir (sideways = range sempit)
    recent = df.iloc[-sideways_days:]
    price_range = (recent['High'].max() - recent['Low'].min()) / recent['Close'].mean() * 100
    is_sideways = price_range < 15  # Range < 15% = sideways
    
    # Cek volume spike hari ini
    avg_vol = df['Volume'].iloc[-sideways_days:-1].mean()
    today_vol = df['Volume'].iloc[-1]
    vol_spike = today_vol > (avg_vol * vol_multiplier)
    
    is_dragon = is_sideways and vol_spike
    return is_dragon, price_range, (today_vol / avg_vol if avg_vol > 0 else 0)


def detect_obv_divergence(df, lookback=20):
    """
    🕵️ OBV Divergence Detector
    Harga sideways tapi OBV naik = Akumulasi diam-diam (Smart Money).
    """
    if len(df) < lookback:
        return False, "N/A"
    
    recent = df.iloc[-lookback:]
    
    # Trend harga (pakai close pertama vs terakhir)
    price_change = (recent['Close'].iloc[-1] - recent['Close'].iloc[0]) / recent['Close'].iloc[0] * 100
    
    # Trend OBV
    obv = calculate_obv(recent)
    obv_change = (obv.iloc[-1] - obv.iloc[0])
    
    # Divergence: Harga flat/turun tapi OBV naik
    if abs(price_change) < 5 and obv_change > 0:  # Harga bergerak < 5%
        return True, "🕵️ AKUMULASI TERSEMBUNYI"
    elif price_change < -5 and obv_change > 0:
        return True, "🕵️ BULLISH DIVERGENCE"
    elif price_change > 5 and obv_change < 0:
        return True, "⚠️ BEARISH DIVERGENCE (Distribusi)"
    else:
        return False, "Normal"


def detect_morning_spike(df):
    """
    ⚡ Morning Spike Detector (Open = Low pattern)
    HAKA setup: Harga buka = harga terendah (strong buyer dari awal).
    """
    if len(df) < 1:
        return False, 0
    
    today = df.iloc[-1]
    open_price = float(today['Open'])
    low_price = float(today['Low'])
    high_price = float(today['High'])
    
    # Open = Low (dengan toleransi 0.5%)
    is_open_low = (open_price - low_price) / open_price * 100 < 0.5
    
    # High volatility (range > 2%)
    daily_range = (high_price - low_price) / low_price * 100
    is_high_vol = daily_range > 2
    
    return (is_open_low and is_high_vol), daily_range


def parse_ticker_input(text: str) -> list:
    """Parse comma or newline separated tickers."""
    if not text or not text.strip():
        return []
    
    # Replace newlines with commas, then split
    text = text.replace('\n', ',').replace(';', ',')
    tickers = [t.strip().upper() for t in text.split(',') if t.strip()]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tickers = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            unique_tickers.append(t)
    
    return unique_tickers[:50]  # Limit to 50 tickers


def scan_gem(ticker: str) -> dict:
    """
    💎 GEM Scanner (David Noah Swing Style)
    Cari saham UPTREND yang lagi KONSOLIDASI.
    """
    try:
        symbol = f"{ticker}.JK"
        df = yf.download(symbol, period="1mo", interval="1d", progress=False)
        
        if df.empty or len(df) < 5:
            return {"ticker": ticker, "status": "error", "reason": "Data tidak tersedia"}
        
        # Flatten multi-index if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        last_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        ema20 = float(calculate_ema(df['Close'], 20).iloc[-1])
        
        # Calculate volume ratio
        avg_vol = float(df['Volume'].iloc[-21:-1].mean()) if len(df) > 20 else float(df['Volume'].mean())
        today_vol = float(df['Volume'].iloc[-1])
        vol_ratio = today_vol / avg_vol if avg_vol > 0 else 0
        
        # Condition 1: Uptrend
        is_uptrend = last_close > ema20
        
        # Condition 2: Konsolidasi (-3% to +2%)
        change_pct = ((last_close - prev_close) / prev_close) * 100
        is_consolidating = -3 <= change_pct <= 2
        
        is_gem = is_uptrend and is_consolidating
        
        return {
            "ticker": ticker,
            "price": int(last_close),
            "ema20": int(ema20),
            "change_pct": change_pct,
            "vol_ratio": vol_ratio,
            "is_gem": is_gem,
            "status": "💎 GEM" if is_gem else "❌",
            "reason": "Uptrend + Konsolidasi" if is_gem else (
                "Bukan uptrend" if not is_uptrend else "Tidak konsolidasi"
            )
        }
    except Exception as e:
        return {"ticker": ticker, "status": "error", "reason": str(e)[:30]}


def scan_dragon(ticker: str) -> dict:
    """
    🐉 Dragon Scanner (Momentum/Scalper Style)
    Cari saham dengan VOLUME EXPLOSION dan PRICE SURGE.
    """
    try:
        symbol = f"{ticker}.JK"
        df = yf.download(symbol, period="1mo", interval="1d", progress=False)
        
        if df.empty or len(df) < 5:
            return {"ticker": ticker, "status": "error", "reason": "Data tidak tersedia"}
        
        # Flatten multi-index if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        last_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        
        # Volume analysis
        avg_vol = float(df['Volume'].iloc[-21:-1].mean()) if len(df) > 20 else float(df['Volume'].mean())
        today_vol = float(df['Volume'].iloc[-1])
        vol_ratio = today_vol / avg_vol if avg_vol > 0 else 0
        
        # Price change
        change_pct = ((last_close - prev_close) / prev_close) * 100
        
        # Conditions
        is_volume_spike = vol_ratio > 1.5
        is_price_surge = change_pct > 2
        
        is_dragon = is_volume_spike and is_price_surge
        
        return {
            "ticker": ticker,
            "price": int(last_close),
            "change_pct": change_pct,
            "vol_ratio": vol_ratio,
            "is_dragon": is_dragon,
            "status": "🐉 DRAGON" if is_dragon else "❌",
            "reason": f"Vol {vol_ratio:.1f}x + {change_pct:+.1f}%" if is_dragon else (
                f"Vol {vol_ratio:.1f}x (min 1.5x)" if not is_volume_spike else f"Change {change_pct:+.1f}% (min +2%)"
            )
        }
    except Exception as e:
        return {"ticker": ticker, "status": "error", "reason": str(e)[:30]}


def scan_daytrade(ticker: str) -> dict:
    """
    🎯 Day Trade Scanner (David Noah Day Trade Style)
    Cari saham aktif dengan likuiditas tinggi untuk day trading.
    """
    try:
        symbol = f"{ticker}.JK"
        df = yf.download(symbol, period="1mo", interval="1d", progress=False)
        
        if df.empty or len(df) < 5:
            return {"ticker": ticker, "status": "error", "reason": "Data tidak tersedia"}
        
        # Flatten multi-index if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        last_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        today_vol = float(df['Volume'].iloc[-1])
        
        # Volume analysis
        avg_vol = float(df['Volume'].iloc[-21:-1].mean()) if len(df) > 20 else float(df['Volume'].mean())
        vol_ratio = today_vol / avg_vol if avg_vol > 0 else 0
        
        # Price change
        change_pct = ((last_close - prev_close) / prev_close) * 100
        
        # Liquidity (Transaction Value in IDR)
        liquidity = last_close * today_vol
        liquidity_billion = liquidity / 1_000_000_000  # Convert to Billion
        
        # === DAY TRADE CONDITIONS ===
        
        # Condition 1: Active price movement (+2% to +10%)
        is_active = 2 <= change_pct <= 10
        
        # Condition 2: High liquidity (> 5 Billion IDR)
        is_liquid = liquidity_billion > 5
        
        # Condition 3: Volume spike (> 1.2x average)
        is_vol_valid = vol_ratio > 1.2
        
        # All conditions must be met
        is_daytrade = is_active and is_liquid and is_vol_valid
        
        # Build reason string
        if is_daytrade:
            reason = f"✅ {change_pct:+.1f}% | {liquidity_billion:.1f}B | Vol {vol_ratio:.1f}x"
        else:
            issues = []
            if not is_active:
                if change_pct < 2:
                    issues.append(f"Change {change_pct:+.1f}% (min +2%)")
                else:
                    issues.append(f"Change {change_pct:+.1f}% (max +10%)")
            if not is_liquid:
                issues.append(f"Liq {liquidity_billion:.1f}B (min 5B)")
            if not is_vol_valid:
                issues.append(f"Vol {vol_ratio:.1f}x (min 1.2x)")
            reason = " | ".join(issues)
        
        return {
            "ticker": ticker,
            "price": int(last_close),
            "change_pct": change_pct,
            "vol_ratio": vol_ratio,
            "liquidity_b": liquidity_billion,
            "is_daytrade": is_daytrade,
            "is_active": is_active,
            "is_liquid": is_liquid,
            "is_vol_valid": is_vol_valid,
            "status": "🎯 DAYTRADE" if is_daytrade else "❌",
            "reason": reason
        }
    except Exception as e:
        return {"ticker": ticker, "status": "error", "reason": str(e)[:30]}


def batch_scan(tickers: list, scan_type: str, progress_callback=None) -> list:
    """
    Batch scan multiple tickers with rate limiting.
    """
    results = []
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        if scan_type == "gem":
            result = scan_gem(ticker)
        elif scan_type == "dragon":
            result = scan_dragon(ticker)
        elif scan_type == "daytrade":
            result = scan_daytrade(ticker)
        else:
            result = scan_gem(ticker)  # Default
        
        results.append(result)
        
        if progress_callback:
            progress_callback((i + 1) / total)
        
        # Rate limiting to avoid API throttling
        if i < total - 1:
            time.sleep(0.3)
    
    return results

@st.cache_data(ttl=300)  # Cache 5 menit
def get_market_insight(ticker_symbol: str) -> tuple:
    """
    Tarik data market dan hitung indikator teknikal otomatis.
    Returns: (dataframe, market_data_dict)
    market_data_dict berisi: insight, price, trend_score, ema20, ema50, atr, 
                             sl_atr, tp_atr, pivot, r1, s1, rsi, vol_spike, is_uptrend
    """
    if not MARKET_INTEL_AVAILABLE:
        return None, {"error": "⚠️ Install dulu: pip install yfinance"}
    
    # Tambah .JK buat saham Indo
    symbol = f"{ticker_symbol}.JK"
    
    try:
        # 1. Tarik Data (3 bulan terakhir)
        df = yf.download(symbol, period="3mo", interval="1d", progress=False)
        
        if df.empty:
            return None, {"error": "❌ Data tidak ditemukan. Cek kode saham."}
        
        # Flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 2. Hitung Indikator secara manual
        df['EMA_20'] = calculate_ema(df['Close'], 20)
        df['EMA_50'] = calculate_ema(df['Close'], 50)
        df['RSI_14'] = calculate_rsi(df['Close'], 14)
        df['ATR_14'] = calculate_atr(df, 14)
        
        # Ambil data candle terakhir
        last_close = float(df['Close'].iloc[-1])
        last_ema20 = float(df['EMA_20'].iloc[-1])
        last_ema50 = float(df['EMA_50'].iloc[-1])
        last_rsi = float(df['RSI_14'].iloc[-1]) if not pd.isna(df['RSI_14'].iloc[-1]) else 50
        last_atr = float(df['ATR_14'].iloc[-1]) if not pd.isna(df['ATR_14'].iloc[-1]) else 0
        
        # Hitung Volume Spike
        avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
        curr_vol = df['Volume'].iloc[-1]
        vol_spike = bool(curr_vol > (avg_vol * 1.5))
        vol_above_avg = bool(curr_vol > avg_vol)
        
        # Hitung Pivot Points
        pivot, r1, s1 = calculate_pivot_points(df)
        
        # Hitung ATR-based SL & TP
        sl_atr = int(last_close - (2 * last_atr)) if last_atr > 0 else 0
        tp_atr = int(last_close + (3 * last_atr)) if last_atr > 0 else 0
        
        # 3. Bikin Kesimpulan Otomatis
        insight_parts = []
        trend_score = 0
        is_uptrend = False
        
        # Cek Trend
        if last_close > last_ema20 and last_ema20 > last_ema50:
            insight_parts.append("✅ **STRONG UPTREND** (Harga > EMA20 > EMA50)")
            trend_score += 2
            is_uptrend = True
        elif last_close > last_ema20:
            insight_parts.append("✅ **Short Term Bullish** (Harga > EMA20)")
            trend_score += 1
            is_uptrend = True
        else:
            insight_parts.append("⚠️ **Downtrend/Weak** (Harga < EMA20)")
            trend_score -= 1
        
        # Cek RSI
        rsi_ok = True
        if last_rsi > 70:
            insight_parts.append(f"⚠️ **RSI Overbought** ({last_rsi:.0f}) - Rawan koreksi")
            rsi_ok = False
        elif last_rsi < 30:
            insight_parts.append(f"✅ **RSI Oversold** ({last_rsi:.0f}) - Potensi pantulan")
            trend_score += 1
        else:
            insight_parts.append(f"ℹ️ RSI Netral ({last_rsi:.0f})")
        
        # Cek Volume
        if vol_spike:
            insight_parts.append("🔥 **VOLUME SPIKE!** Big money masuk/keluar")
            trend_score += 1
        
        # Add ATR info
        if last_atr > 0:
            insight_parts.append(f"📊 ATR: Rp {int(last_atr):,}")
        
        # === ADVANCED BANDAR DETECTION ===
        
        # 🐉 Sleeping Dragon
        is_dragon, dragon_range, dragon_vol_ratio = detect_sleeping_dragon(df)
        if is_dragon:
            insight_parts.append(f"🐉 **SLEEPING DRAGON!** Sideways {dragon_range:.1f}% + Vol {dragon_vol_ratio:.1f}x")
            trend_score += 2
        
        # 🕵️ OBV Divergence
        has_divergence, divergence_type = detect_obv_divergence(df)
        if has_divergence:
            insight_parts.append(f"**{divergence_type}**")
            if "AKUMULASI" in divergence_type or "BULLISH" in divergence_type:
                trend_score += 1
        
        # 📈 VWAP Check
        vwap_series = calculate_vwap(df)
        last_vwap = float(vwap_series.iloc[-1]) if len(vwap_series) > 0 else 0
        price_above_vwap = last_close > last_vwap if last_vwap > 0 else False
        if price_above_vwap:
            insight_parts.append(f"📈 **Harga > VWAP** (Bandar Jaga Harga)")
        
        # ⚡ Morning Spike
        is_morning_spike, daily_range = detect_morning_spike(df)
        if is_morning_spike:
            insight_parts.append(f"⚡ **MORNING SPIKE!** Open=Low, Range {daily_range:.1f}%")
            trend_score += 1
        
        # Volume 5 hari (untuk Mini-Bandar style)
        avg_vol_5d = float(df['Volume'].iloc[-6:-1].mean()) if len(df) > 5 else 0
        vol_above_5d = float(curr_vol) > avg_vol_5d if avg_vol_5d > 0 else False
        
        # === TIER 1 AUTOMATION LOGIC (NEW) ===

        # 1. Market Sentiment (IHSG Logic)
        try:
            ihsg = yf.Ticker("^JKSE")
            ihsg_hist = ihsg.history(period="1mo")
            if not ihsg_hist.empty and len(ihsg_hist) > 20:
                ihsg_now = ihsg_hist['Close'].iloc[-1]
                ihsg_ma20 = ihsg_hist['Close'].ewm(span=20).mean().iloc[-1]
                is_ihsg_uptrend = bool(ihsg_now > ihsg_ma20)
            else:
                is_ihsg_uptrend = False
        except:
            is_ihsg_uptrend = False

        # 2. Multi-Timeframe (Weekly)
        try:
            weekly_df = yf.download(symbol, period="6mo", interval="1wk", progress=False)
            if hasattr(weekly_df.columns, 'levels'): weekly_df.columns = weekly_df.columns.get_level_values(0)
            
            if not weekly_df.empty and len(weekly_df) >= 20:
                wk_ma20 = calculate_ema(weekly_df['Close'], 20).iloc[-1]
                is_weekly_uptrend = bool(weekly_df['Close'].iloc[-1] > wk_ma20)
            else:
                is_weekly_uptrend = False
        except:
            is_weekly_uptrend = False

        # 3. Pattern Candle (Daily)
        is_candle_pattern = False
        pattern_name = ""
        if len(df) >= 2:
            last_c = df.iloc[-1]
            prev_c = df.iloc[-2]
            
            body = abs(last_c['Close'] - last_c['Open'])
            lower_shadow = min(last_c['Close'], last_c['Open']) - last_c['Low']
            upper_shadow = last_c['High'] - max(last_c['Close'], last_c['Open'])
            
            # Hammer
            if lower_shadow >= 2 * body and upper_shadow <= 0.5 * body:
                is_candle_pattern = True
                pattern_name = "Hammer"
            
            # Bullish Engulfing
            elif (last_c['Close'] > last_c['Open'] and 
                  last_c['Close'] > prev_c['Open'] and 
                  last_c['Open'] < prev_c['Close']):
                is_candle_pattern = True
                pattern_name = "Bullish Engulfing"
        
        if is_candle_pattern:
             insight_parts.append(f"🕯️ **Pattern {pattern_name}** Detected!")
             trend_score += 1
        
        insight_text = "\n".join(insight_parts)
        
        # Return extended market data - ensure all booleans are explicit
        market_data = {
            "insight": insight_text,
            "price": int(last_close),
            "trend_score": trend_score,
            "ema20": int(last_ema20),
            "ema50": int(last_ema50),
            "atr": int(last_atr),
            "sl_atr": sl_atr,
            "tp_atr": tp_atr,
            "pivot": pivot,
            "r1": r1,
            "s1": s1,
            "rsi": last_rsi,
            "vol_spike": bool(vol_spike),
            "vol_above_avg": bool(vol_above_avg),
            "is_uptrend": bool(is_uptrend),
            "rsi_ok": bool(rsi_ok),
            # Advanced Bandar Detection
            "is_dragon": bool(is_dragon),
            "dragon_range": dragon_range,
            "dragon_vol_ratio": dragon_vol_ratio,
            "has_divergence": bool(has_divergence),
            "divergence_type": divergence_type,
            "vwap": int(last_vwap) if last_vwap > 0 else 0,
            "price_above_vwap": bool(price_above_vwap),
            "is_morning_spike": bool(is_morning_spike),
            "vol_above_5d": bool(vol_above_5d),
            
            # Tier 1 Automation
            "is_ihsg_uptrend": is_ihsg_uptrend,
            "is_weekly_uptrend": is_weekly_uptrend,
            "is_candle_pattern": is_candle_pattern,
            "pattern_name": pattern_name
        }
        
        return df, market_data
        
    except Exception as e:
        return None, {"error": f"❌ Error: {str(e)}"}
