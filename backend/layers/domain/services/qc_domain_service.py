"""
QC Domain Service - Enterprise Architecture
==========================================
Core business logic encapsulated as domain services.
These services orchestrate complex business operations and enforce
business rules across multiple entities.

Follows Domain-Driven Design principles and SOLID practices.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from ..entities.qc_entities import (
    QCBatch, QCRecord, TemperatureReading, ValidationLevel,
    QCProduct, QCFacility, QCEvent, 
    QCCompletedEvent, TemperatureAlertEvent, BatchCreatedEvent
)

logger = logging.getLogger("qc.domain.services")

class QCBusinessRule(str, Enum):
    """QC business rule identifiers for validation"""
    TEMPERATURE_RANGE_VALID = "TEMP_RANGE_VALID"
    BATCH_EXPIRY_CHECK = "BATCH_EXPIRY_CHECK"
    RETENTION_APPLICABLE = "RETENTION_APPLICABLE"
    QC_COMPLETION_VALID = "QC_COMPLETION_VALID"

class ValidationResult:
    """Result of business rule validation"""
    
    def __init__(
        self,
        is_valid: bool,
        rule: QCBusinessRule,
        message: str,
        severity: str = "error"
    ):
        self.is_valid = is_valid
        self.rule = rule
        self.message = message
        self.severity = severity
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        return f"ValidationResult(valid={self.is_valid}, rule={self.rule}, message={self.message})"

class QCDomainService:
    """
    Core QC domain services for business logic orchestration.
    Implements complex business rules and cross-entity operations.
    """
    
    def __init__(self):
        """Initialize QC domain service"""
        self.logger = logging.getLogger("qc.domain.services")
    
    async def validate_temperature_reading(
        self, 
        reading: TemperatureReading, 
        sop_requirements: Optional[Dict[str, Any]] = None
    ) -> List[ValidationResult]:
        """
        Validate temperature reading against SOP requirements
        
        Args:
            reading: Temperature reading to validate
            sop_requirements: Optional SOP requirements override
            
        Returns:
            List of validation results
        """
        results = []
        
        # Temperature range validation
        sop_range = sop_requirements or self._get_sop_temperature_range(reading.unit_type)
        
        if reading.temperature_celsius < sop_range['min'] or reading.temperature_celsius > sop_range['max']:
            results.append(ValidationResult(
                is_valid=True,  # We record the reading but mark it
                rule=QCBusinessRule.TEMPERATURE_RANGE_VALID,
                message=f"Temperature {reading.temperature_celsius}°C outside SOP range {sop_range['min']}°C - {sop_range['max']}°C",
                severity="warning" if reading.unit_type in ["chiller", "ambient"] else "error"
            ))
        
        # Critical threshold validation
        critical_threshold = self._get_critical_threshold(reading.unit_type)
        if abs(reading.temperature_celsius) > critical_threshold:
            results.append(ValidationResult(
                is_valid=False,
                rule=QCBusinessRule.TEMPERATURE_RANGE_VALID,
                message=f"Temperature {reading.temperature_celsius}°C exceeds critical threshold {critical_threshold}°C",
                severity="critical"
            ))
        
        # Device validation if device ID is provided
        if reading.device_id:
            device_valid = await self._validate_device(reading.device_id, reading.facility_id)
            if not device_valid:
                results.append(ValidationResult(
                    is_valid=False,
                    rule=QCBusinessRule.TEMPERATURE_RANGE_VALID,
                    message=f"Device {reading.device_id} not validated for facility {reading.facility_id}",
                    severity="warning"
                ))
        
        self.logger.info(f"Temperature validation completed: {len(results)} results")
        return results
    
    async def validate_batch_expiry(
        self,
        batch: QCBatch,
        check_date: Optional[datetime] = None
    ) -> List[ValidationResult]:
        """
        Validate batch for expiry and shelf life
        
        Args:
            batch: Batch to validate
            check_date: Date to check against (defaults to current)
            
        Returns:
            Validation results
        """
        results = []
        check_date = check_date or datetime.utcnow()
        
        # Expiry date validation
        if batch.expiry_date:
            days_to_expiry = (batch.expiry_date - check_date).days
            
            if days_to_expiry < 0:
                results.append(ValidationResult(
                    is_valid=False,
                    rule=QCBusinessRule.BATCH_EXPIRY_CHECK,
                    message=f"Batch expired {abs(days_to_expiry)} days ago",
                    severity="critical"
                ))
            elif days_to_expiry <= 7:
                results.append(ValidationResult(
                    is_valid=True,
                    rule=QCBusinessRule.BATCH_EXPIRY_CHECK,
                    message=f"Batch expires in {days_to_expiry} days",
                    severity="high"
                ))
        
        # Shelf life validation
        if batch.production_date:
            days_since_production = (check_date - batch.production_date).days
            
            # Get product shelf life from repository or use defaults
            max_shelf_life = await self._get_product_shelf_life(batch.product_id)
            
            if max_shelf_life and days_since_production > max_shelf_life:
                results.append(ValidationResult(
                    is_valid=False,
                    rule=QCBusinessRule.BATCH_EXPIRY_CHECK,
                    message=f"Batch exceeds shelf life by {days_since_production - max_shelf_life} days",
                    severity="error"
                ))
        
        self.logger.info(f"Batch expiry validation completed: {len(results)} results")
        return results
    
    async def calculate_retention_required(
        self,
        qc_record: QCRecord
    ) -> List[ValidationResult]:
        """
        Calculate if batch retention is required based on QC results
        
        Args:
            qc_record: QC record to evaluate
            
        Returns:
            Validation results for retention decisions
        """
        results = []
        retention_reasons = []
        
        # Check for any failures in temperature readings
        failed_temps = [r for r in qc_record.temperature_readings 
                       if r.validation_result == ValidationLevel.FAIL]
        if failed_temps:
            retention_reasons.append("Temperature failures detected")
        
        # Check microbiological results
        if qc_record.microbiological_tests:
            micro_result = qc_record.microbiological_tests.get('result', ValidationLevel.PASS)
            if micro_result == ValidationLevel.FAIL:
                retention_reasons.append("Microbiological test failure")
        
        # Check critical sensory issues
        if qc_record.sensory_evaluation:
            sensory_result = qc_record.sensory_evaluation.get('result', ValidationLevel.PASS)
            if sensory_result == ValidationLevel.CRITICAL:
                retention_reasons.append("Critical sensory issues")
        
        # Check quality indicators
        if qc_record.visual_inspection:
            visual_result = qc_record.visual_inspection.get('result', ValidationLevel.PASS)
            if visual_result == ValidationLevel.FAIL:
                retention_reasons.append("Visual inspection failure")
        
        # Determine retention requirement
        requires_retention = len(retention_reasons) > 0
        
        results.append(ValidationResult(
            is_valid=not requires_retention,
            rule=QCBusinessRule.RETENTION_APPLICABLE,
            message="Retention required" if requires_retention else "No retention required",
            severity="high" if requires_retention else "info"
        ))
        
        if requires_retention:
            results.append(ValidationResult(
                is_valid=True,
                rule=QCBusinessRule.RETENTION_APPLICABLE,
                message=f"Retention reasons: {', '.join(retention_reasons)}",
                severity="info"
            ))
        
        self.logger.info(f"Retention evaluation completed: requires_retention={requires_retention}")
        return results
    
    async def validate_qc_completion(
        self,
        qc_record: QCRecord
    ) -> List[ValidationResult]:
        """
        Validate that QC record is complete and can be finalized
        
        Args:
            qc_record: QC record to validate
            
        Returns:
            Validation results for completion
        """
        results = []
        
        # Check temperature readings completeness
        if not qc_record.temperature_readings:
            results.append(ValidationResult(
                is_valid=False,
                rule=QCBusinessRule.QC_COMPLETION_VALID,
                message="No temperature readings recorded",
                severity="error"
            ))
        
        # Check required personnel information
        if not qc_record.qc_performed_by or len(qc_record.qc_performed_by.strip()) < 3:
            results.append(ValidationResult(
                is_valid=False,
                rule=QCBusinessRule.QC_COMPLETION_VALID,
                message="QC performed by information incomplete",
                severity="error"
            ))
        
        # Check overall result consistency
        calculated_result = qc_record.calculate_overall_result()
        if calculated_result != qc_record.overall_result:
            results.append(ValidationResult(
                is_valid=True,  # We'll auto-correct
                rule=QCBusinessRule.QC_COMPLETION_VALID,
                message=f"Overall result mismatch: calculated={calculated_result}, stored={qc_record.overall_result}",
                severity="warning"
            ))
        
        # Check retention consistency
        retention_eval = await self.calculate_retention_required(qc_record)
        requires_retention = any(not r.is_valid for r in retention_eval if r.rule == QCBusinessRule.RETENTION_APPLICABLE)
        
        if requires_retention != qc_record.requires_retention:
            results.append(ValidationResult(
                is_valid=True,  # We'll auto-correct
                rule=QCBusinessRule.QC_COMPLETION_VALID,
                message=f"Retention flag mismatch: calculated={requires_retention}, stored={qc_record.requires_retention}",
                severity="warning"
            ))
        
        self.logger.info(f"QC completion validation completed: {len(results)} results")
        return results
    
    async def create_qc_events(
        self,
        qc_record: QCRecord
    ) -> List[QCEvent]:
        """
        Create appropriate QC events based on record state
        
        Args:
            qc_record: QC record to generate events for
            
        Returns:
            List of QC events
        """
        events = []
        
        # Temperature alert events
        for reading in qc_record.temperature_readings:
            if reading.validation_result in [ValidationLevel.WARNING, ValidationLevel.FAIL]:
                alert_event = QCEvent(
                    event_type="temperature_alert",
                    entity_type="temperature_reading",
                    entity_id=reading.id,
                    event_data={
                        "temperature": reading.temperature_celsius,
                        "unit_type": reading.unit_type,
                        "validation_result": reading.validation_result.value
                    },
                    severity="high" if reading.validation_result == ValidationLevel.FAIL else "medium",
                    facility_id=qc_record.facility_id
                )
                events.append(alert_event)
        
        # QC completion event
        if qc_record.status == "completed":
            completion_event = QCEvent(
                event_type="qc_completed",
                entity_type="qc_record",
                entity_id=qc_record.id,
                event_data={
                    "overall_result": qc_record.overall_result.value,
                    "requires_retention": qc_record.requires_retention
                },
                severity="high" if qc_record.overall_result == ValidationLevel.FAIL else "info",
                facility_id=qc_record.facility_id
            )
            events.append(completion_event)
        
        return events
    
    async def schedule_follow_up_checks(
        self,
        qc_record: QCRecord,
        facility_config: Optional[Dict[str, Any]] = None
    ) -> Optional[datetime]:
        """
        Calculate next required check date based on QC results
        
        Args:
            qc_record: QC record to evaluate
            facility_config: Facility-specific configuration
            
        Returns:
            Next check date if required
        """
        if qc_record.overall_result == ValidationLevel.PASS:
            # Standard check frequency
            frequency_hours = facility_config.get('standard_check_frequency_hours', 8) if facility_config else 8
        elif qc_record.overall_result == ValidationLevel.WARNING:
            # More frequent checks for warnings
            frequency_hours = facility_config.get('warning_check_frequency_hours', 4) if facility_config else 4
        else:
            # Failed records need immediate re-check
            frequency_hours = 1
        
        next_check = datetime.utcnow() + timedelta(hours=frequency_hours)
        
        self.logger.info(f"Scheduled next check for batch {qc_record.batch_id}: {next_check}")
        return next_check
    
    # Private helper methods
    
    def _get_sop_temperature_range(self, unit_type: str) -> Dict[str, float]:
        """Get SOP temperature requirements by unit type"""
        ranges = {
            "chiller": {"min": 0, "max": 8},
            "freezer": {"min": -20, "max": -18},
            "ambient": {"min": 20, "max": 30},
            "dry_storage": {"min": 15, "max": 25},
            "preparation": {"min": 10, "max": 25}
        }
        return ranges.get(unit_type, {"min": 0, "max": 50})
    
    def _get_critical_threshold(self, unit_type: str) -> float:
        """Get critical temperature threshold by unit type"""
        thresholds = {
            "chiller": 15,
            "freezer": 30,
            "ambient": 40,
            "dry_storage": 50,
            "preparation": 45
        }
        return thresholds.get(unit_type, 100)
    
    async def _validate_device(self, device_id: str, facility_id: str) -> bool:
        """Validate that device belongs to facility (placeholder for repository call)"""
        # This would call repository to validate device-facility mapping
        # For now, return True - implement with actual repository call
        return True
    
    async def _get_product_shelf_life(self, product_id: str) -> Optional[int]:
        """Get product shelf life from repository (placeholder)"""
        # This would call repository to get product information
        # For now, return None - implement with actual repository call
        return None

class TemperatureValidationService:
    """Specialized service for temperature validation logic"""
    
    def __init__(self, domain_service: QCDomainService):
        self.domain_service = domain_service
    
    async def validate_batch_temperature_compliance(
        self,
        batch_id: str,
        readings: List[TemperatureReading]
    ) -> Dict[str, Any]:
        """
        Validate full batch temperature compliance
        
        Args:
            batch_id: Batch identifier
            readings: List of temperature readings
            
        Returns:
            Compliance report
        """
        if not readings:
            return {
                "batch_id": batch_id,
                "is_compliant": False,
                "issues": ["No temperature readings available"]
            }
        
        issues = []
        warnings = []
        critical_alerts = []
        
        for reading in readings:
            validations = await self.domain_service.validate_temperature_reading(reading)
            
            for validation in validations:
                if validation.severity == "critical":
                    critical_alerts.append(validation.message)
                elif validation.severity == "error":
                    issues.append(validation.message)
                elif validation.severity == "warning":
                    warnings.append(validation.message)
        
        # Determine overall compliance
        is_compliant = len(critical_alerts) == 0 and len(issues) == 0
        
        compliance_level = "PASS"
        if critical_alerts:
            compliance_level = "FAIL"
        elif issues:
            compliance_level = "WARNING"
        elif warnings:
            compliance_level = "PASS_WITH_WARNINGS"
        
        return {
            "batch_id": batch_id,
            "is_compliant": is_compliant,
            "compliance_level": compliance_level,
            "total_readings": len(readings),
            "critical_alerts": critical_alerts,
            "issues": issues,
            "warnings": warnings,
            "validated_at": datetime.utcnow()
        }

class ReportingService:
    """Service for generating QC reports and analytics"""
    
    def __init__(self):
        self.logger = logging.getLogger("qc.reporting")
    
    async def generate_facility_compliance_report(
        self,
        facility_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Generate facility compliance report for date range
        
        Args:
            facility_id: Facility identifier
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Compliance report data
        """
        # This would use repository data to generate comprehensive report
        # For now, return report structure
        return {
            "facility_id": facility_id,
            "report_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "summary": {
                "total_checks": 0,
                "pass_rate": 0.0,
                "warning_rate": 0.0,
                "failure_rate": 0.0
            },
            "by_unit_type": {},
            "trends": [],
            "recommendations": [],
            "generated_at": datetime.utcnow()
        }