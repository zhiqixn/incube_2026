# Action Taxonomy and Behavior Node Reference

## Complete behavior chains

### Search

Full chain for area search until target detection. The chain has two phases:
transit to the search area (GoToArea, wrapped in a Timeout), then the search
pattern itself (wrapped in RetryUntilSuccessful + Timeout).

```
Sequence:
  controller_BatteryOK(agent_id, min_battery_pct)        [COND]
  controller_StateOK(agent_id)                            [COND]
  mission_SetAgentTask(agent_id, task="search")

  --- Transit to search area (Timeout: go_to_area timeout) ---
  mission_GetPolygonCentroid(polygon={mission_area}) -> centroid
  mission_LLAToPose(lla=centroid) -> pose
  mission_OverridePoseAltitude(pose, altitude) -> pose_out   [air only]
  navigation_NavigateToPose(agent_id, pose=pose_out)      [STATEFUL]

  --- Search pattern (RetryUntilSuccessful + Timeout: search timeout) ---
  exploration_GetSearchArea(mission_area) -> search_area
  exploration_PartitionSearchArea(search_area) -> partitions
  exploration_SetPartitions(partitions)
  exploration_AssignPartitions(agents, partitions) -> assignments
  exploration_DeconflictAssignments(assignments) -> assignments_out
  exploration_SetPartitionAssignments(assignments)
  exploration_GetAgentAssignedPartitionId(agent_id, assignments) -> partition_id
  exploration_GetPartitionPolygon(partitions, partition_id) -> polygon
  exploration_FindIngressPoint(polygon) -> ingress_point
  mission_PointToPoseStamped(point=ingress_point) -> pose_stamped
  navigation_NavigateToPose(agent_id, pose=pose_stamped)  [STATEFUL]
  exploration_SetAgentExplorationStatus(agent_id, status="searching")

  RetryUntilSuccessful / Loop:
    exploration_PlanNextViewpoint(polygon, agent_id) -> viewpoint
    mission_PointToPoseStamped(point=viewpoint) -> pose_stamped
    navigation_NavigateToPose(agent_id, pose=pose_stamped)  [STATEFUL]

  Exit conditions:
    TargetDetected(source_vehicle=agent_id) -> target_id
    OR exploration_IsAllPartitionsComplete(partitions)
    OR exploration_IsPartitionComplete(partition_id)
```

### Track

Full chain for target handoff and stable tracking:

```
Sequence:
  controller_BatteryOK(agent_id, min_battery_pct)        [COND]
  controller_StateOK(agent_id)                            [COND]
  HandoffTarget(vehicle_id, target_id)
  TargetAssigned(vehicle_id, target_id)
  TrackTarget(vehicle_id, target_id)                      [STATEFUL]
  TrackStable(vehicle_id, target_id)                      [COND]
```

### Encircle

Parallel execution across all assigned encirclement agents:

```
Parallel (success_count=N, failure_count=1):
  EncircleTarget(vehicle_id=agent_1, target_id, radius_m, standoff_m)  [STATEFUL]
  EncircleTarget(vehicle_id=agent_2, target_id, radius_m, standoff_m)  [STATEFUL]
  EncircleTarget(vehicle_id=agent_3, target_id, radius_m, standoff_m)  [STATEFUL]
  ...
```

### Abort / Recover

Sequential recovery for all vehicles:

```
Sequence:
  ReturnHome(vehicle_id=vehicle_1)
  ReturnHome(vehicle_id=vehicle_2)
  ...
```

Recovery action per platform type (from platform-reference):
- quadrotor: `return_home_and_land`
- fixed_wing: `return_to_safe_zone`
- usv: `return_home`
- ugv: `return_home`

### Launch (air platforms)

Pre-mission launch sequence for air vehicles:

```
Sequence:
  controller_SetHome(agent_id, home_pose)
  controller_CommandArm(agent_id)
  controller_SetMode(agent_id, mode)
  controller_CommandTakeOff(agent_id, altitude)
```

