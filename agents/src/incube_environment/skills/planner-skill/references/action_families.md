# Action Families

Use these families to keep decomposition consistent across many source libraries.

## `move`

Use for direct transit toward a destination or moving point.

Default subactions:
- identify destination or intercept target
- determine transit constraints
- compute route or pursuit logic
- execute movement
- confirm arrival or engagement geometry

## `hold`

Use for maintaining current or commanded state.

Default subactions:
- capture hold parameters
- stabilize position or state
- maintain until exit criteria
- monitor deviations and resource limits

## `coordinate`

Use for multi-entity alignment, formation, staging, sequencing, or handoff.

Default subactions:
- identify participating entities
- assign roles or geometry
- synchronize entry conditions
- maintain coordination or spacing
- transition or dissolve formation cleanly

## `observe`

Use for persistent observation of a point, object, or local scene.

Default subactions:
- identify point or subject of interest
- establish sensor-supporting position
- align sensor or vehicle posture
- collect and maintain observation
- report or hand off findings

## `area_cover`

Use for surveying, scanning, or partitioning a wider area.

Default subactions:
- define the area of interest
- divide coverage across entities
- assign paths or sectors
- execute collection pass
- merge findings and note gaps

## `deliver`

Use for payload delivery, spawning, transporting, or releasing subordinate assets.

Default subactions:
- prepare payload or carried asset
- compute ingress profile
- position for release or delivery
- execute transfer
- verify successful delivery or deployment

## `recover`

Use for returning, rejoining, landing, or safe recovery.

Default subactions:
- identify recovery target or location
- compute approach profile
- deconflict terminal movement
- execute recovery
- confirm safe recovered state

## `pathfind`

Use for path planning in constrained or adversarial environments.

Default subactions:
- identify origin destination and constraints
- build route options or cost map
- select preferred path
- monitor for changes
- replan when needed

## `relay`

Use for extending communications or shared sensing.

Default subactions:
- identify communication or sensing gap
- position relay asset
- verify connectivity or coverage
- maintain relay posture
- hand off or terminate when no longer needed

## `track`

Use for maintaining identity, location, targeting data, or shared learned state.

Default subactions:
- establish initial target or knowledge state
- maintain updates over time
- refine certainty or geometry
- share track or derived data
- trigger follow-on actions when thresholds are met

## `strike`

Use for kinetic or offensive effect generation.

Default subactions:
- identify target and effect intent
- position asset or effect chain
- validate firing or impact conditions
- execute offensive effect
- assess result and decide continue or abort

## `protect`

Use for defense, evasion, self-protection, and shielding behaviors.

Default subactions:
- identify protected asset or threat
- choose protective posture
- position or maneuver defensively
- monitor threat changes
- disengage or recover when threat ends

## `deceive`

Use for signature management, misdirection, spoofing, or intentional distraction.

Default subactions:
- identify observer or system to influence
- choose deception method
- execute misleading pattern or signature change
- monitor whether deception is effective
- terminate without compromising follow-on actions

## `sustain`

Use for endurance, refueling, cycling, or long-duration continuity.

Default subactions:
- identify persistence requirement
- assess available assets or fuel states
- schedule relief or sustainment event
- execute turnover or refuel
- verify continuity of mission effect

## `inspect`

Use for structured documentation, inspection, assessment, or evidence capture.

Default subactions:
- identify subject or scene
- choose inspection geometry
- execute capture pattern
- compile assessment or record
- mark completeness and unresolved gaps
