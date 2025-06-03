import os

from autogen_ext.models.openai import OpenAIChatCompletionClient

MODEL_ENDPOINT = f"http://{os.environ['VLLM_HOST']}:{os.environ['VLLM_H_PORT']}/v1"
MODEL_NAME = os.environ["MODEL_NAME"]


model_cfg = {
    "base_url": MODEL_ENDPOINT,
    "model": MODEL_NAME,
    "temperature": 0,
    "api_key": "EMPTY",
    "model_capabilities": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
    },
}