from minio import Minio
import os
import io
from minio.commonconfig import CopySource

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def save_to_minio(bucket_name: str, object_name: str, file_bytes: bytes, content_type: str = "image/png") -> str:
    """
    Saves file to MinIO and returns the path/reference.
    """
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
        
    data_stream = io.BytesIO(file_bytes)
    length = len(file_bytes)
    
    minio_client.put_object(
        bucket_name,
        object_name,
        data=data_stream,
        length=length,
        content_type=content_type
    )
    
    return f"{bucket_name}/{object_name}"

def move_minio_object(src_bucket: str, src_object: str, dest_bucket: str, dest_object: str) -> str:
    """
    Moves an object from a temporary bucket to a permanent bucket securely.
    """
    if not minio_client.bucket_exists(dest_bucket):
        minio_client.make_bucket(dest_bucket)
        
    minio_client.copy_object(
        dest_bucket,
        dest_object,
        CopySource(src_bucket, src_object)
    )
    
    minio_client.remove_object(src_bucket, src_object)
    
    return f"{dest_bucket}/{dest_object}"


async def get_minio_file(file_url: str) -> bytes:
    """
    Retrieve file bytes from MinIO given a stored URL path.

    Parameters
    ----------
    file_url:
        Path in the format ``"bucket_name/object_key"``
        (as stored in ``user_documents.file_url``).

    Returns
    -------
    bytes
        The raw file content.

    Raises
    ------
    ValueError
        If *file_url* cannot be parsed into bucket + object key.
    Exception
        Any MinIO client error is propagated.
    """
    import asyncio

    if "/" not in file_url:
        raise ValueError(f"Invalid MinIO file URL (no '/' separator): {file_url}")

    bucket_name, object_key = file_url.split("/", 1)

    def _fetch() -> bytes:
        response = minio_client.get_object(bucket_name, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    return await asyncio.to_thread(_fetch)

