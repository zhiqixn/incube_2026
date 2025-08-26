import os

delegate_cfg = {
    "description": (
        "Call this tool to delegate tasks to other agents if there "
        "are any information outside of your expertise. "
        "Only delegate to these agents:\n\n{agents}\n\n"
        "Field 'name' MUST be the one word name of agent delegating task. "
        "E.g. MarketAnalyst, Researcher, Trader, etc.\n"
        "Each DelegationTask data model should contain the fields "
        "'task', 'agent' and 'name'."
    )
}

# default tools
rag_cfg = {
    "description": (
        "Call this tool to query the knowledge base for information "
        "relevant to the task. "
        "Provide a detailed search query.\n"
        "Tool follows this format: query, database\n"
        "[rag({'query': '','name': ''}), rag({'query': '','name': ''})]\n"
    ),
    "weaviate_client_configs": {
        "http_host": os.environ.get("WEAVIATE_HOST", "weaviate"),
        "http_port": os.environ.get("WEAVIATE_PORT", 8080),
        "http_secure": False,
        "grpc_host": os.environ.get("WEAVIATE_HOST", "weaviate"),
        "grpc_port": os.environ.get("WEAVIATE_GRPC_PORT", 50051),
        "grpc_secure": False,
    },
    "weaviate_collection": "SOP",
    "weaviate_query_kwargs": {
        "query_properties": ["content^2", "extended_content"],
        "alpha": 0.8,
        "limit": 3,
    },
    "weaviate_content_field": "content",
    "embedding_api_endpoint": "http://192.168.100.110:8000/v1/embeddings",
    "embedding_model": "BAAI/bge-m3",
}

think_cfg = {
    "description": (
        "Use the tool to think about the task and context. It will not obtain "
        "new information, but just log the thought. Use it when complex reasoning "
        "or brainstorming is needed."
        "The tool simply logs your thought process for better transparency and "
        "does not execute any code or make changes."
    )
}

condenser_cfg = {
    "description": (
        "Use this tool to trigger a context summarization process. "
        "Call this tool in this format: condenser()"
    ),
    "condenser_configs": (
        """You are maintaining the long term memory state for a multi-agent system. \
Condensing the memory state is critical because it:
1. Preserves essential context when conversation history grows too large
2. Helps maintain continuity across multiple interactions

You will be given:
- A list of responses (actions taken by each agent)

Your task is the summarize the content of the memory.
- Exclude formatting, repetitions, introductions or conclusions

Capture all relevant information, especially:
- User requirements that were explicitly stated
- Arguments given by the agent, data retrieved by the agent and its tool calls

Content below:
"""
    ),
}

# domain specific tools
yfin_tool_cfg = {
    "description": (
        "Call this tool to retrieve financial data from Yahoo Finance. "
        "Provide a stock ticker symbol and a date range based on the user task."
        "Symbol should be a valid stock ticker, e.g. 'AAPL' for Apple Inc."
        "The date range should be in the format 'YYYY-MM-DD'."
        "Tool follows this format: stock ticker, start date, end date."
    )
}

googlenews_tool_cfg = {
    "description": (
        "Call this tool to retrieve the latest news articles from Google News. "
        "Provide a search query and a date range based on the user task."
    )
}

stockstats_tool_cfg = {
    "description": (
        "Call this tool to retrieve stock statistics indicators based on the "
        "indicator descriptions. "
        "Provide a stock ticker, an indicator, "
        "the current date, and the number of days to look back. "
        "Tool follows this format: symbol, indicator, curr_date, look_back_days"
    )
}
reddit_news_tool_cfg = {
    "description": (
        "Call this tool to retrieve the latest top reddit news "
        "for a given company ticker. "
        "Provide the ticker symbol, start date and look back days"
        "The tool will return a formatted string containing the latest "
        "news articles posts on reddit."
    )
}
