# trading/hedge_fund.py

from dataclasses import dataclass
import pandas as pd
import numpy as np
from typing import Optional
from .trades import QuotedTrade

@dataclass
class HfResponse:
    ticker: str
    trade_volume: float
    trade_price: float
    hf_action: str         # "buy", "sell", "refuse"
    ref_price: float
    bid_price: float
    offer_price: float
    date: pd.Timestamp


class HedgeFund:
    """
    Simple decision model for the hedge fund.
    - It sees your quoted trade
    - Decides to buy/sell/refuse
    - Uses bid/offer as transaction price
    """
    def __init__(self, buy_prob=0.4, sell_prob=0.4, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self.buy_prob = buy_prob
        self.sell_prob = sell_prob
        self.refuse_prob = 1.0 - buy_prob - sell_prob

    def show(self, quote: QuotedTrade) -> HfResponse:
        r = self.rng.random()

        if r < self.buy_prob:
            hf_action = "buy"
            trade_price = quote.offer_price     # client buys → pays offer
            trade_volume = quote.trade_volume

        elif r < self.buy_prob + self.sell_prob:
            hf_action = "sell"
            trade_price = quote.bid_price       # client sells → receives bid
            trade_volume = quote.trade_volume

        else:
            hf_action = "refuse"
            trade_price = np.nan
            trade_volume = 0.0

        return HfResponse(
            ticker=quote.ticker,
            trade_volume=trade_volume,
            trade_price=trade_price,
            hf_action=hf_action,
            ref_price=quote.ref_price,
            bid_price=quote.bid_price,
            offer_price=quote.offer_price,
            date=quote.date,
        )
