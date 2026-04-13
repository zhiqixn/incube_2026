# Planner Output Schema

Use this schema when converting ingested input into a planning-stage handoff.

## Top-Level Shape

```json
{
  "objective": {
    "primary": "string",
    "secondary": ["string"],
    "success_definition": "string"
  },
  "scenario": {
    "summary": "string",
    "environment": "string",
    "constraints": ["string"],
    "assumptions": ["string"]
  },
  "entities": [
    {
      "entity_id": "string",
      "role": "string",
      "capabilities": ["string"],
      "limitations": ["string"]
    }
  ],
  "planned_actions": [
    {
      "action_id": "string",
      "action_name": "string",
      "catalog_status": "cataloged | provisional",
      "owner_entity": "string",
      "supporting_entities": ["string"],
      "objective_link": "string",
      "why_selected": "string",
      "scenario_fit": "string",
      "subactions": [
        {
          "subaction_id": "string",
          "intent": "string",
          "expected_effect": "string",
          "dependencies": ["string"]
        }
      ],
      "constraints": ["string"],
      "success_signals": ["string"],
      "generator_handoff": {
        "expand_next": ["string"],
        "open_questions": ["string"]
      }
    }
  ]
}
```

## Notes

- `why_selected` explains the action choice at planner level.
- `scenario_fit` explains why this action fits the specific environment or threat model.
- `subactions` should remain generator-ready and not collapse into implementation detail.
- `expand_next` is the exact list of subactions or components the generator should build next.

## Minimal Planning Standard

Every plan should answer:
- what is the mission objective
- which entities are participating
- which actions each entity will perform
- how each action breaks into subactions
- why the chosen actions are appropriate
- what the generator should elaborate next
