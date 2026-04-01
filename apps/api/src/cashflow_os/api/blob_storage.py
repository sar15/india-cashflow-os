import os
from typing import Optional


def storage_backend() -> str:
    configured_backend = os.getenv("CASHFLOW_STORAGE_BACKEND", "").strip().lower()
    if configured_backend:
        return configured_backend
    return "vercel_blob" if os.getenv("BLOB_READ_WRITE_TOKEN") else "local"


def is_blob_storage_enabled() -> bool:
    return storage_backend() in {"vercel_blob", "minio", "s3"}


def state_blob_path() -> str:
    return os.getenv("CASHFLOW_STATE_BLOB_PATH", "cashflow-os/state.json").strip() or "cashflow-os/state.json"


def report_blob_path(report_id: str, file_format: str) -> str:
    prefix = os.getenv("CASHFLOW_REPORT_BLOB_PREFIX", "cashflow-os/reports").strip().strip("/")
    return "{prefix}/{report_id}.{file_format}".format(
        prefix=prefix or "cashflow-os/reports",
        report_id=report_id,
        file_format=file_format,
    )


def read_private_bytes(pathname: str) -> Optional[bytes]:
    backend = storage_backend()
    if backend in {"minio", "s3"}:
        try:
            import boto3
            from botocore.config import Config
            from botocore.exceptions import ClientError
        except ImportError as exc:
            raise RuntimeError("S3-compatible storage is enabled but 'boto3' is not installed.") from exc

        client = boto3.client(
            "s3",
            endpoint_url=os.getenv("CASHFLOW_S3_ENDPOINT_URL") or None,
            region_name=os.getenv("CASHFLOW_S3_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
            config=Config(s3={"addressing_style": "path"}),
        )
        bucket_name = os.getenv("CASHFLOW_S3_BUCKET", "cashflow-os-local").strip() or "cashflow-os-local"
        try:
            response = client.get_object(Bucket=bucket_name, Key=pathname)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404"}:
                return None
            raise RuntimeError("Could not read object from S3-compatible storage.") from exc
        return response["Body"].read()

    try:
        from vercel.blob import get
    except ImportError as exc:
        raise RuntimeError("Blob storage is enabled but the 'vercel' package is not installed.") from exc

    result = get(pathname, access="private")
    if result is None or result.status_code != 200 or result.stream is None:
        return None
    return b"".join(result.stream)


def write_private_bytes(pathname: str, content: bytes, *, content_type: Optional[str] = None) -> None:
    backend = storage_backend()
    if backend in {"minio", "s3"}:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError("S3-compatible storage is enabled but 'boto3' is not installed.") from exc

        client = boto3.client(
            "s3",
            endpoint_url=os.getenv("CASHFLOW_S3_ENDPOINT_URL") or None,
            region_name=os.getenv("CASHFLOW_S3_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
            config=Config(s3={"addressing_style": "path"}),
        )
        bucket_name = os.getenv("CASHFLOW_S3_BUCKET", "cashflow-os-local").strip() or "cashflow-os-local"
        put_args = {"Bucket": bucket_name, "Key": pathname, "Body": content}
        if content_type:
            put_args["ContentType"] = content_type
        client.put_object(**put_args)
        return

    try:
        from vercel.blob import put
    except ImportError as exc:
        raise RuntimeError("Blob storage is enabled but the 'vercel' package is not installed.") from exc

    put(
        pathname,
        content,
        access="private",
        content_type=content_type,
        overwrite=True,
    )
