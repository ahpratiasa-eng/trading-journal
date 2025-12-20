# 📊 Pro Trading Journal & Kalkulator v2.0

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green)

**Aplikasi trading journal pintar untuk trader Indonesia (IDX).** Dilengkapi dengan AI Market Intelligence, Batch Scanner, Risk Calculator, dan Smart Checklist untuk membantu eksekusi trade yang disiplin dan profitable.

---

## 🚀 Fitur Utama

### 1. 🧮 Risk Calculator (Kalkulator Posisi)
Hitung otomatis:
- **Max Lot** yang boleh dibeli berdasarkan risiko
- **Position Value** (nilai posisi)
- **Fee Broker** (beli & jual)
- **Potensi Profit/Loss** bersih setelah fee
- **Risk-Reward Ratio (RRR)**

### 2. 🤖 AI Market Intelligence
Analisa teknikal otomatis dari Yahoo Finance:
- **Trend Analysis** (EMA 20 & 50)
- **RSI Indicator** (Overbought/Oversold)
- **Volume Spike Detection**
- **ATR (Volatility)** untuk SL/TP dinamis
- **Pivot Points** (Support & Resistance)
- **VWAP Check** (Bandar Jaga Harga)

### 3. 🐉 Advanced Bandar Detection
- **Sleeping Dragon** - Deteksi saham sideways yang tiba-tiba ada volume spike
- **OBV Divergence** - Deteksi akumulasi tersembunyi (smart money)
- **VWAP Check** - Cek apakah bandar "jaga harga"
- **Morning Spike** - Deteksi setup HAKA (Open = Low)

### 4. 📈 Candlestick Chart
- Chart interaktif dengan **Moving Average overlay**
- **Volume bar** di bagian bawah
- **Date range** display
- **Adaptive timeframe**: Daily untuk Swing, 5-min untuk Scalper

### 5. 🎮 Strategy Mode Selector
Pilih gaya trading, checklist otomatis menyesuaikan:

| Mode | Struktur Pasar | Volume Check |
|------|----------------|--------------|
| 📈 Swing/Normal | Harga > EMA20 | > Rata-rata 20 hari |
| ⚡ Scalper (HAKA) | Open = Low | > Rata-rata 20 hari |
| 🐋 Mini-Bandar | Harga > VWAP | > Rata-rata 5 hari |

### 6. ✅ Smart Auto-Checklist
- Item **teknikal otomatis dicentang** berdasarkan data market
- Item **subjektif** (sentimen, berita, broker summary) input manual
- Progress bar dan skor checklist
- **Strategy-based logic** (bypass EMA untuk Scalper mode)

### 7. 🏆 Win Rate Keeper
- Tracking win rate dari jurnal trading
- Warning otomatis kalau performa turun di bawah 50%
- Pressure bar untuk menjaga disiplin

### 8. 🌍 Foreign Flow Integration
Input manual dari OLT/Stockbit:
- **Net Buy** → Score +1 (Support)
- **Net Sell** → Score -2 (Penalty - Rawan Guyur!)
- Terintegrasi dengan Decision Engine

### 9. 🔍 Batch Scanner (NEW!)
Scan massal saham dari screener Stockbit/RTI:

| Mode | Logic | Hasil |
|------|-------|-------|
| 💎 GEM (Swing DN) | Uptrend + Konsolidasi (-3% s/d +2%) | Saham siap breakout |
| 🐉 Dragon (Momentum) | Vol > 1.5x + Change > 2% | Saham lagi terbang |

**Fitur Batch Scanner:**
- Paste sampai 50 ticker sekaligus
- Progress bar real-time
- Results table dengan sorting
- Quick Analyze buttons (1-click analisa)

---

## 📦 Instalasi

### Prerequisites
- Python 3.10 atau lebih baru
- pip (Python package manager)

### Langkah Instalasi

```bash
# 1. Clone atau download repository
cd trading-journal

# 2. Install dependencies
pip install -r requirements.txt

# 3. Jalankan aplikasi
streamlit run trading_journal.py
```

### Dependencies
```
streamlit>=1.28.0
pandas>=2.0.0
yfinance>=0.2.0
mplfinance>=0.12.0
matplotlib>=3.7.0
```

