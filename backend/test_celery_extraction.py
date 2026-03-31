"""
Test script to verify the Celery document extraction pipeline.
Steps:
  1. Check Redis connection
  2. Check MinIO connection + list available sessions in the 'temp' bucket
  3. Dispatch the process_documents_async Celery task for a real session
  4. Poll Redis every 3s (up to 60s) watching for extraction results
"""
import time
import json
import sys

# ─── STEP 1: Redis Connectivity ───────────────────────────────────────────────
print("\n" + "="*60)
print(" STEP 1: Checking Redis connectivity...")
print("="*60)
try:
    from app.db.redis_client import redis_client, get_temp_extraction
    redis_client.ping()
    print("[✓] Redis is connected and responding!")
except Exception as e:
    print(f"[✗] Redis connection FAILED: {e}")
    sys.exit(1)

# ─── STEP 2: MinIO Connectivity + Session Discovery ───────────────────────────
print("\n" + "="*60)
print(" STEP 2: Checking MinIO + discovering sessions in 'temp' bucket...")
print("="*60)
try:
    from app.storage.minio import minio_client
    buckets = minio_client.list_buckets()
    print(f"[✓] MinIO is connected! Buckets: {[b.name for b in buckets]}")

    if not minio_client.bucket_exists("temp"):
        print("[✗] No 'temp' bucket found. Please upload documents first via the frontend!")
        sys.exit(1)

    # Discover all unique session ULIDs present in the temp bucket
    objects = list(minio_client.list_objects("temp", recursive=True))
    sessions = list({obj.object_name.split("/")[0] for obj in objects if "/" in obj.object_name})

    if not sessions:
        print("[✗] No session folders found in 'temp' bucket. Please upload documents first!")
        sys.exit(1)

    # Use the most recent session (last in the list)
    test_session = sessions[-1]
    session_files = [o.object_name for o in objects if o.object_name.startswith(test_session + "/")]
    print(f"[✓] Found {len(sessions)} session(s) in MinIO.")
    print(f"[✓] Using session: {test_session}")
    print(f"    Files: {session_files}")

except Exception as e:
    print(f"[✗] MinIO connection FAILED: {e}")
    sys.exit(1)

# ─── STEP 3: Dispatch Celery Task ─────────────────────────────────────────────
print("\n" + "="*60)
print(f" STEP 3: Dispatching Celery extraction task for session: {test_session}")
print("="*60)
try:
    from app.workers.tasks.extraction import process_documents_async
    task = process_documents_async.delay(test_session)
    print(f"[✓] Task dispatched! Task ID: {task.id}")
    print(f"    State: {task.state}")
except Exception as e:
    print(f"[✗] Celery task dispatch FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ─── STEP 4: Poll Redis for Results ───────────────────────────────────────────
print("\n" + "="*60)
print(" STEP 4: Polling Redis for extraction results (up to 60 seconds)...")
print("="*60)

# Clear any existing cached result first so we see a fresh write
from app.db.redis_client import redis_client
redis_client.delete(f"extractor:{test_session}")
print(f"[i] Cleared existing Redis key 'extractor:{test_session}' for a clean test.\n")

timeout = 60
start = time.time()
found = False

while time.time() - start < timeout:
    elapsed = round(time.time() - start, 1)
    result = get_temp_extraction(test_session)

    if result:
        print(f"\n[✓] SUCCESS at {elapsed}s! Extraction result saved to Redis.")
        print("    Redis Key Contents:")
        print(json.dumps(result, indent=2, default=str))
        found = True
        break

    # Also check task state
    try:
        current_state = task.state
        print(f"  [{elapsed}s] Waiting... Celery task state: {current_state}")
    except Exception:
        print(f"  [{elapsed}s] Waiting... (task state unavailable)")
    
    time.sleep(3)

if not found:
    print(f"\n[✗] TIMEOUT after {timeout}s. No extraction result was saved to Redis.")
    print("    This suggests the Celery worker may have failed or timed out processing the documents.")
    print("    Check the Celery worker terminal window for detailed error logs.")
    sys.exit(1)

print("\n" + "="*60)
print(" ALL TESTS PASSED! Celery extraction pipeline is working correctly.")
print("="*60)