### Common Safety subtree

Reusable safety check invoked at the start of each phase per vehicle:

```
Sequence:
  controller_BatteryOK(vehicle_id, min_battery_pct)       [COND]
  controller_StateOK(vehicle_id)                           [COND]
```

Extended with geofence/restricted-zone checks when the mission specifies them
(these are custom conditions, not in the base node set):
- `WithinGeofence(vehicle_id, geofence_id)`
- `OutsideRestrictedZone(vehicle_id, restricted_zone_list)`

---

## Parent action classes

Logical groupings of BT nodes by functional purpose (from the autonomy stack):

| Class | Nodes |
|-------|-------|
| **Search** | exploration_GetSearchArea, exploration_PartitionSearchArea, exploration_AssignPartitions, exploration_DeconflictAssignments, exploration_FindIngressPoint, exploration_GetAgentAssignedPartitionId, exploration_GetPartitionPolygon, exploration_PlanNextViewpoint, exploration_SetAgentExplorationStatus, exploration_SetPartitionAssignments, exploration_SetPartitionCompletion, exploration_SetPartitions, exploration_IsAllPartitionsComplete, exploration_IsPartitionComplete, exploration_IsPartitionSet, navigation_NavigateToPose |
| **Assign Task** | mission_SetAgentTask, mission_SetTeamTask |
| **Assign Area** | exploration_AssignPartitions, exploration_DeconflictAssignments, exploration_SetPartitionAssignments |
| **Detect** | TargetDetected |
| **Track** | TrackTarget, TrackStable |
| **Reassign Target** | HandoffTarget |
| **Follow-On** | EncircleTarget |
| **Navigate** | navigation_NavigateToPose, controller_SetPointLocal |
| **Launch / Recover** | controller_CommandArm, controller_CommandTakeOff, controller_CommandLand, controller_SetMode, controller_SetHome |
| **Health Monitoring** | controller_BatteryOK, controller_StateOK |
| **Task Monitoring** | mission_IsAgentInArea, mission_IsAgentTask, exploration_IsAllPartitionsComplete, exploration_IsPartitionComplete, exploration_IsPartitionSet, TrackStable |
| **Delineate** | mission_GetPolygonCentroid, exploration_GetSearchArea, exploration_GetPartitionPolygon |
| **PrepareNavigationTarget** | mission_LLAToPose, mission_OverridePoseAltitude, mission_PointToPoseStamped |
| **Partition Search Area** | exploration_PartitionSearchArea |
| **CueNextSearchMove** | exploration_PlanNextViewpoint |

---

## BT node port signatures

### Mission nodes

| Node | Type | Ports |
|------|------|-------|
| `mission_GetPolygonCentroid` | Action | in: `polygon` (string); out: `centroid` (string) |
| `mission_LLAToPose` | Action | in: `lla` (string); out: `pose` (string) |
| `mission_OverridePoseAltitude` | Action | in: `pose` (string), `altitude` (double); out: `pose_out` (string) |
| `mission_PointToPoseStamped` | Action | in: `point` (string); out: `pose_stamped` (string) |
| `mission_SetAgentTask` | Action | in: `agent_id` (string), `task` (string) |
| `mission_SetTeamTask` | Action | in: `team_id` (string), `task` (string) |
| `mission_IsAgentInArea` | Condition | in: `agent_id` (string), `area` (string) |
| `mission_IsAgentTask` | Condition | in: `agent_id` (string), `task` (string) |

### Controller nodes

| Node | Type | Ports |
|------|------|-------|
| `controller_CommandArm` | Action | in: `agent_id` (string) |
| `controller_CommandLand` | Action | in: `agent_id` (string) |
| `controller_CommandTakeOff` | Action | in: `agent_id` (string), `altitude` (double) |
| `controller_SetHome` | Action | in: `agent_id` (string), `home_pose` (string) |
| `controller_SetMode` | Action | in: `agent_id` (string), `mode` (string) |
| `controller_SetPointLocal` | Action | in: `agent_id` (string), `pose` (string) |
| `controller_BatteryOK` | Condition | in: `agent_id` (string), `min_battery_pct` (double) |
| `controller_StateOK` | Condition | in: `agent_id` (string) |