---

## 📖 Cara Penggunaan

### Step 1: Pilih Strategy Mode
Di sidebar, pilih gaya trading lo:
- **Swing/Normal** - Untuk swing trading berbasis trend EMA
- **Scalper** - Untuk scalping dengan setup HAKA
- **Mini-Bandar** - Untuk flow trading berbasis VWAP

### Step 2: Input Kode Saham
Ketik kode saham Indonesia (tanpa .JK), contoh:
- `BBRI` - Bank BRI
- `TLKM` - Telkom
- `TINS` - Timah

### Step 3: Klik "Analisa Saham"
Buka expander **"📊 Market Intel & Chart"** dan klik tombol **"🔍 Analisa Saham"**.

Aplikasi akan menampilkan:
- 📊 Candlestick Chart dengan date range
- 🤖 AI Analysis (Trend, RSI, Volume, dll)
- 🎯 Pivot Points (S1, P, R1)
- 🐉 Deteksi pola khusus (Sleeping Dragon, dll)

### Step 4: Set Entry, SL, TP
Gunakan tombol cepat untuk SL & TP:

**Stop Loss:**
- `EMA20` - Set SL ke level EMA 20
- `EMA50` - Set SL ke level EMA 50
- `ATR` - Set SL ke Harga - (2 × ATR)
- `S1` - Set SL ke Support 1 (Pivot)

> **Note:** Tombol hanya muncul jika level valid (di bawah entry)

**Take Profit:**
- `ATR` - Set TP ke Harga + (3 × ATR)
- `R1` - Set TP ke Resistance 1 (Pivot)

### Step 5: Input Foreign Flow
Di sidebar bagian bawah, pilih status asing:
- ⚪ **Netral** - Tidak ada info
- 🟢 **Net Buy** - Asing akumulasi
- 🔴 **Net Sell** - Asing distribusi (BAHAYA!)

### Step 6: Cek Smart Checklist
Scroll ke bagian **"Smart Checklist Pra-Trade"**:
- ✅ 🔒 = Item teknikal yang sudah terpenuhi (otomatis)
- ❌ = Item teknikal yang belum terpenuhi
- ☐ = Item manual yang perlu dicek sendiri

### Step 7: Lihat Keputusan Trade
Aplikasi memberikan rekomendasi:
- 🚀 **STRONG BUY** - RRR bagus + Checklist sempurna + Asing OK
- ☔ **BAHAYA** - Teknikal bagus TAPI Asing jualan (Bull Trap!)
- ⚠️ **HATI-HATI** - RRR bagus tapi checklist belum lengkap
- 🛑 **JANGAN TRADE** - RRR jelek atau checklist kurang

### Step 8: Gunakan Batch Scanner
Scroll ke bagian paling bawah:
1. Pilih mode: **GEM** atau **Dragon**
2. Paste ticker dari screener Stockbit/RTI
3. Klik **"🚀 Mulai Scan"**
4. Lihat hasil di table
5. Klik ticker yang lolos untuk analisa detail

---

## 🎓 Penjelasan Indikator

### EMA (Exponential Moving Average)
- **EMA 20**: Trend jangka pendek
- **EMA 50**: Trend jangka menengah
- **Harga > EMA20 > EMA50** = Strong Uptrend

### RSI (Relative Strength Index)
- **RSI > 70**: Overbought (rawan koreksi)
- **RSI < 30**: Oversold (potensi pantulan)
- **RSI 30-70**: Netral

### ATR (Average True Range)
- Mengukur volatilitas harian saham
- **SL = Harga - (2 × ATR)** → Kasih ruang gerak
- **TP = Harga + (3 × ATR)** → Target RRR 1:1.5

### VWAP (Volume Weighted Average Price)
- Harga rata-rata tertimbang volume
- **Harga > VWAP** = Buyer dominan (bandar jaga harga)
- **Harga < VWAP** = Seller dominan

### OBV (On Balance Volume)
- Mengukur aliran volume
- **Harga sideways + OBV naik** = Akumulasi tersembunyi

---

## 🐉 Special Patterns

