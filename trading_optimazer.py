import pandas as pd
from sklearn.model_selection import ParameterGrid

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