import os
from google.cloud import vision
import io

class VisionHelper:
    """
    Helper for Google Cloud Vision API integration.
    Used for extracting temperatures from thermometer photos.
    """
    def __init__(self, credentials_path=None):
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        self.client = vision.ImageAnnotatorClient()

    def extract_text(self, content):
        image = vision.Image(content=content)
        response = self.client.text_detection(image=image)
        texts = response.text_annotations
        
        if response.error.message:
            raise Exception(f"Vision API Error: {response.error.message}")

        return texts[0].description if texts else ""

    def parse_temperature(self, text):
        import re
        # Look for patterns like 4.2, 75.0, -18.5
        match = re.search(r'(-?\d{1,3}[\.,]\d)', text)
        if match:
            return float(match.group(0).replace(',', '.'))
        return None
