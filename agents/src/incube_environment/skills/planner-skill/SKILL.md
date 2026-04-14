---
name: plan-mission
description: >
  Decomposes a multi-domain autonomous mission specification into a structured
  high-level action plan. Assigns fleet assets to Search, Detect, Track, and
  Encircle actions with behavior chains and sequencing. Use when planning a
  mission, decomposing a mission spec, or allocating assets to mission phases.
  Takes a mission_spec.yaml as input. Platform capabilities are embedded in
  the skill references.
---

# Mission Planner

Produce a structured, human-readable **mission action plan** from a mission
specification. The plan assigns fleet assets to mission phases, specifies
behavior chains per asset, and defines sequential/parallel ordering. This
plan is the intermediate artifact between mission intent and behavior tree
generation.

Platform capabilities, BT node availability, sensor specs, domain rules,
and behavior chains are **embedded in this skill's reference files**. Do not
search for a platform catalog -- use the references below.

## Step 0: Gather inputs

Locate the **mission specification**. Use whichever source is available,
checked in this order:

1. **Conversation context** -- if the user has already shared or opened a
   mission spec (e.g. pasted content, an open editor tab, or a previous
   message), use that directly.
2. **Working directory search** -- if not in context, search for
   `mission_spec.yaml` (or `**/mission_spec.yaml`) in the working directory.
3. **Ask the user** -- if neither is found, ask the user for the mission spec.

Once the mission spec is loaded, read the reference files bundled with this
skill to inform your planning:
- [references/platform-reference.md](references/platform-reference.md) -- platform capabilities, sensors, BT nodes, defaults, constraints
- [references/action-taxonomy.md](references/action-taxonomy.md) -- behavior chains and BT node port signatures
- [references/domain-rules.md](references/domain-rules.md) -- domain compatibility, handoff paths, environment rules

Do NOT produce YAML or XML. The output is structured plain text.

---

## Action types (toolkit)

The following action types are available building blocks. A mission may use
any combination of them. The decomposition methodology (below) determines
which are needed, how many of each, and in what order.

**Search** -- Explore an area to find something.
Control: Sequence. Chain: GoToArea (Timeout) -> SearchArea
(RetryUntilSuccessful + Timeout) with exploration_* and navigation nodes.
May end with TargetDetected or area-complete.

**Detect** -- Not a standalone phase. A transition state achieved during
Search when `TargetDetected` fires. Can trigger a handoff to another action.

**Track** -- Follow a detected or known target to establish stable tracking.
Control: Sequence. Chain: HandoffTarget (Timeout) -> TargetAssigned ->
TrackTarget (Timeout) -> TrackStable. Requires a target_id (from Detect or
from the mission spec directly).

**Encircle** -- Contain a target using multiple assets in parallel.
Control: Parallel (success_count=N, failure_count=1). Chain: EncircleTarget
per assigned agent. Requires stable tracking or known target position.

**Abort / Recover** -- Safety fallback for all vehicles.
Control: Sequence. Chain: ReturnHome per vehicle. Always present as the
recovery branch of the root control node.

Not every mission uses all action types. A patrol mission might only need
Search + Recover. A containment mission might skip Search if the target
location is already known.

### Naming convention

- Single-platform actions: `[Platform]_[Action]` (e.g. `UAV_Search`, `USV_Track`)
- Multi-platform joint actions: `Joint_[Action]` (e.g. `Joint_Encircle`)
- Phase IDs become BehaviorTree IDs in the compiled output.

See [references/action-taxonomy.md](references/action-taxonomy.md) for complete
behavior chains with full node names and port signatures.

---

## Critical rules (always enforce)

### Asset allocation rules

1. **Parallel exclusivity** -- an asset assigned to a phase CANNOT be
   simultaneously assigned to another phase that runs in parallel. A single
   vehicle can only execute one behavior chain at a time.
2. **Sequential reuse** -- an asset CAN be reused across sequential phases
   (Phase N then Phase N+1), but only if:
   (a) Phase N completes or the asset is explicitly released before Phase N+1.
   (b) Any handoff between phases is valid per `can_send_to`/`can_receive_from`.
   (c) The asset's platform supports the action in the new phase.
