import pandas as pd
from collections import defaultdict

def transaction_cost(volume, price, fee_rate=0.00005, fee_per_unit=0.0):
    """
    Simple transaction cost model.
    fee_rate: proportional fee on notional (e.g. 0.00005 = 0.5 bp)
    fee_per_unit: fixed fee per unit traded (e.g. per share/contract)
    """
    notional = abs(volume) * price
    return fee_rate * notional + fee_per_unit * abs(volume)


def compute_pnl_with_attribution(
    mm,
    prices: pd.DataFrame,
    fee_rate_client=0.0,
    fee_rate_hedge=0.0,
    fee_per_unit_client=0.0,
    fee_per_unit_hedge=0.0,
    futures_multipliers=None,  # e.g. {"YM=F": 5.0}, None for ETF-only
):
    """
    Compute PnL with attribution:
      - spread_pnl: from trading against clients vs ref price
      - inventory_pnl: price move on client inventory
      - hedge_pnl: price move on hedge positions (ETF/futures)
      - client_cost, hedge_cost: transaction costs
      - total_pnl: spread + inventory + hedge - costs
      - equity: cash + MTM inventory (starting from 0)
    
    Args:
        mm: MarketMaker instance
        prices: DataFrame (index = dates, columns = tickers)
        fee_*: transaction cost parameters
        futures_multipliers: dict[ticker -> contract multiplier] for futures,
                             if None, all multipliers = 1.
    """
    prices = prices.sort_index()
    dates = prices.index
    futures_multipliers = futures_multipliers or {}

    # Group trades by date
    trades_by_date = defaultdict(list)
    for ct in mm.completed_trades:
        trades_by_date[ct.date].append(("client", ct))
    for ht in mm.ETF_positions:
        trades_by_date[ht.date].append(("hedge", ht))

    # State
    inventory_main = defaultdict(float)   # client inventory (units)
    inventory_hedge = defaultdict(float)  # hedge inventory (units or contracts)
    cash = 0.0

    # Flows (per date)
    spread_pnl = pd.Series(0.0, index=dates)
    inventory_pnl = pd.Series(0.0, index=dates)
    hedge_pnl = pd.Series(0.0, index=dates)
    client_cost = pd.Series(0.0, index=dates)
    hedge_cost = pd.Series(0.0, index=dates)
    equity = pd.Series(0.0, index=dates)

    prev_date = None

    for current_date in dates:
        # 1) Price-move PnL from prev_date to current_date
        if prev_date is not None:
            dP = prices.loc[current_date] - prices.loc[prev_date]

            # inventory PnL (client book)
            inv_p = 0.0
            for ticker, qty in inventory_main.items():
                if ticker in prices.columns:
                    inv_p += qty * dP.get(ticker, 0.0)

            # hedge PnL
            hed_p = 0.0
            for ticker, qty in inventory_hedge.items():
                if ticker in prices.columns:
                    mult = futures_multipliers.get(ticker, 1.0)
                    hed_p += qty * mult * dP.get(ticker, 0.0)

            inventory_pnl.loc[current_date] = inv_p
            hedge_pnl.loc[current_date] = hed_p

        # 2) Spread PnL + costs + inventory updates from trades at current_date
        sp = 0.0
        cc = 0.0
        hc = 0.0

        for trade_type, tr in trades_by_date[current_date]:
            if trade_type == "client":
                # client trade
                ticker = tr.ticker
                price = tr.trade_price
                vol = tr.trade_volume
                signed_vol = vol if tr.mm_action == "buy" else -vol
                mid = tr.ref_price

                # spread PnL
                sp += (mid - price) * signed_vol

                # transaction cost
                cost = transaction_cost(
                    volume=vol,
                    price=price,
                    fee_rate=fee_rate_client,
                    fee_per_unit=fee_per_unit_client,
                )
                cc += cost

                # update cash and inventory
                notional = signed_vol * price
                cash -= notional
                cash -= cost
                inventory_main[ticker] += signed_vol

            else:
                # hedge trade
                ticker = tr.ticker
                price = tr.trade_price
                vol = tr.trade_volume
                signed_vol = vol if tr.action == "buy" else -vol

                cost = transaction_cost(
                    volume=vol,
                    price=price,
                    fee_rate=fee_rate_hedge,
                    fee_per_unit=fee_per_unit_hedge,
                )
                hc += cost

                notional = signed_vol * price
                cash -= notional
                cash -= cost
                inventory_hedge[ticker] += signed_vol

        spread_pnl.loc[current_date] = sp
        client_cost.loc[current_date] = cc
        hedge_cost.loc[current_date] = hc

        # 3) Mark-to-market equity at current_date
        port_val = 0.0
        for ticker, qty in inventory_main.items():
            if ticker in prices.columns:
                port_val += qty * prices.loc[current_date, ticker]
        for ticker, qty in inventory_hedge.items():
            if ticker in prices.columns:
                mult = futures_multipliers.get(ticker, 1.0)
                port_val += qty * mult * prices.loc[current_date, ticker]

        equity[current_date] = cash + port_val
        prev_date = current_date

    # Pack into DataFrame
    pnl_df = pd.DataFrame({
        "spread_pnl": spread_pnl,
        "inventory_pnl": inventory_pnl,
        "hedge_pnl": hedge_pnl,
        "client_cost": client_cost,
        "hedge_cost": hedge_cost,
    })
    pnl_df["total_cost"] = pnl_df["client_cost"] + pnl_df["hedge_cost"]
    pnl_df["total_pnl"] = (
        pnl_df["spread_pnl"]
        + pnl_df["inventory_pnl"]
        + pnl_df["hedge_pnl"]
        - pnl_df["total_cost"]
    )
    pnl_df["equity"] = equity

    pnl_df["cum_spread_pnl"] = pnl_df["spread_pnl"].cumsum()
    pnl_df["cum_inventory_pnl"] = pnl_df["inventory_pnl"].cumsum()
    pnl_df["cum_hedge_pnl"] = pnl_df["hedge_pnl"].cumsum()
    pnl_df["cum_total_cost"] = pnl_df["total_cost"].cumsum()
    pnl_df["cum_total_pnl"] = pnl_df["total_pnl"].cumsum()

    return pnl_df


