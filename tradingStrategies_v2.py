
import pandas as pd
import matplotlib.pyplot as plt
from binance.spot import Spot as Client
from dotenv import load_dotenv
from datetime import date
import os
from sklearn.model_selection import ParameterGrid

def save_to_file(data, symbol):
    date_ = date.today()
    data.to_csv(f"MRS_{symbol}_{date_}.csv")

def stop_loss_signal(buy_price, stop_loss_pct):
        stop_loss_price = buy_price * (1 - stop_loss_pct / 100)
        return stop_loss_price

def death_cross_signal(fast_ma, slow_ma):
    return fast_ma < slow_ma 

def golden_cross_signal(fast_ma, slow_ma):
    return fast_ma > slow_ma 

class TradingStrategyOptimizer:
    def __init__(self, data, symbol, investment, strategy_class):
        self.data = data
        self.symbol = symbol
        self.investment = investment
        self.strategy_class = strategy_class

    def evaluate_strategy(self, fast_window, slow_window, stop_loss_pct):
        strategy = self.strategy_class(self.symbol, self.data, self.investment, fast_window, slow_window, stop_loss_pct)
        strategy.run_strategy()
        return strategy.fetch_performance()
    
    def grid_search(self, param_grid):
        grid = ParameterGrid(param_grid)
        results_df = pd.DataFrame(columns=['Stop_Loss_PCT', 'Fast_MA', 'Slow_MA', 'Performance_Metric'])

        index = 0
        for params in grid:
            index += 1
            stop_loss_pct = params['Stop_Loss_PCT']
            fast_ma = params['Fast_MA']
            slow_ma = params['Slow_MA']
     
            performance_metric = self.evaluate_strategy(fast_window = fast_ma, slow_window = slow_ma, stop_loss_pct = stop_loss_pct)

            performance_dict = {
                'index': index,
                'Stop_Loss_PCT': stop_loss_pct,
                'Fast_MA': fast_ma,
                'Slow_MA': slow_ma,
                'Performance_Metric': performance_metric
            }
            performance_df = pd.DataFrame(performance_dict, index = [0])
            results_df = pd.concat([results_df, performance_df], ignore_index = True)

        results_df = results_df.drop(['index'], axis = 1)
        results_df = results_df.sort_values(by = ['Performance_Metric'], ascending = False, ignore_index=True)

        return results_df

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
    
class ReturnCalculator:
    def __init__(self, data, investment):
        self.data = data
        self.investment = investment
        self._initial_investment = investment

    def _calc_return(self, original_price, current_price):
        return_price = (current_price-original_price)/original_price
        return return_price
    
    def calc_performance(self):
        performance_dic = {}
        meta_data_dic = {}
        meta_data_lst = []
        
        # net profit
        last_profit_index = self.data[self.data['Profit'].notna() & (self.data['Profit'] != 0)].last_valid_index()
        last_profit = self.data.at[last_profit_index, 'Profit']
        net_profit = last_profit - self._initial_investment

        # win ratio
        count_winners_condition = (self.data['Return_PCT'] > 0)
        count_total_condition = (self.data['Signal'] == 'Sold')

        count_winners_total = count_total_condition.sum()
        count_winners = count_winners_condition.sum()
        win_ratio = count_winners / count_winners_total
        
        # storing data
        meta_data_dic['_initial_investment'] = self._initial_investment
        meta_data_dic['last_profit'] = last_profit
        meta_data_lst.append(meta_data_dic)

        performance_dic['meta_data'] = meta_data_lst
        performance_dic['net_profit'] = net_profit
        performance_dic['win_ratio'] = win_ratio

        return performance_dic

    def calculate_return(self):

        self.data['Buying_Value'] = 0
        self.data['Selling_Value'] = 0
        self.data['Return_PCT'] = 0
        self.data['Investment'] = 0
        self.data['Profit'] = 0

        for index, row in self.data.iterrows():
            
            if row['Signal'] == 'Bought':
                current_price = row['Close']
                self.data.loc[index, 'Buying_Value'] = current_price
                self.data.loc[index, 'Investment'] = self.investment

                self._return_Index = index
                

            elif row['Signal'] == 'Sold':
                current_price = row['Close']
                original_price = self.data.loc[self._return_Index, 'Close']
                investment_amount = self.investment 
                return_pct = self._calc_return(original_price, current_price)
                profit = investment_amount * return_pct
                total_budget = profit + investment_amount

                self.data.loc[index, 'Selling_Value'] = current_price
                self.data.loc[index, 'Return_PCT'] = return_pct
                self.data.loc[index, 'Profit'] = total_budget

                self.investment = total_budget
        
