from math import floor
import itertools
import argparse
import pandas as pd
import ta
import tqdm
from utils import (
    ASSET_VALUE, TAX, MARGIN_RATIO, ACCOUNT_RATIO, MULTIPLIER,
    holding_period_returns, maximum_drawdown, longest_drawdown, sharpe_ratio, sortino_ratio
)

def loss_score(hpr: float, mdd: float, ldd: int, sharpe: float, sortino: float) -> float:
    return round(hpr + mdd / 10 - ldd / 100 + ((sharpe + sortino) / 2) ** 3, 6)

def momentum_algo(
    data: pd.DataFrame,
    fast_ema_window: int,
    slow_ema_window: int,
    ema_signal_window: int,
    rsi_window: int,
    rsi_threshold: int,
    atr_window: int,
    atr_multiplier: float
    ) -> pd.DataFrame:
    """
    Executes a momentum-based trading strategy using MACD, RSI, and ATR indicators.

    This algorithm seeks to identify and exploit price trends (momentum) by:
    - Opening positions when MACD and RSI jointly signal trend confirmation.
    - Closing positions on reaching take-profit or stop-loss thresholds,
      or when technical indicators suggest weakening momentum.

    Stop-loss and take-profit levels are automatically determined at the time of entry,
    based on the Average True Range (ATR) and a configurable multiplier,
    allowing the system to adapt to market volatility.

    Parameters:
        data (pd.DataFrame): Historical OHLC data with at least the following columns: ['High', 'Low', 'Close'].
        fast_ema_window (int): EMA window size for the fast component of the MACD.
        slow_ema_window (int): EMA window size for the slow component of the MACD.
        ema_signal_window (int): EMA window for the MACD signal line.
        rsi_window (int): Window size for the RSI indicator.
        rsi_threshold (int): RSI threshold to define overbought/oversold conditions.
        atr_window (int): Window size for the Average True Range (ATR) calculation.
        atr_multiplier (float): Multiplier for ATR to compute stop-loss and take-profit levels.

    Returns:
        pd.DataFrame: A DataFrame indexed by date containing:
            - 'Asset': Simulated portfolio value (cash + unrealized positions) over time.
            - 'Return': Daily percentage change in portfolio value.

    Notes:
        - Position sizing is based on using 50% of available cash at the time of entry.
        - Positions are only opened if no other positions are active.
        - The strategy supports both long and short positions.
    """
    data = data.copy()
    price_multiplier = MULTIPLIER * MARGIN_RATIO / ACCOUNT_RATIO

    # Initialize trading variables
    cash = ASSET_VALUE
    holdings = []  # List of (entry_date, pos_type, entry_price, quantity, stop_loss_price, take_profit_price)
    trading_data = pd.DataFrame(index = data.index, columns = ['Asset'])
    trading_data['Asset'] = cash
    trading_data['Asset'] = trading_data['Asset'].astype(float)

    # Calculate technical indicators
    data['MACD_diff'] = ta.trend.macd_diff(
        data['Close'], window_slow=fast_ema_window, window_fast=slow_ema_window, window_sign=ema_signal_window
    )
    data['RSI'] = ta.momentum.rsi(data['Close'], window = rsi_window)
    data['ATR'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = atr_window)

    # Trading loop starting from the second day
    for i in range(1, len(data)):
        row = data.iloc[i]
        if pd.isna(row['RSI']) or pd.isna(row['MACD_diff']) or pd.isna(row['ATR']):
            continue
        date = data.index[i]
        cur_price = row['Close']

        # Check for positions to close
        for position in holdings[:]:
            entry_date, pos_type, entry_price, quantity, stop_loss_price, take_profit_price = position

            if pos_type == 'LONG':
                if (cur_price >= take_profit_price or cur_price <= stop_loss_price or
                    row['RSI'] >= (100 - rsi_threshold) or row['MACD_diff'] < 0):
                    # Closing a LONG position (selling)
                    cash += quantity * cur_price * price_multiplier - quantity * TAX * MULTIPLIER
                    holdings.remove(position)
            else:  # SHORT
                if (cur_price <= take_profit_price or cur_price >= stop_loss_price or
                    row['RSI'] <= rsi_threshold or row['MACD_diff'] > 0):
                    # Closing a SHORT position (buying back)
                    cash -= quantity * cur_price * price_multiplier + quantity * TAX * MULTIPLIER
                    holdings.remove(position)

        # Calculate unrealized P&L and update asset value
        total_unrealized_pnf = sum(
            cur_price * price_multiplier * pos[3] if pos[1] == 'LONG'
            else -cur_price * price_multiplier * pos[3] for pos in holdings
        )
        asset_value = cash + total_unrealized_pnf
        trading_data.loc[date, 'Asset'] = asset_value

        # Open new position if no holdings
        if not holdings:

            # LONG position entry conditions
            if row['MACD_diff'] > 0 and 50 < row['RSI'] < (100 - rsi_threshold):
                # Use half of cash, accounting for TAX
                quantity = floor((cash / 2) / (cur_price * price_multiplier))
                if quantity > 0:
                    cash -= quantity * cur_price * price_multiplier
                    stop_loss_price = cur_price - row['ATR'] * atr_multiplier
                    take_profit_price = cur_price + row['ATR'] * atr_multiplier
                    holdings.append((date, 'LONG', cur_price, quantity, stop_loss_price, take_profit_price))

            # SHORT position entry conditions
            elif row['MACD_diff'] < 0 and rsi_threshold < row['RSI'] < 50:
                # Use half of cash to determine quantity
                quantity = min(floor((cash / 2) / (cur_price * price_multiplier)), 3)
                if quantity > 0:
                    cash += quantity * cur_price * price_multiplier
                    stop_loss_price = cur_price + row['ATR'] * atr_multiplier
                    take_profit_price = cur_price - row['ATR'] * atr_multiplier
                    holdings.append((date, 'SHORT', cur_price, quantity, stop_loss_price, take_profit_price))

    trading_data['Return'] = trading_data['Asset'].pct_change()

    return trading_data

