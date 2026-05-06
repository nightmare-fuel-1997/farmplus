# scripts/test_publish.py
import json, time
import paho.mqtt.client as mqtt

PAYLOAD = {
    "schema_version": "1.0",
    "org_id":    "org_sunrise",
    "farm_id":   "farm_01",
    "device_id": "gw_lora_001",
    "sent_ts":   int(time.time() * 1000),
    "seq":       1,
    "is_buffered": False,
    "readings": {
        "temperature": 24.7,
        "humidity":    63.2,
        "lux":         320.0,
        "nh3":         12.5
    }
}

client = mqtt.Client(
    client_id="test-publisher",
    protocol=mqtt.MQTTv5,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
)
client.connect("localhost", 1884)
client.publish(
    topic="org_sunrise/farms/farm_01/gateways/gw_lora_001/telemetry",
    payload=json.dumps(PAYLOAD),
    qos=1,
)
client.disconnect()
print("✅ Published test message to EMQX")