"""
Single-file extraction test - tests one PDF directly against Gemini 1.5 Flash.
"""
import asyncio

async def test():
    from app.storage.minio import minio_client
    from app.workers.tasks.extraction import process_and_standardize_file
    from app.agents.extraction_agent import extract_document_data
    from app.db.redis_client import get_temp_extraction, save_temp_extraction
    from app.agents.validation_agent import cross_check_documents

    session = '01KK7F6WZPFJKV4N89T35YKEQQ'
    objects = list(minio_client.list_objects('temp', prefix=f'{session}/', recursive=True))
    print(f"Found {len(objects)} files in session: {session}")
    
    extracted_collection = []
    
    for obj in objects:
        print(f"\n--- Processing: {obj.object_name} ---")
        try:
            resp = minio_client.get_object('temp', obj.object_name)
            f_bytes = resp.read()
            print(f"Downloaded {len(f_bytes)} bytes")
            
            clean_bytes, mime_type = process_and_standardize_file(f_bytes)
            print(f"MIME type: {mime_type}")
            
            print("Calling Gemini Vision OCR...")
            result = await extract_document_data(clean_bytes, mime_type)
            print(f"Result: {result}")
            
            if result and not result.get('error'):
                extracted_collection.append(result)
            else:
                print(f"ERROR or empty result: {result}")
        except Exception as e:
            import traceback
            print(f"Exception: {e}")
            traceback.print_exc()
    
    print(f"\n=== SUMMARY: {len(extracted_collection)} docs extracted ===")
    if extracted_collection:
        val = cross_check_documents(extracted_collection)
        print(f"Validation result: {val}")
        save_temp_extraction(session, {'files': [], 'validation': val})
        saved = get_temp_extraction(session)
        if saved:
            print(f"Redis SAVE SUCCESS! combined_data: {saved['validation']['combined_data']}")
        else:
            print("Redis save FAILED")
    else:
        print("No data to save to Redis")

asyncio.run(test())
