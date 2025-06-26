from autogen_core.tools import FunctionTool
from configs.tools_config import PLACEHOLDER_tool_cfg

# TODO: Replace all PLACEHOLDER with concrete names


def PLACEHOLDER_tool() -> str:
    """
    Extracts the lab order information from a document based on an admission ID.

    Returns:
        str: A string containing the lab order information if found, or "NIL" if the
        "LABS" section is not found.
    """
    # DO SOMETHING
    return ""


placeholder_tool = FunctionTool(
    PLACEHOLDER_tool_cfg, description=PLACEHOLDER_tool_cfg["description"]
)
