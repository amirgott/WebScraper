from PIL import Image
from typing import List
import numpy as np

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("Warning: EasyOCR not available. Image text extraction will be disabled.")

class OCRService:
    def __init__(self):
        # Initialize EasyOCR with Hebrew and English support
        if EASYOCR_AVAILABLE:
            try:
                self.reader = easyocr.Reader(['he', 'en'])
            except Exception as e:
                print(f"Warning: Failed to initialize EasyOCR: {e}")
                self.reader = None
        else:
            self.reader = None

    def extract_text(self, image: Image.Image) -> str:
        """
        Extract text from image using EasyOCR.
        """
        if not self.reader:
            print("OCR reader not available")
            return ""

        try:
            # Convert PIL image to numpy array
            image_array = np.array(image)

            # Perform OCR
            results = self.reader.readtext(image_array)

            # Extract text from results
            extracted_texts = [result[1] for result in results if result[2] > 0.5]  # Filter by confidence

            return '\n'.join(extracted_texts)

        except Exception as e:
            print(f"Error in OCR extraction: {e}")
            return ""

    def extract_text_with_bounds(self, image: Image.Image) -> List[dict]:
        """
        Extract text with bounding boxes from image.
        """
        if not self.reader:
            print("OCR reader not available")
            return []

        try:
            image_array = np.array(image)
            results = self.reader.readtext(image_array)

            formatted_results = []
            for result in results:
                if result[2] > 0.5:  # Filter by confidence
                    formatted_results.append({
                        'text': result[1],
                        'confidence': result[2],
                        'bbox': result[0]
                    })

            return formatted_results

        except Exception as e:
            print(f"Error in OCR extraction with bounds: {e}")
            return []
