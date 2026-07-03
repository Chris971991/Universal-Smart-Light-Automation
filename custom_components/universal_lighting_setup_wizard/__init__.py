"""Universal Smart Lighting Setup Wizard for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "universal_lighting_setup_wizard"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Universal Lighting Setup Wizard from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Show the setup-complete notification ONCE (async_setup_entry runs on
    # every HA restart for every entry - without this flag the "Setup
    # Complete" notification re-appeared for every room at every boot).
    if not entry.data.get("setup_notified"):
        room_name = entry.data.get("room_name", "Unknown")
        sanitized_name = entry.data.get("sanitized_room_name", room_name)
        automation_id = entry.data.get("automation_id", "N/A")

        notification_message = f"""
## ✅ Universal Smart Lighting Setup Complete!

**Room:** {room_name}

**What was created:**
- ✅ 6 Helper entities (automation_active, manual_override, light_auto_on, occupancy_state, last_automation_action, illuminance_history)
- ✅ Automation **Universal Smart Lighting - {room_name}** in `/config/automations.yaml`
- ✅ Helper package file `/config/packages/lighting_{sanitized_name}.yaml`

**Next Steps:**
1. Go to **Settings → Automations & Scenes**
2. Open **Universal Smart Lighting - {room_name}** to fine-tune any settings
3. Test by walking into the room!

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
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "setup_notified": True}
        )
        _LOGGER.info("Universal Lighting setup completed for room: %s", room_name)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    _LOGGER.info(
        "Removing Universal Lighting Setup Wizard entry for room: %s "
        "(the helpers, package file and automation are NOT deleted - remove "
        "them manually if no longer wanted)",
        entry.data.get("room_name"),
    )
