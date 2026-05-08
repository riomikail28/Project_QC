"""
QC Workflow Service - Application Layer
======================================
Application service orchestrating QC workflow operations.
Implements use cases that coordinate between repositories and domain services.

This service handles:
- QC record creation and completion workflows
- Business rule enforcement across multiple domains
- Event generation and notification coordination
- Transaction management for complex operations
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4

from ...domain.repositories.base_repository import AuditableRepository
from ...domain.entities.qc_entities import (
    QCRecord, QCBatch, TemperatureReading, ValidationLevel,
    QCEntityStatus, QCEvent, QCCompletedEvent, TemperatureAlertEvent
)
from ...domain.services.qc_domain_service import (
    QCDomainService, TemperatureValidationService, ValidationResult
)
from ..services.enterprise_response import create_qc_response, create_temperature_response
from ..services.enterprise_response import ResponseBuilder, ErrorType

logger = logging.getLogger("qc.application.workflow")

class QCWorkflowService:
    """QC Workflow - Application layer service for QC operations"""
    
    def __init__(
        self,
        qc_repository: AuditableRepository[QCRecord],
        batch_repository: AuditableRepository[QCBatch],
        temperature_repository: AuditableRepository[TemperatureReading],
        domain_service: QCDomainService,
        temp_validation_service: TemperatureValidationService,
        audit_service = None,
        notification_service = None
    ):
        self.qc_repository = qc_repository
        self.batch_repository = batch_repository
        self.temperature_repository = temperature_repository
        self.domain_service = domain_service
        self.temp_validation_service = temp_validation_service
        self.audit_service = audit_service
        self.notification_service = notification_service
        self.logger = logging.getLogger("qc.workflow.service")
    
    async def create_qc_record(
        self,
        batch_id: str,
        facility_id: str,
        check_type: str,
        performed_by: str,
        temperature_readings: Optional[List[Dict[str, Any]]] = None,
        visual_inspection: Optional[Dict[str, Any]] = None,
        sensory_evaluation: Optional[Dict[str, Any]] = None,
        microbiological_tests: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete QC record creation workflow
        """
        try:
            # Validate batch exists and is ready for QC
            batch = await self.batch_repository.get_by_id(batch_id)
            if not batch:
                return ResponseBuilder().error(f"Batch {batch_id} not found").add_error(
                    code="BATCH_NOT_FOUND",
                    message=f"Batch with ID {batch_id} was not found",
                    error_type=ErrorType.NOT_FOUND_ERROR,
                    details={"batch_id": batch_id}
                ).build().dict()
            
            if batch.qc_completed:
                return ResponseBuilder().warning(
                    f"Batch {batch.batch_number} already has QC completed"
                ).data(batch.dict()).build().dict()
            
            # Create temperature reading objects
            processed_readings = []
            validation_results = []
            
            if temperature_readings:
                for temp_data in temperature_readings:
                    reading = TemperatureReading(
                        facility_id=facility_id,
                        batch_id=batch_id,
                        unit_type=temp_data['unit_type'],
                        temperature_celsius=temp_data['temperature_celsius'],
                        target_min=temp_data['target_min'],
                        target_max=temp_data['target_max'],
                        validation_result=temp_data.get('validation_result', 'PASS'),
                        notes=temp_data.get('notes'),
                        monitored_by=temp_data.get('monitored_by', performed_by),
                        device_id=temp_data.get('device_id')
                    )
                    
                    # Validate temperature using domain service
                    temp_validations = await self.domain_service.validate_temperature_reading(reading)
                    validation_results.extend(temp_validations)
                    
                    # Apply SOP validation result
                    reading.validation_result = reading.validate_against_sop()
                    
                    processed_readings.append(reading)
            
            # Create QC record entity
            qc_record = QCRecord(
                facility_id=facility_id,
                batch_id=batch_id,
                product_id=batch.product_id,
                check_type=check_type,
                temperature_readings=processed_readings,
                visual_inspection=visual_inspection or {},
                sensory_evaluation=sensory_evaluation or {},
                microbiological_tests=microbiological_tests or {},
                qc_performed_by=performed_by,
                metadata={
                    'workflow_version': '2.0',
                    'validation_results': [v.dict() for v in validation_results]
                }
            )
            
            # Calculate overall result
            qc_record.overall_result = qc_record.calculate_overall_result()
            
            # Evaluate retention requirements
            retention_validations = await self.domain_service.calculate_retention_required(qc_record)
            qc_record.requires_retention = any(not v.is_valid for v in retention_validations)
            qc_record.retention_reasons = [v.message for v in retention_validations if not v.is_valid]
            
            # Schedule next check
            qc_record.next_check_date = await self.domain_service.schedule_follow_up_checks(qc_record)
            
            # Save QC record with audit trail
            saved_record = await self.qc_repository.create_with_audit(
                entity=qc_record,
                created_by=performed_by
            )
            
            # Save temperature readings
            for reading in processed_readings:
                await self.temperature_repository.create(reading)
            
            # Update batch status if QC is completed
            if qc_record.overall_result in [ValidationLevel.PASS, ValidationLevel.WARNING]:
                batch.qc_completed = True
                batch.qc_result = qc_record.overall_result
                await self.batch_repository.update_with_audit(
                    entity_id=batch.id,
                    updates={
                        'qc_completed': True,
                        'qc_result': qc_record.overall_result,
                        'status': QCEntityStatus.COMPLETED
                    },
                    updated_by=performed_by
                )
            
            # Generate QC events
            events = await self.domain_service.create_qc_events(saved_record)
            await self._handle_events(events)
            
            # Send notifications for alerts
            if qc_record.overall_result == ValidationLevel.FAIL:
                await self._send_failure_notification(qc_record, batch)
            elif qc_record.temperature_readings and any(
                r.validation_result == ValidationLevel.WARNING for r in qc_record.temperature_readings
            ):
                await self._send_warning_notification(qc_record, batch)
            
            return create_qc_response(
                saved_record.dict(),
                qc_record.overall_result.value
            )
            
        except Exception as e:
            self.logger.error(f"QC record creation failed: {e}")
            return ResponseBuilder().error("Failed to create QC record").add_error(
                code="QC_CREATION_ERROR",
                message=str(e),
                error_type=ErrorType.SYSTEM_ERROR
            ).build().dict()
    
    async def complete_qc_record(
        self,
        qc_record_id: str,
        completed_by: str,
        final_inspection: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete QC record workflow with final validation
        """
        try:
            # Get existing QC record
            qc_record = await self.qc_repository.get_by_id(qc_record_id)
            if not qc_record:
                return ResponseBuilder().error(f"QC record {qc_record_id} not found").add_error(
                    code="QC_NOT_FOUND",
                    message=f"QC record with ID {qc_record_id} was not found",
                    error_type=ErrorType.NOT_FOUND_ERROR
                ).build().dict()
            
            if qc_record.status == QCEntityStatus.COMPLETED:
                return ResponseBuilder().warning(
                    "QC record is already completed"
                ).data(qc_record.dict()).build().dict()
            
            # Apply final inspection results if provided
            if final_inspection:
                qc_record.visual_inspection.update(final_inspection)
            
            # Final validation
            validations = await self.domain_service.validate_qc_completion(qc_record)
            
            # Check for any critical issues
            critical_issues = [v for v in validations if not v.is_valid and v.severity == "critical"]
            if critical_issues:
                return ResponseBuilder().error("Critical validation issues found").add_error(
                    code="CRITICAL_VALIDATION_ISSUES",
                    message="QC record cannot be completed due to critical issues",
                    error_type=ErrorType.BUSINESS_ERROR,
                    details={"issues": [v.message for v in critical_issues]}
                ).build().dict()
            
            # Update QC record status
            qc_record.status = QCEntityStatus.COMPLETED
            qc_record.updated_by = completed_by
            
            # Recalculate final results
            qc_record.overall_result = qc_record.calculate_overall_result()
            qc_record.requires_retention = any(
                r not in [ValidationLevel.PASS, ValidationLevel.WARNING] 
                for r in [qc_record.overall_result] + [r.validation_result for r in qc_record.temperature_readings]
            )
            
            # Get batch for status update
            batch = await self.batch_repository.get_by_id(qc_record.batch_id)
            if batch:
                batch.qc_completed = True
                batch.qc_result = qc_record.overall_result
                batch.status = QCEntityStatus.COMPLETED
                
                await self.batch_repository.update_with_audit(
                    entity_id=batch.id,
                    updates={
                        'qc_completed': True,
                        'qc_result': qc_record.overall_result,
                        'status': QCEntityStatus.COMPLETED
                    },
                    updated_by=completed_by
                )
            
            # Save updated QC record
            completed_record = await self.qc_repository.update_with_audit(
                entity_id=qc_record_id,
                updates={
                    'status': QCEntityStatus.COMPLETED,
                    'overall_result': qc_record.overall_result,
                    'requires_retention': qc_record.requires_retention,
                    'updated_by': completed_by,
                    'visual_inspection': qc_record.visual_inspection,
                    'metadata': {
                        **(qc_record.metadata or {}),
                        'validations': [v.dict() for v in validations]
                    }
                },
                updated_by=completed_by
            )
            
            # Generate completion events
            completion_event = QCCompletedEvent(
                aggregate_id=qc_record_id,
                aggregate_type="qc_record",
                event_data={
                    "overall_result": qc_record.overall_result.value,
                    "requires_retention": qc_record.requires_retention,
                    "completed_by": completed_by,
                    "validation_results": [v.dict() for v in validations]
                }
            )
            await self._handle_events([completion_event])
            
            # Send completion notifications
            await self._send_completion_notification(completed_record, batch)
            
            return create_qc_response(
                completed_record.dict(),
                completed_record.overall_result.value
            )
            
        except Exception as e:
            self.logger.error(f"QC record completion failed: {e}")
            return ResponseBuilder().error("Failed to complete QC record").add_error(
                code="QC_COMPLETION_ERROR",
                message=str(e),
                error_type=ErrorType.SYSTEM_ERROR
            ).build().dict()
    
    async def get_qc_dashboard_data(
        self,
        facility_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get QC dashboard data for reporting
        """
        try:
            # Get compliance summary
            compliance_data = await self.qc_repository.get_compliance_summary(
                facility_id, start_date, end_date
            )
            
            # Get recent QC records
            recent_records = await self.qc_repository.get_records_by_facility(
                facility_id, start_date, end_date
            )
            
            # Get temperature anomalies
            anomaly_readings = await self.temperature_repository.get_anomaly_readings(
                facility_id, hours_back=24
            )
            
            # Get pending QC tasks
            pending_tasks = await self.qc_repository.get_pending_records(facility_id)
            
            # Calculate trends
            trends = self._calculate_qc_trends(recent_records)
            
            return ResponseBuilder().success("QC dashboard data retrieved").data({
                "compliance_summary": compliance_data,
                "recent_records": [r.dict() for r in recent_records[:10]],
                "temperature_anomalies": [r.dict() for r in anomaly_readings],
                "pending_tasks": [r.dict() for r in pending_tasks],
                "trends": trends,
                "facility_id": facility_id,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            }).build().dict()
            
        except Exception as e:
            self.logger.error(f"Dashboard data retrieval failed: {e}")
            return ResponseBuilder().error("Failed to retrieve dashboard data").add_error(
                code="DASHBOARD_ERROR",
                message=str(e),
                error_type=ErrorType.SYSTEM_ERROR
            ).build().dict()
    
    async def _handle_events(self, events: List[QCEvent]):
        """Handle domain events generated during workflow"""
        try:
            for event in events:
                # Store event in repository
                await self.qc_repository.create(event)
                
                # Trigger notifications based on event type
                if event.event_type == "temperature_alert":
                    await self._send_temperature_alert(event)
                elif event.event_type == "qc_completed":
                    await self._send_qc_completion_event(event)
                
                self.logger.info(f"Handled event: {event.event_type} for {event.entity_id}")
            
        except Exception as e:
            self.logger.error(f"Event handling failed: {e}")
            # Don't fail the main workflow for event handling issues
    
    async def _send_failure_notification(self, qc_record: QCRecord, batch: QCBatch):
        """Send failure notification"""
        if self.notification_service:
            try:
                await self.notification_service.send_qc_failure_notification(
                    qc_record=qc_record,
                    batch=batch,
                    facility_id=qc_record.facility_id
                )
                self.logger.info(f"Failure notification sent for batch {batch.batch_number}")
            except Exception as e:
                self.logger.error(f"Failed to send failure notification: {e}")
    
    async def _send_warning_notification(self, qc_record: QCRecord, batch: QCBatch):
        """Send warning notification"""
        if self.notification_service:
            try:
                await self.notification_service.send_qc_warning_notification(
                    qc_record=qc_record,
                    batch=batch,
                    facility_id=qc_record.facility_id
                )
                self.logger.info(f"Warning notification sent for batch {batch.batch_number}")
            except Exception as e:
                self.logger.error(f"Failed to send warning notification: {e}")
    
    async def _send_completion_notification(self, qc_record: QCRecord, batch: QCBatch):
        """Send completion notification"""
        if self.notification_service:
            try:
                await self.notification_service.send_qc_completion_notification(
                    qc_record=qc_record,
                    batch=batch,
                    facility_id=qc_record.facility_id
                )
                self.logger.info(f"Completion notification sent for batch {batch.batch_number}")
            except Exception as e:
                self.logger.error(f"Failed to send completion notification: {e}")
    
    def _calculate_qc_trends(self, records: List[QCRecord]) -> Dict[str, Any]:
        """Calculate QC trends from records"""
        if not records:
            return {"trend": "stable", "daily_rates": []}
        
        # Group by day
        daily_data = {}
        for record in records:
            date_key = record.created_at.date()
            if date_key not in daily_data:
                daily_data[date_key] = {"pass": 0, "warning": 0, "fail": 0}
            
            daily_data[date_key][record.overall_result.value.lower()] += 1
        
        # Calculate pass rates and trend
        daily_rates = []
        pass_rates = []
        
        for date, data in sorted(daily_data.items()):
            total = sum(data.values())
            pass_rate = (data["pass"] / total) * 100 if total > 0 else 0
            pass_rates.append(pass_rate)
            
            daily_rates.append({
                "date": date.isoformat(),
                "pass_rate": round(pass_rate, 2),
                "total_checks": total,
                "pass_count": data["pass"],
                "warning_count": data["warning"],
                "fail_count": data["fail"]
            })
        
        # Determine trend
        trend = "stable"
        if len(pass_rates) >= 2:
            if pass_rates[-1] > pass_rates[-2] + 5:
                trend = "improving"
            elif pass_rates[-1] < pass_rates[-2] - 5:
                trend = "declining"
        
        return {
            "trend": trend,
            "daily_rates": daily_rates,
            "current_pass_rate": pass_rates[-1] if pass_rates else 0
        }