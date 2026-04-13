import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url=os.getenv("MODEL_ENDPOINT") or "http://192.168.100.1:5000/v1",
    api_key=os.getenv("MODEL_API_KEY") or "not-needed",
    model=os.getenv("MODEL_NAME") or "gemma-4-26B-A4B-it",
)
