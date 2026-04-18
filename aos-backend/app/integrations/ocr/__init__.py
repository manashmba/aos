"""OCR integration for invoice/receipt extraction."""
from app.integrations.ocr.protocol import OCRProvider, OCRResult
from app.integrations.ocr.mock import MockOCRProvider

__all__ = ["OCRProvider", "OCRResult", "MockOCRProvider"]