def dynamic_momentum_algo(
    data: pd.DataFrame,
    fast_ema_window: int,
    slow_ema_window: int,
    ema_signal_window: int,
    rsi_window: int,
    rsi_threshold: int,
    atr_window: int
    ) -> pd.DataFrame:
    """
    Executes a dynamic-ATR momentum trading strategy using MACD, RSI, and adaptive ATR-based risk management.

    This algorithm identifies momentum-driven trading opportunities by combining:
    - MACD for trend confirmation.
    - RSI for momentum filtering and overbought/oversold detection.
    - ATR for volatility-aware stop-loss and take-profit placement, dynamically adjusted
      based on short-term and long-term volatility comparisons.

    Parameters:
        data (pd.DataFrame): Historical price data with at least the following columns: ['High', 'Low', 'Close'].
        fast_ema_window (int): Fast EMA window size for MACD calculation.
        slow_ema_window (int): Slow EMA window size for MACD calculation.
        ema_signal_window (int): Signal line EMA window size for MACD.
        rsi_window (int): Rolling window size for the RSI indicator.
        rsi_threshold (int): RSI cutoff used for both entry and exit conditions (upper and lower band symmetry).
        atr_window (int): Rolling window size for ATR calculation used in position sizing and risk control.

    Returns:
        pd.DataFrame: A DataFrame indexed by datetime, containing:
            - 'Asset': Simulated portfolio value (including unrealized P&L) over time.
            - 'Return': Daily percentage returns of the portfolio.

    Note: Position size is calculated to use 50% of available capital at entry.
    """
    data = data.copy()
    price_multiplier = MULTIPLIER * MARGIN_RATIO / ACCOUNT_RATIO

    # Initialize trading variables
    cash = ASSET_VALUE
    holdings = []  # List of (entry_date, pos_type, entry_price, quantity, stop_loss_price, take_profit_price)
    trading_data = pd.DataFrame(index = data.index, columns = ['Asset'])
    trading_data['Asset'] = cash
    trading_data['Asset'] = trading_data['Asset'].astype(float)

    # Calculate technical indicators
    data['MACD_diff'] = ta.trend.macd_diff(
        data['Close'], window_slow=fast_ema_window, window_fast=slow_ema_window, window_sign=ema_signal_window
    )
    data['RSI'] = ta.momentum.rsi(data['Close'], window = rsi_window)
    data['ATR'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = atr_window)
    data['ATR_short'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = 10)
    data['ATR_long'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = 50)

    # Trading loop starting from the second day
    for i in range(1, len(data)):
        row = data.iloc[i]
        if pd.isna(row['RSI']) or pd.isna(row['MACD_diff']) or pd.isna(row['ATR']):
            continue
        date = data.index[i]
        cur_price = row['Close']

        # Determine ATR multiplier based on volatility trend
        if row['ATR_short'] > row['ATR_long']:
            atr_multiplier = 2.0  # Higher volatility → wider SL/TP
        else:
            atr_multiplier = 1.5  # Lower volatility → tighter SL/TP

        # Check for positions to close
        for position in holdings[:]:
            entry_date, pos_type, entry_price, quantity, stop_loss_price, take_profit_price = position

            if pos_type == 'LONG':
                if (cur_price >= take_profit_price or cur_price <= stop_loss_price or
                    row['RSI'] >= (100 - rsi_threshold) or row['MACD_diff'] < 0):
                    # Closing a LONG position (selling)
                    cash += quantity * cur_price * price_multiplier - quantity * TAX * MULTIPLIER
                    holdings.remove(position)
            else:  # SHORT
                if (cur_price <= take_profit_price or cur_price >= stop_loss_price or
                    row['RSI'] <= rsi_threshold or row['MACD_diff'] > 0):
                    # Closing a SHORT position (buying back)
                    cash -= quantity * cur_price * price_multiplier + quantity * TAX * MULTIPLIER
                    holdings.remove(position)

        # Calculate unrealized P&L and update asset value
        total_unrealized_pnf = sum(
            cur_price * price_multiplier * pos[3] if pos[1] == 'LONG'
            else -cur_price * price_multiplier * pos[3] for pos in holdings
        )
        asset_value = cash + total_unrealized_pnf
        trading_data.loc[date, 'Asset'] = asset_value

        # Open new position if no holdings
        if not holdings:

            # LONG position entry conditions
            if row['MACD_diff'] > 0 and 50 < row['RSI'] < (100 - rsi_threshold):
                # Use half of cash, accounting for TAX
                quantity = floor((cash / 2) / (cur_price * price_multiplier))
                if quantity > 0:
                    cash -= quantity * cur_price * price_multiplier
                    stop_loss_price = cur_price - row['ATR'] * atr_multiplier
                    take_profit_price = cur_price + row['ATR'] * atr_multiplier
                    holdings.append((date, 'LONG', cur_price, quantity, stop_loss_price, take_profit_price))

            # SHORT position entry conditions
            elif row['MACD_diff'] < 0 and rsi_threshold < row['RSI'] < 50:
                # Use half of cash to determine quantity
                quantity = min(floor((cash / 2) / (cur_price * price_multiplier)), 3)
                if quantity > 0:
                    cash += quantity * cur_price * price_multiplier
                    stop_loss_price = cur_price + row['ATR'] * atr_multiplier
                    take_profit_price = cur_price - row['ATR'] * atr_multiplier
                    holdings.append((date, 'SHORT', cur_price, quantity, stop_loss_price, take_profit_price))

    trading_data['Return'] = trading_data['Asset'].pct_change()

    return trading_data

