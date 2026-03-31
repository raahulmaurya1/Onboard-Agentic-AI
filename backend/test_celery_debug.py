"""
Debug test - runs the extraction pipeline inline (no Celery broker needed).
This reveals exactly what the Celery task is doing internally.
"""
import asyncio
import fitz

async def test():
    from app.db.redis_client import get_temp_extraction, redis_client, save_temp_extraction
    from app.storage.minio import minio_client
    from app.workers.tasks.extraction import process_and_standardize_file
    from app.agents.extraction_agent import extract_document_data, extract_document_data_from_text
    from app.agents.validation_agent import cross_check_documents
    
    session_ulid = '01KK7F6WZPFJKV4N89T35YKEQQ'
    
    print(f'Testing session: {session_ulid}')
    objects = list(minio_client.list_objects('temp', prefix=f'{session_ulid}/', recursive=True))
    print(f'Found {len(objects)} MinIO objects')
    
    extracted_collection = []
    
    for obj in objects:
        print(f'\nProcessing: {obj.object_name}')
        try:
            resp = minio_client.get_object('temp', obj.object_name)
            f_bytes = resp.read()
            clean_bytes, mime_type = process_and_standardize_file(f_bytes)
            print(f'  MIME: {mime_type}, Size: {len(clean_bytes)} bytes')
            
            ext_json = None
            extracted_from_text = False
            
            if mime_type == 'application/pdf':
                doc = fitz.open(stream=clean_bytes, filetype='pdf')
                text_content = ''
                for page in doc:
                    text_content += page.get_text()
                print(f'  PDF text length: {len(text_content.strip())} chars')
                print(f'  PDF text preview: {text_content.strip()[:200]}')
                
                if len(text_content.strip()) > 50:
                    print(f'  >> Calling TEXT extraction (skipping Vision OCR)...')
                    ext_json = await extract_document_data_from_text(text_content)
                    print(f'  Text Extraction Result: {ext_json}')
                    if ext_json and not ext_json.get('error') and ext_json.get('document_type') in ['PAN', 'Aadhaar']:
                        extracted_from_text = True
                        print(f'  >> Text extraction SUCCEEDED, skipping Vision OCR.')
                    else:
                        print(f'  >> Text extraction returned Unknown/error, falling back to Vision OCR.')
            
            if not extracted_from_text:
                print(f'  >> Calling VISION OCR fallback...')
                ext_json = await extract_document_data(clean_bytes, mime_type)
                print(f'  Vision OCR Result: {ext_json}')
            
            if ext_json and not ext_json.get('error'):
                extracted_collection.append(ext_json)
                print(f'  >> Added to extracted_collection. Total: {len(extracted_collection)}')
            else:
                print(f'  >> WARNING: ext_json is empty or errored, skipping. Value: {ext_json}')
        except Exception as e:
            import traceback
            print(f'  ERROR processing {obj.object_name}: {e}')
            traceback.print_exc()
    
    print(f'\n--- FINAL RESULTS ---')
    print(f'Extracted collection size: {len(extracted_collection)}')
    
    if extracted_collection:
        validation_result = cross_check_documents(extracted_collection)
        print(f'Validation result: {validation_result}')
        save_temp_extraction(session_ulid, {'files': [], 'validation': validation_result})
        saved = get_temp_extraction(session_ulid)
        print(f'Redis save successful: {saved is not None}')
        if saved and 'validation' in saved:
            combined = saved['validation'].get('combined_data', {})
            print(f'combined_data keys: {list(combined.keys())}')
            print(f'combined_data values: {combined}')
        print('\n[SUCCESS] Celery pipeline is working correctly!')
    else:
        print('\n[FAILURE] extracted_collection is EMPTY - check errors above!')

asyncio.run(test())
