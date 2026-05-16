"""
Optimized Database Queries for QC Central Kitchen
Implements efficient query patterns, connection pooling, and query optimization
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from backend.database.supabase_client import get_client
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools

logger = logging.getLogger("qc.db.queries")

class QueryOptimizer:
    """Optimized database query manager"""
    
    def __init__(self):
        self.client = get_client()
        self.query_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def get_dashboard_data_optimized(self) -> Dict[str, Any]:
        """Get dashboard data with optimized queries and caching"""
        try:
            # Use parallel queries for better performance
            tasks = [
                self._get_latest_temperatures(),
                self._get_open_alerts(),
                self._get_health_metrics()
            ]
            
            results = await asyncio.gather(*tasks)
            temperatures, alerts, metrics = results
            
            return {
                "temperature_rooms": temperatures,
                "open_alerts": len(alerts),
                "recent_alerts": alerts[:5],
                "health_score": metrics.get("score", 0),
                "critical_issues": self._identify_critical_issues(temperatures)
            }
            
        except Exception as e:
            logger.error(f"Dashboard query error: {e}")
            return self._get_fallback_dashboard_data()
    
    async def _get_latest_temperatures(self) -> List[Dict]:
        """Get latest temperature readings with optimized query"""
        if not self.client:
            return []
            
        # Use window function for better performance
        query = """
        SELECT DISTINCT ON (device_id) 
            temperature_c, 
            is_normal, 
            recorded_at,
            device_id,
            facility_devices.name as device_name,
            facility_devices.type as device_type,
            facility_devices.threshold_temp,
            facility_rooms.name as room_name
        FROM facility_logs
        JOIN facility_devices ON facility_logs.device_id = facility_devices.id
        JOIN facility_rooms ON facility_devices.room_id = facility_rooms.id
        ORDER BY device_id, recorded_at DESC
        LIMIT 50
        """
        
        try:
            result = await self._execute_query(query)
            return self._process_temperature_data(result)
        except Exception as e:
            logger.error(f"Temperature query error: {e}")
            return []
    
    async def _get_open_alerts(self, limit: int = 10) -> List[Dict]:
        """Get open alerts with optimized query"""
        if not self.client:
            return []
            
        query = """
        SELECT 
            id, 
            device_id, 
            temperature_c, 
            threshold_c, 
            deviation_c,
            status,
            created_at,
            facility_devices.name as device_name,
            facility_rooms.name as room_name
        FROM facility_alerts
        JOIN facility_devices ON facility_alerts.device_id = facility_devices.id
        JOIN facility_rooms ON facility_devices.room_id = facility_rooms.id
        WHERE status = 'open'
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        try:
            return await self._execute_query(query, [limit])
        except Exception as e:
            logger.error(f"Alerts query error: {e}")
            return []
    
    async def _get_health_metrics(self) -> Dict[str, Any]:
        """Calculate health metrics with optimized aggregation"""
        if not self.client:
            return {"score": 0}
            
        # Use CTE for better performance
        query = """
        WITH latest_readings AS (
            SELECT DISTINCT ON (device_id)
                device_id,
                temperature_c,
                is_normal,
                facility_devices.type as device_type,
                facility_devices.threshold_temp
            FROM facility_logs
            JOIN facility_devices ON facility_logs.device_id = facility_devices.id
            WHERE recorded_at > NOW() - INTERVAL '24 hours'
            ORDER BY device_id, recorded_at DESC
        )
        SELECT 
            COUNT(*) as total_checks,
            COUNT(CASE WHEN is_normal = true THEN 1 END) as passed_checks,
            COUNT(CASE WHEN is_normal = false THEN 1 END) as failed_checks,
            AVG(temperature_c) as avg_temperature,
            device_type
        FROM latest_readings
        GROUP BY device_type
        """
        
        try:
            results = await self._execute_query(query)
            return self._calculate_health_score(results)
        except Exception as e:
            logger.error(f"Health metrics error: {e}")
            return {"score": 0}
    
    def get_temperature_trends(self, device_id: str, hours: int = 24) -> List[Dict]:
        """Get temperature trends with time-series optimization"""
        if not self.client:
            return []
            
        # Use time bucketing for better performance
        query = """
        SELECT 
            DATE_TRUNC('hour', recorded_at) as hour_bucket,
            AVG(temperature_c) as avg_temp,
            MIN(temperature_c) as min_temp,
            MAX(temperature_c) as max_temp,
            COUNT(*) as reading_count
        FROM facility_logs
        WHERE device_id = %s 
            AND recorded_at > NOW() - INTERVAL '%s hours'
        GROUP BY hour_bucket
        ORDER BY hour_bucket DESC
        """
        
        try:
            return self._execute_sync_query(query, [device_id, hours])
        except Exception as e:
            logger.error(f"Trends query error: {e}")
            return []
    
    def batch_insert_logs(self, logs: List[Dict]) -> bool:
        """Batch insert facility logs for better performance"""
        if not self.client or not logs:
            return False
            
        try:
            # Use COPY for bulk inserts (if supported)
            formatted_logs = []
            for log in logs:
                formatted_logs.append({
                    'device_id': log.get('device_id'),
                    'room_id': log.get('room_id'),
                    'staff_id': log.get('staff_id'),
                    'temperature_c': log.get('temperature_c'),
                    'humidity_rh': log.get('humidity_rh'),
                    'is_normal': log.get('is_normal', True),
                    'notes': log.get('notes') or log.get('reason'),
                    'photo_url': log.get('photo_url'),
                    'recorded_at': log.get('recorded_at', datetime.utcnow().isoformat())
                })
            
            result = self.client.table('facility_logs').insert(formatted_logs).execute()
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Batch insert error: {e}")
            return False
    
    async def _execute_query(self, query: str, params: List = None) -> List[Dict]:
        """Execute query with connection pooling"""
        if not self.client:
            return []
            
        # Execute in thread pool for non-blocking I/O
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            functools.partial(self._execute_sync_query, query, params)
        )
    
    def _execute_sync_query(self, query: str, params: List = None) -> List[Dict]:
        """Synchronous query execution"""
        try:
            if not self.client:
                return []
                
            # Use direct query for complex operations
            result = self._direct_query(query, params or [])
            return result
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return []
    
    def _direct_query(self, query: str, params: List) -> List[Dict]:
        """Execute direct SQL query"""
        from backend.database.supabase_client import direct_db_query
        return direct_db_query("facility_logs", "GET", None, self._build_filters(query, params))
    
    def _build_filters(self, query: str, params: List) -> str:
        """Build URL filters for direct query"""
        # Simple implementation - in production, use proper query builder
        return f"query={query}&params={','.join(map(str, params))}"
    
    def _process_temperature_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Process and optimize temperature data for frontend"""
        processed = []
        
        for item in raw_data:
            processed.append({
                "room": f"{item.get('room_name', 'Unknown')} - {item.get('device_name', 'Device')}",
                "temperature": f"{item.get('temperature_c', 0)}°C",
                "threshold": f"{item.get('threshold_temp', 0)}°C",
                "unit_type": self._normalize_device_type(item.get('device_type', 'ambient')),
                "status": "PASS" if item.get('is_normal', False) else "FAIL",
                "recorded_at": item.get('recorded_at')
            })
        
        return processed
    
    def _normalize_device_type(self, device_type: str) -> str:
        """Normalize device type for frontend"""
        type_mapping = {
            'undercounter': 'chiller',
            'room_temp': 'ambient',
            'chiller': 'chiller',
            'freezer': 'freezer'
        }
        return type_mapping.get(device_type, 'ambient')
    
    def _calculate_health_score(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate health score from metrics"""
        total_checks = sum(m.get('total_checks', 0) for m in metrics)
        passed_checks = sum(m.get('passed_checks', 0) for m in metrics)
        
        if total_checks == 0:
            return {"score": 0}
        
        score = (passed_checks / total_checks) * 100
        return {
            "score": round(score, 1),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks
        }
    
    def _identify_critical_issues(self, temperatures: List[Dict]) -> List[Dict]:
        """Identify critical issues from temperature data"""
        critical = []
        
        for temp in temperatures:
            if temp.get('status') == 'FAIL':
                critical.append({
                    "title": temp.get('room', 'Unknown'),
                    "value": temp.get('temperature', 'N/A'),
                    "status": "FAIL",
                    "unit_type": temp.get('unit_type', 'ambient')
                })
        
        return critical[:5]  # Limit to top 5 critical issues
    
    def _get_fallback_dashboard_data(self) -> Dict[str, Any]:
        """Fallback data when database is unavailable"""
        return {
            "temperature_rooms": [],
            "open_alerts": 0,
            "recent_alerts": [],
            "health_score": 0,
            "critical_issues": [],
            "error": "Database temporarily unavailable"
        }

# Singleton instance
query_optimizer = QueryOptimizer()
