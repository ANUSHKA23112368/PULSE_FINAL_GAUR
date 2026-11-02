"""
Lightweight In-Memory Telemetry and Latency Monitor for Inference Pipeline.
"""

import time
from typing import Dict, Any

class TelemetryMonitor:
    def __init__(self):
        self.call_count = 0
        self.total_latency_ms = 0.0

    def record_run(self, duration_sec: float) -> Dict[str, Any]:
        self.call_count += 1
        ms = duration_sec * 1000.0
        self.total_latency_ms += ms
        return {
            "calls": self.call_count,
            "last_latency_ms": round(ms, 2),
            "avg_latency_ms": round(self.total_latency_ms / self.call_count, 2)
        }

monitor = TelemetryMonitor()
