
import pandas as pd
import yfinance as yf 
import matplotlib.pyplot as plt


def save_to_file(data, symbol, start_date, end_date):
    data.to_csv(f"MRS_{symbol}_{start_date}_{end_date}.csv")

def stop_loss_signal(buy_price, stop_loss_pct):
        stop_loss_price = buy_price * (1 - stop_loss_pct / 100)
        return stop_loss_price

def death_cross_signal(fast_ma, slow_ma):
    return fast_ma < slow_ma 

def golden_cross_signal(fast_ma, slow_ma):
    return fast_ma > slow_ma 

class DataDownloader:
    def __init__(self, symbol, start_date, end_date):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date

    def download_data(self):
        data = yf.download(self.symbol, start = self.start_date, end = self.end_date)
        return data 
    
class ReturnCalculator:
    def __init__(self, data, investment):
        self.data = data
        self.investment = investment

    def calc_return(self, original_price, current_price):
        return_price = (current_price-original_price)/original_price
        return return_price
    
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
                return_pct = self.calc_return(original_price, current_price)
                profit = investment_amount * return_pct
                total_budget = profit + investment_amount

                self.data.loc[index, 'Selling_Value'] = current_price
                self.data.loc[index, 'Return_PCT'] = return_pct
                self.data.loc[index, 'Profit'] = total_budget

                self.investment = total_budget
        
class MeanReversionStrategy:
    def __init__(self, symbol, start_date, end_date, data, investment, stop_loss_pct = 5, fast_window = 20, slow_window = 100):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
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

        self.data = self.data.drop(columns=['Open', 'High', 'Low', 'Adj Close'])

    def calculate_return(self):
        ReturnCalculator(self.data, self.investment).calculate_return()

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

    def run_strategy(self):
        self.generate_signals()
        self.calculate_return()
        save_to_file(self.data, self.symbol, self.start_date, self.end_date)


def Main():

    # Download historical stock price data
    symbol = "AAPL"
    start_date = "2022-01-01"
    end_date = "2023-01-01"
    investment = 100

    data = DataDownloader(symbol, start_date, end_date).download_data()
    mrs = MeanReversionStrategy(data=data, symbol=symbol, start_date=start_date, end_date=end_date, investment=investment)
    mrs.run_strategy()
    mrs.draw_roi_plot()
    #mrs.draw_plot()

if __name__ == "__main__":
    Main()