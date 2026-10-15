from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "inference_requests_total", "Total inference requests received", ["model", "status"]
)
REQUEST_LATENCY = Histogram(
    "inference_latency_seconds", "End-to-end inference latency in seconds", ["model"]
)
INFERENCE_ERRORS = Counter(
    "inference_errors_total", "Total inference errors", ["model", "error_type"]
)
HTTP_REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests to the gateway", ["method", "path", "status_code"]
)
