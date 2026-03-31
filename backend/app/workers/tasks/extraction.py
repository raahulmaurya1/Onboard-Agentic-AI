import io
import re
import os
import json
import logging
import fitz  # PyMuPDF
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from magika import Magika

logger = logging.getLogger(__name__)


# ─── FILE DETECTION & STANDARDIZATION ─────────────────────────────────────────

def process_and_standardize_file(file_bytes: bytes) -> tuple[bytes, str]:
    """
    Uses Magika to definitively identify the exact mime type of the binary payload.
    Standardizes images to PNG for consistent Vision AI input.
    Returns (processed_bytes, true_mime_type).
    """
    try:
        m = Magika()
        result = m.identify_bytes(file_bytes)
        true_mime_type = result.output.mime_type

        allowed_mimes = ["application/pdf", "image/jpeg", "image/png", "image/webp"]
        if true_mime_type not in allowed_mimes:
            raise ValueError(f"Unsupported file type: {true_mime_type}")

        # Standardize images to PNG
        if true_mime_type in ["image/jpeg", "image/webp"]:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            out = io.BytesIO()
            img.save(out, format="PNG")
            return out.getvalue(), "image/png"

        return file_bytes, true_mime_type

    except Exception as e:
        logger.error(f"File standardization failed: {e}")
        raise ValueError(f"Failed to process document payload: {str(e)}")


