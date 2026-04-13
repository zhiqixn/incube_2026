from langchain.tools import tool

import os
import json
import re

from datetime import datetime
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
import pandas as pd

ticker_to_company = {
    "ASML": "ASML ",
    "JPM": "JPMorgan Chase OR JP Morgan",
    "LVMHF": "LVMH OR Louis Vuitton OR Moet Hennessy",
    "BABA": "Alibaba",
    "RHHBY": "Roche",
    "GS": "Goldman Sachs",
    "NSRGY": "Nestle",
    "NVO": "Novo Nordisk",
    "TSLA": "Tesla",
    "NVDA": "Nvidia",
    "PLTR": "Palantir",
    "SSNLF": "Samsung",
    "BHP": "BHP Group",
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "TSM": "Taiwan Semiconductor Manufacturing Company OR TSMC",
    "PFE": "Pfizer",
    "XOM": "Exxon Mobil OR Exxon",
}


# @tool
# TODO: Create DB calling memory tool for planner agent


@tool
def get_reddit_company_news(
    ticker: str,
    start_date: str,
    look_back_days: int,
) -> str:
    """
    Retrieve the latest top reddit news
    Args:
        ticker: ticker symbol of the company
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the latest news
        articles posts on reddit and meta information in these
        columns: "created_utc", "id", "title", "selftext", "score",
        "num_comments", "url"
    """

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    posts = []
    # iterate from start_date to end_date
    curr_date = datetime.strptime(before, "%Y-%m-%d")

    total_iterations = (start_date - curr_date).days + 1
    pbar = tqdm(
        desc=f"Getting Company News for {ticker} on {start_date}",
        total=total_iterations,
    )

    while curr_date <= start_date:
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        fetch_result = fetch_top_from_category(
            "company_news",
            curr_date_str,
            20,
            ticker,
            data_path="/data",
        )
        posts.extend(fetch_result)
        curr_date += relativedelta(days=1)

        pbar.update(1)

    pbar.close()

    if len(posts) == 0:
        return "No relevant news found for the given date range."

    news_str = ""
    for post in posts:
        if post["content"] == "":
            news_str += f"### {post['title']}\n\n"
        else:
            news_str += f"### {post['title']}\n\n{post['content']}\n\n"

    return f"##{ticker} News Reddit, from {before} to {curr_date}:\n\n{news_str}"


def fetch_top_from_category(
    category: str,
    date: str,
    max_limit: int,
    query: str,
    data_path: str,
):
    base_path = data_path

    all_content = []

    if max_limit < len(os.listdir(os.path.join(base_path, category))):
        raise ValueError(
            "REDDIT FETCHING ERROR: max limit is less than the number "
            "of files in the category. Will not be able to fetch any posts"
        )

    limit_per_subreddit = max_limit // len(
        os.listdir(os.path.join(base_path, category))
    )

    for data_file in os.listdir(os.path.join(base_path, category)):
        # check if data_file is a .jsonl file
        if not data_file.endswith(".jsonl"):
            continue

        all_content_curr_subreddit = []

        with open(os.path.join(base_path, category, data_file), "rb") as f:
            for i, line in enumerate(f):
                # skip empty lines
                if not line.strip():
                    continue

                parsed_line = json.loads(line)

                post_date = parsed_line["posted_date"].split("T")[0]

                if post_date != date:
                    continue

                # check that the title or the content has the company's
                # name (query) mentioned
                search_terms = []
                if "OR" in ticker_to_company[query]:
                    search_terms = ticker_to_company[query].split(" OR ")
                else:
                    search_terms = [ticker_to_company[query]]

                search_terms.append(query)

                found = False
                for term in search_terms:
                    if re.search(
                        term, parsed_line["title"], re.IGNORECASE
                    ) or re.search(term, parsed_line["content"], re.IGNORECASE):
                        found = True
                        break

                if not found:
                    continue

                post = {
                    "title": parsed_line["title"],
                    "content": parsed_line["content"],
                    "url": parsed_line["url"],
                    # "upvotes": parsed_line["ups"],
                    "posted_date": post_date,
                }

                all_content_curr_subreddit.append(post)

        all_content.extend(all_content_curr_subreddit[:limit_per_subreddit])

    return all_content


@tool
def get_YF_data_tool(
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
