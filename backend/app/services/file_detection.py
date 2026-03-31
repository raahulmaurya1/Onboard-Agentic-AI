import io
from magika import Magika
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Initialize Magika once globally to reuse the loaded model
magika_detector = Magika()

def detect_file_type(file_bytes: bytes) -> str:
    """
    Analyzes raw file bytes returning the true MIME type 
    to prevent file extension spoofing (e.g. .exe masquerading as .pdf).
    """
    try:
        # get_result_from_bytes expects bytes and returns MagikaResult
        result = magika_detector.identify_bytes(file_bytes)
        
        if result and hasattr(result.output, 'mime_type'):
            mime_type = result.output.mime_type
            return mime_type
        
        raise ValueError("Could not determine file type.")
    except Exception as e:
        logger.error(f"Magika file detection failed: {e}")
        raise HTTPException(status_code=400, detail="Failed to safely detect file type")
