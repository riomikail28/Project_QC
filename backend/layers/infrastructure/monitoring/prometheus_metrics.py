"""
Prometheus Metrics Collection - Enterprise Monitoring
=================================================
Comprehensive metrics collection for QC Central Kitchen system.
Implements business and system metrics with proper labeling
and cardinality management following Prometheus best practices.

Metrics Categories:
- Business Metrics: QC operations, compliance rates, batch status
- Performance Metrics: Response times, throughput, error rates
- System Metrics: Database connections, memory usage, CPU
- Security Metrics: Authentication events, rate limits, security violations
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps
from prometheus_client import (
    Counter, Histogram, Gauge, Info, CollectorRegistry,
    CONTENT_TYPE_LATEST, generate_latest, CollectorRegistry,
    MetricWrapperBase
)
from flask import Flask, Response, g, request
import redis
import psutil

logger = logging.getLogger("qc.monitoring.metrics")

class QCMetricsConfig:
    """Configuration for QC metrics collection"""
    
    def __init__(
        self,
        enabled: bool = True,
        registry: Optional[CollectorRegistry] = None,
        default_labels: Optional[Dict[str, str]] = None,
        label_cardinality_limits: Optional[Dict[str, int]] = None
    ):
        self.enabled = enabled
        self.registry = registry or CollectorRegistry()
        self.default_labels = default_labels or {}
        self.label_cardinality_limits = label_cardinality_limits or {
            'facility_id': 100,
            'batch_id': 1000,
            'user_id': 500,
            'product_id': 200
        }

class BaseQCMetrics:
    """Base class for QC metrics with common functionality"""
    
    def __init__(self, config: QCMetricsConfig):
        self.config = config
        self.logger = logging.getLogger("qc.metrics.base")
    
    def _add_default_labels(self, labels: Dict[str, str]) -> Dict[str, str]:
        """Add default labels to metrics"""
        merged_labels = self.config.default_labels.copy()
        merged_labels.update(labels)
        return merged_labels
    
    def _validate_label_cardinality(self, metric_name: str, labels: Dict[str, str]):
        """Validate label cardinality to prevent high-cardinality metrics"""
        if metric_name not in self.config.label_cardinality_limits:
            return
        
        limit = self.config.label_cardinality_limits[metric_name]
        for label_name, label_value in labels.items():
            if label_name.endswith('_id') and len(label_value) > limit:
                self.logger.warning(
                    f"High cardinality label detected: {metric_name}.{label_name}={label_value}"
                )
                # Truncate or hash high-cardinality values
                labels[label_name] = label_value[:limit]

class BusinessMetrics(BaseQCMetrics):
    """QC business metrics for operations and compliance tracking"""
    
    def __init__(self, config: QCMetricsConfig):
        super().__init__(config)
        
        # QC Operations Counter
        self.qc_operations_total = Counter(
            'qc_operations_total',
            'Total QC operations performed',
            [
                'facility_id', 'operation_type', 'result', 'batch_id',
                'product_category', 'user_role', 'shift'
            ],
            registry=config.registry
        )
        
        # QC Results Counter
        self.qc_results_total = Counter(
            'qc_results_total',
            'QC test results distribution',
            ['facility_id', 'test_type', 'result', 'severity'],
            registry=config.registry
        )
        
        # Batch Processing Gauge
        self.active_batches = Gauge(
            'qc_active_batches_total',
            'Number of active QC batches in processing',
            ['facility_id', 'status', 'priority'],
            registry=config.registry
        )
        
        # Compliance Rate Gauge
        self.compliance_rate = Gauge(
            'qc_compliance_rate',
            'QC compliance rate (percentage)',
            ['facility_id', 'time_period', 'test_category'],
            registry=config.registry
        )
        
        # Retention Rate Gauge
        self.retention_rate = Gauge(
            'qc_retention_rate',
            'QC product retention rate (percentage)',
            ['facility_id', 'reason', 'time_period'],
            registry=config.registry
        )
        
        # Validation Time Histogram
        self.qc_validation_duration = Histogram(
            'qc_validation_duration_seconds',
            'Time spent on QC validation operations',
            ['facility_id', 'test_type', 'complexity'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=config.registry
        )
    
    def record_qc_operation(
        self,
        facility_id: str,
        operation_type: str,
        result: str,
        batch_id: Optional[str] = None,
        user_info: Optional[Dict[str, str]] = None
    ):
        """Record QC operation metric"""
        labels = self._add_default_labels({
            'facility_id': facility_id,
            'operation_type': operation_type,
            'result': result,
            'batch_id': batch_id or 'unknown',
            'product_category': 'unknown',  # Would come from batch data
            'user_role': user_info.get('role', 'unknown') if user_info else 'unknown',
            'shift': self._get_current_shift()
        })
        
        self._validate_label_cardinality('qc_operations_total', labels)
        self.qc_operations_total.labels(**labels).inc()
    
    def record_qc_result(
        self,
        facility_id: str,
        test_type: str,
        result: str,
        severity: str = 'normal'
    ):
        """Record QC test result"""
        labels = self._add_default_labels({
            'facility_id': facility_id,
            'test_type': test_type,
            'result': result,
            'severity': severity
        })
        
        self.qc_results_total.labels(**labels).inc()
    
    def update_active_batches(self, facility_id: str, count: int, status: str, priority: str = 'normal'):
        """Update active batches count"""
        labels = self._add_default_labels({
            'facility_id': facility_id,
            'status': status,
            'priority': priority
        })
        
        self.active_batches.labels(**labels).set(count)
    
    def update_compliance_rate(
        self,
        facility_id: str,
        rate: float,
        time_period: str = 'daily',
        test_category: str = 'all'
    ):
        """Update compliance rate"""
        labels = self._add_default_labels({
            'facility_id': facility_id,
            'time_period': time_period,
            'test_category': test_category
        })
        
        self.compliance_rate.labels(**labels).set(rate)
    
    def _get_current_shift(self) -> str:
        """Get current shift based on time"""
        hour = datetime.now().hour
        if 6 <= hour < 14:
            return 'morning'
        elif 14 <= hour < 22:
            return 'evening'
        else:
            return 'night'

class PerformanceMetrics(BaseQCMetrics):
    """System performance metrics for monitoring and alerting"""
    
    def __init__(self, config: QCMetricsConfig):
        super().__init__(config)
        
        # HTTP Request Counter
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests processed',
            ['method', 'endpoint', 'status_code', 'facility_id', 'user_anonymous'],
            registry=config.registry
        )
        
        # HTTP Request Duration Histogram
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'facility_id', 'user_anonymous'],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=config.registry
        )
        
        # Database Connection Pool Gauge
        self.database_connections = Gauge(
            'database_connections_active',
            'Number of active database connections',
            ['database_type', 'facility_id'],
            registry=config.registry
        )
        
        # Database Query Duration Histogram
        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query execution duration',
            ['operation_type', 'table_name', 'query_complexity'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
            registry=config.registry
        )
        
        # Cache Operations Counter
        self.cache_operations_total = Counter(
            'cache_operations_total',
            'Total cache operations performed',
            ['operation', 'cache_type', 'hit_status', 'facility_id'],
            registry=config.registry
        )
        
        # Error Rate Counter
        self.errors_total = Counter(
            'errors_total',
            'Total errors encountered',
            ['error_type', 'severity', 'component', 'facility_id'],
            registry=config.registry
        )
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        labels = self._add_default_labels({
            'method': method,
            'endpoint': self._sanitize_endpoint(endpoint),
            'status_code': str(status_code),
            'facility_id': getattr(g, 'facility_id', 'unknown'),
            'user_anonymous': str(getattr(g, 'user_anonymous', 'false'))
        })
        
        self.http_requests_total.labels(**labels).inc()
        self.http_request_duration.labels(**labels).observe(duration)
    
    def record_database_operation(
        self,
        operation_type: str,
        table_name: str,
        duration: float,
        complexity: str = 'simple'
    ):
        """Record database operation metrics"""
        labels = self._add_default_labels({
            'operation_type': operation_type,
            'table_name': table_name,
            'query_complexity': complexity
        })
        
        self.database_query_duration.labels(**labels).observe(duration)
    
    def record_cache_operation(
        self,
        operation: str,
        cache_type: str,
        hit_status: str
    ):
        """Record cache operation metrics"""
        labels = self._add_default_labels({
            'operation': operation,
            'cache_type': cache_type,
            'hit_status': hit_status,
            'facility_id': getattr(g, 'facility_id', 'unknown')
        })
        
        self.cache_operations_total.labels(**labels).inc()
    
    def record_error(
        self,
        error_type: str,
        severity: str,
        component: str
    ):
        """Record system error metrics"""
        labels = self._add_default_labels({
            'error_type': error_type,
            'severity': severity,
            'component': component,
            'facility_id': getattr(g, 'facility_id', 'unknown')
        })
        
        self.errors_total.labels(**labels).inc()
    
    def _sanitize_endpoint(self, endpoint: str) -> str:
        """Sanitize endpoint to prevent high cardinality"""
        # Replace dynamic path parameters with placeholders
        import re
        endpoint = re.sub(r'/[a-f0-9-]{8,36}', '/{id}', endpoint)
        endpoint = re.sub(r'/\d+', '/{number}', endpoint)
        endpoint = re.sub(r'/[^/]*@[^/]*', '/{email}', endpoint)
        return endpoint

class SecurityMetrics(BaseQCMetrics):
    """Security metrics for authentication and authorization events"""
    
    def __init__(self, config: QCMetricsConfig):
        super().__init__(config)
        
        # Authentication Events Counter
        self.auth_events_total = Counter(
            'authentication_events_total',
            'Total authentication events',
            ['event_type', 'result', 'auth_method', 'facility_id', 'client_ip'],
            registry=config.registry
        )
        
        # Authorization Events Counter
        self.authz_events_total = Counter(
            'authorization_events_total',
            'Total authorization events', 
            ['result', 'permission', 'resource', 'facility_id'],
            registry=config.registry
        )
        
        # Security Violations Counter
        self.security_violations_total = Counter(
            'security_violations_total',
            'Total security violations detected',
            ['violation_type', 'severity', 'source_ip', 'facility_id'],
            registry=config.registry
        )
        
        # Rate Limit Events Counter
        self.rate_limit_events_total = Counter(
            'rate_limit_events_total',
            'Total rate limit events',
            ['endpoint', 'limit_type', 'result', 'facility_id'],
            registry=config.registry
        )
        
        # Active Sessions Gauge
        self.active_sessions = Gauge(
            'active_sessions_total',
            'Number of active user sessions',
            ['session_type', 'facility_id'],
            registry=config.registry
        )
    
    def record_auth_event(
        self,
        event_type: str,
        result: str,
        auth_method: str,
        client_ip: Optional[str] = None
    ):
        """Record authentication event"""
        labels = self._add_default_labels({
            'event_type': event_type,
            'result': result,
            'auth_method': auth_method,
            'facility_id': getattr(g, 'facility_id', 'unknown'),
            'client_ip': client_ip or 'unknown'
        })
        
        self.auth_events_total.labels(**labels).inc()
    
    def record_authz_event(
        self,
        result: str,
        permission: str,
        resource: str
    ):
        """Record authorization event"""
        labels = self._add_default_labels({
            'result': result,
            'permission': permission,
            'resource': resource,
            'facility_id': getattr(g, 'facility_id', 'unknown')
        })
        
        self.authz_events_total.labels(**labels).inc()
    
    def record_security_violation(
        self,
        violation_type: str,
        severity: str,
        source_ip: Optional[str] = None
    ):
        """Record security violation"""
        labels = self._add_default_labels({
            'violation_type': violation_type,
            'severity': severity,
            'source_ip': source_ip or 'unknown',
            'facility_id': getattr(g, 'facility_id', 'unknown')
        })
        
        self.security_violations_total.labels(**labels).inc()
    
    def update_active_sessions(self, session_type: str, count: int):
        """Update active sessions count"""
        labels = self._add_default_labels({
            'session_type': session_type,
            'facility_id': getattr(g, 'facility_id', 'unknown')
        })
        
        self.active_sessions.labels(**labels).set(count)

class SystemMetrics(BaseQCMetrics):
    """System resource monitoring metrics"""
    
    def __init__(self, config: QCMetricsConfig):
        super().__init__(config)
        
        # CPU Usage Gauge
        self.cpu_usage_percent = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            ['metric_type', 'facility_id'],
            registry=config.registry
        )
        
        # Memory Usage Gauge
        self.memory_usage_bytes = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['memory_type', 'facility_id'],
            registry=config.registry
        )
        
        # Disk Usage Gauge
        self.disk_usage_bytes = Gauge(
            'disk_usage_bytes',
            'Disk usage in bytes',
            ['mount_point', 'disk_type', 'facility_id'],
            registry=config.registry
        )
        
        # Network I/O Counter
        self.network_io_bytes = Counter(
            'network_io_bytes_total',
            'Total network I/O bytes',
            ['direction', 'interface', 'facility_id'],
            registry=config.registry
        )
        
        # Process Metrics Gauge
        self.process_count = Gauge(
            'process_count_total',
            'Number of processes',
            ['process_type', 'facility_id'],
            registry=config.registry
        )
    
    def update_cpu_metrics(self, facility_id: str):
        """Update CPU usage metrics"""
        cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
        
        labels = self._add_default_labels({
            'metric_type': 'total',
            'facility_id': facility_id
        })
        
        self.cpu_usage_percent.labels(**labels).set(cpu_percent)
    
    def update_memory_metrics(self, facility_id: str):
        """Update memory usage metrics"""
        memory = psutil.virtual_memory()
        
        labels = self._add_default_labels({
            'facility_id': facility_id
        })
        
        self.memory_usage_bytes.labels(
            memory_type='used', **labels
        ).set(memory.used)
        
        self.memory_usage_bytes.labels(
            memory_type='available', **labels
        ).set(memory.available)
    
    def update_disk_metrics(self, facility_id: str):
        """Update disk usage metrics"""
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                labels = self._add_default_labels({
                    'mount_point': partition.mountpoint,
                    'disk_type': partition.fstype,
                    'facility_id': facility_id
                })
                
                self.disk_usage_bytes.labels(**labels).set(usage.used)
                
            except PermissionError:
                continue

class PrometheusMetricsCollector:
    """Main metrics collector orchestrating all metric types"""
    
    def __init__(self, config: QCMetricsConfig):
        self.config = config
        self.logger = logging.getLogger("qc.metrics.collector")
        
        # Initialize metric collectors
        self.business_metrics = BusinessMetrics(config)
        self.performance_metrics = PerformanceMetrics(config)
        self.security_metrics = SecurityMetrics(config)
        self.system_metrics = SystemMetrics(config)
        
        # Collection state
        self.is_collecting = False
        self.last_collection_time = None
    
    def collect_system_metrics(self, facility_id: str = 'global'):
        """Collect system resource metrics"""
        try:
            self.system_metrics.update_cpu_metrics(facility_id)
            self.system_metrics.update_memory_metrics(facility_id)
            self.system_metrics.update_disk_metrics(facility_id)
            
            self.last_collection_time = time.time()
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def start_continuous_collection(self, interval: int = 30, facility_id: str = 'global'):
        """Start continuous metrics collection (placeholder for background task)"""
        # This would be implemented with a background scheduler
        pass

class MetricsMiddleware:
    """Flask middleware for automatic metrics collection"""
    
    def __init__(self, app: Flask, collector: PrometheusMetricsCollector):
        self.app = app
        self.collector = collector
        self.logger = logging.getLogger("qc.metrics.middleware")
        
        self._register_middleware()
    
    def _register_middleware(self):
        """Register Flask middleware hooks"""
        
        @self.app.before_request
        def before_request():
            g.start_time = time.time()
            g.facility_id = self._extract_facility_id()
            g.user_anonymous = not self._is_authenticated()
        
        @self.app.after_request
        def after_request(response):
            if not self.collector.config.enabled:
                return response
            
            # Record request metrics
            duration = time.time() - g.start_time
            self.collector.performance_metrics.record_http_request(
                request.method,
                request.endpoint or 'unknown',
                response.status_code,
                duration
            )
            
            # Record security metrics for certain endpoints
            if '/login' in request.endpoint or '/auth' in request.endpoint:
                result = 'success' if response.status_code < 400 else 'failure'
                self.collector.security_metrics.record_auth_event(
                    'login', result, 'password', request.remote_addr
                )
            
            return response
        
        @self.app.route('/metrics')
        def metrics_endpoint():
            if not self.collector.config.enabled:
                return "Metrics disabled", 404
            
            # Collect latest system metrics
            self.collector.collect_system_metrics()
            
            # Generate metrics response
            metrics_data = generate_latest(self.collector.config.registry)
            return Response(
                metrics_data,
                mimetype=CONTENT_TYPE_LATEST
            )
    
    def _extract_facility_id(self) -> str:
        """Extract facility ID from request context"""
        # Try to get from JWT token, headers, or session
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # This would decode JWT and extract facility_id
            pass
        return getattr(g, 'facility_id', 'unknown')
    
    def _is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        # This would check JWT token or session
        return getattr(g, 'user_id', None) is not None

# Utility decorators for automatic instrumentation
def track_metric(operation_type: str, table_name: str = None):
    """Decorator to automatically track database operation metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record successful operation
                complexity = 'complex' if kwargs.get('filters') else 'simple'
                collector = get_global_metrics_collector()
                if collector:
                    collector.performance_metrics.record_database_operation(
                        operation_type, table_name or 'unknown', duration, complexity
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Record error
                collector = get_global_metrics_collector()
                if collector:
                    collector.performance_metrics.record_error(
                        'database_error', 'high', 'database_layer'
                    )
                    collector.performance_metrics.record_database_operation(
                        operation_type, table_name or 'unknown', duration, 'failed'
                    )
                
                raise
        
        return wrapper
    return decorator

def get_global_metrics_collector() -> Optional[PrometheusMetricsCollector]:
    """Get global metrics collector instance"""
    # This would be implemented with application context or dependency injection
    return None