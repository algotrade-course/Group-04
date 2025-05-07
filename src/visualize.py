from matplotlib import pyplot as plt
import pandas as pd
import argparse
import matplotlib.patches as mpatches

def visualize_data(data_file: str) -> None:
    """
    Visualizes the data using a line plot.
    
    Parameters:
    data_file (str): Name of the CSV file containing the data, including at least 'Time' and 'Close' columns.
    """
    data = pd.read_csv(data_file, parse_dates=['Time'], index_col='Time')
    data['Close'].plot(kind='line', figsize=(8, 6))
    plt.title(f'{data_file.split('.')[0]} Close Prices Plot')
    plt.xlabel('Date')
    plt.ylabel('Close Price')
    plt.gca().spines[['top', 'right']].set_visible(False)
    plt.tight_layout()
    plt.show()

def visualize_trades(result: pd.DataFrame) -> None:
    """
    Visualizes the trades using a line plot.

    Parameters:
    result (pd.DataFrame): DataFrame containing the trades data, including at least 'Asset' and 'Return' columns.
    """
    nav = result['Asset']

    # Compute maximum drawdown
    rolling_max = nav.cummax()
    drawdown = nav / rolling_max - 1
    mdd = drawdown.min()
    mdd_end = drawdown.idxmin()
    mdd_start = nav[:mdd_end].idxmax()

    # Compute longest drawdown period
    ldd = (0, 0)
    ldd_length = 0
    start = 0
    while start < len(nav):
        peak = nav[start]
        end = start + 1
        while end < len(nav) and nav[end] < peak:
            end += 1
        if end != len(nav) and end - start - 1 > ldd_length:
            ldd = (start, end)
            ldd_length = end - start - 1
        start = end

    # Compute holding period return
    hpr = nav.iloc[-1] / nav.iloc[0] - 1

    # Plot NAV
    plt.figure(figsize=(8, 6))
    plt.plot(result.index, nav, label='Net Asset Value', color='blue')

    # Annotate maximum drawdown
    plt.axvspan(mdd_start, mdd_end, color='red', alpha=0.5, label='Max Drawdown')
    plt.text(mdd_end, nav[mdd_end], f'MDD: {mdd:.2%}', color='red')

    # Annotate longest drawdown
    plt.axvspan(result.index[ldd[0]], result.index[ldd[1]], color='gold', alpha=0.5, label='Longest Drawdown')
    plt.text(result.index[ldd[1]], nav[ldd[1]], f'LDD: {ldd_length} days', color='gold')

    # Annotate holding period return
    end_date = result.index[-1]
    end_nav = nav.iloc[-1]
    plt.text(end_date, end_nav, f'HPR: {hpr:.2%}', color='blueviolet', verticalalignment='bottom')

    # Check for overlap
    overlap_start = max(mdd_start, result.index[ldd[0]])
    overlap_end = min(mdd_end, result.index[ldd[1]])

    if overlap_start < overlap_end:
        # Add dummy patch just for legend
        overlap_patch = mpatches.Patch(color='darkorange', alpha=0.5, label='Overlapping Region')
        plt.legend(handles=[*plt.gca().get_legend_handles_labels()[0], overlap_patch])
    else:
        plt.legend()
    
    plt.title(f'NAV Chart with Max Drawdown, Longest Drawdown, and Holding Period Return')
    plt.xlabel('Date')
    plt.ylabel('Net Asset Value')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize stock data.")
    parser.add_argument("--file", type=str, required=True, help="Path to the CSV file containing stock data.")
    args = parser.parse_args()
    
    visualize_data(args.file)