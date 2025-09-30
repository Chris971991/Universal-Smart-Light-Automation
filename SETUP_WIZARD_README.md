# 🧙 Universal Smart Lighting Setup Wizard

**Effortlessly configure your Universal Smart Lighting automation with a guided setup wizard!**

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/Chris971991/universal-smart-light-automation)

Say goodbye to manual helper creation and configuration complexity. This setup wizard automates everything!

---

## ✨ What This Wizard Does

### 🎯 Automated Setup
- ✅ Creates all 6 required helper entities automatically
- ✅ Generates complete automation configuration
- ✅ Uses package-based helper system (non-destructive & isolated)
- ✅ Validates configuration before creating anything
- ✅ Provides step-by-step guidance with helpful descriptions

### 🚀 One-Click Configuration
Instead of:
1. Manually creating 6 helper entities
2. Remembering naming conventions
3. Configuring the blueprint manually
4. Debugging typos and errors

**You get**:
1. Click "Add Integration"
2. Follow the wizard (5 easy steps)
3. Done! ✨

---

## 📦 Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Click **Integrations**
3. Click the **3 dots** (⋮) → **Custom repositories**
4. Add:
   - **Repository**: `https://github.com/Chris971991/universal-smart-light-automation`
   - **Category**: `Integration`
5. Click **Install**
6. **Restart Home Assistant**

### Manual Installation

1. Download the `custom_components/universal_lighting_setup_wizard` folder
2. Copy to `/config/custom_components/` in your Home Assistant
3. Restart Home Assistant

---

## 🎬 Quick Start

### Prerequisites

1. **Install the Blueprint First**:
   ```
   https://github.com/Chris971991/universal-smart-light-automation
   ```

2. **Have Your Sensors Ready**:
   - Motion/occupancy sensor
   - Light/illuminance sensor (or create `input_number` as placeholder)

### Run the Wizard

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"** (bottom right)
3. Search for **"Universal Smart Lighting Setup Wizard"**
4. Follow the 5-step guided wizard:

#### 📍 Step 1: Room Setup
```
Room Name: bedroom
Control Mode: Smart Switch + Smart Lights
Light Switch: switch.bedroom_light
Light Entities: light.bedroom_ceiling, light.bedroom_lamp
```

#### 🚶 Step 2: Presence Detection
```
Motion Sensor: binary_sensor.bedroom_motion
Occupancy Sensor: binary_sensor.bedroom_mmwave (optional)
Fixed Latency: 60 seconds
Vacancy Multiplier: 5
```

#### 💡 Step 3: Light Levels
```
Illuminance Sensor: sensor.bedroom_illuminance
Dark Threshold: 30 lux (lights turn ON below this)
Bright Threshold: 200 lux (enough natural light above this)
Extremely Dark: 3 lux (pitch black, night mode)
Enable Averaging: Yes
```

#### ✋ Step 4: Manual Override
```
Override Method: Timeout Only
Timeout Duration: 3 hours
Respect Presence: Yes (pause timeout while present)
Vacancy Clear Time: 45 minutes
```

#### ⚙️ Step 5: Optional Features
```
Enable Daytime Control: Yes
Daytime Mode: Block When Away
Device Trackers: person.chris, person.partner

Enable Bed Sensor: Yes (for bedrooms)
Bed Sensor: binary_sensor.bed_occupied
Auto-off when bed occupied: Yes

Enable Guest Mode: Yes
Enable Debug Logs: No (enable for troubleshooting)
Enable Update Check: Yes
```

#### 🎨 Step 6: Adaptive Lighting
```
Adaptive Brightness: Yes
Color Temperature: Yes
Day Color: 5000K (cool, energizing)
Night Color: 3000K (warm, relaxing)

Fade On: Yes (1.5 seconds)
Fade Off: Yes (2.0 seconds)

Guest Vacancy Multiplier: 2.5x
Guest Override Multiplier: 2.0x
Ignore Bed in Guest Mode: Yes
```

### What Gets Created

After completing the wizard:

#### 1. Helper Package File
**Location**: `/config/packages/lighting_bedroom.yaml`
```yaml
input_boolean:
  bedroom_automation_active:
    name: Bedroom Automation Active
    icon: mdi:power
    initial: true
  bedroom_manual_override:
    name: Bedroom Manual Override
    icon: mdi:hand-back-right
    initial: false
  bedroom_light_auto_on:
    name: Bedroom Light Auto On
    icon: mdi:lightbulb-auto
    initial: true
  bedroom_occupancy_state:
    name: Bedroom Occupancy State
    icon: mdi:account-check
    initial: false

input_datetime:
  bedroom_last_automation_action:
    name: Bedroom Last Automation Action
    icon: mdi:clock-outline
    has_date: true
    has_time: true

input_text:
  bedroom_illuminance_history:
    name: Bedroom Illuminance History
    icon: mdi:brightness-6
    initial: ''
    max: 255
```

