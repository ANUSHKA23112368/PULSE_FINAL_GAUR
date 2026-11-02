"""
Tests for Telemetry Monitor.
"""

from backend.api.telemetry_monitor import TelemetryMonitor

def test_telemetry_monitor():
    m = TelemetryMonitor()
    res = m.record_run(0.025)
    assert res["calls"] == 1
    assert res["last_latency_ms"] == 25.0
    res2 = m.record_run(0.035)
    assert res2["calls"] == 2
    assert res2["avg_latency_ms"] == 30.0
