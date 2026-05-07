"""Alert service for sending notifications to Slack and PagerDuty."""

import os
import http.client
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertService:
    """Service for sending alerts to various channels."""

    def __init__(self):
        self.slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        self.pagerduty_key = os.environ.get('PAGERDUTY_INTEGRATION_KEY')
        self.enabled = bool(self.slack_webhook_url or self.pagerduty_key)

    def send_slack_alert(self, message: str, severity: str = 'warning', context: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert to Slack channel."""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        try:
            # Map severity to color
            color_map = {
                'critical': 'danger',
                'warning': 'warning',
                'info': 'good',
            }
            color = color_map.get(severity, 'warning')

            payload = {
                "text": f"[{severity.upper()}] QC System Alert",
                "attachments": [{
                    "color": color,
                    "fields": [{
                        "title": "Message",
                        "value": message,
                        "short": False
                    }],
                    "footer": "QC System",
                    "ts": datetime.now().timestamp()
                }]
            }

            # Add context if provided
            if context:
                for key, value in context.items():
                    payload['attachments'][0]['fields'].append({
                        'title': key,
                        'value': str(value),
                        'short': True
                    })

            # Send to Slack
            conn = http.client.HTTPSConnection("hooks.slack.com")
            conn.request("POST", self.slack_webhook_url, json.dumps(payload), {
                'Content-Type': 'application/json'
            })
            response = conn.getresponse()
            conn.close()

            if response.status == 200:
                logger.info("Slack alert sent successfully")
                return True
            else:
                logger.error(f"Failed to send Slack alert: {response.status}")
                return False

        except Exception as e:
            logger.error(f"Error sending Slack alert: {str(e)}")
            return False

    def send_pagerduty_alert(self, message: str, severity: str = 'error', component: Optional[str] = None) -> bool:
        """Send alert to PagerDuty."""
        if not self.pagerduty_key:
            logger.warning("PagerDuty integration key not configured")
            return False

        try:
            # Map severity to event type
            severity_map = {
                'critical': 'critical',
                'warning': 'warning',
                'info': 'info',
                'error': 'error'
            }
            event_type = severity_map.get(severity, 'error')

            payload = {
                "routing_key": self.pagerduty_key,
                "event_action": "trigger",
                "payload": {
                    "summary": f"QC System Alert: {message}",
                    "severity": event_type,
                    "source": component or "qc-backend",
                    "timestamp": datetime.now().isoformat()
                }
            }

            # Send to PagerDuty
            conn = http.client.HTTPSConnection("events.pagerduty.com")
            conn.request("POST", "/v2/enqueue", json.dumps(payload), {
                'Content-Type': 'application/json',
                'Authorization': f'Token token={self.pagerduty_key}'
            })
            response = conn.getresponse()
            conn.close()

            if response.status == 202:  # Accepted
                logger.info("PagerDuty alert sent successfully")
                return True
            else:
                logger.error(f"Failed to send PagerDuty alert: {response.status}")
                return False

        except Exception as e:
            logger.error(f"Error sending PagerDuty alert: {str(e)}")
            return False

    def send_alert(self, message: str, severity: str = 'warning', component: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """Send alert to all configured channels."""
        results = {}

        # Send to Slack
        if self.slack_webhook_url:
            results['slack'] = self.send_slack_alert(message, severity, context)

        # Send to PagerDuty for critical/warning/error
        if self.pagerduty_key and severity in ['critical', 'warning', 'error']:
            results['pagerduty'] = self.send_pagerduty_alert(message, severity, component)

        return results

    def send_task_failure_alert(self, task_name: str, error: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert when a Celery task fails."""
        message = f"Task '{task_name}' failed: {error}"
        ctx = {
            'Task Name': task_name,
            'Error': str(error),
            'Timestamp': datetime.now().isoformat()
        }
        if context:
            ctx.update(context)

        results = self.send_alert(message, severity='error', component='celery-worker', context=ctx)
        return any(results.values())

    def send_backup_failure_alert(self, backup_type: str, error: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert when backup operations fail."""
        message = f"Backup '{backup_type}' failed: {error}"
        ctx = {
            'Backup Type': backup_type,
            'Error': str(error),
            'Timestamp': datetime.now().isoformat()
        }
        if context:
            ctx.update(context)

        results = self.send_alert(message, severity='critical', component='backup-service', context=ctx)
        return any(results.values())


# Singleton instance
alert_service = AlertService()