def compute_simple_pnl(mm, prices: pd.DataFrame,
                       fee_rate_client=0.0, fee_rate_hedge=0.0,
                       fee_per_unit_client=0.0, fee_per_unit_hedge=0.0):
    """
    Very simple PnL engine with transaction costs, no attribution.
    
    - Tracks cash + inventory over time.
    - Applies transaction costs on each trade.
    - Returns a time series of equity (PnL if starting from 0).
    
    Args:
        mm: MarketMaker
        prices: DataFrame (index = dates, columns = tickers)
        fee_rate_client: proportional fee for client trades
        fee_rate_hedge: proportional fee for hedge trades
        fee_per_unit_client: per-unit fee for client trades
        fee_per_unit_hedge: per-unit fee for hedge trades
    """
    prices = prices.sort_index()
    dates = prices.index

    # Group trades by date (client + hedge)
    trades_by_date = defaultdict(list)

    # Client trades: CompletedTrade, with mm_action ('buy'/'sell')
    for ct in mm.completed_trades:
        trades_by_date[ct.date].append(("client", ct))

    # Hedge trades: ETFPosition (or futures), with action ('buy'/'sell')
    for ht in mm.ETF_positions:
        trades_by_date[ht.date].append(("hedge", ht))

    # State
    inventory = defaultdict(float)   # units per ticker
    cash = 0.0

    # PnL (equity) time series
    equity = pd.Series(0.0, index=dates)

    for current_date in dates:
        # 1) Apply all trades at this date
        for trade_type, tr in trades_by_date[current_date]:
            if trade_type == "client":
                ticker = tr.ticker
                price = tr.trade_price
                vol = tr.trade_volume
                # from MM perspective
                signed_vol = vol if tr.mm_action == "buy" else -vol

                cost = transaction_cost(
                    volume=vol,
                    price=price,
                    fee_rate=fee_rate_client,
                    fee_per_unit=fee_per_unit_client,
                )

            else:  # "hedge"
                ticker = tr.ticker
                price = tr.trade_price
                vol = tr.trade_volume
                signed_vol = vol if tr.action == "buy" else -vol

                cost = transaction_cost(
                    volume=vol,
                    price=price,
                    fee_rate=fee_rate_hedge,
                    fee_per_unit=fee_per_unit_hedge,
                )

            notional = signed_vol * price

            # Update cash & inventory
            cash -= notional          # buying -> negative notional; selling -> positive
            cash -= cost              # always pay costs
            inventory[ticker] += signed_vol

        # 2) Mark-to-market inventory at current_date
        port_val = 0.0
        for ticker, qty in inventory.items():
            if ticker in prices.columns:
                port_val += qty * prices.loc[current_date, ticker]

        equity[current_date] = cash + port_val

    return equity
