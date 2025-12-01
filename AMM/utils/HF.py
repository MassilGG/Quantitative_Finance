''' Utilities for HF data analysis'''

import numpy as np
import pandas as pd
from scipy.stats import norm

def vwap(df):
    '''
    Compute Vwap price
    '''
    vol = df['AskVolume'] + df['BidVolume']
    num = df['Ask'] * df['AskVolume'] + df['Bid'] * df['BidVolume']
    tot_vol = vol.sum()
    if tot_vol == 0:
        return np.nan   # no volume in this bin
    return num.sum() / tot_vol
    
def resample(data, T):
    """
    Resample DataFrame on calendar time with VWAP and previous-tick interpolation.

    data : pd.DataFrame with columns ['Time','Bid','BidVolume','Ask','AskVolume']
    T    : sampling period in seconds (int)
    """
    data = data.copy()
    prices_resampled = pd.DataFrame(
                            (data
                            .resample(f'{T}s')
                            .apply(vwap)),
                        columns=['mid']
    )
                
    df_resampled = (
        data.resample(f'{T}s').agg({
            'Bid': 'last',
            'Ask': 'last',
            'BidVolume': 'last',
            'AskVolume': 'last',
            'price': 'last',
            'volume' : 'last',
        })
        .merge(prices_resampled, right_index = True, left_index = True,how='outer')
        .assign(logret=lambda df : (np.log(df['mid'])**2).diff())
        .replace(0, np.nan).ffill() # Replace 0 or NaN by previous value (previous-tick interpolation)
    )
    return df_resampled

def get_vol(data,window_size=50,method='kernel'):
    '''
    Compute spot volatility, 
    data (pd.DataFrame) - price data
    method (string) - method to estimate
    window_size (int) - number of observation to estimate
    '''
    if method == 'MA':
        vol = (
            data['logret'].rolling(window_size)
            .apply(lambda df : (df**2).sum())
            .dropna()
            /window_size
        )
        
    elif method == 'kernel':
        bandwidth = window_size / 6  
        vol = (
            data['logret']
            .rolling(window_size, min_periods=window_size)
            .apply(
                lambda x: (
                    norm.pdf(
                        (x.index.values - x.index.values[len(x)//2]) / bandwidth
                    ) * (x.values**2)
                ).sum()
                /window_size
            )
        )
    return vol*100
