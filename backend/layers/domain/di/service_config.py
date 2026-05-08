"""
Enterprise Dependency Injection Configuration
============================================
Complete DI container setup for QC Central Kitchen enterprise system.
Registers all services, repositories, and infrastructure components
following SOLID principles and clean architecture.

Supported lifecycles:
- Singleton: Shared across application (configuration, database managers)
- Transient: New instance every time (services, repositories)
- Scoped: Same instance per request (unit of work)
"""

import logging
from typing import Dict, Any, Optional
import os

from .container import (
    DependencyContainer, ServiceLifetime, get_container, configure_services
)
from ..repositories.base_repository import BaseRepository, AuditableRepository
from ...infrastructure.database.base_repository_impl import (
    DatabaseManager, DatabaseConfig, create_database_manager
)
from ...infrastructure.database.qc_repository_impl import (
    QCRepositoryImpl, QCBatchRepositoryImpl, TemperatureReadingRepositoryImpl
)
from ..services.qc_domain_service import QCDomainService, TemperatureValidationService, ReportingService
from ..entities.qc_entities import QCRecord, QCBatch, TemperatureReading

logger = logging.getLogger("qc.di.service_config")

class EnterpriseServiceConfig:
    """Enterprise service configuration with environment support"""
    
    def __init__(self):
        self._container = get_container()
        self.logger = logging.getLogger("qc.enterprise.config")
    
    def configure_database_services(self, db_config: Optional[DatabaseConfig] = None):
        """Configure database services and repositories"""
        try:
            # Create database configuration
            if not db_config:
                db_config = DatabaseConfig(
                    database_url=os.getenv('DATABASE_URL', 'postgresql+asyncpg://localhost:5432/qc_system'),
                    pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
                    max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20')),
                    echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
                )
            
            # Register database manager as singleton
            def create_db_manager():
                import asyncio
                manager = DatabaseManager(db_config)
                return manager
            
            self._container.register_singleton(
                DatabaseManager, 
                type('DatabaseManagerFactory', (), {'__call__': lambda self: create_db_manager()})
            )
            
            # Register repositories as transient (new instance per use)
            self._container.register_transient(BaseRepository, BaseRepository)  # Base interface
            self._container.register_transient(AuditableRepository, AuditableRepository)  # Base interface for audit
            
            # QC-specific repositories
            self._container.register_transient(QCRepositoryImpl, QCRepositoryImpl)
            self._container.register_transient(QCBatchRepositoryImpl, QCBatchRepositoryImpl)
            self._container.register_transient(TemperatureReadingRepositoryImpl, TemperatureReadingRepositoryImpl)
            
            self.logger.info("Database services configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to configure database services: {e}")
            raise
    
    def configure_domain_services(self):
        """Configure domain services and business logic"""
        try:
            # Register core domain services
            self._container.register_singleton(QCDomainService, QCDomainService)
            self._container.register_singleton(TemperatureValidationService, TemperatureValidationService)
            self._container.register_singleton(ReportingService, ReportingService)
            
            self.logger.info("Domain services configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to configure domain services: {e}")
            raise
    
    def configure_infrastructure_services(self):
        """Configure infrastructure services caching, messaging, etc."""
        try:
            # Redis/Cache service
            if os.getenv('REDIS_ENABLED', 'false').lower() == 'true':
                from ...infrastructure.cache.redis_cache import RedisCacheService
                self._container.register_singleton(RedisCacheService, RedisCacheService)
            
            # File storage service
            if os.getenv('AWS_S3_ENABLED', 'false').lower() == 'true':
                from ...infrastructure.storage.s3_storage import S3StorageService
                self._container.register_singleton(S3StorageService, S3StorageService)
            else:
                from ...infrastructure.storage.local_storage import LocalStorageService
                self._container.register_singleton(LocalStorageService, LocalStorageService)
            
            # Notification service
            if os.getenv('EMAIL_ENABLED', 'false').lower() == 'true':
                from ...infrastructure.notifications.email_service import EmailNotificationService
                self._container.register_singleton(EmailNotificationService, EmailNotificationService)
            
            self.logger.info("Infrastructure services configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to configure infrastructure services: {e}")
            raise
    
    def configure_security_services(self):
        """Configure security and authentication services"""
        try:
            # JWT service
            from ...infrastructure.security.jwt_service import JWTService
            self._container.register_singleton(JWTService, JWTService)
            
            # Authentication service
            from ...infrastructure.security.auth_service import AuthenticationService
            self._container.register_transient(AuthenticationService, AuthenticationService)
            
            # Audit service
            from ...infrastructure.security.audit_service import AuditService
            self._container.register_singleton(AuditService, AuditService)
            
            self.logger.info("Security services configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to configure security services: {e}")
            raise
    
    def configure_monitoring_services(self):
        """Configure monitoring and observability services"""
        try:
            # Metrics service
            from ...infrastructure.monitoring.metrics_service import MetricsService
            self._container.register_singleton(MetricsService, MetricsService)
            
            # Health check service
            from ...infrastructure.monitoring.health_service import HealthCheckService
            self._container.register_singleton(HealthCheckService, HealthCheckService)
            
            # Logging service
            from ...infrastructure.monitoring.logging_service import LoggingService
            self._container.register_singleton(LoggingService, LoggingService)
            
            self.logger.info("Monitoring services configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to configure monitoring services: {e}")
            raise
    
    def configure_application_services(self):
        """Configure application-level services that orchestrate domain operations"""
        try:
            # QC workflow service
            from ...application.services.qc_workflow_service import QCWorkflowService
            self._container.register_transient(QCWorkflowService, QCWorkflowService)
            
            # Batch management service
            from ...application.services.batch_management_service import BatchManagementService
            self._container.register_transient(BatchManagementService, BatchManagementService)
            
            # Temperature monitoring service
            from ...application.services.temperature_monitoring_service import TemperatureMonitoringService
            self._container.register_transient(TemperatureMonitoringService, TemperatureMonitoringService)
            
            # Facility management service
            from ...application.services.facility_management_service import FacilityManagementService
            self._container.register_transient(FacilityManagementService, FacilityManagementService)
            
            # Reporting service integration
            from ...application.services.reporting_application_service import ReportingApplicationService
            self._container.register_transient(ReportingApplicationService, ReportingApplicationService)
            
            self.logger.info("Application services configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to configure application services: {e}")
            raise
    
    def configure_all_services(self, db_config: Optional[DatabaseConfig] = None):
        """Configure all services for the enterprise system"""
        try:
            self.logger.info("Configuring enterprise services...")
            
            # Configure in dependency order
            self.configure_database_services(db_config)
            self.configure_domain_services()
            self.configure_infrastructure_services()
            self.configure_security_services()
            self.configure_monitoring_services()
            self.configure_application_services()
            
            self.logger.info("All enterprise services configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to configure all services: {e}")
            raise
    
    def get_container(self) -> DependencyContainer:
        """Get the configured dependency container"""
        return self._container
    
    async def initialize_database(self):
        """Initialize database and create tables if needed"""
        try:
            db_manager = self._container.get(DatabaseManager)
            await db_manager.initialize()
            
            # Create tables
            from ...infrastructure.database.base_repository_impl import create_tables
            await create_tables(db_manager)
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def register_custom_service(self, interface: type, implementation: type, lifetime: ServiceLifetime = ServiceLifetime.SINGLETON):
        """Register custom service for extension"""
        try:
            if lifetime == ServiceLifetime.SINGLETON:
                self._container.register_singleton(interface, implementation)
            elif lifetime == ServiceLifetime.TRANSIENT:
                self._container.register_transient(interface, implementation)
            else:
                self._container.register_scoped(interface, implementation)
            
            self.logger.info(f"Custom service registered: {interface.__name__} -> {implementation.__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to register custom service: {e}")
            raise

