import asyncio
from typing import Any

import httpx
from fastapi import APIRouter, Body, Header, Query, Request

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.config import get_settings
from ...infrastructure.dependencies import AsyncSessionDep
from ...infrastructure.logging import get_logger
from .sync import (
    logger as sync_logger,
)
from .sync import (
    sync_base_price_data,
    sync_base_price_task,
    sync_customer_master_data,
    sync_customer_master_task,
    sync_item_branch_data,
    sync_item_branch_task,
)

router = APIRouter(tags=["Sync Integrations"])
logger = get_logger()
settings = get_settings()


@router.post(
    "/item-branch",
    summary="Webhook Sync Item Branch",
    description="""
    Menerima payload JSON untuk sinkronisasi Item Branch (Stok Inventory) secara async (background task) atau sync.
    Menangani timeout koneksi/eksekusi dan memverifikasi API Key di header.
    """,
    responses={
        200: {
            "description": "Sinkronisasi Item Branch selesai secara synchronous.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "completed",
                        "message": "Sinkronisasi Item Branch selesai dijalankan secara synchronous.",
                        "result": {
                            "total_items": 100,
                            "updated_variants": 85,
                            "not_found_variants": 15,
                            "failed_items": 0
                        }
                    }
                }
            }
        },
        202: {
            "description": "Sinkronisasi Item Branch berhasil dijadwalkan secara asynchronous.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "queued",
                        "task_id": "task_abc123",
                        "message": "Sinkronisasi Item Branch telah dijadwalkan di latar belakang menggunakan worker."
                    }
                }
            }
        }
    }
)
async def webhook_sync_item_branch(
    request: Request,
    db: AsyncSessionDep,
    body: dict[str, Any] = Body(None),
    sync: bool = Query(False, description="Jalankan secara synchronous (tidak disarankan untuk data besar)"),
    x_api_key: str = Header(..., alias="X-API-Key", description="API Key untuk integrasi JDE"),
) -> dict[str, Any]:
    # 1. Verify API Key
    logger = sync_logger
    logger.info(f"Menerima request webhook sync item-branch. Headers: {dict(request.headers)}")
    if x_api_key != settings.JDE_API_KEY:
        logger.warning(f"Verifikasi API Key gagal. Nilai header X-API-Key: '{x_api_key}'")
        raise HTTPException(
            status_code=401,
            detail="API Key tidak valid atau tidak ditemukan di header X-API-Key.",
        )

    payload = body

    # 2. Fetch from JDE if payload is empty
    has_jde_keys = any(k.startswith("POS_") for k in payload.keys()) if payload and isinstance(payload, dict) else False
    if not payload or not isinstance(payload, dict) or not (has_jde_keys or "rowset" in payload or "data" in payload):
        jde_url = f"{settings.JDE_BASE_URL.rstrip('/')}/sync/item-branch"
        logger.info(f"Tidak ada payload body. Mengambil data dari JDE POS Server: {jde_url}")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    jde_url,
                    headers={"X-API-Key": settings.JDE_API_KEY},
                )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "Gagal mengambil data dari JDE POS Server. "
                            f"Server JDE merespons dengan status code: {resp.status_code}"
                        ),
                    )
                payload = resp.json()
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Waktu tunggu habis (Request Timeout) saat menghubungi JDE POS Server.",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Kesalahan koneksi saat menghubungi JDE POS Server: {str(e)}",
            )
        except ValueError:
            raise HTTPException(
                status_code=502,
                detail="Respon dari JDE POS Server bukan JSON yang valid.",
            )

    # Validate structure
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail=f"Format payload tidak valid. Tipe data yang diterima: {type(payload)}",
        )

    # 3. Execution
    if sync:
        logger.info("Menjalankan sinkronisasi Item Branch secara synchronous...")
        try:
            result = await asyncio.wait_for(sync_item_branch_data(db, payload), timeout=60.0)
            return {
                "success": True,
                "status": "completed",
                "message": "Sinkronisasi Item Branch selesai dijalankan secara synchronous.",
                "result": result,
            }
        except asyncio.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Waktu eksekusi sinkronisasi habis (Processing Timeout). Harap jalankan secara asynchronous.",
            )
        except Exception as e:
            logger.error(f"Kesalahan sinkronisasi synchronous: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Terjadi kesalahan saat sinkronisasi: {str(e)}")
    else:
        logger.info("Menjadwalkan sinkronisasi Item Branch secara asynchronous...")
        try:
            task = await sync_item_branch_task.kiq(payload)
            return {
                "success": True,
                "status": "queued",
                "task_id": task.task_id,
                "message": "Sinkronisasi Item Branch telah dijadwalkan di latar belakang menggunakan worker.",
            }
        except Exception as e:
            logger.error(f"Gagal menjadwalkan background task: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Gagal menjadwalkan sinkronisasi di latar belakang: {str(e)}",
            )


