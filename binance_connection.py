from binance.spot import Spot as Client
from dotenv import load_dotenv
import os 
import pandas as pd

class CreateConnection:
    def __init__(self):
        self._api_key = None
        self._api_secret = None
        
    def load_env(self):
        load_dotenv()
        self._api_key = os.getenv('API_KEY')
        self._api_secret = os.getenv('API_SECRET')

    def auth(self):
        try:
            self.load_env()
            _client = Client(self._api_key, self._api_secret)
            return _client
        except Exception as e:
            print(f"Authentication failed: {e}")
            return None

class DataDownloader:
    def __init__(self, symbol, interval, limit):
        self.symbol = symbol
        self.interval = interval
        self.limit = limit
        self._client = CreateConnection().auth()
        
    def download_data(self):
        if self._client is None:
            return None
        try:
            _klines = self._client.klines(self.symbol, self.interval, limit = self.limit)
            data = pd.DataFrame(_klines)
            data.columns = ['Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Kline_Close_time', 'Quote_Asset_Volume', 'Nr_Trades', 'Taker_Buy_Asset_Vol', 'Taker_Buy_Q_Vol', 'Flag']
            data = data.drop(['Kline_Close_time', 'Quote_Asset_Volume', 'Nr_Trades', 'Taker_Buy_Asset_Vol', 'Taker_Buy_Q_Vol', 'Flag'], axis = 1)
            data['Date'] = pd.to_datetime(data.Open_Time, unit = 'ms')
            data[[ 'Open', 'High', 'Low', 'Close']] = data[[ 'Open', 'High', 'Low', 'Close']].apply(pd.to_numeric)
            return data 
        except Exception as e:
            print(f"Data download failed: {e}")
            return None