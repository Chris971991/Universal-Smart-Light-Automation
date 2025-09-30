"""Config flow for Universal Smart Lighting Setup Wizard."""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import voluptuous as vol
import yaml

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.components import input_boolean, input_datetime, input_text
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "universal_lighting_setup_wizard"

# Helper definitions for Universal Smart Lighting
HELPER_DEFINITIONS = {
    "automation_active": {
        "domain": "input_boolean",
        "name": "{room} Automation Active",
        "icon": "mdi:power",
        "initial": True,
    },
    "manual_override": {
        "domain": "input_boolean",
        "name": "{room} Manual Override",
        "icon": "mdi:hand-back-right",
        "initial": False,
    },
    "light_auto_on": {
        "domain": "input_boolean",
        "name": "{room} Light Auto On",
        "icon": "mdi:lightbulb-auto",
        "initial": True,
    },
    "occupancy_state": {
        "domain": "input_boolean",
        "name": "{room} Occupancy State",
        "icon": "mdi:account-check",
        "initial": False,
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
        "initial": "",
        "max_length": 255,
    },
}


def sanitize_room_name(room_name: str) -> str:
    """Convert room name to valid entity ID format."""
    # Convert to lowercase
    sanitized = room_name.lower()
    # Replace spaces and special chars with underscores
    sanitized = re.sub(r'[^a-z0-9]+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized


class UniversalLightingSetupWizardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Universal Lighting Setup Wizard."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.config_data = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step - Room Setup."""
        errors = {}

        if user_input is not None:
            # Sanitize room name
            room_name = user_input["room_name"]
            sanitized_name = sanitize_room_name(room_name)

            # Validate room name
            if not sanitized_name:
                errors["room_name"] = "invalid_room_name"
            elif len(sanitized_name) < 2:
                errors["room_name"] = "room_name_too_short"
            else:
                # Check if helpers already exist
                existing_helpers = await self._check_existing_helpers(sanitized_name)
                if existing_helpers:
                    errors["base"] = "helpers_exist"
                else:
                    # Store room setup data
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
                "room_example": "bedroom, living_room, home_office",
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
            # Validate thresholds
            dark = user_input.get("dark_threshold", 30)
            bright = user_input.get("bright_threshold", 200)

            if bright <= dark + 10:
                errors["bright_threshold"] = "bright_must_exceed_dark"
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
        if user_input is not None:
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
                vol.Required("enable_guest_mode", default=False): cv.boolean,
                vol.Required("enable_debug_logs", default=False): cv.boolean,
                vol.Required("enable_update_check", default=True): cv.boolean,
            }),
        )

    async def async_step_adaptive_lighting(self, user_input=None):
        """Handle adaptive lighting configuration."""
        if user_input is not None:
            self.config_data.update(user_input)
            # Final step - create everything
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

    async def _check_existing_helpers(self, sanitized_name: str) -> list[str]:
        """Check if helpers already exist for this room."""
        existing = []
        for helper_key, helper_def in HELPER_DEFINITIONS.items():
            domain = helper_def["domain"]
            object_id = f"{sanitized_name}_{helper_key}"
            entity_id = f"{domain}.{object_id}"

            if self.hass.states.get(entity_id) is not None:
                existing.append(entity_id)

        return existing

    async def _create_setup(self):
        """Create all helpers and automation."""
        try:
            # Step 1: Ensure packages configuration exists
            await self._add_packages_configuration()

            # Step 2: Create helper entities via package file
            await self._create_helpers()

            # Step 3: Create automation configuration
            await self._create_automation()

            # Step 4: Reload helper domains
            await self._reload_helpers()

            # Step 5: Create config entry
            return self.async_create_entry(
                title=f"Universal Lighting - {self.config_data['room_name']}",
                data=self.config_data,
            )

        except Exception as e:
            _LOGGER.error("Failed to create setup: %s", str(e))
            return self.async_abort(reason="setup_failed")

    async def _add_packages_configuration(self):
        """Add packages configuration to configuration.yaml if not present."""
        config_path = self.hass.config.path("configuration.yaml")

        # Read current configuration
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Check if packages are already configured
        if "homeassistant" in config:
            if "packages" in config["homeassistant"]:
                _LOGGER.info("Packages already configured in configuration.yaml")
                return
        else:
            config["homeassistant"] = {}

        # Add packages configuration
        config["homeassistant"]["packages"] = "!include_dir_named packages"

        # Write back to configuration.yaml
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        _LOGGER.info("Added packages configuration to configuration.yaml")

    async def _create_helpers(self):
        """Create all required helper entities via YAML package file."""
        sanitized_name = self.config_data["sanitized_room_name"]
        room_name = self.config_data["room_name"]

        # Build YAML configuration for all helpers
        helpers_config = {}

        for helper_key, helper_def in HELPER_DEFINITIONS.items():
            domain = helper_def["domain"]
            object_id = f"{sanitized_name}_{helper_key}"

            # Initialize domain dict if needed
            if domain not in helpers_config:
                helpers_config[domain] = {}

            # Build helper configuration
            helper_config = {"name": helper_def["name"].format(room=room_name)}

            if helper_def.get("icon"):
                helper_config["icon"] = helper_def["icon"]

            # Domain-specific configuration
            if domain == "input_boolean":
                helper_config["initial"] = helper_def.get("initial", False)
            elif domain == "input_datetime":
                helper_config["has_date"] = helper_def.get("has_date", True)
                helper_config["has_time"] = helper_def.get("has_time", True)
            elif domain == "input_text":
                helper_config["initial"] = helper_def.get("initial", "")
                helper_config["max"] = helper_def.get("max_length", 255)

            helpers_config[domain][object_id] = helper_config

        # Write YAML package file
        packages_dir = self.hass.config.path("packages")
        os.makedirs(packages_dir, exist_ok=True)

        package_file = os.path.join(packages_dir, f"lighting_{sanitized_name}.yaml")

        with open(package_file, "w", encoding="utf-8") as f:
            yaml.dump(helpers_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        _LOGGER.info("Created helper package file: %s", package_file)

    async def _create_automation(self):
        """Create automation configuration in automations.yaml."""
        sanitized_name = self.config_data["sanitized_room_name"]
        room_name = self.config_data["room_name"]

        # Build automation config using the blueprint
        automation_config = {
            "id": f"universal_lighting_{sanitized_name}",
            "alias": f"Universal Smart Lighting - {room_name}",
            "use_blueprint": {
                "path": "Chris971991/universal-smart-light-automation.yaml",
                "input": {
                    # Room Setup
                    "room_name": sanitized_name,
                    "control_mode": self.config_data.get("control_mode", "switch_only"),
                },
            },
        }

        # Add optional fields
        if self.config_data.get("light_switch"):
            automation_config["use_blueprint"]["input"]["light_switch"] = self.config_data["light_switch"]

        if self.config_data.get("light_entities"):
            automation_config["use_blueprint"]["input"]["light_entities"] = self.config_data["light_entities"]

        # Presence Detection
        automation_config["use_blueprint"]["input"]["presence_pir_sensor"] = self.config_data["presence_pir_sensor"]
        if self.config_data.get("presence_mmwave_sensor"):
            automation_config["use_blueprint"]["input"]["presence_mmwave_sensor"] = self.config_data["presence_mmwave_sensor"]
        if self.config_data.get("sensor_off_latency_entity"):
            automation_config["use_blueprint"]["input"]["sensor_off_latency_entity"] = self.config_data["sensor_off_latency_entity"]

        automation_config["use_blueprint"]["input"]["fixed_latency_seconds"] = self.config_data.get("fixed_latency_seconds", 60)
        automation_config["use_blueprint"]["input"]["vacancy_timeout_multiplier"] = self.config_data.get("vacancy_timeout_multiplier", 5)

        # Light Levels
        automation_config["use_blueprint"]["input"]["illuminance_sensor"] = self.config_data["illuminance_sensor"]
        automation_config["use_blueprint"]["input"]["dark_threshold"] = self.config_data.get("dark_threshold", 30)
        automation_config["use_blueprint"]["input"]["bright_threshold"] = self.config_data.get("bright_threshold", 200)
        automation_config["use_blueprint"]["input"]["extremely_dark_threshold"] = self.config_data.get("extremely_dark_threshold", 3)
        automation_config["use_blueprint"]["input"]["enable_illuminance_averaging"] = self.config_data.get("enable_illuminance_averaging", True)

        # Manual Override
        automation_config["use_blueprint"]["input"]["override_behavior"] = self.config_data.get("override_behavior", "timeout_only")
        automation_config["use_blueprint"]["input"]["override_timeout_hours"] = self.config_data.get("override_timeout_hours", 3)
        automation_config["use_blueprint"]["input"]["override_respect_presence"] = self.config_data.get("override_respect_presence", True)
        automation_config["use_blueprint"]["input"]["vacancy_clear_minutes"] = self.config_data.get("vacancy_clear_minutes", 45)

        # Daytime Control
        if self.config_data.get("enable_daytime_control"):
            automation_config["use_blueprint"]["input"]["daytime_control_mode"] = self.config_data.get("daytime_control_mode", "always_allow")
            if self.config_data.get("presence_trackers"):
                automation_config["use_blueprint"]["input"]["presence_trackers"] = self.config_data["presence_trackers"]

        # Bed Sensor
        if self.config_data.get("enable_bed_sensor") and self.config_data.get("bed_occupied_helper"):
            automation_config["use_blueprint"]["input"]["bed_occupied_helper"] = self.config_data["bed_occupied_helper"]
            automation_config["use_blueprint"]["input"]["turn_off_when_bed_occupied"] = self.config_data.get("turn_off_when_bed_occupied", True)

        # Adaptive Lighting
        automation_config["use_blueprint"]["input"]["enable_adaptive_brightness"] = self.config_data.get("enable_adaptive_brightness", True)
        automation_config["use_blueprint"]["input"]["enable_color_temperature"] = self.config_data.get("enable_color_temperature", True)
        automation_config["use_blueprint"]["input"]["day_color_temp"] = self.config_data.get("day_color_temp", 5000)
        automation_config["use_blueprint"]["input"]["night_color_temp"] = self.config_data.get("night_color_temp", 3000)
        automation_config["use_blueprint"]["input"]["enable_fade_on"] = self.config_data.get("enable_fade_on", True)
        automation_config["use_blueprint"]["input"]["fade_on_time"] = self.config_data.get("fade_on_time", 1.5)
        automation_config["use_blueprint"]["input"]["enable_fade_off"] = self.config_data.get("enable_fade_off", True)
        automation_config["use_blueprint"]["input"]["fade_off_time"] = self.config_data.get("fade_off_time", 2.0)

        # Guest Mode
        if self.config_data.get("enable_guest_mode"):
            automation_config["use_blueprint"]["input"]["enable_guest_mode"] = True
            automation_config["use_blueprint"]["input"]["guest_vacancy_multiplier"] = self.config_data.get("guest_vacancy_multiplier", 2.5)
            automation_config["use_blueprint"]["input"]["guest_override_multiplier"] = self.config_data.get("guest_override_multiplier", 2.0)
            automation_config["use_blueprint"]["input"]["guest_ignore_bed"] = self.config_data.get("guest_ignore_bed", True)

        # Debug and Update Check
        automation_config["use_blueprint"]["input"]["enable_debug_logs"] = self.config_data.get("enable_debug_logs", False)
        automation_config["use_blueprint"]["input"]["enable_update_check"] = self.config_data.get("enable_update_check", True)

        # Read existing automations
        automations_path = self.hass.config.path("automations.yaml")
        if os.path.exists(automations_path):
            with open(automations_path, "r", encoding="utf-8") as f:
                automations = yaml.safe_load(f) or []
        else:
            automations = []

        # Add new automation
        automations.append(automation_config)

        # Write back
        with open(automations_path, "w", encoding="utf-8") as f:
            yaml.dump(automations, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        _LOGGER.info("Created automation: %s", automation_config["id"])
        self.config_data["automation_id"] = automation_config["id"]

    async def _reload_helpers(self):
        """Reload all helper domains to activate new entities."""
        for domain in ["input_boolean", "input_datetime", "input_text"]:
            try:
                await self.hass.services.async_call(domain, "reload", blocking=False)
                _LOGGER.info("Reloaded domain: %s", domain)
            except Exception as e:
                _LOGGER.warning("Failed to reload domain %s: %s", domain, str(e))

        # Also reload automations
        try:
            await self.hass.services.async_call("automation", "reload", blocking=False)
            _LOGGER.info("Reloaded automations")
        except Exception as e:
            _LOGGER.warning("Failed to reload automations: %s", str(e))
