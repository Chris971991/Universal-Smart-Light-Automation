# Installation Guide

## Quick Install

### HACS (Recommended)

1. Open HACS → Integrations
2. Click ⋮ → Custom repositories
3. Add: `https://github.com/Chris971991/universal-smart-light-automation`
4. Category: Integration
5. Install
6. Restart Home Assistant

### Manual

1. Copy `custom_components/universal_lighting_setup_wizard/` to your HA config
2. Restart Home Assistant

## Usage

1. Settings → Devices & Services
2. Add Integration → "Universal Smart Lighting Setup Wizard"
3. Follow the wizard steps
4. Done!

## What You Need

- Universal Smart Lighting Blueprint installed
- At least one motion/occupancy sensor
- At least one illuminance sensor (or create `input_number` helper)

## Troubleshooting

### Helpers not appearing?
1. Check `/config/packages/` exists
2. Verify `configuration.yaml` has packages config
3. Reload helper domains (Developer Tools → YAML)

### Automation not working?
1. Check blueprint is installed
2. Enable automation (Settings → Automations)
3. Enable debug logging for detailed logs

Full docs: [README.md](README.md)
