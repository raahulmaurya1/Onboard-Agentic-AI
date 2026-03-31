"""
Runs the new Celery task logic INLINE (no Celery broker) to capture full output.
"""
import asyncio
import sys

session_ulid = '01KK7F6WZPFJKV4N89T35YKEQQ'

async def run():
    # Import everything the Celery task uses
    from app.db.redis_client import save_temp_extraction, get_temp_extraction, redis_client
    from app.storage.minio import minio_client
    from app.agents.validation_agent import cross_check_documents
    import fitz

    # Import the new tiered functions from the rewritten extraction.py
    from app.workers.tasks.extraction import (
        process_and_standardize_file,
        pdf_to_png,
        regex_extract_kyc
    )
    from app.agents.extraction_agent import extract_document_data, extract_document_data_from_text

    objects = list(minio_client.list_objects("temp", prefix=f"{session_ulid}/", recursive=True))
    print(f"Found {len(objects)} files")

    extracted_collection = []
    minio_temp_paths = []

    for obj in objects:
        print(f"\n{'='*50}")
        print(f"Processing: {obj.object_name}")
        try:
            resp = minio_client.get_object("temp", obj.object_name)
            raw_bytes = resp.read()
            print(f"Raw bytes: {len(raw_bytes)}")

            clean_bytes, mime_type = process_and_standardize_file(raw_bytes)
            print(f"After standardize: mime={mime_type}, size={len(clean_bytes)}")

            ext_json = None
            raw_text = ""

            # Step 1: Try PDF text extraction
            if mime_type == "application/pdf":
                try:
                    doc = fitz.open(stream=clean_bytes, filetype="pdf")
                    for page in doc:
                        raw_text += page.get_text()
                    print(f"PDF text chars: {len(raw_text.strip())}")
                    print(f"PDF text sample: {raw_text.strip()[:300]!r}")
                except Exception as e:
                    print(f"fitz error: {e}")

            # Step 2: Tier 1 Regex
            if raw_text.strip():
                print("Running Tier 1 Regex...")
                ext_json = regex_extract_kyc(raw_text)
                print(f"Regex result: {ext_json}")

            # Step 3: Tier 2 Gemini (only if regex failed)
            if not ext_json:
                if raw_text.strip():
                    print("Regex failed, trying Gemini text...")
                    try:
                        ext_json = await extract_document_data_from_text(raw_text)
                        print(f"Gemini text result: {ext_json}")
                    except Exception as e:
                        print(f"Gemini text error: {e}")
                else:
                    print("No text layer, trying Gemini Vision...")
                    vision_bytes = clean_bytes
                    vision_mime = mime_type
                    if mime_type == "application/pdf":
                        print("Rendering PDF page to PNG...")
                        vision_bytes = pdf_to_png(clean_bytes)
                        vision_mime = "image/png"
                        print(f"PNG size: {len(vision_bytes)} bytes")
                    try:
                        ext_json = await extract_document_data(vision_bytes, vision_mime)
                        print(f"Gemini Vision result: {ext_json}")
                    except Exception as e:
                        print(f"Gemini Vision error: {e}")

            if ext_json and not ext_json.get("error"):
                extracted_collection.append(ext_json)
                minio_temp_paths.append({"filename": obj.object_name.split("/")[-1]})
                print(f"✓ Added to collection")
            else:
                print(f"✗ Skipped (error or empty): {ext_json}")

        except Exception as e:
            import traceback
            print(f"EXCEPTION: {e}")
            traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"FINAL: {len(extracted_collection)} docs extracted")

    if extracted_collection:
        val = cross_check_documents(extracted_collection)
        print(f"Validation: {val}")
        save_temp_extraction(session_ulid, {"files": minio_temp_paths, "validation": val})
        saved = get_temp_extraction(session_ulid)
        if saved:
            print(f"✓ Redis SAVED! combined_data = {saved['validation']['combined_data']}")
        else:
            print("✗ Redis save FAILED")
    else:
        print("✗ Nothing to save")

asyncio.run(run())
