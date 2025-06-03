## TODO List:
- How can we make delegate_tool more cohesive like the other tools?
    - Today, we have a workaround in order for us to be able to get agents' description, by instantiating `FunctionTool` of delegate_tool inside the agent instantiation, rather than `tools` itself
    - The design is not consistent with the rest 
- Revise autogen version to 0.5.x