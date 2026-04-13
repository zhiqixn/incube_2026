# Skills

This directory contains AgentSkills-compliant skills for the incube_environment agent system. Skills are discovered and loaded by the DeepAgents library via `create_deep_agent(skills=[...])`.

## Directory Structure

Each skill is a folder containing a `SKILL.md` file and optional subdirectories:

```
skills/
├── planner-skill/
│   ├── SKILL.md              # Required: frontmatter + instructions
│   ├── references/           # Optional: documentation the agent reads on demand
│   │   ├── action_families.md
│   │   ├── action_library.autonodyne.csv
│   │   └── planner_output_schema.md
│   └── scripts/              # Optional: executable helpers
│       └── validate_action_library.py
├── generator-skill/          # (example future skill)
│   ├── SKILL.md
│   └── references/
└── ...
```

## SKILL.md Format

Every `SKILL.md` must contain YAML frontmatter followed by Markdown instructions:

```md
---
name: your-skill-name
description: Describe what this skill does and when to use it. Include keywords users are likely to say.
license: MIT                    # optional
compatibility: Requires X       # optional
metadata:                       # optional
  author: your-team
  version: "1.0"
allowed-tools: tool_name        # optional: space-delimited tool names
---

# Skill Title

## Purpose
Explain the task this skill handles.

## When to Use
- Trigger case 1
- Trigger case 2

## Workflow
1. Step one
2. Step two

## Gotchas
- Non-obvious fact 1
- Non-obvious fact 2
```

### Frontmatter Rules

| Field | Required | Rules |
|---|---|---|
| `name` | Yes | 1-64 chars, lowercase letters + numbers + hyphens only. Must match the parent directory name. |
| `description` | Yes | 1-1024 chars. Should describe both **what** the skill does and **when** to use it. |
| `license` | No | Short license identifier |
| `compatibility` | No | Environment requirements |
| `metadata` | No | Arbitrary key/value strings |
| `allowed-tools` | No | Space-delimited list of pre-approved tool names |

## How Skills Are Loaded

Skills are loaded by the DeepAgents library via `create_deep_agent()`:

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=llm,
    tools=[...],
    system_prompt="...",
    skills=["skills/planner-skill/"],  # Path to skill directories
)
```

### Progressive Disclosure

1. **Discovery**: The agent sees only `name` and `description` from each skill's frontmatter
2. **Activation**: If the task matches, the agent loads the full `SKILL.md` body
3. **Execution**: The agent follows instructions and optionally reads `references/` or runs `scripts/`

## How to Add a New Skill

### 1. Create the skill directory

```bash
mkdir -p skills/my-new-skill/references
mkdir -p skills/my-new-skill/scripts
mkdir -p skills/my-new-skill/assets
```

### 2. Write SKILL.md

Create `skills/my-new-skill/SKILL.md` with frontmatter and instructions.

**Tips for good descriptions** (from the AgentSkills spec):
- Include both **what** the skill does and **when** to use it
- Use concrete keywords likely to appear in real user prompts
- Avoid vague descriptions that fail to trigger when they should
- Avoid overly broad descriptions that trigger on wrong tasks

### 3. Add references (optional)

Place documentation files in `references/`. Reference them from `SKILL.md` using relative paths:

```md
See [the reference guide](./references/REFERENCE.md) for details.
```

### 4. Add scripts (optional)

Place executable helpers in `scripts/`. Scripts should:
- Be self-contained or document dependencies clearly
- Support `--help`
- Print useful error messages
- Avoid interactive prompts

Reference them from `SKILL.md`:

```md
Run `scripts/validate.py` to check the configuration.
```

### 5. Wire the skill into an agent

In `agents/agent_langgraph.py`, add the skill path to the agent's `skills` parameter:

```python
my_agent = create_deep_agent(
    model=llm,
    tools=[...],
    system_prompt="...",
    skills=[
        "skills/planner-skill/",
        "skills/my-new-skill/",   # <-- Add your new skill
    ],
)
```

### 6. Validate

Check that:
- The `name` field matches the directory name
- The `description` is present and 1-1024 characters
- The markdown body is non-empty
- Any referenced files in `references/` exist
- Any scripts in `scripts/` are executable and have `--help`

## Current Skills

| Skill | Directory | Used By | Description |
|---|---|---|---|
| `planner-skill` | `skills/planner-skill/` | planner agent | Turns ingested input into planning-stage objectives, entities, actions, and subactions |

## References

- [AgentSkills Specification](https://agentskills.io/specification)
- [DeepAgents Skills Documentation](https://docs.langchain.com/oss/python/deepagents/skills)
- [Local DeepAgents Reference](../../../docs/deepagents-skills-reference.md)
- [Skills Architecture Document](../../../docs/skills-architecture.md)
