# Platform Capability Reference

## Quick reference table

| Attribute | quadrotor | fixed_wing | usv | ugv |
|-----------|-----------|------------|-----|-----|
| **Domain** | air | air | sea | land |
| **Exploration** | full | limited (wide_area_only) | full | full |
| **Tracking** | yes | yes | yes | yes |
| **Encirclement** | yes | **NO** | yes | yes |
| **Handoff send to** | usv, ugv | quadrotor, usv | usv, ugv | **NONE** |
| **Handoff recv from** | quadrotor, fixed_wing | fixed_wing, quadrotor | quadrotor, fixed_wing, usv | quadrotor, usv |
| **Sensors** | RGB, thermal, GPS, IMU | RGB, thermal, GPS, IMU | RGB, thermal, **radar**, GPS, IMU | RGB, thermal, **lidar**, GPS, IMU |
| **Night capable** | yes | yes | yes | yes |
| **Detection range** | 80 m | 120 m | 100 m | 40 m |
| **FOV** | 90 deg | 70 deg | 120 deg | 100 deg |
| **Endurance** | 35 min | 90 min | 360 min | 240 min |
| **Reserve** | 20% | 25% | 20% | 20% |
| **Max mission time** | 25 min | -- | -- | -- |
| **Max speed** | 12 m/s | 22 m/s | 6 m/s | 3 m/s |
| **Cruise speed** | 8 m/s | 18 m/s | 4.5 m/s | 2 m/s |
| **Can hover** | yes | **NO** | n/a | n/a |
| **Min turning radius** | -- | 60 m | -- | 2.5 m |
| **Min safe separation** | 10 m | 20 m | 12 m | 5 m |
| **Search patterns** | lawnmower, spiral | racetrack, corridor_pass | sector_scan, perimeter, shoreline_sweep | corridor_sweep, perimeter, waypoint_patrol |
| **Max track target speed** | 15 m/s | 25 m/s | 8 m/s | 4 m/s |
| **Encircle min team** | 3 | n/a | 3 | 3 |
| **Encircle allowed domains** | air, land, sea | n/a | sea, air | land, air |
| **Encircle radius range** | 10-50 m | n/a | 12-60 m | 15-40 m |
| **Recovery action** | return_home_and_land | return_to_safe_zone | return_home | return_home |
| **Abort battery** | 20% | 25% | 20% | 20% |
| **Must land on abort** | yes | no | no | no |
| **Recovery speed** | 10 m/s | -- | -- | -- |
| **Comms range** | 1000 m | 5000 m | 3000 m | 500 m |
| **Max teammates** | 5 | -- | -- | -- |

---

## Task constraints (detailed)

### Exploration constraints

| Constraint | quadrotor | fixed_wing | usv | ugv |
|------------|-----------|------------|-----|-----|
| **Mode** | full | wide_area_only | full | full |
| **Allowed patterns** | lawnmower, spiral | racetrack, corridor_pass | sector_scan, perimeter, shoreline_sweep | corridor_sweep, perimeter, waypoint_patrol |
| **Disallowed patterns** | -- | spiral, hover_viewpoint_hopping, dense_cell_decomposition | -- | open_water_sector_scan, aerial_lawnmower |
| **Min altitude** | 20 m | 80 m | n/a | n/a |
| **Max altitude** | 80 m | 250 m | n/a | n/a |
| **Operating altitude range** | 5-120 m | up to 300 m | n/a | n/a |
| **Requires forward motion** | no | yes | no | no |
| **Requires water access** | no | no | yes | no |
| **Requires traversable ground** | no | no | no | yes |
| **Preferred partition shape** | -- | -- | coastal_or_sector | corridor_or_bounded_zone |

### Tracking constraints

| Constraint | quadrotor | fixed_wing | usv | ugv |
|------------|-----------|------------|-----|-----|
| **Max target speed** | 15 m/s | 25 m/s | 8 m/s | 4 m/s |
| **Max tracking distance** | 100 m | -- | -- | -- |
| **Requires line of sight** | yes | -- | yes | -- |
| **Requires continuous motion** | no | yes | no | no |
| **Max tracking turn rate** | -- | 15 deg/s | -- | -- |
| **Max intercept angle** | -- | -- | 60 deg | -- |
| **Preferred target domains** | -- | -- | sea, littoral | land, shoreline |
| **Preferred role** | -- | overwatch | -- | -- |

