from dataclasses import dataclass
import pandas as pd

@dataclass
class QuotedTrade:
    ticker: str
    trade_volume: float
    ref_price: float
    bid_price: float
    offer_price: float
    date: pd.Timestamp

@dataclass
class CompletedTrade:
    ticker: str
    trade_volume: float
    trade_price: float
    mm_action: str     # buy / sell
    ref_price: float
    bid_price: float
    offer_price: float
    date: pd.Timestamp
