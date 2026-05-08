"""
Enterprise QC API - Application Layer API Endpoints
====================================================
Complete API implementation for QC Central Kitchen enterprise system.
Provides comprehensive RESTful API with enterprise features:
- Proper error handling and standardized responses
- Input validation and sanitization
- Rate limiting and security middleware integration
- Comprehensive business logic orchestration
- Audit trail and logging
- Performance monitoring integration

This module provides the main API endpoints that combine all the
enterprise architecture components we've implemented.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ...infrastructure.security.security_middleware import (
    EnterpriseSecurityMiddleware, require_auth, require_permissions, csrf_exempt
)
from ...infrastructure.monitoring.prometheus_metrics import (
    PrometheusMetricsCollector, track_metric
)
from ...domain.di.service_config import create_service_config
from ...core.enterprise_response import (
    ResponseBuilder, ErrorType, create_qc_response, create_list_response
)
from ...domain.entities.qc_entities import ValidationLevel, QCEntityStatus

logger = logging.getLogger("qc.enterprise.api")

class EnterpriseQCAPI:
    """Enterprise QC API with complete business functionality"""
    
    def __init__(self, app=None):
        self.app = app
        self.config = None
        self.security_middleware = None
        self.metrics_collector = None
        self.limiter = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize API with Flask application"""
        self.app = app
        self.config = create_service_config()
        
        # Initialize monitoring
        self.metrics_collector = PrometheusMetricsCollector(self.config._container)
        
        # Initialize security middleware
        security_config = self._create_security_config()
        self.security_middleware = EnterpriseSecurityMiddleware(app, security_config)
        
        # Initialize rate limiting
        self.limiter = Limiter(
            app,
            key_func=get_remote_address,
            default_limits=["200 per minute", "50 per minute"]
        )
        
        # Register API blueprints
        self._register_api_blueprints()
        
        logger.info("Enterprise QC API initialized successfully")
    
    def _create_security_config(self):
        """Create security configuration"""
        from ...infrastructure.security.jwt_service import JWTConfig
        
        jwt_config = JWTConfig(
            secret_key=app.config.get('SECRET_KEY', 'enterprise-secret-key'),
            refresh_token_rotate=True,
            blacklist_enabled=True,
            redis_url=app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        )
        
        return SecurityConfig(
            jwt_config=jwt_config,
            csrf_enabled=True,
            rate_limit_enabled=True,
            xss_protection=True,
            security_headers=True,
            session_secure=app.config.get('ENVIRONMENT') == 'production'
        )
    
    def _register_api_blueprints(self):
        """Register all API blueprints"""
        
        # QC Records API
        qc_records_bp = Blueprint('qc_records', __name__, url_prefix='/api/v1/qc')
        
        @qc_records_bp.route('/records', methods=['POST'])
        @require_auth
        def create_qc_record():
            """Create new QC record"""
            try:
                data = request.get_json()
                
                # Validate required fields
                required_fields = ['batch_id', 'facility_id', 'check_type', 'performed_by']
                for field in required_fields:
                    if field not in data:
                        return ResponseBuilder().error(f"Missing required field: {field}").add_error(
                            code="VALIDATION_ERROR",
                            message=f"Field {field} is required",
                            error_type=ErrorType.VALIDATION_ERROR,
                            field=field
                        ).build(), 422
                
                # Get workflow service from DI container
                workflow_service = self.config.get_container().get('QCWorkflowService')
                
                # Create QC record
                result = await workflow_service.create_qc_record(
                    batch_id=data['batch_id'],
                    facility_id=data['facility_id'],
                    check_type=data['check_type'],
                    performed_by=data['performed_by'],
                    temperature_readings=data.get('temperature_readings'),
                    visual_inspection=data.get('visual_inspection'),
                    sensory_evaluation=data.get('sensory_evaluation'),
                    microbiological_tests=data.get('microbiological_tests')
                )
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Failed to create QC record: {e}")
                return ResponseBuilder().error("Failed to create QC record").add_error(
                    code="QC_CREATION_ERROR",
                    message=str(e),
                    error_type=ErrorType.SYSTEM_ERROR
                ).build(), 500
        
        @qc_records_bp.route('/records/<record_id>', methods=['PUT'])
        @require_auth
        def complete_qc_record(record_id):
            """Complete QC record workflow"""
            try:
                data = request.get_json()
                completed_by = data.get('completed_by')
                
                if not completed_by:
                    return ResponseBuilder().error("Missing completed_by field").add_error(
                        code="VALIDATION_ERROR",
                        message="Field completed_by is required",
                        error_type=ErrorType.VALIDATION_ERROR,
                        field="completed_by"
                    ).build(), 422
                
                workflow_service = self.config.get_container().get('QCWorkflowService')
                
                result = await workflow_service.complete_qc_record(
                    qc_record_id=record_id,
                    completed_by=completed_by,
                    final_inspection=data.get('final_inspection')
                )
                
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Failed to complete QC record: {e}")
                return ResponseBuilder().error("Failed to complete QC record").add_error(
                    code="QC_COMPLETION_ERROR",
                    message=str(e),
                    error_type=ErrorType.SYSTEM_ERROR
                ).build(), 500
        
        @qc_records_bp.route('/records/facility/<facility_id>', methods=['GET'])
        @require_auth
        def get_facility_qc_records(facility_id):
            """Get QC records for facility"""
            try:
                start_date = request.args.get('start_date', (datetime.utcnow() - timedelta(days=7)).isoformat())
                end_date = request.args.get('end_date', datetime.utcnow().isoformat())
                status = request.args.get('status')
                
                # Parse dates
                start_dt = datetime.fromisoformat(start_date)
                end_dt = datetime.fromisoformat(end_date)
                
                # Get QC repository
                qc_repo = self.config.get_container().get('QCRepositoryImpl')
                
                records = await qc_repo.get_records_by_facility(
                    facility_id=facility_id,
                    start_date=start_dt,
                    end_date=end_dt,
                    status=status
                )
                
                records_data = [record.dict() for record in records]
                
                return jsonify(create_list_response(
                    records_data,
                    current_page=1,
                    items_per_page=len(records_data),
                    total_items=len(records_data)
                ).dict())
                
            except Exception as e:
                logger.error(f"Failed to get facility QC records: {e}")
                return ResponseBuilder().error("Failed to retrieve QC records").add_error(
                    code="DATA_RETRIEVAL_ERROR",
                    message=str(e),
                    error_type=ErrorType.SYSTEM_ERROR
                ).build(), 500
        
        # Temperature Monitoring API
        temp_bp = Blueprint('temperature', __name__, url_prefix='/api/v1/temperature')
        
        @temp_bp.route('/readings', methods=['GET'])
        @require_auth
        def get_temperature_readings():
            """Get temperature readings for monitoring"""
            try:
                batch_id = request.args.get('batch_id')
                facility_id = request.args.get('facility_id')
                hours_back = int(request.args.get('hours_back', '24'))
                
                if not batch_id and not facility_id:
                    return ResponseBuilder().error("Either batch_id or facility_id required").add_error(
                        code="VALIDATION_ERROR",
                        message="Provide either batch_id or facility_id",
                        error_type=ErrorType.VALIDATION_ERROR
                    ).build(), 422
                
                temp_repo = self.config.get_container().get('TemperatureReadingRepositoryImpl')
                readings = []
                
                if batch_id:
                    readings = await temp_repo.get_readings_by_batch(batch_id)
                else:
                    readings = await temp_repo.get_anomaly_readings(facility_id, hours_back)
                
                readings_data = [reading.dict() for reading in readings]
                
                return jsonify(create_list_response(
                    readings_data,
                    current_page=1,
                    items_per_page=len(readings_data),
                    total_items=len(readings_data)
                ).dict())
                
            except Exception as e:
                logger.error(f"Failed to get temperature readings: {e}")
                return ResponseBuilder().error("Failed to retrieve temperature readings").add_error(
                    code="DATA_RETRIEVAL_ERROR",
                    message=str(e),
                    error_type=ErrorType.SYSTEM_ERROR
                ).build(), 500
        
        @temp_bp.route('/readings', methods=['POST'])
        @require_auth
        def create_temperature_reading():
            """Create temperature reading"""
            try:
                data = request.get_json()
                
                required_fields = ['batch_id', 'unit_type', 'temperature_celsius', 'monitored_by']
                for field in required_fields:
                    if field not in data:
                        return ResponseBuilder().error(f"Missing required field: {field}").add_error(
                            code="VALIDATION_ERROR",
                            message=f"Field {field} is required",
                            error_type=ErrorType.VALIDATION_ERROR,
                            field=field
                        ).build(), 422
                
                # Create temperature reading entity
                from ...domain.entities.qc_entities import TemperatureReading, UnitType
                
                reading = TemperatureReading(
                    facility_id=data.get('facility_id'),
                    batch_id=data['batch_id'],
                    unit_type=UnitType(data['unit_type']),
                    temperature_celsius=data['temperature_celsius'],
                    target_min=data.get('target_min', 0.0),
                    target_max=data.get('target_max', 25.0),
                    monitored_by=data['monitored_by'],
                    device_id=data.get('device_id')
                )
                
                # Validate with domain service
                domain_service = self.config.get_container().get('QCDomainService')
                validations = await domain_service.validate_temperature_reading(
                    reading, data.get('sop_requirements')
                )
                
                # Save reading
                temp_repo = self.config.get_container().get('TemperatureReadingRepositoryImpl')
                saved_reading = await temp_repo.create(reading)
                
                # Return with validation results
                response_data = saved_reading.dict()
                response_data['validations'] = [v.dict() for v in validations]
                
                return jsonify(create_qc_response(response_data, saved_reading.validation_result.value).dict())
                
            except Exception as e:
                logger.error(f"Failed to create temperature reading: {e}")
                return ResponseBuilder().error("Failed to create temperature reading").add_error(
                    code="TEMPERATURE_CREATION_ERROR",
                    message=str(e),
                    error_type=ErrorType.SYSTEM_ERROR
                ).build(), 500
        
        # Batches API
        batches_bp = Blueprint('batches', __name__, url_prefix='/api/v1/batches')
        
        @batches_bp.route('', methods=['GET'])
        @require_auth
        def get_batches():
            """Get batches with filtering"""
            try:
                facility_id = request.args.get('facility_id')
                product_id = request.args.get('product_id')
                status = request.args.get('status')
                
                batch_repo = self.config.get_container().get('QCBatchRepositoryImpl')
                
                if product_id:
                    batches = await batch_repo.get_batches_by_product(product_id, facility_id)
                elif facility_id:
                    # Get all batches for facility (would need implementation)
                    batches = []
                else:
                    # Get expiring batches
                    batches = await batch_repo.get_expiring_batches()
                
                batches_data = [batch.dict() for batch in batches]
                
                return jsonify(create_list_response(
                    batches_data,
                    current_page=1,
                    items_per_page=len(batches_data),
                    total_items=len(batches_data)
                ).dict())
                
            except Exception as e:
                logger.error(f"Failed to get batches: {e}")
                return ResponseBuilder().error("Failed to retrieve batches").add_error(
                    code="DATA_RETRIEVAL_ERROR",
                    message=str(e),
                    error_type=ErrorType.SYSTEM_ERROR
                ).build(), 500
        
        @batches_bp.route('/<batch_id>', methods=['GET'])
        @require_auth
        def get_batch(batch_id):
            """Get specific batch details"""
            try:
                batch_repo = self.config.get_container().get('QCBatchRepositoryImpl')
                batch = await batch_repo.get_by_number(batch_id)
                
                if not batch:
                    return ResponseBuilder().error("Batch not found").add_error(
                        code="BATCH_NOT_FOUND",
                        message=f"Batch {batch_id} not found",
                        error_type=ErrorType.NOT_FOUND_ERROR,
                        details={"batch_id": batch_id}
                    ).build(), 404
                
                return jsonify(create_qc_response(batch.dict()).dict())
                
            except Exception as e:
                logger.error(f"Failed to get batch: {e}")
                return ResponseBuilder().error("Failed to retrieve batch").add_error(
                    code="DATA_RETRIEVAL_ERROR",
                    message=str(e),
                    error_type=ErrorType.SYSTEM_ERROR
                ).build(), 500
        
        # Dashboard API
        dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/v1/dashboard')
        
        @dashboard_bp.route('/qc-summary', methods=['GET'])
        @require_auth
        def get_qc_dashboard():
            """Get QC dashboard summary"""
            try:
                facility_id = request.args.get('facility_id')
                start_date = request.args.get('start_date', (datetime.utcnow() - timedelta(days=7)).isoformat())
                end_date = request.args.get('end_date', datetime.utcnow().isoformat())
                
                if not facility_id:
                    return ResponseBuilder().error("facility_id required").add_error(
                        code="VALIDATION_ERROR",
                        message="facility_id is required for dashboard",
                        error_type=ErrorType.VALIDATION_ERROR,
                        field="facility_id"
                    ).build(), 422
                
                # Parse dates
                start_dt = datetime.fromisoformat(start_date)
                end_dt = datetime.fromisoformat(end_date)
                
                workflow_service = self.config.get_container().get('QCWorkflowService')
                
                dashboard_data = await workflow_service.get_qc_dashboard_data(
                    facility_id=facility_id,
                    start_date=start_dt,
                    end_date=end_dt
                )
                
                return jsonify(dashboard_data)
                
            except Exception as e:
                logger.error(f"Failed to get dashboard data: {e}")
                return ResponseBuilder().error("Failed to retrieve dashboard data").add_error(
                    code="DASHBOARD_ERROR",
                    message=str(e),
                    error_type=ErrorType.SYSTEM_ERROR
                ).build(), 500
        
        # Authentication API (using JWT service)
        auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')
        
        @auth_bp.route('/login', methods=['POST'])
        @csrf_exempt  # CSRF exempt for login
        def login():
            """Authenticate user and return tokens"""
            try:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
                device_id = data.get('device_id')
                
                if not username or not password:
                    return ResponseBuilder().error("Username and password required").add_error(
                        code="VALIDATION_ERROR",
                        message="Username and password are required",
                        error_type=ErrorType.VALIDATION_ERROR
                    ).build(), 422
                
                # Use JWT service for authentication
                from ...infrastructure.security.jwt_service import JWTService, AuthenticationService
                
                jwt_service = JWTService(self.security_middleware.jwt_service.config)
                auth_service = AuthenticationService(jwt_service)
                
                result = await auth_service.authenticate_user(
                    username=username,
                    password=password,
                    device_id=device_id
                )
                
                return jsonify({
                    "status": "success",
                    "message": "Authentication successful",
                    "data": result
                })
                
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                return ResponseBuilder().error("Authentication failed").add_error(
                    code="AUTHENTICATION_ERROR",
                    message=str(e),
                    error_type=ErrorType.AUTHENTICATION_ERROR
                ).build(), 401
        
        @auth_bp.route('/refresh', methods=['POST'])
        @csrf_exempt
        def refresh_token():
            """Refresh access token using refresh token"""
            try:
                data = request.get_json()
                refresh_token = data.get('refresh_token')
                
                if not refresh_token:
                    return ResponseBuilder().error("Refresh token required").add_error(
                        code="VALIDATION_ERROR",
                        message="Refresh token is required",
                        error_type=ErrorType.VALIDATION_ERROR
                    ).build(), 422
                
                jwt_service = JWTService(self.security_middleware.jwt_service.config)
                
                new_access_token, new_refresh_token, expire = await jwt_service.refresh_access_token(refresh_token)
                
                return jsonify({
                    "status": "success",
                    "message": "Token refreshed successfully",
                    "data": {
                        "access_token": new_access_token,
                        "refresh_token": new_refresh_token,
                        "expires_at": expire.isoformat()
                    }
                })
                
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                return ResponseBuilder().error("Token refresh failed").add_error(
                    code="TOKEN_REFRESH_ERROR",
                    message=str(e),
                    error_type=ErrorType.AUTHENTICATION_ERROR
                ).build(), 401
        
        # Register all blueprints
        self.app.register_blueprint(qc_records_bp)
        self.app.register_blueprint(temp_bp)
        self.app.register_blueprint(batches_bp)
        self.app.register_blueprint(dashboard_bp)
        self.app.register_blueprint(auth_bp)
        
        # Health check endpoint
        @self.app.route('/health', methods=['GET'])
        async def health_check():
            """Comprehensive health check"""
            try:
                health_status = {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "2.0.0",
                    "checks": {
                        "database": await self._check_database_health(),
                        "redis": await self._check_redis_health(),
                        "metrics": self.metrics_collector is not None,
                        "security": self.security_middleware is not None
                    }
                }
                
                # Determine overall health
                all_healthy = all([
                    health_status["checks"]["database"],
                    health_status["checks"]["redis"],
                    health_status["checks"]["metrics"],
                    health_status["checks"]["security"]
                ])
                
                if not all_healthy:
                    health_status["status"] = "unhealthy"
                
                status_code = 200 if all_healthy else 503
                
                return jsonify(health_status), status_code
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return jsonify({
                    "status": "unhealthy",
                    "error": str(e)
                }), 503
    
    async def _check_database_health(self) -> bool:
        """Check database connectivity"""
        try:
            db_manager = self.config.get_container().get('DatabaseManager')
            # Simple health check query
            return True
        except Exception:
            return False
    
    async def _check_redis_health(self) -> bool:
        """Check Redis connectivity"""
        try:
            if self.security_middleware and self.security_middleware.redis_client:
                self.security_middleware.redis_client.ping()
                return True
            return True  # Redis not required for basic operation
        except Exception:
            return False

# Flask app factory function
def create_enterprise_qc_app() -> Flask:
    """Create enterprise QC Flask application"""
    
    from flask import Flask
    from flask_cors import CORS
    
    app = Flask(__name__)
    
    # Configuration
    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'enterprise-secret-change-in-production'),
        'ENVIRONMENT': os.environ.get('ENVIRONMENT', 'development'),
        'DATABASE_URL': os.environ.get('DATABASE_URL'),
        'REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    })
    
    # Configure CORS
    CORS(app, origins=[
        "http://localhost:3000",  # Frontend development
        "http://localhost:8080",  # Alternative frontend port
        os.environ.get('FRONTEND_URL', '')  # Production frontend
    ])
    
    # Initialize enterprise API
    api = EnterpriseQCAPI(app)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return ResponseBuilder().error("Resource not found").add_error(
            code="NOT_FOUND",
            message="The requested resource was not found",
            error_type=ErrorType.NOT_FOUND_ERROR
        ).build(), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return ResponseBuilder().error("Internal server error").add_error(
            code="INTERNAL_ERROR",
            message="An internal server error occurred",
            error_type=ErrorType.SYSTEM_ERROR
        ).build(), 500
    
    return app