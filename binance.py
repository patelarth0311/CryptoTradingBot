from ast import ExceptHandler
import urllib.parse
import hashlib
import hmac
import base64
import requests
import time
from enum import Enum
import ccxt
from pprint import pprint
import pandas as pd
import matplotlib.pyplot as plt
import os

### WORK IN PROGRESS


def engage_binance_client():
    binanceUS = 'binanceus'
    exchange_class = getattr(ccxt, binanceUS)
    exchange = exchange_class({
    'apiKey': os.getenv('API_KEY'),
    'secret': os.getenv('API_SECRET'),
    })
    return exchange

client = engage_binance_client()

def create_ohlcv_df(timeframe: str):
    
    candles = client.fetch_index_ohlcv('BTCUSDT', timeframe=timeframe)
# https://github.com/ccxt/ccxt/blob/19e13b5867311107ad119ad1f35d90fd2ffc6cc3/python/ccxt/base/exchange.py
    for i in candles:
        del i[-1]

    df = pd.DataFrame (candles, columns = ['date', 'open','high','low','close'])
    df.set_index('date', inplace=True)
    df.index = pd.to_datetime(df.index, unit='ms')
    return df

#MACD
def macd(df):
    macd_df = pd.DataFrame()
    macd_df['ema_12'] = df['close'].ewm(span=12,adjust=False).mean()
    macd_df['ema_26'] = df['close'].ewm(span=26,adjust=False).mean()
    macd_df['macd'] = macd_df['ema_12'] - macd_df['ema_26']
    macd_df['signal'] = macd_df['macd'].ewm(span=9,adjust=False).mean()
    macd_df['histogram'] = macd_df['macd'] - macd_df['signal']
    return macd_df

#RSI
def rsi(df):
    rsi_df = pd.DataFrame()
    close_delta = df['close'].diff()
    positive_delta = close_delta.clip(lower=0)
    negative_delta = close_delta.clip(upper=0) * -1
    ema_up = positive_delta.ewm(com=13, adjust=True, min_periods = 14).mean()
    ema_down = negative_delta.ewm(com=13, adjust=True, min_periods = 14).mean()
    rs = ema_up/ema_down
    rsi = 100 - (100/(1 + rs))
    rsi_df['rsi'] =  rsi 
    return rsi_df

#EMA200
def ema_200(df):
    ema_200_df = pd.DataFrame()
    ema_200_df['ema_200'] = df['close'].ewm(span=200,adjust=False).mean()
    return ema_200_df

#combining df
def aggregate_df(timeframe: str):
    df = create_ohlcv_df(timeframe)
    df = df.join(other = [rsi(df),macd(df),ema_200(df)], how = "inner")

    return df

# Take a long when EMA fast is above EMA slow and both are below the zero line
# and when the candle closes above 200 EMA 
def check_buying_conditions(timeframe: str):
    latest_timeframe_entry_df = aggregate_df(timeframe).tail(1)
    below_zero = latest_timeframe_entry_df.macd[0] < 0 and latest_timeframe_entry_df.signal[0]  < 0
    macd_greater = latest_timeframe_entry_df.macd[0] > latest_timeframe_entry_df.signal[0] 
    closed_above_ema_200 = latest_timeframe_entry_df.close[0] > latest_timeframe_entry_df.ema_200[0]
    rsi_oversold = latest_timeframe_entry_df.rsi[0] < 30
    return latest_timeframe_entry_df, (below_zero and macd_greater and closed_above_ema_200 and rsi_oversold)

def take_order():

    latest_timeframe_entry_df, check_4hr_timeframe = check_buying_conditions('4h')
    latest_timeframe_entry_df, check_2hr_timeframe = check_buying_conditions('2h')

    params = {
         'stopPrice' : latest_timeframe_entry_df.close[0] * .90
    }
    
    if check_4hr_timeframe or check_2hr_timeframe:
        client.create_order('BTCUSDT', 'STOP_LOSS', 'BUY', amount = (client.fetch_balance() * .20), params = params)

    
    



#df['MACD'].plot()
#df['histogram'].plot()
#ax = df['signal'].plot()
#df['close'].plot(ax=ax,secondary_y=True)
#df['ema_200'].plot()
#df['rsi'].plot()
#plt.show()