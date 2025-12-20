import pandas as pd
import os
import streamlit as st
from abc import ABC, abstractmethod
from models import TradeRecord

# File paths
DEFAULT_JOURNAL_FILE = "trading_journal.csv"

class DataPersistence(ABC):
    """Abstract base class untuk persistensi data."""
    
    @abstractmethod
    def save_trade(self, record: TradeRecord) -> bool:
        """Simpan catatan trade. Return True jika berhasil."""
        pass
    
    @abstractmethod
    def load_trades(self) -> pd.DataFrame:
        """Load semua catatan trade."""
        pass
    
    @abstractmethod
    def get_trade_count(self) -> int:
        """Dapatkan total jumlah trade."""
        pass

    @abstractmethod
    def save_all_trades(self, df: pd.DataFrame) -> bool:
        """Simpan ulang seluruh dataframe."""
        pass


class CSVPersistence(DataPersistence):
    """Implementasi persistensi data berbasis CSV."""
    
    def __init__(self, filepath: str = DEFAULT_JOURNAL_FILE):
        self.filepath = filepath
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Buat file CSV dengan header jika belum ada."""
        if not os.path.exists(self.filepath):
            df = pd.DataFrame(columns=[
                'timestamp', 'ticker', 'entry_price', 'stop_loss', 'take_profit',
                'lots', 'capital', 'risk_percent', 'rrr', 'potential_profit',
                'potential_loss', 'checklist_score', 'decision', 'notes',
                'exit_price', 'realized_pnl', 'status'
            ])
            df.to_csv(self.filepath, index=False)
    
    def save_trade(self, record: TradeRecord) -> bool:
        """Simpan catatan trade ke CSV."""
        try:
            df = pd.DataFrame([{
                'timestamp': record.timestamp,
                'ticker': record.ticker,
                'entry_price': record.entry_price,
                'stop_loss': record.stop_loss,
                'take_profit': record.take_profit,
                'lots': record.lots,
                'capital': record.capital,
                'risk_percent': record.risk_percent,
                'rrr': round(record.rrr, 2),
                'potential_profit': round(record.potential_profit, 2),
                'potential_loss': round(record.potential_loss, 2),
                'checklist_score': record.checklist_score,
                'decision': record.decision,
                'notes': record.notes,
                'exit_price': record.exit_price,
                'realized_pnl': record.realized_pnl,
                'status': record.status
            }])
            
            df.to_csv(self.filepath, mode='a', header=False, index=False)
            return True
        except Exception as e:
            st.error(f"Error menyimpan trade: {e}")
            return False
    
    def load_trades(self) -> pd.DataFrame:
        """Load semua catatan trade dari CSV."""
        try:
            if os.path.exists(self.filepath):
                # Force types for critical columns to prevent editing errors
                df = pd.read_csv(self.filepath, dtype={
                    'notes': str, 
                    'ticker': str,
                    'decision': str,
                    'status': str
                })
                
                # Ensure new columns exist for backward compatibility
                required_cols = {
                    'exit_price': 0.0, 
                    'realized_pnl': 0.0, 
                    'status': 'OPEN'
                }
                for col, default in required_cols.items():
                    if col not in df.columns:
                        df[col] = default
                
                # Sanitize text columns
                if 'notes' in df.columns:
                    df['notes'] = df['notes'].fillna('')
                if 'decision' in df.columns:
                    df['decision'] = df['decision'].fillna('')
                    
                return df
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error memuat trade: {e}")
            return pd.DataFrame()
    
    
    def get_trade_count(self) -> int:
        """Dapatkan total jumlah trade."""
        df = self.load_trades()
        return len(df)

    def save_all_trades(self, df: pd.DataFrame) -> bool:
        """Simpan ulang seluruh dataframe (untuk edit)."""
        try:
            df.to_csv(self.filepath, index=False)
            return True
        except Exception as e:
            st.error(f"Error menyimpan perubahan: {e}")
            return False


class FirestorePersistence(DataPersistence):
    """Implementasi persistensi data berbasis Google Cloud Firestore."""
    
    def __init__(self, collection_name: str = "trades"):
        try:
            from google.cloud import firestore
            from google.oauth2 import service_account
            import json
        except ImportError:
            st.error("⚠️ Library google-cloud-firestore belum terinstall.")
            return

        self.collection_name = collection_name
        self.db = None
        
        try:
            # Coba autentikasi via st.secrets (Prioritas untuk Streamlit Cloud)
            if "gcp_service_account" in st.secrets:
                # Menggunakan dictionary langsung dari secrets TOML
                key_dict = dict(st.secrets["gcp_service_account"])
                
                # Fix: Handle private_key formatting if it comes from TOML string with escaped newlines
                if "private_key" in key_dict:
                    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
                
                creds = service_account.Credentials.from_service_account_info(key_dict)
                self.db = firestore.Client(credentials=creds)
            
            # Fallback: Environment Variable (Data lokal / Default gcloud auth)
            else:
                self.db = firestore.Client()
                
            self.collection = self.db.collection(collection_name)
            
        except Exception as e:
            st.error(f"❌ Gagal koneksi ke Firestore: {e}")
            self.db = None

    def save_trade(self, record: TradeRecord) -> bool:
        """Simpan catatan trade ke Firestore."""
        if not self.db: return False
        try:
            # Convert Record ke Dict
            data = {
                'timestamp': record.timestamp,
                'ticker': record.ticker,
                'entry_price': record.entry_price,
                'stop_loss': record.stop_loss,
                'take_profit': record.take_profit,
                'lots': record.lots,
                'capital': record.capital,
                'risk_percent': record.risk_percent,
                'rrr': record.rrr,
                'potential_profit': record.potential_profit,
                'potential_loss': record.potential_loss,
                'checklist_score': record.checklist_score,
                'decision': record.decision,
                'notes': record.notes,
                'exit_price': record.exit_price,
                'realized_pnl': record.realized_pnl,
                'status': record.status,
                'created_at': firestore.SERVER_TIMESTAMP  # Tambah timestamp server
            }
            
            # Add document (Auto ID)
            self.collection.add(data)
            return True
        except Exception as e:
            st.error(f"Error menyimpan ke Firestore: {e}")
            return False

    def load_trades(self) -> pd.DataFrame:
        """Load semua catatan trade dari Firestore."""
        if not self.db: return pd.DataFrame()
        try:
            docs = self.collection.order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
            
            items = []
            for doc in docs:
                item = doc.to_dict()
                # Server timestamp might be None locally immediately after write? 
                # or a Datetime object. Pandas handles datetime objects well.
                items.append(item)
            
            if not items:
                return pd.DataFrame()

            df = pd.DataFrame(items)
            
            # Ensure required columns
            required_cols = {
                    'exit_price': 0.0, 
                    'realized_pnl': 0.0, 
                    'status': 'OPEN',
                    'notes': '',
                    'decision': ''
            }
            for col, default in required_cols.items():
                if col not in df.columns:
                    df[col] = default
            
            return df
        except Exception as e:
            st.error(f"Error memuat dari Firestore: {e}")
            return pd.DataFrame()

    def get_trade_count(self) -> int:
         if not self.db: return 0
         # Note: Costly counting for large collections, but fine for journal
         return len(self.load_trades())

    def save_all_trades(self, df: pd.DataFrame) -> bool:
        """
        CAUTION: Firestore tidak didesain untuk overwrite bulk seperti CSV.
        Fungsi ini (edit) agak kompleks di NoSQL.
        Kita harus update dokumen spesifik. Untuk sekarang, return False atau
        implementasi update by timestamp/ID jika memungkinkan.
        """
        st.warning("⚠️ Fitur edit massal belum support penuh di Cloud Mode.")
        return False

