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


class MeanReversionStrategy:
    def __init__(self, symbol, start_date, end_date, fast_window = 20, slow_window = 50) -> None:
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.data = None

    def download_data(self):
        self.data = yf.download(self.symbol, start = self.start_date, end = self.end_date)
        return self.data 
    
    def generate_signals(self):
        self.data['Fast_MA'] = self.data['Close'].rolling(window = self.fast_window).mean()
        self.data['Slow_MA'] = self.data['Close'].rolling(window = self.slow_window).mean()

        # Create a new column to signal when to enter or exit the market
        self.data['Signal'] = 0  # 0 indicates no action

        # Generate signals based on moving average crossovers
        self.data.loc[self.data['Fast_MA'] > self.data['Slow_MA'], 'Signal'] = -1  # Short signal
        self.data.loc[self.data['Fast_MA'] < self.data['Slow_MA'], 'Signal'] = 1   # Long signal

    def calculate_return(self):
        # Calculate daily returns
        self.data['Daily_Return'] = self.data['Close'].pct_change()

        # Apply the signals to calculate strategy returns
        self.data['Strategy_Return'] = self.data['Signal'].shift(1) * self.data['Daily_Return']

        # Calculate cumulative returns
        self.data['Cumulative_Strategy_Return'] = (1 + self.data['Strategy_Return']).cumprod()

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
        self.download_data()
        self.generate_signals()
        self.calculate_return()


def Main():

    # Download historical stock price data
    symbol = "AAPL"
    start_date = "2022-10-01"
    end_date = "2023-01-01"

    mrs = MeanReversionStrategy(symbol, start_date, end_date)
    mrs.run_strategy()
    mrs.draw_plot()
    mrs.save_to_file()

if __name__ == "__main__":
    Main()