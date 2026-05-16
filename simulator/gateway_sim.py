"""
FarmPulse Edge Gateway Simulator — Multi-Org/Farm/Device Edition

Usage:
  python simulator/gateway_sim.py                         # single device (default)
  python simulator/gateway_sim.py --all                   # all 14 registered devices
  python simulator/gateway_sim.py --org org-sunrise        # all devices in one org
  python simulator/gateway_sim.py --farm farm-gv-01        # all devices in one farm
  python simulator/gateway_sim.py --device-id gw-lora-002  # specific device
  python simulator/gateway_sim.py --interval 5 --all       # fast dev mode
  python simulator/gateway_sim.py --replay buffer.json     # replay buffer
"""

import argparse
import json
import math
import random
import sys
import time
import threading
import os
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

# ─── MQTT Config ──────────────────────────────────────────────────────────────
MQTT_HOST = os.environ.get("EMQX_HOST", "localhost")
MQTT_PORT = int(os.environ.get("EMQX_PORT", 1884))
TOPIC_TMPL = "{org_id}/farms/{farm_id}/gateways/{device_id}/telemetry"

# ─── Device Registry (matches seed_dev_data.py) ───────────────────────────────
# Each entry: (org_id, farm_id, device_id, sensors, status)
DEVICE_REGISTRY = [
    # org-sunrise
    ("org-sunrise",    "farm-01",      "gw-lora-001", ["temperature", "humidity"],              "active"),
    ("org-sunrise",    "farm-01",      "gw-lora-002", ["temperature", "humidity", "lux"],       "active"),
    ("org-sunrise",    "farm-02",      "gw-lora-003", ["temperature", "humidity", "nh3"],       "active"),
    ("org-sunrise",    "farm-02",      "gw-lora-004", ["temperature", "humidity"],              "inactive"),
    # org-greenvalley
    ("org-greenvalley","farm-gv-01",   "gw-gv-001",   ["temperature", "humidity", "lux"],       "active"),
    ("org-greenvalley","farm-gv-01",   "gw-gv-002",   ["temperature", "humidity", "lux", "nh3"],"active"),
    ("org-greenvalley","farm-gv-02",   "gw-gv-003",   ["temperature", "humidity"],              "active"),
    ("org-greenvalley","farm-gv-03",   "gw-gv-004",   ["temperature", "humidity", "lux"],       "active"),
    ("org-greenvalley","farm-gv-03",   "gw-gv-005",   ["temperature", "humidity"],              "stolen"),
    # org-tehranagri
    ("org-tehranagri", "farm-ta-01",   "gw-ta-001",   ["temperature", "humidity", "nh3"],       "active"),
    ("org-tehranagri", "farm-ta-01",   "gw-ta-002",   ["temperature", "humidity"],              "active"),
    ("org-tehranagri", "farm-ta-02",   "gw-ta-003",   ["temperature", "humidity", "lux"],       "inactive"),
]

# ─── Sensor Simulators ────────────────────────────────────────────────────────

def _hour_frac() -> float:
    now = datetime.now()
    return now.hour + now.minute / 60.0

def simulate_temperature(base: float = 24.0, amplitude: float = 4.0) -> float:
    h = _hour_frac()
    cycle = math.sin((h / 24.0) * 2 * math.pi - math.pi / 2 + (14 / 24.0) * 2 * math.pi)
    value = base + amplitude * cycle + random.gauss(0, 0.3)
    return round(max(15.0, min(40.0, value)), 2)

def simulate_humidity(base: float = 65.0) -> float:
    h = _hour_frac()
    cycle = -math.sin((h / 24.0) * 2 * math.pi - math.pi / 2 + (14 / 24.0) * 2 * math.pi)
    value = base + 8 * cycle + random.gauss(0, 1.0)
    return round(max(30.0, min(95.0, value)), 2)