3. **Transition validity** -- when an asset moves from one phase to the next,
   the transition condition (e.g. TargetDetected, TrackStable) must be
   achievable by the preceding phase. If Phase N cannot produce the condition
   Phase N+1 depends on, the plan is invalid.

### Platform capability rules

4. Fixed-wing **cannot encircle** (encirclement.supported: false).
5. Fixed-wing **cannot hover** -- requires continuous forward motion.
6. Fixed-wing exploration is **wide_area_only** -- racetrack/corridor_pass patterns only.
7. UGV **cannot hand off targets** (handoff_target: false, can_send_to: []).
8. Handoff paths must follow `coordination.handoff.can_send_to` / `can_receive_from`.
9. Encirclement requires a **minimum team of 3** for all platform types.
10. Encirclement `allowed_domains` restricts which platform types may participate together.
11. Each platform has a **max tracking target speed** -- verify the target speed does not exceed it.
12. Air platforms must not track underwater/subsurface targets.
13. Sea platforms must not track land-only targets beyond the shoreline.

### Sensor and environment rules

- **Night** -- prefer thermal sensors; verify `night_capable: true`.
- **Degraded visibility** -- reduce effective detection range (~0.6-0.7x).
- **Rain** -- quadrotors have `low` rain tolerance; flag operational risk.
- **Sea state moderate+** -- check USV `wave_height_limit_m` (2.0 m).
- **Geofence** -- all assets must stay inside (`geofence_policy: must_stay_inside`).
- **Restricted zones** -- constrain search patterns and transit paths.

See [references/domain-rules.md](references/domain-rules.md) for the full ruleset.
See [references/platform-reference.md](references/platform-reference.md) for capability tables.

---

## Decomposition methodology

Follow these steps in order. Read the reference files as needed.

### Step 1: Parse mission objective

Read `mission.objective`. Map natural language verbs to actions:

| Verb in objective | Maps to action |
|-------------------|----------------|
| find, locate, search, detect, scan | Search |
| pursue, follow, shadow, monitor | Track |
| contain, encircle, surround, cordon | Encircle |
| observe, watch, overwatch | Overwatch (Track variant) |
| abort, retreat, return | Abort / Recover |

Identify the target description, operational environment, and domains involved.

### Step 2: Map fleet roles to actions

Read the `fleet` section. Map roles to primary actions:

| Role | Primary action |
|------|----------------|
| scout | Search |
| tracker | Track |
| interceptor | Encircle |
| overwatch | Wide-area monitoring (Search/Track variant) |

Group assets by their `group` field. Note which groups collaborate across phases.

### Step 3: Validate domain compatibility

For each asset-action pair:
- Verify the platform supports the action (check `capabilities` in platform-reference).
- Check domain compatibility with target and environment.
- Verify the platform has the required BT nodes (check BT node availability tables in platform-reference).
- Flag violations and suggest reassignment.

### Step 4: Determine which phases are needed and their sequencing

Derive phases from the mission objective -- do not assume a fixed pipeline.
Select action types from the toolkit (Search, Track, Encircle, etc.) based
on what the objective requires, then order them by dependency logic:

**Dependency rules:**
- Track requires a target_id. If the target is not known at mission start,
  a Search phase must precede Track to produce TargetDetected.
- Encircle requires a tracked target position. If not already tracked, a
  Track phase must precede Encircle to produce TrackStable.
- If the mission spec provides a known target location, Track or Encircle
  can be the first operational phase (no Search needed).
- Actions with no dependencies between them can run in Parallel.
  (e.g. multi-domain search across air + land simultaneously)
- Abort / Recover is always present as the recovery branch of the root
  control node. It is reactive, not sequential with mission phases.

**Root control:** if `constraints.soft.priority == safety`, use
`ReactiveFallback` as the root (re-checks safety every tick). Otherwise
use `Fallback`.

**Transitions between phases** are driven by conditions:
- Search -> Track: `TargetDetected`
- Track -> Encircle: `TrackStable`
- Any phase -> Abort: abort conditions (battery, operator, target lost)