### Navigation nodes

| Node | Type | Ports |
|------|------|-------|
| `navigation_NavigateToPose` | Stateful | in: `agent_id` (string), `pose` (string) |

### Exploration nodes

| Node | Type | Ports |
|------|------|-------|
| `exploration_AssignPartitions` | Action | in: `agents` (string), `partitions` (string); out: `assignments` (string) |
| `exploration_DeconflictAssignments` | Action | in: `assignments` (string); out: `assignments_out` (string) |
| `exploration_FindIngressPoint` | Action | in: `polygon` (string); out: `ingress_point` (string) |
| `exploration_GetAgentAssignedPartitionId` | Action | in: `agent_id` (string), `assignments` (string); out: `partition_id` (string) |
| `exploration_GetPartitionPolygon` | Action | in: `partitions` (string), `partition_id` (string); out: `polygon` (string) |
| `exploration_GetSearchArea` | Action | in: `mission_area` (string); out: `search_area` (string) |
| `exploration_PartitionSearchArea` | Action | in: `search_area` (string); out: `partitions` (string) |
| `exploration_PlanNextViewpoint` | Action | in: `polygon` (string), `agent_id` (string); out: `viewpoint` (string) |
| `exploration_SetAgentExplorationStatus` | Action | in: `agent_id` (string), `status` (string) |
| `exploration_SetPartitionAssignments` | Action | in: `assignments` (string) |
| `exploration_SetPartitionCompletion` | Action | in: `partition_id` (string), `complete` (bool) |
| `exploration_SetPartitions` | Action | in: `partitions` (string) |
| `exploration_IsAllPartitionsComplete` | Condition | in: `partitions` (string) |
| `exploration_IsPartitionComplete` | Condition | in: `partition_id` (string) |
| `exploration_IsPartitionSet` | Condition | in: `partition_id` (string) |

### Engagement nodes

| Node | Type | Ports |
|------|------|-------|
| `TargetDetected` | Action | in: `source_vehicle` (string); out: `target_id` (string) |
| `HandoffTarget` | Action | in: `vehicle_id` (string), `target_id` (string) |
| `TargetAssigned` | Action | in: `vehicle_id` (string), `target_id` (string) |
| `TrackTarget` | Stateful | in: `vehicle_id` (string), `target_id` (string) |
| `TrackStable` | Condition | in: `vehicle_id` (string), `target_id` (string) |
| `EncircleTarget` | Stateful | in: `vehicle_id` (string), `target_id` (string), `radius_m` (double), `standoff_m` (double) |

---

## Control flow node types

| Node | Behavior |
|------|----------|
| `Sequence` | Tick children left-to-right. Fail on first FAILURE. Succeed when all succeed. |
| `Fallback` | Tick children left-to-right. Succeed on first SUCCESS. Fail when all fail. |
| `ReactiveFallback` | Re-evaluates from the first child every tick. Used as root when safety is priority. |
| `ReactiveSequence` | Re-evaluates from the first child every tick. |
| `Parallel` | Tick all children simultaneously. Configurable `success_count` and `failure_count` thresholds. |

## Decorator node types

| Node | Behavior |
|------|----------|
| `Timeout` | Fail child if it exceeds `msec` milliseconds. |
| `RetryUntilSuccessful` | Re-run child up to `num_attempts` times on failure. |
| `ForceSuccess` | Always return SUCCESS regardless of child result. |
| `ForceFailure` | Always return FAILURE regardless of child result. |
| `Inverter` | Invert child result (SUCCESS <-> FAILURE). |
