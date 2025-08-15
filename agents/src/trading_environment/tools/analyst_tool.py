from autogen_core.tools import FunctionTool
from configs.tools_config import yfin_tool_cfg, stockstats_tool_cfg
from datetime import datetime
from tools.tool_tracing_utils import trace_span_info
import pandas as pd

from stockstats import wrap
from dateutil.relativedelta import relativedelta


@trace_span_info
async def get_YF_data_tool(
    symbol: str,
    start_date: str,
    end_date: str,
) -> str:
    """Fetches data from Yahoo Finance."""

    try:
        # Convert start_date and end_date to datetime
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except ValueError as e:
        return f"Invalid date format: {e}"

    file_path = f"/data/ticker_price/{symbol}.csv"

    # Read CSV
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return f"Data on ticker '{symbol}' not available."

    # Ensure report_date is datetime
    df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_convert(None)

    # Filter by date range
    mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
    filtered_df = df.loc[mask]

    # Convert the filtered DataFrame to CSV string
    csv_string = filtered_df.to_csv(index=False)

    # Add header information
    header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
    # header += f"# Total records: {len(data)}\n"

    return header + csv_string


get_YF_data_tool = FunctionTool(
    get_YF_data_tool, description=yfin_tool_cfg["description"]
)


def get_stock_stats(
    symbol: str,
    indicator: str,
    curr_date: str,
):
    df = None
    file_path = f"/data/ticker_price/{symbol}.csv"

    # Read CSV
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return f"Data on ticker '{symbol}' not available."
    # Ensure report_date is datetime
    df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_convert(None)
    df.set_index("Date", inplace=True)
    df = wrap(df)
    if isinstance(curr_date, str):
        curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    else:
        curr_date_dt = curr_date

    df[indicator]  # trigger stockstats to calculate the indicator
    matching_rows = df[df.index.date == curr_date_dt.date()]

    if not matching_rows.empty:
        return matching_rows[indicator].iloc[0]
    else:
        return "N/A: Not a trading day (weekend or holiday)"


@trace_span_info
async def get_stock_stats_indicators(
    symbol: str,
    indicator: str,
    curr_date: str,
    look_back_days: int,
) -> str:

    best_ind_params = {
        # Moving Averages
        "close_50_sma": (
            "50 SMA: A medium-term trend indicator. "
            "Usage: Identify trend direction and serve as dynamic support/resistance. "
            "Tips: It lags price; combine with faster indicators for timely signals."
        ),
        "close_200_sma": (
            "200 SMA: A long-term trend benchmark. "
            "Usage: Confirm overall market trend and identify golden/death cross "
            "setups. Tips: It reacts slowly; best for strategic trend confirmation "
            "rather than frequent trading entries."
        ),
        "close_10_ema": (
            "10 EMA: A responsive short-term average. "
            "Usage: Capture quick shifts in momentum and potential entry points. "
            "Tips: Prone to noise in choppy markets; use alongside longer averages "
            "for filtering false signals."
        ),
        # MACD Related
        "macd": (
            "MACD: Computes momentum via differences of EMAs. "
            "Usage: Look for crossovers and divergence as signals of trend changes. "
            "Tips: Confirm with other indicators in low-volatility or sideways markets."
        ),
        "macds": (
            "MACD Signal: An EMA smoothing of the MACD line. "
            "Usage: Use crossovers with the MACD line to trigger trades. "
            "Tips: Should be part of a broader strategy to avoid false positives."
        ),
        "macdh": (
            "MACD Histogram: Shows the gap between the MACD line and its signal. "
            "Usage: Visualize momentum strength and spot divergence early. "
            "Tips: Can be volatile; complement with additional filters in "
            "fast-moving markets."
        ),
        # Momentum Indicators
        "rsi": (
            "RSI: Measures momentum to flag overbought/oversold conditions. "
            "Usage: Apply 70/30 thresholds and watch for divergence to signal "
            "reversals. Tips: In strong trends, RSI may remain extreme; always "
            "cross-check with trend analysis."
        ),
        # Volatility Indicators
        "boll": (
            "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. "
            "Usage: Acts as a dynamic benchmark for price movement. "
            "Tips: Combine with the upper and lower bands to effectively spot "
            "breakouts or reversals."
        ),
        "boll_ub": (
            "Bollinger Upper Band: Typically 2 standard deviations above the middle "
            "line. Usage: Signals potential overbought conditions and breakout zones. "
            "Tips: Confirm signals with other tools; prices may ride the band in "
            "strong trends."
        ),
        "boll_lb": (
            "Bollinger Lower Band: Typically 2 standard deviations below the middle "
            "line. Usage: Indicates potential oversold conditions. "
            "Tips: Use additional analysis to avoid false reversal signals."
        ),
        "atr": (
            "ATR: Averages true range to measure volatility. "
            "Usage: Set stop-loss levels and adjust position sizes based on current "
            "market volatility. "
            "Tips: It's a reactive measure, so use it as part of a broader risk "
            "management strategy."
        ),
        # Volume-Based Indicators
        "vwma": (
            "VWMA: A moving average weighted by volume. "
            "Usage: Confirm trends by integrating price action with volume data. "
            "Tips: Watch for skewed results from volume spikes; use in combination "
            "with other volume analyses."
        ),
        "mfi": (
            "MFI: The Money Flow Index is a momentum indicator that uses both "
            "price and volume to measure buying and selling pressure. "
            "Usage: Identify overbought (>80) or oversold (<20) conditions and "
            "confirm the strength of trends or reversals. "
            "Tips: Use alongside RSI or MACD to confirm signals; divergence between "
            "price and MFI can indicate potential reversals."
        ),
    }

    if indicator not in best_ind_params:
        raise ValueError(
            f"Indicator {indicator} is not supported. "
            f"Please choose from: {list(best_ind_params.keys())}"
        )

    end_date = curr_date
    curr_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date - relativedelta(days=look_back_days)

    ind_string = ""
    while curr_date >= before:
        indicator_value = get_stock_stats(
            symbol, indicator, curr_date.strftime("%Y-%m-%d")
        )

        ind_string += f"{curr_date.strftime('%Y-%m-%d')}: {indicator_value}\n"

        curr_date = curr_date - relativedelta(days=1)

    result_str = (
        f"## {indicator} values from {before.strftime('%Y-%m-%d')} to {end_date}:\n\n"
        f"{ind_string}\n\n"
        f"{best_ind_params.get(indicator, 'No description available.')}"
    )

    return result_str


get_stock_stats_indicators_tool = FunctionTool(
    get_stock_stats_indicators, description=stockstats_tool_cfg["description"]
)
