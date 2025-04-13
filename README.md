# Plutus Project Template

Template repository of a Plutus Project.

This templte project sturcture also specifies how to store and structure the source code and report of a standard Plutus Project.

This `README.md` file serves as an example how a this will look like in a standard Plutus project. Below listed out the sample section.

## Abstract
<!-- - Summarize the project: motivation, methods, findings, etc.  -->
This project develops and evaluates trading algorithms for VN30F1M futures, a derivative tied to Vietnam’s VN30 index, aiming to achieve consistent profitability in dynamic market conditions. Two strategies are implemented: an original algorithm using fixed parameters for the Moving Average Convergence Divergence (MACD), Relative Strength Index (RSI), and Average True Range (ATR) indicators, and a dynamic variant that adjusts ATR-based risk levels based on short-term versus long-term volatility. Historical data from 2020 to 2024 is utilized, with in-sample testing (2020–2023) for strategy development and out-of-sample testing (2024) for validation. Through grid search optimization, key parameters are tuned to maximize returns while controlling risk. Results indicate that both strategies generate positive returns, with the dynamic algorithm outperforming the original by adapting to volatility shifts, achieving higher Holding Period Returns (HPR) and lower Maximum Drawdowns (MDD). The findings suggest that volatility-adaptive strategies enhance trading performance, though success remains sensitive to market trends, highlighting the need for ongoing refinement.

## Introduction
<!-- - Briefly introduce the project.
- Problem statement, research question or the hypothesis.
- Method(s) to solve the problem
- What are the results? -->

The VN30F1M futures contract, representing leveraged exposure to Vietnam’s VN30 index, offers significant opportunities for systematic trading due to its liquidity and volatility. This project aims to design and backtest trading algorithms that exploit price movements in VN30F1M futures while managing risk effectively. The central research question is: *Can a combination of MACD, RSI, and ATR indicators form a robust trading strategy that outperforms a buy-and-hold approach across diverse market conditions?*

To address this, two algorithmic strategies are developed. The original strategy employs fixed parameters to generate trading signals based on MACD for trend detection, RSI for momentum confirmation, and ATR for setting stop-loss and take-profit levels. The dynamic strategy enhances this by adjusting ATR multipliers according to volatility trends, aiming to improve adaptability.

Preliminary results show that both strategies yield positive returns, with the dynamic variant demonstrating superior performance due to its responsiveness to market volatility. Optimized parameters enhance profitability, though performance varies with market conditions, suggesting potential for further improvements through adaptive techniques.


## Related Work (or Background)
<!-- - Prerequisite reading if the audience needs knowledge before exploring the project.
- Optional -->
The development of systematic trading strategies for financial instruments like futures has long been a cornerstone of quantitative finance. This project leverages established principles from technical analysis, futures trading, and algorithmic backtesting, applying them to the VN30F1M futures contract—a monthly derivative tied to Vietnam’s VN30 index. Here, we outline the foundational concepts and prior work that inform our approach, setting the stage for the project’s contributions.

Technical analysis uses historical price and volume data to predict market movements, relying heavily on indicators such as:

- **Moving Average Convergence Divergence (MACD)**: Developed by Gerald Appel in the 1970s, MACD is a trend-following momentum indicator. It calculates the difference between a 12-day and 26-day exponential moving average (EMA), with a 9-day EMA signal line triggering buy or sell signals via crossovers. MACD excels at identifying trend shifts but can lag in volatile conditions.
- **Relative Strength Index (RSI)**: Introduced by J. Welles Wilder in 1978, RSI measures momentum on a 0–100 scale, flagging overbought (above 70) or oversold (below 30) conditions. While effective in range-bound markets, RSI may generate false signals during strong trends.
- **Average True Range (ATR)**: Also by Wilder, ATR measures volatility by averaging the true range over a period (typically 14 days). It’s widely used to set dynamic stop-loss and take-profit levels, adapting to market conditions.
These indicators are often applied individually or in basic pairs. This project, however, integrates MACD for trend detection, RSI for momentum confirmation, and ATR for risk management, creating a more comprehensive framework for trading signals and position sizing.

### Futures Trading and VN30F1M

Futures contracts are agreements to trade an asset at a set price on a future date. The VN30F1M, tied to the VN30 index of the top 30 stocks on the Ho Chi Minh Stock Exchange, is a popular instrument in Vietnam due to its leverage and hedging potential (Ho Chi Minh Stock Exchange, 2023).

While extensive research exists on global futures like the S&P 500, studies on VN30F1M are scarce. Emerging market research suggests volatility-based strategies may thrive in such contexts. This project fills a gap by tailoring technical indicators to VN30F1M, with a focus on volatility adaptation.

### Backtesting Methodologies

Backtesting evaluates trading strategies using historical data, emphasizing:
- **Data Quality**: Clean, bias-free data is critical.
- **Transaction Costs**: Slippage and commissions must be factored.
- **Risk Metrics**: Metrics like Maximum Drawdown and Sharpe Ratio assess performance.

This project follows these principles, using cleaned VN30F1M data, incorporating costs (e.g., taxes), and applying in-sample/out-of-sample testing to ensure robustness and avoid overfitting.

### Algorithmic Trading Strategies

Algorithmic trading spans simple moving average systems to complex learning. Indicator-based strategies remain prevalent for their transparency and practicality. Recent work shows:
- Combining MACD and RSI reduces false signals.
- ATR-based stop-losses enhance risk control in trend strategies.

This project builds on these insights, applying a multi-indicator approach to VN30F1M with a novel twist: a dynamic ATR that adjusts risk based on short- and long-term volatility. This aims to improve performance in Vietnam’s dynamic market.