def pdf_to_png(file_bytes: bytes) -> bytes:
    """
    Renders the first page of a scanned PDF to a high-res PNG for Vision AI.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(dpi=200)
    return pix.tobytes("png")


# ─── TIER 1: REGEX-BASED LOCAL EXTRACTION ─────────────────────────────────────

def regex_extract_kyc(text: str) -> dict | None:
    """
    Zero-API-cost extraction using regex patterns.
    Returns the same schema as the Gemini extraction functions, or None if insufficient.
    """
    text_upper = text.upper()

    is_pan = any(kw in text_upper for kw in [
        "INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "GOVT. OF INDIA", "INCOME TAX"
    ])
    is_aadhaar = any(kw in text_upper for kw in [
        "AADHAAR", "AADHAR", "UNIQUE IDENTIFICATION", "UIDAI", "VID:"
    ])

    if not is_pan and not is_aadhaar:
        return None

    fields = {}

    # PAN ID: 5 letters + 4 digits + 1 letter
    pan_match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text_upper)
    if pan_match:
        fields["id_number"] = pan_match.group()

    # Aadhaar ID: 12 digits in groups of 4
    aadhaar_match = re.search(r'\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b', text)
    if aadhaar_match:
        fields["id_number"] = re.sub(r'[\s\-]', '', aadhaar_match.group())

    # DOB: DD/MM/YYYY or DD-MM-YYYY
    dob_match = re.search(r'\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b', text)
    if dob_match:
        fields["dob"] = dob_match.group().replace("-", "/")

    # Name extraction
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    name = None
    father_name = None

    if is_pan:
        pan_noise = {
            "INCOME", "TAX", "DEPARTMENT", "GOVT", "INDIA", "PERMANENT",
            "ACCOUNT", "NUMBER", "CARD", "DATE", "OF", "BIRTH", "FATHER"
        }
        for line in lines:
            words = line.split()
            if (len(words) >= 2 and line.isupper() and
                    all(w not in pan_noise for w in words) and
                    not re.search(r'\d', line)):
                if name is None:
                    name = line.title()
                elif father_name is None:
                    father_name = line.title()

    if is_aadhaar:
        aadhaar_noise = {
            "AADHAAR", "AADHAR", "UIDAI", "GOVERNMENT", "INDIA", "UNIQUE",
            "IDENTIFICATION", "AUTHORITY", "ENROLLMENT", "VID", "DOB", "MALE", "FEMALE"
        }
        for line in lines:
            words = line.split()
            if (len(words) >= 2 and re.match(r'^[A-Za-z\s]+$', line) and
                    not any(w.upper() in aadhaar_noise for w in words) and
                    len(line) < 50):
                name = line.strip()
                break

        # Address: try anchoring on an explicit "Address:" label first
        raw_address = None

        # Strategy 1: capture everything after "Address:" or "address:" up to the PIN code
        addr_label_match = re.search(
            r'(?i)address[:\s]+(.+?\d{6})',
            text,
            re.DOTALL
        )
        if addr_label_match:
            raw_address = addr_label_match.group(1)

        # Strategy 2: capture a multi-line block that ends with a 6-digit PIN
        if not raw_address:
            addr_block_match = re.search(
                r'((?:[A-Za-z0-9 ,\-/\n]{5,}\n?){1,6}\d{6})',
                text
            )
            if addr_block_match:
                candidate = addr_block_match.group(1)
                # Reject pure phone numbers (strings that are mostly digits)
                if not re.match(r'^\s*[\d\s]+\s*$', candidate):
                    raw_address = candidate

        # Strategy 3: single line containing 6-digit PIN
        if not raw_address:
            for line in lines:
                if re.search(r'\b\d{6}\b', line) and not re.match(r'^\s*[\d\s]+\s*$', line):
                    raw_address = line.strip()
                    break

        if raw_address:
            # Strip C/O: <name>, (case-insensitive, everything up to first comma)
            cleaned = re.sub(r'(?i)c/o\s*:?\s*[^,]+,?\s*', '', raw_address)
            # Collapse newlines and multiple spaces into a single clean string
            cleaned = " ".join(cleaned.split()).strip()
            # Remove any leading commas or stray punctuation left behind
            cleaned = cleaned.lstrip(", ")
            if cleaned:
                fields["address"] = cleaned


    if name:
        fields["name"] = name
    if father_name and is_pan:
        fields["father_name"] = father_name

    # Require at least id_number or name to call this a success
    if not fields.get("id_number") and not fields.get("name"):
        return None

    doc_type = "PAN" if is_pan else "Aadhaar"
    print(f"[OnboardAI][REGEX] ✓ Tier 1 success for {doc_type}: {fields}")
    return {"document_type": doc_type, "extracted_fields": fields}


# ─── SINGLE FILE PROCESSOR (SYNCHRONOUS) ──────────────────────────────────────

def _process_single_file(object_name: str) -> dict | None:
    """
    Processes one MinIO file through the local Tesseract OCR pipeline.
    """
    from app.storage.minio import minio_client
    from app.agents.extraction_agent import extract_and_classify_local

    try:
        print(f"[OnboardAI] Fetching: {object_name}")
        # Strip bucket prefix if present in the path string
        clean_path = object_name.replace("temp/", "")
        resp = minio_client.get_object("temp", clean_path)
        raw_bytes = resp.read()

        clean_bytes, mime_type = process_and_standardize_file(raw_bytes)
        
        # ── Local OCR Extraction ─────────────────────────────────────────────
        # Standardize to PNG for OCR if it's a PDF
        ocr_bytes = clean_bytes
        if mime_type == "application/pdf":
            ocr_bytes = pdf_to_png(clean_bytes)
            
        ext_json = extract_and_classify_local(ocr_bytes)

        if ext_json and not ext_json.get("error"):
            filename = clean_path.split("/")[-1]
            return {
                "ext_json": ext_json,
                "path": {"filename": filename, "url": f"temp/{clean_path}", "mime_type": mime_type}
            }
        return None

    except Exception as err:
        import traceback
        print(f"[OnboardAI][CRITICAL] Exception for {object_name}: {err}")
        traceback.print_exc()
        return None


# ─── CELERY TASK (FULLY SYNCHRONOUS) ──────────────────────────────────────────

from app.workers.celery_app import celery_app


@celery_app.task(name="process_documents_async")
def process_documents_async(session_ulid: str, minio_paths: list[str]):
    """
    Retail KYC OCR task (Aadhaar + PAN).
    Uses strict filename-based routing so a GST certificate is never fed into
    the generic KYC classifier, preventing GSTIN from being misread as a PAN ID.
    """
    from app.db.redis_client import save_temp_extraction
    from app.agents.validation_agent import cross_check_documents

    try:
        print(f"[OnboardAI][CELERY] Processing {len(minio_paths)} files for session {session_ulid}")

        # ── Strict filename-based routing ──────────────────────────────────────
        # Each path is classified BEFORE any OCR function is called.
        # This prevents GSTIN from being misidentified as a PAN number.
        pan_result     = None
        aadhaar_result = None
        gst_result     = None
        all_file_paths = []

        futures_map = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            for path in minio_paths:
                fname = path.lower()
                if "gst" in fname:
                    print(f"[OnboardAI][CELERY] Routing '{path}' → GST parser")
                    fut = executor.submit(_process_gst_file, path)
                    futures_map[fut] = ("gst", path)
                elif "pan" in fname:
                    print(f"[OnboardAI][CELERY] Routing '{path}' → KYC extractor (PAN hint)")
                    fut = executor.submit(_process_single_file, path)
                    futures_map[fut] = ("pan", path)
                elif "aadhaar" in fname or "aadhar" in fname:
                    print(f"[OnboardAI][CELERY] Routing '{path}' → KYC extractor (Aadhaar hint)")
                    fut = executor.submit(_process_single_file, path)
                    futures_map[fut] = ("aadhaar", path)
                else:
                    # Fallback for unknown filenames — use generic KYC extractor
                    print(f"[OnboardAI][CELERY] Routing '{path}' → KYC extractor (no hint)")
                    fut = executor.submit(_process_single_file, path)
                    futures_map[fut] = ("kyc", path)

            for future in as_completed(futures_map):
                doc_hint, path = futures_map[future]
                result = future.result()
                if doc_hint == "gst":
                    if result and result.get("gst_data"):
                        gst_result = result["gst_data"]
                        if result.get("path"):
                            all_file_paths.append(result["path"])
                else:
                    if result and result.get("ext_json") and not result["ext_json"].get("error"):
                        dt = result["ext_json"].get("document_type", "").upper()
                        if dt == "PAN":
                            pan_result = result["ext_json"]
                        elif "AADHAAR" in dt or "AADHAR" in dt:
                            aadhaar_result = result["ext_json"]
                        else:
                            # Catch-all for generic KYC hint
                            if not pan_result:
                                pan_result = result["ext_json"]
                            elif not aadhaar_result:
                                aadhaar_result = result["ext_json"]
                        all_file_paths.append(result["path"])

        kyc_docs = [d for d in [pan_result, aadhaar_result] if d]
        print(f"[OnboardAI][CELERY] Extracted KYC={len(kyc_docs)}/{len(minio_paths)} | GST={'✓' if gst_result else '✗'}")

        if not kyc_docs:
            print(f"[OnboardAI][CELERY] ✗ No KYC documents extracted for session {session_ulid}")
            return {"error": "No valid document data extracted.", "ui_action": "RENDER_KYC_UPLOAD"}

        # ── Rulebook Cross-Check (PAN ↔ Aadhaar ONLY — GST is excluded) ────────
        try:
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            rule_book_path = os.path.join(root_path, "agents", "rule_book.json")
            with open(rule_book_path, 'r') as f:
                rules = json.load(f).get("document_validation", {})

            if pan_result and aadhaar_result:
                validation_errors = []
                if rules.get("require_name_match"):
                    p_name = str(pan_result.get("name") or "").strip().upper()
                    a_name = str(aadhaar_result.get("name") or "").strip().upper()
                    if p_name and a_name and not (p_name in a_name or a_name in p_name):
                        validation_errors.append(f"Name mismatch: PAN '{p_name}' not in Aadhaar '{a_name}'")
                if rules.get("require_dob_match"):
                    # Strictly use pan_result.dob and aadhaar_result.dob — never gst_data
                    p_dob = str(pan_result.get("dob") or "").strip()
                    a_dob = str(aadhaar_result.get("dob") or "").strip()
                    if p_dob and a_dob and not (p_dob in a_dob or a_dob in p_dob):
                        validation_errors.append(f"DOB mismatch: PAN '{p_dob}' not in Aadhaar '{a_dob}'")

                if validation_errors:
                    error_msg = "; ".join(validation_errors)
                    print(f"[OnboardAI][CELERY] ✗ DEMOGRAPHIC MISMATCH: {error_msg}")
                    return {
                        "error": f"Demographic mismatch: {error_msg}",
                        "ui_action": "RENDER_KYC_UPLOAD",
                        "extracted_data": {},
                        "is_mismatch": True
                    }
        except Exception as rule_err:
            logger.warning(f"[OnboardAI][CELERY] Rulebook check bypassed: {rule_err}")

        # ── Merge KYC only — GST is in its own key, never in combined_data ──────
        validation_result = cross_check_documents(kyc_docs)
        combined_data     = dict(validation_result.get("combined_data", {}))
        is_valid          = validation_result.get("valid", True)
        flags             = validation_result.get("flags", [])

        print(f"[OnboardAI][CELERY] combined_data keys: {list(combined_data.keys())}")

        redis_payload = {
            "files": all_file_paths,
            "validation": {
                "valid":        bool(is_valid),
                "flags":        list(flags),
                "combined_data": combined_data,   # KYC fields only
                "gst_data":     gst_result or {}  # GST fields isolated separately
            }
        }

        from app.db.redis_client import save_temp_extraction, get_temp_extraction
        save_temp_extraction(session_ulid, redis_payload)

        verify = get_temp_extraction(session_ulid)
        if verify and "validation" in verify:
            saved_cd = verify["validation"].get("combined_data", {})
            print(f"[OnboardAI][CELERY] ✓ Redis VERIFIED. combined_data keys: {list(saved_cd.keys())}")
        else:
            print(f"[OnboardAI][CELERY] ✗ Redis write VERIFICATION FAILED!")

        return {"status": "success", "extracted_data": redis_payload["validation"]}

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Celery task failed: {e}", exc_info=True)
        return {"error": str(e), "ui_action": "RENDER_KYC_UPLOAD"}



# ─── GST FILE PROCESSOR (SYNCHRONOUS HELPER) ──────────────────────────────────

def _process_gst_file(object_name: str) -> dict | None:
    """
    Fetches a GST certificate from MinIO, runs Tesseract OCR,
    and passes the raw text through extract_gst_data.
    Thread-safe: each call initialises its own Tesseract subprocess.
    """
    from app.storage.minio import minio_client
    from app.agents.extraction_agent import extract_gst_data

    try:
        print(f"[OnboardAI][GST] Fetching GST document: {object_name}")
        clean_path = object_name.replace("temp/", "")
        resp = minio_client.get_object("temp", clean_path)
        raw_bytes = resp.read()

        clean_bytes, mime_type = process_and_standardize_file(raw_bytes)

        # Always convert to a rasterized image for Tesseract
        ocr_bytes = clean_bytes
        if mime_type == "application/pdf":
            ocr_bytes = pdf_to_png(clean_bytes)

        # Extract raw text via Tesseract (reuses the same pytesseract config)
        import io as _io
        import pytesseract
        from PIL import Image as _Img, ImageEnhance as _Enh
        img = _Img.open(_io.BytesIO(ocr_bytes)).convert("L")
        img = _Enh.Contrast(img).enhance(2.0)
        raw_text = pytesseract.image_to_string(img)

        gst_data = extract_gst_data(raw_text)
        if gst_data:
            filename = clean_path.split("/")[-1]
            return {
                "gst_data": gst_data,
                "path": {"filename": filename, "url": f"temp/{clean_path}", "mime_type": mime_type}
            }
        return None

    except Exception as err:
        import traceback
        print(f"[OnboardAI][GST][CRITICAL] Exception processing {object_name}: {err}")
        traceback.print_exc()
        return None


# ─── SME CELERY TASK (CONCURRENT OCR) ─────────────────────────────────────────

@celery_app.task(name="process_sme_documents_async")
def process_sme_documents_async(session_ulid: str, minio_paths: list[str]):
    """
    Concurrent OCR task for SME onboarding (Aadhaar + PAN + GST).
    Runs all 3 extractions in parallel via ThreadPoolExecutor and saves
    the merged result to Redis for the frontend POLL_STATUS hook.
    """
    from app.db.redis_client import save_temp_extraction, get_temp_extraction

    try:
        print(f"[OnboardAI][SME_CELERY] Processing {len(minio_paths)} SME files for session {session_ulid}")

        # Detect GST document by filename convention (case-insensitive)
        gst_paths = [p for p in minio_paths if "gst" in p.lower()]
        kyc_paths = [p for p in minio_paths if "gst" not in p.lower()]

        extracted_kyc = []
        kyc_file_paths = []
        gst_result = None
        gst_file_path = None

        # Build concurrent futures: KYC docs + GST doc
        futures_map = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            for path in kyc_paths:
                fut = executor.submit(_process_single_file, path)
                futures_map[fut] = ("kyc", path)
            for path in gst_paths:
                fut = executor.submit(_process_gst_file, path)
                futures_map[fut] = ("gst", path)

            for future in as_completed(futures_map):
                doc_type, path = futures_map[future]
                result = future.result()
                if doc_type == "kyc":
                    if result and result.get("ext_json") and not result["ext_json"].get("error"):
                        extracted_kyc.append(result["ext_json"])
                        kyc_file_paths.append(result["path"])
                elif doc_type == "gst":
                    if result and result.get("gst_data"):
                        gst_result = result["gst_data"]
                        gst_file_path = result["path"]

        print(f"[OnboardAI][SME_CELERY] KYC extracted: {len(extracted_kyc)}/{len(kyc_paths)} | GST: {'✓' if gst_result else '✗'}")

        # ── PAN ↔ Aadhaar Rulebook Cross-Check ────────────────────────────────
        validation_errors = []
        try:
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            rule_book_path = os.path.join(root_path, "agents", "rule_book.json")
            with open(rule_book_path, 'r') as f:
                rules = json.load(f).get("document_validation", {})

            pan_data     = next((d for d in extracted_kyc if d.get("document_type") == "PAN"), None)
            aadhaar_data = next((d for d in extracted_kyc if d.get("document_type") in ["AADHAAR", "Aadhaar"]), None)

            if pan_data and aadhaar_data:
                if rules.get("require_name_match"):
                    p_name = str(pan_data.get("name") or "").strip().upper()
                    a_name = str(aadhaar_data.get("name") or "").strip().upper()
                    if p_name and a_name and not (p_name in a_name or a_name in p_name):
                        validation_errors.append(f"Name mismatch: PAN '{p_name}' vs Aadhaar '{a_name}'")
                if rules.get("require_dob_match"):
                    p_dob = str(pan_data.get("dob") or "").strip()
                    a_dob = str(aadhaar_data.get("dob") or "").strip()
                    if p_dob and a_dob and not (p_dob in a_dob or a_dob in p_dob):
                        validation_errors.append(f"DOB mismatch: PAN '{p_dob}' vs Aadhaar '{a_dob}'")
        except Exception as rule_err:
            logger.warning(f"[OnboardAI][SME_CELERY] Rulebook check bypassed: {rule_err}")

        if validation_errors:
            error_msg = "; ".join(validation_errors)
            print(f"[OnboardAI][SME_CELERY] ✗ DEMOGRAPHIC MISMATCH: {error_msg}")
            return {
                "error": f"Demographic mismatch: {error_msg}",
                "ui_action": "RENDER_KYC_UPLOAD",
                "extracted_data": {},
                "is_mismatch": True
            }

        # ── Merge KYC only — GST always stays in its own key, NEVER in combined_data ─
        # cross_check_documents only receives the KYC list (Aadhaar + PAN).
        # This guarantees GSTIN, gst_address, and date_of_liability can NEVER
        # overwrite the real pan_id, address, or dob fields.
        from app.agents.validation_agent import cross_check_documents
        validation_result = cross_check_documents(extracted_kyc) if extracted_kyc else {"combined_data": {}, "valid": True, "flags": []}
        combined_data = dict(validation_result.get("combined_data", {}))

        all_file_paths = kyc_file_paths + ([gst_file_path] if gst_file_path else [])

        redis_payload = {
            "files": all_file_paths,
            "validation": {
                "valid":        bool(validation_result.get("valid", True)),
                "flags":        list(validation_result.get("flags", [])),
                "combined_data": combined_data,   # KYC fields only (PAN + Aadhaar)
                "gst_data":     gst_result or {}  # GST isolated — separate key
            }
        }

        save_temp_extraction(session_ulid, redis_payload)

        verify = get_temp_extraction(session_ulid)
        if verify:
            print(
                f"[OnboardAI][SME_CELERY] ✓ Redis VERIFIED. "
                f"combined_data keys: {list(verify['validation'].get('combined_data', {}).keys())} | "
                f"GST present: {bool(gst_result)}"
            )
        else:
            print(f"[OnboardAI][SME_CELERY] ✗ Redis write VERIFICATION FAILED!")

        return {"status": "success", "extracted_data": redis_payload["validation"]}

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[OnboardAI][SME_CELERY] Task failed: {e}", exc_info=True)
        return {"error": str(e), "ui_action": "RENDER_KYC_UPLOAD"}

