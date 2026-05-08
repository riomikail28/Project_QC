"""
QC Domain Entities - Enterprise Architecture
============================================
Core business entities following Domain-Driven Design principles.
These represent the fundamental business concepts and rules.

Entities include validation, business rules, and domain logic
to ensure data integrity and business rule enforcement.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid

class QCEntityStatus(str, Enum):
    """QC entity status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class UnitType(str, Enum):
    """Storage unit types"""
    CHILLER = "chiller"
    FREEZER = "freezer"
    AMBIENT = "ambient"
    DRY_STORAGE = "dry_storage"
    PREPARATION = "preparation"

class ValidationLevel(str, Enum):
    """QC validation levels"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    CRITICAL = "critical"

class BaseQCEntity(BaseModel):
    """Base QC entity with common fields and audit trail"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    facility_id: str = Field(..., description="Facility identifier")
    status: QCEntityStatus = QCEntityStatus.PENDING
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True
        validate_assignment = True
        use_enum_values = True
    
    @validator('updated_at', pre=True, always=True)
    def update_timestamp(cls, v, values):
        """Automatically update timestamp on modification"""
        return datetime.utcnow() if not v else v

class QCFacility(BaseQCEntity):
    """QC Facility entity representing a branch or location"""
    
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    address: str = Field(..., min_length=1, max_length=500)
    city: str = Field(..., min_length=1, max_length=100)
    province: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=5, max_length=10)
    phone: str = Field(..., min_length=10, max_length=20)
    manager_name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = Field(default=True)
    
    @validator('code')
    def validate_facility_code(cls, v):
        """Validate facility code format"""
        if not v or not v.replace('_', '').isalnum():
            raise ValueError('Facility code must be alphanumeric with optional underscores')
        return v.upper()

class QCProduct(BaseQCEntity):
    """QC Product entity representing food items"""
    
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., min_length=1, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    storage_requirements: Dict[str, Any] = Field(default_factory=dict)
    shelf_life_days: Optional[int] = Field(None, ge=0)
    is_perishable: bool = Field(default=True)
    allergens: Optional[List[str]] = Field(default_factory=list)
    nutritional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('sku')
    def validate_sku(cls, v):
        """Validate SKU format"""
        if not v or not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('SKU must be alphanumeric with optional hyphens/underscores')
        return v.upper()
    
    @validator('shelf_life_days')
    def validate_shelf_life(cls, v):
        """Validate shelf life for perishable items"""
        if v is not None and v < 1:
            raise ValueError('Shelf life must be at least 1 day')
        return v

class QCBatch(BaseQCEntity):
    """QC Batch entity for production batch tracking"""
    
    batch_number: str = Field(..., min_length=1, max_length=50)
    product_id: str = Field(..., description="Product identifier")
    quantity_produced: int = Field(..., gt=0, description="Quantity produced")
    production_date: datetime = Field(..., description="Production timestamp")
    expiry_date: Optional[datetime] = Field(None, description="Expiry date")
    storage_unit_id: Optional[str] = Field(None, description="Storage unit identifier")
    temperature_zone: UnitType = Field(..., description="Temperature storage zone")
    qc_required: bool = Field(default=True)
    qc_completed: bool = Field(default=False)
    qc_result: Optional[ValidationLevel] = Field(None)
    
    @validator('batch_number')
    def validate_batch_number(cls, v):
        """Validate batch number format"""
        if not v or len(v.strip()) < 1:
            raise ValueError('Batch number cannot be empty')
        return v.strip().upper()
    
    @validator('expiry_date')
    def validate_expiry_date(cls, v, values):
        """Validate expiry date is after production date"""
        if v and 'production_date' in values and v <= values['production_date']:
            raise ValueError('Expiry date must be after production date')
        return v

class TemperatureReading(BaseQCEntity):
    """Temperature reading entity for QC monitoring"""
    
    batch_id: str = Field(..., description="Batch identifier")
    unit_type: UnitType = Field(..., description="Storage unit type")
    temperature_celsius: float = Field(..., description="Temperature in Celsius")
    target_min: float = Field(..., description="Minimum acceptable temperature")
    target_max: float = Field(..., description="Maximum acceptable temperature")
    validation_result: ValidationLevel = Field(..., description="QC validation result")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")
    monitored_by: str = Field(..., description="Who performed the check")
    device_id: Optional[str] = Field(None, description="Monitoring device ID")
    
    @validator('temperature_celsius')
    def validate_temperature(cls, v):
        """Validate temperature range"""
        if abs(v) > 100:  # Reasonable temperature range
            raise ValueError('Temperature seems unrealistic (extreme value)')
        return v
    
    @validator('target_min', 'target_max')
    def validate_target_range(cls, v):
        """Validate target temperature range"""
        if abs(v) > 100:
            raise ValueError('Target temperatures seem unrealistic')
        return v
    
    def validate_against_sop(self) -> ValidationLevel:
        """Apply SOP validation rules for this temperature reading"""
        if self.unit_type == UnitType.CHILLER:
            if 0 <= self.temperature_celsius <= 5:
                return ValidationLevel.PASS
            elif 5 < self.temperature_celsius <= 8:
                return ValidationLevel.WARNING
            else:
                return ValidationLevel.FAIL
                
        elif self.unit_type == UnitType.FREEZER:
            if self.temperature_celsius <= -18:
                return ValidationLevel.PASS
            elif -18 < self.temperature_celsius <= -10:
                return ValidationLevel.WARNING
            else:
                return ValidationLevel.FAIL
                
        elif self.unit_type == UnitType.AMBIENT:
            if self.temperature_celsius <= 25:
                return ValidationLevel.PASS
            elif 25 < self.temperature_celsius <= 30:
                return ValidationLevel.WARNING
            else:
                return ValidationLevel.FAIL
                
        else:  # Other units
            if self.target_min <= self.temperature_celsius <= self.target_max:
                return ValidationLevel.PASS
            else:
                return ValidationLevel.WARNING