### Step 5: Build behavior chains per asset

For each asset assigned to an action, construct the behavior chain from the
action taxonomy. Read [references/action-taxonomy.md](references/action-taxonomy.md)
for full chains with node names and ports.

- Select search pattern based on platform defaults and `preferences.search_style`.
- Include safety checks (BatteryOK, StateOK) at the start of each chain.
- Cross-check every BT node against the platform's `bt_nodes` list.

### Step 6: Define transitions and handoff points

For each phase transition, specify the condition that triggers it.
If a transition involves passing a target between assets (handoff):
- Identify the producer (e.g. detecting asset) and consumer (e.g. tracker).
- Verify the handoff path: producer `can_send_to` must include the consumer's
  platform type, and consumer `can_receive_from` must include the producer's.
- Note the `handoff_mode` from `preferences.coordination.handoff_mode`.
- If no handoff is needed (same asset continues), note that explicitly.

### Step 7: Define recovery / abort policy

- List all `mission.abort_conditions`.
- For each platform type, specify the recovery action from
  `recovery.preferred_abort_action` in platform-reference.
- All vehicles execute ReturnHome in a Sequence.
- Note battery abort thresholds per platform.

### Step 8: Apply tuning parameters

- Map `tuning.timeout_s` values to each phase/action.
- Apply `tuning.retry_count` to retryable actions (Search).
- Note `tuning.tick_hz` for BT execution rate.

### Step 9: Validate and degrade gracefully

After assembling the plan, run through the validation checklist. If the plan
fails validation (constraint violations, infeasible assignments, unresolvable
handoff paths, insufficient assets for a phase), do NOT give up. Instead,
iteratively degrade the plan:

**Degradation must respect dependencies.** Never drop or demote an action
that a remaining action depends on. If the phase chain is
Search -> Detect -> Track -> Encircle, degradation works **from the tail
inward**: Encircle is dropped before Track, Track before Search. Dropping
Search while keeping Track is invalid because Track depends on
TargetDetected which Search produces.

**Abort / Recover is never dropped** -- safety is non-negotiable.

**Degradation strategy (apply in order until a valid plan is produced):**
1. **Reduce scope** -- shrink the failing phase. E.g. reduce encirclement
   team size, narrow search area, simplify formation.
2. **Reassign assets** -- move assets from a later phase to resolve the
   constraint in an earlier one. E.g. pull an interceptor from encircle
   to fill a broken handoff path in tracking.
3. **Demote the action** -- replace a failing action with a simpler variant.
   E.g. replace Encircle with Track (shadow instead of contain), replace
   a multi-domain search with a single-domain search.
4. **Drop the tail action** -- remove the last (deepest-dependency) failing
   phase. Then check if any remaining phases depended on it and remove
   those too. Flag which `success_criteria` can no longer be met.

**On each attempt:**
- Log what failed validation and why.
- Log what was deprioritized or dropped.
- Re-validate the modified plan.
- Repeat until valid or all non-safety actions are exhausted.

If the plan cannot satisfy any mission objective even after degradation,
produce the best achievable plan and clearly state:
- Which actions were dropped and why.
- Which `success_criteria` are unachievable with the given fleet/constraints.
- What would be needed to restore them (e.g. "add 1 more quadrotor" or
  "relax encirclement team size to 2").

---

## Output format

The plan has three fixed sections (overview, recovery, validation) plus a
variable number of **phases derived from the mission**. Use the action type
templates below to build each phase. Number phases sequentially.

### Fixed header