# Environment-specific configurations
class DevelopmentServiceConfig(EnterpriseServiceConfig):
    """Development environment configuration with additional debug services"""
    
    def configure_all_services(self, db_config: Optional[DatabaseConfig] = None):
        """Configure development services with debug features"""
        super().configure_all_services(db_config)
        
        # Add debug services
        try:
            # Mock services for testing
            if os.getenv('USE_MOCK_SERVICES', 'false').lower() == 'true':
                self._configure_mock_services()
            
            # Development logging
            from ...infrastructure.monitoring.dev_logging_service import DevLoggingService
            self._container.register_singleton(DevLoggingService, DevLoggingService)
            
            self.logger.info("Development services configured")
            
        except Exception as e:
            self.logger.error(f"Failed to configure development services: {e}")
            raise
    
    def _configure_mock_services(self):
        """Configure mock services for development/testing"""
        from ...infrastructure.mock.mock_batch_service import MockBatchService
        from ...infrastructure.mock.mock_temperature_service import MockTemperatureService
        
        self._container.register_transient(MockBatchService, MockBatchService)
        self._container.register_transient(MockTemperatureService, MockTemperatureService)

class ProductionServiceConfig(EnterpriseServiceConfig):
    """Production environment configuration with enhanced security and monitoring"""
    
    def configure_all_services(self, db_config: Optional[DatabaseConfig] = None):
        """Configure production services with enterprise security"""
        super().configure_all_services(db_config)
        
        # Add production-specific services
        try:
            # Enhanced security
            from ...infrastructure.security.enterprise_security_service import EnterpriseSecurityService
            self._container.register_singleton(EnterpriseSecurityService, EnterpriseSecurityService)
            
            # Enhanced monitoring
            from ...infrastructure.monitoring.prometheus_metrics import PrometheusMetricsService
            self._container.register_singleton(PrometheusMetricsService, PrometheusMetricsService)
            
            # Performance monitoring
            from ...infrastructure.monitoring.apm_service import APMService
            self._container.register_singleton(APMService, APMService)
            
            self.logger.info("Production services configured")
            
        except Exception as e:
            self.logger.error(f"Failed to configure production services: {e}")
            raise

# Global configuration factory
def create_service_config() -> EnterpriseServiceConfig:
    """Create appropriate service configuration based on environment"""
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    if environment == 'production':
        return ProductionServiceConfig()
    elif environment == 'staging':
        return EnterpriseServiceConfig()  # Use standard config for staging
    else:
        return DevelopmentServiceConfig()  # Default to development config

# Convenience functions for service registration
def configure_enterprise_services(db_config: Optional[DatabaseConfig] = None) -> DependencyContainer:
    """Configure all enterprise services and return the container"""
    config = create_service_config()
    config.configure_all_services(db_config)
    return config.get_container()

async def initialize_services(db_config: Optional[DatabaseConfig] = None) -> DependencyContainer:
    """Initialize and configure all enterprise services including database"""
    config = create_service_config()
    config.configure_all_services(db_config)
    await config.initialize_database()
    return config.get_container()