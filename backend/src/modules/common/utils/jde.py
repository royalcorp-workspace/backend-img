"""Helpers for interacting with the external JDE POS Server.

These utilities centralize fetching the payload from the JDE POS Server when no
request body is provided, validating the response structure, and logging the
result (item count) so each receiver endpoint behaves consistently.
"""

import logging
from typing import Any

from ....infrastructure.auth.http_exceptions import HTTPException
from ....infrastructure.config import get_settings


_ENDPOINT_ITEM_KEYS = {
    "item-branch": {"branches", "items", "stores", "rows"},
    "customer-master": {"customers", "branches"},
}


def extract_jde_rowset(payload: Any, endpoint: str = "") -> Any:
    """Extract the rowset/data list from a JDE payload.

    Preferred keys depend on endpoint:
      - item-branch: rowset, data, branches, items, stores, rows, POS_* wrappers
      - customer-master: rowset, data, customers, branches, POS_* wrappers
      - base-price: rowset, data, prices, POS_* wrappers
    A bare list payload is returned as-is.
    """
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return None
    preferred_keys = ("rowset", "data", *_ENDPOINT_ITEM_KEYS.get(endpoint, ()))
    for key in preferred_keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    for key, value in payload.items():
        if key.startswith("POS_") and isinstance(value, dict):
            rowset = value.get("rowset") or value.get("data")
            if isinstance(rowset, list):
                return rowset
    if endpoint == "item-branch":
        for key, value in payload.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
    return None


def validate_and_log_jde_payload(
    payload: Any,
    endpoint: str,
    logger: logging.Logger,
) -> int:
    """Validate a payload returned by the JDE POS Server and log the result.

    Args:
        payload: The parsed JSON response from the JDE POS Server.
        endpoint: Receiver endpoint name (e.g. ``item-branch``) used in logs.
        logger: Logger for the current receiver.

    Returns:
        The number of items in the payload's rowset (``0`` when empty).

    Raises:
        HTTPException: When the payload is not a dict, lacks any recognizable
            data structure, or cannot be interpreted as a list of rows.
    """
    if not isinstance(payload, (dict, list)):
        logger.error(f"Respon JDE untuk '{endpoint}' tidak valid (bukan objek JSON).")
        raise HTTPException(
            status_code=502,
            detail=f"Respon JDE untuk '{endpoint}' tidak valid (bukan objek JSON).",
        )

    rowset = extract_jde_rowset(payload, endpoint)
    if rowset is None:
        allowed = ["rowset", "data", *_ENDPOINT_ITEM_KEYS.get(endpoint, ())]
        logger.error(
            f"Respon JDE untuk '{endpoint}' tidak mengandung data "
            f"({', '.join(allowed)}). Kunci response: {list(payload.keys()) if isinstance(payload, dict) else payload}"
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Format payload JDE tidak valid. Tidak ditemukan data "
                f"'{', '.join(allowed)}' dalam response JDE '{endpoint}'. "
                f"Kunci response: {list(payload.keys()) if isinstance(payload, dict) else payload}"
            ),
        )

    if not isinstance(rowset, list):
        logger.error(f"Respon JDE untuk '{endpoint}' bukan berisi list rowset.")
        raise HTTPException(
            status_code=400,
            detail=f"Format payload JDE '{endpoint}' tidak valid (rowset bukan list).",
        )

    total = len(rowset)
    if total == 0:
        logger.warning(f"Respon JDE untuk '{endpoint}' kosong (0 item).")
    else:
        logger.info(f"Berhasil mengambil {total} item dari JDE POS Server ({endpoint}).")
    return total


async def fetch_jde_payload(
    endpoint: str,
    logger: logging.Logger,
) -> tuple[dict[str, Any], int]:
    """Fetch the payload from the JDE POS Server and validate/log the response.

    Used when the incoming webhook request has no payload body. Validates the
    response structure and item count before the caller schedules or runs sync.

    Returns:
        A tuple of ``(payload, total_items)``.

    Raises:
        HTTPException: On connection errors, non-200 status, invalid JSON,
            or an invalid/empty-struct JDE response.
    """
    settings = get_settings()
    jde_url = f"{settings.JDE_BASE_URL.rstrip('/')}/sync/{endpoint}"
    logger.info(f"Tidak ada payload body. Mengambil data dari JDE POS Server: {jde_url}")
    try:
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                jde_url,
                headers={"X-API-Key": settings.JDE_API_KEY},
            )
            if resp.status_code != 200:
                logger.error(
                    f"Gagal mengambil data dari JDE POS Server. Status: {resp.status_code}"
                )
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Gagal mengambil data dari JDE POS Server. "
                        f"Server JDE merespons dengan status code: {resp.status_code}"
                    ),
                )
            try:
                payload = resp.json()
            except ValueError:
                logger.error("Respon dari JDE POS Server bukan JSON yang valid.")
                raise HTTPException(
                    status_code=502,
                    detail="Respon dari JDE POS Server bukan JSON yang valid.",
                )
    except httpx.TimeoutException:
        logger.error("Waktu tunggu habis (Request Timeout) saat menghubungi JDE POS Server.")
        raise HTTPException(
            status_code=408,
            detail="Waktu tunggu habis (Request Timeout) saat menghubungi JDE POS Server.",
        )
    except httpx.RequestError as e:
        logger.error(f"Kesalahan koneksi saat menghubungi JDE POS Server: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Kesalahan koneksi saat menghubungi JDE POS Server: {str(e)}",
        )

    total = validate_and_log_jde_payload(payload, endpoint, logger)
    return payload, total
