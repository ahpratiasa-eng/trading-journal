from dataclasses import dataclass

# Konstanta
LOT_SIZE = 100

@dataclass
class TradeSetup:
    """Representasi setup trade lengkap dengan semua parameter."""
    ticker: str
    capital: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_percent: float
    buy_fee_pct: float
    sell_fee_pct: float
    
    @property
    def risk_per_share(self) -> float:
        """Hitung risiko per lembar (Entry - SL)."""
        return self.entry_price - self.stop_loss
    
    @property
    def reward_per_share(self) -> float:
        """Hitung reward per lembar (TP - Entry)."""
        return self.take_profit - self.entry_price
    
    @property
    def max_risk_amount(self) -> float:
        """Maksimum risiko dalam Rupiah berdasarkan modal dan % risiko."""
        return self.capital * (self.risk_percent / 100)
    
    @property
    def rrr(self) -> float:
        """Hitung Risk-to-Reward Ratio."""
        if self.risk_per_share <= 0:
            return 0
        return self.reward_per_share / self.risk_per_share
    
    def calculate_max_lots(self) -> int:
        """
        Hitung maksimum lot berdasarkan jumlah risiko.
        Rumus: Max Risk (Rp) / (Entry - SL) / LOT_SIZE
        Batasan: Total Nilai Beli + Fee Beli <= Modal
        """
        if self.risk_per_share <= 0:
            return 0
        
        # Hitung lot berdasarkan risiko
        max_shares_by_risk = self.max_risk_amount / self.risk_per_share
        max_lots_by_risk = int(max_shares_by_risk / LOT_SIZE)
        
        # Hitung lot berdasarkan batasan modal
        # Total = (Harga * Lot * 100) * (1 + fee_beli)
        max_value_with_fee = self.capital / (1 + self.buy_fee_pct)
        max_shares_by_capital = max_value_with_fee / self.entry_price
        max_lots_by_capital = int(max_shares_by_capital / LOT_SIZE)
        
        # Return minimum dari kedua batasan
        return max(0, min(max_lots_by_risk, max_lots_by_capital))
    
    def calculate_position_value(self, lots: int) -> float:
        """Hitung total nilai posisi untuk lot tertentu."""
        return self.entry_price * lots * LOT_SIZE
    
    def calculate_buy_fee(self, lots: int) -> float:
        """Hitung fee beli untuk lot tertentu."""
        return self.calculate_position_value(lots) * self.buy_fee_pct
    
    def calculate_total_buy_cost(self, lots: int) -> float:
        """Hitung total biaya beli termasuk fee."""
        return self.calculate_position_value(lots) + self.calculate_buy_fee(lots)
    
    def calculate_potential_profit(self, lots: int) -> float:
        """
        Hitung potensi profit bersih setelah fee jual.
        Profit = (TP - Entry) * lembar - Fee Jual di TP
        """
        shares = lots * LOT_SIZE
        gross_profit = self.reward_per_share * shares
        sell_value_at_tp = self.take_profit * shares
        sell_fee = sell_value_at_tp * self.sell_fee_pct
        return gross_profit - sell_fee
    
    def calculate_potential_loss(self, lots: int) -> float:
        """
        Hitung potensi loss bersih setelah fee jual.
        Loss = (Entry - SL) * lembar + Fee Jual di SL
        """
        shares = lots * LOT_SIZE
        gross_loss = self.risk_per_share * shares
        sell_value_at_sl = self.stop_loss * shares
        sell_fee = sell_value_at_sl * self.sell_fee_pct
        return gross_loss + sell_fee


@dataclass  
class TradeRecord:
    """Representasi catatan trade untuk jurnal."""
    timestamp: str
    ticker: str
    entry_price: float
    stop_loss: float
    take_profit: float
    lots: int
    capital: float
    risk_percent: float
    rrr: float
    potential_profit: float
    potential_loss: float
    checklist_score: int
    decision: str
    notes: str = ""
    exit_price: float = 0.0
    realized_pnl: float = 0.0
    status: str = "OPEN"
