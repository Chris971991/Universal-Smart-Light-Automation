# Weather-Station Daytime Source — Plan

**Created:** 2026-07-06
**Status:** Planning — no code yet
**Hardware:** Ecowitt GW3000C on the roof — `sensor.gw3000c_solar_lux` (updates ~every 30 s),
plus `sensor.gw3000c_solar_radiation` (W/m²) and `sensor.gw3000c_uv_index` as secondary signals.
**Goal:** let the blueprint (and the kitchen controller, which is married to the same gate)
decide "daytime vs dark" from **real outdoor light** instead of sun clock-times — so a gloomy
storm afternoon gets lights early and a bright summer evening isn't lit an hour before it's dim.

---

## Why (what sun-times can't do)

The current gate is `sunrise+60 → sunset−60`, pure geometry. It is identical on a clear day and
in a black thunderstorm. Measured on 2026-07-05 (fairly clear):

| Boundary today | Clock | Actual outdoor lux |
|---|---|---|
| Evening unlock (sunset−60) | 16:00 | ~8,500 lx |
| Old kitchen dark point (elev<6°) | 16:25 | ~1,400 lx |
| Sunset | 17:00 | ~300 lx |
| Morning off (sunrise+60) | 07:56 | ~5,000–6,000 lx |

On an overcast day those clock boundaries land at completely different light levels — which is
exactly the complaint lux mode fixes.

---

## Design

### New blueprint inputs (v3.12.0 candidate, all backward-compatible)

1. **`daytime_source`** select: `sun_times` (default — zero change for existing configs) |
   `outdoor_lux`.
2. **`outdoor_lux_sensor`** — entity selector (illuminance), default empty.
3. **`outdoor_dark_below_lux`** — number, default **3,000** (≈16:12 evening / ≈07:35 morning on
   a clear winter day, between the rooms' old unlock and the old kitchen dark point).
4. **`outdoor_light_above_lux`** — number, default **4,500**. The gap between the two thresholds
   is the hysteresis band: once dark, it takes >4,500 to be day again; once day, <3,000 to be
   dark. Never allow equal values (validate / clamp in the blueprint).
5. **Existing sunrise/sunset offsets keep working** and become the **fallback window**.

### Semantics

- `is_daytime` (the block/forced-off gate) = outdoor lux above/below thresholds with hysteresis,
  instead of the clock window. Everything downstream (always_block, forced daytime off,
  vacancy behavior) is untouched — only the *source* of `is_daytime` changes.
- Room **indoor** illuminance sensors keep their current role (they gate the actual turn-on).
  Outdoor lux replaces only the window. Net effect per room: earliest-allowed time, forced-off
  time. For the kitchen (no indoor sensor) it becomes the whole darkness decision — the biggest
  winner.
- A storm at noon **counts as dark** — that is the feature, not a bug. The hysteresis band plus
  the sensor's 30 s cadence means a passing cloud (minutes) can dip below 3,000 only briefly;
  if flapping is observed in practice, add a **sustained-for window** (see Open questions).

### Fail-safe (non-negotiable)

If the lux sensor is `unavailable`/`unknown` **or stale** (no update for >10 min — it normally
reports every ~30 s), the blueprint silently reverts to the `sun_times` window. A dead/covered
roof sensor must never strand the house dark-mode at noon or light-blocked at night.

### Triggers

Add the outdoor sensor as a numeric_state trigger pair (crossing each threshold) so boundary
response is immediate; the existing periodic/sensor triggers re-evaluate anyway. The kitchen's
5 s tick needs nothing new.

### Kitchen controller (stays married)

Whatever the rooms use, the kitchen must use, or the 2026-07-05 marriage silently unmarries.
When the rooms flip to `outdoor_lux`, the kitchen's `is_dark` swaps to the same thresholds +
same sun-times fallback. One further simplification becomes possible: the kitchen currently has
no light input at all — outdoor lux effectively gives it one for free, ahead of the Phase 4
indoor presence/lux sensor (which remains the proper fix for occupancy).

---

## Open questions (decide before implementing)

1. **Hysteresis memory.** Blueprint runs are stateless; "which side of the band am I on" needs
   memory. Options:
   a. **HA Threshold helper** (native, has hysteresis built in): user/wizard creates
      `binary_sensor.outdoor_is_dark` from the lux sensor; blueprint just takes a binary
      sensor. Simplest and most robust; adds one helper (wizard could create it).
   b. Infer the current side from the lights' own state — free but couples the gate to light
      state (the exact feedback class the v2.11 kitchen red-team killed; avoid).
   c. Single threshold, no hysteresis — simplest, risks dawn/dusk flapping (~30 s cadence
      makes this real).
   **Recommendation: (a).**
2. **Sustained-for window** (cloud vs storm): start without it (hysteresis band may be enough);
   add `for:` minutes on the threshold triggers if practice shows flapping.
3. **Threshold defaults**: 3,000/4,500 are grounded in one clear winter day. Verify against an
   overcast day and a summer day before locking defaults; they're user-tunable regardless.
4. **Sequencing**: fold into blueprint **v3.12.0** alongside the migration-plan Phase 2 features
   (occupancy_source, schedule brightness, arrival boost) or ship as a standalone v3.12 first.
   Standalone-first is lower risk: one feature, default-off, soak on the office.

---

## Rollout

1. Blueprint v3.12.0 with `daytime_source: sun_times` default → import + **full HA restart**
   (blueprint cache) → zero behavior change, verify.
2. Create the threshold helper (or pick option c) → flip the **office** to `outdoor_lux`
   (it has an indoor lux sensor as a safety net) → soak a few days incl. one gloomy day.
3. Flip the master bedroom.
4. Swap the kitchen controller's `is_dark` to the same source (small, isolated change —
   the v2.8 template already has a sun fallback branch to reuse as the fail-safe).
5. Tune thresholds off real incidents; document final values here.

## Verification checklist

- [ ] Clear evening: lights unlock within a few minutes of the old sunset−60 time
- [ ] Overcast/storm afternoon: rooms allowed early, kitchen lights early — the headline win
- [ ] Bright morning: everything off near old sunrise+60; gloomy morning: allowed to run later
- [ ] No dawn/dusk flapping (watch two dawns/dusks in history)
- [ ] Unplug/cover test: lux sensor unavailable → behavior identical to sun_times within 10 min
- [ ] Kitchen and rooms flip on the same evening within minutes of each other (marriage intact)
