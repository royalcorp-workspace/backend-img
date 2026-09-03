import os
from typing import Any

DEFAULT_MEDIA_BASE_URL = "https://media.royalcorp.co.id/ecommerce-media"


def get_media_url(path: Any) -> str | None:
    """Format an image path into a full public S3 URL.

    If path is already a full URL (starts with http:// or https://), it is returned as-is.
    If path is None or empty, returns None.
    Otherwise, it is prefixed with the public S3 base URL.
    """
    if not path:
        return None
    path_str = str(path).strip()
    if not path_str:
        return None

    if path_str.startswith(("http://", "https://")):
        return path_str

    base_url = (os.getenv("AWS_URL") or os.getenv("MEDIA_URL") or DEFAULT_MEDIA_BASE_URL).rstrip("/")
    clean_path = path_str.lstrip("/")
    return f"{base_url}/{clean_path}"
