"""Config flow for Universal Smart Lighting Setup Wizard.

v2.0.0 (2026-07) - full rewrite after audit:
- configuration.yaml is NEVER round-tripped through PyYAML (custom tags like
  !include crashed safe_load on virtually every real install, and yaml.dump
  would have destroyed comments and emitted the packages directive as a quoted
  string). Packages detection/insertion is now text-based and surgical.
- automations.yaml is APPEND-ONLY: existing content (comments, formatting) is
  preserved byte-for-byte; only the new automation block is added.
- All file writes are atomic (temp + os.replace) with a .wizard-backup copy,
  and all file I/O runs in the executor (no event-loop blocking).
- The blueprint's existence is verified before anything is written, and the
  correct capitalized blueprint path is used (HAOS filesystems are
  case-sensitive; the old lowercase path produced automations that never
  loaded).
- Helpers no longer carry `initial:` values (they forcibly reset state on
  every HA restart - wiping manual overrides and corrupting the blueprint's
  restore-dependent logic).
- Cross-field validation: control mode vs entities, bed sensor, trackers,
  thresholds. Duplicate rooms are rejected via unique_id + automation-id scan.
- Failed runs are safely retryable: existing orphaned helpers are reused, the
  automation append is the last write, and every step aborts with a specific
  reason.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
from typing import Any

import voluptuous as vol
import yaml

from homeassistant import config_entries
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "universal_lighting_setup_wizard"

BLUEPRINT_PATH = "Chris971991/Universal-Smart-Light-Automation.yaml"

# Helper definitions for Universal Smart Lighting.
# NOTE: deliberately no `initial:` values - input_boolean/input_text `initial`
# resets the state on EVERY Home Assistant restart, which would wipe active
# manual overrides and reset the blueprint's bookkeeping at each boot.
HELPER_DEFINITIONS = {
    "automation_active": {
        "domain": "input_boolean",
        "name": "{room} Automation Active",
        "icon": "mdi:power",
    },
    "manual_override": {
        "domain": "input_boolean",
        "name": "{room} Manual Override",
        "icon": "mdi:hand-back-right",
    },
    "light_auto_on": {
        "domain": "input_boolean",
        "name": "{room} Light Auto On",
        "icon": "mdi:lightbulb-auto",
    },
    "occupancy_state": {
        "domain": "input_boolean",
        "name": "{room} Occupancy State",
        "icon": "mdi:account-check",
    },
    "last_automation_action": {
        "domain": "input_datetime",
        "name": "{room} Last Automation Action",
        "icon": "mdi:clock-outline",
        "has_date": True,
        "has_time": True,
    },
    "illuminance_history": {
        "domain": "input_text",
        "name": "{room} Illuminance History",
        "icon": "mdi:brightness-6",
        "max_length": 255,
    },
    # v2.1.0: hysteresis latch for blueprint v3.13.0's outdoor lux thresholds.
    # Maintained by the blueprint itself; harmless (unused) when no outdoor
    # lux sensor is configured on the automation.
    "outdoor_dark": {
        "domain": "input_boolean",
        "name": "{room} Outdoor Dark",
        "icon": "mdi:weather-sunset-down",
    },
}


def sanitize_room_name(room_name: str) -> str:
    """Convert room name to valid entity ID format (matches the blueprint)."""
    sanitized = room_name.lower()
    sanitized = re.sub(r"[^a-z0-9]+", "_", sanitized)
    sanitized = sanitized.strip("_")
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized


# ---------------------------------------------------------------------------
# Synchronous file helpers (always called via hass.async_add_executor_job)
# ---------------------------------------------------------------------------

def _read_text(path: str) -> str | None:
    """Read a text file, returning None if it does not exist."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _atomic_write(path: str, content: str, backup: bool = True) -> None:
    """Write a file atomically (temp + rename), keeping a .wizard-backup copy."""
    if backup and os.path.exists(path):
        shutil.copy2(path, path + ".wizard-backup")
    tmp_path = path + ".wizard-tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _file_exists(path: str) -> bool:
    return os.path.exists(path)