class MeanReversionStrategy:
   
    def __init__(self, symbol, data, investment, fast_window, slow_window, stop_loss_pct):
        self.symbol = symbol
        self.start_date = None
        self.investment = investment
        self.stop_loss_pct = stop_loss_pct
        self.fast_window = fast_window
        self.slow_window = slow_window
        self._buy = True
        self._sell = False
        self.data = data
        self._return_Index = 0

    def generate_signals(self):

        self.data = self.data.copy()

        self.data['Fast_MA'] = self.data['Close'].rolling(window = self.fast_window).mean()
        self.data['Slow_MA'] = self.data['Close'].rolling(window = self.slow_window).mean()

        #The analyzis start when we have all of the data 
        self.data = self.data[self.data['Slow_MA'].notna()]

        self.data.reset_index(inplace=True)
        self.data['Index'] = self.data.index
        
        #Golden Cross: A bullish signal is generated when a short-term moving average crosses above a long-term moving average
        #Death Cross:A bearish signal is generated when a short-term moving average crosses below a long-term moving average.

        for index, row in self.data.iterrows():
            self._close_price = row['Close']
            self._fast_ma = row['Fast_MA']
            self._slow_ma = row['Slow_MA']
            self._stop_loss_price = stop_loss_signal(self._close_price, self.stop_loss_pct)
            self._golden_cross = golden_cross_signal(self._fast_ma, self._slow_ma)
            self._death_cross = death_cross_signal(self._fast_ma, self._slow_ma)

            if self._buy and (self._golden_cross or self._close_price > self._fast_ma):
                
                self.data.loc[index, 'Signal'] = 'Bought'
                self._buy = False
                self._sell = True
                self._buy_price = self._close_price

            elif self._sell and ((self._death_cross or self._close_price < self._fast_ma) or self._close_price < self._stop_loss_price) :
                self.data.loc[index, 'Signal'] = 'Sold'
                self._buy = True
                self._sell = False

            elif self._sell:
                self.data.loc[index, 'Signal'] = 'Hold'

            else:
                self.data.loc[index, 'Signal'] = 'Waiting to Buy'


    def calculate_return(self):
        return_calculater = ReturnCalculator(self.data, self.investment)
        return_calculater.calculate_return()
        

    def fetch_performance(self):
        return_calculater = ReturnCalculator(self.data, self.investment)
        
        performance_metric = return_calculater.calc_performance()
        return performance_metric['net_profit']

    def draw_roi_plot(self):

        rolling_return = self.data['Return_PCT'].cumsum()
        plt.figure(figsize=(12, 6))
        plt.plot(self.data['Date'], self.data['Return_PCT'], label='Return PCT', alpha=0.7)
        plt.plot(self.data['Date'], rolling_return, label='Total Return PCT', alpha=0.7, linestyle='--')

        plt.legend()
        plt.show()
       
    def draw_plot(self):
   
        plt.figure(figsize=(12, 6))
        plt.plot(self.data['Date'], self.data['Close'], label='Close Price', alpha=0.7)
        plt.plot(self.data['Date'], self.data['Fast_MA'], label=f'{self.fast_window}-Day MA', linestyle='-.')
        plt.plot(self.data['Date'], self.data['Slow_MA'], label=f'{self.slow_window}-Day MA', linestyle='--')

        plt.scatter(self.data.loc[self.data['Signal'] == 'Bought', 'Date'], self.data.loc[self.data['Signal'] == 'Bought', 'Close'], marker='^', color='g', label='Buy', alpha=1)
        plt.scatter(self.data.loc[self.data['Signal'] == 'Sold', 'Date'], self.data.loc[self.data['Signal'] == 'Sold', 'Close'], marker='v', color='r', label='Sell', alpha=1)

        plt.title(f'Mean Reversion Strategy for {self.symbol}')
        plt.legend()
        plt.show()

    def save_data(self):
        save_to_file(self.data, self.symbol)

    def run_strategy(self):
        self.generate_signals()
        self.calculate_return()
        


def Main():

    # Download historical stock price data
    symbol = 'BTCUSDT'
    interval = '1m'
    limit = 1000
    investment = 100

    #stop_loss_pct = 10
    #fast_window = 8
    #slow_window = 30

    downloader = DataDownloader(symbol, interval, limit)
    data = downloader.download_data()
    #print(data)
    param_grid = {
        'Stop_Loss_PCT': [1, 3, 5, 10],
        'Fast_MA': [4, 5, 8, 12],
        'Slow_MA': [18, 21, 30, 35, 40]
    }

    optimizer = TradingStrategyOptimizer(data=data, symbol=symbol, investment=investment, strategy_class=MeanReversionStrategy)
    results = optimizer.grid_search(param_grid)
    print(results)
    #print(data)
    #mrs = MeanReversionStrategy(data=data, symbol=symbol, investment=investment, fast_window=fast_window, slow_window=slow_window, stop_loss_pct=10)
    #mrs.run_strategy()
    #mrs.draw_roi_plot()
    #mrs.draw_plot()
    #mrs.save_data()
if __name__ == "__main__":
    Main()