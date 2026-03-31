"""
Quick sync test - runs the full new tiered pipeline synchronously (no asyncio, no Celery).
Verifies the new code works before worrying about the worker cache.
"""
import sys

session_ulid = '01KKFAYF20X8W26WCY08Q4X2TB'

from app.storage.minio import minio_client
from app.workers.tasks.extraction import _process_single_file, regex_extract_kyc
from app.agents.validation_agent import cross_check_documents
from app.db.redis_client import save_temp_extraction, get_temp_extraction
import fitz

objects = list(minio_client.list_objects("temp", prefix=f"{session_ulid}/", recursive=True))
print(f"Found {len(objects)} files for session {session_ulid}")

extracted_collection = []
minio_temp_paths = []

for obj in objects:
    print(f"\n{'='*50}")
    print(f"Running _process_single_file for: {obj.object_name}")
    result = _process_single_file(obj.object_name)
    print(f"Result: {result}")
    if result and result.get("ext_json") and not result["ext_json"].get("error"):
        extracted_collection.append(result["ext_json"])
        minio_temp_paths.append(result["path"])

print(f"\n{'='*50}")
print(f"FINAL: {len(extracted_collection)} docs extracted successfully")

if extracted_collection:
    val = cross_check_documents(extracted_collection)
    print(f"Validation: {val}")
    save_temp_extraction(session_ulid, {"files": minio_temp_paths, "validation": val})
    saved = get_temp_extraction(session_ulid)
    if saved:
        print(f"\n✓ Redis SAVE CONFIRMED!")
        print(f"combined_data = {saved['validation']['combined_data']}")
    else:
        print("✗ Redis save FAILED")
else:
    print("✗ No documents extracted")
    sys.exit(1)