#### 2. Automation Configuration
**Added to**: `/config/automations.yaml`
```yaml
- id: universal_lighting_bedroom
  alias: Universal Smart Lighting - bedroom
  use_blueprint:
    path: Chris971991/universal-smart-light-automation.yaml
    input:
      room_name: bedroom
      control_mode: switch_and_lights
      light_switch: switch.bedroom_light
      light_entities:
        - light.bedroom_ceiling
        - light.bedroom_lamp
      # ... all your wizard settings ...
```

#### 3. Completion Notification
You'll see a persistent notification with:
- ✅ What was created
- 📍 File locations
- 🔧 Next steps
- 🆔 Automation ID

---

## 🎯 Example Use Cases

### 🛏️ Bedroom with Bed Sensor

**Configuration**:
- Bed sensor: `binary_sensor.bed_occupied`
- Turn off when bed occupied: ✅
- Dark threshold: 25 lux
- Night color: 2700K (very warm)
- Extremely dark: 2 lux

**Result**:
- Lights won't turn on if you move in bed at night
- Auto-off when getting into bed
- Very dim warm lighting for late-night bathroom trips

### 🏢 Home Office with mmWave

**Configuration**:
- PIR sensor: Quick movement detection
- mmWave sensor: Detects stillness at desk
- Dark threshold: 40 lux
- Day color: 5500K (energizing)
- Vacancy multiplier: 10 (keeps lights on while working)

**Result**:
- Lights stay on even when sitting still
- Bright productive lighting
- Won't turn off during long focus sessions

### 🛋️ Living Room with Guest Mode

**Configuration**:
- Guest mode: ✅
- Guest vacancy multiplier: 2.5x
- Guest override multiplier: 2.0x
- Standard vacancy: 5 minutes → 12.5 minutes with guests

**Result**:
- Lights more patient when guests visit
- Manual adjustments last longer
- Less aggressive automation for visitors

### 🚽 Bathroom (Quick & Responsive)

**Configuration**:
- Fixed latency: 30 seconds (quick response)
- Vacancy multiplier: 2 (lights off quickly)
- Fade on: 0.5 seconds (instant feel)
- Bright threshold: 180 lux

**Result**:
- Lights on instantly when entering
- Quick turn-off when empty
- Responsive and efficient

---

## 🔧 Customization After Setup

### Editing the Automation

1. **Settings** → **Automations & Scenes**
2. Find **Universal Smart Lighting - {room_name}**
3. Click to edit
4. Adjust any settings in the blueprint UI

### Modifying Helpers

**Package file**: `/config/packages/lighting_{room_name}.yaml`

Edit manually, then reload:
1. **Developer Tools** → **YAML**
2. Reload **Input Boolean**
3. Reload **Input DateTime**
4. Reload **Input Text**

### Enabling/Disabling Automation

Toggle the helper: `input_boolean.{room_name}_automation_active`

Or disable the automation in the UI.

---

## 📋 Helper Entities Reference

For room name `bedroom`, the wizard creates:

| Entity | Type | Purpose |
|--------|------|---------|
| `input_boolean.bedroom_automation_active` | Boolean | Master on/off switch for automation |
| `input_boolean.bedroom_manual_override` | Boolean | Tracks when user manually controls lights |
| `input_boolean.bedroom_light_auto_on` | Boolean | Controls auto-on behavior |
| `input_boolean.bedroom_occupancy_state` | Boolean | Tracks room occupancy state |
| `input_datetime.bedroom_last_automation_action` | DateTime | Timestamp of last automation action |
| `input_text.bedroom_illuminance_history` | Text | Stores illuminance data for averaging |

All helpers are automatically named with proper formatting and icons.

---

## 🐛 Troubleshooting

### Problem: "Helpers already exist"

**Error**: `Helper entities already exist for this room name`

**Solutions**:
1. **Choose different room name**: Use `bedroom_main`, `bedroom_2`, etc.
2. **Delete existing helpers**: Remove package file and reload helpers
3. **Check for conflicts**: Search in Developer Tools → States

### Problem: Wizard creates automation but it doesn't work