```
================================================================
MISSION PLAN: [mission.id]
================================================================

MISSION OVERVIEW
  Objective:    [Paraphrase of mission.objective]
  Environment:  [type], [time_of_day], visibility=[visibility],
                weather=[weather], sea_state=[sea_state]
  Geofence:     [polygon_id]
  Restricted:   [comma-separated restricted zones]
  Fleet Size:   [N] assets across [domains]
  Root Control: [ReactiveFallback | Fallback] (priority=[safety|...])

FLEET ROSTER
  ID        | Domain | Platform    | Role        | Group       | Primary Action
  ----------|--------|-------------|-------------|-------------|---------------
  [id]      | [dom]  | [type]      | [role]      | [group]     | [action]
  ...

BLACKBOARD VARIABLES
  [list all variables that flow between phases, e.g.:]
  mission_area:          [area_id or geofence polygon]
  target_id:             (set at runtime by TargetDetected)
  geofence_id:           [polygon_id]
  restricted_zone_list:  [zones]

PHASE SEQUENCE
  [list derived phases in order, noting sequential vs parallel grouping]
  e.g. Phase 1 (Search) -> Phase 2 (Track) -> Phase 3 (Encircle)
  e.g. Phase 1a (UAV_Search) || Phase 1b (UGV_Search) -> Phase 2 (Track)

DEGRADATION LOG (omit if plan is fully achievable)
  Attempt [N]: [what failed validation and why]
  Action taken: [reduced scope / reassigned / demoted / dropped]
  Unmet criteria: [which success_criteria can no longer be satisfied]
  Recommendation: [what would restore full capability]
```

### Phase templates (use whichever the mission requires)

#### SEARCH phase template

```
================================================================
PHASE [N]: SEARCH ([Action_Name])
================================================================
  Control:      Sequence
  Assigned:     [asset IDs]
  Dependencies: [predecessor phases, or "none"]

  Safety Check (CommonSafety subtree, per asset):
    -> controller_BatteryOK(agent_id=[id], min_battery_pct=[pct])
    -> controller_StateOK(agent_id=[id])

  GoToArea (Timeout: [go_to_area_timeout]s):
    1.  mission_SetAgentTask(agent_id=[id], task=search)
    2.  mission_GetPolygonCentroid(polygon={mission_area})
    3.  mission_LLAToPose(lla=centroid)
    4.  mission_OverridePoseAltitude(pose, altitude=[alt])    [air only]
    5.  navigation_NavigateToPose(agent_id=[id], pose=...)

  SearchArea (RetryUntilSuccessful: [retry_count]x, Timeout: [search_timeout]s):
    6.  exploration_GetSearchArea(mission_area={mission_area})
    7.  exploration_PartitionSearchArea(search_area=...)
    8.  exploration_AssignPartitions(agents=[list], partitions=...)
    9.  exploration_DeconflictAssignments(assignments=...)
   10.  exploration_GetAgentAssignedPartitionId(agent_id=[id], ...)
   11.  exploration_GetPartitionPolygon(partitions=..., partition_id=...)
   12.  exploration_FindIngressPoint(polygon=...)
   13.  mission_PointToPoseStamped(point=...)
   14.  navigation_NavigateToPose(agent_id=[id], pose=...)
   15.  exploration_PlanNextViewpoint(polygon=..., agent_id=[id])
   16.  mission_PointToPoseStamped(point=...)
   17.  navigation_NavigateToPose(agent_id=[id], pose=...)
        [LOOP steps 15-17 until exit condition]

  Exit Condition: [TargetDetected | IsAllPartitionsComplete | timeout]
  Search Pattern: [pattern from platform defaults/preferences]
  Sensor Mode:    [thermal | rgb] (based on time_of_day/visibility)
  Notes:          [domain-specific notes, e.g. degraded visibility adjustments]
  Transition:     [what phase follows and why]

  [If multiple domains search in parallel, split into sub-phases:
   e.g. PHASE Na: UAV_Search, PHASE Nb: UGV_Search as Parallel children]
```

#### TRACK phase template