def _packages_status(config_path: str) -> str:
    """Inspect configuration.yaml TEXT for packages config.

    Returns one of:
      'configured'   - a packages: key already exists
      'no_ha_block'  - no top-level homeassistant: key (safe to append one)
      'insertable'   - plain 'homeassistant:' block key (safe to insert into)
      'manual'       - homeassistant: has inline content (do not touch)
    """
    text = _read_text(config_path)
    if text is None:
        return "no_ha_block"
    if re.search(r"(?m)^\s+packages\s*:", text):
        return "configured"
    match = re.search(r"(?m)^homeassistant\s*:(.*)$", text)
    if match is None:
        return "no_ha_block"
    trailing = match.group(1).strip()
    if trailing == "" or trailing.startswith("#"):
        return "insertable"
    return "manual"


def _add_packages_to_config(config_path: str) -> None:
    """Surgically enable packages in configuration.yaml (text-based, atomic).

    Never parses or re-serializes the file - existing content, comments and
    custom YAML tags are preserved byte-for-byte.
    """
    status = _packages_status(config_path)
    if status == "configured":
        _LOGGER.info("Packages already configured in configuration.yaml")
        return
    if status == "manual":
        raise RuntimeError("packages_manual")

    text = _read_text(config_path) or ""
    if status == "no_ha_block":
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\nhomeassistant:\n  packages: !include_dir_named packages\n"
    else:  # insertable
        text = re.sub(
            r"(?m)^(homeassistant\s*:.*)$",
            r"\1\n  packages: !include_dir_named packages",
            text,
            count=1,
        )
    _atomic_write(config_path, text)
    _LOGGER.info("Enabled packages in configuration.yaml (text-preserving edit)")


def _write_package_file(packages_dir: str, package_path: str, helpers_config: dict) -> None:
    """Write the (wizard-owned) helper package file."""
    os.makedirs(packages_dir, exist_ok=True)
    content = yaml.safe_dump(
        helpers_config, default_flow_style=False, allow_unicode=True, sort_keys=False
    )
    _atomic_write(package_path, content, backup=False)


def _automation_id_exists(automations_path: str, automation_id: str) -> bool:
    """Check automations.yaml text for an existing automation id."""
    text = _read_text(automations_path)
    if text is None:
        return False
    pattern = rf"(?m)^[-\s]*id\s*:\s*['\"]?{re.escape(automation_id)}['\"]?\s*$"
    return re.search(pattern, text) is not None


def _append_automation(automations_path: str, automation_config: dict) -> None:
    """Append ONE automation to automations.yaml, preserving existing content."""
    block = yaml.safe_dump(
        [automation_config], default_flow_style=False, allow_unicode=True, sort_keys=False
    )
    existing = _read_text(automations_path)
    if existing is None or existing.strip() in ("", "[]"):
        content = block
    else:
        if not existing.endswith("\n"):
            existing += "\n"
        content = existing + block
    _atomic_write(automations_path, content)


class UniversalLightingSetupWizardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Universal Lighting Setup Wizard."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.config_data: dict[str, Any] = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step - Room Setup."""
        errors = {}

        if user_input is not None:
            room_name = user_input["room_name"]
            sanitized_name = sanitize_room_name(room_name)
            control_mode = user_input.get("control_mode", "switch_only")
            light_switch = user_input.get("light_switch")
            light_entities = user_input.get("light_entities")

            if not sanitized_name:
                errors["room_name"] = "invalid_room_name"
            elif len(sanitized_name) < 2:
                errors["room_name"] = "room_name_too_short"
            elif control_mode == "switch_only" and not light_switch:
                errors["light_switch"] = "switch_required"
            elif control_mode == "lights_only" and not light_entities:
                errors["light_entities"] = "lights_required"
            elif control_mode == "switch_and_lights" and not light_switch and not light_entities:
                errors["base"] = "entities_required"
            else:
                # One config entry per room
                await self.async_set_unique_id(f"universal_lighting_{sanitized_name}")
                self._abort_if_unique_id_configured()

                # Reject rooms whose automation already exists (helpers alone
                # are fine - orphans from a failed run are reused on retry)
                automations_path = self.hass.config.path("automations.yaml")
                automation_exists = await self.hass.async_add_executor_job(
                    _automation_id_exists,
                    automations_path,
                    f"universal_lighting_{sanitized_name}",
                )
                if automation_exists:
                    errors["room_name"] = "automation_exists"
                else:
                    self.config_data.update(user_input)
                    self.config_data["sanitized_room_name"] = sanitized_name
                    return await self.async_step_presence_detection()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("room_name"): cv.string,
                vol.Required("control_mode", default="switch_only"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Smart Switch + Smart Lights", "value": "switch_and_lights"},
                            {"label": "Smart Lights Only", "value": "lights_only"},
                            {"label": "Smart Switch Only", "value": "switch_only"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Optional("light_switch"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch", "light"]),
                ),
                vol.Optional("light_entities"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light", multiple=True),
                ),
            }),
            errors=errors,
            description_placeholders={
                "room_example": "Bedroom, Living Room, Home Office",
            },
        )

    async def async_step_presence_detection(self, user_input=None):
        """Handle presence detection configuration."""
        errors = {}

        if user_input is not None:
            self.config_data.update(user_input)
            return await self.async_step_light_levels()

        return self.async_show_form(
            step_id="presence_detection",
            data_schema=vol.Schema({
                vol.Required("presence_pir_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                        device_class=["motion", "occupancy", "presence"],
                    ),
                ),
                vol.Optional("presence_mmwave_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                        device_class=["motion", "occupancy", "presence"],
                    ),
                ),
                vol.Optional("sensor_off_latency_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number"),
                ),
                vol.Required("fixed_latency_seconds", default=60): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=300)
                ),
                vol.Required("vacancy_timeout_multiplier", default=5): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=30)
                ),
            }),
            errors=errors,
        )

    async def async_step_light_levels(self, user_input=None):
        """Handle light level configuration."""
        errors = {}

        if user_input is not None:
            dark = user_input.get("dark_threshold", 30)
            bright = user_input.get("bright_threshold", 200)
            extremely_dark = user_input.get("extremely_dark_threshold", 3)

            if bright - dark < 10:
                errors["bright_threshold"] = "bright_must_exceed_dark"
            elif extremely_dark >= dark:
                errors["extremely_dark_threshold"] = "extreme_must_be_below_dark"
            else:
                self.config_data.update(user_input)
                return await self.async_step_manual_override()

        return self.async_show_form(
            step_id="light_levels",
            data_schema=vol.Schema({
                vol.Required("illuminance_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "input_number"]),
                ),
                vol.Required("dark_threshold", default=30): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=499)
                ),
                vol.Required("bright_threshold", default=200): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=500)
                ),
                vol.Required("extremely_dark_threshold", default=3): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=20)
                ),
                vol.Required("enable_illuminance_averaging", default=True): cv.boolean,
            }),
            errors=errors,
        )

    async def async_step_manual_override(self, user_input=None):
        """Handle manual override configuration."""
        if user_input is not None:
            self.config_data.update(user_input)
            return await self.async_step_optional_features()

        return self.async_show_form(
            step_id="manual_override",
            data_schema=vol.Schema({
                vol.Required("override_behavior", default="timeout_only"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Timeout Only - Full manual control", "value": "timeout_only"},
                            {"label": "Vacancy Can Clear - Smarter but less control", "value": "vacancy_clear"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Required("override_timeout_hours", default=3): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=24)
                ),
                vol.Required("override_respect_presence", default=True): cv.boolean,
                vol.Required("vacancy_clear_minutes", default=45): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=120)
                ),
            }),
        )

    async def async_step_optional_features(self, user_input=None):
        """Handle optional features selection."""
        errors = {}

        if user_input is not None:
            if user_input.get("enable_bed_sensor") and not user_input.get("bed_occupied_helper"):
                errors["bed_occupied_helper"] = "bed_helper_required"
            elif (
                user_input.get("enable_daytime_control")
                and user_input.get("daytime_control_mode") == "block_when_away"
                and not user_input.get("presence_trackers")
            ):
                errors["presence_trackers"] = "trackers_required"
            else:
                self.config_data.update(user_input)
                return await self.async_step_adaptive_lighting()

        return self.async_show_form(
            step_id="optional_features",
            data_schema=vol.Schema({
                vol.Required("enable_daytime_control", default=False): cv.boolean,
                vol.Optional("daytime_control_mode", default="always_allow"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Always Allow - Normal operation", "value": "always_allow"},
                            {"label": "Block When Away - Save energy when gone", "value": "block_when_away"},
                            {"label": "Always Block - No daytime auto-on", "value": "always_block"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Optional("presence_trackers"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="device_tracker", multiple=True),
                ),
                vol.Required("enable_bed_sensor", default=False): cv.boolean,
                vol.Optional("bed_occupied_helper"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["binary_sensor", "input_boolean"]),
                ),
                vol.Required("turn_off_when_bed_occupied", default=True): cv.boolean,
                vol.Required("bed_exit_delay_seconds", default=15): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=120)
                ),
                vol.Required("bed_entry_delay_seconds", default=15): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=120)
                ),
                vol.Required("enable_guest_mode", default=False): cv.boolean,
                vol.Required("enable_debug_logs", default=False): cv.boolean,
                vol.Required("enable_update_check", default=True): cv.boolean,
            }),
            errors=errors,
        )

    async def async_step_adaptive_lighting(self, user_input=None):
        """Handle adaptive lighting configuration."""
        if user_input is not None:
            self.config_data.update(user_input)
            return await self._create_setup()

        return self.async_show_form(
            step_id="adaptive_lighting",
            data_schema=vol.Schema({
                vol.Required("enable_adaptive_brightness", default=True): cv.boolean,
                vol.Required("enable_color_temperature", default=True): cv.boolean,
                vol.Required("day_color_temp", default=5000): vol.All(
                    vol.Coerce(int), vol.Range(min=2700, max=6500)
                ),
                vol.Required("night_color_temp", default=3000): vol.All(
                    vol.Coerce(int), vol.Range(min=2700, max=6500)
                ),
                vol.Required("enable_fade_on", default=True): cv.boolean,
                vol.Required("fade_on_time", default=1.5): vol.All(
                    vol.Coerce(float), vol.Range(min=0.5, max=10)
                ),
                vol.Required("enable_fade_off", default=True): cv.boolean,
                vol.Required("fade_off_time", default=2.0): vol.All(
                    vol.Coerce(float), vol.Range(min=0.5, max=10)
                ),
                vol.Required("guest_vacancy_multiplier", default=2.5): vol.All(
                    vol.Coerce(float), vol.Range(min=1.5, max=5.0)
                ),
                vol.Required("guest_override_multiplier", default=2.0): vol.All(
                    vol.Coerce(float), vol.Range(min=1.5, max=5.0)
                ),
                vol.Required("guest_ignore_bed", default=True): cv.boolean,
            }),
        )

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    async def _create_setup(self):
        """Create all helpers and the automation.

        Ordered safest-first so a failure never leaves a broken system:
        blueprint check (read-only) -> packages config (usually a no-op) ->
        package file (new, wizard-owned) -> helper reload + verification ->
        automation append (atomic, last) -> automation reload.
        """
        # Step 0: The blueprint must exist BEFORE anything is written -
        # otherwise the created automation would be permanently 'unavailable'.
        blueprint_file = self.hass.config.path(
            "blueprints", "automation", *BLUEPRINT_PATH.split("/")
        )
        if not await self.hass.async_add_executor_job(_file_exists, blueprint_file):
            _LOGGER.error(
                "Blueprint not found at %s - import it before running the wizard",
                blueprint_file,
            )
            return self.async_abort(reason="blueprint_missing")

        # Step 1: Ensure packages are enabled (text-preserving, atomic)
        try:
            await self.hass.async_add_executor_job(
                _add_packages_to_config, self.hass.config.path("configuration.yaml")
            )
        except RuntimeError:
            return self.async_abort(reason="packages_manual")
        except Exception:
            _LOGGER.exception("Failed to enable packages in configuration.yaml")
            return self.async_abort(reason="packages_failed")

        # Step 2: Write the helper package file (wizard-owned, safe to overwrite)
        try:
            await self._create_helpers()
        except Exception:
            _LOGGER.exception("Failed to write the helper package file")
            return self.async_abort(reason="helpers_failed")

        # Step 3: Reload helper domains and verify the helpers came up
        if not await self._reload_and_verify_helpers():
            return self.async_abort(reason="helpers_failed")

        # Step 4: Append the automation (atomic, preserves existing content)
        try:
            await self._create_automation()
        except Exception:
            _LOGGER.exception("Failed to append the automation to automations.yaml")
            return self.async_abort(reason="automation_failed")

        # Step 5: Reload automations so the new one goes live
        try:
            await self.hass.services.async_call("automation", "reload", blocking=True)
        except Exception:
            _LOGGER.exception("Automation reload failed (automation was written)")

        return self.async_create_entry(
            title=f"Universal Lighting - {self.config_data['room_name']}",
            data=self.config_data,
        )

    async def _create_helpers(self):
        """Create all required helper entities via a YAML package file."""
        sanitized_name = self.config_data["sanitized_room_name"]
        room_name = self.config_data["room_name"]

        helpers_config: dict[str, dict] = {}
        for helper_key, helper_def in HELPER_DEFINITIONS.items():
            domain = helper_def["domain"]
            object_id = f"{sanitized_name}_{helper_key}"
            helpers_config.setdefault(domain, {})

            helper_config: dict[str, Any] = {"name": helper_def["name"].format(room=room_name)}
            if helper_def.get("icon"):
                helper_config["icon"] = helper_def["icon"]
            if domain == "input_datetime":
                helper_config["has_date"] = helper_def.get("has_date", True)
                helper_config["has_time"] = helper_def.get("has_time", True)
            elif domain == "input_text":
                helper_config["max"] = helper_def.get("max_length", 255)

            helpers_config[domain][object_id] = helper_config

        packages_dir = self.hass.config.path("packages")
        package_file = os.path.join(packages_dir, f"lighting_{sanitized_name}.yaml")
        await self.hass.async_add_executor_job(
            _write_package_file, packages_dir, package_file, helpers_config
        )
        _LOGGER.info("Created helper package file: %s", package_file)

    async def _reload_and_verify_helpers(self) -> bool:
        """Reload helper domains (blocking) and verify all helpers exist."""
        for domain in ("input_boolean", "input_datetime", "input_text"):
            try:
                await self.hass.services.async_call(domain, "reload", blocking=True)
            except Exception:
                _LOGGER.exception("Failed to reload domain %s", domain)
                return False

        sanitized_name = self.config_data["sanitized_room_name"]
        missing = [
            f"{helper_def['domain']}.{sanitized_name}_{helper_key}"
            for helper_key, helper_def in HELPER_DEFINITIONS.items()
            if self.hass.states.get(
                f"{helper_def['domain']}.{sanitized_name}_{helper_key}"
            ) is None
        ]
        if missing:
            _LOGGER.error("Helpers missing after reload: %s", ", ".join(missing))
            return False
        return True

    async def _create_automation(self):
        """Append the blueprint automation to automations.yaml."""
        sanitized_name = self.config_data["sanitized_room_name"]
        room_name = self.config_data["room_name"]
        data = self.config_data

        inputs: dict[str, Any] = {
            # The blueprint sanitizes internally; passing the original name
            # keeps notifications and logs human-readable.
            "room_name": room_name,
            "control_mode": data.get("control_mode", "switch_only"),
        }
        if data.get("light_switch"):
            inputs["light_switch"] = data["light_switch"]
        if data.get("light_entities"):
            inputs["light_entities"] = data["light_entities"]

        inputs["presence_pir_sensor"] = data["presence_pir_sensor"]
        if data.get("presence_mmwave_sensor"):
            inputs["presence_mmwave_sensor"] = data["presence_mmwave_sensor"]
        if data.get("sensor_off_latency_entity"):
            inputs["sensor_off_latency_entity"] = data["sensor_off_latency_entity"]
        inputs["fixed_latency_seconds"] = data.get("fixed_latency_seconds", 60)
        inputs["vacancy_timeout_multiplier"] = data.get("vacancy_timeout_multiplier", 5)

        inputs["illuminance_sensor"] = data["illuminance_sensor"]
        inputs["dark_threshold"] = data.get("dark_threshold", 30)
        inputs["bright_threshold"] = data.get("bright_threshold", 200)
        inputs["extremely_dark_threshold"] = data.get("extremely_dark_threshold", 3)
        inputs["enable_illuminance_averaging"] = data.get("enable_illuminance_averaging", True)

        inputs["override_behavior"] = data.get("override_behavior", "timeout_only")
        inputs["override_timeout_hours"] = data.get("override_timeout_hours", 3)
        inputs["override_respect_presence"] = data.get("override_respect_presence", True)
        inputs["vacancy_clear_minutes"] = data.get("vacancy_clear_minutes", 45)

        if data.get("enable_daytime_control"):
            inputs["daytime_control_mode"] = data.get("daytime_control_mode", "always_allow")
            if data.get("presence_trackers"):
                inputs["presence_trackers"] = data["presence_trackers"]

        if data.get("enable_bed_sensor") and data.get("bed_occupied_helper"):
            inputs["bed_occupied_helper"] = data["bed_occupied_helper"]
            inputs["turn_off_when_bed_occupied"] = data.get("turn_off_when_bed_occupied", True)
            inputs["bed_exit_delay_seconds"] = data.get("bed_exit_delay_seconds", 15)
            inputs["bed_entry_delay_seconds"] = data.get("bed_entry_delay_seconds", 15)

        inputs["enable_adaptive_brightness"] = data.get("enable_adaptive_brightness", True)
        inputs["enable_color_temperature"] = data.get("enable_color_temperature", True)
        inputs["day_color_temp"] = data.get("day_color_temp", 5000)
        inputs["night_color_temp"] = data.get("night_color_temp", 3000)
        inputs["enable_fade_on"] = data.get("enable_fade_on", True)
        inputs["fade_on_time"] = data.get("fade_on_time", 1.5)
        inputs["enable_fade_off"] = data.get("enable_fade_off", True)
        inputs["fade_off_time"] = data.get("fade_off_time", 2.0)

        if data.get("enable_guest_mode"):
            inputs["enable_guest_mode"] = True
            inputs["guest_vacancy_multiplier"] = data.get("guest_vacancy_multiplier", 2.5)
            inputs["guest_override_multiplier"] = data.get("guest_override_multiplier", 2.0)
            inputs["guest_ignore_bed"] = data.get("guest_ignore_bed", True)

        inputs["enable_debug_logs"] = data.get("enable_debug_logs", False)
        inputs["enable_update_check"] = data.get("enable_update_check", True)

        automation_config = {
            "id": f"universal_lighting_{sanitized_name}",
            "alias": f"Universal Smart Lighting - {room_name}",
            "description": "Created by the Universal Smart Lighting Setup Wizard",
            "use_blueprint": {
                "path": BLUEPRINT_PATH,
                "input": inputs,
            },
        }

        automations_path = self.hass.config.path("automations.yaml")

        # Belt-and-suspenders: never append a duplicate id
        if await self.hass.async_add_executor_job(
            _automation_id_exists, automations_path, automation_config["id"]
        ):
            raise RuntimeError(f"Automation id {automation_config['id']} already exists")

        await self.hass.async_add_executor_job(
            _append_automation, automations_path, automation_config
        )
        _LOGGER.info("Appended automation: %s", automation_config["id"])
        self.config_data["automation_id"] = automation_config["id"]
