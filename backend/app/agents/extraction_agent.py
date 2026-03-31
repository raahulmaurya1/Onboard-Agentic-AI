import json
import logging
import google.generativeai as genai
from app.services.gemini_client import gemini_client
import re
import io
import os
import pytesseract
from PIL import Image, ImageEnhance

# Configure Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logger = logging.getLogger(__name__)

async def extract_document_data(file_bytes: bytes, mime_type: str) -> dict:
    """
    Sends the raw document bytes to Gemini Flash to extract structured JSON data.
    """
    prompt = """
    You are an expert OCR and document classification AI for a bank.
    Analyze the attached document and determine if it is a 'PAN', 'Aadhaar', or 'Signature'.
    
    Respond STRICTLY with a JSON object containing two top-level keys:
    1. 'document_type': EXACTLY one of ['PAN', 'Aadhaar', 'Signature', 'Unknown']
    2. 'extracted_fields': A nested JSON object capturing the relevant parameters.
    
    For PAN exclusively, extract:
    - "name"
    - "father_name"
    - "dob"
    - "id_number" (The alphanumeric PAN ID)
    
    For Aadhaar exclusively, extract:
    - "name"
    - "dob"
    - "address" (The full address string)
    - "id_number" (The 12-digit Aadhaar ID)
    
    For Signature, extract:
    - "detected": true or false
    
    If any field is missing or unreadable, set its value to null.
    Do NOT include markdown block formatting (like ```json), just return the raw JSON braces.
    """
    
    try:
        document_part = {
            "mime_type": mime_type,
            "data": file_bytes
        }
        
        response = await gemini_client.model.generate_content_async(
            [prompt, document_part],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        
        extracted_json = json.loads(response.text)
        return extracted_json
        
    except Exception as e:
        logger.error(f"Failed to extract document data: {e}")
        return {"error": "Failed to extract data natively", "details": str(e)}

async def extract_document_data_from_text(text: str) -> dict:
    """
    Sends raw parsed text strings to Gemini Flash to extract structured JSON data.
    """
    prompt = f"""
    You are an expert OCR and document classification AI for a bank.
    Analyze the following document text and determine if it is a 'PAN', 'Aadhaar', or 'Signature'.
    
    Respond STRICTLY with a JSON object containing two top-level keys:
    1. 'document_type': EXACTLY one of ['PAN', 'Aadhaar', 'Signature', 'Unknown']
    2. 'extracted_fields': A nested JSON object capturing the relevant parameters.
    
    For PAN exclusively, extract:
    - "name"
    - "father_name"
    - "dob"
    - "id_number" (The alphanumeric PAN ID)
    
    For Aadhaar exclusively, extract:
    - "name"
    - "dob"
    - "address" (The full address string)
    - "id_number" (The 12-digit Aadhaar ID)
    
    For Signature, extract:
    - "detected": true or false
    
    If any field is missing or unreadable, set its value to null.
    Do NOT include markdown block formatting (like ```json), just return the raw JSON braces.
    
    Document Text:
    {text}
    """
    
    try:
        response = await gemini_client.model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        
        extracted_json = json.loads(response.text)
        return extracted_json
        
    except Exception as e:
        logger.error(f"Failed to extract document data from text: {e}")
        return {"error": "Failed to extract data from text natively", "details": str(e)}


# ─── SYNCHRONOUS VERSIONS FOR CELERY WORKERS ──────────────────────────────────
# Celery workers are synchronous. Using `generate_content_async` inside
# `asyncio.run()` causes 'Event loop is closed' errors due to gRPC internals.
# These sync versions use the blocking `generate_content()` call instead.

def extract_document_data_sync(file_bytes: bytes, mime_type: str) -> dict:
    """
    Synchronous version for use inside Celery background tasks.
    Sends raw document bytes to Gemini Vision to extract structured KYC data.
    """
    prompt = """
    You are an expert OCR and document classification AI for a bank.
    Analyze the attached document and determine if it is a 'PAN', 'Aadhaar', or 'Signature'.
    
    Respond STRICTLY with a JSON object containing two top-level keys:
    1. 'document_type': EXACTLY one of ['PAN', 'Aadhaar', 'Signature', 'Unknown']
    2. 'extracted_fields': A nested JSON object capturing the relevant parameters.
    
    For PAN exclusively, extract:
    - "name"
    - "father_name"
    - "dob"
    - "id_number" (The alphanumeric PAN ID)
    
    For Aadhaar exclusively, extract:
    - "name"
    - "dob"
    - "address" (The full address string)
    - "id_number" (The 12-digit Aadhaar ID)
    
    For Signature, extract:
    - "detected": true or false
    
    If any field is missing or unreadable, set its value to null.
    Do NOT include markdown block formatting (like ```json), just return the raw JSON braces.
    """
    try:
        document_part = {"mime_type": mime_type, "data": file_bytes}
        response = gemini_client.model.generate_content(
            [prompt, document_part],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"[Sync] Failed to extract document data via Vision: {e}")
        return {"error": "Failed to extract data natively", "details": str(e)}


def extract_document_data_from_text_sync(text: str) -> dict:
    """
    Synchronous version for use inside Celery background tasks.
    Sends plain text to Gemini to extract structured KYC data.
    """
    prompt = f"""
    You are an expert OCR and document classification AI for a bank.
    Analyze the following document text and determine if it is a 'PAN', 'Aadhaar', or 'Signature'.
    
    Respond STRICTLY with a JSON object containing two top-level keys:
    1. 'document_type': EXACTLY one of ['PAN', 'Aadhaar', 'Signature', 'Unknown']
    2. 'extracted_fields': A nested JSON object capturing the relevant parameters.
    
    For PAN exclusively, extract:
    - "name"
    - "father_name"
    - "dob"
    - "id_number" (The alphanumeric PAN ID)
    
    For Aadhaar exclusively, extract:
    - "name"
    - "dob"
    - "address" (The full address string)
    - "id_number" (The 12-digit Aadhaar ID)
    
    If any field is missing or unreadable, set its value to null.
    Do NOT include markdown block formatting (like ```json), just return the raw JSON braces.
    
    Document Text:
    {text}
    """
    try:
        response = gemini_client.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"[Sync] Failed to extract document data from text: {e}")
        return {"error": "Failed to extract data from text natively", "details": str(e)}