def simulate_lux(day_max: float = 800.0) -> float:
    h = _hour_frac()
    if h < 6.0 or h > 20.0:
        return 0.0
    peak_hour, width = 13.0, 4.5
    cycle = math.exp(-((h - peak_hour) ** 2) / (2 * width ** 2))
    value = day_max * cycle + random.gauss(0, 15.0)
    return round(max(0.0, value), 2)

def simulate_nh3(device_state: dict) -> float:
    current = device_state.get("nh3", 12.0)
    if random.random() < 0.05:
        current = max(5.0, current - random.uniform(5.0, 15.0))
    else:
        drift = random.gauss(0.15, 0.1)
        current = current + drift + random.gauss(0, 0.5)
        current = max(3.0, min(80.0, current))
    device_state["nh3"] = current
    return round(current, 2)

# ─── Simulator Class ──────────────────────────────────────────────────────────

class GatewaySimulator:
    def __init__(self, org_id: str, farm_id: str, device_id: str,
                 sensors: list, interval: int = 60):
        self.org_id = org_id
        self.farm_id = farm_id
        self.device_id = device_id
        self.sensors = sensors          # e.g. ["temperature", "humidity", "lux"]
        self.interval = interval
        self.seq = 0
        self.state = {"nh3": random.uniform(8.0, 18.0)}
        self.client = None
        self.connected = False
        self.topic = TOPIC_TMPL.format(
            org_id=org_id, farm_id=farm_id, device_id=device_id
        )

    def _build_readings(self) -> dict:
        readings = {
            "temperature": simulate_temperature(),
            "humidity":    simulate_humidity(),
        }
        if "lux" in self.sensors:
            readings["lux"] = simulate_lux()
        if "nh3" in self.sensors:
            readings["nh3"] = simulate_nh3(self.state)
        return readings

    def build_payload(self, is_buffered: bool = False, override_ts: int = None) -> dict:
        self.seq += 1
        return {
            "schema_version": "1.0",
            "org_id":    self.org_id,
            "farm_id":   self.farm_id,
            "device_id": self.device_id,
            "sent_ts":   override_ts or int(time.time() * 1000),
            "seq":       self.seq,
            "is_buffered": is_buffered,
            "readings":  self._build_readings(),
        }

    # ── MQTT callbacks ────────────────────────────────────────────────────────
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.connected = True
            print(f"[{self.device_id}] Connected to EMQX at {MQTT_HOST}:{MQTT_PORT}")
        else:
            print(f"[{self.device_id}] Connection failed: {reason_code}")

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False
        if reason_code != 0:
            print(f"[{self.device_id}] Disconnected unexpectedly ({reason_code}). Reconnecting...")

    def on_publish(self, client, userdata, mid, reason_codes, properties):
        print(f"[{self.device_id}] Published mid={mid}, seq={self.seq}")

    # ── Connection ────────────────────────────────────────────────────────────
    def connect(self):
        self.client = mqtt.Client(
            client_id=f"farmpulse-sim-{self.device_id}",
            protocol=mqtt.MQTTv5,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self.client.on_connect    = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish    = self.on_publish
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        self.client.loop_start()

        timeout = 10
        while not self.connected and timeout > 0:
            time.sleep(0.5)
            timeout -= 0.5
        if not self.connected:
            raise ConnectionError(f"[{self.device_id}] Could not connect to EMQX")

    # ── Publish modes ─────────────────────────────────────────────────────────
    def publish_once(self):
        payload = self.build_payload()
        readings = payload["readings"]
        self.client.publish(self.topic, json.dumps(payload), qos=1)
        parts = [
            f"temp={readings['temperature']}°C",
            f"hum={readings['humidity']}%",
        ]
        if "lux" in readings:
            parts.append(f"lux={readings['lux']}")
        if "nh3" in readings:
            parts.append(f"nh3={readings['nh3']}ppm")
        print(f"[{self.device_id}] Sending {' | '.join(parts)}")

    def run_continuous(self):
        print(f"[{self.device_id}] Publishing every {self.interval}s (sensors: {self.sensors})")
        while True:
            try:
                self.publish_once()
            except Exception as e:
                print(f"[{self.device_id}] Publish error: {e}")
            time.sleep(self.interval)

    def replay_buffer(self, buffer_file: str):
        path = Path(buffer_file)
        if not path.exists():
            print(f"[{self.device_id}] Buffer file not found: {buffer_file}")
            sys.exit(1)
        with open(path) as f:
            entries = json.load(f)
        print(f"[{self.device_id}] Replaying {len(entries)} buffered entries from {buffer_file}")
        for entry in entries:
            payload = self.build_payload(is_buffered=True, override_ts=entry.get("sent_ts"))
            if "readings" in entry:
                payload["readings"] = entry["readings"]
            self.client.publish(self.topic, json.dumps(payload), qos=1)
            print(f"[{self.device_id}] Replayed ts={payload['sent_ts']}")
            time.sleep(0.2)
        print(f"[{self.device_id}] Replay complete")

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

# ─── Thread Runner ────────────────────────────────────────────────────────────

def run_device(org_id, farm_id, device_id, sensors, interval):
    sim = GatewaySimulator(org_id, farm_id, device_id, sensors, interval)
    sim.connect()
    sim.run_continuous()

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FarmPulse Gateway Simulator")
    parser.add_argument("--all",       action="store_true", help="Run all registered devices")
    parser.add_argument("--org",       type=str, default=None, help="Filter by org slug")
    parser.add_argument("--farm",      type=str, default=None, help="Filter by farm slug")
    parser.add_argument("--device-id", type=str, default=None, help="Specific device ID")
    parser.add_argument("--interval",  type=int, default=60,   help="Publish interval in seconds")
    parser.add_argument("--replay",    type=str, default=None, help="Path to JSON buffer file")
    parser.add_argument("--skip-inactive", action="store_true",
                        help="Skip devices with inactive/stolen status (default: include all)")
    args = parser.parse_args()

    # Build candidate list from registry
    candidates = list(DEVICE_REGISTRY)

    if args.skip_inactive:
        candidates = [d for d in candidates if d[4] == "active"]
    if args.org:
        candidates = [d for d in candidates if d[0] == args.org]
    if args.farm:
        candidates = [d for d in candidates if d[1] == args.farm]
    if args.device_id:
        candidates = [d for d in candidates if d[2] == args.device_id]

    if not candidates:
        print("No devices matched your filters. Check --org / --farm / --device-id values.")
        sys.exit(1)

    # ── Replay mode (single device only) ──────────────────────────────────────
    if args.replay:
        org_id, farm_id, device_id, sensors, _ = candidates[0]
        sim = GatewaySimulator(org_id, farm_id, device_id, sensors, args.interval)
        sim.connect()
        sim.replay_buffer(args.replay)
        sim.disconnect()
        return

    # ── Single device (main thread) ───────────────────────────────────────────
    if not args.all and len(candidates) == 1:
        org_id, farm_id, device_id, sensors, _ = candidates[0]
        sim = GatewaySimulator(org_id, farm_id, device_id, sensors, args.interval)
        sim.connect()
        sim.run_continuous()
        return

    # ── Multi-device (threaded) ───────────────────────────────────────────────
    threads = []
    for org_id, farm_id, device_id, sensors, status in candidates:
        t = threading.Thread(
            target=run_device,
            args=(org_id, farm_id, device_id, sensors, args.interval),
            daemon=True,
            name=f"sim-{device_id}",
        )
        threads.append(t)
        t.start()
        time.sleep(0.5)  # stagger connections

    print(f"\n▶ {len(threads)} gateway simulators running. Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")

if __name__ == "__main__":
    main()
    
    
    
# All active devices, fast mode
# python simulator/gateway_sim.py --all --interval 5 --skip-inactive

# Only Sunrise Poultry devices
# python simulator/gateway_sim.py --org org-sunrise --interval 10

# Just one specific device
# python simulator/gateway_sim.py --device-id gw-gv-002 --interval 5

# Replay a buffer for a specific farm
# python simulator/gateway_sim.py --farm farm-ta-01 --replay buffer.json