```
================================================================
PHASE [N]: TRACK ([Action_Name])
================================================================
  Control:      Sequence
  Assigned:     [asset IDs]
  Dependencies: [phase that provides target_id]

  Safety Check (CommonSafety subtree, per asset):
    -> controller_BatteryOK(agent_id=[id], min_battery_pct=[pct])
    -> controller_StateOK(agent_id=[id])

  Handoff (if target comes from another asset):
    From:       [producing_asset_id] ([platform_type])
    To:         [tracking_asset_id] ([platform_type])
    Mode:       [handoff_mode from preferences]
    Valid path: [confirm can_send_to / can_receive_from]

  Behavior Chain:
    1. HandoffTarget(vehicle_id=[id], target_id={target_id})
       (Timeout: [handoff_target_timeout]s)
    2. TargetAssigned(vehicle_id=[id], target_id={target_id})
    3. TrackTarget(vehicle_id=[id], target_id={target_id})
       (Timeout: [track_timeout]s)
    4. TrackStable(vehicle_id=[id], target_id={target_id})

  Notes:      [tracking constraints, e.g. max target speed vs platform limit]
  Transition: [what phase follows and why]
```

#### ENCIRCLE phase template

```
================================================================
PHASE [N]: ENCIRCLE ([Action_Name])
================================================================
  Control:      Parallel (success_count=[N], failure_count=1)
  Assigned:     [asset IDs] (minimum 3)
  Dependencies: [phase that establishes target tracking or position]
  Timeout:      [encircle_timeout]s (wraps entire Parallel)

  Per-asset (parallel):
    EncircleTarget(vehicle_id=[id], target_id={target_id},
                   radius_m=[r], standoff_m=[s])

  Formation:    [formation preference from mission spec]
  Strategy:     [encircle_strategy from preferences]
  Domain Mix:   [domains participating -- verify allowed_domains]
  Notes:        [radius intersection check, team size validation]
```

#### Other phase types

If the mission requires actions not covered above (e.g. patrol, escort,
relay), construct a phase using the same structure: Control type, assigned
assets, dependencies, safety check, behavior chain from available BT nodes,
exit condition, and transition. Reference the action-taxonomy for available
nodes and the platform-reference for compatibility.

### Fixed footer

```
================================================================
RECOVERY POLICY
================================================================
  Trigger:  [list abort_conditions from mission spec]
  Control:  Sequence
  Mode:     return_home_all

  Per-Asset Recovery:
    [id] ([platform_type]): [preferred_abort_action], abort_battery=[pct]%
    ...

================================================================
VALIDATION CHECKLIST
================================================================
  [ ] All assets assigned to at least one phase
  [ ] No asset assigned to two parallel phases simultaneously
  [ ] Assets reused across sequential phases have valid transitions
  [ ] No platform assigned to an unsupported action
  [ ] Handoff paths valid per can_send_to / can_receive_from
  [ ] Encirclement team size >= min_team_size per platform
  [ ] Search patterns match platform allowed_patterns
  [ ] Sensor modes appropriate for environment (night/day/visibility)
  [ ] Timeouts specified for all timed phases
  [ ] Battery thresholds set per platform
  [ ] Geofence and restricted zones noted and respected
  [ ] Domain compatibility verified for all assignments
  [ ] Fixed-wing not assigned to encircle or hover tasks
  [ ] UGV not assigned to handoff tasks
  [ ] Phase dependencies form a valid DAG (no circular deps)
  [ ] Each transition condition is producible by its predecessor phase
  [ ] All success_criteria from mission spec are achievable by the phases
```

---

## Important reminders

- If `constraints.soft.priority == safety`, the BT root MUST be `ReactiveFallback`
  (checks safety conditions every tick before continuing the mission sequence).
- If a fixed_wing has role `overwatch`, treat it as a wide-area search asset with
  limited exploration. It cannot hover at viewpoints.
- If multiple assets perform the same action type across different domains (e.g.
  air search + land search), they should be **parallel sub-phases**.
- When `coordination.handoff_mode: producer_consumer`, annotate which asset is
  the producer (detecting) and which is the consumer (tracking).
- Always cross-check the platform-reference BT node availability tables to
  confirm every node in the behavior chain is available for the assigned platform.
- Air platforms need a launch sequence before mission actions:
  `controller_SetHome -> controller_CommandArm -> controller_SetMode ->
  controller_CommandTakeOff`. Include a Launch phase if the mission requires it.
- Verify that the derived phases collectively satisfy all `success_criteria`
  from the mission spec. If a criterion cannot be met, flag it.
- The number and type of phases is driven by the mission objective. Do not
  include phases the mission does not need.
