# Domain Compatibility and Environment Rules

## Domain compatibility rules

These rules MUST be enforced when assigning assets to actions.

### 1. Domain-action restrictions

| Rule | Detail |
|------|--------|
| Air platforms must not track underwater/subsurface targets | Hand off to sea platform |
| Sea platforms must not track land-only targets | Hand off to land or air platform |
| Land platforms cannot operate in water | UGV restricted to traversable ground |
| Sea platforms restricted to water regions | USV cannot traverse land |

### 2. Platform-specific restrictions

| Platform | Restriction | Impact |
|----------|-------------|--------|
| **fixed_wing** | Cannot encircle | `encirclement.supported: false` -- never assign to encircle phase |
| **fixed_wing** | Cannot hover | `can_hover: false` -- no spiral, no hover_viewpoint_hopping, no dense_cell_decomposition |
| **fixed_wing** | Limited exploration | `exploration: limited` -- wide_area_only; patterns restricted to racetrack, corridor_pass |
| **fixed_wing** | Requires forward motion | `requires_forward_motion: true` -- continuous motion for search and tracking |
| **ugv** | Cannot hand off targets | `handoff_target: false`, `can_send_to: []` -- never assign as handoff producer |
| **ugv** | Terrain restricted | `terrain_types: [road, grass, urban]`, `max_slope_deg: 20` |
| **usv** | Water only | `operating_region: water_only`, requires `shoreline_clearance_m: 10` |

### 3. Encirclement constraints

| Platform | Min team | Allowed partner domains | Radius range |
|----------|----------|------------------------|--------------|
| quadrotor | 3 | air, land, sea | 10-50 m |
| usv | 3 | sea, air | 12-60 m |
| ugv | 3 | land, air | 15-40 m |
| fixed_wing | **not supported** | -- | -- |

A valid encirclement team must:
- Have at least `min_team_size` members (3 for all platforms).
- Only include platforms from `allowed_domains` that are compatible with each other.
- Use a radius within the intersection of all participating platforms' radius ranges.

---

## Cross-domain handoff paths

Handoffs transfer target tracking responsibility between platforms.

### Valid handoff paths

| From (sender) | Can send to |
|----------------|-------------|
| quadrotor | usv, ugv |
| fixed_wing | quadrotor, usv |
| usv | usv, ugv |
| ugv | **nobody** (cannot hand off) |

### Receiving capabilities

| To (receiver) | Can receive from |
|----------------|-----------------|
| quadrotor | quadrotor, fixed_wing |
| fixed_wing | fixed_wing, quadrotor |
| usv | quadrotor, fixed_wing, usv |
| ugv | quadrotor, usv |

### Handoff validation

When planning a handoff, verify BOTH directions:
1. The sender's `can_send_to` includes the receiver's platform type.
2. The receiver's `can_receive_from` includes the sender's platform type.

Common handoff scenarios:
- **Air-to-sea**: quadrotor detects target over water -> hands off to USV for tracking.
- **Air-to-air**: fixed_wing detects target -> hands off to quadrotor for closer tracking.
- **Sea-to-land**: USV tracks target approaching shore -> hands off to UGV.
- **Air-to-land**: quadrotor detects ground target -> hands off to UGV.

Invalid handoff scenarios:
- UGV cannot hand off to anyone.
- USV cannot hand off to fixed_wing.
- UGV cannot hand off to fixed_wing.

---

## Environment rules

### Time of day

| Condition | Sensor guidance |
|-----------|----------------|
| **Night** | Prefer thermal sensors. Verify `night_capable: true` in platform-reference. All current platforms are night-capable. Annotate `sensor_mode: thermal` in the plan. |
| **Day** | RGB is default. Thermal optional for heat-signature targets. |
| **Dawn/dusk** | Consider both RGB and thermal. Transitional lighting may degrade RGB. |

### Visibility

| Condition | Impact |
|-----------|--------|
| **Normal** | Use detection ranges from platform-reference as-is. |
| **Degraded** | Reduce effective detection range to ~60-70% of platform-reference value. Note adjusted range in plan. |
| **Severely degraded** | Reduce to ~40-50%. Consider radar-equipped platforms (USV) for primary detection. |

### Weather

| Condition | Platform impact |
|-----------|----------------|
| **Clear** | No restrictions. |
| **Light rain** | quadrotor: `rain_tolerance: low` -- flag operational risk. Consider reduced flight time. fixed_wing: generally more tolerant. USV/UGV: no significant impact. |
| **Heavy rain** | quadrotor: high risk, consider grounding or reduced operations. All air: degraded sensor performance. |
| **Wind** | quadrotor: check `wind_limit_mps: 12`. fixed_wing: more wind-tolerant but affects turn radius. |

### Sea state

| Condition | Impact |
|-----------|--------|
| **Calm** | No restrictions on USV operations. |
| **Moderate** | Check USV `wave_height_limit_m: 2.0 m`. If exceeded, restrict USV operations or flag risk. USV `max_current_mps: 2.0` may affect tracking performance. |
| **Rough** | USV operations may be infeasible. Re-allocate sea tasks to air if possible. |

### Geofence and restricted zones

| Rule | Detail |
|------|--------|
| **Geofence** | `geofence_policy: must_stay_inside` -- all assets must remain within the geofence polygon at all times. Search patterns and transit paths must be bounded by the geofence. |
| **Restricted zones** | Assets must not enter restricted zones (e.g. `harbor_lane`, `marina_exclusion`). Search partitions should exclude restricted areas. Transit paths must route around them. |

---

## Role-to-action mapping

Standard mappings from fleet roles to primary mission actions:

| Role | Primary action | Notes |
|------|----------------|-------|
| scout | Search | Assigned to exploration/search phases |
| tracker | Track | Assigned to tracking phase after handoff |
| interceptor | Encircle | Assigned to encirclement phase |
| overwatch | Wide-area monitoring | Search variant using fixed_wing wide-area patterns; may also contribute to tracking from altitude |

These are defaults. The mission spec may override role assignments. Always verify
against the actual `fleet` section and `preferences` in the mission spec.

---

## Verb-to-action mapping

For parsing natural language mission objectives:

| Verbs in objective | Maps to action |
|-------------------|----------------|
| find, locate, search, detect, scan, survey, reconnoiter | **Search** |
| pursue, follow, shadow, monitor, observe, watch, surveil | **Track** |
| contain, encircle, surround, cordon, blockade, enclose | **Encircle** |
| overwatch, patrol, cover | **Search/Track** (wide-area variant) |
| abort, retreat, return, recover, withdraw | **Abort / Recover** |
