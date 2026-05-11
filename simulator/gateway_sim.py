"""
FarmPulse Edge Gateway Simulator

Simulates a LoRa gateway that reads from sensors and publishes 
averaged telemetry every 60 seconds via MQTT.

Usage:
  python simulator/gateway_sim.py                  # single device, default config
  python simulator/gateway_sim.py --devices 3      # 3 concurrent gateways
  python simulator/gateway_sim.py --replay buffer.json  # replay offline buffer
  python simulator/gateway_sim.py --interval 5     # publish every 5s (fast dev mode)
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

# --- MQTT Config ---
MQTT_HOST = os.environ.get("EMQX_HOST", "localhost")
MQTT_PORT = int(os.environ.get("EMQX_PORT", 1884))
TOPIC_TMPL = "{org_id}/farms/{farm_id}/gateways/{device_id}/telemetry"

# --- Farm Identity ---
# UPDATED: Matches seed_dev_data.py exactly
ORG_ID = os.environ.get("SIM_ORG_ID", "org-sunrise")
FARM_ID = os.environ.get("SIM_FARM_ID", "farm01")

def get_hour_fraction() -> float:
    """Current time as a float 0.0-24.0"""
    now = datetime.now()
    return now.hour + (now.minute / 60.0)

def simulate_temperature(base: float = 24.0, amplitude: float = 4.0) -> float:
    """
    Sinusoidal daily cycle peaking at 14:00, trough at 02:00.
    Base 24C +/- 4C + small Gaussian noise. Healthy range: 18-32C
    """
    h = get_hour_fraction()
    # Peak at hour 14 -> phase shift: (14/24)*2pi
    cycle = math.sin((h / 24.0) * 2 * math.pi - (math.pi / 2) + (14 / 24.0) * 2 * math.pi)
    value = base + (amplitude * cycle) + random.gauss(0, 0.3)
    return round(max(15.0, min(40.0, value)), 2)

def simulate_humidity(base: float = 65.0) -> float:
    """
    Inversely correlated with temperature (hotter = drier).
    Base 65% +/- 8% + noise. Healthy range: 50-80%
    """
    h = get_hour_fraction()
    # Inverse of temperature cycle
    cycle = -math.sin((h / 24.0) * 2 * math.pi - (math.pi / 2) + (14 / 24.0) * 2 * math.pi)
    value = base + (8 * cycle) + random.gauss(0, 1.0)
    return round(max(30.0, min(95.0, value)), 2)

def simulate_lux(day_max: float = 800.0) -> float:
    """
    Lux follows a bell curve during daylight hours (06:00-20:00).
    Zero at night. Sharp sunrise/sunset transitions.
    """
    h = get_hour_fraction()
    if h < 6.0 or h > 20.0:
        return 0.0
    
    # Bell curve centered at 13:00
    peak_hour = 13.0
    width = 4.5
    cycle = math.exp(-((h - peak_hour)**2) / (2 * width**2))
    value = (day_max * cycle) + random.gauss(0, 15.0)
    return round(max(0.0, value), 2)

def simulate_nh3(device_state: dict) -> float:
    """
    NH3 drifts slowly upward (accumulation) with occasional drops (ventilation event).
    Healthy range: 5-25 ppm. Warning: 25-50 ppm. Danger: >50 ppm.
    """
    current = device_state.get('nh3', 12.0)
    
    # 5% chance of ventilation event -> NH3 drops sharply
    if random.random() < 0.05:
        current = max(5.0, current - random.uniform(5.0, 15.0))
        device_state['nh3'] = current
        return round(current, 2)
    
    # Normal slow drift upward + noise
    drift = random.gauss(0.15, 0.1)  # average +0.15 ppm per reading
    current = current + drift + random.gauss(0, 0.5)
    current = max(3.0, min(80.0, current))
    device_state['nh3'] = current
    return round(current, 2)


class GatewaySimulator:
    def __init__(self, device_id: str, interval: int = 60):
        self.device_id = device_id
        self.interval = interval
        self.seq = 0
        self.state = {
            'nh3': random.uniform(8.0, 18.0) # each device starts at different NH3
        }
        self.client = None
        self.connected = False
        self.topic = TOPIC_TMPL.format(
            org_id=ORG_ID, farm_id=FARM_ID, device_id=device_id
        )

    def build_payload(self, is_buffered: bool = False, override_ts: int = None) -> dict:
        self.seq += 1
        return {
            "schema_version": "1.0",
            "org_id": ORG_ID,
            "farm_id": FARM_ID,
            "device_id": self.device_id,
            "sent_ts": override_ts or int(time.time() * 1000),
            "seq": self.seq,
            "is_buffered": is_buffered,
            "readings": {
                "temperature": simulate_temperature(),
                "humidity": simulate_humidity(),
                "lux": simulate_lux(),
                "nh3": simulate_nh3(self.state),
            }
        }

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.connected = True
            print(f"[{self.device_id}] Connected to EMQX at {MQTT_HOST}:{MQTT_PORT}")
        else:
            print(f"[{self.device_id}] Connection failed: {reason_code}")

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False
        if reason_code != 0:
            print(f"[{self.device_id}] Disconnected unexpectedly (code {reason_code}). Reconnecting...")

    def on_publish(self, client, userdata, mid, reason_codes, properties):
        print(f"[{self.device_id}] ✅ Published (mid={mid}, seq={self.seq})")

    def connect(self):
        # Build MQTT client (paho-mqtt v2 API)
        client_id = f"farmpulse-sim-{self.device_id}"
        self.client = mqtt.Client(
            client_id=client_id,
            protocol=mqtt.MQTTv5,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        
        # non-blocking, runs network loop in background thread
        self.client.loop_start() 

        # Wait for connection
        timeout = 10
        while not self.connected and timeout > 0:
            time.sleep(0.5)
            timeout -= 0.5
        
        if not self.connected:
            raise ConnectionError(f"[{self.device_id}] Could not connect to EMQX")

    def publish_once(self):
        payload = self.build_payload()
        self.client.publish(self.topic, json.dumps(payload), qos=1)
        print(f"[{self.device_id}] 📡 Sending: temp={payload['readings']['temperature']}°C "
              f"hum={payload['readings']['humidity']}% lux={payload['readings']['lux']} "
              f"nh3={payload['readings']['nh3']}ppm")

    def run_continuous(self):
        """Publish every `interval` seconds forever."""
        print(f"[{self.device_id}] 🚀 Starting — publishing every {self.interval}s")
        while True:
            try:
                self.publish_once()
            except Exception as e:
                print(f"[{self.device_id}] Publish error: {e}")
            time.sleep(self.interval)

    def replay_buffer(self, buffer_file: str):
        """
        Load a JSON buffer file and replay all entries with `is_buffered=True`.
        The original `sent_ts` is preserved — this is what triggers the buffered
        data routing fork in Sprint 3.
        """
        path = Path(buffer_file)
        if not path.exists():
            print(f"[{self.device_id}] Buffer file not found: {buffer_file}")
            sys.exit(1)
            
        with open(path) as f:
            entries = json.load(f)
            
        print(f"[{self.device_id}] Replaying {len(entries)} buffered entries from {buffer_file}")
        
        for entry in entries:
            payload = self.build_payload(
                is_buffered=True, 
                override_ts=entry.get('sent_ts', int(time.time() * 1000))
            )
            
            # Override readings with stored values if present
            if 'readings' in entry:
                payload['readings'] = entry['readings']
                
            self.client.publish(self.topic, json.dumps(payload), qos=1)
            print(f"[{self.device_id}] Replayed entry ts={payload['sent_ts']}")
            time.sleep(0.2) # small delay between replayed messages
            
        print(f"[{self.device_id}] Replay complete")

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


def run_device(device_id: str, interval: int):
    """Thread target for multi-device mode."""
    sim = GatewaySimulator(device_id=device_id, interval=interval)
    sim.connect()
    sim.run_continuous()


def main():
    parser = argparse.ArgumentParser(description="FarmPulse Gateway Simulator")
    parser.add_argument("--devices", type=int, default=1, help="Number of concurrent gateways")
    parser.add_argument("--interval", type=int, default=60, help="Publish interval in seconds")
    parser.add_argument("--replay", type=str, default=None, help="Path to JSON buffer file to replay")
    parser.add_argument("--device-id", type=str, default=None, help="Specific device ID (single device mode)")
    
    args = parser.parse_args()
    
    if args.replay:
        # Replay mode (single device, send buffered messages)
        # UPDATED: default to gw-lora-001
        device_id = args.device_id or "gw-lora-001"
        sim = GatewaySimulator(device_id=device_id, interval=args.interval)
        sim.connect()
        sim.replay_buffer(args.replay)
        sim.disconnect()
        return

    if args.devices == 1:
        # Single device run in main thread
        # UPDATED: default to gw-lora-001
        device_id = args.device_id or "gw-lora-001"
        sim = GatewaySimulator(device_id=device_id, interval=args.interval)
        sim.connect()
        sim.run_continuous()
    else:
        # Multi-device (each runs in its own thread)
        threads = []
        for i in range(1, args.devices + 1):
            # UPDATED: generates gw-lora-001, gw-lora-002, etc
            device_id = f"gw-lora-{i:03d}"
            t = threading.Thread(
                target=run_device, 
                args=(device_id, args.interval),
                daemon=True,
                name=f"sim-{device_id}"
            )
            threads.append(t)
            t.start()
            time.sleep(0.5) # stagger connections slightly
            
        print(f"✅ {args.devices} gateway simulators running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nSimulator stopped.")

if __name__ == "__main__":
    main()