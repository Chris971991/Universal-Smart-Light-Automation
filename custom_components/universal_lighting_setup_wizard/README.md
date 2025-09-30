# Universal Smart Lighting Setup Wizard

**The easiest way to configure [Universal Smart Presence Lighting Control](https://github.com/Chris971991/universal-smart-light-automation)!**

This custom integration provides a guided, step-by-step wizard that automatically:
- ✅ Creates all required helper entities using the package-based system
- ✅ Generates the automation configuration
- ✅ Sets up everything with best practices built-in
- ✅ Validates your configuration before creating anything

No more manual helper creation. No more copy-paste errors. Just click through a simple wizard and your smart lighting is ready to go!

---

## 🎯 Features

### Automated Helper Creation
- Creates all 6 required helper entities automatically
- Uses **package-based system** (non-destructive, isolated helpers)
- Proper naming convention enforced
- No conflicts with existing entities

### Guided Configuration Flow
1. **Room Setup** - Name your room and select control mode
2. **Presence Detection** - Configure motion/occupancy sensors
3. **Light Levels** - Set illuminance thresholds
4. **Manual Override** - Control automation behavior
5. **Optional Features** - Daytime control, bed sensors, guest mode
6. **Adaptive Lighting** - Brightness, color temperature, fade effects

### Smart Validation
- Checks for existing helpers before creating
- Validates threshold values (bright must exceed dark)
- Sanitizes room names automatically
- Prevents configuration errors

### Package-Based Helper System
All helpers are created in an isolated package file:
```
/config/packages/lighting_{room_name}.yaml
```

**Benefits:**
- Non-destructive (doesn't affect other helpers)
- Easy to backup/restore
- Can be version controlled
- Simple to delete if needed

---

## 📦 Installation

### Method 1: HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the 3 dots in top right → Custom repositories
3. Add repository URL: `https://github.com/Chris971991/universal-smart-light-automation`
4. Category: Integration
5. Click "Install"
6. Restart Home Assistant

### Method 2: Manual Installation

1. Download the `custom_components/universal_lighting_setup_wizard` folder
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

---

## 🚀 Usage

### Initial Setup

1. **Go to Settings → Devices & Services**
2. **Click "+ Add Integration"**
3. **Search for "Universal Smart Lighting Setup Wizard"**
4. **Follow the guided wizard:**

#### Step 1: Room Setup
- Enter room name (e.g., `bedroom`, `living_room`)
- Select control mode (switch + lights, lights only, or switch only)
- Choose light entities

#### Step 2: Presence Detection
- Select motion/occupancy sensors
- Configure sensor timing
- Set vacancy timeout

#### Step 3: Light Levels
- Choose illuminance sensor
- Set dark threshold (when lights turn ON)
- Set bright threshold (when natural light is enough)
- Configure extremely dark threshold for night mode

#### Step 4: Manual Override
- Choose override clearing method
- Set timeout duration
- Configure vacancy clearing

#### Step 5: Optional Features
- Enable daytime energy saving
- Add bed occupancy sensor (for bedrooms)
- Enable guest mode
- Turn on debug logging if needed

#### Step 6: Adaptive Lighting
- Configure adaptive brightness
- Set color temperatures (day/night)
- Configure fade effects
- Set guest mode multipliers

### What Gets Created

After completing the wizard, you'll have:

1. **Helper Package File**: `/config/packages/lighting_{room_name}.yaml`
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
     # ... and 4 more helpers
   ```

2. **Automation Configuration**: Added to `/config/automations.yaml`
   ```yaml
   - id: universal_lighting_bedroom
     alias: Universal Smart Lighting - bedroom
     use_blueprint:
       path: Chris971991/universal-smart-light-automation.yaml
       input:
         room_name: bedroom
         # ... all your settings
   ```

3. **Persistent Notification**: Summary of what was created with next steps

---

## 🔧 Configuration

### Required Prerequisites

1. **Universal Smart Lighting Blueprint** must be installed:
   - Import from: `https://github.com/Chris971991/universal-smart-light-automation`

2. **Packages must be enabled** in `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
   *(The wizard automatically adds this if missing)*

### Supported Control Modes

| Mode | Description | Requires |
|------|-------------|----------|
| **Smart Switch + Smart Lights** | Wall switch that doesn't cut power to smart bulbs | Switch entity + Light entities |
| **Smart Lights Only** | Lamps or fixtures with smart bulbs, no wall switch | Light entities only |
| **Smart Switch Only** | Wall switch controlling regular (non-smart) bulbs | Switch entity only |

### Helper Entities Created

For a room named `bedroom`, the wizard creates:

| Entity ID | Type | Purpose |
|-----------|------|---------|
| `input_boolean.bedroom_automation_active` | Boolean | Enable/disable automation |
| `input_boolean.bedroom_manual_override` | Boolean | Track manual control |
| `input_boolean.bedroom_light_auto_on` | Boolean | Allow auto-on behavior |
| `input_boolean.bedroom_occupancy_state` | Boolean | Track occupancy |
| `input_datetime.bedroom_last_automation_action` | DateTime | Last action timestamp |
| `input_text.bedroom_illuminance_history` | Text | Illuminance averaging data |

---

## 🎨 Customization

### After Wizard Completion

You can customize the automation:
1. Go to **Settings → Automations & Scenes**
2. Find **Universal Smart Lighting - {room_name}**
3. Click to edit and adjust any settings
4. All blueprint inputs are fully customizable

### Modifying Helpers

Helper package file location: `/config/packages/lighting_{room_name}.yaml`

You can manually edit this file if needed, then reload helpers:
```yaml
# Developer Tools → YAML → Input Boolean → Reload
# (Repeat for Input DateTime and Input Text)
```

---

## 🐛 Troubleshooting

### Helpers Already Exist Error

**Problem**: "Helper entities already exist for this room name"

**Solution**:
1. Choose a different room name, OR
2. Delete existing helpers and try again

### Automation Not Working

**Problem**: Automation created but not functioning

**Solutions**:
1. Check if blueprint is installed correctly
2. Enable the automation (Settings → Automations)
3. Verify helper entities exist (Developer Tools → States)
4. Enable debug logging in the automation for detailed logs

### Packages Not Loading

**Problem**: Helpers not appearing after wizard

**Solution**:
1. Verify `/config/packages/` directory exists
2. Check `configuration.yaml` has packages config:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
3. Restart Home Assistant
4. Check logs for YAML errors

### Reload Helpers

If helpers don't appear immediately:
1. Go to **Developer Tools → YAML**
2. Reload **Input Boolean**
3. Reload **Input DateTime**
4. Reload **Input Text**

---

## 📚 Documentation

### Related Resources

- **Blueprint Documentation**: [Universal Smart Lighting README](https://github.com/Chris971991/universal-smart-light-automation)
- **Blueprint Issues**: [GitHub Issues](https://github.com/Chris971991/universal-smart-light-automation/issues)
- **Home Assistant Blueprints**: [Blueprint Documentation](https://www.home-assistant.io/docs/automation/using_blueprints/)

### Example Configurations

<details>
<summary><b>Bedroom with Bed Sensor</b></summary>

**Settings:**
- Room Name: `master_bedroom`
- Control Mode: Smart Switch + Smart Lights
- Bed Sensor: `binary_sensor.bed_occupied`
- Turn off when bed occupied: Yes
- Dark Threshold: 25 lux
- Night Color Temp: 2700K

**Result**: Lights auto-off when you get in bed, gentle warm lighting at night, prevents motion from triggering lights when sleeping.

</details>

<details>
<summary><b>Home Office with mmWave</b></summary>

**Settings:**
- Room Name: `home_office`
- Control Mode: Smart Lights Only
- Primary Sensor: PIR motion sensor
- Secondary Sensor: mmWave occupancy sensor
- Dark Threshold: 40 lux
- Day Color Temp: 5500K (energizing)

**Result**: Detects when you're sitting still at desk, keeps lights on during work, bright energizing daylight color.

</details>

<details>
<summary><b>Living Room with Guest Mode</b></summary>

**Settings:**
- Room Name: `living_room`
- Control Mode: Smart Switch + Smart Lights
- Enable Guest Mode: Yes
- Guest Vacancy Multiplier: 2.5x
- Guest Override Multiplier: 2.0x

**Result**: When guests visit, lights stay on longer, manual adjustments last longer, less aggressive automation.

</details>

---

## 🔄 Updates

### Checking for Updates

The wizard creates automations with update checking enabled by default. To check manually:
1. Look for sensor: `sensor.universal_lighting_updates`
2. Check notification in Home Assistant

### Updating the Integration

1. **HACS**: Click "Update" when available
2. **Manual**: Replace files and restart

**Note**: Updates to the wizard don't affect existing automations - they continue to work independently.

---

## ⚙️ Advanced Usage

### Multiple Rooms

Run the wizard once for each room:
1. **Bedroom** → `bedroom` → Creates `lighting_bedroom.yaml` package
2. **Living Room** → `living_room` → Creates `lighting_living_room.yaml` package
3. **Office** → `home_office` → Creates `lighting_home_office.yaml` package

Each room gets isolated helpers and automation.

### Deleting a Room Setup

To completely remove a room's setup:

1. **Delete Automation**:
   - Settings → Automations → Find room automation → Delete

2. **Delete Helper Package**:
   - Delete `/config/packages/lighting_{room_name}.yaml`

3. **Reload Everything**:
   - Developer Tools → YAML → Reload All

4. **Remove Integration Entry**:
   - Settings → Devices & Services → Find wizard entry → Delete

### Backup & Restore

**Backup a room:**
```bash
# Backup helpers
cp /config/packages/lighting_bedroom.yaml ~/backup/

# Backup automation (extract from automations.yaml)
# Or backup entire automations.yaml
```

**Restore a room:**
```bash
# Restore helpers
cp ~/backup/lighting_bedroom.yaml /config/packages/

# Reload
# Developer Tools → YAML → Reload Input Boolean/DateTime/Text
```

---

## 🤝 Contributing

Found a bug or want to suggest a feature?

1. **For wizard issues**: [Open an issue](https://github.com/Chris971991/universal-smart-light-automation/issues)
2. **For blueprint issues**: [Blueprint issues](https://github.com/Chris971991/universal-smart-light-automation/issues)

---

## 📄 License

This integration is part of the Universal Smart Lighting project.

---

## 🙏 Credits

- **Blueprint**: [Universal Smart Presence Lighting Control](https://github.com/Chris971991/universal-smart-light-automation)
- **Architecture Reference**: [Smart Climate Control Setup Wizard](https://github.com/Chris971991/Smart-Climate-Control)
- **Home Assistant Community**: For amazing tools and support

---

**Made with ❤️ for the Home Assistant community**

🤖 *Automate your lighting, the smart way!*