def reversion_algo(
    data: pd.DataFrame,
    fast_ema_window: int,
    slow_ema_window: int,
    ema_signal_window: int,
    rsi_window: int,
    atr_window: int,
    atr_multiplier: float
    ) -> pd.DataFrame:
    """
    Executes a mean-reversion trading strategy using MACD, RSI, and ATR indicators.

    This algorithm aims to capture profits from price reversals by:
    - Entering positions when the market shows signs of being overbought or oversold.
    - Using MACD to confirm the price direction, RSI to detect extreme conditions,
      and ATR to dynamically set stop-loss and take-profit levels based on volatility.

    Parameters:
        data (pd.DataFrame): Historical OHLC price data with required columns: ['High', 'Low', 'Close'].
        fast_ema_window (int): Fast EMA window size for MACD calculation.
        slow_ema_window (int): Slow EMA window size for MACD calculation.
        ema_signal_window (int): Signal line EMA window size for MACD.
        rsi_window (int): Rolling window size for the RSI indicator.
        atr_window (int): Rolling window size for ATR volatility measurement.
        atr_multiplier (float): Multiplier for ATR to determine stop-loss and take-profit boundaries.

    Returns:
        pd.DataFrame: DataFrame indexed by date containing:
            - 'Asset': Simulated portfolio value (cash + unrealized positions) over time.
            - 'Return': Daily percentage return of the simulated portfolio.

    Notes:
        - The strategy trades both long and short positions, but only one position is held at a time.
        - Position size is calculated to deploy 50% of available cash at entry.
    """
    data = data.copy()
    price_multiplier = MULTIPLIER * MARGIN_RATIO / ACCOUNT_RATIO

    # Initialize trading variables
    cash = ASSET_VALUE
    holdings = []  # List of (entry_date, pos_type, entry_price, quantity, stop_loss_price, take_profit_price)
    trading_data = pd.DataFrame(index = data.index, columns = ['Asset'])
    trading_data['Asset'] = cash
    trading_data['Asset'] = trading_data['Asset'].astype(float)

    # Calculate technical indicators
    data['MACD_diff'] = ta.trend.macd_diff(
        data['Close'], window_slow=fast_ema_window, window_fast=slow_ema_window, window_sign=ema_signal_window
    )
    data['RSI'] = ta.momentum.rsi(data['Close'], window = rsi_window)
    data['ATR'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = atr_window)

    # Trading loop starting from the second day
    for i in range(1, len(data)):
        row = data.iloc[i]
        if pd.isna(row['RSI']) or pd.isna(row['MACD_diff']) or pd.isna(row['ATR']):
            continue
        date = data.index[i]
        cur_price = row['Close']

        # Check for positions to close
        for position in holdings[:]:
            entry_date, pos_type, entry_price, quantity, stop_loss_price, take_profit_price = position

            if pos_type == 'LONG':
                if (cur_price >= take_profit_price or cur_price <= stop_loss_price or
                    row['RSI'] >= 50 or row['MACD_diff'] < 0):
                    # Closing a LONG position (selling)
                    cash += quantity * cur_price * price_multiplier - quantity * TAX * MULTIPLIER
                    holdings.remove(position)
            else:  # SHORT
                if (cur_price <= take_profit_price or cur_price >= stop_loss_price or
                    row['RSI'] <= 50 or row['MACD_diff'] > 0):
                    # Closing a SHORT position (buying back)
                    cash -= quantity * cur_price * price_multiplier + quantity * TAX * MULTIPLIER
                    holdings.remove(position)

        # Calculate unrealized P&L and update asset value
        total_unrealized_pnf = sum(
            cur_price * price_multiplier * pos[3] if pos[1] == 'LONG'
            else -cur_price * price_multiplier * pos[3] for pos in holdings
        )
        asset_value = cash + total_unrealized_pnf
        trading_data.loc[date, 'Asset'] = asset_value

        # Open new position if no holdings
        if not holdings:

            # LONG position entry conditions
            if row['MACD_diff'] > 0 and row['RSI'] < 30:
                # Use half of cash, accounting for TAX
                quantity = floor((cash / 2) / (cur_price * price_multiplier))
                if quantity > 0:
                    cash -= quantity * cur_price * price_multiplier
                    stop_loss_price = cur_price - row['ATR'] * atr_multiplier
                    take_profit_price = cur_price + row['ATR'] * atr_multiplier
                    holdings.append((date, 'LONG', cur_price, quantity, stop_loss_price, take_profit_price))

            # SHORT position entry conditions
            elif row['MACD_diff'] < 0 and row['RSI'] > 70:
                # Use half of cash to determine quantity
                quantity = min(floor((cash / 2) / (cur_price * price_multiplier)), 3)
                if quantity > 0:
                    cash += quantity * cur_price * price_multiplier
                    stop_loss_price = cur_price + row['ATR'] * atr_multiplier
                    take_profit_price = cur_price - row['ATR'] * atr_multiplier
                    holdings.append((date, 'SHORT', cur_price, quantity, stop_loss_price, take_profit_price))

    trading_data['Return'] = trading_data['Asset'].pct_change()

    return trading_data