@router.post(
    "/base-price",
    summary="Webhook Sync Base Price",
    description="""
    Menerima payload JSON untuk sinkronisasi Base Price secara async (background task) atau sync.
    Menangani timeout koneksi/eksekusi dan memverifikasi API Key di header.
    """,
    responses={
        200: {
            "description": "Sinkronisasi Base Price selesai secara synchronous.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "completed",
                        "message": "Sinkronisasi Base Price selesai dijalankan secara synchronous.",
                        "result": {
                            "total_items": 100,
                            "updated_variants": 85,
                            "not_found_variants": 15,
                            "failed_items": 0
                        }
                    }
                }
            }
        },
        202: {
            "description": "Sinkronisasi Base Price berhasil dijadwalkan secara asynchronous.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "queued",
                        "task_id": "task_abc123",
                        "message": "Sinkronisasi Base Price telah dijadwalkan di latar belakang menggunakan worker."
                    }
                }
            }
        }
    }
)
async def webhook_sync_base_price(
    request: Request,
    db: AsyncSessionDep,
    body: dict[str, Any] = Body(None),
    sync: bool = Query(False, description="Jalankan secara synchronous (tidak disarankan untuk data besar)"),
    x_api_key: str = Header(..., alias="X-API-Key", description="API Key untuk integrasi JDE"),
) -> dict[str, Any]:
    # 1. Verify API Key
    logger = sync_logger
    logger.info(f"Menerima request webhook sync base-price. Headers: {dict(request.headers)}")
    if x_api_key != settings.JDE_API_KEY:
        logger.warning(f"Verifikasi API Key gagal. Nilai header X-API-Key: '{x_api_key}'")
        raise HTTPException(
            status_code=401,
            detail="API Key tidak valid atau tidak ditemukan di header X-API-Key.",
        )

    payload = body

    # 2. Fetch from JDE if payload is empty
    has_jde_keys = any(k.startswith("POS_") for k in payload.keys()) if payload and isinstance(payload, dict) else False
    if not payload or not isinstance(payload, dict) or not (has_jde_keys or "rowset" in payload or "data" in payload):
        jde_url = f"{settings.JDE_BASE_URL.rstrip('/')}/sync/base-price"
        logger.info(f"Tidak ada payload body. Mengambil data dari JDE POS Server: {jde_url}")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    jde_url,
                    headers={"X-API-Key": settings.JDE_API_KEY},
                )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "Gagal mengambil data dari JDE POS Server. "
                            f"Server JDE merespons dengan status code: {resp.status_code}"
                        ),
                    )
                payload = resp.json()
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Waktu tunggu habis (Request Timeout) saat menghubungi JDE POS Server.",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Kesalahan koneksi saat menghubungi JDE POS Server: {str(e)}",
            )
        except ValueError:
            raise HTTPException(
                status_code=502,
                detail="Respon dari JDE POS Server bukan JSON yang valid.",
            )

    # Validate structure
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail=f"Format payload tidak valid. Tipe data yang diterima: {type(payload)}",
        )

    # 3. Execution
    if sync:
        logger.info("Menjalankan sinkronisasi Base Price secara synchronous...")
        try:
            result = await asyncio.wait_for(sync_base_price_data(db, payload), timeout=60.0)
            return {
                "success": True,
                "status": "completed",
                "message": "Sinkronisasi Base Price selesai dijalankan secara synchronous.",
                "result": result,
            }
        except asyncio.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Waktu eksekusi sinkronisasi habis (Processing Timeout). Harap jalankan secara asynchronous.",
            )
        except Exception as e:
            logger.error(f"Kesalahan sinkronisasi synchronous: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Terjadi kesalahan saat sinkronisasi: {str(e)}")
    else:
        logger.info("Menjadwalkan sinkronisasi Base Price secara asynchronous...")
        try:
            task = await sync_base_price_task.kiq(payload)
            return {
                "success": True,
                "status": "queued",
                "task_id": task.task_id,
                "message": "Sinkronisasi Base Price telah dijadwalkan di latar belakang menggunakan worker.",
            }
        except Exception as e:
            logger.error(f"Gagal menjadwalkan background task: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Gagal menjadwalkan sinkronisasi di latar belakang: {str(e)}",
            )


