import os
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf 
import matplotlib.pyplot as plt


# Load environment variables from the .env file
load_dotenv()

# Access the variables
api_key = os.getenv('API_KEY')
database_url = os.getenv('DATABASE_URL')

def calc_return(original_price, current_price):
    return_price = (current_price-original_price)/original_price
    return return_price

class DataDownloader:
    def __init__(self, symbol, start_date, end_date):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date

    def download_data(self):
        data = yf.download(self.symbol, start = self.start_date, end = self.end_date)
        return data 

class MeanReversionStrategy:
    def __init__(self, symbol, start_date, end_date, investment, fast_window = 20, slow_window = 40):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.investment = investment
        self.fast_window = fast_window
        self.slow_window = slow_window
        self._buy = True
        self._sell = False
        self.data = DataDownloader(self.symbol, self.start_date, self.end_date).download_data()
        self._return_Index = 0

    def generate_signals(self):

        self.data['Fast_MA'] = self.data['Close'].rolling(window = self.fast_window).mean()
        self.data['Slow_MA'] = self.data['Close'].rolling(window = self.slow_window).mean()

        for index, row in self.data.iterrows():
            if self._buy and row['Fast_MA'] > row['Slow_MA']:
                
                self.data.loc[index, 'Signal'] = 'Bought'
                self._buy = False
                self._sell = True

            elif self._sell and row['Fast_MA'] < row['Slow_MA']:
                self.data.loc[index, 'Signal'] = 'Sold'
                self._buy = True
                self._sell = False

            elif self._sell:
                self.data.loc[index, 'Signal'] = 'Hold'

            else:
                self.data.loc[index, 'Signal'] = 'Waiting to Buy'

        self.data = self.data.drop(columns=['Open', 'High', 'Low', 'Adj Close'])

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
                investment_amount = self.investment #self.data.loc[self._return_Index, 'Investment']
                return_pct = calc_return(original_price, current_price)
                profit = investment_amount * return_pct
                total_budget = profit + investment_amount

                self.data.loc[index, 'Selling_Value'] = current_price
                self.data.loc[index, 'Return_PCT'] = return_pct
                self.data.loc[index, 'Profit'] = total_budget

                self.investment = total_budget
                

    def draw_plot(self):
        plt.figure(figsize=(12, 6))
        plt.plot(self.data['Close'], label='Close Price', alpha=0.7)
        plt.plot(self.data['Fast_MA'], label=f'{self.fast_window}-Day MA', linestyle='-.')
        plt.plot(self.data['Slow_MA'], label=f'{self.slow_window}-Day MA', linestyle='--')
        plt.title(f'Mean Reversion Strategy for {self.symbol}')
        plt.legend()
        plt.show()

    def save_to_file(self):
        self.data.to_csv(f"MRS_{self.symbol}_{self.start_date}_{self.end_date}.csv")

    def run_strategy(self):
        self.generate_signals()
        self.calculate_return()


def Main():

    # Download historical stock price data
    symbol = "AAPL"
    start_date = "2022-01-01"
    end_date = "2023-01-01"
    investment = 100

    mrs = MeanReversionStrategy(symbol, start_date, end_date, investment)
    mrs.run_strategy()
    # mrs.draw_plot()
    mrs.save_to_file()

if __name__ == "__main__":
    Main()