def dynamic_reversion_algo(
    data: pd.DataFrame,
    fast_ema_window: int,
    slow_ema_window: int,
    ema_signal_window: int,
    rsi_window: int,
    atr_window: int
    ) -> pd.DataFrame:
    """
    Executes a dynamic-ATR mean-reversion trading strategy using MACD, RSI, and adaptive volatility-based risk management.

    This algorithm identifies potential price reversals by:
    - Using MACD to detect trend direction and momentum shifts.
    - Using RSI to identify overbought and oversold conditions.
    - Using ATR to set stop-loss and take-profit boundaries, dynamically adjusting the risk margin based on
      short-term and long-term volatility comparisons.

    Parameters:
        data (pd.DataFrame): Historical price data, must contain: ['High', 'Low', 'Close'].
        fast_ema_window (int): Fast EMA window size for MACD calculation.
        slow_ema_window (int): Slow EMA window size for MACD calculation.
        ema_signal_window (int): Signal line EMA window size for MACD.
        rsi_window (int): Window size for the RSI indicator.
        atr_window (int): Window size for the ATR calculation, used for stop-loss and take-profit setting.

    Returns:
        pd.DataFrame: A DataFrame indexed by datetime, containing:
            - 'Asset': Simulated portfolio value over time (including unrealized P&L).
            - 'Return': Daily percentage returns of the simulated asset value.

    Note: Capital is allocated at 50% of available cash per trade.
    """
    data = data.copy()
    price_multiplier = MULTIPLIER * MARGIN_RATIO / ACCOUNT_RATIO

    # Initialize trading variables
    cash = ASSET_VALUE
    holdings = []  # List of (entry_date, pos_type, entry_price, quantity, stop_loss_price, take_profit_price)
    trading_data = pd.DataFrame(index = data.index, columns = ['Asset'])
    trading_data['Asset'] = cash
    trading_data['Asset'] = trading_data['Asset'].astype(float)

    # Calculate technical indicators
    data['MACD_diff'] = ta.trend.macd_diff(
        data['Close'], window_slow=fast_ema_window, window_fast=slow_ema_window, window_sign=ema_signal_window
    )
    data['RSI'] = ta.momentum.rsi(data['Close'], window = rsi_window)
    data['ATR'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = atr_window)
    data['ATR_short'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = 10)
    data['ATR_long'] = ta.volatility.average_true_range(data['High'], data['Low'], data['Close'], window = 50)

    # Trading loop starting from the second day
    for i in range(1, len(data)):
        row = data.iloc[i]
        if pd.isna(row['RSI']) or pd.isna(row['MACD_diff']) or pd.isna(row['ATR']):
            continue
        date = data.index[i]
        cur_price = row['Close']

        # Determine ATR multiplier based on volatility trend
        if row['ATR_short'] > row['ATR_long']:
            atr_multiplier = 2.0  # Higher volatility → wider SL/TP
        else:
            atr_multiplier = 1.5  # Lower volatility → tighter SL/TP

        # Check for positions to close
        for position in holdings[:]:
            entry_date, pos_type, entry_price, quantity, stop_loss_price, take_profit_price = position

            if pos_type == 'LONG':
                if (cur_price >= take_profit_price or cur_price <= stop_loss_price or
                    row['RSI'] >= 50 or row['MACD_diff'] < 0):
                    # Closing a LONG position (selling)
                    cash += quantity * cur_price * price_multiplier - quantity * TAX * MULTIPLIER
                    holdings.remove(position)
            else:  # SHORT
                if (cur_price <= take_profit_price or cur_price >= stop_loss_price or
                    row['RSI'] <= 50 or row['MACD_diff'] > 0):
                    # Closing a SHORT position (buying back)
                    cash -= quantity * cur_price * price_multiplier + quantity * TAX * MULTIPLIER
                    holdings.remove(position)

        # Calculate unrealized P&L and update asset value
        total_unrealized_pnf = sum(
            cur_price * price_multiplier * pos[3] if pos[1] == 'LONG'
            else -cur_price * price_multiplier * pos[3] for pos in holdings
        )
        asset_value = cash + total_unrealized_pnf
        trading_data.loc[date, 'Asset'] = asset_value

        # Open new position if no holdings
        if not holdings:

            # LONG position entry conditions
            if row['MACD_diff'] > 0 and row['RSI'] < 30:
                # Use half of cash, accounting for TAX
                quantity = floor((cash / 2) / (cur_price * price_multiplier))
                if quantity > 0:
                    cash -= quantity * cur_price * price_multiplier
                    stop_loss_price = cur_price - row['ATR'] * atr_multiplier
                    take_profit_price = cur_price + row['ATR'] * atr_multiplier
                    holdings.append((date, 'LONG', cur_price, quantity, stop_loss_price, take_profit_price))

            # SHORT position entry conditions
            elif row['MACD_diff'] < 0 and row['RSI'] > 70:
                # Use half of cash to determine quantity
                quantity = min(floor((cash / 2) / (cur_price * price_multiplier)), 3)
                if quantity > 0:
                    cash += quantity * cur_price * price_multiplier
                    stop_loss_price = cur_price + row['ATR'] * atr_multiplier
                    take_profit_price = cur_price - row['ATR'] * atr_multiplier
                    holdings.append((date, 'SHORT', cur_price, quantity, stop_loss_price, take_profit_price))

    trading_data['Return'] = trading_data['Asset'].pct_change()

    return trading_data

