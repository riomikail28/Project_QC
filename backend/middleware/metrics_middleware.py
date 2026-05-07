"""Prometheus metrics middleware for Flask."""
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from time import time
from flask import Blueprint, request, Response, g

REQUEST_COUNT = Counter(
    'qc_http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram('qc_http_request_latency_seconds', 'HTTP request latency', ['endpoint'])

metrics_bp = Blueprint('metrics_bp', __name__)


@metrics_bp.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


def init_metrics(app):
    @app.before_request
    def _before():
        g._start_time = time()

    @app.after_request
    def _after(response):
        try:
            endpoint = request.endpoint or 'unknown'
            status = str(response.status_code)
            REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, http_status=status).inc()
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(time() - getattr(g, '_start_time', time()))
        except Exception:
            pass
        return response
