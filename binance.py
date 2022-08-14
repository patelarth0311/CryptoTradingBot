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


### WORK IN PROGRESS

binanceUS = 'binanceus'
exchange_class = getattr(ccxt, binanceUS)
exchange = exchange_class({
    'apiKey': 'qZd0TVwy6nCgxWvRiYoEoOEG9N2lEthcTv7Zbc8xjegLYIg94pDdGcKfoYXibYge',
    'secret': 'uDtR7qHQNooW2OcdITnhj6DWGN78ErLoOYRUP2Fc2YqhG7UuMlnbJ7XOdhjg8jQJ',
})




candles = exchange.fetch_index_ohlcv('BTCUSDT', timeframe='4h')
# https://github.com/ccxt/ccxt/blob/19e13b5867311107ad119ad1f35d90fd2ffc6cc3/python/ccxt/base/exchange.py
for i in candles:
  del i[-1]

df = pd.DataFrame (candles, columns = ['date', 'open','high','low','close'])
df.set_index('date', inplace=True)
df.index = pd.to_datetime(df.index, unit='ms')


#MACD
df['ema_12'] = df['close'].ewm(span=12,adjust=False).mean()
df['ema_26'] = df['close'].ewm(span=26,adjust=False).mean()
df['MACD'] = df['ema_12'] - df['ema_26']
df['signal'] = df['MACD'].ewm(span=9,adjust=False).mean()
df['histogram'] = df['MACD'] - df['signal']

#RSI
close_delta = df['close'].diff()
positive_delta = close_delta.clip(lower=0)
negative_delta = close_delta.clip(upper=0) * -1
ema_up = positive_delta.ewm(com=13, adjust=True, min_periods = 14).mean()
ema_down = negative_delta.ewm(com=13, adjust=True, min_periods = 14).mean()
rs = ema_up/ema_down
rsi = 100 - (100/(1 + rs))
df['rsi'] =  rsi 


# 200 EMA to check if crypto is in a up/down trend
df['ema_200'] = df['close'].ewm(span=200,adjust=False).mean()



#df['MACD'].plot()
#df['histogram'].plot()
#ax = df['signal'].plot()
#df['close'].plot(ax=ax,secondary_y=True)
#df['ema_200'].plot()
#df['rsi'].plot()
#plt.show()



# Take a long when EMA fast is above EMA slow below the zero line
# and when the candle is above 200 EMA 
print(df['MACD'].tail(1))
print(df['signal'].tail(1))
print(df['close'].tail(1))
print(df['ema_200'].tail(1))