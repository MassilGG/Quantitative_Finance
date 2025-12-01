''' store quotes '''
import numpy as np

def fixed_quote(current_price, base_spread):
    """
    Compute fixed quote based on inventory.
    
    Args:
        current_price (float): current mid/close price
        base_spread (float): base spread (as fraction of price, e.g. 0.02 = 2%)
        
    Returns:
        (bid_price, offer_price)
    """
    spread = current_price * base_spread  
    bid_price = current_price - spread/2
    offer_price = current_price + spread/2
    return bid_price, offer_price



def skewed_quote(current_price, base_spread, inventory,
                 inventory_ideal_size, sensitivity, max_skew):
    """
    Compute skewed quote based on inventory.
    
    Args:
        current_price (float): current mid/close price
        base_spread (float): base spread (as fraction of price, e.g. 0.02 = 2%)
        inventory (float): current inventory in $ (position_volume * price)
        inventory_ideal_size (float): $ inventory level you're comfortable with
        sensitivity (float): how aggressively you react to inventory
        max_skew (float): max skew (as fraction of price, e.g. 0.02 = 2%)
        
    Returns:
        (bid_price, offer_price)
    """
    raw_skew = sensitivity * inventory / inventory_ideal_size
    skew = current_price * max_skew * np.tanh(raw_skew)
    spread = current_price * base_spread  
    
    bid_price = current_price + skew - spread/2
    offer_price = current_price + skew + spread/2
    return bid_price, offer_price