### Encirclement constraints

| Constraint | quadrotor | fixed_wing | usv | ugv |
|------------|-----------|------------|-----|-----|
| **Supported** | yes | **NO** | yes | yes |
| **Min team size** | 3 | -- | 3 | 3 |
| **Allowed domains** | air, land, sea | -- | sea, air | land, air |
| **Min radius** | 10 m | -- | 12 m | 15 m |
| **Max radius** | 50 m | -- | 60 m | 40 m |
| **Max vertical separation** | 100 m | -- | -- | -- |
| **Default radius** | 18 m | -- | 18 m | 18 m |
| **Default standoff** | 10 m | -- | 10 m | 10 m |

### Motion and terrain constraints

| Constraint | quadrotor | fixed_wing | usv | ugv |
|------------|-----------|------------|-----|-----|
| **Max acceleration** | 4.0 m/s2 | -- | -- | -- |
| **Min speed** | -- | 12 m/s | -- | -- |
| **Min turning radius** | -- | 60 m | -- | 2.5 m |
| **Can hover** | yes | **NO** | n/a | n/a |
| **Wind limit** | 12 m/s | -- | -- | -- |
| **Rain tolerance** | low | -- | -- | -- |
| **Wave height limit** | -- | -- | 2.0 m | -- |
| **Max current** | -- | -- | 2.0 m/s | -- |
| **Shoreline clearance** | -- | -- | 10 m | -- |
| **Operating region** | -- | -- | water_only | -- |
| **Max slope** | -- | -- | -- | 20 deg |
| **Obstacle clearance** | -- | -- | -- | 0.5 m |
| **Terrain types** | -- | -- | -- | road, grass, urban |

---

## BT node availability per platform

Nodes marked with **x** are available for that platform type.

### Mission nodes

| Node | quadrotor | fixed_wing | usv | ugv |
|------|:---------:|:----------:|:---:|:---:|
| mission_GetPolygonCentroid | x | x | x | x |
| mission_LLAToPose | x | x | x | x |
| mission_OverridePoseAltitude | x | x | -- | -- |
| mission_PointToPoseStamped | x | x | x | x |
| mission_SetAgentTask | x | x | x | x |
| mission_SetTeamTask | x | x | x | x |
| mission_IsAgentInArea | x | x | x | x |
| mission_IsAgentTask | x | x | x | x |

### Controller nodes

| Node | quadrotor | fixed_wing | usv | ugv |
|------|:---------:|:----------:|:---:|:---:|
| controller_CommandArm | x | -- | -- | -- |
| controller_CommandLand | x | -- | -- | -- |
| controller_CommandTakeOff | x | -- | -- | -- |
| controller_SetHome | x | x | -- | -- |
| controller_SetMode | x | x | -- | -- |
| controller_SetPointLocal | x | x | x | -- |
| controller_BatteryOK | x | x | x | x |
| controller_StateOK | x | x | x | x |

### Navigation nodes

| Node | quadrotor | fixed_wing | usv | ugv |
|------|:---------:|:----------:|:---:|:---:|
| navigation_NavigateToPose | x | x | x | x |

### Exploration nodes

| Node | quadrotor | fixed_wing | usv | ugv |
|------|:---------:|:----------:|:---:|:---:|
| exploration_AssignPartitions | x | -- | x | x |
| exploration_DeconflictAssignments | x | -- | x | x |
| exploration_FindIngressPoint | x | x | x | x |
| exploration_GetAgentAssignedPartitionId | x | -- | x | x |
| exploration_GetPartitionPolygon | x | x | x | x |
| exploration_GetSearchArea | x | x | x | x |
| exploration_PartitionSearchArea | x | -- | x | x |
| exploration_PlanNextViewpoint | x | x | x | x |
| exploration_SetAgentExplorationStatus | x | x | x | x |
| exploration_SetPartitionAssignments | x | -- | x | x |
| exploration_SetPartitionCompletion | x | -- | x | x |
| exploration_SetPartitions | x | -- | x | x |
| exploration_IsAllPartitionsComplete | x | -- | x | x |
| exploration_IsPartitionComplete | x | -- | x | x |
| exploration_IsPartitionSet | x | -- | x | x |

