import logging

from backend.database.supabase_client import get_client
from backend.services.approval_service import ApprovalService
from backend.services.base_service import BaseService
from backend.services.dashboard_service import DashboardService
from backend.services.google_apps_script_service import send_monitoring_log, send_qc_finding, send_qc_report
from backend.services.monitoring_service import MonitoringService
from backend.services.product_service import ProductService
from backend.services.report_service import ReportService

logger = logging.getLogger("qc.services.admin")

__all__ = [
    "AdminService",
    "send_monitoring_log",
    "send_qc_finding",
    "send_qc_report",
]


class AdminService(BaseService):
    def __init__(self, sb_client=None):
        sb_client = sb_client or get_client()
        super().__init__(sb_client)

        self.dashboard_service = DashboardService(sb_client)
        self.monitoring_service = MonitoringService(sb_client)
        self.report_service = ReportService(sb_client)
        self.approval_service = ApprovalService(sb_client)
        self.product_service = ProductService(sb_client)

    # 1. Dashboard Service Delegation
    def get_dashboard_overview(self):
        return self.dashboard_service.get_dashboard_overview()

    # 2. Monitoring Service Delegation
    def get_realtime_monitoring(self):
        return self.monitoring_service.get_realtime_monitoring()

    def get_daily_monitoring(self, date=None):
        return self.monitoring_service.get_daily_monitoring(date)

    # 3. Report Service Delegation
    def get_qc_reports(self, page=1, limit=20, status_filter=None):
        return self.report_service.get_qc_reports(page=page, limit=limit, status_filter=status_filter)

    def get_traceability(self, barcode=None, limit=50):
        return self.report_service.get_traceability(barcode=barcode, limit=limit)

    def get_batch_production(self, date=None, status_filter=None, search=None, limit=200):
        return self.report_service.get_batch_production(
            date=date, status_filter=status_filter, search=search, limit=limit
        )

    def get_audit_trail(self, limit=50, date=None, action=None, user=None):
        return self.report_service.get_audit_trail(limit=limit, date=date, action=action, user=user)

    def get_temperature_report(self, limit=100, date=None, staff_id=None, status_filter=None):
        return self.report_service.get_temperature_report(
            limit=limit, date=date, staff_id=staff_id, status_filter=status_filter
        )

    def get_alert_report(self, limit=100):
        return self.report_service.get_alert_report(limit=limit)

    def export_google_sheets_monitoring(self, start_date=None, end_date=None, limit=5000):
        return self.report_service.export_google_sheets_monitoring(
            start_date=start_date, end_date=end_date, limit=limit
        )

    def export_google_sheets_qc(self, start_date=None, end_date=None, limit=5000):
        return self.report_service.export_google_sheets_qc(start_date=start_date, end_date=end_date, limit=limit)

    def get_inspection_report(self, limit=100, status_filter=None, date=None, staff_id=None):
        return self.report_service.get_inspection_report(
            limit=limit, status_filter=status_filter, date=date, staff_id=staff_id
        )

    def get_findings_report(self, limit=100, date=None, staff_id=None, status_filter=None):
        return self.report_service.get_findings_report(
            limit=limit, date=date, staff_id=staff_id, status_filter=status_filter
        )

    def get_evidence_report(self, limit=100, date=None, staff_id=None):
        return self.report_service.get_evidence_report(limit=limit, date=date, staff_id=staff_id)

    def get_daily_staff_report(self, date=None, staff_id=None, status_filter=None, limit=500):
        return self.report_service.get_daily_staff_report(
            date=date, staff_id=staff_id, status_filter=status_filter, limit=limit
        )

    def export_daily_report_csv(self, date=None, staff_id=None, status_filter=None):
        return self.report_service.export_daily_report_csv(date=date, staff_id=staff_id, status_filter=status_filter)

    def get_batch_report(self, limit=100):
        return self.report_service.get_batch_report(limit=limit)

    def get_staff_activity_report(self, limit=100):
        return self.report_service.get_staff_activity_report(limit=limit)

    # 4. Approval Service Delegation
    def get_pending_approvals(self, limit=50):
        return self.approval_service.get_pending_approvals(limit=limit)

    def get_approval_detail(self, approval_id):
        return self.approval_service.get_approval_detail(approval_id)

    def approve_item(self, approval_id, actor_id=None, comment=None, approved=True):
        return self.approval_service.approve_item(approval_id, actor_id=actor_id, comment=comment, approved=approved)

    def update_qc_finding_status(self, finding_id, status):
        return self.approval_service.update_qc_finding_status(finding_id, status)

    # 5. Product Service Delegation
    def list_products(self):
        return self.product_service.list_products()

    def create_product(self, payload):
        return self.product_service.create_product(payload)

    def update_product(self, product_id, payload):
        return self.product_service.update_product(product_id, payload)

    def delete_product(self, product_id):
        return self.product_service.delete_product(product_id)
