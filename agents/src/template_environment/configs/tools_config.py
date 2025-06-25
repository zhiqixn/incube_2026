# TODO: Replace all PLACEHOLDER with concrete names

delegate_cfg = {
    "description": (
        "Call this tool to delegate your task to other agents if there "
        "are any tasks outside of your expertise. "
        "Only delegate to these agents:\n\n{agents}\n\n"
        "Each DelegationTask data model should contain the fields "
        "'task', 'agent' and 'name'."
    )
}

PLACEHOLDER_tool_cfg = {"description": ""}
