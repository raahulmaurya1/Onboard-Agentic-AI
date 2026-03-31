import io
import fitz  # PyMuPDF
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def standardize_to_png(file_bytes: bytes, mime_type: str) -> bytes:
    """
    Takes raw bytes and true mime_type.
    If PDF: rasterizes the very first page to high-res PNG.
    If Image (JPEG/PNG/etc): normalizes to standard RGB PNG.
    Returns standard PNG bytes.
    """
    try:
        if 'pdf' in mime_type.lower():
            # Open PDF from bytes
            pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
            if not pdf_document.page_count:
                raise ValueError("PDF is empty")
            
            # Load first page
            page = pdf_document.load_page(0)
            
            # Render to pixmap with high resolution (DPI ~300)
            matrix = fitz.Matrix(3.0, 3.0) 
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            output_io = io.BytesIO()
            img.save(output_io, format="PNG")
            return output_io.getvalue()
            
        elif 'image' in mime_type.lower():
            # Open image from bytes
            img = Image.open(io.BytesIO(file_bytes))
            
            # Convert to standard RGB to drop transparency/alpha if present implicitly
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
                
            output_io = io.BytesIO()
            img.save(output_io, format="PNG")
            return output_io.getvalue()
            
        else:
            raise ValueError(f"Unsupported file type for standardization: {mime_type}")
            
    except Exception as e:
        logger.error(f"Standardization failed: {e}")
        raise
