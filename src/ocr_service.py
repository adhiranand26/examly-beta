import logging
import pytesseract
from PIL import Image, ImageEnhance

class OCRService:
    @staticmethod
    def preprocess_image(img: Image.Image) -> Image.Image:
        # High contrast grayscale preprocessing
        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.0)
        return img

    @staticmethod
    def extract_structured(img: Image.Image) -> dict:
        """
        Returns structured OCR output with confidence scores.
        """
        try:
            processed = OCRService.preprocess_image(img)
            # Fetch verbose bounding box data to calculate confidence
            data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
            
            text_blocks = []
            total_conf = 0
            count = 0
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                if text and conf > -1:
                    text_blocks.append(text)
                    total_conf += conf
                    count += 1
            
            avg_conf = (total_conf / count / 100.0) if count > 0 else 0.0
            full_text = " ".join(text_blocks)
            
            return {
                "text": full_text,
                "confidence": round(avg_conf, 2),
                "blocks": text_blocks
            }
        except Exception as e:
            logging.error(f"OCR failure: {e}")
            return {"text": "", "confidence": 0.0, "blocks": []}
