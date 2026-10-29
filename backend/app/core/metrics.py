import time
from typing import Dict, Any

class SystemMetricsCollector:
    """
    Lightweight, thread-safe in-memory metrics collector for observability.
    Tracks total requests, error rates, average latency, and estimated token usage.
    """
    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.total_errors = 0
        self.total_latency_ms = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def record_request(self, duration_ms: float, is_error: bool = False):
        self.total_requests += 1
        self.total_latency_ms += duration_ms
        if is_error:
            self.total_errors += 1

    def record_tokens(self, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def get_summary(self) -> Dict[str, Any]:
        uptime_seconds = int(time.time() - self.start_time)
        avg_latency = (self.total_latency_ms / self.total_requests) if self.total_requests > 0 else 0.0
        error_rate = (self.total_errors / self.total_requests * 100) if self.total_requests > 0 else 0.0

        # Estimated cost calculation: Gemini Flash Lite estimated at $0.075 / 1M input, $0.30 / 1M output
        est_input_cost = (self.total_input_tokens / 1_000_000) * 0.075
        est_output_cost = (self.total_output_tokens / 1_000_000) * 0.30
        total_cost = est_input_cost + est_output_cost

        return {
            "uptime_seconds": uptime_seconds,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate_percent": round(error_rate, 2),
            "average_latency_ms": round(avg_latency, 1),
            "tokens": {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "total_tokens": self.total_input_tokens + self.total_output_tokens
            },
            "estimated_cost_usd": round(total_cost, 6)
        }

metrics_collector = SystemMetricsCollector()