### Sleeping Dragon 🐉
**Kondisi:**
- Saham sideways (range < 15%) selama 20 hari
- Volume hari ini > 2× rata-rata

**Arti:** Potensi mark-up phase, bandar mulai gerak.

### Morning Spike ⚡
**Kondisi:**
- Open = Low (harga buka = harga terendah)
- Daily range > 2%

**Arti:** Strong buyer dari menit pertama (HAKA setup).

### OBV Divergence 🕵️
**Kondisi:**
- Harga flat/turun
- OBV naik

**Arti:** Smart money sedang akumulasi diam-diam.

---

## 🔍 Batch Scanner Logic

### 💎 GEM Scanner (David Noah Style)
Mencari saham untuk **Swing Trading**:
```
Kondisi:
1. Harga > EMA20 (Confirmed Uptrend)
2. Daily Change -3% s/d +2% (Konsolidasi)

Hasil: Saham "tidur" yang siap breakout
```

### 🐉 Dragon Scanner (Momentum Style)
Mencari saham untuk **Scalping/Momentum**:
```
Kondisi:
1. Volume > 1.5x rata-rata 20 hari
2. Daily Change > +2%

Hasil: Saham yang lagi "terbang"
```

---

## ⚙️ Pengaturan

### Profil Risiko Cepat
| Profil | Risk % | Deskripsi |
|--------|--------|-----------|
| 🛡️ Konservatif | 0.5% | Risiko rendah |
| ⚖️ Moderat | 1.0% | Risiko seimbang |
| 🔥 Agresif | 2.0% | Risiko tinggi |
| 💀 YOLO | 5.0% | All-in! |

### Fee Broker
Default:
- Fee Beli: 0.15%
- Fee Jual: 0.25%

Bisa diubah di **"🏦 Fee Broker"** expander.

---

## 📁 Struktur File

```
trading-journal/
├── trading_journal.py    # Aplikasi utama
├── requirements.txt      # Dependencies
├── README.md            # Dokumentasi ini
├── user_settings.json   # Settings user (auto-generated)
└── trading_journal.csv  # Data jurnal (auto-generated)
```

---

## 🔧 Troubleshooting

### Chart tidak muncul
```bash
pip install mplfinance matplotlib
```

### Data saham tidak ditemukan
- Pastikan kode saham benar (tanpa .JK)
- Cek koneksi internet
- Beberapa saham mungkin tidak ada di Yahoo Finance

### Batch Scanner lambat
- Normal! Ada rate limiting 0.3 detik per ticker
- Maksimal 50 ticker per scan
- Tunggu progress bar selesai

### Error saat jalankan
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

---

## 📝 Changelog

### v2.0.0 (Current) 🎉
- ✨ **Batch Scanner** (GEM & Dragon mode)
- ✨ **Foreign Flow Integration** (Net Buy/Sell)
- ✨ Decision Engine with Foreign scoring
- ✨ Smart SL/TP buttons (only valid levels shown)
- ✨ Chart date range display
- 🔧 Strategy-based checklist bypass

### v1.2.0
- ✨ Candlestick chart dengan mplfinance
- ✨ Strategy mode selector (Swing/Scalper/Mini-Bandar)
- ✨ Advanced bandar detection (Sleeping Dragon, OBV, VWAP)
- ✨ Win Rate Keeper widget
- 🔧 Smart checklist dengan auto-check

### v1.1.0
- ✨ Market Intelligence dengan yfinance
- ✨ ATR-based SL/TP
- ✨ Pivot Points

### v1.0.0
- 🎉 Initial release
- Risk calculator
- Basic checklist
- Trade journal

---

## 📜 Disclaimer

⚠️ **Aplikasi ini hanya untuk edukasi dan referensi.**

- Bukan rekomendasi jual/beli saham
- Keputusan trading sepenuhnya tanggung jawab user
- Past performance does not guarantee future results
- Selalu lakukan riset sendiri sebelum trading

---

## 🤝 Contributing

Pull requests welcome! Untuk perubahan besar, silakan buka issue terlebih dahulu.

---

## 📧 Contact

Made with ❤️ for Indonesian traders.

**Happy Trading & Stay Disciplined!** 🚀📈
