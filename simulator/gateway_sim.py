"""
FarmPulse Edge Gateway Simulator

Simulates one or more LoRa gateways that publish telemetry to EMQX.
Aligned with the FarmPulse seeded database slugs.

Examples:
  python simulator/gateway_sim.py
  python simulator/gateway_sim.py --interval 5
  python simulator/gateway_sim.py --device-id gw-lora-002
  python simulator/gateway_sim.py --org-id org-greenfield --farm-id farm10 --device-id gw-lora-101
  python simulator/gateway_sim.py --devices 3
  python simulator/gateway_sim.py --replay simulator/sample_buffer.json --device-id gw-lora-001
"""

import argparse
import json
import math
import os
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.environ.get("EMQX_HOST", "localhost")
MQTT_PORT = int(os.environ.get("EMQX_PORT", 1884))
TOPIC_TMPL = "{org_id}/farms/{farm_id}/gateways/{device_id}/telemetry"

DEFAULT_ORG_ID = os.environ.get("SIM_ORG_ID", "org-sunrise")
DEFAULT_FARM_ID = os.environ.get("SIM_FARM_ID", "farm01")
DEFAULT_DEVICE_ID = os.environ.get("SIM_DEVICE_ID", "gw-lora-001")

SEEDED_DEVICE_PRESETS = [
    {"org_id": "org-sunrise", "farm_id": "farm01", "device_id": "gw-lora-001"},
    {"org_id": "org-sunrise", "farm_id": "farm01", "device_id": "gw-lora-002"},
    {"org_id": "org-sunrise", "farm_id": "farm02", "device_id": "gw-lora-011"},
    {"org_id": "org-greenfield", "farm_id": "farm10", "device_id": "gw-lora-101"},
    {"org_id": "org-greenfield", "farm_id": "farm10", "device_id": "gw-lora-102"},
    {"org_id": "org-northbarn", "farm_id": "farm20", "device_id": "gw-lora-201"},
    {"org_id": "org-northbarn", "farm_id": "farm20", "device_id": "gw-lora-202"},
    {"org_id": "org-northbarn", "farm_id": "farm21", "device_id": "gw-lora-211"},
]


def get_hour_fraction() -> float:
    now = datetime.now()
    return now.hour + now.minute / 60.0


def simulate_temperature(base: float = 24.0, amplitude: float = 4.0) -> float:
    h = get_hour_fraction()
    cycle = math.sin((h / 24.0) * 2 * math.pi - math.pi / 2 + (14 / 24.0) * 2 * math.pi)
    value = base + amplitude * cycle + random.gauss(0, 0.3)
    return round(max(15.0, min(40.0, value)), 2)


def simulate_humidity(base: float = 65.0) -> float:
    h = get_hour_fraction()
    cycle = -math.sin((h / 24.0) * 2 * math.pi - math.pi / 2 + (14 / 24.0) * 2 * math.pi)
    value = base + 8 * cycle + random.gauss(0, 1.0)
    return round(max(30.0, min(95.0, value)), 2)


def simulate_lux(day_max: float = 800.0) -> float:
    h = get_hour_fraction()
    if h < 6.0 or h > 20.0:
        return 0.0
    peak_hour = 13.0
    width = 4.5
    cycle = math.exp(-((h - peak_hour) ** 2) / (2 * width ** 2))
    value = day_max * cycle + random.gauss(0, 15.0)
    return round(max(0.0, value), 2)


def simulate_nh3(device_state: dict) -> float:
    current = device_state.get("nh3", 12.0)
    if random.random() < 0.05:
        current = max(5.0, current - random.uniform(5.0, 15.0))
        device_state["nh3"] = current
        return round(current, 2)
    drift = random.gauss(0.15, 0.1)
    current = current + drift + random.gauss(0, 0.5)
    current = max(3.0, min(80.0, current))
    device_state["nh3"] = current
    return round(current, 2)