def momentum_optimize(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()

    fast_ema_range = range(7, 15)
    slow_ema_range = range(20, 30)
    ema_signal_range = range(7, 10)
    rsi_range = range(2, 8)
    rsi_threshold_range = [20, 25, 30]
    atr_range = range(8, 20)
    atr_multiplier_range = [2.0, 2.5, 3.0]

    # Generate all possible parameter combinations
    param_combinations = list(itertools.product(
        fast_ema_range, slow_ema_range, ema_signal_range,
        rsi_range, rsi_threshold_range,
        atr_range, atr_multiplier_range
    ))

    # Preallocate DataFrame with correct size
    table = pd.DataFrame(index = range(len(param_combinations)), columns = [
        'Fast EMA Window', 'Slow EMA Window', 'EMA Signal Window', 'RSI Window', 'RSI Threshold', 'ATR Window', 'ATR Multiplier',
        'Accumulate Rate', 'Maximum Drawdown', 'Longest Drawdown', 'Sharpe Ratio', 'Sortino Ratio',
        'Score'
    ])

    # Loop through combinations with tqdm progress bar
    for index, (f, s, e, r, r_t, a, a_m) in tqdm(enumerate(param_combinations), total=len(param_combinations), desc="Optimizing"):
        params = (f, s, e, r, r_t, a, a_m)
        result = momentum_algo(data, f, s, e, r, r_t, a, a_m)

        hpr = holding_period_returns(result)
        mdd = maximum_drawdown(result)
        ldd = longest_drawdown(result)
        sharpe = sharpe_ratio(result)
        sortino = sortino_ratio(result)
        score = loss_score(hpr, mdd, ldd, sharpe, sortino)

        table.loc[index] = [*params, hpr, mdd, ldd, sharpe, sortino, score]

    return table.sort_values('Score', ascending = False)

def dynamic_momentum_optimize(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()

    fast_ema_range = range(7, 15)
    slow_ema_range = range(20, 30)
    ema_signal_range = range(7, 10)
    rsi_range = range(2, 10)
    rsi_threshold_range = [20, 25, 30]
    atr_range = range(8, 20)

    # Generate all possible parameter combinations
    param_combinations = list(itertools.product(
        fast_ema_range, slow_ema_range, ema_signal_range,
        rsi_range, rsi_threshold_range, atr_range
    ))

    # Preallocate DataFrame with correct size
    table = pd.DataFrame(index = range(len(param_combinations)), columns = [
        'Fast EMA Window', 'Slow EMA Window', 'EMA Signal Window', 'RSI Window', 'RSI Threshold', 'ATR Window',
        'Accumulate Rate', 'Maximum Drawdown', 'Longest Drawdown', 'Sharpe Ratio', 'Sortino Ratio',
        'Score'
    ])

    # Loop through combinations with tqdm progress bar
    for index, (f, s, e, r, r_t, a) in tqdm(enumerate(param_combinations), total=len(param_combinations), desc="Optimizing"):
        params = (f, s, e, r, r_t, a)
        result = dynamic_momentum_algo(data, f, s, e, r, r_t, a)

        hpr = holding_period_returns(result)
        mdd = maximum_drawdown(result)
        ldd = longest_drawdown(result)
        sharpe = sharpe_ratio(result)
        sortino = sortino_ratio(result)
        score = loss_score(hpr, mdd, ldd, sharpe, sortino)

        table.loc[index] = [*params, hpr, mdd, ldd, sharpe, sortino, score]

    return table.sort_values('Score', ascending = False)

def reversion_optimize(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()

    fast_ema_range = range(10, 20)
    slow_ema_range = range(25, 40)
    ema_signal_range = range(9, 15)
    rsi_range = range(10, 15)
    atr_range = range(6, 15)
    atr_multiplier_range = [1.0, 1.5, 2.0]

    # Generate all possible parameter combinations
    param_combinations = list(itertools.product(fast_ema_range, slow_ema_range, ema_signal_range, rsi_range, atr_range, atr_multiplier_range))

    # Preallocate DataFrame with correct size
    table = pd.DataFrame(index = range(len(param_combinations)), columns = [
        'Fast EMA Window', 'Slow EMA Window', 'EMA Signal Window', 'RSI Window', 'ATR Window', 'ATR Multiplier',
        'Accumulate Rate', 'Maximum Drawdown', 'Longest Drawdown', 'Sharpe Ratio', 'Sortino Ratio',
        'Score'
    ])

    # Loop through combinations with tqdm progress bar
    for index, (f, s, e, r, a, a_m) in tqdm(enumerate(param_combinations), total = len(param_combinations), desc = "Optimizing"):
        params = (f, s, e, r, a, a_m)
        result = reversion_algo(data, f, s, e, r, a, a_m)

        hpr = holding_period_returns(result)
        mdd = maximum_drawdown(result)
        ldd = longest_drawdown(result)
        sharpe = sharpe_ratio(result)
        sortino = sortino_ratio(result)
        score = loss_score(hpr, mdd, ldd, sharpe, sortino)

        table.loc[index] = [*params, hpr, mdd, ldd, sharpe, sortino, score]

    return table.sort_values('Score', ascending = False)

def dynamic_reversion_optimize(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()

    fast_ema_range = range(10, 20)
    slow_ema_range = range(25, 40)
    ema_signal_range = range(8, 15)
    rsi_range = range(10, 15)
    atr_range = range(6, 15)

    # Generate all possible parameter combinations
    param_combinations = list(itertools.product(fast_ema_range, slow_ema_range, ema_signal_range, rsi_range, atr_range))

    # Preallocate DataFrame with correct size
    table = pd.DataFrame(index = range(len(param_combinations)), columns = [
        'Fast EMA Window', 'Slow EMA Window', 'EMA Signal Window', 'RSI Window', 'ATR Window',
        'Accumulate Rate', 'Maximum Drawdown', 'Longest Drawdown', 'Sharpe Ratio', 'Sortino Ratio',
        'Score'
    ])

    # Loop through combinations with tqdm progress bar
    for index, (f, s, e, r, a) in tqdm(enumerate(param_combinations), total = len(param_combinations), desc = "Optimizing"):
        params = (f, s, e, r, a)
        result = dynamic_reversion_algo(data, f, s, e, r, a)

        hpr = holding_period_returns(result)
        mdd = maximum_drawdown(result)
        ldd = longest_drawdown(result)
        sharpe = sharpe_ratio(result)
        sortino = sortino_ratio(result)
        score = loss_score(hpr, mdd, ldd, sharpe, sortino)

        table.loc[index] = [*params, hpr, mdd, ldd, sharpe, sortino, score]

    return table.sort_values('Score', ascending = False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Optimize a trading strategy using historical data.")
    parser.add_argument('--data', type=str, default='in_sample.csv', help='Path to the CSV file containing OHLC data.')
    parser.add_argument(
        '--algo', type=str, choices=['static_momentum', 'dynamic_momentum', 'static_reversion', 'dynamic_reversion'], required=True,
        help='Type of algorithm to run: "static_momentum", "dynamic_momentum", "static_reversion", or "dynamic_reversion".'
    )

    args = parser.parse_args()

    # Load data
    data = pd.read_csv(args.data, index_col=0, parse_dates=True)

    if args.algo == 'static_momentum':
        result = momentum_optimize(data)
    elif args.algo == 'dynamic_momentum':
        result = dynamic_momentum_optimize(data)
    elif args.algo == 'static_reversion':
        result = reversion_optimize(data)
    elif args.algo == 'dynamic_reversion':
        result = dynamic_reversion_optimize(data)
    
    result.to_csv(f'optimize_{args.algo}.csv', index=False)
    print(f"Optimization results saved to optimize_{args.algo}.csv")