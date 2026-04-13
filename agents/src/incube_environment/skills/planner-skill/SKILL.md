---
name: planner-skill
description: Use when an ingestion layer has already collected scenario or mission input and the task is to turn that input into planning-stage objectives, entities, actions, and subactions for a downstream generator. This skill maps scenarios to a reusable action library, decomposes each chosen action at planner granularity, and produces a generator-ready handoff without building implementation details.
---

# Planner Skill

This skill is for the planning stage only.

It sits between:
- an ingestion layer that captures or normalizes source material
- a downstream generator that turns approved subactions into detailed building blocks

The planner should decide what needs to happen and who should do it. The generator should decide how to build each subaction rigorously.

## Planner Boundary

Use this skill to produce:
- the objective
- scenario framing
- entities and their roles
- recommended actions for each entity
- planner-level subactions for each action
- rationale and constraints
- a clean handoff payload for the generator stage

Do not:
- write implementation-level blocks
- over-specify mechanics that belong in the generator
- invent tactical detail that is not supported by the input or the action library

## When NOT to Use

Do not activate this skill when:
- no ingestion layer has run yet and the input is still raw or unstructured
- the task is to build implementation-level detail for a subaction (that belongs to the generator stage)
- the scenario is already fully planned and only generation or execution remains

## Workflow

1. Normalize the ingested input into plain planning language.
2. Identify the primary objective and any secondary objectives.
3. Extract entities, roles, capabilities, constraints, and environment.
4. Read [planner_output_schema.md](./references/planner_output_schema.md).
5. Read [action_families.md](./references/action_families.md).
6. Consult [action_library.autonodyne.csv](./references/action_library.autonodyne.csv) for seeded behaviors and scenarios.
7. Choose the smallest set of actions that satisfies the objective.
8. Decompose each chosen action with its family template, then adapt the subactions to the scenario.
9. Produce a generator-ready handoff that preserves rationale, assumptions, and unresolved gaps.

## Action Selection Rules

- Prefer cataloged actions over invented actions.
- Reuse the exact catalog action name when there is a close semantic match.
- Use aliases only to improve retrieval or traceability.
- If no catalog action fits, create a provisional action and mark it `catalog_status: provisional`.
- Choose actions based on the objective, not just keyword overlap.
- Keep the action list minimal. Fewer well-scoped actions are better than a long list of overlapping actions.

## Decomposition Rules

- Use the action family as the default decomposition template.
- Subactions should be planner-grade steps, not implementation details.
- Each subaction should state intent and expected effect.
- Decomposition should be entity-aware. If multiple entities participate, make ownership explicit.
- Include assumptions or dependencies only when they affect action choice or sequencing.

## Output Expectations

The planner output should be structured enough for a downstream generator to expand without re-deciding the plan.

Every selected action should include:
- `action_id`
- `action_name`
- `catalog_status`
- `owner_entity`
- `supporting_entities`
- `objective_link`
- `why_selected`
- `scenario_fit`
- `subactions`
- `constraints`
- `success_signals`
- `generator_handoff`

Use the schema and example in [planner_output_schema.md](./references/planner_output_schema.md).

## Source Library

The seeded catalog in [action_library.autonodyne.csv](./references/action_library.autonodyne.csv) is derived from:
- Autonodyne Autonomy Behaviors 26 Oct 2019 (source PDF, located outside the skill directory at `../sample_docs/`)

The catalog is intentionally compact. It stores stable planner-facing fields:
- action id
- action name and aliases
- action family
- one-line summary
- representative commercial scenarios
- representative defense scenarios
- source revision date
- tags

When the compact catalog is not enough, inspect the source PDF directly for nuance before inventing behavior.

## Scalability Pattern

Keep the skill lean and add scale through references:
- add new source catalogs as additional `references/action_library.*.csv` files
- keep family decomposition logic in [action_families.md](./references/action_families.md)
- keep planner output rules in [planner_output_schema.md](./references/planner_output_schema.md)
- validate catalogs with `python scripts/validate_action_library.py` (run from the skill root directory)

This keeps the main skill stable while letting the action repository grow.

## Fallback Behavior

If the input implies an uncataloged action:
- create a provisional action id in snake case
- assign the closest family
- explain why the existing catalog was insufficient
- keep the provisional action narrow and scenario-specific

## Success Criteria

A good planner output:
- names the objective clearly
- assigns actions to entities cleanly
- uses reusable catalog actions where possible
- decomposes actions into generator-ready subactions
- preserves enough rationale that the generator does not need to reinterpret the mission
