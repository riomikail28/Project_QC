import requests
import json

class WhatsAppService:
    """
    Integration for sending critical QC alerts via WhatsApp.
    Currently configured as a mock/base for Twilio or Fonnte.
    """
    def __init__(self, api_key=None, phone_number=None):
        self.api_key = api_key
        self.target_phone = phone_number

    def send_critical_alert(self, zone, temp, timestamp):
        message = (
            f"🚨 *CRITICAL QC ALERT*\n\n"
            f"Area: {zone}\n"
            f"Suhu: {temp}°C\n"
            f"Waktu: {timestamp}\n\n"
            f"⚠️ *SOP ACTION REQUIRED:* Segera periksa unit pendingin!"
        )
        
        print(f"[WA MOCK] Sending to {self.target_phone}: {message}")
        # actual implementation:
        # requests.post(API_URL, data={"to": self.target_phone, "text": message})
        return True

    def send_batch_report(self, batch_code, status, score):
        message = (
            f"✅ *BATCH COMPLETED*\n\n"
            f"Batch: {batch_code}\n"
            f"Status: {status}\n"
            f"QC Score: {score}/100"
        )
        print(f"[WA MOCK] Sending report: {message}")
        return True
