from autogen_core.tools import FunctionTool
from configs.tools_config import googlenews_tool_cfg, reddit_news_tool_cfg
from datetime import datetime
from tools.tool_tracing_utils import trace_span_info
import httpx
from bs4 import BeautifulSoup
import re
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
import os
import json


# TODO: Fix google news tool
@trace_span_info
async def get_google_news_tool(
    query: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, str]]:
    """
    Scrape Google News search results for a given query and date range.
    query: str - search query
    start_date: str - start date in the format yyyy-mm-dd or mm/dd/yyyy
    end_date: str - end date in the format yyyy-mm-dd or mm/dd/yyyy
    """
    if "-" in start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    if "-" in end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%m/%d/%Y")

    news_results = []
    page_num = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(headers=headers) as client:
        while True:
            offset = page_num * 10
            url = (
                f"https://www.google.com/search?q={query}"
                f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
                f"&tbm=nws&start={offset}"
            )

            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            results_on_page = soup.select("div.SoaBEf")
            if not results_on_page:
                break

            for el in results_on_page:
                try:
                    link = el.find("a")["href"]
                    title = el.select_one("div.MBeuO").get_text(strip=True)
                    snippet = el.select_one(".GI74Re").get_text(strip=True)
                    date = el.select_one(".LfVVr").get_text(strip=True)
                    source = el.select_one(".NUnG9d span").get_text(strip=True)
                    news_results.append(
                        {
                            "link": link,
                            "title": title,
                            "snippet": snippet,
                            "date": date,
                            "source": source,
                        }
                    )
                except Exception as e:
                    print(f"Error processing result: {e}")
                    continue

            next_button = soup.find("a", id="pnnext")
            if not next_button:
                break

            page_num += 1

    return news_results


get_google_news_tool = FunctionTool(
    get_google_news_tool, description=googlenews_tool_cfg["description"]
)

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


async def get_reddit_company_news(
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


get_reddit_company_news_tool = FunctionTool(
    get_reddit_company_news,
    reddit_news_tool_cfg["description"],
)
