import logging
from datetime import datetime, timezone
from flask import jsonify

from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.service.admin")

class AdminService:
    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()

    def get_dashboard_overview(self):
        """Aggregate data for admin dashboard overview."""
        try:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # 1. Total batches today
            batches_res = self.sb.table("production_batches").select("id", count="exact").eq("production_date", today_str).execute()
            total_batches_today = batches_res.count if hasattr(batches_res, 'count') else 0
            if total_batches_today is None and batches_res.data:
                total_batches_today = len(batches_res.data)

            # 2. Total QC Pending vs Completed for today
            # Assuming pending if status == 'open' or final_qc_status == 'pending'
            pending_res = self.sb.table("production_batches").select("id", count="exact").eq("final_qc_status", "pending").execute()
            total_pending = pending_res.count if hasattr(pending_res, 'count') and pending_res.count is not None else (len(pending_res.data) if pending_res.data else 0)

            completed_res = self.sb.table("production_batches").select("id", count="exact").neq("final_qc_status", "pending").execute()
            total_completed = completed_res.count if hasattr(completed_res, 'count') and completed_res.count is not None else (len(completed_res.data) if completed_res.data else 0)

            # 3. Total open alerts
            alerts_res = self.sb.table("facility_alerts").select("id", count="exact").eq("status", "open").execute()
            total_alerts = alerts_res.count if hasattr(alerts_res, 'count') and alerts_res.count is not None else (len(alerts_res.data) if alerts_res.data else 0)

            # 4. Total staff
            staff_res = self.sb.table("staff_accounts").select("id", count="exact").eq("is_active", True).execute()
            total_staff = staff_res.count if hasattr(staff_res, 'count') and staff_res.count is not None else (len(staff_res.data) if staff_res.data else 0)

            return {
                "success": True,
                "data": {
                    "total_batches_today": total_batches_today,
                    "total_qc_pending": total_pending,
                    "total_qc_completed": total_completed,
                    "total_open_alerts": total_alerts,
                    "total_active_staff": total_staff,
                }
            }
        except Exception as e:
            logger.error("Error in get_dashboard_overview: %s", e)
            return {"success": False, "detail": str(e)}

    def get_realtime_monitoring(self):
        """Fetch latest temperatures from all facility devices."""
        try:
            # We get devices and their latest logs
            devices_res = self.sb.table("facility_devices").select("id, name, type, threshold_temp, facility_rooms(name)").eq("is_active", True).execute()
            devices = devices_res.data or []

            # Enhance with latest log for each
            # Ideally this is a view in DB, but for now we loop or use a query if possible
            for dev in devices:
                logs_res = self.sb.table("facility_logs").select("temperature_c, is_normal, recorded_at").eq("device_id", dev["id"]).order("recorded_at", desc=True).limit(1).execute()
                dev["latest_log"] = logs_res.data[0] if logs_res.data else None

            return {"success": True, "data": devices}
        except Exception as e:
            logger.error("Error in get_realtime_monitoring: %s", e)
            return {"success": False, "detail": str(e)}

    def get_qc_reports(self, page=1, limit=20, status_filter=None):
        """Get paginated QC reports."""
        try:
            offset = (page - 1) * limit
            query = self.sb.table("production_batches").select("*, products(product_name, sku_code), staff_accounts!operator_id(full_name, username)", count="exact")
            if status_filter:
                query = query.eq("final_qc_status", status_filter)
            
            res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            return {"success": True, "data": res.data, "count": res.count if hasattr(res, 'count') else len(res.data)}
        except Exception as e:
            logger.error("Error in get_qc_reports: %s", e)
            return {"success": False, "detail": str(e)}

    def get_audit_trail(self, limit=50):
        """Get recent audit trail logs."""
        try:
            res = self.sb.table("audit_trail").select("*, staff_accounts(username)").order("created_at", desc=True).limit(limit).execute()
            return {"success": True, "data": res.data}
        except Exception as e:
            logger.error("Error in get_audit_trail: %s", e)
            return {"success": False, "detail": str(e)}
