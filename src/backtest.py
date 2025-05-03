import pandas as pd
import ta
from math import floor
import argparse
import json
from utils import (
    ASSET_VALUE, TAX, MARGIN_RATIO, ACCOUNT_RATIO, MULTIPLIER,
    holding_period_returns, maximum_drawdown, longest_drawdown, sharpe_ratio, sortino_ratio
)

def algo(
    data: pd.DataFrame,
    momentum_fast_ema: int,
    momentum_slow_ema: int,
    momentum_signal_ema: int,
    momentum_rsi_window: int,
    momentum_rsi_threshold: int,
    momentum_atr_window: int,
    momentum_atr_multiplier: float,
    reversion_fast_ema: int,
    reversion_slow_ema: int,
    reversion_signal_ema: int,
    reversion_rsi_window: int,
    reversion_atr_window: int,
    reversion_atr_multiplier: float
) -> pd.DataFrame:
    """
    Executes a hybrid trading strategy that allocates capital between Momentum and
    Mean Reversion approaches, using MACD, RSI, and ATR-based conditions for
    position management.

    The algorithm processes historical OHLC data and simulates trading by:
    - Opening and closing positions based on technical indicators.
    - Splitting capital evenly between Momentum and Reversion strategies.
    - Tracking asset value over time, including both cash and unrealized P&L.

    Parameters:
        data (pd.DataFrame): Input dataframe with columns: ['Open', 'High', 'Low', 'Close'].
        momentum_fast_ema (int): Fast EMA period for Momentum MACD calculation.
        momentum_slow_ema (int): Slow EMA period for Momentum MACD calculation.
        momentum_signal_ema (int): Signal line EMA period for Momentum MACD.
        momentum_rsi_window (int): Window length for Momentum RSI.
        momentum_rsi_threshold (int): Threshold for overbought/oversold RSI levels in Momentum strategy.
        momentum_atr_window (int): ATR window size for Momentum stop-loss/take-profit.
        momentum_atr_multiplier (float): Multiplier for ATR-based exit levels in Momentum strategy.
        reversion_fast_ema (int): Fast EMA period for Reversion MACD calculation.
        reversion_slow_ema (int): Slow EMA period for Reversion MACD calculation.
        reversion_signal_ema (int): Signal line EMA period for Reversion MACD.
        reversion_rsi_window (int): Window length for Reversion RSI.
        reversion_atr_window (int): ATR window size for Reversion stop-loss/take-profit.
        reversion_atr_multiplier (float): Multiplier for ATR-based exit levels in Reversion strategy.

    Returns:
        pd.DataFrame: DataFrame indexed by date with columns:
            - 'Asset': Total portfolio value (cash + unrealized P&L) at each timestep.
            - 'Return': Percentage return compared to the previous timestep.
    """
    data = data.copy()
    price_multiplier = MULTIPLIER * MARGIN_RATIO / ACCOUNT_RATIO

    cash = ASSET_VALUE
    holdings_momentum = []
    holdings_reversion = []
    trading_data = pd.DataFrame(index=data.index, columns=['Asset'])
    trading_data['Asset'] = cash
    trading_data['Asset'] = trading_data['Asset'].astype(float)

    # Calculate technical indicators for Momentum
    data['MACD_diff_mom'] = ta.trend.macd_diff(
        data['Close'], window_slow=momentum_slow_ema, window_fast=momentum_fast_ema, window_sign=momentum_signal_ema
    )
    data['RSI_mom'] = ta.momentum.rsi(data['Close'], window=momentum_rsi_window)
    data['ATR_mom'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window=momentum_atr_window)

    # Calculate technical indicators for Mean Reversion
    data['MACD_diff_rev'] = ta.trend.macd_diff(
        data['Close'], window_slow=reversion_slow_ema, window_fast=reversion_fast_ema, window_sign=reversion_signal_ema
    )
    data['RSI_rev'] = ta.momentum.rsi(data['Close'], window=reversion_rsi_window)
    data['ATR_rev'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window=reversion_atr_window)

    for i in range(1, len(data)):
        row = data.iloc[i]
        if (pd.isna(row['RSI_mom']) or pd.isna(row['MACD_diff_mom']) or pd.isna(row['ATR_mom']) or
            pd.isna(row['RSI_rev']) or pd.isna(row['MACD_diff_rev']) or pd.isna(row['ATR_rev'])
        ): continue
        date = data.index[i]
        cur_price = row['Close']

        # Exit Momentum Positions
        for position in holdings_momentum[:]:
            entry_date, pos_type, entry_price, quantity, stop_loss, take_profit = position
            if pos_type == 'LONG' and (
                cur_price >= take_profit or cur_price <= stop_loss or
                row['RSI_mom'] >= (100 - momentum_rsi_threshold) or row['MACD_diff_mom'] < 0
            ):
                cash += quantity * cur_price * price_multiplier - quantity * TAX * MULTIPLIER
                holdings_momentum.remove(position)
            elif pos_type == 'SHORT' and (
                cur_price <= take_profit or cur_price >= stop_loss or
                row['RSI_mom'] <= momentum_rsi_threshold or row['MACD_diff_mom'] > 0
            ):
                cash -= quantity * cur_price * price_multiplier + quantity * TAX * MULTIPLIER
                holdings_momentum.remove(position)

        # Exit Mean Reversion Positions
        for position in holdings_reversion[:]:
            entry_date, pos_type, entry_price, quantity, stop_loss, take_profit = position
            if pos_type == 'LONG' and (
                cur_price >= take_profit or cur_price <= stop_loss or row['RSI_rev'] >= 50 or row['MACD_diff_rev'] < 0
            ):
                cash += quantity * cur_price * price_multiplier - quantity * TAX * MULTIPLIER
                holdings_reversion.remove(position)
            elif pos_type == 'SHORT' and (
                cur_price <= take_profit or cur_price >= stop_loss or row['RSI_rev'] >= 50 or row['MACD_diff_rev'] > 0
            ):
                cash -= quantity * cur_price * price_multiplier + quantity * TAX * MULTIPLIER
                holdings_reversion.remove(position)

        total_unrealized = sum(
            cur_price * price_multiplier * pos[3] if pos[1] == 'LONG'
            else -cur_price * price_multiplier * pos[3] for pos in holdings_momentum + holdings_reversion
        )
        trading_data.loc[date, 'Asset'] = cash + total_unrealized

        available_cash = cash / 2
        # Momentum Entry Logic
        if not holdings_momentum:
            if row['MACD_diff_mom'] > 0 and 50 < row['RSI_mom'] < (100 - momentum_rsi_threshold):
                quantity = floor(available_cash / (cur_price * price_multiplier))
                if quantity > 0:
                    cash -= quantity * cur_price * price_multiplier
                    stop_loss = cur_price - row['ATR_mom'] * momentum_atr_multiplier
                    take_profit = cur_price + row['ATR_mom'] * momentum_atr_multiplier
                    holdings_momentum.append((date, 'LONG', cur_price, quantity, stop_loss, take_profit))
            elif row['MACD_diff_mom'] < 0 and momentum_rsi_threshold < row['RSI_mom'] < 50:
                quantity = floor(available_cash / (cur_price * price_multiplier))
                if quantity > 0:
                    cash += quantity * cur_price * price_multiplier
                    stop_loss = cur_price + row['ATR_mom'] * momentum_atr_multiplier
                    take_profit = cur_price - row['ATR_mom'] * momentum_atr_multiplier
                    holdings_momentum.append((date, 'SHORT', cur_price, quantity, stop_loss, take_profit))

        # Mean Reversion Entry Logic
        if not holdings_reversion:
            if row['MACD_diff_rev'] > 0 and row['RSI_rev'] < 30:
                quantity = floor(available_cash / (cur_price * price_multiplier))
                if quantity > 0:
                    cash -= quantity * cur_price * price_multiplier
                    stop_loss = cur_price - row['ATR_rev'] * reversion_atr_multiplier
                    take_profit = cur_price + row['ATR_rev'] * reversion_atr_multiplier
                    holdings_reversion.append((date, 'LONG', cur_price, quantity, stop_loss, take_profit))
            elif row['MACD_diff_rev'] < 0 and row['RSI_rev'] > 70:
                quantity = min(floor(available_cash / (cur_price * price_multiplier)), 3)
                if quantity > 0:
                    cash += quantity * cur_price * price_multiplier
                    stop_loss = cur_price + row['ATR_rev'] * reversion_atr_multiplier
                    take_profit = cur_price - row['ATR_rev'] * reversion_atr_multiplier
                    holdings_reversion.append((date, 'SHORT', cur_price, quantity, stop_loss, take_profit))

    trading_data['Return'] = trading_data['Asset'].pct_change()

    return trading_data

