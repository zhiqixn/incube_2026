"""
Config class to help you track your experiments and its configs
Add more variable if required subsequently.
"""

import json
import os


class AgentConfig:
    def __init__(self):
        self.exp_description = ""  # What did you change in this experiments
        self.es_endpoint = f"http://{os.environ['ELASTICSEARCH_HOST']}:{os.environ['ELASTICSEARCH_PORT']}"
        self.es_conversation_index = ""
        self.llm_endpoint = (
            f"http://{os.environ['VLLM_HOST']}:{os.environ['VLLM_H_PORT']}"
        )
        self.model_name = os.environ["MODEL_NAME"]
        self.experiment_notes = ""  # For writing notes afterwards
        self.save_configs()

    def save_configs(self):
        """
        Increment exp number and save the parameters
        """
        exp_count = len(os.listdir("configs"))

        with open(f"configs/experiment_{exp_count}.json", "w") as f:
            json.dump(vars(self), f, indent=4)