def extract_and_classify_local(image_bytes: bytes) -> dict:
    """
    Tier 0: Strictly local extraction using Tesseract OCR and PIL Preprocessing.
    Enhanced to extract DOB, IDs, Name, Father's Name, and cleaned Address.
    """
    try:
        # 1. Load the image with PIL
        img = Image.open(io.BytesIO(image_bytes))
        
        # 2. Preprocessing: Convert to Grayscale
        img = img.convert('L')
        
        # 3. Preprocessing: Boost Contrast (2.0x)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # 4. Extract text via Tesseract
        raw_text = pytesseract.image_to_string(img)
        raw_text = raw_text.strip()
        logger.info(f"[OnboardAI][TESSERACT_OCR] Raw text length: {len(raw_text)}")
        
        # 5. Advanced Field Extraction
        # DOB: Strict format-bound
        dob_match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', raw_text)
        # PAN ID
        pan_match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', raw_text.upper())
        # Aadhaar ID
        aadhaar_match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', raw_text)
        # Address (Aadhaar): Strictly look for "Address:" (with colon) followed by spaces/newlines
        address_match = re.search(r'\bAddress:[\s\n]+(.*?\d{6})', raw_text, re.DOTALL)
        
        dob = dob_match.group(1).strip() if dob_match else None
        pan_id = pan_match.group() if pan_match else None
        aadhar_id = re.sub(r'\s+', '', aadhaar_match.group()) if aadhaar_match else None
        address = address_match.group(1).strip() if address_match else None
        
        # 6. Name & Father's Name Extraction (Logic: Targeted Regex with no newline bleed)
        name_regex = r'(?i)(?:Name|नाम|ava /Name)[\s:]*\n?([A-Z ]{3,})'
        father_regex = r'(?i)(?:Father\'s Name|पिता का नाम)[\s:]*\n?([A-Z ]{3,})'
        
        name_match = re.search(name_regex, raw_text)
        father_match = re.search(father_regex, raw_text)
        
        name = name_match.group(1).strip() if name_match else None
        father_name = father_match.group(1).strip() if father_match else None
        
        # 7. Address Cleanup
        if address:
            # Removes "C/O: [Name]," cleanly by stopping at the first comma
            address = re.sub(r'^(?:C/O|S/O|W/O|D/O)[\s:]*[^,]+,\s*', '', address, flags=re.IGNORECASE).strip()
            # Clean up random newlines inside the address
            address = address.replace('\n', ' ')

        # 8. Document Classification
        doc_type = "UNKNOWN"
        if pan_id:
            doc_type = "PAN"
        elif aadhar_id:
            doc_type = "AADHAAR"
            
        # 9. Return standard structured format
        return {
            "document_type": doc_type,
            "aadhar_id": aadhar_id,
            "pan_id": pan_id,
            "name": name,
            "father_name": father_name,
            "dob": dob,
            "address": address,
            "raw_text": raw_text,
            "extracted_fields": {
                "aadhar_id": aadhar_id,
                "pan_id": pan_id,
                "name": name,
                "father_name": father_name,
                "dob": dob,
                "address": address
            }
        }
    except Exception as e:
        logger.error(f"[OnboardAI][TESSERACT_OCR] Critical failure: {e}")
        return {
            "document_type": "UNKNOWN",
            "error": str(e),
            "aadhar_id": None,
            "pan_id": None,
            "name": None,
            "father_name": None,
            "dob": None,
            "address": None
        }


# ─── GST CERTIFICATE PARSER ────────────────────────────────────────────────────

def _clean_str(s: str) -> str:
    """Replaces newlines/carriage-returns with spaces and strips whitespace."""
    if not s:
        return ""
    return s.replace('\n', ' ').replace('\r', ' ').strip()


