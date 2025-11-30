import pandas as pd

def get_quotes_df(mm,ticker_to_plot):
    '''
    Get all generated quotes
    Args:
        mm (MarketMaker Class) - current MM
        ticker_to_plot (str)

    Returns
        quotes_df (date,ref_price,bid_price,offer_price)
    '''
    
    # Extract data from mm.quoted_trades
    records = []
    for qt in mm.quoted_trades:
        if qt.ticker == ticker_to_plot:
            records.append({
                "date": qt.date,
                "ref_price": qt.ref_price,
                "bid_price": qt.bid_price,
                "offer_price": qt.offer_price,
            })
    
    quotes_df = pd.DataFrame(records).sort_values("date").set_index("date")
    return quotes_df

def get_inventory_df(mm,ticker_to_plot):
    '''
    Get running inventory
    Args:
        mm (MarketMaker Class) - current MM
        ticker_to_plot (str)

    Returns
        inventory_df (date,inventory_volume,inventory_value)
    '''
    records_inv = []
    running_inventory = 0.0  # position in *units*, not USD

    for ct in mm.completed_trades:
        if ct.ticker == ticker_to_plot:
            if ct.mm_action == "buy":
                running_inventory += ct.trade_volume
            elif ct.mm_action == "sell":
                running_inventory -= ct.trade_volume

            records_inv.append({
                "date": ct.date,
                "inventory_volume": running_inventory,
                "inventory_value": running_inventory * ct.trade_price
            })

    inventory_df = pd.DataFrame(records_inv).sort_values("date").set_index("date")
    return inventory_df


def get_ETF_inventory_df(mm,ticker_to_plot):
    '''
    Get running inventory
    Args:
        mm (MarketMaker Class) - current MM
        ticker_to_plot (str)

    Returns
        inventory_df (date,inventory_volume,inventory_value)
    '''
    records_inv = []
    running_inventory = 0.0  # position in *units*, not USD

    for ct in mm.ETF_positions:
        if ct.ticker == ticker_to_plot:
            if ct.action == "buy":
                running_inventory += ct.trade_volume
            elif ct.action == "sell":
                running_inventory -= ct.trade_volume

            records_inv.append({
                "date": ct.date,
                "inventory_volume": running_inventory,
                "inventory_value": running_inventory * ct.trade_price
            })

    inventory_df = pd.DataFrame(records_inv).sort_values("date").set_index("date")
    return inventory_df