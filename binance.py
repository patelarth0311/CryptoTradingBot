"""Crypto Trading Bot- engages with the BinanceUS API to
execute orders based on favorable market conditions-
that being: For buying (1) MACD and Signal Line is less than zero,
(2) MACD is greater than Signal Line, (3) currency closed above the ema 200;
and for selling, the opposite is expected to occurr."""
import os
import ccxt
import pandas as pd
from dotenv import load_dotenv



### WORK IN PROGRESS


def engage_binance_client() -> ccxt.binanceus.binanceus:
    """Establish connection with BinanceUSD"""
    load_dotenv()
    binance_us = 'binanceus'
    exchange_class = getattr(ccxt, binance_us)
    exchange = exchange_class({
    'apiKey': os.getenv('API_KEY'),
    'secret': os.getenv('API_SECRET')
    })
    return exchange

client = engage_binance_client()

def create_ohlcv_df(timeframe: str) -> pd.DataFrame:
    """Returns dataframe representative of the historical data"""
    candles = client.fetch_index_ohlcv('BTCUSDT', timeframe=timeframe)
# https://github.com/ccxt/ccxt/blob/19e13b5867311107ad119ad1f35d90fd2ffc6cc3/python/ccxt/base/exchange.py
    for i in candles:
        del i[-1]
    d_f = pd.DataFrame (candles, columns = ['date', 'open','high','low','close'])
    d_f.set_index('date', inplace=True)
    d_f.index = pd.to_datetime(d_f.index, unit='ms')
    return d_f

#MACD
def macd(d_f: pd.DataFrame) -> pd.DataFrame:
    """Returns dataframe representative of the macd"""
    macd_df = pd.DataFrame()
    macd_df['ema_12'] = d_f['close'].ewm(span=12,adjust=False).mean()
    macd_df['ema_26'] = d_f['close'].ewm(span=26,adjust=False).mean()
    macd_df['macd'] = macd_df['ema_12'] - macd_df['ema_26']
    macd_df['signal'] = macd_df['macd'].ewm(span=9,adjust=False).mean()
    macd_df['histogram'] = macd_df['macd'] - macd_df['signal']
    return macd_df

#RSI
def rsi(d_f: pd.DataFrame) -> pd.DataFrame:
    """Returns dataframe representative of a rsi"""
    rsi_df = pd.DataFrame()
    close_delta = d_f['close'].diff()
    positive_delta = close_delta.clip(lower=0)
    negative_delta = close_delta.clip(upper=0) * -1
    ema_up = positive_delta.ewm(com=13, adjust=True, min_periods = 14).mean()
    ema_down = negative_delta.ewm(com=13, adjust=True, min_periods = 14).mean()
    r_s = ema_up/ema_down
    rsi_value = 100 - (100/(1 + r_s))
    rsi_df['rsi'] =  rsi_value
    return rsi_df

#EMA200
def ema_200(d_f: pd.DataFrame) -> pd.DataFrame:
    """Returns dataframe representative of an ema_200"""
    ema_200_df = pd.DataFrame()
    ema_200_df['ema_200'] = d_f['close'].ewm(span=200,adjust=False).mean()
    return ema_200_df

#combining d_f
def aggregate_df(timeframe: str) -> pd.DataFrame:
    """Aggregates dataframes returned by rsi, macd, and emma_200 by an inner join"""
    d_f = create_ohlcv_df(timeframe)
    d_f = d_f.join(other = [rsi(d_f),macd(d_f),ema_200(d_f)], how = "inner")

    return d_f

# Take a long when EMA fast is above EMA slow and both are below the zero line
# and when the candle closes above 200 EMA
def check_buying_conditions(timeframe: str) -> tuple([pd.DataFrame, bool]):
    """Returns latest row from the dataframe returned
    from aggregated_df and a boolean indiciative of an existence of flavorable buying conditions"""
    latest_timeframe_entry_df = aggregate_df(timeframe).tail(1)
    below_zero = latest_timeframe_entry_df.macd[0] < 0 and latest_timeframe_entry_df.signal[0]  < 0
    macd_greater = latest_timeframe_entry_df.macd[0] > latest_timeframe_entry_df.signal[0]
    closed_above_ema_200 = latest_timeframe_entry_df.close[0] > latest_timeframe_entry_df.ema_200[0]
    rsi_oversold = latest_timeframe_entry_df.rsi[0] < 30
    return latest_timeframe_entry_df, (below_zero and macd_greater
    and closed_above_ema_200 and rsi_oversold)

def get_balance() -> float:
    """Checks for available USDT"""
    balance = 0
    for available in client.fetch_balance()['info']['balances']:
        if available['asset'] == 'USDT':
            balance = (available['free'])
            break
    return balance

def take_order() -> None:
    """Checks if desired buying condiitions are true. If so, BINANCEUS's create_order is executed"""
    latest_timeframe_entry_df, check_4hr_timeframe = check_buying_conditions('4h')
    latest_timeframe_entry_df, check_2hr_timeframe = check_buying_conditions('2h')
    balance = float(get_balance())
    stop_price = latest_timeframe_entry_df.close[0] * .90
    #quantity = balance * .20
    params = {
        'stopPrice' : stop_price,
    }
    if  check_4hr_timeframe or check_2hr_timeframe:
        client.create_order( symbol = 'BTCUSDT',  type = 'STOP_LOSS_LIMIT',
        side = 'buy', price = latest_timeframe_entry_df.close[0],
        amount = (balance * .20), params = params)
#d_f['MACD'].plot()
#d_f['histogram'].plot()
#ax = d_f['signal'].plot()
#d_f['close'].plot(ax=ax,secondary_y=True)
#d_f['ema_200'].plot()
#d_f['rsi'].plot()
#plt.show()
