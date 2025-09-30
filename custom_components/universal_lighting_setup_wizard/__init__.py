"""Universal Smart Lighting Setup Wizard for Home Assistant."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "universal_lighting_setup_wizard"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Universal Lighting Setup Wizard from a config entry."""
    _LOGGER.info("Setting up Universal Lighting Setup Wizard for room: %s", entry.data.get("room_name"))

    # Store the config entry data for reference
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Create a persistent notification with the setup summary
    room_name = entry.data.get("room_name")
    automation_id = entry.data.get("automation_id", "N/A")

    notification_message = f"""
## ✅ Universal Smart Lighting Setup Complete!

**Room:** {room_name}

**What was created:**
- ✅ 6 Helper entities (automation_active, manual_override, light_auto_on, occupancy_state, last_automation_action, illuminance_history)
- ✅ Automation configuration in `/config/automations.yaml`
- ✅ Helper package file in `/config/packages/lighting_{room_name}.yaml`

**Next Steps:**
1. Go to **Settings → Automations & Scenes**
2. Find your automation: **Universal Smart Lighting - {room_name}**
3. Enable the automation if it's not already enabled
4. Test by walking into the room!

**To customize settings:**
- Edit the automation in the UI
- Adjust thresholds, timings, and features as needed

**Package file location:** `/config/packages/lighting_{room_name}.yaml`
**Automation ID:** `{automation_id}`

---
🤖 Generated with Universal Smart Lighting Setup Wizard
"""

    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": f"🎉 {room_name} Lighting Setup Complete",
            "message": notification_message,
            "notification_id": f"lighting_wizard_{entry.entry_id}",
        },
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Universal Lighting Setup Wizard for room: %s", entry.data.get("room_name"))

    # Remove the stored data
    hass.data[DOMAIN].pop(entry.entry_id, None)

    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    _LOGGER.info("Removing Universal Lighting Setup Wizard entry for room: %s", entry.data.get("room_name"))
    # Note: We don't delete the helper entities or automation - user can manually remove if needed