def _fmt_date(dmy: str) -> str | None:
    """Converts DD/MM/YYYY → YYYY-MM-DD for PostgreSQL DATE columns."""
    if not dmy:
        return None
    parts = dmy.strip().split('/')
    if len(parts) == 3:
        dd, mm, yyyy = parts
        if len(yyyy) == 4 and yyyy.isdigit():
            return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
    return None


def extract_gst_data(raw_text: str) -> dict | None:
    """
    Parses raw Tesseract OCR text from a GST Registration Certificate.
    Uses label-based regex patterns that match unquoted plain-text output
    (as opposed to the quoted CSV format exported from the GSTN portal).
    Returns a structured dict with cleaned values, or None on failure.
    """
    try:
        # 1. GSTIN / Registration Number
        gstin = None
        m = re.search(r'(?i)Registration Number[\s:]*([A-Z0-9]{15})', raw_text)
        if m:
            gstin = m.group(1).strip()

        # 2. Legal Name
        legal_name = None
        m = re.search(r'(?i)Legal Name[\s:]*(.+)', raw_text)
        if m:
            legal_name = _clean_str(m.group(1))

        # 3. Trade Name (optional suffix "if any")
        trade_name = None
        m = re.search(r'(?i)Trade Name(?:,?\s*if any)?[\s:]*(.+)', raw_text)
        if m:
            trade_name = _clean_str(m.group(1))

        # 4. Constitution of Business
        constitution = None
        m = re.search(r'(?i)Constitution of Business[\s:]*(.+)', raw_text)
        if m:
            constitution = _clean_str(m.group(1))

        # 5. GST Address — multiline capture to handle Tesseract's column interleaving.
        # Captures everything between "Address of Principal Place of" and "Date of Liability",
        # then strips OCR artefacts that bleed in from adjacent table cells.
        address = None
        address_match = re.search(
            r'(?i)Address of Principal Place of[\s:]*([\s\S]*?)(?=\bDate of Liability\b)',
            raw_text
        )
        if address_match:
            raw_address = address_match.group(1)
            # 1. Replace newlines with single spaces
            clean_address = raw_address.replace('\n', ' ').replace('\r', ' ')
            # 2. Remove the interleaved column word "Business"
            clean_address = re.sub(r'(?i)\bBusiness\b', '', clean_address)
            # 3. Remove a stray row-number "5" or "5." that bled into the capture
            clean_address = re.sub(r'\b5\.?\s*$', '', clean_address)
            # 4. Collapse double spaces and strip edges
            address = re.sub(r'\s{2,}', ' ', clean_address).strip() or None
        else:
            # Fallback: simpler label match (single line)
            m = re.search(r'(?i)(?:Principal Place of Business|Address)[\s:]*(.+)', raw_text)
            if m:
                address = _clean_str(m.group(1))

        # 6. Date of Liability (DD/MM/YYYY or DD-MM-YYYY)
        date_of_liability = None
        m = re.search(r'(?i)Date of Liability[\s:]*(\d{2}[/-]\d{2}[/-]\d{4})', raw_text)
        if m:
            raw_dol = m.group(1).replace('-', '/')
            date_of_liability = _fmt_date(raw_dol)

        # 7. Period of Validity — try inline From/To first, then fallback to findall
        from_date = to_date = None
        # Inline pattern: "From: DD/MM/YYYY To: DD/MM/YYYY"
        m_validity = re.search(
            r'(?i)Period of Validity[\s:]*From[\s:]*(\d{2}[/-]\d{2}[/-]\d{4})'
            r'[\s\w/:.-]*To[\s:]*(\d{2}[/-]\d{2}[/-]\d{4}|NA|N/A|Regular)',
            raw_text
        )
        if m_validity:
            from_date = _fmt_date(m_validity.group(1).replace('-', '/'))
            to_raw = m_validity.group(2).strip().upper()
            if to_raw not in ("NA", "N/A", "REGULAR"):
                to_date = _fmt_date(to_raw.replace('-', '/'))
        else:
            # Fallback: collect all dates near "Period of Validity"
            block_m = re.search(r'(?i)Period of Validity(.{0,200})', raw_text, re.DOTALL)
            if block_m:
                dates_found = re.findall(r'(\d{2}[/-]\d{2}[/-]\d{4})', block_m.group(1))
                if dates_found:
                    from_date = _fmt_date(dates_found[0].replace('-', '/'))
                if len(dates_found) >= 2:
                    to_date = _fmt_date(dates_found[1].replace('-', '/'))

        # Require at least GSTIN or Legal Name to consider parsing successful
        if not gstin and not legal_name:
            logger.warning("[OnboardAI][GST_PARSER] Could not extract GSTIN or Legal Name. Returning None.")
            return None

        result = {
            "document_type": "GST",
            "gstin": gstin,
            "legal_name": legal_name,
            "trade_name": trade_name,
            "constitution": constitution,
            "address": address,
            "date_of_liability": date_of_liability,
            "validity_from": from_date,
            "validity_to": to_date,
        }
        logger.info(f"[OnboardAI][GST_PARSER] Extracted GST data: GSTIN={gstin}, Legal Name={legal_name}")
        return result

    except Exception as e:
        logger.error(f"[OnboardAI][GST_PARSER] Failed to parse GST data: {e}")
        return None
