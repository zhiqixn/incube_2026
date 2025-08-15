import asyncio
import json
import requests

from autogen_core.tools import FunctionTool
from configs.tools_config import condenser_cfg
from configs.models_config import model_chat_completion_cfg
from utils.logger import get_logger

logger = get_logger()


def condenser(message: str) -> str:

    headers = {"Content-Type": "application/json"}
    if model_chat_completion_cfg["api_key"]:
        headers["Authorization"] = f"Bearer {model_chat_completion_cfg['api_key']}"

    payload = {
        "model": model_chat_completion_cfg["model"],
        "temperature": model_chat_completion_cfg["temperature"],
        "messages": [
            {"role": "system", "content": condenser_cfg["condenser_configs"]},
            {"role": "user", "content": message},
        ],
    }

    try:
        response = requests.post(
            model_chat_completion_cfg["base_url"], headers=headers, json=payload
        )
        response.raise_for_status()
        result = response.json()
        summarized_msg = result["choices"][0]["message"]["content"]

        return summarized_msg
    except requests.RequestException as e:
        logger.error("HTTP request failed: %s", e)
        raise
    except (KeyError, IndexError):
        logger.error("Unexpected response format: %s", response.text)
        raise


condenser_tool = FunctionTool(condenser, description=condenser_cfg["description"])
