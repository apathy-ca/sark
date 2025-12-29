#!/usr/bin/env python3
"""
Multi-Protocol Smart Home Automation Example for SARK v2.0.

Demonstrates orchestrating HTTP, MCP, and gRPC protocols under unified governance.
"""

import asyncio
from datetime import datetime
import sys
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class SmartHomeAutomation:
    """
    Smart home automation system using SARK multi-protocol governance.

    Protocols used:
    - HTTP: Weather API, Slack notifications
    - MCP: Weather analytics tool
    - gRPC: IoT device controller
    """

    def __init__(self, sark_url: str = "http://localhost:8000"):
        """Initialize automation system."""
        self.sark_url = sark_url
        self.principal_id = "automation-service"
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def run_automation(self) -> dict[str, Any]:
        """
        Execute the complete automation workflow.

        Workflow:
        1. Fetch weather (HTTP)
        2. Analyze weather (MCP)
        3. Control devices (gRPC)
        4. Send notification (HTTP)
        """
        print("🏠 Starting Smart Home Automation...")
        results = {"steps": [], "timestamp": datetime.utcnow().isoformat()}

        try:
            # Step 1: Fetch weather from OpenWeatherMap
            print("\n🌡️  Step 1: Fetching weather data (HTTP)...")
            weather = await self._fetch_weather()
            results["weather"] = weather
            print(f"   Weather: {weather['description']}, {weather['temperature']}°C")

            # Step 2: Analyze weather using MCP tool
            print("\n📊 Step 2: Analyzing weather data (MCP)...")
            analysis = await self._analyze_weather(weather)
            results["analysis"] = analysis
            print(f"   Recommendation: {analysis['recommendation']}")

            # Step 3: Control devices via gRPC
            print("\n🏠 Step 3: Controlling smart home devices (gRPC)...")
            device_states = await self._control_devices(analysis)
            results["devices"] = device_states
            print(f"   Devices updated: {device_states}")

            # Step 4: Send Slack notification
            print("\n📱 Step 4: Sending notification (Slack HTTP)...")
            notification = await self._send_notification(weather, analysis, device_states)
            results["notification"] = notification
            print(f"   Notification sent to #{notification['channel']}")

            results["success"] = True
            print("\n✅ Automation complete!")

        except Exception as e:
            logger.error("automation_failed", error=str(e), exc_info=True)
            results["success"] = False
            results["error"] = str(e)
            print(f"\n❌ Automation failed: {e}")

        finally:
            await self.http_client.aclose()

        return results

    async def _fetch_weather(self) -> dict[str, Any]:
        """
        Fetch current weather from OpenWeatherMap API.

        Protocol: HTTP
        Resource: OpenWeatherMap API
        Capability: GET /weather
        """
        response = await self.http_client.post(
            f"{self.sark_url}/api/v2/authorize",
            json={
                "capability_id": "http-openweathermap-GET-/weather",
                "principal_id": self.principal_id,
                "arguments": {
                    "q": "London,UK",
                    "units": "metric"
                },
                "context": {
                    "automation": "smart_home",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            raise Exception(f"Weather API error: {result.get('error')}")

        data = result["result"]
        return {
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "clouds": data["clouds"]["all"]
        }

    async def _analyze_weather(self, weather: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze weather data using MCP analytics tool.

        Protocol: MCP
        Resource: Weather Analytics Tool
        Capability: analyze_comfort
        """
        response = await self.http_client.post(
            f"{self.sark_url}/api/v2/authorize",
            json={
                "capability_id": "mcp-weather-analytics-analyze_comfort",
                "principal_id": self.principal_id,
                "arguments": {
                    "temperature": weather["temperature"],
                    "humidity": weather["humidity"],
                    "cloud_coverage": weather["clouds"]
                },
                "context": {
                    "weather_source": "openweathermap",
                    "automation": "smart_home"
                }
            }
        )
        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            raise Exception(f"Analytics error: {result.get('error')}")

        return result["result"]

    async def _control_devices(self, analysis: dict[str, Any]) -> dict[str, Any]:
        """
        Control smart home devices via gRPC.

        Protocol: gRPC
        Resource: IoT Device Controller
        Service: DeviceController
        Method: SetDeviceStates
        """
        # Build device commands based on analysis
        device_commands = []

        if analysis.get("lighting_recommendation") == "increase":
            device_commands.append({
                "device_id": "living_room_lights",
                "state": "on",
                "brightness": 80
            })

        if analysis.get("temperature_action") == "heat":
            device_commands.append({
                "device_id": "heater",
                "state": "on",
                "temperature": 22
            })
        elif analysis.get("temperature_action") == "cool":
            device_commands.append({
                "device_id": "ac",
                "state": "on",
                "temperature": 20
            })

        response = await self.http_client.post(
            f"{self.sark_url}/api/v2/authorize",
            json={
                "capability_id": "DeviceController.SetDeviceStates",
                "principal_id": self.principal_id,
                "arguments": {
                    "commands": device_commands
                },
                "context": {
                    "automation": "smart_home",
                    "reason": analysis.get("recommendation")
                }
            }
        )
        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            raise Exception(f"Device control error: {result.get('error')}")

        return result["result"]["states"]

    async def _send_notification(
        self,
        weather: dict[str, Any],
        analysis: dict[str, Any],
        device_states: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Send notification to Slack.

        Protocol: HTTP
        Resource: Slack API
        Capability: chat.postMessage
        """
        # Build message
        device_summary = ", ".join([
            f"{device}: {state['state']}"
            for device, state in device_states.items()
        ])

        message = f"""
🏠 *Smart Home Automation Update*

*Weather:* {weather['description']}, {weather['temperature']}°C
*Humidity:* {weather['humidity']}%

*AI Recommendation:* {analysis.get('recommendation')}

*Devices Adjusted:*
{device_summary}

*Timestamp:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
*Automation ID:* `{self.principal_id}`
"""

        response = await self.http_client.post(
            f"{self.sark_url}/api/v2/authorize",
            json={
                "capability_id": "http-slack-chat.postMessage",
                "principal_id": self.principal_id,
                "arguments": {
                    "channel": "#smart-home",
                    "text": message,
                    "unfurl_links": False
                },
                "context": {
                    "automation": "smart_home",
                    "notification_type": "status_update"
                }
            }
        )
        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            raise Exception(f"Slack notification error: {result.get('error')}")

        return {
            "channel": "#smart-home",
            "message_ts": result["result"].get("ts")
        }


async def main():
    """Run the automation."""
    automation = SmartHomeAutomation()
    results = await automation.run_automation()

    # Print summary
    print("\n" + "=" * 60)
    print("AUTOMATION SUMMARY")
    print("=" * 60)
    print(f"Success: {results.get('success')}")
    print(f"Timestamp: {results.get('timestamp')}")

    if results.get("success"):
        print(f"\nWeather: {results['weather']['description']}")
        print(f"Temperature: {results['weather']['temperature']}°C")
        print(f"\nAnalysis: {results['analysis'].get('recommendation')}")
        print(f"\nDevices: {len(results['devices'])} updated")
        print(f"Notification: Sent to {results['notification']['channel']}")
    else:
        print(f"\nError: {results.get('error')}")

    # View audit trail
    print("\n" + "=" * 60)
    print("View complete audit trail at:")
    print("http://localhost:8000/api/v1/audit-log?principal_id=automation-service")
    print("=" * 60)

    return 0 if results.get("success") else 1


if __name__ == "__main__":
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ]
    )

    sys.exit(asyncio.run(main()))
