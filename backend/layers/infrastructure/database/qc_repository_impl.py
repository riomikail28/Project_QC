"""
QC Repository Implementation - Enterprise Architecture
=====================================================
Concrete implementations for QC domain repositories with PostgreSQL support.
Includes optimization for high-volume QC operations and audit capabilities.

Implements:
- QC Record repository with pagination and filtering
- Temperature reading repository with time-series optimization  
- Batch repository with status tracking
- Facility repository with multi-tenant support
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, desc, asc, func, between
from sqlalchemy.orm import joinedload
import uuid
import logging

from .base_repository_impl import AuditableRepositoryImpl, Base
from ...domain.entities.qc_entities import (
    QCRecord, QCBatch, TemperatureReading, QCFacility, QCProduct,
    ValidationLevel, QCEntityStatus
)

logger = logging.getLogger("qc.database.repositories")

# SQLAlchemy Database Models
class QCRecordModel(Base):
    """QC Record database model"""
    __tablename__ = 'qc_records'
    
    id = sa.Column(sa.String, primary_key=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = sa.Column(sa.DateTime, nullable=True)
    created_by = sa.Column(sa.String, nullable=True)
    updated_by = sa.Column(sa.String, nullable=True)
    facility_id = sa.Column(sa.String, nullable=False, index=True)
    status = sa.Column(sa.Enum(QCEntityStatus), default=QCEntityStatus.PENDING, nullable=False, index=True)
    metadata = sa.Column(sa.JSON)
    
    # QC-specific fields
    batch_id = sa.Column(sa.String, nullable=False, index=True)
    product_id = sa.Column(sa.String, nullable=False, index=True)
    check_type = sa.Column(sa.String, nullable=False)
    overall_result = sa.Column(sa.Enum(ValidationLevel), nullable=False)
    requires_retention = sa.Column(sa.Boolean, default=False)
    retention_reasons = sa.Column(sa.JSON)
    next_check_date = sa.Column(sa.DateTime, nullable=True, index=True)
    qc_performed_by = sa.Column(sa.String, nullable=False)
    qc_supervisor = sa.Column(sa.String, nullable=True)

class QCBatchModel(Base):
    """QC Batch database model"""
    __tablename__ = 'qc_batches'
    
    id = sa.Column(sa.String, primary_key=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = sa.Column(sa.DateTime, nullable=True)
    created_by = sa.Column(sa.String, nullable=True)
    updated_by = sa.Column(sa.String, nullable=True)
    facility_id = sa.Column(sa.String, nullable=False, index=True)
    status = sa.Column(sa.Enum(QCEntityStatus), default=QCEntityStatus.PENDING, nullable=False, index=True)
    metadata = sa.Column(sa.JSON)
    
    # Batch-specific fields
    batch_number = sa.Column(sa.String, unique=True, nullable=False, index=True)
    product_id = sa.Column(sa.String, nullable=False, index=True)
    quantity_produced = sa.Column(sa.Integer, nullable=False)
    production_date = sa.Column(sa.DateTime, nullable=False, index=True)
    expiry_date = sa.Column(sa.DateTime, nullable=True, index=True)
    storage_unit_id = sa.Column(sa.String, nullable=True)
    temperature_zone = sa.Column(sa.String, nullable=False)
    qc_required = sa.Column(sa.Boolean, default=True)
    qc_completed = sa.Column(sa.Boolean, default=False)
    qc_result = sa.Column(sa.Enum(ValidationLevel), nullable=True)

class TemperatureReadingModel(Base):
    """Temperature Reading database model with partitioning support"""
    __tablename__ = 'temperature_readings'
    
    id = sa.Column(sa.String, primary_key=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = sa.Column(sa.DateTime, nullable=True)
    created_by = sa.Column(sa.String, nullable=True)
    updated_by = sa.Column(sa.String, nullable=True)
    facility_id = sa.Column(sa.String, nullable=False, index=True)
    status = sa.Column(sa.Enum(QCEntityStatus), default=QCEntityStatus.PENDING, nullable=False)
    metadata = sa.Column(sa.JSON)
    
    # Temperature-specific fields
    batch_id = sa.Column(sa.String, nullable=False, index=True)
    unit_type = sa.Column(sa.String, nullable=False, index=True)
    temperature_celsius = sa.Column(sa.Numeric(5, 2), nullable=False, index=True)
    target_min = sa.Column(sa.Numeric(5, 2), nullable=False)
    target_max = sa.Column(sa.Numeric(5, 2), nullable=False)
    validation_result = sa.Column(sa.Enum(ValidationLevel), nullable=False, index=True)
    notes = sa.Column(sa.Text, nullable=True)
    monitored_by = sa.Column(sa.String, nullable=False)
    device_id = sa.Column(sa.String, nullable=True, index=True)

class QCFacilityModel(Base):
    """QC Facility database model"""
    __tablename__ = 'qc_facilities'
    
    id = sa.Column(sa.String, primary_key=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = sa.Column(sa.DateTime, nullable=True)
    created_by = sa.Column(sa.String, nullable=True)
    updated_by = sa.Column(sa.String, nullable=True)
    facility_id = sa.Column(sa.String, nullable=False, index=True)  # Duplicate for consistency
    status = sa.Column(sa.Enum(QCEntityStatus), default=QCEntityStatus.PENDING, nullable=False)
    metadata = sa.Column(sa.JSON)
    
    # Facility-specific fields
    name = sa.Column(sa.String, nullable=False)
    code = sa.Column(sa.String, unique=True, nullable=False)
    address = sa.Column(sa.String, nullable=False)
    city = sa.Column(sa.String, nullable=False)
    province = sa.Column(sa.String, nullable=False)
    postal_code = sa.Column(sa.String, nullable=False)
    phone = sa.Column(sa.String, nullable=False)
    manager_name = sa.Column(sa.String, nullable=False)
    is_active = sa.Column(sa.Boolean, default=True, nullable=False)

class QCProductModel(Base):
    """QC Product database model"""
    __tablename__ = 'qc_products'
    
    id = sa.Column(sa.String, primary_key=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = sa.Column(sa.DateTime, nullable=True)
    created_by = sa.Column(sa.String, nullable=True)
    updated_by = sa.Column(sa.String, nullable=True)
    facility_id = sa.Column(sa.String, nullable=False, index=True)
    status = sa.Column(sa.Enum(QCEntityStatus), default=QCEntityStatus.PENDING, nullable=False)
    metadata = sa.Column(sa.JSON)
    
    # Product-specific fields
    name = sa.Column(sa.String, nullable=False)
    sku = sa.Column(sa.String, unique=True, nullable=False, index=True)
    category = sa.Column(sa.String, nullable=False, index=True)
    subcategory = sa.Column(sa.String, nullable=True, index=True)
    description = sa.Column(sa.Text, nullable=True)
    storage_requirements = sa.Column(sa.JSON)
    shelf_life_days = sa.Column(sa.Integer, nullable=True)
    is_perishable = sa.Column(sa.Boolean, default=True)
    allergens = sa.Column(sa.JSON)
    nutritional_info = sa.Column(sa.JSON)

# Repository Implementations
class QCRepositoryImpl(AuditableRepositoryImpl[QCRecord]):
    """QC Record repository implementation"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager, QCRecordModel)
    
    async def get_records_by_batch(self, batch_id: str) -> List[QCRecord]:
        """Get QC records for specific batch"""
        async with self.db_manager.get_session() as session:
            try:
                query = select(QCRecordModel).where(
                    QCRecordModel.batch_id == batch_id
                ).order_by(desc(QCRecordModel.created_at))
                
                result = await session.execute(query)
                models = result.scalars().all()
                
                return [self._model_to_entity(model) for model in models]
                
            except Exception as e:
                self.logger.error(f"Failed to get QC records for batch {batch_id}: {e}")
                raise
    
    async def get_records_by_facility(
        self, 
        facility_id: str,
        start_date: datetime,
        end_date: datetime,
        status: Optional[QCEntityStatus] = None
    ) -> List[QCRecord]:
        """Get QC records for facility within date range"""
        async with self.db_manager.get_session() as session:
            try:
                # Build query with date range filtering
                query_conditions = [
                    QCRecordModel.facility_id == facility_id,
                    between(QCRecordModel.created_at, start_date, end_date)
                ]
                
                if status:
                    query_conditions.append(QCRecordModel.status == status)
                
                query = select(QCRecordModel).where(
                    and_(*query_conditions)
                ).order_by(desc(QCRecordModel.created_at))
                
                result = await session.execute(query)
                models = result.scalars().all()
                
                return [self._model_to_entity(model) for model in models]
                
            except Exception as e:
                self.logger.error(f"Failed to get QC records for facility {facility_id}: {e}")
                raise
    
    async def get_pending_records(self, facility_id: Optional[str] = None) -> List[QCRecord]:
        """Get pending QC records"""
        async with self.db_manager.get_session() as session:
            try:
                query_conditions = [QCRecordModel.status == QCEntityStatus.PENDING]
                
                if facility_id:
                    query_conditions.append(QCRecordModel.facility_id == facility_id)
                
                query = select(QCRecordModel).where(
                    and_(*query_conditions)
                ).order_by(asc(QCRecordModel.created_at))
                
                result = await session.execute(query)
                models = result.scalars().all()
                
                return [self._model_to_entity(model) for model in models]
                
            except Exception as e:
                self.logger.error(f"Failed to get pending QC records: {e}")
                raise
    
    async def get_compliance_summary(
        self,
        facility_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get compliance summary for facility and date range"""
        async with self.db_manager.get_session() as session:
            try:
                # Aggregate query for compliance statistics
                query = select(
                    QCRecordModel.overall_result,
                    func.count(QCRecordModel.id).label('count')
                ).where(
                    and_(
                        QCRecordModel.facility_id == facility_id,
                        between(QCRecordModel.created_at, start_date, end_date)
                    )
                ).group_by(QCRecordModel.overall_result)
                
                result = await session.execute(query)
                data = {row.overall_result: row.count for row in result}
                
                total = sum(data.values())
                
                return {
                    'total_records': total,
                    'pass_count': data.get(ValidationLevel.PASS, 0),
                    'warning_count': data.get(ValidationLevel.WARNING, 0),
                    'fail_count': data.get(ValidationLevel.FAIL, 0),
                    'pass_rate': (data.get(ValidationLevel.PASS, 0) / total * 100) if total > 0 else 0
                }
                
            except Exception as e:
                self.logger.error(f"Failed to get compliance summary: {e}")
                raise
    
    def _entity_to_model(self, entity: QCRecord) -> QCRecordModel:
        """Convert QC Record entity to database model"""
        return QCRecordModel(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            facility_id=entity.facility_id,
            status=entity.status,
            metadata=entity.metadata,
            
            # QC-specific fields
            batch_id=entity.batch_id,
            product_id=entity.product_id,
            check_type=entity.check_type,
            overall_result=entity.overall_result,
            requires_retention=entity.requires_retention,
            retention_reasons=entity.retention_reasons,
            next_check_date=entity.next_check_date,
            qc_performed_by=entity.qc_performed_by,
            qc_supervisor=entity.qc_supervisor
        )
    
    def _model_to_entity(self, model: QCRecordModel) -> QCRecord:
        """Convert database model to QC Record entity"""
        return QCRecord(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            updated_by=model.updated_by,
            facility_id=model.facility_id,
            status=model.status,
            metadata=model.metadata,
            
            batch_id=model.batch_id,
            product_id=model.product_id,
            check_type=model.check_type,
            overall_result=model.overall_result,
            requires_retention=model.requires_retention,
            retention_reasons=model.retention_reasons or [],
            next_check_date=model.next_check_date,
            qc_performed_by=model.qc_performed_by,
            qc_supervisor=model.qc_supervisor
        )

class QCBatchRepositoryImpl(AuditableRepositoryImpl[QCBatch]):
    """QC Batch repository implementation"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager, QCBatchModel)
    
    async def get_batch_by_number(self, batch_number: str) -> Optional[QCBatch]:
        """Get batch by batch number"""
        async with self.db_manager.get_session() as session:
            try:
                result = await session.execute(
                    select(QCBatchModel).where(QCBatchModel.batch_number == batch_number)
                )
                model = result.scalar_one_or_none()
                
                if model:
                    return self._model_to_entity(model)
                return None
                
            except Exception as e:
                self.logger.error(f"Failed to get batch by number {batch_number}: {e}")
                raise
    
    async def get_batches_by_product(self, product_id: str, facility_id: Optional[str] = None) -> List[QCBatch]:
        """Get batches for specific product"""
        async with self.db_manager.get_session() as session:
            try:
                query_conditions = [QCBatchModel.product_id == product_id]
                
                if facility_id:
                    query_conditions.append(QCBatchModel.facility_id == facility_id)
                
                query = select(QCBatchModel).where(
                    and_(*query_conditions)
                ).order_by(desc(QCBatchModel.production_date))
                
                result = await session.execute(query)
                models = result.scalars().all()
                
                return [self._model_to_entity(model) for model in models]
                
            except Exception as e:
                self.logger.error(f"Failed to get batches for product {product_id}: {e}")
                raise
    
    async def get_expiring_batches(self, days_ahead: int = 7) -> List[QCBatch]:
        """Get batches expiring within specified days"""
        async with self.db_manager.get_session() as session:
            try:
                target_date = datetime.utcnow() + timedelta(days=days_ahead)
                
                query = select(QCBatchModel).where(
                    and_(
                        QCBatchModel.expiry_date <= target_date,
                        QCBatchModel.expiry_date > datetime.utcnow(),
                        QCBatchModel.status != QCEntityStatus.COMPLETED
                    )
                ).order_by(asc(QCBatchModel.expiry_date))
                
                result = await session.execute(query)
                models = result.scalars().all()
                
                return [self._model_to_entity(model) for model in models]
                
            except Exception as e:
                self.logger.error(f"Failed to get expiring batches: {e}")
                raise
    
    def _entity_to_model(self, entity: QCBatch) -> QCBatchModel:
        """Convert QCBatch entity to database model"""
        return QCBatchModel(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            facility_id=entity.facility_id,
            status=entity.status,
            metadata=entity.metadata,
            
            batch_number=entity.batch_number,
            product_id=entity.product_id,
            quantity_produced=entity.quantity_produced,
            production_date=entity.production_date,
            expiry_date=entity.expiry_date,
            storage_unit_id=entity.storage_unit_id,
            temperature_zone=entity.temperature_zone.value if hasattr(entity.temperature_zone, 'value') else entity.temperature_zone,
            qc_required=entity.qc_required,
            qc_completed=entity.qc_completed,
            qc_result=entity.qc_result
        )
    
    def _model_to_entity(self, model: QCBatchModel) -> QCBatch:
        """Convert database model to QCBatch entity"""
        from ...domain.entities.qc_entities import UnitType
        
        return QCBatch(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            updated_by=model.updated_by,
            facility_id=model.facility_id,
            status=model.status,
            metadata=model.metadata,
            
            batch_number=model.batch_number,
            product_id=model.product_id,
            quantity_produced=model.quantity_produced,
            production_date=model.production_date,
            expiry_date=model.expiry_date,
            storage_unit_id=model.storage_unit_id,
            temperature_zone=UnitType(model.temperature_zone) if model.temperature_zone else None,
            qc_required=model.qc_required,
            qc_completed=model.qc_completed,
            qc_result=model.qc_result
        )

class TemperatureReadingRepositoryImpl(BaseRepositoryImpl[TemperatureReading]):
    """Temperature Reading repository implementation with time-series optimization"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager, TemperatureReadingModel)
    
    async def get_readings_by_batch(
        self, 
        batch_id: str, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[TemperatureReading]:
        """Get temperature readings for batch within time range"""
        async with self.db_manager.get_session() as session:
            try:
                query_conditions = [TemperatureReadingModel.batch_id == batch_id]
                
                if start_time:
                    query_conditions.append(TemperatureReadingModel.created_at >= start_time)
                if end_time:
                    query_conditions.append(TemperatureReadingModel.created_at <= end_time)
                
                query = select(TemperatureReadingModel).where(
                    and_(*query_conditions)
                ).order_by(desc(TemperatureReadingModel.created_at))
                
                result = await session.execute(query)
                models = result.scalars().all()
                
                return [self._model_to_entity(model) for model in models]
                
            except Exception as e:
                self.logger.error(f"Failed to get temperature readings for batch {batch_id}: {e}")
                raise
    
    async def get_anomaly_readings(
        self, 
        facility_id: str,
        hours_back: int = 24
    ) -> List[TemperatureReading]:
        """Get anomalous temperature readings (warning/fail)"""
        async with self.db_manager.get_session() as session:
            try:
                start_time = datetime.utcnow() - timedelta(hours=hours_back)
                
                query = select(TemperatureReadingModel).where(
                    and_(
                        TemperatureReadingModel.facility_id == facility_id,
                        TemperatureReadingModel.created_at >= start_time,
                        TemperatureReadingModel.validation_result.in_([ValidationLevel.WARNING, ValidationLevel.FAIL])
                    )
                ).order_by(desc(TemperatureReadingModel.created_at))
                
                result = await session.execute(query)
                models = result.scalars().all()
                
                return [self._model_to_entity(model) for model in models]
                
            except Exception as e:
                self.logger.error(f"Failed to get anomaly readings for facility {facility_id}: {e}")
                raise
    
    def _entity_to_model(self, entity: TemperatureReading) -> TemperatureReadingModel:
        """Convert TemperatureReading entity to database model"""
        return TemperatureReadingModel(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            facility_id=entity.facility_id,
            status=entity.status,
            metadata=entity.metadata,
            
            batch_id=entity.batch_id,
            unit_type=entity.unit_type.value if hasattr(entity.unit_type, 'value') else entity.unit_type,
            temperature_celsius=entity.temperature_celsius,
            target_min=entity.target_min,
            target_max=entity.target_max,
            validation_result=entity.validation_result,
            notes=entity.notes,
            monitored_by=entity.monitored_by,
            device_id=entity.device_id
        )
    
    def _model_to_entity(self, model: TemperatureReadingModel) -> TemperatureReading:
        """Convert database model to TemperatureReading entity"""
        from ...domain.entities.qc_entities import UnitType
        
        return TemperatureReading(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            updated_by=model.updated_by,
            facility_id=model.facility_id,
            status=model.status,
            metadata=model.metadata,
            
            batch_id=model.batch_id,
            unit_type=UnitType(model.unit_type) if model.unit_type else None,
            temperature_celsius=float(model.temperature_celsius),
            target_min=float(model.target_min),
            target_max=float(model.target_max),
            validation_result=model.validation_result,
            notes=model.notes,
            monitored_by=model.monitored_by,
            device_id=model.device_id
        )