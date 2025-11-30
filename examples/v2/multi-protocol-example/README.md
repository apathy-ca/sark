# Multi-Protocol Example: Smart Home Automation

This example demonstrates SARK v2.0's ability to govern workflows spanning multiple protocols in a real-world smart home automation scenario.

## Scenario

Build a smart home automation system that:
1. **Monitors weather** via REST API (HTTP)
2. **Analyzes data** using an MCP analytics tool
3. **Controls devices** via gRPC IoT service
4. **Sends notifications** via Slack (HTTP)

All governed by SARK with unified policies and complete audit trail.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                SARK v2.0 Gateway                │
│         (Unified Policy & Audit)                │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬──────────────┐
        │             │             │              │
   ┌────────┐   ┌─────────┐   ┌─────────┐   ┌──────────┐
   │Weather │   │Analytics│   │  IoT    │   │  Slack   │
   │  API   │   │   MCP   │   │ gRPC    │   │   HTTP   │
   │ (HTTP) │   │  Tool   │   │Service  │   │   API    │
   └────────┘   └─────────┘   └─────────┘   └──────────┘
```

## Prerequisites

- SARK v2.0 running (see [QUICKSTART](../../../docs/tutorials/v2/QUICKSTART.md))
- Python 3.11+
- Docker for running sample IoT service

## Setup

### 1. Start the Sample IoT gRPC Service

```bash
cd iot-service
docker-compose up -d
```

This starts a sample gRPC service that controls simulated smart home devices.

### 2. Register Resources with SARK

```bash
# Run the setup script
python setup_resources.py
```

This registers:
- OpenWeatherMap API (HTTP)
- Weather Analytics Tool (MCP)
- IoT Device Controller (gRPC)
- Slack Notifications (HTTP)

### 3. Configure Policies

```bash
# Upload the smart home policy
./upload_policy.sh
```

## Running the Example

### Basic Automation

```bash
python automation.py

# Output:
# 🌡️  Checking weather...
# ☁️  Weather: Cloudy, 15°C
# 📊 Analyzing weather data (MCP)...
# 💡 Decision: Turn on indoor lights (comfort mode)
# 🏠 Controlling devices (gRPC)...
# ✅ Devices updated: [living_room_lights=on, heater=off]
# 📱 Sending notification (Slack)...
# ✅ Notification sent to #smart-home
# ✅ Automation complete!
```

### Advanced Workflow

```bash
python advanced_automation.py --scenario rainy_day

# Runs a complex workflow:
# 1. Fetch weather forecast (HTTP)
# 2. Analyze trend (MCP)
# 3. Adjust multiple devices (gRPC batch)
# 4. Send summary (Slack with charts)
```

## Files

- `setup_resources.py` - Register all resources with SARK
- `automation.py` - Basic multi-protocol automation
- `advanced_automation.py` - Advanced workflows with error handling
- `policy.rego` - Smart home authorization policies
- `iot-service/` - Sample gRPC IoT service
- `test_automation.py` - Automated tests

## Policy Highlights

```rego
# Allow automation service to control devices
# but only during specific scenarios

allow if {
    input.principal.id == "automation-service"
    input.capability.name == "SetDevice"

    # Only allow if weather conditions warrant it
    weather_justifies_action(input.context.weather, input.arguments.device)
}

# Prevent dangerous combinations
deny["Cannot enable heater and AC simultaneously"] if {
    input.arguments.device == "heater"
    input.arguments.state == "on"
    current_ac_state == "on"
}
```

## Audit Trail

View the complete multi-protocol audit trail:

```bash
python view_audit.py

# Shows:
# - All weather API calls (HTTP)
# - All analytics invocations (MCP)
# - All device controls (gRPC)
# - All notifications (Slack HTTP)
```

## Learn More

- [QUICKSTART Guide](../../../docs/tutorials/v2/QUICKSTART.md)
- [Multi-Protocol Orchestration](../../../docs/tutorials/v2/MULTI_PROTOCOL_ORCHESTRATION.md)
- [Building Adapters](../../../docs/tutorials/v2/BUILDING_ADAPTERS.md)

## License

MIT
