import argparse
import pandas as pd
from vnstock import Vnstock

def load_data(symbol, start_date='2020-01-01', end_date='2025-01-01'):
    """
    Load and preprocess symbol from vnstock.

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

def process_split_data(data: pd.DataFrame, split_date='2024-01-01'):
    """
    Process and split data for backtesting.

    Parameters:
    - data (pd.DataFrame): Raw data with OHLC columns.
    - split_date (str): Date to split in-sample and out-of-sample data (format: 'YYYY-MM-DD').

    Returns:
    - tuple: (in_sample_df, out_sample_df)
        - in_sample_df (pd.DataFrame): Preprocessed in-sample data with OHLC columns.
        - out_sample_df (pd.DataFrame): Preprocessed out-of-sample data with OHLC columns.
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

    # Ensure required columns are present
    required_columns = ['Open', 'High', 'Low', 'Close']
    for df in [in_sample, out_sample]:
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Missing required columns in data: {required_columns}")

    return in_sample, out_sample

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch and split stock data from vnstock.")
    parser.add_argument('--symbol', type=str, default='VN30F1M', help='Ticker symbol (e.g., VN30F1M).')
    parser.add_argument('--start_date', type=str, default='2020-01-01', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end_date', type=str, default='2025-01-01', help='End date (YYYY-MM-DD).')
    parser.add_argument('--split_date', type=str, default='2024-01-01', help='Split date for in/out sample (YYYY-MM-DD).')

    args = parser.parse_args()

    data = load_data(args.symbol, args.start_date, args.end_date)
    in_sample_df, out_sample_df = process_split_data(data, args.split_date)

    in_sample_df.to_csv('in_sample.csv', index=True)
    out_sample_df.to_csv('out_sample.csv', index=True)

    print(f"Data for {args.symbol} saved to 'in_sample.csv' and 'out_sample.csv'.")