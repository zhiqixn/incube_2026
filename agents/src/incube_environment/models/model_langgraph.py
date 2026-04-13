import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://192.168.100.1:5000/v1",
    api_key="not-needed",
    model="gemma-4-26B-A4B-it",
)