def dynamic_algo(
    data: pd.DataFrame,
    momentum_fast_ema: int,
    momentum_slow_ema: int,
    momentum_signal_ema: int,
    momentum_rsi_window: int,
    momentum_rsi_threshold: int,
    momentum_atr_window: int,
    reversion_fast_ema: int,
    reversion_slow_ema: int,
    reversion_signal_ema: int,
    reversion_rsi_window: int,
    reversion_atr_window: int
) -> pd.DataFrame:
    """
    Executes a dynamic hybrid trading strategy combining Momentum and Mean Reversion models,
    driven by MACD, RSI, and ATR indicators.

    This algorithm allocates capital evenly between two strategies: Momentum and Mean Reversion.

    A key feature of this strategy is its adaptive position sizing logic:
    ATR-based stop-loss and take-profit levels are dynamically adjusted at each time step
    depending on short-term vs long-term volatility (measured by short and long ATR windows).
    This allows the system to widen or tighten risk thresholds based on changing market conditions.

    Parameters:
        data (pd.DataFrame): Historical OHLCV data with at least 'High', 'Low', 'Close' columns.
        momentum_fast_ema (int): Fast EMA period for Momentum MACD.
        momentum_slow_ema (int): Slow EMA period for Momentum MACD.
        momentum_signal_ema (int): Signal line EMA period for Momentum MACD.
        momentum_rsi_window (int): RSI window for Momentum strategy.
        momentum_rsi_threshold (int): Threshold used to define RSI extreme zones.
        momentum_atr_window (int): ATR window for base Momentum volatility.
        reversion_fast_ema (int): Fast EMA period for Reversion MACD.
        reversion_slow_ema (int): Slow EMA period for Reversion MACD.
        reversion_signal_ema (int): Signal line EMA period for Reversion MACD.
        reversion_rsi_window (int): RSI window for Reversion strategy.
        reversion_atr_window (int): ATR window for base Reversion volatility.

    Returns:
        pd.DataFrame: Time series of the simulated portfolio, with:
            - 'Asset': Total asset value (cash + unrealized positions).
            - 'Return': Daily percentage change of the asset value.
    """
    data = data.copy()
    price_multiplier = MULTIPLIER * MARGIN_RATIO / ACCOUNT_RATIO

    cash = ASSET_VALUE
    holdings_momentum = []
    holdings_reversion = []
    trading_data = pd.DataFrame(index=data.index, columns=['Asset'])
    trading_data['Asset'] = cash
    trading_data['Asset'] = trading_data['Asset'].astype(float)

    # Calculate technical indicators for Momentum
    data['MACD_diff_mom'] = ta.trend.macd_diff(
        data['Close'], window_slow=momentum_slow_ema, window_fast=momentum_fast_ema, window_sign=momentum_signal_ema
    )
    data['RSI_mom'] = ta.momentum.rsi(data['Close'], window=momentum_rsi_window)
    data['ATR_mom'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window=momentum_atr_window)
    data['ATR_mom_short'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = 10)
    data['ATR_mom_long'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = 20)

    # Calculate technical indicators for Mean Reversion
    data['MACD_diff_rev'] = ta.trend.macd_diff(
        data['Close'], window_slow=reversion_slow_ema, window_fast=reversion_fast_ema, window_sign=reversion_signal_ema
    )
    data['RSI_rev'] = ta.momentum.rsi(data['Close'], window=reversion_rsi_window)
    data['ATR_rev'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window=reversion_atr_window)
    data['ATR_rev_short'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = 7)
    data['ATR_rev_long'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = 14)

    for i in range(1, len(data)):
        row = data.iloc[i]
        if (pd.isna(row['RSI_mom']) or pd.isna(row['MACD_diff_mom']) or pd.isna(row['ATR_mom']) or
            pd.isna(row['RSI_rev']) or pd.isna(row['MACD_diff_rev']) or pd.isna(row['ATR_rev'])
        ): continue
        date = data.index[i]
        cur_price = row['Close']

        # Determine ATR multiplier based on volatility trend
        if row['ATR_mom_short'] > row['ATR_mom_long']:
            momentum_atr_multiplier = 2.0  # Higher volatility → wider SL/TP
        else:
            momentum_atr_multiplier = 2.0  # Lower volatility → tighter SL/TP
        if row['ATR_rev_short'] > row['ATR_rev_long']:
            reversion_atr_multiplier = 2.0  # Higher volatility → wider SL/TP
        else:
            reversion_atr_multiplier = 1.5  # Lower volatility → tighter SL/TP

        # Exit Momentum Positions
        for position in holdings_momentum[:]:
            entry_date, pos_type, entry_price, quantity, stop_loss, take_profit = position
            if pos_type == 'LONG' and (
                cur_price >= take_profit or cur_price <= stop_loss or
                row['RSI_mom'] >= (100 - momentum_rsi_threshold) or row['MACD_diff_mom'] < 0
            ):
                cash += quantity * cur_price * price_multiplier - quantity * TAX * MULTIPLIER
                holdings_momentum.remove(position)
            elif pos_type == 'SHORT' and (
                cur_price <= take_profit or cur_price >= stop_loss or
                row['RSI_mom'] <= momentum_rsi_threshold or row['MACD_diff_mom'] > 0
            ):
                cash -= quantity * cur_price * price_multiplier + quantity * TAX * MULTIPLIER
                holdings_momentum.remove(position)

        # Exit Mean Reversion Positions
        for position in holdings_reversion[:]:
            entry_date, pos_type, entry_price, quantity, stop_loss, take_profit = position
            if pos_type == 'LONG' and (
                cur_price >= take_profit or cur_price <= stop_loss or row['RSI_rev'] >= 50 or row['MACD_diff_rev'] < 0
            ):
                cash += quantity * cur_price * price_multiplier - quantity * TAX * MULTIPLIER
                holdings_reversion.remove(position)
            elif pos_type == 'SHORT' and (
                cur_price <= take_profit or cur_price >= stop_loss or row['RSI_rev'] >= 50 or row['MACD_diff_rev'] > 0
            ):
                cash -= quantity * cur_price * price_multiplier + quantity * TAX * MULTIPLIER
                holdings_reversion.remove(position)

        total_unrealized = sum(
            cur_price * price_multiplier * pos[3] if pos[1] == 'LONG'
            else -cur_price * price_multiplier * pos[3] for pos in holdings_momentum + holdings_reversion
        )
        trading_data.loc[date, 'Asset'] = cash + total_unrealized

        available_cash = cash / 2
        # Momentum Entry Logic
        if not holdings_momentum:
            if row['MACD_diff_mom'] > 0 and 50 < row['RSI_mom'] < (100 - momentum_rsi_threshold):
                quantity = floor(available_cash / (cur_price * price_multiplier))
                if quantity > 0:
                    cash -= quantity * cur_price * price_multiplier
                    stop_loss = cur_price - row['ATR_mom'] * momentum_atr_multiplier
                    take_profit = cur_price + row['ATR_mom'] * momentum_atr_multiplier
                    holdings_momentum.append((date, 'LONG', cur_price, quantity, stop_loss, take_profit))
            elif row['MACD_diff_mom'] < 0 and momentum_rsi_threshold < row['RSI_mom'] < 50:
                quantity = floor(available_cash / (cur_price * price_multiplier))
                if quantity > 0:
                    cash += quantity * cur_price * price_multiplier
                    stop_loss = cur_price + row['ATR_mom'] * momentum_atr_multiplier
                    take_profit = cur_price - row['ATR_mom'] * momentum_atr_multiplier
                    holdings_momentum.append((date, 'SHORT', cur_price, quantity, stop_loss, take_profit))

        # Mean Reversion Entry Logic
        if not holdings_reversion:
            if row['MACD_diff_rev'] > 0 and row['RSI_rev'] < 30:
                quantity = floor(available_cash / (cur_price * price_multiplier))
                if quantity > 0:
                    cash -= quantity * cur_price * price_multiplier
                    stop_loss = cur_price - row['ATR_rev'] * reversion_atr_multiplier
                    take_profit = cur_price + row['ATR_rev'] * reversion_atr_multiplier
                    holdings_reversion.append((date, 'LONG', cur_price, quantity, stop_loss, take_profit))
            elif row['MACD_diff_rev'] < 0 and row['RSI_rev'] > 70:
                quantity = min(floor(available_cash / (cur_price * price_multiplier)), 3)
                if quantity > 0:
                    cash += quantity * cur_price * price_multiplier
                    stop_loss = cur_price + row['ATR_rev'] * reversion_atr_multiplier
                    take_profit = cur_price - row['ATR_rev'] * reversion_atr_multiplier
                    holdings_reversion.append((date, 'SHORT', cur_price, quantity, stop_loss, take_profit))

    trading_data['Return'] = trading_data['Asset'].pct_change()

    return trading_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest a trading strategy using historical data.")
    parser.add_argument('--data', type=str, default='in_sample.csv', help='Path to the CSV file containing OHLC data.')
    parser.add_argument(
        '--dynamic', type=str, choices=['true', 'false'], required=True, help='Type of algorithm: dynamic (true) or non-dynamic(false).'
    )
    parser.add_argument('--params', type=str, required=True, help='Path to the JSON file with strategy parameters.')

    args = parser.parse_args()

    # Load data
    data = pd.read_csv(args.data, index_col=0, parse_dates=True)

    # Load parameters
    with open(args.params, 'r') as f:
        params = json.load(f)

    # Run selected algorithm
    if args.dynamic == 'true':
        result = algo(data, **params)
    else: result = dynamic_algo(data, **params)
    
    print("\n=== Backtest Performance Metrics ===")

    hpr = holding_period_returns(result)
    print(f"Holding Period Return: {hpr:.2f}%")

    try:
        max_dd = maximum_drawdown(result)
        print(f"Maximum Drawdown: {max_dd:.2f}%")
    except Exception as e:
        print(f"Maximum Drawdown: Error - {e}")
    
    try:
        ldd = longest_drawdown(result)
        print(f"Longest Drawdown Duration: {ldd} days")
    except Exception as e:
        print(f"Longest Drawdown: Error - {e}")

    try:
        sharpe = sharpe_ratio(result)
        print(f"Sharpe Ratio: {sharpe:.6f}")
    except Exception as e:
        print(f"Sharpe Ratio: Error - {e}")

    try:
        sortino = sortino_ratio(result)
        print(f"Sortino Ratio: {sortino}")
    except Exception as e:
        print(f"Sortino Ratio: Error - {e}")

    print("====================================\n")