## Trading (Algorithm) Hypotheses
- Describe the Trading Hypotheses
- Step 1 of the Nine-Step

## Data
- **Data Source**: Historical VN30F1M index data fetched via the `vnstock`, provided by TCBS (Techcom Securities).
- **Data Type**: Daily OHLC (Open, High, Low, Close) prices.
- **Data Period**: January 1, 2020, to January 1, 2025.
  - **In-sample**: 2020-01-01 to 2024-01-01 (for strategy development and optimization).
  - **Out-of-sample**: 2024-01-01 to 2025-01-01 (for validation on unseen data).
- **Input Data**: Data is fetched programmatically via the `Vnstock().stock(symbol="VN30F1M", source="TCBS").quote.history()` function for VN30F1M futures.
- **Output Data**: Processed data stored in pandas DataFrames for analysis and backtesting.
    - **In-memory**: Stored as pandas DataFrames during script execution for efficient computation and analysis.
    - **Persistent Storage**: Saved to Excel files (`in_sample_VN30F1M.xlsx`, `out_sample_VN30F1M.xlsx`) for future use and reference.
### Data collection
- **Process**: The `load_data` function fetches raw OHLC data for VN30F1M via the `vnstock`.
```python
def load_data(symbol, start_date='2020-01-01', end_date='2025-01-01'):
    """
    Load data from vnstock.

    Parameters:
    - symbol (str): Ticker symbol ('VN30F1M' for futures).
    - start_date (str): Start date for data retrieval (format: 'YYYY-MM-DD').
    - end_date (str): End date for data retrieval (format: 'YYYY-MM-DD').

    Returns:
    - data (pd.DataFrame): data with OHLC columns.
    """
    # Initialize vnstock client
    stock = Vnstock().stock(symbol=symbol, source='TCBS')

    # Fetch historical OHLC data
    try:
        data = stock.quote.history(start=start_date, end=end_date)
    except Exception as e:
        raise ValueError(f"Failed to fetch data for {symbol}: {str(e)}")

    return data
```
### Data Processing
- **Steps**:
    - Standardize column names.
    - Convert 'Time' column to datetime and set as index.
    - Remove duplicates and handle missing values.
    - Split into in-sample and out-of-sample.
    - Validate data integrity (no missing OHLC values).
- **Output**: 
    - In-sample data and Out-sample data with OHLC columns.

```python
def process_split_data(data: pd.DataFrame, split_date='2024-01-01'):
    """
    Process and split data for backtesting.

    Parameters:
    - data (pd.DataFrame): Raw data with OHLC columns.
    - split_date (str): Date to split in-sample and out-of-sample data (format: 'YYYY-MM-DD').

    Returns:
    - tuple: (in_sample_df, out_sample_df)
        - in_sample_df (pd.DataFrame): Preprocessed in-sample data with OHLC columns.
        - out_sample_df (pd.DataFrame): Preprocessed out-sample data with OHLC columns.
    """
    # Standardize column names (capitalize first letter)
    data = data.rename(columns=lambda x: x.capitalize())

    # Convert 'Time' column to datetime and set as index
    data['Time'] = pd.to_datetime(data['Time'])
    data = data.sort_values('Time').set_index('Time')

    # Remove duplicates and handle missing values
    data = data.drop_duplicates()
    data = data.dropna(subset=['Open', 'High', 'Low', 'Close'])

    # Split into in-sample and out-of-sample
    split_timestamp = pd.Timestamp(split_date)
    in_sample = data[data.index < split_timestamp]
    out_sample = data[data.index >= split_timestamp]

    # Validate data integrity (no missing OHLC values)
    required_columns = ['Open', 'High', 'Low', 'Close']
    for df in [in_sample, out_sample]:
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Missing required columns in data: {required_columns}")

    return in_sample, out_sample
```


| In-sample Data Graph | Out-sample Data Graph |
|:---------------------------------------:|:---------------------------------------:|
| ![In-sample Data Graph](images/in_sample_original.png){ width=400 } | ![Out-sample Dynamic Graph](images/out_sample_original.png){ width=400 } |



## Implementation
- Briefly describe the implemetation.
    - How to set up the enviroment to run the source code and required steps to replicate the results
    - Discuss the concrete implementation if there are any essential details
    - How to run each step from `In-sample Backtesting`, Step 4 to `Out-of-sample Backtesting`, Step 6 (or `Paper Trading`, Step 7).
    - How to change the algorithm configurations for different run.
- Most important section and need the most details to correctly replicate the results.

## In-sample Backtesting
- Describe the In-sample Backtesting step
    - Parameters
    - Data
- Step 4 of the Nine-Step
### In-sample Backtesting Result
- Brieftly shown the result: table, image, etc.
- Has link to the In-sample Backtesting Report

## Optimization
- Describe the Optimization step
    - Optimization process/methods/library
    - Parameters to optimize
    - Hyper-parameter of the optimize process
- Step 5 of the Nine-Step
### Optimization Result
- Brieftly shown the result: table, image, etc.
- Has link to the Optimization Report

## Out-of-sample Backtesting
- Describe the Out-of-sample Backtesting step
    - Parameter
    - Data
- Step 6 of th Nine-Step
### Out-of-sample Backtesting Reuslt
- Brieftly shown the result: table, image, etc.
- Has link to the Out-of-sample Backtesting Report

## Paper Trading
- Describe the Paper Trading step
- Step 7 of the Nine-Step
- Optional
### Optimization Result
- Brieftly shown the result: table, image, etc.
- Has link to the Paper Trading Report


## Conclusion
- What is the conclusion?
- Optional

## Reference
- All the reference goes here.

## Other information
- Link to the Final Report (Paper) should be somewhere in the `README.md` file.
- Please make sure this file is relatively easy to follow.