class QCRecord(BaseQCEntity):
    """Complete QC check record with comprehensive validation"""
    
    batch_id: str = Field(..., description="Batch being checked")
    product_id: str = Field(..., description="Product being checked")
    facility_id: str = Field(..., description="Where check was performed")
    check_type: str = Field(..., description="Type of QC check")
    temperature_readings: List[TemperatureReading] = Field(default_factory=list)
    visual_inspection: Optional[Dict[str, Any]] = Field(default_factory=dict)
    sensory_evaluation: Optional[Dict[str, Any]] = Field(default_factory=dict)
    microbiological_tests: Optional[Dict[str, Any]] = Field(default_factory=dict)
    overall_result: ValidationLevel = Field(..., description="Overall QC result")
    requires_retention: bool = Field(default=False)
    retention_reasons: Optional[List[str]] = Field(default_factory=list)
    next_check_date: Optional[datetime] = Field(None)
    qc_performed_by: str = Field(..., description="QC personnel")
    qc_supervisor: Optional[str] = Field(None, description="QC supervisor")
    
    @validator('qc_performed_by')
    def validate_qc_performer(cls, v):
        """Validate QC performer exists and is qualified"""
        if not v or len(v.strip()) < 1:
            raise ValueError('QC performer must be specified')
        return v.strip()
    
    def calculate_overall_result(self) -> ValidationLevel:
        """Calculate overall QC result from all components"""
        results = []
        
        # Temperature readings
        if self.temperature_readings:
            temp_results = [reading.validation_result for reading in self.temperature_readings]
            if ValidationLevel.FAIL in temp_results:
                return ValidationLevel.FAIL
            if ValidationLevel.WARNING in temp_results:
                results.append(ValidationLevel.WARNING)
            else:
                results.append(ValidationLevel.PASS)
        
        # Visual inspection
        if self.visual_inspection:
            visual_result = self.visual_inspection.get('result', ValidationLevel.PASS)
            if visual_result == ValidationLevel.FAIL:
                return ValidationLevel.FAIL
            if visual_result == ValidationLevel.WARNING:
                results.append(ValidationLevel.WARNING)
        
        # Sensory evaluation
        if self.sensory_evaluation:
            sensory_result = self.sensory_evaluation.get('result', ValidationLevel.PASS)
            if sensory_result == ValidationLevel.FAIL:
                return ValidationLevel.FAIL
            if sensory_result == ValidationLevel.WARNING:
                results.append(ValidationLevel.WARNING)
        
        # Microbiological tests
        if self.microbiological_tests:
            micro_result = self.microbiological_tests.get('result', ValidationLevel.PASS)
            if micro_result == ValidationLevel.FAIL:
                return ValidationLevel.FAIL
            if micro_result == ValidationLevel.WARNING:
                results.append(ValidationLevel.WARNING)
        
        # Determine overall result
        if ValidationLevel.WARNING in results:
            return ValidationLevel.WARNING
        return ValidationLevel.PASS

class QCEvent(BaseQCEntity):
    """QC Event for audit trail and monitoring"""
    
    event_type: str = Field(..., description="Type of QC event")
    entity_type: str = Field(..., description="Type of entity affected")
    entity_id: str = Field(..., description="ID of affected entity")
    event_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    severity: str = Field(default="info", description="Event severity level")
    source_system: str = Field(default="qc_system", description="System generating event")
    
    @validator('severity')
    def validate_severity(cls, v):
        """Validate severity level"""
        valid_severities = ['low', 'info', 'medium', 'high', 'critical']
        if v not in valid_severities:
            raise ValueError(f'Severity must be one of: {valid_severities}')
        return v

# Domain Events for event-driven architecture
class DomainEvent(BaseModel):
    """Base domain event"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    aggregate_id: str
    aggregate_type: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    event_data: Dict[str, Any]

class QCCompletedEvent(DomainEvent):
    """Event raised when QC is completed"""
    event_type: str = "qc_completed"
    aggregate_type: str = "qc_record"
    
class BatchCreatedEvent(DomainEvent):
    """Event raised when a batch is created"""
    event_type: str = "batch_created"
    aggregate_type: str = "batch"

class TemperatureAlertEvent(DomainEvent):
    """Event raised when temperature readings are out of range"""
    event_type: str = "temperature_alert"
    aggregate_type: str = "temperature_reading"