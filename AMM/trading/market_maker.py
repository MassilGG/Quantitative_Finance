# trading/market_maker.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from .trades import QuotedTrade, CompletedTrade
import pandas as pd

@dataclass
class Position:
    ticker: str
    position_volume: float = 0.0

@dataclass
class ETFPosition:
    ticker: str
    trade_volume: float
    trade_price: float
    action: str
    date: pd.Timestamp

@dataclass
class ExecutedTrade:
    """
    Execution report returned by the exchange.
    """
    ticker: str
    trade_volume: float
    trade_price: float        # actual execution price
    action: str               # 'buy' or 'sell'
    date: pd.Timestamp

class MarketMaker:
    """
    Market maker object, reconstructed from the assessment.
    Accepts lists of trades at initialization.
    """

    def __init__(
        self,
        quoted_trades: Optional[List[QuotedTrade]] = None,
        completed_trades: Optional[List[CompletedTrade]] = None
    ):
        self.quoted_trades: List[QuotedTrade] = quoted_trades if quoted_trades else []
        self.completed_trades: List[CompletedTrade] = completed_trades if completed_trades else []
        self.current_positions: Dict[str, Position] = {}
        self.ETF_positions: List[ETFPosition] = []

    @classmethod
    def mm(cls, quoted_trades=None, completed_trades=None):
        """
        Mimics AmplifyQuantTrading.MarketMaker.mm() behavior.
        """
        return cls(quoted_trades, completed_trades)

    def add_quoted_trade(self, trade: QuotedTrade) -> str:
        self.quoted_trades.append(trade)
        return f"QuotedTrade added for {trade.ticker} on {trade.date}"

    def add_trade(self, trade: CompletedTrade) -> str:
        self.completed_trades.append(trade)

        pos = self.current_positions.get(trade.ticker, Position(trade.ticker, 0.0))

        if trade.mm_action == "buy":
            pos.position_volume += trade.trade_volume
        elif trade.mm_action == "sell":
            pos.position_volume -= trade.trade_volume
        else:
            raise ValueError(f"Unknown mm_action: {trade.mm_action}")

        self.current_positions[trade.ticker] = pos
        return f"CompletedTrade logged: {trade.mm_action} {trade.trade_volume} {trade.ticker} @ {trade.trade_price:.2f}"

    def update_ETF_position(self, executed_trade: ExecutedTrade) -> str:
            """
            Update positions and log ETF / hedge positions.
            """
            # 1) update position in current_positions dict
            pos = self.current_positions.get(
                executed_trade.ticker,
                Position(executed_trade.ticker, 0.0)
            )

            if executed_trade.action == "buy":
                pos.position_volume += executed_trade.trade_volume
            elif executed_trade.action == "sell":
                pos.position_volume -= executed_trade.trade_volume
            else:
                raise ValueError(f"Unknown action {executed_trade.action}")

            self.current_positions[executed_trade.ticker] = pos

            # 2) log in ETF_positions for later PnL attribution
            etf_pos = ETFPosition(
                ticker=executed_trade.ticker,
                trade_volume=executed_trade.trade_volume,
                trade_price=executed_trade.trade_price,
                action=executed_trade.action,
                date=executed_trade.date
            )
            self.ETF_positions.append(etf_pos)

            return (
                f"Hedge {executed_trade.action} {executed_trade.trade_volume} "
                f"{executed_trade.ticker} @ {executed_trade.trade_price:.2f}"
            )