**Solutions**:
1. ✅ Verify blueprint is installed
2. ✅ Check automation is enabled (Settings → Automations)
3. ✅ Verify helpers exist (Developer Tools → States)
4. ✅ Enable debug logging in automation for detailed logs

### Problem: Helpers not appearing

**Solutions**:
1. Check `/config/packages/` directory exists
2. Verify `configuration.yaml` has:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
3. Restart Home Assistant
4. Manually reload helper domains:
   - Developer Tools → YAML → Input Boolean → Reload
   - Developer Tools → YAML → Input DateTime → Reload
   - Developer Tools → YAML → Input Text → Reload

### Problem: Package configuration not loading

**Solution**: The wizard auto-adds packages config to `configuration.yaml`. If it fails:

1. Manually add to `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
2. Create `/config/packages/` directory if missing
3. Restart Home Assistant

---

## 🔄 Managing Multiple Rooms

### Adding More Rooms

Run the wizard multiple times:
1. **First run**: `bedroom` → Creates `lighting_bedroom.yaml`
2. **Second run**: `living_room` → Creates `lighting_living_room.yaml`
3. **Third run**: `home_office` → Creates `lighting_home_office.yaml`

Each room is completely isolated with its own:
- Helper package file
- Automation configuration
- Helper entities

### Deleting a Room Setup

**Complete removal**:

1. **Delete automation**:
   - Settings → Automations → Find room → Delete

2. **Delete helper package**:
   ```bash
   rm /config/packages/lighting_{room_name}.yaml
   ```

3. **Reload helpers**:
   - Developer Tools → YAML → Reload all input domains

4. **Remove wizard entry**:
   - Settings → Devices & Services → Universal Lighting → Delete

---

## 📚 Documentation

### Additional Resources

- 📘 **Blueprint Documentation**: [Universal Smart Lighting README](https://github.com/Chris971991/universal-smart-light-automation/blob/main/README.md)
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/Chris971991/universal-smart-light-automation/issues)
- 💡 **Blueprint Features**: [Feature Documentation](https://github.com/Chris971991/universal-smart-light-automation)
- 🏠 **Home Assistant Blueprints**: [Official Docs](https://www.home-assistant.io/docs/automation/using_blueprints/)

### Architecture Reference

This wizard uses the same package-based helper system as:
- [Smart Climate Control Setup Wizard](https://github.com/Chris971991/Smart-Climate-Control)

**Benefits of package-based approach**:
- ✅ Non-destructive (isolated from other helpers)
- ✅ Easy backup/restore
- ✅ Version control friendly
- ✅ Simple deletion
- ✅ No configuration.yaml pollution

---

## 🚀 Advanced Features

### Validation & Safety

The wizard includes smart validation:
- ✅ Room name sanitization (auto-converts to valid format)
- ✅ Existing helper detection (prevents duplicates)
- ✅ Threshold validation (bright > dark + 10 lux)
- ✅ Package configuration auto-setup
- ✅ Automatic helper reloading

### Auto-Configuration

The wizard automatically:
- Creates packages directory if missing
- Adds packages config to `configuration.yaml`
- Reloads all affected helper domains
- Reloads automation configuration
- Creates persistent notification with summary

### Error Handling

Comprehensive error messages:
- Invalid room name → Guidance on naming rules
- Helpers exist → Options to resolve conflict
- Threshold errors → Explanation of requirements
- Setup failures → Detailed logs for debugging

---

## 🙏 Credits

- **Created by**: [@Chris971991](https://github.com/Chris971991)
- **Blueprint**: [Universal Smart Presence Lighting Control](https://github.com/Chris971991/universal-smart-light-automation)
- **Inspired by**: [Smart Climate Control Setup Wizard](https://github.com/Chris971991/Smart-Climate-Control)
- **Community**: Home Assistant community for amazing tools and support

---

## 📄 License

This integration is part of the Universal Smart Lighting project.

---

## ⭐ Support This Project

If this wizard saves you time and hassle:
- ⭐ **Star the repository** on GitHub
- 🐛 **Report issues** to help improve it
- 💡 **Share with others** in the HA community
- 📝 **Contribute** improvements or documentation

---

**Made with ❤️ for the Home Assistant community**

🧙‍♂️ *Automate your setup, the wizard way!*

---

## 🎯 Next Steps

1. **Install the integration** (see Installation section)
2. **Run the wizard** (Settings → Add Integration)
3. **Test your automation** (walk into the room!)
4. **Fine-tune settings** (edit automation as needed)
5. **Add more rooms** (run wizard again for each room)

Happy automating! ✨
