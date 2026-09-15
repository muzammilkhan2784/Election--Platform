"""
Prometheus metrics for the web application.

Gunicorn runs several worker processes and Prometheus scrapes a single
endpoint, so each worker writing its own in-memory counters would report
whichever worker happened to answer. prometheus_client solves this with a
shared directory of memory-mapped files that every worker appends to; the
/metrics endpoint then aggregates across all of them.

PROMETHEUS_MULTIPROC_DIR must be set and writable, which docker-compose does.
When it is unset (running run.py directly) the library falls back to ordinary
single-process collection.
"""
import os
import time

from flask import Response, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)

REQUEST_COUNT = Counter(
    "election_http_requests_total",
    "HTTP requests handled",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "election_http_request_duration_seconds",
    "Time spent handling a request",
    ["method", "endpoint"],
    # Tuned to this app: most reads are single-digit ms, a vote is ~20ms, and
    # anything past 1s means the worker pool is saturated.
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

VOTES_SUBMITTED = Counter(
    "election_votes_submitted_total",
    "Ballots accepted by the API",
)


def _endpoint_label():
    """
    Use the Flask rule ('/api/elections/<int:election_id>/results') rather than
    the raw path, so 2,000 elections do not become 2,000 separate time series.
    """
    if request.url_rule:
        return request.url_rule.rule
    return "<unmatched>"


def init_metrics(app):
    @app.before_request
    def _start_timer():
        request._metrics_start = time.perf_counter()

    @app.after_request
    def _record(response):
        started = getattr(request, "_metrics_start", None)
        if started is not None:
            endpoint = _endpoint_label()
            REQUEST_LATENCY.labels(request.method, endpoint).observe(
                time.perf_counter() - started
            )
            REQUEST_COUNT.labels(
                request.method, endpoint, str(response.status_code)
            ).inc()
            if (
                endpoint.endswith("/vote")
                and request.method == "POST"
                and response.status_code == 200
            ):
                VOTES_SUBMITTED.inc()
        return response

    @app.route("/metrics")
    def metrics():
        if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
            payload = generate_latest(registry)
        else:
            payload = generate_latest()
        return Response(payload, mimetype=CONTENT_TYPE_LATEST)

    return app
