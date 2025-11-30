# trading/exchange.py

from dataclasses import dataclass
import pandas as pd

@dataclass
class ExchangeTrade:
    """
    Order you send to the exchange for hedging.
    """
    ticker: str
    trade_volume: float       # >0, in units (shares or contracts)
    ref_price: float          # price used to size the trade
    action: str               # 'buy' or 'sell'
    date: pd.Timestamp        # timestamp of the hedge


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


class Exchange:
    """
    Very simple exchange simulator: you send an ExchangeTrade,
    it fills you at the mid (or close) price from a prices DataFrame.
    """

    def __init__(self, prices: pd.DataFrame):
        """
        prices: DataFrame with columns = tickers, index = timestamps
        """
        self.prices = prices

    def execute(self, trade: ExchangeTrade) -> ExecutedTrade:
        # Get execution price from the market data
        try:
            px = float(self.prices.loc[trade.date, trade.ticker])
        except KeyError:
            # Fallback: use ref_price if date/ticker not found
            px = trade.ref_price

        return ExecutedTrade(
            ticker=trade.ticker,
            trade_volume=trade.trade_volume,
            trade_price=px,
            action=trade.action,
            date=trade.date
        )