class GatewaySimulator:
    def __init__(self, org_id: str, farm_id: str, device_id: str, interval: int = 60):
        self.org_id = org_id
        self.farm_id = farm_id
        self.device_id = device_id
        self.interval = interval
        self.seq = 0
        self.state = {"nh3": random.uniform(8.0, 18.0)}
        self.client = None
        self.connected = False
        self.topic = TOPIC_TMPL.format(
            org_id=self.org_id,
            farm_id=self.farm_id,
            device_id=self.device_id,
        )

    def _build_payload(self, is_buffered: bool = False, override_ts: int | None = None) -> dict:
        self.seq += 1
        return {
            "schema_version": "1.0",
            "org_id": self.org_id,
            "farm_id": self.farm_id,
            "device_id": self.device_id,
            "sent_ts": override_ts or int(time.time() * 1000),
            "seq": self.seq,
            "is_buffered": is_buffered,
            "readings": {
                "temperature": simulate_temperature(),
                "humidity": simulate_humidity(),
                "lux": simulate_lux(),
                "nh3": simulate_nh3(self.state),
            },
        }

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.connected = True
            print(f"[{self.device_id}] Connected to EMQX at {MQTT_HOST}:{MQTT_PORT} | topic={self.topic}")
        else:
            print(f"[{self.device_id}] Connection failed: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False
        if reason_code != 0:
            print(f"[{self.device_id}] Disconnected unexpectedly (code {reason_code}). Reconnecting...")

    def _on_publish(self, client, userdata, mid, reason_codes, properties):
        print(f"[{self.device_id}] ✅ Published (mid={mid}, seq={self.seq})")

    def connect(self):
        self.client = mqtt.Client(
            client_id=f"farmpulse-sim-{self.device_id}",
            protocol=mqtt.MQTTv5,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        self.client.loop_start()

        timeout = 10
        while not self.connected and timeout > 0:
            time.sleep(0.5)
            timeout -= 0.5
        if not self.connected:
            raise ConnectionError(f"[{self.device_id}] Could not connect to EMQX")

    def publish_once(self):
        payload = self._build_payload()
        self.client.publish(self.topic, json.dumps(payload), qos=1)
        print(
            f"[{self.device_id}] 📡 Sending: org={self.org_id} farm={self.farm_id} "
            f"temp={payload['readings']['temperature']}°C hum={payload['readings']['humidity']}% "
            f"lux={payload['readings']['lux']} nh3={payload['readings']['nh3']}ppm"
        )

    def run_continuous(self):
        print(f"[{self.device_id}] 🚀 Starting — publishing every {self.interval}s")
        while True:
            try:
                self.publish_once()
            except Exception as e:
                print(f"[{self.device_id}] ⚠️ Publish error: {e}")
            time.sleep(self.interval)

    def replay_buffer(self, buffer_file: str):
        path = Path(buffer_file)
        if not path.exists():
            print(f"[{self.device_id}] ❌ Buffer file not found: {buffer_file}")
            sys.exit(1)

        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)

        print(f"[{self.device_id}] 📦 Replaying {len(entries)} buffered entries from {buffer_file}")
        for entry in entries:
            payload = self._build_payload(
                is_buffered=True,
                override_ts=entry.get("sent_ts", int(time.time() * 1000)),
            )
            if "readings" in entry:
                payload["readings"] = entry["readings"]
            self.client.publish(self.topic, json.dumps(payload), qos=1)
            print(f"[{self.device_id}] 📦 Replayed entry ts={payload['sent_ts']}")
            time.sleep(0.2)

        print(f"[{self.device_id}] ✅ Replay complete")

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


def run_device(org_id: str, farm_id: str, device_id: str, interval: int):
    sim = GatewaySimulator(org_id=org_id, farm_id=farm_id, device_id=device_id, interval=interval)
    sim.connect()
    sim.run_continuous()


def main():
    parser = argparse.ArgumentParser(description="FarmPulse Gateway Simulator")
    parser.add_argument("--devices", type=int, default=1, help="Number of concurrent gateways to run from the seeded preset list")
    parser.add_argument("--interval", type=int, default=60, help="Publish interval in seconds")
    parser.add_argument("--replay", type=str, default=None, help="Path to JSON buffer file to replay")
    parser.add_argument("--device-id", type=str, default=None, help="Specific device slug (single device mode)")
    parser.add_argument("--org-id", type=str, default=DEFAULT_ORG_ID, help="Organization slug")
    parser.add_argument("--farm-id", type=str, default=DEFAULT_FARM_ID, help="Farm slug")
    args = parser.parse_args()

    if args.replay:
        sim = GatewaySimulator(
            org_id=args.org_id,
            farm_id=args.farm_id,
            device_id=args.device_id or DEFAULT_DEVICE_ID,
            interval=args.interval,
        )
        sim.connect()
        sim.replay_buffer(args.replay)
        sim.disconnect()
        return

    if args.devices == 1:
        sim = GatewaySimulator(
            org_id=args.org_id,
            farm_id=args.farm_id,
            device_id=args.device_id or DEFAULT_DEVICE_ID,
            interval=args.interval,
        )
        sim.connect()
        sim.run_continuous()
        return

    presets = SEEDED_DEVICE_PRESETS[: args.devices]
    if not presets:
        print("No seeded device presets available.")
        sys.exit(1)

    threads = []
    for preset in presets:
        t = threading.Thread(
            target=run_device,
            args=(preset["org_id"], preset["farm_id"], preset["device_id"], args.interval),
            daemon=True,
            name=f"sim-{preset['device_id']}",
        )
        threads.append(t)
        t.start()
        time.sleep(0.5)

    print(f"🐔 {len(presets)} gateway simulators running from seeded presets. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⛔ Simulator stopped.")


if __name__ == "__main__":
    main()
