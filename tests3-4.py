from apps.telemetry.pipeline import _check_clock_drift
from apps.telemetry.pipeline import _check_clock_drift, BUFFERED_CUTOFF_MS
now = 1778326304000  # fake "now" in ms

# Test 1 — fresh live data (drift ~2 seconds, normal)
drift, old = _check_clock_drift("t001", {"sent_ts": now - 2000, "device_id": "gw-lora-001"}, now)
print(f"✓ Test 1 | drift={drift:+,}ms | is_old_buffered={old}")
assert drift == 2000 and old == False

# Test 2 — 4-hour-old buffered data (should flag as old_buffered)
drift, old = _check_clock_drift("t002", {"sent_ts": now - (4 * 3600 * 1000), "device_id": "gw-lora-001"}, now)
print(f"✓ Test 2 | drift={drift:+,}ms | is_old_buffered={old}")
assert old == True

# Test 3 — device clock running 10 minutes ahead (negative drift, warning logged)
drift, old = _check_clock_drift("t003", {"sent_ts": now + (10 * 60 * 1000), "device_id": "gw-lora-001"}, now)
print(f"✓ Test 3 | drift={drift:+,}ms | is_old_buffered={old}")
assert drift < 0 and old == False

# Test 4 — exactly at the 15-minute cutoff boundary
drift, old = _check_clock_drift("t004", {"sent_ts": now - BUFFERED_CUTOFF_MS, "device_id": "gw-lora-001"}, now)
print(f"✓ Test 4 | drift={drift:+,}ms | is_old_buffered={old}")