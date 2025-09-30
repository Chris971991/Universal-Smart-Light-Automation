## Remote Home Assistant File Access

### Accessing Running Home Assistant Files
Claude can read files directly from the user's Home Assistant instance when shared via network path (SMB/CIFS).

**Access Pattern:**
```bash
# Windows UNC path format
//192.168.50.45/config/blueprints/automation/Chris971991/universal-smart-light-automation.yaml

# Read files to verify deployed blueprint version
Read(file_path="//192.168.50.45/config/blueprints/automation/Chris971991/universal-smart-light-automation.yaml")

# Grep through deployed files
grep -n "pattern" "//192.168.50.45/config/file.yaml"
```

**Use Cases:**
- Verify Deployed Code: Check if blueprint updates have been loaded by Home Assistant
- Debug Issues: Read actual running configuration to identify discrepancies
- Compare Versions: Diff local repository code vs deployed instance code
- Validate Fixes: Confirm that specific logic changes are present in running system

**Example Workflow:**
```bash
# User reports lights not turning off when bed occupied
# Check if deployed blueprint has the latest bed sensor logic (around line 1775-1786)
Read(file_path="//192.168.50.45/config/blueprints/automation/Chris971991/universal-smart-light-automation.yaml", offset=1770, limit=30)

# Verify the bed_occupied logic includes guest mode check:
# bed_occupied: >-
#   {% if not has_bed_sensor %}
#     {{ false }}
#   {% elif enable_guest_mode and guest_ignore_bed %}
#     {{ false }}
#   {% else %}
#     {{ bed_occupied_raw }}
#   {% endif %}
```

**Benefits:**
- Root Cause Analysis: Distinguish between "fix not implemented" vs "fix not working"
- Version Verification: Confirm user has re-imported latest blueprint
- Real-Time Debugging: Inspect actual state when issues occur
- Faster Resolution: No need to ask user to manually check/paste file contents

**Network Path Requirements:**
- Home Assistant must be accessible via SMB/CIFS share
- User must have network share configured: \\192.168.50.45\config
- Claude uses UNC path format with forward slashes: //192.168.50.45/config/

**Key Points:**
- Your HA IP: `192.168.50.45`
- Path format: `//192.168.50.45/config/[path]`
- Works with Read, Grep, and Bash tools
- All your automations: `//192.168.50.45/config/automations.yaml`
- Configuration: `//192.168.50.45/config/configuration.yaml`

## Blueprint Version Updates

### Updating Blueprint Description
When changes are made to the blueprint that warrant a version bump, **ALWAYS update the blueprint description** in `universal-smart-light-automation.yaml`:

**Update Required Fields:**
1. **Version number** in the `name` field: `Universal Smart Presence Lighting Control - v3.9.X`
2. **Version number** in the description header: `**Universal Smart Presence Lighting Control v3.9.X**`
3. **Latest Update section** - Replace with current version changes:

```yaml
## 🆕 Latest Update - v3.9.X

**🐛 Bug Fixes:** or **✨ New Features:** or **⚡ Improvements:**
- ✅ Description of change 1
- ✅ Description of change 2
- ✅ Description of change 3

📖 **Full changelog:** https://github.com/Chris971991/universal-smart-light-automation/releases
```

**Important:**
- Only show the **LATEST version** changes in the description
- Keep it brief (3-5 bullet points max)
- Use appropriate emoji: 🐛 for fixes, ✨ for features, ⚡ for improvements
- Point to GitHub releases for full changelog
- Update BOTH the name field AND description block version numbers