### Engagement nodes

| Node | quadrotor | fixed_wing | usv | ugv |
|------|:---------:|:----------:|:---:|:---:|
| TargetDetected | x | x | x | x |
| HandoffTarget | x | x | x | -- |
| TargetAssigned | x | x | x | x |
| TrackTarget | x | x | x | x |
| TrackStable | x | x | x | x |
| EncircleTarget | x | -- | x | x |

---

## Platform default values

Default values per platform. Use these when the mission spec does not
override them.

### quadrotor

| Parameter | Default |
|-----------|---------|
| controller_CommandTakeOff altitude | 30.0 m |
| controller_SetMode mode | OFFBOARD |
| controller_BatteryOK min_battery_pct | 20.0% |
| mission_SetAgentTask task | search |
| exploration_SetAgentExplorationStatus status | searching |
| navigation_NavigateToPose pose | {goal_pose} |
| TargetDetected source_vehicle | {agent_id} |
| TrackTarget vehicle_id / target_id | {agent_id} / {target_id} |
| EncircleTarget radius_m | 18.0 m |
| EncircleTarget standoff_m | 10.0 m |
| search_pattern | lawnmower |
| home_pose | home_uav |
| takeoff_altitude_m | 30.0 m |

### fixed_wing

| Parameter | Default |
|-----------|---------|
| controller_SetMode mode | AUTO |
| controller_BatteryOK min_battery_pct | 25.0% |
| mission_SetAgentTask task | overwatch |
| exploration_SetAgentExplorationStatus status | searching |
| TargetDetected source_vehicle | {agent_id} |
| TrackTarget vehicle_id / target_id | {agent_id} / {target_id} |
| search_pattern | racetrack |
| home_pose | home_fixed_wing |

### usv

| Parameter | Default |
|-----------|---------|
| controller_BatteryOK min_battery_pct | 20.0% |
| mission_SetAgentTask task | track |
| exploration_SetAgentExplorationStatus status | searching |
| navigation_NavigateToPose pose | {goal_pose} |
| TargetDetected source_vehicle | {agent_id} |
| HandoffTarget vehicle_id / target_id | {agent_id} / {target_id} |
| TrackTarget vehicle_id / target_id | {agent_id} / {target_id} |
| EncircleTarget radius_m | 18.0 m |
| EncircleTarget standoff_m | 10.0 m |
| search_pattern | sector_scan |
| home_pose | home_usv |

### ugv

| Parameter | Default |
|-----------|---------|
| controller_BatteryOK min_battery_pct | 20.0% |
| mission_SetAgentTask task | search |
| exploration_SetAgentExplorationStatus status | searching |
| navigation_NavigateToPose pose | {goal_pose} |
| TargetDetected source_vehicle | {agent_id} |
| TrackTarget vehicle_id / target_id | {agent_id} / {target_id} |
| EncircleTarget radius_m | 18.0 m |
| EncircleTarget standoff_m | 10.0 m |
| search_pattern | corridor_sweep |
| home_pose | home_ugv |

---

## Feasibility parameters

Use these to validate that the mission is achievable.

| Parameter | quadrotor | fixed_wing | usv | ugv |
|-----------|-----------|------------|-----|-----|
| Endurance (min) | 35 | 90 | 360 | 240 |
| Reserve (%) | 20 | 25 | 20 | 20 |
| Transit speed (m/s) | 10.0 | 18.0 | 4.5 | 2.0 |
| Coverage rate (m2/min) | 15,000 | 35,000 | 7,000 | 2,500 |
| Max partition area (m2) | 400,000 | 1,200,000 | 500,000 | 120,000 |
| Min partition area (m2) | -- | 80,000 | -- | -- |
| Max mission time (min) | 25 | -- | -- | -- |
| Climb rate (m/s) | 3.0 | -- | -- | -- |

---

## Policy

| Rule | Value |
|------|-------|
| **Root control when priority=safety** | `ReactiveFallback` |

When the mission spec sets `constraints.soft.priority: safety`, the BT root
MUST be a `ReactiveFallback` node. This re-evaluates safety conditions
(battery, geofence, restricted zones) on every tick before continuing the
mission sequence. If any safety condition fails, execution falls through to
the recovery branch.
