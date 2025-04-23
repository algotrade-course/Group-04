import pandas as pd
import numpy as np

# Constants
ASSET_VALUE = 2 * (10 ** 8)
TAX = 0.47
MARGIN_RATIO = 0.175
ACCOUNT_RATIO = 0.8
MULTIPLIER = 10 ** 5

def holding_period_returns(data: pd.DataFrame) -> float:
    """
    Calculates the Holding Period Return (HPR) of a portfolio.

    Args:
        data (pd.DataFrame): A DataFrame containing an 'Asset' column, which tracks the portfolio value over time.

    Returns:
        float: The total return over the period, expressed as a percentage.
    """
    cur_asset_value = data['Asset'].iloc[-1]
    init_asset_value = data['Asset'].iloc[0]
    return round((cur_asset_value / init_asset_value - 1) * 100, 6)

def maximum_drawdown(data: pd.DataFrame) -> float:
    """
    Returns the Maximum Drawdown (MDD) of the portfolio.

    Args:
        data: DataFrame with a 'Return' column representing daily returns.

    Returns:
        The Maximum Drawdown (MDD) of the portfolio.

    Raises:
        ValueError when:
        - The data['Return'] is empty or only has one value (the first NaN value from pct_change method)
        - The data['Return'] contains the value -1 (meaning all the capital of the portfolio is lost)
    """
    # Initial and peak asset
    peak = 1
    cur_asset = 1

    period_returns = data['Return'].dropna()

    if period_returns.empty:
        raise ValueError("Period returns is empty")
    if period_returns.isin([-1]).any():
        raise ValueError("All capital of the portfolio is lost")

    mdd = 0
    for val in period_returns:
        cur_asset *= (1 + val)
        peak = max(peak, cur_asset)
        mdd = min(mdd, -(1 - cur_asset / peak))
    return round(mdd * 100, 6)

def longest_drawdown(data: pd.DataFrame) -> int:
    """
    Returns the longest drawdown period from the period returns.

    Args:
        data: DataFrame with a 'Return' column representing daily returns.

    Returns:
        The longest drawdown of the portfolio.

    Raises:
        ValueError when:
        - The data['Return'] is empty or only has one value (the first NaN value from pct_change method)
        - The data['Return'] contains the value -1 (meaning all the capital of the portfolio is lost)
    """
    # Initial and peak asset
    cur_asset = 1
    peak = 1

    period_returns = data['Return'].dropna()

    if period_returns.empty:
        raise ValueError("Period returns is empty")
    if period_returns.isin([-1]).any():
        raise ValueError("All capital of the portfolio is lost")

    count = 0
    ldd = 0
    for val in period_returns:
        cur_asset *= (1 + val)
        if cur_asset >= peak:
            peak = cur_asset
            ldd = max(ldd, count)
            count = 0
        else:
            count += 1
    ldd = max(ldd, count)
    return ldd

def sharpe_ratio(data: pd.DataFrame, risk_free_return: float = 0.03093) -> float:
    """Returns the Sharpe Ratio

    Args:
        data: DataFrame with a 'Return' column representing daily returns.
        risk_free_return: The annual risk-free return rate.

    Returns:
        Sharpe ratio of the portfolio.

    Raises:
        ValueError: If data['Return'] is an empty Series or only has one value (the first NaN value from pct_change method).
    """
    period_returns = data['Return'].dropna()
    if period_returns.empty:
        raise ValueError("Period returns is empty")

    std = np.std(period_returns, ddof=1)
    if std == 0:
        return 0

    return round((252 * np.mean(data['Return']) - risk_free_return) / (np.sqrt(252) * std), 6)

def sortino_ratio(data: pd.DataFrame, risk_free_return: float = 0.03093) -> float:
    """Returns the Sortino Ratio

    Args:
        data: DataFrame with a 'Return' column representing daily returns.
        risk_free_return: The annual risk-free return rate.

    Returns:
        Sortino ratio of the portfolio.

    Raises:
        ValueError: If data['Return'] is an empty Series or only has one value (the first NaN value from pct_change method).
    """
    period_returns = data['Return'].dropna()
    if period_returns.empty:
        raise ValueError("Period returns is empty")

    downside_risk = np.sqrt(np.mean([0 if val > risk_free_return else (val - risk_free_return) ** 2 for val in period_returns]))
    if downside_risk == 0:
        return 0

    return round((np.sqrt(252) * np.mean(period_returns) - risk_free_return) / downside_risk, 6)