@router.post(
    "/customer-master",
    summary="Webhook Sync Customer Master",
    description="""
    Menerima payload JSON untuk sinkronisasi Customer Master secara async (background task) atau sync.
    Menangani timeout koneksi/eksekusi dan memverifikasi API Key di header.
    """,
    responses={
        200: {
            "description": "Sinkronisasi Customer Master selesai secara synchronous.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "completed",
                        "message": "Sinkronisasi Customer Master selesai dijalankan secara synchronous.",
                        "result": {
                            "total_items": 50,
                            "inserted_customers": 5,
                            "updated_customers": 45,
                            "inserted_addresses": 10,
                            "updated_addresses": 35,
                            "failed_items": 0
                        }
                    }
                }
            }
        },
        202: {
            "description": "Sinkronisasi Customer Master berhasil dijadwalkan secara asynchronous.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "queued",
                        "task_id": "task_abc123",
                        "message": "Sinkronisasi Customer Master telah dijadwalkan di latar belakang menggunakan worker."
                    }
                }
            }
        }
    }
)
async def webhook_sync_customer_master(
    request: Request,
    db: AsyncSessionDep,
    body: dict[str, Any] = Body(None),
    sync: bool = Query(False, description="Jalankan secara synchronous (tidak disarankan untuk data besar)"),
    x_api_key: str = Header(..., alias="X-API-Key", description="API Key untuk integrasi JDE"),
) -> dict[str, Any]:
    # 1. Verify API Key
    logger = sync_logger
    logger.info(f"Menerima request webhook sync customer-master. Headers: {dict(request.headers)}")
    if x_api_key != settings.JDE_API_KEY:
        logger.warning(f"Verifikasi API Key gagal. Nilai header X-API-Key: '{x_api_key}'")
        raise HTTPException(
            status_code=401,
            detail="API Key tidak valid atau tidak ditemukan di header X-API-Key.",
        )

    payload = body

    # 2. Fetch from JDE if payload is empty
    has_jde_keys = any(k.startswith("POS_") for k in payload.keys()) if payload and isinstance(payload, dict) else False
    if not payload or not isinstance(payload, dict) or not (has_jde_keys or "rowset" in payload or "data" in payload):
        jde_url = f"{settings.JDE_BASE_URL.rstrip('/')}/sync/customer-master"
        logger.info(f"Tidak ada payload body. Mengambil data dari JDE POS Server: {jde_url}")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    jde_url,
                    headers={"X-API-Key": settings.JDE_API_KEY},
                )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "Gagal mengambil data dari JDE POS Server. "
                            f"Server JDE merespons dengan status code: {resp.status_code}"
                        ),
                    )
                payload = resp.json()
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Waktu tunggu habis (Request Timeout) saat menghubungi JDE POS Server.",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Kesalahan koneksi saat menghubungi JDE POS Server: {str(e)}",
            )
        except ValueError:
            raise HTTPException(
                status_code=502,
                detail="Respon dari JDE POS Server bukan JSON yang valid.",
            )

    # Validate structure
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail=f"Format payload tidak valid. Tipe data yang diterima: {type(payload)}",
        )

    # 3. Execution
    if sync:
        logger.info("Menjalankan sinkronisasi Customer Master secara synchronous...")
        try:
            result = await asyncio.wait_for(sync_customer_master_data(db, payload), timeout=60.0)
            return {
                "success": True,
                "status": "completed",
                "message": "Sinkronisasi Customer Master selesai dijalankan secara synchronous.",
                "result": result,
            }
        except asyncio.TimeoutException:
            raise HTTPException(
                status_code=408,
                detail="Waktu eksekusi sinkronisasi habis (Processing Timeout). Harap jalankan secara asynchronous.",
            )
        except Exception as e:
            logger.error(f"Kesalahan sinkronisasi synchronous: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Terjadi kesalahan saat sinkronisasi: {str(e)}")
    else:
        logger.info("Menjadwalkan sinkronisasi Customer Master secara asynchronous...")
        try:
            task = await sync_customer_master_task.kiq(payload)
            return {
                "success": True,
                "status": "queued",
                "task_id": task.task_id,
                "message": "Sinkronisasi Customer Master telah dijadwalkan di latar belakang menggunakan worker.",
            }
        except Exception as e:
            logger.error(f"Gagal menjadwalkan background task: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Gagal menjadwalkan sinkronisasi di latar belakang: {str(e)}",
            )
